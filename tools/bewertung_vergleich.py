r"""Nachweis „gleiche Bewertung vorher/nachher“ für die Laufzeit-Arbeit an der Fundamental-Bewertung (Jakob 19.11.2026).

Rechnet `engines/fundamental/aktuell.bewertung_am(stichtag, aktualisieren=False)` – ohne Kursabruf, also auf dem
vorhandenen Kursstand – und vergleicht die Bewertungstabelle sowie die Ranglisten A und B exakt (Spalten, Datentypen,
jeder Wert, Gründe und Signale) mit einer zuvor festgehaltenen Referenz.

Läuft im Betriebsmodus in einer eigenen, nicht geleerten Probe-Schicht (`daten/betrieb/probe/bewertung_referenz/schicht`):
Betriebs- und Entwicklungsdaten bleiben unverändert (daten/schicht.py), und das Universum des Betriebs wird je Kalendertag
höchstens einmal in der Schicht gebaut.

  .venv\Scripts\python tools\bewertung_vergleich.py --referenz        Referenz schreiben (vor jeder Änderung)
  .venv\Scripts\python tools\bewertung_vergleich.py                   mit der Referenz vergleichen; Ausgang 0 nur bei „identisch“
"""
import argparse
import json
import pickle
import subprocess
import sys
import time
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

from tradingbot.konfiguration import PROJEKT_WURZEL

STICHTAG = "2026-11-18"
ORDNER = PROJEKT_WURZEL / "daten" / "betrieb" / "probe" / "bewertung_referenz"
REFERENZ = ORDNER / "referenz.pkl"


def rechnen(stichtag: str) -> tuple[dict, float]:
    from tradingbot.backtest.tresor import betriebsmodus
    from tradingbot.daten.schicht import probe_schicht
    from tradingbot.engines.fundamental.aktuell import bewertung_am, rangliste

    with probe_schicht(ORDNER / "schicht"), betriebsmodus("Probe: Bewertungsvergleich (Laufzeit, nur Schicht)"):
        beginn = time.perf_counter()
        bewertung, symbole, meldungen = bewertung_am(pd.Timestamp(stichtag), aktualisieren=False)
        dauer = time.perf_counter() - beginn
        ergebnis = {"bewertung": bewertung, "symbole": symbole, "meldungen": meldungen,
                    "rangliste_A": rangliste(bewertung, "A"), "rangliste_B": rangliste(bewertung, "B")}
    return ergebnis, dauer


def unterschiede(alt: pd.DataFrame, neu: pd.DataFrame, name: str) -> list[str]:
    """Leer, wenn beide Tabellen exakt gleich sind (Spalten, Reihenfolge, Datentypen, Werte); sonst die ersten Abweichungen."""
    if alt.equals(neu) and list(alt.columns) == list(neu.columns) and (alt.dtypes == neu.dtypes).all():
        return []
    aus = [f"{name}: Form {alt.shape} gegen {neu.shape}"]
    if list(alt.columns) != list(neu.columns):
        aus.append(f"{name}: Spalten verschieden: {sorted(set(alt.columns) ^ set(neu.columns))}")
        return aus
    unterschiedliche_typen = [s for s in alt.columns if alt[s].dtype != neu[s].dtype]
    if unterschiedliche_typen:
        aus.append(f"{name}: Datentypen verschieden: {unterschiedliche_typen}")
    if alt.shape == neu.shape:
        for s in alt.columns:
            for i in range(len(alt)):
                a, n = alt[s].iloc[i], neu[s].iloc[i]
                if not (a == n if not (pd.api.types.is_scalar(a) and pd.isna(a)) else pd.api.types.is_scalar(n) and pd.isna(n)):
                    aus.append(f"{name}: Zeile {i} ({alt['symbol'].iloc[i] if 'symbol' in alt else i}), Spalte {s}: {a!r} gegen {n!r}")
                    if len(aus) > 20:
                        return aus
    return aus


def git_stand() -> str:
    r = subprocess.run(["git", "describe", "--always", "--dirty"], cwd=PROJEKT_WURZEL, capture_output=True, text=True)
    return r.stdout.strip()


def main() -> int:
    load_dotenv(PROJEKT_WURZEL / ".env")
    a = argparse.ArgumentParser()
    a.add_argument("--referenz", action="store_true", help="Referenz schreiben statt vergleichen")
    a.add_argument("--stichtag", default=STICHTAG)
    arg = a.parse_args()
    ergebnis, dauer = rechnen(arg.stichtag)
    stand = {"stichtag": arg.stichtag, "git": git_stand(), "gerechnet_um": datetime.now().isoformat(timespec="seconds"),
             "dauer_s": round(dauer, 1), "firmen": len(ergebnis["bewertung"])}
    if arg.referenz:
        ORDNER.mkdir(parents=True, exist_ok=True)
        with REFERENZ.open("wb") as f:
            pickle.dump({**ergebnis, "stand": stand}, f)
        (ORDNER / "referenz.json").write_text(json.dumps(stand, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Referenz geschrieben: {stand}")
        return 0
    with REFERENZ.open("rb") as f:
        ref = pickle.load(f)
    if ref["stand"]["stichtag"] != arg.stichtag:
        print(f"Referenz gilt für {ref['stand']['stichtag']}, nicht {arg.stichtag}")
        return 2
    abw = []
    for teil in ("bewertung", "rangliste_A", "rangliste_B"):
        abw += unterschiede(ref[teil], ergebnis[teil], teil)
    if ref["symbole"] != ergebnis["symbole"]:
        abw.append("Symbol je Firma verschieden")
    if list(ref["meldungen"]) != list(ergebnis["meldungen"]):
        abw.append(f"Meldungen verschieden: {ref['meldungen']} gegen {ergebnis['meldungen']}")
    print(f"Referenz: Git {ref['stand']['git']}, {ref['stand']['dauer_s']} s; jetzt: Git {stand['git']}, {stand['dauer_s']} s")
    if abw:
        print("NICHT identisch:")
        print("\n".join(f"  {z}" for z in abw))
        return 1
    print(f"identisch ({stand['firmen']} Firmen, Bewertung und Ranglisten A und B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
