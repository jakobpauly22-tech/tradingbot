r"""Journal-Korrektur: alte Crossover-Sperren nach verpassten Stops entfernen (Jakob 24.11.2026).

Befund: Der Lauf vom 23.11.2026 hat die Stops vom 20.11. für IUSA.DE und IUSP.DE nach der damaligen Regel nachgeholt und
dabei im Crossover-Zustand („nach“) die Wiedereinstiegssperre `gesperrt` = 2026-11-20 gesetzt. Die Verkäufe hat Jakob
bewusst nicht freigegeben; nach der Regel vom 23.11.2026 (docs/BETRIEB.md, „Verpasste Ausstiege“) gilt ein verpasster
Stop, dessen Bedingung am aktuellen Signaltag nicht mehr erfüllt ist, nicht mehr – die Sperre entfällt.

Korrektur: Sicherung, dann `gesperrt` für IUSA.DE und IUSP.DE (je 2026-11-20) aus dem Zustand „nach“ entfernen (im
Zustand „vor“ stehen sie nicht), je Titel ein Ereignis „korrektur“ mit altem Wert und Grund. Alles andere bleibt.

  .venv\Scripts\python tools\journal_korrektur_20261124.py            Prüfung, Trockenlauf (ändert nichts)
  .venv\Scripts\python tools\journal_korrektur_20261124.py --buchen   Korrektur im echten Journal
"""
import argparse
import copy
import sys

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.betrieb.sperre import laufsperre
from tradingbot.konfiguration import PROJEKT_WURZEL

SPERREN = {"IUSA.DE": "2026-11-20", "IUSP.DE": "2026-11-20"}
GRUND = ("Regel vom 23.11.2026 (verpasste Ausstiege nur bei weiter erfüllter Bedingung): verpasster Stop vom 20.11.2026 "
         "nicht mehr gültig, Schluss am 23.11. wieder über dem Stop, Verkauf bewusst nicht freigegeben; Korrektur 24.11.2026")


def pruefen(zustand: dict) -> list[str]:
    fehler = []
    if zustand.get("signaltag") != "2026-11-23":
        fehler.append(f"Crossover-Zustand unerwartet: Signaltag {zustand.get('signaltag')} statt 2026-11-23")
    nach = zustand.get("nach", {})
    for t, d in SPERREN.items():
        if nach.get("gesperrt", {}).get(t) != d:
            fehler.append(f"{t}: Sperre im Zustand „nach“ ist {nach.get('gesperrt', {}).get(t)!r}, erwartet {d}")
        if t not in nach.get("positionen", {}):
            fehler.append(f"{t}: keine Position im Zustand „nach“")
    return fehler


def korrigiert(zustand: dict) -> dict:
    neu = copy.deepcopy(zustand)
    for t in SPERREN:
        neu["nach"]["gesperrt"].pop(t)
    return neu


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--buchen", action="store_true")
    arg = a.parse_args()
    with betriebsmodus("Journal-Korrektur 24.11.2026 (Crossover-Sperren)" + ("" if arg.buchen else ", Trockenlauf")):
        with laufsperre(betriebspfad("tageslauf.sperre"), zweck="Journal-Korrektur"):
            j = Journal(betriebspfad("journal.sqlite"))
            zustand = j.zustand("crossover")
            fehler = pruefen(zustand)
            if fehler:
                print("ABBRUCH, nichts geändert:\n  " + "\n  ".join(fehler))
                return 1
            print(f"Befund passt: Sperren {SPERREN} im Zustand „nach“ vom 23.11., Positionen vorhanden.")
            if not arg.buchen:
                print("Trockenlauf – mit --buchen korrigieren.")
                return 0
            print(f"gesichert vorher: {j.sichern(None).name}")
            j.zustand_speichern("crossover", korrigiert(zustand))
            for t, d in SPERREN.items():
                j.ereignis("korrektur", f"Crossover-Sperre {t} entfernt (alter Wert gesperrt = {d}). Grund: {GRUND}", "crossover")
            print(f"Sperren entfernt; verbleibend: {j.zustand('crossover')['nach']['gesperrt']}")
            return 0


if __name__ == "__main__":
    sys.exit(main())
