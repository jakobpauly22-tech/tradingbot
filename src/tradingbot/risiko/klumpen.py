"""Bewertungsbasis und Klumpen-Kennzahlen der Risiko-Übersicht (docs/RISIKO_UEBERSICHT.md, Abschnitte 1–5 und 8;
Festlegungen Jakob 25.11.2026). Reine Auswertung: liest das Journal nur und hat keine Wirkung auf Vorschläge oder Orders.

Bewertungsbasis je Buch (Abschnitt 3):
- Stückzahl aus `Journal.bestand`, Kurse in EUR je Buch als Eingabe (im Tageslauf die Schlusskurse, mit denen er den
  Buchwert gerechnet hat).
- Kasse in der **Konvention des Buchwerts**: `Journal.kasse` (Fremdwährung zum Kurs der Ausführung bzw. des Tauschs).
  Zusätzlich die Fremdwährungskasse zum Tageskurs (`Journal.kasse_je_waehrung` / Kurs); der Unterschied wird als eigene
  Zeile ausgewiesen, nie still angeglichen (offener Punkt, docs/BETRIEB.md „Offene Punkte zum Buchwert“).

Kennzahlen (Abschnitt 5; Quelle Klumpenrisiko: wissen/04_Finanzielles_Risikomanagement.md, docs/ROADMAP.md
„Was Risiko im Bot bedeutet“):
- Anteil wᵢ = Wertᵢ / Buchwert je Titel, Land/Region, Sektor, Anlageklasse und Währung (Notierung, wirtschaftlich); Kasse
  als eigener Block („Kasse“, in den Währungssichten unter ihrer Währung). Die Anteile ergeben 100 %.
- Größte Position und Anteil der fünf größten Positionen, jeweils am Buchwert.
- Herfindahl-Index HHI = Σ vᵢ² mit vᵢ = Wertᵢ / Σ Positionen (ohne Kasse); effektive Titelzahl = 1 / HHI.
  Annahme: Kasse ist kein Titel; ein Buch nur aus Kasse hat keinen HHI.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from tradingbot.risiko.zuordnung import UNBEKANNT, Zuordnung

DIMENSIONEN = ("titel", "land", "sektor", "anlageklasse", "waehrung_notierung", "waehrung_wirtschaftlich")
WAEHRUNGSSICHTEN = ("waehrung_notierung", "waehrung_wirtschaftlich")
KASSE = "Kasse"


@dataclass
class Posten:
    ticker: str
    stueck: float
    kurs_eur: float | None
    zuordnung: Zuordnung
    buecher: tuple[str, ...] = ()

    @property
    def wert_eur(self) -> float:
        return float("nan") if self.kurs_eur is None else self.stueck * self.kurs_eur


@dataclass
class Basis:
    """Bewertungsbasis eines Buchs oder eines Gesamtblocks."""

    name: str
    rolle: str | None
    posten: list[Posten]
    kasse_eur: float                                  # Konvention des Buchwerts (Journal.kasse)
    kasse_je_waehrung: dict[str, float]               # Originalbeträge (Journal.kasse_je_waehrung)
    fx: dict[str, float]                              # Währung → Einheiten je EUR (z. B. {"USD": 1,0967})
    buecher: tuple[str, ...] = ()
    doppelt: tuple[str, ...] = ()                     # Titel in mehreren Büchern (nur Gesamtblöcke)
    hinweise: list[str] = field(default_factory=list)

    @property
    def vollstaendig(self) -> bool:
        return all(p.kurs_eur is not None for p in self.posten)

    @property
    def positionen_eur(self) -> float:
        return sum(p.wert_eur for p in self.posten)

    @property
    def wert_eur(self) -> float:
        """Buchwert in der Konvention des Tageslaufs: Positionen zum Kurs + Journal.kasse."""
        return self.positionen_eur + self.kasse_eur

    @property
    def kasse_fremd_buchwert(self) -> float:
        """Fremdwährungskasse in EUR, wie sie im Buchwert steckt (Kurs der Ausführung bzw. des Tauschs)."""
        return self.kasse_eur - self.kasse_je_waehrung.get("EUR", 0.0)

    @property
    def kasse_fremd_tageskurs(self) -> float:
        """Fremdwährungskasse in EUR zum Tageskurs (nan, wenn ein Kurs fehlt)."""
        summe = 0.0
        for w, betrag in self.kasse_je_waehrung.items():
            if w == "EUR" or abs(betrag) < 1e-9:
                continue
            summe += betrag / self.fx[w] if self.fx.get(w) else float("nan")
        return summe


def rollen(betrieb: dict) -> dict[str, str | None]:
    """Rolle je Buch aus config/betrieb.yaml (`buecher.<buch>.rolle`, Abschnitt 2)."""
    return {n: (b or {}).get("rolle") for n, b in betrieb["buecher"].items()}


def arten(betrieb: dict) -> dict[str, str | None]:
    """Art je Buch (real | skalierung) aus config/betrieb.yaml."""
    return {n: (b or {}).get("art") for n, b in betrieb["buecher"].items()}


def buchbasis(journal, buch: str, kurse_eur: dict[str, float], fx: dict[str, float], rolle: str | None, zuordnen) -> Basis:
    """Bewertungsbasis eines Buchs aus dem Journal (nur lesend). `kurse_eur`: Kurs je Titel in EUR für dieses Buch,
    `zuordnen`: Ticker → Zuordnung."""
    posten, hinweise = [], []
    for ticker, stueck in sorted(journal.bestand(buch).items()):
        kurs = kurse_eur.get(ticker)
        if kurs is None:
            hinweise.append(f"{buch}: kein Kurs für {ticker} – Buch nicht vollständig bewertbar")
        z = zuordnen(ticker)
        posten.append(Posten(ticker, float(stueck), None if kurs is None else float(kurs), z, (buch,)))
    if rolle is None:
        hinweise.append(f"{buch}: Rolle unbekannt (config/betrieb.yaml buecher.{buch}.rolle fehlt) – keine Drift-Schwelle")
    return Basis(buch, rolle, posten, float(journal.kasse(buch)), dict(journal.kasse_je_waehrung(buch)), dict(fx), (buch,),
                 hinweise=hinweise)


def gesamtblock(name: str, basen: list[Basis]) -> Basis:
    """Gesamtblock aus mehreren Büchern (Abschnitt 1): gleiche Titel zusammengefasst, Titel aus mehreren Büchern markiert.
    Bei unterschiedlichem Kurs desselben Titels in zwei Büchern wird gemeldet und der Wert je Buch summiert."""
    je_titel: dict[str, list[Posten]] = {}
    for b in basen:
        for p in b.posten:
            je_titel.setdefault(p.ticker, []).append(p)
    posten, hinweise = [], []
    for ticker, liste in sorted(je_titel.items()):
        stueck = sum(p.stueck for p in liste)
        buecher = tuple(bb for p in liste for bb in p.buecher)
        kurse = {p.kurs_eur for p in liste}
        if None in kurse:
            kurs = None
        elif len(kurse) == 1:
            kurs = kurse.pop()
        else:
            wert = sum(p.wert_eur for p in liste)
            kurs = wert / stueck if stueck else None
            hinweise.append(f"{name}: {ticker} mit unterschiedlichen Kursen je Buch ({', '.join(f'{p.buecher[0]} {p.kurs_eur:.4f}' for p in liste)})")
        posten.append(Posten(ticker, stueck, kurs, liste[0].zuordnung, buecher))
    kasse_w: dict[str, float] = {}
    fx: dict[str, float] = {}
    for b in basen:
        for w, betrag in b.kasse_je_waehrung.items():
            kasse_w[w] = kasse_w.get(w, 0.0) + betrag
        fx.update(b.fx)
    doppelt = tuple(p.ticker for p in posten if len(p.buecher) > 1)
    return Basis(name, None, posten, sum(b.kasse_eur for b in basen), kasse_w, fx, tuple(n for b in basen for n in b.buecher),
                 doppelt, hinweise + [h for b in basen for h in b.hinweise])


def bloecke(basen: dict[str, Basis], betrieb: dict) -> dict[str, Basis]:
    """Die beiden Gesamtblöcke „real“ und „Skalierung“ (nie zusammengezählt)."""
    art = arten(betrieb)
    real = [b for n, b in basen.items() if art.get(n) == "real"]
    skal = [b for n, b in basen.items() if art.get(n) == "skalierung"]
    return {"real": gesamtblock("real gesamt", real), "skalierung": gesamtblock("Skalierungsbücher zusammen", skal)}


def _kasse_je_waehrung_buchwert(basis: Basis) -> dict[str, float]:
    """Kasse je Währung in EUR in der Konvention des Buchwerts: EUR-Kasse direkt, die Fremdwährungskasse des Buchwerts
    aufgeteilt im Verhältnis der Tageswerte (bei nur einer Fremdwährung genau dieser Betrag)."""
    erg = {"EUR": basis.kasse_je_waehrung.get("EUR", 0.0)}
    fremd = {w: b / basis.fx[w] for w, b in basis.kasse_je_waehrung.items()
             if w != "EUR" and abs(b) > 1e-9 and basis.fx.get(w)}
    rest = basis.kasse_fremd_buchwert
    summe = sum(fremd.values())
    if len(fremd) == 1:
        erg[next(iter(fremd))] = rest
    elif fremd and abs(summe) > 1e-9:
        for w, v in fremd.items():
            erg[w] = rest * v / summe
    elif abs(rest) > 1e-9:
        erg[UNBEKANNT] = rest
    return {w: v for w, v in erg.items() if abs(v) > 1e-9}


def anteile(basis: Basis, dimension: str) -> pd.Series:
    """Anteile am Buchwert je Ausprägung der Dimension, absteigend; Summe 1 (Kasse eingeschlossen)."""
    if dimension not in DIMENSIONEN:
        raise ValueError(f"unbekannte Dimension {dimension}")
    werte: dict[str, float] = {}
    for p in basis.posten:
        schluessel = p.ticker if dimension == "titel" else getattr(p.zuordnung, dimension)
        werte[schluessel] = werte.get(schluessel, 0.0) + p.wert_eur
    if dimension in WAEHRUNGSSICHTEN:
        for w, v in _kasse_je_waehrung_buchwert(basis).items():
            werte[w] = werte.get(w, 0.0) + v
    elif abs(basis.kasse_eur) > 1e-9:
        werte[KASSE] = werte.get(KASSE, 0.0) + basis.kasse_eur
    gesamt = basis.wert_eur
    return (pd.Series(werte, dtype=float) / gesamt).sort_values(ascending=False)


def hhi(basis: Basis) -> float:
    """HHI = Σ vᵢ², vᵢ = Wertᵢ / Σ Positionen (ohne Kasse); nan ohne Positionen."""
    summe = basis.positionen_eur
    if not basis.posten or not summe:
        return float("nan")
    return sum((p.wert_eur / summe) ** 2 for p in basis.posten)


def kennzahlen(basis: Basis) -> dict:
    """Klumpen-Kennzahlen eines Buchs oder Gesamtblocks (Abschnitt 5)."""
    wert = basis.wert_eur
    pos = sorted(basis.posten, key=lambda p: p.wert_eur, reverse=True)
    h = hhi(basis)
    fremd_tag = basis.kasse_fremd_tageskurs
    return {
        "name": basis.name,
        "buchwert_eur": wert,
        "kasse_eur": basis.kasse_eur,
        "kasse_anteil": basis.kasse_eur / wert if wert else float("nan"),
        "groesste": (pos[0].ticker, pos[0].wert_eur / wert) if pos else None,
        "top5_anteil": sum(p.wert_eur for p in pos[:5]) / wert if pos else 0.0,
        "hhi": h,
        "effektive_titel": 1 / h if h and not math.isnan(h) else float("nan"),
        "anteile": {d: anteile(basis, d) for d in DIMENSIONEN},
        "kasse_fremd_buchwert_eur": basis.kasse_fremd_buchwert,
        "kasse_fremd_tageskurs_eur": fremd_tag,
        "kasse_fremd_unterschied_eur": fremd_tag - basis.kasse_fremd_buchwert,
        "doppelt": basis.doppelt,
        "vollstaendig": basis.vollstaendig,
        "kennzeichen": sorted({p.zuordnung.kennzeichen for p in basis.posten}),
    }


def _prozent(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def drift_hinweise(basis: Basis, schwellen: dict) -> list[str]:
    """Drift-Hinweise je Rolle (Abschnitt 8, nur Anzeige): Einzelaktie über `core_einzelaktie` (Core) bzw.
    `satellite_einzelaktie` (Satellite) des Buchwerts. ETFs ohne Drift-Schwelle; Buch ohne Rolle ohne Hinweis."""
    schwelle = {"core": schwellen["core_einzelaktie"], "satellite": schwellen["satellite_einzelaktie"]}.get(basis.rolle or "")
    if schwelle is None:
        return []
    wert = basis.wert_eur
    erg = []
    for p in basis.posten:
        if p.zuordnung.art != "Einzelaktie" or not wert:
            continue
        a = p.wert_eur / wert
        if a > schwelle:
            erg.append(f"{basis.name}: {p.ticker} {_prozent(a)} des Buchwerts, über der Hinweisgrenze {_prozent(schwelle)} "
                       f"({basis.rolle}; nur Hinweis, kein Zwangsverkauf)")
    return erg


def buchwert_abgleich(basis: Basis, gespeichert: float | None, toleranz: float) -> str | None:
    """Meldung, wenn die Summe der Übersicht vom gespeicherten Buchwert abweicht (nie still angleichen)."""
    if gespeichert is None:
        return None
    if not basis.vollstaendig:
        return f"{basis.name}: Abgleich mit dem Buchwert nicht möglich (Kurs fehlt)"
    diff = basis.wert_eur - gespeichert
    if abs(diff) > toleranz:
        return (f"{basis.name}: Summe der Übersicht {basis.wert_eur:,.2f} € weicht vom gespeicherten Buchwert {gespeichert:,.2f} € "
                f"um {diff:+,.2f} € ab")
    return None
