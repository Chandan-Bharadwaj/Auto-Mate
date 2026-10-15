"""Lazy per-document cache of part graphs and metadata."""

from __future__ import annotations

from MateCore.MateGraph.model import PartAAG
from MateCore.MateGraph.options import GraphBuildOptions
from MateCore.MateGraph.metadata_store import PartMetadataStore
from MateCore.MateGraph.store import PartGraphStore
from MateCore.context import PartContext
from MateCore.trace import MODULE_CACHE, TRACE_DEEP, TRACE_HIGH, trace_at_least, trace_emit, trace_milestone

from .part_graph_build import build_part_graph
from .part_metadata_collect import collect_part_metadata

_registry: dict[str, DocumentGeometryCache] = {}
_graph_store_registry: dict[str, PartGraphStore] = {}
_metadata_store_registry: dict[str, PartMetadataStore] = {}


def get_part_metadata_store(document_name: str) -> PartMetadataStore:
    store = _metadata_store_registry.get(document_name)
    if store is None:
        store = PartMetadataStore(document_name, collect_part_metadata)
        _metadata_store_registry[document_name] = store
    return store


def get_part_graph_store(
    document_name: str,
    default_options: GraphBuildOptions | None = None,
) -> PartGraphStore:
    store = _graph_store_registry.get(document_name)
    if store is None:
        opts = default_options or GraphBuildOptions()

        def builder(part: PartContext, options: GraphBuildOptions, reporter) -> PartAAG:
            return build_part_graph(part, options, reporter)

        store = PartGraphStore(document_name, builder, default_options=opts)
        _graph_store_registry[document_name] = store
    return store


class DocumentGeometryCache:
    """Per-document handle for graph and metadata stores."""

    def __init__(self, document_name: str) -> None:
        self.document_name = document_name

    def part_graph_store(self, default_options: GraphBuildOptions | None = None) -> PartGraphStore:
        return get_part_graph_store(self.document_name, default_options)

    def part_metadata_store(self) -> PartMetadataStore:
        return get_part_metadata_store(self.document_name)


def get_or_create(document_name: str) -> DocumentGeometryCache:
    cache = _registry.get(document_name)
    if cache is None:
        cache = DocumentGeometryCache(document_name)
        _registry[document_name] = cache
    return cache


def clear_registry() -> None:
    _registry.clear()
    _graph_store_registry.clear()
    _metadata_store_registry.clear()
