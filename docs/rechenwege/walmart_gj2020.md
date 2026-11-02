# Rechenweg: Walmart Inc., Geschäftsjahr 2020 (Ende 31.01.2020)

Stichtag 2020-03-25 (Tag nach Bekanntwerden des 10-K). Werte in Mio. USD. Quelle: SEC-XBRL-Fakten (Erstmeldung).
Abgeleitete Werte sind mit „abgeleitet“ markiert (Regeln in `engines/fundamental/kennzahlen.py`).

## Eingangswerte

| Posten | Teil | GJ 2020-01-31 | GJ 2019-01-31 | GJ 2018-01-31 | Begriff / Fundstelle |
| --- | --- | --- | --- | --- | --- |
| abschreibungen | Kapitalflussrechnung | 10.987 | 10.678 | 10.529 | us-gaap:DepreciationAmortizationAndAccretionNet; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| bilanzsumme | Bilanz | 236.495 | 219.295 | 204.522 | us-gaap:Assets; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| bruttoergebnis | GuV | 129.359 (abgeleitet) | 129.104 (abgeleitet) | 126.947 (abgeleitet) | abgeleitet bzw. siehe Vorjahres-10-K |
| eigenkapital | Bilanz | 74.669 | 72.496 | 77.869 | us-gaap:StockholdersEquity; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| eigenkapital_inkl_minderheiten | Bilanz | 81.552 | 79.634 | 80.822 | us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| ergebnis_vor_steuern | GuV | 20.116 | 11.460 | 15.123 | us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest; 10-K 0000104169-22-000012 vom 2022-03-18 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416922000012/0000104169-22-000012-index.htm)) |
| forderungen | Bilanz | 6.284 | 6.283 | 5.614 | us-gaap:ReceivablesNetCurrent; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| gewichtete_aktien | GuV (EPS) | 2.850 | 2.929 | 2.995 | us-gaap:WeightedAverageNumberOfSharesOutstandingBasic; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| gewinnruecklagen | Bilanz | 83.943 | 80.785 | 85.107 | us-gaap:RetainedEarningsAccumulatedDeficit; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| jahresueberschuss | GuV | 14.881 | 6.670 | 9.862 | us-gaap:NetIncomeLoss; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| kurzfristige_verbindlichkeiten | Bilanz | 77.790 | 77.477 | 78.521 | us-gaap:LiabilitiesCurrent; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| langfristige_finanzschulden | Bilanz | 43.714 | 43.520 | 30.045 | us-gaap:LongTermDebtNoncurrent; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| operativer_cashflow | Kapitalflussrechnung | 25.255 | 27.753 | 28.337 | us-gaap:NetCashProvidedByUsedInOperatingActivities; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| operatives_ergebnis | GuV | 20.568 | 21.957 | 20.437 | us-gaap:OperatingIncomeLoss; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| sachanlagen_netto | Bilanz | 105.208 | 104.317 | 107.675 | us-gaap:PropertyPlantAndEquipmentNet; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| umlaufvermoegen | Bilanz | 61.806 | 61.897 | 59.664 | us-gaap:AssetsCurrent; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| umsatz | GuV | 523.964 | 514.405 | 500.343 | us-gaap:Revenues; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| umsatzkosten | GuV | 394.605 | 385.301 | 373.396 | us-gaap:CostOfRevenue; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |
| verbindlichkeiten | Bilanz | 154.943 (abgeleitet) | 139.661 (abgeleitet) | 123.700 (abgeleitet) | abgeleitet bzw. siehe Vorjahres-10-K |
| vertriebs_verwaltungskosten | GuV | 108.791 | 107.147 | 106.510 | us-gaap:SellingGeneralAndAdministrativeExpense; 10-K 0000104169-20-000011 vom 2020-03-20 ([Index](https://www.sec.gov/Archives/edgar/data/104169/000010416920000011/0000104169-20-000011-index.htm)) |

## Altman Z'' (übrige Firmen)



| Bestandteil | Wert | Gewicht | Beitrag |
| --- | --- | --- | --- |
| X1 = (UV − kfr. Verb.)/BS | -0.0676 | 6.56 | -0.4434 |
| X2 = Gewinnrücklagen/BS | 0.3549 | 3.26 | +1.1571 |
| X3 = EBIT/BS | 0.0870 | 6.72 | +0.5844 |
| X4 = Buchwert EK/Verbindlichkeiten | 0.5263 | 1.05 | +0.5527 |

**Z'' = 1.8508** → Zone: grau (Gefahr < 1.1, sicher > 2.6)