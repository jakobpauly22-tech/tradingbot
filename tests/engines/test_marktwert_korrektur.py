"""Datenkorrektur Marktwert, Teil b (Jakob 13.11.2026): Abspaltungen nicht als Split in der Aktienzahl, Ersatz-Aktienzahl,
Kursreihe E. I. du Pont gekappt.

Nachgestellt: CMCSA (Deckblatt-Zahl von 2009, Split 2017, Abspaltung Versant 2026), Abspaltung nach dem Stichtag,
Split zwischen Messtag und Stichtag, kombiniert (LDOS 2013: Abspaltung und Reverse-Split 1:4), ungeklärtes Ereignis,
Ersatz-Aktienzahl und Ersatz zu alt, Index-Nachbau, DD-Kappung mit Delisting-Regel, Zuschaltung ab 04.01.2027."""
import pandas as pd
import pytest

from tradingbot.daten import kapitalmassnahmen_historie as kh
from tradingbot.daten.delisting import delisting_grund_mit_korrektur
from tradingbot.daten.index_nachbau import aktien_splitbereinigt, marktwerte_aus_streubesitz
from tradingbot.engines.fundamental import aktienzahl as az
from tradingbot.engines.fundamental.multiples import marktwert_am, marktwert_korrigiert

BASIC = "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic"


@pytest.fixture
def ohne_tresor(monkeypatch):
    """Betriebsfälle mit Daten ab 2025 (wie im Betriebsmodus)."""
    from tradingbot.backtest import tresor
    monkeypatch.setattr(tresor, "datengrenze", lambda konfig=None: None)


def _kurse(von, bis, ereignisse=(), close=100.0):
    tage = pd.bdate_range(von, bis)
    k = pd.DataFrame({"close": close, "split": 0.0}, index=tage)
    for tag, f in ereignisse:
        k.loc[pd.Timestamp(tag), "split"] = f
    return k


def _liste(*zeilen):
    """zeilen: (datum, art, split_faktor, faktor_kursreihe)."""
    t = pd.DataFrame([{"datum": pd.Timestamp(d), "art": a, "split_faktor": s, "faktor_kursreihe": f, "geprueft": True, "quelle": "Test"}
                      for d, a, s, f in zeilen])
    return t.set_index("datum")


def _aktien(*zeilen):
    """zeilen: (Messtag, wert, filed)."""
    return pd.DataFrame({"wert": [w for _, w, _ in zeilen], "filed": [pd.Timestamp(f) for *_, f in zeilen]},
                        index=pd.DatetimeIndex([pd.Timestamp(m) for m, *_ in zeilen], name="ende"))


def _fakt(start, ende, wert, filed, rang=0, form="10-Q"):
    return {"konzept": BASIC if rang == 0 else "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", "rang": rang,
            "start": pd.Timestamp(start), "ende": pd.Timestamp(ende), "wert": wert, "filed": pd.Timestamp(filed), "form": form, "accn": filed}


# --- Korrekturfaktor K(d, T) ----------------------------------------------------------------------------------------------
def test_korrektur_abspaltung_zwischen_messtag_und_stichtag():
    k = _kurse("2020-01-01", "2020-12-31", [("2020-06-01", 1.25)])
    faktor, offen = kh.korrektur(k["split"], _liste(("2020-06-01", "abspaltung", 1.0, 1.25)), "2020-03-01", "2020-09-01")
    assert faktor == pytest.approx(1 / 1.25) and offen == []


def test_korrektur_split_unveraendert_und_nach_stichtag_nicht_gezaehlt():
    k = _kurse("2020-01-01", "2020-12-31", [("2020-06-01", 3.0), ("2020-10-01", 1.25)])
    liste = _liste(("2020-06-01", "split", 3.0, 3.0), ("2020-10-01", "abspaltung", 1.0, 1.25))
    assert kh.korrektur(k["split"], liste, "2020-03-01", "2020-09-01") == (1.0, [])       # Abspaltung erst nach T
    assert kh.korrektur(k["split"], liste, "2020-07-01", "2020-12-31")[0] == pytest.approx(0.8)


