"""SEC-Aktualisierung des Betriebs, Schritt 2 (Festlegung Jakob 23.11.2026; betrieb/secaktualisierung.py)."""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

import tradingbot.betrieb.speicher as speicher
import tradingbot.daten.cache as cache_modul
from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb import secaktualisierung as sa
from tradingbot.daten import schicht
from tradingbot.daten.abruf import Drossel
from tradingbot.daten.cache import ParquetCache
from tradingbot.daten.fehlerschwelle import Fehlerschwelle
from tradingbot.daten.sec import SecClient, cik10, erstmeldungen, fakten_tabelle, sec_cache, sec_rohwurzel


def _fakt(ende, wert, filed, accn, start="2023-01-01"):
    return {"start": start, "end": ende, "val": wert, "filed": filed, "form": "10-K", "accn": accn, "fy": 2023, "fp": "FY"}


def _facts(*fakten):
    return {"cik": 1, "entityName": "Beispiel AG", "facts": {"us-gaap": {"Revenues": {"units": {"USD": list(fakten)}}}}}


ALT = _facts(_fakt("2023-12-31", 100, "2024-02-15", "0000000001-24-000001"))
NEU_ANGEHAENGT = _facts(_fakt("2023-12-31", 100, "2024-02-15", "0000000001-24-000001"),
                        _fakt("2026-09-30", 80, "2026-11-05", "0000000001-26-000009", start="2026-07-01"),
                        _fakt("2023-12-31", 999, "2026-11-05", "0000000001-26-000009"))   # Vorjahr im neuen Bericht: keine Erstmeldung
NEU_RESTATEMENT_FRUEHER = _facts(_fakt("2023-12-31", 95, "2024-02-01", "0000000001-24-000000"))
NEU_ALTES_FILED = _facts(_fakt("2023-12-31", 100, "2024-02-15", "0000000001-24-000001"),
                         _fakt("2022-12-31", 70, "2025-03-01", "0000000001-25-000001", start="2022-01-01"))


def _erst(roh):
    """Erstmeldungen wie im Betrieb (im Betriebsmodus; sonst begrenzt der Tresor auf Einreichungen bis 2024)."""
    import tempfile
    from pathlib import Path

    with betriebsmodus("Test", protokoll=Path(tempfile.gettempdir()) / "tradingbot_test_freigaben.log"):
        return erstmeldungen(fakten_tabelle(roh))


# --- Prüfregeln ---------------------------------------------------------------------------------------------------
def test_grenze_ist_abrufdatum_minus_drei_tage():
    assert sa.grenze_fuer(datetime(2026, 11, 2, 0, 25, tzinfo=timezone.utc)) == pd.Timestamp("2026-10-30")
    assert sa.grenze_fuer(None) is None


def test_pruefregel_nur_anhaengen_besteht():
    ok, text, neue, hinweise = sa.pruefe_erstmeldungen(_erst(ALT), _erst(NEU_ANGEHAENGT), pd.Timestamp("2026-10-30"))
    assert ok and len(neue) == 1 and "1 neue" in text and hinweise == []


def test_pruefregel_geaenderte_erstmeldung_verletzt():
    ok, text, _, _ = sa.pruefe_erstmeldungen(_erst(ALT), _erst(NEU_RESTATEMENT_FRUEHER), pd.Timestamp("2026-10-30"),
                                             einreichung=lambda a: ("2024-02-01", "10-K"))   # Beleg hilft hier nie
    assert not ok and "geändert oder entfernt" in text and "accn 0000000001-24-000001" in text


def test_pruefregel_neue_zeile_mit_altem_filed_verletzt():
    ok, text, neue, _ = sa.pruefe_erstmeldungen(_erst(ALT), _erst(NEU_ALTES_FILED), pd.Timestamp("2026-10-30"))
    assert not ok and "vor 2026-10-30" in text and "ohne Beleg" in text and len(neue) == 1
    assert sa.pruefe_erstmeldungen(None, _erst(NEU_ALTES_FILED), None)[0]   # neue CIK ohne bisherigen Stand: alles erlaubt


