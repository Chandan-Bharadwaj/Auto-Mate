"""Host-independent document and recognition request data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SurfaceRef:
    object_name: str
    object_label: str
    face_name: str
    shape: Any
    owner: Any
    part_id: str = ""


@dataclass(frozen=True, slots=True)
class PartContext:
    part_id: str
    name: str
    object_name: str
    solid_index: int | None = None
    shape: Any = None
    faces: tuple[SurfaceRef, ...] = ()
    kind: str = "solid"


@dataclass(frozen=True, slots=True)
class DocumentObjectContext:
    name: str
    label: str
    type_id: str
    kind: str
    group_members: tuple[str, ...]
    faces: tuple[SurfaceRef, ...] = ()
    parts: tuple[PartContext, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentContext:
    document_name: str
    objects: tuple[DocumentObjectContext, ...]

    @property
    def all_parts(self) -> tuple[PartContext, ...]:
        return tuple(part for obj in self.objects for part in obj.parts)

    def get_part(self, part_id: str) -> PartContext | None:
        for part in self.all_parts:
            if part.part_id == part_id:
                return part
        return None

    def get_part_for_face(self, surface: SurfaceRef) -> PartContext | None:
        if surface.part_id:
            part = self.get_part(surface.part_id)
            if part is not None:
                return part
        for part in self.all_parts:
            if any(
                f.object_name == surface.object_name and f.face_name == surface.face_name
                for f in part.faces
            ):
                return part
        return None


@dataclass(frozen=True, slots=True)
class RecognitionRequest:
    context: DocumentContext
    surfaces: tuple[SurfaceRef, ...]


@dataclass(frozen=True, slots=True)
class MateQuery:
    """A request resolved to its source part (None when it spans no single part)."""

    source_part: PartContext | None
    surfaces: tuple[SurfaceRef, ...]
    context: DocumentContext
