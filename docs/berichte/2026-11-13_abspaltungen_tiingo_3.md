# Teil c1: Abspaltungen in Tiingo-Reihen – dritter Lauf

Erstellt 15.11.2026 00:29 mit `tools/pruefe_abspaltungen_tiingo.py`. Kriterien zweimal nach einer Suche geändert und jeweils vorher festgehalten (docs/FUNDAMENTAL.md): S1 Gesamtrendite ≤ −3 % (auch über zwei Tage), S2 Volltext aller 8-K im Fenster −30 … +5 Tage mit „spin-off“, „spinoff“, „spin off“, „separation and distribution“ oder „distribution of all“. Nichts wurde korrigiert.

Grundmenge: 118 Mitgliedschaften mit Tiingo-Reihe. Treffer: 509 Ereignisse. Unklar (≤ −15 % ohne S2): 146.

## Probe

- CSC 2015-11-30: gefunden (muss Treffer sein)
- TGNA 2017-06-01: kein Treffer (darf kein Treffer sein)
- TWX 2014-06-06: TREFFER (darf nicht) (darf kein Treffer sein)
- TWX 2014-06-09: kein Treffer (darf kein Treffer sein)

## S2 an den Abspaltungen aus Teil a

- LDOS 2013-09-30 (CIK 1336920): gefunden – 8-K/A 2013-09-04 (0001193125-13-356282): spin-off; 8-K 2013-09-04 (0001193125-13-356120): spin-off; 8-K 2013-09-10 (0001193125-13-362164): spin-off, spinoff
- CSC/DXC 2015-11-30 (CIK 23082): gefunden – 8-K 2015-11-04 (0000023082-15-000060): distribution of all, spin-off; 8-K 2015-11-30 (0000023082-15-000078): spin-off; 8-K 2015-12-02 (0000023082-15-000081): separation and distribution, spin-off
- OXY 2016-02-25 (CIK 797468): gefunden – 8-K 2016-02-04 (0001104659-16-093778): spin-off
- HLT 2017-01-04 (CIK 1585689): gefunden – 8-K 2016-12-05 (0001193125-16-784419): spin-off; 8-K 2016-12-08 (0001193125-16-787940): spin-off; 8-K 2017-01-04 (0001193125-17-001901): spin-off, spinoff
- DD (Dow) 2019-04-02 (CIK 1666700): gefunden – 8-K 2019-03-13 (0001666700-19-000010): spin-off; 8-K 2019-04-02 (0001193125-19-095042): distribution of all, separation and distribution, spin-off
- DD (Corteva) 2019-06-03 (CIK 1666700): gefunden – 8-K 2019-05-23 (0001666700-19-000023): distribution of all, spin-off; 8-K 2019-06-03 (0001193125-19-163322): distribution of all, separation and distribution, spin-off; 8-K 2019-06-07 (0001666700-19-000056): distribution of all, spin-off
- MTCH 2020-07-01 (CIK 891103): gefunden – 8-K 2020-07-02 (0001104659-20-080606): spin-off

## Stichprobe (10 Treffer, Startwert 13112026) mit Ausschnitt aus dem 8-K

- **COV 2014-09-30** (-3.9%): 8-K 2014-09-23 (0001193125-14-350066): spin-off — „… stock split, dividend or other distribution (whether in the form of cash, Shares, other securities or other property), extraordinary cash dividend, recapitalization, merger, consolidation, split-up, spin-off, reorganization, combination, repurchase or exchange of Shares or other securities, the issuance of warrants or other rights to purchase Shares or other securities, or other similar corporate…“
- **NLSN 2020-05-12** (-12.1%): 8-K 2020-04-29 (0001193125-20-126532): spin-off; 8-K 2020-04-30 (0001564590-20-019934): spin-off, spinoff — „…severance that may become due upon a qualifying termination of employment under the Severance Policy, and (2) a Severance Policy participant will not be entitled to severance as a result of a sale or spin-off of a business unit that employs the participant if the participant is offered a comparable position with the buyer or any affiliate thereof, the spun-off entity or the Company or any of its a…“
- **EA 2021-03-04** (-4.1%): 8-K 2021-02-08 (0001193125-21-032346): spin-off — „…ted assets or to which more than 15% of the Company s revenues or earnings on a consolidated basis are attributable, (ii) direct or indirect acquisition or issuance (whether by merger, consolidation, spin-off, share exchange (including a split-off), business combination or otherwise or similar transaction involving an acquisition or issuance) of more than 15% of any class of voting equity securiti…“
- **COV 2014-08-06** (-4.6%): 8-K 2014-07-11 (0001385187-14-000025): distribution of all, spin off — „…, began trading on the New York Stock Exchange on June 5, 2009, under the symbol COV, the same symbol under which Covidien Ltd. shares were previously traded. On June 28, 2013, Covidien completed the spin off of its Pharmaceuticals business to Covidien shareholders, through a distribution of all of the outstanding ordinary shares of Mallinckrodt plc, the company formed to hold Covidien s former Ph…“
- **WPX 2012-06-13** (-6.3%): 8-K 2012-05-15 (0001193125-12-235045): separation and distribution, spin-off, spinoff — „…rcent ownership interest in Apco in October 2011. We refer to the collective contributions described herein as the Contribution . On November 30, 2011, the Board of Directors of Williams approved the spin-off of the Company. The spin-off was completed by way of a pro rata distribution on December 31, 2011, of WPX common stock to Williams stockholders of record as of the close of business on Decemb…“
- **NLSN 2020-05-29** (-4.9%): 8-K 2020-04-29 (0001193125-20-126532): spin-off; 8-K 2020-04-30 (0001564590-20-019934): spin-off, spinoff — „…severance that may become due upon a qualifying termination of employment under the Severance Policy, and (2) a Severance Policy participant will not be entitled to severance as a result of a sale or spin-off of a business unit that employs the participant if the participant is offered a comparable position with the buyer or any affiliate thereof, the spun-off entity or the Company or any of its a…“
- **CFN 2012-07-24** (-3.6%): 8-K 2012-07-02 (0001193125-12-292062): spin-off — „…; (c) acknowledges previously accepting, and voluntarily and knowingly accepts, the terms of the equity awards of the Company and/or Cardinal Health, Inc. that Awardee received in connection with the spin-off of the Company from Cardinal Health, Inc., subject to all the provisions of the applicable equity incentive plan(s) under which the award(s) was granted; and (d) represents that he or she und…“
- **TWTR 2020-03-27** (-8.9%): 8-K 2020-03-09 (0001193125-20-067362): spin-off; 8-K 2020-03-13 (0001193125-20-072915): spin-off — „… cash amount per $1,000 principal amount of Notes to be received upon conversion as specified (or deemed specified pursuant to this Indenture) in the Settlement Notice related to any converted Notes. Spin-Off shall have the meaning specified in Section 13.04(c). Sponsor Global Notes means the Global Notes issued and authenticated on the Issue Date with an initial balance of $1,000,000,000 and iden…“
- **TFCF 2017-12-13** (-3.7%): 8-K 2017-12-14 (0001193125-17-368807): separation and distribution, spin off, spin-off, spinoff; 8-K 2017-12-15 (0001193125-17-370718): separation and distribution, spin-off — „…ders. A copy of the joint press release is filed as Exhibit 99.1 hereto and is incorporated herein by reference. On December 14, 2017, the Company issued a press release announcing that it intends to spin-off to its shareholders a portfolio of the Company s news, sports and broadcast businesses, including the Fox News Channel, Fox Business Network, Fox Broadcasting Company, Fox Sports, Fox Televis…“
- **SRCL 2017-11-09** (-4.6%): 8-K 2017-10-18 (0001564590-17-019576): spin-off — „…n VIII of this Agreement and in the Final Order and Final Judgment. 35. Released Parties or Released Party means Stericycle and each of its past, present and future parents, predecessors, successors, spin-offs, assigns, holding companies, joint-ventures and joint-venturers, partnerships and partners, members, divisions, stockholders, bondholders, subsidiaries, related companies, affiliates, office…“

## Treffer

