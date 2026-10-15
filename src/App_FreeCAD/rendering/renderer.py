"""FreeCAD renderer: bright overlay for matched faces, transparent owning parts."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from MateCore.rendering.plan import RenderPlan
from MateCore.rendering.style import DEFAULT_STYLE, RenderStyle

from .overlay_geometry import tessellate_surface_global


class ResultRenderer(Protocol):
    @property
    def style(self) -> RenderStyle: ...

    def render(self, plan: RenderPlan) -> None: ...

    def clear(self) -> None: ...

    def is_active(self) -> bool: ...

    def teardown(self) -> None: ...


def facets_to_coord_index(facets: Any) -> list[int]:
    """Flatten triangles into Coin's -1 terminated index list."""
    flat: list[int] = []
    for facet in facets:
        flat.extend(int(i) for i in facet)
        flat.append(-1)
    return flat


class FreeCADResultRenderer:
    def __init__(
        self,
        freecad_gui: Any,
        style_provider: Callable[[], RenderStyle] | None = None,
        coin: Any = None,
    ) -> None:
        self._gui = freecad_gui
        self._style_provider = style_provider or (lambda: DEFAULT_STYLE)
        self._coin = coin
        self._saved_parts: list[tuple[Any, dict[str, Any]]] = []
        self._nodes: list[Any] = []
        self._scenegraph: Any = None
        self._last_plan: RenderPlan | None = None

    @property
    def style(self) -> RenderStyle:
        return self._style_provider()

    def render(self, plan: RenderPlan) -> None:
        self.clear()
        self._ghost_parts(plan)
        try:
            self._draw_surfaces(plan)
        except Exception:
            self.clear()
            self._select_fallback(plan)
            return
        self._last_plan = plan
        self.refresh_display()

    def is_active(self) -> bool:
        return bool(self._saved_parts or self._nodes)

    def teardown(self) -> None:
        self.clear()
        self._last_plan = None

    def clear(self) -> None:
        for view, saved in reversed(self._saved_parts):
            for name, value in saved.items():
                try:
                    setattr(view, name, value)
                except Exception:
                    pass
        self._saved_parts = []
        self._remove_nodes()
        self.refresh_display()

    def refresh_display(self) -> None:
        try:
            self._gui.updateGui()
        except Exception:
            pass
        try:
            document = self._gui.ActiveDocument
            if document is None:
                return
            for view in self._gui.getViews(document.Name):
                redraw = getattr(view, "redraw", None)
                if callable(redraw):
                    redraw()
        except Exception:
            pass

    def _ghost_parts(self, plan: RenderPlan) -> None:
        style = plan.style
        for owner in plan.part_owners:
            view = getattr(owner, "ViewObject", None)
            if view is None:
                continue
            saved: dict[str, Any] = {}
            try:
                saved["Transparency"] = view.Transparency
                view.Transparency = style.part_transparency
                if style.part_tint is not None:
                    saved["ShapeColor"] = view.ShapeColor
                    view.ShapeColor = style.part_tint
            except Exception:
                pass
            if saved:
                self._saved_parts.append((view, saved))

    def _draw_surfaces(self, plan: RenderPlan) -> None:
        coin = self._coin
        if coin is None:
            import pivy.coin as coin  # noqa: PLC0415
        self._scenegraph = self._gui.ActiveDocument.ActiveView.getSceneGraph()
        style = plan.style
        for group in plan.groups:
            for surface in group.surfaces:
                vertices, facets = tessellate_surface_global(
                    surface, style.tessellation_tolerance
                )
                if not facets:
                    continue
                root = coin.SoSeparator()
                material = coin.SoMaterial()
                material.diffuseColor = group.color
                material.emissiveColor = group.color
                material.transparency = style.surface_transparency / 100.0
                offset = coin.SoPolygonOffset()
                offset.factor = -2.0
                offset.units = -2.0
                points = coin.SoCoordinate3()
                points.point.setValues(0, len(vertices), vertices)
                indices = facets_to_coord_index(facets)
                face_set = coin.SoIndexedFaceSet()
                face_set.coordIndex.setValues(0, len(indices), indices)
                for node in (material, offset, points, face_set):
                    root.addChild(node)
                self._scenegraph.addChild(root)
                self._nodes.append(root)

    def _scene_graph_candidates(self) -> list[Any]:
        graphs: list[Any] = []
        if self._scenegraph is not None:
            graphs.append(self._scenegraph)
        try:
            graphs.append(self._gui.ActiveDocument.ActiveView.getSceneGraph())
        except Exception:
            pass
        unique: list[Any] = []
        seen: set[int] = set()
        for graph in graphs:
            key = id(graph)
            if key not in seen:
                seen.add(key)
                unique.append(graph)
        return unique

    def _remove_nodes(self) -> None:
        for node in list(self._nodes):
            for graph in self._scene_graph_candidates():
                try:
                    graph.removeChild(node)
                except Exception:
                    continue
        self._nodes = []
        self._scenegraph = None

    def _select_fallback(self, plan: RenderPlan) -> None:
        selection = self._gui.Selection
        selection.clearSelection()
        for group in plan.groups:
            for surface in group.surfaces:
                selection.addSelection(surface.owner, surface.face_name)
