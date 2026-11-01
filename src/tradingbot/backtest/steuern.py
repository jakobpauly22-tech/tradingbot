"""Deutsche Besteuerung privater Kapitalerträge für Backtest und Paper Trading.

Grundsatz: Das heutige Recht gilt für alle simulierten Jahre (Pauschbetrag 1.000 €, Teilfreistellung und
Vorabpauschale nach dem InvStG 2018). So wird eine Strategie so bewertet, wie sie künftig besteuert wird.
Quellen sind Gesetze, nicht wissen/ (dort gibt es noch keine Steuerdatei):

- Abgeltungsteuer 25 % (§ 32d Abs. 1 EStG), Solidaritätszuschlag 5,5 % darauf (§§ 3, 4 SolZG).
  Kirchensteuer: Jakob zahlt keine, daher nicht modelliert.
- Sparer-Pauschbetrag 1.000 € pro Person und Jahr (§ 20 Abs. 9 EStG); nicht genutzter Rest verfällt.
- Verlustverrechnung (§ 20 Abs. 6 EStG): Verluste aus Aktienverkäufen nur mit Gewinnen aus Aktienverkäufen
  (Aktientopf); übrige Verluste (z.B. ETF-Verkäufe) mit allen Kapitalerträgen (allgemeiner Topf).
  Nicht verrechnete Verluste werden unbegrenzt vorgetragen. Vorträge mindern den Ertrag vor dem Pauschbetrag.
- FIFO bei Verkäufen (§ 20 Abs. 4 S. 7 EStG), siehe portfolio.py. Gewinn = Erlös nach Verkaufskosten
  − Anschaffungskosten inklusive Nebenkosten (§ 20 Abs. 4 S. 1 EStG).
- Investmentfonds (ETFs): Teilfreistellung 30 % bei Aktienfonds, 15 % bei Mischfonds (§ 20 InvStG); gilt für
  Ausschüttungen, Vorabpauschalen und Veräußerungsergebnisse, auch für Verluste.
- Vorabpauschale (§ 18 InvStG): Basisertrag = Rücknahmepreis Jahresanfang · Basiszins · 0,7; höchstens der
  Mehrbetrag (Preis Jahresende − Preis Jahresanfang + Ausschüttungen); abzüglich Ausschüttungen, nicht negativ.
  Im Erwerbsjahr minus 1/12 je vollem Monat vor dem Erwerbsmonat. Zufluss am ersten Werktag des Folgejahres.
  Beim Verkauf mindern die angesetzten Vorabpauschalen den Gewinn (§ 19 Abs. 1 S. 3 InvStG).
- Ausländische Quellensteuer (USA 15 % mit W-8BEN) wird auf die Abgeltungsteuer angerechnet (§ 32d Abs. 5 EStG),
  höchstens 25 % des ausländischen Ertrags. Nicht anrechenbar, soweit die Erträge durch den Pauschbetrag
  steuerfrei sind (Jakob, 01.11.2026). Vorsichtig wird der Pauschbetrag zuerst den ausländischen Erträgen
  zugerechnet, damit möglichst wenig Quellensteuer angerechnet wird.

Vereinfachungen (bewusst, von Jakob am 01.11.2026 akzeptiert):
- Quellensteuer: Anrechnung je Jahr über alle ausländischen Erträge, nicht je einzelnem Ertrag.
- Die Vorabpauschale des letzten simulierten Jahres fließt erst nach Simulationsende zu und wird nicht erfasst.
- ETCs (z.B. Gold) sind steuerlich Sonderfälle (physisch besichert teils nach einem Jahr steuerfrei). Bis zur
  sauberen Modellierung vorsichtig wie sonstige Kapitalerträge: Abgeltungsteuer auf den vollen Gewinn, keine
  Teilfreistellung, keine Vorabpauschale, Verluste im allgemeinen Topf (Steuerart „etc“).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

STEUERARTEN = ("aktie", "aktienfonds", "mischfonds", "sonstiger_fonds", "etc")
FONDS = ("aktienfonds", "mischfonds", "sonstiger_fonds")   # nur Investmentfonds haben eine Vorabpauschale
ERTRAGSARTEN = ("veraeusserung", "dividende", "ausschuettung", "vorabpauschale")


@dataclass(frozen=True)
class Steuerregeln:
    abgeltungsteuer: float = 0.25
    soli: float = 0.055
    sparer_pauschbetrag: float = 1000.0
    teilfreistellung: dict = field(default_factory=lambda: {"aktienfonds": 0.30, "mischfonds": 0.15, "sonstiger_fonds": 0.0})
    quellensteuer: dict = field(default_factory=lambda: {"USD": 0.15})
    basiszins: dict = field(default_factory=dict)   # Jahr -> Dezimalzahl
    aktiv: bool = True

    @classmethod
    def aus_konfig(cls, konfig: dict | None = None) -> "Steuerregeln":
        if konfig is None:
            from tradingbot.konfiguration import lade_konfiguration

            konfig = lade_konfiguration("backtest")
        s = konfig["steuern"]
        if float(s.get("kirchensteuer", 0.0)) != 0.0:
            raise NotImplementedError("Kirchensteuer ist nicht modelliert (Jakob zahlt keine)")
        return cls(
            abgeltungsteuer=float(s["abgeltungsteuer"]),
            soli=float(s["soli"]),
            sparer_pauschbetrag=float(s["sparer_pauschbetrag"]),
            teilfreistellung={k: float(v) for k, v in s["teilfreistellung"].items()},
            quellensteuer={k: float(v) for k, v in s["quellensteuer"].items()},
            basiszins={int(j): float(v) / 100 for j, v in s["basiszins_prozent"].items()},
        )

    @classmethod
    def ohne_steuern(cls) -> "Steuerregeln":
        return cls(aktiv=False)

    def teilfreistellung_fuer(self, steuerart: str) -> float:
        if steuerart not in STEUERARTEN:
            raise ValueError(f"Unbekannte Steuerart {steuerart!r}, erlaubt: {STEUERARTEN}")
        return self.teilfreistellung.get(steuerart, 0.0) if steuerart in FONDS else 0.0

    def basiszins_fuer(self, jahr: int) -> float:
        if jahr not in self.basiszins:
            raise KeyError(f"Basiszins {jahr} fehlt in config/backtest.yaml (steuern.basiszins_prozent)")
        return self.basiszins[jahr]


@dataclass(frozen=True)
class Steuerereignis:
    datum: pd.Timestamp       # Zuflusszeitpunkt (bestimmt das Steuerjahr)
    teilportfolio: str
    ticker: str
    art: str                  # veraeusserung | dividende | ausschuettung | vorabpauschale
    steuerart: str            # aktie | aktienfonds | mischfonds | sonstiger_fonds
    betrag: float             # EUR vor Teilfreistellung; Verluste negativ
    quellensteuer: float = 0.0


def erster_werktag(jahr: int) -> pd.Timestamp:
    """Erster Werktag (Mo–Fr) nach Neujahr; Zufluss der Vorabpauschale."""
    return pd.Timestamp(np.busday_offset(date(jahr, 1, 2), 0, roll="forward"))


def vorabpauschale_je_anteil(preis_anfang: float, preis_ende: float, ausschuettung: float, basiszins: float,
                             erwerbsmonat: int | None = None) -> float:
    """Vorabpauschale je Fondsanteil (§ 18 InvStG).

    Basisertrag = P_Anfang · Basiszins · 0,7
    Mehrbetrag  = P_Ende − P_Anfang + Ausschüttungen
    VP          = max(0, min(Basisertrag, Mehrbetrag) − Ausschüttungen) · (13 − Erwerbsmonat)/12 im Erwerbsjahr
    """
    basisertrag = preis_anfang * basiszins * 0.7
    mehrbetrag = preis_ende - preis_anfang + ausschuettung
    vp = max(0.0, min(basisertrag, mehrbetrag) - ausschuettung)
    if erwerbsmonat is not None:
        vp *= (13 - erwerbsmonat) / 12
    return vp


def _jahre(ereignisse: list[Steuerereignis], jahre) -> list[int]:
    alle = {e.datum.year for e in ereignisse} | set(jahre or [])
    return list(range(min(alle), max(alle) + 1)) if alle else []


def berechne_jahressteuer(ereignisse: list[Steuerereignis], regeln: Steuerregeln, *, pauschbetrag: float | None = None,
                          jahre=None) -> pd.DataFrame:
    """Steuer je Kalenderjahr mit Verlusttöpfen und Verlustvorträgen.

    Rechenweg je Jahr:
    1. Aktientopf: Aktiengewinne − Aktienverluste − Vortrag Aktien; negativ → neuer Vortrag.
    2. Allgemein: übrige Erträge nach Teilfreistellung − Vortrag allgemein; ist das negativ, wird es mit dem
       Aktien-Saldo verrechnet, der Rest vorgetragen.
    3. Summe − Pauschbetrag (höchstens bis 0) = steuerpflichtig.
    4. Abgeltungsteuer 25 %, Quellensteuer anrechnen, Soli 5,5 % auf den Rest. Anrechenbar ist höchstens
       25 % des ausländischen Ertrags, der nach dem Pauschbetrag steuerpflichtig bleibt; der Pauschbetrag
       wird vorsichtig zuerst den ausländischen Erträgen zugerechnet.
    """
    pauschbetrag = regeln.sparer_pauschbetrag if pauschbetrag is None else pauschbetrag
    zeilen = []
    vortrag_aktie = vortrag_allg = 0.0
    for jahr in _jahre(ereignisse, jahre):
        im_jahr = [e for e in ereignisse if e.datum.year == jahr]
        aktie = [e.betrag for e in im_jahr if e.art == "veraeusserung" and e.steuerart == "aktie"]
        aktien_gewinne = sum(b for b in aktie if b > 0)
        aktien_verluste = -sum(b for b in aktie if b < 0)
        allgemein = sum(e.betrag * (1 - regeln.teilfreistellung_fuer(e.steuerart))
                        for e in im_jahr if not (e.art == "veraeusserung" and e.steuerart == "aktie"))
        quellensteuer = sum(e.quellensteuer for e in im_jahr)
        auslaendisch = sum(e.betrag for e in im_jahr if e.quellensteuer > 0)

        aktie_saldo = aktien_gewinne - aktien_verluste - vortrag_aktie
        vortrag_aktie = max(-aktie_saldo, 0.0)
        aktie_saldo = max(aktie_saldo, 0.0)
        allg_saldo = allgemein - vortrag_allg
        if allg_saldo < 0:
            verrechnet = min(-allg_saldo, aktie_saldo)
            aktie_saldo -= verrechnet
            allg_saldo += verrechnet
        vortrag_allg = max(-allg_saldo, 0.0)
        allg_saldo = max(allg_saldo, 0.0)

        summe = aktie_saldo + allg_saldo
        pausch = min(pauschbetrag, summe) if regeln.aktiv else 0.0
        steuerpflichtig = summe - pausch if regeln.aktiv else 0.0
        abgeltung = steuerpflichtig * regeln.abgeltungsteuer
        auslaendisch_steuerpflichtig = min(max(auslaendisch - pausch, 0.0), steuerpflichtig)
        angerechnet = min(quellensteuer, auslaendisch_steuerpflichtig * regeln.abgeltungsteuer, abgeltung)
        abgeltung -= angerechnet
        soli = abgeltung * regeln.soli
        zeilen.append({
            "jahr": jahr,
            "aktien_gewinne": aktien_gewinne,
            "aktien_verluste": aktien_verluste,
            "allgemein_nach_teilfreistellung": allgemein,
            "summe_nach_verrechnung": summe,
            "pauschbetrag_genutzt": pausch,
            "steuerpflichtig": steuerpflichtig,
            "abgeltungsteuer": abgeltung,
            "soli": soli,
            "quellensteuer_gezahlt": quellensteuer,
            "quellensteuer_angerechnet": angerechnet,
            "steuer": abgeltung + soli,
            "vortrag_aktien": vortrag_aktie,
            "vortrag_allgemein": vortrag_allg,
        })
    spalten = ["jahr", "aktien_gewinne", "aktien_verluste", "allgemein_nach_teilfreistellung", "summe_nach_verrechnung",
               "pauschbetrag_genutzt", "steuerpflichtig", "abgeltungsteuer", "soli", "quellensteuer_gezahlt",
               "quellensteuer_angerechnet", "steuer", "vortrag_aktien", "vortrag_allgemein"]
    return pd.DataFrame(zeilen, columns=spalten).set_index("jahr")


def steuerpflichtiger_beitrag(e: Steuerereignis, regeln: Steuerregeln) -> float:
    """Beitrag eines Ereignisses zur Bemessungsgrundlage (nach Teilfreistellung), für die Zuordnung auf Teilportfolios."""
    return e.betrag * (1 - regeln.teilfreistellung_fuer(e.steuerart))
