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


# Warnstufe (23.11.2026): Die Datei ist nutzbar, aber etwas fällt auf.
BEKANNTE_QUELLE_BIS = dt.date(2026, 10, 30)   # bis dahin ist `quelle` bei Sammelmeldungen (item_key mit -b) teils falsch


def warnungen(d):
    """Auffälligkeiten einer gültigen Datei (Aufruf nur, wenn `pruefe` keine Fehler fand)."""
    hinweise = []
    tag = dt.date.fromisoformat(d["datum"])
    spaet = (dt.datetime.fromisoformat(d["erstellt_um"]).date() - tag).days
    if spaet > 1:
        hinweise.append(f"nachgeholt: erstellt_um {spaet} Tage nach dem Datum (im Backtest erst ab erstellt_um nutzbar)")
    if not d["nachrichten"]:
        hinweise.append("keine Nachrichten")
    if not d["makro_kalender"]:
        hinweise.append("kein Makro-Kalender")
    schluessel = [(n["block_id"], n["item_key"]) for n in d["nachrichten"]]   # item_key gilt nur innerhalb eines Blocks
    doppelt = sorted({f"{b}/{k}" for b, k in schluessel if schluessel.count((b, k)) > 1})
    if doppelt:
        hinweise.append(f"doppelte item_key im selben Block: {', '.join(doppelt)}")
    if tag <= BEKANNTE_QUELLE_BIS and any("-b" in n["item_key"] for n in d["nachrichten"]):
        hinweise.append("bekannte Einschränkung: quelle bei Sammelmeldungen (-b) teils falsch")
    return hinweise


def pruefe_datei(pfad):
    """Prüft eine Datei und liefert (status, gruende); status ist 'gültig', 'Warnung' oder 'ungültig'.

    Ergänzt `pruefe` um alles, was nur mit dem Dateinamen oder mit der Datei als Ganzes prüfbar ist: lesbares JSON,
    Dateiname JJJJ-MM-TT.json, Datum im Dateinamen = `datum` im Inhalt, `erstellt_um` nicht vor dem Datum."""
    pfad = pathlib.Path(pfad)
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:   # ValueError umfasst JSONDecodeError und UnicodeDecodeError
        return "ungültig", [f"nicht lesbar: {e}"]
    if not isinstance(d, dict):
        return "ungültig", ["Datei ist kein JSON-Objekt"]
    try:
        fehler = pruefe(d)
    except (ValueError, TypeError, AttributeError, KeyError) as e:   # z. B. Datum oder Zeitstempel im falschen Format
        return "ungültig", [f"Struktur nicht prüfbar: {type(e).__name__}: {e}"]
    if not DATUM.match(pfad.stem):
        fehler.append(f"Dateiname {pfad.name} ist nicht JJJJ-MM-TT.json")
    elif d.get("datum") != pfad.stem:
        fehler.append(f"Dateiname {pfad.stem} passt nicht zu datum {d.get('datum')!r} im Inhalt")
    if not fehler and dt.datetime.fromisoformat(d["erstellt_um"]).date() < dt.date.fromisoformat(d["datum"]):
        fehler.append("erstellt_um liegt vor dem Datum")
    if fehler:
        return "ungültig", fehler
    hinweise = warnungen(d)
    return ("Warnung", hinweise) if hinweise else ("gültig", [])


def dateien(argumente):
    for a in argumente:
        p = pathlib.Path(a)
        yield from (sorted(p.glob("*.json")) if p.is_dir() else [p])


if __name__ == "__main__":
    fehlerhaft = 0
    for pfad in dateien(sys.argv[1:] or ["daten/briefings"]):
        status, gruende = pruefe_datei(pfad)
        fehlerhaft += status == "ungültig"
        try:
            d = json.loads(pfad.read_text(encoding="utf-8"))
            zaehlung = f" · {len(d.get('nachrichten', []))} Nachrichten · {len(d.get('makro_kalender', []))} Termine"
        except (OSError, ValueError, AttributeError):
            zaehlung = ""
        marke = {"gültig": "OK", "Warnung": "WARNUNG", "ungültig": "FEHLER"}[status]
        print(f"{pfad.name}: {marke}{zaehlung}")
        for g in gruende:
            print("   ", g)
    sys.exit(1 if fehlerhaft else 0)
