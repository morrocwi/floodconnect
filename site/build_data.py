#!/usr/bin/env python3
"""
build_data.py -- FloodConnect data.json builder (TWO AREAS: หมู่บ้านสัมมากร + ซอยรามคำแหง 53).

READ-ONLY. Never fetches the network EXCEPT the one optional Playwright navigation for
the hourly rain-forecast strip (item D), which fails soft to "no forecast" if Playwright
or the page layout is unavailable. All flood/canal/pump/tide/community data is read from
CACHED official snapshots already on disk under `raw/` (repo root, relative to this file)
plus compiled files under this script's own `sammakorn/` and `ram53/` input trees, and
writes `data.json` next to this script.

Schema (2026-09-26, area-generalised):
  {
    "generated_at_bkk": ..., "epistemic_note": ..., "default_area": "sammakorn",
    "forecast": {...shared Google-forecast readout, trust_tier third_party_forecast...},
    "areas": {
      "sammakorn": {label, centre, sources, stations_near, pumps, rain, tide,
                    flood_roads, tiers, tiers_note, dds_quotes, dds_report, exits,
                    hospitals, staleness, community, community_label},
      "ram53": {... same shape ...}
    }
  }

Epistemic discipline (see DATA_README.md for the full field-by-field source map):
  - Every number carries its own `observed_at`/`fetched_at` timestamp; this is a READOUT
    of official instruments/reports, never a forecast/risk score (except `forecast`,
    which is explicitly labelled third_party_forecast, not an official Thai source).
  - Community reports are carried as "ชาวบ้านรายงาน"/"เสียงจากอินเทอร์เน็ต" (RELAYED),
    time-stamped, never with a person's name.
  - `classify_level()` / `age_hours()` / `haversine_km()` are IMPORTED from
    live_water_level.py, never re-implemented, so NORMAL/WATCH/CRITICAL/OVERBANK/
    NO_THRESHOLD bands are the one canonical definition for both areas.

Run: python3 build_data.py
"""
from __future__ import annotations

import csv
import datetime
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # PyYAML -- optional; degrade gracefully if absent.
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

# --- Paths --------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent          # .../repo/site
FLOOD_KG = HERE.parent                           # .../repo (repo root)
RAW = FLOOD_KG / "raw"
SAMMAKORN = HERE / "inputs"                      # curated, checked-into-git compiled files
COMMUNITY_DIR = SAMMAKORN / "community"
UPSTREAM_REPORT_PATH = SAMMAKORN / "upstream_watchlist.md"
RAM53_DIR = SAMMAKORN / "ram53"
KHLONGCHAN_SOCIAL_PATH = RAM53_DIR / "social_timeline_khlongchan_2026-09-26.md"
BALANCE_DIR = FLOOD_KG / "site" / "inputs" / "areas"       # *.balance.yaml -- PROP-FLOOD-03 inputs
CANALS_DIR = FLOOD_KG / "site" / "inputs" / "canals"       # *.yaml -- PROP-FLOOD-04 declared graphs
CAPACITY_JSON_PATH = FLOOD_KG / "site" / "inputs" / "capacity" / "bma_capacity.json"
OFFICIAL_DIR = FLOOD_KG / "site" / "inputs" / "official"
BRIEFING_1300_PATH = OFFICIAL_DIR / "bma_briefing_2026-09-26_1300.json"
BRIEFING_1615_PATH = OFFICIAL_DIR / "bma_briefing_2026-09-26_1615.json"
BRIEFING_PATH = OFFICIAL_DIR / "bma_briefing_2026-09-27_1100.json"  # newest -- governor
# interview via media, 27 ก.ย. -- supersedes the two 26 ก.ย. official_report briefings
# (1300/1615, both kept on disk, never deleted) on the hero line. This one carries a
# DIFFERENT trust_tier (official_report-via-media, tag RELAYED) because it is a media
# relay of a spoken interview, not a กทม.-issued document like the 26 ก.ย. pair.

OUT_JSON = HERE / "dist" / "data.json"

# --- Retained-history lookup (review MUST-FIX #1: trend arrows on every station/pump
# row) ------------------------------------------------------------------------------
# `data/observations.sqlite` is collect.py's append-only observation store (never
# rewritten in place -- see its `ux_observations_identity_v2` unique index). This
# build never writes to it, only reads the already-collected history back out, so a
# "previous retained reading" is always a real earlier readout, never a fabricated
# one. This is Toledo PROP-FLOOD-01's lag-k retained-difference construction (RISING/
# FLAT/FALLING/NO_READOUT), applied here with k defined by "most recent reading at
# least PREV_READING_MIN_GAP_HOURS older than the current one" -- not a new formula.
OBS_DB_PATH = FLOOD_KG / "data" / "observations.sqlite"
PREV_READING_MIN_GAP_HOURS = 1.0
_CANAL_SOURCE_ID = "thaiwater_canal_waterlevel"
_PUMP_SOURCE_ID = "bma_pumphistory"


def open_observations_db() -> sqlite3.Connection | None:
    """Read-only connection to the append-only observation store, or None if it is
    absent -- callers must degrade to "no prior reading" (never fabricate one), never
    raise, since this DB is optional local cache, not a required input."""
    if not OBS_DB_PATH.exists():
        return None
    try:
        uri = f"file:{OBS_DB_PATH}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        return conn
    except sqlite3.Error:
        return None


def previous_reading(conn: sqlite3.Connection | None, source_id: str, station_code,
                      cur_value, cur_observed_at_iso: str | None,
                      min_gap_hours: float = PREV_READING_MIN_GAP_HOURS) -> dict | None:
    """Look up the most recent retained observation for (source_id, station_code) that
    is at least `min_gap_hours` OLDER than `cur_observed_at_iso` -- the lag-k retained
    reading PROP-FLOOD-01's trend construction compares against. Returns
    {"value": float, "observed_at": iso_str, "delta": cur_value - value} or None when
    the DB, station_code, current value/timestamp, or any qualifying prior row is
    missing -- never a guessed/interpolated value."""
    if conn is None or not station_code or cur_value is None or not cur_observed_at_iso:
        return None
    try:
        cur_dt = datetime.datetime.fromisoformat(cur_observed_at_iso)
    except (TypeError, ValueError):
        return None
    cutoff_dt = cur_dt - datetime.timedelta(hours=min_gap_hours)
    cutoff_iso = cutoff_dt.isoformat()
    try:
        # Sensor-fault guard (2026-09-27): a row whose `status` column carries a known
        # fault marker (e.g. ขัดข้อง) is excluded here even though its `value` may still
        # be non-NULL for rows written before the parser fix (append-only -- old rows are
        # never rewritten, only marked untrusted at query time, per AGENTS.md's "never
        # prune" rule). New rows are already NULL-valued at write time (see
        # live_water_level.sensor_status_from_status_th / collect_bma_pumphistory), so
        # this filter is a belt-and-braces guard against the historical rows, not the
        # only line of defense.
        fault_placeholders = ",".join("?" for _ in lwl.SENSOR_FAULT_STATUS_TH)
        try:
            row = conn.execute(
                "SELECT value, observed_at_utc FROM observations "
                "WHERE source_id = ? AND station_code = ? AND observed_at_utc <= ? "
                f"AND (status IS NULL OR status NOT IN ({fault_placeholders})) "
                "ORDER BY observed_at_utc DESC LIMIT 1",
                (source_id, station_code, cutoff_iso, *lwl.SENSOR_FAULT_STATUS_TH),
            ).fetchone()
        except sqlite3.OperationalError:
            # A `status`-less observations table (e.g. an older DB file, or a minimal
            # test fixture predating this column) -- degrade to the unfiltered query
            # rather than losing every trend lookup against it. The fault guard is then
            # simply unavailable for that DB, not a hard failure.
            row = conn.execute(
                "SELECT value, observed_at_utc FROM observations "
                "WHERE source_id = ? AND station_code = ? AND observed_at_utc <= ? "
                "ORDER BY observed_at_utc DESC LIMIT 1",
                (source_id, station_code, cutoff_iso),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None or row[0] is None:
        return None
    prev_value, prev_observed_at = row
    try:
        prev_value = float(prev_value)
    except (TypeError, ValueError):
        return None
    return {"value": prev_value, "observed_at": prev_observed_at,
            "delta": cur_value - prev_value}


# --- Per-canal normal/control level + back-to-normal readout (build 5, 2026-09-27) ----
# Founder ask (verbatim): "สกัดหาประโยชน์มาให้ได้ เพื่อให้คลองกลายเป็น node ที่จะระบุได้ง่ายๆ
# ว่าสถานการณ์กลับสู่ปกติ คลองนี้ควรอยู่ที่เลขเท่าไหร่". Rule (mirrors
# tools/kg/build_kg.py's apply_canal_normal_levels(), kept independent/self-contained
# here since this file does not import that module): normal_level_m = the live BMA
# `water_control` value (VERIFIED-BMA-control, data/observations.sqlite,
# bma_watermap/bma_station_detail) if present, else the dry-season median
# (MEASURED-history, sources/canal_normal_levels.yaml), else None/OPEN.
#
# "Time to back-to-normal" below is Toledo PROP-FLOOD-02 (time-to-threshold) --
# PROPOSAL, UNVERIFIED, not yet registered in Toledo (see AGENTS.md §8's own note that
# this proposal existed only in planning docs until this build). Simple linear
# extrapolation from PROP-FLOOD-01's own lag-k retained-difference rate
# (previous_reading() above) -- REFUSED (never computed) when the trend is flat/rising,
# when the level is already at/below normal from the wrong side, or when no qualifying
# prior reading exists (PROP-FLOOD-01's own >= PREV_READING_MIN_GAP_HOURS floor already
# enforces the ">= 60 minutes of history" requirement -- reused, not re-implemented).
CANAL_NORMAL_LEVELS_PATH = FLOOD_KG / "sources" / "canal_normal_levels.yaml"


# P0 fix, 2026-09-27 (orchestrator-verified real incident): an `official_threshold` row
# in sources/canal_normal_levels.yaml (WL.BMA.02, re-keyed to ST.SPS.01 the same day --
# see that file's CORRECTION note) was applied to a station ~630 m away on a different,
# unconfirmed datum. Re-keying the mislocated row fixes THAT incident, but the general
# hole -- an official_threshold row could be mis-authored again -- stays open unless the
# loader itself refuses to apply one that isn't demonstrably about the station it's
# keyed to. `station_distance_m` (declared at authoring time: distance between the row's
# own lat/lon and the station's independently-known location, e.g.
# docs/knowledge/bma_plan2569_stations.yaml) and `datum` are therefore load-bearing
# fields for `basis: official_threshold` rows, not decoration -- absent/too-far/unknown
# = refused, never silently applied. `unknown = refuse` (never guess) per AGENTS.md §2
# and sources/rain_alert_thresholds_crosswalk.yaml rule R4 ("compare only same station,
# same datum").
OFFICIAL_THRESHOLD_MAX_DISTANCE_M = 100.0
_DATUM_UNKNOWN_VALUES = {None, "", "OPEN", "open", "unknown", "UNKNOWN", "UNCONFIRMED",
                         "unconfirmed"}


def _official_threshold_row_admissible(row: dict) -> bool:
    """True only when an `official_threshold` row declares BOTH a same-station distance
    (<= OFFICIAL_THRESHOLD_MAX_DISTANCE_M) and a confirmed (non-OPEN/unknown) datum.
    Any other basis (dry_season_median/MEASURED-history) is untouched by this guard --
    it only gates the "official printed ceiling" path, which is the one that can be
    mis-keyed to the wrong station/datum (real incident, see module note above)."""
    dist = row.get("station_distance_m")
    if dist is None:
        return False
    try:
        if float(dist) > OFFICIAL_THRESHOLD_MAX_DISTANCE_M:
            return False
    except (TypeError, ValueError):
        return False
    if row.get("datum") in _DATUM_UNKNOWN_VALUES:
        return False
    return True


def load_canal_normal_levels() -> dict:
    """sources/canal_normal_levels.yaml -> {station_code: row}. Never raises -- a
    missing/unparseable file degrades to {} (OPEN for every station), same posture as
    this file's other optional-input loaders. An `official_threshold` row that fails
    `_official_threshold_row_admissible()` (mislocated and/or unconfirmed datum) is
    dropped here -- never returned to a caller, never rendered as if it applied."""
    if not HAVE_YAML or not CANAL_NORMAL_LEVELS_PATH.is_file():
        return {}
    try:
        doc = yaml.safe_load(CANAL_NORMAL_LEVELS_PATH.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover - defensive, malformed yaml never crashes the build
        return {}
    out = {}
    for r in (doc.get("canals") or []):
        code = r.get("station_code")
        if not code:
            continue
        if r.get("basis") == "official_threshold" and not _official_threshold_row_admissible(r):
            continue  # REFUSED: mislocated (>100 m) and/or datum unconfirmed -- never applied
        out[code] = r
    return out


def latest_bma_control_level(conn, station_code: str) -> dict | None:
    """Latest `water_control_m` observation for this BMA station code, from whichever
    of bma_watermap/bma_station_detail fetched it most recently. None if absent/no DB --
    never fabricated."""
    if conn is None or not station_code:
        return None
    try:
        row = conn.execute(
            "SELECT value, observed_at_utc, fetched_at_utc, source_id FROM observations "
            "WHERE station_code = ? AND variable = 'water_control_m' AND value IS NOT NULL "
            "AND source_id IN ('bma_watermap', 'bma_station_detail') "
            "ORDER BY fetched_at_utc DESC LIMIT 1",
            (station_code,),
        ).fetchone()
    except sqlite3.Error:  # pragma: no cover - defensive
        return None
    if row is None:
        return None
    value, observed_at, fetched_at, source_id = row
    return {"value": value, "observed_at": observed_at, "fetched_at": fetched_at,
            "source_id": source_id}


def resolve_normal_level(conn, station_code: str, dry_season_rows: dict) -> dict:
    """Rule: BMA water_control (VERIFIED-BMA-control) > an official printed threshold
    from sources/canal_normal_levels.yaml (`basis: official_threshold`, e.g.
    ST.SPS.01's plan-C ceiling, TODO #50/#62 2026-09-27; corrected 2026-09-27 -- this
    row was mis-keyed to WL.BMA.02, a different station ~630 m away, see that file's
    CORRECTION note and load_canal_normal_levels()'s admissibility guard above) >
    dry-season median (MEASURED-history) >
    None/OPEN. Returns {"value": float|None, "basis": str}."""
    control = latest_bma_control_level(conn, station_code) if station_code else None
    if control is not None:
        return {"value": control["value"], "basis": "VERIFIED-BMA-control"}
    dry = dry_season_rows.get(station_code) if station_code else None
    if dry is not None and dry.get("normal_level_m") is not None:
        if dry.get("basis") == "official_threshold":
            return {"value": dry["normal_level_m"], "basis": "OFFICIAL-BMA-plan"}
        return {"value": dry["normal_level_m"], "basis": "MEASURED-history"}
    return {"value": None, "basis": "OPEN"}


PROP_FLOOD_02_FLAT_RATE_M_PER_H = 0.01  # declared convention -- |rate| below this is FLAT


def prop_flood_02_time_to_threshold(current_value, current_observed_at_iso: str | None,
                                     prev_reading: dict | None, threshold_value) -> dict:
    """PROP-FLOOD-02, PROPOSAL/UNVERIFIED -- simple linear extrapolation of the
    PROP-FLOOD-01 lag-k rate to the declared threshold. Returns one of:
      {"status": "already_at_or_below", ...}      -- current_value <= threshold already
      {"status": "refused", "reason": "..."}      -- no history / flat / rising away
      {"status": "ok", "hours": float, "rate_m_per_h": float}
    Never fabricates an hours figure outside these three cases."""
    if current_value is None or threshold_value is None:
        return {"status": "refused", "reason": "no_current_or_threshold_value"}
    if current_value <= threshold_value:
        return {"status": "already_at_or_below"}
    if prev_reading is None or current_observed_at_iso is None:
        return {"status": "refused", "reason": "no_qualifying_prior_reading"}
    try:
        cur_dt = datetime.datetime.fromisoformat(current_observed_at_iso)
        prev_dt = datetime.datetime.fromisoformat(prev_reading["observed_at"])
    except (TypeError, ValueError, KeyError):
        return {"status": "refused", "reason": "unparseable_timestamp"}
    hours_between = (cur_dt - prev_dt).total_seconds() / 3600.0
    if hours_between <= 0:
        return {"status": "refused", "reason": "non_positive_time_gap"}
    rate_m_per_h = prev_reading["delta"] / hours_between  # negative == falling
    if rate_m_per_h > -PROP_FLOOD_02_FLAT_RATE_M_PER_H:
        # flat (|rate| below the declared convention) or rising -- never extrapolate
        return {"status": "refused", "reason": "trend_flat_or_rising"}
    hours = (current_value - threshold_value) / (-rate_m_per_h)
    return {"status": "ok", "hours": hours, "rate_m_per_h": rate_m_per_h}


def canal_normal_level_readout(conn, station_code: str, current_value, current_observed_at_iso,
                                dry_season_rows: dict, min_gap_hours: float = PREV_READING_MIN_GAP_HOURS,
                                source_id: str = "thaiwater_canal_waterlevel") -> dict | None:
    """Builds one canal node's "back to normal" readout dict (basis + current diff +
    trend + time-to-threshold text), or None when the station has no normal_level_m at
    all (OPEN -- caller should render nothing, not a fabricated line). Never itself
    writes to observations.sqlite (read-only lookups)."""
    if not station_code:
        return None
    normal = resolve_normal_level(conn, station_code, dry_season_rows)
    basis_label = {
        "VERIFIED-BMA-control": "ควบคุม กทม.",
        "OFFICIAL-BMA-plan": "เกณฑ์ทางการ (แผน กทม.)",
        "MEASURED-history": "ค่ากลางฤดูแล้ง",
        "OPEN": None,
    }[normal["basis"]]
    if normal["value"] is None:
        return {"normal_level_m": None, "basis": "OPEN", "basis_label": None,
                "readout_th": None, "status": "open"}
    diff_m = (current_value - normal["value"]) if current_value is not None else None
    prev = previous_reading(conn, source_id, station_code, current_value,
                             current_observed_at_iso, min_gap_hours=min_gap_hours)
    ttt = prop_flood_02_time_to_threshold(current_value, current_observed_at_iso, prev,
                                          normal["value"])
    out = {
        "normal_level_m": normal["value"], "basis": normal["basis"], "basis_label": basis_label,
        "current_value_m": current_value, "diff_m": diff_m,
    }
    if current_value is None:
        out["status"] = "refused"
        out["readout_th"] = "ยังบอกไม่ได้ (ไม่มีค่าปัจจุบัน)"
    elif ttt["status"] == "already_at_or_below":
        out["status"] = "at_normal"
        out["readout_th"] = f"ปกติ ≈ {normal['value']:.2f} ม. · ตอนนี้ {diff_m:+.2f} ม. · ปกติแล้ว"
    elif ttt["status"] == "refused":
        out["status"] = "refused"
        out["readout_th"] = "ยังบอกไม่ได้"
        out["refused_reason"] = ttt["reason"]
    else:
        out["status"] = "trending_to_normal"
        out["hours_to_normal"] = round(ttt["hours"], 1)
        out["readout_th"] = (
            f"ปกติ ≈ {normal['value']:.2f} ม. · ตอนนี้ {diff_m:+.2f} ม. · "
            f"แนวโน้ม ลง → กลับสู่ปกติ ~{ttt['hours']:.0f} ชม.")
    return out


def canal_normal_level_hero_summary(readouts: list) -> dict:
    """Aggregate "how many nearby canals are back to normal" line, over a list of
    canal_normal_level_readout() results (skipping None/OPEN entries -- never counted
    as either normal or not-normal)."""
    known = [r for r in readouts if r and r.get("status") not in (None, "open")]
    at_normal = sum(1 for r in known if r["status"] == "at_normal")
    return {"known": len(known), "at_normal": at_normal,
            "readout_th": (f"{at_normal}/{len(known)} คลองใกล้เคียงกลับสู่ระดับปกติแล้ว"
                            if known else None)}


_HOUSE_RANGE_RE = re.compile(r"\s*\(\d+\s*[-–]\s*\d+\)")


def strip_house_range(s):
    """Drop trailing/inline house-number ranges like '(251-260)' from a soi/place name --
    they come from raw community reports and are not meaningful once grouped by soi."""
    if not s:
        return s
    return _HOUSE_RANGE_RE.sub("", s).strip()

sys.path.insert(0, str(FLOOD_KG))
try:
    import parsers  # noqa: E402 -- repo-root parsers.py (openmeteo forecast parser, etc.)
except Exception:  # pragma: no cover - defensive fallback, same posture as lwl below
    parsers = None
try:
    import water_balance as wbmod  # noqa: E402 -- Toledo PROP-FLOOD-03 (proposal, PR #60)
except Exception:  # pragma: no cover - defensive fallback
    wbmod = None
try:
    import canal_graph as cgmod  # noqa: E402 -- Toledo PROP-FLOOD-04 (proposal)
except Exception:  # pragma: no cover - defensive fallback
    cgmod = None
try:
    import burden_ledger as blmod  # noqa: E402 -- Toledo PROP-FLOOD-05a/05b (proposals, PR #62)
except Exception:  # pragma: no cover - defensive fallback
    blmod = None
try:
    import store  # noqa: E402 -- append-only observations.sqlite (readout_log table)
except Exception:  # pragma: no cover - defensive fallback
    store = None
try:
    from tools import reconcile as reconcile_mod  # noqa: E402 -- build 4, 2026-09-27:
    # bma_watermap vs thaiwater_canal_waterlevel cross-source reconciliation
except Exception:  # pragma: no cover - defensive fallback
    reconcile_mod = None
try:
    from tools import layer0 as layer0mod  # noqa: E402 -- LAYER 0 (น้ำเข้า/น้ำออก/รับมือได้),
    # PROPOSAL-derived simplification of PROP-FLOOD-06 -- see docs/LAYER0_IN_OUT_CAPACITY.md.
    # Written as a standalone new-files-only module by another worker this build; wired
    # into the live pipeline here (was not wired in by that worker's own write-scope).
    from tools.layer0.render_block import render_layer0_block as _render_layer0_block
except Exception:  # pragma: no cover - defensive fallback, same posture as the imports above
    layer0mod = None
    _render_layer0_block = None
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "backtest"))
    import compute_prop_flood_06_sammakorn as pf06mod  # noqa: E402 -- PROP-FLOOD-06 v5
    # engine (tools/backtest/prop_flood_06_v5.py), called for the "sammakorn" unit
    # (raw/backtest/units.yaml) -- founder task 2026-09-27, FOUNDER_TASKS row 19.
except Exception:  # pragma: no cover - defensive fallback, same posture as layer0mod above
    pf06mod = None
try:
    from tools.harvest.forecast7d_draft import spread_disagreement  # noqa: E402 -- reuse the
    # ALREADY-documented "models disagree" rule (max-min>20mm OR max>3*min when min>0)
    # instead of re-deriving a second copy of the same threshold -- see
    # docs/knowledge/FORECAST_7DAY_SOURCES.md ss2 and that module's own docstring.
except Exception:  # pragma: no cover - defensive fallback, same posture as the imports above
    def spread_disagreement(max_v, min_v):  # type: ignore[no-redef]
        if (max_v - min_v) > 20:
            return True
        if min_v > 0 and max_v > 3 * min_v:
            return True
        return False
try:
    import live_water_level as lwl  # noqa: E402