def test_pruefregel_sic_nur_anhaengen():
    alt = [(pd.Timestamp("2010-02-26"), 2911)]
    assert sa.pruefe_sic(alt, alt + [(pd.Timestamp("2026-02-20"), 2912)])[0]
    assert sa.pruefe_sic([], [(pd.Timestamp("2026-02-20"), 7372)])[0]
    assert not sa.pruefe_sic(alt, [(pd.Timestamp("2010-02-26"), 2912)])[0]
    assert not sa.pruefe_sic(alt, [])[0]


def test_hoechste_rate():
    assert sa.hoechste_rate([i * 0.125 for i in range(10)]) == 8
    assert sa.hoechste_rate([]) == 0


# --- Lauf mit nachgestellter SEC -----------------------------------------------------------------------------------
class _Antwort:
    def __init__(self, status, daten=None, text=""):
        self.status_code, self._daten, self.text = status, daten, text
        self.content = (json.dumps(daten) if daten is not None else text).encode()
        self.headers = {}

    def json(self):
        return self._daten


ZUSATZ: dict = {}                      # weitere Einreichungen je CIK in den submissions: (Datum, accn, Formular)
ZEHN_K = {1: [("2024-02-15", "0000000001-24-000001", 3711), ("2026-11-05", "0000000001-26-000009", 3711)],
          2: [("2025-03-01", "0000000002-25-000001", 7372)]}


class _SEC:
    """Nachgestellte SEC: companyfacts, submissions und Köpfe je CIK; `gesperrt_ab`: ab dieser Anfrage HTTP 403."""

    def __init__(self, facts: dict, gesperrt_ab: int | None = None, fehlt=frozenset(), kaputt=frozenset()):
        self.facts, self.gesperrt_ab, self.fehlt, self.kaputt, self.aufrufe = facts, gesperrt_ab, fehlt, kaputt, []

    def get(self, url, headers=None, timeout=None):
        self.aufrufe.append(url)
        assert headers["User-Agent"] == "Test test@example.com"
        if self.gesperrt_ab is not None and len(self.aufrufe) >= self.gesperrt_ab:
            return _Antwort(403)
        cik = next((int(x[3:13]) for x in url.split("/") if x.startswith("CIK")), None)
        if "/companyfacts/" in url:
            if cik in self.kaputt:
                return _Antwort(400)
            return _Antwort(404) if cik in self.fehlt else _Antwort(200, self.facts[cik])
        if "/submissions/" in url:
            liste = [(d, a, "10-K") for d, a, _ in ZEHN_K.get(cik, [])] + ZUSATZ.get(cik, [])
            return _Antwort(200, {"filings": {"recent": {"filingDate": [d for d, _, _ in liste], "accessionNumber": [a for _, a, _ in liste],
                                                         "form": [f for _, _, f in liste]}, "files": []}})
        if url.endswith(".hdr.sgml"):
            sic = next(s for liste in ZEHN_K.values() for _, a, s in liste if a in url)
            return _Antwort(200, text=f"STANDARD INDUSTRIAL CLASSIFICATION: X [{sic}]")
        raise AssertionError(url)


@pytest.fixture
def betrieb(tmp_path, monkeypatch):
    """Entwicklungs-Cache mit CIK 1 (Stand 02.11.2026) und SIC-Historie; Betriebsbereich in tmp_path."""
    daten = tmp_path / "daten"
    standard = ParquetCache(daten / "cache")
    monkeypatch.setattr(cache_modul, "standard_cache", lambda: standard)
    monkeypatch.setattr(schicht, "_daten", lambda: daten.resolve())

    def betriebspfad(relativ="", **kw):
        p = daten / "betrieb" / relativ
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    monkeypatch.setattr(speicher, "betriebspfad", betriebspfad)
    datei = daten / "cache" / "sec" / "companyfacts" / "CIK0000000001.json.gz"
    datei.parent.mkdir(parents=True)
    with gzip.open(datei, "wt", encoding="utf-8") as f:
        json.dump({"url": "u", "abgerufen_um": "2026-11-02T00:25:00+00:00", "daten": ALT}, f)
    standard.schreiben("universum", "sic_historie",
                       pd.DataFrame({"cik": [1], "gueltig_ab": [pd.Timestamp("2024-02-15")], "sic": [3711]}), {})
    return daten, tmp_path / "freigaben.log"


