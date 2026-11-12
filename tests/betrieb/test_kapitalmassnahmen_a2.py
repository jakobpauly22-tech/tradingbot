"""A2 (Jakob 12.11.2026): Split, Reverse-Split und Tickerwechsel automatisch buchen – Probe, Spitzen, Kurseinheiten,
Kursreihe im Speicher, Fundamental-Kennzahlen je Aktie, Order über den Stichtag."""
import dataclasses
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from tradingbot.betrieb import buchstopp, kapitalmassnahmen as km
from tradingbot.betrieb.journal import Journal
from tradingbot.betrieb.kalender import pruefe_tageskurse
from tradingbot.broker.basis import Position
from tradingbot.engines.technik.strategien import Position as TechnikPosition
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import RiskManager

from test_kapitalmassnahmen import NAECHSTER, flex_mit, kauf
from test_tageslauf import KOSTEN, BrokerAttrappe, KontoAttrappe, kurse_attrappe, lauf

JETZT = datetime(2026, 11, 3, 23, 30)
FX = {"USD": 1.10}
TAG = "20261102"


@pytest.fixture
def j(tmp_path):
    jj = Journal(tmp_path / "journal.sqlite")
    for b in ("crossover", "momentum", "fundamental_a"):
        jj.buch_anlegen(b, 10_000.0)
    yield jj
    jj.schliessen()


@pytest.fixture
def umgebung(tmp_path):
    jj = Journal(tmp_path / "journal.sqlite")
    rm = RiskManager(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), KOSTEN, tmp_path)
    yield jj, rm
    jj.schliessen()


def zeile(menge, *, typ="FS", aid="77", conid="111", symbol="ABC", waehrung="EUR", erloes="0", beschreibung="SPLIT 2 FOR 1", tag=TAG,
          isin="DE0001"):
    return {"type": typ, "actionID": aid, "conid": conid, "symbol": symbol, "isin": isin, "currency": waehrung, "quantity": str(menge),
            "proceeds": erloes, "reportDate": tag, "description": f"{symbol}({isin}) {beschreibung} ({symbol}, {symbol} AG, {isin})",
            "transactionID": f"9{aid}{menge}", "levelOfDetail": "DETAIL"}


def erkennen_und_buchen(j, belege, positionen, buecher=("crossover", "momentum", "fundamental_a"), **kw):
    m: list[str] = []
    km.erkennen(j, list(buecher), flex_mit(belege), m, ticker_je_conid=kw.get("ticker_je_conid", {}))
    erg = km.buchen(j, list(buecher), positionen, m, fx=FX, jetzt=JETZT, **{"ticker_je_conid": {}, **kw})
    return erg, m


def technik_zustand(stop, atr, ticker="ABC.DE"):
    pos = {ticker: {"regel": "crossover", "signal_tag": "2026-09-30", "kauf_tag": "2026-10-01", "stop": stop, "atr_signal": atr}}
    return {"signaltag": "2026-10-30", "vor": {"positionen": dict(pos), "gesperrt": {}}, "nach": {"positionen": dict(pos), "gesperrt": {}},
            "vor_signaltag": "2026-10-29"}


def vorschlag(j, vid, buch, ticker, richtung, stueck, limit, status, signaltag="2026-11-01", stop=None):
    j.db.execute("INSERT INTO vorschlaege (id, erstellt, signaltag, buch, ticker, art, waehrung, richtung, stueck, limit_preis, "
                 "letzter_kurs_eur, stop, frei, status, freigabe_bis, order_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (vid, f"{signaltag}T20:00:00", signaltag, buch, ticker, "etf", "EUR", richtung, stueck, limit, limit / 1.02, stop, 1, status,
                  f"{signaltag}T23:59:59", "5" if status in ("gesendet", "ausgefuehrt") else None))
    j.db.commit()


