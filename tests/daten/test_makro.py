from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
import requests

from tradingbot.daten.abruf import DatenFehler, Drossel
from tradingbot.daten.makro import OFFEN, fred_holer, fred_tabelle, lade_makro_tabelle, stand_am

# US-BIP (Mrd. USD). Echt laut ALFRED (Abruf 01.11.2026): 26465.865 als Stand vom 01.05.2023 und
# 27241.282 als aktueller Wert für Q1 2023. Zwischenstand, Zeiträume und Q2-Wert sind ausgedacht.
GDP_ZEILEN = [
    {"date": "2023-01-01", "value": "26465.865", "realtime_start": "2023-04-27", "realtime_end": "2023-05-24"},
    {"date": "2023-01-01", "value": "26486.287", "realtime_start": "2023-05-25", "realtime_end": "2023-06-28"},
    {"date": "2023-01-01", "value": "27241.282", "realtime_start": "2023-06-29", "realtime_end": "9999-12-31"},
    {"date": "2023-04-01", "value": "26834.000", "realtime_start": "2023-07-27", "realtime_end": "9999-12-31"},
]


class FredAttrappe:
    """Antwortet wie die FRED-API und merkt sich die Abfragen."""

    def __init__(self, beobachtungen, vintages=()):
        self.beobachtungen = beobachtungen
        self.vintages = list(vintages)
        self.abfragen: list[tuple[str, dict]] = []

    def __call__(self, pfad, parameter):
        self.abfragen.append((pfad, parameter))
        if pfad == "series/vintagedates":
            teil = self.vintages[parameter["offset"] : parameter["offset"] + parameter["limit"]]
            return {"vintage_dates": teil}
        return {"count": len(self.beobachtungen), "observations": self.beobachtungen}


def test_stand_am_liefert_wissensstand_des_stichtags():
    tabelle = fred_tabelle("GDP", revidiert=True, holen=FredAttrappe(GDP_ZEILEN, ["2023-04-27"]))

    assert stand_am(tabelle, "2023-04-26").empty                      # vor der Erstveröffentlichung
    assert stand_am(tabelle, "2023-05-01").tolist() == [26465.865]   # Erstveröffentlichung
    assert stand_am(tabelle, "2023-06-01").tolist() == [26486.287]   # zweite Schätzung
    heute = stand_am(tabelle, "2026-11-01")
    assert heute.to_dict() == {pd.Timestamp("2023-01-01"): 27241.282, pd.Timestamp("2023-04-01"): 26834.0}
    assert tabelle["gueltig_bis"].max() == OFFEN


def test_nicht_revidierte_serie_erst_nach_verzoegerung_sichtbar():
    zeilen = [
        {"date": "2024-06-03", "value": "4.41", "realtime_start": "2026-11-01", "realtime_end": "9999-12-31"},
        {"date": "2024-06-04", "value": ".", "realtime_start": "2026-11-01", "realtime_end": "9999-12-31"},
    ]
    tabelle = fred_tabelle("DGS10", revidiert=False, verzoegerung_tage=1, holen=FredAttrappe(zeilen))
    assert stand_am(tabelle, "2024-06-03").empty
    assert stand_am(tabelle, "2024-06-04").tolist() == [4.41]
    assert stand_am(tabelle, "2024-06-10").tolist() == [4.41]  # "." = kein Wert, wird entfernt


def test_vintages_in_abschnitten_ohne_luecke():
    tage = pd.date_range("2010-01-01", periods=4500, freq="D").strftime("%Y-%m-%d").tolist()
    attrappe = FredAttrappe([], tage)
    fred_tabelle("DGS10", revidiert=True, holen=attrappe)

    zeitraeume = [(p["realtime_start"], p["realtime_end"]) for pfad, p in attrappe.abfragen if pfad == "series/observations"]
    assert zeitraeume == [
        (tage[0], (pd.Timestamp(tage[2000]) - timedelta(days=1)).strftime("%Y-%m-%d")),
        (tage[2000], (pd.Timestamp(tage[4000]) - timedelta(days=1)).strftime("%Y-%m-%d")),
        (tage[4000], "9999-12-31"),
    ]


def test_cache_wird_nach_maximalem_alter_erneuert(cache):
    konfig = {"fred": {"serien": {"GDP": {"revidiert": True}}}, "cache": {"makro_max_alter_stunden": 24}}
    attrappe = FredAttrappe(GDP_ZEILEN, ["2023-04-27"])
    jetzt = datetime(2026, 11, 1, 8, tzinfo=timezone.utc)

    lade_makro_tabelle("GDP", cache=cache, holen=attrappe, konfig=konfig, jetzt=jetzt)
    lade_makro_tabelle("GDP", cache=cache, holen=attrappe, konfig=konfig, jetzt=jetzt + timedelta(hours=23))
    assert sum(p == "series/vintagedates" for p, _ in attrappe.abfragen) == 1
    lade_makro_tabelle("GDP", cache=cache, holen=attrappe, konfig=konfig, jetzt=jetzt + timedelta(hours=25))
    assert sum(p == "series/vintagedates" for p, _ in attrappe.abfragen) == 2


class _Sitzung:
    def __init__(self, antwort=None, fehler=None):
        self.antwort, self.fehler = antwort, fehler

    def get(self, url, params, timeout):
        if self.fehler:
            raise self.fehler
        return self.antwort


class _Antwort:
    def __init__(self, status, daten):
        self.status_code, self._daten = status, daten

    def json(self):
        return self._daten


def _ohne_pause():
    return Drossel(0, schlafen=lambda s: None)


def test_schluessel_erscheint_nie_in_fehlermeldungen(monkeypatch):
    monkeypatch.setattr("tradingbot.daten.abruf.time.sleep", lambda s: None)
    geheim = "abc123geheim"
    netzfehler = requests.ConnectionError(f"Max retries exceeded with url: /fred?api_key={geheim}")
    holen = fred_holer(geheim, sitzung=_Sitzung(fehler=netzfehler), drossel=_ohne_pause())
    with pytest.raises(DatenFehler) as info:
        holen("series/observations", {"series_id": "GDP"})
    assert geheim not in str(info.value) and info.value.__cause__ is None

    antwort = _Antwort(400, {"error_message": f"Bad Request. api_key {geheim} invalid"})
    holen = fred_holer(geheim, sitzung=_Sitzung(antwort=antwort), drossel=_ohne_pause())
    with pytest.raises(DatenFehler) as info:
        holen("series/observations", {"series_id": "GDP"})
    assert geheim not in str(info.value) and "***" in str(info.value)
