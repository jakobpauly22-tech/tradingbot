# Ersatz-ETFs wegen Stückpreis – Liste zur Freigabe vor dem Neulauf

## Bruchstücke über die IBKR-API

IBKR bietet Bruchstücke für europäische Aktien und ETFs seit 2022 an, laut eigener FAQ aber nur über die
Handelsoberflächen und FIX/CTCI, **nicht über die API** (Fehlermeldung „Fractional-sized order cannot be placed via
API“). Das deckt sich mit `CLAUDE.md` („Bruchteilsaktien gibt es über die IBKR-API nicht“). Ersatz-ETFs sind also nötig.

## Prüfung der Regel „Anteilspreis höchstens ein Drittel der Positionsgröße am Starttag“

Positionsgröße 25 % von 1.250 € = 312,50 €, ein Drittel = **104,17 €**. Starttag 03.01.2013 (Schluss).

| ETF | Klasse | Start | Höchster Kurs 2013–2024 | Start ≤ 104,17 € | über 312,50 € ab |
| --- | --- | --- | --- | --- | --- |
| SXR8 | Aktien USA | 98,83 | 614,72 | ja | **19.02.2020** |
| EUNK | Aktien Europa | 32,53 | 81,38 | ja | – |
| EUNN | Aktien Japan | 19,82 | 54,09 | ja | – |
| SXR1 | Aktien Pazifik ex Japan | 90,30 | 184,34 | ja | – |
| EUNM | Aktien Schwellenländer | 23,92 | 39,69 | ja | – |
| EUNH | Anleihen Euro-Staaten | 107,93 | 136,21 | **nein** | – |
| EUN5 | Anleihen Euro-Unternehmen | 121,84 | 136,73 | **nein** | – |
| IBCI | Anleihen Euro inflationsindexiert | 195,58 | 251,42 | **nein** | – |
| SXRM | Anleihen US-Staaten (EUR) | 98,55 | 157,43 | ja | – |
| IUSP | Anleihen Schwellenländer | 73,70 | 77,55 | ja | – |
| 4GLD | Gold | 41,18 | 83,51 | ja | – |

**Problem:** Wörtlich angewendet trifft die Regel das eigentliche Problem nicht. SXR8 besteht am Starttag (98,83 €),
ist aber ab 19.02.2020 (nicht erst 2023) teurer als die ganze Position. Dafür fallen drei Anleihe-ETFs heraus, die nie
unkaufbar waren; für Euro-Anleihen gibt es auf Xetra kaum breite ETFs unter 104 € (fast alle 107–260 €).

## Vorschlag (bitte entscheiden)

**Regel:** Anteilspreis im ganzen gewerteten Zeitraum höchstens ein Drittel der Positionsgröße **bei Aktien-ETFs** und
höchstens die Positionsgröße bei allen; geprüft an den Kursen 2013–2024. Damit fällt nur SXR8 heraus; Anleihe-ETFs
(höchstens 251 €) bleiben kaufbar (mindestens ein Stück je Position, Rundungsfehler bis 80 % der Position bei IBCI).
Alternative: die Drittel-Regel über den ganzen Zeitraum für alle (dann fallen alle Euro-Anleihe-ETFs heraus, ohne Ersatz
auf Xetra).

**Ersatz für SXR8** nach der Rangfolge der Auswahlregel (größter physischer S&P-500-UCITS-ETF mit Xetra-Kursen seit
spätestens 2012), Volumen laut justETF:

| Rang | ETF | Volumen Mio. € | Xetra-Kurse ab | Kurs 2013 / Höchstkurs | Ergebnis |
| --- | --- | --- | --- | --- | --- |
| 1 | iShares Core S&P 500 (Acc), SXR8 | 137.659 | 2010 | 98,83 / 614,72 | Stückpreis zu hoch |
| 2 | Vanguard S&P 500 (Dist), VUSA | 46.908 | 10/2017 (Yahoo) | – | Xetra-Kurse zu spät |
| 3 | Invesco S&P 500 (Acc) | 38.164 | – | – | synthetisch |
| 4 | Vanguard S&P 500 (Acc) | 33.115 | 2019 | – | zu spät |
| 5 | **iShares Core S&P 500 (Dist), IUSA** | 20.247 | 2002 | 11,15 / 57,83 | **erfüllt beide Lesarten** |

Vorschlag: **IUSA.DE** (IE0031442068, physisch, vollständige Replikation, ausschüttend; Steuerart Aktienfonds).
Bei der wörtlichen Regel zusätzlich Ersatz für EUNH, EUN5 und IBCI nötig; auf Xetra mit Kurs unter 104 € am Starttag
gibt es nur Teilsegmente (z.B. iShares eb.rexx Government Germany 1.5-2.5yr, 95,92 €), keine breiten Euro-Anleihe-ETFs.
