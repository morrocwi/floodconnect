#!/usr/bin/env python3
"""Fail-closed evaluator for TDLC Lifeline Convergence Feasibility.

This module operationalises the canonical FloodConnect question:

    Can at least one declared provider move a required essential function
    through a verified/fresh interface and support path, with enough supply
    and path capacity, before the recipient's function fails?

It is a feasibility predicate, not a weighted risk/resilience score.
UNKNOWN is preserved whenever evidence required for a hard constraint is
missing or unverified.
"""

from dataclasses import dataclass, asdict
from math import isfinite
from typing import Any, Iterable, Optional

FEASIBLE = "FEASIBLE"
INFEASIBLE = "INFEASIBLE"
NOT_REQUIRED = "NOT_REQUIRED"
UNKNOWN = "UNKNOWN"

REASON_NO_GAP = "NO_DECLARED_LIFELINE_GAP"
REASON_DEMAND_UNKNOWN = "DEMAND_UNKNOWN"
REASON_LOCAL_STOCK_UNKNOWN = "LOCAL_STOCK_UNKNOWN"
REASON_INTERFACE_UNKNOWN = "INTERFACE_UNKNOWN"
REASON_NO_INTERFACE = "NO_REACHABLE_INTERFACE"
REASON_INTERFACE_UNVERIFIED = "INTERFACE_UNVERIFIED"
REASON_INTERFACE_STALE = "INTERFACE_STALE"
REASON_PATH_UNKNOWN = "PATH_UNKNOWN"
REASON_PATH_UNVERIFIED = "PATH_UNVERIFIED"
REASON_PATH_STALE = "PATH_STALE"
REASON_PATH_INFEASIBLE = "PATH_INFEASIBLE"
REASON_PROVIDER_SUPPLY_UNKNOWN = "PROVIDER_SUPPLY_UNKNOWN"
REASON_PATH_CAPACITY_UNKNOWN = "PATH_CAPACITY_UNKNOWN"
REASON_PROVIDER_SUPPLY_INSUFFICIENT = "PROVIDER_SUPPLY_INSUFFICIENT"
REASON_PATH_CAPACITY_INSUFFICIENT = "PATH_CAPACITY_INSUFFICIENT"
REASON_FAILURE_TIME_UNKNOWN = "FAILURE_TIME_UNKNOWN"
REASON_ARRIVAL_TIME_UNKNOWN = "ARRIVAL_TIME_UNKNOWN"
REASON_ARRIVAL_TOO_LATE = "ARRIVAL_TOO_LATE"


