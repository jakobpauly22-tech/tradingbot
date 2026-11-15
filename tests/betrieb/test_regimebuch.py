"""Schattenbuch regime im Betrieb (betrieb/regimebuch.py; docs/REGIME.md, Abschnitt 9): Bewertungstag, Protokoll,
Haltepflicht, Nachholen, geänderte Historie, Ausfall der Makrodaten, Orders mit Kauf- und Verkaufslimit, zwei Bücher mit
SPYI.DE, Festlegung b628678."""
import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from tradingbot.betrieb import regimebuch
from tradingbot.betrieb.speicher import BetriebsbereichGesperrt
from tradingbot.betrieb.tageslauf import freigeben_und_senden
from tradingbot.broker.basis import Auftrag, Position, SendenGesperrt, pruefe_senden, verkaufslimit_abschlag
from tradingbot.engines.regime import signale
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration
from tradingbot.risiko.manager import Kontext, OrderVorschlag

from test_tageslauf import ABEND, BrokerAttrappe, betrieb_mit, kurse_attrappe, lauf, umgebung  # noqa: F401

BERLIN = ZoneInfo("Europe/Berlin")
MIT_REGIME = betrieb_mit(True, ("real", "crossover", "regime"))


def abend(jahr, monat, tag):
    return datetime(jahr, monat, tag, 23, 30, tzinfo=BERLIN)


def kursreihe(bis, fallend_ab=None, steigend_ab=None) -> pd.Series:
    """Tagesschlusskurse ab 2012: steigend (Trend an); ab `fallend_ab` fallend (Trend aus), ab `steigend_ab` wieder steigend."""
    tage = pd.bdate_range("2012-01-02", bis)
    r = np.full(len(tage), 0.0004)
    if fallend_ab is not None:
        r[tage >= pd.Timestamp(fallend_ab)] = -0.004
    if steigend_ab is not None:
        r[tage >= pd.Timestamp(steigend_ab)] = 0.006
    return pd.Series(100 * np.cumprod(1 + r), index=tage)


class Makro:
    """Makrostand-Attrappe: Zinskurve immer invers (aus), Kreditaufschlag und Arbeitsmarkt ruhig (an). V1 folgt damit dem
    Trend. Merkt sich die abgefragten Stichtage und zählt die Ladevorgänge."""

    def __init__(self, ausfall=False):
        self.ausfall, self.geladen, self.stichtage = ausfall, 0, []

    def laden(self):
        if self.ausfall:
            raise ConnectionError("FRED nicht erreichbar")
        self.geladen += 1
        return self.stand

    def stand(self, reihe, stichtag):
        self.stichtage.append(pd.Timestamp(stichtag))
        if reihe == "UNRATE":
            monate = pd.date_range("2010-01-01", pd.Timestamp(stichtag) - pd.Timedelta(days=35), freq="MS")
            return pd.Series(4.0, index=monate)
        tage = pd.bdate_range("2010-01-01", pd.Timestamp(stichtag) - pd.Timedelta(days=1))
        return pd.Series(-0.5 if reihe == "T10Y3M" else 2.0, index=tage)


def daten(schluss, makro):
    return lambda tag, ticker: (schluss.loc[: pd.Timestamp(tag)], makro.laden)


# --- Bewertungstag -------------------------------------------------------------------------------------------------------
def test_bewertungstag_ist_der_letzte_xetra_handelstag_des_monats():
    assert regimebuch.ist_monatsende("2026-11-30") and not regimebuch.ist_monatsende("2026-11-27")
    assert regimebuch.ist_monatsende("2026-12-30") and not regimebuch.ist_monatsende("2026-12-29")     # 31.12. ist Xetra-Feiertag
    assert regimebuch.ist_monatsende("2029-03-29") and not regimebuch.ist_monatsende("2029-03-28")     # Karfreitag 30.03.2029
    assert regimebuch.ist_monatsende("2026-10-30")                                                       # 31.10. ist ein Samstag
    assert regimebuch.naechste_bewertung("2026-11-16") == pd.Timestamp("2026-11-30")
    assert regimebuch.naechste_bewertung("2026-11-30") == pd.Timestamp("2026-12-30")


