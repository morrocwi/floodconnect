#!/usr/bin/env python3
"""
finite_temporal_ledger.py

Toledo-aligned finite temporal accumulation for FloodConnect environmental mechanisms.

Principles:
- one bounded declared observation window [t0, t1];
- one finite declared event set inside that window;
- exact rational (Fraction/Q) duration arithmetic;
- no infinity sentinel;
- unknown prior history is LEFT_CENSORED, never silently zero;
- incomplete event history REFUSES exact accumulation;
- a mitigation event does not stop a clock; only a verified RESOLVED event does.

This is temporal bookkeeping, not a dose-response or toxicity model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from fractions import Fraction
from typing import Any, Optional

OK = "OK"
REFUSED = "REFUSED"
UNKNOWN = "UNKNOWN"

REASON_MISSING_WINDOW = "MISSING_WINDOW"
REASON_INVALID_WINDOW = "INVALID_WINDOW"
REASON_INCOMPLETE_WINDOW = "INCOMPLETE_WINDOW"
REASON_TIMELINE_NOT_FINITE_LIST = "TIMELINE_NOT_FINITE_LIST"
REASON_EVENT_OUTSIDE_WINDOW = "EVENT_OUTSIDE_WINDOW"
REASON_INVALID_EVENT = "INVALID_EVENT"
REASON_UNVERIFIED_EVENT = "UNVERIFIED_EVENT"
REASON_INVALID_TRANSITION = "INVALID_TRANSITION"
REASON_LEFT_CENSORED = "LEFT_CENSORED"
REASON_MISSING_COVERAGE = "MISSING_COVERAGE"
REASON_INVALID_COVERAGE = "INVALID_COVERAGE"
REASON_MISSING_BOUNDARY_STATE = "MISSING_BOUNDARY_STATE"
REASON_EVENT_OUTSIDE_COVERAGE = "EVENT_OUTSIDE_COVERAGE"

ALLOWED_EVENTS = {"START", "OBSERVED_ACTIVE", "MITIGATION", "RESOLVED"}

# Deliberately finite, explicit mechanism vocabulary for this version.
MECHANISMS = (
    "sewage_intrusion",
    "sewer_backflow",
    "sewer_gas_odor",
    "dry_trap",
    "indoor_wet_materials",
    "standing_water",
    "stagnation",
    "toilet_service_failure",
    "solid_waste_accumulation",
)


@dataclass(frozen=True)
class MechanismAccumulation:
    mechanism: str
    cumulative_h: Optional[Fraction]
    current_episode_h: Optional[Fraction]
    recurrence_count: int
    active_at_window_end: Optional[bool]
    left_censored: bool = False
    current_episode_lower_bound_h: Optional[Fraction] = None

    def as_dict(self) -> dict[str, Any]:
        def q(x: Optional[Fraction]) -> Optional[str]:
            return None if x is None else str(x)
        return {
            "mechanism": self.mechanism,
            "cumulative_h_q": q(self.cumulative_h),
            "current_episode_h_q": q(self.current_episode_h),
            "recurrence_count": self.recurrence_count,
            "active_at_window_end": self.active_at_window_end,
            "left_censored": self.left_censored,
            "current_episode_lower_bound_h_q": q(self.current_episode_lower_bound_h),
        }


@dataclass(frozen=True)
class TemporalLedgerResult:
    status: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    window_h: Optional[Fraction] = None
    mechanisms: tuple[MechanismAccumulation, ...] = ()
    active_mechanism_count: Optional[int] = None
    max_concurrent_mechanisms: Optional[int] = None
    reason_codes: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def refused(self) -> bool:
        return self.status == REFUSED

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "window_h_q": None if self.window_h is None else str(self.window_h),
            "mechanisms": [m.as_dict() for m in self.mechanisms],
            "active_mechanism_count": self.active_mechanism_count,
            "max_concurrent_mechanisms": self.max_concurrent_mechanisms,
            "reason_codes": list(self.reason_codes),
            "details": dict(self.details),
        }


def _dedup(xs):
    return tuple(dict.fromkeys(xs))


def _parse_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _delta_hours_q(a: datetime, b: datetime) -> Fraction:
    """Exact rational hours from Python's finite microsecond datetime resolution."""
    td = b - a
    total_us = (
        td.days * 86400 * 1_000_000
        + td.seconds * 1_000_000
        + td.microseconds
    )
    return Fraction(total_us, 3_600_000_000)


