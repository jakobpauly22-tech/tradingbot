# Risiko-Übersicht über alle Bücher

Festlegungen vor dem Code (Jakob, 25.11.2026). Roadmap: Entwicklungsreihenfolge Punkt 4, „Risiko-Übersicht über alle
Bücher mit Value at Risk und Stresstests“. Grundlagen: `wissen/04_Finanzielles_Risikomanagement.md`, Abschnitte 1 und 3
(VaR, Expected Shortfall, historische Simulation, Stressed VaR und Stresstests).

Grenzen, Fenster und Methoden in diesem Dokument werden nach dem ersten Lauf nicht geändert. Weicht ein Ergebnis von der
Erwartung ab, wird die Ursache gesucht und mit Jakob besprochen, nicht nachjustiert.

## 1. Zweck und Wirkung

- **Reine Auswertung.** Die Übersicht hat keine Wirkung auf Vorschläge, Urteile des Risk-Managers, Freigaben, Orders oder
  das Journal. Sie liest das Journal nur und schreibt in eine eigene Datei.
- **Je Buch und gesamt.** Gesamt in zwei getrennten Blöcken: „real“ und „Skalierungsbücher zusammen“. Die beiden werden
  nie zusammengezählt. Titel, die in mehreren Skalierungsbüchern liegen (z. B. fundamental_a und fundamental_b), werden
  in der Summe zusammengefasst und markiert.
- **Stand der Bestände:** nach dem Abgleich des Tageslaufs, ohne die Vorschläge des Tages. Gesendete, nicht ausgeführte
  Orders („unterwegs“) erscheinen nur als Hinweis und gehen nicht in die Kennzahlen ein.

## 2. Zuordnung der Bücher zu Core und Satellite

Quelle: `config/betrieb.yaml`, Abschnitt `buecher`, Feld `rolle` (Entscheidungen Jakob 02.11.2026 und 15.11.2026). Die
Übersicht liest die Rolle zur Laufzeit aus dieser Datei; die Tabelle hält den Stand vom 25.11.2026 fest.

| Buch | Art | Rolle | Inhalt |
| --- | --- | --- | --- |
| real | real | Core | 500 € in SPYI.DE (Satellite-Anteil fließt in den Core, Satellite nur als Schatten) |
| fundamental_a | Skalierung | Core | 20 Einzelaktien, Originalscore |
| fundamental_b | Skalierung | Core | Einzelaktien, nur Qualitätshälfte |
| crossover | Skalierung | Satellite | Satellite-ETFs, Crossover 50/200 |
| momentum | Skalierung | Satellite | Satellite-ETFs, Momentum 12−1 |
| regime | Skalierung | Core | SPYI.DE oder Kasse (Schattenbuch der Regime-Engine) |

Ein neues Buch ohne `rolle` wird in der Übersicht als „Rolle unbekannt“ gemeldet und bekommt keine Drift-Schwelle.

## 3. Bewertungsbasis

- Stückzahl je Titel aus `Journal.bestand` (Ausführungen und gebuchte Kapitalmaßnahmen), Kasse je Währung aus
  `Journal.kasse_je_waehrung`.
- Kurse aus dem Kurs-Cache des Betriebs (`daten/betrieb/cache/kurse`), so wie der Tageslauf sie geladen hat; USD in EUR
  mit EURUSD (`EURUSD=X`) aus demselben Cache.
- Abnahmebedingung: Die Summe aus Positionen und Kasse je Buch ist gleich dem Buchwert, den der Tageslauf für denselben
  Tag speichert und die Oberfläche zeigt.
- Konvention des Buchwerts (Jakob 25.11.2026): Die Übersicht übernimmt sie, weist Unterschiede sichtbar aus und gleicht
  nichts still an. Seit Befund 1 (25.11.2026) steht die USD-Kasse im Buchwert zum Kurs des Laufs
  (`Journal.kasse_bewertet`); die Zeile „Unterschied USD-Kasse“ bleibt als Kontrollzeile (erwartet 0,00 €, D5). Kurse
  kommen je Buch herein. Hintergrund und offener Punkt 2: `docs/BETRIEB.md`, Abschnitt „Punkte zum Buchwert“.

