"""Verpasste Abende (Jakob 09.11.2026): Ausführungen außerhalb des API-Zeitfensters werden erkannt und mit Beleg
nachgetragen (Flex, sonst Position mit Einstand); ohne Beleg stoppt der Tageslauf, nichts wird gebucht oder verfallen."""
import copy
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from test_tageslauf import ABEND, AN, BrokerAttrappe, KontoAttrappe, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb.nachtrag import flex_ausfuehrungen, naechste_sitzung
from tradingbot.betrieb.tageslauf import freigeben_und_senden
from tradingbot.broker.basis import Position
from tradingbot.konfiguration import lade_konfiguration

SPAETER = datetime(2026, 11, 5, 19, 30, tzinfo=ZoneInfo("Europe/Berlin"))   # Abende 03. und 04.11. verpasst
HANDELSTAG = date(2026, 11, 3)                                                # Order vom 02.11. abends gilt am 03.11.


PLAN = {"xetra_eur": {"je_order": 3.0}, "us_usd": {"je_aktie": 0.005, "minimum": 1.0, "maximum_anteil": 0.01}}


def _konfig(gebuehr=3.0):
    k = {n: lade_konfiguration(n) for n in ("betrieb", "technik", "fundamental", "backtest")}
    k["betrieb"] = copy.deepcopy(k["betrieb"])
    k["betrieb"]["nachtrag"] = {"gebuehr": None if gebuehr is None else {**PLAN, "xetra_eur": {"je_order": gebuehr}}}
    return k


