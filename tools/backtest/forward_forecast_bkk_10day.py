"""forward_forecast_bkk_10day.py -- TRIAL forward run of the PROP-FLOOD-10 zoom forecast
(levels 0-3) for Bangkok, D+1..D+10, with the central-region release chain carried as an
INBOUND term beside the rain state (never merged).

    ทดลอง — สมการเป็นข้อเสนอ ยังไม่ลงทะเบียน Toledo

Every equation used here is a PROPOSAL (PROP-FLOOD-10 v2.1, 10a v1.1, 08 v1.2, 09 v1.1,
03/06 as already implemented in this repo) -- NEW DERIVATION / PROPOSAL, not yet in
Toledo. Nothing this module writes goes on the public page.

Inputs are read ONLY from:
  * the raw snapshots written by ONE `collect.py --all` sweep (raw/live/<source>/<stamp>*),
    selected by --run-prefix (the UTC stamp prefix of that sweep);
  * data/observations.sqlite (read-only URI) for gauge/telemetry rows;
  * tracked source files (sources/*.yaml).
No network call is made here.

Output: raw/forecast_tests/bkk_10day_<UTC>.json (gitignored, append-only, one new file per
run, never overwritten). tools/backtest/score_forward_forecast.py reads that record later.

Provisional values (ค่าชั่วคราว รอผู้ก่อตั้ง): N_MIN = 10; EPS_SRC undeclared (a single
source is POSSIBLE); N_CELLS = 50 Bangkok districts at level 1 + the Sammakorn chain at
levels 2-3; A5 as currently coded (a POSSIBLE forecast with NO_EVENT counts CORRECT_NEG under
STRICT). A6 = founder decision 2026-09-28: the agency's inclusive lower edge is a ZOOM-FOCUS
trigger (AT_THRESHOLD/POSSIBLE -> descend); the public rung stays strict; the agency class
label is shown beside our rung.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import sqlite3
import sys
from fractions import Fraction
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "site"))

RAW_LIVE = REPO_ROOT / "raw" / "live"
DB_PATH = REPO_ROOT / "data" / "observations.sqlite"
OUT_DIR = REPO_ROOT / "raw" / "forecast_tests"

LABEL_TH = "ทดลอง — สมการเป็นข้อเสนอ ยังไม่ลงทะเบียน Toledo"
PROVISIONAL_TH = "ค่าชั่วคราว รอผู้ก่อตั้ง"
BKK_TZ = dt.timezone(dt.timedelta(hours=7))

# ---- provisional founder-pending values -------------------------------------------------
N_MIN = 10            # FEW_EVENTS floor (ค่าชั่วคราว รอผู้ก่อตั้ง)
EPS_SRC = None        # undeclared -> single source forced POSSIBLE (ค่าชั่วคราว รอผู้ก่อตั้ง)
N_CELLS_L1 = 50       # Bangkok districts at level 1 (ค่าชั่วคราว รอผู้ก่อตั้ง)

# ---- the unified ladder (sources/rain_alert_thresholds_crosswalk.yaml unified_ladder) --
# kind: "class_edge" = agency class closed at the lower edge (reached at >=);
#       "capacity"   = a design capacity (exceeded at >); strict ROBUST needs lo > theta.
LADDER_24H = [
    {"theta": "35.1", "rung": "L1", "kind": "class_edge", "agency": "TMD เหลือง 35.1–65.0 มม./24 ชม."},
    {"theta": "65.1", "rung": "L2", "kind": "class_edge", "agency": "TMD ส้ม 65.1–125.0 มม./24 ชม."},
    {"theta": "80", "rung": "L3", "kind": "capacity", "agency": "BMA ความจุออกแบบ 80 มม./24 ชม. (หน่วยระบาย กทม.)"},
    {"theta": "125.1", "rung": "L3", "kind": "class_edge", "agency": "TMD แดง 125.1–250.0 มม./24 ชม."},
    {"theta": "250.1", "rung": "L5", "kind": "class_edge", "agency": "TMD ม่วง >250.0 มม./24 ชม."},
]
TMD_CLASSES = [  # inclusive lower edges, for the agency class label only
    ("0", "TMD ขาว 0–35.0"), ("35.1", "TMD เหลือง 35.1–65.0"), ("65.1", "TMD ส้ม 65.1–125.0"),
    ("125.1", "TMD แดง 125.1–250.0"), ("250.1", "TMD ม่วง >250.0"),
]
D_DESIGN_1H_MM = Fraction("58.7")   # BMA plan 2569 p.63, declared 1 h depth (PROP-FLOOD-08)
D_DESIGN_24H_MM = Fraction("80")    # BMA plan 2569 p.63, declared 24 h depth (PROP-FLOOD-08)
STAGE_LINES_MSL = [("1.80", "BMA derating line +1.80 ม.รทก."), ("2.00", "BMA plan 2569 'may fail' line +2.00 ม.รทก.")]

FORECAST_POINTS = {  # collect.FORECAST7D_POINTS Bangkok subset; district per repo docs
    "sammakorn": {"district_th": "สะพานสูง", "district_basis": "RELAYED — repo docs name เขตสะพานสูง for the Sammakorn demo point"},
    "bangkok_east": {"district_th": "สะพานสูง", "district_basis": "RELAYED — repo demo target 'เขตสะพานสูง (approx)'"},
    "ram53": {"district_th": "วังทองหลาง", "district_basis": "RELAYED — repo pin 'ซอยรามคำแหง 53 เขตวังทองหลาง'"},
}
DET_MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "jma_seamless", "gem_seamless",
              "meteofrance_seamless", "ukmo_seamless", "knmi_seamless", "cma_grapes_global"]
HOURLY_MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "jma_seamless", "gem_seamless",
                 "meteofrance_seamless"]


# =========================================================================================
# three-state classification (PROP-FLOOD-10a cl = D/M.71-76 classify, renamed)
# =========================================================================================

def q(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(str(x))


def cl(lo, hi, theta) -> str:
    """cl(lo,hi;θ) := classify((hi−lo)/2, (lo+hi)/2 − θ).
    ROBUST iff lo > θ; BELOW iff hi < θ; AT_THRESHOLD iff lo = hi = θ; else POSSIBLE."""
    lo, hi, theta = q(lo), q(hi), q(theta)
    if lo > hi:
        return "REFUSED:BOUND_ORDER"
    if lo > theta:
        return "ROBUST"
    if hi < theta:
        return "BELOW"
    if lo == hi == theta:
        return "AT_THRESHOLD"
    return "POSSIBLE"


def zoom_state(named_values: list, theta) -> dict:
    """C1+C2+C3: named sources, duplicate names refused, single source forced POSSIBLE when
    EPS_SRC is undeclared. `named_values` = [(name, value)], value None = absent that day."""
    present = [(n, q(v)) for n, v in named_values if v is not None]
    names = [n for n, _ in present]
    if not present:
        return {"state": "REFUSED", "reason": "MISSING_INPUT", "n_sources": 0}
    if len(set(names)) != len(names):
        return {"state": "REFUSED", "reason": "DUPLICATE_SOURCE", "n_sources": len(set(names))}
    lo = min(v for _, v in present)
    hi = max(v for _, v in present)
    out = {"lo": float(lo), "hi": float(hi), "n_sources": len(present),
           "worst_source": max(present, key=lambda nv: nv[1])[0],
           "best_source": min(present, key=lambda nv: nv[1])[0]}
    if len(present) == 1 and EPS_SRC is None:
        out.update(state="POSSIBLE", spread="UNKNOWN_SINGLE_SOURCE",
                   raw_ge_theta=bool(hi >= q(theta)))
    else:
        out["state"] = cl(lo, hi, theta)
    out["fires_strict"] = out["state"] == "ROBUST"
    out["fires_worst_first"] = bool(hi >= q(theta))
    return out


def agency_class(x) -> Optional[str]:
    if x is None:
        return None
    x = q(x)
    label = None
    for edge, name in TMD_CLASSES:
        if x >= q(edge):
            label = name
    return label


def ladder_readout(named_values: list) -> dict:
    per_theta = []
    for rung in LADDER_24H:
        zs = zoom_state(named_values, rung["theta"])
        # A6 (founder 2026-09-28): inclusive lower edge = zoom-focus trigger only
        edge_reached = (zs.get("hi") is not None and q(zs["hi"]) >= q(rung["theta"]))
        zoom_focus = zs["state"] in ("ROBUST", "AT_THRESHOLD", "POSSIBLE") or (
            rung["kind"] == "class_edge" and edge_reached)
        per_theta.append({"theta": float(q(rung["theta"])), "rung": rung["rung"], "kind": rung["kind"],
                          "agency_edge": rung["agency"], **zs,
                          "agency_edge_reached_inclusive": edge_reached if zs["state"] != "REFUSED" else None,
                          "zoom_focus_descend": zoom_focus if zs["state"] != "REFUSED" else None})
    order = ["L0", "L1", "L2", "L3", "L4", "L5"]
    strict = "L0"
    wf = "L0"
    any_ref = all(p["state"] == "REFUSED" for p in per_theta)
    for p in per_theta:
        if p["state"] == "ROBUST" and order.index(p["rung"]) > order.index(strict):
            strict = p["rung"]
        if p.get("fires_worst_first") and order.index(p["rung"]) > order.index(wf):
            wf = p["rung"]
    first = per_theta[0]
    return {
        "per_theta": per_theta,
        "rung_strict": None if any_ref else strict,
        "rung_worst_first": None if any_ref else wf,
        "tier_cap_note": "forecast-only readout: tier capped at L1 (PROP-FLOOD-06 C6); both rungs reported",
        "agency_class_hi": agency_class(first.get("hi")),
        "agency_class_lo": agency_class(first.get("lo")),
        "interval_mm": None if any_ref else [first["lo"], first["hi"]],
        "worst_source": first.get("worst_source"), "best_source": first.get("best_source"),
        "n_sources": first.get("n_sources"),
    }


# =========================================================================================
# raw snapshot loading (ONE collect sweep, selected by stamp prefix)
# =========================================================================================

def _latest(source: str, run_prefix: str, suffix: str = "") -> Optional[Path]:
    files = sorted(glob.glob(str(RAW_LIVE / source / f"{run_prefix}*{suffix}")))
    return Path(files[-1]) if files else None


def _load(p: Optional[Path]):
    if p is None:
        return None
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _rel(p: Optional[Path]) -> Optional[str]:
    return None if p is None else str(p.relative_to(REPO_ROOT))


def _stamp_of(p: Path) -> str:
    s = p.name[:18]  # 2026-09-27T181027Z
    return f"{s[:13]}:{s[13:15]}:{s[15:17]}Z"


def local_day_window_utc(date_local: str):
    d = dt.date.fromisoformat(date_local)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=BKK_TZ).astimezone(dt.timezone.utc)
    return start, start + dt.timedelta(days=1)


# ---- daily per-model rain at the Bangkok points ------------------------------------------

def load_daily_models(run_prefix: str) -> dict:
    """{point: {"file","grid":[lat,lon],"series":{model:{date:mm|None}}}} from openmeteo_forecast16d."""
    out = {}
    for point in FORECAST_POINTS:
        p = _latest("openmeteo_forecast16d", run_prefix, f"_{point}.json")
        d = _load(p)
        if not d:
            out[point] = {"file": None}
            continue
        times = d["daily"]["time"]
        series = {}
        for m in DET_MODELS:
            vals = d["daily"].get(f"precipitation_sum_{m}") or []
            series[m] = {t: (vals[i] if i < len(vals) else None) for i, t in enumerate(times)}
        out[point] = {"file": _rel(p), "fetched_at_utc": _stamp_of(p),
                      "grid": [d.get("latitude"), d.get("longitude")], "series": series}
    return out


def load_metno_local_days(run_prefix: str) -> dict:
    """MET Norway: local-day (UTC+7) totals from next_1_hours ONLY where every hour of the
    local day is covered by an hourly step; 6-hour blocks start at 00/06/12/18 UTC and never
    align with local midnight (07:00 local offset) -> such days are REFUSED WINDOW_MISALIGNED
    (conversion rule R3: no day-boundary shift without the hourly series)."""
    out = {}
    for point in FORECAST_POINTS:
        p = _latest("metno_locationforecast", run_prefix, f"_{point}.json")
        d = _load(p)
        if not d:
            out[point] = {"file": None}
            continue
        hourly = {}
        for e in d["properties"]["timeseries"]:
            n1 = e["data"].get("next_1_hours")
            if n1 is None:
                continue
            t = dt.datetime.fromisoformat(e["time"].replace("Z", "+00:00"))
            hourly[t] = n1["details"].get("precipitation_amount")
        days = {}
        hmax = {}
        dates = sorted({t.astimezone(BKK_TZ).date().isoformat() for t in hourly})
        for date in dates:
            s, e_ = local_day_window_utc(date)
            hours = [s + dt.timedelta(hours=k) for k in range(24)]
            vals = [hourly.get(h) for h in hours]
            if any(v is None for v in vals):
                days[date] = None
                hmax[date] = None
            else:
                days[date] = round(sum(vals), 1)
                hmax[date] = max(vals)
        out[point] = {"file": _rel(p), "fetched_at_utc": _stamp_of(p),
                      "updated_at": d["properties"]["meta"].get("updated_at"),
                      "daily_local": days, "hourly_max_local": hmax}
    return out


def load_ensemble_members(run_prefix: str) -> dict:
    out = {}
    for point in FORECAST_POINTS:
        p = _latest("openmeteo_ensemble_daily", run_prefix, f"_{point}.json")
        d = _load(p)
        if not d:
            out[point] = {"file": None}
            continue
        daily = d["daily"]
        times = daily["time"]
        members = {}
        for k, vals in daily.items():
            if k == "time":
                continue
            name = "member00" if k == "precipitation_sum" else k[len("precipitation_sum_"):]
            members[name] = {t: (vals[i] if i < len(vals) else None) for i, t in enumerate(times)}
        out[point] = {"file": _rel(p), "fetched_at_utc": _stamp_of(p),
                      "grid": [d.get("latitude"), d.get("longitude")], "members": members}
    return out


def load_hourly_models(run_prefix: str) -> dict:
    out = {}
    for m in HOURLY_MODELS:
        p = _latest("openmeteo_multimodel", run_prefix, f"_{m}.json")
        d = _load(p)
        if not d:
            out[m] = {"file": None}
            continue
        times = d["hourly"]["time"]
        vals = d["hourly"]["precipitation"]
        by_day = {}
        for t, v in zip(times, vals):
            by_day.setdefault(t[:10], []).append(v)
        out[m] = {"file": _rel(p), "fetched_at_utc": _stamp_of(p), "grid": [d.get("latitude"), d.get("longitude")],
                  "max_hour_mm": {day: (max(v) if len(v) == 24 and all(x is not None for x in v) else None)
                                  for day, v in by_day.items()}}
    return out


# ---- boundary / inbound / context snapshots ---------------------------------------------

def load_glofas(run_prefix: str) -> dict:
    out = {}
    for pt in ("nakhonsawan", "chaophraya_dam", "bang_sai"):
        p = _latest("openmeteo_flood", run_prefix, f"_{pt}.json")
        d = _load(p)
        if not d:
            out[pt] = {"file": None}
            continue
        out[pt] = {"file": _rel(p), "fetched_at_utc": _stamp_of(p), "grid": [d["latitude"], d["longitude"]],
                   "daily_m3s": dict(zip(d["daily"]["time"], d["daily"]["river_discharge"])),
                   "tag": "forecast-inferred (GloFAS model via Open-Meteo) — never substituted for a gauge"}
    return out


def load_marine(run_prefix: str) -> dict:
    p = _latest("openmeteo_marine", run_prefix, ".json")
    d = _load(p)
    if not d:
        return {"file": None}
    by_day = {}
    for t, v in zip(d["hourly"]["time"], d["hourly"]["sea_level_height_msl"]):
        by_day.setdefault(t[:10], []).append(v)
    return {"file": _rel(p), "fetched_at_utc": _stamp_of(p), "grid": [d["latitude"], d["longitude"]],
            "daily_max_m": {k: (max(v) if len(v) == 24 else None) for k, v in by_day.items()},
            "datum_caveat": ("model MSL at the river-mouth bar grid point — NOT ม.รทก. (Ko Lak) and NOT a stage "
                             "at C.12; compared with +1.80/+2.00 only as context, never as the stage readout")}


def load_pressure(run_prefix: str) -> dict:
    out = {}
    for point in ("sammakorn", "ram53"):
        p = _latest("openmeteo_pressure", run_prefix, f"_{point}.json")
        d = _load(p)
        if not d:
            continue
        times = d["hourly"]["time"]
        per_model = {}
        for k, vals in d["hourly"].items():
            if not k.startswith("pressure_msl_"):
                continue
            m = k[len("pressure_msl_"):]
            idx = {t: v for t, v in zip(times, vals)}
            day_min_d24 = {}
            for i, t in enumerate(times):
                if i < 24 or vals[i] is None or vals[i - 24] is None:
                    continue
                d24 = round(vals[i] - vals[i - 24], 1)
                day = t[:10]
                day_min_d24[day] = d24 if day not in day_min_d24 else min(day_min_d24[day], d24)
            per_model[m] = day_min_d24
            _ = idx
        out[point] = {"file": _rel(p), "fetched_at_utc": _stamp_of(p), "min_delta24_hpa_per_local_day": per_model}
    return {"points": out, "caveat": ("context only — PRESSURE_DROP_24H is a candidate promoter, not yet in Toledo; "
                                      "lag-24 difference cancels an exact 12 h/24 h periodic (atmospheric tide) part only "
                                      "if it is exactly periodic")}


def load_soil_and_archive(run_prefix: str, issue_utc: dt.datetime) -> dict:
    out = {}
    for point in ("sammakorn", "ram53", "bangkok_east"):
        ps = _latest("openmeteo_soil_moisture", run_prefix, f"_{point}.json")
        pa = _latest("openmeteo_archive_precip", run_prefix, f"_{point}.json")
        ds, da = _load(ps), _load(pa)
        rec = {}
        if ds:
            h = ds["hourly"]
            issue_local = issue_utc.astimezone(BKK_TZ).strftime("%Y-%m-%dT%H:00")
            i = h["time"].index(issue_local) if issue_local in h["time"] else 0
            rec["soil_moisture"] = {"file": _rel(ps), "at_local": h["time"][i],
                                    "0_1cm": h["soil_moisture_0_to_1cm"][i], "1_3cm": h["soil_moisture_1_to_3cm"][i],
                                    "3_9cm": h["soil_moisture_3_to_9cm"][i], "unit": "m3/m3",
                                    "tag": "RELAYED model analysis/forecast (Open-Meteo), not a gauge"}
        if da:
            vals = [v for v in da["daily"]["precipitation_sum"] if v is not None]
            rec["archive_precip"] = {"file": _rel(pa), "first_day": da["daily"]["time"][0],
                                     "last_day": da["daily"]["time"][-1], "n_days": len(vals),
                                     "sum_30d_mm": round(sum(vals), 1),
                                     "sum_last7_mm": round(sum(vals[-7:]), 1),
                                     "tag": "RELAYED reanalysis (Open-Meteo archive), not a gauge"}
        out[point] = rec
    return out


def load_sst(run_prefix: str) -> dict:
    p = _latest("openmeteo_sst", run_prefix, ".json")
    d = _load(p)
    if not d:
        return {"file": None}
    pts = []
    for x in d:
        v = [a for a in x["hourly"]["sea_surface_temperature"] if a is not None]
        pts.append({"grid": [x["latitude"], x["longitude"]], "last_c": v[-1] if v else None,
                    "max_c": max(v) if v else None, "min_c": min(v) if v else None})
    return {"file": _rel(p), "fetched_at_utc": _stamp_of(p), "points": pts, "tag": "context only"}


# =========================================================================================
# DB readers (read-only)
# =========================================================================================

def db_connect(path: Path = DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _km(a, b) -> float:
    return math.hypot((a[0] - b[0]) * 111.0, (a[1] - b[1]) * 111.0 * math.cos(math.radians(13.75)))


def road_stations(conn) -> dict:
    rows = conn.execute("SELECT station_code, lat, lon, provenance_json FROM observations "
                        "WHERE source_id='thaiwater_flood_road' GROUP BY station_code").fetchall()
    out = {}
    for sc, la, lo, prov in rows:
        try:
            dname = json.loads(prov or "{}").get("district_th")
        except ValueError:
            dname = None
        out[sc] = {"lat": la, "lon": lo, "district_th": dname}
    return out


def flood_road_now(conn, issue_utc: dt.datetime) -> dict:
    """Latest flood_road reading per station within 2 h before issue."""
    lo = (issue_utc - dt.timedelta(hours=2)).isoformat()
    rows = conn.execute("SELECT station_code, value, observed_at_utc, provenance_json FROM observations "
                        "WHERE source_id='thaiwater_flood_road' AND observed_at_utc>=? AND observed_at_utc<=? "
                        "ORDER BY observed_at_utc", (lo, issue_utc.isoformat())).fetchall()
    latest = {}
    for sc, v, t, prov in rows:
        latest[sc] = (v, t, json.loads(prov or "{}").get("district_th"))
    by_d = {}
    for sc, (v, t, d) in latest.items():
        rec = by_d.setdefault(d, {"n_stations_reporting": 0, "n_ge_10cm": 0, "max_cm": None, "last_obs_utc": None})
        rec["n_stations_reporting"] += 1
        if v is not None:
            rec["max_cm"] = v if rec["max_cm"] is None else max(rec["max_cm"], v)
            if v >= 10:
                rec["n_ge_10cm"] += 1
        rec["last_obs_utc"] = max(rec["last_obs_utc"] or t, t)
    return by_d


# Declared gauge -> district (overrides the nearest-road-station INSTINCT rule): the repo's
# own declared nearest official gauge to the Sammakorn pond (compute_prop_flood_06_sammakorn
# SAMMAKORN_RAIN_STATION_CODE, "สนข.สะพานสูง").
DECLARED_GAUGE_DISTRICT = {"528759": "สะพานสูง"}


def assign_gauge_district(code, lat, lon, roads: dict) -> Optional[str]:
    if code in DECLARED_GAUGE_DISTRICT:
        return DECLARED_GAUGE_DISTRICT[code]
    if not roads or lat is None or lon is None:
        return None
    best = min(roads.items(), key=lambda kv: _km((lat, lon), (kv[1]["lat"], kv[1]["lon"])))
    if _km((lat, lon), (best[1]["lat"], best[1]["lon"])) > 3.0:
        return None
    return best[1]["district_th"]


def gauges_by_district(conn, issue_utc: dt.datetime, roads: dict) -> dict:
    """Latest rain_24h / rain_1h per Bangkok-bbox gauge (<= 2 h before issue), assigned to the
    district of the nearest flood_road station if <= 3 km (INSTINCT assignment, same rule as
    the 2026-09-27 zoom backtest; no district polygons are held)."""
    lo = (issue_utc - dt.timedelta(hours=2)).isoformat()
    out = {}
    for var in ("rain_24h_mm", "rain_1h_mm"):
        rows = conn.execute(
            "SELECT station_code, station_name, lat, lon, value, observed_at_utc FROM observations "
            "WHERE source_id='thaiwater_rain_24h' AND variable=? AND lat BETWEEN 13.49 AND 13.96 "
            "AND lon BETWEEN 100.32 AND 100.94 AND observed_at_utc>=? AND observed_at_utc<=? "
            "ORDER BY observed_at_utc", (var, lo, issue_utc.isoformat())).fetchall()
        latest = {}
        for sc, sn, la, lo_, v, t in rows:
            latest[sc] = (sn, la, lo_, v, t)
        for sc, (sn, la, lo_, v, t) in latest.items():
            d = assign_gauge_district(sc, la, lo_, roads)
            if v is None or d is None:
                continue
            rec = out.setdefault(d, {}).setdefault(var, {"gauges": [], "obs_utc": None})
            rec["gauges"].append({"code": sc, "name": sn, "value": v})
            rec["obs_utc"] = max(rec["obs_utc"] or t, t)
    for d, rec in out.items():
        for var, r in rec.items():
            vs = [g["value"] for g in r["gauges"]]
            r["interval"] = [min(vs), max(vs)]
            r["n"] = len(vs)
    return out


def river_rows(conn) -> dict:
    out = {}
    for sc in ("C.12", "C.13", "C.2", "C.3", "C.7A", "C.35", "C.36", "C.37", "S.26", "S.28"):
        rows = conn.execute("SELECT source_id, variable, value, observed_at_utc FROM observations "
                            "WHERE station_code=? AND source_id IN ('thaiwater_waterlevel','hii_waterlevel_load') "
                            "ORDER BY observed_at_utc", (sc,)).fetchall()
        out[sc] = [{"source": s, "variable": v, "value": x, "observed_at_utc": t} for s, v, x, t in rows]
    dds = conn.execute("SELECT variable, value, observed_at_utc FROM observations WHERE source_id='dds_daily_pdf' "
                       "AND variable LIKE 'qmax%' ORDER BY variable, observed_at_utc").fetchall()
    out["dds_daily_pdf_qmax"] = [{"variable": v, "value": x, "day_end_utc": t} for v, x, t in dds]
    return out


def dam_rows(conn) -> list:
    rows = conn.execute(
        "SELECT station_code, station_name, variable, value, observed_at_utc FROM observations WHERE source_id='hii_dam' "
        "AND variable IN ('dam_daily_inflow_mcm','dam_daily_release_mcm','dam_daily_release_m3s_computed',"
        "'dam_daily_storage_pct','dam_daily_spilled_mcm') AND (station_name LIKE '%ภูมิพล%' OR station_name LIKE '%สิริกิติ์%' "
        "OR station_name LIKE '%ป่าสัก%' OR station_name LIKE '%แควน้อย%') ORDER BY station_name, variable, observed_at_utc").fetchall()
    return [{"station_code": a, "dam": b, "variable": c, "value": d, "observed_at_utc": e} for a, b, c, d, e in rows]


def navy_tide_by_day(conn, dates: list) -> dict:
    out = {}
    for date in dates:
        s, e = local_day_window_utc(date)
        rows = conn.execute("SELECT variable, value, observed_at_utc FROM observations WHERE source_id='dds_tide_pdf' "
                            "AND variable LIKE 'tide_hw%' AND observed_at_utc>=? AND observed_at_utc<? ORDER BY value DESC",
                            (s.isoformat(), e.isoformat())).fetchall()
        out[date] = {"hw_max_m": rows[0][1] if rows else None, "at_utc": rows[0][2] if rows else None}
    return out


def oni(conn) -> Optional[dict]:
    r = conn.execute("SELECT value, observed_at_utc, provenance_json FROM observations WHERE source_id='noaa_oni' "
                     "ORDER BY observed_at_utc DESC LIMIT 1").fetchone()
    return None if r is None else {"value_degC": r[0], "fetched_at_utc": r[1], "provenance": json.loads(r[2] or "{}")}


# =========================================================================================
# assembly
# =========================================================================================

def dedupe_sources(daily: dict, metno: dict, dates: list) -> tuple:
    """Build named sources per day. A (model, point) whose whole series equals the same
    model's series at an earlier point is the SAME reading (same grid cell) and is counted
    once (C3: two copies of one reading never count as two sources)."""
    order = ["sammakorn", "ram53", "bangkok_east"]
    kept, collapsed = [], []
    for m in DET_MODELS:
        seen = {}
        for pt in order:
            s = (daily.get(pt) or {}).get("series", {}).get(m)
            if s is None:
                continue
            key = tuple(s.get(d) for d in dates)
            if key in seen:
                collapsed.append({"source": f"{m}@{pt}", "same_reading_as": f"{m}@{seen[key]}"})
                continue
            seen[key] = pt
            kept.append((f"{m}@{pt}", s))
    seen_metno = {}
    for pt in order:
        s = (metno.get(pt) or {}).get("daily_local")
        if s is None:
            continue
        key = tuple(s.get(d) for d in dates)
        if key in seen_metno:
            collapsed.append({"source": f"metno@{pt}", "same_reading_as": f"metno@{seen_metno[key]}"})
            continue
        seen_metno[key] = pt
        kept.append((f"metno@{pt}", s))
    return kept, collapsed


def district_sources(kept: list, district: str) -> list:
    pts = [p for p, meta in FORECAST_POINTS.items() if meta["district_th"] == district]
    return [(n, s) for n, s in kept if n.split("@")[1] in pts]


def compute(run_prefix: str, issue_utc: Optional[dt.datetime] = None, db_path: Path = DB_PATH) -> dict:
    import yaml
    daily = load_daily_models(run_prefix)
    metno = load_metno_local_days(run_prefix)
    ens = load_ensemble_members(run_prefix)
    hourly = load_hourly_models(run_prefix)
    samm_file = daily["sammakorn"]
    if issue_utc is None:
        issue_utc = dt.datetime.fromisoformat(samm_file["fetched_at_utc"].replace("Z", "+00:00"))
    dates = list(samm_file["series"]["ecmwf_ifs025"].keys())[:10]
    kept, collapsed = dedupe_sources(daily, metno, dates)

    conn = db_connect(db_path)
    try:
        roads = road_stations(conn)
        fr_now = flood_road_now(conn, issue_utc)
        gauges = gauges_by_district(conn, issue_utc, roads)
        rivers = river_rows(conn)
        dams = dam_rows(conn)
        tide = navy_tide_by_day(conn, dates)
        oni_row = oni(conn)
    finally:
        conn.close()

    # Sammakorn chain (existing readout, reused verbatim, read-only DB)
    try:
        import build_data as bd  # site/build_data.py
        bconn = bd.open_observations_db()
        chain = bd.sammakorn_chain_readout(bconn, issue_utc.isoformat())
        bconn.close()
    except Exception as exc:  # pragma: no cover - defensive
        chain = {"available": False, "error": repr(exc)}
    pumps = _sammakorn_pumps(db_path, issue_utc)

    glofas = load_glofas(run_prefix)
    marine = load_marine(run_prefix)
    pressure = load_pressure(run_prefix)
    soil = load_soil_and_archive(run_prefix, issue_utc)
    sst = load_sst(run_prefix)
    districts50 = [r["district_th"] for r in
                   yaml.safe_load(open(REPO_ROOT / "sources" / "bkk_district_elevation.yaml", encoding="utf-8"))["districts"]]
    units = yaml.safe_load(open(REPO_ROOT / "sources" / "backtest_units.yaml", encoding="utf-8"))
    samm_fields = (units.get("normalized_fields") or {}).get("sammakorn") or {}

    c12 = [r for r in rivers["C.12"] if r["variable"] == "waterlevel_msl"]
    c12_last = c12[-1] if c12 else None
    c12_max = max(c12, key=lambda r: r["value"]) if c12 else None
    stage_now = {}
    for theta, lab in STAGE_LINES_MSL:
        if c12_max:
            zs = zoom_state([("C.12@thaiwater_waterlevel", c12_max["value"])], theta)
            stage_now[theta] = {"line": lab, "reading": "max of held 27 Sep series", **zs}
    inbound = build_inbound(rivers, dams, glofas)
    days = []
    for n, date in enumerate(dates, start=1):
        s_utc, e_utc = local_day_window_utc(date)
        h_hours = math.floor((s_utc - issue_utc).total_seconds() / 3600)
        named = [(name, series.get(date)) for name, series in kept]
        l0 = ladder_readout(named)
        l0["unit"] = "DWR sub-basin 1002 (Bangkok part) — Open-Meteo grid cells (13.75,100.75) and (13.75,100.5) + MET Norway points"
        l0["sources_used"] = [{"name": nm, "mm": v} for nm, v in named if v is not None]
        l0["sources_absent_this_day"] = [nm for nm, v in named if v is None]
        l0["metno_refused"] = [f"metno@{p}" for p in FORECAST_POINTS
                               if (metno.get(p) or {}).get("daily_local", {}).get(date, "ABSENT") is None]
        # ensemble envelope per point (schema: members of ONE model; never averaged, never merged)
        env = {}
        for pt, e in ens.items():
            if not e.get("members"):
                continue
            vals = [(f"gefs_{k}@{pt}", v.get(date)) for k, v in e["members"].items()]
            present = [v for _, v in vals if v is not None]
            if not present:
                continue
            env[pt] = {"n_members": len(present), "min": min(present), "max": max(present),
                       "state_at_35_1": cl(min(present), max(present), "35.1"),
                       "members_ge_35_1": sum(1 for v in present if q(v) >= q("35.1"))}
        l0["ensemble_envelope_gefs"] = env
        # level 1 — 1 h window at the Sammakorn grid cell (forecast-inferred)
        hnamed = [(f"{m}@sammakorn_hourly", (hourly.get(m) or {}).get("max_hour_mm", {}).get(date)) for m in HOURLY_MODELS]
        hnamed += [(f"metno@{p}_hourly", (metno.get(p) or {}).get("hourly_max_local", {}).get(date))
                   for p in ("sammakorn", "ram53")]
        if all(v is None for _, v in hnamed):
            l1h = {"state": "REFUSED", "reason": "INPUT_ABSENT (no hourly forecast covers this local day; "
                                                   "never bridged from the 24 h total)"}
        else:
            l1h = zoom_state(hnamed, D_DESIGN_1H_MM)
            l1h["L1_ratio_interval"] = [round(l1h["lo"] / 58.7, 3), round(l1h["hi"] / 58.7, 3)]
            l1h["sources"] = [{"name": a, "max_hour_mm": b} for a, b in hnamed if b is not None]
        l1h["tag"] = "forecast-inferred (model grid value, max hourly per local day) vs D_design(U,1h)=58.7 mm"
        # level 1 — districts (N_cells = 50)
        dist_rows = []
        for dname in districts50:
            srcs = district_sources(kept, dname)
            row = {"district_th": dname}
            if srcs:
                lr = ladder_readout([(nm, s.get(date)) for nm, s in srcs])
                row.update(forecast=lr, forecast_points=sorted({nm.split('@')[1] for nm, _ in srcs}),
                           evaluated_by_gate=(l0["per_theta"][0]["zoom_focus_descend"] is True),
                           l24_vs_80=lr["per_theta"][2]["state"])
            else:
                row["forecast"] = {"state": "REFUSED", "reason": "INPUT_ABSENT — no forecast grid point declared inside this "
                                   "district; a city/screen readout never licenses a district statement (EQ-002/M.01); "
                                   "no district polygons held (UNIT_POLYGON_MISSING)"}
            row["carried_at_issue"] = {"flood_road": fr_now.get(dname), "gauges": gauges.get(dname)}
            dist_rows.append(row)
        # boundary: stage and tide
        stage = {
            "C12_forecast": {"state": "REFUSED", "reason": "NO_STAGE_FORECAST — no routing model, no stage forecast "
                             "source held; the measured 27 Sep exceedance is carried as a flag, never projected"},
            "navy_astronomical_hw_max_m": tide.get(date),
            "navy_note": "Royal Thai Navy astronomical prediction (ม.รทก., RELAYED datum); excludes dam release and rain",
            "openmeteo_marine_daily_max_m": (marine.get("daily_max_m") or {}).get(date),
            "marine_note": marine.get("datum_caveat"),
        }
        inbound_day = {"D_in": {"state": "REFUSED", "reason": "TAU_UNDECLARED"},
                       "glofas_forecast_inferred_m3s": {pt: (g.get("daily_m3s") or {}).get(date) for pt, g in glofas.items()}}
        days.append({"day_index": n, "date_local": date, "window_utc": [s_utc.isoformat(), e_utc.isoformat()],
                     "h_hours": h_hours, "level0": l0, "level1_1h_sammakorn_cell": l1h,
                     "level1_districts": dist_rows, "stage_boundary": stage, "inbound": inbound_day,
                     "pressure_min_delta24_hpa": {pt: {m: v.get(date) for m, v in rec["min_delta24_hpa_per_local_day"].items()}
                                                  for pt, rec in pressure["points"].items()}})
    level23 = build_sammakorn_chain(chain, pumps, samm_fields)
    record = {
        "record_type": "bkk_10day_forward_forecast",
        "label_th": LABEL_TH,
        "public_page": False,
        "equations": {"PROP-FLOOD-10": "v2.1", "PROP-FLOOD-10a": "v1.1", "PROP-FLOOD-08": "v1.2",
                      "PROP-FLOOD-09": "v1.1", "PROP-FLOOD-03/06": "as implemented in this repo",
                      "status": "NEW DERIVATION / PROPOSAL — not yet in Toledo"},
        "issued_at_utc": issue_utc.isoformat(),
        "issued_at_local": issue_utc.astimezone(BKK_TZ).isoformat(),
        "collect_run_prefix": run_prefix,
        "provisional_values": {"N_min": N_MIN, "eps_src": EPS_SRC, "N_cells_level1": N_CELLS_L1,
                               "N_cells_level23": "Sammakorn chain (soi, pond, บ้านม้า 2, แสนแสบ)",
                               "A5": "as currently coded: under STRICT, POSSIBLE + NO_EVENT counts CORRECT_NEG",
                               "label_th": PROVISIONAL_TH},
        "founder_decisions": {"A6": ("decided 2026-09-28 (founder 'เอาเลย'): the agency's inclusive lower edge is a "
                                     "ZOOM-FOCUS trigger (AT_THRESHOLD/POSSIBLE -> descend); the public rung stays strict; "
                                     "the agency class label is shown beside our rung")},
        "ladder_24h": LADDER_24H,
        "source_dedupe": {"kept": [n for n, _ in kept], "collapsed_same_reading": collapsed},
        "inputs": {
            "daily_models": daily, "metno": metno,
            "ensemble_files": {p: {k: v for k, v in e.items() if k != "members"} for p, e in ens.items()},
            "hourly_models": hourly, "glofas": glofas, "marine": marine, "pressure": pressure,
            "soil_and_archive": soil, "sst": sst, "oni": oni_row,
            "rivers": rivers, "dams": dams, "navy_tide_hw_by_day": tide,
            "flood_road_now_by_district": fr_now, "gauges_by_district": gauges,
        },
        "stage_now": {"C12_last": c12_last, "C12_max_held": c12_max, "vs_lines": stage_now,
                      "datum": "waterlevel_msl field = ม.รทก. by field name (sources/units_datum_crosswalk.yaml)"},
        "inbound_summary": inbound,
        "level23_sammakorn": level23,
        "days": days,
    }
    return record


def _sammakorn_pumps(db_path: Path, issue_utc: dt.datetime) -> dict:
    conn = db_connect(db_path)
    try:
        out = {}
        for code in ("ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"):
            r = conn.execute("SELECT station_name, status, observed_at_utc, provenance_json FROM observations WHERE "
                             "station_code=? AND observed_at_utc<=? ORDER BY observed_at_utc DESC LIMIT 1",
                             (code, issue_utc.isoformat())).fetchone()
            if r:
                p = json.loads(r[3] or "{}")
                out[code] = {"name": r[0], "status": r[1], "observed_at_utc": r[2], "pumps_on": p.get("pumps_on"),
                             "pumps_total": p.get("pumps_total"), "sensor_status": p.get("sensor_status")}
        return out
    finally:
        conn.close()


def build_inbound(rivers: dict, dams: list, glofas: dict) -> dict:
    def last(sc, var):
        rows = [r for r in rivers.get(sc, []) if r["variable"] == var]
        return rows[-1] if rows else None
    c13q = last("C.13", "discharge")
    booked = None
    if c13q and c13q["value"] is not None:
        booked = {"edge": "C.13 → Bangkok reach (declared link, PROP-FLOOD-10 inbound list)",
                  "Q_m3s": c13q["value"], "observed_at_utc": c13q["observed_at_utc"],
                  "q_per_hour_tick_m3": c13q["value"] * 3600,
                  "note": "q(k) = Q·τ for the one held hourly tick; booked, arrival time unknown"}
    return {
        "D_in_state": "REFUSED",
        "D_in_reason": ("TAU_UNDECLARED — no Bangkok-linked edge has a declared d_e. HII chaophraya.svg carries the "
                        "labels '2 วัน','1 วัน','3 วัน','6 ชม.','2 วัน','2 วัน','20 ชม.','2.5 วัน','1 วัน','1 วัน','1 วัน' "
                        "in an SVG group 'Days' with positions only; no label is tied to a station pair in the file "
                        "(no id/edge reference), so none is RELAYED-declared here"),
        "booked_arrival_unknown": booked,
        "measured_now": {sc: {"discharge": last(sc, "discharge"), "waterlevel_msl": last(sc, "waterlevel_msl")}
                         for sc in ("C.2", "C.13", "C.3", "C.7A", "C.35", "C.36", "C.37", "S.26", "S.28")},
        "dds_qmax_series": rivers.get("dds_daily_pdf_qmax"),
        "dams_daily": dams,
        "dam_trend": "REFUSED TREND_SERIES_SHORT — only 1–2 daily rows held per dam in this store",
        "glofas_note": ("GloFAS forecast-inferred per day, beside and never substituted for gauges. bang_sai grid cell "
                        "(14.325,100.575) returns single-digit m3/s — not the Chao Phraya main stem (INSTINCT); "
                        "excluded as an inbound proxy (GRID_CELL_NOT_ON_MAIN_STEM)"),
        "sources_linked": ["C.13 release", "C.2", "C.29/Sam Khok/Bang Sai", "Pasak via Rama VI (S.26)",
                           "Bhumibol / Sirikit (upstream of C.2)", "east field water (INPUT_ABSENT)"],
        "excluded": "Mae Klong releases (RID Region 13) — not linked (INSTINCT, PROP-FLOOD-10)",
    }


def build_sammakorn_chain(chain: dict, pumps: dict, fields: dict) -> dict:
    nodes = (chain or {}).get("nodes") or {}
    pond = nodes.get("pond") or {}
    pumps_on = sum((p.get("pumps_on") or 0) for p in pumps.values())
    pumps_total_stations = len(pumps)
    faults = [c for c, p in pumps.items() if p.get("sensor_status") == "fault"]
    cap = (fields.get("pond_storage_capacity_m3") or {}).get("value")
    dh = (fields.get("D_H") or {}).get("value")
    tdd_full = None
    if cap and dh:
        tdd_full = {"V_m3": cap, "Q_out_rated_m3s": dh, "T_dd_s": round(cap / dh), "T_dd_h": round(cap / dh / 3600, 2),
                    "meaning": ("LOWER bound on drawdown of a FULL pond at the declared rated outflow of all four "
                                "ST.SPS stations (PROP-FLOOD-08 drawdown_is_lower_bound); conditional on V = declared "
                                "capacity, not the current storage")}
    return {
        "level2_nodes": {k: {kk: v.get(kk) for kk in ("station_code", "value_m", "observed_at", "status_code",
                                                         "warning", "critical", "datum", "suspect", "stale")}
                         for k, v in nodes.items()},
        "level2_edges": [{k: e.get(k) for k in ("edge_id", "status", "refusal_reason", "delta_h", "direction")}
                         for e in (chain or {}).get("edges") or []],
        "saensaeb_suspect_check": (chain or {}).get("saensaeb_suspect_check"),
        "level2_forecast": {"state": "REFUSED", "reason": "NO_LEVEL_FORECAST — no forecast of H at any chain node; "
                            "t_arr REFUSED TAU_UNDECLARED (no declared d_e on any chain edge)"},
        "banma2_line": "NO_NORMAL_BASIS — บ้านม้า 2 has no normal level; its own warning/critical lines are shown, not a band",
        "pumps": pumps, "pumps_on_total": pumps_on, "pump_stations_reporting": pumps_total_stations,
        "pump_sensor_faults": faults,
        "T_dd_effective": {"state": "REFUSED", "reason": "ZERO_OUTFLOW (0 pumps reported running; every ST.SPS row "
                           "carries sensor_status=fault, so '0 running' may be a telemetry fault — not a confirmed stop)"},
        "T_dd_rated_current": {"state": "REFUSED", "reason": "MISSING_INPUT — V_stored undeclared (no stage–storage "
                               "curve for บึงสัมมากร)"},
        "T_dd_rated_full_pond": tdd_full,
        "E_k": {"state": "REFUSED", "reason": "SAFE_STORAGE_UNDECLARED + MISSING_INPUT(storage_state)"},
        "level3_point_depth": {"state": "REFUSED", "reason": "DATUM_UNDECLARED — pond/canal gauges on station-local datum "
                               "(datum null), no ground elevation on the same datum at Sammakorn"},
        "pond_now": {"value_m": pond.get("value_m"), "critical_m": pond.get("critical"), "warning_m": pond.get("warning"),
                     "status": pond.get("status_code"), "observed_at": pond.get("observed_at"),
                     "vs_critical": (zoom_state([("WL.SMK.01@bma_watermap", pond["value_m"])], pond["critical"])
                                     if pond.get("value_m") is not None and pond.get("critical") is not None else None),
                     "single_source_note": "one gauge: strict state forced POSSIBLE by C3; raw comparison shown"},
    }


def write_record(record: dict, out_dir: Path = OUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = out_dir / f"bkk_10day_{stamp}.json"
    if p.exists():  # append-only: never overwrite
        raise FileExistsError(p)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=1, default=str)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-prefix", required=True, help="UTC stamp prefix of the collect sweep, e.g. 2026-09-27T18")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    a = ap.parse_args()
    rec = compute(a.run_prefix)
    p = write_record(rec, Path(a.out_dir))
    print(p)


if __name__ == "__main__":
    main()
