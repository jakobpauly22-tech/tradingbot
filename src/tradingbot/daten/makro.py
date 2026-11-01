"""Makrodaten über FRED, mit historischen Datenständen über ALFRED (Look-ahead-Schutz).

Kernidee: Jede Serie wird als Tabelle mit Gültigkeitszeitraum gespeichert:

    datum | wert | gueltig_ab | gueltig_bis

`gueltig_ab` ist der Tag, ab dem der Wert öffentlich bekannt war. Für einen Stichtag gilt die Zeile,
deren Zeitraum den Stichtag enthält (`stand_am`). So sieht ein Backtest am 01.05.2023 das US-BIP für
Q1 2023 mit 26.466 Mrd. USD (Erstveröffentlichung) und nicht mit dem später revidierten Wert.

- Revidierte Serien (BIP, Inflation, Arbeitsmarkt): `gueltig_ab` = realtime_start aus ALFRED.
  Vor dem ersten ALFRED-Stand (z.B. CPI: 17.02.1994) gibt es bewusst keine Werte.
- Nicht revidierte Marktdaten (Zinsen, VIX): `gueltig_ab` = Datum + Veröffentlichungsverzögerung.

Der API-Schlüssel kommt nur aus .env und erscheint nie in Fehlermeldungen oder Logs.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import pandas as pd
import requests

from tradingbot.daten.abruf import DatenFehler, Drossel, VoruebergehenderFehler, mit_wiederholung
from tradingbot.daten.cache import ParquetCache, standard_cache

log = logging.getLogger(__name__)

FRED_URL = "https://api.stlouisfed.org/fred"
OFFEN = pd.Timestamp("2200-12-31")      # steht für FREDs 9999-12-31 („bis heute gültig“)
MAX_VINTAGES_JE_ABFRAGE = 2000         # Grenze der FRED-API
MAX_ZEILEN_JE_ABFRAGE = 100_000
BEREICH = "makro"
SPALTEN = ["datum", "wert", "gueltig_ab", "gueltig_bis"]

# Holer: (pfad, parameter ohne Schlüssel) -> JSON-Antwort
Holer = Callable[[str, dict], dict]

_fred_drossel = Drossel(min_abstand_s=0.6)  # FRED erlaubt 120 Abfragen pro Minute


def fred_holer(schluessel: str, *, sitzung=None, drossel: Drossel = _fred_drossel) -> Holer:
    """Erzeugt eine Abruffunktion für die FRED-API, die den Schlüssel nie nach außen gibt."""
    sitzung = sitzung or requests.Session()

    def einmal(pfad: str, parameter: dict) -> dict:
        drossel.warten()
        try:
            antwort = sitzung.get(
                f"{FRED_URL}/{pfad}",
                params={**parameter, "api_key": schluessel, "file_type": "json"},
                timeout=30,
            )
        except requests.RequestException as fehler:
            # Die Originalmeldung enthält die URL samt Schlüssel, deshalb nur den Fehlertyp weitergeben
            raise VoruebergehenderFehler(f"FRED nicht erreichbar ({type(fehler).__name__})") from None
        if antwort.status_code == 200:
            return antwort.json()
        try:
            text = antwort.json().get("error_message", "")
        except ValueError:
            text = ""
        text = f"FRED {pfad}: HTTP {antwort.status_code} {text}".replace(schluessel, "***")
        if antwort.status_code == 429 or antwort.status_code >= 500:
            raise VoruebergehenderFehler(text)
        raise DatenFehler(text)

    def holen(pfad: str, parameter: dict) -> dict:
        return mit_wiederholung(lambda: einmal(pfad, parameter), beschreibung=f"FRED {pfad} {parameter.get('series_id', '')}")

    return holen


def _beobachtungen(holen: Holer, parameter: dict) -> list[dict]:
    """Alle Beobachtungen einer Abfrage, seitenweise."""
    zeilen: list[dict] = []
    while True:
        antwort = holen("series/observations", {**parameter, "limit": MAX_ZEILEN_JE_ABFRAGE, "offset": len(zeilen)})
        teil = antwort.get("observations", [])
        zeilen.extend(teil)
        if len(teil) < MAX_ZEILEN_JE_ABFRAGE or len(zeilen) >= int(antwort.get("count", 0)):
            return zeilen


def _vintage_daten(holen: Holer, serie: str) -> list[date]:
    daten: list[str] = []
    while True:
        antwort = holen("series/vintagedates", {"series_id": serie, "limit": 10_000, "offset": len(daten)})
        teil = antwort.get("vintage_dates", [])
        daten.extend(teil)
        if len(teil) < 10_000:
            return [date.fromisoformat(d) for d in daten]


def _tabelle(zeilen: list[dict]) -> pd.DataFrame:
    if not zeilen:
        return pd.DataFrame({s: pd.Series(dtype="datetime64[ns]" if s != "wert" else float) for s in SPALTEN})

    def zeitpunkt(text: str) -> pd.Timestamp:
        return OFFEN if text.startswith("9999") else pd.Timestamp(text)

    tabelle = pd.DataFrame(
        {
            "datum": pd.to_datetime([z["date"] for z in zeilen]),
            "wert": pd.to_numeric([z["value"] for z in zeilen], errors="coerce"),  # "." = kein Wert
            "gueltig_ab": [zeitpunkt(z["realtime_start"]) for z in zeilen],
            "gueltig_bis": [zeitpunkt(z["realtime_end"]) for z in zeilen],
        }
    )
    tabelle["gueltig_ab"] = pd.to_datetime(tabelle["gueltig_ab"])
    tabelle["gueltig_bis"] = pd.to_datetime(tabelle["gueltig_bis"])
    return tabelle.drop_duplicates().sort_values(["datum", "gueltig_ab"]).reset_index(drop=True)


def fred_tabelle(serie: str, *, revidiert: bool, verzoegerung_tage: int = 1, holen: Holer) -> pd.DataFrame:
    """Lädt eine FRED-Serie als Tabelle mit Gültigkeitszeiträumen (siehe Moduldoku)."""
    if not revidiert:
        tabelle = _tabelle(_beobachtungen(holen, {"series_id": serie}))
        tabelle["gueltig_ab"] = tabelle["datum"] + pd.Timedelta(days=verzoegerung_tage)
        tabelle["gueltig_bis"] = OFFEN
        return tabelle

    # ALFRED: höchstens 2.000 Datenstände je Abfrage, daher in Abschnitte teilen. Jeder Abschnitt
    # reicht bis einen Tag vor dem nächsten, damit keine Lücke zwischen den Abschnitten entsteht.
    vintages = _vintage_daten(holen, serie)
    if not vintages:
        raise DatenFehler(f"FRED {serie}: keine Datenstände gefunden")
    abschnitte = [vintages[i : i + MAX_VINTAGES_JE_ABFRAGE] for i in range(0, len(vintages), MAX_VINTAGES_JE_ABFRAGE)]
    zeilen: list[dict] = []
    for nr, abschnitt in enumerate(abschnitte):
        ende = (abschnitte[nr + 1][0] - timedelta(days=1)).isoformat() if nr + 1 < len(abschnitte) else "9999-12-31"
        zeilen += _beobachtungen(
            holen, {"series_id": serie, "realtime_start": abschnitt[0].isoformat(), "realtime_end": ende}
        )
    return _tabelle(zeilen)


def stand_am(tabelle: pd.DataFrame, stichtag) -> pd.Series:
    """Werte einer Serie, wie sie am Stichtag öffentlich bekannt waren.

    Bedingung: gueltig_ab <= Stichtag <= gueltig_bis. Index = Beobachtungsdatum, fehlende Werte entfernt.
    """
    tag = pd.Timestamp(stichtag).normalize()
    maske = (tabelle["gueltig_ab"] <= tag) & (tabelle["gueltig_bis"] >= tag)
    werte = tabelle.loc[maske].sort_values("gueltig_ab").set_index("datum")["wert"]
    werte = werte[~werte.index.duplicated(keep="last")].sort_index().dropna()
    werte.index.name = "datum"
    return werte


def _serien_einstellung(serie: str, konfig: dict | None) -> dict:
    if konfig is None:
        from tradingbot.konfiguration import lade_konfiguration

        konfig = lade_konfiguration("daten")
    # Unbekannte Serien gelten vorsichtshalber als revidiert
    return konfig.get("fred", {}).get("serien", {}).get(serie, {"revidiert": True})


def lade_makro_tabelle(
    serie: str,
    *,
    cache: ParquetCache | None = None,
    holen: Holer | None = None,
    konfig: dict | None = None,
    jetzt: datetime | None = None,
    max_alter_stunden: float | None = None,
) -> pd.DataFrame:
    """Gültigkeitstabelle einer Serie aus dem Cache; neu geladen, wenn älter als `max_alter_stunden`."""
    cache = cache or standard_cache()
    jetzt = jetzt or datetime.now(timezone.utc)
    einstellung = _serien_einstellung(serie, konfig)
    if max_alter_stunden is None:
        from tradingbot.konfiguration import lade_konfiguration

        max_alter_stunden = (konfig or lade_konfiguration("daten"))["cache"]["makro_max_alter_stunden"]

    tabelle, meta = cache.lesen(BEREICH, serie)
    if tabelle is not None:
        alter = jetzt - datetime.fromisoformat(meta["abgerufen_um"])
        if alter < timedelta(hours=max_alter_stunden) and meta.get("revidiert") == bool(einstellung["revidiert"]):
            return tabelle

    if holen is None:
        from tradingbot.konfiguration import geheimnis

        holen = fred_holer(geheimnis("FRED_API_KEY"))
    tabelle = fred_tabelle(
        serie,
        revidiert=bool(einstellung["revidiert"]),
        verzoegerung_tage=int(einstellung.get("verzoegerung_tage", 1)),
        holen=holen,
    )
    cache.schreiben(
        BEREICH,
        serie,
        tabelle,
        {
            "quelle": "FRED/ALFRED" if einstellung["revidiert"] else "FRED",
            "revidiert": bool(einstellung["revidiert"]),
            "abgerufen_um": jetzt.isoformat(timespec="seconds"),
        },
    )
    log.info("FRED %s geladen: %d Zeilen", serie, len(tabelle))
    return tabelle


def makro_am_stichtag(serie: str, stichtag, **kwargs) -> pd.Series:
    """Für Backtests: die Serie mit dem Wissensstand des Stichtags (kein Look-ahead)."""
    werte = stand_am(lade_makro_tabelle(serie, **kwargs), stichtag)
    werte.name = serie
    return werte


def lade_makro(serie: str, start=None, ende=None, **kwargs) -> pd.Series:
    """Aktueller Datenstand einer Serie, optional auf [start, ende] begrenzt."""
    werte = makro_am_stichtag(serie, date.today(), **kwargs)
    return werte.loc[pd.Timestamp(start) if start else None : pd.Timestamp(ende) if ende else None]
