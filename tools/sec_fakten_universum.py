r"""Lädt die SEC-Erstmeldungen (companyfacts) aller Universums-CIKs ab 2012 inklusive Vorgänger in den Cache.

Aufruf:  .venv\Scripts\python tools\sec_fakten_universum.py
Höchstens 8 Anfragen pro Sekunde; bereits gecachte CIKs werden übersprungen. Abbrechen und neu starten ist möglich.
"""
import logging
import sys
import warnings

from tradingbot.daten.abruf import DatenFehler
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden
from tradingbot.daten.sec import SecClient, lade_erstmeldungen
from tradingbot.daten.universum import lade_universum

warnings.simplefilter("ignore")
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    universum, _ = lade_universum()
    relevant = universum[universum["bis"].isna() | (universum["bis"] >= "2012-01-01")]
    ciks = {int(c) for c in relevant["cik"].dropna()}
    ciks |= {int(c) for liste in relevant["vorgaenger_ciks"] if liste is not None for c in list(liste)}
    client = SecClient()
    fehler = []
    schwelle = Fehlerschwelle("SEC-Fakten")
    for nr, cik in enumerate(sorted(ciks), 1):
        text = None
        try:
            lade_erstmeldungen(cik, client=client)
        except DatenFehler as f:
            text = str(f)[:100]
            fehler.append((cik, text))
        schwelle.zaehle(text)
        if nr % 50 == 0 or nr == len(ciks):
            print(f"{nr}/{len(ciks)} fertig, Fehler bisher: {len(fehler)}", flush=True)
    schwelle.pruefe()
    for cik, text in fehler:
        print("FEHLER", cik, text)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FehlerschwelleUeberschritten as fehler:
        sys.exit(laut_melden(fehler))
