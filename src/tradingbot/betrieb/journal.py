"""Journal des Paper Tradings je Buch (SQLite im Betriebsbereich, Entscheidungen Jakob 02.11.2026).

Inhalt: Bücher (Startkapital, Messbeginn = Tag der ersten Freigabe), Vorschläge mit Investment-These und Urteil des
Risk-Managers, Freigabe- und Sendestatus, Ausführungen (aus IBKR über orderRef „<Buch>:<Vorschlag-ID>“), Dividenden,
Ereignisse (Datenprüfung, Abgleich, „hätte gesperrt“, Sicherung) und Strategiezustände (JSON).
Bestand und Kasse je Buch werden aus Ausführungen und Dividenden berechnet, nie aus dem Kontostand: Das Paper-Konto
enthält mehrere Bücher und viel Fantasiekapital. Kontonummern nur gekürzt („DUR3…“).

Status eines Vorschlags: vorgeschlagen → freigegeben → gesendet → ausgefuehrt | verfallen; oder veto / abgelaufen.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS buecher (buch TEXT PRIMARY KEY, startkapital REAL NOT NULL, messbeginn TEXT);
CREATE TABLE IF NOT EXISTS vorschlaege (
    id TEXT PRIMARY KEY, erstellt TEXT NOT NULL, signaltag TEXT NOT NULL, buch TEXT NOT NULL, ticker TEXT NOT NULL,
    art TEXT NOT NULL, waehrung TEXT NOT NULL, richtung INTEGER NOT NULL, stueck INTEGER NOT NULL, limit_preis REAL,
    letzter_kurs_eur REAL NOT NULL, stop REAL, these TEXT, frei INTEGER NOT NULL, gruende TEXT, hinweise TEXT,
    status TEXT NOT NULL, freigabe_bis TEXT NOT NULL, order_id TEXT, aktualisiert TEXT);
CREATE TABLE IF NOT EXISTS ausfuehrungen (
    exec_id TEXT PRIMARY KEY, order_ref TEXT NOT NULL, buch TEXT NOT NULL, ticker TEXT NOT NULL, richtung INTEGER NOT NULL,
    stueck REAL NOT NULL, preis_eur REAL NOT NULL, gebuehr_eur REAL NOT NULL, zeit TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dividenden (buch TEXT, ticker TEXT, ex_tag TEXT, stueck REAL, betrag_eur REAL, PRIMARY KEY (buch, ticker, ex_tag));
CREATE TABLE IF NOT EXISTS ereignisse (zeit TEXT NOT NULL, art TEXT NOT NULL, buch TEXT, text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS zustand (buch TEXT PRIMARY KEY, json TEXT NOT NULL, aktualisiert TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS buchwerte (buch TEXT, tag TEXT, wert REAL, kasse REAL, PRIMARY KEY (buch, tag));
CREATE TABLE IF NOT EXISTS kassenbuchungen (
    beleg_id TEXT NOT NULL, buch TEXT NOT NULL, art TEXT NOT NULL, ticker TEXT, conid INTEGER, action_id TEXT, ex_tag TEXT,
    zahltag TEXT, waehrung TEXT NOT NULL, betrag REAL NOT NULL, betrag_eur REAL NOT NULL, stueck REAL, satz REAL, steuer TEXT,
    quelle TEXT, gebucht TEXT NOT NULL, PRIMARY KEY (beleg_id, buch));
CREATE TABLE IF NOT EXISTS kapitalmassnahmen (
    beleg_id TEXT NOT NULL, buch TEXT NOT NULL, code TEXT, art TEXT NOT NULL, tag TEXT, beschreibung TEXT, status TEXT NOT NULL,
    steuer TEXT, quelle TEXT, erkannt TEXT NOT NULL, aktualisiert TEXT, PRIMARY KEY (beleg_id, buch));
CREATE TABLE IF NOT EXISTS kapitalmassnahmen_posten (
    beleg_id TEXT NOT NULL, buch TEXT NOT NULL, nr INTEGER NOT NULL, ticker TEXT, conid INTEGER, symbol TEXT, isin TEXT,
    stueck REAL NOT NULL DEFAULT 0, waehrung TEXT, betrag REAL NOT NULL DEFAULT 0, betrag_eur REAL NOT NULL DEFAULT 0,
    einstand REAL, einstand_eur REAL, angeschafft TEXT, PRIMARY KEY (beleg_id, buch, nr));
CREATE TABLE IF NOT EXISTS conid_vorschlaege (conid INTEGER PRIMARY KEY, symbol TEXT, isin TEXT, waehrung TEXT, ticker_vorschlag TEXT,
    beleg_id TEXT, status TEXT NOT NULL, erstellt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tausche (exec_id TEXT PRIMARY KEY, order_ref TEXT, buch TEXT, von TEXT, nach TEXT, betrag_von REAL,
    betrag_nach REAL, gebuehr_eur REAL, zeit TEXT);
"""


def konto_kurz(konto_id: str) -> str:
    return f"{konto_id[:4]}…" if konto_id else ""


