# Tweakable parameters reference

Catalog of configuration knobs for Auto-Mate mating: defaults, effects, and how to change them (FreeCAD session vs code-only). Related: [`HEURISTIC_MATE_ALGORITHM.md`](HEURISTIC_MATE_ALGORITHM.md), [`MATEGRAPH.md`](MATEGRAPH.md).

---

## 1. FreeCAD workbench session (`App_FreeCAD/settings.py`)

These affect the next **heuristic** run via `get_heuristic_mate_config()` and `create_algorithm()`.

| Parameter | API | Default | Effect |
|-----------|-----|---------|--------|
| Algorithm | `set_algorithm` / `get_algorithm` | `"heuristic"` | `heuristic`, `debug_mate_graph`, or registered demos |
| Pose validation | `set_heuristic_pose_validation` | `"strict"` | `strict` \| `warn` \| `skip` — pose gate after alignment |
| Fit validation | `set_heuristic_fit_validation` | `"strict"` | Same modes for fit assessment |
| Skip pose + fit | `set_heuristic_skip_pose_fit(True)` | off | Sets both validations to `skip` (alignment-only preview) |
| Nominal fit gap (max clearance) | `set_heuristic_nominal_fit_gap_mm(g)` / `None` | `None` | When active, fit band is **0..g** mm (`clearance_fit`); `None` = exact contact (0). Active if pattern is **axis-aligned** or includes any **cylinder** slot |
| Trace global | `set_trace_global` | from prefs | Enables trace system |
| Trace default level | `set_trace_default` | from prefs | 0=off, 1=high, 2=deep, 3=verbose |
| Per-module trace | `set_trace_module(module, level)` | — | Overrides for `MODULE_HEURISTIC`, `MODULE_REPORT`, etc. |

**Not wired through settings** (always `HeuristicMateConfig` defaults unless the algorithm is constructed in code): `enricher`, `topology_profile`, `flank_spacing_rel_tol`, `hub_node_weight`, `plane_shape_reject_floor`, `plane_shape_penalty_exponent`.

**Factory run caps** (`algorithm_factory.py`): `AlgorithmConfig(max_parts=10, max_matches_per_part=5)` — fixed in the factory, not user settings.

---

## 2. Heuristic mate config (`HeuristicMateConfig`)

Source: `src/MateCore/MateAlgo_Heuristic/config.py`.

| Field | Default | Role |
|-------|---------|------|
| `fit_validation` | `"strict"` | Failed fit → reject pose (or warn/skip) |
| `pose_validation` | `"strict"` | Failed pose → reject (or warn/skip) |
| `enricher` | `"selection_only"` | `selection_only` \| `one_hop_analytic` — pattern growth from selection |
| `topology_profile` | `"default"` | `coarse` → lighter edge weighting in search policy |
| `flank_spacing_rel_tol` | `0.05` | Relative tolerance on U-slot flank span vs mapped neighbors |
| `hub_node_weight` | `2.0` | Beam score weight for hub slots in flank topology |
| `nominal_fit_gap_mm` | `None` | Max clearance (mm); enables 0..max band when axis-aligned or pattern has a cylinder |
| `plane_shape_reject_floor` | `0.15` | Planes: hard reject if `area_ratio × aspect_ratio` below this |
| `plane_shape_penalty_exponent` | `2.0` | Planes: multiply node similarity by `raw^exponent` |

**Axis alignment** is not a config field: it is computed from the pattern using `FitResolver.angle_tolerance` (see §4).

**Single-face selection** is always allowed (no minimum face count gate).

---

## 3. Graph alignment search (`MatingAlignmentSearchPolicy`)

Source: `src/MateCore/MateAlgo_Heuristic/policy.py`. Built in `_build_policy()` from fit resolver tolerances + `HeuristicMateConfig`. **Not** exposed in FreeCAD settings today.

| Field | Default | Role |
|-------|---------|------|
| `beam_width` | `32` | Beam search width |
| `max_candidates` | `16` | Alignments per target part (also `max_alignments_per_part` on algorithm constructor) |
| `node_min_similarity` | `0.3` | Minimum node similarity to keep a mapping |
| `len_tol` | from `FitResolver` `abs_len` | Length tolerance in comparators / flank spacing |
| `angle_tol` | from `FitResolver` `abs_angle` | Angular tolerance (search, flank, axis alignment) |
| `missing_edge_penalty` | `0.25` | Score penalty for missing pattern edges |
| `unmapped_slot_penalty` | `0.15` | Unmapped non-anchor slots |
| `unmapped_anchor_penalty` | `0.5` | Unmapped anchor slots |
| `weight_node` | `0.4` | Alignment score: node term |
| `weight_edge` | `0.35` | Edge term |
| `weight_coverage` | `0.15` | Slot coverage |
| `weight_anchor_coverage` | `0.1` | Anchor coverage |
| `flank_spacing_rel_tol` | from mate config | Passed into `MatingNodeComparator` |
| `plane_shape_reject_floor` / `plane_shape_penalty_exponent` | from mate config | Plane size/shape gate |

**`topology_profile == "coarse"`** (`coarse_topology` classmethod): sets `weight_edge=0.1`, `missing_edge_penalty=0.05`; other kwargs still apply.

**Inner node comparator** (heuristic mating): `compare_node_axis=False` — direct slot↔target axis match is off; relational checks remain.

**Hardcoded (not configurable):**

