"""A1 (Jakob 12.11.2026): Kapitalmaßnahmen erkennen, Stopp je Buch, Aufhebung und Quittung."""
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from tradingbot.betrieb import buchstopp, kapitalmassnahmen
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.tageslauf import freigeben_und_senden
from tradingbot.broker.basis import Position
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import RiskManager

from test_tageslauf import ABEND, AN, KOSTEN, BrokerAttrappe, KontoAttrappe, kurse_attrappe, lauf

NAECHSTER = datetime(2026, 11, 3, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))


@pytest.fixture
def umgebung(tmp_path):
    j = Journal(tmp_path / "journal.sqlite")
    rm = RiskManager(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), KOSTEN, tmp_path)
    yield j, rm
    j.schliessen()


def flex_mit(massnahmen=(), quelle="Flex Test"):
    def laden():
        return [], quelle
    laden.bargeld = lambda: ([], quelle)
    laden.kapitalmassnahmen = lambda: (list(massnahmen), quelle)
    return laden


def kauf(j, buch, ticker, stueck, preis=50.0, nr="1", zeit="2026-10-01T09:00:00"):
    j.ausfuehrung(f"x{buch}{ticker}{nr}", f"{buch}:k{nr}{ticker}", ticker, 1, stueck, preis, 1.25, zeit, waehrung="EUR", preis=preis)


# --- Parser -------------------------------------------------------------------------------------------------------------
SPLIT = [{"type": "FS", "actionID": "77", "conid": "111", "symbol": "ABC", "isin": "US0001", "currency": "USD", "quantity": "-10",
          "proceeds": "0", "reportDate": "20261105", "description": "ABC(US0001) SPLIT 2 FOR 1 (ABC, ABC INC, US0001)",
          "transactionID": "9001", "levelOfDetail": "DETAIL"},
         {"type": "FS", "actionID": "77", "conid": "111", "symbol": "ABC", "isin": "US0001", "currency": "USD", "quantity": "20",
          "proceeds": "0", "reportDate": "20261105", "description": "ABC(US0001) SPLIT 2 FOR 1 (ABC, ABC INC, US0001)",
          "transactionID": "9002", "levelOfDetail": "DETAIL"}]


def test_parser_buendelt_split_und_tickerwechsel():
    tc = [{"type": "IC", "actionID": "88", "conid": "222", "symbol": "ALT", "currency": "USD", "quantity": "-5", "proceeds": "0",
           "reportDate": "2026-11-06", "description": "ALT CUSIP/ISIN CHANGE"},
          {"type": "IC", "actionID": "88", "conid": "333", "symbol": "NEU", "isin": "US0003", "currency": "USD", "quantity": "5",
           "proceeds": "0", "reportDate": "2026-11-06", "description": "ALT CUSIP/ISIN CHANGE"},
          {"type": "IC", "actionID": "88", "conid": "333", "symbol": "NEU", "currency": "USD", "quantity": "5", "levelOfDetail": "SUMMARY"}]
    ms = kapitalmassnahmen.belege_aus_flex(SPLIT + tc)
    assert [(m.beleg_id, m.art, len(m.posten), m.tag) for m in ms] == [("CA:77", "split", 2, "2026-11-05"),
                                                                        ("CA:88", "tickerwechsel", 2, "2026-11-06")]
    assert sum(p["stueck"] for p in ms[0].posten) == 10
    # TC heißt laut IBKR „Merger“, nicht Tickerwechsel; Barkomponente aus proceeds
    ue = kapitalmassnahmen.belege_aus_flex([{"type": "TC", "conid": "444", "symbol": "XY", "currency": "USD", "quantity": "-3",
                                              "proceeds": "150.00", "reportDate": "20261107", "transactionID": "5"}])
    assert ue[0].art == "uebernahme" and ue[0].bar == {"USD": 150.0} and ue[0].beleg_id == "CA:TC:5"
    assert kapitalmassnahmen.belege_aus_flex([{"type": "SD", "symbol": "Q", "quantity": "1", "transactionID": "6"}])[0].art == "sonstige"


