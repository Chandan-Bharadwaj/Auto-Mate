"""Register the Auto-Mate workbench with FreeCAD's GUI."""

import traceback

import FreeCAD
import FreeCADGui


class AutoMateWorkbench(FreeCADGui.Workbench):
    MenuText = "Auto-Mate"
    ToolTip = "Select and analyze CAD surfaces"

    def Initialize(self):
        try:
            from App_FreeCAD.command import COMMAND_ID, register_command
            from App_FreeCAD.rendering.lifecycle import register_render_lifecycle

            register_command()
            register_render_lifecycle()
            self.appendToolbar("Auto-Mate", [COMMAND_ID])
            self.appendMenu("Auto-Mate", [COMMAND_ID])
        except Exception:
            FreeCAD.Console.PrintError(
                "Auto-Mate workbench failed to initialize:\n"
                f"{traceback.format_exc()}\n"
            )
            raise


FreeCADGui.addWorkbench(AutoMateWorkbench())
