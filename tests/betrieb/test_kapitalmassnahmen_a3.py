"""A3 (Jakob 12.11.2026): Übernahme (TC) und Delisting wertlos (DW) nach Bestätigung in der Oberfläche.

Kenvue-Konditionen laut gemeinsamer Pressemitteilung vom 03.11.2025 und 8-K vom 02.11.2026 (Vollzug): je Kenvue-Aktie
0,14625 Kimberly-Clark-Aktien und 3,50 USD bar; Bruchteile bar (VWAP-Durchschnitt der 5 Handelstage vor dem Vollzug –
hier ein angenommener Kurs von 120 USD, der echte steht im Flex-Beleg)."""
from datetime import datetime

import pytest

from tradingbot.betrieb import buchstopp, kapitalmassnahmen as km
from tradingbot.broker.basis import Position

from test_kapitalmassnahmen import flex_mit, kauf
from test_kapitalmassnahmen_a2 import FX, JETZT, erkennen_und_buchen, j, umgebung, vorschlag, zeile  # noqa: F401
from test_tageslauf import BrokerAttrappe, lauf

KVUE = "MERGED(Acquisition) WITH US4943681035 14625 FOR 100000 AND USD 3.50"
TAB = {901: "KMB"}


def kauf_usd(j, buch, ticker, stueck, preis, nr="1"):
    j.ausfuehrung(f"u{buch}{ticker}{nr}", f"{buch}:u{nr}{ticker}", ticker, 1, stueck, preis / FX["USD"], 1.10, "2026-10-01T15:30:00",
                  waehrung="USD", preis=preis, gebuehr=1.0, gebuehr_waehrung="USD")


def kenvue(alt, neu, erloes, beschreibung=KVUE):
    return [zeile(-alt, typ="TC", aid="55", conid="900", symbol="KVUE", waehrung="USD", erloes=erloes, beschreibung=beschreibung,
                  isin="US49177J1025"),
            zeile(neu, typ="TC", aid="55", conid="901", symbol="KMB", waehrung="USD", beschreibung=beschreibung, isin="US4943681035")]


def test_konditionen_aus_der_beschreibung():
    assert km.konditionen(f"KVUE(US49177J1025) {KVUE} (KVUE, KENVUE INC)") == (pytest.approx(0.14625), "USD", 3.5)
    assert km.konditionen("XYZ(US1) MERGED(Acquisition) FOR USD 50.00 PER SHARE (XYZ)") == (None, "USD", 50.0)


def test_kenvue_ein_buch_erst_nach_bestaetigung_exakt_gebucht(j):
    kauf_usd(j, "fundamental_a", "KVUE", 100, 20.0)                        # Einstand 2.000 USD
    j.zustand_speichern("fundamental_a", {"letzter_signaltag": "2026-10-01", "ziel": {"KVUE": 0.05, "AAA": 0.05}, "rang": {"KVUE": 4}})
    usd = j.kasse_je_waehrung("fundamental_a").get("USD", 0.0)
    pos = [Position("DU1", "KMB", 14, 120.0)]
    # 100 × 0,14625 = 14,625 → 14 KMB; bar 100 × 3,50 = 350 + Spitze 0,625 × 120 = 75 → 425 USD
    erg, m = erkennen_und_buchen(j, kenvue(100, 14, "425.00"), pos, ticker_je_conid=TAB)
    assert erg == [] and any("wartet auf Bestätigung" in x for x in m) and j.bestand("fundamental_a") == {"KVUE": 100}
    assert [o["bestaetigbar"] for o in km.bestaetigung_offen(j, "fundamental_a")] == [True]
    assert "0.14625 neue Aktien je Aktie" in km.bestaetigung_offen(j)[0]["text"]
    text = km.bestaetigen(j, "CA:55", datetime(2026, 11, 3, 21, 0, 5))
    assert "bestätigt von Jakob am 03.11.2026 21:00:05" in text and "nächsten Tageslauf" in text
    assert j.bestand("fundamental_a") == {"KVUE": 100}                       # gebucht erst im nächsten Lauf
    m = []
    erg = km.buchen(j, ["crossover", "momentum", "fundamental_a"], pos, m, fx=FX, ticker_je_conid=TAB, jetzt=JETZT)
    assert [b.ok for b in erg] == [True], m
    assert j.bestand("fundamental_a") == {"KMB": 14}
    assert j.einstaende("fundamental_a")["KMB"]["w"] == pytest.approx(2000.0 * 14 / 14.625)   # Einstand übertragen, Spitze anteilig ab
    assert j.kasse_je_waehrung("fundamental_a")["USD"] == pytest.approx(usd + 425.0)
    arten = {p["art"]: p["betrag"] for p in j.massnahme_posten("CA:55", "fundamental_a") if p["art"] != "bestand"}
    assert arten == {"barzuzahlung": pytest.approx(350.0), "spitzenausgleich": pytest.approx(75.0)}
    assert any("Barzuzahlung (§ 20 Abs. 4a, zu prüfen) +350.00 USD" in x for x in m)
    assert j.zustand("fundamental_a")["ziel"] == {"AAA": 0.05} and j.zustand("fundamental_a")["rang"] == {}
    assert km.buchen(j, ["fundamental_a"], pos, [], fx=FX, ticker_je_conid=TAB) == []          # nicht doppelt


