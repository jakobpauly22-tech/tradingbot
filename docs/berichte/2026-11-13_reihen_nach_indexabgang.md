# Musterprüfung: Kursreihen nach dem Indexabgang

Erstellt 13.11.2026 13:09 mit `tools/pruefe_reihen_nach_indexabgang.py`. Kriterien vor der Suche festgelegt (docs/FUNDAMENTAL.md, Abschnitt „Dritte Datenkorrektur“): K1 mehr als 10 Handelstage Kurse nach dem Abgang; K2 Tagesänderung über ±15 % ohne Split im Fenster −5 … +10 Handelstage; K3 Symbol heute laut SEC einer anderen CIK zugeordnet. Treffer: K1 und (K2 oder K3).

Grundmenge: 218 Firmen mit Indexabgang ab 2012 und gültiger Kursreihe. Treffer: 14 (K2: 13, K3: 2, beide: 1). Nichts wurde korrigiert.

| Ticker (CIK) | Name | Indexabgang | Grund laut Liste | Kursreihe (Quelle) | Name in der Kursquelle | Kurse danach bis | Sprung (K2) | Ticker heute bei (K3) | letzter eigener 10-K/10-Q |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ANR (1301063) | Alpha Natural Resources | 2012-10-02 | Kraft split into two companies. | ANR (tiingo) | Alpha Natural Resources, Inc | 2015-07-16 (699 Tage) | 2012-10-11 +17.0% | – | 2015-08-03 |
| CSC (23082) | Computer Sciences Corporation | 2015-12-01 | CSC completed the corporate spin-off off CSRA. | CSC (tiingo) | Computer Sciences Corp | 2017-04-10 (341 Tage) | 2015-11-30 -54.3% | – | 2017-05-26 |
| TGNA (39899) | Tegna | 2017-06-02 | TGNA completed the corporate spin-off of Cars.com. | TGNA (tiingo) | TEGNA Inc | 2026-03-20 (2211 Tage) | 2017-06-01 -35.3% | – | 2026-03-02 |
| DD (30554) | DuPont | 2017-09-01 | The Dow Chemical Company acquired DuPont. | DD (tiingo) | DuPont de Nemours Inc | 2026-10-30 (2302 Tage) | 2017-09-01 -20.0% | CIK 1666700 DuPont de Nemours, Inc. | 2026-07-31 |
| SIG (832988) | Signet Jewelers | 2018-03-19 | Market capitalization changes. | SIG (yfinance) | Signet Jewelers Limited | 2026-10-30 (2167 Tage) | 2018-03-14 -20.2% | – | 2026-09-09 |
| FL (850209) | Foot Locker | 2019-08-09 | Market capitalization changes. | FL (tiingo) | Foot Locker Inc | 2026-10-30 (1709 Tage) | 2019-08-23 -18.9% | – | 2025-09-02 |
| XEC (1168054) | Cimarex Energy | 2020-03-03 | Gardner Denver acquired Ingersoll Rand's industrial businesses then changed its name to the "new" Ingersoll Rand Inc. | XEC (tiingo) | Cimarex Energy Company | 2021-10-04 (401 Tage) | 2020-03-09 -38.2% | – | 2021-08-06 |
| M (794367) | Macy's | 2020-04-06 | Market capitalization changes. | M (yfinance) | Macy's, Inc. | 2026-10-30 (1651 Tage) | 2020-04-06 +17.0% | – | 2026-09-10 |
| XRX (108772) | Xerox | 2021-03-22 | Market capitalization changes. | XRX (tiingo) | Xerox Holdings Corp | 2026-10-30 (1410 Tage) | – | CIK 1770450 Xerox Holdings Corp | 2026-11-05 |
| MBC (1941365) | MasterBrand | 2022-12-19 | Market capitalization changes. | MBC (yfinance) | MasterBrand, Inc. | 2026-10-30 (969 Tage) | 2022-12-16 +20.8% | – | 2026-11-06 |
| SIVB (719739) | SVB Financial Group | 2023-03-15 | The FDIC placed SVB's main subsidiary, Silicon Valley Bank, into receivership. | SIVBQ (tiingo) | SVB Financial Group | 2026-10-30 (595 Tage) | 2023-03-29 +142.5% | – | 2023-02-24 |
| SEDG (1419612) | SolarEdge | 2023-12-18 | Market capitalization changes. | SEDG (yfinance) | SolarEdge Technologies, Inc. | 2026-10-30 (719 Tage) | 2023-12-14 +16.6% | – | 2026-11-05 |
| CE (1306830) | Celanese | 2025-03-24 | Market capitalization changes. | CE (yfinance) | Celanese Corporation | 2026-10-30 (404 Tage) | 2025-04-03 -16.6% | – | 2026-11-03 |
| KMX (1170010) | CarMax | 2025-10-31 | Market capitalization changes. | KMX (yfinance) | CarMax, Inc. | 2026-10-30 (250 Tage) | 2025-11-06 -24.3% | – | 2026-09-30 |
