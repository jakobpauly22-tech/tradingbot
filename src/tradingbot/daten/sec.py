"""Bilanzdaten aus SEC EDGAR (XBRL-Fakten) mit Point-in-Time-Schutz.

Quellen (kostenlos, offiziell):
- https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json  alle XBRL-Fakten eines Unternehmens
- https://data.sec.gov/submissions/CIK##########.json            Stammdaten (SIC-Code, frühere Namen, Filings)
- https://www.sec.gov/files/company_tickers.json                  heutige Ticker → CIK (nur aktive Titel!)

Regeln (Jakob, 02.11.2026; config/fundamental.yaml):
- Höchstens 10 Anfragen pro Sekunde (wir: 8), User-Agent mit Name und E-Mail aus .env, alles lokal cachen.
- Ein Wert ist erst ab dem Handelstag nach seinem Einreichungsdatum (`filed`) bekannt. Die Uhrzeit der
  Einreichung steht nicht in den XBRL-Fakten; ein 10-K von 16:30 Uhr darf nicht in das Signal vom selben
  Schlusskurs eingehen.
- Bei Restatements gilt der zuerst gemeldete Wert: Je Konzept, Einheit und Periode zählt die früheste
  Einreichung. Spätere Korrekturen (10-K/A) und Vorjahreszahlen in neueren Berichten ersetzen ihn nie; sie
  bleiben in der Rohtabelle für spätere Prüfungen erhalten.

Feiertage der US-Börse werden bei „Handelstag nach filed“ nicht berücksichtigt (nächster Werktag). Das ist
unschädlich: Fällt der Tag auf einen Feiertag, gibt es an ihm ohnehin keinen Kurs und kein Signal.
"""
from __future__ import annotations

import gzip
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from tradingbot.daten.abruf import DatenFehler, Drossel, VoruebergehenderFehler, mit_wiederholung

log = logging.getLogger(__name__)

SEC_DATA = "https://data.sec.gov"
SEC_WWW = "https://www.sec.gov"
SPALTEN = ["taxonomie", "konzept", "einheit", "start", "ende", "wert", "filed", "form", "accn", "fy", "fp", "frame"]


def cik10(cik) -> str:
    """CIK als zehnstellige Zeichenkette mit führenden Nullen, wie die SEC-URLs sie verlangen."""
    return f"{int(cik):010d}"


