# Abnahme der Rohreihen für den Marktwert (c2 (2))

Erstellt 16.11.2026 12:47 mit `tools/pruefe_rohkurse.py`. Kriterien vor dem Lauf festgehalten (docs/FUNDAMENTAL.md, „c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“): Vergleich nur gegen splitbereinigte Reihen, ≥ 250 Tage, |v/(H·Πf) − 1| ≤ 1 % an ≥ 99 % der Tage; Yahoo-Reihen zusätzlich Kriterium „Splitspalte“ (Befund 10, festgehalten 16.11.2026 11:21: Tiingo-Splitfaktoren gegen Yahoo-Ereignisse und Kapitalmaßnahmen-Liste, ±1 Handelstag, ±1 %; geändert nach dem ersten Lauf, festgehalten 12:45: Tiingo-Faktor genau am Datum einer Abspaltung der Liste gilt als bestanden). Nichts wurde angepasst.

Gültige Reihen: 721. Mit Rohreihe: 563, davon bestanden 545, nicht bestanden 18. Ohne Rohreihe: 158. Für c3 noch offen (ohne Abnahme, nicht dauerhaft unverfügbar): 158.

Davon nur am Kriterium „Splitspalte“ gescheitert: 11. Fehlerschwelle (Befund 14, sperrt c3): nicht überschritten.

## Nicht bestanden (18)

