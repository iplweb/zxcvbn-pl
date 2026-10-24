# zxcvbn-pl

[![PyPI](https://img.shields.io/pypi/v/zxcvbn-pl.svg)](https://pypi.org/project/zxcvbn-pl/)
[![CI](https://github.com/iplweb/zxcvbn-pl/actions/workflows/ci.yml/badge.svg)](https://github.com/iplweb/zxcvbn-pl/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Polskie słowniki dla [zxcvbn](https://github.com/dwolfhub/zxcvbn-python)
(port w Pythonie) — pospolite słowa, imiona i nazwiska.

*Polish dictionaries for the Python port of zxcvbn — common words, first
names and last names. [English below.](#english)*

---

## 🇵🇱 Po polsku

### Po co

zxcvbn szacuje, ile prób potrzeba do odgadnięcia hasła, rozpoznając w nim
słowa ze słowników, powtórzenia, sekwencje, układy klawiatury i daty. Ma
jednak **tylko angielskie słowniki** — polskie słowo to dla niego losowe
litery. Przez to hasła łatwe do zgadnięcia dla każdego, kto ma polską listę
słów, dostają najwyższą ocenę:

| Hasło | zxcvbn | zxcvbn + zxcvbn-pl |
|---|---|---|
| `słoneczko123456` | 4 | 2 |
| `pomidorowa123456` | 3 | 2 |
| `Katarzyna1985!` | 3 | 2 |
| `agnieszka.nowak1` | 4 | 3 |
| `Wojciechowski77` | 2 | 1 |
| `ptaszek-na-drzewie` | 4 | 4 |
| `zielonaherbatazcytryna` | 4 | 4 |

Frazy z kilku słów nadal są oceniane wysoko — tak jak zaleca NIST
SP 800-63B. Spada ocena haseł z jednego pospolitego słowa, imienia lub
nazwiska z dopiskiem. Efekt jest umiarkowany: słowa spoza ok. 50 tys.
najczęstszych (np. `kaczuszka2000!!`) nadal są dla zxcvbn losowymi literami.

Port zxcvbn w JavaScripcie (zxcvbn-ts) ma pakiety językowe; port w Pythonie
— nie. Ten pakiet wypełnia tę lukę danymi z `@zxcvbn-ts/language-pl`.

### Instalacja i użycie

```bash
pip install zxcvbn-pl
```

```python
import zxcvbn_pl
from zxcvbn import zxcvbn

zxcvbn_pl.register()  # raz, np. przy starcie aplikacji; wielokrotne wywołanie nic nie psuje

wynik = zxcvbn("słoneczko123456")
wynik["score"]  # 2
[m.get("dictionary_name") for m in wynik["sequence"]]
# ['pl_common_words', 'passwords']
```

`register()` dokłada trzy słowniki do globalnego rejestru zxcvbn
(`zxcvbn.matching.RANKED_DICTIONARIES`), więc działa dla każdego kolejnego
wywołania `zxcvbn()` w procesie:

| Nazwa (`dictionary_name`) | Zawartość |
|---|---|
| `pl_common_words` | ok. 52 tys. najczęstszych słów (napisy filmowe) |
| `pl_first_names` | imiona z rejestru PESEL (≥ 200 osób) |
| `pl_last_names` | nazwiska z rejestru PESEL (≥ 200 osób) |

Każde słowo z polskimi znakami jest też w wariancie bez nich (`żółw` →
`zolw`) z tą samą pozycją. Pomijane są wpisy krótsze niż 3 znaki.

Słowniki to indeksy [marisa-trie](https://github.com/pytries/marisa-trie)
czytane przez mmap (~1 MB na dysku, znikomy narzut RAM).

### Uwaga o wątkach

zxcvbn trzyma słowniki — także `user_inputs` przekazane do `zxcvbn()` —
w globalnym słowniku modułu. `register()` jest bezpieczne, ale jeśli
wywołujesz `zxcvbn(..., user_inputs=...)` z wielu wątków, owiń wywołanie
blokadą (to ograniczenie samego zxcvbn, nie tego pakietu).

### Dane i licencje

Kod: MIT. Dane pochodzą z `@zxcvbn-ts/language-pl` i mają własne licencje —
szczegóły w [NOTICE.md](NOTICE.md):

- pospolite słowa: OPUS OpenSubtitles 2024 — **ODC-BY** (wymaga podania źródła),
- imiona i nazwiska: rejestr PESEL, dane.gov.pl — **CC0 1.0**.

Odbudowa słowników (deterministyczna, z weryfikacją sha512 paczki npm):

```bash
uv run python scripts/build_dictionaries.py
```

---

## English

zxcvbn ships with English dictionaries only, so Polish words look like random
letters to it and passwords such as `słoneczko123456` or `Katarzyna1985!`
get the top score. `zxcvbn-pl` adds Polish common words, first names and last
names (plus diacritics-free variants) to the Python port of zxcvbn:

```python
import zxcvbn_pl
from zxcvbn import zxcvbn

zxcvbn_pl.register()
zxcvbn("słoneczko123456")["score"]  # 2 instead of 4
```

`register()` is idempotent and adds three dictionaries (`pl_common_words`,
`pl_first_names`, `pl_last_names`) to zxcvbn's global
`zxcvbn.matching.RANKED_DICTIONARIES`. Multi-word passphrases still score
high, in line with NIST SP 800-63B.

The data comes from the `@zxcvbn-ts/language-pl` npm package: common words
from OPUS OpenSubtitles 2024 (ODC-BY), first and last names from the Polish
PESEL registry published on dane.gov.pl (CC0 1.0). See [NOTICE.md](NOTICE.md).
The code is MIT-licensed.
