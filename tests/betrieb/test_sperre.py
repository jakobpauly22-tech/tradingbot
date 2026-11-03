"""Laufsperre gegen zwei gleichzeitige Tagesläufe (Jakob 03.11.2026)."""
import os

import pytest

from tradingbot.betrieb.sperre import LaufGesperrt, laufsperre, prozess_lebt


def test_zweiter_lauf_wird_abgewiesen_und_sperre_freigegeben(tmp_path):
    datei = tmp_path / "tageslauf.sperre"
    with laufsperre(datei):
        assert datei.exists() and f"Prozess {os.getpid()}" in datei.read_text(encoding="utf-8")
        datei.write_text(f"Tageslauf seit jetzt, Prozess {os.getppid()}", encoding="utf-8")   # lebender fremder Prozess
        with pytest.raises(LaufGesperrt, match="läuft bereits"):
            with laufsperre(datei):
                pass
    assert not datei.exists()


def test_sperre_wird_auch_nach_fehler_freigegeben(tmp_path):
    datei = tmp_path / "s.sperre"
    with pytest.raises(ZeroDivisionError):
        with laufsperre(datei):
            1 / 0
    assert not datei.exists()


def test_verwaiste_sperre_wird_uebernommen(tmp_path):
    datei = tmp_path / "s.sperre"
    datei.write_text("Tageslauf seit gestern, Prozess 999999", encoding="utf-8")   # Prozess existiert nicht
    meldungen = []
    with laufsperre(datei, meldungen=meldungen):
        assert f"Prozess {os.getpid()}" in datei.read_text(encoding="utf-8")
    assert any("verwaiste Sperre" in m for m in meldungen)


def test_prozess_lebt():
    assert prozess_lebt(os.getpid()) and not prozess_lebt(999999)
