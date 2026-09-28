#!/usr/bin/env python3
"""
shelter_decision.py -- constraint-first community sustainment and shelter decisions.

This module deliberately separates three different graphs/readouts:

1) hydrology/control state (owned elsewhere in FloodConnect/Toledo);
2) the movement DAG in community_dag.py;
3) a support/resource network, which MAY contain lateral/backward edges because food,
   water, medicine, power and helpers can move toward households while people stay put.

It never predicts flood depth, never assumes evacuation is safer than staying, never
turns UNKNOWN into SAFE, and never invents a 24/48/72-hour stock horizon.

Core repository construct:
    Lowest Viable Community Node (LVCN)

LVCN means the lowest declared support layer that is KNOWN to sustain the affected
household/group for a caller-supplied planning horizon.  Egress is never an LVCN
candidate: it is a movement connector, not a sustainment unit.

Literature-facing design notes are documented in:
    docs/SHELTER_DECISION_AND_COMMUNITY_SUSTAINMENT.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import community_dag as cd


UNKNOWN = "UNKNOWN"
SUFFICIENT = "SUFFICIENT"
INSUFFICIENT = "INSUFFICIENT"
NOT_REQUIRED = "NOT_REQUIRED"

SAFE = "SAFE"
UNSAFE = "UNSAFE"

SUSTAINABLE = "SUSTAINABLE"
NOT_SUSTAINABLE = "NOT_SUSTAINABLE"

ESCALATABLE = "ESCALATABLE"
ISOLATED = "ISOLATED"

EXACT_LVCN = "EXACT_LVCN"
KNOWN_VIABLE_UPPER_BOUND = "KNOWN_VIABLE_UPPER_BOUND"
NO_VIABLE_NODE = "NO_VIABLE_NODE"

SUPPORTABLE_KINDS = {
    "household": 0,
    "buddy_cell": 1,
    "zone": 2,
    "internal_safe": 3,
    "external_safe": 4,
}

RESOURCE_FIELDS = (
    "potable_water_for_horizon",
    "food_for_horizon",
    "essential_medicine_for_horizon",
    "service_water_for_horizon",
    "sanitation_hygiene",
    "communications",
    "vulnerable_support",
)

CONDITIONAL_RESOURCE_FIELDS = (
    "critical_power",
)

REASON_MISSING_PLANNING_HORIZON = "MISSING_PLANNING_HORIZON"
REASON_MISSING_SUSTAINMENT_DECLARATION = "MISSING_SUSTAINMENT_DECLARATION"
REASON_STALE_SUSTAINMENT = "STALE_SUSTAINMENT"
REASON_UNKNOWN_PHYSICAL_SAFETY = "UNKNOWN_PHYSICAL_SAFETY"
REASON_PHYSICAL_SAFETY_FAILED = "PHYSICAL_SAFETY_FAILED"
REASON_INSUFFICIENT_WATER = "INSUFFICIENT_WATER"
REASON_INSUFFICIENT_SERVICE_WATER = "INSUFFICIENT_SERVICE_WATER"
REASON_INSUFFICIENT_FOOD = "INSUFFICIENT_FOOD"
REASON_ESSENTIAL_MEDICINE_GAP = "ESSENTIAL_MEDICINE_GAP"
REASON_CRITICAL_POWER_GAP = "CRITICAL_POWER_GAP"
REASON_WASH_GAP = "WASH_GAP"
REASON_COMMUNICATION_GAP = "COMMUNICATION_GAP"
REASON_VULNERABLE_SUPPORT_GAP = "VULNERABLE_SUPPORT_GAP"
REASON_UNKNOWN_ESSENTIAL = "UNKNOWN_ESSENTIAL"
REASON_NO_ESCALATION_MECHANISM = "NO_ESCALATION_MECHANISM"
REASON_ESCALATION_UNKNOWN = "ESCALATION_UNKNOWN"
REASON_SUPPORT_PATH_UNVERIFIED = "SUPPORT_PATH_UNVERIFIED"
REASON_LOWER_NODE_UNRESOLVED = "LOWER_NODE_UNRESOLVED"
REASON_NO_DECLARED_SUPPORT_CHAIN = "NO_DECLARED_SUPPORT_CHAIN"
REASON_RESUPPLY_ROUTE_UNVERIFIED = "RESUPPLY_ROUTE_UNVERIFIED"
REASON_RESUPPLY_DESTINATION_UNVERIFIED = "RESUPPLY_DESTINATION_UNVERIFIED"
REASON_OFFICIAL_MOVEMENT_CONFLICT = "OFFICIAL_MOVEMENT_CONFLICT"
REASON_NO_DECLARED_RESUPPLY_NEED = "NO_DECLARED_RESUPPLY_NEED"
REASON_CURRENT_NODE_UNSAFE = "CURRENT_NODE_UNSAFE"
REASON_SHELTER_UNSAFE = "SHELTER_UNSAFE"
REASON_SHELTER_UNKNOWN = "SHELTER_UNKNOWN"
REASON_SHELTER_CAPACITY_UNKNOWN = "SHELTER_CAPACITY_UNKNOWN"
REASON_SHELTER_CAPACITY_INSUFFICIENT = "SHELTER_CAPACITY_INSUFFICIENT"
REASON_NO_FEASIBLE_SAFE_ROUTE = "NO_FEASIBLE_SAFE_ROUTE"
REASON_INVALID_NODE_KIND = "INVALID_NODE_KIND"
REASON_SUPPORT_PROVIDER_UNVERIFIED = "SUPPORT_PROVIDER_UNVERIFIED"
REASON_SUPPORT_DELIVERY_PATH_UNVERIFIED = "SUPPORT_DELIVERY_PATH_UNVERIFIED"
REASON_SUPPORT_RESOURCE_UNAVAILABLE = "SUPPORT_RESOURCE_UNAVAILABLE"


_FIELD_REASON = {
    "potable_water_for_horizon": REASON_INSUFFICIENT_WATER,
    "service_water_for_horizon": REASON_INSUFFICIENT_SERVICE_WATER,
    "food_for_horizon": REASON_INSUFFICIENT_FOOD,
    "essential_medicine_for_horizon": REASON_ESSENTIAL_MEDICINE_GAP,
    "critical_power": REASON_CRITICAL_POWER_GAP,
    "sanitation_hygiene": REASON_WASH_GAP,
    "communications": REASON_COMMUNICATION_GAP,
    "vulnerable_support": REASON_VULNERABLE_SUPPORT_GAP,
}


SHELTER_PHASE_REQUIREMENTS = {
    "PRE_OPEN": (
        "site_hazard_safety",
        "structural_fire_safety",
        "access_accessibility",
        "communications",
        "capacity",
        "management_staffing",
        "perimeter_flood_defense",
        "dewatering_capability",
        "exit_closure_plan",
    ),
    "OCCUPIED": (
        "site_hazard_safety",
        "structural_fire_safety",
        "access_accessibility",
        "drinking_water",
        "service_water",
        "sanitation_hygiene",
        "food_special_diets",
        "medicine_health",
        "critical_power",
        "communications",
        "capacity",
        "member_accountability",
        "vulnerable_support",
        "resupply_access",
        "management_staffing",
        "waste_management",
        "sleeping_protection",
        "exit_closure_plan",
    ),
    "RECOVERY": (
        "site_hazard_safety",
        "service_water",
        "sanitation_hygiene",
        "medicine_health",
        "communications",
        "waste_management",
        "post_flood_cleaning",
        "exit_closure_plan",
    ),
}


@dataclass(frozen=True)
class SustainmentResult:
    state: str
    reason_codes: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()
    escalation_state: str = UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "reason_codes": list(self.reason_codes),
            "gaps": list(self.gaps),
            "unknown_fields": list(self.unknown_fields),
            "escalation_state": self.escalation_state,
        }


@dataclass(frozen=True)
class LVCNResult:
    state: str
    node_id: Optional[str] = None
    node_kind: Optional[str] = None
    exact: bool = False
    lower_unresolved: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    evaluations: tuple[tuple[str, str], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "node_id": self.node_id,
            "node_kind": self.node_kind,
            "exact": self.exact,
            "lower_unresolved": list(self.lower_unresolved),
            "reason_codes": list(self.reason_codes),
            "evaluations": [list(x) for x in self.evaluations],
        }


@dataclass(frozen=True)
class DecisionResult:
    admitted: bool
    state: str
    reason_codes: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "admitted": self.admitted,
            "state": self.state,
            "reason_codes": list(self.reason_codes),
            "details": dict(self.details),
        }


def _dedup(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _resource_value(block: dict[str, Any], field_name: str) -> str:
    value = block.get(field_name, UNKNOWN)
    if value is True:
        return SUFFICIENT
    if value is False:
        return INSUFFICIENT
    if value in {SUFFICIENT, INSUFFICIENT, UNKNOWN, NOT_REQUIRED}:
        return value
    return UNKNOWN


def _escalation_state(block: dict[str, Any]) -> tuple[str, list[str]]:
    esc = block.get("escalation") or {}
    status = esc.get("status", UNKNOWN)
    if status in {"AVAILABLE", "ASSISTED"}:
        if esc.get("fresh") is True and esc.get("verified") is True:
            return ESCALATABLE, []
        return UNKNOWN, [REASON_ESCALATION_UNKNOWN]
    if status in {"UNAVAILABLE", "BLOCKED"}:
        return ISOLATED, [REASON_NO_ESCALATION_MECHANISM]
    return UNKNOWN, [REASON_ESCALATION_UNKNOWN]


def evaluate_sustainment(
    node: dict[str, Any],
    planning_horizon_h: Optional[float],
) -> SustainmentResult:
    """Evaluate stay/sustain capacity independent of evacuation capability.

    A safe and fully supplied household can be SUSTAINABLE even if its escape route is
    unknown.  Escalation capability is returned separately and must never be allowed to
    turn a safe/supplied node into NOT_SUSTAINABLE.
    """
    if planning_horizon_h is None or planning_horizon_h <= 0:
        return SustainmentResult(
            UNKNOWN,
            (REASON_MISSING_PLANNING_HORIZON,),
            escalation_state=UNKNOWN,
        )

    block = node.get("sustainment")
    if not isinstance(block, dict):
        return SustainmentResult(
            UNKNOWN,
            (REASON_MISSING_SUSTAINMENT_DECLARATION,),
            escalation_state=UNKNOWN,
        )

    if block.get("fresh") is not True:
        return SustainmentResult(
            UNKNOWN,
            (REASON_STALE_SUSTAINMENT,),
            escalation_state=_escalation_state(block)[0],
        )

    physical = block.get("physical_safety", UNKNOWN)
    escalation_state, escalation_reasons = _escalation_state(block)

    if physical == UNSAFE:
        return SustainmentResult(
            NOT_SUSTAINABLE,
            (REASON_PHYSICAL_SAFETY_FAILED,),
            ("physical_safety",),
            escalation_state=escalation_state,
        )
    if physical != SAFE:
        return SustainmentResult(
            UNKNOWN,
            (REASON_UNKNOWN_PHYSICAL_SAFETY,),
            unknown_fields=("physical_safety",),
            escalation_state=escalation_state,
        )

    gaps: list[str] = []
    unknowns: list[str] = []
    reasons: list[str] = []

    for field_name in RESOURCE_FIELDS + CONDITIONAL_RESOURCE_FIELDS:
        value = _resource_value(block, field_name)
        if value == INSUFFICIENT:
            gaps.append(field_name)
            reasons.append(_FIELD_REASON[field_name])
        elif value == UNKNOWN:
            unknowns.append(field_name)

    if gaps:
        return SustainmentResult(
            NOT_SUSTAINABLE,
            _dedup(reasons),
            tuple(gaps),
            tuple(unknowns),
            escalation_state,
        )

    if unknowns:
        return SustainmentResult(
            UNKNOWN,
            (REASON_UNKNOWN_ESSENTIAL,),
            (),
            tuple(unknowns),
            escalation_state,
        )

    # Escalation is intentionally NOT part of sustainment viability.
    return SustainmentResult(
        SUSTAINABLE,
        _dedup(escalation_reasons),
        (),
        (),
        escalation_state,
    )


def _support_edges(doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw = doc.get("support_edges") or []
    return raw if isinstance(raw, list) else []


def _support_path_exists(
    doc: dict[str, Any],
    provider: str,
    recipient: str,
    required_resources: Iterable[str],
) -> bool:
    """Directed resource-delivery reachability over the non-DAG support network."""
    required = set(required_resources)
    outgoing: dict[str, list[dict[str, Any]]] = {}
    for edge in _support_edges(doc):
        if edge.get("status") not in {"OPEN", "ASSISTED"}:
            continue
        if edge.get("fresh") is not True or edge.get("field_verified") is not True:
            continue
        resources = set(edge.get("resources") or [])
        if required and "*" not in resources and not required.issubset(resources):
            continue
        outgoing.setdefault(edge.get("from"), []).append(edge)

    seen = {provider}
    queue = [provider]
    while queue:
        u = queue.pop(0)
        if u == recipient:
            return True
        for edge in outgoing.get(u, []):
            v = edge.get("to")
            if v and v not in seen:
                seen.add(v)
                queue.append(v)
    return False


def _movement_route_to_target(
    doc: dict[str, Any],
    start_node: str,
    target_node: str,
    *,
    group_size: int,
    mode: str,
) -> bool:
    """Use community_dag's own edge/node rules; no duplicated route scoring."""
    fn = getattr(cd, "find_feasible_route_to_target", None)
    if fn is None:
        return False
    result = fn(
        doc,
        start_node,
        target_node,
        group_size=group_size,
        mode=mode,
    )
    return bool(result.found)


