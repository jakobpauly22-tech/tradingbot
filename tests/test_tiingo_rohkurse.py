"""Nachladen unbereinigter Tiingo-Kurse bis zur Tresorgrenze (Weg A, Jakob 13.11.2026): Zeitraum, Tresor, Grenzen,
Wiederaufnahme, Fehler. Ohne Netz (Sitzung nachgestellt)."""
import json
from datetime import date

import pandas as pd
import pytest

from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.tiingo_rohkurse import Grenzen, Nachlader, lade_rohkurse, tiingo_ticker


class _Antwort:
    def __init__(self, status, daten):
        self.status_code, self._daten, self.text = status, daten, json.dumps(daten)

    def json(self):
        return self._daten


class _Sitzung:
    def __init__(self, fehlt=()):
        self.aufrufe, self.fehlt = [], set(fehlt)

    def get(self, url, params=None, headers=None, timeout=None):
        self.aufrufe.append((url, dict(params or {})))
        ticker = url.split("/daily/")[1].split("/")[0]
        if ticker in self.fehlt:
            return _Antwort(404, {"detail": "not found"})
        if url.endswith("/prices"):
            return _Antwort(200, [{"date": "2024-12-30T00:00:00.000Z", "close": 1180.0, "splitFactor": 1.0, "volume": 5.0},
                                  {"date": "2024-12-31T00:00:00.000Z", "close": 1185.8, "splitFactor": 1.0, "volume": 5.0},
                                  {"date": "2025-01-02T00:00:00.000Z", "close": 1190.0, "splitFactor": 1.0, "volume": 5.0}])
        return _Antwort(200, {"ticker": ticker, "name": f"{ticker.upper()} Inc"})


def _nachlader(tmp_path, sitzung, grenzen=None, heute=date(2026, 11, 14), gelistet=(), pausen=None):
    client = TiingoClient("test", cache_wurzel=tmp_path, sitzung=sitzung, anfragen_pro_stunde=1000)
    zusatz = {"pausen": pausen} if pausen is not None else {}
    return Nachlader(client, grenzen=grenzen, heute=lambda: heute, ende="2024-12-31", bekannt=lambda t: t in set(gelistet),
                     schlafen=lambda s: None, **zusatz)


def test_zeitraum_bis_tresorgrenze_und_nichts_danach(tmp_path):
    s = _Sitzung()
    n = _nachlader(tmp_path, s)
    assert n.lade("orly") == "geladen"
    preise = [p for u, p in s.aufrufe if u.endswith("/prices")][0]
    assert preise["startDate"] == "2011-01-01" and preise["endDate"] == "2024-12-31"
    k = lade_rohkurse("ORLY", ablage=n.ablage)
    assert k.index.max() == pd.Timestamp("2024-12-31") and k["close"].iloc[-1] == 1185.8      # 2025 nicht gespeichert
    assert k.attrs["name"] == "ORLY Inc"


def test_wiederaufnahme_ueberspringt_vorhandene(tmp_path):
    s = _Sitzung()
    n = _nachlader(tmp_path, s)
    n.lade("orly")
    vorher = len(s.aufrufe)
    assert n.lade("orly") == "vorhanden" and len(s.aufrufe) == vorher


def test_monatsgrenze_symbole(tmp_path):
    n = _nachlader(tmp_path, _Sitzung(), Grenzen(monat_symbole=2))
    assert [n.lade(t) for t in ("a", "b", "c")] == ["geladen", "geladen", "grenze"]
    assert "Monatsgrenze 2" in n.grenze_erreicht(n.stand())
    neu = _nachlader(tmp_path, _Sitzung(), Grenzen(monat_symbole=2), heute=date(2026, 12, 1))      # neuer Monat
    assert neu.lade("c") == "geladen"


def test_tagesgrenze_und_datenvolumen(tmp_path):
    n = _nachlader(tmp_path, _Sitzung(), Grenzen(tag_anfragen=4))
    assert [n.lade(t) for t in ("a", "b", "c")] == ["geladen", "geladen", "grenze"]
    m = _nachlader(tmp_path / "v", _Sitzung(), Grenzen(monat_bytes=1))
    assert [m.lade(t) for t in ("a", "b")] == ["geladen", "grenze"]


