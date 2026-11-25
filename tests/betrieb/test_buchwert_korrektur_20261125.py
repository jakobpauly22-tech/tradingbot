"""Datenkorrektur Buchwert 25.11.2026 (Befund 1): Rekonstruktion, Laufkurs, Korrektur, Idempotenz – ohne echtes Journal."""
import importlib.util
from datetime import datetime

import pytest

from tradingbot.betrieb.journal import Journal
from tradingbot.konfiguration import PROJEKT_WURZEL

_spec = importlib.util.spec_from_file_location("korrektur_bw", PROJEKT_WURZEL / "tools" / "buchwert_korrektur_20261125.py")
k = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k)

SCHLUSS = {("AAA", "2026-11-09"): 100.0, ("AAA", "2026-11-10"): 104.0, ("BBB", "2026-11-10"): 50.0}


def schluss(t, tag):
    return SCHLUSS.get((t, tag))


def _lauf(j, zeit, xetra, nyse):
    j.ereignis("tageslauf", f"3 Vorschläge, Befunde in []; Xetra {xetra}, NYSE {nyse}", jetzt=datetime.fromisoformat(zeit))


@pytest.fixture
def j(tmp_path):
    """Zwei Fundamental-Bücher wie im Betrieb: Tausch während des Laufs (erst am nächsten Tag eingelesen), Kauf zum
    Tageskurs 1,12 eingelesen am 10.11., am 11.11. Kauf nur in fundamental_b (Beleg 1,10), fundamental_a rückgerechnet. Buchwerte in alter Konvention."""
    jo = Journal(tmp_path / "j.sqlite")
    for b in ("fundamental_a", "fundamental_b", "real"):
        jo.buch_anlegen(b, 10_000.0 if b != "real" else 500.0)
    _lauf(jo, "2026-11-09T22:10:00", "09.11.2026", "06.11.2026")
    jo.buchwert_speichern("fundamental_a", "2026-11-09", 10_000.0, 10_000.0, 10_000.0)
    jo.buchwert_speichern("fundamental_b", "2026-11-09", 10_000.0, 10_000.0, 10_000.0)
    jo.buchwert_speichern("real", "2026-11-09", 500.0, 500.0, 500.0)
    # Tausche um 22:07 Ortszeit (vor Laufende), aber erst am 10.11. eingelesen
    jo.tausch("t1", "fundamental_a:x", "EUR", "USD", 5000.0, 5600.0, 2.0, "2026-11-09 21:07:00+00:00")
    jo.tausch("t2", "fundamental_b:x", "EUR", "USD", 1000.0, 1120.0, 2.0, "2026-11-09 21:07:30+00:00")
    jo.ausfuehrung("e1", "fundamental_a:k", "AAA", 1, 50, 100.0 / 1.12, 1.0 / 1.12, "2026-11-10 14:30:00+00:00", waehrung="USD",
                   preis=100.0, gebuehr=1.0, gebuehr_waehrung="USD")
    _lauf(jo, "2026-11-10T22:30:00", "10.11.2026", "09.11.2026")
    for b, pos in (("fundamental_a", 50 * 100.0 / 1.12), ("fundamental_b", 0.0)):
        kasse = jo.kasse(b)
        jo.buchwert_speichern(b, "2026-11-10", kasse + pos, kasse, kasse + pos + 0.5)
    jo.buchwert_speichern("real", "2026-11-10", 501.0, 500.0, 501.0)
    jo.ausfuehrung("e2", "fundamental_b:k", "BBB", 1, 10, 50.0 / 1.10, 1.0 / 1.10, "2026-11-11 14:30:00+00:00", waehrung="USD",
                   preis=50.0, gebuehr=1.0, gebuehr_waehrung="USD")
    _lauf(jo, "2026-11-11T22:30:00", "11.11.2026", "10.11.2026")
    for b, pos in (("fundamental_a", 50 * 104.0 / 1.10), ("fundamental_b", 10 * 50.0 / 1.10)):
        kasse = jo.kasse(b)
        jo.buchwert_speichern(b, "2026-11-11", kasse + pos, kasse, kasse + pos + 0.5)
    yield jo
    jo.schliessen()


def _z(zeilen, buch, tag):
    return next(z for z in zeilen if z.buch == buch and z.tag == tag)


