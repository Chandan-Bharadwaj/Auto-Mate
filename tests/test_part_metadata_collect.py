from App_FreeCAD.part_metadata_collect import collect_part_metadata
from MateCore.context import PartContext, SurfaceRef


class Plane:
    pass


class _Face:
    def __init__(self, area: float, surface: object) -> None:
        self.Area = area
        self.Surface = surface


def _ref(area: float, surface: object, part_id: str = "P") -> SurfaceRef:
    return SurfaceRef("O", "O", "F", _Face(area, surface), None, part_id=part_id)


def test_collect_median_and_kinds():
    part = PartContext(
        "P",
        "P",
        "O",
        faces=(
            _ref(1.0, Plane()),
            _ref(3.0, Plane()),
            _ref(2.0, Plane()),
        ),
    )
    meta = collect_part_metadata(part)
    assert meta.face_count == 3
    assert meta.median_face_area == 2.0
    assert meta.total_face_area == 6.0
    assert meta.faces_by_kind.get("plane") == 3


def test_collect_empty_part():
    part = PartContext("P", "P", "O", faces=())
    meta = collect_part_metadata(part)
    assert meta.face_count == 0
    assert meta.median_face_area == 0.0