# --- Split 2:1: Bestand, Einstand, Stop-Niveaus, keine Doppelbuchung --------------------------------------------------------
def test_split_bucht_bestand_einstand_und_teilt_kurseinheiten(j):
    kauf(j, "crossover", "ABC.DE", 10, preis=100.0)
    j.zustand_speichern("crossover", technik_zustand(90.0, 5.0))
    erg, m = erkennen_und_buchen(j, [zeile(-10), zeile(20)], [Position("DU1", "ABC.DE", 20, 50.0)])
    assert [b.ok for b in erg] == [True], m
    assert j.bestand("crossover") == {"ABC.DE": 20}
    e = j.einstaende("crossover")["ABC.DE"]
    assert e["s"] == 20 and e["w"] == pytest.approx(1000.0) and e["w"] / e["s"] == pytest.approx(50.0)
    z = j.zustand("crossover")
    for teil in ("vor", "nach"):
        p = z[teil]["positionen"]["ABC.DE"]
        assert p["stop"] == pytest.approx(45.0) and p["atr_signal"] == pytest.approx(2.5) and p["kauf_tag"] == "2026-10-01"
    # Risiko bis Stop bleibt gleich: 10 × (100 − 90) = 20 × (50 − 45); ohne Umrechnung riss Kurs 50 den alten Stop 90 (Fehlalarm)
    assert 20 * (50 - z["nach"]["positionen"]["ABC.DE"]["stop"]) == pytest.approx(10 * (100 - 90))
    ereignisse = [r["art"] for r in j.db.execute("SELECT art FROM ereignisse")]
    assert "kapitalmassnahme_gebucht" in ereignisse and "kurseinheiten" in ereignisse
    assert all(r["status"] == "gebucht" for r in j.massnahmen("beleg_id='CA:77'"))
    # zweiter Lauf mit demselben Beleg: nichts mehr (keine Doppelbuchung, keine zweite Umrechnung)
    assert km.buchen(j, ["crossover"], [Position("DU1", "ABC.DE", 20, 50.0)], [], fx=FX, ticker_je_conid={}) == []
    assert j.zustand("crossover")["nach"]["positionen"]["ABC.DE"]["stop"] == pytest.approx(45.0)


def test_einstand_gleitender_durchschnitt_nach_teilverkauf_und_split(j):
    kauf(j, "crossover", "ABC.DE", 15, preis=100.0)
    j.ausfuehrung("v1", "crossover:v1", "ABC.DE", -1, 5, 110.0, 1.25, "2026-10-15T09:00:00", waehrung="EUR", preis=110.0)
    erkennen_und_buchen(j, [zeile(-10), zeile(20)], [Position("DU1", "ABC.DE", 20, 50.0)])
    from tradingbot.betrieb.ansicht import _kaufkurse
    assert _kaufkurse(j, "crossover")["ABC.DE"]["kaufkurs"] == pytest.approx(50.0)      # nicht 1500 / 25 = 60


def test_zwei_buecher_verteilung_und_probe_gegen_ibkr(j):
    kauf(j, "crossover", "ABC.DE", 10)
    kauf(j, "momentum", "ABC.DE", 4)
    drei_zu_zwei = [zeile(7, beschreibung="SPLIT 3 FOR 2")]                  # eine Zeile mit der Änderung: 14 → 21
    erg, m = erkennen_und_buchen(j, drei_zu_zwei, [Position("DU1", "ABC.DE", 20, 50.0)])
    assert not erg[0].ok and "Probe gegen IBKR" in erg[0].text and j.bestand("crossover") == {"ABC.DE": 10}
    erg, _ = erkennen_und_buchen(j, drei_zu_zwei, [Position("DU1", "ABC.DE", 21, 50.0)])
    assert erg[0].ok and j.bestand("crossover") == {"ABC.DE": 15} and j.bestand("momentum") == {"ABC.DE": 6}


def test_verhaeltnis_aus_beschreibung_widerspricht_stueckzahlen(j):
    kauf(j, "crossover", "ABC.DE", 10)
    erg, m = erkennen_und_buchen(j, [zeile(5)], [Position("DU1", "ABC.DE", 15, 50.0)])
    assert not erg[0].ok and "Probe" in erg[0].text and j.bestand("crossover") == {"ABC.DE": 10}
    assert km.verhaeltnis("X SPLIT 1 FOR 10 (X)") == pytest.approx(0.1) and km.verhaeltnis("ISIN CHANGE") is None


def test_reverse_split_mit_spitze_barausgleich_und_anteiligem_einstand(j):
    kauf(j, "crossover", "ABC.DE", 25, preis=4.0)                              # Einstand 100 €
    belege = [zeile(-25, typ="RS", beschreibung="SPLIT 1 FOR 10"), zeile(2, typ="RS", beschreibung="SPLIT 1 FOR 10", erloes="20.00")]
    kasse = j.kasse("crossover")
    erg, m = erkennen_und_buchen(j, belege, [Position("DU1", "ABC.DE", 2, 40.0)])
    assert erg[0].ok, m
    assert j.bestand("crossover") == {"ABC.DE": 2}
    assert j.einstaende("crossover")["ABC.DE"]["w"] == pytest.approx(80.0)          # 100 · 2 / 2,5
    assert j.kasse("crossover") == pytest.approx(kasse + 20.0)
    assert "Barausgleich" in m[-1] and "Steuer zu prüfen" in m[-1]


