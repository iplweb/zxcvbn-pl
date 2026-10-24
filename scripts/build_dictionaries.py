"""Build the Polish zxcvbn dictionaries shipped in ``src/zxcvbn_pl/data``.

Common words, first names and last names come from the
``@zxcvbn-ts/language-pl`` npm package (pinned version, verified against the
registry's sha512 integrity). Each upstream list is ordered by frequency; the
position becomes the zxcvbn rank. Male and female lists are merged (lower rank
wins).

Place names (``pl_places``) come from two public sources, both pinned and
checksum-verified (see ``build_places`` for the ranking):

* the official list of Polish place names (Wykaz urzędowych nazw miejscowości
  i ich części, MSWiA, CC0 1.0, dane.gov.pl dataset 188) — every locality with
  its TERYT SIMC identifier,
* the population of every town as of 31 Dec 2025 (GUS, Bank Danych Lokalnych,
  CC BY 4.0) — used to order the towns.

First names, last names and place names are then extended with their
inflected forms (cases, plural: ``wrocławiu``, ``kowalskiego``,
``zielonejgórze``) taken from SGJP, the grammatical dictionary of Polish
(BSD-2-Clause, pinned and checksum-verified; see ``Inflector`` and
``add_inflections``).

For every word with Polish diacritics a variant without them is added with
the same rank (``żółw`` -> ``zolw``) — that is how such words are usually
typed in passwords.

Run from the repository root (needs only the runtime dependency)::

    uv run python scripts/build_dictionaries.py [--cache-dir DIR]

It downloads ~50 MB and makes ~40 requests to the GUS BDL API, which limits
anonymous clients (HTTP 429 is retried); ``--cache-dir`` avoids re-downloading
on repeated builds.

The output is deterministic: the same upstream data gives byte-identical
``.marisa`` files.
"""

import argparse
import base64
import gzip
import hashlib
import io
import itertools
import json
import re
import tarfile
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import marisa_trie

UPSTREAM_VERSION = "4.1.1"
UPSTREAM_URL = (
    "https://registry.npmjs.org/@zxcvbn-ts/language-pl/-/"
    f"language-pl-{UPSTREAM_VERSION}.tgz"
)
UPSTREAM_SHA512 = (
    "hF6Qu9cyHx7sSEzNOQrJQntq8geoincsGvlOC0wkD43LnUVSTR49MKxdsifsemlQgtxR7aUK"
    "DgK/e/RFHOljoQ=="
)

# Output dictionary name -> upstream lists merged into it.
DICTIONARIES = {
    "pl_common_words": ["commonWords"],
    "pl_first_names": ["femaleFirstnames", "maleFirstnames"],
    "pl_last_names": ["femaleLastnames", "maleLastnames"],
}

# Single letters and two-letter tokens match everywhere and only add noise.
MIN_LENGTH = 3

# Wykaz urzędowych nazw miejscowości i ich części — the annex to the MSWiA
# notice of 17 Oct 2019 (Dz. U. 2019 poz. 2360), state as of 1 Jan 2019.
# https://dane.gov.pl/pl/dataset/188 (CC0 1.0), resource 60795.
PLACES_URL = (
    "https://api.dane.gov.pl/media/resources/20240918/wykaz_stan_na_1.1.2019.xlsx"
)
PLACES_SHA256 = "13ac25bee2d120c6cdfec02449d08d468394e402574f3855c95fbc689773c101"
# Number of localities in the list; a guard against a silently changed file
# format (the checksum guards the bytes, this guards the parser).
PLACES_ROWS = 102875

# GUS Bank Danych Lokalnych, variable 72305 (population, total, actual place of
# residence, as of 31 Dec) at the gmina level. https://api.stat.gov.pl/Home/BdlApi
# (CC BY 4.0). The API returns JSON whose formatting may change, so the
# checksum covers a normalized ``unit_id<TAB>name<TAB>population`` listing.
POPULATION_YEAR = 2025
POPULATION_URL = (
    "https://bdl.stat.gov.pl/api/v1/data/by-variable/72305"
    f"?unit-level=6&year={POPULATION_YEAR}&page-size=100&format=json"
)
POPULATION_SHA256 = "7b51b7794f2a41aa9baf09cfd65b05556268d87242a3b62cee15b44fc15bb665"
# The last digit of a BDL gmina-level unit id is its kind: 1 = urban gmina,
# 4 = the town of an urban-rural gmina. Together they are all Polish towns.
TOWN_UNIT_KINDS = ("1", "4")

