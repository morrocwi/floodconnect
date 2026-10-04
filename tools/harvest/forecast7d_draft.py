#!/usr/bin/env python3
"""
tools/harvest/forecast7d_draft.py -- DRAFT, pure parsers only. Not wired into collect.py.

Normalises the >=7-day precipitation forecast sources censused in
sources/api_census_forecast7d.yaml into one common table shape:

    {source, model, target_date, precip_mm, run_time, horizon_day, tag}

  source      -- census id, e.g. "openmeteo_forecast16d_multimodel", "metno_locationforecast"
  model       -- which model/member within that source, e.g. "ecmwf_ifs025", "gfs_ensemble_p50"
  target_date -- ISO date (UTC) the number applies to
  precip_mm   -- precipitation total for that date, in mm (None if the source had no data
                 for that day -- this is recorded, never silently dropped, so a caller can
                 see exactly where each source's real horizon ends)
  run_time    -- ISO timestamp this forecast was generated/fetched (best available; for
                 samples archived by this check, the archive filename's UTC timestamp)
  horizon_day -- integer, 0 = the day the forecast was made/fetched, 1 = next day, etc.
  tag         -- VERIFIED / MEASURED / MEASURED-vs-forecast / OPEN, per this repo's
                 epistemic-tag convention (AGENTS.md) -- carried per-row, not just per-file,
                 so a downstream consumer never has to go back to the yaml to know a row's
                 evidentiary status.

Every function here is PURE: it takes already-parsed JSON (a dict, already loaded from an
archived raw/live/**/*.json file) and returns a list of row-dicts. No network I/O, no file
writes, no side effects -- this module does not call collect.py's fetch/cache machinery and
is NOT registered in sources/registry.yaml. It exists to be reviewed, and to be promoted to
a real collector (with fetch + store.py wiring + fixtures under tests/) only after
an independent maker != checker review, per AGENTS.md §5.

Run directly for a tiny self-test against this check's own archived samples under raw/live/:

    python3 -m tools.harvest.forecast7d_draft

which loads the real files this check fetched, runs every parser, asserts basic shape
invariants, and prints the Sammakorn cross-source table (median/min/max per day, 7-day
totals, spread, horizon-end per source) -- the same numbers reported in
docs/knowledge/FORECAST_7DAY_SOURCES.md, generated the same way, not hand-copied.
"""
from __future__ import annotations

import glob
import json
import statistics
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
RAW_LIVE = HERE / "raw" / "live"

MULTIMODEL_KEYS = (
    "ecmwf_ifs025", "gfs_seamless", "icon_seamless", "jma_seamless", "gem_seamless",
    "ukmo_seamless", "meteofrance_seamless", "bom_access_global", "cma_grapes_global",
    "knmi_seamless",
)


def _row(source, model, target_date, precip_mm, run_time, horizon_day, tag):
    return {
        "source": source,
        "model": model,
        "target_date": target_date,
        "precip_mm": precip_mm,
        "run_time": run_time,
        "horizon_day": horizon_day,
        "tag": tag,
    }


def parse_openmeteo_multimodel_daily(data: dict, run_time: str, source_id: str = "openmeteo_forecast16d_multimodel") -> list:
    """Open-Meteo /v1/forecast, daily=precipitation_sum, multiple models= in one call.
    Each model column is precipitation_sum_<model>. Returns one row per (model, day),
    precip_mm=None where that model's own real horizon has already ended (a `null` in
    the source array -- this parser never fabricates a 0 in its place).
    """
    daily = data.get("daily", {})
    times = daily.get("time", [])
    rows = []
    for key, values in daily.items():
        if not key.startswith("precipitation_sum_"):
            continue
        model = key[len("precipitation_sum_"):]
        for i, target_date in enumerate(times):
            precip = values[i] if i < len(values) else None
            rows.append(_row(source_id, model, target_date, precip, run_time, i, "VERIFIED"))
    return rows


