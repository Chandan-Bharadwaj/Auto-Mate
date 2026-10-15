"""Graph alignment search engine."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from ..model import PartGraph
from .alignment import AlignmentScore, GraphAlignment, ScoredAlignment, SearchResult
from MateCore.trace import (
    MODULE_MATEGRAPH,
    TRACE_DEEP,
    TRACE_VERBOSE,
    trace_at_least,
    trace_duration,
    trace_emit,
    trace_milestone,
)

from .candidates import candidates_for_slot
from .index import TargetIndex
from .pattern import GraphPattern
from .policy import AlignmentSearchPolicy, DefaultSearchPolicy

_VERBOSE_BEAM_CAP = 500


def _score_summary(score: AlignmentScore) -> str:
    return (
        f"total={score.total:.4f} cov={score.coverage:.2f} "
        f"node={score.node_term:.2f} edge={score.edge_term:.2f} pen={score.penalty:.2f}"
    )


def _node_rejection_reason(
    node_cmp: object,
    slot,
    tnode,
    mapping: dict[str, str],
) -> str:
    explain = getattr(node_cmp, "explain_node_rejection", None)
    if explain is not None:
        reason = explain(slot, tnode, mapping)
        if reason:
            return reason
    sim = node_cmp.similarity(slot, tnode, mapping)  # type: ignore[attr-defined]
    if sim is None:
        return "incompatible"
    return ""


class GraphSearcher(Protocol):
    search_protocol_version: int

    def search(
        self,
        pattern: GraphPattern,
        target: PartGraph,
        policy: AlignmentSearchPolicy,
    ) -> SearchResult: ...


def _score_alignment(
    pattern: GraphPattern,
    target: PartGraph,
    mapping: dict[str, str],
    policy: AlignmentSearchPolicy,
) -> AlignmentScore:
    node_cmp = policy.node_comparator()
    edge_cmp = policy.edge_comparator()

    node_sims: list[float] = []
    node_weights: list[float] = []
    anchor_sims: list[float] = []
    weight_fn = getattr(policy, "slot_node_weight", None)
    for slot in pattern.slots:
        tid = mapping.get(slot.slot_id)
        if tid is None:
            continue
        tnode = target.node(tid)
        if tnode is None:
            continue
        sim = node_cmp.similarity(slot, tnode, mapping)
        if sim is not None:
            w = float(weight_fn(slot)) if weight_fn is not None else 1.0
            node_sims.append(sim)
            node_weights.append(w)
            if slot.slot_id in pattern.anchor_slots:
                anchor_sims.append(sim)

    edge_sims: list[float] = []
    missing_edges = 0
    for pe in pattern.edges:
        ta = mapping.get(pe.a)
        tb = mapping.get(pe.b)
        if ta is None or tb is None:
            continue
        te = target.edge_between(ta, tb)
        if te is None:
            missing_edges += 1
            edge_sims.append(0.0)
        else:
            edge_sims.append(edge_cmp.similarity(pe, te))

    n_slots = max(1, len(pattern.slots))
    n_anchors = max(1, len(pattern.anchor_slots))
    mapped = len(mapping)
    mapped_anchors = sum(
        1 for s in pattern.anchor_slots if s in mapping
    )

    coverage = mapped / n_slots
    anchor_coverage = mapped_anchors / n_anchors if pattern.anchor_slots else 1.0

    if node_sims:
        wsum = sum(node_weights)
        node_term = (
            sum(s * w for s, w in zip(node_sims, node_weights)) / wsum
            if wsum > 0
            else sum(node_sims) / len(node_sims)
        )
    else:
        node_term = 0.0
    edge_term = sum(edge_sims) / max(1, len(edge_sims)) if edge_sims else 0.0

    unmapped = len(pattern.slots) - mapped
    unmapped_anchors = len(pattern.anchor_slots) - mapped_anchors
    penalty = (
        unmapped * policy.unmapped_slot_penalty
        + unmapped_anchors * policy.unmapped_anchor_penalty
        + missing_edges * policy.missing_edge_penalty
    )

    total = (
        policy.weight_node * node_term
        + policy.weight_edge * edge_term
        + policy.weight_coverage * coverage
        + policy.weight_anchor_coverage * anchor_coverage
        - penalty
    )

    return AlignmentScore(
        node_term=node_term,
        edge_term=edge_term,
        coverage=coverage,
        anchor_coverage=anchor_coverage,
        penalty=penalty,
        total=total,
    )


@dataclass
class _BeamState:
    mapping: dict[str, str]
    used_targets: set[str]
    depth: int


@dataclass(slots=True)
class BeamGraphSearcher:
    search_protocol_version: int = 1

    def search(
        self,
        pattern: GraphPattern,
        target: PartGraph,
        policy: AlignmentSearchPolicy,
    ) -> SearchResult:
        start = time.monotonic()
        trace_milestone(
            MODULE_MATEGRAPH,
            "alignment_search",
            context={
                "part_id": target.part_id,
                "slots": len(pattern.slots),
                "beam_width": policy.beam_width,
                "max_candidates": policy.max_candidates,
            },
        )
        if trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP):
            trace_emit(
                MODULE_MATEGRAPH,
                f"alignment search slots={len(pattern.slots)} "
                f"beam_width={policy.beam_width} max_candidates={policy.max_candidates}",
                min_level=TRACE_DEEP,
            )
        index = TargetIndex.from_graph(target)
        node_cmp = policy.node_comparator()
        order = policy.slot_order(pattern)
        verbose = trace_at_least(MODULE_MATEGRAPH, TRACE_VERBOSE)

        beam: list[_BeamState] = [_BeamState({}, set(), 0)]
        completed: list[ScoredAlignment] = []
        round_index = 0

        while beam and len(completed) < policy.max_candidates:
            next_beam: list[_BeamState] = []
            if verbose:
                trace_emit(
                    MODULE_MATEGRAPH,
                    f"beam round={round_index} depth={beam[0].depth if beam else 0} "
                    f"states={len(beam)}",
                    min_level=TRACE_VERBOSE,
                )
            verbose_events = 0
            skip_slot_logged = False
            for state in beam:
                if state.depth >= len(order):
                    align = GraphAlignment(tuple(state.mapping.items()))
                    score = _score_alignment(pattern, target, state.mapping, policy)
                    completed.append(ScoredAlignment(align, score))
                    if verbose and verbose_events < _VERBOSE_BEAM_CAP:
                        trace_emit(
                            MODULE_MATEGRAPH,
                            f"beam complete mapping={state.mapping} "
                            f"{_score_summary(score)}",
                            min_level=TRACE_VERBOSE,
                        )
                        verbose_events += 1
                    continue

                slot_id = order[state.depth]
                slot = pattern.slot(slot_id)
                if slot is None:
                    next_beam.append(
                        _BeamState(dict(state.mapping), set(state.used_targets), state.depth + 1)
                    )
                    continue

                if slot_id in state.mapping:
                    next_beam.append(
                        _BeamState(dict(state.mapping), set(state.used_targets), state.depth + 1)
                    )
                    continue

                if verbose and not skip_slot_logged and verbose_events < _VERBOSE_BEAM_CAP:
                    trace_emit(
                        MODULE_MATEGRAPH,
                        f"beam branch skip_slot depth={state.depth} slot={slot_id}",
                        min_level=TRACE_VERBOSE,
                    )
                    skip_slot_logged = True
                    verbose_events += 1
                skipped = dict(state.mapping)
                next_beam.append(
                    _BeamState(skipped, set(state.used_targets), state.depth + 1)
                )

                pool_fn = getattr(policy, "candidates_for_slot", None)
                if pool_fn is not None:
                    pool = pool_fn(slot, target, index)
                else:
                    pool = candidates_for_slot(
                        slot,
                        target,
                        index,
                        len_tol=getattr(policy, "len_tol", 1e-3),
                        angle_tol=getattr(policy, "angle_tol", 0.1),
                    )

                if verbose and not pool and verbose_events < _VERBOSE_BEAM_CAP:
                    trace_emit(
                        MODULE_MATEGRAPH,
                        f"beam slot={slot_id} reason=no_index_candidates",
                        min_level=TRACE_VERBOSE,
                    )
                    verbose_events += 1

                for tid in pool:
                    if tid in state.used_targets:
                        if verbose and verbose_events < _VERBOSE_BEAM_CAP:
                            trace_emit(
                                MODULE_MATEGRAPH,
                                f"beam slot={slot_id} reject {tid} "
                                f"reason=target_already_mapped",
                                min_level=TRACE_VERBOSE,
                            )
                            verbose_events += 1
                        continue
                    tnode = target.node(tid)
                    if tnode is None:
                        if verbose and verbose_events < _VERBOSE_BEAM_CAP:
                            trace_emit(
                                MODULE_MATEGRAPH,
                                f"beam slot={slot_id} reject {tid} "
                                f"reason=missing_target_node",
                                min_level=TRACE_VERBOSE,
                            )
                            verbose_events += 1
                        continue
                    reason = _node_rejection_reason(
                        node_cmp, slot, tnode, state.mapping
                    )
                    if reason:
                        if verbose and verbose_events < _VERBOSE_BEAM_CAP:
                            trace_emit(
                                MODULE_MATEGRAPH,
                                f"beam slot={slot_id} reject {tid} reason={reason}",
                                min_level=TRACE_VERBOSE,
                            )
                            verbose_events += 1
                        continue
                    sim = node_cmp.similarity(slot, tnode, state.mapping)
                    new_map = dict(state.mapping)
                    new_map[slot_id] = tid
                    new_used = set(state.used_targets)
                    new_used.add(tid)
                    partial = _score_alignment(pattern, target, new_map, policy)
                    if policy.should_prune_partial(len(new_map), partial.total):
                        if verbose and verbose_events < _VERBOSE_BEAM_CAP:
                            trace_emit(
                                MODULE_MATEGRAPH,
                                f"beam slot={slot_id} prune {tid} reason=partial_pruned "
                                f"{_score_summary(partial)}",
                                min_level=TRACE_VERBOSE,
                            )
                            verbose_events += 1
                        continue
                    if verbose and verbose_events < _VERBOSE_BEAM_CAP:
                        sim_txt = f" sim={sim:.3f}" if sim is not None else ""
                        trace_emit(
                            MODULE_MATEGRAPH,
                            f"beam slot={slot_id} assign {tid}{sim_txt} "
                            f"{_score_summary(partial)}",
                            min_level=TRACE_VERBOSE,
                        )
                        verbose_events += 1
                    next_beam.append(
                        _BeamState(new_map, new_used, state.depth + 1)
                    )

            if verbose and len(next_beam) > _VERBOSE_BEAM_CAP:
                trace_emit(
                    MODULE_MATEGRAPH,
                    f"beam round={round_index} expanded={len(next_beam)} "
                    f"(detail capped at {_VERBOSE_BEAM_CAP})",
                    min_level=TRACE_VERBOSE,
                )

            next_beam.sort(
                key=lambda s: _score_alignment(
                    pattern, target, s.mapping, policy
                ).total,
                reverse=True,
            )
            if verbose and len(next_beam) > policy.beam_width:
                kept = next_beam[: policy.beam_width]
                worst = _score_alignment(
                    pattern, target, kept[-1].mapping, policy
                ).total
                trace_emit(
                    MODULE_MATEGRAPH,
                    f"beam trim kept={policy.beam_width} "
                    f"dropped={len(next_beam) - policy.beam_width} "
                    f"worst_kept_score={worst:.4f}",
                    min_level=TRACE_VERBOSE,
                )
            beam = next_beam[: policy.beam_width]
            round_index += 1

        completed.sort(key=lambda c: c.score.total, reverse=True)
        unique: list[ScoredAlignment] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        for c in completed:
            key = tuple(sorted(c.alignment.mapping))
            if key in seen:
                continue
            seen.add(key)
            unique.append(c)
            if len(unique) >= policy.max_candidates:
                break

        elapsed = time.monotonic() - start
        if trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP):
            trace_duration(
                MODULE_MATEGRAPH,
                f"alignment search candidates={len(unique)}",
                elapsed,
                min_level=TRACE_DEEP,
            )
        return SearchResult(
            candidates=tuple(unique),
            elapsed_s=elapsed,
            metadata={"searcher": "beam", "version": str(self.search_protocol_version)},
        )


def run_search(
    pattern: GraphPattern,
    target: PartGraph,
    policy: AlignmentSearchPolicy | None = None,
    searcher: GraphSearcher | None = None,
) -> SearchResult:
    eng = searcher or BeamGraphSearcher()
    pol = policy or DefaultSearchPolicy()
    return eng.search(pattern, target, pol)
