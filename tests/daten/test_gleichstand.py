"""Sechste Datenkorrektur (Jakob 24.11.2026, docs/FUNDAMENTAL.md): bei gleichem filed gewinnt das spätere Stichtagsdatum,
dann die größere accn, dann der größere Wert – unabhängig von Zeilenfolge und Länge der Tabelle.

Die Fälle sind echte Einreichungen aus den SEC-Daten (Deckblatt dei:EntityCommonStockSharesOutstanding gegen Bilanz
us-gaap:CommonStockSharesOutstanding, gleiche accn, gleiches filed); INTU aus dem Betriebsstand (docs/TRESOR_BEKANNT.md Nr. 13).
"""
import itertools

import numpy as np
import pandas as pd
import pytest

from tradingbot.daten.index_nachbau import _aktien_je_messtag, marktwerte_aus_streubesitz
from tradingbot.daten.sec import gleichstand_ordnen, reihe_bekannt_ab
from tradingbot.engines.fundamental.multiples import aktienzahl_waehlen, marktwert_am

BILANZ, DECKBLATT = "CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"

# (Symbol, accn, filed, (Stichtag Bilanz, Wert), (Stichtag Deckblatt, Wert))
FAELLE = [
    ("INTU", "0000896878-26-000037", "2026-09-09", ("2026-07-31", 268_384_000.0), ("2026-08-31", 267_236_000.0)),
    ("CTXS", "0000877890-21-000051", "2021-02-08", ("2020-12-31", 321_964_000.0), ("2021-02-01", 122_963_727.0)),
    ("EXE", "0000895126-20-000138", "2020-08-10", ("2020-04-10", 1_957_000_000.0), ("2020-08-07", 9_780_335.0)),
    ("PCG", "0001004980-17-000023", "2017-11-02", ("2017-09-30", 513_773_072_000_000.0), ("2017-10-24", 514_422_806.0)),
    ("GAS", "0001004155-16-000202", "2016-07-26", ("2016-06-30", 120_741_810.0), ("2016-07-25", 100.0)),
]


def _tabelle(fall, davor: int = 0) -> pd.DataFrame:
    """Aktienzahlen wie aus kennzahl_jahreswerte (Index = Stichtag), mit `davor` älteren Quartalen (längere Tabelle)."""
    _, accn, filed, (e_b, w_b), (e_d, w_d) = fall
    zeilen = [(pd.Timestamp(e_b), w_b, BILANZ, pd.Timestamp(filed), accn), (pd.Timestamp(e_d), w_d, DECKBLATT, pd.Timestamp(filed), accn)]
    basis = pd.Timestamp(e_b)
    for i in range(1, davor + 1):                                  # ältere Einreichungen, je zwei Werte mit gleichem filed
        f = basis - pd.DateOffset(months=3 * i) + pd.Timedelta(days=35)
        zeilen += [(basis - pd.DateOffset(months=3 * i), w_d * (1 + i / 1000), BILANZ, f, f"alt-{i:03d}"),
                   (f - pd.Timedelta(days=7), w_d * (1 + i / 1000) * 0.999, DECKBLATT, f, f"alt-{i:03d}")]
    t = pd.DataFrame(zeilen, columns=["ende", "wert", "konzept", "filed", "accn"]).set_index("ende").sort_index()
    return t


@pytest.mark.parametrize("fall", FAELLE, ids=[f[0] for f in FAELLE])
def test_deckblatt_mit_spaeterem_stichtag_gewinnt(fall):
    wert_deckblatt = fall[4][1]
    t = _tabelle(fall)
    assert gleichstand_ordnen(t).iloc[-1]["wert"] == wert_deckblatt
    r = reihe_bekannt_ab(t)
    assert r.index[-1] == pd.Timestamp(fall[2]) + pd.Timedelta(days=1) and r.iloc[-1] == wert_deckblatt
    # Korrekturweg (multiples.aktienzahl_waehlen): dieselbe Wahl
    tag = pd.Timestamp(fall[2]) + pd.Timedelta(days=5)
    wahl, _ = aktienzahl_waehlen(tag, t[["wert", "filed", "accn"]], None, 15)
    assert wahl[0] == wert_deckblatt and wahl[1] == pd.Timestamp(fall[4][0])


@pytest.mark.parametrize("fall", FAELLE, ids=[f[0] for f in FAELLE])
def test_unabhaengig_von_zeilenfolge_und_laenge(fall):
    """Früher hing die Wahl an der Länge (quicksort ab 16 Elementen) und der Zeilenfolge der Datei."""
    rng = np.random.default_rng(24)
    for davor in (0, 5, 20, 40):
        t = _tabelle(fall, davor)
        erwartet = reihe_bekannt_ab(t)
        for _ in range(10):
            gemischt = t.iloc[rng.permutation(len(t))]
            r = reihe_bekannt_ab(gemischt)
            assert r.index.equals(erwartet.index) and np.array_equal(r.to_numpy(), erwartet.to_numpy())
            assert r.loc[:pd.Timestamp(fall[2]) + pd.Timedelta(days=1)].iloc[-1] == fall[4][1]