def _window(
    env: dict[str, Any],
) -> tuple[Optional[datetime], Optional[datetime], tuple[str, ...], dict[str, str], list[str]]:
    w = env.get("timeline_window")
    if not isinstance(w, dict):
        return None, None, (), {}, [REASON_MISSING_WINDOW]
    start = _parse_time(w.get("start"))
    end = _parse_time(w.get("end"))
    reasons = []
    if start is None or end is None or end <= start:
        reasons.append(REASON_INVALID_WINDOW)
    if w.get("complete") is not True:
        reasons.append(REASON_INCOMPLETE_WINDOW)

    raw_covered = w.get("covered_mechanisms")
    if not isinstance(raw_covered, list) or not raw_covered:
        covered: tuple[str, ...] = ()
        reasons.append(REASON_MISSING_COVERAGE)
    else:
        covered = tuple(dict.fromkeys(str(x) for x in raw_covered))
        if any(m not in MECHANISMS for m in covered):
            reasons.append(REASON_INVALID_COVERAGE)

    raw_boundary = w.get("left_boundary_state")
    boundary: dict[str, str] = {}
    if not isinstance(raw_boundary, dict):
        reasons.append(REASON_MISSING_BOUNDARY_STATE)
    else:
        for mechanism in covered:
            state = str(raw_boundary.get(mechanism, "")).upper()
            if state not in {"ACTIVE", "INACTIVE", "UNKNOWN"}:
                reasons.append(REASON_MISSING_BOUNDARY_STATE)
            else:
                boundary[mechanism] = state

    return start, end, covered, boundary, reasons


