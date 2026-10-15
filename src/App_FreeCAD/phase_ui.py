"""Per-phase presentation (icon, text, tooltip) of the Auto-Mate command."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

ICON_DIR = Path(__file__).resolve().parent / "icons"


class CommandPhase(Enum):
    IDLE = auto()
    SELECTION = auto()
    COMPUTE = auto()
    DISPLAY = auto()


@dataclass(frozen=True)
class PhasePresentation:
    icon: str
    menu_text: str
    tooltip: str


PHASE_PRESENTATION = {
    CommandPhase.IDLE: PhasePresentation(
        str(ICON_DIR / "automate_idle.svg"),
        "Auto-Mate: Select Surfaces",
        "Click to begin selecting faces",
    ),
    CommandPhase.SELECTION: PhasePresentation(
        str(ICON_DIR / "automate_selection.svg"),
        "Auto-Mate: Finish Selection",
        "Selecting faces: click to finish selection and compute",
    ),
    CommandPhase.COMPUTE: PhasePresentation(
        str(ICON_DIR / "automate_compute.svg"),
        "Auto-Mate: Computing",
        "Computing grouped surfaces",
    ),
    CommandPhase.DISPLAY: PhasePresentation(
        str(ICON_DIR / "automate_display.svg"),
        "Auto-Mate: New Run",
        "Results displayed: click to start a new selection",
    ),
}
