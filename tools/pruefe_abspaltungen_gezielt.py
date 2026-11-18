r"""Teil c1 b): gezielte Prüfung der Fälle, die wirken können (Jakob 15.11.2026, docs/FUNDAMENTAL.md, „Teil c1:
Methodenwechsel nach dem dritten Lauf“). Nur lesend; korrigiert wird erst nach Jakobs Prüfung der Liste.

Aufruf:  .venv\Scripts\python tools\pruefe_abspaltungen_gezielt.py
Ergebnis: docs/berichte/2026-11-15_abspaltungen_gezielt.md

Fälle (aus dem Bericht der Obergrenze, docs/berichte/2026-11-15_abspaltungen_obergrenze.md):
- Backtest A: Ereignisse des dritten Laufs mit Kandidatentagen im Bestand (Gesamtrendite ≤ −3 %, auch Zwei-Tage-Fenster).
- Index-Nachbau: Ereignisse ≤ −15 % während der Mitgliedschaft.
Beleg: Hauptdokument jedes 8-K im Fenster −30 … +5 Kalendertage (Dokumenttyp 8-K, ohne Anhänge) und Pressemitteilungen
(EX-99.x) mit den Suchwörtern des dritten Laufs, je Fundstelle ein Ausschnitt. Ein 8-K, dessen Volltext (Cache des dritten
Laufs) kein Suchwort enthält, wird nicht erneut geladen: Dann enthalten auch Hauptdokument und Pressemitteilung keins.
Zur Einordnung: Gesamtrendite des Titels und des S&P 500 TR über dasselbe Fenster (Marktbewegung oder Einzelereignis).
Netz: nur SEC (Drossel und Wiederholung im SecClient); Tiingo nur aus dem Cache.
"""
import gzip
import json
import re
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.obergrenze_scheinverluste import gesamtrendite, lies_ereignisse
from tradingbot.daten.abruf import DatenFehler, VoruebergehenderFehler
from tradingbot.daten.kurse import lade_kurse
from tradingbot.daten.sec import SecClient
from tradingbot.daten.sp500_nachbau import ENDE, VORLAUF, ciks_der_zeile, lade_firmendaten
from tradingbot.daten.tiingo import TiingoClient
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.daten.kursstatus import lade_kursstatus
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
LAUF3 = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_abspaltungen_tiingo_3.md"
OBERGRENZE = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-15_abspaltungen_obergrenze.md"
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-15_abspaltungen_gezielt.md"
VOLLTEXT = PROJEKT_WURZEL / "daten" / "cache" / "sec" / "volltext_8k_text"
DOKUMENTE = PROJEKT_WURZEL / "daten" / "cache" / "sec" / "volltext_8k_dokumente"
WORTE = re.compile(r"spin[- ]?off|separation and distribution|distribution of all", re.I)   # wie dritter Lauf
FENSTER = (30, 5)
ABRUFFEHLER: list[str] = []


class OhneNetz:
    def get(self, *a, **k):
        raise RuntimeError("Tiingo-Abruf in diesem Werkzeug verboten (nur Cache)")


