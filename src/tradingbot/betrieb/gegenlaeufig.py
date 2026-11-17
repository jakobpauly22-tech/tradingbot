"""Gegenläufige Orders im selben Titel aus verschiedenen Büchern (Befund 2 der unabhängigen Prüfung; Plan freigegeben von
Jakob 16.11.2026).

Problem: Die Bücher schlagen unabhängig vor. Kauft das Realbuch SPYI.DE (Limit Vortagesschluss + 2 %) am selben Abend, an dem
„regime“ SPYI.DE verkauft (Limit Vortagesschluss − 2 %), lägen beide Orders in derselben Eröffnungsauktion im selben Konto.
Wie IBKR das behandelt (Ablehnung, Neubepreisung, Ausführung gegeneinander), ist nicht verlässlich belegt; der Bot schließt
den Fall deshalb selbst aus.

Regel (vor dem Senden, über alle Bücher):
1. Liegt im selben Titel schon eine Order eines anderen Buchs in Gegenrichtung (im Journal unterwegs oder bei IBKR offen,
   auch ohne Bot-Kennung), wird die neue Order nicht gesendet: Die bestehende lässt sich nicht zurückholen.
2. Kommen am selben Abend beide Richtungen neu, geht der Verkauf raus (Risiko senken), der Kauf wartet (Jakob 16.11.2026).
„Wartet“: nicht gesendet, laute Meldung und Journal-Ereignis; die Freigabe bleibt bis zu ihrem Ablauf stehen, der
Vorschlag kommt am nächsten Abend von selbst wieder. Gleiche Richtung in mehreren Büchern ist erlaubt. Tausch (fx) ist
nicht betroffen.
"""
from __future__ import annotations

MELDUNG = "WARTET – gegenläufige Order im selben Titel"


def wartende(freigegeben, unterwegs, offene) -> dict[str, str]:
    """Freigegebene Orders, die wegen einer gegenläufigen Order eines anderen Buchs nicht gesendet werden: id → Grund.

    `freigegeben`, `unterwegs`: Journalzeilen (buch, id, ticker, richtung, art); `offene`: (buch, ticker, richtung) der bei
    IBKR offenen Orders (Buch aus der Kennung, leer bei Orders ohne Bot-Kennung)."""
    bestehend = {(z["buch"], z["ticker"], int(z["richtung"])) for z in unterwegs if z["art"] != "fx"}
    bestehend |= {(b, t, int(r)) for b, t, r in offene if b != "fx"}
    warten: dict[str, str] = {}
    neu = [z for z in freigegeben if z["art"] != "fx"]
    for z in neu:
        gegen = sorted(b or "ohne Bot-Kennung" for b, t, r in bestehend if t == z["ticker"] and r == -int(z["richtung"]) and b != z["buch"])
        if gegen:
            warten[z["id"]] = f"{'Kauf' if int(z['richtung']) < 0 else 'Verkauf'} von {', '.join(gegen)} schon unterwegs"
    for z in neu:
        if z["id"] in warten or int(z["richtung"]) < 0:
            continue
        verkaeufe = sorted({v["buch"] for v in neu if v["id"] not in warten and v["ticker"] == z["ticker"] and int(v["richtung"]) < 0
                            and v["buch"] != z["buch"]})
        if verkaeufe:
            warten[z["id"]] = f"Verkauf von {', '.join(verkaeufe)} am selben Abend hat Vorrang"
    return warten


def meldung(z, grund: str) -> str:
    return (f"{z['id']}: {MELDUNG} ({z['buch']} {'KAUF' if int(z['richtung']) > 0 else 'VERKAUF'} {z['ticker']}; {grund}) – "
            "nicht gesendet, der Vorschlag kommt am nächsten Abend wieder")