# --- Bewertung, Protokoll, Haltepflicht ------------------------------------------------------------------------------------
def test_start_protokolliert_die_vorgeschichte_und_setzt_den_zustand():
    m = Makro()
    z, s = regimebuch.bewerten("2026-11-16", kursreihe("2026-11-16"), m.laden, {})
    assert s.start and s.risiko_aus is False and s.monat == "2026-10" and not s.neu and not s.wechsel and not s.laut
    assert min(z["protokoll"]) == "2012-10" and max(z["protokoll"]) == "2026-10"          # erste Bewertung wie im Backtest
    e = z["protokoll"]["2026-10"]
    assert e == {"monatsende": "2026-10-30", "trend_aus": False, "kurve_aus": True, "kredit_aus": False, "arbeit_aus": False,
                 "roh_aus": False, "risiko_aus": False, "bewertet_am": "2026-11-16", "art": "start"}
    assert z["festlegung"] == "b628678" and z["variante"] == "V1"
    assert any("Start" in x and "Risiko an" in x for x in s.meldungen)


def test_zustand_stimmt_mit_dem_eingefrorenen_verlauf_ueberein():
    """Das Protokoll trägt denselben Zustand wie `regime_verlauf` (Backtest-Rechnung), auch mit Haltepflicht."""
    c = kursreihe("2026-11-16", fallend_ab="2026-08-15", steigend_ab="2026-10-05")
    z, s = regimebuch.bewerten("2026-11-16", c, Makro().laden, {})
    v = signale.regime_verlauf(c, Makro().stand, letzter_monat_abgeschlossen=False)
    v = v[v["roh_aus"].notna()]
    assert [e["risiko_aus"] for _, e in sorted(z["protokoll"].items())] == [bool(x) for x in v["risiko_aus"]]
    assert s.risiko_aus is bool(v["risiko_aus"].iloc[-1])


def test_ohne_faellige_bewertung_werden_keine_makrodaten_geladen():
    m = Makro()
    z, _ = regimebuch.bewerten("2026-11-16", kursreihe("2026-11-16"), m.laden, {})
    assert m.geladen == 1
    z2, s = regimebuch.bewerten("2026-11-27", kursreihe("2026-11-27"), m.laden, z)       # mitten im Monat
    assert m.geladen == 1 and z2 == z and s.risiko_aus is False and not s.start and not s.neu
    z3, _ = regimebuch.bewerten("2026-11-16", kursreihe("2026-11-16"), m.laden, z)       # wiederholter Lauf am selben Tag
    assert m.geladen == 1 and z3 == z


def test_monatsbewertung_wechsel_und_haltepflicht():
    m = Makro()
    c = kursreihe("2027-02-26", fallend_ab="2026-11-02", steigend_ab="2026-12-01")
    z, s = regimebuch.bewerten("2026-11-16", c.loc[:"2026-11-16"], m.laden, {})
    assert s.risiko_aus is False
    z, s = regimebuch.bewerten("2026-11-30", c.loc[:"2026-11-30"], m.laden, z)           # Trend bricht: Wechsel auf Risiko aus
    assert s.neu == ["2026-11"] and s.wechsel and s.risiko_aus is True and z["protokoll"]["2026-11"]["art"] == "bewertung"
    assert any("Wechsel auf Risiko aus" in x for x in s.laut) and any("Monatsbewertung 2026-11" in x for x in s.meldungen)
    z, s = regimebuch.bewerten("2026-12-30", c.loc[:"2026-12-30"], m.laden, z)           # Rohzustand an, aber Haltepflicht
    e = z["protokoll"]["2026-12"]
    assert e["roh_aus"] is False and e["risiko_aus"] is True and not s.wechsel and s.risiko_aus is True and not s.laut
    z, s = regimebuch.bewerten("2027-01-29", c.loc[:"2027-01-29"], m.laden, z)           # zwei Monate nach dem Wechsel: zurück
    assert s.wechsel and s.risiko_aus is False and any("Wechsel auf Risiko an" in x for x in s.laut)


