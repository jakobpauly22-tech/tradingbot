from datetime import date

import pandas as pd

from conftest import yahoo_rohdaten
from tradingbot.daten.kurse import normalisieren
from tradingbot.daten.pruefung import pruefe_kurse


def _saubere_kurse():
    return normalisieren(yahoo_rohdaten("2024-06-03", "2024-06-28"))


def _arten(befunde):
    return {b.pruefung for b in befunde}


def test_saubere_kurse_ohne_befund():
    assert pruefe_kurse(_saubere_kurse(), heute=date(2024, 7, 1)) == []


def test_leer():
    assert _arten(pruefe_kurse(_saubere_kurse().iloc[:0])) == {"leer"}


def test_preisfehler():
    kurse = _saubere_kurse()
    kurse.iloc[2, kurse.columns.get_loc("close")] = -1.0
    kurse.iloc[5, kurse.columns.get_loc("low")] = kurse.iloc[5]["high"] * 2
    assert {"nicht_positiv", "spanne", "sprung"} <= _arten(pruefe_kurse(kurse))


def test_sprung_nur_ohne_split():
    kurse = _saubere_kurse()
    tag = kurse.index[10]
    kurse.loc[tag:, ["open", "high", "low", "close"]] /= 2
    befunde = pruefe_kurse(kurse)
    assert [(b.pruefung, b.datum) for b in befunde] == [("sprung", tag.date())]

    kurse.loc[tag, "split"] = 2.0
    assert pruefe_kurse(kurse) == []


def test_luecke_doppelt_und_veraltet():
    kurse = _saubere_kurse()
    kurse = kurse.drop(kurse.index[5:12])                 # 7 Werktage fehlen
    kurse = pd.concat([kurse, kurse.iloc[[0]]]).sort_index()  # ein Tag doppelt
    befunde = pruefe_kurse(kurse, heute=date(2024, 7, 15))
    assert _arten(befunde) == {"luecke", "doppelt", "veraltet"}
