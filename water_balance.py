#!/usr/bin/env python3
"""
water_balance.py -- finite water-balance readout for one basin node, one tick.

Implements Toledo PROP-FLOOD-03 ("Finite water-balance readout for a bounded basin over
one tick, with refusal") EXACTLY as registered in the proposal JSON reviewed for this
work: `registry/proposals/flood_water_balance.json` in the `toledo` repo, open as
Toledo PR https://github.com/morrocwi/toledo/pull/60 -- **proposal, unverified, PR
pending**. Do not cite this as a Toledo theorem until that PR merges and the object's
tier/status change from "unverified"/"Dr" to something the registry itself marks settled.

    S_b(k+1) := S_b(k) + P(k)*A_b*c_b + Q_in(k)*tau - Q_out(k)*tau

    Q_out(k) := 0                                  if gate_flag(k) == CLOSED
              := min(Q_out_meas(k), C_pump_b)       if gate_flag(k) == OPEN

All arithmetic is carried out on `fractions.Fraction` (Q), never on `float`, per this
workspace's ℚ-computability law (a "computed" number must carry a finite base-b or ℚ
representation, never a silently-rounded float) -- see IDM ℚ-computability law.

This module composes with, but does not re-derive, Toledo PROP-FLOOD-01 (lag-k
retained-difference sign readout: RISING/FLAT/FALLING/NO_READOUT). The `trend` field
this module's `step()` returns is exactly PROP-FLOOD-01's construction applied, at
lag k=1 tick, to this module's own output series S_b -- see PROP-FLOOD-03's
`readout_classes.trend` field in the registered proposal for the precise statement.

**What this is NOT** (claim_boundary, copied from the registered proposal so it is never
silently dropped): this is bookkeeping of DECLARED readouts, not a hydraulic model. No
routing time between basin nodes is modelled, no infiltration/evaporation model beyond
the single declared scalar `c` is asserted, and no level<->volume (stage-storage) curve
is implied or provided. Converting S_b to a water level at a house or road requires a
separately declared stage-storage relation this module does not provide -- that
conversion is OPEN. An inflow arriving over an undeclared edge is REFUSED
(UNDECLARED_EDGE), never folded silently into the inflow sum as zero. `c` (runoff
fraction) is INSTINCT (a judgment call, not a checked fact) until measured against real
rainfall-runoff data for the declared catchment.

Every refusal is a total, first-class outcome -- never a defaulted or clamped numeric
value. REFUSED reason codes: MISSING_INPUT, STALE_INPUT, UNDECLARED_AREA,
UNDECLARED_EDGE, NEGATIVE_STORAGE.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional, Union

Numeric = Union[Fraction, int, float, str]


def _q(x: Optional[Numeric]) -> Optional[Fraction]:
    """Coerce a declared numeric input to an exact Fraction (Q). `float` is accepted at
    the boundary (most real-world readouts arrive as float/JSON-number) but is converted
    via `Fraction(str(x))`-style exactness is not guaranteed for float -- callers that
    care about exactness should pass `str`/`int`/`Fraction` directly, never a bare float
    literal that already lost precision before it reached this module. `None` stays
    `None` (a missing declaration), never coerced to 0."""
    if x is None:
        return None
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, str):
        return Fraction(x)
    # float: go through repr to avoid binary-float noise beyond what the float itself
    # already carries; this is still ℚ (every float IS a rational number), just not
    # necessarily the "nice" decimal the caller intended -- documented above.
    return Fraction(x).limit_denominator(10**12)


REASON_MISSING_INPUT = "MISSING_INPUT"
REASON_STALE_INPUT = "STALE_INPUT"
REASON_UNDECLARED_AREA = "UNDECLARED_AREA"
REASON_UNDECLARED_EDGE = "UNDECLARED_EDGE"
REASON_NEGATIVE_STORAGE = "NEGATIVE_STORAGE"

TREND_RISING = "RISING"
TREND_FALLING = "FALLING"
TREND_FLAT = "FLAT"


@dataclass
class InflowEdge:
    """One declared upstream inflow edge into basin node b. `edge_id` must match a
    declared edge for the node (see `WaterBalanceInputs.declared_edges`) or the whole
    tick is REFUSED UNDECLARED_EDGE -- an inflow is never silently treated as zero just
    because its edge was not declared."""
    edge_id: str
    q_in: Optional[Numeric]          # m^3/s, time-varying
    observed_at: Optional[str] = None  # ISO8601 timestamp of this edge's reading


@dataclass
class WaterBalanceInputs:
    """One tick's worth of declared inputs for basin node `node_id`, per Toledo
    PROP-FLOOD-03. Every field is a DECLARATION -- a missing/undeclared one causes a
    total REFUSED outcome, never a silent default.

    Static declarations (A, c, C_pump, tau): only ever MISSING_INPUT / UNDECLARED_AREA,
    never STALE_INPUT (no per-tick timestamp to go stale against).
    Time-varying inputs (P, Q_in edges, Q_out_meas, gate_flag): STALE_INPUT if their own
    `observed_at` is older than `stale_after_hours` relative to `tick_time`, or
    MISSING_INPUT if absent.
    """
    node_id: str
    tick_index: int
    tick_time: str                      # ISO8601 timestamp this tick is evaluated "as of"

    S0: Optional[Numeric] = None        # required declared initial storage, m^3 (tick 0 only)
    A: Optional[Numeric] = None         # catchment area, m^2 (static)
    c: Optional[Numeric] = None         # runoff fraction in [0,1] (static, INSTINCT)
    tau: Optional[Numeric] = None       # tick length, s (static)
    C_pump: Optional[Numeric] = None    # declared pump/drainage capacity, m^3/s (static)

    P: Optional[Numeric] = None                 # rain depth over the tick, m
    P_observed_at: Optional[str] = None
    inflow_edges: list = field(default_factory=list)   # list[InflowEdge], declared readings only
    declared_edges: set = field(default_factory=set)    # set[str] of edge_ids this node accepts
    Q_out_meas: Optional[Numeric] = None        # measured outflow, m^3/s
    Q_out_observed_at: Optional[str] = None
    gate_flag: Optional[str] = None             # "OPEN" | "CLOSED"
    gate_flag_observed_at: Optional[str] = None

    stale_after_hours: float = 2.0

    def _is_stale(self, observed_at: Optional[str]) -> bool:
        if observed_at is None:
            return False  # absence is MISSING_INPUT territory, checked separately
        try:
            obs = datetime.datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
            tick = datetime.datetime.fromisoformat(self.tick_time.replace("Z", "+00:00"))
        except ValueError:
            return False
        if obs.tzinfo is None:
            obs = obs.replace(tzinfo=datetime.timezone.utc)
        if tick.tzinfo is None:
            tick = tick.replace(tzinfo=datetime.timezone.utc)
        age_hours = (tick - obs).total_seconds() / 3600.0
        return age_hours > self.stale_after_hours


@dataclass
class StepResult:
    """Total, first-class outcome of one `step()` call. Exactly one of
    (`S_next` is not None) or (`refused` is True) holds -- never a numeric value AND a
    refusal at once, and never neither."""
    node_id: str
    tick_index: int
    refused: bool
    reason_codes: list          # list[str], empty when not refused
    S_next: Optional[Fraction] = None
    increment: Optional[Fraction] = None
    trend: Optional[str] = None
    inputs_present: list = field(default_factory=list)
    inputs_missing: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "tick_index": self.tick_index,
            "status": "REFUSED" if self.refused else "OK",
            "reason_codes": list(self.reason_codes),
            "S_next": str(self.S_next) if self.S_next is not None else None,
            "increment": str(self.increment) if self.increment is not None else None,
            "trend": self.trend,
            "inputs_present": list(self.inputs_present),
            "inputs_missing": list(self.inputs_missing),
        }


def step(inp: WaterBalanceInputs, S_prev: Optional[Numeric] = None,
         prev_increment: Optional[Numeric] = None,
         trend_epsilon: Numeric = Fraction(0)) -> StepResult:
    """One tick of Toledo PROP-FLOOD-03. `S_prev` is the previous tick's stored volume
    (m^3); pass `None` (with `inp.S0` set) only for the very first tick of a chain, or
    for the first tick after a REFUSED gap (a fresh declared restart, never an
    extrapolation across the gap -- see the registered proposal's honest_caveats).

    Returns a `StepResult` that is REFUSED with one or more reason codes, or carries a
    computed `S_next`/`increment`/`trend` -- never both, never neither.
    """
    present: list = []
    missing: list = []
    reasons: list = []

    def require(name: str, value, observed_at=None, static=False):
        if value is None:
            missing.append(name)
            reasons.append(REASON_MISSING_INPUT)
            return None
        present.append(name)
        if not static and observed_at is not None and inp._is_stale(observed_at):
            reasons.append(REASON_STALE_INPUT)
        return value

    # --- static declarations -------------------------------------------------------
    A = require("A", inp.A, static=True)
    c = require("c", inp.c, static=True)
    tau = require("tau", inp.tau, static=True)
    C_pump = require("C_pump", inp.C_pump, static=True)

    if inp.A is None:
        # UNDECLARED_AREA is the more specific reason for a missing catchment area;
        # MISSING_INPUT was already appended by require() above -- add the specific one too.
        reasons.append(REASON_UNDECLARED_AREA)

    # --- initial storage (tick 0 of a chain only) -----------------------------------
    if S_prev is None:
        S_prev_val = require("S0", inp.S0, static=True)
    else:
        present.append("S_prev")
        S_prev_val = S_prev

    # --- time-varying inputs ---------------------------------------------------------
    P = require("P", inp.P, observed_at=inp.P_observed_at)
    gate_flag = require("gate_flag", inp.gate_flag, observed_at=inp.gate_flag_observed_at)
    Q_out_meas = require("Q_out_meas", inp.Q_out_meas, observed_at=inp.Q_out_observed_at)

    # --- inflow edges: sum only declared edges; an inflow over an undeclared edge is
    # a hard REFUSED, never an implicit zero.
    Q_in_total = Fraction(0)
    any_inflow_present = False
    for edge in inp.inflow_edges:
        if edge.edge_id not in inp.declared_edges:
            reasons.append(REASON_UNDECLARED_EDGE)
            missing.append(f"edge:{edge.edge_id}")
            continue
        if edge.q_in is None:
            missing.append(f"edge:{edge.edge_id}")
            reasons.append(REASON_MISSING_INPUT)
            continue
        if edge.observed_at is not None and inp._is_stale(edge.observed_at):
            reasons.append(REASON_STALE_INPUT)
        Q_in_total += _q(edge.q_in)
        present.append(f"edge:{edge.edge_id}")
        any_inflow_present = True
    if inp.declared_edges and not inp.inflow_edges:
        # edges were declared for this node but none supplied this tick
        missing.append("Q_in")
        reasons.append(REASON_MISSING_INPUT)

    if reasons:
        # de-duplicate while preserving first-seen order
        seen = []
        for r in reasons:
            if r not in seen:
                seen.append(r)
        return StepResult(node_id=inp.node_id, tick_index=inp.tick_index, refused=True,
                           reason_codes=seen, inputs_present=present, inputs_missing=missing)

    # --- everything required is present and fresh: compute -------------------------
    A_f, c_f, tau_f, C_pump_f = _q(A), _q(c), _q(tau), _q(C_pump)
    P_f = _q(P)
    S_prev_f = _q(S_prev_val)

    if gate_flag == "CLOSED":
        Q_out = Fraction(0)
    else:
        Q_out = min(_q(Q_out_meas), C_pump_f)

    increment = P_f * A_f * c_f + Q_in_total * tau_f - Q_out * tau_f
    S_next = S_prev_f + increment

    if S_next < 0:
        return StepResult(node_id=inp.node_id, tick_index=inp.tick_index, refused=True,
                           reason_codes=[REASON_NEGATIVE_STORAGE],
                           inputs_present=present, inputs_missing=missing)

    trend = TREND_FLAT
    if prev_increment is not None:
        eps = _q(trend_epsilon) or Fraction(0)
        diff = increment - _q(prev_increment)
        if diff > eps:
            trend = TREND_RISING
        elif diff < -eps:
            trend = TREND_FALLING
    else:
        eps = _q(trend_epsilon) or Fraction(0)
        if increment > eps:
            trend = TREND_RISING
        elif increment < -eps:
            trend = TREND_FALLING

    return StepResult(node_id=inp.node_id, tick_index=inp.tick_index, refused=False,
                       reason_codes=[], S_next=S_next, increment=increment, trend=trend,
                       inputs_present=present, inputs_missing=missing)