# --- Journal: gebuchte Maßnahme in Bestand, Kasse, Einstand ----------------------------------------------------------------
def test_gebuchte_massnahme_aendert_bestand_kasse_und_einstand(umgebung):
    from tradingbot.betrieb.ansicht import _kaufkurse
    from tradingbot.betrieb.dividenden import stueck_vor

    j, _ = umgebung
    j.buch_anlegen("crossover", 10_000.0)
    kauf(j, "crossover", "ABC", 10, preis=100.0)
    posten = [{"ticker": "ABC", "stueck": -10, "einstand": -1000.0, "einstand_eur": -1000.0},
              {"ticker": "ABC", "stueck": 20, "einstand": 1000.0, "einstand_eur": 1000.0, "angeschafft": "2026-10-01"},
              {"ticker": None, "stueck": 0, "waehrung": "USD", "betrag": 12.5, "betrag_eur": 11.0}]
    j.massnahme(beleg_id="CA:77", buch="crossover", art="split", tag="2026-11-05", posten=posten)
    assert j.bestand("crossover") == {"ABC": 10}                      # erkannt: zählt noch nicht
    kasse_vorher = j.kasse("crossover")
    j.massnahme_status("CA:77", "crossover", "gebucht")
    assert j.bestand("crossover") == {"ABC": 20}
    assert j.kasse("crossover") == pytest.approx(kasse_vorher + 11.0)
    assert j.kasse_je_waehrung("crossover")["USD"] == pytest.approx(12.5)
    k = _kaufkurse(j, "crossover")["ABC"]
    assert k["kaufkurs"] == pytest.approx(50.0) and k["erst"] == "2026-10-01"
    assert stueck_vor(j, "crossover", "ABC", "2026-11-05") == 10 and stueck_vor(j, "crossover", "ABC", "2026-11-06") == 20


# --- Stopp je Buch im Tageslauf -----------------------------------------------------------------------------------------------
def test_abweichung_stoppt_nur_das_buch_das_den_titel_haelt(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "EUNK.DE", 10)
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 20, 25.0)]), flex=flex_mit())
    assert e.gestoppt is None and e.abgleich == "teilweise"
    assert set(e.buchstopps) == {"crossover"} and e.buchstopps["crossover"]["kategorie"] == buchstopp.KAT_OHNE
    buecher = {bv.vorschlag.buch for bv, _ in e.vorschlaege}
    assert "crossover" not in buecher and "real" in buecher                 # die anderen Bücher laufen weiter
    assert any("Buch crossover gestoppt" in s and "EUNK.DE" in s for s in e.sofort)
    assert not any(r["buch"] == "crossover" for r in j.db.execute("SELECT buch FROM buchwerte WHERE tag='2026-10-30'"))


def test_derselbe_titel_in_zwei_buechern_beide_stoppen_drittes_laeuft(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "EUNK.DE", 10)
    kauf(j, "momentum", "EUNK.DE", 4)
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 28, 25.0)]), flex=flex_mit())
    assert e.gestoppt is None and set(e.buchstopps) == {"crossover", "momentum"}
    buecher = {bv.vorschlag.buch for bv, _ in e.vorschlaege}
    assert "real" in buecher and not buecher & {"crossover", "momentum"}


def test_position_ohne_buch_stoppt_alles(umgebung):
    j, rm = umgebung
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "ZZZ", 5, 10.0)]), flex=flex_mit())
    assert e.gestoppt and "ZZZ" in e.gestoppt and e.vorschlaege == [] and not e.buchstopps


def test_erkannte_massnahme_ordnet_neue_position_dem_buch_zu(umgebung):
    """Tickerwechsel ALT → NEU: IBKR zeigt NEU (kein Buch hält es); über den Flex-Beleg gehört es zu crossover. Neue Conid nur als
    Vorschlag im Journal (mit ISIN und IBKR-Symbol)."""
    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "ALT.DE", 5)
    ic = [{"type": "IC", "actionID": "88", "conid": "222", "symbol": "ALT", "currency": "EUR", "quantity": "-5", "proceeds": "0",
           "reportDate": "20261102", "description": "ALT ISIN CHANGE"},
          {"type": "IC", "actionID": "88", "conid": "333", "symbol": "NEU", "isin": "DE0003", "currency": "EUR", "quantity": "5",
           "proceeds": "0", "reportDate": "20261102", "description": "ALT ISIN CHANGE"}]
    e = lauf(j, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=[Position("DU1", "NEU.DE", 5, 25.0)]), flex=flex_mit(ic))
    assert e.gestoppt is None and set(e.buchstopps) == {"crossover"}
    st = e.buchstopps["crossover"]
    assert st["kategorie"] == buchstopp.KAT_BELEG and st["belege"] == ["CA:88"] and {"ALT.DE", "NEU.DE"} <= set(st["titel"])
    assert [r["status"] for r in j.massnahmen("beleg_id='CA:88'")] == ["erkannt", "erkannt"]    # _konto und crossover, nicht gebucht
    v = j.conid_vorschlaege()
    assert [(r["conid"], r["symbol"], r["isin"], r["ticker_vorschlag"], r["status"]) for r in v] == [(333, "NEU", "DE0003", "NEU.DE", "offen")]
    assert any("Kapitalmaßnahme erkannt" in m and "Tickerwechsel" in m for m in e.meldungen)
    assert j.bestand("crossover") == {"ALT.DE": 5}                            # A1 bucht nichts


