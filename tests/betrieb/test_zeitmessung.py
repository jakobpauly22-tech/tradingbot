"""Zeitmessung je Abschnitt im Tageslauf und beim Senden (Jakob 17.11.2026, nur Anzeige)."""
from test_tageslauf import AN, ABEND, BrokerAttrappe, kurse_attrappe, lauf, umgebung  # noqa: F401
from tradingbot.betrieb import benachrichtigung as bn
from tradingbot.betrieb.ansicht import meldungsart
from tradingbot.betrieb.tageslauf import freigeben_und_senden
from tradingbot.betrieb.zeitmessung import PRAEFIX, Zeitmessung


def test_abschnitte_addieren_und_zeile():
    t = iter([0.0, 1.0, 3.5, 4.0, 4.25, 10.0, 10.0])
    u = Zeitmessung(uhr=lambda: next(t))          # Beginn 0,0
    u.abschnitt("A")                              # 1,0
    u.abschnitt("B")                              # 3,5: A 2,5 s
    u.abschnitt("A")                              # 4,0: B 0,5 s
    u.abschnitt("C")                              # 4,25: A + 0,25 s
    assert u.zeile() == f"{PRAEFIX}: A 2,8 s; B 0,5 s; C 5,8 s; gesamt 10,0 s"
    assert u.dauer == {"A": 2.75, "B": 0.5, "C": 5.75}


def test_tageslauf_protokolliert_dauer_ohne_folgen(umgebung):
    j, rm = umgebung
    e = lauf(j, rm)
    (zeile,) = [m for m in e.meldungen if m.startswith(PRAEFIX + ":")]
    for name in ("Vorbereitung und Devisenkurs", "Realbuch", "Regime", "Technik-Bücher", "Fundamental-Bewertung", "gesamt"):
        assert name in zeile
    assert set(e.dauer) >= {"Realbuch", "Technik-Bücher", "Fundamental-Bewertung"} and all(d >= 0 for d in e.dauer.values())
    assert meldungsart(zeile) == "info" and not any(PRAEFIX in s for s in e.sofort)


def test_senden_protokolliert_dauer_ohne_sendeproblem(umgebung):
    j, rm = umgebung
    lauf(j, rm)
    z = next(x for x in j.vorschlaege(buch="real") if x["status"] == "vorgeschlagen")
    meldungen = freigeben_und_senden(j, [z["id"]], BrokerAttrappe(), ABEND, risk=rm, kurse_laden=kurse_attrappe(), konfig_betrieb=AN)
    (zeile,) = [m for m in meldungen if m.startswith(PRAEFIX + " (Senden):")]
    assert "Sendeschleife" in zeile and meldungsart(zeile) == "info"
    assert bn.sendeprobleme(j, [z["id"]], "2000-01-01T00:00:00", meldungen, ABEND) is None