def _gesendet(j, rm):
    """Realbuch: Tageslauf am 02.11., Freigabe und Senden; die Order steht danach als „gesendet“ im Journal."""
    lauf(j, rm)
    z = next(x for x in j.vorschlaege(buch="real") if x["status"] == "vorgeschlagen")
    freigeben_und_senden(j, [z["id"]], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    z = j.vorschlaege(buch="real")[0]
    assert z["status"] == "gesendet"
    return z


def _tagespreis():
    k = kurse_attrappe()("SPYI.DE", HANDELSTAG, "etf")
    return float(k.loc[str(HANDELSTAG), "open"])


def test_naechste_sitzung():
    assert naechste_sitzung("xetra", "2026-11-03") == date(2026, 11, 4)
    assert naechste_sitzung("xetra", "2026-11-06") == date(2026, 11, 9)          # Freitag → Montag
    assert naechste_sitzung("xetra", "2026-12-23") == date(2026, 12, 28)         # Heiligabend und Feiertage


def test_verpasster_abend_nachtrag_aus_position(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    preis = _tagespreis()
    einstand = (preis * z["stueck"] + 3.0) / z["stueck"]                          # IBKR: Einstand inklusive Gebühr
    broker = KontoAttrappe({"EUR": 1_000_000.0 - preis * z["stueck"] - 3.0},
                           positionen=[Position("DU1", "SPYI.DE", z["stueck"], einstand)])   # keine Fills mehr über die API
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt is None, e.gestoppt
    assert any("außerhalb des API-Zeitfensters vermutet" in m for m in e.meldungen)
    assert any(m.startswith("Nachtrag real:") and "IBKR Position (Einstand)" in m for m in e.meldungen)
    a = j.db.execute("SELECT * FROM ausfuehrungen WHERE buch='real'").fetchone()
    assert a["stueck"] == z["stueck"] and abs(a["preis"] - preis) < 1e-9 and a["gebuehr_eur"] == 3.0
    assert a["quelle"].startswith("IBKR Position (Einstand)") and a["zeit"] == "2026-11-03" and a["boerse"] is None
    assert j.vorschlaege(buch="real")[0]["status"] == "ausgefuehrt"
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='nachtrag' AND buch='real'").fetchone()[0] == 1
    assert any("Abgleich: Bestände aller Bücher stimmen" in m for m in e.meldungen)
    assert abs(j.kasse("real") - (500 - preis * z["stueck"] - 3.0)) < 1e-6
    # Kassenbasis ohne den nachgetragenen Kauf: Paper-Startguthaben
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_000.0) < 1e-6
    # nächster Lauf: kein zweiter Nachtrag, Kasse stimmt weiter
    e2 = lauf(j, rm, jetzt=SPAETER.replace(day=6), broker=broker, konfig=_konfig(), flex=None)
    assert e2.gestoppt is None and len(j.db.execute("SELECT * FROM ausfuehrungen").fetchall()) == 1
    assert any("Kasse je Währung stimmt" in m for m in e2.meldungen)


def test_verpasster_abend_ohne_beleg_stoppt(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    broker = KontoAttrappe({"EUR": 999_000.0}, positionen=[Position("DU1", "SPYI.DE", z["stueck"], 11.0)])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(gebuehr=None), flex=None)
    assert e.gestoppt and "ohne Beleg" in e.gestoppt and "Flex" in e.gestoppt and e.vorschlaege == []
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet"                 # weder verfallen noch gebucht
    assert j.bestand("real") == {} and "kassenbasis" not in j.zustand("_konto")


def test_preis_ausserhalb_der_tagesspanne_stoppt(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    broker = KontoAttrappe({"EUR": 999_000.0}, positionen=[Position("DU1", "SPYI.DE", z["stueck"], _tagespreis() * 0.8)])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt and "außerhalb Tief/Hoch" in e.gestoppt
    assert j.vorschlaege(buch="real")[0]["status"] == "gesendet"


def test_teilausfuehrung_ohne_flex_stoppt(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    broker = KontoAttrappe({"EUR": 999_000.0}, positionen=[Position("DU1", "SPYI.DE", z["stueck"] - 1, _tagespreis())])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt and "Teilausführung" in e.gestoppt


def test_verpasster_abend_nachtrag_aus_flex(umgebung):
    j, rm = umgebung
    z = _gesendet(j, rm)
    preis = _tagespreis()
    flex_zeilen = [{"orderReference": f"real:{z['id']}", "ibExecID": "0000e0d5.6729a1b2.01.01", "assetCategory": "STK", "symbol": "SPYI",
                    "conid": "0", "currency": "EUR", "buySell": "BUY", "quantity": str(z["stueck"]), "tradePrice": str(preis),
                    "ibCommission": "-3", "ibCommissionCurrency": "EUR", "dateTime": "20261103;090007", "exchange": "IBIS2"},
                   {"orderReference": "fremd:x", "ibExecID": "y", "assetCategory": "STK", "symbol": "ABC", "conid": "0", "currency": "USD",
                    "buySell": "BUY", "quantity": "1", "tradePrice": "1", "ibCommission": "-1", "dateTime": "20261103;150000"}]
    broker = KontoAttrappe({"EUR": 1_000_000.0 - preis * z["stueck"] - 3.0},
                           positionen=[Position("DU1", "SPYI.DE", z["stueck"], preis + 3.0 / z["stueck"])])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(gebuehr=None), flex=lambda: (flex_zeilen, "IBKR Flex-Abfrage 123, erstellt x"))
    assert e.gestoppt is None, e.gestoppt
    a = j.db.execute("SELECT * FROM ausfuehrungen").fetchall()
    assert len(a) == 1 and a[0]["exec_id"] == "0000e0d5.6729a1b2.01.01" and a[0]["boerse"] == "IBIS2"
    assert a[0]["quelle"] == "IBKR Flex-Abfrage 123, erstellt x" and a[0]["zeit"] == "2026-11-03T09:00:07"


def test_ohne_abweichung_verfallen_wie_bisher(umgebung):
    j, rm = umgebung
    _gesendet(j, rm)
    e = lauf(j, rm, jetzt=SPAETER, broker=KontoAttrappe({"EUR": 1_000_000.0}), konfig=_konfig(), flex=None)
    assert e.gestoppt is None and j.vorschlaege(buch="real")[0]["status"] in ("verfallen",)
    assert any("verfallen" in m for m in e.meldungen)


def test_flex_tausch():
    zeilen = [{"orderReference": "fundamental_a:t", "ibExecID": "f1", "assetCategory": "CASH", "symbol": "EUR.USD", "currency": "USD",
               "buySell": "SELL", "quantity": "-9000", "tradePrice": "1.1", "ibCommission": "-2", "ibCommissionCurrency": "USD",
               "dateTime": "2026-11-03;22:10:00"}]
    a = flex_ausfuehrungen(zeilen, {"fundamental_a:t"})[0]
    assert a["art"] == "fx" and a["von"] == "EUR" and a["nach"] == "USD" and a["betrag_von"] == 9000
    assert a["betrag_nach"] == pytest.approx(9900) and a["gebuehr"] == 2 and a["zeit"] == "2026-11-03T22:10:00"


# --- Gebühr je Markt und Währung, angenommen, Abgleich mit Flex (Jakob 09.11.2026) -----------------------------------------
def test_nachtrag_gebuehr_je_markt():
    from tradingbot.betrieb.nachtrag import nachtrag_gebuehr
    assert nachtrag_gebuehr(PLAN, "SPYI.DE", 42, 11.6)[0] == 3.0
    assert nachtrag_gebuehr(PLAN, "AAPL", 10, 100.1)[0] == pytest.approx(1.0)              # Minimum 1 USD
    assert nachtrag_gebuehr(PLAN, "F", 1000, 12.0)[0] == pytest.approx(5.0)                # 0,005 je Aktie
    assert nachtrag_gebuehr(PLAN, "X", 1, 50.0)[0] == pytest.approx(0.5, abs=0.01)         # höchstens 1 % des Orderwerts
    g = lade_konfiguration("betrieb")["nachtrag"]["gebuehr"]                               # Konfiguration wie festgelegt
    assert g["xetra_eur"]["je_order"] == 3.0 and g["us_usd"] == {"je_aktie": 0.005, "minimum": 1.0, "maximum_anteil": 0.01}


def _nachgetragen(j, rm):
    z = _gesendet(j, rm)
    preis = _tagespreis()
    broker = KontoAttrappe({"EUR": 1_000_000.0 - preis * z["stueck"] - 3.0},
                           positionen=[Position("DU1", "SPYI.DE", z["stueck"], (preis * z["stueck"] + 3.0) / z["stueck"])])
    e = lauf(j, rm, jetzt=SPAETER, broker=broker, konfig=_konfig(), flex=None)
    assert e.gestoppt is None and len(j.angenommene()) == 1
    return z, preis, broker


def test_angenommene_gebuehr_mit_flex_abgeglichen(umgebung):
    j, rm = umgebung
    z, preis, broker = _nachgetragen(j, rm)
    kasse_vorher = j.kasse("real")
    ref = f"real:{z['id']}"
    teil = z["stueck"] // 2
    p1, p2 = preis - 0.01, (preis * z["stueck"] - (preis - 0.01) * teil) / (z["stueck"] - teil)   # gleicher Kurswert
    zeilen = [{"orderReference": ref, "ibExecID": f"x{i}", "assetCategory": "STK", "symbol": "SPYI", "conid": "0", "currency": "EUR",
               "buySell": "BUY", "quantity": str(q), "tradePrice": str(p), "ibCommission": str(-g), "ibCommissionCurrency": "EUR",
               "dateTime": "20261103;090001", "exchange": "GETTEX2"}
              for i, (q, p, g) in enumerate(((teil, p1, 3.0), (z["stueck"] - teil, p2, 0.0)))]
    e = lauf(j, rm, jetzt=SPAETER.replace(day=6), broker=broker, konfig=_konfig(), flex=lambda: (zeilen, "IBKR Flex-Abfrage 7, erstellt y"))
    assert e.gestoppt is None, e.gestoppt
    assert any(m.startswith(f"Abgleich {ref} mit IBKR Flex-Abfrage 7") and "(angenommen)" in m for m in e.meldungen)
    a = j.db.execute("SELECT exec_id, gebuehr_angenommen, quelle FROM ausfuehrungen ORDER BY exec_id").fetchall()
    assert [r["exec_id"] for r in a] == ["x0", "x1"] and not any(r["gebuehr_angenommen"] for r in a)
    assert j.angenommene() == [] and j.bestand("real") == {"SPYI.DE": z["stueck"]}
    assert abs(j.kasse("real") - kasse_vorher) < 1e-6
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='nachtrag_abgleich'").fetchone()[0] == 1


def test_angenommene_gebuehr_flex_stueck_weicht_ab_stoppt(umgebung):
    j, rm = umgebung
    z, preis, broker = _nachgetragen(j, rm)
    zeilen = [{"orderReference": f"real:{z['id']}", "ibExecID": "x0", "assetCategory": "STK", "symbol": "SPYI", "conid": "0",
               "currency": "EUR", "buySell": "BUY", "quantity": "1", "tradePrice": str(preis), "ibCommission": "-3",
               "dateTime": "20261103;090001"}]
    e = lauf(j, rm, jetzt=SPAETER.replace(day=6), broker=broker, konfig=_konfig(), flex=lambda: (zeilen, "Flex"))
    assert e.gestoppt and "Flex meldet 1 Stück" in e.gestoppt and len(j.angenommene()) == 1


# --- Zinsen (Jakob 09.11.2026) --------------------------------------------------------------------------------------
class ZinsAttrappe(KontoAttrappe):
    def __init__(self, kasse, zinsen, **kw):
        super().__init__(kasse, **kw)
        self._zinsen = zinsen

    def aufgelaufene_zinsen(self):
        return dict(self._zinsen)


def test_zinsbuchung_mit_abnahme_der_aufgelaufenen_zinsen(umgebung):
    from tradingbot.betrieb.tageslauf import kassenabgleich
    j, rm = umgebung
    lauf(j, rm)
    b = lade_konfiguration("betrieb")
    buecher = list(b["buecher"])
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 225.74}), b)
    diff, _ = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 240.10}), b)   # Zinsen laufen auf
    assert diff == [] and j.zustand("_konto")["aufgelaufene_zinsen"] == {"EUR": 240.10}
    diff, text = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_240.10}, {"EUR": 0.0}), b)   # Zinsen gebucht
    assert diff == [] and "Zinsbuchung belegt" in text and "+240.10" in text
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_240.10) < 1e-6
    assert all(abs(j.kasse(n) - j.startkapital(n)) < 1e-9 for n in buecher)                       # Bücher ohne Zinsen
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE text LIKE 'Zinsbuchung belegt%'").fetchone()[0] == 1
    # Kassenerhöhung ohne passende Abnahme der aufgelaufenen Zinsen → Stopp
    diff, _ = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_540.10}, {"EUR": 0.0}), b)
    assert diff and "unerklärte Buchung" in diff[0] and "passt nicht" in diff[0]
    # Erhöhung kleiner als der letzte Zinsstand → Stopp
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_240.10}, {"EUR": 100.0}), b)
    diff, _ = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_300.10}, {"EUR": 0.0}), b)
    assert diff and "passt nicht" in diff[0]
    # Kassenabnahme über 10 € stoppt weiter
    diff, _ = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_200.10}, {"EUR": 0.0}), b)
    assert diff and "-40.00" in diff[0]


