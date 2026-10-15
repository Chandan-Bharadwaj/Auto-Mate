from dataclasses import replace

import numpy as np
import pytest

from MateCore.algorithm import AlgorithmConfig
from MateCore.MateFit.descriptors import CONE, CYLINDER, PLANE, FaceDescriptor
from MateCore.MateGraph.model import PartAAG
from MateCore.MateAlgo_Heuristic.config import HeuristicMateConfig
from MateCore.MateAlgo_Heuristic.algorithm_heuristic import (
    HeuristicMatch,
    MateAlgorithm_Heuristic,
)
from MateCore.MateFit import FitPolicy, FitResolver, clearance_fit
from MateCore.MateFit.configuration import MateConfigurationKind, classify_configuration
from MateCore.context import (
    DocumentContext,
    DocumentObjectContext,
    PartContext,
    RecognitionRequest,
    SurfaceRef,
)
from test_aag_world import part_aag_from_descriptors


class World:
    def __init__(self):
        self.parts = {}
        self.descs = {}

    def add(self, part_id, specs):
        refs, descs = [], []
        for i, spec in enumerate(specs, start=1):
            ref = SurfaceRef(part_id, part_id, f"Face{i}", None, None, part_id=part_id)
            refs.append(ref)
            descs.append(
                FaceDescriptor(
                    id=f"{part_id}:Face{i}",
                    part_id=part_id,
                    ref=ref,
                    area=spec.pop("area", 1.0),
                    **spec,
                )
            )
        self.parts[part_id] = PartContext(part_id, part_id, part_id, faces=tuple(refs))
        self.descs[part_id] = descs
        return refs

    def request(self, surfaces):
        ctx = DocumentContext(
            "Doc",
            (DocumentObjectContext("o", "o", "t", "part", (), parts=tuple(self.parts.values())),),
        )
        return RecognitionRequest(ctx, tuple(surfaces))

    def algorithm(self, resolver=None, **kw):
        resolver = resolver or FitResolver()
        tol = resolver.policy.default.tolerance

        def graph_for(part: PartContext) -> PartAAG:
            return part_aag_from_descriptors(
                part.part_id,
                list(self.descs[part.part_id]),
                tol_len=tol.abs_len,
                tol_angle=tol.abs_angle,
            )

        mate_config = kw.pop("mate_config", HeuristicMateConfig())
        return MateAlgorithm_Heuristic(
            graph_for,
            metadata_store=None,
            resolver=resolver,
            mate_config=mate_config,
            **kw,
        )


def plane(origin, normal):
    return dict(kind=PLANE, origin=origin, axis=normal)


def uslot_faces(origin=(0, 0, 0), half_width=5.0):
    ox, oy, oz = origin
    hw = half_width
    return [
        plane((ox, oy, oz), (0, 0, 1)),
        plane((ox - hw, oy, oz), (1, 0, 0)),
        plane((ox + hw, oy, oz), (-1, 0, 0)),
    ]


def uslot_faces_mating_partner(origin=(0, 0, 0), half_width=5.0):
    """Normals aligned with complemented search template from ``uslot_faces``."""
    ox, oy, oz = origin
    hw = half_width
    return [
        plane((ox, oy, oz), (0, 0, -1)),
        plane((ox - hw, oy, oz), (-1, 0, 0)),
        plane((ox + hw, oy, oz), (1, 0, 0)),
    ]


def wire_uslot_adjacency(world: World, part_id: str) -> None:
    ids = tuple(f"{part_id}:Face{i}" for i in (1, 2, 3))
    world.descs[part_id] = [
        replace(d, adjacent=ids[1:] if i == 0 else (ids[0],))
        for i, d in enumerate(world.descs[part_id])
    ]


def cyl(origin, axis, r, convex):
    return dict(kind=CYLINDER, origin=origin, axis=axis, radius=r, convex=convex)


def cone(origin, axis, radius, semi_angle, convex):
    return dict(
        kind=CONE,
        origin=origin,
        axis=axis,
        radius=radius,
        semi_angle=semi_angle,
        convex=convex,
    )


def matches(world, refs, resolver=None):
    result = world.algorithm(resolver).run(world.request(refs))
    return result.matches


def test_peg_finds_matching_hole_and_ignores_decoys():
    w = World()
    a = w.add("A", [cyl((0, 0, 0), (0, 0, 1), 5, True)])
    w.add("B", [cyl((10, 0, 0), (0, 0, 1), 5, False), cyl((0, 9, 0), (0, 0, 1), 6, False)])
    found = matches(w, a)
    assert len(found) == 1
    m = found[0]
    assert isinstance(m, HeuristicMatch) and m.part_id == "B"
    assert [f.face_name for f in m.faces] == ["Face1"]
    assert m.dof == 2
    assert m.fits[0].fit_class == "exact"
    assert m.mate_configuration_kind == MateConfigurationKind.EXACT_FIT.value


