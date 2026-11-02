"""Gesamtscore: Ränge und Median-Ersatz an einem von Hand nachgerechneten Beispiel."""
import math

import pandas as pd
import pytest

from tradingbot.engines.fundamental.gesamtscore import gesamtscore, vergleichsgruppe
from tradingbot.konfiguration import lade_konfiguration

KONFIG = lade_konfiguration("fundamental")
NAN = math.nan

# Fünf Firmen in SIC 28 (eigene Gruppe), zwei in SIC 73 (zu klein → Division I)
BEISPIEL = pd.DataFrame({
    "firma":            [1, 2, 3, 4, 5, 6, 7],
    "sic":              [2834, 2836, 2800, 2860, 2810, 7372, 7373],
    "piotroski_filter": [8, 6, 6, 4, NAN, 5, 7],
    "accruals":         [-0.05, 0.0, 0.02, 0.10, -0.01, 0.0, 0.01],
    "ep":               [0.08, 0.05, NAN, 0.02, 0.04, 0.03, 0.06],
    "ebit_ev":          [0.10, 0.06, 0.03, NAN, 0.05, NAN, NAN],
})


def test_vergleichsgruppe():
    assert vergleichsgruppe(BEISPIEL["sic"]).tolist() == ["SIC 28"] * 5 + ["Division I"] * 2


def test_gesamtscore_von_hand():
    # Von Hand (Perzentil-Rang, Gleichstand = Durchschnittsrang):
    # Piotroski SIC 28: 4→0,25, 6→0,625, 8→1,0; Firma 5 fehlt → Median 0,625
    # −Accruals SIC 28: Firma 4 0,2, 3 0,4, 2 0,6, 5 0,8, 1 1,0
    # E/P SIC 28: 4 0,25, 5 0,5, 2 0,75, 1 1,0; Firma 3 fehlt → Median 0,625
    # EBIT/EV SIC 28: 3 0,25, 5 0,5, 2 0,75, 1 1,0; Firma 4 fehlt → Median 0,625
    # Division I: EBIT/EV fehlt bei beiden, Gruppe ohne Wert → 0,5
    t = gesamtscore(BEISPIEL, KONFIG).set_index("firma")
    erwartet = {1: 1.0, 2: (0.625 + 0.6) / 4 + 0.75 / 2, 3: (0.625 + 0.4) / 4 + (0.625 + 0.25) / 4,
                4: (0.25 + 0.2) / 4 + (0.25 + 0.625) / 4, 5: (0.625 + 0.8) / 4 + 0.5 / 2, 6: 0.75 / 2 + 0.5 / 2, 7: 0.75 / 2 + 0.75 / 2}
    for firma, wert in erwartet.items():
        assert t.loc[firma, "gesamt"] == pytest.approx(wert), firma
    assert t.loc[5, "ersetzt"] == "piotroski" and t.loc[3, "ersetzt"] == "ep" and t.loc[4, "ersetzt"] == "ebit_ev"
    assert t.loc[6, "ersetzt"] == "ebit_ev" and t.loc[1, "ersetzt"] == ""
    assert list(gesamtscore(BEISPIEL, KONFIG)["firma"]) == [1, 7, 2, 6, 5, 3, 4]


def test_fehlender_score_nie_besser_als_median():
    # Firma ohne jeden Wert landet genau in der Mitte ihrer Gruppe, nie oben
    t = BEISPIEL.copy()
    t.loc[0, ["piotroski_filter", "accruals", "ep", "ebit_ev"]] = NAN
    erg = gesamtscore(t, KONFIG).set_index("firma")
    assert erg.loc[1, "ersetzt"] == "piotroski;accruals;ep;ebit_ev"
    assert erg.loc[1, "gesamt"] <= erg["gesamt"].max() and erg.loc[1, "gesamt"] < 0.75
