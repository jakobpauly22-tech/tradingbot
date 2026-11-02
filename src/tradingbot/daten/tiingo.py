"""Tageskurse von Tiingo, vor allem für nicht mehr gelistete US-Aktien (Survivorship-Schutz).

- Schlüssel `TIINGO_API_KEY` aus .env, gesendet im Header (nie in der URL, nie im Log).
- Abruflimit pro Stunde aus config/fundamental.yaml (kostenloser Zugang: 50/h). Das Limit gilt über Prozesse
  hinweg: die Zeitpunkte der letzten Anfragen stehen in daten/cache/tiingo/anfragen.json.
- Je Ticker wird einmal die ganze Historie geladen und gecacht. Nicht mehr gelistete Titel ändern sich nicht mehr.
- Tiingo liefert unbereinigte Kurse plus `splitFactor` am Split-Tag. `normalisieren` rechnet auf die Yahoo-
  Konvention um (tradingbot.daten.kurse): Preise und Dividenden splitbereinigt, nicht dividendenbereinigt.
"""
from __future__ import annotations

import gzip
import io
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

from tradingbot.daten.abruf import DatenFehler, VoruebergehenderFehler
from tradingbot.daten.kurse import SPALTEN

log = logging.getLogger(__name__)

TIINGO_API = "https://api.tiingo.com/tiingo/daily"
TIINGO_LISTE = "https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip"


class TiingoLimitErreicht(VoruebergehenderFehler):
    """Stundenlimit erreicht und Warten nicht erlaubt."""


class TiingoClient:
    def __init__(self, schluessel: str | None = None, *, cache_wurzel: Path | None = None, anfragen_pro_stunde: int | None = None,
                 sitzung=None, uhr=time.time, schlafen=time.sleep, warten: bool = True):
        from tradingbot.konfiguration import PROJEKT_WURZEL, geheimnis, lade_konfiguration

        konfig = lade_konfiguration("fundamental").get("tiingo", {})
        self._schluessel = schluessel or geheimnis("TIINGO_API_KEY")
        self.cache_wurzel = Path(cache_wurzel or PROJEKT_WURZEL / "daten" / "cache" / "tiingo")
        self.anfragen_pro_stunde = int(anfragen_pro_stunde or konfig.get("anfragen_pro_stunde", 50))
        self.sitzung = sitzung or requests.Session()
        self._uhr, self._schlafen, self.warten = uhr, schlafen, warten

    # --- Stundenlimit über Prozesse hinweg ----------------------------------------------------------
    def _protokoll(self) -> Path:
        return self.cache_wurzel / "anfragen.json"

    def _limit_abwarten(self) -> None:
        datei = self._protokoll()
        jetzt = self._uhr()
        zeiten = json.loads(datei.read_text()) if datei.exists() else []
        zeiten = [z for z in zeiten if jetzt - z < 3600]
        if len(zeiten) >= self.anfragen_pro_stunde:
            warte = 3600 - (jetzt - min(zeiten)) + 1
            if not self.warten:
                raise TiingoLimitErreicht(f"Tiingo-Stundenlimit ({self.anfragen_pro_stunde}) erreicht, frei in {warte:.0f} s")
            log.info("Tiingo-Stundenlimit erreicht, warte %.0f s", warte)
            self._schlafen(warte)
            jetzt = self._uhr()
            zeiten = [z for z in zeiten if jetzt - z < 3600]
        zeiten.append(jetzt)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(json.dumps(zeiten))

    def _holen(self, url: str, params: dict) -> list | dict:
        self._limit_abwarten()
        try:
            antwort = self.sitzung.get(url, params=params, headers={"Authorization": f"Token {self._schluessel}"}, timeout=60)
        except requests.RequestException as fehler:
            raise VoruebergehenderFehler(f"Tiingo nicht erreichbar ({type(fehler).__name__})") from None
        if antwort.status_code == 200:
            return antwort.json()
        text = antwort.text[:200].replace(self._schluessel, "***")
        if antwort.status_code == 404:
            raise DatenFehler(f"Tiingo: {url} nicht gefunden")
        if antwort.status_code in (429, 500, 502, 503):
            raise VoruebergehenderFehler(f"Tiingo HTTP {antwort.status_code}: {text}")
        raise DatenFehler(f"Tiingo HTTP {antwort.status_code}: {text}")

    # --- Kurse ---------------------------------------------------------------------------------
    def historie(self, ticker: str, *, max_alter: timedelta | None = None) -> pd.DataFrame:
        """Ganze Tageshistorie eines Tiingo-Tickers im Bot-Format (Cache; `max_alter` None = nie erneuern)."""
        datei = self.cache_wurzel / "kurse" / f"{ticker.lower().replace('/', '_')}.json.gz"
        if datei.exists():
            alter = datetime.now(timezone.utc) - datetime.fromtimestamp(datei.stat().st_mtime, tz=timezone.utc)
            if max_alter is None or alter < max_alter:
                with gzip.open(datei, "rt", encoding="utf-8") as f:
                    return normalisieren(json.load(f))
        roh = self._holen(f"{TIINGO_API}/{ticker.lower()}/prices", {"startDate": "1990-01-01", "resampleFreq": "daily"})
        datei.parent.mkdir(parents=True, exist_ok=True)
        temporaer = datei.with_suffix(".tmp")
        with gzip.open(temporaer, "wt", encoding="utf-8") as f:
            json.dump(roh, f)
        os.replace(temporaer, datei)
        return normalisieren(roh)


