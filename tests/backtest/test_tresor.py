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