def _kasse_lauf(j, rm, kasse, positionen, flex, jetzt):
    return lauf(j, rm, jetzt=jetzt, broker=KontoAttrappe(kasse, positionen=positionen), flex=flex)


def test_kassendifferenz_passend_zur_barkomponente_stoppt_nur_das_buch(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "EUNK.DE", 3)
    start = sum(j.kasse_je_waehrung(n)["EUR"] - j.startkapital(n) for n in lade_konfiguration("betrieb")["buecher"])
    basis = 100_000.0
    _kasse_lauf(j, rm, {"EUR": basis + start}, [Position("DU1", "EUNK.DE", 3, 50.0)], flex_mit(), ABEND)   # Basis festhalten
    tc = [{"type": "TC", "actionID": "99", "conid": "444", "symbol": "EUNK", "currency": "EUR", "quantity": "-3", "proceeds": "150.00",
           "reportDate": "20261103", "description": "XY MERGED"}]
    # Barübernahme: Position weg, Kasse +150 (passt zur Barkomponente laut Beleg) → nur crossover
    e = _kasse_lauf(j, rm, {"EUR": basis + start + 150.03}, [], flex_mit(tc), NAECHSTER)
    assert e.gestoppt is None, e.gestoppt
    assert set(e.buchstopps) == {"crossover"} and "Kasse EUR" in e.buchstopps["crossover"]["titel"]
    assert j.zustand("_konto")["kassenbasis"]["EUR"] == pytest.approx(basis)       # Basis unverändert bis zur Buchung
    # passt nicht (149 statt 150) → Kontokasse: Stopp für alles
    buchstopp.aktualisieren(j, {}, NAECHSTER, aufheben=False)
    e2 = _kasse_lauf(j, rm, {"EUR": basis + start + 149.0}, [], flex_mit(tc), NAECHSTER)
    assert e2.gestoppt and "Kasse EUR" in e2.gestoppt


def test_abweichung_ohne_beleg_verschwindet_stopp_bleibt_bis_zur_quittung(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "EUNK.DE", 10)
    lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 20, 25.0)]), flex=flex_mit())
    with pytest.raises(ValueError, match="besteht noch"):
        buchstopp.quittieren(j, "crossover")
    e = lauf(j, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 10, 25.0)]), flex=flex_mit())
    assert "crossover" in e.buchstopps and e.buchstopps["crossover"]["abweichung_weg"]
    assert not any(bv.vorschlag.buch == "crossover" for bv, _ in e.vorschlaege)
    assert any("Quittung" in s for s in e.sofort)
    e = lauf(j, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 10, 25.0)]), flex=flex_mit())
    assert "crossover" in e.buchstopps and not any("Quittung" in s for s in e.sofort)     # nur einmal gemeldet
    text = buchstopp.quittieren(j, "crossover", datetime(2026, 11, 4, 19, 5, 7))
    assert "quittiert von Jakob am 04.11.2026 19:05:07" in text and buchstopp.gestoppt(j) == {}
    q = j.db.execute("SELECT zeit, buch, text FROM ereignisse WHERE art='stopp_quittiert'").fetchall()
    assert [(r["zeit"], r["buch"]) for r in q] == [("2026-11-04T19:05:07", "crossover")]


def test_stopp_aufgehoben_wenn_beleg_gebucht_und_abgleich_sauber(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "EUNK.DE", 10, preis=100.0)
    fs = [{**z, "symbol": "EUNK", "currency": "EUR", "reportDate": "20261102"} for z in SPLIT]
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 20, 50.0)]), flex=flex_mit(fs))
    assert e.buchstopps["crossover"]["belege"] == ["CA:77"]
    # Buchung wie in A2 (hier von Hand): Posten des Buchs, Status gebucht
    j.db.execute("DELETE FROM kapitalmassnahmen WHERE beleg_id='CA:77' AND buch='crossover'")
    j.massnahme(beleg_id="CA:77", buch="crossover", art="split", status="gebucht", tag="2026-11-02",
                posten=[{"ticker": "EUNK.DE", "stueck": -10, "einstand": -1000.0}, {"ticker": "EUNK.DE", "stueck": 20, "einstand": 1000.0}])
    e = lauf(j, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 20, 50.0)]), flex=flex_mit(fs))
    assert e.buchstopps == {} and e.abgleich == "ok"
    assert any(s.startswith("Stopp aufgehoben: Buch crossover") for s in e.sofort)


