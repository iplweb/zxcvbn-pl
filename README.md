# zxcvbn-pl

[![PyPI](https://img.shields.io/pypi/v/zxcvbn-pl.svg)](https://pypi.org/project/zxcvbn-pl/)
[![CI](https://github.com/iplweb/zxcvbn-pl/actions/workflows/ci.yml/badge.svg)](https://github.com/iplweb/zxcvbn-pl/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Polskie słowniki dla [zxcvbn](https://github.com/dwolfhub/zxcvbn-python)
(port w Pythonie) — pospolite słowa, imiona, nazwiska i nazwy miejscowości.

*Polish dictionaries for the Python port of zxcvbn — common words, first
names, last names and place names. [English below.](#english)*

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
| `Warszawa2024!` | 3 | 2 |
| `Poznań2023!` | 4 | 2 |
| `ZielonaGora2020` | 4 | 1 |
| `Częstochowa77` | 4 | 1 |
| `ptaszek-na-drzewie` | 4 | 4 |
| `zielonaherbatazcytryna` | 4 | 4 |

Frazy z kilku słów nadal są oceniane wysoko — tak jak zaleca NIST
SP 800-63B. Spada ocena haseł z jednego pospolitego słowa, imienia,
nazwiska lub nazwy miejscowości z dopiskiem. Efekt jest umiarkowany: słowa spoza ok. 50 tys.
najczęstszych (np. `kaczuszka2000!!`) nadal są dla zxcvbn losowymi literami.

### Formy odmienione (od 0.3.0)

zxcvbn rozpoznaje tylko słowo w formie ze słownika — końcówkę fleksyjną
liczy jak losowe litery. Dlatego `Wrocław2025` dostawał ocenę 1, ale
`Wrocławiu2025` — 3, a `Krakowie2024!!!` — 4. Od wersji 0.3.0 słowniki
imion, nazwisk i miejscowości zawierają też formy odmienione (wszystkie
przypadki, liczba pojedyncza i mnoga) ze Słownika gramatycznego języka
polskiego (SGJP), również bez polskich znaków. Nazwy wieloczłonowe są
odmieniane człon po członie i sklejane (`zielonejgórze`, `nowymsączu`,
`bielskubiałej`).

Oceny zmierzone (zxcvbn 4.5.0):

| Hasło | zxcvbn | + zxcvbn-pl 0.2.0 | + zxcvbn-pl 0.3.0 |
|---|---|---|---|
| `Wrocławiu2025` | 4 | 3 | 1 |
| `Gdańsku12345678` | 3 | 3 | 1 |
| `Kowalskiego1990` | 3 | 3 | 1 |
| `Warszawie2024!` | 4 | 4 | 2 |
| `ZielonejGorze2020` | 4 | 4 | 2 |
| `Katarzyno1985!` | 4 | 3 | 2 |
| `Nowakowi2024!` | 4 | 4 | 2 |
| `Wroclawiu2025!!` | 4 | 4 | 3 |
| `Krakowie2024!!!` | 4 | 4 | 3 |
| `zKrakowa1990abc` | 4 | 4 | 4 |
| `kot-pije-mleko-w-krakowie` | 4 | 4 | 4 |
| `ptaszek-na-drzewie` | 4 | 4 | 4 |
| `zielonaherbatazcytryna` | 4 | 4 | 4 |

Forma odmieniona trafia do słownika swojej formy podstawowej (to samo
`dictionary_name`) i dostaje jej dwukrotną pozycję (np. `kraków` = 2,
`krakowa` = 4). Wpisy, które już były w słowniku, zachowują swoją pozycję.
Formy będące jednocześnie częstymi zwykłymi słowami (`górze`, `kota`) zostają
tylko w `pl_common_words`, który ocenia je wg rzeczywistej częstości.

Port zxcvbn w JavaScripcie (zxcvbn-ts) ma pakiety językowe; port w Pythonie
— nie. Ten pakiet wypełnia tę lukę danymi z `@zxcvbn-ts/language-pl`
i dokłada nazwy miejscowości z urzędowego wykazu (TERYT).

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

`register()` dokłada cztery słowniki do globalnego rejestru zxcvbn
(`zxcvbn.matching.RANKED_DICTIONARIES`), więc działa dla każdego kolejnego
wywołania `zxcvbn()` w procesie:

| Nazwa (`dictionary_name`) | Zawartość |
|---|---|
| `pl_common_words` | ok. 52 tys. najczęstszych słów (napisy filmowe) |
| `pl_first_names` | imiona z rejestru PESEL (≥ 200 osób) i ich formy odmienione |
| `pl_last_names` | nazwiska z rejestru PESEL (≥ 200 osób) i ich formy odmienione |
| `pl_places` | nazwy miejscowości z urzędowego wykazu: najpierw miasta wg liczby ludności, potem pozostałe wg liczby miejscowości o tej nazwie; z formami odmienionymi |

Nazwy wieloczłonowe są sklejone (`Zielona Góra` → `zielonagora`); człony
nazw miast, które nie są pospolitymi słowami, są też osobno (`bielsko`,
`gorzow`).

Każde słowo z polskimi znakami jest też w wariancie bez nich (`żółw` →
`zolw`) z tą samą pozycją. Pomijane są wpisy krótsze niż 3 znaki.

Słowniki to indeksy [marisa-trie](https://github.com/pytries/marisa-trie)
czytane przez mmap (~3,9 MB na dysku, znikomy narzut RAM).

### Uwaga o wątkach

zxcvbn trzyma słowniki — także `user_inputs` przekazane do `zxcvbn()` —
w globalnym słowniku modułu. `register()` jest bezpieczne, ale jeśli
wywołujesz `zxcvbn(..., user_inputs=...)` z wielu wątków, owiń wywołanie
blokadą (to ograniczenie samego zxcvbn, nie tego pakietu).

### Dane i licencje

Kod: MIT. Dane pochodzą z `@zxcvbn-ts/language-pl` i mają własne licencje —
szczegóły w [NOTICE.md](NOTICE.md):

- pospolite słowa: OPUS OpenSubtitles 2024 — **ODC-BY** (wymaga podania źródła),
- imiona i nazwiska: rejestr PESEL, dane.gov.pl — **CC0 1.0**,
- nazwy miejscowości: Wykaz urzędowych nazw miejscowości i ich części
  (MSWiA, stan na 1.01.2019), dane.gov.pl — **CC0 1.0**; kolejność miast:
  liczba ludności wg GUS, Bank Danych Lokalnych (stan na 31.12.2025) —
  **CC BY 4.0**,
- formy odmienione imion, nazwisk i nazw miejscowości: Słownik gramatyczny
  języka polskiego (SGJP, M. Woliński, Z. Bronk, W. Gruszczyński,
  W. Kieraś, Z. Saloni, D. Skowrońska, R. Wołosz), wydanie 2026.06.29 —
  **BSD-2-Clause** (pełny tekst w [NOTICE.md](NOTICE.md) i `LICENSE.sgjp`).

Odbudowa słowników (deterministyczna, z weryfikacją sum kontrolnych
pobieranych danych):

```bash
uv run python scripts/build_dictionaries.py
```

---

## English

zxcvbn ships with English dictionaries only, so Polish words look like random
letters to it and passwords such as `słoneczko123456` or `Katarzyna1985!`
get the top score. `zxcvbn-pl` adds Polish common words, first names, last
names and place names (plus diacritics-free variants) to the Python port of
zxcvbn:

```python
import zxcvbn_pl
from zxcvbn import zxcvbn

zxcvbn_pl.register()
zxcvbn("słoneczko123456")["score"]  # 2 instead of 4
```

`register()` is idempotent and adds four dictionaries (`pl_common_words`,
`pl_first_names`, `pl_last_names`, `pl_places`) to zxcvbn's global
`zxcvbn.matching.RANKED_DICTIONARIES`. Multi-word passphrases still score
high, in line with NIST SP 800-63B.

| Password | zxcvbn | zxcvbn + zxcvbn-pl |
|---|---|---|
| `słoneczko123456` | 4 | 2 |
| `Katarzyna1985!` | 3 | 2 |
| `Warszawa2024!` | 3 | 2 |
| `Poznań2023!` | 4 | 2 |
| `ZielonaGora2020` | 4 | 1 |
| `zielonaherbatazcytryna` | 4 | 4 |

`pl_places` holds the names of Polish localities from the official list of
place names (towns first, by population; then the other names by how many
localities share them). Multi-word names are glued (`zielonagora`).

**Inflected forms (since 0.3.0).** zxcvbn only recognizes the dictionary
form of a word and counts an inflectional ending as random letters, so
`Wrocławiu2025` ("in Wrocław") scored 3 and `Krakowie2024!!!` 4. The first
name, last name and place dictionaries now also hold all case forms,
singular and plural, of their names (`wrocławiu`, `krakowa`, `katarzyno`,
`kowalskiego`, multi-word `zielonejgorze`) from SGJP, the grammatical
dictionary of Polish, with diacritics-free variants. A form is added to the
dictionary of its base form (same `dictionary_name`) with twice its rank;
existing entries keep their rank; forms that are also frequent ordinary words
are left to `pl_common_words`. Measured scores (zxcvbn 4.5.0):

| Password | zxcvbn | + zxcvbn-pl 0.2.0 | + zxcvbn-pl 0.3.0 |
|---|---|---|---|
| `Wrocławiu2025` | 4 | 3 | 1 |
| `Gdańsku12345678` | 3 | 3 | 1 |
| `Kowalskiego1990` | 3 | 3 | 1 |
| `Katarzyno1985!` | 4 | 3 | 2 |
| `Wroclawiu2025!!` | 4 | 4 | 3 |
| `Krakowie2024!!!` | 4 | 4 | 3 |
| `kot-pije-mleko-w-krakowie` | 4 | 4 | 4 |
| `zielonaherbatazcytryna` | 4 | 4 | 4 |

Common words, first and last names come from the `@zxcvbn-ts/language-pl`
npm package: common words from OPUS OpenSubtitles 2024 (ODC-BY), first and
last names from the Polish PESEL registry published on dane.gov.pl (CC0 1.0).
Place names come from the official list of Polish place names (Ministry of
the Interior and Administration, state as of 1 Jan 2019, dane.gov.pl,
CC0 1.0), towns are ordered by population from Statistics Poland's Local Data
Bank (31 Dec 2025, CC BY 4.0). Inflected forms come from SGJP — Słownik
gramatyczny języka polskiego by M. Woliński, Z. Bronk, W. Gruszczyński,
W. Kieraś, Z. Saloni, D. Skowrońska and R. Wołosz, edition 2026.06.29
(BSD-2-Clause; full text in `LICENSE.sgjp`). See [NOTICE.md](NOTICE.md).
The code is MIT-licensed.
