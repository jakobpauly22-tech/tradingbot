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
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta

import pandas as pd

from tradingbot.betrieb.buecher import BuchVorschlag, fundamentalbuch, quartalsstichtag, realbuch, tausch_vorschlag, technikbuch
from tradingbot.betrieb.kalender import letzte_abgeschlossene_sitzung, pruefe_tageskurse
from tradingbot.broker.basis import Auftrag, KontraktUnbekannt, SendeErgebnis, SendenGesperrt
from tradingbot.risiko.manager import Kontext, OrderVorschlag, RiskManager, Urteil

FREIGABE_VON = time(18, 0)


def buch_freigeschaltet(betrieb: dict, buch: str) -> bool:
    """Senden je Buch freigeschaltet (config/betrieb.yaml `buecher.<buch>.senden_freigeschaltet`, Jakob 03.11.2026) und global an."""
    return bool(betrieb["ibkr"].get("senden_freigeschaltet", False)) and bool((betrieb["buecher"].get(buch) or {}).get("senden_freigeschaltet", False))


@dataclass
class Laufergebnis:
    jetzt: datetime
    vorschlaege: list[tuple[BuchVorschlag, Urteil]] = field(default_factory=list)
    befunde: dict[str, list[str]] = field(default_factory=dict)       # Buch → Datenbefunde (Buch ohne Vorschläge)
    meldungen: list[str] = field(default_factory=list)
    gestoppt: str | None = None
    # nur zur Anzeige (betrieb/ansicht.py, neue Oberfläche 10.11.2026); ändern nichts am Ablauf
    xetra: object = None                                              # Signaltag Xetra (letzte abgeschlossene Sitzung)
    nyse: object = None                                               # Signaltag NYSE
    kurse_eur: dict[str, float] = field(default_factory=dict)         # letzter Schluss je Titel in EUR
    spyi: object = None                                               # Schlusskurse SPYI in EUR (Vergleich je Buch)
    fx: dict[str, float] = field(default_factory=dict)                # Devisenkurse des Laufs (Fremdwährung je EUR)


# --- Ausführungen, Verfall, Abgleich ------------------------------------------------------------------------------
def modellgebuehr_eur(kosten, ticker: str, waehrung: str, stueck: float, wert_eur: float, fx: dict[str, float]) -> float:
    """Gebühr laut Kostenmodell (config/backtest.yaml, IBKR Tiered: 1,25 € Minimum an EUR-Börsen; US-Aktien je Stück)."""
    plan = "USD" if waehrung == "USD" and not ticker.endswith(".DE") else "EUR"
    return float(kosten.gebuehren_eur(plan, stueck, wert_eur, fx.get("USD", 1.0)))


def _ausfuehrungstag(zeit, ticker: str):
    """Handelstag der Ausführung in der Zeitzone des Heimatplatzes (Xetra: Berlin, US: New York)."""
    ts = pd.Timestamp(str(zeit))
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("Europe/Berlin" if ticker.endswith(".DE") else "America/New_York").date()


def einlesen(journal, broker, fx: dict[str, float], *, kosten=None, protokoll: list[str] | None = None, eroeffnung=None) -> list[str]:
    """Ausführungen der Bot-Orders ins Journal; gibt die Bücher mit neuen Ausführungen zurück.

    Gebühren (Jakob 04.11.2026): gebucht wird die tatsächliche IBKR-Gebühr (Kasse = IBKR); fehlt der CommissionReport,
    wird vorläufig die Modellgebühr gebucht und das gemeldet. Die Modellgebühr (Tiered) steht daneben. `eroeffnung(ticker,
    tag)` liefert den Eröffnungskurs des Ausführungstags (Abweichung im Protokoll)."""
    neu = []
    for a in broker.ausfuehrungen():
        ibkr, ibkr_w = a["gebuehr"], a["gebuehr_waehrung"]
        fg = fx.get(ibkr_w, 1.0) if ibkr_w != "EUR" else 1.0
        ibkr_eur = None if ibkr is None else ibkr / fg
        if a.get("art") == "fx":
            modell = kosten.tauschkosten_eur("USD", a["betrag_nach"], fx.get("USD", 1.0)) if kosten else (ibkr_eur or 0.0)
            gebucht = ibkr_eur if ibkr_eur is not None else modell
            if journal.tausch(a["exec_id"], a["order_ref"], a["von"], a["nach"], a["betrag_von"], a["betrag_nach"], gebucht, a["zeit"],
                              gebuehr_ibkr=ibkr, gebuehr_ibkr_waehrung=ibkr_w, gebuehr_modell_eur=modell):
                neu.append(a["order_ref"].split(":")[0])
                if protokoll is not None:
                    protokoll.append(f"Tausch {a['betrag_von']:,.2f} EUR → {a['betrag_nach']:,.2f} USD: Gebühr IBKR "
                                     f"{'nicht gemeldet' if ibkr is None else f'{ibkr:.2f} {ibkr_w}'}, Modell {modell:.2f} €")
            continue
        f = fx.get(a["waehrung"], 1.0) if a["waehrung"] != "EUR" else 1.0
        preis_eur = a["preis"] / f
        if kosten:
            s0, w0, g0 = journal.gebuchte_gebuehr(a["order_ref"])
            gesamt = modellgebuehr_eur(kosten, a["ticker"], a["waehrung"], s0 + a["stueck"], w0 + a["stueck"] * preis_eur, fx)
            modell_eur = max(gesamt - g0, 0.0)
        else:
            modell_eur = ibkr_eur or 0.0
        if ibkr is not None:
            gebucht_eur, gebucht_fw, gebucht_w = ibkr_eur, ibkr, ibkr_w
        else:                                                    # kein CommissionReport: vorläufig Modell, gemeldet
            plan_w = "USD" if a["waehrung"] == "USD" and not a["ticker"].endswith(".DE") else "EUR"
            gebucht_eur, gebucht_w = modell_eur, plan_w
            gebucht_fw = modell_eur * (fx.get("USD", 1.0) if plan_w == "USD" else 1.0)
        eroeffnung_kurs = None
        if eroeffnung is not None:
            try:
                eroeffnung_kurs = eroeffnung(a["ticker"], _ausfuehrungstag(a["zeit"], a["ticker"]))
            except Exception:  # noqa: BLE001 – Kurs fehlt: nur im Protokoll vermerkt
                eroeffnung_kurs = None
        if journal.ausfuehrung(a["exec_id"], a["order_ref"], a["ticker"], a["richtung"], a["stueck"], preis_eur, gebucht_eur, a["zeit"],
                               waehrung=a["waehrung"], preis=a["preis"], gebuehr=gebucht_fw, gebuehr_waehrung=gebucht_w,
                               boerse=a.get("boerse"), gebuehr_ibkr=ibkr, gebuehr_ibkr_waehrung=ibkr_w, gebuehr_modell_eur=modell_eur,
                               eroeffnung=eroeffnung_kurs):
            neu.append(a["order_ref"].split(":")[0])
            if protokoll is not None:
                abw = "" if ibkr_eur is None else f", Abweichung IBKR − Modell {ibkr_eur - modell_eur:+.2f} €"
                geb = (f"Gebühr IBKR {ibkr:.2f} {ibkr_w} (gebucht), Modell {modell_eur:.2f} €{abw}" if ibkr is not None
                       else f"Gebühr IBKR nicht gemeldet – vorläufig Modell {modell_eur:.2f} € gebucht")
                eroe = (f"; Eröffnung {eroeffnung_kurs:.4f}, Abweichung {a['preis'] / eroeffnung_kurs - 1:+.2%} {PAPER_SIMULATION}"
                        if eroeffnung_kurs else "; Eröffnungskurs nicht verfügbar")
                protokoll.append(f"Ausführung {a['order_ref'].split(':')[0]} {'KAUF' if a['richtung'] > 0 else 'VERKAUF'} {a['stueck']:g} × "
                                 f"{a['ticker']} @ {a['preis']:.4f} {a['waehrung']} am {a.get('boerse') or '–'} um {a['zeit']}: {geb}{eroe}")
    return sorted(set(neu))


