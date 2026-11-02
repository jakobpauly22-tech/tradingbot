"""Fundamental-Schattenportfolio: Auswahlregel, Halten im Drift-Band, Delisting, Kontrollportfolio."""
import math

import numpy as np
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.marktdaten import Delisting, Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.backtest.strategie import BuyAndHold
from tradingbot.engines.fundamental.schatten import FundamentalSchatten, auswahl, kontrollportfolio
from tradingbot.kennzahlen.rendite import total_return_index


def _rangliste(n, sic=None):
    return pd.DataFrame({"ticker": [f"T{i:02d}" for i in range(1, n + 1)], "sic": sic or [2800 + i for i in range(n)], "ersetzt": ""})


REGEL = dict(titel=20, puffer=30, max_je_branche=5, band=(0.025, 0.075))


def test_erste_auswahl_top_20_mit_branchenobergrenze():
    # T01–T08 in SIC 28, Rest in verschiedenen Branchen: nur 5 aus SIC 28
    r = _rangliste(40, [2834] * 8 + [1000 + 100 * i for i in range(32)])
    ziel, prot = auswahl(r, pd.Series(dtype=float), **REGEL)
    gekauft = list(ziel.index)
    assert len(gekauft) == 20 and all(ziel == 0.05)
    assert sum(t in gekauft for t in [f"T{i:02d}" for i in range(1, 9)]) == 5   # T06–T08 übersprungen
    assert "T06" not in gekauft and "T23" in gekauft


def test_puffer_ausschluss_und_drift_band():
    r = _rangliste(60, [1000 + 100 * i for i in range(60)])
    # Gehalten: T25 (Rang 25, im Puffer, Gewicht 5 %) bleibt, T31 (Rang 31) raus, X (nicht im Universum) raus,
    # T02 mit 8 % zurück auf 5 %, T03 mit 2 % zurück auf 5 %, T04 mit 7 % halten (NaN)
    gew = pd.Series({"T25": 0.05, "T31": 0.05, "X": 0.04, "T02": 0.08, "T03": 0.02, "T04": 0.07})
    ziel, prot = auswahl(r, gew, **REGEL)
    assert ziel["T31"] == 0.0 and ziel["X"] == 0.0
    assert math.isnan(ziel["T25"]) and math.isnan(ziel["T04"])
    assert ziel["T02"] == 0.05 and ziel["T03"] == 0.05
    gehalten = {"T25", "T02", "T03", "T04"}
    neu = [t for t, w in ziel.items() if t not in gew.index]
    assert len(gehalten) + len(neu) == 20 and neu[0] == "T01"
    gruende = {p["ticker"]: p["grund"] for p in prot}
    assert gruende["X"] == "nicht im gefilterten Universum" and gruende["T31"] == "Rang 31 > 30"


