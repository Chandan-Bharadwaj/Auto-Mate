# Auto-Mate FreeCAD Workbench Specification

## 1. Purpose and current scope

Auto-Mate is a Python add-on for the installed FreeCAD application. Its purpose
is **part mating**: given faces selected on one part of an assembly, find which
other parts mate with it and how (see [Auto-Mating.md](Auto-Mating.md) for the
model). The unit of output is the *part*; faces are the evidence for a match.

The workbench is a single FreeCAD GUI command that captures the active document
context, accepts selected faces on one part, runs a replaceable algorithm, and
reports the mating parts ranked best-first. The command and algorithm
boundaries are the extension points; the default algorithm is **`heuristic`**
(graph-pattern beam search with pose/fit; see [OVERVIEW.md](OVERVIEW.md)).
Factory ids `dummy` and `rendering_demo` remain for workflow and render tests.
The command never modifies the model.

## 2. FreeCAD installation and production location

The current FreeCAD installation is:

| Item | Location |
|---|---|
| Application | `C:\Program Files\FreeCAD 1.1` (FreeCAD 1.1.4) |
| FreeCAD modules directory | `C:\Program Files\FreeCAD 1.1\Mod` |
| Production add-on package | `C:\Program Files\FreeCAD 1.1\Mod\FeatureTools` |
| FreeCAD Python executable | `C:\Program Files\FreeCAD 1.1\bin\python.exe` |
| Embedded Python | Python 3.11.14 |
| Bundled PythonOCC package | `C:\Program Files\FreeCAD 1.1\bin\Lib\site-packages\OCC` |
| Add-on source in this repository | `FeatureTools\` |
| Deployment helper | `updateProduction.py` |

`FeatureTools` is the installable module/workbench package, not the repository
root. All add-on source is developed in the repository and copied as a complete
package to the production location by `updateProduction.py`. The installer
requests Windows elevation through UAC when the production directory requires
administrator access, stages the new package before replacement, and preserves
the previous package as a backup.

The user-level FreeCAD add-on directory (`%APPDATA%\FreeCAD\Mod`) does not need
administrator access and is a suitable development alternative. The agreed
production location remains the installed application's `Mod` directory above.

## 3. Product and technology boundaries

- **Host and user interface:** FreeCAD 1.1 GUI, Python command/workbench APIs,
  `FreeCAD`, `FreeCADGui`, and the built-in `Part` geometry objects.
- **Algorithm language:** Python. The pure matching core depends only on numpy.
- **Geometry kernel:** FreeCAD's bundled Open CASCADE integration for native
  B-rep shapes and face selection.
- **PythonOCC:** the current FreeCAD-bundled Python can import `OCC` and
  `OCC.Core.TopoDS`. A smoke test converted a FreeCAD box to PythonOCC and back
  with a valid six-face result after importing `OCC.Core.TopoDS`. Calling the
  conversion hook before loading that SWIG wrapper failed with
  `No SWIG wrapped library loaded`; the successful conversion also emitted
  SWIG deprecation/memory-leak warnings. PythonOCC remains optional for the
  dummy command. Any production adapter must initialize its wrapper explicitly
  and investigate those warnings.
- **Tests:** pytest for host-independent algorithm and deployment tests;
  FreeCAD GUI smoke tests for registration, selection, and display behavior.

FreeCAD's `Part` API is the default interface for the first implementation.
Conversion to PythonOCC and back is an adapter concern, not a dependency of the
command or domain contracts. Prefer the PythonOCC package bundled with this
FreeCAD interpreter rather than an unrelated Python installation.

## 4. User workflow and phases

The command is exposed in the **Auto-Mate** workbench, in its toolbar and menu.
It has three phases:

1. **Selection**
   - The first click on **Auto-Mate: Select Surfaces** snapshots the active
     document context and enters selection mode.
   - The user selects one or more faces in the FreeCAD model view or tree.
   - The command reports that it is waiting for selected faces. If a later
     activation has no face selection, it stays in this phase and asks the user
     to select faces.
2. **Compute**
   - Clicking the command again finalizes the current face selection.
   - The command captures the selected face objects and invokes the algorithm
     with both the document context and the selected surfaces.
   - The command reports the compute phase; the algorithm returns candidate
     parts with their mating configurations.
3. **Display output**
   - The mating parts are listed best-first in FreeCAD's Report view / Python
     console, with the **mating report** (pairings and reasons, default on),
     a one-line rejection summary, and optional trace inventory at `report` level 2+.
   - Each result group's matched faces are drawn as a bright, opaque overlay
     (one palette colour per group) and the part owning them is rendered
     transparent, so the matched surfaces stand out against their part.
   - The look (palette, brightness, surface/part transparency, tint) is defined
     by `RenderStyle` in `rendering/style.py` and can be overridden from the
     FreeCAD preference group `Mod/AutoMate/Render` without code changes.
   - Part transparency is restored and the overlay removed when the next run
     starts. If the overlay cannot be drawn, matched faces fall back to
     FreeCAD selection highlighting.
   - The command remains in the display phase until the next activation starts
     a new selection run.

No document geometry is created, changed, or saved by the command.

The toolbar/menu button changes icon, label and tooltip with the phase
(defined in `App_FreeCAD/phase_ui.py`, icons in `src/App_FreeCAD/icons/`):

| Phase | Icon | Label |
|-------|------|-------|
| Idle | blue circle with play arrow | Auto-Mate: Select Surfaces |
| Selection | yellow face with green check | Auto-Mate: Finish Selection |
| Compute | grey gear | Auto-Mate: Computing |
| Display | four coloured groups | Auto-Mate: New Run |

## 5. Context and algorithm contracts

### Document context

At the start of each run, capture the active document name and a snapshot of
every document object: internal name, label, `TypeId`, group members, and a
best-effort kind (`assembly`, `part`, or `object`). This records all parts and
assemblies present in the command's context without depending on one particular
assembly workbench's object classes. Preserve this snapshot through compute and
display.

### Surface selection

Resolve `Gui.Selection.getSelectionEx()` entries to face subelements. Each
selected surface reference carries its owning document object, object name and
label, face subelement name (for example, `Face3`), and the native FreeCAD face
shape. Ignore whole-object selections that do not identify face subelements.
Deduplicate repeated references to the same object face.

Selection is restricted while the selection phase is active: a FreeCAD
selection gate accepts only `Face<N>` subelements, and after the first face is
selected, only faces on the same **part** (one solid; adjacency is not
required). Compute re-applies the same rule and reports any ignored faces. The
part that owns the selection is the *source part*; every other part is a
candidate.

### Replaceable algorithm

The algorithm receives a request containing the captured document context
(including every part and its faces) and the selected surface references. The
base class resolves the request to a source part and drives a fixed,
part-oriented pipeline; subclasses implement one abstract hook,
`match_part(state, part, run)`, which returns the mating configurations of the
source part with one candidate part.

Its result is part-oriented: `part_matches` (candidate parts ranked best-first,
each with its configurations and score), `rejected_parts` (parts that did not
mate, with a reason), diagnostics and timings. `compute()` remains available and
returns the flat `list[list[SurfaceRef]]` of configuration faces for callers
that only need surfaces. Configurable caps: `max_parts`,
`max_matches_per_part`, `max_results`. Post-processing and ranking exist at
configuration level and part level and default to empty. The **dummy**
implementation returns placeholder groups for workflow tests; production uses
**heuristic** part-oriented `AlgorithmResult`.

The command depends on the algorithm interface, not on a concrete algorithm.

For the default **heuristic** algorithm, `App_FreeCAD` builds a **PartGraph**
per part on demand (`part_graph_build.build_part_graph`) via `PartGraphStore`
and caches it per document name for the FreeCAD session. Repeat mate searches
on the same document reuse that cache. The product assumes the **model geometry
is unchanged** between such runs; there is no automatic invalidation when shapes
are edited in place. See [Auto-Mating.md](Auto-Mating.md) (geometry cache).

## 6. Modular package design

```text
src/
├── MateCore/                      # host-independent library
│   ├── algorithm.py               # MateAlgorithm ABC (part-oriented)
│   ├── context.py                 # document data contracts
│   ├── dummy_algorithm.py
│   ├── MateFit/                   # descriptors, pose, fits
│   ├── MateAlgo_Heuristic/        # production MateAlgorithm_Heuristic
│   ├── MateGraph/                 # PartGraph store + search
│   ├── postprocessors.py          # shared rankers / dedupe
│   ├── mate_match.py              # MateMatch DTO
│   └── rendering/                 # style + render plan (no GUI)
└── App_FreeCAD/                   # FreeCAD adapters
    ├── command.py
    ├── document_context.py        # capture_document_context
    ├── display.py
    ├── part_graph_build.py
    ├── geometry_cache.py
    ├── mate_report.py               # via MateCore copy
    ├── selection.py
    └── rendering/                 # FreeCAD renderer + preferences

