r"""Lädt und prüft die Kurse aller Universums-Mitgliedschaften ab 2012 (yfinance und Tiingo).

Aufruf:  .venv\\Scripts\\python tools\\kurse_universum.py
Dauert wegen des Tiingo-Stundenlimits mehrere Stunden; kann jederzeit abgebrochen und neu gestartet werden,
bereits geladene Kurse und Namen kommen aus dem Cache. Status je Mitgliedschaft: daten/universum/kursstatus.csv

Prüfregel (Jakob 03.11.2026, kursquellen.pruefe_kursreihe): Eine Kursreihe zählt nur, wenn sie den Mitgliedszeitraum
ab 2012 abdeckt und der Firmenname aus den Metadaten passt. Sonst `gueltig = False`; im Backtest greift dann die
Rückfall-Regel, und der Fall wird markiert. Tiingo-Metadaten werden nur abgefragt, wenn die Abdeckung passt.
Fehlerschwelle (fehlerschwelle.py): über 5 % Lade- oder Prüffehler → Abbruch mit Exit-Code 1, keine Statusdatei.
"""
import logging
import sys
import warnings

import pandas as pd

from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.kursquellen import kursquelle, pruefe_abdeckung, pruefe_kursreihe, yahoo_name
from tradingbot.daten.sec import SecClient
from tradingbot.daten.tiingo import TiingoClient, lade_tiingo_liste
from tradingbot.daten.universum import lade_universum, sec_namen_einer_cik
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")


def _vorgaenger(zeile) -> list[int]:
    """Vorgänger-CIKs; aus dem Parquet-Cache kommen sie als NumPy-Array (dessen Wahrheitswert ist mehrdeutig)."""
    liste = zeile["vorgaenger_ciks"]
    return [] if liste is None else [int(c) for c in list(liste)]


def _bekannte_namen(zeile, sec_client) -> list[str]:
    namen = [zeile["name"]]
    ciks = ([int(zeile["cik"])] if pd.notna(zeile["cik"]) else []) + _vorgaenger(zeile)
    for cik in ciks:
        try:
            namen += sec_namen_einer_cik(cik, sec_client)
        except Exception:  # fehlende Submissions: dann nur der Indexname
            pass
    return [n for n in namen if isinstance(n, str) and n]


def main() -> None:
    universum, _ = lade_universum()
    relevant = universum[universum["bis"].isna() | (universum["bis"] >= "2012-01-01")].copy()
    sec_client = SecClient()
    sec = sec_client.ticker_tabelle().groupby("cik").ticker.apply(list).to_dict()
    liste = lade_tiingo_liste()
    quellen = pd.DataFrame([kursquelle(r, sec, liste) for _, r in relevant.iterrows()], index=relevant.index)
    relevant = relevant.join(quellen)
    tiingo = TiingoClient()
    datenende = pd.Timestamp.today().normalize() - pd.Timedelta(days=7)
    status = []
    gesamt = len(relevant)
    schwelle = Fehlerschwelle("Kurs-Download")
    for nr, (i, r) in enumerate(relevant.sort_values("quelle", key=lambda s: s.eq("tiingo")).iterrows(), 1):
        eintrag = {"index": i, "ticker": r["ticker"], "name": r["name"], "von": r["von"], "bis": r["bis"], "quelle": r["quelle"],
                   "symbol": r["symbol"], "quelle_hinweis": r["quelle_hinweis"], "erster_kurs": None, "letzter_kurs": None,
                   "name_meta": None, "gueltig": False, "grund": None, "fehler": None}
        try:
            if r["quelle"] == "yfinance":
                k = lade_kurse(r["symbol"], "2011-01-01")
            elif r["quelle"] == "tiingo":
                k = tiingo.historie(r["symbol"])
            else:
                k = None
            if k is not None and len(k):
                eintrag["erster_kurs"], eintrag["letzter_kurs"] = k.index.min().date(), k.index.max().date()
            abdeckung = pruefe_abdeckung(k, r["von"], r["bis"], datenende=datenende)
            if not abdeckung["ok"]:
                eintrag["grund"] = abdeckung["grund"] if r["quelle"] else r["quelle_hinweis"]
            else:
                meta_name = yahoo_name(r["symbol"]) if r["quelle"] == "yfinance" else tiingo.metadaten(r["symbol"]).get("name")
                p = pruefe_kursreihe(k, meta_name, _bekannte_namen(r, sec_client), r["von"], r["bis"], datenende=datenende)
                eintrag.update({"name_meta": meta_name, "gueltig": bool(p["ok"]), "grund": p["grund"]})
        except Exception as fehler:  # einzelne Fehler protokollieren, Lauf fortsetzen
            eintrag["fehler"] = f"{type(fehler).__name__}: {str(fehler)[:120]}"
            eintrag["grund"] = "Fehler beim Laden"
        status.append(eintrag)
        schwelle.zaehle(eintrag["fehler"])
        if nr % 25 == 0 or nr == gesamt:
            gueltig = sum(e["gueltig"] for e in status)
            print(f"{nr}/{gesamt} fertig, gültig {gueltig}, Fehler {len(schwelle.fehler)}", flush=True)
    schwelle.pruefe()
    ziel = PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(status).to_csv(ziel, index=False)
    print(f"Status geschrieben: {ziel}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
