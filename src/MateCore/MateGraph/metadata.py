"""Lightweight per-part statistics for pre-filtering before graph build."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

METADATA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PartMetadata:
    part_id: str
    face_count: int
    median_face_area: float
    total_face_area: float
    faces_by_kind: dict[str, int]
    metadata_version: int = METADATA_VERSION
    extras: dict[str, float] = field(default_factory=dict)


class PartMetadataPredicate(Protocol):
    def accept(self, metadata: PartMetadata) -> bool: ...
