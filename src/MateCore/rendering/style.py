"""Tweakable look of result rendering. Edit DEFAULT_STYLE or set preferences."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

Color = tuple[float, float, float]

BRIGHT_GREEN: Color = (0.15, 1.00, 0.25)

BRIGHT_PALETTE: tuple[Color, ...] = (
    (1.00, 0.10, 0.10),  # red
    (0.10, 0.85, 0.20),  # green
    (0.10, 0.45, 1.00),  # blue
    (1.00, 0.85, 0.00),  # yellow
    (1.00, 0.20, 0.90),  # magenta
    (0.00, 0.90, 0.90),  # cyan
    (1.00, 0.55, 0.00),  # orange
)

@dataclass(frozen=True, slots=True)
class RenderStyle:
    palette: tuple[Color, ...] = BRIGHT_PALETTE
    highlight_color: Color = BRIGHT_GREEN
    # Matched surfaces: brightness multiplier (clamped to 1.0) and 0-100 transparency.
    surface_brightness: float = 1.0
    surface_transparency: int = 0
    # Parts owning matched surfaces: 0-100 transparency; optional flat tint.
    part_transparency: int = 70
    part_tint: Color | None = BRIGHT_GREEN
    # Mesh deviation used to tessellate overlay faces.
    tessellation_tolerance: float = 0.1

    def __post_init__(self) -> None:
        if not self.palette:
            raise ValueError("palette must not be empty")
        for name in ("surface_transparency", "part_transparency"):
            if not 0 <= getattr(self, name) <= 100:
                raise ValueError(f"{name} must be within 0..100")
        if self.surface_brightness <= 0 or self.tessellation_tolerance <= 0:
            raise ValueError("surface_brightness and tessellation_tolerance must be > 0")


DEFAULT_STYLE = RenderStyle()

_OVERRIDABLE = {
    "surface_brightness": float,
    "surface_transparency": int,
    "part_transparency": int,
    "tessellation_tolerance": float,
}


def brighten(color: Color, factor: float) -> Color:
    return tuple(min(1.0, max(0.0, c * factor)) for c in color)  # type: ignore[return-value]


def style_from_mapping(values: Mapping[str, Any], base: RenderStyle = DEFAULT_STYLE) -> RenderStyle:
    """Apply scalar overrides; unknown or invalid entries are ignored."""
    changes: dict[str, Any] = {}
    for name, cast in _OVERRIDABLE.items():
        if name in values:
            try:
                changes[name] = cast(values[name])
            except (TypeError, ValueError):
                continue
    try:
        return replace(base, **changes)
    except ValueError:
        return base
