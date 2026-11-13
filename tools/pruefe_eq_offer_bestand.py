r"""Datenkorrektur Piotroski EQ_OFFER (Jakob 13.11.2026): Welche gehaltenen oder vorgeschlagenen Titel der Bücher
Fundamental A und B wären betroffen? Nur lesend (Journal read-only), im Betriebsmodus (Daten ab 2025).

Aufruf:  .venv\Scripts\python tools\pruefe_eq_offer_bestand.py
Ergebnis: docs/berichte/2026-11-13_piotroski_eq_offer_bestand.md

Je Titel: Splits laut Kursreihe (Spalte `split`, Yahoo) seit 2023 und quittierte Flex-Splits, EQ_OFFER bisher und
korrigiert mit Quelle (A/B) und Piotroski für den Filter zum letzten Quartalsstichtag und zur letzten NYSE-Sitzung.
Splits werden nur aus den Daten bestätigt, nicht aus dem Gedächtnis. Kurse werden nicht neu geladen (Cache).
"""
import sqlite3
import sys
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.betrieb.speicher import betriebspfad
from tradingbot.daten.cache import standard_cache
from tradingbot.engines.fundamental.aktuell import bewertung_am
from tradingbot.engines.fundamental.scores import piotroski  # noqa: F401 – Rechnung wie im Betrieb über bewertung_am
from tradingbot.konfiguration import PROJEKT_WURZEL

BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_piotroski_eq_offer_bestand.md"
BUECHER = ("fundamental_a", "fundamental_b")


def titel_aus_journal(datei) -> dict[str, set[str]]:
    """Bestand > 0, Orders unterwegs und offene Vorschläge je Titel (Journal nur lesend)."""
    db = sqlite3.connect(f"file:{datei}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    titel: dict[str, set[str]] = {}
    try:
        for buch in BUECHER:
            for z in db.execute("SELECT ticker, SUM(richtung * stueck) s FROM ausfuehrungen WHERE buch=? GROUP BY ticker", (buch,)):
                if (z["s"] or 0) > 0:
                    titel.setdefault(z["ticker"], set()).add(f"{buch}: Bestand")
            for z in db.execute("SELECT ticker, status FROM vorschlaege WHERE buch=? AND art='aktie' AND status IN "
                                "('vorgeschlagen','freigegeben','gesendet','unbestaetigt')", (buch,)):
                titel.setdefault(z["ticker"], set()).add(f"{buch}: {z['status']}")
    finally:
        db.close()
    return titel


def splits_seit(symbol: str, ab="2023-01-01") -> str:
    k, _ = standard_cache().lesen("kurse", symbol)
    if k is None or "split" not in k.columns:
        return "keine Kursreihe im Cache"
    s = k["split"].fillna(0)
    s = s[(s > 0) & (s.index >= pd.Timestamp(ab))]
    return ", ".join(f"{d:%d.%m.%Y} {v:g}:1" if v >= 1 else f"{d:%d.%m.%Y} 1:{1 / v:g}" for d, v in s.items()) or "keiner"


def main() -> int:
    with betriebsmodus("Prüfung Datenkorrektur Piotroski EQ_OFFER, gehaltene Titel (nur lesend)"):
        from tradingbot.betrieb import kapitalmassnahmen as km
        from tradingbot.betrieb.journal import Journal

        datei = betriebspfad("journal.sqlite")
        titel = titel_aus_journal(datei)
        flex = km.flex_splits_je_symbol(Journal(datei))
        stichtag = pd.Timestamp("2026-10-01")
        k, _ = standard_cache().lesen("kurse", "SPY")
        letzte = pd.Timestamp(k.index.max()) if k is not None else pd.Timestamp(datetime.now().date())
        tabellen = {}
        for tag in (stichtag, letzte):
            b, _, meldungen = bewertung_am(tag, aktualisieren=False, splits_flex=flex or None)
            tabellen[tag] = b.set_index("symbol")
        text = ["# Datenkorrektur EQ_OFFER: gehaltene und vorgeschlagene Titel (Fundamental A und B)", "",
                f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_eq_offer_bestand.py` (Betriebsmodus, Journal nur lesend, "
                "Kurse aus dem Cache). Splits nur aus der Kursreihe (Yahoo, Spalte `split`) und quittierten Flex-Belegen.", "",
                f"Quartalsstichtag {stichtag.date()} und letzte NYSE-Sitzung im Kurs-Cache {letzte.date()}. "
                "Die Korrektur wirkt im Betrieb erst ab 04.01.2027; bis dahin gilt die Spalte „bisher“.", "",
                "| Titel | Buch | Splits seit 2023 | Flex | EQ bisher / korrigiert (Quelle) am Stichtag | Piotroski bisher / korrigiert am Stichtag | "
                "EQ bisher / korrigiert (Quelle) zuletzt | betroffen |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        betroffen = []
        for t in sorted(titel):
            zellen = []
            aenderung = False
            for tag in (stichtag, letzte):
                b = tabellen[tag]
                if t not in b.index:
                    zellen.append(("nicht bewertet", "–"))
                    continue
                z = b.loc[t]
                aenderung |= z["eq_offer_alt"] != z["eq_offer_neu"]
                zellen.append((f"{z['eq_offer_alt']} / {z['eq_offer_neu']} ({z['eq_offer_quelle'] or '–'}, Faktor {z['eq_offer_split_faktor']:g})",
                               f"{z['piotroski_filter']} / {z['piotroski_filter_korrigiert']}"))
            if aenderung:
                betroffen.append(t)
            text.append(f"| {t} | {'; '.join(sorted(titel[t]))} | {splits_seit(t)} | {', '.join(f'{d} {r:g}' for d, r in flex.get(t, [])) or '–'} | "
                        f"{zellen[0][0]} | {zellen[0][1]} | {zellen[1][0]} | {'**ja**' if aenderung else 'nein'} |")
        text += ["", f"Betroffen (Signal bisher ≠ korrigiert an einem der beiden Tage): {', '.join(betroffen) or 'keiner'}."]
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