def test_spitzen_ueber_zwei_buecher_nach_groesstem_rest(j):
    kauf(j, "crossover", "ABC.DE", 6, preis=4.0)
    kauf(j, "momentum", "ABC.DE", 6, preis=4.0)
    # 12 · 0,1 = 1,2 → IBKR 1 ganzes Stück, 0,2 Stück bar zu 40 € = 8 €; Gleichstand 0,6/0,6 → nach Buchname: crossover
    belege = [zeile(-12, typ="RS", beschreibung="SPLIT 1 FOR 10"), zeile(1, typ="RS", beschreibung="SPLIT 1 FOR 10", erloes="8.00")]
    k_c, k_m = j.kasse("crossover"), j.kasse("momentum")
    erg, m = erkennen_und_buchen(j, belege, [Position("DU1", "ABC.DE", 1, 40.0)])
    assert erg[0].ok, m
    assert j.bestand("crossover") == {"ABC.DE": 1} and j.bestand("momentum") == {}
    assert j.kasse("crossover") == pytest.approx(k_c - 16.0) and j.kasse("momentum") == pytest.approx(k_m + 24.0)
    assert j.einstaende("crossover")["ABC.DE"]["w"] == pytest.approx(24.0 + 16.0)   # 6 · 4 + zugekaufte Spitze 0,4 · 40
    assert km.verteilen({"a": 6, "b": 6}, 0.1, 1) == {"a": (1, pytest.approx(-0.4)), "b": (0, pytest.approx(0.6))}
    texte = [r["text"] for r in j.db.execute("SELECT text FROM ereignisse WHERE art='kapitalmassnahme_gebucht'")]
    assert len(texte) == 2 and all("größtem Rest" in t for t in texte)


def test_spitzenausgleich_ohne_barkurs_wird_nicht_gebucht(j):
    kauf(j, "crossover", "ABC.DE", 5)
    kauf(j, "momentum", "ABC.DE", 5)
    belege = [zeile(-10, typ="RS", beschreibung="SPLIT 1 FOR 10"), zeile(1, typ="RS", beschreibung="SPLIT 1 FOR 10")]
    erg, _ = erkennen_und_buchen(j, belege, [Position("DU1", "ABC.DE", 1, 40.0)])
    assert not erg[0].ok and "ohne Barausgleichskurs" in erg[0].text


def test_kein_buch_betroffen_nichts_zu_buchen(j):
    erg, m = erkennen_und_buchen(j, [zeile(10)], [])
    assert erg == [] and j.massnahmen("beleg_id='CA:77' AND buch='_konto'")[0]["status"] == "ohne_buch"


def test_buchung_ist_eine_transaktion(j):
    kauf(j, "crossover", "ABC.DE", 10)
    km.erkennen(j, ["crossover"], flex_mit([zeile(10)]), [], ticker_je_conid={})
    with pytest.raises(Exception):
        j.massnahme_buchen(beleg_id="CA:77", art="split", felder={}, posten_je_buch={"crossover": [{"ticker": "ABC.DE", "stueck": 10}]},
                           zustaende={"crossover": {"x": 1}}, vorschlaege=[("v", {"gibt_es_nicht": 1})], ereignisse=[])
    assert j.bestand("crossover") == {"ABC.DE": 10} and j.zustand("crossover") == {}
    assert [r["status"] for r in j.massnahmen("beleg_id='CA:77'")] == ["erkannt", "erkannt"]


