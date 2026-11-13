"""Gewichtete Aktienzahl für Piotroski EQ_OFFER auf gleicher Split-Basis (Datenkorrektur, Jakob 13.11.2026).

Befund: EQ_OFFER verglich die Erstmeldungen der Jahre t und t−1. Nach US-GAAP (ASC 260) wird die Aktienzahl rückwirkend
auf die Split-Basis gebracht, auch bei einem Split nach dem Geschäftsjahresende, solange er vor der Einreichung liegt.
Liegt ein Split zwischen den Einreichungen für t−1 und t, steht ein Wert nach dem Split gegen einen davor: Ein Split
wirkt wie eine Kapitalerhöhung, ein Reverse-Split wie ein Rückkauf, jeweils für einen 10-K-Zyklus.

Korrektur (docs/FUNDAMENTAL.md, Abschnitt Datenkorrektur):
- Weg A: t−1 als Vergleichswert aus derselben Einreichung wie der Wert für t (gleiche accn, gleicher Begriff). Point-in-time
  sauber, weil er ab der Einreichung von t bekannt ist; Ausnahme von der Erstmeldungs-Regel nur für diesen Vergleichswert.
- Weg B (Rückfall, wenn A fehlt): Erstmeldung für t−1 mal Produkt der Split-Faktoren nach ihrer Einreichung bis
  einschließlich der Einreichung von t (nur Splits bis zum Stichtag). Split-Quelle ist die Spalte `split` der Kursreihe
  (Yahoo, Tiingo; im Betrieb zusätzlich quittierte Flex-Verhältnisse). Fehlt das Ereignis, bleibt B unbereinigt.
Beide Wege werden immer gerechnet (Gegenprobe).

Daten: Cache „sec_aktienfakten“ je CIK mit allen Einreichungen der Begriffe für die gewichtete Aktienzahl (nicht nur der
Erstmeldung), gebaut offline aus den gecachten companyfacts. Der Cache enthält alle Einreichungen; jede Abfrage geht über
`tresor.begrenze` (wie kennzahl_jahreswerte), damit Backtests nichts aus dem Tresor sehen.
"""
from __future__ import annotations

import pandas as pd

BEREICH = "sec_aktienfakten"
SPALTEN = ["konzept", "rang", "start", "ende", "wert", "filed", "form", "accn"]


def aktienfakten(roh: dict, definition: dict, jahresdauer: tuple[int, int] = (350, 380)) -> pd.DataFrame:
    """Alle Jahreswerte (Dauer `jahresdauer`) der Begriffe aus `definition` (config gewichtete_aktien), je Einreichung eine Zeile.
    `rang` = Position des Begriffs in der Liste (0 = Basic vor 1 = Diluted)."""
    zeilen = []
    fakten = roh.get("facts", {}) if roh else {}
    for rang, name in enumerate(definition["konzepte"]):
        taxonomie, _, konzept = name.partition(":")
        for w in fakten.get(taxonomie, {}).get(konzept, {}).get("units", {}).get(definition["einheit"], []):
            if w.get("start"):
                zeilen.append((name, rang, w["start"], w["end"], w["val"], w["filed"], w.get("form"), w.get("accn")))
    t = pd.DataFrame(zeilen, columns=SPALTEN)
    for spalte in ("start", "ende", "filed"):
        t[spalte] = pd.to_datetime(t[spalte])
    t["wert"] = pd.to_numeric(t["wert"], errors="coerce")
    t["rang"] = t["rang"].astype("int64")
    dauer = (t["ende"] - t["start"]).dt.days
    return t[dauer.between(*jahresdauer) & t["wert"].notna()].sort_values(["ende", "filed", "accn"]).reset_index(drop=True)


