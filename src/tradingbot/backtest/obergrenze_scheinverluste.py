"""Obergrenze der Wirkung möglicher Scheinverluste aus unbereinigten Abspaltungen in Tiingo-Reihen (Teil c1,
Methodenwechsel nach dem dritten Lauf, Jakob 15.11.2026, docs/FUNDAMENTAL.md).

Idee: Jeder Kandidatentag gilt als vollständiger Scheinverlust, seine (negative) Tagesrendite wird auf 0 gesetzt. Die
Differenz der Jahresrendite gegenüber dem unveränderten Lauf ist eine Obergrenze für die Wirkung echter Abspaltungen,
solange diese in der Kandidatenmenge enthalten sind (gute Trefferquote des dritten Laufs).

Formeln:
- Gesamtrendite eines Titels r_t = (P_t + D_t − P_{t−1}) / P_{t−1} (kennzahlen.rendite.simple_return).
- Zwei-Tage-Rendite (1 + r_{t−1})(1 + r_t) − 1 wie Kriterium S1 im dritten Lauf.
- Buch: R'_t = R_t + Σ_i w_{i,t−1} · (−r_{i,t}) über neutralisierte Tage, w = Positionswert / Buchwert zum Vortagesschluss;
  W'_t = W'_{t−1} · (1 + R'_t). Näherung ohne Neusimulation (ohne Kosten- und Steuerwirkung, ohne geänderte
  Rebalancing-Entscheidungen).
- Jahresrendite geometrisch (CAGR), wissen/01, Abschnitt 5.
"""
from __future__ import annotations

import re

import pandas as pd

from tradingbot.kennzahlen.rendite import simple_return

S1 = -0.03
INDEX_SCHWELLE = -0.15

_ZEILE = re.compile(r"^\| (?P<ticker>[^|(]+?) \((?P<cik>\d+)\) \| (?P<name>[^|]*) \| (?P<von>\d{4}-\d{2}-\d{2})"
                    r"(?: bis (?P<bis>\d{4}-\d{2}-\d{2}))? \| (?P<rendite>[-+]?[\d.]+)% \|")


def lies_ereignisse(bericht: str) -> pd.DataFrame:
    """Ereignisse (Treffer und „unklar“) aus dem Bericht des dritten Laufs.
    Spalten: liste, ticker, cik, name, von, bis, rendite (gerundet wie im Bericht)."""
    zeilen, liste = [], None
    for zeile in bericht.splitlines():
        if zeile.startswith("## "):
            liste = "treffer" if zeile.startswith("## Treffer") else "unklar" if zeile.startswith("## Unklar") else None
            continue
        m = _ZEILE.match(zeile) if liste else None
        if m:
            von = pd.Timestamp(m["von"])
            zeilen.append({"liste": liste, "ticker": m["ticker"].strip(), "cik": int(m["cik"]), "name": m["name"].strip(),
                           "von": von, "bis": pd.Timestamp(m["bis"]) if m["bis"] else von, "rendite": float(m["rendite"]) / 100})
    return pd.DataFrame(zeilen, columns=["liste", "ticker", "cik", "name", "von", "bis", "rendite"])


def gesamtrendite(kurse: pd.DataFrame) -> pd.Series:
    k = kurse.sort_index()
    dividende = k["dividende"] if "dividende" in k.columns else 0.0
    return simple_return(k["close"].shift(1), k["close"], dividende)


def kandidatentage(kurse: pd.DataFrame, von, bis, schwelle: float = S1) -> pd.Series:
    """Zu neutralisierende Tage eines Ereignisses: Tage in [von, bis] mit Gesamtrendite ≤ Schwelle ohne Split oder Ende
    eines Zwei-Tage-Fensters ≤ Schwelle (beide Tage ohne Split; dann zählen beide Tage des Fensters). Nur negative
    Renditen. Ergebnis: Tag → gemessene Rendite."""
    k = kurse.sort_index()
    r = gesamtrendite(k)
    split = k["split"].fillna(0) if "split" in k.columns else pd.Series(0.0, index=k.index)
    ohne_split = split == 0
    zwei = (1 + r) * (1 + r.shift(1)) - 1
    im_fenster = (r.index >= pd.Timestamp(von)) & (r.index <= pd.Timestamp(bis))
    einzeln = (r <= schwelle) & ohne_split & im_fenster
    paar = (zwei <= schwelle) & ohne_split & ohne_split.shift(1, fill_value=True) & im_fenster
    tage = set(r.index[einzeln]) | set(r.index[paar])
    pos = {d: i for i, d in enumerate(r.index)}
    tage |= {r.index[pos[d] - 1] for d in r.index[paar] if pos[d] > 0}
    auswahl = r.loc[sorted(tage)]
    return auswahl[auswahl < 0]


def schlechteste_rendite(kurse: pd.DataFrame, von, bis) -> float:
    """Schlechteste Tages- oder Zwei-Tage-Gesamtrendite im Ereignisfenster (wie „schlechteste“ im Bericht)."""
    r = gesamtrendite(kurse)
    zwei = (1 + r) * (1 + r.shift(1)) - 1
    fenster = (r.index >= pd.Timestamp(von)) & (r.index <= pd.Timestamp(bis))
    return float(min(r[fenster].min(), zwei[fenster].min()))


def neutralisiere(kurse: pd.DataFrame, tage) -> pd.DataFrame:
    """Kursreihe, deren Gesamtrendite an `tage` genau 0 ist: Dividende = Vortagesschluss − Schluss. Schlusskurse (und
    damit Marktwerte) bleiben unverändert."""
    k = kurse.sort_index().copy()
    if "dividende" not in k.columns:
        k["dividende"] = 0.0
    vortag = k["close"].shift(1)
    tage = pd.DatetimeIndex([t for t in tage if t in k.index])
    k.loc[tage, "dividende"] = (vortag - k["close"]).loc[tage]
    return k


def bestand_zum_vortag(trades: pd.DataFrame, tage: pd.DatetimeIndex) -> pd.DataFrame:
    """Stückzahl je Titel am Ende des Vortags (Tage × Titel) aus der Trade-Liste (datum, ticker, richtung, stueck)."""
    t = trades.copy()
    t["datum"] = pd.to_datetime(t["datum"])
    t["menge"] = t["richtung"] * t["stueck"]
    je_tag = t.pivot_table(index="datum", columns="ticker", values="menge", aggfunc="sum").fillna(0.0)
    tagesende = je_tag.reindex(je_tag.index.union(tage)).fillna(0.0).cumsum().reindex(tage)
    return tagesende.shift(1).fillna(0.0)


def korrigierte_werte(werte: pd.Series, korrektur: pd.Series) -> pd.Series:
    """W'_t = W'_{t−1} · (1 + R_t + k_t) mit R_t = W_t / W_{t−1} − 1 (ohne Einzahlungen) und k_t aus `korrektur`."""
    w = werte.sort_index()
    r = w.pct_change().fillna(0.0) + korrektur.reindex(w.index).fillna(0.0)
    return w.iloc[0] * (1 + r).cumprod()