class SecClient:
    """HTTP-Zugriff auf EDGAR mit Drosselung, Wiederholung und Datei-Cache (gzip-JSON)."""

    def __init__(self, user_agent: str | None = None, *, cache_wurzel: Path | None = None, sitzung=None,
                 drossel: Drossel | None = None, max_alter: timedelta | None = None, jetzt=None):
        from tradingbot.konfiguration import PROJEKT_WURZEL, geheimnis, lade_konfiguration

        konfig = lade_konfiguration("fundamental")["sec"]
        self.user_agent = user_agent or geheimnis("SEC_USER_AGENT")
        self.cache_wurzel = Path(cache_wurzel or PROJEKT_WURZEL / "daten" / "cache" / "sec")
        self.sitzung = sitzung or requests.Session()
        self.drossel = drossel or Drossel(min_abstand_s=1.0 / float(konfig["max_anfragen_pro_sekunde"]))
        self.max_alter = max_alter or timedelta(days=float(konfig["cache_max_alter_tage"]))
        self._jetzt = jetzt or (lambda: datetime.now(timezone.utc))

    # --- Cache ------------------------------------------------------------------------------------
    def _cache_lesen(self, datei: Path) -> tuple[dict | None, datetime | None]:
        if not datei.exists():
            return None, None
        with gzip.open(datei, "rt", encoding="utf-8") as f:
            inhalt = json.load(f)
        return inhalt["daten"], datetime.fromisoformat(inhalt["abgerufen_um"])

    def _cache_schreiben(self, datei: Path, url: str, daten: dict, zeitpunkt: datetime) -> None:
        datei.parent.mkdir(parents=True, exist_ok=True)
        temporaer = datei.with_suffix(".tmp")
        with gzip.open(temporaer, "wt", encoding="utf-8") as f:
            json.dump({"url": url, "abgerufen_um": zeitpunkt.isoformat(timespec="seconds"), "daten": daten}, f)
        os.replace(temporaer, datei)

    # --- Abruf ------------------------------------------------------------------------------------
    def _holen(self, url: str) -> dict:
        def einmal():
            self.drossel.warten()
            try:
                antwort = self.sitzung.get(url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}, timeout=60)
            except requests.RequestException as fehler:
                raise VoruebergehenderFehler(f"SEC nicht erreichbar ({type(fehler).__name__})") from None
            if antwort.status_code == 200:
                return antwort.json()
            if antwort.status_code in (429, 500, 502, 503, 504):
                raise VoruebergehenderFehler(f"SEC HTTP {antwort.status_code} für {url}")
            if antwort.status_code == 404:
                raise DatenFehler(f"SEC: nicht gefunden ({url})")
            raise DatenFehler(f"SEC HTTP {antwort.status_code} für {url}")

        return mit_wiederholung(einmal, beschreibung=f"SEC {url}", pause_s=2.0)

    def json_mit_cache(self, url: str, datei: Path) -> tuple[dict, datetime]:
        """JSON aus dem Cache, wenn jünger als `max_alter`; sonst neu laden. Gibt (Daten, Abrufzeit) zurück."""
        daten, zeitpunkt = self._cache_lesen(datei)
        if daten is not None and self._jetzt() - zeitpunkt < self.max_alter:
            return daten, zeitpunkt
        try:
            daten_neu = self._holen(url)
        except VoruebergehenderFehler:
            if daten is not None:  # lieber etwas ältere Daten als gar keine; im Log vermerkt
                log.warning("SEC nicht erreichbar, nutze Cache vom %s für %s", zeitpunkt, url)
                return daten, zeitpunkt
            raise
        zeitpunkt = self._jetzt()
        self._cache_schreiben(datei, url, daten_neu, zeitpunkt)
        return daten_neu, zeitpunkt

    def companyfacts_aus_cache(self, cik) -> tuple[dict | None, datetime | None]:
        """companyfacts nur aus dem lokalen Cache, ohne Netzabruf (None, None, wenn nichts gecacht ist)."""
        return self._cache_lesen(self.cache_wurzel / "companyfacts" / f"CIK{cik10(cik)}.json.gz")

    def companyfacts(self, cik) -> tuple[dict, datetime]:
        return self.json_mit_cache(f"{SEC_DATA}/api/xbrl/companyfacts/CIK{cik10(cik)}.json",
                                   self.cache_wurzel / "companyfacts" / f"CIK{cik10(cik)}.json.gz")

    def submissions(self, cik) -> tuple[dict, datetime]:
        return self.json_mit_cache(f"{SEC_DATA}/submissions/CIK{cik10(cik)}.json",
                                   self.cache_wurzel / "submissions" / f"CIK{cik10(cik)}.json.gz")

    def submissions_seite(self, name: str) -> tuple[dict, datetime]:
        """Zusatzseite älterer Einreichungen (Name aus submissions['filings']['files'])."""
        return self.json_mit_cache(f"{SEC_DATA}/submissions/{name}", self.cache_wurzel / "submissions" / f"{name}.gz")

    def einreichungskopf(self, cik, accn: str) -> str:
        """Kopf (Header) einer Einreichung als Text; ändert sich nie, daher dauerhaft gecacht."""
        datei = self.cache_wurzel / "koepfe" / f"{accn}.txt.gz"
        if datei.exists():
            with gzip.open(datei, "rt", encoding="utf-8") as f:
                return f.read()
        ordner = f"{SEC_WWW}/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/{accn}"

        def einmal(url):
            self.drossel.warten()
            try:
                antwort = self.sitzung.get(url, headers={"User-Agent": self.user_agent}, timeout=60)
            except requests.RequestException as fehler:
                raise VoruebergehenderFehler(f"SEC nicht erreichbar ({type(fehler).__name__})") from None
            if antwort.status_code == 200:
                return antwort.text
            if antwort.status_code in (429, 500, 502, 503, 504):
                raise VoruebergehenderFehler(f"SEC HTTP {antwort.status_code} für {url}")
            raise DatenFehler(f"SEC HTTP {antwort.status_code} für {url}")

        # .hdr.sgml gibt es für alle Jahrgänge (klein); -index-headers.html nur für neuere Einreichungen
        try:
            text = mit_wiederholung(lambda: einmal(ordner + ".hdr.sgml"), beschreibung=f"SEC Kopf {accn}")
        except DatenFehler as fehler:
            if isinstance(fehler, VoruebergehenderFehler):
                raise
            text = mit_wiederholung(lambda: einmal(ordner + "-index-headers.html"), beschreibung=f"SEC Kopf {accn}")
        datei.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(datei, "wt", encoding="utf-8") as f:
            f.write(text)
        return text

    def entity_suche(self, text: str) -> list[tuple[int, str]]:
        """SEC-Firmensuche (wie das Suchfeld auf sec.gov): Liste (CIK, Name), beste Treffer zuerst."""
        import hashlib

        datei = self.cache_wurzel / "suche" / f"{hashlib.sha1(text.lower().encode()).hexdigest()}.json.gz"
        daten, _ = self.json_mit_cache(f"https://efts.sec.gov/LATEST/search-index?keysTyped={requests.utils.quote(text)}", datei)
        return [(int(h["_id"]), h["_source"].get("entity", "")) for h in daten.get("hits", {}).get("hits", [])]

    def ticker_tabelle(self) -> pd.DataFrame:
        """Heutige Ticker → CIK. Enthält nur aktive Titel; für historische Mitglieder nicht ausreichend."""
        daten, _ = self.json_mit_cache(f"{SEC_WWW}/files/company_tickers.json", self.cache_wurzel / "company_tickers.json.gz")
        tabelle = pd.DataFrame(list(daten.values())).rename(columns={"cik_str": "cik", "title": "name"})
        return tabelle[["ticker", "cik", "name"]]