def _clients(sec):
    d = Drossel(0.0)
    return (SecClient("Test test@example.com", sitzung=sec, drossel=d, pausen=()),
            SecClient("Test test@example.com", sitzung=sec, drossel=d, pausen=(), max_alter=timedelta(0)))


def _abdruck(wurzel):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in wurzel.rglob("*") if p.is_file()}


def test_lauf_uebernimmt_neue_meldungen_schreibt_stand_und_laesst_entwicklung_unveraendert(betrieb):
    daten, log = betrieb
    entwicklung_vorher = _abdruck(daten / "cache")
    sec = _SEC({1: NEU_ANGEHAENGT, 2: _facts(_fakt("2024-12-31", 5, "2025-03-01", "0000000002-25-000001", start="2024-01-01"))},
               fehlt={3})
    jetzt = datetime(2026, 12, 5, 9, 0, tzinfo=timezone.utc)
    with betriebsmodus("Test", protokoll=log):
        client, frisch = _clients(sec)
        erg = sa.aktualisieren([1, 2, 3], client=client, client_frisch=frisch, sec_tabellen=sec_cache(), jetzt=lambda: jetzt)
        stand = sa.stand_schreiben(sec_rohwurzel(), erg, ende=jetzt)
        e1, e2, e3 = (erg.je_cik[str(c)] for c in (1, 2, 3))
        assert erg.erfolgreich and not erg.meldungen
        assert e1["stand"] == "übernommen" and e1["neue_zeilen"] == 1 and e1["neueste_filed"] == "2026-11-05" and e1["sic_neu"] == 0
        assert e2["stand"] == "übernommen" and e2["sic_neu"] == 1 and e3["stand"] == "ohne Daten"
        assert len(sec_cache().lesen("sec_erstmeldungen", cik10(1))[0]) == 2
        assert sorted(sec_cache().lesen("universum", "sic_historie")[0]["cik"]) == [1, 2]
        assert stand["letzter_erfolg"] == jetzt.isoformat(timespec="seconds") and stand["zusammenfassung"]["neue_zeilen"] == 2
    assert _abdruck(daten / "cache") == entwicklung_vorher                 # Entwicklungs-Cache byteweise unverändert
    gespeichert = json.loads((daten / "betrieb" / "cache" / "sec" / "STAND.json").read_text(encoding="utf-8"))
    assert gespeichert["je_cik"]["1"]["stand"] == "übernommen" and gespeichert["erfolgreich"] is True


def test_verletzte_pruefregel_behaelt_alten_stand(betrieb):
    _, log = betrieb
    sec = _SEC({1: NEU_RESTATEMENT_FRUEHER})
    with betriebsmodus("Test", protokoll=log):
        client, frisch = _clients(sec)
        erg = sa.aktualisieren([1], client=client, client_frisch=frisch, sec_tabellen=sec_cache())
        assert erg.je_cik["1"]["stand"] == "alter Stand" and erg.erfolgreich
        assert "CIK 1 behält den alten Stand" in erg.meldungen[0]
        roh, abgerufen = client.companyfacts_aus_cache(1)
        assert roh == ALT and abgerufen == datetime.fromisoformat("2026-11-02T00:25:00+00:00")


def test_neues_filed_vor_der_grenze_behaelt_alten_stand(betrieb):
    _, log = betrieb
    with betriebsmodus("Test", protokoll=log):
        client, frisch = _clients(_SEC({1: NEU_ALTES_FILED}))
        erg = sa.aktualisieren([1], client=client, client_frisch=frisch, sec_tabellen=sec_cache())
        assert erg.je_cik["1"]["stand"] == "alter Stand" and "vor 2026-10-30" in erg.je_cik["1"]["text"]
        assert client.companyfacts_aus_cache(1)[0] == ALT


