from types import SimpleNamespace

from App_FreeCAD.phase_ui import CommandPhase
from App_FreeCAD.rendering.lifecycle import RenderLifecycle


def make_command(phase, active=False, document_name="Doc1"):
    messages: list[str] = []
    renderer = SimpleNamespace(
        is_active=lambda: active,
        teardown=lambda: None,
    )
    context = (
        SimpleNamespace(document_name=document_name) if document_name else None
    )
    command = SimpleNamespace(
        _phase=phase,
        _renderer=renderer,
        _context=context,
        teardown_calls=[],
    )

    def teardown_rendering(reason: str = "") -> None:
        command.teardown_calls.append(reason)

    command.teardown_rendering = teardown_rendering
    return command


def test_save_teardown_when_renderer_active():
    command = make_command(CommandPhase.DISPLAY, active=True)
    RenderLifecycle.configure(lambda: command)
    RenderLifecycle.on_document_save_start(SimpleNamespace(Name="Doc1"))
    assert command.teardown_calls == ["save"]


def test_save_teardown_when_selection_on_same_document():
    command = make_command(CommandPhase.SELECTION, active=False, document_name="Doc1")
    RenderLifecycle.configure(lambda: command)
    RenderLifecycle.on_document_save_start(SimpleNamespace(Name="Doc1"))
    assert command.teardown_calls == ["save"]


def test_save_skipped_when_idle_and_inactive():
    command = make_command(CommandPhase.IDLE, active=False)
    RenderLifecycle.configure(lambda: command)
    RenderLifecycle.on_document_save_start(SimpleNamespace(Name="Doc1"))
    assert command.teardown_calls == []


def test_document_closed_teardown():
    command = make_command(CommandPhase.DISPLAY, active=True)
    RenderLifecycle.configure(lambda: command)
    RenderLifecycle.on_document_closed(SimpleNamespace(Name="Doc1"))
    assert command.teardown_calls == ["document_closed"]
