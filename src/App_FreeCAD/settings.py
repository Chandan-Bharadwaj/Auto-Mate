"""Session-scoped Auto-Mate settings (set from the FreeCAD Python console)."""

from __future__ import annotations

import sys
import types

from MateCore.trace import (
    KNOWN_MODULES,
    TRACE_HIGH,
    TRACE_OFF,
    clear_module_trace_level,
    get_default_trace_level,
    get_module_trace_level,
    is_global_trace_enabled,
    module_trace_levels,
    set_default_trace_level,
    set_global_trace_enabled,
    set_module_trace_level,
)

from MateCore.MateAlgo_Heuristic import HeuristicMateConfig

from .algorithm_factory import known_algorithms, normalize_algorithm_name
from .rendering.preferences import (
    SETTINGS_PATH,
    TRACE_DEFAULT_LEVEL_KEY,
    TRACE_ENABLED_KEY,
    TRACE_MODE_KEY,
    _module_pref_key,
)

_algorithm: str = "heuristic"
_VALIDATION_MODES = frozenset({"strict", "warn", "skip"})
_heuristic_pose_validation: str = "strict"
_heuristic_fit_validation: str = "strict"
_heuristic_nominal_fit_gap_mm: float | None = None


def get_algorithm() -> str:
    return _algorithm


def get_trace_global() -> bool:
    return is_global_trace_enabled()


def set_trace_global(enabled: bool) -> None:
    set_global_trace_enabled(bool(enabled))
    _persist_trace_prefs()
    state = "on" if enabled else "off"
    _notify(f"Auto-Mate trace global {state}.\n")


def get_trace_default() -> int:
    return get_default_trace_level()


def set_trace_default(level: int) -> None:
    set_default_trace_level(max(TRACE_OFF, int(level)))
    _persist_trace_prefs()
    _notify(
        f"Auto-Mate trace default level {level} "
        "(0=off, 1=high, 2=deep, 3=verbose).\n"
    )


def get_trace_module(module: str) -> int | None:
    return get_module_trace_level(module)


def set_trace_module(module: str, level: int) -> None:
    if module not in KNOWN_MODULES:
        raise ValueError(
            f"Unknown trace module '{module}'. Known: {', '.join(KNOWN_MODULES)}"
        )
    set_module_trace_level(module, max(TRACE_OFF, int(level)))
    _persist_trace_prefs()
    _notify(f"Auto-Mate trace module '{module}' level {level}.\n")


def clear_trace_module(module: str) -> None:
    clear_module_trace_level(module)
    _persist_trace_prefs()
    _notify(f"Auto-Mate trace module '{module}' uses default level.\n")


def get_trace_modules() -> dict[str, int]:
    return module_trace_levels()


def get_trace() -> int:
    """Default trace level (backward-compatible alias)."""
    return get_trace_default()


def set_trace(level: int | bool) -> None:
    """Set default trace level (bool True/False maps to 1/0)."""
    if isinstance(level, bool):
        level = TRACE_HIGH if level else TRACE_OFF
    set_trace_default(int(level))


def _normalize_validation_mode(mode: str) -> str:
    key = str(mode).strip().lower()
    if key not in _VALIDATION_MODES:
        raise ValueError(
            f"Unknown validation mode '{mode}'. Use: strict, warn, or skip."
        )
    return key


def get_heuristic_pose_validation() -> str:
    return _heuristic_pose_validation


def set_heuristic_pose_validation(mode: str) -> None:
    global _heuristic_pose_validation
    _heuristic_pose_validation = _normalize_validation_mode(mode)
    _notify(
        f"Auto-Mate heuristic pose_validation={_heuristic_pose_validation}.\n"
    )


def get_heuristic_fit_validation() -> str:
    return _heuristic_fit_validation


def set_heuristic_fit_validation(mode: str) -> None:
    global _heuristic_fit_validation
    _heuristic_fit_validation = _normalize_validation_mode(mode)
    _notify(
        f"Auto-Mate heuristic fit_validation={_heuristic_fit_validation}.\n"
    )