def _bereinigt(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&#\d+;|&nbsp;|&amp;|&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def haupt_und_pressemitteilungen(roh: str) -> list[dict]:
    """Dokumente einer vollständigen Einreichung: nur Hauptdokument (Typ 8-K, 8-K/A) und Pressemitteilungen (EX-99.x)."""
    aus = []
    for m in re.finditer(r"<DOCUMENT>(.*?)</DOCUMENT>", roh, re.S | re.I):
        dok = m.group(1)
        typ = re.search(r"<TYPE>\s*([^\s<]+)", dok, re.I)
        typ = typ.group(1).upper() if typ else ""
        if typ.startswith("8-K") or typ.startswith("EX-99"):
            aus.append({"typ": typ, "text": _bereinigt(dok.split(">", 1)[-1] if typ else dok)})
    return aus


def fundstellen(dokumente: list[dict], max_je_dokument: int = 3, breite: int = 300) -> list[dict]:
    aus = []
    for d in dokumente:
        for i, m in enumerate(WORTE.finditer(d["text"])):
            if i >= max_je_dokument:
                break
            aus.append({"typ": d["typ"], "wort": m.group(0), "ausschnitt": d["text"][max(0, m.start() - breite):m.end() + breite]})
    return aus


def volltext_hat_suchwort(accn: str) -> bool | None:
    datei = VOLLTEXT / f"{accn}.txt.gz"
    if not datei.exists():
        return None
    with gzip.open(datei, "rt", encoding="utf-8") as f:
        return bool(WORTE.search(f.read()))


def dokumente(client, cik: int, accn: str) -> list[dict] | None:
    datei = DOKUMENTE / f"{accn}.json.gz"
    if datei.exists():
        with gzip.open(datei, "rt", encoding="utf-8") as f:
            return json.load(f)
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/{accn}.txt"
    try:
        roh = client.text_holen(url)
    except VoruebergehenderFehler:
        raise                                   # Netz auch nach allen Versuchen weg: anhalten, Cache macht den Neustart billig
    except DatenFehler as f:
        ABRUFFEHLER.append(f"8-K {accn}: {str(f)[:150]}")
        return None
    doks = haupt_und_pressemitteilungen(roh)
    DOKUMENTE.mkdir(parents=True, exist_ok=True)
    tmp = datei.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(doks, f)
    tmp.replace(datei)
    return doks


def einreichungen(client, ciks) -> pd.DataFrame:
    teile = []
    for c in ciks:
        try:
            subs, _ = client.submissions(int(c))
        except Exception as f:  # noqa: BLE001
            ABRUFFEHLER.append(f"Einreichungsliste CIK {int(c)}: {type(f).__name__} {str(f)[:150]}")
            continue
        seiten = [subs.get("filings", {}).get("recent", {})]
        for datei in subs.get("filings", {}).get("files", []) or []:
            try:
                seiten.append(client.submissions_seite(datei["name"])[0])
            except Exception as f:  # noqa: BLE001
                ABRUFFEHLER.append(f"Einreichungsliste {datei['name']}: {type(f).__name__} {str(f)[:150]}")
        for s in seiten:
            n = len(s.get("form", []))
            teile.append(pd.DataFrame({"cik": int(c), "datum": s.get("filingDate", []), "form": s.get("form", []),
                                       "accn": s.get("accessionNumber", [""] * n), "items": s.get("items", [""] * n)}))
    if not teile:
        return pd.DataFrame(columns=["cik", "datum", "form", "accn", "items"])
    t = pd.concat(teile, ignore_index=True)
    t["datum"] = pd.to_datetime(t["datum"])
    return t.fillna("").drop_duplicates("accn")


def faelle_aus_obergrenze(obergrenze: str, ereignisse: pd.DataFrame) -> pd.DataFrame:
    """Fälle (cik, ticker, von, bis) mit Kennzeichen A und/oder Index aus den Tabellen des Obergrenzen-Berichts."""
    zeilen, abschnitt = [], None
    for z in obergrenze.splitlines():
        if z.startswith("## "):
            abschnitt = "A" if z.startswith("## Backtest A") else "Index" if z.startswith("## Index-Nachbau") else None
            continue
        if abschnitt == "A" and (m := re.match(r"^\| (\S+) \| (\d{4}-\d{2}-\d{2}) \|", z)):
            ticker, tag = m.group(1), pd.Timestamp(m.group(2))
            e = ereignisse[(ereignisse["ticker"] == ticker) & (ereignisse["von"] - pd.Timedelta(days=5) <= tag) & (ereignisse["bis"] >= tag)]
            if len(e):
                x = e.iloc[0]
                zeilen.append({"cik": x["cik"], "ticker": ticker, "von": x["von"], "bis": x["bis"], "liste": x["liste"], "A": True, "Index": False})
        if abschnitt == "Index" and (m := re.match(r"^\| (\S+) \((\d+)\) \| (\d{4}-\d{2}-\d{2})(?: bis (\d{4}-\d{2}-\d{2}))? \| [^|]+ \| (\w+) \|", z)):
            von = pd.Timestamp(m.group(3))
            zeilen.append({"cik": int(m.group(2)), "ticker": m.group(1), "von": von, "bis": pd.Timestamp(m.group(4)) if m.group(4) else von,
                           "liste": m.group(5), "A": False, "Index": True})
    f = pd.DataFrame(zeilen)
    return (f.groupby(["cik", "ticker", "von", "bis", "liste"], as_index=False)[["A", "Index"]].max()
            .sort_values(["von", "ticker"]).reset_index(drop=True))


def fensterrendite(r: pd.Series, von, bis) -> float:
    teil = r.loc[pd.Timestamp(von):pd.Timestamp(bis)].dropna()
    return float((1 + teil).prod() - 1) if len(teil) else float("nan")


def main() -> int:
    ereignisse = lies_ereignisse(LAUF3.read_text(encoding="utf-8"))
    faelle = faelle_aus_obergrenze(OBERGRENZE.read_text(encoding="utf-8"), ereignisse)
    universum, _ = lade_universum()
    status = lade_kursstatus(universum)                 # über den Schlüssel (Befund 19, Schritt 2)
    daten = lade_firmendaten(universum, status, lade_sic_historien(universum), tiingo=TiingoClient(sitzung=OhneNetz()))
    referenz = lade_kurse("^SP500TR", VORLAUF, ENDE)["close"].pct_change()
    client = SecClient()
    filings_je_cik, ergebnisse = {}, []
    for nr, fall in faelle.iterrows():
        zeilen = universum[universum["cik"] == fall["cik"]]
        ciks = sorted(set(ciks_der_zeile(zeilen.iloc[-1])) | {int(fall["cik"])}) if len(zeilen) else [int(fall["cik"])]
        schluessel = tuple(ciks)
        if schluessel not in filings_je_cik:
            filings_je_cik[schluessel] = einreichungen(client, ciks)
        f = filings_je_cik[schluessel]
        f = f[(f["datum"] >= fall["von"] - pd.Timedelta(days=FENSTER[0])) & (f["datum"] <= fall["bis"] + pd.Timedelta(days=FENSTER[1]))
              & f["form"].str.startswith("8-K")].sort_values("datum")
        belege, ohne_wort, geladen = [], 0, 0
        for _, z in f.iterrows():
            if volltext_hat_suchwort(z["accn"]) is False:
                ohne_wort += 1
                continue
            doks = dokumente(client, z["cik"], z["accn"])
            geladen += 1
            for s in fundstellen(doks or []):
                belege.append({"form": z["form"], "datum": z["datum"].date(), "accn": z["accn"], "items": z["items"], **s})
        k = daten.kurse.get(int(fall["cik"]))
        r_titel = fensterrendite(gesamtrendite(k), fall["von"], fall["bis"]) if k is not None else float("nan")
        r_markt = fensterrendite(referenz, fall["von"], fall["bis"])
        ergebnisse.append({**fall.to_dict(), "achtk": len(f), "ohne_wort": ohne_wort, "geladen": geladen, "belege": belege,
                           "r_titel": r_titel, "r_markt": r_markt})
        print(f"{nr + 1}/{len(faelle)} {fall['ticker']} {fall['von'].date()}: {len(f)} 8-K, {len(belege)} Fundstellen", flush=True)

    mit = [e for e in ergebnisse if e["belege"]]
    text = ["# Teil c1 b): gezielte Prüfung der wirksamen Fälle", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_abspaltungen_gezielt.py`. Methode vor der Rechnung festgehalten "
            "(docs/FUNDAMENTAL.md, „Teil c1: Methodenwechsel nach dem dritten Lauf“, Jakob 15.11.2026). Nichts wurde korrigiert.", "",
            f"Fälle: {len(faelle)} Ereignisse ({int(faelle['A'].sum())} mit Bestand in Backtest A, {int(faelle['Index'].sum())} im Index-Nachbau ≤ −15 %). "
            f"Mit Suchwort im Hauptdokument eines 8-K oder in einer Pressemitteilung (EX-99): {len(mit)}; ohne: {len(ergebnisse) - len(mit)}.", "",
            "## Übersicht", "",
            "| Ticker (CIK) | Ereignis | Liste | A | Index | Titel im Fenster | S&P 500 TR im Fenster | 8-K im Fenster | Suchwort in Hauptdokument/Pressemitteilung |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for e in ergebnisse:
        zeit = f"{e['von'].date()}" + (f" bis {e['bis'].date()}" if e["bis"] != e["von"] else "")
        text.append(f"| {e['ticker']} ({e['cik']}) | {zeit} | {e['liste']} | {'ja' if e['A'] else ''} | {'ja' if e['Index'] else ''} | "
                    f"{e['r_titel']:+.1%} | {e['r_markt']:+.1%} | {e['achtk']} | {len(e['belege']) or 'keins'} |")
    text += ["", "## Fundstellen im Hauptdokument oder in Pressemitteilungen", ""]
    for e in mit:
        text.append(f"### {e['ticker']} ({e['cik']}) {e['von'].date()}" + (f" bis {e['bis'].date()}" if e["bis"] != e["von"] else ""))
        text.append("")
        for b in e["belege"]:
            text.append(f"- {b['form']} {b['datum']} ({b['accn']}, Items {b['items'] or '–'}), {b['typ']}, „{b['wort']}“: „…{b['ausschnitt']}…“")
        text.append("")
    text += [f"## Abruffehler ({len(ABRUFFEHLER)})", ""] + [f"- {x}" for x in ABRUFFEHLER]
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text[:8]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
