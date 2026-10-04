"""Bangkok coping ("repayment") indicator for the BMA plan 2569 section 5.1 table.

NEW DERIVATION / PROPOSAL -- not yet in Toledo. Nothing here is a registered equation.
Every arithmetic step is a reuse of an existing object, named at the point of use:

  * load ratio L = rain / design      -- PROP-FLOOD-08-DRAFT L_H (itself PROP-FLOOD-06
    S_H = F_H / C_H), evaluated per window H with the OWNER-DECLARED design depth for
    that same window (BMA plan 2569 p.63: 58.7 mm in 1 h, 80 mm in 1 day). The 08 draft's
    pro-rating (H/24) * D_design is NOT used: at H = 1 it would give 3.33 mm/h, which
    contradicts the owner's own 1-h figure and crosses durations (forbidden by conversion
    rule R2). See the S51 knowledge card, section 2, and TODO #180.
  * three-state readout               -- D/M.71..76 `classify floor v` by renaming
    v := (lo + hi)/2 - theta, floor := (hi - lo)/2 (same renaming PROP-FLOOD-10-DRAFT C2
    uses). Returns '+' (certain above), '-' (certain below), '0' (exact balance),
    '_|_' (unresolved at this resolution).
  * worst-first per model / gauge     -- conversion rule R8 (PROP-FLOOD-06 v6.1
    multi_model_scenarios): never averaged.
  * verification cells                -- PROP-FLOOD-10-DRAFT delta 10.3 (5 cells,
    UNRESOLVED never counted as a correct negative, skill REFUSED below N_min).

No mm/h <-> mm/24h conversion is ever made here (rules R1/R2). All arithmetic is on
fractions.Fraction (finite rationals) -- no floats enter a comparison.
"""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path

# ---- owner-declared numbers (BMA plan 2569) -- every value tagged VERIFIED at its page --
DESIGN_DEPTH_MM = {
    1: Fraction("58.7"),   # 1-h window, plan p.63 ("ไม่เกิน 58.7 มม./ชม."), = IDF T=2y/1h p.18
    24: Fraction("80"),    # 24-h window, plan p.63 ("ไม่เกิน 80 มม. ใน 1 วัน")
}

# Section 5.1 (plan p.22), rain descriptors in mm/h (1-h window). None = open-ended edge,
# never replaced by infinity (conversion rule R7).
PERIODS = {
    "P1": {"months": (5, 6, 7), "rain_band_mm_h": (Fraction(10), Fraction(60)),
           "rain_abnormal_lo_mm_h": Fraction(90), "stage_msl": (Fraction("1.20"), Fraction("1.20"))},
    "P2": {"months": (8, 9, 10), "rain_band_mm_h": (Fraction(60), Fraction(90)),
           "rain_abnormal_lo_mm_h": Fraction(90), "stage_msl": (Fraction("1.50"), Fraction("1.80"))},
    "P3": {"months": (10, 11, 12), "rain_band_mm_h": (Fraction(90), None),
           "rain_abnormal_lo_mm_h": None, "stage_msl": (Fraction("1.80"), None)},
}
DEFENCE_LINE_MSL = Fraction("2.00")        # plan p.47 (section 9.2.1), VERIFIED
C29B_CRITICAL_M3S = Fraction(3500)         # plan p.22 (unit printed "ล้าน" -- typo), VERIFIED
REACH_NO_OVERBANK_M3S = (Fraction(2500), Fraction(3500))   # plan p.19, VERIFIED

STATES = ("+", "-", "0", "_|_")
REFUSED = "REFUSED"


