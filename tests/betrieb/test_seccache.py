"""Eigener SEC-Cache des Betriebs (SEC-Aktualisierung, Schritt 1, Festlegung Jakob 23.11.2026; betrieb/seccache.py).

Nachweise für Abnahme A: Übernahme byteweise mit Marke (A1), Trennung von Betrieb, Probe und Entwicklung byteweise (A3),
kein automatisches Nachladen des SecClient (A4)."""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import tradingbot.betrieb.speicher as speicher
import tradingbot.daten.cache as cache_modul
from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb import seccache
from tradingbot.daten import schicht
from tradingbot.daten import sec as sec_modul
from tradingbot.daten.abruf import Drossel
from tradingbot.daten.cache import ParquetCache
from tradingbot.daten.sec import SecClient, cik10, lade_erstmeldungen, sec_cache, sec_rohwurzel

FAKTEN = {
    "cik": 1, "entityName": "Beispiel AG",
    "facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"start": "2023-01-01", "end": "2023-12-31", "val": 100, "filed": "2024-02-15", "form": "10-K",
         "accn": "0000000001-24-000001", "fy": 2023, "fp": "FY"},
    ]}}}},
}


class _Antwort:
    def __init__(self, daten):
        self.status_code, self._daten = 200, daten

    def json(self):
        return self._daten


class _Sitzung:
    def __init__(self, daten):
        self.daten, self.aufrufe = daten, []

    def get(self, url, headers=None, timeout=None):
        self.aufrufe.append(url)
        return _Antwort(self.daten)


