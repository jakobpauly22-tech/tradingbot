"""Ausführungen außerhalb des API-Zeitfensters (Jakob 09.11.2026, Anlass: verpasste Abende 04.–08.11.2026).

Problem: reqExecutions liefert über das Gateway nur die Ausführungen des laufenden Tages. Läuft an einem Abend kein
Tageslauf, sieht der nächste Lauf die Ausführung nicht mehr. Ohne diese Prüfung würde die Order als „verfallen“ markiert
(und später als Nachkauf wieder vorgeschlagen), und die Kassenbasis würde den Kauf verschlucken.

Festgelegter Weg (je Order „unterwegs“, deren Handelstag vorbei ist und die bei IBKR nicht mehr offen ist):
1. Erkennen: IBKR-Position je Ticker minus Summe der Bücher. Abweichung 0 → die Order ist verfallen. Abweichung ≠ 0 →
   Verdacht auf eine Ausführung außerhalb des API-Zeitfensters. Tausch (EUR.USD): USD-Kasse gegen Kassenbasis plus Bücher.
2. Beleg suchen, in dieser Reihenfolge:
   a) IBKR-Flex-Abfrage (Trades; FLEX_TOKEN und FLEX_QUERY_ID in .env): Ausführungs-ID, Preis, Gebühr, Zeit und Platz wie
      von IBKR gemeldet. Vollwertiger Beleg.
   b) Position mit Einstand (nur Käufe, nur wenn die Order allein die Position erklärt: kein Bestand in den Büchern, genau
      eine Order unterwegs, Position = Stückzahl der Order). IBKR führt den Einstand inklusive Gebühr, also
      Preis = Einstand − Gebühr/Stück. Gebühr je Markt und Währung (config/betrieb.yaml `nachtrag.gebuehr`, Jakob 09.11.2026):
      Xetra EUR 3,00 € je Order (Paper-Festpreis); US-Aktien IBKR Pro Fixed: 0,005 USD je Aktie, mindestens 1,00 USD,
      höchstens 1 % des Orderwerts. Plausibilität: Preis höchstens Limit und innerhalb von Tief und Hoch des Ausführungstags
      (Yahoo). Abgeleiteter Beleg: Gebühr als „angenommen“ markiert (`ausfuehrungen.gebuehr_angenommen`), beim nächsten
      Flex-Abruf abgeglichen (`angenommene_abgleichen`); Uhrzeit und Platz sind unbekannt und so im Journal vermerkt.
3. Buchen über denselben Weg wie API-Ausführungen (`einlesen`), mit Quelle je Ausführung (`ausfuehrungen.quelle`) und
   Ereignis „nachtrag“ im Journal. Jede Nachbuchung steht im Protokoll des Laufs.
4. Bleibt ein Verdacht ohne Beleg, stoppt der Lauf (keine Vorschläge, Status bleibt „gesendet“).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from tradingbot.betrieb.kalender import boerse_von, ist_handelstag

QUELLE_FLEX = "IBKR Flex-Abfrage"
QUELLE_POSITION = "IBKR Position (Einstand)"


@dataclass
class Klaerung:
    verfallen: list = field(default_factory=list)        # Journalzeilen
    verdacht: list = field(default_factory=list)         # Journalzeilen: Ausführung außerhalb des API-Zeitfensters vermutet
    gebucht: list[str] = field(default_factory=list)     # Meldungen der Nachbuchungen
    ohne_beleg: list[str] = field(default_factory=list)  # Meldungen: Verdacht ohne Beleg → Stopp
    hinweise: list[str] = field(default_factory=list)


def naechste_sitzung(boerse: str, d) -> date:
    """Erster Handelstag nach `d` (Orders werden nach Börsenschluss gesendet und gelten für den nächsten Handelstag)."""
    d = pd.Timestamp(d).date() + timedelta(days=1)
    while not ist_handelstag(boerse, d):
        d += timedelta(days=1)
    return d


def _ref(z) -> str:
    return f"{z['buch']}:{z['id']}"


def klaeren(journal, buecher: list[str], offene_refs: set[str], positionen, letzte_sitzung, *, kasse_ibkr: dict | None = None,
            toleranz: float = 0.05) -> Klaerung:
    """Schritt 1: Orders unterwegs, deren Handelstag vorbei ist und die nicht mehr offen sind → verfallen oder Verdacht."""
    k = Klaerung()
    vorbei = [z for z in journal.unterwegs() if pd.Timestamp(z["signaltag"]) < pd.Timestamp(letzte_sitzung) and _ref(z) not in offene_refs]
    if not vorbei:
        return k
    soll: dict[str, float] = {}
    for b in buecher:
        for t, s in journal.bestand(b).items():
            soll[t] = soll.get(t, 0.0) + s
    ist = {p.ticker: p.stueck for p in positionen}
    usd_abw = None
    if kasse_ibkr is not None:
        basis = journal.zustand("_konto").get("kassenbasis")
        bot_usd = sum(journal.kasse_je_waehrung(b).get("USD", 0.0) for b in buecher)
        usd_abw = kasse_ibkr.get("USD", 0.0) - ((basis or {}).get("USD", 0.0) + bot_usd)
    for z in vorbei:
        if z["art"] == "fx":
            if usd_abw is None or abs(usd_abw) <= toleranz:
                k.verfallen.append(z)
            else:
                k.verdacht.append(z)
        elif abs(ist.get(z["ticker"], 0.0) - soll.get(z["ticker"], 0.0)) > 1e-9:
            k.verdacht.append(z)
        else:
            k.verfallen.append(z)
    return k


# --- Belege ------------------------------------------------------------------------------------------------------------
def flex_aus_env():
    """Lädt die Trades der Flex-Abfrage aus .env (FLEX_TOKEN, FLEX_QUERY_ID; Jakob 09.11.2026); None, wenn nicht eingerichtet."""
    token, abfrage = os.getenv("FLEX_TOKEN"), os.getenv("FLEX_QUERY_ID")
    if not token or not abfrage:
        return None

    def laden() -> tuple[list[dict], str]:
        from ib_async import FlexReport

        bericht = FlexReport(token=token, queryId=abfrage)
        kopf = next(iter(bericht.root.iter("FlexStatement")), None)
        stand = (kopf.attrib.get("whenGenerated") if kopf is not None else "") or "unbekannt"
        return [dict(t.attrib) for t in bericht.root.iter("Trade")], f"{QUELLE_FLEX} {abfrage}, erstellt {stand}"
    return laden


def _flex_zeit(text: str) -> str:
    """Flex-Zeitstempel „20261104;090012“ oder „2026-11-04;09:00:12“ → ISO (Zeitzone wie in der Abfrage eingestellt)."""
    datum, _, uhr = str(text).partition(";")
    datum = datum.replace("-", "")
    uhr = uhr.replace(":", "") or "000000"
    return f"{datum[:4]}-{datum[4:6]}-{datum[6:8]}T{uhr[:2]}:{uhr[2:4]}:{uhr[4:6]}"


def flex_ausfuehrungen(zeilen: list[dict], refs: set[str], ticker_je_conid: dict[int, str] | None = None) -> list[dict]:
    """Flex-Trades (Attribute als Text) → Ausführungen im Format von `broker.ausfuehrungen()`, nur für `refs`."""
    ticker_je_conid = ticker_je_conid or {}
    aus = []
    for t in zeilen:
        ref = t.get("orderReference") or ""
        if ref not in refs:
            continue
        menge = abs(float(t["quantity"]))
        gebuehr = -float(t.get("ibCommission") or 0.0)            # Flex meldet die Gebühr negativ
        gw = t.get("ibCommissionCurrency") or t.get("currency")
        zeit = _flex_zeit(t.get("dateTime") or t.get("tradeDate", ""))
        if t.get("assetCategory") == "CASH":
            von, _, nach = str(t.get("symbol", "EUR.USD")).partition(".")
            aus.append({"art": "fx", "exec_id": t["ibExecID"], "order_ref": ref, "von": von, "nach": nach, "betrag_von": menge,
                        "betrag_nach": menge * float(t["tradePrice"]), "kurs": float(t["tradePrice"]), "gebuehr": gebuehr,
                        "gebuehr_waehrung": gw, "zeit": zeit})
            continue
        cid = int(float(t.get("conid") or 0))
        ticker = ticker_je_conid.get(cid) or (f"{t['symbol']}.DE" if t.get("currency") == "EUR" else str(t["symbol"]).replace(" ", "-"))
        aus.append({"exec_id": t["ibExecID"], "order_ref": ref, "ticker": ticker, "boerse": t.get("exchange"),
                    "richtung": 1 if str(t.get("buySell", "")).upper().startswith("BUY") else -1, "stueck": menge,
                    "preis": float(t["tradePrice"]), "waehrung": t.get("currency", "EUR"), "gebuehr": gebuehr, "gebuehr_waehrung": gw,
                    "zeit": zeit})
    return aus


def nachtrag_gebuehr(plan: dict, ticker: str, stueck: float, einstand: float) -> tuple[float, str]:
    """Angenommene Gebühr für den Weg über die Position (Jakob 09.11.2026), in der Handelswährung.

    Xetra (EUR): fester Betrag je Order. US-Aktien (IBKR Pro Fixed): min(max(0,005 · Stück; 1,00); 1 % · Stück · Preis).
    Da der Einstand die Gebühr enthält (Einstand · Stück = Stück · Preis + Gebühr), wird der Preis mit der Gebühr aus dem
    Einstand geschätzt und einmal nachgerechnet. Quelle: config/betrieb.yaml `nachtrag.gebuehr`."""
    if ticker.endswith(".DE"):
        g = float(plan["xetra_eur"]["je_order"])
        return g, f"Xetra-Festpreis {g:.2f} EUR je Order"
    us = plan["us_usd"]
    preis = einstand
    for _ in range(2):
        g = min(max(float(us["je_aktie"]) * stueck, float(us["minimum"])), float(us["maximum_anteil"]) * stueck * preis)
        preis = (einstand * stueck - g) / stueck
    return g, (f"US-Festpreis {us['je_aktie']} USD × {stueck:g} Stück, mindestens {float(us['minimum']):.2f}, höchstens "
               f"{float(us['maximum_anteil']):.0%} des Orderwerts → {g:.2f} USD")


def position_ausfuehrung(z, positionen, soll: dict[str, float], verdacht: list, plan: dict, kurse_laden) -> tuple[dict | None, str]:
    """Beleg aus Position mit Einstand (Weg 2b). Gibt (Ausführung, Begründung) zurück; None = kein Beleg."""
    t = z["ticker"]
    if z["art"] == "fx" or z["richtung"] < 0:
        return None, "nur Käufe lassen sich aus dem Einstand belegen"
    if sum(1 for v in verdacht if v["ticker"] == t) != 1:
        return None, "mehrere Orders unterwegs für denselben Titel"
    if abs(soll.get(t, 0.0)) > 1e-9:
        return None, f"Bücher halten schon {soll[t]:g} Stück (Einstand gemischt)"
    pos = next((p for p in positionen if p.ticker == t), None)
    if pos is None or abs(pos.stueck - z["stueck"]) > 1e-9:
        return None, f"Position {0 if pos is None else pos.stueck:g} Stück ≠ Order {z['stueck']} Stück (Teilausführung?)"
    gebuehr, regel = nachtrag_gebuehr(plan, t, pos.stueck, pos.einstand)
    preis = (pos.einstand * pos.stueck - gebuehr) / pos.stueck
    tag = naechste_sitzung(boerse_von(t), z["signaltag"])
    if z["limit_preis"] is not None and preis > z["limit_preis"] + 1e-6:
        return None, f"abgeleiteter Preis {preis:.4f} über dem Limit {z['limit_preis']:.4f}"
    try:
        k = kurse_laden(t, tag, "etf" if t.endswith(".DE") else "aktie_usd")
        k = k[k.index.normalize() == pd.Timestamp(tag)]
    except Exception as f:  # noqa: BLE001
        return None, f"Tageskurse {tag:%d.%m.%Y} nicht verfügbar ({type(f).__name__})"
    if not len(k):
        return None, f"kein Tageskurs am {tag:%d.%m.%Y} zur Plausibilisierung"
    tief, hoch = float(k["low"].iloc[-1]), float(k["high"].iloc[-1])
    if not tief * 0.995 <= preis <= hoch * 1.005:
        return None, f"abgeleiteter Preis {preis:.4f} außerhalb Tief/Hoch {tief:.4f}–{hoch:.4f} am {tag:%d.%m.%Y}"
    a = {"exec_id": f"nachtrag-position:{_ref(z)}", "order_ref": _ref(z), "ticker": t, "boerse": None, "richtung": 1,
         "stueck": float(z["stueck"]), "preis": preis, "waehrung": z["waehrung"], "gebuehr": gebuehr, "gebuehr_waehrung": z["waehrung"],
         "zeit": tag.isoformat()}
    return a, (f"Einstand {pos.einstand:.6f} {z['waehrung']} × {pos.stueck:g} (inkl. Gebühr) − Gebühr {gebuehr:.2f} {z['waehrung']} "
               f"(angenommen: {regel}) → Preis {preis:.4f}; Tief/Hoch {tief:.4f}–{hoch:.4f} am {tag:%d.%m.%Y}; Uhrzeit und Platz unbekannt")


class _Liste:
    """Belege als Pseudo-Broker, damit sie über `einlesen` wie API-Ausführungen gebucht werden."""
    def __init__(self, a):
        self.a = a

    def ausfuehrungen(self):
        return self.a


def nachtragen(journal, buecher: list[str], k: Klaerung, positionen, fx, *, kosten, kurse_laden, flex=None,
               gebuehrenplan: dict | None = None, eroeffnung=None) -> Klaerung:
    """Schritte 2 und 3 für alle Verdachtsfälle in `k`; füllt `k.gebucht` und `k.ohne_beleg`."""
    from tradingbot.betrieb.tageslauf import einlesen
    from tradingbot.broker.ibkr import _ticker_je_conid

    if not k.verdacht:
        return k
    refs = {_ref(z) for z in k.verdacht}
    belege: dict[str, tuple[list[dict], str]] = {}
    if flex is not None:
        try:
            zeilen, quelle = flex()
            for a in flex_ausfuehrungen(zeilen, refs, _ticker_je_conid()):
                belege.setdefault(a["order_ref"], ([], quelle))[0].append(a)
        except Exception as f:  # noqa: BLE001
            k.hinweise.append(f"Flex-Abfrage fehlgeschlagen ({type(f).__name__}: {f})")
    else:
        k.hinweise.append("Flex-Abfrage nicht eingerichtet (FLEX_TOKEN, FLEX_QUERY_ID in .env)")
    soll: dict[str, float] = {}
    for b in buecher:
        for t, s in journal.bestand(b).items():
            soll[t] = soll.get(t, 0.0) + s
    for z in k.verdacht:
        r = _ref(z)
        if r in belege:
            menge = sum(a["betrag_von"] if a.get("art") == "fx" else a["stueck"] for a in belege[r][0])
            if abs(menge - z["stueck"]) > 1e-6 and z["art"] != "fx":
                k.ohne_beleg.append(f"{r}: Flex meldet {menge:g} von {z['stueck']} Stück (Teilausführung) – bitte prüfen")
                del belege[r]
            continue
        if not gebuehrenplan:
            k.ohne_beleg.append(f"{r}: kein Beleg (Flex ohne Treffer, Gebühr für den Weg über die Position nicht festgelegt)")
            continue
        a, grund = position_ausfuehrung(z, positionen, soll, k.verdacht, gebuehrenplan, kurse_laden)
        if a is None:
            k.ohne_beleg.append(f"{r}: kein Beleg – {grund}")
        else:
            belege[r] = ([a], f"{QUELLE_POSITION}: {grund}")
    if k.ohne_beleg:                                   # alles oder nichts: bei offenem Fall wird nichts gebucht
        return k
    for r, (ausf, quelle) in belege.items():
        zeilen: list[str] = []
        einlesen(journal, _Liste(ausf), fx, kosten=kosten, protokoll=zeilen, eroeffnung=eroeffnung)
        for a in ausf:
            journal.quelle_setzen(a["exec_id"], quelle, gebuehr_angenommen=quelle.startswith(QUELLE_POSITION))
        buch = r.split(":")[0]
        text = f"Nachtrag {r} (Ausführung außerhalb des API-Zeitfensters), Quelle: {quelle}"
        journal.ereignis("nachtrag", text + (" | " + " | ".join(zeilen) if zeilen else ""), buch)
        k.gebucht.append(text)
        k.gebucht += [f"  {x}" for x in zeilen]
    return k


def angenommene_abgleichen(journal, flex, fx, *, kosten, eroeffnung=None) -> tuple[list[str], list[str]]:
    """Nachgetragene Ausführungen mit angenommener Gebühr gegen die Flex-Abfrage abgleichen (Jakob 09.11.2026).

    Liefert Flex alle Ausführungen einer Order (gleiche Stückzahl), ersetzt das Journal die abgeleitete Zeile durch die
    Flex-Ausführungen (echte Ausführungs-ID, Preis, Gebühr, Zeit, Platz) und protokolliert alt und neu (Ereignis
    „nachtrag_abgleich“). Weicht die Stückzahl ab, bleibt die Zeile stehen und der Lauf stoppt. Orders, die Flex (noch) nicht
    enthält, bleiben „angenommen“. Gibt (Meldungen, Stoppgründe) zurück."""
    from tradingbot.betrieb.tageslauf import einlesen
    from tradingbot.broker.ibkr import _ticker_je_conid

    zeilen_j = journal.angenommene()
    if not zeilen_j or flex is None:
        return [], []
    meldungen, stopp = [], []
    try:
        zeilen, quelle = flex()
    except Exception as f:  # noqa: BLE001
        return [f"Abgleich angenommener Gebühren: Flex-Abfrage fehlgeschlagen ({type(f).__name__}: {f}), bleibt angenommen"], []
    refs = {z["order_ref"] for z in zeilen_j}
    flex_je_ref: dict[str, list[dict]] = {}
    for a in flex_ausfuehrungen(zeilen, refs, _ticker_je_conid()):
        flex_je_ref.setdefault(a["order_ref"], []).append(a)
    for r in sorted(refs):
        alt = [z for z in zeilen_j if z["order_ref"] == r]
        neu = flex_je_ref.get(r)
        if not neu:
            meldungen.append(f"Abgleich angenommener Gebühren: {r} nicht in der Flex-Abfrage ({quelle}) – bleibt angenommen")
            continue
        s_alt, s_neu = sum(z["stueck"] for z in alt), sum(a["stueck"] for a in neu)
        if abs(s_alt - s_neu) > 1e-9:
            stopp.append(f"{r}: Flex meldet {s_neu:g} Stück, Journal (Nachtrag) {s_alt:g} – bitte prüfen")
            continue
        text_alt = "; ".join(f"{z['stueck']:g} × {z['preis']:.4f}, Gebühr {z['gebuehr']:.2f} {z['gebuehr_waehrung']} (angenommen)" for z in alt)
        journal.ausfuehrungen_entfernen([z["exec_id"] for z in alt])
        protokoll: list[str] = []
        einlesen(journal, _Liste(neu), fx, kosten=kosten, protokoll=protokoll, eroeffnung=eroeffnung)
        for a in neu:
            journal.quelle_setzen(a["exec_id"], quelle)
        text_neu = "; ".join(f"{a['stueck']:g} × {a['preis']:.4f}, Gebühr {a['gebuehr']:.2f} {a['gebuehr_waehrung']}" for a in neu)
        text = f"Abgleich {r} mit {quelle}: vorher {text_alt} → jetzt {text_neu}"
        journal.ereignis("nachtrag_abgleich", text, r.split(":")[0])
        meldungen.append(text)
    return meldungen, stopp
