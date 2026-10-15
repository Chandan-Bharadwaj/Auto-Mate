"""Abstract mate algorithm interface the command depends on.

The unit of output is the *part*: given faces selected on one source part, an
algorithm reports which other parts mate with it, each with one or more mating
configurations (``Match``). ``MateAlgorithm.run`` is a template method
that owns the part loop, cancellation, caps, ranking and rejection reporting;
subclasses implement ``match_part`` and may override any other hook.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from contextlib import nullcontext
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Protocol, Sequence

from .context import MateQuery, PartContext, RecognitionRequest, SurfaceRef
from .trace import (
    MODULE_RUN,
    TRACE_DEEP,
    TRACE_HIGH,
    trace_at_least,
    trace_duration,
    trace_emit,
    trace_milestone,
    trace_span,
)


@dataclass(frozen=True, slots=True)
class Match:
    """One mating configuration of the source part with a candidate part."""

    faces: tuple[SurfaceRef, ...]
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    part_id: str = ""  # stamped by the base class when left empty


@dataclass(frozen=True, slots=True)
class PartMatch:
    """A candidate part together with its mating configurations (best first)."""

    part_id: str
    part_name: str
    matches: tuple[Match, ...]
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def faces(self) -> tuple[SurfaceRef, ...]:
        seen: list[SurfaceRef] = []
        for m in self.matches:
            seen.extend(f for f in m.faces if f not in seen)
        return tuple(seen)


@dataclass(frozen=True, slots=True)
class RejectedPart:
    part_id: str
    part_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class Diagnostic:
    level: str  # "info" | "warning"
    message: str


@dataclass(frozen=True, slots=True)
class AlgorithmResult:
    part_matches: tuple[PartMatch, ...]
    rejected_parts: tuple[RejectedPart, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    timings: dict[str, float] = field(default_factory=dict)
    cancelled: bool = False

    @property
    def matches(self) -> tuple[Match, ...]:
        """All configurations, flattened in part-rank order."""
        return tuple(m for p in self.part_matches for m in p.matches)

    @property
    def warnings(self) -> tuple[str, ...]:
        return tuple(d.message for d in self.diagnostics if d.level == "warning")

    def as_surface_groups(self) -> list[list[SurfaceRef]]:
        return [list(m.faces) for m in self.matches]

    def as_part_surface_groups(self) -> list[list[SurfaceRef]]:
        """One face list per matched part (all configurations merged, deduped)."""
        groups: list[list[SurfaceRef]] = []
        for part in self.part_matches:
            seen: set[tuple[str, str]] = set()
            faces: list[SurfaceRef] = []
            for match in part.matches:
                for surface in match.faces:
                    key = (surface.object_name, surface.face_name)
                    if key not in seen:
                        seen.add(key)
                        faces.append(surface)
            if faces:
                groups.append(faces)
        return groups

    def as_part_groups(self) -> list[tuple[PartMatch, list[list[SurfaceRef]]]]:
        return [(p, [list(m.faces) for m in p.matches]) for p in self.part_matches]


@dataclass(frozen=True, slots=True)
class AlgorithmConfig:
    """Run-wide settings shared by all algorithms; subclasses may extend it."""

    max_results: int | None = None  # total configurations over all parts
    max_parts: int | None = None
    max_matches_per_part: int | None = None
    time_budget_s: float | None = None
    seed: int | None = None

    def __post_init__(self) -> None:
        for name in ("max_results", "max_parts", "max_matches_per_part"):
            value = getattr(self, name)
            if value is not None and value < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.time_budget_s is not None and self.time_budget_s <= 0:
            raise ValueError("time_budget_s must be positive")


class RunContext:
    """Per-run channel for diagnostics, progress and cooperative cancellation."""

    def __init__(
        self,
        config: AlgorithmConfig,
        is_cancelled: Callable[[], bool] | None = None,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> None:
        self.config = config
        self._is_cancelled = is_cancelled or (lambda: False)
        self._on_progress = on_progress
        self._started = time.monotonic()
        self.diagnostics: list[Diagnostic] = []
        self._reasons: dict[str, str] = {}

    def explain(self, part_id: str, reason: str) -> None:
        """Record why a part did not mate (reported in ``rejected_parts``)."""
        self._reasons[part_id] = reason

    def reason_for(self, part_id: str) -> str | None:
        return self._reasons.get(part_id)

    def info(self, message: str) -> None:
        self.diagnostics.append(Diagnostic("info", message))

    def warn(self, message: str) -> None:
        self.diagnostics.append(Diagnostic("warning", message))

    def progress(self, fraction: float, message: str = "") -> None:
        if self._on_progress is not None:
            self._on_progress(max(0.0, min(1.0, fraction)), message)

    @property
    def should_stop(self) -> bool:
        """True when cancelled or the time budget is spent; hooks should poll it."""
        budget = self.config.time_budget_s
        if budget is not None and time.monotonic() - self._started > budget:
            return True
        return bool(self._is_cancelled())


class MatchPostProcessor(Protocol):
    """A stage that filters, merges, annotates or re-orders matches."""

    name: str

    def process(
        self, matches: list[Match], request: RecognitionRequest, run: RunContext
    ) -> list[Match]: ...


class Ranker(Protocol):
    def rank(self, matches: list[Match]) -> list[Match]: ...


class PartPostProcessor(Protocol):
    """A stage that filters, merges or annotates whole candidate parts."""

    name: str

    def process(
        self, parts: list[PartMatch], request: RecognitionRequest, run: RunContext
    ) -> list[PartMatch]: ...


class PartRanker(Protocol):
    def rank(self, parts: list[PartMatch]) -> list[PartMatch]: ...


def _limit_total(parts: list[PartMatch], limit: int | None) -> list[PartMatch]:
    if limit is None:
        return parts
    out: list[PartMatch] = []
    remaining = limit
    for part in parts:
        if remaining <= 0:
            break
        kept = part.matches[:remaining]
        remaining -= len(kept)
        out.append(part if len(kept) == len(part.matches) else replace(part, matches=kept))
    return out


class MateAlgorithm(ABC):
    """Contract between the command and any recognition implementation."""

    name: str = "algorithm"
    version: str = "0"
    supported_surface_kinds: tuple[str, ...] = ()
    # The selection must lie on exactly one known part (the source part).
    single_source_part: bool = True

    def __init__(self, config: AlgorithmConfig | None = None) -> None:
        self.config = config or AlgorithmConfig()
        self._postprocessors: list[MatchPostProcessor] = []
        self._ranker: Ranker | None = None
        self._part_postprocessors: list[PartPostProcessor] = []
        self._part_ranker: PartRanker | None = None

    # -- public API -------------------------------------------------------
    def compute(self, request: RecognitionRequest) -> list[list[SurfaceRef]]:
        """Return zero or more groups of surfaces for the supplied request."""
        return self.run(request).as_surface_groups()

    def run(
        self,
        request: RecognitionRequest,
        *,
        is_cancelled: Callable[[], bool] | None = None,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> AlgorithmResult:
        run = RunContext(self.config, is_cancelled, on_progress)
        if trace_at_least(MODULE_RUN, TRACE_HIGH):
            trace_emit(MODULE_RUN, f"run.start algorithm={self.name}", min_level=TRACE_HIGH)
        timings: dict[str, float] = {}

        def timed(
            stage: str,
            fn: Callable[[], Any],
            *,
            milestone: dict[str, str | int | float] | None = None,
        ) -> Any:
            trace_milestone(MODULE_RUN, stage, context=milestone)
            start = time.monotonic()
            if trace_at_least(MODULE_RUN, TRACE_HIGH):
                trace_emit(MODULE_RUN, f"run.{stage} …", min_level=TRACE_HIGH)
            try:
                return fn()
            finally:
                elapsed = time.monotonic() - start
                timings[stage] = elapsed
                if trace_at_least(MODULE_RUN, TRACE_HIGH):
                    trace_duration(
                        MODULE_RUN, f"run.{stage}", elapsed, min_level=TRACE_HIGH
                    )

        timed(
            "validate",
            lambda: self.validate(request, run),
            milestone={
                "algorithm": self.name,
                "selected_faces": len(request.surfaces),
            },
        )
        aborted = self.abort_result_after_validate(request, run)
        if aborted is not None:
            return replace(aborted, timings=timings)
        query = timed("query", lambda: self._resolve_query(request))
        state = timed("prepare", lambda: self.prepare(request, run))
        parts = list(
            timed(
                "candidates",
                lambda: self.candidate_parts(state, query, run),
                milestone={"algorithm": self.name},
            )
        )
        trace_milestone(
            MODULE_RUN,
            "match_parts",
            context={"candidate_count": len(parts), "algorithm": self.name},
        )

        part_matches: list[PartMatch] = []
        rejected: list[RejectedPart] = []
        total = max(1, len(parts))
        search_time = 0.0
        for index, part in enumerate(parts):
            if run.should_stop:
                break
            run.progress(index / total, f"Matching part {part.name}")
            start = time.monotonic()
            label = (
                f"run.match_part [{index + 1}/{total}] "
                f"part={part.part_id} ({part.name})"
            )
            with (
                trace_span(MODULE_RUN, label, min_level=TRACE_HIGH)
                if trace_at_least(MODULE_RUN, TRACE_HIGH)
                else nullcontext()
            ):
                raw_matches = list(self.match_part(state, part, run))
            matches = [
                m if m.part_id else replace(m, part_id=part.part_id)
                for m in raw_matches
            ]
            for stage in self._postprocessors:
                matches = list(stage.process(matches, request, run))
            matches = self.rank(matches)
            cap = self.config.max_matches_per_part
            if cap is not None:
                matches = matches[:cap]
            search_time += time.monotonic() - start
            if not matches:
                rejected.append(
                    RejectedPart(
                        part.part_id,
                        part.name,
                        run.reason_for(part.part_id) or "no mating configuration found",
                    )
                )
                continue
            part_matches.append(
                PartMatch(
                    part_id=part.part_id,
                    part_name=part.name,
                    matches=tuple(matches),
                    score=self.score_part(part, matches),
                )
            )
        run.progress(1.0, "Done")
        timings["match_parts"] = search_time

        for stage in self._part_postprocessors:
            before = {p.part_id for p in part_matches}
            part_matches = list(
                timed(
                    f"postprocess-parts:{stage.name}",
                    lambda s=stage: s.process(part_matches, request, run),
                )
            )
            kept = {p.part_id for p in part_matches}
            names = {p.part_id: p.name for p in parts}
            rejected.extend(
                RejectedPart(pid, names.get(pid, pid), f"removed by {stage.name}")
                for pid in sorted(before - kept)
            )
        part_matches = list(timed("rank_parts", lambda: self.rank_parts(part_matches)))
        if self.config.max_parts is not None:
            part_matches = part_matches[: self.config.max_parts]
        part_matches = _limit_total(part_matches, self.config.max_results)
        if trace_at_least(MODULE_RUN, TRACE_HIGH):
            summary = ", ".join(
                f"{k}={v:.3f}s" for k, v in sorted(timings.items())
            )
            trace_emit(
                MODULE_RUN, f"run.complete timings: {summary}", min_level=TRACE_HIGH
            )
        return AlgorithmResult(
            part_matches=tuple(part_matches),
            rejected_parts=tuple(rejected),
            diagnostics=tuple(run.diagnostics),
            timings=timings,
            cancelled=run.should_stop,
        )

    def _resolve_query(self, request: RecognitionRequest) -> MateQuery:
        context = request.context
        found = {}
        unknown = 0
        for surface in request.surfaces:
            part = context.get_part_for_face(surface)
            if part is None:
                unknown += 1
            else:
                found[part.part_id] = part
        if self.single_source_part:
            if unknown:
                raise ValueError("Selected surfaces must belong to a known part")
            if len(found) > 1:
                raise ValueError("Selected surfaces must all belong to one part")
        source = next(iter(found.values())) if len(found) == 1 and not unknown else None
        return MateQuery(source, request.surfaces, context)

    def add_postprocessor(self, stage: MatchPostProcessor) -> None:
        self._postprocessors.append(stage)

    def clear_postprocessors(self) -> None:
        self._postprocessors.clear()

    @property
    def postprocessors(self) -> tuple[MatchPostProcessor, ...]:
        return tuple(self._postprocessors)

    def set_ranker(self, ranker: Ranker | None) -> None:
        self._ranker = ranker

    def add_part_postprocessor(self, stage: PartPostProcessor) -> None:
        self._part_postprocessors.append(stage)

    def clear_part_postprocessors(self) -> None:
        self._part_postprocessors.clear()

    @property
    def part_postprocessors(self) -> tuple[PartPostProcessor, ...]:
        return tuple(self._part_postprocessors)

    def set_part_ranker(self, ranker: PartRanker | None) -> None:
        self._part_ranker = ranker

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "supported_surface_kinds": list(self.supported_surface_kinds),
            "postprocessors": [p.name for p in self._postprocessors],
        }

    # -- hooks ------------------------------------------------------------
    def validate(self, request: RecognitionRequest, run: RunContext) -> None:
        """Raise ValueError when the request is unusable. Default: surfaces required."""
        if not request.surfaces:
            raise ValueError("At least one selected surface is required")

    def abort_result_after_validate(
        self, request: RecognitionRequest, run: RunContext
    ) -> AlgorithmResult | None:
        """Return a result to skip prepare/match after validate; default continues."""
        return None

    def prepare(self, request: RecognitionRequest, run: RunContext) -> Any:
        """Build caches/descriptors once; the result is passed to find_matches."""
        return request

    def candidate_parts(
        self, state: Any, query: MateQuery, run: RunContext
    ) -> Sequence[PartContext]:
        """Parts to examine. Default: every part except the source part."""
        source_id = query.source_part.part_id if query.source_part else None
        return [p for p in query.context.all_parts if p.part_id != source_id]

    @abstractmethod
    def match_part(
        self, state: Any, part: PartContext, run: RunContext
    ) -> Sequence[Match]:
        """Return every mating configuration of the source part with ``part``.

        An empty result means the part does not mate; call
        ``run.explain(part.part_id, reason)`` to say why.
        """

    def score_part(self, part: PartContext, matches: Sequence[Match]) -> float:
        """Aggregate configuration scores into a part score. Default: the best."""
        return max(m.score for m in matches)

    def rank(self, matches: list[Match]) -> list[Match]:
        """Order the configurations within one part."""
        return self._ranker.rank(matches) if self._ranker else matches

    def rank_parts(self, parts: list[PartMatch]) -> list[PartMatch]:
        """Order the candidate parts. Default: best score first."""
        if self._part_ranker:
            return self._part_ranker.rank(parts)
        return sorted(parts, key=lambda p: -p.score)


AlgorithmFactory = Callable[[], MateAlgorithm]


class AlgorithmRegistry:
    """Name -> algorithm factory, so the command can select algorithms by name."""

    def __init__(self) -> None:
        self._factories: dict[str, AlgorithmFactory] = {}

    def register(self, name: str, factory: AlgorithmFactory) -> None:
        if name in self._factories:
            raise ValueError(f"Algorithm '{name}' is already registered")
        self._factories[name] = factory

    def create(self, name: str) -> MateAlgorithm:
        try:
            return self._factories[name]()
        except KeyError:
            raise KeyError(f"Unknown algorithm '{name}'") from None

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


algorithm_registry = AlgorithmRegistry()