# SGJP — Słownik gramatyczny języka polskiego (Woliński, Bronk, Gruszczyński,
# Kieraś, Saloni, Skowrońska, Wołosz; BSD-2-Clause), the "tab" export used by
# Morfeusz 2: one ``form<TAB>lemma<TAB>tag<TAB>qualifiers<TAB>...`` line per
# inflected form. https://morfeusz.sgjp.pl/download/ — the same edition that
# polish-inflection-data 2026.6.28 is built from.
SGJP_VERSION = "20260628"
SGJP_DICT_ID = "pl.sgjp.sgjp-2026.06.29"
SGJP_URL = (
    f"https://download.sgjp.pl/morfeusz/{SGJP_VERSION}/sgjp-{SGJP_VERSION}.tab.gz"
)
SGJP_SHA256 = "84b9b98148f73ecee8fadde2bb827e9711c364f59cc1b56efe99fe81c9db8a3b"

# SGJP qualifiers (4th column) of the lexemes whose forms extend a dictionary.
# Only proper names are used, so ``Wrocław`` gets ``wrocławiu`` but a village
# called ``Las`` does not get the forms of the common noun ``las``.
INFLECTED_CATEGORIES = {
    "pl_first_names": frozenset({"imię"}),
    "pl_last_names": frozenset(
        {"nazwisko", "nazwisko_(odmężowskie)", "nazwisko_(odojcowskie)"}
    ),
    "pl_places": frozenset({"nazwa_geograficzna", "człon_nazwy_geograficznej"}),
}
# Qualifiers of ordinary vocabulary (adjectives and verbs have none).
COMMON_CATEGORIES = frozenset({"", "nazwa_pospolita"})
# Inflected forms that are also among this many most frequent common words
# (and forms of a common word in SGJP) are left to ``pl_common_words``:
# ``górze`` (997th), ``kota`` (3400th), ``mają`` (233rd) are everyday words.
# SGJP lists many rare common homographs (``warszawa`` the car, ``paweł`` a
# rose, ``marto`` from ``mrzeć``), so a rarer form (``warszawie``, 38069th;
# ``poznaniu``, 47529th) is taken to be mostly the name itself.
COMMON_WORD_RANK_LIMIT = 10000

# An inflected form gets the rank of its base form times this factor (zxcvbn
# reads the rank as "guesses needed"). A name has ~10-14 forms, but they are
# far from equally likely — the locative and genitive (``we Wrocławiu``,
# ``z Krakowa``) dominate — so the full form count would overrate the typical
# password; 2 says "a bit less likely than the base form". Measured on ~6800
# passwords built from the forms of the top 100 towns, first and last names
# (``Wrocławiu2024!``, ``krakowa1990``): factors 1 and 2 give the same score
# distribution, 4 moves ~3 % of them from 2 to 3, the form count (14) ~24 %.
INFLECTED_RANK_FACTOR = 2

SGJP_CASES = ("nom", "gen", "dat", "acc", "inst", "loc", "voc")
SGJP_NUMBERS = ("sg", "pl")
# Parts of speech that decline like adjectives; their last tag field is the
# degree (adj) or negation (participles), only the plain one is used.
SGJP_ADJECTIVES = {"adj": "pos", "pact": "aff", "ppas": "aff"}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "zxcvbn_pl" / "data"


def strip_diacritics(word):
    word = word.replace("ł", "l")
    word = unicodedata.normalize("NFKD", word)
    return "".join(c for c in word if not unicodedata.combining(c))


# Optional download cache (``--cache-dir``); every download is still
# checksum-verified, so a cached file cannot change the output.
CACHE_DIR = None


