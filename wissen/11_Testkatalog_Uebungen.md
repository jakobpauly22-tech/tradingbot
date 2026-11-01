# 11 Testkatalog aus den Übungen

Die Rechenaufgaben mit Musterlösung aus dem Ordner `Übungen` sind als automatische Tests erfasst. Stand: 31.10.2026: **641 Testfälle, alle bestanden** gegen die Referenzformeln in `referenz.py`.

## Zweck

- Jede Formel im Bot muss die Ergebnisse der Musterlösungen reproduzieren. So ist nachweisbar, dass der Code so rechnet wie in der Vorlesung.
- Ablauf in Claude Code: Funktionen des Bots tragen dieselben Namen wie in `referenz.py`; `test_uebungen.py` läuft bei jeder Änderung mit (`pytest`). Ein roter Test stoppt das Feature.
- Dateien im Ordner `Grundlagenwissen/Tests`: `testfaelle_uebungen.json` (Daten), `referenz.py` (Formeln), `test_uebungen.py` (Testlauf), `build_tests.py` (erzeugt die JSON-Datei aus den Musterlösungen).

## Quellen

| Datei | Status | Testfälle |
| --- | --- | --- |
| Übungsblatt_Bonds_1_Vorlesung_mit_Lösung | erfasst | 18 |
| Übungsblatt_Bonds_2_Selbststudium_mit_Lösung | erfasst (20 Anleihen × 8 Kennzahlen) | 160 |
| Übungsblatt_FuturesForwards_1_Vorlesung_mit_Lösung | erfasst | 13 |
| Übungsblatt_FuturesForwards_2_Selbststudium_mit_Lösung | erfasst | 15 |
| Übungsblatt_Optionen_mit_Lösung | erfasst | 12 |
| BFIN Übungssammlung Hackethal_mit Lösungen | erfasst | 48 |
| OFIN Uebung - SoSe26 (Tutoriumsfolien mit Lösungen) | erfasst | 111 |
| Accounting 1 SoSe 2026 Übungsaufgaben + Accounting_1_WiSe_2026_27_Lösung | erfasst, soweit Aufgabe und Lösung übereinstimmen (28 von 35 Aufgaben) | 264 |
| Bonds_1, FuturesForwards_1, Optionen, BFIN „ohne Lösungen“ | Dubletten der Fassungen mit Lösung | 0 |

## Abdeckung nach Thema

| Thema | Testfälle | Wissensdatei |
| --- | --- | --- |
| Anleihen, Duration, Konvexität, Immunisierung | 186 | 02 |
| Zinsstruktur (YTM, Spot, Forward, Stückzinsen) | 6 | 02 |
| Barwert, Kapitalwert, interner Zins, Annuität, ewige Rente | 31 | 01, 02 |
| Rendite, Erwartungswert, Varianz, Portfolio, CML | 24 | 02 |
| CAPM, Performancemessung, Faktormodelle | 19 | 02, 04, 09 |
| Aktienbewertung (DDM, PVGO, implizites Wachstum, FCF) | 17 | 01, 02 |
| Kapitalstruktur, MM, Tax Shield, Trade-off | 33 | 01 |
| Forwards, Futures, Hedging | 28 | 03 |
| Optionen (Binomial, amerikanisch, Black-Scholes, Parität) | 22 | 03 |
| Agency (Asset Substitution) | 11 | 02 |
| Kostenartenrechnung (FIFO/LIFO, Abschreibungen, kalkulatorische Zinsen) | 66 | 08 |
| Kostenstellenrechnung (BAB, Block-, Treppen-, Gleichungsverfahren, Zuschlagssätze) | 81 | 08 |
| Kalkulation (Zuschlag, Division, Activity-based Costing) | 48 | 08 |
| Erfolgsrechnung (Voll-/Teilkosten, GKV/UKV, ein- und mehrstufiger Deckungsbeitrag) | 33 | 08 |
| Break-even (inkl. Währungseffekte) | 17 | 08 |
| Engpassplanung, Zusatzauftrag, Make-or-Buy | 19 | 08 |

## Accounting 1: Zuordnung von Aufgaben und Lösung