| Ticker (CIK) | Name | Tage | Gesamtrendite (schlechteste) | SEC-Beleg (S2) |
| --- | --- | --- | --- | --- |
| AET (1122304) | Aetna | 2017-02-17 | -3.3% | 8-K 2017-02-22 (0000950103-17-001608): spin-off |
| AGN (1578845) | Allergan | 2014-06-05 | -3.4% | 8-K 2014-05-20 (0001193125-14-205703): distribution of all |
| AGN (1578845) | Allergan | 2014-11-20 | -4.1% | 8-K 2014-11-17 (0001193125-14-415382): spin-off; 8-K/A 2014-11-18 (0001193125-14-416032): spin-off |
| AGN (1578845) | Allergan | 2014-12-23 | -3.6% | 8-K 2014-12-05 (0001193125-14-434971): distribution of all; 8-K 2014-12-22 (0001193125-14-449447): spin-off |
| AGN (1578845) | Allergan | 2015-03-25 | -4.6% | 8-K 2015-03-02 (0001193125-15-073589): spin-off; 8-K 2015-03-12 (0001193125-15-089341): spin-off; 8-K 2015-03-13 (0001193125-15-091325): spin-off |
| AGN (1578845) | Allergan | 2018-10-24 bis 2018-10-31 | -9.3% | 8-K 2018-11-01 (0001193125-18-314269): spin-off |
| AGN (1578845) | Allergan | 2018-11-14 | -3.8% | 8-K 2018-11-01 (0001193125-18-314269): spin-off |
| BBBY (886158) | Bed Bath & Beyond | 2012-06-21 bis 2012-06-25 | -18.1% | 8-K 2012-06-26 (0001104659-12-045877): spin-off |
| BCR (9892) | CR Bard | 2014-04-23 bis 2014-04-24 | -3.3% | 8-K 2014-04-17 (0001193125-14-147626): spin-off |
| BCR (9892) | CR Bard | 2015-04-29 | -3.4% | 8-K 2015-04-17 (0001193125-15-133767): spin-off |
| BHI (808362) | Baker Hughes | 2012-01-11 bis 2012-01-13 | -7.0% | 8-K 2011-12-20 (0001193125-11-347264): distribution of all |
| BHI (808362) | Baker Hughes | 2014-05-09 | -3.4% | 8-K 2014-04-29 (0000808362-14-000028): spin-off |
| BHI (808362) | Baker Hughes | 2016-05-24 | -3.0% | 8-K 2016-05-25 (0000950103-16-013575): spin-off |
| BHI (808362) | Baker Hughes | 2016-06-08 bis 2016-06-13 | -4.3% | 8-K 2016-05-25 (0000950103-16-013575): spin-off |
| BHI (808362) | Baker Hughes | 2016-06-24 bis 2016-06-28 | -10.8% | 8-K 2016-05-25 (0000950103-16-013575): spin-off |
| BHI (808362) | Baker Hughes | 2016-10-31 bis 2016-11-01 | -6.4% | 8-K 2016-11-01 (0000950103-16-017539): spin-off |
| BHI (808362) | Baker Hughes | 2017-04-21 | -3.1% | 8-K 2017-03-31 (0000950103-17-003027): spin-off |
| CELG (816284) | Celgene | 2017-06-30 | -3.2% | 8-K 2017-06-14 (0001571049-17-005959): spin-off |
| CELG (816284) | Celgene | 2018-01-17 | -3.8% | 8-K 2018-01-22 (0001144204-18-002997): spin-off |
| CELG (816284) | Celgene | 2018-01-30 | -3.4% | 8-K 2018-01-22 (0001144204-18-002997): spin-off |
| CELG (816284) | Celgene | 2018-02-05 bis 2018-02-08 | -6.6% | 8-K 2018-01-22 (0001144204-18-002997): spin-off |
| CFN (1457543) | Carefusion | 2012-01-09 bis 2012-01-10 | -9.8% | 8-K 2012-01-09 (0001193125-12-005920): spinoff |
| CFN (1457543) | Carefusion | 2012-07-24 | -3.6% | 8-K 2012-07-02 (0001193125-12-292062): spin-off |
| CFN (1457543) | Carefusion | 2013-02-25 | -3.3% | 8-K 2013-01-31 (0001193125-13-032726): spinoff; 8-K 2013-02-07 (0001193125-13-043452): spinoff |
| CFN (1457543) | Carefusion | 2013-05-10 | -3.1% | 8-K 2013-04-25 (0001193125-13-173896): spinoff; 8-K 2013-05-09 (0001193125-13-211029): spinoff |
| CFN (1457543) | Carefusion | 2013-08-02 bis 2013-08-05 | -6.0% | 8-K 2013-08-08 (0001193125-13-326828): spinoff; 8-K 2013-08-08 (0001193125-13-326817): spinoff |
| CFN (1457543) | Carefusion | 2013-08-15 bis 2013-08-16 | -4.4% | 8-K 2013-08-08 (0001193125-13-326828): spinoff; 8-K 2013-08-08 (0001193125-13-326817): spinoff |
| CMA (28412) | Comerica | 2022-11-17 | -4.2% | 8-K 2022-11-14 (0000028412-22-000168): spin-off |
| CMA (28412) | Comerica | 2022-12-05 bis 2022-12-06 | -7.1% | 8-K 2022-11-14 (0000028412-22-000168): spin-off |
| COL (1137411) | Rockwell Collins | 2016-10-24 bis 2016-10-25 | -6.2% | 8-K 2016-10-27 (0001104659-16-152312): spin-off |
| COL (1137411) | Rockwell Collins | 2016-11-02 | -3.2% | 8-K 2016-10-27 (0001104659-16-152312): spin-off |
| CSC (23082) | Computer Sciences Corporation | 2012-02-07 | -5.7% | 8-K 2012-02-08 (0001104659-12-007786): distribution of all |
| CSC (23082) | Computer Sciences Corporation | 2012-02-21 bis 2012-02-22 | -3.9% | 8-K 2012-02-08 (0001104659-12-007786): distribution of all |
| CSC (23082) | Computer Sciences Corporation | 2012-03-07 | -3.1% | 8-K 2012-02-08 (0001104659-12-007786): distribution of all |
| CSC (23082) | Computer Sciences Corporation | 2012-03-20 | -3.6% | 8-K 2012-03-16 (0000023082-12-000019): distribution of all |
| CSC (23082) | Computer Sciences Corporation | 2012-04-04 | -3.8% | 8-K 2012-03-16 (0000023082-12-000019): distribution of all |
| CSC (23082) | Computer Sciences Corporation | 2012-04-10 bis 2012-04-11 | -4.3% | 8-K 2012-03-16 (0000023082-12-000019): distribution of all |
| CSC (23082) | Computer Sciences Corporation | 2015-08-20 bis 2015-08-25 | -7.3% | 8-K 2015-08-12 (0000023082-15-000037): spin off |
| CSC (23082) | Computer Sciences Corporation | 2015-09-01 | -4.5% | 8-K 2015-08-12 (0000023082-15-000037): spin off; 8-K 2015-09-01 (0000023082-15-000045): spin-off, spinoff; 8-K 2015-09-01 (0000023082-15-000043): spin-off |
| CSC (23082) | Computer Sciences Corporation | 2015-11-13 | -3.4% | 8-K 2015-11-04 (0000023082-15-000060): distribution of all, spin-off |
| CSC (23082) | Computer Sciences Corporation | 2015-11-30 bis 2015-12-03 | -39.8% | 8-K 2015-11-04 (0000023082-15-000060): distribution of all, spin-off; 8-K 2015-11-30 (0000023082-15-000078): spin-off; 8-K 2015-12-02 (0000023082-15-000081): separation and distribution, spin-off |
| CTXS (877890) | Citrix Systems | 2015-08-21 bis 2015-08-25 | -11.7% | 8-K 2015-07-28 (0001193125-15-266066): spin-off |
| CTXS (877890) | Citrix Systems | 2015-11-13 | -3.7% | 8-K 2015-11-17 (0001157523-15-003875): spin off, spin-off, spinoff |
| CTXS (877890) | Citrix Systems | 2015-11-18 bis 2015-11-19 | -11.2% | 8-K 2015-11-17 (0001157523-15-003875): spin off, spin-off, spinoff |
| CTXS (877890) | Citrix Systems | 2015-12-03 | -3.1% | 8-K 2015-11-17 (0001157523-15-003875): spin off, spin-off, spinoff |
| CTXS (877890) | Citrix Systems | 2016-01-27 | -3.4% | 8-K 2016-01-27 (0001157523-16-004309): spin-off, spinoff |
| CTXS (877890) | Citrix Systems | 2016-02-02 bis 2016-02-08 | -6.5% | 8-K 2016-01-27 (0001157523-16-004309): spin-off, spinoff |
| CTXS (877890) | Citrix Systems | 2016-08-02 | -6.4% | 8-K 2016-07-26 (0001157523-16-006193): spin-off; 8-K 2016-07-28 (0001193125-16-661270): distribution of all, separation and distribution, spin off, spin-off, spinoff |
| CTXS (877890) | Citrix Systems | 2016-09-09 | -4.6% | 8-K 2016-09-01 (0001193125-16-699644): spin-off |
| CTXS (877890) | Citrix Systems | 2017-01-26 bis 2017-01-27 | -6.5% | 8-K 2017-01-06 (0001193125-17-004612): spin-off; 8-K 2017-01-20 (0001193125-17-013672): spin-off; 8-K 2017-01-25 (0001157523-17-000161): spin-off |
| CTXS (877890) | Citrix Systems | 2017-04-27 bis 2017-04-28 | -3.8% | 8-K 2017-04-26 (0001157523-17-001201): spin-off |
| CTXS (877890) | Citrix Systems | 2017-05-17 | -4.2% | 8-K 2017-04-26 (0001157523-17-001201): spin-off |
| CTXS (877890) | Citrix Systems | 2018-02-05 bis 2018-02-08 | -5.2% | 8-K 2018-02-05 (0001193125-18-030997): spin-off |
| CTXS (877890) | Citrix Systems | 2020-01-29 | -3.1% | 8-K 2020-01-31 (0001193125-20-020301): spin-off |
| CTXS (877890) | Citrix Systems | 2020-02-20 bis 2020-02-28 | -6.4% | 8-K 2020-01-31 (0001193125-20-020301): spin-off |
| DD (30554) | DuPont | 2014-01-23 bis 2014-01-24 | -4.8% | 8-K 2014-01-28 (0001104659-14-004510): spinoff |
| DD (30554) | DuPont | 2014-06-27 bis 2014-06-30 | -3.5% | 8-K 2014-06-26 (0000030554-14-000039): spinoff |
| DD (30554) | DuPont | 2014-12-12 bis 2014-12-15 | -3.3% | 8-K 2014-12-18 (0000030554-14-000072): spinoff; 8-K/A 2014-12-18 (0000030554-14-000071): spinoff |
| DD (30554) | DuPont | 2015-01-05 bis 2015-01-06 | -3.8% | 8-K 2014-12-18 (0000030554-14-000072): spinoff; 8-K/A 2014-12-18 (0000030554-14-000071): spinoff |
| DD (30554) | DuPont | 2015-01-28 | -3.2% | 8-K 2015-01-27 (0000030554-15-000002): spinoff |
| DD (30554) | DuPont | 2015-03-25 | -3.2% | 8-K 2015-03-30 (0001104659-15-023627): spin-off, spinoff |
| DD (30554) | DuPont | 2015-05-13 bis 2015-05-14 | -7.4% | 8-K 2015-04-21 (0000030554-15-000018): spin-off, spinoff; 8-K 2015-05-13 (0000030554-15-000027): spinoff |
| DD (30554) | DuPont | 2015-06-05 | -3.1% | 8-K 2015-05-13 (0000030554-15-000027): spinoff |
| DD (30554) | DuPont | 2015-07-08 | -3.1% | 8-K 2015-07-08 (0000030554-15-000065): distribution of all, spin-off |
| DD (30554) | DuPont | 2015-07-24 | -3.3% | 8-K 2015-07-08 (0000030554-15-000065): distribution of all, spin-off |
| DD (30554) | DuPont | 2015-12-11 bis 2015-12-15 | -8.9% | 8-K 2015-12-11 (0001104659-15-084413): spin-off |
| DD (30554) | DuPont | 2015-12-18 | -4.3% | 8-K 2015-12-11 (0001104659-15-084413): spin-off |
| DD (30554) | DuPont | 2016-01-04 bis 2016-01-19 | -7.3% | 8-K 2015-12-11 (0001104659-15-084413): spin-off |
| DD (30554) | DuPont | 2016-01-25 bis 2016-01-27 | -3.7% | 8-K 2016-01-26 (0000030554-16-000102): spin-off |
| DD (30554) | DuPont | 2016-02-11 | -3.5% | 8-K 2016-01-26 (0000030554-16-000102): spin-off |
| DD (30554) | DuPont | 2017-09-01 bis 2017-09-06 | -22.6% | 8-K 2017-08-04 (0001104659-17-049576): spin-off |
| DNR (945764) | Denbury Resources | 2013-05-22 bis 2013-05-23 | -3.6% | 8-K 2013-05-28 (0000945764-13-000045): spin-off |
| DNR (945764) | Denbury Resources | 2013-06-11 bis 2013-06-12 | -4.2% | 8-K 2013-05-28 (0000945764-13-000045): spin-off |
| DNR (945764) | Denbury Resources | 2013-06-20 bis 2013-06-21 | -6.0% | 8-K 2013-05-28 (0000945764-13-000045): spin-off |
| EA (712515) | Electronic Arts | 2019-08-05 bis 2019-08-06 | -6.4% | 8-K 2019-08-09 (0000712515-19-000060): spin-off |
| EA (712515) | Electronic Arts | 2019-08-09 bis 2019-08-15 | -4.8% | 8-K 2019-08-09 (0000712515-19-000060): spin-off |
| EA (712515) | Electronic Arts | 2021-02-03 bis 2021-02-04 | -6.9% | 8-K 2021-02-08 (0001193125-21-032346): spin-off |
| EA (712515) | Electronic Arts | 2021-02-22 bis 2021-02-25 | -4.2% | 8-K 2021-02-08 (0001193125-21-032346): spin-off |
| EA (712515) | Electronic Arts | 2021-03-04 bis 2021-03-08 | -4.1% | 8-K 2021-02-08 (0001193125-21-032346): spin-off |
| EA (712515) | Electronic Arts | 2022-08-22 | -3.3% | 8-K 2022-08-15 (0000712515-22-000047): spin-off |
| EA (712515) | Electronic Arts | 2022-08-30 | -4.2% | 8-K 2022-08-15 (0000712515-22-000047): spin-off |
| EA (712515) | Electronic Arts | 2022-09-14 bis 2022-09-16 | -4.1% | 8-K 2022-08-15 (0000712515-22-000047): spin-off |
| EA (712515) | Electronic Arts | 2024-09-03 bis 2024-09-04 | -3.7% | 8-K 2024-08-05 (0000712515-24-000040): spin-off |
| HES (4447) | Hess Corporation | 2012-03-21 bis 2012-03-22 | -4.0% | 8-K 2012-03-13 (0000950127-12-000072): spin-off |
| HES (4447) | Hess Corporation | 2012-04-09 bis 2012-04-10 | -4.2% | 8-K 2012-03-13 (0000950127-12-000072): spin-off |
| HES (4447) | Hess Corporation | 2014-02-03 | -3.4% | 8-K 2014-01-29 (0001157523-14-000263): spin-off |
| HES (4447) | Hess Corporation | 2015-05-11 bis 2015-05-12 | -3.8% | 8-K 2015-05-12 (0001193125-15-184091): spin-off |
| HES (4447) | Hess Corporation | 2015-05-26 | -3.8% | 8-K 2015-05-12 (0001193125-15-184091): spin-off |
| HES (4447) | Hess Corporation | 2016-02-05 bis 2016-02-08 | -12.5% | 8-K 2016-02-10 (0001193125-16-457764): spin-off |
| HES (4447) | Hess Corporation | 2016-02-18 | -3.2% | 8-K 2016-02-10 (0001193125-16-457764): spin-off |
| HES (4447) | Hess Corporation | 2016-02-23 bis 2016-02-24 | -6.5% | 8-K 2016-02-10 (0001193125-16-457764): spin-off |
| HES (4447) | Hess Corporation | 2016-03-08 bis 2016-03-09 | -5.1% | 8-K 2016-02-10 (0001193125-16-457764): spin-off |
| HES (4447) | Hess Corporation | 2017-06-07 bis 2017-06-08 | -7.3% | 8-K 2017-06-13 (0001193125-17-202523): spin-off |
| HES (4447) | Hess Corporation | 2017-06-15 bis 2017-06-21 | -6.2% | 8-K 2017-06-13 (0001193125-17-202523): spin-off |
| HES (4447) | Hess Corporation | 2017-07-05 bis 2017-07-07 | -5.7% | 8-K 2017-06-13 (0001193125-17-202523): spin-off |
| HSP (1274057) | Hospira | 2012-01-06 | -3.3% | 8-K 2011-12-09 (0001104659-11-068653): spin-off |
| K (55067) | Kellanova | 2023-10-05 bis 2023-10-06 | -4.8% | 8-K 2023-09-12 (0001193125-23-233552): separation and distribution, spin-off; 8-K 2023-10-02 (0001193125-23-249062): distribution of all, separation and distribution, spin-off |
| K (55067) | Kellanova | 2023-10-12 | -4.1% | 8-K 2023-09-12 (0001193125-23-233552): separation and distribution, spin-off; 8-K 2023-10-02 (0001193125-23-249062): distribution of all, separation and distribution, spin-off |
| LEG (58492) | Leggett & Platt | 2018-11-12 | -3.2% | 8-K 2018-11-07 (0001193125-18-320095): distribution of all |
| LEG (58492) | Leggett & Platt | 2018-12-04 | -4.4% | 8-K 2018-11-07 (0001193125-18-320095): distribution of all |
| LM (704051) | Legg Mason | 2012-06-01 bis 2012-06-04 | -5.2% | 8-K 2012-05-22 (0000930413-12-003234): spin-off; 8-K 2012-05-23 (0000930413-12-003269): spin-off |
| LM (704051) | Legg Mason | 2012-06-11 | -3.2% | 8-K 2012-05-22 (0000930413-12-003234): spin-off; 8-K 2012-05-23 (0000930413-12-003269): spin-off |
| LM (704051) | Legg Mason | 2012-06-21 | -4.2% | 8-K 2012-05-22 (0000930413-12-003234): spin-off; 8-K 2012-05-23 (0000930413-12-003269): spin-off |
| MRO (101778) | Marathon Oil | 2012-01-26 bis 2012-01-27 | -4.1% | 8-K 2012-02-01 (0000101778-12-000007): spin-off |
| MRO (101778) | Marathon Oil | 2012-02-29 | -3.3% | 8-K 2012-02-01 (0000101778-12-000007): spin-off |
| MRO (101778) | Marathon Oil | 2012-05-02 bis 2012-05-07 | -8.4% | 8-K 2012-05-02 (0000101778-12-000016): spin-off |
| MRO (101778) | Marathon Oil | 2012-05-14 bis 2012-05-16 | -5.0% | 8-K 2012-05-02 (0000101778-12-000016): spin-off |
| MRO (101778) | Marathon Oil | 2012-06-01 bis 2012-06-04 | -4.3% | 8-K 2012-05-02 (0000101778-12-000016): spin-off |
| MRO (101778) | Marathon Oil | 2013-02-20 bis 2013-02-26 | -5.3% | 8-K 2013-02-06 (0000101778-13-000003): spin-off |
| MRO (101778) | Marathon Oil | 2013-03-04 | -3.4% | 8-K 2013-02-06 (0000101778-13-000003): spin-off |
| MWV (1159297) | MeadWestvaco | 2012-04-10 | -3.8% | 8-K 2012-03-23 (0000898822-12-000130): spin off; 8-K 2012-04-11 (0001193125-12-158154): spin-off |
| MWV (1159297) | MeadWestvaco | 2012-05-01 bis 2012-05-02 | -9.9% | 8-K 2012-04-11 (0001193125-12-158154): spin-off; 8-K 2012-04-17 (0000898822-12-000161): spin-off; 8-K 2012-04-25 (0001193125-12-181057): spin-off |
| MWV (1159297) | MeadWestvaco | 2012-05-17 | -3.1% | 8-K 2012-04-17 (0000898822-12-000161): spin-off; 8-K 2012-04-25 (0001193125-12-181057): spin-off; 8-K 2012-05-03 (0001193125-12-207131): spin-off |
| MWV (1159297) | MeadWestvaco | 2012-06-01 bis 2012-06-04 | -4.3% | 8-K 2012-05-03 (0001193125-12-207131): spin-off |
| MWV (1159297) | MeadWestvaco | 2012-07-24 | -4.0% | 8-K 2012-07-25 (0001193125-12-313584): spin-off, spinoff |
| MWV (1159297) | MeadWestvaco | 2012-08-02 | -3.9% | 8-K 2012-07-25 (0001193125-12-313584): spin-off, spinoff |
| MWV (1159297) | MeadWestvaco | 2012-11-15 | -3.9% | 8-K 2012-10-30 (0001193125-12-441231): spin-off |
| MWV (1159297) | MeadWestvaco | 2013-10-29 bis 2013-10-30 | -10.6% | 8-K 2013-10-29 (0001193125-13-416180): distribution of all; 8-K 2013-10-29 (0001193125-13-414687): spin-off |
| MWV (1159297) | MeadWestvaco | 2013-11-05 bis 2013-11-06 | -3.5% | 8-K 2013-10-29 (0001193125-13-416180): distribution of all; 8-K 2013-10-29 (0001193125-13-414687): spin-off |
| MWV (1159297) | MeadWestvaco | 2014-01-24 | -4.4% | 8-K 2014-01-29 (0001193125-14-025493): spin-off |
| MWV (1159297) | MeadWestvaco | 2015-01-06 | -3.3% | 8-K 2015-01-08 (0001193125-15-004534): spinoff |
| MWV (1159297) | MeadWestvaco | 2015-03-06 | -3.3% | 8-K 2015-02-24 (0001193125-15-060231): spinoff; 8-K/A 2015-02-27 (0001193125-15-067571): spinoff |
| PXD (1038357) | Pioneer Natural Resources | 2016-06-10 | -4.5% | 8-K 2016-05-24 (0001038357-16-000135): spin-off |
| PXD (1038357) | Pioneer Natural Resources | 2016-06-16 bis 2016-06-17 | -6.4% | 8-K 2016-05-24 (0001038357-16-000135): spin-off |
| PXD (1038357) | Pioneer Natural Resources | 2020-05-11 bis 2020-05-13 | -6.6% | 8-K 2020-05-15 (0001193125-20-144156): spin-off |
| PXD (1038357) | Pioneer Natural Resources | 2020-05-19 | -4.0% | 8-K 2020-05-15 (0001193125-20-144156): spin-off |
| PXD (1038357) | Pioneer Natural Resources | 2020-06-09 bis 2020-06-12 | -12.0% | 8-K 2020-05-15 (0001193125-20-144156): spin-off |
| PXD (1038357) | Pioneer Natural Resources | 2021-04-05 bis 2021-04-06 | -8.0% | 8-K 2021-04-02 (0001193125-21-105219): distribution of all |
| PXD (1038357) | Pioneer Natural Resources | 2021-04-09 | -4.1% | 8-K 2021-04-02 (0001193125-21-105219): distribution of all |
| PXD (1038357) | Pioneer Natural Resources | 2021-04-16 | -3.1% | 8-K 2021-04-02 (0001193125-21-105219): distribution of all |
| PXD (1038357) | Pioneer Natural Resources | 2021-04-30 | -3.6% | 8-K 2021-04-02 (0001193125-21-105219): distribution of all |
| RAI (1275283) | Reynolds American | 2013-04-15 | -3.4% | 8-K 2013-03-18 (0001193125-13-111770): spin off, spin-off |
| RAI (1275283) | Reynolds American | 2014-08-07 bis 2014-08-08 | -4.6% | 8-K 2014-08-11 (0001193125-14-304991): spin-off |
| RAI (1275283) | Reynolds American | 2014-12-15 | -3.1% | 8-K 2014-12-19 (0001193125-14-448675): spin off, spin-off |
| RAI (1275283) | Reynolds American | 2015-04-29 bis 2015-04-30 | -3.9% | 8-K 2015-04-02 (0001193125-15-117912): spin-off |
| RDC (85408) | Rowan Companies | 2012-03-20 bis 2012-03-22 | -6.1% | 8-K 2012-03-15 (0001144204-12-015056): spin-off |
| RDC (85408) | Rowan Companies | 2012-04-10 bis 2012-04-11 | -4.4% | 8-K 2012-03-15 (0001144204-12-015056): spin-off |
| RDC (85408) | Rowan Companies | 2012-05-04 bis 2012-05-08 | -6.8% | 8-K12B 2012-05-04 (0001193125-12-211636): spin-off; 8-K 2012-05-04 (0001193125-12-210466): spin-off |
| RDC (85408) | Rowan Companies | 2012-05-14 bis 2012-05-15 | -4.2% | 8-K12B 2012-05-04 (0001193125-12-211636): spin-off; 8-K 2012-05-04 (0001193125-12-210466): spin-off |
| RDC (85408) | Rowan Companies | 2012-05-30 bis 2012-06-01 | -7.9% | 8-K12B 2012-05-04 (0001193125-12-211636): spin-off; 8-K 2012-05-04 (0001193125-12-210466): spin-off |
| RDC (85408) | Rowan Companies | 2012-07-06 | -3.7% | 8-K 2012-07-05 (0001144204-12-038178): spin-off |
| RDC (85408) | Rowan Companies | 2012-07-24 | -4.2% | 8-K 2012-07-05 (0001144204-12-038178): spin-off |
| RDC (85408) | Rowan Companies | 2012-07-31 | -3.3% | 8-K 2012-07-05 (0001144204-12-038178): spin-off |
| RDC (85408) | Rowan Companies | 2013-03-19 | -3.9% | 8-K 2013-03-08 (0001144204-13-014055): spin-off |
| RDC (85408) | Rowan Companies | 2013-04-02 bis 2013-04-03 | -5.1% | 8-K 2013-03-08 (0001144204-13-014055): spin-off |
| RHT (1087423) | Red Hat | 2014-10-10 bis 2014-10-13 | -6.6% | 8-K 2014-10-07 (0001193125-14-365618): spin-off |
| RHT (1087423) | Red Hat | 2014-10-22 | -4.1% | 8-K 2014-10-07 (0001193125-14-365618): spin-off |
| RTN (1047122) | Raytheon Company | 2014-07-24 bis 2014-07-25 | -3.5% | 8-K 2014-07-28 (0001047122-14-000189): spin-off |
| RTN (1047122) | Raytheon Company | 2019-06-11 bis 2019-06-12 | -5.4% | 8-K 2019-06-10 (0000947871-19-000428): separation and distribution, spin-off |
| RTN (1047122) | Raytheon Company | 2019-07-01 | -3.9% | 8-K 2019-06-10 (0000947871-19-000428): separation and distribution, spin-off |
| RTN (1047122) | Raytheon Company | 2019-07-31 bis 2019-08-01 | -3.9% | 8-K 2019-07-25 (0001047122-19-000171): spin-off |
| RTN (1047122) | Raytheon Company | 2019-08-23 | -3.4% | 8-K 2019-07-25 (0001047122-19-000171): spin-off |
| RTN (1047122) | Raytheon Company | 2020-03-05 bis 2020-03-23 | -16.8% | 8-K 2020-03-13 (0001193125-20-072473): spin-off |
| RTN (1047122) | Raytheon Company | 2020-03-27 bis 2020-04-03 | -13.3% | 8-K 2020-03-13 (0001193125-20-072473): spin-off; 8-K 2020-04-03 (0001193125-20-097237): spin-off |
| SEE (1012100) | Sealed Air | 2017-02-09 bis 2017-02-10 | -6.1% | 8-K 2017-02-09 (0001564590-17-001238): spin-off |
| SEE (1012100) | Sealed Air | 2017-03-06 bis 2017-03-07 | -4.1% | 8-K 2017-02-09 (0001564590-17-001238): spin-off; 8-K 2017-02-23 (0001193125-17-053265): spin-off; 8-K 2017-03-10 (0001193125-17-078173): spin-off |
| SEE (1012100) | Sealed Air | 2017-03-27 | -4.2% | 8-K 2017-03-10 (0001193125-17-078173): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-01-03 bis 2012-01-06 | -5.2% | 8-K 2011-12-15 (0001181431-11-060635): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-02-21 bis 2012-02-22 | -7.1% | 8-K 2012-02-23 (0001193125-12-073963): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-03-06 | -3.3% | 8-K 2012-02-23 (0001193125-12-073963): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-03-12 | -3.4% | 8-K 2012-02-23 (0001193125-12-073963): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-03-19 bis 2012-03-23 | -7.9% | 8-K 2012-02-23 (0001193125-12-073963): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-05-14 bis 2012-05-16 | -4.1% | 8-K 2012-05-17 (0001193125-12-237287): spin-off; 8-K 2012-05-17 (0001193125-12-237278): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-05-30 bis 2012-06-04 | -14.1% | 8-K 2012-05-17 (0001193125-12-237287): spin-off; 8-K 2012-05-17 (0001193125-12-237278): spin-off; 8-K 2012-06-01 (0001193125-12-255862): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-06-11 bis 2012-06-13 | -5.4% | 8-K 2012-05-17 (0001193125-12-237287): spin-off; 8-K 2012-05-17 (0001193125-12-237278): spin-off; 8-K 2012-06-01 (0001193125-12-255862): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-06-21 | -3.1% | 8-K 2012-06-01 (0001193125-12-255862): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-08-20 bis 2012-08-23 | -5.2% | 8-K 2012-08-16 (0001193125-12-358158): spin-off |
| SHLD (1310067) | Sears Holdings | 2012-08-30 bis 2012-08-31 | -8.2% | 8-K 2012-08-16 (0001193125-12-358158): spin-off |
| SNI (1430602) | Scripps Networks Interactive | 2016-02-08 bis 2016-02-11 | -10.6% | 8-K 2016-02-08 (0001564590-16-012462): spin off, spin-off |
| SRCL (861878) | Stericycle | 2017-11-01 bis 2017-11-02 | -4.1% | 8-K 2017-10-18 (0001564590-17-019576): spin-off |
| SRCL (861878) | Stericycle | 2017-11-09 bis 2017-11-10 | -4.6% | 8-K 2017-10-18 (0001564590-17-019576): spin-off |
| STJ (203077) | St Jude Medical | 2015-07-24 bis 2015-07-27 | -3.6% | 8-K 2015-07-22 (0001104659-15-052337): spin-off |
| STJ (203077) | St Jude Medical | 2015-08-20 bis 2015-08-24 | -5.7% | 8-K 2015-07-22 (0001104659-15-052337): spin-off; 8-K 2015-08-05 (0001104659-15-056302): spin-off |
| STJ (203077) | St Jude Medical | 2015-09-01 | -5.4% | 8-K 2015-08-05 (0001104659-15-056302): spin-off |
| SVU (95521) | Supervalu | 2012-04-18 bis 2012-04-19 | -4.6% | 8-K 2012-04-20 (0001193125-12-173396): spin-off |
| SVU (95521) | Supervalu | 2012-04-30 bis 2012-05-03 | -6.0% | 8-K 2012-04-20 (0001193125-12-173396): spin-off |
| SVU (95521) | Supervalu | 2012-05-09 | -4.0% | 8-K 2012-04-20 (0001193125-12-173396): spin-off |
| SVU (95521) | Supervalu | 2012-05-15 bis 2012-05-23 | -9.2% | 8-K 2012-04-20 (0001193125-12-173396): spin-off |
| SWN (7332) | Southwestern Energy | 2015-01-28 bis 2015-01-29 | -5.0% | 8-K 2015-01-21 (0001193125-15-016320): spin-off |
| SWY (86144) | Safeway | 2014-04-15 bis 2014-04-16 | -10.3% | 8-K 2014-03-24 (0001193125-14-112558): spin-off; 8-K 2014-04-08 (0001193125-14-135663): distribution of all, spin-off; 8-K 2014-04-14 (0001193125-14-141375): spin-off |
| TFCF (1308161) | 21st Century Fox | 2013-06-12 | -3.0% | 8-K 2013-05-24 (0001193125-13-235936): distribution of all; 8-K 2013-06-17 (0001193125-13-259983): distribution of all |
| TFCF (1308161) | 21st Century Fox | 2013-06-19 bis 2013-06-20 | -12.7% | 8-K 2013-05-24 (0001193125-13-235936): distribution of all; 8-K 2013-06-17 (0001193125-13-259983): distribution of all |
| TFCF (1308161) | 21st Century Fox | 2013-07-30 | -3.1% | 8-K 2013-07-03 (0001193125-13-281456): distribution of all, separation and distribution |
| TFCF (1308161) | 21st Century Fox | 2013-11-07 | -3.5% | 8-K 2013-10-18 (0001193125-13-404025): spin-off |
| TFCF (1308161) | 21st Century Fox | 2017-12-13 | -3.7% | 8-K 2017-12-14 (0001193125-17-368807): separation and distribution, spin off, spin-off, spinoff; 8-K 2017-12-15 (0001193125-17-370718): separation and distribution, spin-off |
| TFCF (1308161) | 21st Century Fox | 2018-02-27 bis 2018-03-01 | -5.2% | 8-K 2018-02-22 (0001193125-18-054182): separation and distribution |
| TFCF (1308161) | 21st Century Fox | 2018-07-11 bis 2018-07-12 | -4.7% | 8-K 2018-06-14 (0001193125-18-192424): separation and distribution; 8-K 2018-06-20 (0001193125-18-197423): separation and distribution; 8-K 2018-06-21 (0001193125-18-199619): separation and distribution, spin-off |
| TFCF (1308161) | 21st Century Fox | 2019-03-19 | -4.1% | 8-K 2019-03-19 (0001193125-19-079716): spin-off; 8-K 2019-03-19 (0001193125-19-079034): distribution of all, separation and distribution; 8-K 2019-03-20 (0000950157-19-000309): distribution of all |
| TFCFA (1308161) | 21st Century Fox | 2013-06-12 | -3.2% | 8-K 2013-05-24 (0001193125-13-235936): distribution of all; 8-K 2013-06-17 (0001193125-13-259983): distribution of all |
| TFCFA (1308161) | 21st Century Fox | 2013-06-19 bis 2013-06-20 | -12.9% | 8-K 2013-05-24 (0001193125-13-235936): distribution of all; 8-K 2013-06-17 (0001193125-13-259983): distribution of all |
| TFCFA (1308161) | 21st Century Fox | 2013-07-30 | -3.3% | 8-K 2013-07-03 (0001193125-13-281456): distribution of all, separation and distribution |
| TFCFA (1308161) | 21st Century Fox | 2013-11-07 | -3.8% | 8-K 2013-10-18 (0001193125-13-404025): spin-off |
| TFCFA (1308161) | 21st Century Fox | 2017-12-13 | -4.0% | 8-K 2017-12-14 (0001193125-17-368807): separation and distribution, spin off, spin-off, spinoff; 8-K 2017-12-15 (0001193125-17-370718): separation and distribution, spin-off |
| TFCFA (1308161) | 21st Century Fox | 2018-02-27 bis 2018-03-01 | -5.1% | 8-K 2018-02-22 (0001193125-18-054182): separation and distribution |
| TFCFA (1308161) | 21st Century Fox | 2018-07-11 bis 2018-07-12 | -4.8% | 8-K 2018-06-14 (0001193125-18-192424): separation and distribution; 8-K 2018-06-20 (0001193125-18-197423): separation and distribution; 8-K 2018-06-21 (0001193125-18-199619): separation and distribution, spin-off |
| TFCFA (1308161) | 21st Century Fox | 2019-03-19 bis 2019-03-20 | -4.5% | 8-K 2019-03-19 (0001193125-19-079716): spin-off; 8-K 2019-03-19 (0001193125-19-079034): distribution of all, separation and distribution; 8-K 2019-03-20 (0000950157-19-000309): distribution of all |
| TGNA (39899) | Tegna | 2015-07-02 bis 2015-07-08 | -7.2% | 8-K/A 2015-06-09 (0001104659-15-044100): separation and distribution; 8-K 2015-06-09 (0001104659-15-044099): separation and distribution, spin-off, spinoff; 8-K 2015-06-17 (0001193125-15-226039): spin-off |
| TGNA (39899) | Tegna | 2015-07-21 bis 2015-07-22 | -7.4% | 8-K 2015-07-02 (0001047469-15-005951): separation and distribution, spinoff; 8-K 2015-07-06 (0001193125-15-245318): spin-off, spinoff; 8-K 2015-07-21 (0000039899-15-000016): spin-off |
| TGNA (39899) | Tegna | 2015-08-04 bis 2015-08-12 | -5.6% | 8-K 2015-07-06 (0001193125-15-245318): spin-off, spinoff; 8-K 2015-07-21 (0000039899-15-000016): spin-off |
| TGNA (39899) | Tegna | 2015-08-19 bis 2015-08-25 | -6.3% | 8-K 2015-07-21 (0000039899-15-000016): spin-off |
| TGNA (39899) | Tegna | 2015-11-13 | -4.8% | 8-K 2015-10-20 (0000039899-15-000022): spin-off |
| TGNA (39899) | Tegna | 2015-12-08 bis 2015-12-14 | -5.0% | 8-K 2015-12-11 (0001193125-15-401613): spin-off, spinoff |
| TGNA (39899) | Tegna | 2015-12-18 | -4.6% | 8-K 2015-12-11 (0001193125-15-401613): spin-off, spinoff |
| TGNA (39899) | Tegna | 2016-01-04 bis 2016-01-08 | -4.3% | 8-K 2015-12-11 (0001193125-15-401613): spin-off, spinoff |
| TGNA (39899) | Tegna | 2016-07-26 bis 2016-08-02 | -9.4% | 8-K 2016-07-26 (0000039899-16-000046): spin-off |
| TGNA (39899) | Tegna | 2016-09-09 | -3.2% | 8-K 2016-09-07 (0001193125-16-702747): separation and distribution, spin off, spin-off |
| TGNA (39899) | Tegna | 2016-09-20 | -4.1% | 8-K 2016-09-07 (0001193125-16-702747): separation and distribution, spin off, spin-off |
| TGNA (39899) | Tegna | 2016-10-07 bis 2016-10-10 | -4.4% | 8-K 2016-09-07 (0001193125-16-702747): separation and distribution, spin off, spin-off |
| TGNA (39899) | Tegna | 2016-11-02 bis 2016-11-03 | -8.2% | 8-K 2016-11-02 (0000039899-16-000056): spin-off |
| TGNA (39899) | Tegna | 2017-03-21 | -3.0% | 8-K 2017-02-27 (0000039899-17-000007): spin-off |
| TGNA (39899) | Tegna | 2017-05-09 bis 2017-05-11 | -9.6% | 8-K 2017-05-09 (0001193125-17-164289): distribution of all, separation and distribution, spin-off, spinoff; 8-K 2017-05-09 (0000039899-17-000017): spin-off; 8-K 2017-05-16 (0001193125-17-171557): distribution of all, separation and distribution, spin-off |
| TGNA (39899) | Tegna | 2017-05-16 bis 2017-05-17 | -6.8% | 8-K 2017-05-09 (0001193125-17-164289): distribution of all, separation and distribution, spin-off, spinoff; 8-K 2017-05-09 (0000039899-17-000017): spin-off; 8-K 2017-05-16 (0001193125-17-171557): distribution of all, separation and distribution, spin-off |
| TGNA (39899) | Tegna | 2017-06-02 bis 2017-06-05 | -5.2% | 8-K 2017-05-09 (0001193125-17-164289): distribution of all, separation and distribution, spin-off, spinoff; 8-K 2017-05-09 (0000039899-17-000017): spin-off; 8-K 2017-05-16 (0001193125-17-171557): distribution of all, separation and distribution, spin-off |
| TGNA (39899) | Tegna | 2017-06-20 bis 2017-06-21 | -5.6% | 8-K 2017-06-06 (0001193125-17-196074): distribution of all, separation and distribution, spin-off |
| TIF (98246) | Tiffany & Co | 2017-06-13 | -3.0% | 8-K 2017-06-01 (0000098246-17-000153): spin-off |
| TIF (98246) | Tiffany & Co | 2019-10-18 | -3.4% | 8-K 2019-10-22 (0000098246-19-000129): distribution of all |
| TIF (98246) | Tiffany & Co | 2019-10-30 | -4.5% | 8-K 2019-10-22 (0000098246-19-000129): distribution of all |
| TWC (1377013) | Time Warner Cable | 2013-08-15 | -3.2% | 8-K 2013-07-29 (0001193125-13-306215): spin-off, spinoff |
| TWC (1377013) | Time Warner Cable | 2014-02-19 | -3.4% | 8-K 2014-02-13 (0001193125-14-051452): spin off |
| TWC (1377013) | Time Warner Cable | 2014-07-31 bis 2014-08-01 | -4.2% | 8-K 2014-07-31 (0001193125-14-288219): spin-off |
| TWC (1377013) | Time Warner Cable | 2014-10-30 | -6.6% | 8-K 2014-10-30 (0001193125-14-388261): spin-off |
| TWC (1377013) | Time Warner Cable | 2014-11-10 bis 2014-11-11 | -6.7% | 8-K 2014-10-30 (0001193125-14-388261): spin-off |
| TWC (1377013) | Time Warner Cable | 2015-01-28 bis 2015-01-29 | -4.6% | 8-K 2015-01-29 (0001193125-15-024469): spin-off |
| TWC (1377013) | Time Warner Cable | 2015-08-21 bis 2015-08-24 | -4.5% | 8-K 2015-07-30 (0001193125-15-269262): spin-off |
| TWC (1377013) | Time Warner Cable | 2015-09-28 bis 2015-09-29 | -4.9% | 8-K 2015-09-09 (0000950142-15-002066): spin-off |
| TWX (1105705) | Time Warner | 2013-06-11 | -3.2% | 8-K 2013-05-29 (0001105705-13-000022): spin-off |
| TWX (1105705) | Time Warner | 2013-06-20 | -4.4% | 8-K 2013-05-29 (0001105705-13-000022): spin-off |
| TWX (1105705) | Time Warner | 2014-06-06 | -3.9% | 8-K 2014-05-09 (0001105705-14-000025): distribution of all, spin-off; 8-K 2014-06-09 (0001105705-14-000031): separation and distribution, spin-off |
| TWX (1105705) | Time Warner | 2014-08-06 bis 2014-08-07 | -15.4% | 8-K 2014-08-06 (0001193125-14-296984): spin-off |
| TWX (1105705) | Time Warner | 2014-11-04 | -5.7% | 8-K 2014-10-08 (0001105705-14-000036): spin-off; 8-K 2014-11-05 (0001193125-14-397406): spin-off |
| TWX (1105705) | Time Warner | 2016-10-24 | -3.1% | 8-K 2016-10-24 (0000950157-16-002366): spin-off |
| VAR (203527) | Varian Medical Systems | 2016-09-09 | -3.7% | 8-K 2016-09-07 (0001144204-16-123103): spin off |
| VAR (203527) | Varian Medical Systems | 2016-10-21 | -3.0% | 8-K 2016-10-04 (0001144204-16-126769): spin-off; 8-K 2016-10-14 (0001144204-16-128068): spin off; 8-K 2016-10-26 (0001144204-16-129597): spin-off |
| VAR (203527) | Varian Medical Systems | 2016-10-26 bis 2016-10-28 | -5.8% | 8-K 2016-10-04 (0001144204-16-126769): spin-off; 8-K 2016-10-14 (0001144204-16-128068): spin off; 8-K 2016-10-26 (0001144204-16-129597): spin-off |
| VAR (203527) | Varian Medical Systems | 2016-11-09 bis 2016-11-10 | -3.5% | 8-K 2016-10-14 (0001144204-16-128068): spin off; 8-K 2016-10-26 (0001144204-16-129597): spin-off; 8-K 2016-10-27 (0001144204-16-129730): spin-off |
| VAR (203527) | Varian Medical Systems | 2017-01-26 bis 2017-01-27 | -6.4% | 8-K 2017-01-10 (0001193125-17-006350): separation and distribution; 8-K 2017-01-20 (0001193125-17-014255): distribution of all, separation and distribution, spin-off; 8-K 2017-01-30 (0001193125-17-022651): separation and distribution |
| VAR (203527) | Varian Medical Systems | 2017-09-28 | -3.6% | 8-K 2017-09-05 (0001144204-17-046615): spin-off |
| VAR (203527) | Varian Medical Systems | 2017-10-26 | -3.5% | 8-K 2017-10-25 (0001144204-17-054114): spin off, spinoff |
| VAR (203527) | Varian Medical Systems | 2018-01-16 | -3.1% | 8-K 2018-01-11 (0001144204-18-001925): spinoff |
| VAR (203527) | Varian Medical Systems | 2018-02-05 bis 2018-02-08 | -6.0% | 8-K 2018-01-11 (0001144204-18-001925): spinoff; 8-K 2018-01-24 (0001144204-18-003505): spinoff |
| VAR (203527) | Varian Medical Systems | 2018-04-26 bis 2018-04-27 | -7.5% | 8-K 2018-04-04 (0001144204-18-019215): spin-off; 8-K 2018-04-25 (0001144204-18-022412): spinoff |
| VIAB (1339947) | Viacom | 2016-06-24 bis 2016-06-27 | -10.6% | 8-K 2016-06-29 (0001339947-16-000088): spin-off |
| VIAB (1339947) | Viacom | 2016-08-22 bis 2016-08-23 | -4.1% | 8-K 2016-08-23 (0001193125-16-687817): spin-off |
| VIAB (1339947) | Viacom | 2016-09-09 bis 2016-09-13 | -8.3% | 8-K 2016-08-23 (0001193125-16-687817): spin-off |
| WBA (1618921) | Walgreens Boots Alliance | 2012-06-19 bis 2012-06-21 | -8.6% | 8-K 2012-06-19 (0001193125-12-275340): spin-off |
| WBA (1618921) | Walgreens Boots Alliance | 2018-01-30 bis 2018-02-05 | -7.4% | 8-K 2018-01-19 (0001193125-18-013986): spin-off |
| WBA (1618921) | Walgreens Boots Alliance | 2018-02-08 bis 2018-02-09 | -5.0% | 8-K 2018-01-19 (0001193125-18-013986): spin-off |
| WBA (1618921) | Walgreens Boots Alliance | 2021-02-01 bis 2021-02-02 | -3.7% | 8-K 2021-01-08 (0001193125-21-004703): distribution of all, spin-off; 8-K 2021-02-02 (0001359948-21-000018): spin-off |
| WBA (1618921) | Walgreens Boots Alliance | 2021-06-18 | -4.6% | 8-K 2021-06-04 (0001193125-21-183107): distribution of all, spin-off |
| WBA (1618921) | Walgreens Boots Alliance | 2021-07-01 bis 2021-07-02 | -8.4% | 8-K 2021-06-04 (0001193125-21-183107): distribution of all, spin-off |
| X (1163302) | United States Steel | 2013-04-01 bis 2013-04-03 | -9.5% | 8-K 2013-03-27 (0001193125-13-129608): spin-off |
| X (1163302) | United States Steel | 2013-04-15 bis 2013-04-16 | -5.2% | 8-K 2013-03-27 (0001193125-13-129608): spin-off |
| XL (875159) | XL Group | 2013-10-31 | -3.1% | 8-K 2013-11-04 (0000875159-13-000021): spin-off |
| XL (875159) | XL Group | 2013-12-03 | -3.5% | 8-K 2013-11-04 (0000875159-13-000021): spin-off |
| XRX (108772) | Xerox | 2016-04-25 bis 2016-04-26 | -13.3% | 8-K 2016-04-25 (0000108772-16-000044): spin-off, spinoff |
| XRX (108772) | Xerox | 2016-04-29 | -4.0% | 8-K 2016-04-25 (0000108772-16-000044): spin-off, spinoff |
| XRX (108772) | Xerox | 2016-08-02 | -4.8% | 8-K 2016-07-29 (0000108772-16-000061): spin-off |
| XRX (108772) | Xerox | 2016-11-01 | -3.5% | 8-K 2016-10-28 (0000108772-16-000069): spin-off; 8-K 2016-10-28 (0001193125-16-750058): separation and distribution, spin-off |
| XRX (108772) | Xerox | 2016-11-04 | -3.6% | 8-K 2016-10-28 (0000108772-16-000069): spin-off; 8-K 2016-10-28 (0001193125-16-750058): separation and distribution, spin-off; 8-K 2016-11-07 (0001193125-16-760779): spin-off |
| XRX (108772) | Xerox | 2016-12-14 | -3.2% | 8-K 2016-12-02 (0001193125-16-783200): spin-off |
| XRX (108772) | Xerox | 2017-03-21 bis 2017-03-22 | -3.4% | 8-K 2017-03-02 (0001193125-17-067802): spin-off; 8-K 2017-03-14 (0001193125-17-082106): spin-off; 8-K 2017-03-17 (0001193125-17-087478): spin-off |
| XRX (108772) | Xerox | 2017-05-17 | -3.8% | 8-K 2017-04-25 (0000108772-17-000012): distribution of all, separation and distribution, spin-off |
| XRX (108772) | Xerox | 2017-06-21 | -3.2% | 8-K 2017-05-24 (0001193125-17-181711): spin-off; 8-K 2017-06-14 (0001193125-17-203567): spin-off |
| XRX (108772) | Xerox | 2017-10-26 bis 2017-10-27 | -8.4% | 8-K 2017-10-26 (0000108772-17-000041): distribution of all, separation and distribution, spin-off |
| XRX (108772) | Xerox | 2017-11-03 | -4.1% | 8-K 2017-10-26 (0000108772-17-000041): distribution of all, separation and distribution, spin-off |
| XRX (108772) | Xerox | 2017-11-13 bis 2017-11-14 | -3.8% | 8-K 2017-10-26 (0000108772-17-000041): distribution of all, separation and distribution, spin-off |
| XRX (108772) | Xerox | 2018-02-01 bis 2018-02-05 | -7.3% | 8-K 2018-01-31 (0001193125-18-026289): spin-off; 8-K 2018-01-31 (0000108772-18-000003): distribution of all, separation and distribution, spin-off; 8-K 2018-02-05 (0001193125-18-030969): distribution of all, spin-off |
| XRX (108772) | Xerox | 2018-02-08 bis 2018-02-09 | -5.0% | 8-K 2018-01-31 (0001193125-18-026289): spin-off; 8-K 2018-01-31 (0000108772-18-000003): distribution of all, separation and distribution, spin-off; 8-K 2018-02-05 (0001193125-18-030969): distribution of all, spin-off |
| XRX (108772) | Xerox | 2018-05-02 bis 2018-05-04 | -12.3% | 8-K 2018-05-02 (0001193125-18-147461): spin-off; 8-K 2018-05-03 (0000108772-18-000021): distribution of all; 8-K 2018-05-04 (0001193125-18-152998): spin-off |
| XRX (108772) | Xerox | 2018-05-14 bis 2018-05-15 | -5.5% | 8-K 2018-05-02 (0001193125-18-147461): spin-off; 8-K 2018-05-03 (0000108772-18-000021): distribution of all; 8-K 2018-05-04 (0001193125-18-152998): spin-off |
| XRX (108772) | Xerox | 2019-03-22 bis 2019-03-25 | -5.6% | 8-K 2019-03-18 (0001193125-19-077418): spin-off |
| AGN (850693) | Allergan | 2014-05-08 | -3.0% | 8-K 2014-05-12 (0001193125-14-194323): spin-off |
| AGN (850693) | Allergan | 2014-06-05 | -3.4% | 8-K 2014-05-12 (0001193125-14-194323): spin-off |
| YHOO (1011006) | Yahoo! | 2015-01-28 bis 2015-01-30 | -8.9% | 8-K 2015-01-27 (0001157523-15-000219): spin-off; 8-K 2015-01-27 (0001157523-15-000218): spin off, spin-off |
| YHOO (1011006) | Yahoo! | 2015-04-30 | -4.0% | 8-K 2015-04-21 (0001157523-15-001219): spin-off |
| YHOO (1011006) | Yahoo! | 2015-05-19 bis 2015-05-20 | -8.4% | 8-K 2015-04-21 (0001157523-15-001219): spin-off |
| YHOO (1011006) | Yahoo! | 2015-07-27 | -3.5% | 8-K 2015-07-17 (0001193125-15-256092): spin off, spin-off; 8-K 2015-07-21 (0001157523-15-002415): spin-off |
| YHOO (1011006) | Yahoo! | 2015-08-11 bis 2015-08-12 | -7.2% | 8-K 2015-07-17 (0001193125-15-256092): spin off, spin-off; 8-K 2015-07-21 (0001157523-15-002415): spin-off |
| YHOO (1011006) | Yahoo! | 2015-08-20 bis 2015-08-25 | -8.2% | 8-K 2015-07-21 (0001157523-15-002415): spin-off |
| YHOO (1011006) | Yahoo! | 2015-09-08 | -5.0% | 8-K 2015-09-08 (0001193125-15-314494): spin-off |
| YHOO (1011006) | Yahoo! | 2015-09-14 | -3.5% | 8-K 2015-09-08 (0001193125-15-314494): spin-off |
| YHOO (1011006) | Yahoo! | 2015-09-23 bis 2015-09-28 | -5.9% | 8-K 2015-09-08 (0001193125-15-314494): spin-off; 8-K 2015-09-28 (0001193125-15-330962): spin off, spin-off |
| YHOO (1011006) | Yahoo! | 2015-10-21 bis 2015-10-22 | -7.1% | 8-K 2015-09-28 (0001193125-15-330962): spin off, spin-off; 8-K 2015-10-20 (0001157523-15-003347): spin-off, spinoff |
| YHOO (1011006) | Yahoo! | 2015-11-09 | -4.1% | 8-K 2015-10-20 (0001157523-15-003347): spin-off, spinoff |
| YHOO (1011006) | Yahoo! | 2015-11-13 | -3.6% | 8-K 2015-10-20 (0001157523-15-003347): spin-off, spinoff |
| YHOO (1011006) | Yahoo! | 2015-12-11 bis 2015-12-14 | -5.9% | 8-K 2015-12-09 (0001193125-15-398244): spin off |
| YHOO (1011006) | Yahoo! | 2016-01-04 bis 2016-01-08 | -6.3% | 8-K 2015-12-09 (0001193125-15-398244): spin off |
| YHOO (1011006) | Yahoo! | 2016-05-25 | -5.2% | 8-K 2016-04-27 (0001193125-16-558861): spin-off |
| ESRX (1532063) | Express Scripts | 2012-03-06 | -3.0% | 8-K 2012-02-29 (0001193125-12-089131): spin-off |
| ESRX (1532063) | Express Scripts | 2012-05-04 bis 2012-05-07 | -4.3% | 8-K 2012-05-10 (0001193125-12-225539): spin-off |
| ESRX (1532063) | Express Scripts | 2012-05-16 bis 2012-05-18 | -4.1% | 8-K 2012-05-10 (0001193125-12-225539): spin-off |
| ESRX (1532063) | Express Scripts | 2012-06-01 | -3.5% | 8-K 2012-05-10 (0001193125-12-225539): spin-off |
| ESRX (1532063) | Express Scripts | 2014-06-18 | -3.5% | 8-K 2014-06-02 (0001193125-14-221065): spin-off |
| ESRX (1532063) | Express Scripts | 2016-04-29 | -3.1% | 8-K 2016-05-04 (0001193125-16-577530): spin-off |
| JNPR (1043604) | Juniper Networks | 2012-05-23 bis 2012-05-24 | -5.5% | 8-K 2012-05-24 (0001299933-12-001313): spin-off |
| JNPR (1043604) | Juniper Networks | 2012-06-07 bis 2012-06-08 | -5.2% | 8-K 2012-05-24 (0001299933-12-001313): spin-off |
| JNPR (1043604) | Juniper Networks | 2012-06-21 bis 2012-06-26 | -5.1% | 8-K 2012-05-24 (0001299933-12-001313): spin-off |
| JNPR (1043604) | Juniper Networks | 2017-06-07 | -3.2% | 8-K 2017-05-30 (0001193125-17-187392): spin-off |
| LO (1424847) | Lorillard Tobacco Company | 2013-07-23 bis 2013-07-24 | -5.2% | 8-K 2013-06-27 (0001193125-13-273899): spin-off |
| LO (1424847) | Lorillard Tobacco Company | 2014-02-12 bis 2014-02-13 | -5.0% | 8-K 2014-02-18 (0001193125-14-057392): spin-off |
| LO (1424847) | Lorillard Tobacco Company | 2014-03-05 bis 2014-03-06 | -5.2% | 8-K 2014-02-18 (0001193125-14-057392): spin-off |
| LO (1424847) | Lorillard Tobacco Company | 2014-03-12 | -3.6% | 8-K 2014-02-18 (0001193125-14-057392): spin-off |
| LO (1424847) | Lorillard Tobacco Company | 2014-05-22 bis 2014-05-23 | -5.0% | 8-K 2014-05-16 (0001193125-14-202966): spin-off |
| LO (1424847) | Lorillard Tobacco Company | 2014-06-03 | -4.4% | 8-K 2014-05-16 (0001193125-14-202966): spin-off |
| CTRA (858470) | Coterra Energy | 2023-05-02 bis 2023-05-03 | -5.3% | 8-K 2023-05-05 (0000858470-23-000024): spin-off |
| CTRA (858470) | Coterra Energy | 2023-05-16 bis 2023-05-17 | -3.6% | 8-K 2023-05-05 (0000858470-23-000024): spin-off |
| CTRA (858470) | Coterra Energy | 2023-05-26 bis 2023-05-31 | -5.2% | 8-K 2023-05-05 (0000858470-23-000024): spin-off |
| CTRA (858470) | Coterra Energy | 2024-11-26 | -3.1% | 8-K 2024-11-15 (0001104659-24-119463): distribution of all |
| CTRA (858470) | Coterra Energy | 2024-12-09 | -3.1% | 8-K 2024-11-15 (0001104659-24-119463): distribution of all |
| ARG (804212) | Airgas | 2012-09-13 | -3.6% | 8-K 2012-08-15 (0000804212-12-000030): spin-off |
| QEP (1108827) | QEP Resources | 2012-03-02 bis 2012-03-05 | -4.8% | 8-K 2012-02-23 (0001140361-12-010281): spin-off |
| QEP (1108827) | QEP Resources | 2012-03-12 bis 2012-03-13 | -5.2% | 8-K 2012-02-23 (0001140361-12-010281): spin-off |
| QEP (1108827) | QEP Resources | 2012-03-21 bis 2012-03-23 | -5.7% | 8-K 2012-02-23 (0001140361-12-010281): spin-off |
| QEP (1108827) | QEP Resources | 2012-05-14 bis 2012-05-16 | -7.2% | 8-K 2012-05-16 (0001140361-12-025850): spin-off |
| QEP (1108827) | QEP Resources | 2012-05-30 bis 2012-06-04 | -4.7% | 8-K 2012-05-16 (0001140361-12-025850): spin-off |
| QEP (1108827) | QEP Resources | 2013-02-21 | -3.9% | 8-K 2013-01-31 (0001108827-13-000001): distribution of all |
| QEP (1108827) | QEP Resources | 2013-03-01 bis 2013-03-04 | -3.4% | 8-K 2013-01-31 (0001108827-13-000001): distribution of all |
| QEP (1108827) | QEP Resources | 2013-09-20 | -3.6% | 8-K 2013-08-29 (0001108827-13-000028): spin-off |
| QEP (1108827) | QEP Resources | 2014-01-27 | -3.4% | 8-K 2014-01-23 (0001108827-14-000005): spinoff |
| QEP (1108827) | QEP Resources | 2014-02-03 | -3.7% | 8-K 2014-01-23 (0001108827-14-000005): spinoff |
| QEP (1108827) | QEP Resources | 2014-02-26 bis 2014-02-27 | -11.2% | 8-K 2014-02-25 (0001108827-14-000014): spin-off |
| QEP (1108827) | QEP Resources | 2014-09-03 bis 2014-09-09 | -4.4% | 8-K 2014-08-07 (0001108827-14-000045): spin-off, spinoff |
| QEP (1108827) | QEP Resources | 2014-10-07 bis 2014-10-15 | -13.5% | 8-K 2014-10-20 (0001108827-14-000050): distribution of all |
| QEP (1108827) | QEP Resources | 2014-10-22 | -3.8% | 8-K 2014-10-20 (0001108827-14-000050): distribution of all |
| QEP (1108827) | QEP Resources | 2014-10-27 | -5.7% | 8-K 2014-10-20 (0001108827-14-000050): distribution of all |
| QEP (1108827) | QEP Resources | 2014-11-03 bis 2014-11-04 | -7.1% | 8-K 2014-10-20 (0001108827-14-000050): distribution of all |
| QEP (1108827) | QEP Resources | 2014-11-10 bis 2014-11-18 | -5.7% | 8-K 2014-10-20 (0001108827-14-000050): distribution of all |
| COV (1385187) | Covidien | 2012-11-08 | -4.3% | 8-K 2012-11-09 (0001193125-12-461709): spinoff |
| COV (1385187) | Covidien | 2013-04-15 | -3.5% | 8-K 2013-03-26 (0001385187-13-000010): spin-off |
| COV (1385187) | Covidien | 2013-04-26 bis 2013-04-29 | -6.6% | 8-K 2013-04-26 (0001385187-13-000014): spin-off; 8-K 2013-05-03 (0001385187-13-000021): spin off, spin-off |
| COV (1385187) | Covidien | 2013-06-19 bis 2013-06-20 | -7.0% | 8-K 2013-05-24 (0001385187-13-000031): separation and distribution, spin-off |
| COV (1385187) | Covidien | 2013-07-01 bis 2013-07-02 | -9.1% | 8-K 2013-07-01 (0001193125-13-279776): separation and distribution, spin-off |
| COV (1385187) | Covidien | 2013-08-16 | -4.8% | 8-K 2013-08-01 (0001385187-13-000041): spin-off |
| COV (1385187) | Covidien | 2014-07-17 | -3.8% | 8-K 2014-07-11 (0001385187-14-000025): distribution of all, spin off |
| COV (1385187) | Covidien | 2014-08-06 bis 2014-08-07 | -4.6% | 8-K 2014-07-11 (0001385187-14-000025): distribution of all, spin off |
| COV (1385187) | Covidien | 2014-09-23 | -3.0% | 8-K 2014-09-23 (0001193125-14-350066): spin-off |
| COV (1385187) | Covidien | 2014-09-30 | -3.9% | 8-K 2014-09-23 (0001193125-14-350066): spin-off |
| COV (1385187) | Covidien | 2014-10-15 bis 2014-10-17 | -7.4% | 8-K 2014-09-23 (0001193125-14-350066): spin-off |
| WPX (1518832) | WPX Energy | 2012-01-05 bis 2012-01-09 | -4.9% | 8-K 2012-01-06 (0001193125-12-004256): separation and distribution, spin-off |
| WPX (1518832) | WPX Energy | 2012-01-12 bis 2012-01-13 | -7.8% | 8-K 2012-01-06 (0001193125-12-004256): separation and distribution, spin-off |
| WPX (1518832) | WPX Energy | 2012-01-19 bis 2012-01-20 | -4.3% | 8-K 2012-01-06 (0001193125-12-004256): separation and distribution, spin-off |
| WPX (1518832) | WPX Energy | 2012-01-26 | -3.0% | 8-K 2012-01-06 (0001193125-12-004256): separation and distribution, spin-off |
| WPX (1518832) | WPX Energy | 2012-05-15 bis 2012-05-18 | -7.1% | 8-K 2012-05-15 (0001193125-12-235045): separation and distribution, spin-off, spinoff |
| WPX (1518832) | WPX Energy | 2012-05-24 bis 2012-06-04 | -8.6% | 8-K 2012-05-15 (0001193125-12-235045): separation and distribution, spin-off, spinoff |
| WPX (1518832) | WPX Energy | 2012-06-07 bis 2012-06-08 | -5.3% | 8-K 2012-05-15 (0001193125-12-235045): separation and distribution, spin-off, spinoff |
| WPX (1518832) | WPX Energy | 2012-06-13 | -6.3% | 8-K 2012-05-15 (0001193125-12-235045): separation and distribution, spin-off, spinoff |
| WPX (1518832) | WPX Energy | 2012-07-24 | -5.0% | 8-K 2012-07-23 (0001193125-12-310401): spin-off |
| WPX (1518832) | WPX Energy | 2012-08-02 bis 2012-08-03 | -7.7% | 8-K 2012-07-23 (0001193125-12-310401): spin-off; 8-K 2012-08-02 (0001193125-12-330222): spin-off |
| WPX (1518832) | WPX Energy | 2012-08-13 bis 2012-08-14 | -4.5% | 8-K 2012-07-23 (0001193125-12-310401): spin-off; 8-K 2012-08-02 (0001193125-12-330222): spin-off |
| WPX (1518832) | WPX Energy | 2012-11-01 bis 2012-11-02 | -6.3% | 8-K 2012-11-01 (0001193125-12-445091): spin-off |
| WPX (1518832) | WPX Energy | 2012-11-07 bis 2012-11-08 | -5.4% | 8-K 2012-11-01 (0001193125-12-445091): spin-off |
| WPX (1518832) | WPX Energy | 2012-11-26 bis 2012-11-27 | -3.6% | 8-K 2012-11-01 (0001193125-12-445091): spin-off |
| WPX (1518832) | WPX Energy | 2013-06-05 bis 2013-06-06 | -5.6% | 8-K 2013-05-29 (0001193125-13-239540): spin-off |
| WPX (1518832) | WPX Energy | 2013-06-20 bis 2013-06-21 | -7.6% | 8-K 2013-05-29 (0001193125-13-239540): spin-off |
| WPX (1518832) | WPX Energy | 2013-06-28 | -3.3% | 8-K 2013-05-29 (0001193125-13-239540): spin-off |
| WPX (1518832) | WPX Energy | 2013-12-18 | -3.6% | 8-K 2013-12-17 (0001193125-13-475659): spinoff |
| WPX (1518832) | WPX Energy | 2014-01-03 | -4.0% | 8-K 2013-12-17 (0001193125-13-475659): spinoff |
| WPX (1518832) | WPX Energy | 2014-01-13 | -3.4% | 8-K 2013-12-17 (0001193125-13-475659): spinoff |
| WPX (1518832) | WPX Energy | 2014-02-10 bis 2014-02-12 | -11.3% | 8-K 2014-02-10 (0001193125-14-043157): spinoff |
| WPX (1518832) | WPX Energy | 2014-02-25 bis 2014-02-27 | -4.9% | 8-K 2014-02-10 (0001193125-14-043157): spinoff; 8-K 2014-02-27 (0001193125-14-071040): spinoff |
| WPX (1518832) | WPX Energy | 2014-03-12 | -3.2% | 8-K 2014-02-10 (0001193125-14-043157): spinoff; 8-K 2014-02-27 (0001193125-14-071040): spinoff |
| WPX (1518832) | WPX Energy | 2014-03-26 | -5.1% | 8-K 2014-02-27 (0001193125-14-071040): spinoff; 8-K 2014-03-19 (0001193125-14-106386): spinoff |
| ALXN (899866) | Alexion Pharmaceuticals | 2017-04-21 | -3.0% | 8-K 2017-03-27 (0000899866-17-000071): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2017-05-17 bis 2017-05-18 | -4.0% | 8-K 2017-05-23 (0000899866-17-000117): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2017-05-23 bis 2017-05-26 | -12.4% | 8-K 2017-05-23 (0000899866-17-000117): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2017-06-16 | -3.4% | 8-K 2017-05-23 (0000899866-17-000117): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2019-10-16 bis 2019-10-17 | -5.1% | 8-K 2019-10-16 (0001193125-19-268091): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2019-11-14 | -3.2% | 8-K 2019-10-16 (0001193125-19-268091): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2020-01-23 bis 2020-01-24 | -5.5% | 8-K 2020-01-28 (0000899866-20-000005): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2020-01-30 bis 2020-01-31 | -7.1% | 8-K 2020-01-28 (0000899866-20-000005): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2020-02-07 | -3.3% | 8-K 2020-01-28 (0000899866-20-000005): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2020-02-24 bis 2020-02-27 | -6.8% | 8-K 2020-01-28 (0000899866-20-000005): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2020-05-01 bis 2020-05-06 | -6.7% | 8-K 2020-05-07 (0001104659-20-058178): spin-off |
| ALXN (899866) | Alexion Pharmaceuticals | 2020-06-02 bis 2020-06-03 | -4.3% | 8-K 2020-05-07 (0001104659-20-058178): spin-off |
| KRFT (1545158) | Kraft Foods | 2013-05-30 | -3.7% | 8-K 2013-05-02 (0001193125-13-196106): spin-off; 8-K 2013-05-29 (0001193125-13-239410): spin off |
| KRFT (1545158) | Kraft Foods | 2013-06-20 bis 2013-06-21 | -6.5% | 8-K 2013-05-29 (0001193125-13-239410): spin off; 8-K 2013-06-20 (0001193125-13-265320): spin off |
| KRFT (1545158) | Kraft Foods | 2013-08-15 bis 2013-08-16 | -4.5% | 8-K 2013-08-01 (0001193125-13-315031): spin-off |
| KRFT (1545158) | Kraft Foods | 2013-11-08 | -3.0% | 8-K 2013-10-30 (0001193125-13-418502): spin-off; 8-K 2013-10-30 (0001545158-13-000006): spin-off; 8-K 2013-11-12 (0001193125-13-438486): separation and distribution |
| KRFT (1545158) | Kraft Foods | 2014-07-31 bis 2014-08-01 | -7.2% | 8-K 2014-07-30 (0001193125-14-286915): spin-off |
| KRFT (1545158) | Kraft Foods | 2015-03-31 | -3.9% | 8-K 2015-04-01 (0001545158-15-000068): separation and distribution, spin-off |
| KSU (54480) | Kansas City Southern | 2015-03-23 bis 2015-03-24 | -9.2% | 8-K 2015-02-23 (0001193125-15-058291): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2015-09-01 | -3.7% | 8-K 2015-08-31 (0001193125-15-307563): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2015-09-28 bis 2015-09-29 | -3.5% | 8-K 2015-08-31 (0001193125-15-307563): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2019-05-23 bis 2019-05-28 | -4.1% | 8-K 2019-05-23 (0001193125-19-155318): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2019-11-06 bis 2019-11-07 | -4.7% | 8-K 2019-11-07 (0001564590-19-041325): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2019-11-21 | -3.2% | 8-K 2019-11-07 (0001564590-19-041325): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2019-12-24 | -3.3% | 8-K 2019-12-23 (0001193125-19-321787): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-01-27 | -3.4% | 8-K 2020-01-14 (0001193125-20-006747): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-02-24 bis 2020-03-12 | -15.0% | 8-K 2020-02-27 (0001564590-20-006995): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-03-19 bis 2020-03-23 | -21.1% | 8-K 2020-02-27 (0001564590-20-006995): spin-off; 8-K 2020-03-20 (0001193125-20-080675): spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-03-27 bis 2020-04-01 | -9.5% | 8-K 2020-02-27 (0001564590-20-006995): spin-off; 8-K 2020-03-20 (0001193125-20-080675): spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-04-09 bis 2020-04-22 | -10.1% | 8-K 2020-03-20 (0001193125-20-080675): spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-05-01 bis 2020-05-06 | -7.1% | 8-K 2020-04-29 (0001193125-20-126532): spin-off; 8-K 2020-04-30 (0001564590-20-019934): spin-off, spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-05-12 bis 2020-05-13 | -12.1% | 8-K 2020-04-29 (0001193125-20-126532): spin-off; 8-K 2020-04-30 (0001564590-20-019934): spin-off, spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-05-19 | -3.3% | 8-K 2020-04-29 (0001193125-20-126532): spin-off; 8-K 2020-04-30 (0001564590-20-019934): spin-off, spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-05-29 | -4.9% | 8-K 2020-04-29 (0001193125-20-126532): spin-off; 8-K 2020-04-30 (0001564590-20-019934): spin-off, spinoff |
| NLSN (1492633) | Nielsen Holdings | 2020-06-09 bis 2020-06-12 | -9.4% | 8-K 2020-06-04 (0001193125-20-160766): separation and distribution |
| NLSN (1492633) | Nielsen Holdings | 2020-06-22 bis 2020-06-25 | -4.6% | 8-K 2020-06-04 (0001193125-20-160766): separation and distribution |
| NLSN (1492633) | Nielsen Holdings | 2020-07-20 | -4.6% | 8-K 2020-07-07 (0001193125-20-188369): spin-off; 8-K 2020-07-22 (0001193125-20-196560): separation and distribution |
| NLSN (1492633) | Nielsen Holdings | 2020-08-20 bis 2020-08-21 | -6.6% | 8-K 2020-07-22 (0001193125-20-196560): separation and distribution; 8-K 2020-08-05 (0001564590-20-036401): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-09-01 | -4.6% | 8-K 2020-08-05 (0001564590-20-036401): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-09-08 bis 2020-09-10 | -3.3% | 8-K 2020-09-09 (0001193125-20-241638): separation and distribution, spin-off; 8-K 2020-09-10 (0001193125-20-243241): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-09-18 bis 2020-09-23 | -9.0% | 8-K 2020-09-09 (0001193125-20-241638): separation and distribution, spin-off; 8-K 2020-09-10 (0001193125-20-243241): spin-off; 8-K 2020-09-24 (0001193125-20-253483): separation and distribution |
| NLSN (1492633) | Nielsen Holdings | 2020-10-09 bis 2020-10-12 | -4.8% | 8-K 2020-09-09 (0001193125-20-241638): separation and distribution, spin-off; 8-K 2020-09-10 (0001193125-20-243241): spin-off; 8-K 2020-09-24 (0001193125-20-253483): separation and distribution |
| NLSN (1492633) | Nielsen Holdings | 2020-10-26 bis 2020-10-29 | -3.7% | 8-K 2020-11-02 (0001193125-20-283281): spin-off; 8-K 2020-11-02 (0001564590-20-049422): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-11-12 | -4.9% | 8-K 2020-11-02 (0001193125-20-283281): spin-off; 8-K 2020-11-02 (0001564590-20-049422): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2020-11-19 | -3.1% | 8-K 2020-11-02 (0001193125-20-283281): spin-off; 8-K 2020-11-02 (0001564590-20-049422): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2021-01-29 bis 2021-02-02 | -3.7% | 8-K 2021-02-01 (0001193125-21-023564): spin-off |
| NLSN (1492633) | Nielsen Holdings | 2021-02-25 bis 2021-02-26 | -7.9% | 8-K 2021-02-01 (0001193125-21-023564): spin-off |
| GGP (1496048) | GGP Inc. | 2018-03-27 bis 2018-03-28 | -5.3% | 8-K 2018-03-27 (0001193125-18-097891): distribution of all, spin-off |
| GGP (1496048) | GGP Inc. | 2018-04-20 | -3.3% | 8-K 2018-03-27 (0001193125-18-097891): distribution of all, spin-off |
| XEC (1168054) | Cimarex Energy | 2018-11-20 bis 2018-11-23 | -6.3% | 8-K 2018-11-20 (0001104659-18-069307): spin-off |
| XEC (1168054) | Cimarex Energy | 2018-12-04 bis 2018-12-11 | -11.7% | 8-K 2018-11-20 (0001104659-18-069307): spin-off |
| XEC (1168054) | Cimarex Energy | 2018-12-14 bis 2018-12-24 | -7.4% | 8-K 2018-11-20 (0001104659-18-069307): spin-off |
| XEC (1168054) | Cimarex Energy | 2019-03-06 bis 2019-03-11 | -5.4% | 8-K 2019-03-01 (0001104659-19-012019): spin-off |
| XEC (1168054) | Cimarex Energy | 2019-03-22 bis 2019-03-25 | -6.3% | 8-K 2019-03-01 (0001104659-19-012019): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2015-06-09 | -3.0% | 8-K 2015-05-22 (0001437107-15-000019): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2017-07-31 bis 2017-08-01 | -9.9% | 8-K 2017-07-31 (0001193125-17-241440): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2017-08-04 | -5.0% | 8-K 2017-07-31 (0001193125-17-241440): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2017-08-10 | -4.7% | 8-K 2017-07-31 (0001193125-17-241440): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2017-08-30 | -3.1% | 8-K 2017-07-31 (0001193125-17-241440): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2018-05-09 | -4.6% | 8-K 2018-05-10 (0001437107-18-000062): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2018-05-15 | -5.0% | 8-K 2018-05-10 (0001437107-18-000062): spin-off; 8-K/A 2018-05-16 (0001437107-18-000065): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2018-05-18 | -4.6% | 8-K 2018-05-10 (0001437107-18-000062): spin-off; 8-K/A 2018-05-16 (0001437107-18-000065): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2018-05-23 bis 2018-05-31 | -4.8% | 8-K 2018-05-10 (0001437107-18-000062): spin-off; 8-K/A 2018-05-16 (0001437107-18-000065): spin-off |
| DISCK (1437107) | Discovery, Inc. | 2020-11-12 | -5.0% | 8-K 2020-11-05 (0001437107-20-000085): spinoff |
| DISCK (1437107) | Discovery, Inc. | 2021-05-12 bis 2021-05-13 | -4.2% | 8-K 2021-05-17 (0001193125-21-162727): spin off, spin-off |
| DISCK (1437107) | Discovery, Inc. | 2021-05-20 bis 2021-05-24 | -6.2% | 8-K 2021-05-17 (0001193125-21-162727): spin off, spin-off; 8-K 2021-05-20 (0001193125-21-167834): separation and distribution, spin-off |
| DISCK (1437107) | Discovery, Inc. | 2021-06-08 | -4.5% | 8-K 2021-05-17 (0001193125-21-162727): spin off, spin-off; 8-K 2021-05-20 (0001193125-21-167834): separation and distribution, spin-off; 8-K 2021-06-10 (0001193125-21-187821): separation and distribution, spinoff |
| DISCK (1437107) | Discovery, Inc. | 2021-06-17 bis 2021-06-18 | -4.6% | 8-K 2021-05-20 (0001193125-21-167834): separation and distribution, spin-off; 8-K 2021-06-10 (0001193125-21-187821): separation and distribution, spinoff |
| DISCK (1437107) | Discovery, Inc. | 2021-07-07 bis 2021-07-08 | -5.0% | 8-K 2021-06-10 (0001193125-21-187821): separation and distribution, spinoff |
| DISCK (1437107) | Discovery, Inc. | 2022-03-04 bis 2022-03-08 | -10.8% | 8-K 2022-03-07 (0001193125-22-066935): separation and distribution |
| DISCK (1437107) | Discovery, Inc. | 2022-03-11 bis 2022-03-14 | -5.3% | 8-K 2022-03-07 (0001193125-22-066935): separation and distribution |
| DISCK (1437107) | Discovery, Inc. | 2022-03-28 bis 2022-03-31 | -6.2% | 8-K 2022-03-07 (0001193125-22-066935): separation and distribution |
| DISCK (1437107) | Discovery, Inc. | 2022-04-05 bis 2022-04-07 | -7.3% | 8-K 2022-03-07 (0001193125-22-066935): separation and distribution; 8-K 2022-04-12 (0001193125-22-103051): separation and distribution, spin off, spin-off, spinoff |
| HBI (1359841) | Hanesbrands | 2016-06-14 | -3.5% | 8-K 2016-06-13 (0001359841-16-000378): spinoff |
| HBI (1359841) | Hanesbrands | 2016-06-24 bis 2016-06-27 | -4.0% | 8-K 2016-06-13 (0001359841-16-000378): spinoff |
| HBI (1359841) | Hanesbrands | 2016-06-30 | -4.4% | 8-K 2016-06-13 (0001359841-16-000378): spinoff |
| HBI (1359841) | Hanesbrands | 2017-05-03 bis 2017-05-04 | -6.1% | 8-K 2017-04-12 (0001359841-17-000054): spinoff |
| HBI (1359841) | Hanesbrands | 2017-05-12 bis 2017-05-17 | -5.1% | 8-K 2017-04-12 (0001359841-17-000054): spinoff |
| HBI (1359841) | Hanesbrands | 2020-04-30 bis 2020-05-13 | -8.7% | 8-K 2020-04-29 (0001193125-20-126433): spin-off |
| HBI (1359841) | Hanesbrands | 2020-05-28 bis 2020-05-29 | -12.7% | 8-K 2020-04-29 (0001193125-20-126433): spin-off |
| QRVO (1604778) | Qorvo | 2017-05-17 | -3.1% | 8-K 2017-05-17 (0001604778-17-000025): spin-off |
| QRVO (1604778) | Qorvo | 2017-06-09 bis 2017-06-15 | -4.4% | 8-K 2017-05-17 (0001604778-17-000025): spin-off |
| BXLT (1620546) | Baxalta | 2015-07-08 | -5.9% | 8-K 2015-07-02 (0001193125-15-244456): distribution of all, separation and distribution, spin off, spin-off |
| BXLT (1620546) | Baxalta | 2015-08-11 | -4.2% | 8-K 2015-07-30 (0001193125-15-269260): spin-off; 8-K 2015-08-10 (0001193125-15-284815): spin-off |
| BXLT (1620546) | Baxalta | 2015-08-20 bis 2015-08-24 | -13.4% | 8-K 2015-07-30 (0001193125-15-269260): spin-off; 8-K 2015-08-10 (0001193125-15-284815): spin-off |
| BXLT (1620546) | Baxalta | 2015-08-27 bis 2015-08-28 | -3.5% | 8-K 2015-07-30 (0001193125-15-269260): spin-off; 8-K 2015-08-10 (0001193125-15-284815): spin-off |
| BXLT (1620546) | Baxalta | 2015-09-08 | -5.2% | 8-K 2015-08-10 (0001193125-15-284815): spin-off |
| BXLT (1620546) | Baxalta | 2015-10-28 bis 2015-10-29 | -4.2% | 8-K 2015-10-29 (0001193125-15-356983): spin off, spin-off |
| BXLT (1620546) | Baxalta | 2015-11-09 | -4.1% | 8-K 2015-10-29 (0001193125-15-356983): spin off, spin-off |
| BXLT (1620546) | Baxalta | 2015-11-27 bis 2015-11-30 | -3.9% | 8-K 2015-10-29 (0001193125-15-356983): spin off, spin-off |
| BXLT (1620546) | Baxalta | 2016-01-06 | -5.3% | 8-K 2016-01-11 (0001193125-16-426678): separation and distribution |
| BXLT (1620546) | Baxalta | 2016-01-11 | -3.4% | 8-K 2016-01-11 (0001193125-16-426678): separation and distribution |
| BXLT (1620546) | Baxalta | 2016-01-27 | -3.6% | 8-K 2016-01-11 (0001193125-16-426678): separation and distribution |
| BXLT (1620546) | Baxalta | 2016-02-08 bis 2016-02-09 | -6.2% | 8-K 2016-01-11 (0001193125-16-426678): separation and distribution |
| BXLT (1620546) | Baxalta | 2016-03-15 bis 2016-03-16 | -3.4% | 8-K 2016-02-16 (0001193125-16-463792): spin off, spin-off |
| BXLT (1620546) | Baxalta | 2016-04-05 | -7.4% | 8-K 2016-04-07 (0001193125-16-533953): spin off |
| CPGX (1629995) | Columbia Pipeline Group | 2015-07-09 | -4.5% | 8-K 2015-07-02 (0001193125-15-243669): distribution of all, separation and distribution |
| CPGX (1629995) | Columbia Pipeline Group | 2015-12-03 bis 2015-12-07 | -5.4% | 8-K 2015-12-07 (0001193125-15-396540): separation and distribution |
| CPGX (1629995) | Columbia Pipeline Group | 2015-12-11 bis 2015-12-14 | -3.3% | 8-K 2015-12-07 (0001193125-15-396540): separation and distribution |
| CPGX (1629995) | Columbia Pipeline Group | 2016-01-06 bis 2016-01-13 | -9.0% | 8-K 2015-12-07 (0001193125-15-396540): separation and distribution |
| CPGX (1629995) | Columbia Pipeline Group | 2016-02-23 | -4.2% | 8-K 2016-02-23 (0001629995-16-000035): separation and distribution, spin-off |
| CPGX (1629995) | Columbia Pipeline Group | 2016-03-08 | -4.1% | 8-K 2016-02-23 (0001629995-16-000035): separation and distribution, spin-off |
| ATVI (718877) | Activision Blizzard | 2016-11-18 bis 2016-11-23 | -3.9% | 8-K 2016-11-25 (0001104659-16-159113): spin-off |
| ATVI (718877) | Activision Blizzard | 2016-11-30 bis 2016-12-01 | -6.2% | 8-K 2016-11-25 (0001104659-16-159113): spin-off |
| CXO (1358071) | Concho Resources | 2019-01-22 bis 2019-01-23 | -7.7% | 8-K 2019-01-04 (0001193125-19-002565): spin-off |
| CXO (1358071) | Concho Resources | 2019-05-22 bis 2019-05-24 | -11.0% | 8-K 2019-05-17 (0001193125-19-150588): spin-off |
| CXO (1358071) | Concho Resources | 2020-01-22 bis 2020-01-27 | -6.4% | 8-K 2020-01-06 (0001358071-20-000002): spin-off |
| CXO (1358071) | Concho Resources | 2020-01-31 bis 2020-02-03 | -3.6% | 8-K 2020-01-06 (0001358071-20-000002): spin-off |
| CXO (1358071) | Concho Resources | 2020-10-19 bis 2020-10-21 | -6.3% | 8-K 2020-10-19 (0001193125-20-271642): spinoff |
| CXO (1358071) | Concho Resources | 2020-10-26 bis 2020-10-29 | -6.9% | 8-K 2020-10-19 (0001193125-20-271642): spinoff |
| CXO (1358071) | Concho Resources | 2020-11-03 | -3.1% | 8-K 2020-10-19 (0001193125-20-271642): spinoff |
| CXO (1358071) | Concho Resources | 2020-11-06 | -3.6% | 8-K 2020-10-19 (0001193125-20-271642): spinoff |
| CXO (1358071) | Concho Resources | 2020-11-12 | -4.3% | 8-K 2020-10-19 (0001193125-20-271642): spinoff |
| CXO (1358071) | Concho Resources | 2021-01-15 | -6.0% | 8-K 2021-01-04 (0001193125-21-001028): spin-off |
| HOLX (859737) | Hologic | 2018-12-06 bis 2018-12-07 | -4.4% | 8-K 2018-11-19 (0001157523-18-002457): spin-off |
| HOLX (859737) | Hologic | 2018-12-17 bis 2018-12-21 | -6.0% | 8-K 2018-11-19 (0001157523-18-002457): spin-off |
| FL (850209) | Foot Locker | 2016-04-11 bis 2016-04-12 | -4.7% | 8-K 2016-03-29 (0000930413-16-006244): spin-off |
| EVHC (1678531) | Envision Healthcare | 2016-12-07 | -3.6% | 8-K 2016-12-07 (0001193125-16-787523): spin-off |
| EVHC (1678531) | Envision Healthcare | 2016-12-13 bis 2016-12-15 | -5.4% | 8-K 2016-12-07 (0001193125-16-787523): spin-off |
| DISH (1001082) | Dish Network | 2017-03-21 | -3.1% | 8-K 2017-03-20 (0001104659-17-017692): spin-off |
| DISH (1001082) | Dish Network | 2017-04-17 bis 2017-04-18 | -8.1% | 8-K 2017-03-20 (0001104659-17-017692): spin-off |
| DISH (1001082) | Dish Network | 2019-05-20 | -5.9% | 8-K 2019-05-20 (0001001082-19-000013): spin-off |
| DISH (1001082) | Dish Network | 2020-12-14 bis 2020-12-22 | -12.0% | 8-K 2020-12-22 (0001104659-20-138382): spin-off |
| ANSS (1013462) | Ansys | 2021-06-07 | -3.0% | 8-K 2021-05-18 (0001013462-21-000023): spin-off |
| ANSS (1013462) | Ansys | 2024-03-05 | -3.4% | 8-K 2024-02-20 (0001193125-24-039509): spin-off |
| DRE (783280) | Duke Realty | 2021-03-03 | -3.4% | 8-K 2021-02-19 (0001193125-21-048953): spin-off |
| ABMD (815094) | Abiomed | 2022-10-28 bis 2022-10-31 | -5.8% | 8-K 2022-11-01 (0001193125-22-274497): spin-off |
| TWTR (1418091) | Twitter | 2018-06-25 | -3.7% | 8-K 2018-06-11 (0001193125-18-189555): spin-off |
| TWTR (1418091) | Twitter | 2018-07-09 bis 2018-07-10 | -6.2% | 8-K 2018-06-11 (0001193125-18-189555): spin-off |
| TWTR (1418091) | Twitter | 2020-03-06 bis 2020-03-18 | -21.9% | 8-K 2020-03-09 (0001193125-20-067362): spin-off; 8-K 2020-03-13 (0001193125-20-072915): spin-off |
| TWTR (1418091) | Twitter | 2020-03-27 bis 2020-04-02 | -8.9% | 8-K 2020-03-09 (0001193125-20-067362): spin-off; 8-K 2020-03-13 (0001193125-20-072915): spin-off |
| TWTR (1418091) | Twitter | 2021-03-02 bis 2021-03-10 | -9.4% | 8-K 2021-03-04 (0001193125-21-069550): spin-off |
| TWTR (1418091) | Twitter | 2021-03-18 bis 2021-03-19 | -5.7% | 8-K 2021-03-04 (0001193125-21-069550): spin-off |
| TWTR (1418091) | Twitter | 2021-03-24 bis 2021-03-25 | -4.8% | 8-K 2021-03-04 (0001193125-21-069550): spin-off |
| TWTR (1418091) | Twitter | 2022-02-11 bis 2022-02-14 | -5.3% | 8-K 2022-02-11 (0001193125-22-035882): spin-off |
| TWTR (1418091) | Twitter | 2022-02-17 bis 2022-02-23 | -7.1% | 8-K 2022-02-11 (0001193125-22-035882): spin-off |
| TWTR (1418091) | Twitter | 2022-03-03 bis 2022-03-07 | -5.8% | 8-K 2022-02-11 (0001193125-22-035882): spin-off |
| TWTR (1418091) | Twitter | 2022-03-11 bis 2022-03-14 | -4.0% | 8-K 2022-02-11 (0001193125-22-035882): spin-off |
| WBD (1437107) | Warner Bros. Discovery | 2022-04-14 bis 2022-04-29 | -12.4% | 8-K 2022-04-12 (0001193125-22-103051): separation and distribution, spin off, spin-off, spinoff; 8-K/A 2022-04-15 (0001193125-22-106913): separation and distribution |
| WBD (1437107) | Warner Bros. Discovery | 2022-05-05 bis 2022-05-11 | -9.7% | 8-K 2022-04-12 (0001193125-22-103051): separation and distribution, spin off, spin-off, spinoff; 8-K/A 2022-04-15 (0001193125-22-106913): separation and distribution |
| WBD (1437107) | Warner Bros. Discovery | 2022-08-05 bis 2022-08-10 | -19.8% | 8-K 2022-08-04 (0001437107-22-000205): separation and distribution |
| WBD (1437107) | Warner Bros. Discovery | 2022-08-15 bis 2022-08-23 | -7.4% | 8-K 2022-08-04 (0001437107-22-000205): separation and distribution |
| WBD (1437107) | Warner Bros. Discovery | 2023-03-01 | -5.8% | 8-K 2023-03-06 (0001193125-23-060775): separation and distribution |
| WBD (1437107) | Warner Bros. Discovery | 2023-03-07 bis 2023-03-15 | -6.5% | 8-K 2023-03-06 (0001193125-23-060775): separation and distribution; 8-K 2023-03-10 (0001193125-23-067637): separation and distribution |
| WBD (1437107) | Warner Bros. Discovery | 2023-03-22 bis 2023-03-24 | -3.8% | 8-K 2023-03-06 (0001193125-23-060775): separation and distribution; 8-K 2023-03-10 (0001193125-23-067637): separation and distribution |
| DAY (1725057) | Dayforce | 2024-03-01 bis 2024-03-06 | -5.7% | 8-K 2024-03-01 (0000950170-24-023418): spin-off |
| DAY (1725057) | Dayforce | 2024-03-25 bis 2024-03-26 | -5.9% | 8-K 2024-03-01 (0000950170-24-023418): spin-off |

