"""Capture FreeCAD document objects into host-independent context snapshots."""

from __future__ import annotations

from typing import Any

from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    SurfaceRef,
)


def capture_document_context(document: Any) -> DocumentContext:
    objects: list[DocumentObjectContext] = []
    for obj in document.Objects:
        type_id = str(obj.TypeId)
        shape = getattr(obj, "Shape", None)
        shape_faces = tuple(getattr(shape, "Faces", ()))
        shape_solids = tuple(getattr(shape, "Solids", ()))
        shape_shells = tuple(getattr(shape, "Shells", ()))
        group_members = tuple(str(member.Name) for member in getattr(obj, "Group", ()))

        is_container = _is_container_aggregate(obj)
        is_datum = _is_datum_or_helper(type_id)

        faces, parts = _decompose_object_parts(
            obj=obj,
            shape_faces=shape_faces,
            shape_solids=shape_solids,
            shape_shells=shape_shells,
            is_container=is_container,
            is_datum=is_datum,
        )

        objects.append(
            DocumentObjectContext(
                name=str(obj.Name),
                label=str(obj.Label),
                type_id=type_id,
                kind=_object_kind(type_id, bool(shape_faces), is_container),
                group_members=group_members,
                faces=faces,
                parts=parts,
            )
        )
    return DocumentContext(str(document.Name), tuple(objects))


def _is_datum_or_helper(type_id: str) -> bool:
    normalized = type_id.casefold()
    return any(
        d in normalized
        for d in ("app::plane", "app::line", "app::point", "origin", "datum")
    )


def _is_container_aggregate(obj: Any) -> bool:
    group = getattr(obj, "Group", ())
    for member in group:
        m_shape = getattr(member, "Shape", None)
        if m_shape and len(getattr(m_shape, "Faces", ())) > 0:
            return True
    return False


def _faces_match(f1: Any, f2: Any) -> bool:
    if f1 is f2:
        return True
    is_same = getattr(f1, "isSame", None)
    if callable(is_same):
        try:
            return bool(is_same(f2))
        except Exception:
            pass
    return False


def _decompose_object_parts(
    obj: Any,
    shape_faces: tuple[Any, ...],
    shape_solids: tuple[Any, ...],
    shape_shells: tuple[Any, ...],
    is_container: bool,
    is_datum: bool,
) -> tuple[tuple[SurfaceRef, ...], tuple[PartContext, ...]]:
    obj_name = str(obj.Name)
    obj_label = str(obj.Label)

    if is_container or is_datum or not shape_faces:
        faces = tuple(
            SurfaceRef(obj_name, obj_label, f"Face{i}", f, obj, part_id="")
            for i, f in enumerate(shape_faces, start=1)
        )
        return faces, ()

    if len(shape_solids) > 1:
        parts: list[PartContext] = []
        all_face_refs: list[SurfaceRef] = []
        assigned_indices: set[int] = set()

        for s_idx, solid in enumerate(shape_solids, start=1):
            part_id = f"{obj_name}:Solid{s_idx}"
            part_name = f"{obj_label} (Solid {s_idx})"
            solid_faces_raw = tuple(getattr(solid, "Faces", ()))
            part_face_refs: list[SurfaceRef] = []

            for f_idx, raw_face in enumerate(shape_faces, start=1):
                if any(_faces_match(raw_face, sf) for sf in solid_faces_raw):
                    ref = SurfaceRef(
                        obj_name,
                        obj_label,
                        f"Face{f_idx}",
                        raw_face,
                        obj,
                        part_id=part_id,
                    )
                    part_face_refs.append(ref)
                    assigned_indices.add(f_idx)

            if not part_face_refs and len(solid_faces_raw) > 0:
                for sf_idx, sf in enumerate(solid_faces_raw, start=1):
                    ref = SurfaceRef(
                        obj_name,
                        obj_label,
                        f"Solid{s_idx}_Face{sf_idx}",
                        sf,
                        obj,
                        part_id=part_id,
                    )
                    part_face_refs.append(ref)

            parts.append(
                PartContext(
                    part_id=part_id,
                    name=part_name,
                    object_name=obj_name,
                    solid_index=s_idx,
                    shape=solid,
                    faces=tuple(part_face_refs),
                    kind="solid",
                )
            )
            all_face_refs.extend(part_face_refs)

        for f_idx, raw_face in enumerate(shape_faces, start=1):
            if f_idx not in assigned_indices:
                all_face_refs.append(
                    SurfaceRef(
                        obj_name,
                        obj_label,
                        f"Face{f_idx}",
                        raw_face,
                        obj,
                        part_id="",
                    )
                )

        return tuple(all_face_refs), tuple(parts)

    if len(shape_solids) == 1:
        part_id = obj_name
        faces = tuple(
            SurfaceRef(obj_name, obj_label, f"Face{i}", f, obj, part_id=part_id)
            for i, f in enumerate(shape_faces, start=1)
        )
        part = PartContext(
            part_id=part_id,
            name=obj_label,
            object_name=obj_name,
            solid_index=None,
            shape=shape_solids[0],
            faces=faces,
            kind="solid",
        )
        return faces, (part,)

    part_id = obj_name
    faces = tuple(
        SurfaceRef(obj_name, obj_label, f"Face{i}", f, obj, part_id=part_id)
        for i, f in enumerate(shape_faces, start=1)
    )
    part = PartContext(
        part_id=part_id,
        name=obj_label,
        object_name=obj_name,
        solid_index=None,
        shape=getattr(obj, "Shape", None),
        faces=faces,
        kind="shell",
    )
    return faces, (part,)


def _object_kind(type_id: str, has_faces: bool, is_container: bool = False) -> str:
    normalized = type_id.casefold()
    if "assembly" in normalized or is_container:
        return "assembly"
    if "part" in normalized or "body" in normalized or has_faces:
        return "part"
    return "object"
