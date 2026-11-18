"""Befund 19, Schritt 3 (Plan Jakob 17.11.2026, Entscheidungen 18.11.2026): eigenes Universum und eigener Kursstatus
des Betriebs, Übernahme über Ticker und CIK, neue Mitglieder nach Variante (a), Betriebskorrekturen, Wächter."""
from __future__ import annotations

import inspect
import os

import pandas as pd
import pytest

from tradingbot.betrieb import universum_betrieb as ub
from tradingbot.daten.kursstatus import UniversumVerschoben
from tradingbot.daten.sp500_nachbau import pruefe_zuordnung
from tradingbot.daten.universum import betriebskorrekturen_anwenden


def _uni(zeilen):
    """zeilen: (ticker, name, von, bis, cik)"""
    t = pd.DataFrame(zeilen, columns=["ticker", "name", "von", "bis", "cik"])
    t["von"], t["bis"] = pd.to_datetime(t["von"]), pd.to_datetime(t["bis"])
    t["cik"] = t["cik"].astype("Int64")
    return t


def _basis(zeilen):
    """Wie kursstatus.csv gelesen: (index, ticker, von, bis, symbol, gueltig)."""
    t = pd.DataFrame(zeilen, columns=["index", "ticker", "von", "bis", "symbol", "gueltig"])
    t[["von", "bis"]] = t[["von", "bis"]].replace("", float("nan"))
    t["quelle"] = "yfinance"
    return t


# --- Wikipedia-Seiten: einmalige Übernahme -----------------------------------------------------------------------------
def test_seiten_einmal_uebernommen_mit_zeitstempel(tmp_path):
    quelle, ziel = tmp_path / "q", tmp_path / "z"
    quelle.mkdir()
    for name in ub.SEITEN:
        (quelle / name).write_bytes(b"alt")
        os.utime(quelle / name, (1_700_000_000, 1_700_000_000))
    info = ub.seiten_uebernehmen(quelle, ziel)
    assert info["neu"] and sorted(info["dateien"]) == sorted(ub.SEITEN)
    assert all((ziel / n).stat().st_mtime == 1_700_000_000 for n in ub.SEITEN)          # Wochenrhythmus bleibt
    (quelle / ub.SEITEN[0]).write_bytes(b"neu")                                          # spätere Änderung der Quelle
    assert not ub.seiten_uebernehmen(quelle, ziel)["neu"]
    assert (ziel / ub.SEITEN[0]).read_bytes() == b"alt"


# --- Betriebskorrekturen -----------------------------------------------------------------------------------------------
def _cday_eintrag():
    return {"aktion": "beenden", "ticker": "CDAY", "name": "Ceridian", "bis": "2024-02-01", "quelle": "Test"}


def test_betriebskorrektur_greift():
    t, meldungen = betriebskorrekturen_anwenden(_uni([("CDAY", "Ceridian", "2021-09-20", None, 1725057)]).assign(hinweis=None),
                                                [_cday_eintrag()])
    assert t.at[0, "bis"] == pd.Timestamp("2024-02-01") and meldungen == []


def test_betriebskorrektur_ohne_treffer_ist_meldung_kein_fehler():
    t, meldungen = betriebskorrekturen_anwenden(_uni([("CDAY", "Ceridian", "2021-09-20", "2024-02-01", 1725057)]).assign(hinweis=None),
                                                [_cday_eintrag()])
    assert len(meldungen) == 1 and "greift nicht mehr" in meldungen[0]


def test_betriebskorrektur_mehrdeutig_bricht_laut_ab():
    u = _uni([("CDAY", "Ceridian", "2021-09-20", None, 1), ("CDAY", "Ceridian", "2022-01-03", None, 2)]).assign(hinweis=None)
    with pytest.raises(ValueError, match="2 Treffer"):
        betriebskorrekturen_anwenden(u, [_cday_eintrag()])


def test_betriebskorrektur_steht_in_der_konfiguration():
    from tradingbot.konfiguration import lade_konfiguration

    eintraege = lade_konfiguration("universum_korrekturen")["betrieb_korrekturen"]
    assert [(e["ticker"], e["name"], str(e["bis"])) for e in eintraege] == [("CDAY", "Ceridian", "2024-02-01")]


