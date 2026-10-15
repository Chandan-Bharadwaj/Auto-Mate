"""FreeCAD GUI command and selection/compute/display phase controller."""

from __future__ import annotations

from collections.abc import Callable

import FreeCAD
import FreeCADGui

from MateCore.algorithm import MateAlgorithm
from MateCore.context import RecognitionRequest
from MateCore.trace import MODULE_COMMAND, set_trace_sink, trace_milestone

from .algorithm_factory import create_algorithm, known_algorithms
from .document_context import capture_document_context
from .geometry_cache import DocumentGeometryCache, get_or_create
from .display import display_part_results
from .phase_ui import PHASE_PRESENTATION, CommandPhase
from .rendering import FreeCADResultRenderer, load_style
from .rendering.lifecycle import (
    _REASON_MESSAGES,
    install_escape_filter,
    uninstall_escape_filter,
)
from .command_trace import trace_compute_context, trace_sink_for_freecad
from .rendering.preferences import sync_trace_from_preferences
from .selection import (
    SamePartSelectionGate,
    filter_same_part,
    get_selected_surfaces,
)
from .settings import get_algorithm

COMMAND_ID = "AutoMate_SelectSurfaces"

_command_registered = False
_command_instance = None


def register_command() -> None:
    """Register the Auto-Mate command with FreeCAD (call from InitGui.Initialize)."""
    global _command_registered
    if _command_registered:
        return
    FreeCADGui.addCommand(COMMAND_ID, get_command())
    _command_registered = True


class AutoMateCommand:
    def __init__(
        self,
        renderer=None,
        algorithm_factory: Callable[[str], MateAlgorithm] | None = None,
    ) -> None:
        self._algorithm_factory = algorithm_factory or create_algorithm
        self._renderer = renderer or FreeCADResultRenderer(FreeCADGui, load_style)
        self._phase = CommandPhase.IDLE
        self._context = None
        self._geometry_cache: DocumentGeometryCache | None = None
        self._cache_document: str | None = None

    def GetResources(self):
        presentation = PHASE_PRESENTATION[self._phase]
        return {
            "Pixmap": presentation.icon,
            "MenuText": presentation.menu_text,
            "ToolTip": presentation.tooltip,
        }

    def _set_phase(self, phase: CommandPhase) -> None:
        """Change phase and refresh the toolbar/menu action's icon and text."""
        self._phase = phase
        presentation = PHASE_PRESENTATION[phase]
        try:
            from PySide import QtGui

            icon = QtGui.QIcon(presentation.icon)
            for action in FreeCADGui.Command.get(COMMAND_ID).getAction() or ():
                action.setIcon(icon)
                action.setText(presentation.menu_text)
                action.setToolTip(presentation.tooltip)
            QtGui.QApplication.processEvents()
        except Exception:
            pass

    def IsActive(self) -> bool:
        return FreeCAD.ActiveDocument is not None

    def Activated(self) -> None:
        if self._phase != CommandPhase.SELECTION:
            self._begin_selection()
            return
        self._compute_and_display()

    def Deactivated(self) -> None:
        """Drop overlays and part tints when another command takes focus."""
        self.teardown_rendering()

    def teardown_rendering(self, reason: str = "") -> None:
        uninstall_escape_filter()
        if self._phase in (CommandPhase.SELECTION, CommandPhase.DISPLAY):
            try:
                FreeCADGui.Selection.removeSelectionGate()
            except Exception:
                pass
        self._renderer.teardown()
        self._context = None
        self._set_phase(CommandPhase.IDLE)
        if reason:
            message = _REASON_MESSAGES.get(
                reason, f"Cleared mate rendering ({reason}).\n"
            )
            FreeCAD.Console.PrintMessage(message)

    def _begin_selection(self) -> None:
        if self._phase == CommandPhase.DISPLAY:
            FreeCAD.Console.PrintMessage("Clearing result rendering.\n")
            self.teardown_rendering()
        elif self._renderer.is_active():
            self._renderer.teardown()
        document = FreeCAD.ActiveDocument
        if document is None:
            FreeCAD.Console.PrintError("Open a document before running Auto-Mate.\n")
            self._set_phase(CommandPhase.IDLE)
            self._context = None
            return

        self._context = capture_document_context(document)
        self._ensure_geometry_cache(document.Name)
        self._set_phase(CommandPhase.SELECTION)
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelectionGate(
            SamePartSelectionGate(FreeCADGui.Selection, self._context)
        )
        FreeCAD.Console.PrintMessage(
            f"Selection phase started for '{self._context.document_name}'. "
            "Select faces on a single part (they need not be adjacent); "
            "click Auto-Mate again to finish.\n"
        )
        install_escape_filter()

    def _compute_and_display(self) -> None:
        context = self._context
        if context is None:
            self._begin_selection()
            return

        document = FreeCAD.ActiveDocument
        if document is None or document.Name != context.document_name:
            self.teardown_rendering()
            FreeCAD.Console.PrintError(
                "The active document changed during selection. "
                "Click Auto-Mate to start a new run.\n"
            )
            return

        surfaces, rejected = filter_same_part(
            get_selected_surfaces(FreeCADGui.Selection, context=context)
        )
        if rejected:
            FreeCAD.Console.PrintWarning(
                f"Ignored {len(rejected)} face(s) not on the same part as the first one.\n"
            )
        if not surfaces:
            FreeCAD.Console.PrintError(
                "No faces selected. Select one or more faces, then click "
                "Auto-Mate again.\n"
            )
            return

        FreeCADGui.Selection.removeSelectionGate()
        self._set_phase(CommandPhase.COMPUTE)
        FreeCAD.Console.PrintMessage(
            f"Compute phase: processing {len(surfaces)} selected surface(s).\n"
        )
        request = RecognitionRequest(context, tuple(surfaces))
        sync_trace_from_preferences()
        set_trace_sink(trace_sink_for_freecad(FreeCAD.Console))
        algorithm_id = get_algorithm()
        trace_milestone(
            MODULE_COMMAND,
            "compute",
            context={
                "algorithm": algorithm_id,
                "document": context.document_name,
                "face_count": len(surfaces),
            },
        )
        self._ensure_geometry_cache(document.Name)
        try:
            with trace_compute_context():
                try:
                    algorithm = self._algorithm_factory(
                        algorithm_id,
                        geometry_cache=self._ensure_geometry_cache(document.Name),
                    )
                except (KeyError, ValueError) as exc:
                    ids = ", ".join(known_algorithms())
                    FreeCAD.Console.PrintError(
                        f"Cannot create algorithm '{algorithm_id}': {exc}. "
                        f"Known algorithms: {ids}.\n"
                    )
                    self._set_phase(CommandPhase.SELECTION)
                    return
                FreeCAD.Console.PrintMessage(
                    f"Using algorithm '{algorithm_id}' ({algorithm.name}).\n"
                )
                result = algorithm.run(request)
        finally:
            set_trace_sink(None)
        self._set_phase(CommandPhase.DISPLAY)
        display_part_results(
            FreeCAD,
            FreeCADGui,
            context,
            result,
            self._renderer,
            request=request,
        )
        install_escape_filter()

    def _ensure_geometry_cache(self, document_name: str) -> DocumentGeometryCache:
        if self._cache_document != document_name:
            self._cache_document = document_name
            self._geometry_cache = get_or_create(document_name)
        return self._geometry_cache


def get_command() -> AutoMateCommand:
    global _command_instance
    if _command_instance is None:
        _command_instance = AutoMateCommand()
    return _command_instance
