"""Eigener Kurs-Cache des Betriebs (Befund 5, Jakob 16./17.11.2026; tradingbot/betrieb/kurscache.py)."""
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("daten_conftest_kurscache", Path(__file__).resolve().parents[1] / "daten" / "conftest.py")
_hilfen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_hilfen)
HEUTE, SimulierteQuelle, yahoo_rohdaten = _hilfen.HEUTE, _hilfen.SimulierteQuelle, _hilfen.yahoo_rohdaten

import tradingbot.betrieb.speicher as speicher  # noqa: E402
import tradingbot.daten.cache as cache_modul  # noqa: E402
import tradingbot.daten.kurse as kurse  # noqa: E402
from tradingbot.backtest.tresor import betriebsmodus  # noqa: E402
from tradingbot.betrieb import kurscache  # noqa: E402
from tradingbot.daten.cache import ParquetCache  # noqa: E402


@pytest.fixture
def ablage(tmp_path, monkeypatch):
    """Standard-Cache und Betriebsbereich in tmp_path."""
    standard = ParquetCache(tmp_path / "cache")
    monkeypatch.setattr(cache_modul, "standard_cache", lambda: standard)
    monkeypatch.setattr(kurse, "standard_cache", lambda: standard)

    def betriebspfad(relativ="", **kw):
        p = tmp_path / "betrieb" / relativ
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    monkeypatch.setattr(speicher, "betriebspfad", betriebspfad)
    return standard, tmp_path / "betrieb" / "cache" / "kurse", tmp_path / "freigaben.log"


def test_uebernahme_einmalig_mit_marke_und_zahl(tmp_path):
    quelle, ziel = tmp_path / "q", tmp_path / "z"
    quelle.mkdir()
    for n in ("A.parquet", "B.DE.parquet", "C.parquet.tmp"):
        (quelle / n).write_bytes(n.encode())
    info = kurscache.uebernehmen(quelle, ziel, jetzt=datetime(2026, 11, 17, 17, 0))
    assert info["neu"] and info["dateien"] == 2
    assert sorted(p.name for p in ziel.iterdir()) == ["A.parquet", "B.DE.parquet", kurscache.MARKE]
    assert "2 Kursdateien" in kurscache.protokollzeile(info)
    (quelle / "D.parquet").write_bytes(b"neu")                       # später in der Quelle: wird nie mehr übernommen
    (ziel / "A.parquet").write_bytes(b"Betrieb")                     # der Betrieb schreibt in seinen Cache
    info2 = kurscache.uebernehmen(quelle, ziel)
    assert not info2["neu"] and info2["dateien"] == 2
    assert not (ziel / "D.parquet").exists() and (ziel / "A.parquet").read_bytes() == b"Betrieb"
    assert "übernommen am 17.11.2026 17:00, 2 Dateien" in kurscache.protokollzeile(info2)


def test_abgebrochene_uebernahme_wird_wiederholt(tmp_path):
    quelle, ziel = tmp_path / "q", tmp_path / "z"
    quelle.mkdir()
    ziel.mkdir()
    (quelle / "A.parquet").write_bytes(b"voll")
    (ziel / "A.parquet").write_bytes(b"ha")                          # halbe Kopie, keine Marke
    assert kurscache.uebernehmen(quelle, ziel)["neu"]
    assert (ziel / "A.parquet").read_bytes() == b"voll"


def test_ausserhalb_des_betriebsmodus_standard_cache(ablage):
    standard, _, _ = ablage
    assert kurse.kurscache() is standard


def test_betriebslauf_veraendert_den_standard_cache_nie(ablage):
    """Neuer Split nach dem letzten Abruf: lade_kurse lädt die ganze Historie neu – im Betrieb nur im eigenen Cache."""
    standard, ziel, log = ablage
    alt = SimulierteQuelle(yahoo_rohdaten("2024-01-01", "2024-06-14"))
    kurse.lade_kurse("TEST", "2024-01-01", "2024-06-14", cache=standard, abrufer=alt, heute=HEUTE)
    datei = standard.pfad("kurse", "TEST")
    vorher = datei.read_bytes()

    neu_roh = yahoo_rohdaten("2024-01-01", "2024-06-28", basis=50.0)  # rückwirkend halbiert (2:1-Split)
    neu = SimulierteQuelle(neu_roh)
    with betriebsmodus("Test", protokoll=log):
        assert isinstance(kurse.kurscache(), ParquetCache) and kurse.kurscache().wurzel == ziel.parent
        daten = kurse.lade_kurse("TEST", "2024-01-01", "2024-06-28", abrufer=neu, heute=HEUTE)
    assert len(neu.abrufe) == 2                                       # Nachladen, Abgleich scheitert, Vollabruf
    assert daten["close"].iloc[0] == pytest.approx(50.0)
    assert datei.read_bytes() == vorher                               # Entwicklungsdaten unverändert
    betrieb = ParquetCache(ziel.parent).lesen("kurse", "TEST")[0]
    assert betrieb.index[-1] == pd.Timestamp("2024-06-28") and betrieb["close"].iloc[0] == pytest.approx(50.0)
    assert (ziel / kurscache.MARKE).exists()