def parse_openmeteo_ensemble_members(data: dict, run_time: str, source_id: str = "openmeteo_ensemble_daily_precip") -> list:
    """Open-Meteo Ensemble API, daily=precipitation_sum, one model= (many members returned
    as precipitation_sum_member01..NN, plus a bare precipitation_sum for member 0/control).
    Returns one row per (member, day) PLUS synthesised per-day median/p10/p90 summary rows
    (model="<models>_ensemble_median" etc.) -- these summary rows are DERIVED by this
    parser, not sent by the API, and are tagged MEASURED (computed from this check's own
    fetched data) rather than VERIFIED (which this repo reserves for values read directly
    off the wire).
    """
    daily = data.get("daily", {})
    times = daily.get("time", [])
    member_keys = [k for k in daily if k == "precipitation_sum" or k.startswith("precipitation_sum_member")]
    rows = []
    per_day_values = {t: [] for t in times}
    for key in member_keys:
        values = daily[key]
        member = "member00" if key == "precipitation_sum" else key[len("precipitation_sum_"):]
        for i, target_date in enumerate(times):
            precip = values[i] if i < len(values) else None
            rows.append(_row(source_id, f"gfs_ensemble_{member}", target_date, precip, run_time, i, "VERIFIED"))
            if precip is not None:
                per_day_values[target_date].append(precip)
    for i, target_date in enumerate(times):
        vals = per_day_values[target_date]
        if not vals:
            continue
        vals_sorted = sorted(vals)
        median = statistics.median(vals_sorted)
        p10 = vals_sorted[max(0, int(round(0.10 * (len(vals_sorted) - 1))))]
        p90 = vals_sorted[max(0, int(round(0.90 * (len(vals_sorted) - 1))))]
        rows.append(_row(source_id, "gfs_ensemble_median", target_date, median, run_time, i, "MEASURED"))
        rows.append(_row(source_id, "gfs_ensemble_p10", target_date, p10, run_time, i, "MEASURED"))
        rows.append(_row(source_id, "gfs_ensemble_p90", target_date, p90, run_time, i, "MEASURED"))
    return rows


def parse_metno_locationforecast_daily(data: dict, run_time: str, source_id: str = "metno_locationforecast") -> list:
    """MET Norway compact timeseries -> daily totals using ONLY non-overlapping
    `next_6_hours` blocks (timestep hour % 6 == 0). Naively summing every timestep's
    `next_6_hours` block double/triple counts, since consecutive hourly timesteps carry
    overlapping 6h-ahead windows -- this was a real mistake caught and fixed in this same
    task (see sources/api_census_forecast7d.yaml, metno_locationforecast notes) before it
    reached this parser.
    """
    ts = data.get("properties", {}).get("timeseries", [])
    from collections import defaultdict
    totals = defaultdict(float)
    counts = defaultdict(int)
    for entry in ts:
        t = entry["time"]
        hour = int(t[11:13])
        if hour % 6 != 0:
            continue
        det = entry.get("data", {}).get("next_6_hours")
        if not det:
            continue
        v = det.get("details", {}).get("precipitation_amount")
        if v is None:
            continue
        day = t[:10]
        totals[day] += v
        counts[day] += 1
    rows = []
    days_sorted = sorted(totals)
    for i, day in enumerate(days_sorted):
        # a day represented by fewer than 4 non-overlapping 6h blocks is a PARTIAL day
        # (the forecast run started partway through it, or the source's horizon ends
        # partway through it) -- flagged in the row itself via a distinct tag, not
        # silently treated the same as a complete day.
        tag = "VERIFIED" if counts[day] >= 4 else "VERIFIED-partial-day"
        rows.append(_row(source_id, "metno_locationforecast", day, round(totals[day], 1), run_time, i, tag))
    return rows


