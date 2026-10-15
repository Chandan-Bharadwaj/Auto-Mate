"""FreeCAD surface accessor compatibility (no FreeCAD runtime)."""

from __future__ import annotations

import numpy as np
import pytest

from App_FreeCAD.fc_surface import (
    aag_surface_kind,
    aag_surface_kind_from_surface,
    fc_analytic_surface,
    fc_cone_ref_radius,
    fc_cone_semi_angle,
    fc_torus_origin,
    fc_torus_radii,
    fc_vector,
)


class _Vec:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = x, y, z


def test_aag_surface_kind_maps_bezier_surface():
    assert aag_surface_kind("BSplineSurface") == "freeform"
    assert aag_surface_kind("BezierSurface") == "freeform"
    assert aag_surface_kind("Toroid") == "torus"


def test_cone_radius_property_not_method():
    class Cone:
        Radius = 2.5

    assert fc_cone_ref_radius(Cone()) == 2.5


def test_cone_semi_angle_property():
    class Cone:
        SemiAngle = 0.15

    assert fc_cone_semi_angle(Cone()) == 0.15


def test_cone_semi_angle_degrees_heuristic():
    class Cone:
        SemiAngle = 15.0

    assert fc_cone_semi_angle(Cone()) == pytest.approx(np.radians(15.0))


def test_analytic_surface_unwraps_trimmed_cone():
    class Cone:
        pass

    class RectangularTrimmedSurface:
        BasisSurface = Cone()

    assert type(fc_analytic_surface(RectangularTrimmedSurface())).__name__ == "Cone"
    assert aag_surface_kind_from_surface(RectangularTrimmedSurface()) == "cone"


def test_cone_ref_radius_callable_fallback():
    class Cone:
        def RefRadius(self) -> float:
            return 4.0

    assert fc_cone_ref_radius(Cone()) == 4.0


def test_torus_uses_center_not_location():
    class Toroid:
        Center = _Vec(1.0, 2.0, 3.0)
        MajorRadius = 10.0
        MinorRadius = 1.0

    np.testing.assert_allclose(fc_torus_origin(Toroid()), [1.0, 2.0, 3.0])
    assert fc_torus_radii(Toroid()) == (10.0, 1.0)


def test_vector_first_matching_attribute():
    class S:
        Location = _Vec(0.0, 0.0, 0.0)
        Center = _Vec(5.0, 0.0, 0.0)

    np.testing.assert_allclose(fc_vector(S(), "Center", "Location"), [5.0, 0.0, 0.0])


def test_vector_missing_raises():
    with pytest.raises(AttributeError):
        fc_vector(object(), "Axis")
