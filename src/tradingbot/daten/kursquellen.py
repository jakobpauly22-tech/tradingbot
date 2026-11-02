"""Kursquelle je Mitgliedschaft im Universum und Plausibilitätsprüfung der Kursreihe.

Regel (Entscheidung Jakob 02.11.2026, Survivorship-Schutz):
- Heute noch gelistet (CIK in der SEC-Tickerliste): yfinance mit dem passenden heutigen Ticker der Stammaktie.
- Nicht mehr gelistet: Tiingo. Den Tiingo-Ticker bestimmt die Tickerliste von Tiingo: gleicher (früherer) Ticker oder
  Ticker mit Insolvenz-Suffix „Q“, Kurse ab spätestens Beginn des relevanten Zeitraums und Ende passend zum
  Indexabgang. Es wird nicht geraten: ohne passenden Kandidaten bleibt die Quelle leer und wird gezählt.

Plausibilität: Börsenwert = Schlusskurs × ausstehende Aktien (SEC, point-in-time) muss für ein S&P-500-Mitglied
zwischen 0,5 Mrd. und 10 Bio. USD liegen. So fällt eine falsche Aktie (gleicher Ticker, andere Firma) auf.
"""
from __future__ import annotations

import re

import pandas as pd

AB = pd.Timestamp("2012-01-01")


def yahoo_ticker(ticker: str) -> str:
    """Yahoo schreibt Aktiengattungen mit Bindestrich: BRK.B → BRK-B."""
    return ticker.replace(".", "-").strip().split(" ")[0]


def _ist_stammaktie(ticker: str) -> bool:
    return not re.search(r"-(P[A-Z]?|W[S]?|U|R)$|\bPR[A-Z]?$", ticker)


def kursquelle(zeile, sec_ticker: dict[int, list[str]], tiingo_liste: pd.DataFrame | None) -> dict:
    """Bestimmt {quelle, symbol, hinweis} für eine Mitgliedschaft (Zeile aus lade_universum)."""
    if pd.isna(zeile["cik"]):
        return {"quelle": None, "symbol": None, "kurs_ab": pd.NaT, "quelle_hinweis": "keine CIK"}
    eigene = [yahoo_ticker(t) for t in (zeile["ticker"], zeile.get("ticker_frueher")) if isinstance(t, str)]
    heutige = [yahoo_ticker(t) for t in sec_ticker.get(int(zeile["cik"]), [])]
    stamm = [t for t in heutige if _ist_stammaktie(t)]
    if stamm:
        gleich = [t for t in eigene if t in stamm]
        return {"quelle": "yfinance", "symbol": gleich[0] if gleich else stamm[0], "kurs_ab": pd.NaT,
                "quelle_hinweis": None if gleich else "heutiger Ticker weicht ab"}
    if tiingo_liste is None:
        return {"quelle": None, "symbol": None, "kurs_ab": pd.NaT, "quelle_hinweis": "nicht mehr gelistet, Tiingo-Liste fehlt"}

    beginn = max(zeile["von"], AB) if pd.notna(zeile["von"]) else AB
    ende = zeile["bis"] if pd.notna(zeile["bis"]) else pd.Timestamp.today().normalize()
    varianten = set()
    for t in eigene:
        basis = t.replace("-", "")
        varianten |= {t, basis, basis + "Q", t + "Q"}
    # Tiingo markiert manche Aktien als ETF (z.B. LLL, HOT); die Börsenwert-Prüfung fängt Fehlgriffe ab.
    # Tiingo-Kurse nicht mehr gelisteter Titel beginnen teils erst 2016: ein später Beginn ist kein Ausschluss,
    # die Lücke wird als `kurs_ab` ausgewiesen und im Bericht als Rest-Bias gezählt.
    kandidaten = tiingo_liste[
        tiingo_liste["ticker"].str.upper().isin(varianten)
        & tiingo_liste["assetType"].isin(["Stock", "ETF"]) & (tiingo_liste["priceCurrency"] == "USD")
        & (tiingo_liste["startDate"] <= ende)
        & (tiingo_liste["endDate"] >= ende - pd.Timedelta(days=30))
        & (tiingo_liste["endDate"] >= beginn)
    ]
    if kandidaten.empty:
        return {"quelle": None, "symbol": None, "kurs_ab": pd.NaT, "quelle_hinweis": "kein passender Tiingo-Ticker"}
    # bevorzugt: als Aktie geführt, Kursende nahe am Indexabgang (Delisting), dann die längste Historie
    kandidaten = kandidaten.assign(etf=kandidaten["assetType"] == "ETF", abstand=(kandidaten["endDate"] - ende).abs(),
                                   laenge=kandidaten["endDate"] - kandidaten["startDate"])
    beste = kandidaten.sort_values(["etf", "abstand", "laenge"], ascending=[True, True, False]).iloc[0]
    hinweise = []
    if len(kandidaten) > 1:
        hinweise.append("mehrere Tiingo-Kandidaten")
    if beste["startDate"] > beginn + pd.Timedelta(days=30):
        hinweise.append(f"Tiingo-Kurse erst ab {beste['startDate'].date()}")
    return {"quelle": "tiingo", "symbol": beste["ticker"], "kurs_ab": beste["startDate"],
            "quelle_hinweis": "; ".join(hinweise) or None}


def plausibel(kurse: pd.DataFrame, aktien: pd.Series, von, bis, *, min_usd=5e8, max_usd=1e13) -> dict:
    """Prüft Abdeckung und Börsenwert einer Kursreihe für den relevanten Teil einer Mitgliedschaft.

    `aktien`: ausstehende Aktien (SEC) mit Datum als Index, splitbereinigt wie die Kurse.
    Ergebnis: {abdeckung (Anteil Werktage mit Kurs), boersenwert_median, ok, grund}.
    """
    beginn = max(pd.Timestamp(von), AB) if pd.notna(von) else AB
    ende = pd.Timestamp(bis) - pd.Timedelta(days=1) if pd.notna(bis) else kurse.index.max() if len(kurse) else beginn
    werktage = pd.bdate_range(beginn, ende)
    im_zeitraum = kurse.loc[beginn:ende] if len(kurse) else kurse
    abdeckung = len(im_zeitraum) / max(len(werktage), 1)
    wert = None
    if len(im_zeitraum) and len(aktien):
        a = aktien.sort_index().reindex(im_zeitraum.index, method="ffill")
        wert = float((im_zeitraum["close"] * a).dropna().median()) if a.notna().any() else None
    if abdeckung < 0.9:
        return {"abdeckung": abdeckung, "boersenwert_median": wert, "ok": False, "grund": f"nur {abdeckung:.0%} der Werktage mit Kurs"}
    if wert is not None and not (min_usd <= wert <= max_usd):
        return {"abdeckung": abdeckung, "boersenwert_median": wert, "ok": False, "grund": f"Börsenwert {wert/1e9:.2f} Mrd. USD unplausibel"}
    return {"abdeckung": abdeckung, "boersenwert_median": wert, "ok": True, "grund": None if wert is not None else "keine Aktienzahl zur Prüfung"}
