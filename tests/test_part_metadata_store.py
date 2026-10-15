from MateCore.MateGraph.metadata import PartMetadata
from MateCore.MateGraph.metadata_store import PartMetadataStore
from MateCore.context import PartContext, SurfaceRef
from App_FreeCAD.geometry_cache import clear_registry, get_or_create, get_part_metadata_store


def _part(part_id: str) -> PartContext:
    ref = SurfaceRef(part_id, part_id, "Face1", None, None, part_id=part_id)
    return PartContext(part_id, part_id, part_id, faces=(ref,))


def test_metadata_store_builds_once_per_part():
    calls: list[str] = []

    def collector(part: PartContext) -> PartMetadata:
        calls.append(part.part_id)
        return PartMetadata(
            part_id=part.part_id,
            face_count=1,
            median_face_area=1.0,
            total_face_area=1.0,
            faces_by_kind={"plane": 1},
        )

    store = PartMetadataStore("Doc", collector)
    part = _part("P")
    assert store.get(part) is store.get(part)
    assert calls == ["P"]


def test_metadata_store_lazy_per_part():
    built: list[str] = []

    def collector(part: PartContext) -> PartMetadata:
        built.append(part.part_id)
        return PartMetadata(
            part_id=part.part_id,
            face_count=0,
            median_face_area=0.0,
            total_face_area=0.0,
            faces_by_kind={},
        )

    store = PartMetadataStore("Doc", collector)
    store.get(_part("A"))
    assert built == ["A"]
    store.get(_part("B"))
    assert built == ["A", "B"]


def test_get_part_metadata_store_separate_documents():
    clear_registry()
    assert get_part_metadata_store("A") is not get_part_metadata_store("B")
    assert get_or_create("A").part_metadata_store() is get_part_metadata_store("A")
