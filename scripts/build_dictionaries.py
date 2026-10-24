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

For every word with Polish diacritics a variant without them is added with
the same rank (``żółw`` -> ``zolw``) — that is how such words are usually
typed in passwords.

Run from the repository root (needs only the runtime dependency)::

    uv run python scripts/build_dictionaries.py [--cache-dir DIR]

It downloads ~7 MB and makes ~40 requests to the GUS BDL API, which limits
anonymous clients (HTTP 429 is retried); ``--cache-dir`` avoids re-downloading
on repeated builds.

The output is deterministic: the same upstream data gives byte-identical
``.marisa`` files.
"""

import argparse
import base64
import hashlib
import io
import json
import re
import tarfile
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
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
    ranks = {}
    for words in upstream_lists:
        for position, word in enumerate(words, start=1):
            add_word(ranks, word.strip().lower(), position)
    return ranks


def add_word(ranks, word, rank):
    """Add ``word`` and its diacritics-free variant, keeping the lower rank."""
    if len(word) < MIN_LENGTH or not word.isalpha():
        return
    for variant in (word, strip_diacritics(word)):
        if rank < ranks.get(variant, rank + 1):
            ranks[variant] = rank


def split_place_name(name):
    """``"Bielsko-Biała"`` -> ``["bielsko", "biała"]``.

    Drops the disambiguating ``k. <other place>`` ("near ...") suffix that a
    few names in the official list carry: ``"Brzezie k. Sulechowa"``.
    """
    name = re.sub(r"\s+k\.\s.*$", "", name.strip())
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
    """
    ranks = {}
    ordered_towns = sorted(towns, key=lambda town: (-town[1], town[0]))
    for position, (name, _) in enumerate(ordered_towns, start=1):
        parts = split_place_name(name)
        add_word(ranks, "".join(parts), position)
        if len(parts) > 1:
            for part in parts:
                if part not in common_words:
                    add_word(ranks, part, position)
    counts = Counter("".join(split_place_name(name)) for name in places)
    ordered_places = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    for position, (word, _) in enumerate(ordered_places, start=len(towns) + 1):
        add_word(ranks, word, position)
    return ranks


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
    for dictionary, sources in DICTIONARIES.items():
        built[dictionary] = build_ranks(lists[source] for source in sources)
        save(dictionary, built[dictionary])
    places = build_places(
        read_town_population(), read_places(), built["pl_common_words"]
    )
    save("pl_places", places)


if __name__ == "__main__":
    main()
