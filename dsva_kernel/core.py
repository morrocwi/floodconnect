"""Exact-finite primitives for the DSVA v0.8 obstruction kernel.

The module borrows three *operator-level* disciplines from the sibling
information-discrete-math project: exact retained arithmetic where possible,
fail-closed verdicts, and an explicit cost ledger.  It is not a runtime
dependency on IDM and does not create a parallel ontology.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, Mapping

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
SUPPORTED_INFO_STATUS = {"SUPPORTED", "UNRESOLVED", "CONTRADICTION"}
SUPPORTED_REQ_OPS = {
    "eq", "ne", "ge", "gt", "le", "lt",
    "in", "not_in", "truthy", "falsy",
}
SUPPORTED_TRACE_SEMANTICS = {"discrete_retained"}


@dataclass
class CostLedger:
    actions_checked: int = 0
    branches_checked: int = 0
    states_checked: int = 0
    predicates_checked: int = 0
    state_cache_hits: int = 0
    traces_checked: int = 0
    trace_cache_hits: int = 0
    exact_time_parses: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "actions_checked": self.actions_checked,
            "branches_checked": self.branches_checked,
            "states_checked": self.states_checked,
            "predicates_checked": self.predicates_checked,
            "state_cache_hits": self.state_cache_hits,
            "traces_checked": self.traces_checked,
            "trace_cache_hits": self.trace_cache_hits,
            "exact_time_parses": self.exact_time_parses,
        }


@dataclass(frozen=True)
class Obstruction:
    code: str
    detail: str = ""
    scope: str = "scenario"

    def text(self) -> str:
        parts = [self.code]
        if self.scope:
            parts.append(f"scope={self.scope}")
        if self.detail:
            parts.append(self.detail)
        return ":".join(parts)


def freeze(v: Any) -> Any:
    """Deterministic finite readout key; never relies on process-random hash."""
    if isinstance(v, Mapping):
        return tuple(sorted((str(k), freeze(x)) for k, x in v.items()))
    if isinstance(v, (list, tuple)):
        return tuple(freeze(x) for x in v)
    if isinstance(v, set):
        return tuple(sorted(freeze(x) for x in v))
    if isinstance(v, float):
        if not math.isfinite(v):
            return ("nonfinite", repr(v))
        return ("q", str(Fraction(str(v))))
    if isinstance(v, (int, str, bool, type(None), Fraction)):
        return v
    return ("repr", repr(v))


def q(v: Any, *, ledger: CostLedger | None = None) -> Fraction:
    """Read a decision-time scalar as an exact rational.

    JSON decimals are converted through their decimal string, not through the
    binary float ratio, so 0.1 is retained as 1/10.
    """
    if ledger:
        ledger.exact_time_parses += 1
    if isinstance(v, bool):
        raise ValueError("boolean is not a time/number")
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int):
        return Fraction(v, 1)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise ValueError("non-finite number")
        return Fraction(str(v))
    if isinstance(v, str):
        return Fraction(v.strip())
    raise ValueError(f"unsupported exact number {type(v).__name__}")


def dig(obj: Mapping[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            raise KeyError(path)
        cur = cur[part]
    return cur


def as_str_set(v: Any, *, name: str, allow_empty: bool = False) -> set[str]:
    if not isinstance(v, list):
        raise ValueError(f"{name} must be a list")
    out: list[str] = []
    for x in v:
        if not isinstance(x, str) or not x:
            raise ValueError(f"{name} entries must be non-empty strings")
        out.append(x)
    if len(set(out)) != len(out):
        raise ValueError(f"{name} contains duplicates")
    if not allow_empty and not out:
        raise ValueError(f"{name} must be non-empty")
    return set(out)