## 4. Zuordnung der Titel (Land, Sektor, Anlageklasse, Währung)

Jede Angabe trägt ein Kennzeichen: **exakt**, **Näherung** oder **unbekannt**.

### 4a. Einzelaktien (exakt, aus dem SEC-Cache des Betriebs)

- **Land:** Geschäftsadresse aus den SEC-`submissions` (`addresses.business`); US-Bundesstaaten zählen als USA.
  Zusatzspalte: Land der Inkorporation (`stateOfIncorporation`), z. B. PNR: Geschäftsadresse Vereinigtes Königreich,
  inkorporiert in Irland (SEC-Stand November 2026).
- **Sektor:** SIC-Division (A–J, amtliche Bereiche) und als zweite Ebene die zweistellige Major Group. Ausgewiesen als
  „SIC“, nicht als GICS.
- **Anlageklasse:** Aktie. **Währung:** USD (Notierung und wirtschaftlich).
- Fehlt der Titel im SEC-Cache des Betriebs, gilt „unbekannt“; das wird gezählt und gemeldet. Es wird nichts nachgeladen.

### 4b. ETFs und ETCs (Näherung: Indexregion, Variante A)

Ein ETF wird nie anteilig auf Länder oder Sektoren aufgeteilt; es gibt keine Durchschau auf die Einzeltitel. Die
Zuordnung steht von Hand in `config/risiko_uebersicht.yaml` mit Index und Quelle (`config/technik.yaml`, `config/betrieb.yaml`,
`config/kontrakte.yaml`). Kennzeichnung „Näherung: Indexregion“.

| Ticker | Anlageklasse | Region | Sektor | Währung wirtschaftlich |
| --- | --- | --- | --- | --- |
| SPYI.DE | Aktien | Welt (ACWI IMI), nicht aufgeteilt | breit gestreut | Welt gemischt |
| IUSA.DE | Aktien | USA | breit gestreut | USD |
| EUNK.DE | Aktien | Europa | breit gestreut | Europa gemischt |
| EUNN.DE | Aktien | Japan | breit gestreut | JPY |
| SXR1.DE | Aktien | Pazifik ex Japan | breit gestreut | Pazifik gemischt |
| EUNM.DE | Aktien | Schwellenländer | breit gestreut | Schwellenländer gemischt |
| EUNH.DE | Anleihen Staaten | Eurozone | – | EUR |
| EUN5.DE | Anleihen Unternehmen | Eurozone | – | EUR |
| IBCI.DE | Anleihen inflationsindexiert | Eurozone | – | EUR |
| IUSM.DE | Anleihen Staaten | USA | – | USD |
| IUSP.DE | Anleihen Staaten, Lokalwährung | Schwellenländer | – | Schwellenländer gemischt |
| 4GLD.DE | Gold (ETC) | – | – | Gold |

„–“ in der Spalte Sektor wird als „kein Sektor (Anleihen, Gold)“ ausgewiesen. Ein ETF oder ETC, der nicht in der Tabelle steht, gilt als „unbekannt“ und wird gemeldet. Schlüssel ist immer der
Yahoo-Ticker; IBKR-Symbole sind nur andere Namen desselben Titels (z. B. SEML = IUSP.DE, IJPA = EUNN.DE, laut
`config/kontrakte.yaml`).

### 4c. Währung in zwei Sichten

1. **Notierung und Kasse (exakt):** Notierungswährung aus `config/kontrakte.yaml`, Kasse je Währung aus dem Journal.
2. **Wirtschaftlich (Näherung):** Einzelaktien nach Notierung, ETFs nach Tabelle 4b. Diese Sicht zeigt zum Beispiel, dass
   IUSA in Euro notiert, aber ein USD-Risiko trägt.

## 5. Klumpen-Kennzahlen

