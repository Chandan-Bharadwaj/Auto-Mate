"""Graph pattern (induced subgraph query)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class PatternSlot:
    slot_id: str
    source_node_id: str
    surface_kind: str
    origin: np.ndarray
    axis: np.ndarray
    area: float = 0.0
    radius: float = 0.0
    semi_angle: float = 0.0
    convex: bool = True
    plane_aspect: float = 0.0
    member_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin", np.asarray(self.origin, dtype=float))
        object.__setattr__(self, "axis", np.asarray(self.axis, dtype=float))


@dataclass(frozen=True, slots=True)
class PatternEdge:
    a: str
    b: str
    convexity: str
    dihedral_angle: float = 0.0


@dataclass(frozen=True, slots=True)
class GraphPattern:
    part_id: str
    slots: tuple[PatternSlot, ...]
    edges: tuple[PatternEdge, ...]
    anchor_slots: frozenset[str]
    _adjacency: dict[str, frozenset[str]] = field(repr=False)
    _by_slot: dict[str, PatternSlot] = field(repr=False)

    def slot(self, slot_id: str) -> PatternSlot | None:
        return self._by_slot.get(slot_id)

    def neighbors(self, slot_id: str) -> frozenset[str]:
        return self._adjacency.get(slot_id, frozenset())

    def degree(self, slot_id: str) -> int:
        return len(self.neighbors(slot_id))

    def edge_between(self, a: str, b: str) -> PatternEdge | None:
        for e in self.edges:
            if (e.a, e.b) == (a, b) or (e.a, e.b) == (b, a):
                return e
        return None

    def map_slots(self, transform) -> GraphPattern:
        """Return a copy with slots transformed (e.g. complement geometry)."""
        slots = tuple(transform(s) for s in self.slots)
        by_slot = {s.slot_id: s for s in slots}
        return GraphPattern(
            part_id=self.part_id,
            slots=slots,
            edges=self.edges,
            anchor_slots=self.anchor_slots,
            _adjacency=dict(self._adjacency),
            _by_slot=by_slot,
        )
