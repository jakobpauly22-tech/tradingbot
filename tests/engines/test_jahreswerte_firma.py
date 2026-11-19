"""jahreswerte_firma, schneller Rechenweg (Laufzeit, Jakob 19.11.2026): exakt dasselbe Ergebnis wie der alte Weg über
daten.sec.kennzahl_jahreswerte je Kennzahl und Begriff. Der alte Weg steht hier unverändert als Referenz."""
import random

import numpy as np
import pandas as pd
import pytest

from tradingbot.daten.sec import erstmeldungen, kennzahl_jahreswerte
from tradingbot.engines.fundamental.kennzahlen import jahreswerte_firma, zusammenlegen
from tradingbot.konfiguration import lade_konfiguration

SPALTEN = ["kennzahl", "ende", "wert", "bekannt_ab", "konzept", "rang"]


def jahreswerte_firma_alt(erst: pd.DataFrame, definitionen: dict) -> pd.DataFrame:
    """Rechenweg bis 19.11.2026 (Commit c80a85c), unverändert."""
    from tradingbot.backtest.tresor import begrenze

    erst = begrenze(erst, "filed")
    zeilen = []
    for name, d in definitionen.items():
        if d["art"] == "letzter" or erst is None or len(erst) == 0:
            continue
        for rang, konzept in enumerate(d["konzepte"]):
            w = kennzahl_jahreswerte(erst, {**d, "konzepte": [konzept]}, "2100-01-01")
            for ende, r in w.iterrows():
                zeilen.append((name, ende, float(r["wert"]), r["filed"] + pd.Timedelta(days=1), r["konzept"], rang))
    return pd.DataFrame(zeilen, columns=SPALTEN)


def _gleich(erst, definitionen):
    alt, neu = jahreswerte_firma_alt(erst, definitionen), jahreswerte_firma(erst, definitionen)
    assert list(alt.columns) == list(neu.columns)
    assert (alt.dtypes == neu.dtypes).all(), (alt.dtypes, neu.dtypes)
    assert alt.equals(neu)
    return neu


def _fakt(konzept, ende, wert, filed, start=None, einheit="USD", form="10-K", accn="a1", taxonomie="us-gaap"):
    return {"taxonomie": taxonomie, "konzept": konzept, "einheit": einheit, "start": pd.Timestamp(start) if start else pd.NaT,
            "ende": pd.Timestamp(ende), "wert": float(wert), "filed": pd.Timestamp(filed), "form": form, "accn": accn}


DEFINITIONEN = {
    "umsatz": {"art": "dauer", "einheit": "USD", "konzepte": ["us-gaap:Revenues", "us-gaap:SalesRevenueNet"]},
    "bilanzsumme": {"art": "stichtag", "einheit": "USD", "konzepte": ["us-gaap:Assets"]},
    "aktien": {"art": "letzter", "einheit": "shares", "konzepte": ["dei:EntityCommonStockSharesOutstanding"]},
}


def _beispiel():
    f = [
        _fakt("Revenues", "2019-12-31", 100, "2020-02-20", start="2019-01-01"),
        _fakt("Revenues", "2020-12-31", 110, "2021-02-20", start="2020-01-01"),
        _fakt("Revenues", "2020-12-31", 111, "2021-02-20", start="2020-01-02", accn="a2"),   # zwei Jahresperioden, gleiches Ende
        _fakt("Revenues", "2020-06-30", 50, "2020-08-01", start="2020-01-01", form="10-Q"),  # Halbjahr: kein Jahreswert
        _fakt("SalesRevenueNet", "2018-12-31", 90, "2019-02-20", start="2018-01-01"),
        _fakt("SalesRevenueNet", "2019-12-31", 99, "2020-02-20", start="2019-01-01"),
        _fakt("Revenues", "2019-12-31", 7, "2020-02-20", start="2019-01-01", einheit="EUR"),  # andere Einheit
        _fakt("Assets", "2019-12-31", 500, "2020-02-20"),
        _fakt("Assets", "2020-06-30", 520, "2020-08-01", form="10-Q"),                        # kein Geschäftsjahresende
        _fakt("Assets", "2020-12-31", 540, "2021-02-20"),
        _fakt("Assets", "2018-12-31", 480, "2020-02-20"),                                      # Vorjahr aus späterem 10-K
        _fakt("Assets", "2018-12-31", 470, "2019-02-20", taxonomie="ifrs-full"),
        _fakt("EntityCommonStockSharesOutstanding", "2021-02-01", 10, "2021-02-20", einheit="shares", taxonomie="dei"),
        _fakt("Assets", "2025-12-31", 600, "2026-02-20"),                                      # Tresorzeitraum
        _fakt("Revenues", "2025-12-31", 130, "2026-02-20", start="2025-01-01"),
    ]
    return erstmeldungen(pd.DataFrame(f))


