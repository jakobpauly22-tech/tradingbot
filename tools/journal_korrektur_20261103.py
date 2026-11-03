"""Einmalige Korrektur des echten Journals (Jakob 03.11.2026): Die Orders 3–7 vom 03.11.2026 hat IBKR nie angenommen
(Gateway-Log: Kontrakt mit conId 0 → Fehler 200 „Es wurde keine Wertpapierdefinition gefunden“; im Client Portal keine
offene Order). Sie werden auf „abgelehnt“ gesetzt, Reservierungen entfallen, der Messbeginn von real und crossover wird
zurückgesetzt. Vorher wird das Journal gesichert (JOURNAL_BACKUP_DIR). Läuft unter der Laufsperre.
"""
import sys

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.betrieb.sperre import laufsperre
from tradingbot.konfiguration import PROJEKT_WURZEL

IDS = ["crossover-20261103-EUNM.DE-K", "crossover-20261103-EUNN.DE-K", "crossover-20261103-IUSA.DE-K",
       "crossover-20261103-SXR1.DE-K", "real-20261103-SPYI.DE-K"]
TEXT = ("200: Es wurde keine Wertpapierdefinition gefunden (Kontrakt mit conId 0, Symbol = Xetra-Kürzel; IBKR führt EUNM als IEMA, "
        "EUNN als IJPA) – von IBKR nie angenommen, Korrektur 03.11.2026")


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    with betriebsmodus("Journal-Korrektur 03.11.2026 (abgelehnte Orders 3–7)"):
        with laufsperre(betriebspfad("tageslauf.sperre"), zweck="Journal-Korrektur"):
            j = Journal(betriebspfad("journal.sqlite"))
            ziel = j.sichern(None)
            if ziel is None:
                print("ABBRUCH: keine Sicherung (JOURNAL_BACKUP_DIR fehlt)")
                return 1
            print(f"gesichert: {ziel.name}")
            buecher = j.nachtraeglich_abgelehnt(IDS, TEXT)
            for z in j.vorschlaege():
                if z["id"] in IDS:
                    print(f"{z['id']}: {z['status']} (Order {z['order_id']})")
            for b in buecher:
                print(f"{b}: Messbeginn {j.messbeginn(b)}, unterwegs {len(j.unterwegs(b))}")
            ziel = j.sichern(None)
            print(f"gesichert nach Korrektur: {ziel.name}")
            j.schliessen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