def lade_aktienfakten(ciks, *, definition: dict | None = None, cache=None, client=None) -> pd.DataFrame:
    """Aktienfakten mehrerer CIKs (Firma und Vorgänger) aus dem Cache. Fehlt der Eintrag oder passt er nicht zum Stand der
    Erstmeldungen (`roh_abgerufen_um`), wird er offline aus den gecachten companyfacts neu gebaut (kein Netzabruf).
    CIKs ohne gecachte companyfacts fehlen im Ergebnis (dann greift Weg B)."""
    from tradingbot.daten.cache import standard_cache
    from tradingbot.daten.sec import SecClient, cik10
    from tradingbot.konfiguration import lade_konfiguration

    konfig = lade_konfiguration("fundamental")
    definition = definition or konfig["kennzahlen"]["gewichtete_aktien"]
    jahresdauer = tuple(konfig["sec"]["jahresdauer_tage"])
    cache = cache or standard_cache()
    teile = []
    for cik in ciks:
        schluessel = cik10(cik)
        tabelle, meta = cache.lesen(BEREICH, schluessel)
        _, meta_erst = cache.lesen("sec_erstmeldungen", schluessel)
        stand = (meta_erst or {}).get("roh_abgerufen_um")
        if tabelle is None or (stand and meta.get("roh_abgerufen_um") != stand):
            client = client or SecClient(user_agent="offline")
            roh, abgerufen = client.companyfacts_aus_cache(cik)
            if roh is None:
                continue
            tabelle = aktienfakten(roh, definition, jahresdauer)
            cache.schreiben(BEREICH, schluessel, tabelle, {"quelle": "SEC companyfacts (Cache, offline)",
                                                            "roh_abgerufen_um": abgerufen.isoformat(timespec="seconds")})
        teile.append(tabelle)
    teile = [t for t in teile if len(t)]
    return pd.concat(teile, ignore_index=True) if teile else pd.DataFrame(columns=SPALTEN)


def _erstmeldung(k: pd.DataFrame):
    """Zuerst gemeldeter Wert wie in kennzahlen.abschluesse_am: je Begriff die früheste Einreichung (Original vor „/A“,
    dann kleinere accn), über die Begriffe die früheste Einreichung, bei Gleichstand der vorrangige Begriff."""
    if k.empty:
        return None
    k = k.assign(_berichtigung=k["form"].fillna("").str.endswith("/A")).sort_values(["filed", "_berichtigung", "accn"])
    k = k.drop_duplicates("konzept", keep="first").sort_values(["filed", "rang"])
    return k.iloc[0]


def split_faktor(splits: pd.Series | None, nach, bis) -> float:
    """Produkt der Split-Faktoren mit nach < Datum ≤ bis (`splits`: Faktor am Split-Tag, sonst 0 oder fehlend)."""
    if splits is None or len(splits) == 0:
        return 1.0
    s = splits[splits.fillna(0) > 0]
    s = s[(s.index > pd.Timestamp(nach)) & (s.index <= pd.Timestamp(bis))]
    return float(s.prod()) if len(s) else 1.0