# --- Kurseinheiten: vollständige Liste, nichts vergessen ----------------------------------------------------------------------
def test_kurseinheiten_vollstaendig(umgebung):
    """Jede Spalte des Journals und jedes Feld der gespeicherten Zustände ist in EINHEITEN eingeordnet (Entscheidung 3).
    Kommt ein neues Feld dazu, schlägt dieser Test fehl, bis es eingeordnet ist."""
    jj, rm = umgebung
    for tabelle in [r["name"] for r in jj.db.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        spalten = {r["name"] for r in jj.db.execute(f"PRAGMA table_info({tabelle})")}
        assert tabelle in km.EINHEITEN, f"Tabelle {tabelle} fehlt in EINHEITEN"
        assert spalten == set(km.EINHEITEN[tabelle]), f"{tabelle}: nicht eingeordnet {spalten - set(km.EINHEITEN[tabelle])}"
    assert {f.name for f in dataclasses.fields(TechnikPosition)} == set(km.EINHEITEN["technik_position"])
    # echte Zustände aus Tagesläufen (Technik, Fundamental, Konto mit Kassenabgleich, Buchstopps)
    lauf(jj, rm)
    kauf(jj, "crossover", "EUNK.DE", 10)
    start = sum(jj.kasse_je_waehrung(n)["EUR"] - jj.startkapital(n) for n in lade_konfiguration("betrieb")["buecher"])
    lauf(jj, rm, broker=KontoAttrappe({"EUR": 100_000.0 + start}, positionen=[Position("DU1", "EUNK.DE", 10, 25.0)]), flex=flex_mit())
    lauf(jj, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=[Position("DU1", "EUNK.DE", 20, 25.0)]), flex=flex_mit())
    from tradingbot.engines.technik.strategien import SatelliteStrategie
    from tradingbot.betrieb.buecher import zustand_speichern
    kt = lade_konfiguration("technik")
    k = {"EUNK.DE": kurse_attrappe()("EUNK.DE", "2026-11-02", "etf")}
    s = SatelliteStrategie(["crossover", "momentum"], k, kt)
    s.pos["EUNK.DE"] = TechnikPosition("crossover", pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-02"), 40.0, 1.5)
    gespeichert = zustand_speichern(s)
    assert set(gespeichert) <= set(km.EINHEITEN["technik_zustand"])
    assert set(gespeichert["positionen"]["EUNK.DE"]) == set(km.EINHEITEN["technik_position"])
    for buch in ("crossover", "momentum"):
        z = jj.zustand(buch)
        assert set(z) <= set(km.EINHEITEN["technik_lauf"]), z.keys()
        for teil in ("vor", "nach"):
            assert set(z[teil]) <= set(km.EINHEITEN["technik_zustand"])
            for p in z[teil].get("positionen", {}).values():
                assert set(p) <= set(km.EINHEITEN["technik_position"])
    for buch in ("fundamental_a", "fundamental_b"):
        assert set(jj.zustand(buch)) <= set(km.EINHEITEN["fundamental_zustand"]), jj.zustand(buch).keys()
    assert jj.zustand("_konto") and set(jj.zustand("_konto")) <= set(km.EINHEITEN["konto_zustand"]), jj.zustand("_konto").keys()
    stopps = buchstopp.gestoppt(jj)
    assert stopps and all(set(e) <= set(km.EINHEITEN["buchstopp_eintrag"]) for e in stopps.values())
    # Umrechnung folgt der Liste: Kurs ÷ r, Stück × r, alles andere unverändert
    vorschlag(jj, "v9", "crossover", "EUNK.DE", 1, 10, 102.0, "gesendet", stop=90.0)
    z = jj.db.execute("SELECT * FROM vorschlaege WHERE id='v9'").fetchone()
    werte = km.vorschlag_umrechnen(z, 2.0)
    assert werte == {"stueck": 20, "limit_preis": pytest.approx(51.0), "letzter_kurs_eur": pytest.approx(z["letzter_kurs_eur"] / 2),
                     "stop": pytest.approx(45.0)}
    assert set(werte) == {f for f, e in km.EINHEITEN["vorschlaege"].items() if e in ("kurs", "stueck")}


# --- Kursreihe nur im Speicher bereinigen ---------------------------------------------------------------------------------------
def _reihe(nach_split: np.ndarray, tage, r=2.0, sprung_ab=None, split_ereignis=False):
    """Yahoo-Reihe: `nach_split` = richtig bereinigte Schlusskurse; unbereinigt (sprung_ab) = davor × r."""
    c = nach_split.copy()
    if sprung_ab is not None:
        c[:sprung_ab] = c[:sprung_ab] * r
    df = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 100.0, "dividende": 0.0, "split": 0.0}, index=tage)
    if split_ereignis:
        df.iloc[sprung_ab if sprung_ab is not None else -1, df.columns.get_loc("split")] = r
    return df


