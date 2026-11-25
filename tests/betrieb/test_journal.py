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


def test_kasse_je_waehrung_mit_tausch_und_usd_kauf(j):
    j.buch_anlegen("fundamental_a", 10_000.0)
    j.tausch("fx1", "fundamental_a:t1", "EUR", "USD", 1000.0, 1100.0, 1.82, "2026-11-03T19:00")
    j.ausfuehrung("e9", "fundamental_a:k1", "AAPL", 1, 5, 200.0 / 1.1, 1.0 / 1.1, "2026-11-04T15:30", waehrung="USD", preis=200.0,
                  gebuehr=1.0, gebuehr_waehrung="USD")
    kassen = j.kasse_je_waehrung("fundamental_a")
    assert kassen["EUR"] == pytest.approx(10_000 - 1000 - 1.82) and kassen["USD"] == pytest.approx(1100 - 1000 - 1.0)
    assert j.kasse("fundamental_a") == pytest.approx(10_000 - 1.82 - 1000 / 1.1 - 1.0 / 1.1)


def test_sicherung_ueberschreibt_nie(tmp_path):
    from datetime import datetime

    from tradingbot.betrieb.journal import Journal
    j = Journal(tmp_path / "journal.sqlite")
    t = datetime(2026, 11, 3, 21, 23, 42)
    a, b = j.sichern(str(tmp_path / "s"), jetzt=t), j.sichern(str(tmp_path / "s"), jetzt=t)
    assert a != b and a.exists() and b.exists()
    j.schliessen()


def test_tauschgebuehr_in_usd_abgezogen(tmp_path):
    from tradingbot.betrieb.journal import Journal
    j = Journal(tmp_path / "j.sqlite")
    j.buch_anlegen("fundamental_a", 10_000.0)
    j.tausch("t1", "fundamental_a:x", "EUR", "USD", 9000.0, 9900.0, 2.0 / 1.1, "2026-11-04T09:00", gebuehr_ibkr=2.0, gebuehr_ibkr_waehrung="USD")
    k = j.kasse_je_waehrung("fundamental_a")
    assert abs(k["EUR"] - 1000.0) < 1e-9 and abs(k["USD"] - 9898.0) < 1e-9
    j.schliessen()


# --- Befund 1 (Jakob 25.11.2026): Fremdwährungskasse im Buchwert zum Kurs des Laufs ------------------------------------
def test_kasse_bewertet_ohne_fremdwaehrung_genau_alte_kasse(j):
    j.vorschlag_speichern(_v(), Urteil(True), waehrung="EUR", freigabe_bis="2026-11-02T23:59:59", jetzt=JETZT)
    j.ausfuehrung("e1", "real:v1", "SPYI.DE", 1, 2, 201.37, 1.25, "2026-11-03T09:00")
    j.dividende("real", "SPYI.DE", "2026-12-10", 2, 3.07)
    assert j.kasse_bewertet("real", {"USD": 1.1}) == j.kasse("real")              # byte-gleich, nicht nur ungefähr
    assert j.kasse_bewertet("real", {}) == j.kasse("real")                        # ohne Fremdwährung braucht es keinen Kurs
    assert j.kasse_bewertet("crossover", {}) == 10_000.0


def test_kasse_bewertet_usd_kasse_zum_laufkurs(j):
    # Tausch 1.000 € → 1.100 $ (1,10), Kauf 5 × 200 $ am Tag mit 1,12 gebucht; Lauf mit 1,25:
    # EUR 10.000 − 1.000 − 1,82 = 8.998,18; USD 1.100 − 1.000 − 1 = 99 $ → 79,20 €
    j.buch_anlegen("fundamental_a", 10_000.0)
    j.tausch("fx1", "fundamental_a:t1", "EUR", "USD", 1000.0, 1100.0, 1.82, "2026-11-03T19:00")
    j.ausfuehrung("e9", "fundamental_a:k1", "AAPL", 1, 5, 200.0 / 1.12, 1.0 / 1.12, "2026-11-04T15:30", waehrung="USD", preis=200.0,
                  gebuehr=1.0, gebuehr_waehrung="USD")
    assert j.kasse_bewertet("fundamental_a", {"USD": 1.25}) == pytest.approx(8_998.18 + 99.0 / 1.25, abs=1e-9)
    assert j.kasse("fundamental_a") == pytest.approx(10_000 - 1.82 - 1001.0 / 1.12)               # alte Konvention unverändert
    with pytest.raises(ValueError, match="kein Kurs für USD"):
        j.kasse_bewertet("fundamental_a", {})


def test_kasse_bewertet_nur_tausch_ohne_kauf(j):
    j.buch_anlegen("fundamental_b", 10_000.0)
    j.tausch("fx2", "fundamental_b:t1", "EUR", "USD", 9000.0, 9900.0, 2.0 / 1.1, "2026-11-04T09:00", gebuehr_ibkr=2.0, gebuehr_ibkr_waehrung="USD")
    assert j.kasse_bewertet("fundamental_b", {"USD": 1.0}) == pytest.approx(1000.0 + 9898.0)


def test_buchwert_speichert_laufkurs(j):
    j.buchwert_speichern("real", "2026-11-25", 505.0, 5.0, 506.0, {"USD": 1.09673})
    j.buchwert_speichern("crossover", "2026-11-25", 10_000.0, 10_000.0, 10_000.0)
    z = {r["buch"]: r["fx"] for r in j.db.execute("SELECT buch, fx FROM buchwerte")}
    assert z == {"real": '{"USD": 1.09673}', "crossover": None}
