"""Nachbau eines nach Börsenwert gewichteten Total-Return-Index aus dem point-in-time-Universum.

Zweck (Entscheidung Jakob 02.11.2026): Benchmark „S&P 500 ohne Finanzwerte“ (SIC 6000–6999, point-in-time), für den
es keine frei verfügbare Historie gibt. Derselbe Nachbau ohne Ausschluss dient als Gegenprobe gegen den offiziellen
S&P 500 Total Return; die Abweichung zeigt die Qualität von Universum und Kursdaten.

Formel (Laspeyres-Kettenindex, wie bei Indexanbietern):
    w_i,t   = MW_i,t−1 / Σ_j MW_j,t−1              über die Mitglieder am Tag t (Gewichte vom Vortag, kein Look-ahead)
    r_i,t   = (C_i,t + D_i,t − C_i,t−1) / C_i,t−1   Gesamtrendite inklusive Dividende (simple_return)
    I_t     = I_t−1 · (1 + Σ_i w_i,t · r_i,t)
Marktwert MW = splitbereinigter Schlusskurs × splitbereinigte ausstehende Aktien (SEC, point-in-time).
Abweichung zum Original: S&P gewichtet nach Streubesitz (float-adjusted), wir nach allen ausstehenden Aktien.
Quelle Formel Gesamtrendite: wissen/02_Kapitalmarkttheorie_Portfolio_Anleihen.md, Abschnitt 2; referenz.simple_return.
"""
from __future__ import annotations

import pandas as pd

from tradingbot.kennzahlen.rendite import simple_return


def aktien_splitbereinigt(aktien: pd.Series, splits: pd.Series) -> pd.Series:
    """Gemeldete Aktienzahl auf die heutige Split-Basis der Kurse bringen.

    Ein Wert vom Datum d wird mit allen Split-Faktoren nach d multipliziert (Yahoo-/Tiingo-Kurse sind rückwirkend
    durch diese Faktoren geteilt). `splits`: Faktor am Split-Tag, sonst 0 oder fehlend.
    """
    faktoren = splits[splits.fillna(0) > 0]
    if faktoren.empty or aktien.empty:
        return aktien.astype(float)
    return pd.Series({d: float(a) * float(faktoren[faktoren.index > d].prod()) for d, a in aktien.items()}).sort_index()


def marktwert_index(renditen: pd.DataFrame, marktwerte: pd.DataFrame, mitglied: pd.DataFrame, basis: float = 100.0) -> pd.DataFrame:
    """Kettenindex aus Tagesrenditen und Marktwerten (Tage × Titel); `mitglied` bool (Tage × Titel).

    Gewichte aus den Marktwerten des Vortags, nur für Titel, die am Tag t Mitglied sind und für die eine Rendite
    vorliegt. Ergebnis: Spalten index, abdeckung (Anteil der Mitglieder mit Rendite und Vortags-Marktwert).
    """
    mw_vortag = marktwerte.shift(1)
    nutzbar = mitglied & renditen.notna() & mw_vortag.notna() & (mw_vortag > 0)
    gewicht_roh = mw_vortag.where(nutzbar)
    gewichte = gewicht_roh.div(gewicht_roh.sum(axis=1), axis=0)
    r_index = (gewichte * renditen).sum(axis=1, min_count=1).fillna(0.0)
    r_index.iloc[0] = 0.0
    abdeckung = nutzbar.sum(axis=1) / mitglied.sum(axis=1).where(mitglied.sum(axis=1) > 0)
    return pd.DataFrame({"index": basis * (1 + r_index).cumprod(), "abdeckung": abdeckung})


# --- Abnahme der Gegenprobe (Entscheidung Jakob 03.11.2026, docs/DATENQUALITAET.md) ----------------------------
# Nachbau ohne Ausschluss gegen den offiziellen S&P 500 Total Return (^SP500TR), beide in USD, gemeinsame Handelstage.
# Wird ein Kriterium verfehlt: erst Ursachen suchen und mit Jakob besprechen, NICHT nachjustieren.
ABNAHME_KORRELATION_MIN = 0.99          # Korrelation der Tagesrenditen
ABNAHME_JAHRESABWEICHUNG_MAX = 0.01     # Abweichung der Jahresrenditen je Kalenderjahr (1 Prozentpunkt)
ABNAHME_ANNUALISIERT_MAX = 0.005        # Abweichung der annualisierten Rendite 2012–2024 (0,5 Prozentpunkte)
ABNAHME_ZEITRAUM = ("2012-01-01", "2024-12-31")


def abnahme_gegenprobe(nachbau: pd.Series, referenz: pd.Series, zeitraum=ABNAHME_ZEITRAUM) -> dict:
    """Prüft den Nachbau gegen den Referenzindex nach den drei Abnahmekriterien.

    Formeln: Tagesrendite r_t = I_t / I_{t−1} − 1 (gemeinsame Handelstage); Jahresrendite = Indexstand am letzten
    gemeinsamen Handelstag des Jahres / Stand am letzten des Vorjahres − 1 (erstes Jahr ab dem ersten Tag);
    annualisiert geometrisch (CAGR, wissen/01 Abschnitt 5 und „Bezug zum Trading-Bot“).
    Ergebnis: Werte je Kriterium, Grenzen, `bestanden` je Kriterium und gesamt sowie die Jahrestabelle.
    """
    from tradingbot.kennzahlen.performance import cagr

    von, bis = (pd.Timestamp(z) for z in zeitraum)
    beide = pd.concat({"nachbau": nachbau, "referenz": referenz}, axis=1).dropna().loc[von:bis]
    renditen = beide.pct_change().dropna()
    korrelation = float(renditen["nachbau"].corr(renditen["referenz"]))
    jahresende = beide.groupby(beide.index.year).last()
    start = beide.iloc[[0]].set_axis([beide.index[0].year - 1])
    jahre = pd.concat([start, jahresende]).pct_change().dropna()
    jahre["abweichung"] = jahre["nachbau"] - jahre["referenz"]
    annualisiert = cagr(beide["nachbau"]) - cagr(beide["referenz"])
    kriterien = {
        "korrelation": {"wert": korrelation, "grenze": f">= {ABNAHME_KORRELATION_MIN}", "bestanden": korrelation >= ABNAHME_KORRELATION_MIN},
        "jahresabweichung_max": {"wert": float(jahre["abweichung"].abs().max()), "grenze": f"<= {ABNAHME_JAHRESABWEICHUNG_MAX}",
                                 "bestanden": bool((jahre["abweichung"].abs() <= ABNAHME_JAHRESABWEICHUNG_MAX + 1e-12).all())},
        "annualisiert_abweichung": {"wert": float(annualisiert), "grenze": f"|x| <= {ABNAHME_ANNUALISIERT_MAX}",
                                    "bestanden": abs(annualisiert) <= ABNAHME_ANNUALISIERT_MAX + 1e-12},
    }
    return {"kriterien": kriterien, "bestanden": all(k["bestanden"] for k in kriterien.values()),
            "jahre": jahre, "tage": len(beide), "zeitraum": (beide.index[0].date(), beide.index[-1].date())}


def gesamtrenditen(kurse: dict[str, pd.DataFrame], tage: pd.DatetimeIndex) -> pd.DataFrame:
    """Tägliche Gesamtrenditen je Titel (Tage × Titel); fehlende Tage bleiben leer (kein Auffüllen von Renditen)."""
    spalten = {}
    for titel, k in kurse.items():
        k = k.sort_index()
        r = simple_return(k["close"].shift(1), k["close"], k["dividende"])
        spalten[titel] = r.reindex(tage)
    return pd.DataFrame(spalten, index=tage)