# --- Faktentabelle und Point-in-Time ------------------------------------------------------------
def fakten_tabelle(companyfacts: dict) -> pd.DataFrame:
    """Alle XBRL-Fakten als Tabelle (eine Zeile je gemeldetem Wert und Einreichung)."""
    zeilen = []
    for taxonomie, konzepte in companyfacts.get("facts", {}).items():
        for konzept, inhalt in konzepte.items():
            for einheit, werte in inhalt.get("units", {}).items():
                for w in werte:
                    zeilen.append((taxonomie, konzept, einheit, w.get("start"), w["end"], w["val"], w["filed"],
                                   w.get("form"), w.get("accn"), w.get("fy"), w.get("fp"), w.get("frame")))
    tabelle = pd.DataFrame(zeilen, columns=SPALTEN)
    for spalte in ("start", "ende", "filed"):
        tabelle[spalte] = pd.to_datetime(tabelle[spalte])
    tabelle["wert"] = pd.to_numeric(tabelle["wert"], errors="coerce")
    from tradingbot.backtest.tresor import begrenze

    return begrenze(tabelle, "filed")            # Tresor: nur Einreichungen bis zur Datumsgrenze


def verfuegbar_ab(filed: pd.Series) -> pd.Series:
    """Nächster Werktag nach dem Einreichungsdatum."""
    tage = filed.to_numpy(dtype="datetime64[D]")
    return pd.Series(pd.to_datetime(np.busday_offset(tage, 1, roll="forward")), index=filed.index)