# Kennzeichnung der Abweichung zum Eröffnungskurs (Jakob 11.11.2026): IBKR simuliert Ausführungen im Paper-Konto, der Preis
# kommt nicht aus der echten Eröffnungsauktion – die Abweichung ist nur eingeschränkt aussagekräftig.
PAPER_SIMULATION = "(Paper-Simulation: IBKR simuliert Paper-Ausführungen, nur eingeschränkt aussagekräftig)"


def _eroeffnung_fn(kurse_laden):
    """Eröffnungskurs am Heimatplatz in der Handelswährung (Xetra-ETF: EUR-Reihe, US-Aktie: USD-Reihe)."""
    def eroeffnung(ticker, tag):
        art = "etf" if ticker.endswith(".DE") else "aktie_usd"
        k = kurse_laden(ticker, tag, art)
        k = k[k.index.normalize() == pd.Timestamp(tag)]
        return float(k["open"].iloc[-1]) if len(k) else None
    return eroeffnung


def nicht_handelbare_entfernen(bewertung: pd.DataFrame, nyse, max_alter_handelstage: int = 5) -> tuple[pd.DataFrame, list[str]]:
    """Titel, die nicht mehr notiert oder bei IBKR nicht handelbar sind, dürfen nicht vorgeschlagen werden (Jakob
    04.11.2026, Anlass KVUE: in der Wikipedia-Zusammensetzung noch Mitglied, letzter Kurs 30.10.2026, bei IBKR kein Kontrakt).
    Raus: (a) letzter Kurs älter als `max_alter_handelstage` NYSE-Handelstage, (b) in config/kontrakte.yaml unter
    `nicht_aufloesbar`. Gibt die bereinigte Bewertung und Meldungen zurück."""
    from tradingbot.broker.ibkr import nicht_aufloesbar

    if bewertung is None or not len(bewertung) or "symbol" not in bewertung.columns:
        return bewertung, []
    grenze = pd.Timestamp(nyse) - pd.offsets.BDay(max_alter_handelstage)
    kursdatum = pd.to_datetime(bewertung["kursdatum"]) if "kursdatum" in bewertung.columns else pd.Series(pd.Timestamp(nyse), index=bewertung.index)
    alt = kursdatum < grenze
    unbekannt = bewertung["symbol"].isin(set(nicht_aufloesbar()))
    raus = bewertung[alt | unbekannt]
    meldungen = []
    for r in raus.itertuples():
        grund = []
        if alt.loc[r.Index]:
            grund.append(f"letzter Kurs {pd.Timestamp(kursdatum.loc[r.Index]).date():%d.%m.%Y}")
        if unbekannt.loc[r.Index]:
            grund.append("bei IBKR nicht handelbar")
        meldungen.append(f"Fundamental: {r.symbol} nicht vorschlagbar ({', '.join(grund)}) – vermutlich nicht mehr notiert oder nicht "
                         f"mehr im Index; Zusammensetzung prüfen")
    return bewertung[~(alt | unbekannt)], meldungen


US_OFFEN_BIS = time(22, 0)           # US-Handel offen bis 22:00 Uhr deutscher Zeit (im Regelfall)
FX_PAUSE = (time(22, 55), time(23, 15))  # IDEALPRO-Tagesschluss


def zeitfenster_hinweis(jetzt: datetime, vorschlaege) -> list[str]:
    """Hinweis für US-Orders mit OPG und den EUR→USD-Tausch (Jakob 04.11.2026): Freigabe vor 22:00 Uhr (US-Handel offen)
    oder zwischen 22:55 und 23:15 Uhr (FX-Tagesschluss). `vorschlaege`: OrderVorschläge oder Journalzeilen."""
    def feld(v, n):
        return v[n] if not hasattr(v, n) else getattr(v, n)
    us = [v for v in vorschlaege if feld(v, "art") == "aktie" and not str(feld(v, "ticker")).endswith(".DE") and feld(v, "richtung") > 0]
    fx = [v for v in vorschlaege if feld(v, "art") == "fx"]
    t = jetzt.time()
    hinweise = []
    if us and t < US_OFFEN_BIS:
        hinweise.append(f"HINWEIS Zeitpunkt: {len(us)} US-Käufe mit Limit-On-Open – Freigabe vor 22:00 Uhr, der US-Handel ist noch offen "
                        f"(jetzt {jetzt:%H:%M}); besser zwischen 22:05 und 22:50 Uhr freigeben")
    if (us or fx) and FX_PAUSE[0] <= t <= FX_PAUSE[1]:
        hinweise.append(f"HINWEIS Zeitpunkt: {'EUR→USD-Tausch' if fx else ''}{' und ' if fx and us else ''}{'US-Käufe' if us else ''} "
                        f"im FX-Tagesschluss 22:55–23:15 Uhr (jetzt {jetzt:%H:%M}); besser zwischen 22:05 und 22:50 Uhr freigeben")
    return hinweise


ZINS_PUFFER_EUR = 1.0               # Zuschlag auf die geschätzten neuen Zinsen (Jakob 10.11.2026)


def zinsbilanz(d: float, vorher: float, jetzt: float) -> float:
    """Zinsbilanz seit dem letzten Lauf = Gutschrift + aktueller Zinsstand − letzter Zinsstand: die seit dem letzten Lauf
    neu entstandenen Zinsen, egal welcher Teil davon schon gutgeschrieben ist (Jakob 10.11.2026)."""
    return d + jetzt - vorher


def zinsbilanz_grenze(tageszins: float, tage: int) -> float:
    """Obergrenze der Zinsbilanz: geschätzter Tageszins × Kalendertage seit dem letzten Lauf + 1 €."""
    return max(tageszins, 0.0) * max(tage, 0) + ZINS_PUFFER_EUR


def zinsbuchung_belegt(d: float, vorher: float, jetzt: float, tageszins: float, tage: int, toleranz: float) -> bool:
    """Belegte Zinsbuchung (Jakob 10.11.2026, Zinsbilanz): Die aufgelaufenen Zinsen sind gesunken, und
    Gutschrift + aktueller Zinsstand − letzter Zinsstand liegt zwischen −`toleranz` (0,05 €) und Tageszins × Tage + 1 €.

    Deckt beide Fälle: Gutschrift inklusive neuer Tage (Gutschrift > letzter Stand) und Gutschrift nur des Vormonats,
    während der letzte Lauf schon Tage des neuen Monats enthielt (Gutschrift < letzter Stand, Rest im neuen Stand)."""
    return d > 0 and jetzt < vorher - 1e-9 and -toleranz - 1e-9 <= zinsbilanz(d, vorher, jetzt) <= zinsbilanz_grenze(tageszins, tage) + 1e-9


