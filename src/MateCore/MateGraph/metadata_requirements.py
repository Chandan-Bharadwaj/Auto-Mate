"""Domain-neutral metadata bounds derived from a graph pattern."""

from __future__ import annotations

from dataclasses import dataclass

from .search.pattern import GraphPattern


@dataclass(frozen=True, slots=True)
class PatternMetadataRequirements:
    """Lower bounds used to pre-filter candidate parts before graph build."""

    min_face_count: int
    min_faces_by_kind: dict[str, int]

    @classmethod
    def from_pattern(cls, pattern: GraphPattern) -> PatternMetadataRequirements:
        by_kind: dict[str, int] = {}
        for slot in pattern.slots:
            by_kind[slot.surface_kind] = by_kind.get(slot.surface_kind, 0) + 1
        return cls(
            min_face_count=len(pattern.slots),
            min_faces_by_kind=by_kind,
        )


def requirements_from_pattern(pattern: GraphPattern) -> PatternMetadataRequirements:
    return PatternMetadataRequirements.from_pattern(pattern)
