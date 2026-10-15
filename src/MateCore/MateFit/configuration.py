"""Mate configuration rollup from per-pair fit results."""

from __future__ import annotations

from enum import Enum
from typing import Sequence

from .fits import FitResult


class MateConfigurationKind(str, Enum):
    EXACT_FIT = "exact_fit"
    CLEARANCE_FIT = "clearance_fit"
    INTERFERENCE = "interference"
    REJECTED = "rejected"


def classify_configuration(fits: Sequence[FitResult]) -> MateConfigurationKind | None:
    if not fits:
        return None
    if not all(f.ok for f in fits):
        if any(f.fit_class == "interference" for f in fits):
            return MateConfigurationKind.INTERFERENCE
        return MateConfigurationKind.REJECTED
    if all(f.fit_class == "exact" for f in fits):
        return MateConfigurationKind.EXACT_FIT
    if all(f.fit_class in ("exact", "clearance") for f in fits) and not any(
        f.fit_class == "exact" for f in fits
    ):
        return MateConfigurationKind.CLEARANCE_FIT
    return MateConfigurationKind.CLEARANCE_FIT
