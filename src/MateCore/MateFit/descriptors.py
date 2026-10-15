"""Host-independent numeric face descriptors."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

PLANE = "plane"
CYLINDER = "cylinder"
CONE = "cone"


@dataclass(frozen=True, slots=True, eq=False)
class FaceDescriptor:
    """Analytic face frame.

    plane: ``origin`` is a point on the plane, ``axis`` the OUTWARD unit normal.
    cylinder: ``origin`` is a point on the axis, ``axis`` the unit axis direction
    (sign-free), ``radius`` the radius, ``convex`` True for a shaft/boss surface
    (outward normal pointing away from the axis) and False for a bore.
    cone: ``origin`` at apex, ``axis`` along cone axis, ``radius`` ref radius at
    the reference plane, ``semi_angle`` half-angle from axis to surface (radians).
    """

    id: str
    part_id: str
    kind: str
    origin: np.ndarray
    axis: np.ndarray
    radius: float = 0.0
    semi_angle: float = 0.0
    convex: bool = True
    area: float = 0.0
    plane_aspect: float = 0.0
    ref: Any = None
    adjacent: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if self.kind not in (PLANE, CYLINDER, CONE):
            raise ValueError(f"Unsupported surface kind: {self.kind}")
        if self.kind == CONE and self.semi_angle <= 0.0:
            raise ValueError("cone semi_angle must be positive")
        object.__setattr__(self, "origin", np.asarray(self.origin, dtype=float))
        axis = np.asarray(self.axis, dtype=float)
        norm = float(np.linalg.norm(axis))
        if norm == 0.0:
            raise ValueError("axis must be non-zero")
        object.__setattr__(self, "axis", axis / norm)


def complement(face: FaceDescriptor) -> FaceDescriptor:
    """The surface that mates with ``face`` in place (flipped normal / convexity)."""
    if face.kind == PLANE:
        return replace(face, axis=-face.axis)
    return replace(face, convex=not face.convex)


@dataclass(frozen=True, slots=True, eq=False)
class SurfacePatch:
    """One or more adjacent faces lying on the same analytic surface."""

    descriptor: FaceDescriptor
    members: tuple[FaceDescriptor, ...]

    @property
    def refs(self) -> tuple[Any, ...]:
        return tuple(m.ref for m in self.members)

    @property
    def area(self) -> float:
        return sum(m.area for m in self.members)
