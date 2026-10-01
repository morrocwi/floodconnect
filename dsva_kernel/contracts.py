"""DSVA v0.10 executable second-order theory contracts.

These functions project existing DSVA v0.6 theory obligations into finite,
auditable checks. They do not prove world truth: model-behavior sets,
lineage declarations, resource availability and checker metadata remain
caller-supplied evidence whose external validity is a separate obligation.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations
from typing import Any, Mapping

from .core import CostLedger, freeze, q, typed_equal


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