def test_buch_mit_order_unterwegs_fuer_den_titel_wird_gestoppt_und_nicht_gesendet(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    kauf_cross = [z for z in j.vorschlaege(buch="crossover") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    assert len(kauf_cross) >= 2
    unterwegs, rest = kauf_cross[0], kauf_cross[1]
    j.status_setzen(unterwegs["id"], "gesendet", order_id="7")
    # IBKR meldet eine Position im Titel der Order unterwegs (kein Buch hält ihn): betrifft das Buch mit der Order
    pos = [Position("DU1", unterwegs["ticker"], 3, 25.0)]
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=pos), flex=flex_mit())
    assert e.gestoppt is None and set(e.buchstopps) == {"crossover"}
    assert any("Order unterwegs" in d for d in e.buchstopps["crossover"]["details"])
    # nicht freigebbar, und eine ältere Freigabe wird beim Senden übersprungen
    j.status_setzen(rest["id"], "freigegeben")
    b = BrokerAttrappe(positionen=pos)
    m = freigeben_und_senden(j, [], b, ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    assert b.gesendet == [] and any("gestoppt – nicht gesendet" in x for x in m), m
    real = [z["id"] for z in j.vorschlaege(buch="real") if z["status"] == "vorgeschlagen"]
    j.db.execute("UPDATE vorschlaege SET status='vorgeschlagen' WHERE id=?", (rest["id"],))
    j.db.commit()
    m = freigeben_und_senden(j, [rest["id"]] + real, BrokerAttrappe(positionen=pos), ABEND, risk=rm, kurse_laden=kurse_attrappe(),
                             konfig_betrieb=AN)
    assert any("ist gestoppt (Abgleich) – nicht freigebbar" in x for x in m)
    assert j.db.execute("SELECT status FROM vorschlaege WHERE id=?", (rest["id"],)).fetchone()[0] == "vorgeschlagen"


def test_stop_gerissen_im_gestoppten_buch_nur_meldung():
    def bv(ticker, richtung, ausstieg=None):
        return SimpleNamespace(vorschlag=SimpleNamespace(ticker=ticker, richtung=richtung), daten={"ausstieg": ausstieg} if ausstieg else {})
    w = buchstopp.stop_warnungen("crossover", [bv("ABC.DE", -1, "stop"), bv("EUNK.DE", -1, "stop"), bv("X.DE", -1, "zeit"), bv("Y.DE", 1)],
                                 {"titel": ["ABC.DE"]})
    assert w == ["Stop gerissen in gestopptem Buch: ABC.DE (crossover) – Werte vor Buchung der Maßnahme, ggf. Fehlalarm",
                 "Stop gerissen in gestopptem Buch: EUNK.DE (crossover)"]


def test_kurzfassung_ampel_und_sofortmeldung_zeigen_gestopptes_buch(umgebung):
    from tradingbot.betrieb import ansicht
    from tradingbot.betrieb.benachrichtigung import kurzfassung, nach_tageslauf

    j, rm = umgebung
    lauf(j, rm)
    kauf(j, "crossover", "EUNK.DE", 10)
    e = lauf(j, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 20, 25.0)]), flex=flex_mit())
    b = lade_konfiguration("betrieb")
    text = kurzfassung(e, j, b)
    assert "gestoppt: crossover" in text.splitlines()[0] and "Abgleich: ok außer in gestoppten Büchern" in text
    zeile = next(z for z in text.splitlines() if z.startswith("Buch crossover gestoppt"))
    assert "EUNK.DE" in zeile and "Stück" not in zeile and "20" not in zeile
    lampen = {la.name: la for la in ansicht.ampel(e, j, b, probe=False, gateway={"verbunden": True}, jetzt=ABEND)}
    assert lampen["Stopp crossover"].farbe == ansicht.ROT and lampen["Senden crossover"].text == "gestoppt"

    class Melder:
        eurobetraege = True
        def __init__(self):
            self.texte = []
        def melden(self, t):
            self.texte.append(t)
            return "gesendet"
        def lebenszeichen(self):
            return "ping"
    m = Melder()
    nach_tageslauf(e, j, b, m)
    assert len(m.texte) == 2 and m.texte[1].startswith("⛔ Sofortmeldung") and "Buch crossover gestoppt" in m.texte[1]
