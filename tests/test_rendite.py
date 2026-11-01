import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from tradingbot.kennzahlen.rendite import simple_return, total_return_index

_pfad = Path(__file__).parent / "musterloesungen" / "referenz.py"
_spec = importlib.util.spec_from_file_location("referenz_rendite", _pfad)
referenz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(referenz)


@pytest.mark.parametrize("p0, p1, d1", [(100, 110, 0), (50, 48, 3), (20, 20, 0.5)])
def test_simple_return_wie_referenz(p0, p1, d1):
    assert simple_return(p0, p1, d1) == pytest.approx(referenz.simple_return(p0, p1, d1))


def test_total_return_index_reinvestiert_dividende_am_ex_tag():
    kurse = pd.DataFrame(
        {"close": [100.0, 102.0, 99.0, 100.0], "dividende": [0.0, 0.0, 3.0, 0.0]},
        index=pd.to_datetime(["2024-06-03", "2024-06-04", "2024-06-05", "2024-06-06"]),
    )
    index = total_return_index(kurse)
    # Tag 3: (99 + 3 − 102) / 102 = 0 → Dividende gleicht den Kursabschlag aus
    assert index.tolist() == pytest.approx([100.0, 102.0, 102.0, 102.0 * 100 / 99])
