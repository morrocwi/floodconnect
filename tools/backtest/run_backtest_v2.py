#!/usr/bin/env python3
"""run_backtest_v2.py -- PROP-FLOOD-06 PROPOSAL v5, unverified.

Falsifier loop v2: re-runs the SAME 271 unit-days (+ same c in {0.5,1}, H in {24,48}
controls) as v1 (docs/BACKTEST_PROP_FLOOD_06_v1.md, raw/backtest/results_v1.jsonl)
through the v5 engine (tools/backtest/prop_flood_06_v5.py), which adds the 3 LEADING
promoters (upstream_rise_rate, basin_rain_accum, forecast_rain_72h), v4's promoter-floor
fix, and persistence (p=2/q=3) on top of v3's C_H(U)/PARTIAL machinery -- unchanged.

Upstream gauge per unit (declared here, per this check's brief -- NOT re-derived from any
new source read):
  - NAN        <- N.64 (Tha Wang Pha, station 3246) -- CONFIRMED present, hourly
                 discharge. tau_up SWEPT over {0, 6, 12} h (declared OPEN, all three
                 reported, per brief) -- 3x rows for this unit only.
  - CHIANGMAI  <- no confirmed upstream series anywhere in this repo's own knowledge
                 base (P.67/P.75 unconfirmed, per PROP-FLOOD-06.md sec."tau_up"). Uses
                 P.1 ITSELF as a degraded leading input (tau_up=0h, DEGRADED-SELF-AS-
                 UPSTREAM -- this is NOT a real leading signal, flagged).
  - HATYAI     <- X.44 only (X.90/X.173 unconfirmed as upstream gauges). Uses X.44
                 ITSELF (tau_up=0h, DEGRADED-SELF-AS-UPSTREAM), additionally flagged
                 DOWNSTREAM-OF-R1-INTAKE-EXPECTED-WEAK per the founder's instructions (X.44 sits
                 past the R.1 floodway diversion, per DATA_SWEEP_2026-09-27.md).
  - AYUTTHAYA  <- C.2 (Nakhon Sawan) -- no HII telemetry archived for C.2 in this repo;
                 uses the GloFAS/Open-Meteo Flood API daily series already fetched at
                 raw/backtest/flood/NAKHONSAWAN_C2_UPSTREAM_*.json (same proxy already
                 used as this unit's Q_in,up in v0/v1), tagged RELAYED-GloFAS, daily
                 granularity only (no hourly). tau_up declared 48h (INSTINCT, Nakhon
                 Sawan-to-Ayutthaya Chao Phraya travel time order-of-magnitude, NOT
                 independently sourced this check).
  - BANGKOK_EAST <- no upstream gauge declared anywhere in this proposal (per its own
                 worked-instantiation table: "no material upstream-mainstem inflow term
                 declared for this zone") -- upstream_rise_rate is structurally absent
                 (UPSTREAM_GAUGE_UNDECLARED) for every row of this unit, exactly as the
                 registry's own refusal-code scoping states (refuses only this one term,
                 never the whole readout).

basin_rain_accum / forecast_rain_72h: this check's brief instructs "aggregate the grid
points you have; if only the unit-centre point exists, say so and use it, flagged" --
every ERA5 rain archive under raw/backtest/rain/ IS the unit-centre point only (single
lat/lon request, per fetch_historical.py), never a true upstream-sub-basin polygon
aggregate. Every basin_rain_accum/forecast_rain_72h value in this run is therefore
tagged AGGREGATE-PROXY-CENTRE-POINT, not a real upstream-polygon rain figure -- the DWR
sub-basin polygons (sources/dwr_subbasins.yaml, raw/gis/dwr_subbasin/page_0.geojson,
tools/kg/unit_resolver.py (promoted from unit_resolver_draft.py, commit c07eb87)) are read and reported below (sb_code per unit) but this
run does NOT re-fetch or spatially aggregate ERA5 grid points over that polygon -- doing
so would require a new ERA5 pull this check did not perform (reuse-only brief).

forecast_rain_72h uses the ERA5 "future" window (the same archived reanalysis, read
forward from the evaluation day) as a PERFECT-PROGNOSIS PROXY for a genuine forecast --
explicitly flagged as an UPPER BOUND on what a real forecast-driven promoter could
achieve, never presented as an actual forecast skill measurement.

Write-scope: writes only raw/backtest/results_v2.jsonl (new file, streamed line-by-line
to keep memory low) and reads sb_code via tools/kg/unit_resolver.py (promoted from unit_resolver_draft.py, commit c07eb87). Does not edit
events.yaml, units.yaml, results_v1.jsonl, or any existing tracked file. Not committed as
part of this change.
"""
import csv
import json
import os
import sys
import glob
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from prop_flood_06_v5 import full_tier_v5, apply_persistence  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)


