import numpy as np

from MateCore.MateFit.descriptors import CONE, FaceDescriptor, complement
from MateCore.MateGraph.model import AAGNode
from MateCore.MateGraph.node_adapter import node_to_face_descriptor
from MateCore.MateGraph.search.comparators import DefaultNodeComparator
from MateCore.MateGraph.search.pattern import PatternSlot


def test_cone_descriptor_requires_positive_semi_angle():
    FaceDescriptor(
        "c",
        "P",
        CONE,
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=5.0,
        semi_angle=0.1,
    )


def test_cone_complement_flips_convex_only():
    f = FaceDescriptor(
        "c",
        "P",
        CONE,
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=5.0,
        semi_angle=0.1,
        convex=True,
    )
    c = complement(f)
    assert c.convex is False
    assert c.semi_angle == f.semi_angle


def test_node_adapter_invalid_cone_semi_angle_returns_none():
    node = AAGNode(
        "n",
        "P",
        "cone",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=4.0,
        semi_angle=0.0,
        convex=True,
    )
    assert node_to_face_descriptor(node) is None


def test_node_adapter_maps_cone():
    node = AAGNode(
        "n",
        "P",
        "cone",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=4.0,
        semi_angle=0.12,
        convex=True,
    )
    desc = node_to_face_descriptor(node)
    assert desc is not None
    assert desc.kind == CONE
    assert desc.semi_angle == 0.12


def test_comparator_rejects_taper_mismatch():
    cmp = DefaultNodeComparator(angle_tol=0.05, min_similarity=0.3)
    slot = PatternSlot(
        "s",
        "n",
        "cone",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=10.0,
        semi_angle=0.1,
    )
    node = AAGNode(
        "t",
        "Q",
        "cone",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=10.0,
        semi_angle=0.2,
    )
    assert cmp.similarity(slot, node) is None
    assert cmp.explain_node_rejection(slot, node) == "taper_mismatch"


def test_mating_comparator_skips_invalid_cone_target_without_raise():
    from MateCore.MateAlgo_Heuristic.policy import MatingNodeComparator
    from MateCore.MateFit import FitResolver

    cmp = MatingNodeComparator(
        FitResolver(),
        "P",
        DefaultNodeComparator(compare_node_axis=False),
    )
    slot = PatternSlot(
        "s",
        "n",
        "cylinder",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=5.0,
    )
    bad_cone = AAGNode(
        "t",
        "Q",
        "cone",
        np.zeros(3),
        np.array([0.0, 0.0, 1.0]),
        radius=5.0,
        semi_angle=0.0,
    )
    partial = {"other": "T:other"}
    assert cmp.similarity(slot, bad_cone, partial) is None