def fetch(url, attempts=5):
    if CACHE_DIR is not None:
        cached = CACHE_DIR / hashlib.sha256(url.encode()).hexdigest()
        if cached.exists():
            return cached.read_bytes()
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                payload = response.read()
            break
        except urllib.error.HTTPError as error:
            # The BDL API rate-limits anonymous clients (HTTP 429); wait and
            # retry, give up (re-raise) after the last attempt.
            if error.code != 429 or attempt == attempts:
                raise
            # BDL sends a non-standard "Retry-After: 532 sek".
            retry_after = re.match(r"\d+", error.headers.get("Retry-After") or "")
            delay = int(retry_after.group()) + 1 if retry_after else 60
            print(f"HTTP 429 for {url}, retrying in {delay} s")
            time.sleep(delay)
    if CACHE_DIR is not None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(payload)
    return payload


def download():
    payload = fetch(UPSTREAM_URL)
    digest = base64.b64encode(hashlib.sha512(payload).digest()).decode()
    if digest != UPSTREAM_SHA512:
        raise RuntimeError(
            f"sha512 mismatch for {UPSTREAM_URL}: got {digest}, "
            f"expected {UPSTREAM_SHA512}"
        )
    return payload


def read_lists(payload):
    lists = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        for name in {n for names in DICTIONARIES.values() for n in names}:
            member = tar.extractfile(f"package/src/{name}.json")
            lists[name] = json.load(member)
    return lists


def build_ranks(upstream_lists):
    """Return ``(ranks, sources)``: the dictionary and its ``(word, rank)``."""
    ranks = {}
    sources = []
    for words in upstream_lists:
        for position, word in enumerate(words, start=1):
            word = word.strip().lower()
            add_word(ranks, word, position)
            sources.append((word, position))
    return ranks, sources


def add_word(ranks, word, rank):
    """Add ``word`` and its diacritics-free variant, keeping the lower rank."""
    if len(word) < MIN_LENGTH or not word.isalpha():
        return
    for variant in (word, strip_diacritics(word)):
        if rank < ranks.get(variant, rank + 1):
            ranks[variant] = rank


def strip_place_suffix(name):
    """Drop the disambiguating ``k. <other place>`` ("near ...") suffix that a
    few names in the official list carry: ``"Brzezie k. Sulechowa"``."""
    return re.sub(r"\s+k\.\s.*$", "", name.strip())


def split_place_name(name):
    """``"Bielsko-Biała"`` -> ``["bielsko", "biała"]``."""
    name = strip_place_suffix(name)
    return [part for part in re.split(r"[\s-]+", name.lower()) if part]


def sha256_checked(payload, expected, what):
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected:
        raise RuntimeError(
            f"sha256 mismatch for {what}: got {digest}, expected {expected}"
        )


def read_places():
    """Return all locality names from the official list (one per locality)."""
    payload = fetch(PLACES_URL)
    sha256_checked(payload, PLACES_SHA256, PLACES_URL)
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(io.BytesIO(payload)) as xlsx:
        with xlsx.open("xl/sharedStrings.xml") as f:
            strings = [
                "".join(t.text or "" for t in item.iter(f"{ns}t"))
                for item in ET.parse(f).getroot()
            ]
        names = []
        with xlsx.open("xl/worksheets/sheet1.xml") as f:
            for _, row in ET.iterparse(f):
                if row.tag != f"{ns}row":
                    continue
                cells = {}
                for cell in row:
                    value = cell.find(f"{ns}v")
                    if value is None:
                        continue
                    text = value.text or ""
                    if cell.get("t") == "s":
                        text = strings[int(text)]
                    cells[cell.get("r").rstrip("0123456789")] = text
                row.clear()
                # Column A: name, F: TERYT SIMC id. Rows without an id are
                # the title, the (repeated) header and the column numbers.
                if re.fullmatch(r"\d{7}", cells.get("F", "").strip()):
                    names.append(cells["A"])
    if len(names) != PLACES_ROWS:
        raise RuntimeError(f"expected {PLACES_ROWS} localities, got {len(names)}")
    return names


