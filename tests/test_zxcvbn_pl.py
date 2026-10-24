from contextlib import contextmanager

import pytest
from zxcvbn import matching, zxcvbn

import zxcvbn_pl


@contextmanager
def slowniki_zarejestrowane():
    przed = dict(matching.RANKED_DICTIONARIES)
    zxcvbn_pl.register()
    try:
        yield
    finally:
        matching.RANKED_DICTIONARIES.clear()
        matching.RANKED_DICTIONARIES.update(przed)


@pytest.fixture
def zarejestrowane():
    with slowniki_zarejestrowane():
        yield


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
        ("pl_places", "warszawa"),
        ("pl_places", "kraków"),
        ("pl_places", "krakow"),
        ("pl_places", "wrocław"),
        ("pl_places", "wroclaw"),
        ("pl_places", "poznań"),
        ("pl_places", "poznan"),
        ("pl_places", "zielonagóra"),
        ("pl_places", "zielonagora"),
        ("pl_places", "bielskobiała"),
        ("pl_places", "bielsko"),
        ("pl_places", "nowawies"),
        ("pl_places", "mokotów"),
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


def test_miasto_bez_polskich_znakow_ma_te_sama_pozycje():
    slownik = zxcvbn_pl.dictionaries()["pl_places"]
    assert slownik["krakow"] == slownik["kraków"]
    assert slownik["lodz"] == slownik["łódź"]
    assert slownik["zielonagora"] == slownik["zielonagóra"]


def test_wieksze_miasto_ma_nizsza_pozycje():
    slownik = zxcvbn_pl.dictionaries()["pl_places"]
    assert slownik["warszawa"] == 1
    assert slownik["warszawa"] < slownik["kraków"] < slownik["zielonagóra"]
    # Najpierw wszystkie miasta, potem wsie (wg liczby miejscowości o tej nazwie).
    assert slownik["zielonagóra"] < slownik["nowawieś"]


def test_nazwy_wieloczlonowe_tylko_sklejone():
    slownik = zxcvbn_pl.dictionaries()["pl_places"]
    assert "zielona góra" not in slownik
    assert "bielsko-biała" not in slownik
    # Człon nazwy miasta dostaje pozycję miasta...
    assert slownik["bielsko"] == slownik["bielskobiała"]
    # ...chyba że to pospolite słowo — wtedy nie dostaje pozycji miasta.
    assert "zielona" in zxcvbn_pl.dictionaries()["pl_common_words"]
    assert slownik.get("zielona", 10**9) > slownik["zielonagóra"]


def test_dopisek_kolo_miejscowosci_jest_pomijany():
    # W wykazie jest tylko "Osiedle Zarzeczan k. Łazów" (i "k. Stacji").
    assert "osiedlezarzeczan" in zxcvbn_pl.dictionaries()["pl_places"]


@pytest.mark.parametrize(
    "haslo",
    ["Warszawa2024!", "Wroclaw1990", "Poznań2023!", "ZielonaGora2020"],
)
def test_miasto_z_dopiskiem_obniza_ocene(haslo):
    przed = zxcvbn(haslo)["score"]
    with slowniki_zarejestrowane():
        wynik = zxcvbn(haslo)
    assert wynik["score"] < przed
    assert "pl_places" in [m.get("dictionary_name") for m in wynik["sequence"]]


@pytest.mark.parametrize(
    "haslo",
    ["zielonaherbatazcytryna", "ptaszek-na-drzewie", "kot-pije-mleko-w-krakowie"],
)
def test_fraza_z_nazwa_miejscowosci_nadal_mocna(zarejestrowane, haslo):
    assert zxcvbn(haslo)["score"] == 4


