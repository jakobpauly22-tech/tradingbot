"""Stopp je Buch (A1, Entscheidungen Jakob 12.11.2026).

Eine unbelegte Abweichung stoppt nur das betroffene Buch; die übrigen Bücher laufen weiter.
- Betroffen von einer Titelabweichung sind die Bücher, die den Titel halten oder eine Order dafür unterwegs haben; hält
  ihn keines, die Bücher einer erkannten Kapitalmaßnahme mit diesem Titel. Sonst (Position ohne Buch): Stopp für alles.
- Kontokasse: Stopp für alles. Ausnahme: Die Differenz passt in Währung und Betrag (± 0,05) zur Barkomponente einer
  erkannten Maßnahme laut Flex-Beleg → nur deren Bücher (betrieb/tageslauf.kassenabgleich).
- Ein gestopptes Buch bekommt keine Vorschläge, ist nicht freigebbar und wird beim Senden übersprungen. Ein gerissener
  Stop im gestoppten Buch wird nur gemeldet („Stop gerissen in gestopptem Buch: <Titel>“).
- Aufhebung automatisch mit Meldung „Stopp aufgehoben“, aber nur wenn die Abweichung durch gebuchte Belege erklärt ist
  und der Abgleich des Buchs sauber ist. Verschwindet die Abweichung ohne Beleg, bleibt das Buch gestoppt, bis Jakob in
  der Oberfläche quittiert (Quittung mit Zeitstempel als Ereignis „stopp_quittiert“ im Journal).
Zustand im Journal unter `_buchstopps` (bleibt über Läufe bestehen).
"""
from __future__ import annotations

from datetime import datetime

from tradingbot.betrieb import kapitalmassnahmen

SCHLUESSEL = "_buchstopps"
KAT_BELEG = "Kapitalmaßnahme erkannt, noch nicht gebucht"
KAT_OHNE = "Abweichung zu IBKR ohne Beleg"
FEHLALARM = "Werte vor Buchung der Maßnahme, ggf. Fehlalarm"


def gestoppt(journal) -> dict[str, dict]:
    """Gestoppte Bücher mit Kategorie, Titeln, Belegen, Details, seit und ggf. `abweichung_weg` (wartet auf Quittung)."""
    return journal.zustand(SCHLUESSEL) or {}


def eintragen(je_buch: dict, buch: str, titel: str, belege, text: str):
    e = je_buch.setdefault(buch, {"titel": set(), "belege": set(), "details": []})
    e["titel"].add(titel)
    e["belege"].update(belege)
    e["details"].append(text)


def zuordnen(journal, buecher: list[str], positionen, offen: list[dict] | None = None) -> tuple[list[str], dict[str, dict]]:
    """Titelabgleich Bücher gegen IBKR: (nicht zuordenbare Abweichungen → Stopp für alles, Abweichungen je Buch)."""
    offen = kapitalmassnahmen.offene(journal) if offen is None else offen
    bestaende = {b: journal.bestand(b) for b in buecher}
    unterwegs = {b: {z["ticker"] for z in journal.unterwegs(b)} for b in buecher}
    soll: dict[str, float] = {}
    for b in buecher:
        for t, s in bestaende[b].items():
            soll[t] = soll.get(t, 0.0) + s
    ist = {p.ticker: p.stueck for p in positionen if abs(p.stueck) > 1e-9}
    nicht_zuordenbar, je_buch = [], {}
    for t in sorted(set(soll) | set(ist)):
        if abs(soll.get(t, 0) - ist.get(t, 0)) <= 1e-6:
            continue
        text = f"{t}: Bücher {soll.get(t, 0):g} Stück, IBKR {ist.get(t, 0):g} Stück"
        belege = [m for m in offen if t in m["titel"]]
        betroffen = [b for b in buecher if abs(bestaende[b].get(t, 0.0)) > 1e-9 or t in unterwegs[b]]
        if not betroffen:
            betroffen = sorted({b for m in belege for b in m["buecher"] if b in buecher})
        if not betroffen:
            nicht_zuordenbar.append(text)
            continue
        for b in betroffen:
            hinweis = " (Order unterwegs für diesen Titel – bitte im Client Portal prüfen)" if t in unterwegs[b] else ""
            eintragen(je_buch, b, t, [m["beleg_id"] for m in belege if b in m["buecher"]], text + hinweis)
    return nicht_zuordenbar, je_buch


def kurz(buch: str, e: dict) -> str:
    """Positivliste für Nachrichten: Buch, Kategorie, Titel – ohne Stück und Beträge."""
    weg = "; Abweichung ohne Beleg verschwunden – Quittung in der Oberfläche nötig" if e.get("abweichung_weg") else ""
    return f"Buch {buch} gestoppt – {e['kategorie']}; betroffen: {', '.join(e['titel'][:10])}{weg}"


