"""Wächter gegen ein verschobenes Universum (Jakob 17.11.2026): kursstatus.csv hängt an der Zeilennummer des Universums;
nach dem Wikipedia-Abruf des Betriebs am 16.11.2026 (22:18) passten 653 Zeilen nicht mehr. Ohne stimmige Zuordnung keine
Kurse (lauter Abbruch); im Tageslauf setzen nur die Fundamental-Bücher aus."""
import pandas as pd
import pytest

from test_tageslauf import ABEND, kurse_attrappe, umgebung  # noqa: F401
from tradingbot.betrieb.tageslauf import tageslauf
from tradingbot.daten.sp500_nachbau import UniversumVerschoben, lade_firmendaten, pruefe_zuordnung


def _universum(ticker):
    return pd.DataFrame({"ticker": ticker, "von": pd.NaT, "bis": pd.NaT, "cik": range(1, len(ticker) + 1)})


def test_stimmige_zuordnung_ok_und_fehlende_zeilen_erlaubt():
    u = _universum(["AAA", "BBB", "CCC"])
    status = pd.DataFrame({"ticker": ["AAA", "CCC"]}, index=[0, 2])
    pruefe_zuordnung(u, status)                                       # Zeile 1 ohne Status: wie bisher ohne Kurse


def test_verschobene_zuordnung_bricht_laut_ab():
    u = _universum(["NEU", "AAA", "BBB"])                            # eine Zeile vorne eingefügt
    status = pd.DataFrame({"ticker": ["AAA", "BBB"]}, index=[0, 1])
    with pytest.raises(UniversumVerschoben, match=r"2 von 2 Zeilen.*Zeile 0: \('NEU',\) ≠ \('AAA',\)"):
        pruefe_zuordnung(u, status)


def test_waechter_prueft_den_ganzen_schluessel():
    """Befund 19, Schritt 2: gleicher Ticker, aber anderes von/bis (z. B. XEC 02.03. statt 03.03.2020) ist eine Abweichung."""
    u = pd.DataFrame({"ticker": ["XEC"], "von": pd.to_datetime(["2014-06-20"]), "bis": pd.to_datetime(["2020-03-03"]), "cik": [1]})
    status = pd.DataFrame({"ticker": ["XEC"], "von": ["2014-06-20"], "bis": ["2020-03-02"]}, index=[0])
    with pytest.raises(UniversumVerschoben, match=r"1 von 1 Zeilen.*2020-03-03.*2020-03-02"):
        pruefe_zuordnung(u, status)
    pruefe_zuordnung(u, status.assign(bis="2020-03-03"))


def test_lade_firmendaten_ordnet_nie_still_falsch_zu():
    u = _universum(["NEU", "AAA"])
    status = pd.DataFrame({"ticker": ["AAA", "BBB"], "gueltig": True, "quelle": "yfinance", "symbol": ["AAA", "BBB"]}, index=[0, 1])
    with pytest.raises(UniversumVerschoben):
        lade_firmendaten(u, status, {})


def test_tageslauf_sperrt_nur_die_fundamental_buecher(umgebung):
    j, rm = umgebung

    def verschoben(tag):
        raise UniversumVerschoben("Universum und kursstatus.csv verschoben: 653 von 813 Zeilen mit anderem Ticker")

    e = tageslauf(ABEND, j, kurse_laden=kurse_attrappe(), fundamental_bewertung=verschoben, risk=rm, sichern=False)
    buecher = {bv.vorschlag.buch for bv, _ in e.vorschlaege}
    assert "real" in buecher and not buecher & {"fundamental_a", "fundamental_b"} and e.gestoppt is None
    assert any("Fundamental-Bewertung gesperrt" in s and "übrige Bücher laufen normal" in s for s in e.sofort)
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='fundamental_gesperrt'").fetchone()[0] == 1
    assert all(len(j.buchwerte(n)) == 1 for n in ("fundamental_a", "fundamental_b"))   # Buchwert trotzdem gespeichert
