"""Betriebsbereich daten/betrieb: Journal, Buchzustände, Protokolle des Paper Tradings.

Nur im Betriebsmodus (backtest/tresor.betriebsmodus) zugänglich. Backtest- und Auswertungswerkzeuge laufen nie im
Betriebsmodus (sie verweigern den Start) und kommen deshalb nicht an diese Daten (Entscheidung Jakob 02.11.2026).
"""
from __future__ import annotations

from pathlib import Path

from tradingbot.backtest.tresor import TresorGesperrt, im_betriebsmodus


class BetriebsbereichGesperrt(TresorGesperrt):
    """Zugriff auf Betriebsdaten außerhalb des Betriebsmodus."""


def betriebspfad(relativ: str = "", *, wurzel: Path | None = None) -> Path:
    """Pfad im Betriebsbereich; außerhalb des Betriebsmodus gesperrt."""
    if not im_betriebsmodus():
        raise BetriebsbereichGesperrt("Betriebsdaten sind nur im Tageslauf (Betriebsmodus) zugänglich")
    from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

    basis = (wurzel or PROJEKT_WURZEL) / lade_konfiguration("betrieb")["daten"]["betriebsbereich"]
    pfad = basis / relativ if relativ else basis
    pfad.parent.mkdir(parents=True, exist_ok=True)
    return pfad