def test_kursreihe_selbst_bereinigt_nur_im_speicher_und_nie_doppelt():
    from tradingbot.engines.technik.strategien import berechne_indikatoren

    tage = pd.bdate_range(end="2026-11-02", periods=300)
    richtig = 50 + np.sin(np.arange(300) / 10)
    roh = _reihe(richtig, tage, sprung_ab=299)                              # Yahoo noch unbereinigt: Sprung am 02.11.
    kopie = roh.copy()
    assert pruefe_tageskurse(roh, tage[-1].date(), 0.15)                  # ohne Beleg: Sprungbefund
    k, d = km.selbst_bereinigen(roh, 2.0, "2026-11-02")
    assert d == tage[-1] and pruefe_tageskurse(k, tage[-1].date(), 0.15) == []
    pd.testing.assert_frame_equal(roh, kopie)                              # Original (Cache) unverändert
    kt = lade_konfiguration("technik")
    a, b = berechne_indikatoren(k, kt), berechne_indikatoren(_reihe(richtig, tage), kt)
    pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-9)     # Indikatoren wie bei bereinigter Yahoo-Reihe
    k2, d2 = km.selbst_bereinigen(k, 2.0, "2026-11-02")                   # schon bereinigt → keine Doppelbereinigung
    assert d2 is None and k2 is k


def test_kurslader_bereinigt_titel_mit_beleg_und_meldet_einmal(j):
    kauf(j, "crossover", "ABC.DE", 10)
    km.erkennen(j, ["crossover"], flex_mit([zeile(-10), zeile(20)]), [], ticker_je_conid={})
    tage = pd.bdate_range(end="2026-11-02", periods=300)
    roh = _reihe(np.full(300, 50.0), tage, sprung_ab=299)
    meldungen: list[str] = []
    laden = km.kurse_mit_massnahmen(lambda t, bis, art: roh if t == "ABC.DE" else _reihe(np.full(300, 9.0), tage), j, meldungen)
    assert laden("ABC.DE", None, "etf")["close"].iloc[0] == pytest.approx(50.0)
    laden("ABC.DE", None, "etf")
    assert laden("XYZ.DE", None, "etf")["close"].iloc[0] == pytest.approx(9.0)
    assert len(meldungen) == 1 and "selbst bereinigt" in meldungen[0] and "Kurs-Cache unverändert" in meldungen[0]
    assert laden.roh("ABC.DE", None, "etf")["close"].iloc[0] == pytest.approx(100.0)


# --- Fundamental: Kurs und Kennzahlen je Aktie auf demselben Stand -------------------------------------------------------------
def test_kennzahlen_je_aktie_passend():
    tage = pd.bdate_range(end="2026-11-02", periods=50)
    richtig = np.full(50, 80.0)
    assert km.kennzahlen_je_aktie_passend(_reihe(richtig, tage, sprung_ab=49), 2.0, "2026-11-02")[0] is False     # unbereinigt
    ok, grund = km.kennzahlen_je_aktie_passend(_reihe(richtig, tage), 2.0, "2026-11-02")                          # ohne Ereignis
    assert not ok and "nicht als Ereignis" in grund
    assert km.kennzahlen_je_aktie_passend(_reihe(richtig, tage, sprung_ab=49, split_ereignis=True) * 1, 2.0, "2026-11-02")[0] is False
    bereinigt = _reihe(richtig, tage)
    bereinigt.iloc[-1, bereinigt.columns.get_loc("split")] = 2.0
    assert km.kennzahlen_je_aktie_passend(bereinigt, 2.0, "2026-11-02") == (True, "Yahoo führt den Split 2")


def test_fundamental_buch_bleibt_gestoppt_bis_kennzahlen_passen(umgebung):
    jj, rm = umgebung
    lauf(jj, rm)
    kauf(jj, "fundamental_a", "US1", 10, preis=80.0)
    fs = [zeile(-10, conid="555", symbol="US1", waehrung="USD", isin="US0005"), zeile(20, conid="555", symbol="US1", waehrung="USD", isin="US0005")]
    pos = [Position("DU1", "US1", 20, 40.0)]
    e = lauf(jj, rm, broker=BrokerAttrappe(positionen=pos), flex=flex_mit(fs))         # Yahoo-Attrappe: kein Split-Ereignis
    assert jj.bestand("fundamental_a") == {"US1": 20}                                  # gebucht
    assert set(e.buchstopps) == {"fundamental_a"}
    assert any("Kennzahlen je Aktie nicht auf demselben Stand" in d for d in e.buchstopps["fundamental_a"]["details"])
    assert not any(bv.vorschlag.buch == "fundamental_a" for bv, _ in e.vorschlaege)

    attrappe = kurse_attrappe()

    def mit_ereignis(ticker, bis, art):
        k = attrappe(ticker, bis, art)
        if ticker == "US1":
            k = k.copy()
            k.iloc[-1, k.columns.get_loc("split")] = 2.0
        return k
    e = lauf(jj, rm, jetzt=NAECHSTER, broker=BrokerAttrappe(positionen=pos), flex=flex_mit(fs), kurse=mit_ereignis)
    assert e.buchstopps == {} and any(s.startswith("Stopp aufgehoben: Buch fundamental_a") for s in e.sofort)
    assert jj.zustand("_konto")["kennzahlen_passend"] == ["CA:77"]


