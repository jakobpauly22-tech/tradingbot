import pytest

from tradingbot.backtest.tresor import TresorFreigabe, TresorGesperrt, geoeffnete_phasen, oeffne_tresor, pruefe_zeitraum


def test_entwicklungsdaten_frei(konfig):
    pruefe_zeitraum("2024-12-31", konfig=konfig)


def test_gesperrte_daten_ohne_freigabe(konfig):
    with pytest.raises(TresorGesperrt, match="ab 2025-01-01 sind gesperrt"):
        pruefe_zeitraum("2025-01-01", konfig=konfig)


def test_selbstgebaute_freigabe_gilt_nicht(konfig):
    with pytest.raises(TresorGesperrt, match="nicht im Tresor-Protokoll"):
        pruefe_zeitraum("2026-06-30", freigabe=TresorFreigabe("Phase 1", "geschummelt"), konfig=konfig)


def test_einmal_pro_phase(konfig, tmp_path):
    freigabe = oeffne_tresor("Phase 1", "Regeln und Parameter fix", konfig=konfig)
    pruefe_zeitraum("2026-06-30", freigabe=freigabe, konfig=konfig)
    assert geoeffnete_phasen(tmp_path / "TRESOR_PROTOKOLL.md") == {"Phase 1"}

    with pytest.raises(TresorGesperrt, match="verbraucht"):
        oeffne_tresor("Phase 1", "noch ein Versuch nach Anpassung", konfig=konfig)
    oeffne_tresor("Phase 2", "neue Phase", konfig=konfig)
    assert geoeffnete_phasen(tmp_path / "TRESOR_PROTOKOLL.md") == {"Phase 1", "Phase 2"}


def test_echtes_protokoll_mit_verweis_ist_keine_oeffnung(konfig, tmp_path):
    """docs/TRESOR_PROTOKOLL.md (angelegt 16.11.2026) enthält nur Kopf und Verweis auf docs/TRESOR_BEKANNT.md: keine
    geöffnete Phase. Eine spätere Öffnung hängt ihre Zeile an die Tabelle an."""
    import shutil
    from pathlib import Path

    echt = Path(__file__).resolve().parents[2] / "docs" / "TRESOR_PROTOKOLL.md"
    assert geoeffnete_phasen(echt) == set()
    assert "TRESOR_BEKANNT.md" in echt.read_text(encoding="utf-8")
    shutil.copy(echt, tmp_path / "TRESOR_PROTOKOLL.md")
    oeffne_tresor("Phase X", "Test", konfig=konfig)
    assert geoeffnete_phasen(tmp_path / "TRESOR_PROTOKOLL.md") == {"Phase X"}
    assert (tmp_path / "TRESOR_PROTOKOLL.md").read_text(encoding="utf-8").rstrip().splitlines()[-1].startswith("| ")
