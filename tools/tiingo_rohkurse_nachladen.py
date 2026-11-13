r"""Unbereinigte Tiingo-Schlusskurse 2011 bis zur Tresorgrenze für alle Yahoo-Kursreihen des Universums nachladen
(Weg A, Jakob 13.11.2026; Logik und Grenzen: src/tradingbot/daten/tiingo_rohkurse.py).

Aufruf (Git Bash, im Projektordner):  .venv/Scripts/python tools/tiingo_rohkurse_nachladen.py
Optionen: --anzahl N (höchstens N neue Symbole), --symbole A B … (nur diese).
Wiederaufnehmbar: einfach erneut starten; vorhandene Dateien werden übersprungen. Das Werkzeug wartet selbst auf das
Stundenlimit und hört an der Tages- oder Monatsgrenze auf (Meldung, wann es weitergeht). Abbruch mit Strg+C ist sicher.
"""
import argparse
import sys
from datetime import datetime

import pandas as pd

from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.tiingo_rohkurse import Nachlader, tiingo_ticker
from tradingbot.konfiguration import PROJEKT_WURZEL


def symbole_des_universums() -> list[str]:
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv")
    s = status[status["gueltig"].astype(bool) & (status["quelle"] == "yfinance")]["symbol"]
    return sorted({tiingo_ticker(x) for x in s})


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--anzahl", type=int, default=None)
    a.add_argument("--symbole", nargs="*", default=None)
    arg = a.parse_args(argv)
    nachlader = Nachlader(TiingoClient())
    liste = [tiingo_ticker(x) for x in arg.symbole] if arg.symbole else symbole_des_universums()
    offen = [t for t in liste if not nachlader.datei(t).exists()]
    print(f"{datetime.now():%d.%m.%Y %H:%M}  {len(liste)} Symbole, davon {len(offen)} offen; Ablage {nachlader.ablage}", flush=True)
    zaehler = {"geladen": 0, "fehler": 0}
    for i, t in enumerate(offen, 1):
        if arg.anzahl is not None and zaehler["geladen"] + zaehler["fehler"] >= arg.anzahl:
            break
        ergebnis = nachlader.lade(t)
        if ergebnis == "grenze":
            print("Halt: " + nachlader.grenze_erreicht(nachlader.stand()), flush=True)
            break
        zaehler[ergebnis] = zaehler.get(ergebnis, 0) + 1
        fehler = nachlader.stand()["fehler"].get(t, {}).get("fehler", "")
        print(f"{datetime.now():%H:%M}  {i}/{len(offen)}  {t:8s} {ergebnis} {fehler}", flush=True)
    rest = sum(1 for t in liste if not nachlader.datei(t).exists())
    print(f"Fertig für diesen Lauf: {zaehler['geladen']} geladen, {zaehler['fehler']} Fehler, noch offen {rest}.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
