"""Neue Oberfläche (Jakob 10.11.2026): Ampel bei Read-Only, Knöpfe sichtbar bei vielen Vorschlägen, Auswahl wie bisher,
Senden nur über senden_fn, Fehler beenden das Fenster nie, Positionen einklappbar, Protokoll farbig."""
from datetime import date, datetime

import pandas as pd
import pytest

from test_ansicht import FREI, READ_ONLY, betrieb, erg_mit, journal, vorschlag  # noqa: F401
from tradingbot.betrieb import ansicht

tk = pytest.importorskip("tkinter")


@pytest.fixture
def wurzel():
    try:
        w = tk.Tk()
    except tk.TclError:
        pytest.skip("keine Anzeige verfügbar")
    w.withdraw()
    yield w
    try:
        w.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def dialoge(monkeypatch):
    from tradingbot.betrieb import oberflaeche_neu
    aufrufe = []
    monkeypatch.setattr(oberflaeche_neu.messagebox, "askyesno", lambda *a, **k: True)
    for name in ("showerror", "showwarning", "showinfo"):
        monkeypatch.setattr(oberflaeche_neu.messagebox, name, lambda *a, _n=name, **k: aufrufe.append((_n, a)))
    return aufrufe


def viele(n=200):
    buecher = ["real", "fundamental_a", "fundamental_b", "crossover", "momentum"]
    return [vorschlag(i, buecher[i % 5], f"T{i}.DE", frei=i % 7 != 0) for i in range(n)]


def fenster(wurzel, journal, vs=(), *, probe=False, gateway=FREI, senden_fn=lambda ids: [], status_fn=None, b=None, erg=None):
    from tradingbot.betrieb.oberflaeche_neu import Tagesfenster
    return Tagesfenster(wurzel, erg or erg_mit(vs), journal, b or betrieb(), probe=probe, senden_fn=senden_fn, status_fn=status_fn,
                        gateway=gateway, jetzt_fn=lambda: datetime(2026, 11, 10, 22, 10))


def test_knoepfe_sichtbar_bei_vielen_vorschlaegen(wurzel, journal):
    f = fenster(wurzel, journal, viele(200))
    wurzel.deiconify()
    wurzel.geometry("1200x700")
    f.reiter.select(f.seite_vorschlaege)
    wurzel.update()
    for knopf in (f.knopf_freigabe, f.knopf_status):
        assert knopf.winfo_ismapped() and knopf.winfo_viewable()
    unten = f.leiste.winfo_y() + f.knopf_freigabe.winfo_y() + f.knopf_freigabe.winfo_height()
    assert unten <= wurzel.winfo_height()                                           # Fußleiste im Fenster
    assert len(f.tabelle.get_children()) == 200 and f.tabelle.yview()[1] < 1.0       # Tabelle scrollt
    assert f.theme in ("sun-valley-light", "vista", "clam")


def test_ampel_read_only_sperrt_senden_bis_status_gruen(wurzel, journal, dialoge):
    status = [FREI]
    f = fenster(wurzel, journal, viele(10), gateway=READ_ONLY, status_fn=lambda: status[0])
    assert f.lampe("Schreibzugriff").farbe == ansicht.ROT and f.lampe("Schreibzugriff").text.startswith("Read-Only an")
    assert f.knopf_freigabe.instate(["disabled"]) and f.hinweis_text.get() == ansicht.READ_ONLY_HINWEIS
    f.umschalten("real-0" if f.zeilen["real-0"].waehlbar else "real-5")
    f.senden()                                                                       # Knopf umgangen: trotzdem gesperrt
    assert dialoge[-1][0] == "showwarning"
    f.status_pruefen()
    assert f.lampe("Schreibzugriff").farbe == ansicht.GRUEN and not f.knopf_freigabe.instate(["disabled"]) and f.hinweis_text.get() == ""
    assert "Status geprüft: Gateway verbunden, Schreibzugriff frei" in f.protokoll.get("1.0", "end")


def test_auswahl_einzeln_sammel_veto_gesperrt(wurzel, journal):
    vs = [vorschlag(1, "real", "SPYI.DE"), vorschlag(2, "real", "SPYI.DE"), vorschlag(3, "crossover"), vorschlag(4, "crossover", "IUSA.DE"),
          vorschlag(5, "crossover", "EUNK.DE", frei=False), vorschlag(6, "momentum")]
    f = fenster(wurzel, journal, vs, b=betrieb(alle_an=False) | {"buecher": {**betrieb(alle_an=False)["buecher"],
                                                                              "crossover": {**betrieb()["buecher"]["crossover"]}}})
    f.umschalten("real-1")
    assert f.ausgewaehlt() == ["real-1"]                                            # Realbuch einzeln
    f.umschalten("crossover-3")
    assert f.ausgewaehlt() == ["crossover-3", "crossover-4", "real-1"]             # Sammelfreigabe: ganzes Buch, ohne Veto
    f.umschalten("crossover-5")
    f.umschalten("momentum-6")                                                     # Veto und gesperrtes Buch: nicht wählbar
    assert f.ausgewaehlt() == ["crossover-3", "crossover-4", "real-1"]
    f.umschalten("crossover-4")
    assert f.ausgewaehlt() == ["real-1"]
    assert f.tabelle.set("real-1", "wahl") == "☑" and f.tabelle.set("crossover-5", "wahl") == "–"
    f.tabelle.selection_set("crossover-5")
    wurzel.update()
    assert "VETO: Test-Veto" in f.detail.get("1.0", "end")
    f.filter.set("crossover")
    f._tabelle_fuellen()
    assert set(f.tabelle.get_children()) == {"crossover-3", "crossover-4", "crossover-5"}


