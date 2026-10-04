"""prop_flood_06.py -- PROP-FLOOD-06 PROPOSAL, unverified.

Pure-function implementation of the area-generic outlet-headroom / drainage-coping
tier-ladder indicator specified in the Toledo proposal
toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md
(registry entry: registry/proposals/flood_outlet_coping.json, tier Dr, status unverified).

This module implements the proposal AS WRITTEN, for falsifier-loop testing only, per
this repo's Toledo rule ("you may IMPLEMENT a registered PROPOSAL for testing as long as
every output says PROP-FLOOD-06 PROPOSAL, unverified"). It is NOT registered as a Toledo
theorem and must never be cited as one.

No network calls, no file I/O, no pandas -- pure arithmetic over plain dicts/lists so the
whole backtest (200+ unit-days x 2 c-values x 2 pump-scenarios x 2 horizons) stays cheap
and inspectable.

All refusal codes, thresholds, and the fixed precedence order are copied verbatim from
the proposal text; the five tier thresholds (0.3/0.6/0.9/1.2 on S_H; 6h/24h/48h on
T_act) are the proposal's own OPEN-for-founder-tuning convention, not re-derived here.
"""
from __future__ import annotations
from fractions import Fraction

PROPOSAL_TAG = "PROP-FLOOD-06 PROPOSAL, unverified"

REFUSAL_PRECEDENCE = [
    "UNIT_NOT_DECLARED",
    "UNIT_POLYGON_MISSING",
    "OUTLET_CAPACITY_UNKNOWN",
    "NO_GAUGE_IN_UNIT",
    "MISSING_INPUT",
    "STALE_INPUT",
    "UNDECLARED_AREA",
    "UNDECLARED_EDGE",
    "ZERO_CAPACITY_NONZERO_INFLOW",
]


class Refused(Exception):
    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(f"REFUSED({code}): {detail}")


def compute_R_H(outlets, H_hours):
    """R_H(U) = sum over outlets o of max(0, Q_cap,o - Q_o,now) * H * 3600 (m3).

    outlets: list of dicts {Q_cap_o: Fraction|None, Q_o_now: Fraction|None, credible: bool}
    Raises Refused(OUTLET_CAPACITY_UNKNOWN) if any outlet's Q_cap_o is None.
    Raises Refused(MISSING_INPUT) if any outlet's Q_o_now is None or not credible.
    """
    if not outlets:
        raise Refused("UNIT_NOT_DECLARED", "no outlet declared")
    total = Fraction(0)
    per_outlet = []
    for o in outlets:
        if o.get("Q_cap_o") is None:
            raise Refused("OUTLET_CAPACITY_UNKNOWN", o.get("element_th", "outlet"))
        if o.get("Q_o_now") is None or not o.get("credible", True):
            raise Refused("MISSING_INPUT", f"Q_o,now not credible for {o.get('element_th','outlet')}")
        margin = max(Fraction(0), o["Q_cap_o"] - o["Q_o_now"])
        r_o = margin * H_hours * 3600
        per_outlet.append({"element_th": o.get("element_th"), "R_o": r_o})
        total += r_o
    return total, per_outlet


def compute_D_H(P_run_m3s, H_hours, g=Fraction(1)):
    """D_H(U) = sum_t (sum running pump capacity) * 3600 * g_U(t). g constant=1 (OPEN
    default per proposal) unless a tide/gravity condition is declared -- none declared
    in this backtest, flagged.
    """
    if P_run_m3s == 0:
        return Fraction(0), True  # NO_PUMPS_IN_UNIT / pumps-0 scenario -- not a refusal
    return Fraction(P_run_m3s) * H_hours * 3600 * g, False


def compute_F_H(c_U, A_U_km2, rain_mm_series, Q_in_up_m3s_series, H_hours):
    """F_H(U) = c_U * A_U * sum(rain_t) + sum(Q_in,up(t) * 3600).

    rain_mm_series: list of hourly rain (mm) over the horizon.
    Q_in_up_m3s_series: list of hourly (or held-constant daily) upstream discharge (m3/s).
    A_U in km2 -> m2 (*1e6); rain in mm -> m (*1e-3).
    """
    if len(rain_mm_series) < H_hours:
        raise Refused("MISSING_INPUT", "rain series shorter than horizon")
    A_m2 = Fraction(A_U_km2) * 1_000_000
    rain_sum_m = sum(Fraction(str(r)) for r in rain_mm_series[:H_hours]) * Fraction(1, 1000)
    runoff_term = Fraction(str(c_U)) * A_m2 * rain_sum_m
    if Q_in_up_m3s_series is None:
        upstream_term = Fraction(0)
    else:
        upstream_term = sum(Fraction(str(q)) * 3600 for q in Q_in_up_m3s_series[:H_hours])
    return runoff_term + upstream_term, runoff_term, upstream_term


