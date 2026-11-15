r"""Identitätsprüfung der Betriebsregel für Datenlücken (docs/REGIME.md, Abschnitt 9b; Jakob 15.11.2026).

Vergleicht `engines/regime/signale.py` von heute mit dem Stand im Festlegungs-Commit b628678 über den gesamten
Backtest-Zeitraum (Entwicklungsdaten bis 31.12.2024, Tresor bleibt zu): Signale, Rohzustand und Zustand mit Haltepflicht
je Monatsende für V1 und D1–D4 müssen identisch sein, ebenso der Sahm-Wert (alte Formel gegen die Lückenregel auf
lückenlosen Daten). Kein Backtest, keine Kennzahlen, kein Eintrag in daten/regime/varianten.csv.

Aufruf: .venv\Scripts\python tools\pruefe_regime_datenluecke.py
"""
import subprocess
import sys
import types
from datetime import date
from pathlib import Path

import pandas as pd

FESTLEGUNG = "b628678"
DATEI = "src/tradingbot/engines/regime/signale.py"
ETF, DATEN_AB, ENDE = "SPYI.DE", "2012-01-01", "2024-12-31"


def signale_aus_commit(commit: str, wurzel: Path) -> types.ModuleType:
    """`signale.py` genau so, wie es im Commit steht, als eigenes Modul."""
    quelle = subprocess.run(["git", "show", f"{commit}:{DATEI}"], cwd=wurzel, capture_output=True, check=True).stdout.decode("utf-8")
    modul = types.ModuleType(f"signale_{commit}")
    exec(compile(quelle, f"{commit}:{DATEI}", "exec"), modul.__dict__)
    return modul


def vergleiche(alt, neu, schlusskurse: pd.Series, makro) -> dict:
    """Vergleich je Variante (Verlauf identisch?) und je Monatsende (Sahm-Wert alt gegen Lückenregel)."""
    erg = {"varianten": {}, "monate": 0, "abweichungen": []}
    for v in alt.VARIANTEN:
        a = alt.regime_verlauf(schlusskurse, makro, variante=v)
        n = neu.regime_verlauf(schlusskurse, makro, variante=v)
        gleich = a.astype(object).where(a.notna(), None).equals(n.astype(object).where(n.notna(), None))
        erg["varianten"][v] = gleich
        erg["monate"] = len(a)
        if not gleich:
            erg["abweichungen"].append(f"Verlauf {v} weicht ab")
    sahm = 0
    for tag in neu.monatsenden(schlusskurse.dropna().index):
        u = makro(neu.REIHEN["arbeit"], tag - pd.Timedelta(days=1))
        s_alt, s_neu = alt.sahm_wert(u), neu.sahm_wert_bei_datenluecke(u)
        if s_alt is None:
            erg["abweichungen"].append(f"{tag.date()}: Sahm-Wert nach b628678 nicht bestimmbar (Lücke im Backtest-Zeitraum?)")
        elif s_neu is None or abs(s_alt - s_neu) > 1e-12:
            erg["abweichungen"].append(f"{tag.date()}: Sahm-Wert alt {s_alt}, Lückenregel {s_neu}")
        else:
            sahm += 1
    erg["sahm_gleich"] = sahm
    return erg


def main() -> int:
    from tradingbot.backtest.tresor import pruefe_kein_betriebsmodus
    from tradingbot.daten.kurse import lade_kurse
    from tradingbot.engines.regime import signale as neu
    from tradingbot.konfiguration import PROJEKT_WURZEL

    pruefe_kein_betriebsmodus("Identitätsprüfung Regime")
    alt = signale_aus_commit(FESTLEGUNG, PROJEKT_WURZEL)
    kurse = lade_kurse(ETF, DATEN_AB, ENDE)["close"]
    erg = vergleiche(alt, neu, kurse, neu.makro_stand_aus_cache())
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJEKT_WURZEL, capture_output=True, text=True).stdout.strip()
    ok = not erg["abweichungen"]
    zeilen = ["# Regime-Engine: Identitätsprüfung der Betriebsregel für Datenlücken", "",
              f"Stand {date.today():%d.%m.%Y}, Git {git}. Vergleich von `{DATEI}` heute mit dem Festlegungs-Commit {FESTLEGUNG}.", "",
              f"- Zeitraum: Monatsenden von {ETF} {kurse.index[0]:%d.%m.%Y} bis {kurse.index[-1]:%d.%m.%Y} ({erg['monate']} Monatsenden), "
              "Makrodaten point-in-time (ALFRED), Tresor geschlossen.",
              "- Verläufe (vier Signale, Rohzustand, Zustand mit Haltepflicht) je Variante: "
              + ", ".join(f"{v} {'identisch' if g else 'ABWEICHUNG'}" for v, g in erg["varianten"].items()) + ".",
              f"- Sahm-Wert: alte Formel und Lückenregel stimmen an {erg['sahm_gleich']} Monatsenden überein (Toleranz 1e-12).",
              f"- **Ergebnis: {'identisch' if ok else 'NICHT identisch'}.**", "",
              "Kein Backtest: keine Wertreihen, keine Kennzahlen, kein Eintrag in `daten/regime/varianten.csv`. Das Urteil "
              "„V1 nicht bestanden“ bleibt unberührt.", ""]
    zeilen += [f"- {a}" for a in erg["abweichungen"]]
    text = "\n".join(zeilen)
    (PROJEKT_WURZEL / "docs" / "berichte" / f"{date.today():%Y-%m-%d}_regime_datenluecke.md").write_text(text, encoding="utf-8")
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
