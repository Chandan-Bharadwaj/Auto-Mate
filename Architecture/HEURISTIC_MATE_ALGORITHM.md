# Heuristic mate algorithm (`MateAlgo_Heuristic`)

Architecture note for the **heuristic** graph-pattern mate searcher (factory id `heuristic`). **Session dials summary:** [OVERVIEW.md](OVERVIEW.md). Shared graph infrastructure: [`MATEGRAPH.md`](MATEGRAPH.md). Consolidated pointer: [`GRAPH_MATE_CONSOLIDATED.md`](GRAPH_MATE_CONSOLIDATED.md).

## Registered algorithms (mate search)

| Package | Factory id | Role |
|---------|------------|------|
| **MateAlgo_Heuristic** | `heuristic` | Default: `GraphPattern` + beam alignment + shared pose/fit |
| **Debug mate graph** | `debug_mate_graph` | Build/cache stress only |
| **Dummy** | `dummy` | Workflow placeholder |
| **Rendering demo** | `rendering_demo` | Overlay/render smoke test |

`MateAlgo_Heuristic` is a **consumer** of `MateCore.MateGraph`: mating complements, fit, pose, and `HeuristicMatch` live in the algorithm package.

## Pipeline

```
PartGraph (source)  -->  extract_pattern_from_refs  -->  enricher  -->  mating_search_pattern
  -->  PatternMetadataRequirements  -->  filter_parts_by_metadata
  -->  run_search (beam + MatingAlignmentSearchPolicy)  -->  solve_poses + assess_pairs
  -->  HeuristicMatch (pose, fits, mate_configuration_kind, score)
```

## Configuration

Full parameter catalog (search, fit, session settings, factory caps): [`TWEAKABLE_PARAMETERS.md`](TWEAKABLE_PARAMETERS.md).

`HeuristicMateConfig` (`src/MateCore/MateAlgo_Heuristic/config.py`):

- `fit_validation` / `pose_validation`: `strict` | `warn` | `skip`
- `enricher`: `selection_only` | `one_hop_analytic`
- `topology_profile`: `default` | `coarse` (lower edge weight / missing-edge penalty)

Enable in the workbench:

```python
import App_FreeCAD.settings as s
s.set_algorithm("heuristic")
```

### Pose and fit validation (session settings)

Alignment-only preview (no rigid transform, no tolerance gate):

```python
s.set_heuristic_skip_pose_fit(True)   # pose_validation=skip, fit_validation=skip
# run Auto-Mate compute, then restore:
s.set_heuristic_skip_pose_fit(False)
```

Or set modes independently (`strict` | `warn` | `skip`):

```python
s.heuristic_pose_validation = "skip"
s.heuristic_fit_validation = "skip"
```

`warn` still runs pose and fit but keeps matches with warnings in metadata.

Max clearance: `set_heuristic_nominal_fit_gap_mm(10)` sets fit band 0..10 mm (clearance fit) when the pattern is axis-aligned or includes a cylinder; see [`TWEAKABLE_PARAMETERS.md`](TWEAKABLE_PARAMETERS.md).

## Mate configuration labels

`MateFit.classify_configuration` rolls up per-pair `FitResult` into `exact_fit`, `clearance_fit`, etc. on `HeuristicMatch.metadata["mate_configuration_kind"]` and the mating report ([`mate_report.py`](../src/MateCore/mate_report.py), trace module `report`).

## Trace

Per [`TRACE.md`](TRACE.md): `set_trace_module("heuristic", 1)` for prepare and match stages; `set_trace_module("heuristic", 2)` for enricher, validation mode, and pose outcome stats. Beam alignment detail uses `set_trace_module("mategraph", 2)`.

## Tests

- `tests/test_heuristic_mate.py` — peg/plane scenarios without FreeCAD
- `tests/test_trace_heuristic.py` — `heuristic` module registration and emitters
- MateGraph search/index tests cover Tier-1 `candidates_for_slot` and radius buckets
