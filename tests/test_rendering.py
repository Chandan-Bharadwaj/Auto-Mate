from types import SimpleNamespace

import pytest

from App_FreeCAD.rendering.renderer import FreeCADResultRenderer, facets_to_coord_index
from MateCore.rendering import RenderStyle, build_render_plan, legend_lines
from MateCore.rendering.style import brighten, style_from_mapping


def face(obj, name, tess=None):
    view = SimpleNamespace(Transparency=0, ShapeColor=(0.5, 0.5, 0.5))
    owner = SimpleNamespace(ViewObject=view) if not hasattr(obj, "owner") else obj.owner
    return SimpleNamespace(
        object_name=obj, object_label=obj.upper(), face_name=name, owner=owner,
        shape=SimpleNamespace(tessellate=lambda tol: tess or ([], [])),
    )


def test_plan_uses_highlight_color_and_dedupes_faces():
    style = RenderStyle(highlight_color=(0.15, 1.0, 0.25))
    a1, a2, b1 = face("a", "Face1"), face("a", "Face2"), face("b", "Face1")
    b1.owner = a1.owner
    plan = build_render_plan([[a1, a2], [a1], [b1]], style)
    assert [g.color for g in plan.groups] == [style.highlight_color] * 3
    assert plan.groups[1].surfaces == ()
    assert len(plan.part_owners) == 2
    assert len(legend_lines(plan)) == 3


def test_style_validation_and_overrides():
    with pytest.raises(ValueError):
        RenderStyle(part_transparency=101)
    assert style_from_mapping({"part_transparency": "40"}).part_transparency == 40
    assert style_from_mapping({"part_transparency": 500}).part_transparency == 70
    assert brighten((0.8, 0.5, 0.1), 2.0) == (1.0, 1.0, 0.2)


def test_coord_index():
    assert facets_to_coord_index([(0, 1, 2), (2, 1, 3)]) == [0, 1, 2, -1, 2, 1, 3, -1]


class FakeNode:
    def __init__(self):
        self.children = []
        self.point = SimpleNamespace(setValues=lambda *a: None)
        self.coordIndex = SimpleNamespace(setValues=lambda *a: None)

    def addChild(self, node):
        self.children.append(node)

    def removeChild(self, node):
        self.children.remove(node)


def fake_gui():
    graph = FakeNode()
    gui = SimpleNamespace(
        ActiveDocument=SimpleNamespace(ActiveView=SimpleNamespace(getSceneGraph=lambda: graph)),
        Selection=SimpleNamespace(
            added=[], clearSelection=lambda: None,
            addSelection=lambda *a: gui.Selection.added.append(a),
        ),
    )
    return gui, graph


COIN = SimpleNamespace(
    SoSeparator=FakeNode, SoMaterial=FakeNode, SoPolygonOffset=FakeNode,
    SoCoordinate3=FakeNode, SoIndexedFaceSet=FakeNode,
)
V = SimpleNamespace(x=0, y=0, z=0)


def test_renderer_is_active_and_teardown_clears_last_plan():
    gui, graph = fake_gui()
    f = face("a", "Face1", ([V, V, V], [(0, 1, 2)]))
    plan = build_render_plan([[f]], RenderStyle())
    renderer = FreeCADResultRenderer(gui, coin=COIN)
    assert not renderer.is_active()
    renderer.render(plan)
    assert renderer.is_active()
    assert renderer._last_plan is plan
    renderer.teardown()
    assert not renderer.is_active()
    assert renderer._last_plan is None


def test_renderer_ghosts_parts_draws_and_restores():
    gui, graph = fake_gui()
    f = face("a", "Face1", ([V, V, V], [(0, 1, 2)]))
    tint = (0.15, 1.0, 0.25)
    plan = build_render_plan(
        [[f]], RenderStyle(part_transparency=80, part_tint=tint)
    )
    renderer = FreeCADResultRenderer(gui, coin=COIN)
    renderer.render(plan)
    assert f.owner.ViewObject.Transparency == 80
    assert f.owner.ViewObject.ShapeColor == tint
    assert len(graph.children) == 1
    renderer.clear()
    renderer.clear()
    assert f.owner.ViewObject.Transparency == 0
    assert graph.children == []


def test_renderer_falls_back_to_selection():
    gui, graph = fake_gui()
    f = face("a", "Face1", ([V], [(0, 0, 0)]))
    broken = SimpleNamespace(SoSeparator=lambda: 1 / 0)
    plan = build_render_plan([[f]], RenderStyle(part_tint=(0.2, 1, 0.2)))
    FreeCADResultRenderer(gui, coin=broken).render(plan)
    assert gui.Selection.added == [(f.owner, "Face1")]
    assert f.owner.ViewObject.Transparency == 0
    assert f.owner.ViewObject.ShapeColor == (0.5, 0.5, 0.5)
