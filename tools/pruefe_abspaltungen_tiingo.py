r"""Teil c1: Abspaltungen in Tiingo-Reihen suchen (Kriterien vor der Suche festgelegt, docs/FUNDAMENTAL.md, Abschnitt
„Teil c1“, Jakob 13.11.2026). Nur lesend; korrigiert wird erst nach Jakobs Prüfung der Liste.

Aufruf:  .venv\Scripts\python tools\pruefe_abspaltungen_tiingo.py
Ergebnis: docs/berichte/2026-11-13_abspaltungen_tiingo.md

Grundmenge: Firmen mit Tiingo-Kursreihe, Mitgliedschaft 2012–2024 bis zum nächsten Rebalancing-Stichtag nach dem Abgang.
S1: Schluss/Vortag − 1 ≤ −3 % ohne Split-Eintrag. S2: 8-K mit Item 2.01 oder Dokumentbeschreibung mit „spin“, „separation“,
„distribution“ im Fenster −30 … +5 Kalendertage. Treffer: S1 und S2. Unklar: Rückgang ≥ 15 % ohne S2.
"""
import re
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import begrenze
from tradingbot.daten.abdeckung import rebalancing_stichtage
from tradingbot.daten.sec import SecClient
from tradingbot.daten.sp500_nachbau import ciks_der_zeile
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_universum
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_abspaltungen_tiingo.md"
S1, UNKLAR, FENSTER = -0.03, -0.15, (30, 5)
WORTE = re.compile(r"spin|separation|distribution", re.I)
PROBE = {("CSC", "2015-11-30"), ("TGNA", "2017-06-01"), ("TWX", "2014-06-09")}


def einreichungen(client, ciks) -> pd.DataFrame:
    teile = []
    for c in ciks:
        try:
            subs, _ = client.submissions(int(c))
        except Exception:  # noqa: BLE001
            continue
        seiten = [subs.get("filings", {}).get("recent", {})]
        for f in subs.get("filings", {}).get("files", []) or []:
            try:
                seiten.append(client.submissions_seite(f["name"])[0])
            except Exception:  # noqa: BLE001
                pass
        for s in seiten:
            n = len(s.get("form", []))
            teile.append(pd.DataFrame({"datum": s.get("filingDate", []), "form": s.get("form", []),
                                       "items": s.get("items", [""] * n), "beschreibung": s.get("primaryDocDescription", [""] * n)}))
    if not teile:
        return pd.DataFrame(columns=["datum", "form", "items", "beschreibung"])
    t = pd.concat(teile, ignore_index=True)
    t["datum"] = pd.to_datetime(t["datum"])
    return t.fillna("")


def beleg_s2(filings: pd.DataFrame, tag: pd.Timestamp) -> str | None:
    f = filings[(filings["datum"] >= tag - pd.Timedelta(days=FENSTER[0])) & (filings["datum"] <= tag + pd.Timedelta(days=FENSTER[1]))]
    zeilen = []
    for _, z in f.iterrows():
        if z["form"].startswith("8-K") and re.search(r"\b2\.01\b", str(z["items"])):
            zeilen.append(f"{z['form']} {z['datum'].date()} Item 2.01")
        elif WORTE.search(str(z["beschreibung"])):
            zeilen.append(f"{z['form']} {z['datum'].date()} „{str(z['beschreibung'])[:60]}“")
    return "; ".join(zeilen[:3]) if zeilen else None


def main() -> int:
    universum, _ = lade_universum()
    status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
    stichtage = pd.DatetimeIndex(rebalancing_stichtage())
    client, tiingo = SecClient(), TiingoClient()
    treffer, unklar, grundmenge = [], [], 0
    for nr, z in universum.iterrows():
        if nr not in status.index or not bool(status.loc[nr, "gueltig"]) or status.loc[nr, "quelle"] != "tiingo" or pd.isna(z["cik"]):
            continue
        von = max(pd.Timestamp(z["von"]) if pd.notna(z["von"]) else pd.Timestamp("2012-01-01"), pd.Timestamp("2012-01-01"))
        bis = pd.Timestamp(z["bis"]) if pd.notna(z["bis"]) else pd.Timestamp("2024-12-31")
        naechster = stichtage[stichtage > bis]
        bis = min(naechster[0] if len(naechster) else bis, pd.Timestamp("2024-12-31"))
        if bis < von:
            continue
        try:
            k = begrenze(tiingo.historie(status.loc[nr, "symbol"])).sort_index()
        except Exception:  # noqa: BLE001
            continue
        grundmenge += 1
        r = k["close"].pct_change()
        split = k["split"].fillna(0)
        tage = r[(r.index >= von) & (r.index <= bis) & (r <= S1) & (split == 0)]
        if tage.empty:
            continue
        filings = einreichungen(client, ciks_der_zeile(z))
        for tag, aenderung in tage.items():
            beleg = beleg_s2(filings, tag)
            zeile = {"ticker": z["ticker"], "cik": int(z["cik"]), "name": z["name"], "tag": tag.date(), "aenderung": aenderung,
                     "beleg": beleg, "probe": (z["ticker"], str(tag.date())) in PROBE}
            if beleg:
                treffer.append(zeile)
            elif aenderung <= UNKLAR:
                unklar.append(zeile)
    t, u = pd.DataFrame(treffer), pd.DataFrame(unklar)
    gefunden = {(x.ticker, str(x.tag)) for x in t.itertuples()} if len(t) else set()
    fehlende_probe = sorted(PROBE - gefunden)
    text = ["# Teil c1: Abspaltungen in Tiingo-Reihen", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_abspaltungen_tiingo.py`. Kriterien vor der Suche festgelegt "
            "(docs/FUNDAMENTAL.md, Abschnitt „Teil c1“). Nichts wurde korrigiert.", "",
            f"Grundmenge: {grundmenge} Mitgliedschaften mit Tiingo-Reihe. Treffer (S1 und S2): {len(t)}. Unklar (≥ 15 % ohne S2): {len(u)}.", "",
            "Probe: " + ("alle drei gefunden (CSC, TGNA, TWX)." if not fehlende_probe else
                         "NICHT gefunden: " + ", ".join(f"{a} {b}" for a, b in fehlende_probe) + " – Kriterien nicht geändert, an Jakob."), "",
            "## Treffer", "", "| Ticker (CIK) | Name | Tag | Änderung | SEC-Beleg (S2) | Probe |", "| --- | --- | --- | --- | --- | --- |"]
    for x in t.itertuples():
        text.append(f"| {x.ticker} ({x.cik}) | {x.name} | {x.tag} | {x.aenderung:+.1%} | {x.beleg} | {'ja' if x.probe else ''} |")
    text += ["", "## Unklar (Rückgang ≥ 15 % ohne SEC-Beleg)", "", "| Ticker (CIK) | Name | Tag | Änderung |", "| --- | --- | --- | --- |"]
    for x in u.itertuples():
        text.append(f"| {x.ticker} ({x.cik}) | {x.name} | {x.tag} | {x.aenderung:+.1%} |")
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