| Symbol (Quelle) | Tage | Anteil ≤ 1 % | größte Abweichung | H | Grund |
| --- | --- | --- | --- | --- | --- |
| GOOG (yfinance) | 2710 | 100.0% | 0.1% | 1 | Splitspalte: 2014-03-27: Split 2.002 fehlt bei Tiingo (Art split) |
| GOOGL (yfinance) | 3522 | 100.0% | 0.2% | 1 | Splitspalte: 2014-04-03: Split 1.998 fehlt bei Tiingo (nicht in der Liste) |
| HWM (yfinance) | 2054 | 58.2% | 30.5% | 1 | nur 58.2% der Tage innerhalb 1 %; Splitspalte: 2016-10-06: Tiingo-Faktor 0.333333 ohne Yahoo-Ereignis; 2020-04-01: Tiingo-Faktor 1.304 ohne Yahoo-Ereignis |
| EXPE (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2011-12-21: Split 0.5 fehlt bei Tiingo (nicht in der Liste) |
| BX (yfinance) | 3522 | 66.1% | 1.9% | 1 | nur 66.1% der Tage innerhalb 1 % |
| GEV (yfinance) | 193 | 100.0% | 0.0% | 1 | nur 193 gemeinsame Tage |
| MTCH (yfinance) | 2293 | 50.6% | 250.2% | 0.2856 | nur 50.6% der Tage innerhalb 1 %; Splitspalte: 2020-07-01: Split 2.1584 fehlt bei Tiingo (Art kombiniert) |
| FERG (yfinance) | 3437 | 99.7% | 4.2% | 1 | Splitspalte: 2018-06-11: Yahoo 0.947 in der Liste unklar (nicht eingeordnet); 2013-11-29: Tiingo-Faktor 0.967742 ohne Yahoo-Ereignis |
| DELL (yfinance) | 1516 | 99.7% | 58.9% | 1 | Splitspalte: 2018-12-28: Yahoo 1.806 in der Liste unklar (nicht eingeordnet) |
| AMTM (yfinance) | 69 | 100.0% | 0.0% | 1 | nur 69 gemeinsame Tage |
| DD (yfinance) | 3522 | 52.4% | 80.9% | 0.7967 | nur 52.4% der Tage innerhalb 1 %; Splitspalte: 2017-09-01: Tiingo-Faktor 1.282 ohne Yahoo-Ereignis |
| CNX (yfinance) | 3522 | 100.0% | 9.0% | 1 | Splitspalte: 2017-11-29: Split 1.2 fehlt bei Tiingo (nicht in der Liste) |
| MAR (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2011-11-22: Split 1.061 fehlt bei Tiingo (nicht in der Liste) |
| EL (yfinance) | 3522 | 100.0% | 2.9% | 1 | Splitspalte: 2011-11-23: Tiingo-Faktor 1.05 ohne Yahoo-Ereignis |
| GHC (yfinance) | 3522 | 99.9% | 3.9% | 1 | Splitspalte: 2015-07-01: Split 1.655 fehlt bei Tiingo (nicht in der Liste) |
| MSI (yfinance) | 3522 | 100.0% | 3.2% | 1 | Splitspalte: 2011-01-04: Tiingo 0.142857 statt 0.247372 |
| NOC (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2011-03-31: Split 1.10681 fehlt bei Tiingo (nicht in der Liste) |
| BXLT (tiingo) | 242 | 100.0% | 0.0% | 1 | nur 242 gemeinsame Tage |

## Bestanden mit Tiingo-Faktor an einer Abspaltung der Liste (über K behandelt) (26)

| Symbol (Quelle) | Hinweis |
| --- | --- |
| BFH (yfinance) | 2021-11-08: Tiingo-Faktor 1.253 an Abspaltung der Liste (über K behandelt) |
| PNR (yfinance) | 2018-05-01: Tiingo-Faktor 1.489 an Abspaltung der Liste (über K behandelt) |
| HSIC (yfinance) | 2019-02-08: Tiingo-Faktor 1.275 an Abspaltung der Liste (über K behandelt) |
| FBIN (yfinance) | 2022-12-15: Tiingo-Faktor 1.17 an Abspaltung der Liste (über K behandelt) |
| FTV (yfinance) | 2020-10-09: Tiingo-Faktor 1.195 an Abspaltung der Liste (über K behandelt) |
| O (yfinance) | 2021-11-15: Tiingo-Faktor 1.032 an Abspaltung der Liste (über K behandelt) |
| ILMN (yfinance) | 2024-06-25: Tiingo-Faktor 1.028 an Abspaltung der Liste (über K behandelt) |
| BWA (yfinance) | 2023-07-05: Tiingo-Faktor 1.136 an Abspaltung der Liste (über K behandelt) |
| FMC (yfinance) | 2019-03-04: Tiingo-Faktor 1.153 an Abspaltung der Liste (über K behandelt) |
| JEF (yfinance) | 2019-09-27: Tiingo-Faktor 1.068 an Abspaltung der Liste (über K behandelt); 2023-01-17: Tiingo-Faktor 1.046 an Abspaltung der Liste (über K behandelt) |
| FTI (yfinance) | 2021-02-16: Tiingo-Faktor 1.344 an Abspaltung der Liste (über K behandelt) |
| J (yfinance) | 2024-09-30: Tiingo-Faktor 1.197 an Abspaltung der Liste (über K behandelt) |
| EQT (yfinance) | 2018-11-13: Tiingo-Faktor 1.837 an Abspaltung der Liste (über K behandelt) |
| ECHO (yfinance) | 2019-09-11: Tiingo-Faktor 1.234 an Abspaltung der Liste (über K behandelt) |
| FLEX (yfinance) | 2024-01-03: Tiingo-Faktor 1.327 an Abspaltung der Liste (über K behandelt) |
| LH (yfinance) | 2023-07-03: Tiingo-Faktor 1.164 an Abspaltung der Liste (über K behandelt) |
| IP (yfinance) | 2021-10-01: Tiingo-Faktor 1.056 an Abspaltung der Liste (über K behandelt) |
| MRK (yfinance) | 2021-06-03: Tiingo-Faktor 1.048 an Abspaltung der Liste (über K behandelt) |
| EXC (yfinance) | 2022-02-02: Tiingo-Faktor 1.402 an Abspaltung der Liste (über K behandelt) |
| DOV (yfinance) | 2018-05-09: Tiingo-Faktor 1.238 an Abspaltung der Liste (über K behandelt) |
| DTE (yfinance) | 2021-07-01: Tiingo-Faktor 1.175 an Abspaltung der Liste (über K behandelt) |
| HON (yfinance) | 2018-10-01: Tiingo-Faktor 1.011 an Abspaltung der Liste (über K behandelt); 2018-10-29: Tiingo-Faktor 1.032 an Abspaltung der Liste (über K behandelt) |
| IBM (yfinance) | 2021-11-04: Tiingo-Faktor 1.046 an Abspaltung der Liste (über K behandelt) |
| GE (yfinance) | 2023-01-04: Tiingo-Faktor 1.281 an Abspaltung der Liste (über K behandelt); 2024-04-02: Tiingo-Faktor 1.253 an Abspaltung der Liste (über K behandelt) |
| PFE (yfinance) | 2020-11-17: Tiingo-Faktor 1.054 an Abspaltung der Liste (über K behandelt) |
| BDX (yfinance) | 2022-04-01: Tiingo-Faktor 1.025 an Abspaltung der Liste (über K behandelt) |

## Verdeckter Faktor H ≠ 1 (Split nach der Tresorgrenze; Rohkurs nötig) (22)

| Symbol (Quelle) | H |
| --- | --- |
| MNST (yfinance) | 2.0000 |
| FTV (yfinance) | 1.3270 |
| CMCSA (yfinance) | 1.0670 |
| NFLX (yfinance) | 10.0000 |
| BKNG (yfinance) | 25.0000 |
| FAST (yfinance) | 2.0000 |
| J (yfinance) | 1.0100 |
| CRWD (yfinance) | 4.0000 |
| CVNA (yfinance) | 5.0000 |
| IBKR (yfinance) | 4.0000 |
| NKTR (yfinance) | 0.0667 |
| CTVA (yfinance) | 6.6650 |
| AMCR (yfinance) | 0.2000 |
| NOW (yfinance) | 5.0000 |
| LEN (yfinance) | 1.0330 |
| KLAC (yfinance) | 10.0000 |
| FDX (yfinance) | 1.2410 |
| HON (yfinance) | 1.0117 |
| APH (yfinance) | 2.0000 |
| ORLY (yfinance) | 15.0000 |
| BDX (yfinance) | 1.2720 |
| DD (tiingo) | 0.3333 |

## Name bei Tiingo passt nicht zum Universum (4, nur Meldung)

| Symbol | Tiingo | Universum | Abnahme |
| --- | --- | --- | --- |
| CPAY | Fleetcor Technologies Inc | Corpay, Inc. | bestanden |
| LH | Laboratory Corp Of America Holdings | Labcorp Holdings Inc. | bestanden |
| GE | General Electric Company | GE Aerospace | bestanden |
| CVSA | Adtalem Global Education Inc | Covista Inc. | bestanden |

## Für c3 noch offen (158)

FDXF (yfinance), HONA (yfinance), META (yfinance), PRU (yfinance), PSA (yfinance), PSX (yfinance), PTC (yfinance), PVH (yfinance), PWR (yfinance), PYPL (yfinance), Q (yfinance), QCOM (yfinance), R (yfinance), RCL (yfinance), RDDT (yfinance), REG (yfinance), REGN (yfinance), RF (yfinance), RHI (yfinance), RIG (yfinance), RJF (yfinance), RL (yfinance), RMD (yfinance), ROK (yfinance), ROL (yfinance), ROP (yfinance), ROST (yfinance), RRC (yfinance), RSG (yfinance), RTX (yfinance), RVTY (yfinance), SBAC (yfinance), SBUX (yfinance), SCHW (yfinance), SEDG (yfinance), SHW (yfinance), SIG (yfinance), SJM (yfinance), SKYD (yfinance), SLB (yfinance), SLG (yfinance), SLM (yfinance), SMCI (yfinance), SNA (yfinance), SNDK (yfinance), SNPS (yfinance), SO (yfinance), SOLS (yfinance), SOLV (yfinance), SPG (yfinance), SPGI (yfinance), SRE (yfinance), STE (yfinance), STLD (yfinance), STT (yfinance), STX (yfinance), STZ (yfinance), SW (yfinance), SWK (yfinance), SWKS (yfinance), SYF (yfinance), SYK (yfinance), SYY (yfinance), T (yfinance), TAP (yfinance), TDC (yfinance), TDG (yfinance), TDY (yfinance), TECH (yfinance), TEL (yfinance), TER (yfinance), TFC (yfinance), TFX (yfinance), TGT (yfinance), THC (yfinance), TJX (yfinance), TKO (yfinance), TMO (yfinance), TMUS (yfinance), TNL (yfinance), TPL (yfinance), TPR (yfinance), TRGP (yfinance), TRIP (yfinance), TRMB (yfinance), TROW (yfinance), TRV (yfinance), TSCO (yfinance), TSLA (yfinance), TSN (yfinance), TT (yfinance), TTD (yfinance), TTWO (yfinance), TWLO (yfinance), TXN (yfinance), TXT (yfinance), TYL (yfinance), UAA (yfinance), UAL (yfinance), UBER (yfinance), UDR (yfinance), UHS (yfinance), ULTA (yfinance), UNH (yfinance), UNM (yfinance), UNP (yfinance), UPS (yfinance), URBN (yfinance), URI (yfinance), USB (yfinance), V (yfinance), VEEV (yfinance), VFC (yfinance), VIAV (yfinance), VICI (yfinance), VLO (yfinance), VLTO (yfinance), VMC (yfinance), VMRK (yfinance), VNO (yfinance), VNT (yfinance), VRSK (yfinance), VRSN (yfinance), VRT (yfinance), VRTX (yfinance), VST (yfinance), VTR (yfinance), VTRS (yfinance), VYLR (yfinance), VZ (yfinance), WAB (yfinance), WAT (yfinance), WDAY (yfinance), WDC (yfinance), WEC (yfinance), WELL (yfinance), WFC (yfinance), WHR (yfinance), WM (yfinance), WMB (yfinance), WMT (yfinance), WRB (yfinance), WSM (yfinance), WST (yfinance), WTW (yfinance), WU (yfinance), WY (yfinance), WYNN (yfinance), XEL (yfinance), XOM (yfinance), XRAY (yfinance), XYL (yfinance), XYZ (yfinance), YUM (yfinance), ZBH (yfinance), ZBRA (yfinance), ZION (yfinance), ZTS (yfinance)

## Ursache je nicht bestandener Reihe (Claude, 16.11.2026; nichts angepasst)

Zweiter Lauf nach der Änderung des Kriteriums (festgehalten 12:45, `docs/FUNDAMENTAL.md`): 18 von 563 Reihen (3,2 %),
Fehlerschwelle nicht überschritten, c3 nicht mehr gesperrt. Erster Lauf: `docs/berichte/2026-11-16_rohkurse_abnahme.md`.
Alle 18 rechnen nach Teil b (gemeldet); MTCH und DD bekommen nach Variante B keinen Marktwert (|H − 1| > 0,5 %). Bei den
übrigen 16 ist H = 1; Teil b hat dort keinen verdeckten Faktor, der Rückfall ändert den Marktwert nicht.
„Vermutlich“ heißt: aus Datum und Faktor erschlossen, nicht an einer Primärquelle geprüft.

| Reihe | Kriterium | Ursache |
| --- | --- | --- |
| GOOG | Splitspalte | Ereignis 27.03.2014 (Faktor 2,002, Liste: split) fehlt bei Tiingo; vermutlich Ausgabe der Class-C-Aktien 2014. Rohkurs passt (100 % der Tage); betrifft nur Aktienzahlen vor April 2014. |
| GOOGL | Splitspalte | Dasselbe Ereignis am 03.04.2014 (1,998), fehlt bei Tiingo; in der Liste nur am Datum der GOOG-Reihe (27.03.), daher „nicht in der Liste“. |
| HWM | beide | Rohkurs passt nur an 58 % der Tage. Tiingo führt 06.10.2016 (1/3) und 01.04.2020 (1,304), Yahoo nicht; vermutlich Reverse-Split 1:3 von Arconic 2016 und Abspaltung der Arconic Corp. 2020. Die Reihen bilden die Geschichte von Alcoa/Arconic/Howmet unterschiedlich ab. Seit 15.11. bekannt. |
| EXPE | Splitspalte | 21.12.2011 (0,5) fehlt bei Tiingo; vermutlich Reverse-Split 1:2 mit Abspaltung TripAdvisor. 2011, vor Beginn der Liste. |
| BX | Rohkurs | Nur 66 % der Tage innerhalb 1 %, größte Abweichung 1,9 %; Ursache nicht geklärt (seit 15.11. bekannt). |
| GEV | Rohkurs | Zu kurz: 193 gemeinsame Tage bis zur Tresorgrenze (Börsengang 2024). |
| MTCH | beide | Rohkurs passt nur an 51 % der Tage, H 0,29; das kombinierte Ereignis 01.07.2020 (Split-Faktor 2,1584, geprüft) fehlt bei Tiingo. Die Reihen gehören vor 2020 vermutlich zu verschiedenen Vorgängern (Match Group / IAC). **Kein Marktwert (Variante B).** |
| FERG | Splitspalte | 11.06.2018 (0,947) in der Liste „unklar“ (kein SEC-Periodenbericht davor); Tiingo 29.11.2013 (0,9677) ohne Yahoo-Ereignis. Vermutlich Aktienzusammenlegungen mit Sonderdividende (18/19, 30/31). |
| DELL | Splitspalte | 28.12.2018 (1,806) in der Liste „unklar“ (dieselbe Periode davor nicht gemeldet); vermutlich Umtausch der Class-V-Aktien bei der Rückkehr an die Börse. |
| AMTM | Rohkurs | Zu kurz: 69 gemeinsame Tage (Börsengang 2024). |
| DD | beide | Rohkurs passt nur an 52 % der Tage, H 0,80; Tiingo 01.09.2017 (1,282) ohne Yahoo-Ereignis = Umtausch E. I. du Pont in DowDuPont (dritte Datenkorrektur, 13.11.2026). **Kein Marktwert (Variante B).** |
| CNX | Splitspalte | 29.11.2017 (1,2) fehlt bei Tiingo und steht nicht in der Liste; vermutlich Abspaltung von CONSOL Energy (dann ist Tiingo richtig). |
| MAR | Splitspalte | 22.11.2011 (1,061) fehlt bei Tiingo; vermutlich Abspaltung Marriott Vacations (Tiingo richtig). 2011. |
| EL | Splitspalte | Tiingo 23.11.2011 (1,05) ohne Yahoo-Ereignis; Ursache nicht geklärt. 2011. |
| GHC | Splitspalte | 01.07.2015 (1,655) fehlt bei Tiingo und steht nicht in der Liste; vermutlich Abspaltung Cable One (Tiingo richtig). |
| MSI | Splitspalte | 04.01.2011: Yahoo 0,2474, Tiingo 1/7; vermutlich Reverse-Split 1:7 mit Abspaltung Motorola Mobility (Tiingo zeigt nur den Split-Anteil). 2011. |
| NOC | Splitspalte | 31.03.2011 (1,1068) fehlt bei Tiingo; vermutlich Abspaltung Huntington Ingalls (Tiingo richtig). 2011. |
| BXLT (Tiingo) | Rohkurs | Zu kurz: 242 gemeinsame Tage (Baxalta, 2015–2016 börsennotiert). |

Auffällig: In 6 Fällen (EXPE, CNX, MAR, GHC, MSI, NOC) ist Tiingo vermutlich richtig und das Ereignis fehlt nur in der
Liste (2011 vor ihrem Beginn, sonst nicht erfasst). Das Kriterium wertet das wie festgelegt als nicht bestanden; wegen
H = 1 ohne Wirkung auf den Marktwert.