def test_dauerhafter_fehler_wird_nicht_wiederholt(tmp_path):
    s = _Sitzung(fehlt={"weg"})
    n = _nachlader(tmp_path, s)
    assert n.lade("weg") == "fehler" and n.stand()["fehler"]["weg"]["dauerhaft"]
    vorher = len(s.aufrufe)
    assert n.lade("weg") == "uebersprungen" and len(s.aufrufe) == vorher


def test_ohne_tresorgrenze_kein_nachladen(monkeypatch, tmp_path):
    from tradingbot.backtest import tresor
    monkeypatch.setattr(tresor, "datengrenze", lambda konfig=None: None)
    client = TiingoClient("test", cache_wurzel=tmp_path, sitzung=_Sitzung())
    with pytest.raises(RuntimeError, match="Tresorgrenze"):
        Nachlader(client)


def test_ticker_schreibweise():
    assert tiingo_ticker("BRK-B") == "brk-b" and tiingo_ticker("BF.B") == "bf-b"



# --- META (14.11.2026) und Netzfehler (Jakob 15.11.2026) ---------------------------------------------------------------
class _MetaSitzung(_Sitzung):
    """Wie bei META: Metadaten-URL /tiingo/daily/meta liefert 404, die Kurse unter /meta/prices gibt es."""

    def get(self, url, params=None, headers=None, timeout=None):
        if url.rstrip("/").endswith("/daily/meta"):
            self.aufrufe.append((url, dict(params or {})))
            return _Antwort(404, {"detail": "not found"})
        return super().get(url, params, headers, timeout)


def test_meta_metadaten_404_laedt_trotzdem_kurse(tmp_path):
    n = _nachlader(tmp_path, _MetaSitzung(), gelistet={"meta"})
    assert n.lade("meta") == "geladen"
    k = lade_rohkurse("META", ablage=n.ablage)
    assert k["close"].iloc[-1] == 1185.8 and k.attrs["name"] is None
    assert "meta" not in n.stand()["fehler"]


def test_alter_dauerfehler_aus_metadaten_wird_erneut_versucht(tmp_path):
    n = _nachlader(tmp_path, _MetaSitzung(), gelistet={"meta"})
    s = n.stand()
    s["fehler"]["meta"] = {"zeit": "2026-11-14T18:39:04", "fehler": "Tiingo: https://api.tiingo.com/tiingo/daily/meta nicht gefunden",
                           "dauerhaft": True}
    s["monate"]["2026-11"] = {"symbole": ["meta"], "bytes": 0}
    n._speichern(s)
    assert n.lade("meta") == "geladen"


def test_kurs_404_bei_gelistetem_ticker_nicht_dauerhaft(tmp_path):
    n = _nachlader(tmp_path, _Sitzung(fehlt={"neu"}), gelistet={"neu"})
    assert n.lade("neu") == "fehler"
    eintrag = n.stand()["fehler"]["neu"]
    assert not eintrag["dauerhaft"] and "Tiingos Liste" in eintrag["fehler"]
    assert n.lade("neu") == "fehler"                         # wird erneut versucht, nicht übersprungen


class _WackeligeSitzung(_Sitzung):
    def __init__(self, abbrueche):
        super().__init__()
        self.abbrueche = abbrueche

    def get(self, url, params=None, headers=None, timeout=None):
        import requests

        if self.abbrueche > 0:
            self.abbrueche -= 1
            self.aufrufe.append((url, dict(params or {})))
            raise requests.ConnectionError(ConnectionResetError(10054, "Verbindung vom Remotehost geschlossen"))
        return super().get(url, params, headers, timeout)


def test_verbindungsabbruch_wird_wiederholt_und_gezaehlt(tmp_path):
    n = _nachlader(tmp_path, _WackeligeSitzung(2))
    assert n.lade("orly") == "geladen"
    assert n.stand()["tage"]["2026-11-14"] == 4               # 2 gezählt vorab + 2 Wiederholungen


def test_netz_dauerhaft_weg_haelt_an(tmp_path):
    n = _nachlader(tmp_path, _WackeligeSitzung(100), pausen=(1, 2))
    assert n.lade("orly") == "netz"
    eintrag = n.stand()["fehler"]["orly"]
    assert not eintrag["dauerhaft"] and "nach 3 Versuchen" in eintrag["fehler"]
    assert not n.datei("orly").exists()
