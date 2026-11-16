# Abnahme der Rohreihen für den Marktwert (c2 (2))

Erstellt 16.11.2026 12:28 mit `tools/pruefe_rohkurse.py`. Kriterien vor dem Lauf festgehalten (docs/FUNDAMENTAL.md, „c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“): Vergleich nur gegen splitbereinigte Reihen, ≥ 250 Tage, |v/(H·Πf) − 1| ≤ 1 % an ≥ 99 % der Tage; Yahoo-Reihen zusätzlich Kriterium „Splitspalte“ (Befund 10, festgehalten 16.11.2026 11:21: Tiingo-Splitfaktoren gegen Yahoo-Ereignisse und Kapitalmaßnahmen-Liste, ±1 Handelstag, ±1 %). Nichts wurde angepasst.

Gültige Reihen: 721. Mit Rohreihe: 563, davon bestanden 519, nicht bestanden 44. Ohne Rohreihe: 158. Für c3 noch offen (ohne Abnahme, nicht dauerhaft unverfügbar): 158.

Davon nur am Kriterium „Splitspalte“ gescheitert: 37. Fehlerschwelle (Befund 14, sperrt c3): Fehlerschwelle der Abnahme überschritten: 44 von 563 Reihen nicht bestanden (7.8% > 5%).

## Nicht bestanden (44)