def test_korrektur_kombiniert_ldos():
    """LDOS 30.09.2013: Kursfaktor 0,405, Aktienzahl 1:4 (Split-Faktor 0,25, von Jakob geprüft)."""
    k = _kurse("2013-01-01", "2013-12-31", [("2013-09-30", 0.405)])
    faktor, _ = kh.korrektur(k["split"], _liste(("2013-09-30", "kombiniert", 0.25, 0.405)), "2013-06-01", "2013-12-01")
    assert faktor == pytest.approx(0.25 / 0.405)


def test_korrektur_ungeklaert_behaelt_kursfaktor_und_meldet():
    k = _kurse("2020-01-01", "2020-12-31", [("2020-06-01", 2.0), ("2020-07-01", 1.1)])
    faktor, offen = kh.korrektur(k["split"], _liste(("2020-06-01", "unklar", None, 2.0)), "2020-01-01", "2020-12-31")
    assert faktor == 1.0
    assert [(o["art"], o["faktor_kursreihe"]) for o in offen] == [("unklar", 2.0), ("nicht in der Liste", 1.1)]


def test_korrektur_ordnet_neues_ereignis_automatisch_ein():
    """Betrieb: Ereignis nicht in der Liste, SEC zeigt dieselbe Periode davor und danach gleich → Abspaltung."""
    k = _kurse("2020-01-01", "2020-12-31", [("2020-06-01", 1.2)])
    fakten = pd.DataFrame([_fakt("2020-01-01", "2020-03-31", 100e6, "2020-05-01"),
                           _fakt("2020-01-01", "2020-03-31", 100e6, "2020-08-01")])
    faktor, offen = kh.korrektur(k["split"], None, "2020-01-01", "2020-12-31", fakten=fakten)
    assert faktor == pytest.approx(1 / 1.2) and offen == []


def test_korrektur_reihe_stufenweise():
    k = _kurse("2020-01-01", "2020-12-31", [("2020-06-01", 1.25)])
    reihe = kh.korrektur_reihe(k["split"], _liste(("2020-06-01", "abspaltung", 1.0, 1.25)), "2020-01-01", k.index)
    assert reihe.loc["2020-05-29"] == 1.0 and reihe.loc["2020-06-01"] == pytest.approx(0.8) and reihe.iloc[-1] == pytest.approx(0.8)


# --- Marktwert ------------------------------------------------------------------------------------------------------------
def test_ohne_ereignis_wie_bisher():
    k = _kurse("2019-01-01", "2020-12-31", [("2020-10-01", 2.0)], close=50.0)
    a = _aktien(("2020-01-31", 1e9, "2020-02-15"))
    alt, _ = marktwert_am("2020-06-01", k["close"], pd.Series(aktien_splitbereinigt(a["wert"], k["split"]).to_numpy(),
                                                              index=a["filed"] + pd.Timedelta(days=1)), None)
    neu = marktwert_korrigiert("2020-06-01", k, a, None, ereignisse=_liste(("2020-10-01", "split", 2.0, 2.0)))
    assert neu["marktwert"] == pytest.approx(alt) == pytest.approx(50 * 1e9 * 2)
    assert neu["quelle"] == "Deckblatt" and neu["korrektur"] == 1.0


def test_abspaltung_nach_stichtag_bleibt():
    """Kurs bei T ist um die spätere Abspaltung bereinigt: Faktor nach T gehört weiter in die Aktienzahl."""
    k = _kurse("2019-01-01", "2020-12-31", [("2020-10-01", 1.25)], close=80.0)
    neu = marktwert_korrigiert("2020-06-01", k, _aktien(("2020-01-31", 1e9, "2020-02-15")), None,
                               ereignisse=_liste(("2020-10-01", "abspaltung", 1.0, 1.25)))
    assert neu["marktwert"] == pytest.approx(80 * 1e9 * 1.25)


