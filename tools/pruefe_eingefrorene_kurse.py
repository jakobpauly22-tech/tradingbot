r"""Suche nach eingefrorenen Kursen nach einem Handelsstopp bei Insolvenz (vierte Datenkorrektur, Anlass SIVB; Kriterien
vor der Suche festgelegt, docs/FUNDAMENTAL.md, Jakob 13.11.2026). Nur lesend; korrigiert wird erst nach Jakobs Prüfung.

Aufruf:  .venv\Scripts\python tools\pruefe_eingefrorene_kurse.py
Ergebnis: docs/berichte/2026-11-13_eingefrorene_kurse.md

Grundmenge: Firmen des Universums mit gültiger Kursreihe und einem 8-K mit Item 1.03. Fenster: 10. Handelstag vor bis
60 Kalendertage nach dem ersten 8-K mit Item 1.03. E1: mindestens 3 aufeinanderfolgende Handelstage mit unverändertem
Schlusskurs und Umsatz 0 (oder fehlend). Kurse wie im Backtest (bis zur Datumsgrenze des Tresors).
"""
import glob
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import begrenze
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.delisting import einreichungen
from tradingbot.daten.sec import SecClient
from tradingbot.daten.sp500_nachbau import ciks_der_zeile
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_eingefrorene_kurse.md"
MIN_TAGE, VOR_HANDELSTAGE, NACH_TAGEN = 3, 10, 60


def eingefroren(kurse: pd.DataFrame, von, bis) -> list[dict]:
    """Läufe von mindestens MIN_TAGE Handelstagen mit Schluss = Vortag und Umsatz 0/fehlend, die im Fenster beginnen."""
    k = kurse.sort_index()
    gleich = k["close"].diff() == 0
    ohne_umsatz = (k["volume"].fillna(0) == 0) if "volume" in k.columns else pd.Series(True, index=k.index)
    flag = gleich & ohne_umsatz
    laeufe, start = [], None
    for i, (tag, f) in enumerate(flag.items()):
        if f and start is None:
            start = i
        if (not f or i == len(flag) - 1) and start is not None:
            ende = i if f else i - 1
            if ende - start + 1 >= MIN_TAGE and pd.Timestamp(von) <= k.index[start] <= pd.Timestamp(bis):
                danach = k.iloc[ende + 1:]
                echt = danach[(danach["close"] != k["close"].iloc[ende])
                              & ((danach["volume"].fillna(0) > 0) if "volume" in danach.columns else True)]
                laeufe.append({"erster_tag": k.index[start], "letzter_tag": k.index[ende], "tage": ende - start + 1,
                               "kurs": float(k["close"].iloc[ende]),
                               "erster_echter_tag": echt.index[0] if len(echt) else None,
                               "erster_echter_kurs": float(echt["close"].iloc[0]) if len(echt) else None})
            start = None
    return laeufe


def main() -> int:
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    client, tiingo, cache = SecClient(), TiingoClient(), standard_cache()
    gehalten = set()
    for f in glob.glob(str(PROJEKT_WURZEL / "daten" / "backtests" / "2026111*fundamental*" / "trades_vor_steuern.csv")):
        gehalten |= set(pd.read_csv(f)["ticker"])
    zeilen, grundmenge = [], 0
    for cik, g in universum[universum["cik"].notna()].groupby("cik"):
        letzte = g.sort_values("bis", na_position="last").iloc[-1]
        if pd.notna(letzte["bis"]) and pd.Timestamp(letzte["bis"]) < pd.Timestamp("2012-01-01"):
            continue
        pleite = []
        for c in ciks_der_zeile(letzte):
            try:
                e = einreichungen(client.submissions(int(c))[0])
            except Exception:  # noqa: BLE001 – ohne Einreichungen kein Kandidat
                continue
            pleite += list(e[e["form"].str.startswith("8-K") & e["items"].str.contains(r"\b1\.03\b")]["datum"])
        nr = letzte.name
        if not pleite or nr not in status.index or not bool(status.loc[nr, "gueltig"]):
            continue
        s = status.loc[nr]
        try:
            k = cache.lesen("kurse", s["symbol"])[0] if s["quelle"] == "yfinance" else tiingo.historie(s["symbol"])
            k = begrenze(k)
        except Exception:  # noqa: BLE001
            k = None
        if k is None or k.empty:
            continue
        grundmenge += 1
        acht_k = min(pleite)
        pos = max(0, int(k.index.searchsorted(acht_k)) - VOR_HANDELSTAGE)
        von, bis = k.index[min(pos, len(k) - 1)], acht_k + pd.Timedelta(days=NACH_TAGEN)
        for lauf in eingefroren(k, von, bis):
            tag = lauf["erster_tag"]
            mitglied = bool(((g["von"].isna() | (g["von"] <= tag)) & (g["bis"].isna() | (g["bis"] > tag))).any())
            zeilen.append({"ticker": letzte["ticker"], "cik": int(cik), "name": letzte["name"],
                           "mitglied": f"{g['von'].min().date() if pd.notna(g['von'].min()) else '–'} bis "
                                       f"{letzte['bis'].date() if pd.notna(letzte['bis']) else 'heute'}",
                           "acht_k": acht_k.date(), "symbol": f"{s['symbol']} ({s['quelle']})", **lauf,
                           "mitglied_am_stopp": mitglied, "gehalten": f"CIK{int(cik)}" in gehalten})
    df = pd.DataFrame(zeilen)
    text = ["# Eingefrorene Kurse nach Handelsstopp bei Insolvenz", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_eingefrorene_kurse.py`. Kriterien vor der Suche festgelegt "
            "(docs/FUNDAMENTAL.md, Abschnitt „Vierte Datenkorrektur“): Grundmenge Firmen mit 8-K Item 1.03 und gültiger Kursreihe; "
            f"Fenster {VOR_HANDELSTAGE} Handelstage vor bis {NACH_TAGEN} Tage nach dem ersten 8-K; mindestens {MIN_TAGE} Handelstage "
            "unveränderter Schluss ohne Umsatz. Kurse bis zur Datumsgrenze des Tresors.", "",
            f"Grundmenge: {grundmenge} Firmen. Treffer: {len(df)}. Nichts wurde korrigiert.", "",
            "| Ticker (CIK) | Name | Mitgliedschaft | 8-K 1.03 | Kursreihe | eingefroren | Kurs | erster echter Kurs danach | "
            "Mitglied am 1. Tag | in Backtest A gehalten |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for z in df.itertuples():
        echt = f"{z.erster_echter_kurs:g} USD am {z.erster_echter_tag.date()}" if z.erster_echter_tag is not None else "keiner (Reihenende)"
        text.append(f"| {z.ticker} ({z.cik}) | {z.name} | {z.mitglied} | {z.acht_k} | {z.symbol} | {z.erster_tag.date()} bis "
                    f"{z.letzter_tag.date()} ({z.tage} Tage) | {z.kurs:g} | {echt} | {'ja' if z.mitglied_am_stopp else 'nein'} | "
                    f"{'ja' if z.gehalten else 'nein'} |")
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
