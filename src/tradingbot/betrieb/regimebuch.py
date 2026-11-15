"""Schattenbuch „regime“ im Paper Trading (Jakob 15.11.2026; docs/REGIME.md, Abschnitt 9).

V1 genau aus dem Festlegungs-Commit b628678: Signale, Rohzustand und Haltepflicht kommen unverändert aus
`engines/regime/signale.py` (Prüfsumme im Test). V1 hat den Backtest nicht bestanden; das Buch beobachtet nur und
begründet nie echte Trades.

- Bewertung am letzten Xetra-Handelstag des Monats, nach Börsenschluss; die Order gilt für den nächsten Handelstag.
  Verpasste Abende werden nachgeholt: Die Signale eines Monatsendes nutzen den Wissensstand dieses Tages (ALFRED).
- Protokoll im Journal (Buchzustand `protokoll`, je Monat die vier Signale, Rohzustand und Zustand mit Haltepflicht).
  Für protokollierte Monate gilt das Protokoll. Weicht eine Neuberechnung ab (z. B. geänderte Yahoo-Kurse), wird das
  einmal laut gemeldet und nichts übernommen; das Buch läuft weiter.
- Beim ersten Lauf wird die Vorgeschichte ab der ersten möglichen Bewertung (Kurse ab 2012, wie im Backtest)
  protokolliert und die Position sofort nach dem aktuellen Zustand eingenommen.
- Makrodaten (FRED/ALFRED) werden nur geladen, wenn eine Bewertung ansteht, und liegen im Betriebsbereich. Ohne Daten
  gibt es keinen neuen Zustand: Position bleibt, Meldung, Bewertung am nächsten Abend.
- Orders: „Risiko an“ ohne Bestand → Kauf in ganzen Stücken, Limit = Vortagesschluss + 2 %; „Risiko aus“ mit Bestand →
  Verkauf des ganzen Bestands, Limit = Vortagesschluss − 2 % (aufgerundet). Passt der Bestand nicht zum Zustand und ist
  keine Order unterwegs, kommt der Vorschlag am nächsten Abend wieder. Kasse wird mit 0 % verzinst.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd

from tradingbot.betrieb.buecher import BuchVorschlag, _kauf, _z, details_text, limit_preis, stueck_fuer, vorschlag_id
from tradingbot.betrieb.kalender import ist_handelstag
from tradingbot.engines.regime import signale
from tradingbot.risiko.manager import OrderVorschlag

BUCH = "regime"
VARIANTE = "V1"
FESTLEGUNG = "b628678"
KURSE_AB = "2012-01-01"          # wie im Backtest (Yahoo-Kurse von SPYI.DE davor fehlerhaft)
FELDER = signale.SIGNALE + ("roh_aus",)
SIGNALNAMEN = {"trend_aus": "Trend", "kurve_aus": "Zinskurve", "kredit_aus": "Kreditaufschlag", "arbeit_aus": "Arbeitsmarkt"}
HINWEIS = "V1 hat den Backtest nicht bestanden (docs/REGIME.md); das Buch beobachtet nur und begründet nie echte Trades."


@dataclass
class Stand:
    """Ergebnis einer Bewertung. `risiko_aus`: True/False, None = kein Zustand (keine Orders)."""
    risiko_aus: bool | None = None
    monat: str | None = None                                 # Monat der letzten Bewertung (JJJJ-MM)
    eintrag: dict = field(default_factory=dict)              # Protokolleintrag dieses Monats
    neu: list[str] = field(default_factory=list)             # in diesem Lauf bewertete Monate (ohne Vorgeschichte)
    wechsel: bool = False                                    # Zustand hat in diesem Lauf gewechselt
    start: bool = False                                      # erster Lauf (Vorgeschichte protokolliert)
    meldungen: list[str] = field(default_factory=list)
    laut: list[str] = field(default_factory=list)            # Sofortmeldungen (Ausfall, Abweichung, Wechsel)


def zustand_text(aus: bool | None) -> str:
    return "kein Zustand" if aus is None else ("Risiko aus" if aus else "Risiko an")


def ist_monatsende(tag) -> bool:
    """Letzter Xetra-Handelstag des Kalendermonats (danach folgt im selben Monat kein Handelstag mehr)."""
    d = pd.Timestamp(tag).date()
    monat, d = d.month, d + timedelta(days=1)
    while d.month == monat:
        if ist_handelstag("xetra", d):
            return False
        d += timedelta(days=1)
    return True


def _schluesse(schlusskurse: pd.Series, tag) -> pd.Series:
    c = schlusskurse.dropna().sort_index()
    return c.loc[: pd.Timestamp(tag)]


def faellige_monate(schlusskurse: pd.Series, tag, protokoll: dict) -> list[str]:
    """Abgeschlossene Monate der Kursreihe (bis `tag`) nach dem letzten protokollierten Monat. Ohne Protokoll: alle."""
    c = _schluesse(schlusskurse, tag)
    if c.empty:
        return []
    enden = signale.monatsenden(c.index, letzter_monat_abgeschlossen=ist_monatsende(c.index[-1]))
    monate = [str(e.to_period("M")) for e in enden]
    return [m for m in monate if not protokoll or m > max(protokoll)]


def signale_text(eintrag: dict) -> str:
    return ", ".join(f"{SIGNALNAMEN[s]} {'aus' if eintrag.get(s) else 'an'}" for s in signale.SIGNALE)


def signalwerte(monatsende, schlusskurse: pd.Series, makro) -> dict:
    """Werte und Schwellen der vier Signale am Monatsende, nur zur Anzeige (dieselben Daten und Hilfsfunktionen wie die
    eingefrorenen Signale; entschieden wird allein in `signale.signale_am`)."""
    tag = pd.Timestamp(monatsende).normalize()
    c = schlusskurse.dropna().sort_index().loc[:tag]
    enden = signale.monatsenden(c.index)
    monat = c.loc[enden]
    periode = tag.to_period("M")
    kurve = signale._monatsmittel(makro(signale.REIHEN["kurve"], tag))
    kredit = signale._monatsmittel(makro(signale.REIHEN["kredit"], tag))
    fenster = kredit.reindex(pd.period_range(periode - (signale.KREDIT_MONATE - 1), periode, freq="M"))
    sahm = signale.sahm_wert(makro(signale.REIHEN["arbeit"], tag - pd.Timedelta(days=1)))

    def zahl(x):
        return None if x is None or pd.isna(x) else round(float(x), 4)

    return {"schluss": zahl(monat.iloc[-1]), "schluss_mittel": zahl(monat.iloc[-signale.TREND_MONATE:].mean()),
            "kurve": zahl(kurve.get(periode)), "kredit": zahl(fenster.iloc[-1]), "kredit_mittel": zahl(fenster.mean()), "sahm": zahl(sahm)}


def haltepflicht_bis(protokoll: dict) -> str | None:
    """Monat (JJJJ-MM), an dessen Ende der Zustand frühestens wieder wechseln kann: zwei Monate nach dem letzten Wechsel
    (die erste Bewertung zählt als Wechsel). None, wenn dieser Monat schon bewertet ist (keine Haltepflicht mehr)."""
    monate = sorted(protokoll)
    if not monate:
        return None
    wechsel = monate[0]
    for vor, m in zip(monate, monate[1:]):
        if protokoll[m]["risiko_aus"] != protokoll[vor]["risiko_aus"]:
            wechsel = m
    frei = str(pd.Period(wechsel, "M") + signale.HALTEPFLICHT_MONATE)
    return frei if frei > monate[-1] else None


def seit(protokoll: dict) -> str | None:
    """Monat des letzten Wechsels auf den aktuellen Zustand."""
    monate = sorted(protokoll)
    if not monate:
        return None
    wechsel = monate[0]
    for vor, m in zip(monate, monate[1:]):
        if protokoll[m]["risiko_aus"] != protokoll[vor]["risiko_aus"]:
            wechsel = m
    return wechsel


def _de(x, n=2) -> str:
    return "–" if x is None else f"{x:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def signalzeilen(eintrag: dict) -> list[str]:
    """Die vier Signale mit Wert und Schwelle (Werte fehlen in der Vorgeschichte: dann nur an/aus)."""
    w = eintrag.get("werte") or {}

    def lage(s):
        return "aus" if eintrag.get(s) else "an"

    return [f"Trend {lage('trend_aus')}: Monatsschluss {_de(w.get('schluss'))} gegen 10-Monats-Durchschnitt {_de(w.get('schluss_mittel'))} (aus, wenn darunter)",
            f"Zinskurve {lage('kurve_aus')}: 10 Jahre − 3 Monate im Monatsdurchschnitt {_de(w.get('kurve'))} Pp. (aus, wenn unter 0)",
            f"Kreditaufschlag {lage('kredit_aus')}: Baa − 10 Jahre {_de(w.get('kredit'))} Pp. gegen 10-Monats-Durchschnitt {_de(w.get('kredit_mittel'))} (aus, wenn darüber)",
            f"Arbeitsmarkt {lage('arbeit_aus')}: Sahm-Wert {_de(w.get('sahm'))} Pp. (aus ab 0,50)"]


def karte(zustand: dict, tag) -> list[tuple[str, str]]:
    """Zeilen für die Buchkarte: Zustand, letzte und nächste Bewertung, Haltepflicht, die vier Signale, Hinweis."""
    protokoll = zustand.get("protokoll") or {}
    if not protokoll:
        return [("Regime", "noch keine Bewertung (kein Zustand, Buch bleibt in Kasse)"), ("Hinweis", HINWEIS)]
    monat = max(protokoll)
    e = protokoll[monat]
    halte = haltepflicht_bis(protokoll)
    zeilen = [("Regime", f"{zustand_text(e['risiko_aus'])} seit der Bewertung {seit(protokoll)} (Rohzustand {'aus' if e['roh_aus'] else 'an'})"),
              ("Bewertung", f"letzte {pd.Timestamp(e['monatsende']):%d.%m.%Y}"
                            + (f" (nachgeholt am {pd.Timestamp(e['bewertet_am']):%d.%m.%Y})" if e.get("art") == "nachgeholt" else "")
                            + f", nächste {naechste_bewertung(tag):%d.%m.%Y}"),
              ("Haltepflicht", f"Wechsel frühestens mit der Bewertung {halte}" if halte else "keine (Wechsel mit der nächsten Bewertung möglich)")]
    zeilen += [("Signal", z) for z in signalzeilen(e)]
    return zeilen + [("Hinweis", HINWEIS)]


def kurzzeile(regime: dict) -> str | None:
    """Zeile für die Kurzfassung: nur am Bewertungstag (auch nachgeholt), beim Start oder bei einem Problem."""
    if not regime:
        return None
    if regime.get("fehler"):
        return "Regime: Monatsbewertung nicht möglich – Position bleibt, wird nachgeholt"
    if not (regime.get("neu") or regime.get("start")) or regime.get("risiko_aus") is None:
        return None
    e = regime.get("eintrag") or {}
    art = "Start" if regime.get("start") else ("Wechsel" if regime.get("wechsel") else "unverändert")
    return f"Regime: Bewertung {regime.get('monat')} – {zustand_text(regime['risiko_aus'])} ({art}; {signale_text(e)})"


def fehlende_signale(c: pd.Series, makro) -> str:
    """Diagnose, wenn die eingefrorene Rechnung abbricht: erstes Monatsende nach Beginn, an dem ein Signal nicht bestimmbar
    ist, und das letzte Monatsende der Reihe (nur Text für die Meldung; an den Regeln ändert das nichts)."""
    enden = signale.monatsenden(c.index, letzter_monat_abgeschlossen=ist_monatsende(c.index[-1]))
    monat, begonnen, erster = c.loc[enden], False, None
    for t in enden:
        z = signale.signale_am(t, monat, makro)
        fehlt = [SIGNALNAMEN[k] for k in signale.SIGNALE if z[k] is None]
        if not fehlt:
            begonnen = True
        elif begonnen and erster is None:
            erster = (t, fehlt)
    if erster is None:
        return "kein Signal fehlt"
    text = f"nicht bestimmbar seit {erster[0]:%d.%m.%Y}: {', '.join(erster[1])}"
    return text + (f"; am {enden[-1]:%d.%m.%Y} weiter nicht bestimmbar: {', '.join(fehlt)}" if fehlt else f"; am {enden[-1]:%d.%m.%Y} wieder bestimmbar")


def bewerten(tag, schlusskurse: pd.Series, makro_laden, zustand: dict) -> tuple[dict, Stand]:
    """Zustand des Buchs am Signaltag `tag`. `makro_laden()` liefert den MakroStand und wird nur gerufen, wenn eine
    Bewertung ansteht. Gibt den neuen Buchzustand (fürs Journal) und den Stand zurück. Fehler (keine Makrodaten, Lücke)
    werfen eine Ausnahme; der Aufrufer behält dann den alten Zustand."""
    tag = pd.Timestamp(tag)
    protokoll: dict = dict(zustand.get("protokoll") or {})
    gemeldet = list(zustand.get("abweichungen_gemeldet") or [])
    stand = Stand(start=not protokoll)
    faellig = faellige_monate(schlusskurse, tag, protokoll)
    if faellig:
        c = _schluesse(schlusskurse, tag)
        makro = makro_laden()
        try:
            verlauf = signale.regime_verlauf(c, makro, variante=VARIANTE, letzter_monat_abgeschlossen=ist_monatsende(c.index[-1]))
        except ValueError as f:
            raise ValueError(f"{f}; {fehlende_signale(c, makro)}") from None
        verlauf = verlauf[verlauf["roh_aus"].notna()]
        neu_gerechnet = {str(pd.Timestamp(e).to_period("M")): (pd.Timestamp(e), z) for e, z in verlauf.iterrows()}
        # Protokoll gegen Neuberechnung: das Protokoll gilt, jede Abweichung wird einmal laut gemeldet
        for monat in sorted(set(protokoll) & set(neu_gerechnet)):
            for f in FELDER:
                kennung = f"{monat}:{f}"
                if bool(neu_gerechnet[monat][1][f]) != bool(protokoll[monat][f]) and kennung not in gemeldet:
                    gemeldet.append(kennung)
                    stand.laut.append(f"regime: Neuberechnung weicht vom Protokoll ab ({monat}, {SIGNALNAMEN.get(f, 'Rohzustand')}: "
                                      f"protokolliert {'aus' if protokoll[monat][f] else 'an'}, neu gerechnet "
                                      f"{'aus' if neu_gerechnet[monat][1][f] else 'an'}) – das Protokoll gilt, nichts übernommen; "
                                      "Ursache prüfen (geänderte Kurshistorie?)")
        fehlend = [m for m in faellig if m not in neu_gerechnet]
        if stand.start:
            fehlend = [m for m in fehlend if neu_gerechnet and m > min(neu_gerechnet)]    # Vorlauf ohne Zustand ist in Ordnung
        if fehlend or not neu_gerechnet:
            raise ValueError(f"kein Rohzustand für {', '.join(fehlend) or 'die Kursreihe'} (Signal ohne Daten)")
        vorher = protokoll[max(protokoll)]["risiko_aus"] if protokoll else None
        for monat in [m for m in faellig if m in neu_gerechnet]:
            ende, z = neu_gerechnet[monat]
            if protokoll and pd.Period(monat, "M") != pd.Period(max(protokoll), "M") + 1:
                raise ValueError(f"Lücke im Protokoll zwischen {max(protokoll)} und {monat}")
            protokoll[monat] = {"monatsende": str(ende.date()), **{f: bool(z[f]) for f in FELDER}, "bewertet_am": str(tag.date()),
                                "art": "start" if stand.start else ("bewertung" if ende == tag else "nachgeholt")}
            if not stand.start:
                stand.neu.append(monat)
        # Haltepflicht über die protokollierten Rohzustände (eingefrorene Funktion); protokollierte Monate bleiben unverändert
        monate = sorted(protokoll)
        mit = signale.mit_haltepflicht(pd.Series([protokoll[m]["roh_aus"] for m in monate], index=monate, dtype=object))
        for m in monate:
            protokoll[m].setdefault("risiko_aus", bool(mit[m]))
        stand.wechsel = vorher is not None and protokoll[monate[-1]]["risiko_aus"] != vorher
        for m in ([monate[-1]] if stand.start else stand.neu):          # Werte und Schwellen zur Anzeige (Vorgeschichte: nur der letzte Monat)
            protokoll[m]["werte"] = signalwerte(protokoll[m]["monatsende"], c, makro)
    if protokoll:
        stand.monat = max(protokoll)
        stand.eintrag = protokoll[stand.monat]
        stand.risiko_aus = bool(stand.eintrag["risiko_aus"])
    if stand.start and protokoll:
        stand.meldungen.append(f"regime: Start – Vorgeschichte {min(protokoll)} bis {max(protokoll)} protokolliert ({len(protokoll)} Monate); "
                               f"aktueller Zustand {zustand_text(stand.risiko_aus)} ({signale_text(stand.eintrag)})")
    for monat in stand.neu:
        e = protokoll[monat]
        nach = "" if e["art"] == "bewertung" else f", nachgeholt am {tag:%d.%m.%Y} mit dem Wissensstand vom {pd.Timestamp(e['monatsende']):%d.%m.%Y}"
        stand.meldungen.append(f"regime: Monatsbewertung {monat}{nach}: {zustand_text(e['risiko_aus'])} ({signale_text(e)}; "
                               f"Rohzustand {'aus' if e['roh_aus'] else 'an'})")
    if stand.wechsel:
        stand.laut.append(f"regime: Wechsel auf {zustand_text(stand.risiko_aus)} ({signale_text(stand.eintrag)}) – Vorschlag im Tageslauf. {HINWEIS}")
    neu = {**zustand, "protokoll": protokoll, "variante": VARIANTE, "festlegung": FESTLEGUNG, "abweichungen_gemeldet": gemeldet}
    return neu, stand


def naechste_bewertung(tag) -> pd.Timestamp:
    """Nächster Bewertungstag nach `tag`: letzter Xetra-Handelstag des laufenden oder des nächsten Monats."""
    d = pd.Timestamp(tag).date() + timedelta(days=1)
    while not (ist_handelstag("xetra", d) and ist_monatsende(d)):
        d += timedelta(days=1)
    return pd.Timestamp(d)


def limit_verkauf(kurs: float, abschlag: float) -> float:
    """Verkaufslimit = Vortagesschluss · (1 − Abschlag), auf Cent AUFGERUNDET (nie mehr als der Abschlag unter dem Kurs)."""
    return math.ceil(kurs * (1 - abschlag) * 100 - 1e-9) / 100


def vorschlaege(tag, ticker: str, kurs: float, stand: Stand, bestand: float, kasse_frei: float, aufschlag: float, abschlag: float,
                gebuehr) -> list[BuchVorschlag]:
    """Order zum Zustand: nur wenn der Bestand nicht zum Zustand passt (wie `RegimeStrategie` im Backtest)."""
    if stand.risiko_aus is None:
        return []
    e = stand.eintrag
    zahlen = [f"Zustand seit der Bewertung {stand.monat}: {zustand_text(stand.risiko_aus)} (Rohzustand {'aus' if e.get('roh_aus') else 'an'}, "
              "zwei Monate Haltepflicht nach einem Wechsel)",
              f"Signale am {pd.Timestamp(e['monatsende']):%d.%m.%Y}: {signale_text(e)}",
              "Regel V1: Risiko aus, wenn der Trend aus ist und zugleich Zinskurve, Kreditaufschlag oder Arbeitsmarkt aus zeigen"]
    if stand.risiko_aus and bestand > 0:
        limit = limit_verkauf(kurs, abschlag)
        n = int(bestand)
        these = (f"Regime V1: Risiko aus seit der Bewertung {stand.monat} ({signale_text(e)}) – ganzer Bestand in Kasse (0 %). "
                 "Widerlegt, wenn der Markt ohne Rückgang weiter steigt (Fehlsignal wie 2015/16).")
        v = OrderVorschlag(vorschlag_id(BUCH, tag, ticker, -1), pd.Timestamp(tag), BUCH, ticker, -1, n, float(kurs), "etf", limit=limit, these=these)
        bv = BuchVorschlag(v, "EUR", limit)
        bv.kern = f"Risiko aus: {ticker} ganz verkaufen ({signale_text(e)})."
        bv.details = details_text(zahlen + [f"Kurs {_z(kurs)} €, Verkaufslimit {_z(limit)} € (Vortagesschluss − 2 %, aufgerundet)",
                                            f"{n} Stück ≈ {_z(n * kurs)} €; verfällt das Limit, kommt der Vorschlag am nächsten Abend wieder"],
                                  ["Fehlsignale kosten Rendite und Steuern (Backtest 2015/16)", HINWEIS],
                                  "der Markt ohne Rückgang weiter steigt; Wiedereinstieg frühestens nach zwei Monaten Haltepflicht.")
        return [bv]
    if not stand.risiko_aus and bestand <= 0:
        limit = limit_preis(kurs, aufschlag)
        n = stueck_fuer(kasse_frei, kasse_frei, limit, gebuehr)
        if n <= 0:
            return []
        these = (f"Regime V1: Risiko an seit der Bewertung {stand.monat} ({signale_text(e)}) – Kasse in {n} ganzen Anteilen {ticker} anlegen. "
                 "Widerlegt, wenn der Trend bricht und zugleich ein Makrosignal aus zeigt (nächste Monatsbewertung).")
        bv = _kauf(BUCH, tag, ticker, n, kurs, kurs, "EUR", aufschlag, "etf", these)
        rest = kasse_frei - n * limit - gebuehr(n, n * limit)
        bv.kern = f"Risiko an: Kasse in {ticker} anlegen ({signale_text(e)})."
        bv.details = details_text(zahlen + [f"Kurs {_z(kurs)} €, Limit {_z(limit)} € (Vortagesschluss + 2 %, abgerundet)",
                                            f"{n} Stück ≈ {_z(n * limit)} €, Gebühr {_z(gebuehr(n, n * limit))} €, Restkasse ≈ {_z(rest)} € (0 % Zins)"],
                                  ["Später Einstieg nach einer Erholung möglich (Backtest 2020)", HINWEIS],
                                  "der Trend bricht und zugleich ein Makrosignal aus zeigt (nächste Monatsbewertung).")
        return [bv]
    return []


# --- Standard-Datenquellen (nur im Betriebsmodus) --------------------------------------------------------------------
def daten_betrieb(tag, ticker: str):
    """Schlusskurse ab 2012 (Yahoo, splitbereinigt und damit in sich stimmig) und ein Lader für den Makrostand aus dem
    Betriebsbereich (daten/betrieb/cache/makro, getrennt vom Backtest-Cache). Der Makrostand wird bei jedem Aufruf neu
    von FRED/ALFRED geholt; ein Ausfall wirft eine Ausnahme."""
    from tradingbot.betrieb.speicher import betriebspfad
    from tradingbot.daten.cache import ParquetCache
    from tradingbot.daten.kurse import lade_kurse
    from tradingbot.daten.makro import lade_makro_tabelle, stand_am

    cache = ParquetCache(betriebspfad("cache/makro/x").parent.parent)        # außerhalb des Betriebsmodus gesperrt
    bis = pd.Timestamp(tag).date()
    schluss = lade_kurse(ticker, KURSE_AB, bis, heute=bis + timedelta(days=1))["close"]

    def makro_laden():
        tabellen = {r: lade_makro_tabelle(r, cache=cache, max_alter_stunden=0.0) for r in signale.REIHEN.values()}
        return lambda reihe, stichtag: stand_am(tabellen[reihe], stichtag)

    return schluss, makro_laden
