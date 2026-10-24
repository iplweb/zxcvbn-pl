# Changelog

## 0.3.0 — unreleased

- Inflected forms of names: `pl_first_names`, `pl_last_names` and
  `pl_places` now also hold all cases, singular and plural, of their names
  (`wrocławiu`, `krakowa`, `katarzyno`, `kowalskiego`), with diacritics-free
  variants, from SGJP — the grammatical dictionary of Polish (edition
  2026.06.29, BSD-2-Clause, see `NOTICE.md` and `LICENSE.sgjp`). Multi-word
  place names are declined word by word and glued (`zielonejgórze`,
  `nowymsączu`, `bielskubiałej`). Forms stay in the dictionary of their base
  form, so `dictionary_name` does not change. Passwords such as
  `Wrocławiu2025` (3 -> 1), `Gdańsku12345678` (3 -> 1) or `Krakowie2024!!!`
  (4 -> 3) now get a lower score.
- An inflected form gets twice the rank of its base form; entries that were
  already in a dictionary keep their rank (base forms do not change). Forms
  that are also frequent ordinary words (`górze`, `kota`) are left to
  `pl_common_words`.
- The wheel grows from ~1.0 MB to ~3.2 MB (`pl_places.marisa` ~2.4 MB).
- `scripts/build_dictionaries.py`: checksum-verified download of SGJP;
  no new runtime or build dependencies.

## 0.2.0 — 2026-10-24

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
