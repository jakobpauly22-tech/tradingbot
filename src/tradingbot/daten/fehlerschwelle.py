"""Fehlerschwelle für Datenwerkzeuge (Entscheidung Jakob 03.11.2026).

Liegt der Anteil an Lade- oder Prüffehlern über 5 %, bricht das Werkzeug ab und meldet das laut, statt eine
Statusdatei zu schreiben. Ein Fehler ist eine Ausnahme beim Laden oder Prüfen; ein reguläres Prüfergebnis wie
„Kursreihe ungültig“ ist kein Fehler. Damit ein stundenlanger Lauf früh stoppt, wird schon ab `mindestens`
bearbeiteten Einträgen laufend geprüft. Gehäufte Fehler am Anfang (z.B. Netzausfall) führen so bewusst früh zum
Abbruch, auch wenn der Anteil am Ende vielleicht unter 5 % gelegen hätte.
"""
from __future__ import annotations

import sys

SCHWELLE = 0.05


class FehlerschwelleUeberschritten(RuntimeError):
    """Zu viele Lade- oder Prüffehler; Ergebnisse werden nicht geschrieben."""


class Fehlerschwelle:
    def __init__(self, beschreibung: str, *, schwelle: float = SCHWELLE, mindestens: int = 40):
        self.beschreibung = beschreibung
        self.schwelle = schwelle
        self.mindestens = mindestens
        self.gesamt = 0
        self.fehler: list[str] = []

    @property
    def anteil(self) -> float:
        return len(self.fehler) / self.gesamt if self.gesamt else 0.0

    def zaehle(self, fehler: str | None = None) -> None:
        """Einen bearbeiteten Eintrag zählen (mit Fehlertext, falls er fehlgeschlagen ist); prüft laufend."""
        self.gesamt += 1
        if fehler:
            self.fehler.append(fehler)
        if self.gesamt >= self.mindestens:
            self.pruefe()

    def pruefe(self) -> None:
        if self.gesamt and self.anteil > self.schwelle:
            beispiele = "; ".join(sorted(set(self.fehler))[:3])
            raise FehlerschwelleUeberschritten(
                f"{self.beschreibung}: {len(self.fehler)} von {self.gesamt} Einträgen fehlerhaft ({self.anteil:.1%} > "
                f"{self.schwelle:.0%}). Abbruch, keine Statusdatei geschrieben. Beispiele: {beispiele}")


def laut_melden(fehler: Exception) -> int:
    """Fehlermeldung gut sichtbar auf stderr; gibt den Exit-Code 1 zurück."""
    rahmen = "!" * 80
    print(f"\n{rahmen}\nABBRUCH: {fehler}\n{rahmen}\n", file=sys.stderr, flush=True)
    return 1
