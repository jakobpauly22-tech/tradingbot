"""Tiingo-Umrechnung, Stundenlimit, Wahl der Kursquelle und Börsenwert-Prüfung (offline)."""
import pandas as pd
import pytest

from tradingbot.daten.kursquellen import kursquelle, plausibel, yahoo_ticker
from tradingbot.daten.tiingo import TiingoClient, TiingoLimitErreicht, normalisieren


def test_tiingo_split_wie_yahoo():
    # Apple 7:1 am 09.06.2014 (echte Tiingo-Rohwerte); vor dem Split durch 7 teilen
    roh = [
        {"date": "2014-06-06T00:00:00.000Z", "open": 649.9, "high": 651.26, "low": 644.47, "close": 645.57, "volume": 12497800, "divCash": 0.0, "splitFactor": 1.0},
        {"date": "2014-06-09T00:00:00.000Z", "open": 92.7, "high": 93.88, "low": 91.75, "close": 93.7, "volume": 75415000, "divCash": 0.0, "splitFactor": 7.000007},
        {"date": "2014-08-07T00:00:00.000Z", "open": 94.9, "high": 95.0, "low": 94.0, "close": 94.48, "volume": 1, "divCash": 0.47, "splitFactor": 1.0},
    ]
    k = normalisieren(roh)
    assert k.loc["2014-06-06", "close"] == pytest.approx(645.57 / 7.000007)
    assert k.loc["2014-06-09", "close"] == pytest.approx(93.7) and k.loc["2014-06-09", "split"] == pytest.approx(7.000007)
    assert k.loc["2014-08-07", "dividende"] == pytest.approx(0.47) and k.loc["2014-06-06", "split"] == 0.0
    assert k.index.tz is None and list(k.columns) == ["open", "high", "low", "close", "volume", "dividende", "split"]


class _Uhr:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


class _Antwort:
    status_code = 200

    def json(self):
        return []


class _Sitzung:
    def __init__(self):
        self.aufrufe = []

    def get(self, url, params, headers, timeout):
        self.aufrufe.append((url, headers))
        return _Antwort()


def test_tiingo_stundenlimit_und_schluessel_im_header(tmp_path):
    uhr, sitzung = _Uhr(), _Sitzung()
    client = TiingoClient("geheim123", cache_wurzel=tmp_path, anfragen_pro_stunde=2, sitzung=sitzung, uhr=uhr, warten=False)
    client.historie("aaa")
    client.historie("bbb")
    assert "geheim123" not in sitzung.aufrufe[0][0] and sitzung.aufrufe[0][1]["Authorization"] == "Token geheim123"
    client.historie("aaa")                                       # aus dem Cache, kein Abruf
    with pytest.raises(TiingoLimitErreicht):
        client.historie("ccc")
    uhr.t += 3601                                                 # eine Stunde später wieder frei
    client.historie("ccc")
    assert len(sitzung.aufrufe) == 3


LISTE = pd.DataFrame({
    "ticker": ["MON", "MON", "SHLDQ", "SHLD"],
    "exchange": ["NYSE", "NASDAQ", "PINK", "NYSE"],
    "assetType": ["Stock", "Stock", "Stock", "ETF"],
    "priceCurrency": ["USD"] * 4,
    "startDate": pd.to_datetime(["2000-10-18", "2021-03-16", "2003-05-01", "2023-09-13"]),
    "endDate": pd.to_datetime(["2018-06-08", "2022-12-23", "2022-10-31", "2026-10-30"]),
})


def _zeile(ticker, cik, von, bis, frueher=None):
    return pd.Series({"ticker": ticker, "ticker_frueher": frueher, "cik": cik, "von": pd.Timestamp(von) if von else pd.NaT,
                      "bis": pd.Timestamp(bis) if bis else pd.NaT})


def test_kursquelle_heute_gelistet_und_vorzugsaktien():
    sec = {320193: ["AAPL"], 30554: ["CTA-PB", "CTA-PA"], 1067983: ["BRK-B", "BRK-A"]}
    assert kursquelle(_zeile("AAPL", 320193, "1982-11-30", None), sec, LISTE)["symbol"] == "AAPL"
    assert kursquelle(_zeile("BRK.B", 1067983, "2010-02-16", None), sec, LISTE)["symbol"] == "BRK-B"
    # nur Vorzugsaktien gelistet → keine yfinance-Quelle, Suche bei Tiingo
    assert kursquelle(_zeile("DD", 30554, None, "2017-09-01"), sec, LISTE)["quelle"] is None
    assert yahoo_ticker("BF.B") == "BF-B"


