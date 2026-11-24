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


def pruefe_erstmeldungen(alt: pd.DataFrame | None, neu: pd.DataFrame, grenze: pd.Timestamp | None, *,
                         alt_accn=frozenset(), einreichung=None) -> tuple[bool, str, list, list]:
    """(bestanden, Text, neue Zeilen, Hinweise). Bisherige Zeilen müssen alle unverändert bleiben; neue nur mit
    filed ≥ grenze.

    Nachtrag 23.11.2026 (Jakob, docs/BETRIEB.md): eine neue Zeile vor der Grenze ist erlaubt, wenn (a) ihre accn in
    `alt_accn` (alle accn des bisherigen Stands, nicht nur der Erstmeldungen) nicht vorkommt und (b) `einreichung(accn)`
    (submissions der SEC: (filingDate, Formular) oder None) dasselbe Datum wie `filed` nennt. Hinweise: ein Eintrag je
    nachgelieferter Einreichung {accn, form, filed, zeilen}."""
    a, n = _zeilen(alt), _zeilen(neu)
    weg = a - n
    neue = list((n - a).elements())
    if weg:
        beispiele = "; ".join(f"{z[1]} {_datum(z[4]) if z[4] is not None else '–'} filed "
                              f"{_datum(z[6]) if z[6] is not None else '–'} accn {z[7]}" for z in list(weg.elements())[:3])
        return False, f"{sum(weg.values())} bisherige Erstmeldungen geändert oder entfernt (z. B. {beispiele})", neue, []
    hinweise: dict[str, dict] = {}
    if grenze is not None:
        verletzt = []
        for z in (z for z in neue if z[6] is not None and pd.Timestamp(z[6]) < grenze):
            accn, filed = z[7], pd.Timestamp(z[6])
            beleg = einreichung(accn) if (einreichung is not None and accn and accn not in alt_accn) else None
            if beleg is not None and pd.Timestamp(beleg[0]) == filed:
                h = hinweise.setdefault(accn, {"accn": accn, "form": beleg[1], "filed": str(filed.date()), "zeilen": 0})
                h["zeilen"] += 1
            else:
                verletzt.append(z)
        if verletzt:
            beispiele = "; ".join(f"{z[1]} {_datum(z[4]) if z[4] is not None else '–'} filed {_datum(z[6])} accn {z[7]}"
                                  for z in verletzt[:3])
            return False, (f"{len(verletzt)} neue Erstmeldungen mit filed vor {_datum(grenze)} ohne Beleg als nachgelieferte "
                           f"Einreichung (z. B. {beispiele})"), neue, []
    text = f"{len(neue)} neue Erstmeldungen"
    if hinweise:
        text += f", davon {sum(h['zeilen'] for h in hinweise.values())} aus {len(hinweise)} nachgelieferten Einreichungen"
    return True, text, neue, list(hinweise.values())


def einreichungen_aus_submissions(subs: dict, seite_laden=None):
    """Nachschlagen accn → (filingDate, Formular) in den submissions einer CIK. Zusatzseiten (`filings.files`) werden
    erst geladen, wenn eine accn in der Liste „recent“ fehlt (`seite_laden(name)` → Seite als dict)."""
    tabelle: dict[str, tuple[str, str]] = {}

    def aufnehmen(seite: dict) -> None:
        for d, a, f in zip(seite.get("filingDate", []), seite.get("accessionNumber", []), seite.get("form", [])):
            tabelle.setdefault(a, (d, f))

    aufnehmen(subs.get("filings", {}).get("recent", {}))
    offen = list(subs.get("filings", {}).get("files", []))

    def nachschlagen(accn: str):
        while accn not in tabelle and offen and seite_laden is not None:
            aufnehmen(seite_laden(offen.pop(0)["name"]))
        return tabelle.get(accn)

    return nachschlagen


def _datum(d) -> str:
    """Datum für Meldetexte als TT.MM.JJJJ (Jakob 24.11.2026)."""
    return f"{pd.Timestamp(d):%d.%m.%Y}"


