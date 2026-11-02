"""Bilanz-Scores aus point-in-time-Jahresabschlüssen (kennzahlen.abschluesse_am: Zeile 0 = Jahr t, 1 = t−1, 2 = t−2).

Jede Funktion gibt ein Dictionary zurück: Wert, Einzelbestandteile und `fehlend` (benötigte, aber fehlende Posten).
Fehlt ein benötigter Posten, ist der Score nicht berechenbar (Wert None) – es wird nichts geraten.
Quellen: Piotroski (2000), Altman (1968; Z'' Altman 2000), Beneish (1999); wissen/04 Abschnitt 8 (Altman), wissen/08
(Accruals). Die Originalaufsätze stehen nicht im Repository.
"""
from __future__ import annotations

import math

import pandas as pd


def _w(t: pd.DataFrame, name: str, jahr: int):
    """Wert der Kennzahl im Jahr t−jahr oder None."""
    if name not in t.columns or jahr >= len(t):
        return None
    v = t[name].iloc[jahr]
    return None if pd.isna(v) else float(v)


def _quotient(a, b):
    return None if a is None or b is None or b == 0 else a / b


def _brauche(t, posten: list[tuple[str, int]]) -> list[str]:
    return [f"{n}@t-{j}" if j else f"{n}@t" for n, j in posten if _w(t, n, j) is None]


# --- Piotroski F-Score -----------------------------------------------------------------------------
PIOTROSKI_SIGNALE = {
    # Signal: benötigte Posten (Name, Jahr t−j)
    "roa": [("jahresueberschuss", 0), ("bilanzsumme", 1)],
    "cfo": [("operativer_cashflow", 0), ("bilanzsumme", 1)],
    "delta_roa": [("jahresueberschuss", 0), ("bilanzsumme", 1), ("jahresueberschuss", 1), ("bilanzsumme", 2)],
    "accrual": [("operativer_cashflow", 0), ("jahresueberschuss", 0), ("bilanzsumme", 1)],
    "delta_lever": [("langfristige_finanzschulden", 0), ("langfristige_finanzschulden", 1), ("bilanzsumme", 0),
                    ("bilanzsumme", 1), ("bilanzsumme", 2)],
    "delta_liquid": [("umlaufvermoegen", 0), ("kurzfristige_verbindlichkeiten", 0), ("umlaufvermoegen", 1),
                     ("kurzfristige_verbindlichkeiten", 1)],
    "eq_offer": [("gewichtete_aktien", 0), ("gewichtete_aktien", 1)],
    "delta_margin": [("bruttoergebnis", 0), ("umsatz", 0), ("bruttoergebnis", 1), ("umsatz", 1)],
    "delta_turn": [("umsatz", 0), ("bilanzsumme", 1), ("umsatz", 1), ("bilanzsumme", 2)],
}
PIOTROSKI_MINDESTSIGNALE = 7      # Entscheidung Jakob 02.11.2026 (config/fundamental.yaml)


