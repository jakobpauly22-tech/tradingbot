"""Gemeinsame Hilfen für Datenabrufe: Fehlerklassen, Drosselung, Wiederholung."""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, TypeVar

log = logging.getLogger(__name__)
T = TypeVar("T")

# Wartezeiten zwischen den Versuchen bei Netzfehlern (Verbindungsabbruch, Ruhezustand des Laptops), Jakob 15.11.2026:
# zusammen gut 9 Minuten, genug, bis das Netz nach dem Aufwachen wieder steht.
NETZ_PAUSEN_S: tuple[float, ...] = (5, 15, 30, 60, 120, 300)


class DatenFehler(RuntimeError):
    """Daten konnten nicht geladen werden oder sind unbrauchbar."""


class VoruebergehenderFehler(DatenFehler):
    """Fehler, bei dem sich ein neuer Versuch lohnt (Netz, Server, Abruflimit)."""


class Drossel:
    """Hält einen Mindestabstand zwischen zwei Abrufen ein (Abruflimits der Quellen).

    Thread-sicher (Laufzeit Schritt 3, Jakob 23.11.2026): Jeder Aufruf reserviert unter einer Sperre seinen Zeitpunkt
    (frühestens letzter Zeitpunkt + Abstand) und schläft außerhalb der Sperre bis dahin. Der Abstand gilt damit global
    über alle Threads, die dieselbe Drossel nutzen, nicht je Thread."""

    def __init__(self, min_abstand_s: float, uhr=time.monotonic, schlafen=time.sleep):
        self.min_abstand_s = min_abstand_s
        self._uhr = uhr
        self._schlafen = schlafen
        self._letzter: float | None = None
        self._sperre = threading.Lock()

    def warten(self) -> None:
        with self._sperre:
            jetzt = self._uhr()
            zeitpunkt = jetzt if self._letzter is None else max(jetzt, self._letzter + self.min_abstand_s)
            self._letzter = zeitpunkt
        if zeitpunkt > jetzt:
            self._schlafen(zeitpunkt - jetzt)


def mit_wiederholung(
    funktion: Callable[[], T],
    *,
    beschreibung: str,
    versuche: int = 3,
    pause_s: float = 2.0,
    wiederholen_bei: tuple[type[BaseException], ...] = (VoruebergehenderFehler,),
    schlafen: Callable[[float], None] | None = None,
    pausen: tuple[float, ...] | None = None,
) -> T:
    """Führt `funktion` aus und wiederholt bei vorübergehenden Fehlern mit wachsender Pause.

    Mit `pausen` gilt diese Folge von Wartezeiten (Versuche = Anzahl Pausen + 1) statt `versuche`/`pause_s`.

    Nach dem letzten Versuch bleibt ein vorübergehender Fehler ein `VoruebergehenderFehler`, damit Aufrufer
    z.B. auf einen älteren Cache ausweichen können; alle anderen werden zu `DatenFehler`.
    """
    schlafen = schlafen or time.sleep  # erst beim Aufruf auflösen (in Tests ersetzbar)
    if pausen is not None:
        versuche = len(pausen) + 1
    for versuch in range(1, versuche + 1):
        try:
            return funktion()
        except wiederholen_bei as fehler:
            if versuch == versuche:
                klasse = VoruebergehenderFehler if isinstance(fehler, VoruebergehenderFehler) else DatenFehler
                raise klasse(f"{beschreibung}: nach {versuche} Versuchen gescheitert ({fehler})") from None
            warte = pausen[versuch - 1] if pausen is not None else pause_s * 2 ** (versuch - 1)
            log.warning("%s: Versuch %d gescheitert (%s), neuer Versuch in %.0f s", beschreibung, versuch, fehler, warte)
            schlafen(warte)
    raise AssertionError("unerreichbar")
