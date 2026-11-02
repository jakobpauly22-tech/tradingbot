r"""Prüft, wie gut die Kennzahlen-Zuordnung (config/fundamental.yaml) echte SEC-Daten abdeckt.

Aufruf:  .venv\Scripts\python tools\sec_abdeckung.py 2019-12-31 320193 789019 19617
         (Stichtag, danach CIKs). Ausgabe: Tabelle Firma × Kennzahl und Abdeckung je Kennzahl.
"""
import sys

import pandas as pd

from tradingbot.daten.sec import SecClient, abdeckung, lade_erstmeldungen, stammdaten
from tradingbot.konfiguration import lade_konfiguration


def main(argumente: list[str]) -> None:
    if len(argumente) < 2:
        print(__doc__)
        sys.exit(1)
    stichtag, ciks = argumente[0], [int(c) for c in argumente[1:]]
    kennzahlen = lade_konfiguration("fundamental")["kennzahlen"]
    client = SecClient()
    zeilen = {}
    for cik in ciks:
        name = stammdaten(cik, client=client)["name"]
        zeilen[f"{cik} {name[:25]}"] = abdeckung(lade_erstmeldungen(cik, client=client), kennzahlen, stichtag)
    tabelle = pd.DataFrame(zeilen).T
    pd.set_option("display.width", 250)
    print(tabelle.replace({True: "x", False: "."}).to_string())
    print("\nAbdeckung je Kennzahl:")
    print(tabelle.mean().sort_values().round(2).to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
