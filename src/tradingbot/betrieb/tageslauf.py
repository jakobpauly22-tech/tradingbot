"""Tageslauf und Freigabe des Paper Tradings (Phase 2, 6c; Entscheidungen Jakob 02.11.2026).

Tageslauf (abends nach Börsenschluss, im Betriebsmodus):
1. Gateway verbunden? Dann Ausführungen des Tages einlesen (orderRef → Buch), verfallene Orders markieren und den
   Bestand abgleichen: Summe der Bücher je Ticker = IBKR-Position. Abweichung → Stopp mit Meldung, keine Vorschläge.
   Ohne Gateway: Vorschläge aus dem Journalstand, Hinweis; eingelesen und abgeglichen wird dann vor dem Senden.
2. Datenprüfung je Buch (Schluss vom letzten Handelstag der jeweiligen Börse, Sprünge > 15 % ohne Kapitalmaßnahme);
   Befund → an diesem Tag keine Vorschläge für dieses Buch.
3. Vorschläge je Buch (betrieb/buecher.py), Prüfung durch den Risk-Manager, Speichern im Journal (freigebbar bis
   24 Uhr), Buchwerte und Strategiezustände speichern, Journal sichern (JOURNAL_BACKUP_DIR).

Freigabe und Senden (18–24 Uhr): Freigabe im Realbuch einzeln, in Skalierungsbüchern als Sammelfreigabe. Vor dem
Senden: Gateway verbunden? (sonst sauber abbrechen, Freigaben bleiben bis 24 Uhr), Ausführungen einlesen, Abgleich,
zweite Prüfung durch den Risk-Manager, dann Senden über die Riegel des Broker-Adapters.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

import pandas as pd

from tradingbot.betrieb.buecher import BuchVorschlag, fundamentalbuch, quartalsstichtag, realbuch, tausch_vorschlag, technikbuch
from tradingbot.betrieb.kalender import letzte_abgeschlossene_sitzung, pruefe_tageskurse
from tradingbot.broker.basis import Auftrag, SendenGesperrt
from tradingbot.risiko.manager import Kontext, OrderVorschlag, RiskManager, Urteil

FREIGABE_VON = time(18, 0)


@dataclass
class Laufergebnis:
    jetzt: datetime
    vorschlaege: list[tuple[BuchVorschlag, Urteil]] = field(default_factory=list)
    befunde: dict[str, list[str]] = field(default_factory=dict)       # Buch → Datenbefunde (Buch ohne Vorschläge)
    meldungen: list[str] = field(default_factory=list)
    gestoppt: str | None = None


# --- Ausführungen, Verfall, Abgleich ------------------------------------------------------------------------------
def einlesen(journal, broker, fx: dict[str, float]) -> list[str]:
    """Ausführungen der Bot-Orders ins Journal; gibt die Bücher mit neuen Ausführungen zurück."""
    neu = []
    for a in broker.ausfuehrungen():
        fg = fx.get(a["gebuehr_waehrung"], 1.0) if a["gebuehr_waehrung"] != "EUR" else 1.0
        if a.get("art") == "fx":
            if journal.tausch(a["exec_id"], a["order_ref"], a["von"], a["nach"], a["betrag_von"], a["betrag_nach"], a["gebuehr"] / fg, a["zeit"]):
                neu.append(a["order_ref"].split(":")[0])
            continue
        f = fx.get(a["waehrung"], 1.0) if a["waehrung"] != "EUR" else 1.0
        if journal.ausfuehrung(a["exec_id"], a["order_ref"], a["ticker"], a["richtung"], a["stueck"], a["preis"] / f, a["gebuehr"] / fg, a["zeit"],
                               waehrung=a["waehrung"], preis=a["preis"], gebuehr=a["gebuehr"], gebuehr_waehrung=a["gebuehr_waehrung"]):
            neu.append(a["order_ref"].split(":")[0])
    return sorted(set(neu))


def verfallene_markieren(journal, offene_refs: set[str], letzte_sitzung) -> int:
    """Gesendete Orders, deren Handelstag vorbei ist, ohne Ausführung und nicht mehr offen → verfallen."""
    n = 0
    for z in journal.vorschlaege(status=("gesendet",)):
        if pd.Timestamp(z["signaltag"]) < pd.Timestamp(letzte_sitzung) and f"{z['buch']}:{z['id']}" not in offene_refs:
            journal.status_setzen(z["id"], "verfallen")
            journal.ereignis("verfallen", f"Order {z['id']} nicht ausgeführt, verfallen", z["buch"])
            n += 1
    return n


def abgleich(journal, buecher: list[str], positionen) -> list[str]:
    """Summe der Bücher je Ticker gegen die IBKR-Positionen; leere Liste = in Ordnung."""
    soll: dict[str, float] = {}
    for b in buecher:
        for t, s in journal.bestand(b).items():
            soll[t] = soll.get(t, 0.0) + s
    ist = {p.ticker: p.stueck for p in positionen if abs(p.stueck) > 1e-9}
    return [f"{t}: Bücher {soll.get(t, 0):g} Stück, IBKR {ist.get(t, 0):g} Stück" for t in sorted(set(soll) | set(ist))
            if abs(soll.get(t, 0) - ist.get(t, 0)) > 1e-6]


# --- Risiko-Kontext je Buch -----------------------------------------------------------------------------------------
def kontext(journal, buch: str, tag, wert: float, *, offene=(), fundamental=None) -> Kontext:
    werte = journal.buchwerte(buch)
    werte = pd.concat([werte, pd.Series({pd.Timestamp(tag): wert})]).groupby(level=0).last().sort_index()
    hoch = float(werte.max()) if len(werte) else wert
    monatsende = werte[werte.index < pd.Timestamp(tag).to_period("M").start_time]
    monat = wert / float(monatsende.iloc[-1]) - 1 if len(monatsende) else 0.0
    return Kontext(buch=buch, kasse=journal.kasse(buch), wert=wert, bestand={t: int(round(s)) for t, s in journal.bestand(buch).items()},
                   kasse_je_waehrung=journal.kasse_je_waehrung(buch),
                   monatsrendite=monat, vom_hoch=wert / hoch - 1 if hoch > 0 else 0.0, orders_heute=journal.orders_heute(buch, tag),
                   gesendete_ids={r.split(":", 1)[1] for r in journal.gesendete_refs()}, offene_orders=list(offene), fundamental=fundamental or {})


# --- Tageslauf --------------------------------------------------------------------------------------------------------
def tageslauf(jetzt: datetime, journal, *, broker=None, kurse_laden=None, fundamental_bewertung=None, risk: RiskManager | None = None,
              konfig: dict | None = None, sichern: bool = True) -> Laufergebnis:
    """Ein Tageslauf. `kurse_laden(ticker, bis, art) -> DataFrame` (EUR-Kurse) und `fundamental_bewertung(tag)` sind
    austauschbar (Tests); Standard sind Yahoo-Kurse und engines/fundamental/aktuell.py."""
    from tradingbot.konfiguration import lade_konfiguration

    konfig = konfig or {n: lade_konfiguration(n) for n in ("betrieb", "technik", "fundamental", "backtest")}
    b, kt, kf = konfig["betrieb"], konfig["technik"], konfig["fundamental"]
    risk = risk or RiskManager.aus_konfig()
    kurse_laden = kurse_laden or _yahoo_kurse
    erg = Laufergebnis(jetzt)
    xetra, nyse = letzte_abgeschlossene_sitzung("xetra", jetzt), letzte_abgeschlossene_sitzung("nyse", jetzt)
    tag = pd.Timestamp(xetra)
    aufschlag = float(b["orders"]["kauf"]["aufschlag_vortagesschluss"])
    max_sprung = float(b["datenpruefung"]["max_tagessprung"])
    for name, bk in b["buecher"].items():
        journal.buch_anlegen(name, float(bk["budget_eur"]))
    journal.abgelaufene_markieren(jetzt)
    eurusd = float(kurse_laden("EURUSD=X", tag.date(), "fx")["close"].iloc[-1])
    fx = {"USD": eurusd}

    offene = []
    if broker is not None:
        try:
            if not broker.verbunden():
                broker.verbinden()
            neu = einlesen(journal, broker, fx)
            if neu:
                erg.meldungen.append(f"Neue Ausführungen eingelesen: {', '.join(neu)}")
            offen_liste = broker.offene_orders()
            offene = [(o.order_ref.split(":")[0], o.ticker, o.richtung) for o in offen_liste]
            n = verfallene_markieren(journal, {o.order_ref for o in offen_liste}, xetra)
            if n:
                erg.meldungen.append(f"{n} nicht ausgeführte Order(s) verfallen")
            diff = abgleich(journal, list(b["buecher"]), broker.positionen())
            if diff:
                erg.gestoppt = "Abgleich mit IBKR weicht ab – Tageslauf gestoppt: " + "; ".join(diff)
                journal.ereignis("abgleich", erg.gestoppt)
                return erg
            journal.ereignis("abgleich", "Bestände aller Bücher stimmen mit IBKR überein")
        except Exception as f:  # noqa: BLE001 – Gateway nicht erreichbar: Vorschläge trotzdem, Abgleich vor dem Senden
            erg.meldungen.append(f"Gateway nicht verbunden ({type(f).__name__}): Ausführungen nicht eingelesen; Abgleich vor dem Senden")
    else:
        erg.meldungen.append("ohne Gateway: Ausführungen nicht eingelesen; Abgleich vor dem Senden")

    def gebuehr_fuer(plan, f=1.0):
        return lambda n, wert_eur: risk.kosten.gebuehren_eur(plan, n, wert_eur, f)

    roh: list[BuchVorschlag] = []
    fundamental_gruende: dict[str, list[str]] = {}

    def pruefen(buch, kurse: dict[str, pd.DataFrame], erwartet) -> bool:
        befunde = [f"{t}: {x}" for t, k in kurse.items() for x in pruefe_tageskurse(k, erwartet if not isinstance(erwartet, dict) else erwartet[t], max_sprung)]
        if befunde:
            erg.befunde[buch] = befunde
            journal.ereignis("datenpruefung", "; ".join(befunde[:10]), buch)
        return not befunde

    # Realbuch
    etf = b["core"]["etf"]
    k_real = {etf: kurse_laden(etf, tag.date(), "etf")}
    werte_buch = {}
    if pruefen("real", k_real, xetra):
        kurs = float(k_real[etf]["close"].iloc[-1])
        werte_buch["real"] = journal.kasse("real") + sum(s * kurs for t, s in journal.bestand("real").items())
        roh += realbuch(tag, etf, kurs, journal.kasse("real"), aufschlag, gebuehr_fuer("EUR"))

    # Technik-Bücher
    etfs = kt["universum"]["etfs"]
    k_tech = {e["ticker"]: kurse_laden(e["ticker"], tag.date(), "etf") for e in etfs}
    waehrung = {e["ticker"]: e.get("handelswaehrung", "EUR") for e in etfs}
    orderkurs = {t: float(k.attrs.get("orderkurs", k["close"].iloc[-1])) for t, k in k_tech.items()}
    technik_ok = pruefen("technik", k_tech, xetra)
    for buch in ("crossover", "momentum"):
        if buch not in b["buecher"]:
            continue
        if not technik_ok:
            erg.befunde[buch] = erg.befunde.get("technik", [])
            continue
        bestand = journal.bestand(buch)
        werte_buch[buch] = journal.kasse(buch) + sum(s * float(k_tech[t]["close"].iloc[-1]) for t, s in bestand.items())
        v, z = technikbuch(buch, buch, tag, k_tech, orderkurs, waehrung, fx, journal.kasse(buch), bestand, journal.zustand(buch), kt,
                           aufschlag, gebuehr_fuer("EUR"))
        journal.zustand_speichern(buch, z)
        roh += v
    erg.befunde.pop("technik", None)

    # Fundamental-Bücher (Bewertung nur, wenn ein Buch sie heute braucht)
    fb = {n: v for n, v in (("fundamental_a", "A"), ("fundamental_b", "B")) if n in b["buecher"]}
    braucht = [n for n in fb if not journal.bestand(n) or quartalsstichtag(nyse)]
    kurse_usd: dict[str, float] = {}
    for n in fb:
        bestand = journal.bestand(n)
        if bestand and n not in braucht:
            k_b = {t: kurse_laden(t, nyse, "aktie_usd") for t in bestand}
            kurse_usd.update({t: float(k["close"].iloc[-1]) for t, k in k_b.items()})
            werte_buch[n] = journal.kasse(n) + sum(s * kurse_usd[t] / eurusd for t, s in bestand.items())
    if braucht:
        bewertung, _, meldungen = (fundamental_bewertung or _fundamental_bewertung)(pd.Timestamp(nyse))
        erg.meldungen += meldungen[:5]
        from tradingbot.engines.fundamental.aktuell import rangliste

        fundamental_gruende = {r.symbol: list(r.gruende) for r in bewertung.itertuples() if r.symbol}
        for n in braucht:
            rl = rangliste(bewertung, fb[n])
            bestand = journal.bestand(n)
            preise = {r.symbol: float(r.schluss_usd) for r in bewertung.itertuples() if r.symbol}
            preise.update({t: float(kurse_laden(t, nyse, "aktie_usd")["close"].iloc[-1]) for t in bestand if t not in preise})
            v, z, grund = fundamentalbuch(n, fb[n], pd.Timestamp(nyse), rl, preise, eurusd, journal.kasse(n), bestand, journal.zustand(n), kf,
                                          aufschlag, gebuehr_fuer("USD", eurusd))
            tickers = sorted({x.vorschlag.ticker for x in v} | set(bestand))
            if not pruefen(n, {t: kurse_laden(t, nyse, "aktie_usd") for t in tickers}, nyse):
                continue
            werte_buch[n] = journal.kasse(n) + sum(s * preise[t] / eurusd for t, s in bestand.items())
            journal.zustand_speichern(n, z)
            erg.meldungen.append(f"{n}: {grund}, {len(v)} Vorschläge")
            roh += v

    # Devisentausch je Buch vor den USD-Käufen (Entscheidung Jakob 03.11.2026)
    puffer = float(b.get("waehrung", {}).get("tausch_puffer", 0.02))
    for n in werte_buch:
        t = tausch_vorschlag(n, tag, roh, journal.kasse_je_waehrung(n).get("USD", 0.0), eurusd, puffer,
                             lambda v: risk._gebuehr(v) * eurusd)
        if t is not None:
            roh.append(t)

    # Risk-Manager je Buch, Speichern
    kontexte = {n: kontext(journal, n, tag, werte_buch[n], offene=offene, fundamental=fundamental_gruende) for n in werte_buch}
    urteile = risk.pruefe_alle([x.vorschlag for x in roh], kontexte)
    nach_id = {x.vorschlag.id: x for x in roh}
    freigabe_bis = f"{jetzt.date()}T23:59:59"
    for v, u in urteile:
        bv = nach_id[v.id]
        journal.vorschlag_speichern(v, u, waehrung=bv.waehrung, freigabe_bis=freigabe_bis, limit_order=bv.limit_order, jetzt=jetzt)
        erg.vorschlaege.append((bv, u))
    for n, w in werte_buch.items():
        journal.buchwert_speichern(n, tag, w, journal.kasse(n))
    journal.ereignis("tageslauf", f"{len(erg.vorschlaege)} Vorschläge, Befunde in {sorted(erg.befunde)}; Xetra {xetra:%d.%m.%Y}, NYSE {nyse:%d.%m.%Y}")
    if sichern:
        ziel = journal.sichern(None, jetzt=jetzt)
        erg.meldungen.append(f"Journal gesichert: {ziel.name}" if ziel else "Journal NICHT gesichert: JOURNAL_BACKUP_DIR fehlt in .env")
    return erg


# --- Freigabe und Senden ----------------------------------------------------------------------------------------------
def freigeben_und_senden(journal, ids: list[str], broker, jetzt: datetime, *, risk: RiskManager | None = None,
                         konfig_betrieb: dict | None = None, kurse_laden=None, probe: bool = False) -> list[str]:
    """Gibt frei und sendet. Gibt Meldungen zurück; nie eine Ausnahme bis zur Oberfläche (sauberer Abbruch).

    Probe-Modus (03.11.2026): Freigabe jederzeit, nichts wird gesendet, kein Messbeginn. Messbeginn auch im echten
    Journal nur, wenn das Senden freigeschaltet ist."""
    from tradingbot.konfiguration import lade_konfiguration

    b = konfig_betrieb or lade_konfiguration("betrieb")
    risk = risk or RiskManager.aus_konfig()
    meldungen = []
    if not probe and not (FREIGABE_VON <= jetzt.time()):
        return [f"Freigabe nur zwischen 18 und 24 Uhr (jetzt {jetzt:%H:%M})"]
    messbeginn = (not probe) and bool(b["ibkr"].get("senden_freigeschaltet", False))
    for i in ids:
        try:
            journal.freigeben(i, jetzt=jetzt, messbeginn=messbeginn)
        except ValueError as f:
            meldungen.append(str(f))
    if probe:
        return meldungen + [f"Probe: {len(ids)} Vorschläge freigegeben, nichts gesendet, kein Messbeginn"]
    if not messbeginn:
        meldungen.append("Senden ist ausgeschaltet: Freigaben zählen nicht als Messbeginn")
    try:
        if not broker.verbunden():
            broker.verbinden()
        if not broker.verbunden():
            raise ConnectionError("nicht verbunden")
    except Exception as f:  # noqa: BLE001
        return meldungen + [f"Gateway nicht verbunden ({type(f).__name__}) – nichts gesendet. Freigaben bleiben bis 24 Uhr; Gateway starten und erneut senden."]
    kurse_laden = kurse_laden or _yahoo_kurse
    fx = {"USD": float(kurse_laden("EURUSD=X", jetzt.date(), "fx")["close"].iloc[-1])}
    neu = einlesen(journal, broker, fx)
    freigegeben = journal.vorschlaege(status=("freigegeben",))
    betroffen = {z["buch"] for z in freigegeben} & set(neu)
    if betroffen:
        meldungen.append(f"Neue Ausführungen in {sorted(betroffen)} seit dem Tageslauf – Tageslauf neu starten, diese Bücher werden nicht gesendet")
    diff = abgleich(journal, list(b["buecher"]), broker.positionen())
    if diff:
        return meldungen + ["Abgleich mit IBKR weicht ab – nichts gesendet: " + "; ".join(diff)]
    offene_liste = broker.offene_orders()
    offene = [(o.order_ref.split(":")[0], o.ticker, o.richtung) for o in offene_liste]
    gesendet = journal.gesendete_refs()
    stand = {}                                                                     # Kasse je Buch und Währung im Durchgang
    reihenfolge = lambda z: (z["buch"], 1 if z["art"] == "fx" else (0 if z["richtung"] < 0 else 2))   # noqa: E731 – Verkäufe, Tausch, Käufe
    for z in sorted(freigegeben, key=reihenfolge):
        if z["buch"] in betroffen:
            continue
        letzte = journal.buchwerte(z["buch"])
        wert = float(letzte.iloc[-1]) if len(letzte) else journal.kasse(z["buch"])
        fremd = z["waehrung"] != "EUR"
        v = OrderVorschlag(z["id"], pd.Timestamp(z["signaltag"]), z["buch"], z["ticker"], z["richtung"], z["stueck"], z["letzter_kurs_eur"],
                           z["art"], limit=(z["limit_preis"] / fx.get(z["waehrung"], 1.0) if fremd else z["limit_preis"]) if z["limit_preis"] else None,
                           stop=z["stop"], gebuehrenplan="USD" if z["art"] == "aktie" and z["waehrung"] == "USD" else "EUR",
                           eur_kurs=fx.get(z["waehrung"], 1.0) if fremd else 1.0, waehrung=z["waehrung"], these=z["these"])
        k = kontext(journal, z["buch"], pd.Timestamp(z["signaltag"]), wert, offene=offene)
        k.orders_heute -= 1                                          # die eigene Freigabe nicht doppelt zählen
        if z["buch"] in stand:                                       # Orders desselben Durchgangs verbrauchen die Kasse
            k.kasse, k.kasse_je_waehrung = stand[z["buch"]]
        u = risk.pruefe(v, k)
        if not u.frei:
            journal.status_setzen(z["id"], "veto")
            meldungen.append(f"{z['id']}: Veto bei der zweiten Prüfung – {'; '.join(u.gruende)}")
            continue
        auftrag = Auftrag(z["buch"], z["id"], z["ticker"], z["richtung"], z["stueck"], z["limit_preis"] if z["richtung"] > 0 else None,
                          z["art"], z["waehrung"])
        try:
            order_id = broker.sende(auftrag, gesendet)
        except SendenGesperrt as f:
            meldungen.append(f"{z['id']}: nicht gesendet – {f}")
            continue
        journal.status_setzen(z["id"], "gesendet", order_id=order_id)
        risk.verbuchen(v, k)
        stand[z["buch"]] = (k.kasse, k.kasse_je_waehrung)
        offene.append((z["buch"], z["ticker"], z["richtung"]))
        meldungen.append(f"{z['id']}: gesendet (Order {order_id})")
    return meldungen


# --- Standard-Datenquellen (Yahoo, im Betriebsmodus) -----------------------------------------------------------------------
def _yahoo_kurse(ticker: str, bis, art: str) -> pd.DataFrame:
    """Kurse bis einschließlich `bis` (letzte abgeschlossene Sitzung) aus Yahoo; ETFs in EUR, Ersatzquellen laut
    config/technik.yaml (Order-Kurs in der Handelswährung in attrs['orderkurs']); US-Aktien in USD."""
    from tradingbot.daten.kurse import lade_kurse, lade_kurse_eur
    from tradingbot.konfiguration import lade_konfiguration

    bis = pd.Timestamp(bis).date()
    heute = bis + timedelta(days=1)
    start = "2023-01-01"
    if art == "fx":
        return lade_kurse(ticker, "2025-01-01", bis, heute=heute)
    if art == "etf":
        e = next((e for e in lade_konfiguration("technik")["universum"]["etfs"] if e["ticker"] == ticker), {})
        quelle = e.get("kursquelle")
        if quelle:
            k = lade_kurse_eur(quelle, start, bis, heute=heute)
            k.attrs["orderkurs"] = float(lade_kurse(quelle, start, bis, heute=heute)["close"].iloc[-1])
            return k
        if e.get("handelswaehrung", "EUR") != "EUR":
            return lade_kurse_eur(ticker, start, bis, heute=heute)
        return lade_kurse(ticker, start, bis, heute=heute)
    return lade_kurse(ticker, start, bis, heute=heute)


def _fundamental_bewertung(tag):
    from tradingbot.engines.fundamental.aktuell import bewertung_am

    return bewertung_am(tag)