def kassenabgleich(journal, buecher: list[str], broker, b: dict, heute=None) -> tuple[list[str], str]:
    """Kasse je Währung (Jakob 04.11.2026): Summe der Buchkassen gegen die IBKR-Kontokasse, bezogen auf die Kassenbasis
    (Kontokasse ohne Bot-Bewegungen, einmalig festgehalten). Toleranz `abgleich_kasse_toleranz` (Standard 0,05).

    Abweichungen (Jakob 04. und 09.11.2026):
    - Zinsbuchung, belegt (`zinsbuchung_belegt`, Jakob 09. und 10.11.2026): Die aufgelaufenen Zinsen (AccruedCash) sind
      gesunken, und die Zinsbilanz (Gutschrift + aktueller Zinsstand − letzter Zinsstand) liegt zwischen −0,05 € und
      Tageszins × Tage seit dem letzten Lauf + 1 €. Tageszins geschätzt aus der Veränderung der aufgelaufenen Zinsen
      zwischen zwei Läufen (Kalendertage). → Kassenbasis, Protokoll, kein Stopp. Bücher erhalten keine Zinsen (wie im Backtest).
    - Buchung ohne Buchbezug bis `abgleich_buchung_ohne_buchbezug_max` (10 €) → Kassenbasis, als „vermutet“ protokolliert.
    - Alles andere über 10 € stoppt."""
    if not hasattr(broker, "kasse_je_waehrung"):
        return [], ""
    ibkr = broker.kasse_je_waehrung()
    if not ibkr:
        return [], "Kassen-Abgleich: IBKR meldet keine Kontokasse (accountValues leer) – nicht geprüft"
    zinsen = broker.aufgelaufene_zinsen() if hasattr(broker, "aufgelaufene_zinsen") else None
    heute = pd.Timestamp(heute if heute is not None else pd.Timestamp.now()).normalize()
    bot: dict[str, float] = {}
    for n in buecher:
        start = journal.startkapital(n)
        for w, betrag in journal.kasse_je_waehrung(n).items():
            bot[w] = bot.get(w, 0.0) + betrag - (start if w == "EUR" else 0.0)
    konto = journal.zustand("_konto")
    basis = konto.get("kassenbasis")
    if basis is None:
        basis = {w: ibkr.get(w, 0.0) - bot.get(w, 0.0) for w in sorted(set(ibkr) | set(bot))}
        konto.update({"kassenbasis": basis, "festgehalten": str(heute.date())})
        if zinsen is not None:
            konto["aufgelaufene_zinsen"], konto["zinsstand_tag"] = zinsen, str(heute.date())
        journal.zustand_speichern("_konto", konto)
        journal.ereignis("kassenbasis", "Kassenbasis festgehalten: " + ", ".join(f"{w} {v:,.2f}" for w, v in basis.items()))
        return [], "Kassen-Abgleich: Kassenbasis erstmals festgehalten (" + ", ".join(f"{w} {v:,.2f}" for w, v in basis.items()) + \
            ") – bitte mit dem Startguthaben des Paper-Kontos vergleichen"
    tol = float(b.get("sicherheit", {}).get("abgleich_kasse_toleranz", 0.05))
    grenze = float(b.get("sicherheit", {}).get("abgleich_buchung_ohne_buchbezug_max", 10.0))
    vorher = konto.get("aufgelaufene_zinsen")
    tage = (heute - pd.Timestamp(konto["zinsstand_tag"])).days if konto.get("zinsstand_tag") else 0
    tageszins = konto.get("tageszins") or {}
    abw, uebernommen, zinsbuchungen = [], [], []
    for w in sorted(set(ibkr) | set(bot) | set(basis)):
        soll = basis.get(w, 0.0) + bot.get(w, 0.0)
        d = ibkr.get(w, 0.0) - soll
        if abs(d) <= tol:
            continue
        abnahme = (vorher.get(w, 0.0) - zinsen.get(w, 0.0)) if (vorher is not None and zinsen is not None) else None
        grenze_bilanz = zinsbilanz_grenze(tageszins.get(w, 0.0), tage)
        bilanz = None if abnahme is None else zinsbilanz(d, vorher.get(w, 0.0), zinsen.get(w, 0.0))
        if abnahme is not None and zinsbuchung_belegt(d, vorher.get(w, 0.0), zinsen.get(w, 0.0), tageszins.get(w, 0.0), tage, tol):
            basis[w] = basis.get(w, 0.0) + d                # belegte Zinsbuchung (Jakob 09./10.11.2026)
            zinsbuchungen.append(f"{w} {d:+,.2f} (aufgelaufene Zinsen {vorher.get(w, 0.0):,.2f} → {zinsen.get(w, 0.0):,.2f}; Zinsbilanz "
                                 f"{bilanz:+,.2f}, zulässig −0,05 bis {grenze_bilanz:,.2f} bei Tageszins {tageszins.get(w, 0.0):,.2f} × {tage} Tage + 1 €)")
        elif abs(d) <= grenze:
            # Buchung ohne Buchbezug (Zinsen, Kontogebühren; Jakob 04.11.2026): in die Kassenbasis, protokolliert
            basis[w] = basis.get(w, 0.0) + d
            uebernommen.append(f"{w} {d:+,.2f}")
        else:
            zins = ("aufgelaufene Zinsen: kein Vergleichsstand" if abnahme is None else
                    f"aufgelaufene Zinsen {vorher.get(w, 0.0):,.2f} → {zinsen.get(w, 0.0):,.2f}, Erhöhung passt nicht als Zinsbuchung "
                    f"(Zinsbilanz {bilanz:+,.2f}, zulässig −0,05 bis {grenze_bilanz:,.2f} bei gesunkenen Zinsen)")
            abw.append(f"Kasse {w}: Bücher + Basis {soll:,.2f}, IBKR {ibkr.get(w, 0.0):,.2f} (Abweichung {d:+,.2f}, über "
                       f"{grenze:.0f} € – unerklärte Buchung, bitte im Client Portal klären; {zins})")
    if abw:
        return abw, ""
    konto["kassenbasis"] = basis
    heute_text = str(heute.date())
    if uebernommen:
        konto.setdefault("buchungen_ohne_buchbezug", []).append({"tag": heute_text, "betraege": uebernommen})
        journal.ereignis("kassenbasis", "Buchung ohne Buchbezug (Zinsen/Kontogebühren vermutet) in die Kassenbasis: " + ", ".join(uebernommen))
    if zinsbuchungen:
        konto.setdefault("zinsbuchungen", []).append({"tag": heute_text, "betraege": zinsbuchungen})
        journal.ereignis("kassenbasis", "Zinsbuchung belegt (Abnahme der aufgelaufenen Zinsen), in die Kassenbasis, Bücher ohne Zinsen: "
                         + ", ".join(zinsbuchungen))
    if zinsen is not None:
        if vorher is not None and tage > 0:                # Tageszins aus zwei Läufen ohne Gutschrift dazwischen
            for w, z in zinsen.items():
                if z > vorher.get(w, 0.0) + 1e-9:
                    tageszins[w] = (z - vorher.get(w, 0.0)) / tage
            konto["tageszins"] = tageszins
        konto["aufgelaufene_zinsen"], konto["zinsstand_tag"] = zinsen, str(heute.date())
    journal.zustand_speichern("_konto", konto)
    text = "Kassen-Abgleich: Kasse je Währung stimmt mit IBKR überein (" + ", ".join(f"{w} {ibkr.get(w, 0.0):,.2f}" for w in sorted(ibkr)) + ")"
    if zinsbuchungen:
        text += "; Zinsbuchung belegt, in die Kassenbasis (Bücher ohne Zinsen): " + ", ".join(zinsbuchungen)
    if uebernommen:
        text += "; Buchung ohne Buchbezug in die Kassenbasis übernommen: " + ", ".join(uebernommen)
    return [], text


