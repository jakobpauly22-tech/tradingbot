"""Handelskalender (Xetra, NYSE) und Datenprüfung vor dem Tageslauf (Entscheidung Jakob 02.11.2026).

Letzte abgeschlossene Sitzung: Heute zählt erst, wenn die Börse geschlossen hat (Xetra 17:35 Uhr Frankfurt, NYSE 16:00 Uhr
New York, je plus 15 Minuten, bis Yahoo den Schlusskurs führt); sonst der vorige Handelstag.
Feiertage: Xetra – Neujahr, Karfreitag, Ostermontag, 1. Mai, 24., 25., 26. und 31. Dezember. NYSE – Neujahr, Martin
Luther King (3. Mo Jan), Presidents Day (3. Mo Feb), Karfreitag, Memorial Day (letzter Mo Mai), Juneteenth (ab 2022),
Independence Day, Labor Day (1. Mo Sep), Thanksgiving (4. Do Nov), Weihnachten; Samstag → Freitag davor, Sonntag →
Montag danach (Neujahr auf Samstag wird nicht vorgezogen). Sonderschließungen (z.B. Trauertage) sind nicht enthalten;
die Datenprüfung meldet dann einen fehlenden Kurs, der Tag bleibt ohne Vorschläge.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

BOERSEN = {
    "xetra": {"zone": ZoneInfo("Europe/Berlin"), "schluss": time(17, 50)},
    "nyse": {"zone": ZoneInfo("America/New_York"), "schluss": time(16, 15)},
}


def ostersonntag(jahr: int) -> date:
    """Gaußsche Osterformel (anonymer gregorianischer Algorithmus)."""
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    monat = (h + l_ - 7 * m + 114) // 31
    tag = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(jahr, monat, tag)


def _nter_wochentag(jahr, monat, wochentag, n):
    d = date(jahr, monat, 1)
    d += timedelta(days=(wochentag - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _letzter_wochentag(jahr, monat, wochentag):
    d = (date(jahr, monat + 1, 1) if monat < 12 else date(jahr + 1, 1, 1)) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - wochentag) % 7)


def _beobachtet(d: date, neujahr: bool = False) -> date | None:
    if d.weekday() == 5:
        return None if neujahr else d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def feiertage(boerse: str, jahr: int) -> set[date]:
    ostern = ostersonntag(jahr)
    if boerse == "xetra":
        return {date(jahr, 1, 1), ostern - timedelta(days=2), ostern + timedelta(days=1), date(jahr, 5, 1),
                date(jahr, 12, 24), date(jahr, 12, 25), date(jahr, 12, 26), date(jahr, 12, 31)}
    if boerse == "nyse":
        tage = [_beobachtet(date(jahr, 1, 1), neujahr=True), _nter_wochentag(jahr, 1, 0, 3), _nter_wochentag(jahr, 2, 0, 3),
                ostern - timedelta(days=2), _letzter_wochentag(jahr, 5, 0), _beobachtet(date(jahr, 7, 4)),
                _nter_wochentag(jahr, 9, 0, 1), _nter_wochentag(jahr, 11, 3, 4), _beobachtet(date(jahr, 12, 25))]
        if jahr >= 2022:
            tage.append(_beobachtet(date(jahr, 6, 19)))
        return {d for d in tage if d is not None}
    raise ValueError(f"unbekannte Börse {boerse}")


def ist_handelstag(boerse: str, d: date) -> bool:
    return d.weekday() < 5 and d not in feiertage(boerse, d.year)


def letzte_abgeschlossene_sitzung(boerse: str, jetzt: datetime) -> date:
    b = BOERSEN[boerse]
    lokal = jetzt.astimezone(b["zone"])
    d = lokal.date()
    if not (ist_handelstag(boerse, d) and lokal.time() >= b["schluss"]):
        d -= timedelta(days=1)
        while not ist_handelstag(boerse, d):
            d -= timedelta(days=1)
    return d


def boerse_von(ticker: str) -> str:
    return "xetra" if ticker.endswith(".DE") else "nyse"


def pruefe_tageskurse(kurse: pd.DataFrame, erwartet: date, max_sprung: float) -> list[str]:
    """Befunde für eine Kursreihe: Schlusskurs nicht vom erwarteten Handelstag; Tagesänderung des letzten Tags über
    `max_sprung` ohne Kapitalmaßnahme (Split oder Ausschüttung an diesem Tag). Leere Liste = in Ordnung."""
    if kurse is None or kurse.empty:
        return ["keine Kurse"]
    befunde = []
    letzter = pd.Timestamp(kurse.index[-1]).date()
    if letzter != erwartet:
        befunde.append(f"letzter Schlusskurs vom {letzter:%d.%m.%Y}, erwartet {erwartet:%d.%m.%Y}")
    if len(kurse) >= 2:
        z, vor = kurse.iloc[-1], kurse.iloc[-2]
        aenderung = z["close"] / vor["close"] - 1 if vor["close"] > 0 else float("inf")
        massnahme = (z.get("split", 0) or 0) > 0 or (z.get("dividende", 0) or 0) > 0
        if abs(aenderung) > max_sprung and not massnahme:
            befunde.append(f"Tagesänderung {aenderung:+.1%} am {letzter:%d.%m.%Y} ohne Kapitalmaßnahme")
    return befunde
