"""Regression: AAGNode construction from mocked Part faces (no FreeCAD)."""

from __future__ import annotations

import numpy as np

from App_FreeCAD.aag_build import _node_from_ref
from MateCore.context import SurfaceRef


class _Vec:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x, self.y, self.z = x, y, z


class _BBox:
    XMin, YMin, ZMin = 0.0, 0.0, 0.0
    XMax, YMax, ZMax = 10.0, 10.0, 10.0


def _mock_face(surface: object, *, area: float = 1.0) -> object:
    class Face:
        ParameterRange = (0.0, 1.0, 0.0, 1.0)
        Area = area
        BoundBox = _BBox()
        Surface = surface

        @staticmethod
        def valueAt(u: float, v: float) -> _Vec:
            return _Vec(1.0, 0.0, 0.0)

        @staticmethod
        def normalAt(u: float, v: float) -> _Vec:
            return _Vec(0.0, 0.0, 1.0)

    return Face()


class Plane:
    pass


class Cylinder:
    Axis = _Vec(0.0, 0.0, 1.0)
    Center = _Vec(0.0, 0.0, 0.0)
    Radius = 5.0


class BSpline:
    pass


class BSplineSurface:
    pass


class Sphere:
    Center = _Vec(2.0, 0.0, 0.0)
    Radius = 7.0


class Toroid:
    Center = _Vec(0.0, 1.0, 0.0)
    Axis = _Vec(0.0, 0.0, 1.0)
    MajorRadius = 12.0
    MinorRadius = 2.0


class Cone:
    Axis = _Vec(0.0, 0.0, 1.0)
    Apex = _Vec(0.0, 0.0, 10.0)
    Radius = 3.5
    SemiAngle = 0.12


def _ref(shape: object) -> SurfaceRef:
    return SurfaceRef("Part", "Part", "Face7", shape, None, part_id="Part")


def test_node_from_ref_cylinder_analytic_fields():
    node = _node_from_ref(_ref(_mock_face(Cylinder())))
    assert node.surface_kind == "cylinder"
    assert node.radius == 5.0
    np.testing.assert_allclose(node.origin, [0.0, 0.0, 0.0])
    np.testing.assert_allclose(node.axis, [0.0, 0.0, 1.0])


def test_node_from_ref_plane():
    node = _node_from_ref(_ref(_mock_face(Plane())))
    assert node.surface_kind == "plane"
    np.testing.assert_allclose(node.origin, [1.0, 0.0, 0.0])


def test_node_from_ref_cone_uses_radius_property():
    node = _node_from_ref(_ref(_mock_face(Cone())))
    assert node.surface_kind == "cone"
    assert node.radius == 3.5
    assert node.semi_angle == 0.12
    np.testing.assert_allclose(node.origin, [0.0, 0.0, 10.0])


class RectangularTrimmedSurface:
    BasisSurface = Cone()


def test_node_from_ref_trimmed_cone_surface():
    node = _node_from_ref(_ref(_mock_face(RectangularTrimmedSurface())))
    assert node.surface_kind == "cone"
    assert node.semi_angle == 0.12
    assert node.radius == 3.5
    assert node.surface_kind != "freeform"


def test_node_from_ref_freeform_path():
    node = _node_from_ref(_ref(_mock_face(BSpline())))
    assert node.surface_kind == "freeform"
    assert len(node.normal_samples) == 4
    assert node.bbox_diag > 0.0


def test_node_from_ref_bspline_surface_class_name():
    node = _node_from_ref(_ref(_mock_face(BSplineSurface())))
    assert node.surface_kind == "freeform"


def test_node_from_ref_sphere():
    node = _node_from_ref(_ref(_mock_face(Sphere())))
    assert node.surface_kind == "sphere"
    assert node.radius == 7.0
    np.testing.assert_allclose(node.origin, [2.0, 0.0, 0.0])


def test_node_from_ref_toroid_uses_center():
    node = _node_from_ref(_ref(_mock_face(Toroid())))
    assert node.surface_kind == "torus"
    assert node.radius == 12.0
    assert node.secondary_radius == 2.0
    np.testing.assert_allclose(node.origin, [0.0, 1.0, 0.0])