# --- Verpasste Tage im Technikbuch (Jakob 09.11.2026) ----------------------------------------------------------------
def _mit_einbruch(ticker, tag, faktor):
    basis = kurse_attrappe()

    def laden(t, bis, art):
        k = basis(t, bis, art)
        if t == ticker and pd.Timestamp(tag) in k.index:
            k = k.copy()
            k.loc[pd.Timestamp(tag), ["low", "close"]] = k.loc[pd.Timestamp(tag), ["low", "close"]] * faktor
        return k
    return laden


def _crossover_gekauft(j, rm):
    """Crossover-Käufe am 02.11. vorgeschlagen, gesendet und am 03.11. zur Eröffnung ausgeführt."""
    lauf(j, rm)
    ids = [z["id"] for z in j.vorschlaege(buch="crossover") if z["status"] == "vorgeschlagen" and z["richtung"] > 0]
    assert ids
    freigeben_und_senden(j, ids, BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    for z in j.vorschlaege(buch="crossover"):
        if z["status"] == "gesendet":
            k = kurse_attrappe()(z["ticker"], HANDELSTAG, "etf")
            j.ausfuehrung(f"c-{z['ticker']}", f"crossover:{z['id']}", z["ticker"], 1, z["stueck"],
                          float(k.loc[str(HANDELSTAG), "open"]), 3.0, "2026-11-03T09:00")
    return sorted(j.bestand("crossover"))


FREITAG = datetime(2026, 11, 6, 23, 30, tzinfo=ZoneInfo("Europe/Berlin"))       # Abende 03.–05.11. verpasst


def test_verpasste_tage_stop_wird_nachgeholt(umgebung):
    j, rm = umgebung
    titel = _crossover_gekauft(j, rm)
    t = titel[0]
    e = lauf(j, rm, jetzt=FREITAG, kurse=_mit_einbruch(t, "2026-11-04", 0.8))
    assert any("Handelstag(e) ohne Lauf seit 02.11.2026" in m for m in e.meldungen)
    verkauf = [bv for bv, u in e.vorschlaege if bv.vorschlag.buch == "crossover" and bv.vorschlag.richtung < 0]
    assert [bv.vorschlag.ticker for bv in verkauf] == [t]
    assert "gerissen am 04.11., nachgeholt" in verkauf[0].kern and verkauf[0].vorschlag.stueck == j.bestand("crossover")[t]
    # Einstiege verpasster Tage werden nicht nachgeholt; gehaltene Titel werden nicht erneut gekauft
    assert not any(bv.vorschlag.ticker in titel and bv.vorschlag.richtung > 0 for bv, _ in e.vorschlaege if bv.vorschlag.buch == "crossover")


def test_verpasste_tage_ohne_ausstieg_kein_verkauf(umgebung):
    j, rm = umgebung
    _crossover_gekauft(j, rm)
    e = lauf(j, rm, jetzt=FREITAG)
    assert not any(bv.vorschlag.buch == "crossover" and bv.vorschlag.richtung < 0 for bv, _ in e.vorschlaege)
    # zweiter Lauf am selben Abend: verpasste Tage weiter ab dem Vorlauf (02.11.)
    assert j.vorlauf_signaltag("crossover", "2026-11-06") == "2026-11-02"


def test_verpasste_handelstage():
    from tradingbot.betrieb.tageslauf import verpasste_handelstage
    assert verpasste_handelstage("xetra", "2026-11-03", "2026-11-09") == [pd.Timestamp(d) for d in ("2026-11-04", "2026-11-05", "2026-11-06")]
    assert verpasste_handelstage("xetra", "2026-11-06", "2026-11-09") == []
    assert verpasste_handelstage("xetra", None, "2026-11-09") == []


def test_zinsbuchung_mit_neuen_zinsen_zwischen_lauf_und_gutschrift(umgebung):
    """Jakob 10.11.2026, Zinsbilanz: belegt, wenn die aufgelaufenen Zinsen gesunken sind und Gutschrift + aktueller Stand −
    letzter Stand zwischen −0,05 € und Tageszins × Tage + 1 € liegt; Tageszins aus zwei Läufen geschätzt.
    Fall 1: Gutschrift enthält neue Tage. Fall 2 (Lücke): Gutschrift nur des Vormonats, letzter Lauf enthielt schon Tage
    des neuen Monats."""
    from tradingbot.betrieb.tageslauf import kassenabgleich
    j, rm = umgebung
    lauf(j, rm)
    b = lade_konfiguration("betrieb")
    buecher = list(b["buecher"])
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 225.74}), b, heute="2026-11-27")
    diff, _ = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 248.24}), b, heute="2026-11-30")
    assert diff == [] and abs(j.zustand("_konto")["tageszins"]["EUR"] - 7.5) < 1e-9          # (248,24 − 225,74) / 3 Tage
    # Fall 1: Läufe 01. und 02.12. verpasst; Gutschrift 263,24 (inkl. 01./02.12.), neu aufgelaufen 7,50 (03.12.), Lauf am 03.12.
    # Zinsbilanz 263,24 + 7,50 − 248,24 = 22,50 ≤ 7,50 × 3 + 1 = 23,50 → belegt
    diff, text = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_263.24}, {"EUR": 7.50}), b, heute="2026-12-03")
    assert diff == [] and "Zinsbuchung belegt" in text and "+263.24" in text and "Zinsbilanz +22.50" in text
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_263.24) < 1e-6
    assert all(abs(j.kasse(n) - j.startkapital(n)) < 1e-9 for n in buecher)                  # Bücher ohne Zinsen
    assert j.zustand("_konto")["zinsstand_tag"] == "2026-12-03" and j.zustand("_konto")["aufgelaufene_zinsen"] == {"EUR": 7.5}
    assert abs(j.zustand("_konto")["tageszins"]["EUR"] - 7.5) < 1e-9                         # bei Gutschrift unverändert


