"""Lazy per-part metadata cache."""

from __future__ import annotations

import time
from typing import Protocol

from MateCore.context import PartContext
from MateCore.trace import (
    MODULE_MATEGRAPH,
    TRACE_DEEP,
    TRACE_HIGH,
    trace_at_least,
    trace_duration,
    trace_emit,
)

from .metadata import PartMetadata, PartMetadataPredicate


class PartMetadataCollector(Protocol):
    def __call__(self, part: PartContext, /) -> PartMetadata: ...


class PartMetadataStore:
    """Document-scoped cache: collects metadata per ``get`` on cache miss."""

    def __init__(
        self,
        document_name: str,
        collector: PartMetadataCollector,
    ) -> None:
        self.document_name = document_name
        self._collector = collector
        self._entries: dict[str, PartMetadata] = {}

    def get(self, part: PartContext) -> PartMetadata:
        cached = self._entries.get(part.part_id)
        if cached is not None:
            if trace_at_least(MODULE_MATEGRAPH, TRACE_DEEP):
                trace_emit(
                    MODULE_MATEGRAPH,
                    f"metadata cache hit part={part.part_id} doc={self.document_name}",
                    min_level=TRACE_DEEP,
                )
            return cached

        label = f"mate_graph.metadata part={part.part_id} faces={len(part.faces)}"
        start = time.monotonic()
        if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
            trace_emit(MODULE_MATEGRAPH, f"{label} …", min_level=TRACE_HIGH)
        meta = self._collector(part)
        elapsed = time.monotonic() - start
        self._entries[part.part_id] = meta
        if trace_at_least(MODULE_MATEGRAPH, TRACE_HIGH):
            trace_duration(
                MODULE_MATEGRAPH,
                f"{label} face_count={meta.face_count}",
                elapsed,
                min_level=TRACE_HIGH,
            )
        return meta

    def invalidate(self, part_id: str | None = None) -> None:
        if part_id is None:
            self._entries.clear()
            return
        self._entries.pop(part_id, None)


def filter_parts_by_metadata(
    parts: tuple[PartContext, ...] | list[PartContext],
    store: PartMetadataStore,
    predicate: PartMetadataPredicate,
) -> list[PartContext]:
    """Load metadata per part (lazy) and keep those accepted by ``predicate``."""
    out: list[PartContext] = []
    for part in parts:
        if predicate.accept(store.get(part)):
            out.append(part)
    return out
