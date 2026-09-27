#!/usr/bin/env python3
"""
hierarchical_flood_zoom.py -- Urban -> Zone/Node -> Point flood reasoning.

STATUS: PROPOSAL / NOT A TOLEDO THEOREM.

Purpose
-------
Keep Toledo PROP-FLOOD-03 as the canonical finite water-balance ledger, while allowing
coarser urban screening to remain computable when local inputs are incomplete.

Three layers:

1) URBAN SCREENING (equivalent-depth debt, NOT Toledo)
   D[t+1] = max(0, D[t] + P[t] - C[t])

   P and C may be ranges. This layer answers only whether the urban drainage envelope
   is under pressure; it does NOT predict a street/house depth.

2) ZONE/NODE ZOOM (Toledo-compatible interval projection)
   ΔS = P*A*c + Qin*tau - Qout*tau

   Instead of inventing missing point values, callers may pass finite physical bounds.
   If finite bounds are unavailable, this layer REFUSES while the urban layer still
   remains usable. The exact Toledo ledger in water_balance.py remains unchanged.

3) POINT ZOOM
   depth(point) = max(0, H_water - z_ground)

   This requires a measured/modelled water-surface interval H and ground-elevation
   interval z using a compatible datum. Without those, point depth is REFUSED.

This module deliberately separates:
- city-scale screening,
- finite water-balance bounds,
- point-level inundation depth.

No risk probability is invented and no arbitrary weighted score is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Optional, Union

Numeric = Union[int, str, Fraction]


def _q(x: Numeric) -> Fraction:
    if isinstance(x, Fraction):
        return x
    return Fraction(x)


@dataclass(frozen=True)
class QInterval:
    """Closed rational interval [low, high]."""
    low: Fraction
    high: Fraction

    def __post_init__(self):
        if self.high < self.low:
            raise ValueError("interval high must be >= low")

    @classmethod
    def of(cls, low: Numeric, high: Numeric | None = None) -> "QInterval":
        lo = _q(low)
        hi = lo if high is None else _q(high)
        return cls(lo, hi)

    def as_dict(self):
        return {"low": str(self.low), "high": str(self.high)}


@dataclass(frozen=True)
class Refusal:
    reason: str

    def as_dict(self):
        return {"status": "REFUSED", "reason": self.reason}


def _mul_nonnegative(*xs: QInterval) -> QInterval:
    """Interval product for quantities declared non-negative."""
    lo = Fraction(1)
    hi = Fraction(1)
    for x in xs:
        if x.low < 0:
            raise ValueError("non-negative interval required")
        lo *= x.low
        hi *= x.high
    return QInterval(lo, hi)


def urban_debt_step(
    debt_mm: QInterval,
    rain_mm: QInterval,
    capacity_mm: QInterval,
) -> QInterval:
    """One coarse urban screening step.

    This is NOT Toledo. It is an equivalent-depth envelope comparison that remains
    computable from rainfall and drainage-envelope ranges.

    Because max(0, D + P - C) is monotone increasing in D/P and decreasing in C:
      low  = max(0, D_low  + P_low  - C_high)
      high = max(0, D_high + P_high - C_low)
    """
    if min(debt_mm.low, rain_mm.low, capacity_mm.low) < 0:
        raise ValueError("urban debt/rain/capacity must be non-negative")

    low = max(Fraction(0), debt_mm.low + rain_mm.low - capacity_mm.high)
    high = max(Fraction(0), debt_mm.high + rain_mm.high - capacity_mm.low)
    return QInterval(low, high)


def urban_debt_path(
    rain_by_step_mm: Iterable[QInterval],
    capacity_by_step_mm: Iterable[QInterval],
    opening_debt_mm: QInterval = QInterval(Fraction(0), Fraction(0)),
) -> list[dict]:
    rains = list(rain_by_step_mm)
    caps = list(capacity_by_step_mm)
    if len(rains) != len(caps):
        raise ValueError("rain and capacity series must have equal length")

    debt = opening_debt_mm
    out = []
    for i, (rain, cap) in enumerate(zip(rains, caps)):
        debt = urban_debt_step(debt, rain, cap)
        if debt.low > 0:
            state = "ROBUST_DEFICIT"
        elif debt.high > 0:
            state = "POSSIBLE_DEFICIT"
        else:
            state = "NO_DEFICIT_SIGNAL"
        out.append({
            "step": i,
            "rain_mm": rain.as_dict(),
            "capacity_mm": cap.as_dict(),
            "closing_debt_mm": debt.as_dict(),
            "state": state,
        })
    return out


def toledo_increment_bounds(
    *,
    P_m: QInterval,
    A_m2: QInterval,
    c: QInterval,
    Qin_m3s: QInterval,
    tau_s: QInterval,
    Qout_m3s: QInterval,
) -> QInterval | Refusal:
    """Finite interval projection of the Toledo increment.

    Canonical exact ledger remains in water_balance.py:
        ΔS = P*A*c + Qin*tau - Qout*tau

    This helper computes only a CLOSED finite bound:
        ΔS_low  = min(rain term) + min(inflow term) - max(outflow term)
        ΔS_high = max(rain term) + max(inflow term) - min(outflow term)

    If the caller cannot provide finite bounds, it should not call this function and
    should return a Refusal upstream instead of inventing them.
    """
    try:
        rain = _mul_nonnegative(P_m, A_m2, c)
        inflow = _mul_nonnegative(Qin_m3s, tau_s)
        outflow = _mul_nonnegative(Qout_m3s, tau_s)
    except ValueError as exc:
        return Refusal(str(exc))

    low = rain.low + inflow.low - outflow.high
    high = rain.high + inflow.high - outflow.low
    return QInterval(low, high)


def classify_storage_increment(delta_s: QInterval | Refusal) -> dict:
    if isinstance(delta_s, Refusal):
        return delta_s.as_dict()
    if delta_s.low > 0:
        state = "GUARANTEED_ACCUMULATION_WITHIN_DECLARED_BOUNDS"
    elif delta_s.high < 0:
        state = "GUARANTEED_DRAINAGE_WITHIN_DECLARED_BOUNDS"
    elif delta_s.low == 0 and delta_s.high == 0:
        state = "FLAT"
    else:
        state = "UNCERTAIN_SIGN"
    return {
        "status": "OK",
        "delta_storage_m3": delta_s.as_dict(),
        "state": state,
    }


def point_depth_bounds(
    water_surface_m_datum: QInterval | None,
    ground_elevation_m_datum: QInterval | None,
) -> QInterval | Refusal:
    """Point-level inundation depth interval.

    depth = max(0, H_water - z_ground)

    Both intervals MUST use a compatible vertical datum. If either is missing, refuse.
    """
    if water_surface_m_datum is None or ground_elevation_m_datum is None:
        return Refusal("MISSING_WATER_SURFACE_OR_GROUND_ELEVATION")

    low = max(
        Fraction(0),
        water_surface_m_datum.low - ground_elevation_m_datum.high,
    )
    high = max(
        Fraction(0),
        water_surface_m_datum.high - ground_elevation_m_datum.low,
    )
    return QInterval(low, high)


def hierarchical_readout(
    *,
    urban_debt_mm: QInterval,
    urban_rain_mm: QInterval,
    urban_capacity_mm: QInterval,
    node_delta_s: QInterval | Refusal | None = None,
    point_depth: QInterval | Refusal | None = None,
) -> dict:
    """Compose coarse-to-fine results without laundering one scale into another."""
    next_debt = urban_debt_step(urban_debt_mm, urban_rain_mm, urban_capacity_mm)
    urban_state = (
        "ROBUST_DEFICIT" if next_debt.low > 0
        else "POSSIBLE_DEFICIT" if next_debt.high > 0
        else "NO_DEFICIT_SIGNAL"
    )

    out = {
        "urban": {
            "status": "OK",
            "closing_debt_mm": next_debt.as_dict(),
            "state": urban_state,
            "claim_boundary": "urban screening only; not a point flood-depth prediction",
        },
        "node": {
            "status": "NOT_ZOOMED",
            "claim_boundary": "requires finite local Toledo bounds",
        },
        "point": {
            "status": "NOT_ZOOMED",
            "claim_boundary": "requires compatible water-surface and ground-elevation data",
        },
    }

    if node_delta_s is not None:
        out["node"] = classify_storage_increment(node_delta_s)

    if point_depth is not None:
        if isinstance(point_depth, Refusal):
            out["point"] = point_depth.as_dict()
        else:
            out["point"] = {
                "status": "OK",
                "depth_m": point_depth.as_dict(),
                "state": (
                    "INUNDATED_WITHIN_ALL_DECLARED_BOUNDS"
                    if point_depth.low > 0
                    else "POSSIBLY_INUNDATED"
                    if point_depth.high > 0
                    else "NO_INUNDATION_IN_DECLARED_BOUNDS"
                ),
            }
    return out