def test_beispiel_gleich_wie_alter_weg():
    neu = _gleich(_beispiel(), DEFINITIONEN)
    assert len(neu) > 0
    assert set(neu["kennzahl"]) == {"umsatz", "bilanzsumme"}             # „letzter“ wird übergangen
    assert pd.Timestamp("2025-12-31") not in set(neu["ende"])               # Tresorgrenze außerhalb des Betriebs
    assert pd.Timestamp("2020-06-30") not in set(neu["ende"])               # weder Jahreswert noch Geschäftsjahresende


def test_im_betriebsmodus_gleich_wie_alter_weg():
    from tradingbot.backtest.tresor import betriebsmodus

    with betriebsmodus("Test jahreswerte_firma", protokoll=_protokoll()):
        neu = _gleich(_beispiel(), DEFINITIONEN)
    assert pd.Timestamp("2025-12-31") in set(neu["ende"])


def _protokoll():
    import tempfile
    from pathlib import Path

    return Path(tempfile.mkdtemp()) / "freigaben.log"


def test_leer_und_none():
    _gleich(_beispiel().iloc[0:0], DEFINITIONEN)
    assert jahreswerte_firma(None, DEFINITIONEN).equals(jahreswerte_firma_alt(None, DEFINITIONEN))


def test_unbekannte_art_wie_bisher_fehler():
    with pytest.raises(ValueError):
        jahreswerte_firma_alt(_beispiel(), {"x": {"art": "quartal", "einheit": "USD", "konzepte": ["us-gaap:Revenues"]}})
    with pytest.raises(ValueError):
        jahreswerte_firma(_beispiel(), {"x": {"art": "quartal", "einheit": "USD", "konzepte": ["us-gaap:Revenues"]}})


def test_echte_firmen_aus_dem_cache_gleich():
    """Stichprobe echter Erstmeldungen (lokaler Cache, ohne Netz); ohne Cache übersprungen. Vollprüfung aller 806 Firmen
    einmalig am 19.11.2026, im Betriebsmodus und mit Tresorgrenze: 0 Abweichungen (Commit-Nachricht)."""
    from tradingbot.daten.cache import standard_cache

    cache = standard_cache()
    ordner = cache.wurzel / "sec_erstmeldungen"
    dateien = sorted(p.stem for p in ordner.glob("*.parquet")) if ordner.exists() else []
    if not dateien:
        pytest.skip("keine SEC-Erstmeldungen im lokalen Cache")
    kennzahlen = lade_konfiguration("fundamental")["kennzahlen"]
    for schluessel in random.Random(19112026).sample(dateien, min(6, len(dateien))):
        erst, _ = cache.lesen("sec_erstmeldungen", schluessel)
        _gleich(zusammenlegen([erst]), kennzahlen)


def test_zufaellige_tabellen_gleich():
    """Viele Gleichstände (gleiches Ende, mehrere Einheiten und Begriffe) als Zufallstabellen."""
    zufall = np.random.default_rng(7)
    for _ in range(30):
        f = []
        for _ in range(int(zufall.integers(0, 60))):
            jahr = int(zufall.integers(2015, 2027))
            ende = pd.Timestamp(f"{jahr}-12-31") - pd.Timedelta(days=int(zufall.choice([0, 0, 0, 3, 180])))
            dauer = int(zufall.choice([0, 365, 364, 371, 90, 381, 349]))
            f.append(_fakt(str(zufall.choice(["Revenues", "SalesRevenueNet", "Assets"])), ende, float(zufall.integers(1, 1000)),
                           ende + pd.Timedelta(days=int(zufall.integers(20, 900))),
                           start=ende - pd.Timedelta(days=dauer) if dauer else None, einheit=str(zufall.choice(["USD", "USD", "EUR"])),
                           form=str(zufall.choice(["10-K", "10-K/A", "10-Q"])), accn=f"a{int(zufall.integers(0, 5))}"))
        erst = erstmeldungen(pd.DataFrame(f)) if f else _beispiel().iloc[0:0]
        _gleich(erst, DEFINITIONEN)