def test_403_bricht_sofort_ab_und_stand_behaelt_letzten_erfolg(betrieb):
    _, log = betrieb
    with betriebsmodus("Test", protokoll=log):
        wurzel = sec_rohwurzel()
        (wurzel / "STAND.json").write_text(json.dumps({"letzter_erfolg": "2026-11-28T09:01:00+00:00"}), encoding="utf-8")
        sec = _SEC({1: NEU_ANGEHAENGT, 2: NEU_ANGEHAENGT}, gesperrt_ab=1)
        client, frisch = _clients(sec)
        erg = sa.aktualisieren([1, 2], client=client, client_frisch=frisch, sec_tabellen=sec_cache())
        stand = sa.stand_schreiben(wurzel, erg, ende=datetime(2026, 12, 5, 9, 1, tzinfo=timezone.utc))
    assert len(sec.aufrufe) == 1 and "403" in erg.abbruch and not erg.erfolgreich
    assert stand["erfolgreich"] is False and stand["letzter_erfolg"] == "2026-11-28T09:01:00+00:00"
    assert stand["je_cik"]["1"]["stand"] == "Fehler" and "2" not in stand["je_cik"]
    assert erg.meldungen[0].startswith("SEC-Aktualisierung nicht erfolgreich")


def test_fehlerschwelle_macht_lauf_erfolglos_geprueftes_bleibt(betrieb, monkeypatch):
    _, log = betrieb
    monkeypatch.setattr(sa, "Fehlerschwelle", lambda b: Fehlerschwelle(b, mindestens=1))
    sec = _SEC({1: NEU_ANGEHAENGT}, kaputt={2})
    with betriebsmodus("Test", protokoll=log):
        client, frisch = _clients(sec)
        erg = sa.aktualisieren([1, 2], client=client, client_frisch=frisch, sec_tabellen=sec_cache())
        stand = sa.stand_schreiben(sec_rohwurzel(), erg, ende=datetime(2026, 12, 5, tzinfo=timezone.utc))
    assert not erg.erfolgreich and "fehlerhaft" in erg.abbruch
    assert stand["je_cik"]["1"]["stand"] == "übernommen" and stand["je_cik"]["2"]["stand"] == "Fehler"
    assert stand["letzter_erfolg"] is None and stand["erfolgreich"] is False


def test_geaenderte_sic_historie_behaelt_alten_sic_stand_fakten_getrennt(betrieb, monkeypatch):
    """Lauf 23.11.2026 (Probe, Google Inc.): Fakten übernommen, SIC-Historie geändert → SIC bleibt alt, beides sichtbar."""
    _, log = betrieb
    monkeypatch.setitem(ZEHN_K, 1, [("2010-02-12", "0000000001-10-000001", 3711)] + ZEHN_K[1])
    with betriebsmodus("Test", protokoll=log):
        client, frisch = _clients(_SEC({1: NEU_ANGEHAENGT}))
        erg = sa.aktualisieren([1], client=client, client_frisch=frisch, sec_tabellen=sec_cache())
        e = erg.je_cik["1"]
        assert e["stand"] == "alter Stand" and e["fakten"] == "übernommen" and e["sic"] == "alter Stand"
        assert sec_cache().lesen("universum", "sic_historie")[0]["gueltig_ab"].tolist() == [pd.Timestamp("2024-02-15")]
        assert client.companyfacts_aus_cache(1)[0] == NEU_ANGEHAENGT


# --- Nachtrag 23.11.2026: nachgelieferte Einreichungen ------------------------------------------------------------
JULI = "0000000001-26-000005"
NEU_NACHGELIEFERT = _facts(_fakt("2023-12-31", 100, "2024-02-15", "0000000001-24-000001"),
                           _fakt("2026-06-30", 70, "2026-07-29", JULI, start="2026-04-01"),
                           _fakt("2026-06-30", 71, "2026-07-29", JULI, start="2026-01-01"),
                           _fakt("2026-09-30", 80, "2026-11-05", "0000000001-26-000009", start="2026-07-01"))


