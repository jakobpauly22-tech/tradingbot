r"""Teil c1, Schlussprüfung (Jakob 15.11.2026): Die drei Fälle der gezielten Prüfung ohne 8-K im Fenster werden am
Hauptdokument des nächsten 10-Q/10-K nach dem Ereignis geprüft, ob eine Abspaltung erwähnt ist. Nur lesend.

Aufruf:  .venv\Scripts\python tools\pruefe_abspaltungen_schluss.py
Ergebnis: Abschnitt wird an docs/berichte/2026-11-15_abspaltungen_gezielt.md angehängt (bzw. ersetzt).
Suchwörter wie im dritten Lauf; je Fundstelle ein Ausschnitt.
"""
import re
import sys
from datetime import datetime

import pandas as pd

from tradingbot.daten.sec import SecClient
from tradingbot.konfiguration import PROJEKT_WURZEL

BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-15_abspaltungen_gezielt.md"
WORTE = re.compile(r"spin[- ]?off|separation and distribution|distribution of all", re.I)
FAELLE = [("PBCT", 1378946, "2020-03-19", "2020-04-03"), ("DISH", 1001082, "2023-06-08", "2023-06-15"),
          ("CTLT", 1596783, "2023-10-31", "2023-11-02")]
UEBERSCHRIFT = "## Schlussprüfung am nächsten 10-Q/10-K (Fälle ohne 8-K im Fenster)"


def bereinigt(roh: str) -> str:
    text = re.sub(r"<[^>]+>", " ", roh)
    text = re.sub(r"&#\d+;|&nbsp;|&amp;|&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text)


def naechster_bericht(subs: dict, nach: pd.Timestamp) -> dict | None:
    """Erster 10-Q/10-K (ohne /A), eingereicht nach `nach`, aus der Einreichungsliste (nur „recent“)."""
    r = subs.get("filings", {}).get("recent", {})
    t = pd.DataFrame({k: r.get(k, []) for k in ("form", "filingDate", "accessionNumber", "primaryDocument", "reportDate")})
    t["filingDate"] = pd.to_datetime(t["filingDate"])
    t = t[t["form"].isin(["10-Q", "10-K"]) & (t["filingDate"] > nach)].sort_values("filingDate")
    return t.iloc[0].to_dict() if len(t) else None


def main() -> int:
    client = SecClient()
    zeilen = [UEBERSCHRIFT, "", f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/pruefe_abspaltungen_schluss.py`: Hauptdokument des ersten "
              "10-Q/10-K nach dem Ereignis, Suchwörter wie im dritten Lauf.", ""]
    for ticker, cik, von, bis in FAELLE:
        subs, _ = client.submissions(cik)
        b = naechster_bericht(subs, pd.Timestamp(bis))
        if b is None:
            zeilen.append(f"- **{ticker} {von} bis {bis}:** kein 10-Q/10-K nach dem Ereignis in der Einreichungsliste gefunden.")
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{b['accessionNumber'].replace('-', '')}/{b['primaryDocument']}"
        text = bereinigt(client.text_holen(url))
        funde = [text[max(0, m.start() - 250):m.end() + 250] for m in WORTE.finditer(text)]
        kopf = (f"- **{ticker} {von} bis {bis}:** {b['form']} für {b['reportDate']}, eingereicht {b['filingDate'].date()} "
                f"({b['accessionNumber']}, {b['primaryDocument']}, {len(text):,} Zeichen): ")
        if not funde:
            zeilen.append(kopf + "**keine Erwähnung** einer Abspaltung.")
        else:
            zeilen.append(kopf + f"{len(funde)} Fundstelle(n):")
            zeilen += [f"  - „…{f}…“" for f in funde[:5]]
    abschnitt = "\n".join(zeilen) + "\n"
    s = BERICHT.read_text(encoding="utf-8")
    if UEBERSCHRIFT in s:
        vorher, rest = s.split(UEBERSCHRIFT, 1)
        naechster = rest.find("\n## ")
        s = vorher + abschnitt + (rest[naechster + 1:] if naechster >= 0 else "")
    else:
        s = s.replace("## Übersicht", abschnitt + "\n## Übersicht", 1)
    BERICHT.write_text(s, encoding="utf-8")
    print(abschnitt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
