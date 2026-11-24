"""SNDK: Aktiensplit 8:1 wirksam 20.11.2026, bestätigt über 8-K vom 29.10.2026 (Jakob 24.11.2026). Der Korrekturweg
behandelt das Ereignis der Kursreihe als geklärten Split (keine Meldung „ungeklärte Kapitalmaßnahme“)."""
import numpy as np
import pandas as pd
import pytest

from tradingbot.daten.kapitalmassnahmen_historie import lade_ereignisse
from tradingbot.engines.fundamental.multiples import marktwert_korrigiert


def test_sndk_split_bestaetigt_in_der_liste():
    e = lade_ereignisse()[2023554].loc[pd.Timestamp("2026-11-20")]
    assert e["art"] == "split" and e["split_faktor"] == 8.0 and bool(e["geprueft"])
    assert "8-K 29.10.2026" in e["quelle"] and "0001628280-26-068243" in e["quelle"]


def test_korrekturweg_ohne_ungeklaerte_massnahme():
    tage = pd.bdate_range("2026-10-01", "2026-11-23")
    close = pd.Series(np.where(tage < pd.Timestamp("2026-11-20"), 95.0, 80.0), index=tage)
    kurse = pd.DataFrame({"close": close, "split": np.where(tage == pd.Timestamp("2026-11-20"), 8.0, 0.0)}, index=tage)
    aktien = pd.DataFrame({"wert": [142_289_365.0], "filed": [pd.Timestamp("2026-10-30")], "accn": ["0001628280-26-068601"]},
                          index=pd.DatetimeIndex([pd.Timestamp("2026-10-26")]))
    mk = marktwert_korrigiert(pd.Timestamp("2026-11-23"), kurse, aktien, None, ereignisse=lade_ereignisse()[2023554],
                              max_alter_monate=15, automatisch_einordnen=True)
    assert mk["ungeklaert"] == [] and mk["marktwert"] == pytest.approx(80.0 * 142_289_365.0 * 8)
