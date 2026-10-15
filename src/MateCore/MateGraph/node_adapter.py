"""Convert graph nodes to FaceDescriptor for pose and fit evaluation."""

from __future__ import annotations

from MateCore.MateFit.descriptors import CONE, CYLINDER, PLANE, FaceDescriptor

from .model import AAGNode, FREEFORM, OTHER


def node_to_face_descriptor(node: AAGNode) -> FaceDescriptor | None:
    if node.surface_kind == "plane":
        kind = PLANE
    elif node.surface_kind == "cylinder":
        kind = CYLINDER
    elif node.surface_kind == "cone":
        kind = CONE
    elif node.surface_kind in (FREEFORM, OTHER):
        if node.normal_samples:
            n = node.normal_samples[0].normal
            return FaceDescriptor(
                id=node.node_id,
                part_id=node.part_id,
                kind=PLANE,
                origin=node.normal_samples[0].point,
                axis=n,
                area=node.area,
                ref=node.ref,
            )
        return FaceDescriptor(
            id=node.node_id,
            part_id=node.part_id,
            kind=PLANE,
            origin=node.origin,
            axis=node.axis if float(node.axis @ node.axis) > 0 else (0, 0, 1),
            area=node.area,
            ref=node.ref,
        )
    else:
        return None
    if kind == CONE and node.semi_angle <= 0.0:
        return None
    return FaceDescriptor(
        id=node.node_id,
        part_id=node.part_id,
        kind=kind,
        origin=node.origin,
        axis=node.axis,
        radius=node.radius,
        semi_angle=node.semi_angle,
        convex=node.convex,
        area=node.area,
        ref=node.ref,
    )
