"""Hilfsfunktionen der Werkzeuge in tools/ (die Skripte selbst brauchen Netz und Cache)."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd


def _werkzeug(name):
    pfad = Path(__file__).parents[1] / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"werkzeug_{name}", pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class _Sec:
    def submissions(self, cik):
        namen = {1288776: ("GOOGLE INC.", []), 1652044: ("Alphabet Inc.", [])}
        name, frueher = namen[cik]
        return {"name": name, "formerNames": [{"name": n} for n in frueher]}, None


def test_bekannte_namen_mit_vorgaengern_als_numpy_array():
    w = _werkzeug("kurse_universum")
    for vorgaenger in (np.array([1288776]), np.array([], dtype=np.int64), None, [1288776]):
        zeile = pd.Series({"name": "Alphabet Inc. (Class A)", "cik": 1652044, "vorgaenger_ciks": vorgaenger})
        namen = w._bekannte_namen(zeile, _Sec())
        assert "Alphabet Inc." in namen
        assert ("GOOGLE INC." in namen) == (vorgaenger is not None and len(vorgaenger) > 0)