# --- Zuordnung der Basis: Schlüssel, sonst Ticker und CIK ---------------------------------------------------------------
def test_uebernahme_ueber_ticker_und_cik():
    """XEC/IR wie am 16.11.2026: Datum um einen Tag verschoben, eine Zeile davor eingefügt."""
    basis = _basis([(0, "AAA", "", "", "AAA", True), (1, "XEC", "2014-06-20", "2020-03-02", "XEC", True),
                    (2, "IR", "2020-03-02", "", "IR", True)])
    cik = {0: 10, 1: 20, 2: 30}
    u = _uni([("NEU", "Neu", None, "2026-02-09", 99), ("AAA", "A", None, None, 10),
              ("XEC", "Cimarex", "2014-06-20", "2020-03-03", 20), ("IR", "Ingersoll", "2020-03-03", None, 30)])
    s, meldungen = ub.ordne_basis_zu(u, basis, cik)
    assert list(s.index) == [1, 2, 3] and list(s["herkunft"]) == ["basis", "uebernommen", "uebernommen"]
    assert list(s["index_csv"]) == [0, 1, 2]
    assert len(meldungen) == 2 and "XEC 2014-06-20…2020-03-02 → 2014-06-20…2020-03-03" in meldungen[0]
    pruefe_zuordnung(u, s)                                   # Schlüssel im Status sind die des Betriebsstands


@pytest.mark.parametrize("zeilen, anzahl", [
    ([("XEC", "Cimarex", "2014-06-20", "2020-03-03", 21)], 0),                                       # andere CIK
    ([("XEC", "Cimarex", "2021-01-04", None, 20)], 0),                                               # keine Überlappung
    ([("XEC", "Cimarex", "2014-06-20", "2018-01-02", 20), ("XEC", "Cimarex", "2018-01-02", "2020-03-03", 20)], 2),
])
def test_uebernahme_ohne_eindeutigen_treffer_bricht_laut_ab(zeilen, anzahl):
    basis = _basis([(0, "XEC", "2014-06-20", "2020-03-02", "XEC", True)])
    with pytest.raises(UniversumVerschoben, match=f"{anzahl} passende Mitgliedschaften"):
        ub.ordne_basis_zu(_uni(zeilen), basis, {0: 20})


# --- Neue Mitglieder (Variante a) --------------------------------------------------------------------------------------
@pytest.fixture
def betrieb_tmp(tmp_path, monkeypatch):
    eingefroren = _uni([("AAA", "A", None, None, 10), ("KVUE", "Kenvue", "2023-08-25", None, 30)])
    monkeypatch.setattr(ub, "ordner", lambda: tmp_path)
    monkeypatch.setattr("tradingbot.daten.universum.lade_eingefrorenen_stand", lambda: (eingefroren, {}))
    monkeypatch.setattr(ub, "lies_kursstatus", lambda: _basis([(0, "AAA", "", "", "AAA", True),
                                                               (1, "KVUE", "2023-08-25", "", "KVUE", True)]))
    betrieb = _uni([("AAA", "A", None, None, 10), ("KVUE", "Kenvue", "2023-08-25", "2026-10-30", 30),
                    ("OKTA", "Okta, Inc.", "2026-10-30", None, 40), ("ALT", "Alt", None, "2005-01-03", 50)])
    aufrufe = []

    def pruefe(neu, gueltig=True):
        aufrufe.append(list(neu["ticker"]))
        return [{"index": nr, "ticker": z["ticker"], "name": z["name"], "von": ub.tag_text(z["von"]), "bis": ub.tag_text(z["bis"]),
                 "quelle": "yfinance", "symbol": z["ticker"], "gueltig": gueltig, "grund": None if gueltig else "Name passt nicht"}
                for nr, z in neu.iterrows()]

    return tmp_path, betrieb, aufrufe, pruefe


def test_neues_mitglied_einmal_geprueft_und_festgehalten(betrieb_tmp, monkeypatch):
    ordner, betrieb, aufrufe, pruefe = betrieb_tmp
    monkeypatch.setattr(ub, "_pruefe_neu", pruefe)
    s, meldungen = ub.kursstatus_betrieb(betrieb)
    assert aufrufe == [["OKTA"]] and (ordner / ub.NEU_DATEI).exists()
    assert s.loc[2, "herkunft"] == "neu" and bool(s.loc[2, "gueltig"]) and s.loc[2, "symbol"] == "OKTA"
    assert s.loc[1, "herkunft"] == "uebernommen" and 3 not in s.index                    # ALT endet vor 2012
    assert any("Neues Mitglied OKTA" in m and "gültig" in m for m in meldungen)
    s2, _ = ub.kursstatus_betrieb(betrieb)
    assert aufrufe == [["OKTA"]]                                                         # kein zweiter Abruf
    pd.testing.assert_frame_equal(s, s2, check_dtype=False)


def test_neues_mitglied_ohne_gueltige_reihe_bleibt_aussen_vor(betrieb_tmp, monkeypatch):
    _, betrieb, _, pruefe = betrieb_tmp
    monkeypatch.setattr(ub, "_pruefe_neu", lambda neu: pruefe(neu, gueltig=False))
    s, meldungen = ub.kursstatus_betrieb(betrieb)
    assert not bool(s.loc[2, "gueltig"])
    assert any("OKTA" in m and "außen vor" in m and "Name passt nicht" in m for m in meldungen)