def test_kursquelle_tiingo_wiederverwendeter_ticker_und_insolvenz():
    monsanto = kursquelle(_zeile("MON", 1110783, None, "2018-06-07"), {}, LISTE)
    assert monsanto["quelle"] == "tiingo" and monsanto["symbol"] == "MON"   # Kursende passt zum Indexabgang
    sears = kursquelle(_zeile("SHLD", 1310067, None, "2012-12-21"), {}, LISTE)
    assert sears["symbol"] == "SHLDQ"                                       # nicht der heutige ETF mit Ticker SHLD


def test_plausibel_boersenwert_und_abdeckung():
    tage = pd.bdate_range("2012-01-02", "2012-12-31")
    kurse = pd.DataFrame({"close": 50.0}, index=tage)
    aktien = pd.Series([1e9], index=[pd.Timestamp("2011-12-31")])
    assert plausibel(kurse, aktien, None, "2013-01-01")["ok"]                       # 50 Mrd. USD
    assert not plausibel(kurse, aktien * 1e-3, None, "2013-01-01")["ok"]            # 50 Mio. USD: falsche Aktie?
    luecke = kurse.iloc[::3]
    assert "Werktage" in plausibel(luecke, aktien, None, "2013-01-01")["grund"]


# --- Wiederverwendete Ticker (Rückmeldung Jakob 02.11.2026) ---------------------------------------------------
# Kurszeitraum und Name: echte Tiingo-Werte vom 02.11.2026 (kursstatus.csv, Metadaten-Abruf); Mitgliedschaft aus
# dem Universum; die Kursreihen selbst sind künstlich (gleichbleibender Kurs an jedem Werktag).
SIEBEN_FAELLE = [
    # ticker, Mitglied bis, Tiingo erster/letzter Kurs, Tiingo-Name, bekannte Namen (Index, SEC heute und früher)
    ("CA", "2018-11-06", "2023-12-14", "2026-10-30", "XTRACKERS CALIFORNIA MUNICIPAL BOND ETF",
     ["CA Technologies", "CA, INC.", "COMPUTER ASSOCIATES INTERNATIONAL INC"]),
    ("CEG", "2012-03-13", "2022-02-02", "2026-10-30", "Constellation Energy Corporation", ["Constellation Energy Group"]),
    ("BEAM", "2014-05-01", "2020-02-06", "2026-10-30", "Beam Therapeutics Inc",
     ["Suntory Global Spirits", "Beam Suntory Inc.", "BEAM INC", "FORTUNE BRANDS INC"]),
    ("BRCM", "2016-02-01", "2016-01-04", "2016-01-29", "Broadcom Corp", ["Broadcom Corporation", "BROADCOM CORP"]),
    ("APC", "2019-08-09", "2026-02-12", "2026-10-30", "ARKO Petroleum Corp - Class A", ["Anadarko Petroleum"]),
    ("DISCA", "2022-04-11", "2022-04-08", "2022-09-16", None, ["Discovery, Inc."]),
    ("POM", "2016-03-30", "2026-10-21", "2026-10-30", "Pomdoctor Ltd - Class A", ["Pepco Holdings"]),
]


def _reihe(von, bis):
    return pd.DataFrame({"close": 10.0}, index=pd.bdate_range(von, bis))


@pytest.mark.parametrize("ticker, bis, kurs_von, kurs_bis, meta_name, namen", SIEBEN_FAELLE, ids=[f[0] for f in SIEBEN_FAELLE])
def test_sieben_faelle_wiederverwendeter_ticker_werden_abgelehnt(ticker, bis, kurs_von, kurs_bis, meta_name, namen):
    from tradingbot.daten.kursquellen import pruefe_kursreihe

    ergebnis = pruefe_kursreihe(_reihe(kurs_von, kurs_bis), meta_name, namen, pd.NaT, pd.Timestamp(bis))
    assert not ergebnis["ok"]
    assert "Kurse erst ab" in ergebnis["grund"]                 # alle sieben scheitern schon an der Abdeckung ab 2012


