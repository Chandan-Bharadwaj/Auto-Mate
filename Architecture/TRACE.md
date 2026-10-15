# Auto-Mate trace protocol

All timing and diagnostic logging uses one host-independent API in `MateCore/trace.py`. FreeCAD mirrors preferences into MateCore before each compute run and attaches a console sink for that run.

## Levels (shared by every module)

| Level | Name | Typical output |
|------:|------|----------------|
| 0 | off | Nothing for that module |
| 1 | high | Stage spans, timings, summaries |
| 2 | deep | **Phase milestones** (decorated context) + graph build, beam search summary, factory/command wiring |
| 3 | verbose | Everything at level 2 **plus** per-step decisions (beam expand/prune, heuristic accept/reject) |

Level 1 does **not** emit milestone banners (keeps the console quieter at “high only”).

## Phase milestones (`trace_milestone`)

At levels **2 and 3**, modules emit a short banner and a few `key=value` context lines at major phase boundaries (see table below). Use `trace_milestone(module, title, context={...})` in code.

| Module | Milestones | Example context |
|--------|------------|-----------------|
| `run` | validate, prepare, candidates, match_parts | algorithm, selected_faces, candidate_count |
| `heuristic` | prepare, metadata_filter, match_part | source_part, slots, topology_profile, target_part |
| `mategraph` | graph_build, alignment_search | part_id, slots, beam_width, faces |
| `command` | compute | algorithm, document, face_count |
| `factory` | create_algorithm | algorithm_id |
| `cache` | graph_build | part_id, face_count |

## Controls

1. **Global switch** — when off, algorithm trace modules are silent. MateCore and FreeCAD both default to **global off** and **default level 0**; only module **`report`** is on (level 1) unless you set `TraceLevel_report=0`.
2. **Default level** — applies to any module without its own override.
3. **Per-module level** — override for one area; `0` turns that module off while others can stay on.

```python
import App_FreeCAD.settings as s
from App_FreeCAD.settings import set_trace_module

s.trace_global = True
s.trace_default = 2              # milestones + deep lines for all modules
set_trace_module("heuristic", 3) # + every heuristic decision
set_trace_module("mategraph", 3) # + every beam step
set_trace_module("report", 0)    # silence mating report (default is on)
set_trace_module("report", 2)    # + document inventory and render legend in display
```

## Display console (module `report`)

The mating report (surface pairings and reasons) is **on by default** (`report` level 1), even when global trace is off.

When `report` is off (`0`), the Report view shows only:

- Mating rank / score summary
- A one-line rejection count (not every rejected part)
- Warnings

With `report` on (default), per-part rejection reasons appear inside the **mating report** block; the console also prints a single summary line pointing to that block.

Overlays and highlighting still run. With `report` ≥ 2 (`TRACE_DEEP`), display also prints document object inventory, per-group face lists, and render legend text.

## Registered modules

| ID | Area |
|----|------|
| `run` | `MateAlgorithm.run` template |
| `heuristic` | Heuristic alignment + pose/fit validation |
| `mategraph` | Graph store + beam alignment search |
| `cache` | Document part-graph cache |
| `factory` | Algorithm factory |
| `command` | Command compute path |
| `report` | Mating result report (default on); display inventory at level 2+ |

## Mategraph level 3 (beam search reasons)

At `set_trace_module("mategraph", 3)`, beam lines include explicit **reason** codes:

| Reason | Meaning |
|--------|---------|
| `surface_kind_mismatch` | Pattern slot kind ≠ target node kind |
| `axis_misaligned` | Axis dot below angle tolerance |
| `below_min_similarity` | Weighted similarity below policy minimum (includes poor radius/area match) |
| `descriptor_missing` | Mating comparator could not build face descriptor |
| `kinds_incompatible` | `FitResolver.kinds_compatible` failed |
| `plane_axis_not_parallel` | Plane normals not parallel (only when partial map non-empty) |
| `neighbor_angle_mismatch` | Adjacent mapped plane angle pattern mismatch |
| `flank_spacing_mismatch` | Flank span vs pattern metadata |
| `target_already_mapped` | Target node id already used in partial map |
| `missing_target_node` | Node id not in target graph |
| `no_index_candidates` | Candidate index returned empty pool |
| `partial_pruned` | `should_prune_partial` rejected branch |

**Assign** and **complete** lines include a score breakdown: `total=… cov=… node=… edge=… pen=…`, plus `sim=…` on assign when applicable. **Beam trim** logs how many states were dropped after sorting.

## Verbose caps

Beam search verbose output is capped at 500 events per round; additional expansions are summarized in one line. See `MateGraph/search/searcher.py`.

## Headless / pytest

```python
from MateCore.trace import (
    MODULE_HEURISTIC,
    TRACE_VERBOSE,
    reset_trace_state,
    set_global_trace_enabled,
    set_module_trace_level,
    set_trace_sink,
)

lines = []
reset_trace_state()
set_global_trace_enabled(True)
set_module_trace_level(MODULE_HEURISTIC, TRACE_VERBOSE)
set_trace_sink(lines.append)
# ... run algorithm ...
set_trace_sink(None)
reset_trace_state()
```

## `debug_mate_graph` algorithm

An **algorithm id** (`s.algorithm = "debug_mate_graph"`), not a trace toggle. Use module `mategraph` for build/search trace.
