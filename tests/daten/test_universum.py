"""Rekonstruktion der S&P-500-Mitgliedschaften mit kleinen, nachvollziehbaren Tabellen."""
import pandas as pd
import pytest

from tradingbot.daten.universum import (
    anzahl_je_stichtag,
    cik_kandidaten,
    korrekturen_anwenden,
    mitglieder_am,
    mitgliedschaften,
    name_normalisieren,
    passt_zum_intervall,
    vorgaenger_fehlt,
    zehn_k_daten,
)


def _aktuell(zeilen):
    return pd.DataFrame(zeilen, columns=["ticker", "name", "sektor", "aufgenommen", "cik"]).assign(
        aufgenommen=lambda d: pd.to_datetime(d.aufgenommen), cik=lambda d: d.cik.astype("Int64"))


def _aenderungen(zeilen):
    return pd.DataFrame(zeilen, columns=["datum", "zugang_ticker", "zugang_name", "abgang_ticker", "abgang_name", "grund"]).assign(
        datum=lambda d: pd.to_datetime(d.datum))


SEC_NAMEN = pd.DataFrame({"name": ["TESORO CORP /NEW/", "ANDEAVOR", "META PLATFORMS, INC.", "FACEBOOK INC"],
                          "cik": [50104, 50104, 1326801, 1326801]}).assign(norm=lambda d: d.name.map(name_normalisieren))


def test_name_normalisieren():
    assert name_normalisieren("TESORO CORP /NEW/") == name_normalisieren("Tesoro Corporation") == "tesoro"
    assert name_normalisieren("Under Armour (Class A)") == "under armour"
    assert name_normalisieren("Procter & Gamble Co.") == "procter gamble"


def test_zu_und_abgang_gleicher_ticker_und_stichtag_regel():
    aenderungen = _aenderungen([
        ("2014-03-01", "NEU", "Neu AG", "ALT", "Alt AG", "Marktkapitalisierung"),
        ("2010-01-04", "ALT", "Alt AG", None, None, None),
    ])
    iv = mitgliedschaften(_aktuell([("NEU", "Neu AG", "IT", "2014-03-01", 1)]), aenderungen)
    alt = iv[iv.ticker == "ALT"].iloc[0]
    assert (alt.von, alt.bis) == (pd.Timestamp("2010-01-04"), pd.Timestamp("2014-03-01"))
    assert set(mitglieder_am(iv, "2014-02-28").ticker) == {"ALT"}             # Abgangstag: nicht mehr Mitglied
    assert set(mitglieder_am(iv, "2014-03-01").ticker) == {"NEU"}             # Zugangstag: schon Mitglied


def test_tickerwechsel_heutiges_mitglied_und_abgang_per_cik():
    aenderungen = _aenderungen([
        ("2007-09-27", "TSO", "Tesoro Corporation", None, None, None),
        ("2013-12-23", "FB", "Facebook", None, None, None),
        ("2018-10-01", None, None, "ANDV", "Andeavor", "Marathon übernahm Andeavor"),
    ])
    aktuell = _aktuell([("META", "Meta Platforms", "Kommunikation", "2013-12-23", 1326801)])
    iv = mitgliedschaften(aktuell, aenderungen, SEC_NAMEN).set_index("ticker")
    assert iv.loc["META", "ticker_frueher"] == "FB" and iv.loc["META", "von"] == pd.Timestamp("2013-12-23")
    assert iv.loc["ANDV", "ticker_frueher"] == "TSO"                          # gleiche CIK unter früherem Namen
    assert (iv.loc["ANDV", "von"], iv.loc["ANDV", "bis"]) == (pd.Timestamp("2007-09-27"), pd.Timestamp("2018-10-01"))
    assert iv.hinweis.isna().all()


def test_unbelegtes_aufnahmedatum_gilt_als_frueheres_mitglied():
    aenderungen = _aenderungen([("2016-01-04", "X", "X Corp", None, None, None)])
    aktuell = _aktuell([("X", "X Corp", "IT", "2016-01-04", 1), ("D", "Dominion", "Versorger", "2016-11-30", 2)])
    iv = mitgliedschaften(aktuell, aenderungen).set_index("ticker")
    assert pd.isna(iv.loc["D", "von"]) and "nicht durch Änderungstabelle belegt" in iv.loc["D", "hinweis"]
    assert "D" in set(mitglieder_am(iv.reset_index(), "2012-06-30").ticker)


def test_korrekturen():
    iv = mitgliedschaften(_aktuell([("SW", "Smurfit", "Material", "2024-07-08", 3)]),
                          _aenderungen([("1976-07-01", "BUD", "Anheuser Busch", None, None, None)]))
    korrigiert = korrekturen_anwenden(iv, [
        {"aktion": "beenden", "ticker": "BUD", "name": "Anheuser Busch", "bis": "2008-11-18", "quelle": "q1"},
        {"aktion": "von_setzen", "ticker": "SW", "name": "Smurfit", "von": "2024-07-08", "quelle": "q2"},
        {"aktion": "ergaenzen", "ticker": "WRK", "name": "WestRock", "von": "2015-07-02", "bis": "2024-07-08", "quelle": "q3"},
    ])
    assert list(anzahl_je_stichtag(korrigiert, ["2012-01-02", "2016-01-04", "2025-01-02"])) == [0, 1, 1]
    assert korrigiert.hinweis.str.startswith("korrigiert").all()
    with pytest.raises(ValueError, match="Treffer statt 1"):
        korrekturen_anwenden(iv, [{"aktion": "beenden", "ticker": "XYZ", "name": "?", "bis": "2020-01-01", "quelle": "q"}])