def _abdruck(wurzel, ohne=None):
    """SHA-256 je Datei unter `wurzel` (ohne den Teilbaum `ohne`)."""
    return {str(p.relative_to(wurzel)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(wurzel.rglob("*"))
            if p.is_file() and (ohne is None or ohne not in p.resolve().parents)}


def _gz_json(pfad, inhalt):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(pfad, "wt", encoding="utf-8") as f:
        json.dump(inhalt, f)


@pytest.fixture
def ablage(tmp_path, monkeypatch):
    """daten/ in tmp_path: Entwicklungs-Cache daten/cache mit je einer Datei je Bereich, Betriebsbereich daten/betrieb."""
    daten = tmp_path / "daten"
    entwicklung = daten / "cache"
    standard = ParquetCache(entwicklung)
    monkeypatch.setattr(cache_modul, "standard_cache", lambda: standard)
    monkeypatch.setattr(schicht, "_daten", lambda: daten.resolve())

    def betriebspfad(relativ="", **kw):
        p = daten / "betrieb" / relativ
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    monkeypatch.setattr(speicher, "betriebspfad", betriebspfad)
    abgerufen = "2026-11-02T00:00:00+00:00"
    _gz_json(entwicklung / "sec" / "companyfacts" / "CIK0000000001.json.gz", {"url": "u", "abgerufen_um": abgerufen, "daten": FAKTEN})
    _gz_json(entwicklung / "sec" / "submissions" / "CIK0000000001.json.gz", {"url": "u", "abgerufen_um": abgerufen, "daten": {"cik": 1}})
    _gz_json(entwicklung / "sec" / "submissions" / "CIK0000000001-submissions-001.json.gz", {"url": "u", "abgerufen_um": abgerufen, "daten": {}})
    (entwicklung / "sec" / "koepfe").mkdir(parents=True)
    with gzip.open(entwicklung / "sec" / "koepfe" / "0000000001-24-000001.txt.gz", "wt") as f:
        f.write("STANDARD INDUSTRIAL CLASSIFICATION: [3711]")
    _gz_json(entwicklung / "sec" / "suche" / "abc.json.gz", {"url": "u", "abgerufen_um": abgerufen, "daten": {}})
    _gz_json(entwicklung / "sec" / "company_tickers.json.gz", {"url": "u", "abgerufen_um": abgerufen, "daten": {}})
    _gz_json(entwicklung / "sec" / "volltext_8k_text" / "x.json.gz", {"nicht": "übernehmen"})
    leer = pd.DataFrame({"wert": [1.0]})
    for bereich in ("sec_erstmeldungen", "sec_aktienfakten", "sec_aktienfakten_quartale"):
        standard.schreiben(bereich, cik10(1), leer, {"roh_abgerufen_um": "2026-11-02T00:00:00+00:00"})
    standard.schreiben("universum", "sic_historie", pd.DataFrame({"cik": [1], "gueltig_ab": [pd.Timestamp("2010-01-01")], "sic": [3711]}), {})
    standard.schreiben("universum", "sp500", leer, {})                       # gehört nicht zur SEC-Übernahme
    (entwicklung / "sec_erstmeldungen" / "halb.parquet.tmp").write_bytes(b"halb")
    return daten, entwicklung, daten / "betrieb" / "cache", tmp_path / "freigaben.log"


def test_uebernahme_byteweise_einmalig_mit_marke(ablage):
    """A1: jede Datei der Bereiche byteweise gleich, Dateizahl je Bereich in der Marke; danach nie wieder kopiert."""
    _, entwicklung, betrieb, _ = ablage
    info = seccache.uebernehmen(entwicklung, betrieb, jetzt=datetime(2026, 11, 23, 15, 0))
    assert info["neu"] and info["dateien"] == 10
    assert info["je_bereich"]["sec/submissions"] == 2 and info["je_bereich"]["universum/sic_historie.parquet"] == 1
    quelle = _abdruck(entwicklung)
    ziel = _abdruck(betrieb)
    uebernommen = {k: v for k, v in quelle.items() if "volltext" not in k and "sp500" not in k and not k.endswith(".tmp")}
    assert {k: v for k, v in ziel.items() if "UEBERNAHME" not in k} == uebernommen
    assert not (betrieb / "universum" / "sp500.parquet").exists() and not (betrieb / "sec" / "volltext_8k_text").exists()
    assert "10 Dateien" in seccache.protokollzeile(info)
    (entwicklung / "sec" / "companyfacts" / "CIK0000000002.json.gz").write_bytes(b"neu")   # später: nie mehr übernommen
    info2 = seccache.uebernehmen(entwicklung, betrieb)
    assert not info2["neu"] and not (betrieb / "sec" / "companyfacts" / "CIK0000000002.json.gz").exists()
    assert "übernommen am 23.11.2026 15:00, 10 Dateien" in seccache.protokollzeile(info2)


def test_abgebrochene_uebernahme_wird_vollstaendig_wiederholt(ablage):
    _, entwicklung, betrieb, _ = ablage
    halb = betrieb / "sec" / "companyfacts" / "CIK0000000001.json.gz"
    halb.parent.mkdir(parents=True)
    halb.write_bytes(b"halb")                                               # keine Marke
    assert seccache.uebernehmen(entwicklung, betrieb)["neu"]
    assert halb.read_bytes() == (entwicklung / "sec" / "companyfacts" / "CIK0000000001.json.gz").read_bytes()


def test_wege_ausserhalb_und_im_betriebsmodus(ablage):
    daten, entwicklung, betrieb, log = ablage
    assert sec_cache().wurzel == entwicklung and sec_rohwurzel() == entwicklung / "sec"
    assert SecClient("Test test@example.com").cache_wurzel == entwicklung / "sec"
    with betriebsmodus("Test", protokoll=log):
        assert sec_cache().wurzel == betrieb and sec_rohwurzel() == betrieb / "sec"
        assert SecClient("Test test@example.com").cache_wurzel == betrieb / "sec"
    assert (betrieb / seccache.MARKE).exists()


def test_betriebslauf_veraendert_den_entwicklungs_cache_nie(ablage, monkeypatch):
    """A3: Abruf, Erstmeldungen und SIC-Historie im Betrieb schreiben nur in den Betriebs-Cache."""
    daten, entwicklung, betrieb, log = ablage
    vorher = _abdruck(entwicklung)
    sitzung = _Sitzung(FAKTEN)
    with betriebsmodus("Test", protokoll=log):
        client = SecClient("Test test@example.com", sitzung=sitzung, drossel=Drossel(0.0), max_alter=timedelta(0))
        erst = lade_erstmeldungen(1, client=client)                          # erzwungen neu geladen
        assert len(sitzung.aufrufe) == 1 and len(erst) == 1
        from tradingbot.daten.universum import lade_sic_historien

        monkeypatch.setattr("tradingbot.daten.universum.sic_historie", lambda cik, client: [(pd.Timestamp("2020-01-01"), 7372)])
        universum = pd.DataFrame({"cik": [1, 9], "bis": [pd.NaT, pd.NaT], "vorgaenger_ciks": [None, None]})
        historien = lade_sic_historien(universum, client=client)
        assert historien[9] == [(pd.Timestamp("2020-01-01"), 7372)]
    assert _abdruck(entwicklung) == vorher
    t, meta = ParquetCache(betrieb).lesen("sec_erstmeldungen", cik10(1))
    assert meta["roh_abgerufen_um"] != "2026-11-02T00:00:00+00:00"
    assert set(ParquetCache(betrieb).lesen("universum", "sic_historie")[0]["cik"]) == {1, 9}


def test_probe_schreibt_nur_in_die_schicht(ablage):
    """A3: Probe mit Übernahme und Abruf: Entwicklungs- und Betriebsdaten byteweise unverändert."""
    daten, entwicklung, betrieb, log = ablage
    betrieb.mkdir(parents=True)
    (betrieb / "vorhanden.txt").write_text("Betrieb")
    vorher = _abdruck(daten)
    s = daten / "betrieb" / "probe" / "cache"
    with schicht.probe_schicht(s, leeren=True), betriebsmodus("Probe", protokoll=log):
        client = SecClient("Test test@example.com", sitzung=_Sitzung(FAKTEN), drossel=Drossel(0.0), max_alter=timedelta(0))
        lade_erstmeldungen(1, client=client)
        assert seccache.sicherstellen()["neu"] is False                    # Marke liegt jetzt in der Schicht
    assert _abdruck(daten, ohne=s.resolve()) == vorher
    assert (s / "betrieb" / "cache" / "sec" / "UEBERNAHME.json").exists()
    assert (s / "betrieb" / "cache" / "sec_erstmeldungen" / "0000000001.parquet").exists()


def test_secclient_laedt_ohne_ausdrueckliches_max_alter_nie_nach(tmp_path):
    """A4 (Zusage Jakob 23.11.2026): was im Cache liegt, gilt – auch nach 30 Tagen; nur Fehlendes wird geladen."""
    jetzt = [datetime(2026, 11, 2, tzinfo=timezone.utc)]
    sitzung = _Sitzung(FAKTEN)
    client = SecClient("Test test@example.com", cache_wurzel=tmp_path, sitzung=sitzung, drossel=Drossel(0.0),
                       jetzt=lambda: jetzt[0])
    client.companyfacts(1)                                                    # fehlt: wird geladen
    jetzt[0] += timedelta(days=30)
    client.companyfacts(1)
    client.submissions(1)                                                     # fehlt: wird geladen
    assert len(sitzung.aufrufe) == 2
    ausdruecklich = SecClient("Test test@example.com", cache_wurzel=tmp_path, sitzung=sitzung, drossel=Drossel(0.0),
                              max_alter=timedelta(days=7), jetzt=lambda: jetzt[0])
    ausdruecklich.companyfacts(1)                                             # ausdrücklich: älter als 7 Tage → neu
    assert len(sitzung.aufrufe) == 3
    assert sec_modul.SecClient("x", cache_wurzel=tmp_path).max_alter is None
