"""Shared match payload with surface pairings and pose metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from MateCore.algorithm import Match
from MateCore.context import SurfaceRef
from MateCore.MateFit.fits import FitResult


@dataclass(frozen=True, slots=True)
class MateMatch(Match):
    """Faces on a candidate part that mate with the selection, with pair detail."""

    pairs: tuple[tuple[tuple[SurfaceRef, ...], tuple[SurfaceRef, ...]], ...] = ()
    rotation: tuple[tuple[float, ...], ...] = ()
    translation: tuple[float, ...] = ()
    dof: int = 0
    fits: tuple[FitResult, ...] = field(default=())
