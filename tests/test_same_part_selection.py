from types import SimpleNamespace

from App_FreeCAD.selection import SamePartSelectionGate, filter_same_part
from MateCore.context import SurfaceRef


def _ref(obj, face, part):
    return SurfaceRef(obj, obj, face, object(), object(), part_id=part)


def test_filter_same_part_keeps_anchor_part_only():
    a1, a2, b1 = _ref("O", "Face1", "A"), _ref("O", "Face2", "A"), _ref("O", "Face3", "B")
    kept, rejected = filter_same_part([a1, b1, a2])
    assert kept == [a1, a2]
    assert rejected == [b1]


def test_filter_same_part_empty():
    assert filter_same_part([]) == ([], [])


def _selection(obj, names):
    entry = SimpleNamespace(Object=obj, SubElementNames=names)
    return SimpleNamespace(getSelectionEx=lambda: [entry] if names else [])


def test_gate_allows_only_faces_of_anchor_object():
    doc = SimpleNamespace(Name="D")
    first = SimpleNamespace(Name="X", Document=doc)
    other = SimpleNamespace(Name="Y", Document=doc)
    gate = SamePartSelectionGate(_selection(first, ["Face1"]))
    assert gate.allow(doc, first, "Face2")
    assert not gate.allow(doc, other, "Face1")
    assert not gate.allow(doc, first, "Edge1")


def test_gate_allows_anything_face_when_empty():
    doc = SimpleNamespace(Name="D")
    obj = SimpleNamespace(Name="X", Document=doc)
    assert SamePartSelectionGate(_selection(obj, [])).allow(doc, obj, "Face3")
