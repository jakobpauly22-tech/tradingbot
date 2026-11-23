"""Laufzeit Schritt 3 (Jakob 23.11.2026): paralleler Kursabruf der Bewertung – Drossel global über alle Threads,
Betriebsmodus in den Threads, zweiter Durchgang, Fehlliste ohne stille Lücken, Probe schreibt nur in die Schicht."""
import threading
import time
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from tradingbot.daten import schicht
from tradingbot.daten.abruf import Drossel
from tradingbot.daten.cache import ParquetCache
from tradingbot.engines.fundamental import aktuell

BIS = date(2026, 11, 20)                       # Freitag


def roh(bis: date, start: date = date(2026, 10, 1)) -> pd.DataFrame:
    tage = pd.bdate_range(start, bis, tz="America/New_York")
    return pd.DataFrame({"Open": 10.0, "High": 11.0, "Low": 9.0, "Close": [10.0 + i / 100 for i in range(len(tage))],
                         "Volume": 1000.0, "Dividends": 0.0, "Stock Splits": 0.0}, index=tage)


def test_drossel_haelt_den_abstand_global_ueber_alle_threads():
    d, zeiten, sperre = Drossel(0.05), [], threading.Lock()

    def arbeiter():
        for _ in range(5):
            d.warten()
            with sperre:
                zeiten.append(time.monotonic())
    faeden = [threading.Thread(target=arbeiter) for _ in range(4)]
    for f in faeden:
        f.start()
    for f in faeden:
        f.join()
    zeiten.sort()
    assert len(zeiten) == 20 and min(b - a for a, b in zip(zeiten, zeiten[1:])) >= 0.05 - 0.01


def test_drossel_einzeln_wie_bisher():
    uhr = {"t": 100.0}
    d = Drossel(0.5, uhr=lambda: uhr["t"], schlafen=lambda s: uhr.__setitem__("t", uhr["t"] + s))
    d.warten()
    assert uhr["t"] == 100.0
    uhr["t"] += 0.2
    d.warten()
    assert uhr["t"] == pytest.approx(100.5)
    uhr["t"] += 1.0
    d.warten()
    assert uhr["t"] == pytest.approx(101.5)


def test_parallel_mit_wiederholung_und_fehlliste(tmp_path):
    from tradingbot.backtest.tresor import betriebsmodus, im_betriebsmodus

    versuche, modus = {}, set()

    def abrufer(t, start, ende):
        modus.add(im_betriebsmodus())                                     # Kontext kommt in den Threads an
        versuche[t] = versuche.get(t, 0) + 1
        if t == "WACKEL" and versuche[t] == 1:
            raise ConnectionError("429")                                  # erster Durchgang scheitert, zweiter klappt
        if t == "KAPUTT":
            raise ConnectionError("immer")
        return roh(date(2026, 11, 19) if t == "ALT" else ende), "USD"     # ALT: Yahoo liefert den 20.11. nicht
    symbole = ["AAA", "WACKEL", "ALT", "BBB", "KAPUTT", "CCC"]
    pausen = []
    with betriebsmodus("Test: paralleler Kursabruf", protokoll=tmp_path / "log"):
        fehl = aktuell.kurse_aktualisieren(symbole, BIS, cache=ParquetCache(tmp_path / "c"), abrufer=abrufer, abstand_s=0.0,
                                           erwartet=BIS, schlafen=pausen.append)
    assert modus == {True}
    assert fehl == ["ALT: letzter Kurs 2026-11-19 statt 2026-11-20", "KAPUTT: ConnectionError"]
    assert versuche["WACKEL"] == 2 and versuche["AAA"] == 1 and pausen == [aktuell.KURS_NACHLAUF_PAUSE_S]
    cache = ParquetCache(tmp_path / "c")
    for t in ("AAA", "WACKEL", "BBB", "CCC"):
        daten, _ = cache.lesen("kurse", t)
        assert daten.index.max() == pd.Timestamp(BIS)


def test_seriell_und_parallel_gleich(tmp_path):
    from tradingbot.backtest.tresor import betriebsmodus

    symbole = [f"T{i:02d}" for i in range(12)]

    def abrufer(t, start, ende):
        return roh(ende), "USD"
    ergebnisse = {}
    for name, threads in (("seriell", 1), ("parallel", 4)):
        cache = ParquetCache(tmp_path / name)
        with betriebsmodus("Test", protokoll=tmp_path / "log"):          # ohne Betriebsmodus begrenzt der Tresor auf < 2025
            assert aktuell.kurse_aktualisieren(symbole, BIS, threads=threads, cache=cache, abrufer=abrufer, abstand_s=0.0,
                                               erwartet=BIS, schlafen=lambda s: None) == []
        ergebnisse[name] = {t: cache.lesen("kurse", t)[0] for t in symbole}
    assert all(ergebnisse["seriell"][t].equals(ergebnisse["parallel"][t]) for t in symbole)


def test_probe_schreibt_auch_parallel_nur_in_die_schicht(tmp_path, monkeypatch):
    from tradingbot.backtest.tresor import betriebsmodus

    daten = tmp_path / "daten"
    monkeypatch.setattr(schicht, "_daten", lambda: daten.resolve())
    betrieb = ParquetCache(daten / "betrieb" / "cache")
    for t in ("AAA", "BBB", "CCC", "DDD"):
        betrieb.schreiben("kurse", t, aktuell.lade_kurse.__globals__["normalisieren"](roh(date(2026, 11, 13))),
                          {"quelle": "yfinance", "von": "2026-10-01", "bis": "2026-11-13", "waehrung": "USD", "abgerufen_um": "x"})
    vorher = {p.name: p.read_bytes() for p in (daten / "betrieb" / "cache" / "kurse").iterdir()}
    with schicht.probe_schicht(daten / "betrieb" / "probe" / "cache", leeren=True) as s, betriebsmodus("Test", protokoll=tmp_path / "log"):
        fehl = aktuell.kurse_aktualisieren(["AAA", "BBB", "CCC", "DDD"], BIS, cache=betrieb, abrufer=lambda t, a, e: (roh(e), "USD"),
                                           abstand_s=0.0, erwartet=BIS, schlafen=lambda s: None)
    assert fehl == []
    assert {p.name: p.read_bytes() for p in (daten / "betrieb" / "cache" / "kurse").iterdir()} == vorher
    assert sorted(p.name for p in (s / "betrieb" / "cache" / "kurse").iterdir()) == [f"{t}.parquet" for t in ("AAA", "BBB", "CCC", "DDD")]


def test_erwartete_sitzung():
    abends = datetime(2026, 11, 20, 22, 30, tzinfo=timezone.utc)          # 17:30 New York, nach Schluss
    mittags = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)          # 10:00 New York, Handel läuft
    assert aktuell.erwartete_sitzung(BIS, abends) == BIS
    assert aktuell.erwartete_sitzung(BIS, mittags) == date(2026, 11, 19)
    assert aktuell.erwartete_sitzung(date(2026, 11, 22), datetime(2026, 11, 23, 9, tzinfo=timezone.utc)) == BIS   # Sonntag