def eq_offer_vergleich(fakten: pd.DataFrame, ende_t, ende_vj, stichtag, splits: pd.Series | None = None) -> dict:
    """Aktienzahl t und t−1 auf gleicher Split-Basis, wie am Stichtag bekannt (bekannt ab dem Tag nach `filed`).

    Rückgabe: wert_t, wert_vj (gewählt: Weg A, sonst B), quelle („einreichung“ = A, „split“ = B, None = nichts bekannt),
    wert_vj_erst (Erstmeldung t−1, bisherige Rechnung), wert_vj_einreichung (A), wert_vj_split (B), split_faktor
    (Splits zwischen den Einreichungen, nur bis zum Stichtag), konzept, accn_t.
    """
    from tradingbot.backtest.tresor import begrenze

    tag = pd.Timestamp(stichtag)
    ergebnis = {"wert_t": None, "wert_vj": None, "quelle": None, "wert_vj_erst": None, "wert_vj_einreichung": None,
                "wert_vj_split": None, "split_faktor": 1.0, "konzept": None, "accn_t": None}
    if fakten is None or len(fakten) == 0:
        return ergebnis
    f = begrenze(fakten, "filed")
    bekannt = f[f["filed"] + pd.Timedelta(days=1) <= tag]
    zeile_t = _erstmeldung(bekannt[bekannt["ende"] == pd.Timestamp(ende_t)])
    zeile_vj = _erstmeldung(bekannt[bekannt["ende"] == pd.Timestamp(ende_vj)])
    if zeile_vj is not None:
        ergebnis["wert_vj_erst"] = float(zeile_vj["wert"])
    if zeile_t is None:
        return ergebnis
    ergebnis.update(wert_t=float(zeile_t["wert"]), konzept=zeile_t["konzept"], accn_t=zeile_t["accn"])
    gleich = bekannt[(bekannt["accn"] == zeile_t["accn"]) & (bekannt["konzept"] == zeile_t["konzept"])
                     & (bekannt["ende"] == pd.Timestamp(ende_vj))]
    if len(gleich):
        ergebnis["wert_vj_einreichung"] = float(gleich["wert"].iloc[0])
    if zeile_vj is not None:
        splits_bis = None if splits is None else splits[splits.index <= tag]
        faktor = split_faktor(splits_bis, zeile_vj["filed"], zeile_t["filed"])
        ergebnis.update(split_faktor=faktor, wert_vj_split=float(zeile_vj["wert"]) * faktor)
    if ergebnis["wert_vj_einreichung"] is not None:
        ergebnis.update(wert_vj=ergebnis["wert_vj_einreichung"], quelle="einreichung")
    elif ergebnis["wert_vj_split"] is not None:
        ergebnis.update(wert_vj=ergebnis["wert_vj_split"], quelle="split")
    return ergebnis


def korrektur_aktiv(tag, konfig: dict | None = None) -> bool:
    """Gilt die Datenkorrektur im Betrieb am Tag `tag`? Ab `piotroski_eq_offer.splitbereinigt_ab` (04.01.2027, erster
    Rebalancing-Stichtag Januar 2027), gleichzeitig für Auswahl A/B und das Fundamental-Veto (Jakob 13.11.2026)."""
    from tradingbot.konfiguration import lade_konfiguration

    ab = ((konfig or lade_konfiguration("fundamental")).get("piotroski_eq_offer") or {}).get("splitbereinigt_ab")
    return ab is not None and pd.Timestamp(tag).normalize() >= pd.Timestamp(str(ab))


def vergleich_fuer_abschluesse(t: pd.DataFrame, fakten: pd.DataFrame, stichtag, splits: pd.Series | None = None) -> dict | None:
    """eq_offer_vergleich für die Jahre t (Zeile 0) und t−1 (Zeile 1) aus kennzahlen.abschluesse_am; None ohne zwei Jahre."""
    if t is None or len(t) < 2:
        return None
    return eq_offer_vergleich(fakten, t.index[0], t.index[1], stichtag, splits)


def signal_alt_neu(t: pd.DataFrame, eq: dict | None) -> tuple[int | None, int | None]:
    """EQ_OFFER bisher (Erstmeldungen aus `t`) und korrigiert (`eq`); None, wo die Werte fehlen. Fehlt die Korrektur,
    gilt für „neu“ derselbe Wert wie bisher (Rückfall in piotroski)."""
    from tradingbot.engines.fundamental.scores import _w

    a_t, a_vj = (_w(t, "gewichtete_aktien", 0), _w(t, "gewichtete_aktien", 1)) if t is not None and len(t) else (None, None)
    alt = None if a_t is None or a_vj is None else int(a_t <= a_vj)
    if eq and eq.get("wert_t") is not None and eq.get("wert_vj") is not None:
        return alt, int(eq["wert_t"] <= eq["wert_vj"])
    return alt, alt