def verpasste_handelstage(boerse: str, seit, tag) -> list[pd.Timestamp]:
    """Handelstage strikt zwischen dem Signaltag des letzten Laufs (`seit`) und dem heutigen Signaltag `tag`."""
    from tradingbot.betrieb.kalender import ist_handelstag

    if seit is None:
        return []
    d, ende, tage = pd.Timestamp(seit).date() + timedelta(days=1), pd.Timestamp(tag).date(), []
    while d < ende:
        if ist_handelstag(boerse, d):
            tage.append(pd.Timestamp(d))
        d += timedelta(days=1)
    return tage


def ausfuehrungen_klaeren(journal, b: dict, offen_liste, positionen, broker, letzte_sitzung, fx, risk, kurse_laden, flex,
                          erg: Laufergebnis, jetzt=None) -> str | None:
    """Orders unterwegs, deren Handelstag vorbei ist und die bei IBKR nicht mehr offen sind (betrieb/nachtrag.py): ohne
    Abweichung zur IBKR-Position → verfallen; mit Abweichung → Ausführung außerhalb des API-Zeitfensters, Nachtrag mit
    Beleg (Flex, sonst Position mit Einstand) und Meldung. Gibt den Stoppgrund zurück, wenn ein Verdacht ohne Beleg bleibt."""
    from tradingbot.betrieb import nachtrag

    buecher = list(b["buecher"])
    quelle = nachtrag.flex_aus_env() if flex == "env" else flex
    # angenommene Gebühren früherer Nachträge mit Flex abgleichen (Jakob 09.11.2026)
    abgeglichen, stopp = nachtrag.angenommene_abgleichen(journal, quelle, fx, kosten=risk.kosten, eroeffnung=_eroeffnung_fn(kurse_laden))
    erg.meldungen += abgeglichen
    if stopp:
        return "Abgleich angenommener Gebühren mit Flex weicht ab – Tageslauf gestoppt: " + "; ".join(stopp)
    kasse_ibkr = broker.kasse_je_waehrung() if hasattr(broker, "kasse_je_waehrung") else None
    tol = float(b.get("sicherheit", {}).get("abgleich_kasse_toleranz", 0.05))
    k = nachtrag.klaeren(journal, buecher, {o.order_ref for o in offen_liste}, positionen, letzte_sitzung,
                         kasse_ibkr=kasse_ibkr or None, toleranz=tol, jetzt=jetzt)
    if k.verdacht:
        erg.meldungen.append("Ausführung außerhalb des API-Zeitfensters vermutet (IBKR-Position weicht ab, Order nicht mehr offen): "
                             + ", ".join(f"{z['buch']}:{z['id']}" for z in k.verdacht))
        nachtrag.nachtragen(journal, buecher, k, positionen, fx, kosten=risk.kosten, kurse_laden=kurse_laden, flex=quelle,
                            gebuehrenplan=(b.get("nachtrag") or {}).get("gebuehr"), eroeffnung=_eroeffnung_fn(kurse_laden))
        erg.meldungen += [f"Nachtrag: {h}" for h in k.hinweise]
        if k.ohne_beleg:
            return ("Ausführung außerhalb des API-Zeitfensters ohne Beleg – Tageslauf gestoppt, nichts gebucht: " + "; ".join(k.ohne_beleg)
                    + ". Weg: Flex-Abfrage einrichten (docs/BETRIEB.md) oder im Client Portal prüfen und mit Jakob klären")
        erg.meldungen += k.gebucht
    for z in k.verfallen:
        journal.status_setzen(z["id"], "verfallen")
        journal.ereignis("verfallen", f"Order {z['id']} nicht ausgeführt, verfallen (IBKR-Position unverändert)", z["buch"])
    if k.verfallen:
        erg.meldungen.append(f"{len(k.verfallen)} nicht ausgeführte Order(s) verfallen")
    return None


def abgleich(journal, buecher: list[str], positionen) -> list[str]:
    """Summe der Bücher je Ticker gegen die IBKR-Positionen; leere Liste = in Ordnung."""
    soll: dict[str, float] = {}
    for b in buecher:
        for t, s in journal.bestand(b).items():
            soll[t] = soll.get(t, 0.0) + s
    ist = {p.ticker: p.stueck for p in positionen if abs(p.stueck) > 1e-9}
    return [f"{t}: Bücher {soll.get(t, 0):g} Stück, IBKR {ist.get(t, 0):g} Stück" for t in sorted(set(soll) | set(ist))
            if abs(soll.get(t, 0) - ist.get(t, 0)) > 1e-6]


def _bestand_text(journal, b) -> str:
    n = sum(1 for buch in b["buecher"] for s in journal.bestand(buch).values() if abs(s) > 1e-9)
    return "alle Bücher ohne Bestand" if n == 0 else f"{n} Positionen in den Büchern"


# --- Risiko-Kontext je Buch -----------------------------------------------------------------------------------------
def kasse_frei(journal, buch: str, fx: dict[str, float] | None = None) -> tuple[float, dict[str, float]]:
    """Kasse des Buchs abzüglich Orders unterwegs (gesamt in EUR und je Währung); ein Tausch unterwegs zählt als
    abgehende EUR und zugehende Fremdwährung."""
    res = journal.reserviert(buch)
    kassen = journal.kasse_je_waehrung(buch)
    for w, betrag in res.items():
        if w != "EUR_gesamt":
            kassen[w] = kassen.get(w, 0.0) - betrag
    for z in journal.unterwegs(buch):
        if z["art"] == "fx":
            kassen[z["waehrung"]] = kassen.get(z["waehrung"], 0.0) + z["stueck"] * (fx or {}).get(z["waehrung"], 1.0)
    return journal.kasse(buch) - res["EUR_gesamt"], kassen


def kontext(journal, buch: str, tag, wert: float, *, offene=(), fundamental=None, fx=None) -> Kontext:
    werte = journal.buchwerte(buch)
    werte = pd.concat([werte, pd.Series({pd.Timestamp(tag): wert})]).groupby(level=0).last().sort_index()
    hoch = float(werte.max()) if len(werte) else wert
    monatsende = werte[werte.index < pd.Timestamp(tag).to_period("M").start_time]
    monat = wert / float(monatsende.iloc[-1]) - 1 if len(monatsende) else 0.0
    kasse, kassen = kasse_frei(journal, buch, fx)
    unterwegs = [(z["buch"], z["ticker"], z["richtung"]) for z in journal.unterwegs(buch)]
    return Kontext(buch=buch, kasse=kasse, wert=wert, bestand={t: int(round(s)) for t, s in journal.bestand(buch).items()},
                   kasse_je_waehrung=kassen,
                   monatsrendite=monat, vom_hoch=wert / hoch - 1 if hoch > 0 else 0.0, orders_heute=journal.orders_heute(buch, tag),
                   gesendete_ids={r.split(":", 1)[1] for r in journal.gesendete_refs()},
                   offene_orders=list(offene) + [o for o in unterwegs if o not in offene], fundamental=fundamental or {})


