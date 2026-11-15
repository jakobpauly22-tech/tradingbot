# Abnahme der Rohreihen für den Marktwert (c2 (2))

Erstellt 15.11.2026 11:17 mit `tools/pruefe_rohkurse.py`. Kriterien vor dem Lauf festgehalten (docs/FUNDAMENTAL.md, „c2 (2): Marktwert aus Rohkursen – Abnahme und Stichprobe“): Vergleich nur gegen splitbereinigte Reihen, ≥ 250 Tage, |v/(H·Πf) − 1| ≤ 1 % an ≥ 99 % der Tage. Nichts wurde angepasst.

Gültige Reihen: 721. Mit Rohreihe: 563, davon bestanden 556, nicht bestanden 7. Ohne Rohreihe: 158. Für c3 noch offen (ohne Abnahme, nicht dauerhaft unverfügbar): 158.

## Nicht bestanden (7)

| Symbol (Quelle) | Tage | Anteil ≤ 1 % | größte Abweichung | H | Grund |
| --- | --- | --- | --- | --- | --- |
| HWM (yfinance) | 2054 | 58.2% | 30.5% | 1 | nur 58.2% der Tage innerhalb 1 % |
| BX (yfinance) | 3522 | 66.1% | 1.9% | 1 | nur 66.1% der Tage innerhalb 1 % |
| GEV (yfinance) | 193 | 100.0% | 0.0% | 1 | nur 193 gemeinsame Tage |
| MTCH (yfinance) | 2293 | 50.6% | 250.2% | 0.2856 | nur 50.6% der Tage innerhalb 1 % |
| AMTM (yfinance) | 69 | 100.0% | 0.0% | 1 | nur 69 gemeinsame Tage |
| DD (yfinance) | 3522 | 52.4% | 80.9% | 0.7967 | nur 52.4% der Tage innerhalb 1 % |
| BXLT (tiingo) | 242 | 100.0% | 0.0% | 1 | nur 242 gemeinsame Tage |

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
