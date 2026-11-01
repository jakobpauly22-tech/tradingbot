"""Transaktionskosten: IBKR-Gebühren, Spread, Slippage, Währungstausch (Werte in config/backtest.yaml)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Kostenmodell:
    gebuehren: dict = field(default_factory=dict)       # je Handelswährung
    spread: dict = field(default_factory=dict)          # halbe Geld-Brief-Spanne je Instrumentklasse
    slippage: float = 0.0
    fx_satz: float = 0.0
    fx_minimum_usd: float = 0.0
    ohne_gebuehren: bool = False

    @classmethod
    def aus_konfig(cls, konfig: dict | None = None) -> "Kostenmodell":
        if konfig is None:
            from tradingbot.konfiguration import lade_konfiguration

            konfig = lade_konfiguration("backtest")
        kosten = konfig["kosten"]
        return cls(
            gebuehren=kosten["gebuehren"],
            spread=kosten["spread"],
            slippage=float(kosten["slippage"]),
            fx_satz=float(kosten["waehrungstausch"]["satz"]),
            fx_minimum_usd=float(kosten["waehrungstausch"]["minimum_usd"]),
        )

    @classmethod
    def ohne_kosten(cls) -> "Kostenmodell":
        """Für Gegenproben: keine Gebühren, kein Spread, keine Slippage."""
        return cls(ohne_gebuehren=True)

    def ausfuehrungspreis(self, kurs: float, richtung: int, klasse: str) -> float:
        """Kauf (richtung +1) zahlt halben Spread plus Slippage auf, Verkauf (−1) bekommt entsprechend weniger.

        Formel: P_ausf = P_eröffnung · (1 + richtung · (s/2 + slippage))
        """
        aufschlag = (self.spread.get(klasse, 0.0) if self.spread else 0.0) + self.slippage
        return kurs * (1.0 + richtung * aufschlag)

    def gebuehren_eur(self, waehrung: str, stueck: float, orderwert_eur: float, eur_kurs: float) -> tuple[float, float]:
        """(Ordergebühr, Währungstausch) in EUR.

        EUR-Börsen: max(Minimum, Satz · Orderwert), höchstens Maximum.
        USD-Börsen: max(Minimum, je Stück · Stückzahl), höchstens max_anteil · Orderwert; dazu Währungstausch
        max(Minimum, Satz · Orderwert) in USD. Umrechnung mit `eur_kurs` (USD je 1 EUR).
        """
        if self.ohne_gebuehren:
            return 0.0, 0.0
        if waehrung not in self.gebuehren:
            raise KeyError(f"Gebührenmodell für {waehrung} fehlt in config/backtest.yaml")
        g = self.gebuehren[waehrung]
        if waehrung == "EUR":
            gebuehr = max(g["minimum"], g["satz"] * orderwert_eur)
            return min(gebuehr, g.get("maximum", float("inf"))), 0.0
        orderwert_fw = orderwert_eur * eur_kurs
        gebuehr_fw = min(max(g["minimum"], g["je_stueck"] * stueck), g["max_anteil"] * orderwert_fw)
        if waehrung == "USD":
            tausch_fw = max(self.fx_minimum_usd, self.fx_satz * orderwert_fw)
        else:
            raise KeyError(f"Währungstausch für {waehrung} ist noch nicht modelliert")
        return gebuehr_fw / eur_kurs, tausch_fw / eur_kurs
