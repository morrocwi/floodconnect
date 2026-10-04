"""compute_prop_flood_06_sammakorn.py -- calls the EXISTING PROP-FLOOD-06 v5 implementation
(tools/backtest/prop_flood_06_v5.full_tier_v5, imported verbatim, never re-derived -- Toledo
reuse-pipeline discipline, AGENTS.md ss2) for the "sammakorn" unit registered in
raw/backtest/units.yaml, using this run's REAL observations from data/observations.sqlite +
the BMA แผนปฏิบัติการป้องกันและแก้ไขปัญหาน้ำท่วม กทม. 2569 anchors recorded on that unit
(FOUNDER_TASKS_2026-09-27.md row 19).

This module ADAPTS THE CALLER, not the equation: `raw/backtest/units.yaml`'s SAMMAKORN entry
has no `A_U`/`R_H`(outlet) figure (both genuinely OPEN, never estimated -- see that file's own
notes), so `F_H(U)` cannot be computed and this unit is expected to resolve as PARTIAL, not
FULL -- exactly what `full_tier_v5`'s own mode-selection already does for any unit whose ledger
does not resolve. No new tier/promoter/threshold logic is added here.

Write-scope: reads data/observations.sqlite (read-only) and raw/backtest/units.yaml
(read-only, gitignored -- callers must handle it being absent in a fresh checkout).
Writes ONLY to raw/tier_runs/sammakorn_<UTC>.json (new, append-only directory, also
gitignored per AGENTS.md ss2 "never prune" -- each run is its own new file, nothing is
overwritten or deleted).
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from prop_flood_06_v5 import (  # noqa: E402
    full_tier_v5,
    coverage_vector_v5,
    COV5_COMPONENTS,
)

_REPO_ROOT_FOR_LWL = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT_FOR_LWL) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_LWL))
import live_water_level as lwl  # noqa: E402 -- reuses the repo's ONE staleness constant
# (lwl.STALE_HOURS) and the ONE sensor-fault status set (lwl.SENSOR_FAULT_STATUS_TH),
# never re-declared here (a safety fix, 2026-10-02, defects A/D below).

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = REPO_ROOT / "data" / "observations.sqlite"
UNITS_YAML_PATH = REPO_ROOT / "raw" / "backtest" / "units.yaml"
TRACKED_UNITS_YAML_PATH = REPO_ROOT / "sources" / "backtest_units.yaml"
TIER_RUNS_DIR = REPO_ROOT / "raw" / "tier_runs"


def _load_yaml_doc(path: Path) -> dict:
    """Never raises: an absent/unparseable file returns {} so callers fall back to the
    hardcoded defaults below (same defensive posture as every other optional loader in
    this module)."""
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover - defensive
        return {}


def _sammakorn_normalized_fields() -> dict:
    """Task 1 loader discipline (FOUNDER_TASKS_2026-09-27.md #38, follow-up on commit
    9105fa3): the whole PROP-FLOOD-06 unit registry (HATYAI/NAN/CHIANGMAI/
    AYUTTHAYA_BANGBAN/BANGKOK_EAST/SAMMAKORN) used to live ONLY in raw/backtest/
    units.yaml, which .gitignore's `raw/` line excludes entirely from git -- so this
    unit's VERIFIED BMA-plan D_H/pond-capacity figures were never actually tracked.
    Fixed by moving the registry to sources/backtest_units.yaml (tracked, committed,
    `normalized_fields.sammakorn` sub-block, same value/unit/source/page/tag shape for
    every field). This loader reads the TRACKED file FIRST -- the base of record, present
    even in a fresh checkout with no raw/ workspace at all -- and treats
    raw/backtest/units.yaml purely as an optional RUN-TIME OVERRIDE layer on top (used by
    the other backtest runners, run_backtest_v1.py/run_backtest_v2.py, for their own
    untracked what-if edits): if that gitignored file exists and declares its own
    normalized_fields.sammakorn block, its fields win for THIS run only, nothing is ever
    written back to the tracked file from it."""
    tracked = (_load_yaml_doc(TRACKED_UNITS_YAML_PATH).get("normalized_fields") or {}).get(
        "sammakorn") or {}
    override_doc = _load_yaml_doc(UNITS_YAML_PATH)
    override = (override_doc.get("normalized_fields") or {}).get("sammakorn") or {}
    merged = dict(tracked)
    merged.update(override)
    return merged


_SAMMAKORN_FIELDS = _sammakorn_normalized_fields()


def _sammakorn_field(name: str, key: str, default):
    return (_SAMMAKORN_FIELDS.get(name) or {}).get(key, default)


# Design/declared constants for the SAMMAKORN unit -- read from the tracked registry
# above (sources/backtest_units.yaml's normalized_fields.sammakorn block) at import time,
# with the original literal values kept as the fallback default if that file is ever
# absent/unparseable (defensive only -- in normal operation the tracked file always wins).
SAMMAKORN_D_H_M3S = _sammakorn_field(
    "D_H", "value", 7.75)          # VERIFIED, BMA plan 2569 ภาคผนวก ง หน้า ง-25 (ST.SPS.01-04)
SAMMAKORN_D_H_SOURCE = _sammakorn_field(
    "D_H", "source",
    "BMA plan 2569 ภาคผนวก ง หน้า ง-25, ลำดับ 28-31 (ST.SPS.01-04)")
SAMMAKORN_POND_CAPACITY_M3 = _sammakorn_field(
    "pond_storage_capacity_m3", "value", 227200)  # VERIFIED, BMA plan 2569 ภาคผนวก ก หน้า 74 (row 25)
SAMMAKORN_POND_CAPACITY_SOURCE = _sammakorn_field(
    "pond_storage_capacity_m3", "source",
    "BMA แผนปฏิบัติการป้องกันและแก้ไขปัญหาน้ำท่วมกรุงเทพมหานคร ปี 2569 "
    "ภาคผนวก ก หน้า 74 (แถวลำดับที่ 25 บึงรับน้ำหมู่บ้านสัมมากร 227,200 ลบ.ม.)",
)
SAMMAKORN_CANAL_GAUGE_CODE = "WL.SMK.01"

# Nearest official rain gauge to the Sammakorn pond (13.767,100.677) with a live
# rain_24h_mm reading -- สนข.สะพานสูง, ~0.9 km away. Declared here, not re-derived per run
# (a fixed nearest-station choice, matching this repo's own registry.yaml station list).
SAMMAKORN_RAIN_STATION_CODE = "528759"


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path or DB_PATH))


# Task 3 (FOUNDER_TASKS_2026-09-27.md #38): forecast_rain_72h, per-model, worst-case-first.
# Deliberately queries only these two source_ids -- the ensemble-MEMBER source
# ("openmeteo_ensemble_daily_precip", see tools/harvest/forecast7d_draft.py) is a
# DIFFERENT source_id and is never touched by this query, so raw per-member rows are
# skipped entirely by construction, never averaged in with the named per-model rows
# (founder rule: never average across models -- PROP-FLOOD-06 v6.1 forecast-input note,
# "Multi-model inputs are NEVER averaged into one number").
_FORECAST16D_SOURCE_IDS = ("openmeteo_forecast16d", "metno_locationforecast")


def _load_point_forecast_daily(
    conn: Optional[sqlite3.Connection], point_id: str = "sammakorn",
    now_utc: Optional[datetime.datetime] = None,
) -> dict:
    """Per-model DAILY forecast rows for this point. Same query shape as
    site/build_data.py's own `_load_point_forecast_daily()` -- duplicated here rather
    than imported, so this module stays import-independent of site/build_data.py (this is
    a SQL data-access query, not an equation, so the Toledo reuse-pipeline gate that
    governs formulas does not apply to duplicating it). Returns {model: {date_str: mm}},
    {} on any DB error or when this point has no rows yet -- never fabricates a value.

    FIX (2026-10-03, ): previously had NO freshness check at all -- a model's
    cached forecast row, however many days old, fed straight into
    `forecast_rain_72h_per_model` and from there into `RAIN_24H_EXCEEDS_DESIGN`/an L-tier
    promoter. Now drops a row whose own `fetched_at_utc` (issue time) fails
    `lwl.is_fresh(..., lwl.max_age_hours_for('openmeteo_forecast16d'))` -- same single
    gate, same registry-driven cutoff every other reading in this repo uses, keyed on
    this specific row's source_id (`openmeteo_forecast16d` vs `metno_locationforecast`
    can carry different registry cutoffs). `now_utc=None` (the production default) skips
    the check, matching every other OPEN-by-default read in this module -- `compute()`
    always passes a real `now_utc`."""
    if conn is None:
        return {}
    try:
        placeholders = ",".join("?" for _ in _FORECAST16D_SOURCE_IDS)
        rows = conn.execute(
            f"""SELECT station_code, observed_at_utc, value, source_id, fetched_at_utc
                FROM observations
                WHERE source_id IN ({placeholders}) AND station_code LIKE ?
                AND variable = 'precipitation_forecast_daily_mm'""",
            (*_FORECAST16D_SOURCE_IDS, f"{point_id}:%"),
        ).fetchall()
    except Exception:  # pragma: no cover - defensive, optional cache only
        return {}
    out: dict = {}
    for station_code, observed_at_utc, value, source_id, fetched_at_utc in rows:
        if value is None or not observed_at_utc:
            continue
        if now_utc is not None:
            max_age = lwl.max_age_hours_for(source_id)
            fresh, _issue_age_h = lwl.is_fresh(fetched_at_utc, now_utc.isoformat(), max_age)
            # `now_utc` here is always a real wall-clock instant (never an `as_of_date`
            # day-truncated pin -- see `is_fresh`'s own docstring), so a negative
            # `_issue_age_h` can only be a future-dated/clock-skewed `fetched_at_utc`;
            # reject it the same way `_non_stale` does, on top of `is_fresh`'s result.
            if not fresh or _issue_age_h is None or _issue_age_h < 0:
                continue  # issue too old/future/missing/unparseable -- never fed forward
        try:
            model = station_code.split(":", 1)[1]
        except IndexError:
            continue
        date_str = observed_at_utc[:10]  # Bangkok-midnight-as-UTC-instant -> the date
        out.setdefault(model, {})[date_str] = float(value)
    return out


def forecast_rain_72h_per_model(conn: Optional[sqlite3.Connection], point_id: str = "sammakorn",
                                 n_days: int = 3,
                                 now_utc: Optional[datetime.datetime] = None) -> dict:
    """Sums each named model's own earliest `n_days` (default 3 = 72h) available daily
    rows -- a model with fewer than 3 real days left just totals what it actually has,
    never padded with 0s (same convention as site/build_data.py's `_point_forecast_range`).
    Returns {model: mm_total}, an empty dict when no per-model rows exist this run
    (never fabricates a value; caller must treat that as OPEN, not zero).

    `now_utc`, when given, is forwarded to `_load_point_forecast_daily` so a stale-issued
    model forecast is dropped before summing () -- `None` (the default)
    skips that check, matching every other OPEN-by-default read in this module."""
    daily_by_model = _load_point_forecast_daily(conn, point_id, now_utc=now_utc)
    per_model_total: dict = {}
    for model, by_date in daily_by_model.items():
        dates = sorted(by_date)
        if not dates:
            continue
        window = dates[:n_days]
        per_model_total[model] = round(sum(by_date[d] for d in window), 1)
    return per_model_total


def _latest_row(conn: sqlite3.Connection, station_code: str, variable: Optional[str] = None):
    q = ("SELECT station_code, station_name, value, unit, observed_at_utc, warning, critical, "
         "bank, status, trust_tier FROM observations WHERE station_code=?")
    params = [station_code]
    if variable is not None:
        q += " AND variable=?"
        params.append(variable)
    q += " ORDER BY observed_at_utc DESC LIMIT 1"
    row = conn.execute(q, params).fetchone()
    return row


def _non_stale(row, now_utc: Optional[datetime.datetime], source_id: Optional[str] = None):
    """`_latest_row`
    has no time bound of its own -- a reading from days ago could otherwise still unlock
    a tier promoter today. Returns `row` unchanged when it is fresh, else None (treated by
    every caller exactly like "no row this run" -- absent, never a stale value silently
    reused). `now_utc=None` (the production default, real wall clock) skips the check --
    test callers that want a pinned reference pass their own `now_utc`; `compute()` always
    passes one (real `datetime.now(utc)` when the caller gave none itself).

    FIX (2026-10-03, ): now routes through `lwl.is_fresh` -- the SAME single
    freshness-AGE/cutoff gate `readout.py`/`kb.py` use for every other reading in this
    repo -- instead of a local re-inlined `age_h is None or age_h > lwl.STALE_HOURS`
    check. `source_id`, when given, looks up that source's own `max_age_hours` from
    `sources/registry.yaml` via `lwl.max_age_hours_for` (never a new/invented cutoff);
    omitted (the default), it falls back to `lwl.STALE_HOURS` (24h), unchanged from
    before this fix.

    The `age_h < 0` guard stays HERE, on top of `is_fresh`'s result, rather than moving
    into `is_fresh` itself -- `is_fresh` is also called by `readout.py` with an
    `as_of_date`-pinned, deliberately day-TRUNCATED `reference` (local midnight), where a
    real same-day reading legitimately produces a small negative age and must still read
    as fresh (see `is_fresh`'s own docstring); pushing this rejection down into `is_fresh`
    broke that path (VERIFIED: `tests/test_kb_answer.py`'s `test_dual_state_*` suite). A
    real PF06 `now_utc` (always a real wall-clock instant in production, never a
    day-truncated pin) has no such legitimate negative-age case, so the extra guard is
    still correct here, unchanged from before this refactor."""
    if row is None or now_utc is None:
        return row
    max_age = lwl.max_age_hours_for(source_id) if source_id else lwl.STALE_HOURS
    fresh, age_h = lwl.is_fresh(row[4], now_utc.isoformat(), max_age)
    if not fresh or age_h is None or age_h < 0:
        return None
    return row


def gather_real_inputs(conn: Optional[sqlite3.Connection] = None,
                        now_utc: Optional[datetime.datetime] = None) -> dict:
    """Reads this run's REAL, currently-available anchors for the sammakorn unit. Never
    fabricates a value -- every key that has no real row this run stays None/absent, which
    `coverage_vector_v5` then correctly marks 'absent' (never a silent 0).

    - `pond_row` and every `pump_rows` row are dropped (treated as absent) when
        older than `lwl.STALE_HOURS` relative to `now_utc` -- a fresh RED/L5-looking
        promoter can no longer fire off a days-old canal or pump reading. `now_utc=None`
        (no pin) skips this, matching every other OPEN-by-default read in this module.
      - `pumps_running_count` is ONLY ever a non-None number when at least one pump
        STATION this check reported a non-fault status. If pump rows exist this check
        but EVERY one of them is `lwl.SENSOR_FAULT_STATUS_TH` (ขัดข้อง), that is "no
        trustworthy pump reading at all" -- NOT "confirmed zero pumps running". The old
        code conflated the two (`any(pump_rows.values())` true + the fault rows excluded
        from the sum landed on a bare `0`), which let
        PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD (tools/backtest/prop_flood_06_v3.py) fire an
        L5 promoter from 4 faulted sensors alone -- the same kind of invented evidence
        the sensor-fault exclusion in kb.py's own current_local_state classifier
        already bans one call away. Fixed here, in the CALLER (per this module's own
        "adapts the caller, not the equation" discipline) -- the promoter in v3 is
        untouched, never re-derived."""
    owns_conn = conn is None
    conn = conn or _connect()
    try:
        # FIX (2026-10-03, ): `rain_row` used to skip `_non_stale` entirely --
        # the ONLY row in this function not gated by freshness, so stale rain could still
        # feed `RAIN_24H_EXCEEDS_DESIGN`. Now gated the same as every other row here,
        # keyed on its own source_id (`thaiwater_rain_24h`) for the registry-driven cutoff.
        rain_row = _non_stale(
            _latest_row(conn, SAMMAKORN_RAIN_STATION_CODE, "rain_24h_mm"), now_utc,
            source_id="thaiwater_rain_24h")
        pond_row = _non_stale(_latest_row(conn, SAMMAKORN_CANAL_GAUGE_CODE), now_utc,
                               source_id="thaiwater_canal_waterlevel")
        pump_rows = {
            code: _non_stale(_latest_row(conn, code), now_utc, source_id="bma_pumphistory")
            for code in ("ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04")
        }
        # Task 3: forecast_rain_72h, per model, worst case (highest total -- rain is an
        # inflow-raising term, so "worst" := max, per PROP-FLOOD-06 v6.1's own
        # worst_case/best_case convention) fed to the engine; every named model's own
        # value recorded in provenance below, never averaged. `now_utc` forwarded so a
        # stale-issued model forecast cannot promote an L-tier either ().
        per_model_72h = forecast_rain_72h_per_model(conn, now_utc=now_utc)
    finally:
        if owns_conn:
            conn.close()

    # A pump STATION row is trustworthy running-evidence only when it is present,
    # has a real status word (not None -- a row
    # with status=None is not in the fault set either, so it was falling through into
    # this dict and then being summed as "0 pumps running" by the `sum(... if r[8] is
    # not None)` below -- that is fabricated evidence, not an absent reading), AND is
    # not a sensor fault (lwl.SENSOR_FAULT_STATUS_TH).
    non_fault_pump_rows = {
        code: r for code, r in pump_rows.items()
        if r and r[8] is not None and r[8] not in lwl.SENSOR_FAULT_STATUS_TH
    }
    if any(pump_rows.values()) and not non_fault_pump_rows:
        # every pump row that exists this check is a sensor fault -- no trustworthy
        # running-count evidence at all; absent, never a fabricated 0.
        pumps_running_count = None
    elif non_fault_pump_rows:
        pumps_running_count = sum(
            1 for r in non_fault_pump_rows.values() if r[8] is not None)
    else:
        pumps_running_count = None

    if per_model_72h:
        worst_model_72h = max(per_model_72h, key=per_model_72h.get)
        forecast_rain_72h_mm = per_model_72h[worst_model_72h]
    else:
        worst_model_72h = None
        forecast_rain_72h_mm = None

    inputs = {
        "rain_24h_mm": rain_row[2] if rain_row else None,
        "canal_level_m": pond_row[2] if pond_row else None,
        "canal_warning_m": pond_row[5] if pond_row else None,
        "canal_critical_m": pond_row[6] if pond_row else None,
        "canal_bank_m": pond_row[7] if pond_row else None,
        "Q_o_now": None,      # R_H OPEN -- no คลองบ้านม้า 2 discharge/design figure found
        "Q_cap_o": None,      # same
        "pumps_running_count": pumps_running_count,  # see this
        # function's own docstring -- None (absent) when every present pump row this
        # round is a sensor fault, never a fabricated 0.
        "Q_in_up": None,      # no upstream discharge gauge for this village unit
        "upstream_delta_pct": None,
        "tau_up_h": None,
        "upstream_gauge_id": None,
        "basin_rain_24h_mm": None,   # not disaggregated per-model this run -- see report
        "basin_rain_72h_mm": None,
        "forecast_rain_72h_mm": forecast_rain_72h_mm,  # task 3: worst-model 72h total,
        # per-model values recorded in provenance below -- see forecast_rain_72h_per_model()
    }
    provenance = {
        "rain_24h_mm": {
            "station": SAMMAKORN_RAIN_STATION_CODE, "station_name": rain_row[1] if rain_row else None,
            "observed_at_utc": rain_row[4] if rain_row else None, "tag": "MEASURED",
        } if rain_row else {"tag": "OPEN", "note": "no rain_24h_mm row this run"},
        "canal_level_m": {
            "station": SAMMAKORN_CANAL_GAUGE_CODE, "station_name": pond_row[1] if pond_row else None,
            "observed_at_utc": pond_row[4] if pond_row else None, "tag": "MEASURED",
        } if pond_row else {"tag": "OPEN", "note": "no WL.SMK.01 row this run"},
        "pumps_running_count": (
            {
                "stations": {
                    code: (r[8] if r else None) for code, r in pump_rows.items()
                },
                "observed_at_utc": next((r[4] for r in pump_rows.values() if r), None),
                "tag": "MEASURED",
            } if non_fault_pump_rows else
            {
                "stations": {
                    code: (r[8] if r else None) for code, r in pump_rows.items()
                },
                "tag": "OPEN",
                "note": (
                    "no fresh, non-fault pump-station reading this check (every present "
                    "row is a sensor fault, or no row is fresh/present at all) -- "
                    "absent, never read as a confirmed zero"
                ) if any(pump_rows.values()) else "no pump-station row this run",
            }
        ),
        "forecast_rain_72h_mm": (
            {
                "per_model_mm": per_model_72h,
                "worst_model": worst_model_72h,
                "worst_value_mm": forecast_rain_72h_mm,
                "n_models": len(per_model_72h),
                "tag": "RELAYED",
                "note": ("worst model's own next-72h total used as this promoter's "
                         "input (founder rule: never average across models, worst case "
                         "used first); every named model's own value is recorded here, "
                         "per-model, not averaged away -- PROP-FLOOD-06 v6.1 "
                         "forecast-input note (multi_model_scenarios)"),
            } if per_model_72h else
            {"tag": "OPEN", "note": "no per-model 72h forecast rows this run"}
        ),
    }
    return {"inputs": inputs, "provenance": provenance}


def build_unit_tuple(inputs: dict) -> dict:
    """Adapts the caller (this function), not the equation: D_H is this unit's registered
    design pump capacity (VERIFIED, see module header); R_H stays None (OPEN, gravity outlet
    unknown); F_H stays None (A_U OPEN, catchment area unknown) -- the caller supplies no
    F_H key at all when it cannot be computed, exactly like every other unit in
    raw/backtest/units.yaml with an OPEN A_U/outlet."""
    return {
        "pumps_declared": True,
        "R_H": None,
        "D_H": SAMMAKORN_D_H_M3S,
        "F_H": None,
        "inputs": inputs,
    }


_COMPONENT_TH = {
    "rain_obs": "ฝนวัดจริง 24 ชม.", "rain_fcst": "ฝนพยากรณ์", "canal_level_vs_lines": "ระดับบึง/คลอง",
    "river_flow_vs_cap": "อัตราการไหลแม่น้ำเทียบความจุ", "dam_release": "การระบายน้ำจากเขื่อน",
    "pumps_state": "สถานะปั๊ม", "upstream_inflow": "น้ำต้นทาง", "upstream_rise_rate": "อัตราขึ้นของน้ำต้นทาง",
    "basin_rain_accum": "ฝนสะสมลุ่มน้ำต้นทาง", "forecast_rain_72h": "ฝนพยากรณ์ 72 ชม.",
}


def component_label_th(component_key: str) -> str:
    return _COMPONENT_TH.get(component_key, component_key)


# Tier word + colour, verbatim from docs/knowledge/TIER_THRESHOLDS_RATIONALE.md ss2's own
# L0-L5/LR <-> Thai-word table (this repo's own already-adopted convention, not invented
# here). Colours are a declared, OPEN-for-founder-tuning presentation choice (traffic-
# light-style escalation), not part of the PROP-FLOOD-06 registration itself.
TIER_WORD_TH = {
    "L0": "ปกติ", "L1": "เฝ้าดู", "L2": "เตรียมตัวได้ ยังมีเวลา", "L3": "ทำตอนนี้ภายในวันนี้",
    "L4": "เร่งด่วนเดี๋ยวนี้", "L5": "เกินระบบแล้ว", "LR": "ยังคำนวณระดับไม่ได้ (ข้อมูลไม่พอ)",
}
TIER_COLOR = {
    "L0": "#2e7d32", "L1": "#7cb342", "L2": "#f9a825", "L3": "#ef6c00",
    "L4": "#d32f2f", "L5": "#8e0000", "LR": "#757575",
}


def tier_word_th(tier: str) -> str:
    return TIER_WORD_TH.get(tier, tier)


def tier_color(tier: str) -> str:
    return TIER_COLOR.get(tier, "#757575")



# Task 2 (FOUNDER_TASKS_2026-09-27.md #38): engine-version honesty. The registered
# proposal is PROP-FLOOD-06 v6.1 (toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md),
# but this script calls the v5 Python engine (tools/backtest/prop_flood_06_v5.py) --
# never re-derived here, no new tier/promoter/threshold logic added by this check. The
# delta below is the honest, explicit list of what v6.1 registers that this code does
# NOT yet implement.
ENGINE_VERSION_DELTA_ITEMS = (
    "coverage3 present/inferred/absent widening (v6's cov6/readout_v6/full_tier_v6 -- "
    "this engine's coverage_vector_v5 still only has present/absent, a bool)",
    "persisted_v6 L5/LR immediate-bypass hysteresis (a genuine raise into T_L5/T_LR "
    "reported the same hour, no p-consecutive-readout delay -- this engine's own "
    "persistence step, applied by the runner, is still the plain v5 p/q gate)",
    "the general v6.1 multi-model discipline as a registered mechanism (forecast "
    "grid-cell-mean caveat, worst_case/best_case/majority_band/disagreement_flag for "
    "EVERY multi-source input) -- this script implements the SAME worst-case-first "
    "idea ad hoc, for forecast_rain_72h only, not as the general mechanism",
)
ENGINE_VERSION = (
    "full_tier_v5 (code, tools/backtest/prop_flood_06_v5.py) -- proposal v6.1 "
    "(toledo-wt-flood06/docs/proposals/PROP-FLOOD-06.md) not yet fully implemented; "
    "delta: " + "; ".join(ENGINE_VERSION_DELTA_ITEMS)
)
ENGINE_NOTE_TH = "คำนวณด้วยสมการรุ่น 5 ของเรา; รุ่น 6.1 ที่ยื่นไว้ยังไม่ครบในโค้ด"


def compute(now_utc: Optional[datetime.datetime] = None, conn: Optional[sqlite3.Connection] = None) -> dict:
    """Runs full_tier_v5 for the sammakorn unit against this run's real inputs. Returns a
    dict with the readout, the coverage breakdown (present/absent -- this repo's backtest
    ENGINE has no 'inferred' state of its own; PROP-FLOOD-06's v6 coverage3/inferred rung
    is a Coq-level primitive not implemented in this Python backtest engine, so
    coverage_present_components/coverage_absent_components below are the ENGINE's own
    present/absent truth, never silently upgraded. `coverage_inferred_components` is a
    SEPARATE, presentation-only annotation this script adds on top (task 3): whenever
    forecast_rain_72h has a value, it is flagged 'inferred' rather than 'measured' in the
    human-facing coverage_measured_n/coverage_inferred_n counts below, because a forecast
    is not a direct field reading -- this NEVER changes what the engine itself computed
    (forecast_rain_72h still counts as 'present' to full_tier_v5/coverage_vector_v5, so
    its promoter fires exactly per the registered v5 rule, unchanged)."""
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    # Pass now_utc through so canal/pump rows older than
    # lwl.STALE_HOURS are dropped (absent), never silently reused regardless of age.
    gathered = gather_real_inputs(conn, now_utc=now_utc)
    inputs = gathered["inputs"]
    unit_tuple = build_unit_tuple(inputs)
    readout = full_tier_v5(unit_tuple, H=24.0)
    cov = coverage_vector_v5(inputs)

    present = [k for k in COV5_COMPONENTS if cov[k] == "present"]
    absent = [k for k in COV5_COMPONENTS if cov[k] != "present"]
    # Task 3: reporting-only "inferred" annotation -- see compute()'s own docstring above.
    inferred_components = (
        ["forecast_rain_72h"] if inputs.get("forecast_rain_72h_mm") is not None
        and "forecast_rain_72h" in present else []
    )
    measured_components = [k for k in present if k not in inferred_components]

    record = {
        "unit_id": "sammakorn",
        "generated_at_utc": now_utc.isoformat(),
        "engine_version": ENGINE_VERSION,
        "engine_note_th": ENGINE_NOTE_TH,
        "unit_fields": {
            "A_U_km2": {"value": None, "tag": "OPEN", "note": "catchment area, genuinely absent"},
            "D_H_m3s": {"value": SAMMAKORN_D_H_M3S, "tag": "VERIFIED",
                        "source": SAMMAKORN_D_H_SOURCE},
            "R_H_m3s": {"value": None, "tag": "OPEN",
                        "note": "คลองบ้านม้า 2 gravity outlet design capacity, genuinely absent"},
            "pond_storage_capacity_m3": {"value": SAMMAKORN_POND_CAPACITY_M3, "tag": "VERIFIED",
                                          "source": SAMMAKORN_POND_CAPACITY_SOURCE},
        },
        "inputs": inputs,
        "input_provenance": gathered["provenance"],
        "coverage_present_components": present,
        "coverage_absent_components": absent,
        "coverage_present_n": len(present),
        "coverage_absent_n": len(absent),
        "coverage_total_n": len(COV5_COMPONENTS),
        "coverage_inferred_components": inferred_components,
        "coverage_measured_n": len(measured_components),
        "coverage_inferred_n": len(inferred_components),
        "mode": readout.mode,
        "tier": readout.tier,
        "band_tier": readout.band_tier,
        "promoter_tier": readout.promoter_tier,
        "S_H": readout.S_H,
        "promoters_fired": readout.promoters_fired,
        "based_on": readout.based_on,
        "missing": readout.missing,
        "refused_reason": readout.refused_reason,
        "lead_time_h": readout.lead_time_h,
        "calibrated": readout.calibrated,
        "partial_flag": readout.mode == "PARTIAL",
    }
    return record


def write_tier_run(record: dict, out_dir: Optional[Path] = None) -> Path:
    out_dir = out_dir or TIER_RUNS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = record["generated_at_utc"].replace(":", "").replace("+00:00", "Z").replace(".", "")
    out_path = out_dir / f"sammakorn_{ts}.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return out_path


def compute_and_write(now_utc: Optional[datetime.datetime] = None,
                       conn: Optional[sqlite3.Connection] = None,
                       out_dir: Optional[Path] = None) -> tuple[dict, Path]:
    record = compute(now_utc=now_utc, conn=conn)
    path = write_tier_run(record, out_dir=out_dir)
    return record, path


if __name__ == "__main__":  # pragma: no cover - manual/debug entry point
    rec, path = compute_and_write()
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"written to {path}", file=sys.stderr)
