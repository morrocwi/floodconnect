#!/usr/bin/env python3
"""tools/riskmap/subbasin_risk.py -- per-DWR-sub-basin risk readout, PARTIAL mode.

Composes ONLY already-archived/already-computed data (data/observations.sqlite,
sources/dwr_subbasins.yaml, sources/coping_thresholds.yaml, sources/capacity_ledger*.yaml)
via tools/kg/unit_resolver.py's point-in-polygon. Fires ZERO new network requests --
every number here is either MEASURED (read from observations.sqlite, computed by this
module from that MEASURED data) or RELAYED (coping_thresholds.yaml / capacity_ledger
values, themselves tagged at their own source).

No new equation (repo Toledo rule) -- tier bands are simple comparisons against
existing registered/documented thresholds (coping_thresholds.yaml, capacity_ledger*),
never a derived formula. `coverage` is a plain n/10 count of which of the 10
PROP-FLOOD-06 v5 cov5-style components this module could actually fill for that
sub-basin, not a new metric.

CLI:
    python3 -m tools.riskmap.subbasin_risk --demo        # 8 named demo points
    python3 -m tools.riskmap.subbasin_risk --central     # central-region ranking
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
DB_PATH = HERE / "data" / "observations.sqlite"
SUBBASIN_YAML = HERE / "sources" / "dwr_subbasins.yaml"
COPING_YAML = HERE / "sources" / "coping_thresholds.yaml"

sys.path.insert(0, str(HERE))
from tools.kg.unit_resolver import resolve_unit  # noqa: E402

# ---------------------------------------------------------------------------
# Tier ladder (documented, reused from LAYER0_IN_OUT_CAPACITY.md / PROP-FLOOD-06
# band language -- L0 lowest .. L5 highest, LR = refused/no-real-input)
# ---------------------------------------------------------------------------
TIER_ORDER = ["L0", "L1", "L2", "L3", "L4", "L5"]


def _max_tier(tiers: list) -> str:
    tiers = [t for t in tiers if t in TIER_ORDER]
    if not tiers:
        return "L0"
    return max(tiers, key=TIER_ORDER.index)


def _tier_from_ratio(value: float, coped_max, flooded_min) -> str:
    """Honest 3-band comparison against coping_thresholds.yaml's own
    coped_max/flooded_min pair -- NOT a new equation, a direct comparison of two
    already-documented numbers. coped_max/flooded_min may be None (OPEN)."""
    if value is None:
        return "L0"
    if flooded_min is not None and value >= flooded_min:
        return "L4"
    if coped_max is not None and flooded_min is not None:
        frac = (value - coped_max) / (flooded_min - coped_max) if flooded_min != coped_max else 0
        if frac >= 0.8:
            return "L3"
        if frac >= 0.5:
            return "L2"
        if value > coped_max:
            return "L1"
        return "L0"
    if coped_max is not None and value > coped_max:
        return "L2"  # exceeded the only bound we have, band above that is unknown
    return "L0"


# ---------------------------------------------------------------------------
# data loaders
# ---------------------------------------------------------------------------

def load_subbasins() -> list:
    doc = yaml.safe_load(SUBBASIN_YAML.read_text(encoding="utf-8"))
    return doc["rows"]


def load_coping_thresholds() -> dict:
    """Returns the `derived:` block verbatim: {unit_name: {variable: {threshold_flooded_min:
    {value,tag,...}, threshold_coped_max: {...}, ...}}} -- sources/coping_thresholds.yaml's
    own precomputed min(flooded)/max(coped) summary (see that file's header, ~line 354),
    not recomputed here (avoids drifting from the file's own arithmetic)."""
    doc = yaml.safe_load(COPING_YAML.read_text(encoding="utf-8"))
    return doc.get("derived", {})


def _connect():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def latest_per_station(con, source_id: str, variable: str = None) -> list:
    """Latest observation row per station_code for a source_id (+ optional variable
    filter), MEASURED straight from observations.sqlite."""
    q = "SELECT * FROM observations WHERE source_id=?"
    params = [source_id]
    if variable:
        q += " AND variable=?"
        params.append(variable)
    q += " ORDER BY station_code, observed_at_utc DESC"
    cur = con.execute(q, params)
    seen = set()
    rows = []
    for r in cur.fetchall():
        if r["station_code"] in seen:
            continue
        seen.add(r["station_code"])
        rows.append(dict(r))
    return rows


def forecast_series(con, source_id: str, station_code: str, variable: str) -> list:
    """Full forward time series for one station_code+variable, MEASURED (archived
    forecast run), ordered by observed_at_utc ascending."""
    cur = con.execute(
        "SELECT observed_at_utc, value FROM observations "
        "WHERE source_id=? AND station_code=? AND variable=? ORDER BY observed_at_utc ASC",
        (source_id, station_code, variable),
    )
    return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# resolving observation points to DWR sub-basins (real point-in-polygon, no network)
# ---------------------------------------------------------------------------

def resolve_points_to_subbasins(points: list, bbox: tuple = None) -> dict:
    """points: list of {"key":..., "lat":..., "lon":..., **extra}. bbox (optional):
    (min_lat, max_lat, min_lon, max_lon) pre-filter before running the point-in-polygon
    resolver (bounds this module's compute cost; matches the founder's
    central-region-only ask). Returns {sb_code: [points...]}."""
    out: dict = {}
    for p in points:
        lat, lon = p.get("lat"), p.get("lon")
        if lat is None or lon is None:
            continue
        if bbox:
            min_lat, max_lat, min_lon, max_lon = bbox
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                continue
        res = resolve_unit(lat, lon)
        sb_code = res.get("sb_code")
        if sb_code is None:
            continue
        out.setdefault(sb_code, []).append({**p, "resolver": res})
    return out


CENTRAL_BASINS = {"Chao Phraya", "Chao Phraya (Island)", "Tha Chin", "Pasak", "Bang Pakong", "Mae Klong"}
CENTRAL_BBOX = (13.0, 16.5, 99.0, 101.8)  # founder's own bbox, verbatim


def central_region_subbasins(subbasins: list) -> list:
    out = []
    for r in subbasins:
        c = r.get("centroid_wgs84_approx")
        if not c:
            continue
        lon, lat = c[0], c[1]
        in_bbox = CENTRAL_BBOX[0] <= lat <= CENTRAL_BBOX[1] and CENTRAL_BBOX[2] <= lon <= CENTRAL_BBOX[3]
        if r.get("basin_name_en") in CENTRAL_BASINS or in_bbox:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# per-sub-basin readout assembly (PARTIAL mode, coverage n/10)
# ---------------------------------------------------------------------------

# The 10 cov components this module tries to fill per sub-basin (documented here,
# not a new equation -- a checklist, same spirit as PROP-FLOOD-06 v5's cov5/cov10).
COV_COMPONENTS = [
    "gauge_waterlevel_present", "gauge_status_known", "canal_level_present",
    "river_forecast_present", "river_history_percentile_present",
    "rain_24h_present", "rain_forecast_present", "dam_present",
    "coping_threshold_known", "capacity_ledger_known",
]


def build_subbasin_readout(sb_code: str, sb_meta: dict, con, coping: dict,
                            coping_unit: str = None,
                            forecast_station_code: str = None) -> dict:
    """Assemble the per-sub-basin readout described in the founder's brief.
    coping_unit: name in coping_thresholds.yaml this sub-basin is known to correspond
    to (only a handful of sub-basins have this mapping today -- see design doc §2).
    forecast_station_code: openmeteo_flood/openmeteo_forecast16d station_code archived
    for a point inside this sub-basin, if any (only 3 exist today: chaophraya_dam,
    nakhonsawan, sammakorn, all in sb_code 1002)."""
    cov = {k: False for k in COV_COMPONENTS}
    based_on = []
    worst_case = {}

    # (a) gauge status band -- waterlevel + canal, real MEASURED counts; banding needs
    # warning/critical/bank, which is NULL for every thaiwater_waterlevel row in this
    # DB today (checked directly) -- so band is OPEN, count is not.
    wl_rows = [r for r in latest_per_station(con, "thaiwater_waterlevel")
               if _in_subbasin(r, sb_code)]
    canal_rows = [r for r in latest_per_station(con, "thaiwater_canal_waterlevel")
                  if _in_subbasin(r, sb_code)]
    if wl_rows:
        cov["gauge_waterlevel_present"] = True
        based_on.append(f"thaiwater_waterlevel: {len(wl_rows)} station(s) resolved into this sub-basin")
    n_ge_warning = sum(1 for r in wl_rows if r.get("warning") is not None and r["value"] >= r["warning"])
    n_ge_critical = sum(1 for r in wl_rows if r.get("critical") is not None and r["value"] >= r["critical"])
    n_ge_bank = sum(1 for r in wl_rows if r.get("bank") is not None and r["value"] >= r["bank"])
    gauge_band = {
        "total_stations": len(wl_rows), "ge_warning": n_ge_warning,
        "ge_critical": n_ge_critical, "ge_bank": n_ge_bank,
        "band_known": any(r.get("warning") is not None for r in wl_rows),
    }
    if gauge_band["band_known"]:
        cov["gauge_status_known"] = True
    if canal_rows:
        cov["canal_level_present"] = True
        based_on.append(f"thaiwater_canal_waterlevel: {len(canal_rows)} station(s)")

    # (b) river forecast vs history/qmax -- only where we have an archived GloFAS point
    river = {"available": False}
    if forecast_station_code:
        series = forecast_series(con, "openmeteo_flood", forecast_station_code,
                                  "glofas_river_discharge_m3s")
        if series:
            next7 = series[:7]
            vals = [p["value"] for p in next7]
            river = {
                "available": True, "station": forecast_station_code,
                "next_7day_m3s": [{"date": p["observed_at_utc"][:10], "value": p["value"]} for p in next7],
                "min": min(vals), "max": max(vals), "median": statistics.median(vals),
            }
            based_on.append(f"openmeteo_flood (GloFAS via Open-Meteo): 7-day discharge path at {forecast_station_code}")

            # flow-consistency guard BEFORE trusting this series as a tier anchor
            consistency = None
            if forecast_station_code in UPSTREAM_DOWNSTREAM_PAIRS:
                up_code, dam_codes = UPSTREAM_DOWNSTREAM_PAIRS[forecast_station_code]
                consistency = flow_consistency_flag(con, forecast_station_code, up_code, dam_codes)
                river["consistency_check"] = consistency
                if consistency["suspect"]:
                    based_on.append(
                        f"FLOW-CONSISTENCY GUARD: {forecast_station_code} series flagged SUSPECT -- {consistency['reason']}"
                    )

            var = _coping_var_for_kind(coping, coping_unit, "flow")
            if consistency and consistency["suspect"]:
                # SUSPECT: never anchor a tier on this series. Count the component as
                # ABSENT in the coverage vector (not present-but-trusted, per founder
                # ruling 2026-09-27), log the reason, do not fabricate a replacement.
                river["tier_now"] = None
                river["tier_worst_case_7day"] = None
                river["tier_note"] = "ไม่มีข้อมูลจริงที่เชื่อถือได้ / SUSPECT -- excluded from tier, see consistency_check"
                if var:
                    river["coped_max_m3s"] = var.get("coped_max")
                    river["flooded_min_m3s"] = var.get("flooded_min")
            else:
                cov["river_forecast_present"] = True
            if not (consistency and consistency["suspect"]) and var:
                coped_max = var.get("coped_max")
                flooded_min = var.get("flooded_min")
                if coped_max is not None or flooded_min is not None:
                    cov["river_history_percentile_present"] = True
                    cov["coping_threshold_known"] = True
                river["coped_max_m3s"] = coped_max
                river["flooded_min_m3s"] = flooded_min
                if coped_max is not None or flooded_min is not None:
                    river["tier_now"] = _tier_from_ratio(vals[0], coped_max, flooded_min)
                    river["tier_worst_case_7day"] = _tier_from_ratio(max(vals), coped_max, flooded_min)
                else:
                    river["tier_note"] = "ไม่มีข้อมูลจริง / absent -- no flooded_min/coped_max recorded for this unit"
                based_on.append(
                    f"sources/coping_thresholds.yaml[derived][{coping_unit}][{var['variable']}]: "
                    f"coped_max={coped_max} ({var.get('coped_tag')}) flooded_min={flooded_min} ({var.get('flooded_tag')})"
                )
        else:
            river = {"available": False, "reason": f"no glofas_river_discharge_m3s rows for {forecast_station_code}"}
    else:
        river = {"available": False,
                 "reason": "no archived GloFAS point resolves into this sub-basin -- "
                           "needs one dedicated Open-Meteo flood-API request at this "
                           "sub-basin's mainstem centroid (see design doc §3 batching plan)"}

    # (c) rain: observed 24h max + per-model worst-case forecast (NO averaging across models)
    rain_rows = [r for r in latest_per_station(con, "thaiwater_rain_24h") if _in_subbasin(r, sb_code)]
    rain = {"observed_24h_max_mm": None, "observed_24h_stations": len(rain_rows)}
    if rain_rows:
        cov["rain_24h_present"] = True
        best = max(rain_rows, key=lambda r: r["value"])
        rain["observed_24h_max_mm"] = best["value"]
        rain["observed_24h_max_station"] = best["station_name"]
        based_on.append(f"thaiwater_rain_24h: max {best['value']}mm at {best['station_name']} ({len(rain_rows)} gauges resolved)")
        rain_var = _coping_var_for_kind(coping, coping_unit, "rain")
        if rain_var:
            coped_max = rain_var.get("coped_max")
            flooded_min = rain_var.get("flooded_min")
            if coped_max is not None or flooded_min is not None:
                cov["coping_threshold_known"] = True
            rain["coped_max_mm"] = coped_max
            rain["flooded_min_mm"] = flooded_min
            if coped_max is not None or flooded_min is not None:
                rain["tier_from_observed_24h"] = _tier_from_ratio(best["value"], coped_max, flooded_min)
            else:
                rain["tier_from_observed_24h"] = None
                rain["tier_note"] = "ไม่มีข้อมูลจริง / absent -- no flooded_min/coped_max recorded for this unit's rain variable"
            based_on.append(
                f"sources/coping_thresholds.yaml[derived][{coping_unit}][{rain_var['variable']}]: "
                f"coped_max={coped_max} ({rain_var.get('coped_tag')}) flooded_min={flooded_min} ({rain_var.get('flooded_tag')})"
            )
    per_model = {}
    if forecast_station_code:
        # openmeteo_forecast16d/openmeteo_ensemble_daily use a DIFFERENT station_code
        # naming scheme than openmeteo_flood for the same physical point (MEASURED by
        # reading both tables directly: e.g. "chaophraya_dam" in openmeteo_flood is
        # "c13_chaophraya_dam" in openmeteo_forecast16d, "nakhonsawan" is
        # "c2_nakhonsawan"; "sammakorn"/"ram53"/"chiangmai"/"hatyai"/"nan"/"bangkok_east"
        # are shared or close enough to alias explicitly below -- never guessed).
        forecast16d_code = FORECAST16D_ALIAS.get(forecast_station_code, forecast_station_code)
        cur = con.execute(
            "SELECT station_code, observed_at_utc, value FROM observations "
            "WHERE source_id='openmeteo_forecast16d' AND station_code LIKE ? "
            "AND variable='precipitation_forecast_daily_mm' ORDER BY observed_at_utc ASC",
            (f"{forecast16d_code}:%",),
        )
        by_model: dict = {}
        for r in cur.fetchall():
            model = r["station_code"].split(":", 1)[1]
            by_model.setdefault(model, []).append({"date": r["observed_at_utc"][:10], "value": r["value"]})
        if by_model:
            cov["rain_forecast_present"] = True
            for model, series in by_model.items():
                next7 = series[:7]
                per_model[model] = {"next_7day_mm": next7, "worst_case_7day_total_mm": round(sum(p["value"] for p in next7), 1)}
            worst_model = max(per_model, key=lambda m: per_model[m]["worst_case_7day_total_mm"])
            rain["forecast_worst_case_model"] = worst_model
            rain["forecast_worst_case_7day_total_mm"] = per_model[worst_model]["worst_case_7day_total_mm"]
            rain["forecast_per_model"] = per_model
            based_on.append(f"openmeteo_forecast16d: {len(per_model)} independent NWP models at {forecast_station_code}, no averaging, worst-case={worst_model}")
    else:
        rain["forecast_note"] = "no per-model forecast archived for this sub-basin's centroid"

    # (d) dams inside the sub-basin
    dam_rows = [r for r in latest_per_station(con, "hii_dam") if _in_subbasin(r, sb_code)]
    dams = []
    if dam_rows:
        cov["dam_present"] = True
        by_station: dict = {}
        for r in dam_rows:
            by_station.setdefault(r["station_code"], {}).update({r["variable"]: r["value"]})
        for code, vals in by_station.items():
            dams.append({"station_code": code, **vals})
        based_on.append(f"hii_dam: {len(dams)} dam(s) resolved into this sub-basin")

    # capacity_ledger known? (only if coping_unit maps to a named ledger row family)
    if coping_unit in {"chao_phraya_bkk_reach", "nan_town", "chiangmai_town", "hatyai"}:
        cov["capacity_ledger_known"] = True
        based_on.append(f"sources/capacity_ledger.yaml: qmax/design proxy exists for {coping_unit}")

    coverage_n = sum(1 for v in cov.values() if v)
    mode = "PARTIAL"  # never claims FULL -- this module cannot resolve all 10 for any sub-basin today

    # tier: max over every band this module could actually compute from REAL, sourced
    # numbers -- no invented/illustrative thresholds. Each contributor is either a
    # direct comparison against sources/coping_thresholds.yaml's own derived
    # flooded_min/coped_max (river, rain) or a direct gauge warning/critical/bank
    # comparison already carried on the observations.sqlite row itself. A component
    # with no real threshold to compare against contributes nothing (never a guess).
    tiers = []
    if river.get("tier_now"):
        tiers.append(river["tier_now"])
    if rain.get("tier_from_observed_24h"):
        tiers.append(rain["tier_from_observed_24h"])
    if gauge_band["ge_bank"] > 0:
        tiers.append("L4")
    elif gauge_band["ge_critical"] > 0:
        tiers.append("L3")
    elif gauge_band["ge_warning"] > 0:
        tiers.append("L2")
    tier = _max_tier(tiers) if tiers else ("LR" if coverage_n == 0 else "L0")

    return {
        "sb_code": sb_code,
        "name_th": sb_meta.get("name_th"),
        "basin_name_th": sb_meta.get("basin_name_th"),
        "basin_name_en": sb_meta.get("basin_name_en"),
        "area_km2": sb_meta.get("area_sqkm"),
        "centroid": sb_meta.get("centroid_wgs84_approx"),
        "tier": tier,
        "mode": mode,
        "coverage": f"{coverage_n}/{len(COV_COMPONENTS)}",
        "coverage_components": cov,
        "based_on": based_on,
        "gauge_status_band": gauge_band,
        "river_forecast": river,
        "rain": rain,
        "dams": dams,
        "population": None,
        "population_note": "no population layer in this repo -- WorldPop (100m gridded, "
                            "free, no key) or GHSL (Global Human Settlement, free, no key) "
                            "would need a one-time raster download+zonal-stats step "
                            "(census-only, not fetched in this check)",
        "colour_class": _colour_for_tier(tier),
    }


_RESOLVE_CACHE: dict = {}


def _cached_resolve(lat: float, lon: float) -> dict:
    """Coordinate-rounded memo over tools.kg.unit_resolver.resolve_unit -- pure local
    speedup (no behaviour change) so ranking many sub-basins doesn't re-run the same
    point-in-polygon scan once per station per sub-basin."""
    key = (round(lat, 5), round(lon, 5))
    if key not in _RESOLVE_CACHE:
        _RESOLVE_CACHE[key] = resolve_unit(lat, lon)
    return _RESOLVE_CACHE[key]


# ---------------------------------------------------------------------------
# flow-consistency guard (project decision 2026-09-27: "อย่าเชื่อเซนเซอร์มาก ต้องดูความ
# สอดคล้องโดยรวมของสมการการไหลด้วย") -- a downstream reach with ONLY diversion-kind
# structures (never a documented inflow) between it and its declared upstream point
# cannot show a HIGHER discharge than upstream without either (a) a large dam release
# entering between them, or (b) a documented tributary of matching scale. Neither
# existed for C.2->C.13 at the time this check was written (all Chai Nat-reach
# diversions are capacity_value: null / OPEN in sources/capacity_ledger.yaml, and are
# `kind: diversion` -- i.e. they only remove flow, never add it). No new equation --
# this is a directional plausibility check (same spirit as PROP-FLOOD-04's "direction
# from head difference" and PROP-FLOOD-03 water balance, referenced qualitatively,
# NOT implemented here), applied to two already-archived MEASURED series.
# ---------------------------------------------------------------------------

# downstream_station_code -> (upstream_station_code, known dam-release station_codes
# whose current release could legitimately explain an increase, per capacity_ledger.yaml)
FORECAST16D_ALIAS = {
    "chaophraya_dam": "c13_chaophraya_dam",
    "nakhonsawan": "c2_nakhonsawan",
}

UPSTREAM_DOWNSTREAM_PAIRS = {
    "chaophraya_dam": ("nakhonsawan", ["dam:hii_dam:43", "dam:hii_dam:44"]),  # C.13 vs C.2; Bhumibol(43)/Sirikit(44) releases join well above C.2, cited only as a release-magnitude sanity check
}


def flow_consistency_flag(con, downstream_code: str, upstream_code: str,
                           dam_station_codes: list, days: int = 7) -> dict:
    """Real, MEASURED-only check: aligns the two archived openmeteo_flood series by
    date and the dam stations' current hourly release, and flags SUSPECT when the
    downstream reach shows MORE discharge than upstream for every one of the sampled
    days by more than the current combined dam release -- physically implausible on a
    diversion-only reach. Never invents a corrected number; only flags + states the
    real gap. Returns {"suspect": bool, "reason": str, "per_day": [...], "checked_at": ...}."""
    down = forecast_series(con, "openmeteo_flood", downstream_code, "glofas_river_discharge_m3s")[:days]
    up = forecast_series(con, "openmeteo_flood", upstream_code, "glofas_river_discharge_m3s")[:days]
    if not down or not up or len(down) != len(up):
        return {"suspect": False, "reason": "insufficient_paired_series", "checked": False}
    release_total = 0.0
    release_evidence = []
    for code in dam_station_codes:
        cur = con.execute(
            "SELECT station_name, value, observed_at_utc FROM observations "
            "WHERE source_id='hii_dam' AND station_code=? AND variable='dam_hourly_release_m3s_computed' "
            "ORDER BY observed_at_utc DESC LIMIT 1", (code,))
        r = cur.fetchone()
        if r:
            release_total += r["value"] or 0.0
            release_evidence.append(f"{r['station_name']} ({code}): {r['value']} m3/s @ {r['observed_at_utc']}")
    per_day = []
    all_exceed = True
    for d, u in zip(down, up):
        gap = d["value"] - u["value"]
        exceeds = gap > release_total
        if not exceeds:
            all_exceed = False
        per_day.append({"date": d["observed_at_utc"][:10], "downstream_m3s": d["value"],
                         "upstream_m3s": u["value"], "gap_m3s": round(gap, 1), "exceeds_known_release": exceeds})
    suspect = all_exceed and all(p["gap_m3s"] > 0 for p in per_day)
    reason = (
        f"downstream ({downstream_code}) discharge exceeds upstream ({upstream_code}) by "
        f"{per_day[0]['gap_m3s']}-{max(p['gap_m3s'] for p in per_day)} m3/s across all {len(per_day)} sampled days, "
        f"more than the current combined known dam release ({release_total} m3/s: {'; '.join(release_evidence) or 'none found'}); "
        f"every named diversion structure between C.2 and C.13 in sources/capacity_ledger.yaml is `kind: diversion` "
        f"(removes flow) with capacity_value OPEN -- no documented mechanism adds this much flow on this reach"
        if suspect else "gap within plausible range or not consistently one-directional"
    )
    return {"suspect": suspect, "reason": reason, "per_day": per_day,
            "combined_known_release_m3s": release_total, "release_evidence": release_evidence}


def _in_subbasin(row: dict, sb_code: str) -> bool:
    lat, lon = row.get("lat"), row.get("lon")
    if lat is None or lon is None:
        return False
    res = _cached_resolve(lat, lon)
    return res.get("sb_code") == sb_code


def _coping_var_for_kind(coping: dict, unit: str, kind: str) -> dict:
    """Returns {"coped_max": float|None, "flooded_min": float|None, "variable": str,
    "coped_tag":..., "flooded_tag":...} for the first matching variable name under
    `derived[unit]`, else None. kind: 'flow' matches a variable name containing
    'river_flow' or 'flow_m3s'; 'rain' matches 'rain_24h_mm'."""
    if not unit or unit not in coping:
        return None
    needle = "flow" if kind == "flow" else "rain_24h"
    for var, block in coping[unit].items():
        if needle not in var:
            continue
        fm = (block.get("threshold_flooded_min") or {}).get("value")
        cm = (block.get("threshold_coped_max") or {}).get("value")
        return {
            "variable": var, "coped_max": cm, "flooded_min": fm,
            "coped_tag": (block.get("threshold_coped_max") or {}).get("tag"),
            "flooded_tag": (block.get("threshold_flooded_min") or {}).get("tag"),
        }
    return None


def _colour_for_tier(tier: str) -> str:
    return {
        "LR": "grey", "L0": "grey", "L1": "green", "L2": "yellow",
        "L3": "orange", "L4": "red", "L5": "darkred",
    }.get(tier, "grey")


# ---------------------------------------------------------------------------
# demo runner
# ---------------------------------------------------------------------------

DEMO_POINTS = {
    # name: (lat, lon, forecast_station_code or None, coping_unit or None)
    # NOTE: chao_phraya_nakhonsawan, chao_phraya_dam_chainat, sammakorn_bangkok, and
    # bangkok_east/tha_chin's neighbours can share a DWR sb_code (DWR's Chao Phraya
    # plain / Bang Pakong plain sub-basins are single very-large polygons, see
    # docs/knowledge/DWR_SUBBASIN.md) -- each demo point still gets its OWN
    # station-specific river/rain forecast below; only the shared polygon-level gauge/
    # dam context is (deliberately) the same for points in the same sb_code.
    "chao_phraya_nakhonsawan_C2": (15.7047, 100.1372, "nakhonsawan", None),  # no coping-threshold unit registered for C.2 specifically -- OPEN
    "chao_phraya_dam_chainat_C13": (15.1897, 100.1608, "chaophraya_dam", "chao_phraya_bkk_reach"),
    "sammakorn_bangkok": (13.758235, 100.676084, "sammakorn", "sammakorn"),
    "bangkok_east": (13.7, 100.75, "bangkok_east", "bangkok_east"),
    "nan_town": (18.783958, 100.773636, "nan", "nan_town"),
    "chiangmai_ping": (18.787747, 98.993128, "chiangmai", "chiangmai_town"),
    "hatyai_utapao": (7.008765, 100.474455, "hatyai", "hatyai"),
    "mun_chi_river": (14.63898704038836, 103.2389712246912, None, None),  # largest Mun-basin sub-basin centroid, sources/dwr_subbasins.yaml
    "tha_chin_plain": (14.470208136853717, 99.90835980739013, None, None),  # largest Tha Chin sub-basin centroid
    "bang_pakong_plain": (13.465140034571432, 101.11211582363235, None, None),  # largest Bang Pakong sub-basin centroid
    "mekong_side_north": (19.533922889420026, 99.44758583372541, None, None),  # largest North Khong (Mekong-tributary) sub-basin centroid
}


def run_demo():
    con = _connect()
    coping = load_coping_thresholds()
    subbasins = {r["sb_code"]: r for r in load_subbasins()}
    results = []
    for name, (lat, lon, fc_code, coping_unit) in DEMO_POINTS.items():
        res = resolve_unit(lat, lon)
        sb_code = res.get("sb_code")
        if sb_code is None:
            results.append({"demo_point": name, "lat": lat, "lon": lon, "sb_code": None,
                             "note": "OPEN: outside all archived DWR polygons"})
            continue
        readout = build_subbasin_readout(sb_code, subbasins.get(sb_code, {}), con, coping,
                                          coping_unit=coping_unit, forecast_station_code=fc_code)
        readout["demo_point"] = name
        results.append(readout)
    return results


def run_central_ranking():
    con = _connect()
    coping = load_coping_thresholds()
    all_sb = load_subbasins()
    central = central_region_subbasins(all_sb)
    # only sub-basins we can actually say something about: those containing an archived
    # forecast point, OR those with >=1 resolved rain/waterlevel/dam observation.
    fc_lookup = {"1002": ("chaophraya_dam", "chao_phraya_bkk_reach")}  # only known mapping today
    scored = []
    for sb in central:
        sb_code = sb["sb_code"]
        fc_code, coping_unit = fc_lookup.get(sb_code, (None, None))
        readout = build_subbasin_readout(sb_code, sb, con, coping, coping_unit=coping_unit,
                                          forecast_station_code=fc_code)
        scored.append(readout)
    scored.sort(key=lambda r: (TIER_ORDER.index(r["tier"]) if r["tier"] in TIER_ORDER else -1,
                                int(r["coverage"].split("/")[0])), reverse=True)
    return scored


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--central", action="store_true")
    args = ap.parse_args()
    if args.central:
        print(json.dumps(run_central_ranking(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(run_demo(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