class Journal:
    def __init__(self, datei: Path):
        self.datei = Path(datei)
        self.datei.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.datei)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        v_spalten = {z["name"] for z in self.db.execute("PRAGMA table_info(vorschlaege)")}
        for name in ("kern", "details", "meldung"):
            if name not in v_spalten:
                self.db.execute(f"ALTER TABLE vorschlaege ADD COLUMN {name} TEXT")
        spalten = {z["name"] for z in self.db.execute("PRAGMA table_info(ausfuehrungen)")}
        for name, typ in (("waehrung", "TEXT DEFAULT 'EUR'"), ("preis", "REAL"), ("gebuehr", "REAL"), ("gebuehr_waehrung", "TEXT"), ("boerse", "TEXT"),
                          ("gebuehr_ibkr", "REAL"), ("gebuehr_ibkr_waehrung", "TEXT"), ("gebuehr_modell_eur", "REAL"),
                          ("eroeffnung", "REAL"), ("quelle", "TEXT"), ("gebuehr_angenommen", "INTEGER DEFAULT 0")):
            if name not in spalten:                                   # ältere Journale ergänzen
                self.db.execute(f"ALTER TABLE ausfuehrungen ADD COLUMN {name} {typ}")
        t_spalten = {z["name"] for z in self.db.execute("PRAGMA table_info(tausche)")}
        for name, typ in (("gebuehr_ibkr", "REAL"), ("gebuehr_ibkr_waehrung", "TEXT"), ("gebuehr_modell_eur", "REAL"), ("quelle", "TEXT")):
            if name not in t_spalten:
                self.db.execute(f"ALTER TABLE tausche ADD COLUMN {name} {typ}")
        # Nachträge vom 09.11.2026 (Weg über die Position) tragen eine angenommene Gebühr (Jakob 09.11.2026)
        self.db.execute("UPDATE ausfuehrungen SET gebuehr_angenommen=1 WHERE quelle LIKE 'IBKR Position (Einstand)%' "
                        "AND COALESCE(gebuehr_angenommen, 0)=0")
        if "wert_modell" not in {z["name"] for z in self.db.execute("PRAGMA table_info(buchwerte)")}:
            self.db.execute("ALTER TABLE buchwerte ADD COLUMN wert_modell REAL")
        self.db.commit()

    def schliessen(self):
        self.db.close()

    # --- Bücher --------------------------------------------------------------------------------------------
    def buch_anlegen(self, buch: str, startkapital: float):
        self.db.execute("INSERT OR IGNORE INTO buecher (buch, startkapital) VALUES (?, ?)", (buch, startkapital))
        self.db.commit()

    def messbeginn(self, buch: str) -> str | None:
        z = self.db.execute("SELECT messbeginn FROM buecher WHERE buch=?", (buch,)).fetchone()
        return z["messbeginn"] if z else None

    def startkapital(self, buch: str) -> float:
        return float(self.db.execute("SELECT startkapital FROM buecher WHERE buch=?", (buch,)).fetchone()["startkapital"])

    # --- Bestand und Kasse ---------------------------------------------------------------------------------
    # gebuchte Posten von Kapitalmaßnahmen (A1, Jakob 12.11.2026): Stückänderungen, Barkomponente, übertragener Einstand
    _POSTEN_GEBUCHT = ("FROM kapitalmassnahmen_posten p JOIN kapitalmassnahmen k ON k.beleg_id=p.beleg_id AND k.buch=p.buch "
                       "WHERE p.buch=? AND k.status='gebucht'")

    def bestand(self, buch: str) -> dict[str, float]:
        """Bestand je Titel aus Ausführungen und gebuchten Kapitalmaßnahmen (Split, Tickerwechsel, Übernahme, Abspaltung)."""
        zeilen = self.db.execute("SELECT ticker, SUM(s) AS s FROM (SELECT ticker, richtung * stueck AS s FROM ausfuehrungen WHERE buch=? "
                                 f"UNION ALL SELECT p.ticker, p.stueck {self._POSTEN_GEBUCHT} AND p.ticker IS NOT NULL) GROUP BY ticker",
                                 (buch, buch))
        return {z["ticker"]: z["s"] for z in zeilen if abs(z["s"]) > 1e-9}

    def massnahmen_posten(self, buch: str, *, bis: str | None = None) -> list[sqlite3.Row]:
        """Gebuchte Posten von Kapitalmaßnahmen des Buchs (optional nur mit Stichtag vor `bis`)."""
        sql, par = f"SELECT p.*, k.tag, k.art {self._POSTEN_GEBUCHT}", [buch]
        if bis is not None:
            sql += " AND k.tag < ?"
            par.append(bis)
        return self.db.execute(sql + " ORDER BY k.tag, p.beleg_id, p.nr", par).fetchall()

    def kasse(self, buch: str) -> float:
        """Kasse des Buchs gesamt in EUR (Fremdwährung zum Kurs der jeweiligen Ausführung bzw. des Tauschs)."""
        handel = self.db.execute("SELECT COALESCE(SUM(-richtung * stueck * preis_eur - gebuehr_eur), 0) AS k FROM ausfuehrungen WHERE buch=?",
                                 (buch,)).fetchone()["k"]
        div = self.db.execute("SELECT COALESCE(SUM(betrag_eur), 0) AS d FROM dividenden WHERE buch=?", (buch,)).fetchone()["d"]
        tausch = self.db.execute("SELECT COALESCE(SUM(gebuehr_eur), 0) AS t FROM tausche WHERE buch=?", (buch,)).fetchone()["t"]
        bar = self.db.execute("SELECT COALESCE(SUM(betrag_eur), 0) FROM kassenbuchungen WHERE buch=?", (buch,)).fetchone()[0]
        massnahmen = self.db.execute(f"SELECT COALESCE(SUM(p.betrag_eur), 0) {self._POSTEN_GEBUCHT}", (buch,)).fetchone()[0]
        return self.startkapital(buch) + handel + div - tausch + bar + massnahmen

    def gebuehren_differenz(self, buch: str) -> float:
        """Gebucht (IBKR) minus Modellgebühr in EUR, über alle Ausführungen und Tausche des Buchs (fehlende Modellwerte = 0)."""
        a = self.db.execute("SELECT COALESCE(SUM(gebuehr_eur - COALESCE(gebuehr_modell_eur, gebuehr_eur)), 0) FROM ausfuehrungen WHERE buch=?",
                            (buch,)).fetchone()[0]
        t = self.db.execute("SELECT COALESCE(SUM(gebuehr_eur - COALESCE(gebuehr_modell_eur, gebuehr_eur)), 0) FROM tausche WHERE buch=?",
                            (buch,)).fetchone()[0]
        return float(a + t)

    def kasse_modell(self, buch: str) -> float:
        """Kasse mit Modellgebühr (Tiered) statt der gebuchten Paper-Gebühr – zweite Kennzahl im Bericht (04.11.2026)."""
        return self.kasse(buch) + self.gebuehren_differenz(buch)

    def kasse_je_waehrung(self, buch: str) -> dict[str, float]:
        """Kasse des Buchs je Währung (keine darf negativ werden, Risk-Manager Regel 10)."""
        kassen = {"EUR": self.startkapital(buch)}
        for z in self.db.execute("SELECT waehrung, richtung, stueck, preis, preis_eur, gebuehr, gebuehr_eur, gebuehr_waehrung FROM ausfuehrungen WHERE buch=?", (buch,)):
            w = z["waehrung"] or "EUR"
            preis = z["preis"] if z["preis"] is not None else z["preis_eur"]
            kassen[w] = kassen.get(w, 0.0) - z["richtung"] * z["stueck"] * preis
            gw = z["gebuehr_waehrung"] or "EUR"
            kassen[gw] = kassen.get(gw, 0.0) - (z["gebuehr"] if z["gebuehr"] is not None and gw != "EUR" else z["gebuehr_eur"])
        for z in self.db.execute("SELECT von, nach, betrag_von, betrag_nach, gebuehr_eur, gebuehr_ibkr, gebuehr_ibkr_waehrung FROM tausche "
                                 "WHERE buch=?", (buch,)):
            kassen[z["von"]] = kassen.get(z["von"], 0.0) - z["betrag_von"]
            kassen[z["nach"]] = kassen.get(z["nach"], 0.0) + z["betrag_nach"]
            gw = z["gebuehr_ibkr_waehrung"] if z["gebuehr_ibkr"] is not None else "EUR"
            if gw and gw != "EUR":                                   # IBKR rechnet die Tauschgebühr in USD ab
                kassen[gw] = kassen.get(gw, 0.0) - z["gebuehr_ibkr"]
            else:
                kassen["EUR"] -= z["gebuehr_eur"]
        kassen["EUR"] += self.db.execute("SELECT COALESCE(SUM(betrag_eur), 0) AS d FROM dividenden WHERE buch=?", (buch,)).fetchone()["d"]
        for z in self.db.execute("SELECT waehrung, SUM(betrag) AS b FROM kassenbuchungen WHERE buch=? GROUP BY waehrung", (buch,)):
            kassen[z["waehrung"]] = kassen.get(z["waehrung"], 0.0) + z["b"]   # Dividenden/Quellensteuer in Originalwährung (A0)
        for z in self.db.execute(f"SELECT p.waehrung, SUM(p.betrag) AS b {self._POSTEN_GEBUCHT} AND p.waehrung IS NOT NULL "
                                 "GROUP BY p.waehrung", (buch,)):
            kassen[z["waehrung"]] = kassen.get(z["waehrung"], 0.0) + z["b"]   # Barkomponente von Kapitalmaßnahmen (A1)
        return kassen

    def tausch(self, exec_id, order_ref, von, nach, betrag_von, betrag_nach, gebuehr_eur, zeit, *, gebuehr_ibkr=None,
               gebuehr_ibkr_waehrung=None, gebuehr_modell_eur=None) -> bool:
        buch, _, vid = order_ref.partition(":")
        neu = self.db.execute("INSERT OR IGNORE INTO tausche (exec_id, order_ref, buch, von, nach, betrag_von, betrag_nach, gebuehr_eur, zeit, "
                              "gebuehr_ibkr, gebuehr_ibkr_waehrung) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                              (exec_id, order_ref, buch, von, nach, betrag_von, betrag_nach, gebuehr_eur, str(zeit), gebuehr_ibkr,
                               gebuehr_ibkr_waehrung)).rowcount > 0
        if neu and gebuehr_modell_eur is not None:
            self.db.execute("UPDATE tausche SET gebuehr_modell_eur=? WHERE exec_id=?", (gebuehr_modell_eur, exec_id))
        if neu:
            self.status_setzen(vid, "ausgefuehrt")
        self.db.commit()
        return neu

    # --- Vorschläge ----------------------------------------------------------------------------------------
    def vorschlag_speichern(self, v, urteil, *, waehrung: str, freigabe_bis: str, limit_order: float | None = None,
                            jetzt: datetime | None = None, kern: str = "", details: str = ""):
        """Speichert Vorschlag und Urteil; `limit_order` = Limit in der Handelswährung (sonst das EUR-Limit)."""
        jetzt = (jetzt or datetime.now()).isoformat(timespec="seconds")
        alt = self.db.execute("SELECT status FROM vorschlaege WHERE id=?", (v.id,)).fetchone()
        # „abgelehnt“ = nie bei IBKR angekommen: darf neu vorgeschlagen werden (Jakob 03.11.2026)
        if alt is not None and alt["status"] not in ("vorgeschlagen", "veto", "ersetzt", "abgelaufen", "abgelehnt"):
            return                                       # schon freigegeben oder gesendet: nicht überschreiben
        status = "vorgeschlagen" if urteil.frei else "veto"
        self.db.execute(
            "INSERT OR REPLACE INTO vorschlaege (id, erstellt, signaltag, buch, ticker, art, waehrung, richtung, stueck, limit_preis, "
            "letzter_kurs_eur, stop, these, frei, gruende, hinweise, status, freigabe_bis, order_id, aktualisiert) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (v.id, jetzt, str(v.datum.date()), v.buch, v.ticker, v.art, waehrung, v.richtung, v.stueck,
             limit_order if limit_order is not None else v.limit, v.letzter_kurs,
             v.stop, v.these, int(urteil.frei), json.dumps(urteil.gruende, ensure_ascii=False), json.dumps(urteil.hinweise, ensure_ascii=False),
             status, freigabe_bis, None, jetzt))
        self.db.execute("UPDATE vorschlaege SET kern=?, details=? WHERE id=?", (kern, details, v.id))
        for hinweis in urteil.hinweise:
            if hinweis.startswith("hätte gesperrt"):
                self.ereignis("haette_gesperrt", hinweis, v.buch)
        self.db.commit()

    def vorschlaege(self, *, status: tuple[str, ...] | None = None, buch: str | None = None) -> list[sqlite3.Row]:
        sql, par = "SELECT * FROM vorschlaege WHERE 1=1", []
        if status:
            sql += f" AND status IN ({','.join('?' * len(status))})"
            par += list(status)
        if buch:
            sql += " AND buch=?"
            par.append(buch)
        return self.db.execute(sql + " ORDER BY buch, richtung, ticker", par).fetchall()

    def status_setzen(self, vorschlag_id: str, status: str, *, order_id: str | None = None, jetzt: datetime | None = None,
                      meldung: str | None = None):
        self.db.execute("UPDATE vorschlaege SET status=?, order_id=COALESCE(?, order_id), meldung=COALESCE(?, meldung), aktualisiert=? WHERE id=?",
                        (status, order_id, meldung, (jetzt or datetime.now()).isoformat(timespec="seconds"), vorschlag_id))
        self.db.commit()

    def messbeginn_setzen(self, buch: str, tag, grund: str = "erste angenommene Order"):
        """Messbeginn eines Buchs, einmalig; seit 03.11.2026 erst mit der ersten von IBKR angenommenen Order."""
        if self.messbeginn(buch) is None:
            tag = pd.Timestamp(tag).date()
            self.db.execute("UPDATE buecher SET messbeginn=? WHERE buch=?", (tag.isoformat(), buch))
            self.ereignis("messbeginn", f"Messbeginn {tag:%d.%m.%Y} ({grund})", buch)
            self.db.commit()

    def nachtraeglich_abgelehnt(self, ids: list[str], text: str) -> list[str]:
        """Korrektur: Orders, die als „gesendet“ im Journal stehen, IBKR aber nie angenommen hat, auf „abgelehnt“ setzen
        (Fehlertext gespeichert, Reservierung entfällt). Bücher ohne verbleibende angenommene Order verlieren ihren
        Messbeginn (Messbeginn erst mit der ersten angenommenen Order, Jakob 03.11.2026). Gibt die betroffenen Bücher zurück."""
        buecher = set()
        for i in ids:
            z = self.db.execute("SELECT buch, status, order_id FROM vorschlaege WHERE id=?", (i,)).fetchone()
            if z is None or z["status"] not in ("gesendet", "unbestaetigt"):
                raise ValueError(f"{i}: nicht als gesendet im Journal (Status {z['status'] if z else 'unbekannt'})")
            self.status_setzen(i, "abgelehnt", meldung=text)
            self.ereignis("abgelehnt", f"{i} (Order {z['order_id']}) nachträglich: {text}", z["buch"])
            buecher.add(z["buch"])
        for b in sorted(buecher):
            angenommen = self.db.execute("SELECT COUNT(*) FROM vorschlaege WHERE buch=? AND status IN ('gesendet','ausgefuehrt')", (b,)).fetchone()[0]
            if angenommen == 0 and self.messbeginn(b) is not None:
                self.messbeginn_zuruecksetzen(b, "keine Order von IBKR angenommen (Korrektur)")
        return sorted(buecher)

    def messbeginn_zuruecksetzen(self, buch: str, grund: str):
        self.db.execute("UPDATE buecher SET messbeginn=NULL WHERE buch=?", (buch,))
        self.ereignis("messbeginn", f"Messbeginn zurückgesetzt: {grund}", buch)
        self.db.commit()

    def freigeben(self, vorschlag_id: str, *, jetzt: datetime | None = None, messbeginn: bool = True):
        """Freigabe durch Jakob; setzt beim ersten Mal den Messbeginn des Buchs – aber nur mit `messbeginn=True`
        (echtes Senden möglich). Freigaben im Probe-Modus oder bei ausgeschaltetem Senden zählen nie (03.11.2026)."""
        jetzt = jetzt or datetime.now()
        z = self.db.execute("SELECT buch, status, freigabe_bis FROM vorschlaege WHERE id=?", (vorschlag_id,)).fetchone()
        if z is None or z["status"] != "vorgeschlagen":
            raise ValueError(f"Vorschlag {vorschlag_id} ist nicht freigebbar (Status {z['status'] if z else 'unbekannt'})")
        if jetzt.isoformat(timespec="seconds") > z["freigabe_bis"]:
            self.status_setzen(vorschlag_id, "abgelaufen", jetzt=jetzt)
            raise ValueError(f"Freigabefenster für {vorschlag_id} ist abgelaufen ({z['freigabe_bis']})")
        self.status_setzen(vorschlag_id, "freigegeben", jetzt=jetzt)
        if messbeginn and self.messbeginn(z["buch"]) is None:
            self.db.execute("UPDATE buecher SET messbeginn=? WHERE buch=?", (jetzt.date().isoformat(), z["buch"]))
            self.ereignis("messbeginn", f"Messbeginn {jetzt.date():%d.%m.%Y} (erste Freigabe)", z["buch"])
            self.db.commit()

    def unterwegs(self, buch: str | None = None) -> list[sqlite3.Row]:
        """Von IBKR angenommene („gesendet“) oder unbestätigte, noch nicht ausgeführte Orders: reservieren Kasse und sperren
        den Titel im Buch. Abgelehnte Orders reservieren nichts."""
        return self.vorschlaege(status=("gesendet", "unbestaetigt"), buch=buch)

    def reserviert(self, buch: str) -> dict[str, float]:
        """Durch Orders unterwegs reservierte Kasse (Jakob 03.11.2026). Käufe: je Währung Stück · Limit · 1,01 (Gebühr
        höchstens 1 %), gesamt in EUR Stück · letzter Kurs · 1,02 · 1,01 (Limit = Vortagesschluss + 2 %). Tausch:
        abgehende EUR (Stück = EUR-Betrag); der Gesamtwert ändert sich durch den Tausch nicht. Gesamt unter „EUR_gesamt“."""
        res: dict[str, float] = {"EUR_gesamt": 0.0}
        for z in self.unterwegs(buch):
            if z["art"] == "fx":
                res["EUR"] = res.get("EUR", 0.0) + z["stueck"]
            elif z["richtung"] > 0:
                res[z["waehrung"]] = res.get(z["waehrung"], 0.0) + z["stueck"] * (z["limit_preis"] or z["letzter_kurs_eur"]) * 1.01
                res["EUR_gesamt"] += z["stueck"] * z["letzter_kurs_eur"] * 1.02 * 1.01
        return res

    def gebuchte_gebuehr(self, order_ref: str) -> tuple[float, float, float]:
        """Bisher je Order (Teilausführungen): (Stück, Kurswert in EUR, Modellgebühr in EUR)."""
        z = self.db.execute("SELECT COALESCE(SUM(stueck),0) s, COALESCE(SUM(stueck*preis_eur),0) w, "
                            "COALESCE(SUM(COALESCE(gebuehr_modell_eur, gebuehr_eur)),0) g "
                            "FROM ausfuehrungen WHERE order_ref=?", (order_ref,)).fetchone()
        return float(z["s"]), float(z["w"]), float(z["g"])

    def nachkauf_kandidaten(self, buch: str, seit) -> set[str]:
        """Titel, deren letzter Kaufvorschlag seit `seit` von IBKR abgelehnt wurde oder verfallen ist, ohne Bestand und ohne
        Order unterwegs (Restfall eines Aufbaus, Jakob 04.11.2026). Ob das Signal noch gilt, prüft das Buch."""
        letzte: dict[str, str] = {}
        for z in self.db.execute("SELECT ticker, status FROM vorschlaege WHERE buch=? AND richtung>0 AND art!='fx' AND signaltag>=? "
                                 "AND status IN ('abgelehnt','verfallen','gesendet','unbestaetigt','ausgefuehrt') ORDER BY signaltag, aktualisiert",
                                 (buch, str(pd.Timestamp(seit).date()))):
            letzte[z["ticker"]] = z["status"]
        bestand = {t for t, s in self.bestand(buch).items() if s > 0}
        unterwegs = {z["ticker"] for z in self.unterwegs(buch)}
        return {t for t, s in letzte.items() if s in ("abgelehnt", "verfallen") and t not in bestand and t not in unterwegs}

    def gesendete_refs(self) -> set[str]:
        return {f"{z['buch']}:{z['id']}" for z in self.db.execute("SELECT buch, id FROM vorschlaege WHERE (order_id IS NOT NULL AND status NOT IN ('abgelehnt','vorgeschlagen','veto','ersetzt','abgelaufen')) "
                                                                      "OR status IN ('gesendet','unbestaetigt','ausgefuehrt','verfallen')")}

    def abgelaufene_markieren(self, jetzt: datetime):
        self.db.execute("UPDATE vorschlaege SET status='abgelaufen', aktualisiert=? WHERE status IN ('vorgeschlagen','freigegeben') AND freigabe_bis < ?",
                        (jetzt.isoformat(timespec="seconds"), jetzt.isoformat(timespec="seconds")))
        self.db.commit()

    # --- Ausführungen und Dividenden --------------------------------------------------------------------------
    def ausfuehrung(self, exec_id, order_ref, ticker, richtung, stueck, preis_eur, gebuehr_eur, zeit, *, waehrung="EUR", preis=None,
                    gebuehr=None, gebuehr_waehrung=None, boerse=None, gebuehr_ibkr=None, gebuehr_ibkr_waehrung=None,
                    gebuehr_modell_eur=None, eroeffnung=None) -> bool:
        """Ausführung ins Journal; `boerse` = Ausführungsplatz laut IBKR (SMART-Routing, Jakob 03.11.2026).

        Gebühren (Jakob 04.11.2026, zweite Entscheidung): `gebuehr_eur`/`gebuehr` sind die gebuchte, tatsächliche IBKR-Gebühr
        (Kasse stimmt mit IBKR überein); `gebuehr_modell_eur` ist die Gebühr laut Kostenmodell (Tiered, 1,25 € Minimum),
        maßgeblich für den späteren Echtbetrieb und die zweite Kennzahl im Bericht. `eroeffnung` = Eröffnungskurs des
        Ausführungstags am Heimatplatz (Xetra bzw. US) in der Handelswährung."""
        buch, _, vid = order_ref.partition(":")
        neu = self.db.execute("INSERT OR IGNORE INTO ausfuehrungen (exec_id, order_ref, buch, ticker, richtung, stueck, preis_eur, gebuehr_eur, zeit, "
                              "waehrung, preis, gebuehr, gebuehr_waehrung) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (exec_id, order_ref, buch, ticker, richtung, stueck, preis_eur, gebuehr_eur, str(zeit), waehrung,
                               preis if preis is not None else preis_eur, gebuehr, gebuehr_waehrung or waehrung)).rowcount > 0
        if neu:
            self.db.execute("UPDATE ausfuehrungen SET boerse=?, gebuehr_ibkr=?, gebuehr_ibkr_waehrung=?, gebuehr_modell_eur=?, eroeffnung=? "
                            "WHERE exec_id=?", (boerse, gebuehr_ibkr, gebuehr_ibkr_waehrung, gebuehr_modell_eur, eroeffnung, exec_id))
            self.status_setzen(vid, "ausgefuehrt")
        self.db.commit()
        return neu

    def quelle_setzen(self, exec_id: str, quelle: str, *, gebuehr_angenommen: bool = False):
        """Beleg einer nachgetragenen Ausführung (betrieb/nachtrag.py, Jakob 09.11.2026); leer = IBKR-API am Ausführungstag.
        `gebuehr_angenommen`: Gebühr nicht von IBKR gemeldet, sondern nach Plan angenommen (Abgleich beim Flex-Abruf)."""
        self.db.execute("UPDATE ausfuehrungen SET quelle=?, gebuehr_angenommen=? WHERE exec_id=?",
                        (quelle, int(gebuehr_angenommen), exec_id))
        self.db.execute("UPDATE tausche SET quelle=? WHERE exec_id=?", (quelle, exec_id))
        self.db.commit()

    def angenommene(self) -> list[sqlite3.Row]:
        """Ausführungen mit angenommener Gebühr (Nachtrag über die Position), offen für den Abgleich mit Flex."""
        return self.db.execute("SELECT * FROM ausfuehrungen WHERE gebuehr_angenommen=1 ORDER BY zeit").fetchall()

    def ausfuehrungen_entfernen(self, exec_ids: list[str]):
        """Nur für den Abgleich angenommener Nachträge: die abgeleitete Zeile wird durch die Flex-Ausführungen ersetzt
        (alt und neu stehen im Ereignis „nachtrag_abgleich“)."""
        for e in exec_ids:
            z = self.db.execute("SELECT gebuehr_angenommen FROM ausfuehrungen WHERE exec_id=?", (e,)).fetchone()
            if z is None or not z["gebuehr_angenommen"]:
                raise ValueError(f"{e}: keine Ausführung mit angenommener Gebühr – wird nicht entfernt")
            self.db.execute("DELETE FROM ausfuehrungen WHERE exec_id=?", (e,))
        self.db.commit()

    def beleg_gebucht(self, beleg_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM kassenbuchungen WHERE beleg_id=? LIMIT 1", (beleg_id,)).fetchone() is not None

    def kassenbuchung(self, **z) -> bool:
        """Bardividende, Ersatzzahlung oder Quellensteuer je Buch aus einem Flex-Beleg (A0, Jakob 12.11.2026); einmal je Beleg und Buch."""
        z.setdefault("gebucht", datetime.now().isoformat(timespec="seconds"))
        spalten = ", ".join(z)
        neu = self.db.execute(f"INSERT OR IGNORE INTO kassenbuchungen ({spalten}) VALUES ({', '.join('?' * len(z))})",
                              tuple(z.values())).rowcount > 0
        self.db.commit()
        return neu

    def kassenbuchungen(self, where: str = "1", params: tuple = ()) -> list[sqlite3.Row]:
        return self.db.execute(f"SELECT * FROM kassenbuchungen WHERE {where} ORDER BY gebucht, beleg_id, buch", params).fetchall()

    # --- Kapitalmaßnahmen (A1, Jakob 12.11.2026) ----------------------------------------------------------------
    def massnahme(self, *, beleg_id: str, buch: str, art: str, status: str = "erkannt", posten: list[dict] = (), **felder) -> bool:
        """Kapitalmaßnahme je Beleg und Buch („_konto“ = Flex-Posten des ganzen Kontos); einmal je Beleg und Buch. Status:
        erkannt → bestätigt → gebucht | abgelehnt. Nur gebuchte Posten zählen in Bestand und Kasse."""
        jetzt = datetime.now().isoformat(timespec="seconds")
        z = {"beleg_id": beleg_id, "buch": buch, "art": art, "status": status, "erkannt": jetzt, "aktualisiert": jetzt, **felder}
        neu = self.db.execute(f"INSERT OR IGNORE INTO kapitalmassnahmen ({', '.join(z)}) VALUES ({', '.join('?' * len(z))})",
                              tuple(z.values())).rowcount > 0
        if neu:
            for nr, pz in enumerate(posten, 1):
                q = {"beleg_id": beleg_id, "buch": buch, "nr": nr, **pz}
                self.db.execute(f"INSERT INTO kapitalmassnahmen_posten ({', '.join(q)}) VALUES ({', '.join('?' * len(q))})", tuple(q.values()))
        self.db.commit()
        return neu

    def massnahmen(self, where: str = "1", params: tuple = ()) -> list[sqlite3.Row]:
        return self.db.execute(f"SELECT * FROM kapitalmassnahmen WHERE {where} ORDER BY tag, beleg_id, buch", params).fetchall()

    def massnahme_posten(self, beleg_id: str, buch: str = "_konto") -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM kapitalmassnahmen_posten WHERE beleg_id=? AND buch=? ORDER BY nr", (beleg_id, buch)).fetchall()

    def massnahme_status(self, beleg_id: str, buch: str, status: str):
        self.db.execute("UPDATE kapitalmassnahmen SET status=?, aktualisiert=? WHERE beleg_id=? AND buch=?",
                        (status, datetime.now().isoformat(timespec="seconds"), beleg_id, buch))
        self.db.commit()

    def conid_vorschlag(self, conid: int, **felder) -> bool:
        """Zuordnung neue Conid → Yahoo-Ticker nur als Vorschlag (Jakob 12.11.2026); config/kontrakte.yaml ändert Jakob selbst."""
        z = {"conid": conid, "status": "offen", "erstellt": datetime.now().isoformat(timespec="seconds"), **felder}
        neu = self.db.execute(f"INSERT OR IGNORE INTO conid_vorschlaege ({', '.join(z)}) VALUES ({', '.join('?' * len(z))})",
                              tuple(z.values())).rowcount > 0
        self.db.commit()
        return neu

    def conid_vorschlaege(self) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM conid_vorschlaege ORDER BY erstellt, conid").fetchall()

    def dividende(self, buch, ticker, ex_tag, stueck, betrag_eur) -> bool:
        neu = self.db.execute("INSERT OR IGNORE INTO dividenden VALUES (?,?,?,?,?)", (buch, ticker, str(ex_tag), stueck, betrag_eur)).rowcount > 0
        self.db.commit()
        return neu

    def buchwert_speichern(self, buch: str, tag, wert: float, kasse: float, wert_modell: float | None = None):
        self.db.execute("INSERT OR REPLACE INTO buchwerte (buch, tag, wert, kasse, wert_modell) VALUES (?,?,?,?,?)",
                        (buch, str(pd.Timestamp(tag).date()), wert, kasse, wert_modell))
        self.db.commit()

    def buchwerte(self, buch: str) -> pd.Series:
        z = self.db.execute("SELECT tag, wert FROM buchwerte WHERE buch=? ORDER BY tag", (buch,)).fetchall()
        return pd.Series({pd.Timestamp(r["tag"]): r["wert"] for r in z}, dtype=float)

    def orders_heute(self, buch: str, tag) -> int:
        return self.db.execute("SELECT COUNT(*) FROM vorschlaege WHERE buch=? AND signaltag=? AND status IN ('freigegeben','gesendet','ausgefuehrt')",
                               (buch, str(pd.Timestamp(tag).date()))).fetchone()[0]

    # --- Ereignisse und Zustände ----------------------------------------------------------------------------
    def ereignis(self, art: str, text: str, buch: str | None = None, *, jetzt: datetime | None = None):
        self.db.execute("INSERT INTO ereignisse VALUES (?,?,?,?)", ((jetzt or datetime.now()).isoformat(timespec="seconds"), art, buch, text))
        self.db.commit()

    def offene_ersetzen(self, *, jetzt: datetime | None = None) -> int:
        """Noch nicht freigegebene Vorschläge (Status „vorgeschlagen“) werden „ersetzt“ und sind nicht mehr freigebbar.
        Jeder Tageslauf ruft das vor dem Speichern neuer Vorschläge auf (Entscheidung Jakob 03.11.2026): Ein zweiter Lauf am
        selben Tag ersetzt den ersten, statt Vorschläge zu addieren. Freigegebene und gesendete bleiben unberührt."""
        n = self.db.execute("UPDATE vorschlaege SET status='ersetzt', aktualisiert=? WHERE status='vorgeschlagen'",
                            ((jetzt or datetime.now()).isoformat(timespec="seconds"),)).rowcount
        self.db.commit()
        return n

    def signaltag_gesendet(self, buch: str, tag) -> bool:
        """Hat eine Order des Buchs vom Signaltag `tag` IBKR erreicht (gesendet, unbestätigt, ausgeführt, verfallen)?"""
        return self.db.execute("SELECT 1 FROM vorschlaege WHERE buch=? AND signaltag=? AND status IN "
                               "('gesendet','unbestaetigt','ausgefuehrt','verfallen') LIMIT 1",
                               (buch, str(pd.Timestamp(tag).date()))).fetchone() is not None

    def _wiederholung(self, buch: str, tag, z: dict) -> bool:
        """Erneuter Lauf am selben Signaltag, dessen Entscheidung noch offen ist (noch keine Order des Tages bei IBKR).
        Korrektur 11.11.2026 (Probelauf 10.11., 11:06): Nach dem Senden ist der Signaltag entschieden; ein erneuter Lauf
        startet vom Stand NACH dem Tag. Sonst sähe er den Stand vor dem Tag zusammen mit den inzwischen ausgeführten Käufen
        und legte Restkasse an (Momentum: zweite Monatsprüfung) – das tut der Backtest nicht."""
        return z["signaltag"] == str(pd.Timestamp(tag).date()) and not self.signaltag_gesendet(buch, tag)

    def zustand_fuer_signaltag(self, buch: str, tag) -> dict:
        """Strategiezustand als Ausgangspunkt für einen Lauf am Signaltag `tag`: bei erneutem Lauf am selben Signaltag der
        Stand VOR diesem Tag (wiederholbar, kein Aufaddieren), solange keine Order des Tages gesendet ist; sonst der Stand
        nach dem letzten Lauf."""
        z = self.zustand(buch)
        if "signaltag" not in z:
            return z                                     # ältere Form: flacher Zustand
        return z["vor"] if self._wiederholung(buch, tag, z) else z["nach"]

    def vorlauf_signaltag(self, buch: str, tag) -> str | None:
        """Signaltag des Laufs, aus dem der Ausgangszustand für `tag` stammt (verpasste Tage dazwischen, Jakob 09.11.2026)."""
        z = self.zustand(buch)
        if "signaltag" not in z:
            return None
        return z.get("vor_signaltag") if self._wiederholung(buch, tag, z) else z["signaltag"]

    def zustand_nach_lauf(self, buch: str, tag, vor: dict, nach: dict):
        alt = self.zustand(buch)
        vor_signaltag = alt.get("signaltag")
        if alt.get("signaltag") == str(pd.Timestamp(tag).date()):
            vor = alt["vor"]                             # der Stand vor dem Tag bleibt der vom ersten Lauf
            vor_signaltag = alt.get("vor_signaltag")
        self.zustand_speichern(buch, {"signaltag": str(pd.Timestamp(tag).date()), "vor": vor, "nach": nach,
                                      "vor_signaltag": vor_signaltag})

    def zustand(self, buch: str) -> dict:
        z = self.db.execute("SELECT json FROM zustand WHERE buch=?", (buch,)).fetchone()
        return json.loads(z["json"]) if z else {}

    def zustand_speichern(self, buch: str, daten: dict):
        self.db.execute("INSERT OR REPLACE INTO zustand VALUES (?,?,?)", (buch, json.dumps(daten, ensure_ascii=False, default=str),
                                                                          datetime.now().isoformat(timespec="seconds")))
        self.db.commit()

    # --- Sicherung ----------------------------------------------------------------------------------------------
    def sichern(self, ziel_ordner: str | None, *, jetzt: datetime | None = None) -> Path | None:
        """Kopie außerhalb des Repos (JOURNAL_BACKUP_DIR); konsistent über die SQLite-Backup-Schnittstelle."""
        ziel_ordner = ziel_ordner if ziel_ordner is not None else os.getenv("JOURNAL_BACKUP_DIR")
        if not ziel_ordner:
            self.ereignis("sicherung", "JOURNAL_BACKUP_DIR nicht gesetzt – keine Sicherung")
            return None
        ordner = Path(ziel_ordner)
        ordner.mkdir(parents=True, exist_ok=True)
        ziel = ordner / f"{self.datei.stem}_{(jetzt or datetime.now()):%Y-%m-%d_%H%M%S}.sqlite"
        n = 1
        while ziel.exists():                                   # nie eine ältere Sicherung überschreiben
            n += 1
            ziel = ziel.with_name(f"{self.datei.stem}_{(jetzt or datetime.now()):%Y-%m-%d_%H%M%S}_{n}.sqlite")
        kopie = sqlite3.connect(ziel)
        with kopie:
            self.db.backup(kopie)
        kopie.close()
        self.ereignis("sicherung", f"Kopie nach {ziel.name}")
        return ziel
