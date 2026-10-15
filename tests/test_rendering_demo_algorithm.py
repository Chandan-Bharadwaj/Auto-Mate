import random

from MateCore.algorithm import AlgorithmConfig
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.rendering_demo_algorithm import DummyRenderingDemoAlgorithm


def make_surface(part_id: str, object_name: str, label: str, face: str) -> SurfaceRef:
    return SurfaceRef(
        object_name,
        label,
        face,
        object(),
        object(),
        part_id=part_id,
    )


def make_multi_part_context(part_face_counts: dict[str, int]) -> DocumentContext:
    objects: list[DocumentObjectContext] = []
    for name, count in part_face_counts.items():
        part_id = name
        faces = tuple(
            make_surface(part_id, name, name.upper(), f"Face{i}")
            for i in range(1, count + 1)
        )
        objects.append(
            DocumentObjectContext(
                name=name,
                label=name.upper(),
                type_id="Part::Feature",
                kind="part",
                group_members=(),
                faces=faces,
                parts=(
                    PartContext(part_id, name.upper(), name, faces=faces),
                ),
            )
        )
    return DocumentContext(document_name="Document", objects=tuple(objects))


def test_rendering_demo_picks_four_parts_with_ten_faces_each():
    context = make_multi_part_context(
        {f"p{i}": 12 for i in range(1, 7)} | {"source": 12}
    )
    source = context.objects[-1].faces[0]
    request = RecognitionRequest(context, (source,))
    algo = DummyRenderingDemoAlgorithm(
        rng=random.Random(0),
        part_count=4,
        surfaces_per_part=10,
        config=AlgorithmConfig(max_parts=4, max_matches_per_part=1),
    )

    result = algo.run(request)

    assert len(result.part_matches) == 4
    for part_match in result.part_matches:
        assert part_match.part_id != "source"
        assert len(part_match.matches) == 1
        assert len(part_match.matches[0].faces) == 10
    groups = result.as_surface_groups()
    assert len(groups) == 4
    assert all(len(group) == 10 for group in groups)
    keys = {(f.object_name, f.face_name) for group in groups for f in group}
    assert len(keys) == 40
    assert not any(
        f.object_name == source.object_name and f.face_name == source.face_name
        for group in groups
        for f in group
    )


def test_rendering_demo_uses_fewer_parts_when_document_is_small():
    context = make_multi_part_context({"source": 5, "only": 8})
    request = RecognitionRequest(context, (context.objects[0].faces[0],))
    algo = DummyRenderingDemoAlgorithm(
        rng=random.Random(1),
        part_count=4,
        surfaces_per_part=10,
        config=AlgorithmConfig(max_parts=4, max_matches_per_part=1),
    )

    result = algo.run(request)

    assert len(result.part_matches) == 1
    assert len(result.part_matches[0].matches[0].faces) == 8
    assert any("Rendering demo" in w for w in result.warnings)