def test_cmcsa_nachgestellt(ohne_tresor):
    """CMCSA: Deckblatt-Zahl von 2009 (danach nur noch Gattungen einzeln), Split 2:1 2017, Abspaltung Versant 05.01.2026
    (Kursfaktor 1,067). Bisher: 2009-Zahl × 2 × 1,067. Korrigiert: Ersatz (Basic Q3 2026, nach dem Split und der Abspaltung
    gemeldet), ohne den Abspaltungsfaktor."""
    k = _kurse("2009-01-01", "2026-11-12", [("2017-02-21", 2.0), ("2026-01-05", 1.067)], close=27.0)
    liste = _liste(("2017-02-21", "split", 2.0, 2.0), ("2026-01-05", "abspaltung", 1.0, 1.067))
    deckblatt = _aktien(("2009-10-20", 2.8e9, "2009-10-29"))
    fakten = pd.DataFrame([_fakt("2026-07-01", "2026-09-30", 3.70e9, "2026-10-30"),
                           _fakt("2026-01-01", "2026-09-30", 3.72e9, "2026-10-30"),          # YTD: kürzere Periode gewinnt
                           _fakt("2026-07-01", "2026-09-30", 3.75e9, "2026-10-30", rang=1)])  # Diluted: nicht Basic
    tag = "2026-11-12"
    alt, _ = marktwert_am(tag, k["close"], pd.Series(aktien_splitbereinigt(deckblatt["wert"], k["split"]).to_numpy(),
                                                     index=deckblatt["filed"] + pd.Timedelta(days=1)), None)
    assert alt == pytest.approx(27 * 2.8e9 * 2 * 1.067)
    neu = marktwert_korrigiert(tag, k, deckblatt, None, ereignisse=liste, ersatz_fakten=fakten)
    assert neu["quelle"].startswith("Ersatz") and neu["aktien_filed"] == pd.Timestamp("2026-10-30")
    assert neu["marktwert"] == pytest.approx(27 * 3.70e9)
    # gleiche Deckblatt-Zahl, aber frisch: Abspaltung zwischen Messtag und T fällt heraus, Split nicht
    frisch = marktwert_korrigiert(tag, k, _aktien(("2025-10-20", 3.8e9, "2025-10-30")), None, ereignisse=liste)
    assert frisch["quelle"] == "Deckblatt" and frisch["marktwert"] == pytest.approx(27 * 3.8e9) and frisch["korrektur"] == pytest.approx(1 / 1.067)


def test_ersatz_zu_alt_kein_marktwert():
    k = _kurse("2018-01-01", "2020-12-31", close=10.0)
    fakten = pd.DataFrame([_fakt("2018-07-01", "2018-09-30", 1e9, "2018-10-30")])
    neu = marktwert_korrigiert("2020-06-01", k, _aktien(("2018-01-31", 1e9, "2018-02-15")), None, ersatz_fakten=fakten)
    assert neu["marktwert"] is None and "älter als 15 Monate" in neu["grund"]
    leer = marktwert_korrigiert("2020-06-01", k, None, None)
    assert leer["marktwert"] is None and leer["grund"] == "keine Aktienzahl bekannt"


def test_ersatz_wenn_deckblatt_fehlt_und_point_in_time():
    k = _kurse("2019-01-01", "2020-12-31", close=10.0)
    fakten = pd.DataFrame([_fakt("2020-01-01", "2020-03-31", 2e9, "2020-05-01"),
                           _fakt("2020-04-01", "2020-06-30", 2.1e9, "2020-08-01")])                # erst nach dem Stichtag bekannt
    neu = marktwert_korrigiert("2020-06-01", k, None, None, ersatz_fakten=fakten)
    assert neu["marktwert"] == pytest.approx(10 * 2e9) and "2020-03-31" in neu["quelle"]