def _q(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(str(x))


def periods_for_month(month: int) -> list[str]:
    """October sits in BOTH P2 and P3 in the plan's own table -- both are returned,
    never one silently picked."""
    return [p for p, spec in PERIODS.items() if month in spec["months"]]


def classify(floor: Fraction, v: Fraction) -> str:
    """D/M.71..76 `classify` (IDM_ResolvedCount.v), transcribed branch for branch."""
    if floor < v:
        return "+"
    if v < -floor:
        return "-"
    if floor == 0:
        return "0"
    return "_|_"


def three_state(lo, hi, theta) -> str:
    """Interval [lo, hi] against edge theta by the D/M.71..76 renaming.

    hi = None is an open-ended upper edge: the renaming still decides '+' when lo > theta
    (v - floor = lo - theta), otherwise the reading is '_|_' -- no infinity is formed.
    lo = None (unknown lower edge) is REFUSED."""
    if lo is None:
        return REFUSED
    lo, theta = _q(lo), _q(theta)
    if hi is None:
        return "+" if lo > theta else "_|_"
    hi = _q(hi)
    if hi < lo:
        raise ValueError("interval with hi < lo")
    return classify((hi - lo) / 2, (lo + hi) / 2 - theta)


def load_ratio(depth_mm_lo, depth_mm_hi, window_h: int):
    """L over one window, as an interval; REFUSED DESIGN_DEPTH_UNDECLARED when the owner
    has published no design depth for exactly this window (no pro-rating, no R2 bridge)."""
    if window_h not in DESIGN_DEPTH_MM:
        return REFUSED, "DESIGN_DEPTH_UNDECLARED"
    d = DESIGN_DEPTH_MM[window_h]
    lo = None if depth_mm_lo is None else _q(depth_mm_lo) / d
    hi = None if depth_mm_hi is None else _q(depth_mm_hi) / d
    return (lo, hi), None


def borrowing_state(depth_mm_lo, depth_mm_hi, window_h: int) -> str:
    """New borrowing on one window: L against 1 (equivalently depth against the owner's
    design depth for the same window)."""
    ratio, why = load_ratio(depth_mm_lo, depth_mm_hi, window_h)
    if ratio == REFUSED:
        return REFUSED
    return three_state(ratio[0], ratio[1], 1)


def hourly_interval_from_window_total(total_mm):
    """Only a window total is held (no hourly series): the hour of interest lies in
    [0, total] -- a part of a non-negative total is non-negative and not larger than the
    total. This is a bound, not a conversion (it never produces an intensity value)."""
    return Fraction(0), _q(total_mm)


def stage_state(h_msl, period: str, eps=Fraction("0.01")) -> dict:
    """Repayment-capacity readout from a river stage on the MSL datum.

    Edges from plan p.22 (period characteristic level) and p.47 (+2.00 defence line).
    Reading them as 'repayment derated above the period's upper characteristic level' is
    OUR proposal (INSTINCT); only the +2.00 meaning is stated by the owner."""
    if h_msl is None:
        return {"derating": REFUSED, "defence_line": REFUSED}
    h = _q(h_msl)
    lo_edge, hi_edge = PERIODS[period]["stage_msl"]
    edge = hi_edge if hi_edge is not None else lo_edge
    return {
        "derating": three_state(h - eps, h + eps, edge),
        "defence_line": three_state(h - eps, h + eps, DEFENCE_LINE_MSL),
    }


def composite_state(borrow: str, inbound: str, derating: str) -> str:
    """Debt readout for one unit/window.

    '+' if new borrowing or booked inbound is certain; derating alone never makes debt
    certain (the derating factor eta is ABSENT, 08-DRAFT) -- it turns a '-' borrowing
    reading into '_|_' (capacity below rated by an undeclared amount), because with
    eta unknown the upper end of L is not bounded (reported as unresolved, never inf).
    inbound: '+', '-', '_|_', REFUSED (term listed but no feed) or 'NA' (not listed)."""
    # inbound 'NA' = the owner's table lists no inbound term for this period (P1/P2):
    # treated as no inbound by declaration (INSTINCT reading of plan p.22, flagged).
    if "+" in (borrow, inbound):
        return "+"
    if borrow == REFUSED:
        return REFUSED
    if inbound == REFUSED or "_|_" in (borrow, inbound):
        return "_|_"
    if derating in ("+", "_|_"):
        return "_|_"
    return borrow  # '-' or '0'


def score(issued: str, truth) -> str:
    """Delta 10.3 cell. truth: True (flooded), False (verified not flooded), None
    (unknown/uncertain). '_|_', '0' and REFUSED issue states are UNRESOLVED, never CN."""
    if truth is None or issued not in ("+", "-"):
        return "UNRESOLVED"
    if issued == "+":
        return "HIT" if truth else "FALSE_ALARM"
    return "MISS" if truth else "CORRECT_NEG"


def lead_ticks(t_cross_h, t_onset_h):
    """Lead in integer 1-h ticks (onset minus crossing). Either side None -> None."""
    if t_cross_h is None or t_onset_h is None:
        return None
    return int(t_onset_h - t_cross_h)


def skill_guard(n_independent: int, n_min: int) -> str:
    return "REFUSED FEW_EVENTS" if n_independent < n_min else "OK"


# ---------------------------------------------------------------------------------------
def summarise(path: Path) -> int:
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    n_min = doc["scoring"]["n_min_proposal"]
    bad = 0
    tally = {}
    for ev in doc["events"]:
        for r in ev.get("readouts", []):
            if r.get("scored") is False:
                continue
            want = score(r["issued_state"], ev["truth"]["flooded"])
            if want != r["cell"]:
                bad += 1
                print(f"MISMATCH {ev['event_id']} {r['axis']}/{r['input']}: file={r['cell']} recomputed={want}")
            key = (r["axis"], r["input"])
            tally.setdefault(key, {}).setdefault(r["cell"], set()).add(ev["independence_group"])
    for (axis, inp), cells in sorted(tally.items()):
        resolved = set().union(*[g for c, g in cells.items() if c != "UNRESOLVED"] or [set()])
        print(f"{axis:<10} {inp:<10} " + "  ".join(f"{c}={len(g)}" for c, g in sorted(cells.items()))
              + f"  | independent resolved={len(resolved)} -> {skill_guard(len(resolved), n_min)}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--summarise", type=Path, help="events YAML to re-score and tally")
    a = ap.parse_args(argv)
    if a.summarise:
        return summarise(a.summarise)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
