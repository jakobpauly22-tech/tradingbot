# Bot-Anhang: Schnittstelle zum Tagesbriefing

Das Tagesbriefing läuft als zwei geplante Aufgaben in Claude („Newsletter-Briefing“ Mo–Fr um 7, 12, 19 und 22 Uhr, „Briefing Wochenende“ um 12 und 22 Uhr) und speichert jeden Lauf als Block in Jakobs Briefing-Seite. Die geplante Aufgabe „Briefing-Export Bot-Anhang“ fasst die Blöcke eines Tages täglich um 22:40 zu einer Datei zusammen.

- **Ablage:** Google Drive, `TradingBot/Briefing-Archiv/JJJJ-MM-TT.json`; lokal `daten/briefings/` (nicht in Git).
- **Nachholen:** Verpasste Tage holt die Aufgabe bis zu 3 Tage rückwirkend nach. Bestehende Dateien werden nie überschrieben.
- **Prüfung:** `python tools/pruefe_bot_anhang.py daten/briefings` prüft alle Dateien gegen das Schema.

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

## Nutzung im Bot

- **Look-ahead-Schutz:** Eine Datei darf im Backtest erst ab `erstellt_um` verwendet werden.
- **Rolle:** Kontext und Risikofilter, kein Kaufauslöser. Der Makro-Kalender bremst neue oder große Positionen vor wichtigen Terminen.
- **Bekannte Einschränkung:** In den Dateien vom 28. bis 30.10.2026 ist `quelle` bei Einträgen aus Sammelmeldungen (`item_key` mit `-b`) teils falsch. Ab 31.10.2026 ist das korrigiert.
