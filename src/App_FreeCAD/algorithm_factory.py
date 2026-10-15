"""Workbench algorithm registry and factory (resolved per compute run)."""

from __future__ import annotations

from MateCore.algorithm import AlgorithmConfig, AlgorithmRegistry, MateAlgorithm
from MateCore.dummy_algorithm import DummyMateAlgorithm
from MateCore.MateAlgo_Heuristic.algorithm_heuristic import MateAlgorithm_Heuristic
from MateCore.MateFit.fits import FitResolver
from MateCore.MateGraph.debug_mate_graph_algorithm import MateAlgorithm_DebugMateGraph
from MateCore.MateGraph.options import GraphBuildOptions
from MateCore.rendering_demo_algorithm import DummyRenderingDemoAlgorithm
from MateCore.trace import MODULE_FACTORY, TRACE_DEEP, trace_milestone, trace_span

from .geometry_cache import (
    DocumentGeometryCache,
    get_part_graph_store,
    get_part_metadata_store,
)

_ALIASES: dict[str, str] = {
    "rendering": "rendering_demo",
    "render": "rendering_demo",
}

_registry = AlgorithmRegistry()


def _run_config() -> AlgorithmConfig:
    return AlgorithmConfig(max_parts=10, max_matches_per_part=5)


def _build_heuristic(cache: DocumentGeometryCache) -> MateAlgorithm_Heuristic:
    from .settings import get_heuristic_mate_config

    tol = FitResolver().policy.default.tolerance
    options = GraphBuildOptions(
        tol_len=tol.abs_len,
        tol_angle=tol.abs_angle,
        merge_smooth=True,
    )
    store = get_part_graph_store(cache.document_name, default_options=options)

    def graph_for(part):
        return store.get(part)

    meta_store = get_part_metadata_store(cache.document_name)
    return MateAlgorithm_Heuristic(
        graph_for,
        metadata_store=meta_store,
        config=_run_config(),
        mate_config=get_heuristic_mate_config(),
    )


def _build_debug_mate_graph(cache: DocumentGeometryCache) -> MateAlgorithm_DebugMateGraph:
    tol = FitResolver().policy.default.tolerance
    options = GraphBuildOptions(
        tol_len=tol.abs_len,
        tol_angle=tol.abs_angle,
        merge_smooth=False,
    )
    store = get_part_graph_store(cache.document_name, default_options=options)
    return MateAlgorithm_DebugMateGraph(store, options=options, config=_run_config())


def _register_defaults() -> None:
    _registry.register(
        "rendering_demo",
        lambda: DummyRenderingDemoAlgorithm(
            config=AlgorithmConfig(max_parts=4, max_matches_per_part=1),
        ),
    )
    _registry.register("dummy", lambda: DummyMateAlgorithm())


_register_defaults()


def normalize_algorithm_name(name: str) -> str:
    key = name.strip().lower()
    return _ALIASES.get(key, key)


def known_algorithms() -> tuple[str, ...]:
    return ("heuristic", "debug_mate_graph") + _registry.names()


def create_algorithm(
    name: str, *, geometry_cache: DocumentGeometryCache | None = None
) -> MateAlgorithm:
    canonical = normalize_algorithm_name(name)
    trace_milestone(
        MODULE_FACTORY, "create_algorithm", context={"algorithm_id": canonical}
    )
    with trace_span(
        MODULE_FACTORY, f"create_algorithm id={canonical}", min_level=TRACE_DEEP
    ):
        if canonical == "heuristic":
            if geometry_cache is None:
                raise ValueError(
                    "geometry_cache is required for the heuristic algorithm"
                )
            return _build_heuristic(geometry_cache)
        if canonical == "debug_mate_graph":
            if geometry_cache is None:
                raise ValueError(
                    "geometry_cache is required for the debug_mate_graph algorithm"
                )
            return _build_debug_mate_graph(geometry_cache)
        return _registry.create(canonical)
