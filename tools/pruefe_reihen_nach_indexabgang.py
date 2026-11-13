r"""Musterprüfung: Kursreihen, die nach dem Indexabgang einer Firma weiterlaufen und wahrscheinlich zu einem anderen
Unternehmen gehören (Anlass E. I. du Pont, CIK 30554; Kriterien vor der Suche festgelegt, docs/FUNDAMENTAL.md,
Abschnitt „Dritte Datenkorrektur“, Jakob 13.11.2026). Nur lesend; korrigiert wird erst nach Jakobs Prüfung.

Aufruf:  .venv\Scripts\python tools\pruefe_reihen_nach_indexabgang.py
Ergebnis: docs/berichte/2026-11-13_reihen_nach_indexabgang.md

Kriterien: Grundmenge = Firmen (CIK), deren letzte Mitgliedschaft ab 01.01.2012 endet, mit gültiger Kursreihe.
K1 mehr als 10 Handelstage Kurse nach dem Indexabgang; K2 Tagesänderung über ±15 % ohne Split im Fenster −5 … +10
Handelstage um den Abgang; K3 Symbol laut SEC-Tickerliste heute einer anderen CIK zugeordnet. Treffer: K1 und (K2 oder K3).
Läuft im Betriebsmodus, damit auch Kurse nach 2024 sichtbar sind (nur gelesen).
"""
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.sec import SecClient
from tradingbot.daten.sp500_nachbau import ciks_der_zeile
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_reihen_nach_indexabgang.md"
NACHLAUF_TAGE, SPRUNG, FENSTER = 10, 0.15, (-5, 10)
PERIODENBERICHTE = ("10-K", "10-Q", "10-K/A", "10-Q/A")


def symbol_normal(s: str) -> str:
    return str(s).upper().replace(".", "-").replace("/", "-")


def kriterien(kurse: pd.DataFrame, abgang: pd.Timestamp) -> dict:
    """K1 und K2 für eine Kursreihe (Spalten close, split) und den Tag des Indexabgangs."""
    k = kurse.sort_index()
    nach = k[k.index > abgang]
    ergebnis = {"k1": len(nach) > NACHLAUF_TAGE, "tage_nach": len(nach), "letzter_kurs": k.index.max(), "k2": False, "sprung": None}
    if k.empty:
        return ergebnis
    pos = int(k.index.searchsorted(abgang))
    lo, hi = max(1, pos + FENSTER[0]), min(len(k) - 1, pos + FENSTER[1])
    aenderung = k["close"].pct_change()
    split = k["split"].fillna(0) if "split" in k.columns else pd.Series(0.0, index=k.index)
    for i in range(lo, hi + 1):
        a = aenderung.iloc[i]
        if pd.notna(a) and abs(a) > SPRUNG and split.iloc[i] == 0:
            if ergebnis["sprung"] is None or abs(a) > abs(ergebnis["sprung"][1]):
                ergebnis["sprung"] = (k.index[i], float(a))
            ergebnis["k2"] = True
    return ergebnis


def letzter_periodenbericht(client, ciks) -> str:
    daten = []
    for c in ciks:
        try:
            subs, _ = client.submissions(int(c))
        except Exception:  # noqa: BLE001 – Zusatzangabe, kein Kriterium
            continue
        r = pd.DataFrame(subs.get("filings", {}).get("recent", {}))
        if len(r):
            r = r[r["form"].isin(PERIODENBERICHTE)]
            if len(r):
                daten.append(str(r["filingDate"].max()))
    return max(daten) if daten else "–"


def main() -> int:
    with betriebsmodus("Musterprüfung Kursreihen nach Indexabgang (nur lesend)"):
        universum, _ = lade_universum()
        status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
        client, tiingo, cache = SecClient(), TiingoClient(), standard_cache()
        tickerliste = client.ticker_tabelle()
        inhaber = {symbol_normal(z["ticker"]): (int(z["cik"]), z["name"]) for _, z in tickerliste.iterrows()}
        u = universum[universum["cik"].notna()]
        zeilen, grundmenge = [], 0
        for cik, g in u.groupby("cik"):
            if g["bis"].isna().any():
                continue                                   # noch Mitglied
            abgang = pd.Timestamp(g["bis"].max())
            if abgang < pd.Timestamp("2012-01-01"):
                continue
            letzte = g.sort_values("bis").iloc[-1]
            nr = letzte.name
            if nr not in status.index or not bool(status.loc[nr, "gueltig"]):
                continue
            s = status.loc[nr]
            try:
                kurse = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
            except Exception:  # noqa: BLE001
                kurse = None
            if kurse is None or kurse.empty:
                continue
            grundmenge += 1
            k = kriterien(kurse, abgang)
            ciks = ciks_der_zeile(letzte)
            besitzer = inhaber.get(symbol_normal(s["symbol"]))
            k3 = besitzer is not None and besitzer[0] not in ciks
            if not (k["k1"] and (k["k2"] or k3)):
                continue
            zeilen.append({"ticker": letzte["ticker"], "cik": int(cik), "name": letzte["name"], "abgang": abgang.date(),
                           "grund": letzte.get("grund_abgang") or "–", "symbol": s["symbol"], "quelle": s["quelle"],
                           "name_kursquelle": s.get("name_meta"), "tage_nach": k["tage_nach"], "letzter_kurs": k["letzter_kurs"].date(),
                           "k2": k["k2"], "sprung": "–" if k["sprung"] is None else f"{k['sprung'][0].date()} {k['sprung'][1]:+.1%}",
                           "k3": k3, "ticker_heute": "–" if besitzer is None else f"CIK {besitzer[0]} {besitzer[1]}",
                           "letzter_periodenbericht": letzter_periodenbericht(client, ciks)})
    df = pd.DataFrame(zeilen).sort_values("abgang") if zeilen else pd.DataFrame()
    text = ["# Musterprüfung: Kursreihen nach dem Indexabgang", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_reihen_nach_indexabgang.py`. Kriterien vor der Suche festgelegt "
            "(docs/FUNDAMENTAL.md, Abschnitt „Dritte Datenkorrektur“): K1 mehr als 10 Handelstage Kurse nach dem Abgang; K2 Tagesänderung "
            "über ±15 % ohne Split im Fenster −5 … +10 Handelstage; K3 Symbol heute laut SEC einer anderen CIK zugeordnet. Treffer: K1 und (K2 oder K3).", "",
            f"Grundmenge: {grundmenge} Firmen mit Indexabgang ab 2012 und gültiger Kursreihe. Treffer: {len(df)} "
            f"(K2: {int(df['k2'].sum()) if len(df) else 0}, K3: {int(df['k3'].sum()) if len(df) else 0}, beide: "
            f"{int((df['k2'] & df['k3']).sum()) if len(df) else 0}). Nichts wurde korrigiert.", "",
            "| Ticker (CIK) | Name | Indexabgang | Grund laut Liste | Kursreihe (Quelle) | Name in der Kursquelle | Kurse danach bis | "
            "Sprung (K2) | Ticker heute bei (K3) | letzter eigener 10-K/10-Q |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for z in df.itertuples():
        text.append(f"| {z.ticker} ({z.cik}) | {z.name} | {z.abgang} | {z.grund} | {z.symbol} ({z.quelle}) | {z.name_kursquelle} | "
                    f"{z.letzter_kurs} ({z.tage_nach} Tage) | {z.sprung} | {z.ticker_heute if z.k3 else '–'} | {z.letzter_periodenbericht} |")
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
