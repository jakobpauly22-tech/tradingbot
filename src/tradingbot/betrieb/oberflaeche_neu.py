"""Neue Oberfläche des Tageslaufs (Jakob 10.11.2026, Variante A: Tkinter mit ttk, Theme sv-ttk falls installiert).

Aufbau (Priorität von oben):
1. Kopfzeile mit Ampel: Gateway, Schreibzugriff (Read-Only), Freigabefenster, Uhrzeit US/FX, letzter Tageslauf
   (gelb bei verpassten Handelstagen), Datenstand, Senden je Buch; Probe-Modus als breites Band. „Status prüfen“ prüft
   Gateway und Schreibzugriff neu (sonst nur beim Start).
2. Reiter „Übersicht“: je Buch Buchwert (wie gebucht / mit Modellgebühr), Kasse je Währung, Entwicklung seit Messbeginn
   gegen SPYI (TWR), Positionen (einklappbar), offene Orders.
3. Reiter „Vorschläge“: Tabelle (Buch, Kauf/Verkauf, Stück, Titel, Limit, Wert, Kurz-These, Veto) mit Detailbereich.
4. Reiter „Protokoll“: Meldungen farbig (ok / Hinweis / Fehler).
Die Fußleiste mit Auswahlzähler und „Freigeben und senden“ ist immer sichtbar. Bei Read-Only ist der Knopf gesperrt, bis
„Status prüfen“ grün zeigt.

Nur Darstellung: Daten aus betrieb/ansicht.py, Freigabe und Senden über `senden_fn` (tageslauf.freigeben_und_senden,
unverändert). Die alte Oberfläche (betrieb/oberflaeche.py, Tageslauf.bat) bleibt Reserve, bis Jakob umstellt.
"""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from tradingbot.betrieb import ansicht

FARBEN_MELDUNG = {"ok": "#2e7d32", "hinweis": "#b26a00", "fehler": "#c62828", "info": "#333333"}
# Farben gezielt und ruhig (Jakob 10.11.2026): Aktion als Schriftfarbe, Status als Hintergrund der Zeile (ttk.Treeview kann
# einzelne Zellen nicht färben), Veto hellrot hinterlegt.
FARBE_AKTION = {"KAUF": "#2e7d32", "VERKAUF": "#c62828", "TAUSCH": "#1565c0"}
FARBE_STATUS = {"veto": "#fde7e9", "freigegeben": "#fff8e1", "gesendet": "#e3f2fd", "unbestaetigt": "#fff3e0", "ausgefuehrt": "#e8f5e9",
                "abgelehnt": "#eeeeee", "verfallen": "#eeeeee", "abgelaufen": "#eeeeee", "ersetzt": "#eeeeee"}
FARBE_AMPEL = {"gruen": "#2e7d32", "gelb": "#f9a825", "rot": "#c62828", None: "#9e9e9e"}
ORANGE_TEXT = "#b26a00"
SPALTEN = (("wahl", "", 34), ("buch", "Buch", 105), ("art", "Art", 70), ("stueck", "Stück", 55), ("titel", "Titel", 260),
           ("limit", "Limit", 110), ("wert", "Wert €", 90), ("kurz", "Kurz-These", 260), ("veto", "Veto", 140), ("status", "Status", 110))


def theme_setzen(wurzel) -> str:
    """sv-ttk (Sun Valley, hell), falls installiert; sonst eingebautes Theme."""
    try:
        import sv_ttk

        sv_ttk.set_theme("light")
    except Exception:  # noqa: BLE001
        stil = ttk.Style(wurzel)
        stil.theme_use("vista" if "vista" in stil.theme_names() else "clam")
    return ttk.Style(wurzel).theme_use()


