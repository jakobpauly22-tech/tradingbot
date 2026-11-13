"""Unbereinigte Schlusskurse 2011 bis zur Tresorgrenze von Tiingo nachladen (Weg A, Jakob 13.11.2026, docs/FUNDAMENTAL.md).

Zweck: Marktwert im Backtest = unbereinigter Kurs × SEC-Aktienzahl × Splits zwischen Meldung und Stichtag. Die Yahoo-Kurse
im Cache sind rückwirkend auch um Splits und Abspaltungen nach 2024 bereinigt; deren Faktoren blendet der Tresor aus.
Tiingo liefert `close` unbereinigt und `splitFactor` nur für echte Splits.

- Abgerufen wird nur der Zeitraum 01.01.2011 bis zur Datumsgrenze des Tresors (`endDate`): Der Cache enthält keine Daten
  aus dem Tresor. Ablage: daten/cache/tiingo/roh_bis_tresor/<ticker>.json.gz (Tiingo-Rohformat).
- Grenzen des kostenlosen Zugangs (Tiingo-Preisseite, geprüft 13.11.2026): 50 Anfragen je Stunde (TiingoClient, über
  Prozesse hinweg), 1.000 je Tag, 500 verschiedene Symbole und 1 GB Datenvolumen je Monat. Das Werkzeug bleibt mit
  Abstand darunter (Monat 450 Symbole, 900 MB; Tag 900 Anfragen) und hört an einer Grenze sauber auf.
- Wiederaufnehmbar: vorhandene Dateien werden übersprungen; Zähler je Monat und Tag in `stand.json` im Ablageordner.
"""
from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from tradingbot.daten.abruf import DatenFehler, VoruebergehenderFehler

START = "2011-01-01"
MONAT_SYMBOLE, MONAT_BYTES, TAG_ANFRAGEN = 450, 900 * 1024**2, 900


@dataclass
class Grenzen:
    monat_symbole: int = MONAT_SYMBOLE
    monat_bytes: int = MONAT_BYTES
    tag_anfragen: int = TAG_ANFRAGEN


def tiingo_ticker(yahoo_symbol: str) -> str:
    """Yahoo-Symbol → Tiingo-Ticker (BRK-B → brk-b; Tiingo schreibt Gattungen mit Bindestrich)."""
    return str(yahoo_symbol).strip().lower().replace(".", "-").replace("/", "-")


def ordner(cache_wurzel: Path | None = None) -> Path:
    from tradingbot.konfiguration import PROJEKT_WURZEL

    return Path(cache_wurzel or PROJEKT_WURZEL / "daten" / "cache" / "tiingo") / "roh_bis_tresor"


def ende_datum() -> str:
    """Letzter abgerufener Tag = Datumsgrenze des Tresors (backtest/tresor.py)."""
    from tradingbot.backtest.tresor import datengrenze

    grenze = datengrenze()
    if grenze is None:
        raise RuntimeError("Keine Datumsgrenze (Betriebsmodus?): Nachladen nur mit Tresorgrenze")
    return str(pd.Timestamp(grenze).date())