def piotroski(t: pd.DataFrame, mindestsignale: int = PIOTROSKI_MINDESTSIGNALE) -> dict:
    """Piotroski F-Score (0–9), neun binäre Signale, jedes einzeln berechnet, soweit seine Posten vorliegen.

    Ursprünglich für Value-Aktien entwickelt (Firmen mit hohem Buchwert-Markt-Verhältnis, Piotroski 2000); hier dient er
    als allgemeiner Qualitätsfilter für das ganze investierbare Universum (Entscheidung Jakob, Filter F ≤ 3 → raus).

    Rentabilität:  ROA = JÜ_t / BS_{t−1} > 0;  CFO = CF_t / BS_{t−1} > 0;  ΔROA = ROA_t − ROA_{t−1} > 0;
                   ACCRUAL: CFO > ROA
    Finanzierung:  ΔLEVER = LFS_t/Ø(BS_t, BS_{t−1}) − LFS_{t−1}/Ø(BS_{t−1}, BS_{t−2}) ≤ 0 (keine Zunahme der Verschuldung;
                   Piotroski wertet nur eine Zunahme als negatives Signal, schuldenfreie Firmen zählen daher als 1);
                   ΔLIQUID: Liquidität 3. Grades (UV/kfr. Verbindlichkeiten) gestiegen;
                   EQ_OFFER: keine neuen Aktien – Näherung über die gewichtete Aktienzahl (t ≤ t−1), da die SEC-Daten
                   die Ausgabe von Stammaktien nicht einheitlich melden
    Effizienz:     ΔMARGIN: Bruttomarge gestiegen;  ΔTURN: Kapitalumschlag Umsatz_t/BS_{t−1} gestiegen
    Fehlende Signale (Entscheidung Jakob 02.11.2026): alle 9 → `wert`; 7 oder 8 → auf 9 Punkte hochgerechnet
    (`wert_hochgerechnet` = Punkte · 9 / Anzahl, `hochgerechnet` = True); weniger → kein Wert, der Filter wird übersprungen.
    """
    signale, zwischen, fehlend = {}, {}, []
    w = lambda n, j: _w(t, n, j)  # noqa: E731
    for name, posten in PIOTROSKI_SIGNALE.items():
        luecken = _brauche(t, posten)
        if luecken:
            fehlend += [f"{name}:{x}" for x in luecken]
            continue
        try:
            if name == "roa":
                zwischen["roa"] = w("jahresueberschuss", 0) / w("bilanzsumme", 1); signale[name] = int(zwischen["roa"] > 0)
            elif name == "cfo":
                zwischen["cfo"] = w("operativer_cashflow", 0) / w("bilanzsumme", 1); signale[name] = int(zwischen["cfo"] > 0)
            elif name == "delta_roa":
                roa, roa_vj = w("jahresueberschuss", 0) / w("bilanzsumme", 1), w("jahresueberschuss", 1) / w("bilanzsumme", 2)
                zwischen.update(roa=roa, roa_vj=roa_vj); signale[name] = int(roa > roa_vj)
            elif name == "accrual":
                signale[name] = int(w("operativer_cashflow", 0) / w("bilanzsumme", 1) > w("jahresueberschuss", 0) / w("bilanzsumme", 1))
            elif name == "delta_lever":
                lever = w("langfristige_finanzschulden", 0) / ((w("bilanzsumme", 0) + w("bilanzsumme", 1)) / 2)
                lever_vj = w("langfristige_finanzschulden", 1) / ((w("bilanzsumme", 1) + w("bilanzsumme", 2)) / 2)
                zwischen.update(lever=lever, lever_vj=lever_vj); signale[name] = int(lever <= lever_vj)
            elif name == "delta_liquid":
                liquid = w("umlaufvermoegen", 0) / w("kurzfristige_verbindlichkeiten", 0)
                liquid_vj = w("umlaufvermoegen", 1) / w("kurzfristige_verbindlichkeiten", 1)
                zwischen.update(liquid=liquid, liquid_vj=liquid_vj); signale[name] = int(liquid > liquid_vj)
            elif name == "eq_offer":
                signale[name] = int(w("gewichtete_aktien", 0) <= w("gewichtete_aktien", 1))
            elif name == "delta_margin":
                marge, marge_vj = w("bruttoergebnis", 0) / w("umsatz", 0), w("bruttoergebnis", 1) / w("umsatz", 1)
                zwischen.update(marge=marge, marge_vj=marge_vj); signale[name] = int(marge > marge_vj)
            elif name == "delta_turn":
                turn, turn_vj = w("umsatz", 0) / w("bilanzsumme", 1), w("umsatz", 1) / w("bilanzsumme", 2)
                zwischen.update(turn=turn, turn_vj=turn_vj); signale[name] = int(turn > turn_vj)
        except ZeroDivisionError:
            fehlend.append(f"{name}:Division durch null")
    n = len(signale)
    punkte = sum(signale.values())
    return {"wert": punkte if n == 9 else None,
            "wert_hochgerechnet": punkte * 9 / n if n >= mindestsignale else None,
            "hochgerechnet": mindestsignale <= n < 9, "anzahl_signale": n,
            "signale": signale, "zwischenwerte": zwischen, "fehlend": fehlend}


