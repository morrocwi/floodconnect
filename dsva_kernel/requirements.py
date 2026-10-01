"""Subject-bound protected-requirement compilation and retained-state quotient."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .core import CostLedger, SUPPORTED_REQ_OPS, dig, freeze, q, typed_equal


def requirement_population(req: Mapping[str, Any]) -> set[str]:
    p = req.get("population")
    if isinstance(p, str) and p:
        return {p}
    if isinstance(p, list) and p and all(isinstance(x, str) and x for x in p):
        if len(set(p)) != len(p):
            raise ValueError("requirement population contains duplicates")
        return set(p)
    raise ValueError("requirement population must be a non-empty string/list")


def requirement_bindings(req: Mapping[str, Any]) -> dict[str, str]:
    """Compile an executable per-subject binding.

    v0.9 strong semantics:
    - a one-subject legacy requirement may use field directly;
    - multi-subject requirements MUST bind every subject to a distinct field;
    - binding keys must equal the declared population exactly.

    Aggregate/group semantics are intentionally not inferred here. They require
    a separate adapter/certificate rather than silently treating one field as
    evidence for multiple protected subjects.
    """
    pop = requirement_population(req)
    bindings = req.get("bindings")
    if bindings is None:
        field = req.get("field")
        if len(pop) == 1 and isinstance(field, str) and field:
            return {next(iter(pop)): field}
        raise ValueError(
            "multi-subject requirement requires explicit per-subject bindings"
        )
    if not isinstance(bindings, Mapping) or not bindings:
        raise ValueError("requirement bindings must be a non-empty mapping")
    out: dict[str, str] = {}
    for subject, field in bindings.items():
        if not isinstance(subject, str) or not subject:
            raise ValueError("requirement binding subject must be a non-empty string")
        if not isinstance(field, str) or not field:
            raise ValueError("requirement binding field must be a non-empty string")
        out[subject] = field
    if set(out) != pop:
        raise ValueError(
            f"requirement bindings must exactly cover population: "
            f"population={sorted(pop)},bindings={sorted(out)}"
        )
    if len(set(out.values())) != len(out):
        raise ValueError(
            "per-subject bindings must use distinct fields; aggregate semantics "
            "need a separate certified adapter"
        )
    return out


def _typed_membership(actual: Any, expected: Any) -> bool:
    if not isinstance(expected, (list, tuple, set)):
        raise ValueError("membership expected value must be a finite collection")
    return any(typed_equal(actual, x) for x in expected)


def _atomic_holds(
    state: Mapping[str, Any],
    field: str,
    op: str,
    expected: Any,
) -> tuple[bool, str | None]:
    try:
        actual = dig(state, field)
    except Exception:
        return False, f"REQUIREMENT_FIELD_MISSING:{field}"
    try:
        if op == "eq":
            ok = typed_equal(actual, expected)
        elif op == "ne":
            ok = not typed_equal(actual, expected)
        elif op in {"ge", "gt", "le", "lt"}:
            a, b = q(actual), q(expected)
            ok = {"ge": a >= b, "gt": a > b, "le": a <= b, "lt": a < b}[op]
        elif op == "in":
            ok = _typed_membership(actual, expected)
        elif op == "not_in":
            ok = not _typed_membership(actual, expected)
        elif op == "truthy":
            ok = isinstance(actual, bool) and actual is True
        elif op == "falsy":
            ok = isinstance(actual, bool) and actual is False
        else:
            return False, f"REQUIREMENT_OPERATOR_UNSUPPORTED:{op}"
    except Exception as exc:
        return False, f"REQUIREMENT_EVAL_ERROR:{type(exc).__name__}"
    return (True, None) if ok else (False, "REQUIREMENT_ATOM_FAIL")


def requirement_holds(
    state: Mapping[str, Any],
    req: Mapping[str, Any],
) -> tuple[bool, str | None]:
    rid = str(req.get("id", "?"))
    op = req.get("op", "eq")
    if op not in SUPPORTED_REQ_OPS:
        return False, f"REQUIREMENT_OPERATOR_UNSUPPORTED:{rid}:{op}"
    try:
        bindings = requirement_bindings(req)
    except Exception as exc:
        return False, f"REQUIREMENT_BINDING_INVALID:{rid}:{exc}"
    expected = req.get("value")
    for subject, field in bindings.items():
        ok, why = _atomic_holds(state, field, op, expected)
        if not ok:
            return False, f"REQUIREMENT_FAIL:{rid}:subject={subject}:{why}"
    return True, None


def state_signature(
    state: Mapping[str, Any],
    reqs: Sequence[Mapping[str, Any]],
) -> tuple:
    """Type-stable reader-equivalence signature over bound requirement fields."""
    vals = []
    for req in reqs:
        rid = str(req.get("id", "?"))
        try:
            bindings = requirement_bindings(req)
        except Exception as exc:
            vals.append(("bad-binding", rid, str(exc)))
            continue
        for subject, field in sorted(bindings.items()):
            try:
                vals.append((rid, subject, field, freeze(dig(state, field))))
            except Exception:
                vals.append((rid, subject, field, ("missing",)))
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