def test_rekonstruktion_tausch_waehrend_des_laufs_und_laufkurs(j):
    zeilen = k.rekonstruieren(j.db, schluss)
    a9, a10, a11 = (_z(zeilen, "fundamental_a", t) for t in ("2026-11-09", "2026-11-10", "2026-11-11"))
    assert a9.anfang == 0 and a9.status == "unverändert"                  # Tausch 22:07 noch nicht eingelesen
    assert a10.fx == pytest.approx(1.12) and a10.fx_quelle == "Ausführung"
    # 11.11.: Beleg aus dem Kauf in fundamental_b gilt auch für fundamental_a; dessen Rückrechnung stimmt damit überein
    assert a11.fx == pytest.approx(1.10) and a11.fx_quelle == "Ausführung" and a11.fx_rueck == pytest.approx(1.10)
    assert _z(zeilen, "fundamental_b", "2026-11-10").fx == pytest.approx(1.12)   # ein Laufkurs für alle Bücher
    # 10.11.: EUR 10.000 − 5.000 − 2 = 4.998; USD 5.600 − 5.000 − 1 = 599 $ / 1,12
    assert a10.kasse_neu == pytest.approx(4998.0 + 599.0 / 1.12)
    assert a10.delta == pytest.approx(4998.0 + 599.0 / 1.12 - j.db.execute(
        "SELECT kasse FROM buchwerte WHERE buch='fundamental_a' AND tag='2026-11-10'").fetchone()[0])
    assert a11.wert_neu == pytest.approx(4998.0 + 599.0 / 1.10 + 50 * 104.0 / 1.10)
    assert a11.wert_modell_neu == pytest.approx(a11.wert_neu + 0.5)
    assert all(z.status != "Bruch" for z in zeilen)


def test_ausfuehren_idempotent_und_nur_fremdwaehrungszeilen(j):
    vorher = j.db.execute("SELECT * FROM buchwerte WHERE buch='real' OR tag='2026-11-09' ORDER BY buch, tag").fetchall()
    zeilen = k.rekonstruieren(j.db, schluss)
    assert k.ausfuehren(j.db, zeilen) == 4                                 # a und b, je 10. und 11.11.
    j.db.commit()
    assert [tuple(r) for r in vorher] == [tuple(r) for r in j.db.execute(
        "SELECT * FROM buchwerte WHERE buch='real' OR tag='2026-11-09' ORDER BY buch, tag")]
    r = j.db.execute("SELECT wert, kasse, fx FROM buchwerte WHERE buch='fundamental_a' AND tag='2026-11-11'").fetchone()
    assert r["kasse"] == pytest.approx(j.kasse_bewertet("fundamental_a", {"USD": 1.10})) and r["fx"] == '{"USD": 1.1}'
    nochmal = k.rekonstruieren(j.db, schluss)
    assert {z.status for z in nochmal if z.tag != "2026-11-09"} == {"bereits korrigiert"}
    assert k.ausfuehren(j.db, nochmal) == 0


def test_bruch_wenn_kasse_nicht_rekonstruierbar(j):
    j.db.execute("UPDATE buchwerte SET kasse = kasse + 1 WHERE buch='fundamental_b' AND tag='2026-11-11'")
    z = _z(k.rekonstruieren(j.db, schluss), "fundamental_b", "2026-11-11")
    assert z.status == "Bruch" and "gespeicherte Kasse" in z.hinweise[0]


def test_bruch_wenn_rueckrechnungen_der_buecher_abweichen(j):
    SCHLUSS[("BBB", "2026-11-10")] = 51.0
    try:
        zeilen = k.rekonstruieren(j.db, schluss)
    finally:
        SCHLUSS[("BBB", "2026-11-10")] = 50.0
    assert {z.status for z in zeilen if z.tag == "2026-11-11"} == {"Bruch"}
    assert any("weichen ab" in h for h in _z(zeilen, "fundamental_a", "2026-11-11").hinweise)


def test_bericht_mit_vorher_nachher_und_abnahme(j):
    zeilen = k.rekonstruieren(j.db, schluss)
    text = k.bericht(zeilen, ausgefuehrt=False, jetzt=datetime(2026, 11, 25, 14, 0), querpruefung=k.abgleich_mit_journal(j.db, zeilen))
    assert "**Probelauf**" in text and "## fundamental_a" in text and "Brüche: 0." in text
    assert "1,12000 (Ausführung)" in text and "Zu korrigieren: 4" in text
    assert text.count("– gleich") == 2


def test_ohne_beleg_mittel_der_rueckrechnungen(j, monkeypatch):
    original = k.kassenereignisse

    def ohne_beleg(db, buch):
        ev = original(db, buch)
        for e in ev:
            if e.zeit.day == 11:
                e.fx_beleg = None                                          # Kauf am 11.11. ohne Kursbeleg
        return ev

    monkeypatch.setattr(k, "kassenereignisse", ohne_beleg)
    zeilen = k.rekonstruieren(j.db, schluss)
    for b in ("fundamental_a", "fundamental_b"):
        z = _z(zeilen, b, "2026-11-11")
        assert z.fx_quelle == "Rückrechnung" and z.fx == pytest.approx(1.10) and z.status == "korrigieren"