# --- Order über den Stichtag ---------------------------------------------------------------------------------------------------
def test_order_unterwegs_ueber_stichtag_umgerechnet_und_stopp_bis_abgeschlossen(j):
    kauf(j, "crossover", "ABC.DE", 10)
    vorschlag(j, "k1", "crossover", "ABC.DE", 1, 4, 102.0, "gesendet")                 # Kauf 4 Stück, Limit 102, vor dem Stichtag
    vorschlag(j, "k2", "momentum", "ABC.DE", 1, 3, 102.0, "vorgeschlagen")
    vorschlag(j, "k3", "momentum", "ABC.DE", 1, 3, 51.0, "vorgeschlagen", signaltag="2026-11-02")   # schon in neuen Einheiten
    erg, m = erkennen_und_buchen(j, [zeile(-10), zeile(20)], [Position("DU1", "ABC.DE", 20, 50.0)])
    assert erg[0].ok, m
    z = {r["id"]: r for r in j.db.execute("SELECT * FROM vorschlaege")}
    assert (z["k1"]["stueck"], z["k1"]["limit_preis"]) == (8, pytest.approx(51.0))
    assert (z["k2"]["stueck"], z["k2"]["limit_preis"]) == (6, pytest.approx(51.0))
    assert (z["k3"]["stueck"], z["k3"]["limit_preis"]) == (3, pytest.approx(51.0))
    assert j.reserviert("crossover")["EUR"] == pytest.approx(4 * 102.0 * 1.01)        # Stück × Limit bleibt gleich
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='order_an_split_angepasst'").fetchone()[0] == 1
    st = buchstopp.gestoppt(j)["crossover"]
    assert "CA:77" in st["belege"] and any("über den Stichtag unterwegs" in d for d in st["details"])
    zeilen, _ = buchstopp.aktualisieren(j, {}, JETZT)                                  # Abgleich sauber, Order noch unterwegs
    assert "crossover" in buchstopp.gestoppt(j) and any("Order unterwegs" in x for x in zeilen)
    j.status_setzen("k1", "verfallen")
    _, sofort = buchstopp.aktualisieren(j, {}, JETZT)
    assert buchstopp.gestoppt(j) == {} and any(s.startswith("Stopp aufgehoben: Buch crossover") for s in sofort)


def test_order_ueber_stichtag_unveraendert_ausgefuehrt_braucht_quittung(j):
    kauf(j, "crossover", "ABC.DE", 30)
    vorschlag(j, "s1", "crossover", "ABC.DE", -1, 10, 95.0, "gesendet")
    j.ausfuehrung("e1", "crossover:s1", "ABC.DE", -1, 10, 50.0, 1.25, "2026-11-02T09:05:00", waehrung="EUR", preis=50.0)   # 10 statt 20
    erg, m = erkennen_und_buchen(j, [zeile(-30), zeile(60)], [Position("DU1", "ABC.DE", 50, 50.0)])
    assert erg[0].ok, m
    assert j.bestand("crossover") == {"ABC.DE": 50}
    st = buchstopp.gestoppt(j)["crossover"]
    assert "10 Stück statt 20" in st["quittung_noetig"] and "quittieren" in st["quittung_noetig"]
    assert "Quittung in der Oberfläche nötig" in buchstopp.kurz("crossover", st) and "Stück" not in buchstopp.kurz("crossover", st)
    _, sofort = buchstopp.aktualisieren(j, {}, JETZT)
    assert "crossover" in buchstopp.gestoppt(j) and buchstopp.gestoppt(j)["crossover"]["abweichung_weg"]
    assert "quittiert von Jakob" in buchstopp.quittieren(j, "crossover", JETZT)