def load_yaml(path):
    import yaml
    with open(os.path.join(REPO, path)) as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(os.path.join(REPO, path)) as f:
        return json.load(f)


UNITS = load_yaml("raw/backtest/units.yaml")["units"]
UNITS_BY_ID = {u["id"]: u for u in UNITS}
EVENTS = load_yaml("raw/backtest/events.yaml")["units"]
CAP_ADD = load_yaml("sources/capacity_ledger_additions.yaml")["additions"]

C_VALUES = [0.5, 1.0]
H_VALUES = [24, 48]

GT_FLOODED = {}
for ev in EVENTS:
    GT_FLOODED[(ev["unit"], ev["date"])] = ev["flooded_significantly"]

# ---------------------------------------------------------------------------
# sb_code per unit via the DWR sub-basin resolver (read-only reuse, per the founder's instructions).
# ---------------------------------------------------------------------------
SB_CODE_BY_UNIT = {}
try:
    from tools.kg.unit_resolver import resolve_unit  # noqa: E402 -- promoted from
    # unit_resolver_draft in commit c07eb87 (tools/kg/unit_resolver.py); this file's
    # import path is fixed here to match, per that commit's own note that a separate
    # worker still importing the old path would need to update it itself.
    for u in UNITS:
        c = u.get("centre") or {}
        lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            SB_CODE_BY_UNIT[u["id"]] = {"sb_code": None, "reason": "no centre declared"}
            continue
        try:
            SB_CODE_BY_UNIT[u["id"]] = resolve_unit(lat, lon)
        except Exception as e:  # noqa: BLE001 -- resolver import/data issue, don't crash the run
            SB_CODE_BY_UNIT[u["id"]] = {"sb_code": None, "reason": f"resolver error: {e}"}
except Exception as e:  # noqa: BLE001
    for u in UNITS:
        SB_CODE_BY_UNIT[u["id"]] = {"sb_code": None, "reason": f"resolver unavailable: {e}"}


# ---------------------------------------------------------------------------
# Hourly / daily series loaders (merge every archived window per unit into one dict)
# ---------------------------------------------------------------------------

def merge_hourly_hii(paths, value_key="discharge"):
    """Returns {'YYYY-MM-DD HH:MM': value} merged across archives."""
    out = {}
    for p in paths:
        full = os.path.join(REPO, p)
        if not os.path.exists(full):
            continue
        d = load_json(p)["data"]["graph_data"]
        for row in d:
            v = row.get(value_key)
            if v is not None:
                out[row["datetime"]] = v
    return out


def merge_hourly_rain(unit_prefix):
    """Returns {'YYYY-MM-DDTHH:MM': mm} merged across every raw/backtest/rain/<prefix>_*.json."""
    out = {}
    for full in sorted(glob.glob(os.path.join(REPO, f"raw/backtest/rain/{unit_prefix}_*.json"))):
        d = load_json(os.path.relpath(full, REPO))
        h = d.get("hourly", {})
        for t, p in zip(h.get("time", []), h.get("precipitation", [])):
            out[t] = p if p is not None else 0.0
    return out


def merge_daily_glofas(paths, value_key="river_discharge"):
    out = {}
    for p in paths:
        full = os.path.join(REPO, p)
        if not os.path.exists(full):
            continue
        d = load_json(p)["daily"]
        for t, v in zip(d.get("time", []), d.get(value_key, [])):
            if v is not None:
                out[t] = v
    return out