Die Lösung stammt aus dem **WiSe 2026/27** (Prof. Dr. Sara Bormann), die Aufgaben aus dem **SoSe 2026** (Prof. Dr. Anna Rohlfing-Bastian). Jede Aufgabe wurde anhand ihrer Zahlen nachgerechnet, bevor sie zum Test wurde.

| Status | Aufgaben (Nummerierung SoSe 2026) |
| --- | --- |
| Lösung passt, Rechenaufgabe als Test erfasst (23) | 3.1, 3.2, 3.3, 3.5, 3.6, 4.1, 4.2, 4.4 (= Lösung 4.3), 4.5, 5.1, 5.2, 5.3, 5.4, 5.6, 5.7, 6.2, 7.1, 7.3, 7.4, 7.5, 8.1, 8.2, 9.2 (= Lösung 9.3) |
| Lösung passt, Konzeptaufgabe (5) | 1.1, 1.2, 1.3, 2.2, 2.3 |
| Keine passende Lösung (7) | 2.1 (Telefontarife; Lösung behandelt einen T-Shirt-Laden), 3.4 (andere Bilanz; Lösung 6.672.000 € statt rund 1,3 Mio. €), 4.3 (Tragemi), 5.5 (Produkte A/B; Lösung: Pflege-Sets), 6.1 (Bikey; Lösung: Kabel), 7.2 (Durchschlag; Lösung mit Beschäftigungsabweichung), 9.1 (Sigmatherm; Lösung: Schneider GmbH) |
| Lösung ohne Aufgabe im SoSe-Blatt (8) | Lösung 2.1, 3.4, 4.4, 5.5, 6.1, 7.2, 9.1, 9.2; dafür fehlt das Aufgabenblatt WiSe 2026/27 |

## Auffälligkeiten beim Nachrechnen

- **Bonds 2, absolute Preisänderung:** Die Spalte nutzt Duration **und** Konvexität, nicht nur die Duration und auch nicht die exakte Neubewertung (Funktion `abs_change_dur_conv`).
- **Rundung und Abschneiden:** Einige Folien schneiden Nachkommastellen ab (z.B. 6,818 → 6,81, 2,946 → 2,94) oder rechnen mit gerundeten Zwischenergebnissen (σ²_M = 0,0071 statt 0,00711; Spot Rates auf zwei Stellen). Die Toleranz jedes Testfalls ist darauf abgestimmt und im Feld `hinweis` begründet.
- **Black-Scholes:** Musterlösung 2,57 per Tabellenwert N(0,12) = 0,5478; exakt 2,5675.
- **IRR-Fallstricke bestätigt:** zwei positive interne Zinsfüße (12 % und 54 %, Aufgabe 23), IRR und NPV wählen unterschiedliche Projekte (Aufgabe 22, Skalenproblem 0,90 vs. 89,52).
- **Wachstum über dem Diskontsatz** (g = 6 % > r = 5 %) liefert keinen endlichen Aktienwert; der Test erwartet „unendlich“, der Bot muss diesen Fall abfangen.
- **Accounting, Restwertverfahren:** Die Zinsen werden auf den Durchschnitt aus Restwert am Jahresanfang und -ende gerechnet (Nagel-Blitz Jahr 1: 10 % · 81.000 = 8.100 €), nicht auf den Restwert am Jahresanfang.
- **Accounting, Abzugskapital:** Die Musterlösung zählt auch die Rückstellungen zum Abzugskapital (3.3 d: 1,86 Mio. €), obwohl der Hinweis der Aufgabe nur Anzahlungen und Lieferantenverbindlichkeiten als zinslos nennt.
- **Accounting, gerundete Sätze:** Die Lösung rechnet mit 42,26 % (degressive Abschreibung, Restwert 20.007 statt 20.000 €), 96,64 % (5.1), 2,82 (5.7) und 2,67 € Gemeinkosten je Stück (5.2 b: 7,545 statt 7,5417 €). Die Tests bilden das ab und prüfen zusätzlich den exakten Wert, wo die Lösung ihn nennt.
- **Accounting 7.5 b:** „Produkt D“ in der Lösung meint P4 (negativer Deckungsbeitrag I von −1.000 €).

