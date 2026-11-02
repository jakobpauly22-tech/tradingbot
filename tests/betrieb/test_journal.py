"""Journal je Buch: Bestand und Kasse aus Ausführungen, Messbeginn, Freigabefenster, Sicherung."""
import sqlite3
from datetime import datetime

import pandas as pd
import pytest

from tradingbot.betrieb.journal import Journal, konto_kurz
from tradingbot.risiko.manager import OrderVorschlag, Urteil

JETZT = datetime(2026, 11, 2, 19, 0)


@pytest.fixture
def j(tmp_path):
    jo = Journal(tmp_path / "journal.sqlite")
    jo.buch_anlegen("real", 500.0)
    jo.buch_anlegen("crossover", 10_000.0)
    yield jo
    jo.schliessen()


def _v(i="v1", buch="real", richtung=1, stueck=2):
    return OrderVorschlag(i, pd.Timestamp("2026-11-02"), buch, "SPYI.DE", richtung, stueck, 200.0, limit=204.0 if richtung > 0 else None, these="Test")


def test_bestand_und_kasse_je_buch(j):
    j.vorschlag_speichern(_v(), Urteil(True), waehrung="EUR", freigabe_bis="2026-11-02T23:59:59", jetzt=JETZT)
    assert j.ausfuehrung("e1", "real:v1", "SPYI.DE", 1, 2, 201.0, 1.25, "2026-11-03T09:00")
    assert not j.ausfuehrung("e1", "real:v1", "SPYI.DE", 1, 2, 201.0, 1.25, "2026-11-03T09:00")   # doppelt eingelesen
    j.dividende("real", "SPYI.DE", "2026-12-10", 2, 3.0)
    assert j.bestand("real") == {"SPYI.DE": 2} and j.bestand("crossover") == {}
    assert j.kasse("real") == pytest.approx(500 - 402 - 1.25 + 3.0) and j.kasse("crossover") == 10_000.0
    assert j.vorschlaege(buch="real")[0]["status"] == "ausgefuehrt"


def test_messbeginn_bei_erster_freigabe_und_fenster(j):
    j.vorschlag_speichern(_v(), Urteil(True), waehrung="EUR", freigabe_bis="2026-11-02T23:59:59", jetzt=JETZT)
    j.vorschlag_speichern(_v("v2", stueck=1), Urteil(True), waehrung="EUR", freigabe_bis="2026-11-02T23:59:59", jetzt=JETZT)
    assert j.messbeginn("real") is None
    j.freigeben("v1", jetzt=JETZT)
    assert j.messbeginn("real") == "2026-11-02"
    with pytest.raises(ValueError, match="abgelaufen"):
        j.freigeben("v2", jetzt=datetime(2026, 11, 3, 0, 5))
    with pytest.raises(ValueError, match="nicht freigebbar"):
        j.freigeben("v1", jetzt=JETZT)


def test_veto_nicht_freigebbar_und_hinweis_protokolliert(j):
    j.vorschlag_speichern(_v("v3", buch="crossover"), Urteil(True, hinweise=["hätte gesperrt am 02.11.2026: Satellite-Buch crossover gestoppt"]),
                          waehrung="EUR", freigabe_bis="2026-11-02T23:59:59", jetzt=JETZT)
    j.vorschlag_speichern(_v("v4"), Urteil(False, ["Kasse"]), waehrung="EUR", freigabe_bis="2026-11-02T23:59:59", jetzt=JETZT)
    with pytest.raises(ValueError):
        j.freigeben("v4", jetzt=JETZT)
    arten = [z["art"] for z in j.db.execute("SELECT art FROM ereignisse")]
    assert "haette_gesperrt" in arten


def test_sicherung_ausserhalb_und_konto_gekuerzt(j, tmp_path):
    ziel = j.sichern(str(tmp_path / "onedrive"), jetzt=JETZT)
    assert ziel.exists() and sqlite3.connect(ziel).execute("SELECT COUNT(*) FROM buecher").fetchone()[0] == 2
    assert j.sichern("") is None                                       # nicht gesetzt: Ereignis statt Fehler
    assert konto_kurz("DUR3123456") == "DUR3…"
