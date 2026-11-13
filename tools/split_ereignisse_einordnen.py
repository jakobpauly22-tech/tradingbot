r"""Einordnung der „Split“-Ereignisse der Kursreihen: echter Split, Abspaltung, kombiniert oder unklar (Teil a der
Datenkorrektur Marktwert, Jakob 13.11.2026, docs/FUNDAMENTAL.md).

Aufruf:  .venv\Scripts\python tools\split_ereignisse_einordnen.py
Ergebnis: config/kapitalmassnahmen_historie.yaml (je Ereignis Art, Split-Faktor, Quelle; Einträge mit `geprueft: true`
bleiben bei einem neuen Lauf unverändert) und docs/berichte/2026-11-13_split_ereignisse.md (Prüfliste der unklaren Fälle).

Methode: Yahoo (und Tiingo) führen in der Spalte `split` echte Splits, aber auch Abspaltungen (Kursbereinigung). Den
echten Split-Faktor zeigt die SEC: Dieselbe Periode (gewichtete Aktienzahl eines Geschäftsjahrs) steht vor dem Ereignis
in der alten und danach in der ersten Einreichung neu auf der neuen Basis (ASC 260, rückwirkend). Verhältnis r = neu/alt.
- r ≈ Faktor der Kursreihe → Split (auch Aktiendividende); r ≈ 1 → Abspaltung (Split-Faktor 1);
- r weder noch → kombiniert (z. B. Reverse-Split und Abspaltung am selben Tag), Vorschlag Split-Faktor = r, zu prüfen;
- kein r (keine Einreichung davor/danach, Skalierungsfehler, Faktor nahe 1) → unklar, zu prüfen. Geraten wird nichts.
Liegen mehrere Ereignisse zwischen den beiden Einreichungen, wird gegen ihr Produkt geprüft.
Läuft im Betriebsmodus (auch Ereignisse ab 2025); Backtests lesen die Liste nur bis zur Datumsgrenze des Tresors.
"""
import math
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM
from tradingbot.daten.sp500_nachbau import ciks_der_zeile, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.engines.fundamental.aktienzahl import aktienfakten
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
LISTE = PROJEKT_WURZEL / "config" / "kapitalmassnahmen_historie.yaml"
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_split_ereignisse.md"
TOLERANZ = 0.015          # relative Abweichung, bis zu der r als „gleich“ gilt
ENG = 0.002               # enge Toleranz bei Faktoren nahe 1
MAX_TAGE_DANACH = 460     # erste Einreichung nach dem Ereignis höchstens ~15 Monate später
# Bekannte Bestätigungen aus Primärquellen (nicht aus dem Gedächtnis): Ticker, Datum → Bemerkung
BESTAETIGT = {("CMCSA", "2026-01-05"): ("abspaltung", "SEC 8-K vom 05.01.2026 (accn 0000950103-26-000079): Abspaltung Versant Media "
                                                     "(VSNT), 1 Versant je 25 Comcast, wirksam 02.01.2026 23:59 ET")}


def gleich(a: float, b: float) -> bool:
    return b != 0 and abs(a / b - 1) <= TOLERANZ


def skalierungsfehler(r: float) -> bool:
    e = math.log10(r) if r > 0 else 0
    return abs(e) >= 2.5 and abs(e - 3 * round(e / 3)) < 0.05


PERIODENBERICHTE = ("10-K", "10-Q", "10-K/A", "10-Q/A", "10-KT", "10-KT/A", "20-F", "40-F")


