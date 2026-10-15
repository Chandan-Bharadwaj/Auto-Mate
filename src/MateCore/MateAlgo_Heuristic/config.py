"""Heuristic mate algorithm configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ValidationMode = Literal["strict", "warn", "skip"]
EnricherMode = Literal["selection_only", "one_hop_analytic"]
TopologyProfile = Literal["default", "coarse"]


@dataclass(frozen=True, slots=True)
class HeuristicMateConfig:
    fit_validation: ValidationMode = "strict"
    pose_validation: ValidationMode = "strict"
    enricher: EnricherMode = "selection_only"
    topology_profile: TopologyProfile = "default"
    flank_spacing_rel_tol: float = 0.05
    hub_node_weight: float = 2.0
    nominal_fit_gap_mm: float | None = None
    plane_shape_reject_floor: float = 0.15
    plane_shape_penalty_exponent: float = 2.0
