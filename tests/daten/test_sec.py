"""SEC-Datenschicht: Point-in-Time-Regeln mit erfundenen Fakten im echten companyfacts-Format."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from tradingbot.daten.abruf import DatenFehler, Drossel
from tradingbot.daten.sec import (
    SecClient,
    abdeckung,
    erstmeldungen,
    fakten_tabelle,
    geschaeftsjahresenden,
    ist_bank_oder_versicherung,
    kennzahl_jahreswerte,
    letzter_wert,
)

UMSATZ = {"art": "dauer", "einheit": "USD",
          "konzepte": ["us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "us-gaap:SalesRevenueNet"]}
GEWINN = {"art": "dauer", "einheit": "USD", "konzepte": ["us-gaap:NetIncomeLoss"]}
BILANZ = {"art": "stichtag", "einheit": "USD", "konzepte": ["us-gaap:Assets"]}
AKTIEN = {"art": "letzter", "einheit": "shares", "konzepte": ["dei:EntityCommonStockSharesOutstanding"]}


def _w(start, ende, wert, filed, form="10-K", accn="a1", fp="FY"):
    w = {"end": ende, "val": wert, "accn": accn, "fy": int(ende[:4]), "fp": fp, "form": form, "filed": filed}
    if start:
        w["start"] = start
    return w


FAKTEN = {
    "cik": 1, "entityName": "Beispiel AG",
    "facts": {
        "us-gaap": {
            # Begriffswechsel: bis GJ 2017 SalesRevenueNet, ab GJ 2018 RevenueFromContract...
            "SalesRevenueNet": {"units": {"USD": [
                _w("2016-10-01", "2017-09-30", 229.0, "2017-11-03", accn="k17"),
                _w("2016-10-01", "2017-09-30", 229.0, "2018-11-05", accn="k18"),       # Vorjahr im nächsten 10-K
            ]}},
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
                _w("2017-10-01", "2018-09-29", 265.0, "2018-11-05", accn="k18"),
                _w("2018-07-01", "2018-09-29", 62.0, "2018-11-05", accn="k18"),       # Q4 im 10-K: kein Jahreswert
            ]}},
            "NetIncomeLoss": {"units": {"USD": [
                _w("2017-10-01", "2018-09-29", 100.0, "2018-11-05", accn="k18"),
                _w("2017-10-01", "2018-09-29", 90.0, "2019-02-01", form="10-K/A", accn="k18a"),   # Restatement
                _w("2017-10-01", "2018-09-29", 95.0, "2019-11-01", accn="k19"),                   # Vorjahr, korrigiert
                _w("2018-09-30", "2019-09-28", 110.0, "2019-11-01", accn="k19"),
            ]}},
            "Assets": {"units": {"USD": [
                _w(None, "2017-09-30", 1000.0, "2017-11-03", accn="k17"),
                _w(None, "2018-09-29", 1100.0, "2018-11-05", accn="k18"),
                _w(None, "2018-12-29", 1150.0, "2019-01-30", form="10-Q", accn="q1", fp="Q1"),  # Quartal: kein GJ-Ende
            ]}},
        },
        "dei": {
            "EntityCommonStockSharesOutstanding": {"units": {"shares": [
                _w(None, "2018-10-19", 50.0, "2018-11-05", accn="k18"),
                _w(None, "2019-01-18", 49.0, "2019-01-30", form="10-Q", accn="q1", fp="Q1"),
            ]}},
        },
    },
}


@pytest.fixture
def erst():
    return erstmeldungen(fakten_tabelle(FAKTEN))


def test_verfuegbar_erst_ab_dem_handelstag_nach_filed(erst):
    assert kennzahl_jahreswerte(erst, GEWINN, "2018-11-05").empty                 # Tag der Einreichung: noch nicht
    assert kennzahl_jahreswerte(erst, GEWINN, "2018-11-06")["wert"].tolist() == [100.0]
    # Freitag eingereicht → ab Montag
    freitag = erstmeldungen(fakten_tabelle({"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        _w("2018-01-01", "2018-12-31", 5.0, "2019-03-01")]}}}}}))
    assert freitag["verfuegbar_ab"].iloc[0] == pd.Timestamp("2019-03-04")


def test_restatement_aendert_den_erstgemeldeten_wert_nie(erst):
    spaeter = kennzahl_jahreswerte(erst, GEWINN, "2024-01-01")
    assert spaeter.loc["2018-09-29", "wert"] == 100.0                             # nicht 90 (10-K/A), nicht 95
    assert spaeter.loc["2019-09-28", "wert"] == 110.0


def test_originalfassung_vor_berichtigung_am_selben_tag():
    fakten = {"facts": {"us-gaap": {"NetIncomeLoss": {"units": {"USD": [
        _w("2018-01-01", "2018-12-31", 7.0, "2019-03-01", form="10-K/A", accn="b"),
        _w("2018-01-01", "2018-12-31", 8.0, "2019-03-01", form="10-K", accn="c"),
    ]}}}}}
    assert erstmeldungen(fakten_tabelle(fakten))["wert"].tolist() == [8.0]


def test_begriffswechsel_und_nur_jahreswerte(erst):
    umsatz = kennzahl_jahreswerte(erst, UMSATZ, "2019-06-30")
    assert umsatz["wert"].tolist() == [229.0, 265.0]                              # Q4-Wert 62 fehlt
    assert umsatz["konzept"].tolist() == ["SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"]
    assert umsatz.loc["2017-09-30", "filed"] == pd.Timestamp("2017-11-03")         # Erstmeldung, nicht der spätere 10-K


def test_bilanzwerte_nur_zum_geschaeftsjahresende(erst):
    assert list(geschaeftsjahresenden(erst, "2019-06-30")) == [pd.Timestamp("2017-09-30"), pd.Timestamp("2018-09-29")]
    bilanz = kennzahl_jahreswerte(erst, BILANZ, "2019-06-30")
    assert bilanz["wert"].tolist() == [1000.0, 1100.0]                            # Quartalsbilanz 1150 nicht dabei


def test_letzter_wert_aktien(erst):
    assert letzter_wert(erst, AKTIEN, "2018-12-31") == 50.0
    assert letzter_wert(erst, AKTIEN, "2019-02-15") == 49.0
    assert letzter_wert(erst, AKTIEN, "2018-01-01") is None


def test_abdeckung(erst):
    a = abdeckung(erst, {"umsatz": UMSATZ, "bilanz": BILANZ, "aktien": AKTIEN, "gewinn": GEWINN}, "2019-06-30")
    assert a == {"umsatz": True, "bilanz": True, "aktien": True, "gewinn": True}
    assert abdeckung(erst, {"umsatz": UMSATZ}, "2021-06-30") == {"umsatz": False}   # letzter Wert zu alt


def test_banken_und_versicherungen():
    konfig = {"universum": {"sic_banken": [[6000, 6199]], "sic_versicherungen": [[6300, 6411]]}}
    assert ist_bank_oder_versicherung(6021, konfig) and ist_bank_oder_versicherung(6331, konfig)
    assert not ist_bank_oder_versicherung(3571, konfig) and not ist_bank_oder_versicherung(None, konfig)


# --- Client ------------------------------------------------------------------------------------
class _Antwort:
    def __init__(self, status, daten=None):
        self.status_code, self._daten = status, daten

    def json(self):
        return self._daten


class _Sitzung:
    def __init__(self, antworten):
        self.antworten = list(antworten)
        self.aufrufe = []

    def get(self, url, headers, timeout):
        self.aufrufe.append((url, headers))
        a = self.antworten.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


class _Uhr:
    def __init__(self):
        self.t = 0.0
        self.pausen = []

    def __call__(self):
        return self.t

    def schlafen(self, s):
        self.pausen.append(s)
        self.t += s


def _client(tmp_path, sitzung, jetzt, uhr=None):
    uhr = uhr or _Uhr()
    return SecClient("Test Nutzer test@example.com", cache_wurzel=tmp_path, sitzung=sitzung,
                     drossel=Drossel(0.125, uhr=uhr, schlafen=uhr.schlafen), max_alter=timedelta(days=7), jetzt=lambda: jetzt[0])


def test_client_user_agent_cache_und_drossel(tmp_path):
    uhr = _Uhr()
    jetzt = [datetime(2026, 11, 2, tzinfo=timezone.utc)]
    sitzung = _Sitzung([_Antwort(200, FAKTEN), _Antwort(200, {"cik": 2}), _Antwort(200, FAKTEN)])
    client = _client(tmp_path, sitzung, jetzt, uhr)

    daten, _ = client.companyfacts(1)
    assert daten["entityName"] == "Beispiel AG"
    assert sitzung.aufrufe[0][0].endswith("/CIK0000000001.json")
    assert sitzung.aufrufe[0][1]["User-Agent"] == "Test Nutzer test@example.com"
    client.companyfacts(1)                                    # aus dem Cache
    assert len(sitzung.aufrufe) == 1
    client.submissions(2)                                     # zweiter Abruf direkt danach: Drossel wartet
    assert uhr.pausen == [pytest.approx(0.125)]
    jetzt[0] += timedelta(days=8)                              # Cache abgelaufen
    client.companyfacts(1)
    assert len(sitzung.aufrufe) == 3


def test_client_fehler(tmp_path, monkeypatch):
    monkeypatch.setattr("tradingbot.daten.abruf.time.sleep", lambda s: None)
    jetzt = [datetime(2026, 11, 2, tzinfo=timezone.utc)]
    with pytest.raises(DatenFehler, match="nicht gefunden"):
        _client(tmp_path, _Sitzung([_Antwort(404)]), jetzt).companyfacts(9)
    # Vorübergehender Fehler mit vorhandenem (abgelaufenem) Cache: alter Stand wird genutzt
    client = _client(tmp_path, _Sitzung([_Antwort(200, FAKTEN)] + [_Antwort(503)] * 3), jetzt)
    client.companyfacts(1)
    jetzt[0] += timedelta(days=8)
    daten, zeitpunkt = client.companyfacts(1)
    assert daten["entityName"] == "Beispiel AG" and zeitpunkt == datetime(2026, 11, 2, tzinfo=timezone.utc)
