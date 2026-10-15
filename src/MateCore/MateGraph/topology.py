"""Topology discovery results (host-independent)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FaceAdjacencyEdge:
    face_a: str
    face_b: str
    shared_edge: Any
