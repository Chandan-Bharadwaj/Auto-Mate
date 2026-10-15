"""Extensible fit / tolerance resolution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from MateCore.MateFit.descriptors import CONE, CYLINDER, PLANE, FaceDescriptor


@dataclass(frozen=True, slots=True)
class Tolerance:
    abs_len: float = 1e-3
    rel_len: float = 0.0
    abs_angle: float = 1e-3  # radians

    def length(self, nominal: float = 0.0) -> float:
        return self.abs_len + self.rel_len * abs(nominal)


@dataclass(frozen=True, slots=True)
class Measurement:
    """Residuals of one selected/candidate pair under a concrete pose."""

    gap: float  # signed; > 0 clearance (air), < 0 interference
    lateral: float = 0.0  # axis-to-axis offset (cylinders)
    angle: float = 0.0  # radians off perfect alignment


@dataclass(frozen=True, slots=True)
class FitResult:
    ok: bool
    fit_class: str  # "exact" | "clearance" | "interference" | "rejected"
    gap: float
    residual: float


class FitType(ABC):
    name: str = "fit"

    def __init__(self, tolerance: Tolerance | None = None) -> None:
        self.tolerance = tolerance or Tolerance()

    @abstractmethod
    def gap_band(self) -> tuple[float, float]:
        """Allowed (min, max) signed gap, before tolerance."""

    def target_gap(self, sel: FaceDescriptor, cand: FaceDescriptor) -> float:
        lo, hi = self.gap_band()
        return 0.5 * (lo + hi)

    def size_band(self, sel: FaceDescriptor) -> tuple[float, float] | None:
        if sel.kind not in (CYLINDER, CONE):
            return None
        lo, hi = self.gap_band()
        tol = self.tolerance.length(sel.radius)
        if sel.convex:
            return sel.radius + lo - tol, sel.radius + hi + tol
        return sel.radius - hi - tol, sel.radius - lo + tol

    def evaluate(
        self, sel: FaceDescriptor, cand: FaceDescriptor, m: Measurement
    ) -> FitResult:
        tol = self.tolerance
        nominal = sel.radius if sel.kind in (CYLINDER, CONE) else 0.0
        len_tol = tol.length(nominal)
        lo, hi = self.gap_band()
        taper_residual = (
            abs(sel.semi_angle - cand.semi_angle)
            if sel.kind == CONE
            else 0.0
        )
        residual = max(m.lateral, abs(m.angle), taper_residual)
        ok = (
            m.angle <= tol.abs_angle
            and m.lateral <= len_tol
            and lo - len_tol <= m.gap <= hi + len_tol
            and sel.kind == cand.kind
            and taper_residual <= tol.abs_angle
        )
        if sel.kind == CYLINDER and sel.convex == cand.convex:
            ok = False
        if sel.kind == CONE and sel.convex == cand.convex:
            ok = False
        if not ok:
            return FitResult(False, "rejected", m.gap, residual)
        target = self.target_gap(sel, cand)
        if lo == hi:
            delta_gap = m.gap - target
            if abs(delta_gap) <= len_tol:
                fit_class = "exact"
            elif delta_gap > len_tol:
                fit_class = "clearance"
            else:
                fit_class = "interference"
            spread = abs(delta_gap)
        else:
            if abs(m.gap) <= len_tol:
                fit_class = "exact"
            else:
                fit_class = "clearance" if m.gap > 0 else "interference"
            spread = abs(m.gap - target)
        return FitResult(True, fit_class, m.gap, max(residual, spread))


class BandFit(FitType):
    def __init__(
        self, name: str, lo: float, hi: float, tolerance: Tolerance | None = None
    ) -> None:
        super().__init__(tolerance)
        if lo > hi:
            raise ValueError("gap band lower bound exceeds upper bound")
        self.name = name
        self._band = (lo, hi)

    def gap_band(self) -> tuple[float, float]:
        return self._band


def exact_fit(tolerance: Tolerance | None = None) -> FitType:
    return BandFit("exact", 0.0, 0.0, tolerance)


def clearance_fit(
    min_gap: float = 0.0, max_gap: float = 0.1, tolerance: Tolerance | None = None
) -> FitType:
    return BandFit("clearance", min_gap, max_gap, tolerance)


def interference_fit(max_overlap: float = 0.05, tolerance: Tolerance | None = None) -> FitType:
    return BandFit("interference", -max_overlap, 0.0, tolerance)


def transition_fit(
    max_interference: float = 0.02,
    max_clearance: float = 0.02,
    tolerance: Tolerance | None = None,
) -> FitType:
    return BandFit("transition", -max_interference, max_clearance, tolerance)


class FitRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Callable[..., FitType]] = {}

    def register(self, name: str, factory: Callable[..., FitType]) -> None:
        if name in self._factories:
            raise ValueError(f"Fit '{name}' is already registered")
        self._factories[name] = factory

    def create(self, name: str, **params) -> FitType:
        try:
            factory = self._factories[name]
        except KeyError:
            raise KeyError(f"Unknown fit '{name}'") from None
        return factory(**params)

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


def default_registry() -> FitRegistry:
    reg = FitRegistry()
    reg.register("exact", exact_fit)
    reg.register("clearance", clearance_fit)
    reg.register("interference", interference_fit)
    reg.register("transition", transition_fit)
    return reg


@dataclass(frozen=True, slots=True)
class FitPolicy:
    default: FitType
    overrides: tuple[tuple[tuple[str, str], FitType], ...] = ()

    @staticmethod
    def of(
        default: FitType, overrides: dict[tuple[str, str], FitType] | None = None
    ) -> FitPolicy:
        return FitPolicy(default, tuple((overrides or {}).items()))

    def fit_for(self, sel_kind: str, cand_kind: str) -> FitType:
        for key, fit in self.overrides:
            if key == (sel_kind, cand_kind):
                return fit
        return self.default


class FitResolver:
    def __init__(self, policy: FitPolicy | None = None) -> None:
        self.policy = policy or FitPolicy(exact_fit())

    @property
    def angle_tolerance(self) -> float:
        tols = [self.policy.default.tolerance.abs_angle]
        tols += [f.tolerance.abs_angle for _, f in self.policy.overrides]
        return max(tols)

    def kinds_compatible(self, sel: FaceDescriptor, cand: FaceDescriptor) -> bool:
        if sel.kind != cand.kind or sel.kind not in (PLANE, CYLINDER, CONE):
            return False
        tol = self.policy.default.tolerance
        if sel.kind == CONE:
            if sel.convex == cand.convex:
                return False
            if abs(sel.semi_angle - cand.semi_angle) > tol.abs_angle:
                return False
            band = self.policy.fit_for(sel.kind, cand.kind).size_band(sel)
            if band is not None and not band[0] <= cand.radius <= band[1]:
                return False
            return True
        if sel.kind == CYLINDER:
            if sel.convex == cand.convex:
                return False
            band = self.policy.fit_for(sel.kind, cand.kind).size_band(sel)
            if band is not None and not band[0] <= cand.radius <= band[1]:
                return False
        return True

    def target_gap(self, sel: FaceDescriptor, cand: FaceDescriptor) -> float:
        return self.policy.fit_for(sel.kind, cand.kind).target_gap(sel, cand)

    def evaluate(
        self, sel: FaceDescriptor, cand: FaceDescriptor, m: Measurement
    ) -> FitResult:
        return self.policy.fit_for(sel.kind, cand.kind).evaluate(sel, cand, m)
