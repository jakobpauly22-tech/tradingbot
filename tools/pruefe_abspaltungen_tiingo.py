r"""Teil c1: Abspaltungen in Tiingo-Reihen suchen (Kriterien vor der Suche festgelegt, docs/FUNDAMENTAL.md, Abschnitte
„Teil c1“ und „Änderung der Kriterien nach der ersten Suche“, Jakob 13.11.2026). Nur lesend; korrigiert wird erst nach
Jakobs Prüfung der Liste.

Aufruf:  .venv\Scripts\python tools\pruefe_abspaltungen_tiingo.py
Ergebnis: docs/berichte/2026-11-13_abspaltungen_tiingo_3.md (erste Suche: …_tiingo.md, bleibt stehen; der zweite Lauf
brach wegen Speichermangel ab, ohne Bericht)

Grundmenge: Firmen mit Tiingo-Kursreihe, Mitgliedschaft 2012–2024 bis zum nächsten Rebalancing-Stichtag nach dem Abgang.
S1: Gesamtrendite (Schluss plus Dividende gegen Vortag) ≤ −3 % ohne Split-Eintrag, auch über zwei Tage zusammen.
S2 (zweite Änderung, 13.11.2026): irgendein 8-K im Fenster −30 … +5 Kalendertage, dessen Volltext „spin-off“, „spinoff“,
„spin off“, „separation and distribution“ oder „distribution of all“ enthält.
Speicher: 8-K werden einzeln geladen; der Text (nur Text-Dokumente, ohne Bilder, PDF, XBRL) wird komprimiert unter
daten/cache/sec/volltext_8k_text/ gespeichert, damit geänderte Suchwörter keinen neuen Abruf brauchen.
Treffer: S1 und S2. Unklar: Gesamtrendite ≤ −15 % ohne S2. Aufeinanderfolgende Kandidatentage (Abstand höchstens zwei
Handelstage) einer Firma bilden ein Ereignis.
"""
import gzip
import random
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
from tradingbot.kennzahlen.rendite import simple_return
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_abspaltungen_tiingo_3.md"   # erste Suche: …_tiingo.md
VOLLTEXT = PROJEKT_WURZEL / "daten" / "cache" / "sec" / "volltext_8k_text"
S1, UNKLAR, FENSTER = -0.03, -0.15, (30, 5)
WORTE = re.compile(r"spin[- ]?off|separation and distribution|distribution of all", re.I)
OHNE_TEXT = re.compile(r"^(GRAPHIC|ZIP|EXCEL|PDF|XML|JSON|EX-101|EX-104)", re.I)
PROBE_TREFFER = [("CSC", "2015-11-30")]
PROBE_KEIN_TREFFER = [("TGNA", "2017-06-01"), ("TWX", "2014-06-06"), ("TWX", "2014-06-09")]
PROBE_S2 = [(1336920, "LDOS", "2013-09-30"), (23082, "CSC/DXC", "2015-11-30"), (797468, "OXY", "2016-02-25"), (1585689, "HLT", "2017-01-04"),
            (1666700, "DD (Dow)", "2019-04-02"), (1666700, "DD (Corteva)", "2019-06-03"), (891103, "MTCH", "2020-07-01")]


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
            teile.append(pd.DataFrame({"cik": int(c), "datum": s.get("filingDate", []), "form": s.get("form", []),
                                       "accn": s.get("accessionNumber", [""] * n), "items": s.get("items", [""] * n)}))
    if not teile:
        return pd.DataFrame(columns=["cik", "datum", "form", "accn", "items"])
    t = pd.concat(teile, ignore_index=True)
    t["datum"] = pd.to_datetime(t["datum"])
    return t.fillna("").drop_duplicates("accn")


