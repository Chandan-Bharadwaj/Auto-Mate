"""Fast PartMetadata from Part face list (no adjacency graph)."""

from __future__ import annotations

import statistics
from collections import Counter

from MateCore.MateGraph.metadata import METADATA_VERSION, PartMetadata
from MateCore.context import PartContext

from .fc_surface import aag_surface_kind_from_surface


def collect_part_metadata(part: PartContext) -> PartMetadata:
    areas: list[float] = []
    kinds: Counter[str] = Counter()
    for ref in part.faces:
        shape = ref.shape
        if shape is None:
            continue
        areas.append(float(shape.Area))
        surface = getattr(shape, "Surface", None)
        if surface is None:
            kinds["other"] += 1
        else:
            kinds[aag_surface_kind_from_surface(surface)] += 1

    face_count = len(areas)
    if face_count == 0:
        return PartMetadata(
            part_id=part.part_id,
            face_count=0,
            median_face_area=0.0,
            total_face_area=0.0,
            faces_by_kind=dict(kinds),
            metadata_version=METADATA_VERSION,
        )

    return PartMetadata(
        part_id=part.part_id,
        face_count=face_count,
        median_face_area=float(statistics.median(areas)),
        total_face_area=float(sum(areas)),
        faces_by_kind=dict(kinds),
        metadata_version=METADATA_VERSION,
    )