def sic_text(liste: list) -> str:
    return "[" + ", ".join(f"{_datum(d)}: {int(s)}" for d, s in liste) + "]"


def pruefe_sic(alt: list, neu: list) -> tuple[bool, str]:
    """Bestehende SIC-Einträge unverändert, neue nur angehängt."""
    alt, neu = [(pd.Timestamp(d), int(s)) for d, s in alt], [(pd.Timestamp(d), int(s)) for d, s in neu]
    if neu[:len(alt)] != alt:
        return False, f"SIC-Historie geändert: bisher {sic_text(alt)}, neu {sic_text(neu)}"
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
    hinweise: list = field(default_factory=list)       # nachgelieferte Einreichungen (Nachtrag 23.11.2026)
    quittiert: list = field(default_factory=list)      # Verletzungen, die exakt einer Quittung entsprechen: nur Protokoll

    def zaehlen(self) -> Counter:
        return Counter(e["stand"] for e in self.je_cik.values())


def ciks_betrieb(universum: pd.DataFrame, tag) -> list[int]:
    """Heutige Mitglieder des Betriebsuniversums plus Vorgänger-CIKs (Festlegung: etwa 550)."""
    from tradingbot.daten.universum import mitglieder_am

    aktiv = mitglieder_am(universum, pd.Timestamp(tag))
    ciks = {int(c) for c in aktiv["cik"].dropna()}
    ciks |= {int(c) for liste in aktiv["vorgaenger_ciks"] if liste is not None for c in list(liste)}
    return sorted(ciks)


def _fakten(cik: int, client, jetzt, einreichung=None) -> dict:
    """Schritt 1 für eine CIK (siehe Moduldoku); gibt den Eintrag für STAND.json zurück (ohne SIC).
    `einreichung`: Nachschlagen in den frischen submissions (Nachtrag 23.11.2026)."""
    from tradingbot.daten.sec import lade_erstmeldungen
    from tradingbot.engines.fundamental.aktienzahl import lade_aktienfakten

    alt_roh, alt_abgerufen = client.companyfacts_aus_cache(cik)
    try:
        neu_roh = client.companyfacts_holen(cik)
    except DatenFehler as f:
        if alt_roh is None and "nicht gefunden" in str(f) and not isinstance(f, VoruebergehenderFehler):
            return {"stand": OHNE_DATEN, "text": "keine companyfacts bei der SEC (404), auch bisher nicht"}
        raise
    alt_fakten = fakten_tabelle(alt_roh) if alt_roh is not None else None
    alt = erstmeldungen(alt_fakten) if alt_fakten is not None else None
    alt_accn = frozenset(alt_fakten["accn"].dropna()) if alt_fakten is not None else frozenset()
    neu = erstmeldungen(fakten_tabelle(neu_roh))
    ok, text, neue, hinweise = pruefe_erstmeldungen(alt, neu, grenze_fuer(alt_abgerufen), alt_accn=alt_accn,
                                                    einreichung=einreichung)
    eintrag = {"neue_zeilen": len(neue), "bisher_abgerufen_um": alt_abgerufen.isoformat(timespec="seconds") if alt_abgerufen else None,
               "neueste_filed": max((str(pd.Timestamp(z[6]).date()) for z in neue if z[6] is not None), default=None),
               "firma": neu_roh.get("entityName")}
    if hinweise:
        eintrag["nachgeliefert"] = hinweise
    if not ok:
        return {**eintrag, "stand": ALTER_STAND, "text": text}
    zeitpunkt = jetzt()
    client.companyfacts_speichern(cik, neu_roh, zeitpunkt)
    lade_erstmeldungen(cik, client=client)                       # liest das eben Gespeicherte, baut die Tabelle neu
    lade_aktienfakten([cik])                                     # Aktienfakten (Jahr) offline neu
    lade_aktienfakten([cik], mit_quartalen=True)                 # und Quartale
    return {**eintrag, "stand": UEBERNOMMEN, "text": text, "abgerufen_um": zeitpunkt.isoformat(timespec="seconds")}


