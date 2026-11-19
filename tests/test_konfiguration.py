"""lade_konfiguration: Zwischenspeicher je Datei (Laufzeit, Jakob 19.11.2026) ohne Wirkung auf den Inhalt."""
import os

import pytest

from tradingbot import konfiguration as k


@pytest.fixture
def projekt(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    monkeypatch.setattr(k, "PROJEKT_WURZEL", tmp_path)
    monkeypatch.setattr(k, "_GELESEN", {})
    return tmp_path / "config"


def test_gleicher_inhalt_wie_direkt_geparst():
    for datei in sorted((k.PROJEKT_WURZEL / "config").glob("*.yaml")):
        with datei.open(encoding="utf-8") as f:
            direkt = k.YAML(typ="safe", pure=True).load(f) or {}
        assert k.lade_konfiguration(datei.stem) == direkt
        assert k.lade_konfiguration(datei.stem) == direkt          # zweiter Aufruf aus dem Zwischenspeicher


def test_jeder_aufruf_bekommt_eine_eigene_kopie(projekt):
    (projekt / "x.yaml").write_text("a:\n  b: [1, 2]\n", encoding="utf-8")
    erste = k.lade_konfiguration("x")
    erste["a"]["b"].append(3)
    erste["neu"] = 1
    assert k.lade_konfiguration("x") == {"a": {"b": [1, 2]}}


def test_geaenderte_datei_wirkt_sofort(projekt):
    datei = projekt / "x.yaml"
    datei.write_text("wert: 1\n", encoding="utf-8")
    assert k.lade_konfiguration("x") == {"wert": 1}
    datei.write_text("wert: 2\n", encoding="utf-8")                 # gleiche Größe
    st = datei.stat()
    os.utime(datei, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))  # Änderungszeit sicher anders
    assert k.lade_konfiguration("x") == {"wert": 2}
    datei.write_text("wert: 30\n", encoding="utf-8")
    assert k.lade_konfiguration("x") == {"wert": 30}


def test_fehlende_datei_wie_bisher(projekt):
    with pytest.raises(k.KonfigurationsFehler):
        k.lade_konfiguration("gibt_es_nicht")


def test_leere_datei_gibt_leeres_dictionary(projekt):
    (projekt / "leer.yaml").write_text("", encoding="utf-8")
    assert k.lade_konfiguration("leer") == {}