Je Buch und je Gesamtblock: Anteil je Titel, Land/Region, Sektor, Anlageklasse und Währung (beide Sichten), jeweils mit
Kasse als eigenem Block; größte Position; Anteil der fünf größten Positionen; Herfindahl-Index HHI = Σ wᵢ² über die
Positionen ohne Kasse und die effektive Titelzahl 1/HHI.

## 6. Value at Risk und Expected Shortfall

- **Methode:** historische Simulation mit vollständiger Neubewertung. Szenario-GuV(t) = Σ heutige Stückzahl × heutiger
  Kurs in EUR × rᵢ(t). Kasse in EUR: 0 %. Kasse in USD: Wechselkursänderung.
- **Euro-Sicht:** für USD-Titel rᵢ,EUR = (1 + rᵢ,USD) · (1 + r_FX) − 1, r_FX aus EURUSD. In Euro notierte ETFs enthalten
  ihr Währungsrisiko bereits im Kurs.
- **Kalender:** Xetra-Handelstage (`betrieb/kalender.py`). US-Kurse und EURUSD werden auf Xetra-Tage vorgetragen. Bekannte
  Einschränkung: Xetra schließt 17:30, NYSE 22:00 Uhr; die Tagesrenditen sind nicht zeitgleich.
- **Fenster:** die letzten 500 Xetra-Tagesrenditen bis zum Stichtag (501 Kurse).
- **Haltedauer:** 1 Tag und 10 Tage. 10 Tage aus überlappenden echten 10-Tages-Renditen je Titel im selben Fenster
  (491 Szenarien), Pᵢ(t+10)/Pᵢ(t) − 1. √10 · VaR(1 Tag) nur als Vergleichswert.
- **Niveaus:** 95 % und 99 %.
- **Quantil-Konvention:** Die n Szenario-GuV werden aufsteigend sortiert. VaR = Verlust der k-ten schlechtesten Beobachtung
  mit k = ⌈n · (1 − α)⌉, ohne Interpolation; ES = Durchschnitt der k schlechtesten Beobachtungen (einschließlich der
  k-ten). Bei n = 500: k = 25 (95 %) und k = 5 (99 %); bei n = 491: k = 25 und k = 5. Neue Funktion in
  `kennzahlen/`, neben `performance.var_cvar_historisch`; diese bleibt unverändert (Backtests nutzen sie).
- **Hinweis 99 %:** Bei 500 Beobachtungen liegen nur 5 Werte im Rand. Der Wert wird als „unsicher“ gekennzeichnet.
- **Beitrag je Position:** ES-Beitrag = durchschnittliche GuV der Position in den k schlechtesten Szenarien des Buchs. Die
  Beiträge summieren sich zum ES des Buchs.
- **Laufende Kontrolle:** Überschreitungen des VaR(1 Tag, 99 %) vom Vortag gegen die tatsächliche Wertänderung des Buchs
  (ohne Tage mit Ausführungen, Ein- oder Auszahlungen) werden ab dem ersten Lauf gezählt. Nur Anzeige; ein
  statistischer Test (Kupiec) frühestens nach 250 Tagen und nur nach Entscheidung von Jakob.

### 6a. Kurze Historie: Ersatzreihen

Feste Rangfolge, je Titel offen gekennzeichnet:

1. eigene Reihe, wenn sie das ganze Fenster abdeckt;
2. Reihe des Vorgängers aus einer gebuchten Kapitalmaßnahme (Tickerwechsel);
3. Ersatz: US-Einzelaktie → IUSA.DE; ETF → ETF derselben Region und Anlageklasse aus dem Cache (Zuordnung in
   `config/risiko_uebersicht.yaml`); jeweils ohne Beta-Skalierung.

Das Fenster wird nie je Titel gekürzt (das würde die gemeinsame Verteilung zerstören). Je Buch wird der Anteil am Wert
ausgewiesen, der mit Ersatz gerechnet ist. Über 25 % gilt der VaR des Buchs als „eingeschränkt“.

## 7. Stresstests

