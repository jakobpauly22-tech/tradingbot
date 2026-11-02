# Rechenweg: Apple Inc., Geschäftsjahr 2019 (Ende 28.09.2019)

Stichtag 2019-11-01 (Tag nach Bekanntwerden des 10-K). Werte in Mio. USD. Quelle: SEC-XBRL-Fakten (Erstmeldung).
Abgeleitete Werte sind mit „abgeleitet“ markiert (Regeln in `engines/fundamental/kennzahlen.py`).

## Eingangswerte

| Posten | Teil | GJ 2019-09-28 | GJ 2018-09-29 | GJ 2017-09-30 | Begriff / Fundstelle |
| --- | --- | --- | --- | --- | --- |
| abschreibungen | Kapitalflussrechnung | 12.547 | 10.903 | 8.200 | us-gaap:DepreciationDepletionAndAmortization; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| bilanzsumme | Bilanz | 338.516 | 365.725 | 375.319 | us-gaap:Assets; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| bruttoergebnis | GuV | 98.392 | 101.839 | 88.186 | us-gaap:GrossProfit; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| eigenkapital | Bilanz | 90.488 | 107.147 | 134.047 | us-gaap:StockholdersEquity; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| eigenkapital_inkl_minderheiten | Bilanz | 90.488 | 107.147 | 134.047 | us-gaap:StockholdersEquity; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| ergebnis_vor_steuern | GuV | 65.737 | 72.903 | 64.089 | us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| forderungen | Bilanz | 22.926 | 23.186 | 17.874 | us-gaap:AccountsReceivableNetCurrent; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| gewichtete_aktien | GuV (EPS) | 4.618 | 4.955 | 5.217 | us-gaap:WeightedAverageNumberOfSharesOutstandingBasic; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| gewinnruecklagen | Bilanz | 45.898 | 70.400 | 98.330 | us-gaap:RetainedEarningsAccumulatedDeficit; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| jahresueberschuss | GuV | 55.256 | 59.531 | 48.351 | us-gaap:NetIncomeLoss; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| kurzfristige_verbindlichkeiten | Bilanz | 105.718 | 116.866 | 100.814 | us-gaap:LiabilitiesCurrent; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| langfristige_finanzschulden | Bilanz | 91.807 | 93.735 | 97.207 | us-gaap:LongTermDebtNoncurrent; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| operativer_cashflow | Kapitalflussrechnung | 69.391 | 77.434 | 63.598 | us-gaap:NetCashProvidedByUsedInOperatingActivities; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| operatives_ergebnis | GuV | 63.930 | 70.898 | 61.344 | us-gaap:OperatingIncomeLoss; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| sachanlagen_netto | Bilanz | 37.378 | 41.304 | 33.783 | us-gaap:PropertyPlantAndEquipmentNet; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| umlaufvermoegen | Bilanz | 162.819 | 131.339 | 128.645 | us-gaap:AssetsCurrent; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| umsatz | GuV | 260.174 | 265.595 | 229.234 | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| umsatzkosten | GuV | 161.782 | 163.756 | 141.048 | us-gaap:CostOfGoodsAndServicesSold; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| verbindlichkeiten | Bilanz | 248.028 | 258.578 | 241.272 | us-gaap:Liabilities; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| vertriebs_verwaltungskosten | GuV | 18.245 | 16.705 | 15.261 | us-gaap:SellingGeneralAndAdministrativeExpense; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |
| zinsaufwand | GuV/Anhang | 3.576 | 3.240 | 2.323 | us-gaap:InterestExpense; 10-K 0000320193-19-000119 vom 2019-10-31 ([Index](https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119-index.htm)) |

## Piotroski F-Score

Formeln im Docstring von `scores.piotroski` (Piotroski 2000). Ursprünglich für Value-Aktien, hier allgemeiner Qualitätsfilter.

| Signal | Rechnung | Wert | Punkt |
| --- | --- | --- | --- |
| ROA > 0 | JÜ_t / BS_t−1 = 55.256 / 365.725 | 0.1511 | 1 |
| CFO > 0 | CF_t / BS_t−1 = 69.391 / 365.725 | 0.1897 | 1 |
| ΔROA > 0 | ROA_t − ROA_t−1, ROA_t−1 = 59.531 / 375.319 = 0.1586 | -0.0075 | 0 |
| ACCRUAL | CFO > ROA | 0.1897 vs. 0.1511 | 1 |
| ΔLEVER ≤ 0 | LFS/Ø BS: t 0.2607, t−1 0.2530 | +0.0077 | 0 |
| ΔLIQUID > 0 | UV/kfr. Verb.: t 1.5401, t−1 1.1238 | +0.4163 | 1 |
| EQ_OFFER | gew. Aktien t ≤ t−1: 4.618 vs. 4.955 (Mio. Stück) | – | 1 |
| ΔMARGIN > 0 | Bruttomarge: t 0.3782, t−1 0.3834 | -0.0053 | 0 |
| ΔTURN > 0 | Umsatz/BS_Vorjahr: t 0.7114, t−1 0.7077 | +0.0037 | 1 |

**F-Score = 6**

## Beneish M-Score (8 Variablen)

Formeln im Docstring von `scores.beneish` (Beneish 1999). Gewichte: −4,84 + 0,920·DSRI + 0,528·GMI + 0,404·AQI + 0,892·SGI + 0,115·DEPI − 0,172·SGAI + 4,679·TATA − 0,327·LVGI.

| Variable | Wert | Gewicht | Beitrag |
| --- | --- | --- | --- |
| DSRI | 1.0094 | +0.920 | +0.9286 |
| GMI | 1.0139 | +0.528 | +0.5353 |
| AQI | 0.7740 | +0.404 | +0.3127 |
| SGI | 0.9796 | +0.892 | +0.8738 |
| DEPI | 0.8310 | +0.115 | +0.0956 |
| SGAI | 1.1149 | -0.172 | -0.1918 |
| TATA | -0.0418 | +4.679 | -0.1954 |
| LVGI | 1.0133 | -0.327 | -0.3313 |

**M = -2.8125** (Konstante −4,84); Schwelle −1,78 → unauffällig

## Altman Z (1968, verarbeitendes Gewerbe)

Marktwert EK am Stichtag = Schlusskurs 2019-11-01 × ausstehende Aktien laut Deckblatt (2019-10-18, 10-K): 255.82 USD × 4,443,265,000 = **1,136,676 Mio. USD** (Kurs unbereinigt; spätere Splits Faktor 4 herausgerechnet).

| Bestandteil | Wert | Gewicht | Beitrag |
| --- | --- | --- | --- |
| X1 = (UV − kfr. Verb.)/BS | 0.1687 | 1.2 | +0.2024 |
| X2 = Gewinnrücklagen/BS | 0.1356 | 1.4 | +0.1898 |
| X3 = EBIT/BS | 0.1889 | 3.3 | +0.6232 |
| X4 = Marktwert EK/Verbindlichkeiten | 4.5829 | 0.6 | +2.7497 |
| X5 = Umsatz/BS | 0.7686 | 1.0 | +0.7686 |

**Z = 4.5337** → Zone: sicher (Gefahr < 1.81, sicher > 2.99)