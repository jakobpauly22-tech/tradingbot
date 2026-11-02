"""Risk-Manager: je Regel ein Test, je Buch (Entscheidungen 31.10., 01.11. und 02.11.2026)."""
import pandas as pd
import pytest

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import Kontext, OrderVorschlag, RiskManager

KOSTEN = Kostenmodell(gebuehren={"EUR": {"satz": 0.0005, "minimum": 1.25, "maximum": 29.0},
                                 "USD": {"je_stueck": 0.005, "minimum": 1.0, "max_anteil": 0.01}})
TAG = pd.Timestamp("2026-11-02")


@pytest.fixture
def rm(tmp_path):
    return RiskManager(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), KOSTEN, tmp_path)


def kauf(**kw):
    basis = dict(id="v1", datum=TAG, buch="real", ticker="SPYI.DE", richtung=1, stueck=2, letzter_kurs=200.0, art="etf", limit=204.0)
    return OrderVorschlag(**{**basis, **kw})


def real(**kw):
    return Kontext(**{**dict(buch="real", kasse=500.0, wert=500.0), **kw})


def sat(buch="crossover", **kw):
    return Kontext(**{**dict(buch=buch, kasse=10_000.0, wert=10_000.0), **kw})


def sat_kauf(**kw):
    basis = dict(buch="crossover", ticker="EUNK.DE", stueck=30, letzter_kurs=80.0, limit=81.0, stop=77.0)
    return kauf(**{**basis, **kw})


def test_core_etf_kauf_im_realbuch_frei(rm):
    u = rm.pruefe(kauf(), real())
    assert u.frei, u.gruende


def test_unbekanntes_buch_und_falscher_kontext(rm):
    assert "unbekanntes Buch" in rm.pruefe(kauf(buch="phantasie"), real()).gruende[0]
    assert "geprüft gegen Buch" in rm.pruefe(kauf(buch="crossover"), real()).gruende[0]


def test_not_aus_sperrt_alles(rm, tmp_path):
    (tmp_path / "STOP").write_text("")
    assert "Not-Aus" in rm.pruefe(kauf(), real()).gruende[0]
    assert not rm.pruefe(kauf(richtung=-1, limit=None), real(bestand={"SPYI.DE": 2})).frei


def test_kein_leerverkauf_und_kein_hebel_je_buch(rm):
    assert any("Leerverkäufe" in g for g in rm.pruefe(kauf(richtung=-1, limit=None), real()).gruende)
    assert any("kein Hebel" in g for g in rm.pruefe(kauf(), real(kasse=300.0)).gruende)
    # Bestand eines anderen Buchs zählt nicht
    assert not rm.pruefe(kauf(buch="crossover", richtung=-1, limit=None), sat(bestand={})).frei


def test_gebuehrenregel_nur_fuer_kaeufe(rm):
    klein = kauf(stueck=1, letzter_kurs=100.0, limit=102.0)          # 102 € Orderwert: 1,25 € > 1 %
    assert any("1 %" in g for g in rm.pruefe(klein, real()).gruende)
    ausstieg = kauf(stueck=1, letzter_kurs=100.0, richtung=-1, limit=None)
    assert rm.pruefe(ausstieg, real(bestand={"SPYI.DE": 1})).frei


def test_usd_gebuehrenplan_fuer_us_aktien(rm):
    aktie = kauf(buch="fundamental_a", ticker="AAPL", art="aktie", stueck=2, letzter_kurs=200.0, limit=204.0,
                 gebuehrenplan="USD", eur_kurs=1.1)
    u = rm.pruefe(aktie, Kontext(buch="fundamental_a", kasse=10_000.0, wert=10_000.0, fundamental={"AAPL": []}))
    assert u.frei, u.gruende                                         # 1 USD Mindestgebühr ≪ 1 % von 408 €


def test_positionsgrenzen_je_buch(rm):
    aktie = kauf(buch="fundamental_a", ticker="AAPL", art="aktie", stueck=3, letzter_kurs=200.0, limit=204.0)
    k = Kontext(buch="fundamental_a", kasse=10_000.0, wert=10_000.0, fundamental={"AAPL": []})
    assert any("5 % des Buchwerts" in g for g in rm.pruefe(aktie, k).gruende)     # 600 € > 500 €
    assert any("25 % des Buchwerts" in g for g in rm.pruefe(sat_kauf(stueck=32), sat()).gruende)   # 2.560 € > 2.500 €
    assert any("ohne Stop" in g for g in rm.pruefe(sat_kauf(stop=None), sat()).gruende)
    assert any("Risiko" in g for g in rm.pruefe(sat_kauf(stop=70.0), sat()).gruende)                # 300 € > 100 €
    assert rm.pruefe(sat_kauf(), sat()).frei


def test_fundamental_veto_nur_einzelaktien_beneish_nur_hinweis(rm):
    aktie = kauf(buch="fundamental_a", ticker="XYZ", art="aktie", stueck=1, letzter_kurs=150.0, limit=152.0)
    k = Kontext(buch="fundamental_a", kasse=10_000.0, wert=10_000.0, fundamental={"XYZ": ["Piotroski 3 ≤ 3", "Beneish -1.50 > -1.78"]})
    u = rm.pruefe(aktie, k)
    assert not u.frei and any("Piotroski" in g for g in u.gruende) and not any("Beneish" in g for g in u.gruende)
    assert any("Beneish" in x for x in u.hinweise)
    k.fundamental = {"XYZ": ["Beneish -1.50 > -1.78"]}
    assert rm.pruefe(aktie, k).frei
    assert rm.pruefe(kauf(), real(fundamental={"SPYI.DE": ["Piotroski 2 ≤ 3"]})).frei      # ruht bei ETFs


