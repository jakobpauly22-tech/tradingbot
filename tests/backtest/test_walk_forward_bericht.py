import json

import numpy as np
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.bericht import fuehre_lauf_aus
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import TeilportfolioDefinition
from tradingbot.backtest.strategie import BuyAndHold, FesteGewichte
from tradingbot.backtest.walk_forward import walk_forward, walk_forward_fenster


def test_fenster_nach_kalenderjahren():
    f = walk_forward_fenster("2012-01-01", "2024-12-31", kalibrierung_jahre=3, test_jahre=1)
    assert len(f) == 10
    assert (f[0].kalibrierung_ab, f[0].test_ab, f[0].test_bis) == (pd.Timestamp("2012-01-01"), pd.Timestamp("2015-01-01"), pd.Timestamp("2015-12-31"))
    assert f[-1].test_ab == pd.Timestamp("2024-01-01") and f[-1].test_bis == pd.Timestamp("2024-12-31")
    with pytest.raises(ValueError):
        walk_forward_fenster("2023-01-01", "2024-12-31", kalibrierung_jahre=3)


def _markt(n=800, start="2020-01-01", seed=4):
    rng = np.random.default_rng(seed)
    return Marktdaten({
        "A": kerzen(100 * np.cumprod(1 + rng.normal(0.0005, 0.012, n)), start=start),
        "B": kerzen(100 * np.cumprod(1 + rng.normal(0.0003, 0.010, n)), start=start),
    })


def test_kalibrierung_ohne_blick_ins_testfenster(konfig, ohne_kosten, bruchteile):
    m = _markt()
    fenster = walk_forward_fenster("2020-01-01", "2023-01-31", kalibrierung_jahre=1, test_jahre=1)

    class Lernend(BuyAndHold):
        def __init__(self):
            super().__init__({"A": 1.0})
            self.aufrufe = []

        def kalibrieren(self, sicht, kalibrierung_ab):
            test_ab = fenster[len(self.aufrufe)].test_ab
            assert sicht.schlusskurse().index.max() < test_ab      # kein Blick ins Testfenster
            self.aufrufe.append((kalibrierung_ab, sicht.stichtag))

    strategie = Lernend()
    ergebnisse, tabelle = walk_forward([TeilportfolioDefinition("core", 1000.0, strategie, [Instrument("A")])], m, fenster,
                                       kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)
    assert [a for a, _ in strategie.aufrufe] == [f.kalibrierung_ab for f in fenster]
    assert all(s < f.test_ab for (_, s), f in zip(strategie.aufrufe, fenster))
    assert ergebnisse["core"].wert.index[0] >= fenster[0].test_ab           # gewertet wird nur außerhalb der Stichprobe
    assert list(tabelle.test_ab) == [f.test_ab.date() for f in fenster]


def test_fenstertabelle_rechnet_renditen_je_fenster(konfig, ohne_kosten, bruchteile):
    m = _markt()
    fenster = walk_forward_fenster("2020-01-01", "2022-12-31", kalibrierung_jahre=1, test_jahre=1)
    ergebnisse, tabelle = walk_forward([TeilportfolioDefinition("core", 1000.0, BuyAndHold({"A": 1.0}), [Instrument("A")])], m, fenster,
                                       benchmark=m.schluss["B"], kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)
    w = ergebnisse["core"].wert
    zweites = tabelle.iloc[1]
    erwartet = w.loc[:"2022-12-31"].iloc[-1] / w.loc[:"2021-12-31"].iloc[-1] - 1
    assert zweites.rendite == pytest.approx(erwartet)
    b = m.schluss["B"]
    assert zweites.benchmark == pytest.approx(b.loc[:"2022-12-31"].iloc[-1] / b.loc[:"2021-12-31"].iloc[-1] - 1)


def test_lauf_mit_bericht_und_ablage(konfig, mit_kosten, tmp_path):
    m = _markt(n=520, start="2022-01-03")
    rf = pd.Series([2.0], index=pd.to_datetime(["2021-12-01"]))
    definitionen = [
        TeilportfolioDefinition("core", 500.0, BuyAndHold({"B": 1.0}), [Instrument("A"), Instrument("B")]),
        TeilportfolioDefinition("satellite_schatten", 1250.0, FesteGewichte({"A": 0.5, "B": 0.5}, "M"),
                                [Instrument("A"), Instrument("B")], art="schatten", steuergruppe="schatten", rolle="satellite"),
    ]
    lauf = fuehre_lauf_aus("test", definitionen, m, "2022-01-03", "2023-12-29", benchmark_ticker="B", rf_zins_prozent=rf,
                           kosten=mit_kosten, konfig=konfig, ablage_wurzel=tmp_path)
    k = lauf.kennzahlen
    # Core = Buy & Hold der Benchmark: identisch mit dem Zwilling auf allen Ebenen
    assert k.loc["core", "differenz_cagr_nach_verkauf_und_steuern"] == pytest.approx(0.0, abs=1e-12)
    assert k.loc["core", "endwert_nach_verkauf_und_steuern"] <= k.loc["core", "endwert"]
    assert k.loc["satellite_schatten", "art"] == "schatten"
    assert isinstance(k.loc["satellite_schatten", "monate_unter_minus_10"], list)

    pfad = lauf.pfad
    for datei in ["bericht.md", "kennzahlen.json", "meta.json", "config/backtest.yaml", "core/werte.csv", "core/trades.csv",
                  "benchmark_core/werte.csv", "satellite_schatten/steuerereignisse.csv"]:
        assert (pfad / datei).exists(), datei
    meta = json.loads((pfad / "meta.json").read_text(encoding="utf-8"))
    assert meta["zeitraum"] == ["2022-01-03", "2023-12-29"] and meta["benchmark"] == "B" and "commit" in meta["git"]
    bericht = (pfad / "bericht.md").read_text(encoding="utf-8")
    for teil in ["Ergebnis auf drei Ebenen", "nach Verkauf und Steuern", "Monat ≤ −10 %", "Core-Notbremse", "nicht geöffnet"]:
        assert teil in bericht, teil
