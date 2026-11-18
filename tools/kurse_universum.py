r"""Lädt und prüft die Kurse aller Universums-Mitgliedschaften ab 2012 (yfinance und Tiingo).

Aufruf:  .venv\Scripts\python tools\kurse_universum.py
Dauert wegen des Tiingo-Stundenlimits mehrere Stunden; kann jederzeit abgebrochen und neu gestartet werden,
bereits geladene Kurse und Namen kommen aus dem Cache. Status je Mitgliedschaft: daten/universum/kursstatus.csv

Prüfregel (Jakob 02.11.2026, kursquellen.pruefe_kursreihe): Eine Kursreihe zählt nur, wenn sie den Mitgliedszeitraum
ab 2012 abdeckt und der Firmenname aus den Metadaten passt. Sonst `gueltig = False`; im Backtest greift dann die
Rückfall-Regel, und der Fall wird markiert. Tiingo-Metadaten werden nur abgefragt, wenn die Abdeckung passt.
Fehlerschwelle (fehlerschwelle.py): über 5 % Lade- oder Prüffehler → Abbruch mit Exit-Code 1, keine Statusdatei.
"""
import logging
import sys
import warnings

import pandas as pd

from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.kursquellen import kursquelle, pruefe_mitgliedschaft
from tradingbot.daten.sec import SecClient
from tradingbot.daten.tiingo import TiingoClient, lade_tiingo_liste
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")


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
        eintrag = pruefe_mitgliedschaft(i, r, sec_client=sec_client, tiingo=tiingo, datenende=datenende)
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