## Unklar (≤ −15 % ohne SEC-Beleg)

| Ticker (CIK) | Name | Tage | Gesamtrendite |
| --- | --- | --- | --- |
| AVP (8868) | Avon Products | 2013-10-31 bis 2013-11-05 | -21.9% |
| BBBY (886158) | Bed Bath & Beyond | 2017-09-18 bis 2017-09-21 | -17.7% |
| CELG (816284) | Celgene | 2017-10-26 bis 2017-10-27 | -17.9% |
| CMA (28412) | Comerica | 2016-06-24 bis 2016-06-27 | -16.9% |
| CMA (28412) | Comerica | 2020-02-24 bis 2020-03-23 | -23.0% |
| CMA (28412) | Comerica | 2020-04-13 bis 2020-04-16 | -15.7% |
| CMA (28412) | Comerica | 2020-06-10 bis 2020-06-12 | -17.5% |
| CMA (28412) | Comerica | 2023-03-07 bis 2023-03-14 | -31.3% |
| CMA (28412) | Comerica | 2023-03-17 bis 2023-03-24 | -16.3% |
| CMA (28412) | Comerica | 2023-05-02 bis 2023-05-04 | -16.3% |
| DNR (945764) | Denbury Resources | 2014-11-26 bis 2014-12-15 | -17.8% |
| ETFC (1015780) | E-Trade | 2012-01-26 bis 2012-01-27 | -16.3% |
| ETFC (1015780) | E-Trade | 2016-06-24 bis 2016-06-28 | -16.6% |
| ETFC (1015780) | E-Trade | 2019-10-01 bis 2019-10-02 | -19.4% |
| ETFC (1015780) | E-Trade | 2020-02-24 bis 2020-03-23 | -22.1% |
| FLIR (354908) | FLIR Systems | 2018-10-29 bis 2018-10-31 | -15.1% |
| FLIR (354908) | FLIR Systems | 2020-02-25 bis 2020-03-04 | -21.5% |
| FLIR (354908) | FLIR Systems | 2020-03-09 bis 2020-03-13 | -17.1% |
| FLIR (354908) | FLIR Systems | 2020-03-18 bis 2020-03-23 | -24.2% |
| HES (4447) | Hess Corporation | 2018-12-17 bis 2018-12-24 | -16.3% |
| HES (4447) | Hess Corporation | 2020-03-05 bis 2020-03-17 | -39.5% |
| HES (4447) | Hess Corporation | 2020-04-14 bis 2020-04-20 | -15.7% |
| HES (4447) | Hess Corporation | 2020-06-09 bis 2020-06-12 | -15.8% |
| IPG (51644) | Interpublic Group | 2017-07-25 bis 2017-07-27 | -16.2% |
| IPG (51644) | Interpublic Group | 2020-03-05 bis 2020-03-23 | -19.0% |
| JWN (72333) | Nordstrom | 2017-05-11 bis 2017-05-15 | -17.6% |
| JWN (72333) | Nordstrom | 2018-11-12 bis 2018-11-19 | -16.6% |
| JWN (72333) | Nordstrom | 2020-02-24 bis 2020-03-17 | -26.7% |
| JWN (72333) | Nordstrom | 2020-03-20 bis 2020-03-23 | -26.5% |
| JWN (72333) | Nordstrom | 2020-03-26 bis 2020-04-02 | -15.8% |
| JWN (72333) | Nordstrom | 2020-05-28 bis 2020-06-01 | -17.9% |
| JWN (72333) | Nordstrom | 2020-06-09 bis 2020-06-12 | -19.2% |
| K (55067) | Kellanova | 2020-03-19 bis 2020-03-23 | -19.1% |
| LEG (58492) | Leggett & Platt | 2020-03-05 bis 2020-03-23 | -17.6% |
| LEG (58492) | Leggett & Platt | 2020-05-01 bis 2020-05-13 | -18.5% |
| MRO (101778) | Marathon Oil | 2016-01-06 bis 2016-01-20 | -16.4% |
| MRO (101778) | Marathon Oil | 2020-03-03 bis 2020-03-23 | -53.5% |
| MRO (101778) | Marathon Oil | 2020-03-27 bis 2020-04-01 | -16.5% |
| MRO (101778) | Marathon Oil | 2020-06-09 bis 2020-06-12 | -18.3% |
| NBL (72207) | Noble Energy | 2020-03-03 bis 2020-03-19 | -42.3% |
| NBL (72207) | Noble Energy | 2020-06-09 bis 2020-06-12 | -18.8% |
| PBCT (1378946) | People's United Financial | 2020-03-05 bis 2020-03-16 | -18.8% |
| PBCT (1378946) | People's United Financial | 2020-03-19 bis 2020-04-03 | -18.4% |
| PDCO (891024) | Patterson Companies | 2016-11-18 bis 2016-11-23 | -17.4% |
| PDCO (891024) | Patterson Companies | 2018-03-01 bis 2018-03-02 | -24.3% |
| PXD (1038357) | Pioneer Natural Resources | 2017-08-02 bis 2017-08-07 | -17.2% |
| PXD (1038357) | Pioneer Natural Resources | 2020-03-03 bis 2020-03-18 | -44.1% |
| RHT (1087423) | Red Hat | 2018-06-19 bis 2018-06-27 | -16.0% |
| RRD (29669) | RR Donnelley | 2012-01-17 bis 2012-01-18 | -17.9% |
| SEE (1012100) | Sealed Air | 2012-08-02 bis 2012-08-03 | -18.8% |
| SEE (1012100) | Sealed Air | 2020-03-05 bis 2020-03-18 | -21.6% |
| SRCL (861878) | Stericycle | 2015-10-23 bis 2015-10-26 | -19.3% |
| SRCL (861878) | Stericycle | 2016-04-29 bis 2016-05-02 | -22.3% |
| SRCL (861878) | Stericycle | 2016-07-29 bis 2016-08-01 | -15.6% |
| SRCL (861878) | Stericycle | 2018-02-22 bis 2018-02-23 | -19.8% |
| SWN (7332) | Southwestern Energy | 2015-12-11 bis 2015-12-17 | -22.3% |
| SWN (7332) | Southwestern Energy | 2016-02-09 bis 2016-03-01 | -20.2% |
| SWN (7332) | Southwestern Energy | 2016-03-08 bis 2016-03-09 | -17.0% |
| SWY (86144) | Safeway | 2013-04-25 bis 2013-05-01 | -17.5% |
| TIF (98246) | Tiffany & Co | 2015-01-12 bis 2015-01-13 | -16.6% |
| VAR (203527) | Varian Medical Systems | 2020-03-19 bis 2020-03-23 | -16.8% |
| VIAB (1339947) | Viacom | 2015-08-05 bis 2015-08-07 | -20.7% |
| VIAB (1339947) | Viacom | 2016-02-05 bis 2016-02-10 | -25.0% |
| WBA (1618921) | Walgreens Boots Alliance | 2014-08-05 bis 2014-08-07 | -17.9% |
| WBA (1618921) | Walgreens Boots Alliance | 2020-03-09 bis 2020-03-12 | -16.6% |
| WBA (1618921) | Walgreens Boots Alliance | 2024-06-27 bis 2024-07-09 | -22.8% |
| WFM (865436) | Whole Foods Market | 2014-05-05 bis 2014-05-08 | -19.4% |
| XLNX (743988) | Xilinx | 2019-04-25 bis 2019-04-26 | -17.1% |
| XRX (108772) | Xerox | 2020-02-27 bis 2020-03-23 | -19.9% |
| XRX (108772) | Xerox | 2020-06-09 bis 2020-06-12 | -15.1% |
| JNPR (1043604) | Juniper Networks | 2016-01-28 bis 2016-01-29 | -15.7% |
| AVB (915912) | AvalonBay Communities | 2020-03-06 bis 2020-03-24 | -19.3% |
| DFS (1393612) | Discover Financial | 2020-02-24 bis 2020-03-23 | -28.8% |
| DFS (1393612) | Discover Financial | 2020-03-27 bis 2020-04-03 | -16.1% |
| DFS (1393612) | Discover Financial | 2020-06-09 bis 2020-06-12 | -16.0% |
| DFS (1393612) | Discover Financial | 2023-07-20 bis 2023-07-21 | -15.9% |
| CTRA (858470) | Coterra Energy | 2020-03-11 bis 2020-03-23 | -19.4% |
| QEP (1108827) | QEP Resources | 2014-11-26 bis 2014-12-01 | -18.0% |
| JOY (801898) | Joy Global | 2015-09-01 bis 2015-09-04 | -15.8% |
| ANR (1301063) | Alpha Natural Resources | 2012-11-07 bis 2012-11-15 | -15.3% |
| WPX (1518832) | WPX Energy | 2013-11-06 bis 2013-11-08 | -15.5% |
| ALXN (899866) | Alexion Pharmaceuticals | 2016-12-12 bis 2016-12-13 | -16.7% |
| ALXN (899866) | Alexion Pharmaceuticals | 2019-08-30 bis 2019-09-04 | -15.1% |
| KSU (54480) | Kansas City Southern | 2014-01-24 bis 2014-01-27 | -15.3% |
| KSU (54480) | Kansas City Southern | 2020-03-06 bis 2020-03-23 | -18.8% |
| NLSN (1492633) | Nielsen Holdings | 2016-10-25 bis 2016-10-26 | -16.9% |
| NLSN (1492633) | Nielsen Holdings | 2018-07-26 bis 2018-07-27 | -25.2% |
| GMCR (909954) | Keurig Green Mountain | 2015-08-06 bis 2015-08-14 | -31.2% |
| XEC (1168054) | Cimarex Energy | 2020-02-24 bis 2020-02-27 | -15.5% |
| XEC (1168054) | Cimarex Energy | 2020-03-03 bis 2020-03-23 | -47.7% |
| DISCK (1437107) | Discovery, Inc. | 2021-03-23 bis 2021-03-29 | -34.1% |
| ENDP (1593034) | Endo International | 2015-10-19 bis 2015-10-22 | -18.5% |
| ENDP (1593034) | Endo International | 2015-11-05 bis 2015-11-06 | -15.6% |
| ENDP (1593034) | Endo International | 2016-02-29 bis 2016-03-01 | -21.0% |
| ENDP (1593034) | Endo International | 2016-03-15 bis 2016-03-21 | -23.2% |
| ENDP (1593034) | Endo International | 2016-05-05 bis 2016-05-12 | -42.6% |
| ENDP (1593034) | Endo International | 2016-10-26 bis 2016-11-08 | -22.5% |
| HBI (1359841) | Hanesbrands | 2016-02-02 bis 2016-02-09 | -19.0% |
| HBI (1359841) | Hanesbrands | 2017-02-02 bis 2017-02-06 | -18.3% |
| HBI (1359841) | Hanesbrands | 2018-08-01 bis 2018-08-02 | -19.3% |
| HBI (1359841) | Hanesbrands | 2020-03-03 bis 2020-03-19 | -17.8% |
| HBI (1359841) | Hanesbrands | 2020-11-05 bis 2020-11-06 | -21.5% |
| QRVO (1604778) | Qorvo | 2015-07-30 bis 2015-08-07 | -17.8% |
| QRVO (1604778) | Qorvo | 2020-03-05 bis 2020-03-23 | -20.0% |
| QRVO (1604778) | Qorvo | 2024-05-01 bis 2024-05-03 | -18.1% |
| QRVO (1604778) | Qorvo | 2024-10-30 bis 2024-10-31 | -29.1% |
| ATVI (718877) | Activision Blizzard | 2018-11-05 bis 2018-11-20 | -15.5% |
| ATVI (718877) | Activision Blizzard | 2021-11-03 bis 2021-11-04 | -15.9% |
| CXO (1358071) | Concho Resources | 2019-08-01 bis 2019-08-07 | -25.4% |
| CXO (1358071) | Concho Resources | 2020-03-05 bis 2020-03-18 | -26.5% |
| CXO (1358071) | Concho Resources | 2020-06-09 bis 2020-06-12 | -15.2% |
| HOLX (859737) | Hologic | 2020-03-03 bis 2020-03-18 | -22.4% |
| FL (850209) | Foot Locker | 2017-05-12 bis 2017-05-22 | -17.1% |
| FL (850209) | Foot Locker | 2017-08-18 bis 2017-08-22 | -33.3% |
| FL (850209) | Foot Locker | 2019-05-22 bis 2019-05-31 | -19.3% |
| FL (850209) | Foot Locker | 2019-08-23 bis 2019-08-26 | -18.9% |
| EVHC (1678531) | Envision Healthcare | 2017-10-30 bis 2017-11-10 | -36.0% |
| DISH (1001082) | Dish Network | 2020-02-24 bis 2020-03-23 | -24.6% |
| DISH (1001082) | Dish Network | 2022-05-05 bis 2022-05-12 | -24.4% |
| DISH (1001082) | Dish Network | 2023-06-08 bis 2023-06-15 | -15.8% |
| DRE (783280) | Duke Realty | 2020-03-05 bis 2020-03-23 | -18.0% |
| SIVB (719739) | SVB Financial Group | 2018-10-19 bis 2018-10-29 | -15.1% |
| SIVB (719739) | SVB Financial Group | 2020-02-21 bis 2020-03-17 | -19.9% |
| SIVB (719739) | SVB Financial Group | 2022-03-04 bis 2022-03-08 | -15.4% |
| SIVB (719739) | SVB Financial Group | 2022-07-22 bis 2022-07-26 | -17.2% |
| SIVB (719739) | SVB Financial Group | 2022-10-14 bis 2022-10-24 | -27.1% |
| SIVB (719739) | SVB Financial Group | 2023-03-07 bis 2023-03-10 | -60.4% |
| SIVB (719739) | SVB Financial Group | 2023-03-28 bis 2023-03-31 | -99.6% |
| ABMD (815094) | Abiomed | 2018-11-12 bis 2018-11-14 | -18.4% |
| ABMD (815094) | Abiomed | 2019-08-01 bis 2019-08-02 | -28.0% |
| ABMD (815094) | Abiomed | 2019-11-18 bis 2019-11-19 | -20.2% |
| ABMD (815094) | Abiomed | 2020-03-11 bis 2020-03-13 | -16.9% |
| TWTR (1418091) | Twitter | 2018-07-27 bis 2018-07-31 | -26.9% |
| TWTR (1418091) | Twitter | 2018-12-17 bis 2018-12-24 | -17.1% |
| TWTR (1418091) | Twitter | 2019-10-22 bis 2019-10-25 | -22.0% |
| TWTR (1418091) | Twitter | 2020-10-28 bis 2020-11-02 | -24.7% |
| TWTR (1418091) | Twitter | 2021-04-30 bis 2021-05-03 | -16.1% |
| TWTR (1418091) | Twitter | 2022-05-09 bis 2022-05-18 | -17.1% |
| TWTR (1418091) | Twitter | 2022-07-08 bis 2022-07-12 | -15.8% |
| MXIM (743316) | Maxim Integrated | 2020-02-28 bis 2020-03-20 | -15.5% |
| CTLT (1596783) | Catalent | 2022-10-27 bis 2022-11-04 | -31.7% |
| CTLT (1596783) | Catalent | 2023-04-12 bis 2023-04-19 | -28.2% |
| CTLT (1596783) | Catalent | 2023-05-05 bis 2023-05-17 | -28.0% |
| CTLT (1596783) | Catalent | 2023-10-31 bis 2023-11-02 | -19.4% |
| WBD (1437107) | Warner Bros. Discovery | 2022-11-02 bis 2022-11-09 | -17.7% |
| WBD (1437107) | Warner Bros. Discovery | 2023-11-08 bis 2023-11-09 | -19.0% |