# --- Tageslauf --------------------------------------------------------------------------------------------------------
def tageslauf(jetzt: datetime, journal, *, broker=None, kurse_laden=None, fundamental_bewertung=None, risk: RiskManager | None = None,
              konfig: dict | None = None, sichern: bool = True, flex="env") -> Laufergebnis:
    """Ein Tageslauf. `kurse_laden(ticker, bis, art) -> DataFrame` (EUR-Kurse) und `fundamental_bewertung(tag)` sind
    austauschbar (Tests); Standard sind Yahoo-Kurse und engines/fundamental/aktuell.py. `flex`: Beleg-Quelle für
    Ausführungen außerhalb des API-Zeitfensters („env“ = Flex-Abfrage aus .env, None = keine, sonst Funktion)."""
    from tradingbot.konfiguration import lade_konfiguration

    konfig = konfig or {n: lade_konfiguration(n) for n in ("betrieb", "technik", "fundamental", "backtest")}
    b, kt, kf = konfig["betrieb"], konfig["technik"], konfig["fundamental"]
    risk = risk or RiskManager.aus_konfig()
    kurse_laden = kurse_laden or _yahoo_kurse
    erg = Laufergebnis(jetzt)
    xetra, nyse = letzte_abgeschlossene_sitzung("xetra", jetzt), letzte_abgeschlossene_sitzung("nyse", jetzt)
    erg.xetra, erg.nyse = xetra, nyse
    tag = pd.Timestamp(xetra)
    aufschlag = float(b["orders"]["kauf"]["aufschlag_vortagesschluss"])
    max_sprung = float(b["datenpruefung"]["max_tagessprung"])
    for name, bk in b["buecher"].items():
        journal.buch_anlegen(name, float(bk["budget_eur"]))
    journal.abgelaufene_markieren(jetzt)
    eurusd = float(kurse_laden("EURUSD=X", tag.date(), "fx")["close"].iloc[-1])
    fx = {"USD": eurusd}
    erg.fx = dict(fx)

    offene = []
    if broker is not None:
        try:
            if not broker.verbunden():
                broker.verbinden()
            zeilen: list[str] = []
            neu = einlesen(journal, broker, fx, kosten=risk.kosten, protokoll=zeilen, eroeffnung=_eroeffnung_fn(kurse_laden))
            if neu:
                erg.meldungen.append(f"Neue Ausführungen eingelesen: {', '.join(neu)}")
                erg.meldungen += zeilen
            offen_liste = broker.offene_orders()
            offene = [(o.order_ref.split(":")[0], o.ticker, o.richtung) for o in offen_liste]
            positionen = broker.positionen()
            # Ausführungen außerhalb des API-Zeitfensters (verpasste Abende, Jakob 09.11.2026): erst klären, dann verfallen
            stopp = ausfuehrungen_klaeren(journal, b, offen_liste, positionen, broker, xetra, fx, risk, kurse_laden, flex, erg, jetzt)
            if stopp:
                erg.gestoppt = stopp
                journal.ereignis("abgleich", erg.gestoppt)
                erg.meldungen.append(erg.gestoppt)
                return erg
            diff = abgleich(journal, list(b["buecher"]), positionen)
            if not diff:                                     # Kassenbasis erst festhalten, wenn die Bestände stimmen
                kasse_diff, kasse_text = kassenabgleich(journal, list(b["buecher"]), broker, b, heute=jetzt.date())
                if kasse_text:
                    erg.meldungen.append(kasse_text)
                diff += kasse_diff
            if diff:
                erg.gestoppt = "Abgleich mit IBKR weicht ab – Tageslauf gestoppt: " + "; ".join(diff)
                journal.ereignis("abgleich", erg.gestoppt)
                erg.meldungen.append(erg.gestoppt)
                return erg
            journal.ereignis("abgleich", "Bestände aller Bücher stimmen mit IBKR überein")
            erg.meldungen.append(f"Abgleich: Bestände aller Bücher stimmen mit IBKR überein ({_bestand_text(journal, b)})")
        except Exception as f:  # noqa: BLE001 – Gateway nicht erreichbar: Vorschläge trotzdem, Abgleich vor dem Senden
            erg.meldungen.append(f"Gateway nicht verbunden ({type(f).__name__}): Ausführungen nicht eingelesen; Abgleich vor dem Senden")
            erg.meldungen.append("Abgleich: nicht möglich (Gateway nicht verbunden), wird vor dem Senden nachgeholt")
    else:
        erg.meldungen.append("ohne Gateway: Ausführungen nicht eingelesen; Abgleich vor dem Senden")
        erg.meldungen.append("Abgleich: nicht möglich (ohne Gateway), wird vor dem Senden nachgeholt")

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
    erg.spyi = k_real[etf]["close"]
    erg.kurse_eur[etf] = float(k_real[etf]["close"].iloc[-1])
    werte_buch = {}
    if pruefen("real", k_real, xetra):
        kurs = float(k_real[etf]["close"].iloc[-1])
        werte_buch["real"] = journal.kasse("real") + sum(s * kurs for t, s in journal.bestand("real").items())
        frei_real, _ = kasse_frei(journal, "real", fx)
        if not any(z["ticker"] == etf for z in journal.unterwegs("real")):
            roh += realbuch(tag, etf, kurs, frei_real, aufschlag, gebuehr_fuer("EUR"))

    # Technik-Bücher
    etfs = kt["universum"]["etfs"]
    k_tech = {e["ticker"]: kurse_laden(e["ticker"], tag.date(), "etf") for e in etfs}
    waehrung = {e["ticker"]: e.get("handelswaehrung", "EUR") for e in etfs}
    orderkurs = {t: float(k.attrs.get("orderkurs", k["close"].iloc[-1])) for t, k in k_tech.items()}
    technik_ok = pruefen("technik", k_tech, xetra)
    erg.kurse_eur.update({t: float(k["close"].iloc[-1]) for t, k in k_tech.items()})
    for buch in ("crossover", "momentum"):
        if buch not in b["buecher"]:
            continue
        if not technik_ok:
            erg.befunde[buch] = erg.befunde.get("technik", [])
            continue
        bestand = journal.bestand(buch)
        werte_buch[buch] = journal.kasse(buch) + sum(s * float(k_tech[t]["close"].iloc[-1]) for t, s in bestand.items())
        vor = journal.zustand_fuer_signaltag(buch, tag)
        if vor and not any(x > 0 for x in bestand.values()) and not journal.unterwegs(buch):
            # aufgebaut erst mit Bestand oder Orders unterwegs (wie Fundamental, Korrektur 04.11.2026): Zustände aus Läufen
            # ohne Kauf (Buch gesperrt, nicht freigegeben, abgelehnt, verfallen) gelten nicht – Aufbau wie beim ersten Lauf
            erg.meldungen.append(f"{buch}: noch kein Bestand und keine Order unterwegs – Aufbau wie beim ersten Lauf")
            vor = {}
        frei_buch, _ = kasse_frei(journal, buch, fx)
        # verpasste Tage (Jakob 09.11.2026): Schlusskurse seit dem letzten Lauf der Reihe nach; Ausstiege werden nachgeholt
        seit = journal.vorlauf_signaltag(buch, tag) if vor else None
        verpasst = verpasste_handelstage("xetra", seit, tag)
        if verpasst and any(x > 0 for x in bestand.values()):
            erg.meldungen.append(f"{buch}: {len(verpasst)} Handelstag(e) ohne Lauf seit {pd.Timestamp(seit):%d.%m.%Y} geprüft "
                                 f"({', '.join(f'{d:%d.%m.}' for d in verpasst)}): Ausstiege werden nachgeholt, Einstiege nur mit "
                                 "Signal am aktuellen Tag")
        v, z = technikbuch(buch, buch, tag, k_tech, orderkurs, waehrung, fx, frei_buch, bestand, vor, kt,
                           aufschlag, gebuehr_fuer("EUR"), gesperrt_titel={u["ticker"] for u in journal.unterwegs(buch)},
                           reserviert=journal.kasse(buch) - frei_buch,
                           nachkauf=journal.nachkauf_kandidaten(buch, tag - pd.Timedelta(days=45)), verpasste_tage=verpasst)
        journal.zustand_nach_lauf(buch, tag, vor, z)
        roh += v
    erg.befunde.pop("technik", None)

    # Fundamental-Bücher (Bewertung nur, wenn ein Buch sie heute braucht)
    fb = {n: v for n, v in (("fundamental_a", "A"), ("fundamental_b", "B")) if n in b["buecher"]}
    def _nachkauf(n):
        seit = (journal.zustand(n) or {}).get("letzter_signaltag")
        return journal.nachkauf_kandidaten(n, seit) if seit else set()

    nachkauf_fb = {n: _nachkauf(n) for n in fb}
    # Bücher mit Orders unterwegs gelten als aufgebaut (Jakob 10.11.2026): weder Aufbau noch Nachkauf, solange etwas
    # unterwegs ist; nur der Quartalsstichtag rechnet trotzdem (Titel unterwegs bleiben dabei gesperrt).
    braucht = [n for n in fb if quartalsstichtag(nyse) or (not journal.unterwegs(n) and (not journal.bestand(n) or nachkauf_fb[n]))]
    for n in fb:
        if n not in braucht and journal.unterwegs(n):
            erg.meldungen.append(f"{n}: {len(journal.unterwegs(n))} Order(s) unterwegs – Buch gilt als aufgebaut, keine neuen Käufe")
    kurse_usd: dict[str, float] = {}
    for n in fb:
        bestand = journal.bestand(n)
        if not bestand and n not in braucht:
            werte_buch[n] = journal.kasse(n)                 # nur Kasse (Orders unterwegs), Buchwert trotzdem speichern
        if bestand and n not in braucht:
            k_b = {t: kurse_laden(t, nyse, "aktie_usd") for t in bestand}
            kurse_usd.update({t: float(k["close"].iloc[-1]) for t, k in k_b.items()})
            werte_buch[n] = journal.kasse(n) + sum(s * kurse_usd[t] / eurusd for t, s in bestand.items())
            erg.kurse_eur.update({t: kurse_usd[t] / eurusd for t in bestand})
    if fundamental_bewertung is None and fb:
        try:
            from tradingbot.daten.universum import universum_aktualisieren
            stand = universum_aktualisieren(erzwingen=quartalsstichtag(nyse))
            erg.meldungen.append(f"S&P-500-Liste: Wikipedia, abgerufen {stand['wikipedia_aktuell'][:16].replace('T', ' ')} UTC"
                                 f"{' (Quartalsstichtag: neu abgerufen)' if quartalsstichtag(nyse) else ''}; letzte erfasste Änderung "
                                 f"{stand['letzte_aenderung']} (rein: {stand['zugang'] or '–'}, raus: {stand['abgang'] or '–'})")
        except Exception as f:  # noqa: BLE001
            erg.meldungen.append(f"S&P-500-Liste nicht aktualisiert ({type(f).__name__}: {f}) – Stand unverändert")
    if braucht:
        bewertung, _, meldungen = (fundamental_bewertung or _fundamental_bewertung)(pd.Timestamp(nyse))
        erg.meldungen += meldungen[:5]
        bewertung, raus = nicht_handelbare_entfernen(bewertung, nyse)
        erg.meldungen += raus
        from tradingbot.engines.fundamental.aktuell import rangliste

        fundamental_gruende = {r.symbol: list(r.gruende) for r in bewertung.itertuples() if r.symbol}
        for n in braucht:
            rl = rangliste(bewertung, fb[n])
            bestand = journal.bestand(n)
            preise = {r.symbol: float(r.schluss_usd) for r in bewertung.itertuples() if r.symbol}
            preise.update({t: float(kurse_laden(t, nyse, "aktie_usd")["close"].iloc[-1]) for t in set(bestand) | nachkauf_fb[n] if t not in preise})
            frei_n = kasse_frei(journal, n, fx)[0]
            v, z, grund = fundamentalbuch(n, fb[n], pd.Timestamp(nyse), rl, preise, eurusd, frei_n, bestand,
                                          journal.zustand(n), kf, aufschlag, gebuehr_fuer("USD", eurusd),
                                          gesperrt_titel={u["ticker"] for u in journal.unterwegs(n)}, reserviert=journal.kasse(n) - frei_n,
                                          nachkauf=nachkauf_fb[n])
            tickers = sorted({x.vorschlag.ticker for x in v} | set(bestand))
            if not pruefen(n, {t: kurse_laden(t, nyse, "aktie_usd") for t in tickers}, nyse):
                continue
            werte_buch[n] = journal.kasse(n) + sum(s * preise[t] / eurusd for t, s in bestand.items())
            erg.kurse_eur.update({t: preise[t] / eurusd for t in bestand})
            journal.zustand_speichern(n, z)
            erg.meldungen.append(f"{n}: {grund}, {len(v)} Vorschläge")
            roh += v

    # Devisentausch je Buch vor den USD-Käufen (Entscheidung Jakob 03.11.2026)
    puffer = float(b.get("waehrung", {}).get("tausch_puffer", 0.02))
    for n in werte_buch:
        t = tausch_vorschlag(n, tag, roh, kasse_frei(journal, n, fx)[1].get("USD", 0.0), eurusd, puffer,
                             lambda v: risk._gebuehr(v) * eurusd)
        if t is not None:
            roh.append(t)

    # Risk-Manager je Buch, Speichern
    kontexte = {n: kontext(journal, n, tag, werte_buch[n], offene=offene, fundamental=fundamental_gruende, fx=fx) for n in werte_buch}
    urteile = risk.pruefe_alle([x.vorschlag for x in roh], kontexte)
    nach_id = {x.vorschlag.id: x for x in roh}
    freigabe_bis = f"{jetzt.date()}T23:59:59"
    n_ersetzt = journal.offene_ersetzen(jetzt=jetzt)
    if n_ersetzt:
        journal.ereignis("ersetzt", f"{n_ersetzt} noch nicht freigegebene Vorschläge früherer Läufe ersetzt")
    if broker is not None and hasattr(broker, "kontrakt_aufloesen") and _verbunden(broker):
        urteile = kontrakte_pruefen(urteile, nach_id, broker, b, erg.meldungen)
    for v, u in urteile:
        bv = nach_id[v.id]
        journal.vorschlag_speichern(v, u, waehrung=bv.waehrung, freigabe_bis=freigabe_bis, limit_order=bv.limit_order, jetzt=jetzt,
                                    kern=bv.kern, details=bv.details)
        erg.vorschlaege.append((bv, u))
    for n, w in werte_buch.items():
        w_modell = w + journal.gebuehren_differenz(n)
        journal.buchwert_speichern(n, tag, w, journal.kasse(n), w_modell)
        erg.meldungen.append(f"{n}: Buchwert wie gebucht (Paper, Festpreis) {w:,.2f} €, mit Modellgebühr (Tiered, 1,25 € Minimum) "
                             f"{w_modell:,.2f} € (maßgeblich für den Echtbetrieb)")
    us_fx = [bv.vorschlag for bv, u in erg.vorschlaege if u.frei and (bv.vorschlag.art == "fx" or
             (bv.vorschlag.art == "aktie" and not bv.vorschlag.ticker.endswith(".DE") and bv.vorschlag.richtung > 0))]
    if us_fx:
        erg.meldungen.append("Zeitpunkt: US-Käufe (Limit-On-Open) und EUR→USD-Tausch nicht vor 22:00 Uhr (US-Handel offen) und nicht "
                             "zwischen 22:55 und 23:15 Uhr (FX-Tagesschluss) freigeben; empfohlen 22:05–22:50 Uhr")
        erg.meldungen += zeitfenster_hinweis(jetzt, us_fx)
    journal.ereignis("tageslauf", f"{len(erg.vorschlaege)} Vorschläge, Befunde in {sorted(erg.befunde)}; Xetra {xetra:%d.%m.%Y}, NYSE {nyse:%d.%m.%Y}")
    if sichern:
        ziel = journal.sichern(None, jetzt=jetzt)
        erg.meldungen.append(f"Journal gesichert: {ziel.name}" if ziel else "Journal NICHT gesichert: JOURNAL_BACKUP_DIR fehlt in .env")
    return erg


