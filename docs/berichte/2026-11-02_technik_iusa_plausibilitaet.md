# Ersatz IUSA: Plausibilitätsprüfung nicht bestanden (Datenlücke) – Entscheidung nötig vor dem Neulauf

Prüfung laut Entscheidung 03.11.2026: IUSA.DE inklusive Dividenden gegen SXR8.DE, 03.01.2013–31.12.2019, Abweichung der
Rendite p.a. höchstens 0,3 Prozentpunkte. `tools/backtest_technik.py` sperrt den Lauf (Exit 2).

| Prüfung | IUSA inkl. Dividenden | SXR8 | Differenz |
| --- | --- | --- | --- |
| 03.01.2013–31.12.2019 (Vorgabe) | 16,07 % | 16,53 % | **−0,46 Pp. (nicht bestanden)** |
| 02.01.2014–31.12.2019 (nur zur Ursachensuche) | | | −0,20 Pp. |

**Ursache:** Yahoo führt für IUSA (alle Linien: .DE, .AS, .L, .MI) **2012 und 2013 keine Ausschüttungen**. Ab 2014 sind
sie vollständig (vierteljährlich, in EUR; Abgleich mit der USD-Linie desselben Fonds an der LSE, IDUS.L, umgerechnet:
Median-Verhältnis 1,0003). IDUS.L (iShares Core S&P 500 USD Dist, gleicher Fonds IE0031442068) hat die vier
Ausschüttungen 2013.

**Vorschlag (nicht angewendet):** die vier Ausschüttungen 2013 aus IDUS.L ergänzen, zum EUR/USD-Kurs des Ex-Tags
umgerechnet, als dokumentierte Korrektur (`universum.korrekturen`, Regel `dividende_ergaenzen`):

| Ex-Tag | USD (IDUS.L) | EUR |
| --- | --- | --- |
| 20.02.2013 | 0,0681 | 0,0508 |
| 29.05.2013 | 0,0684 | 0,0532 |
| 28.08.2013 | 0,0585 | 0,0437 |
| 27.11.2013 | 0,0582 | 0,0429 |

Damit läge die Differenz bei **−0,21 Pp.** (bestanden). Der Rest erklärt sich plausibel (Ausschüttung mit Abzug der
US-Quellensteuer im Fonds bei beiden gleich; Unterschiede in Ex-Tagen und Wiederanlage).

**Hinweis zum Tresor:** Beim Abgleich der Dividenden-Währung hat die Abfrage bei Yahoo auch IUSA-Ausschüttungsbeträge aus
2025/2026 angezeigt (nur Beträge je Anteil, keine Kurse oder Renditen). Sie flossen in nichts ein; künftig werden solche
Abfragen auf Daten bis 31.12.2024 begrenzt.