def daterange(d0, d1):
    cur = datetime.strptime(d0, "%Y-%m-%d")
    end = datetime.strptime(d1, "%Y-%m-%d")
    while cur <= end:
        yield cur.strftime("%Y-%m-%d")
        cur += timedelta(days=1)


NAN_UPSTREAM = merge_hourly_hii(["raw/backtest/hii_history/N64_3246_2567.json"])
HATYAI_SELF_UPSTREAM = merge_hourly_hii([
    "raw/backtest/hii_history/X44_2591_2565.json",
    "raw/backtest/hii_history/X44_2591_2553.json",
])
CHIANGMAI_SELF_UPSTREAM = merge_hourly_hii(["raw/backtest/hii_history/P1_3226_2567.json"])
AYUTTHAYA_UPSTREAM_C2 = merge_daily_glofas([
    "raw/backtest/flood/NAKHONSAWAN_C2_UPSTREAM_2011-09-20_2011-10-20.json",
    "raw/backtest/flood/NAKHONSAWAN_C2_UPSTREAM_2012-02-01_2012-02-10.json",
])

RAIN_HOURLY = {
    "HATYAI": merge_hourly_rain("HATYAI"),
    "NAN": merge_hourly_rain("NAN"),
    "CHIANGMAI": merge_hourly_rain("CHIANGMAI"),
    "AYUTTHAYA_BANGBAN": merge_hourly_rain("AYUTTHAYA_BANGBAN"),
    "BANGKOK_EAST": merge_hourly_rain("BANGKOK_EAST"),
}


