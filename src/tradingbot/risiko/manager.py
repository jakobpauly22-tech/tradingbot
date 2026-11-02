"""Risk-Manager mit Vetorecht (Phase 2, Entscheidungen Jakob 31.10., 01.11. und 02.11.2026).

Jeder Order-Vorschlag wird vor der Freigabe und noch einmal vor dem Senden geprüft. Ergebnis: frei oder Veto mit
Gründen, dazu Hinweise (kein Veto). Regeln (CLAUDE.md „Feste Regeln“, config/risiko.yaml, config/betrieb.yaml):

1. Not-Aus: Existiert die Datei STOP im Projektordner, wird nichts freigegeben (auch keine Verkäufe).
2. Nur long, ohne Hebel: Verkauf höchstens bis zum Bestand; Kauf nur aus vorhandener Kasse (inkl. Gebühr).
3. Gebührenregel: Käufe und Aufstockungen nur, wenn die Gebühr ≤ 1 % des Orderwerts ist; Ausstiege immer erlaubt.
4. Positionsgrenzen nach dem Kauf: Core höchstens 5 % je Einzelaktie (breite ETFs ausgenommen); Satellite höchstens
   25 % je ETF und 10 % je Einzelaktie; Satellite-Käufe brauchen einen Stop und riskieren höchstens 1 % des
   Satellite-Werts: Stück · (Kurs − Stop) ≤ 0,01 · Satellite-Wert.
5. Fundamental-Veto für Einzelaktien: Piotroski ≤ 3, Z'' mit zweitem Signal, Altman Z (Industrie); Beneish und Z''
   allein nur Hinweis; ruht bei ETFs (config/risiko.yaml `fundamental_veto`).
6. Satellite-Limits: Monat ≤ −10 % → Pause (keine Käufe); −20 % vom Höchststand → Stopp (keine Käufe); Ausstiege
   bleiben erlaubt. Core-Notbremse (12 Monate > 10 Pp. hinter MSCI ACWI IMI) ist ein Review-Hinweis, kein Veto.
7. Plausibilität: Orderwert ≤ Bot-Budget; Orders je Tag ≤ Höchstzahl; Kauflimit vorhanden und höchstens 2 % über dem
   letzten Kurs; Verkäufe ohne Limit.
8. Doppel-Orders: Ein Vorschlag (ID) kann nur einmal gesendet werden; keine zweite Order, solange für denselben Ticker
   und dieselbe Richtung eine offene Order besteht.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ETF_ARTEN = ("etf", "etc")


@dataclass(frozen=True)
class OrderVorschlag:
    id: str                       # eindeutig je Vorschlag (Doppel-Order-Schutz)
    datum: pd.Timestamp           # Signaltag
    teil: str                     # core | satellite
    ticker: str
    richtung: int                 # +1 Kauf, −1 Verkauf
    stueck: int
    letzter_kurs: float           # EUR
    art: str = "etf"              # etf | etc | aktie
    limit: float | None = None    # Kauflimit in EUR; Verkäufe ohne Limit
    stop: float | None = None     # Satellite: Stopkurs (für die 1-%-Risikoregel)
    these: str = ""               # Investment-These (Grund und was sie widerlegt)

    @property
    def orderwert(self) -> float:
        return self.stueck * (self.limit if (self.richtung > 0 and self.limit) else self.letzter_kurs)


@dataclass
class Kontext:
    """Stand des Bot-Depots zum Zeitpunkt der Prüfung (Werte in EUR)."""
    kasse: float
    bestand: dict[str, int] = field(default_factory=dict)            # Stück je Ticker
    kurse: dict[str, float] = field(default_factory=dict)            # letzter Kurs je Ticker
    teil_wert: dict[str, float] = field(default_factory=dict)        # Wert je Teil (core, satellite)
    teil_je_ticker: dict[str, str] = field(default_factory=dict)     # gehaltene Ticker → Teil
    satellite_monat: float = 0.0                                     # Rendite im laufenden Monat
    satellite_vom_hoch: float = 0.0                                  # Drawdown vom Höchststand (≤ 0)
    core_rueckstand_12m_pp: float = 0.0                              # Core minus ACWI IMI über 12 Monate in Pp.
    orders_heute: int = 0                                            # heute schon freigegebene/gesendete Orders
    gesendete_ids: set[str] = field(default_factory=set)
    offene_orders: list[tuple[str, int]] = field(default_factory=list)   # (Ticker, Richtung)
    fundamental: dict[str, list[str]] = field(default_factory=dict)  # Ticker → Ausschlussgründe aus filter.anwenden


@dataclass
class Urteil:
    frei: bool
    gruende: list[str] = field(default_factory=list)     # Veto-Gründe
    hinweise: list[str] = field(default_factory=list)


class RiskManager:
    def __init__(self, risiko: dict, betrieb: dict, kosten, projekt_wurzel: Path):
        self.r, self.b, self.kosten, self.wurzel = risiko, betrieb, kosten, Path(projekt_wurzel)

    @classmethod
    def aus_konfig(cls) -> "RiskManager":
        from tradingbot.backtest.kosten import Kostenmodell
        from tradingbot.konfiguration import PROJEKT_WURZEL, lade_konfiguration

        return cls(lade_konfiguration("risiko"), lade_konfiguration("betrieb"), Kostenmodell.aus_konfig(), PROJEKT_WURZEL)

    def not_aus(self) -> bool:
        return (self.wurzel / self.b["sicherheit"]["not_aus_datei"]).exists()

    def pruefe(self, v: OrderVorschlag, k: Kontext) -> Urteil:
        g, h = [], []
        if self.not_aus():
            g.append("Not-Aus: Datei STOP im Projektordner")
        # 8. Doppel-Orders
        if v.id in k.gesendete_ids:
            g.append(f"Vorschlag {v.id} wurde schon gesendet")
        if (v.ticker, v.richtung) in k.offene_orders:
            g.append(f"offene Order für {v.ticker} ({'Kauf' if v.richtung > 0 else 'Verkauf'}) besteht schon")
        # 2. nur long, kein Hebel
        if v.stueck <= 0 or v.richtung not in (1, -1):
            g.append("Stückzahl muss positiv und Richtung Kauf oder Verkauf sein")
            return Urteil(False, g, h)
        bestand = k.bestand.get(v.ticker, 0)
        if v.richtung < 0 and v.stueck > bestand:
            g.append(f"Verkauf von {v.stueck} Stück, Bestand {bestand} (keine Leerverkäufe)")
        gebuehr = self.kosten.gebuehren_eur("EUR", v.stueck, v.orderwert, 1.0)
        if v.richtung > 0 and v.orderwert + gebuehr > k.kasse + 1e-9:
            g.append(f"Kasse {k.kasse:.2f} € reicht nicht für {v.orderwert + gebuehr:.2f} € (kein Hebel)")
        # 3. Gebührenregel (nur Käufe)
        if v.richtung > 0 and gebuehr > 0.01 * v.orderwert + 1e-12:
            g.append(f"Gebühr {gebuehr:.2f} € > 1 % von {v.orderwert:.2f} €")
        # 7. Plausibilität
        p = self.b["sicherheit"]["plausibilitaet"]
        if v.orderwert > float(p["max_orderwert_eur"]) + 1e-9:
            g.append(f"Orderwert {v.orderwert:.2f} € über dem Höchstwert {float(p['max_orderwert_eur']):.2f} €")
        if k.orders_heute + 1 > int(p["max_orders_pro_tag"]):
            g.append(f"mehr als {int(p['max_orders_pro_tag'])} Orders an einem Tag")
        if v.richtung > 0:
            if v.limit is None:
                g.append("Kauf ohne Limit")
            elif v.limit > v.letzter_kurs * (1 + float(p["max_limit_abstand"])) + 1e-9:
                g.append(f"Limit {v.limit:.2f} mehr als {float(p["max_limit_abstand"]) * 100:.0f} % über dem letzten Kurs {v.letzter_kurs:.2f}")
        elif v.limit is not None:
            g.append("Verkäufe ohne Limit (Entscheidung 02.11.2026)")
        if v.richtung > 0:
            self._kaufregeln(v, k, g, h)
        if v.teil == "core" and k.core_rueckstand_12m_pp < -10:
            h.append(f"Core-Notbremse: 12 Monate {k.core_rueckstand_12m_pp:.1f} Pp. hinter MSCI ACWI IMI – Review")
        return Urteil(not g, g, h)

    def _kaufregeln(self, v: OrderVorschlag, k: Kontext, g: list, h: list):
        teil_wert = k.teil_wert.get(v.teil, 0.0)
        nachher = (k.bestand.get(v.ticker, 0) + v.stueck) * v.letzter_kurs
        sat = self.r["positionsgroesse"]["satellite"]
        if v.teil == "core":
            if v.art not in ETF_ARTEN and teil_wert > 0 and nachher > float(self.r["positionsgroesse"]["core"]["max_einzelaktie"]) * teil_wert + 1e-9:
                g.append(f"Core: Einzelaktie {v.ticker} über 5 % des Core-Werts")
        elif v.teil == "satellite":
            grenze = float(sat["max_position"]["etf" if v.art in ETF_ARTEN else "aktie"])
            if teil_wert > 0 and nachher > grenze * teil_wert + 1e-9:
                g.append(f"Satellite: Position {v.ticker} über {grenze * 100:.0f} % des Satellite-Werts")
            if v.stop is None:
                g.append("Satellite-Kauf ohne Stop")
            elif v.stueck * (v.letzter_kurs - v.stop) > float(sat["risiko_je_trade"]) * teil_wert + 1e-9:
                g.append(f"Risiko {v.stueck * (v.letzter_kurs - v.stop):.2f} € über 1 % des Satellite-Werts")
            if k.satellite_monat <= -0.10:
                g.append(f"Satellite pausiert: Monat {k.satellite_monat:.1%} (Grenze −10 %)")
            if k.satellite_vom_hoch <= -0.20:
                g.append(f"Satellite gestoppt: {k.satellite_vom_hoch:.1%} vom Höchststand (Grenze −20 %)")
        else:
            g.append(f"unbekannter Teil {v.teil}")
        # 5. Fundamental-Veto (nur Einzelaktien)
        if v.art not in ETF_ARTEN:
            gruende = k.fundamental.get(v.ticker)
            if gruende is None:
                h.append(f"keine Fundamentalprüfung für {v.ticker} vorhanden")
            for grund in gruende or []:
                (h if grund.startswith("Beneish") else g).append(f"Fundamental: {grund}" if not grund.startswith("Beneish") else f"Warnhinweis Fundamental: {grund}")

    def pruefe_alle(self, vorschlaege: list[OrderVorschlag], k: Kontext) -> list[tuple[OrderVorschlag, Urteil]]:
        """Prüft nacheinander; freigegebene Käufe verbrauchen Kasse und zählen als Order des Tages (Verkäufe zuerst)."""
        ergebnis = []
        kasse, heute = k.kasse, k.orders_heute
        for v in sorted(vorschlaege, key=lambda x: x.richtung):
            kk = Kontext(**{**k.__dict__, "kasse": kasse, "orders_heute": heute})
            u = self.pruefe(v, kk)
            if u.frei:
                heute += 1
                gebuehr = self.kosten.gebuehren_eur("EUR", v.stueck, v.orderwert, 1.0)
                kasse += (v.orderwert - gebuehr) if v.richtung < 0 else -(v.orderwert + gebuehr)
            ergebnis.append((v, u))
        return ergebnis
