"""Prüft Bot-Anhang-Dateien (Schema 1.1) aus dem Briefing-Archiv.

Aufruf: python tools/pruefe_bot_anhang.py <Datei oder Ordner> [...]
Beendet sich mit Code 1, wenn eine Datei Fehler enthält.
"""
import datetime as dt
import json
import pathlib
import re
import sys

ENUM = {
    "region": {"USA", "Eurozone", "Deutschland", "UK", "China", "Japan", "Schwellenländer", "Welt"},
    "ereignistyp": {"Earnings", "M&A", "Zinsentscheid", "Konjunkturdaten", "Regulierung", "Politik", "Rohstoffe", "Sonstiges"},
    "richtung": {"positiv", "negativ", "neutral"},
    "wirkungsdauer": {"Tage", "Wochen", "Monate"},
}
FELDER_NACHRICHT = ["titel", "anlage", "ticker", "region", "ereignistyp", "richtung", "staerke",
                    "wirkungsdauer", "quelle", "quellen", "block_id", "item_key", "story_id"]
FELDER_TERMIN = ["datum", "ereignis", "region", "bedeutung"]
DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ITEM_KEY = re.compile(r"^(s\d+-i\d+(-b\d+)?|e\d+)$")


def pruefe(d):
    fehler = []
    for k in ["schema_version", "datum", "erstellt_um", "bloecke", "nachrichten", "makro_kalender"]:
        if k not in d:
            fehler.append(f"Feld fehlt: {k}")
    if fehler:
        return fehler
    if d["schema_version"] != "1.1":
        fehler.append(f"schema_version {d['schema_version']!r} statt '1.1'")
    tag = dt.date.fromisoformat(d["datum"])
    erstellt = dt.datetime.fromisoformat(d["erstellt_um"])
    if erstellt.tzinfo is None:
        fehler.append("erstellt_um ohne Zeitzone")
    for i, n in enumerate(d["nachrichten"]):
        for k in FELDER_NACHRICHT:
            if k not in n:
                fehler.append(f"nachrichten[{i}]: Feld {k} fehlt")
        for k, erlaubt in ENUM.items():
            if n.get(k) not in erlaubt:
                fehler.append(f"nachrichten[{i}].{k} = {n.get(k)!r}")
        if not (isinstance(n.get("staerke"), int) and 1 <= n["staerke"] <= 3):
            fehler.append(f"nachrichten[{i}].staerke = {n.get('staerke')!r}")
        if n.get("quelle") is not None and not str(n["quelle"]).startswith("https://"):
            fehler.append(f"nachrichten[{i}].quelle ist keine https-URL")
        if not isinstance(n.get("quellen"), list) or not n["quellen"]:
            fehler.append(f"nachrichten[{i}].quellen leer")
        if n.get("block_id") not in d["bloecke"]:
            fehler.append(f"nachrichten[{i}].block_id nicht in bloecke")
        if not ITEM_KEY.match(str(n.get("item_key", ""))):
            fehler.append(f"nachrichten[{i}].item_key = {n.get('item_key')!r}")
    for i, t in enumerate(d["makro_kalender"]):
        for k in FELDER_TERMIN:
            if k not in t:
                fehler.append(f"makro_kalender[{i}]: Feld {k} fehlt")
        if not DATUM.match(str(t.get("datum", ""))):
            fehler.append(f"makro_kalender[{i}].datum hat kein Format JJJJ-MM-TT")
        elif not 1 <= (dt.date.fromisoformat(t["datum"]) - tag).days <= 7:
            fehler.append(f"makro_kalender[{i}].datum {t['datum']} liegt nicht in den 7 Folgetagen")
        if not (isinstance(t.get("bedeutung"), int) and 1 <= t["bedeutung"] <= 3):
            fehler.append(f"makro_kalender[{i}].bedeutung = {t.get('bedeutung')!r}")
    return fehler


def dateien(argumente):
    for a in argumente:
        p = pathlib.Path(a)
        yield from (sorted(p.glob("*.json")) if p.is_dir() else [p])


if __name__ == "__main__":
    fehlerhaft = 0
    for pfad in dateien(sys.argv[1:] or ["daten/briefings"]):
        d = json.loads(pfad.read_text(encoding="utf-8"))
        fehler = pruefe(d)
        fehlerhaft += bool(fehler)
        print(f"{pfad.name}: {'OK' if not fehler else 'FEHLER'} · {len(d.get('nachrichten', []))} Nachrichten · {len(d.get('makro_kalender', []))} Termine")
        for f in fehler:
            print("   ", f)
    sys.exit(1 if fehlerhaft else 0)