- **Methode:** heutige Stückzahlen statisch auf historische Fenster: keine Stops, keine Signale, kein Rebalancing, Kasse
  0 % (USD-Kasse mit Wechselkurs, wo vorhanden). Ausgewiesen in EUR (Ausnahme 2008, siehe unten) und in %:
  Rendite vom ersten bis zum letzten Tag des Fensters und maximaler Drawdown des statischen Bestands innerhalb des
  Fensters.
- **Fenster (fest, nach Kalender, unabhängig vom Bestand):**

| Name | von | bis | Begründung |
| --- | --- | --- | --- |
| 2008 | 09.10.2007 | 09.03.2009 | Hoch bis Tief des S&P 500 |
| 2020 | 19.02.2020 | 23.03.2020 | Hoch bis Tief des S&P 500 |
| 2022 | 03.01.2022 | 30.12.2022 | Kalenderjahr; der Zinsschock traf Anleihen das ganze Jahr; der maximale Drawdown im Fenster deckt das Tief ab |

- **Ersatzreihen:** Rangfolge wie in 6a. Kein Titel wird still mit 0 % gerechnet: Was nicht abbildbar ist, steht als
  Lücke mit Anteil am Wert im Ergebnis.
- **2020 und 2022:** eigene Reihen (Kurs-Cache ab 2011/2012), Euro-Sicht mit EURUSD. Später gelistete Titel nach 6a.
- **2008, Variante b:** Der Kurs-Cache beginnt 2011/2012, EURUSD am 03.01.2011. Vor 2011 gibt es nur `_SP500TR`
  (S&P 500 Total Return, USD, ab 1988). Deshalb:
  - US-Einzelaktien, IUSA.DE und SPYI.DE werden mit `_SP500TR` in USD gerechnet; SPYI zusätzlich als „Näherung: Welt
    über USA“.
  - Alle übrigen Titel (Europa, Japan, Pazifik, Schwellenländer, Anleihen, Gold) sind „nicht abbildbar“ und stehen als
    Lücke im Ergebnis.
  - Kennzeichnung im Ergebnis: **„USD-Sicht ohne Währungseffekt, überzeichnet für Euro-Anleger“** (der US-Dollar stieg
    Ende 2008 gegenüber dem Euro).
- **Tresor:** Alle Stressfenster liegen vor dem 01.01.2025.

## 8. Schwellen und Meldungen

Alle Schwellen sind Hinweise ohne jede Wirkung (kein Veto, kein Zwangsverkauf, keine Sperre).

| Schwelle | Bücher | Meldung |
| --- | --- | --- |
| VaR nicht berechenbar | alle | Telegram |
| Ersatzanteil > 25 % des Buchwerts | alle | Telegram |
| VaR(10 Tage, 99 %) > 10 % des Buchwerts | Satellite | nur Anzeige |
| VaR(10 Tage, 99 %) > 15 % des Buchwerts | Core | nur Anzeige |
| Einzelaktie > 7,5 % des Buchwerts | Core | nur Anzeige |
| Einzelaktie > 12,5 % des Buchwerts | Satellite | nur Anzeige |
| Stressverlust > 20 % | alle | nur Anzeige |

- **5-%-Regel im Core (Jakob 25.11.2026):** Die Grenze von 5 % je Einzelaktie gilt beim Kauf. Laufend durch Kursdrift
  nur Hinweis ab 7,5 % (Core) bzw. 12,5 % (Satellite, Grenze 10 % je Einzelaktie); kein Zwangsverkauf. Die ETF-Grenze
  von 25 % im Satellite wird nur angezeigt, ohne eigene Drift-Schwelle.
- **Telegram:** nur beim Wechsel von „unter“ auf „über“ der Schwelle; danach erst wieder, wenn der Wert zwischendurch unter
  die Schwelle gefallen ist. Probe und Kopie senden nie. Eurobeträge nur bei `benachrichtigung.eurobetraege: true`.
- **Risikoschwellen (VaR, Drift, Stress):** in den ersten 4 Wochen ab dem ersten echten Tageslauf mit Übersicht nur
  Anzeige. Danach entscheidet Jakob anhand der Werte, ob und welche davon melden. Das Datum des ersten Laufs wird hier
  eingetragen.

