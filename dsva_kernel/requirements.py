"""Protected-requirement compilation and retained-state quotient."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .core import CostLedger, SUPPORTED_REQ_OPS, dig, freeze, q


def requirement_population(req: Mapping[str, Any]) -> set[str]:
    p = req.get("population")
    if isinstance(p, str) and p:
        return {p}
    if isinstance(p, list) and p and all(isinstance(x, str) and x for x in p):
        if len(set(p)) != len(p):
            raise ValueError("requirement population contains duplicates")
        return set(p)
    raise ValueError("requirement population must be a non-empty string/list")


def requirement_holds(
    state: Mapping[str, Any],
    req: Mapping[str, Any],
) -> tuple[bool, str | None]:
    rid = str(req.get("id", req.get("field", "?")))
    field = req.get("field")
    op = req.get("op", "eq")
    if not isinstance(field, str) or not field:
        return False, f"REQUIREMENT_FIELD_INVALID:{rid}"
    if op not in SUPPORTED_REQ_OPS:
        return False, f"REQUIREMENT_OPERATOR_UNSUPPORTED:{rid}:{op}"
    try:
        actual = dig(state, field)
    except Exception:
        return False, f"REQUIREMENT_FIELD_MISSING:{rid}:{field}"
    expected = req.get("value")
    try:
        if op == "eq":
            ok = actual == expected
        elif op == "ne":
            ok = actual != expected
        elif op in {"ge", "gt", "le", "lt"}:
            a, b = q(actual), q(expected)
            ok = {"ge": a >= b, "gt": a > b, "le": a <= b, "lt": a < b}[op]
        elif op == "in":
            if not isinstance(expected, (list, tuple, set)):
                return False, f"REQUIREMENT_VALUE_INVALID:{rid}:in"
            ok = actual in expected
        elif op == "not_in":
            if not isinstance(expected, (list, tuple, set)):
                return False, f"REQUIREMENT_VALUE_INVALID:{rid}:not_in"
            ok = actual not in expected
        elif op == "truthy":
            ok = bool(actual)
        elif op == "falsy":
            ok = not bool(actual)
        else:
            return False, f"REQUIREMENT_OPERATOR_UNSUPPORTED:{rid}:{op}"
    except Exception as exc:
        return False, f"REQUIREMENT_EVAL_ERROR:{rid}:{type(exc).__name__}"
    return (True, None) if ok else (False, f"REQUIREMENT_FAIL:{rid}")


def state_signature(
    state: Mapping[str, Any],
    reqs: Sequence[Mapping[str, Any]],
) -> tuple:
    """Reader-equivalence signature over only fields the requirements can read.

    If two states have the same signature, the compiled requirement reader must
    return the same result.  This is the finite quotient used for cache-safe
    acceleration; irrelevant state fields are intentionally discarded.
    """
    vals = []
    for req in reqs:
        field = req.get("field")
        if not isinstance(field, str) or not field:
            vals.append(("bad-field", str(field)))
            continue
        try:
            vals.append(freeze(dig(state, field)))
        except Exception:
            vals.append(("missing", field))
    return tuple(vals)


def state_safe(
    state: Mapping[str, Any],
    reqs: Sequence[Mapping[str, Any]],
    cache: dict,
    ledger: CostLedger,
) -> tuple[bool, str | None]:
    sig = state_signature(state, reqs)
    if sig in cache:
        ledger.state_cache_hits += 1
        return cache[sig]
    ledger.states_checked += 1
    for req in reqs:
        ledger.predicates_checked += 1
        ok, why = requirement_holds(state, req)
        if not ok:
            cache[sig] = (False, why)
            return False, why
    cache[sig] = (True, None)
    return True, None