def _sic(cik: int, client, bisher: list) -> tuple[dict, list | None]:
    """Schritt 2 für eine CIK: (Eintrag, neue Historie oder None, wenn der alte Stand bleibt). Die submissions sind zu
    diesem Zeitpunkt schon frisch geladen (`aktualisieren`)."""
    from tradingbot.daten.universum import sic_historie

    neu = [(d, s) for d, s in sic_historie(cik, client) if s is not None]
    ok, text = pruefe_sic(bisher, neu)
    eintrag = {"sic": UEBERNOMMEN if ok else ALTER_STAND, "sic_text": text, "sic_neu": len(neu) - len(bisher) if ok else 0}
    if not ok:                                          # für die Quittung (Jakob 24.11.2026): genau der alte und neue Wert
        eintrag["sic_bisher"] = [[str(pd.Timestamp(d).date()), int(s)] for d, s in bisher]
        eintrag["sic_abgerufen"] = [[str(pd.Timestamp(d).date()), int(s)] for d, s in neu]
    return eintrag, (neu if ok else None)


def _sic_norm(liste) -> list:
    return [(pd.Timestamp(str(d)).normalize(), int(s)) for d, s in (liste or [])]


def quittung_fuer(cik: int, eintrag: dict, quittiert: list | None) -> dict | None:
    """Quittierte Verletzung der Prüfregel (Jakob 24.11.2026, config/betrieb.yaml `sec_quittiert`): passt nur, wenn allein
    die SIC-Historie den alten Stand behält (Fakten übernommen) und bisheriger wie abgerufener Wert exakt dem Eintrag
    entsprechen. Jede andere oder abweichende Verletzung bleibt eine Meldung (Telegram)."""
    if eintrag.get("stand") != ALTER_STAND or eintrag.get("fakten") == ALTER_STAND or eintrag.get("sic") != ALTER_STAND:
        return None
    for q in quittiert or []:
        if (int(q.get("cik", -1)) == int(cik) and q.get("teil", "sic") == "sic"
                and _sic_norm(q.get("alt")) == _sic_norm(eintrag.get("sic_bisher"))
                and _sic_norm(q.get("neu")) == _sic_norm(eintrag.get("sic_abgerufen"))):
            return q
    return None


def aktualisieren(ciks: list[int], *, client, client_frisch, sec_tabellen, jetzt=None,
                  fortschritt=None, quittiert: list | None = None) -> Ergebnis:
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
                subs, _ = client_frisch.submissions(cik)              # frisch: Beleg für Nachlieferungen und SIC
                einreichung = einreichungen_aus_submissions(subs, lambda name: client.submissions_seite(name)[0])
                eintrag = _fakten(cik, client, jetzt, einreichung)
                eintrag["fakten"] = eintrag["stand"]                 # Stand der companyfacts getrennt vom SIC-Stand
                for h in eintrag.get("nachgeliefert", []):
                    erg.hinweise.append({"cik": cik, "firma": eintrag.get("firma"), **h})
                sic_eintrag, neu = _sic(cik, client, sic.get(cik, []))   # auch ohne companyfacts
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
                text = f"SEC-Prüfregel verletzt, CIK {cik} behält den alten Stand: {eintrag['text']}"
                q = quittung_fuer(cik, eintrag, quittiert)
                if q is not None:
                    eintrag["quittiert"] = {"datum": str(q.get("datum")), "grund": q.get("grund")}
                    erg.quittiert.append(f"{text} (quittiert {_datum(q.get('datum'))}: {q.get('grund')})")
                else:
                    erg.meldungen.append(text)
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
                            "neue_zeilen": sum(e.get("neue_zeilen", 0) for e in erg.je_cik.values()),
                            "hinweise": len(erg.hinweise), "quittiert": len(erg.quittiert)},
        "hinweise": erg.hinweise,
        **(zusatz or {}),
        "je_cik": erg.je_cik,
    }
    ziel = schreibpfad(datei)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    temporaer = ziel.with_suffix(".tmp")
    temporaer.write_text(json.dumps(inhalt, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    os.replace(temporaer, ziel)
    return inhalt