def test_senden_ueber_senden_fn_und_fehler_beendet_nie(wurzel, journal, dialoge):
    gesendet = []
    f = fenster(wurzel, journal, viele(10), senden_fn=lambda ids: gesendet.append(ids) or ["real-5: von IBKR angenommen (Order 7)"])
    f.umschalten("real-5")
    f.senden()
    assert gesendet == [["real-5"]] and f.ausgewaehlt() == []
    assert f.protokoll.tag_ranges("ok")                                             # grün markiert
    f.senden_fn = lambda ids: (_ for _ in ()).throw(RuntimeError("Gateway weg"))
    f.umschalten("real-5")
    f.senden()                                                                      # keine Ausnahme
    assert dialoge[-1][0] == "showerror" and "Gateway weg" in f.protokoll.get("1.0", "end") and f.protokoll.tag_ranges("fehler")
    f.senden_fn = lambda ids: ["Read-Only im Gateway ist aktiv – bitte ausschalten und Tageslauf neu starten (Fehler 321). Nichts gesendet."]
    f.umschalten("real-5")
    f.senden()
    assert f.gateway["schreiben"] is False and f.knopf_freigabe.instate(["disabled"])
    assert f.lampe("Schreibzugriff").farbe == ansicht.ROT


def test_probe_band_und_senden_ohne_gateway(wurzel, journal, dialoge):
    gesendet = []
    f = fenster(wurzel, journal, viele(10), probe=True, gateway={"verbunden": False, "schreiben": None},
                senden_fn=lambda ids: gesendet.append(ids) or ["Probe: 1 Vorschläge freigegeben, nichts gesendet, kein Messbeginn"])
    wurzel.deiconify()
    wurzel.update()
    assert f.probe_band.winfo_viewable() and "PROBE" in f.probe_band.cget("text") and "PROBE" in wurzel.title()
    assert not f.knopf_freigabe.instate(["disabled"])
    f.umschalten("momentum-4")                                                      # Probe: auch gesperrte Bücher wählbar
    f.senden()
    assert gesendet and "momentum-4" in gesendet[0]


def test_gestoppter_lauf_sperrt_senden(wurzel, journal):
    e = erg_mit(viele(5))
    e.gestoppt = "Abgleich mit IBKR weicht ab"
    f = fenster(wurzel, journal, erg=e)
    assert f.knopf_freigabe.instate(["disabled"]) and "gestoppt" in f.hinweis_text.get()
    assert "GESTOPPT: Abgleich mit IBKR weicht ab" in f.protokoll.get("1.0", "end") and f.protokoll.tag_ranges("fehler")


def test_uebersicht_positionen_einklappbar(wurzel, journal):
    journal.messbeginn_setzen("fundamental_a", "2026-11-09")
    for i in range(20):
        journal.ausfuehrung(f"e{i}", f"fundamental_a:k{i}", f"US{i}", 1, 5, 50.0 + i, 1.0, "2026-11-10", waehrung="USD", preis=55.0 + i)
    e = erg_mit()
    e.kurse_eur = {f"US{i}": 52.0 + i for i in range(20)}
    e.spyi = pd.Series({pd.Timestamp("2026-11-09"): 11.6, pd.Timestamp("2026-11-10"): 11.7})
    f = fenster(wurzel, journal, erg=e)
    wurzel.deiconify()
    wurzel.update()
    rahmen = f.positionen_rahmen["fundamental_a"]
    assert rahmen.winfo_manager() == "" and f.positionen_knoepfe["fundamental_a"].cget("text").startswith("▸ Positionen (20)")
    f.positionen_umschalten("fundamental_a")
    wurzel.update()
    assert rahmen.winfo_manager() == "pack" and f.positionen_knoepfe["fundamental_a"].cget("text").startswith("▾")
    tabelle = rahmen.winfo_children()[0]
    assert len(tabelle.get_children()) == 20 and "55.0000 USD" in tabelle.item(tabelle.get_children()[0])["values"][2]
    f.positionen_umschalten("fundamental_a")
    assert rahmen.winfo_manager() == ""


def test_protokollfilter_nur_wichtig(wurzel, journal):
    e = erg_mit()
    e.meldungen = ["Abgleich: Bestände aller Bücher stimmen", "HINWEIS Zeitpunkt: US-Käufe", "real: Buchwert 491.70 €"]
    f = fenster(wurzel, journal, erg=e)
    f.nur_wichtig.set(True)
    f._protokoll_neu()
    text = f.protokoll.get("1.0", "end")
    assert "HINWEIS Zeitpunkt" in text and "Bestände aller Bücher" not in text and "Buchwert" not in text


def test_schliessen_waehrend_senden_verweigert(wurzel, journal, dialoge):
    f = fenster(wurzel, journal, viele(5))
    f._sendet = True
    f.schliessen()
    assert wurzel.winfo_exists() and dialoge[-1][0] == "showinfo"
    f._sendet = False
    f.schliessen()
    with pytest.raises(tk.TclError):
        wurzel.winfo_exists()


def test_letzter_tageslauf_in_der_kopfzeile(wurzel, journal):
    journal.ereignis("tageslauf", "x; Xetra 03.11.2026, NYSE 03.11.2026", jetzt=datetime(2026, 11, 3, 22, 8))
    e = erg_mit()
    e.xetra = date(2026, 11, 10)
    f = fenster(wurzel, journal, erg=e)
    assert f.lampe("Letzter Tageslauf").farbe == ansicht.GELB
    assert "ohne Lauf" in f.lampen_widgets["Letzter Tageslauf"].cget("text")
