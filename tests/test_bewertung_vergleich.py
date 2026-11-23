"""tools/bewertung_vergleich.py mit eingefrorenen Eingaben (Jakob 23.11.2026): Einfrieren, Prüfen, Laufkopie mit
Tagesstempel des Universums, Sichern der alten Referenz, Wache gegen direkte Lesezugriffe und Netz."""
import importlib.util
import json
import socket
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tradingbot.daten import schicht
from tradingbot.daten.cache import ParquetCache


def werkzeug():
    pfad = Path(__file__).parents[1] / "tools" / "bewertung_vergleich.py"
    spec = importlib.util.spec_from_file_location("werkzeug_bewertung_vergleich", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


bv = werkzeug()


@pytest.fixture
def daten(tmp_path, monkeypatch):
    wurzel = tmp_path / "daten"
    monkeypatch.setattr(schicht, "_daten", lambda: wurzel.resolve())
    (wurzel / "cache" / "kurse").mkdir(parents=True)
    (wurzel / "universum").mkdir()
    (wurzel / "cache" / "kurse" / "MDLZ.parquet").write_text("66.565")
    (wurzel / "universum" / "kursstatus.csv").write_text("ticker\nMDLZ\n")
    return wurzel


def test_einfrieren_und_pruefen_erkennt_spaetere_korrektur(daten):
    s = daten / "betrieb" / "probe" / "ref" / "eingefroren"
    s.mkdir(parents=True)
    (s / "cache").mkdir()
    (s / "cache" / "geschrieben.parquet").write_text("vom Lauf")         # vom Lauf selbst geschrieben: bleibt
    protokoll = {"cache/kurse/MDLZ.parquet": True, "cache/kurse/NEU.parquet": False, "cache/geschrieben.parquet": False}
    v = bv.einfrieren(protokoll, {"universum/kursstatus.csv", "cache/kurse/MDLZ.parquet"}, s, daten)
    assert set(v["dateien"]) == {"cache/kurse/MDLZ.parquet", "cache/geschrieben.parquet"}
    assert v["fehlend"] == ["cache/kurse/NEU.parquet"] and list(v["direkt"]) == ["universum/kursstatus.csv"]
    assert bv.pruefen(v, s, daten) == []
    (daten / "cache" / "kurse" / "MDLZ.parquet").write_text("66.570")      # Yahoo-Korrektur im Betriebscache: egal
    assert bv.pruefen(v, s, daten) == [] and (s / "cache" / "kurse" / "MDLZ.parquet").read_text() == "66.565"
    (daten / "universum" / "kursstatus.csv").write_text("ticker\nMDLZ\nNEU\n")
    (s / "cache" / "kurse" / "MDLZ.parquet").write_text("verändert")
    assert bv.pruefen(v, s, daten) == ["eingefroren/cache/kurse/MDLZ.parquet: geändert",
                                       "daten/universum/kursstatus.csv (direkt gelesen): geändert seit der Referenz"]


def test_laufkopie_setzt_nur_den_tagesstempel_des_universums(tmp_path):
    s, lauf = tmp_path / "eingefroren", tmp_path / "lauf"
    t = pd.DataFrame({"ticker": ["MDLZ", "KO"], "cik": [1103982, 21344]})
    ParquetCache(s / "betrieb" / "cache").schreiben("universum", "sp500", t, {"stand": "betrieb", "berechnet_am": "2026-11-23T10:00:00+00:00"})
    (lauf / "alt").mkdir(parents=True)
    alt = bv.laufkopie(s, lauf)
    assert alt == "2026-11-23T10:00:00+00:00" and not (lauf / "alt").exists()
    neu, meta = ParquetCache(lauf / "betrieb" / "cache").lesen("universum", "sp500")
    assert neu.equals(t) and meta["stand"] == "betrieb" and meta["eingefroren_berechnet_am"] == alt
    assert meta["berechnet_am"][:10] == pd.Timestamp.now(tz="UTC").date().isoformat()
    (tmp_path / "ohne_universum").mkdir()
    assert bv.laufkopie(tmp_path / "ohne_universum", tmp_path / "lauf2") is None


def test_alte_referenz_wird_mit_vermerk_gesichert_nicht_geloescht(tmp_path):
    (tmp_path / "referenz.pkl").write_bytes(b"alt")
    (tmp_path / "schicht" / "x").mkdir(parents=True)
    ziel = bv.archivieren(tmp_path, "Yahoo-Korrektur MDLZ 18.11. im Betriebscache", date(2026, 11, 23))
    assert ziel.name == "ersetzt_2026-11-23" and (ziel / "referenz.pkl").read_bytes() == b"alt" and (ziel / "schicht" / "x").is_dir()
    assert (ziel / "VERMERK.txt").read_text(encoding="utf-8") == "ersetzt 23.11.2026, Grund: Yahoo-Korrektur MDLZ 18.11. im Betriebscache\n"
    assert not (tmp_path / "referenz.pkl").exists()
    (tmp_path / "referenz.pkl").write_bytes(b"zweite")
    assert bv.archivieren(tmp_path, "nochmal", date(2026, 11, 23)).name == "ersetzt_2026-11-23_2"
    assert bv.archivieren(tmp_path, "nichts da", date(2026, 11, 23)) is None


def test_wache_erfasst_direkte_lesezugriffe_und_sperrt_im_vergleich(daten):
    with bv.wache("erfassen", daten) as gelesen:
        (daten / "universum" / "kursstatus.csv").read_text()
        (daten / "betrieb.log").open("a").close()                         # Schreiben/Anhängen zählt nicht
    assert gelesen == {"universum/kursstatus.csv"}
    with bv.wache("versiegelt", daten, erlaubt={"universum/kursstatus.csv"}):
        (daten / "universum" / "kursstatus.csv").read_text()
        with pytest.raises(schicht.SchichtLuecke, match="direkter Lesezugriff auf daten/cache/kurse/MDLZ.parquet"):
            (daten / "cache" / "kurse" / "MDLZ.parquet").read_text()
        with pytest.raises(bv.Abbruch, match="Netzzugriff"):
            socket.getaddrinfo("example.org", 443)
    (daten / "cache" / "kurse" / "MDLZ.parquet").read_text()              # danach wieder frei
    assert socket.getaddrinfo is not None and bv._WACHE["modus"] is None
