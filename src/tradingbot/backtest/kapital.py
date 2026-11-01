"""Kapitalaufteilung Core/Satellite mit Schattenbetrieb (Entscheidung 01.11.2026, config/backtest.yaml).

Solange der Satellite-Anteil unter dem Mindestkapital (1.250 €) liegt, fließt er in den Core, und der
Satellite läuft als Schattenportfolio mit virtuellem Kapital. Danach werden beide echt geführt.
"""
from __future__ import annotations


def kapitalplan(gesamt: float, konfig: dict | None = None) -> dict[str, float]:
    """Gibt {core, satellite, satellite_schatten} in Euro zurück; genau einer der Satellite-Werte ist > 0."""
    if konfig is None:
        from tradingbot.konfiguration import lade_konfiguration

        konfig = lade_konfiguration("backtest")
    k = konfig["kapital"]
    satellite = gesamt * float(k["aufteilung"]["satellite"])
    if satellite < float(k["satellite_mindestkapital"]):
        return {"core": gesamt, "satellite": 0.0, "satellite_schatten": float(k["satellite_schattenkapital"])}
    return {"core": gesamt - satellite, "satellite": satellite, "satellite_schatten": 0.0}
