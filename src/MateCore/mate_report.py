"""Mating result report: per-mate surface pairings and matching reasons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from MateCore.algorithm import AlgorithmResult, Match
from MateCore.context import RecognitionRequest, SurfaceRef
from MateCore.MateFit.fits import FitResult


def _face_key(ref: SurfaceRef) -> tuple[str, str]:
    return ref.object_name, ref.face_name


def _label(ref: SurfaceRef) -> str:
    return f"{ref.object_label}.{ref.face_name}"


def surface_pairings(
    match: Match,
) -> list[tuple[SurfaceRef, SurfaceRef, int]]:
    """Map source-side faces to candidate faces; third item is pair index in ``match.pairs``."""
    pairs = getattr(match, "pairs", None)
    if not pairs:
        return []
    rows: list[tuple[SurfaceRef, SurfaceRef, int]] = []
    for index, (src_refs, cand_refs) in enumerate(pairs):
        src_list = [r for r in src_refs if isinstance(r, SurfaceRef)]
        cand_list = [r for r in cand_refs if isinstance(r, SurfaceRef)]
        if not src_list or not cand_list:
            continue
        if len(src_list) == len(cand_list):
            for src, cand in zip(src_list, cand_list):
                rows.append((src, cand, index))
        elif len(src_list) == 1:
            for cand in cand_list:
                rows.append((src_list[0], cand, index))
        elif len(cand_list) == 1:
            for src in src_list:
                rows.append((src, cand_list[0], index))
        else:
            for src, cand in zip(src_list, cand_list):
                rows.append((src, cand, index))
    return rows


def _fit_at_index(match: Match, pair_index: int) -> FitResult | None:
    fits: Sequence[Any] = getattr(match, "fits", ()) or ()
    if pair_index < len(fits):
        item = fits[pair_index]
        if isinstance(item, FitResult):
            return item
    return None


def _fit_class_at_index(match: Match, pair_index: int) -> str | None:
    fit = _fit_at_index(match, pair_index)
    if fit is not None:
        return fit.fit_class
    meta = getattr(match, "metadata", None) or {}
    classes = meta.get("fit_classes")
    if isinstance(classes, Sequence) and pair_index < len(classes):
        return str(classes[pair_index])
    return None


def pairing_reason(match: Match, pair_index: int) -> str:
    """Human-readable explanation for one pairing index."""
    parts: list[str] = ["graph correspondence"]
    meta = getattr(match, "metadata", None) or {}
    if meta.get("graph_alignment_score") is not None:
        parts.append(f"alignment_score={float(meta['graph_alignment_score']):.4f}")
    if meta.get("pose_residual") is not None:
        parts.append(f"pose_residual={float(meta['pose_residual']):.4f}")

    fit = _fit_at_index(match, pair_index)
    if fit is not None:
        parts.append(f"fit: {fit.fit_class}")
        parts.append(f"gap={fit.gap:.4g} mm")
        parts.append(f"ok={fit.ok}")
    else:
        fit_class = _fit_class_at_index(match, pair_index)
        if fit_class:
            parts.append(f"fit: {fit_class}")
        else:
            parts.append("fit: (not assessed)")

    kind = getattr(match, "mate_configuration_kind", None)
    if kind is None:
        kind = meta.get("mate_configuration_kind")
    if kind:
        parts.append(f"configuration: {kind}")

    return "; ".join(parts)


def _config_context(match: Match) -> str:
    meta = getattr(match, "metadata", None) or {}
    bits: list[str] = []
    if meta.get("axis_aligned") is True:
        bits.append("axis_aligned")
    elif meta.get("axis_aligned") is False:
        bits.append("axis_not_aligned")
    warnings = meta.get("warnings")
    if warnings:
        bits.append(f"warnings={warnings}")
    if meta.get("nominal_fit_gap_mm") is not None:
        bits.append(f"nominal_gap_mm={meta['nominal_fit_gap_mm']}")
    return "; ".join(bits)


@dataclass(frozen=True, slots=True)
class SurfacePairingRow:
    source_label: str
    mate_label: str
    fit_class: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ConfigurationPairing:
    configuration_index: int
    score: float
    dof: int
    pairings: tuple[SurfacePairingRow, ...]
    mate_configuration_kind: str | None = None
    context: str = ""


@dataclass(frozen=True, slots=True)
class PartMateView:
    rank: int
    part_id: str
    part_name: str
    part_score: float
    configurations: tuple[ConfigurationPairing, ...]


@dataclass(frozen=True, slots=True)
class MateReport:
    source_part_name: str | None
    selected_surfaces: tuple[str, ...]
    parts: tuple[PartMateView, ...]
    rejected: tuple[tuple[str, str], ...]
    timings: dict[str, float]


def build_mate_report(request: RecognitionRequest, result: AlgorithmResult) -> MateReport:
    source = request.context.get_part_for_face(request.surfaces[0]) if request.surfaces else None
    selected_labels = tuple(_label(s) for s in request.surfaces)
    selected_keys = {_face_key(s) for s in request.surfaces}

    part_views: list[PartMateView] = []
    for rank, part in enumerate(result.part_matches, start=1):
        configs: list[ConfigurationPairing] = []
        for cfg_index, match in enumerate(part.matches, start=1):
            raw = surface_pairings(match)
            pair_rows: list[SurfacePairingRow] = []
            for src, cand, pair_index in raw:
                if _face_key(src) in selected_keys or not selected_keys:
                    pair_rows.append(
                        SurfacePairingRow(
                            source_label=_label(src),
                            mate_label=_label(cand),
                            fit_class=_fit_class_at_index(match, pair_index),
                            reason=pairing_reason(match, pair_index),
                        )
                    )
            if not pair_rows and match.faces:
                for face in match.faces:
                    pair_rows.append(
                        SurfacePairingRow(
                            source_label="?",
                            mate_label=_label(face),
                            fit_class=None,
                            reason="mate faces (pairing not recorded)",
                        )
                    )
            dof = int(getattr(match, "dof", 0))
            kind = getattr(match, "mate_configuration_kind", None)
            if kind is None and getattr(match, "metadata", None):
                kind = match.metadata.get("mate_configuration_kind")
            configs.append(
                ConfigurationPairing(
                    configuration_index=cfg_index,
                    score=float(match.score),
                    dof=dof,
                    pairings=tuple(pair_rows),
                    mate_configuration_kind=kind,
                    context=_config_context(match),
                )
            )
        part_views.append(
            PartMateView(
                rank=rank,
                part_id=part.part_id,
                part_name=part.part_name,
                part_score=float(part.score),
                configurations=tuple(configs),
            )
        )

    rejected = tuple((r.part_name, r.reason) for r in result.rejected_parts)
    return MateReport(
        source_part_name=source.name if source else None,
        selected_surfaces=selected_labels,
        parts=tuple(part_views),
        rejected=rejected,
        timings=dict(result.timings),
    )


def format_mate_report(report: MateReport) -> list[str]:
    lines = ["=== Auto-Mate mating report ==="]
    if report.source_part_name:
        lines.append(
            f"Source part: {report.source_part_name} "
            f"({len(report.selected_surfaces)} selected surface(s))"
        )
    if report.selected_surfaces:
        lines.append("  Selection: " + ", ".join(report.selected_surfaces))
    if report.timings:
        timing = ", ".join(f"{k}={v:.3f}s" for k, v in sorted(report.timings.items()))
        lines.append(f"Timings: {timing}")
    if not report.parts:
        lines.append("Mating parts: (none)")
    for part in report.parts:
        lines.append(
            f"--- Mate #{part.rank}: {part.part_name} ({part.part_id}) "
            f"score {part.part_score:.3f} ---"
        )
        for cfg in part.configurations:
            kind_txt = (
                f", kind {cfg.mate_configuration_kind}"
                if cfg.mate_configuration_kind
                else ""
            )
            lines.append(
                f"  Config {cfg.configuration_index}: score {cfg.score:.3f}, "
                f"dof {cfg.dof}{kind_txt}"
            )
            if cfg.context:
                lines.append(f"    Context: {cfg.context}")
            if not cfg.pairings:
                lines.append("    (no surface pairings recorded)")
            for row in cfg.pairings:
                fit_txt = f" [{row.fit_class}]" if row.fit_class else ""
                lines.append(f"    {row.source_label}  ->  {row.mate_label}{fit_txt}")
                lines.append(f"      reason: {row.reason}")
    if report.rejected:
        lines.append(f"Rejected ({len(report.rejected)}):")
        for name, reason in report.rejected:
            lines.append(f"  - {name}: {reason}")
    lines.append("=== end mating report ===")
    return lines
