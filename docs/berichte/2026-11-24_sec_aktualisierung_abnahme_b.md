# SEC-Aktualisierung: erster echter Lauf und Abnahme B (24.11.2026)

Festlegung: `docs/BETRIEB.md`, Abschnitt „SEC-Aktualisierung im Betrieb“. Schritt 5 wurde auf Jakobs Entscheidung vom
24.11.2026 vorgezogen (Option b: sonst hätte der Tageslauf bis zum 05.12. jeden Abend „STAND.json fehlt“ als
Sofortmeldung geschickt). Kriterien für diesen Lauf nach Jakob (24.11.2026):
- (a) Die Erstmeldungen des Entwicklungs-Caches sind im Betriebs-Cache identisch. Neue Zeilen haben `filed` ab dem
  30.10.2026 oder sind als nachgelieferte Einreichung gemeldet.
- (b) `bewertung_am(18.11.2026)` gegen die Referenz: Abweichen dürfen nur Firmen mit neuer Erstmeldung zwischen dem
  30.10. und dem 18.11. (einschließlich der sechs Nachlieferungen). Die abweichenden Firmen stehen mit Grund im Bericht.
- (c) Der Entwicklungs-Cache ist byteweise unverändert.

**Urteil (Jakob 24.11.2026): bestanden mit erklärter Ausnahme INTU.** (a) und (c) sind bestanden. (b) ist nur durch
INTU verfehlt; die Ursache liegt nicht in den SEC-Daten, sondern in der Auswahl bei gleichem `filed` (Befund unten).
Nichts wurde nachjustiert.

## Lauf

- `tools/sec_aktualisieren.py`, echter Lauf am 24.11.2026 von 11:13 bis 11:27 Uhr, mit Laufsperre, Git 3f4474a.
- Die einmalige Übernahme des SEC-Caches (6.907 Dateien, ohne Downloads) lief in diesem Werkzeug, nicht erst im
  Abendlauf.
- **CIKs:** 515 (heutige Mitglieder des Betriebsuniversums plus Vorgänger): 514 übernommen, 1 alter Stand, 0 Fehler.
  - Den alten Stand hat Google Inc. (1288776), nur in der SIC-Historie (Beginn 12.02.2010 statt 11.02.2016, Code 7370
    unverändert), wie am 23.11. festgelegt. Die Meldung ging per Telegram hinaus.
- **Neue Erstmeldungen:** 51.392 in 235 CIKs, neueste `filed` 23.11.2026. Davon 7.308 für Okta (1660134, neue CIK ohne
  bisherigen Stand) und 44.084 in 234 bekannten CIKs.
- **Nachgelieferte Einreichungen:** 6 Hinweise, dieselben wie in der Probe: Abbott, Humana, UDR, Johnson Controls,
  Visa, Verisk, je das 10-Q vom 28./29.07.2026.
- **Anfragen:** 1.055 (517 submissions, 515 companyfacts, 23 Köpfe), alle mit Status 200, höchste Rate 5/s.
- 1.364,5 MB übertragen, 2.060,8 MB entpackt; Abruf 807 s, Übernahme 8,4 s.
- `STAND.json`: erfolgreich, `letzter_erfolg` 24.11.2026 10:26 UTC. Der Tageslauf zeigt ab heute „SEC-Stand vom …“.

## (a) Erstmeldungen: bestanden

- Verglichen wurden alle 806 CIKs des Entwicklungs-Caches als Mehrfachmenge über die Prüfspalten (taxonomie, konzept,
  einheit, start, ende, wert, filed, accn, form).
- **Bestand:** 0 CIKs mit geänderter oder fehlender bisheriger Erstmeldung.
- **Neue Zeilen:** 44.084 in 234 CIKs. 1.250 davon haben `filed` vor dem 30.10.; alle gehören zu den sechs gemeldeten
  Nachlieferungen. Es gibt keine andere neue Zeile vor der Grenze.
- Nur im Betrieb: Okta (1660134). Im Betrieb fehlt keine CIK.
- **Nebenbefund:** Die SEC vergibt `frame` (z. B. „CY2025Q3“) je Zeitraum nur an einen Fakt und verschiebt das Feld,
  wenn eine neuere Einreichung denselben Zeitraum meldet. Bei INTU stehen deshalb 131 Zeilen zweier alter Einreichungen
  im neuen Stand ohne `frame`. `frame` gehört nicht zu den Prüfspalten und geht in keine Rechnung ein
  (`daten/sec.py`, nur gespeichert).

## (c) Entwicklungs-Cache: bestanden

- SHA-256 jeder Datei unter `daten/cache` vor und nach dem Lauf: 16.194 Dateien (0,71 GB).
- 0 neu, 0 entfernt, 0 mit anderem Inhalt, 0 mit anderem Änderungszeitpunkt.

## (b) Bewertung am 18.11.2026: verfehlt durch INTU, sonst erklärt

**Rechnung:**
- `tools/bewertung_vergleich.py --sec-betrieb` (neuer Schalter, mit Test): eingefrorene Eingaben der Referenz vom
  18.11.2026 (Git 6e4ff8a), versiegelt und ohne Netz.
