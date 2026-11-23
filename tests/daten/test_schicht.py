"""Befund 20, Schritt 4 (Regel Jakob 17.11.2026): eine Probe verändert keinerlei Betriebsdaten. Kurse, Wikipedia,
Universum, SIC, SEC und Tiingo werden in der Probe nur in die Schicht daten/betrieb/probe/cache geschrieben; gelesen wird
zuerst dort, dann das Original. Nachweis byteweise über alle Dateien unter daten/ außerhalb der Schicht."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from tradingbot.daten import schicht


@pytest.fixture
def daten(tmp_path, monkeypatch):
    """Ein eigenes daten/ mit einigen Cache-Dateien; die Schicht liegt darin wie im Betrieb."""
    wurzel = tmp_path / "daten"
    monkeypatch.setattr(schicht, "_daten", lambda: wurzel.resolve())
    (wurzel / "cache" / "kurse").mkdir(parents=True)
    return wurzel


def _abdruck(wurzel, ohne):
    """SHA-256 je Datei unter `wurzel`, ohne den Teilbaum `ohne` (die Schicht)."""
    aus = {}
    for p in sorted(wurzel.rglob("*")):
        if p.is_file() and ohne not in p.resolve().parents:
            aus[str(p.relative_to(wurzel))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return aus


def test_ohne_schicht_sind_die_pfade_unveraendert(daten):
    p = daten / "cache" / "x.parquet"
    assert schicht.lesepfad(p) == p and schicht.schreibpfad(p) == p and schicht.aktive_schicht() is None


def test_lesen_zuerst_schicht_dann_original_und_schreiben_nur_in_die_schicht(daten):
    original = daten / "cache" / "a.txt"
    original.write_text("betrieb")
    with schicht.probe_schicht(daten / "betrieb" / "probe" / "cache") as s:
        assert schicht.lesepfad(original) == original                        # noch nichts in der Schicht
        ziel = schicht.schreibpfad(original)
        assert ziel == s / "cache" / "a.txt"
        ziel.write_text("probe")
        assert schicht.lesepfad(original).read_text() == "probe"
        aussen = daten.parent / "anderswo.txt"                               # außerhalb von daten/: unverändert
        assert schicht.schreibpfad(aussen) == aussen
        assert schicht.schreibpfad(s / "cache" / "a.txt") == s / "cache" / "a.txt"   # in der Schicht: nicht doppelt
    assert original.read_text() == "betrieb" and schicht.aktive_schicht() is None


def test_schicht_wird_zu_beginn_geleert(daten):
    s = daten / "betrieb" / "probe" / "cache"
    (s / "cache").mkdir(parents=True)
    (s / "cache" / "alt.txt").write_text("vom letzten Mal")
    with schicht.probe_schicht(s):
        assert (s / "cache" / "alt.txt").exists()                            # ohne leeren bleibt sie
    with schicht.probe_schicht(s, leeren=True):
        assert not (s / "cache" / "alt.txt").exists()


class _Antwort:
    def __init__(self, inhalt, status=200):
        self.status_code, self._inhalt = status, inhalt
        self.text = inhalt if isinstance(inhalt, str) else json.dumps(inhalt)
        self.content = self.text.encode()
        self.encoding = "utf-8"

    def json(self):
        return self._inhalt if not isinstance(self._inhalt, str) else json.loads(self._inhalt)


class _Sitzung:
    def __init__(self, antworten):
        self.antworten, self.urls = antworten, []

    def get(self, url, **_):
        self.urls.append(url)
        for teil, inhalt in self.antworten.items():
            if teil in url:
                return _Antwort(inhalt)
        return _Antwort("nicht da", 404)


def test_probe_laesst_alle_betriebsdaten_byteweise_unveraendert(daten, monkeypatch):
    """Kurse (Parquet), Universum, SIC, SEC (JSON und Kopf), Tiingo (Kurse, Metadaten, Stundenzähler, Liste), Wikipedia,
    Yahoo-Namen, Übernahmen des Betriebs und kursstatus_neu.csv: jede Schreibstelle einmal in der Probe."""
    from tradingbot.betrieb import kurscache, universum_betrieb
    from tradingbot.daten import universum as u
    from tradingbot.daten.cache import ParquetCache
    from tradingbot.daten.kursquellen import yahoo_name
    from tradingbot.daten.sec import SecClient
    from tradingbot.daten.tiingo import TiingoClient, lade_tiingo_liste

    alt = datetime.now(timezone.utc) - timedelta(days=400)
    cache = ParquetCache(daten / "cache")
    betrieb_cache = ParquetCache(daten / "betrieb" / "cache")
    reihe = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.to_datetime(["2026-11-16", "2026-11-17"]))
    for c, bereich, schl in ((cache, "kurse", "AAA"), (betrieb_cache, "kurse", "AAA"), (cache, "universum", "sic_historie"),
                             (betrieb_cache, "universum", "sp500"), (betrieb_cache, "makro", "UNRATE")):
        c.schreiben(bereich, schl, reihe, {"quelle": "vorher"})
    sec_datei = daten / "cache" / "sec" / "submissions" / "CIK0000000001.json.gz"
    sec_datei.parent.mkdir(parents=True)
    with gzip.open(sec_datei, "wt", encoding="utf-8") as f:
        json.dump({"url": "x", "abgerufen_um": alt.isoformat(), "daten": {"alt": True}}, f)
    tiingo_kurs = daten / "cache" / "tiingo" / "kurse" / "aaa.json.gz"
    tiingo_kurs.parent.mkdir(parents=True)
    with gzip.open(tiingo_kurs, "wt", encoding="utf-8") as f:
        json.dump([], f)
    os.utime(tiingo_kurs, (alt.timestamp(), alt.timestamp()))
    wiki = daten / "betrieb" / "cache" / "universum" / "wikipedia_aktuell.html.gz"
    wiki.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(wiki, "wt", encoding="utf-8") as f:
        f.write("<html>alt</html>")
    os.utime(wiki, (alt.timestamp(), alt.timestamp()))
    namen = daten / "cache" / "namen" / "yahoo.json"
    namen.parent.mkdir(parents=True)
    namen.write_text(json.dumps({"AAA": "Alt Inc."}), encoding="utf-8")
    (daten / "cache" / "universum").mkdir(parents=True, exist_ok=True)
    for name in universum_betrieb.SEITEN:
        (daten / "cache" / "universum" / name).write_bytes(b"seite")
    vorher_neu = daten / "betrieb" / "cache" / "universum" / universum_betrieb.NEU_DATEI
    vorher_neu.write_text("index,ticker,von,bis,gueltig\n", encoding="utf-8")

    schicht_wurzel = (daten / "betrieb" / "probe" / "cache").resolve()
    vorher = _abdruck(daten, schicht_wurzel)

    with schicht.probe_schicht(schicht_wurzel, leeren=True):
        # Parquet: Kurse (Entwicklung und Betrieb), SIC, Universum, Makro
        for c, bereich, schl in ((cache, "kurse", "AAA"), (betrieb_cache, "kurse", "AAA"), (cache, "universum", "sic_historie"),
                                 (betrieb_cache, "universum", "sp500"), (betrieb_cache, "makro", "UNRATE")):
            c.schreiben(bereich, schl, reihe.assign(close=9.0), {"quelle": "probe"})
            assert c.lesen(bereich, schl)[1]["quelle"] == "probe"            # Probe liest ihre eigene Schicht
        # SEC: veraltete Submissions neu (Nachladen ausdrücklich angefordert, seit 23.11.2026 kein automatisches), Kopf neu
        sec = SecClient("test", cache_wurzel=daten / "cache" / "sec", schlafen=lambda s: None, max_alter=timedelta(days=7),
                        sitzung=_Sitzung({"submissions": {"neu": True}, "hdr.sgml": "KOPF"}))
        assert sec.json_mit_cache("https://data.sec.gov/submissions/CIK0000000001.json", sec_datei)[0] == {"neu": True}
        assert sec.einreichungskopf(1, "0000000001-26-000001") == "KOPF"
        # Tiingo: Kurse (veraltet), Metadaten, Stundenzähler, Liste
        tiingo = TiingoClient("test", cache_wurzel=daten / "cache" / "tiingo", warten=False,
                              sitzung=_Sitzung({"/aaa/prices": [{"date": "2026-11-17T00:00:00Z", "close": 3.0, "high": 3.0,
                                                                 "low": 3.0, "open": 3.0, "volume": 1, "adjClose": 3.0,
                                                                 "adjHigh": 3.0, "adjLow": 3.0, "adjOpen": 3.0, "adjVolume": 1,
                                                                 "divCash": 0.0, "splitFactor": 1.0}],
                                                "/aaa": {"name": "Aaa Inc."}}))
        tiingo.historie("AAA", max_alter=timedelta(days=1))
        assert tiingo.metadaten("AAA")["name"] == "Aaa Inc."
        monkeypatch.setattr("tradingbot.daten.tiingo.requests.get", lambda *a, **k: _Antwort("zip"))
        try:
            lade_tiingo_liste(daten / "cache" / "tiingo")
        except Exception:                                                    # Inhalt ist kein ZIP; geschrieben wurde trotzdem
            pass
        # Wikipedia (veraltet → Abruf), Yahoo-Name neu
        monkeypatch.setattr(u.requests, "get", lambda *a, **k: _Antwort("<html>neu</html>"))
        assert u._text_mit_cache("https://x", wiki, "ua", timedelta(days=7))[0] == "<html>neu</html>"
        monkeypatch.setattr("yfinance.Ticker", lambda s: type("T", (), {"info": {"longName": "Bbb Inc."}})(), raising=False)
        assert yahoo_name("BBB", namen) == "Bbb Inc."
        # Übernahmen des Betriebs (noch ohne Marke) und kursstatus_neu.csv
        kurscache.uebernehmen(daten / "cache" / "kurse", daten / "betrieb" / "cache" / "kurse_neu")
        universum_betrieb.seiten_uebernehmen(daten / "cache" / "universum", daten / "betrieb" / "cache" / "universum")
        ziel = schicht.schreibpfad(vorher_neu)
        ziel.write_text("index,ticker,von,bis,gueltig\n896,OKTA,2026-10-30,,True\n", encoding="utf-8")

    assert _abdruck(daten, schicht_wurzel) == vorher                         # Betriebsdaten byteweise unverändert
    in_schicht = {str(p.relative_to(schicht_wurzel)).replace("\\", "/") for p in schicht_wurzel.rglob("*") if p.is_file()}
    for erwartet in ("cache/kurse/AAA.parquet", "betrieb/cache/kurse/AAA.parquet", "cache/universum/sic_historie.parquet",
                     "betrieb/cache/universum/sp500.parquet", "betrieb/cache/makro/UNRATE.parquet",
                     "cache/sec/submissions/CIK0000000001.json.gz", "cache/sec/koepfe/0000000001-26-000001.txt.gz",
                     "cache/tiingo/kurse/aaa.json.gz", "cache/tiingo/meta/aaa.json", "cache/tiingo/supported_tickers.zip",
                     "betrieb/cache/universum/wikipedia_aktuell.html.gz", "cache/namen/yahoo.json",
                     "betrieb/cache/kurse_neu/UEBERNAHME.json", "betrieb/cache/universum/UEBERNAHME.json",
                     "betrieb/cache/universum/kursstatus_neu.csv"):
        assert erwartet in in_schicht, erwartet
    assert any(p.startswith("cache/tiingo/") and "aaa" not in p and "supported" not in p for p in in_schicht)   # Stundenzähler


def test_werkzeug_startet_jede_probe_in_geleerter_schicht(monkeypatch):
    import importlib.util
    from pathlib import Path

    pfad = Path(__file__).parents[2] / "tools" / "tageslauf.py"
    spec = importlib.util.spec_from_file_location("werkzeug_tageslauf", pfad)
    w = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(w)
    gesehen = []
    monkeypatch.setattr(w, "_starten", lambda arg: gesehen.append((arg.probe, arg.kopie, schicht.aktive_schicht())) or 0)
    import sys

    aufrufe = [["--probe"], ["--kopie"], ["--neu", "--kopie"], ["--ohne-fenster"], []]
    for argumente in aufrufe:
        monkeypatch.setattr(sys, "argv", ["tageslauf.py", *argumente])
        geleert = []
        monkeypatch.setattr(schicht.shutil, "rmtree", lambda p: geleert.append(p))
        assert w.main() == 0
    schichten = [s for _, _, s in gesehen]
    assert all(s == schicht.standard_wurzel() for s in schichten[:3])        # Probe, Kopie, Probefenster
    assert schichten[3:] == [None, None]                                     # echter Lauf: ohne Schicht


# --- Erfassen und Versiegeln (tools/bewertung_vergleich.py, Jakob 23.11.2026) -------------------------------------------
def test_erfassen_protokolliert_lesezugriffe_mit_existenz(daten):
    (daten / "cache" / "kurse" / "A.parquet").write_text("a")
    with schicht.probe_schicht(daten / "betrieb" / "probe" / "x"), schicht.erfassen() as protokoll:
        schicht.lesepfad(daten / "cache" / "kurse" / "A.parquet")
        schicht.lesepfad(daten / "cache" / "kurse" / "FEHLT.parquet")
        schicht.lesepfad(daten.parent / "ausserhalb.txt")                    # außerhalb von daten/: nicht erfasst
    assert protokoll == {"cache/kurse/A.parquet": True, "cache/kurse/FEHLT.parquet": False}
    assert schicht.lesepfad(daten / "cache" / "kurse" / "A.parquet") == daten / "cache" / "kurse" / "A.parquet"


def test_versiegelt_liest_nur_die_schicht_und_bricht_bei_luecke_ab(daten):
    (daten / "cache" / "kurse" / "A.parquet").write_text("betrieb, inzwischen korrigiert")
    (daten / "cache" / "kurse" / "B.parquet").write_text("betrieb")
    s = daten / "betrieb" / "probe" / "versiegelt"
    (s / "cache" / "kurse").mkdir(parents=True)
    (s / "cache" / "kurse" / "A.parquet").write_text("eingefroren")
    with schicht.probe_schicht(s), schicht.versiegelt({"cache/kurse/FEHLT.parquet"}):
        assert schicht.lesepfad(daten / "cache" / "kurse" / "A.parquet").read_text() == "eingefroren"
        assert not schicht.lesepfad(daten / "cache" / "kurse" / "FEHLT.parquet").exists()   # fehlte schon: bleibt fehlend
        with pytest.raises(schicht.SchichtLuecke, match="cache/kurse/B.parquet fehlt"):
            schicht.lesepfad(daten / "cache" / "kurse" / "B.parquet")                       # nie still vom Original
    assert schicht.lesepfad(daten / "cache" / "kurse" / "B.parquet") == daten / "cache" / "kurse" / "B.parquet"
