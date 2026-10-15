"""Heuristic fit resolver and mate fit summary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from MateCore.MateFit.configuration import MateConfigurationKind, classify_configuration
from MateCore.MateFit.fits import (
    FitPolicy,
    FitResolver,
    FitResult,
    clearance_fit,
)
from MateCore.MateGraph.search.pattern import GraphPattern

from .axis_alignment import AxisAlignmentMeasure
from .config import HeuristicMateConfig


def pattern_has_cylinder_slots(pattern: GraphPattern | None) -> bool:
    if pattern is None:
        return False
    return any(s.surface_kind == "cylinder" for s in pattern.slots)


def clearance_policy_active(
    mate_cfg: HeuristicMateConfig,
    axis_alignment: AxisAlignmentMeasure,
    pattern: GraphPattern | None,
) -> bool:
    gap = mate_cfg.nominal_fit_gap_mm
    if gap is None or gap <= 0.0:
        return False
    return axis_alignment.axis_aligned or pattern_has_cylinder_slots(pattern)


def build_heuristic_fit_resolver(
    mate_cfg: HeuristicMateConfig,
    axis_alignment: AxisAlignmentMeasure,
    base_resolver: FitResolver,
    pattern: GraphPattern | None = None,
) -> FitResolver:
    if not clearance_policy_active(mate_cfg, axis_alignment, pattern):
        return base_resolver
    gap = float(mate_cfg.nominal_fit_gap_mm)
    tol = base_resolver.policy.default.tolerance
    fit = clearance_fit(0.0, gap, tol)
    return FitResolver(FitPolicy(fit))


def effective_nominal_gap_mm(
    mate_cfg: HeuristicMateConfig,
    axis_alignment: AxisAlignmentMeasure,
    pattern: GraphPattern | None = None,
) -> float | None:
    if not clearance_policy_active(mate_cfg, axis_alignment, pattern):
        return None
    return mate_cfg.nominal_fit_gap_mm


@dataclass(frozen=True, slots=True)
class MateFitSummary:
    configuration_kind: MateConfigurationKind | None
    axis_aligned: bool
    nominal_gap_mm: float | None
    per_pair: tuple[FitResult, ...]


def summarize_mate_fit(
    axis_alignment: AxisAlignmentMeasure,
    mate_cfg: HeuristicMateConfig,
    fits: Sequence[FitResult],
    pattern: GraphPattern | None = None,
) -> MateFitSummary:
    return MateFitSummary(
        configuration_kind=classify_configuration(fits),
        axis_aligned=axis_alignment.axis_aligned,
        nominal_gap_mm=effective_nominal_gap_mm(mate_cfg, axis_alignment, pattern),
        per_pair=tuple(fits),
    )
