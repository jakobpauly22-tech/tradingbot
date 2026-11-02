r"""Gegenprobe Crossover 50/200 auf einem ETF: Bot-Seite (TradingView-Seite: tools/tradingview/crossover_gegenprobe.pine).

Aufruf:  .venv\Scripts\python tools\gegenprobe_crossover.py [TICKER]   (Standard SXR8.DE)
Einstellungen wie im Pine Script: 1.250 € Startkapital, Gebühr 1,25 € je Order (IBKR-Minimum, bei Orders unter
2.500 € exakt), kein Spread, keine Slippage, keine Steuern, ganze Stücke, 1-%-Gebührenregel, Zeitraum laut
config/technik.yaml. Ergebnis: daten/technik/gegenprobe_crossover_<ticker>.csv (Trades) und Endwert auf der Konsole.
Vergleich: Trades (Datum, Richtung, Stück) und Endwert mit der Liste of Trades im Strategy Tester.
"""
import sys
import warnings

import pandas as pd

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.backtest.marktdaten import Instrument, Marktdaten
from tradingbot.backtest.simulation import Ausfuehrungsregeln, TeilportfolioDefinition, simuliere
from tradingbot.backtest.steuern import Steuerregeln
from tradingbot.daten.kurse import lade_kurse_eur
from tradingbot.engines.technik.strategien import SatelliteStrategie
from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

warnings.simplefilter("ignore")


def main(ticker: str = "SXR8.DE") -> int:
    k = lade_konfiguration("technik")
    bt = lade_konfiguration("backtest")
    kurse = lade_kurse_eur(ticker, str(k["backtest"]["daten_ab"]), str(k["backtest"]["gewertet_bis"]))
    start = pd.Timestamp("2013-01-03")   # gewerteter Beginn laut tools/backtest_technik.py (alle ETFs 12 Monate Historie)
    kosten = Kostenmodell(gebuehren={"EUR": {"satz": 0.0, "minimum": 1.25, "maximum": 1.25}}, spread={}, slippage=0.0)
    s = SatelliteStrategie(["crossover"], {ticker: kurse}, k)
    d = TeilportfolioDefinition("gegenprobe", float(k["backtest"]["kapital"]), s, [Instrument(ticker, "etf")], rolle="satellite")
    e = simuliere([d], Marktdaten({ticker: kurse}), start, kurse.index[-1], kosten=kosten, regeln=Ausfuehrungsregeln(),
                  steuern=Steuerregeln.ohne_steuern(), konfig=bt)["gegenprobe"]
    ziel = PROJEKT_WURZEL / "daten" / "technik"
    ziel.mkdir(parents=True, exist_ok=True)
    e.trades.to_csv(ziel / f"gegenprobe_crossover_{ticker.replace('.', '_')}.csv", index=False)
    print(e.trades[["datum", "richtung", "stueck", "eroeffnung", "gebuehr"]].to_string(index=False))
    print(f"Endwert {e.wert.iloc[-1]:.2f} € (Start {start.date()}), Trades {len(e.trades)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
