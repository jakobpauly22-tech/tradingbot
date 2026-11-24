"""Meldungen zur SEC-Aktualität im Tageslauf (SEC-Aktualisierung Schritt 3; Festlegung Jakob 23.11.2026, docs/BETRIEB.md,
Abschnitt „SEC-Aktualisierung im Betrieb“, Regel „Meldungen im Tageslauf“). Nur Meldung, nie Stopp.

- **SEC-Stand:** Das Protokoll nennt immer „SEC-Stand vom …“ (`letzter_erfolg` aus `STAND.json`), bei einem nicht
  erfolgreichen letzten Lauf auch diesen Lauf mit der Zahl der Fehler.
- **Sofortmeldung** (Telegram), wenn `letzter_erfolg` mehr als `stand_max_tage` (9) Tage zurückliegt oder `STAND.json`
  fehlt bzw. unlesbar ist. Die Bewertung läuft mit dem vorhandenen Betriebs-Cache weiter.
- **Je Firma** (am Bewertungstag der Fundamental-Bewertung): neueste Erstmeldung (`filed`) mehr als
  `meldung_max_alter_tage` (120) Tage alt → Symbol und Alter in Tagen. Die 19 Firmen mit bekannt unvollständigen
  SEC-Daten (Befund A2 vom 23.11.2026, `config/betrieb.yaml` `sec_meldungen.bekannt`) stehen als eigene Gruppe
  „bekannt“ (Jakob 24.11.2026).
- **Immer:** die Zahl der Firmen, die wegen `veraltet` aus der Bewertung fallen (bisher still).

Alle Zeilen außer den Sofortmeldungen gehen nur ins Protokoll, nicht nach Telegram (Jakob 24.11.2026).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

STAND_DATEI = "STAND.json"


def stand_lesen(wurzel: Path) -> dict:
    """`STAND.json` aus der Wurzel der SEC-Rohdaten des Betriebs (über die Probe-Schicht). Wirft OSError/ValueError."""
    from tradingbot.daten.schicht import lesepfad

    return json.loads(lesepfad(Path(wurzel) / STAND_DATEI).read_text(encoding="utf-8"))


def _zeit(text) -> datetime | None:
    return datetime.fromisoformat(str(text)) if text else None


def _alter_tage(jetzt: datetime, t: datetime) -> float:
    if (jetzt.tzinfo is None) != (t.tzinfo is None):        # naive Zeit = Ortszeit des Laufs
        t = t.replace(tzinfo=jetzt.tzinfo) if t.tzinfo is None else t.astimezone(jetzt.tzinfo).replace(tzinfo=None)
    return (jetzt - t).total_seconds() / 86400


def stand_meldungen(lesen, jetzt: datetime, konfig: dict) -> tuple[list[str], list[str]]:
    """(Protokollzeilen, Sofortmeldungen) zum SEC-Stand. `lesen()` liefert den Inhalt von `STAND.json`."""
    grenze = float(konfig.get("stand_max_tage", 9))
    weiter = "Bewertung läuft mit dem vorhandenen Betriebs-Cache weiter"
    try:
        stand = lesen()
        if not isinstance(stand, dict):
            raise ValueError("kein JSON-Objekt")
    except FileNotFoundError:
        text = f"SEC-Stand unbekannt: {STAND_DATEI} fehlt (noch kein Lauf von tools/sec_aktualisieren.py) – {weiter}"
        return [text], [text]
    except (OSError, ValueError) as f:
        text = f"SEC-Stand unbekannt: {STAND_DATEI} unlesbar ({type(f).__name__}) – {weiter}"
        return [text], [text]
    zeilen, sofort = [], []
    erfolg = _zeit(stand.get("letzter_erfolg"))
    zeile = (f"SEC-Stand vom {erfolg:%d.%m.%Y %H:%M} (letzter erfolgreicher Lauf)" if erfolg
             else "SEC-Stand: noch kein erfolgreicher Lauf von tools/sec_aktualisieren.py")
    if not stand.get("erfolgreich"):
        ende = _zeit(stand.get("lauf_ende"))
        fehler = (stand.get("zusammenfassung") or {}).get("Fehler", 0)
        zeile += (f"; letzter Lauf {ende:%d.%m.%Y %H:%M} nicht erfolgreich" if ende else "; letzter Lauf nicht erfolgreich")
        zeile += f", {fehler} Fehler" + (f" ({stand['abbruch']})" if stand.get("abbruch") else "")
    zeilen.append(zeile)
    if erfolg is None:
        sofort.append(f"SEC-Stand: kein erfolgreicher Lauf in {STAND_DATEI} – {weiter}")
    else:
        alter = _alter_tage(jetzt, erfolg)
        if alter > grenze:
            sofort.append(f"SEC-Stand vom {erfolg:%d.%m.%Y} ist {alter:.0f} Tage alt (Grenze {grenze:g} Tage) – {weiter}")
    return zeilen, sofort


def neueste_meldung(erst: pd.DataFrame | None) -> pd.Timestamp | None:
    """Neueste `filed` der Erstmeldungen einer Firma (alle CIKs zusammengelegt) oder None."""
    if erst is None or len(erst) == 0 or "filed" not in erst:
        return None
    m = pd.to_datetime(erst["filed"]).max()
    return None if pd.isna(m) else pd.Timestamp(m)


def firmen_meldungen(sec: dict | None, tag, konfig: dict) -> list[str]:
    """Protokollzeilen aus der Bewertung: `sec` = {"firmen": [{"symbol", "ciks", "neueste" (Datum als Text)}], "veraltet": [Symbol]}
    (engines/fundamental/aktuell.bewertung_am, `attrs["sec"]`). Alter = Bewertungstag − neueste `filed` in Kalendertagen."""
    if not sec:
        return []
    tag = pd.Timestamp(tag).normalize()
    grenze = int(konfig.get("meldung_max_alter_tage", 120))
    bekannt = {int(c) for c in (konfig.get("bekannt") or {})}
    alt, alt_bekannt = [], []
    for f in sec.get("firmen", []):
        neu = f.get("neueste")
        tage = None if neu is None else (tag - pd.Timestamp(neu).normalize()).days
        if tage is not None and tage <= grenze:
            continue
        eintrag = (-(tage if tage is not None else 10**6), str(f.get("symbol") or f.get("firma")),
                   "ohne Meldung" if tage is None else f"{tage} Tage")
        (alt_bekannt if bekannt & {int(c) for c in f.get("ciks", [])} else alt).append(eintrag)
    zeilen = []
    if alt:
        zeilen.append(f"SEC: {len(alt)} Firma(en) mit neuester Meldung älter als {grenze} Tage (Bewertungstag {tag:%d.%m.%Y}): "
                      + ", ".join(f"{s} {a}" for _, s, a in sorted(alt)))
    if alt_bekannt:
        zeilen.append(f"SEC bekannt (unvollständige SEC-Daten, Befund A2 vom 23.11.2026): {len(alt_bekannt)} Firma(en) älter als "
                      f"{grenze} Tage: " + ", ".join(f"{s} {a}" for _, s, a in sorted(alt_bekannt)))
    veraltet = sorted(str(s) for s in sec.get("veraltet", []))
    zeilen.append(f"SEC: {len(veraltet)} Firma(en) wegen veraltetem Abschluss nicht bewertet"
                  + (f" ({', '.join(veraltet)})" if veraltet else ""))
    return zeilen
