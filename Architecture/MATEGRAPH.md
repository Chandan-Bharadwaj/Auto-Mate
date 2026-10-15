# MateGraph

Product context: [OVERVIEW.md](OVERVIEW.md). Mating domain: [Auto-Mating.md](Auto-Mating.md).

Host-independent **part attributed adjacency graphs** (AAG-style data) and a **domain-neutral graph search** layer. MateGraph lives under [`src/MateCore/MateGraph/`](../src/MateCore/MateGraph/). It does not import FreeCAD and does not implement mating logic (no poses, complements, or `Match`).

Production mate search uses [`MateAlgorithm_Heuristic`](../src/MateCore/MateAlgo_Heuristic/algorithm_heuristic.py) on top of MateGraph **construction**, **caching**, and **beam alignment search**.

## Intent

| Concern | MateGraph responsibility |
| -------- | ------------------------- |
| **What is a part graph?** | Immutable `PartGraph`: nodes (faces), edges (adjacency + attributes), O(1) node lookup. |
| **How is it built?** | Pipeline + FreeCAD builder in `App_FreeCAD` (not in MateCore). |
| **When is it built?** | Lazy, **per part**, via `PartGraphStore` (one store per document). |
| **Cheap part summary?** | `PartMetadata` via `PartMetadataStore` — O(faces) stats for **primary filtration** before graph build. |
| **How do we search graphs?** | Extract a `GraphPattern` from a selection, align into another `PartGraph` with scored candidates; policy and post-filter are **injected by the consumer**. |

```text
  PartContext (faces)          MateGraph                    Consumer (e.g. future algo)
        |                           |                                    |
        v                           v                                    v
  App_FreeCAD                 PartGraphStore                    AlignmentSearchPolicy
  build_part_graph    -->     .get(part) --> PartGraph    -->    GraphSearcher.search
  (geometry_cache)            (cache miss only)                  AlignmentResultFilter
```

## Package layout

```text
MateCore/MateGraph/
  model.py              PartGraph, AAGNode, AAGEdge (+ shared constants)
  options.py            GraphBuildOptions
  metadata.py           PartMetadata, PartMetadataPredicate
  metadata_store.py     PartMetadataStore, filter_parts_by_metadata
  store.py              PartGraphStore, PartGraphBuilder protocol
  pipeline.py           assemble_graph, apply_merge
  topology.py           FaceAdjacencyEdge (build intermediate)
  reporting.py          GraphBuildReporter (build-time observability)
  debug_mate_graph_algorithm.py   Workbench-only graph build stress test
  search/               Subgraph pattern extraction + alignment search
```

FreeCAD adapters (not in MateGraph):

- [`App_FreeCAD/part_graph_build.py`](../src/App_FreeCAD/part_graph_build.py) — B-Rep → `PartGraph`
- [`App_FreeCAD/geometry_cache.py`](../src/App_FreeCAD/geometry_cache.py) — `get_part_graph_store()`, `get_part_metadata_store()`, document registry
- [`App_FreeCAD/part_metadata_collect.py`](../src/App_FreeCAD/part_metadata_collect.py) — `collect_part_metadata` (fast face scan)
- [`App_FreeCAD/aag_build.py`](../src/App_FreeCAD/aag_build.py) — legacy `build_part_aag()` wrapper

`PartAAG` in [`MateGraph/model.py`](../src/MateCore/MateGraph/model.py) is an alias of `PartGraph`. Smooth-face merge lives in [`MateGraph/merge.py`](../src/MateCore/MateGraph/merge.py).

---

## Main entry points

### Data model

| Import | Role |
| ------ | ---- |
| `from MateCore.MateGraph import PartGraph, AAGNode, AAGEdge` | Graph types and surface/edge label constants (`PLANE`, `CONVEX`, …). |
| `PartGraph.build(part_id, nodes, edges)` | Construct graph with adjacency indexes. |

### Build options and store

| Import / API | Role |
| ------------ | ---- |
| `GraphBuildOptions` | `tol_len`, `tol_angle`, `merge_smooth` (cache key fingerprint). |
| `PartGraphStore(document_name, builder, default_options?)` | Lazy cache: `get(part)` builds **only that** `part_id` on miss. |
| `App_FreeCAD.geometry_cache.get_part_graph_store(doc)` | Document singleton store wired to `build_part_graph`. |
| `DocumentGeometryCache.part_graph_store()` | Same store for a document cache instance. |

### Part metadata (pre-filter)

