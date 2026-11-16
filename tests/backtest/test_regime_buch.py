"""Schattenbuch „regime“: Strategie, statische Mischung, Aktienanteil und Kriterien je Hälfte (docs/REGIME.md)."""
import numpy as np
import pandas as pd
import pytest

from conftest import kerzen
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.engines.regime import buch


def _definition(strategie, kapital=10_000.0):
    return TeilportfolioDefinition("regime", kapital, strategie, [Instrument("A", "etf")], art="schatten", steuergruppe="schatten")


def _zustand(werte: dict) -> pd.Series:
    return pd.Series({pd.Timestamp(t): w for t, w in werte.items()}, dtype=object)


# --- Strategie ---

def test_regime_strategie_wechselt_am_tag_nach_der_bewertung(konfig, ohne_kosten, bruchteile):
    m = Marktdaten({"A": kerzen([100.0] * 60, start="2024-01-31")})
    zustand = _zustand({"2024-01-31": False, "2024-02-29": True, "2024-03-29": False})
    e = simuliere([_definition(buch.RegimeStrategie("A", zustand))], m, "2024-01-31", "2024-04-22",
                  kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["regime"]
    assert [(t.datum.date().isoformat(), t.richtung) for t in e.trades.itertuples()] == [
        ("2024-02-01", 1), ("2024-03-01", -1), ("2024-04-01", 1)]
    assert e.bestaende.loc["2024-02-29", "A"] == pytest.approx(100.0)       # am Bewertungstag noch investiert
    assert e.bestaende.loc["2024-03-01", "A"] == 0.0
    assert e.werte.loc["2024-03-15", "cash"] == pytest.approx(10_000.0)     # Kasse zu 0 %


def test_regime_strategie_beginnt_mit_risiko_aus_in_kasse(konfig, mit_kosten):
    m = Marktdaten({"A": kerzen([100.0] * 30, start="2024-01-31")})
    e = simuliere([_definition(buch.RegimeStrategie("A", _zustand({"2024-01-31": True})))], m, "2024-01-31", "2024-03-11",
                  kosten=mit_kosten, regeln=Ausfuehrungsregeln(), konfig=konfig)["regime"]
    assert e.trades.empty and e.wert.iloc[-1] == 10_000.0


def test_regime_strategie_wiederholt_gescheiterte_order(konfig, ohne_kosten, bruchteile):
    k = kerzen([100.0] * 10, start="2024-01-31")
    k.loc["2024-02-01", "open"] = 0.0                                       # kein Handel am ersten Ausführungstag
    e = simuliere([_definition(buch.RegimeStrategie("A", _zustand({"2024-01-31": False})))], Marktdaten({"A": k}),
                  "2024-01-31", "2024-02-13", kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["regime"]
    assert len(e.verworfen) == 1 and e.trades.iloc[0].datum == pd.Timestamp("2024-02-02")


def test_regime_strategie_ohne_zustand_bricht_ab():
    with pytest.raises(ValueError, match="kein Zustand"):
        buch.RegimeStrategie("A", pd.Series([None, None], index=pd.to_datetime(["2024-01-31", "2024-02-29"]), dtype=object))


def test_mischung_quartalsweise_und_neues_gewicht_an_der_haelftengrenze(konfig, ohne_kosten, bruchteile):
    rng = np.random.default_rng(3)
    m = Marktdaten({"A": kerzen(100 * np.cumprod(1 + rng.normal(0, 0.01, 200)), start="2024-01-31")})
    gewicht = pd.Series({pd.Timestamp("2024-01-31"): 0.8, pd.Timestamp("2024-05-31"): 0.5})
    e = simuliere([_definition(buch.MischungStrategie("A", gewicht))], m, "2024-01-31", "2024-11-05",
                  kosten=ohne_kosten, regeln=bruchteile, konfig=konfig)["regime"]
    tage = [t.date().isoformat() for t in e.trades.datum]
    # erster Tag, Quartalsbeginn 01.04. (Signal) → 02.04., Gewichtswechsel 31.05. → 03.06., Quartale 01.07. → 02.07., 01.10. → 02.10.
    assert tage == ["2024-02-01", "2024-04-02", "2024-06-03", "2024-07-02", "2024-10-02"]
    anteil = 1 - e.werte["cash"] / e.werte["wert"]
    assert anteil.loc["2024-02-01":"2024-05-31"].between(0.75, 0.85).all()
    assert anteil.loc["2024-06-03":].between(0.45, 0.55).all()


# --- Aktienanteil ---

def test_ziel_gilt_ab_dem_tag_nach_dem_monatsende():
    tage = pd.bdate_range("2024-01-31", "2024-04-30")
    zustand = _zustand({"2024-01-31": False, "2024-02-29": True, "2024-03-29": False})
    an = buch.ziel_an_je_tag(zustand, tage)
    assert an.index[0] == pd.Timestamp("2024-02-01")                         # der Bewertungstag selbst zählt noch nicht
    assert an.loc["2024-02-29"] and not an.loc["2024-03-01"]                 # am Monatsende noch der alte Zustand
    assert not an.loc["2024-03-29"] and an.loc["2024-04-01"]


def test_aktienanteil_je_abschnitt():
    tage = pd.bdate_range("2024-01-31", "2024-04-30")
    zustand = _zustand({"2024-01-31": False, "2024-02-29": True, "2024-03-29": False})
    n_feb, n_mrz = len(pd.bdate_range("2024-02-01", "2024-02-29")), len(pd.bdate_range("2024-03-01", "2024-03-29"))
    assert buch.aktienanteil(zustand, tage, "2024-02-01", "2024-03-29") == pytest.approx(n_feb / (n_feb + n_mrz))
    assert buch.aktienanteil(zustand, tage, "2024-04-01", "2024-04-30") == 1.0
    assert buch.aktienanteil(zustand, tage, "2024-03-01", "2024-03-29") == 0.0
    with pytest.raises(ValueError, match="keine Handelstage"):
        buch.aktienanteil(zustand, tage, "2023-01-01", "2023-12-31")


# --- Kriterien ---

def _reihe(renditen, start="2020-01-01"):
    tage = pd.bdate_range(start, periods=len(renditen) + 1)
    return pd.Series(100 * np.cumprod(np.r_[1.0, 1 + np.asarray(renditen, dtype=float)]), index=tage)


def test_abschnitt_nimmt_den_letzten_wert_davor_als_basis():
    w = _reihe([0.01] * 9)
    teil = buch.abschnitt(w, w.index[5], w.index[8])
    assert teil.index[0] == w.index[4] and teil.index[-1] == w.index[8]
    assert buch.abschnitt(w, w.index[0], w.index[3]).index[0] == w.index[0]


def test_kriterien_a_b_c_je_haelfte():
    rng = np.random.default_rng(11)
    r = rng.normal(0.0004, 0.01, 400)
    r[100:120] = -0.02                                           # Einbruch in Hälfte 1
    r[300:320] = -0.02                                           # Einbruch in Hälfte 2
    kuh = _reihe(r)
    r_v1 = r.copy()
    r_v1[100:120] = 0.0                                          # V1 steht im ersten Einbruch in Kasse, im zweiten nicht
    v1 = _reihe(r_v1)
    mischung = _reihe(r * 0.95)                                  # etwas weniger Aktien: fast derselbe Sharpe wie KuH
    tage = kuh.index
    haelften = [(tage[1], tage[200]), (tage[201], tage[-1])]
    rf = pd.Series(0.0, index=tage)
    k = buch.kriterien_je_haelfte(v1, kuh, mischung, haelften, rf)

    h1, h2 = k.iloc[0], k.iloc[1]
    assert (h1.a, h1.b, h1.c) == (True, True, True)             # höherer Sharpe, Drawdown deutlich kleiner
    assert h1.v1_max_dd > h1.kuh_max_dd and abs(h1.v1_max_dd) <= 0.75 * abs(h1.kuh_max_dd)
    assert bool(h2.a) and not bool(h2.c)                        # gleiche Reihe wie KuH: Sharpe gleich, Drawdown nicht kleiner
    assert h2.v1_sharpe == pytest.approx(h2.kuh_sharpe)


def test_kriterium_c_grenze_ist_relativ_75_prozent():
    kuh = _reihe([0.0, -0.20, 0.0, 0.05])
    rf = pd.Series(0.0, index=kuh.index)
    h = [(kuh.index[1], kuh.index[-1])]
    knapp_ok = _reihe([0.0, -0.15, 0.0, 0.05])                   # −15 % = genau 75 % von −20 %
    knapp_nicht = _reihe([0.0, -0.151, 0.0, 0.05])
    assert bool(buch.kriterien_je_haelfte(knapp_ok, kuh, kuh, h, rf).iloc[0].c) is True
    assert bool(buch.kriterien_je_haelfte(knapp_nicht, kuh, kuh, h, rf).iloc[0].c) is False


def test_sharpe_nicht_bestimmbar_gilt_als_nicht_erfuellt():
    kuh = _reihe([0.01, -0.02, 0.01, 0.005])
    kasse = pd.Series(100.0, index=kuh.index)                    # V1 ganz in Kasse: keine Schwankung
    rf = pd.Series(0.0, index=kuh.index)
    k = buch.kriterien_je_haelfte(kasse, kuh, kasse, [(kuh.index[1], kuh.index[-1])], rf).iloc[0]
    assert bool(k.a) is False and bool(k.b) is False and bool(k.c) is True


# --- Werkzeug tools/backtest_regime.py mit künstlichen Daten (kein Lauf auf echten Daten) ---

def _werkzeug():
    import importlib.util
    from pathlib import Path

    pfad = Path(__file__).parents[2] / "tools" / "backtest_regime.py"
    spec = importlib.util.spec_from_file_location("werkzeug_backtest_regime", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _kuenstlicher_lauf(konfig):
    w = _werkzeug()
    kurse, verlaeufe, rf, haelften = _kuenstliche_eingaben()
    erg = w.rechne(kurse, verlaeufe, rf, konfig=konfig, start="2020-01-31", ende=kurse.index[-1], haelften=haelften, ablage=False)
    return w, erg, verlaeufe["V1"]


def _kuenstliche_eingaben():
    rng = np.random.default_rng(5)
    r = rng.normal(0.0005, 0.008, 1000)
    r[300:340] = -0.012                                          # Einbruch in Hälfte 1
    kurse = kerzen(100 * np.cumprod(1 + r), start="2020-01-31")
    enden = pd.DatetimeIndex(pd.Series(kurse.index, index=kurse.index).groupby(kurse.index.to_period("M")).max().to_numpy())
    aus = pd.Series(False, index=enden, dtype=object)
    aus.loc["2021-03-31":"2021-05-31"] = True                    # V1 steht im Einbruch in Kasse
    leer = pd.Series([None] * len(enden), index=enden, dtype=object)
    verlauf = pd.DataFrame({"trend_aus": aus, "kurve_aus": aus, "kredit_aus": leer.fillna(False), "arbeit_aus": leer.fillna(False),
                            "roh_aus": aus, "risiko_aus": aus})
    verlaeufe = {"V1": verlauf, "D1": verlauf.assign(risiko_aus=False)}
    haelften = [(pd.Timestamp("2020-02-03"), pd.Timestamp("2021-12-31")), (pd.Timestamp("2022-01-01"), kurse.index[-1])]
    rf = pd.Series([0.0], index=[pd.Timestamp("2019-01-01")])
    return kurse, verlaeufe, rf, haelften


def test_werkzeug_rechnet_v1_zwilling_und_mischung(konfig):
    w, erg, _ = _kuenstlicher_lauf(konfig)
    k = erg["kriterien"]
    assert list(k.haelfte) == [1, 2]
    assert 0.8 < erg["anteile"][0] < 1.0 and erg["anteile"][1] == 1.0
    assert bool(k.iloc[0].c) and k.iloc[0].v1_max_dd > k.iloc[0].kuh_max_dd       # dem Einbruch ausgewichen
    # Hälfte 2 ohne Wechsel: V1 hält dieselben Aktien wie zuvor, Drawdown nicht kleiner als Kaufen und Halten
    assert not bool(k.iloc[1].c)
    assert set(erg["je_haelfte"].portfolio) == {"V1", "D1", "Kaufen und Halten", "Mischung"}
    v1 = erg["laeufe"]["V1"].ergebnisse["regime_V1"]
    assert [int(t.richtung) for t in v1.trades.itertuples()] == [1, -1, 1]
    assert v1.trades.datum.iloc[1] == pd.Timestamp("2021-04-01")                 # Bewertung 31.03., Order am nächsten Handelstag
    assert erg["gesamt"].loc["V1", "steuern_gezahlt"] >= 0


def test_vergleich_mit_ablage_findet_gleichheit_und_abweichung(konfig, tmp_path):
    """Befund 3 (16.11.2026): Prüfung, ob ein Lauf frühere Ablagen trifft (Werte, Trades, Kriterien)."""
    w = _werkzeug()
    kurse, verlaeufe, rf, haelften = _kuenstliche_eingaben()
    abgelegt = w.rechne(kurse, verlaeufe, rf, konfig=konfig, start="2020-01-31", ende=kurse.index[-1], haelften=haelften,
                        ablage_wurzel=tmp_path)
    ordner = [l.pfad for l in [*abgelegt["laeufe"].values(), abgelegt["lauf_mischung"]]]
    abgelegt["kriterien"].to_csv(abgelegt["laeufe"]["V1"].pfad / "kriterien.csv", index=False)
    erneut = w.rechne(kurse, verlaeufe, rf, konfig=konfig, start="2020-01-31", ende=kurse.index[-1], haelften=haelften, ablage=False)
    geprueft, abweichungen = w.vergleiche_mit_ablage(erneut, ordner)
    assert abweichungen == [] and len(geprueft) == 7                     # V1, D1, Mischung je mit Zwilling, Kriterien
    datei = abgelegt["laeufe"]["V1"].pfad / "regime_V1" / "werte.csv"
    werte = pd.read_csv(datei, index_col="datum")
    werte.iloc[-1, werte.columns.get_loc("wert_nach_steuern")] *= 1.001
    werte.to_csv(datei)
    _, abweichungen = w.vergleiche_mit_ablage(erneut, ordner)
    assert len(abweichungen) == 1 and abweichungen[0].startswith("regime_V1.wert_nach_steuern")


def test_werkzeug_bricht_bei_anderer_erster_bewertung_ab(konfig):
    w = _werkzeug()
    kurse = kerzen([100.0] * 300, start="2020-01-31")
    zustand = pd.Series({pd.Timestamp("2020-03-31"): False}, dtype=object)
    with pytest.raises(RuntimeError, match="erste Bewertung"):
        w.rechne(kurse, {"V1": pd.DataFrame({"risiko_aus": zustand})}, pd.Series([0.0], index=[pd.Timestamp("2019-01-01")]),
                 konfig=konfig, start="2020-01-31", ende=kurse.index[-1], ablage=False)


def test_bericht_ohne_gesamturteil_mit_festlegung_und_verzerrung(konfig):
    w, erg, verlauf = _kuenstlicher_lauf(konfig)
    text = w.bericht_text(erg, verlauf, festlegung="abc1234", git="def5678", befunde=["Datenhinweis X"])
    assert "Kein Gesamturteil" in text and "`abc1234`" in text and "Kasse zu 0 %" in text and "Datenhinweis X" in text
    assert "Gesamt: bestanden" not in text and "nicht bestanden" not in text.lower().replace("datenprüfung nicht bestanden", "")
    assert "3 Wechsel" not in text and "2 Wechsel nach der ersten Bewertung" in text


def test_festlegung_muss_existieren_und_unveraendert_sein():
    from pathlib import Path

    w = _werkzeug()
    wurzel = Path(__file__).parents[2]
    assert "gibt es nicht" in w.pruefe_festlegung("0000000000", wurzel)
    assert "gibt es nicht" in w.pruefe_festlegung("", wurzel)
    # ein alter Commit, in dem es docs/REGIME.md noch nicht gab: seitdem geändert
    assert "geändert" in w.pruefe_festlegung("6bcfb30", wurzel)
