import importlib

import pytest

from App_FreeCAD.algorithm_factory import (
    create_algorithm,
    known_algorithms,
    normalize_algorithm_name,
)
from App_FreeCAD.geometry_cache import clear_registry, get_or_create
from App_FreeCAD.settings import get_algorithm, set_algorithm
from MateCore.dummy_algorithm import DummyMateAlgorithm
from MateCore.MateAlgo_Heuristic.algorithm_heuristic import MateAlgorithm_Heuristic
from MateCore.MateGraph.debug_mate_graph_algorithm import MateAlgorithm_DebugMateGraph
from MateCore.rendering_demo_algorithm import DummyRenderingDemoAlgorithm


def test_known_algorithms():
    assert known_algorithms() == (
        "heuristic",
        "debug_mate_graph",
        "dummy",
        "rendering_demo",
    )


def test_normalize_aliases():
    assert normalize_algorithm_name("render") == "rendering_demo"
    assert normalize_algorithm_name("RENDERING") == "rendering_demo"
    assert normalize_algorithm_name("heuristic") == "heuristic"


def test_create_algorithm_by_id():
    clear_registry()
    cache = get_or_create("TestDoc")
    assert isinstance(
        create_algorithm("heuristic", geometry_cache=cache), MateAlgorithm_Heuristic
    )
    assert isinstance(
        create_algorithm("debug_mate_graph", geometry_cache=cache),
        MateAlgorithm_DebugMateGraph,
    )
    assert isinstance(create_algorithm("rendering_demo"), DummyRenderingDemoAlgorithm)
    assert isinstance(create_algorithm("render"), DummyRenderingDemoAlgorithm)
    assert isinstance(create_algorithm("dummy"), DummyMateAlgorithm)


def test_create_algorithm_unknown():
    with pytest.raises(KeyError):
        create_algorithm("nope")


def test_create_heuristic_requires_geometry_cache():
    with pytest.raises(ValueError, match="geometry_cache"):
        create_algorithm("heuristic")


def test_settings_set_and_get_algorithm():
    settings = importlib.import_module("App_FreeCAD.settings")
    previous = get_algorithm()
    try:
        set_algorithm("dummy")
        assert get_algorithm() == "dummy"
        settings.algorithm = "rendering_demo"
        assert get_algorithm() == "rendering_demo"
        assert settings.algorithm == "rendering_demo"
    finally:
        set_algorithm(previous)


def test_settings_rejects_unknown_algorithm():
    previous = get_algorithm()
    try:
        with pytest.raises(ValueError, match="Unknown algorithm"):
            set_algorithm("not-real")
        assert get_algorithm() == previous
    finally:
        set_algorithm(previous)