def test_zinsbuchung_nur_vormonat_waehrend_letzter_lauf_neue_tage_enthielt(umgebung):
    """Lückenfall: letzter Stand 263,24 (Vormonat 248,24 + zwei Tage des neuen Monats), IBKR schreibt nur den Vormonat gut
    (248,24), neuer Stand 22,50, 1 Tag später. Zinsbilanz 248,24 + 22,50 − 263,24 = 7,50 ≤ 7,50 × 1 + 1 → belegt."""
    from tradingbot.betrieb.tageslauf import kassenabgleich
    j, rm = umgebung
    lauf(j, rm)
    b = lade_konfiguration("betrieb")
    buecher = list(b["buecher"])
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 248.24}), b, heute="2026-11-30")
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 263.24}), b, heute="2026-12-02")
    assert abs(j.zustand("_konto")["tageszins"]["EUR"] - 7.5) < 1e-9
    diff, text = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_248.24}, {"EUR": 22.50}), b, heute="2026-12-03")
    assert diff == [] and "Zinsbuchung belegt" in text and "+248.24" in text and "Zinsbilanz +7.50" in text
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_248.24) < 1e-6
    assert all(abs(j.kasse(n) - j.startkapital(n)) < 1e-9 for n in buecher)


def test_zinsbilanz_grenzen():
    from tradingbot.betrieb.tageslauf import zinsbilanz, zinsbuchung_belegt
    assert zinsbilanz(263.24, 248.24, 7.5) == pytest.approx(22.5)
    # Fall 1: Grenze 7,50 × 3 + 1 = 23,50
    assert zinsbuchung_belegt(263.24, 248.24, 7.5, 7.5, 3, 0.05)
    assert zinsbuchung_belegt(264.24, 248.24, 7.5, 7.5, 3, 0.05)                             # Bilanz 23,50
    assert not zinsbuchung_belegt(264.30, 248.24, 7.5, 7.5, 3, 0.05)                         # Bilanz 23,56
    assert not zinsbuchung_belegt(263.24, 248.24, 7.5, 7.5, 2, 0.05)                         # 2 Tage: Grenze 16,00
    # Lückenfall: Grenze 7,50 × 1 + 1 = 8,50
    assert zinsbuchung_belegt(248.24, 263.24, 22.5, 7.5, 1, 0.05)                            # Bilanz 7,50
    assert zinsbuchung_belegt(240.79, 263.24, 22.5, 7.5, 1, 0.05)                            # Bilanz 0,05
    assert zinsbuchung_belegt(240.69, 263.24, 22.5, 7.5, 1, 0.05)                            # Bilanz −0,05
    assert not zinsbuchung_belegt(240.60, 263.24, 22.5, 7.5, 1, 0.05)                        # Bilanz −0,14
    assert not zinsbuchung_belegt(250.00, 248.24, 260.0, 7.5, 2, 0.05)                       # Zinsen nicht gesunken
    assert zinsbuchung_belegt(248.90, 248.24, 0.0, 0.0, 5, 0.05)                             # ohne Schätzung: nur + 1 €
    assert not zinsbuchung_belegt(249.30, 248.24, 0.0, 0.0, 5, 0.05)


def test_zinsbuchung_zu_gross_stoppt(umgebung):
    from tradingbot.betrieb.tageslauf import kassenabgleich
    j, rm = umgebung
    lauf(j, rm)
    b = lade_konfiguration("betrieb")
    buecher = list(b["buecher"])
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 225.74}), b, heute="2026-11-27")
    kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_000.0}, {"EUR": 248.24}), b, heute="2026-11-30")
    # Gutschrift 300 € nach zwei Tagen: Zinsbilanz 300 + 0 − 248,24 = 51,76 > 7,50 × 2 + 1 = 16,00 → Stopp
    diff, _ = kassenabgleich(j, buecher, ZinsAttrappe({"EUR": 1_000_300.0}, {"EUR": 0.0}), b, heute="2026-12-02")
    assert diff and "unerklärte Buchung" in diff[0] and "Zinsbilanz +51.76, zulässig −0,05 bis 16.00" in diff[0]
    assert abs(j.zustand("_konto")["kassenbasis"]["EUR"] - 1_000_000.0) < 1e-6               # nichts übernommen