def find_lowest_viable_node(
    doc: dict[str, Any],
    household_id: str,
    planning_horizon_h: Optional[float],
    *,
    group_size: int = 1,
    mode: str = "walk",
) -> LVCNResult:
    """Find the exact LVCN or a known-viable upper bound.

    Egress is excluded. Social support nodes require a verified support-delivery path
    toward the household for the household's declared resource gaps. Shelter nodes
    require a verified movement route to the shelter.

    If any lower layer is UNKNOWN, a higher known-viable candidate is returned only as
    KNOWN_VIABLE_UPPER_BOUND, never falsely labelled the exact lowest node.
    """
    nodes = doc.get("nodes") or {}
    if household_id not in nodes:
        return LVCNResult(
            NO_VIABLE_NODE,
            reason_codes=("UNKNOWN_HOUSEHOLD",),
        )

    household = nodes[household_id]
    candidates = household.get("support_candidates")
    if not isinstance(candidates, list) or not candidates:
        return LVCNResult(
            NO_VIABLE_NODE,
            reason_codes=(REASON_NO_DECLARED_SUPPORT_CHAIN,),
        )

    household_eval = evaluate_sustainment(household, planning_horizon_h)
    household_gaps = set(household_eval.gaps)
    physical = (household.get("sustainment") or {}).get("physical_safety", UNKNOWN)

    lower_unresolved: list[str] = []
    evaluations: list[tuple[str, str]] = []

    for node_id in candidates:
        node = nodes.get(node_id)
        if not isinstance(node, dict):
            lower_unresolved.append(node_id)
            evaluations.append((node_id, UNKNOWN))
            continue

        kind = node.get("kind")
        if kind not in SUPPORTABLE_KINDS:
            # egress/supply points/etc. are connectors/services, not viable community nodes.
            continue

        ev = evaluate_sustainment(node, planning_horizon_h)
        evaluations.append((node_id, ev.state))

        if ev.state == UNKNOWN:
            lower_unresolved.append(node_id)
            continue
        if ev.state != SUSTAINABLE:
            continue

        admissible = False

        if node_id == household_id or kind == "household":
            admissible = True

        elif kind in {"buddy_cell", "zone"}:
            # Social support can close resource/service gaps only while the home itself is
            # physically safe. Unsafe occupancy requires movement, not more supplies.
            if physical == SAFE and household_gaps:
                admissible = _support_path_exists(
                    doc, node_id, household_id, household_gaps
                )
            elif physical == SAFE and not household_gaps:
                # A higher social node is unnecessary if the household is already
                # sustainable; if household was UNKNOWN for another reason, do not use
                # the higher node to wash that uncertainty away.
                admissible = False

        elif kind in {"internal_safe", "external_safe"}:
            screen = screen_shelter_candidate(
                node,
                phase="OCCUPIED",
                group_size=group_size,
            )
            if screen.admitted:
                admissible = _movement_route_to_target(
                    doc,
                    household_id,
                    node_id,
                    group_size=group_size,
                    mode=mode,
                )

        if not admissible:
            continue

        exact = not lower_unresolved
        return LVCNResult(
            EXACT_LVCN if exact else KNOWN_VIABLE_UPPER_BOUND,
            node_id=node_id,
            node_kind=kind,
            exact=exact,
            lower_unresolved=tuple(lower_unresolved),
            reason_codes=(
                () if exact else (REASON_LOWER_NODE_UNRESOLVED,)
            ),
            evaluations=tuple(evaluations),
        )

    reasons: list[str] = []
    if lower_unresolved:
        reasons.append(REASON_LOWER_NODE_UNRESOLVED)
    return LVCNResult(
        NO_VIABLE_NODE,
        lower_unresolved=tuple(lower_unresolved),
        reason_codes=_dedup(reasons),
        evaluations=tuple(evaluations),
    )


