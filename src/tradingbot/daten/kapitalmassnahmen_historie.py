"""Kapitalmaßnahmen der Kursreihen: Einordnung (Split, Abspaltung, kombiniert, unklar) und Korrekturfaktor für den
Marktwert (Datenkorrektur Marktwert, Teile a und b, Jakob 13.11.2026, docs/FUNDAMENTAL.md).

Befund: Yahoo (und Tiingo) führen in der Spalte `split` echte Splits, aber auch Abspaltungen (Kursbereinigung). Die
Aktienzahl wurde bisher mit allen Faktoren nach ihrem Messtag d multipliziert (index_nachbau.aktien_splitbereinigt).
Für einen Stichtag T ist das nur für Ereignisse nach T richtig (der Kurs bei T ist um sie bereinigt). Zwischen d und T
ändert nur ein echter Split die Aktienzahl, eine Abspaltung nicht.

    Aktienzahl auf Kursbasis(T) = A_d · Π_{d<e≤T} s_e · Π_{e>T} f_e
                                = A_d · Π_{e>d} f_e · K(d, T),     K(d, T) = Π_{d<e≤T} s_e / f_e

f_e = Faktor der Kursreihe, s_e = Split-Faktor für die Aktienzahl (Liste `config/kapitalmassnahmen_historie.yaml`;
Abspaltung 1, Split f_e, kombiniert der geprüfte Wert). Ungeklärte Ereignisse (unklar, nicht_zugehoerig, nicht in der
Liste) behalten s_e = f_e (bisheriges Verhalten) und werden markiert (Entscheidung Jakob 13.11.2026). Derselbe Faktor
K(e, T) korrigiert die Fortschreibung des Streubesitzes F_e · C_T / C_e (Index-Nachbau, Plausibilitätsprüfung).

Einordnung (Teil a, `einordnen`): Den echten Split-Faktor zeigt die SEC. Dieselbe Periode (gewichtete Aktienzahl) steht
vor dem Ereignis in der alten und danach im ersten Periodenbericht neu auf der neuen Basis (ASC 260, rückwirkend).
Verhältnis r = neu/alt: r ≈ Faktor → Split; r ≈ 1 → Abspaltung; sonst kombiniert (zu prüfen) oder unklar.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

TOLERANZ = 0.015          # relative Abweichung, bis zu der r als „gleich“ gilt
ENG = 0.002               # enge Toleranz bei Faktoren nahe 1
MAX_TAGE_DANACH = 460     # erste Einreichung nach dem Ereignis höchstens ~15 Monate später
PERIODENBERICHTE = ("10-K", "10-Q", "10-K/A", "10-Q/A", "10-KT", "10-KT/A", "20-F", "40-F")
EINDEUTIG = {"split", "abspaltung", "kombiniert"}      # Arten mit Split-Faktor für die Aktienzahl


def gleich(a: float, b: float) -> bool:
    return b != 0 and abs(a / b - 1) <= TOLERANZ


def skalierungsfehler(r: float) -> bool:
    e = math.log10(r) if r > 0 else 0
    return abs(e) >= 2.5 and abs(e - 3 * round(e / 3)) < 0.05


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


def einordnen_automatisch(fakten: pd.DataFrame | None, splits: pd.Series, tag) -> tuple[str, float | None, str]:
    """Einordnung eines Ereignisses der Kursreihe zur Laufzeit (Betrieb: neue Ereignisse, noch nicht in der Liste).
    `fakten`: gewichtete Aktienzahl mit Quartalen (aktienzahl.lade_aktienfakten(..., mit_quartalen=True))."""
    tag = pd.Timestamp(tag)
    s = splits.fillna(0)
    s = s[s > 0]
    f = float(s.get(tag, 0) or 0)
    if not f > 0:
        return "unklar", None, "kein Ereignis an diesem Tag"
    r, vor_f, nach_f, grund = sec_verhaeltnis(fakten, tag)
    fenster = s[(s.index > vor_f) & (s.index < nach_f)] if r is not None else s[s.index == tag]
    art, faktor, bemerkung = einordnen(f, r, float(fenster.prod()), len(fenster), grund)
    if art == "kombiniert":                       # kombiniert nur nach Prüfung durch Jakob; automatisch bleibt es ungeklärt
        return "unklar", None, bemerkung
    return art, faktor, bemerkung


LISTE = Path(__file__).resolve().parents[3] / "config" / "kapitalmassnahmen_historie.yaml"


def lade_ereignisse(pfad: Path | None = None) -> dict[int, pd.DataFrame]:
    """Liste der eingeordneten Ereignisse je CIK: Index datum, Spalten art, split_faktor, faktor_kursreihe, geprueft, quelle.
    Die Liste enthält auch Ereignisse ab 2025; wirksam werden nur Ereignisse, die in der (vom Tresor begrenzten) Kursreihe
    stehen, weil `korrektur` von den Ereignissen der Kursreihe ausgeht."""
    from ruamel.yaml import YAML

    pfad = pfad or LISTE
    roh = (YAML(typ="safe").load(pfad.read_text(encoding="utf-8")) or {}).get("ereignisse", []) or []
    tabelle = pd.DataFrame(roh)
    if tabelle.empty:
        return {}
    tabelle["datum"] = pd.to_datetime(tabelle["datum"].astype(str))
    tabelle["geprueft"] = tabelle.get("geprueft", False)
    ergebnis = {}
    for cik, g in tabelle.groupby("cik"):
        g = g.sort_values(["datum", "geprueft"], ascending=[True, False]).drop_duplicates("datum", keep="first")
        ergebnis[int(cik)] = g.set_index("datum")[["art", "split_faktor", "faktor_kursreihe", "geprueft", "quelle"]]
    return ergebnis


def ereignisse_mit_flex(ereignisse: pd.DataFrame | None, kurse: pd.DataFrame, splits_flex: list[tuple[str, float]] | None) -> pd.DataFrame | None:
    """Quittierte Splits „Quelle: Flex“ (Betrieb, gehaltene Titel) als eingeordnete Splits ergänzen. Datum: Ereignis der
    Kursreihe bis 3 Handelstage um den Flex-Stichtag, sonst erster Handelstag ab dem Stichtag (wie
    aktuell.split_ereignisse_ergaenzen). Split-Faktor = Faktor der Kursreihe dort, sonst das Flex-Verhältnis. Flex hat Vorrang."""
    if not splits_flex:
        return ereignisse
    zeilen = []
    split = kurse["split"].fillna(0) if "split" in kurse.columns else pd.Series(0.0, index=kurse.index)
    for tag, r in splits_flex:
        pos = int(kurse.index.searchsorted(pd.Timestamp(tag)))
        if pos >= len(kurse.index):
            continue
        nahe = split.iloc[max(0, pos - 3):pos + 4]
        nahe = nahe[nahe > 0]
        datum = min(nahe.index, key=lambda d: abs((d - pd.Timestamp(tag)).days)) if len(nahe) else kurse.index[pos]
        f = float(split.get(datum, 0) or 0)
        zeilen.append({"datum": datum, "art": "split", "split_faktor": f if f > 0 else float(r), "faktor_kursreihe": f or float(r),
                       "geprueft": True, "quelle": "Flex"})
    if not zeilen:
        return ereignisse
    flex = pd.DataFrame(zeilen).set_index("datum")
    basis = ereignisse if ereignisse is not None else flex.iloc[0:0]
    return pd.concat([flex, basis[~basis.index.isin(flex.index)]]).sort_index()


def korrektur(splits: pd.Series | None, ereignisse: pd.DataFrame | None, nach, bis, *, fakten: pd.DataFrame | None = None
              ) -> tuple[float, list[dict]]:
    """K(nach, bis) = Π s_e / f_e über die Ereignisse der Kursreihe mit nach < e ≤ bis, und die ungeklärten Ereignisse.

    `splits`: Spalte `split` der Kursreihe (Faktor am Tag, sonst 0/NaN); `ereignisse`: Liste dieser Firma (lade_ereignisse).
    Ereignis nicht in der Liste: mit `fakten` automatisch einordnen (einordnen_automatisch), sonst ungeklärt.
    Ungeklärt (unklar, nicht_zugehoerig, kombiniert ohne Faktor, unbekannt): s_e = f_e, Faktor 1, Eintrag in der Liste.
    """
    if splits is None or len(splits) == 0:
        return 1.0, []
    s = splits.fillna(0)
    s = s[(s > 0) & (s.index > pd.Timestamp(nach)) & (s.index <= pd.Timestamp(bis))]
    faktor, ungeklaert = 1.0, []
    for tag, f in s.items():
        art, sf, quelle = None, None, None
        if ereignisse is not None and tag in ereignisse.index:
            z = ereignisse.loc[tag]
            art, sf, quelle = z["art"], z["split_faktor"], "Liste"
            if art == "unklar" and not bool(z["geprueft"]) and fakten is not None:   # Betrieb: neuer Periodenbericht da?
                neu = einordnen_automatisch(fakten, splits, tag)
                if neu[0] in EINDEUTIG:
                    art, sf, quelle = neu[0], neu[1], "automatisch eingeordnet, ungeprüft"
        elif fakten is not None:
            art, sf, _ = einordnen_automatisch(fakten, splits, tag)
            quelle = "automatisch eingeordnet, ungeprüft"
        if art in EINDEUTIG and sf is not None and not pd.isna(sf) and float(sf) > 0:
            faktor *= float(sf) / float(f)
        else:
            ungeklaert.append({"datum": tag.date(), "faktor_kursreihe": float(f), "art": art or "nicht in der Liste",
                               "quelle": quelle or "–"})
    return faktor, ungeklaert


def korrektur_reihe(splits: pd.Series | None, ereignisse: pd.DataFrame | None, nach, tage: pd.DatetimeIndex) -> pd.Series:
    """K(nach, t) für alle Tage t (Index-Nachbau): stufenweise ab dem Tag des Ereignisses."""
    ergebnis = pd.Series(1.0, index=tage)
    if splits is None or len(splits) == 0 or len(tage) == 0:
        return ergebnis
    s = splits.fillna(0)
    for tag in s[(s > 0) & (s.index > pd.Timestamp(nach)) & (s.index <= tage.max())].index:
        k, _ = korrektur(splits, ereignisse, tag - pd.Timedelta(days=1), tag)
        if k != 1.0:
            ergebnis[ergebnis.index >= tag] *= k
    return ergebnis
