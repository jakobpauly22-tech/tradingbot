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
        wurzel.title("Trading-Bot – " + ("PROBELAUF (nichts wird gesendet)" if probe else "Tageslauf (Paper)"))
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

        # Kopfzeile oben
        kopf = tk.Frame(wurzel)
        kopf.pack(side="top", fill="x", padx=8, pady=4)
        modus = "PROBE – sendet nie, kein Messbeginn" if probe else ("Senden AN" if betrieb["ibkr"].get("senden_freigeschaltet") else "Senden AUS (nur Freigabe)")
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
        if bk["freigabe"] == "sammel" and frei:
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
            v = bv.vorschlag
            text = (f"{'TAUSCH' if v.art == 'fx' else ('KAUF' if v.richtung > 0 else 'VERKAUF')} {v.stueck} × {v.ticker}  "
                    f"{('Limit %.2f %s' % (bv.limit_order, bv.waehrung)) if bv.limit_order else 'ohne Limit'}  ≈ {v.orderwert:,.2f} €  "
                    f"{'' if u.frei else 'VETO: ' + '; '.join(u.gruende)}")
            if bk["freigabe"] == "einzeln" and u.frei:
                var = tk.BooleanVar(value=False)
                var.trace_add("write", lambda *a: self._zaehlen())
                self.auswahl[v.id] = var
                tk.Checkbutton(inhalt, text=text, variable=var, anchor="w", justify="left").pack(anchor="w")
            else:
                tk.Label(inhalt, text=text, anchor="w", justify="left", fg="black" if u.frei else "gray").pack(anchor="w")
            tk.Label(inhalt, text="   These: " + v.these + ("   Hinweise: " + "; ".join(u.hinweise) if u.hinweise else ""),
                     wraplength=1000, justify="left", fg="#444").pack(anchor="w")

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
        if not messagebox.askyesno("Freigabe bestätigen", f"{len(ids)} Vorschläge freigeben" + ("" if self.probe else " und senden") + "?"):
            return
        meldungen = self.senden_fn(ids)
        self.protokoll.insert("end", "\n".join(meldungen) + "\n")
        self.protokoll.see("end")
