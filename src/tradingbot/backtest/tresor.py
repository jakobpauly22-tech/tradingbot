"""Tresor: gesperrte Out-of-Sample-Daten (ab `tresor.gesperrt_ab` in config/backtest.yaml).

Regeln (Jakob, 01.11.2026):
1. Einmal pro Phase öffnen, und zwar erst, wenn Regeln und Parameter feststehen.
2. Bei einem schlechten Ergebnis nicht nachjustieren und erneut testen, sonst ist der Tresor verbraucht.
   Dann: Erkenntnis notieren, zurück auf die Entwicklungsdaten; als neue Prüfung dient das Paper Trading.
3. Das Paper Trading ist der zweite, noch strengere Tresor, weil diese Daten heute noch nicht existieren.

Technik: Jeder Zugriff auf Daten ab dem Sperrdatum braucht eine `TresorFreigabe`. Eine Freigabe entsteht
nur über `oeffne_tresor`, das sie im Protokoll (docs/TRESOR_PROTOKOLL.md, in Git) einträgt. Eine zweite
Öffnung für dieselbe Phase wird verweigert.

Zentrale Datumsgrenze (Jakob, 02.11.2026): Alle Datenlader (Kurse mit Dividenden und Splits, Tiingo, FRED,
SEC-Fundamentaldaten) liefern nur Daten bis `datengrenze()` (Tag vor dem Sperrdatum, heute 31.12.2024). Aufgehoben
wird die Grenze nur innerhalb von `with tresor_geoeffnet(freigabe):` mit einer im Protokoll eingetragenen Freigabe.
"""
from __future__ import annotations

import subprocess
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import lru_cache
from datetime import date, datetime
from pathlib import Path

import pandas as pd

_KOPF = """# Tresor-Protokoll

Jede Öffnung des Tresors (gesperrte Daten ab `tresor.gesperrt_ab` in `config/backtest.yaml`) wird hier
automatisch eingetragen. Regeln: einmal pro Phase, erst wenn Regeln und Parameter feststehen; bei einem
schlechten Ergebnis nicht nachjustieren, sondern Erkenntnis notieren und auf die Entwicklungsdaten zurück.
Einträge nicht löschen.

| Zeitpunkt | Phase | Begründung | Git-Commit |
| --- | --- | --- | --- |
"""


class TresorGesperrt(RuntimeError):
    """Zugriff auf gesperrte Daten ohne gültige Freigabe."""


@dataclass(frozen=True)
class TresorFreigabe:
    phase: str
    begruendung: str


def _einstellungen(konfig: dict | None) -> tuple[date, Path]:
    from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

    tresor = (konfig or lade_konfiguration("backtest"))["tresor"]
    protokoll = Path(tresor["protokoll"])
    if not protokoll.is_absolute():
        protokoll = PROJEKT_WURZEL / protokoll
    return pd.Timestamp(str(tresor["gesperrt_ab"])).date(), protokoll


def geoeffnete_phasen(protokoll: Path) -> set[str]:
    if not protokoll.exists():
        return set()
    phasen = set()
    for zeile in protokoll.read_text(encoding="utf-8").splitlines():
        teile = [t.strip() for t in zeile.strip().strip("|").split("|")]
        if len(teile) == 4 and teile[0] not in ("Zeitpunkt", "---"):
            phasen.add(teile[1])
    return phasen


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unbekannt"


def oeffne_tresor(phase: str, begruendung: str, *, konfig: dict | None = None, jetzt: datetime | None = None) -> TresorFreigabe:
    """Öffnet den Tresor einmalig für eine Phase und trägt das im Protokoll ein."""
    _, protokoll = _einstellungen(konfig)
    if not phase.strip() or not begruendung.strip():
        raise ValueError("Phase und Begründung sind Pflicht")
    if "|" in phase + begruendung:
        raise ValueError("Phase und Begründung dürfen kein | enthalten")
    if phase in geoeffnete_phasen(protokoll):
        raise TresorGesperrt(
            f"Der Tresor wurde für „{phase}“ schon geöffnet und ist verbraucht. Erkenntnis notieren, "
            "auf den Entwicklungsdaten weiterarbeiten; neue Prüfung ist das Paper Trading."
        )
    if not protokoll.exists():
        protokoll.parent.mkdir(parents=True, exist_ok=True)
        protokoll.write_text(_KOPF, encoding="utf-8")
    zeitpunkt = (jetzt or datetime.now()).isoformat(timespec="minutes")
    with protokoll.open("a", encoding="utf-8") as datei:
        datei.write(f"| {zeitpunkt} | {phase} | {begruendung} | {_git_commit()} |\n")
    return TresorFreigabe(phase, begruendung)


_AKTIVE_FREIGABE: ContextVar["TresorFreigabe | None"] = ContextVar("tresor_freigabe", default=None)


@lru_cache(maxsize=1)
def _standard_sperre() -> tuple[date, Path]:
    return _einstellungen(None)


def datengrenze(konfig: dict | None = None) -> pd.Timestamp | None:
    """Letzter Tag, bis zu dem Datenlader Daten liefern dürfen; None nur bei gültiger, aktiver Tresor-Öffnung."""
    gesperrt_ab, _ = _einstellungen(konfig) if konfig is not None else _standard_sperre()
    if _AKTIVE_FREIGABE.get() is not None:      # nur über tresor_geoeffnet() gesetzt, dort gegen das Protokoll geprüft
        return None
    return pd.Timestamp(gesperrt_ab) - pd.Timedelta(days=1)


@contextmanager
def tresor_geoeffnet(freigabe: "TresorFreigabe", *, konfig: dict | None = None):
    """Hebt die Datumsgrenze für diesen Block auf; nur mit einer im Tresor-Protokoll eingetragenen Freigabe."""
    _, protokoll = _einstellungen(konfig)
    if freigabe is None or freigabe.phase not in geoeffnete_phasen(protokoll):
        raise TresorGesperrt("Datumsgrenze aufheben nur mit einer Freigabe aus oeffne_tresor() (Tresor-Protokoll)")
    token = _AKTIVE_FREIGABE.set(freigabe)
    try:
        yield
    finally:
        _AKTIVE_FREIGABE.reset(token)


def begrenze(daten, spalte: str | None = None, konfig: dict | None = None):
    """Entfernt Zeilen nach der Datumsgrenze (Index oder Datumsspalte `spalte`)."""
    grenze = datengrenze(konfig)
    if grenze is None or daten is None or len(daten) == 0:
        return daten
    datum = daten.index if spalte is None else daten[spalte]
    return daten[pd.to_datetime(datum) <= grenze]


def pruefe_zeitraum(ende, *, freigabe: TresorFreigabe | None = None, konfig: dict | None = None) -> None:
    """Wirft `TresorGesperrt`, wenn `ende` im gesperrten Bereich liegt und keine gültige Freigabe vorliegt."""
    gesperrt_ab, protokoll = _einstellungen(konfig)
    if pd.Timestamp(ende).date() < gesperrt_ab:
        return
    if freigabe is None:
        raise TresorGesperrt(
            f"Daten ab {gesperrt_ab} sind gesperrt (Tresor). Entwicklung nur bis {gesperrt_ab - pd.Timedelta(days=1):%d.%m.%Y}. "
            "Öffnen nur einmal pro Phase mit oeffne_tresor(), wenn Regeln und Parameter feststehen."
        )
    if freigabe.phase not in geoeffnete_phasen(protokoll):
        raise TresorGesperrt(f"Freigabe für „{freigabe.phase}“ steht nicht im Tresor-Protokoll")
