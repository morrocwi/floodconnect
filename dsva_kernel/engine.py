"""DSVA v0.11 finite retained obstruction + finite realizability evaluator."""
from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction
from typing import Any, Dict, Mapping, Sequence

from .core import (
    FIRST_ORDER,
    SECOND_ORDER,
    SUPPORTED_INFO_STATUS,
    SUPPORTED_REQ_OPS,
    SUPPORTED_TRACE_SEMANTICS,
    STATUS_CONTRADICTION,
    STATUS_HOLD,
    STATUS_INVALIDATED,
    STATUS_LICENSED,
    STATUS_LOCAL,
    STATUS_UNRESOLVED,
    CostLedger,
    Obstruction,
    as_str_set,
    q,
)
from .contracts import (
    adaptive_policy_obstruction,
    applicability_check,
    boundary_contract_obstruction,
    dependency_check,
    execution_obstruction,
    future_observation_obstruction,
    hazard_dependency_check,
    recovery_trace_obstruction,
    requirement_ledger_check,
    resource_obstruction,
    verification_binding,
)
from .requirements import requirement_bindings, requirement_population, state_safe


def trace_times(
    trace: Sequence[Mapping[str, Any]],
    horizon: Fraction,
    resolution: Fraction,
    ledger: CostLedger,
) -> tuple[list[Fraction], str | None]:
    if not trace:
        return [], "EMPTY_TRACE"
    explicit = ["t" in s for s in trace]
    if any(explicit) and not all(explicit):
        return [], "MIXED_EXPLICIT_IMPLICIT_TRACE_TIME"
    try:
        if all(explicit):
            ts = [q(s["t"], ledger=ledger) for s in trace]
        else:
            ts = [Fraction(i, 1) * resolution for i in range(len(trace))]
    except Exception as exc:
        return [], f"TRACE_TIME_INVALID:{type(exc).__name__}"
    if ts[0] != 0:
        return [], "TRACE_MUST_START_AT_ZERO"
    if any(ts[i] >= ts[i + 1] for i in range(len(ts) - 1)):
        return [], "TRACE_TIME_NOT_STRICTLY_INCREASING"
    if any((t / resolution).denominator != 1 for t in ts):
        return [], "TRACE_TIME_OFF_DECLARED_RESOLUTION"
    if ts[-1] != horizon:
        return [], f"TRACE_HORIZON_MISMATCH:last={ts[-1]}:H={horizon}"
    return ts, None


