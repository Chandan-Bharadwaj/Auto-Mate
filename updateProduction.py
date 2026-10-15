"""Deploy the repository's FeatureTools add-on to the FreeCAD production Mod folder."""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

PACKAGE_NAME = "FeatureTools"
APP_SOURCE_ROOT = Path(__file__).resolve().parent / "src"
APP_PACKAGE_NAMES = ("MateCore", "App_FreeCAD")
DEFAULT_TARGET = (
    Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    / "FreeCAD 1.1"
    / "Mod"
    / PACKAGE_NAME
)


def _app_required_paths(root: Path) -> tuple[Path, ...]:
    return (
        root / "MateCore" / "__init__.py",
        root / "MateCore" / "algorithm.py",
        root / "MateCore" / "context.py",
        root / "MateCore" / "dummy_algorithm.py",
        root / "MateCore" / "MateAlgo_Heuristic" / "algorithm_heuristic.py",
        root / "App_FreeCAD" / "__init__.py",
        root / "App_FreeCAD" / "command.py",
        root / "App_FreeCAD" / "document_context.py",
        root / "App_FreeCAD" / "display.py",
        root / "App_FreeCAD" / "selection.py",
        root / "App_FreeCAD" / "occ_parts.py",
    )


def validate_app_packages(package_root: Path) -> None:
    missing = [path for path in _app_required_paths(package_root) if not path.is_file()]
    if missing:
        formatted = "\n".join(f"  {path}" for path in missing)
        raise FileNotFoundError(f"Incomplete application source; missing:\n{formatted}")


def validate_source(source: Path) -> None:
    required = (source / "Init.py", source / "InitGui.py")
    missing = [path for path in required if not path.is_file()]
    if missing:
        formatted = "\n".join(f"  {path}" for path in missing)
        raise FileNotFoundError(f"Incomplete add-on source; missing:\n{formatted}")


def validate_deployment(source: Path, app_source_root: Path) -> None:
    validate_source(source)
    validate_app_packages(app_source_root)


def install_package(
    source: Path,
    target: Path,
    app_source_root: Path = APP_SOURCE_ROOT,
) -> Path | None:
    source = source.resolve()
    target = target.resolve()
    app_source_root = app_source_root.resolve()
    if source == target or source in target.parents:
        raise ValueError("The production target must not be inside the source package.")
    if app_source_root == target or app_source_root in target.parents:
        raise ValueError("The production target must not be inside the application source.")

    validate_deployment(source, app_source_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f".{PACKAGE_NAME}-staging-{os.getpid()}"
    if staging.exists():
        raise FileExistsError(f"Staging path already exists: {staging}")

    backup: Path | None = None
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    try:
        shutil.copytree(source, staging, ignore=ignore)
        for package_name in APP_PACKAGE_NAMES:
            shutil.copytree(
                app_source_root / package_name,
                staging / package_name,
                ignore=ignore,
            )
        validate_source(staging)
        validate_app_packages(staging)
        if target.exists():
            local_app_data = Path(
                os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
            )
            backup_root = local_app_data / "AutoMate" / "production-backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = backup_root / f"{timestamp}-{PACKAGE_NAME}"
            shutil.move(str(target), str(backup))
        try:
            os.replace(staging, target)
        except OSError:
            if backup is not None and backup.exists() and not target.exists():
                shutil.move(str(backup), str(target))
                backup = None
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    return backup


def _is_windows_admin() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def _is_under_program_files(path: Path) -> bool:
    if os.name != "nt":
        return False
    roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    ]
    candidate = path.resolve()
    for root in roots:
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            continue
        return True
    return False


class _ShellExecuteInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("fMask", ctypes.c_ulong),
        ("hwnd", ctypes.c_void_p),
        ("lpVerb", ctypes.c_wchar_p),
        ("lpFile", ctypes.c_wchar_p),
        ("lpParameters", ctypes.c_wchar_p),
        ("lpDirectory", ctypes.c_wchar_p),
        ("nShow", ctypes.c_int),
        ("hInstApp", ctypes.c_void_p),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", ctypes.c_wchar_p),
        ("hkeyClass", ctypes.c_void_p),
        ("dwHotKey", ctypes.c_ulong),
        ("hIconOrMonitor", ctypes.c_void_p),
        ("hProcess", ctypes.c_void_p),
    ]


def _run_elevated(arguments: Sequence[str]) -> int:
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_ShellExecuteInfo)]
    shell32.ShellExecuteExW.restype = ctypes.c_int
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel32.WaitForSingleObject.restype = ctypes.c_ulong
    kernel32.GetExitCodeProcess.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    kernel32.GetExitCodeProcess.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    params = subprocess.list2cmdline(
        [str(Path(__file__).resolve()), *arguments, "--elevated-child"]
    )
    info = _ShellExecuteInfo()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x00000040 | 0x00000100
    info.lpVerb = "runas"
    info.lpFile = sys.executable
    info.lpParameters = params
    info.lpDirectory = str(Path(__file__).resolve().parent)
    info.nShow = 1
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        error_code = ctypes.get_last_error()
        if error_code == 1223:
            print("Administrator approval was cancelled; production was not changed.")
            return 1
        raise OSError(error_code, "Could not start the updater with administrator rights.")

    try:
        kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        exit_code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(exit_code.value)
    finally:
        kernel32.CloseHandle(info.hProcess)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage and deploy the Auto-Mate FreeCAD add-on."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(__file__).resolve().parent / PACKAGE_NAME,
        help="repository FreeCAD module startup-files directory",
    )
    parser.add_argument(
        "--app-source",
        type=Path,
        default=APP_SOURCE_ROOT,
        help="repository src/ directory containing MateCore and App_FreeCAD",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="production add-on package directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print paths without changing production",
    )
    parser.add_argument("--elevated-child", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    args = _parse_args(raw_arguments)
    source = args.source.resolve()
    app_source_root = args.app_source.resolve()
    target = args.target.resolve()
    validate_deployment(source, app_source_root)

    if args.dry_run:
        print(f"Source:      {source}")
        print(f"App source:  {app_source_root}")
        print(f"Packages:    {', '.join(APP_PACKAGE_NAMES)}")
        print(f"Destination: {target}")
        print("Dry run complete; no files changed.")
        return 0

    if (
        os.name == "nt"
        and _is_under_program_files(target)
        and not args.elevated_child
        and not _is_windows_admin()
    ):
        return _run_elevated(raw_arguments)

    backup = install_package(source, target, app_source_root)
    print(f"Installed {source} to {target}")
    if backup is not None:
        print(f"Previous production package preserved at {backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"Production update failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