def text_aus_einreichung(roh: str) -> str:
    """Lesbarer Text einer vollständigen Einreichung (<accn>.txt): nur Text-Dokumente (8-K, Exhibits), ohne Bilder, PDF,
    Excel, XBRL; HTML-Tags und Entitäten entfernt, Leerraum zusammengefasst."""
    teile = []
    dokumente = (m.group(1) for m in re.finditer(r"<DOCUMENT>(.*?)</DOCUMENT>", roh, re.S | re.I))
    if "<DOCUMENT>" not in roh.upper()[:100000]:
        dokumente = iter([roh])
    for dok in dokumente:                                   # einzeln, ohne Liste aller Dokumente im Speicher
        typ = re.search(r"<TYPE>\s*([^\s<]+)", dok, re.I)
        if typ and OHNE_TEXT.match(typ.group(1)):
            continue
        dok = re.sub(r"<[^>]+>", " ", dok)
        dok = re.sub(r"&#\d+;|&nbsp;|&amp;|&[a-z]+;", " ", dok)
        teile.append(re.sub(r"\s+", " ", dok))
    return " ".join(teile)


def volltext(client, cik: int, accn: str) -> str | None:
    """Text eines 8-K aus dem Festplatten-Cache (gzip), sonst einzeln von der SEC laden und speichern. None bei Fehler."""
    datei = VOLLTEXT / f"{accn}.txt.gz"
    if datei.exists():
        with gzip.open(datei, "rt", encoding="utf-8") as f:
            return f.read()
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/{accn}.txt"
    client.drossel.warten()
    antwort = client.sitzung.get(url, headers={"User-Agent": client.user_agent}, timeout=120)
    if antwort.status_code != 200:
        return None
    text = text_aus_einreichung(antwort.text)
    del antwort
    VOLLTEXT.mkdir(parents=True, exist_ok=True)
    tmp = datei.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        f.write(text)
    tmp.replace(datei)
    return text


def volltext_treffer(client, cik: int, accn: str) -> dict:
    """Suchwörter im Text eines 8-K (aus dem Cache bzw. einzeln geladen); nur Wörter und ein Ausschnitt bleiben im Speicher."""
    text = volltext(client, cik, accn)
    if text is None:
        return {"fehler": "nicht abrufbar"}
    m = WORTE.search(text)
    return {"worte": sorted({w.lower() for w in WORTE.findall(text)}),
            "ausschnitt": text[max(0, m.start() - 200):m.end() + 200] if m else ""}


def beleg_s2(client, filings: pd.DataFrame, von: pd.Timestamp, bis: pd.Timestamp) -> tuple[str | None, str]:
    f = filings[(filings["datum"] >= von - pd.Timedelta(days=FENSTER[0])) & (filings["datum"] <= bis + pd.Timedelta(days=FENSTER[1]))
                & filings["form"].str.startswith("8-K")]
    belege, ausschnitt = [], ""
    for _, z in f.sort_values("datum").iterrows():
        v = volltext_treffer(client, z["cik"], z["accn"])
        if v.get("worte"):
            belege.append(f"{z['form']} {z['datum'].date()} ({z['accn']}): {', '.join(v['worte'])}")
            ausschnitt = ausschnitt or v.get("ausschnitt", "")
    return ("; ".join(belege[:3]) if belege else None), ausschnitt


