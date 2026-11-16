"""c3-Absicherung nach der unabhängigen Prüfung (Jakob 16.11.2026, docs/FUNDAMENTAL.md): Befund 10 (Kriterium
„Splitspalte“), Befund 11 Variante B (kein Marktwert bei unsicherem H, Rückfall sichtbar), Befund 14 (harte Sperre).
Ohne Netz."""
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

import tradingbot.daten.rohkurse_marktwert as rm
from tradingbot.daten.rohkurse_marktwert import schwelle_der_abnahme, sperrtext, splitabgleich, unsichere_reihen

TAGE = pd.bdate_range("2010-06-01", "2024-12-31")
WERKZEUGE = Path(__file__).resolve().parents[2] / "tools"


def _werkzeug(name):
    spec = importlib.util.spec_from_file_location(f"werkzeug_{name}", WERKZEUGE / f"{name}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _split(**ereignisse) -> pd.Series:
    s = pd.Series(0.0, index=TAGE)
    for tag, f in ereignisse.items():
        s[pd.Timestamp(tag.lstrip("d").replace("_", "-"))] = f
    return s


def _liste(*zeilen) -> pd.DataFrame:
    return pd.DataFrame([{"art": a, "split_faktor": f} for _, a, f in zeilen],
                        index=pd.DatetimeIndex([t for t, _, _ in zeilen]))


# --- Befund 10: Splitspalte ---------------------------------------------------------------------------------------
def test_split_bei_beiden_quellen_besteht():
    y = _split(d2014_06_09=7.0, d2020_08_31=4.0)
    t = _split(d2014_06_09=7.000007, d2020_08_31=4.0)
    assert splitabgleich(t, y, _liste(("2014-06-09", "split", 7.0)))["bestanden"]
    assert splitabgleich(t, y, None)["bestanden"]                        # nicht in der Liste, beide führen ihn


def test_fehlender_split_bei_tiingo_faellt_durch():
    e = splitabgleich(_split(), _split(d2020_08_31=4.0), _liste(("2020-08-31", "split", 4.0)))
    assert not e["bestanden"] and "fehlt bei Tiingo" in e["grund"]


def test_datum_plus_minus_ein_handelstag():
    y = _split(d2020_08_31=4.0)                                          # Montag
    assert splitabgleich(_split(d2020_09_01=4.0), y)["bestanden"]        # 1 Handelstag später
    assert splitabgleich(_split(d2020_08_28=4.0), y)["bestanden"]        # Freitag davor = 1 Handelstag
    e = splitabgleich(_split(d2020_09_02=4.0), y)                        # 2 Handelstage: kein Partner
    assert not e["bestanden"] and "fehlt bei Tiingo" in e["grund"] and "ohne Yahoo-Ereignis" in e["grund"]


def test_faktor_plus_minus_ein_prozent():
    y = _split(d2020_08_31=4.0)
    assert splitabgleich(_split(d2020_08_31=4.039), y)["bestanden"]
    e = splitabgleich(_split(d2020_08_31=4.05), y)
    assert not e["bestanden"] and "Tiingo 4.05 statt 4" in e["grund"]


def test_abspaltung_ohne_tiingo_partner_besteht_mit_partner_nicht():
    """Yahoo führt die Abspaltung als Split, Tiingo nicht: richtig. Tiingo mit Faktor (MRK/Organon 1,048): nicht bestanden."""
    y = _split(d2021_06_03=1.048)
    liste = _liste(("2021-06-03", "abspaltung", 1.0))
    assert splitabgleich(_split(), y, liste)["bestanden"]
    e = splitabgleich(_split(d2021_06_03=1.048), y, liste)
    assert not e["bestanden"] and "abspaltung" in e["grund"]
    assert not splitabgleich(_split(), y, None)["bestanden"]              # ohne Einordnung: fehlt bei Tiingo


def test_nicht_zugehoerig_wie_abspaltung():
    y = _split(d2019_04_02=1.487)
    assert splitabgleich(_split(), y, _liste(("2019-04-02", "nicht_zugehoerig", None)))["bestanden"]


def test_kombiniert_gegen_geprueften_split_faktor():
    """LDOS 2013: Yahoo 0,405 (Reverse-Split 1:4 und Abspaltung), Aktienzahl-Faktor 0,25."""
    y = _split(d2013_09_30=0.405)
    liste = _liste(("2013-09-30", "kombiniert", 0.25))
    assert splitabgleich(_split(d2013_09_30=0.25), y, liste)["bestanden"]
    assert not splitabgleich(_split(d2013_09_30=0.405), y, liste)["bestanden"]
    assert not splitabgleich(_split(), y, liste)["bestanden"]


def test_unklar_besteht_nie():
    y = _split(d2018_12_28=1.806)
    e = splitabgleich(_split(d2018_12_28=1.806), y, _liste(("2018-12-28", "unklar", None)))
    assert not e["bestanden"] and "unklar" in e["grund"]


def test_tiingo_ereignis_ohne_yahoo_faellt_durch_und_vor_2011_zaehlt_nicht():
    e = splitabgleich(_split(d2017_05_01=2.0), _split())
    assert not e["bestanden"] and "ohne Yahoo-Ereignis" in e["grund"]
    assert splitabgleich(_split(d2010_07_01=2.0), _split())["bestanden"]  # vor 01.01.2011 nicht geprüft


def test_liste_findet_eintrag_einen_handelstag_daneben():
    y = _split(d2021_06_03=1.048)
    assert splitabgleich(_split(), y, _liste(("2021-06-04", "abspaltung", 1.0)))["bestanden"]


def test_abnahmewerkzeug_ordnet_ciks_der_reihe_zu():
    w = _werkzeug("pruefe_rohkurse")
    status = pd.DataFrame({"quelle": ["yfinance", "yfinance", "tiingo"], "symbol": ["DD", "DD", "DD"],
                           "gueltig": [True, True, False]}, index=[3, 7, 9])
    universum = pd.DataFrame({"cik": [30554, 1666700, 1], "vorgaenger_ciks": [[], [99], []]}, index=[3, 7, 9])
    assert w.ciks_je_reihe(status, universum) == {("yfinance", "DD"): {30554, 1666700, 99}}
    a = _liste(("2019-06-03", "kombiniert", 0.333333))
    b = _liste(("2019-06-03", "nicht_zugehoerig", None), ("2017-09-01", "split", 2.0))
    t = w.liste_der_reihe({1666700, 30554}, {1666700: a, 30554: b})
    assert len(t) == 2 and t.loc["2019-06-03", "art"] in ("kombiniert", "nicht_zugehoerig")
    assert w.liste_der_reihe({5}, {}) is None


# --- Befund 14: harte Sperre --------------------------------------------------------------------------------------
def _abnahme(nicht: int, gesamt: int) -> pd.DataFrame:
    return pd.DataFrame({"quelle": "yfinance", "symbol": [f"S{i}" for i in range(gesamt)],
                         "bestanden": [i >= nicht for i in range(gesamt)], "H": 1.0, "grund": ""})


def test_fehlerschwelle_der_abnahme():
    assert schwelle_der_abnahme(_abnahme(5, 100)) is None                # genau 5 %: noch erlaubt
    text = schwelle_der_abnahme(_abnahme(6, 100))
    assert text and "6 von 100" in text
    assert schwelle_der_abnahme(pd.DataFrame(columns=["bestanden"])) is None


def test_sperre_c3_mit_fehlerschwelle(monkeypatch):
    monkeypatch.setattr(rm, "lade_abnahme", lambda: _abnahme(10, 100))
    monkeypatch.setattr(rm, "dauerhaft_nicht_verfuegbar", lambda: set())
    monkeypatch.setattr(pd, "read_csv", lambda *a, **k: pd.DataFrame({"quelle": ["yfinance"], "symbol": ["S1"], "gueltig": [True]}))
    gruende = rm.sperre_c3()
    assert gruende and gruende[0].startswith("Fehlerschwelle")
    assert "Fehlerschwelle der Abnahme überschritten" in sperrtext(gruende)


def test_alle_c3_werkzeuge_sperren_bei_fehlerschwelle(monkeypatch, capsys):
    monkeypatch.setattr(rm, "sperre_c3", lambda: ["Fehlerschwelle der Abnahme überschritten: 40 von 563 Reihen nicht bestanden"])
    for name in ("gegenprobe_index", "nachbau_sp500_ohne_finanzwerte", "obergrenze_abspaltungen_tiingo"):
        assert _werkzeug(name).main(["--c3"] + (["--backtest", "x"] if name.startswith("obergrenze") else [])) == 1, name
    assert _werkzeug("auswertung_scores").main(["--eq-offer-splitbereinigt", "--marktwert-rohkurse"]) == 1
    assert "Fehlerschwelle der Abnahme" in capsys.readouterr().err


# --- Befund 11: Variante B und Sichtbarkeit -----------------------------------------------------------------------
def test_unsichere_reihen_nur_bei_nicht_bestanden_und_h_ungleich_1():
    abn = pd.DataFrame({"quelle": "yfinance", "symbol": ["DD", "MTCH", "HWM", "ORLY", "GEV"],
                        "bestanden": [False, False, False, True, False], "H": [0.7967, 0.2856, 1.002, 15.0, float("nan")],
                        "grund": ["nur 50 %", "nur 52 %", "nur 97 %", "", "keine gemeinsamen Tage"]})
    u = unsichere_reihen(abn)
    assert set(u) == {("yfinance", "DD"), ("yfinance", "MTCH")}
    assert u[("yfinance", "DD")]["H"] == pytest.approx(0.7967)


def test_rueckfall_tabelle_der_scores():
    w = _werkzeug("auswertung_scores")
    tab = pd.DataFrame({"firma": [1, 1, 2, 3], "veraltet": False, "marktwert": [None, None, 5e9, 7e9],
                        "marktwert_kurs": ["kein Marktwert (Befund 11)"] * 2 + ["Abnahme fehlt oder nicht bestanden (GEV)", "roh"]})
    text = "\n".join(w.rueckfall_tabelle(tab, {1: "Abnahme fehlt oder nicht bestanden (DD)", 2: "x", 3: "roh"},
                                         {1: {"symbol": "DD", "H": 0.7967, "grund": ""}}, {1: "DD", 2: "GEV"}))
    assert "2 Firmen, 3 Firmen-Stichtage" in text
    assert "| 1 | DD | kein Marktwert (Befund 11) |" in text and "| 0.7967 | 2 | 2 |" in text
    assert "| 2 | GEV |" in text and "| – | 1 | 0 |" in text
    assert w.rueckfall_tabelle(tab.drop(columns="marktwert_kurs"), {}, {}, {}) == []


def test_rueckfall_im_backtest_mit_haltetagen():
    w = _werkzeug("backtest_fundamental")
    scores = pd.DataFrame({"firma": [1, 1, 3], "veraltet": False, "marktwert": [None, 4e9, 7e9],
                           "marktwert_kurs": ["kein Marktwert (Befund 11)", "Rohkurs erst nach dem Stichtag (Teil b)", "roh"]})
    bestaende = pd.DataFrame({"CIK1": [0, 5, 5, 0], "CIK3": [1, 1, 1, 1]})
    text = "\n".join(w.rueckfall_im_buch(scores, bestaende, {1: "DD"}))
    assert "1 Firmen" in text and "| 1 | DD | Rohkurs erst nach dem Stichtag (Teil b) | 2 | 1 | 2 |" in text


def test_rueckfall_gewichte_im_nachbau():
    from tradingbot.daten.sp500_nachbau import Firmendaten, rueckfall_gewichte

    tage = pd.bdate_range("2016-09-28", "2016-10-06")
    gewichte = pd.DataFrame({1: 0.02, 2: 0.98, 3: float("nan")}, index=tage)
    daten = Firmendaten({}, {}, {}, pd.DataFrame(), pd.DataFrame(),
                        rohkurse_status={1: "Abnahme fehlt oder nicht bestanden (DD)", 2: "roh", 3: "Rohreihe fehlt (X)"},
                        rohkurse_unsicher={1: {"symbol": "DD", "H": 0.8, "grund": ""}})
    rf = rueckfall_gewichte(daten, gewichte, "2016-10-01")
    assert list(rf["firma"]) == [1, 3]
    assert rf.iloc[0]["gewicht_mittel"] == pytest.approx(0.02) and rf.iloc[0]["H"] == 0.8 and rf.iloc[0]["tage"] == 4
    assert rf.iloc[1]["tage"] == 0