def set_heuristic_skip_pose_fit(skip: bool) -> None:
    """When True, skip pose solve and fit gate (alignment-only preview)."""
    mode = "skip" if skip else "strict"
    global _heuristic_pose_validation, _heuristic_fit_validation
    _heuristic_pose_validation = mode
    _heuristic_fit_validation = mode
    state = "off (skip)" if skip else "on (strict)"
    _notify(f"Auto-Mate heuristic pose+fit validation {state}.\n")


def get_heuristic_nominal_fit_gap_mm() -> float | None:
    return _heuristic_nominal_fit_gap_mm


def set_heuristic_nominal_fit_gap_mm(gap_mm: float | None) -> None:
    """Max allowed clearance (mm) for heuristic fit band 0..gap; None = exact contact."""
    global _heuristic_nominal_fit_gap_mm
    if gap_mm is not None:
        _heuristic_nominal_fit_gap_mm = float(gap_mm)
        _notify(f"Auto-Mate heuristic nominal_fit_gap_mm={_heuristic_nominal_fit_gap_mm}.\n")
    else:
        _heuristic_nominal_fit_gap_mm = None
        _notify("Auto-Mate heuristic nominal_fit_gap_mm disabled (exact contact).\n")


def get_heuristic_mate_config() -> HeuristicMateConfig:
    return HeuristicMateConfig(
        pose_validation=_heuristic_pose_validation,
        fit_validation=_heuristic_fit_validation,
        nominal_fit_gap_mm=_heuristic_nominal_fit_gap_mm,
    )


def set_algorithm(name: str) -> None:
    """Select the mate algorithm for the next compute run."""
    global _algorithm
    canonical = normalize_algorithm_name(name)
    ids = known_algorithms()
    if canonical not in ids:
        raise ValueError(
            f"Unknown algorithm '{name}'. Known algorithms: {', '.join(ids)}"
        )
    _algorithm = canonical
    _notify(f"Auto-Mate algorithm set to '{canonical}'.\n")


def _persist_trace_prefs() -> None:
    try:
        import FreeCAD

        group = FreeCAD.ParamGet(SETTINGS_PATH)
        group.SetBool(TRACE_ENABLED_KEY, is_global_trace_enabled())
        group.SetInt(TRACE_DEFAULT_LEVEL_KEY, get_default_trace_level())
        group.SetInt(TRACE_MODE_KEY, get_default_trace_level())
        group.SetBool(f"{TRACE_MODE_KEY}LegacyBool", False)
        group.SetBool("TraceMigratedFromLegacy", True)
        for module in KNOWN_MODULES:
            key = _module_pref_key(module)
            level = get_module_trace_level(module)
            if level is None:
                group.SetInt(key, -1)
                continue
            group.SetInt(key, level)
    except Exception:
        pass


def _notify(message: str) -> None:
    try:
        import FreeCAD

        FreeCAD.Console.PrintMessage(message)
    except Exception:
        pass


class _SettingsModule(types.ModuleType):
    def __getattr__(self, name: str):
        if name == "algorithm":
            return get_algorithm()
        if name == "trace_global":
            return get_trace_global()
        if name == "trace_default":
            return get_trace_default()
        if name == "trace_modules":
            return get_trace_modules()
        if name == "trace":
            return get_trace()
        if name == "heuristic_pose_validation":
            return get_heuristic_pose_validation()
        if name == "heuristic_fit_validation":
            return get_heuristic_fit_validation()
        if name == "heuristic_skip_pose_fit":
            return (
                get_heuristic_pose_validation() == "skip"
                and get_heuristic_fit_validation() == "skip"
            )
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    def __setattr__(self, name: str, value) -> None:
        if name == "algorithm":
            set_algorithm(str(value))
        elif name == "trace_global":
            set_trace_global(bool(value))
        elif name == "trace_default":
            set_trace_default(int(value))
        elif name == "trace":
            if isinstance(value, bool):
                set_trace(value)
            else:
                set_trace(int(value))
        elif name == "heuristic_pose_validation":
            set_heuristic_pose_validation(str(value))
        elif name == "heuristic_fit_validation":
            set_heuristic_fit_validation(str(value))
        elif name == "heuristic_skip_pose_fit":
            set_heuristic_skip_pose_fit(bool(value))
        else:
            super().__setattr__(name, value)


if not isinstance(sys.modules[__name__], _SettingsModule):
    sys.modules[__name__].__class__ = _SettingsModule
