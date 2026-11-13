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


def _nachlader(tmp_path, sitzung, grenzen=None, heute=date(2026, 11, 14)):
    client = TiingoClient("test", cache_wurzel=tmp_path, sitzung=sitzung, anfragen_pro_stunde=1000)
    return Nachlader(client, grenzen=grenzen, heute=lambda: heute, ende="2024-12-31")


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
