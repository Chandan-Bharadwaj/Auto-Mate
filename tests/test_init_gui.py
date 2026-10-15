"""Workbench init: command registration without loading FreeCAD."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock


def _load_init_gui(repo_root: Path) -> ModuleType:
    init_path = repo_root / "FeatureTools" / "InitGui.py"
    spec = importlib.util.spec_from_file_location("FeatureTools_InitGui", init_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)

    fake_gui = MagicMock()
    fake_gui.Workbench = type("Workbench", (), {})
    registered_workbenches: list[object] = []

    def add_workbench(wb):
        registered_workbenches.append(wb)

    fake_gui.addCommand = MagicMock()
    class _WB:
        MenuText = ""
        ToolTip = ""
        Icon = ""

        def appendToolbar(self, *_args, **_kwargs):
            pass

        def appendMenu(self, *_args, **_kwargs):
            pass

    fake_gui.Workbench = _WB
    fake_gui.addWorkbench = add_workbench

    fake_fc = MagicMock()
    fake_fc.Console.PrintError = MagicMock()

    sys.modules["FreeCAD"] = fake_fc
    sys.modules["FreeCADGui"] = fake_gui
    src = str(repo_root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    spec.loader.exec_module(module)
    module._test_registered = registered_workbenches  # type: ignore[attr-defined]
    return module


def test_init_gui_registers_workbench(tmp_path_factory):
    repo = Path(__file__).resolve().parents[1]
    mod = _load_init_gui(repo)
    assert len(mod._test_registered) == 1
    wb = mod._test_registered[0]
    assert wb.MenuText == "Auto-Mate"

    wb.Initialize()
    from App_FreeCAD.command import COMMAND_ID

    fake_gui = sys.modules["FreeCADGui"]
    fake_gui.addCommand.assert_called()
    assert fake_gui.addCommand.call_args[0][0] == COMMAND_ID