@pytest.mark.parametrize(
    "nazwa,slowo",
    [
        # Miejscownik, dopełniacz, narzędnik, liczba mnoga miast (SGJP).
        ("pl_places", "wrocławiu"),
        ("pl_places", "wroclawiu"),
        ("pl_places", "krakowa"),
        ("pl_places", "krakowie"),
        ("pl_places", "gdańsku"),
        ("pl_places", "gdansku"),
        ("pl_places", "warszawie"),
        ("pl_places", "poznaniem"),
        ("pl_places", "tychach"),
        # Nazwy wieloczłonowe: oba człony w tym samym przypadku, sklejone.
        ("pl_places", "zielonejgórze"),
        ("pl_places", "zielonejgorze"),
        ("pl_places", "nowymsączu"),
        ("pl_places", "bielskubiałej"),
        ("pl_places", "tarnowskichgórach"),
        ("pl_places", "dusznikachzdroju"),
        ("pl_places", "nowymmieścienadpilicą"),
        # Wołacz i inne przypadki imion.
        ("pl_first_names", "katarzyno"),
        ("pl_first_names", "agnieszko"),
        ("pl_first_names", "tomaszu"),
        # Nazwiska (przymiotnikowe i rzeczownikowe).
        ("pl_last_names", "kowalskiego"),
        ("pl_last_names", "kowalskiej"),
        ("pl_last_names", "kowalskich"),
        ("pl_last_names", "nowakowi"),
    ],
)
def test_forma_odmieniona_w_slowniku(nazwa, slowo):
    assert slowo in zxcvbn_pl.dictionaries()[nazwa]


@pytest.mark.parametrize(
    "nazwa,podstawowa,odmieniona",
    [
        ("pl_places", "wrocław", "wrocławiu"),
        ("pl_places", "kraków", "krakowa"),
        ("pl_places", "zielonagóra", "zielonejgórze"),
        ("pl_first_names", "katarzyna", "katarzyno"),
        ("pl_last_names", "kowalski", "kowalskiego"),
    ],
)
def test_forma_odmieniona_ma_dwukrotna_pozycje_podstawowej(
    nazwa, podstawowa, odmieniona
):
    slownik = zxcvbn_pl.dictionaries()[nazwa]
    assert slownik[odmieniona] == 2 * slownik[podstawowa]


def test_odmiana_bez_polskich_znakow_ma_te_sama_pozycje():
    slownik = zxcvbn_pl.dictionaries()["pl_places"]
    assert slownik["wroclawiu"] == slownik["wrocławiu"]
    assert slownik["zielonejgorze"] == slownik["zielonejgórze"]


def test_forma_podstawowa_zachowuje_pozycje():
    # Odmiany innych nazw nie nadpisują wpisów, które już są w słowniku.
    assert zxcvbn_pl.dictionaries()["pl_places"]["warszawa"] == 1
    assert zxcvbn_pl.dictionaries()["pl_last_names"]["nowak"] == 1


@pytest.mark.parametrize(
    "nazwa,slowo",
    [
        # Częste zwykłe słowa zostają w pl_common_words, nie dostają pozycji
        # miasta Góra, miejscowości Dobra ani nazwiska Kot.
        ("pl_places", "górze"),
        ("pl_places", "dobrej"),
        ("pl_last_names", "kota"),
        ("pl_first_names", "nadzieję"),
    ],
)
def test_czeste_zwykle_slowa_nie_dostaja_pozycji_nazwy(nazwa, slowo):
    assert slowo not in zxcvbn_pl.dictionaries()[nazwa]
    assert slowo in zxcvbn_pl.dictionaries()["pl_common_words"]


@pytest.mark.parametrize(
    "haslo,slownik",
    [
        ("Wroclawiu2025!!", "pl_places"),
        ("Krakowie2024!!!", "pl_places"),
        ("Gdańsku12345678", "pl_places"),
        ("ZielonejGorze2020", "pl_places"),
        ("Katarzyno1985!", "pl_first_names"),
        ("Kowalskiego1990", "pl_last_names"),
    ],
)
def test_forma_odmieniona_obniza_ocene(haslo, slownik):
    przed = zxcvbn(haslo)["score"]
    with slowniki_zarejestrowane():
        wynik = zxcvbn(haslo)
    assert wynik["score"] < przed
    assert wynik["score"] <= 3
    # Odmiana jest w tym samym słowniku co forma podstawowa.
    assert slownik in [m.get("dictionary_name") for m in wynik["sequence"]]


@pytest.mark.parametrize(
    "haslo",
    [
        "wrzos-kaktus-lipa-7",
        "dluga-fraza-hasla-testowego",
        "ala ma kota i psa",
        "ŻółtaŁódźPłyniePoWiśle",
        "mostek-zebra-1987-pliszka",
        "kot1-pies2-kot3-mysz4",
        "ptaszek-na-drzewie-gra",
        "zielonaherbatazcytryna",
        "przykladowska-zofia-zielony-rower",
    ],
)
def test_frazy_nadal_mocne(zarejestrowane, haslo):
    assert zxcvbn(haslo)["score"] >= 3
