"""Risiko-Übersicht Schritt 2: VaR/ES mit Währung, Ersatzreihen und Beiträgen (docs/RISIKO_UEBERSICHT.md, Abschnitte 6, 6a).
Synthetische Reihen mit bekanntem Ergebnis."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.kennzahlen.performance import k_schlechteste, var_es_kte_schlechteste
from tradingbot.risiko import var as rv
from tradingbot.risiko.klumpen import Basis, Posten
from tradingbot.risiko.zuordnung import Zuordnung

STICHTAG = "2026-11-24"
TAGE = rv.xetra_tage(STICHTAG)
ETFS = {"IUSA.DE": {"region": "USA", "anlageklasse": "Aktien"}, "SXR1.DE": {"region": "USA", "anlageklasse": "Aktien"},
        "EUNN.DE": {"region": "Japan", "anlageklasse": "Aktien"}}


def _aktie(t):
    return Zuordnung(t, "Einzelaktie", "Aktie", "USA", "D", waehrung_notierung="USD", waehrung_wirtschaftlich="USD", kennzeichen="exakt")


def _etf(t, region="USA"):
    return Zuordnung(t, "ETF", "Aktien", region, "breit gestreut", waehrung_notierung="EUR", waehrung_wirtschaftlich="USD",
                     kennzeichen="Näherung: Indexregion")


def _kurse_aus_renditen(renditen, start=100.0, tage=TAGE, dividende=None):
    preise = start * np.concatenate([[1.0], np.cumprod(1 + np.asarray(renditen, dtype=float))])
    return pd.DataFrame({"close": preise, "dividende": 0.0 if dividende is None else dividende}, index=tage)


def _basis(posten, kasse_w=None, fx=None, name="b"):
    kasse_w = kasse_w or {"EUR": 0.0}
    return Basis(name, "core", posten, 0.0, kasse_w, fx or {"USD": 1.0}, (name,))


def _quelle(d):
    return lambda t: d.get(t)


# Verluste 1 … 500 ‰ in fester, gemischter Reihenfolge (bekannte Ordnungsstatistik)
RNG = np.random.default_rng(7)
VERLUSTE = RNG.permutation(np.arange(1, 501)) / 10_000


# --- Quantil-Konvention -------------------------------------------------------------------------------------------------
def test_k_ohne_gleitkommafehler():
    assert 500 * (1 - 0.95) > 25                                        # 25,000000000000004 – darum gerundet
    assert [k_schlechteste(500, 0.95), k_schlechteste(500, 0.99), k_schlechteste(491, 0.95), k_schlechteste(491, 0.99)] == [25, 5, 25, 5]
    assert k_schlechteste(10, 0.99) == 1


def test_kte_schlechteste_ohne_interpolation():
    guv = -np.arange(1, 501)[RNG.permutation(500)].astype(float)       # GuV −1 … −500
    v = var_es_kte_schlechteste(guv, 0.95)
    assert (v["k"], v["n"], v["var"]) == (25, 500, 476.0)               # 25. schlechteste: −476
    assert v["es"] == pytest.approx(np.mean(np.arange(476, 501)))       # 488
    assert -np.quantile(guv, 0.05) != pytest.approx(476.0)              # numpy interpoliert (475,05)
    v99 = var_es_kte_schlechteste(guv, 0.99)
    assert (v99["k"], v99["var"], v99["es"]) == (5, 496.0, 498.0)


def test_gleichstand_stabile_reihenfolge_und_leere_eingabe():
    v = var_es_kte_schlechteste([-5.0, -5.0, 1.0, -5.0], 0.5)          # k = 2
    assert list(v["schlechteste"]) == [0, 1] and v["var"] == 5.0
    with pytest.raises(ValueError):
        var_es_kte_schlechteste([], 0.95)


# --- Szenarien ----------------------------------------------------------------------------------------------------------
def test_ein_euro_etf_bekannte_verluste_und_beitraege():
    kurse = {"IUSA.DE": _kurse_aus_renditen(-VERLUSTE)}
    b = _basis([Posten("IUSA.DE", 10, 100.0, _etf("IUSA.DE"))])      # Wert 1.000 €
    e = rv.var_es(b, _quelle(kurse), STICHTAG, etfs=ETFS)
    assert e.status == rv.OK and e.quellen["IUSA.DE"].quelle == rv.EIGEN
    k = e.kennzahlen[(1, 0.95)]
    assert (k["n"], k["k"]) == (500, 25)
    assert k["var"] == pytest.approx(1000 * 476 / 10_000) and k["es"] == pytest.approx(1000 * 488 / 10_000)
    assert e.kennzahlen[(1, 0.99)]["var"] == pytest.approx(49.6) and e.kennzahlen[(1, 0.99)]["unsicher"]
    assert not e.kennzahlen[(1, 0.95)]["unsicher"]
    assert e.beitraege[(1, 0.95)].sum() == pytest.approx(k["es"])
    assert e.wurzel10_var[0.95] == pytest.approx(np.sqrt(10) * k["var"])


def test_zehn_tage_aus_echten_zehntagesrenditen():
    r = np.full(500, 0.001)
    r[250] = -0.05                                                       # ein Einbruch
    kurse = {"IUSA.DE": _kurse_aus_renditen(r)}
    e = rv.var_es(_basis([Posten("IUSA.DE", 10, 100.0, _etf("IUSA.DE"))]), _quelle(kurse), STICHTAG, etfs=ETFS)
    k = e.kennzahlen[(10, 0.95)]
    assert (k["n"], k["k"]) == (491, 25)
    p = kurse["IUSA.DE"]["close"].to_numpy()
    zehn = np.sort(1000 * (p[10:] / p[:-10] - 1))
    assert k["var"] == pytest.approx(-zehn[24]) and k["es"] == pytest.approx(-zehn[:25].mean())
    assert e.szenarien[10].index[0] == TAGE[10]


def test_usd_titel_in_euro_sicht():
    r_usd = np.linspace(-0.02, 0.02, 500)
    eurusd = 1.10 * np.concatenate([[1.0], np.cumprod(1 + np.linspace(0.01, -0.01, 500))])
    kurse = {"AAA": _kurse_aus_renditen(r_usd), "EURUSD=X": pd.DataFrame({"close": eurusd}, index=TAGE)}
    b = _basis([Posten("AAA", 5, 100.0, _aktie("AAA"))], fx={"USD": eurusd[-1]})
    e = rv.var_es(b, _quelle(kurse), STICHTAG, etfs=ETFS)
    r_fx = eurusd[:-1] / eurusd[1:] - 1                                  # Wert eines USD in EUR
    erwartet = 500 * ((1 + r_usd) * (1 + r_fx) - 1)
    assert e.szenarien[1]["AAA"].to_numpy() == pytest.approx(erwartet, abs=1e-9)


def test_usd_kasse_traegt_wechselkursrisiko_eur_kasse_nicht():
    eurusd = 1.10 * np.concatenate([[1.0], np.cumprod(1 + VERLUSTE * 0.1)])   # EUR steigt → USD verliert
    kurse = {"EURUSD=X": pd.DataFrame({"close": eurusd}, index=TAGE)}
    b = _basis([], kasse_w={"EUR": 5000.0, "USD": 1100.0}, fx={"USD": 1.10})
    e = rv.var_es(b, _quelle(kurse), STICHTAG, etfs=ETFS)
    guv = e.szenarien[1]["Kasse USD"].to_numpy()
    assert guv == pytest.approx(1000.0 * (eurusd[:-1] / eurusd[1:] - 1))
    assert list(e.szenarien[1].columns) == ["Kasse USD"]
    nur_eur = rv.var_es(_basis([], kasse_w={"EUR": 5000.0}), _quelle({}), STICHTAG, etfs=ETFS)
    assert nur_eur.status == rv.OK and nur_eur.kennzahlen[(1, 0.95)]["var"] == 0.0


def test_dividende_am_ex_tag_kein_scheinverlust():
    preise = np.full(501, 100.0)
    preise[300:] = 98.0
    div = np.zeros(501)
    div[300] = 2.0
    kurse = {"IUSA.DE": pd.DataFrame({"close": preise, "dividende": div}, index=TAGE)}
    e = rv.var_es(_basis([Posten("IUSA.DE", 10, 98.0, _etf("IUSA.DE"))]), _quelle(kurse), STICHTAG, etfs=ETFS)
    assert e.szenarien[1]["IUSA.DE"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_beitraege_zweier_positionen_summieren_sich_zum_es():
    kurse = {"IUSA.DE": _kurse_aus_renditen(-VERLUSTE), "EUNN.DE": _kurse_aus_renditen(np.sin(np.arange(500)) / 100)}
    b = _basis([Posten("IUSA.DE", 10, 100.0, _etf("IUSA.DE")), Posten("EUNN.DE", 20, 50.0, _etf("EUNN.DE", "Japan"))])
    e = rv.var_es(b, _quelle(kurse), STICHTAG, etfs=ETFS)
    for (h, a), beitrag in e.beitraege.items():
        assert beitrag.sum() == pytest.approx(e.kennzahlen[(h, a)]["es"]), (h, a)
        assert set(beitrag.index) == {"IUSA.DE", "EUNN.DE"}
    assert e.sigma_guv_1 == pytest.approx(np.std(e.szenarien[1].sum(axis=1), ddof=1))


# --- Ersatzreihen -------------------------------------------------------------------------------------------------------
def test_kurze_einzelaktie_ersatz_iusa_und_schwelle():
    kurz = _kurse_aus_renditen(np.zeros(100), tage=TAGE[-101:])
    kurse = {"NEU": kurz, "IUSA.DE": _kurse_aus_renditen(-VERLUSTE), "EUNN.DE": _kurse_aus_renditen(np.zeros(500))}
    b = _basis([Posten("NEU", 2, 100.0, _aktie("NEU")), Posten("EUNN.DE", 16, 100.0, _etf("EUNN.DE", "Japan"))])  # 200 / 1.600
    e = rv.var_es(b, _quelle(kurse), STICHTAG, etfs=ETFS)
    assert (e.quellen["NEU"].quelle, e.quellen["NEU"].genutzt) == (rv.ERSATZ, "IUSA.DE")
    assert e.ersatz_anteil == pytest.approx(200 / 1800) and e.status == rv.OK
    assert e.kennzahlen[(1, 0.95)]["var"] == pytest.approx(200 * 476 / 10_000)
    b2 = _basis([Posten("NEU", 6, 100.0, _aktie("NEU")), Posten("EUNN.DE", 16, 100.0, _etf("EUNN.DE", "Japan"))])  # 600 / 2.200
    e2 = rv.var_es(b2, _quelle(kurse), STICHTAG, etfs=ETFS)
    assert e2.ersatz_anteil == pytest.approx(600 / 2200) and e2.status == rv.EINGESCHRAENKT


def test_etf_ersatz_gleiche_region_und_anlageklasse():
    kurse = {"FREMD.DE": _kurse_aus_renditen(np.zeros(50), tage=TAGE[-51:]), "SXR1.DE": _kurse_aus_renditen(-VERLUSTE)}
    e = rv.var_es(_basis([Posten("FREMD.DE", 1, 100.0, _etf("FREMD.DE"))]), _quelle(kurse), STICHTAG, etfs=ETFS)
    assert e.quellen["FREMD.DE"].genutzt == "SXR1.DE"                    # IUSA.DE fehlt im Cache, SXR1.DE gleiche Region
    j = rv.var_es(_basis([Posten("FREMD.DE", 1, 100.0, _etf("FREMD.DE", "Mond"))]), _quelle(kurse), STICHTAG, etfs=ETFS)
    assert j.status == rv.NICHT_BERECHENBAR and "kein Ersatz" in j.hinweise[-1]


def test_vorgaenger_aus_tickerwechsel():
    wechsel = TAGE[400]
    alt = _kurse_aus_renditen(-VERLUSTE).loc[:wechsel - pd.Timedelta(days=1)] * 2          # alter Ticker, anderes Niveau
    neu_r = -VERLUSTE[399:]
    neu = _kurse_aus_renditen(neu_r, tage=TAGE[400 - 1:]).iloc[1:]                         # ab Wechseltag
    eurusd = pd.DataFrame({"close": np.full(501, 1.0)}, index=TAGE)
    kurse = {"ALT": alt, "NEU": neu, "EURUSD=X": eurusd}
    e = rv.var_es(_basis([Posten("NEU", 10, 100.0, _aktie("NEU"))]), _quelle(kurse), STICHTAG, etfs=ETFS,
                  vorgaenger={"NEU": ("ALT", str(wechsel.date()))})
    assert e.quellen["NEU"].quelle == rv.VORGAENGER and e.ersatz_anteil == 0.0
    g = e.szenarien[1]["NEU"].to_numpy()
    assert g[:399] == pytest.approx(-1000 * VERLUSTE[:399])              # Renditen des Vorgängers
    assert g[400:] == pytest.approx(-1000 * VERLUSTE[400:])              # danach eigene


def test_vorgaenger_aus_journal(tmp_path):
    from tradingbot.betrieb.journal import Journal
    j = Journal(tmp_path / "j.sqlite")
    j.massnahme(beleg_id="b1", buch="fundamental_a", art="tickerwechsel", status="gebucht", tag="2026-06-01",
                posten=[{"ticker": "ALT", "stueck": -5}, {"ticker": "NEU", "stueck": 5}])
    j.massnahme(beleg_id="b2", buch="fundamental_a", art="tickerwechsel", status="erkannt", tag="2026-06-02",
                posten=[{"ticker": "X", "stueck": -1}, {"ticker": "Y", "stueck": 1}])
    assert rv.vorgaenger_aus_journal(j) == {"NEU": ("ALT", "2026-06-01")}
    j.schliessen()


def test_nicht_berechenbar_ohne_kurs_oder_fx():
    b = _basis([Posten("AAA", 1, None, _aktie("AAA"))])
    assert rv.var_es(b, _quelle({}), STICHTAG, etfs=ETFS).status == rv.NICHT_BERECHENBAR
    b = _basis([], kasse_w={"EUR": 1.0, "USD": 10.0}, fx={"USD": 1.1})
    e = rv.var_es(b, _quelle({}), STICHTAG, etfs=ETFS)
    assert e.status == rv.NICHT_BERECHENBAR and any("USD" in h for h in e.hinweise)


def test_veraltete_reihe_deckt_fenster_nicht():
    alt = _kurse_aus_renditen(np.zeros(500)).iloc[:-10]                  # endet 10 Handelstage vor dem Stichtag
    assert rv.gesamtrendite_index(alt, TAGE) is None
    assert rv.gesamtrendite_index(_kurse_aus_renditen(np.zeros(500)), TAGE) is not None


def test_fenster_501_xetra_tage():
    assert len(TAGE) == 501 and TAGE[-1] == pd.Timestamp(STICHTAG)
    assert pd.Timestamp("2025-12-25") not in TAGE and pd.Timestamp("2025-12-24") not in TAGE


# --- Datenquelle: nur Cache des Betriebs, ohne Netz, Probe-Schicht -------------------------------------------------------
def test_cache_kurse_liest_nur_ueber_lesepfad_ohne_netz(tmp_path, monkeypatch):
    from tradingbot.betrieb import kurscache
    from tradingbot.daten import kurse as daten_kurse
    from tradingbot.daten import schicht
    from tradingbot.daten.cache import ParquetCache

    daten = tmp_path / "daten"
    monkeypatch.setattr(schicht, "_daten", lambda: daten.resolve())
    wurzel = daten / "betrieb" / "cache"
    monkeypatch.setattr(kurscache, "_wurzel", lambda: wurzel)

    def verboten(*a, **k):
        raise AssertionError("kein Netzabruf in der Risiko-Übersicht")

    monkeypatch.setattr(daten_kurse, "lade_kurse", verboten)
    ParquetCache(wurzel).schreiben("kurse", "IUSA.DE", _kurse_aus_renditen(-VERLUSTE), {})
    schicht_wurzel = daten / "betrieb" / "probe" / "cache"
    with schicht.probe_schicht(schicht_wurzel):
        ParquetCache(wurzel).schreiben("kurse", "IUSA.DE", _kurse_aus_renditen(np.zeros(500)), {})   # nur in die Schicht
        e = rv.var_es(_basis([Posten("IUSA.DE", 10, 100.0, _etf("IUSA.DE"))]), rv.cache_kurse(), STICHTAG, etfs=ETFS)
        assert e.kennzahlen[(1, 0.95)]["var"] == pytest.approx(0.0)      # Schicht zuerst
    e = rv.var_es(_basis([Posten("IUSA.DE", 10, 100.0, _etf("IUSA.DE"))]), rv.cache_kurse(), STICHTAG, etfs=ETFS)
    assert e.kennzahlen[(1, 0.95)]["var"] == pytest.approx(47.6)         # Original unverändert
