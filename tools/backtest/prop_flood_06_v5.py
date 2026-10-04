"""prop_flood_06_v5.py -- PROP-FLOOD-06 PROPOSAL v5, unverified.

Falsifier loop v2 engine. Reuses tools/backtest/prop_flood_06_v3.py's coverage_vector
(base 7), compute_C_H, s_band, t_act_band, TIER_ORDER, _max_tier UNCHANGED (imported, not
copied) and adds the v5 registration (toledo-wt-flood06 HEAD ebd34071,
registry/proposals/flood_outlet_coping.json + docs/proposals/PROP-FLOOD-06.md):

  - cov5(U): the existing 7-component cov(U) plus 3 new LEADING components
    (upstream_rise_rate, basin_rain_accum, forecast_rain_72h) -- widens the
    coverage_total from 7 to 10.
  - v4's floor fix, implemented here for the first time in this repo's backtest history
    (v1's report explicitly noted v4 was not at HEAD when it ran, so it used v3's
    EXCLUSIVE FULL-xor-PARTIAL mode split): promoters (base + leading) are now a floor
    under EVERY mode -- base_tier := max(band_tier, promoter_max), band_tier := the
    S_H/T_act combined tier if the ledger resolves else L0, promoter_max := the max
    tier over every promoter whose required cov5 component is present, in every mode.
  - 3 new promoters (UPSTREAM_RISE_RATE_EXCEEDS L3, BASIN_RAIN_ACCUM_EXCEEDS L2,
    FORECAST_RAIN_72H_EXCEEDS L1) per the registry's promoter_table, thresholds declared
    here (OPEN-for-founder-tuning, INSTINCT -- this proposal's own JSON leaves the
    national-default rise-rate/72h-rain thresholds unspecified; the values below are
    this check's own declared choice, not derived, not previously registered elsewhere).
  - `lead_time_h`: a SIMPLIFIED proxy for PROP-FLOOD-02's full T_act_upstream
    construction (T_k := (theta-h(t))*k/Delta_k(t) applied to the shifted upstream
    series) -- this backtest does NOT implement the full threshold-crossing search;
    it reports lead_time_h := the declared tau_up actually used for that record when
    UPSTREAM_RISE_RATE_EXCEEDS fires, else None. This is an INSTINCT approximation,
    flagged exactly like v1's T_act daily-granularity approximation (see
    docs/BACKTEST_PROP_FLOOD_06_v1.md limitation #4) -- NOT a literal implementation
    of the registry's T_k formula.
  - persistence (p=2 raise / q=3 step-down) is a POST-PROCESSING layer over a
    chronological per-(unit,c,H,tau) raw-tier sequence -- see `apply_persistence` below,
    applied by the runner, not inside `full_tier_v5` itself (matches the registry's own
    "post-processing layer over the per-hour readout stream" framing; here it runs over
    the per-DAY stream, since this backtest has no hourly readout series -- an explicit
    granularity downgrade from the registry's hourly persistence spec, flagged).

Write-scope note: new file only, written by a non-committing worker in this worktree.
Does not edit prop_flood_06_v3.py or any existing tracked file.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from prop_flood_06_v3 import (  # noqa: E402
    coverage_vector as coverage_vector_v4,
    coverage_score as coverage_score_v4,
    compute_C_H,
    evaluate_promoters as evaluate_promoters_v4,
    s_band,
    t_act_band,
    TIER_ORDER,
    _max_tier,
)

# ---------------------------------------------------------------------------
# v5 declared thresholds -- OPEN-for-founder-tuning, INSTINCT (this check's own choice,
# not previously registered; the registry's JSON leaves these national defaults TBD).
# ---------------------------------------------------------------------------

UPSTREAM_RISE_RATE_PCT_THRESHOLD = 0.15   # 15% rise over lag k=24h on the upstream series
BASIN_RAIN_24H_THRESHOLD_MM = 80.0        # reuses RAIN_24H_EXCEEDS_DESIGN's own 80mm, per
                                            # the registry's own note that this may be a
                                            # reasonable starting default for the 24h edge
BASIN_RAIN_72H_THRESHOLD_MM = 150.0       # declared here, INSTINCT, no source
FORECAST_RAIN_72H_THRESHOLD_MM = 150.0    # same value as basin_rain_accum's 72h edge,
                                            # declared here, INSTINCT

COV5_COMPONENTS = [
    "rain_obs", "rain_fcst", "canal_level_vs_lines", "river_flow_vs_cap", "dam_release",
    "pumps_state", "upstream_inflow",
    "upstream_rise_rate", "basin_rain_accum", "forecast_rain_72h",
]


def coverage_vector_v5(inputs: dict) -> dict:
    cov = dict(coverage_vector_v4(inputs))
    cov["upstream_rise_rate"] = "present" if inputs.get("upstream_delta_pct") is not None else "absent"
    cov["basin_rain_accum"] = (
        "present"
        if (inputs.get("basin_rain_24h_mm") is not None or inputs.get("basin_rain_72h_mm") is not None)
        else "absent"
    )
    cov["forecast_rain_72h"] = "present" if inputs.get("forecast_rain_72h_mm") is not None else "absent"
    return cov


def coverage_score_v5(cov: dict) -> float:
    return sum(1 for v in cov.values() if v == "present") / 10.0


def evaluate_promoters_v5(inputs: dict, cov: dict) -> list:
    """Base 6 promoters (v3/v4, unchanged, evaluated on the 7-component slice of cov)
    plus the 3 new v5 leading promoters."""
    base_cov = {k: cov[k] for k in [
        "rain_obs", "rain_fcst", "canal_level_vs_lines", "river_flow_vs_cap",
        "dam_release", "pumps_state", "upstream_inflow",
    ]}
    fired = list(evaluate_promoters_v4(inputs, base_cov))

    if cov["upstream_rise_rate"] == "present":
        pct = inputs["upstream_delta_pct"]
        cond = pct > UPSTREAM_RISE_RATE_PCT_THRESHOLD
        fired.append({
            "id": "UPSTREAM_RISE_RATE_EXCEEDS", "requires_cov": "upstream_rise_rate",
            "fires": cond, "min_tier": "L3" if cond else None,
            "value": f"{pct*100:.1f}% over lag-24h (tau_up={inputs.get('tau_up_h')}h, "
                     f"gauge={inputs.get('upstream_gauge_id')})",
        })

    if cov["basin_rain_accum"] == "present":
        r24 = inputs.get("basin_rain_24h_mm")
        r72 = inputs.get("basin_rain_72h_mm")
        cond = (r24 is not None and r24 > BASIN_RAIN_24H_THRESHOLD_MM) or \
               (r72 is not None and r72 > BASIN_RAIN_72H_THRESHOLD_MM)
        fired.append({
            "id": "BASIN_RAIN_ACCUM_EXCEEDS", "requires_cov": "basin_rain_accum",
            "fires": cond, "min_tier": "L2" if cond else None,
            "value": f"24h={r24}mm 72h={r72}mm",
        })

    if cov["forecast_rain_72h"] == "present":
        f72 = inputs["forecast_rain_72h_mm"]
        cond = f72 > FORECAST_RAIN_72H_THRESHOLD_MM
        fired.append({
            "id": "FORECAST_RAIN_72H_EXCEEDS", "requires_cov": "forecast_rain_72h",
            "fires": cond, "min_tier": "L1" if cond else None,
            "value": f"{f72}mm next 72h (perfect-prognosis proxy)",
        })

    return fired


@dataclass
class ReadoutV5:
    mode: str
    tier: str
    band_tier: str = "L0"
    promoter_tier: str = "L0"
    based_on: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    coverage: float = 0.0
    terms_present: set = field(default_factory=set)
    S_H: Optional[float] = None
    promoters_fired: list = field(default_factory=list)
    refused_reason: Optional[str] = None
    lead_time_h: Optional[float] = None
    calibrated: str = 'no ("ยังไม่สอบเทียบที่นี่")'


def full_tier_v5(unit_tuple: dict, H: float) -> ReadoutV5:
    """v5: v4's floor fix (promoters are a floor under FULL too) + cov5 (10 components)
    + 3 leading promoters. unit_tuple keys: pumps_declared, R_H, D_H, F_H, inputs (dict,
    v3 keys plus upstream_delta_pct/tau_up_h/upstream_gauge_id/basin_rain_24h_mm/
    basin_rain_72h_mm/forecast_rain_72h_mm)."""
    inputs = unit_tuple["inputs"]
    cov = coverage_vector_v5(inputs)
    cov_score = coverage_score_v5(cov)

    if all(v != "present" for v in cov.values()):
        return ReadoutV5(mode="LR", tier="LR", coverage=cov_score, refused_reason="NO_REAL_INPUT")

    C_H, terms_present, refused_reason = compute_C_H(
        unit_tuple["pumps_declared"], unit_tuple.get("R_H"), unit_tuple.get("D_H")
    )
    F_H = unit_tuple.get("F_H")
    full_resolves = C_H is not None and F_H is not None

    band_tier = "L0"
    S_H = None
    if full_resolves:
        if C_H == 0 and F_H > 0:
            band_tier = "L5"
            S_H = 0.0
        else:
            s_h = (F_H / C_H) if C_H > 0 else 0.0
            S_H = s_h
            t_act = (H * (C_H / F_H)) if F_H > 0 else None
            band_tier = _max_tier([s_band(s_h), t_act_band(t_act, H)])

    promoters = evaluate_promoters_v5(inputs, cov)
    fired_tiers = [p["min_tier"] for p in promoters if p["fires"]]
    promoter_tier = _max_tier(fired_tiers) if fired_tiers else "L0"
    base_tier = _max_tier([band_tier, promoter_tier])

    mode = "FULL" if full_resolves else "PARTIAL"
    based_on = [k for k, v in cov.items() if v == "present"]
    missing = [k for k, v in cov.items() if v != "present"]

    lead_time_h = None
    for p in promoters:
        if p["id"] == "UPSTREAM_RISE_RATE_EXCEEDS" and p["fires"]:
            lead_time_h = inputs.get("tau_up_h")

    return ReadoutV5(
        mode=mode, tier=base_tier, band_tier=band_tier, promoter_tier=promoter_tier,
        based_on=based_on, missing=missing, coverage=cov_score, terms_present=terms_present,
        S_H=S_H, promoters_fired=[p["id"] for p in promoters if p["fires"]],
        refused_reason=refused_reason, lead_time_h=lead_time_h,
    )


# ---------------------------------------------------------------------------
# Persistence (hysteresis), p=2 raise / q=3 step-down -- registry's `persisted`, applied
# over the per-day raw-tier sequence (granularity downgrade from hourly, flagged above).
# `persisted_is_some_historical_raw`'s guarantee (persistence never fabricates a tier
# absent from the raw history) is preserved by construction below: the returned sequence
# at each index is always copied from some earlier-or-equal raw index, never invented.
# ---------------------------------------------------------------------------

def apply_persistence(raw_tiers: list, p: int = 2, q: int = 3) -> list:
    """raw_tiers: chronological list of tier strings (e.g. 'L0'..'L5','LR'). Returns the
    persisted sequence, same length. LR passes through unpersisted (a refusal state, not
    part of the raise/lower ladder -- mirrors the registry's LR-dominates-unconditionally
    rule)."""
    def rank(t):
        if t == "LR":
            return -1  # never compared numerically; handled by pass-through below
        return TIER_ORDER.index(t)

    out = []
    current = raw_tiers[0] if raw_tiers else "L0"
    out.append(current)
    for i in range(1, len(raw_tiers)):
        raw = raw_tiers[i]
        if raw == "LR" or current == "LR":
            current = raw
            out.append(current)
            continue
        if rank(raw) > rank(current):
            # candidate raise: must hold for p consecutive raw readouts (incl. this one)
            window = raw_tiers[max(0, i - p + 1): i + 1]
            if len(window) == p and all(w != "LR" and rank(w) >= rank(raw) for w in window):
                current = raw
        elif rank(raw) < rank(current):
            window = raw_tiers[max(0, i - q + 1): i + 1]
            if len(window) == q and all(w != "LR" and rank(w) <= rank(raw) for w in window):
                current = raw
        out.append(current)
    return out
