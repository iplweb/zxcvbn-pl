# Changelog

## 0.2.0 — unreleased

- New `pl_places` dictionary: Polish place names from the official list of
  place names (Wykaz urzędowych nazw miejscowości i ich części, MSWiA, state
  as of 1 Jan 2019, CC0 1.0). Towns come first, ordered by population (GUS
  Local Data Bank, 31 Dec 2025, CC BY 4.0), then all other locality names by
  how many localities share the name. Multi-word names are glued
  (`zielonagora`); words of town names that are not common words are added
  separately (`bielsko`). Passwords such as `Warszawa2024!` or
  `ZielonaGora2020` now get a lower score.
- `scripts/build_dictionaries.py`: checksum-verified download of the new
  sources, `--cache-dir` option, retries on HTTP 429 from the GUS API.

## 0.1.0 — 2026-10-24

- First release: `pl_common_words`, `pl_first_names` and `pl_last_names`
  dictionaries built from `@zxcvbn-ts/language-pl` 4.1.1, with
  diacritics-free variants; `zxcvbn_pl.register()`.
