"""Kursstatus je Mitgliedschaft (daten/universum/kursstatus.csv), zugeordnet über den Schlüssel (Befund 19, Schritt 2).

kursstatus.csv nennt je Mitgliedschaft Quelle, Symbol und Gültigkeit der Kursreihe. Bis zum 18.11.2026 hing die Datei
allein an der Zeilennummer (Spalte `index`) des Universums; eine eingefügte Zeile verschob still alle folgenden
Zuordnungen (Befund 19, 16.11.2026). Seit Schritt 2 (Plan Jakob 17.11.2026) gilt:

- Zuordnung über den Schlüssel (Ticker, von, bis) der Mitgliedschaft, nie über die Zeilennummer.
- Laut (UniversumVerschoben) statt still: ein Schlüssel kommt doppelt vor (Universum oder Status), oder eine Statuszeile
  findet ihre Mitgliedschaft im Universum nicht mehr (z. B. geändertes Datum bei Wikipedia). Universumszeilen ohne
  Statuszeile bleiben wie bisher ohne Kurse (vor allem Mitgliedschaften, die vor 2012 enden).
- Ergebnis in derselben Form wie früher `read_csv(...).set_index("index")`: Index „index“ ist die Zeilennummer im
  übergebenen Universum; Spalte `index_csv` ist die in der Datei gespeicherte Nummer (nur zur Nachverfolgung).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class UniversumVerschoben(RuntimeError):
    """Universum und kursstatus.csv passen über den Schlüssel (Ticker, von, bis) nicht zusammen; nie still übergangen."""


def status_datei() -> Path:
    from tradingbot.konfiguration import PROJEKT_WURZEL

    return PROJEKT_WURZEL / "daten" / "universum" / "kursstatus.csv"


def tag_text(wert) -> str:
    """Datum als JJJJ-MM-TT, leer für fehlend (NaT, None, leerer Text)."""
    if wert is None or (isinstance(wert, str) and wert == "") or pd.isna(wert):
        return ""
    return pd.Timestamp(wert).strftime("%Y-%m-%d")


def schluessel(tabelle: pd.DataFrame) -> pd.Series:
    """(Ticker, von, bis) je Zeile, Daten als Text; Index wie `tabelle`."""
    return pd.Series([(str(t), tag_text(v), tag_text(b)) for t, v, b in zip(tabelle["ticker"], tabelle["von"], tabelle["bis"])],
                     index=tabelle.index, dtype=object)


def lies_kursstatus(pfad: Path | None = None) -> pd.DataFrame:
    """kursstatus.csv unverändert (für Auswertungen, die nur Quelle und Symbol brauchen, nicht die Mitgliedschaft)."""
    pfad = pfad or status_datei()
    t = pd.read_csv(pfad)
    t["ticker"] = pd.read_csv(pfad, usecols=["ticker"], dtype=str, keep_default_na=False)["ticker"]   # „NA“ ist ein Ticker
    return t


def _doppelte(s: pd.Series) -> list:
    return sorted(set(s[s.duplicated(keep=False)]))


def ordne_zu(universum: pd.DataFrame, status: pd.DataFrame) -> pd.DataFrame:
    """Statuszeilen über den Schlüssel den Universumszeilen zuordnen (siehe Moduldoku). Wirft UniversumVerschoben."""
    s_uni, s_stat = schluessel(universum), schluessel(status)
    for name, s in (("Universum", s_uni), ("kursstatus.csv", s_stat)):
        doppelt = _doppelte(s)
        if doppelt:
            raise UniversumVerschoben(f"Schlüssel (Ticker, von, bis) doppelt in {name}: {len(doppelt)} "
                                      f"(z. B. {', '.join(map(str, doppelt[:3]))}) – keine Kurse zugeordnet")
    nr_je_schluessel = {k: nr for nr, k in s_uni.items()}
    zeilen = s_stat.map(nr_je_schluessel.get)
    ohne = s_stat[zeilen.isna()]
    if len(ohne):
        raise UniversumVerschoben(f"Universum und kursstatus.csv passen nicht: {len(ohne)} von {len(status)} Statuszeilen ohne "
                                  f"Mitgliedschaft mit gleichem Schlüssel (z. B. {', '.join(map(str, ohne.iloc[:3]))}) – "
                                  "keine Kurse zugeordnet")
    aus = status.rename(columns={"index": "index_csv"})
    aus.index = pd.Index(zeilen.to_numpy(), name="index").astype(universum.index.dtype)
    return aus                                   # Reihenfolge der Datei bleibt (z. B. drop_duplicates „erste Zeile gewinnt“)


def lade_kursstatus(universum: pd.DataFrame, pfad: Path | None = None) -> pd.DataFrame:
    """kursstatus.csv, über den Schlüssel dem übergebenen Universum zugeordnet (Index = Zeile im Universum)."""
    return ordne_zu(universum, lies_kursstatus(pfad))
