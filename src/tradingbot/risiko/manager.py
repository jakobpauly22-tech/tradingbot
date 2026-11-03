"""Risk-Manager mit Vetorecht (Phase 2, Entscheidungen Jakob 31.10., 01.11. und 02.11.2026).

Jeder Order-Vorschlag gehört zu einem Buch (config/betrieb.yaml `buecher`: Realbuch und Skalierungsbücher). Er wird vor
der Freigabe und noch einmal vor dem Senden gegen den Stand SEINES Buchs geprüft. Ergebnis: frei oder Veto mit Gründen,
dazu Hinweise (kein Veto). Regeln (CLAUDE.md „Feste Regeln“, config/risiko.yaml, config/betrieb.yaml):

1. Not-Aus: Existiert die Datei STOP im Projektordner, wird nichts freigegeben (auch keine Verkäufe).
2. Buch: nur bekannte Bücher; Rolle (core oder satellite) und Grenzen kommen aus dem Buch.
3. Nur long, ohne Hebel: Verkauf höchstens bis zum Bestand des Buchs; Kauf nur aus der Kasse des Buchs (inkl. Gebühr).
4. Gebührenregel: Käufe und Aufstockungen nur, wenn die Gebühr ≤ 1 % des Orderwerts ist; Ausstiege immer erlaubt.
5. Positionsgrenzen nach dem Kauf, bezogen auf den Wert des Buchs: Core höchstens 5 % je Einzelaktie (breite ETFs
   ausgenommen); Satellite höchstens 25 % je ETF und 10 % je Einzelaktie; Satellite-Käufe brauchen einen Stop und
   riskieren höchstens 1 % des Buchwerts: Stück · (Kurs − Stop) ≤ 0,01 · Buchwert.
6. Fundamental-Veto für Einzelaktien: Piotroski ≤ 3, Z'' mit zweitem Signal, Altman Z (Industrie); Beneish nur Hinweis;
   ruht bei ETFs (config/risiko.yaml `fundamental_veto`).
7. Satellite-Limits je Buch (eigene Höchststände): Monat ≤ −10 % → Pause; −20 % vom Höchststand → Stopp; jeweils nur
   Käufe gesperrt. In den Skalierungsbüchern werden sie nur protokolliert („hätte gesperrt am …“), damit die Messung
   der Signalqualität nicht abbricht; im Realbuch sperren sie (Entscheidung 02.11.2026). Alle übrigen Regeln gelten in
   allen Büchern hart. Core-Notbremse (12 Monate > 10 Pp. hinter MSCI ACWI IMI) ist ein Review-Hinweis, kein Veto.
8. Plausibilität je Buch: Orderwert ≤ Budget des Buchs; Orders je Tag ≤ Höchstzahl des Buchs (Realbuch 5,
   Skalierungsbücher 25); Kauflimit vorhanden und höchstens 2 % über dem letzten Kurs; Verkäufe ohne Limit.
9. Doppel-Orders: Ein Vorschlag (ID) kann nur einmal gesendet werden; keine zweite Order, solange im selben Buch für
   denselben Ticker und dieselbe Richtung eine offene Order besteht (andere Bücher dürfen denselben Ticker handeln).
10. Kasse je Währung (Jakob 03.11.2026): Käufe werden in ihrer Handelswährung bezahlt (USD-Aktien, SXRM auf Xetra in USD).
   Keine Währung darf negativ werden, sonst Veto „Hebel“. USD entsteht über einen Tausch-Vorschlag (art „fx“: Verkauf von
   EUR gegen USD, Stück = EUR-Betrag), der vor den Käufen geprüft und gesendet wird.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import pandas as pd

ETF_ARTEN = ("etf", "etc")


@dataclass(frozen=True)
class OrderVorschlag:
    id: str                       # eindeutig je Vorschlag (Doppel-Order-Schutz)
    datum: pd.Timestamp           # Signaltag
    buch: str                     # Schlüssel in config/betrieb.yaml `buecher`
    ticker: str
    richtung: int                 # +1 Kauf, −1 Verkauf
    stueck: int
    letzter_kurs: float           # EUR
    art: str = "etf"              # etf | etc | aktie
    limit: float | None = None    # Kauflimit in EUR; Verkäufe ohne Limit
    stop: float | None = None     # Satellite: Stopkurs (für die 1-%-Risikoregel)
    gebuehrenplan: str = "EUR"    # Schlüssel in config/backtest.yaml `kosten.gebuehren` (USD für US-Aktien)
    eur_kurs: float = 1.0         # Einheiten der Handelswährung je 1 EUR (auch für den USD-Gebührenplan)
    waehrung: str = "EUR"         # Handelswährung: Kasse, aus der bezahlt bzw. in die gutgeschrieben wird
    these: str = ""               # Investment-These (Grund und was sie widerlegt)

    @property
    def orderwert(self) -> float:
        return self.stueck * (self.limit if (self.richtung > 0 and self.limit) else self.letzter_kurs)


@dataclass
class Kontext:
    """Stand EINES Buchs zum Zeitpunkt der Prüfung (Werte in EUR) plus kontoweite Angaben zu Orders."""
    buch: str
    kasse: float
    wert: float                                                      # Buchwert (Kasse plus Positionen)
    bestand: dict[str, int] = field(default_factory=dict)            # Stück je Ticker in diesem Buch
    monatsrendite: float = 0.0                                       # Satellite: Rendite im laufenden Monat
    vom_hoch: float = 0.0                                            # Satellite: Drawdown vom eigenen Höchststand (≤ 0)
    core_rueckstand_12m_pp: float = 0.0                              # Core: Buch minus ACWI IMI über 12 Monate in Pp.
    orders_heute: int = 0                                            # heute in diesem Buch freigegebene/gesendete Orders
    gesendete_ids: set[str] = field(default_factory=set)             # kontoweit
    offene_orders: list[tuple[str, str, int]] = field(default_factory=list)   # kontoweit: (Buch, Ticker, Richtung)
    fundamental: dict[str, list[str]] = field(default_factory=dict)  # Ticker → Ausschlussgründe aus filter.anwenden
    kasse_je_waehrung: dict[str, float] | None = None                # Kasse des Buchs je Währung (ohne Angabe: alles EUR)

    def waehrungskasse(self) -> dict[str, float]:
        return dict(self.kasse_je_waehrung) if self.kasse_je_waehrung is not None else {"EUR": self.kasse}


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

    def buch(self, name: str) -> dict | None:
        return (self.b.get("buecher") or {}).get(name)

    def _gebuehr(self, v: OrderVorschlag) -> float:
        if v.art == "fx":
            return self.kosten.tauschkosten_eur("USD", v.stueck * v.eur_kurs, v.eur_kurs)
        return self.kosten.gebuehren_eur(v.gebuehrenplan, v.stueck, v.orderwert, v.eur_kurs)

    def _fx_pruefen(self, v: OrderVorschlag, k: Kontext, b: dict, g: list) -> None:
        """Tausch EUR → Handelswährung: nur aus vorhandener EUR-Kasse, Plausibilität wie bei Orders."""
        gebuehr = self._gebuehr(v)
        eur = k.waehrungskasse().get("EUR", 0.0)
        if v.orderwert + gebuehr > eur + 1e-9:
            g.append(f"Hebel: EUR-Kasse {eur:.2f} € reicht nicht für den Tausch von {v.orderwert:.2f} € (keine Währung darf negativ werden)")
        if v.orderwert > float(b["budget_eur"]) + 1e-9:
            g.append(f"Tausch {v.orderwert:.2f} € über dem Budget des Buchs ({float(b['budget_eur']):.2f} €)")
        if k.orders_heute + 1 > int(b["max_orders_pro_tag"]):
            g.append(f"mehr als {int(b['max_orders_pro_tag'])} Orders an einem Tag im Buch {v.buch}")

    def pruefe(self, v: OrderVorschlag, k: Kontext) -> Urteil:
        g, h = [], []
        if self.not_aus():
            g.append("Not-Aus: Datei STOP im Projektordner")
        b = self.buch(v.buch)
        if b is None:
            return Urteil(False, g + [f"unbekanntes Buch {v.buch}"], h)
        if k.buch != v.buch:
            return Urteil(False, g + [f"Vorschlag für Buch {v.buch}, geprüft gegen Buch {k.buch}"], h)
        if v.art == "fx":
            if v.id in k.gesendete_ids:
                g.append(f"Vorschlag {v.id} wurde schon gesendet")
            self._fx_pruefen(v, k, b, g)
            return Urteil(not g, g, h)
        # 9. Doppel-Orders
        if v.id in k.gesendete_ids:
            g.append(f"Vorschlag {v.id} wurde schon gesendet")
        if (v.buch, v.ticker, v.richtung) in k.offene_orders:
            g.append(f"offene Order im Buch {v.buch} für {v.ticker} ({'Kauf' if v.richtung > 0 else 'Verkauf'}) besteht schon")
        # 3. nur long, kein Hebel
        if v.stueck <= 0 or v.richtung not in (1, -1):
            return Urteil(False, g + ["Stückzahl muss positiv und Richtung Kauf oder Verkauf sein"], h)
        bestand = k.bestand.get(v.ticker, 0)
        if v.richtung < 0 and v.stueck > bestand:
            g.append(f"Verkauf von {v.stueck} Stück, Bestand im Buch {bestand} (keine Leerverkäufe)")
        gebuehr = self._gebuehr(v)
        if v.richtung > 0 and v.orderwert + gebuehr > k.kasse + 1e-9:
            g.append(f"Kasse des Buchs {k.kasse:.2f} € reicht nicht für {v.orderwert + gebuehr:.2f} € (kein Hebel)")
        if v.richtung > 0:
            bedarf = (v.orderwert + gebuehr) * (v.eur_kurs if v.waehrung != "EUR" else 1.0)
            vorhanden = k.waehrungskasse().get(v.waehrung, 0.0)
            if bedarf > vorhanden + 1e-6:
                g.append(f"Hebel: {v.waehrung}-Kasse {vorhanden:.2f} reicht nicht für {bedarf:.2f} {v.waehrung} (keine Währung darf negativ werden)")
        # 4. Gebührenregel (nur Käufe)
        if v.richtung > 0 and gebuehr > 0.01 * v.orderwert + 1e-12:
            g.append(f"Gebühr {gebuehr:.2f} € > 1 % von {v.orderwert:.2f} €")
        # 8. Plausibilität je Buch
        if v.orderwert > float(b["budget_eur"]) + 1e-9:
            g.append(f"Orderwert {v.orderwert:.2f} € über dem Budget des Buchs ({float(b['budget_eur']):.2f} €)")
        if k.orders_heute + 1 > int(b["max_orders_pro_tag"]):
            g.append(f"mehr als {int(b['max_orders_pro_tag'])} Orders an einem Tag im Buch {v.buch}")
        abstand = float(self.b["sicherheit"]["plausibilitaet"]["max_limit_abstand"])
        if v.richtung > 0:
            if v.limit is None:
                g.append("Kauf ohne Limit")
            elif v.limit > v.letzter_kurs * (1 + abstand) + 1e-9:
                g.append(f"Limit {v.limit:.2f} mehr als {abstand * 100:.0f} % über dem letzten Kurs {v.letzter_kurs:.2f}")
            self._kaufregeln(v, k, b, g, h)
        elif v.limit is not None:
            g.append("Verkäufe ohne Limit (Entscheidung 02.11.2026)")
        if b["rolle"] == "core" and k.core_rueckstand_12m_pp < -10:
            h.append(f"Core-Notbremse im Buch {v.buch}: 12 Monate {k.core_rueckstand_12m_pp:.1f} Pp. hinter MSCI ACWI IMI – Review")
        return Urteil(not g, g, h)

    def _kaufregeln(self, v: OrderVorschlag, k: Kontext, b: dict, g: list, h: list):
        rolle = b["rolle"]
        # Satellite-Limits: im Realbuch Veto, in Skalierungsbüchern nur Protokoll (02.11.2026)
        limit_ziel = h if b.get("art") == "skalierung" else g
        vorsatz = f"hätte gesperrt am {pd.Timestamp(v.datum).date():%d.%m.%Y}: " if b.get("art") == "skalierung" else ""
        nachher = (k.bestand.get(v.ticker, 0) + v.stueck) * v.letzter_kurs
        sat = self.r["positionsgroesse"]["satellite"]
        if rolle == "core":
            grenze = float(self.r["positionsgroesse"]["core"]["max_einzelaktie"])
            if v.art not in ETF_ARTEN and k.wert > 0 and nachher > grenze * k.wert + 1e-9:
                g.append(f"Core: Einzelaktie {v.ticker} über {grenze * 100:.0f} % des Buchwerts")
        elif rolle == "satellite":
            grenze = float(sat["max_position"]["etf" if v.art in ETF_ARTEN else "aktie"])
            if k.wert > 0 and nachher > grenze * k.wert + 1e-9:
                g.append(f"Satellite: Position {v.ticker} über {grenze * 100:.0f} % des Buchwerts")
            if v.stop is None:
                g.append("Satellite-Kauf ohne Stop")
            elif v.stueck * (v.letzter_kurs - v.stop) > float(sat["risiko_je_trade"]) * k.wert + 1e-9:
                g.append(f"Risiko {v.stueck * (v.letzter_kurs - v.stop):.2f} € über 1 % des Buchwerts")
            if k.monatsrendite <= -0.10:
                limit_ziel.append(f"{vorsatz}Satellite-Buch {v.buch} pausiert: Monat {k.monatsrendite:.1%} (Grenze −10 %)")
            if k.vom_hoch <= -0.20:
                limit_ziel.append(f"{vorsatz}Satellite-Buch {v.buch} gestoppt: {k.vom_hoch:.1%} vom eigenen Höchststand (Grenze −20 %)")
        else:
            g.append(f"unbekannte Rolle {rolle}")
        # 6. Fundamental-Veto (nur Einzelaktien)
        if v.art not in ETF_ARTEN:
            gruende = k.fundamental.get(v.ticker)
            if gruende is None:
                h.append(f"keine Fundamentalprüfung für {v.ticker} vorhanden")
            for grund in gruende or []:
                if grund.startswith("Beneish"):
                    h.append(f"Warnhinweis Fundamental: {grund}")
                else:
                    g.append(f"Fundamental: {grund}")

    def verbuchen(self, v: OrderVorschlag, k: Kontext) -> None:
        """Wirkung eines freigegebenen Vorschlags auf die Kasse des Buchs (gesamt in EUR und je Währung)."""
        gebuehr = self._gebuehr(v)
        kassen = k.waehrungskasse()
        if v.art == "fx":
            kassen["EUR"] = kassen.get("EUR", 0.0) - v.orderwert - gebuehr
            kassen[v.waehrung] = kassen.get(v.waehrung, 0.0) + v.stueck * v.eur_kurs
            k.kasse -= gebuehr
        else:
            f = v.eur_kurs if v.waehrung != "EUR" else 1.0
            betrag = (v.orderwert - gebuehr) if v.richtung < 0 else -(v.orderwert + gebuehr)
            kassen[v.waehrung] = kassen.get(v.waehrung, 0.0) + betrag * f
            k.kasse += betrag
        k.kasse_je_waehrung = kassen

    def pruefe_alle(self, vorschlaege: list[OrderVorschlag], kontexte: dict[str, Kontext]) -> list[tuple[OrderVorschlag, Urteil]]:
        """Prüft je Buch nacheinander (Verkäufe zuerst); freigegebene Orders verbrauchen Kasse und zählen als Order des
        Tages ihres Buchs. Freigegebene Vorschläge gelten danach kontoweit als offen (Doppel-Order-Schutz)."""
        stand = {n: replace(k, kasse_je_waehrung=k.waehrungskasse()) for n, k in kontexte.items()}
        offen = [o for k in kontexte.values() for o in k.offene_orders]
        ergebnis = []
        reihenfolge = lambda x: (x.buch, 1 if x.art == "fx" else (0 if x.richtung < 0 else 2))   # noqa: E731 – Verkäufe, Tausch, Käufe
        for v in sorted(vorschlaege, key=reihenfolge):
            k = stand.get(v.buch)
            if k is None:
                ergebnis.append((v, Urteil(False, [f"kein Stand für Buch {v.buch}"])))
                continue
            k.offene_orders = list(offen)
            u = self.pruefe(v, k)
            if u.frei:
                k.orders_heute += 1
                self.verbuchen(v, k)
                offen.append((v.buch, v.ticker, v.richtung))
            ergebnis.append((v, u))
        return ergebnis
