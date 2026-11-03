"""Sperre gegen zwei gleichzeitige Tagesläufe bzw. Freigaben auf demselben Journal (Jakob 03.11.2026).

Eine Sperrdatei neben dem Journal wird exklusiv angelegt (O_CREAT | O_EXCL) und beim Ende gelöscht, auch nach einem
Fehler. Sie gilt für die ganze Sitzung: Tageslauf rechnen, Fenster offen, Freigabe und Senden. Existiert sie schon und
lebt der eintragende Prozess noch, bricht der zweite Start mit `LaufGesperrt` ab. Eine Sperre eines beendeten Prozesses
(Absturz) oder eine ältere als `max_alter_stunden` gilt als verwaist, wird übernommen und gemeldet.
"""
from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class LaufGesperrt(RuntimeError):
    """Ein anderer Tageslauf oder eine Freigabe läuft gerade auf demselben Journal."""


def prozess_lebt(pid: int) -> bool:
    """Prüft, ob ein Prozess läuft, ohne ihn zu berühren (Windows: OpenProcess/GetExitCodeProcess; sonst Signal 0)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)                     # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_aus(inhalt: str) -> int:
    try:
        return int(inhalt.rsplit("Prozess", 1)[1].strip())
    except (IndexError, ValueError):
        return -1


@contextmanager
def laufsperre(datei: Path, *, zweck: str = "Tageslauf", max_alter_stunden: float = 24.0, meldungen: list | None = None):
    datei = Path(datei)
    datei.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    for _ in range(2):
        try:
            fd = os.open(datei, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                inhalt = datei.read_text(encoding="utf-8", errors="replace").strip()
                alter_h = (time.time() - datei.stat().st_mtime) / 3600
            except FileNotFoundError:                                # gerade freigegeben
                continue
            pid = _pid_aus(inhalt)
            if pid != os.getpid() and prozess_lebt(pid) and alter_h <= max_alter_stunden:
                raise LaufGesperrt(f"Es läuft bereits ein Vorgang auf diesem Journal ({inhalt}). Erst das andere Fenster schließen, "
                                   f"dann neu starten. Sperrdatei: {datei}")
            if pid == os.getpid():
                raise LaufGesperrt(f"Dieser Prozess hält die Sperre schon ({inhalt})")
            if meldungen is not None:
                meldungen.append(f"verwaiste Sperre übernommen ({inhalt}; Prozess beendet oder {alter_h:.1f} h alt)")
            datei.unlink(missing_ok=True)
    if fd is None:
        raise LaufGesperrt(f"Sperre konnte nicht angelegt werden: {datei}")
    try:
        os.write(fd, f"{zweck} seit {datetime.now():%d.%m.%Y %H:%M:%S}, Prozess {os.getpid()}".encode("utf-8"))
    finally:
        os.close(fd)
    try:
        yield datei
    finally:
        datei.unlink(missing_ok=True)