def ereignisse(r: pd.Series, kand: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp, float]]:
    """Kandidatentage (Abstand höchstens zwei Handelstage) zu Ereignissen: (erster Tag, letzter Tag, schlechteste Rendite)."""
    pos = {d: i for i, d in enumerate(r.index)}
    aus, start, ende, schlecht = [], None, None, 0.0
    for d, w in kand.items():
        if start is not None and pos[d] - pos[ende] <= 2:
            ende, schlecht = d, min(schlecht, w)
            continue
        if start is not None:
            aus.append((start, ende, schlecht))
        start, ende, schlecht = d, d, w
    if start is not None:
        aus.append((start, ende, schlecht))
    return aus


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
        r = simple_return(k["close"].shift(1), k["close"], k["dividende"])
        ohne_split = k["split"].fillna(0) == 0
        zwei = (1 + r) * (1 + r.shift(1)) - 1
        s1 = ((r <= S1) | ((zwei <= S1) & ohne_split.shift(1, fill_value=True))) & ohne_split & (r.index >= von) & (r.index <= bis)
        kand = zwei.where(zwei < r, r)[s1]
        if kand.empty:
            continue
        filings = einreichungen(client, ciks_der_zeile(z))
        for start, ende, schlecht in ereignisse(r, kand):
            beleg, ausschnitt = beleg_s2(client, filings, start, ende)
            zeile = {"ticker": z["ticker"], "cik": int(z["cik"]), "name": z["name"], "von": start.date(), "bis": ende.date(),
                     "rendite": schlecht, "beleg": beleg, "ausschnitt": ausschnitt}
            if beleg:
                treffer.append(zeile)
            elif schlecht <= UNKLAR:
                unklar.append(zeile)
        print(f"{z['ticker']}: {len(treffer)} Treffer bisher", flush=True)

    def enthalten(liste, ticker, tag):
        t = pd.Timestamp(tag).date()
        return any(x["ticker"] == ticker and x["von"] <= t <= x["bis"] for x in liste)

    probe = [f"{a} {b}: {'gefunden' if enthalten(treffer, a, b) else 'NICHT gefunden'} (muss Treffer sein)" for a, b in PROBE_TREFFER]
    probe += [f"{a} {b}: {'TREFFER (darf nicht)' if enthalten(treffer, a, b) else 'kein Treffer'} (darf kein Treffer sein)"
              for a, b in PROBE_KEIN_TREFFER]
    probe_s2 = []
    for cik, name, tag in PROBE_S2:
        zeilen = universum[universum["cik"] == cik]
        ciks = ciks_der_zeile(zeilen.iloc[-1]) if len(zeilen) else [cik]
        ciks = sorted(set(ciks) | {cik})
        beleg, _ = beleg_s2(client, einreichungen(client, ciks), pd.Timestamp(tag), pd.Timestamp(tag))
        probe_s2.append(f"{name} {tag} (CIK {', '.join(map(str, ciks))}): " + (f"gefunden – {beleg}" if beleg else "NICHT gefunden"))
    stichprobe = random.Random(13112026).sample(treffer, min(10, len(treffer)))

    t, u = pd.DataFrame(treffer), pd.DataFrame(unklar)
    text = ["# Teil c1: Abspaltungen in Tiingo-Reihen – dritter Lauf", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_abspaltungen_tiingo.py`. Kriterien zweimal nach einer Suche geändert "
            "und jeweils vorher festgehalten (docs/FUNDAMENTAL.md): S1 Gesamtrendite ≤ −3 % (auch über zwei Tage), S2 Volltext aller 8-K "
            "im Fenster −30 … +5 Tage mit „spin-off“, „spinoff“, „spin off“, „separation and distribution“ oder „distribution of all“. "
            "Nichts wurde korrigiert.", "",
            f"Grundmenge: {grundmenge} Mitgliedschaften mit Tiingo-Reihe. Treffer: {len(t)} Ereignisse. Unklar (≤ −15 % ohne S2): {len(u)}.", "",
            "## Probe", ""] + [f"- {p}" for p in probe] + ["", "## S2 an den Abspaltungen aus Teil a", ""] + [f"- {p}" for p in probe_s2]
    text += ["", "## Stichprobe (10 Treffer, Startwert 13112026) mit Ausschnitt aus dem 8-K", ""]
    for x in stichprobe:
        text.append(f"- **{x['ticker']} {x['von']}** ({x['rendite']:+.1%}): {x['beleg']} — „…{x['ausschnitt'][:400]}…“")
    text += ["", "## Treffer", "", "| Ticker (CIK) | Name | Tage | Gesamtrendite (schlechteste) | SEC-Beleg (S2) |", "| --- | --- | --- | --- | --- |"]
    for x in t.itertuples():
        text.append(f"| {x.ticker} ({x.cik}) | {x.name} | {x.von}" + (f" bis {x.bis}" if x.bis != x.von else "") + f" | {x.rendite:+.1%} | {x.beleg} |")
    text += ["", "## Unklar (≤ −15 % ohne SEC-Beleg)", "", "| Ticker (CIK) | Name | Tage | Gesamtrendite |", "| --- | --- | --- | --- |"]
    for x in u.itertuples():
        text.append(f"| {x.ticker} ({x.cik}) | {x.name} | {x.von}" + (f" bis {x.bis}" if x.bis != x.von else "") + f" | {x.rendite:+.1%} |")
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
