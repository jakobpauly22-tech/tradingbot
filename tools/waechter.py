r"""Wächter für den Tageslauf (Benachrichtigung b, Jakob 12.11.2026).

Läuft über die Windows-Aufgabenplanung montags bis freitags um 22:25 (Einrichtung: tools\waechter_einrichten.ps1).
- Xetra-Handelstag ohne Tageslauf im echten Journal → Erinnerung per Telegram.
- Xetra-Feiertag unter der Woche → Lebenszeichen an Healthchecks.io (kein Fehlalarm, wenn der Laptop an ist).
- Nach Mitternacht nachgeholt (Laptop war aus oder schlief) → nichts; dann meldet Healthchecks.io von außen.
Liest das Journal nur (SQLite read-only). Ergebnis jeder Prüfung in daten/betrieb/waechter.log.

Aufruf von Hand: .venv\Scripts\python tools\waechter.py
"""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb.benachrichtigung import melder_aus_env, waechter
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    jetzt = datetime.now(ZoneInfo("Europe/Berlin")).replace(tzinfo=None)
    with betriebsmodus("Wächter Tageslauf (22:25)"):
        journal = betriebspfad("journal.sqlite")
        log = betriebspfad("waechter.log")
        try:
            ergebnis = waechter(jetzt, journal, melder_aus_env(lade_konfiguration("betrieb")))
        except Exception as f:  # noqa: BLE001
            ergebnis = f"Fehler {type(f).__name__}"
        with log.open("a", encoding="utf-8") as datei:
            datei.write(f"{jetzt.isoformat(timespec='seconds')} | {ergebnis}\n")
    print(ergebnis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
