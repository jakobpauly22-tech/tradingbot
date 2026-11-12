r"""Verbindungstest der Benachrichtigungen (Jakob 12.11.2026).

Schickt per Telegram nur den festen Text „Verbindung ok“ (keine Kontodaten) und pingt Healthchecks.io einmal über …/log:
Der Ping erscheint im Protokoll des Checks, ändert dessen Status aber nicht (überdeckt also keinen ausgefallenen Abendlauf).
Liest weder Journal noch Gateway. Schalter und Variablen wie im Betrieb (config/betrieb.yaml `benachrichtigung`, .env).

Aufruf: .venv\Scripts\python tools\verbindungstest.py
"""
import sys

from dotenv import load_dotenv

from tradingbot.betrieb.benachrichtigung import melder_aus_env, verbindungstest
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    zeilen = verbindungstest(melder_aus_env(lade_konfiguration("betrieb")))
    for zeile in zeilen:
        print(zeile)
    return 0 if all("gesendet" in z and "fehlgeschlagen" not in z for z in zeilen) else 1


if __name__ == "__main__":
    sys.exit(main())
