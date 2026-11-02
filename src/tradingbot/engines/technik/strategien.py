"""Satellite-Strategien der Technik-Engine (Entscheidungen Jakob 02.11.2026, config/technik.yaml).

Rahmen für alle Strategien (`SatelliteStrategie`, Schnittstelle `backtest.strategie.Strategie`):
- Signale auf den Tagesschluss, Ausführung zur Eröffnung des nächsten Handelstags (Simulation).
- Positionsgröße: 1 % Risiko je Trade bei Stop 2 × ATR(20):  Gewicht = 0,01 · Schluss / (2 · ATR),
  höchstens 25 % je ETF (10 % je Einzelaktie); begrenzt durch freie Kasse. Die 125-€-Regel prüft die Simulation.
- Stop: Einstiegskurs (Eröffnung des Kauftags) − 2 × ATR(20) vom Signaltag, fest; geprüft auf den Tagesschluss.
- Zeit-Stop in Handelstagen seit dem Kauf: „zwang“ (RSI(2) 10, Price Channel 63) oder „bedingt“ (Crossover,
  Momentum 63: nur verkaufen, wenn das Einstiegssignal nicht mehr gilt).
- Mehr Signale als Plätze: Vergabe nach Stärke der jeweiligen Regel.
- Regime (ADX(14) je ETF am Signaltag): über 25 nur Trend und Ausbruch, unter 20 nur RSI(2), dazwischen alle.
  Ausstiege folgen immer der Regel, die den Einstieg erzeugt hat.

Indikatoren werden einmal aus den vollständigen Kursreihen berechnet; jeder Wert am Tag t hängt nur von Daten bis t
ab (Test `test_indikatoren_ohne_blick_nach_vorn`). Die Strategie liest am Tag t ausschließlich Werte bis t.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from tradingbot.engines.technik.indikatoren import adx, atr, donchian_hoch, donchian_tief, momentum_12_1, rsi, sma

TREND, AUSBRUCH, UMKEHR = "trend", "ausbruch", "umkehr"


@dataclass
class Position:
    regel: str
    signal_tag: pd.Timestamp
    kauf_tag: pd.Timestamp | None = None
    stop: float | None = None
    atr_signal: float = math.nan


class Regel:
    """Basisklasse einer Einstiegs- und Ausstiegsregel je Ticker."""

    name = "regel"
    familie = TREND
    zeit_stop = 0                 # 0 = keiner
    zeit_stop_art = "zwang"       # zwang | bedingt

    def __init__(self, ind: dict[str, pd.DataFrame]):
        self.ind = ind

    def einstieg(self, ticker, tag) -> float | None:
        """Stärke des Einstiegssignals am Tag (höher = stärker) oder None."""
        raise NotImplementedError

    def ausstieg(self, ticker, tag) -> str | None:
        raise NotImplementedError

    def nach_stop(self, ticker, tag):
        pass

    def tag_ende(self, ticker, tag):
        pass


class Crossover(Regel):
    """Two MA Crossover: investiert, solange SMA50 > SMA200; Ausstieg beim Kreuzen nach unten.
    Nach einem Stop wieder, sobald der Kurs über SMA50 schließt und SMA50 > SMA200 gilt (Jakob 02.11.2026; der Schluss
    am Stop-Tag zählt nicht). Stärke = SMA50/SMA200 − 1 (prozentualer Abstand)."""

    name, familie = "crossover", TREND

    def __init__(self, ind, zeit_stop=63):
        super().__init__(ind)
        self.zeit_stop, self.zeit_stop_art = zeit_stop, "bedingt"
        self.gesperrt: dict[str, pd.Timestamp] = {}

    def _ueber(self, t, tag):
        z = self.ind[t].loc[tag]
        return pd.notna(z["sma_schnell"]) and pd.notna(z["sma_langsam"]) and z["sma_schnell"] > z["sma_langsam"]

    def einstieg(self, t, tag):
        if not self._ueber(t, tag):
            return None
        z = self.ind[t].loc[tag]
        if t in self.gesperrt:
            if tag <= self.gesperrt[t] or not z["close"] > z["sma_schnell"]:
                return None
            del self.gesperrt[t]
        return z["sma_schnell"] / z["sma_langsam"] - 1

    def ausstieg(self, t, tag):
        z = self.ind[t].loc[tag]
        return "SMA50 unter SMA200" if pd.notna(z["sma_langsam"]) and not self._ueber(t, tag) else None

    def nach_stop(self, t, tag):
        self.gesperrt[t] = tag


class Momentum(Regel):
    """Zeitreihen-Momentum 12−1, monatlich geprüft (erster Handelstag des Monats): investiert, wenn 12−1 > 0.
    Ausstieg bei der Monatsprüfung, wenn 12−1 ≤ 0. Stärke = 12−1-Wert."""

    name, familie = "momentum", TREND

    def __init__(self, ind, zeit_stop=63):
        super().__init__(ind)
        self.zeit_stop, self.zeit_stop_art = zeit_stop, "bedingt"
        self.pruefmonat: dict[str, pd.Period] = {}

    def _pruefung(self, t, tag) -> bool:
        return self.pruefmonat.get(t) != tag.to_period("M")

    def einstieg(self, t, tag):
        if not self._pruefung(t, tag):
            return None
        m = self.ind[t].loc[tag, "mom"]
        return float(m) if pd.notna(m) and m > 0 else None

    def ausstieg(self, t, tag):
        if not self._pruefung(t, tag):
            return None
        m = self.ind[t].loc[tag, "mom"]
        return "12−1 ≤ 0" if pd.notna(m) and m <= 0 else None

    def gilt_noch(self, t, tag) -> bool:
        m = self.ind[t].loc[tag, "mom"]
        return pd.notna(m) and m > 0

    def tag_ende(self, t, tag):
        self.pruefmonat[t] = tag.to_period("M")


class PriceChannel(Regel):
    """Donchian-Ausbruch: Einstieg, wenn der Schluss über dem Hoch der letzten 55 Tage liegt; Ausstieg, wenn er unter
    dem Tief der letzten 20 Tage liegt. Stärke = (Schluss − 55-Tage-Hoch) / ATR."""

    name, familie = "price_channel", AUSBRUCH

    def __init__(self, ind, zeit_stop=63):
        super().__init__(ind)
        self.zeit_stop, self.zeit_stop_art = zeit_stop, "zwang"

    def einstieg(self, t, tag):
        z = self.ind[t].loc[tag]
        if pd.notna(z["hoch_55"]) and z["close"] > z["hoch_55"] and z["atr"] > 0:
            return (z["close"] - z["hoch_55"]) / z["atr"]
        return None

    def ausstieg(self, t, tag):
        z = self.ind[t].loc[tag]
        return "Schluss unter 20-Tage-Tief" if pd.notna(z["tief_20"]) and z["close"] < z["tief_20"] else None


class Rsi2(Regel):
    """RSI(2) < 10 und Schluss über SMA200 → Einstieg; Ausstieg, wenn der Schluss über SMA5 liegt.
    Stärke = −RSI (am stärksten überverkauft zuerst)."""

    name, familie = "rsi2", UMKEHR

    def __init__(self, ind, zeit_stop=10, grenze=10.0):
        super().__init__(ind)
        self.zeit_stop, self.zeit_stop_art, self.grenze = zeit_stop, "zwang", grenze

    def einstieg(self, t, tag):
        z = self.ind[t].loc[tag]
        if pd.notna(z["rsi2"]) and pd.notna(z["sma_trend"]) and z["rsi2"] < self.grenze and z["close"] > z["sma_trend"]:
            return -float(z["rsi2"])
        return None

    def ausstieg(self, t, tag):
        z = self.ind[t].loc[tag]
        return "Schluss über SMA5" if pd.notna(z["sma_kurz"]) and z["close"] > z["sma_kurz"] else None


def berechne_indikatoren(kurse: pd.DataFrame, konfig: dict) -> pd.DataFrame:
    """Alle Indikatoren eines Tickers als Tabelle (je Tag; jeder Wert nur aus Daten bis zu diesem Tag)."""
    s, sat = konfig["strategien"], konfig["satellite"]
    c = kurse["close"]
    return pd.DataFrame({
        "close": c,
        "sma_schnell": sma(c, s["crossover"]["schnell"]),
        "sma_langsam": sma(c, s["crossover"]["langsam"]),
        "mom": momentum_12_1(c, s["momentum"]["monate"], s["momentum"]["ohne_letzte_monate"]),
        "hoch_55": donchian_hoch(kurse["high"], s["price_channel"]["einstieg_hoch_tage"]),
        "tief_20": donchian_tief(kurse["low"], s["price_channel"]["ausstieg_tief_tage"]),
        "rsi2": rsi(c, s["rsi2"]["tage"]),
        "sma_trend": sma(c, s["rsi2"]["trendfilter_sma"]),
        "sma_kurz": sma(c, s["rsi2"]["ausstieg_ueber_sma"]),
        "atr": atr(kurse, sat["atr_tage"]),
        "adx": adx(kurse, s["regime"]["adx_tage"]),
    })


REGELN = {"crossover": Crossover, "momentum": Momentum, "price_channel": PriceChannel, "rsi2": Rsi2}
# Reihenfolge bei gleichzeitigen Signalen im Regime (Claude, zur Prüfung): Trend vor Ausbruch vor Umkehr
REIHENFOLGE = ["momentum", "crossover", "price_channel", "rsi2"]


class SatelliteStrategie:
    """Strategie aus einer oder mehreren Regeln, optional mit ADX-Regime."""

    def __init__(self, regeln: list[str], kurse: dict[str, pd.DataFrame], konfig: dict, *, regime: bool = False,
                 klassen: dict[str, str] | None = None):
        sat = konfig["satellite"]
        self.konfig = konfig
        self.ind = {t: berechne_indikatoren(k, konfig) for t, k in kurse.items()}
        self.kurse = kurse
        zs = sat["zeit_stop_tage"]
        self.regeln = {n: REGELN[n](self.ind, zeit_stop=zs[n]) for n in REIHENFOLGE if n in regeln}
        self.regime = regime
        r = konfig["strategien"]["regime"]
        self.stark, self.schwach = float(r["stark_ueber"]), float(r["schwach_unter"])
        self.risiko = float(sat["risiko_je_trade"])
        self.stop_faktor = float(sat["stop_atr_faktor"])
        self.max_position = {k: float(v) for k, v in sat["max_position"].items()}
        self.klassen = klassen or {t: "etf" for t in kurse}
        self.pos: dict[str, Position] = {}
        self.protokoll: list[dict] = []
        self.name = ("Regime: " if regime else "") + "+".join(self.regeln)

    # --- Hilfen ------------------------------------------------------------------------------------------------
    def _regime_erlaubt(self, regel: Regel, t, tag) -> bool:
        if not self.regime:
            return True
        a = self.ind[t].loc[tag, "adx"]
        if pd.isna(a):
            return False
        if a > self.stark:
            return regel.familie in (TREND, AUSBRUCH)
        if a < self.schwach:
            return regel.familie == UMKEHR
        return True

    def _gewicht(self, t, tag) -> float:
        z = self.ind[t].loc[tag]
        if not (z["atr"] > 0):
            return 0.0
        return min(self.risiko * z["close"] / (self.stop_faktor * z["atr"]), self.max_position.get(self.klassen.get(t, "etf"), 0.10))

    def _handelstage_seit(self, t, von, bis) -> int:
        idx = self.ind[t].index
        return int(((idx > von) & (idx <= bis)).sum())

    def _log(self, tag, t, aktion, regel, grund, gewicht=None):
        self.protokoll.append({"tag": tag, "ticker": t, "aktion": aktion, "regel": regel, "grund": grund, "gewicht": gewicht})

    # --- Schnittstelle ------------------------------------------------------------------------------------------
    def zielgewichte(self, stichtag, sicht):
        tag = pd.Timestamp(stichtag)
        bestand = {t for t, s in sicht.bestand.items() if s > 0}
        gewichte = sicht.gewichte() if bestand else pd.Series(dtype=float)
        ziel: dict[str, float] = {}

        # Abgleich mit dem tatsächlichen Bestand (Kauf ausgeführt, verworfen oder Verkauf ausgeführt)
        for t in list(self.pos):
            p = self.pos[t]
            if t in bestand and p.kauf_tag is None:
                kauf_tag = self.ind[t].index[self.ind[t].index > p.signal_tag][0]
                p.kauf_tag = kauf_tag
                p.stop = float(self.kurse[t].loc[kauf_tag, "open"]) - self.stop_faktor * p.atr_signal
            elif t not in bestand and (p.kauf_tag is not None or tag >= self.ind[t].index[self.ind[t].index > p.signal_tag][0]):
                del self.pos[t]

        # Ausstiege
        for t in sorted(bestand):
            p = self.pos.get(t)
            if p is None or p.kauf_tag is None or tag not in self.ind[t].index:
                continue
            regel = self.regeln[p.regel]
            z = self.ind[t].loc[tag]
            grund = None
            if z["close"] <= p.stop:
                grund = f"Stop {p.stop:.2f}"
                regel.nach_stop(t, tag)
            elif (g := regel.ausstieg(t, tag)) is not None:
                grund = g
            elif regel.zeit_stop and self._handelstage_seit(t, p.kauf_tag, tag) >= regel.zeit_stop:
                if regel.zeit_stop_art == "zwang":
                    grund = f"Zeit-Stop {regel.zeit_stop} Tage"
                elif not (regel.gilt_noch(t, tag) if hasattr(regel, "gilt_noch") else regel.einstieg(t, tag) is not None):
                    grund = f"Zeit-Stop {regel.zeit_stop} Tage, Signal erloschen"
            if grund:
                ziel[t] = 0.0
                self._log(tag, t, "verkaufen", p.regel, grund)

        # Einstiege
        belegt = float(gewichte.drop([t for t in ziel if t in gewichte.index]).sum()) if len(gewichte) else 0.0
        frei = max(0.0, 1.0 - belegt - 0.005)               # kleiner Puffer für Kosten und Rundung
        kandidaten = []
        for rang, (name, regel) in enumerate(self.regeln.items()):
            for t in self.ind:
                if t in bestand or t in self.pos or tag not in self.ind[t].index:
                    continue
                if not self._regime_erlaubt(regel, t, tag):
                    continue
                staerke = regel.einstieg(t, tag)
                if staerke is not None:
                    kandidaten.append((rang, -staerke, t, name))
        gewaehlt: set[str] = set()
        for _, _, t, name in sorted(kandidaten):
            if t in gewaehlt or frei <= 0:
                continue
            w = min(self._gewicht(t, tag), frei)
            if w <= 0:
                continue
            ziel[t] = w
            frei -= w
            gewaehlt.add(t)
            self.pos[t] = Position(name, tag, atr_signal=float(self.ind[t].loc[tag, "atr"]))
            self._log(tag, t, "kaufen", name, f"Signal, Stärke {-_staerke(kandidaten, t, name):.4f}", w)

        for regel in self.regeln.values():
            for t in self.ind:
                if tag in self.ind[t].index:
                    regel.tag_ende(t, tag)
        if not ziel:
            return None
        return pd.Series({**{t: math.nan for t in bestand if t not in ziel}, **ziel}, dtype=float)


def _staerke(kandidaten, t, name) -> float:
    return next(s for _, s, tt, n in kandidaten if tt == t and n == name)


def score(stichtag, universum, kurse: dict[str, pd.DataFrame], konfig: dict, regime: bool = True) -> pd.Series:
    """Engine-Schnittstelle: Zahl der aktiven Einstiegssignale je Ticker am Stichtag (regimegefiltert).

    Nur Kurse bis zum Stichtag werden verwendet. Monatliche Momentum-Prüfung gilt hier an jedem Tag.
    """
    tag = pd.Timestamp(stichtag)
    teil = {t: kurse[t].loc[:tag] for t in universum if t in kurse and len(kurse[t].loc[:tag])}
    s = SatelliteStrategie(list(REGELN), teil, konfig, regime=regime)
    werte = {}
    for t in teil:
        if tag not in s.ind[t].index:
            werte[t] = 0.0
            continue
        werte[t] = float(sum(1 for r in s.regeln.values() if s._regime_erlaubt(r, t, tag) and r.einstieg(t, tag) is not None))
    return pd.Series(werte, dtype=float).reindex(list(universum)).fillna(0.0)
