"""prop_flood_06_v3.py -- PROP-FLOOD-06 PROPOSAL, unverified.

Core readout engine implementing PROP-FLOOD-06 v3 (as registered in
toledo-wt-flood06/registry/proposals/flood_outlet_coping.json at HEAD, read-only,
this check's implementation target):

  - C_H(U): total case split replacing the literal min(D_H,R_H) (fixes the
    no-pump contradiction found in BACKTEST_PROP_FLOOD_06_v0.md sec.2.1).
  - mode in {FULL, PARTIAL, LR}: PARTIAL is a total max over a declared
    promoter table whenever >=1 of the 7 coverage-vector components is
    present but the full ledger does not resolve; LR only when cov(U) is
    entirely absent/stale.
  - promoter table adopted verbatim from the registry entry
    (readout_classes.promoter_table).

This is a NEW DERIVATION / PROPOSAL implementation, not a verified Toledo
theorem. Every numeric threshold below (0.3/0.6/0.9/1.2 on S_H, 6/24/48h on
T_act, 80mm rain, canal warning/critical/bank) is OPEN-for-founder-tuning,
copied from the registry entry, never invented here.

Write-scope note: this file is new code only, written by a non-committing
worker in this worktree. It does not edit any existing tool or data file.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Coverage vector
# ---------------------------------------------------------------------------

COV_COMPONENTS = [
    "rain_obs",
    "rain_fcst",
    "canal_level_vs_lines",
    "river_flow_vs_cap",
    "dam_release",
    "pumps_state",
    "upstream_inflow",
]


def coverage_vector(inputs: dict) -> dict:
    """Each component -> 'present' | 'absent'. ('stale' is not modelled in this
    backtest -- every archived reading used here is either a real historical
    value or genuinely missing; no live-staleness clock applies to a replay.)"""
    cov = {}
    cov["rain_obs"] = "present" if inputs.get("rain_24h_mm") is not None else "absent"
    cov["rain_fcst"] = "absent"  # this backtest only has observed reanalysis/telemetry rain, never a forecast
    cov["canal_level_vs_lines"] = (
        "present"
        if inputs.get("canal_level_m") is not None and inputs.get("canal_warning_m") is not None
        else "absent"
    )
    cov["river_flow_vs_cap"] = (
        "present" if inputs.get("Q_o_now") is not None and inputs.get("Q_cap_o") is not None else "absent"
    )
    cov["dam_release"] = "absent"  # no dam-release feed available to this backtest
    cov["pumps_state"] = "present" if inputs.get("pumps_running_count") is not None else "absent"
    cov["upstream_inflow"] = "present" if inputs.get("Q_in_up") is not None else "absent"
    return cov


def coverage_score(cov: dict) -> float:
    return sum(1 for v in cov.values() if v == "present") / 7.0


# ---------------------------------------------------------------------------
# C_H(U) -- v3 total case split (registry definitions.C_H(U))
# ---------------------------------------------------------------------------

def compute_C_H(pumps_declared: bool, R_H: Optional[float], D_H: Optional[float]):
    """Returns (C_H_value_or_None, terms_present, refused_reason_or_None)."""
    if not pumps_declared and R_H is not None:
        return R_H, {"R"}, None
    if pumps_declared and R_H is None and D_H is not None:
        return D_H, {"D"}, None
    if R_H is not None and D_H is not None:
        return min(R_H, D_H), {"R", "D"}, None
    return None, set(), "OUTLET_CAPACITY_UNKNOWN"


# ---------------------------------------------------------------------------
# Promoter table (registry readout_classes.promoter_table, verbatim thresholds)
# ---------------------------------------------------------------------------

def evaluate_promoters(inputs: dict, cov: dict) -> list:
    """Returns list of dicts: {id, requires_cov, fires, min_tier}."""
    fired = []

    if cov["rain_obs"] == "present":
        rain = inputs["rain_24h_mm"]
        fired.append({
            "id": "RAIN_24H_EXCEEDS_DESIGN", "requires_cov": "rain_obs",
            "fires": rain > 80, "min_tier": "L3" if rain > 80 else None,
            "value": f"{rain} mm",
        })

    if cov["canal_level_vs_lines"] == "present":
        lvl = inputs["canal_level_m"]
        warn = inputs.get("canal_warning_m")
        crit = inputs.get("canal_critical_m")
        bank = inputs.get("canal_bank_m")
        if bank is not None and lvl >= bank:
            fired.append({"id": "CANAL_AT_BANK_LEVEL", "requires_cov": "canal_level_vs_lines",
                          "fires": True, "min_tier": "L5", "value": f"{lvl}m >= bank {bank}m"})
        elif crit is not None and lvl >= crit:
            fired.append({"id": "CANAL_AT_CRITICAL_LINE", "requires_cov": "canal_level_vs_lines",
                          "fires": True, "min_tier": "L4", "value": f"{lvl}m >= critical {crit}m"})
        elif warn is not None and lvl >= warn:
            fired.append({"id": "CANAL_AT_WARNING_LINE", "requires_cov": "canal_level_vs_lines",
                          "fires": True, "min_tier": "L2", "value": f"{lvl}m >= warning {warn}m"})
        else:
            fired.append({"id": "CANAL_AT_WARNING_LINE", "requires_cov": "canal_level_vs_lines",
                          "fires": False, "min_tier": None, "value": f"{lvl}m below warning"})

    if cov["pumps_state"] == "present":
        running = inputs["pumps_running_count"]
        crit = inputs.get("canal_critical_m")
        lvl = inputs.get("canal_level_m")
        cond = running == 0 and crit is not None and lvl is not None and lvl >= crit
        fired.append({"id": "PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD", "requires_cov": "pumps_state",
                      "fires": cond, "min_tier": "L5" if cond else None,
                      "value": f"{running} pumps running"})

    # DAM_RELEASE_ABOVE_SPILL_THRESHOLD, VULNERABLE_UNIT_PROMOTION: no data feed in this
    # backtest -- not evaluated (OPEN, noted in the report, never silently assumed absent-of-risk).
    return fired


TIER_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5"]


def _max_tier(tiers):
    if not tiers:
        return "L0"
    return max(tiers, key=lambda t: TIER_ORDER.index(t))


def s_band(s_h: float) -> str:
    if s_h < 0.3:
        return "L0"
    if s_h < 0.6:
        return "L1"
    if s_h < 0.9:
        return "L2"
    if s_h < 1.2:
        return "L3"
    return "L4"


def t_act_band(t_act, horizon: float) -> str:
    if t_act is None or t_act > horizon:
        return "L0"
    if t_act > 48:
        return "L1"
    if t_act > 24:
        return "L2"
    if t_act > 6:
        return "L3"
    return "L4"


@dataclass
class Readout:
    mode: str
    tier: str
    based_on: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    coverage: float = 0.0
    terms_present: set = field(default_factory=set)
    S_H: Optional[float] = None
    T_act: Optional[float] = None
    promoters_fired: list = field(default_factory=list)
    refused_reason: Optional[str] = None


def full_tier_v3(unit_tuple: dict, H: float) -> Readout:
    """unit_tuple keys: pumps_declared(bool), R_H, D_H, F_H (all Optional[float]),
    rain-based inputs already summarised into R_H/D_H/F_H by the caller; plus raw
    `inputs` dict for cov()/promoters()."""
    inputs = unit_tuple["inputs"]
    cov = coverage_vector(inputs)
    cov_score = coverage_score(cov)

    if all(v != "present" for v in cov.values()):
        return Readout(mode="LR", tier="LR", coverage=cov_score, refused_reason="NO_REAL_INPUT")

    C_H, terms_present, refused_reason = compute_C_H(
        unit_tuple["pumps_declared"], unit_tuple.get("R_H"), unit_tuple.get("D_H")
    )
    F_H = unit_tuple.get("F_H")

    full_resolves = C_H is not None and F_H is not None

    if full_resolves:
        if C_H == 0 and F_H > 0:
            tier = "L5"
        else:
            s_h = (F_H / C_H) if C_H > 0 else 0.0
            # T_act (INSTINCT approximation at daily granularity): linear scaling of the
            # horizon by how much of C_H the forecast inflow already consumes -- flagged,
            # not a true sub-horizon hourly crossing search (no hourly F_H series here).
            t_act = (H * (C_H / F_H)) if F_H > 0 else None
            tier = _max_tier([s_band(s_h), t_act_band(t_act, H)])
        return Readout(
            mode="FULL", tier=tier, based_on=[k for k, v in cov.items() if v == "present"],
            missing=[k for k, v in cov.items() if v != "present"], coverage=cov_score,
            terms_present=terms_present, S_H=(F_H / C_H) if (C_H and C_H > 0) else (0.0 if C_H == 0 else None),
        )

    # PARTIAL mode
    promoters = evaluate_promoters(inputs, cov)
    fired_tiers = [p["min_tier"] for p in promoters if p["fires"]]
    tier = _max_tier(fired_tiers) if fired_tiers else "L0"
    based_on = sorted({p["requires_cov"] for p in promoters})
    missing = [k for k, v in cov.items() if v != "present"]
    return Readout(
        mode="PARTIAL", tier=tier, based_on=based_on, missing=missing, coverage=cov_score,
        terms_present=terms_present, promoters_fired=[p["id"] for p in promoters if p["fires"]],
        refused_reason=refused_reason,
    )