def test_cik_pruefungen():
    assert cik_kandidaten("Tesoro Corporation", SEC_NAMEN) == [50104]
    subs = {"filings": {"recent": {"filingDate": ["2016-02-11", "2017-02-03", "2016-05-01"], "form": ["10-K", "10-K", "10-Q"]}}}
    zk = zehn_k_daten(subs)
    assert list(zk) == [pd.Timestamp("2016-02-11"), pd.Timestamp("2017-02-03")]
    assert passt_zum_intervall(zk, "2006-04-03", pd.NaT)
    assert not passt_zum_intervall(zk, "2000-01-01", "2010-06-30")
    assert vorgaenger_fehlt(zk, "2006-04-03")                                 # wie Alphabet: 10-K erst ab 2016
    assert not vorgaenger_fehlt(zk, "2015-10-02")


def test_ueberdeckung_waehlt_die_passende_gesellschaft():
    from tradingbot.daten.universum import ueberdeckung_tage

    alte_ag = pd.DatetimeIndex(pd.to_datetime(["2010-03-01", "2011-03-01", "2012-03-01", "2013-03-01", "2014-03-01"]))
    neue_plc = pd.DatetimeIndex(pd.to_datetime(["2015-02-15", "2016-02-15", "2017-02-15", "2018-02-15", "2019-02-15", "2020-02-15"]))
    # Mitgliedschaft bis Mai 2020: die plc überdeckt mehr als die alte AG (obwohl beide 10-K im Zeitraum haben)
    assert ueberdeckung_tage(neue_plc, pd.NaT, "2020-05-12") > ueberdeckung_tage(alte_ag, pd.NaT, "2020-05-12")
    assert ueberdeckung_tage(pd.DatetimeIndex([]), pd.NaT, "2020-05-12") == 0


class _SubsClient:
    def __init__(self, namen):
        self.namen = namen

    def submissions(self, cik):
        name, frueher = self.namen[cik]
        return {"name": name, "formerNames": [{"name": n} for n in frueher]}, None


def test_cik_korrekturen_mit_namenspruefung():
    from tradingbot.daten.universum import cik_korrekturen_anwenden

    t = pd.DataFrame({"ticker": ["CA", "XOM"], "name": ["CA Technologies", "ExxonMobil"], "cik": pd.array([1376793, 2115436], dtype="Int64"),
                      "cik_quelle": ["sec_suche", "heutige_liste"], "cik_status": ["mehrdeutig", "keine_10k_im_zeitraum"],
                      "vorgaenger_pruefen": [False, True], "vorgaenger_status": [None, "neue_gesellschaft_ohne_10k"]})
    client = _SubsClient({356028: ("CA, INC.", ["COMPUTER ASSOCIATES INTERNATIONAL INC"]), 34088: ("EXXON MOBIL CORP", ["EXXON CORP"])})
    korrekturen = {"cik": [{"ticker": "CA", "name": "CA Technologies", "cik": 356028, "erwartet": "CA, INC"}],
                   "vorgaenger": [{"ticker": "XOM", "name": "ExxonMobil", "ciks": [34088], "erwartet": ["EXXON"]}]}
    neu = cik_korrekturen_anwenden(t, korrekturen, client).set_index("ticker")
    assert neu.loc["CA", "cik"] == 356028 and neu.loc["CA", "cik_status"] == "ok"
    assert neu.loc["XOM", "vorgaenger_ciks"] == [34088] and neu.loc["XOM", "cik_status"] == "ok_ueber_vorgaenger"
    falsch = {"cik": [{"ticker": "CA", "name": "CA Technologies", "cik": 34088, "erwartet": "CA, INC"}]}
    with pytest.raises(ValueError, match="erwartet war"):
        cik_korrekturen_anwenden(t, falsch, client)


def test_sic_aus_kopf_beide_formate():
    from tradingbot.daten.universum import sic_aus_kopf

    assert sic_aus_kopf("STANDARD INDUSTRIAL CLASSIFICATION:\tELECTRONIC COMPUTERS [3571]\n") == 3571
    assert sic_aus_kopf("<COMPANY-DATA>\n<CONFORMED-NAME>X\n<ASSIGNED-SIC>2834\n") == 2834
    assert sic_aus_kopf("kein Code") is None


class _KopfClient:
    """10-K von 2010 bis 2019; SIC wechselt mit dem 10-K von 2016 (z.B. REIT-Umwandlung)."""

    def __init__(self):
        self.abrufe = 0
        jahre = range(2010, 2020)
        self.recent = {"filingDate": [f"{j}-02-20" for j in jahre], "accessionNumber": [f"a{j}" for j in jahre], "form": ["10-K"] * 10}

    def submissions(self, cik):
        return {"filings": {"recent": self.recent, "files": []}}, None

    def einreichungskopf(self, cik, accn):
        self.abrufe += 1
        return f"<ASSIGNED-SIC>{4899 if int(accn[1:]) < 2016 else 6798}"


def test_sic_historie_findet_wechsel_mit_wenigen_abrufen():
    from tradingbot.daten.universum import ist_finanzwert, sic_am, sic_historie

    client = _KopfClient()
    historie = sic_historie(1, client)
    assert historie == [(pd.Timestamp("2010-02-20"), 4899), (pd.Timestamp("2016-02-20"), 6798)]
    assert client.abrufe <= 6                                               # Halbierung statt zehn Abrufe
    assert sic_am(historie, "2015-12-31") == 4899 and sic_am(historie, "2016-03-01") == 6798
    assert sic_am(historie, "2005-01-01") == 4899                           # vor dem ersten 10-K: erster Code
    assert ist_finanzwert(6798) and not ist_finanzwert(4899) and ist_finanzwert(None) is None
