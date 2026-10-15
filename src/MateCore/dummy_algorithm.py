"""Dummy implementation of the mate algorithm interface for workflow testing."""

from __future__ import annotations

import random

from .algorithm import AlgorithmConfig, Match, MateAlgorithm, RunContext
from .context import DocumentContext, PartContext, RecognitionRequest


def object_level_parts(context: DocumentContext) -> list[PartContext]:
    """Treat each document object with faces as one part (no solid analysis)."""
    return [
        PartContext(o.name, o.label, o.name, faces=o.faces)
        for o in context.objects
        if o.faces
    ]


class DummyMateAlgorithm(MateAlgorithm):
    name = "dummy"
    single_source_part = False

    def __init__(
        self,
        rng: random.Random | None = None,
        max_group_size: int = 3,
        max_total: int = 90,
        config: AlgorithmConfig | None = None,
    ) -> None:
        super().__init__(config)
        if max_group_size < 1 or max_total < 1:
            raise ValueError("max_group_size and max_total must be at least 1")
        self._rng = rng or random.Random()
        self._max_group_size = max_group_size
        self._max_total = max_total

    def validate(self, request: RecognitionRequest, run: RunContext) -> None:
        context_names = {obj.name for obj in request.context.objects}
        unknown_objects = sorted(
            {surface.object_name for surface in request.surfaces} - context_names
        )
        if unknown_objects:
            names = ", ".join(unknown_objects)
            raise ValueError(
                f"Selected surfaces are not part of document "
                f"'{request.context.document_name}': {names}"
            )

    def candidate_parts(self, state, query, run) -> list[PartContext]:
        return object_level_parts(query.context)

    def match_part(
        self, state: RecognitionRequest, part: PartContext, run: RunContext
    ) -> list[Match]:
        selected = {(s.object_name, s.face_name) for s in state.surfaces}
        faces = [f for f in part.faces if (f.object_name, f.face_name) not in selected]
        if not faces:
            return []
        total = self._rng.randint(1, min(len(faces), self._max_total))
        shuffled = self._rng.sample(faces, total)
        groups: list[Match] = []
        offset = 0
        while offset < len(shuffled):
            remaining = len(shuffled) - offset
            size = self._rng.randint(1, min(self._max_group_size, remaining))
            groups.append(Match(tuple(shuffled[offset : offset + size])))
            offset += size
        return groups
