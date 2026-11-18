"""Befund 19, Schritt 1: eingefrorener Universumsstand für Backtest und c3 (Jakob 17.11.2026)."""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from tradingbot.daten import universum as u
from tradingbot.konfiguration import PROJEKT_WURZEL


def _sha(pfad) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


@pytest.fixture
def stand_im_ordner(tmp_path):
    t = pd.DataFrame({"ticker": ["A", "B"], "von": pd.to_datetime([None, "2015-01-02"]), "bis": pd.to_datetime([None, None]),
                      "cik": pd.array([1, 2], dtype="Int64")})
    t.to_parquet(tmp_path / "universum.parquet")
    (tmp_path / "a.html.gz").write_bytes(b"aktuell")
    (tmp_path / "h.html.gz").write_bytes(b"historie")
    stand = {"zeitpunkt_utc": "2026-10-29T22:20:50+00:00",
             "aktuell": {"revid": 1, "datei": "a.html.gz", "sha256": _sha(tmp_path / "a.html.gz")},
             "historie": {"revid": 2, "datei": "h.html.gz", "sha256": _sha(tmp_path / "h.html.gz")},
             "universum": {"datei": "universum.parquet", "zeilen": 2, "sha256": _sha(tmp_path / "universum.parquet")}}
    return tmp_path, stand, t


def test_eingefrorener_stand_wird_geladen(stand_im_ordner):
    ordner, stand, t = stand_im_ordner
    geladen, meta = u.lade_eingefrorenen_stand(ordner, stand)
    pd.testing.assert_frame_equal(geladen, t, check_dtype=False)   # Zeiteinheit nach Parquet egal (s/ms)
    assert meta["revid_aktuell"] == 1 and meta["revid_historie"] == 2 and meta["stand"] == "eingefroren"


@pytest.mark.parametrize("teil", ["aktuell", "historie", "universum"])
def test_veraenderte_datei_bricht_laut_ab(stand_im_ordner, teil):
    ordner, stand, _ = stand_im_ordner
    datei = ordner / stand[teil]["datei"]
    datei.write_bytes(datei.read_bytes() + b"x")
    with pytest.raises(u.StandPasstNicht, match="SHA-256"):
        u.lade_eingefrorenen_stand(ordner, stand)


def test_fehlende_datei_bricht_laut_ab(stand_im_ordner):
    ordner, stand, _ = stand_im_ordner
    (ordner / "h.html.gz").unlink()
    with pytest.raises(u.StandPasstNicht, match="fehlt"):
        u.lade_eingefrorenen_stand(ordner, stand)


def test_falsche_zeilenzahl_bricht_laut_ab(stand_im_ordner):
    ordner, stand, _ = stand_im_ordner
    stand["universum"]["zeilen"] = 3
    with pytest.raises(u.StandPasstNicht, match="Zeilen"):
        u.lade_eingefrorenen_stand(ordner, stand)


def test_eingefrorener_stand_wird_nie_neu_berechnet():
    with pytest.raises(ValueError, match="nicht neu berechnet"):
        u.lade_universum(neu_berechnen=True)
    with pytest.raises(ValueError, match="Unbekannter"):
        u.lade_universum(stand="live")


def test_betrieb_nutzt_den_laufenden_stand(monkeypatch):
    """universum_aktualisieren (Tageslauf) liest weiter den Betriebsstand, nie den eingefrorenen (Sperre bis Schritt 3)."""
    aufrufe = []
    monkeypatch.setattr(u, "lade_wikipedia", lambda **kw: None)

    def lade(neu_berechnen=False, stand="eingefroren"):
        aufrufe.append(stand)
        return pd.DataFrame({"ticker": ["A"], "von": pd.to_datetime(["2020-01-02"]), "bis": pd.to_datetime([None])}), {}

    monkeypatch.setattr(u, "lade_universum", lade)
    u.universum_aktualisieren()
    assert aufrufe == ["betrieb"]


def test_bewertung_des_betriebs_nutzt_den_laufenden_stand():
    import inspect

    from tradingbot.engines.fundamental import aktuell

    assert 'lade_universum(stand="betrieb")' in inspect.getsource(aktuell.bewertung_am)


_ORDNER = PROJEKT_WURZEL / "daten" / "universum" / "eingefroren"


@pytest.mark.skipif(not _ORDNER.exists(), reason="eingefrorener Stand nicht lokal vorhanden")
def test_echter_stand_besteht_abnahme_a_und_b():
    """(a) 896 Zeilen, (b) alle 813 Statuszeilen passen über Zeilennummer und Schlüssel (ticker, von, bis)."""
    t, _ = u.lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv", keep_default_na=False)
    tag = lambda v: "" if v in ("", None) or pd.isna(v) else str(pd.Timestamp(v).date())  # noqa: E731
    assert len(t) == 896 and len(status) == 813
    falsch = [r.index for r in status.itertuples()
              if (t.at[r.index, "ticker"], tag(t.at[r.index, "von"]), tag(t.at[r.index, "bis"])) != (r.ticker, tag(r.von), tag(r.bis))]
    assert falsch == []
