"""Prüft referenz.py gegen alle Musterlösungen der Übungsblätter (testfaelle_uebungen.json).

Ausführen: pytest test_uebungen.py   (oder: python test_uebungen.py)
Später im Bot: referenz durch die Module des Bots ersetzen, Funktionsnamen beibehalten.
"""
import json, math, pathlib
import referenz as R

DATA = json.loads((pathlib.Path(__file__).parent / "testfaelle_uebungen.json").read_text(encoding="utf-8"))
NS = {k: getattr(R, k) for k in dir(R) if not k.startswith("_")}
NS.update({"max": max, "min": min, "round": round, "sum": sum})
NS.update({k: {float(t): v for t, v in d.items()} for k, d in DATA["konstanten"].items()})


def check(case):
    got = eval(case["ausdruck"], {"__builtins__": {}}, NS)
    if case["erwartet"] == "unendlich":
        return math.isinf(got), got
    return abs(got - case["erwartet"]) <= case["toleranz"] + 1e-12, got


try:
    import pytest

    @pytest.mark.parametrize("case", DATA["faelle"], ids=[c["id"] for c in DATA["faelle"]])
    def test_musterloesung(case):
        ok, got = check(case)
        assert ok, f"{case['id']} ({case['quelle']}, {case['aufgabe']}): erwartet {case['erwartet']}, berechnet {got}"
except ImportError:
    pass

if __name__ == "__main__":
    bad = [(c["id"], c["erwartet"], g) for c in DATA["faelle"] for ok, g in [check(c)] if not ok]
    print(f"{len(DATA['faelle'])} Testfälle, {len(DATA['faelle']) - len(bad)} bestanden")
    for b in bad:
        print("ABWEICHUNG", b)
