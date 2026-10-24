# Data sources and licenses

The code of zxcvbn-pl is licensed under the MIT License (see `LICENSE`).
The dictionaries in `src/zxcvbn_pl/data/*.marisa` carry the licenses of
their sources. `pl_common_words`, `pl_first_names` and `pl_last_names` are
derived from the
[`@zxcvbn-ts/language-pl`](https://github.com/zxcvbn-ts/zxcvbn/tree/master/packages/languages/pl)
npm package, version 4.1.1 (MIT); `pl_places` is built from Polish public
data (see the section on `pl_places`). The inflected forms added to
`pl_first_names`, `pl_last_names` and `pl_places` come from SGJP (see the
last section, BSD-2-Clause).

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

## Inflected forms (SGJP)

Since version 0.3.0 `pl_first_names.marisa`, `pl_last_names.marisa` and
`pl_places.marisa` also contain the inflected forms (all cases, singular and
plural) of the names they hold — `wrocławiu`, `krakowa`, `katarzyno`,
`kowalskiego`, `zielonejgórze` — taken from:

- **SGJP — Słownik gramatyczny języka polskiego** (Grammatical Dictionary of
  Polish) by Marcin Woliński, Zbigniew Bronk, Włodzimierz Gruszczyński,
  Witold Kieraś, Zygmunt Saloni, Danuta Skowrońska and Robert Wołosz,
  https://sgjp.pl/ — edition `pl.sgjp.sgjp-2026.06.29`, the Morfeusz 2
  "tab" export `sgjp-20260628.tab.gz` from https://morfeusz.sgjp.pl/download/
  (sha256 pinned in the build script; the same edition that the
  `polish-inflection-data` 2026.6.28 package is built from).
- License: **BSD-2-Clause**, https://morfeusz.sgjp.pl/doc/license/en

Processing (by zxcvbn-pl): only lexemes marked in SGJP as proper names
(first names, surnames, geographic names and parts of geographic names) are
used; multi-word place names are declined word by word and glued
(`zielonejgórze`); forms lowercased, entries shorter than 3 characters or
containing non-letters dropped, forms that are frequent ordinary words left
out, diacritics-free variants added, converted to a marisa-trie index.

The SGJP license requires that redistributions in binary form reproduce the
copyright notice, the conditions and the disclaimer below. The verbatim text,
as shipped in the header of the SGJP file, is also in `LICENSE.sgjp` (both
files are included in the wheel and the sdist):

```
Copyright © 2007–2026 Marcin Woliński, Zbigniew Bronk, Włodzimierz Gruszczyński, Witold Kieraś, Zygmunt Saloni, Danuta Skowrońska, Robert Wołosz

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY COPYRIGHT HOLDERS “AS IS” AND ANY EXPRESS
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL COPYRIGHT HOLDERS OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.
```
