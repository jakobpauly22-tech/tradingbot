"""Multiples als Perzentil-Rang innerhalb der Vergleichsgruppe (Entscheidung Jakob 02.11.2026, config/fundamental.yaml).

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
    """Marktwert EK am Stichtag und ggf. Grund, warum keiner vorliegt (bisherige Rechnung, ohne Datenkorrektur Marktwert).

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
    grund = _unplausibel(mw, tag, kurse, schluss, streubesitz)
    return (None, grund) if grund else (mw, None)


def _unplausibel(mw: float, tag, kurse: pd.Series, schluss: pd.Series, streubesitz: pd.DataFrame | None,
                 fortschreibung=None) -> str | None:
    """Plausibilitätsprüfung gegen den Streubesitz (30–130 % des Marktwerts), ohne Streubesitz 0,5 Mrd. bis 10 Bio. USD.
    `fortschreibung(e)`: Korrekturfaktor K(e, Stichtag) für die Fortschreibung F_e · C_T / C_e (None = 1)."""
    if streubesitz is not None and len(streubesitz):
        sb = streubesitz[(streubesitz["filed"] + pd.Timedelta(days=1)) <= tag]
        if len(sb):
            e = sb.index[-1]
            vorher = schluss.loc[:e].dropna()
            if len(vorher):
                fort = float(sb["wert"].iloc[-1]) * float(kurse.iloc[-1]) / float(vorher.iloc[-1])
                if fortschreibung is not None:
                    fort *= fortschreibung(e)
                anteil = fort / mw if mw > 0 else float("inf")
                if not STREUBESITZ_ANTEIL_MIN <= anteil <= STREUBESITZ_ANTEIL_MAX:
                    return f"Streubesitz {anteil:.0%} des Marktwerts (Aktienzahl unplausibel)"
                return None
    if not STREUBESITZ_MIN <= mw <= STREUBESITZ_MAX:
        return f"Marktwert {mw/1e9:.2f} Mrd. USD unplausibel"
    return None


def marktwert_korrigiert(stichtag, kurse: pd.DataFrame, aktien: pd.DataFrame, streubesitz: pd.DataFrame | None, *,
                         ereignisse: pd.DataFrame | None = None, ersatz_fakten: pd.DataFrame | None = None,
                         max_alter_monate: int = 15, automatisch_einordnen: bool = False) -> dict:
    """Marktwert EK mit der Datenkorrektur Marktwert (Jakob 13.11.2026, docs/FUNDAMENTAL.md, Teil b).

        MW_T = C_T · A_d · Π_{e>d} f_e · K(d, T)        (daten/kapitalmassnahmen_historie.py)

    C_T: letzter splitbereinigter Schlusskurs bis T; A_d: Aktienzahl vom Messtag d; f_e: Faktoren der Kursreihe;
    K(d, T) = Π_{d<e≤T} s_e / f_e nimmt Abspaltungen zwischen d und T aus der Aktienzahl heraus.
    Aktienzahl: Deckblatt (`aktien`: Spalten wert, filed; Index = Messtag), wenn höchstens `max_alter_monate` alt (nach
    `filed`, gegen T); sonst Ersatz = jüngste gewichtete Basic-Zahl (aktienzahl.ersatz_aktienzahl, Messtag = filed),
    markiert „Ersatz“; ist auch der Ersatz zu alt oder fehlt er: kein Marktwert. Plausibilität gegen den Streubesitz wie
    bisher, dessen Fortschreibung ebenfalls mit K(e, T). Ungeklärte Ereignisse behalten den Kursfaktor und werden gemeldet.
    `automatisch_einordnen` (Betrieb): Ereignisse, die nicht in der Liste stehen, über das SEC-Verhältnis einordnen.
    Rückgabe: marktwert, grund, quelle (Deckblatt | Ersatz), aktien_filed, korrektur (K), ungeklaert (Liste).
    """
    from tradingbot.daten.kapitalmassnahmen_historie import korrektur
    from tradingbot.engines.fundamental.aktienzahl import ersatz_aktienzahl

    tag = pd.Timestamp(stichtag)
    ergebnis = {"marktwert": None, "grund": None, "quelle": None, "aktien_filed": None, "korrektur": 1.0, "ungeklaert": []}
    schluss = kurse["close"]
    kurse_bis = schluss.loc[:tag].dropna()
    if kurse_bis.empty:
        return {**ergebnis, "grund": "kein Kurs bis zum Stichtag"}
    splits = kurse["split"] if "split" in kurse.columns else None
    grenze = tag - pd.DateOffset(months=max_alter_monate)
    bekannt = aktien[(aktien["filed"] + pd.Timedelta(days=1)) <= tag].dropna(subset=["wert"]) if aktien is not None and len(aktien) else None
    wahl = None
    if bekannt is not None and len(bekannt):
        letzte = bekannt.sort_values("filed").iloc[-1]
        if letzte["filed"] >= grenze:
            wahl = (float(letzte["wert"]), pd.Timestamp(letzte.name), letzte["filed"], "Deckblatt")
    if wahl is None:
        e = ersatz_aktienzahl(ersatz_fakten, tag)
        if e is not None and e["filed"] >= grenze:
            wahl = (e["wert"], e["filed"], e["filed"], f"Ersatz (Basic, Periode bis {e['ende'].date()})")
        elif bekannt is not None and len(bekannt):
            return {**ergebnis, "grund": f"Aktienzahl älter als {max_alter_monate} Monate, kein aktueller Ersatz"}
        else:
            return {**ergebnis, "grund": "keine Aktienzahl bekannt" + ("" if e is None else f", Ersatz älter als {max_alter_monate} Monate")}
    wert, messtag, filed, quelle = wahl
    faktoren = splits[splits.fillna(0) > 0] if splits is not None else pd.Series(dtype=float)
    alle_nach = float(faktoren[faktoren.index > messtag].prod()) if len(faktoren) else 1.0
    fakten = ersatz_fakten if automatisch_einordnen else None
    k, ungeklaert = korrektur(splits, ereignisse, messtag, tag, fakten=fakten)
    mw = float(kurse_bis.iloc[-1]) * wert * alle_nach * k
    grund = _unplausibel(mw, tag, kurse_bis, schluss, streubesitz,
                         fortschreibung=lambda e: korrektur(splits, ereignisse, e, tag, fakten=fakten)[0])
    return {"marktwert": None if grund else mw, "grund": grund, "quelle": quelle, "aktien_filed": filed, "korrektur": k,
            "ungeklaert": ungeklaert}


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
