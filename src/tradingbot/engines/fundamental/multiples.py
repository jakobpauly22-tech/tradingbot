"""Multiples als Perzentil-Rang innerhalb der Vergleichsgruppe (Entscheidung Jakob 03.11.2026, config/fundamental.yaml).

- Marktwert EK am Stichtag = Schlusskurs (letzter bis zum Stichtag) × ausstehende Aktien (SEC-Deckblatt, bekannt bis zum
  Stichtag, splitbereinigt). Plausibilisiert gegen den geprüften Streubesitz, fortgeschrieben mit dem Kurs: Streubesitz
  muss 30–130 % des Marktwerts betragen (wie im Index-Nachbau); ohne Streubesitz nur 0,5 Mrd. bis 10 Bio. USD. Sonst
  kein Marktwert → keine Multiples, gezählt.
- Unternehmenswert EV = Marktwert EK + kurz- und langfristige Finanzschulden − Zahlungsmittel (Jahr t). Negativer EV
  wird markiert; EBIT/EV ist dann nicht sinnvoll und entfällt.
- E/P = Jahresüberschuss_t / Marktwert EK; EBIT/EV = EBIT_t / EV. Kehrwerte statt KGV und EV/EBIT, damit negative
  Gewinne und das 1/X-Problem nicht stören (wissen/01, Abschnitt 9).
- Vergleichsgruppe: zweistellige SIC (Major Group) mit mindestens 5 Firmen mit Wert, sonst SIC-Division.
  Vorher Kappung auf das 1./99. Perzentil über das ganze Universum am Stichtag. Höherer Rang = günstiger.
"""
from __future__ import annotations

import pandas as pd

from tradingbot.daten.abdeckung import STREUBESITZ_MAX, STREUBESITZ_MIN
from tradingbot.daten.index_nachbau import STREUBESITZ_ANTEIL_MAX, STREUBESITZ_ANTEIL_MIN

SIC_DIVISIONEN = [((100, 999), "A"), ((1000, 1499), "B"), ((1500, 1799), "C"), ((2000, 3999), "D"), ((4000, 4999), "E"),
                  ((5000, 5199), "F"), ((5200, 5999), "G"), ((6000, 6799), "H"), ((7000, 8999), "I"), ((9100, 9999), "J")]


def sic_division(sic: int | None) -> str | None:
    if sic is None:
        return None
    for (a, b), buchstabe in SIC_DIVISIONEN:
        if a <= sic <= b:
            return buchstabe
    return None


def marktwert_am(stichtag, schluss: pd.Series, aktien: pd.Series, streubesitz: pd.DataFrame | None) -> tuple[float | None, str | None]:
    """Marktwert EK am Stichtag und ggf. Grund, warum keiner vorliegt.

    `schluss`: splitbereinigte Schlusskurse; `aktien`: Aktienzahl splitbereinigt, Index = bekannt ab;
    `streubesitz`: geprüfte Werte (Spalten wert, filed; Index = Messtag) oder None.
    """
    tag = pd.Timestamp(stichtag)
    kurse = schluss.loc[:tag].dropna()
    if kurse.empty:
        return None, "kein Kurs bis zum Stichtag"
    bekannt = aktien.loc[:tag].dropna()
    if bekannt.empty:
        return None, "keine Aktienzahl bekannt"
    mw = float(kurse.iloc[-1]) * float(bekannt.iloc[-1])
    if streubesitz is not None and len(streubesitz):
        sb = streubesitz[(streubesitz["filed"] + pd.Timedelta(days=1)) <= tag]
        if len(sb):
            e = sb.index[-1]
            vorher = schluss.loc[:e].dropna()
            if len(vorher):
                fort = float(sb["wert"].iloc[-1]) * float(kurse.iloc[-1]) / float(vorher.iloc[-1])
                anteil = fort / mw if mw > 0 else float("inf")
                if not STREUBESITZ_ANTEIL_MIN <= anteil <= STREUBESITZ_ANTEIL_MAX:
                    return None, f"Streubesitz {anteil:.0%} des Marktwerts (Aktienzahl unplausibel)"
                return mw, None
    if not STREUBESITZ_MIN <= mw <= STREUBESITZ_MAX:
        return None, f"Marktwert {mw/1e9:.2f} Mrd. USD unplausibel"
    return mw, None


def multiples(t: pd.DataFrame, marktwert_ek: float | None) -> dict:
    """E/P und EBIT/EV aus dem Jahresabschluss t (Zeile 0) und dem Marktwert am Stichtag."""
    if marktwert_ek is None or t.empty:
        return {"ep": None, "ebit_ev": None, "ev": None, "ev_negativ": False}
    w = lambda n: (None if n not in t.columns or pd.isna(t[n].iloc[0]) else float(t[n].iloc[0]))  # noqa: E731
    ep = w("jahresueberschuss") / marktwert_ek if w("jahresueberschuss") is not None else None
    lfs, kfs, cash = w("langfristige_finanzschulden"), w("kurzfristige_finanzschulden"), w("zahlungsmittel")
    ev = marktwert_ek + (lfs or 0.0) + (kfs or 0.0) - (cash or 0.0) if lfs is not None else None
    ev_negativ = ev is not None and ev <= 0
    ebit = w("operatives_ergebnis")
    ebit_ev = ebit / ev if ebit is not None and ev is not None and not ev_negativ else None
    return {"ep": ep, "ebit_ev": ebit_ev, "ev": ev, "ev_negativ": ev_negativ}


def perzentil_raenge(tabelle: pd.DataFrame, spalten=("ep", "ebit_ev"), *, min_firmen: int = 5, kappung=(0.01, 0.99)) -> pd.DataFrame:
    """Perzentil-Rang (0–1, höher = günstiger) je Multiple innerhalb der Vergleichsgruppe.

    `tabelle`: eine Zeile je Firma am Stichtag mit Spalte `sic` und den Multiples. Ergebnis: Spalten `rang_<multiple>`
    und `gruppe_<multiple>` (z.B. „SIC 28“ oder „Division D“). Kappung vor dem Rang auf das 1./99. Perzentil.
    """
    t = tabelle.copy()
    sic2 = t["sic"].map(lambda s: None if pd.isna(s) else int(s) // 100)
    division = t["sic"].map(lambda s: sic_division(None if pd.isna(s) else int(s)))
    for spalte in spalten:
        werte = t[spalte].astype(float)
        unten, oben = werte.quantile(kappung[0]), werte.quantile(kappung[1])
        gekappt = werte.clip(lower=unten, upper=oben)
        hat = gekappt.notna()
        groesse = sic2[hat].map(sic2[hat].value_counts())
        gruppe = pd.Series(None, index=t.index, dtype=object)
        gruppe[hat] = [f"SIC {s:02d}" if g >= min_firmen else f"Division {d}" for s, g, d in zip(sic2[hat], groesse, division[hat])]
        t[f"gruppe_{spalte}"] = gruppe
        t[f"rang_{spalte}"] = gekappt.groupby(gruppe).rank(pct=True)
    return t