@dataclass(frozen=True)
class ConvergenceResult:
    state: str
    reason_codes: tuple[str, ...] = ()
    provider_id: Optional[str] = None
    interface_node: Optional[str] = None
    resource: Optional[str] = None
    need_gap: Optional[float] = None
    deliverable_quantity: Optional[float] = None
    arrival_slack_h: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite_nonnegative(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(out) or out < 0:
        return None
    return out


def evaluate_candidate(
    *,
    provider_id: str,
    resource: str,
    demand: Any,
    local_stock: Any,
    provider_supply: Any,
    path_capacity: Any,
    interface_node: Optional[str],
    interface_exists: Optional[bool],
    interface_verified: Optional[bool],
    interface_fresh: Optional[bool],
    path_exists: Optional[bool],
    path_verified: Optional[bool],
    path_fresh: Optional[bool],
    path_feasible: Optional[bool],
    failure_time_h: Any,
    arrival_time_h: Any,
) -> ConvergenceResult:
    """Evaluate one provider/interface/path candidate.

    Canonical quantity terms:
        gap = max(0, D - X)
        deliverable = min(S, B)

    A positive gap is FEASIBLE only when every hard connectivity/evidence
    constraint is verified and fresh, deliverable >= gap, and
    arrival_time_h < failure_time_h.

    Explicitly absent/blocked constraints return INFEASIBLE.
    Missing/unverified/stale evidence returns UNKNOWN.
    """

    d = _finite_nonnegative(demand)
    if d is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_DEMAND_UNKNOWN,), provider_id=provider_id, resource=resource
        )

    x = _finite_nonnegative(local_stock)
    if x is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_LOCAL_STOCK_UNKNOWN,), provider_id=provider_id, resource=resource
        )

    gap = max(0.0, d - x)
    if gap == 0:
        return ConvergenceResult(
            NOT_REQUIRED,
            (REASON_NO_GAP,),
            provider_id=provider_id,
            interface_node=interface_node,
            resource=resource,
            need_gap=0.0,
            deliverable_quantity=0.0,
        )

    if interface_exists is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_INTERFACE_UNKNOWN,), provider_id, interface_node, resource, gap
        )
    if interface_exists is False:
        return ConvergenceResult(
            INFEASIBLE, (REASON_NO_INTERFACE,), provider_id, interface_node, resource, gap
        )
    if interface_verified is not True:
        return ConvergenceResult(
            UNKNOWN, (REASON_INTERFACE_UNVERIFIED,), provider_id, interface_node, resource, gap
        )
    if interface_fresh is not True:
        return ConvergenceResult(
            UNKNOWN, (REASON_INTERFACE_STALE,), provider_id, interface_node, resource, gap
        )

    if path_exists is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_PATH_UNKNOWN,), provider_id, interface_node, resource, gap
        )
    if path_exists is False:
        return ConvergenceResult(
            INFEASIBLE, (REASON_PATH_INFEASIBLE,), provider_id, interface_node, resource, gap
        )
    if path_verified is not True:
        return ConvergenceResult(
            UNKNOWN, (REASON_PATH_UNVERIFIED,), provider_id, interface_node, resource, gap
        )
    if path_fresh is not True:
        return ConvergenceResult(
            UNKNOWN, (REASON_PATH_STALE,), provider_id, interface_node, resource, gap
        )
    if path_feasible is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_PATH_UNKNOWN,), provider_id, interface_node, resource, gap
        )
    if path_feasible is False:
        return ConvergenceResult(
            INFEASIBLE, (REASON_PATH_INFEASIBLE,), provider_id, interface_node, resource, gap
        )

    s = _finite_nonnegative(provider_supply)
    if s is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_PROVIDER_SUPPLY_UNKNOWN,), provider_id, interface_node, resource, gap
        )
    b = _finite_nonnegative(path_capacity)
    if b is None:
        return ConvergenceResult(
            UNKNOWN, (REASON_PATH_CAPACITY_UNKNOWN,), provider_id, interface_node, resource, gap
        )

    deliverable = min(s, b)
    if s < gap:
        return ConvergenceResult(
            INFEASIBLE,
            (REASON_PROVIDER_SUPPLY_INSUFFICIENT,),
            provider_id,
            interface_node,
            resource,
            gap,
            deliverable,
        )
    if b < gap:
        return ConvergenceResult(
            INFEASIBLE,
            (REASON_PATH_CAPACITY_INSUFFICIENT,),
            provider_id,
            interface_node,
            resource,
            gap,
            deliverable,
        )

    tfail = _finite_nonnegative(failure_time_h)
    if tfail is None:
        return ConvergenceResult(
            UNKNOWN,
            (REASON_FAILURE_TIME_UNKNOWN,),
            provider_id,
            interface_node,
            resource,
            gap,
            deliverable,
        )
    tarrive = _finite_nonnegative(arrival_time_h)
    if tarrive is None:
        return ConvergenceResult(
            UNKNOWN,
            (REASON_ARRIVAL_TIME_UNKNOWN,),
            provider_id,
            interface_node,
            resource,
            gap,
            deliverable,
        )

    slack = tfail - tarrive
    if slack <= 0:
        return ConvergenceResult(
            INFEASIBLE,
            (REASON_ARRIVAL_TOO_LATE,),
            provider_id,
            interface_node,
            resource,
            gap,
            deliverable,
            slack,
        )

    return ConvergenceResult(
        FEASIBLE,
        (),
        provider_id,
        interface_node,
        resource,
        gap,
        deliverable,
        slack,
    )


def evaluate_candidates(candidates: Iterable[dict[str, Any]]) -> ConvergenceResult:
    """Evaluate alternative provider/path candidates under existential semantics.

    - any FEASIBLE candidate -> FEASIBLE
    - otherwise any UNKNOWN candidate -> UNKNOWN
    - otherwise all NOT_REQUIRED -> NOT_REQUIRED
    - otherwise -> INFEASIBLE

    This matches the canonical TDLC construct: convergence succeeds when at
    least one declared provider/interface/path tuple closes the required gap.
    UNKNOWN is never converted to failure or success merely because another
    non-feasible path exists.
    """

    results = [evaluate_candidate(**candidate) for candidate in candidates]
    if not results:
        return ConvergenceResult(UNKNOWN, ("NO_DECLARED_CANDIDATE",))

    for result in results:
        if result.state == FEASIBLE:
            return result

    unknown = next((r for r in results if r.state == UNKNOWN), None)
    if unknown is not None:
        return unknown

    if all(r.state == NOT_REQUIRED for r in results):
        return results[0]

    return next(r for r in results if r.state == INFEASIBLE)