def sec_verhaeltnis(fakten: pd.DataFrame, tag: pd.Timestamp) -> tuple[float | None, pd.Timestamp | None, pd.Timestamp | None, str]:
    """r = Wert derselben Periode im ersten Periodenbericht (10-K/10-Q) nach `tag` / Wert in einem Periodenbericht davor
    (gleicher Begriff). 8-K-Neudarstellungen zählen nicht (CF 2015: 8-K nach dem Split noch auf alter Basis). Paare mit
    Skalierungsfehler (Verhältnis ≈ 10^3k) werden übersprungen; es gilt das jüngste übrige Paar."""
    if fakten is None or fakten.empty:
        return None, None, None, "keine SEC-Aktienzahlen"
    f = fakten[fakten["form"].fillna("").isin(PERIODENBERICHTE)]
    vor, nach = f[f["filed"] < tag], f[f["filed"] > tag]
    if vor.empty or nach.empty:
        return None, None, None, "kein Periodenbericht " + ("davor" if vor.empty else "danach")
    erste_nach = nach["filed"].min()
    if (erste_nach - tag).days > MAX_TAGE_DANACH:
        return None, None, None, f"erster Periodenbericht danach erst {erste_nach.date()}"
    neu = nach[nach["filed"] == erste_nach]
    skaliert = None
    for _, z in neu.sort_values(["ende", "rang"], ascending=[False, True]).iterrows():
        alt = vor[(vor["ende"] == z["ende"]) & (vor["start"] == z["start"]) & (vor["konzept"] == z["konzept"])].sort_values("filed", ascending=False)
        for _, a in alt.iterrows():
            if not a["wert"]:
                continue
            r = float(z["wert"]) / float(a["wert"])
            if skalierungsfehler(r):
                skaliert = skaliert or (r, a["filed"])
                continue
            return r, a["filed"], erste_nach, ""
    if skaliert:                                  # nur Paare mit Skalierungsfehler: Verhältnis trotzdem zurück (einordnen bereinigt)
        return skaliert[0], skaliert[1], erste_nach, ""
    return None, None, None, "dieselbe Periode davor nicht gemeldet"


def einordnen(f: float, r: float | None, produkt: float, anzahl: int, grund: str) -> tuple[str, float | None, str]:
    """(Art, Split-Faktor, Bemerkung) für ein Ereignis mit Faktor f; `produkt` = Produkt aller Faktoren im Fenster."""
    if r is None:
        return "unklar", None, grund
    for basis, art, faktor in ((produkt, "split", f), (1.0, "abspaltung", 1.0)):
        if skalierungsfehler(r / basis):
            k = round(math.log10(r / basis) / 3)
            rest = r / 1000 ** k
            if gleich(rest, basis):
                return "unklar", None, (f"SEC-Verhältnis {r:.4g}: Skalierungsfehler (Tausend statt Stück), bereinigt {rest:.4f}; "
                                        f"Vorschlag: {art}, Split-Faktor {faktor:g}")
    if skalierungsfehler(r):
        return "unklar", None, f"SEC-Verhältnis {r:.4g}: Skalierungsfehler (Tausend statt Stück)"
    if abs(produkt - 1) < 2 * TOLERANZ:          # Faktor nahe 1: Split und Abspaltung nur mit enger Toleranz unterscheidbar
        if abs(r - 1) < ENG and abs(r / produkt - 1) >= ENG:
            return "abspaltung", 1.0, f"Faktor nahe 1, SEC-Verhältnis {r:.4f} = 1"
        if abs(r / produkt - 1) < ENG and abs(r - 1) >= ENG:
            return "split", f, f"Faktor nahe 1, SEC-Verhältnis {r:.4f} = Faktor (Aktiendividende)"
        return "unklar", None, f"Faktor nahe 1, SEC-Verhältnis {r:.4f} nicht eindeutig"
    ueberlagert = f" (zusammen mit {anzahl - 1} weiteren Ereignissen im Fenster, Produkt {produkt:.4g})" if anzahl > 1 else ""
    if gleich(r, produkt):
        return "split", f, "SEC-Verhältnis = Faktor" + ueberlagert
    if gleich(r, 1.0):
        return "abspaltung", 1.0, "SEC-Verhältnis = 1" + ueberlagert
    if anzahl > 1:
        return "unklar", None, f"SEC-Verhältnis {r:.4f} passt weder zu 1 noch zum Produkt" + ueberlagert
    return "kombiniert", r, f"SEC-Verhältnis {r:.4f}: Split-Anteil, Rest Abspaltung (Vorschlag, zu prüfen)"