FeatureTools/
├── Init.py
└── InitGui.py

updateProduction.py
```

Dependency direction:

```text
FreeCAD InitGui / workbench
            |
            v
   App_FreeCAD/command.py ------> display.py
            |                        ^
            +--> selection.py        |
            +--> document_context.py |
            +--> MateCore (MateAlgorithm) --+
```

Maintained Python lives in `src/MateCore` and `src/App_FreeCAD`. `FeatureTools`
holds only startup hooks. The updater copies both packages from `src/` into
`Mod\FeatureTools`. New mating logic belongs in **MateCore** (typically
`MateAlgo_Heuristic` or a new `MateAlgorithm` subclass), not in the command.

## 7. Deployment and development

From the repository root:

```powershell
python .\updateProduction.py --dry-run
python .\updateProduction.py
```

The dry run reports the startup-file source, application source, and
destination without changing files. A normal update validates both source
packages, requests
elevation if required, stages a combined copy, moves the current production
package to a timestamped backup under
`%LOCALAPPDATA%\AutoMate\production-backups`, then installs the new package.
The script supports `--source` and `--target` for an explicitly chosen startup
package or FreeCAD module directory, and `--app-source` for an explicitly
chosen application package. Restart FreeCAD after deployment to load the
updated workbench.

Develop and test the algorithm without FreeCAD installed. Validate the GUI
adapters in FreeCAD itself: select the Auto-Mate workbench, open a document,
click the command once, select faces, click it again, and confirm grouped
results and highlights. A standalone import of `FreeCADGui` in the bundled
Python does not expose `Workbench` or `addCommand`; command registration must
therefore be verified inside an actual FreeCAD GUI session.

## 8. Acceptance criteria

1. FreeCAD discovers and displays the Auto-Mate workbench and command.
2. The first command activation enters selection phase and snapshots every
   document object, including parts and assemblies.
3. Only face selections are accepted as surface inputs, and only faces on the
   same part as the first selected face; a missing face
   selection leaves the command in selection phase with an actionable message.
4. The second activation invokes the algorithm with the context and selected
   surfaces.
5. The result is part-oriented: candidate parts ranked best-first with their
   mating configurations, plus rejected parts with reasons (detailed in the
   mating report when `report` trace is on, default).
6. Display reports each mating part, prints the mating report and rejection
   summary, and highlights matched faces without changing document geometry.
7. The algorithm can be replaced without rewriting selection, workbench, or
   display adapters.
8. The updater dry run makes no changes; a real update stages the package,
   preserves a backup, and reports failures rather than claiming success.
9. Host-independent tests pass. GUI behavior is smoke-tested in the installed
   FreeCAD version before release.

## 9. Explicitly deferred

- Geometric verification of matches (contact area, interference), surfaces
  other than planes and cylinders, and sub-assembly-aware part grouping.
- Importing STEP files or constructing an assembly.
- Editing or creating document objects, constraints, or placements.
- Persistent result objects, result serialization, or automated screenshots.
- PythonOCC conversion until a compatible runtime is verified.
