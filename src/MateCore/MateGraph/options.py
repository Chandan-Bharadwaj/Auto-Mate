"""Build-time options for part graphs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraphBuildOptions:
    tol_len: float = 1e-3
    tol_angle: float = 1e-3
    merge_smooth: bool = False

    def cache_key(self) -> tuple[float, float, bool]:
        return (self.tol_len, self.tol_angle, self.merge_smooth)