def test_marktwert_am_nimmt_deckblatt_und_gas_faellt_heraus():
    tage = pd.bdate_range("2016-07-20", "2016-08-05")
    kurs = pd.Series(50.0, index=tage)
    gas = next(f for f in FAELLE if f[0] == "GAS")
    mw, grund = marktwert_am("2016-08-01", kurs, reihe_bekannt_ab(_tabelle(gas)), None)
    assert mw is None and grund                          # 50 × 100 Aktien: unplausibel, Firma fällt am Stichtag heraus
    ctxs = next(f for f in FAELLE if f[0] == "CTXS")
    tage = pd.bdate_range("2021-02-01", "2021-02-20")
    mw, grund = marktwert_am("2021-02-15", pd.Series(130.0, index=tage), reihe_bekannt_ab(_tabelle(ctxs)), None)
    assert grund is None and mw == pytest.approx(130.0 * 122_963_727.0)


def test_gleicher_stichtag_dann_accn_dann_wert():
    t = pd.DataFrame({"ende": pd.to_datetime(["2024-03-31"] * 3), "wert": [10.0, 30.0, 20.0],
                      "filed": pd.to_datetime(["2024-05-01"] * 3), "accn": ["a-2", "a-1", "a-2"]}).set_index("ende")
    for perm in itertools.permutations(range(3)):
        assert gleichstand_ordnen(t.iloc[list(perm)]).iloc[-1]["wert"] == 20.0      # accn a-2, dann größerer Wert
    ohne_accn = t.drop(columns="accn")
    assert gleichstand_ordnen(ohne_accn).iloc[-1]["wert"] == 30.0                    # ohne accn: größerer Wert
    # früheres filed bleibt davor, auch mit späterem Stichtag
    t2 = pd.DataFrame({"wert": [5.0, 6.0], "filed": pd.to_datetime(["2024-06-01", "2024-05-01"]), "accn": ["x", "y"]},
                      index=pd.to_datetime(["2024-01-31", "2024-05-31"]))
    assert list(gleichstand_ordnen(t2)["wert"]) == [6.0, 5.0]


def test_werte_ueber_stichtag_zugeordnet_nicht_ueber_position():
    """aktien_splitbereinigt sortiert nach Stichtag; die Zuordnung darf nicht an der Position hängen."""
    t = _tabelle(FAELLE[1], 3).iloc[::-1]
    bereinigt = (t["wert"] * 2).sort_index()
    r = reihe_bekannt_ab(t, bereinigt)
    assert r.iloc[-1] == 2 * FAELLE[1][4][1]


def test_aktien_je_messtag_firma_und_vorgaenger():
    """index_nachbau: gleicher Messtag bei Firma und Vorgänger-CIK → späteres filed, dann größere accn, dann Wert."""
    t = pd.DataFrame({"wert": [100.0, 101.0, 50.0], "filed": pd.to_datetime(["2020-02-01", "2020-03-01", "2020-02-01"]),
                      "accn": ["v-1", "f-1", "v-1"]}, index=pd.to_datetime(["2019-12-31", "2019-12-31", "2019-06-30"]))
    for perm in itertools.permutations(range(3)):
        a = _aktien_je_messtag(t.iloc[list(perm)])
        assert list(a.index) == list(pd.to_datetime(["2019-06-30", "2019-12-31"])) and list(a) == [50.0, 101.0]
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2019-12-31", "2019-12-31"]))
    assert list(_aktien_je_messtag(s)) == [2.0]                                      # Reihe: zuletzt übergebener


def test_streubesitz_gleiches_filed_spaeterer_messtag_gilt():
    tage = pd.bdate_range("2012-06-01", "2013-03-29")
    schluss = pd.DataFrame({1: pd.Series(100.0, index=tage)})
    reihe = pd.DataFrame({"wert": [69.4e9, 61.9e9], "filed": pd.to_datetime(["2013-02-14", "2013-02-14"]), "accn": ["m", "m"]},
                         index=pd.to_datetime(["2012-06-29", "2012-06-30"]))
    for r in (reihe, reihe.iloc[::-1]):
        mw = marktwerte_aus_streubesitz(schluss, {1: r})
        assert mw.loc["2013-03-01", 1] == pytest.approx(61.9e9)                     # Messtag 30.06. gewinnt


def test_echte_tabelle_ctxs_jeder_einreichungstag_nach_regel():
    """Vollständige Aktienzahl-Tabelle von CTXS (Entwicklungs-Cache, 107 Zeilen, Einreichungen 2009–2022). Die alte
    Rechnung (`sort_index()` nach filed + 1) wählte hier an 10 Tagen die Bilanzzahl statt des Deckblatts (Messung
    24.11.2026), z.B. am 10.11.2010 276,3 Mio. statt 187,8 Mio."""
    from pathlib import Path
    t = pd.read_csv(Path(__file__).with_name("daten_ctxs_aktien.csv"), parse_dates=["ende", "filed"]).set_index("ende")
    assert len(t) == 107
    erwartet = {f + pd.Timedelta(days=1): g.loc[g.index.max(), "wert"] for f, g in t.groupby("filed")}   # späterer Stichtag
    rng = np.random.default_rng(24)
    for folge in [t, t.iloc[::-1]] + [t.iloc[rng.permutation(len(t))] for _ in range(10)]:
        r = reihe_bekannt_ab(folge)
        for tag, wert in erwartet.items():
            assert r.loc[:tag].iloc[-1] == wert, tag
    assert r.loc[:pd.Timestamp("2010-11-10")].iloc[-1] == 187_774_447.0
