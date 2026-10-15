import pytest

from App_FreeCAD.algorithm_factory import create_algorithm
from App_FreeCAD.geometry_cache import clear_registry, get_or_create
from App_FreeCAD.settings import (
    get_heuristic_nominal_fit_gap_mm,
    get_heuristic_fit_validation,
    get_heuristic_mate_config,
    get_heuristic_pose_validation,
    set_heuristic_nominal_fit_gap_mm,
    set_heuristic_fit_validation,
    set_heuristic_pose_validation,
    set_heuristic_skip_pose_fit,
)


@pytest.fixture(autouse=True)
def _reset_heuristic_validation():
    set_heuristic_skip_pose_fit(False)
    yield
    set_heuristic_skip_pose_fit(False)


def test_validation_setters():
    set_heuristic_pose_validation("warn")
    set_heuristic_fit_validation("skip")
    assert get_heuristic_pose_validation() == "warn"
    assert get_heuristic_fit_validation() == "skip"
    cfg = get_heuristic_mate_config()
    assert cfg.pose_validation == "warn"
    assert cfg.fit_validation == "skip"


def test_skip_pose_fit_toggle():
    set_heuristic_skip_pose_fit(True)
    assert get_heuristic_pose_validation() == "skip"
    assert get_heuristic_fit_validation() == "skip"
    set_heuristic_skip_pose_fit(False)
    assert get_heuristic_pose_validation() == "strict"


def test_factory_uses_session_heuristic_config():
    set_heuristic_skip_pose_fit(True)
    clear_registry()
    algo = create_algorithm("heuristic", geometry_cache=get_or_create("CfgDoc"))
    assert algo._mate_config.pose_validation == "skip"
    assert algo._mate_config.fit_validation == "skip"


def test_nominal_fit_gap_setting():
    set_heuristic_nominal_fit_gap_mm(0.05)
    assert get_heuristic_nominal_fit_gap_mm() == 0.05
    assert get_heuristic_mate_config().nominal_fit_gap_mm == 0.05
    set_heuristic_nominal_fit_gap_mm(None)
    assert get_heuristic_nominal_fit_gap_mm() is None


def test_invalid_validation_mode():
    with pytest.raises(ValueError, match="Unknown validation"):
        set_heuristic_pose_validation("nope")
