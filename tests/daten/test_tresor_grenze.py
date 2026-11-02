"""Zentrale Datumsgrenze (Tresor): Abfragen über den 31.12.2024 hinaus liefern nichts dahinter, außer bei Tresor-Öffnung."""
from datetime import date

import pandas as pd
import pytest

from conftest import SimulierteQuelle, yahoo_rohdaten
from tradingbot.backtest.tresor import TresorFreigabe, TresorGesperrt, datengrenze, oeffne_tresor, tresor_geoeffnet
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sec import fakten_tabelle, kennzahl_jahreswerte
from tradingbot.engines.fundamental.kennzahlen import jahreswerte_firma

HEUTE_SPAETER = date(2025, 3, 31)


def _konfig(tmp_path):
    return {"tresor": {"gesperrt_ab": "2025-01-01", "protokoll": str(tmp_path / "TRESOR_PROTOKOLL.md")}}


def test_grenze_ist_31_12_2024():
    assert datengrenze() == pd.Timestamp("2024-12-31")


def test_kurse_mit_dividenden_enden_an_der_grenze(cache, tmp_path):
    quelle = SimulierteQuelle(yahoo_rohdaten("2024-11-01", "2025-03-28"))
    daten = lade_kurse("TEST", "2024-12-02", "2025-02-28", cache=cache, abrufer=quelle, heute=HEUTE_SPAETER)
    assert daten.index.max() <= pd.Timestamp("2024-12-31") and len(daten) > 0
    assert set(daten.columns) >= {"dividende", "split"}            # Dividenden und Splits hängen am selben Index
    # nur mit eingetragener Öffnung kommen die Tage danach
    freigabe = oeffne_tresor("Test-Phase", "Test der Datumsgrenze", konfig=_konfig(tmp_path))
    with tresor_geoeffnet(freigabe, konfig=_konfig(tmp_path)):
        offen = lade_kurse("TEST", "2024-12-02", "2025-02-28", cache=cache, abrufer=quelle, heute=HEUTE_SPAETER)
    assert offen.index.max() > pd.Timestamp("2025-01-31")
    assert datengrenze() == pd.Timestamp("2024-12-31")             # nach dem Block wieder gesperrt


def test_oeffnen_ohne_protokolleintrag_verweigert(tmp_path):
    with pytest.raises(TresorGesperrt):
        with tresor_geoeffnet(TresorFreigabe("nie geöffnet", "x"), konfig=_konfig(tmp_path)):
            pass


def _facts():
    def wert(ende, filed, val):
        return {"start": f"{ende[:4]}-01-01", "end": ende, "val": val, "filed": filed, "form": "10-K", "accn": filed, "fy": 0, "fp": "FY"}
    return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [wert("2023-12-31", "2024-02-20", 100), wert("2024-12-31", "2025-02-20", 120)]}}}}}


def test_fundamentaldaten_nur_bis_zur_grenze():
    tab = fakten_tabelle(_facts())
    assert list(tab["filed"]) == [pd.Timestamp("2024-02-20")]
    # auch Erstmeldungen aus dem Cache (an fakten_tabelle vorbei) werden begrenzt
    from tradingbot.daten.sec import erstmeldungen
    roh = tab.copy()
    spaet = roh.iloc[[0]].assign(ende=pd.Timestamp("2024-12-31"), start=pd.Timestamp("2024-01-01"), filed=pd.Timestamp("2025-02-20"))
    erst = erstmeldungen(pd.concat([roh, spaet], ignore_index=True))
    definition = {"art": "dauer", "einheit": "USD", "konzepte": ["us-gaap:Revenues"]}
    werte = kennzahl_jahreswerte(erst, definition, "2025-06-30")
    assert list(werte.index) == [pd.Timestamp("2023-12-31")]
    jahr = jahreswerte_firma(erst, {"umsatz": definition})
    assert pd.to_datetime(jahr["bekannt_ab"]).max() < pd.Timestamp("2025-01-01")
