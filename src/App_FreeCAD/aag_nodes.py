"""AAG node construction from FreeCAD Part faces."""

from __future__ import annotations

from typing import Any

import numpy as np

from MateCore.MateGraph.model import (
    FREEFORM,
    OTHER,
    AAGNode,
    NormalSample,
)
from MateCore.context import SurfaceRef

from .fc_surface import (
    FC_CONE,
    FC_CYLINDER,
    FC_PLANE,
    FC_SPHERE,
    FC_TOROID,
    FREEFORM_FC_NAMES,
    aag_surface_kind_from_surface,
    fc_analytic_surface,
    fc_cone_ref_radius,
    fc_cone_semi_angle,
    fc_float,
    fc_surface_class_name,
    fc_torus_origin,
    fc_torus_radii,
    fc_vector,
)


def _vec(v: Any) -> np.ndarray:
    return np.array([v.x, v.y, v.z], dtype=float)


def face_id(ref: SurfaceRef) -> str:
    return f"{ref.object_name}:{ref.face_name}"


def _surface_kind(shape: Any) -> str:
    surface = getattr(shape, "Surface", None)
    if surface is None:
        return OTHER
    return aag_surface_kind_from_surface(surface)


def _node_identity(ref: SurfaceRef, nid: str, area: float) -> dict[str, Any]:
    return {
        "node_id": nid,
        "part_id": ref.part_id,
        "area": area,
        "ref": ref,
        "member_ids": (nid,),
    }


def _bbox_diag(shape: Any) -> float:
    bb = shape.BoundBox
    return float(
        np.linalg.norm([bb.XMax - bb.XMin, bb.YMax - bb.YMin, bb.ZMax - bb.ZMin])
    )


def _plane_bbox_aspect(shape: Any, normal: np.ndarray) -> float:
    """Long/short in-plane extent from the face AABB projected onto the plane."""
    n = normal / max(float(np.linalg.norm(normal)), 1e-12)
    ref = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(ref, n))) > 0.9:
        ref = np.array([0.0, 1.0, 0.0])
    u = np.cross(n, ref)
    u = u / max(float(np.linalg.norm(u)), 1e-12)
    v = np.cross(n, u)
    bb = shape.BoundBox
    corners = (
        (bb.XMin, bb.YMin, bb.ZMin),
        (bb.XMax, bb.YMin, bb.ZMin),
        (bb.XMin, bb.YMax, bb.ZMin),
        (bb.XMax, bb.YMax, bb.ZMin),
        (bb.XMin, bb.YMin, bb.ZMax),
        (bb.XMax, bb.YMin, bb.ZMax),
        (bb.XMin, bb.YMax, bb.ZMax),
        (bb.XMax, bb.YMax, bb.ZMax),
    )
    us: list[float] = []
    vs: list[float] = []
    for cx, cy, cz in corners:
        p = np.array([cx, cy, cz], dtype=float)
        us.append(float(np.dot(p, u)))
        vs.append(float(np.dot(p, v)))
    extent_u = max(us) - min(us)
    extent_v = max(vs) - min(vs)
    short = max(min(extent_u, extent_v), 1e-12)
    long = max(extent_u, extent_v)
    return float(long / short)


def _cone_convex(normal: np.ndarray, axis: np.ndarray, apex: np.ndarray, point: np.ndarray) -> bool:
    ax = axis / max(float(np.linalg.norm(axis)), 1e-12)
    radial = point - apex - float(np.dot(point - apex, ax)) * ax
    if float(np.linalg.norm(radial)) < 1e-12:
        return bool(np.dot(normal, ax) > 0)
    return bool(np.dot(normal, radial) > 0.0)


def node_from_ref(ref: SurfaceRef) -> AAGNode:
    shape = ref.shape
    kind = _surface_kind(shape)
    u0, u1, v0, v1 = shape.ParameterRange
    u, v = 0.5 * (u0 + u1), 0.5 * (v0 + v1)
    point = _vec(shape.valueAt(u, v))
    normal = _vec(shape.normalAt(u, v))
    area = float(shape.Area)
    nid = face_id(ref)
    ident = _node_identity(ref, nid, area)
    surface = shape.Surface
    analytic = fc_analytic_surface(surface)
    stype = fc_surface_class_name(analytic)
    if stype == FC_PLANE:
        return AAGNode(
            **ident,
            surface_kind=kind,
            origin=point,
            axis=normal,
            bbox_diag=_bbox_diag(shape),
            plane_aspect=_plane_bbox_aspect(shape, normal),
        )
    if stype == FC_CYLINDER:
        axis = fc_vector(analytic, "Axis")
        center = fc_vector(analytic, "Center", "Location")
        radial = point - center - np.dot(point - center, axis) * axis
        return AAGNode(
            **ident,
            surface_kind=kind,
            axis=axis,
            origin=center,
            radius=fc_float(analytic, "Radius"),
            convex=bool(np.dot(normal, radial) > 0.0),
        )
    if stype == FC_CONE:
        axis = fc_vector(analytic, "Axis")
        apex = fc_vector(analytic, "Apex")
        return AAGNode(
            **ident,
            surface_kind=kind,
            axis=axis,
            origin=apex,
            radius=fc_cone_ref_radius(analytic),
            semi_angle=fc_cone_semi_angle(analytic),
            convex=_cone_convex(normal, axis, apex, point),
        )
    if stype == FC_SPHERE:
        return AAGNode(
            **ident,
            surface_kind=kind,
            axis=normal,
            origin=fc_vector(analytic, "Center", "Location"),
            radius=fc_float(analytic, "Radius"),
            convex=True,
        )
    if stype == FC_TOROID:
        major, minor = fc_torus_radii(analytic)
        return AAGNode(
            **ident,
            surface_kind=kind,
            axis=fc_vector(analytic, "Axis"),
            origin=fc_torus_origin(analytic),
            radius=major,
            secondary_radius=minor,
        )
    outer_name = fc_surface_class_name(surface)
    samples = _sample_normals(shape, 4)
    bb = shape.BoundBox
    diag = float(
        np.linalg.norm(
            [bb.XMax - bb.XMin, bb.YMax - bb.YMin, bb.ZMax - bb.ZMin]
        )
    )
    return AAGNode(
        **ident,
        surface_kind=FREEFORM
        if kind == FREEFORM or outer_name in FREEFORM_FC_NAMES
        else OTHER,
        origin=point,
        axis=normal,
        normal_samples=tuple(samples),
        bbox_diag=diag,
    )


def _sample_normals(shape: Any, n: int) -> list[NormalSample]:
    u0, u1, v0, v1 = shape.ParameterRange
    out: list[NormalSample] = []
    for i in range(n):
        u = u0 + (i + 0.5) / n * (u1 - u0)
        v = v0 + 0.5 * (v1 - v0)
        out.append(
            NormalSample(_vec(shape.valueAt(u, v)), _vec(shape.normalAt(u, v)))
        )
    return out
