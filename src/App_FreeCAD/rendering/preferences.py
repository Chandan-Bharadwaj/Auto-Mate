"""Load render style overrides and trace settings from FreeCAD user preferences."""

from __future__ import annotations

from typing import Any

from MateCore.rendering.style import (
    DEFAULT_STYLE,
    RenderStyle,
    style_from_mapping,
)
from MateCore.trace import KNOWN_MODULES, set_default_trace_level, set_global_trace_enabled
from MateCore.trace import set_module_trace_level

PREFERENCE_PATH = "User parameter:BaseApp/Preferences/Mod/AutoMate/Render"
SETTINGS_PATH = "User parameter:BaseApp/Preferences/Mod/AutoMate"

TRACE_ENABLED_KEY = "TraceEnabled"
TRACE_DEFAULT_LEVEL_KEY = "TraceDefaultLevel"
TRACE_MODE_KEY = "TraceMode"
DEBUG_MODE_KEY = "DebugMode"

_MODULE_LEVEL_PREFIX = "TraceLevel_"

_OVERRIDABLE = {
    "surface_brightness": float,
    "surface_transparency": int,
    "part_transparency": int,
    "tessellation_tolerance": float,
}


def _module_pref_key(module: str) -> str:
    return f"{_MODULE_LEVEL_PREFIX}{module}"


def read_trace_global_enabled() -> bool:
    try:
        import FreeCAD

        group = FreeCAD.ParamGet(SETTINGS_PATH)
        if group.GetBool("TraceMigratedFromLegacy", False):
            return bool(group.GetBool(TRACE_ENABLED_KEY, False))
        if group.GetInt(TRACE_DEFAULT_LEVEL_KEY, -1) >= 0:
            return True
        if group.GetInt(TRACE_MODE_KEY, 0) > 0:
            return True
        if group.GetBool(DEBUG_MODE_KEY, False):
            return True
        return bool(group.GetBool(TRACE_ENABLED_KEY, False))
    except Exception:
        from MateCore.trace import is_global_trace_enabled

        return is_global_trace_enabled()


def read_trace_default_level() -> int:
    try:
        import FreeCAD

        group = FreeCAD.ParamGet(SETTINGS_PATH)
        default = int(group.GetInt(TRACE_DEFAULT_LEVEL_KEY, -1))
        if default >= 0:
            return default
        level = int(group.GetInt(TRACE_MODE_KEY, 0))
        if level <= 0 and group.GetBool(f"{TRACE_MODE_KEY}LegacyBool", False):
            return 1
        return max(0, level)
    except Exception:
        from MateCore.trace import get_default_trace_level

        return get_default_trace_level()


def read_module_trace_level(module: str) -> int | None:
    try:
        import FreeCAD

        group = FreeCAD.ParamGet(SETTINGS_PATH)
        key = _module_pref_key(module)
        level = int(group.GetInt(key, -1))
        if level < 0:
            if module == "report":
                legacy = int(group.GetInt(_module_pref_key("result"), -1))
                if legacy >= 0:
                    return legacy
                if group.GetBool(DEBUG_MODE_KEY, False):
                    return 1
            return None
        return level
    except Exception:
        from MateCore.trace import get_module_trace_level

        return get_module_trace_level(module)


def sync_trace_from_preferences() -> None:
    """Load FreeCAD trace preferences into MateCore."""
    from MateCore.trace import clear_module_trace_level

    set_global_trace_enabled(read_trace_global_enabled())
    set_default_trace_level(read_trace_default_level())
    for module in KNOWN_MODULES:
        clear_module_trace_level(module)
        level = read_module_trace_level(module)
        if level is not None:
            set_module_trace_level(module, level)


def load_style(base: RenderStyle = DEFAULT_STYLE) -> RenderStyle:
    """Read overrides from the FreeCAD preference group, if available."""
    try:
        import FreeCAD

        group = FreeCAD.ParamGet(PREFERENCE_PATH)
        values: dict[str, Any] = {}
        for name, cast in _OVERRIDABLE.items():
            default = getattr(base, name)
            getter = group.GetFloat if cast is float else group.GetInt
            values[name] = getter(name, default)
        return style_from_mapping(values, base)
    except Exception:
        return base