def test_verpasster_abend_wird_mit_dem_damaligen_wissensstand_nachgeholt():
    m = Makro()
    c = kursreihe("2026-12-03", fallend_ab="2026-11-02")
    z, _ = regimebuch.bewerten("2026-11-16", c.loc[:"2026-11-16"], m.laden, {})
    m.stichtage.clear()
    z, s = regimebuch.bewerten("2026-12-03", c, m.laden, z)                              # kein Lauf am 30.11., 01.12., 02.12.
    assert s.neu == ["2026-11"] and z["protokoll"]["2026-11"]["art"] == "nachgeholt" and s.risiko_aus is True and s.wechsel
    assert z["protokoll"]["2026-11"]["monatsende"] == "2026-11-30" and "2026-12" not in z["protokoll"]
    assert max(m.stichtage) == pd.Timestamp("2026-11-30")                                 # nichts mit späterem Wissensstand
    assert any("nachgeholt am 03.12.2026" in x and "30.11.2026" in x for x in s.meldungen)


def test_geaenderte_historie_das_protokoll_gilt_und_wird_einmal_laut_gemeldet():
    m = Makro()
    c = kursreihe("2026-12-30")
    z, _ = regimebuch.bewerten("2026-11-16", c.loc[:"2026-11-16"], m.laden, {})
    geaendert = c.copy()
    geaendert.loc["2026-08-20":"2026-10-30"] *= 0.5                                       # „Yahoo“ ändert alte Kurse: Trend wäre aus
    z2, s = regimebuch.bewerten("2026-11-30", geaendert.loc[:"2026-11-30"], m.laden, z)
    assert any("weicht vom Protokoll ab" in x and "2026-10" in x and "das Protokoll gilt" in x for x in s.laut)
    assert {k: v for k, v in z2["protokoll"].items() if k <= "2026-10"} == z["protokoll"]  # nichts still übernommen
    assert z2["protokoll"]["2026-10"]["risiko_aus"] is False and s.neu == ["2026-11"]
    z3, s3 = regimebuch.bewerten("2026-12-30", geaendert, m.laden, z2)                    # dieselbe Abweichung nicht noch einmal
    assert not any("2026-10" in x for x in s3.laut) and len(z3["abweichungen_gemeldet"]) == len(z2["abweichungen_gemeldet"])


def test_luecke_oder_fehlendes_signal_bricht_laut_ab():
    z, _ = regimebuch.bewerten("2026-11-16", kursreihe("2026-11-16"), Makro().laden, {})
    ohne_kurve = Makro()
    # Zinskurve ohne Werte im Bewertungsmonat (Stand zwei Monate alt): kein Rohzustand → laut, nichts protokolliert
    ohne_kurve.stand = lambda reihe, stichtag: Makro().stand(reihe, pd.Timestamp(stichtag) - pd.Timedelta(days=60 if reihe == "T10Y3M" else 0))
    with pytest.raises(ValueError):
        regimebuch.bewerten("2026-11-30", kursreihe("2026-11-30"), ohne_kurve.laden, z)


# --- Orders ----------------------------------------------------------------------------------------------------------------
def _stand(aus):
    e = {"monatsende": "2026-10-30", "trend_aus": aus, "kurve_aus": True, "kredit_aus": False, "arbeit_aus": False, "roh_aus": aus, "risiko_aus": aus}
    return regimebuch.Stand(risiko_aus=aus, monat="2026-10", eintrag=e)


def _gebuehr(n, wert):
    return max(1.25, 0.0005 * wert)


