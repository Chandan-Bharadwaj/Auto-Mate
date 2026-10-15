"""Part metadata predicate derived from a search pattern."""

from __future__ import annotations

from MateCore.MateGraph.metadata import PartMetadata, PartMetadataPredicate
from MateCore.MateGraph.metadata_requirements import PatternMetadataRequirements


class MatingMetadataPredicate:
    def __init__(self, requirements: PatternMetadataRequirements) -> None:
        self._requirements = requirements

    def accept(self, metadata: PartMetadata) -> bool:
        req = self._requirements
        if metadata.face_count < req.min_face_count:
            return False
        for kind, need in req.min_faces_by_kind.items():
            if metadata.faces_by_kind.get(kind, 0) < need:
                return False
        return True


def predicate_from_pattern(requirements: PatternMetadataRequirements) -> PartMetadataPredicate:
    return MatingMetadataPredicate(requirements)