def aktualisieren(journal, je_buch: dict[str, dict], jetzt: datetime, *, aufheben: bool = True) -> tuple[list[str], list[str]]:
    """Neue Stopps festhalten, bestehende fortschreiben und – nur nach einem vollständigen Abgleich (`aufheben`) – aufheben.
    Gibt (Protokollzeilen, Sofortmeldungen) zurück."""
    st = gestoppt(journal)
    zeit = jetzt.replace(tzinfo=None).isoformat(timespec="seconds")
    meldungen, sofort = [], []
    for b, e in sorted(je_buch.items()):
        alt = st.get(b)
        belege = sorted(set(alt["belege"] if alt else ()) | e["belege"])
        eintrag = {"seit": alt["seit"] if alt else zeit, "kategorie": KAT_BELEG if belege else KAT_OHNE,
                   "titel": sorted(set(alt["titel"] if alt else ()) | e["titel"]), "belege": belege, "details": e["details"],
                   "abweichung_weg": None}
        st[b] = eintrag
        if alt is None:
            journal.ereignis("buchstopp", f"Buch {b} gestoppt – {eintrag['kategorie']}: " + "; ".join(e["details"]), b)
            sofort.append(kurz(b, eintrag))
        meldungen.append(f"Buch {b} gestoppt ({eintrag['kategorie']}, seit {eintrag['seit'][:16].replace('T', ' ')}): "
                         + "; ".join(e["details"]) + " – keine Vorschläge, nicht freigebbar; die übrigen Bücher laufen weiter")
    if aufheben:
        for b in [b for b in st if b not in je_buch]:
            e = st[b]
            erklaert = bool(e["belege"]) and all(journal.massnahmen("beleg_id=? AND buch=? AND status='gebucht'", (x, b)) for x in e["belege"])
            if erklaert:
                del st[b]
                text = f"Stopp aufgehoben: Buch {b} (Abweichung durch gebuchten Beleg erklärt, Abgleich sauber)"
                journal.ereignis("stopp_aufgehoben", text + ": " + ", ".join(e["belege"]), b)
                meldungen.append(text)
                sofort.append(text)
            else:
                if not e.get("abweichung_weg"):
                    e["abweichung_weg"] = zeit
                    journal.ereignis("buchstopp", f"Buch {b}: Abweichung ohne gebuchten Beleg verschwunden – Stopp bleibt bis zur Quittung", b)
                    sofort.append(kurz(b, e))
                meldungen.append(f"Buch {b} bleibt gestoppt: Abweichung ohne gebuchten Beleg verschwunden – bitte in der Oberfläche "
                                 "prüfen und quittieren")
    journal.zustand_speichern(SCHLUESSEL, st)
    return meldungen, sofort


def quittieren(journal, buch: str, jetzt: datetime | None = None) -> str:
    """Quittung durch Jakob in der Oberfläche; nur wenn die Abweichung verschwunden ist (sonst stoppt der nächste Lauf erneut)."""
    st = gestoppt(journal)
    e = st.get(buch)
    if e is None:
        raise ValueError(f"Buch {buch} ist nicht gestoppt")
    if not e.get("abweichung_weg"):
        raise ValueError(f"Buch {buch}: Abweichung besteht noch – Quittung erst, wenn der Abgleich des Buchs sauber ist")
    jetzt = jetzt or datetime.now()
    del st[buch]
    journal.zustand_speichern(SCHLUESSEL, st)
    text = (f"Stopp {buch} quittiert von Jakob am {jetzt:%d.%m.%Y %H:%M:%S} (gestoppt seit {e['seit'][:16].replace('T', ' ')}, "
            f"{e['kategorie']}; Titel {', '.join(e['titel'])}; Abweichung ohne Beleg verschwunden am {e['abweichung_weg'][:16].replace('T', ' ')})")
    journal.ereignis("stopp_quittiert", text, buch, jetzt=jetzt.replace(tzinfo=None))
    return text


def stop_warnungen(buch: str, vorschlaege, eintrag: dict) -> list[str]:
    """Gerissene Stops im gestoppten Buch (kein Vorschlag, nur Sofortmeldung; Jakob 12.11.2026)."""
    aus = []
    for bv in vorschlaege:
        v = bv.vorschlag
        if v.richtung < 0 and (bv.daten or {}).get("ausstieg") == "stop":
            zusatz = f" – {FEHLALARM}" if v.ticker in eintrag.get("titel", ()) else ""
            aus.append(f"Stop gerissen in gestopptem Buch: {v.ticker} ({buch}){zusatz}")
    return aus