def hourly_window_sum(hourly: dict, start: datetime, end: datetime):
    """Sum of hourly values with start <= t < end (all-or-nothing: returns None unless
    every expected hour in [start,end) is present in the dict -- an honest 'incomplete
    window' refusal rather than a silent partial sum)."""
    total = 0.0
    n_expected = int((end - start).total_seconds() // 3600)
    n_found = 0
    t = start
    while t < end:
        key = t.strftime("%Y-%m-%dT%H:%M")
        if key in hourly:
            total += hourly[key]
            n_found += 1
        t += timedelta(hours=1)
    if n_expected == 0 or n_found < n_expected:
        return None
    return total


def hii_value_at(hourly: dict, dt: datetime):
    key = dt.strftime("%Y-%m-%d %H:%M")
    return hourly.get(key)


def upstream_delta_pct_hourly(hourly: dict, day: str, tau_h: int, lag_h: int = 24):
    """Max over day's 24 hours of the lag-h percent rise on `hourly`, evaluated
    tau_h hours BEFORE each hour of `day` (i.e. h(t-tau) vs h(t-tau-lag)). None if no
    valid (both-present, denominator!=0) reading exists anywhere in the day."""
    day_dt = datetime.strptime(day, "%Y-%m-%d")
    best = None
    for hour in range(24):
        t = day_dt + timedelta(hours=hour) - timedelta(hours=tau_h)
        v_now = hii_value_at(hourly, t)
        v_prev = hii_value_at(hourly, t - timedelta(hours=lag_h))
        if v_now is None or v_prev is None or v_prev == 0:
            continue
        pct = (v_now - v_prev) / v_prev
        if best is None or pct > best:
            best = pct
    return best


def upstream_delta_pct_daily(daily: dict, day: str, tau_days: int):
    day_dt = datetime.strptime(day, "%Y-%m-%d") - timedelta(days=tau_days)
    d_now = day_dt.strftime("%Y-%m-%d")
    d_prev = (day_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    v_now, v_prev = daily.get(d_now), daily.get(d_prev)
    if v_now is None or v_prev is None or v_prev == 0:
        return None
    return (v_now - v_prev) / v_prev


def basin_rain_24_72_forecast(unit_id: str, day: str):
    hourly = RAIN_HOURLY.get(unit_id, {})
    day_dt = datetime.strptime(day, "%Y-%m-%d")
    r24 = hourly_window_sum(hourly, day_dt, day_dt + timedelta(days=1))
    r72 = hourly_window_sum(hourly, day_dt - timedelta(days=2), day_dt + timedelta(days=1))
    f72 = hourly_window_sum(hourly, day_dt + timedelta(days=1), day_dt + timedelta(days=4))
    return r24, r72, f72


# ---------------------------------------------------------------------------
# Emit (streamed): build raw rows grouped by scenario key for persistence, write once
# per unit at the end of that unit's block to keep the resident set small.
# ---------------------------------------------------------------------------

out_path = os.path.join(REPO, "raw/backtest/results_v2.jsonl")
out_f = open(out_path, "w")
total_written = 0


def make_row(unit, date, c, H, tau_up_h, upstream_gauge_id, inputs, pumps_declared, R_H, D_H, F_H,
             flooded, gt_source, gt_tag, notes):
    inputs = dict(inputs)
    inputs["tau_up_h"] = tau_up_h
    inputs["upstream_gauge_id"] = upstream_gauge_id
    readout = full_tier_v5(
        {"pumps_declared": pumps_declared, "R_H": R_H, "D_H": D_H, "F_H": F_H, "inputs": inputs}, H
    )
    return {
        "unit": unit, "date": date, "c": c, "H": H, "tau_up_h": tau_up_h,
        "upstream_gauge_id": upstream_gauge_id,
        "mode": readout.mode, "tier_raw": readout.tier, "band_tier": readout.band_tier,
        "promoter_tier": readout.promoter_tier,
        "coverage_n_of_10": round(readout.coverage * 10, 2),
        "based_on": readout.based_on, "missing": readout.missing,
        "promoters_fired": readout.promoters_fired,
        "terms_present": sorted(readout.terms_present),
        "S_H": readout.S_H, "lead_time_h_raw": readout.lead_time_h,
        "sb_code": SB_CODE_BY_UNIT.get(unit, {}).get("sb_code"),
        "flooded_significantly": flooded,
        "ground_truth_source": gt_source, "ground_truth_tag": gt_tag,
        "notes": notes,
    }


def write_group(rows):
    """rows: chronological list of row dicts for one (unit,c,H,tau) scenario. Applies
    persistence over tier_raw, writes each row with tier_persisted added."""
    if not rows:
        return
    tiers = [r["tier_raw"] for r in rows]
    persisted = apply_persistence(tiers, p=2, q=3)
    for r, pt in zip(rows, persisted):
        r["tier_persisted"] = pt
        out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
    global total_written
    total_written += len(rows)


# ---------------------------------------------------------------------------
# Part A: the 217 v0-carryover unit-days (GloFAS-era HATYAI 2553/NAN pre-Aug/CHIANGMAI
# pre-Oct/AYUTTHAYA/BANGKOK_EAST from events.yaml), same R_H/D_H/F_H construction as v1
# Part A, now also carrying whatever leading inputs are available for those same dates.
# ---------------------------------------------------------------------------
by_unit_scenario = {}  # (unit, c, H, tau) -> list of rows, built in date order per unit

for unit_id in ["HATYAI", "NAN", "CHIANGMAI", "AYUTTHAYA_BANGBAN", "BANGKOK_EAST"]:
    u = UNITS_BY_ID[unit_id]
    pumps_declared = (u["pumps"]["P_U_m3s"] or 0) > 0
    A_U_m2 = u["A_U"]["value_km2"] * 1e6
    Q_cap_o = u["outlet"]["Q_cap_o_m3s"]["value"] if unit_id in ("AYUTTHAYA_BANGBAN", "BANGKOK_EAST") else None

    unit_events = [ev for ev in EVENTS if ev["unit"] == unit_id]
    for ev in unit_events:
        date = ev["date"]
        Q_o_now = ev.get("Q_o_now_m3s") if ev.get("Q_o_now_credible", True) else None
        Q_in_up = ev.get("Q_in_up_m3s")
        rain = ev.get("rain_mm_24h")

        r24_leading, r72_leading, f72_leading = basin_rain_24_72_forecast(unit_id, date)

        if unit_id == "NAN":
            tau_variants = [0, 6, 12]
            gauge_id = "N.64 (Tha Wang Pha, station 3246)"
        elif unit_id == "HATYAI":
            tau_variants = [0]
            gauge_id = "X.44 (station 2591) -- DEGRADED-SELF-AS-UPSTREAM, DOWNSTREAM-OF-R1-INTAKE-EXPECTED-WEAK"
        elif unit_id == "CHIANGMAI":
            tau_variants = [0]
            gauge_id = "P.1 (station 3226) -- DEGRADED-SELF-AS-UPSTREAM (no confirmed real upstream gauge)"
        elif unit_id == "AYUTTHAYA_BANGBAN":
            tau_variants = [48]
            gauge_id = "C.2 Nakhon Sawan (GloFAS/Open-Meteo proxy, RELAYED-GloFAS, daily)"
        else:  # BANGKOK_EAST
            tau_variants = [None]
            gauge_id = None

        for tau in tau_variants:
            if unit_id == "NAN":
                delta_pct = upstream_delta_pct_hourly(NAN_UPSTREAM, date, tau)
            elif unit_id == "HATYAI":
                delta_pct = upstream_delta_pct_hourly(HATYAI_SELF_UPSTREAM, date, tau)
            elif unit_id == "CHIANGMAI":
                delta_pct = upstream_delta_pct_hourly(CHIANGMAI_SELF_UPSTREAM, date, tau)
            elif unit_id == "AYUTTHAYA_BANGBAN":
                delta_pct = upstream_delta_pct_daily(AYUTTHAYA_UPSTREAM_C2, date, tau_days=2)
            else:
                delta_pct = None

            for c in C_VALUES:
                for H in H_VALUES:
                    R_H = None
                    if Q_cap_o is not None and Q_o_now is not None:
                        R_H = max(0.0, Q_cap_o - Q_o_now) * H * 3600
                    D_H = 0.0 if not pumps_declared else None
                    if unit_id == "BANGKOK_EAST" and pumps_declared:
                        D_H = u["pumps"]["P_U_m3s"] * H * 3600
                    F_H = None
                    if rain is not None:
                        F_H = c * A_U_m2 * (rain / 1000.0)
                        if Q_in_up is not None:
                            F_H += Q_in_up * H * 3600
                    elif Q_in_up is not None:
                        F_H = Q_in_up * H * 3600
                    inputs = {
                        "rain_24h_mm": rain, "Q_o_now": Q_o_now, "Q_cap_o": Q_cap_o,
                        "pumps_running_count": (4 if unit_id == "BANGKOK_EAST" and pumps_declared else None),
                        "Q_in_up": Q_in_up,
                        "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None,
                        "upstream_delta_pct": delta_pct,
                        "basin_rain_24h_mm": r24_leading, "basin_rain_72h_mm": r72_leading,
                        "forecast_rain_72h_mm": f72_leading,
                    }
                    row = make_row(unit_id, date, c, H, tau, gauge_id, inputs, pumps_declared, R_H, D_H, F_H,
                                   ev["flooded_significantly"], ev["ground_truth_source"], ev["ground_truth_tag"],
                                   notes="v0/v1-carryover unit-day, rerun through v5 engine (cov5+leading promoters+persistence)")
                    key = (unit_id, c, H, tau)
                    by_unit_scenario.setdefault(key, []).append(row)

# ---------------------------------------------------------------------------
# Part B: Thai official history (HATYAI X.44 2565, NAN N.1 2567, CHIANGMAI P.1 2567) --
# same date windows as v1 Part B.
# ---------------------------------------------------------------------------

def daily_from_hii(path, value_key="discharge"):
    d = load_json(path)["data"]["graph_data"]
    by_day = {}
    for row in d:
        day = row["datetime"][:10]
        v = row.get(value_key)
        if v is None:
            continue
        by_day.setdefault(day, []).append(v)
    return {day: max(vals) for day, vals in by_day.items()}


def daily_rain_from_era5(path):
    if not os.path.exists(os.path.join(REPO, path)):
        return {}
    d = load_json(path)["hourly"]
    by_day = {}
    for t, p in zip(d["time"], d["precipitation"]):
        day = t[:10]
        by_day.setdefault(day, 0.0)
        by_day[day] += (p or 0.0)
    return by_day


x44 = {a["ledger_id_new"]: a for a in CAP_ADD}["led:U_hatyai_x44_station"]
qcap_hatyai = x44["Q_cap_o_m3s"]["value"]
discharge_hatyai = daily_from_hii("raw/backtest/hii_history/X44_2591_2565.json", "discharge")
rain_hatyai = daily_rain_from_era5("raw/backtest/rain/HATYAI_2022-11-15_2022-12-05.json")
HATYAI_FLOOD_DAYS = set(daterange("2022-11-30", "2022-12-03"))
A_U_hatyai = UNITS_BY_ID["HATYAI"]["A_U"]["value_km2"] * 1e6

for day in daterange("2022-11-10", "2022-12-10"):
    q_now = discharge_hatyai.get(day)
    rain = rain_hatyai.get(day)
    flooded = GT_FLOODED.get(("HATYAI", day), day in HATYAI_FLOOD_DAYS)
    r24_leading, r72_leading, f72_leading = basin_rain_24_72_forecast("HATYAI", day)
    delta_pct = upstream_delta_pct_hourly(HATYAI_SELF_UPSTREAM, day, 0)
    for c in C_VALUES:
        for H in H_VALUES:
            R_H = max(0.0, qcap_hatyai - q_now) * H * 3600 if q_now is not None else None
            F_H = c * A_U_hatyai * (rain / 1000.0) if rain is not None else None
            inputs = {"rain_24h_mm": rain, "Q_o_now": q_now, "Q_cap_o": qcap_hatyai,
                      "pumps_running_count": None, "Q_in_up": None,
                      "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None,
                      "upstream_delta_pct": delta_pct,
                      "basin_rain_24h_mm": r24_leading, "basin_rain_72h_mm": r72_leading,
                      "forecast_rain_72h_mm": f72_leading}
            row = make_row("HATYAI", day, c, H, 0,
                            "X.44 (station 2591) -- DEGRADED-SELF-AS-UPSTREAM, DOWNSTREAM-OF-R1-INTAKE-EXPECTED-WEAK",
                            inputs, False, R_H, 0.0, F_H, flooded,
                            "raw/backtest/hii_history/X44_2591_2565.json + docs/knowledge/case_hatyai_2553_2565.md",
                            "MEASURED-history(X.44 discharge)/RELAYED(flood window)",
                            notes="X.44 real gauge; v5 leading terms all use X.44 itself (degraded)")
            by_unit_scenario.setdefault(("HATYAI", c, H, 0), []).append(row)

n1 = {a["ledger_id_new"]: a for a in CAP_ADD}["led:U_nan_n1_station"]
qcap_nan = n1["Q_cap_o_m3s"]["value"]
discharge_nan = daily_from_hii("raw/backtest/hii_history/N1_3219_2567.json", "discharge")
rain_nan = daily_rain_from_era5("raw/backtest/rain/NAN_2024-08-15_2024-08-31.json")
NAN_FLOOD_DAYS = set(daterange("2024-08-19", "2024-08-30"))
A_U_nan = UNITS_BY_ID["NAN"]["A_U"]["value_km2"] * 1e6

for day in daterange("2024-08-01", "2024-09-15"):
    q_now = discharge_nan.get(day)
    rain = rain_nan.get(day)
    flooded = GT_FLOODED.get(("NAN", day), day in NAN_FLOOD_DAYS)
    r24_leading, r72_leading, f72_leading = basin_rain_24_72_forecast("NAN", day)
    for c in C_VALUES:
        for H in H_VALUES:
            R_H = max(0.0, qcap_nan - q_now) * H * 3600 if q_now is not None else None
            F_H = c * A_U_nan * (rain / 1000.0) if rain is not None else None
            for tau in (0, 6, 12):
                delta_pct = upstream_delta_pct_hourly(NAN_UPSTREAM, day, tau)
                inputs = {"rain_24h_mm": rain, "Q_o_now": q_now, "Q_cap_o": qcap_nan,
                          "pumps_running_count": None, "Q_in_up": None,
                          "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None,
                          "upstream_delta_pct": delta_pct,
                          "basin_rain_24h_mm": r24_leading, "basin_rain_72h_mm": r72_leading,
                          "forecast_rain_72h_mm": f72_leading}
                row = make_row("NAN", day, c, H, tau, "N.64 (Tha Wang Pha, station 3246)",
                                inputs, False, R_H, 0.0, F_H, flooded,
                                "raw/backtest/hii_history/N1_3219_2567.json + N64_3246_2567.json + docs/knowledge/case_nan_2567.md",
                                "MEASURED-history(N.1 discharge, N.64 upstream)/RELAYED(flood window dates)",
                                notes="N.1 outlet gauge + N.64 declared UPSTREAM gauge, tau_up swept 0/6/12h per the founder's instructions")
                by_unit_scenario.setdefault(("NAN", c, H, tau), []).append(row)

p1 = {a["ledger_id_new"]: a for a in CAP_ADD}["led:U_chiangmai_p1_station"]
qcap_cm = p1["Q_cap_o_m3s"]["value"]
discharge_cm = daily_from_hii("raw/backtest/hii_history/P1_3226_2567.json", "discharge")
rain_cm = daily_rain_from_era5("raw/backtest/rain/CHIANGMAI_2024-09-22_2024-10-07.json")
CM_FLOOD_DAYS = set(daterange("2024-10-03", "2024-10-07"))
A_U_cm = UNITS_BY_ID["CHIANGMAI"]["A_U"]["value_km2"] * 1e6

for day in daterange("2024-09-15", "2024-10-15"):
    q_now = discharge_cm.get(day)
    rain = rain_cm.get(day)
    flooded = GT_FLOODED.get(("CHIANGMAI", day), day in CM_FLOOD_DAYS)
    r24_leading, r72_leading, f72_leading = basin_rain_24_72_forecast("CHIANGMAI", day)
    delta_pct = upstream_delta_pct_hourly(CHIANGMAI_SELF_UPSTREAM, day, 0)
    for c in C_VALUES:
        for H in H_VALUES:
            R_H = max(0.0, qcap_cm - q_now) * H * 3600 if q_now is not None else None
            F_H = c * A_U_cm * (rain / 1000.0) if rain is not None else None
            inputs = {"rain_24h_mm": rain, "Q_o_now": q_now, "Q_cap_o": qcap_cm,
                      "pumps_running_count": None, "Q_in_up": None,
                      "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None,
                      "upstream_delta_pct": delta_pct,
                      "basin_rain_24h_mm": r24_leading, "basin_rain_72h_mm": r72_leading,
                      "forecast_rain_72h_mm": f72_leading}
            row = make_row("CHIANGMAI", day, c, H, 0,
                            "P.1 (station 3226) -- DEGRADED-SELF-AS-UPSTREAM (no confirmed real upstream gauge)",
                            inputs, False, R_H, 0.0, F_H, flooded,
                            "raw/backtest/hii_history/P1_3226_2567.json + founder's instructions (P.1 5 Oct 2024 onset)",
                            "MEASURED-history(P.1 discharge)/RELAYED(onset date)",
                            notes="P.1 gauge; v5 leading terms use P.1 itself (degraded, no confirmed real upstream)")
            by_unit_scenario.setdefault(("CHIANGMAI", 0.5 if c == 0.5 else 1.0, H, 0), []).append(row)

# ---------------------------------------------------------------------------
# Part C: BANGKOK_EAST 2569 real pumps_2569.csv + canal_normal_levels.yaml.
# ---------------------------------------------------------------------------
pump_codes = {"ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"}
canal_rows = []
pump_rows = []
with open(os.path.join(REPO, "raw/backtest/pumps_2569.csv")) as f:
    for r in csv.DictReader(f):
        day = r["observed_at_utc"][:10]
        if r["variable"] == "pump_level_m" and r["station_code"] in pump_codes:
            pump_rows.append((day, r["station_code"], r["status"]))
        elif r["variable"] in ("canal_water_level_m", "canal_level_0700_m") and r["value"]:
            try:
                val = float(r["value"])
                warn = float(r["warning"]) if r["warning"] else None
                crit = float(r["critical"]) if r["critical"] else None
                bank = float(r["bank"]) if r["bank"] else None
            except ValueError:
                continue
            canal_rows.append((day, r["station_code"] or r["station_name"], val, warn, crit, bank))

rain_bkk_2569 = {}
with open(os.path.join(REPO, "raw/backtest/pumps_2569.csv")) as f:
    for r in csv.DictReader(f):
        if r["variable"] == "rain_24h_mm" and r["value"]:
            day = r["observed_at_utc"][:10]
            rain_bkk_2569.setdefault(day, []).append(float(r["value"]))

BKK_2569_DAYS = sorted({d for d, *_ in canal_rows} | {d for d, *_ in pump_rows})
pumps_total_installed = 1200.0

for day in BKK_2569_DAYS:
    day_canal = [c for c in canal_rows if c[0] == day]
    worst = None
    worst_ratio = -1e9
    for (_, code, val, warn, crit, bank) in day_canal:
        ref = bank or crit or warn or 1.0
        ratio = val / ref if ref else 0
        if ratio > worst_ratio:
            worst_ratio, worst = ratio, (code, val, warn, crit, bank)
    day_pumps = [p for p in pump_rows if p[0] == day]
    running = sum(1 for (_, code, status) in day_pumps if status == "ปกติ")
    n_pump_readings = len(day_pumps)
    running_frac = (running / n_pump_readings) if n_pump_readings else None
    rain = sum(rain_bkk_2569.get(day, [])) if rain_bkk_2569.get(day) else None
    computed_flooded = worst is not None and worst[4] is not None and worst[1] >= worst[4]
    flooded = GT_FLOODED.get(("BANGKOK_EAST", day), computed_flooded)
    r24_leading, r72_leading, f72_leading = basin_rain_24_72_forecast("BANGKOK_EAST", day)

    for c in C_VALUES:
        for H in H_VALUES:
            D_H = (pumps_total_installed * (running_frac if running_frac is not None else 0.0)) * H * 3600
            F_H = c * (UNITS_BY_ID["BANGKOK_EAST"]["A_U"]["value_km2"] * 1e6) * ((rain or 0.0) / 1000.0) if rain is not None else None
            inputs = {
                "rain_24h_mm": rain, "Q_o_now": None, "Q_cap_o": None,
                "pumps_running_count": running if n_pump_readings else None,
                "Q_in_up": None,
                "canal_level_m": worst[1] if worst else None,
                "canal_warning_m": worst[2] if worst else None,
                "canal_critical_m": worst[3] if worst else None,
                "canal_bank_m": worst[4] if worst else None,
                "upstream_delta_pct": None,  # UPSTREAM_GAUGE_UNDECLARED for this unit -- no upstream edge
                "basin_rain_24h_mm": r24_leading, "basin_rain_72h_mm": r72_leading,
                "forecast_rain_72h_mm": f72_leading,
            }
            row = make_row("BANGKOK_EAST", day, c, H, None, None, inputs, True, None, D_H, F_H, flooded,
                            "raw/backtest/pumps_2569.csv (BMA official_telemetry) + sources/canal_normal_levels.yaml",
                            "MEASURED-on-backtest(canal level vs BMA-declared lines)/MEASURED(pump running status)",
                            notes="no upstream gauge declared for this unit (per proposal's own worked-instantiation "
                                  "table) -- upstream_rise_rate structurally absent (UPSTREAM_GAUGE_UNDECLARED)")
            by_unit_scenario.setdefault(("BANGKOK_EAST", c, H, None), []).append(row)

# ---------------------------------------------------------------------------
# Sort each scenario group chronologically and write with persistence applied.
# ---------------------------------------------------------------------------
for key in sorted(by_unit_scenario.keys(), key=lambda k: (k[0], str(k[3]), k[1], k[2])):
    rows = sorted(by_unit_scenario[key], key=lambda r: r["date"])
    write_group(rows)

out_f.close()
print(f"wrote {total_written} rows to {out_path}")
