"""Befund 19, Schritt 2 (Plan Jakob 17.11.2026): kursstatus.csv wird über den Schlüssel (Ticker, von, bis) zugeordnet,
nie über die Zeilennummer; jede Abweichung bricht laut ab."""
from __future__ import annotations

import pandas as pd
import pytest

from tradingbot.daten.kursstatus import UniversumVerschoben, lade_kursstatus, ordne_zu, schluessel, tag_text
from tradingbot.daten.sp500_nachbau import UniversumVerschoben as AusNachbau


def _universum(zeilen):
    t = pd.DataFrame(zeilen, columns=["ticker", "von", "bis"])
    t["von"], t["bis"] = pd.to_datetime(t["von"]), pd.to_datetime(t["bis"])
    t["cik"] = range(1, len(t) + 1)
    return t


def _status(zeilen):
    """Wie aus der CSV gelesen: index (gespeicherte Zeile), ticker, von, bis als Text, leere Daten als NaN."""
    t = pd.DataFrame(zeilen, columns=["index", "ticker", "von", "bis"])
    t[["von", "bis"]] = t[["von", "bis"]].replace("", float("nan"))
    t["symbol"] = t["ticker"]
    return t


def test_gleiche_ausnahme_wie_im_tageslauf():
    assert AusNachbau is UniversumVerschoben


def test_tag_text_und_schluessel():
    assert tag_text(None) == tag_text(float("nan")) == tag_text(pd.NaT) == tag_text("") == ""
    assert tag_text("2020-03-02") == tag_text(pd.Timestamp("2020-03-02")) == "2020-03-02"
    u = _universum([("AAA", None, "2015-01-02")])
    assert schluessel(u).iloc[0] == ("AAA", "", "2015-01-02")


def test_eingefuegte_zeile_verschiebt_nichts_mehr():
    """Der Fall vom 16.11.2026: eine Zeile vorne eingefügt; die gespeicherten Nummern zeigen jetzt daneben."""
    status = _status([(0, "AAA", "", ""), (1, "BBB", "2015-01-02", ""), (2, "CCC", "", "2020-03-02")])
    u = _universum([("DAY", None, "2026-02-09"), ("AAA", None, None), ("BBB", "2015-01-02", None), ("CCC", None, "2020-03-02")])
    s = ordne_zu(u, status)
    assert s.index.name == "index" and list(s.index) == [1, 2, 3]
    assert list(s["ticker"]) == ["AAA", "BBB", "CCC"] and list(s["index_csv"]) == [0, 1, 2]
    assert "index" not in s.columns                                 # gleiche Form wie read_csv(...).set_index("index")
    assert list(s.reset_index()["index"]) == [1, 2, 3]
    for nr, z in s.iterrows():
        assert u.at[nr, "ticker"] == z["ticker"]


def test_universumszeile_ohne_status_bleibt_ohne_kurse():
    status = _status([(0, "AAA", "", "")])
    s = ordne_zu(_universum([("AAA", None, None), ("ALT", None, "2005-01-03")]), status)
    assert list(s.index) == [0]


def test_geaendertes_datum_bricht_laut_ab():
    """XEC/IR: Wikipedia verschiebt das Datum um einen Tag; die Statuszeile findet ihre Mitgliedschaft nicht mehr."""
    status = _status([(0, "XEC", "2014-06-20", "2020-03-02"), (1, "IR", "2020-03-02", "")])
    u = _universum([("XEC", "2014-06-20", "2020-03-03"), ("IR", "2020-03-03", None)])
    with pytest.raises(UniversumVerschoben, match=r"2 von 2 Statuszeilen ohne Mitgliedschaft.*XEC"):
        ordne_zu(u, status)


def test_doppelter_schluessel_bricht_laut_ab():
    status = _status([(0, "AAA", "", "")])
    with pytest.raises(UniversumVerschoben, match="doppelt in Universum"):
        ordne_zu(_universum([("AAA", None, None), ("AAA", None, None)]), status)
    with pytest.raises(UniversumVerschoben, match="doppelt in kursstatus.csv"):
        ordne_zu(_universum([("AAA", None, None)]), _status([(0, "AAA", "", ""), (1, "AAA", "", "")]))


def test_lade_kursstatus_liest_ticker_na_nicht_als_fehlend(tmp_path):
    datei = tmp_path / "kursstatus.csv"
    datei.write_text("index,ticker,name,von,bis,quelle,symbol,gueltig\n0,NA,Nationale,,,yfinance,NA,True\n", encoding="utf-8")
    s = lade_kursstatus(_universum([("NA", None, None)]), datei)
    assert s.loc[0, "ticker"] == "NA" and bool(s.loc[0, "gueltig"])
