"""Ausschlussfilter: je Zweig der Entscheidung vom 02.11.2026 ein Fall."""
import pytest

from tradingbot.engines.fundamental.filter import anwenden
from tradingbot.konfiguration import lade_konfiguration

KONFIG = lade_konfiguration("fundamental")


def _p(wert=6, n=9):
    hoch = 7 <= n < 9
    return {"wert": wert if n == 9 else None, "wert_hochgerechnet": (wert * 9 / n) if n >= 7 else None, "hochgerechnet": hoch, "anzahl_signale": n}


def _a(wert, zone, variante="Z''"):
    return {"wert": wert, "zone": zone, "variante": variante}


GUT_BENEISH = {"wert": -2.8}


def test_verarbeitendes_gewerbe_altman_gefahr_ist_harter_ausschluss():
    e = anwenden(sic=3571, piotroski=_p(8), altman=_a(1.2, "gefahr", "Z"), beneish=GUT_BENEISH, cfo_t=1e9, konfig=KONFIG)
    assert e.ausgeschlossen and "verarbeitendes Gewerbe" in e.gruende[0]


def test_uebrige_z2_gefahr_allein_nur_warnhinweis():
    # wie Verisign, Domino's: negatives Buch-Eigenkapital durch Rückkäufe, sonst gesund
    e = anwenden(sic=7371, piotroski=_p(8), altman=_a(-22.4, "gefahr"), beneish=GUT_BENEISH, cfo_t=1e9, konfig=KONFIG)
    assert not e.ausgeschlossen and any("Warnhinweis" in h for h in e.hinweise)


@pytest.mark.parametrize("piotroski, cfo, grund", [(_p(3), 1e9, "Piotroski ≤ 3"), (_p(6), -5e8, "negativer operativer Cashflow")])
def test_uebrige_z2_gefahr_mit_zweitem_signal_raus(piotroski, cfo, grund):
    # wie Sears 2018: Z'' −4,40, Piotroski 2, operativer Cashflow negativ
    e = anwenden(sic=5311, piotroski=piotroski, altman=_a(-4.4, "gefahr"), beneish=GUT_BENEISH, cfo_t=cfo, konfig=KONFIG)
    assert e.ausgeschlossen and any(grund in g for g in e.gruende)


def test_versorger_ohne_altman():
    e = anwenden(sic=4911, piotroski=_p(5), altman=_a(0.5, "gefahr"), beneish=GUT_BENEISH, cfo_t=-1e9, konfig=KONFIG)
    assert not e.ausgeschlossen and "Altman nicht angewendet (Versorger)" in e.hinweise


def test_piotroski_hochgerechnet_und_uebersprungen():
    hoch = anwenden(sic=7372, piotroski=_p(2, n=8), altman=None, beneish=GUT_BENEISH, cfo_t=1e9, konfig=KONFIG)
    assert hoch.ausgeschlossen and "Piotroski 2 ≤ 3" in hoch.gruende and any("hochgerechnet" in h for h in hoch.hinweise)
    weg = anwenden(sic=7372, piotroski=_p(1, n=6), altman=None, beneish=GUT_BENEISH, cfo_t=1e9, konfig=KONFIG)
    assert not weg.ausgeschlossen and any("übersprungen" in h for h in weg.hinweise)


def test_beneish_raus_oder_uebersprungen():
    raus = anwenden(sic=2834, piotroski=_p(7), altman=_a(4.0, "sicher", "Z"), beneish={"wert": -1.5}, cfo_t=1e9, konfig=KONFIG)
    assert raus.ausgeschlossen and "Beneish -1.50 > -1.78" in raus.gruende
    fehlt = anwenden(sic=2834, piotroski=_p(7), altman=_a(4.0, "sicher", "Z"), beneish={"wert": None}, cfo_t=1e9, konfig=KONFIG)
    assert not fehlt.ausgeschlossen and "Beneish übersprungen (nicht berechenbar)" in fehlt.hinweise


@pytest.mark.parametrize("punkte, signale, gerundet, raus", [(3, 8, 3, True), (3, 7, 4, False), (4, 8, 5, False)])
def test_piotroski_hochgerechnet_kaufmaennisch_gerundet(punkte, signale, gerundet, raus):
    # 3 von 8 → 3,375 → 3 → raus; 3 von 7 → 3,857 → 4 → bleibt; 4 von 8 → 4,5 → 5 (kaufmännisch, nicht 4)
    from tradingbot.engines.fundamental.filter import piotroski_fuer_filter
    p = _p(punkte, n=signale)
    assert piotroski_fuer_filter(p) == gerundet
    e = anwenden(sic=7372, piotroski=p, altman=None, beneish=GUT_BENEISH, cfo_t=1e9, konfig=KONFIG)
    assert e.ausgeschlossen is raus
