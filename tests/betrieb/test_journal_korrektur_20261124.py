"""Journal-Korrektur 24.11.2026: Prüfung und Entfernen der alten Crossover-Sperren (ohne echtes Journal)."""
import importlib.util

from tradingbot.konfiguration import PROJEKT_WURZEL

_spec = importlib.util.spec_from_file_location("korrektur", PROJEKT_WURZEL / "tools" / "journal_korrektur_20261124.py")
korrektur = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(korrektur)

POS = {"regel": "crossover", "signal_tag": "2026-11-03", "kauf_tag": "2026-11-04", "stop": 65.9, "atr_signal": 0.58}


def _zustand():
    gesperrt = {"EUNN.DE": "2026-11-06", "IUSA.DE": "2026-11-20", "IUSP.DE": "2026-11-20"}
    return {"signaltag": "2026-11-23", "vor_signaltag": "2026-11-19",
            "vor": {"positionen": {"IUSA.DE": POS, "IUSP.DE": POS}, "gesperrt": {"EUNN.DE": "2026-11-06"}},
            "nach": {"positionen": {"IUSA.DE": POS, "IUSP.DE": POS}, "gesperrt": gesperrt}}


def test_korrektur_entfernt_nur_die_beiden_sperren():
    z = _zustand()
    assert korrektur.pruefen(z) == []
    neu = korrektur.korrigiert(z)
    assert neu["nach"]["gesperrt"] == {"EUNN.DE": "2026-11-06"} and neu["vor"] == z["vor"]
    assert neu["nach"]["positionen"] == z["nach"]["positionen"]
    assert z["nach"]["gesperrt"]["IUSA.DE"] == "2026-11-20"          # Original unverändert


def test_korrektur_bricht_bei_anderem_stand_ab():
    z = _zustand()
    z["signaltag"] = "2026-11-24"
    assert any("Signaltag" in f for f in korrektur.pruefen(z))
    z = korrektur.korrigiert(_zustand())
    z["signaltag"] = "2026-11-23"
    assert len(korrektur.pruefen(z)) == 2                             # schon korrigiert → kein zweites Mal
