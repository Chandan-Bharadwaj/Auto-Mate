import random
from pathlib import Path
from types import SimpleNamespace

import pytest

import MateCore.algorithm as algorithm_module
from App_FreeCAD.document_context import capture_document_context
from App_FreeCAD.selection import (
    FaceAdjacencySelectionGate,
    are_adjacent,
    filter_adjacent_to_first,
    get_selected_surfaces,
)
from MateCore.algorithm import Match, MateAlgorithm
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    RecognitionRequest,
    SurfaceRef,
)
from MateCore.dummy_algorithm import DummyMateAlgorithm, object_level_parts


def test_host_independent_core_is_loaded_from_src():
    src = Path(__file__).resolve().parents[1] / "src"

    assert Path(algorithm_module.__file__).resolve().is_relative_to(src / "MateCore")
    assert {
        path.name
        for path in src.iterdir()
        if path.is_dir()
        and path.name != "__pycache__"
        and not path.name.endswith(".egg-info")
    } == {"MateCore", "App_FreeCAD"}

def make_face(name, object_name="part"):
    return SurfaceRef(object_name, object_name, name, object(), object())


def make_request(face_count, selected_count):
    faces = tuple(make_face(f"Face{i}") for i in range(1, face_count + 1))
    context = DocumentContext(
        document_name="Document",
        objects=(
            DocumentObjectContext(
                name="part",
                label="Part",
                type_id="Part::Feature",
                kind="part",
                group_members=(),
                faces=faces,
            ),
        ),
    )
    selected = faces[:selected_count]
    return RecognitionRequest(context, selected), selected


@pytest.mark.parametrize("seed", range(20))
def test_dummy_algorithm_outputs_distinct_unselected_faces(seed):
    request, selected = make_request(12, 3)

    groups = DummyMateAlgorithm(rng=random.Random(seed)).compute(request)

    names = [s.face_name for group in groups for s in group]
    assert names
    assert len(names) == len(set(names))
    assert not set(names) & {s.face_name for s in selected}
    assert all(1 <= len(group) <= 3 for group in groups)


def test_dummy_algorithm_returns_empty_when_no_other_faces_exist():
    request, _ = make_request(2, 2)

    assert DummyMateAlgorithm(rng=random.Random(1)).compute(request) == []

def test_dummy_algorithm_rejects_surfaces_outside_document_context():
    request, surfaces = make_request(1, 1)
    invalid_surface = SurfaceRef(
        object_name="other-part",
        object_label="Other Part",
        face_name="Face1",
        shape=object(),
        owner=object(),
    )
    invalid_request = RecognitionRequest(request.context, (surfaces[0], invalid_surface))

    with pytest.raises(ValueError, match="other-part"):
        DummyMateAlgorithm(rng=random.Random(1)).compute(invalid_request)


def test_algorithm_interface_is_abstract_and_dummy_implements_it():
    with pytest.raises(TypeError):
        MateAlgorithm()
    assert issubclass(DummyMateAlgorithm, MateAlgorithm)


def test_any_subclass_can_replace_dummy_via_interface():
    class FirstFace(MateAlgorithm):
        single_source_part = False

        def candidate_parts(self, state, query, run):
            return object_level_parts(query.context)

        def match_part(self, state, part, run):
            return [Match((part.faces[0],))]

    request, _ = make_request(2, 1)
    algorithm: MateAlgorithm = FirstFace()

    assert algorithm.compute(request)[0][0].face_name == "Face1"


def test_document_snapshot_records_parts_assemblies_and_groups():
    part = SimpleNamespace(
        Name="Body",
        Label="Main body",
        TypeId="PartDesign::Body",
        Shape=SimpleNamespace(Faces=(object(),)),
        Group=(),
    )
    assembly = SimpleNamespace(
        Name="Assembly",
        Label="Assembly",
        TypeId="Assembly::AssemblyObject",
        Group=(part,),
    )
    document = SimpleNamespace(Name="CurrentDoc", Objects=(assembly, part))

    context = capture_document_context(document)

    assert context.document_name == "CurrentDoc"
    assert [(obj.name, obj.kind) for obj in context.objects] == [
        ("Assembly", "assembly"),
        ("Body", "part"),
    ]
    assert context.objects[0].group_members == ("Body",)


def test_selection_adapter_returns_unique_face_subobjects_only():
    owner = SimpleNamespace(
        Name="Body",
        Label="Main body",
        Shape=SimpleNamespace(Faces=("shape-face-1", "shape-face-2")),
    )
    entry = SimpleNamespace(
        Object=owner,
        SubElementNames=("Face1", "Edge1", "Face2"),
        SubObjects=("selected-face-1", "selected-face-2", "selected-face-2"),
    )
    selection = SimpleNamespace(getSelectionEx=lambda: (entry, entry))

    surfaces = get_selected_surfaces(selection)

    assert [surface.face_name for surface in surfaces] == ["Face1", "Face2"]
    assert [surface.shape for surface in surfaces] == [
        "selected-face-1",
        "selected-face-2",
    ]


class FakeFace:
    def __init__(self, *edges):
        self.Edges = edges


class Edge:
    def isSame(self, other):
        return self is other