def test_order_ueber_stichtag_von_ibkr_angepasst_hebt_auf(j):
    kauf(j, "crossover", "ABC.DE", 30)
    vorschlag(j, "s1", "crossover", "ABC.DE", -1, 10, 95.0, "gesendet")
    j.ausfuehrung("e1", "crossover:s1", "ABC.DE", -1, 20, 50.0, 1.25, "2026-11-02T09:05:00", waehrung="EUR", preis=50.0)
    buchstopp.aktualisieren(j, {"crossover": {"titel": {"ABC.DE"}, "belege": set(), "details": ["ABC.DE: Bücher 10, IBKR 40"]}}, JETZT)
    erg, m = erkennen_und_buchen(j, [zeile(-30), zeile(60)], [Position("DU1", "ABC.DE", 40, 50.0)])
    assert erg[0].ok and any("von IBKR angepasst ausgeführt (20 Stück)" in x for x in m), m
    _, sofort = buchstopp.aktualisieren(j, {}, JETZT)
    assert buchstopp.gestoppt(j) == {} and any(s.startswith("Stopp aufgehoben") for s in sofort)


def test_negativer_bestand_stoppt_das_buch(j):
    j.ausfuehrung("e1", "crossover:s1", "ABC.DE", -1, 5, 50.0, 1.25, "2026-11-02T09:05:00", waehrung="EUR", preis=50.0)
    diff, je_buch = buchstopp.zuordnen(j, ["crossover", "momentum"], [Position("DU1", "ABC.DE", -5, 50.0)], offen=[])
    assert diff == [] and set(je_buch) == {"crossover"} and "negativer Bestand" in je_buch["crossover"]["details"][0]


# --- Tickerwechsel ---------------------------------------------------------------------------------------------------------------
IC = [zeile(-5, typ="IC", aid="88", conid="222", symbol="ALT", beschreibung="ISIN CHANGE", isin="DE0002"),
      zeile(5, typ="IC", aid="88", conid="333", symbol="NEU", beschreibung="ISIN CHANGE", isin="DE0003")]


def test_tickerwechsel_erst_nach_kontrakte_yaml_dann_umgebucht(j):
    kauf(j, "crossover", "ALT.DE", 5, preis=30.0)
    j.zustand_speichern("crossover", technik_zustand(27.0, 1.0, ticker="ALT.DE"))
    j.zustand_speichern("fundamental_a", {"letzter_signaltag": "2026-10-01", "ziel": {"ALT.DE": 0.05}, "rang": {"ALT.DE": 3}})
    vorschlag(j, "f1", "crossover", "ALT.DE", 1, 2, 31.0, "vorgeschlagen")
    pos = [Position("DU1", "NEU.DE", 5, 30.0)]
    erg, m = erkennen_und_buchen(j, IC, pos)
    assert not erg[0].ok and "config/kontrakte.yaml" in erg[0].text and j.bestand("crossover") == {"ALT.DE": 5}
    # Jakob hat kontrakte.yaml umgestellt; ALT.DE steht im Technik-Universum, NEU.DE noch nicht → warten
    erg = km.buchen(j, ["crossover"], pos, [], fx=FX, ticker_je_conid={333: "NEU.DE"}, technik_universum={"ALT.DE"})
    assert not erg[0].ok and "config/technik.yaml" in erg[0].text
    erg = km.buchen(j, ["crossover", "fundamental_a"], pos, [], fx=FX, ticker_je_conid={333: "NEU.DE"},
                    technik_universum={"ALT.DE", "NEU.DE"})
    assert erg[0].ok and j.bestand("crossover") == {"NEU.DE": 5}
    assert j.einstaende("crossover")["NEU.DE"]["w"] == pytest.approx(150.0)
    z = j.zustand("crossover")["nach"]["positionen"]
    assert "ALT.DE" not in z and z["NEU.DE"]["stop"] == pytest.approx(27.0)              # r = 1: Stop unverändert
    assert j.zustand("fundamental_a")["ziel"] == {"NEU.DE": 0.05}
    assert j.db.execute("SELECT status FROM vorschlaege WHERE id='f1'").fetchone()[0] == "ersetzt"


# --- Split ohne Yahoo-Ereignis (SPYI-Fall): Verhältnis aus Flex nach Quittung (Jakob 12.11.2026) ------------------------------
def _fundamental_split_gebucht(j):
    kauf(j, "fundamental_a", "US1", 10, preis=80.0)
    fs = [zeile(-10, conid="555", symbol="US1", waehrung="USD", isin="US0005"), zeile(20, conid="555", symbol="US1", waehrung="USD", isin="US0005")]
    erg, m = erkennen_und_buchen(j, fs, [Position("DU1", "US1", 20, 40.0)])
    assert erg[0].ok, m
    tage = pd.bdate_range(end="2026-11-20", periods=60)
    return lambda t, bis, art: _reihe(np.full(60, 40.0), tage)            # bereinigt, aber ohne Split-Ereignis