def read_town_population():
    """Return ``[(town name, population)]`` for every Polish town."""
    results = []
    url = POPULATION_URL
    while url:
        page = json.loads(fetch(url))
        results.extend(page["results"])
        url = page["links"].get("next")
        time.sleep(0.5)  # stay well below the anonymous API rate limit
    listing = "".join(
        f"{unit['id']}\t{unit['name']}\t{unit['values'][0]['val']}\n"
        for unit in sorted(results, key=lambda unit: unit["id"])
    )
    sha256_checked(listing.encode(), POPULATION_SHA256, POPULATION_URL)
    towns = []
    for unit in results:
        if unit["id"][-1] not in TOWN_UNIT_KINDS:
            continue
        # "M.st.Warszawa od 2002" -> "Warszawa", "Wałbrzych od 2013" ->
        # "Wałbrzych", "Skawina - miasto" -> "Skawina".
        name = re.sub(r"^M\.\s?st\.\s?", "", unit["name"])
        name = re.sub(r"\s+od\s+\d{4}$", "", name)
        name = re.sub(r"\s+-\s+miasto$", "", name)
        if not re.fullmatch(r"[^\W\d_]+(?:[ -][^\W\d_]+)*", name):
            raise RuntimeError(f"unexpected town name in BDL: {unit['name']!r}")
        towns.append((name, unit["values"][0]["val"]))
    return towns


def build_places(towns, places, common_words):
    """Rank place names; there is no usage frequency for them, so:

    1. Towns first, by population, largest first (Warszawa = 1, Kraków = 2,
       ...). A big town is a far more likely password ingredient than a small
       one (more people live there, more people know it), so population is the
       best open proxy for "how often it gets typed".
    2. Then every other locality name (villages, hamlets, districts of towns
       such as Mokotów or Nowa Huta), by how many localities in Poland carry
       it, most common first (Nowa Wieś, Dąbrowa, ...): a name shared by
       hundreds of villages is known to far more people than a one-off hamlet.
       Ties are broken alphabetically to keep the output deterministic.

    Multi-word and hyphenated names are glued (``zielonagora``,
    ``bielskobiala``) — that is how they end up in passwords. The separate
    words of *town* names are added too, with the town's rank (``bielsko``,
    ``gorzow``, ``sacz``): people shorten them that way — except words that
    are in ``pl_common_words`` (``zielona``, ``nowa``, ``wielkopolski``): those
    are ordinary words, already ranked there by real frequency, and giving
    them a town's top rank would only weaken passphrases. For other localities
    only the glued form is added — their parts are almost always ordinary
    words (``nowa``, ``wieś``, ``górna``).

    Returns ``(ranks, sources)``; ``sources`` lists the original names (and
    the added town words) with their ranks, for ``add_inflections``.
    """
    ranks = {}
    sources = []
    ordered_towns = sorted(towns, key=lambda town: (-town[1], town[0]))
    for position, (name, _) in enumerate(ordered_towns, start=1):
        parts = split_place_name(name)
        add_word(ranks, "".join(parts), position)
        sources.append((name, position))
        if len(parts) > 1:
            for part in parts:
                if part not in common_words:
                    add_word(ranks, part, position)
                    sources.append((part, position))
    # The glued name -> the original spellings it comes from; the inflection
    # needs the original (case marks the frozen tail of "Nowe Miasto nad
    # Pilicą"), the smallest one is taken to stay deterministic.
    spellings = defaultdict(set)
    for name in places:
        spellings["".join(split_place_name(name))].add(strip_place_suffix(name))
    counts = Counter("".join(split_place_name(name)) for name in places)
    ordered_places = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    for position, (word, _) in enumerate(ordered_places, start=len(towns) + 1):
        add_word(ranks, word, position)
        sources.append((min(spellings[word]), position))
    return ranks, sources


def read_sgjp():
    """Return the pinned SGJP export, checksum- and edition-verified."""
    payload = fetch(SGJP_URL)
    sha256_checked(payload, SGJP_SHA256, SGJP_URL)
    with gzip.open(io.BytesIO(payload), "rt", encoding="utf-8") as f:
        header = f.readline().strip()
    if header != f"#!DICT-ID {SGJP_DICT_ID}":
        raise RuntimeError(f"unexpected SGJP edition: {header!r}")
    return payload