def make_gate_world():
    e1, e2, e3 = Edge(), Edge(), Edge()
    faces = {"Face1": FakeFace(e1, e2), "Face2": FakeFace(e2, e3), "Face3": FakeFace(e3)}
    obj = SimpleNamespace(
        Name="Body",
        Document=SimpleNamespace(Name="Doc"),
        Shape=SimpleNamespace(getElement=faces.__getitem__),
    )
    return obj, faces


def test_are_adjacent_uses_shared_edges():
    _, faces = make_gate_world()

    assert are_adjacent(faces["Face1"], faces["Face2"])
    assert not are_adjacent(faces["Face1"], faces["Face3"])


def test_filter_adjacent_to_first_rejects_non_neighbours_and_other_objects():
    _, faces = make_gate_world()
    refs = [
        SurfaceRef("Body", "Body", name, faces[name], None) for name in faces
    ] + [SurfaceRef("Other", "Other", "Face1", faces["Face2"], None)]

    kept, rejected = filter_adjacent_to_first(refs)

    assert [s.face_name for s in kept] == ["Face1", "Face2"]
    assert [(s.object_name, s.face_name) for s in rejected] == [
        ("Body", "Face3"),
        ("Other", "Face1"),
    ]


def test_selection_gate_accepts_only_faces_adjacent_to_first():
    obj, _ = make_gate_world()
    doc = obj.Document
    selected = []
    selection = SimpleNamespace(
        getSelectionEx=lambda: [
            SimpleNamespace(Object=obj, SubElementNames=tuple(selected))
        ]
    )
    gate = FaceAdjacencySelectionGate(selection)

    assert not gate.allow(doc, obj, "Edge1")
    assert gate.allow(doc, obj, "Face1")
    selected.append("Face1")
    assert gate.allow(doc, obj, "Face2")
    assert not gate.allow(doc, obj, "Face3")
    assert not gate.allow(doc, SimpleNamespace(Name="Other"), "Face1")


def test_part_context_and_multisolid_decomposition():
    f1, f2, f3 = object(), object(), object()
    solid1 = SimpleNamespace(Faces=(f1, f2))
    solid2 = SimpleNamespace(Faces=(f3,))
    compound_shape = SimpleNamespace(
        Faces=(f1, f2, f3),
        Solids=(solid1, solid2),
        Shells=(),
    )
    obj = SimpleNamespace(
        Name="Part__Feature004",
        Label="COMPOUND001",
        TypeId="Part::Feature",
        Shape=compound_shape,
        Group=(),
    )
    doc = SimpleNamespace(Name="Doc", Objects=(obj,))

    context = capture_document_context(doc)

    assert len(context.all_parts) == 2
    p1 = context.get_part("Part__Feature004:Solid1")
    p2 = context.get_part("Part__Feature004:Solid2")
    assert p1 is not None and p2 is not None
    assert p1.solid_index == 1
    assert p2.solid_index == 2
    assert [f.face_name for f in p1.faces] == ["Face1", "Face2"]
    assert [f.face_name for f in p2.faces] == ["Face3"]
    assert all(f.part_id == "Part__Feature004:Solid1" for f in p1.faces)
    assert all(f.part_id == "Part__Feature004:Solid2" for f in p2.faces)


def test_container_aggregate_filtering_prevents_duplicate_parts():
    f1, f2 = object(), object()
    leaf_part = SimpleNamespace(
        Name="Body",
        Label="Main body",
        TypeId="PartDesign::Body",
        Shape=SimpleNamespace(Faces=(f1,), Solids=(SimpleNamespace(Faces=(f1,)),)),
        Group=(),
    )
    parent_assembly = SimpleNamespace(
        Name="Assembly",
        Label="Assembly",
        TypeId="App::Part",
        Shape=SimpleNamespace(Faces=(f1, f2), Solids=(SimpleNamespace(Faces=(f1, f2)),)),
        Group=(leaf_part,),
    )
    datum_plane = SimpleNamespace(
        Name="XY_Plane",
        Label="XY-Plane",
        TypeId="App::Plane",
        Shape=SimpleNamespace(Faces=(object(),), Solids=()),
        Group=(),
    )
    doc = SimpleNamespace(Name="Doc", Objects=(parent_assembly, leaf_part, datum_plane))

    context = capture_document_context(doc)

    assert len(context.all_parts) == 1
    assert context.all_parts[0].part_id == "Body"
    assert context.all_parts[0].name == "Main body"


def test_get_part_for_face_lookup():
    f1 = object()
    part = SimpleNamespace(
        Name="Body",
        Label="Main body",
        TypeId="PartDesign::Body",
        Shape=SimpleNamespace(Faces=(f1,), Solids=(SimpleNamespace(Faces=(f1,)),)),
        Group=(),
    )
    doc = SimpleNamespace(Name="Doc", Objects=(part,))
    context = capture_document_context(doc)

    ref = SurfaceRef("Body", "Main body", "Face1", f1, part)
    found_part = context.get_part_for_face(ref)
    assert found_part is not None
    assert found_part.part_id == "Body"


def test_occ_parts_module_safety_in_host_environment():
    from App_FreeCAD import occ_parts

    assert isinstance(occ_parts.is_occ_available(), bool)
    if not occ_parts.is_occ_available():
        with pytest.raises(RuntimeError, match="PythonOCC"):
            occ_parts.explore_solids(object())

