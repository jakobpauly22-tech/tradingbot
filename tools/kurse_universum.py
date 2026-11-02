"""Lädt die Kurse aller Universums-Mitgliedschaften ab 2012 in den Cache (yfinance und Tiingo).

Aufruf:  .venv\Scripts\python tools\kurse_universum.py
Dauert wegen des Tiingo-Stundenlimits mehrere Stunden; kann jederzeit abgebrochen und neu gestartet werden,
bereits geladene Kurse kommen aus dem Cache. Status je Mitgliedschaft: daten/universum/kursstatus.csv
"""
import logging
import sys
import warnings

import pandas as pd

from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.kursquellen import kursquelle
from tradingbot.daten.sec import SecClient
from tradingbot.daten.tiingo import TiingoClient, lade_tiingo_liste
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    universum, _ = lade_universum()
    relevant = universum[universum["bis"].isna() | (universum["bis"] >= "2012-01-01")].copy()
    sec = SecClient().ticker_tabelle().groupby("cik").ticker.apply(list).to_dict()
    liste = lade_tiingo_liste()
    quellen = pd.DataFrame([kursquelle(r, sec, liste) for _, r in relevant.iterrows()], index=relevant.index)
    relevant = relevant.join(quellen)
    tiingo = TiingoClient()
    status = []
    gesamt = len(relevant)
    for nr, (i, r) in enumerate(relevant.sort_values("quelle", key=lambda s: s.eq("tiingo")).iterrows(), 1):
        eintrag = {"index": i, "ticker": r["ticker"], "name": r["name"], "quelle": r["quelle"], "symbol": r["symbol"],
                   "kurs_ab": r["kurs_ab"], "quelle_hinweis": r["quelle_hinweis"], "erster_kurs": None, "letzter_kurs": None, "fehler": None}
        try:
            if r["quelle"] == "yfinance":
                k = lade_kurse(r["symbol"], "2011-01-01")
            elif r["quelle"] == "tiingo":
                k = tiingo.historie(r["symbol"])
            else:
                k = None
            if k is not None and len(k):
                eintrag["erster_kurs"], eintrag["letzter_kurs"] = k.index.min().date(), k.index.max().date()
        except Exception as fehler:  # einzelne Fehler protokollieren, Lauf fortsetzen
            eintrag["fehler"] = f"{type(fehler).__name__}: {str(fehler)[:120]}"
        status.append(eintrag)
        if nr % 25 == 0 or nr == gesamt:
            print(f"{nr}/{gesamt} fertig", flush=True)
            ziel = PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv"
            ziel.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(status).to_csv(ziel, index=False)


if __name__ == "__main__":
    sys.exit(main())
