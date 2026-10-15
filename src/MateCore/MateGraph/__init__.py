"""Host-independent part attributed adjacency graphs (MateGraph)."""

from .model import (
    AAGEdge,
    AAGNode,
    ANALYTIC_KINDS,
    CONCAVE,
    CONVEX,
    CONE,
    CYLINDER,
    FREEFORM,
    NormalSample,
    OTHER,
    PLANE,
    SMOOTH,
    SPHERE,
    TORUS,
    UNKNOWN,
    PartGraph,
)
from .metadata import METADATA_VERSION, PartMetadata, PartMetadataPredicate
from .metadata_store import (
    PartMetadataCollector,
    PartMetadataStore,
    filter_parts_by_metadata,
)
from .options import GraphBuildOptions
from .store import PartGraphStore

__all__ = [
    "AAGEdge",
    "AAGNode",
    "ANALYTIC_KINDS",
    "CONCAVE",
    "CONVEX",
    "CONE",
    "CYLINDER",
    "FREEFORM",
    "GraphBuildOptions",
    "METADATA_VERSION",
    "NormalSample",
    "PartMetadata",
    "PartMetadataCollector",
    "PartMetadataPredicate",
    "PartMetadataStore",
    "filter_parts_by_metadata",
    "OTHER",
    "PLANE",
    "PartGraph",
    "PartGraphStore",
    "SMOOTH",
    "SPHERE",
    "TORUS",
    "UNKNOWN",
]