def evaluate_resupply_window(
    doc: dict[str, Any],
    node_id: str,
    planning_horizon_h: Optional[float],
    *,
    mode: str = "walk",
    group_size: int = 1,
) -> DecisionResult:
    """Admit a resupply opportunity only on fully declared, verified mobility.

    This is an opportunity state, never a command to travel.
    """
    nodes = doc.get("nodes") or {}
    node = nodes.get(node_id)
    if not isinstance(node, dict):
        return DecisionResult(False, "RESUPPLY_NOT_ADMITTED", ("UNKNOWN_NODE",))

    if planning_horizon_h is None or planning_horizon_h <= 0:
        return DecisionResult(
            False, "RESUPPLY_NOT_ADMITTED", (REASON_MISSING_PLANNING_HORIZON,)
        )

    block = node.get("sustainment") or {}
    if block.get("physical_safety") != SAFE:
        return DecisionResult(
            False, "RESUPPLY_NOT_ADMITTED", (REASON_CURRENT_NODE_UNSAFE,)
        )

    gaps = [
        f for f in RESOURCE_FIELDS + CONDITIONAL_RESOURCE_FIELDS
        if _resource_value(block, f) == INSUFFICIENT
    ]
    if not gaps:
        return DecisionResult(
            False, "RESUPPLY_NOT_ADMITTED", (REASON_NO_DECLARED_RESUPPLY_NEED,)
        )

    rs = block.get("resupply") or {}
    if rs.get("official_movement_conflict") is True:
        return DecisionResult(
            False, "RESUPPLY_NOT_ADMITTED", (REASON_OFFICIAL_MOVEMENT_CONFLICT,)
        )

    supplier = rs.get("supplier_node")
    supplier_node = nodes.get(supplier) if supplier else None
    if (
        not isinstance(supplier_node, dict)
        or supplier_node.get("kind") != "supply_point"
        or supplier_node.get("fresh") is not True
        or supplier_node.get("verified_service") is not True
        or supplier_node.get("status") not in {"SAFE", "DEGRADED"}
    ):
        return DecisionResult(
            False,
            "RESUPPLY_NOT_ADMITTED",
            (REASON_RESUPPLY_DESTINATION_UNVERIFIED,),
        )

    route_edges = rs.get("route_edges")
    fn = getattr(cd, "validate_declared_edge_path", None)
    if not isinstance(route_edges, list) or not route_edges or fn is None:
        return DecisionResult(
            False, "RESUPPLY_NOT_ADMITTED", (REASON_RESUPPLY_ROUTE_UNVERIFIED,)
        )

    route = fn(
        doc,
        node_id,
        supplier,
        route_edges,
        group_size=group_size,
        mode=mode,
    )
    if not route.found:
        return DecisionResult(
            False,
            "RESUPPLY_NOT_ADMITTED",
            (REASON_RESUPPLY_ROUTE_UNVERIFIED,),
            {"route_reason": route.reason},
        )

    return DecisionResult(
        True,
        "RESUPPLY_WINDOW",
        (),
        {
            "supplier_node": supplier,
            "declared_gaps": gaps,
            "route": list(route.path),
            "note": "opportunity only; not an automatic travel instruction",
        },
    )



