"""Übernimmt das Briefing-Archiv aus Google Drive nach daten/briefings/, prüft alle Dateien und meldet Lücken.

Aufruf: python tools/briefing_uebernehmen.py [--ohne-kopie]

- Quelle und Ablage stehen in config/briefing.yaml. Die Quelle wird nur gelesen, nie beschrieben oder gelöscht.
- Neue Dateien werden kopiert. Eine vorhandene Datei wird nur bei geänderter Prüfsumme (SHA-256) überschrieben,
  und das wird laut gemeldet (eine geänderte Datei kann ein anderes `erstellt_um` haben, Look-ahead-Schutz).
- Ungültige Dateien werden trotzdem kopiert, aber in der Übersicht markiert.
- Lücken: Tage ohne Datei seit der ersten Datei bis gestern (Wochenende zählt mit), heute erst ab der Export-Uhrzeit.
- `--ohne-kopie` prüft nur, was schon in der Ablage liegt (kein Zugriff auf Drive).
Ist die Quelle nicht erreichbar, wird einmal nach 5 s erneut versucht, danach Code 2.
Beendet sich mit Code 1, wenn eine Datei ungültig oder nicht lesbar ist; Lücken allein ändern den Code nicht.
"""
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import time

WARTEZEIT_S = 5

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pruefe_bot_anhang as anhang  # noqa: E402
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration  # noqa: E402

WOCHENTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def pruefsumme(inhalt: bytes) -> str:
    return hashlib.sha256(inhalt).hexdigest()


def _erstellt_um(inhalt: bytes) -> str:
    try:
        return str(json.loads(inhalt.decode("utf-8")).get("erstellt_um"))
    except (ValueError, AttributeError):
        return "unlesbar"


def uebernehmen(quelle: pathlib.Path, ablage: pathlib.Path) -> list[tuple[str, str, str]]:
    """Kopiert neue und geänderte JSON-Dateien von `quelle` nach `ablage`. Liefert (Dateiname, Aktion, Detail) mit
    Aktion in neu, unverändert, geändert, nicht lesbar. Die Quelle wird nur gelesen (read_bytes)."""
    ablage.mkdir(parents=True, exist_ok=True)
    ergebnis = []
    for datei in sorted(quelle.glob("*.json")):
        try:
            neu = datei.read_bytes()   # bei Streaming lädt das Lesen den Platzhalter aus Drive
        except OSError as e:
            ergebnis.append((datei.name, "nicht lesbar", str(e)))
            continue
        ziel = ablage / datei.name
        if ziel.exists():
            alt = ziel.read_bytes()
            if pruefsumme(alt) == pruefsumme(neu):
                ergebnis.append((datei.name, "unverändert", ""))
                continue
            aktion = "geändert"
            detail = (f"Prüfsumme {pruefsumme(alt)[:10]} → {pruefsumme(neu)[:10]}, "
                      f"erstellt_um {_erstellt_um(alt)} → {_erstellt_um(neu)}")
        else:
            aktion, detail = "neu", ""
        zwischen = ziel.with_name(ziel.name + ".tmp")
        zwischen.write_bytes(neu)
        os.replace(zwischen, ziel)
        ergebnis.append((datei.name, aktion, detail))
    return ergebnis


def tage_der_dateien(namen) -> list[dt.date]:
    tage = []
    for n in namen:
        stem = pathlib.Path(n).stem
        if anhang.DATUM.match(stem):
            try:
                tage.append(dt.date.fromisoformat(stem))
            except ValueError:
                pass
    return sorted(set(tage))


def luecken(vorhandene: list[dt.date], bis: dt.date) -> list[tuple[dt.date, dt.date]]:
    """Zusammenhängende Bereiche fehlender Tage zwischen der ersten Datei und `bis` (einschließlich)."""
    if not vorhandene:
        return []
    da = set(vorhandene)
    bereiche, start, tag = [], None, vorhandene[0]
    while tag <= bis:
        if tag not in da:
            start = start or tag
        elif start:
            bereiche.append((start, tag - dt.timedelta(days=1)))
            start = None
        tag += dt.timedelta(days=1)
    if start:
        bereiche.append((start, bis))
    return bereiche


def letzter_faelliger_tag(jetzt: dt.datetime, export_uhrzeit: str) -> dt.date:
    """Gestern; heute erst, wenn die Export-Uhrzeit erreicht ist."""
    stunde, minute = map(int, export_uhrzeit.split(":"))
    faellig = jetzt.time() >= dt.time(stunde, minute)
    return jetzt.date() if faellig else jetzt.date() - dt.timedelta(days=1)


def _tag(d: dt.date) -> str:
    return f"{WOCHENTAG[d.weekday()]} {d:%d.%m.%Y}"


def main(argv: list[str]) -> int:
    cfg = lade_konfiguration("briefing")
    quelle = pathlib.Path(cfg["quelle"])
    ablage = PROJEKT_WURZEL / cfg["ablage"]
    code = 0

    if "--ohne-kopie" not in argv:
        if not quelle.is_dir():   # Drive meldet sich manchmal kurz nicht: einmal nach 5 s erneut versuchen
            print(f"Quelle nicht erreichbar: {quelle}, neuer Versuch in {WARTEZEIT_S} s")
            time.sleep(WARTEZEIT_S)
        if not quelle.is_dir():
            print(f"Quelle nicht erreichbar: {quelle} (Google Drive für Desktop gestartet?)")
            return 2
        print(f"Übernahme aus {quelle}")
        for name, aktion, detail in uebernehmen(quelle, ablage):
            if aktion in ("neu", "geändert", "nicht lesbar"):
                print(f"  {aktion.upper():<13} {name} {detail}".rstrip())
            if aktion == "nicht lesbar":
                code = 1
        print()

    dateien = sorted(ablage.glob("*.json"))
    zaehler = {"gültig": 0, "Warnung": 0, "ungültig": 0}
    auffaellig, schemas = [], {}
    for pfad in dateien:
        status, gruende = anhang.pruefe_datei(pfad)
        zaehler[status] += 1
        if status != "gültig":
            auffaellig.append((pfad.name, status, gruende))
        try:
            version = json.loads(pfad.read_text(encoding="utf-8")).get("schema_version")
        except (OSError, ValueError, AttributeError):
            version = "unlesbar"
        schemas[version] = schemas.get(version, 0) + 1

    tage = tage_der_dateien(p.name for p in dateien)
    print(f"Ablage {ablage}: {len(dateien)} Dateien")
    if tage:
        print(f"  ältestes {_tag(tage[0])}, neuestes {_tag(tage[-1])}")
    print(f"  schema_version: {', '.join(f'{v}: {n}' for v, n in sorted(schemas.items(), key=str))}")
    print(f"  gültig {zaehler['gültig']} · Warnung {zaehler['Warnung']} · ungültig {zaehler['ungültig']}")
    for name, status, gruende in auffaellig:
        print(f"  {status.upper()}: {name}")
        for g in gruende:
            print(f"      {g}")
    if zaehler["ungültig"]:
        code = 1

    bis = letzter_faelliger_tag(dt.datetime.now(), cfg["export_uhrzeit"])
    fehlend = luecken(tage, bis)
    print(f"Lücken bis {_tag(bis)}: " + ("keine" if not fehlend else f"{sum((b - a).days + 1 for a, b in fehlend)} Tage"))
    for von, bis_ in fehlend:
        n = (bis_ - von).days + 1
        print(f"  {_tag(von)}" + (f" bis {_tag(bis_)}" if n > 1 else "") + f" ({n} {'Tag' if n == 1 else 'Tage'})")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