def test_nachgelieferte_einreichung_mit_beleg_ist_hinweis():
    beleg = {JULI: ("2026-07-29", "10-Q")}.get
    ok, text, neue, hinweise = sa.pruefe_erstmeldungen(_erst(ALT), _erst(NEU_NACHGELIEFERT), pd.Timestamp("2026-10-30"),
                                                       alt_accn=frozenset({"0000000001-24-000001"}), einreichung=beleg)
    assert ok and len(neue) == 3 and "2 aus 1 nachgelieferten" in text
    assert hinweise == [{"accn": JULI, "form": "10-Q", "filed": "2026-07-29", "zeilen": 2}]


def test_nachlieferung_ohne_bedingung_a_oder_b_bleibt_verletzung():
    grenze = pd.Timestamp("2026-10-30")
    # (a) verletzt: die accn kommt im bisherigen Stand schon vor (etwa in einem Fakt, der keine Erstmeldung ist)
    ok, text, _, _ = sa.pruefe_erstmeldungen(_erst(ALT), _erst(NEU_NACHGELIEFERT), grenze,
                                             alt_accn=frozenset({"0000000001-24-000001", JULI}),
                                             einreichung={JULI: ("2026-07-29", "10-Q")}.get)
    assert not ok and "ohne Beleg" in text
    # (b) verletzt: anderes Datum in den submissions, oder gar nicht dort
    for beleg in ({JULI: ("2026-07-30", "10-Q")}.get, {}.get, None):
        ok, _, _, hinweise = sa.pruefe_erstmeldungen(_erst(ALT), _erst(NEU_NACHGELIEFERT), grenze,
                                                     alt_accn=frozenset({"0000000001-24-000001"}), einreichung=beleg)
        assert not ok and hinweise == []


def test_einreichungen_aus_submissions_laedt_zusatzseiten_nur_bei_bedarf():
    subs = {"filings": {"recent": {"filingDate": ["2026-07-29"], "accessionNumber": [JULI], "form": ["10-Q"]},
                        "files": [{"name": "CIK0000000001-submissions-001.json"}]}}
    geladen = []

    def seite(name):
        geladen.append(name)
        return {"filingDate": ["2012-02-15"], "accessionNumber": ["0000000001-12-000001"], "form": ["10-K"]}

    nachschlagen = sa.einreichungen_aus_submissions(subs, seite)
    assert nachschlagen(JULI) == ("2026-07-29", "10-Q") and geladen == []
    assert nachschlagen("0000000001-12-000001") == ("2012-02-15", "10-K") and len(geladen) == 1
    assert nachschlagen("fehlt") is None and len(geladen) == 1


def test_lauf_mit_nachgelieferter_einreichung_uebernimmt_und_meldet_hinweis(betrieb, monkeypatch):
    _, log = betrieb
    monkeypatch.setitem(ZUSATZ, 1, [("2026-07-29", JULI, "10-Q")])
    jetzt = datetime(2026, 12, 5, 9, 0, tzinfo=timezone.utc)
    with betriebsmodus("Test", protokoll=log):
        client, frisch = _clients(_SEC({1: NEU_NACHGELIEFERT}))
        erg = sa.aktualisieren([1], client=client, client_frisch=frisch, sec_tabellen=sec_cache(), jetzt=lambda: jetzt)
        stand = sa.stand_schreiben(sec_rohwurzel(), erg, ende=jetzt)
        assert erg.je_cik["1"]["stand"] == "übernommen" and not erg.meldungen
        assert erg.hinweise == [{"cik": 1, "firma": "Beispiel AG", "accn": JULI, "form": "10-Q", "filed": "2026-07-29", "zeilen": 2}]
        assert stand["hinweise"] == erg.hinweise and stand["zusammenfassung"]["hinweise"] == 1
        assert client.companyfacts_aus_cache(1)[0] == NEU_NACHGELIEFERT
