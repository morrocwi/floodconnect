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
import environmental_degradation as envd
import human_animal_household as hahu


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
REASON_MISSING_ASSESSED_HORIZON = "MISSING_ASSESSED_HORIZON"
REASON_ASSESSED_HORIZON_TOO_SHORT = "ASSESSED_HORIZON_TOO_SHORT"
REASON_SUPPORT_CAPACITY_UNKNOWN = "SUPPORT_CAPACITY_UNKNOWN"
REASON_SUPPORT_CAPACITY_INSUFFICIENT = "SUPPORT_CAPACITY_INSUFFICIENT"
REASON_SUPPORT_ARRIVAL_UNKNOWN = "SUPPORT_ARRIVAL_UNKNOWN"
REASON_SUPPORT_ARRIVAL_TOO_LATE = "SUPPORT_ARRIVAL_TOO_LATE"
REASON_SUPPLIER_STOCK_UNKNOWN = "SUPPLIER_STOCK_UNKNOWN"
REASON_SUPPLIER_STOCK_INSUFFICIENT = "SUPPLIER_STOCK_INSUFFICIENT"
REASON_FORWARD_HAZARD_UNKNOWN = "FORWARD_HAZARD_UNKNOWN"
REASON_ENVIRONMENTAL_DEGRADATION_UNSAFE = "ENVIRONMENTAL_DEGRADATION_UNSAFE"
REASON_ENVIRONMENTAL_DEGRADATION_UNKNOWN = "ENVIRONMENTAL_DEGRADATION_UNKNOWN"
REASON_ENVIRONMENTAL_DEGRADATION_WITHIN_HORIZON = "ENVIRONMENTAL_DEGRADATION_WITHIN_HORIZON"


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
        "residual_flood_exposure",
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
        "privacy_dignity",
        "child_safeguarding",
        "gbv_protection",
        "feedback_complaints",
        "family_unity",
        "psychosocial_referral",
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


