"""Statuszeile fuer Claude Code: Wochen- und 5-Stunden-Nutzung, Kontext.

Ampel fuer die Wochennutzung (Jakobs Regel vom 09.11.2026):
  unter 60 %  gruen   - normal arbeiten
  60-79 %     gelb    - nur noch Wichtiges
  ab 80 %     rot     - STOPP Bot-Entwicklung, Rest der Woche fuer die Uni
Claude Code uebergibt die Daten als JSON auf stdin (rate_limits nur bei Pro/Max).
"""
import json
import sys
from datetime import datetime

GRENZE_STOPP = 80
GRENZE_WARNUNG = 60
GRUEN, GELB, ROT, AUS = "\033[32m", "\033[33m", "\033[1;31m", "\033[0m"


def zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        daten = json.load(sys.stdin)
    except Exception:
        print("Nutzung: keine Daten")
        return
    teile = []
    limits = daten.get("rate_limits") or {}
    woche = limits.get("seven_day") or {}
    pct = zahl(woche.get("used_percentage"))
    if pct is None:
        teile.append("Woche: noch keine Daten (nach der ersten Antwort)")
    else:
        reset = ""
        if woche.get("resets_at"):
            try:
                zeit = datetime.fromtimestamp(int(woche["resets_at"]))
                tag = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][zeit.weekday()]
                reset = f" | Reset {tag} {zeit:%d.%m. %H:%M}"
            except Exception:
                reset = ""
        if pct >= GRENZE_STOPP:
            teile.append(f"{ROT}Woche {pct:.0f} % - STOPP: Puffer fuer die Uni{reset}{AUS}")
        elif pct >= GRENZE_WARNUNG:
            teile.append(f"{GELB}Woche {pct:.0f} % - nur noch Wichtiges{reset}{AUS}")
        else:
            teile.append(f"{GRUEN}Woche {pct:.0f} %{reset}{AUS}")
    fuenf = zahl((limits.get("five_hour") or {}).get("used_percentage"))
    if fuenf is not None:
        teile.append(f"5h {fuenf:.0f} %")
    kontext = zahl((daten.get("context_window") or {}).get("used_percentage"))
    if kontext is not None:
        hinweis = " - /clear bei neuer Aufgabe" if kontext >= 50 else ""
        teile.append(f"Kontext {kontext:.0f} %{hinweis}")
    print("  |  ".join(teile))


if __name__ == "__main__":
    main()
