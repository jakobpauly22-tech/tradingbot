"""Risk-Manager: je Regel ein Test (Entscheidungen 31.10., 01.11. und 02.11.2026)."""
import pandas as pd
import pytest

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import Kontext, OrderVorschlag, RiskManager

KOSTEN = Kostenmodell(gebuehren={"EUR": {"satz": 0.0005, "minimum": 1.25, "maximum": 29.0}})
TAG = pd.Timestamp("2026-11-02")


@pytest.fixture
def rm(tmp_path):
    return RiskManager(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), KOSTEN, tmp_path)


def kauf(**kw):
    basis = dict(id="v1", datum=TAG, teil="core", ticker="SPYI.DE", richtung=1, stueck=2, letzter_kurs=200.0, art="etf", limit=204.0)
    return OrderVorschlag(**{**basis, **kw})


def kontext(**kw):
    basis = dict(kasse=500.0, teil_wert={"core": 500.0, "satellite": 1250.0})
    return Kontext(**{**basis, **kw})


def test_core_etf_kauf_frei(rm):
    u = rm.pruefe(kauf(), kontext())
    assert u.frei, u.gruende


def test_not_aus_sperrt_alles(rm, tmp_path):
    (tmp_path / "STOP").write_text("")
    assert "Not-Aus" in rm.pruefe(kauf(), kontext()).gruende[0]
    verkauf = kauf(richtung=-1, limit=None)
    assert not rm.pruefe(verkauf, kontext(bestand={"SPYI.DE": 2})).frei


def test_kein_leerverkauf_und_kein_hebel(rm):
    assert any("Leerverkäufe" in g for g in rm.pruefe(kauf(richtung=-1, limit=None), kontext()).gruende)
    assert any("kein Hebel" in g for g in rm.pruefe(kauf(), kontext(kasse=300.0)).gruende)


def test_gebuehrenregel_nur_fuer_kaeufe(rm):
    klein = kauf(stueck=1, letzter_kurs=100.0, limit=102.0)          # 102 € Orderwert: 1,25 € > 1 %
    assert any("1 %" in g for g in rm.pruefe(klein, kontext()).gruende)
    ausstieg = kauf(stueck=1, letzter_kurs=100.0, richtung=-1, limit=None)
    assert rm.pruefe(ausstieg, kontext(bestand={"SPYI.DE": 1})).frei


def test_positionsgrenzen(rm):
    aktie = kauf(teil="core", ticker="AAPL", art="aktie", stueck=1, letzter_kurs=150.0, limit=152.0)
    assert any("5 %" in g for g in rm.pruefe(aktie, kontext(kasse=5000.0, teil_wert={"core": 1000.0}, fundamental={"AAPL": []})).gruende)
    sat = kauf(teil="satellite", ticker="EUNK.DE", stueck=4, letzter_kurs=80.0, limit=81.0, stop=78.0)
    assert any("25 %" in g for g in rm.pruefe(sat, kontext(kasse=1250.0)).gruende)        # 320 € > 312,50 €
    ohne_stop = kauf(teil="satellite", ticker="EUNK.DE", stueck=3, letzter_kurs=80.0, limit=81.0)
    assert any("ohne Stop" in g for g in rm.pruefe(ohne_stop, kontext(kasse=1250.0)).gruende)
    riskant = kauf(teil="satellite", ticker="EUNK.DE", stueck=3, letzter_kurs=80.0, limit=81.0, stop=70.0)   # 30 € > 12,50 €
    assert any("Risiko" in g for g in rm.pruefe(riskant, kontext(kasse=1250.0)).gruende)


def test_fundamental_veto_nur_einzelaktien_beneish_nur_hinweis(rm):
    aktie = kauf(teil="core", ticker="XYZ", art="aktie", stueck=1, letzter_kurs=150.0, limit=152.0)
    k = kontext(kasse=5000.0, teil_wert={"core": 10_000.0}, fundamental={"XYZ": ["Piotroski 3 ≤ 3", "Beneish -1.50 > -1.78"]})
    u = rm.pruefe(aktie, k)
    assert not u.frei and any("Piotroski" in g for g in u.gruende) and not any("Beneish" in g for g in u.gruende)
    assert any("Beneish" in x for x in u.hinweise)
    nur_beneish = kontext(kasse=5000.0, teil_wert={"core": 10_000.0}, fundamental={"XYZ": ["Beneish -1.50 > -1.78"]})
    assert rm.pruefe(aktie, nur_beneish).frei
    assert rm.pruefe(kauf(), kontext(fundamental={"SPYI.DE": ["Piotroski 2 ≤ 3"]})).frei      # ruht bei ETFs


def test_satellite_pause_und_stopp_nur_fuer_kaeufe(rm):
    sat = kauf(teil="satellite", ticker="EUNK.DE", stueck=3, letzter_kurs=80.0, limit=81.0, stop=78.0)
    assert any("pausiert" in g for g in rm.pruefe(sat, kontext(kasse=1250.0, satellite_monat=-0.11)).gruende)
    assert any("gestoppt" in g for g in rm.pruefe(sat, kontext(kasse=1250.0, satellite_vom_hoch=-0.21)).gruende)
    ausstieg = kauf(teil="satellite", ticker="EUNK.DE", stueck=3, letzter_kurs=80.0, richtung=-1, limit=None)
    assert rm.pruefe(ausstieg, kontext(bestand={"EUNK.DE": 3}, satellite_vom_hoch=-0.25)).frei


def test_core_notbremse_nur_hinweis(rm):
    u = rm.pruefe(kauf(), kontext(core_rueckstand_12m_pp=-11.0))
    assert u.frei and "Review" in u.hinweise[0]


def test_plausibilitaet(rm):
    assert any("Höchstwert" in g for g in rm.pruefe(kauf(stueck=3, limit=204.0), kontext(kasse=10_000.0)).gruende)   # 612 € > 500 €
    assert any("Orders an einem Tag" in g for g in rm.pruefe(kauf(), kontext(orders_heute=5)).gruende)
    assert any("ohne Limit" in g for g in rm.pruefe(kauf(limit=None), kontext()).gruende)
    assert any("2 %" in g for g in rm.pruefe(kauf(limit=204.5), kontext()).gruende)
    assert any("Verkäufe ohne Limit" in g for g in rm.pruefe(kauf(richtung=-1, limit=199.0), kontext(bestand={"SPYI.DE": 2})).gruende)


def test_doppel_orders(rm):
    assert any("schon gesendet" in g for g in rm.pruefe(kauf(), kontext(gesendete_ids={"v1"})).gruende)
    assert any("offene Order" in g for g in rm.pruefe(kauf(id="v2"), kontext(offene_orders=[("SPYI.DE", 1)])).gruende)


def test_pruefe_alle_verbraucht_kasse_und_zaehlt_orders(rm):
    a = kauf(id="a", stueck=1, limit=204.0)
    b = kauf(id="b", stueck=1, limit=204.0, ticker="EUNL.DE")
    c = kauf(id="c", stueck=1, limit=204.0, ticker="IUSQ.DE")
    ergebnis = rm.pruefe_alle([a, b, c], kontext(kasse=420.0))
    frei = [v.id for v, u in ergebnis if u.frei]
    assert frei == ["a", "b"]                                   # dritter Kauf scheitert an der Kasse