class Tagesfenster:
    def __init__(self, wurzel: tk.Tk, erg, journal, betrieb: dict, *, probe: bool, senden_fn, status_fn=None, gateway: dict | None = None,
                 jetzt_fn=datetime.now):
        self.wurzel, self.erg, self.journal, self.betrieb, self.probe = wurzel, erg, journal, betrieb, probe
        self.senden_fn, self.status_fn, self.jetzt_fn = senden_fn, status_fn, jetzt_fn
        self.gateway = gateway or {"verbunden": False, "schreiben": None, "grund": "nicht geprüft"}
        self.zeilen = {z.id: z for z in ansicht.vorschlagszeilen(erg, betrieb, probe=probe)}
        self.gewaehlt: set[str] = set()
        self._sendet = False
        self._uhr_id = None
        self.theme = theme_setzen(wurzel)
        wurzel.title("■ PROBE ■ Tageslauf – sendet nie" if probe else "Trading-Bot – Tageslauf (Paper)")
        wurzel.geometry("1400x900")
        wurzel.columnconfigure(0, weight=1)
        wurzel.rowconfigure(3, weight=1)

        # 0. Probe-Band
        if probe:
            self.probe_band = tk.Label(wurzel, text="PROBE – nichts wird gesendet, kein Messbeginn", bg=ansicht.ORANGE, fg="white",
                                       font=("Segoe UI", 14, "bold"), pady=6)
            self.probe_band.grid(row=0, column=0, sticky="ew")
        # 1. Kopfzeile mit Ampel
        self.kopf = ttk.Frame(wurzel, padding=(8, 6))
        self.kopf.grid(row=1, column=0, sticky="ew")
        self.lampen_rahmen = ttk.Frame(self.kopf)
        self.lampen_rahmen.pack(side="left", fill="x", expand=True)
        rechts = ttk.Frame(self.kopf)
        rechts.pack(side="right", anchor="n")
        ttk.Label(rechts, text=f"Tageslauf {erg.jetzt:%d.%m.%Y %H:%M}", font=("Segoe UI", 11, "bold")).pack(anchor="e")
        self.knopf_status = ttk.Button(rechts, text="Status prüfen", command=self.status_pruefen)
        self.knopf_status.pack(anchor="e", pady=4)
        self.lampen: list[ansicht.Lampe] = []
        if erg.gestoppt:
            tk.Label(wurzel, text="GESTOPPT: " + erg.gestoppt, fg="white", bg=ansicht.ROT, wraplength=1350, justify="left",
                     padx=8, pady=4).grid(row=2, column=0, sticky="ew")

        # 4. Fußleiste (zuerst angelegt, immer sichtbar)
        self.leiste = ttk.Frame(wurzel, padding=(8, 6))
        self.leiste.grid(row=4, column=0, sticky="ew")
        self.auswahl_text = tk.StringVar(value="0 Vorschläge ausgewählt")
        ttk.Label(self.leiste, textvariable=self.auswahl_text, font=("Segoe UI", 11)).pack(side="left")
        self.hinweis_text = tk.StringVar(value="")
        self.hinweis = tk.Label(self.leiste, textvariable=self.hinweis_text, fg=ansicht.ROT, font=("Segoe UI", 10, "bold"))
        self.hinweis.pack(side="left", padx=12)
        ttk.Button(self.leiste, text="Schließen", command=self.schliessen).pack(side="right")
        wurzel.protocol("WM_DELETE_WINDOW", self.schliessen)
        self.knopf_freigabe = ttk.Button(self.leiste, text="Freigeben (Probe)" if probe else "Freigeben und senden", command=self.senden)
        self.knopf_freigabe.pack(side="right", padx=8)

        # Reiter
        self.reiter = ttk.Notebook(wurzel)
        self.reiter.grid(row=3, column=0, sticky="nsew", padx=8)
        self.seite_uebersicht = ttk.Frame(self.reiter)
        self.seite_vorschlaege = ttk.Frame(self.reiter)
        self.seite_protokoll = ttk.Frame(self.reiter)
        self.reiter.add(self.seite_uebersicht, text="Übersicht")
        self.reiter.add(self.seite_vorschlaege, text=f"Vorschläge ({len(self.zeilen)})")
        self.reiter.add(self.seite_protokoll, text="Protokoll")
        self._uebersicht_bauen()
        self._vorschlaege_bauen()
        self._protokoll_bauen()
        self._lampen_zeichnen()
        self._knopf_aktualisieren()
        self._uhr()

    # --- 1. Ampel --------------------------------------------------------------------------------------------------------
    def _lampen_zeichnen(self):
        for w in self.lampen_rahmen.winfo_children():
            w.destroy()
        self.lampen = ansicht.ampel(self.erg, self.journal, self.betrieb, probe=self.probe, gateway=self.gateway, jetzt=self.jetzt_fn())
        self.lampen_widgets: dict[str, tk.Label] = {}
        haupt = [la for la in self.lampen if not la.name.startswith("Senden ")]
        buecher = [la for la in self.lampen if la.name.startswith("Senden ")]
        for i, la in enumerate(haupt):
            zeile, spalte = divmod(i, 2)
            rahmen = ttk.Frame(self.lampen_rahmen)
            rahmen.grid(row=zeile, column=spalte, sticky="w", padx=(0, 18), pady=1)
            tk.Label(rahmen, text="●", fg=la.farbe, font=("Segoe UI", 13)).pack(side="left")
            ttk.Label(rahmen, text=f"{la.name}:", font=("Segoe UI", 9, "bold")).pack(side="left")
            w = tk.Label(rahmen, text=la.text, fg="#222", font=("Segoe UI", 9), wraplength=520, justify="left")
            w.pack(side="left", padx=4)
            self.lampen_widgets[la.name] = w
        zeile_b = ttk.Frame(self.lampen_rahmen)
        zeile_b.grid(row=(len(haupt) + 1) // 2, column=0, columnspan=2, sticky="w", pady=(3, 0))
        ttk.Label(zeile_b, text="Senden:", font=("Segoe UI", 9, "bold")).pack(side="left")
        for la in buecher:
            tk.Label(zeile_b, text=f"● {la.name.removeprefix('Senden ')} {la.text}", fg=la.farbe, font=("Segoe UI", 9)).pack(side="left", padx=6)

    def lampe(self, name: str) -> ansicht.Lampe | None:
        return next((la for la in self.lampen if la.name == name), None)

    def _uhr(self):
        """Uhrzeit-Hinweise und Freigabefenster alle 30 s neu (ohne Gateway-Abfrage)."""
        try:
            self._lampen_zeichnen()
            self._knopf_aktualisieren()
            self._uhr_id = self.wurzel.after(30_000, self._uhr)
        except tk.TclError:
            pass

    def schliessen(self):
        if self._sendet:                                   # nie mitten im Senden schließen
            messagebox.showinfo("Senden läuft", "Bitte warten, bis das Senden abgeschlossen ist.")
            return
        try:
            self.wurzel.after_cancel(self._uhr_id)
        except Exception:  # noqa: BLE001
            pass
        self.wurzel.destroy()

    def status_pruefen(self):
        """Gateway und Schreibzugriff neu prüfen (nur beim Start und per Knopf, Jakob 10.11.2026)."""
        if self.status_fn is None:
            return
        try:
            self.gateway = self.status_fn()
        except Exception as f:  # noqa: BLE001
            self.gateway = {"verbunden": False, "schreiben": None, "grund": f"Statusprüfung fehlgeschlagen ({type(f).__name__})"}
        self._lampen_zeichnen()
        self._knopf_aktualisieren()
        self._protokoll_schreiben([f"Status geprüft: Gateway {'verbunden' if self.gateway.get('verbunden') else 'nicht verbunden'}, "
                                   f"Schreibzugriff {({True: 'frei', False: 'gesperrt', None: 'nicht geprüft'})[self.gateway.get('schreiben')]}"
                                   + (f" – {self.gateway['grund']}" if self.gateway.get("grund") else "")])

    def _knopf_aktualisieren(self):
        ok, grund = ansicht.senden_erlaubt(self.gateway, self.probe, self.erg.gestoppt)
        self.knopf_freigabe.state(["!disabled"] if ok else ["disabled"])
        self.hinweis_text.set("" if ok else grund)

    # --- 2. Übersicht je Buch --------------------------------------------------------------------------------------------
    def _uebersicht_bauen(self):
        for w in self.seite_uebersicht.winfo_children():
            w.destroy()
        canvas = tk.Canvas(self.seite_uebersicht, highlightthickness=0)
        leiste = ttk.Scrollbar(self.seite_uebersicht, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=leiste.set)
        leiste.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        innen = ttk.Frame(canvas, padding=6)
        fid = canvas.create_window((0, 0), window=innen, anchor="nw")
        innen.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(fid, width=e.width))
        self.uebersicht_canvas = canvas
        self.positionen_rahmen: dict[str, ttk.Frame] = {}
        self.positionen_knoepfe: dict[str, ttk.Button] = {}
        self.differenz_labels: dict[str, tk.Label] = {}
        try:
            karten = ansicht.buchuebersicht(self.journal, self.betrieb, self.erg)
        except Exception as f:  # noqa: BLE001 – Anzeige darf nie den Lauf blockieren
            ttk.Label(innen, text=f"Übersicht nicht verfügbar ({type(f).__name__}: {f})", foreground=ansicht.ROT).pack(anchor="w")
            return
        for k in karten:
            self._karte(innen, k)

    def _karte(self, innen, k: ansicht.BuchKarte):
        rahmen = ttk.LabelFrame(innen, text=f"{k.buch}  ({k.art}, Budget {k.budget:,.0f} €)", padding=6)
        rahmen.pack(fill="x", pady=4)
        wert = "–" if k.wert is None else f"{k.wert:,.2f} € wie gebucht · {k.wert_modell or k.wert:,.2f} € mit Modellgebühr (Stand {k.wert_tag})"
        kasse = ", ".join(f"{w} {b:,.2f}" for w, b in k.kasse.items()) + (
            "  (reserviert: " + ", ".join(f"{w} {b:,.2f}" for w, b in k.reserviert.items()) + ")" if k.reserviert else "")
        if k.messbeginn is None:
            entw = "noch kein Messbeginn"
        else:
            r = "–" if k.rendite is None else f"{k.rendite:+.2%}"
            s = "–" if k.rendite_spyi is None else f"{k.rendite_spyi:+.2%}"
            d = "" if (k.rendite is None or k.rendite_spyi is None) else f", Differenz {(k.rendite - k.rendite_spyi) * 100:+.2f} Pp."
            entw = f"seit Messbeginn {k.messbeginn}: Buch {r} (TWR) gegen SPYI {s} (Kauf und Halten, ohne Kosten){d}"
        for name, text in (("Buchwert", wert), ("Kasse", kasse), ("Entwicklung", entw)):
            z = ttk.Frame(rahmen)
            z.pack(fill="x")
            ttk.Label(z, text=f"{name}:", width=12, font=("Segoe UI", 9, "bold")).pack(side="left")
            ttk.Label(z, text=text.split(", Differenz")[0] if name == "Entwicklung" else text).pack(side="left")
            if name == "Entwicklung" and k.rendite is not None and k.rendite_spyi is not None:
                diff = k.rendite - k.rendite_spyi
                self.differenz_labels[k.buch] = tk.Label(z, text=f"Differenz {diff * 100:+.2f} Pp.", font=("Segoe UI", 9, "bold"),
                                                         fg="#2e7d32" if diff >= 0 else "#c62828")
                self.differenz_labels[k.buch].pack(side="left", padx=6)
        # Positionen (einklappbar, Jakob 10.11.2026)
        kopf = ttk.Frame(rahmen)
        kopf.pack(fill="x", pady=(4, 0))
        tabelle_rahmen = ttk.Frame(rahmen)
        knopf = ttk.Button(kopf, text=f"▸ Positionen ({len(k.positionen)})", width=22)
        knopf.configure(command=lambda: self.positionen_umschalten(k.buch))
        knopf.pack(side="left")
        if k.offene:
            ttk.Label(kopf, text=f"{len(k.offene)} offene Order(s)", foreground="#b26a00").pack(side="left", padx=8)
        self.positionen_rahmen[k.buch], self.positionen_knoepfe[k.buch] = tabelle_rahmen, knopf
        if k.positionen:
            t = ttk.Treeview(tabelle_rahmen, columns=("titel", "stueck", "kauf", "kurs", "wert"), show="headings",
                             height=min(len(k.positionen), 22))
            for c, h, b in (("titel", "Titel", 100), ("stueck", "Stück", 70), ("kauf", "Ø Kaufkurs", 130), ("kurs", "Kurs €", 100),
                            ("wert", "Wert €", 110)):
                t.heading(c, text=h)
                t.column(c, width=b, anchor="e" if c != "titel" else "w")
            for p in k.positionen:
                t.insert("", "end", values=(p.ticker, f"{p.stueck:g}", "–" if p.kaufkurs is None else f"{p.kaufkurs:,.4f} {p.waehrung}",
                                            "–" if p.kurs_eur is None else f"{p.kurs_eur:,.2f}", "–" if p.wert_eur is None else f"{p.wert_eur:,.2f}"))
            t.pack(fill="x")
        if k.offene:
            ttk.Label(tabelle_rahmen, text="Offene Orders", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 0))
            o = ttk.Treeview(tabelle_rahmen, columns=("order", "art", "titel", "stueck", "limit", "status"), show="headings",
                             height=min(len(k.offene), 22))
            for c, h, b in (("order", "Order", 70), ("art", "Art", 80), ("titel", "Titel", 100), ("stueck", "Stück", 70),
                            ("limit", "Limit", 120), ("status", "Status", 110)):
                o.heading(c, text=h)
                o.column(c, width=b)
            for z in k.offene:
                o.insert("", "end", values=(z["order_id"], z["art"], z["ticker"], z["stueck"],
                                            "ohne" if z["limit"] is None else f"{z['limit']:,.2f} {z['waehrung']}", z["status"]))
            o.pack(fill="x")

    def positionen_umschalten(self, buch: str, offen: bool | None = None):
        rahmen, knopf = self.positionen_rahmen[buch], self.positionen_knoepfe[buch]
        sichtbar = rahmen.winfo_manager() != ""
        offen = (not sichtbar) if offen is None else offen
        if offen and not sichtbar:
            rahmen.pack(fill="x")
        elif not offen and sichtbar:
            rahmen.pack_forget()
        knopf.configure(text=("▾ " if offen else "▸ ") + knopf.cget("text")[2:])

    # --- 3. Vorschläge ---------------------------------------------------------------------------------------------------
    def _vorschlaege_bauen(self):
        oben = ttk.Frame(self.seite_vorschlaege, padding=(0, 4))
        oben.pack(fill="x")
        ttk.Label(oben, text="Buch:").pack(side="left")
        self.filter = tk.StringVar(value="alle")
        auswahl = ttk.Combobox(oben, textvariable=self.filter, state="readonly", width=16,
                               values=["alle"] + list(self.betrieb["buecher"]))
        auswahl.pack(side="left", padx=4)
        auswahl.bind("<<ComboboxSelected>>", lambda e: self._tabelle_fuellen())
        ttk.Label(oben, text="Klick auf ☐ oder Leertaste wählt aus. Realbuch einzeln, Skalierungsbücher als Sammelfreigabe "
                             "(ganzes Buch).").pack(side="left", padx=12)
        self.teilung = ttk.PanedWindow(self.seite_vorschlaege, orient="horizontal")
        self.teilung.pack(fill="both", expand=True)
        links = ttk.Frame(self.teilung)
        self.tabelle = ttk.Treeview(links, columns=[c for c, _, _ in SPALTEN], show="headings", selectmode="browse")
        for c, h, b in SPALTEN:
            self.tabelle.heading(c, text=h)
            self.tabelle.column(c, width=b, minwidth=30 if c == "wahl" else 50, anchor="e" if c in ("stueck", "wert") else "w",
                                stretch=c in ("titel", "kurz"))
        for art, farbe in FARBE_AKTION.items():
            self.tabelle.tag_configure(f"art_{art}", foreground=farbe)
        self.tabelle.tag_configure("gesperrt", foreground=ansicht.GRAU)
        for st, farbe in FARBE_STATUS.items():
            self.tabelle.tag_configure(f"st_{st}", background=farbe)
        self.tabelle.tag_configure("gewaehlt", font=("Segoe UI", 9, "bold"))
        rollen = ttk.Scrollbar(links, orient="vertical", command=self.tabelle.yview)
        quer = ttk.Scrollbar(links, orient="horizontal", command=self.tabelle.xview)
        self.tabelle.configure(yscrollcommand=rollen.set, xscrollcommand=quer.set)
        quer.pack(side="bottom", fill="x")
        rollen.pack(side="right", fill="y")
        self.tabelle.pack(side="left", fill="both", expand=True)
        self.teilung.add(links, weight=3)
        # Detailbereich: verschiebbar, Standard ca. 40 %, scrollbar
        rechts = ttk.Frame(self.teilung)
        self.detail_canvas = tk.Canvas(rechts, highlightthickness=0, background="#ffffff")
        d_rollen = ttk.Scrollbar(rechts, orient="vertical", command=self.detail_canvas.yview)
        self.detail_canvas.configure(yscrollcommand=d_rollen.set)
        d_rollen.pack(side="right", fill="y")
        self.detail_canvas.pack(side="left", fill="both", expand=True)
        self.detail_rahmen = tk.Frame(self.detail_canvas, background="#ffffff", padx=10, pady=8)
        did = self.detail_canvas.create_window((0, 0), window=self.detail_rahmen, anchor="nw")
        self.detail_rahmen.bind("<Configure>", lambda e: self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox("all")))
        self.detail_canvas.bind("<Configure>", lambda e: (self.detail_canvas.itemconfigure(did, width=e.width), self._umbruch(e.width)))
        self.teilung.add(rechts, weight=2)
        self._sash_gesetzt = False
        self.teilung.bind("<Configure>", self._sash_setzen)
        self.tabelle.bind("<<TreeviewSelect>>", lambda e: self._detail_zeigen())
        self.tabelle.bind("<Button-1>", self._klick)
        self.tabelle.bind("<space>", lambda e: self.umschalten(self.tabelle.focus()) if self.tabelle.focus() else None)
        self._status_journal = {}
        self._umbruch_breite = 480
        self._tabelle_fuellen()
        self._detail_zeigen()

    def _sash_setzen(self, ereignis):
        """Detailbereich anfangs ca. 40 % der Breite; danach verschiebt Jakob ihn selbst."""
        if not self._sash_gesetzt and ereignis.width > 200:
            self._sash_gesetzt = True
            self.teilung.sashpos(0, int(ereignis.width * 0.6))

    def _umbruch(self, breite):
        self._umbruch_breite = max(250, breite - 40)
        for w in getattr(self, "_umbruch_widgets", []):
            try:
                w.configure(wraplength=self._umbruch_breite)
            except tk.TclError:
                pass

    def _journal_status(self) -> dict[str, str]:
        try:
            return {z["id"]: z["status"] for z in self.journal.vorschlaege()}
        except Exception:  # noqa: BLE001 – Attrappen ohne Vorschläge
            return {}

    def _tabelle_fuellen(self):
        self._status_journal = self._journal_status()
        auswahl = self.tabelle.selection()
        self.tabelle.delete(*self.tabelle.get_children())
        f = self.filter.get()
        for z in self.zeilen.values():
            if f != "alle" and z.buch != f:
                continue
            status = self._status_journal.get(z.id, "veto" if z.veto else "")
            if z.veto:
                status = "veto"
            tags = ["gesperrt" if z.gesperrt else f"art_{z.art}"]
            if status in FARBE_STATUS:
                tags.append(f"st_{status}")
            if z.id in self.gewaehlt:
                tags.append("gewaehlt")
            wahl = ("☑" if z.id in self.gewaehlt else "☐") if z.waehlbar else "–"
            self.tabelle.insert("", "end", iid=z.id, tags=tags, values=(
                wahl, z.buch, z.art, z.stueck, z.titel, z.limit, f"{z.wert:,.2f}", z.kurz, z.veto, status))
        for i in auswahl:
            if self.tabelle.exists(i):
                self.tabelle.selection_set(i)
        self._zaehlen()

    def _klick(self, ereignis):
        if self.tabelle.identify_region(ereignis.x, ereignis.y) == "cell" and self.tabelle.identify_column(ereignis.x) == "#1":
            zeile = self.tabelle.identify_row(ereignis.y)
            if zeile:
                self.umschalten(zeile)

    def umschalten(self, vid: str):
        """Auswahl wie in der alten Oberfläche: nur wählbare Zeilen; Sammelfreigabe wählt alle wählbaren des Buchs."""
        z = self.zeilen.get(vid)
        if z is None or not z.waehlbar:
            return
        gruppe = [x.id for x in self.zeilen.values() if x.buch == z.buch and x.waehlbar] if z.freigabe == "sammel" else [vid]
        if vid in self.gewaehlt:
            self.gewaehlt.difference_update(gruppe)
        else:
            self.gewaehlt.update(gruppe)
        self._tabelle_fuellen()
        if self.tabelle.exists(vid):
            self.tabelle.selection_set(vid)
            self.tabelle.focus(vid)

    # Detailbereich, gegliedert (Jakob 10.11.2026)
    def _abschnitt(self, titel: str, farbe: str = "#333333"):
        tk.Label(self.detail_rahmen, text=titel, font=("Segoe UI", 10, "bold"), fg=farbe, bg="#ffffff", anchor="w").pack(fill="x", pady=(10, 2))

    def _text(self, text: str, farbe: str = "#222222", fett: bool = False, einzug: int = 0):
        w = tk.Label(self.detail_rahmen, text=text, fg=farbe, bg="#ffffff", anchor="w", justify="left", wraplength=self._umbruch_breite,
                     font=("Segoe UI", 9, "bold" if fett else "normal"), padx=einzug)
        w.pack(fill="x")
        self._umbruch_widgets.append(w)
        return w

    def _detail_zeigen(self):
        for w in self.detail_rahmen.winfo_children():
            w.destroy()
        self._umbruch_widgets = []
        self.detail_abschnitte: list[str] = []
        auswahl = self.tabelle.selection()
        z = self.zeilen.get(auswahl[0]) if auswahl else None
        if z is None:
            self._text("Vorschlag in der Tabelle anklicken, um die Details zu sehen.", ansicht.GRAU)
            return
        g = z.gliederung
        # Kopf
        tk.Label(self.detail_rahmen, text=g["titel"], font=("Segoe UI", 13, "bold"), bg="#ffffff", anchor="w").pack(fill="x")
        self._text(g["kopf"], FARBE_AKTION.get(g["art"], "#222222"), fett=True)
        self.detail_abschnitte.append("Kopf")
        if g["veto"]:
            self._abschnitt("Veto", "#c62828")
            for x in g["veto"]:
                self._text(f"• {x}", "#c62828")
            self.detail_abschnitte.append("Veto")
        if g["gesperrt"]:
            self._text("Buch zum Senden nicht freigeschaltet – nicht freigebbar", ansicht.GRAU)
        # Warum
        self._abschnitt("Warum")
        self._text(g["warum"])
        self.detail_abschnitte.append("Warum")
        # Kennzahlen als Tabelle
        if g["kennzahlen"] or g["zahlen"]:
            self._abschnitt("Kennzahlen")
            self.detail_abschnitte.append("Kennzahlen")
            tabelle = tk.Frame(self.detail_rahmen, bg="#ffffff")
            tabelle.pack(fill="x")
            if g["kennzahlen"]:
                for spalte, (kopf, breite) in enumerate((("Kennzahl", 0), ("Wert", 0), ("Branchenmedian", 0), ("", 0))):
                    tk.Label(tabelle, text=kopf, font=("Segoe UI", 9, "bold"), bg="#f5f5f5", anchor="w", padx=4).grid(row=0, column=spalte, sticky="ew")
                for zeile, (name, wert, median, urteil) in enumerate(g["kennzahlen"], start=1):
                    for spalte, text in enumerate((name, wert, median)):
                        tk.Label(tabelle, text=text, bg="#ffffff", anchor="w" if spalte == 0 else "e", padx=4,
                                 font=("Segoe UI", 9)).grid(row=zeile, column=spalte, sticky="ew")
                    zeichen, farbe = ("✓", "#2e7d32") if urteil is True else ("✗", "#c62828") if urteil is False else ("", "#222222")
                    tk.Label(tabelle, text=zeichen, fg=farbe, bg="#ffffff", font=("Segoe UI", 10, "bold"), padx=4).grid(row=zeile, column=3)
                tabelle.columnconfigure(0, weight=1)
            for x in g["zahlen"]:
                self._text(f"• {x}")
        # Filter als Ampel
        if g["filter"]:
            self._abschnitt("Filter")
            self.detail_abschnitte.append("Filter")
            for name, text, farbe in g["filter"]:
                zeile = tk.Frame(self.detail_rahmen, bg="#ffffff")
                zeile.pack(fill="x")
                tk.Label(zeile, text="●", fg=FARBE_AMPEL.get(farbe, "#9e9e9e"), bg="#ffffff", font=("Segoe UI", 12)).pack(side="left")
                tk.Label(zeile, text=f"{name}: {text}", bg="#ffffff", font=("Segoe UI", 9)).pack(side="left")
        # Was dagegen spricht
        self._abschnitt("Was dagegen spricht", ORANGE_TEXT)
        self.detail_abschnitte.append("Was dagegen spricht")
        for x in (g["dagegen"] or ["nichts Besonderes"]):
            self._text(f"• {x}", ORANGE_TEXT)
        # Widerlegt, wenn
        if g["widerlegt"]:
            self._abschnitt("Widerlegt, wenn")
            self._text(g["widerlegt"])
            self.detail_abschnitte.append("Widerlegt, wenn")
        # Technisches, eingeklappt
        if g["technisch"]:
            rahmen = tk.Frame(self.detail_rahmen, bg="#ffffff")
            knopf = ttk.Button(self.detail_rahmen, text="▸ Technisches")
            knopf.pack(anchor="w", pady=(12, 2))
            for x in g["technisch"]:
                tk.Label(rahmen, text=x, fg="#555555", bg="#ffffff", anchor="w", justify="left", wraplength=self._umbruch_breite,
                         font=("Consolas", 8)).pack(fill="x")

            def umschalten():
                if rahmen.winfo_manager():
                    rahmen.pack_forget()
                    knopf.configure(text="▸ Technisches")
                else:
                    rahmen.pack(fill="x", after=knopf)
                    knopf.configure(text="▾ Technisches")
            knopf.configure(command=umschalten)
            self.technisch_rahmen, self.technisch_knopf = rahmen, knopf
            self.detail_abschnitte.append("Technisches")
        self.detail_canvas.yview_moveto(0)

    def detail_text(self) -> str:
        """Sichtbarer Text des Detailbereichs (für Tests)."""
        texte = []

        def sammeln(w):
            for c in w.winfo_children():
                if isinstance(c, tk.Label) and c.winfo_manager():
                    texte.append(c.cget("text"))
                if c.winfo_manager():
                    sammeln(c)
        sammeln(self.detail_rahmen)
        return "\n".join(texte)

    def ausgewaehlt(self) -> list[str]:
        return sorted(self.gewaehlt)

    def _zaehlen(self):
        wert = sum(self.zeilen[i].wert for i in self.gewaehlt)
        self.auswahl_text.set(f"{len(self.gewaehlt)} Vorschläge ausgewählt (≈ {wert:,.2f} €)")

    # --- 4. Protokoll ------------------------------------------------------------------------------------------------------
    def _protokoll_bauen(self):
        oben = ttk.Frame(self.seite_protokoll, padding=(0, 4))
        oben.pack(fill="x")
        self.nur_wichtig = tk.BooleanVar(value=False)
        ttk.Checkbutton(oben, text="nur Hinweise und Fehler", variable=self.nur_wichtig, command=self._protokoll_neu).pack(side="left")
        rahmen = ttk.Frame(self.seite_protokoll)
        rahmen.pack(fill="both", expand=True)
        self.protokoll = tk.Text(rahmen, wrap="word", font=("Consolas", 9))
        rollen = ttk.Scrollbar(rahmen, orient="vertical", command=self.protokoll.yview)
        self.protokoll.configure(yscrollcommand=rollen.set)
        rollen.pack(side="right", fill="y")
        self.protokoll.pack(side="left", fill="both", expand=True)
        for art, farbe in FARBEN_MELDUNG.items():
            self.protokoll.tag_configure(art, foreground=farbe)
        self.meldungen: list[str] = list(self.erg.meldungen) + ([f"GESTOPPT: {self.erg.gestoppt}"] if self.erg.gestoppt else [])
        self._protokoll_neu()

    def _protokoll_neu(self):
        self.protokoll.configure(state="normal")
        self.protokoll.delete("1.0", "end")
        for m in self.meldungen:
            art = ansicht.meldungsart(m)
            if self.nur_wichtig.get() and art not in ("hinweis", "fehler"):
                continue
            self.protokoll.insert("end", m + "\n", art)
        self.protokoll.configure(state="disabled")
        self.protokoll.see("end")

    def _protokoll_schreiben(self, meldungen: list[str]):
        self.meldungen += meldungen
        self._protokoll_neu()

    # --- Senden (unverändert über senden_fn) -----------------------------------------------------------------------------
    def senden(self):
        ids = self.ausgewaehlt()
        if not ids:
            messagebox.showinfo("Freigabe", "Nichts ausgewählt.")
            return
        ok, grund = ansicht.senden_erlaubt(self.gateway, self.probe, self.erg.gestoppt)
        if not ok:
            messagebox.showwarning("Senden gesperrt", grund)
            return
        if self._sendet:
            return
        from tradingbot.betrieb.tageslauf import zeitfenster_hinweis

        gewaehlt = [bv.vorschlag for bv, _ in self.erg.vorschlaege if bv.vorschlag.id in set(ids)]
        hinweis = "\n\n".join(zeitfenster_hinweis(self.jetzt_fn(), gewaehlt))
        if not messagebox.askyesno("Freigabe bestätigen", f"{len(ids)} Vorschläge freigeben" + ("" if self.probe else " und senden") + "?"
                                   + (f"\n\n{hinweis}" if hinweis else "")):
            return
        self._sendet = True
        self.knopf_freigabe.state(["disabled"])
        try:
            meldungen = self.senden_fn(ids)
        except Exception as f:  # noqa: BLE001 – eine Ablehnung oder ein Fehler darf das Fenster nie beenden
            meldungen = [f"Senden abgebrochen ({type(f).__name__}: {f}) – Journal und offene Orders prüfen, Tageslauf neu starten"]
            messagebox.showerror("Senden abgebrochen", meldungen[0])
        finally:
            self._sendet = False
        self._protokoll_schreiben(meldungen)
        self.gewaehlt.clear()
        self._tabelle_fuellen()
        self._uebersicht_bauen()
        if any("Read-Only im Gateway ist aktiv" in m for m in meldungen):
            self.gateway = {**self.gateway, "schreiben": False, "grund": "Read-Only im Gateway ist aktiv"}
            messagebox.showwarning("Read-Only im Gateway", "Read-Only im Gateway ist aktiv – bitte ausschalten und Tageslauf neu starten.")
        self._lampen_zeichnen()
        self._knopf_aktualisieren()
        self.reiter.select(self.seite_protokoll)