def sgjp_entries(payload):
    """Yield ``(form, lemma, pos, fields, qualifiers)`` for every SGJP line.

    ``fields`` are the tag fields after the part of speech (``subst:sg:
    gen.acc:m1`` -> ``("sg", "gen.acc", "m1")``). The licence block at the
    top of the file has no tabs, which is how it is skipped.
    """
    with gzip.open(io.BytesIO(payload), "rt", encoding="utf-8") as f:
        for line in f:
            columns = line.rstrip("\r\n").split("\t")
            if len(columns) < 4 or line.startswith("#"):
                continue
            pos, *fields = columns[2].split(":")
            yield columns[0], columns[1], pos, fields, columns[3]


class Inflector:
    """Inflected forms of names, from SGJP.

    SGJP keeps one lexeme per proper name (``Wrocław``, ``Kowalski:Sm1``,
    ``Katarzyna``) with all its forms; multi-word place names are stored word
    by word (``Zielona`` and ``Góra`` are both geographic names, ``Sącz`` and
    ``Wieś`` are "parts of geographic names", ``Nowy`` may only be an
    adjective), so ``inflect`` declines every word of a name in the same
    case and glues them: ``Zielona Góra`` -> ``zielonejgórze``.

    Built in two passes over SGJP: the first finds the lexemes whose
    nominative is one of ``words`` (lowercase), the second collects all their
    forms. ``common_forms`` makes a third pass.
    """

    def __init__(self, payload, words):
        self._payload = payload
        # word -> [(kind, lemma, number, genders, qualifiers)], kind is
        # "subst" or "adj"; from nominative forms only.
        self._nominatives = defaultdict(list)
        for form, lemma, pos, fields, qualifiers in sgjp_entries(payload):
            entry = self._entry(pos, fields)
            if entry is None or "nom" not in fields[1].split("."):
                continue
            word = form.lower()
            if word not in words:
                continue
            kind, genders = entry
            for number in fields[0].split("."):
                self._nominatives[word].append(
                    (kind, lemma, number, genders, frozenset(qualifiers.split("|")))
                )
        wanted = {
            (kind, lemma) for c in self._nominatives.values() for kind, lemma, *_ in c
        }
        # (kind, lemma) -> {(number, case, gender): {forms}}
        self._forms = defaultdict(lambda: defaultdict(set))
        for form, lemma, pos, fields, _ in sgjp_entries(payload):
            entry = self._entry(pos, fields)
            if entry is None or (entry[0], lemma) not in wanted:
                continue
            kind, genders = entry
            slots = self._forms[(kind, lemma)]
            for number in fields[0].split("."):
                for case in fields[1].split("."):
                    for gender in genders:
                        slots[(number, case, gender)].add(form.lower())

    @staticmethod
    def _entry(pos, fields):
        """``(kind, genders)`` for nouns and adjectival words, else ``None``.

        Deprecative forms (``depr``) and comparatives are left out.
        """
        if pos == "subst" and len(fields) >= 3:
            return "subst", tuple(fields[2].split("."))
        if SGJP_ADJECTIVES.get(pos) and len(fields) >= 4:
            if fields[3] == SGJP_ADJECTIVES[pos]:
                return "adj", tuple(fields[2].split("."))
        return None

    def _forms_of(self, kind, lemma, number, case, genders):
        slots = self._forms[(kind, lemma)]
        return {form for g in genders for form in slots.get((number, case, g), ())}

    def _nouns(self, word, categories):
        """Noun readings of ``word``, best tier only: geographic (or other
        ``categories``) first, then other proper names, then common nouns."""
        tiers = (
            lambda q: q & categories,
            lambda q: not q & COMMON_CATEGORIES,
            lambda q: True,
        )
        nouns = [c for c in self._nominatives.get(word, ()) if c[0] == "subst"]
        for tier in tiers:
            found = [c for c in nouns if tier(c[4])]
            if found:
                return found
        return []

    def inflect_word(self, word, categories):
        """All forms of the ``categories`` lexemes whose nominative is ``word``.

        A singular nominative brings both numbers (``wrocławiu``,
        ``wrocławiach``), a plural one (``Tychy``) only the plural.
        """
        forms = set()
        for _, lemma, number, genders, qualifiers in self._nominatives.get(
            word.lower(), ()
        ):
            if qualifiers & categories and len(word) >= MIN_LENGTH:
                numbers = SGJP_NUMBERS if number == "sg" else (number,)
                for n in numbers:
                    for case in SGJP_CASES:
                        forms |= self._forms_of("subst", lemma, n, case, genders)
        return forms

    def inflect(self, name, categories):
        """Glued inflected forms of a (possibly multi-word) name.

        Words from the first lowercase one on (``nad Pilicą``, ``pod
        Ojcowem``) stay as they are. The head is the first ``categories``
        noun that is not also an adjective (``Góra``, not ``Zielona``), the
        name is only declined in the number of its head (``Tarnowskie Góry``
        stays plural). Returns an empty set when any word has no reading in
        SGJP.
        """
        words = [w for w in re.split(r"[\s-]+", name) if w]
        if len(words) == 1:
            return self.inflect_word(words[0], categories)
        frozen = next((i for i, w in enumerate(words) if w[0].islower()), len(words))
        tail = "".join(words[frozen:]).lower()
        words = [w.lower() for w in words[:frozen]]
        if not words:
            return set()
        nouns = [self._nouns(w, categories) for w in words]
        adjectives = [
            [c for c in self._nominatives.get(w, ()) if c[0] == "adj"] for w in words
        ]

        def head_rank(i):
            proper = bool(nouns[i]) and bool(nouns[i][0][4] & categories)
            if not nouns[i]:
                return 4
            return (0 if proper else 2) + bool(adjectives[i])

        head = min(range(len(words)), key=lambda i: (head_rank(i), i))
        if not nouns[head]:
            return set()
        number = "sg" if any(c[2] == "sg" for c in nouns[head]) else nouns[head][0][2]

        def declension(i, head_genders):
            """``[(kind, lemma, number, genders)]`` readings of word ``i``.

            The other words decline as ``categories`` nouns (``Bielsko-Biała``,
            ``Kobyla Wola``) or as adjectives agreeing with the head; a word
            that is both declines as the adjective when the noun declines
            like one anyway (``Nowe Miasto`` -> ``Nowym Mieście``, not the
            town ``Nowe`` -> ``Nowem``), else as the noun (``Wola`` ->
            ``Woli``, not the adjective ``woli`` -> ``wolej``). Other nouns
            are used for words that are not adjectives (``Miasto``) but not
            for adjectives that do not agree (``Nowy`` with the feminine
            ``Ostrów``). Always in the number of the head, except proper
            nouns that only have the other one (``Czerwionka-Leszczyny``,
            ``Duszniki-Zdrój``).
            """
            in_number = [c for c in nouns[i] if c[2] == number]
            proper = bool(nouns[i]) and bool(nouns[i][0][4] & categories)
            agreeing = [
                ("adj", c[1], number, set(c[3]) & head_genders)
                for c in adjectives[i]
                if c[2] == number and set(c[3]) & head_genders
            ]
            as_nouns = [("subst", c[1], number, c[3]) for c in in_number]
            if agreeing and as_nouns and proper:
                genitives = [
                    {f for r in rs for f in self._forms_of(*r[:2], number, "gen", r[3])}
                    for rs in (agreeing, as_nouns)
                ]
                return agreeing if genitives[0] & genitives[1] else as_nouns
            if agreeing:
                return agreeing
            if in_number and (proper or not adjectives[i]):
                return as_nouns
            if proper:
                return [("subst", c[1], c[2], c[3]) for c in nouns[i]]
            return []

        forms = set()
        # Each lexeme of the head separately, so that the adjectives agree
        # with it (``Ostrów`` is both masculine and feminine in SGJP).
        for _, lemma, _, genders, _ in sorted(c for c in nouns[head] if c[2] == number):
            readings = [
                [("subst", lemma, number, genders)]
                if i == head
                else declension(i, set(genders))
                for i in range(len(words))
            ]
            if not all(readings):
                continue
            for case in SGJP_CASES:
                options = [
                    sorted(
                        set().union(
                            *(self._forms_of(k, x, n, case, g) for k, x, n, g in r)
                        )
                    )
                    for r in readings
                ]
                for parts in itertools.product(*options):
                    forms.add("".join(parts) + tail)
        return forms

    def common_forms(self, forms):
        """The subset of ``forms`` (lowercase) that are also forms of ordinary
        words in SGJP (``górach`` from ``góra``, ``róże`` from ``róża``)."""
        found = set()
        for form, _, _, _, qualifiers in sgjp_entries(self._payload):
            word = form.lower()
            if word in forms and set(qualifiers.split("|")) & COMMON_CATEGORIES:
                found.add(word)
        return found