def _nach_handelstagen(start: str, n: int):
    from tradingbot.betrieb.dividenden import handelstage_nach
    d = pd.Timestamp(start).date()
    while handelstage_nach(start, d) < n:
        d += pd.Timedelta(days=1)
    return d


def test_split_ohne_yahoo_ereignis_vorschlag_nach_5_handelstagen_und_quittung(j):
    kurse = _fundamental_split_gebucht(j)
    erkannt = j.massnahmen("beleg_id='CA:77' AND buch='_konto'")[0]["erkannt"][:10]
    je_buch: dict = {}
    z = km.kennzahlen_pruefen(j, ["fundamental_a"], kurse, je_buch, "2026-11-20", _nach_handelstagen(erkannt, 4))
    assert z == [] and set(je_buch) == {"fundamental_a"} and km.flex_split_offen(j) == {}
    buchstopp.aktualisieren(j, je_buch, JETZT)
    je_buch = {}
    z = km.kennzahlen_pruefen(j, ["fundamental_a"], kurse, je_buch, "2026-11-20", _nach_handelstagen(erkannt, 5))
    assert len(z) == 1 and "Quelle: Flex" in z[0] and "Quittung" in z[0]
    assert "fundamental_a" in je_buch and "wartet auf Quittung" in je_buch["fundamental_a"]["details"][0]   # gilt noch nicht
    assert set(km.flex_split_offen(j, "fundamental_a")) == {"CA:77"} and km.flex_splits_je_symbol(j) == {}
    # zweiter Lauf: kein zweiter Vorschlag
    assert km.kennzahlen_pruefen(j, ["fundamental_a"], kurse, {}, "2026-11-20", _nach_handelstagen(erkannt, 6)) == []
    text = km.flex_split_quittieren(j, "CA:77", datetime(2026, 11, 20, 19, 1, 2))
    assert "quittiert von Jakob am 20.11.2026 19:01:02" in text and "Stopp aufgehoben: fundamental_a" in text
    assert buchstopp.gestoppt(j) == {} and km.flex_splits_je_symbol(j) == {"US1": [("2026-11-02", 2.0)]}
    assert j.db.execute("SELECT zeit FROM ereignisse WHERE art='flex_split_quittiert'").fetchone()[0] == "2026-11-20T19:01:02"
    je_buch = {}
    km.kennzahlen_pruefen(j, ["fundamental_a"], kurse, je_buch, "2026-11-20", _nach_handelstagen(erkannt, 7))
    assert je_buch == {}
    with pytest.raises(ValueError, match="kein offener Vorschlag"):
        km.flex_split_quittieren(j, "CA:77")


def test_kein_flex_vorschlag_solange_yahoo_reihe_unbereinigt(j):
    _fundamental_split_gebucht(j)
    tage = pd.bdate_range(end="2026-11-20", periods=60)
    sprung = int(np.searchsorted(tage, pd.Timestamp("2026-11-02")))
    roh = lambda t, bis, art: _reihe(np.full(60, 40.0), tage, sprung_ab=sprung)       # noqa: E731
    erkannt = j.massnahmen("beleg_id='CA:77' AND buch='_konto'")[0]["erkannt"][:10]
    je_buch: dict = {}
    assert km.kennzahlen_pruefen(j, ["fundamental_a"], roh, je_buch, "2026-11-20", _nach_handelstagen(erkannt, 10)) == []
    assert "fundamental_a" in je_buch and km.flex_split_offen(j) == {}


def test_split_ereignis_aus_flex_fuer_die_aktienzahl():
    from tradingbot.daten.index_nachbau import aktien_splitbereinigt
    from tradingbot.engines.fundamental.aktuell import split_ereignisse_ergaenzen

    tage = pd.bdate_range("2026-10-26", "2026-11-06")
    k = _reihe(np.full(len(tage), 40.0), tage)
    neu = split_ereignisse_ergaenzen(k, [("2026-11-01", 2.0)])                       # Sonntag → erster Handelstag danach
    assert neu.loc["2026-11-02", "split"] == 2.0 and k["split"].sum() == 0              # Original unverändert
    aktien = pd.Series([1000.0], index=[pd.Timestamp("2026-10-15")])
    assert aktien_splitbereinigt(aktien, neu["split"]).iloc[0] == 2000.0
    yahoo = k.copy()
    yahoo.loc["2026-11-03", "split"] = 2.0
    assert split_ereignisse_ergaenzen(yahoo, [("2026-11-03", 2.0)])["split"].sum() == 2.0   # Yahoo-Ereignis bleibt, nicht doppelt
