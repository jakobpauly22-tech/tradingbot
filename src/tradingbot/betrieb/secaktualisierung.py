"""SEC-Aktualisierung des Betriebs (Schritt 2; Festlegung Jakob 23.11.2026, docs/BETRIEB.md, Abschnitt „SEC-Aktualisierung
im Betrieb“). Aufruf über tools/sec_aktualisieren.py, getrennt vom Abendlauf.

Ablauf je CIK (heutige Mitglieder des Betriebsuniversums plus Vorgänger):
1. companyfacts frisch laden (ohne Cache), daraus die Erstmeldungen bilden und gegen den bisherigen Stand prüfen:
   - alle bisherigen Erstmeldungen unverändert (Spalten `PRUEF_SPALTEN`), neu hinzukommen dürfen nur Zeilen;
   - neue Zeilen nur mit `filed` ab der Grenze = Abrufdatum des bisherigen Stands minus `PUFFER_TAGE` (Stand vom
     02.11.2026 → ab 30.10.2026; Verzögerung der SEC-API).
   Bestanden: companyfacts übernehmen, Erstmeldungen und Aktienfakten neu bauen. Verletzt: CIK behält den alten Stand.
2. SIC-Historie: submissions frisch, 10-K-Köpfe nur, wenn sie fehlen; bestehende Einträge müssen unverändert bleiben,
   neue werden nur angehängt. Verletzt: alter Eintrag bleibt.
3. `STAND.json` (in der Wurzel der SEC-Rohdaten des Betriebs): Zeitpunkt, `erfolgreich`, Stand je CIK, `letzter_erfolg`
   (nur ein erfolgreicher Lauf setzt ihn neu). Wird immer geschrieben, auch bei Fehlerschwelle oder Abbruch (403).

Point-in-time bleibt wie bisher über `filed` (daten/sec.py); die Prüfregel sorgt zusätzlich dafür, dass eine spätere
Korrektur der SEC nie einen zuerst gemeldeten Wert ersetzt.
"""
from __future__ import annotations

import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
import requests

from tradingbot.daten.abruf import DatenFehler, VoruebergehenderFehler
from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten
from tradingbot.daten.sec import SecGesperrt, cik10, erstmeldungen, fakten_tabelle

PRUEF_SPALTEN = ["taxonomie", "konzept", "einheit", "start", "ende", "wert", "filed", "accn", "form"]
PUFFER_TAGE = 3                       # 02.11.2026 − 3 Tage = 30.10.2026 (Jakob 23.11.2026)
STAND_DATEI = "STAND.json"
NETZ_AUSFAELLE_BIS_ABBRUCH = 3        # so viele CIKs hintereinander ohne Netz → Lauf abbrechen

UEBERNOMMEN, ALTER_STAND, FEHLER, OHNE_DATEN = "übernommen", "alter Stand", "Fehler", "ohne Daten"


# --- Prüfregeln ---------------------------------------------------------------------------------------------------
def _zeilen(tabelle: pd.DataFrame | None) -> Counter:
    """Erstmeldungen als Mehrfachmenge von Tupeln über `PRUEF_SPALTEN` (NaN/NaT → None)."""
    if tabelle is None or not len(tabelle):
        return Counter()
    t = tabelle[PRUEF_SPALTEN].astype(object)
    t = t.where(t.notna(), None)
    return Counter(tuple(z) for z in t.itertuples(index=False, name=None))


def grenze_fuer(alt_abgerufen: datetime | None) -> pd.Timestamp | None:
    """Früheste erlaubte `filed` neuer Zeilen: Abrufdatum des bisherigen Stands minus `PUFFER_TAGE` (None ohne Stand)."""
    if alt_abgerufen is None:
        return None
    return pd.Timestamp(alt_abgerufen.date()) - pd.Timedelta(days=PUFFER_TAGE)


