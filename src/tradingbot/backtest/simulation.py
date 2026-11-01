"""Tagesschleife des Backtests.

Ablauf je Handelstag t:
1. Dividenden mit Ex-Tag t gutschreiben (Anspruch hat, wer vor Handelsbeginn hält).
2. Offene Zielgewichte vom Vortag zur Eröffnung ausführen: erst Verkäufe, dann Käufe.
3. Bewertung zum Schlusskurs (fehlende Kurse: letzter bekannter Schluss).
4. Strategie mit der Sicht bis t fragen; neue Zielgewichte werden am nächsten Handelstag ausgeführt.

Regeln der Ausführung (config/backtest.yaml):
- Nur long, keine Margin: Käufe nur aus vorhandenem Cash, Verkäufe höchstens bis zum Bestand.
- Ganze Stücke (IBKR-API bietet keine Bruchteile).
- Käufe und Aufstockungen nur, wenn Gebühr plus Währungstausch höchstens `max_gebuehr_anteil` (1 %) des
  Orderwerts sind; sonst wird die Order verworfen und protokolliert. Verkäufe (Ausstiege, Stops, Zeit-Stops,
  gebrochene These, Reduzierungen) sind immer erlaubt (Jakob, 01.11.2026).

Bekannte Vereinfachung: Yahoo-Kurse sind rückwirkend splitbereinigt, Stückzahlen vor einem Split sind
daher „bereinigte Stück“. Das betrifft nur die Rundung auf ganze Stücke und Gebühren je Stück (USA).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from tradingbot.backtest.kosten import Kostenmodell
from tradingbot.backtest.marktdaten import Instrument, Marktdaten, Sicht
from tradingbot.backtest.portfolio import TOLERANZ, Teilportfolio
from tradingbot.backtest.strategie import Strategie
from tradingbot.backtest.tresor import TresorFreigabe, pruefe_zeitraum


@dataclass(frozen=True)
class Ausfuehrungsregeln:
    max_gebuehr_anteil: float = 0.01
    ganze_stuecke: bool = True

    @classmethod
    def aus_konfig(cls, konfig: dict | None = None) -> "Ausfuehrungsregeln":
        if konfig is None:
            from tradingbot.konfiguration import lade_konfiguration

            konfig = lade_konfiguration("backtest")
        a = konfig["ausfuehrung"]
        return cls(max_gebuehr_anteil=float(a["max_gebuehr_anteil"]), ganze_stuecke=bool(a["ganze_stuecke"]))


@dataclass
class TeilportfolioDefinition:
    name: str
    startkapital: float
    strategie: Strategie
    instrumente: list[Instrument]
    art: str = "echt"             # echt | schatten (virtuelles Kapital, getrennt ausgewiesen)
    steuergruppe: str = "depot"   # Teilportfolios einer Gruppe teilen Pauschbetrag und Verlusttöpfe

    def __post_init__(self):
        if self.art not in ("echt", "schatten"):
            raise ValueError("art muss 'echt' oder 'schatten' sein")


@dataclass
class Ergebnis:
    name: str
    strategie: str
    werte: pd.DataFrame          # je Tag: wert, cash
    bestaende: pd.DataFrame      # je Tag: Stück je Ticker
    trades: pd.DataFrame
    verworfen: pd.DataFrame
    dividenden: pd.DataFrame
    meta: dict = field(default_factory=dict)

    @property
    def wert(self) -> pd.Series:
        return self.werte["wert"]


_TRADE_SPALTEN = [
    "datum", "ticker", "richtung", "stueck", "eroeffnung", "ausfuehrungspreis", "kurswert",
    "gebuehr", "waehrungstausch", "spread_slippage", "einstand_fifo", "gewinn_realisiert",
]


class _Lauf:
    """Simulation eines Teilportfolios."""

    def __init__(self, definition, marktdaten, kosten, regeln):
        self.d = definition
        self.m = marktdaten
        self.kosten = kosten
        self.regeln = regeln
        self.klassen = {i.ticker: i.klasse for i in definition.instrumente}
        self.portfolio = Teilportfolio(definition.name, definition.startkapital)
        self.trades: list[dict] = []
        self.verworfen: list[dict] = []
        self.dividenden: list[dict] = []

    # --- Hilfen -----------------------------------------------------------------------------------
    def _stueck_runden(self, stueck: float) -> float:
        return math.floor(stueck + 1e-9) if self.regeln.ganze_stuecke else stueck

    def _gebuehren(self, tag, ticker, stueck, kurswert) -> tuple[float, float]:
        waehrung = self.m.waehrungen[ticker]
        return self.kosten.gebuehren_eur(waehrung, stueck, kurswert, self.m.eur_kurs(waehrung, tag))

    def _verwerfen(self, tag, ticker, richtung, stueck, grund):
        self.verworfen.append({"datum": tag, "ticker": ticker, "richtung": richtung, "stueck": stueck, "grund": grund})

    def _gebuehrenregel_ok(self, gebuehr, tausch, kurswert) -> bool:
        return kurswert > 0 and gebuehr + tausch <= self.regeln.max_gebuehr_anteil * kurswert + 1e-12

    # --- Tagesschritte ----------------------------------------------------------------------------
    def dividenden_gutschreiben(self, tag):
        for ticker, stueck in self.portfolio.bestand().items():
            kerze = self.m.kerze(ticker, tag)
            if kerze is not None and kerze["dividende"] > 0:
                betrag = stueck * float(kerze["dividende"])
                self.portfolio.cash += betrag
                self.dividenden.append({"datum": tag, "ticker": ticker, "stueck": stueck, "je_stueck": float(kerze["dividende"]), "betrag": betrag})

    def ausfuehren(self, tag, ziel: pd.Series):
        if (ziel < 0).any():
            raise ValueError(f"{self.d.strategie.name}: negative Gewichte sind nicht erlaubt (nur long)")
        if ziel.sum() > 1 + 1e-9:
            raise ValueError(f"{self.d.strategie.name}: Summe der Gewichte {ziel.sum():.4f} > 1 (kein Hebel)")
        unbekannt = set(ziel.index) - set(self.klassen)
        if unbekannt:
            raise ValueError(f"{self.d.strategie.name}: Ticker außerhalb des Universums: {sorted(unbekannt)}")

        bestand = self.portfolio.bestand()
        betroffen = sorted(set(bestand) | set(ziel.index))
        # Ohne Eröffnungskurs gilt der Schluss des Vortags (der heutige Schluss ist morgens noch unbekannt)
        vortage = self.m.schluss.loc[self.m.schluss.index < tag]
        schluss_vortag = vortage.iloc[-1] if len(vortage) else pd.Series(dtype=float)
        eroeffnung, bewertung = {}, {}
        for ticker in betroffen:
            kerze = self.m.kerze(ticker, tag)
            if kerze is not None and kerze["open"] > 0:
                eroeffnung[ticker] = bewertung[ticker] = float(kerze["open"])
            elif pd.notna(schluss_vortag.get(ticker)):
                bewertung[ticker] = float(schluss_vortag[ticker])
        gesamtwert = self.portfolio.cash + sum(s * bewertung[t] for t, s in bestand.items())

        plan = {}
        for ticker in betroffen:
            zielwert = float(ziel.get(ticker, 0.0)) * gesamtwert
            if ticker not in eroeffnung:
                if abs(zielwert - bestand.get(ticker, 0.0) * bewertung.get(ticker, 0.0)) > 0.005 * gesamtwert:
                    self._verwerfen(tag, ticker, 0, 0, "kein Handel an diesem Tag")
                continue
            ziel_stueck = zielwert / eroeffnung[ticker]
            plan[ticker] = ziel_stueck - bestand.get(ticker, 0.0)

        # Verkäufe zuerst, damit Cash für Käufe frei wird
        for ticker, delta in sorted(plan.items(), key=lambda x: x[1]):
            if delta >= -TOLERANZ:
                continue
            vorhanden = bestand[ticker]
            ziel_stueck = vorhanden + delta
            stueck = vorhanden if ziel_stueck <= TOLERANZ else vorhanden - self._stueck_runden_auf(ziel_stueck)
            if stueck > TOLERANZ:
                self._verkaufen(tag, ticker, min(stueck, vorhanden), eroeffnung[ticker])

        # Käufe, größte Lücke zuerst
        kaeufe = sorted(((t, d) for t, d in plan.items() if d > TOLERANZ), key=lambda x: -x[1] * eroeffnung[x[0]])
        for ticker, delta in kaeufe:
            self._kaufen(tag, ticker, delta, eroeffnung[ticker])

    def _stueck_runden_auf(self, stueck: float) -> float:
        """Zielbestand beim Verkauf aufrunden: Es wird nur so viel verkauft, wie das Ziel verlangt (weniger Umschlag)."""
        return math.ceil(stueck - 1e-9) if self.regeln.ganze_stuecke else stueck

    def _verkaufen(self, tag, ticker, stueck, kurs):
        # Ausstiege und Reduzierungen sind immer erlaubt, auch wenn die Gebühr über 1 % liegt (Jakob, 01.11.2026)
        preis = self.kosten.ausfuehrungspreis(kurs, -1, self.klassen[ticker])
        kurswert = stueck * preis
        gebuehr, tausch = self._gebuehren(tag, ticker, stueck, kurswert)
        if gebuehr + tausch > kurswert:
            self._verwerfen(tag, ticker, -1, stueck, f"Gebühren {gebuehr + tausch:.2f} € übersteigen den Erlös {kurswert:.2f} €")
            return
        ergebnis = self.portfolio.verkaufen(tag, ticker, stueck, preis, gebuehr + tausch)
        self.trades.append(dict(zip(_TRADE_SPALTEN, [
            tag, ticker, -1, stueck, kurs, preis, kurswert, gebuehr, tausch, stueck * (kurs - preis), ergebnis.einstand, ergebnis.gewinn,
        ])))

    def _kaufen(self, tag, ticker, delta, kurs):
        preis = self.kosten.ausfuehrungspreis(kurs, +1, self.klassen[ticker])
        stueck = self._stueck_runden(delta * kurs / preis)  # Zielwert durch den teureren Ausführungspreis
        if stueck <= TOLERANZ:
            return  # Abweichung vom Ziel kleiner als ein Stück: keine Order nötig
        # So weit reduzieren, bis Kurswert plus Gebühren ins Cash passen
        for _ in range(3):
            if stueck <= TOLERANZ:
                break
            gebuehr, tausch = self._gebuehren(tag, ticker, stueck, stueck * preis)
            if stueck * preis + gebuehr + tausch <= self.portfolio.cash + 1e-9:
                break
            stueck = self._stueck_runden(max(self.portfolio.cash - gebuehr - tausch, 0.0) / preis)
        if stueck <= TOLERANZ:
            self._verwerfen(tag, ticker, +1, 0, "zu wenig Cash für ein Stück")
            return
        kurswert = stueck * preis
        gebuehr, tausch = self._gebuehren(tag, ticker, stueck, kurswert)
        if stueck * preis + gebuehr + tausch > self.portfolio.cash + 1e-9:
            self._verwerfen(tag, ticker, +1, stueck, "zu wenig Cash")
            return
        if not self._gebuehrenregel_ok(gebuehr, tausch, kurswert):
            self._verwerfen(tag, ticker, +1, stueck, f"Gebühren {gebuehr + tausch:.2f} € > {self.regeln.max_gebuehr_anteil:.0%} von {kurswert:.2f} €")
            return
        self.portfolio.kaufen(tag, ticker, stueck, preis, gebuehr + tausch)
        self.trades.append(dict(zip(_TRADE_SPALTEN, [
            tag, ticker, +1, stueck, kurs, preis, kurswert, gebuehr, tausch, stueck * (preis - kurs), None, None,
        ])))


def simuliere(
    definitionen: list[TeilportfolioDefinition],
    marktdaten: Marktdaten,
    start,
    ende,
    *,
    kosten: Kostenmodell | None = None,
    regeln: Ausfuehrungsregeln | None = None,
    tresor_freigabe: TresorFreigabe | None = None,
    konfig: dict | None = None,
) -> dict[str, Ergebnis]:
    """Simuliert jedes Teilportfolio getrennt (eigenes Cash, Verluste berühren die anderen nie)."""
    pruefe_zeitraum(ende, freigabe=tresor_freigabe, konfig=konfig)
    kosten = kosten or Kostenmodell.aus_konfig(konfig)
    regeln = regeln or Ausfuehrungsregeln.aus_konfig(konfig)
    tage = marktdaten.kalender[(marktdaten.kalender >= pd.Timestamp(start)) & (marktdaten.kalender <= pd.Timestamp(ende))]
    if len(tage) == 0:
        raise ValueError(f"Keine Handelstage zwischen {start} und {ende}")

    ergebnisse = {}
    for definition in definitionen:
        lauf = _Lauf(definition, marktdaten, kosten, regeln)
        offen: pd.Series | None = None
        werte, bestaende = [], []
        for tag in tage:
            lauf.dividenden_gutschreiben(tag)
            if offen is not None:
                lauf.ausfuehren(tag, offen)
                offen = None
            schluss = marktdaten.schluss.loc[tag]
            werte.append({"datum": tag, "wert": lauf.portfolio.wert(schluss), "cash": lauf.portfolio.cash})
            bestaende.append({"datum": tag, **lauf.portfolio.bestand()})
            ziel = definition.strategie.zielgewichte(tag, Sicht(marktdaten, tag))
            if ziel is not None:
                offen = pd.Series(ziel, dtype=float)

        ergebnisse[definition.name] = Ergebnis(
            name=definition.name,
            strategie=definition.strategie.name,
            werte=pd.DataFrame(werte).set_index("datum"),
            bestaende=pd.DataFrame(bestaende).set_index("datum").fillna(0.0),
            trades=pd.DataFrame(lauf.trades, columns=_TRADE_SPALTEN),
            verworfen=pd.DataFrame(lauf.verworfen, columns=["datum", "ticker", "richtung", "stueck", "grund"]),
            dividenden=pd.DataFrame(lauf.dividenden, columns=["datum", "ticker", "stueck", "je_stueck", "betrag"]),
            meta={"start": str(tage[0].date()), "ende": str(tage[-1].date()), "startkapital": definition.startkapital,
                  "art": definition.art, "steuergruppe": definition.steuergruppe, "kosten": kosten, "regeln": regeln},
        )
    return ergebnisse