def compute_T_act(F_hourly_cumfn, DR_min_m3, H_hours):
    """T_act(U) = min{t in 1..H : F_t(U) >= min(D_t,R_t)} else '>H'.

    F_hourly_cumfn(t) -> cumulative forecast inflow volume (m3) through hour t.
    DR_min_m3: the (held-constant-through-horizon, per this backtest's INSTINCT
    approximation) min(D_H,R_H) capacity ceiling, pro-rated linearly to hour t.
    """
    if DR_min_m3 == 0:
        return 1 if F_hourly_cumfn(1) > 0 else ">H"
    for t in range(1, H_hours + 1):
        cap_t = DR_min_m3 * Fraction(t, H_hours)
        if F_hourly_cumfn(t) >= cap_t:
            return t
    return f">{H_hours}"


def tier_ladder(S_H, T_act, H_hours):
    """Tiers L0..L5 per the proposal's table (combines S_H and T_act, higher governs).
    L5 pre-check (capacity already 0 and pumps not running, or level already above
    threshold) is NOT implemented here -- no credible "already above threshold" input
    exists in this backtest (see docs/BACKTEST_PROP_FLOOD_06_v0.md limitations); this is
    an explicit gap, not a silent omission.
    """
    def s_level(s):
        if s < Fraction(3, 10):
            return 0
        if s < Fraction(6, 10):
            return 1
        if s < Fraction(9, 10):
            return 2
        if s < Fraction(12, 10):
            return 3
        return 4

    def t_level(t):
        if t == f">{H_hours}" or t == ">H":
            return 0
        if isinstance(t, str):
            return 0
        if t > 48:
            return 0
        if t > 24:
            return 2
        if t > 6:
            return 3
        return 4

    sl = s_level(S_H)
    tl = t_level(T_act)
    level = max(sl, tl)
    return f"L{level}"


def evaluate(unit_day, H_hours):
    """Top-level entry point. unit_day is a dict assembled by run_backtest.py with all
    resolved inputs for one (unit, day, c, pump_scenario, horizon) combination.

    Returns a dict: {tag: PROPOSAL_TAG, refused: bool, code, tier, S_H, T_act, binding, ...}
    """
    out = {"tag": PROPOSAL_TAG, "refused": False}
    try:
        outlets = unit_day["outlets"]
        R_H, per_outlet = compute_R_H(outlets, H_hours)
        D_H, no_pumps = compute_D_H(unit_day["P_run_m3s"], H_hours)
        F_H, runoff_term, upstream_term = compute_F_H(
            unit_day["c_U"], unit_day["A_U_km2"],
            unit_day["rain_mm_hourly"], unit_day.get("Q_in_up_m3s_hourly"), H_hours,
        )
        min_DR = min(D_H, R_H)
        if min_DR == 0 and F_H > 0:
            raise Refused("ZERO_CAPACITY_NONZERO_INFLOW",
                          f"min(D_H,R_H)=0 (D_H={D_H}, R_H={R_H}), F_H={F_H}>0")
        if min_DR == 0 and F_H == 0:
            S_H = Fraction(0)
        else:
            S_H = F_H / min_DR
        binding = "PUMP" if D_H <= R_H else "OUTLET"

        def cum_F(t):
            rain_partial = unit_day["rain_mm_hourly"][:t]
            A_m2 = Fraction(unit_day["A_U_km2"]) * 1_000_000
            rain_sum_m = sum(Fraction(str(r)) for r in rain_partial) * Fraction(1, 1000)
            term1 = Fraction(str(unit_day["c_U"])) * A_m2 * rain_sum_m
            up = unit_day.get("Q_in_up_m3s_hourly")
            term2 = sum(Fraction(str(q)) * 3600 for q in up[:t]) if up else Fraction(0)
            return term1 + term2

        T_act = compute_T_act(cum_F, min_DR, H_hours)
        tier = tier_ladder(S_H, T_act, H_hours)

        out.update({
            "code": None, "tier": tier,
            "S_H": float(S_H), "T_act": T_act if isinstance(T_act, str) else int(T_act),
            "binding": binding, "R_H_m3": float(R_H), "D_H_m3": float(D_H),
            "F_H_m3": float(F_H), "runoff_term_m3": float(runoff_term),
            "upstream_term_m3": float(upstream_term), "no_pumps_in_unit": no_pumps,
        })
        return out
    except Refused as r:
        if r.code not in REFUSAL_PRECEDENCE:
            raise
        out.update({"refused": True, "code": r.code, "detail": r.detail, "tier": "LR"})
        return out