- Neighbor plane angle consistency: `abs(pat_ang - tgt_ang) > 0.15` in `policy.py`.
- First assigned slot: kind-only similarity `1.0` on empty partial mapping.

**Flank annotate** (`annotate_flank_topology` in `flank_index.py`): `angle_tol`, `hub_node_weight`, `flank_node_weight=1.0` (latter not on `HeuristicMateConfig`).

---

## 4. Fit, clearance, and tolerance (`MateFit/fits.py`)

Workbench uses default `FitResolver()` → **`exact_fit()`** (0 gap target) unless `build_heuristic_fit_resolver` applies **`clearance_fit(0, max)`** when `nominal_fit_gap_mm` is set and the policy is active.

### `Tolerance` (on each `FitType`)

| Field | Default | Role |
|-------|---------|------|
| `abs_len` | `1e-3` mm | Base length tolerance |
| `rel_len` | `0.0` | Added as `rel_len * |nominal|` for radii |
| `abs_angle` | `1e-3` rad | Angle / taper checks; drives `FitResolver.angle_tolerance` (max across policy) |

### `FitPolicy`

| Piece | Role |
|-------|------|
| `default` | e.g. `exact_fit()`, `clearance_fit(min, max)`, `BandFit("nominal", g, g)` |
| `overrides` | Per `(sel_kind, cand_kind)` fit types |

Factory helpers: `exact_fit`, `clearance_fit`, `interference_fit`, `transition_fit`.

**Evaluation behavior:**

- **Point band** (`lo == hi`): `exact` if \|gap − target_gap\| ≤ len_tol; else clearance/interference vs target.
- **Wide band**: sign-based exact/clearance/interference.
- **Shaft/hole**: same convexity on cylinder/cone → incompatible.

**Heuristic max-clearance path:** `build_heuristic_fit_resolver` swaps policy to `clearance_fit(0, nominal_fit_gap_mm)` when `nominal_fit_gap_mm > 0` and the pattern is **axis-aligned** or contains a **cylinder** slot. Pairs with positive gap within the band classify as **`clearance`** / **`clearance_fit`**.

**Custom runs:** pass `FitResolver(FitPolicy(clearance_fit(0, 0.1)))` into `MateAlgorithm_Heuristic(resolver=...)`.

---

## 5. Algorithm run limits (`AlgorithmConfig`)

Source: `src/MateCore/algorithm.py`.

| Field | Factory default (heuristic) | Role |
|-------|-----------------------------|------|
| `max_parts` | `10` | Cap candidate parts |
| `max_matches_per_part` | `5` | Configurations per part |
| `max_results` | `None` | Global configuration cap |
| `time_budget_s` | `None` | Cooperative cancel by time |
| `seed` | `None` | Reproducibility if used |

---

## 6. Part graph build (`GraphBuildOptions`)

Source: `src/MateCore/MateGraph/options.py`. Set in `algorithm_factory.py` from default fit tolerance.

| Field | Heuristic | Debug mate graph |
|-------|-----------|------------------|
| `tol_len` | `FitResolver` `abs_len` | same |
| `tol_angle` | `FitResolver` `abs_angle` | same |
| `merge_smooth` | `True` | `False` |

Affects AAG merge/smooth neighbors and cache key.

---

## 7. Rendering and display (`App_FreeCAD/rendering/preferences.py`)

FreeCAD user prefs under `Mod/AutoMate/Render`:

| Key | Type | Role |
|-----|------|------|
| `surface_brightness` | float | Highlight style |
| `surface_transparency` | int | |
| `part_transparency` | int | |
| `tessellation_tolerance` | float | Mesh quality for overlays |

Trace prefs: `TraceEnabled`, `TraceDefaultLevel`, per-module `TraceLevel_*`.

**Mate report** (console when trace ≥ HIGH): alignment score, fit class, gap, `axis_aligned`, `nominal_gap_mm`, `mate_configuration_kind` — tolerance values are not printed.

---

## 8. Match outputs (read-only, not knobs)

On each **`HeuristicMatch`** / `metadata`:

| Key / field | Meaning |
|-------------|---------|
| `axis_aligned`, `max_axis_misalignment_rad` | Pattern-level axis alignment |
| `nominal_fit_gap_mm` | Effective nominal gap when applicable |
| `fit_classes`, `pair_gaps` | Per-pair fit labels and signed gaps (mm) |
| `mate_configuration_kind` | `exact_fit`, `clearance_fit`, `interference`, `rejected` |
| `graph_alignment_score` | Beam alignment total |
| `fits[]` | `FitResult`: `fit_class`, `gap`, `ok`, `residual` |

---

## Quick reference: common goals

| Goal | Where to tweak |
|------|----------------|
| Loose shaft/hole matching | Custom `FitResolver` + clearance band (code/tests); no workbench UI |
| Design clearance when selection is coaxial | `set_heuristic_nominal_fit_gap_mm` |
| Stricter angles in search + axis-aligned check | `Tolerance.abs_angle` on fit policy (code) |
| Stricter plane rectangle matching | Lower `plane_shape_reject_floor` or raise `plane_shape_penalty_exponent` (code) |
| Faster/sloppier topology match | `topology_profile="coarse"` or raise beam/candidate limits (code) |
| Alignment-only debug | `set_heuristic_skip_pose_fit(True)` |
| More mates in results | Raise `max_parts` / `max_matches_per_part` in factory or `AlgorithmConfig` |
