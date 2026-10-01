"""Test-only helpers for DSVA v0.10 bound finite snapshots."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


SPEC_KEYS = (
    "question", "envelope", "requirements", "valid_until", "assumptions",
)
INPUT_KEYS = (
    "information_status", "model_invalidated", "closures", "closure_audit",
    "worlds", "disturbances", "actor_information", "trace_library", "actions",
    "typed_reader", "proposed_action", "applicability_evidence", "dependency_audit",
    "resource_audit", "hazard_dependency_audit", "adaptive_policy",
    "boundary_contracts", "recovery_contract", "provenance",
)


def _digest(obj: Any) -> str:
    payload = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def rebind(s: dict) -> dict:
    """Rebind an already well-formed test snapshot after a deliberate mutation."""
    contract = s.get("verification_contract")
    if not isinstance(contract, dict):
        return s
    spec = {k: s[k] for k in SPEC_KEYS if k in s}
    inp = {k: s[k] for k in INPUT_KEYS if k in s}
    contract["spec_digest"] = _digest(spec)
    contract["input_digest"] = _digest(inp)
    return s


def req(
    *,
    rid: str,
    population,
    bindings: dict[str, str],
    op: str,
    value,
    horizon,
    field: str | None = None,
) -> dict:
    out = {
        "id": rid,
        "population": population,
        "bindings": bindings,
        "op": op,
        "value": value,
        "function": f"protect {rid}",
        "constraint": f"{rid}:{op}",
        "threshold": copy.deepcopy(value),
        "horizon": horizon,
        "provenance": ["test-fixture"],
        "coverageStatus": "COVERED",
    }
    if field is not None:
        out["field"] = field
    return out


def execution(action_id: str) -> dict:
    return {
        "commanded": action_id,
        "realized_status": "BOUNDED",
        "bound": "all admitted realized outcomes represented by finite traces",
        "runtime_revalidation_required": False,
        "runtime_revalidation_status": "NOT_REQUIRED",
    }
