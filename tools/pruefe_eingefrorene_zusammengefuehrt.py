r"""Eingefrorene Kurse in zusammengeführten Kursreihen suchen (Kriterien vor der Suche festgelegt, docs/FUNDAMENTAL.md,
„Fünfte Datenkorrektur … Eingefrorene Kurse in zusammengeführten Reihen“, Jakob 15.11.2026). Nur lesend, ohne Netz.

Aufruf:  .venv\Scripts\python tools\pruefe_eingefrorene_zusammengefuehrt.py
Ergebnis: docs/berichte/2026-11-15_eingefrorene_zusammengefuehrt.md

Grundmenge: Firmen (CIK), deren Kursreihe aus mehr als einer gültigen Teilreihe zusammengeführt wird (Mitgliedschaften
2012–2024), jede Teilreihe einzeln, ohne die Kappungen aus `kursreihe_ende` (gekappte Abschnitte als „bereits erfasst“).
E1 wie in der vierten Datenkorrektur (tools/pruefe_eingefrorene_kurse.py, `eingefroren`): mindestens 3 aufeinanderfolgende
Handelstage mit Eröffnung = Hoch = Tief = Schluss und Schluss gleich dem Vortagesschluss.
"""
import importlib.util
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

from tradingbot.backtest.tresor import begrenze
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.sp500_nachbau import ENDE, VORLAUF, firmen_schluessel, kursreihen_ende, kursreihen_ende_je_ticker
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-15_eingefrorene_zusammengefuehrt.md"
_spec = importlib.util.spec_from_file_location("pruefe_eingefrorene_kurse", Path(__file__).with_name("pruefe_eingefrorene_kurse.py"))
_vierte = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vierte)
eingefroren = _vierte.eingefroren


class OhneNetz:
    def get(self, *a, **k):
        raise RuntimeError("Tiingo-Abruf in diesem Werkzeug verboten (nur Cache)")


def uebernommen(teilreihen: list[tuple[str, pd.DataFrame]], index: int, tage: pd.DatetimeIndex) -> int:
    """Anzahl der Tage, an denen die zusammengeführte Reihe (combine_first in Ladereihenfolge) den Wert der Teilreihe
    `index` übernimmt: Die Teilreihe hat den Tag, und keine früher geladene Teilreihe hat ihn."""
    frueher = set()
    for _, k in teilreihen[:index]:
        frueher |= set(k.index)
    return sum(1 for t in tage if t in teilreihen[index][1].index and t not in frueher)


def main() -> int:
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    relevant = universum[(universum["bis"].isna() | (universum["bis"] > VORLAUF)) & (universum["von"].isna() | (universum["von"] <= ENDE))]
    cache, tiingo = standard_cache(), TiingoClient(sitzung=OhneNetz())
    kappung, kappung_ticker = kursreihen_ende(), kursreihen_ende_je_ticker()
    zeilen: dict = {}
    for nr, z in relevant.iterrows():
        s = status.loc[nr] if nr in status.index else None
        if s is None or not bool(s["gueltig"]):
            continue
        zeilen.setdefault(firmen_schluessel(z, nr), []).append((z, s))
    mehrfach = {f: l for f, l in zeilen.items() if len(l) > 1}
    funde, fehler = [], []
    for firma, liste in mehrfach.items():
        teilreihen = []
        for z, s in liste:
            try:
                k = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
                k = begrenze(k).sort_index().loc[VORLAUF:ENDE]
            except Exception as f:  # noqa: BLE001
                fehler.append(f"{z['ticker']} ({firma}): {type(f).__name__}")
                k = pd.DataFrame(columns=["open", "high", "low", "close"])
            teilreihen.append((z, s, k))
        for i, (z, s, k) in enumerate(teilreihen):
            if k.empty:
                continue
            ende_kappung = kappung.get(firma) if firma in kappung else kappung_ticker.get((firma, str(z["ticker"]).upper()))
            von = pd.Timestamp(z["von"]) if pd.notna(z["von"]) else VORLAUF
            bis = pd.Timestamp(z["bis"]) if pd.notna(z["bis"]) else ENDE
            for lauf in eingefroren(k, VORLAUF, ENDE):
                tage = k.loc[lauf["erster_tag"]:lauf["letzter_tag"]].index
                funde.append({"firma": firma, "ticker": z["ticker"], "quelle": s["quelle"], "symbol": s["symbol"], **lauf,
                              "mitgliedschaft": f"{von.date()} – {bis.date() if pd.notna(z['bis']) else 'offen'}",
                              "in_mitgliedschaft": bool(lauf["erster_tag"] <= bis and lauf["letzter_tag"] >= von),
                              "uebernommen": uebernommen([(x[0], x[2]) for x in teilreihen], i, tage),
                              "bereits_erfasst": bool(ende_kappung is not None and lauf["erster_tag"] > ende_kappung)})

    text = ["# Eingefrorene Kurse in zusammengeführten Kursreihen", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_eingefrorene_zusammengefuehrt.py`. Kriterien vor der Suche festgehalten "
            "(docs/FUNDAMENTAL.md, „Fünfte Datenkorrektur“, Jakob 15.11.2026). Nichts wurde korrigiert.", "",
            f"Grundmenge: {len(mehrfach)} Firmen mit mehr als einer gültigen Teilreihe "
            f"({', '.join(f'{f} ' + '/'.join(z['ticker'] for z, _ in l) for f, l in mehrfach.items())}). Funde (E1): {len(funde)}.", "",
            "„Übernommen“ = Tage des Laufs, an denen die zusammengeführte Reihe den Wert dieser Teilreihe nimmt (keine früher "
            "geladene Teilreihe hat den Tag). Nur solche Tage wirken in Backtest und Index-Nachbau.", "",
            "| Firma | Teilreihe (Quelle) | Mitgliedschaft der Zeile | eingefroren | Tage | Kurs | erster echter Kurs danach | in der Mitgliedschaft | übernommen | bereits gekappt |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for f in funde:
        echt = f"{f['erster_echter_tag'].date()}: {f['erster_echter_kurs']:.2f}" if f["erster_echter_tag"] is not None else "Reihenende"
        text.append(f"| {f['firma']} | {f['ticker']} ({f['quelle']}, {f['symbol']}) | {f['mitgliedschaft']} | {f['erster_tag'].date()} – "
                    f"{f['letzter_tag'].date()} | {f['tage']} | {f['kurs']:.2f} | {echt} | {'ja' if f['in_mitgliedschaft'] else 'nein'} | "
                    f"{f['uebernommen']} | {'ja' if f['bereits_erfasst'] else 'nein'} |")
    if fehler:
        text += ["", f"## Teilreihen nicht lesbar ({len(fehler)})", ""] + [f"- {x}" for x in fehler]
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
