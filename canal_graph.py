#!/usr/bin/env python3
"""
canal_graph.py -- Toledo PROP-FLOOD-04 ("edge-direction readout for a declared canal
graph from paired gauge levels, with refusal") -- **PROPOSAL, unverified, Toledo PR not
yet opened** (parents: PROP-FLOOD-01's delta_R lag-k retained-difference sign readout,
applied here spatially between two gauge points on one declared canal reach instead of
temporally at one point; see water_balance.py's own PROP-FLOOD-03 docstring for the
sibling proposal this reuses the same discipline from). Do not cite this as a Toledo
theorem until a PR is opened and merged -- track that PR link here once it exists.

    edge (u, v) declared in site/inputs/canals/*.yaml
    delta := h_u - h_v                          (both readings on the SAME datum)
    direction := FORWARD (u->v)   if delta >  epsilon
              := REVERSE (v->u)   if delta < -epsilon
              := UNRESOLVED       if |delta| <= epsilon (within declared sensor resolution)
    status := CONTROLLED (locked) if either endpoint is a floodgate (`is_gate`) whose own
              in/out reading shows out level > in level by more than epsilon -- the gate
              is holding water back, so no direction is asserted from levels at all
    status := REFUSED with reason codes MISSING_INPUT / STALE_INPUT / DATUM_MISMATCH /
              UNDECLARED_EDGE otherwise, matching water_balance.py's own reason-code
              vocabulary and total-outcome discipline (never a guessed direction).

**What this is NOT** (claim_boundary): this is a two-point level-difference readout, not
a hydraulic/routing model -- it says nothing about flow speed/volume, only which of the
two declared endpoints currently reads higher, net of one declared sensor-resolution
epsilon. An edge whose endpoint has no public gauge at all ("ไม่มีเครื่องวัด") NEVER gets a
guessed direction -- it is REFUSED MISSING_INPUT, and the page must show only that
edge's own declared `design_direction` (thin/RELAYED, labelled as such), never a live
reading standing in for it. `epsilon_m` (declared sensor-resolution cutoff) is INSTINCT
(a judgment call on what counts as a resolvable difference at BMA's own 2-decimal-place
publishing precision), not a manufacturer-specified accuracy figure -- see
site/inputs/canals/east_chain.yaml's own `sensor_resolution_m` declaration.

All arithmetic on level readings is carried out on `fractions.Fraction` (Q), never on
`float`, per this workspace's IDM ℚ-computability law -- same discipline as
water_balance.py's `_q()`.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional, Union

Numeric = Union[Fraction, int, float, str]

DIR_FORWARD = "FORWARD"       # u -> v
DIR_REVERSE = "REVERSE"       # v -> u
DIR_UNRESOLVED = "UNRESOLVED"

STATUS_OK = "OK"
STATUS_CONTROLLED = "CONTROLLED"
STATUS_REFUSED = "REFUSED"

REASON_MISSING_INPUT = "MISSING_INPUT"
REASON_STALE_INPUT = "STALE_INPUT"
REASON_DATUM_MISMATCH = "DATUM_MISMATCH"
REASON_UNDECLARED_EDGE = "UNDECLARED_EDGE"

DEFAULT_EPSILON_M = Fraction("0.02")   # declared sensor-resolution cutoff, INSTINCT
DEFAULT_STALE_AFTER_HOURS = 2.0


def _q(x: Optional[Numeric]) -> Optional[Fraction]:
    """Coerce a declared numeric reading to an exact Fraction (Q) -- identical
    discipline/behaviour to water_balance.py's own `_q()` (kept as a separate copy
    rather than a cross-module import so this module has no hard dependency on
    water_balance.py; the two proposals are siblings, not a chain of imports)."""
    if x is None:
        return None
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, str):
        return Fraction(x)
    return Fraction(x).limit_denominator(10**12)


def _hours_between(observed_at_iso: Optional[str], ref_iso: str) -> Optional[float]:
    """Hours from `observed_at_iso` to `ref_iso` (positive = observed_at is in the
    past). None if either timestamp is missing/unparseable -- caller decides how to
    treat that (this module treats "can't tell the age" as NOT stale, matching
    water_balance.py's `_is_stale`, since staleness is a total function only over
    parseable timestamps -- a genuinely missing timestamp is its own MISSING_INPUT
    case, checked separately, never silently folded into STALE_INPUT)."""
    if not observed_at_iso or not ref_iso:
        return None
    try:
        obs = datetime.datetime.fromisoformat(observed_at_iso.replace("Z", "+00:00"))
        ref = datetime.datetime.fromisoformat(ref_iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if obs.tzinfo is None:
        obs = obs.replace(tzinfo=datetime.timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=datetime.timezone.utc)
    return (ref - obs).total_seconds() / 3600.0


def _is_stale(observed_at_iso: Optional[str], ref_iso: str,
              stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS) -> bool:
    hrs = _hours_between(observed_at_iso, ref_iso)
    if hrs is None:
        return False
    return hrs > stale_after_hours


@dataclass
class EdgeResult:
    """Total, first-class outcome for one declared edge, one readout instant. Exactly
    one of (`direction` is not None) or (`status != OK`) holds -- never a direction AND
    a refusal/lock at once, never neither."""
    edge_id: str
    u: str
    v: str
    status: str                       # OK | CONTROLLED | REFUSED
    reason_codes: list = field(default_factory=list)
    direction: Optional[str] = None   # FORWARD | REVERSE | UNRESOLVED (only when status==OK)
    delta_m: Optional[Fraction] = None
    locked_node: Optional[str] = None       # which endpoint's gate is holding, if CONTROLLED
    design_direction: Optional[str] = None  # "u_to_v" | "v_to_u" | "unknown" -- always carried
    design_direction_source: Optional[str] = None
    control_structures: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "edge_id": self.edge_id, "u": self.u, "v": self.v,
            "status": self.status, "reason_codes": list(self.reason_codes),
            "direction": self.direction,
            "delta_m": str(self.delta_m) if self.delta_m is not None else None,
            "locked_node": self.locked_node,
            "design_direction": self.design_direction,
            "design_direction_source": self.design_direction_source,
            "control_structures": list(self.control_structures),
        }


def _gate_locked(node_id: str, node: dict, reading: Optional[dict],
                  epsilon: Fraction) -> bool:
    """True iff `node` is declared a floodgate (`is_gate`) and its own live reading's
    outside level (`canal_out`) exceeds its inside level (`level_m`) by more than
    `epsilon` -- the maintainer's own stated derivation ("ปตร. in/out: out>in =>
    CONTROLLED/locked"). A gate with no `canal_out` reading, or `canal_out in (None, 0)`
    (BMA's convention for "not a two-sided gate reading this tick"), is never treated as
    locked from this signal -- it falls through to the ordinary level-diff path instead."""
    if not node.get("is_gate") or reading is None:
        return False
    g_in = reading.get("level_m")
    g_out = reading.get("canal_out")
    if g_in is None or g_out in (None, 0):
        return False
    return (_q(g_out) - _q(g_in)) > epsilon


def edge_direction(edge: dict, u_node: dict, v_node: dict,
                    u_reading: Optional[dict], v_reading: Optional[dict],
                    ref_iso: str, declared_edges: Optional[set] = None,
                    epsilon_m: Numeric = DEFAULT_EPSILON_M,
                    stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS) -> EdgeResult:
    """One readout of one declared edge. `edge` is one entry from the declared graph's
    `edges` list (see site/inputs/canals/east_chain.yaml); `u_node`/`v_node` are the
    matching entries from `edges`'s `nodes` map; `u_reading`/`v_reading` are the current
    thaiwater canal-station dict for that node's `canal_oldcode` (as built by
    `build_data.py`'s `canal_by_code`), or None if that node has no gauge declared or no
    live row was found for its code today.
    """
    edge_id = edge["edge_id"]
    u_id, v_id = edge["u"], edge["v"]
    design_direction = edge.get("design_direction", "unknown")
    design_direction_source = edge.get("design_direction_source")
    control_structures = edge.get("control_structures") or []
    base = dict(edge_id=edge_id, u=u_id, v=v_id, design_direction=design_direction,
                design_direction_source=design_direction_source,
                control_structures=control_structures)

    if declared_edges is not None and edge_id not in declared_edges:
        return EdgeResult(status=STATUS_REFUSED, reason_codes=[REASON_UNDECLARED_EDGE], **base)

    epsilon = _q(epsilon_m)

    for node_id, node, reading in ((u_id, u_node, u_reading), (v_id, v_node, v_reading)):
        if _gate_locked(node_id, node, reading, epsilon):
            return EdgeResult(status=STATUS_CONTROLLED, locked_node=node_id, **base)

    missing = []
    if not u_node.get("canal_oldcode") or u_reading is None or u_reading.get("level_m") is None:
        missing.append(u_id)
    if not v_node.get("canal_oldcode") or v_reading is None or v_reading.get("level_m") is None:
        missing.append(v_id)
    if missing:
        return EdgeResult(status=STATUS_REFUSED, reason_codes=[REASON_MISSING_INPUT], **base)

    stale = []
    if _is_stale(u_reading.get("observed_at"), ref_iso, stale_after_hours):
        stale.append(u_id)
    if _is_stale(v_reading.get("observed_at"), ref_iso, stale_after_hours):
        stale.append(v_id)
    if stale:
        return EdgeResult(status=STATUS_REFUSED, reason_codes=[REASON_STALE_INPUT], **base)

    if (u_node.get("datum") or "MSL") != (v_node.get("datum") or "MSL"):
        return EdgeResult(status=STATUS_REFUSED, reason_codes=[REASON_DATUM_MISMATCH], **base)

    delta = _q(u_reading["level_m"]) - _q(v_reading["level_m"])
    if abs(delta) <= epsilon:
        direction = DIR_UNRESOLVED
    elif delta > 0:
        direction = DIR_FORWARD
    else:
        direction = DIR_REVERSE

    return EdgeResult(status=STATUS_OK, direction=direction, delta_m=delta, **base)


def compute_all_edges(graph: dict, canal_by_code: dict, ref_iso: str,
                       epsilon_m: Optional[Numeric] = None,
                       stale_after_hours: Optional[float] = None) -> list:
    """Run `edge_direction()` for every edge in a loaded declared graph (the parsed
    contents of site/inputs/canals/east_chain.yaml). Returns a list of `EdgeResult`,
    one per declared edge, in declared order -- never skips an edge, never fabricates
    one not declared."""
    nodes = graph.get("nodes") or {}
    edges = graph.get("edges") or []
    declared_edges = {e["edge_id"] for e in edges}
    eps = _q(epsilon_m) if epsilon_m is not None else _q(
        (graph.get("sensor_resolution_m") or {}).get("value", DEFAULT_EPSILON_M))
    stale_after = stale_after_hours if stale_after_hours is not None else \
        (graph.get("stale_after_hours") or DEFAULT_STALE_AFTER_HOURS)

    out = []
    for edge in edges:
        u_node = nodes.get(edge["u"]) or {}
        v_node = nodes.get(edge["v"]) or {}
        u_reading = canal_by_code.get(u_node.get("canal_oldcode")) if u_node.get("canal_oldcode") else None
        v_reading = canal_by_code.get(v_node.get("canal_oldcode")) if v_node.get("canal_oldcode") else None
        out.append(edge_direction(edge, u_node, v_node, u_reading, v_reading, ref_iso,
                                   declared_edges=declared_edges, epsilon_m=eps,
                                   stale_after_hours=stale_after))
    return out