def evaluate_support_delivery(
    doc: dict[str, Any],
    recipient_id: str,
    provider_id: str,
    resources: Iterable[str],
) -> DecisionResult:
    """Evaluate service/resource delivery TOWARD a household/zone.

    This is deliberately different from RESUPPLY_WINDOW: the recipient does not need to
    travel. It represents Thai field patterns such as community kitchens, foundations,
    buddy cells or zone volunteers carrying food/water/medicine toward isolated homes.

    Quantitative throughput is not inferred here. The function only admits a categorical
    deliverability claim when provider and support path are fresh and verified.
    """
    nodes = doc.get("nodes") or {}
    recipient = nodes.get(recipient_id)
    provider = nodes.get(provider_id)
    requested = tuple(dict.fromkeys(resources))

    if not isinstance(recipient, dict):
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", ("UNKNOWN_RECIPIENT",))
    if not isinstance(provider, dict):
        return DecisionResult(
            False, "SUPPORT_DELIVERY_NOT_ADMITTED", (REASON_SUPPORT_PROVIDER_UNVERIFIED,)
        )
    if not requested:
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", ("NO_RESOURCE_REQUEST",))

    if (
        provider.get("fresh") is not True
        or provider.get("status") not in {"SAFE", "DEGRADED"}
    ):
        return DecisionResult(
            False, "SUPPORT_DELIVERY_NOT_ADMITTED", (REASON_SUPPORT_PROVIDER_UNVERIFIED,)
        )

    provider_resources = set(provider.get("services") or []) | set(provider.get("resources") or [])
    missing = [r for r in requested if r not in provider_resources and "*" not in provider_resources]
    if missing:
        return DecisionResult(
            False,
            "SUPPORT_DELIVERY_NOT_ADMITTED",
            (REASON_SUPPORT_RESOURCE_UNAVAILABLE,),
            {"missing_resources": missing},
        )

    if not _support_path_exists(doc, provider_id, recipient_id, requested):
        return DecisionResult(
            False,
            "SUPPORT_DELIVERY_NOT_ADMITTED",
            (REASON_SUPPORT_DELIVERY_PATH_UNVERIFIED,),
        )

    return DecisionResult(
        True,
        "SUPPORT_DELIVERY_AVAILABLE",
        (),
        {
            "provider_node": provider_id,
            "recipient_node": recipient_id,
            "resources": list(requested),
            "note": "categorical deliverability only; no throughput inferred",
        },
    )


