@echo off
rem Probelauf: eigenes Probe-Journal, jederzeit bedienbar, sendet nie, setzt nie einen Messbeginn.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "tools\tageslauf.py" --probe
