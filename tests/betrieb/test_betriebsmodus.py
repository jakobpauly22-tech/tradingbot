"""Betriebsfreigabe und abgeschotteter Betriebsbereich (Entscheidung Jakob 02.11.2026)."""
import pandas as pd
import pytest

from tradingbot.backtest.tresor import TresorGesperrt, betriebsmodus, datengrenze, im_betriebsmodus
from tradingbot.betrieb.speicher import BetriebsbereichGesperrt, betriebspfad


def test_betriebsmodus_hebt_grenze_auf_und_protokolliert(tmp_path):
    log = tmp_path / "freigaben.log"
    assert datengrenze() == pd.Timestamp("2024-12-31")
    with betriebsmodus("Tageslauf Test", protokoll=log):
        assert im_betriebsmodus() and datengrenze() is None
    assert datengrenze() == pd.Timestamp("2024-12-31") and not im_betriebsmodus()
    assert "Tageslauf Test" in log.read_text(encoding="utf-8")


def test_betriebsbereich_ausserhalb_gesperrt(tmp_path):
    with pytest.raises(BetriebsbereichGesperrt):
        betriebspfad("journal.sqlite", wurzel=tmp_path)
    with betriebsmodus("Test", protokoll=tmp_path / "log"):
        pfad = betriebspfad("journal.sqlite", wurzel=tmp_path)
    assert pfad.parent.name == "betrieb"


def test_backtest_im_betriebsmodus_verweigert(tmp_path):
    from tradingbot.backtest.marktdaten import Marktdaten
    from tradingbot.backtest.simulation import simuliere
    with betriebsmodus("Test", protokoll=tmp_path / "log"):
        with pytest.raises(TresorGesperrt, match="Betriebsmodus"):
            simuliere([], Marktdaten({}), "2024-01-01", "2024-01-31")
