"""Map face tessellation into document (global) coordinates for Coin overlays."""

from __future__ import annotations

from typing import Any


def global_placement(owner: Any) -> Any | None:
    getter = getattr(owner, "getGlobalPlacement", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
    return getattr(owner, "Placement", None)


def resolve_face_shape(surface: Any) -> Any:
    owner = surface.owner
    doc_shape = getattr(owner, "Shape", None)
    if doc_shape is not None:
        get_element = getattr(doc_shape, "getElement", None)
        if callable(get_element):
            try:
                return get_element(surface.face_name)
            except Exception:
                pass
    return surface.shape


def tessellate_surface_global(
    surface: Any, tolerance: float
) -> tuple[list[tuple[float, float, float]], Any]:
    """Return vertices in global coordinates and triangle indices."""
    face = resolve_face_shape(surface)
    tessellate = getattr(face, "tessellate", None)
    if not callable(tessellate):
        return [], ()
    vertices, facets = tessellate(tolerance)
    if not facets:
        return [], facets
    placement = global_placement(surface.owner)
    return transform_vertices(vertices, placement), facets


def transform_vertices(vertices: Any, placement: Any | None) -> list[tuple[float, float, float]]:
    if placement is None:
        return [_vertex_tuple(v) for v in vertices]
    mult = getattr(placement, "multVec", None)
    if not callable(mult):
        return [_vertex_tuple(v) for v in vertices]
    return [_vertex_tuple(mult(v)) for v in vertices]


def _vertex_tuple(point: Any) -> tuple[float, float, float]:
    return (float(point.x), float(point.y), float(point.z))