def test_ohne_pruefen_bleibt_neues_mitglied_ungeprueft_und_ungueltig(betrieb_tmp, monkeypatch):
    ordner, betrieb, aufrufe, pruefe = betrieb_tmp
    monkeypatch.setattr(ub, "_pruefe_neu", pruefe)
    s, meldungen = ub.kursstatus_betrieb(betrieb, pruefen=False)
    assert aufrufe == [] and not (ordner / ub.NEU_DATEI).exists()
    assert not bool(s.loc[2, "gueltig"]) and any("noch nicht geprüft" in m for m in meldungen)


# --- Wächter -----------------------------------------------------------------------------------------------------------
_GATTUNGEN = {1652044: frozenset({"GOOG", "GOOGL"})}


def test_waechter_erlaubt_bekannte_gattungen():
    u = _uni([("GOOG", "Alphabet C", None, None, 1652044), ("GOOGL", "Alphabet A", None, None, 1652044)])
    s = pd.DataFrame({"gueltig": [True, True]}, index=[0, 1])
    assert ub.pruefe_betriebsstand(u, s, "2026-11-18", _GATTUNGEN) == []


@pytest.mark.parametrize("zeilen", [
    [("CDAY", "Ceridian", "2021-09-20", None, 1725057), ("DAY", "Dayforce", None, "2026-02-09", 1725057)],   # Fall 16.11.2026
    [("AAA", "A", None, None, 10), ("AAA", "A", "2020-01-02", None, 10)],                                     # Ticker doppelt
    [("GOOG", "Alphabet C", None, None, 1652044), ("GOOGL", "Alphabet A", None, None, 1652044),
     ("GOOGX", "Alphabet X", None, None, 1652044)],                                                          # neue Gattung
])
def test_waechter_meldet_doppelte_mitgliedschaft_laut(zeilen):
    u = _uni(zeilen)
    s = pd.DataFrame({"gueltig": [True] * len(u)}, index=u.index)
    with pytest.raises(UniversumVerschoben, match="doppelt Mitglied"):
        ub.pruefe_betriebsstand(u, s, "2025-06-02", _GATTUNGEN)


def test_waechter_meldet_heutiges_mitglied_ohne_gueltige_reihe():
    u = _uni([("AAA", "A", None, None, 10), ("CDAY", "Ceridian", "2021-09-20", None, 1725057)])
    s = pd.DataFrame({"gueltig": [True, False]}, index=[0, 1])
    meldungen = ub.pruefe_betriebsstand(u, s, "2026-11-18", {})
    assert meldungen == ["Heutiges Mitglied CDAY (Ceridian) ohne gültige Kursreihe – keine Bewertung, keine Vorschläge"]


@pytest.mark.skipif(not ub.Path(__file__).parents[2].joinpath("daten", "universum", "eingefroren").exists(),
                    reason="eingefrorener Stand nicht lokal vorhanden")
def test_bekannte_gattungen_aus_dem_eingefrorenen_stand():
    g = ub.bekannte_gattungen()
    assert g[1652044] == frozenset({"GOOG", "GOOGL"}) and 1725057 not in g


# --- Verdrahtung -------------------------------------------------------------------------------------------------------
def test_bewertung_nutzt_kursstatus_und_waechter_des_betriebs():
    from tradingbot.engines.fundamental import aktuell

    quelle = inspect.getsource(aktuell.bewertung_am)
    assert "kursstatus_betrieb(universum, pruefen=aktualisieren)" in quelle and "pruefe_betriebsstand(universum, status, tag)" in quelle


def test_firmendaten_lesen_kurse_ueber_kurscache():
    """Bis 18.11.2026 las lade_firmendaten auch im Betrieb den Entwicklungs-Cache (seit Befund 5 nicht mehr aktuell)."""
    from tradingbot.daten import sp500_nachbau

    quelle = inspect.getsource(sp500_nachbau.lade_firmendaten)
    assert "kurse_cache = kurscache()" in quelle and 'kurse_cache.lesen("kurse"' in quelle and 'cache.lesen("kurse"' not in quelle.replace("kurse_cache.lesen", "")


def test_kontraktpruefung_nutzt_den_betriebsstand():
    import importlib.util

    pfad = ub.Path(__file__).parents[2] / "tools" / "kontrakte_pruefen.py"
    text = pfad.read_text(encoding="utf-8")
    assert 'lade_universum(stand="betrieb")' in text and "kursstatus_betrieb(universum, pruefen=False)" in text
    assert importlib.util.spec_from_file_location("k", pfad) is not None
