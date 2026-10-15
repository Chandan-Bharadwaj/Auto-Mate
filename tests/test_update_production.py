from pathlib import Path

from updateProduction import install_package, validate_deployment, validate_source


def create_package(root: Path, marker: str) -> Path:
    package = root / "FeatureTools"
    package.mkdir(parents=True)
    (package / "Init.py").write_text('"""init"""', encoding="utf-8")
    (package / "InitGui.py").write_text(marker, encoding="utf-8")
    return package


def create_app_src(root: Path, marker: str) -> Path:
    src = root / "src"
    mate_core = src / "MateCore"
    mate_core.mkdir(parents=True)
    (mate_core / "__init__.py").write_text('"""MateCore"""', encoding="utf-8")
    (mate_core / "algorithm.py").write_text(marker, encoding="utf-8")
    (mate_core / "context.py").write_text(marker, encoding="utf-8")
    (mate_core / "dummy_algorithm.py").write_text(marker, encoding="utf-8")
    heuristic = mate_core / "MateAlgo_Heuristic"
    heuristic.mkdir()
    (heuristic / "algorithm_heuristic.py").write_text(marker, encoding="utf-8")
    app_fc = src / "App_FreeCAD"
    app_fc.mkdir()
    (app_fc / "__init__.py").write_text('"""App_FreeCAD"""', encoding="utf-8")
    for module in (
        "command.py",
        "document_context.py",
        "display.py",
        "selection.py",
        "occ_parts.py",
    ):
        (app_fc / module).write_text(marker, encoding="utf-8")
    return src


def test_install_package_replaces_target_and_preserves_backup(tmp_path, monkeypatch):
    source = create_package(tmp_path / "source", "new")
    app_source = create_app_src(tmp_path / "source", "new-app")
    target = create_package(tmp_path / "production", "old")
    backup_root = tmp_path / "local-app-data"
    monkeypatch.setenv("LOCALAPPDATA", str(backup_root))

    backup = install_package(source, target, app_source)

    assert backup is not None
    assert (target / "InitGui.py").read_text(encoding="utf-8") == "new"
    assert (target / "MateCore" / "algorithm.py").read_text(encoding="utf-8") == "new-app"
    assert (target / "App_FreeCAD" / "command.py").read_text(encoding="utf-8") == "new-app"
    assert (backup / "InitGui.py").read_text(encoding="utf-8") == "old"
    assert not list(target.parent.glob(".FeatureTools-staging-*"))


def test_validate_source_rejects_incomplete_package(tmp_path):
    source = tmp_path / "FeatureTools"
    source.mkdir()

    try:
        validate_source(source)
    except FileNotFoundError as error:
        assert "InitGui.py" in str(error)
    else:
        raise AssertionError("incomplete packages must be rejected")


def test_validate_deployment_requires_app_packages(tmp_path):
    source = create_package(tmp_path, "ok")
    app_src = tmp_path / "src"
    app_src.mkdir()
    try:
        validate_deployment(source, app_src)
    except FileNotFoundError as error:
        assert "MateCore" in str(error)
    else:
        raise AssertionError("missing app packages must be rejected")
