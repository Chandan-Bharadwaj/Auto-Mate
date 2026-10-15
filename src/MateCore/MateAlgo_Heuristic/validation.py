"""Post-alignment pose and fit validation modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from MateCore.MateFit.descriptors import FaceDescriptor
from MateCore.MateFit.pose import Pose, solve_poses
from MateCore.MateFit.assessment import FitAssessment, assess_pairs

from MateCore.trace import MODULE_HEURISTIC, TRACE_VERBOSE, trace_at_least, trace_emit

from .config import HeuristicMateConfig, ValidationMode


@dataclass(frozen=True, slots=True)
class PoseFitOutcome:
    accepted: bool
    pose: Pose | None
    assessment: FitAssessment | None
    warnings: tuple[str, ...] = ()


def _mode(config: HeuristicMateConfig) -> ValidationMode:
    if config.pose_validation == "skip" or config.fit_validation == "skip":
        return "skip"
    if config.pose_validation == "warn" or config.fit_validation == "warn":
        return "warn"
    return "strict"


def evaluate_pose_and_fit(
    pairs_desc: Sequence[tuple[FaceDescriptor, FaceDescriptor]],
    resolver,
    config: HeuristicMateConfig,
    *,
    log_context: str | None = None,
) -> list[PoseFitOutcome]:
    mode = _mode(config)
    verbose = trace_at_least(MODULE_HEURISTIC, TRACE_VERBOSE)
    prefix = log_context or "pose_fit"
    if mode == "skip":
        if verbose:
            trace_emit(
                MODULE_HEURISTIC,
                f"{prefix} accept skip validation",
                min_level=TRACE_VERBOSE,
            )
        return [
            PoseFitOutcome(True, None, None, ("pose_validation=skip",))
        ]

    outcomes: list[PoseFitOutcome] = []
    for pose_index, pose in enumerate(solve_poses(list(pairs_desc), resolver), start=1):
        assessment = assess_pairs(list(pairs_desc), resolver, pose)
        if assessment.ok:
            if verbose:
                trace_emit(
                    MODULE_HEURISTIC,
                    f"{prefix} pose#{pose_index} accept dof={pose.dof}",
                    min_level=TRACE_VERBOSE,
                )
            outcomes.append(PoseFitOutcome(True, pose, assessment, ()))
            continue
        if mode == "warn":
            if verbose:
                trace_emit(
                    MODULE_HEURISTIC,
                    f"{prefix} pose#{pose_index} warn-accept failed tolerance",
                    min_level=TRACE_VERBOSE,
                )
            outcomes.append(
                PoseFitOutcome(
                    True,
                    pose,
                    assessment,
                    ("fit_validation=warn: pose kept despite failed tolerance",),
                )
            )
        else:
            if verbose:
                trace_emit(
                    MODULE_HEURISTIC,
                    f"{prefix} pose#{pose_index} reject failed tolerance",
                    min_level=TRACE_VERBOSE,
                )
            outcomes.append(PoseFitOutcome(False, pose, assessment, ()))
    return outcomes