# --- Altman Z und Z'' ------------------------------------------------------------------------------
ALTMAN_1968 = {"gewichte": (1.2, 1.4, 3.3, 0.6, 1.0), "gefahr": 1.81, "sicher": 2.99}
ALTMAN_Z2 = {"gewichte": (6.56, 3.26, 6.72, 1.05), "gefahr": 1.10, "sicher": 2.60}


def altman(t: pd.DataFrame, *, industrie: bool, marktwert_ek: float | None = None) -> dict:
    """Altman Z (1968, verarbeitendes Gewerbe SIC 2000–3999) oder Z'' (übrige Firmen).

    Z   = 1,2·X1 + 1,4·X2 + 3,3·X3 + 0,6·X4 + 1,0·X5   Zonen: < 1,81 Gefahr, > 2,99 sicher (wissen/04, Abschnitt 8)
    Z'' = 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4         Zonen: < 1,10 Gefahr, > 2,60 sicher (Altman 2000)
    X1 = (UV − kfr. Verbindlichkeiten)/BS, X2 = Gewinnrücklagen/BS, X3 = EBIT/BS, X5 = Umsatz/BS;
    X4 = Marktwert EK (point-in-time am Stichtag) / Buchwert Verbindlichkeiten (Z) bzw. Buchwert EK / Verbindlichkeiten (Z'').
    Alle Werte aus dem Jahr t (Stichtagsbilanz des letzten Geschäftsjahres).
    """
    noetig = [("umlaufvermoegen", 0), ("kurzfristige_verbindlichkeiten", 0), ("gewinnruecklagen", 0), ("operatives_ergebnis", 0),
              ("bilanzsumme", 0), ("verbindlichkeiten", 0)]
    noetig += [("umsatz", 0)] if industrie else [("eigenkapital_inkl_minderheiten", 0)]
    fehlend = _brauche(t, noetig) + (["marktwert_ek"] if industrie and marktwert_ek is None else [])
    if fehlend:
        return {"wert": None, "variante": "Z" if industrie else "Z''", "fehlend": fehlend}
    w = lambda n: _w(t, n, 0)  # noqa: E731
    bs = w("bilanzsumme")
    x1 = _quotient(w("umlaufvermoegen") - w("kurzfristige_verbindlichkeiten"), bs)
    x2 = _quotient(w("gewinnruecklagen"), bs)
    x3 = _quotient(w("operatives_ergebnis"), bs)
    if industrie:
        x4 = _quotient(marktwert_ek, w("verbindlichkeiten"))
        x5 = _quotient(w("umsatz"), bs)
        x = (x1, x2, x3, x4, x5)
        modell = ALTMAN_1968
    else:
        x4 = _quotient(w("eigenkapital_inkl_minderheiten"), w("verbindlichkeiten"))
        x = (x1, x2, x3, x4)
        modell = ALTMAN_Z2
    if any(v is None for v in x):
        return {"wert": None, "variante": "Z" if industrie else "Z''", "fehlend": ["Division durch null"]}
    z = sum(g * v for g, v in zip(modell["gewichte"], x))
    zone = "gefahr" if z < modell["gefahr"] else "sicher" if z > modell["sicher"] else "grau"
    return {"wert": z, "variante": "Z" if industrie else "Z''", "zone": zone, "x": x, "fehlend": []}


# --- Beneish M-Score -------------------------------------------------------------------------------
BENEISH = {"konstante": -4.84, "dsri": 0.920, "gmi": 0.528, "aqi": 0.404, "sgi": 0.892, "depi": 0.115, "sgai": -0.172,
           "tata": 4.679, "lvgi": -0.327}