def screen_shelter_candidate(
    node: dict[str, Any],
    *,
    phase: str = "OCCUPIED",
    group_size: int = 1,
    needs: Iterable[str] = (),
) -> DecisionResult:
    """Constraint-first phase-aware shelter screening."""
    if node.get("kind") not in {"internal_safe", "external_safe"}:
        return DecisionResult(False, "SHELTER_REJECTED", (REASON_INVALID_NODE_KIND,))

    block = node.get("shelter")
    if not isinstance(block, dict):
        return DecisionResult(False, "SHELTER_UNRESOLVED", (REASON_SHELTER_UNKNOWN,))

    phase = phase.upper()
    required = SHELTER_PHASE_REQUIREMENTS.get(phase)
    if required is None:
        return DecisionResult(False, "SHELTER_UNRESOLVED", ("UNKNOWN_SHELTER_PHASE",))

    failed: list[str] = []
    unknown: list[str] = []
    for field_name in required:
        value = block.get(field_name, UNKNOWN)
        if field_name == "capacity":
            cap = node.get("capacity_persons")
            occ = node.get("occupied_persons")
            if cap is None or occ is None:
                unknown.append(field_name)
            else:
                try:
                    if int(cap) - int(occ) < group_size:
                        failed.append(field_name)
                except (TypeError, ValueError):
                    unknown.append(field_name)
            continue

        if value in {False, "UNSAFE", "INSUFFICIENT", "UNAVAILABLE", "BLOCKED"}:
            failed.append(field_name)
        elif value not in {True, "SAFE", "SUFFICIENT", "AVAILABLE", "READY", NOT_REQUIRED}:
            unknown.append(field_name)

    services = set(node.get("services") or [])
    missing_needs = set(needs) - services
    if missing_needs:
        failed.extend(f"service:{x}" for x in sorted(missing_needs))

    if failed:
        return DecisionResult(
            False,
            "SHELTER_REJECTED",
            (REASON_SHELTER_UNSAFE,),
            {"failed": failed, "unknown": unknown, "phase": phase},
        )
    if unknown:
        reasons = [REASON_SHELTER_UNKNOWN]
        if "capacity" in unknown:
            reasons.append(REASON_SHELTER_CAPACITY_UNKNOWN)
        return DecisionResult(
            False,
            "SHELTER_UNRESOLVED",
            _dedup(reasons),
            {"unknown": unknown, "phase": phase},
        )

    return DecisionResult(
        True,
        "SHELTER_ADMISSIBLE",
        (),
        {"phase": phase},
    )