def parse_openmeteo_previous_runs_skillcheck(data: dict, run_time: str, source_id: str = "openmeteo_previous_runs") -> list:
    """Open-Meteo Previous-Runs API, hourly=precipitation,precipitation_previous_day1,
    precipitation_previous_day3 -> daily sums for three columns: the model's own current
    best estimate for that past day, and what it forecast 1 and 3 days before that day.
    Rows for the "current" column are tagged MEASURED-vs-forecast (a model self-estimate,
    NOT an independent gauge observation -- see caveat in sources/api_census_forecast7d.yaml);
    rows for the previous_dayN columns are the actual past forecasts being skill-checked.
    """
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    from collections import defaultdict
    series = {
        "gfs_seamless_currentbest": hourly.get("precipitation", []),
        "gfs_seamless_forecast_made_1d_before": hourly.get("precipitation_previous_day1", []),
        "gfs_seamless_forecast_made_3d_before": hourly.get("precipitation_previous_day3", []),
    }
    rows = []
    for model, values in series.items():
        if not values:
            continue
        totals = defaultdict(float)
        counts = defaultdict(int)
        for t, v in zip(times, values):
            if v is None:
                continue
            day = t[:10]
            totals[day] += v
            counts[day] += 1
        for i, day in enumerate(sorted(totals)):
            rows.append(_row(source_id, model, day, round(totals[day], 1), run_time, i, "MEASURED-vs-forecast"))
    return rows


def spread_disagreement(max_v: float, min_v: float) -> bool:
    """Founder rule (verbatim, relayed): flag disagreement when `max - min > 20mm` OR
    `max > 3 * min` (guarded against min==0, where the ratio test is skipped and only the
    absolute-difference test applies -- a min of 0mm makes any nonzero max "infinite times"
    bigger, which is not a meaningful ratio)."""
    if (max_v - min_v) > 20:
        return True
    if min_v > 0 and max_v > 3 * min_v:
        return True
    return False


def cross_source_daily_summary(rows: list, models_to_include: Optional[list] = None) -> dict:
    """Given a mixed list of rows (any subset of the parsers above, deterministic models
    only -- caller should exclude the raw ensemble member rows and pass only summary/
    deterministic rows, e.g. the multimodel rows + gfs_ensemble_median + metno), returns
    {target_date: {"median": x, "min": x, "max": x, "n": k, "disagree": bool, "entries": [...]}}.

    Per project decision (verbatim, relayed): the forecast readout must NEVER collapse to one
    number -- always report as a range "min-max (median ~x) from N models", with a spread
    flag when models disagree (see `spread_disagreement()`). `median`/`min`/`max` here are
    the range's own components, not a replacement for reporting the range itself -- callers
    must render all three plus `n`, never `median` alone (see `format_range_readout()`).
    """
    from collections import defaultdict
    by_day = defaultdict(list)
    for r in rows:
        if r["precip_mm"] is None:
            continue
        if models_to_include is not None and r["model"] not in models_to_include:
            continue
        by_day[r["target_date"]].append((r["source"], r["model"], r["precip_mm"]))
    summary = {}
    for day, entries in by_day.items():
        vals = [v for _, _, v in entries]
        mn_v = round(min(vals), 1)
        mx_v = round(max(vals), 1)
        summary[day] = {
            "median": round(statistics.median(vals), 1),
            "min": mn_v,
            "max": mx_v,
            "n": len(vals),
            "disagree": spread_disagreement(mx_v, mn_v),
            "entries": entries,
        }
    return summary


def format_range_readout(day_summary: dict, ensemble_p10: Optional[float] = None, ensemble_p90: Optional[float] = None) -> str:
    """Renders the founder-mandated range readout string for one day, e.g.:
        "14.0-53.1 มม. (มัธยฐาน ~40.4) จาก 11 โมเดล [โมเดลไม่ตรงกัน] (ensemble p10-p90: 8.5-24.7)"
    Never a single number -- always the range, the model count, and the disagreement flag
    (present only when true), plus the ensemble percentile range alongside it when given.
    """
    flag = " [โมเดลไม่ตรงกัน]" if day_summary["disagree"] else ""
    base = f"{day_summary['min']}-{day_summary['max']} มม. (มัธยฐาน ~{day_summary['median']}) จาก {day_summary['n']} โมเดล{flag}"
    if ensemble_p10 is not None and ensemble_p90 is not None:
        base += f" (ensemble p10-p90: {ensemble_p10}-{ensemble_p90})"
    return base


