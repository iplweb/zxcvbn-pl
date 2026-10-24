# Data sources and licenses

The code of zxcvbn-pl is licensed under the MIT License (see `LICENSE`).
The dictionaries in `src/zxcvbn_pl/data/*.marisa` carry the licenses of
their sources. `pl_common_words`, `pl_first_names` and `pl_last_names` are
derived from the
[`@zxcvbn-ts/language-pl`](https://github.com/zxcvbn-ts/zxcvbn/tree/master/packages/languages/pl)
npm package, version 4.1.1 (MIT); `pl_places` is built from Polish public
data (see the last section).

## `pl_common_words.marisa`

Derived from OpenSubtitles via OPUS (`commonWords.json` in
`@zxcvbn-ts/language-pl`).

- Source dataset: OpenSubtitles 2024, https://opus.nlpl.eu/OpenSubtitles.php
- Provider: Helsinki-NLP / OPUS
- License: **ODC-BY** (Open Data Commons Attribution License),
  https://opendatacommons.org/licenses/by/
- Original data is attributed to subtitle contributors and rights holders
  (http://www.opensubtitles.org/).

This package contains a processed derivative: tokenized text, frequency
aggregation, normalization and filtering (by zxcvbn-ts), then lowercasing,
dropping entries shorter than 3 characters or containing non-letters, adding
diacritics-free variants and converting to a marisa-trie index (by
zxcvbn-pl). Any redistribution must retain this notice.

## `pl_first_names.marisa`, `pl_last_names.marisa`

Derived from the lists of first names and last names in the Polish PESEL
registry, published by the Ministry of Digital Affairs on dane.gov.pl:

- Lista imion występujących w rejestrze PESEL,
  https://dane.gov.pl/pl/dataset/1667 — **CC0 1.0**
- Nazwiska występujące w rejestrze PESEL,
  https://dane.gov.pl/pl/dataset/1681 — **CC0 1.0**

zxcvbn-ts keeps names with at least 200 occurrences; zxcvbn-pl merges the
male and female lists, lowercases them and adds diacritics-free variants.

## `pl_places.marisa`

Polish place names, built by `scripts/build_dictionaries.py` directly from
public data (not from `@zxcvbn-ts/language-pl`):

- **Wykaz urzędowych nazw miejscowości i ich części** (the official list of
  names of Polish localities and their parts, with their TERYT SIMC
  identifiers), the annex to the notice of the Minister of the Interior and
  Administration of 17 October 2019 (Dz. U. 2019 poz. 2360), state as of
  1 January 2019. Published by the Ministry of the Interior and
  Administration on dane.gov.pl: https://dane.gov.pl/pl/dataset/188 —
  **CC0 1.0** (file `wykaz_stan_na_1.1.2019.xlsx`, resource 60795, published
  18 September 2024, sha256 pinned in the build script). As part of an
  official act it is also excluded from copyright (art. 4 of the Polish
  Copyright Act).
- **Population of towns** as of 31 December 2025 — Statistics Poland (GUS),
  Bank Danych Lokalnych (Local Data Bank), variable 72305, via the BDL API:
  https://api.stat.gov.pl/Home/BdlApi — **CC BY 4.0**,
  https://creativecommons.org/licenses/by/4.0/. Source: Główny Urząd
  Statystyczny, Bank Danych Lokalnych. Used to list the towns (as of 2026)
  and to order them by population; the population figures themselves are not
  shipped.

Processing (by zxcvbn-pl): towns ranked by population, then all other
locality names ranked by how many localities share the name; names
lowercased, multi-word and hyphenated names glued together (`zielonagora`),
separate words of town names added, entries shorter than 3 characters or
containing non-letters dropped, diacritics-free variants added, converted to
a marisa-trie index. Names changed after 1 January 2019 (other than town
names) are not reflected.
