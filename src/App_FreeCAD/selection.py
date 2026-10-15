"""Adapt FreeCAD GUI extended selections to surface references."""

from __future__ import annotations

import re
from typing import Any

from MateCore.context import SurfaceRef

_FACE_NAME = re.compile(r"Face([1-9][0-9]*)\Z")


def are_adjacent(face_a: Any, face_b: Any) -> bool:
    """Faces are adjacent when they share at least one edge."""
    return any(a.isSame(b) for a in face_a.Edges for b in face_b.Edges)


def filter_adjacent_to_first(
    surfaces: list[SurfaceRef],
) -> tuple[list[SurfaceRef], list[SurfaceRef]]:
    """Keep the first surface plus same-object faces sharing an edge with it."""
    if not surfaces:
        return [], []
    anchor = surfaces[0]
    kept = [anchor]
    rejected: list[SurfaceRef] = []
    for surface in surfaces[1:]:
        if surface.object_name == anchor.object_name and are_adjacent(
            anchor.shape, surface.shape
        ):
            kept.append(surface)
        else:
            rejected.append(surface)
    return kept, rejected


class SamePartSelectionGate:
    """FreeCAD selection gate: faces only, all on the same part as the first face."""

    def __init__(self, selection: Any, context: Any = None) -> None:
        self._selection = selection
        self._part_of = _part_lookup(context)

    def _part_key(self, obj_name: str, face_name: str) -> str:
        return self._part_of.get((obj_name, face_name), obj_name)

    def allow(self, doc: Any, obj: Any, sub: str) -> bool:
        if _FACE_NAME.fullmatch(str(sub)) is None:
            return False
        anchor = self._first_selected_face()
        if anchor is None:
            return True
        anchor_obj, anchor_name = anchor
        if doc.Name != anchor_obj.Document.Name:
            return False
        return self._part_key(str(obj.Name), str(sub)) == self._part_key(
            str(anchor_obj.Name), anchor_name
        )

    def _first_selected_face(self) -> tuple[Any, str] | None:
        for entry in self._selection.getSelectionEx():
            for name in entry.SubElementNames:
                if _FACE_NAME.fullmatch(str(name)):
                    return entry.Object, str(name)
        return None


def _part_lookup(context: Any) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    for part in getattr(context, "all_parts", ()) or ():
        for face in part.faces:
            lookup[(face.object_name, face.face_name)] = part.part_id
    return lookup


def surface_part_key(surface: SurfaceRef) -> str:
    return surface.part_id or surface.object_name


def filter_same_part(
    surfaces: list[SurfaceRef],
) -> tuple[list[SurfaceRef], list[SurfaceRef]]:
    """Keep the first surface plus every surface on the same part."""
    if not surfaces:
        return [], []
    anchor_key = surface_part_key(surfaces[0])
    kept = [s for s in surfaces if surface_part_key(s) == anchor_key]
    rejected = [s for s in surfaces if surface_part_key(s) != anchor_key]
    return kept, rejected


class FaceAdjacencySelectionGate:
    """FreeCAD selection gate: faces only, adjacent to the first selected face."""

    def __init__(self, selection: Any) -> None:
        self._selection = selection

    def allow(self, doc: Any, obj: Any, sub: str) -> bool:
        if _FACE_NAME.fullmatch(str(sub)) is None:
            return False
        anchor = self._first_selected_face()
        if anchor is None:
            return True
        anchor_obj, anchor_name = anchor
        if obj.Name != anchor_obj.Name or doc.Name != anchor_obj.Document.Name:
            return False
        if sub == anchor_name:
            return True
        return are_adjacent(
            anchor_obj.Shape.getElement(anchor_name), obj.Shape.getElement(sub)
        )

    def _first_selected_face(self) -> tuple[Any, str] | None:
        for entry in self._selection.getSelectionEx():
            for name in entry.SubElementNames:
                if _FACE_NAME.fullmatch(str(name)):
                    return entry.Object, str(name)
        return None


def get_selected_surfaces(
    selection: Any, context: Any = None
) -> list[SurfaceRef]:
    surfaces: list[SurfaceRef] = []
    seen: set[tuple[str, str]] = set()

    for entry in selection.getSelectionEx():
        owner = entry.Object
        sub_element_names = tuple(entry.SubElementNames)
        sub_objects = tuple(entry.SubObjects)
        shape_faces = getattr(getattr(owner, "Shape", None), "Faces", ())

        for position, face_name in enumerate(sub_element_names):
            match = _FACE_NAME.fullmatch(str(face_name))
            if match is None:
                continue

            key = (str(owner.Name), str(face_name))
            if key in seen:
                continue

            face_index = int(match.group(1)) - 1
            if position < len(sub_objects):
                face_shape = sub_objects[position]
            elif face_index < len(shape_faces):
                face_shape = shape_faces[face_index]
            else:
                continue

            seen.add(key)
            part_id = ""
            if context is not None and hasattr(context, "get_part_for_face"):
                probe_ref = SurfaceRef(
                    str(owner.Name),
                    str(owner.Label),
                    str(face_name),
                    face_shape,
                    owner,
                )
                part = context.get_part_for_face(probe_ref)
                if part is not None:
                    part_id = part.part_id

            surfaces.append(
                SurfaceRef(
                    object_name=str(owner.Name),
                    object_label=str(owner.Label),
                    face_name=str(face_name),
                    shape=face_shape,
                    owner=owner,
                    part_id=part_id,
                )
            )

    return surfaces