def pruefe_erstmeldungen(alt: pd.DataFrame | None, neu: pd.DataFrame, grenze: pd.Timestamp | None) -> tuple[bool, str, list]:
    """(bestanden, Text, neue Zeilen). Bisherige Zeilen müssen alle unverändert bleiben; neue nur mit filed ≥ grenze."""
    a, n = _zeilen(alt), _zeilen(neu)
    weg = a - n
    neue = list((n - a).elements())
    if weg:
        beispiele = "; ".join(f"{z[1]} {z[4]} filed {z[6]} accn {z[7]}" for z in list(weg.elements())[:3])
        return False, f"{sum(weg.values())} bisherige Erstmeldungen geändert oder entfernt (z. B. {beispiele})", neue
    if grenze is not None:
        zu_alt = [z for z in neue if z[6] is not None and pd.Timestamp(z[6]) < grenze]
        if zu_alt:
            beispiele = "; ".join(f"{z[1]} {z[4]} filed {pd.Timestamp(z[6]).date()}" for z in zu_alt[:3])
            return False, (f"{len(zu_alt)} neue Erstmeldungen mit filed vor {grenze.date()} (z. B. {beispiele})"), neue
    return True, f"{len(neue)} neue Erstmeldungen", neue


def pruefe_sic(alt: list, neu: list) -> tuple[bool, str]:
    """Bestehende SIC-Einträge unverändert, neue nur angehängt."""
    alt, neu = [(pd.Timestamp(d), int(s)) for d, s in alt], [(pd.Timestamp(d), int(s)) for d, s in neu]
    if neu[:len(alt)] != alt:
        return False, f"SIC-Historie geändert: bisher {alt}, neu {neu}"
    return True, f"{len(neu) - len(alt)} neue SIC-Einträge"


# --- Messung ------------------------------------------------------------------------------------------------------
class ZaehlendeSitzung(requests.Session):
    """requests.Session, die Zeitpunkt, Art und Größe (entpackt) jeder Anfrage festhält."""

    def __init__(self):
        super().__init__()
        self.anfragen: list[tuple[float, str, int, int, int]] = []    # (Zeit, Art, Status, Bytes entpackt, Bytes übertragen)

    def get(self, url, **kwargs):
        zeit = time.monotonic()
        antwort = super().get(url, **kwargs)
        art = ("companyfacts" if "/companyfacts/" in url else "submissions" if "/submissions/" in url
               else "kopf" if url.endswith(".hdr.sgml") or "/Archives/" in url else "sonstige")
        uebertragen = int(antwort.headers.get("Content-Length") or 0) or len(antwort.content)
        self.anfragen.append((zeit, art, antwort.status_code, len(antwort.content), uebertragen))
        return antwort


def hoechste_rate(zeiten: list[float], fenster_s: float = 1.0) -> int:
    """Höchste Zahl von Anfragen in einem beliebigen Fenster von `fenster_s` Sekunden."""
    zeiten, hoechste, links = sorted(zeiten), 0, 0
    for rechts, t in enumerate(zeiten):
        while t - zeiten[links] >= fenster_s:
            links += 1
        hoechste = max(hoechste, rechts - links + 1)
    return hoechste


# --- Lauf ---------------------------------------------------------------------------------------------------------
@dataclass
class Ergebnis:
    beginn: datetime
    je_cik: dict = field(default_factory=dict)
    erfolgreich: bool = False
    abbruch: str | None = None
    meldungen: list = field(default_factory=list)

    def zaehlen(self) -> Counter:
        return Counter(e["stand"] for e in self.je_cik.values())


def ciks_betrieb(universum: pd.DataFrame, tag) -> list[int]:
    """Heutige Mitglieder des Betriebsuniversums plus Vorgänger-CIKs (Festlegung: etwa 550)."""
    from tradingbot.daten.universum import mitglieder_am

    aktiv = mitglieder_am(universum, pd.Timestamp(tag))
    ciks = {int(c) for c in aktiv["cik"].dropna()}
    ciks |= {int(c) for liste in aktiv["vorgaenger_ciks"] if liste is not None for c in list(liste)}
    return sorted(ciks)


