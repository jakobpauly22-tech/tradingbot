# Eingefrorene Kurse nach Handelsstopp bei Insolvenz

Erstellt 13.11.2026 15:35 mit `tools/pruefe_eingefrorene_kurse.py`. Kriterien vor der Suche festgelegt (docs/FUNDAMENTAL.md, Abschnitt „Vierte Datenkorrektur“): Grundmenge Firmen mit 8-K Item 1.03 und gültiger Kursreihe; Fenster 10 Handelstage vor bis 60 Tage nach dem ersten 8-K; mindestens 3 Handelstage Eröffnung = Hoch = Tief = Schluss = Vortagesschluss (zweite Suche, ohne Umsatzbedingung). Kurse bis zur Datumsgrenze des Tresors.

Grundmenge: 10 Firmen. Treffer: 1. Nichts wurde korrigiert.

| Ticker (CIK) | Name | Mitgliedschaft | 8-K 1.03 | Kursreihe | eingefroren | Kurs | erster echter Kurs danach | Mitglied am 1. Tag | in Backtest A gehalten |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SIVB (719739) | SVB Financial Group | 2018-03-19 bis 2023-03-15 | 2023-03-10 | SIVBQ (tiingo) | 2023-03-10 bis 2023-03-27 (12 Tage) | 106.04 | 0.4 USD am 2023-03-28 | ja | nein |