def erstmeldungen(fakten: pd.DataFrame) -> pd.DataFrame:
    """Je Konzept, Einheit und Periode der zuerst gemeldete Wert (Regel für Restatements).

    Bei gleicher Einreichung zählt die Originalfassung vor einer Berichtigung (Formular mit „/A“), danach die
    kleinere Accession-Nummer. Ergänzt die Spalte `verfuegbar_ab` (Handelstag nach filed).
    """
    if fakten.empty:
        return fakten.assign(verfuegbar_ab=pd.Series(dtype="datetime64[ns]"))
    sortiert = fakten.assign(_berichtigung=fakten["form"].fillna("").str.endswith("/A"))
    sortiert = sortiert.sort_values(["filed", "_berichtigung", "accn"])
    schluessel = ["taxonomie", "konzept", "einheit", "start", "ende"]
    erste = sortiert.drop_duplicates(subset=schluessel, keep="first").drop(columns="_berichtigung")
    erste = erste.assign(verfuegbar_ab=verfuegbar_ab(erste["filed"]))
    return erste.sort_values(["taxonomie", "konzept", "ende"]).reset_index(drop=True)


def _konzept_teile(name: str) -> tuple[str, str]:
    taxonomie, _, konzept = name.partition(":")
    return taxonomie, konzept


def _ist_jahr(tabelle: pd.DataFrame, jahresdauer: tuple[int, int]) -> pd.Series:
    dauer = (tabelle["ende"] - tabelle["start"]).dt.days
    return dauer.between(*jahresdauer)


def geschaeftsjahresenden(erst: pd.DataFrame, stichtag, jahresdauer=(350, 380)) -> pd.DatetimeIndex:
    """Enden der Geschäftsjahre, die am Stichtag bekannt sind (aus Jahreswerten beliebiger Konzepte)."""
    bekannt = erst[(erst["verfuegbar_ab"] <= pd.Timestamp(stichtag)) & erst["start"].notna()]
    return pd.DatetimeIndex(sorted(bekannt.loc[_ist_jahr(bekannt, jahresdauer), "ende"].unique()))


def kennzahl_jahreswerte(erst: pd.DataFrame, definition: dict, stichtag, jahresdauer=(350, 380)) -> pd.DataFrame:
    """Jahreswerte einer Kennzahl, wie sie am Stichtag bekannt waren.

    `definition` aus config/fundamental.yaml (art, einheit, konzepte). Je Geschäftsjahresende gilt der erste
    Kandidat in `konzepte`, der einen Wert hat (Unternehmen wechseln über die Jahre die Begriffe).
    Ergebnis: Index = Geschäftsjahresende, Spalten wert, konzept, filed.
    """
    from tradingbot.backtest.tresor import begrenze

    stichtag = pd.Timestamp(stichtag)
    erst = begrenze(erst, "filed")               # Tresor: auch Erstmeldungen aus dem Cache nur bis zur Datumsgrenze
    bekannt = erst[(erst["verfuegbar_ab"] <= stichtag) & (erst["einheit"] == definition["einheit"])]
    art = definition["art"]
    enden = geschaeftsjahresenden(erst, stichtag, jahresdauer) if art == "stichtag" else None
    teile = []
    for rang, name in enumerate(definition["konzepte"]):
        taxonomie, konzept = _konzept_teile(name)
        k = bekannt[(bekannt["taxonomie"] == taxonomie) & (bekannt["konzept"] == konzept)]
        if art == "dauer":
            k = k[k["start"].notna() & _ist_jahr(k, jahresdauer)]
        elif art == "stichtag":
            k = k[k["start"].isna() & k["ende"].isin(enden)]
        elif art == "letzter":
            k = k[k["start"].isna()]
        else:
            raise ValueError(f"Unbekannte Art {art!r}")
        teile.append(k.assign(_rang=rang))
    alle = pd.concat(teile) if teile else pd.DataFrame(columns=[*erst.columns, "_rang"])
    if alle.empty:
        return pd.DataFrame(columns=["wert", "konzept", "filed"], index=pd.DatetimeIndex([], name="ende"))
    alle = alle.sort_values(["ende", "_rang"]).drop_duplicates(subset="ende", keep="first")
    ergebnis = alle.set_index("ende")[["wert", "konzept", "filed"]]
    ergebnis.index.name = "ende"
    return ergebnis