def aggregate_member_need_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Return privacy-preserving operational demand categories.

    The public graph should store aggregate counts/flags, not names, diagnoses, phone
    numbers or room/house identifiers.  Medical fields are functional needs rather than
    diagnoses.
    """
    allowed = (
        # age/life-stage groups
        "child_0_5",
        "child_6_12",
        "adolescent_13_17",
        "adult_18_59",
        "older_adult_60_plus",
        "pregnant_person",
        "postpartum_person",

        # health / functional dependency
        "mobility_assistance",
        "essential_medication",
        "time_critical_medical_followup",
        "medical_device_power_dependency",
        "communication_assistance",
        "special_diet",
        "infant_feeding",

        # living arrangement / household composition
        "single_person_household",
        "older_adult_alone",
        "single_caregiver_household",
        "dependents_without_co_resident_capable_adult",
        "co_resident_capable_adults",
        "co_resident_caregivers",
        "unreachable_households",

        # declared support-link coverage; do not infer from age alone
        "child_caregiver_link_uncovered",
        "older_adult_support_link_uncovered",
        "pregnancy_support_link_uncovered",
        "medical_support_link_uncovered",
        "living_alone_buddy_link_uncovered",
    )
    out = {k: profile.get(k) for k in allowed if k in profile}
    out["privacy"] = "aggregate_operational_needs_only"
    return out


def evaluate_dependency_coverage(profile: dict[str, Any]) -> DecisionResult:
    """Check whether declared functional dependencies have a support link.

    This is intentionally relationship-based, not demographic scoring.
    Being a child, older adult, pregnant person or patient does not by itself mean
    "not viable". The failure condition is an explicitly declared support dependency
    that lacks a corresponding caregiver/buddy/medical/logistics link.

    Input is aggregate only; no names or diagnoses are required.
    """
    uncovered_fields = (
        "child_caregiver_link_uncovered",
        "older_adult_support_link_uncovered",
        "pregnancy_support_link_uncovered",
        "medical_support_link_uncovered",
        "living_alone_buddy_link_uncovered",
    )
    missing = []
    uncovered = []
    for field_name in uncovered_fields:
        value = profile.get(field_name, UNKNOWN)
        if value == UNKNOWN or value is None:
            missing.append(field_name)
            continue
        try:
            if int(value) > 0:
                uncovered.append(field_name)
        except (TypeError, ValueError):
            missing.append(field_name)

    if uncovered:
        return DecisionResult(
            False,
            "DEPENDENCY_SUPPORT_GAP",
            (REASON_VULNERABLE_SUPPORT_GAP,),
            {"uncovered_links": uncovered},
        )
    if missing:
        return DecisionResult(
            False,
            "DEPENDENCY_COVERAGE_UNKNOWN",
            (REASON_UNKNOWN_ESSENTIAL,),
            {"unknown_links": missing},
        )
    return DecisionResult(True, "DEPENDENCY_COVERED", (), {})


def recommend_protective_state(
    doc: dict[str, Any],
    household_id: str,
    planning_horizon_h: Optional[float],
    *,
    group_size: int = 1,
    mode: str = "walk",
) -> DecisionResult:
    """Small deterministic state machine; no risk score and no forced binary choice."""
    nodes = doc.get("nodes") or {}
    node = nodes.get(household_id)
    if not isinstance(node, dict):
        return DecisionResult(False, "UNKNOWN", ("UNKNOWN_HOUSEHOLD",))

    sustain = evaluate_sustainment(node, planning_horizon_h)
    official = (node.get("sustainment") or {}).get("official_instruction", "NONE")

    # Surface official evacuation instruction without pretending an unsafe route is safe.
    if official == "EVACUATE":
        route = cd.find_safe_route(
            doc,
            household_id,
            group_size=group_size,
            mode=mode,
        )
        if route.found:
            return DecisionResult(
                True,
                "EVACUATE_ROUTE",
                (),
                {"route": list(route.path), "target": route.target, "official": True},
            )
        return DecisionResult(
            False,
            "REQUEST_ASSISTED_EVACUATION",
            (REASON_NO_FEASIBLE_SAFE_ROUTE,),
            {"official": True},
        )

    if sustain.state == SUSTAINABLE:
        rs = evaluate_resupply_window(
            doc,
            household_id,
            planning_horizon_h,
            mode=mode,
            group_size=group_size,
        )
        if rs.admitted:
            return rs
        return DecisionResult(
            True,
            "STAY_AND_SUSTAIN",
            sustain.reason_codes,
            {"escalation_state": sustain.escalation_state},
        )

    if sustain.state == NOT_SUSTAINABLE:
        # Resource failure does not automatically mean the person should enter floodwater.
        # First check declared support providers that can deliver the missing resources inward.
        providers = (node.get("sustainment") or {}).get("support_providers") or []
        for provider_id in providers:
            delivery = evaluate_support_delivery(
                doc,
                household_id,
                provider_id,
                sustain.gaps,
            )
            if delivery.admitted:
                return DecisionResult(
                    True,
                    "REQUEST_OR_RECEIVE_SUPPORT_DELIVERY",
                    (),
                    delivery.details,
                )

        route = cd.find_safe_route(
            doc,
            household_id,
            group_size=group_size,
            mode=mode,
        )
        if route.found:
            return DecisionResult(
                True,
                "PREPARE_TO_MOVE",
                (),
                {"route": list(route.path), "target": route.target},
            )
        return DecisionResult(
            False,
            "REQUEST_LOGISTICS_OR_ASSISTED_EVACUATION",
            (REASON_NO_FEASIBLE_SAFE_ROUTE,) + sustain.reason_codes,
        )

    return DecisionResult(
        False,
        "VERIFY_BEFORE_ACTION",
        sustain.reason_codes,
        {"unknown_fields": list(sustain.unknown_fields)},
    )
