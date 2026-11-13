# Datenkorrektur EQ_OFFER: gehaltene und vorgeschlagene Titel (Fundamental A und B)

Erstellt 13.11.2026 09:57 mit `tools/pruefe_eq_offer_bestand.py` (Betriebsmodus, Journal nur lesend, Kurse aus dem Cache). Splits nur aus der Kursreihe (Yahoo, Spalte `split`) und quittierten Flex-Belegen.

Quartalsstichtag 2026-10-01 und letzte NYSE-Sitzung im Kurs-Cache 2026-11-13. Die Korrektur wirkt im Betrieb erst ab 04.01.2027; bis dahin gilt die Spalte „bisher“.

| Titel | Buch | Splits seit 2023 | Flex | EQ bisher / korrigiert (Quelle) am Stichtag | Piotroski bisher / korrigiert am Stichtag | EQ bisher / korrigiert (Quelle) zuletzt | betroffen |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ABBV | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| ADBE | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 7.0 / 7.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| APA | fundamental_a: Bestand | keiner | – | 0.0 / 0.0 (einreichung, Faktor 1) | 6.0 / 6.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| BBY | fundamental_a: Bestand; fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| BMY | fundamental_a: Bestand | keiner | – | 0.0 / 0.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| BSX | fundamental_a: Bestand | keiner | – | 0.0 / 0.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| CF | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| CMCSA | fundamental_a: Bestand | 05.01.2026 1.067:1 | – | 1.0 / 1.0 (einreichung, Faktor 1.067) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1.067) | nein |
| DIS | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| DPZ | fundamental_a: Bestand; fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| DVA | fundamental_a: Bestand; fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| DXCM | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| ETR | fundamental_b: Bestand | 13.12.2024 2:1 | – | 0.0 / 0.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| EXE | fundamental_a: Bestand | keiner | – | 0.0 / 0.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| EXPE | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| HCA | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 7.0 / 7.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| HSIC | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 7.0 / 7.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| J | fundamental_b: Bestand | 30.09.2024 1.197:1, 16.05.2025 1.01:1 | – | 1.0 / 1.0 (einreichung, Faktor 1.01) | 7.0 / 7.0 | 1.0 / 1.0 (einreichung, Faktor 1.01) | nein |
| JBHT | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| LOW | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 6.0 / 6.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| LVS | fundamental_a: Bestand; fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| NEM | fundamental_a: Bestand; fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| P | fundamental_b: gesendet | keiner | – | 0.0 / 0.0 (einreichung, Faktor 1) | 7.0 / 7.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| PNR | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| RSG | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| STE | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| TSCO | fundamental_a: Bestand | 20.12.2024 5:1 | – | 1.0 / 1.0 (einreichung, Faktor 1) | 6.0 / 6.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| UAL | fundamental_a: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 7.0 / 7.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| VRSN | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| WDAY | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| WMB | fundamental_b: Bestand | keiner | – | 0.0 / 0.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 0.0 / 0.0 (einreichung, Faktor 1) | nein |
| WMT | fundamental_b: Bestand | 26.02.2024 3:1 | – | 1.0 / 1.0 (einreichung, Faktor 1) | 8.0 / 8.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |
| WST | fundamental_b: Bestand | keiner | – | 1.0 / 1.0 (einreichung, Faktor 1) | 9.0 / 9.0 | 1.0 / 1.0 (einreichung, Faktor 1) | nein |

Betroffen (Signal bisher ≠ korrigiert an einem der beiden Tage): keiner.