def aktienfakten_mit_quartalen(ciks) -> pd.DataFrame:
    """Gewichtete Aktienzahl für Quartale und Geschäftsjahre (80–380 Tage) aus den gecachten companyfacts, ohne Netzabruf.
    Quartale lassen Ereignisse schon mit dem nächsten 10-Q einordnen (Vorjahresquartal neu dargestellt)."""
    from tradingbot.daten.sec import SecClient
    from tradingbot.konfiguration import lade_konfiguration

    definition = lade_konfiguration("fundamental")["kennzahlen"]["gewichtete_aktien"]
    client, teile = SecClient(user_agent="offline"), []
    for cik in ciks:
        roh, _ = client.companyfacts_aus_cache(cik)
        if roh is not None:
            teile.append(aktienfakten(roh, definition, (80, 380)))
    return pd.concat(teile, ignore_index=True) if teile else pd.DataFrame()


def main() -> int:
    from ruamel.yaml import YAML

    yaml = YAML()
    alt = {}
    if LISTE.exists():
        for e in (yaml.load(LISTE.read_text(encoding="utf-8")) or {}).get("ereignisse", []) or []:
            alt[(int(e["cik"]), str(e["datum"]))] = dict(e)
    with betriebsmodus("Einordnung Split-Ereignisse der Kursreihen gegen die SEC (Teil a, nur lesend außer Liste/Bericht)"):
        universum, _ = lade_universum()
        status = pd.read_csv(PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv").set_index("index")
        daten = lade_firmendaten(universum, status, lade_sic_historien(universum), mitglied_ab=ABNAHME_ZEITRAUM[0],
                                  bis=pd.Timestamp(datetime.now().date()))
        namen = {int(z["cik"]): z["ticker"] for _, z in daten.relevant.sort_values("von", na_position="first").iterrows() if pd.notna(z["cik"])}
        cache = standard_cache()
        eintraege = []
        for firma, kurse in sorted(daten.kurse.items(), key=lambda x: str(x[0])):
            if isinstance(firma, str) or kurse is None or "split" not in kurse.columns:
                continue
            s = kurse["split"].fillna(0)
            s = s[(s > 0) & (s.index >= pd.Timestamp("2012-01-01"))]
            if s.empty:
                continue
            zeile = daten.relevant[daten.relevant["cik"] == firma].iloc[0]
            fakten = aktienfakten_mit_quartalen(ciks_der_zeile(zeile))
            for tag, f in s.items():
                schluessel = (int(firma), str(tag.date()))
                if alt.get(schluessel, {}).get("geprueft"):
                    eintraege.append(alt[schluessel])
                    continue
                r, vor_f, nach_f, grund = sec_verhaeltnis(fakten, tag)
                fenster = s[(s.index > vor_f) & (s.index < nach_f)] if r is not None else s[s.index == tag]
                art, faktor, bemerkung = einordnen(float(f), r, float(fenster.prod()), len(fenster), grund)
                ticker = namen.get(int(firma), f"CIK{firma}")
                bestaetigt = BESTAETIGT.get((ticker, str(tag.date())))
                if bestaetigt and bestaetigt[0] == art:
                    bemerkung += "; bestätigt: " + bestaetigt[1]
                elif bestaetigt:
                    bemerkung += f"; ABWEICHUNG zur Primärquelle ({bestaetigt[0]}): " + bestaetigt[1]
                    art, faktor = "unklar", None
                eintraege.append({"cik": int(firma), "ticker": ticker, "datum": str(tag.date()), "faktor_kursreihe": round(float(f), 6),
                                  "sec_verhaeltnis": None if r is None else round(r, 6),
                                  "sec_einreichungen": None if r is None else f"{vor_f.date()} → {nach_f.date()}",
                                  "art": art, "split_faktor": None if faktor is None else round(float(faktor), 6),
                                  "quelle": "SEC-Vergleich automatisch", "geprueft": False, "bemerkung": bemerkung})
    eintraege.sort(key=lambda e: (e["datum"], e["ticker"]))
    kopf = ("# Einordnung der „Split“-Ereignisse der Kursreihen (tools/split_ereignisse_einordnen.py, Jakob 13.11.2026).\n"
            "# art: split | abspaltung | kombiniert | unklar; split_faktor gilt für die Aktienzahl (Abspaltung: 1).\n"
            "# Einträge mit geprueft: true hat Jakob bestätigt; sie bleiben bei neuen Läufen unverändert.\n"
            "# Backtests lesen nur Ereignisse bis zur Datumsgrenze des Tresors.\n")
    from io import StringIO
    puffer = StringIO()
    yaml.dump({"stand": datetime.now().isoformat(timespec="seconds"), "ereignisse": eintraege}, puffer)
    LISTE.write_text(kopf + puffer.getvalue(), encoding="utf-8")

    df = pd.DataFrame(eintraege)
    df["zeitraum"] = df["datum"].map(lambda d: "Backtest bis 2024" if d <= "2024-12-31" else "Betrieb ab 2025")
    zaehl = df.pivot_table(index="art", columns="zeitraum", values="cik", aggfunc="count", fill_value=0)
    pruef = df[df["art"].isin(["kombiniert", "unklar"]) & (df["zeitraum"] == "Backtest bis 2024")]
    pruef_betrieb = df[df["art"].isin(["kombiniert", "unklar"]) & (df["zeitraum"] == "Betrieb ab 2025")]
    text = ["# Split-Ereignisse der Kursreihen: Einordnung und Prüfliste", "",
            f"Erstellt {datetime.now():%d.%m.%Y %H:%M} mit `tools/split_ereignisse_einordnen.py`; Liste `config/kapitalmassnahmen_historie.yaml`. "
            f"{len(df)} Ereignisse ab 2012 in den Kursreihen des Universums.", "",
            "| Art | " + " | ".join(zaehl.columns) + " |", "| --- |" + " --- |" * len(zaehl.columns)]
    for art, z in zaehl.iterrows():
        text.append(f"| {art} | " + " | ".join(str(int(v)) for v in z) + " |")
    text += ["", f"## Prüfliste Backtest bis 2024 ({len(pruef)} Fälle: kombiniert oder unklar)", "",
             "Bitte je Fall: Art (split, abspaltung, kombiniert) und Split-Faktor für die Aktienzahl bestätigen oder korrigieren.", "",
             "| Ticker (CIK) | Datum | Faktor Kursreihe | SEC-Verhältnis | Einreichungen | Vorschlag | Bemerkung |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for z in pruef.itertuples():
        vorschlag = f"{z.art}, Split-Faktor {z.split_faktor:g}" if z.split_faktor is not None and not pd.isna(z.split_faktor) else z.art
        sec = "–" if z.sec_verhaeltnis is None or pd.isna(z.sec_verhaeltnis) else f"{z.sec_verhaeltnis:.4f}"
        text.append(f"| {z.ticker} ({z.cik}) | {z.datum} | {z.faktor_kursreihe:g} | {sec} | {z.sec_einreichungen or '–'} | {vorschlag} | {z.bemerkung} |")
    text += ["", f"## Betrieb ab 2025 noch offen ({len(pruef_betrieb)})", "",
             "Im SEC-Cache (companyfacts vom 02.11.2026) fehlt noch ein Periodenbericht, der dieselbe Periode vor und nach dem "
             "Ereignis zeigt, oder das Verhältnis ist nicht eindeutig. Ein Lauf nach dem nächsten SEC-Abruf ordnet die meisten "
             "selbst ein; was danach offen bleibt, kommt zur Prüfung. Gehaltene Titel der Bücher sind darunter nicht.", "",
             "| Ticker (CIK) | Datum | Faktor Kursreihe | Bemerkung |", "| --- | --- | --- | --- |"]
    for z in pruef_betrieb.itertuples():
        text.append(f"| {z.ticker} ({z.cik}) | {z.datum} | {z.faktor_kursreihe:g} | {z.bemerkung} |")
    abs_ = df[df["art"] == "abspaltung"]
    text += ["", f"## Automatisch als Abspaltung eingeordnet ({len(abs_)})", "",
             ", ".join(f"{z.ticker} {z.datum} ({z.faktor_kursreihe:g})" for z in abs_.itertuples()) or "–", ""]
    einfach_aber_abs = abs_[abs_["faktor_kursreihe"].map(lambda v: abs(v - round(v)) < 1e-6 or abs(1 / v - round(1 / v)) < 1e-6)]
    if len(einfach_aber_abs):
        text += [f"Achtung: {len(einfach_aber_abs)} davon haben ein glattes Verhältnis: "
                 + ", ".join(f"{z.ticker} {z.datum}" for z in einfach_aber_abs.itertuples()), ""]
    BERICHT.write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))
    return 0


if __name__ == "__main__":
    sys.exit(main())
