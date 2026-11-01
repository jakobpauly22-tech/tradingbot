from datetime import date

import pandas as pd

from conftest import HEUTE, SimulierteQuelle, yahoo_rohdaten
from tradingbot.daten.benchmarks import core_benchmarks, historie_ab, lade_benchmark
from tradingbot.konfiguration import lade_konfiguration


def test_konfiguration_hauptbenchmark_und_start():
    konfig = lade_konfiguration("daten")
    assert historie_ab(konfig) == date(2012, 1, 1)
    benchmarks = core_benchmarks(konfig)
    assert benchmarks[0] == {"name": "MSCI ACWI IMI", "ticker": "SPYI.DE", "rolle": "haupt"}
    assert len(benchmarks) == 6


def test_frueherer_start_wird_auf_historie_ab_angehoben(cache):
    quelle = SimulierteQuelle(yahoo_rohdaten("2011-05-16", "2012-02-29"))
    konfig = {"benchmarks": {"historie_ab": "2012-01-01"}, "kurse": {"wechselkurse": {}}}
    kurse = lade_benchmark("SPYI.DE", "2011-05-16", "2012-02-29", konfig=konfig, cache=cache, abrufer=quelle, heute=HEUTE)
    assert kurse.index[0] == pd.Timestamp("2012-01-02")
    assert quelle.abrufe[0][0] == date(2012, 1, 1)