def _fakten(cik: int, client, jetzt) -> dict:
    """Schritt 1 für eine CIK (siehe Moduldoku); gibt den Eintrag für STAND.json zurück (ohne SIC)."""
    from tradingbot.daten.sec import lade_erstmeldungen
    from tradingbot.engines.fundamental.aktienzahl import lade_aktienfakten

    alt_roh, alt_abgerufen = client.companyfacts_aus_cache(cik)
    try:
        neu_roh = client.companyfacts_holen(cik)
    except DatenFehler as f:
        if alt_roh is None and "nicht gefunden" in str(f) and not isinstance(f, VoruebergehenderFehler):
            return {"stand": OHNE_DATEN, "text": "keine companyfacts bei der SEC (404), auch bisher nicht"}
        raise
    alt = erstmeldungen(fakten_tabelle(alt_roh)) if alt_roh is not None else None
    neu = erstmeldungen(fakten_tabelle(neu_roh))
    ok, text, neue = pruefe_erstmeldungen(alt, neu, grenze_fuer(alt_abgerufen))
    eintrag = {"neue_zeilen": len(neue), "bisher_abgerufen_um": alt_abgerufen.isoformat(timespec="seconds") if alt_abgerufen else None,
               "neueste_filed": max((str(pd.Timestamp(z[6]).date()) for z in neue if z[6] is not None), default=None)}
    if not ok:
        return {**eintrag, "stand": ALTER_STAND, "text": text}
    zeitpunkt = jetzt()
    client.companyfacts_speichern(cik, neu_roh, zeitpunkt)
    lade_erstmeldungen(cik, client=client)                       # liest das eben Gespeicherte, baut die Tabelle neu
    lade_aktienfakten([cik])                                     # Aktienfakten (Jahr) offline neu
    lade_aktienfakten([cik], mit_quartalen=True)                 # und Quartale
    return {**eintrag, "stand": UEBERNOMMEN, "text": text, "abgerufen_um": zeitpunkt.isoformat(timespec="seconds")}


def _sic(cik: int, client, client_frisch, bisher: list) -> tuple[dict, list | None]:
    """Schritt 2 für eine CIK: (Eintrag, neue Historie oder None, wenn der alte Stand bleibt)."""
    from tradingbot.daten.universum import sic_historie

    client_frisch.submissions(cik)                               # submissions frisch (Zusatzseiten ändern sich nicht)
    neu = [(d, s) for d, s in sic_historie(cik, client) if s is not None]
    ok, text = pruefe_sic(bisher, neu)
    return ({"sic": UEBERNOMMEN if ok else ALTER_STAND, "sic_text": text, "sic_neu": len(neu) - len(bisher) if ok else 0},
            neu if ok else None)


