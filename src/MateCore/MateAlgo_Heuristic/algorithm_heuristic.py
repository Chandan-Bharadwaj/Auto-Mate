"""Heuristic graph-pattern mate search: MateGraph alignment + shared pose/fit."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Callable, Sequence

from MateCore.algorithm import (
    AlgorithmConfig,
    Match,
    MateAlgorithm,
    RunContext,
)
from MateCore.context import PartContext, RecognitionRequest, SurfaceRef
from MateCore.MateFit.descriptors import CONE, CYLINDER, PLANE
from MateCore.MateGraph.node_adapter import node_to_face_descriptor
from MateCore.MateFit import FitResolver
from MateCore.MateFit.assessment import assess_pairs
from MateCore.MateFit.fits import FitResult
from MateCore.MateGraph.metadata_requirements import PatternMetadataRequirements
from MateCore.MateGraph.metadata_store import PartMetadataStore
from MateCore.MateGraph.model import PartGraph
from MateCore.MateGraph.search import extract_pattern_from_refs, run_search
from MateCore.MateGraph.search.flank_index import annotate_flank_topology
from MateCore.postprocessors import DedupeByFaceSet, ScoreRanker
from MateCore.trace import (
    MODULE_HEURISTIC,
    TRACE_DEEP,
    TRACE_HIGH,
    TRACE_VERBOSE,
    trace_at_least,
    trace_emit,
    trace_milestone,
    trace_span,
)

from .axis_alignment import pattern_axis_alignment
from .config import HeuristicMateConfig
from .enrich import apply_enricher
from .fit_policy import (
    build_heuristic_fit_resolver,
    effective_nominal_gap_mm,
    summarize_mate_fit,
)
from .metadata_predicate import MatingMetadataPredicate
from .policy import MatingAlignmentSearchPolicy
from .transform import mating_search_pattern
from .validation import evaluate_pose_and_fit

PartGraphProvider = Callable[[PartContext], PartGraph]


@dataclass(frozen=True, slots=True)
class HeuristicMatch(Match):
    pairs: tuple[tuple[tuple[SurfaceRef, ...], tuple[SurfaceRef, ...]], ...] = ()
    rotation: tuple[tuple[float, ...], ...] = ()
    translation: tuple[float, ...] = ()
    dof: int = 0
    fits: tuple[FitResult, ...] = field(default=())
    mate_configuration_kind: str | None = None


@dataclass(slots=True)
class _Prepared:
    request: RecognitionRequest
    source_graph: PartGraph
    search_pattern: object
    metadata_predicate: MatingMetadataPredicate
    source_part_id: str
    policy: MatingAlignmentSearchPolicy
    mate_config: HeuristicMateConfig
    axis_alignment: object = None
    fit_resolver: FitResolver | None = None


class MateAlgorithm_Heuristic(MateAlgorithm):
    name = "mate-algorithm-heuristic"
    supported_surface_kinds = (PLANE, CYLINDER, CONE)
    single_source_part = True

    def __init__(
        self,
        graph_provider: PartGraphProvider,
        metadata_store: PartMetadataStore | None = None,
        resolver: FitResolver | None = None,
        config: AlgorithmConfig | None = None,
        *,
        mate_config: HeuristicMateConfig | None = None,
        max_alignments_per_part: int = 16,
    ) -> None:
        super().__init__(config)
        self._graph_for = graph_provider
        self._metadata_store = metadata_store
        self.resolver = resolver or FitResolver()
        self._mate_config = mate_config or HeuristicMateConfig()
        self._max_align = max_alignments_per_part
        self.add_postprocessor(DedupeByFaceSet())
        self.set_ranker(ScoreRanker())

    def _build_policy(
        self, source_part_id: str, fit_resolver: FitResolver
    ) -> MatingAlignmentSearchPolicy:
        cfg = self._mate_config
        if cfg.topology_profile == "coarse":
            return MatingAlignmentSearchPolicy.coarse_topology(
                fit_resolver,
                source_part_id,
                max_candidates=self._max_align,
                len_tol=fit_resolver.policy.default.tolerance.abs_len,
                angle_tol=fit_resolver.angle_tolerance,
                flank_spacing_rel_tol=cfg.flank_spacing_rel_tol,
                hub_node_weight=cfg.hub_node_weight,
                plane_shape_reject_floor=cfg.plane_shape_reject_floor,
                plane_shape_penalty_exponent=cfg.plane_shape_penalty_exponent,
            )
        return MatingAlignmentSearchPolicy(
            fit_resolver,
            source_part_id,
            max_candidates=self._max_align,
            len_tol=fit_resolver.policy.default.tolerance.abs_len,
            angle_tol=fit_resolver.angle_tolerance,
            flank_spacing_rel_tol=cfg.flank_spacing_rel_tol,
            hub_node_weight=cfg.hub_node_weight,
            plane_shape_reject_floor=cfg.plane_shape_reject_floor,
            plane_shape_penalty_exponent=cfg.plane_shape_penalty_exponent,
        )

    def prepare(self, request: RecognitionRequest, run: RunContext) -> _Prepared:
        sel_part = request.context.get_part_for_face(request.surfaces[0])
        if sel_part is None:
            raise ValueError("Selected surfaces must belong to a known part")
        ctx = (
            trace_span(MODULE_HEURISTIC, "prepare", min_level=TRACE_HIGH)
            if trace_at_least(MODULE_HEURISTIC, TRACE_HIGH)
            else nullcontext()
        )
        mate_cfg = self._mate_config
        with ctx:
            source_graph = self._graph_for(sel_part)
            reference = extract_pattern_from_refs(source_graph, request.surfaces)
            reference = apply_enricher(
                source_graph, reference, mate_cfg.enricher
            )
            reference = annotate_flank_topology(
                reference,
                angle_tol=self.resolver.angle_tolerance,
                hub_node_weight=mate_cfg.hub_node_weight,
            )
            search_pattern = mating_search_pattern(reference)
        trace_milestone(
            MODULE_HEURISTIC,
            "prepare",
            context={
                "source_part": sel_part.part_id,
                "slots": len(search_pattern.slots),
                "edges": len(search_pattern.edges),
                "topology_profile": mate_cfg.topology_profile,
            },
        )
        if trace_at_least(MODULE_HEURISTIC, TRACE_HIGH):
            trace_emit(
                MODULE_HEURISTIC,
                f"source part={sel_part.part_id} slots={len(search_pattern.slots)} "
                f"edges={len(search_pattern.edges)}",
                min_level=TRACE_HIGH,
            )
        if trace_at_least(MODULE_HEURISTIC, TRACE_DEEP):
            trace_emit(
                MODULE_HEURISTIC,
                f"enricher={mate_cfg.enricher} topology={mate_cfg.topology_profile} "
                f"max_align={self._max_align} fit_validation={mate_cfg.fit_validation} "
                f"pose_validation={mate_cfg.pose_validation}",
                min_level=TRACE_DEEP,
            )
        requirements = PatternMetadataRequirements.from_pattern(search_pattern)
        axis_alignment = pattern_axis_alignment(
            search_pattern, self.resolver.angle_tolerance
        )
        fit_resolver = build_heuristic_fit_resolver(
            mate_cfg, axis_alignment, self.resolver, search_pattern
        )
        policy = self._build_policy(sel_part.part_id, fit_resolver)
        if trace_at_least(MODULE_HEURISTIC, TRACE_HIGH):
            trace_emit(
                MODULE_HEURISTIC,
                f"axis_aligned={axis_alignment.axis_aligned} "
                f"max_misalign_rad={axis_alignment.max_misalignment_rad:.4f} "
                f"nominal_gap_mm={effective_nominal_gap_mm(mate_cfg, axis_alignment, search_pattern)}",
                min_level=TRACE_HIGH,
            )
        return _Prepared(
            request,
            source_graph,
            search_pattern,
            MatingMetadataPredicate(requirements),
            sel_part.part_id,
            policy,
            mate_cfg,
            axis_alignment=axis_alignment,
            fit_resolver=fit_resolver,
        )

    def candidate_parts(
        self, state: _Prepared, query, run: RunContext
    ) -> Sequence[PartContext]:
        parts = list(super().candidate_parts(state, query, run))
        store = self._metadata_store
        if store is None:
            return parts
        before = len(parts)
        trace_milestone(
            MODULE_HEURISTIC,
            "metadata_filter",
            context={"candidates_before": before},
        )
        filtered: list[PartContext] = []
        verbose = trace_at_least(MODULE_HEURISTIC, TRACE_VERBOSE)
        for part in parts:
            meta = store.get(part)
            if state.metadata_predicate.accept(meta):
                filtered.append(part)
            elif verbose:
                trace_emit(
                    MODULE_HEURISTIC,
                    f"metadata reject part={part.part_id}",
                    min_level=TRACE_VERBOSE,
                )
        if trace_at_least(MODULE_HEURISTIC, TRACE_HIGH):
            trace_emit(
                MODULE_HEURISTIC,
                f"metadata filter candidates {before} -> {len(filtered)}",
                min_level=TRACE_HIGH,
            )
        return filtered

    def match_part(
        self, state: _Prepared, part: PartContext, run: RunContext
    ) -> Sequence[Match]:
        ctx = (
            trace_span(MODULE_HEURISTIC, f"match_part {part.part_id}", min_level=TRACE_HIGH)
            if trace_at_least(MODULE_HEURISTIC, TRACE_HIGH)
            else nullcontext()
        )
        with ctx:
            return self._match_part_inner(state, part, run)

    def _match_part_inner(
        self, state: _Prepared, part: PartContext, run: RunContext
    ) -> Sequence[Match]:
        trace_milestone(
            MODULE_HEURISTIC,
            "match_part",
            context={
                "source_part": state.source_part_id,
                "target_part": part.part_id,
                "slots": len(state.search_pattern.slots),
            },
        )
        target = self._graph_for(part)
        if not target.nodes:
            run.explain(part.part_id, "no faces in part graph")
            return []

        policy = state.policy.with_search_context(state.search_pattern, target)
        result = run_search(state.search_pattern, target, policy)
        if not result.candidates:
            run.explain(part.part_id, "no graph alignment for selection signature")
            return []

        found: list[Match] = []
        pattern = state.search_pattern
        n_slots = len(pattern.slots)
        mate_cfg = state.mate_config
        warn_accepts = 0
        strict_accepts = 0

        verbose = trace_at_least(MODULE_HEURISTIC, TRACE_VERBOSE)
        for align_index, scored in enumerate(
            result.candidates[: self._max_align], start=1
        ):
            mapping = scored.alignment.as_dict()
            if len(mapping) != n_slots:
                if verbose:
                    trace_emit(
                        MODULE_HEURISTIC,
                        f"{part.part_id} align#{align_index} skip incomplete mapping "
                        f"{len(mapping)}/{n_slots}",
                        min_level=TRACE_VERBOSE,
                    )
                continue
            if verbose:
                trace_emit(
                    MODULE_HEURISTIC,
                    f"{part.part_id} align#{align_index} score={scored.score.total:.4f} "
                    f"mapping={mapping}",
                    min_level=TRACE_VERBOSE,
                )
            pairs_desc: list = []
            pair_refs: list[tuple[tuple[SurfaceRef, ...], tuple[SurfaceRef, ...]]] = []
            faces: list[SurfaceRef] = []

            for slot_id, target_nid in mapping.items():
                slot = pattern.slot(slot_id)
                if slot is None:
                    continue
                src_node = state.source_graph.node(slot.source_node_id)
                tgt_node = target.node(target_nid)
                if src_node is None or tgt_node is None:
                    continue
                sel_desc = node_to_face_descriptor(src_node)
                cand_desc = node_to_face_descriptor(tgt_node)
                if sel_desc is None or cand_desc is None:
                    continue
                pairs_desc.append((sel_desc, cand_desc))
                q_refs = tuple(
                    r
                    for r in (src_node.refs or ((src_node.ref,) if src_node.ref else ()))
                    if r is not None
                )
                t_refs = tuple(
                    r
                    for r in (tgt_node.refs or ((tgt_node.ref,) if tgt_node.ref else ()))
                    if r is not None
                )
                pair_refs.append((q_refs, t_refs))
                for r in t_refs:
                    if r not in faces:
                        faces.append(r)

            if len(pairs_desc) != len(mapping):
                if verbose:
                    trace_emit(
                        MODULE_HEURISTIC,
                        f"{part.part_id} align#{align_index} skip descriptor gap",
                        min_level=TRACE_VERBOSE,
                    )
                continue

            best_match: HeuristicMatch | None = None
            fit_resolver = state.fit_resolver or self.resolver
            for outcome in evaluate_pose_and_fit(
                pairs_desc,
                fit_resolver,
                mate_cfg,
                log_context=f"{part.part_id}/align#{align_index}",
            ):
                if not outcome.accepted:
                    continue
                if outcome.warnings:
                    warn_accepts += 1
                else:
                    strict_accepts += 1
                pose = outcome.pose
                if pose is None and mate_cfg.pose_validation == "skip":
                    score = scored.score.total
                    assessment_fits: tuple[FitResult, ...] = ()
                    kind = None
                    dof = 0
                    rotation = ()
                    translation = ()
                else:
                    if pose is None:
                        continue
                    assessment = outcome.assessment or assess_pairs(
                        pairs_desc, fit_resolver, pose
                    )
                    assessment_fits = assessment.fits
                    fit_summary = summarize_mate_fit(
                        state.axis_alignment,
                        mate_cfg,
                        assessment_fits,
                        state.search_pattern,
                    )
                    kind = fit_summary.configuration_kind
                    score = (
                        scored.score.total / (1.0 + assessment.residual)
                        - 0.01 * pose.dof
                    )
                    dof = pose.dof
                    rotation = tuple(tuple(float(x) for x in row) for row in pose.rotation)
                    translation = tuple(float(x) for x in pose.translation)

                meta = {
                    "fit_classes": [f.fit_class for f in assessment_fits],
                    "pair_gaps": [f.gap for f in assessment_fits],
                    "warnings": list(outcome.warnings),
                    "axis_aligned": state.axis_alignment.axis_aligned,
                    "max_axis_misalignment_rad": state.axis_alignment.max_misalignment_rad,
                    "nominal_fit_gap_mm": effective_nominal_gap_mm(
                        mate_cfg, state.axis_alignment, state.search_pattern
                    ),
                    "graph_alignment_score": scored.score.total,
                }
                if kind is not None:
                    meta["mate_configuration_kind"] = kind.value

                candidate = HeuristicMatch(
                    faces=tuple(faces),
                    score=score,
                    metadata=meta,
                    part_id=part.part_id,
                    pairs=tuple(pair_refs),
                    rotation=rotation,
                    translation=translation,
                    dof=dof,
                    fits=assessment_fits,
                    mate_configuration_kind=kind.value if kind else None,
                )
                if best_match is None or candidate.score > best_match.score:
                    if verbose and best_match is not None:
                        trace_emit(
                            MODULE_HEURISTIC,
                            f"{part.part_id} align#{align_index} replace best "
                            f"{best_match.score:.4f}->{candidate.score:.4f}",
                            min_level=TRACE_VERBOSE,
                        )
                    best_match = candidate
            if best_match is not None:
                found.append(best_match)
            elif verbose:
                trace_emit(
                    MODULE_HEURISTIC,
                    f"{part.part_id} align#{align_index} no accepted pose",
                    min_level=TRACE_VERBOSE,
                )

        if trace_at_least(MODULE_HEURISTIC, TRACE_HIGH):
            trace_emit(
                MODULE_HEURISTIC,
                f"match_part {part.part_id}: alignments={len(result.candidates)} "
                f"matches={len(found)}",
                min_level=TRACE_HIGH,
            )
        if trace_at_least(MODULE_HEURISTIC, TRACE_DEEP):
            trace_emit(
                MODULE_HEURISTIC,
                f"match_part {part.part_id}: pose_outcomes strict={strict_accepts} "
                f"warn={warn_accepts}",
                min_level=TRACE_DEEP,
            )
        if not found:
            run.explain(
                part.part_id,
                "graph aligned but no pose satisfied fit tolerance",
            )
        return found
