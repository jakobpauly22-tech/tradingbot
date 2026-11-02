@echo off
rem Tageslauf und Freigabe des Paper Tradings (abends 18-24 Uhr). Doppelklick genügt; kein Terminal nötig.
rem Das IB Gateway muss für Abgleich und Senden laufen (Paper-Konto, Port 4002).
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "tools\tageslauf.py"
