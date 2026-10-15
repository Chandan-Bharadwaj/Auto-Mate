"""Rigid-pose solving from complementary face frames, with DOF tracking."""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from MateCore.MateFit.descriptors import CONE, CYLINDER, PLANE, FaceDescriptor
from MateCore.MateFit.fits import FitResolver, Measurement


@dataclass(frozen=True, slots=True, eq=False)
class Pose:
    """Transform applied to the SELECTED part: p' = R p + t."""

    rotation: np.ndarray
    translation: np.ndarray
    dof_rotation: int = 0
    dof_translation: int = 0

    @property
    def dof(self) -> int:
        return self.dof_rotation + self.dof_translation

    def point(self, p: np.ndarray) -> np.ndarray:
        return self.rotation @ p + self.translation

    def direction(self, d: np.ndarray) -> np.ndarray:
        return self.rotation @ d


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def rotation_about(axis: np.ndarray, theta: float) -> np.ndarray:
    k = _unit(axis)
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(theta) * kx + (1 - np.cos(theta)) * (kx @ kx)


def rotation_aligning(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Smallest rotation taking unit u to unit v."""
    c = float(np.dot(u, v))
    if c > 1.0 - 1e-12:
        return np.eye(3)
    if c < -1.0 + 1e-12:
        helper = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
        return rotation_about(np.cross(u, helper), np.pi)
    axis = np.cross(u, v)
    return rotation_about(axis, float(np.arctan2(np.linalg.norm(axis), c)))


def _frame(u1: np.ndarray, u2: np.ndarray) -> np.ndarray:
    e1 = u1
    e2 = _unit(u2 - np.dot(u2, u1) * u1)
    return np.column_stack([e1, e2, np.cross(e1, e2)])


def _direction_options(sel: FaceDescriptor, cand: FaceDescriptor) -> list[np.ndarray]:
    if sel.kind == PLANE:
        return [-cand.axis]
    return [cand.axis, -cand.axis]


def _perpendicular_basis(a: np.ndarray) -> list[np.ndarray]:
    helper = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = _unit(np.cross(a, helper))
    return [e1, np.cross(a, e1)]


def _solve_translation(
    R: np.ndarray, pairs: list[tuple[FaceDescriptor, FaceDescriptor]], resolver: FitResolver
) -> tuple[np.ndarray, int]:
    rows: list[np.ndarray] = []
    rhs: list[float] = []
    for sel, cand in pairs:
        rs = R @ sel.origin
        if sel.kind == PLANE:
            rows.append(cand.axis)
            rhs.append(resolver.target_gap(sel, cand) + float(np.dot(cand.axis, cand.origin - rs)))
        else:
            for e in _perpendicular_basis(cand.axis):
                rows.append(e)
                rhs.append(float(np.dot(e, cand.origin - rs)))
    A = np.array(rows)
    b = np.array(rhs)
    t = np.linalg.lstsq(A, b, rcond=None)[0]
    rank = int(np.linalg.matrix_rank(A, tol=1e-6))
    return t, 3 - rank


def _rotation_candidates(
    pairs: list[tuple[FaceDescriptor, FaceDescriptor]], angle_tol: float
) -> list[tuple[np.ndarray, int]]:
    """Candidate (rotation, free_rotation_dof) from direction correspondences."""
    s0, c0 = pairs[0]
    u1 = s0.axis
    other = None
    best_sin = max(1e-3, 4.0 * angle_tol)
    for sel, cand in pairs[1:]:
        s = float(np.linalg.norm(np.cross(u1, sel.axis)))
        if s > best_sin:
            best_sin, other = s, (sel, cand)

    results: list[tuple[np.ndarray, int]] = []
    if other is not None:
        u2 = other[0].axis
        for v1, v2 in itertools.product(
            _direction_options(s0, c0), _direction_options(*other)
        ):
            if abs(float(np.dot(u1, u2)) - float(np.dot(v1, v2))) > 2.0 * angle_tol:
                continue
            results.append((_frame(v1, v2) @ _frame(u1, u2).T, 0))
        return results

    for v1 in _direction_options(s0, c0):
        R1 = rotation_aligning(u1, v1)
        theta = _in_plane_angle(R1, v1, pairs)
        if theta is None:
            results.append((R1, 1))
        else:
            results.append((rotation_about(v1, theta) @ R1, 0))
    return results


def _in_plane_angle(
    R1: np.ndarray, v: np.ndarray, pairs: list[tuple[FaceDescriptor, FaceDescriptor]]
) -> float | None:
    """Rotation about v fixed by the layout of two non-coaxial cylinder axes."""
    cyl = [(s, c) for s, c in pairs if s.kind == CYLINDER]

    def proj(x: np.ndarray) -> np.ndarray:
        return x - np.dot(x, v) * v

    for (s_i, c_i), (s_j, c_j) in itertools.combinations(cyl, 2):
        ds = proj(R1 @ s_j.origin - R1 @ s_i.origin)
        dc = proj(c_j.origin - c_i.origin)
        if np.linalg.norm(ds) > 1e-6 and np.linalg.norm(dc) > 1e-6:
            return float(np.arctan2(np.dot(v, np.cross(ds, dc)), np.dot(ds, dc)))
    return None


def solve_poses(
    pairs: list[tuple[FaceDescriptor, FaceDescriptor]], resolver: FitResolver
) -> list[Pose]:
    """All candidate poses that map the selected faces onto their candidates."""
    if not pairs:
        return []
    poses = []
    for R, dof_rot in _rotation_candidates(pairs, resolver.angle_tolerance):
        t, dof_t = _solve_translation(R, pairs, resolver)
        poses.append(Pose(R, t, dof_rot, dof_t))
    return poses


def measure(sel: FaceDescriptor, cand: FaceDescriptor, pose: Pose) -> Measurement:
    p = pose.point(sel.origin)
    d = pose.direction(sel.axis)
    if sel.kind == PLANE:
        angle = float(np.arccos(np.clip(-np.dot(d, cand.axis), -1.0, 1.0)))
        gap = float(np.dot(cand.axis, p - cand.origin))
        return Measurement(gap=gap, angle=angle)
    angle = float(np.arccos(np.clip(abs(np.dot(d, cand.axis)), 0.0, 1.0)))
    if sel.kind == CONE:
        axis_angle = angle
        taper = abs(sel.semi_angle - cand.semi_angle)
        angle = max(axis_angle, taper)
    delta = p - cand.origin
    lateral = float(np.linalg.norm(delta - np.dot(delta, cand.axis) * cand.axis))
    gap = cand.radius - sel.radius if sel.convex else sel.radius - cand.radius
    return Measurement(gap=gap, lateral=lateral, angle=angle)
