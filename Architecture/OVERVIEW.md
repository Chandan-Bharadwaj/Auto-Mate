# Auto-Mate architecture overview

Start here for how the product works, how the code is organized, and where to read next.

## What Auto-Mate does

Select faces on **one** part in a FreeCAD assembly; Auto-Mate searches other parts and returns a **ranked list of mating parts**, with overlays and a **mating report** that explains pairings and rejections.

## Design intent (short)

We do **not** treat mating as “find every cylinder and plane in the model, cluster features, then match by type.” We **do** treat your selection as a **local graph pattern**, align it to candidate parts with a **scored heuristic** (beam search), then **verify** with pose and fit. Analytic surface kinds support **measurement after mapping**, not global feature identification. Full narrative: [Auto-Mating.md](Auto-Mating.md) (design intent and macro/micro).

## End-to-end flow

```mermaid
flowchart LR
  Cmd[FreeCAD command]
  Req[RecognitionRequest]
  Run[MateAlgorithm.run]
  Res[AlgorithmResult]
  Disp[display + mate_report]
  Cmd --> Req --> Run --> Res --> Disp
```

| Package | Role |
|---------|------|
| [`src/MateCore/`](../src/MateCore/) | Host-independent mating logic (no `FreeCAD` imports) |
| [`src/App_FreeCAD/`](../src/App_FreeCAD/) | Document capture, graph build, command, display, factory |
| [`FeatureTools/`](../FeatureTools/) | Workbench `Init.py` / `InitGui.py` only |

Deploy: [`updateProduction.py`](../updateProduction.py) stages `MateCore` + `App_FreeCAD` into the installed Mod tree.

## Default algorithm: heuristic

Production default: factory id **`heuristic`** (`MateAlgorithm_Heuristic`).

1. Build or load **PartGraph** per part ([`part_graph_build.py`](../src/App_FreeCAD/part_graph_build.py), [`geometry_cache.py`](../src/App_FreeCAD/geometry_cache.py)).
2. Extract a **pattern** from selected faces (slots, topology); optional enricher.
3. **Metadata filter** on candidate parts (when configured).
4. **Beam graph alignment** (`MateGraph` search) → scored mappings.
5. **Pose + fit** on top alignments → `HeuristicMatch` / `PartMatch`.

Legacy AAG/VF2-style search is documented separately: [LEGACY_AAG.md](LEGACY_AAG.md).

## Heuristic dials (session)

Set from the FreeCAD Python console (`import App_FreeCAD.settings as s`). Full tables: [HEURISTIC_MATE_ALGORITHM.md](HEURISTIC_MATE_ALGORITHM.md), [TWEAKABLE_PARAMETERS.md](TWEAKABLE_PARAMETERS.md).

| Dial | API (examples) | Typical use |
|------|----------------|-------------|
| Algorithm | `s.set_algorithm("heuristic")` | Default production searcher |
| Pose / fit gate | `s.set_heuristic_pose_validation("strict"\|"warn"\|"skip")`, same for `fit_validation` | `skip` = alignment-only preview |
| Skip both | `s.set_heuristic_skip_pose_fit(True)` | Graph alignment without pose/fit |
| Clearance band | `s.set_heuristic_nominal_fit_gap_mm(0.05)` / `None` | Axis-aligned clearance mates |
| Single-face gate | `s.set_heuristic_disallow_single_surface_mates(...)` | Require multi-face patterns when enabled |

**Code-only** (via `HeuristicMateConfig` unless you construct the algorithm in tests): `enricher`, `topology_profile`, flank/plane-shape search weights.

**Observability:** `s.set_trace_module("heuristic", 2)`, `set_trace_module("mategraph", 3)`, `set_trace_module("report", 0)` — see [TRACE.md](TRACE.md). Module **`report`** is on by default (mating report); other trace defaults off.

## Performance

**Principle:** cache expensive graph builds; bound search with beam width and run caps; run pose/fit only on top alignments.

| Mechanism | What it limits |
|-----------|----------------|
| `DocumentGeometryCache` / `PartGraphStore` | Reuse per-part graphs per document (see stale-cache warning in [Auto-Mating.md](Auto-Mating.md)) |
| `AlgorithmConfig` | `max_parts`, `max_results`, `max_matches_per_part`, optional `time_budget_s` |
| Beam search | `beam_width`, `max_candidates` (see [TWEAKABLE_PARAMETERS.md](TWEAKABLE_PARAMETERS.md)) |
| Metadata filter | Fewer candidate parts before `match_part` |
| Trace verbose | Capped beam event spam; global algorithm trace off by default |

Tuning tradeoffs (accuracy vs speed): [TWEAKABLE_PARAMETERS.md](TWEAKABLE_PARAMETERS.md).

## Reasoning: why a match did or did not happen

Mating is designed to be **explainable**, not a black box.

| Layer | Audience | What you get |
|-------|----------|--------------|
| **Mating report** (default on) | User | Per mate: configurations, surface pairings, **`reason:`** per pair; **Rejected (N)** with part-level reasons |
| **Console summary** | User | Rank/score line; **one-line** rejection count → details in report |
| **Algorithm trace** (opt-in) | Developer | Milestones; mategraph branch **reason codes** — [TRACE.md](TRACE.md) |

**Chain:** candidate part → graph alignment (structural evidence) → pose + per-pair fit (geometric gate) → `PartMatch` or `run.explain` → [`mate_report.py`](../src/MateCore/mate_report.py). Macro/micro framing: [Auto-Mating.md](Auto-Mating.md).

```mermaid
flowchart LR
  Sel[Selection]
  Pat[Pattern]
  Align[Alignment]
  PF[Pose and fit]
  Out[PartMatch or RejectedPart]
  Rep[MateReport]
  Sel --> Pat --> Align --> PF --> Out --> Rep
```

## Console output (Report view)

With default settings you typically see:

- `Display phase: N mating part(s).`
- `=== Auto-Mate mating report ===` … pairings, `reason:` lines, rejections … `=== end mating report ===`
- `1. PartName: … score …` per ranked mate
- `N part(s) rejected (see mating report for details).` (not one line per rejected part)
- Face overlays in the 3D view

Set `set_trace_module("report", 2)` for extra display inventory; `set_trace_module("report", 0)` to hide the mating report block.

## Reading order

1. [README.md](../README.md) — install and try it  
2. [Auto-Mating.md](Auto-Mating.md) — domain, design intent, macro/micro  
3. [PYTHON_ARCHITECTURE.md](PYTHON_ARCHITECTURE.md) — MateCore vs FreeCAD, modules  
4. [HEURISTIC_MATE_ALGORITHM.md](HEURISTIC_MATE_ALGORITHM.md) — heuristic pipeline and dials  
5. [MATEGRAPH.md](MATEGRAPH.md) — `PartGraph` and beam search  
6. [TWEAKABLE_PARAMETERS.md](TWEAKABLE_PARAMETERS.md) — caps and tuning  
7. [TRACE.md](TRACE.md) — trace modules and mategraph reason codes  
8. [SPECIFICATION.md](SPECIFICATION.md) — requirements and acceptance  
9. [LEGACY_AAG.md](LEGACY_AAG.md) — optional; historical AAG/VF2 narrative  

## Repo map

| Path | Purpose |
|------|---------|
| `src/MateCore/` | Algorithms, MateGraph, MateFit, report, trace |
| `src/App_FreeCAD/` | FreeCAD adapter |
| `tests/` | Headless pytest |
| `updateProduction.py` | Deploy to FreeCAD Mod |
