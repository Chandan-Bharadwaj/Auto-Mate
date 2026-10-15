import numpy as np
import pytest

from MateCore.MateAlgo_Heuristic.axis_alignment import AxisAlignmentMeasure
from MateCore.MateAlgo_Heuristic.config import HeuristicMateConfig
from MateCore.MateAlgo_Heuristic.fit_policy import (
    build_heuristic_fit_resolver,
    effective_nominal_gap_mm,
)
from MateCore.MateFit.descriptors import CYLINDER, PLANE, FaceDescriptor
from MateCore.MateFit.fits import Measurement, Tolerance, clearance_fit
from MateCore.MateGraph.search.pattern import GraphPattern, PatternSlot


def _pattern_with_cylinder() -> GraphPattern:
    slot = PatternSlot(
        slot_id="p0",
        source_node_id="A:F1",
        surface_kind="cylinder",
        origin=np.zeros(3),
        axis=np.array([0.0, 0.0, 1.0]),
        radius=5.0,
    )
    return GraphPattern(
        part_id="A",
        slots=(slot,),
        edges=(),
        anchor_slots=frozenset(),
        _adjacency={"p0": frozenset()},
        _by_slot={"p0": slot},
    )


def test_build_resolver_uses_clearance_band_when_axis_aligned():
    cfg = HeuristicMateConfig(nominal_fit_gap_mm=0.05)
    align = AxisAlignmentMeasure(True, np.array([0.0, 0.0, 1.0]), 0.0)
    from MateCore.MateFit.fits import FitResolver

    resolver = build_heuristic_fit_resolver(cfg, align, FitResolver())
    fit = resolver.policy.default
    assert fit.gap_band() == (0.0, 0.05)
    sel = FaceDescriptor("s", "P", PLANE, np.zeros(3), np.array([0.0, 0.0, 1.0]))
    cand = FaceDescriptor("c", "Q", PLANE, np.zeros(3), np.array([0.0, 0.0, -1.0]))
    assert resolver.target_gap(sel, cand) == pytest.approx(0.025)


def test_build_resolver_exact_when_oblique_planes_only():
    cfg = HeuristicMateConfig(nominal_fit_gap_mm=0.05)
    align = AxisAlignmentMeasure(False, None, 1.0, reason="axes_not_parallel")
    from MateCore.MateFit.fits import FitResolver

    resolver = build_heuristic_fit_resolver(cfg, align, FitResolver(), pattern=None)
    sel = FaceDescriptor("s", "P", PLANE, np.zeros(3), np.array([0.0, 0.0, 1.0]))
    cand = FaceDescriptor("c", "Q", PLANE, np.zeros(3), np.array([0.0, 0.0, -1.0]))
    assert resolver.target_gap(sel, cand) == 0.0


def test_build_resolver_clearance_when_oblique_but_pattern_has_cylinder():
    cfg = HeuristicMateConfig(nominal_fit_gap_mm=10.0)
    align = AxisAlignmentMeasure(False, None, 1.0, reason="axes_not_parallel")
    from MateCore.MateFit.fits import FitResolver

    pattern = _pattern_with_cylinder()
    resolver = build_heuristic_fit_resolver(cfg, align, FitResolver(), pattern)
    assert resolver.policy.default.gap_band() == (0.0, 10.0)


def test_effective_nominal_gap_none_when_oblique_planes_only():
    cfg = HeuristicMateConfig(nominal_fit_gap_mm=0.05)
    align = AxisAlignmentMeasure(False, None, 0.5)
    assert effective_nominal_gap_mm(cfg, align, None) is None


def test_effective_nominal_gap_when_oblique_with_cylinder_pattern():
    cfg = HeuristicMateConfig(nominal_fit_gap_mm=0.05)
    align = AxisAlignmentMeasure(False, None, 0.5)
    assert effective_nominal_gap_mm(cfg, align, _pattern_with_cylinder()) == 0.05


def test_evaluate_clearance_within_max_gap():
    fit = clearance_fit(0.0, 10.0, Tolerance(abs_len=0.001))
    sel = FaceDescriptor(
        "s",
        "P",
        CYLINDER,
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=5.0,
        convex=True,
    )
    cand = FaceDescriptor(
        "c",
        "Q",
        CYLINDER,
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=5.05,
        convex=False,
    )
    result = fit.evaluate(sel, cand, Measurement(gap=0.05, lateral=0.0, angle=0.0))
    assert result.ok and result.fit_class == "clearance"
