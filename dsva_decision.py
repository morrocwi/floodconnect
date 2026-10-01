#!/usr/bin/env python3
"""Finite reference implementation of the DSVA v0.7 disaster decision model.

This is an executable projection of DSVA, not a hazard forecaster and not a
replacement ontology. It licenses candidate actions only inside an explicit
scenario envelope and finite set of admitted worlds/disturbances.

Run:
    python3 dsva_decision.py examples/dsva_decision_minimal.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

STATUS_LICENSED = "LICENSED_WITHIN_ENVELOPE"
STATUS_CONDITIONAL = "CONDITIONAL"
STATUS_LOCAL = "LOCAL/PARTIAL"
STATUS_UNRESOLVED = "UNRESOLVED"
STATUS_CONTRADICTION = "CONTRADICTION"
STATUS_INVALIDATED = "INVALIDATED"
STATUS_HOLD = "HOLD"

FIRST_ORDER = (
    "information", "evidence", "state", "transition",
    "boundary", "capacity", "recovery",
)
SECOND_ORDER = (
    "applicability", "dependency", "realizability",
    "execution", "requirement", "verification",
)


def _dig(obj: Mapping[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            raise KeyError(path)
        cur = cur[part]
    return cur


def _requirement_holds(state: Mapping[str, Any], req: Mapping[str, Any]) -> bool:
    try:
        actual = _dig(state, str(req["field"]))
    except KeyError:
        return False
    op = req.get("op", "eq")
    expected = req.get("value")
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "ge":
        return actual >= expected
    if op == "gt":
        return actual > expected
    if op == "le":
        return actual <= expected
    if op == "lt":
        return actual < expected
    if op == "in":
        return actual in expected
    if op == "not_in":
        return actual not in expected
    if op == "truthy":
        return bool(actual)
    if op == "falsy":
        return not bool(actual)
    raise ValueError(f"unsupported requirement operator: {op}")


def _trace_safe(
    trace: Sequence[Mapping[str, Any]],
    requirements: Sequence[Mapping[str, Any]],
) -> Tuple[bool, str | None]:
    if not trace:
        return False, "EMPTY_TRACE"
    for i, state in enumerate(trace):
        for req in requirements:
            if not _requirement_holds(state, req):
                rid = req.get("id", req.get("field"))
                return False, f"TRACE_REQUIREMENT_FAIL:{rid}:step={i}"
    return True, None


def _actor_info_ok(
    action: Mapping[str, Any],
    actor_information: Mapping[str, Any],
) -> Tuple[bool, str | None]:
    actor = action.get("actor")
    needed = set(action.get("requires_info", []))
    if not needed:
        return True, None
    if not actor:
        return False, "ACTOR_NOT_DECLARED"
    known = set(actor_information.get(actor, {}).get("known", []))
    missing = sorted(needed - known)
    if missing:
        return False, "ACTOR_LOCAL_INFO_MISSING:" + ",".join(missing)
    return True, None


def _lease_ok(action: Mapping[str, Any]) -> Tuple[bool, str | None]:
    lease = action.get("lease", {})
    try:
        issue = float(lease["issue"])
        expire = float(lease["expire"])
        effect = float(action.get("effect_time", issue))
    except (KeyError, TypeError, ValueError):
        return False, "LEASE_UNRESOLVED"
    if issue <= effect <= expire:
        return True, None
    return False, "LEASE_EXPIRED_BEFORE_EFFECT"


def _action_check(
    action: Mapping[str, Any],
    worlds: Sequence[str],
    disturbances: Sequence[str],
    requirements: Sequence[Mapping[str, Any]],
    actor_information: Mapping[str, Any],
) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    ok, reason = _lease_ok(action)
    if not ok and reason:
        reasons.append(reason)

    ok, reason = _actor_info_ok(action, actor_information)
    if not ok and reason:
        reasons.append(reason)

    outcomes = action.get("outcomes", {})
    for world in worlds:
        world_out = outcomes.get(world)
        if world_out is None:
            reasons.append(f"MISSING_OUTCOME:{world}")
            continue
        for disturbance in disturbances:
            item = world_out.get(disturbance)
            if item is None:
                reasons.append(f"MISSING_OUTCOME:{world}:{disturbance}")
                continue
            trace = item.get("trace") if isinstance(item, Mapping) else None
            if not isinstance(trace, list):
                reasons.append(f"MISSING_TRACE:{world}:{disturbance}")
                continue
            safe, why = _trace_safe(trace, requirements)
            if not safe and why:
                reasons.append(f"{world}:{disturbance}:{why}")

    return (not reasons), reasons


def _closure_gate(scenario: Mapping[str, Any]) -> Tuple[str | None, List[str]]:
    info_status = scenario.get("information_status", "SUPPORTED")
    if info_status == "CONTRADICTION":
        return STATUS_CONTRADICTION, ["INFORMATION_CONTRADICTION"]
    if scenario.get("model_invalidated", False):
        return STATUS_INVALIDATED, ["MODEL_INVALIDATED"]

    closures = scenario.get("closures", {})
    fo = closures.get("first_order", {})
    so = closures.get("second_order", {})

    missing_fo = [k for k in FIRST_ORDER if fo.get(k) is not True]
    if missing_fo:
        if missing_fo == ["boundary"]:
            return STATUS_LOCAL, ["FIRST_ORDER_BOUNDARY_OPEN"]
        if "information" in missing_fo and info_status == "UNRESOLVED":
            return STATUS_UNRESOLVED, ["INFORMATION_UNRESOLVED"]
        return STATUS_HOLD, ["FIRST_ORDER_OPEN:" + ",".join(missing_fo)]

    missing_so = [k for k in SECOND_ORDER if so.get(k) is not True]
    if missing_so:
        if missing_so == ["requirement"]:
            return STATUS_LOCAL, ["PROTECTED_REQUIREMENT_OPEN"]
        return STATUS_HOLD, ["SECOND_ORDER_OPEN:" + ",".join(missing_so)]

    return None, []


def evaluate(scenario: Mapping[str, Any]) -> Dict[str, Any]:
    question = scenario.get("question", {})
    envelope = scenario.get("envelope", {})
    worlds = [
        str(w["id"] if isinstance(w, Mapping) else w)
        for w in scenario.get("worlds", [])
    ]
    disturbances = [str(d) for d in scenario.get("disturbances", ["base"])]
    requirements = list(scenario.get("requirements", []))
    actor_information = scenario.get("actor_information", {})
    actions = list(scenario.get("actions", []))

    base = {
        "question_id": question.get("id"),
        "task": question.get("task"),
        "horizon": question.get("horizon"),
        "envelope": envelope,
        "assumptions": scenario.get("assumptions", []),
        "valid_until": scenario.get("valid_until"),
        "provenance": scenario.get("provenance", []),
    }

    gate_status, gate_reasons = _closure_gate(scenario)
    if gate_status:
        return {
            **base,
            "status": gate_status,
            "selected_action": None,
            "viable_actions": [],
            "rejected_actions": {},
            "reasons": gate_reasons,
        }

    if not worlds:
        return {
            **base, "status": STATUS_HOLD, "selected_action": None,
            "viable_actions": [], "rejected_actions": {},
            "reasons": ["NO_ADMISSIBLE_WORLDS_DECLARED"],
        }
    if not requirements:
        return {
            **base, "status": STATUS_HOLD, "selected_action": None,
            "viable_actions": [], "rejected_actions": {},
            "reasons": ["NO_PROTECTED_REQUIREMENTS"],
        }
    if not actions:
        return {
            **base, "status": STATUS_HOLD, "selected_action": None,
            "viable_actions": [], "rejected_actions": {},
            "reasons": ["NO_CANDIDATE_ACTIONS"],
        }

    viable: List[str] = []
    rejected: Dict[str, List[str]] = {}
    for action in actions:
        aid = str(action.get("id", ""))
        if not aid:
            continue
        ok, reasons = _action_check(
            action, worlds, disturbances, requirements, actor_information
        )
        if ok:
            viable.append(aid)
        else:
            rejected[aid] = reasons

    typed_reader = scenario.get("typed_reader", {})
    proposed = scenario.get("proposed_action") or typed_reader.get("selected")

    if proposed:
        proposed = str(proposed)
        if proposed in viable:
            return {
                **base,
                "status": STATUS_LICENSED,
                "selected_action": proposed,
                "viable_actions": viable,
                "rejected_actions": rejected,
                "reasons": [
                    "PROPOSED_ACTION_VERIFIED_WITHIN_DECLARED_ENVELOPE"
                ],
                "typed_reader": typed_reader or None,
            }
        return {
            **base,
            "status": STATUS_HOLD,
            "selected_action": None,
            "viable_actions": viable,
            "rejected_actions": rejected,
            "reasons": ["PROPOSED_ACTION_NOT_LICENSED"]
            + rejected.get(proposed, ["PROPOSED_ACTION_UNKNOWN"]),
            "typed_reader": typed_reader or None,
        }

    if len(viable) == 1:
        return {
            **base,
            "status": STATUS_LICENSED,
            "selected_action": viable[0],
            "viable_actions": viable,
            "rejected_actions": rejected,
            "reasons": ["UNIQUE_VERIFIED_ACTION_WITHIN_DECLARED_ENVELOPE"],
        }
    if len(viable) > 1:
        return {
            **base,
            "status": STATUS_UNRESOLVED,
            "selected_action": None,
            "viable_actions": viable,
            "rejected_actions": rejected,
            "reasons": ["MULTIPLE_VIABLE_ACTIONS_READER_REQUIRED"],
        }
    return {
        **base,
        "status": STATUS_HOLD,
        "selected_action": None,
        "viable_actions": [],
        "rejected_actions": rejected,
        "reasons": ["NO_VIABLE_ACTION_WITHIN_DECLARED_ENVELOPE"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a finite DSVA v0.7 decision scenario"
    )
    parser.add_argument("scenario", type=Path, help="Path to scenario JSON")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    args = parser.parse_args(argv)

    with args.scenario.open("r", encoding="utf-8") as f:
        scenario = json.load(f)
    result = evaluate(scenario)
    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