def _verbunden(broker) -> bool:
    try:
        return bool(broker.verbunden())
    except Exception:  # noqa: BLE001
        return False


def kontrakte_pruefen(urteile, nach_id, broker, b, meldungen) -> list:
    """Kontrakte der freigebbaren Vorschläge in freigeschalteten Büchern schon im Tageslauf qualifizieren (nur lesend):
    conId in die Details und ins Protokoll; unbekannt → Veto „Kontrakt unbekannt“ (Jakob 03.11.2026)."""
    neu = []
    for v, u in urteile:
        if u.frei and buch_freigeschaltet(b, v.buch):
            bv = nach_id[v.id]
            try:
                k = broker.kontrakt_aufloesen(v.ticker, v.art, bv.waehrung if v.art != "fx" else "USD")
                text = (f"IBKR-Kontrakt: conId {k.conId}, Symbol {k.symbol}, Xetra-Kürzel/lokal {k.localSymbol}, "
                        f"Routing {k.exchange}/{getattr(k, 'primaryExchange', '') or '–'}, {k.currency}")
                if bv.limit_order and v.art != "fx" and hasattr(broker, "limit_runden"):
                    alt = bv.limit_order
                    gerundet, stufe = broker.limit_runden(v.ticker, alt, v.richtung)
                    bv.limit_order = gerundet
                    v = replace(v, limit=v.limit * gerundet / alt if v.limit else gerundet)
                    bv.vorschlag = v
                    text += f"; Limit {alt:.4f} → {gerundet:.4f} {bv.waehrung} (Kursstufe {stufe:g})"
                bv.details = (bv.details + "\n" if bv.details else "") + text
                meldungen.append(f"{v.buch} {v.ticker}: {text}")
            except KontraktUnbekannt as f:
                u = Urteil(False, u.gruende + [str(f)], u.hinweise)
                meldungen.append(f"{v.buch} {v.ticker}: Veto – {f}")
        neu.append((v, u))
    return neu


