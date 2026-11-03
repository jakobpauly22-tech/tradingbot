"""Freigabefenster mit 50 Vorschlägen: Freigabe-Knopf bleibt sichtbar, Liste scrollt, Auswahl wird gezählt."""
from datetime import datetime

import pandas as pd
import pytest

from tradingbot.betrieb.buecher import BuchVorschlag
from tradingbot.betrieb.tageslauf import Laufergebnis
from tradingbot.konfiguration import lade_konfiguration
from tradingbot.risiko.manager import OrderVorschlag, Urteil

tk = pytest.importorskip("tkinter")


class JournalAttrappe:
    def kasse(self, buch):
        return 10_000.0

    def messbeginn(self, buch):
        return None


def _erg(n=50):
    buecher = ["real", "fundamental_a", "fundamental_b", "crossover", "momentum"]
    vs = []
    for i in range(n):
        buch = buecher[i % len(buecher)]
        v = OrderVorschlag(f"v{i}", pd.Timestamp("2026-11-03"), buch, f"T{i}", 1, 3, 100.0, "aktie", limit=102.0,
                           these="Lange These " * 15)
        vs.append((BuchVorschlag(v, "EUR", 102.0), Urteil(i % 7 != 0, [] if i % 7 else ["Test-Veto"])))
    return Laufergebnis(datetime(2026, 11, 3, 19, 0), vorschlaege=vs, meldungen=["Test"])


@pytest.fixture
def wurzel():
    try:
        w = tk.Tk()
    except tk.TclError:
        pytest.skip("keine Anzeige verfügbar")
    w.withdraw()
    yield w
    w.destroy()


def test_freigabeknopf_sichtbar_und_liste_scrollbar(wurzel):
    from tradingbot.betrieb.oberflaeche import Freigabefenster
    f = Freigabefenster(wurzel, _erg(50), JournalAttrappe(), lade_konfiguration("betrieb"), probe=True, senden_fn=lambda ids: [])
    wurzel.deiconify()
    wurzel.update()
    assert f.knopf_freigabe.winfo_ismapped() and f.knopf_freigabe.winfo_viewable()
    # Knopf liegt im Fenster (nicht herausgedrückt)
    assert f.knopf_freigabe.winfo_y() + f.leiste.winfo_y() + f.knopf_freigabe.winfo_height() <= wurzel.winfo_height()
    region = [float(x) for x in str(f.canvas.cget("scrollregion")).split()]
    assert region[3] > f.canvas.winfo_height()                       # Inhalt höher als der sichtbare Bereich → scrollbar


def test_auswahl_zaehler_und_sammelfreigabe(wurzel):
    from tradingbot.betrieb.oberflaeche import Freigabefenster
    erg = _erg(50)
    f = Freigabefenster(wurzel, erg, JournalAttrappe(), lade_konfiguration("betrieb"), probe=True, senden_fn=lambda ids: [])
    assert f.auswahl_text.get() == "0 Vorschläge ausgewählt"
    sammel = next(var for vid, var in f.auswahl.items() if vid in {bv.vorschlag.id for bv, u in erg.vorschlaege if bv.vorschlag.buch == "crossover"})
    sammel.set(True)
    frei_crossover = sum(1 for bv, u in erg.vorschlaege if bv.vorschlag.buch == "crossover" and u.frei)
    assert f.auswahl_text.get() == f"{frei_crossover} Vorschläge ausgewählt"
    f._alle(False)
    wurzel.update()
    assert all(i.winfo_manager() == "" for i in f.inhalte)



def test_kurzzeile_und_details_aufklappbar(wurzel):
    from tradingbot.betrieb.oberflaeche import Freigabefenster
    erg = _erg(10)
    erg.vorschlaege[0][0].kern = "Trend intakt."
    erg.vorschlaege[0][0].details = "Zahlen:\n  • SMA50 1 €"
    f = Freigabefenster(wurzel, erg, JournalAttrappe(), lade_konfiguration("betrieb"), probe=True, senden_fn=lambda ids: [])
    zeile = Freigabefenster.kurzzeile("real", erg.vorschlaege[0][0], erg.vorschlaege[0][1])
    assert zeile.startswith("real | KAUF 3 × T0 | Limit 102.00 EUR | ≈ 306.00 € | Trend intakt.")
    knopf = f.detail_knoepfe[0]
    knopf.invoke()
    assert knopf.cget("text") == "Details ▾"
    knopf.invoke()
    assert knopf.cget("text") == "Details ▸"
    assert "PROBE" in wurzel.title()


def test_gesperrte_buecher_nicht_auswaehlbar(wurzel):
    from tradingbot.betrieb.oberflaeche import Freigabefenster
    b = lade_konfiguration("betrieb")
    b["ibkr"] = {**b["ibkr"], "senden_freigeschaltet": True}
    b["buecher"] = {n: {**bk, "senden_freigeschaltet": n in ("real", "crossover")} for n, bk in b["buecher"].items()}
    erg = _erg(50)
    f = Freigabefenster(wurzel, erg, JournalAttrappe(), b, probe=False, senden_fn=lambda ids: [])
    buch_von = {bv.vorschlag.id: bv.vorschlag.buch for bv, _ in erg.vorschlaege}
    assert {buch_von[i] for i in f.auswahl} == {"real", "crossover"}
    assert f.modus == "Senden AN für: real, crossover"