| Import / API | Role |
| ------------ | ---- |
| `PartMetadata` | `face_count`, `median_face_area`, `total_face_area`, `faces_by_kind`, optional `extras`. |
| `PartMetadataStore` | Lazy cache keyed by `part_id` only; independent of graph store. |
| `get_part_metadata_store(document_name)` | Document singleton wired to `collect_part_metadata`. |
| `collect_part_metadata(part)` | One pass over `part.faces` (area + surface kind); no adjacency. |
| `PartMetadataPredicate` | Consumer protocol: `accept(metadata) -> bool`. |
| `filter_parts_by_metadata(parts, store, predicate)` | Optional helper: metadata `get` per part, then filter. |

Typical filtration before AAG/graph:

```python
meta_store = get_part_metadata_store(doc_name)
if my_predicate.accept(meta_store.get(candidate_part)):
    graph = graph_store.get(candidate_part)
```

Metadata and graph caches do not populate each other.

### Graph construction (FreeCAD)

| API | Role |
| ----- | ---- |
| `build_part_graph(part, options, reporter?)` | Build one `PartGraph` (no document cache). |
| `build_part_aag(part, tol_len=…, merge_smooth=…)` | Legacy entry; delegates to `build_part_graph`. |

### Debug / validation (workbench)

| API | Role |
| ----- | ---- |
| `MateAlgorithm_DebugMateGraph` | Algorithm id `debug_mate_graph`: loops `all_parts`, calls `store.get(part)` to exercise builds and trace. |
| `algorithm_factory.create_algorithm("debug_mate_graph", geometry_cache=…)` | Factory wiring. |

Not a mating algorithm; it produces diagnostics only.

### Graph search (`MateCore.MateGraph.search`)

Domain-neutral **pattern → target** alignment. The core runs search; **policy** (during search) and **filter** (after search) are supplied by the consumer.

| Import | Role |
| ------ | ---- |
| `extract_pattern(graph, node_ids)` | Induced subgraph as `GraphPattern` (slots `p0`, `p1`, …). |
| `extract_pattern_from_refs(graph, surfaces)` | Same; sets `anchor_slots` from selection. |
| `node_for_ref(graph, ref)` | Face → graph node id (shared with query-graph resolution). |
| `run_search(pattern, target, policy?, searcher?)` | Returns `SearchResult` (ranked `ScoredAlignment` list). |
| `BeamGraphSearcher` | Default `GraphSearcher` (`search_protocol_version = 1`). |
| `AlignmentSearchPolicy` | Protocol: weights, beam width, comparators, slot order, prune hooks. |
| `DefaultSearchPolicy` | Reference implementation for **tests** only. |
| `AlignmentResultFilter` | Protocol: `apply(result, pattern, target)` — **not** called by core. |

Typical consumer flow:

```python
pattern = extract_pattern_from_refs(source_graph, selection)
raw = run_search(pattern, target_graph, my_policy)
final = my_filter.apply(raw, pattern, target_graph)
```

Search uses symmetric attribute similarity (`DefaultNodeComparator` / `DefaultEdgeComparator`). Mating-specific complements belong in the consumer, not in `MateGraph.search`.

---

## Caching semantics

- **One `PartGraphStore` and one `PartMetadataStore` per document name** (registry in `geometry_cache`).
- **Graph cache key:** `(part_id, tol_len, tol_angle, merge_smooth)`.
- **Metadata cache key:** `part_id` only.
- **`get(part_A)` never builds `part_B`.** Only `MateAlgorithm_DebugMateGraph` intentionally touches every part in one run.

---

## Tests

| Area | Tests |
| ---- | ----- |
| Store / lazy build | `tests/test_mate_graph_store.py`, `tests/test_geometry_cache.py` |
| Metadata | `tests/test_part_metadata_store.py`, `tests/test_part_metadata_collect.py` |
| Search | `tests/test_graph_search_extract.py`, `tests/test_graph_search_beam.py` |
| FreeCAD node factory | `tests/test_aag_build_node.py` (via `aag_nodes`) |

All run without a FreeCAD GUI (`python -m pytest -q`).

---

## Related docs

- [`MateCore/MateGraph/ROADMAP.md`](../src/MateCore/MateGraph/ROADMAP.md) — improvement roadmap (Tier 1 search/index/comparator focus)
- [`HEURISTIC_MATE_ALGORITHM.md`](HEURISTIC_MATE_ALGORITHM.md) — `heuristic` mating consumer pipeline
- [`GRAPH_MATE_CONSOLIDATED.md`](GRAPH_MATE_CONSOLIDATED.md) — consolidated heuristic design
- [`PYTHON_ARCHITECTURE.md`](PYTHON_ARCHITECTURE.md) — workbench layout and MateCore packages
- [`TRACE.md`](TRACE.md) — trace levels for build/search diagnostics
