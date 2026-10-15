# Auto-Mate Agent Guidelines

These instructions apply to all AI agent sessions working in this repository.

## 1. Interaction and Governance Rules
- **Documentation Changes**: Always suggest and seek explicit permission from the user before creating, updating, or deleting repository documentation (e.g., `README.md`, `Architecture/SPECIFICATION.md`, `Architecture/PYTHON_ARCHITECTURE.md`).
- **Clarification Over Assumption**: When requirements or architecture boundaries are ambiguous, ask clarifying questions before committing to substantial refactoring or package restructuring.
- **Explain Before Refactoring**: When proposing structural reorganizations (e.g., merging packages, removing legacy features), clearly explain the motivation, impact, and proposed layout first.

## 2. Architecture & Source of Truth
- **Single Source of Truth (`src/`)**: All maintained application and domain logic lives under [src/MateCore/](src/MateCore) and [src/App_FreeCAD/](src/App_FreeCAD).
  - **MateCore** — host-independent contracts, the `MateAlgorithm` ABC, `MateAlgo_Heuristic` (default algorithm), `MateGraph`, `MateFit` (descriptors, pose, fits), `postprocessors`, and render planning (no `FreeCAD` imports).
  - **App_FreeCAD** — FreeCAD command, selection, display, document capture, part graph build (`part_graph_build.py`), per-document graph cache (`geometry_cache.py`), optional OCC helpers, and GUI rendering.
  - Never develop or keep core logic exclusively inside the FreeCAD deployment folder (`FeatureTools/`).
- **Naming**: **MateCore** is the library package; **MateAlgorithm** is the ABC (`from MateCore.algorithm import MateAlgorithm`); **MateAlgorithm_Heuristic** is the default workbench implementation (`factory id` `heuristic`); **MateFit** holds face descriptors, pose solving, and fit/tolerance resolution; **MateGraph** holds `PartGraph` build, merge, and search.
- **FreeCAD Module Root (`FeatureTools/`)**: [FeatureTools/](FeatureTools) serves only as the workbench root packaging directory containing FreeCAD entry hooks (`Init.py` and `InitGui.py`).
- **Production Staging & Deployment**:
  - The installed workbench is deployed to `C:\Program Files\FreeCAD 1.1\Mod\FeatureTools`.
  - Always use [updateProduction.py](updateProduction.py) for deployments. It stages `MateCore` and `App_FreeCAD` from `src/`, automatic timestamped backups in `%LOCALAPPDATA%\AutoMate\production-backups`, and Windows UAC self-elevation.
  - Never edit files directly inside the production `Mod` directory.

## 3. FreeCAD & CAD Geometry Guidelines
- **Adapter Separation**: Keep geometry contracts (`SurfaceRef`, `DocumentContext`, `RecognitionRequest`, and `MateAlgorithm`) inside **MateCore**. Do not import `FreeCAD` or `FreeCADGui` into **MateCore**.
- **Topological Adjacency**: In this project, face adjacency is defined as sharing at least one common edge (`face.Edges` sharing `isSame`) within the same object unless cross-object adjacency is explicitly requested.
- **PythonOCC Considerations**:
  - PythonOCC is bundled with FreeCAD at `C:\Program Files\FreeCAD 1.1\bin\Lib\site-packages\OCC`.
  - `Part.__toPythonOCC__` requires importing `OCC.Core.TopoDS` first to prevent `No SWIG wrapped library loaded` runtime errors.
  - Keep PythonOCC optional and do not couple workbench startup or dummy algorithms to PythonOCC imports.
- **Document Non-Destructiveness**: Analysis and selection commands must avoid modifying, mutating, or dirtying active document geometry unless explicitly instructed.

## 4. Testing & Verification Standards
- **Test Runner**: Run automated tests via pytest using the repo root:
  ```powershell
  python -m pytest -q
  ```
- **Test Independence**: Unit tests must run cleanly without requiring an active FreeCAD GUI process or external display.
- **Deployment Verification**:
  - Test updates using `--dry-run` first: `python .\updateProduction.py --dry-run`.
  - After deploying via `python .\updateProduction.py`, verify file hashes between `src/MateCore` / `src/App_FreeCAD` and `Mod\FeatureTools\MateCore` / `Mod\FeatureTools\App_FreeCAD`.
  - Explicitly remind the user that live FreeCAD GUI behavior (command icons, selection gates, workbench menu) requires a smoke test inside a running FreeCAD GUI session.

## 5. Code Style & Minimal Change
- **Minimal, well-structured diffs**: Prefer the smallest change that correctly solves the task. Keep code clear and organized; avoid drive-by edits, unrelated refactors, and scope creep in the same change.
- **Inject as little as feasible**: Add only what safety and the requirement demand—no extra layers, helpers, or abstractions unless they remove real duplication or match existing patterns in the touched area.
- **Reuse before inventing**: Extend existing functions, types, and conventions in the file or package instead of parallel implementations.
- **Comments**: Code should mostly speak for itself; comment only non-obvious intent, invariants, or domain rules—not what the code already states.
- **Tests**: Add or extend tests when they protect meaningful behavior; skip tests that only restate trivial wiring.
- **Readable for the maintainer**: Write code the project owner can follow without decoding clever tricks—straightforward control flow, precise names, and small functions where it aids clarity. When logic is dense or domain-specific, a short comment or docstring on *why* (not a line-by-line narration) is appropriate so future you can understand and change it safely.

<!-- ds-harness:ds-env:begin -->
DSONE_PATH: \\dsone\rnd
DS environment: This project uses a non-official DS environment. Never run skills from ds-bsf or ds-cd.
Workspace kind: Generic. Never run skills from ds-bsf
<!-- ds-harness:ds-env:end -->