def beneish(t: pd.DataFrame) -> dict:
    """Beneish M-Score, Modell mit acht Variablen (Beneish 1999); M > −1,78 gilt als Manipulationsverdacht (config).

    M = −4,84 + 0,920·DSRI + 0,528·GMI + 0,404·AQI + 0,892·SGI + 0,115·DEPI − 0,172·SGAI + 4,679·TATA − 0,327·LVGI
    DSRI = (Ford_t/Ums_t)/(Ford_{t−1}/Ums_{t−1});  GMI = Marge_{t−1}/Marge_t;
    AQI  = [1 − (UV_t + SA_t)/BS_t] / [1 − (UV_{t−1} + SA_{t−1})/BS_{t−1}]   (SA = Sachanlagen netto);
    SGI  = Ums_t/Ums_{t−1};  DEPI = [Abs_{t−1}/(Abs_{t−1}+SA_{t−1})] / [Abs_t/(Abs_t+SA_t)];
    SGAI = (VVK_t/Ums_t)/(VVK_{t−1}/Ums_{t−1})  (VVK = Vertriebs- und Verwaltungskosten);
    LVGI = [(kfr. Verb._t + LFS_t)/BS_t] / [(kfr. Verb._{t−1} + LFS_{t−1})/BS_{t−1}];  TATA = (JÜ_t − CFO_t)/BS_t.
    """
    posten = ["forderungen", "umsatz", "bruttoergebnis", "umlaufvermoegen", "sachanlagen_netto", "bilanzsumme", "abschreibungen",
              "vertriebs_verwaltungskosten", "kurzfristige_verbindlichkeiten", "langfristige_finanzschulden"]
    fehlend = _brauche(t, [(p, j) for p in posten for j in (0, 1)] + [("jahresueberschuss", 0), ("operativer_cashflow", 0)])
    if fehlend:
        return {"wert": None, "variablen": {}, "fehlend": fehlend}
    w = lambda n, j=0: _w(t, n, j)  # noqa: E731
    try:
        v = {
            "dsri": (w("forderungen") / w("umsatz")) / (w("forderungen", 1) / w("umsatz", 1)),
            "gmi": (w("bruttoergebnis", 1) / w("umsatz", 1)) / (w("bruttoergebnis") / w("umsatz")),
            "aqi": (1 - (w("umlaufvermoegen") + w("sachanlagen_netto")) / w("bilanzsumme"))
                   / (1 - (w("umlaufvermoegen", 1) + w("sachanlagen_netto", 1)) / w("bilanzsumme", 1)),
            "sgi": w("umsatz") / w("umsatz", 1),
            "depi": (w("abschreibungen", 1) / (w("abschreibungen", 1) + w("sachanlagen_netto", 1)))
                    / (w("abschreibungen") / (w("abschreibungen") + w("sachanlagen_netto"))),
            "sgai": (w("vertriebs_verwaltungskosten") / w("umsatz")) / (w("vertriebs_verwaltungskosten", 1) / w("umsatz", 1)),
            "tata": (w("jahresueberschuss") - w("operativer_cashflow")) / w("bilanzsumme"),
            "lvgi": ((w("kurzfristige_verbindlichkeiten") + w("langfristige_finanzschulden")) / w("bilanzsumme"))
                    / ((w("kurzfristige_verbindlichkeiten", 1) + w("langfristige_finanzschulden", 1)) / w("bilanzsumme", 1)),
        }
    except ZeroDivisionError:
        return {"wert": None, "variablen": {}, "fehlend": ["Division durch null"]}
    if any(not math.isfinite(x) for x in v.values()):
        return {"wert": None, "variablen": v, "fehlend": ["nicht endlicher Wert"]}
    m = BENEISH["konstante"] + sum(BENEISH[k] * x for k, x in v.items())
    return {"wert": m, "variablen": v, "fehlend": []}


# --- Accruals -----------------------------------------------------------------------------------
def accruals_quote(t: pd.DataFrame) -> dict:
    """Accruals-Quote = (Jahresüberschuss − operativer Cashflow) / Bilanzsumme, Jahr t (wissen/08; Sloan 1996).

    Hohe Accruals (Gewinne ohne Cash) sagen niedrigere künftige Renditen voraus; im Score gilt: niedriger ist besser.
    """
    fehlend = _brauche(t, [("jahresueberschuss", 0), ("operativer_cashflow", 0), ("bilanzsumme", 0)])
    if fehlend:
        return {"wert": None, "fehlend": fehlend}
    q = _quotient(_w(t, "jahresueberschuss", 0) - _w(t, "operativer_cashflow", 0), _w(t, "bilanzsumme", 0))
    return {"wert": q, "fehlend": [] if q is not None else ["Division durch null"]}