def inflect_sources(inflector, sources, categories):
    """``{form: rank}`` of the inflected forms of ``sources``; a form shared
    by several names keeps the lowest rank. Also returns the (lowercase)
    names that got at least one form."""
    inflected = {}
    covered = set()
    for name, rank in sources:
        forms = inflector.inflect(name, categories)
        forms = {f for f in forms if len(f) >= MIN_LENGTH and f.isalpha()}
        if forms:
            covered.add(name.lower())
        for form in forms:
            if rank < inflected.get(form, rank + 1):
                inflected[form] = rank
    return inflected, covered


def add_inflections(ranks, inflected, common_words, common_forms):
    """Add inflected forms (and their diacritics-free variants) to ``ranks``.

    Existing entries keep their rank — the base forms do not change. A form
    that is also a frequent ordinary word (one of the ``COMMON_WORD_RANK_LIMIT``
    most frequent in ``pl_common_words`` and, per SGJP, a form of a common
    word: ``górze``, ``kota``, ``mają``) is left to ``pl_common_words``, which
    ranks it by real frequency; giving it a town's or a name's top rank would
    only weaken passphrases.

    Returns ``(added, existing, common)``: the number of new entries and of
    the (form or variant) entries skipped for each reason.
    """
    new = {}
    existing, common = set(), set()
    for form, rank in sorted(inflected.items()):
        rank *= INFLECTED_RANK_FACTOR
        for variant in (form, strip_diacritics(form)):
            if variant in ranks:
                existing.add(variant)
                continue
            if (
                common_words.get(variant, COMMON_WORD_RANK_LIMIT + 1)
                <= COMMON_WORD_RANK_LIMIT
                and form in common_forms
            ):
                common.add(variant)
                continue
            if rank < new.get(variant, rank + 1):
                new[variant] = rank
    ranks.update(new)
    return len(new), len(existing), len(common)


