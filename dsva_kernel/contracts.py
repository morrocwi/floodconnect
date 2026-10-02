"""DSVA v0.11 executable second-order theory and finite realizability contracts.

These functions project existing DSVA v0.6 theory obligations into finite,
auditable checks. They do not prove world truth: model-behavior sets,
lineage declarations, resource availability and checker metadata remain
caller-supplied evidence whose external validity is a separate obligation.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from typing import Any, Mapping, Sequence

from .core import CostLedger, dig, freeze, q, typed_equal


SPEC_KEYS = (
    "question",
    "envelope",
    "requirements",
    "valid_until",
    "assumptions",
)

INPUT_KEYS = (
    "information_status",
    "model_invalidated",
    "closures",
    "closure_audit",
    "worlds",
    "disturbances",
    "actor_information",
    "trace_library",
    "actions",
    "typed_reader",
    "proposed_action",
    "applicability_evidence",
    "dependency_audit",
    "resource_audit",
    "hazard_dependency_audit",
    "adaptive_policy",
    "boundary_contracts",
    "recovery_contract",
    "provenance",
)


def canonical_digest(obj: Any) -> str:
    payload = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def projection(s: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: s.get(k) for k in keys if k in s}


def verification_binding(s: Mapping[str, Any], ledger: CostLedger) -> tuple[str | None, dict | None]:
    ledger.contract_checks += 1
    contract = s.get("verification_contract")
    if not isinstance(contract, Mapping):
        return "VERIFICATION_CONTRACT_MISSING", None

    producer = contract.get("producer")
    checker = contract.get("checker")
    certificate = contract.get("certificate")
    if not isinstance(producer, Mapping) or not isinstance(checker, Mapping):
        return "VERIFIER_PARTY_INVALID", None
    if not isinstance(certificate, Mapping):
        return "VERIFICATION_CERTIFICATE_INVALID", None

    def party(name: str, obj: Mapping[str, Any]) -> tuple[str, str, set[str]] | None:
        pid = obj.get("id")
        impl = obj.get("implementation_digest")
        lineage = obj.get("lineage")
        if not isinstance(pid, str) or not pid:
            return None
        if not isinstance(impl, str) or not impl:
            return None
        if (
            not isinstance(lineage, list)
            or not lineage
            or any(not isinstance(x, str) or not x for x in lineage)
        ):
            return None
        return pid, impl, set(lineage)

    p = party("producer", producer)
    c = party("checker", checker)
    if p is None or c is None:
        return "VERIFIER_PARTY_METADATA_INCOMPLETE", None
    p_id, p_impl, p_lineage = p
    c_id, c_impl, c_lineage = c

    ledger.lineage_checks += 1
    if p_id == c_id:
        return "VERIFIER_NOT_INDEPENDENT:SAME_ID", None
    if p_impl == c_impl:
        return "VERIFIER_NOT_INDEPENDENT:SAME_IMPLEMENTATION", None
    common = sorted(p_lineage & c_lineage)
    if common:
        return f"VERIFIER_NOT_INDEPENDENT:COMMON_LINEAGE:{','.join(common)}", None

    kind = certificate.get("kind")
    witness = certificate.get("witness")
    if not isinstance(kind, str) or not kind or witness in (None, ""):
        return "VERIFICATION_CERTIFICATE_INCOMPLETE", None

    try:
        spec_digest = canonical_digest(projection(s, SPEC_KEYS))
        input_digest = canonical_digest(projection(s, INPUT_KEYS))
        cert_digest = canonical_digest(certificate)
    except Exception as exc:
        return f"VERIFICATION_DIGEST_ERROR:{type(exc).__name__}", None
    ledger.digest_checks += 3

    declared_spec = contract.get("spec_digest")
    declared_input = contract.get("input_digest")
    if declared_spec != spec_digest:
        return "VERIFICATION_SPEC_BINDING_MISMATCH", None
    if declared_input != input_digest:
        return "VERIFICATION_INPUT_BINDING_MISMATCH", None

    return None, {
        "spec_digest": spec_digest,
        "input_digest": input_digest,
        "certificate_digest": cert_digest,
        "producer": p_id,
        "checker": c_id,
    }


def applicability_check(s: Mapping[str, Any], ledger: CostLedger) -> tuple[str | None, dict | None]:
    ledger.contract_checks += 1
    evidence = s.get("applicability_evidence")
    if not isinstance(evidence, Mapping):
        return "APPLICABILITY_EVIDENCE_MISSING", None

    model = evidence.get("model_behavior_signatures")
    observed = evidence.get("observed_behavior_signatures")
    if not isinstance(model, list) or not model:
        return "MODEL_BEHAVIOR_SET_EMPTY", None
    if not isinstance(observed, list) or not observed:
        return "OBSERVED_BEHAVIOR_SET_EMPTY", None

    try:
        model_set = {freeze(x) for x in model}
        obs_set = {freeze(x) for x in observed}
    except Exception as exc:
        return f"APPLICABILITY_SIGNATURE_INVALID:{type(exc).__name__}", None

    overlap = model_set & obs_set
    if not overlap:
        return "MODEL_FAMILY_INVALIDATED_BY_BEHAVIOR", {
            "model_count": len(model_set),
            "observed_count": len(obs_set),
            "overlap_count": 0,
        }

    reader = evidence.get("reader")
    qid = s.get("question", {}).get("id") if isinstance(s.get("question"), Mapping) else None
    if reader is not None and reader != qid:
        return "APPLICABILITY_READER_MISMATCH", None

    return None, {
        "model_count": len(model_set),
        "observed_count": len(obs_set),
        "overlap_count": len(overlap),
    }


def dependency_check(s: Mapping[str, Any], ledger: CostLedger) -> tuple[str | None, dict | None]:
    ledger.contract_checks += 1
    audit = s.get("dependency_audit")
    if not isinstance(audit, Mapping):
        return "DEPENDENCY_AUDIT_MISSING", None
    lineage = audit.get("lineage")
    groups = audit.get("independence_groups")
    if not isinstance(lineage, Mapping) or not isinstance(groups, list):
        return "DEPENDENCY_AUDIT_INVALID", None

    normalized: dict[str, set[str]] = {}
    for node, ancestors in lineage.items():
        if (
            not isinstance(node, str)
            or not node
            or not isinstance(ancestors, list)
            or any(not isinstance(x, str) or not x for x in ancestors)
        ):
            return "DEPENDENCY_LINEAGE_INVALID", None
        normalized[node] = set(ancestors)

    checked = 0
    for group in groups:
        if (
            not isinstance(group, list)
            or len(group) < 2
            or any(not isinstance(x, str) or not x for x in group)
        ):
            return "INDEPENDENCE_GROUP_INVALID", None
        if any(node not in normalized for node in group):
            return "INDEPENDENCE_GROUP_NODE_MISSING_LINEAGE", None
        for a, b in combinations(group, 2):
            ledger.lineage_checks += 1
            checked += 1
            common = sorted(normalized[a] & normalized[b])
            if common:
                return (
                    f"DEPENDENCY_INDEPENDENCE_VIOLATION:{a}:{b}:{','.join(common)}",
                    None,
                )
    return None, {"independence_pairs_checked": checked}


def hazard_dependency_check(s: Mapping[str, Any], ledger: CostLedger) -> tuple[str | None, dict | None]:
    ledger.contract_checks += 1
    audit = s.get("hazard_dependency_audit")
    if not isinstance(audit, Mapping):
        return "HAZARD_DEPENDENCY_AUDIT_MISSING", None
    components = audit.get("components")
    factorized = audit.get("factorized")
    licensed = audit.get("factorization_licensed")
    if (
        not isinstance(components, list)
        or not components
        or any(not isinstance(x, str) or not x for x in components)
    ):
        return "HAZARD_COMPONENTS_INVALID", None
    if not isinstance(factorized, bool) or not isinstance(licensed, bool):
        return "HAZARD_FACTORIZATION_STATUS_INVALID", None
    if factorized and len(components) > 1 and not licensed:
        return "COMPOUND_HAZARD_FACTORIZATION_UNLICENSED", None
    return None, {
        "components": list(components),
        "factorized": factorized,
        "factorization_licensed": licensed,
    }


def requirement_ledger_check(
    req: Mapping[str, Any],
    horizon: Any,
    ledger: CostLedger,
) -> str | None:
    ledger.contract_checks += 1
    rid = str(req.get("id", "?"))
    function = req.get("function")
    constraint = req.get("constraint")
    provenance = req.get("provenance")
    status = req.get("coverageStatus")
    if not isinstance(function, str) or not function:
        return f"REQUIREMENT_FUNCTION_MISSING:{rid}"
    if not isinstance(constraint, str) or not constraint:
        return f"REQUIREMENT_CONSTRAINT_MISSING:{rid}"
    if (
        not isinstance(provenance, list)
        or not provenance
        or any(not isinstance(x, str) or not x for x in provenance)
    ):
        return f"REQUIREMENT_PROVENANCE_MISSING:{rid}"
    if status != "COVERED":
        return f"REQUIREMENT_COVERAGE_NOT_COVERED:{rid}:{status}"
    try:
        rh = q(req.get("horizon"), ledger=ledger)
        qh = q(horizon, ledger=ledger)
    except Exception as exc:
        return f"REQUIREMENT_HORIZON_INVALID:{rid}:{type(exc).__name__}"
    if rh < qh:
        return f"REQUIREMENT_HORIZON_TOO_SHORT:{rid}:{rh}<{qh}"

    if "threshold" not in req:
        return f"REQUIREMENT_THRESHOLD_MISSING:{rid}"
    if "value" in req and not typed_equal(req.get("threshold"), req.get("value")):
        return f"REQUIREMENT_THRESHOLD_VALUE_MISMATCH:{rid}"
    return None


def resource_obstruction(
    s: Mapping[str, Any],
    action_id: str,
    ledger: CostLedger,
) -> str | None:
    ledger.contract_checks += 1
    audit = s.get("resource_audit")
    if not isinstance(audit, Mapping):
        return "RESOURCE_AUDIT_MISSING"
    if audit.get("declared_none") is True:
        resources = audit.get("resources", {})
        use = audit.get("action_use", {})
        if resources or use:
            return "RESOURCE_AUDIT_DECLARED_NONE_CONTRADICTION"
        return None

    resources = audit.get("resources")
    action_use = audit.get("action_use")
    if not isinstance(resources, Mapping) or not isinstance(action_use, Mapping):
        return "RESOURCE_AUDIT_INVALID"
    use = action_use.get(action_id, {})
    if not isinstance(use, Mapping):
        return f"RESOURCE_USE_INVALID:{action_id}"

    for rid, amount in use.items():
        if rid not in resources or not isinstance(resources[rid], Mapping):
            return f"RESOURCE_UNDECLARED:{action_id}:{rid}"
        try:
            available = q(resources[rid].get("available"), ledger=ledger)
            needed = q(amount, ledger=ledger)
        except Exception as exc:
            return f"RESOURCE_AMOUNT_INVALID:{action_id}:{rid}:{type(exc).__name__}"
        if available < 0 or needed < 0:
            return f"RESOURCE_NEGATIVE:{action_id}:{rid}"
        if needed > available:
            return f"RESOURCE_OVERBOOKED:{action_id}:{rid}:{needed}>{available}"
    return None


def future_observation_obstruction(
    action: Mapping[str, Any],
    observation_envelope: set[str],
    ledger: CostLedger,
) -> str | None:
    contract = action.get("future_observation_contract")
    if contract is None:
        return None
    ledger.contract_checks += 1
    if not isinstance(contract, Mapping):
        return "FUTURE_OBSERVATION_CONTRACT_INVALID"
    channel = contract.get("channel")
    outcomes = contract.get("admitted_outcomes")
    responses = contract.get("responses")
    if not isinstance(channel, str) or not channel:
        return "FUTURE_OBSERVATION_CHANNEL_INVALID"
    if channel not in observation_envelope:
        return f"FUTURE_OBSERVATION_CHANNEL_OUTSIDE_ENVELOPE:{channel}"
    if (
        not isinstance(outcomes, list)
        or not outcomes
        or any(not isinstance(x, str) or not x for x in outcomes)
        or len(set(outcomes)) != len(outcomes)
    ):
        return "FUTURE_OBSERVATION_OUTCOMES_INVALID"
    if not isinstance(responses, Mapping):
        return "FUTURE_OBSERVATION_RESPONSES_INVALID"
    if set(responses) != set(outcomes):
        missing = sorted(set(outcomes) - set(responses))
        extra = sorted(set(responses) - set(outcomes))
        return f"FUTURE_OBSERVATION_POLICY_NOT_TOTAL:missing={missing}:extra={extra}"
    if any(not isinstance(v, str) or not v for v in responses.values()):
        return "FUTURE_OBSERVATION_RESPONSE_INVALID"
    return None


def execution_obstruction(action: Mapping[str, Any], ledger: CostLedger) -> str | None:
    ledger.contract_checks += 1
    aid = action.get("id")
    contract = action.get("execution_contract")
    if not isinstance(contract, Mapping):
        return f"EXECUTION_CONTRACT_MISSING:{aid}"
    if contract.get("commanded") != aid:
        return f"EXECUTION_COMMAND_MISMATCH:{aid}"
    status = contract.get("realized_status")
    if status not in {"VERIFIED", "BOUNDED"}:
        return f"REALIZED_ACTUATION_UNVERIFIED:{aid}:{status}"
    if status == "BOUNDED" and contract.get("bound") in (None, ""):
        return f"REALIZED_ACTUATION_BOUND_MISSING:{aid}"
    required = contract.get("runtime_revalidation_required")
    rstatus = contract.get("runtime_revalidation_status")
    if not isinstance(required, bool):
        return f"RUNTIME_REVALIDATION_FLAG_INVALID:{aid}"
    if required and rstatus != "PASS":
        return f"RUNTIME_REVALIDATION_NOT_PASS:{aid}:{rstatus}"
    if not required and rstatus not in {"NOT_REQUIRED", "PASS"}:
        return f"RUNTIME_REVALIDATION_STATUS_INVALID:{aid}:{rstatus}"
    return None


def adaptive_policy_obstruction(
    s: Mapping[str, Any],
    action: Mapping[str, Any],
    observation_envelope: set[str],
    actuation_envelope: set[str],
    actor_information: Mapping[str, Any],
    horizon: Any,
    ledger: CostLedger,
) -> str | None:
    """Finite structural projection of SOL-22/23.

    This verifies a finite actor-local policy DAG and anti-hindsight timing.
    Dynamic safety of each admitted world/disturbance remains checked by the
    separate retained traces.
    """
    aid = action.get("id")
    future = action.get("future_observation_contract")
    policy = s.get("adaptive_policy")
    if policy is None:
        return "ADAPTIVE_POLICY_MISSING" if future is not None else None
    if not isinstance(policy, Mapping):
        return "ADAPTIVE_POLICY_INVALID"
    root = policy.get("root")
    nodes = policy.get("nodes")
    if not isinstance(root, str) or not root or not isinstance(nodes, Mapping) or root not in nodes:
        return "ADAPTIVE_POLICY_ROOT_INVALID"

    root_node = nodes.get(root)
    if not isinstance(root_node, Mapping):
        return "ADAPTIVE_POLICY_ROOT_INVALID"
    root_action = root_node.get("action")
    # One top-level finite policy witnesses one current action. Other candidate
    # actions remain open-loop unless they themselves declare future observation.
    if root_action != aid:
        return "ADAPTIVE_POLICY_ROOT_ACTION_MISMATCH" if future is not None else None

    try:
        H = q(horizon, ledger=ledger)
    except Exception as exc:
        return f"ADAPTIVE_POLICY_HORIZON_INVALID:{type(exc).__name__}"

    action_by_id = {}
    actions = s.get("actions")
    if not isinstance(actions, list):
        return "ADAPTIVE_POLICY_ACTION_REGISTRY_INVALID"
    for a in actions:
        if isinstance(a, Mapping) and isinstance(a.get("id"), str):
            action_by_id[a["id"]] = a

    base_known: dict[str, set[str]] = {}
    for actor, meta in actor_information.items():
        if not isinstance(actor, str) or not isinstance(meta, Mapping):
            return "ADAPTIVE_POLICY_ACTOR_INFORMATION_INVALID"
        known = meta.get("known", [])
        if not isinstance(known, list) or any(not isinstance(x, str) for x in known):
            return f"ADAPTIVE_POLICY_ACTOR_INFORMATION_INVALID:{actor}"
        base_known[actor] = set(known)

    reachable: set[str] = set()

    def visit(
        node_id: str,
        known_by_actor: dict[str, set[str]],
        earliest_time: Any,
        stack: tuple[str, ...],
    ) -> str | None:
        ledger.contract_checks += 1
        if node_id in stack:
            return f"ADAPTIVE_POLICY_CYCLE:{node_id}"
        node = nodes.get(node_id)
        if not isinstance(node, Mapping):
            return f"ADAPTIVE_POLICY_NODE_MISSING:{node_id}"
        reachable.add(node_id)

        try:
            t = q(node.get("time"), ledger=ledger)
            t_min = q(earliest_time, ledger=ledger)
        except Exception as exc:
            return f"ADAPTIVE_POLICY_TIME_INVALID:{node_id}:{type(exc).__name__}"
        if t < 0 or t > H:
            return f"ADAPTIVE_POLICY_TIME_OUTSIDE_HORIZON:{node_id}:{t}"
        if t < t_min:
            return f"ADAPTIVE_POLICY_ANTI_HINDSIGHT_VIOLATION:{node_id}:{t}<{t_min}"

        actor = node.get("actor")
        act = node.get("action")
        if not isinstance(actor, str) or actor not in base_known:
            return f"ADAPTIVE_POLICY_ACTOR_INVALID:{node_id}:{actor}"
        if not isinstance(act, str) or act not in actuation_envelope:
            return f"ADAPTIVE_POLICY_ACTION_OUTSIDE_ENVELOPE:{node_id}:{act}"

        registry_action = action_by_id.get(act)
        registry_req = []
        if isinstance(registry_action, Mapping):
            registry_req = registry_action.get("requires_info", [])
        node_req = node.get("requires_info", [])
        if (
            not isinstance(registry_req, list)
            or not isinstance(node_req, list)
            or any(not isinstance(x, str) or not x for x in registry_req + node_req)
        ):
            return f"ADAPTIVE_POLICY_REQUIRES_INFO_INVALID:{node_id}"
        needed = set(registry_req) | set(node_req)
        missing = needed - known_by_actor.get(actor, set())
        if missing:
            return f"ADAPTIVE_POLICY_ACTOR_LOCAL_INFO_MISSING:{node_id}:{','.join(sorted(missing))}"

        observe = node.get("observe")
        terminal = node.get("terminal", False)
        if observe is None:
            if terminal is not True:
                return f"ADAPTIVE_POLICY_NONTERMINAL_WITHOUT_OBSERVATION:{node_id}"
            return None
        if terminal is True:
            return f"ADAPTIVE_POLICY_TERMINAL_HAS_OBSERVATION:{node_id}"
        if not isinstance(observe, Mapping):
            return f"ADAPTIVE_POLICY_OBSERVATION_INVALID:{node_id}"

        channel = observe.get("channel")
        if not isinstance(channel, str) or channel not in observation_envelope:
            return f"ADAPTIVE_POLICY_CHANNEL_OUTSIDE_ENVELOPE:{node_id}:{channel}"
        try:
            obs_t = q(observe.get("time"), ledger=ledger)
        except Exception as exc:
            return f"ADAPTIVE_POLICY_OBSERVATION_TIME_INVALID:{node_id}:{type(exc).__name__}"
        if obs_t <= t or obs_t > H:
            return f"ADAPTIVE_POLICY_OBSERVATION_TIME_INVALID:{node_id}:{obs_t}"

        delivered = observe.get("delivered_to")
        outcomes = observe.get("outcomes")
        admitted = observe.get("admitted_outcomes")
        if (
            not isinstance(delivered, list)
            or not delivered
            or any(not isinstance(x, str) or x not in base_known for x in delivered)
        ):
            return f"ADAPTIVE_POLICY_DELIVERY_INVALID:{node_id}"
        if not isinstance(outcomes, Mapping) or not outcomes:
            return f"ADAPTIVE_POLICY_OUTCOMES_INVALID:{node_id}"

        if node_id == root and future is not None:
            admitted = future.get("admitted_outcomes")
            responses = future.get("responses")
            if future.get("channel") != channel:
                return "ADAPTIVE_POLICY_FUTURE_CHANNEL_MISMATCH"
            if not isinstance(responses, Mapping) or dict(responses) != dict(outcomes):
                return "ADAPTIVE_POLICY_RESPONSE_NODE_BINDING_MISMATCH"
        if (
            not isinstance(admitted, list)
            or not admitted
            or any(not isinstance(x, str) or not x for x in admitted)
            or len(set(admitted)) != len(admitted)
        ):
            return f"ADAPTIVE_POLICY_ADMITTED_OUTCOMES_INVALID:{node_id}"
        if set(outcomes) != set(admitted):
            return f"ADAPTIVE_POLICY_NOT_TOTAL:{node_id}"

        for outcome, child in outcomes.items():
            if not isinstance(child, str) or child not in nodes:
                return f"ADAPTIVE_POLICY_CHILD_INVALID:{node_id}:{outcome}:{child}"
            child_known = {k: set(v) for k, v in known_by_actor.items()}
            for dest in delivered:
                child_known.setdefault(dest, set()).add(channel)
            err = visit(child, child_known, obs_t, stack + (node_id,))
            if err:
                return err
        return None

    err = visit(root, {k: set(v) for k, v in base_known.items()}, 0, tuple())
    if err:
        return err
    # Unreachable policy nodes are ambiguous dead specifications; fail closed.
    extra = set(nodes) - reachable
    if extra:
        return f"ADAPTIVE_POLICY_UNREACHABLE_NODES:{','.join(sorted(extra))}"
    return None


def boundary_contract_obstruction(
    s: Mapping[str, Any],
    action_id: str,
    worlds: Sequence[str],
    disturbances: Sequence[str],
    horizon: Any,
    ledger: CostLedger,
) -> str | None:
    """Finite projection of SOL-20/21 for load-bearing assume-guarantee contracts."""
    contracts = s.get("boundary_contracts")
    if not isinstance(contracts, list):
        return "BOUNDARY_CONTRACT_LEDGER_MISSING"
    seen: set[str] = set()
    try:
        H = q(horizon, ledger=ledger)
    except Exception as exc:
        return f"BOUNDARY_CONTRACT_HORIZON_INVALID:{type(exc).__name__}"

    for contract in contracts:
        ledger.contract_checks += 1
        if not isinstance(contract, Mapping):
            return "BOUNDARY_CONTRACT_INVALID"
        cid = contract.get("id")
        if not isinstance(cid, str) or not cid or cid in seen:
            return f"BOUNDARY_CONTRACT_ID_INVALID:{cid}"
        seen.add(cid)
        used_by = contract.get("used_by", [])
        if not isinstance(used_by, list) or any(not isinstance(x, str) for x in used_by):
            return f"BOUNDARY_CONTRACT_USED_BY_INVALID:{cid}"
        if action_id not in used_by:
            continue
        try:
            invoke = q(contract.get("invoke_time"), ledger=ledger)
        except Exception as exc:
            return f"BOUNDARY_CONTRACT_INVOKE_TIME_INVALID:{cid}:{type(exc).__name__}"
        if invoke < 0 or invoke > H:
            return f"BOUNDARY_CONTRACT_INVOKE_TIME_OUTSIDE_HORIZON:{cid}:{invoke}"
        branches = contract.get("branches")
        if not isinstance(branches, Mapping):
            return f"BOUNDARY_CONTRACT_BRANCHES_INVALID:{cid}"
        for world in worlds:
            w = branches.get(world)
            if not isinstance(w, Mapping):
                return f"BOUNDARY_CONTRACT_BRANCH_MISSING:{cid}:{world}"
            for dist in disturbances:
                ledger.branches_checked += 1
                witness = w.get(dist)
                if not isinstance(witness, Mapping):
                    return f"BOUNDARY_CONTRACT_BRANCH_MISSING:{cid}:{world}/{dist}"
                if witness.get("assumption") is not True:
                    return f"BOUNDARY_CONTRACT_ASSUMPTION_UNREALIZABLE:{cid}:{world}/{dist}"
                if witness.get("guarantee") is not True:
                    return f"BOUNDARY_CONTRACT_GUARANTEE_UNREALIZABLE:{cid}:{world}/{dist}"
    return None


def recovery_trace_obstruction(
    s: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    times: Sequence[Any],
    horizon: Any,
    resolution: Any,
    ledger: CostLedger,
) -> str | None:
    """Finite retained projection of SOL-25..27 persistent recovery."""
    contract = s.get("recovery_contract")
    if not isinstance(contract, Mapping):
        return "RECOVERY_CONTRACT_MISSING"
    required = contract.get("required")
    if not isinstance(required, bool):
        return "RECOVERY_CONTRACT_REQUIRED_FLAG_INVALID"
    if not required:
        return None

    field = contract.get("field")
    if not isinstance(field, str) or not field or "value" not in contract:
        return "RECOVERY_CONTRACT_READER_INVALID"
    try:
        t_return = q(contract.get("return_time"), ledger=ledger)
        H_R = q(contract.get("persistence_horizon"), ledger=ledger)
        H = q(horizon, ledger=ledger)
        lam = q(resolution, ledger=ledger)
    except Exception as exc:
        return f"RECOVERY_CONTRACT_TIME_INVALID:{type(exc).__name__}"
    if t_return < 0 or H_R <= 0 or t_return + H_R > H:
        return f"RECOVERY_PERSISTENCE_WINDOW_INVALID:{t_return}+{H_R}>{H}"
    if (t_return / lam).denominator != 1 or (H_R / lam).denominator != 1:
        return "RECOVERY_WINDOW_OFF_DECLARED_RESOLUTION"

    target = contract.get("value")
    required_times = []
    t = t_return
    while t <= t_return + H_R:
        required_times.append(t)
        t += lam
    index = {q(ti, ledger=ledger): state for ti, state in zip(times, trace)}
    for ti in required_times:
        state = index.get(ti)
        if state is None:
            return f"RECOVERY_STATE_MISSING_AT:{ti}"
        try:
            actual = dig(state, field)
        except Exception:
            return f"RECOVERY_FIELD_MISSING_AT:{ti}:{field}"
        if not typed_equal(actual, target):
            return f"RECOVERY_NOT_PERSISTENT_AT:{ti}:{field}"
    return None
