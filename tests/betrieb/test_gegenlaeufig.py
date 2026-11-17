"""Gegenläufige Orders im selben Titel aus verschiedenen Büchern (Befund 2, Jakob 16.11.2026; betrieb/gegenlaeufig.py)."""
from test_tageslauf import umgebung  # noqa: F401
from tradingbot.betrieb.gegenlaeufig import MELDUNG, meldung, wartende


def z(id_, buch, richtung, ticker="SPYI.DE", art="etf"):
    return {"id": id_, "buch": buch, "ticker": ticker, "richtung": richtung, "art": art}


def test_beide_richtungen_neu_verkauf_hat_vorrang():
    w = wartende([z("k", "real", 1), z("v", "regime", -1)], [], [])
    assert list(w) == ["k"] and "Verkauf von regime am selben Abend hat Vorrang" in w["k"]


def test_neue_order_gegen_unterwegs_wartet_auch_als_verkauf():
    """Eine gesendete Order lässt sich nicht zurückholen: auch ein Verkauf wartet, wenn ein Kauf schon unterwegs ist."""
    assert "Kauf von real schon unterwegs" in wartende([z("v", "regime", -1)], [z("k0", "real", 1)], [])["v"]
    assert "Verkauf von regime schon unterwegs" in wartende([z("k", "real", 1)], [], [("regime", "SPYI.DE", -1)])["k"]
    assert "ohne Bot-Kennung" in wartende([z("k", "real", 1)], [], [("", "SPYI.DE", -1)])["k"]     # von Hand im Client Portal


def test_gleiche_richtung_eigenes_buch_anderer_titel_und_tausch_frei():
    assert wartende([z("a", "real", 1), z("b", "regime", 1)], [z("c", "crossover", 1)], [("regime", "SPYI.DE", 1)]) == {}
    assert wartende([z("a", "real", 1), z("b", "regime", -1, ticker="EUNL.DE")], [], []) == {}
    assert wartende([z("a", "regime", 1)], [z("b", "regime", -1)], []) == {}             # im eigenen Buch: Sperre je Buch
    assert wartende([z("a", "real", 1, art="fx"), z("b", "regime", -1, art="fx", ticker="SPYI.DE")], [], []) == {}


def test_wartender_verkauf_gibt_den_kauf_nicht_frei_zum_vorrang():
    """Wartet der neue Verkauf selbst (Kauf eines dritten Buchs unterwegs), hat er keinen Vorrang vor einem neuen Kauf."""
    w = wartende([z("k", "real", 1), z("v", "regime", -1)], [z("k0", "crossover", 1)], [])
    assert list(w) == ["v"]


def test_meldung_ist_laut_und_nennt_buch_und_titel():
    text = meldung(z("k", "real", 1), "Verkauf von regime am selben Abend hat Vorrang")
    assert text.startswith("k: " + MELDUNG) and "real KAUF SPYI.DE" in text and "nächsten Abend" in text


# --- Sendeschleife (betrieb/tageslauf._senden) ------------------------------------------------------------------------------
def test_senden_verkauf_regime_geht_raus_kauf_realbuch_wartet(umgebung):
    """30.11.: regime wechselt auf Risiko aus und verkauft SPYI.DE, das Realbuch kauft am selben Abend SPYI.DE."""
    from test_regimebuch import MIT_REGIME, Makro, _fill, abend, daten, kursreihe
    from test_tageslauf import BrokerAttrappe, kurse_attrappe, lauf
    from tradingbot.betrieb import benachrichtigung as bn
    from tradingbot.betrieb.tageslauf import freigeben_und_senden
    from tradingbot.broker.basis import Position

    j, rm = umgebung
    m, k = Makro(), kurse_attrappe()
    c = kursreihe("2026-12-02", fallend_ab="2026-11-10")
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, m))
    (kauf,) = [bv.vorschlag.id for bv, u in e.vorschlaege if bv.vorschlag.buch == "regime"]
    freigeben_und_senden(j, [kauf], BrokerAttrappe(), abend(2026, 11, 16), risk=rm, kurse_laden=k, konfig_betrieb=MIT_REGIME)
    z = j.vorschlaege(buch="regime")[0]
    pos = [Position("DU1", "SPYI.DE", z["stueck"], 150.0)]
    lauf(j, rm, jetzt=abend(2026, 11, 17), regime_daten=daten(c, m), broker=BrokerAttrappe(fills=[_fill(z, 150.0, "2026-11-17T09:00")], positionen=pos))
    e = lauf(j, rm, jetzt=abend(2026, 11, 30), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=pos))
    vs = {(bv.vorschlag.buch, bv.vorschlag.richtung): bv.vorschlag.id for bv, u in e.vorschlaege if u.frei and bv.vorschlag.ticker == "SPYI.DE"}
    assert ("regime", -1) in vs and ("real", 1) in vs
    b = BrokerAttrappe(positionen=pos)
    meldungen = freigeben_und_senden(j, [vs[("real", 1)], vs[("regime", -1)]], b, abend(2026, 11, 30), risk=rm, kurse_laden=k,
                                     konfig_betrieb=MIT_REGIME)
    assert [(a.buch, a.richtung) for a in b.gesendet] == [("regime", -1)]
    assert any(MELDUNG in x and "real KAUF SPYI.DE" in x and "Verkauf von regime am selben Abend hat Vorrang" in x for x in meldungen)
    assert {x["id"]: x["status"] for x in j.vorschlaege(buch="real")}[vs[("real", 1)]] == "freigegeben"     # wartet, nicht gesendet
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='wartet_gegenlaeufig'").fetchone()[0] == 1
    assert "gegenläufige Order" in bn.sendeprobleme(j, [vs[("real", 1)]], "2026-11-30T00:00:00", meldungen, abend(2026, 11, 30))
    # zweiter Sendedurchgang am selben Abend: der Verkauf ist jetzt unterwegs, der Kauf wartet weiter
    b2 = BrokerAttrappe(positionen=pos)
    freigeben_und_senden(j, [vs[("real", 1)]], b2, abend(2026, 11, 30), risk=rm, kurse_laden=k, konfig_betrieb=MIT_REGIME)
    assert b2.gesendet == []