def test_simulation_haelt_bestand_bei_nan(konfig, ohne_kosten):
    class Zweimal:
        name = "zweimal"
        def __init__(self):
            self.n = 0
        def zielgewichte(self, tag, sicht):
            self.n += 1
            if self.n == 1:
                return pd.Series({"A": 0.5, "B": 0.5})
            if self.n == 10:
                assert sicht.gewichte()["A"] == pytest.approx(2 / 3, abs=0.01)   # A hat sich verdoppelt
                return pd.Series({"A": math.nan, "B": 0.0})
            return None
    tage = pd.bdate_range("2024-01-01", periods=20)
    a = np.where(np.arange(20) < 5, 100.0, 200.0)
    m = Marktdaten({"A": kerzen(a), "B": kerzen([100.0] * 20)})
    d = TeilportfolioDefinition("core", 1000.0, Zweimal(), [Instrument("A", "aktie"), Instrument("B", "aktie")])
    e = simuliere([d], m, tage[0], tage[-1], kosten=ohne_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["core"]
    assert e.bestaende["A"].iloc[-1] == e.bestaende["A"].iloc[5]           # A unverändert gehalten
    assert e.bestaende["B"].iloc[-1] == 0                                   # B verkauft
    assert set(e.trades.ticker) == {"A", "B"} and (e.trades.ticker == "A").sum() == 1


@pytest.mark.parametrize("rendite, grund", [(0.0, "uebernahme"), (-0.30, "pleite")])
def test_delisting_schliesst_position(konfig, ohne_kosten, bruchteile, rendite, grund):
    a = kerzen([100.0] * 5 + [120.0] * 5)                 # Kursreihe endet am 10. Tag
    b = kerzen([50.0] * 20)
    letzter = a.index[-1]
    m = Marktdaten({"A": a, "B": b}, delistings={"A": Delisting(letzter, rendite, grund)})
    d = TeilportfolioDefinition("core", 1000.0, BuyAndHold({"A": 1.0}), [Instrument("A", "aktie"), Instrument("B", "aktie")])
    e = simuliere([d], m, b.index[0], b.index[-1], kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["core"]
    stueck = 1000.0 / 100.0
    assert e.bestaende.loc[e.bestaende.index > letzter, "A"].eq(0).all()
    assert e.werte["cash"].iloc[-1] == pytest.approx(stueck * 120.0 * (1 + rendite))
    assert e.meta["delistings"].iloc[0]["grund"] == grund


def test_kontrollportfolio_gleichgewichtet_quartalsweise():
    # Zwei Titel, A steigt um 10 %, B fällt um 10 % im ersten Quartal; danach gleich gewichtet neu
    tage = pd.bdate_range("2024-01-01", "2024-06-28")
    a = np.where(tage < "2024-02-01", 100.0, 110.0)
    b = np.where(tage < "2024-02-01", 100.0, 90.0)
    kurse = {"A": kerzen(a, start="2024-01-01"), "B": kerzen(b, start="2024-01-01")}
    rl = {pd.Timestamp("2024-01-01"): pd.DataFrame({"ticker": ["A", "B"]}), pd.Timestamp("2024-04-01"): pd.DataFrame({"ticker": ["A"]})}
    werte, stat = kontrollportfolio(rl, kurse, pd.DatetimeIndex(tage), {}, 1000.0, "2024-06-28")
    assert werte.iloc[0] == 1000.0
    assert werte.loc["2024-03-29"] == pytest.approx(1000.0)                # (1,1 + 0,9) / 2
    assert werte.iloc[-1] == pytest.approx(1000.0)                          # Q2 nur A, Kurs flach
    assert list(stat["titel"]) == [2, 1]


def test_signal_nicht_vor_us_feiertag():
    # Stichtag Montag 03.07.2023: nächster Kalendertag 04.07. ist nur Xetra-Tag → Signal 04.07., Ausführung 05.07.
    kal = pd.bdate_range("2023-06-28", "2023-07-07")
    us = kal.drop(pd.Timestamp("2023-07-04"))
    from tradingbot.engines.fundamental.schatten import signal_und_ausfuehrung
    assert signal_und_ausfuehrung([pd.Timestamp("2023-07-03")], kal, us) == [
        (pd.Timestamp("2023-07-03"), pd.Timestamp("2023-07-04"), pd.Timestamp("2023-07-05"))]
    # Stichtag an einem Feiertag beider Börsen (01.01.): Signal nie vor dem Stichtag
    kal2 = pd.DatetimeIndex(["2017-12-29", "2018-01-02", "2018-01-03"])
    assert signal_und_ausfuehrung([pd.Timestamp("2018-01-01")], kal2, kal2)[0][1:] == (pd.Timestamp("2018-01-02"), pd.Timestamp("2018-01-03"))


def test_haltefaktor_mit_dividende_und_delisting():
    from tradingbot.engines.fundamental.schatten import haltefaktor
    k = kerzen([100.0, 100.0, 110.0, 110.0, 110.0], eroeffnung=[100.0, 95.0, 100.0, 110.0, 110.0], dividende=[0, 0, 0, 2.2, 0])
    tri = total_return_index(k)
    tage = k.index
    # Kauf zur Eröffnung 95 am Tag 2, Schluss Tag 4 = 110 plus Dividende 2,2 reinvestiert: 100/95 · 1,1 · 1,02
    assert haltefaktor(k, tri, tage[1], tage[3]) == pytest.approx(100 / 95 * 1.1 * 1.02)
    pleite = Delisting(tage[2], -0.30, "pleite")
    assert haltefaktor(k, tri, tage[1], tage[4], pleite) == pytest.approx(100 / 95 * 1.1 * 0.7)
