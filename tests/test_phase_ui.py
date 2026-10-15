from pathlib import Path

from App_FreeCAD.phase_ui import PHASE_PRESENTATION, CommandPhase


def test_every_phase_has_a_distinct_existing_icon():
    assert set(PHASE_PRESENTATION) == set(CommandPhase)
    icons = [p.icon for p in PHASE_PRESENTATION.values()]
    assert len(set(icons)) == len(CommandPhase)
    assert all(Path(icon).is_file() for icon in icons)
