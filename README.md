# Auto-Mate for FreeCAD

Auto-Mate is a FreeCAD workbench that finds **which other parts mate** with the
part you are working on. Select faces on one part; the default **heuristic**
algorithm aligns a graph pattern to candidate parts, checks pose and fit, and
returns a ranked list with a **mating report** that explains pairings and
rejections.

Architecture: [Architecture/OVERVIEW.md](Architecture/OVERVIEW.md).

## Prerequisites

- FreeCAD 1.1 (see [Architecture/SPECIFICATION.md](Architecture/SPECIFICATION.md) for install paths)
- Windows deploy target: `C:\Program Files\FreeCAD 1.1\Mod\FeatureTools`

## Install

From the repository root:

```powershell
python .\updateProduction.py --dry-run
python .\updateProduction.py
```

Restart FreeCAD after a successful deploy. Backups: `%LOCALAPPDATA%\AutoMate\production-backups`.

## Try it (4 steps)

1. Switch to the **Auto-Mate** workbench.
2. Click **Auto-Mate: Select Surfaces** — then select **two or more faces on one part** (typical patterns need multiple faces).
3. Click the command again to **compute**.
4. Open the **Report view** / Python console: look for `=== Auto-Mate mating report ===`, ranked mates (`1. PartName: … score …`), and face **overlays** in the 3D view.

## What success looks like

- `Display phase: N mating part(s).`
- Mating report with `source  ->  mate` lines and `reason:` under each pairing
- `N part(s) rejected (see mating report for details).` when other parts did not mate
- Coloured overlays on matched faces

## Tuning (optional)

In the FreeCAD Python console:

```python
import App_FreeCAD.settings as s
# Alignment-only preview (no pose/fit gate):
s.set_heuristic_skip_pose_fit(True)
# Restore strict checking:
s.set_heuristic_skip_pose_fit(False)
# Silence the mating report block:
s.set_trace_module("report", 0)
```

More dials: [Architecture/OVERVIEW.md](Architecture/OVERVIEW.md), [Architecture/HEURISTIC_MATE_ALGORITHM.md](Architecture/HEURISTIC_MATE_ALGORITHM.md).

## Troubleshooting

- **Stale mates after editing geometry** — graph cache does not auto-refresh; restart FreeCAD or use a fresh document session ([Auto-Mating.md](Architecture/Auto-Mating.md)).
- **Quiet console** — `set_trace_module("report", 0)` hides the report; algorithm trace defaults off ([TRACE.md](Architecture/TRACE.md)).

## Developers

- Source: [`src/MateCore`](src/MateCore) (no FreeCAD), [`src/App_FreeCAD`](src/App_FreeCAD) (adapter)
- Tests: `python -m pytest -q`
- Code layout: [Architecture/PYTHON_ARCHITECTURE.md](Architecture/PYTHON_ARCHITECTURE.md)
