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
import sys
import warnings
from datetime import datetime

import pandas as pd

from tradingbot.backtest.tresor import betriebsmodus
from tradingbot.daten.cache import standard_cache
from tradingbot.daten.index_nachbau import ABNAHME_ZEITRAUM
from tradingbot.daten.sp500_nachbau import ciks_der_zeile, lade_firmendaten
from tradingbot.daten.universum import lade_sic_historien, lade_universum
from tradingbot.daten.kapitalmassnahmen_historie import einordnen, sec_verhaeltnis
from tradingbot.engines.fundamental.aktienzahl import aktienfakten
from tradingbot.konfiguration import PROJEKT_WURZEL

warnings.simplefilter("ignore")
LISTE = PROJEKT_WURZEL / "config" / "kapitalmassnahmen_historie.yaml"
BERICHT = PROJEKT_WURZEL / "docs" / "berichte" / "2026-11-13_split_ereignisse.md"
# Bekannte Bestätigungen aus Primärquellen (nicht aus dem Gedächtnis): Ticker, Datum → Bemerkung
BESTAETIGT = {("CMCSA", "2026-01-05"): ("abspaltung", "SEC 8-K vom 05.01.2026 (accn 0000950103-26-000079): Abspaltung Versant Media "
                                                     "(VSNT), 1 Versant je 25 Comcast, wirksam 02.01.2026 23:59 ET")}


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
            "# art: split (auch Reverse-Split, Aktiendividende) | abspaltung | kombiniert | unklar | nicht_zugehoerig; split_faktor gilt für die Aktienzahl (Abspaltung: 1).\n"
            "# Einträge mit geprueft: true hat Jakob bestätigt; sie bleiben bei neuen Läufen unverändert.\n"
            "# Backtests lesen nur Ereignisse bis zur Datumsgrenze des Tresors.\n")
    from io import StringIO
    puffer = StringIO()
    yaml.dump({"stand": datetime.now().isoformat(timespec="seconds"), "ereignisse": eintraege}, puffer)
    LISTE.write_text(kopf + puffer.getvalue(), encoding="utf-8")

    df = pd.DataFrame(eintraege)
    df["zeitraum"] = df["datum"].map(lambda d: "Backtest bis 2024" if d <= "2024-12-31" else "Betrieb ab 2025")
    zaehl = df.pivot_table(index="art", columns="zeitraum", values="cik", aggfunc="count", fill_value=0)
    offen = df["art"].isin(["kombiniert", "unklar"]) & ~df["geprueft"].astype(bool)
    pruef = df[offen & (df["zeitraum"] == "Backtest bis 2024")]
    pruef_betrieb = df[offen & (df["zeitraum"] == "Betrieb ab 2025")]
    geprueft = df[df["geprueft"].astype(bool)]
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
    text += ["", f"## Von Jakob geprüft, mit Beleg ({len(geprueft)})", "",
             "| Ticker (CIK) | Datum | Faktor Kursreihe | Art | Split-Faktor | Beleg |", "| --- | --- | --- | --- | --- | --- |"]
    for z in geprueft.itertuples():
        f = "–" if z.split_faktor is None or pd.isna(z.split_faktor) else f"{z.split_faktor:g}"
        text.append(f"| {z.ticker} ({z.cik}) | {z.datum} | {z.faktor_kursreihe:g} | {z.art} | {f} | {z.quelle} |")
    abs_ = df[(df["art"] == "abspaltung") & ~df["geprueft"].astype(bool)]
    text += ["", f"## Automatisch als Abspaltung eingeordnet, ungeprüft ({len(abs_)})", "",
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
