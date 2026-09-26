#!/usr/bin/env python3
"""
burden_ledger.py -- Toledo PROP-FLOOD-05a/PROP-FLOOD-05b ("control-structure burden
readout from declared gate state and gauged head asymmetry, with refusal" / "zone
net-relief count ordering readout from boundary burden readouts, with no-order and
not-evaluable refusal") -- **PROPOSALS, unverified, Toledo PR #62 (not yet merged)**:
`registry/proposals/flood_burden_ledger.json` in the `toledo` repo, read at commit
1578b35. Do not cite either object as a Toledo theorem until that PR merges.

PROP-FLOOD-05a: `structure_burden()` -- for one declared control structure c between
side A (upstream/inside) and side B (downstream/outside), read a level asymmetry as
BURDENED (higher gauged side)/RELIEVED (lower gauged side) whenever the structure's own
declared control state g_c(t) is CLOSED or PUMPING (free exchange declared blocked or
overridden); GRADIENT_ONLY (defer to PROP-FLOOD-04, canal_graph.py) when g_c(t)=OPEN;
UNRESOLVED when the asymmetry is not distinguishable from zero at the combined
resolution; REFUSED with a fixed precedence otherwise. `persistence()` is a NEW
construction of this proposal: the count of consecutive ticks ending at the latest tick
during which the SAME side read HIGHER_SIDE.

PROP-FLOOD-05b: `zone_order()` -- for a declared zone Z with a declared finite boundary
set dZ, count R(Z)/B(Z) (boundaries whose Z-side currently reads RELIEVED/BURDENED;
GRADIENT_ONLY and UNRESOLVED boundaries are declared NEUTRAL, counted toward neither),
sum the persistence-weighted tie-break SigmaP_rel(Z)-SigmaP_bur(Z), and dense-rank
zones descending by (R-B, SigmaP_rel-SigmaP_bur). A zone with an undeclared/empty
boundary set is NOT_EVALUABLE; a zone with any REFUSED boundary is NO_ORDER; ties are
never broken by name/id.

**What this is NOT** (claim_boundary, copied from the registered proposal so it is
never silently dropped): this is a readout of declared gate state and gauged levels at
one tick, not a claim about intent, fault, engineering-design merit, or fairness. No
hydraulic flow-rate, discharge, or volume estimate is asserted. Tide can produce the
same measured asymmetry a control structure would show when actively closed; this
construction never distinguishes the two by itself -- the declared control state g_c(t)
is what licenses the CLOSED/PUMPING branch at all. R(Z)-B(Z) is a signed count of
readout classes, never a magnitude/capacity-weighted assessment, and must never be
reported as a standalone index without also reporting R(Z) and B(Z) themselves.

All arithmetic on level readings is carried out on `fractions.Fraction` (Q), never on
`float`, per this workspace's IDM ℚ-computability law -- same discipline as
canal_graph.py's/water_balance.py's own `_q()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Optional, Union

Numeric = Union[Fraction, int, float, str]

STATE_OPEN = "OPEN"
STATE_CLOSED = "CLOSED"
STATE_PUMPING_A_TO_B = "PUMPING(A->B)"
STATE_PUMPING_B_TO_A = "PUMPING(B->A)"
PUMPING_STATES = (STATE_PUMPING_A_TO_B, STATE_PUMPING_B_TO_A)

RESULT_GRADIENT_ONLY = "GRADIENT_ONLY"
RESULT_UNRESOLVED = "UNRESOLVED"
RESULT_REFUSED = "REFUSED"
RESULT_DETERMINATE = "DETERMINATE"  # (HIGHER_SIDE, LOWER_SIDE) pair

REASON_UNDECLARED_STRUCTURE = "UNDECLARED_STRUCTURE"
REASON_MISSING_INPUT = "MISSING_INPUT"
REASON_STALE_INPUT = "STALE_INPUT"
REASON_DATUM_MISMATCH = "DATUM_MISMATCH"
REASON_CONTROL_STATE_MISSING = "CONTROL_STATE_MISSING"

SIDE_A = "A"
SIDE_B = "B"

DEFAULT_EPSILON_M = Fraction("0.02")  # per-gauge resolution, INSTINCT (matches canal_graph.py)


def _q(x: Optional[Numeric]) -> Optional[Fraction]:
    """Coerce a declared numeric reading to an exact Fraction (Q) -- identical
    discipline to canal_graph.py's/water_balance.py's own `_q()` (kept as a separate
    copy rather than a cross-module import, same posture as canal_graph.py's own
    docstring gives for its relationship to water_balance.py)."""
    if x is None:
        return None
    if isinstance(x, Fraction):
        return x
    if isinstance(x, int):
        return Fraction(x)
    if isinstance(x, str):
        return Fraction(x)
    return Fraction(x).limit_denominator(10**12)


@dataclass
class BurdenResult:
    """Total, first-class outcome for one declared control structure, one readout
    instant. Exactly one of {GRADIENT_ONLY, UNRESOLVED, REFUSED, DETERMINATE} holds."""
    structure_id: str
    result: str                       # GRADIENT_ONLY | UNRESOLVED | REFUSED | DETERMINATE
    reason_codes: list = field(default_factory=list)
    state: Optional[str] = None       # the declared g_c(t) that licensed this readout, if known
    higher_side: Optional[str] = None    # SIDE_A | SIDE_B (only when result == DETERMINATE)
    lower_side: Optional[str] = None     # SIDE_A | SIDE_B (only when result == DETERMINATE)
    a_c: Optional[Fraction] = None    # h_A - h_B, when both inputs were readable

    @property
    def burdened_side(self) -> Optional[str]:
        """BURDENED is a term of art for HIGHER_SIDE (defined only under DETERMINATE)."""
        return self.higher_side if self.result == RESULT_DETERMINATE else None

    @property
    def relieved_side(self) -> Optional[str]:
        """RELIEVED is a term of art for LOWER_SIDE (defined only under DETERMINATE)."""
        return self.lower_side if self.result == RESULT_DETERMINATE else None

    def as_dict(self) -> dict:
        return {
            "structure_id": self.structure_id, "result": self.result,
            "reason_codes": list(self.reason_codes), "state": self.state,
            "higher_side": self.higher_side, "lower_side": self.lower_side,
            "burdened_side": self.burdened_side, "relieved_side": self.relieved_side,
            "a_c": str(self.a_c) if self.a_c is not None else None,
        }


def structure_burden(structure_id: str, h_A: Optional[Numeric], h_B: Optional[Numeric],
                      eps_A: Numeric, eps_B: Numeric, state: Optional[str],
                      *, declared: bool = True, datum_a: Optional[str] = None,
                      datum_b: Optional[str] = None, stale_a: bool = False,
                      stale_b: bool = False) -> BurdenResult:
    """One readout of one declared control structure `structure_id`, at one tick.

    `h_A`, `h_B`: Q-valued gauged levels on sides A (upstream/inside) and B
    (downstream/outside), already caller-verified to be within their own declared
    staleness windows if `stale_a`/`stale_b` are False (this function does not itself
    know a timestamp -- staleness is a caller-computed boolean per PROP-FLOOD-05a's own
    definition of h_A/h_B, matching canal_graph.py's `_is_stale` split of "compute
    staleness" from "act on it").
    `state`: the declared control state g_c(t) in {OPEN, CLOSED, PUMPING(A->B),
    PUMPING(B->A)}, or None/"" if missing/stale -- a missing state is
    CONTROL_STATE_MISSING, never silently treated as OPEN.
    `declared`: False iff `structure_id` is not itself a declared structure at all
    (UNDECLARED_STRUCTURE, checked before any input is read).

    Refusal rows are checked BEFORE gate-state rows, in this fixed precedence, exactly
    as registered: UNDECLARED_STRUCTURE, MISSING_INPUT/STALE_INPUT, DATUM_MISMATCH,
    CONTROL_STATE_MISSING; only once none of those fire does the gate-state branch run.
    """
    if not declared:
        return BurdenResult(structure_id, RESULT_REFUSED,
                             reason_codes=[REASON_UNDECLARED_STRUCTURE])

    if h_A is None or h_B is None:
        return BurdenResult(structure_id, RESULT_REFUSED,
                             reason_codes=[REASON_MISSING_INPUT])

    if stale_a or stale_b:
        return BurdenResult(structure_id, RESULT_REFUSED,
                             reason_codes=[REASON_STALE_INPUT])

    if (datum_a or "MSL") != (datum_b or "MSL"):
        return BurdenResult(structure_id, RESULT_REFUSED,
                             reason_codes=[REASON_DATUM_MISMATCH])

    if not state:
        return BurdenResult(structure_id, RESULT_REFUSED,
                             reason_codes=[REASON_CONTROL_STATE_MISSING])

    a_c = _q(h_A) - _q(h_B)

    if state == STATE_OPEN:
        return BurdenResult(structure_id, RESULT_GRADIENT_ONLY, state=state, a_c=a_c)

    if state not in (STATE_CLOSED,) + PUMPING_STATES:
        # An undeclared/unknown state value is itself a CONTROL_STATE_MISSING case --
        # never guessed into OPEN or CLOSED.
        return BurdenResult(structure_id, RESULT_REFUSED,
                             reason_codes=[REASON_CONTROL_STATE_MISSING])

    eps_sum = _q(eps_A) + _q(eps_B)
    if abs(a_c) <= eps_sum:
        return BurdenResult(structure_id, RESULT_UNRESOLVED, state=state, a_c=a_c)

    if a_c > eps_sum:
        return BurdenResult(structure_id, RESULT_DETERMINATE, state=state, a_c=a_c,
                             higher_side=SIDE_A, lower_side=SIDE_B)

    return BurdenResult(structure_id, RESULT_DETERMINATE, state=state, a_c=a_c,
                         higher_side=SIDE_B, lower_side=SIDE_A)


def persistence(history_higher_sides: list) -> int:
    """P_c(k) := the count of consecutive ticks ending at the LAST entry of
    `history_higher_sides` during which the SAME side was read HIGHER_SIDE. Each entry
    of `history_higher_sides` is the `higher_side` (SIDE_A/SIDE_B) of a DETERMINATE
    readout at that tick, or None for any tick that was GRADIENT_ONLY/UNRESOLVED/
    REFUSED (which resets the count, matching honest_caveats: "reset whenever the
    higher side changes, the gate state moves to OPEN, or the tick is
    REFUSED/UNRESOLVED"). An empty list, or a list whose last entry is None, has
    persistence 0 (no HIGHER_SIDE readout to persist)."""
    if not history_higher_sides or history_higher_sides[-1] is None:
        return 0
    current = history_higher_sides[-1]
    count = 0
    for side in reversed(history_higher_sides):
        if side != current:
            break
        count += 1
    return count


NOT_EVALUABLE = "NOT_EVALUABLE"
NO_ORDER = "NO_ORDER"


def zone_order(zones: dict, readouts: dict) -> dict:
    """PROP-FLOOD-05b's `result(Z,t)`.

    `zones`: {zone_id: {"boundaries": [(structure_id, side_of_Z), ...]}} -- the declared
    finite boundary set dZ for each zone, `side_of_Z` in {SIDE_A, SIDE_B} naming which
    side of that structure belongs to this zone (from the declared zeta map). A zone
    with an empty or missing `boundaries` list is NOT_EVALUABLE.
    `readouts`: {structure_id: (BurdenResult, persistence_count)} -- PROP-FLOOD-05a's
    own readout plus its P_c(k) for every structure referenced by any zone's boundaries.
    A structure referenced by a zone but absent from `readouts` is treated as REFUSED
    (MISSING_INPUT is the caller's concern; here it is simply "no readout available",
    which forces NO_ORDER on that zone exactly like an explicit REFUSED would).

    Returns {"ranked": [{"zone_id", "rank", "R", "B", "sigma_p_rel", "sigma_p_bur",
    "net": (r_minus_b, sigma_diff)}], "no_order": [{"zone_id", "reasons": [...]}],
    "not_evaluable": [zone_id, ...]}. Dense rank: ties share one rank value, the next
    distinct net value continues at exactly rank+1. Ties are never broken by zone
    name/id or any criterion outside the declared net(Z,t) tuple -- Python's sort is
    stable, so among exact ties the declared iteration order of `zones` is preserved,
    never re-ordered by name."""
    not_evaluable = []
    no_order = []
    evaluable = []  # (zone_id, R, B, sigma_p_rel, sigma_p_bur)

    for zone_id, zdef in zones.items():
        boundaries = (zdef or {}).get("boundaries") or []
        if not boundaries:
            not_evaluable.append(zone_id)
            continue

        refused_reasons = []
        R = B = 0
        sigma_p_rel = sigma_p_bur = 0

        for structure_id, side_of_zone in boundaries:
            entry = readouts.get(structure_id)
            if entry is None:
                refused_reasons.append(f"{structure_id}: REFUSED (no readout available)")
                continue
            res, p_c = entry
            if res.result == RESULT_REFUSED:
                refused_reasons.append(
                    f"{structure_id}: REFUSED ({','.join(res.reason_codes)})")
                continue
            if res.result in (RESULT_GRADIENT_ONLY, RESULT_UNRESOLVED):
                continue  # declared NEUTRAL -- contributes to neither R nor B
            # DETERMINATE
            if res.relieved_side == side_of_zone:
                R += 1
                sigma_p_rel += p_c
            elif res.burdened_side == side_of_zone:
                B += 1
                sigma_p_bur += p_c

        if refused_reasons:
            no_order.append({"zone_id": zone_id, "reasons": refused_reasons})
            continue

        evaluable.append((zone_id, R, B, sigma_p_rel, sigma_p_bur))

    # Dense rank descending by net = (R-B, sigma_p_rel - sigma_p_bur).
    evaluable_sorted = sorted(
        evaluable, key=lambda e: (e[1] - e[2], e[3] - e[4]), reverse=True)

    ranked = []
    rank = 0
    prev_net = None
    for zone_id, R, B, sigma_p_rel, sigma_p_bur in evaluable_sorted:
        net = (R - B, sigma_p_rel - sigma_p_bur)
        if net != prev_net:
            rank += 1
            prev_net = net
        ranked.append({
            "zone_id": zone_id, "rank": rank, "R": R, "B": B,
            "sigma_p_rel": sigma_p_rel, "sigma_p_bur": sigma_p_bur, "net": net,
        })

    return {"ranked": ranked, "no_order": no_order, "not_evaluable": not_evaluable}
