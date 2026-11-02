"""Einstufung von Delistings für die Rückfall-Regel."""
import pandas as pd
import pytest

from tradingbot.daten.delisting import delisting_grund, delisting_grund_mit_korrektur, delisting_rendite, einreichungen

KONFIG = {"universum": {"delisting": {"uebernahme_fusion": "letzter_kurs", "pleite_performance_unbekannt": "letzter_kurs_minus_30_prozent"}}}


def _filings(zeilen):
    return einreichungen({"filings": {"recent": {"filingDate": [z[0] for z in zeilen], "form": [z[1] for z in zeilen],
                                                 "items": [z[2] for z in zeilen]}}})


def test_pleite_uebernahme_unbekannt():
    pleite = _filings([("2020-04-15", "8-K", "1.03,7.01,9.01"), ("2020-03-01", "10-K", "")])
    assert delisting_grund(pleite, "2020-04-23")[0] == "pleite"
    kauf = _filings([("2017-12-29", "8-K", "2.01,3.01,5.01,9.01")])
    assert delisting_grund(kauf, "2017-12-29") == ("uebernahme", "8-K Item 2.01 vom 2017-12-29")
    angebot = _filings([("2016-03-10", "SC 14D9", "")])
    assert delisting_grund(angebot, "2016-05-01")[0] == "uebernahme"
    nichts = _filings([("2010-01-10", "8-K", "1.03")])                      # Insolvenz viel zu früh: zählt nicht
    assert delisting_grund(nichts, "2016-05-01")[0] == "unbekannt"
    assert delisting_grund(nichts, "2016-05-01", "Kraft acquired Heinz")[0] == "uebernahme"


def test_pleite_gewinnt_gegen_uebernahmebeleg():
    beides = _filings([("2023-04-23", "8-K", "1.03"), ("2023-09-01", "8-K", "2.01")])
    assert delisting_grund(beides, "2023-09-29")[0] == "pleite"


def test_korrektur_und_rendite():
    leer = _filings([])
    korrektur = [{"ticker": "TFCF", "grund": "uebernahme", "quelle": "Disney"}]
    assert delisting_grund_mit_korrektur("TFCF", leer, "2019-03-20", None, korrektur) == ("uebernahme", "korrigiert: Disney")
    assert delisting_rendite("uebernahme", KONFIG) == 0.0
    assert delisting_rendite("pleite", KONFIG) == pytest.approx(-0.30) and delisting_rendite("unbekannt", KONFIG) == pytest.approx(-0.30)