| Symbol (Quelle) | Tage | Anteil ≤ 1 % | größte Abweichung | H | Grund |
| --- | --- | --- | --- | --- | --- |
| BFH (yfinance) | 3522 | 100.0% | 1.3% | 1 | Splitspalte: 2021-11-08: Tiingo-Faktor 1.253 an einem Tag mit Art „abspaltung“ |
| GOOG (yfinance) | 2710 | 100.0% | 0.1% | 1 | Splitspalte: 2014-03-27: Split 2.002 fehlt bei Tiingo (Art split) |
| GOOGL (yfinance) | 3522 | 100.0% | 0.2% | 1 | Splitspalte: 2014-04-03: Split 1.998 fehlt bei Tiingo (nicht in der Liste) |
| PNR (yfinance) | 3522 | 100.0% | 0.6% | 1 | Splitspalte: 2018-05-01: Tiingo-Faktor 1.489 an einem Tag mit Art „abspaltung“ |
| HSIC (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2019-02-08: Tiingo-Faktor 1.275 an einem Tag mit Art „abspaltung“ |
| FBIN (yfinance) | 3344 | 100.0% | 1.5% | 1 | Splitspalte: 2022-12-15: Tiingo-Faktor 1.17 an einem Tag mit Art „abspaltung“ |
| FTV (yfinance) | 2138 | 100.0% | 0.0% | 1.327 | Splitspalte: 2020-10-09: Tiingo-Faktor 1.195 an einem Tag mit Art „abspaltung“ |
| HWM (yfinance) | 2054 | 58.2% | 30.5% | 1 | nur 58.2% der Tage innerhalb 1 %; Splitspalte: 2016-10-06: Tiingo-Faktor 0.333333 ohne Yahoo-Ereignis; 2020-04-01: Tiingo-Faktor 1.304 ohne Yahoo-Ereignis |
| O (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2021-11-15: Tiingo-Faktor 1.032 an einem Tag mit Art „abspaltung“ |
| ILMN (yfinance) | 3522 | 100.0% | 0.1% | 1 | Splitspalte: 2024-06-25: Tiingo-Faktor 1.028 an einem Tag mit Art „abspaltung“ |
| BWA (yfinance) | 3522 | 100.0% | 2.2% | 1 | Splitspalte: 2023-07-05: Tiingo-Faktor 1.136 an einem Tag mit Art „abspaltung“ |
| FMC (yfinance) | 3522 | 100.0% | 0.6% | 1 | Splitspalte: 2019-03-04: Tiingo-Faktor 1.153 an einem Tag mit Art „abspaltung“ |
| JEF (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2019-09-27: Tiingo-Faktor 1.068 an einem Tag mit Art „abspaltung“; 2023-01-17: Tiingo-Faktor 1.046 an einem Tag mit Art „abspaltung“ |
| EXPE (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2011-12-21: Split 0.5 fehlt bei Tiingo (nicht in der Liste) |
| FTI (yfinance) | 3522 | 100.0% | 1.7% | 1 | Splitspalte: 2021-02-16: Tiingo-Faktor 1.344 an einem Tag mit Art „abspaltung“ |
| J (yfinance) | 3522 | 100.0% | 0.4% | 1.01 | Splitspalte: 2024-09-30: Tiingo-Faktor 1.197 an einem Tag mit Art „abspaltung“ |
| BX (yfinance) | 3522 | 66.1% | 1.9% | 1 | nur 66.1% der Tage innerhalb 1 % |
| GEV (yfinance) | 193 | 100.0% | 0.0% | 1 | nur 193 gemeinsame Tage |
| MTCH (yfinance) | 2293 | 50.6% | 250.2% | 0.2856 | nur 50.6% der Tage innerhalb 1 %; Splitspalte: 2020-07-01: Split 2.1584 fehlt bei Tiingo (Art kombiniert) |
| EQT (yfinance) | 3522 | 100.0% | 0.4% | 1 | Splitspalte: 2018-11-13: Tiingo-Faktor 1.837 an einem Tag mit Art „abspaltung“ |
| ECHO (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2019-09-11: Tiingo-Faktor 1.234 an einem Tag mit Art „abspaltung“ |
| FLEX (yfinance) | 3522 | 100.0% | 0.6% | 1 | Splitspalte: 2024-01-03: Tiingo-Faktor 1.327 an einem Tag mit Art „abspaltung“ |
| FERG (yfinance) | 3437 | 99.7% | 4.2% | 1 | Splitspalte: 2018-06-11: Yahoo 0.947 in der Liste unklar (nicht eingeordnet); 2013-11-29: Tiingo-Faktor 0.967742 ohne Yahoo-Ereignis |
| DELL (yfinance) | 1516 | 99.7% | 58.9% | 1 | Splitspalte: 2018-12-28: Yahoo 1.806 in der Liste unklar (nicht eingeordnet); 2021-11-02: Tiingo-Faktor 1.973 an einem Tag mit Art „abspaltung“ |
| AMTM (yfinance) | 69 | 100.0% | 0.0% | 1 | nur 69 gemeinsame Tage |
| DD (yfinance) | 3522 | 52.4% | 80.9% | 0.7967 | nur 52.4% der Tage innerhalb 1 %; Splitspalte: 2019-04-02: Tiingo-Faktor 1.487 an einem Tag mit Art „abspaltung“; 2017-09-01: Tiingo-Faktor 1.282 ohne Yahoo-Ereignis |
| CNX (yfinance) | 3522 | 100.0% | 9.0% | 1 | Splitspalte: 2017-11-29: Split 1.2 fehlt bei Tiingo (nicht in der Liste) |
| LH (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2023-07-03: Tiingo-Faktor 1.164 an einem Tag mit Art „abspaltung“ |
| IP (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2021-10-01: Tiingo-Faktor 1.056 an einem Tag mit Art „abspaltung“ |
| MRK (yfinance) | 3522 | 100.0% | 0.8% | 1 | Splitspalte: 2021-06-03: Tiingo-Faktor 1.048 an einem Tag mit Art „abspaltung“ |
| MAR (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2011-11-22: Split 1.061 fehlt bei Tiingo (nicht in der Liste) |
| EXC (yfinance) | 3522 | 100.0% | 2.3% | 1 | Splitspalte: 2022-02-02: Tiingo-Faktor 1.402 an einem Tag mit Art „abspaltung“ |
| DOV (yfinance) | 3522 | 100.0% | 0.5% | 1 | Splitspalte: 2018-05-09: Tiingo-Faktor 1.238 an einem Tag mit Art „abspaltung“ |
| EL (yfinance) | 3522 | 100.0% | 2.9% | 1 | Splitspalte: 2011-11-23: Tiingo-Faktor 1.05 ohne Yahoo-Ereignis |
| DTE (yfinance) | 3522 | 100.0% | 0.2% | 1 | Splitspalte: 2021-07-01: Tiingo-Faktor 1.175 an einem Tag mit Art „abspaltung“ |
| HON (yfinance) | 3522 | 100.0% | 0.4% | 1.012 | Splitspalte: 2018-10-01: Tiingo-Faktor 1.011 an einem Tag mit Art „abspaltung“; 2018-10-29: Tiingo-Faktor 1.032 an einem Tag mit Art „abspaltung“ |
| IBM (yfinance) | 3522 | 100.0% | 0.3% | 1 | Splitspalte: 2021-11-04: Tiingo-Faktor 1.046 an einem Tag mit Art „abspaltung“ |
| GE (yfinance) | 3522 | 100.0% | 0.8% | 1 | Splitspalte: 2023-01-04: Tiingo-Faktor 1.281 an einem Tag mit Art „abspaltung“; 2024-04-02: Tiingo-Faktor 1.253 an einem Tag mit Art „abspaltung“ |
| GHC (yfinance) | 3522 | 99.9% | 3.9% | 1 | Splitspalte: 2015-07-01: Split 1.655 fehlt bei Tiingo (nicht in der Liste) |
| MSI (yfinance) | 3522 | 100.0% | 3.2% | 1 | Splitspalte: 2011-01-04: Tiingo 0.142857 statt 0.247372 |
| NOC (yfinance) | 3522 | 100.0% | 0.0% | 1 | Splitspalte: 2011-03-31: Split 1.10681 fehlt bei Tiingo (nicht in der Liste) |
| PFE (yfinance) | 3522 | 100.0% | 0.9% | 1 | Splitspalte: 2020-11-17: Tiingo-Faktor 1.054 an einem Tag mit Art „abspaltung“ |
| BDX (yfinance) | 3522 | 100.0% | 0.6% | 1.272 | Splitspalte: 2022-04-01: Tiingo-Faktor 1.025 an einem Tag mit Art „abspaltung“ |
| BXLT (tiingo) | 242 | 100.0% | 0.0% | 1 | nur 242 gemeinsame Tage |

## Verdeckter Faktor H ≠ 1 (Split nach der Tresorgrenze; Rohkurs nötig) (18)

| Symbol (Quelle) | H |
| --- | --- |
| MNST (yfinance) | 2.0000 |
| CMCSA (yfinance) | 1.0670 |
| NFLX (yfinance) | 10.0000 |
| BKNG (yfinance) | 25.0000 |
| FAST (yfinance) | 2.0000 |
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
| APH (yfinance) | 2.0000 |
| ORLY (yfinance) | 15.0000 |
| DD (tiingo) | 0.3333 |

## Name bei Tiingo passt nicht zum Universum (4, nur Meldung)

| Symbol | Tiingo | Universum | Abnahme |
| --- | --- | --- | --- |
| CPAY | Fleetcor Technologies Inc | Corpay, Inc. | bestanden |
| LH | Laboratory Corp Of America Holdings | Labcorp Holdings Inc. | nicht bestanden |
| GE | General Electric Company | GE Aerospace | nicht bestanden |
| CVSA | Adtalem Global Education Inc | Covista Inc. | bestanden |

## Für c3 noch offen (158)

FDXF (yfinance), HONA (yfinance), META (yfinance), PRU (yfinance), PSA (yfinance), PSX (yfinance), PTC (yfinance), PVH (yfinance), PWR (yfinance), PYPL (yfinance), Q (yfinance), QCOM (yfinance), R (yfinance), RCL (yfinance), RDDT (yfinance), REG (yfinance), REGN (yfinance), RF (yfinance), RHI (yfinance), RIG (yfinance), RJF (yfinance), RL (yfinance), RMD (yfinance), ROK (yfinance), ROL (yfinance), ROP (yfinance), ROST (yfinance), RRC (yfinance), RSG (yfinance), RTX (yfinance), RVTY (yfinance), SBAC (yfinance), SBUX (yfinance), SCHW (yfinance), SEDG (yfinance), SHW (yfinance), SIG (yfinance), SJM (yfinance), SKYD (yfinance), SLB (yfinance), SLG (yfinance), SLM (yfinance), SMCI (yfinance), SNA (yfinance), SNDK (yfinance), SNPS (yfinance), SO (yfinance), SOLS (yfinance), SOLV (yfinance), SPG (yfinance), SPGI (yfinance), SRE (yfinance), STE (yfinance), STLD (yfinance), STT (yfinance), STX (yfinance), STZ (yfinance), SW (yfinance), SWK (yfinance), SWKS (yfinance), SYF (yfinance), SYK (yfinance), SYY (yfinance), T (yfinance), TAP (yfinance), TDC (yfinance), TDG (yfinance), TDY (yfinance), TECH (yfinance), TEL (yfinance), TER (yfinance), TFC (yfinance), TFX (yfinance), TGT (yfinance), THC (yfinance), TJX (yfinance), TKO (yfinance), TMO (yfinance), TMUS (yfinance), TNL (yfinance), TPL (yfinance), TPR (yfinance), TRGP (yfinance), TRIP (yfinance), TRMB (yfinance), TROW (yfinance), TRV (yfinance), TSCO (yfinance), TSLA (yfinance), TSN (yfinance), TT (yfinance), TTD (yfinance), TTWO (yfinance), TWLO (yfinance), TXN (yfinance), TXT (yfinance), TYL (yfinance), UAA (yfinance), UAL (yfinance), UBER (yfinance), UDR (yfinance), UHS (yfinance), ULTA (yfinance), UNH (yfinance), UNM (yfinance), UNP (yfinance), UPS (yfinance), URBN (yfinance), URI (yfinance), USB (yfinance), V (yfinance), VEEV (yfinance), VFC (yfinance), VIAV (yfinance), VICI (yfinance), VLO (yfinance), VLTO (yfinance), VMC (yfinance), VMRK (yfinance), VNO (yfinance), VNT (yfinance), VRSK (yfinance), VRSN (yfinance), VRT (yfinance), VRTX (yfinance), VST (yfinance), VTR (yfinance), VTRS (yfinance), VYLR (yfinance), VZ (yfinance), WAB (yfinance), WAT (yfinance), WDAY (yfinance), WDC (yfinance), WEC (yfinance), WELL (yfinance), WFC (yfinance), WHR (yfinance), WM (yfinance), WMB (yfinance), WMT (yfinance), WRB (yfinance), WSM (yfinance), WST (yfinance), WTW (yfinance), WU (yfinance), WY (yfinance), WYNN (yfinance), XEL (yfinance), XOM (yfinance), XRAY (yfinance), XYL (yfinance), XYZ (yfinance), YUM (yfinance), ZBH (yfinance), ZBRA (yfinance), ZION (yfinance), ZTS (yfinance)

## Ursachen der Verfehlung (Claude, 16.11.2026; nichts angepasst, Entscheidung bei Jakob)

Erster Lauf mit dem Kriterium „Splitspalte“ (Befund 10, festgehalten 11:21). Fehlerschwelle überschritten: 44 von 563
Reihen (7,8 % > 5 %); c3 ist damit technisch gesperrt (Befund 14). Ohne das neue Kriterium wären es 7 (1,2 %).

| Gruppe | Reihen | Fälle |
| --- | --- | --- |
| Erstes Kriterium (wie 15.11.) | 7 | HWM, BX, MTCH, DD (Abweichungen), GEV, AMTM, BXLT (zu kurz) |
| Nur Splitspalte: Tiingo führt eine Abspaltung der Liste als Split | 26 | BFH, PNR, HSIC, FBIN, FTV, O, ILMN, BWA, FMC, JEF (2), FTI, J, EQT, ECHO, FLEX, LH, IP, MRK, EXC, DOV, DTE, HON (2), IBM, GE (2), PFE, BDX |
| Nur Splitspalte: Ereignis 2011, nicht in der Liste | 5 | EXPE, MAR, EL, MSI, NOC |
| Nur Splitspalte: übrige | 6 | GOOG, GOOGL (Class-C-Ausgabe 2014, fehlt bei Tiingo), GHC 2015, CNX 2017 (nicht in der Liste, fehlt bei Tiingo), FERG, DELL (in der Liste „unklar“) |

- **Abspaltungen als Tiingo-Split sind häufig, nicht selten** (31 Ereignisse in 26 Reihen; am 15.11. waren nur MRK und
  IBM bekannt). Alle 31 liegen exakt auf dem Datum der Liste. Die Marktwert-Formel nimmt sie über K(d, T) mit s_e = 1
  heraus; der zweite Probelauf vom 15.11. fand deshalb keine ungeklärten Tiingo-Faktoren. Falsch rechnet mit ihnen nur die
  Prüfung der Streubesitzwerte, die K nicht anwendet (Befund 12).
- **Ereignisse 2011** liegen vor jedem Messtag einer Aktienzahl, die für die gewerteten Stichtage ab 01.10.2016 zählt; die
  Liste beginnt 2012.
- **Nebenwirkung von Variante B:** FTV (H 1,327), J (1,01), HON (1,012) und BDX (1,272) scheitern nur an
  Tiingo-Abspaltungsfaktoren und verlören deshalb ihren Marktwert, obwohl der Rohkurs-Marktwert für sie richtig ist.