class Nachlader:
    def __init__(self, client, *, ablage: Path | None = None, grenzen: Grenzen | None = None, heute=None, ende: str | None = None):
        self.client, self.grenzen = client, grenzen or Grenzen()
        self.ablage = ablage or ordner(client.cache_wurzel)
        self.heute = heute or date.today
        self.ende = ende or ende_datum()
        self.ablage.mkdir(parents=True, exist_ok=True)

    # --- Stand -------------------------------------------------------------------------------
    def _stand_datei(self) -> Path:
        return self.ablage / "stand.json"

    def stand(self) -> dict:
        d = self._stand_datei()
        s = json.loads(d.read_text(encoding="utf-8")) if d.exists() else {}
        for k in ("monate", "tage", "fehler"):
            s.setdefault(k, {})
        return s

    def _speichern(self, s: dict) -> None:
        tmp = self._stand_datei().with_suffix(".tmp")
        tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._stand_datei())

    def datei(self, ticker: str) -> Path:
        return self.ablage / f"{ticker}.json.gz"

    def grenze_erreicht(self, s: dict) -> str | None:
        heute = self.heute()
        monat = s["monate"].get(heute.strftime("%Y-%m"), {"symbole": [], "bytes": 0})
        if len(monat["symbole"]) >= self.grenzen.monat_symbole:
            return f"Monatsgrenze {self.grenzen.monat_symbole} Symbole erreicht; weiter ab dem 1. des nächsten Monats"
        if monat["bytes"] >= self.grenzen.monat_bytes:
            return f"Monatsgrenze Datenvolumen ({self.grenzen.monat_bytes / 1024**2:.0f} MB) erreicht; weiter im nächsten Monat"
        if s["tage"].get(heute.isoformat(), 0) + 2 > self.grenzen.tag_anfragen:
            return f"Tagesgrenze {self.grenzen.tag_anfragen} Anfragen erreicht; weiter morgen"
        return None

    # --- Abruf -------------------------------------------------------------------------------
    def lade(self, ticker: str) -> str:
        """Lädt Metadaten und Rohkurse eines Tickers. Rückgabe: vorhanden | geladen | fehler | uebersprungen | grenze."""
        if self.datei(ticker).exists():
            return "vorhanden"
        s = self.stand()
        if s["fehler"].get(ticker, {}).get("dauerhaft"):
            return "uebersprungen"               # z. B. bei Tiingo nicht vorhanden: nicht bei jedem Neustart erneut abfragen
        if self.grenze_erreicht(s):
            return "grenze"
        heute = self.heute()
        monat = s["monate"].setdefault(heute.strftime("%Y-%m"), {"symbole": [], "bytes": 0})
        if ticker not in monat["symbole"]:
            monat["symbole"].append(ticker)
        s["tage"][heute.isoformat()] = s["tage"].get(heute.isoformat(), 0) + 2
        self._speichern(s)                       # Zähler vor dem Abruf: ein Abbruch zählt lieber zu viel als zu wenig
        try:
            meta = self.client.metadaten(ticker, max_alter=timedelta(days=36500))   # Name für die spätere Namensprüfung
            roh = self.client._holen(f"https://api.tiingo.com/tiingo/daily/{ticker}/prices",
                                     {"startDate": START, "endDate": self.ende, "resampleFreq": "daily"})
        except (DatenFehler, VoruebergehenderFehler) as f:
            s = self.stand()
            s["fehler"][ticker] = {"zeit": datetime.now().isoformat(timespec="seconds"), "fehler": str(f)[:200],
                                   "dauerhaft": isinstance(f, DatenFehler)}
            self._speichern(s)
            return "fehler"
        roh = [z for z in roh if str(z.get("date", ""))[:10] <= self.ende]       # Sicherheitsnetz Tresor
        inhalt = json.dumps({"ticker": ticker, "name": meta.get("name"), "start": START, "ende": self.ende,
                             "abgerufen_um": datetime.now().isoformat(timespec="seconds"), "kurse": roh})
        tmp = self.datei(ticker).with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            f.write(inhalt)
        os.replace(tmp, self.datei(ticker))
        s = self.stand()
        s["monate"][heute.strftime("%Y-%m")]["bytes"] += len(inhalt.encode("utf-8"))
        s["fehler"].pop(ticker, None)
        self._speichern(s)
        return "geladen"


def lade_rohkurse(ticker: str, *, ablage: Path | None = None) -> pd.DataFrame | None:
    """Unbereinigte Kurse aus der Ablage (Spalten close, split, volume; Index datum), höchstens bis zur Tresorgrenze."""
    from tradingbot.backtest.tresor import begrenze

    d = (ablage or ordner()) / f"{tiingo_ticker(ticker)}.json.gz"
    if not d.exists():
        return None
    with gzip.open(d, "rt", encoding="utf-8") as f:
        roh = json.load(f)
    t = pd.DataFrame(roh["kurse"])
    if t.empty:
        return None
    t.index = pd.DatetimeIndex(pd.to_datetime(t["date"]).dt.tz_localize(None).dt.normalize(), name="datum")
    split = t["splitFactor"].astype(float).replace(1.0, 0.0)
    ergebnis = pd.DataFrame({"close": t["close"].astype(float), "split": split, "volume": t["volume"].astype(float)}).sort_index()
    ergebnis.attrs["name"] = roh.get("name")
    return begrenze(ergebnis)
