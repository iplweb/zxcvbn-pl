"""Build the Polish zxcvbn dictionaries shipped in ``src/zxcvbn_pl/data``.

Source data: the ``@zxcvbn-ts/language-pl`` npm package (pinned version,
verified against the registry's sha512 integrity). Each upstream list is
ordered by frequency; the position becomes the zxcvbn rank. Male and female
lists are merged (lower rank wins). For every word with Polish diacritics a
variant without them is added with the same rank (``żółw`` -> ``zolw``) —
that is how such words are usually typed in passwords.

Run from the repository root (needs only the runtime dependency)::

    uv run python scripts/build_dictionaries.py

The output is deterministic: the same upstream version gives byte-identical
``.marisa`` files.
"""

import base64
import hashlib
import io
import json
import tarfile
import unicodedata
import urllib.request
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

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "zxcvbn_pl" / "data"


def strip_diacritics(word):
    word = word.replace("ł", "l")
    word = unicodedata.normalize("NFKD", word)
    return "".join(c for c in word if not unicodedata.combining(c))


def download():
    with urllib.request.urlopen(UPSTREAM_URL, timeout=60) as response:
        payload = response.read()
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
            word = word.strip().lower()
            if len(word) < MIN_LENGTH or not word.isalpha():
                continue
            for variant in (word, strip_diacritics(word)):
                if position < ranks.get(variant, position + 1):
                    ranks[variant] = position
    return ranks


def main():
    lists = read_lists(download())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for dictionary, sources in DICTIONARIES.items():
        ranks = build_ranks(lists[source] for source in sources)
        trie = marisa_trie.RecordTrie("<I", ((w, (r,)) for w, r in ranks.items()))
        path = OUTPUT_DIR / f"{dictionary}.marisa"
        trie.save(str(path))
        print(f"{path.name}: {len(trie)} entries, {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
