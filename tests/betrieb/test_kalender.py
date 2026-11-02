"""Handelskalender und Datenprüfung vor dem Tageslauf."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from tradingbot.betrieb.kalender import feiertage, ist_handelstag, letzte_abgeschlossene_sitzung, ostersonntag, pruefe_tageskurse

BERLIN = ZoneInfo("Europe/Berlin")


def test_ostern_und_feiertage():
    assert ostersonntag(2026) == date(2026, 4, 5) and ostersonntag(2025) == date(2025, 4, 20)
    assert {date(2026, 4, 3), date(2026, 4, 6), date(2026, 12, 24), date(2026, 12, 31)} <= feiertage("xetra", 2026)
    nyse = feiertage("nyse", 2026)
    assert date(2026, 11, 26) in nyse                  # Thanksgiving
    assert date(2026, 7, 3) in nyse                    # 4. Juli ist Samstag → Freitag
    assert date(2026, 6, 19) in nyse and date(2026, 1, 19) in nyse
    assert date(2027, 12, 31) not in feiertage("nyse", 2028)   # Neujahr 2028 Samstag: nicht vorgezogen
    assert not ist_handelstag("xetra", date(2026, 12, 24)) and ist_handelstag("nyse", date(2026, 12, 24))


def test_letzte_abgeschlossene_sitzung_je_uhrzeit():
    montag_abend = datetime(2026, 11, 2, 18, 30, tzinfo=BERLIN)        # Xetra zu, NYSE noch offen
    assert letzte_abgeschlossene_sitzung("xetra", montag_abend) == date(2026, 11, 2)
    assert letzte_abgeschlossene_sitzung("nyse", montag_abend) == date(2026, 10, 30)   # Freitag davor
    spaet = datetime(2026, 11, 2, 23, 30, tzinfo=BERLIN)
    assert letzte_abgeschlossene_sitzung("nyse", spaet) == date(2026, 11, 2)
    assert letzte_abgeschlossene_sitzung("xetra", datetime(2026, 11, 2, 12, 0, tzinfo=BERLIN)) == date(2026, 10, 30)
    assert letzte_abgeschlossene_sitzung("xetra", datetime(2026, 4, 6, 20, 0, tzinfo=BERLIN)) == date(2026, 4, 2)   # Ostern


def _kurse(schluss, dividende=0.0, split=0.0):
    tage = pd.bdate_range(end="2026-11-02", periods=len(schluss))
    k = pd.DataFrame({"close": schluss, "dividende": 0.0, "split": 0.0}, index=tage)
    k.iloc[-1, k.columns.get_loc("dividende")] = dividende
    k.iloc[-1, k.columns.get_loc("split")] = split
    return k


def test_datenpruefung():
    assert pruefe_tageskurse(_kurse([100, 101]), date(2026, 11, 2), 0.15) == []
    assert "erwartet" in pruefe_tageskurse(_kurse([100, 101]), date(2026, 11, 3), 0.15)[0]
    assert "ohne Kapitalmaßnahme" in pruefe_tageskurse(_kurse([100, 80]), date(2026, 11, 2), 0.15)[0]
    assert pruefe_tageskurse(_kurse([100, 50], split=2.0), date(2026, 11, 2), 0.15) == []
    assert pruefe_tageskurse(pd.DataFrame(), date(2026, 11, 2), 0.15) == ["keine Kurse"]
