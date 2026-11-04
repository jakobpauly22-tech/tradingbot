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

    def gebuehren_eur(self, waehrung: str, stueck: float, orderwert_eur: float, eur_kurs: float) -> float:
        """Ordergebühr in EUR.

        EUR-Börsen: max(Minimum, Satz · Orderwert), höchstens Maximum. Das Minimum von 1,25 € gilt nur im IBKR-Modell
        „Gestaffelt“ (Tiered); das echte Konto ist seit 04.11.2026 darauf umgestellt (Festpreis: 3 € Minimum bei SMART).
        USD-Börsen: max(Minimum, je Stück · Stückzahl), höchstens max_anteil · Orderwert, umgerechnet mit `eur_kurs`
        (USD je 1 EUR). Der Währungstausch ist seit 02.11.2026 keine Orderkost mehr (siehe `tauschkosten_eur`).
        """
        if self.ohne_gebuehren:
            return 0.0
        if waehrung not in self.gebuehren:
            raise KeyError(f"Gebührenmodell für {waehrung} fehlt in config/backtest.yaml")
        g = self.gebuehren[waehrung]
        if waehrung == "EUR":
            return min(max(g["minimum"], g["satz"] * orderwert_eur), g.get("maximum", float("inf")))
        orderwert_fw = orderwert_eur * eur_kurs
        return min(max(g["minimum"], g["je_stueck"] * stueck), g["max_anteil"] * orderwert_fw) / eur_kurs

    def tauschkosten_eur(self, waehrung: str, betrag_fw: float, eur_kurs: float) -> float:
        """Kosten eines Währungstauschs in EUR: max(Minimum, Satz · Betrag) in USD (IBKR), umgerechnet mit `eur_kurs`.

        Entscheidung Jakob 02.11.2026: Die Fremdwährungskasse wird gehalten; getauscht wird nur bei Ein- und Auszahlungen
        bzw. für den Netto-Saldo am Ausführungstag, nicht je Order.
        """
        if self.ohne_gebuehren or betrag_fw <= 0:
            return 0.0
        if waehrung != "USD":
            raise KeyError(f"Währungstausch für {waehrung} ist noch nicht modelliert")
        return max(self.fx_minimum_usd, self.fx_satz * betrag_fw) / eur_kurs
