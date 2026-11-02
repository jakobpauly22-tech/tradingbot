"""Fehlerschwelle der Datenwerkzeuge: über 5 % Fehler → Abbruch, keine Statusdatei."""
import pytest

from tradingbot.daten.fehlerschwelle import Fehlerschwelle, FehlerschwelleUeberschritten, laut_melden


def test_unter_der_schwelle_kein_abbruch():
    s = Fehlerschwelle("Test", mindestens=10)
    for i in range(100):
        s.zaehle("kaputt" if i % 20 == 19 else None)       # gleichmäßig verteilt, genau 5 %: noch erlaubt
    s.pruefe()
    assert s.anteil == pytest.approx(0.05)


def test_ueber_der_schwelle_abbruch_schon_waehrend_des_laufs():
    s = Fehlerschwelle("Kurs-Download", mindestens=40)
    with pytest.raises(FehlerschwelleUeberschritten, match="Kurs-Download: 4 von 40"):
        for i in range(1000):
            s.zaehle("ValueError: x" if i % 13 == 0 else None)
    assert s.gesamt == 40                                  # früh gestoppt, nicht erst nach 1000


def test_vor_mindestanzahl_nur_am_ende_geprueft(capsys):
    s = Fehlerschwelle("SEC-Fakten", mindestens=40)
    s.zaehle("Fehler")                                     # 100 % nach einem Eintrag: noch kein Abbruch
    with pytest.raises(FehlerschwelleUeberschritten) as info:
        s.pruefe()
    assert laut_melden(info.value) == 1
    assert "ABBRUCH" in capsys.readouterr().err
