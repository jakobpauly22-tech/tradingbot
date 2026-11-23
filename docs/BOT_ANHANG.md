# Bot-Anhang: Schnittstelle zum Tagesbriefing

Das Tagesbriefing läuft als geplante Aufgaben in Claude und speichert jeden Lauf als Block in Jakobs Briefing-Seite. Montag bis Freitag gibt es seit 12.11.2026 drei Läufe (07:00, 15:00, 21:00 Uhr; einen Lauf um 22 Uhr gibt es nicht mehr, zuvor 7, 12, 19 und 22 Uhr). Am Wochenende gibt es seit 21.11.2026 nur noch ein Briefing um 10:00 Uhr (zuvor ab 12.11. wie an Werktagen 07/15/21 Uhr, davor 12 und 22 Uhr). Die geplante Aufgabe „Briefing-Export Bot-Anhang“ fasst die Blöcke eines Tages täglich um 21:41 (seit 12.11.2026, zuvor 22:40) zu einer Datei zusammen, auch Samstag und Sonntag.

- **Ablage:** Google Drive, `TradingBot/Briefing-Archiv/JJJJ-MM-TT.json`; lokal `daten/briefings/` (nicht in Git).
- **Nachholen:** Verpasste Tage holt die Aufgabe bis zu 3 Tage rückwirkend nach. Bestehende Dateien werden nie überschrieben.
- **Übernahme:** `python tools/briefing_uebernehmen.py` (Ablauf siehe unten).
- **Prüfung:** `python tools/pruefe_bot_anhang.py daten/briefings` prüft alle Dateien gegen das Schema (die Übernahme ruft dieselbe Prüfung auf).

## Schema 1.1

```json
{
  "schema_version": "1.1",
  "datum": "JJJJ-MM-TT",
  "erstellt_um": "2026-11-02T22:40:12+01:00",
  "bloecke": ["2026-11-02_0700", "2026-11-02_1200"],
  "nachrichten": [
    {
      "titel": "kurze Beschreibung, höchstens 15 Wörter",
      "anlage": "z.B. Aktie Nvidia, Halbleiter, DAX, Staatsanleihen USA, Gold, EUR/USD",
      "ticker": "NVDA oder null",
      "region": "USA | Eurozone | Deutschland | UK | China | Japan | Schwellenländer | Welt",
      "ereignistyp": "Earnings | M&A | Zinsentscheid | Konjunkturdaten | Regulierung | Politik | Rohstoffe | Sonstiges",
      "richtung": "positiv | negativ | neutral",
      "staerke": 1,
      "wirkungsdauer": "Tage | Wochen | Monate",
      "quelle": "https://… oder null",
      "quellen": ["Newsletter-Namen wie im Briefing"],
      "block_id": "2026-11-02_1200",
      "item_key": "s0-i2",
      "story_id": "verfolgte Story oder null"
    }
  ],
  "makro_kalender": [
    {"datum": "JJJJ-MM-TT", "ereignis": "Beschreibung", "region": "USA", "bedeutung": 3}
  ]
}
```

## Regeln

| Feld | Regel |
| --- | --- |
| `nachrichten` | nur marktrelevante Entwicklungen; Wiederholungen eines Tages zu einem Eintrag zusammengefasst |
| `richtung` | aus Sicht der betroffenen Anlage (steigende Renditen sind negativ für Anleihen) |
| `staerke`, `bedeutung` | 1 gering, 2 deutlich, 3 hoch (bewegt Index, Sektor oder Megacap; Notenbankentscheid) |
| `ereignistyp` | `Zinsentscheid` = Notenbankentscheid oder Signale von Notenbankern zum Zinspfad; Datenveröffentlichungen sind `Konjunkturdaten` |
| `ticker` | nur wenn eindeutig, sonst `null`; Kürzel ohne Börsenzusatz |
| `quelle` | erste passende Artikel-URL aus dem Briefing, sonst `null`; `quellen` nennt immer die Newsletter |
| `item_key` | `s<Abschnitt>-i<Eintrag>`, bei Sammelmeldungen `-b<Punkt>`, bei Quartalszahlen `e<Index>` |
| `makro_kalender` | datierte Termine der 7 Folgetage, nur mit einem Datum aus einer Quelle |
| allgemein | keine Kursprognosen, keine Kauf- oder Verkaufsempfehlungen |

## Übernahme und Prüfung (seit 23.11.2026)

`tools/briefing_uebernehmen.py` ist ein eigenes Werkzeug und nicht Teil des Tagesablaufs; der Abendlauf bleibt unverändert. Pfade stehen in `config/briefing.yaml` (`quelle` = lokal gespiegelter Drive-Ordner `G:\Meine Ablage\TradingBot\Briefing-Archiv`, `ablage` = `daten/briefings/`).

1. **Kopieren:** Neue Dateien werden nach `daten/briefings/` kopiert. Eine vorhandene Datei wird nur überschrieben, wenn sich die SHA-256-Prüfsumme geändert hat; das wird mit altem und neuem `erstellt_um` gemeldet. Drive wird nur gelesen, nie beschrieben oder gelöscht. `--ohne-kopie` prüft nur die Ablage.
2. **Prüfen** (`pruefe_datei` in `tools/pruefe_bot_anhang.py`), Ergebnis je Datei:
   - **ungültig:** nicht lesbares JSON, Pflichtfeld fehlt, Wert außerhalb der Aufzählungen (`region`, `ereignistyp`, `richtung`, `wirkungsdauer`), `staerke`/`bedeutung` nicht 1–3, `schema_version` ≠ 1.1, Termin außerhalb der 7 Folgetage, Dateiname ≠ `JJJJ-MM-TT.json` oder ≠ `datum` im Inhalt, `erstellt_um` vor dem Datum. Ungültige Dateien werden trotzdem kopiert, aber in der Übersicht markiert; sie dürfen nicht in die News-Engine.
   - **Warnung:** Datei nutzbar, aber auffällig: `erstellt_um` mehr als 1 Tag nach dem Datum (nachgeholt), keine Nachrichten, kein Makro-Kalender, doppelter `item_key` im selben Block, bekannte `quelle`-Einschränkung (Dateien bis 30.10.2026).
   - **gültig:** sonst.
3. **Lücken:** Tage ohne Datei von der ersten Datei bis gestern (Wochenende zählt mit); der heutige Tag gilt erst ab 21:41 als fällig. Die Aufgabe holt bis zu 3 Tage nach, ältere Lücken bleiben und werden nur gemeldet.

## Nutzung im Bot

- **Look-ahead-Schutz:** Eine Datei darf im Backtest erst ab `erstellt_um` verwendet werden.
- **Rolle:** Kontext und Risikofilter, kein Kaufauslöser. Der Makro-Kalender bremst neue oder große Positionen vor wichtigen Terminen.
- **Bekannte Einschränkung:** In den Dateien vom 28. bis 30.10.2026 ist `quelle` bei Einträgen aus Sammelmeldungen (`item_key` mit `-b`) teils falsch. Ab 31.10.2026 ist das korrigiert.