except Exception as _lwl_exc:  # pragma: no cover - defensive fallback

    class _LwlFallback:
        SENSOR_FAULT_STATUS_TH = {"ขัดข้อง"}
        NO_NORMAL_LEVEL = object()

        @staticmethod
        def sensor_status_from_status_th(status_th):
            if not status_th:
                return None
            return "fault" if status_th in _LwlFallback.SENSOR_FAULT_STATUS_TH else "ok"

        @staticmethod
        def classify_level(value, warning, critical, bank, normal_level=None):
            opted_in = normal_level is not None
            if normal_level is _LwlFallback.NO_NORMAL_LEVEL or normal_level is None:
                nl = None
            else:
                try:
                    nl = float(normal_level)
                except (TypeError, ValueError):
                    nl = None
            if value is None:
                return "NO_THRESHOLD"
            if warning is None and critical is None and bank is None and not opted_in:
                return "NO_THRESHOLD"
            if bank is not None and value >= bank:
                return "OVERBANK"
            if critical is not None and value >= critical:
                return "CRITICAL"
            if warning is not None and value >= warning:
                return "WATCH"
            if opted_in:
                if nl is None:
                    return "NO_NORMAL_BASIS"
                return "NORMAL" if value <= nl else "ABOVE_NORMAL"
            if warning is None and critical is None and bank is None:
                return "NO_THRESHOLD"
            return "NORMAL"

        @staticmethod
        def age_hours(observed_at_iso, ref_iso):
            if not observed_at_iso:
                return None
            try:
                d = datetime.datetime.fromisoformat(observed_at_iso)
                ref = datetime.datetime.fromisoformat(ref_iso)
            except (TypeError, ValueError):
                return None
            return (ref - d).total_seconds() / 3600.0

        @staticmethod
        def haversine_km(lat1, lon1, lat2, lon2):
            import math
            r = 6371.0
            p1, p2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlmb = math.radians(lon2 - lon1)
            a = (math.sin(dphi / 2) ** 2
                 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
            return 2 * r * math.asin(min(1.0, a ** 0.5))

        @staticmethod
        def load_thaiwater_stations_from_file(_path):
            return []

        @staticmethod
        def load_pumphistory_from_file(_path, station_codes=None):
            return []

    lwl = _LwlFallback()

BANGKOK_TZ = datetime.timezone(datetime.timedelta(hours=7))
# Documented (2026-10-03): this is a DIFFERENT, DELIBERATELY TIGHTER cutoff
# than `live_water_level.STALE_HOURS`/`max_age_hours_for` (24h), which is the actual
# decision gate `kb.py`/`readout.py` use before anything is classified RED/YELLOW/GREEN.
# This file's `STALE_HOURS`/`is_stale()`/`freshness_tag()` feed only the PUBLIC SITE's own
# fresh/stale/expired display tag for a reading already shown on a tile -- a UI
# freshness label for a human glancing at the page, not a second decision gate -- so the
# SAME row can legitimately read "stale" on the site tile (>2h old) while the `answer`
# CLI/MCP path still counts it as fresh evidence (<=24h) for its own classification. Not
# unified into one cutoff: the two are different consumers (a decision vs. a display
# label) with different honest tolerances, and unifying them would either hide genuinely
# fresh data behind a 2h display badge or let the display call a day-old reading "fresh".
STALE_HOURS = 2.0
NEAR_STATION_RADIUS_KM = 5.0   # generalised per-centre radius (task spec: stations ≤5 km)
PUMP_RADIUS_KM = 2.5           # generalised per-centre radius (task spec: pumps ≤2.5 km)
FLOOD_ROAD_RADIUS_KM = 5.0
HOSPITAL_RADIUS_KM = 5.0
RAIN_GAUGE_RADIUS_KM = 4.0     # "3 nearest gauges (<= 4 km)" -- RAIN NOW item

# Design drainage capacity -- VERIFIED against the source document itself (see
# raw/capacity/CAPACITY_NOTE.md, not committed -- it quotes the exact Thai sentence).
# "โดยขีดความสามารถของระบบระบายน้ำสามารถรองรับปริมาณฝนตกสะสมรวมได้ไม่เกิน 80 มิลลิเมตร
# ใน 1 วัน ... หรือแปลงเป็นความเข้มของฝนไม่เกิน 58.7 มิลลิเมตรต่อชั่วโมง"
DESIGN_CAPACITY_MM_PER_HOUR = 58.7
DESIGN_CAPACITY_MM_PER_DAY = 80.0
DESIGN_CAPACITY_SOURCE_TH = ("แผนปฏิบัติราชการประจำปี พ.ศ. 2569 สำนักการระบายน้ำ กทม., "
                              "หน้า 4 — อ่านตรงจากเอกสารต้นทาง")
# 2026-09-28 (an earlier check mobile verifier, raw-token cleanup): the raw evidence-tier
# token used to be baked into this Thai sentence as literal "(VERIFIED -- ...)"
# text, leaking straight to residents. The tier itself is unchanged (still
# VERIFIED -- read directly off the source document) -- it now reaches the page
# only via build_page.py's `_tag_pill("VERIFIED")`, same as every other tagged
# source on the page, not as English text inside a Thai sentence.
DESIGN_CAPACITY_SOURCE_TAG = "VERIFIED"

POND_NAME_BY_PUMP_CODE = {
    "ST.SPS.02": "บึงรับน้ำสัมมากร 4",
    "ST.SPS.03": "บึงรับน้ำสัมมากร 2",
    "ST.SPS.04": "บึงรับน้ำสัมมากร 1",
    "ST.SPS.01": None,
}

TIER_LABELS_FALLBACK = {
    "T1": "น้ำเข้าบ้านเร็วที่สุด (ก่อน 6 โมงเช้า หรือลึกเกิน 20 ซม.)",
    "T2": "น้ำเข้าบ้าน/โรงรถ ช่วง 6-8 โมงเช้า",
    "T3": "น้ำเข้าโรงรถ/ท่วมทั้งซอย ช่วง 8-10 โมงเช้า",
    "T4": "น้ำท่วมถนน/ซึมเข้าบ้าน หลัง 10 โมงเช้า",
    "T5": "ยังไม่มีรายงาน — ไม่ได้แปลว่าปลอดภัย",
}
TIER_ORDER = ["T1", "T2", "T3", "T4", "T5"]

UPSTREAM_STRIP_PREFIXES = ["ปตร.", "ปตร ", "ค.", "คลอง", "ส.", "สถานี"]


# --- small generic helpers -------------------------------------------------------------

def newest_file(directory: Path, pattern: str = "*") -> Path | None:
    if not directory.is_dir():
        return None
    candidates = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def newest_file_any(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    candidates = sorted(directory.glob("*"), key=lambda p: p.stat().st_mtime)
    candidates = [p for p in candidates if p.is_file()]
    return candidates[-1] if candidates else None


def to_utc_iso(local_dt_str: str, fmt: str) -> str | None:
    if not local_dt_str:
        return None
    try:
        dt = datetime.datetime.strptime(local_dt_str, fmt)
    except ValueError:
        return None
    dt = dt.replace(tzinfo=BANGKOK_TZ)
    return dt.astimezone(datetime.timezone.utc).isoformat()


def is_stale(observed_at_iso: str | None, ref_iso: str) -> bool:
    hrs = lwl.age_hours(observed_at_iso, ref_iso)
    if hrs is None:
        return True
    return hrs > STALE_HOURS


def age_class(observed_at_iso: str | None, ref_iso: str) -> str:
    """fresh|stale|expired classification, reusing STALE_HOURS/lwl.age_hours --
    the SAME cutoff is_stale() already applies, not a second/new threshold
    (tools/api/export_api.py imports this rather than re-deriving its own
    cutoff -- see FloodConnect API v1 spec sec.1, "freshness rule, reuse not
    reinvent"). `expired` = the age could not even be computed (missing or
    unparseable observed_at) -- distinct from `stale` (a real, aged reading).
    `fresh`/`stale` split is exactly is_stale()'s own STALE_HOURS boundary."""
    if not observed_at_iso:
        return "expired"
    hrs = lwl.age_hours(observed_at_iso, ref_iso)
    if hrs is None:
        return "expired"
    return "stale" if hrs > STALE_HOURS else "fresh"


def fetched_at_of(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    return datetime.datetime.fromtimestamp(
        path.stat().st_mtime, tz=datetime.timezone.utc
    ).isoformat()


# --- 1. BMA canal water-level stations (thaiwater.net) ---------------------------------

def load_canal_stations() -> tuple[list[dict], Path | None]:
    path = newest_file_any(RAW / "live" / "thaiwater_bma")
    if path is None:
        return [], None
    stations = lwl.load_thaiwater_stations_from_file(path)
    return stations, path


# --- 2. BMA PumpHistory ------------------------------------------------------------------

def load_pump_rows(station_codes: list[str]) -> tuple[list[dict], Path | None]:
    path = newest_file_any(RAW / "live" / "pumphistory")
    if path is None:
        return [], None
    rows = lwl.load_pumphistory_from_file(path, station_codes=station_codes)
    return rows, path


# --- 3. Rain (24h, nearest station to a given centre) ------------------------------------

def _rain_tier_word(mm_24h: float | None) -> str:
    """Plain-word tier for a 24h rainfall total -- Dr-tier engineering judgment (this
    codebase's own bucketing, not an agency-issued category), used only for the hero
    tile's plain-language line, never as a computed risk score."""
    if mm_24h is None:
        return ""
    if mm_24h >= 150:
        return "หนักมาก"
    if mm_24h >= 90:
        return "หนัก"
    if mm_24h >= 35:
        return "ปานกลาง"
    if mm_24h > 0:
        return "เบา"
    return "ไม่มีฝน"


def load_rain(generated_at_utc_iso: str, centre_lat: float, centre_lon: float) -> tuple[dict | None, Path | None]:
    # collect.py's thaiwater_rain_24h collector (added 2026-09-26)
    # writes a fresh snapshot every run to raw/live/thaiwater_rain_24h/<ts>.json; the
    # raw/gapfill/rain_24h*.json manual snapshot is now only a fallback for a run where
    # that collector hasn't run yet or failed.
    #
    # RAIN NOW (2026-09-26): the snapshot carries `rain_1h` alongside `rain_24h` per
    # station -- this function now also returns the 3 NEAREST gauges within
    # RAIN_GAUGE_RADIUS_KM (4 km) as `gauges`, each with its own rain_1h/rain_24h/time,
    # so the hero tile can show "ฝนตอนนี้" (rain_1h at the nearest gauge) alongside the
    # 24h total, instead of only the single nearest station regardless of distance.
    path = newest_file(RAW / "live" / "thaiwater_rain_24h", "*.json")
    if path is None:
        path = newest_file(RAW / "gapfill", "rain_24h*.json")
    if path is None:
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, path
    rows = data.get("data") or []
    candidates = []
    for rec in rows:
        station = rec.get("station") or {}
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if lat is None or lon is None or rec.get("rain_24h") is None:
            continue
        dist = lwl.haversine_km(centre_lat, centre_lon, float(lat), float(lon))
        observed_at = to_utc_iso(rec.get("rainfall_datetime"), "%Y-%m-%d %H:%M")
        candidates.append({
            "name": (station.get("tele_station_name") or {}).get("th"),
            "dist_km": round(dist, 2),
            "rain_1h": rec.get("rain_1h"),
            "rain_24h": rec.get("rain_24h"),
            "time": observed_at,
            "agency_th": ((rec.get("agency") or {}).get("agency_name") or {}).get("th"),
            "_dist_raw": dist,
        })
    if not candidates:
        return None, path
    candidates.sort(key=lambda c: c["_dist_raw"])
    best = candidates[0]
    gauges = [{k: v for k, v in c.items() if k != "_dist_raw"}
              for c in candidates if c["_dist_raw"] <= RAIN_GAUGE_RADIUS_KM][:3]
    observed_at = best["time"]
    return {
        "station": best["name"],
        "dist_km": best["dist_km"],
        "mm_24h": best["rain_24h"],
        "mm_1h": best["rain_1h"],
        "observed_at": observed_at,
        "agency_th": best["agency_th"],
        "stale": is_stale(observed_at, generated_at_utc_iso),
        "tier_word": _rain_tier_word(best["rain_24h"]),
        "gauges": gauges,
    }, path


# --- 4. Tide (Royal Thai Navy Hydrographic Dept, astronomical prediction, shared) ---------

def load_tide(generated_at_utc_iso: str) -> tuple[dict | None, Path | None]:
    path = newest_file(RAW / "tide", "*.json")
    if path is None:
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, path
    meta = data.get("meta", {})
    rows = data.get("rows", [])
    now_local = datetime.datetime.now(BANGKOK_TZ)

    def row_dt(r):
        try:
            return datetime.datetime.strptime(
                f"{r['date']} {r['time_local']}", "%Y-%m-%d %H:%M"
            ).replace(tzinfo=BANGKOK_TZ)
        except (KeyError, ValueError):
            return None

    highs = []
    for r in rows:
        if r.get("event") != "HW":
            continue
        dt = row_dt(r)
        if dt is None or dt < now_local:
            continue
        highs.append((dt, r))
    highs.sort(key=lambda x: x[0])
    next_high = [
        {"time": dt.isoformat(), "height_m": r.get("height_m"),
         "hours_until": round((dt - now_local).total_seconds() / 3600.0, 1)}
        for dt, r in highs[:3]
    ]

    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = now_local + datetime.timedelta(days=7)
    week_map: dict[str, list] = {}
    for r in rows:
        dt = row_dt(r)
        if dt is None or dt < today_start or dt > week_end:
            continue
        week_map.setdefault(r["date"], []).append(
            {"t": r["time_local"], "kind": r["event"], "h": r.get("height_m")}
        )
    week = [{"date": d, "events": sorted(week_map[d], key=lambda e: e["t"])}
            for d in sorted(week_map.keys())]

    return {
        "datum": meta.get("datum"),
        "station_th": meta.get("station_th"),
        "prediction_basis": meta.get("prediction_basis"),
        "next_high": next_high,
        "week": week,
    }, path


# --- 5. Flood roads (thaiwater.net flood_road, within FLOOD_ROAD_RADIUS_KM) --------------

def parse_flood_road_records(data: dict) -> list[dict]:
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("floodroad_lat"), station.get("floodroad_long")
        depth = rec.get("floodroad_value")
        if lat is None or lon is None or depth is None:
            continue
        observed_at = to_utc_iso(rec.get("floodroad_datetime"), "%Y-%m-%d %H:%M")
        out.append({
            "name": (station.get("floodroad_name") or {}).get("th"),
            "depth_cm": depth, "lat": float(lat), "lon": float(lon),
            "observed_at": observed_at, "code": station.get("floodroad_oldcode"),
        })
    return out


def load_flood_roads(generated_at_utc_iso: str, centre_lat: float, centre_lon: float) -> tuple[list[dict], Path | None]:
    path = newest_file_any(RAW / "live" / "thaiwater_flood_road")
    if path is None:
        path = SAMMAKORN / "flood_road.json"
        if not path.exists():
            return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], path
    recs = parse_flood_road_records(data)
    out = []
    for r in recs:
        dist = lwl.haversine_km(centre_lat, centre_lon, r["lat"], r["lon"])
        if dist > FLOOD_ROAD_RADIUS_KM:
            continue
        out.append({"name": r["name"], "depth_cm": r["depth_cm"],
                     "dist_km": round(dist, 2), "observed_at": r["observed_at"]})
    out.sort(key=lambda r: -(r["depth_cm"] or 0))
    return out, path


# --- 6. Upstream watch-list (REPORT.md's 12-row table, shared chain, per-centre dist) -----

_UPSTREAM_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*([A-Za-z0-9.]+)\s*\|\s*([\d.\-]+)\s*,\s*([\d.\-]+)\s*\|"
)


def parse_upstream_watchlist(report_md_path: Path) -> list[dict]:
    if not report_md_path.exists():
        return []
    rows = []
    for line in report_md_path.read_text(encoding="utf-8").splitlines():
        m = _UPSTREAM_ROW_RE.match(line.strip())
        if not m:
            continue
        idx, name, code, lat, lon = m.groups()
        rows.append({"code": code, "name": name, "lat": float(lat), "lon": float(lon)})
    return rows


def _short_upstream_name(name: str) -> str:
    n = name
    for pre in UPSTREAM_STRIP_PREFIXES:
        if n.startswith(pre):
            n = n[len(pre):]
    return n.strip("- ").strip()


def _attach_prev_reading(entry: dict, obs_conn, source_id: str, station_code,
                          cur_key: str, prev_key: str) -> None:
    """Mutate `entry` in place: add `prev_key` (prev_value_m/prev_level_m),
    `prev_observed_at`, and `delta_m` from the retained-history lookup (review
    MUST-FIX #1). Always sets all three keys, explicitly to None when no qualifying
    prior reading exists -- build_page.py's fallback rendering relies on the keys
    being present (never simply absent) so it can tell "checked, none found" apart
    from "field never wired up"."""
    prev = previous_reading(obs_conn, source_id, station_code, entry.get(cur_key),
                             entry.get("observed_at"))
    if prev is None:
        entry[prev_key] = None
        entry["prev_observed_at"] = None
        entry["delta_m"] = None
    else:
        entry[prev_key] = prev["value"]
        entry["prev_observed_at"] = prev["observed_at"]
        entry["delta_m"] = prev["delta"]


def build_upstream_stations(canal_by_code: dict, generated_at_utc_iso: str,
                             centre_lat: float, centre_lon: float,
                             obs_conn=None) -> list[dict]:
    watch = parse_upstream_watchlist(UPSTREAM_REPORT_PATH)
    dry_season_rows = load_canal_normal_levels()
    out = []
    for w in watch:
        s = canal_by_code.get(w["code"])
        entry = {
            "code": w["code"],
            "name": s.get("name_th") if s else w["name"],
            "short_name": _short_upstream_name((s.get("name_th") if s else w["name"]) or ""),
            "dist_km": round(lwl.haversine_km(centre_lat, centre_lon, w["lat"], w["lon"]), 2),
            "role": "upstream",
        }
        if s is None:
            entry.update({"value_m": None, "out_m": None, "warning": None, "critical": None,
                          "bank": None, "status": "NO_THRESHOLD", "observed_at": None,
                          "stale": True,
                          "note": "ไม่มีค่านี้ในข้อมูลชุดนี้"})
        else:
            normal = resolve_normal_level(obs_conn, w["code"], dry_season_rows)
            normal_level_for_status = (
                normal["value"] if normal["value"] is not None else lwl.NO_NORMAL_LEVEL)
            status = lwl.classify_level(
                s["level_m"], s.get("warning_level"), s.get("critical_level"), s.get("bank"),
                normal_level=normal_level_for_status,
            )
            # Fix MEDIUM-4 (2026-09-26): store the safe-float'd threshold values
            # (None on anything non-numeric), never the raw agency field.
            entry.update({"value_m": lwl.safe_float(s["level_m"]), "out_m": s.get("canal_out"),
                          "warning": lwl.safe_float(s.get("warning_level")),
                          "critical": lwl.safe_float(s.get("critical_level")),
                          "bank": lwl.safe_float(s.get("bank")), "status": status,
                          "normal_level_m": normal["value"], "normal_level_basis": normal["basis"],
                          "observed_at": s.get("observed_at"),
                          "stale": is_stale(s.get("observed_at"), generated_at_utc_iso)})
        _attach_prev_reading(entry, obs_conn, _CANAL_SOURCE_ID, w["code"],
                             "value_m", "prev_value_m")
        out.append(entry)
    return out


# --- 7. Near-centre canal stations (north/south by latitude) -----------------------------

def build_near_stations(canal_stations: list[dict], exclude_codes: set,
                         generated_at_utc_iso: str, centre_lat: float, centre_lon: float,
                         radius_km: float = NEAR_STATION_RADIUS_KM,
                         obs_conn=None) -> list[dict]:
    dry_season_rows = load_canal_normal_levels()
    out = []
    for s in canal_stations:
        code = s.get("canal_oldcode")
        if not code or code in exclude_codes:
            continue
        dist = lwl.haversine_km(centre_lat, centre_lon, s["lat"], s["lon"])
        if dist > radius_km:
            continue
        normal = resolve_normal_level(obs_conn, code, dry_season_rows)
        normal_level_for_status = (
            normal["value"] if normal["value"] is not None else lwl.NO_NORMAL_LEVEL)
        status = lwl.classify_level(
            s["level_m"], s.get("warning_level"), s.get("critical_level"), s.get("bank"),
            normal_level=normal_level_for_status,
        )
        # Fix MEDIUM-4 (2026-09-26): safe-float the stored thresholds too.
        entry = {
            "code": code, "name": s.get("name_th"), "dist_km": round(dist, 2),
            # `lat`/`lon` (2026-09-28, coord->action feature):
            # the station's own coordinate, carried through unchanged from the canal
            # snapshot -- needed client-side so the coord lookup can pick the nearest
            # REAL node to a resident's own point, not just distance from the area
            # centre. Not a new measurement, just exposing a field this function
            # already reads bracket-style above (dist/role) -- same access pattern.
            "lat": s["lat"], "lon": s["lon"],
            "value_m": lwl.safe_float(s["level_m"]), "out_m": s.get("canal_out"),
            "warning": lwl.safe_float(s.get("warning_level")),
            "critical": lwl.safe_float(s.get("critical_level")),
            "bank": lwl.safe_float(s.get("bank")), "status": status,
            "normal_level_m": normal["value"], "normal_level_basis": normal["basis"],
            "observed_at": s.get("observed_at"),
            "stale": is_stale(s.get("observed_at"), generated_at_utc_iso),
            "role": "north" if s["lat"] >= centre_lat else "south",
        }
        _attach_prev_reading(entry, obs_conn, _CANAL_SOURCE_ID, code,
                             "value_m", "prev_value_m")
        out.append(entry)
    out.sort(key=lambda r: r["dist_km"])
    return out


# --- 8. Pumps ------------------------------------------------------------------------------

def build_pumps(pump_rows: list[dict], generated_at_utc_iso: str,
                 centre_lat: float, centre_lon: float,
                 radius_km: float = PUMP_RADIUS_KM,
                 obs_conn=None) -> list[dict]:
    out = []
    for r in pump_rows:
        dist_m = None
        if r.get("lat") is not None and r.get("lon") is not None:
            dist_m = round(
                lwl.haversine_km(centre_lat, centre_lon, r["lat"], r["lon"]) * 1000.0, 0
            )
        if dist_m is not None and dist_m > radius_km * 1000.0:
            continue
        entry = {
            "code": r["station_code"], "name": r.get("name_th"), "dist_m": dist_m,
            # `lat`/`lon` (2026-09-28, coord->action feature) --
            # same reasoning as build_near_stations()'s own lat/lon addition above:
            # expose the field already present on `r` so the client-side coord lookup
            # can find the nearest real pump station, not just distance from the area
            # centre. `None` when the source row itself never carried a coordinate
            # (never a guess).
            "lat": r.get("lat"), "lon": r.get("lon"),
            "level_m": r.get("level_m"), "pumps_on": r.get("pumps_on"),
            "pumps_total": r.get("pumps_total"), "gate": r.get("gate_open"),
            "status_th": r.get("status_th"), "observed_at": r.get("observed_at"),
            "stale": is_stale(r.get("observed_at"), generated_at_utc_iso),
            "pond_name": POND_NAME_BY_PUMP_CODE.get(r["station_code"]),
        }
        _attach_prev_reading(entry, obs_conn, _PUMP_SOURCE_ID, r["station_code"],
                             "level_m", "prev_level_m")
        out.append(entry)
    out.sort(key=lambda r: (r["dist_m"] if r["dist_m"] is not None else 1e9))
    return out


# --- 9. Community tiers (Sammakorn soi_tiers yaml, else low_areas csv) --------------------

def _first_time_bucket(first_time: str | None, depth_cm) -> str:
    try:
        depth_val = float(depth_cm) if depth_cm not in (None, "") else None
    except (TypeError, ValueError):
        depth_val = None
    if depth_val is not None and depth_val >= 20:
        return "T1"
    if not first_time:
        return "T5"
    m = re.search(r"(\d{1,2}):(\d{2})", str(first_time))
    if not m:
        return "T5"
    hh, mm = int(m.group(1)), int(m.group(2))
    minutes = hh * 60 + mm
    if minutes <= 6 * 60:
        return "T1"
    if minutes <= 8 * 60:
        return "T2"
    if minutes <= 10 * 60:
        return "T3"
    return "T4"


def build_tiers_sammakorn() -> tuple[list[dict], str]:
    yaml_path = newest_file(RAW / "community", "soi_tiers_*.yaml")
    doc = None
    if yaml_path is not None and HAVE_YAML:
        try:
            doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            doc = None
    if isinstance(doc, dict):
        buckets = {t: [] for t in TIER_ORDER}
        for soi in doc.get("sois", []):
            tier = soi.get("tier")
            if tier not in buckets:
                continue
            report = soi.get("report_2026_09_26") or {}
            buckets[tier].append({"soi": strip_house_range(soi.get("soi")), "first_time": report.get("first_time"),
                                   "state": report.get("state"), "depth_cm": report.get("depth_cm")})
        tiers = [{"tier": t, "label_th": TIER_LABELS_FALLBACK[t], "sois": buckets[t]}
                 for t in TIER_ORDER if buckets[t]]
        return tiers, "รวบรวมจากรายงานชาวบ้านวันที่ 26 ก.ย. 2569"

    csv_path = newest_file(RAW / "community", "low_areas_*.csv")
    if csv_path is None:
        return [], "ยังไม่มีข้อมูลรายงานชาวบ้านแยกรายซอยในชุดข้อมูลนี้"
    buckets = {t: [] for t in TIER_ORDER}
    try:
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tier = _first_time_bucket(row.get("report_time"), row.get("depth_cm"))
                buckets[tier].append({"soi": strip_house_range(row.get("soi")), "first_time": row.get("report_time") or None,
                                       "state": row.get("report_state") or None,
                                       "depth_cm": (float(row["depth_cm"]) if row.get("depth_cm") not in (None, "") else None)})
    except (OSError, csv.Error, UnicodeDecodeError):
        return [], "อ่านไฟล์รายงานชาวบ้านแยกรายซอยไม่สำเร็จ"
    tiers = [{"tier": t, "label_th": TIER_LABELS_FALLBACK[t], "sois": buckets[t]}
              for t in TIER_ORDER if buckets[t]]
    return tiers, "รวบรวมจากรายงานชาวบ้านวันที่ 26 ก.ย. 2569"


def build_community_from_tiers(tiers: list[dict]) -> list[dict]:
    out = []
    for t in tiers:
        for s in t.get("sois") or []:
            if not s.get("first_time"):
                continue
            out.append({"time": s.get("first_time"), "place": s.get("soi"),
                        "state": s.get("state") if s.get("state") and s.get("state") != "none" else "-"})
    out.sort(key=lambda r: r.get("time") or "")
    return out


# --- 9b. Ram53 "เสียงจากอินเทอร์เน็ต" social timeline (time/place/state only) -------------

_RAM53_ROW_RE = re.compile(
    r"^\|\s*(?P<time>[^|]+?)\s*\|\s*(?P<platform>[^|]*?)\s*\|\s*(?P<place>[^|]*?)\s*\|\s*(?P<state>[^|]+?)\s*\|\s*$"
)

# Thai abbreviated months, used both to pull YYYY-MM-DD out of a raw "25 ก.ย. ~16:00 ..."
# cell (row-level date, needed so newest-first sort can span >1 calendar day) and, in
# build_page.py, to render that date back next to the time for a report not from today.
THAI_MONTHS_ABBR = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
                     "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
_DATE_PREFIX_RE = re.compile(
    r"(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)"
)


def _snapshot_date_iso(path: Path) -> str | None:
    """Pull YYYY-MM-DD out of a *_YYYY-MM-DD.md/csv/yaml filename (the source
    snapshot's own date), used as the fallback `date` for reports that carry
    no per-row date of their own."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.name) if path else None
    return m.group(1) if m else None


def _date_from_th_prefix(text: str, year_ce: int) -> str | None:
    """'25 ก.ย. ~16:00 ...' / '26 ก.ย. 00:45' -> '2026-09-25'; None if the cell
    carries no explicit date (most rows -- they inherit the previous row's)."""
    m = _DATE_PREFIX_RE.search(text or "")
    if not m:
        return None
    day = int(m.group(1))
    month = THAI_MONTHS_ABBR.index(m.group(2)) + 1
    return f"{year_ce:04d}-{month:02d}-{day:02d}"


def build_ram53_community(social_md_path: Path) -> list[dict]:
    if not social_md_path.exists():
        return []
    out = []
    current_date = _snapshot_date_iso(social_md_path)
    for line in social_md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        m = _RAM53_ROW_RE.match(line)
        if not m:
            continue
        time_th, place, state = m.group("time"), m.group("place"), m.group("state")
        if time_th in ("เวลาโพสต์ (≈)",) or set(time_th) <= {"-"}:
            continue  # header / separator row
        if not place or not state:
            continue
        # Rows are listed chronologically; a row without its own date prefix
        # (the common case) belongs to whichever date the previous dated row set.
        row_date = _date_from_th_prefix(time_th, 2026)
        if row_date:
            current_date = row_date
        out.append({"time": time_th, "place": strip_house_range(place), "state": state,
                    "date": current_date})
    return out


# --- คลองจั่น/บางกะปิ "เสียงจากอินเทอร์เน็ต" -- คลองจั่นอยู่ในโซ่คลองของราม 53 --------------
#
# Added 2026-09-26 (founder request): แฟลตเคหะคลองจั่น is on the same canal chain as ram53
# (แสนแสบ -> คลองจั่น), so its social-media reports are ram53-relevant community signal, and
# a nearby-area sub-line for sammakorn too. A named media outlet (สวพ.FM91, PPTV HD 36, The
# Bangkok Insight) is named as an agency; a personal Facebook post/page/clip is never named.

_KHLONGCHAN_ROW_RE = _RAM53_ROW_RE  # identical 4-column table shape


def _khlongchan_source_label(raw_source: str) -> str | None:
    s = (raw_source or "").strip()
    if not s:
        return None
    if re.search(r"บุคคล|เพจ|คลิป", s):
        return None
    s = re.sub(r"\s*/\s*ข่าว\s*$", "", s).strip()
    return s or None


def build_khlongchan_community(social_md_path: Path) -> list[dict]:
    if not social_md_path.exists():
        return []
    out = []
    current_date = _snapshot_date_iso(social_md_path)
    for line in social_md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        m = _KHLONGCHAN_ROW_RE.match(line)
        if not m:
            continue
        time_th, source_raw, place, state = (m.group("time"), m.group("platform"),
                                              m.group("place"), m.group("state"))
        if time_th in ("เวลาโพสต์ (≈)",) or set(time_th) <= {"-"}:
            continue  # header / separator row
        if not place or not state:
            continue
        row_date = _date_from_th_prefix(time_th, 2026)
        if row_date:
            current_date = row_date
        source = _khlongchan_source_label(source_raw)
        state_out = f"{state} ({source})" if source else state
        out.append({"time": time_th, "place": strip_house_range(place), "state": state_out,
                    "date": current_date})
    return out


# --- 10. Exits ------------------------------------------------------------------------------

def build_exits_sammakorn(community_md_path: Path) -> list[dict]:
    text = community_md_path.read_text(encoding="utf-8") if community_md_path.exists() else ""
    date_m = re.search(r"—\s*([^(\n]+?)\s*\(รวบรวม\s*([0-9:]+)\)", text)
    report_date_th = date_m.group(1).strip() if date_m else None
    report_time_th = date_m.group(2).strip() if date_m else None
    section_m = re.search(r"##\s*C\.[^\n]*\n(.+)", text)
    section_c = section_m.group(1).strip() if section_m else ""
    clauses = [c.strip().lstrip("-").strip() for c in section_c.split("·") if c.strip()]

    def find_clause(needle: str) -> str | None:
        for clause in clauses:
            if needle in clause:
                return clause
        return None

    def exit_entry(name: str, clause: str | None) -> dict:
        if clause:
            return {"name": name, "status_from_reports": clause, "is_community_report": True,
                    "report_date_th": report_date_th, "report_time_th": report_time_th}
        return {"name": name, "status_from_reports": "ยังไม่มีใครรายงานเส้นทางนี้",
                "is_community_report": False, "report_date_th": None, "report_time_th": None}

    return [exit_entry("ราม 110", find_clause("110")), exit_entry("ราม 112", find_clause("112")),
            exit_entry("ราม 118", find_clause("118")), exit_entry("ทางไป รร.นวมินทร์", find_clause("นวมินทร์"))]


# --- 10a. Sammakorn community update, 27 ก.ย. 2569 (6 FB posts, founder-pasted) -----------
#
# Additive over the 26 ก.ย. community_reports file (never edited/replaced -- append-only
# per AGENTS.md). Parses two plain pipe tables out of
# site/inputs/community/community_reports_2026-09-27.md: a community timeline (time/place/
# state, same 3-field shape as build_community_from_tiers()) and an exit-routes table
# (name/status, same shape as build_exits_sammakorn()'s entries). No poster names, no
# personal phone/LINE numbers in that file -- see its own header note.

def _parse_pipe_table(section_text: str, ncols: int) -> list[list[str]]:
    rows = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != ncols:
            continue
        if all(set(c) <= {"-", ":", ""} for c in cells):
            continue  # markdown separator row
        if cells[0] in ("เวลา", "เส้นทาง"):
            continue  # header row
        rows.append(cells)
    return rows


def _extract_section(text: str, heading_prefix: str) -> str:
    m = re.search(rf"##\s*{re.escape(heading_prefix)}.*?\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    return m.group(1) if m else ""


def build_community_extra_20260927(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    section = _extract_section(text, "Community timeline")
    out = []
    for time_th, place, state in _parse_pipe_table(section, 3):
        if not time_th or not state:
            continue
        out.append({"time": time_th, "place": strip_house_range(place) or "หมู่บ้านสัมมากร (ทั่วไป)",
                    "state": state, "date": "2026-09-27"})
    return out


def build_exits_extra_20260927(path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    section = _extract_section(text, "Exit routes")
    out = []
    for name, status in _parse_pipe_table(section, 2):
        if not name or not status:
            continue
        out.append({"name": name, "status_from_reports": status, "is_community_report": True,
                    "report_date_th": "27 ก.ย. 2569", "report_time_th": "15:00"})
    return out


def build_exits_ram53() -> list[dict]:
    return [{
        "name": "ปากซอยด้านใต้",
        "status_from_reports": "ออก ถ.รามคำแหง (ยังไม่ยืนยันจากแผนที่)",
        "is_community_report": False, "report_date_th": None, "report_time_th": None,
    }]


# --- 10b. Hospitals (Overpass cache, ≤5km else []) -----------------------------------------

HEALTH_OVERPASS_PATH = SAMMAKORN / "health_overpass.json"
VET_NAME_MARKERS = ("animalclinic", "สัตว์")


def build_hospitals(centre_lat: float, centre_lon: float, radius_km: float = HOSPITAL_RADIUS_KM) -> list[dict]:
    if not HEALTH_OVERPASS_PATH.exists():
        return []
    try:
        raw = json.loads(HEALTH_OVERPASS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for el in raw.get("elements", []):
        tags = el.get("tags", {}) or {}
        if tags.get("amenity") != "hospital":
            continue
        name = tags.get("name:th") or tags.get("name")
        if not name:
            continue
        name_en = tags.get("name:en") or tags.get("name")
        if any(marker.lower() in (name or "").lower() or marker in (name_en or "")
               for marker in VET_NAME_MARKERS):
            continue
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        dist = lwl.haversine_km(centre_lat, centre_lon, lat, lon)
        if dist > radius_km:
            continue
        out.append({"name": name, "name_en": tags.get("name:en"), "phone": tags.get("phone"),
                    "dist_km": round(dist, 1)})
    out.sort(key=lambda h: h["dist_km"])
    return out


# --- 11. DDS daily-bulletin quotes (shared parser, area-relevant name filter) --------------

_DDS_DATE_RE = re.compile(r"ประจำวัน\S*ที่\s*([\d]{1,2}\s+\S+\s+[\d]{4})")
_DDS_ISSUE_RE = re.compile(r"ฉบับที่\s*([0-9/]+)")
_DDS_RAIN_ROW_RE = re.compile(r"^\s*\d+\s+จุดวัด\s+(.+?)\s{2,}([\d.]+)\s*$")
_DDS_CANAL_ROW_RE = re.compile(
    r"^\s*\d+\.\s*(.+?)\s{2,}([+\-][\d.]+)\s+([+\-][\d.]+)\s+([+\-][\d.]+)\s+(ระดับน้ำ\S*)\s*$"
)
_DDS_NAME_FIXUPS = {"เขตบางกะป": "เขตบางกะปิ"}
_DDS_STATUS_TH = {"ระดับน้ำวิกฤติ": "เกินระดับวิกฤต", "ระดับน้ำปกติ": "ปกติ"}


def _dds_fix_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    for bad, good in _DDS_NAME_FIXUPS.items():
        if name.endswith(bad):
            name = name[: -len(bad)] + good
    name = re.sub(r"(?<=[ก-๙])\.\d+$", "", name)
    return name


def build_dds_quotes(relevant_names: list[str]) -> tuple[list[dict], dict | None, Path | None]:
    # collect.py writes the live PDF to raw/live/dds_daily_pdf/<timestamp>.pdf;
    # raw/dds_reports/ is a manual/legacy drop location kept only as a fallback
    # (fixed 2026-09-26: the two paths had silently diverged).
    pdf_path = newest_file(RAW / "live" / "dds_daily_pdf", "*.pdf")
    if pdf_path is None:
        pdf_path = newest_file(RAW / "dds_reports", "dds_daily_*.pdf")
    if pdf_path is None:
        return [], None, None
    try:
        proc = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                               capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return [], None, pdf_path
    if proc.returncode != 0:
        return [], None, pdf_path
    text = proc.stdout.decode("utf-8", errors="replace")
    text = "".join(ch for ch in text if not (0xE000 <= ord(ch) <= 0xF8FF))
    header = re.sub(r"\s+", " ", " ".join(text.splitlines()[:3])).strip()
    date_m = _DDS_DATE_RE.search(header)
    issue_m = _DDS_ISSUE_RE.search(header)
    report_meta = ({"report_date_th": date_m.group(1) if date_m else None,
                    "issue_no": issue_m.group(1) if issue_m else None}
                   if (date_m or issue_m) else None)
    report_date_th = report_meta["report_date_th"] if report_meta else None

    quotes: list[dict] = []
    seen = set()
    for line in text.splitlines():
        if not any(k in line for k in relevant_names):
            continue
        m = _DDS_RAIN_ROW_RE.match(line)
        if m:
            name = _dds_fix_name(m.group(1))
            mm = m.group(2)
            text_out = f"ฝนสูงสุดใน 24 ชม. ที่ผ่านมา: {name} วัดได้ {mm} มม."
            if report_date_th:
                text_out += f" (รายงานวันที่ {report_date_th})"
            if text_out not in seen:
                seen.add(text_out)
                quotes.append({"text": text_out})
            continue
        m = _DDS_CANAL_ROW_RE.match(line)
        if m:
            name = _dds_fix_name(m.group(1))
            critical, _yesterday_max, today_0700, status_raw = m.group(2), m.group(3), m.group(4), m.group(5)
            status_th = _DDS_STATUS_TH.get(status_raw, status_raw)
            text_out = (f"{name} เวลา 07:00 น. วันนี้ ระดับน้ำ {today_0700} ม.รทก. "
                        f"(เกณฑ์วิกฤต {critical} ม.รทก.) — สถานะ: {status_th}")
            if report_date_th:
                text_out += f" (รายงานวันที่ {report_date_th})"
            if text_out not in seen:
                seen.add(text_out)
                quotes.append({"text": text_out})
    return quotes, report_meta, pdf_path


# --- 12. Hourly rain forecast -- Open-Meteo (third-party, open, no key) ------------------
#
# Replaced 2026-09-26: the previous version did one Playwright navigation to Google's
# hourly-precipitation strip. Replaced with collect.py's `collect_openmeteo_forecast` (a
# plain JSON GET, no key), which writes `raw/live/openmeteo_forecast/<ts>_<area_id>.json`
# per area. This function only READS that cached snapshot -- no network call here, same
# discipline as every other `load_*` function in this file. Fails soft to "unavailable"
# if the collector hasn't run yet or the snapshot can't be parsed.

_FORECAST_UNAVAILABLE = {
    "available": False,
    "status": "ยังไม่มีพยากรณ์ฝนรายชั่วโมง — ดูเรดาร์ กทม.",
    "items": [],
    "hourly": [],
    "source": None,
    "trust_tier": None,
    "direction": "unavailable",
    "trend_word": None,
    "next6h_mm": None, "next24h_mm": None, "h24_48_mm": None, "h48_72_mm": None,
    "first_dry_6h_start": None,
}

DRY_HOUR_MM_THRESHOLD = 0.1  # mm/h at or below this counts as "dry" for first_dry_6h_start
TREND_STEP_MM = 0.5          # minimum mm difference between 3h windows to call a trend


def _fmt_hhmm(time_local: str | None) -> str | None:
    if not time_local:
        return None
    return time_local[-5:] if len(time_local) >= 5 else time_local


def _trend_word(rows: list[dict]) -> tuple[str, str | None]:
    """Compares the next-3h rain sum against the following-3h sum (task spec).
    Returns (direction, thai_word) where direction in {rising, falling, steady}."""
    first3 = sum(r["mm"] for r in rows[0:3])
    next3 = sum(r["mm"] for r in rows[3:6])
    if next3 > first3 + TREND_STEP_MM:
        return "rising", "ฝนกำลังจะตกเพิ่มขึ้น"
    if first3 > next3 + TREND_STEP_MM:
        after = _fmt_hhmm(rows[3]["time_local"]) if len(rows) > 3 else None
        word = f"ฝนกำลังจะเบาลงหลัง {after} น." if after else "ฝนกำลังจะเบาลง"
        return "falling", word
    return "steady", "ฝนยังตกต่อ"


def _first_dry_6h_start(rows: list[dict]) -> str | None:
    for i in range(0, max(0, len(rows) - 5)):
        window = rows[i:i + 6]
        if len(window) == 6 and all(r["mm"] <= DRY_HOUR_MM_THRESHOLD for r in window):
            return _fmt_hhmm(window[0]["time_local"])
    return None


def build_forecast_short(rows: list[dict], fetched_at_iso: str | None) -> dict:
    """Pure function: hourly Open-Meteo rows (ascending, already filtered to "now
    onward") -> the `forecast`/`forecast_short` dict this pipeline renders. Split out
    from `load_openmeteo_forecast` so it's unit-testable on a fixture with no file I/O."""
    if not rows:
        return dict(_FORECAST_UNAVAILABLE)
    direction, trend_word = _trend_word(rows)
    hourly = [{"h": _fmt_hhmm(r["time_local"]), "mm": round(r["mm"], 1), "prob": r.get("prob")}
              for r in rows[:12]]
    items = [{"h": h["h"], "mm": h["mm"]} for h in hourly[:6]]

    def _sum(a, b):
        vals = [r["mm"] for r in rows[a:b]]
        return round(sum(vals), 1) if vals else None

    return {
        "available": True,
        "status": None,
        "items": items,
        "hourly": hourly,
        "source": "Open-Meteo (แบบจำลองเปิด ECMWF/GFS)",
        "trust_tier": "third_party_forecast",
        "direction": direction,
        "trend_word": trend_word,
        "next6h_mm": _sum(0, 6),
        "next24h_mm": _sum(0, 24),
        "h24_48_mm": _sum(24, 48),
        "h48_72_mm": _sum(48, 72),
        "first_dry_6h_start": _first_dry_6h_start(rows),
        "fetched_at": fetched_at_iso,
        # Full hourly series (up to Open-Meteo's forecast horizon) for the
        # drain-timeline chart's rain-input term -- `hourly` above only keeps 12 rows
        # for the short forecast strip; this keeps everything parse_openmeteo_forecast gave us.
        "hourly_full": [{"time_local": r["time_local"], "mm": round(r["mm"], 2)} for r in rows],
    }


def load_openmeteo_forecast(area_id: str, now_local: datetime.datetime) -> tuple[dict, Path | None]:
    path = newest_file(RAW / "live" / "openmeteo_forecast", f"*_{area_id}.json")
    if path is None:
        return dict(_FORECAST_UNAVAILABLE), None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_FORECAST_UNAVAILABLE), path
    if parsers is None:
        return dict(_FORECAST_UNAVAILABLE), path
    try:
        all_rows = parsers.parse_openmeteo_forecast(data)
    except Exception:  # pragma: no cover - defensive, matches this file's fail-soft rule
        return dict(_FORECAST_UNAVAILABLE), path
    now_floor = now_local.replace(minute=0, second=0, microsecond=0)
    future_rows = []
    for r in all_rows:
        try:
            local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M").replace(tzinfo=BANGKOK_TZ)
        except ValueError:
            continue
        if local_dt >= now_floor:
            future_rows.append(r)
    forecast = build_forecast_short(future_rows, fetched_at_of(path))
    return forecast, path


def build_capacity_comparison(rain: dict | None, forecast: dict | None) -> dict:
    """Arithmetic on declared inputs only (sum + ratio) -- never a model, per this
    workspace's equation discipline. `today_mm` is the already-observed rain_24h at the
    nearest gauge; `plus_forecast_mm` adds Open-Meteo's next24h_mm on top -- both compared
    against the DDS-verified design capacity of 80 mm/day."""
    today_mm = (rain or {}).get("mm_24h")
    fc_24h = (forecast or {}).get("next24h_mm") if (forecast or {}).get("available") else None
    out = {
        "mm_per_hour": DESIGN_CAPACITY_MM_PER_HOUR,
        "mm_per_day": DESIGN_CAPACITY_MM_PER_DAY,
        "source_th": DESIGN_CAPACITY_SOURCE_TH,
        "source_tag": DESIGN_CAPACITY_SOURCE_TAG,
        "today_mm": today_mm,
        "today_ratio": round(today_mm / DESIGN_CAPACITY_MM_PER_DAY, 1) if today_mm is not None else None,
        "forecast_24h_mm": fc_24h,
        "total_with_forecast_mm": None,
        "total_with_forecast_ratio": None,
    }
    if today_mm is not None or fc_24h is not None:
        total = (today_mm or 0) + (fc_24h or 0)
        out["total_with_forecast_mm"] = round(total, 1)
        out["total_with_forecast_ratio"] = round(total / DESIGN_CAPACITY_MM_PER_DAY, 1)
    return out


DRAIN_TIMELINE_HORIZON_HOURS = 96
DRAIN_TIMELINE_SCENARIOS = [("c0", 0.0, "ฝนหยุด (c=0)"), ("c50", 0.5, "สมมติ (c=0.5)"),
                            ("c100", 1.0, "ขอบบน (c=1)")]

FORECAST_MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "jma_seamless",
                    "gem_seamless", "meteofrance_seamless"]
FORECAST_DIR = RAW / "forecast"
FORECAST_7DAY_COMPARE_PATH = FORECAST_DIR / "forecast_7day_compare.json"


def load_forecast_7day_compare() -> dict | None:
    """Load raw/forecast/forecast_7day_compare.json AS-IS -- it already has per-day
    per-model mm plus precomputed min/median/max/n (see FORECAST_SPEC.md item 2: "Do not
    recompute"). Returns None on any read failure -- reference/display data only."""
    try:
        return json.loads(FORECAST_7DAY_COMPARE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_multimodel_hourly() -> list[dict]:
    """Merge the 6 raw/forecast/openmeteo_<model>.json hourly precipitation series by
    time index (FORECAST_SPEC.md item 1) -> one row per hour:
    {time_local, median_mm, min_mm, max_mm, jma_mm, n}. A model missing an hour (shorter
    run) is skipped for that hour's median/min/max, never treated as 0mm."""
    per_model = {}
    for model in FORECAST_MODELS:
        path = FORECAST_DIR / f"openmeteo_{model}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if parsers is None:
            continue
        try:
            per_model[model] = parsers.parse_openmeteo_forecast(data)
        except Exception:  # pragma: no cover - defensive
            continue
    if not per_model:
        return []

    by_time: dict[str, dict] = {}
    order: list[str] = []
    for model, rows in per_model.items():
        for r in rows:
            t = r["time_local"]
            if t not in by_time:
                by_time[t] = {}
                order.append(t)
            by_time[t][model] = r["mm"]

    out = []
    for t in order:
        vals = list(by_time[t].values())
        if not vals:
            continue
        out.append({
            "time_local": t,
            "median_mm": round(sorted(vals)[len(vals) // 2] if len(vals) % 2 else
                                (sorted(vals)[len(vals) // 2 - 1] + sorted(vals)[len(vals) // 2]) / 2, 2),
            "min_mm": round(min(vals), 2),
            "max_mm": round(max(vals), 2),
            "jma_mm": round(by_time[t]["jma_seamless"], 2) if "jma_seamless" in by_time[t] else None,
            "n": len(vals),
        })
    return out


_MULTIMODEL_NAMES_TH = ["ECMWF", "GFS", "ICON", "JMA", "GEM", "Météo-France"]


def _rain_source_note_th(n_models_actual: int) -> str:
    """MUST-FIX #1 (independent review, 2026-09-27): the note used to hardcode "6
    แบบจำลองเปิด" no matter how many of collect.py's `openmeteo_multimodel` model files
    this run actually produced. Now built from the count actually seen this run
    (`n_models_actual`, from `build_drain_timeline`'s own `load_multimodel_hourly()`
    read) -- 0 means the fallback single-station path was used instead (see caller)."""
    if n_models_actual <= 0:
        return ("ฝนจากสถานีสัมมากรสถานีเดียว (Open-Meteo forecast) -- ไฟล์แบบจำลองเปิด "
                "หลายตัว (raw/forecast/openmeteo_<model>.json) ยังไม่พร้อมใช้งานรอบนี้")
    if n_models_actual == 1:
        return ("ฝนจากแบบจำลองเดียว (best_match) ที่จุดสัมมากร ใช้เป็นตัวแทนของทั้งเมือง "
                "(proxy) -- แบบจำลองเปิดตัวอื่นไม่พร้อมใช้งานรอบนี้")
    names = ", ".join(_MULTIMODEL_NAMES_TH[:n_models_actual])
    return (f"ฝนมัธยฐาน (median) จาก {n_models_actual} แบบจำลองเปิด ({names}) "
            "ที่จุดสัมมากร ใช้เป็นตัวแทนของทั้งเมือง (proxy)")


def build_drain_timeline(rain: dict | None, forecast: dict | None,
                          generated_at_utc_iso: str) -> dict | None:
    """Hourly drain-timeline for the "สมดุลน้ำ" chart -- V0/Q from the BMA's own 26 ก.ย.
    13:00 briefing (declared, official_report), A from the Bangkok administrative-area
    fallback (RELAYED, same as build_bangkok_east_upper_bound), hourly rain from the
    sammakorn Open-Meteo forecast used as a PROXY for the whole city (labelled as such).
    Three scenarios sweep the undeclared runoff fraction c in {0, 0.5, 1} (per maintainer
    instruction) -- this is still plain arithmetic on declared/labelled inputs, never a
    hydraulic model. Returns None if the briefing or forecast is unavailable."""
    briefing = load_briefing()
    if not briefing:
        return None
    facts = briefing.get("declared_facts") or {}
    v0 = (facts.get("backlog_volume_phra_nakhon_side") or {}).get("value")
    q = (facts.get("total_bma_pumping_capacity") or {}).get("value")
    if v0 is None or not q:
        return None

    cfg = load_balance_yaml("bangkok_east")
    a_km2 = _cfg_value(cfg, "A") or 1568.737
    a_m2 = a_km2 * 1_000_000.0
    q_per_hour = q * 3600.0

    # 2026-09-26 forecast upgrade: use the 6-model median (FORECAST_SPEC.md) instead of
    # a single Open-Meteo run for the chart's rain input -- covers the full 96h horizon
    # (7-day fetch, ~168h) so the grey "no forecast" fallback below rarely triggers now.
    multimodel = load_multimodel_hourly()
    n = DRAIN_TIMELINE_HORIZON_HOURS
    if multimodel:
        rain_mm = [row["median_mm"] for row in multimodel[:n]]
        rain_min = [row["min_mm"] for row in multimodel[:n]]
        rain_max = [row["max_mm"] for row in multimodel[:n]]
        rain_jma = [row["jma_mm"] if row["jma_mm"] is not None else row["median_mm"]
                    for row in multimodel[:n]]
        forecast_coverage_hours = len(multimodel[:n])
        # MUST-FIX #1 (independent review, 2026-09-27): this used to hardcode "6 แบบจำลอง
        # เปิด" unconditionally, but `n` here (the per-hour member count `load_
        # multimodel_hourly` returns) tracks how many of the 6 raw/forecast/openmeteo_
        # <model>.json files this run's collector actually produced -- a partial/failed
        # run (fewer than 6 models fetched) used to still claim "6" regardless. The note
        # below is now built from the max member count actually seen across every hour,
        # never a hardcoded "6".
        n_models_actual = max((row["n"] for row in multimodel), default=0)
    else:
        # fall back to the single-station area forecast (pre-upgrade behaviour) if the
        # 6-model files are unavailable for any reason.
        hourly = (forecast or {}).get("hourly_full") or []
        rain_mm = [h.get("mm") or 0.0 for h in hourly[:n]]
        rain_min = list(rain_mm)
        rain_max = list(rain_mm)
        rain_jma = list(rain_mm)
        forecast_coverage_hours = len(rain_mm)
        n_models_actual = 0
    # Peer-review fix 2026-09-26: hours beyond the real forecast used to be silently
    # padded with 0mm, which the chart could not distinguish from "forecast says no
    # rain". They are still filled with 0 here (arithmetic needs a number), but
    # `forecast_coverage_hours` tells build_page.py exactly where the real data ends, so
    # the chart can grey-shade the unforecast region and label it "ไม่มีพยากรณ์ —
    # สมมติฝน 0" instead of drawing it as an ordinary forecast line.
    for series in (rain_mm, rain_min, rain_max, rain_jma):
        while len(series) < n:
            series.append(0.0)

    scenarios = {}
    for key, c, label_th, rain_series in [
        ("c0", 0.0, "ฝนหยุด (c=0)", rain_mm),
        ("c50", 0.5, "สมมติ (c=0.5)", rain_mm),
        ("c100", 1.0, "ขอบบน (c=1)", rain_mm),
        ("d_jma", 0.5, "แบบจำลองที่ฝนมากที่สุด (JMA, c=0.5)", rain_jma),
    ]:
        values = []
        v = v0
        end_hour = None
        for h in range(n + 1):
            if v <= 0 and end_hour is None:
                end_hour = h
            v_display = 0.0 if end_hour is not None else v
            values.append(round(v_display, 1))
            if h < n and end_hour is None:
                inflow = (rain_series[h] / 1000.0) * a_m2 * c
                v = v - q_per_hour + inflow
        end_time_iso = None
        if end_hour is not None:
            try:
                t0 = datetime.datetime.fromisoformat(generated_at_utc_iso)
                end_time_iso = (t0 + datetime.timedelta(hours=end_hour)).isoformat()
            except ValueError:
                end_time_iso = None
        scenarios[key] = {"label_th": label_th, "c": c, "values_m3": values,
                           "end_hour": end_hour, "end_time_utc": end_time_iso}

    return {
        "generated_at_utc": generated_at_utc_iso,
        "horizon_hours": n,
        "forecast_coverage_hours": forecast_coverage_hours,
        "v0_m3": v0,
        "q_m3s": q,
        "area_km2": a_km2,
        "rain_mm_hourly": rain_mm[:n],
        "rain_min_hourly": rain_min[:n],
        "rain_max_hourly": rain_max[:n],
        "rain_source_note_th": _rain_source_note_th(n_models_actual),
        "scenarios": scenarios,
        "footnote_th": ("เลขคณิตบนค่าที่ประกาศ + พยากรณ์แบบจำลองเปิด · ไม่ใช่แบบจำลองชลศาสตร์ · "
                         "ไม่รวมน้ำจากจังหวัดรอบ · c ยังไม่ประกาศ"),
        "sammakorn_note_th": ("สัมมากรอยู่ท้ายลำดับโซน (ทับช้างล้น, ปั๊มบึงไม่เดิน, ประตูประเวศล็อก) "
                               "จึงน่าจะพ้นน้ำช้ากว่าค่าเฉลี่ยเมือง"),
        "sammakorn_note_tag": "INSTINCT",
    }


def build_sammakorn_rough_estimate(drain_timeline: dict | None) -> dict | None:
    """ROUGH, explicitly-INSTINCT illustrative village-level estimate for the chart's
    bottom panel only -- maintainer decision 2026-09-26. NEVER used by
    build_village_water_balance()/water_balance.step(), which stays on the OPEN A/c in
    sammakorn.balance.yaml's top-level fields and therefore keeps REFUSING, unchanged.
    Every input here is read from sammakorn.balance.yaml's `rough_estimate_instinct`
    block, itself tagged per-field INSTINCT/RELAYED."""
    if not drain_timeline:
        return None
    cfg = (load_balance_yaml("sammakorn") or {}).get("rough_estimate_instinct")
    if not cfg:
        return None

    area_m2 = (cfg.get("area_m2") or {}).get("value")
    c = (cfg.get("c") or {}).get("value")
    pond = (cfg.get("pond_capacity_m3") or {}).get("value")
    s0 = (cfg.get("S0_m3") or {}).get("value")
    if None in (area_m2, c, pond, s0):
        return None

    rain_mm = drain_timeline.get("rain_mm_hourly") or []
    n = drain_timeline.get("horizon_hours") or len(rain_mm)
    bkk_c0_end_hour = ((drain_timeline.get("scenarios") or {}).get("c0") or {}).get("end_hour")

    pump_cfg = cfg.get("pump_scenarios") or {}
    scenarios = {}
    for key, pcfg in pump_cfg.items():
        q0 = pcfg.get("q_m3s") or 0.0
        q_after = pcfg.get("q_m3s_after_bkk_c0_end")
        values_cm = []
        s = s0
        for h in range(n + 1):
            excess = max(s - pond, 0.0)
            depth_cm = (excess / area_m2) * 100.0
            values_cm.append(round(depth_cm, 2))
            if h < n:
                q = q0
                if q_after is not None and bkk_c0_end_hour is not None and h >= bkk_c0_end_hour:
                    q = q_after
                inflow = (rain_mm[h] / 1000.0) * area_m2 * c if h < len(rain_mm) else 0.0
                s = max(s + inflow - q * 3600.0, 0.0)
        scenarios[key] = {"label_th": pcfg.get("label_th") or key, "q_m3s": q0,
                           "values_cm": values_cm}

    # pump0 depth BAND using the low-lying sub-area range (peer-review addition
    # 2026-09-26) -- a smaller area gives a LARGER average depth, so area_low ->
    # depth_high and area_high -> depth_low.
    band = None
    area_range = cfg.get("area_m2_range_for_depth_band") or {}
    a_low, a_high = area_range.get("low"), area_range.get("high")
    pump0_cfg = pump_cfg.get("pump0") or {}
    if a_low and a_high:
        def _band_series(area_for_band):
            values = []
            s = s0
            for h in range(n + 1):
                excess = max(s - pond, 0.0)
                values.append(round((excess / area_for_band) * 100.0, 2))
                if h < n:
                    inflow = (rain_mm[h] / 1000.0) * area_for_band * c if h < len(rain_mm) else 0.0
                    s = max(s + inflow - (pump0_cfg.get("q_m3s") or 0.0) * 3600.0, 0.0)
            return values

        band = {"depth_high_cm": _band_series(a_low), "depth_low_cm": _band_series(a_high),
                "area_low_m2": a_low, "area_high_m2": a_high}

    return {
        "horizon_hours": n,
        "area_m2": area_m2, "c": c, "pond_capacity_m3": pond, "s0_m3": s0,
        "scenarios": scenarios,
        "pump0_depth_band": band,
        "caption_th": cfg.get("caption_th"),
        "decisive_factor_th": cfg.get("decisive_factor_th"),
        "area_note_th": ((cfg.get("area_m2") or {}).get("note") or ""),
        "rain_mm_hourly": rain_mm[:n],
        "forecast_coverage_hours": drain_timeline.get("forecast_coverage_hours"),
    }


# --- BMA governor briefing 2026-09-26 13:00 (official_report) --------------------------

def build_briefing_summary(briefing: dict | None) -> dict | None:
    """Pull just the fields build_page.py needs for the hero line, the forecast section's
    TMD-relay line (shown next to, never replacing, the multi-model 7-day table), and the
    help section's shelters/parking/hotline/school additions.

    As of 2026-09-27 the newest briefing (BRIEFING_PATH) is the governor's media interview
    that morning -- trust_tier official_report-via-media / tag RELAYED, distinct from the
    26 ก.ย. 13:00/16:15 official_report pair it supersedes on the hero line. Its
    declared_facts carry their own hero_line_th/timeframe/ops/evacuation/contradiction_th
    fields rather than reusing the 26 ก.ย. shape, so this function reads them directly with
    a fallback to the older shape for the 26 ก.ย. files (kept on disk, never deleted).
    Never rephrased into a command (no ห้าม/ไม่ต้อง/ไม่ควร/ผ่อนคลาย/ปั๊มเสีย)."""
    if not briefing:
        return None
    facts = briefing.get("declared_facts") or {}

    def v(key):
        return (facts.get(key) or {}).get("value")

    hero_line_th = v("hero_line_th") or (
        "กทม. แถลง 16:15: กรมอุตุฯ คาดฝนลดลงตั้งแต่ 27 ก.ย. — "
        "ถ้าไม่มีฝนเติม สถานการณ์ทยอยคลี่คลาย (น้ำค้าง 223 ล้าน ลบ.ม.)"
    )

    return {
        "briefing_time_bkk": briefing.get("briefing_time_bkk"),
        "briefing_time_approximate": briefing.get("briefing_time_approximate", False),
        "briefing_time_note_th": briefing.get("briefing_time_note_th"),
        "trust_tier": briefing.get("trust_tier"),
        "hero_line_th": hero_line_th,
        "weather_system_note_th": v("main_canals_status"),
        "tmd_forecast_note_th": v("tmd_forecast_note"),
        "canals_to_watch": v("canals_to_watch") or [],
        "roads_affected_count": v("main_roads_affected_count"),
        "households_affected_initial_survey": v("households_affected_initial_survey"),
        "health_support_ready": v("health_support_ready"),
        "disaster_response_support": v("disaster_response_support"),
        "shelters": v("shelters"),
        "bedridden_patients_moved": v("bedridden_patients_moved"),
        # 1422 (กรมควบคุมโรค สอบถามเรื่องโรค) added 2026-09-27, source:
        # docs/knowledge/card_health_2026-09-27_nrct_7_flood_diseases.md ("เลขนี้ใหม่
        # สำหรับคลังนี้ -- ไม่เคยมี 1422 มาก่อน").
        "hotlines": v("hotlines") or ["1555", "Traffy Fondue", "สำนักงานเขต (ขอกระสอบทราย)", "1669",
                                       "1422 (กรมควบคุมโรค สอบถามเรื่องโรค)"],
        "temporary_parking": v("temporary_parking") or [],
        "monday_note_th": v("monday_2026-09-28"),
        "conditional_outlook_th": v("conditional_outlook"),
        "disaster_area_declared": v("disaster_area_declared"),
        # 27 ก.ย. governor-interview fields (None on the older 26 ก.ย. briefing shape)
        "rain_total_note_th": v("rain_total_note_th"),
        "drain_explanation_th": v("drain_explanation_th"),
        "pump_power_note_th": v("pump_power_note_th"),
        "cause_of_local_pump_faults_note_th": v("cause_of_local_pump_faults_note_th"),
        "timeframe": v("timeframe") or {},
        "ops": v("ops") or {},
        "evacuation": v("evacuation") or {},
        "deaths_note_th": v("deaths_note_th"),
        "contradiction_th": v("contradiction_th"),
    }


# --- Sources ---------------------------------------------------------------------------

def build_sources(rain: dict | None, canal_path, pump_path, rain_path, flood_road_path,
                   dds_pdf_path, tide_path, community_path, community_agency: str,
                   community_id: str = "community_reports",
                   forecast: dict | None = None, forecast_path=None) -> list[dict]:
    out = [
        {"id": "thaiwater_canal_waterlevel",
         "agency_th": "สำนักการระบายน้ำ กรุงเทพมหานคร (ผ่าน HII/สสน. thaiwater.net)",
         "url": "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel",
         "fetched_at": fetched_at_of(canal_path), "trust_tier": "official_telemetry"},
        {"id": "bma_pumphistory", "agency_th": "สำนักการระบายน้ำ กรุงเทพมหานคร",
         "url": "https://weather.bangkok.go.th/Station/PumpHistory",
         "fetched_at": fetched_at_of(pump_path), "trust_tier": "official_telemetry"},
        {"id": "thaiwater_rain_24h",
         "agency_th": (rain or {}).get("agency_th") or "กรมชลประทาน/HII สสน. (thaiwater.net)",
         "url": None, "fetched_at": fetched_at_of(rain_path), "trust_tier": "official_telemetry"},
        {"id": "thaiwater_flood_road",
         "agency_th": "สำนักการระบายน้ำ กรุงเทพมหานคร (ผ่าน HII/สสน. thaiwater.net)",
         "url": "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/flood_road",
         "fetched_at": fetched_at_of(flood_road_path), "trust_tier": "official_telemetry"},
        {"id": "dds_daily_pdf", "agency_th": "สำนักการระบายน้ำ กรุงเทพมหานคร (ศูนย์ควบคุมระบบป้องกันน้ำท่วม)",
         "url": "https://dds.bangkok.go.th/public_content/files/001/0004901_1.pdf",
         "fetched_at": fetched_at_of(dds_pdf_path), "trust_tier": "official_report"},
        {"id": "hydro_navy_bangkok_tide", "agency_th": "กรมอุทกศาสตร์ กองทัพเรือ (สถานี กองบัญชาการกองทัพเรือ)",
         "url": "https://dds.bangkok.go.th/public_content/files/001/0006030_1.pdf",
         "fetched_at": fetched_at_of(tide_path), "trust_tier": "official_report"},
        {"id": community_id, "agency_th": community_agency, "url": None,
         "fetched_at": fetched_at_of(community_path), "trust_tier": "community_report"},
    ]
    if forecast and forecast.get("available"):
        out.append({
            "id": "openmeteo_forecast",
            "agency_th": "Open-Meteo (แบบจำลองเปิด ECMWF/GFS) — บุคคลที่สาม ไม่ใช่กรมอุตุนิยมวิทยา (TMD)",
            "url": None, "fetched_at": fetched_at_of(forecast_path),
            "trust_tier": "third_party_forecast",
        })
    # Sync pass (2026-09-27 evening): these two sources feed the knowledge graph / gate
    # -state readouts (docs/knowledge/BMA_WATER_MAP_PROBE.md, docs/knowledge/
    # DWR_SUBBASIN.md, sources/registry.yaml) but were missing from this page's own
    # footer credit list -- added here so the public page discloses every agency this
    # project actually reads from, not only the ones this specific page's own rain/pump/
    # canal fields are wired to.
    bma_watermap_path = newest_file_any(RAW / "live" / "bma_watermap")
    out.append({
        "id": "bma_watermap", "agency_th": "สำนักการระบายน้ำ กรุงเทพมหานคร (สนน. /water/ PageMap)",
        "url": "https://weather.bangkok.go.th/water/PageMap/GoogleMap",
        "fetched_at": fetched_at_of(bma_watermap_path), "trust_tier": "official_telemetry",
    })
    dwr_subbasin_path = newest_file_any(RAW / "gis" / "dwr_subbasin")
    out.append({
        "id": "dwr_gis_subbasin", "agency_th": "กรมทรัพยากรน้ำ (DWR) — ขอบเขตลุ่มน้ำสาขา (Sub_Basin)",
        "url": "https://gis.dwr.go.th/arcgis/rest/services",
        "fetched_at": fetched_at_of(dwr_subbasin_path), "trust_tier": "official_report",
    })
    # L5 survival-card + community-network block sources (2026-09-28, founder-approved
    # life-safety addition) -- reference documents only (no live pull, no fetched_at
    # path on disk), so `fetched_at` stays None; `build_sources_list()` already renders
    # a None fetched_at as "ไม่ทราบเวลา" (fmt_time_full's own documented fallback), never
    # a fabricated time.
    out.extend([
        {"id": "ready_gov_floods", "agency_th": "Ready.gov (สหรัฐฯ) — คำแนะนำรับมือน้ำท่วม",
         "url": "https://www.ready.gov/floods", "fetched_at": None, "trust_tier": "official_report"},
        {"id": "gov_uk_flood_prepare", "agency_th": "GOV.UK — เตรียมรับมือน้ำท่วม",
         "url": "https://www.gov.uk/prepare-for-flooding", "fetched_at": None,
         "trust_tier": "official_report"},
        {"id": "ddc_moph_flood_health", "agency_th": "กรมควบคุมโรค กระทรวงสาธารณสุข — สุขภาพช่วงน้ำท่วม",
         "url": "https://ddc.moph.go.th/brc/news.php?news=59806", "fetched_at": None,
         "trust_tier": "official_report"},
        {"id": "niems", "agency_th": "สถาบันการแพทย์ฉุกเฉินแห่งชาติ (สพฉ., 1669)",
         "url": "https://www.niems.go.th", "fetched_at": None, "trust_tier": "official_report"},
        {"id": "disaster_go_th", "agency_th": "กรมป้องกันและบรรเทาสาธารณภัย (ปภ., 1784)",
         "url": "https://www.disaster.go.th", "fetched_at": None, "trust_tier": "official_report"},
        {"id": "mea_flood_electric_safety",
         "agency_th": "การไฟฟ้านครหลวง (กฟน., 1130) — ความปลอดภัยไฟฟ้าช่วงน้ำท่วม",
         "url": "https://www.mea.or.th/public-relations/corporate-news-activities/announcement/mea-flood-electric-safety-2568",
         "fetched_at": None, "trust_tier": "official_report"},
        {"id": "bangkok_webportal", "agency_th": "กรุงเทพมหานคร (กทม., 1555)",
         "url": "https://webportal.bangkok.go.th", "fetched_at": None, "trust_tier": "official_report"},
    ])
    return out


def load_capacity_records() -> list[dict]:
    """Load site/inputs/capacity/bma_capacity.json's curated records list. Returns []
    on any read failure -- this is reference data for the page, never load-bearing for
    the rest of the build."""
    try:
        data = json.loads(CAPACITY_JSON_PATH.read_text(encoding="utf-8"))
        return data.get("records") or []
    except (OSError, json.JSONDecodeError):
        return []


def load_briefing() -> dict | None:
    """Load site/inputs/official/bma_briefing_2026-09-27_1100.json (governor interview via
    media, 27 ก.ย. -- newest, supersedes the 26 ก.ย. 13:00/16:15 official_report pair on
    the hero line; both 26 ก.ย. files stay on disk, never deleted, so their own facts
    remain in readout_log history). trust_tier official_report-via-media / tag RELAYED
    (a spoken interview relayed by media, not a กทม.-issued document), url OPEN. Returns
    None on any read failure -- this is reference/hero content, never load-bearing for
    the rest of the build."""
    try:
        return json.loads(BRIEFING_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_balance_yaml(node_id: str) -> dict:
    """Load site/inputs/areas/<node_id>.balance.yaml. Returns {} (never raises) if
    PyYAML is unavailable or the file is missing/unparseable -- the caller treats an
    empty dict the same as "every declared field missing", which is the honest outcome."""
    path = BALANCE_DIR / f"{node_id}.balance.yaml"
    if not HAVE_YAML or not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover - defensive, malformed yaml never crashes the build
        return {}


def _cfg_value(cfg: dict, key: str):
    """Pull a declared scalar value out of one field of a *.balance.yaml doc, e.g.
    cfg['A'] == {'value': 1568.737, 'tag': 'RELAYED', ...} -> 1568.737, or None if the
    field/value is absent (an honest OPEN declaration)."""
    field_cfg = cfg.get(key)
    if not isinstance(field_cfg, dict):
        return None
    return field_cfg.get("value")


def build_village_water_balance(node_id: str, generated_at_utc_iso: str,
                                 rain: dict | None) -> dict:
    """Run water_balance.step() for one village node (sammakorn/ram53) using ONLY the
    declared inputs in its *.balance.yaml. Both village yamls declare A/c/C_pump/S0 as
    OPEN today, so this always REFUSES -- that REFUSED outcome, with its reason codes,
    is exactly what the page's "สมดุลน้ำ" section must show (never a guessed number)."""
    cfg = load_balance_yaml(node_id)
    if wbmod is None:
        return {"status": "REFUSED", "reason_codes": ["MISSING_INPUT"],
                "inputs_present": [], "inputs_missing": ["water_balance module unavailable"]}

    p_mm = (rain or {}).get("mm_1h")
    p_m = (p_mm / 1000.0) if p_mm is not None else None

    inp = wbmod.WaterBalanceInputs(
        node_id=node_id, tick_index=0, tick_time=generated_at_utc_iso,
        S0=_cfg_value(cfg, "S0"), A=_cfg_value(cfg, "A"), c=_cfg_value(cfg, "c"),
        tau=_cfg_value(cfg, "tau") or 3600,
        C_pump=_cfg_value(cfg, "C_pump"),
        P=p_m, P_observed_at=(rain or {}).get("observed_at"),
        gate_flag=None, gate_flag_observed_at=None,
        Q_out_meas=None, Q_out_observed_at=None,
        inflow_edges=[], declared_edges=set(),
    )
    res = wbmod.step(inp, S_prev=None)
    return res.as_dict()


def build_bangkok_east_upper_bound(rain: dict | None, forecast: dict | None) -> dict:
    """Bangkok-wide/east-zone UPPER-BOUND arithmetic (maintainer decision 2026-09-26):
    rain-input volume (P * A, declared area only, NOT the water_balance.py ledger --
    runoff fraction c and storage S0 are OPEN for this node, so the actual ledger REFUSES,
    see build_village_water_balance-style call below) vs declared outflow capacity per
    hour, both in million m^3, plus the ratio. This is plain arithmetic on two declared
    quantities (A, C_pump) -- never a hydraulic model, never a substitute for
    water_balance.step()."""
    cfg = load_balance_yaml("bangkok_east")
    if wbmod is None or not cfg:
        return {"available": False, "reason": "bangkok_east.balance.yaml or water_balance module unavailable"}

    a_km2 = _cfg_value(cfg, "A")
    c_pump = _cfg_value(cfg, "C_pump")
    c_pump_cfg = cfg.get("C_pump") or {}
    breakdown = c_pump_cfg.get("breakdown") or []
    citywide_ref = c_pump_cfg.get("citywide_range_reference") or {}

    # Also run the actual PROP-FLOOD-03 ledger for this node -- c is OPEN, so this
    # REFUSES exactly like the villages; shown alongside the upper-bound arithmetic so
    # the page never confuses the two.
    ledger = build_village_water_balance("bangkok_east", rain and rain.get("observed_at")
                                          or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                          rain)

    if a_km2 is None or c_pump is None:
        return {"available": False, "reason": "A or C_pump not declared", "ledger": ledger}

    a_m2 = a_km2 * 1_000_000.0
    mm_1h = (rain or {}).get("mm_1h")
    mm_24h_forecast = (forecast or {}).get("next24h_mm") if (forecast or {}).get("available") else None

    def volume_million_m3(mm):
        if mm is None:
            return None
        return round((mm / 1000.0) * a_m2 / 1_000_000.0, 3)

    rain_now_vol = volume_million_m3(mm_1h)
    rain_forecast_vol = volume_million_m3(mm_24h_forecast)
    outflow_per_hour_m3 = c_pump * 3600.0
    outflow_per_hour_million_m3 = round(outflow_per_hour_m3 / 1_000_000.0, 3)

    ratio_now = (round(rain_now_vol / outflow_per_hour_million_m3, 3)
                 if (rain_now_vol is not None and outflow_per_hour_million_m3) else None)

    briefing = load_briefing()
    briefing_arithmetic = None
    if briefing:
        facts = briefing.get("declared_facts") or {}
        v_backlog = (facts.get("backlog_volume_phra_nakhon_side") or {}).get("value")
        q_official = (facts.get("total_bma_pumping_capacity") or {}).get("value")
        if v_backlog is not None and q_official:
            outflow_per_hour_m3_official = q_official * 3600.0
            hours_if_no_new_rain = round(v_backlog / outflow_per_hour_m3_official, 1)
            days_if_no_new_rain = round(hours_if_no_new_rain / 24.0, 1)
            extra_forecast_vol_m3 = ((rain_forecast_vol * 1_000_000.0)
                                      if rain_forecast_vol is not None else 0.0)
            hours_with_forecast_rain = round(
                (v_backlog + extra_forecast_vol_m3) / outflow_per_hour_m3_official, 1)
            days_with_forecast_rain = round(hours_with_forecast_rain / 24.0, 1)
            briefing_arithmetic = {
                "backlog_volume_m3": v_backlog,
                "pumping_capacity_m3s": q_official,
                "outflow_per_hour_m3": outflow_per_hour_m3_official,
                "hours_if_no_new_rain": hours_if_no_new_rain,
                "days_if_no_new_rain": days_if_no_new_rain,
                "hours_range_with_forecast_rain": [hours_if_no_new_rain, hours_with_forecast_rain],
                "days_range_with_forecast_rain": [days_if_no_new_rain, days_with_forecast_rain],
                "briefing_stated_days": (facts.get("estimated_drain_time_if_no_new_rain") or {}).get("value"),
                "caveat_th": ("52 ชม./2.2 วัน มาจากเลข V=223 ล้าน ลบ.ม. และ Q=1,200 ลบ.ม./วิ ที่ กทม. "
                              "แถลงเองเมื่อ 13:00 -- เป็นเลขคณิตธรรมดา (V หาร Q) ไม่ใช่แบบจำลอง; "
                              "ช่วงบนของช่วง (รวมฝนคาดการณ์) บวกฝนที่ Open-Meteo (แบบจำลองเปิด บุคคลที่สาม) "
                              "คาดว่าจะตกอีกใน 24 ชม.ข้างหน้าเข้าไปเป็นปริมาณน้ำเพิ่มเติม (ค่าบนสุดของช่วง, "
                              "ไม่ใช่ตัวเลขที่ กทม. แถลง)"),
            }

    return {
        "available": True,
        "area_km2": a_km2,
        "area_tag": (cfg.get("A") or {}).get("tag"),
        "c_pump_m3s": c_pump,
        "c_pump_breakdown": breakdown,
        "citywide_range_reference": citywide_ref,
        "rain_now_mm_1h": mm_1h,
        "rain_now_volume_million_m3": rain_now_vol,
        "rain_forecast_24h_mm": mm_24h_forecast,
        "rain_forecast_volume_million_m3": rain_forecast_vol,
        "outflow_capacity_per_hour_million_m3": outflow_per_hour_million_m3,
        "ratio_rain_now_vs_outflow_per_hour": ratio_now,
        "briefing_arithmetic": briefing_arithmetic,
        "ledger": ledger,
        "next_step_th": (cfg.get("next_step") or "").strip(),
        "caveat_th": ("สัดส่วนไหลบ่า (c) และปริมาณน้ำเก็บเริ่มต้น (S0) ยังไม่ได้ประกาศ "
                      "— ตัวเลขนี้เป็นแค่การเทียบ 'ปริมาณฝนที่ตกลงบนพื้นที่' กับ "
                      "'กำลังสูบสูงสุดที่ประกาศแล้ว' (upper bound) ไม่ใช่ผลลัพธ์สมดุลน้ำจริง"),
    }


# --- Canal graph (Toledo PROP-FLOOD-04, proposal) --------------------------------------

def load_canal_graph_yaml(graph_id: str = "east_chain") -> dict:
    """Load site/inputs/canals/<graph_id>.yaml. Returns {} (never raises) if PyYAML is
    unavailable or the file is missing/unparseable -- same posture as load_balance_yaml()."""
    path = CANALS_DIR / f"{graph_id}.yaml"
    if not HAVE_YAML or not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover - defensive, malformed yaml never crashes the build
        return {}


def build_canal_graph_readout(canal_by_code: dict, generated_at_utc_iso: str) -> dict:
    """Run Toledo PROP-FLOOD-04's edge_direction() over every edge declared in
    site/inputs/canals/east_chain.yaml, using today's cached thaiwater canal readings.
    Runs ONCE per build (city/east-zone-wide, not per-area) -- same size-budget reasoning
    as build_bangkok_east_upper_bound(). Returns {"available": False, ...} if the graph
    yaml or canal_graph.py itself is unavailable, never a guessed/partial readout."""
    graph = load_canal_graph_yaml("east_chain")
    if not graph or cgmod is None:
        return {"available": False,
                "reason": "east_chain.yaml or canal_graph module unavailable"}

    edges = [r.as_dict() for r in
             cgmod.compute_all_edges(graph, canal_by_code, generated_at_utc_iso)]

    obs_conn = open_observations_db()
    dry_season_rows = load_canal_normal_levels()
    try:
        nodes = {}
        normal_readouts = []
        for nid, n in (graph.get("nodes") or {}).items():
            code = n.get("canal_oldcode")
            s = canal_by_code.get(code) if code else None
            if not code:
                value_m, status, stale, observed_at = None, "NO_GAUGE", None, None
            elif s is None:
                value_m, status, stale, observed_at = None, "NO_DATA", True, None
            else:
                value_m = lwl.safe_float(s.get("level_m"))
                status = lwl.classify_level(s["level_m"], s.get("warning_level"),
                                             s.get("critical_level"), s.get("bank"))
                observed_at = s.get("observed_at")
                stale = is_stale(observed_at, generated_at_utc_iso)
            normal_level = canal_normal_level_readout(
                obs_conn, code, value_m, observed_at, dry_season_rows)
            if normal_level:
                normal_readouts.append(normal_level)
            nodes[nid] = {"label_th": n.get("label_th"), "canal_oldcode": code,
                          "is_gate": bool(n.get("is_gate")), "value_m": value_m,
                          "status": status, "observed_at": observed_at, "stale": stale,
                          "normal_level": normal_level}
    finally:
        if obs_conn is not None:
            obs_conn.close()

    return {
        "available": True,
        "graph_id": graph.get("graph_id", "east_chain"),
        "epistemic_note_th": graph.get("epistemic_note_th"),
        "sensor_resolution_m": (graph.get("sensor_resolution_m") or {}).get("value"),
        "stale_after_hours": graph.get("stale_after_hours"),
        "nodes": nodes,
        "edges": edges,
        "next_step_th": (graph.get("next_step_th") or "").strip(),
        "normal_level_hero": canal_normal_level_hero_summary(normal_readouts),
    }


# --- Sammakorn head chain (build 6, 2026-09-27 -- PROP-FLOOD-04 instantiation) ----------
# Founder ask (verbatim, docs/SAMMAKORN_STANDING_WATER_2026-09-27.md's own header):
# "ดูหน่อยจากข้อมูลที่มี เราหาการไหลของน้ำที่ค้างอยู่ในหมู่บ้านสัมมากรได้ไหม และบอกได้ไหมว่า
# ตรงไหนมันตัน" -- and a same-day follow-up correction (verbatim): "สัมมากรต้องเชื่อมกับน้ำใน
# คลองด้วย เพราะมันเป็นน้ำย้อนจากคลอง ไม่ใช่แค่ปั๊ม" ("Sammakorn must also be linked to the
# canal's own water, because it's backflow FROM the canal, not just the pumps"). This
# section instantiates PROP-FLOOD-04's edge-direction readout over the declared chain
# ซอย(ผิวน้ำ) -> บึงสัมมากร (WL.SMK.01) -> คลองบ้านม้า 2 (WL.BMA.02) -> คลองแสนแสบ (WL.SSB.08),
# with an EXPLICIT reverse/backflow edge (`kind="backflow-risk"`, บ้านม้า 2 -> บึง) alongside
# the ordinary downstream edges -- gravity flow can run either way depending on which side
# is higher, and this village's own community reports say it has: 26 ก.ย. ซอย 59 "ขึ้นโรงรถ/
# หลังบ้าน จากท่อน้ำคลอง" and ซอย 17 "เข้าโรงรถ + ย้อนขึ้นท่อ" (both
# site/inputs/community/community_reports_2026-09-26.md, tag **RELAYED** -- a community
# report, not an instrument reading, per this repo's own epistemic-tag rule, AGENTS.md §2;
# used here only as corroborating evidence that backflow is a real mechanism this event,
# never promoted to MEASURED).
#
# Every edge below carries THREE INDEPENDENT readouts, never conflated (repeats this
# repo's own founder rule from the same doc: "สถานะประตู ≠ ทิศทางการไหล ≠ น้ำนิ่ง/ตัน"):
#   1. gate_state   -- measured/inferred/unknown, from a declared control structure if any
#   2. flow_direction -- ΔH sign (declared epsilon), or a same-side band-comparison
#                        fallback when datum is unknown (see below)
#   3. flow_status  -- moving/stalled/unknown, from lag-k rate or active pumping --
#                      INDEPENDENT of gate_state (a closed gate does not imply stalled if
#                      pumps are actively lifting water; an open gate does not imply
#                      moving if ΔH is flat)
#
# `datum: None` on every declared node is NOT a placeholder left carelessly blank -- it is
# this repo's own honest, currently-verified state (see the Sammakorn doc's own REFUSED
# item: "ไม่มีค่า MSL ของ WL.SMK.01/WL.BMA.02 ในคลังนี้ ไม่มี anchor ใดเชื่อมถึงตัวเลขนี้ได้เลย").
# Every edge therefore currently REFUSES a true ΔH-in-metres (DATUM_UNKNOWN) except the
# declared backflow-risk edge, which instead falls back to a same-side band comparison
# (canal at/above its own critical AND pond at/below its own bank -> "เสี่ยงย้อน", INSTINCT,
# never a fabricated cross-datum number) -- this degrades to "unavailable" (never a guess)
# when either station has no declared bank threshold, which is this repo's current state
# for these three stations (bank is not yet populated by any collector).
SAMMAKORN_CHAIN_FLOW_EPSILON_M = 0.03   # declared OPEN-convention, INSTINCT (own constant,
# same posture as canal_graph.py's DEFAULT_EPSILON_M -- not a Toledo-registered figure)
SAMMAKORN_STALL_LAGK_M_PER_H = 0.01
SAMMAKORN_MAX_DT_MINUTES = 60.0

SAMMAKORN_CHAIN_NODES = {
    "soi": {"label_th": "ซอย (ผิวน้ำ)", "station_code": None, "source_id": None, "datum": None},
    "pond": {"label_th": "บึงสัมมากร (บึง 2, WL.SMK.01)", "station_code": "WL.SMK.01",
             "source_id": "bma_watermap", "datum": None},
    "banma2": {"label_th": "คลองบ้านม้า 2 @ รามคำแหง (WL.BMA.02)", "station_code": "WL.BMA.02",
               "source_id": "bma_watermap", "datum": None},
    "saensaeb": {"label_th": "คลองแสนแสบ @ เสรีไทย 24 (WL.SSB.08)", "station_code": "WL.SSB.08",
                 "source_id": "bma_watermap", "datum": None},
}

SAMMAKORN_CHAIN_EDGES = [
    {"edge_id": "soi_to_pond", "up": "soi", "down": "pond", "kind": "outflow",
     "label_th": "ซอย → บึง"},
    {"edge_id": "pond_to_banma2", "up": "pond", "down": "banma2", "kind": "outflow",
     "label_th": "บึง → คลองบ้านม้า 2"},
    {"edge_id": "banma2_to_pond", "up": "banma2", "down": "pond", "kind": "backflow-risk",
     "label_th": "คลองบ้านม้า 2 → บึง (ย้อน)"},
    {"edge_id": "banma2_to_saensaeb", "up": "banma2", "down": "saensaeb", "kind": "outflow",
     "label_th": "คลองบ้านม้า 2 → คลองแสนแสบ"},
]

SAMMAKORN_COMMUNITY_BACKFLOW_EVIDENCE = [
    {"soi": "ซอย 59 (สุดซอย/ปากซอย)", "time_th": "06:00-10:00 น. 26 ก.ย.",
     "text_th": "ขึ้นโรงรถ/หลังบ้าน จากท่อน้ำคลอง", "tag": "RELAYED",
     "source": "site/inputs/community/community_reports_2026-09-26.md"},
    {"soi": "ซอย 17", "time_th": "11:10 น. 26 ก.ย.",
     "text_th": "เข้าโรงรถ + ย้อนขึ้นท่อ/ห้องน้ำชั้นล่าง", "tag": "RELAYED",
     "source": "site/inputs/community/community_reports_2026-09-26.md"},
]


# ---- Neighbour-consistency (suspect-station) rule ---------------------------------
# Founder rule (verbatim, 2026-09-27, real incident): "แสนแสบเสรีไทยทำไมปกติ ตรวจหลายแห่ง
# รวมหน่อย" -- WL.SSB.08 (เสรีไทย 24) read -0.13 ปกติ while EVERY neighbouring Saen Saep
# station was WARN/CRIT (SSB.07 บางกะปิ 0.40 WARN, SSB.06 0.49 CRIT, SSB.09 บางชัน 0.95
# CRIT, SSB.10 1.01, SSB.12 1.22) and its own 26 ก.ย. trace swung +0.80 -> -0.34 -> -0.62
# within 3h -- an outlier/suspect single sensor, not a real "this one spot is fine".
# Declared INSTINCT-rule (NOT a Toledo equation -- a data-hygiene/outlier-flag heuristic,
# same posture as SAMMAKORN_CHAIN_FLOW_EPSILON_M above): a station whose status class
# differs from EVERY station within `window` positions of it in a declared canal-profile
# ORDER is flagged `suspect: true`.
SAENSAEB_NEIGHBOUR_ORDER = ["WL.SSB.12", "WL.SSB.10", "WL.SSB.09", "WL.SSB.08",
                            "WL.SSB.07", "WL.SSB.06", "WL.SSB.04"]
# This order is an INSTINCT extrapolation of this repo's own site/inputs/canals/
# east_chain.yaml convention (that file declares WL.SSB.10/09/08/07/04 in strictly
# descending code-number order = downstream direction) -- WL.SSB.06/12 are NOT nodes in
# east_chain.yaml's graph at all, so their position here is declared by the same
# descending-code-number convention, never claimed as a surveyed/verified distance.
SAENSAEB_NEIGHBOUR_WINDOW = 2


def neighbour_consistency_check(order: list, statuses: dict, target_code: str,
                                  window: int = SAENSAEB_NEIGHBOUR_WINDOW) -> dict:
    """Generic, reusable outlier-flag: is `target_code`'s status DIFFERENT from every
    other station within `window` positions of it in `order`? Never flags off a single
    neighbour ("ตรวจหลายแห่งรวมหน่อย" -- check SEVERAL places together) -- needs at least
    2 real neighbour statuses to render any verdict; missing/insufficient data returns
    `suspect: False` with a `reason`, never a fabricated verdict.

    Returns {"suspect": bool, "own_status": str|None,
             "neighbour_statuses": {code: status}} or
            {"suspect": False, "reason": "..."} when the check cannot run.
    """
    if target_code not in order:
        return {"suspect": False, "reason": "not_in_declared_order"}
    idx = order.index(target_code)
    own = statuses.get(target_code)
    if own is None:
        return {"suspect": False, "reason": "no_status_for_target"}
    neighbour_codes = [order[i] for i in range(max(0, idx - window), min(len(order), idx + window + 1))
                        if i != idx]
    neighbour_statuses = {c: statuses[c] for c in neighbour_codes
                           if c in statuses and statuses[c] is not None}
    if len(neighbour_statuses) < 2:
        return {"suspect": False, "reason": "insufficient_neighbour_data",
                "own_status": own, "neighbour_statuses": neighbour_statuses}
    suspect = all(s != own for s in neighbour_statuses.values())
    return {"suspect": suspect, "own_status": own, "neighbour_statuses": neighbour_statuses}


_STATUS_SEVERITY_ORDER = ["NORMAL", "WATCH", "CRITICAL", "OVERBANK"]
_STATUS_SEVERITY_TH = {"WATCH": "เตือน", "CRITICAL": "วิกฤต", "OVERBANK": "ล้นตลิ่ง",
                        "NORMAL": "ปกติ"}


def _neighbour_band_label_th(neighbour_statuses: dict) -> str:
    """Founder instruction: "ใช้ multi-station BAND แทน" -- e.g. 'แสนแสบใกล้หมู่บ้าน =
    SSB.07 + SSB.06 + SSB.09 -> เตือน-วิกฤต'. Renders the [min severity, max severity]
    span across the given neighbour statuses, Thai labels, never a single collapsed
    number."""
    known = [s for s in neighbour_statuses.values() if s in _STATUS_SEVERITY_ORDER]
    if not known:
        return "ยังไม่มีคำตอบ"
    ranks = sorted({_STATUS_SEVERITY_ORDER.index(s) for s in known})
    lo_th = _STATUS_SEVERITY_TH[_STATUS_SEVERITY_ORDER[ranks[0]]]
    hi_th = _STATUS_SEVERITY_TH[_STATUS_SEVERITY_ORDER[ranks[-1]]]
    return lo_th if lo_th == hi_th else f"{lo_th}–{hi_th}"


def saensaeb_suspect_check(conn, generated_at_utc_iso: str) -> dict:
    """Runs `neighbour_consistency_check()` for WL.SSB.08 against its declared Saen Saep
    neighbours (`SAENSAEB_NEIGHBOUR_ORDER`), reading each station's current danger-band
    status (`lwl.classify_level`, 4-arg -- the ORIGINAL warning/critical/bank ladder, not
    the normal-level one) straight from `bma_watermap`. Returns
    `neighbour_consistency_check()`'s own dict plus `"band_label_th"` (the multi-station
    band the founder asked for as the outer-canal replacement anchor when SSB.08 itself
    is suspect). Never raises -- degrades to `{"suspect": False, "reason": ...}` on any
    missing conn/data, same posture as every other function in this section."""
    if conn is None:
        return {"suspect": False, "reason": "no_db_connection"}
    statuses = {}
    for code in SAENSAEB_NEIGHBOUR_ORDER:
        reading = _sammakorn_latest_reading(conn, "bma_watermap", code)
        if reading is None:
            continue
        statuses[code] = lwl.classify_level(
            reading["value_m"], reading.get("warning"), reading.get("critical"),
            reading.get("bank"))
    result = neighbour_consistency_check(SAENSAEB_NEIGHBOUR_ORDER, statuses, "WL.SSB.08")
    idx = SAENSAEB_NEIGHBOUR_ORDER.index("WL.SSB.08")
    band_codes = [SAENSAEB_NEIGHBOUR_ORDER[i] for i in
                  range(max(0, idx - SAENSAEB_NEIGHBOUR_WINDOW),
                        min(len(SAENSAEB_NEIGHBOUR_ORDER), idx + SAENSAEB_NEIGHBOUR_WINDOW + 1))
                  if i != idx]
    band_statuses = {c: statuses[c] for c in band_codes if c in statuses}
    result["band_label_th"] = _neighbour_band_label_th(band_statuses)
    if result.get("suspect") and store is not None:
        # Log a contradictions row (best-effort, never crashes the build) -- a WRITABLE
        # connection is opened here specifically for this one insert, same posture as
        # this file's other write-on-detect call sites (build_burden_ledger_readout's
        # gate-state contradiction, above).
        try:
            write_conn = store.connect(OBS_DB_PATH) if OBS_DB_PATH.exists() else None
        except Exception:  # pragma: no cover - defensive
            write_conn = None
        if write_conn is not None:
            try:
                store.insert_contradiction(
                    write_conn, observed_at_utc=generated_at_utc_iso,
                    topic="neighbour_consistency:WL.SSB.08",
                    source_a="bma_watermap:WL.SSB.08", value_a=result["own_status"],
                    source_b="bma_watermap:neighbours",
                    value_b=json.dumps(result["neighbour_statuses"], ensure_ascii=False),
                    note="WL.SSB.08 differs from every station within "
                         f"{SAENSAEB_NEIGHBOUR_WINDOW} positions in the declared Saen "
                         "Saep profile order -- suspect single sensor, excluded as an "
                         "anchor; see docs/SAMMAKORN_STANDING_WATER_2026-09-27.md anchor A2 "
                         "retraction.")
            finally:
                write_conn.close()
    return result


def _sammakorn_latest_reading(conn, source_id, station_code) -> dict | None:
    """Latest reading for one Sammakorn chain node, excluding sensor-faulted rows (same
    query-time guard as previous_reading() above -- degrades to unfiltered when the
    `status` column itself is absent, e.g. a minimal test DB)."""
    if conn is None or not source_id or not station_code:
        return None
    fault_placeholders = ",".join("?" for _ in lwl.SENSOR_FAULT_STATUS_TH)
    try:
        try:
            row = conn.execute(
                "SELECT value, observed_at_utc, warning, critical, bank, status "
                "FROM observations WHERE source_id = ? AND station_code = ? "
                f"AND (status IS NULL OR status NOT IN ({fault_placeholders})) "
                "ORDER BY observed_at_utc DESC LIMIT 1",
                (source_id, station_code, *lwl.SENSOR_FAULT_STATUS_TH),
            ).fetchone()
        except sqlite3.OperationalError:
            row = conn.execute(
                "SELECT value, observed_at_utc, warning, critical, bank, status "
                "FROM observations WHERE source_id = ? AND station_code = ? "
                "ORDER BY observed_at_utc DESC LIMIT 1",
                (source_id, station_code),
            ).fetchone()
    except sqlite3.Error:  # pragma: no cover - defensive
        return None
    if row is None:
        return None
    value, observed_at, warning, critical, bank, status_th = row
    return {"value_m": value, "observed_at": observed_at, "warning": warning,
            "critical": critical, "bank": bank, "status_th": status_th,
            "sensor_status": lwl.sensor_status_from_status_th(status_th)}


# Founder rule (verbatim, 2026-09-27, real incident -- WL.BMA.02 showed "ยังไม่มีเกณฑ์ปกติ"
# on the hero map but "ปกติ" in this section, for the SAME station+reading): "ปกติ" may
# only ever be shown when a normal_level is on record AND the reading is at/below it --
# otherwise "ยังไม่มีเกณฑ์ปกติ" (no basis) or "สูงกว่าปกติ" (above normal, still below every
# danger threshold). The hero map (tools/heromap/sammakorn_map.py's `classify_tier()`)
# already re-derives its own tier straight from value_m/warning/critical/bank/normal_level_m
# instead of trusting this node's `status_th` -- that's WHY it was right while this section
# was wrong: `_sammakorn_latest_reading()`'s `status_th` is either the bma_watermap AGENCY's
# own raw status text (their own "ปกติ" threshold, not ours) or an old 4-arg
# `classify_level()` call with no normal-basis opt-in at all -- neither ever asks "does this
# station even have OUR normal_level_m on record". Fixed by running the SAME
# `resolve_normal_level()` + `classify_level(..., normal_level=...)` ladder every other
# normal-level-aware section of this file already uses (see `build_near_stations()` /
# `build_upstream_stations()` above), so a chain node's `status_th` and the hero map's tier
# word always agree for the same station+reading. The raw agency text is kept, never
# discarded, under `agency_status_th` for audit.
SAMMAKORN_STATUS_CODE_TH = {
    "OVERBANK": "ล้นตลิ่ง", "CRITICAL": "วิกฤต", "WATCH": "เตือน",
    "NORMAL": "ปกติ", "ABOVE_NORMAL": "สูงกว่าปกติ", "NO_NORMAL_BASIS": "ยังไม่มีเกณฑ์ปกติ",
    "NO_THRESHOLD": "ไม่มีข้อมูลล่าสุด",
}


def sammakorn_node_readout(conn, node_id: str, node_def: dict,
                            generated_at_utc_iso: str, dry_season_rows: dict | None = None) -> dict:
    """One chain node's current reading, or an explicit NO_GAUGE/NO_DATA readout --
    never a fabricated value. Carries its own station_code/source_id/datum through so
    `_sammakorn_lagk_rate()` and the edge function below don't need a second lookup.

    `status_th` is always run through the normal-basis ladder (see module note above
    `SAMMAKORN_STATUS_CODE_TH`) -- never the raw bma_watermap agency label, so this
    section's word for a station always matches the hero map's word for the same
    station+reading."""
    base = {"node_id": node_id, "label_th": node_def.get("label_th"),
            "station_code": node_def.get("station_code"),
            "source_id": node_def.get("source_id"), "datum": node_def.get("datum")}
    if not node_def.get("station_code"):
        return {**base, "value_m": None, "observed_at": None, "status_th": "NO_GAUGE",
                "sensor_status": None, "stale": None, "warning": None, "critical": None,
                "bank": None, "normal_level_m": None, "normal_level_basis": None,
                "agency_status_th": None,
                "readout_th": "ไม่มีเกจวัดผิวน้ำในซอย (มีแต่รายงานชุมชนระดับ tier) — OPEN"}
    reading = _sammakorn_latest_reading(conn, node_def["source_id"], node_def["station_code"])
    if reading is None:
        return {**base, "value_m": None, "observed_at": None, "status_th": "NO_DATA",
                "sensor_status": None, "stale": True, "warning": None, "critical": None,
                "bank": None, "normal_level_m": None, "normal_level_basis": None,
                "agency_status_th": None, "readout_th": "ไม่มีข้อมูล — OPEN"}
    dry_season_rows = load_canal_normal_levels() if dry_season_rows is None else dry_season_rows
    normal = resolve_normal_level(conn, node_def["station_code"], dry_season_rows)
    normal_level_for_status = (
        normal["value"] if normal["value"] is not None else lwl.NO_NORMAL_LEVEL)
    status_code = lwl.classify_level(
        reading["value_m"], reading.get("warning"), reading.get("critical"), reading.get("bank"),
        normal_level=normal_level_for_status)
    status_th = SAMMAKORN_STATUS_CODE_TH.get(status_code, reading["status_th"])
    return {**base, "value_m": reading["value_m"], "observed_at": reading["observed_at"],
            "status_th": status_th, "status_code": status_code,
            "agency_status_th": reading["status_th"], "sensor_status": reading["sensor_status"],
            "stale": is_stale(reading["observed_at"], generated_at_utc_iso),
            "warning": reading["warning"], "critical": reading["critical"],
            "bank": reading["bank"], "normal_level_m": normal["value"],
            "normal_level_basis": normal["basis"]}


def _sammakorn_lagk_rate(conn, node: dict, min_gap_hours: float = 1.0) -> float | None:
    """PROP-FLOOD-01 lag-k rate (m/h) for one chain node's own history -- reuses
    previous_reading() above, never a re-implementation. None when there is no
    qualifying prior reading (never guessed)."""
    if conn is None or not node.get("station_code") or node.get("value_m") is None \
            or not node.get("observed_at"):
        return None
    prev = previous_reading(conn, node["source_id"], node["station_code"],
                             node["value_m"], node["observed_at"], min_gap_hours=min_gap_hours)
    if prev is None:
        return None
    try:
        cur_dt = datetime.datetime.fromisoformat(node["observed_at"])
        prev_dt = datetime.datetime.fromisoformat(prev["observed_at"])
    except (TypeError, ValueError):
        return None
    hours = (cur_dt - prev_dt).total_seconds() / 3600.0
    if hours <= 0:
        return None
    return prev["delta"] / hours


def sammakorn_band_backflow_risk(canal_node: dict, pond_node: dict) -> dict:
    """INSTINCT fallback used only when datum is unknown/mismatched -- compares each
    station against its OWN declared threshold instead of a cross-datum ΔH in metres.
    Founder rule (verbatim, 27 ก.ย.): "สัมมากรต้องเชื่อมกับน้ำในคลองด้วย เพราะมันเป็นน้ำย้อน
    จากคลอง ไม่ใช่แค่ปั๊ม". Never fabricates a bank/critical figure this repo doesn't have
    -- "unavailable" (not a guessed risk level) when either threshold is missing, which is
    this repo's current state (no collector populates `bank` for these stations yet)."""
    canal_value, canal_critical = canal_node.get("value_m"), canal_node.get("critical")
    pond_value, pond_bank = pond_node.get("value_m"), pond_node.get("bank")
    if canal_value is None or canal_critical is None or pond_value is None or pond_bank is None:
        return {"value": "unavailable", "basis": "no_bank_threshold_declared"}
    if canal_value >= canal_critical and pond_value <= pond_bank:
        return {"value": "เสี่ยงย้อน", "basis": "band_comparison"}
    return {"value": "ไม่เสี่ยงย้อน (เท่าที่วัดได้)", "basis": "band_comparison"}


def _sammakorn_edge_refusal_reasons(up: dict, down: dict) -> list:
    reasons = []
    if up.get("suspect") or down.get("suspect"):
        reasons.append("SUSPECT_NEIGHBOUR_MISMATCH")
    if up.get("value_m") is None or down.get("value_m") is None:
        reasons.append("MISSING_INPUT")
        return reasons
    if up.get("sensor_status") == "fault" or down.get("sensor_status") == "fault":
        reasons.append("FAULT_INPUT")
    if up.get("stale") or down.get("stale"):
        reasons.append("STALE_INPUT")
    up_dt, down_dt = up.get("observed_at"), down.get("observed_at")
    if up_dt and down_dt:
        try:
            u = datetime.datetime.fromisoformat(up_dt)
            d = datetime.datetime.fromisoformat(down_dt)
            if abs((u - d).total_seconds()) / 60.0 > SAMMAKORN_MAX_DT_MINUTES:
                reasons.append("DT_EXCEEDS_60MIN")
        except ValueError:
            reasons.append("UNPARSEABLE_TIMESTAMP")
    return reasons


def sammakorn_edge_readout(conn, edge_def: dict, nodes: dict, generated_at_utc_iso: str,
                            gate_state: dict | None = None, pumps_on: int = 0) -> dict:
    """One edge's full readout: the shared head-edge fields (h_up/h_down/datum_*/
    observed_at_*/age_h/sensor_status_*/source_*/delta_h/direction/refusal_reason) plus
    the three independent readouts (gate_state, flow_direction, flow_status)."""
    up, down = nodes[edge_def["up"]], nodes[edge_def["down"]]
    eps = SAMMAKORN_CHAIN_FLOW_EPSILON_M
    reasons = _sammakorn_edge_refusal_reasons(up, down)
    is_backflow_edge = edge_def.get("kind") == "backflow-risk"

    delta_h = None
    band_result = None
    datum_known = (up.get("datum") is not None and down.get("datum") is not None
                   and up["datum"] == down["datum"])
    if "MISSING_INPUT" not in reasons:
        if datum_known and not reasons:
            delta_h = up["value_m"] - down["value_m"]
        elif is_backflow_edge:
            # band fallback tries even when stale/faulted elsewhere -- it degrades on
            # its own missing-threshold check, never silently inherits an unrelated
            # refusal reason.
            band_result = sammakorn_band_backflow_risk(canal_node=up, pond_node=down)
            if band_result["value"] == "unavailable" and not reasons:
                reasons = ["NO_BANK_THRESHOLD_DECLARED"]
        elif not reasons:
            reasons = ["DATUM_UNKNOWN"]

    gate_readout = dict(gate_state) if gate_state is not None else \
        {"value": "unknown", "basis": "NO_GATE_DECLARED"}

    if delta_h is not None:
        if delta_h > eps:
            direction_value = "up_to_down"
        elif delta_h < -eps:
            direction_value = "down_to_up"
        else:
            direction_value = "flat"
        flow_direction = {"value": direction_value, "delta_h_m": round(delta_h, 3),
                           "epsilon_m": eps, "basis": "delta_h"}
    elif band_result is not None:
        flow_direction = {"value": band_result["value"], "basis": band_result["basis"]}
    else:
        flow_direction = {"value": "unknown", "reason_codes": list(reasons)}

    up_rate = _sammakorn_lagk_rate(conn, up)
    down_rate = _sammakorn_lagk_rate(conn, down)
    if pumps_on and pumps_on > 0:
        flow_status = {"value": "moving", "basis": "pumps_running", "pumps_on": pumps_on}
    elif delta_h is not None and abs(delta_h) < eps:
        flow_status = {"value": "stalled", "basis": "delta_h_flat"}
    elif (up_rate is not None and down_rate is not None
          and abs(up_rate) < SAMMAKORN_STALL_LAGK_M_PER_H
          and abs(down_rate) < SAMMAKORN_STALL_LAGK_M_PER_H):
        flow_status = {"value": "stalled", "basis": "lag_k_flat_both_nodes",
                       "up_rate_m_per_h": up_rate, "down_rate_m_per_h": down_rate}
    elif up_rate is None and down_rate is None and delta_h is None:
        flow_status = {"value": "unknown", "basis": "insufficient_history"}
    else:
        flow_status = {"value": "moving", "basis": "rate_or_delta_nonflat",
                       "up_rate_m_per_h": up_rate, "down_rate_m_per_h": down_rate}

    backflow_active = None
    if is_backflow_edge:
        if flow_direction["value"] in ("up_to_down", "เสี่ยงย้อน"):
            backflow_active = True
        elif flow_direction["value"] in ("down_to_up", "flat", "ไม่เสี่ยงย้อน (เท่าที่วัดได้)"):
            backflow_active = False

    age_h = None
    for a in (up.get("observed_at"), down.get("observed_at")):
        h = None
        try:
            if a:
                h = (datetime.datetime.fromisoformat(generated_at_utc_iso)
                     - datetime.datetime.fromisoformat(a)).total_seconds() / 3600.0
        except (TypeError, ValueError):
            h = None
        if h is not None and (age_h is None or h > age_h):
            age_h = h

    return {
        "edge_id": edge_def["edge_id"], "kind": edge_def.get("kind", "outflow"),
        "label_th": edge_def.get("label_th"), "u": edge_def["up"], "v": edge_def["down"],
        "h_up": up.get("value_m"), "h_down": down.get("value_m"),
        "datum_up": up.get("datum"), "datum_down": down.get("datum"),
        "observed_at_up": up.get("observed_at"), "observed_at_down": down.get("observed_at"),
        "age_h": round(age_h, 2) if age_h is not None else None,
        "sensor_status_up": up.get("sensor_status"), "sensor_status_down": down.get("sensor_status"),
        "source_up": up.get("source_id"), "source_down": down.get("source_id"),
        "delta_h": round(delta_h, 3) if delta_h is not None else None,
        "direction": flow_direction["value"],
        "status": "OK" if (delta_h is not None or (band_result is not None
                            and band_result["value"] != "unavailable")) else "REFUSED",
        "refusal_reason": reasons[0] if reasons else None,
        "reason_codes": list(reasons),
        "gate_state": gate_readout, "flow_direction": flow_direction,
        "flow_status": flow_status, "backflow_active": backflow_active,
    }


def sammakorn_chain_readout(conn, generated_at_utc_iso: str,
                             pump_rows: list | None = None) -> dict:
    """Top-level Sammakorn head-chain readout -- see this section's own header comment.
    `pump_rows` (the same ST.SPS pump-row list build_pumps() consumes) feeds the
    pond->banma2 outflow edge's `flow_status` (pumps actively lifting water out of the
    pond is its own independent evidence of "moving", regardless of gate_state)."""
    dry_season_rows = load_canal_normal_levels()
    nodes = {nid: sammakorn_node_readout(conn, nid, ndef, generated_at_utc_iso, dry_season_rows)
              for nid, ndef in SAMMAKORN_CHAIN_NODES.items()}
    # Neighbour-consistency check (founder rule, verbatim, 2026-09-27 -- see this
    # section's own docstring above `SAENSAEB_NEIGHBOUR_ORDER`): WL.SSB.08 is the
    # "saensaeb" node's own station -- when it's an outlier against its declared
    # neighbours, mark it suspect (grey pill + excluded as an anchor, never deleted).
    suspect_check = saensaeb_suspect_check(conn, generated_at_utc_iso)
    if "saensaeb" in nodes:
        nodes["saensaeb"]["suspect"] = bool(suspect_check.get("suspect"))
        nodes["saensaeb"]["suspect_note_th"] = (
            "ค่าเดี่ยวขัดกับเพื่อนบ้าน — ไม่ใช้เป็นตัวแทนคลอง" if suspect_check.get("suspect") else None)
        nodes["saensaeb"]["neighbour_band_label_th"] = suspect_check.get("band_label_th")
        nodes["saensaeb"]["neighbour_statuses"] = suspect_check.get("neighbour_statuses")
    pumps_on_total = sum(
        (r.get("pumps_on") or 0) for r in (pump_rows or [])
        if str(r.get("code") or r.get("station_code") or "").startswith("ST.SPS"))
    edges = []
    for edge_def in SAMMAKORN_CHAIN_EDGES:
        pumps_on = pumps_on_total if edge_def["up"] == "pond" else 0
        edges.append(sammakorn_edge_readout(conn, edge_def, nodes, generated_at_utc_iso,
                                             gate_state=None, pumps_on=pumps_on))
    return {
        "available": True, "epsilon_m": SAMMAKORN_CHAIN_FLOW_EPSILON_M,
        "nodes": nodes, "edges": edges,
        "community_backflow_evidence": list(SAMMAKORN_COMMUNITY_BACKFLOW_EVIDENCE),
        "saensaeb_suspect_check": suspect_check,
        "next_step_th": ("อ่านระดับบึง (WL.SMK.01) และคลองบ้านม้า 2 (WL.BMA.02) พร้อมกัน "
                          "3 รอบ ห่างรอบละ 30 นาที (ดู "
                          "docs/SAMMAKORN_STANDING_WATER_2026-09-27.md §5)"),
    }


# --- LAYER 0 (น้ำเข้า/น้ำออก/รับมือได้) -- wiring into the live pipeline -----------------
# tools/layer0/ itself is written by another worker as a standalone, non-network,
# new-files-only module (see docs/LAYER0_IN_OUT_CAPACITY.md) -- not wired into any build
# script by that worker's own write-scope. This section does the wiring: turns this
# build's own already-computed rain/pump/backflow readouts into tools.layer0.Reading /
# BackflowState `live` overrides and calls the three build_* functions, so the TOP block
# on the public page uses this run's real numbers instead of tools/layer0's own
# hardcoded 26-27 ก.ย. defaults. Falls back to those hardcoded defaults (still tagged
# honestly, still REFUSED where genuinely absent) whenever a live input is missing or
# `layer0mod` failed to import -- never fabricates a number to fill a gap (this file's
# own no-fabrication discipline, matching tools/layer0's own).

def _layer0_ensemble_rain_24h(now_local) -> tuple:
    """Sums the next 24 HOURLY rows of load_multimodel_hourly()'s median_mm/max_mm --
    an ensemble-median/max 24h-ahead rain forecast, at the Sammakorn point (used as the
    zone proxy, same posture as build_bangkok_east_upper_bound's own rain_source_note_th
    above). Returns (median_24h_mm, max_24h_mm, n_models) or (None, None, 0) if no
    multimodel file is on disk this run."""
    rows = load_multimodel_hourly()
    if not rows:
        return None, None, 0
    now_floor = now_local.replace(minute=0, second=0, microsecond=0)
    future = []
    for r in rows:
        try:
            local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M").replace(
                tzinfo=BANGKOK_TZ)
        except ValueError:
            continue
        if local_dt >= now_floor:
            future.append(r)
    window = future[:24]
    if not window:
        return None, None, 0
    median_sum = sum(r["median_mm"] for r in window)
    max_sum = sum(r["max_mm"] for r in window)
    n = max((r["n"] for r in window), default=0)
    return round(median_sum, 1), round(max_sum, 1), n


def _layer0_forecast_24h_range(now_local) -> dict | None:
    """Per-MODEL next-24h rain totals (not an average) -- reuses the same
    raw/forecast/openmeteo_<model>.json files as load_multimodel_hourly(), but keeps
    each model's own 24h sum separate instead of collapsing to one median/max pair, so
    the public page can show a genuine min-max RANGE across named models plus a
    parenthetical mid-point, never a single averaged headline number. Returns
    {"min_mm", "max_mm", "median_mm", "n_models", "per_model": {model: mm}} or None if
    no multimodel file is on disk this run."""
    now_floor = now_local.replace(minute=0, second=0, microsecond=0)
    window_end = now_floor + datetime.timedelta(hours=24)
    per_model_total = {}
    for model in FORECAST_MODELS:
        path = FORECAST_DIR / f"openmeteo_{model}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if parsers is None:
            continue
        try:
            rows = parsers.parse_openmeteo_forecast(data)
        except Exception:  # pragma: no cover - defensive
            continue
        total = 0.0
        found_any = False
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M").replace(
                    tzinfo=BANGKOK_TZ)
            except ValueError:
                continue
            if now_floor <= local_dt < window_end:
                total += r["mm"] or 0.0
                found_any = True
        if found_any:
            per_model_total[model] = round(total, 1)
    if not per_model_total:
        return None
    vals = sorted(per_model_total.values())
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return {"min_mm": vals[0], "max_mm": vals[-1], "median_mm": round(median, 1),
            "n_models": n, "per_model": per_model_total}


_FORECAST16D_SOURCE_IDS = ("openmeteo_forecast16d", "metno_locationforecast")


def _load_point_forecast_daily(conn, point_id: str) -> dict:
    """Query the append-only observations store for this point's per-model DAILY
    forecast rows (collect.collect_openmeteo_forecast16d / collect_metno_locationforecast
    -- Commit 3's 8-point wiring, station_code shaped f"{point_id}:{model}"). Returns
    {model: {date_str: mm}}. Returns {} (never raises) on any DB error or when this point
    has no rows yet -- callers must fall back to the older Sammakorn-only file-based
    reader (`FORECAST_DIR`/openmeteo_<model>.json), never fabricate a value."""
    if conn is None:
        return {}
    try:
        placeholders = ",".join("?" for _ in _FORECAST16D_SOURCE_IDS)
        rows = conn.execute(
            f"""SELECT station_code, observed_at_utc, value FROM observations
                WHERE source_id IN ({placeholders}) AND station_code LIKE ?
                AND variable = 'precipitation_forecast_daily_mm'""",
            (*_FORECAST16D_SOURCE_IDS, f"{point_id}:%"),
        ).fetchall()
    except Exception:  # pragma: no cover - defensive, optional cache only
        return {}
    out: dict = {}
    for station_code, observed_at_utc, value in rows:
        if value is None or not observed_at_utc:
            continue
        try:
            model = station_code.split(":", 1)[1]
        except IndexError:
            continue
        date_str = observed_at_utc[:10]  # Bangkok-midnight-as-UTC-instant -> the date
        out.setdefault(model, {})[date_str] = float(value)
    return out


def _point_forecast_range(daily_by_model: dict, now_local, n_days: int) -> dict | None:
    """Turns `_load_point_forecast_daily()`'s {model: {date: mm}} into the same
    {"min_mm","max_mm","median_mm","n_models","per_model"} shape the file-based readers
    below produce -- `n_days=1` sums only the earliest available date (tomorrow),
    `n_days=7` sums the earliest 7 available dates present for that model (a model with
    fewer than 7 real days left just totals what it actually has, never padded with 0s)."""
    if not daily_by_model:
        return None
    per_model_total = {}
    for model, by_date in daily_by_model.items():
        dates = sorted(by_date)
        if not dates:
            continue
        window = dates[:n_days]
        per_model_total[model] = round(sum(by_date[d] for d in window), 1)
    if not per_model_total:
        return None
    vals = sorted(per_model_total.values())
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return {"min_mm": vals[0], "max_mm": vals[-1], "median_mm": round(median, 1),
            "n_models": n, "per_model": per_model_total}


def _layer0_forecast_24h_range_for_point(conn, point_id: str, now_local) -> dict | None:
    """Prefers the real per-point DB rows (Commit 3, all 8 points); falls back to the
    original Sammakorn-only hourly-file reader (`_layer0_forecast_24h_range()`) only for
    `point_id == "sammakorn"` when the DB has nothing yet -- so a fresh checkout with no
    `collect.py --all` run behind it still shows the pre-Commit-3 numbers rather than
    nothing."""
    db_daily = _load_point_forecast_daily(conn, point_id)
    range_ = _point_forecast_range(db_daily, now_local, n_days=1)
    if range_ is not None:
        return range_
    if point_id == "sammakorn":
        return _layer0_forecast_24h_range(now_local)
    return None


def _layer0_forecast_7day_range_for_point(conn, point_id: str, now_local) -> dict | None:
    """7-day counterpart of `_layer0_forecast_24h_range_for_point()` -- same DB-first,
    Sammakorn-file-fallback posture."""
    db_daily = _load_point_forecast_daily(conn, point_id)
    range_ = _point_forecast_range(db_daily, now_local, n_days=7)
    if range_ is not None:
        return range_
    if point_id == "sammakorn":
        return _layer0_forecast_7day_range(now_local)
    return None


def area_forecast_72h_worst(conn, point_id: str, now_local) -> dict | None:
    """Independent-verifier follow-up (2026-09-28): the four-driver hero tile's ฝน
    figure is NOT a PROP-FLOOD-06 quantity (that tier engine is sammakorn-only by
    design, see tools/backtest/compute_prop_flood_06_sammakorn.py) -- it must work for
    ANY area that has per-model forecast rows in the DB, which `collect.py` already
    populates for both points (verified: `ram53:cma_grapes_global` etc. exist in
    data/observations.sqlite exactly like `sammakorn:cma_grapes_global`). Reuses the
    SAME `_load_point_forecast_daily()` + `_point_forecast_range()` this module's
    24h/7-day per-point readers already call, just with `n_days=3` (72h) -- no new
    equation, the worst-model selection is the same one-line max() already used by
    `_l0_public_forecast_items()` above and by `compute_prop_flood_06_sammakorn.py`.
    Returns {"value_mm", "model_id", "model_th"} or None (never fabricates a value) when
    this point has no per-model forecast rows in the DB this run."""
    db_daily = _load_point_forecast_daily(conn, point_id)
    range_ = _point_forecast_range(db_daily, now_local, n_days=3)
    if not range_ or not range_.get("per_model"):
        return None
    per_model = range_["per_model"]
    worst_model = max(per_model, key=per_model.get)
    return {
        "value_mm": per_model[worst_model],
        "model_id": worst_model,
        "model_th": _L0_MODEL_LABELS_TH.get(worst_model, worst_model),
    }


def _layer0_forecast_7day_range(now_local) -> dict | None:
    """Per-MODEL next-7-day (168h) rain totals -- same shape/posture as
    `_layer0_forecast_24h_range()` above but a 7-day window, so the public block can show
    each named model's own 7-day total next to its tomorrow-only (24h) number. Founder
    ruling (verbatim, relayed): never collapse multiple models into one averaged/median
    headline -- name each model, report its own number, then a count-based scenario band
    (see `_l0_scenario_band()`). This is the ORIGINAL Sammakorn-only file-based reader --
    kept as the fallback `_layer0_forecast_7day_range_for_point()` uses when the DB has no
    rows yet for a point (e.g. a checkout with no `collect.py --all` run behind it)."""
    now_floor = now_local.replace(minute=0, second=0, microsecond=0)
    window_end = now_floor + datetime.timedelta(hours=24 * 7)
    per_model_total = {}
    for model in FORECAST_MODELS:
        path = FORECAST_DIR / f"openmeteo_{model}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if parsers is None:
            continue
        try:
            rows = parsers.parse_openmeteo_forecast(data)
        except Exception:  # pragma: no cover - defensive
            continue
        total = 0.0
        found_any = False
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M").replace(
                    tzinfo=BANGKOK_TZ)
            except ValueError:
                continue
            if now_floor <= local_dt < window_end:
                total += r["mm"] or 0.0
                found_any = True
        if found_any:
            per_model_total[model] = round(total, 1)
    if not per_model_total:
        return None
    vals = sorted(per_model_total.values())
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return {"min_mm": vals[0], "max_mm": vals[-1], "median_mm": round(median, 1),
            "n_models": n, "per_model": per_model_total}


_L0_MODEL_LABELS_TH = dict(zip(FORECAST_MODELS, _MULTIMODEL_NAMES_TH))
# Commit 3 (2026-09-27): the DB-backed per-point loader (`_load_point_forecast_daily()`)
# can return any of the 9 openmeteo_forecast16d models + metno -- not just the original 6
# FORECAST_MODELS this dict covered before. Extended here so a scenario line (worst/best
# case) always shows a real model NAME, never a raw internal model code.
_L0_MODEL_LABELS_TH.update({
    "ukmo_seamless": "UKMO", "knmi_seamless": "KNMI", "cma_grapes_global": "CMA",
    "metno": "MET Norway",
})


def _l0_scenario_band(values: list) -> tuple:
    """Minimum-width window covering a strict MAJORITY (>50%) of the given values --
    e.g. 6 models, majority=4, returns the tightest [A, B] that contains at least 4 of
    the 6 -- a COUNT-based band, never a mean/median headline. Returns
    (band_lo, band_hi, k, n); (0.0, 0.0, 0, 0) for an empty input."""
    vals = sorted(values)
    n = len(vals)
    if n == 0:
        return (0.0, 0.0, 0, 0)
    k = min(n // 2 + 1, n)  # strict majority
    best_lo, best_hi = vals[0], vals[-1]
    best_width = best_hi - best_lo
    for i in range(0, n - k + 1):
        lo, hi = vals[i], vals[i + k - 1]
        width = hi - lo
        if width < best_width:
            best_width = width
            best_lo, best_hi = lo, hi
    return (round(best_lo, 1), round(best_hi, 1), k, n)


def _layer0_rain_observed_reading(rain: dict | None, layer0mod_):
    if not rain or rain.get("mm_24h") is None:
        return None
    return layer0mod_.Reading(
        value=float(rain["mm_24h"]), unit="mm/24h", tag="MEASURED",
        source=f"thaiwater_rain_24h ({rain.get('station') or 'สถานีใกล้สุด'})",
        observed_at=rain.get("observed_at"), note=f"ห่าง {rain.get('dist_km')} กม.")


def _layer0_pumping_reading(pumps_on_total: int, layer0mod_, generated_at_utc_iso: str):
    return layer0mod_.Reading(
        value=float(pumps_on_total), unit="เครื่อง (ของ 4, ST.SPS.01-04)", tag="MEASURED",
        source="site/build_data.py build_pumps() รอบนี้ (bma_pumphistory)",
        observed_at=generated_at_utc_iso)


def build_layer0_readouts(*, sammakorn: dict, ram53: dict, generated_at_utc_iso: str,
                           now_local, sammakorn_chain_readout_result: dict | None) -> dict | None:
    """Returns render_layer0_block()'s dict (title/units/generated_note) or None if
    tools/layer0 failed to import (defensive -- must never break the live build)."""
    if layer0mod is None:
        return None

    median_24h, max_24h, n_models = _layer0_ensemble_rain_24h(now_local)
    rain_fc = None
    if median_24h is not None:
        rain_fc = layer0mod.Reading(
            value=median_24h, unit="mm/24h", tag="RELAYED",
            source=f"Open-Meteo multimodel median across {n_models} models (จุดสัมมากร, proxy โซนตะวันออก)",
            note=f"max ในกลุ่มเดียวกัน {max_24h} mm/24h")

    sammakorn_pump_rows = sammakorn.get("pumps") or []
    sammakorn_pumps_on_total = sum(
        (r.get("pumps_on") or 0) for r in sammakorn_pump_rows
        if str(r.get("code") or "").startswith("ST.SPS"))
    # sammakorn_chain_readout()'s own community_backflow_evidence rows are dicts
    # (soi/time_th/text_th/tag/source, no personal names -- see SAMMAKORN_COMMUNITY_
    # BACKFLOW_EVIDENCE above); compute_backflow_state()/BackflowState.render() expect
    # a list of short STRINGS (its own docstring's worked example), so each dict is
    # formatted into one line here, not passed through as a raw dict.
    community_evidence_raw = (sammakorn_chain_readout_result or {}).get("community_backflow_evidence") or []
    community_evidence = [
        f"{e.get('soi', '')}: \"{e.get('text_th', '')}\" {e.get('time_th', '')}".strip()
        for e in community_evidence_raw
    ] or None

    bangkok_east_live = {}
    rain_obs_bkk = _layer0_rain_observed_reading(sammakorn.get("rain"), layer0mod)
    if rain_obs_bkk is not None:
        bangkok_east_live["rain_observed_24h"] = rain_obs_bkk
    if rain_fc is not None:
        bangkok_east_live["rain_forecast_24h_median"] = rain_fc

    sammakorn_live = {}
    rain_obs_smk = _layer0_rain_observed_reading(sammakorn.get("rain"), layer0mod)
    if rain_obs_smk is not None:
        sammakorn_live["rain_observed_24h"] = rain_obs_smk
    sammakorn_live["pumping_running"] = _layer0_pumping_reading(
        sammakorn_pumps_on_total, layer0mod, generated_at_utc_iso)
    sammakorn_live["backflow_state"] = layer0mod.compute_backflow_state(
        community_evidence=community_evidence)

    ram53_live = {}
    rain_obs_ram53 = _layer0_rain_observed_reading(ram53.get("rain"), layer0mod)
    if rain_obs_ram53 is not None:
        ram53_live["rain_observed_24h"] = rain_obs_ram53

    try:
        readouts = [
            layer0mod.build_bangkok_east(live=bangkok_east_live),
            layer0mod.build_sammakorn(live=sammakorn_live),
            layer0mod.build_ram53(live=ram53_live),
        ]
        return _render_layer0_block(readouts)
    except Exception:  # pragma: no cover - defensive, LAYER 0 must never break the build
        return None


# --- LAYER 0 public rendering (Thai-only, no field names/jargon on the page) -----------
# `build_layer0_readouts()` above returns tools/layer0's own internal analytical block
# (English field-name jargon in its REFUSED reasons, e.g. "gravity_headroom ... ยังไม่ได้
# wire" -- fine for data.json/tests, never fine for the rendered page). This section
# builds a SEPARATE, independently-worded public block straight from this build's own
# raw values (never reusing a Reading's `.source`/`.note` text), so the public page can
# never leak an internal field name or the word "wire" -- see build_page.py's
# build_layer0_top_html(), which renders ONLY this block, never the internal one above.

_L0_TAG_TH = {
    "VERIFIED": "ยืนยันแล้ว", "MEASURED": "วัดจากไฟล์ข้อมูล",
    "MEASURED-community": "รายงานจากชุมชน", "MEASURED-history": "วัดจากประวัติ",
    "RELAYED": "ข่าว/บุคคลที่สาม", "INSTINCT": "ประเมินจากบริบท",
    "OPEN": "ยังไม่มีคำตอบ", "PROPOSAL-derived": "คำนวณจากสูตรที่เสนอ",
}
_L0_UNIT_TH = {"mm/24h": "มม./24 ชม.", "m3/s": "ลบ.ม./วิ", "m": "ม.", "mm": "มม."}


def _l0_tag_pill(tag: str | None) -> str:
    return _L0_TAG_TH.get(tag, "ยังไม่มีคำตอบ")


def _l0_public_item(label_th: str, reading, missing_text_th: str) -> dict:
    """Turns one tools.layer0 Reading into a public {label_th, text_th, tag_th} dict --
    NEVER touches Reading.source/.note (that is where internal field-name jargon like
    "gravity_headroom"/"wire" lives) -- only .value/.unit/.tag, plus a caller-supplied,
    hand-written Thai sentence for the missing case."""
    if reading is None or getattr(reading, "missing", True):
        return {"label_th": label_th, "text_th": f"ยังไม่มีข้อมูล: {missing_text_th}", "tag_th": _l0_tag_pill("OPEN")}
    val = reading.value
    shown = f"{val:.1f}" if isinstance(val, float) else str(val)
    unit_th = _L0_UNIT_TH.get(reading.unit, reading.unit)
    return {"label_th": label_th, "text_th": f"{shown} {unit_th}".strip(), "tag_th": _l0_tag_pill(reading.tag)}


def _l0_public_backflow_item(bf) -> dict:
    state_text = {
        "active": "มีการไหลย้อนจากคลอง", "not_active": "ไม่มีการไหลย้อนจากคลอง",
        "likely": "น่าจะมีการไหลย้อนจากคลอง (ยังไม่ยืนยันด้วยระดับน้ำ)",
    }
    if bf is None or bf.state == "unknown":
        return {"label_th": "น้ำย้อนจากคลอง", "text_th": "ยังไม่มีข้อมูล: ทางน้ำย้อนจากคลอง",
                "tag_th": _l0_tag_pill("OPEN")}
    return {"label_th": "น้ำย้อนจากคลอง", "text_th": state_text.get(bf.state, "ยังไม่มีข้อมูล: ทางน้ำย้อนจากคลอง"),
            "tag_th": _l0_tag_pill(bf.tag)}


def _l0_public_forecast_items(fc_range24: dict | None, fc_range7: dict | None) -> list:
    """Project decision (verbatim, relayed 2026-09-27): "อาจต้องห้ามเฉลี่ยแบบนั้น แต่ให้แยกเลยว่า
    โมเดลนี้ว่าไง โมเดลนี้ว่าไง แล้วทำเป็นเซนารีโอ worst case" -- never collapse the named
    models into one averaged headline number. Returns a LIST of public
    {label_th, text_th, tag_th, ...} items (spliced straight into an area's `in_items` by
    the caller): one row per named model (tomorrow's 24h total + its own 7-day total), one
    placeholder row for the real GFS-ENS member spread (p10-p90 -- not wired into this
    build yet, see docs/knowledge/FORECAST_7DAY_SOURCES.md ss5, tagged OPEN not fabricated),
    then SCENARIOS -- worst case first, best case, and a count-based majority band -- plus
    the model-disagreement flag and a fixed grid-cell-vs-point caveat. Never a single
    dict, never a mean/median headline (see `_l0_scenario_band()`)."""
    items = []
    if not fc_range24:
        items.append({"label_th": "ฝนพยากรณ์ (รายโมเดล)",
                       "text_th": "ยังไม่มีข้อมูล: ฝนพยากรณ์ล่วงหน้า", "tag_th": _l0_tag_pill("OPEN")})
        return items

    per_model24 = fc_range24.get("per_model") or {}
    per_model7 = (fc_range7 or {}).get("per_model") or {}
    # Render EVERY model this run actually has a value for (Commit 3: up to 9 named
    # deterministic models + metno via the DB-backed per-point loader, not just the
    # original 6 FORECAST_MODELS) -- known models first, in a stable declared order,
    # then any future/unrecognised model id appended alphabetically so a new source
    # never silently disappears from the page.
    known_order = list(FORECAST_MODELS) + ["ukmo_seamless", "knmi_seamless",
                                            "cma_grapes_global", "metno"]
    render_order = [m for m in known_order if m in per_model24]
    render_order += sorted(m for m in per_model24 if m not in known_order)
    for model in render_order:
        v24 = per_model24.get(model)
        if v24 is None:
            continue
        v7 = per_model7.get(model)
        label = _L0_MODEL_LABELS_TH.get(model, model)
        text = f"พรุ่งนี้ {v24:.0f} มม." + (f" · รวม 7 วัน {v7:.0f} มม." if v7 is not None else "")
        items.append({"label_th": label, "text_th": text, "tag_th": _l0_tag_pill("RELAYED")})

    # ensemble row -- spread of MEMBERS within one model (GFS-ENS 31 members), a
    # genuinely different signal from the multi-model spread above -- not a mean, real
    # per-member data not connected to this build yet (draft parser only, see
    # docs/knowledge/FORECAST_7DAY_SOURCES.md ss1/ss5) -- OPEN placeholder, never fabricated.
    items.append({"label_th": "สมาชิกโมเดลเดียว (ensemble p10-p90)",
                   "text_th": "ยังไม่มีข้อมูล: ยังไม่เชื่อมข้อมูลสมาชิกโมเดลจริงในระบบนี้",
                   "tag_th": _l0_tag_pill("OPEN")})

    vals24 = sorted(per_model24.values())
    if vals24:
        worst_model = max(per_model24, key=lambda m: per_model24[m])
        best_model = min(per_model24, key=lambda m: per_model24[m])
        worst_v, best_v = per_model24[worst_model], per_model24[best_model]
        band_lo, band_hi, k, n = _l0_scenario_band(vals24)
        disagree = spread_disagreement(max(vals24), min(vals24))
        items.append({"label_th": "กรณีแย่สุด",
                       "text_th": f"{_L0_MODEL_LABELS_TH.get(worst_model, worst_model)} {worst_v:.0f} มม.",
                       "tag_th": _l0_tag_pill("RELAYED")})
        items.append({"label_th": "กรณีดีสุด",
                       "text_th": f"{_L0_MODEL_LABELS_TH.get(best_model, best_model)} {best_v:.0f} มม.",
                       "tag_th": _l0_tag_pill("RELAYED")})
        items.append({"label_th": "โมเดลส่วนใหญ่",
                       "text_th": f"{k} จาก {n} โมเดล อยู่ที่ {band_lo:.0f}–{band_hi:.0f} มม.",
                       "tag_th": _l0_tag_pill("RELAYED"),
                       "spread_flag_th": "โมเดลไม่ตรงกัน" if disagree else None})

    items.append({
        "label_th": "หมายเหตุค่าโมเดล",
        "text_th": ("ค่าโมเดล = ฝนต่อพื้นที่ช่องตาราง ~10–25 กม. รอบจุด ไม่ใช่จุดเดียว — "
                    "26 ก.ย. โมเดลให้ 13–53 มม. แต่สถานี สนข.สะพานสูง วัดได้ 203 "
                    "(ตัวเลข 203 ยังไม่ยืนยันแหล่ง/สถานี/ช่วงเวลาให้ตรงกันในระบบนี้)"),
        "tag_th": _l0_tag_pill("OPEN"),
    })
    return items


def _l0_public_capacity(cap: dict) -> list[dict]:
    items = []
    if cap.get("design") is not None:
        items.append(_l0_public_item("ออกแบบรับได้", cap["design"], "ค่าออกแบบ"))
    items.append(_l0_public_item("เคยท่วมที่", cap["flooded_min"], "เคยท่วมที่เท่าไหร่"))
    items.append(_l0_public_item("เคยรับได้ถึง", cap["coped_max"],
                                  "เคยรับได้ถึงเท่าไหร่ (ไม่เคยพบวันฝนแรงที่ไม่ท่วมในคลังข้อมูลนี้)"))
    return items


_L0_IN_VS_CAP_TH = {"เกิน": "เกินความสามารถรับมือ", "ใกล้ (>=80%)": "ใกล้ความสามารถรับมือ (≥80%)",
                     "ไม่เกิน": "ยังไม่เกินความสามารถรับมือ", "ไม่รู้ (ขาด: น้ำเข้า)": "ยังไม่มีคำตอบ (ไม่มีค่าน้ำเข้า)",
                     "ไม่รู้ (ขาด: ความสามารถรับมือ)": "ยังไม่มีคำตอบ (ไม่มีค่าความสามารถรับมือ)",
                     "ไม่รู้": "ยังไม่มีคำตอบ"}
# Finding: `_in_vs_capacity`'s own new "ขาด: เคยรับได้ถึง" string (see
# tools/layer0/in_out_capacity.py) needs its own mapped sentence too -- without this entry
# it would silently fall through to the generic "ยังไม่มีคำตอบ" default below, which is
# honest but throws away the specific reason. Match built with .startswith in
# `_l0_in_vs_capacity_th` (helper added alongside this dict) since the upstream string
# also carries the live threshold/coped_max values inline, not a fixed key.
_L0_IN_VS_CAP_UNKNOWN_COPED_MAX_PREFIX = "ไม่รู้ (ขาด: เคยรับได้ถึง"
_L0_IN_VS_CAP_UNKNOWN_COPED_MAX_TH = (
    "ยังไม่เกินเกณฑ์เคยท่วม แต่ยังไม่มีคำตอบว่าเกินความสามารถรับมือหรือไม่ "
    "(ไม่มีเกณฑ์ \"เคยรับได้ถึง\" ยืนยัน -- เกณฑ์เคยท่วมอย่างเดียวบอกได้แค่ว่า \"เกิน\" ไม่ได้บอกว่า \"ไม่เกิน\")"
)


def _l0_in_vs_capacity_th(raw_verdict: str) -> str:
    """Wraps `_L0_IN_VS_CAP_TH.get(...)` with one prefix-matched case (see the constant
    above) -- never returns the generic "ยังไม่มีคำตอบ" for the specific "no coped_max"
    reason when a more honest sentence is available."""
    if raw_verdict.startswith(_L0_IN_VS_CAP_UNKNOWN_COPED_MAX_PREFIX):
        return _L0_IN_VS_CAP_UNKNOWN_COPED_MAX_TH
    return _L0_IN_VS_CAP_TH.get(raw_verdict, "ยังไม่มีคำตอบ")


_L0_OUT_VS_IN_TH = {"ระบายทัน": "ระบายทัน", "ไม่ทัน": "ระบายไม่ทัน", "ไม่รู้": "ยังไม่มีคำตอบ"}


def _l0_forecast_verdict_th(fc_range24: dict | None, area_key: str, cap: dict, layer0mod_) -> str | None:
    """Project decision (verbatim, relayed): the forecast-side verdict is computed on the
    WORST-CASE model value FIRST (never an average/median), with the count-based
    majority band shown beside it -- e.g. "เกินความสามารถรับมือ (คิดจากกรณีแย่สุด —
    โมเดลส่วนใหญ่ 4/6: 30-45 มม.)". Returns None when there is no per-model data this run
    (never fabricates a verdict from nothing)."""
    per_model = (fc_range24 or {}).get("per_model") or {}
    if not per_model:
        return None
    worst_v = max(per_model.values())
    worst_reading = layer0mod_.Reading(value=worst_v, unit="mm/24h", tag="RELAYED",
                                        source="กรณีแย่สุดจากโมเดลพยากรณ์รายวัน (ดูรายการต่อโมเดลด้านบน)")
    verdict = _l0_in_vs_capacity_th(
        layer0mod_.render_unit(area_key, "x", {}, {}, cap, primary_in=worst_reading).in_vs_capacity)
    band_lo, band_hi, k, n = _l0_scenario_band(sorted(per_model.values()))
    return f"{verdict} (คิดจากกรณีแย่สุด — โมเดลส่วนใหญ่ {k}/{n}: {band_lo:.0f}–{band_hi:.0f} มม.)"


def _build_sammakorn_prop_flood_06(conn) -> dict | None:
    """Calls tools/backtest/compute_prop_flood_06_sammakorn.compute_and_write() (which
    itself calls the EXISTING PROP-FLOOD-06 v5 engine, never a new formula -- Toledo
    reuse-pipeline discipline) for the "sammakorn" unit, writes the inseparable readout
    record to raw/tier_runs/sammakorn_<UTC>.json (append-only, gitignored raw/ -- never
    overwrites a prior run), and returns a Thai-only, resident-facing dict for the public
    page. Returns None if the compute module failed to import or the run itself raises
    (defensive -- LAYER 0 must never break the build, same posture as every other
    LAYER-0-adjacent function in this file)."""
    if pf06mod is None:
        return None
    try:
        record, path = pf06mod.compute_and_write(conn=conn)
    except Exception:  # pragma: no cover - defensive
        return None

    tier = record["tier"]
    n_present = record["coverage_present_n"]
    n_absent = record["coverage_absent_n"]
    n_total = record["coverage_total_n"]
    # task 3 (FOUNDER_TASKS_2026-09-27.md #38): forecast_rain_72h is reported as
    # "inferred" (a forecast, not a direct measurement), separate from the engine's own
    # present/absent truth -- see compute_prop_flood_06_sammakorn.compute()'s docstring.
    n_measured = record.get("coverage_measured_n", n_present)
    n_inferred = record.get("coverage_inferred_n", 0)
    missing_th = ", ".join(pf06mod.component_label_th(k) for k in record["missing"]) or "ไม่มี"

    # T_act (เวลาก่อนถึงเกณฑ์) is only reportable in FULL mode (this unit is PARTIAL --
    # A_U/R_H genuinely OPEN, see sources/backtest_units.yaml's own SAMMAKORN notes) --
    # never fabricate an hours-remaining figure from a PARTIAL-mode promoter floor.
    if record["mode"] == "FULL" and record.get("lead_time_h") is not None:
        time_text_th = f"รับมือได้อีก ~{record['lead_time_h']:.1f} ชม."
    else:
        time_text_th = f"ยังคำนวณเวลาไม่ได้ — ขาด: {missing_th}"

    # task 3: per-model 72h forecast list, WORST (highest total) FIRST -- never an
    # averaged/median headline, every named model's own value shown (founder rule).
    fc72_prov = (record.get("input_provenance") or {}).get("forecast_rain_72h_mm") or {}
    per_model_72h = fc72_prov.get("per_model_mm") or {}
    forecast_72h_items_th = [
        f"{_L0_MODEL_LABELS_TH.get(model, model)}: {mm:.1f} มม."
        for model, mm in sorted(per_model_72h.items(), key=lambda kv: kv[1], reverse=True)
    ]
    forecast_72h_worst_text_th = (
        f"ฝนพยากรณ์ 72 ชม. (กรณีแย่สุด): {fc72_prov.get('worst_value_mm'):.1f} มม. "
        f"({_L0_MODEL_LABELS_TH.get(fc72_prov.get('worst_model'), fc72_prov.get('worst_model'))})"
        if fc72_prov.get("worst_value_mm") is not None else None
    )
    # an earlier check mobile verifier finding B1 (2026-09-28, second pass): the same worst-value/
    # model this text sentence already reports, exposed as their own fields so a
    # first-screen picture tile can show a big bold NUMBER + short label instead of
    # having to re-parse the Thai sentence -- no new computation, same worst_value_mm/
    # worst_model this function already selected above.
    forecast_72h_worst_value_mm = fc72_prov.get("worst_value_mm")
    forecast_72h_worst_model_th = (
        _L0_MODEL_LABELS_TH.get(fc72_prov.get("worst_model"), fc72_prov.get("worst_model"))
        if fc72_prov.get("worst_value_mm") is not None else None
    )

    # Finding: L0 ("ปกติ"/green) shown unqualified in PARTIAL mode
    # (thin coverage, e.g. 2/10 inputs, 0/4 pumps reporting) reads as "confirmed normal"
    # rather than "not enough measured to say otherwise" (UNKNOWN != SAFE) -- this is the
    # exact field the committed site/dist/api/v1 snapshot shipped to AI readers. Never
    # touches the registered tier/promoter engine (`tier` itself, `record["mode"]`) --
    # only the word/colour this function exposes for an L0+PARTIAL combination.
    if record["mode"] == "PARTIAL" and tier == "L0":
        tier_word_th_out = "ข้อมูลไม่พอจะบอกว่าปกติ"
        tier_color_out = "#757575"
    else:
        tier_word_th_out = pf06mod.tier_word_th(tier)
        tier_color_out = pf06mod.tier_color(tier)

    return {
        "tier": tier,
        "tier_word_th": tier_word_th_out,
        "tier_color": tier_color_out,
        "mode": record["mode"],
        "coverage_text_th": f"ข้อมูลครบ {n_present}/{n_total} (วัดจริง {n_measured} · อนุมาน {n_inferred} · ขาด {n_absent})",
        "time_text_th": time_text_th,
        "pond_capacity_text_th": "บึงรับน้ำ 227,200 ลบ.ม. (แผน กทม. 2569 หน้า 74)",
        "promoters_fired_th": [record_id for record_id in record["promoters_fired"]],
        "engine_note_th": record.get("engine_note_th"),
        "forecast_72h_worst_text_th": forecast_72h_worst_text_th,
        "forecast_72h_worst_value_mm": forecast_72h_worst_value_mm,
        "forecast_72h_worst_model_th": forecast_72h_worst_model_th,
        "forecast_72h_items_th": forecast_72h_items_th,
        "tier_run_path": str(path.relative_to(FLOOD_KG)) if hasattr(path, "relative_to") else str(path),
    }


def build_layer0_public(*, sammakorn: dict, ram53: dict, generated_at_utc_iso: str,
                         now_local, sammakorn_chain_readout_result: dict | None) -> dict | None:
    """Public, Thai-only LAYER 0 block -- this is the one build_page.py's
    build_layer0_top_html() actually renders on the page. See module header above for why
    this is a separate function from build_layer0_readouts()."""
    if layer0mod is None:
        return None
    try:
        thresholds = layer0mod.load_coping_thresholds()
        # Commit 3 (2026-09-27): per-area forecast rows/scenarios now read from the
        # 8-point openmeteo_forecast16d/metno_locationforecast tables in
        # data/observations.sqlite (collect.FORECAST7D_POINTS) -- so bangkok_east/
        # sammakorn/ram53 each get THEIR OWN point's numbers, not all three sharing the
        # single old Sammakorn-hourly-file reading. Falls back to that old file-based
        # reading (Sammakorn only) when the DB has no rows for a point yet.
        forecast_conn = open_observations_db()
        fc_range24_bkk = _layer0_forecast_24h_range_for_point(forecast_conn, "bangkok_east", now_local)
        fc_range7_bkk = _layer0_forecast_7day_range_for_point(forecast_conn, "bangkok_east", now_local)
        fc_range24_smk = _layer0_forecast_24h_range_for_point(forecast_conn, "sammakorn", now_local)
        fc_range7_smk = _layer0_forecast_7day_range_for_point(forecast_conn, "sammakorn", now_local)
        fc_range24_ram = _layer0_forecast_24h_range_for_point(forecast_conn, "ram53", now_local)
        fc_range7_ram = _layer0_forecast_7day_range_for_point(forecast_conn, "ram53", now_local)
        # kept for the pre-Commit-3 REFUSED-DB posture (`fc_range24` still None/legacy
        # anywhere a caller has not been updated to a per-point variant).
        fc_range24 = fc_range24_bkk

        rain_obs_bkk = _layer0_rain_observed_reading(sammakorn.get("rain"), layer0mod)
        cap_bkk = layer0mod.capacity_band("bangkok_east", "rain_24h_mm", "mm/24h", thresholds)
        bkk_area = {
            "label_th": "กทม. ฝั่งตะวันออก",
            "in_items": [
                _l0_public_item("ฝนวัดจริง (24 ชม.)", rain_obs_bkk, "ฝนวัดจริง 24 ชม. ที่ผ่านมา"),
                *_l0_public_forecast_items(fc_range24_bkk, fc_range7_bkk),
            ],
            "out_items": [
                {"label_th": "ปั๊มที่วิ่งอยู่ (ฝั่งพระนคร)", "text_th": "1,200 ลบ.ม./วิ (เต็มกำลัง)",
                 "tag_th": _l0_tag_pill("RELAYED"),
                 "scope_note_th": "เฉพาะฝั่งพระนคร ไม่ใช่ตัวเลขรวมทั้งเมือง"},
                {"label_th": "ทางน้ำออกแบบไหลเอง", "text_th": "ยังไม่มีข้อมูล: ทางออกแบบไหลเอง",
                 "tag_th": _l0_tag_pill("OPEN")},
            ],
            "capacity_items": _l0_public_capacity(cap_bkk),
            "in_vs_capacity_th": _l0_in_vs_capacity_th(
                layer0mod.render_unit("bangkok_east", "x", {}, {}, cap_bkk,
                                       primary_in=rain_obs_bkk).in_vs_capacity),
            "forecast_verdict_th": _l0_forecast_verdict_th(fc_range24_bkk, "bangkok_east", cap_bkk, layer0mod),
            "out_vs_in_th": "ยังไม่มีคำตอบ",
            "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
        }

        rain_obs_smk = _layer0_rain_observed_reading(sammakorn.get("rain"), layer0mod)
        sammakorn_pump_rows = sammakorn.get("pumps") or []
        sps_rows = [r for r in sammakorn_pump_rows if str(r.get("code") or "").startswith("ST.SPS")]
        pumps_on = sum((r.get("pumps_on") or 0) for r in sps_rows)
        n_stations = len(sps_rows) or 4  # ST.SPS.01-04, per docs/ASSETS.md -- 4 if this
        # run found none of them (never show "0/0", which would misleadingly imply the
        # village has zero pump stations rather than zero DATA this run)
        n_fault_stations = sum(1 for r in sps_rows if r.get("status_th") == "ขัดข้อง")
        pump_text = (f"ขัดข้อง (กทม. รายงาน สาเหตุไม่ทราบ) — {n_fault_stations}/{n_stations} สถานี"
                     if n_fault_stations > 0 and pumps_on == 0
                     else f"{pumps_on} จาก {n_stations} สถานี กำลังเดินเครื่อง")
        any_fault = n_fault_stations > 0
        community_evidence_raw = (sammakorn_chain_readout_result or {}).get(
            "community_backflow_evidence") or []
        community_evidence = [
            f"{e.get('soi', '')}: \"{e.get('text_th', '')}\" {e.get('time_th', '')}".strip()
            for e in community_evidence_raw
        ] or None
        bf = layer0mod.compute_backflow_state(community_evidence=community_evidence)
        cap_smk = layer0mod.capacity_band("sammakorn", "rain_24h_mm", "mm/24h", thresholds)
        pond_capacity_item = {
            "label_th": "บึงรับน้ำ (ปริมาตรเก็บกัก)",
            "text_th": "227,200 ลบ.ม.",
            "tag_th": _l0_tag_pill("VERIFIED"),
            "scope_note_th": "แผน กทม. 2569 ภาคผนวก ก หน้า 74 (บึงรับน้ำหมู่บ้านสัมมากร)",
        }
        prop_flood_06 = _build_sammakorn_prop_flood_06(forecast_conn)
        smk_area = {
            "label_th": "สัมมากร",
            "in_items": [
                _l0_public_item("ฝนวัดจริง (24 ชม.)", rain_obs_smk, "ฝนวัดจริง 24 ชม. ที่ผ่านมา"),
                _l0_public_backflow_item(bf),
                *_l0_public_forecast_items(fc_range24_smk, fc_range7_smk),
            ],
            "out_items": [
                {"label_th": "ปั๊มหมู่บ้าน", "text_th": pump_text,
                 "tag_th": _l0_tag_pill("MEASURED")},
                {"label_th": "ทางน้ำออกเมื่อบึงสูงกว่าคลอง", "text_th": "ยังไม่มีข้อมูล: ทางออกแบบไหลเอง",
                 "tag_th": _l0_tag_pill("OPEN")},
            ],
            "capacity_items": _l0_public_capacity(cap_smk) + [pond_capacity_item],
            "in_vs_capacity_th": _l0_in_vs_capacity_th(
                layer0mod.render_unit("sammakorn", "x", {}, {}, cap_smk,
                                       primary_in=rain_obs_smk).in_vs_capacity),
            "forecast_verdict_th": _l0_forecast_verdict_th(fc_range24, "sammakorn", cap_smk, layer0mod),
            "out_vs_in_th": "ระบายไม่ทัน" if (any_fault and pumps_on == 0) else "ยังไม่มีคำตอบ",
            "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
            "prop_flood_06": prop_flood_06,
        }

        rain_obs_ram53 = _layer0_rain_observed_reading(ram53.get("rain"), layer0mod)
        ram53_area = {
            "label_th": "รามคำแหง 53",
            "in_items": [
                _l0_public_item("ฝนวัดจริง (24 ชม.)", rain_obs_ram53, "ฝนวัดจริง 24 ชม. ที่ผ่านมา"),
            ],
            "out_items": [
                {"label_th": "ปั๊มที่วิ่งอยู่", "text_th": "ยังไม่มีข้อมูล: ปั๊มที่วิ่งอยู่",
                 "tag_th": _l0_tag_pill("OPEN")},
            ],
            "capacity_items": _l0_public_capacity(cap_bkk),
            "capacity_note_th": "ยืมข้อมูลรับมือจากโซนตะวันออก — ยังไม่มีประวัติเฉพาะรามคำแหง 53",
            "in_vs_capacity_th": _l0_in_vs_capacity_th(
                layer0mod.render_unit("ram53", "x", {}, {}, cap_bkk,
                                       primary_in=rain_obs_ram53).in_vs_capacity),
            "out_vs_in_th": "ยังไม่มีคำตอบ",
            "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
        }

        return {
            "title_th": "สรุปสั้น — น้ำเข้า · น้ำออก · รับมือได้",
            "areas": {"bangkok_east": bkk_area, "sammakorn": smk_area, "ram53": ram53_area},
        }
    except Exception:  # pragma: no cover - defensive, LAYER 0 must never break the build
        return None


# --- Burden ledger (Toledo PROP-FLOOD-05a/05b, proposals, PR #62 not yet merged) --------

THAIWATER_BMA_DIR = RAW / "live" / "thaiwater_bma"
BURDEN_EPS = "0.02"  # per-gauge resolution, matches control_structures.yaml declaration


def load_control_structures_yaml() -> dict:
    """Load site/inputs/canals/control_structures.yaml. Returns {} (never raises) if
    PyYAML is unavailable or the file is missing/unparseable -- same posture as
    load_canal_graph_yaml()."""
    path = CANALS_DIR / "control_structures.yaml"
    if not HAVE_YAML or not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # pragma: no cover - defensive, malformed yaml never crashes the build
        return {}


def _latest_measured_gate_state(conn, water_code: str) -> dict | None:
    """Look up the most recent `bma_watermap` gate_opening_m reading(s) for this
    control-structure's own `canal_oldcode` -- `bma_watermap`'s `water_code` uses the
    SAME 'WL.xxx.NN' scheme (confirmed in docs/knowledge/BMA_WATER_MAP_PROBE.md), so
    `canal_oldcode` doubles as the join key with no cross-walk needed. `collect.py`'s
    `collect_bma_watermap()` stores each gate reading under station_code
    '<water_code>#gate<NN>' (to avoid an identity-index collision when a structure has
    more than one gate at the same timestamp -- see that function's own docstring), so
    this looks up by a LIKE prefix, not an exact station_code match.

    Returns {"is_open": bool, "gates_m": {gate_index: height_m}, "observed_at": iso} when
    at least one gate reading exists for this water_code, else None (no MEASURED source
    for this structure yet -- callers must fall back to the existing inference, never
    guess). `is_open` is True iff ANY known gate for this structure reads > 0 m (a
    single closed gate among several open ones still lets water through the structure
    as a whole; a structure is CLOSED only when every known gate reads 0)."""
    if conn is None or not water_code:
        return None
    try:
        rows = conn.execute(
            "SELECT station_code, value, observed_at_utc FROM observations "
            "WHERE source_id='bma_watermap' AND variable='gate_opening_m' "
            "AND station_code LIKE ? ORDER BY observed_at_utc DESC",
            (f"{water_code}#gate%",),
        ).fetchall()
    except sqlite3.Error:  # pragma: no cover - defensive, a query error degrades to "no reading"
        return None
    if not rows:
        return None
    # plain-tuple rows (this connection sets no row_factory, same as previous_reading()
    # above) -- (station_code, value, observed_at_utc), positional, not dict-style.
    latest_ts = rows[0][2]
    gates_m = {}
    for station_code, value, observed_at_utc in rows:
        if observed_at_utc != latest_ts:
            continue  # only the latest tick's own gate set, never mixed with an older one
        m = re.search(r"#gate(\d+)$", station_code or "")
        if m and value is not None:
            gates_m[int(m.group(1))] = value
    if not gates_m:
        return None
    return {"is_open": any(v > 0 for v in gates_m.values()), "gates_m": gates_m,
            "observed_at": latest_ts}


def _burden_declared_state(sdef: dict, reading: dict | None, eps_sum,
                            measured_gate: dict | None = None) -> tuple:
    """Derive g_c(t), returning (state, basis_th). `basis_th` is "วัดจริง" (measured) when
    a MEASURED `bma_watermap` gate reading (`measured_gate`, see
    `_latest_measured_gate_state()`) is available for this structure -- CLOSED iff every
    known gate reads 0, else OPEN -- and "อนุมาน" (inferred) when this repo must fall
    back to the existing in/out-level inference rule below (per
    control_structures.yaml's own declared control_state_rule_th: CLOSED iff declared a
    gate AND out-in exceeds the combined resolution; PUMPING iff a declared pump station
    reports pumps_on>0 (not wired to any of today's 5 declared structures -- kept for a
    structure that later declares a pump_station_code); else OPEN iff the structure
    declares SOME control mechanism (is_gate or a pump code); else None/None (no
    declared control-state source at all -> CONTROL_STATE_MISSING, exactly pkn01's case
    today, no basis to report)."""
    if measured_gate is not None:
        state = blmod.STATE_OPEN if measured_gate["is_open"] else blmod.STATE_CLOSED
        return state, "วัดจริง"
    is_gate = bool(sdef.get("is_gate"))
    if is_gate and reading is not None:
        g_in, g_out = reading.get("level_m"), reading.get("canal_out")
        if g_in is not None and g_out not in (None, 0):
            if (blmod._q(g_out) - blmod._q(g_in)) > eps_sum:
                return blmod.STATE_CLOSED, "อนุมาน"
    # pump_station_code is declared but no pump telemetry source is wired for any of
    # today's 5 structures -- left as a documented no-op until one is.
    if is_gate or sdef.get("pump_station_code"):
        return blmod.STATE_OPEN, "อนุมาน"
    return None, None


def _burden_history_higher_sides(canal_oldcode: str, sdef: dict, eps_sum) -> list:
    """Replay every distinct tick in raw/live/thaiwater_bma/*.json (chronological,
    de-duplicated by canal_datetime) for one declared structure's own station code,
    returning [higher_side_or_None, ...] ending at the most recent snapshot -- the input
    persistence() needs. Only the SAME station's canal_value/canal_out pair is used
    (matching control_structures.yaml's own declaration that A/B come from one station's
    two fields, not two stations). Staleness is not applied to historical ticks (each
    snapshot's own timestamp already IS that tick's declared instant); only the CURRENT
    tick's readout (computed separately in build_burden_ledger_readout) checks staleness
    against `generated_at_utc_iso`."""
    if not canal_oldcode or blmod is None or not THAIWATER_BMA_DIR.is_dir():
        return []
    seen_ticks = {}
    for path in sorted(THAIWATER_BMA_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows = payload.get("data") if isinstance(payload, dict) else payload
        for rec in rows or []:
            station = rec.get("station") or {}
            code = station.get("canal_oldcode") or station.get("canal_code")
            if code != canal_oldcode:
                continue
            dt = rec.get("canal_datetime")
            if dt and dt not in seen_ticks:
                seen_ticks[dt] = (rec.get("canal_value"), rec.get("canal_out"))
            break
    history = []
    for dt in sorted(seen_ticks.keys()):
        g_in, g_out = seen_ticks[dt]
        state, _basis = _burden_declared_state(
            sdef, {"level_m": g_in, "canal_out": g_out}, eps_sum)
        result = blmod.structure_burden(canal_oldcode, g_in, g_out, BURDEN_EPS, BURDEN_EPS,
                                         state)
        history.append(result.higher_side if result.result == blmod.RESULT_DETERMINATE
                        else None)
    return history


def build_burden_ledger_readout(canal_by_code: dict, generated_at_utc_iso: str,
                                 obs_conn=None) -> dict:
    """Run Toledo PROP-FLOOD-05a's structure_burden()/persistence() over every declared
    structure in site/inputs/canals/control_structures.yaml, then PROP-FLOOD-05b's
    zone_order() over the declared zeta zone map. Runs ONCE per build (city/east-zone-
    wide, not per-area), same size-budget reasoning as build_canal_graph_readout().
    Returns {"available": False, ...} if the yaml or burden_ledger.py itself is
    unavailable, never a guessed/partial readout.

    `obs_conn` (build 4, 2026-09-27, optional -- defaults to None so every existing
    caller/test keeps its old inferred-only behaviour unchanged) is a read-only sqlite
    connection this function uses to prefer a MEASURED `bma_watermap` gate_opening_m
    reading over the in/out-level inference for any structure that has one -- see
    `_latest_measured_gate_state()`/`_burden_declared_state()`."""
    doc = load_control_structures_yaml()
    structures_def = (doc or {}).get("structures") or {}
    zones_def = (doc or {}).get("zones") or {}
    if not doc or blmod is None or not structures_def:
        return {"available": False,
                "reason": "control_structures.yaml or burden_ledger module unavailable"}

    eps_sum = blmod._q(BURDEN_EPS) * 2

    structure_rows = {}
    readouts_for_zone_order = {}
    for sid, sdef in structures_def.items():
        code = sdef.get("canal_oldcode")
        reading = canal_by_code.get(code) if code else None
        measured_gate = _latest_measured_gate_state(obs_conn, code)
        state, state_basis = _burden_declared_state(sdef, reading, eps_sum, measured_gate)

        # Founder rule (build 4, 2026-09-27, verbatim): "ระวังข้อมูลขัดแย้งด้วย" -- when a
        # MEASURED gate reading is available, `state` above already prefers it (rendered
        # as canonical), but the pre-existing level-difference INFERENCE must stay
        # VISIBLE, not deleted, when the two disagree. Recompute what the inference-only
        # rule would have said (measured_gate=None) purely for this comparison; a real
        # disagreement is logged as a `contradictions` row (never auto-resolved).
        inferred_state_if_no_measurement = None
        gate_state_contradiction = False
        if measured_gate is not None:
            inferred_state_if_no_measurement, _ = _burden_declared_state(
                sdef, reading, eps_sum, measured_gate=None)
            if (inferred_state_if_no_measurement is not None
                    and inferred_state_if_no_measurement != state):
                gate_state_contradiction = True
                if store is not None and obs_conn is not None:
                    store.insert_contradiction(
                        obs_conn, observed_at_utc=measured_gate["observed_at"],
                        topic=f"gate_state:{code}", source_a="bma_watermap_gate_opening_m",
                        value_a=state, observed_a_utc=measured_gate["observed_at"],
                        source_b="inferred_level_diff",
                        value_b=inferred_state_if_no_measurement,
                        observed_b_utc=(reading.get("observed_at") if reading else None),
                        note="measured gate state disagrees with the level-difference "
                             "inference -- the MEASURED reading is rendered as the "
                             "structure's canonical state; the inferred value is kept "
                             "here, visible, never deleted")

        g_in = reading.get("level_m") if reading else None
        g_out = reading.get("canal_out") if reading else None
        observed_at = reading.get("observed_at") if reading else None
        stale = is_stale(observed_at, generated_at_utc_iso) if reading else True

        result = blmod.structure_burden(
            sid, g_in, g_out, BURDEN_EPS, BURDEN_EPS, state,
            datum_a=sdef.get("datum_a"), datum_b=sdef.get("datum_b"),
            stale_a=stale, stale_b=stale)

        history = _burden_history_higher_sides(code, sdef, eps_sum)
        p_c = blmod.persistence(history)

        readouts_for_zone_order[sid] = (result, p_c)
        structure_rows[sid] = {
            "label_th": sdef.get("label_th"), "canal_oldcode": code,
            "side_a_label_th": sdef.get("side_a_label_th"),
            "side_b_label_th": sdef.get("side_b_label_th"),
            "state": state, "state_basis": state_basis, "result": result.result,
            "reason_codes": list(result.reason_codes),
            "higher_side": result.higher_side, "lower_side": result.lower_side,
            "burdened_side": result.burdened_side, "relieved_side": result.relieved_side,
            "a_c": str(result.a_c) if result.a_c is not None else None,
            "value_m": lwl.safe_float(g_in), "out_m": lwl.safe_float(g_out),
            "observed_at": observed_at, "stale": stale, "persistence": p_c,
            "measured_gates_m": (measured_gate or {}).get("gates_m"),
            "gate_state_contradiction": gate_state_contradiction,
            "inferred_state_if_no_measurement": inferred_state_if_no_measurement,
        }

    zones = {zid: {"boundaries": [
                (sid, side) for sid, sdef in structures_def.items()
                for side, zref in (sdef.get("zeta") or {}).items() if zref == zid
            ]} for zid in zones_def}
    ordering = blmod.zone_order(zones, readouts_for_zone_order)

    zones_out = {zid: zdef.get("label_th", zid) for zid, zdef in zones_def.items()}

    return {
        "available": True,
        "sensor_resolution_m": (doc.get("sensor_resolution_m") or {}).get("value"),
        "stale_after_hours": doc.get("stale_after_hours"),
        "control_state_rule_th": (doc.get("control_state_rule_th") or "").strip(),
        "structures": structure_rows,
        "zones": zones_out,
        "zone_order": ordering,
        "next_step_th": (doc.get("next_step_th") or "").strip(),
    }


# --- Area builder ---------------------------------------------------------------------

def build_area_data(*, area_id: str, label: str, centre_lat: float, centre_lon: float,
                     generated_at_bkk: str, generated_at_utc_iso: str, now_local,
                     canal_stations: list[dict], canal_by_code: dict,
                     canal_path, pump_station_codes: list[str], tide: dict | None,
                     dds_relevant_names: list[str], is_ram53: bool = False,
                     obs_conn=None) -> dict:
    pump_rows, pump_path = load_pump_rows(pump_station_codes)
    rain, rain_path = load_rain(generated_at_utc_iso, centre_lat, centre_lon)
    flood_roads, flood_road_path = load_flood_roads(generated_at_utc_iso, centre_lat, centre_lon)
    forecast, forecast_path = load_openmeteo_forecast(area_id, now_local)
    capacity = build_capacity_comparison(rain, forecast)

    upstream_stations = build_upstream_stations(canal_by_code, generated_at_utc_iso, centre_lat, centre_lon,
                                                 obs_conn=obs_conn)
    upstream_codes = {s["code"] for s in upstream_stations}
    near_stations = build_near_stations(canal_stations, upstream_codes, generated_at_utc_iso,
                                         centre_lat, centre_lon, obs_conn=obs_conn)
    stations_near = near_stations + upstream_stations

    pumps = build_pumps(pump_rows, generated_at_utc_iso, centre_lat, centre_lon, obs_conn=obs_conn)
    dds_quotes, dds_report, dds_pdf_path = build_dds_quotes(dds_relevant_names)
    hospitals = build_hospitals(centre_lat, centre_lon)

    khlongchan_rows = build_khlongchan_community(KHLONGCHAN_SOCIAL_PATH)
    nearby_community = khlongchan_rows[-3:]  # newest 3 (table is in ascending time order)

    if is_ram53:
        tiers, tiers_note = [], "ยังไม่มีรายงานรายซอย — ใช้รายงานถนนรามคำแหง/หน้า ม.ราม แทน"
        exits = build_exits_ram53()
        community = (build_ram53_community(RAM53_DIR / "social_timeline_2026-09-26.md")
                     + khlongchan_rows)
        community_label = "จุด"
        community_path = RAM53_DIR / "social_timeline_2026-09-26.md"
        community_agency = ("เสียงจากอินเทอร์เน็ต (โพสต์สาธารณะที่ค้นเจอผ่าน Google -- ไม่ใช่หน่วยงานราชการ, "
                             "ไม่เก็บชื่อผู้โพสต์ ยกเว้นสื่อที่เผยแพร่ชื่อสำนักข่าวเอง)")
    else:
        tiers, tiers_note = build_tiers_sammakorn()
        extra_20260927_path = COMMUNITY_DIR / "community_reports_2026-09-27.md"
        exits = (build_exits_sammakorn(COMMUNITY_DIR / "community_reports_2026-09-26.md")
                 + build_exits_extra_20260927(extra_20260927_path))
        community = build_community_from_tiers(tiers) + build_community_extra_20260927(extra_20260927_path)
        community_label = "ซอย"
        community_path = newest_file(COMMUNITY_DIR, "community_reports_*.md") \
            or COMMUNITY_DIR / "community_reports_2026-09-26.md"
        community_agency = "ชาวบ้านรายงาน (กลุ่มชุมชนออนไลน์ในหมู่บ้าน -- ไม่ใช่หน่วยงานราชการ, ไม่เก็บชื่อผู้โพสต์)"

    # community_from_tiers rows (sammakorn) carry no per-row date of their own --
    # backfill the source snapshot's date so newest-first sort has something to key on
    # and the page can show "(26 ก.ย.)" once that report is no longer from today.
    _snap_date = _snapshot_date_iso(community_path)
    for _r in community:
        _r.setdefault("date", _snap_date)

    obs_candidates = []
    for s in stations_near:
        if s.get("observed_at"):
            obs_candidates.append(s["observed_at"])
    for p in pumps:
        if p.get("observed_at"):
            obs_candidates.append(p["observed_at"])
    if rain and rain.get("observed_at"):
        obs_candidates.append(rain["observed_at"])
    for r in flood_roads:
        if r.get("observed_at"):
            obs_candidates.append(r["observed_at"])
    newest_obs = max(obs_candidates) if obs_candidates else None
    hours_since = lwl.age_hours(newest_obs, generated_at_utc_iso) if newest_obs else None
    staleness = {"newest_official_obs": newest_obs,
                 "hours_since": round(hours_since, 2) if hours_since is not None else None,
                 "banner": (hours_since is None) or (hours_since > 2.0)}

    sources = build_sources(rain, canal_path, pump_path, rain_path, flood_road_path,
                             dds_pdf_path, None, community_path, community_agency,
                             community_id=("community_reports_ram53" if is_ram53 else "community_reports"),
                             forecast=forecast, forecast_path=forecast_path)

    water_balance = build_village_water_balance(area_id, generated_at_utc_iso, rain)

    return {
        "label": label,
        "centre": {"lat": centre_lat, "lon": centre_lon, "label": label},
        "sources": sources,
        "stations_near": stations_near,
        "pumps": pumps,
        "rain": rain,
        "tide": tide,
        "forecast": forecast,
        "forecast_short": forecast,
        "capacity": capacity,
        "flood_roads": flood_roads,
        "tiers": tiers,
        "tiers_note": tiers_note,
        "dds_quotes": dds_quotes,
        "dds_report": dds_report,
        "exits": exits,
        "hospitals": hospitals,
        "staleness": staleness,
        "community": community,
        "community_label": community_label,
        "water_balance": water_balance,
        "nearby_community": [] if is_ram53 else nearby_community,
        "nearby_community_label": "พื้นที่ใกล้เคียง (บางกะปิ/คลองจั่น)",
    }


# --- Append-only per-run readout log + archive (project decision 2026-09-27) -------------
# site/dist/data.json is overwritten every build -- fine for the live page, but it means
# the burden ledger, canal-graph edge directions, pump counts, hero status word,
# rain/tide/forecast summary, BMA briefing fields and water-balance numbers were all lost
# after each run, with nothing left to read a water-politics/overall-picture lens through
# later. Two retention mechanisms, both run ONCE per build, right after data.json is
# written, never touching the live page output:
#   1. raw/readouts/<run_at_utc>.json -- the full data.json payload, verbatim, gitignored
#      (raw/ already is), never deleted.
#   2. data/observations.sqlite's `readout_log` table (see store.py) -- one row per
#      (run_at_utc, area, kind, key), INSERT OR IGNORE so re-running a build for the same
#      data timestamp never duplicates.
READOUTS_DIR = RAW / "readouts"


def archive_readout(data: dict, generated_at_utc_iso: str) -> Path | None:
    """Copy the full data.json payload to raw/readouts/<run_at_utc>.json. Never raises --
    a failure to archive must never break the live build."""
    try:
        dt = datetime.datetime.fromisoformat(generated_at_utc_iso)
        stamp = dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        READOUTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = READOUTS_DIR / f"{stamp}.json"
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return dest
    except Exception:  # pragma: no cover - defensive, archiving never breaks the build
        return None


def _hero_status_word_replica(area_data: dict, generated_at_utc_iso: str) -> str | None:
    """A read-only replica of build_page.py's compute_status() word rule, kept here ONLY
    so the readout_log can record the hero status word actually shown that run (build_page
    is the single source of truth for what actually renders; this must be kept in sync by
    hand if that rule changes -- never re-derives a new formula of its own). Returns None
    if it cannot be computed (defensive -- logging must never break the build)."""
    try:
        now_dt = datetime.datetime.fromisoformat(generated_at_utc_iso)

        def hours_ago(ts):
            if not ts:
                return None
            try:
                t = datetime.datetime.fromisoformat(ts)
            except ValueError:
                return None
            if t.tzinfo is None:
                t = t.replace(tzinfo=datetime.timezone.utc)
            return (now_dt - t).total_seconds() / 3600.0

        near = [s for s in (area_data.get("stations_near") or [])
                if s.get("role") in ("north", "south")]
        fresh_near = [s for s in near
                      if (h := hours_ago(s.get("observed_at"))) is not None and h <= 24
                      and s.get("status") != "NO_THRESHOLD"]
        fresh_crit = sum(1 for s in fresh_near if s.get("status") in ("CRITICAL", "OVERBANK"))
        pumps = area_data.get("pumps") or []
        pump_fail = sum(1 for p in pumps if p.get("status_th") == "ขัดข้อง")
        pump_idle = sum(1 for p in pumps
                         if (p.get("pumps_on") or 0) == 0 and (p.get("pumps_total") or 0) > 0
                         and p.get("status_th") != "ขัดข้อง")
        pumps_all_normal = bool(pumps) and pump_fail == 0 and pump_idle == 0
        all_ok = bool(fresh_near) and all(s.get("status") in ("NORMAL", "WATCH") for s in fresh_near)
        rain_mm = (area_data.get("rain") or {}).get("mm_24h")
        rain_ok = rain_mm is not None and rain_mm < 30
        if pump_fail > 0 or fresh_crit >= 2:
            return "น้ำยังขึ้น"
        if all_ok and pumps_all_normal and rain_ok:
            return "น้ำเริ่มลด"
        return "ยังบอกไม่ได้ — เตรียมพร้อมไว้ก่อน"
    except Exception:  # pragma: no cover - defensive
        return None


def write_readout_log(conn, data: dict, generated_at_utc_iso: str) -> int:
    """Writes one readout_log row per (area, kind, key) for this run -- burden-ledger
    structures, canal-graph edges, per-area pump counts, hero status word, rain/tide/
    forecast summary, water-balance and the BMA briefing. Returns the number of NEW rows
    actually inserted (0 if this run_at_utc was already logged). Never raises -- a
    logging failure must never break the live build."""
    if conn is None or store is None:
        return 0
    run_at_utc = generated_at_utc_iso
    inserted = 0
    try:
        # burden ledger -- one row per declared control structure (citywide, not tied to
        # either village sub-area)
        burden = data.get("burden_ledger") or {}
        for sid, row in (burden.get("structures") or {}).items():
            value_a, value_b = row.get("value_m"), row.get("out_m")
            diff_m = (value_b - value_a) if value_a is not None and value_b is not None else None
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area="citywide", kind="burden", key=sid,
                    state=row.get("state"), burdened_side=row.get("burdened_side"),
                    value_a=value_a, value_b=value_b, diff_m=diff_m,
                    persistence=row.get("persistence"),
                    extra={"label_th": row.get("label_th"), "result": row.get("result"),
                           "reason_codes": row.get("reason_codes"), "a_c": row.get("a_c"),
                           "observed_at": row.get("observed_at"), "stale": row.get("stale")}):
                inserted += 1

        # cross-source reconciliation (build 4, 2026-09-27) -- append-only, one summary
        # row per run plus one row per DISAGREEING station (never the hundreds of
        # AGREE-ing stations every run, to keep this table from ballooning; the summary
        # row's own agree/disagree/one_sided/no_data counts are the retained record of
        # how many agreed even when their per-station detail isn't individually logged).
        recon = data.get("cross_source_reconciliation") or {}
        summary = recon.get("summary")
        if summary:
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area="citywide", kind="reconciliation",
                    key="bma_watermap_vs_thaiwater_canal_waterlevel",
                    extra=summary):
                inserted += 1
        for code, srow in (recon.get("stations") or {}).items():
            if srow.get("status") != "DISAGREE":
                continue
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area="citywide", kind="reconciliation",
                    key=f"disagree:{code}",
                    value_a=(srow.get("a") or {}).get("value"),
                    value_b=(srow.get("b") or {}).get("value"),
                    diff_m=srow.get("delta_m"),
                    extra={"a_observed_at": (srow.get("a") or {}).get("observed_at"),
                           "b_observed_at": (srow.get("b") or {}).get("observed_at"),
                           "minutes_apart": srow.get("minutes_apart")}):
                inserted += 1

        # Sammakorn head chain (build 6, 2026-09-27) -- one row per declared edge,
        # including the backflow-risk edge, so readout_history.py can replay whether
        # backflow was active over time (never overwritten -- append-only, same identity
        # discipline as every other kind here).
        sammakorn_chain = data.get("sammakorn_chain") or {}
        for e in sammakorn_chain.get("edges") or []:
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area="sammakorn", kind="chain_edge",
                    key=e.get("edge_id"), state=e.get("direction"),
                    value_a=e.get("h_up"), value_b=e.get("h_down"), diff_m=e.get("delta_h"),
                    extra={"kind": e.get("kind"), "status": e.get("status"),
                           "refusal_reason": e.get("refusal_reason"),
                           "gate_state": e.get("gate_state"),
                           "flow_status": e.get("flow_status"),
                           "backflow_active": e.get("backflow_active")}):
                inserted += 1

        # canal graph -- one row per declared edge (citywide)
        canal_graph = data.get("canal_graph") or {}
        for e in canal_graph.get("edges") or []:
            # e["delta_m"] can be a Fraction-as-string (e.g. "1/5") rather than a plain
            # float, so it goes into extra_json (TEXT), never the typed diff_m REAL column.
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area="citywide", kind="edge",
                    key=e.get("edge_id"), state=e.get("status"),
                    burdened_side=e.get("locked_node"),
                    extra={"u": e.get("u"), "v": e.get("v"), "direction": e.get("direction"),
                           "delta_m": e.get("delta_m"),
                           "design_direction": e.get("design_direction"),
                           "control_structures": e.get("control_structures")}):
                inserted += 1

        # per-area pump counts, hero status word, rain/tide/forecast summary, water balance
        for aid, ad in (data.get("areas") or {}).items():
            pumps = ad.get("pumps") or []
            running = sum(p.get("pumps_on") or 0 for p in pumps)
            total = sum(p.get("pumps_total") or 0 for p in pumps)
            faulted = sum(1 for p in pumps if p.get("status_th") == "ขัดข้อง")
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area=aid, kind="pump",
                    key=f"{aid}_pumps", value_a=running, value_b=total,
                    extra={"stations_faulted": faulted, "stations_total": len(pumps)}):
                inserted += 1

            hero_word = _hero_status_word_replica(ad, generated_at_utc_iso)
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area=aid, kind="status",
                    key=f"{aid}_status", state=hero_word,
                    extra={"subtitle_time": data.get("generated_at_bkk")}):
                inserted += 1

            rain = ad.get("rain") or {}
            forecast = ad.get("forecast") or {}
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area=aid, kind="rain",
                    key=f"{aid}_rain", value_a=rain.get("mm_24h"), value_b=rain.get("mm_1h"),
                    extra={"observed_at": rain.get("observed_at"),
                           "tier_word": rain.get("tier_word"), "stale": rain.get("stale"),
                           "forecast_direction": forecast.get("direction"),
                           "forecast_trend_word": forecast.get("trend_word"),
                           "forecast_next6h_mm": forecast.get("next6h_mm"),
                           "forecast_next24h_mm": forecast.get("next24h_mm"),
                           "forecast_available": forecast.get("available")}):
                inserted += 1

            tide = ad.get("tide") or {}
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area=aid, kind="tide",
                    key=f"{aid}_tide",
                    extra={"next_high": tide.get("next_high"), "datum": tide.get("datum")}):
                inserted += 1

            wb = ad.get("water_balance") or {}
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area=aid, kind="balance",
                    key=f"{aid}_balance", state=wb.get("status"), value_a=wb.get("S_next"),
                    value_b=wb.get("increment"),
                    extra={"reason_codes": wb.get("reason_codes"), "trend": wb.get("trend")}):
                inserted += 1

        # BMA governor briefing -- one row, citywide (not per-area)
        briefing = data.get("bma_briefing") or {}
        if briefing:
            if store.insert_readout_log(
                    conn, run_at_utc=run_at_utc, area="citywide", kind="briefing",
                    key="bma_briefing", state=briefing.get("hero_line_th"),
                    extra=briefing):
                inserted += 1
    except Exception:  # pragma: no cover - defensive, logging never breaks the build
        return inserted
    return inserted


