#!/usr/bin/env python3
"""
build_data.py -- FloodConnect data.json builder (TWO AREAS: หมู่บ้านสัมมากร + ซอยรามคำแหง 53).

READ-ONLY. Never fetches the network EXCEPT the one optional Playwright navigation for
the hourly rain-forecast strip (item D), which fails soft to "no forecast" if Playwright
or the page layout is unavailable. All flood/canal/pump/tide/community data is read from CACHED official snapshots under this
repo's `raw/live/` (produced by `collect.py`, re-fetched every run, never committed) plus the
curated compiled files checked into `site/inputs/`, and writes `data.json` next to this
script.

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
REPO_ROOT = HERE.parent                          # .../repo
RAW = REPO_ROOT / "raw"                          # live snapshots from collect.py (git-ignored)
INPUTS = HERE / "inputs"                         # curated, checked-into-git compiled files
COMMUNITY_DIR = INPUTS / "community"
UPSTREAM_REPORT_PATH = INPUTS / "upstream_watchlist.md"
RAM53_DIR = INPUTS / "ram53"
TIDE_DIR = INPUTS / "tide"

OUT_JSON = HERE / "dist" / "data.json"

_HOUSE_RANGE_RE = re.compile(r"\s*\(\d+\s*[-–]\s*\d+\)")


def strip_house_range(s):
    """Drop trailing/inline house-number ranges like '(251-260)' from a soi/place name --
    they come from raw community reports and are not meaningful once grouped by soi."""
    if not s:
        return s
    return _HOUSE_RANGE_RE.sub("", s).strip()

sys.path.insert(0, str(REPO_ROOT))
try:
    import live_water_level as lwl  # noqa: E402
except Exception as _lwl_exc:  # pragma: no cover - defensive fallback

    class _LwlFallback:
        @staticmethod
        def classify_level(value, warning, critical, bank):
            if value is None:
                return "NO_THRESHOLD"
            if bank is not None and value >= bank:
                return "OVERBANK"
            if critical is not None and value >= critical:
                return "CRITICAL"
            if warning is not None and value >= warning:
                return "WATCH"
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
STALE_HOURS = 2.0
NEAR_STATION_RADIUS_KM = 5.0   # generalised per-centre radius (task spec: stations ≤5 km)
PUMP_RADIUS_KM = 2.5           # generalised per-centre radius (task spec: pumps ≤2.5 km)
FLOOD_ROAD_RADIUS_KM = 5.0
HOSPITAL_RADIUS_KM = 5.0

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

def load_rain(generated_at_utc_iso: str, centre_lat: float, centre_lon: float) -> tuple[dict | None, Path | None]:
    # collect.py's thaiwater_rain_24h collector (added 2026-09-26, red-team fix HIGH-3)
    # writes a fresh snapshot every run to raw/live/thaiwater_rain_24h/<ts>.json; the
    # raw/gapfill/rain_24h*.json manual snapshot is now only a fallback for a run where
    # that collector hasn't run yet or failed (e.g. local dev, or a CI run before this
    # collector existed).
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
    best = None
    best_dist = None
    for rec in rows:
        station = rec.get("station") or {}
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if lat is None or lon is None or rec.get("rain_24h") is None:
            continue
        dist = lwl.haversine_km(centre_lat, centre_lon, float(lat), float(lon))
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = rec
    if best is None:
        return None, path
    station = best.get("station") or {}
    observed_at = to_utc_iso(best.get("rainfall_datetime"), "%Y-%m-%d %H:%M")
    agency_th = ((best.get("agency") or {}).get("agency_name") or {}).get("th")
    return {
        "station": (station.get("tele_station_name") or {}).get("th"),
        "dist_km": round(best_dist, 2) if best_dist is not None else None,
        "mm_24h": best.get("rain_24h"),
        "observed_at": observed_at,
        "agency_th": agency_th,
        "stale": is_stale(observed_at, generated_at_utc_iso),
    }, path


# --- 4. Tide (Royal Thai Navy Hydrographic Dept, astronomical prediction, shared) ---------

def load_tide(generated_at_utc_iso: str) -> tuple[dict | None, Path | None]:
    path = newest_file(TIDE_DIR, "*.json")
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


def build_upstream_stations(canal_by_code: dict, generated_at_utc_iso: str,
                             centre_lat: float, centre_lon: float) -> list[dict]:
    watch = parse_upstream_watchlist(UPSTREAM_REPORT_PATH)
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
            status = lwl.classify_level(
                s["level_m"], s.get("warning_level"), s.get("critical_level"), s.get("bank")
            )
            # Red-team fix MEDIUM-4 (2026-09-26): store the safe-float'd threshold values
            # (None on anything non-numeric), not the raw agency field -- otherwise a
            # downstream f"{x:.2f}" in build_page.py would crash on a non-numeric value
            # that classify_level itself already tolerated.
            entry.update({"value_m": lwl.safe_float(s["level_m"]), "out_m": s.get("canal_out"),
                          "warning": lwl.safe_float(s.get("warning_level")),
                          "critical": lwl.safe_float(s.get("critical_level")),
                          "bank": lwl.safe_float(s.get("bank")), "status": status,
                          "observed_at": s.get("observed_at"),
                          "stale": is_stale(s.get("observed_at"), generated_at_utc_iso)})
        out.append(entry)
    return out


# --- 7. Near-centre canal stations (north/south by latitude) -----------------------------

def build_near_stations(canal_stations: list[dict], exclude_codes: set,
                         generated_at_utc_iso: str, centre_lat: float, centre_lon: float,
                         radius_km: float = NEAR_STATION_RADIUS_KM) -> list[dict]:
    out = []
    for s in canal_stations:
        code = s.get("canal_oldcode")
        if not code or code in exclude_codes:
            continue
        dist = lwl.haversine_km(centre_lat, centre_lon, s["lat"], s["lon"])
        if dist > radius_km:
            continue
        status = lwl.classify_level(
            s["level_m"], s.get("warning_level"), s.get("critical_level"), s.get("bank")
        )
        # Red-team fix MEDIUM-4 (2026-09-26): safe-float the stored thresholds too --
        # see build_upstream_stations's identical comment above.
        out.append({
            "code": code, "name": s.get("name_th"), "dist_km": round(dist, 2),
            "value_m": lwl.safe_float(s["level_m"]), "out_m": s.get("canal_out"),
            "warning": lwl.safe_float(s.get("warning_level")),
            "critical": lwl.safe_float(s.get("critical_level")),
            "bank": lwl.safe_float(s.get("bank")), "status": status,
            "observed_at": s.get("observed_at"),
            "stale": is_stale(s.get("observed_at"), generated_at_utc_iso),
            "role": "north" if s["lat"] >= centre_lat else "south",
        })
    out.sort(key=lambda r: r["dist_km"])
    return out


# --- 8. Pumps ------------------------------------------------------------------------------

def build_pumps(pump_rows: list[dict], generated_at_utc_iso: str,
                 centre_lat: float, centre_lon: float,
                 radius_km: float = PUMP_RADIUS_KM) -> list[dict]:
    out = []
    for r in pump_rows:
        dist_m = None
        if r.get("lat") is not None and r.get("lon") is not None:
            dist_m = round(
                lwl.haversine_km(centre_lat, centre_lon, r["lat"], r["lon"]) * 1000.0, 0
            )
        if dist_m is not None and dist_m > radius_km * 1000.0:
            continue
        out.append({
            "code": r["station_code"], "name": r.get("name_th"), "dist_m": dist_m,
            "level_m": r.get("level_m"), "pumps_on": r.get("pumps_on"),
            "pumps_total": r.get("pumps_total"), "gate": r.get("gate_open"),
            "status_th": r.get("status_th"), "observed_at": r.get("observed_at"),
            "stale": is_stale(r.get("observed_at"), generated_at_utc_iso),
            "pond_name": POND_NAME_BY_PUMP_CODE.get(r["station_code"]),
        })
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
    yaml_path = newest_file(COMMUNITY_DIR, "soi_tiers_*.yaml")
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

    csv_path = newest_file(COMMUNITY_DIR, "low_areas_*.csv")
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


def build_ram53_community(social_md_path: Path) -> list[dict]:
    if not social_md_path.exists():
        return []
    out = []
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
        out.append({"time": time_th, "place": strip_house_range(place), "state": state})
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


def build_exits_ram53() -> list[dict]:
    return [{
        "name": "ปากซอยด้านใต้",
        "status_from_reports": "ออก ถ.รามคำแหง (ยังไม่ยืนยันจากแผนที่)",
        "is_community_report": False, "report_date_th": None, "report_time_th": None,
    }]


# --- 10b. Hospitals (Overpass cache, ≤5km else []) -----------------------------------------

HEALTH_OVERPASS_PATH = INPUTS / "health_overpass.json"
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
    # collect.py writes the live PDF to raw/live/dds_daily_pdf/<timestamp>.pdf
    # (see collect.py's _cache_raw); raw/dds_reports/ is a manual/legacy drop
    # location kept only as a fallback so an older manually-placed file still
    # works (2026-09-26 red-team fix -- these two paths had silently diverged).
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


# --- 12. Hourly rain forecast -- UNAVAILABLE in the automated CI path -----------------
#
# The previous version of this function did one Playwright navigation to Google's
# hourly-precipitation strip. GitHub Actions runners have no Playwright/Chromium install
# by default and no sanctioned reason to scrape Google from CI, so that fetch has been
# removed here. `forecast` is always the fail-soft "unavailable" readout below; every place
# it is shown is already labelled accordingly (see DATA_README.md).

_FORECAST_UNAVAILABLE = {
    "available": False,
    "status": "ยังไม่มีพยากรณ์ฝนรายชั่วโมง — ดูเรดาร์ กทม.",
    "items": [],
    "source": None,
    "trust_tier": None,
    "direction": "unavailable",
}


def fetch_forecast_short() -> dict:
    """Always returns the fail-soft unavailable readout (see module docstring above)."""
    return dict(_FORECAST_UNAVAILABLE)


# --- Sources ---------------------------------------------------------------------------

def build_sources(rain: dict | None, canal_path, pump_path, rain_path, flood_road_path,
                   dds_pdf_path, tide_path, community_path, community_agency: str,
                   community_id: str = "community_reports") -> list[dict]:
    return [
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


# --- Area builder ---------------------------------------------------------------------

def build_area_data(*, area_id: str, label: str, centre_lat: float, centre_lon: float,
                     generated_at_bkk: str, generated_at_utc_iso: str,
                     canal_stations: list[dict], canal_by_code: dict,
                     canal_path, pump_station_codes: list[str], tide: dict | None,
                     dds_relevant_names: list[str], is_ram53: bool = False) -> dict:
    pump_rows, pump_path = load_pump_rows(pump_station_codes)
    rain, rain_path = load_rain(generated_at_utc_iso, centre_lat, centre_lon)
    flood_roads, flood_road_path = load_flood_roads(generated_at_utc_iso, centre_lat, centre_lon)

    upstream_stations = build_upstream_stations(canal_by_code, generated_at_utc_iso, centre_lat, centre_lon)
    upstream_codes = {s["code"] for s in upstream_stations}
    near_stations = build_near_stations(canal_stations, upstream_codes, generated_at_utc_iso,
                                         centre_lat, centre_lon)
    stations_near = near_stations + upstream_stations

    pumps = build_pumps(pump_rows, generated_at_utc_iso, centre_lat, centre_lon)
    dds_quotes, dds_report, dds_pdf_path = build_dds_quotes(dds_relevant_names)
    hospitals = build_hospitals(centre_lat, centre_lon)

    if is_ram53:
        tiers, tiers_note = [], "ยังไม่มีรายงานรายซอย — ใช้รายงานถนนรามคำแหง/หน้า ม.ราม แทน"
        exits = build_exits_ram53()
        community = build_ram53_community(RAM53_DIR / "social_timeline_2026-09-26.md")
        community_label = "จุด"
        community_path = RAM53_DIR / "social_timeline_2026-09-26.md"
        community_agency = ("เสียงจากอินเทอร์เน็ต (โพสต์สาธารณะที่ค้นเจอผ่าน Google -- ไม่ใช่หน่วยงานราชการ, "
                             "ไม่เก็บชื่อผู้โพสต์)")
    else:
        tiers, tiers_note = build_tiers_sammakorn()
        exits = build_exits_sammakorn(COMMUNITY_DIR / "community_reports_2026-09-26.md")
        community = build_community_from_tiers(tiers)
        community_label = "ซอย"
        community_path = COMMUNITY_DIR / "community_reports_2026-09-26.md"
        community_agency = "ชาวบ้านรายงาน (กลุ่มชุมชนออนไลน์ในหมู่บ้าน -- ไม่ใช่หน่วยงานราชการ, ไม่เก็บชื่อผู้โพสต์)"

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
                             community_id=("community_reports_ram53" if is_ram53 else "community_reports"))

    return {
        "label": label,
        "centre": {"lat": centre_lat, "lon": centre_lon, "label": label},
        "sources": sources,
        "stations_near": stations_near,
        "pumps": pumps,
        "rain": rain,
        "tide": tide,
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
    }


# --- main --------------------------------------------------------------------------------

def main():
    now_local = datetime.datetime.now(BANGKOK_TZ)
    generated_at_bkk = now_local.isoformat()
    generated_at_utc_iso = now_local.astimezone(datetime.timezone.utc).isoformat()

    canal_stations, canal_path = load_canal_stations()
    canal_by_code = {s["canal_oldcode"]: s for s in canal_stations if s.get("canal_oldcode")}
    tide, tide_path = load_tide(generated_at_utc_iso)
    forecast = fetch_forecast_short()

    dds_names = ["สะพานสูง", "แสนแสบ", "ประเวศ", "วังทองหลาง", "บางกะปิ"]

    sammakorn = build_area_data(
        area_id="sammakorn", label="หมู่บ้านสัมมากร (รามคำแหง 112)",
        centre_lat=13.758235, centre_lon=100.676084,
        generated_at_bkk=generated_at_bkk, generated_at_utc_iso=generated_at_utc_iso,
        canal_stations=canal_stations, canal_by_code=canal_by_code, canal_path=canal_path,
        pump_station_codes=["ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"],
        tide=tide, dds_relevant_names=dds_names, is_ram53=False,
    )
    ram53 = build_area_data(
        area_id="ram53", label="ซอยรามคำแหง 53",
        centre_lat=13.765540, centre_lon=100.619095,
        generated_at_bkk=generated_at_bkk, generated_at_utc_iso=generated_at_utc_iso,
        canal_stations=canal_stations, canal_by_code=canal_by_code, canal_path=canal_path,
        pump_station_codes=["ST.WTL.01", "ST.BKP.01", "ST.BKP.06", "ST.BKP.02"],
        tide=tide, dds_relevant_names=dds_names, is_ram53=True,
    )
    # Ram53's rain-forecast card notes it borrows the nearest official district forecast.
    ram53["rain_forecast_area_note"] = "พยากรณ์ของเขตสะพานสูง (ใกล้เคียง)"

    all_sources = []
    seen_ids = set()
    for ad in (sammakorn, ram53):
        for s in ad["sources"]:
            if s["id"] in seen_ids:
                continue
            seen_ids.add(s["id"])
            all_sources.append(s)
    if forecast.get("available"):
        all_sources.append({
            "id": "google_weather_forecast", "agency_th": "Google Weather (weather.com) — ไม่ใช่หน่วยงานรัฐไทย",
            "url": "https://www.google.com/search?q=พยากรณ์อากาศ+สะพานสูง+กรุงเทพ",
            "fetched_at": generated_at_utc_iso, "trust_tier": "third_party_forecast",
        })

    data = {
        "generated_at_bkk": generated_at_bkk,
        "epistemic_note": "เป็นการอ่านค่าจากหน่วยงาน ไม่ใช่การพยากรณ์",
        "default_area": "sammakorn",
        "forecast": forecast,
        "all_sources": all_sources,
        "areas": {"sammakorn": sammakorn, "ram53": ram53},
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {
        "forecast_available": forecast["available"],
        "areas": {},
    }
    for aid, ad in data["areas"].items():
        by_status = {}
        for s in ad["stations_near"]:
            by_status[s["status"]] = by_status.get(s["status"], 0) + 1
        counts["areas"][aid] = {
            "sources": len(ad["sources"]), "stations_near": len(ad["stations_near"]),
            "stations_near_by_status": by_status, "pumps": len(ad["pumps"]),
            "rain": 1 if ad["rain"] else 0,
            "tide_next_high": len((ad["tide"] or {}).get("next_high", [])),
            "flood_roads": len(ad["flood_roads"]), "tiers": len(ad["tiers"]),
            "dds_quotes": len(ad["dds_quotes"]), "exits": len(ad["exits"]),
            "hospitals": len(ad["hospitals"]), "community": len(ad["community"]),
            "staleness_banner": ad["staleness"]["banner"],
        }
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
