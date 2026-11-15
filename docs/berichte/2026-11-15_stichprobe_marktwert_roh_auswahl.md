# Stichprobe Marktwert aus Rohkursen – Auswahl (ohne Marktwerte)

Erstellt 15.11.2026 11:21 mit `tools/stichprobe_marktwert_roh.py`. Kriterien vor dem Lauf festgehalten (docs/FUNDAMENTAL.md, „c2 (2)“): Quelle Streubesitz (dei:EntityPublicFloat), 20 Firmen-Messtage 2016–2024, Startwert 15112026, fest MA/UPS/GOOGL, ≥ 3 mit H ≠ 1, jedes Jahr; Kriterium 0.70 ≤ q ≤ 1.05. Nichts wird angepasst.

Kandidaten: 3119 Firmen-Messtage, Firmen mit H ≠ 1 im Universum: 20.

| Ticker | Messtag | Streubesitz (Mrd. USD) | fest | H ≠ 1 | Rohreihe |
| --- | --- | --- | --- | --- | --- |
| MA | 2020-06-30 | 261.3 | ja |  | roh |
| UPS | 2021-06-30 | 151.3 | ja |  | Abnahme fehlt oder nicht bestanden (UPS) |
| GOOGL | 2018-06-29 | 680.0 | ja |  | roh |
| J | 2019-03-29 | 10.2 |  | ja | roh |
| LEN | 2017-05-31 | 10.6 |  | ja | roh |
| AMCR | 2023-12-31 | 13.9 |  | ja | roh |
| ANDV | 2016-06-30 | 8.8 |  |  | roh |
| CF | 2022-06-30 | 17.4 |  |  | roh |
| PANW | 2024-01-31 | 108.1 |  |  | roh |
| FISV | 2021-06-30 | 70.5 |  |  | roh |
| KMX | 2016-08-31 | 11.3 |  |  | roh |
| WAT | 2016-10-01 | 11.5 |  |  | Abnahme fehlt oder nicht bestanden (WAT) |
| FANG | 2023-06-30 | 23.4 |  |  | roh |
| EIX | 2016-06-30 | 25.3 |  |  | roh |
| FLR | 2018-06-29 | 6.8 |  |  | roh |
| FBHS | 2020-06-30 | 8.8 |  |  | roh |
| SNA | 2019-06-28 | 9.0 |  |  | Abnahme fehlt oder nicht bestanden (SNA) |
| NOV | 2017-06-30 | 12.5 |  |  | roh |
| HAS | 2016-06-24 | 9.4 |  |  | roh |
| KLAC | 2020-12-31 | 39.9 |  | ja | roh |
