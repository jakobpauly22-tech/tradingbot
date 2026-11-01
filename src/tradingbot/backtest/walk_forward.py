"""Walk-forward-Test: rollierende Kalibrierungs- und Testfenster, gewertet wird nur außerhalb der Stichprobe.

Ablauf: Die Historie wird in Fenster geteilt (z.B. 3 Jahre Kalibrierung, dann 1 Jahr Test, um 1 Jahr
verschoben). Die Simulation läuft durchgehend über alle Testfenster, Positionen bleiben zwischen den Fenstern
bestehen (wie im echten Betrieb). Zu Beginn jedes Testfensters ruft der Test `strategie.kalibrieren(sicht,
kalibrierung_ab)` auf, sofern die Strategie das kann; die Sicht endet am Tag vor dem Testfenster, es gibt also
keinen Blick in das Testfenster. Strategien mit festen Parametern (Technik-Startwerte) brauchen keine
Kalibrierung; für sie zeigt der Walk-forward, wie stabil das Ergebnis über die Fenster ist.

Quelle: wissen/09_Oekonometrie.md, „Bezug zum Trading-Bot“ (externe Validität: Out-of-Sample- und
Walk-Forward-Tests).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from tradingbot.backtest.marktdaten import Marktdaten, Sicht
from tradingbot.backtest.simulation import Ergebnis, TeilportfolioDefinition, simuliere
from tradingbot.kennzahlen.performance import max_drawdown


@dataclass(frozen=True)
class Fenster:
    kalibrierung_ab: pd.Timestamp
    test_ab: pd.Timestamp
    test_bis: pd.Timestamp


def walk_forward_fenster(start, ende, *, kalibrierung_jahre: int = 3, test_jahre: int = 1, schritt_jahre: int = 1) -> list[Fenster]:
    """Rollierende Fenster nach Kalenderjahren; das letzte Testfenster endet spätestens am `ende`."""
    start, ende = pd.Timestamp(start), pd.Timestamp(ende)
    fenster = []
    kal = start
    while True:
        test_ab = kal + pd.DateOffset(years=kalibrierung_jahre)
        test_bis = test_ab + pd.DateOffset(years=test_jahre) - pd.Timedelta(days=1)
        if test_ab > ende:
            break
        fenster.append(Fenster(kal, test_ab, min(test_bis, ende)))
        kal = kal + pd.DateOffset(years=schritt_jahre)
    if not fenster:
        raise ValueError("Zeitraum zu kurz für ein Kalibrierungs- plus Testfenster")
    return fenster


class _WalkForwardStrategie:
    """Hülle um eine Strategie: ruft zu Beginn jedes Testfensters `kalibrieren` auf."""

    def __init__(self, strategie, fenster: list[Fenster], marktdaten: Marktdaten):
        self.innen = strategie
        self.name = strategie.name
        self.fenster = list(fenster)
        self.m = marktdaten
        self.kalibriert: list[pd.Timestamp] = []

    def zielgewichte(self, stichtag, sicht):
        while self.fenster and stichtag >= self.fenster[0].test_ab:
            f = self.fenster.pop(0)
            if hasattr(self.innen, "kalibrieren"):
                self.innen.kalibrieren(Sicht(self.m, f.test_ab - pd.Timedelta(days=1)), f.kalibrierung_ab)
            self.kalibriert.append(f.test_ab)
        return self.innen.zielgewichte(stichtag, sicht)


def walk_forward(
    definitionen: list[TeilportfolioDefinition],
    marktdaten: Marktdaten,
    fenster: list[Fenster],
    *,
    benchmark: pd.Series | None = None,
    **simulations_optionen,
) -> tuple[dict[str, Ergebnis], pd.DataFrame]:
    """Simuliert vom ersten bis zum letzten Testfenster und wertet je Fenster aus.

    Gibt (Ergebnisse, Fenstertabelle) zurück. Die Tabelle enthält je Teilportfolio und Fenster die Rendite,
    die der Benchmark (falls übergeben, z.B. Total-Return-Index), die Differenz und den Max Drawdown.
    """
    gehuellt = [
        TeilportfolioDefinition(d.name, d.startkapital, _WalkForwardStrategie(d.strategie, fenster, marktdaten), d.instrumente,
                                art=d.art, steuergruppe=d.steuergruppe, rolle=d.rolle)
        for d in definitionen
    ]
    ergebnisse = simuliere(gehuellt, marktdaten, fenster[0].test_ab, fenster[-1].test_bis, **simulations_optionen)

    zeilen = []
    for name, e in ergebnisse.items():
        for f in fenster:
            werte = _fensterwerte(e.wert, f)
            if werte is None:
                continue
            zeile = {"teilportfolio": name, "test_ab": f.test_ab.date(), "test_bis": f.test_bis.date(),
                     "rendite": float(werte.iloc[-1] / werte.iloc[0] - 1), "max_drawdown": max_drawdown(werte)["max_drawdown"]}
            if benchmark is not None:
                b = _fensterwerte(benchmark, f)
                zeile["benchmark"] = float(b.iloc[-1] / b.iloc[0] - 1) if b is not None else float("nan")
                zeile["differenz"] = zeile["rendite"] - zeile["benchmark"]
            zeilen.append(zeile)
    return ergebnisse, pd.DataFrame(zeilen)


def _fensterwerte(werte: pd.Series, f: Fenster) -> pd.Series | None:
    """Werte vom letzten Schluss vor dem Fenster (Startwert) bis zum Fensterende."""
    vorher = werte.loc[: f.test_ab - pd.Timedelta(days=1)]
    im_fenster = werte.loc[f.test_ab : f.test_bis]
    if im_fenster.empty:
        return None
    return pd.concat([vorher.iloc[-1:], im_fenster]) if len(vorher) else im_fenster