@pytest.mark.parametrize("meta_name, namen, erwartet", [
    ("XTRACKERS CALIFORNIA MUNICIPAL BOND ETF", ["CA Technologies", "CA, INC."], False),
    ("Beam Therapeutics Inc", ["Suntory Global Spirits", "BEAM INC"], False),      # nur 50 % Wortüberdeckung
    ("ARKO Petroleum Corp - Class A", ["Anadarko Petroleum"], False),
    ("Pomdoctor Ltd - Class A", ["Pepco Holdings"], False),
    (None, ["Discovery, Inc."], False),
    ("Constellation Energy Corporation", ["Constellation Energy Group"], True),     # Name ähnlich → Abdeckung nötig
    ("Broadcom Corp", ["Broadcom Corporation"], True),
    ("Howmet Aerospace Inc.", ["Alcoa", "Howmet Aerospace Inc.", "ARCONIC INC", "ALCOA INC"], True),
])
def test_namenspruefung_allein(meta_name, namen, erwartet):
    from tradingbot.daten.kursquellen import name_passt

    assert name_passt(meta_name, namen) is erwartet


def test_volle_abdeckung_aber_falscher_name_wird_abgelehnt_und_gegenproben():
    from tradingbot.daten.kursquellen import pruefe_kursreihe

    voll = _reihe("2011-01-03", "2018-11-05")
    falsch = pruefe_kursreihe(voll, "XTRACKERS CALIFORNIA MUNICIPAL BOND ETF", ["CA Technologies", "CA, INC."], pd.NaT, pd.Timestamp("2018-11-06"))
    assert not falsch["ok"] and falsch["name_ok"] is False and "passt nicht" in falsch["grund"]
    # Gegenprobe Tiingo: Twitter, ganze Mitgliedszeit (2013-11 bis 2022-06) mit passendem Namen
    twitter = pruefe_kursreihe(_reihe("2013-11-07", "2022-06-03"), "Twitter Inc", ["Twitter", "TWITTER, INC."],
                               pd.Timestamp("2018-06-07"), pd.Timestamp("2022-06-08"))
    assert twitter["ok"], twitter["grund"]
    # Gegenprobe yfinance: heutige Constellation Energy (seit 2022 Mitglied), Datenende vorgegeben
    ceg = pruefe_kursreihe(_reihe("2022-01-19", "2026-10-30"), "Constellation Energy Corporation", ["Constellation Energy"],
                           pd.Timestamp("2022-02-02"), pd.NaT, datenende="2026-10-30")
    assert ceg["ok"], ceg["grund"]


def test_luecken_und_fehlendes_ende():
    from tradingbot.daten.kursquellen import pruefe_abdeckung

    zu_frueh_zu_ende = pruefe_abdeckung(_reihe("2011-06-01", "2015-06-30"), pd.NaT, pd.NaT, datenende="2026-10-30")
    assert not zu_frueh_zu_ende["ok"] and "nur bis" in zu_frueh_zu_ende["grund"]
    luecken = _reihe("2011-06-01", "2016-12-30").iloc[::2]
    assert "Werktage" in pruefe_abdeckung(luecken, pd.NaT, pd.Timestamp("2017-01-03"))["grund"]
    assert pruefe_abdeckung(None, pd.NaT, pd.Timestamp("2017-01-03"))["grund"] == "keine Kurse"


def test_gefundene_fehler_vom_03_11():
    from tradingbot.daten.kursquellen import name_passt

    # Prudential: PRU ist die Stammaktie; PFH/PRH/PRS sind Anleihen derselben CIK
    pru = kursquelle(_zeile("PRU", 1137774, None, None), {1137774: ["PRU", "PFH", "PRH", "PRS"]}, LISTE)
    assert pru["symbol"] == "PRU"
    assert kursquelle(_zeile("DD", 30554, None, "2017-09-01"), {30554: ["CTA-PB", "CTA-PA"]}, LISTE)["quelle"] is None
    # Gattungszusatz darf die Namensprüfung nicht kippen, ein anderer Firmenname aber weiterhin schon
    assert name_passt("Dish Network Corp - Class A", ["Dish Network", "DISH Network CORP"])
    assert not name_passt("Beam Therapeutics Inc - Class A", ["BEAM INC"])
