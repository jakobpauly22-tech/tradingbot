"""Auswertung der Kursabdeckung im Universum (Rückmeldung Jakob 03.11.2026).

Zwei Fälle werden getrennt:
1. Nicht kaufbar: Eine Firma hat am Auswahltag (Rebalancing-Stichtag) keine gültige Kursreihe
   (kursquellen.pruefe_kursreihe) für keine ihrer Aktiengattungen. Sie kann nicht ins Portfolio. Ausgewiesen je
   Stichtag: Anzahl (Firmen und Gattungen) und Indexgewicht; Gattungen einer Firma zählen beim Gewicht einmal.
2. Rückfall-Regel: Eine gehaltene Aktie verliert später ihre Kurse (gültige Reihe endet mit dem Indexabgang,
   z.B. Übernahme oder Insolvenz). Dann greift delisting.delisting_rendite. Ausgewiesen je Jahr mit Grund.

Indexgewicht: Börsenwert des Streubesitzes laut Deckblatt der SEC-Berichte (dei:EntityPublicFloat, point-in-time,
jüngster bis zum Stichtag bekannte Wert). Er ist auch für Titel ohne gültige Kurse vorhanden und kommt der
Streubesitz-Gewichtung des S&P 500 nahe. Abweichung: Wert zum Stichtag des Deckblatts (meist Ende Q2 des Vorjahres),
nicht tagesaktuell.
Schwelle: Liegt das Gewicht der nicht kaufbaren Titel im investierbaren Universum (ohne Finanzwerte) über 2 %, wird
das vor dem ersten Backtest mit Jakob besprochen.
"""
from __future__ import annotations

import pandas as pd

SCHWELLE_GEWICHT = 0.02
STREUBESITZ = {"art": "letzter", "einheit": "USD", "konzepte": ["dei:EntityPublicFloat"]}
# Plausibilitätsbereich wie bei der Börsenwert-Prüfung der Kurse (kursquellen.plausibel). Die SEC-Rohdaten enthalten
# grob falsche Streubesitzwerte (z.B. eBay 3·10¹⁹ USD, mehrere Firmen pauschal 10¹⁸ USD, Werte in Tausend statt USD,
# Nullen bei Tochtergesellschaften nach Übernahmen): rund 1,7 % aller Meldungen der Universums-Firmen. Werte außerhalb
# gelten als fehlend; es zählt der jüngste plausible, zum Stichtag bekannte Wert. Nichts wird umgerechnet.
STREUBESITZ_MIN = 5e8
STREUBESITZ_MAX = 1e13


def streubesitz_am(reihe: pd.DataFrame, stichtag) -> float | None:
    """Jüngster plausible Streubesitzwert, der am Stichtag bekannt war (Handelstag nach `filed`).

    `reihe`: Ergebnis von sec.kennzahl_jahreswerte(..., STREUBESITZ, ...) mit Spalten wert, filed; Index = Datum des Werts.
    """
    if reihe is None or len(reihe) == 0:
        return None
    tag = pd.Timestamp(stichtag)
    bekannt = reihe[((reihe["filed"] + pd.Timedelta(days=1)) <= tag) & reihe["wert"].between(STREUBESITZ_MIN, STREUBESITZ_MAX)]
    return float(bekannt["wert"].iloc[-1]) if len(bekannt) else None


def rebalancing_stichtage(von="2012-01-01", bis="2024-12-31", haeufigkeit="QS") -> pd.DatetimeIndex:
    """Erster Werktag je Quartal im Entwicklungszeitraum (Tresor ab 2025 bleibt zu)."""
    anfaenge = pd.date_range(von, bis, freq=haeufigkeit)
    return pd.DatetimeIndex([pd.bdate_range(a, a + pd.Timedelta(days=7))[0] for a in anfaenge])