def save(dictionary, ranks):
    # Sorted input: the trie does not depend on dict insertion order.
    trie = marisa_trie.RecordTrie("<I", ((w, (r,)) for w, r in sorted(ranks.items())))
    path = OUTPUT_DIR / f"{dictionary}.marisa"
    trie.save(str(path))
    print(f"{path.name}: {len(trie)} entries, {path.stat().st_size // 1024} KB")


def main():
    global CACHE_DIR
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="keep downloaded source files here and reuse them on the next run",
    )
    CACHE_DIR = parser.parse_args().cache_dir
    lists = read_lists(download())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    built = {}
    sources = {}
    for dictionary, upstream in DICTIONARIES.items():
        built[dictionary], sources[dictionary] = build_ranks(
            lists[source] for source in upstream
        )
    built["pl_places"], sources["pl_places"] = build_places(
        read_town_population(), read_places(), built["pl_common_words"]
    )
    words = {
        word
        for dictionary in INFLECTED_CATEGORIES
        for name, _ in sources[dictionary]
        for word in re.split(r"[\s-]+", name.lower())
    }
    inflector = Inflector(read_sgjp(), words)
    inflected = {}
    for dictionary, categories in INFLECTED_CATEGORIES.items():
        inflected[dictionary], covered = inflect_sources(
            inflector, sources[dictionary], categories
        )
        names = {name.lower() for name, _ in sources[dictionary]}
        multi = {name for name in names if re.search(r"[\s-]", name)}
        print(
            f"{dictionary}: {len(covered)}/{len(names)} names inflected "
            f"(multi-word: {len(covered & multi)}/{len(multi)})"
        )
    common_forms = inflector.common_forms(
        {form for forms in inflected.values() for form in forms}
    )
    for dictionary in INFLECTED_CATEGORIES:
        added, existing, common = add_inflections(
            built[dictionary],
            inflected[dictionary],
            built["pl_common_words"],
            common_forms,
        )
        print(
            f"{dictionary}: {added} inflected entries added, skipped "
            f"{existing} already present and {common} common words"
        )
    for dictionary, ranks in built.items():
        save(dictionary, ranks)


if __name__ == "__main__":
    main()