def test_kauf_bei_risiko_an_in_ganzen_stuecken_mit_limit():
    v = regimebuch.vorschlaege(pd.Timestamp("2026-11-16"), "SPYI.DE", 250.0, _stand(False), 0, 10_000.0, 0.02, 0.02, _gebuehr)
    assert len(v) == 1
    o = v[0].vorschlag
    assert (o.buch, o.ticker, o.richtung, o.art) == ("regime", "SPYI.DE", 1, "etf") and v[0].limit_order == 255.0 and o.stueck == 39
    assert o.stueck * 255.0 + _gebuehr(o.stueck, o.stueck * 255.0) <= 10_000.0 < (o.stueck + 1) * 255.0
    assert "Risiko an" in v[0].kern and "nicht bestanden" in v[0].details and "Was dagegen spricht" in v[0].details
    assert regimebuch.vorschlaege(pd.Timestamp("2026-11-16"), "SPYI.DE", 250.0, _stand(False), 39, 55.0, 0.02, 0.02, _gebuehr) == []   # investiert


def test_verkauf_bei_risiko_aus_mit_limit_zwei_prozent_unter_dem_schluss():
    v = regimebuch.vorschlaege(pd.Timestamp("2026-11-30"), "SPYI.DE", 251.37, _stand(True), 39, 55.0, 0.02, 0.02, _gebuehr)
    assert len(v) == 1
    o = v[0].vorschlag
    assert (o.richtung, o.stueck) == (-1, 39) and v[0].limit_order == o.limit == 246.35             # 251,37 · 0,98 = 246,3426 → aufgerundet
    assert o.limit >= 251.37 * 0.98 and "Risiko aus" in v[0].kern and "nicht bestanden" in v[0].details
    assert regimebuch.limit_verkauf(250.0, 0.02) == 245.0
    assert regimebuch.vorschlaege(pd.Timestamp("2026-11-30"), "SPYI.DE", 251.37, _stand(True), 0, 10_000.0, 0.02, 0.02, _gebuehr) == []  # schon in Kasse
    assert regimebuch.vorschlaege(pd.Timestamp("2026-11-30"), "SPYI.DE", 251.37, regimebuch.Stand(), 0, 10_000.0, 0.02, 0.02, _gebuehr) == []  # kein Zustand


# --- Risk-Manager und Senderiegel: Verkaufslimit nur im Buch regime -------------------------------------------------------
def test_verkaufslimit_ist_eine_einstellung_des_buchs():
    b = lade_konfiguration("betrieb")
    assert verkaufslimit_abschlag(b, "regime") == 0.02
    assert all(verkaufslimit_abschlag(b, n) is None for n in b["buecher"] if n != "regime")
    r = b["buecher"]["regime"]
    assert (r["art"], r["budget_eur"], r["freigabe"], r["rolle"], r["instrument"]) == ("skalierung", 10000.0, "sammel", "core", "SPYI.DE")
    assert r["senden_freigeschaltet"] is False                                    # Jakob schaltet nach dem Probelauf frei


def test_risk_manager_verkauf_im_regime_nur_mit_limit_hoechstens_zwei_prozent(umgebung):
    _, rm = umgebung
    k = Kontext(buch="regime", kasse=50.0, wert=10_000.0, bestand={"SPYI.DE": 39})

    def verkauf(limit, buch="regime"):
        return OrderVorschlag("x", pd.Timestamp("2026-11-30"), buch, "SPYI.DE", -1, 39, 250.0, "etf", limit=limit)

    assert rm.pruefe(verkauf(245.0), k).frei
    assert any("ohne Limit" in g for g in rm.pruefe(verkauf(None), k).gruende)
    assert any("2 % unter" in g for g in rm.pruefe(verkauf(244.99), k).gruende)
    k_real = Kontext(buch="real", kasse=50.0, wert=10_000.0, bestand={"SPYI.DE": 39})
    assert any("Verkäufe ohne Limit" in g for g in rm.pruefe(verkauf(245.0, "real"), k_real).gruende)   # übrige Bücher unverändert


def test_senderiegel_verkauf_mit_limit_nur_im_regime(tmp_path):
    def pruefe(auftrag):
        pruefe_senden(konto_id="DU1", port=4002, modus="paper", betrieb=MIT_REGIME, projekt_wurzel=tmp_path, auftrag=auftrag,
                      offene=[], gesendete_refs=set())

    pruefe(Auftrag("regime", "v1", "SPYI.DE", -1, 39, 245.0))
    with pytest.raises(SendenGesperrt, match="ohne Limit"):
        pruefe(Auftrag("regime", "v2", "SPYI.DE", -1, 39, None))
    with pytest.raises(SendenGesperrt, match="Verkauf mit Limit"):
        pruefe(Auftrag("crossover", "v3", "SXR1.DE", -1, 5, 245.0))
    pruefe(Auftrag("crossover", "v4", "SXR1.DE", -1, 5, None))


