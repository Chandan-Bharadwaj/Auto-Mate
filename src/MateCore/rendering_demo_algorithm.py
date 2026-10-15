"""Dummy mate algorithm that returns fixed-size random face sets for render smoke tests."""

from __future__ import annotations

import random

from .algorithm import AlgorithmConfig, Match, MateAlgorithm, RunContext
from .context import PartContext, RecognitionRequest


class DummyRenderingDemoAlgorithm(MateAlgorithm):
    """Pick ``part_count`` parts at random and highlight ``surfaces_per_part`` faces each."""

    name = "rendering_demo"
    single_source_part = True

    def __init__(
        self,
        rng: random.Random | None = None,
        part_count: int = 4,
        surfaces_per_part: int = 10,
        config: AlgorithmConfig | None = None,
    ) -> None:
        if part_count < 1 or surfaces_per_part < 1:
            raise ValueError("part_count and surfaces_per_part must be at least 1")
        super().__init__(config)
        self._rng = rng or random.Random()
        self._part_count = part_count
        self._surfaces_per_part = surfaces_per_part
        self._chosen_parts: list[PartContext] = []

    def validate(self, request: RecognitionRequest, run: RunContext) -> None:
        super().validate(request, run)
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

    def prepare(self, request: RecognitionRequest, run: RunContext) -> RecognitionRequest:
        source_ids = {
            part.part_id
            for surface in request.surfaces
            for part in [request.context.get_part_for_face(surface)]
            if part is not None
        }
        selected = {(s.object_name, s.face_name) for s in request.surfaces}
        eligible: list[PartContext] = []
        for part in request.context.all_parts:
            if part.part_id in source_ids:
                continue
            available = [
                face
                for face in part.faces
                if (face.object_name, face.face_name) not in selected
            ]
            if available:
                eligible.append(part)
        pick = min(self._part_count, len(eligible))
        self._chosen_parts = self._rng.sample(eligible, pick) if pick else []
        if pick < self._part_count:
            run.warn(
                f"Rendering demo: {pick} part(s) available "
                f"(requested {self._part_count})."
            )
        return request

    def candidate_parts(
        self, state: RecognitionRequest, query, run: RunContext
    ) -> list[PartContext]:
        return list(self._chosen_parts)

    def match_part(
        self, state: RecognitionRequest, part: PartContext, run: RunContext
    ) -> list[Match]:
        selected = {(s.object_name, s.face_name) for s in state.surfaces}
        available = [
            face
            for face in part.faces
            if (face.object_name, face.face_name) not in selected
        ]
        if not available:
            run.explain(part.part_id, "no faces available for rendering demo")
            return []
        count = min(self._surfaces_per_part, len(available))
        faces = self._rng.sample(available, count)
        return [Match(tuple(faces), score=1.0)]
