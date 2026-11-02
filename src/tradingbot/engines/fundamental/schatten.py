"""Fundamental-Schattenportfolio und Kontrollportfolio (Entscheidungen Jakob 03.11.2026, config/fundamental.yaml
`schattenportfolio`, docs/FUNDAMENTAL.md).

Auswahl am Rebalancing-Stichtag (ausgeführt zur Eröffnung des nächsten Handelstags):
1. Verkaufen: gehaltene Titel, die nicht mehr im gefilterten Universum sind (Filter, Austritt aus dem S&P 500, kein
   aktueller Abschluss) oder dort nicht mehr unter den besten `puffer_rang` (30) stehen.
2. Halten: übrige gehaltene Titel. Zurück auf 5 % nur, wenn ihr Gewicht außerhalb von `drift_band` (2,5–7,5 %) liegt;
   sonst bleibt der Bestand unverändert (Zielgewicht NaN).
3. Auffüllen: freie Plätze (höchstens `titel` = 20) gehen in Rangfolge an die besten noch nicht gehaltenen Titel, solange
   ihre zweistellige SIC unter der Branchenobergrenze bleibt (25 % von 20 = 5 Positionen; gehaltene zählen mit).
Die 125-€-Regel (Gebühr höchstens 1 %) prüft die Simulation zusätzlich.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from tradingbot.kennzahlen.rendite import total_return_index


class FundamentalSchatten:
    """Strategie für `backtest.simulation`: Zielgewichte je Stichtag aus den Gesamtscore-Ranglisten.

    `ranglisten`: Stichtag → gesamtscore()-Tabelle des gefilterten Universums mit Spalte `ticker` (bester zuerst) und
    `sic`. Eine Rangliste wird am ersten Simulationstag ab ihrem Stichtag verwendet, nie vorher (kein Look-ahead).
    """

    def __init__(self, ranglisten: dict[pd.Timestamp, pd.DataFrame], konfig: dict):
        sp = konfig["schattenportfolio"]
        self.titel = int(sp["titel"])
        self.puffer = int(sp["puffer_rang"])
        self.max_je_branche = math.floor(float(sp["max_branchenanteil"]) * self.titel + 1e-9)
        self.band = tuple(float(x) for x in sp["drift_band"])
        self.ranglisten = dict(sorted((pd.Timestamp(k), v) for k, v in ranglisten.items()))
        self._offen = list(self.ranglisten)
        self.name = f"Fundamental-Schatten ({self.titel} Titel, Puffer {self.puffer}, Q)"
        self.protokoll: list[dict] = []

    def zielgewichte(self, stichtag, sicht):
        tag = pd.Timestamp(stichtag)
        faellig = [d for d in self._offen if d <= tag]
        if not faellig:
            return None
        for d in faellig:
            self._offen.remove(d)
        datum = faellig[-1]
        rangliste = self.ranglisten[datum]
        ziel, eintraege = auswahl(rangliste, sicht.gewichte(), titel=self.titel, puffer=self.puffer,
                                  max_je_branche=self.max_je_branche, band=self.band)
        for e in eintraege:
            e.update({"stichtag": datum, "signal_tag": tag})
        self.protokoll.extend(eintraege)
        return ziel


def auswahl(rangliste: pd.DataFrame, gewichte: pd.Series, *, titel: int, puffer: int, max_je_branche: int,
            band: tuple[float, float]) -> tuple[pd.Series, list[dict]]:
    """Reine Auswahlregel (testbar ohne Simulation). Gibt Zielgewichte (NaN = halten) und ein Protokoll zurück."""
    r = rangliste.reset_index(drop=True)
    rang = {t: i + 1 for i, t in enumerate(r["ticker"])}
    sic2 = dict(zip(r["ticker"], r["sic"].astype(int) // 100))
    zeile = r.set_index("ticker")
    ziel_gewicht = 1.0 / titel
    ziel, protokoll, behalten = {}, [], []

    for t in sorted(gewichte.index):
        w = float(gewichte[t])
        if t not in rang:
            ziel[t] = 0.0
            protokoll.append({"ticker": t, "aktion": "verkaufen", "grund": "nicht im gefilterten Universum", "rang": None, "gewicht_vorher": w})
        elif rang[t] > puffer:
            ziel[t] = 0.0
            protokoll.append({"ticker": t, "aktion": "verkaufen", "grund": f"Rang {rang[t]} > {puffer}", "rang": rang[t], "gewicht_vorher": w})
        else:
            behalten.append(t)
    # Bei mehr als `titel` gehaltenen Titeln (kommt nur bei Fehlern vor) die schlechtesten verkaufen
    behalten.sort(key=lambda t: rang[t])
    for t in behalten[titel:]:
        ziel[t] = 0.0
        protokoll.append({"ticker": t, "aktion": "verkaufen", "grund": "mehr als Höchstzahl", "rang": rang[t], "gewicht_vorher": float(gewichte[t])})
    behalten = behalten[:titel]
    for t in behalten:
        w = float(gewichte[t])
        if w < band[0] or w > band[1]:
            ziel[t] = ziel_gewicht
            aktion = "zurück auf Zielgewicht"
        else:
            ziel[t] = math.nan
            aktion = "halten"
        protokoll.append({"ticker": t, "aktion": aktion, "grund": f"Gewicht {w:.1%}", "rang": rang[t], "gewicht_vorher": w,
                          "ersetzt": zeile.loc[t, "ersetzt"] if "ersetzt" in zeile.columns else ""})

    je_branche: dict[int, int] = {}
    for t in behalten:
        je_branche[sic2[t]] = je_branche.get(sic2[t], 0) + 1
    plaetze = titel - len(behalten)
    for t in r["ticker"]:
        if plaetze <= 0:
            break
        if t in gewichte.index:
            continue
        if je_branche.get(sic2[t], 0) >= max_je_branche:
            continue
        ziel[t] = ziel_gewicht
        je_branche[sic2[t]] = je_branche.get(sic2[t], 0) + 1
        plaetze -= 1
        protokoll.append({"ticker": t, "aktion": "kaufen", "grund": "freier Platz", "rang": rang[t], "gewicht_vorher": 0.0,
                          "ersetzt": zeile.loc[t, "ersetzt"] if "ersetzt" in zeile.columns else ""})
    return pd.Series(ziel, dtype=float), protokoll


def kontrollportfolio(ranglisten: dict[pd.Timestamp, pd.DataFrame], kurse: dict[str, pd.DataFrame], kalender: pd.DatetimeIndex,
                      delistings: dict, startkapital: float, ende) -> tuple[pd.Series, pd.DataFrame]:
    """Alle Titel des gefilterten Universums gleich gewichtet, quartalsweise, ohne Kosten, vor Steuern.

    Formel je Quartal q (Kauf zur Eröffnung des ersten Handelstags e_q nach dem Stichtag, wie das Schattenportfolio):
        Faktor_i(t) = TRI_i(t) / TRI_i(e_q) · Close_i(e_q) / Open_i(e_q)        (Dividenden reinvestiert)
        V(t) = V_q · Mittelwert_i Faktor_i(t);   V_{q+1} = V_q · Mittelwert_i Faktor_i zur Eröffnung von e_{q+1}
    Delisting: ab dem letzten Kurstag gilt Faktor_i(L) · (1 + Delisting-Rendite), Erlös bleibt bis zum Quartalsende im
    Mittel (Kasse ohne Zins). Titel ohne Eröffnungskurs an e_q fallen für das Quartal heraus (gezählt).
    """
    ende = pd.Timestamp(ende)
    kal = kalender[kalender <= ende]
    stichtage = sorted(pd.Timestamp(d) for d in ranglisten)
    ausfuehrung = [kal[kal > d][0] for d in stichtage if (kal > d).any()]
    werte = pd.Series(np.nan, index=kal, dtype=float)
    werte.loc[kal[kal <= stichtage[0]][-1:]] = startkapital
    v = startkapital
    tri_cache: dict[str, pd.Series] = {}
    statistik = []
    for q, (d, e) in enumerate(zip(stichtage, ausfuehrung)):
        naechste = ausfuehrung[q + 1] if q + 1 < len(ausfuehrung) else None
        tage = kal[(kal >= e) & ((kal < naechste) if naechste is not None else (kal <= ende))]
        faktoren, faktoren_offen, ohne_kurs = [], [], 0
        for t in ranglisten[d]["ticker"]:
            k = kurse.get(t)
            if k is None or e not in k.index or not k.loc[e, "open"] > 0:
                ohne_kurs += 1
                continue
            if t not in tri_cache:
                tri_cache[t] = total_return_index(k)
            tri = tri_cache[t].reindex(kal).ffill()
            f = tri.loc[tage] / tri.loc[e] * float(k.loc[e, "close"]) / float(k.loc[e, "open"])
            dl = delistings.get(t)
            if dl is not None and dl.letzter_tag < tage[-1]:
                f_l = float(tri.loc[:dl.letzter_tag].iloc[-1] / tri.loc[e]) * float(k.loc[e, "close"]) / float(k.loc[e, "open"])
                f[f.index > dl.letzter_tag] = f_l * (1.0 + dl.rendite)
            faktoren.append(f)
            if naechste is not None:
                if dl is not None and dl.letzter_tag < naechste:
                    faktoren_offen.append(float(f.iloc[-1]))
                elif naechste in k.index and k.loc[naechste, "open"] > 0:
                    vortag = k.loc[k.index < naechste, "close"].iloc[-1]
                    faktoren_offen.append(float(f.iloc[-1]) * float(k.loc[naechste, "open"]) / float(vortag))
                else:
                    faktoren_offen.append(float(f.iloc[-1]))
        mittel = pd.concat(faktoren, axis=1).mean(axis=1)
        werte.loc[tage] = v * mittel
        statistik.append({"stichtag": d, "ausfuehrung": e, "titel": len(faktoren), "ohne_eroeffnungskurs": ohne_kurs})
        if naechste is not None:
            v = v * float(np.mean(faktoren_offen))
    return werte.dropna(), pd.DataFrame(statistik)
