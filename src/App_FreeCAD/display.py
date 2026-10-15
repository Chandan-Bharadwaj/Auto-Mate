"""Display result groups in FreeCAD and highlight their faces."""

from __future__ import annotations

from typing import Any, Sequence

from MateCore.context import DocumentContext, RecognitionRequest, SurfaceRef
from MateCore.mate_report import build_mate_report, format_mate_report
from MateCore.trace import MODULE_REPORT, TRACE_DEEP, TRACE_HIGH, trace_at_least

from .rendering import ResultRenderer, build_render_plan, legend_lines


def display_results(
    freecad: Any,
    freecad_gui: Any,
    context: DocumentContext,
    groups: Sequence[Sequence[SurfaceRef]],
    renderer: ResultRenderer | None = None,
) -> None:
    verbose = trace_at_least(MODULE_REPORT, TRACE_DEEP)
    if verbose:
        parts = [obj for obj in context.objects if obj.kind == "part"]
        assemblies = [obj for obj in context.objects if obj.kind == "assembly"]
        freecad.Console.PrintMessage(
            f"Document '{context.document_name}': "
            f"{len(parts)} part-like object(s), "
            f"{len(assemblies)} assembly object(s), "
            f"{len(context.objects)} document object(s).\n"
        )
        for obj in context.objects:
            if obj.kind in {"part", "assembly"}:
                freecad.Console.PrintMessage(
                    f"  {obj.kind}: {obj.label} ({obj.name}, {obj.type_id})\n"
                )

        freecad.Console.PrintMessage(
            f"Display phase: {len(groups)} result part(s) to highlight.\n"
            "Matched faces only are drawn as overlays; part transparency tints the "
            "whole object in the tree view.\n"
        )
        for group_number, group in enumerate(groups, start=1):
            labels = [
                f"{surface.object_label}.{surface.face_name}" for surface in group
            ]
            owner_name = group[0].object_name if group else "?"
            total_faces = next(
                (
                    len(obj.faces)
                    for obj in context.objects
                    if obj.name == owner_name
                ),
                None,
            )
            if total_faces is not None:
                count_detail = (
                    f" ({len(group)} matched of {total_faces} faces on object)"
                )
            else:
                count_detail = f" ({len(group)} matched face(s))"
            freecad.Console.PrintMessage(
                f"  Part {group_number}{count_detail}: {', '.join(labels)}\n"
            )

    freecad_gui.Selection.clearSelection()
    if renderer is not None:
        plan = build_render_plan(groups, renderer.style)
        if verbose:
            for line in legend_lines(plan):
                freecad.Console.PrintMessage(f"{line}\n")
        renderer.render(plan)
        return

    highlighted: set[tuple[str, str]] = set()
    for group in groups:
        for surface in group:
            key = (surface.object_name, surface.face_name)
            if key not in highlighted:
                freecad_gui.Selection.addSelection(surface.owner, surface.face_name)
                highlighted.add(key)


def display_part_results(
    freecad: Any,
    freecad_gui: Any,
    context: DocumentContext,
    result: Any,
    renderer: ResultRenderer | None = None,
    request: RecognitionRequest | None = None,
) -> None:
    """Report candidate parts best-first, then highlight the matched faces."""
    parts = result.part_matches
    freecad.Console.PrintMessage(f"Display phase: {len(parts)} mating part(s).\n")
    if trace_at_least(MODULE_REPORT, TRACE_HIGH) and request is not None:
        for line in format_mate_report(build_mate_report(request, result)):
            freecad.Console.PrintMessage(f"{line}\n")
    for rank, part in enumerate(parts, start=1):
        fits = sorted(
            {c for m in part.matches for c in m.metadata.get("fit_classes", [])}
        )
        detail = f", fits: {', '.join(fits)}" if fits else ""
        freecad.Console.PrintMessage(
            f"  {rank}. {part.part_name}: {len(part.matches)} configuration(s), "
            f"score {part.score:.3f}{detail}\n"
        )
    rejected_count = len(result.rejected_parts)
    if rejected_count:
        if trace_at_least(MODULE_REPORT, TRACE_HIGH):
            freecad.Console.PrintMessage(
                f"  {rejected_count} part(s) rejected "
                "(see mating report for details).\n"
            )
        else:
            freecad.Console.PrintMessage(
                f"  {rejected_count} part(s) did not mate.\n"
            )
    for message in result.warnings:
        freecad.Console.PrintWarning(f"{message}\n")
    display_results(freecad, freecad_gui, context, result.as_part_surface_groups(), renderer)