- Nur die 3.376 eingefrorenen SEC-Dateien werden durch die Dateien des neuen Betriebs-Caches ersetzt.
- Ergebnis: 143 von 397 Firmen weichen ab. Keine kommt hinzu, keine fällt weg.

**142 Firmen** haben eine neue Erstmeldung mit `filed` zwischen dem 30.10. und dem 17.11.2026; Abbott, Visa, Verisk und
Johnson Controls zusätzlich die Nachlieferung vom Juli. Grund der Abweichung:

- **Marktwert und Multiples (126 Firmen):** neue Aktienzahl aus dem 10-Q bzw. 10-K, dadurch ändern sich Marktwert,
  E/P, EBIT/EV und teils Altman Z. ABBV, ABNB, ABT, ADM, AES, AKAM, ALB, ALGN, AMCR, AMD, AME, AMGN, ANET, APA, APP,
  APTV, AVY, AXON, BALL, BKNG, BR, BSX, CAH, CAT, CDW, CF, CHTR, CMI, COHR, COP, CPAY, CRL, CSCO, CVS, CVX, DD, DDOG,
  DVN, ECHO, ED, EL, EOG, ETN, EW, EXPD, EXPE, FANG, FCX, FIS, FISV, FOX, GNRC, GPN, GWW, HSIC, IDXX, IP, IT, JKHY, KDP,
  KHC, KMB, LDOS, LITE, LYV, MAR, MCD, MCHP, MCK, MLM, MNST, MOS, MPC, MPWR, MRK, MRNA, MSI, MTD, NRG, NUE, NVR, NWSA,
  ODFL, ON, ORLY, OXY, PFE, PH, PKG, PLTR, PNW, PODD, PTC, Q, RL, ROP, RVTY, SMCI, SOLV, STE, SW, SWK, SYY, TECH, TKO,
  TPR, TRGP, TRMB, TSCO, TTWO, UBER, UHS, UPS, VRSK, VRTX, VST, VTRS, WAT, WYNN, XOM, XYZ, YUM, ZBH, ZBRA, ZTS
  (INTU steht in dieser Gruppe, gehört aber nicht dazu, siehe unten).
- **Abschluss oder Piotroski (15 Firmen):** neues 10-K bzw. neue Quartals- oder Vorjahreswerte. AAPL, ATO, CLX, DIS,
  EMR, FFIV, FICO, JCI, QCOM, ROK, SBUX, SWKS, TEL, TSN, V.
- **Ausschlussgründe (2 Firmen), beide bleiben ausgeschlossen:**
  - TDG: 10-K vom 10.11.2026; Altman Z 1,79 → 1,75, Piotroski 4 → 6.
  - IFF: 10-Q vom 03.11.2026; Altman Z 1,35 → 1,33.
- **Ranglisten am 18.11.:**
  - A, Top 20: rein FICO und TEL, raus ADBE und HSIC.
  - B, Top 20: rein ADI, SBUX, TEL und TKO, raus BMY, DVA, WDAY und WMT.
  - Ohne Wirkung auf die Bücher vor dem Quartalsstichtag 04.01.2027; dazwischen gibt es nur Nachkäufe mit den
    Gewichten vom 06.11.

**Ausnahme INTU (896878):** keine neue Erstmeldung zwischen dem 30.10. und dem 18.11.; der alte Marktwert steigt um den
Faktor 1,004296 (83,709 → 84,069 Mrd. USD), E/P und EBIT/EV ändern sich entsprechend.
- **Ursache:** Das 10-K vom 09.09.2026 (0000896878-26-000037) meldet zwei Aktienzahlen mit demselben `filed`:
  - `CommonStockSharesOutstanding` 268.384.000, Stichtag 31.07.2026,
  - `EntityCommonStockSharesOutstanding` 267.236.000, Stichtag 31.08.2026.

  Ihr Verhältnis ist genau 1,004296. Welche als „zuletzt bekannt“ gilt, entscheidet bei gleichem `filed` die
  Zeilenfolge in der Datei. Im neuen Stand steht die Zeile von `CommonStockSharesOutstanding` an anderer Stelle (2275
  statt 2252), weil neue Einreichungen dazugekommen sind.
- Die SEC-Daten selbst sind gleich; die Abweichung entsteht im Code.
- Die genaue Stelle, die Tragweite im Entwicklungs-Cache und eine deterministische Regel werden getrennt untersucht
  (Auftrag Jakob 24.11.2026). Die Änderung kommt als Datenkorrektur mit Zusage vor dem c3-Neulauf am 01.12.2026.

## Nicht Teil dieses Laufs

- **B3** (versiegelter Vergleich mit Begrenzung auf `filed` ≤ 01.11.2026): nicht gerechnet. Jakob hat für diesen Lauf
  die Kriterien (a) bis (c) festgelegt; (a) deckt den Bestand ab.
- **B6** Erfolgs-Ping: kommt mit Schritt 4 (Healthchecks). Die Probe davor lief am 23.11.2026 (Abnahme A3, Schritt 2).
- **B7:** Der Tageslauf zeigt den SEC-Stand ab dem 24.11.2026 abends. Die Liste „älter als 120 Tage“ und die Zahl der
  veralteten Firmen erscheinen nur an Tagen mit Fundamental-Bewertung.