def nicht_kaufbar_je_stichtag(mitglieder_fn, gueltig: pd.Series, gewicht_fn, finanzwert_fn, stichtage, firma_fn=None) -> pd.DataFrame:
    """Je Stichtag Anzahl und Gewicht der Mitglieder ohne gültige Kursreihe.

    mitglieder_fn(stichtag) → DataFrame der Mitgliedschaften (Index = Mitgliedschafts-Nr., eine je Aktiengattung)
    gueltig: bool je Mitgliedschafts-Nr. (fehlend = nicht gültig)
    gewicht_fn(nr, stichtag) → Streubesitz der Firma in USD oder None; finanzwert_fn(nr, stichtag) → True/False/None
    firma_fn(nr) → Firmenschlüssel (CIK). Gattungen derselben Firma (GOOG/GOOGL, FOX/FOXA …) zählen beim Gewicht
    einmal; die Firma gilt als kaufbar, wenn mindestens eine Gattung eine gültige Reihe hat (Jakob, 03.11.2026).
    """
    firma_fn = firma_fn or (lambda nr: nr)
    zeilen = []
    for tag in stichtage:
        nrn = list(mitglieder_fn(tag).index)
        gattungen = pd.DataFrame({"firma": [firma_fn(n) for n in nrn], "ok": [bool(gueltig.get(n, False)) for n in nrn]}, index=nrn)
        firmen = gattungen.groupby("firma", sort=False).agg(ok=("ok", "any"), nr=("ok", lambda x: x.index[0]))
        gewicht = pd.Series([gewicht_fn(n, tag) for n in firmen["nr"]], index=firmen.index, dtype=float)
        finanz = pd.Series([finanzwert_fn(n, tag) for n in firmen["nr"]], index=firmen.index, dtype=object)
        ok = firmen["ok"]
        investierbar = finanz.map(lambda f: f is False)
        zeile = {"stichtag": tag.date(), "mitglieder": len(nrn), "firmen": len(firmen),
                 "gattungen_ohne_gueltige_kurse": int((~gattungen["ok"]).sum()),
                 "ohne_gueltige_kurse": int((~ok).sum()), "gewicht_ohne_kurse": _anteil(gewicht, ~ok),
                 "ohne_streubesitzwert": int(gewicht.isna().sum()),
                 "investierbar": int(investierbar.sum()), "investierbar_ohne_kurse": int((investierbar & ~ok).sum()),
                 "gewicht_investierbar_ohne_kurse": _anteil(gewicht[investierbar], ~ok[investierbar])}
        zeile["ueber_schwelle"] = zeile["gewicht_investierbar_ohne_kurse"] > SCHWELLE_GEWICHT
        zeilen.append(zeile)
    return pd.DataFrame(zeilen)


def gewerteter_beginn(tabelle: pd.DataFrame, schwelle: float = SCHWELLE_GEWICHT) -> pd.Timestamp | None:
    """Regel (Jakob 03.11.2026): erster Rebalancing-Stichtag, ab dem alle folgenden Stichtage unter `schwelle` nicht
    kaufbarem Gewicht im investierbaren Universum liegen. Ergebnis ist der Quartalsbeginn dieses Stichtags.

    `tabelle`: Ergebnis von nicht_kaufbar_je_stichtag (Spalten stichtag, gewicht_investierbar_ohne_kurse).
    Liegt schon der letzte Stichtag über der Schwelle, gibt es keinen Beginn (None).
    """
    t = tabelle.sort_values("stichtag").reset_index(drop=True)
    ueber = t.index[t["gewicht_investierbar_ohne_kurse"] > schwelle]
    erster = 0 if len(ueber) == 0 else ueber.max() + 1
    if erster >= len(t):
        return None
    return pd.Timestamp(t.loc[erster, "stichtag"]).to_period("Q").start_time


def _anteil(gewicht: pd.Series, maske: pd.Series) -> float:
    gesamt = gewicht.sum(skipna=True)
    return float(gewicht[maske].sum(skipna=True) / gesamt) if gesamt > 0 else float("nan")


def rueckfall_faelle(status: pd.DataFrame, gruende: dict) -> pd.DataFrame:
    """Gültige Reihen, die vor dem Ende der Daten aufhören (Delisting nach Indexabgang): je Jahr und Grund.

    status: Spalten index, gueltig, letzter_kurs (aus kursstatus.csv); gruende: Mitgliedschafts-Nr. → Grund.
    """
    s = status[status["gueltig"].astype(bool)].copy()
    s["letzter_kurs"] = pd.to_datetime(s["letzter_kurs"])
    datenende = s["letzter_kurs"].max()
    endet = s[s["letzter_kurs"] < datenende - pd.Timedelta(days=30)].copy()
    endet["jahr"] = endet["letzter_kurs"].dt.year
    endet["grund"] = endet["index"].map(lambda n: gruende.get(n, "unbekannt"))
    return endet.groupby(["jahr", "grund"]).size().unstack(fill_value=0)
