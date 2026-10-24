import pytest
from zxcvbn import matching, zxcvbn

import zxcvbn_pl


@pytest.fixture
def zarejestrowane():
    przed = dict(matching.RANKED_DICTIONARIES)
    zxcvbn_pl.register()
    yield
    matching.RANKED_DICTIONARIES.clear()
    matching.RANKED_DICTIONARIES.update(przed)


def test_slowniki_maja_dane():
    slowniki = zxcvbn_pl.dictionaries()
    assert set(slowniki) == set(zxcvbn_pl.DICTIONARY_NAMES)
    assert all(len(slownik) > 1000 for slownik in slowniki.values())


@pytest.mark.parametrize(
    "nazwa,slowo",
    [
        ("pl_common_words", "kot"),
        ("pl_first_names", "katarzyna"),
        ("pl_last_names", "kowalski"),
        ("pl_last_names", "kowalska"),
    ],
)
def test_slowo_w_slowniku(nazwa, slowo):
    assert slowo in zxcvbn_pl.dictionaries()[nazwa]


def test_wariant_bez_polskich_znakow_ma_te_sama_pozycje():
    slownik = zxcvbn_pl.dictionaries()["pl_common_words"]
    assert slownik["zolw"] == slownik["żółw"]
    assert slownik["slonce"] == slownik["słońce"]


def test_czestsze_slowo_ma_nizsza_pozycje():
    slownik = zxcvbn_pl.dictionaries()["pl_common_words"]
    assert slownik["nie"] < slownik["kot"] < slownik["żółw"]


def test_brak_krotkich_i_nieliterowych_wpisow():
    slownik = zxcvbn_pl.dictionaries()["pl_common_words"]
    assert "na" not in slownik
    assert "xqzvw" not in slownik
    assert slownik.get("xqzvw") is None


def test_register_jest_idempotentne(zarejestrowane):
    zxcvbn_pl.register()
    for nazwa in zxcvbn_pl.DICTIONARY_NAMES:
        assert matching.RANKED_DICTIONARIES[nazwa] is zxcvbn_pl.dictionaries()[nazwa]


@pytest.mark.parametrize(
    "haslo,slownik",
    [
        ("słoneczko123456", "pl_common_words"),
        ("Katarzyna1985!", "pl_first_names"),
        ("Wojciechowski77", "pl_last_names"),
    ],
)
def test_polskie_slowa_obnizaja_ocene(zarejestrowane, haslo, slownik):
    wynik = zxcvbn(haslo)
    assert wynik["score"] <= 2
    assert slownik in [m.get("dictionary_name") for m in wynik["sequence"]]


def test_bez_rejestracji_zxcvbn_nie_zna_polskich_slow():
    assert zxcvbn("słoneczko123456")["score"] == 4


def test_fraza_z_kilku_slow_nadal_mocna(zarejestrowane):
    assert zxcvbn("zielonaherbatazcytryna")["score"] == 4