def normalisieren(roh: list[dict]) -> pd.DataFrame:
    """Tiingo-Rohdaten → Bot-Format (splitbereinigt wie Yahoo, Dividende je splitbereinigter Aktie).

    Bereinigungsfaktor am Tag t = Produkt aller Split-Faktoren nach t; bereinigter Preis = Rohpreis / Faktor.
    """
    if not roh:
        return pd.DataFrame(columns=SPALTEN, index=pd.DatetimeIndex([], name="datum"), dtype=float)
    d = pd.DataFrame(roh)
    d.index = pd.DatetimeIndex(pd.to_datetime(d["date"]).dt.tz_localize(None).dt.normalize(), name="datum")
    d = d.sort_index()
    split = d["splitFactor"].astype(float).replace(0, 1.0)
    faktor = split[::-1].cumprod()[::-1].shift(-1).fillna(1.0)   # Splits strikt nach dem Tag
    ergebnis = pd.DataFrame({
        "open": d["open"] / faktor, "high": d["high"] / faktor, "low": d["low"] / faktor, "close": d["close"] / faktor,
        "volume": d["volume"] * faktor, "dividende": d["divCash"] / faktor,
        "split": split.where(split != 1.0, 0.0),
    }, index=d.index).astype(float)
    return ergebnis[SPALTEN]


def lade_tiingo_liste(cache_wurzel: Path | None = None, max_alter: timedelta = timedelta(days=7)) -> pd.DataFrame:
    """Liste aller Tiingo-Ticker mit Börse, Art und Zeitraum (kostenlose Datei, zählt nicht gegen das API-Limit)."""
    from tradingbot.konfiguration import PROJEKT_WURZEL

    datei = Path(cache_wurzel or PROJEKT_WURZEL / "daten" / "cache" / "tiingo") / "supported_tickers.zip"
    if not datei.exists() or datetime.now(timezone.utc) - datetime.fromtimestamp(datei.stat().st_mtime, tz=timezone.utc) > max_alter:
        antwort = requests.get(TIINGO_LISTE, timeout=120)
        if antwort.status_code != 200:
            raise DatenFehler(f"Tiingo-Tickerliste: HTTP {antwort.status_code}")
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_bytes(antwort.content)
    liste = pd.read_csv(io.BytesIO(datei.read_bytes()), compression="zip")
    for spalte in ("startDate", "endDate"):
        liste[spalte] = pd.to_datetime(liste[spalte], errors="coerce")
    return liste
