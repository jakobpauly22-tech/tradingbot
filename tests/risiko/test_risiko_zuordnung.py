"""Risiko-Übersicht Schritt 1: Zuordnung der Titel (docs/RISIKO_UEBERSICHT.md, Abschnitt 4)."""
import gzip
import json

import pytest

from tradingbot.daten import schicht
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko import zuordnung as zu


def _gz(datei, daten):
    datei.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(datei, "wt", encoding="utf-8") as f:
        json.dump({"url": "u", "abgerufen_um": "2026-11-20T00:00:00", "daten": daten}, f)


def _adresse(code=None, beschr=None, ausland=None, land=None, landcode=None):
    return {"addresses": {"business": {"stateOrCountry": code, "stateOrCountryDescription": beschr, "isForeignLocation": ausland,
                                       "country": land, "countryCode": landcode}}}


@pytest.fixture
def sec_wurzel(tmp_path):
    w = tmp_path / "sec"
    _gz(w / "company_tickers.json.gz", {"0": {"cik_str": 1, "ticker": "BF-B", "title": "Brown Forman"},
                                         "1": {"cik_str": 2, "ticker": "XIR", "title": "Beispiel Sitz USA, Irland"},
                                         "2": {"cik_str": 3, "ticker": "MDT", "title": "Medtronic"},
                                         "3": {"cik_str": 4, "ticker": "OHNE", "title": "ohne Angaben"}})
    _gz(w / "submissions" / "CIK0000000001.json.gz",
        {"sic": "2080", "stateOfIncorporation": "DE", "stateOfIncorporationDescription": "DE", **_adresse("KY", "KY")})
    _gz(w / "submissions" / "CIK0000000002.json.gz",
        {"sic": "3842", "stateOfIncorporation": "L2", "stateOfIncorporationDescription": "Ireland", **_adresse("OH", "OH")})
    _gz(w / "submissions" / "CIK0000000003.json.gz",
        {"sic": "3845", "stateOfIncorporation": "", **_adresse(ausland=1, land="Ireland", landcode="L2")})
    _gz(w / "submissions" / "CIK0000000004.json.gz", {"sic": "", **_adresse()})
    return w


@pytest.fixture
def etfs():
    return lade_konfiguration("risiko_uebersicht")["etfs"]


KONTRAKTE = {"BF-B": {"waehrung": "USD", "art": "aktie"}, "XIR": {"waehrung": "USD", "art": "aktie"},
             "MDT": {"waehrung": "USD", "art": "aktie"}, "OHNE": {"waehrung": "USD", "art": "aktie"},
             "NEU": {"waehrung": "USD", "art": "aktie"},
             "IUSA.DE": {"waehrung": "EUR", "art": "etf"}, "4GLD.DE": {"waehrung": "EUR", "art": "etc"},
             "FREMD.DE": {"waehrung": "EUR", "art": "etf"}}


def _z(ticker, sec_wurzel, etfs):
    return zu.zuordnen(ticker, etfs=etfs, kontrakte=KONTRAKTE, sec=zu.SecStammdaten(sec_wurzel))


def test_einzelaktie_us_adresse_ergibt_usa_division_und_major_group(sec_wurzel, etfs):
    z = _z("BF-B", sec_wurzel, etfs)
    assert (z.art, z.anlageklasse, z.land, z.inkorporation) == ("Einzelaktie", "Aktie", "USA", "USA")
    assert z.sektor == "D Verarbeitendes Gewerbe" and z.sektor_gruppe == "20 Nahrungsmittel und Getränke" and z.sic == 2080
    assert (z.waehrung_notierung, z.waehrung_wirtschaftlich, z.kennzeichen) == ("USD", "USD", zu.EXAKT)


def test_sitz_usa_inkorporation_irland(sec_wurzel, etfs):
    z = _z("XIR", sec_wurzel, etfs)
    assert (z.land, z.inkorporation) == ("USA", "Ireland")


def test_auslaendische_adresse_ueber_country(sec_wurzel, etfs):
    z = _z("MDT", sec_wurzel, etfs)
    assert (z.land, z.inkorporation, z.kennzeichen) == ("Ireland", "–", zu.EXAKT)


def test_auslaendischer_edgar_code_ohne_auslandskennzeichen():
    assert zu.land_geschaeftssitz(_adresse("X0", "United Kingdom")) == "United Kingdom"
    assert zu.land_geschaeftssitz(_adresse("L2", None)) == "L2"


def test_fehlt_im_cache_oder_ohne_angaben_unbekannt(sec_wurzel, etfs):
    z = _z("NEU", sec_wurzel, etfs)
    assert (z.land, z.sektor, z.kennzeichen) == (zu.UNBEKANNT, zu.UNBEKANNT, zu.UNBEKANNT)
    assert "nicht im SEC-Cache" in z.hinweise[0]
    z = _z("OHNE", sec_wurzel, etfs)
    assert (z.land, z.sektor, z.kennzeichen) == (zu.UNBEKANNT, zu.UNBEKANNT, zu.UNBEKANNT) and len(z.hinweise) == 2