def test_satellite_limits_in_skalierungsbuechern_nur_protokolliert(rm):
    u = rm.pruefe(sat_kauf(), sat(monatsrendite=-0.11))
    assert u.frei and any(x.startswith("hätte gesperrt am 02.11.2026") and "pausiert" in x for x in u.hinweise)
    u = rm.pruefe(sat_kauf(), sat(vom_hoch=-0.21))
    assert u.frei and any(x.startswith("hätte gesperrt am") and "gestoppt" in x for x in u.hinweise)
    # harte Regeln gelten trotzdem in allen Büchern
    assert any("kein Hebel" in g for g in rm.pruefe(sat_kauf(), sat(kasse=100.0, vom_hoch=-0.21)).gruende)


def test_satellite_limits_im_realbuch_sperrend(rm, monkeypatch):
    # Realbuch mit Satellite-Rolle (z.B. später echter Satellite): Limits sind Veto
    rm.b = {**rm.b, "buecher": {**rm.b["buecher"], "real_sat": {"art": "real", "budget_eur": 1250.0, "rolle": "satellite",
                                                                  "max_orders_pro_tag": 5, "freigabe": "einzeln"}}}
    v = sat_kauf(buch="real_sat", stueck=3, letzter_kurs=80.0, limit=81.0, stop=78.0)
    k = Kontext(buch="real_sat", kasse=1250.0, wert=1250.0, vom_hoch=-0.21)
    u = rm.pruefe(v, k)
    assert not u.frei and any("gestoppt" in g for g in u.gruende)
    k2 = Kontext(buch="real_sat", kasse=1250.0, wert=1250.0, monatsrendite=-0.12)
    assert any("pausiert" in g for g in rm.pruefe(v, k2).gruende)
    ausstieg = sat_kauf(buch="real_sat", richtung=-1, limit=None, stop=None, stueck=3)
    assert rm.pruefe(ausstieg, Kontext(buch="real_sat", kasse=0.0, wert=1250.0, bestand={"EUNK.DE": 3}, vom_hoch=-0.25)).frei


def test_eigene_hoechststaende_je_buch(rm):
    assert rm.pruefe(sat_kauf(buch="momentum"), sat("momentum", vom_hoch=-0.05)).frei


def test_core_notbremse_nur_hinweis(rm):
    u = rm.pruefe(kauf(), real(core_rueckstand_12m_pp=-11.0))
    assert u.frei and "Review" in u.hinweise[0]


def test_plausibilitaet_je_buch(rm):
    assert any("Budget des Buchs" in g for g in rm.pruefe(kauf(stueck=3), real(kasse=10_000.0)).gruende)   # 612 € > 500 €
    assert rm.pruefe(sat_kauf(), sat()).frei                                                              # 2.430 € ≤ 10.000 €
    assert any("5 Orders" in g for g in rm.pruefe(kauf(), real(orders_heute=5)).gruende)
    assert rm.pruefe(sat_kauf(), sat(orders_heute=24)).frei
    assert any("25 Orders" in g for g in rm.pruefe(sat_kauf(), sat(orders_heute=25)).gruende)
    assert any("ohne Limit" in g for g in rm.pruefe(kauf(limit=None), real()).gruende)
    assert any("2 %" in g for g in rm.pruefe(kauf(limit=204.5), real()).gruende)
    assert any("Verkäufe ohne Limit" in g for g in rm.pruefe(kauf(richtung=-1, limit=199.0), real(bestand={"SPYI.DE": 2})).gruende)


def test_doppel_orders_je_buch(rm):
    assert any("schon gesendet" in g for g in rm.pruefe(kauf(), real(gesendete_ids={"v1"})).gruende)
    assert any("offene Order" in g for g in rm.pruefe(kauf(id="v2"), real(offene_orders=[("real", "SPYI.DE", 1)])).gruende)
    # gleiche Order in einem anderen Buch blockiert nicht
    assert rm.pruefe(kauf(id="v3", buch="fundamental_a", stueck=2),
                     Kontext(buch="fundamental_a", kasse=10_000.0, wert=10_000.0, offene_orders=[("real", "SPYI.DE", 1)])).frei


def test_pruefe_alle_je_buch(rm):
    a = kauf(id="a", stueck=1)
    b = kauf(id="b", stueck=1)                              # gleicher Ticker, gleiche Richtung im selben Buch: Doppel-Order
    c = kauf(id="c", stueck=1, buch="fundamental_a")        # anderes Buch darf denselben Ticker kaufen
    d = kauf(id="d", stueck=1, ticker="EUNL.DE")
    e = kauf(id="e", stueck=1, ticker="IUSQ.DE")            # Kasse des Realbuchs reicht nicht mehr
    kontexte = {"real": real(kasse=420.0), "fundamental_a": Kontext(buch="fundamental_a", kasse=10_000.0, wert=10_000.0)}
    urteile = {v.id: u for v, u in rm.pruefe_alle([a, b, c, d, e], kontexte)}
    assert [i for i, u in sorted(urteile.items()) if u.frei] == ["a", "c", "d"]
    assert any("offene Order" in g for g in urteile["b"].gruende) and any("kein Hebel" in g for g in urteile["e"].gruende)
    assert kontexte["real"].kasse == 420.0                  # Eingangsstand bleibt unverändert
