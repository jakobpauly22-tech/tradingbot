"""Testsperre für echte Zugänge (Jakob 24.11.2026): Umsetzung in tests/_testsperre.py, beim Import aktiv."""
import pytest

import _testsperre as sperre


@pytest.fixture(autouse=True)
def _zugaenge_gesperrt(request):
    """Vor jedem Test: Zugänge aus der Umgebung entfernen (auch wenn ein früherer Test sie gesetzt hat)."""
    sperre._ZUSTAND["netz"] = request.node.get_closest_marker("netz") is not None
    sperre.entfernen()
    yield
    sperre.entfernen()
