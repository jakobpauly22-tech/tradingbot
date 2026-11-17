"""Dauer je Abschnitt des Tageslaufs und des Sendens (Jakob 17.11.2026). Nur Anzeige: ändert nichts am Ablauf, an
Freigabe, Senden, Journal oder Risk-Manager."""
from __future__ import annotations

import time

PRAEFIX = "Dauer je Abschnitt"


class Zeitmessung:
    """Misst nacheinander folgende Abschnitte. `abschnitt(name)` beendet den laufenden und beginnt den nächsten; gleich
    benannte Abschnitte werden addiert."""

    def __init__(self, uhr=time.perf_counter):
        self._uhr = uhr
        self._beginn = uhr()
        self._name: str | None = None
        self._seit = self._beginn
        self.dauer: dict[str, float] = {}

    def abschnitt(self, name: str | None) -> None:
        jetzt = self._uhr()
        if self._name is not None:
            self.dauer[self._name] = self.dauer.get(self._name, 0.0) + (jetzt - self._seit)
        self._name, self._seit = name, jetzt

    def zeile(self, titel: str = PRAEFIX) -> str:
        """Schließt den laufenden Abschnitt und gibt eine Zeile fürs Protokoll zurück."""
        self.abschnitt(None)
        gesamt = self._uhr() - self._beginn
        teile = "; ".join(f"{n} {_s(d)}" for n, d in self.dauer.items())
        return f"{titel}: {teile or '–'}; gesamt {_s(gesamt)}"


def _s(sekunden: float) -> str:
    return f"{sekunden:.1f} s".replace(".", ",")