def test_single_surface_mate_succeeds():
    w = World()
    a = w.add("A", [cyl((0, 0, 0), (0, 0, 1), 5, True)])
    w.add("B", [cyl((10, 0, 0), (0, 0, 1), 5, False)])
    result = w.algorithm().run(w.request(a))
    assert len(result.part_matches) == 1
    assert result.part_matches[0].part_id == "B"
    assert len(result.part_matches[0].matches) >= 1


def test_no_match_returns_empty():
    w = World()
    a = w.add("A", [cyl((0, 0, 0), (0, 0, 1), 5, True)])
    w.add("B", [cyl((0, 0, 0), (0, 0, 1), 7, False), cyl((0, 0, 0), (0, 0, 1), 5, True)])
    assert matches(w, a) == ()


def test_corner_of_two_planes_solves_translation():
    w = World()
    a = w.add("A", [plane((0, 0, 0), (1, 0, 0)), plane((0, 0, 0), (0, 1, 0))])
    w.add("B", [plane((10, 0, 0), (-1, 0, 0)), plane((0, 20, 0), (0, -1, 0))])
    w.add("C", [plane((10, 0, 0), (-1, 0, 0)), plane((0, 20, 0), (-0.7071, -0.7071, 0))])
    found = matches(w, a)
    assert [m.part_id for m in found] == ["B"]
    assert np.allclose(found[0].translation[:2], (10, 20))
    assert found[0].dof == 1


def test_cone_taper_rejects_wrong_semi_angle():
    w = World()
    semi = 0.1
    a_refs = w.add("A", [cone((0, 0, 0), (0, 0, 1), 10.0, semi, True)])
    w.add("B", [cone((20, 0, 0), (0, 0, 1), 10.0, semi, False)])
    w.add("C", [cone((20, 0, 0), (0, 0, 1), 10.0, 0.2, False)])
    # Single-slot pattern uses kind-only on first assign; strict pose/fit drops wrong taper.
    found = w.algorithm().run(w.request(a_refs)).matches
    assert [m.part_id for m in found] == ["B"]


def test_uslot_flank_spacing_rejects_wrong_opening():
    w = World()
    a_refs = w.add("A", uslot_faces((0, 0, 0), 5.0))
    wire_uslot_adjacency(w, "A")
    w.add("B", uslot_faces((10, 0, 0), 5.0))
    wire_uslot_adjacency(w, "B")
    w.add("C", uslot_faces((10, 0, 0), 4.0))
    wire_uslot_adjacency(w, "C")
    cfg = HeuristicMateConfig(pose_validation="skip", fit_validation="skip")
    found = w.algorithm(mate_config=cfg).run(w.request(a_refs)).matches
    assert [m.part_id for m in found] == ["B"]


def test_nominal_fit_gap_allows_clearance_cylinder_mate():
    w = World()
    a = w.add("A", [cyl((0, 0, 0), (0, 0, 1), 5, True)])
    w.add("B", [cyl((10, 0, 0), (0, 0, 1), 5.05, False)])
    cfg = HeuristicMateConfig(nominal_fit_gap_mm=10.0)
    result = w.algorithm(mate_config=cfg).run(w.request(a))
    assert len(result.part_matches) == 1
    m = result.part_matches[0].matches[0]
    assert m.fits[0].fit_class == "clearance"
    assert m.mate_configuration_kind == MateConfigurationKind.CLEARANCE_FIT.value


def test_fit_policy_controls_clearance_matching():
    w = World()
    a_faces = w.add(
        "A",
        [
            cyl((0, 0, 0), (0, 0, 1), 5, True),
            cyl((0, 0, 10), (0, 0, 1), 5, True),
        ],
    )
    w.add(
        "B",
        [
            cyl((0, 0, 0), (0, 0, 1), 5.05, False),
            cyl((0, 0, 10), (0, 0, 1), 5.05, False),
        ],
    )
    assert matches(w, a_faces) == ()
    loose = FitResolver(FitPolicy(clearance_fit(0.0, 0.1)))
    found = matches(w, a_faces, loose)
    assert found and found[0].fits[0].fit_class == "clearance"
    assert found[0].fits[0].gap == pytest.approx(0.05)
    assert found[0].mate_configuration_kind == MateConfigurationKind.CLEARANCE_FIT.value
    assert classify_configuration(found[0].fits) == MateConfigurationKind.CLEARANCE_FIT