# --- Freigabe und Senden ----------------------------------------------------------------------------------------------
READ_ONLY_MELDUNG = "Read-Only im Gateway ist aktiv – bitte ausschalten und Tageslauf neu starten"


def ist_read_only_ablehnung(text: str | None) -> bool:
    """IBKR-Ablehnung wegen Read-Only (Fehler 321, „schreibgeschützten Modus“)."""
    t = text or ""
    return "321" in t and ("schreibgesch" in t or "read-only" in t.lower() or "read only" in t.lower())


def freigeben_und_senden(journal, ids: list[str], broker, jetzt: datetime, *, risk: RiskManager | None = None,
                         konfig_betrieb: dict | None = None, kurse_laden=None, probe: bool = False, fortschritt=None) -> list[str]:
    """Gibt frei und sendet. Gibt Meldungen zurück; nie eine Ausnahme bis zur Oberfläche (sauberer Abbruch).

    Probe-Modus (03.11.2026): Freigabe jederzeit, nichts wird gesendet, kein Messbeginn. Messbeginn auch im echten
    Journal nur, wenn das Senden freigeschaltet ist.

    Vorfall 09.11.2026: Senden mit Read-Only im Gateway; die Wartezeiten auf die Ablehnungen froren das Fenster ein, Windows
    schloss es mitten im Senden. Seitdem: Schreibzugriff vor jedem Senden prüfen, bei Read-Only nichts an IBKR übergeben;
    `fortschritt()` wird zwischen den Orders aufgerufen (Fenster bleibt bedienbar); jede Ausnahme wird zur Meldung."""
    from tradingbot.konfiguration import lade_konfiguration

    b = konfig_betrieb or lade_konfiguration("betrieb")
    risk = risk or RiskManager.aus_konfig()
    meldungen = []
    if not probe and not (FREIGABE_VON <= jetzt.time()):
        return [f"Freigabe nur zwischen 18 und 24 Uhr (jetzt {jetzt:%H:%M})"]
    global_an = bool(b["ibkr"].get("senden_freigeschaltet", False))
    zeilen = [z for z in journal.vorschlaege() if z["id"] in set(ids)]
    meldungen += zeitfenster_hinweis(jetzt, zeilen)
    for i in ids:
        z = journal.db.execute("SELECT buch FROM vorschlaege WHERE id=?", (i,)).fetchone()
        buch_an = bool(z) and buch_freigeschaltet(b, z["buch"])
        if not probe and z and not buch_an:
            meldungen.append(f"{i}: Buch {z['buch']} ist zum Senden noch nicht freigeschaltet – nicht freigebbar")
            continue
        try:
            journal.freigeben(i, jetzt=jetzt, messbeginn=False)           # Messbeginn erst mit der ersten angenommenen Order
        except ValueError as f:
            meldungen.append(str(f))
    messbeginn = (not probe) and global_an
    if probe:
        return meldungen + [f"Probe: {len(ids)} Vorschläge freigegeben, nichts gesendet, kein Messbeginn"]
    if not messbeginn:
        meldungen.append("Senden ist ausgeschaltet: Freigaben zählen nicht als Messbeginn")
    try:
        meldungen = _senden(journal, b, broker, jetzt, risk, kurse_laden, meldungen, fortschritt)
    except Exception as f:  # noqa: BLE001 – nie bis zur Oberfläche (Absturz 09.11.2026)
        journal.ereignis("senden_abbruch", f"{type(f).__name__}: {f}")
        meldungen.append(f"Senden abgebrochen ({type(f).__name__}: {f}) – Journal und offene Orders prüfen, Tageslauf neu starten")
    finally:                                                 # Verbindung nach Freigabe/Senden trennen (Jakob 04.11.2026)
        try:
            if broker is not None and broker.verbunden():
                broker.trennen()
                meldungen.append("Verbindung zum Gateway getrennt")
        except Exception as f:  # noqa: BLE001
            meldungen.append(f"Trennen fehlgeschlagen ({type(f).__name__}: {f})")
    try:                                                     # Sicherung nach Freigabe/Senden (Jakob 03.11.2026)
        ziel = journal.sichern(None, jetzt=datetime.now())
        meldungen.append(f"Journal gesichert nach Freigabe/Senden: {ziel.name}" if ziel else "Journal NICHT gesichert: JOURNAL_BACKUP_DIR fehlt in .env")
    except Exception as f:  # noqa: BLE001 – Sicherung darf das Senden nie rückgängig machen oder abbrechen
        meldungen.append(f"Journal-Sicherung fehlgeschlagen ({type(f).__name__}: {f})")
    return meldungen


