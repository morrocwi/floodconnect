#!/usr/bin/env python3
"""
Unified FloodConnect crisis-state readout.

This module does not create a new risk score. It projects existing FloodConnect evaluators
into one orthogonal state vector:

    Z_i(t,T) = (O, F, M, S, E, H, A, P)

O = occupancy safety
F = essential-function state
M = movement state
S = lowest viable support layer
E = environmental degradation state
H = forward-hazard state
A = human-animal topology
P = operational phase

Operational response patterns are then derived from the existing decision operator.
Patterns are not mutually exclusive disaster "types"; they are action/readout categories.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import community_dag as cd
import environmental_degradation as envd
import human_animal_household as hahu
import shelter_decision as sd

UNKNOWN = "UNKNOWN"

OCCUPANCY_STATES = {"SAFE", "DEGRADING", "UNSAFE", UNKNOWN}
FUNCTION_STATES = {"INTACT", "GAP_CLOSABLE", "GAP_UNCLOSABLE", UNKNOWN}
MOVEMENT_STATES = {"SELF_MOVE", "ASSISTED_ROUTE", "ASSISTED_REQUIRED", "UNVERIFIED", UNKNOWN}
SUPPORT_STATES = {"L0_HOUSEHOLD", "L1_BUDDY", "L2_ZONE", "L3_COMMUNITY", "L4_EXTERNAL", "NO_VIABLE", UNKNOWN}
PHASES = {"PREPARE", "RESPONSE", "SHELTER", "RECOVERY", UNKNOWN}

ACTION_PATTERN_MAP = {
    "STAY_AND_SUSTAIN": "STAY_SUSTAIN",
    "STAY_AND_PREPARE": "STAY_PREPARE",
    "STAY_AND_PREPARE_WINDOW_CLOSING": "STAY_PREPARE_WINDOW_CLOSING",
    "RESUPPLY_WINDOW": "RESUPPLY",
    "REQUEST_OR_RECEIVE_SUPPORT_DELIVERY": "DELIVER_INWARD",
    "VERIFY_SUPPORT_CAPACITY_OR_TIMING": "ESCALATE_SUPPORT",
    "REQUEST_LOGISTICS_OR_REASSESS_MOVEMENT": "ESCALATE_SUPPORT",
    "PREPARE_TO_MOVE": "MOVE",
    "EVACUATE_ROUTE": "MOVE",
    "REQUEST_ASSISTED_EVACUATION": "ASSISTED_EVACUATION",
    "REQUEST_ASSISTED_EVACUATION_WITH_ANIMALS": "ASSISTED_EVACUATION",
    "VERIFY_AND_PREPARE": "VERIFY_PREPARE",
    "VERIFY_BEFORE_ACTION": "VERIFY",
}


@dataclass(frozen=True)
class CrisisState:
    occupancy: str
    function: str
    movement: str
    support: str
    environment: str
    forward_hazard: str
    animal_topology: str
    phase: str
    action_state: str
    action_pattern: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "O_occupancy": self.occupancy,
            "F_function": self.function,
            "M_movement": self.movement,
            "S_support": self.support,
            "E_environment": self.environment,
            "H_forward_hazard": self.forward_hazard,
            "A_animal_topology": self.animal_topology,
            "P_phase": self.phase,
            "action_state": self.action_state,
            "action_pattern": self.action_pattern,
            "details": dict(self.details),
        }


def _occupancy_state(node: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    sustain = node.get("sustainment") or {}
    physical = sustain.get("physical_safety", UNKNOWN)

    env_state = UNKNOWN
    env_details: dict[str, Any] = {}
    if isinstance(node.get("environment"), dict):
        env = envd.evaluate_environmental_degradation(node)
        env_state = env.state
        env_details = env.as_dict()

    if physical == sd.UNSAFE or env_state == envd.UNSAFE:
        return "UNSAFE", {"physical": physical, "environment": env_state, "environment_details": env_details}
    if physical != sd.SAFE:
        return UNKNOWN, {"physical": physical, "environment": env_state, "environment_details": env_details}
    if env_state == envd.DEGRADING:
        return "DEGRADING", {"physical": physical, "environment": env_state, "environment_details": env_details}
    if env_state == envd.UNKNOWN and isinstance(node.get("environment"), dict):
        return UNKNOWN, {"physical": physical, "environment": env_state, "environment_details": env_details}
    return "SAFE", {"physical": physical, "environment": env_state, "environment_details": env_details}


def _animal_topology_label(node: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    profile = node.get("animal_profile")
    if not isinstance(profile, dict) or hahu.declared_animal_count(profile) <= 0:
        return "HUMAN_ONLY", {}
    topo = hahu.classify_animal_topology(profile)
    present = []
    if topo["assistance_animal_count"] > 0:
        present.append("ASSISTANCE")
    companion_non_assistance = max(0, topo["companion_count"] - topo["assistance_animal_count"])
    if companion_non_assistance > 0:
        present.append("COMPANION")
    if topo["livestock_count"] > 0:
        present.append("LIVESTOCK")
    if topo["community_count"] > 0:
        present.append("COMMUNITY")
    if not present:
        return "ANIMAL_TOPOLOGY_UNKNOWN", topo
    return (present[0] if len(present) == 1 else "MIXED"), topo


def _support_state(
    doc: dict[str, Any],
    household_id: str,
    planning_horizon_h: Optional[float],
    *,
    group_size: int,
    mode: str,
) -> tuple[str, dict[str, Any]]:
    result = sd.find_lowest_viable_node(
        doc, household_id, planning_horizon_h, group_size=group_size, mode=mode
    )
    if result.state == sd.NO_VIABLE_NODE:
        if result.lower_unresolved:
            return UNKNOWN, result.as_dict()
        return "NO_VIABLE", result.as_dict()

    mapping = {
        "household": "L0_HOUSEHOLD",
        "buddy_cell": "L1_BUDDY",
        "zone": "L2_ZONE",
        "internal_safe": "L3_COMMUNITY",
        "external_safe": "L4_EXTERNAL",
    }
    return mapping.get(result.node_kind, UNKNOWN), result.as_dict()


def _function_state(
    doc: dict[str, Any],
    household_id: str,
    planning_horizon_h: Optional[float],
    *,
    group_size: int,
    mode: str,
) -> tuple[str, dict[str, Any]]:
    nodes = doc.get("nodes") or {}
    node = nodes.get(household_id)
    if not isinstance(node, dict):
        return UNKNOWN, {}

    sustain = sd.evaluate_sustainment(node, planning_horizon_h)
    nonphysical_gaps = tuple(g for g in sustain.gaps if g != "physical_safety")
    if sustain.state == sd.UNKNOWN:
        return UNKNOWN, sustain.as_dict()
    if not nonphysical_gaps:
        return "INTACT", sustain.as_dict()

    block = node.get("sustainment") or {}
    for provider_id in block.get("support_providers") or []:
        delivery = sd.evaluate_support_delivery(
            doc, household_id, provider_id, nonphysical_gaps, planning_horizon_h
        )
        if delivery.admitted:
            return "GAP_CLOSABLE", {
                "sustainment": sustain.as_dict(),
                "closure": delivery.as_dict(),
            }

    rs = sd.evaluate_resupply_window(
        doc, household_id, planning_horizon_h, group_size=group_size, mode=mode
    )
    if rs.admitted:
        return "GAP_CLOSABLE", {
            "sustainment": sustain.as_dict(),
            "closure": rs.as_dict(),
        }

    return "GAP_UNCLOSABLE", sustain.as_dict()


def _movement_state(
    doc: dict[str, Any],
    household_id: str,
    *,
    group_size: int,
    mode: str,
) -> tuple[str, dict[str, Any]]:
    nodes = doc.get("nodes") or {}
    node = nodes.get(household_id)
    if not isinstance(node, dict):
        return UNKNOWN, {}

    profile = node.get("animal_profile")
    route_needs = ()
    movement = None
    if isinstance(profile, dict) and hahu.declared_animal_count(profile) > 0:
        route_needs = hahu.movement_route_service_needs(profile)
        movement = hahu.evaluate_animal_movement_readiness(profile)
        if movement.state == hahu.NOT_READY:
            return "ASSISTED_REQUIRED", movement.as_dict()
        if movement.state == hahu.UNKNOWN:
            return "UNVERIFIED", movement.as_dict()

    route = cd.find_safe_route(
        doc, household_id, group_size=group_size, mode=mode, needs=route_needs
    )
    if not route.found:
        return "UNVERIFIED", {"route_reason": route.reason}

    if isinstance(profile, dict) and hahu.declared_animal_count(profile) > 0:
        target = nodes.get(route.target)
        if not isinstance(target, dict):
            return "UNVERIFIED", {"route": route.as_dict()}
        destination = hahu.screen_animal_destination(target, profile, doc=doc)
        if destination.state == hahu.NOT_SUSTAINABLE:
            return "ASSISTED_REQUIRED", {
                "route": route.as_dict(),
                "animal_destination": destination.as_dict(),
            }
        if destination.state == hahu.UNKNOWN:
            return "UNVERIFIED", {
                "route": route.as_dict(),
                "animal_destination": destination.as_dict(),
            }

    assisted_edges = None
    if route.score is not None and len(route.score) > 0:
        assisted_edges = route.score[0]
    state = "ASSISTED_ROUTE" if assisted_edges and assisted_edges > 0 else "SELF_MOVE"
    return state, {"route": route.as_dict()}


def derive_shelter_response_pattern(
    node: dict[str, Any],
    *,
    phase: str = "OCCUPIED",
    group_size: int = 1,
) -> dict[str, Any]:
    """Derive shelter lifecycle response pattern from the existing shelter screener."""
    phase_u = str(phase).upper()
    screen = sd.screen_shelter_candidate(node, phase=phase_u, group_size=group_size)

    if screen.state == "SHELTER_UNRESOLVED":
        return {
            "pattern": "VERIFY",
            "screen": screen.as_dict(),
            "phase": phase_u,
        }

    if not screen.admitted:
        return {
            "pattern": "SHELTER_INTERVENTION_RELOCATION",
            "screen": screen.as_dict(),
            "phase": phase_u,
        }

    if phase_u == "RECOVERY":
        return {
            "pattern": "RECOVERY_RETURN",
            "screen": screen.as_dict(),
            "phase": phase_u,
        }

    return {
        "pattern": "SHELTER_OPERATION",
        "screen": screen.as_dict(),
        "phase": phase_u,
    }


def derive_crisis_state(
    doc: dict[str, Any],
    household_id: str,
    planning_horizon_h: Optional[float],
    *,
    group_size: int = 1,
    mode: str = "walk",
    phase: Optional[str] = None,
    forward_hazard: Optional[dict[str, Any]] = None,
) -> CrisisState:
    nodes = doc.get("nodes") or {}
    node = nodes.get(household_id)
    if not isinstance(node, dict):
        return CrisisState(
            UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN,
            UNKNOWN, "UNKNOWN", "VERIFY", {"reason": "UNKNOWN_HOUSEHOLD"}
        )

    occupancy, occupancy_details = _occupancy_state(node)
    function, function_details = _function_state(
        doc, household_id, planning_horizon_h, group_size=group_size, mode=mode
    )
    movement, movement_details = _movement_state(
        doc, household_id, group_size=group_size, mode=mode
    )
    support, support_details = _support_state(
        doc, household_id, planning_horizon_h, group_size=group_size, mode=mode
    )

    environment = UNKNOWN
    if isinstance(node.get("environment"), dict):
        environment = envd.evaluate_environmental_degradation(node).state

    forward_state, forward_details, _ = sd._forward_hazard_state(
        node, planning_horizon_h, forward_hazard
    )
    animal_topology, animal_details = _animal_topology_label(node)

    declared_phase = str(phase or node.get("crisis_phase") or UNKNOWN).upper()
    if declared_phase not in PHASES:
        declared_phase = UNKNOWN

    action = sd.recommend_protective_state(
        doc,
        household_id,
        planning_horizon_h,
        group_size=group_size,
        mode=mode,
        forward_hazard=forward_hazard,
    )
    pattern = ACTION_PATTERN_MAP.get(action.state, "VERIFY")

    return CrisisState(
        occupancy=occupancy,
        function=function,
        movement=movement,
        support=support,
        environment=environment,
        forward_hazard=forward_state,
        animal_topology=animal_topology,
        phase=declared_phase,
        action_state=action.state,
        action_pattern=pattern,
        details={
            "occupancy": occupancy_details,
            "function": function_details,
            "movement": movement_details,
            "support": support_details,
            "forward_hazard": forward_details,
            "animal": animal_details,
            "action": action.as_dict(),
            "note": "orthogonal state vector; no weighted composite risk score",
        },
    )
