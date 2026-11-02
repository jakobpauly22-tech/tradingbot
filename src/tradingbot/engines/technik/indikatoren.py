"""Technische Indikatoren auf Tageskerzen (Spalten open, high, low, close).

Alle Funktionen nutzen nur Daten bis einschließlich Tag t (kein Blick nach vorn). Parameter in config/technik.yaml.
Quellen: Wilder, J. W. (1978): New Concepts in Technical Trading Systems (RSI, ATR, ADX, Wilder-Glättung);
Jegadeesh, N./Titman, S. (1993): Returns to Buying Winners and Selling Losers, Journal of Finance 48 (Momentum 12−1);
Donchian-Kanal (Price Channel) nach R. Donchian, Ausbruchsregel der „Turtle Traders“ (Faith 2007, Way of the Turtle).
Zusammenfassung: wissen/05_Asset_Management_und_Hedgefonds.md, Abschnitt „Technische Indikatoren“.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(werte: pd.Series, tage: int) -> pd.Series:
    """Einfacher gleitender Durchschnitt: SMA_t = (1/n) · Σ_{i=0}^{n−1} x_{t−i}; NaN, solange n Werte fehlen."""
    return werte.rolling(tage, min_periods=tage).mean()


def wilder_glaettung(werte: pd.Series, tage: int) -> pd.Series:
    """Wilder-Glättung (RMA): Start = Mittel der ersten n Werte, danach S_t = S_{t−1} + (x_t − S_{t−1}) / n.

    Entspricht einem exponentiellen Mittel mit α = 1/n (Wilder 1978). NaN-Werte am Anfang werden übersprungen.
    """
    x = werte.astype(float)
    ergebnis = pd.Series(np.nan, index=x.index)
    gueltig = x.dropna()
    if len(gueltig) < tage:
        return ergebnis
    start = gueltig.index[tage - 1]
    s = gueltig.iloc[:tage].mean()
    ergebnis.loc[start] = s
    for tag, wert in gueltig.iloc[tage:].items():
        s = s + (wert - s) / tage
        ergebnis.loc[tag] = s
    return ergebnis


def true_range(kerzen: pd.DataFrame) -> pd.Series:
    """TR_t = max(H_t − L_t, |H_t − C_{t−1}|, |L_t − C_{t−1}|); am ersten Tag H − L."""
    vorschluss = kerzen["close"].shift(1)
    spannen = pd.concat([kerzen["high"] - kerzen["low"], (kerzen["high"] - vorschluss).abs(), (kerzen["low"] - vorschluss).abs()], axis=1)
    return spannen.max(axis=1)


def atr(kerzen: pd.DataFrame, tage: int = 20) -> pd.Series:
    """Average True Range nach Wilder: ATR_t = Wilder-Glättung von TR über n Tage."""
    return wilder_glaettung(true_range(kerzen), tage)


def rsi(schluss: pd.Series, tage: int = 2) -> pd.Series:
    """Relative Strength Index nach Wilder: RSI = 100 − 100 / (1 + RS), RS = Ø Gewinn / Ø Verlust (Wilder-Glättung).

    Ø Verlust = 0 → RSI = 100; beide 0 → RSI = 50.
    """
    diff = schluss.diff()
    gewinn = wilder_glaettung(diff.clip(lower=0).iloc[1:], tage).reindex(schluss.index)
    verlust = wilder_glaettung((-diff).clip(lower=0).iloc[1:], tage).reindex(schluss.index)
    rs = gewinn / verlust
    wert = 100 - 100 / (1 + rs)
    wert[(verlust == 0) & (gewinn > 0)] = 100.0
    wert[(verlust == 0) & (gewinn == 0)] = 50.0
    return wert


def adx(kerzen: pd.DataFrame, tage: int = 14) -> pd.Series:
    """Average Directional Index nach Wilder.

        +DM_t = H_t − H_{t−1}, wenn > L_{t−1} − L_t und > 0, sonst 0;  −DM_t analog mit L_{t−1} − L_t
        +DI = 100 · RMA(+DM) / RMA(TR),  −DI = 100 · RMA(−DM) / RMA(TR)
        DX = 100 · |+DI − −DI| / (+DI + −DI),  ADX = RMA(DX)            (RMA = Wilder-Glättung über n Tage)
    """
    hoch, tief = kerzen["high"], kerzen["low"]
    auf, ab = hoch.diff(), -tief.diff()
    plus_dm = pd.Series(np.where((auf > ab) & (auf > 0), auf, 0.0), index=kerzen.index)
    minus_dm = pd.Series(np.where((ab > auf) & (ab > 0), ab, 0.0), index=kerzen.index)
    tr = true_range(kerzen)
    tr_g = wilder_glaettung(tr.iloc[1:], tage).reindex(kerzen.index)
    plus_di = 100 * wilder_glaettung(plus_dm.iloc[1:], tage).reindex(kerzen.index) / tr_g
    minus_di = 100 * wilder_glaettung(minus_dm.iloc[1:], tage).reindex(kerzen.index) / tr_g
    summe = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / summe
    dx[summe == 0] = 0.0                        # keine Bewegung: DX = 0; NaN in der Anlaufphase bleibt NaN
    return wilder_glaettung(dx, tage)


def momentum_12_1(schluss: pd.Series, monate: int = 12, ohne_letzte: int = 1) -> pd.Series:
    """Momentum 12−1 (Jegadeesh/Titman 1993): Rendite über die Monate M−12 bis M−2, der jüngste Monat M−1 wird ausgelassen.

        MOM(Tag t im Monat M) = C(Ende M−2) / C(Ende M−13) − 1
    Monatsende = letzter Handelstag des Kalendermonats mit Kurs. Der laufende Monat M zählt nie (nicht abgeschlossen).
    Ergebnis je Tag (im Monat konstant).
    """
    monatsende = schluss.groupby(schluss.index.to_period("M")).last()
    wert_monat = monatsende.shift(ohne_letzte) / monatsende.shift(monate) - 1
    # am Tag t gilt der Wert, der auf dem zuletzt abgeschlossenen Monat beruht: Monat(t) − 1 ist das jüngste Monatsende
    perioden = schluss.index.to_period("M")
    return pd.Series(wert_monat.shift(1).reindex(perioden).to_numpy(), index=schluss.index)


def donchian_hoch(hoch: pd.Series, tage: int) -> pd.Series:
    """Höchstes Hoch der letzten n Tage vor t (ohne Tag t): max(H_{t−n}, …, H_{t−1})."""
    return hoch.shift(1).rolling(tage, min_periods=tage).max()


def donchian_tief(tief: pd.Series, tage: int) -> pd.Series:
    """Tiefstes Tief der letzten n Tage vor t (ohne Tag t): min(L_{t−n}, …, L_{t−1})."""
    return tief.shift(1).rolling(tage, min_periods=tage).min()