## 9. Einbindung, Ablage und Daten

- **Tageslauf:** letzter Schritt, nachdem die Vorschläge gespeichert sind; in `try/except`, ein Fehler erzeugt nur eine
  Meldung (und Telegram „VaR nicht berechenbar“), der Tageslauf läuft weiter.
- **Werkzeug `tools/risiko_uebersicht.py`:** Neuberechnung für einen Stichtag, nur aus dem Cache, unter Netzsperre; Export
  der Szenarien je Position als CSV für die Handrechnung.
- **Ablage:** `daten/betrieb/risiko/uebersicht.parquet`, eine Zeile je Tag × Buch × Kennzahl. Keine neue Journal-Tabelle.
  In der Probe nur über `schreibpfad` in die Schicht (`daten/schicht.py`).
- **Netz:** keine Abrufe; nur Kurse, Wechselkurse und SEC-Daten, die schon im Betriebs-Cache liegen.
- **Tresor:** Das VaR-Fenster reicht in die Zeit ab 2025 und läuft deshalb nur im Betrieb; die Ablage liegt im
  Betriebsbereich und ist für Backtest- und Auswertungswerkzeuge nicht lesbar. Eintrag der Kategorie in
  `docs/TRESOR_BEKANNT.md` mit dem ersten echten Lauf.

## 10. Abnahmekriterien

1. **Handrechnung VaR, Buch momentum:** Szenarien-CSV aus dem Werkzeug, Nachrechnung in Excel (Σ Stück × Kurs × r,
   sortieren, k-te schlechteste, ES); identisch bis auf Rundung (≤ 0,01 €).
2. **Handrechnung Währung:** zwei USD-Titel aus fundamental_a an drei Szenariotagen einzeln nachgerechnet.
3. **Handrechnung Stress, Buch real:** Stück × Kurs × (SPYI 23.03.2020 / SPYI 19.02.2020 − 1), exakt.
4. **Klumpen:** Anteile je Buch ergeben 100 % einschließlich Kasse; Buchwert exakt gleich dem gespeicherten Buchwert; kein
   ETF auf Länder oder Sektoren aufgeteilt.
5. **Plausibilität:** VaR(1 Tag, 95 %) des Buchs real innerhalb ±30 % von 1,65 · σ · V (σ aus demselben Fenster).
   Außerhalb: Ursache suchen, nicht nachjustieren.
6. **Keine Wirkung:** zwei Proben mit und ohne Übersicht liefern identische Vorschläge und Urteile; eine absichtlich
   ausgelöste Ausnahme in der Übersicht lässt den Tageslauf weiterlaufen.
7. **Keine Netzabrufe, Probe-Schicht:** Test unter Netzsperre; nach einer Probe sind die Betriebsdateien byteweise
   unverändert.
8. **Laufzeit** unter 10 s zusätzlich; volle Suite grün einschließlich `tests/musterloesungen/test_uebungen.py`.

## 11. Schritte

| Schritt | Inhalt |
| --- | --- |
| 0 | dieses Dokument |
| 1 | Zuordnung, Klumpen und Bewertungsbasis aus dem Journal, mit Tests |
| 2 | VaR/ES mit Währung, Ersatzreihen und Beiträgen |
| 3 | Stresstests 2020, 2022 und 2008 (Variante b) |
| 4 | Einbindung in den Tageslauf, Ablage, Protokoll, Werkzeug mit CSV-Export |
| 5 | Oberfläche, Schwellen, Telegram |
| 6 | Abnahme mit Handrechnung, Probelauf, Bericht in `docs/berichte/` |

## 12. Backlog

- **2008 vollständig in Euro (Variante a):** einmaliger Download langer Reihen per eigenem Werkzeug außerhalb des
  Tageslaufs, als Entwicklungsdaten vor 2025 (z. B. FRED DEXUSEU, regionale Index- und Anleihereihen). Erst nach eigenem
  Plan und Zustimmung von Jakob.