# --- Tageslauf ----------------------------------------------------------------------------------------------------------------
def _regime(e):
    return [(bv, u) for bv, u in e.vorschlaege if bv.vorschlag.buch == "regime"]


def _fill(z, preis, zeit, nr="r1"):
    return {"exec_id": nr, "order_ref": f"regime:{z['id']}", "ticker": "SPYI.DE", "richtung": z["richtung"], "stueck": z["stueck"], "preis": preis,
            "waehrung": "EUR", "gebuehr": 3.0, "gebuehr_waehrung": "EUR", "zeit": zeit}


def test_tageslauf_start_kauf_dann_wechsel_verkauf_mit_limit_und_wiederholung(umgebung):
    j, rm = umgebung
    m, k = Makro(), kurse_attrappe()
    c = kursreihe("2026-12-02", fallend_ab="2026-11-10")
    # 16.11.: Start, Risiko an → Kauf mit Limit; das Buch ist in der echten Konfiguration nicht freigebbar
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, m))
    (bv, u), = _regime(e)
    assert u.frei and bv.vorschlag.richtung == 1 and bv.limit_order and e.regime["risiko_aus"] is False and e.regime["start"]
    assert e.regime["naechste_bewertung"] == pd.Timestamp("2026-11-30") and not any("regime" in s for s in e.sofort)
    assert any("nicht freigeschaltet" in x for x in freigeben_und_senden(j, [bv.vorschlag.id], BrokerAttrappe(), abend(2026, 11, 16), risk=rm,
                                                                         kurse_laden=k))
    b = BrokerAttrappe()
    freigeben_und_senden(j, [bv.vorschlag.id], b, abend(2026, 11, 16), risk=rm, kurse_laden=k, konfig_betrieb=MIT_REGIME)
    assert [(a.buch, a.richtung, a.limit) for a in b.gesendet] == [("regime", 1, bv.limit_order)]
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, m))               # Order unterwegs: kein zweiter Vorschlag
    assert _regime(e) == [] and any("unterwegs" in x for x in e.meldungen if x.startswith("regime"))
    kauf = j.vorschlaege(buch="regime")[0]
    n = kauf["stueck"]
    pos = [Position("DU1", "SPYI.DE", n, 150.0)]
    e = lauf(j, rm, jetzt=abend(2026, 11, 17), regime_daten=daten(c, m), broker=BrokerAttrappe(fills=[_fill(kauf, 150.0, "2026-11-17T09:00")], positionen=pos))
    assert e.gestoppt is None and j.bestand("regime") == {"SPYI.DE": n} and _regime(e) == [] and m.geladen == 1
    # 30.11.: Monatsbewertung, Wechsel auf Risiko aus → Verkauf des ganzen Bestands mit Limit, Sofortmeldung
    e = lauf(j, rm, jetzt=abend(2026, 11, 30), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=pos))
    (bv, u), = _regime(e)
    kurs = e.kurse_eur["SPYI.DE"]
    assert u.frei and bv.vorschlag.richtung == -1 and bv.vorschlag.stueck == n and e.regime["wechsel"] and m.geladen == 2
    assert kurs * 0.98 <= bv.limit_order <= kurs * 0.98 + 0.05 + 1e-9                     # −2 %, auf die Kursstufe aufgerundet
    assert any("Wechsel auf Risiko aus" in s for s in e.sofort)
    assert j.db.execute("SELECT COUNT(*) FROM ereignisse WHERE art='regime_bewertung'").fetchone()[0] == 1
    b = BrokerAttrappe(positionen=pos)
    freigeben_und_senden(j, [bv.vorschlag.id], b, abend(2026, 11, 30), risk=rm, kurse_laden=k, konfig_betrieb=MIT_REGIME)
    assert [(a.buch, a.richtung, a.limit) for a in b.gesendet] == [("regime", -1, bv.limit_order)]
    # 01.12.: Limit nicht erreicht, Order verfallen → am nächsten Abend derselbe Verkauf erneut, ohne neue Bewertung
    e = lauf(j, rm, jetzt=abend(2026, 12, 1), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=pos))
    (bv2, u2), = _regime(e)
    assert u2.frei and bv2.vorschlag.richtung == -1 and bv2.vorschlag.id != bv.vorschlag.id and m.geladen == 2
    assert any(z["status"] == "verfallen" for z in j.vorschlaege(buch="regime")) and not any("Wechsel" in s for s in e.sofort)


