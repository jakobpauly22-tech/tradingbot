"""Zuordnung der Titel für die Risiko-Übersicht: Land, Sektor, Anlageklasse, Währung (docs/RISIKO_UEBERSICHT.md,
Abschnitt 4; Festlegungen Jakob 25.11.2026). Reine Auswertung ohne Wirkung auf Vorschläge oder Orders.

Regeln:
- **Einzelaktien (exakt):** aus den SEC-`submissions` im SEC-Cache des Betriebs. Land = Geschäftsadresse
  (`addresses.business`), US-Bundesstaaten zählen als USA; zusätzlich das Land der Inkorporation. Sektor = SIC-Division
  (A–K) und zweistellige Major Group. Ausgewiesen als „SIC“, nicht als GICS.
- **ETFs und ETCs (Näherung: Indexregion):** nur aus der Tabelle in `config/risiko_uebersicht.yaml`; nie anteilig auf
  Länder oder Sektoren aufgeteilt. Ein ETF, der dort fehlt, ist „unbekannt“ und wird gemeldet.
- **Kein Netz:** Gelesen wird nur aus dem Cache über `daten.schicht.lesepfad` (Probe: Schicht zuerst). Fehlt eine Angabe,
  ist sie „unbekannt“; es wird nie ein SEC-Client gebaut und nichts nachgeladen.

Schlüssel ist immer der Yahoo-Ticker (wie im Journal); IBKR-Symbole sind nur andere Namen desselben Titels.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path

EXAKT, NAEHERUNG, UNBEKANNT = "exakt", "Näherung", "unbekannt"
NAEHERUNG_INDEXREGION = "Näherung: Indexregion"
KEIN_SEKTOR = "kein Sektor (Anleihen, Gold)"

# SIC-Divisionen nach dem Standard Industrial Classification Manual 1987 (OSHA/SEC), Bereiche der vierstelligen Codes.
SIC_DIVISIONEN: tuple[tuple[int, int, str, str], ...] = (
    (100, 999, "A", "Land- und Forstwirtschaft, Fischerei"),
    (1000, 1499, "B", "Bergbau (inkl. Öl- und Gasförderung)"),
    (1500, 1799, "C", "Baugewerbe"),
    (2000, 3999, "D", "Verarbeitendes Gewerbe"),
    (4000, 4999, "E", "Verkehr, Kommunikation, Versorger"),
    (5000, 5199, "F", "Großhandel"),
    (5200, 5999, "G", "Einzelhandel"),
    (6000, 6799, "H", "Finanzen, Versicherungen, Immobilien"),
    (7000, 8999, "I", "Dienstleistungen"),
    (9100, 9729, "J", "Öffentliche Verwaltung"),
    (9900, 9999, "K", "Nicht zuordenbar"),
)

# Zweistellige Major Groups (SIC Manual 1987), deutsche Kurznamen. Fehlt eine Gruppe, wird nur ihre Nummer gezeigt.
SIC_MAJOR_GROUPS: dict[int, str] = {
    1: "Ackerbau", 2: "Viehzucht", 7: "Landwirtschaftliche Dienste", 8: "Forstwirtschaft", 9: "Fischerei",
    10: "Erzbergbau", 12: "Kohlebergbau", 13: "Öl- und Gasförderung", 14: "Abbau nichtmetallischer Mineralien",
    15: "Hochbau", 16: "Tiefbau", 17: "Ausbaugewerbe",
    20: "Nahrungsmittel und Getränke", 21: "Tabak", 22: "Textilien", 23: "Bekleidung", 24: "Holz", 25: "Möbel",
    26: "Papier", 27: "Druck und Verlage", 28: "Chemie und Pharma", 29: "Mineralölverarbeitung", 30: "Gummi und Kunststoff",
    31: "Leder", 32: "Steine, Glas, Beton", 33: "Metallerzeugung", 34: "Metallwaren",
    35: "Maschinen und Computer", 36: "Elektronik und Elektrotechnik", 37: "Fahrzeuge und Luftfahrt",
    38: "Mess-, Medizin- und Optikgeräte", 39: "Sonstige Fertigung",
    40: "Eisenbahn", 41: "Personennahverkehr", 42: "Güterkraftverkehr und Lager", 43: "Post", 44: "Schifffahrt",
    45: "Luftverkehr", 46: "Pipelines (ohne Erdgas)", 47: "Verkehrsdienste", 48: "Kommunikation",
    49: "Strom, Gas, Wasser, Entsorgung",
    50: "Großhandel Gebrauchsgüter", 51: "Großhandel Verbrauchsgüter",
    52: "Baumärkte und Gartenbedarf", 53: "Warenhäuser", 54: "Lebensmittelhandel", 55: "Autohandel und Tankstellen",
    56: "Bekleidungshandel", 57: "Möbel- und Elektronikhandel", 58: "Gastronomie", 59: "Sonstiger Einzelhandel",
    60: "Kreditinstitute", 61: "Sonstige Kreditgeber", 62: "Wertpapierhandel", 63: "Versicherungen",
    64: "Versicherungsvermittler", 65: "Immobilien", 67: "Holdings und Investmentgesellschaften",
    70: "Hotels", 72: "Persönliche Dienste", 73: "Unternehmensdienste und Software", 75: "Kfz-Dienste",
    76: "Reparaturdienste", 78: "Film", 79: "Freizeit und Unterhaltung", 80: "Gesundheitsdienste", 81: "Rechtsdienste",
    82: "Bildung", 83: "Soziale Dienste", 84: "Museen", 86: "Mitgliedsorganisationen",
    87: "Ingenieur-, Buchhaltungs- und Beratungsdienste", 88: "Private Haushalte", 89: "Sonstige Dienste",
    91: "Allgemeine Verwaltung", 92: "Justiz und öffentliche Sicherheit", 93: "Öffentliche Finanzen",
    94: "Personalprogramme", 95: "Umwelt- und Wohnungsprogramme", 96: "Wirtschaftsprogramme",
    97: "Nationale Sicherheit und Internationales", 99: "Nicht zuordenbar",
}

# EDGAR-Codes für US-Bundesstaaten und Gebiete (zweistellig, nur Buchstaben); alle übrigen Codes sind Länder.
US_STAATEN = frozenset(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA "
    "RI SC SD TN TX UT VT VA WA WV WI WY PR VI GU AS MP".split())


@dataclass
class Zuordnung:
    """Zuordnung eines Titels. `kennzeichen` gilt für Land/Region und Sektor (exakt, Näherung: Indexregion, unbekannt)."""

    ticker: str
    art: str                                   # Einzelaktie | ETF | ETC | unbekannt
    anlageklasse: str
    land: str                                  # Land (Einzelaktie) bzw. Region (ETF)
    sektor: str                                # SIC-Division bzw. „breit gestreut“ / KEIN_SEKTOR
    sektor_gruppe: str = "–"                   # SIC Major Group
    sic: int | None = None
    inkorporation: str = "–"
    waehrung_notierung: str = UNBEKANNT
    waehrung_wirtschaftlich: str = UNBEKANNT
    kennzeichen: str = UNBEKANNT
    hinweise: list[str] = field(default_factory=list)


def sic_division(sic: int | None) -> tuple[str, str] | None:
    """(Buchstabe, Name) der SIC-Division oder None."""
    if sic is None:
        return None
    for von, bis, code, name in SIC_DIVISIONEN:
        if von <= sic <= bis:
            return code, name
    return None


def sic_major_group(sic: int | None) -> str:
    """„NN Name“ der zweistelligen Major Group, ohne bekannten Namen nur „NN“."""
    if sic is None:
        return "–"
    gruppe = sic // 100
    name = SIC_MAJOR_GROUPS.get(gruppe)
    return f"{gruppe:02d} {name}" if name else f"{gruppe:02d}"


def _land(code: str | None, beschreibung: str | None) -> str | None:
    """EDGAR-Code: US-Bundesstaat → „USA“, sonst die Länderbezeichnung der SEC (oder der Code)."""
    if not code:
        return None
    code = code.strip().upper()
    if code in US_STAATEN:
        return "USA"
    return (beschreibung or "").strip() or code


def land_geschaeftssitz(submissions: dict) -> str | None:
    """Land der Geschäftsadresse aus den SEC-submissions (None, wenn nicht angegeben)."""
    adresse = (submissions.get("addresses") or {}).get("business") or {}
    if adresse.get("isForeignLocation") in (1, "1", True) and (adresse.get("country") or adresse.get("countryCode")):
        return adresse.get("country") or adresse.get("countryCode")
    return _land(adresse.get("stateOrCountry"), adresse.get("stateOrCountryDescription"))


def land_inkorporation(submissions: dict) -> str | None:
    return _land(submissions.get("stateOfIncorporation"), submissions.get("stateOfIncorporationDescription"))


class SecStammdaten:
    """Liest Ticker → CIK und submissions nur aus einem SEC-Rohdaten-Cache (Ordner wie `daten/betrieb/cache/sec`),
    ohne Netz. Probe: über `lesepfad` zuerst die Schicht."""

    def __init__(self, wurzel: Path):
        self.wurzel = Path(wurzel)
        self._cik: dict[str, int] | None = None

    @staticmethod
    def _json(datei: Path) -> dict | None:
        from tradingbot.daten.schicht import lesepfad

        datei = lesepfad(datei)
        if not datei.exists():
            return None
        with gzip.open(datei, "rt", encoding="utf-8") as f:
            return json.load(f)["daten"]

    def cik(self, ticker: str) -> int | None:
        if self._cik is None:
            tabelle = self._json(self.wurzel / "company_tickers.json.gz") or {}
            self._cik = {str(z["ticker"]).upper(): int(z["cik_str"]) for z in tabelle.values()}
        return self._cik.get(ticker.upper())

    def submissions(self, ticker: str) -> dict | None:
        cik = self.cik(ticker)
        if cik is None:
            return None
        return self._json(self.wurzel / "submissions" / f"CIK{cik:010d}.json.gz")


def zuordnen(ticker: str, *, etfs: dict, kontrakte: dict, sec: SecStammdaten) -> Zuordnung:
    """Zuordnung eines Titels (Abschnitt 4). `etfs` = Tabelle aus config/risiko_uebersicht.yaml, `kontrakte` = Abschnitt
    `kontrakte` aus config/kontrakte.yaml (Notierungswährung und Art)."""
    k = kontrakte.get(ticker) or {}
    notierung = k.get("waehrung") or UNBEKANNT
    art_kontrakt = (k.get("art") or "").lower()
    if ticker in etfs:
        e = etfs[ticker]
        return Zuordnung(ticker, "ETC" if art_kontrakt == "etc" else "ETF", e["anlageklasse"], e.get("region") or "–",
                         e.get("sektor") or KEIN_SEKTOR, waehrung_notierung=notierung,
                         waehrung_wirtschaftlich=e.get("waehrung_wirtschaftlich") or UNBEKANNT, kennzeichen=NAEHERUNG_INDEXREGION)
    if art_kontrakt in ("etf", "etc"):
        return Zuordnung(ticker, art_kontrakt.upper(), UNBEKANNT, UNBEKANNT, UNBEKANNT, waehrung_notierung=notierung,
                         hinweise=[f"{ticker}: {art_kontrakt.upper()} fehlt in config/risiko_uebersicht.yaml (etfs) – Zuordnung unbekannt"])
    s = sec.submissions(ticker)
    if s is None:
        return Zuordnung(ticker, "Einzelaktie" if art_kontrakt == "aktie" else UNBEKANNT, "Aktie" if art_kontrakt == "aktie" else UNBEKANNT,
                         UNBEKANNT, UNBEKANNT, waehrung_notierung=notierung, waehrung_wirtschaftlich=notierung,
                         hinweise=[f"{ticker}: nicht im SEC-Cache des Betriebs – Land und Sektor unbekannt (nichts nachgeladen)"])
    sic = int(s["sic"]) if s.get("sic") not in (None, "") else None
    division = sic_division(sic)
    land = land_geschaeftssitz(s)
    hinweise = []
    if land is None:
        hinweise.append(f"{ticker}: SEC ohne Geschäftsadresse – Land unbekannt")
    if division is None:
        hinweise.append(f"{ticker}: SEC ohne gültigen SIC-Code – Sektor unbekannt")
    return Zuordnung(ticker, "Einzelaktie", "Aktie", land or UNBEKANNT,
                     f"{division[0]} {division[1]}" if division else UNBEKANNT, sic_major_group(sic), sic,
                     land_inkorporation(s) or "–", notierung, notierung,
                     EXAKT if land and division else UNBEKANNT, hinweise)