def test_sic_division_grenzen_und_major_group_ohne_namen():
    assert zu.sic_division(1311)[0] == "B" and zu.sic_division(6798)[0] == "H" and zu.sic_division(7372)[0] == "I"
    assert zu.sic_division(50) is None and zu.sic_division(None) is None
    assert zu.sic_major_group(6770) == "67 Holdings und Investmentgesellschaften"
    assert zu.sic_major_group(6699) == "66"


def test_etf_nach_indexregion_ohne_aufteilung(sec_wurzel, etfs):
    z = _z("IUSA.DE", sec_wurzel, etfs)
    assert (z.art, z.anlageklasse, z.land, z.sektor) == ("ETF", "Aktien", "USA", "breit gestreut")
    assert (z.waehrung_notierung, z.waehrung_wirtschaftlich, z.kennzeichen) == ("EUR", "USD", zu.NAEHERUNG_INDEXREGION)
    g = _z("4GLD.DE", sec_wurzel, etfs)
    assert (g.art, g.anlageklasse, g.land, g.sektor, g.waehrung_wirtschaftlich) == ("ETC", "Gold (ETC)", "–", zu.KEIN_SEKTOR, "Gold")


def test_unbekannter_etf_wird_gemeldet(sec_wurzel, etfs):
    z = _z("FREMD.DE", sec_wurzel, etfs)
    assert z.kennzeichen == zu.UNBEKANNT and "fehlt in config/risiko_uebersicht.yaml" in z.hinweise[0]


def test_etf_tabelle_deckt_core_und_satellite_universum_ab(etfs):
    technik = lade_konfiguration("technik")
    betrieb = lade_konfiguration("betrieb")
    erwartet = {e["ticker"] for e in technik["universum"]["etfs"]} | {betrieb["core"]["etf"]}
    assert set(etfs) == erwartet and len(etfs) == 12
    assert all(e["sektor"] in ("breit gestreut", None) for e in etfs.values())
    assert etfs["IUSP.DE"]["anlageklasse"].startswith("Anleihen")       # SEML = IUSP.DE, EM-Lokalwährungsanleihen


def test_schluessel_ist_yahoo_ticker_nicht_ibkr_symbol(sec_wurzel, etfs):
    kontrakte = lade_konfiguration("kontrakte")["kontrakte"]
    assert kontrakte["IUSP.DE"]["symbol"] == "SEML"
    z = zu.zuordnen("SEML", etfs=etfs, kontrakte=kontrakte, sec=zu.SecStammdaten(sec_wurzel))
    assert z.kennzeichen == zu.UNBEKANNT                                 # IBKR-Symbol ist kein Schlüssel
    assert zu.zuordnen("IUSP.DE", etfs=etfs, kontrakte=kontrakte, sec=zu.SecStammdaten(sec_wurzel)).land == "Schwellenländer"


def test_kein_sec_client_und_kein_netz(sec_wurzel, etfs, monkeypatch):
    from tradingbot.daten import sec

    def verboten(*a, **k):
        raise AssertionError("SecClient darf in der Risiko-Übersicht nicht gebaut werden")

    monkeypatch.setattr(sec.SecClient, "__init__", verboten)
    for t in ("BF-B", "NEU", "IUSA.DE"):
        _z(t, sec_wurzel, etfs)


def test_probe_schicht_wird_zuerst_gelesen(tmp_path, etfs, monkeypatch):
    daten = tmp_path / "daten"
    monkeypatch.setattr(schicht, "_daten", lambda: daten.resolve())
    wurzel = daten / "betrieb" / "cache" / "sec"
    _gz(wurzel / "company_tickers.json.gz", {"0": {"cik_str": 9, "ticker": "NUR", "title": "x"}})
    s = daten / "betrieb" / "probe" / "cache"
    _gz(s / "betrieb" / "cache" / "sec" / "submissions" / "CIK0000000009.json.gz", {"sic": "7372", **_adresse("CA", "CA")})
    with schicht.probe_schicht(s):
        z = zu.zuordnen("NUR", etfs=etfs, kontrakte={}, sec=zu.SecStammdaten(wurzel))
    assert (z.land, z.sektor_gruppe) == ("USA", "73 Unternehmensdienste und Software")
    z = zu.zuordnen("NUR", etfs=etfs, kontrakte={}, sec=zu.SecStammdaten(wurzel))
    assert z.land == zu.UNBEKANNT                                        # ohne Schicht: Datei fehlt im Original