def _horizon_coverage(block: dict[str, Any], planning_horizon_h: Optional[float]) -> tuple[bool, str | None]:
    if planning_horizon_h is None or planning_horizon_h <= 0:
        return False, REASON_MISSING_PLANNING_HORIZON
    assessed = block.get("assessed_horizon_h")
    if assessed is None:
        return False, REASON_MISSING_ASSESSED_HORIZON
    try:
        assessed_f = float(assessed)
        requested_f = float(planning_horizon_h)
    except (TypeError, ValueError):
        return False, REASON_MISSING_ASSESSED_HORIZON
    if assessed_f < requested_f:
        return False, REASON_ASSESSED_HORIZON_TOO_SHORT
    return True, None


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

    horizon_ok, horizon_reason = _horizon_coverage(block, planning_horizon_h)
    if not horizon_ok:
        return SustainmentResult(
            UNKNOWN,
            (horizon_reason,),
            unknown_fields=("assessed_horizon_h",),
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

    member_profile = node.get("member_need_profile")
    if isinstance(member_profile, dict):
        dependency = evaluate_dependency_coverage(member_profile)
        if dependency.state == "DEPENDENCY_SUPPORT_GAP":
            gaps.append("member_dependency_support")
            reasons.append(REASON_VULNERABLE_SUPPORT_GAP)
        elif dependency.state == "DEPENDENCY_COVERAGE_UNKNOWN":
            unknowns.append("member_dependency_support")

    animal_profile = node.get("animal_profile")
    if isinstance(animal_profile, dict) and hahu.declared_animal_count(animal_profile) > 0:
        animal = hahu.evaluate_animal_unit(animal_profile, planning_horizon_h)
        if animal.state == hahu.NOT_SUSTAINABLE:
            gaps.extend(animal.gaps)
            reasons.extend(animal.reason_codes)
        elif animal.state == hahu.UNKNOWN:
            unknowns.extend(animal.unknown_fields or ("animal_household_unit",))
            reasons.extend(animal.reason_codes)

    env_unknown_reason = None
    if isinstance(node.get("environment"), dict):
        env_result = envd.evaluate_environmental_degradation(node)
        if env_result.state == envd.UNSAFE:
            gaps.append("environmental_health")
            reasons.append(REASON_ENVIRONMENTAL_DEGRADATION_UNSAFE)
        elif env_result.state == envd.UNKNOWN:
            unknowns.append("environmental_health")
            env_unknown_reason = REASON_ENVIRONMENTAL_DEGRADATION_UNKNOWN
        elif (
            env_result.state == envd.DEGRADING
            and env_result.next_deadline_h is not None
            and planning_horizon_h is not None
            and env_result.next_deadline_h <= float(planning_horizon_h)
        ):
            env_block = node.get("environment") or {}
            mitigation_ready = (
                env_block.get("mitigation_plan_verified") is True
                and env_block.get("mitigation_before_deadline") is True
            )
            if not mitigation_ready:
                unknowns.append("environmental_health")
                env_unknown_reason = REASON_ENVIRONMENTAL_DEGRADATION_WITHIN_HORIZON

    if gaps:
        return SustainmentResult(
            NOT_SUSTAINABLE,
            _dedup(reasons),
            tuple(gaps),
            tuple(unknowns),
            escalation_state,
        )

    if unknowns:
        unknown_reasons = [REASON_UNKNOWN_ESSENTIAL]
        if env_unknown_reason:
            unknown_reasons.append(env_unknown_reason)
        return SustainmentResult(
            UNKNOWN,
            _dedup(unknown_reasons),
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


def _support_path_assessment(
    doc: dict[str, Any],
    provider: str,
    recipient: str,
    required_resources: Iterable[str],
) -> tuple[str, tuple[str, ...]]:
    """Return UNVERIFIED, PATH_ONLY, or NEED_CLOSABLE for a support path.

    PATH_ONLY means a fresh field-verified path exists, but capacity and/or arrival-before-
    failure are not yet demonstrated. NEED_CLOSABLE requires every edge on at least one path
    to declare sufficient capacity and timely arrival for the requested resources.
    """
    required = set(required_resources)
    outgoing_verified: dict[str, list[dict[str, Any]]] = {}
    outgoing_closable: dict[str, list[dict[str, Any]]] = {}
    capacity_unknown = False
    arrival_unknown = False
    capacity_failed = False
    arrival_failed = False

    for edge in _support_edges(doc):
        if edge.get("status") not in {"OPEN", "ASSISTED"}:
            continue
        if edge.get("fresh") is not True or edge.get("field_verified") is not True:
            continue
        resources = set(edge.get("resources") or [])
        if required and "*" not in resources and not required.issubset(resources):
            continue

        outgoing_verified.setdefault(edge.get("from"), []).append(edge)

        cap = edge.get("capacity_status", UNKNOWN)
        arrive = edge.get("arrival_before_failure", UNKNOWN)
        cap_ok = cap in {SUFFICIENT, True}
        arrive_ok = arrive is True

        if cap == UNKNOWN or cap is None:
            capacity_unknown = True
        elif not cap_ok:
            capacity_failed = True
        if arrive == UNKNOWN or arrive is None:
            arrival_unknown = True
        elif arrive is not True:
            arrival_failed = True

        if cap_ok and arrive_ok:
            outgoing_closable.setdefault(edge.get("from"), []).append(edge)

    def reachable(graph: dict[str, list[dict[str, Any]]]) -> bool:
        seen = {provider}
        queue = [provider]
        while queue:
            u = queue.pop(0)
            if u == recipient:
                return True
            for edge in graph.get(u, []):
                v = edge.get("to")
                if v and v not in seen:
                    seen.add(v)
                    queue.append(v)
        return False

    if not reachable(outgoing_verified):
        return "UNVERIFIED", (REASON_SUPPORT_DELIVERY_PATH_UNVERIFIED,)
    if reachable(outgoing_closable):
        return "NEED_CLOSABLE", ()

    reasons: list[str] = []
    if capacity_failed:
        reasons.append(REASON_SUPPORT_CAPACITY_INSUFFICIENT)
    elif capacity_unknown:
        reasons.append(REASON_SUPPORT_CAPACITY_UNKNOWN)
    if arrival_failed:
        reasons.append(REASON_SUPPORT_ARRIVAL_TOO_LATE)
    elif arrival_unknown:
        reasons.append(REASON_SUPPORT_ARRIVAL_UNKNOWN)
    return "PATH_ONLY", _dedup(reasons or [REASON_SUPPORT_CAPACITY_UNKNOWN, REASON_SUPPORT_ARRIVAL_UNKNOWN])


def _support_path_exists(
    doc: dict[str, Any],
    provider: str,
    recipient: str,
    required_resources: Iterable[str],
) -> bool:
    state, _ = _support_path_assessment(doc, provider, recipient, required_resources)
    return state != "UNVERIFIED"


def evaluate_support_capability(
    node: dict[str, Any],
    required_resources: Iterable[str],
    planning_horizon_h: Optional[float],
) -> DecisionResult:
    """Evaluate a buddy/zone/provider as a support layer, not an occupancy site."""
    block = node.get("support")
    if not isinstance(block, dict):
        return DecisionResult(False, "SUPPORT_CAPABILITY_UNKNOWN", (REASON_SUPPORT_CAPACITY_UNKNOWN,))
    if block.get("fresh") is not True:
        return DecisionResult(False, "SUPPORT_CAPABILITY_UNKNOWN", (REASON_STALE_SUSTAINMENT,))
    horizon_ok, horizon_reason = _horizon_coverage(block, planning_horizon_h)
    if not horizon_ok:
        return DecisionResult(False, "SUPPORT_CAPABILITY_UNKNOWN", (horizon_reason,))

    resources = block.get("resources") or {}
    unknown: list[str] = []
    insufficient: list[str] = []
    for resource in dict.fromkeys(required_resources):
        entry = resources.get(resource, UNKNOWN)
        status = entry.get("status", UNKNOWN) if isinstance(entry, dict) else entry
        if status in {SUFFICIENT, True, "AVAILABLE"}:
            continue
        if status in {INSUFFICIENT, False, "OUT", "UNAVAILABLE"}:
            insufficient.append(resource)
        else:
            unknown.append(resource)

    if insufficient:
        return DecisionResult(
            False,
            "SUPPORT_CAPABILITY_INSUFFICIENT",
            (REASON_SUPPORT_CAPACITY_INSUFFICIENT,),
            {"insufficient_resources": insufficient},
        )
    if unknown:
        return DecisionResult(
            False,
            "SUPPORT_CAPABILITY_UNKNOWN",
            (REASON_SUPPORT_CAPACITY_UNKNOWN,),
            {"unknown_resources": unknown},
        )
    return DecisionResult(True, "SUPPORT_CAPABLE", (), {"resources": list(dict.fromkeys(required_resources))})


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
    """Find the lowest known support layer without conflating support with occupancy."""
    nodes = doc.get("nodes") or {}
    household = nodes.get(household_id)
    if not isinstance(household, dict):
        return LVCNResult(NO_VIABLE_NODE, reason_codes=("UNKNOWN_HOUSEHOLD",))

    candidates = household.get("support_candidates")
    if not isinstance(candidates, list) or not candidates:
        return LVCNResult(NO_VIABLE_NODE, reason_codes=(REASON_NO_DECLARED_SUPPORT_CHAIN,))

    # Never trust YAML/list order for "lowest": normalize by the repository layer ranking.
    ranked: list[tuple[int, int, str, dict[str, Any]]] = []
    for position, node_id in enumerate(candidates):
        node = nodes.get(node_id)
        if not isinstance(node, dict):
            ranked.append((999, position, node_id, {}))
            continue
        kind = node.get("kind")
        if kind in SUPPORTABLE_KINDS:
            ranked.append((SUPPORTABLE_KINDS[kind], position, node_id, node))
    ranked.sort(key=lambda x: (x[0], x[1]))

    household_eval = evaluate_sustainment(household, planning_horizon_h)
    household_gaps = tuple(g for g in household_eval.gaps if g != "physical_safety")
    physical = (household.get("sustainment") or {}).get("physical_safety", UNKNOWN)

    lower_unresolved: list[str] = []
    evaluations: list[tuple[str, str]] = []

    for _, _, node_id, node in ranked:
        if not node:
            lower_unresolved.append(node_id)
            evaluations.append((node_id, UNKNOWN))
            continue
        kind = node.get("kind")

        if kind == "household":
            ev_state = household_eval.state if node_id == household_id else evaluate_sustainment(node, planning_horizon_h).state
            evaluations.append((node_id, ev_state))
            if ev_state == UNKNOWN:
                lower_unresolved.append(node_id)
                continue
            if ev_state != SUSTAINABLE:
                continue
            exact = not lower_unresolved
            return LVCNResult(
                EXACT_LVCN if exact else KNOWN_VIABLE_UPPER_BOUND,
                node_id=node_id,
                node_kind=kind,
                exact=exact,
                lower_unresolved=tuple(lower_unresolved),
                reason_codes=(() if exact else (REASON_LOWER_NODE_UNRESOLVED,)),
                evaluations=tuple(evaluations),
            )

        if kind in {"buddy_cell", "zone"}:
            # A social layer does not need to be habitable. It must be able to close the
            # household's declared resource gaps through a verified, sufficient, timely path.
            if physical != SAFE or not household_gaps:
                evaluations.append((node_id, NOT_SUSTAINABLE))
                continue
            cap = evaluate_support_capability(node, household_gaps, planning_horizon_h)
            path_state, path_reasons = _support_path_assessment(
                doc, node_id, household_id, household_gaps
            )
            if cap.state == "SUPPORT_CAPABILITY_UNKNOWN" or path_state == "PATH_ONLY":
                lower_unresolved.append(node_id)
                evaluations.append((node_id, UNKNOWN))
                continue
            if not cap.admitted or path_state != "NEED_CLOSABLE":
                evaluations.append((node_id, NOT_SUSTAINABLE))
                continue
            evaluations.append((node_id, SUSTAINABLE))
            exact = not lower_unresolved
            return LVCNResult(
                EXACT_LVCN if exact else KNOWN_VIABLE_UPPER_BOUND,
                node_id=node_id,
                node_kind=kind,
                exact=exact,
                lower_unresolved=tuple(lower_unresolved),
                reason_codes=(() if exact else (REASON_LOWER_NODE_UNRESOLVED,)),
                evaluations=tuple(evaluations),
            )

        if kind in {"internal_safe", "external_safe"}:
            screen = screen_shelter_candidate(node, phase="OCCUPIED", group_size=group_size)
            if screen.state == "SHELTER_UNRESOLVED":
                lower_unresolved.append(node_id)
                evaluations.append((node_id, UNKNOWN))
                continue
            if not screen.admitted:
                evaluations.append((node_id, NOT_SUSTAINABLE))
                continue

            animal_profile = household.get("animal_profile")
            if isinstance(animal_profile, dict) and hahu.declared_animal_count(animal_profile) > 0:
                animal_move = hahu.evaluate_animal_movement_readiness(animal_profile)
                if animal_move.state == hahu.UNKNOWN:
                    lower_unresolved.append(node_id)
                    evaluations.append((node_id, UNKNOWN))
                    continue
                if animal_move.state != hahu.READY:
                    evaluations.append((node_id, NOT_SUSTAINABLE))
                    continue
                animal_destination = hahu.screen_animal_destination(
                    node, animal_profile, doc=doc
                )
                if animal_destination.state == hahu.UNKNOWN:
                    lower_unresolved.append(node_id)
                    evaluations.append((node_id, UNKNOWN))
                    continue
                if animal_destination.state != hahu.SUSTAINABLE:
                    evaluations.append((node_id, NOT_SUSTAINABLE))
                    continue

            reachable = _movement_route_to_target(
                doc, household_id, node_id, group_size=group_size, mode=mode
            )
            evaluations.append((node_id, SUSTAINABLE if reachable else NOT_SUSTAINABLE))
            if not reachable:
                continue
            exact = not lower_unresolved
            return LVCNResult(
                EXACT_LVCN if exact else KNOWN_VIABLE_UPPER_BOUND,
                node_id=node_id,
                node_kind=kind,
                exact=exact,
                lower_unresolved=tuple(lower_unresolved),
                reason_codes=(() if exact else (REASON_LOWER_NODE_UNRESOLVED,)),
                evaluations=tuple(evaluations),
            )

    reasons = [REASON_LOWER_NODE_UNRESOLVED] if lower_unresolved else []
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
    animal_profile = node.get("animal_profile")
    if isinstance(animal_profile, dict) and hahu.declared_animal_count(animal_profile) > 0:
        animal = hahu.evaluate_animal_unit(animal_profile, planning_horizon_h)
        if animal.state == hahu.NOT_SUSTAINABLE:
            gaps.extend(
                g for g in animal.gaps
                if g in hahu.ANIMAL_RESOURCE_FIELDS or g == "cat_litter_for_horizon"
            )
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
        or supplier_node.get("kind") not in {"supply_point", "service_node"}
        or supplier_node.get("fresh") is not True
        or supplier_node.get("verified_service") is not True
        or supplier_node.get("status") not in {"SAFE", "DEGRADED"}
    ):
        return DecisionResult(
            False,
            "RESUPPLY_NOT_ADMITTED",
            (REASON_RESUPPLY_DESTINATION_UNVERIFIED,),
        )

    stock = evaluate_support_capability(supplier_node, gaps, planning_horizon_h)
    if not stock.admitted:
        reason = (
            REASON_SUPPLIER_STOCK_INSUFFICIENT
            if stock.state == "SUPPORT_CAPABILITY_INSUFFICIENT"
            else REASON_SUPPLIER_STOCK_UNKNOWN
        )
        return DecisionResult(
            False,
            "RESUPPLY_NOT_ADMITTED",
            (reason,) + stock.reason_codes,
            stock.details,
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
    planning_horizon_h: Optional[float] = None,
) -> DecisionResult:
    """Distinguish a usable path from a support flow that can actually close the need."""
    nodes = doc.get("nodes") or {}
    recipient = nodes.get(recipient_id)
    provider = nodes.get(provider_id)
    requested = tuple(dict.fromkeys(resources))

    if not isinstance(recipient, dict):
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", ("UNKNOWN_RECIPIENT",))
    if not isinstance(provider, dict):
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", (REASON_SUPPORT_PROVIDER_UNVERIFIED,))
    if not requested:
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", ("NO_RESOURCE_REQUEST",))
    if provider.get("fresh") is not True or provider.get("status") not in {"SAFE", "DEGRADED"}:
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", (REASON_SUPPORT_PROVIDER_UNVERIFIED,))

    capability = evaluate_support_capability(provider, requested, planning_horizon_h)
    path_state, path_reasons = _support_path_assessment(
        doc, provider_id, recipient_id, requested
    )

    if path_state == "UNVERIFIED":
        return DecisionResult(False, "SUPPORT_DELIVERY_NOT_ADMITTED", path_reasons)

    if not capability.admitted or path_state != "NEED_CLOSABLE":
        reasons = capability.reason_codes + path_reasons
        return DecisionResult(
            False,
            "SUPPORT_DELIVERY_PATH_ONLY",
            _dedup(reasons),
            {
                "provider_node": provider_id,
                "recipient_node": recipient_id,
                "resources": list(requested),
                "path_state": path_state,
                "capability_state": capability.state,
                "note": "a route/provider may exist, but need closure within the planning horizon is not demonstrated",
            },
        )

    return DecisionResult(
        True,
        "SUPPORT_DELIVERY_NEED_CLOSABLE",
        (),
        {
            "provider_node": provider_id,
            "recipient_node": recipient_id,
            "resources": list(requested),
            "path_state": path_state,
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
        if field_name == "residual_flood_exposure":
            if value in {"NONE", NOT_REQUIRED, False}:
                continue
            if value in {"PRESENT", "LIKELY", True}:
                for conditional in ("perimeter_flood_defense", "dewatering_capability"):
                    cv = block.get(conditional, UNKNOWN)
                    if cv in {False, "UNSAFE", "INSUFFICIENT", "UNAVAILABLE", "BLOCKED"}:
                        failed.append(conditional)
                    elif cv not in {True, "SAFE", "SUFFICIENT", "AVAILABLE", "READY", NOT_REQUIRED}:
                        unknown.append(conditional)
                continue
            unknown.append(field_name)
            continue

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

    environment_details = {}
    env_required = block.get("environmental_assessment_required") is True
    if isinstance(node.get("environment"), dict):
        env_result = envd.evaluate_environmental_degradation(node)
        environment_details = env_result.as_dict()
        if env_result.state == envd.UNSAFE:
            failed.append("environmental_degradation")
        elif env_result.state == envd.UNKNOWN:
            unknown.append("environmental_degradation")
    elif env_required:
        unknown.append("environmental_degradation")

    services = set(node.get("services") or [])
    missing_needs = set(needs) - services
    if missing_needs:
        failed.extend(f"service:{x}" for x in sorted(missing_needs))

    if failed:
        return DecisionResult(
            False,
            "SHELTER_REJECTED",
            (REASON_SHELTER_UNSAFE,),
            {"failed": failed, "unknown": unknown, "phase": phase, "environment": environment_details},
        )
    if unknown:
        reasons = [REASON_SHELTER_UNKNOWN]
        if "capacity" in unknown:
            reasons.append(REASON_SHELTER_CAPACITY_UNKNOWN)
        return DecisionResult(
            False,
            "SHELTER_UNRESOLVED",
            _dedup(reasons),
            {"unknown": unknown, "phase": phase, "environment": environment_details},
        )

    return DecisionResult(
        True,
        "SHELTER_ADMISSIBLE",
        (),
        {"phase": phase, "environment": environment_details},
    )


VULNERABILITY_COUNT_FIELDS = (
    "child_0_5",
    "child_6_12",
    "adolescent_13_17",
    "older_adult_60_plus",
    "pregnant_person",
    "postpartum_person",
    "chronic_or_acute_illness",
    "disability_or_functional_limitation",
    "bedbound_or_homebound",
)

FUNCTIONAL_NEED_COUNT_FIELDS = (
    "needs_continuous_supervision",
    "needs_mobility_assistance",
    "needs_essential_medication",
    "needs_time_critical_medical_followup",
    "needs_power_dependent_medical_device",
    "needs_communication_assistance",
    "needs_special_diet",
    "needs_infant_feeding",
    "needs_maternal_health_access",
)

SUPPORT_LINK_FIELDS = (
    "child_caregiver_link_uncovered",
    "backup_caregiver_link_uncovered",
    "older_adult_support_link_uncovered",
    "pregnancy_support_link_uncovered",
    "medical_support_link_uncovered",
    "mobility_support_link_uncovered",
    "power_dependency_support_link_uncovered",
    "communication_support_link_uncovered",
    "living_alone_buddy_link_uncovered",
)

LIVING_ARRANGEMENTS = {
    "ALONE",
    "PAIR",
    "FAMILY_GROUP",
    "MULTIGENERATIONAL",
    "GROUP_CARE",
    "UNKNOWN",
}


def _count(profile: dict[str, Any], field_name: str) -> Optional[int]:
    value = profile.get(field_name)
    if value is None or value == UNKNOWN:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def classify_group_configuration(profile: dict[str, Any]) -> DecisionResult:
    """Classify household/group composition without turning demographics into risk scores.

    The returned tags describe *who is together with whom* so the support matcher can ask
    the right questions. Tags NEVER by themselves mean unsafe or non-viable.

    Examples:
    - an older-only pair is not assumed helpless;
    - an older adult + child household is flagged for assessment, not automatically failed;
    - a multigenerational household may have strong internal support, but helper capacity
      still must be declared by function.
    """
    total = _count(profile, "total_persons")
    if total is None:
        return DecisionResult(
            False,
            "GROUP_CONFIGURATION_UNKNOWN",
            (REASON_UNKNOWN_ESSENTIAL,),
            {"unknown": ["total_persons"]},
        )

    counts = {k: _count(profile, k) for k in VULNERABILITY_COUNT_FIELDS}
    known_counts = {k: (v or 0) for k, v in counts.items() if v is not None}
    unknown_counts = [k for k, v in counts.items() if v is None]

    children = sum(known_counts.get(k, 0) for k in ("child_0_5", "child_6_12", "adolescent_13_17"))
    older = known_counts.get("older_adult_60_plus", 0)
    pregnant = known_counts.get("pregnant_person", 0)
    postpartum = known_counts.get("postpartum_person", 0)
    illness = known_counts.get("chronic_or_acute_illness", 0)
    disability = known_counts.get("disability_or_functional_limitation", 0)
    bedbound = known_counts.get("bedbound_or_homebound", 0)
    adults = _count(profile, "adult_18_59")
    adults = adults if adults is not None else max(0, total - children - older)

    tags: list[str] = []
    if total == 1:
        tags.append("LIVES_ALONE")
    elif total == 2:
        tags.append("PAIR")
    elif total >= 3:
        tags.append("GROUP")

    if children > 0 and older > 0 and adults == 0:
        tags.append("CHILD_WITH_OLDER_ONLY")
    if older > 0 and older == total:
        tags.append("OLDER_ONLY_HOUSEHOLD")
    if pregnant > 0 and total == 1:
        tags.append("PREGNANT_ALONE")
    if postpartum > 0 and total == 1:
        tags.append("POSTPARTUM_ALONE")
    if (illness > 0 or disability > 0 or bedbound > 0) and total == 1:
        tags.append("HEALTH_DEPENDENCY_ALONE")
    if children > 0 and adults > 0 and older > 0:
        tags.append("MULTIGENERATIONAL")
    if _count(profile, "single_caregiver_household") not in {None, 0}:
        tags.append("SINGLE_CAREGIVER_WITH_DEPENDENTS")
    if _count(profile, "dependents_without_co_resident_capable_adult") not in {None, 0}:
        tags.append("NO_CO_RESIDENT_CAPABLE_ADULT")

    dependency_types = sum(
        1 for k in FUNCTIONAL_NEED_COUNT_FIELDS if (_count(profile, k) or 0) > 0
    )
    if dependency_types >= 2:
        tags.append("MULTIPLE_FUNCTIONAL_DEPENDENCIES")

    living = profile.get("living_arrangement", "UNKNOWN")
    if living not in LIVING_ARRANGEMENTS:
        living = "UNKNOWN"

    return DecisionResult(
        True,
        "GROUP_CONFIGURATION_CLASSIFIED",
        (),
        {
            "living_arrangement": living,
            "composition_tags": tags,
            "unknown_demographic_counts": unknown_counts,
            "note": "composition tags trigger assessment; they do not determine viability",
        },
    )


def required_support_links(profile: dict[str, Any]) -> tuple[str, ...]:
    """Return the minimum link types that must be checked for this declared composition.

    These are FloodConnect operational assessment rules, not a claim that every person in
    a demographic category is dependent. Demographic category triggers an assessment;
    functional-need fields trigger the hard support-link requirement.
    """
    required: list[str] = []

    children = sum((_count(profile, k) or 0) for k in ("child_0_5", "child_6_12"))
    adolescents = _count(profile, "adolescent_13_17") or 0
    if children > 0 or adolescents > 0:
        required.append("child_caregiver_link_uncovered")

    if (_count(profile, "single_caregiver_household") or 0) > 0 and (
        children > 0
        or (_count(profile, "needs_continuous_supervision") or 0) > 0
        or (_count(profile, "needs_mobility_assistance") or 0) > 0
    ):
        required.append("backup_caregiver_link_uncovered")

    # Older age alone is not a dependency. Require a support link only when a functional
    # support need is actually declared.
    if (_count(profile, "older_adult_60_plus") or 0) > 0 and any(
        (_count(profile, k) or 0) > 0
        for k in (
            "needs_mobility_assistance",
            "needs_essential_medication",
            "needs_communication_assistance",
            "needs_continuous_supervision",
        )
    ):
        required.append("older_adult_support_link_uncovered")

    # Pregnancy/postpartum are assessment triggers, not automatic dependency labels.
    # A hard support link is required only when a functional maternal-health need is declared.
    if (
        ((_count(profile, "pregnant_person") or 0) > 0 or (_count(profile, "postpartum_person") or 0) > 0)
        and (_count(profile, "needs_maternal_health_access") or 0) > 0
    ):
        required.append("pregnancy_support_link_uncovered")

    if any(
        (_count(profile, k) or 0) > 0
        for k in (
            "needs_essential_medication",
            "needs_time_critical_medical_followup",
            "bedbound_or_homebound",
            "needs_power_dependent_medical_device",
        )
    ):
        required.append("medical_support_link_uncovered")

    if (_count(profile, "needs_mobility_assistance") or 0) > 0:
        required.append("mobility_support_link_uncovered")

    if (_count(profile, "needs_power_dependent_medical_device") or 0) > 0:
        required.append("power_dependency_support_link_uncovered")

    if (_count(profile, "needs_communication_assistance") or 0) > 0:
        required.append("communication_support_link_uncovered")

    if _count(profile, "total_persons") == 1 and (
        any((_count(profile, k) or 0) > 0 for k in VULNERABILITY_COUNT_FIELDS)
        or any((_count(profile, k) or 0) > 0 for k in FUNCTIONAL_NEED_COUNT_FIELDS)
    ):
        required.append("living_alone_buddy_link_uncovered")

    return _dedup(required)


def aggregate_member_need_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Return privacy-preserving operational demand and composition categories.

    Store counts/links, not names, diagnoses, phone numbers, room numbers or household
    identifiers. Health is represented as a functional dependency, not a diagnosis.
    """
    allowed = (
        "total_persons",
        "living_arrangement",
        "child_0_5",
        "child_6_12",
        "adolescent_13_17",
        "adult_18_59",
        "older_adult_60_plus",
        "pregnant_person",
        "postpartum_person",
        "chronic_or_acute_illness",
        "disability_or_functional_limitation",
        "bedbound_or_homebound",
        "needs_continuous_supervision",
        "needs_mobility_assistance",
        "needs_essential_medication",
        "needs_time_critical_medical_followup",
        "needs_power_dependent_medical_device",
        "needs_communication_assistance",
        "needs_special_diet",
        "needs_infant_feeding",
        "needs_maternal_health_access",
        "single_person_household",
        "older_adult_alone",
        "single_caregiver_household",
        "dependents_without_co_resident_capable_adult",
        "co_resident_capable_adults",
        "co_resident_caregivers",
        "unreachable_households",
    ) + SUPPORT_LINK_FIELDS
    out = {k: profile.get(k) for k in allowed if k in profile}
    out["required_support_links"] = list(required_support_links(profile))
    config = classify_group_configuration(profile)
    if config.admitted:
        out["composition_tags"] = config.details.get("composition_tags", [])
    out["privacy"] = "aggregate_operational_needs_only"
    return out


def evaluate_dependency_coverage(profile: dict[str, Any]) -> DecisionResult:
    """Check whether the household's *required* support relationships are covered.

    Pairing logic is functional:
    - children -> caregiver link;
    - single caregiver + dependents -> backup-caregiver link;
    - older adult -> support link only when functional need is declared;
    - pregnancy/postpartum -> pregnancy/health/transport support check;
    - illness/bedbound/medication -> medical support link;
    - living alone + vulnerability/dependency -> buddy/reassessment link.

    This avoids both errors: treating all older/pregnant/ill people as helpless, and
    ignoring the fact that two dependent people living together may still have no helper.
    """
    required = required_support_links(profile)
    if not required:
        return DecisionResult(True, "NO_SPECIAL_DEPENDENCY_LINK_REQUIRED", (), {})

    unknown: list[str] = []
    uncovered: list[str] = []
    for field_name in required:
        value = profile.get(field_name, UNKNOWN)
        if value == UNKNOWN or value is None:
            unknown.append(field_name)
            continue
        try:
            if int(value) > 0:
                uncovered.append(field_name)
        except (TypeError, ValueError):
            unknown.append(field_name)

    if uncovered:
        return DecisionResult(
            False,
            "DEPENDENCY_SUPPORT_GAP",
            (REASON_VULNERABLE_SUPPORT_GAP,),
            {
                "required_links": list(required),
                "uncovered_links": uncovered,
                "composition": classify_group_configuration(profile).details,
            },
        )
    if unknown:
        return DecisionResult(
            False,
            "DEPENDENCY_COVERAGE_UNKNOWN",
            (REASON_UNKNOWN_ESSENTIAL,),
            {
                "required_links": list(required),
                "unknown_links": unknown,
                "composition": classify_group_configuration(profile).details,
            },
        )
    return DecisionResult(
        True,
        "DEPENDENCY_COVERED",
        (),
        {
            "required_links": list(required),
            "composition": classify_group_configuration(profile).details,
        },
    )


def _forward_hazard_state(
    node: dict[str, Any],
    planning_horizon_h: Optional[float],
    explicit: Optional[dict[str, Any]] = None,
) -> tuple[str, dict[str, Any], tuple[str, ...]]:
    block = explicit if isinstance(explicit, dict) else (node.get("sustainment") or {}).get("forward_hazard")
    if not isinstance(block, dict):
        return UNKNOWN, {}, (REASON_FORWARD_HAZARD_UNKNOWN,)
    if block.get("fresh") is not True:
        return UNKNOWN, block, (REASON_FORWARD_HAZARD_UNKNOWN,)
    state = str(block.get("state", UNKNOWN)).upper()
    valid = {"NONE", "LOW", "WATCH", "HIGH", "CRITICAL", "ACTIVE"}
    if state not in valid:
        return UNKNOWN, block, (REASON_FORWARD_HAZARD_UNKNOWN,)
    horizon = block.get("horizon_h")
    if horizon is not None and planning_horizon_h is not None:
        try:
            if float(horizon) < float(planning_horizon_h):
                return UNKNOWN, block, (REASON_FORWARD_HAZARD_UNKNOWN,)
        except (TypeError, ValueError):
            return UNKNOWN, block, (REASON_FORWARD_HAZARD_UNKNOWN,)
    return state, block, ()


def _household_animal_route_context(
    doc: dict[str, Any],
    household: dict[str, Any],
    route_target: Optional[str] = None,
) -> tuple[tuple[str, ...], Optional[DecisionResult]]:
    profile = household.get("animal_profile")
    if not isinstance(profile, dict) or hahu.declared_animal_count(profile) <= 0:
        return (), None

    needs = hahu.animal_route_needs(profile)
    if route_target is None:
        return needs, None

    nodes = doc.get("nodes") or {}
    target = nodes.get(route_target)
    if not isinstance(target, dict):
        return needs, DecisionResult(
            False,
            "ANIMAL_DESTINATION_UNKNOWN",
            ("ANIMAL_DESTINATION_UNKNOWN",),
        )

    accommodation = hahu.screen_animal_destination(target, profile, doc=doc)
    if accommodation.state == hahu.SUSTAINABLE:
        return needs, DecisionResult(True, "ANIMAL_DESTINATION_ADMISSIBLE", (), {})
    if accommodation.state == hahu.NOT_SUSTAINABLE:
        return needs, DecisionResult(
            False,
            "ANIMAL_DESTINATION_REJECTED",
            accommodation.reason_codes,
            {"gaps": list(accommodation.gaps)},
        )
    return needs, DecisionResult(
        False,
        "ANIMAL_DESTINATION_UNRESOLVED",
        accommodation.reason_codes,
        {"unknown_fields": list(accommodation.unknown_fields)},
    )


def recommend_protective_state(
    doc: dict[str, Any],
    household_id: str,
    planning_horizon_h: Optional[float],
    *,
    group_size: int = 1,
    mode: str = "walk",
    forward_hazard: Optional[dict[str, Any]] = None,
) -> DecisionResult:
    """Decision operator keeping current viability separate from forward hazard."""
    nodes = doc.get("nodes") or {}
    node = nodes.get(household_id)
    if not isinstance(node, dict):
        return DecisionResult(False, "UNKNOWN", ("UNKNOWN_HOUSEHOLD",))

    sustain = evaluate_sustainment(node, planning_horizon_h)
    block = node.get("sustainment") or {}
    animal_profile = node.get("animal_profile")
    animal_needs, _ = _household_animal_route_context(doc, node)
    route_service_needs = (
        ()
        if not isinstance(animal_profile, dict)
        else hahu.movement_route_service_needs(animal_profile)
    )
    animal_movement = (
        None
        if not isinstance(animal_profile, dict)
        else hahu.evaluate_animal_movement_readiness(animal_profile)
    )
    animal_transport_ready = animal_movement is None or animal_movement.state == hahu.READY
    official = block.get("official_instruction", "NONE")
    forward_state, forward_block, forward_reasons = _forward_hazard_state(
        node, planning_horizon_h, forward_hazard
    )

    if official == "EVACUATE":
        route = cd.find_safe_route(
            doc, household_id, group_size=group_size, mode=mode, needs=route_service_needs
        )
        if route.found and animal_transport_ready:
            _, animal_target = _household_animal_route_context(doc, node, route.target)
            if animal_target is None or animal_target.admitted:
                return DecisionResult(
                    True, "EVACUATE_ROUTE", (),
                    {
                        "route": list(route.path),
                        "target": route.target,
                        "official": True,
                        "animal_route_needs": list(animal_needs),
                    },
                )
        if animal_needs:
            return DecisionResult(
                False,
                "REQUEST_ASSISTED_EVACUATION_WITH_ANIMALS",
                (REASON_NO_FEASIBLE_SAFE_ROUTE,),
                {
                    "official": True,
                    "animal_transport_ready": animal_transport_ready,
                    "animal_movement_state": (
                        None if animal_movement is None else animal_movement.state
                    ),
                    "animal_route_needs": list(animal_needs),
                },
            )
        return DecisionResult(
            False, "REQUEST_ASSISTED_EVACUATION",
            (REASON_NO_FEASIBLE_SAFE_ROUTE,), {"official": True},
        )

    physical = block.get("physical_safety", UNKNOWN)

    if sustain.state == SUSTAINABLE:
        if forward_state in {"WATCH", "HIGH", "CRITICAL", "ACTIVE"}:
            state = "STAY_AND_PREPARE"
            if forward_block.get("mobility_window_closing") is True:
                state = "STAY_AND_PREPARE_WINDOW_CLOSING"
            return DecisionResult(
                True,
                state,
                sustain.reason_codes,
                {
                    "escalation_state": sustain.escalation_state,
                    "current_state": "SUSTAINABLE",
                    "forward_hazard": forward_state,
                    "mobility_window_closing": forward_block.get("mobility_window_closing", UNKNOWN),
                },
            )
        return DecisionResult(
            True, "STAY_AND_SUSTAIN", sustain.reason_codes,
            {"escalation_state": sustain.escalation_state, "forward_hazard": forward_state},
        )

    if sustain.state == NOT_SUSTAINABLE and physical == UNSAFE:
        route = cd.find_safe_route(
            doc, household_id, group_size=group_size, mode=mode, needs=animal_needs
        )
        if route.found and animal_transport_ready:
            _, animal_target = _household_animal_route_context(doc, node, route.target)
            if animal_target is None or animal_target.admitted:
                return DecisionResult(
                    True,
                    "PREPARE_TO_MOVE",
                    sustain.reason_codes,
                    {
                        "route": list(route.path),
                        "target": route.target,
                        "cause": "PHYSICAL_UNSAFE",
                        "animal_route_needs": list(animal_needs),
                    },
                )
        if animal_needs:
            return DecisionResult(
                False,
                "REQUEST_ASSISTED_EVACUATION_WITH_ANIMALS",
                (REASON_NO_FEASIBLE_SAFE_ROUTE,) + sustain.reason_codes,
                {
                    "cause": "PHYSICAL_UNSAFE",
                    "animal_transport_ready": animal_transport_ready,
                    "animal_movement_state": (
                        None if animal_movement is None else animal_movement.state
                    ),
                    "animal_route_needs": list(animal_needs),
                },
            )
        return DecisionResult(
            False, "REQUEST_ASSISTED_EVACUATION",
            (REASON_NO_FEASIBLE_SAFE_ROUTE,) + sustain.reason_codes,
            {"cause": "PHYSICAL_UNSAFE"},
        )

    if sustain.state == NOT_SUSTAINABLE and physical == SAFE:
        # Resource/service deficit: move the missing function first, not the person.
        providers = block.get("support_providers") or []
        path_only: list[dict[str, Any]] = []
        for provider_id in providers:
            delivery = evaluate_support_delivery(
                doc, household_id, provider_id, sustain.gaps, planning_horizon_h
            )
            if delivery.admitted:
                return DecisionResult(
                    True, "REQUEST_OR_RECEIVE_SUPPORT_DELIVERY", (),
                    delivery.details | {"forward_hazard": forward_state},
                )
            if delivery.state == "SUPPORT_DELIVERY_PATH_ONLY":
                path_only.append(delivery.details)

        rs = evaluate_resupply_window(
            doc, household_id, planning_horizon_h, mode=mode, group_size=group_size
        )
        if rs.admitted:
            details = dict(rs.details)
            details["forward_hazard"] = forward_state
            details["mobility_window_closing"] = forward_block.get("mobility_window_closing", UNKNOWN)
            return DecisionResult(True, rs.state, rs.reason_codes, details)

        if path_only:
            return DecisionResult(
                False,
                "VERIFY_SUPPORT_CAPACITY_OR_TIMING",
                (REASON_SUPPORT_CAPACITY_UNKNOWN, REASON_SUPPORT_ARRIVAL_UNKNOWN),
                {"candidate_support": path_only, "forward_hazard": forward_state},
            )

        return DecisionResult(
            False,
            "REQUEST_LOGISTICS_OR_REASSESS_MOVEMENT",
            sustain.reason_codes,
            {
                "cause": "RESOURCE_OR_SERVICE_DEFICIT",
                "forward_hazard": forward_state,
                "note": "resource deficit alone does not justify evacuation",
            },
        )

    # Current state unresolved. Forward hazard may justify preparation, never a fabricated
    # evacuation decision.
    if forward_state in {"WATCH", "HIGH", "CRITICAL", "ACTIVE"}:
        return DecisionResult(
            False,
            "VERIFY_AND_PREPARE",
            _dedup(sustain.reason_codes + forward_reasons),
            {
                "unknown_fields": list(sustain.unknown_fields),
                "forward_hazard": forward_state,
            },
        )

    return DecisionResult(
        False,
        "VERIFY_BEFORE_ACTION",
        _dedup(sustain.reason_codes + forward_reasons),
        {"unknown_fields": list(sustain.unknown_fields), "forward_hazard": forward_state},
    )