def accumulate_environment_timeline(node: dict[str, Any]) -> TemporalLedgerResult:
    env = node.get("environment")
    if not isinstance(env, dict):
        return TemporalLedgerResult(REFUSED, reason_codes=(REASON_MISSING_WINDOW,))

    start, end, covered, boundary, window_reasons = _window(env)
    if window_reasons:
        return TemporalLedgerResult(
            REFUSED,
            window_start=None if start is None else start.isoformat(),
            window_end=None if end is None else end.isoformat(),
            reason_codes=_dedup(window_reasons),
        )
    assert start is not None and end is not None

    events = env.get("timeline")
    if not isinstance(events, list):
        return TemporalLedgerResult(
            REFUSED,
            window_start=start.isoformat(),
            window_end=end.isoformat(),
            window_h=_delta_hours_q(start, end),
            reason_codes=(REASON_TIMELINE_NOT_FINITE_LIST,),
        )

    parsed: list[tuple[datetime, str, str]] = []
    reasons: list[str] = []

    for idx, item in enumerate(events):
        if not isinstance(item, dict):
            reasons.append(REASON_INVALID_EVENT)
            continue
        if item.get("verified") is not True:
            reasons.append(REASON_UNVERIFIED_EVENT)
            continue
        mechanism = str(item.get("mechanism", "")).strip()
        event = str(item.get("event", "")).upper().strip()
        at = _parse_time(item.get("at"))
        if mechanism not in MECHANISMS or event not in ALLOWED_EVENTS or at is None:
            reasons.append(REASON_INVALID_EVENT)
            continue
        if mechanism not in covered:
            reasons.append(REASON_EVENT_OUTSIDE_COVERAGE)
            continue
        if at < start or at > end:
            reasons.append(REASON_EVENT_OUTSIDE_WINDOW)
            continue
        parsed.append((at, mechanism, event))

    if reasons:
        return TemporalLedgerResult(
            REFUSED,
            window_start=start.isoformat(),
            window_end=end.isoformat(),
            window_h=_delta_hours_q(start, end),
            reason_codes=_dedup(reasons),
            details={"event_count_declared": len(events), "event_count_valid": len(parsed)},
        )

    parsed.sort(key=lambda x: (x[0], x[1], x[2]))

    by_mechanism: dict[str, list[tuple[datetime, str]]] = {m: [] for m in covered}
    for at, mechanism, event in parsed:
        by_mechanism[mechanism].append((at, event))

    outputs: list[MechanismAccumulation] = []
    transition_errors: list[str] = []

    # concurrency sweep uses verified START/RESOLVED only.
    sweep: list[tuple[datetime, int]] = []

    for mechanism in covered:
        seq = by_mechanism[mechanism]
        left_state = boundary.get(mechanism, "UNKNOWN")
        active_start: Optional[datetime] = start if left_state == "ACTIVE" else None
        cumulative = Fraction(0, 1)
        recurrence = 0
        left_censored = left_state in {"ACTIVE", "UNKNOWN"}
        observed_without_start = left_state == "UNKNOWN"

        if left_state == "ACTIVE":
            # Active at t0 is a finite within-window fact, but the full episode onset lies
            # before/at the left boundary and therefore remains censored.
            sweep.append((start, +1))

        for at, event in seq:
            if event == "START":
                if active_start is not None:
                    transition_errors.append(f"{mechanism}:duplicate_start")
                    continue
                active_start = at
                recurrence += 1
                sweep.append((at, +1))
            elif event == "RESOLVED":
                if active_start is None:
                    transition_errors.append(f"{mechanism}:resolve_without_start")
                    continue
                cumulative += _delta_hours_q(active_start, at)
                active_start = None
                sweep.append((at, -1))
            elif event == "OBSERVED_ACTIVE":
                if active_start is None:
                    # Activity is observed, but onset is not declared. Do not backfill duration.
                    observed_without_start = True
                    left_censored = True
            elif event == "MITIGATION":
                # A mitigation action is not equivalent to resolution.
                pass

        current_episode_h: Optional[Fraction]
        active_at_end: Optional[bool]

        lower_bound_h: Optional[Fraction] = None
        if active_start is not None:
            within_window_episode_h = _delta_hours_q(active_start, end)
            cumulative += within_window_episode_h
            active_at_end = True
            if left_censored:
                current_episode_h = None
                lower_bound_h = within_window_episode_h
            else:
                current_episode_h = within_window_episode_h
        elif observed_without_start:
            current_episode_h = None
            active_at_end = None
        else:
            current_episode_h = None
            active_at_end = False

        # cumulative_h is exact *inside W* when the left boundary is ACTIVE or INACTIVE and
        # the window is certified complete. UNKNOWN left-boundary state with no declared
        # onset cannot produce an exact cumulative duration.
        cumulative_out = None if left_state == "UNKNOWN" else cumulative

        outputs.append(
            MechanismAccumulation(
                mechanism=mechanism,
                cumulative_h=cumulative_out,
                current_episode_h=current_episode_h,
                recurrence_count=recurrence,
                active_at_window_end=active_at_end,
                left_censored=left_censored,
                current_episode_lower_bound_h=lower_bound_h,
            )
        )

    if transition_errors:
        return TemporalLedgerResult(
            REFUSED,
            window_start=start.isoformat(),
            window_end=end.isoformat(),
            window_h=_delta_hours_q(start, end),
            reason_codes=(REASON_INVALID_TRANSITION,),
            details={"transition_errors": transition_errors},
        )

    # If any mechanism is left-censored, only that mechanism's exact cumulative duration is
    # withheld; the finite ledger itself remains valid for mechanisms with complete intervals.
    # Half-open interval semantics [START, RESOLVED): at the same timestamp, close old
    # intervals before opening new ones so concurrency is not inflated by a zero-duration overlap.
    sweep.sort(key=lambda x: (x[0], 0 if x[1] < 0 else 1))
    concurrent = 0
    max_concurrent = 0
    for _, delta in sweep:
        concurrent += delta
        max_concurrent = max(max_concurrent, concurrent)

    active_count = sum(1 for m in outputs if m.active_at_window_end is True)
    left = [m.mechanism for m in outputs if m.left_censored]

    return TemporalLedgerResult(
        OK,
        window_start=start.isoformat(),
        window_end=end.isoformat(),
        window_h=_delta_hours_q(start, end),
        mechanisms=tuple(outputs),
        active_mechanism_count=active_count,
        max_concurrent_mechanisms=max_concurrent,
        reason_codes=((REASON_LEFT_CENSORED,) if left else ()),
        details={
            "event_count": len(parsed),
            "finite_mechanism_count": len(covered),
            "covered_mechanisms": list(covered),
            "left_censored_mechanisms": left,
            "interpretation": (
                "durations are exact within the declared finite complete window only; "
                "they are not toxicity/risk scores and do not describe time before window_start"
            ),
        },
    )


def mechanism(node_result: TemporalLedgerResult, name: str) -> Optional[MechanismAccumulation]:
    for item in node_result.mechanisms:
        if item.mechanism == name:
            return item
    return None