def test_kenvue_zwei_buecher_spitzen_nach_groesstem_rest(j):
    kauf_usd(j, "fundamental_a", "KVUE", 100, 20.0)
    kauf_usd(j, "crossover", "KVUE", 60, 20.0)
    # 14,625 + 8,775 = 23,4 → IBKR 23 KMB; 0,4 bar zu 120 = 48; Barzuzahlung 160 × 3,50 = 560 → 608 USD
    erkennen_und_buchen(j, kenvue(160, 23, "608.00"), [], ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:55")
    erg = km.buchen(j, ["crossover", "fundamental_a"], [Position("DU1", "KMB", 23, 120.0)], m := [], fx=FX, ticker_je_conid=TAB)
    assert erg[0].ok, m
    assert j.bestand("fundamental_a") == {"KMB": 14} and j.bestand("crossover") == {"KMB": 9}      # crossover: Rest 0,775 > 0,625
    spitze = {b: sum(p["betrag"] for p in j.massnahme_posten("CA:55", b) if p["art"] == "spitzenausgleich") for b in ("crossover", "fundamental_a")}
    assert spitze == {"crossover": pytest.approx(-27.0), "fundamental_a": pytest.approx(75.0)}
    bar = {b: sum(p["betrag"] for p in j.massnahme_posten("CA:55", b) if p["art"] == "barzuzahlung") for b in ("crossover", "fundamental_a")}
    assert bar == {"crossover": pytest.approx(210.0), "fundamental_a": pytest.approx(350.0)}


@pytest.mark.parametrize("neu, erloes, grund", [(14, "340.00", "Probe Kasse"), (15, "425.00", "Probe: Bücher")])
def test_kenvue_probe_scheitert_nichts_gebucht(j, neu, erloes, grund):
    kauf_usd(j, "fundamental_a", "KVUE", 100, 20.0)
    erkennen_und_buchen(j, kenvue(100, neu, erloes), [], ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:55")
    erg = km.buchen(j, ["fundamental_a"], [Position("DU1", "KMB", neu, 120.0)], [], fx=FX, ticker_je_conid=TAB)
    assert not erg[0].ok and grund in erg[0].text and j.bestand("fundamental_a") == {"KVUE": 100}


def test_neue_conid_fehlt_in_kontrakte_yaml(j):
    kauf_usd(j, "fundamental_a", "KVUE", 100, 20.0)
    erkennen_und_buchen(j, kenvue(100, 14, "425.00"), [])
    km.bestaetigen(j, "CA:55")
    erg = km.buchen(j, ["fundamental_a"], [Position("DU1", "KMB", 14, 120.0)], [], fx=FX, ticker_je_conid={})
    assert not erg[0].ok and "config/kontrakte.yaml" in erg[0].text


def test_ablehnen_buch_bleibt_gestoppt_bis_zur_quittung(j):
    kauf_usd(j, "fundamental_a", "KVUE", 100, 20.0)
    erkennen_und_buchen(j, kenvue(100, 14, "425.00"), [], ticker_je_conid=TAB)
    text = km.ablehnen(j, "CA:55", datetime(2026, 11, 3, 21, 5))
    assert "abgelehnt von Jakob am 03.11.2026 21:05:00" in text
    assert {r["status"] for r in j.massnahmen("beleg_id='CA:55'")} == {"abgelehnt"}
    assert km.buchen(j, ["fundamental_a"], [Position("DU1", "KMB", 14, 120.0)], [], fx=FX, ticker_je_conid=TAB) == []
    st = buchstopp.gestoppt(j)["fundamental_a"]
    assert st["quittung_noetig"] and "Quittung in der Oberfläche nötig" in buchstopp.kurz("fundamental_a", st)
    # IBKR zeigt KMB, das Buch noch KVUE: dem Buch zugeordnet, nicht Stopp für alles
    diff, je_buch = buchstopp.zuordnen(j, ["crossover", "fundamental_a"], [Position("DU1", "KMB", 14, 120.0)])
    assert diff == [] and set(je_buch) == {"fundamental_a"}
    with pytest.raises(ValueError):
        km.bestaetigen(j, "CA:55")


def test_reine_barabfindung(j):
    kauf_usd(j, "fundamental_a", "XYZ", 10, 40.0)
    usd = j.kasse_je_waehrung("fundamental_a").get("USD", 0.0)
    erkennen_und_buchen(j, [zeile(-10, typ="TC", aid="56", conid="910", symbol="XYZ", waehrung="USD", erloes="500.00",
                                  beschreibung="MERGED(Acquisition) FOR USD 50.00 PER SHARE", isin="US0009")], [])
    km.bestaetigen(j, "CA:56")
    erg = km.buchen(j, ["fundamental_a"], [], m := [], fx=FX, ticker_je_conid={})
    assert erg[0].ok, m
    assert j.bestand("fundamental_a") == {} and j.kasse_je_waehrung("fundamental_a")["USD"] == pytest.approx(usd + 500.0)
    assert [p["art"] for p in j.massnahme_posten("CA:56", "fundamental_a")] == ["bestand", "barabfindung"]
    assert "Barabfindung (Veräußerung § 20 Abs. 2, zu prüfen)" in m[-1]


def test_delisting_wertlos_und_dw_mit_gegenleistung(j):
    kauf_usd(j, "fundamental_a", "PLEITE", 10, 5.0)
    kauf_usd(j, "fundamental_a", "OTC", 10, 5.0)
    erkennen_und_buchen(j, [zeile(-10, typ="DW", aid="57", conid="920", symbol="PLEITE", waehrung="USD", beschreibung="DELISTED WORTHLESS"),
                            zeile(-10, typ="DW", aid="58", conid="921", symbol="OTC", waehrung="USD", erloes="3.00", beschreibung="DELISTED")], [])
    km.bestaetigen(j, "CA:57")
    km.bestaetigen(j, "CA:58")
    erg = {b.beleg_id: b for b in km.buchen(j, ["fundamental_a"], [], [], fx=FX, ticker_je_conid={})}
    assert erg["CA:57"].ok and "PLEITE" not in j.bestand("fundamental_a")
    assert "PLEITE" not in j.einstaende("fundamental_a") or j.einstaende("fundamental_a")["PLEITE"]["w"] == pytest.approx(0.0)
    assert not erg["CA:58"].ok and "kein „Delisting wertlos“" in erg["CA:58"].text and j.bestand("fundamental_a")["OTC"] == 10


def test_delisting_mit_handel_ausserboerslich_unbekanntes_kuerzel_stoppt_wie_a1(umgebung):
    """Kein DW: Handel geht außerbörslich weiter (hier Kürzel „DL“, IBKR-Position unverändert). Unbekanntes Kürzel → Stopp wie
    in A1, nie automatisch gebucht; Jakob lehnt nach Prüfung ab und quittiert."""
    jj, rm = umgebung
    lauf(jj, rm)
    kauf(jj, "crossover", "EUNK.DE", 10)
    dl = [{"type": "DL", "actionID": "60", "conid": "930", "symbol": "EUNK", "currency": "EUR", "quantity": "0", "proceeds": "0",
           "reportDate": "20261102", "description": "EUNK DELISTED - TRADES OTC", "transactionID": "960"}]
    pos = [Position("DU1", "EUNK.DE", 10, 25.0)]
    e = lauf(jj, rm, broker=BrokerAttrappe(positionen=pos), flex=flex_mit(dl))
    assert jj.massnahmen("beleg_id='CA:60' AND buch='_konto'")[0]["art"] == "sonstige"
    assert set(e.buchstopps) == {"crossover"} and jj.bestand("crossover") == {"EUNK.DE": 10}
    offen = km.bestaetigung_offen(jj, "crossover")
    assert [o["bestaetigbar"] for o in offen] == [False]
    with pytest.raises(ValueError, match="nicht bestätigbar"):
        km.bestaetigen(jj, "CA:60")
    km.ablehnen(jj, "CA:60")
    from test_kapitalmassnahmen import NAECHSTER
    e = lauf(jj, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=pos), flex=flex_mit(dl))
    assert e.buchstopps["crossover"]["abweichung_weg"]                         # Quittung jetzt möglich
    assert "quittiert von Jakob" in buchstopp.quittieren(jj, "crossover")


def test_order_ueber_stichtag_bei_uebernahme(j):
    kauf_usd(j, "fundamental_a", "KVUE", 100, 20.0)
    vorschlag(j, "a1", "fundamental_a", "KVUE", 1, 10, 21.0, "vorgeschlagen")
    vorschlag(j, "a2", "fundamental_a", "KVUE", 1, 5, 21.0, "gesendet")
    erkennen_und_buchen(j, kenvue(100, 14, "425.00"), [], ticker_je_conid=TAB)
    km.bestaetigen(j, "CA:55")
    erg = km.buchen(j, ["fundamental_a"], [Position("DU1", "KMB", 14, 120.0)], [], fx=FX, ticker_je_conid=TAB)
    assert erg[0].ok
    status = {r["id"]: (r["status"], r["stueck"]) for r in j.db.execute("SELECT id, status, stueck FROM vorschlaege")}
    assert status == {"a1": ("ersetzt", 10), "a2": ("gesendet", 5)}                  # unterwegs: nicht umgedeutet
    assert any("über den Stichtag unterwegs" in d for d in buchstopp.gestoppt(j)["fundamental_a"]["details"])


def test_fremdtitel_im_technikbuch_bekommt_ausstiegsvorschlag(umgebung):
    jj, rm = umgebung
    lauf(jj, rm)
    kauf(jj, "crossover", "FREMD.DE", 5)
    e = lauf(jj, rm, broker=BrokerAttrappe(positionen=[Position("DU1", "FREMD.DE", 5, 25.0)]), flex=flex_mit())
    v = [bv.vorschlag for bv, _ in e.vorschlaege if bv.vorschlag.buch == "crossover" and bv.vorschlag.ticker == "FREMD.DE"]
    assert len(v) == 1 and v[0].richtung < 0 and v[0].stueck == 5 and "Fremdtitel" in v[0].these
    assert any("Fremdtitel aus Kapitalmaßnahme FREMD.DE" in x for x in e.meldungen)
