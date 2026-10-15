"""Pose verification helpers built on fit evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from MateCore.MateFit.descriptors import FaceDescriptor
from MateCore.MateFit.pose import Pose, measure

from .fits import FitResolver, FitResult


@dataclass(frozen=True, slots=True)
class FitAssessment:
    fits: tuple[FitResult, ...]
    ok: bool
    residual: float


def assess_pairs(
    pairs: list[tuple[FaceDescriptor, FaceDescriptor]],
    resolver: FitResolver,
    pose: Pose,
) -> FitAssessment:
    fits: list[FitResult] = []
    residual = 0.0
    for sel, cand in pairs:
        result = resolver.evaluate(sel, cand, measure(sel, cand, pose))
        fits.append(result)
        residual = max(residual, result.residual)
    ok = all(f.ok for f in fits)
    return FitAssessment(tuple(fits), ok, residual)