def test_tageslauf_fred_ausfall_kein_stiller_zustand_und_nachholen(umgebung):
    j, rm = umgebung
    c = kursreihe("2026-12-02", fallend_ab="2026-11-10")
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, Makro(ausfall=True)))
    assert _regime(e) == [] and e.regime["risiko_aus"] is None and j.zustand("regime") == {}
    assert any("Monatsbewertung nicht möglich" in s and "Buch bleibt in Kasse" in s for s in e.sofort)
    assert any(bv.vorschlag.buch == "real" for bv, _ in e.vorschlaege)                    # die übrigen Bücher laufen weiter
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, Makro()))
    assert len(_regime(e)) == 1 and e.regime["risiko_aus"] is False
    vorher = j.zustand("regime")
    e = lauf(j, rm, jetzt=abend(2026, 11, 30), regime_daten=daten(c, Makro(ausfall=True)))   # Ausfall am Bewertungstag
    assert any("Position bleibt (Risiko an)" in s for s in e.sofort) and j.zustand("regime") == vorher
    assert e.regime["risiko_aus"] is False and "fehler" in e.regime
    assert all(bv.vorschlag.richtung > 0 for bv, _ in _regime(e))                         # kein Verkauf ohne Bewertung
    e = lauf(j, rm, jetzt=abend(2026, 12, 1), regime_daten=daten(c, Makro()))             # am nächsten Abend nachgeholt
    assert e.regime["neu"] == ["2026-11"] and e.regime["risiko_aus"] is True and e.regime["wechsel"]
    assert j.zustand("regime")["protokoll"]["2026-11"]["art"] == "nachgeholt"


def test_zwei_buecher_mit_spyi_abgleich_und_orders_am_selben_abend(umgebung):
    """Realbuch und regime halten SPYI.DE: Der Abgleich summiert je Titel; beide Bücher dürfen am selben Abend handeln
    (Doppel-Order-Regel gilt je Buch); eine Abweichung stoppt beide Bücher, nicht den ganzen Lauf."""
    j, rm = umgebung
    m, k = Makro(), kurse_attrappe()
    c = kursreihe("2026-12-02")
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), regime_daten=daten(c, m))
    ids = [bv.vorschlag.id for bv, u in e.vorschlaege if bv.vorschlag.buch in ("real", "regime") and u.frei]
    assert len(ids) == 2
    b = BrokerAttrappe()
    freigeben_und_senden(j, ids, b, abend(2026, 11, 16), risk=rm, kurse_laden=k, konfig_betrieb=MIT_REGIME)
    assert sorted(a.buch for a in b.gesendet) == ["real", "regime"] and {a.ticker for a in b.gesendet} == {"SPYI.DE"}
    real, reg = j.vorschlaege(buch="real")[0], j.vorschlaege(buch="regime")[0]
    fills = [{**_fill(reg, 150.0, "2026-11-17T09:00"), "exec_id": "a"},
             {**_fill(real, 150.0, "2026-11-17T09:00"), "exec_id": "b", "order_ref": f"real:{real['id']}"}]
    summe = real["stueck"] + reg["stueck"]
    e = lauf(j, rm, jetzt=abend(2026, 11, 17), regime_daten=daten(c, m), broker=BrokerAttrappe(fills=fills, positionen=[Position("DU1", "SPYI.DE", summe, 150.0)]))
    assert e.gestoppt is None and e.abgleich == "ok" and j.bestand("regime") == {"SPYI.DE": reg["stueck"]}
    e = lauf(j, rm, jetzt=abend(2026, 11, 18), regime_daten=daten(c, m), broker=BrokerAttrappe(positionen=[Position("DU1", "SPYI.DE", summe - 1, 150.0)]))
    assert e.gestoppt is None and {"real", "regime"} <= set(e.buchstopps) and _regime(e) == []


