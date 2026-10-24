"""Polish dictionaries for zxcvbn (the Python port).

zxcvbn ships English dictionaries only, so to zxcvbn a Polish word looks like
random letters and passwords such as ``słoneczko123456`` or
``Katarzyna1985!`` get the top score. This package adds Polish common words,
first names, last names and place names (with diacritics-free variants) to
zxcvbn::

    import zxcvbn_pl
    from zxcvbn import zxcvbn

    zxcvbn_pl.register()
    zxcvbn("słoneczko123456")["score"]  # 2 instead of 4

The dictionaries are marisa-trie indices read via mmap (no big RAM cost).
"""

import threading
from pathlib import Path

import marisa_trie

__all__ = ["DICTIONARY_NAMES", "MarisaRankedDictionary", "dictionaries", "register"]
__version__ = "0.2.0"

DATA_DIR = Path(__file__).parent / "data"

#: Names under which the dictionaries are registered in zxcvbn — they show up
#: as ``dictionary_name`` in zxcvbn's match sequence.
DICTIONARY_NAMES = (
    "pl_common_words",
    "pl_first_names",
    "pl_last_names",
    "pl_places",
)

_lock = threading.Lock()
_dictionaries = None


class MarisaRankedDictionary:
    """Read-only ``word -> rank`` mapping over a marisa-trie index.

    zxcvbn only needs ``word in d`` and ``d[word]`` from a ranked dictionary,
    so this is a drop-in replacement for the plain dicts it builds itself.
    """

    def __init__(self, path):
        self._trie = marisa_trie.RecordTrie("<I").mmap(str(path))

    def __contains__(self, word):
        return word in self._trie

    def __getitem__(self, word):
        return self._trie[word][0][0]

    def __len__(self):
        return len(self._trie)

    def get(self, word, default=None):
        return self[word] if word in self else default


def dictionaries():
    """Return ``{name: MarisaRankedDictionary}`` for all Polish dictionaries."""
    global _dictionaries
    with _lock:
        if _dictionaries is None:
            _dictionaries = {
                name: MarisaRankedDictionary(DATA_DIR / f"{name}.marisa")
                for name in DICTIONARY_NAMES
            }
        return _dictionaries


def register():
    """Add the Polish dictionaries to zxcvbn. Safe to call many times.

    zxcvbn keeps its ranked dictionaries in a module-level dict, so this
    affects every later ``zxcvbn()`` call in the process.
    """
    from zxcvbn import matching

    matching.RANKED_DICTIONARIES.update(dictionaries())