def abdeckung(erst: pd.DataFrame, kennzahlen: dict, stichtag, max_alter_tage: int = 460) -> dict[str, bool]:
    """Welche Kennzahlen sind am Stichtag für das letzte Geschäftsjahr vorhanden (nicht älter als ~15 Monate)?"""
    stichtag = pd.Timestamp(stichtag)
    ergebnis = {}
    for name, d in kennzahlen.items():
        werte = kennzahl_jahreswerte(erst, d if d["art"] != "letzter" else {**d, "art": "letzter"}, stichtag)
        ergebnis[name] = bool(len(werte)) and (stichtag - werte.index.max()).days <= max_alter_tage
    return ergebnis


def letzter_wert(erst: pd.DataFrame, definition: dict, stichtag) -> float | None:
    """Jüngster am Stichtag bekannte Wert (z.B. ausstehende Aktien vom Deckblatt des letzten Berichts)."""
    werte = kennzahl_jahreswerte(erst, {**definition, "art": "letzter"}, stichtag)
    return float(werte["wert"].iloc[-1]) if len(werte) else None


# --- Bequemer Zugang mit Cache der aufbereiteten Tabelle ----------------------------------------
def lade_erstmeldungen(cik, *, client: SecClient | None = None, cache=None) -> pd.DataFrame:
    """Erstmeldungen eines Unternehmens; aufbereitete Tabelle im Parquet-Cache, solange die Rohdaten gleich sind."""
    from tradingbot.daten.cache import standard_cache

    client = client or SecClient()
    cache = cache or standard_cache()
    roh, abgerufen = client.companyfacts(cik)
    tabelle, meta = cache.lesen("sec_erstmeldungen", cik10(cik))
    if tabelle is not None and meta.get("roh_abgerufen_um") == abgerufen.isoformat(timespec="seconds"):
        return tabelle
    tabelle = erstmeldungen(fakten_tabelle(roh))
    cache.schreiben("sec_erstmeldungen", cik10(cik), tabelle,
                    {"quelle": "SEC companyfacts", "roh_abgerufen_um": abgerufen.isoformat(timespec="seconds"),
                     "unternehmen": roh.get("entityName")})
    tabelle.attrs["unternehmen"] = roh.get("entityName")
    return tabelle


def stammdaten(cik, *, client: SecClient | None = None) -> dict:
    """Name, SIC-Code und Branche, frühere Namen, Geschäftsjahresende aus den Submissions."""
    client = client or SecClient()
    s, _ = client.submissions(cik)
    return {
        "cik": int(s["cik"]),
        "name": s.get("name"),
        "sic": int(s["sic"]) if s.get("sic") else None,
        "branche": s.get("sicDescription"),
        "tickers": s.get("tickers", []),
        "fruehere_namen": [n.get("name") for n in s.get("formerNames", [])],
        "geschaeftsjahresende": s.get("fiscalYearEnd"),
    }


def ist_bank_oder_versicherung(sic: int | None, konfig: dict | None = None) -> bool:
    """Banken und Versicherungen nach SIC-Bereichen (config/fundamental.yaml); bekommen weder Altman noch Beneish."""
    if sic is None:
        return False
    if konfig is None:
        from tradingbot.konfiguration import lade_konfiguration

        konfig = lade_konfiguration("fundamental")
    u = konfig["universum"]
    return any(a <= sic <= b for a, b in u["sic_banken"] + u["sic_versicherungen"])
