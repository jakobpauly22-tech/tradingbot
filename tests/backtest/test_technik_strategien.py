"""Satellite-Strategien: Sizing, Stop, Zeit-Stop, Regime, Look-ahead, Integration mit der Simulation."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.engines.technik.strategien import SatelliteStrategie, berechne_indikatoren, score
from tradingbot.konfiguration import lade_konfiguration

KONFIG = lade_konfiguration("technik")


def _kerzen(schluss, start="2020-01-01", spanne=0.01):
    tage = pd.bdate_range(start, periods=len(schluss))
    c = pd.Series(schluss, index=tage, dtype=float)
    o = c.shift(1).fillna(c.iloc[0])
    return pd.DataFrame({"open": o, "high": np.maximum(o, c) * (1 + spanne), "low": np.minimum(o, c) * (1 - spanne),
                         "close": c, "volume": 1000.0, "dividende": 0.0, "split": 0.0})


def _lauf(strategie, kurse, konfig_bt):
    m = Marktdaten(kurse)
    d = TeilportfolioDefinition("satellite", 1250.0, strategie, [Instrument(t, "etf") for t in kurse], rolle="satellite")
    tage = m.kalender
    return simuliere([d], m, tage[0], tage[-1], kosten=Kostenmodell.ohne_kosten(), regeln=Ausfuehrungsregeln(ganze_stuecke=False),
                     konfig=konfig_bt)["satellite"]


def test_indikatoren_ohne_blick_nach_vorn():
    rng = np.random.default_rng(5)
    k = _kerzen(100 * np.cumprod(1 + rng.normal(0.0003, 0.01, 400)))
    voll = berechne_indikatoren(k, KONFIG)
    for schnitt in (250, 330, 399):
        teil = berechne_indikatoren(k.iloc[:schnitt], KONFIG)
        pd.testing.assert_frame_equal(teil, voll.iloc[:schnitt], check_freq=False)


def test_positionsgroesse_risiko_und_obergrenze():
    rng = np.random.default_rng(1)
    k = _kerzen(100 * np.cumprod(1 + rng.normal(0.0, 0.01, 300)))
    s = SatelliteStrategie(["crossover"], {"A": k}, KONFIG)
    tag = k.index[-1]
    z = s.ind["A"].loc[tag]
    assert s._gewicht("A", tag) == pytest.approx(min(0.01 * z["close"] / (2 * z["atr"]), 0.25))
    ruhig = _kerzen(np.linspace(100, 101, 300), spanne=0.0005)
    s2 = SatelliteStrategie(["crossover"], {"B": ruhig}, KONFIG)
    assert s2._gewicht("B", ruhig.index[-1]) == 0.25                      # Anleihe-ähnlich: Obergrenze 25 %


def test_price_channel_zeit_stop_63_tage(konfig):
    # 60 Tage seitwärts, dann Ausbruch und langsamer Anstieg ohne 20-Tage-Tief: Ausstieg nur über den Zeit-Stop
    schluss = [100.0] * 60 + list(np.linspace(102, 120, 120))
    k = _kerzen(schluss, spanne=0.001)
    s = SatelliteStrategie(["price_channel"], {"A": k}, KONFIG)
    e = _lauf(s, {"A": k}, konfig)
    prot = pd.DataFrame(s.protokoll)
    assert prot.iloc[0]["aktion"] == "kaufen"
    verkauf = prot[prot.aktion == "verkaufen"].iloc[0]
    assert verkauf["grund"] == "Zeit-Stop 63 Tage"
    kauf_tag = e.trades[e.trades.richtung > 0].datum.iloc[0]
    assert ((k.index > kauf_tag) & (k.index <= verkauf["tag"])).sum() == 63


def test_stop_bei_2_atr(konfig):
    # Ausbruch, dann Absturz unter Einstieg − 2 × ATR → Stop vor dem 20-Tage-Tief
    schluss = [100.0] * 60 + [103.0, 104.0, 104.5] + [95.0] * 10
    k = _kerzen(schluss, spanne=0.002)
    s = SatelliteStrategie(["price_channel"], {"A": k}, KONFIG)
    _lauf(s, {"A": k}, konfig)
    prot = pd.DataFrame(s.protokoll)
    assert prot[prot.aktion == "verkaufen"].iloc[0]["grund"].startswith("Stop")


def test_regime_sperrt_rsi_bei_starkem_trend():
    tage = 300
    k = _kerzen(100 * np.cumprod(np.full(tage, 1.004)))       # starker, gleichmäßiger Trend: ADX hoch
    s = SatelliteStrategie(["rsi2", "crossover"], {"A": k}, KONFIG, regime=True)
    tag = k.index[-1]
    assert s.ind["A"].loc[tag, "adx"] > 25
    rsi_regel, cross = s.regeln["rsi2"], s.regeln["crossover"]
    assert not s._regime_erlaubt(rsi_regel, "A", tag) and s._regime_erlaubt(cross, "A", tag)


def test_crossover_nach_stop_gesperrt_bis_neues_kreuzen():
    from tradingbot.engines.technik.strategien import Crossover
    k = _kerzen(np.linspace(100, 150, 260))
    ind = {"A": berechne_indikatoren(k, KONFIG)}
    c = Crossover(ind)
    tag = k.index[-1]
    assert c.einstieg("A", tag) is not None
    c.nach_stop("A", tag)
    assert c.einstieg("A", tag) is None


def test_score_schnittstelle():
    k = _kerzen(np.linspace(100, 150, 300))
    s = score(k.index[-1], ["A", "B"], {"A": k}, KONFIG)
    assert list(s.index) == ["A", "B"] and s["B"] == 0.0 and s["A"] >= 1