def aktualisieren(ciks: list[int], *, client, client_frisch, sec_tabellen, jetzt=None,
                  fortschritt=None) -> Ergebnis:
    """Ganzer Lauf über `ciks`. `client`: SecClient ohne Nachladen (Betriebs-Cache), `client_frisch`: derselbe Cache mit
    erzwungenem Nachladen (nur submissions), `sec_tabellen`: Parquet-Cache des Betriebs (SIC-Historie).
    Schreibt am Ende `STAND.json` (immer) und die SIC-Historie (geprüfte CIKs)."""
    jetzt = jetzt or (lambda: datetime.now(timezone.utc))
    erg = Ergebnis(beginn=jetzt())
    tabelle, _ = sec_tabellen.lesen("universum", "sic_historie")
    sic = {} if tabelle is None else {int(c): [(d, int(s)) for d, s in zip(g["gueltig_ab"], g["sic"])] for c, g in tabelle.groupby("cik")}
    sic_geaendert = False
    schwelle = Fehlerschwelle("SEC-Aktualisierung je CIK")
    netz_aus = 0
    try:
        for nr, cik in enumerate(ciks, 1):
            fehler = None
            try:
                eintrag = _fakten(cik, client, jetzt)
                eintrag["fakten"] = eintrag["stand"]                 # Stand der companyfacts getrennt vom SIC-Stand
                sic_eintrag, neu = _sic(cik, client, client_frisch, sic.get(cik, []))   # auch ohne companyfacts
                eintrag.update(sic_eintrag)
                if neu is not None and neu != sic.get(cik, []):
                    sic[cik], sic_geaendert = neu, True
                if sic_eintrag["sic"] == ALTER_STAND:
                    # Gesamtstand „alter Stand“, sobald ein Teil den alten Stand behält; `fakten` und `sic` nennen den Teil
                    eintrag["stand"], eintrag["text"] = ALTER_STAND, f"{eintrag['text']}; {sic_eintrag['sic_text']}"
                netz_aus = 0
            except SecGesperrt as f:
                erg.je_cik[str(cik)] = {"stand": FEHLER, "text": str(f)}
                erg.abbruch = str(f)
                break
            except DatenFehler as f:
                fehler = f"{type(f).__name__}: {f}"[:300]
                eintrag = {"stand": FEHLER, "text": fehler}
                netz_aus = netz_aus + 1 if isinstance(f, VoruebergehenderFehler) else 0
            erg.je_cik[str(cik)] = eintrag
            try:
                schwelle.zaehle(fehler)                          # bricht ab 40 CIKs bei mehr als 5 % Fehlern früh ab
            except FehlerschwelleUeberschritten as f:
                erg.abbruch = str(f).replace(" Abbruch, keine Statusdatei geschrieben.", " Lauf abgebrochen.")
                break
            if eintrag["stand"] == ALTER_STAND:
                erg.meldungen.append(f"SEC-Prüfregel verletzt, CIK {cik} behält den alten Stand: {eintrag['text']}")
            if fortschritt:
                fortschritt(nr, len(ciks), cik, eintrag)
            if netz_aus >= NETZ_AUSFAELLE_BIS_ABBRUCH:
                erg.abbruch = f"SEC {netz_aus}-mal hintereinander nicht erreichbar – Lauf abgebrochen"
                break
        if erg.abbruch is None:
            try:
                schwelle.pruefe()
                erg.erfolgreich = True
            except FehlerschwelleUeberschritten as f:
                erg.abbruch = str(f).replace(" Abbruch, keine Statusdatei geschrieben.", " Lauf abgebrochen.")
    finally:
        if sic_geaendert:
            zeilen = [{"cik": c, "gueltig_ab": d, "sic": s} for c, h in sic.items() for d, s in h]
            sec_tabellen.schreiben("universum", "sic_historie", pd.DataFrame(zeilen, columns=["cik", "gueltig_ab", "sic"]),
                                   {"quelle": "SEC-Einreichungsköpfe (10-K)", "ciks": len(sic), "aktualisiert": "tools/sec_aktualisieren.py"})
        if erg.abbruch:
            erg.meldungen.insert(0, f"SEC-Aktualisierung nicht erfolgreich: {erg.abbruch}")
    return erg


def stand_schreiben(wurzel, erg: Ergebnis, *, ende: datetime, zusatz: dict | None = None) -> dict:
    """`STAND.json` unter `wurzel` (SEC-Rohdaten des Betriebs) schreiben; `letzter_erfolg` aus dem bisherigen Stand
    übernehmen, nur bei Erfolg neu setzen. Gibt den Inhalt zurück."""
    from pathlib import Path

    from tradingbot.daten.schicht import lesepfad, schreibpfad

    datei = Path(wurzel) / STAND_DATEI
    bisher = {}
    if lesepfad(datei).exists():
        try:
            bisher = json.loads(lesepfad(datei).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            bisher = {}
    zahl = erg.zaehlen()
    inhalt = {
        "lauf_beginn": erg.beginn.isoformat(timespec="seconds"),
        "lauf_ende": ende.isoformat(timespec="seconds"),
        "erfolgreich": erg.erfolgreich,
        "letzter_erfolg": ende.isoformat(timespec="seconds") if erg.erfolgreich else bisher.get("letzter_erfolg"),
        "abbruch": erg.abbruch,
        "zusammenfassung": {"ciks": len(erg.je_cik), **{k: zahl.get(k, 0) for k in (UEBERNOMMEN, ALTER_STAND, FEHLER, OHNE_DATEN)},
                            "neue_zeilen": sum(e.get("neue_zeilen", 0) for e in erg.je_cik.values())},
        **(zusatz or {}),
        "je_cik": erg.je_cik,
    }
    ziel = schreibpfad(datei)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    temporaer = ziel.with_suffix(".tmp")
    temporaer.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(temporaer, ziel)
    return inhalt

