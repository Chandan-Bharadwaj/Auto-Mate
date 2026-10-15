import re
from pathlib import Path

_IMPORT_FREE = re.compile(r"^\s*(?:import|from)\s+FreeCAD(?:Gui)?\b", re.MULTILINE)


def test_matecore_has_no_freecad_imports():
    root = Path(__file__).resolve().parents[1] / "src" / "MateCore"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if _IMPORT_FREE.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(root.parent.parent)))
    assert offenders == []
