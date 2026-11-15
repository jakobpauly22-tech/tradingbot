"""Schattenbuch „regime“ im Backtest: Strategie, statische Mischung und Kriterien je Hälfte (docs/REGIME.md, Abschnitte
1, 4 und 7c). Die Regeln stehen vor dem ersten Lauf fest; hier wird nichts optimiert.
"""
from __future__ import annotations

import pandas as pd

from tradingbot.kennzahlen.performance import kennzahlen

DRAWDOWN_ANTEIL_MAX = 0.75      # Kriterium c: |MDD_V1| ≤ 0,75 · |MDD_KuH| (mindestens 25 % kleiner)
RUNDUNG = 1e-9


class RegimeStrategie:
    """Hält 100 % des Instruments bei „Risiko an“ und 0 % (Kasse) bei „Risiko aus“.

    `zustand`: Zustand mit Haltepflicht je Monatsende (True = Risiko aus), ohne Lücken. Am Stichtag gilt der Zustand des
    letzten Monatsendes bis einschließlich Stichtag; die Order folgt zur Eröffnung des nächsten Handelstags. Passt der
    Bestand nicht zum Zustand (auch nach einer gescheiterten Order), wird das Ziel erneut gegeben.
    """

    def __init__(self, ticker: str, zustand: pd.Series, name: str = "Regime"):
        z = zustand.dropna()
        if z.empty:
            raise ValueError("Regime: kein Zustand vorhanden")
        self.ticker, self.name = ticker, name
        self.zustand = pd.Series([bool(w) for w in z], index=pd.DatetimeIndex(z.index)).sort_index()

    def zielgewichte(self, stichtag, sicht):
        bekannt = self.zustand.loc[: pd.Timestamp(stichtag)]
        if bekannt.empty:
            return None
        aus = bool(bekannt.iloc[-1])
        investiert = sicht.bestand.get(self.ticker, 0.0) > 1e-9
        if aus != investiert:                       # Bestand passt zum Zustand
            return None
        return pd.Series({self.ticker: 0.0 if aus else 1.0})


class MischungStrategie:
    """Statische Mischung: festes Zielgewicht des Instruments, Rest Kasse, quartalsweise zurückgestellt.

    `gewicht_ab`: Signaltag → Zielgewicht ab diesem Tag (z. B. erster Tag und letzter Handelstag vor der Hälftengrenze).
    Zurückgestellt wird am Signaltag eines neuen Gewichts und am ersten Handelstag jedes neuen Quartals (Ausführung am
    Folgetag, wie `FesteGewichte`).
    """

    def __init__(self, ticker: str, gewicht_ab: pd.Series, name: str = "Statische Mischung"):
        self.ticker, self.name = ticker, name
        self.gewicht_ab = pd.Series(gewicht_ab, dtype=float).sort_index()
        self.gewicht_ab.index = pd.DatetimeIndex(self.gewicht_ab.index)
        self._quartal, self._gewicht = None, None

    def zielgewichte(self, stichtag, sicht):
        tag = pd.Timestamp(stichtag)
        bekannt = self.gewicht_ab.loc[:tag]
        if bekannt.empty:
            return None
        gewicht, quartal = float(bekannt.iloc[-1]), tag.to_period("Q")
        if gewicht == self._gewicht and quartal == self._quartal:
            return None
        self._gewicht, self._quartal = gewicht, quartal
        return pd.Series({self.ticker: gewicht})


def ziel_an_je_tag(zustand: pd.Series, tage: pd.DatetimeIndex) -> pd.Series:
    """Je Handelstag: True, wenn das Buch an diesem Tag Aktien halten soll. Es gilt der Zustand des letzten Monatsendes
    strikt vor dem Tag (die Order wird am Tag nach der Bewertung zur Eröffnung ausgeführt). Tage davor entfallen."""
    z = zustand.dropna()
    z = pd.Series([not bool(w) for w in z], index=pd.DatetimeIndex(z.index)).sort_index()
    tage = pd.DatetimeIndex(tage)
    lage = z.index.searchsorted(tage, side="left") - 1          # letztes Monatsende < Tag
    gueltig = lage >= 0
    return pd.Series(z.to_numpy()[lage[gueltig]], index=tage[gueltig], dtype=bool)


def aktienanteil(zustand: pd.Series, tage: pd.DatetimeIndex, von, bis) -> float:
    """Durchschnittlicher Aktienanteil: Anteil der Handelstage in [von, bis] mit Ziel „Risiko an“."""
    an = ziel_an_je_tag(zustand, tage).loc[pd.Timestamp(von): pd.Timestamp(bis)]
    if an.empty:
        raise ValueError(f"Regime: keine Handelstage mit Zustand zwischen {von} und {bis}")
    return float(an.mean())


def abschnitt(werte: pd.Series, von, bis) -> pd.Series:
    """Wertreihe eines Abschnitts mit dem letzten Wert vor `von` als Basis (so zählt auch die Rendite des ersten Tags)."""
    von, bis = pd.Timestamp(von), pd.Timestamp(bis)
    davor = werte.loc[werte.index < von]
    teil = werte.loc[von:bis]
    return pd.concat([davor.iloc[-1:], teil]) if len(davor) else teil


def kriterien_je_haelfte(v1: pd.Series, kuh: pd.Series, mischung: pd.Series, haelften: list[tuple], rf_tag: pd.Series) -> pd.DataFrame:
    """Kriterien a–c je Hälfte (docs/REGIME.md, Abschnitt 4) aus drei Wertreihen nach Kosten und Steuern:
    a) Sharpe_V1 ≥ Sharpe_KuH; b) Sharpe_V1 ≥ Sharpe_Mischung; c) |MDD_V1| ≤ 0,75 · |MDD_KuH|.
    Ist ein Sharpe nicht bestimmbar (keine Schwankung), gilt das betroffene Kriterium als nicht erfüllt."""
    zeilen = []
    for nr, (von, bis) in enumerate(haelften, start=1):
        k = {n: kennzahlen(abschnitt(w, von, bis), None, rf_tag) for n, w in (("v1", v1), ("kuh", kuh), ("mischung", mischung))}
        zeile = {"haelfte": nr, "von": pd.Timestamp(von).date(), "bis": pd.Timestamp(bis).date()}
        for n, kz in k.items():
            zeile |= {f"{n}_cagr": kz["cagr"], f"{n}_sharpe": kz["sharpe"], f"{n}_max_dd": kz["max_drawdown"]}
        # Vergleiche mit Rundungstoleranz 1e-9 (gleiche Renditen sollen als „≥“ gelten); NaN-Vergleiche sind False
        zeile["a"] = bool(k["v1"]["sharpe"] >= k["kuh"]["sharpe"] - RUNDUNG)
        zeile["b"] = bool(k["v1"]["sharpe"] >= k["mischung"]["sharpe"] - RUNDUNG)
        zeile["c"] = bool(abs(k["v1"]["max_drawdown"]) <= DRAWDOWN_ANTEIL_MAX * abs(k["kuh"]["max_drawdown"]) + RUNDUNG)
        zeilen.append(zeile)
    return pd.DataFrame(zeilen)