def test_streubesitz_fortschreibung_ohne_abspaltung():
    """Plausibilität: Streubesitz F_e · C_T / C_e wird bei einer Abspaltung zwischen e und T ebenfalls korrigiert."""
    k = _kurse("2019-01-01", "2020-12-31", [("2020-06-01", 1.5)], close=100.0)
    sb = pd.DataFrame({"wert": [1.4e11], "filed": [pd.Timestamp("2020-02-15")]}, index=pd.DatetimeIndex([pd.Timestamp("2019-06-28")]))
    liste = _liste(("2020-06-01", "abspaltung", 1.0, 1.5))
    neu = marktwert_korrigiert("2020-09-01", k, _aktien(("2020-01-31", 1e9, "2020-02-15")), sb, ereignisse=liste)
    # Kurs bereinigt konstant 100 (echt 150 vor der Abspaltung): MW = 100 · 1e9 (bisher · 1,5). Streubesitz fortgeschrieben
    # 1,4e11 / 1,5 = 93 % des Marktwerts; ohne Korrektur der Fortschreibung wären es 140 % (verworfen)
    assert neu["marktwert"] == pytest.approx(100 * 1e9) and neu["grund"] is None


# --- Index-Nachbau ----------------------------------------------------------------------------------------------------------
def test_index_nachbau_streubesitz_mit_korrektur():
    k = _kurse("2020-01-01", "2020-12-31", [("2020-06-01", 1.25)])
    sb = {1: pd.DataFrame({"wert": [1e10], "filed": [pd.Timestamp("2020-02-01")]}, index=pd.DatetimeIndex([pd.Timestamp("2020-01-15")]))}
    schluss = pd.DataFrame({1: k["close"]})
    alt = marktwerte_aus_streubesitz(schluss, sb)
    neu = marktwerte_aus_streubesitz(schluss, sb, {1: (k["split"], _liste(("2020-06-01", "abspaltung", 1.0, 1.25)))})
    assert alt.loc["2020-05-29", 1] == neu.loc["2020-05-29", 1] == pytest.approx(1e10)
    assert neu.loc["2020-07-01", 1] == pytest.approx(1e10 / 1.25) and alt.loc["2020-07-01", 1] == pytest.approx(1e10)


# --- Liste, Flex, Zuschaltung ---------------------------------------------------------------------------------------------
def test_liste_aus_der_konfiguration():
    e = kh.lade_ereignisse()
    ldos = e[1336920].loc[pd.Timestamp("2013-09-30")]
    assert ldos["art"] == "kombiniert" and ldos["split_faktor"] == pytest.approx(0.25)
    assert (e[30554].loc[pd.Timestamp("2017-09-01"):, "art"] == "nicht_zugehoerig").all()


def test_flex_split_hat_vorrang():
    k = _kurse("2025-01-01", "2025-12-31", [("2025-06-10", 15.0)])
    e = kh.ereignisse_mit_flex(_liste(("2025-06-10", "unklar", None, 15.0)), k, [("2025-06-09", 15.0)])
    assert e.loc[pd.Timestamp("2025-06-10"), "art"] == "split" and e.loc[pd.Timestamp("2025-06-10"), "quelle"] == "Flex"
    assert len(e) == 1


def test_zuschaltung_ab_januar_2027():
    konfig = {"marktwert_korrektur": {"ab": "2027-01-04"}}
    assert not az.marktwert_korrektur_aktiv("2027-01-03", konfig)
    assert az.marktwert_korrektur_aktiv("2027-01-04", konfig)
    assert az.marktwert_korrektur_aktiv("2027-01-04")                   # config/fundamental.yaml


# --- Dritte Datenkorrektur: Kursreihe E. I. du Pont ------------------------------------------------------------------------
def test_dd_kappung_und_delisting_nach_cik():
    from tradingbot.daten.sp500_nachbau import kursreihen_ende
    from tradingbot.konfiguration import lade_konfiguration

    assert kursreihen_ende()[30554] == pd.Timestamp("2017-08-31")
    korrekturen = lade_konfiguration("universum_korrekturen")["delisting"]
    leer = pd.DataFrame(columns=["datum", "form", "items"]).astype({"datum": "datetime64[ns]"})
    grund, beleg = delisting_grund_mit_korrektur("DD", leer, "2017-08-31", None, korrekturen, cik=30554)
    assert grund == "uebernahme" and "8-K12B" in beleg
    assert delisting_grund_mit_korrektur("DD", leer, "2024-06-28", None, korrekturen, cik=1666700)[0] == "unbekannt"
    assert delisting_grund_mit_korrektur("TFCF", leer, "2019-03-19", None, korrekturen, cik=1308161)[0] == "uebernahme"