def closure_audit(
    s: Mapping[str, Any],
) -> tuple[str | None, dict | None]:
    """Check audit-witness completeness for every asserted closure.

    This is an auditability contract, not a proof that an external checker is
    semantically correct. It prevents a bare caller-written True from being
    indistinguishable from a traced closure result.
    """
    audit = s.get("closure_audit")
    if not isinstance(audit, Mapping):
        return "CLOSURE_AUDIT_MISSING", None
    closures = s.get("closures", {})
    for layer, names in (("first_order", FIRST_ORDER), ("second_order", SECOND_ORDER)):
        layer_audit = audit.get(layer)
        layer_values = closures.get(layer) if isinstance(closures, Mapping) else None
        if not isinstance(layer_audit, Mapping) or not isinstance(layer_values, Mapping):
            return f"CLOSURE_AUDIT_LAYER_INVALID:{layer}", None
        for name in names:
            if layer_values.get(name) is not True:
                continue
            cert = layer_audit.get(name)
            if not isinstance(cert, Mapping):
                return f"CLOSURE_AUDIT_CERT_MISSING:{layer}:{name}", None
            for key in ("spec", "input", "witness", "checker"):
                if key not in cert or cert.get(key) is None or cert.get(key) == "":
                    return f"CLOSURE_AUDIT_FIELD_MISSING:{layer}:{name}:{key}", None
            checker = cert.get("checker")
            spec = cert.get("spec")
            if not isinstance(checker, str) or not checker.strip():
                return f"CLOSURE_AUDIT_CHECKER_INVALID:{layer}:{name}", None
            if not isinstance(spec, str) or not spec.strip():
                return f"CLOSURE_AUDIT_SPEC_INVALID:{layer}:{name}", None
    try:
        payload = json.dumps(audit, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    except Exception as exc:
        return f"CLOSURE_AUDIT_DIGEST_ERROR:{type(exc).__name__}", None
    return None, {"digest": digest, "audit": audit}


def preflight(
    s: Mapping[str, Any],
    ledger: CostLedger,
) -> tuple[str | None, list[Obstruction], dict]:
    ctx: dict[str, Any] = {"scenario": s}
    obs: list[Obstruction] = []
    if not isinstance(s, Mapping):
        return STATUS_HOLD, [Obstruction("SCENARIO_NOT_MAPPING")], ctx
    question, env, closures = s.get("question"), s.get("envelope"), s.get("closures")
    if not isinstance(question, Mapping):
        obs.append(Obstruction("QUESTION_NOT_MAPPING"))
    if not isinstance(env, Mapping):
        obs.append(Obstruction("ENVELOPE_NOT_MAPPING"))
    if not isinstance(closures, Mapping):
        obs.append(Obstruction("CLOSURES_NOT_MAPPING"))
    if obs:
        return STATUS_HOLD, obs, ctx

    info = s.get("information_status", "UNRESOLVED")
    if info not in SUPPORTED_INFO_STATUS:
        return STATUS_HOLD, [Obstruction("INFORMATION_STATUS_UNKNOWN", str(info))], ctx
    if info == "CONTRADICTION":
        return STATUS_CONTRADICTION, [Obstruction("INFORMATION_CONTRADICTION")], ctx
    if info == "UNRESOLVED":
        return STATUS_UNRESOLVED, [Obstruction("INFORMATION_UNRESOLVED")], ctx

    invalidated = s.get("model_invalidated", False)
    if not isinstance(invalidated, bool):
        return STATUS_HOLD, [Obstruction("MODEL_INVALIDATED_FLAG_INVALID", repr(invalidated))], ctx
    if invalidated:
        return STATUS_INVALIDATED, [Obstruction("MODEL_INVALIDATED")], ctx

    try:
        H = q(question.get("horizon"), ledger=ledger)
        valid_until = q(s.get("valid_until"), ledger=ledger)
        if H < 0 or valid_until < 0:
            raise ValueError("negative decision time")
    except Exception as exc:
        return STATUS_HOLD, [Obstruction("TIME_COORDINATE_INVALID", type(exc).__name__)], ctx
    ctx["H"], ctx["valid_until"] = H, valid_until

    semantics = env.get("trace_semantics")
    if semantics not in SUPPORTED_TRACE_SEMANTICS:
        return STATUS_HOLD, [Obstruction("TRACE_SEMANTICS_UNSUPPORTED", str(semantics))], ctx
    try:
        resolution = q(env.get("trace_resolution"), ledger=ledger)
        if resolution <= 0:
            raise ValueError("trace_resolution must be positive")
        if (H / resolution).denominator != 1:
            return STATUS_HOLD, [Obstruction(
                "HORIZON_OFF_DECLARED_RESOLUTION", f"H={H},lambda={resolution}"
            )], ctx
    except Exception as exc:
        return STATUS_HOLD, [Obstruction("TRACE_RESOLUTION_INVALID", str(exc))], ctx
    ctx["trace_semantics"], ctx["trace_resolution"] = semantics, resolution

    fo, so = closures.get("first_order"), closures.get("second_order")
    if not isinstance(fo, Mapping) or not isinstance(so, Mapping):
        return STATUS_HOLD, [Obstruction("CLOSURE_MAP_INVALID")], ctx
    missing_fo = [k for k in FIRST_ORDER if fo.get(k) is not True]
    if missing_fo:
        if missing_fo == ["boundary"]:
            return STATUS_LOCAL, [Obstruction("FIRST_ORDER_BOUNDARY_OPEN")], ctx
        return STATUS_HOLD, [Obstruction("FIRST_ORDER_OPEN", ",".join(missing_fo))], ctx
    missing_so = [k for k in SECOND_ORDER if so.get(k) is not True]
    if missing_so:
        if missing_so == ["requirement"]:
            return STATUS_LOCAL, [Obstruction("PROTECTED_REQUIREMENT_OPEN")], ctx
        return STATUS_HOLD, [Obstruction("SECOND_ORDER_OPEN", ",".join(missing_so))], ctx

    audit_error, audit_info = closure_audit(s)
    if audit_error:
        return STATUS_HOLD, [Obstruction(audit_error)], ctx
    ctx["closure_audit_digest"] = audit_info["digest"]

    try:
        declared_dist = as_str_set(env.get("disturbance_envelope"), name="disturbance_envelope")
        actual_dist = as_str_set(s.get("disturbances"), name="disturbances")
        if declared_dist != actual_dist:
            return STATUS_HOLD, [Obstruction(
                "DISTURBANCE_ENVELOPE_MISMATCH",
                f"declared={sorted(declared_dist)},actual={sorted(actual_dist)}",
            )], ctx
        ctx["disturbances"] = sorted(actual_dist)
        ctx["actuation"] = as_str_set(env.get("actuation_envelope"), name="actuation_envelope")
        ctx["observation_envelope"] = as_str_set(
            env.get("observation_envelope"), name="observation_envelope"
        )
        ctx["protected_population"] = as_str_set(
            env.get("protected_population"), name="protected_population"
        )
    except Exception as exc:
        return STATUS_HOLD, [Obstruction("ENVELOPE_INVALID", str(exc))], ctx

    worlds = s.get("worlds")
    if not isinstance(worlds, list) or not worlds:
        return STATUS_HOLD, [Obstruction("NO_ADMISSIBLE_WORLDS_DECLARED")], ctx
    world_ids: list[str] = []
    for w in worlds:
        wid = w.get("id") if isinstance(w, Mapping) else w
        if not isinstance(wid, str) or not wid:
            return STATUS_HOLD, [Obstruction("WORLD_ID_INVALID")], ctx
        world_ids.append(wid)
    if len(set(world_ids)) != len(world_ids):
        return STATUS_HOLD, [Obstruction("WORLD_ID_DUPLICATE")], ctx
    ctx["worlds"] = world_ids

    reqs = s.get("requirements")
    if not isinstance(reqs, list) or not reqs:
        return STATUS_HOLD, [Obstruction("NO_PROTECTED_REQUIREMENTS")], ctx
    rids: list[str] = []
    covered: set[str] = set()
    for req in reqs:
        if not isinstance(req, Mapping):
            return STATUS_HOLD, [Obstruction("REQUIREMENT_NOT_MAPPING")], ctx
        rid = req.get("id")
        if not isinstance(rid, str) or not rid:
            return STATUS_HOLD, [Obstruction("REQUIREMENT_ID_INVALID")], ctx
        rids.append(rid)
        if req.get("op", "eq") not in SUPPORTED_REQ_OPS:
            return STATUS_HOLD, [Obstruction(
                "REQUIREMENT_OPERATOR_UNSUPPORTED", f"{rid}:{req.get('op')}"
            )], ctx
        try:
            covered |= requirement_population(req)
            requirement_bindings(req)
        except Exception as exc:
            return STATUS_HOLD, [Obstruction(
                "REQUIREMENT_BINDING_INVALID", f"{rid}:{exc}"
            )], ctx
        ledger_error = requirement_ledger_check(req, H, ledger)
        if ledger_error:
            return STATUS_HOLD, [Obstruction(ledger_error)], ctx
    if len(set(rids)) != len(rids):
        return STATUS_HOLD, [Obstruction("REQUIREMENT_ID_DUPLICATE")], ctx
    gap = ctx["protected_population"] - covered
    if gap:
        return STATUS_LOCAL, [Obstruction(
            "PROTECTED_POPULATION_COVERAGE_GAP", ",".join(sorted(gap))
        )], ctx
    ctx["requirements"] = reqs

    actions = s.get("actions")
    if not isinstance(actions, list) or not actions:
        return STATUS_HOLD, [Obstruction("NO_CANDIDATE_ACTIONS")], ctx
    aids: list[str] = []
    for action in actions:
        if not isinstance(action, Mapping):
            return STATUS_HOLD, [Obstruction("ACTION_NOT_MAPPING")], ctx
        aid = action.get("id")
        if not isinstance(aid, str) or not aid:
            return STATUS_HOLD, [Obstruction("ACTION_ID_INVALID")], ctx
        aids.append(aid)
    if len(set(aids)) != len(aids):
        return STATUS_HOLD, [Obstruction("ACTION_ID_DUPLICATE")], ctx
    ctx["actions"] = actions

    actor_info = s.get("actor_information", {})
    if not isinstance(actor_info, Mapping):
        return STATUS_HOLD, [Obstruction("ACTOR_INFORMATION_INVALID")], ctx
    ctx["actor_information"] = actor_info

    trace_library = s.get("trace_library", {})
    if not isinstance(trace_library, Mapping):
        return STATUS_HOLD, [Obstruction("TRACE_LIBRARY_INVALID")], ctx
    for key, value in trace_library.items():
        if not isinstance(key, str) or not key or not isinstance(value, list) or not value:
            return STATUS_HOLD, [Obstruction("TRACE_LIBRARY_ENTRY_INVALID", str(key))], ctx
    ctx["trace_library"] = trace_library

    applicability_error, applicability_info = applicability_check(s, ledger)
    if applicability_error == "MODEL_FAMILY_INVALIDATED_BY_BEHAVIOR":
        return STATUS_INVALIDATED, [Obstruction(applicability_error)], ctx
    if applicability_error:
        return STATUS_HOLD, [Obstruction(applicability_error)], ctx
    ctx["applicability"] = applicability_info

    dependency_error, dependency_info = dependency_check(s, ledger)
    if dependency_error:
        return STATUS_HOLD, [Obstruction(dependency_error)], ctx
    ctx["dependency"] = dependency_info

    hazard_error, hazard_info = hazard_dependency_check(s, ledger)
    if hazard_error:
        return STATUS_HOLD, [Obstruction(hazard_error)], ctx
    ctx["hazard_dependency"] = hazard_info

    verification_error, verification_info = verification_binding(s, ledger)
    if verification_error:
        return STATUS_HOLD, [Obstruction(verification_error)], ctx
    ctx["verification_binding"] = verification_info

    return None, [], ctx


def action_obstruction(
    action: Mapping[str, Any],
    ctx: Mapping[str, Any],
    ledger: CostLedger,
    state_cache: dict,
    trace_cache: dict,
) -> Obstruction | None:
    ledger.actions_checked += 1
    aid = str(action["id"])
    scope = f"action:{aid}"
    if aid not in ctx["actuation"]:
        return Obstruction("ACTION_OUTSIDE_ACTUATION_ENVELOPE", aid, scope)

    future_error = future_observation_obstruction(
        action, ctx["observation_envelope"], ledger
    )
    if future_error:
        return Obstruction(future_error, scope=scope)

    policy_error = adaptive_policy_obstruction(
        ctx["scenario"],
        action,
        ctx["observation_envelope"],
        ctx["actuation"],
        ctx["actor_information"],
        ctx["H"],
        ledger,
    )
    if policy_error:
        return Obstruction(policy_error, scope=scope)

    boundary_error = boundary_contract_obstruction(
        ctx["scenario"],
        aid,
        ctx["worlds"],
        ctx["disturbances"],
        ctx["H"],
        ledger,
    )
    if boundary_error:
        return Obstruction(boundary_error, scope=scope)

    execution_error = execution_obstruction(action, ledger)
    if execution_error:
        return Obstruction(execution_error, scope=scope)

    resource_error = resource_obstruction(ctx["scenario"], aid, ledger)
    if resource_error:
        return Obstruction(resource_error, scope=scope)

    lease = action.get("lease")
    if not isinstance(lease, Mapping):
        return Obstruction("LEASE_UNRESOLVED", scope=scope)
    try:
        issue = q(lease.get("issue"), ledger=ledger)
        expire = q(lease.get("expire"), ledger=ledger)
        effect = q(action.get("effect_time", issue), ledger=ledger)
    except Exception as exc:
        return Obstruction("LEASE_UNRESOLVED", type(exc).__name__, scope)
    if not (issue <= effect <= expire):
        return Obstruction(
            "LEASE_EXPIRED_BEFORE_EFFECT",
            f"issue={issue},effect={effect},expire={expire}",
            scope,
        )
    if effect < 0:
        return Obstruction(
            "EFFECT_BEFORE_DECISION_ORIGIN",
            f"effect={effect}",
            scope,
        )
    if effect > ctx["H"]:
        return Obstruction("EFFECT_AFTER_HORIZON", f"effect={effect},H={ctx['H']}", scope)
    if effect > ctx["valid_until"]:
        return Obstruction(
            "EFFECT_AFTER_VALID_UNTIL",
            f"effect={effect},validUntil={ctx['valid_until']}",
            scope,
        )

    actor = action.get("actor")
    needed = action.get("requires_info", [])
    if not isinstance(actor, str) or not actor:
        return Obstruction("ACTOR_NOT_DECLARED", scope=scope)
    if not isinstance(needed, list) or any(not isinstance(x, str) or not x for x in needed):
        return Obstruction("ACTION_REQUIRES_INFO_INVALID", scope=scope)
    known_obj = ctx["actor_information"].get(actor)
    if not isinstance(known_obj, Mapping):
        return Obstruction("ACTOR_INFORMATION_MISSING", actor, scope)
    known = known_obj.get("known", [])
    if not isinstance(known, list) or any(not isinstance(x, str) for x in known):
        return Obstruction("ACTOR_INFORMATION_INVALID", actor, scope)
    missing = set(needed) - set(known)
    if missing:
        return Obstruction("ACTOR_LOCAL_INFO_MISSING", ",".join(sorted(missing)), scope)

    outcomes = action.get("outcomes")
    if not isinstance(outcomes, Mapping):
        return Obstruction("OUTCOMES_NOT_MAPPING", scope=scope)

    for world in ctx["worlds"]:
        world_out = outcomes.get(world)
        if not isinstance(world_out, Mapping):
            return Obstruction("MISSING_OR_INVALID_WORLD_OUTCOME", world, scope)
        for dist in ctx["disturbances"]:
            ledger.branches_checked += 1
            item = world_out.get(dist)
            if not isinstance(item, Mapping):
                return Obstruction("MISSING_OR_INVALID_BRANCH", f"{world}/{dist}", scope)

            has_trace, has_ref = "trace" in item, "trace_ref" in item
            if has_trace == has_ref:
                return Obstruction("TRACE_SOURCE_AMBIGUOUS_OR_MISSING", f"{world}/{dist}", scope)

            trace_key = None
            if has_ref:
                trace_key = item.get("trace_ref")
                if not isinstance(trace_key, str) or not trace_key:
                    return Obstruction("TRACE_REF_INVALID", f"{world}/{dist}", scope)
                trace = ctx["trace_library"].get(trace_key)
                if not isinstance(trace, list) or not trace:
                    return Obstruction("TRACE_REF_UNRESOLVED", trace_key, scope)
                if trace_key in trace_cache:
                    ledger.trace_cache_hits += 1
                    cached = trace_cache[trace_key]
                    if cached is not None:
                        return Obstruction(cached, f"{world}/{dist}/trace_ref={trace_key}", scope)
                    continue
            else:
                trace = item.get("trace")

            if not isinstance(trace, list) or not trace:
                return Obstruction("MISSING_OR_INVALID_TRACE", f"{world}/{dist}", scope)
            ledger.traces_checked += 1
            if any(not isinstance(st, Mapping) for st in trace):
                why = "TRACE_STATE_NOT_MAPPING"
                if trace_key is not None:
                    trace_cache[trace_key] = why
                return Obstruction(why, f"{world}/{dist}", scope)

            times, why = trace_times(trace, ctx["H"], ctx["trace_resolution"], ledger)
            if why:
                if trace_key is not None:
                    trace_cache[trace_key] = why
                return Obstruction(why, f"{world}/{dist}", scope)

            recovery_error = recovery_trace_obstruction(
                ctx["scenario"],
                trace,
                times,
                ctx["H"],
                ctx["trace_resolution"],
                ledger,
            )
            if recovery_error:
                if trace_key is not None:
                    trace_cache[trace_key] = recovery_error
                return Obstruction(recovery_error, f"{world}/{dist}", scope)

            for i, state in enumerate(trace):
                ok, why = state_safe(state, ctx["requirements"], state_cache, ledger)
                if not ok:
                    code = why or "TRACE_REQUIREMENT_FAIL"
                    if trace_key is not None:
                        trace_cache[trace_key] = code
                    return Obstruction(code, f"{world}/{dist}/step={i}", scope)
            if trace_key is not None:
                trace_cache[trace_key] = None
    return None


def evaluate(scenario: Mapping[str, Any]) -> Dict[str, Any]:
    ledger = CostLedger()
    question = scenario.get("question", {}) if isinstance(scenario, Mapping) else {}
    envelope = scenario.get("envelope", {}) if isinstance(scenario, Mapping) else {}
    base = {
        "question_id": question.get("id") if isinstance(question, Mapping) else None,
        "task": question.get("task") if isinstance(question, Mapping) else None,
        "horizon": question.get("horizon") if isinstance(question, Mapping) else None,
        "envelope": envelope if isinstance(envelope, Mapping) else {},
        "assumptions": scenario.get("assumptions", []) if isinstance(scenario, Mapping) else [],
        "valid_until": scenario.get("valid_until") if isinstance(scenario, Mapping) else None,
        "provenance": scenario.get("provenance", []) if isinstance(scenario, Mapping) else [],
        "kernel": {
            "name": "DSVA finite retained obstruction kernel",
            "version": "0.11",
            "control_warrant": "exact finite + theory contracts + finite adaptive-policy/contract/recovery realizability",
            "trace_warrant": "type-stable retained states + persistent recovery at declared discrete resolution",
        },
    }
    try:
        status, pre_obs, ctx = preflight(scenario, ledger)
        if status:
            return {
                **base,
                "status": status,
                "selected_action": None,
                "viable_actions": [],
                "rejected_actions": {},
                "obstructions": [o.text() for o in pre_obs],
                "cost_ledger": ledger.as_dict(),
            }

        viable: list[str] = []
        rejected: dict[str, list[str]] = {}
        state_cache, trace_cache = {}, {}
        for action in ctx["actions"]:
            obs = action_obstruction(action, ctx, ledger, state_cache, trace_cache)
            aid = str(action["id"])
            if obs is None:
                viable.append(aid)
            else:
                rejected[aid] = [obs.text()]

        typed_reader = scenario.get("typed_reader", {})
        if typed_reader is None:
            typed_reader = {}
        if not isinstance(typed_reader, Mapping):
            return {
                **base, "status": STATUS_HOLD, "selected_action": None,
                "viable_actions": viable, "rejected_actions": rejected,
                "obstructions": ["TYPED_READER_INVALID"],
                "closure_audit_digest": ctx["closure_audit_digest"],
                "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
            }
        if typed_reader:
            rtype = typed_reader.get("type")
            if rtype not in {"Choice", "Score", "Noul", "deterministic"}:
                return {
                    **base, "status": STATUS_HOLD, "selected_action": None,
                    "viable_actions": viable, "rejected_actions": rejected,
                    "obstructions": ["TYPED_READER_TYPE_INVALID"],
                    "closure_audit_digest": ctx["closure_audit_digest"],
                "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
                }
            conf = typed_reader.get("confidence")
            if conf is not None:
                valid_conf = (
                    not isinstance(conf, bool)
                    and isinstance(conf, (int, float))
                    and math.isfinite(float(conf))
                    and 0.0 <= float(conf) <= 1.0
                )
                if not valid_conf:
                    return {
                        **base, "status": STATUS_HOLD, "selected_action": None,
                        "viable_actions": viable, "rejected_actions": rejected,
                        "obstructions": ["TYPED_READER_CONFIDENCE_INVALID"],
                        "closure_audit_digest": ctx["closure_audit_digest"],
                "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
                    }

        explicit_proposed = scenario.get("proposed_action")
        reader_selected = typed_reader.get("selected")
        if (
            explicit_proposed is not None
            and reader_selected is not None
            and explicit_proposed != reader_selected
        ):
            return {
                **base, "status": STATUS_HOLD, "selected_action": None,
                "viable_actions": viable, "rejected_actions": rejected,
                "obstructions": ["READER_PROPOSAL_CONFLICT"],
                "closure_audit_digest": ctx["closure_audit_digest"],
                    "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
            }
        proposed = explicit_proposed or reader_selected
        if proposed is not None and not isinstance(proposed, str):
            return {
                **base, "status": STATUS_HOLD, "selected_action": None,
                "viable_actions": viable, "rejected_actions": rejected,
                "obstructions": ["PROPOSED_ACTION_INVALID"],
                "closure_audit_digest": ctx["closure_audit_digest"],
                "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
            }
        if proposed:
            if proposed in viable:
                return {
                    **base,
                    "status": STATUS_LICENSED,
                    "selected_action": proposed,
                    "viable_actions": viable,
                    "rejected_actions": rejected,
                    "obstructions": [],
                    "reasons": ["NO_FINITE_OBSTRUCTION_FOUND_FOR_PROPOSED_ACTION"],
                    "typed_reader": dict(typed_reader) or None,
                    "closure_audit_digest": ctx["closure_audit_digest"],
                    "verification_binding": ctx["verification_binding"],
                    "cost_ledger": ledger.as_dict(),
                }
            return {
                **base,
                "status": STATUS_HOLD,
                "selected_action": None,
                "viable_actions": viable,
                "rejected_actions": rejected,
                "obstructions": rejected.get(
                    proposed, ["PROPOSED_ACTION_UNKNOWN_OR_NOT_LICENSED"]
                ),
                "typed_reader": dict(typed_reader) or None,
                "closure_audit_digest": ctx["closure_audit_digest"],
                    "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
            }

        if len(viable) == 1:
            return {
                **base,
                "status": STATUS_LICENSED,
                "selected_action": viable[0],
                "viable_actions": viable,
                "rejected_actions": rejected,
                "obstructions": [],
                "reasons": ["UNIQUE_ACTION_WITH_EMPTY_FINITE_OBSTRUCTION_SET"],
                "closure_audit_digest": ctx["closure_audit_digest"],
                    "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
            }
        if len(viable) > 1:
            return {
                **base,
                "status": STATUS_UNRESOLVED,
                "selected_action": None,
                "viable_actions": viable,
                "rejected_actions": rejected,
                "obstructions": ["MULTIPLE_VIABLE_ACTIONS_READER_REQUIRED"],
                "closure_audit_digest": ctx["closure_audit_digest"],
                    "verification_binding": ctx["verification_binding"],
                "cost_ledger": ledger.as_dict(),
            }
        return {
            **base,
            "status": STATUS_HOLD,
            "selected_action": None,
            "viable_actions": [],
            "rejected_actions": rejected,
            "obstructions": ["NO_VIABLE_ACTION_WITHIN_DECLARED_ENVELOPE"],
            "closure_audit_digest": ctx["closure_audit_digest"],
                    "verification_binding": ctx["verification_binding"],
            "cost_ledger": ledger.as_dict(),
        }
    except Exception as exc:
        # Malformed caller data is a decision condition, not a service crash.
        return {
            **base,
            "status": STATUS_HOLD,
            "selected_action": None,
            "viable_actions": [],
            "rejected_actions": {},
            "obstructions": [f"KERNEL_INPUT_ERROR:{type(exc).__name__}:{exc}"],
            "cost_ledger": ledger.as_dict(),
        }