def test_datenbefund_sperrt_das_regime_buch(umgebung):
    j, rm = umgebung
    e = lauf(j, rm, jetzt=abend(2026, 11, 16), kurse=kurse_attrappe(stale={"SPYI.DE"}), regime_daten=daten(kursreihe("2026-11-16"), Makro()))
    assert "regime" in e.befunde and _regime(e) == [] and j.zustand("regime") == {}


# --- Festlegung und Trennung ------------------------------------------------------------------------------------------------
def test_signale_sind_unveraendert_wie_im_festlegungs_commit_b628678():
    """Git-Blob-Prüfsumme von engines/regime/signale.py im Commit b628678 (Zeilenenden normalisiert). Wer die eingefrorenen
    Regeln ändert, ändert das Schattenbuch – das darf nicht still geschehen."""
    inhalt = (PROJEKT_WURZEL / "src/tradingbot/engines/regime/signale.py").read_bytes().replace(b"\r\n", b"\n")
    blob = hashlib.sha1(b"blob %d\x00" % len(inhalt) + inhalt).hexdigest()
    assert blob == "3d23e5e152ecc1244b2492367db869cee06c85a3"
    assert regimebuch.FESTLEGUNG == "b628678" and regimebuch.VARIANTE == "V1"
    assert (signale.TREND_MONATE, signale.KREDIT_MONATE, signale.SAHM_SCHWELLE, signale.HALTEPFLICHT_MONATE) == (10, 10, 0.50, 2)


def test_makrodaten_des_betriebs_nur_im_betriebsmodus(monkeypatch):
    """Außerhalb des Betriebsmodus (Backtest, Auswertung) ist der Makro-Bereich des Betriebs gesperrt, noch vor jedem Abruf."""
    import tradingbot.daten.kurse as kurse

    monkeypatch.setattr(kurse, "lade_kurse", lambda *a, **k: pytest.fail("Abruf außerhalb des Betriebsmodus"))
    with pytest.raises(BetriebsbereichGesperrt):
        regimebuch.daten_betrieb(pd.Timestamp("2026-11-16"), "SPYI.DE")


def test_makro_cache_des_betriebs_liegt_im_betriebsbereich(tmp_path, monkeypatch):
    from tradingbot.backtest.tresor import betriebsmodus
    import tradingbot.betrieb.speicher as speicher
    import tradingbot.daten.kurse as kurse
    import tradingbot.daten.makro as makro

    pfade = []
    monkeypatch.setattr(speicher, "betriebspfad", lambda relativ="", **kw: (tmp_path / "betrieb" / relativ))
    monkeypatch.setattr(kurse, "lade_kurse", lambda t, start, ende, **kw: pd.DataFrame({"close": [1.0]}, index=[pd.Timestamp("2026-11-13")]))
    monkeypatch.setattr(makro, "lade_makro_tabelle", lambda r, *, cache, max_alter_stunden: pfade.append((r, Path(cache.wurzel), max_alter_stunden)))
    with betriebsmodus("Test", protokoll=tmp_path / "log"):
        _, laden = regimebuch.daten_betrieb(pd.Timestamp("2026-11-16"), "SPYI.DE")
        assert pfade == []                                                              # erst laden, wenn eine Bewertung ansteht
        laden()
    assert sorted(r for r, _, _ in pfade) == ["BAA10Y", "T10Y3M", "UNRATE"]
    assert all(w == tmp_path / "betrieb" / "cache" and alter == 0.0 for _, w, alter in pfade)
