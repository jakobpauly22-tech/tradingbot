"""Fenster für Tageslauf und Freigabe (tkinter), getrennt vom Ablauf, damit es ohne Tageslauf testbar ist.

Aufbau (Korrektur nach Jakobs Test vom 03.11.2026): Knopfleiste und Protokoll werden zuerst unten gepackt und bleiben immer
sichtbar; die Vorschläge liegen in einem scrollbaren Bereich (Canvas, Scrollbar, innerer Rahmen, Mausrad). Je Buch eine
Zusammenfassung (Zahl der Vorschläge, Summe Orderwert, Vetos) mit Ein- und Ausklappen; die Kopfzeile zeigt, wie viele
Vorschläge gerade ausgewählt sind. Freigabe im Realbuch einzeln, in Skalierungsbüchern als Sammelfreigabe je Buch.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext


class Freigabefenster:
    def __init__(self, wurzel: tk.Tk, erg, journal, betrieb: dict, *, probe: bool, senden_fn):
        self.wurzel, self.erg, self.journal, self.betrieb, self.probe, self.senden_fn = wurzel, erg, journal, betrieb, probe, senden_fn
        self.auswahl: dict[str, tk.BooleanVar] = {}
        wurzel.title(("■ PROBE ■ PROBELAUF – nichts wird gesendet, kein Messbeginn" if probe else "Trading-Bot – Tageslauf (Paper)"))
        wurzel.geometry("1100x800")

        # 1. unten zuerst: Knopfleiste, dann Protokoll – bleiben immer sichtbar
        self.leiste = tk.Frame(wurzel)
        self.leiste.pack(side="bottom", fill="x", padx=8, pady=6)
        self.knopf_freigabe = tk.Button(self.leiste, text="Freigeben (Probe)" if probe else "Freigeben und senden", command=self.senden,
                                        state="disabled" if erg.gestoppt else "normal")
        self.knopf_freigabe.pack(side="left")
        tk.Button(self.leiste, text="Alle einklappen", command=lambda: self._alle(False)).pack(side="left", padx=6)
        tk.Button(self.leiste, text="Alle ausklappen", command=lambda: self._alle(True)).pack(side="left")
        tk.Button(self.leiste, text="Schließen", command=wurzel.destroy).pack(side="right")
        self.protokoll = scrolledtext.ScrolledText(wurzel, height=7)
        self.protokoll.pack(side="bottom", fill="x", padx=8, pady=4)
        self.protokoll.insert("end", "\n".join(erg.meldungen) + "\n")

        # Kopfzeile oben; Probe deutlich markiert (Entscheidung Jakob 03.11.2026)
        if probe:
            tk.Label(wurzel, text="PROBE – nichts wird gesendet, kein Messbeginn, eigenes Probe-Journal", bg="#c62828", fg="white",
                     font=("Segoe UI", 14, "bold"), pady=6).pack(side="top", fill="x")
            wurzel.configure(bg="#ffebee")
        kopf = tk.Frame(wurzel, bg="#ffebee" if probe else None)
        kopf.pack(side="top", fill="x", padx=8, pady=4)
        an = [n for n, bk in betrieb["buecher"].items() if betrieb["ibkr"].get("senden_freigeschaltet") and bk.get("senden_freigeschaltet")]
        self.modus = modus = "PROBE – sendet nie, kein Messbeginn" if probe else (f"Senden AN für: {', '.join(an)}" if an else "Senden AUS – nichts freigebbar")
        tk.Label(kopf, text=f"Tageslauf {erg.jetzt:%d.%m.%Y %H:%M} – {modus}", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.auswahl_text = tk.StringVar(value="0 Vorschläge ausgewählt")
        tk.Label(kopf, textvariable=self.auswahl_text, font=("Segoe UI", 11)).pack(side="right")
        if erg.gestoppt:
            tk.Label(wurzel, text=erg.gestoppt, fg="red", wraplength=1050, justify="left").pack(side="top", anchor="w", padx=8)

        # 2. scrollbarer Bereich für die Vorschläge
        bereich = tk.Frame(wurzel)
        bereich.pack(side="top", fill="both", expand=True, padx=8)
        self.canvas = tk.Canvas(bereich, highlightthickness=0)
        leiste_scroll = tk.Scrollbar(bereich, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=leiste_scroll.set)
        leiste_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.innen = tk.Frame(self.canvas)
        self._fenster_id = self.canvas.create_window((0, 0), window=self.innen, anchor="nw")
        self.innen.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._fenster_id, width=e.width))
        wurzel.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))

        self.inhalte: list[tk.Frame] = []
        self.klapp_knoepfe: list[tk.Button] = []
        self.detail_knoepfe: list[tk.Button] = []
        for buch, bk in betrieb["buecher"].items():
            self._buch(buch, bk)
        self._zaehlen()

    # 3. je Buch: Zusammenfassung, Ein-/Ausklappen
    def _buch(self, buch: str, bk: dict):
        vs = [(bv, u) for bv, u in self.erg.vorschlaege if bv.vorschlag.buch == buch]
        frei = [(bv, u) for bv, u in vs if u.frei]
        summe = sum(bv.vorschlag.orderwert for bv, _ in vs)
        vetos = sum(1 for _, u in vs if not u.frei)
        gruppe = tk.LabelFrame(self.innen, text=buch)
        gruppe.pack(fill="x", pady=3)
        zeile = tk.Frame(gruppe)
        zeile.pack(fill="x")
        inhalt = tk.Frame(gruppe)
        knopf = tk.Button(zeile, text="▾", width=2)
        knopf.configure(command=lambda: self._klappen(inhalt, knopf))
        knopf.pack(side="left")
        zusammen = (f"{buch}: {len(vs)} Vorschläge, Orderwert {summe:,.2f} €, {vetos} Vetos – Kasse {self.journal.kasse(buch):,.2f} € – "
                    f"Messbeginn {self.journal.messbeginn(buch) or 'noch nicht'}")
        tk.Label(zeile, text=zusammen, font=("Segoe UI", 10, "bold")).pack(side="left", padx=4)
        gesperrt = not self.probe and not (self.betrieb["ibkr"].get("senden_freigeschaltet") and bk.get("senden_freigeschaltet"))
        if gesperrt:
            tk.Label(zeile, text="zum Senden noch nicht freigeschaltet – nicht freigebbar", fg="#c62828").pack(side="right")
        elif bk["freigabe"] == "sammel" and frei:
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a: self._zaehlen())
            tk.Checkbutton(zeile, text=f"Sammelfreigabe ({len(frei)})", variable=var).pack(side="right")
            for bv, _ in frei:
                self.auswahl[bv.vorschlag.id] = var
        inhalt.pack(fill="x")
        self.inhalte.append(inhalt)
        self.klapp_knoepfe.append(knopf)
        if buch in self.erg.befunde:
            tk.Label(inhalt, text="Datenprüfung: " + "; ".join(self.erg.befunde[buch][:3]), fg="red").pack(anchor="w")
        for bv, u in vs:
            self._vorschlag(inhalt, buch, bk if not gesperrt else {**bk, "freigabe": "gesperrt"}, bv, u)

    @staticmethod
    def kurzzeile(buch: str, bv, u) -> str:
        """Kurzzeile: Buch, Kauf/Verkauf, Stück, Titel, Limit, Orderwert, Kernaussage in einem Satz."""
        v = bv.vorschlag
        art = "TAUSCH" if v.art == "fx" else ("KAUF" if v.richtung > 0 else "VERKAUF")
        limit = f"Limit {bv.limit_order:.2f} {bv.waehrung}" if bv.limit_order else "ohne Limit"
        kern = bv.kern or v.these.split(". ")[0]
        veto = "" if u.frei else "  VETO: " + "; ".join(u.gruende)
        return f"{buch} | {art} {v.stueck} × {v.ticker} | {limit} | ≈ {v.orderwert:,.2f} € | {kern}{veto}"

    def _vorschlag(self, inhalt, buch, bk, bv, u):
        v = bv.vorschlag
        zeile = tk.Frame(inhalt)
        zeile.pack(fill="x", anchor="w")
        text = self.kurzzeile(buch, bv, u)
        if bk["freigabe"] == "einzeln" and u.frei:
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a: self._zaehlen())
            self.auswahl[v.id] = var
            tk.Checkbutton(zeile, text=text, variable=var, anchor="w", justify="left").pack(side="left")
        else:
            tk.Label(zeile, text=text, anchor="w", justify="left", fg="black" if u.frei else "gray").pack(side="left")
        detail = bv.details or v.these
        if u.hinweise:
            detail += "\nHinweise des Risk-Managers: " + "; ".join(u.hinweise)
        rahmen = tk.Frame(inhalt)
        label = tk.Label(rahmen, text=detail, wraplength=1000, justify="left", anchor="w", fg="#333", bg="#f5f5f5")
        label.pack(fill="x", padx=24)
        knopf = tk.Button(zeile, text="Details ▸", relief="flat", fg="#1565c0")

        def umschalten():
            if rahmen.winfo_manager():
                rahmen.pack_forget()
                knopf.configure(text="Details ▸")
            else:
                rahmen.pack(fill="x", anchor="w", after=zeile)
                knopf.configure(text="Details ▾")
        knopf.configure(command=umschalten)
        knopf.pack(side="right")
        self.detail_knoepfe.append(knopf)

    def _klappen(self, inhalt: tk.Frame, knopf: tk.Button, offen: bool | None = None):
        sichtbar = inhalt.winfo_manager() != ""
        offen = (not sichtbar) if offen is None else offen
        if offen and not sichtbar:
            inhalt.pack(fill="x")
        elif not offen and sichtbar:
            inhalt.pack_forget()
        knopf.configure(text="▾" if offen else "▸")

    def _alle(self, offen: bool):
        for inhalt, knopf in zip(self.inhalte, self.klapp_knoepfe):
            self._klappen(inhalt, knopf, offen)

    # 4. Kopfzeile: Zahl der ausgewählten Vorschläge
    def ausgewaehlt(self) -> list[str]:
        return sorted({i for i, var in self.auswahl.items() if var.get()})

    def _zaehlen(self):
        self.auswahl_text.set(f"{len(self.ausgewaehlt())} Vorschläge ausgewählt")

    def senden(self):
        ids = self.ausgewaehlt()
        if not ids:
            messagebox.showinfo("Freigabe", "Nichts ausgewählt.")
            return
        from datetime import datetime

        from tradingbot.betrieb.tageslauf import zeitfenster_hinweis
        gewaehlt = [bv.vorschlag for bv, _ in self.erg.vorschlaege if bv.vorschlag.id in set(ids)]
        hinweis = "\n\n".join(zeitfenster_hinweis(datetime.now(), gewaehlt))
        if not messagebox.askyesno("Freigabe bestätigen", f"{len(ids)} Vorschläge freigeben" + ("" if self.probe else " und senden") + "?"
                                   + (f"\n\n{hinweis}" if hinweis else "")):
            return
        meldungen = self.senden_fn(ids)
        self.protokoll.insert("end", "\n".join(meldungen) + "\n")
        self.protokoll.see("end")
