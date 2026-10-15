"""Document and keyboard hooks that tear down mate result rendering."""

from __future__ import annotations

from typing import Any, Callable

from ..phase_ui import CommandPhase

_lifecycle_registered = False
_escape_filter: Any = None
_main_window: Any = None

_REASON_MESSAGES = {
    "save": "Cleared mate rendering before document save.\n",
    "escape": "Mate rendering cancelled (Escape).\n",
    "document_closed": "Cleared mate rendering (document closed).\n",
}


def _get_command() -> Any:
    from ..command import get_command

    return get_command()


def _qt_core() -> Any:
    try:
        from PySide import QtCore
    except ImportError:
        try:
            from PySide2 import QtCore
        except ImportError:
            from PySide6 import QtCore
    return QtCore


def _escape_key_filter_class(QtCore: Any) -> type:
    class _EscapeKeyFilter(QtCore.QObject):
        """Qt event filter: Escape ends selection or result display."""

        def __init__(
            self, command_getter: Callable[[], Any] = _get_command, parent: Any = None
        ) -> None:
            super().__init__(parent)
            self._command_getter = command_getter

        def eventFilter(self, watched: Any, event: Any) -> bool:
            if event.type() != QtCore.QEvent.KeyPress:
                return False
            if event.key() != QtCore.Qt.Key_Escape:
                return False
            command = self._command_getter()
            if command._phase not in (CommandPhase.SELECTION, CommandPhase.DISPLAY):
                return False
            command.teardown_rendering("escape")
            return True

    return _EscapeKeyFilter


def install_escape_filter(command_getter: Callable[[], Any] = _get_command) -> None:
    global _escape_filter, _main_window
    uninstall_escape_filter()
    try:
        import FreeCADGui
    except ImportError:
        return
    QtCore = _qt_core()
    window = FreeCADGui.getMainWindow()
    if window is None:
        return
    filter_cls = _escape_key_filter_class(QtCore)
    _escape_filter = filter_cls(command_getter)
    window.installEventFilter(_escape_filter)
    _main_window = window


def uninstall_escape_filter() -> None:
    global _escape_filter, _main_window
    if _escape_filter is None or _main_window is None:
        _escape_filter = None
        _main_window = None
        return
    try:
        _main_window.removeEventFilter(_escape_filter)
    except Exception:
        pass
    _escape_filter = None
    _main_window = None


class _AppDocumentObserver:
    def slotStartSaveDocument(self, doc: Any, _filename: str) -> None:
        RenderLifecycle.on_document_save_start(doc)

    def slotDeletedDocument(self, doc: Any) -> None:
        RenderLifecycle.on_document_closed(doc)


class _GuiDocumentObserver:
    def slotDeletedDocument(self, doc: Any) -> None:
        RenderLifecycle.on_document_closed(doc)


class RenderLifecycle:
    """Bridge FreeCAD events to command teardown (injectable for tests)."""

    _command_getter: Callable[[], Any] = _get_command

    @classmethod
    def configure(cls, command_getter: Callable[[], Any]) -> None:
        cls._command_getter = command_getter

    @classmethod
    def on_document_save_start(cls, doc: Any) -> None:
        command = cls._command_getter()
        if not cls._should_teardown(command, doc):
            return
        command.teardown_rendering("save")

    @classmethod
    def on_document_closed(cls, doc: Any) -> None:
        command = cls._command_getter()
        if not cls._should_teardown(command, doc):
            return
        command.teardown_rendering("document_closed")

    @classmethod
    def _should_teardown(cls, command: Any, doc: Any) -> bool:
        renderer = command._renderer
        if getattr(renderer, "is_active", lambda: False)():
            return True
        context = command._context
        if context is not None and str(getattr(doc, "Name", "")) == context.document_name:
            if command._phase in (CommandPhase.SELECTION, CommandPhase.DISPLAY):
                return True
        return False


def register_render_lifecycle() -> None:
    global _lifecycle_registered
    if _lifecycle_registered:
        return
    try:
        import FreeCAD
        import FreeCADGui
    except ImportError:
        return
    FreeCAD.addDocumentObserver(_AppDocumentObserver())
    FreeCADGui.addDocumentObserver(_GuiDocumentObserver())
    _lifecycle_registered = True
