"""Einstufung von Delistings für die Rückfall-Regel (Entscheidung Jakob 02.11.2026, config/fundamental.yaml).

Endet die Kursreihe einer gehaltenen Aktie, gilt:
- Übernahme oder Fusion → Position zum letzten Kurs schließen.
- Pleite, Performance (Börsenabstieg) oder unbekannt → letzter Kurs minus 30 % (Shumway 1997, „The Delisting Bias
  in CRSP Data“: durchschnittliche Delisting-Rendite bei performancebedingtem Delisting rund −30 %).

Belege aus den SEC-Einreichungen der Firma im Jahr vor dem Kursende (bis 60 Tage danach):
- Pleite: 8-K mit Item 1.03 (Bankruptcy or Receivership).
- Übernahme: 8-K mit Item 5.01 (Changes in Control) oder 2.01 (Completion of Acquisition), Übernahmeangebot
  (SC TO-T, SC 14D9) oder Fusions-Vollmachtsunterlagen (DEFM14A, PREM14A).
- Ersatzweise der Abgangsgrund aus der Wikipedia-Änderungstabelle („acquired“, „merger“ …).
Gibt es Belege für beides, gewinnt die Pleite (vorsichtig).
"""
from __future__ import annotations

import re

import pandas as pd

UEBERNAHME_FORMULARE = {"SC TO-T", "SC 14D9", "DEFM14A", "PREM14A", "SC TO-T/A", "SC 14D9/A"}
UEBERNAHME_TEXT = re.compile(r"acquir|merg|purchas|bought|takeover|buyout|taken private|combin", re.I)


def einreichungen(submissions: dict, seiten: list[dict] | None = None) -> pd.DataFrame:
    """Alle Einreichungen (datum, form, items) aus Submissions und Zusatzseiten."""
    teile = [submissions.get("filings", {}).get("recent", {})] + list(seiten or [])
    zeilen = [(d, f, i or "") for s in teile for d, f, i in zip(s.get("filingDate", []), s.get("form", []), s.get("items", [""] * len(s.get("form", []))))]
    t = pd.DataFrame(zeilen, columns=["datum", "form", "items"])
    t["datum"] = pd.to_datetime(t["datum"])
    return t


def delisting_grund(filings: pd.DataFrame, letzter_kurs, grund_text: str | None = None) -> tuple[str, str]:
    """Gibt (uebernahme | pleite | unbekannt, Beleg) für ein Kursende zurück."""
    ende = pd.Timestamp(letzter_kurs)
    fenster = filings[(filings["datum"] >= ende - pd.Timedelta(days=365)) & (filings["datum"] <= ende + pd.Timedelta(days=60))]
    acht_k = fenster[fenster["form"].str.startswith("8-K")]
    pleite = acht_k[acht_k["items"].str.contains(r"\b1\.03\b")]
    if len(pleite):
        return "pleite", f"8-K Item 1.03 vom {pleite['datum'].iloc[0].date()}"
    kontrolle = acht_k[acht_k["items"].str.contains(r"\b(5\.01|2\.01)\b")]
    if len(kontrolle):
        return "uebernahme", f"8-K Item {re.search(r'5\.01|2\.01', kontrolle['items'].iloc[-1]).group()} vom {kontrolle['datum'].iloc[-1].date()}"
    angebot = fenster[fenster["form"].isin(UEBERNAHME_FORMULARE)]
    if len(angebot):
        return "uebernahme", f"{angebot['form'].iloc[-1]} vom {angebot['datum'].iloc[-1].date()}"
    if isinstance(grund_text, str) and UEBERNAHME_TEXT.search(grund_text):
        return "uebernahme", f"Wikipedia: {grund_text[:80]}"
    return "unbekannt", "kein Beleg in SEC-Einreichungen oder Abgangsgrund"


def delisting_rendite(grund: str, konfig: dict | None = None) -> float:
    """Rendite beim Schließen nach Delisting: 0 bei Übernahme, −30 % sonst (config/fundamental.yaml)."""
    if konfig is None:
        from tradingbot.konfiguration import lade_konfiguration

        konfig = lade_konfiguration("fundamental")
    regel = konfig["universum"]["delisting"]["uebernahme_fusion" if grund == "uebernahme" else "pleite_performance_unbekannt"]
    return {"letzter_kurs": 0.0, "letzter_kurs_minus_30_prozent": -0.30}[regel]


def delisting_grund_mit_korrektur(ticker: str, filings: pd.DataFrame, letzter_kurs, grund_text: str | None = None,
                                  korrekturen: list[dict] | None = None) -> tuple[str, str]:
    """Wie `delisting_grund`, aber manuelle Einträge (config/universum_korrekturen.yaml, `delisting`) haben Vorrang."""
    for k in korrekturen or []:
        if k["ticker"] == ticker:
            return k["grund"], f"korrigiert: {k['quelle']}"
    return delisting_grund(filings, letzter_kurs, grund_text)
