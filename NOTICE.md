# Data sources and licenses

The code of zxcvbn-pl is licensed under the MIT License (see `LICENSE`).
The dictionaries in `src/zxcvbn_pl/data/*.marisa` are derived from the
[`@zxcvbn-ts/language-pl`](https://github.com/zxcvbn-ts/zxcvbn/tree/master/packages/languages/pl)
npm package, version 4.1.1 (MIT), and carry the licenses of their sources:

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