## Konzeptfragen (nicht automatisiert)

Wahr/Falsch-Aufgaben aus BFIN und dem Optionsblatt sind durch das Grundlagenwissen abgedeckt. Lösungen zum Optionsblatt, Aufgabe 1 (hergeleitet, die Musterlösung markiert sie nur grafisch): a) wahr, b) falsch (Volatilität steckt in u und d), c) falsch (höherer Basispreis erhöht den Putwert), d) wahr, e) falsch (Verlust unbegrenzt), f) wahr.

Accounting 1 laut Musterlösung:

| Aufgabe | Lösung |
| --- | --- |
| 2.3 Auszahlung, Aufwand, Kosten | (1) Barkauf: Auszahlung; (2) Zielkauf: nichts davon; (3) Zielkauf mit sofortigem Verbrauch: Aufwand und Kosten; (4) Dividende: Auszahlung; (5) Eigenkapitalkosten 20 %: Kosten (Zusatzkosten); (6) Forderungsausfall: Aufwand und Kosten |
| 3.1 (b) | LIFO, um die Bestände bei fallenden Preisen möglichst hoch zu bewerten |
| 3.3 (e) | Näherungen: konstanter und pauschaler Zinssatz, keine Trennung von Eigen- und Fremdkapital, kein Geschäftsrisiko, Bilanzmittelwerte, keine Zinseszinsen |
| 4.2 (c) | Block: einfach, Voraussetzung keine Leistungen zwischen Vorkostenstellen. Treppe: Voraussetzung nur einseitige Beziehungen; Nachteil: Reihenfolge muss festgelegt werden, Leistungsströme werden unterdrückt |
| 4.4 | (a) Block geeignet, weil Vorkostenstellen nur Endkostenstellen beliefern; (b) Treppe korrekt, keine Rückkopplung; (c) Rückkopplung durch KS5 → KS1, daher Gleichungsverfahren |
| 4.5 (d) | Geeignet: Gleichungs-, iteratives und Gutschrift-/Lastschriftverfahren; ungeeignet: Block- und Treppenverfahren |
| 6.2 (g) | Die Zuschlagskalkulation rechnet Kleinserien zu wenig Gemeinkosten zu: Großserien subventionieren Kleinserien |
| 7.5 (b) | P4 hat einen negativen DB I: einstellen, Preis erhöhen oder variable Kosten senken |
| 9.2 (e) | Markt- und Produktionsverbund werden mit proportionalen Stückkosten nicht erfasst |

## Nutzen für den Bot

| Testgruppe | Bot-Modul |
| --- | --- |
| Duration, Konvexität, Zinsstruktur | Anleihe-ETFs im Multi-Asset-Teil, Zinsrisiko im Risk-Manager |
| DDM, PVGO, FCF, WACC | Fundamental-Engine (Bewertung) |
| CAPM, Sharpe, Alphas | Backtest-Bericht und Journal |
| Portfolio, MVP, CML | Gewichtung im Core |
| Forwards, Hedge Ratio | Späteres Absicherungsmodul, Plausibilität von Futurespreisen |
| Binomial, Black-Scholes | Implizite Volatilität als Signal |
| Deckungsbeitrag, Break-even, Voll- vs. Teilkosten | Fundamental-Engine: Fixkostenanteil und operativer Hebel; Warnsignal, wenn Gewinne durch Lageraufbau entstehen (Vollkosten aktivieren Fixkosten) |
| Abschreibungen, kalkulatorische Zinsen | Bilanzqualität: Abschreibungspolitik und Kapitalbindung vergleichen |
| Break-even mit Währung (8.1) | News-Engine: Einordnung von Wechselkursmeldungen für Exporteure |

## Erweiterung

Neue Übungsblätter mit Lösung in den Ordner `Übungen` legen; Claude ergänzt die Fälle in `build_tests.py` und prüft sie. Für Accounting 1 fehlen noch Lösungen zu sieben SoSe-Aufgaben (oben aufgeführt). Mit dem Aufgabenblatt WiSe 2026/27 lassen sich zusätzlich die acht übrigen Lösungen erfassen.