def horizon_end_per_model(rows: list) -> dict:
    """Last target_date each (source, model) pair actually had a non-None value --
    i.e. where that source's real horizon ends, regardless of how many array slots the
    API response nominally had."""
    from collections import defaultdict
    last_seen = {}
    for r in rows:
        if r["precip_mm"] is None:
            continue
        key = (r["source"], r["model"])
        d = r["target_date"]
        if key not in last_seen or d > last_seen[key]:
            last_seen[key] = d
    return last_seen


# --------------------------------------------------------------------------------------
# tiny self-test -- runs the parsers over this check's own archived samples, no network.
# --------------------------------------------------------------------------------------

def _load_latest(pattern: str) -> Optional[dict]:
    matches = sorted(glob.glob(str(RAW_LIVE / pattern)))
    if not matches:
        return None
    with open(matches[-1], encoding="utf-8") as f:
        return json.load(f)


def _selftest() -> None:
    all_rows = []

    d = _load_latest("openmeteo_forecast16d_multimodel/*_sammakorn.json")
    assert d is not None, "missing archived multimodel sample -- run the census fetch first"
    mm_rows = parse_openmeteo_multimodel_daily(d, run_time="2026-09-27T11:35:29Z")
    assert len(mm_rows) == len(MULTIMODEL_KEYS) * 16, f"expected {len(MULTIMODEL_KEYS)*16} rows, got {len(mm_rows)}"
    all_rows.extend(mm_rows)

    d = _load_latest("openmeteo_ensemble_daily/*_sammakorn_gfs.json")
    assert d is not None, "missing archived ensemble sample"
    ens_rows = parse_openmeteo_ensemble_members(d, run_time="2026-09-27T11:37Z")
    assert any(r["model"] == "gfs_ensemble_median" for r in ens_rows), "no median summary row produced"
    all_rows.extend(ens_rows)

    d = _load_latest("metno_locationforecast/*_sammakorn.json")
    assert d is not None, "missing archived MET Norway sample"
    metno_rows = parse_metno_locationforecast_daily(d, run_time="2026-09-27T11:40Z")
    assert len(metno_rows) >= 7, f"expected >=7 daily rows from MET Norway, got {len(metno_rows)}"
    all_rows.extend(metno_rows)

    d = _load_latest("openmeteo_previous_runs/*_skillcheck_hourly.json")
    assert d is not None, "missing archived previous-runs skill-check sample"
    skill_rows = parse_openmeteo_previous_runs_skillcheck(d, run_time="2026-09-27T11:50Z")
    assert len(skill_rows) > 0, "no skill-check rows produced"
    all_rows.extend(skill_rows)

    # cross-source summary over deterministic + ensemble-median + metno rows only
    det_models = list(MULTIMODEL_KEYS) + ["gfs_ensemble_median", "metno_locationforecast"]
    summary = cross_source_daily_summary(all_rows, models_to_include=det_models)
    horizons = horizon_end_per_model(all_rows)

    # per-day ensemble p10/p90 for the range readout (from the raw ens_rows already parsed)
    ens_p10 = {r["target_date"]: r["precip_mm"] for r in ens_rows if r["model"] == "gfs_ensemble_p10"}
    ens_p90 = {r["target_date"]: r["precip_mm"] for r in ens_rows if r["model"] == "gfs_ensemble_p90"}

    print("Founder-mandated range readout, per day (never a single number):")
    for day in sorted(summary):
        s = summary[day]
        print(f"  {day}: {format_range_readout(s, ens_p10.get(day), ens_p90.get(day))}")

    print("\nhorizon end (last non-null day) per (source, model):")
    for (source, model), last_day in sorted(horizons.items()):
        print(f"  {source} / {model}: {last_day}")

    print(f"\nOK -- {len(all_rows)} total normalised rows from {len(set(r['source'] for r in all_rows))} sources, self-test passed.")


if __name__ == "__main__":
    _selftest()