def _senden(journal, b, broker, jetzt, risk, kurse_laden, meldungen, fortschritt=None) -> list[str]:
    """Senden nach der Freigabe (unverändert aus freigeben_und_senden ausgelagert, damit danach gesichert wird)."""
    def weiter():
        if fortschritt is not None:
            fortschritt()

    try:
        if not broker.verbunden():
            broker.verbinden()
        if not broker.verbunden():
            raise ConnectionError("nicht verbunden")
    except Exception as f:  # noqa: BLE001
        return meldungen + [f"Gateway nicht verbunden ({type(f).__name__}) – nichts gesendet. Freigaben bleiben bis 24 Uhr; Gateway starten und erneut senden."]
    # Schreibzugriff vor jedem Senden prüfen (Jakob 10.11.2026): bei Read-Only nichts an IBKR übergeben, auch keinen Tausch
    if hasattr(broker, "schreibzugriff"):
        ok, grund = broker.schreibzugriff()
        weiter()
        if not ok:
            journal.ereignis("read_only", f"Senden verweigert: {grund}")
            return meldungen + [f"{READ_ONLY_MELDUNG} ({grund}). Nichts gesendet; Freigaben bleiben bis 24 Uhr gültig."]
        meldungen.append(grund)
    if hasattr(broker, "waehrend_warten"):
        broker.waehrend_warten = fortschritt
    kurse_laden = kurse_laden or _yahoo_kurse
    fx = {"USD": float(kurse_laden("EURUSD=X", jetzt.date(), "fx")["close"].iloc[-1])}
    zeilen: list[str] = []
    neu = einlesen(journal, broker, fx, kosten=risk.kosten, protokoll=zeilen)
    meldungen += zeilen
    freigegeben = journal.vorschlaege(status=("freigegeben",))
    betroffen = {z["buch"] for z in freigegeben} & set(neu)
    if betroffen:
        meldungen.append(f"Neue Ausführungen in {sorted(betroffen)} seit dem Tageslauf – Tageslauf neu starten, diese Bücher werden nicht gesendet")
    diff = abgleich(journal, list(b["buecher"]), broker.positionen())
    if diff:
        return meldungen + ["Abgleich mit IBKR weicht ab – nichts gesendet: " + "; ".join(diff)]
    meldungen.append(f"Abgleich vor dem Senden: Bestände aller Bücher stimmen mit IBKR überein ({_bestand_text(journal, b)})")
    offene_liste = broker.offene_orders()
    offene = [(o.order_ref.split(":")[0], o.ticker, o.richtung) for o in offene_liste]
    gesendet = journal.gesendete_refs()
    stand = {}                                                                     # Kasse je Buch und Währung im Durchgang
    reihenfolge = lambda z: (z["buch"], 1 if z["art"] == "fx" else (0 if z["richtung"] < 0 else 2))   # noqa: E731 – Verkäufe, Tausch, Käufe
    for z in sorted(freigegeben, key=reihenfolge):
        weiter()
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
            antwort = broker.sende(auftrag, gesendet)
        except KontraktUnbekannt as f:
            journal.status_setzen(z["id"], "veto", meldung=str(f))
            journal.ereignis("veto", f"{z['id']}: {f}", z["buch"])
            meldungen.append(f"{z['id']}: Veto „Kontrakt unbekannt“ – {f}")
            continue
        except SendenGesperrt as f:
            meldungen.append(f"{z['id']}: nicht gesendet – {f}")
            continue
        if isinstance(antwort, str):                                   # ältere Adapter/Attrappen: Order-ID = angenommen
            antwort = SendeErgebnis(antwort, "angenommen")
        if ist_read_only_ablehnung(antwort.text):
            # Read-Only erst während des Sendens (Prüfung davor bestanden): abbrechen, nichts weiter übergeben
            journal.status_setzen(z["id"], "abgelehnt", order_id=antwort.order_id, meldung=antwort.text)
            journal.ereignis("abgelehnt", f"{z['id']} (Order {antwort.order_id}): {antwort.text}", z["buch"])
            return meldungen + [f"{z['id']}: von IBKR ABGELEHNT – {antwort.text}", f"{READ_ONLY_MELDUNG}. Senden abgebrochen, "
                                "die übrigen Freigaben wurden nicht übergeben."]
        if antwort.status == "abgelehnt":
            journal.status_setzen(z["id"], "abgelehnt", order_id=antwort.order_id, meldung=antwort.text)
            journal.ereignis("abgelehnt", f"{z['id']} (Order {antwort.order_id}): {antwort.text}", z["buch"])
            opg = " – Limit-On-Open (OPG) nicht angenommen; kein Ersatz-Ordertyp ohne Jakobs Zustimmung" if (
                z["art"] == "aktie" and not z["ticker"].endswith(".DE") and z["richtung"] > 0) else ""
            meldungen.append(f"{z['id']}: von IBKR ABGELEHNT (Order {antwort.order_id}) – {antwort.text}{opg}")
            continue
        if antwort.status == "unbestaetigt":
            journal.status_setzen(z["id"], "unbestaetigt", order_id=antwort.order_id, meldung=antwort.text, jetzt=jetzt)
            journal.ereignis("unbestaetigt", f"{z['id']} (Order {antwort.order_id}): {antwort.text}", z["buch"])
            meldungen.append(f"{z['id']}: UNBESTÄTIGT (Order {antwort.order_id}) – {antwort.text}; bitte im Gateway/Client Portal prüfen")
        else:
            journal.status_setzen(z["id"], "gesendet", order_id=antwort.order_id, meldung=antwort.text or None, jetzt=jetzt)
            if buch_freigeschaltet(b, z["buch"]):
                journal.messbeginn_setzen(z["buch"], jetzt, "erste von IBKR angenommene Order")
        risk.verbuchen(v, k)
        stand[z["buch"]] = (k.kasse, k.kasse_je_waehrung)
        offene.append((z["buch"], z["ticker"], z["richtung"]))
        if antwort.status != "unbestaetigt":
            meldungen.append(f"{z['id']}: von IBKR angenommen (Order {antwort.order_id}, {antwort.text}" + (f", conId {antwort.con_id})" if antwort.con_id else ")"))
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
