"""Target graph indexing for candidate pruning."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..model import PartGraph


@dataclass
class TargetIndex:
    by_kind: dict[str, tuple[str, ...]] = field(default_factory=dict)
    radii_by_kind: dict[str, tuple[tuple[float, str], ...]] = field(default_factory=dict)
    semi_angles_by_kind: dict[str, tuple[tuple[float, str], ...]] = field(
        default_factory=dict
    )

    @classmethod
    def from_graph(cls, graph: PartGraph) -> TargetIndex:
        buckets: dict[str, list[str]] = {}
        radii: dict[str, list[tuple[float, str]]] = {}
        semi: dict[str, list[tuple[float, str]]] = {}
        for node in graph.nodes:
            buckets.setdefault(node.surface_kind, []).append(node.node_id)
            if node.radius > 0:
                radii.setdefault(node.surface_kind, []).append((node.radius, node.node_id))
            if node.surface_kind == "cone" and node.semi_angle > 0:
                semi.setdefault(node.surface_kind, []).append(
                    (node.semi_angle, node.node_id)
                )
        radii_sorted = {
            k: tuple(sorted(v, key=lambda x: x[0])) for k, v in radii.items()
        }
        semi_sorted = {k: tuple(sorted(v, key=lambda x: x[0])) for k, v in semi.items()}
        return cls(
            by_kind={k: tuple(v) for k, v in buckets.items()},
            radii_by_kind=radii_sorted,
            semi_angles_by_kind=semi_sorted,
        )

    def candidates_for_kind(self, kind: str) -> tuple[str, ...]:
        return self.by_kind.get(kind, ())

    def candidates_in_radius_band(
        self, kind: str, lo: float, hi: float
    ) -> tuple[str, ...]:
        entries = self.radii_by_kind.get(kind, ())
        if not entries:
            return ()
        return tuple(nid for r, nid in entries if lo <= r <= hi)

    def candidates_in_semi_angle_band(
        self, kind: str, lo: float, hi: float
    ) -> tuple[str, ...]:
        entries = self.semi_angles_by_kind.get(kind, ())
        if not entries:
            return ()
        return tuple(nid for a, nid in entries if lo <= a <= hi)