# --- main --------------------------------------------------------------------------------

def main():
    now_local = datetime.datetime.now(BANGKOK_TZ)
    generated_at_bkk = now_local.isoformat()
    generated_at_utc_iso = now_local.astimezone(datetime.timezone.utc).isoformat()

    canal_stations, canal_path = load_canal_stations()
    canal_by_code = {s["canal_oldcode"]: s for s in canal_stations if s.get("canal_oldcode")}
    tide, tide_path = load_tide(generated_at_utc_iso)

    dds_names = ["สะพานสูง", "แสนแสบ", "ประเวศ", "วังทองหลาง", "บางกะปิ"]

    # Retained-history DB for trend arrows (review MUST-FIX #1) -- opened once, read-only,
    # shared by both areas' station/pump builders; closed at the end of main().
    obs_conn = open_observations_db()

    sammakorn = build_area_data(
        area_id="sammakorn", label="หมู่บ้านสัมมากร (รามคำแหง 112)",
        centre_lat=13.758235, centre_lon=100.676084,
        generated_at_bkk=generated_at_bkk, generated_at_utc_iso=generated_at_utc_iso,
        now_local=now_local,
        canal_stations=canal_stations, canal_by_code=canal_by_code, canal_path=canal_path,
        pump_station_codes=["ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"],
        tide=tide, dds_relevant_names=dds_names, is_ram53=False,
        obs_conn=obs_conn,
    )
    ram53 = build_area_data(
        area_id="ram53", label="ซอยรามคำแหง 53",
        centre_lat=13.765540, centre_lon=100.619095,
        generated_at_bkk=generated_at_bkk, generated_at_utc_iso=generated_at_utc_iso,
        now_local=now_local,
        canal_stations=canal_stations, canal_by_code=canal_by_code, canal_path=canal_path,
        pump_station_codes=["ST.WTL.01", "ST.BKP.01", "ST.BKP.06", "ST.BKP.02"],
        tide=tide, dds_relevant_names=dds_names, is_ram53=True,
        obs_conn=obs_conn,
    )
    # Independent-verifier follow-up (2026-09-28): per-area (not PROP-FLOOD-06-gated)
    # worst-case 72h rain figure for the four-driver hero tile -- see
    # area_forecast_72h_worst()'s own docstring. Attached directly on each area dict
    # (not layer0_public) since the hero tile builder already receives this dict.
    sammakorn["forecast_72h_worst"] = area_forecast_72h_worst(obs_conn, "sammakorn", now_local)
    ram53["forecast_72h_worst"] = area_forecast_72h_worst(obs_conn, "ram53", now_local)
    # obs_conn stays open a little longer than it used to (build 4, 2026-09-27) --
    # build_burden_ledger_readout() below now also reads it (bma_watermap measured gate
    # state), so its close() moved down past that call instead of happening here.
    # Each area now gets its OWN Open-Meteo forecast (its own lat/lon), not a borrowed
    # district forecast -- see load_openmeteo_forecast / collect_openmeteo_forecast.

    all_sources = []
    seen_ids = set()
    for ad in (sammakorn, ram53):
        for s in ad["sources"]:
            if s["id"] in seen_ids:
                continue
            seen_ids.add(s["id"])
            all_sources.append(s)

    # TMD (กรมอุตุนิยมวิทยา) official forecast could not be fetched in this pipeline
    # (TLS/API-key access this environment does not have) -- Open-Meteo above is the
    # stand-in, always labelled third-party. This caveat is surfaced in the sources
    # footer (see build_page.py's sources block), not silently hidden.
    forecast_caveat_th = ("พยากรณ์ฝนที่แสดงมาจาก Open-Meteo (แบบจำลองเปิด บุคคลที่สาม) "
                           "เนื่องจากดึงข้อมูลอัตโนมัติจากกรมอุตุนิยมวิทยา "
                           "(TMD) ไม่ได้ในระบบนี้")

    # Bangkok-wide/east-zone water-balance upper-bound (maintainer decision 2026-09-26):
    # runs FIRST, ahead of the village sub-units, using sammakorn's own rain/forecast
    # readout as the representative gauge for the zone (labelled as such in the output).
    bangkok_east = build_bangkok_east_upper_bound(sammakorn.get("rain"), sammakorn.get("forecast"))
    bangkok_east["rain_source_note_th"] = ("ใช้ค่าฝนจากสถานีที่ใกล้สัมมากรที่สุดเป็นตัวแทนของโซน "
                                            "— ไม่ใช่ค่าเฉลี่ยทั้งโซนตะวันออก")

    briefing_raw = load_briefing()
    briefing_summary = build_briefing_summary(briefing_raw)
    drain_timeline = build_drain_timeline(sammakorn.get("rain"), sammakorn.get("forecast"),
                                           generated_at_utc_iso)
    sammakorn_rough = build_sammakorn_rough_estimate(drain_timeline)
    canal_graph_readout = build_canal_graph_readout(canal_by_code, generated_at_utc_iso)
    sammakorn_chain_obs_conn = open_observations_db()
    try:
        sammakorn_chain_readout_result = sammakorn_chain_readout(
            sammakorn_chain_obs_conn, generated_at_utc_iso,
            pump_rows=sammakorn.get("pumps"))
    finally:
        if sammakorn_chain_obs_conn is not None:
            sammakorn_chain_obs_conn.close()

    # A WRITABLE connection, separate from the read-only `obs_conn` above -- build 4
    # (2026-09-27) added two things here that need to WRITE `contradictions` rows
    # (never just read): build_burden_ledger_readout()'s measured-vs-inferred gate-state
    # check, and the bma_watermap-vs-thaiwater_canal_waterlevel reconciliation below.
    # `obs_conn` itself stays read-only and is closed first, unchanged from its own use
    # in build_area_data() above.
    if obs_conn is not None:
        obs_conn.close()
    recon_conn = None
    if store is not None and OBS_DB_PATH.exists():
        try:
            recon_conn = store.connect(OBS_DB_PATH)
        except Exception:  # pragma: no cover - defensive, reconciliation never breaks the build
            recon_conn = None

    burden_ledger_readout = build_burden_ledger_readout(canal_by_code, generated_at_utc_iso,
                                                         obs_conn=recon_conn)

    layer0_block = build_layer0_readouts(
        sammakorn=sammakorn, ram53=ram53, generated_at_utc_iso=generated_at_utc_iso,
        now_local=now_local, sammakorn_chain_readout_result=sammakorn_chain_readout_result)
    layer0_public = build_layer0_public(
        sammakorn=sammakorn, ram53=ram53, generated_at_utc_iso=generated_at_utc_iso,
        now_local=now_local, sammakorn_chain_readout_result=sammakorn_chain_readout_result)

    cross_source_reconciliation = None
    if recon_conn is not None and reconcile_mod is not None:
        try:
            cross_source_reconciliation = reconcile_mod.reconcile_canal_water_level(
                recon_conn, sorted(canal_by_code.keys()))
        except Exception:  # pragma: no cover - defensive, reconciliation never breaks the build
            cross_source_reconciliation = None
    if recon_conn is not None:
        recon_conn.close()
    if briefing_raw:
        all_sources_briefing = {
            "id": "bma_governor_briefing", "agency_th": briefing_raw.get("agency_th"),
            "url": briefing_raw.get("url"), "fetched_at": fetched_at_of(BRIEFING_PATH),
            "trust_tier": briefing_raw.get("trust_tier") or "official_report",
        }
    else:
        all_sources_briefing = None
    if all_sources_briefing and all_sources_briefing["id"] not in seen_ids:
        seen_ids.add(all_sources_briefing["id"])
        all_sources.append(all_sources_briefing)

    data = {
        "generated_at_bkk": generated_at_bkk,
        "epistemic_note": "เป็นการอ่านค่าจากหน่วยงาน ไม่ใช่การพยากรณ์",
        "default_area": "sammakorn",
        "forecast": sammakorn["forecast"],  # top-level default/back-compat = sammakorn's
        "forecast_caveat_th": forecast_caveat_th,
        "all_sources": all_sources,
        "bangkok_east_water_balance": bangkok_east,
        "bma_briefing": briefing_summary,
        "capacity_records": load_capacity_records(),
        "drain_timeline": drain_timeline,
        "sammakorn_rough": sammakorn_rough,
        "forecast_7day_compare": load_forecast_7day_compare(),
        "canal_graph": canal_graph_readout,
        "sammakorn_chain": sammakorn_chain_readout_result,
        "burden_ledger": burden_ledger_readout,
        "layer0": layer0_block,
        "layer0_public": layer0_public,
        "cross_source_reconciliation": cross_source_reconciliation,
        "areas": {"sammakorn": sammakorn, "ram53": ram53},
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Append-only archive + readout log -- see comment above write_readout_log(). Never
    # allowed to break the live build: any failure here is swallowed by the helpers
    # themselves (archive_readout / write_readout_log), not by this call site.
    archive_readout(data, generated_at_utc_iso)
    log_conn = None
    if store is not None:
        try:
            log_conn = store.connect(OBS_DB_PATH)
        except Exception:  # pragma: no cover - defensive, logging never breaks the build
            log_conn = None
    if log_conn is not None:
        try:
            write_readout_log(log_conn, data, generated_at_utc_iso)
        finally:
            log_conn.close()

    counts = {"areas": {}}
    for aid, ad in data["areas"].items():
        by_status = {}
        for s in ad["stations_near"]:
            by_status[s["status"]] = by_status.get(s["status"], 0) + 1
        counts["areas"][aid] = {
            "sources": len(ad["sources"]), "stations_near": len(ad["stations_near"]),
            "stations_near_by_status": by_status, "pumps": len(ad["pumps"]),
            "rain": 1 if ad["rain"] else 0,
            "rain_gauges": len((ad["rain"] or {}).get("gauges") or []),
            "forecast_available": ad["forecast"]["available"],
            "tide_next_high": len((ad["tide"] or {}).get("next_high", [])),
            "flood_roads": len(ad["flood_roads"]), "tiers": len(ad["tiers"]),
            "dds_quotes": len(ad["dds_quotes"]), "exits": len(ad["exits"]),
            "hospitals": len(ad["hospitals"]), "community": len(ad["community"]),
            "staleness_banner": ad["staleness"]["banner"],
        }
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
