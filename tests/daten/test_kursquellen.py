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
