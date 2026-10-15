"""Safe accessors for FreeCAD ``Part`` analytic surface bindings.

FreeCAD exposes OCC geometry via SWIG types whose Python names and properties
do not always match raw OCCT (e.g. ``Cone.Radius`` not ``RefRadius()``,
``Toroid.Center`` not ``Location``, ``BSplineSurface`` not ``BSpline``).
This module centralizes those differences so ``aag_build`` stays readable.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from MateCore.MateGraph.model import FREEFORM, OTHER

# Registered in Part/App/AppPart.cpp (FreeCAD 0.19+ / 1.x).
FC_PLANE = "Plane"
FC_CYLINDER = "Cylinder"
FC_CONE = "Cone"
FC_SPHERE = "Sphere"
FC_TOROID = "Toroid"
FC_BEZIER = "BezierSurface"
FC_BSPLINE = "BSplineSurface"

FREEFORM_FC_NAMES = frozenset(
    {
        FC_BEZIER,
        FC_BSPLINE,
        "Bezier",
        "BSpline",
        "PlateSurface",
        "SurfaceOfExtrusion",
        "SurfaceOfRevolution",
    }
)

_SURFACE_WRAPPER_NAMES = frozenset(
    {
        "RectangularTrimmedSurface",
        "OffsetSurface",
    }
)


def fc_surface_class_name(surface: Any) -> str:
    return type(surface).__name__


def fc_analytic_surface(surface: Any, max_depth: int = 8) -> Any:
    """Unwrap trimmed/offset surfaces to underlying analytic geometry (e.g. Cone)."""
    current = surface
    for _ in range(max_depth):
        name = fc_surface_class_name(current)
        if name not in _SURFACE_WRAPPER_NAMES:
            return current
        basis = None
        for attr in ("BasisSurface", "basisSurface"):
            if hasattr(current, attr):
                basis = getattr(current, attr)
                break
        if basis is None:
            return current
        current = basis
    return current


def aag_surface_kind_from_surface(surface: Any) -> str:
    return aag_surface_kind(fc_surface_class_name(fc_analytic_surface(surface)))


def aag_surface_kind(fc_name: str) -> str:
    """Map a FreeCAD surface class name to ``AAGNode.surface_kind``."""
    mapping = {
        FC_PLANE: "plane",
        FC_CYLINDER: "cylinder",
        FC_CONE: "cone",
        FC_SPHERE: "sphere",
        FC_TOROID: "torus",
        FC_BEZIER: FREEFORM,
        FC_BSPLINE: FREEFORM,
        "Bezier": FREEFORM,
        "BSpline": FREEFORM,
    }
    return mapping.get(fc_name, OTHER)


def _vec(v: Any) -> np.ndarray:
    return np.array([v.x, v.y, v.z], dtype=float)


def fc_vector(surface: Any, *attr_names: str) -> np.ndarray:
    for name in attr_names:
        if hasattr(surface, name):
            return _vec(getattr(surface, name))
    raise AttributeError(
        f"{fc_surface_class_name(surface)!r} has none of {attr_names!r}"
    )


def fc_float(surface: Any, *attr_names: str, default: float = 0.0) -> float:
    for name in attr_names:
        if not hasattr(surface, name):
            continue
        value = getattr(surface, name)
        if callable(value):
            try:
                return float(value())
            except TypeError:
                continue
        return float(value)
    return default


def fc_cone_ref_radius(surface: Any) -> float:
    return fc_float(surface, "Radius", "RefRadius", default=0.0)


def fc_cone_semi_angle(surface: Any) -> float:
    angle = fc_float(surface, "SemiAngle", "semiAngle", "Semiangle", default=0.0)
    if angle > 1.0:
        angle = float(np.radians(angle))
    return angle


def fc_torus_radii(surface: Any) -> tuple[float, float]:
    major = fc_float(surface, "MajorRadius", default=0.0)
    minor = fc_float(surface, "MinorRadius", default=0.0)
    return major, minor


def fc_torus_origin(surface: Any) -> np.ndarray:
    return fc_vector(surface, "Center", "Location")
