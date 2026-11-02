"""Ausschlussfilter der Fundamental-Engine (Entscheidungen Jakob 03.11.2026, config/fundamental.yaml `filter`).

- Piotroski: F ≤ 3 → raus. Bei 7 oder 8 von 9 Signalen gilt der auf 9 Punkte hochgerechnete Wert, kaufmännisch auf
  ganze Punkte gerundet (Entscheidung Jakob 03.11.2026: die Hochrechnung schätzt den wahrscheinlichsten ganzzahligen
  Wert der 9-Punkte-Skala, so werden Firmen mit und ohne fehlendes Signal gleich behandelt; 3 von 8 → 3,375 → 3 → raus,
  3 von 7 → 3,857 → 4 → bleibt). Bei weniger Signalen wird der Filter übersprungen (markiert).
- Altman:
  * verarbeitendes Gewerbe (SIC 2000–3999): Z (1968, Marktwert) in der Gefahrenzone → harter Ausschluss;
  * Versorger (SIC 4900–4999): kein Altman;
  * übrige: Z'' (Buchwert) in der Gefahrenzone allein ist nur ein Warnhinweis; Ausschluss nur zusammen mit einem zweiten
    Signal (Piotroski ≤ 3 oder negativer operativer Cashflow im letzten Geschäftsjahr). Grund: Z'' setzt gesunde Firmen
    mit negativem Buch-Eigenkapital durch Aktienrückkäufe in die Gefahrenzone (docs/FUNDAMENTAL.md).
- Beneish: M > −1,78 → raus; nicht berechenbar → Filter übersprungen (markiert).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Filterergebnis:
    ausgeschlossen: bool
    gruende: list[str] = field(default_factory=list)       # warum ausgeschlossen
    hinweise: list[str] = field(default_factory=list)      # Warnhinweise und Markierungen (übersprungen, hochgerechnet)


def kaufmaennisch_runden(x: float) -> int:
    """Rundet .5 immer auf (Python-round rundet .5 zur geraden Zahl)."""
    return math.floor(x + 0.5)


def piotroski_fuer_filter(p: dict) -> int | None:
    """Wert für den Filter: exakter Score bei 9 Signalen, sonst der hochgerechnete (7–8 Signale) kaufmännisch gerundet,
    sonst None."""
    if p["wert"] is not None:
        return p["wert"]
    hoch = p.get("wert_hochgerechnet")
    return None if hoch is None else kaufmaennisch_runden(hoch)


def anwenden(*, sic: int, piotroski: dict, altman: dict | None, beneish: dict, cfo_t: float | None, konfig: dict) -> Filterergebnis:
    """Wendet alle Ausschlussfilter auf eine Firma am Stichtag an."""
    f = konfig["filter"]
    ergebnis = Filterergebnis(False)
    industrie = f["altman"]["industrie_sic"][0] <= sic <= f["altman"]["industrie_sic"][1]
    versorger = f["altman"]["ohne_altman_sic"][0] <= sic <= f["altman"]["ohne_altman_sic"][1]

    f_score = piotroski_fuer_filter(piotroski)
    if f_score is None:
        ergebnis.hinweise.append("Piotroski übersprungen (weniger als 7 Signale)")
    else:
        if piotroski.get("hochgerechnet"):
            ergebnis.hinweise.append(f"Piotroski hochgerechnet ({piotroski['anzahl_signale']} von 9 Signalen, "
                                     f"{piotroski['wert_hochgerechnet']:.3f} → {f_score})")
        if f_score < f["piotroski_min"]:
            ergebnis.gruende.append(f"Piotroski {f_score} ≤ 3")
    piotroski_schwach = f_score is not None and f_score < f["piotroski_min"]

    if versorger:
        ergebnis.hinweise.append("Altman nicht angewendet (Versorger)")
    elif altman is None or altman.get("wert") is None:
        ergebnis.hinweise.append("Altman nicht berechenbar")
    elif altman["zone"] == "gefahr":
        if industrie:
            ergebnis.gruende.append(f"Altman Z {altman['wert']:.2f} in der Gefahrenzone (verarbeitendes Gewerbe)")
        else:
            zweites = []
            if piotroski_schwach:
                zweites.append("Piotroski ≤ 3")
            if cfo_t is not None and cfo_t < 0:
                zweites.append("negativer operativer Cashflow")
            if zweites:
                ergebnis.gruende.append(f"Altman Z'' {altman['wert']:.2f} in der Gefahrenzone und {', '.join(zweites)}")
            else:
                ergebnis.hinweise.append(f"Warnhinweis: Altman Z'' {altman['wert']:.2f} in der Gefahrenzone")

    if beneish.get("wert") is None:
        ergebnis.hinweise.append("Beneish übersprungen (nicht berechenbar)")
    elif beneish["wert"] > f["beneish_max"]:
        ergebnis.gruende.append(f"Beneish {beneish['wert']:.2f} > {f['beneish_max']}")

    ergebnis.ausgeschlossen = bool(ergebnis.gruende)
    return ergebnis
