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
KHLONGCHAN_SOCIAL_PATH = RAM53_DIR / "social_timeline_khlongchan_2026-09-26.md"
TIDE_DIR = INPUTS / "tide"
BALANCE_DIR = INPUTS / "areas"                    # *.balance.yaml -- PROP-FLOOD-03 inputs
CANALS_DIR = INPUTS / "canals"                    # *.yaml -- PROP-FLOOD-04 declared graphs
CAPACITY_JSON_PATH = INPUTS / "capacity" / "bma_capacity.json"
OFFICIAL_DIR = INPUTS / "official"
BRIEFING_1300_PATH = OFFICIAL_DIR / "bma_briefing_2026-09-26_1300.json"
BRIEFING_PATH = OFFICIAL_DIR / "bma_briefing_2026-09-26_1615.json"  # newest -- supersedes 13:00 on the hero line

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
RAIN_GAUGE_RADIUS_KM = 4.0     # "3 nearest gauges (<= 4 km)" -- RAIN NOW item

# Design drainage capacity -- VERIFIED against the source document itself (see
# raw/capacity/CAPACITY_NOTE.md, not committed -- it quotes the exact Thai sentence).
# "โดยขีดความสามารถของระบบระบายน้ำสามารถรองรับปริมาณฝนตกสะสมรวมได้ไม่เกิน 80 มิลลิเมตร
# ใน 1 วัน ... หรือแปลงเป็นความเข้มของฝนไม่เกิน 58.7 มิลลิเมตรต่อชั่วโมง"
DESIGN_CAPACITY_MM_PER_HOUR = 58.7
DESIGN_CAPACITY_MM_PER_DAY = 80.0
DESIGN_CAPACITY_SOURCE_TH = ("แผนปฏิบัติราชการประจำปี พ.ศ. 2569 สำนักการระบายน้ำ กทม., "
                              "หน้า 4 (VERIFIED -- อ่านตรงจากเอกสารต้นทาง)")

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
    # collect.py's thaiwater_rain_24h collector (added 2026-09-26, red-team fix HIGH-3)
    # writes a fresh snapshot every run to raw/live/thaiwater_rain_24h/<ts>.json; the
    # raw/gapfill/rain_24h*.json manual snapshot is now only a fallback for a run where
    # that collector hasn't run yet or failed (e.g. local dev, or a CI run before this
    # collector existed).
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


# --- 9c. คลองจั่น/บางกะปิ "เสียงจากอินเทอร์เน็ต" -- คลองจั่นอยู่ในโซ่คลองของราม 53 -----------
#
# Added 2026-09-26 (maintainer request): แฟลตเคหะคลองจั่น is on the same canal chain as ram53
# (แสนแสบ -> คลองจั่น), so its social-media reports are ram53-relevant community signal, and
# a nearby-area sub-line for sammakorn too. Same time/place/state-only, no-personal-name
# discipline as build_ram53_community -- a media OUTLET (สวพ.FM91, PPTV HD 36, The Bangkok
# Insight) is named as an agency, since it published a public byline-free news item, not a
# private individual; a personal Facebook post/page ("Facebook (บุคคล)"/"(เพจ)"/"(คลิป)") is
# never named, same as every other "ชาวบ้านรายงาน" row in this codebase.

_KHLONGCHAN_ROW_RE = _RAM53_ROW_RE  # identical 4-column table shape


def _khlongchan_source_label(raw_source: str) -> str | None:
    """A named media outlet -> its name (agency disclosure); a personal post/page/clip ->
    None (never named). `raw_source` is the table's own "แหล่ง" column text."""
    s = (raw_source or "").strip()
    if not s:
        return None
    if re.search(r"บุคคล|เพจ|คลิป", s):
        return None
    # "The Bangkok Insight / ข่าว" / "PPTV HD 36 / ข่าว" -> drop the generic " / ข่าว" suffix
    s = re.sub(r"\s*/\s*ข่าว\s*$", "", s).strip()
    return s or None


def build_khlongchan_community(social_md_path: Path) -> list[dict]:
    """Returns rows in the table's own (ascending) time order: [{time, place, state}], with
    a named media outlet's name folded into `state` as "... (<outlet>)" -- never a personal
    name. Same table shape as build_ram53_community, reused here rather than re-implemented."""
    if not social_md_path.exists():
        return []
    out = []
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
        source = _khlongchan_source_label(source_raw)
        state_out = f"{state} ({source})" if source else state
        out.append({"time": time_th, "place": strip_house_range(place), "state": state_out})
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


# --- 12. Hourly rain forecast -- Open-Meteo (third-party, open, no key) ------------------
#
# The previous version of this function did one Playwright navigation to Google's
# hourly-precipitation strip; GitHub Actions runners have no Playwright/Chromium install
# by default and no sanctioned reason to scrape Google from CI. Replaced 2026-09-26 with
# collect.py's `collect_openmeteo_forecast` (a plain JSON GET, no key, works fine in CI),
# which writes `raw/live/openmeteo_forecast/<ts>_<area_id>.json` per area. This function
# only READS that cached snapshot -- no network call here, same discipline as every other
# `load_*` function in this file. Still fails soft to "unavailable" if the collector
# hasn't run yet or the snapshot can't be parsed.

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
        # Full hourly series (up to Open-Meteo's forecast_days=3 horizon, ~72h) for the
        # drain-timeline chart's rain-input term -- `hourly` above only keeps 12 rows for
        # the short forecast strip; this keeps everything parse_openmeteo_forecast gave us.
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
    else:
        # fall back to the single-station area forecast (pre-upgrade behaviour) if the
        # 6-model files are unavailable for any reason.
        hourly = (forecast or {}).get("hourly_full") or []
        rain_mm = [h.get("mm") or 0.0 for h in hourly[:n]]
        rain_min = list(rain_mm)
        rain_max = list(rain_mm)
        rain_jma = list(rain_mm)
        forecast_coverage_hours = len(rain_mm)
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
        "rain_source_note_th": ("ฝนมัธยฐาน (median) จาก 6 แบบจำลองเปิด (ECMWF/GFS/ICON/JMA/GEM/"
                                 "Météo-France) ที่จุดสัมมากร ใช้เป็นตัวแทนของทั้งเมือง (proxy)"),
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
    help section's shelters/parking/hotline/school additions -- all declared official_report
    facts from the 26 ก.ย. 2569 16:15 online meeting (BMA governor + Prime Minister), which
    supersedes the 13:00 briefing on the numbers that changed (shelters in-use, roads
    affected) while keeping the same backlog-volume figure (223 million m^3, unchanged).
    Never rephrased into a command (no ห้าม/ไม่ต้อง/ไม่ควร)."""
    if not briefing:
        return None
    facts = briefing.get("declared_facts") or {}

    def v(key):
        return (facts.get(key) or {}).get("value")

    return {
        "briefing_time_bkk": briefing.get("briefing_time_bkk"),
        "hero_line_th": ("กทม. แถลง 16:15: กรมอุตุฯ คาดฝนลดลงตั้งแต่ 27 ก.ย. — "
                          "ถ้าไม่มีฝนเติม สถานการณ์ทยอยคลี่คลาย (น้ำค้าง 223 ล้าน ลบ.ม.)"),
        "weather_system_note_th": v("main_canals_status"),
        "tmd_forecast_note_th": v("tmd_forecast_note"),
        "canals_to_watch": v("canals_to_watch") or [],
        "roads_affected_count": v("main_roads_affected_count"),
        "households_affected_initial_survey": v("households_affected_initial_survey"),
        "health_support_ready": v("health_support_ready"),
        "disaster_response_support": v("disaster_response_support"),
        "shelters": v("shelters"),
        "bedridden_patients_moved": v("bedridden_patients_moved"),
        "hotlines": v("hotlines") or ["1555", "Traffy Fondue", "district office (sandbags)", "1669"],
        "temporary_parking": v("temporary_parking") or [],
        "monday_note_th": v("monday_2026-09-28"),
        "conditional_outlook_th": v("conditional_outlook"),
        "disaster_area_declared": v("disaster_area_declared"),
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
    return out


# --- Water balance (Toledo PROP-FLOOD-03, proposal, PR #60 pending) --------------------

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
    """Load site/inputs/official/bma_briefing_2026-09-26_1615.json (the 2026-09-26 16:15
    online meeting between the BMA governor and the Prime Minister -- newest briefing,
    supersedes the 13:00 one, bma_briefing_2026-09-26_1300.json, on the hero line) --
    declared official_report facts, url OPEN (no direct bangkok.go.th/prbangkok/Facebook
    URL located yet). Returns None on any read failure -- this is reference/hero content,
    never load-bearing for the rest of the build."""
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
                              "ช่วงบนของช่วง (with forecast rain) บวกฝนที่ Open-Meteo (third-party) "
                              "คาดว่าจะตกอีกใน 24 ชม.ข้างหน้าเข้าไปเป็นปริมาณน้ำเพิ่มเติม (upper bound, "
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

    nodes = {}
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
        nodes[nid] = {"label_th": n.get("label_th"), "canal_oldcode": code,
                      "is_gate": bool(n.get("is_gate")), "value_m": value_m,
                      "status": status, "observed_at": observed_at, "stale": stale}
    return {
        "available": True,
        "graph_id": graph.get("graph_id", "east_chain"),
        "epistemic_note_th": graph.get("epistemic_note_th"),
        "sensor_resolution_m": (graph.get("sensor_resolution_m") or {}).get("value"),
        "stale_after_hours": graph.get("stale_after_hours"),
        "nodes": nodes,
        "edges": edges,
        "next_step_th": (graph.get("next_step_th") or "").strip(),
    }


# --- Area builder ---------------------------------------------------------------------

def build_area_data(*, area_id: str, label: str, centre_lat: float, centre_lon: float,
                     generated_at_bkk: str, generated_at_utc_iso: str, now_local,
                     canal_stations: list[dict], canal_by_code: dict,
                     canal_path, pump_station_codes: list[str], tide: dict | None,
                     dds_relevant_names: list[str], is_ram53: bool = False) -> dict:
    pump_rows, pump_path = load_pump_rows(pump_station_codes)
    rain, rain_path = load_rain(generated_at_utc_iso, centre_lat, centre_lon)
    flood_roads, flood_road_path = load_flood_roads(generated_at_utc_iso, centre_lat, centre_lon)
    forecast, forecast_path = load_openmeteo_forecast(area_id, now_local)
    capacity = build_capacity_comparison(rain, forecast)

    upstream_stations = build_upstream_stations(canal_by_code, generated_at_utc_iso, centre_lat, centre_lon)
    upstream_codes = {s["code"] for s in upstream_stations}
    near_stations = build_near_stations(canal_stations, upstream_codes, generated_at_utc_iso,
                                         centre_lat, centre_lon)
    stations_near = near_stations + upstream_stations

    pumps = build_pumps(pump_rows, generated_at_utc_iso, centre_lat, centre_lon)
    dds_quotes, dds_report, dds_pdf_path = build_dds_quotes(dds_relevant_names)
    hospitals = build_hospitals(centre_lat, centre_lon)

    # คลองจั่น/บางกะปิ is on ram53's own canal chain (แสนแสบ -> คลองจั่น) -- its social
    # timeline is ram53-relevant community signal, and a "nearby area" note for sammakorn.
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
        # Newest 3 คลองจั่น/บางกะปิ social-media reports, sammakorn only -- ram53 already has
        # the full khlongchan set folded into `community` above (it's on ram53's own canal
        # chain), so showing it again here would duplicate the same rows.
        "nearby_community": [] if is_ram53 else nearby_community,
        "nearby_community_label": "พื้นที่ใกล้เคียง (บางกะปิ/คลองจั่น)",
    }


# --- main --------------------------------------------------------------------------------

def main():
    now_local = datetime.datetime.now(BANGKOK_TZ)
    generated_at_bkk = now_local.isoformat()
    generated_at_utc_iso = now_local.astimezone(datetime.timezone.utc).isoformat()

    canal_stations, canal_path = load_canal_stations()
    canal_by_code = {s["canal_oldcode"]: s for s in canal_stations if s.get("canal_oldcode")}
    tide, tide_path = load_tide(generated_at_utc_iso)

    dds_names = ["สะพานสูง", "แสนแสบ", "ประเวศ", "วังทองหลาง", "บางกะปิ"]

    sammakorn = build_area_data(
        area_id="sammakorn", label="หมู่บ้านสัมมากร (รามคำแหง 112)",
        centre_lat=13.758235, centre_lon=100.676084,
        generated_at_bkk=generated_at_bkk, generated_at_utc_iso=generated_at_utc_iso,
        now_local=now_local,
        canal_stations=canal_stations, canal_by_code=canal_by_code, canal_path=canal_path,
        pump_station_codes=["ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"],
        tide=tide, dds_relevant_names=dds_names, is_ram53=False,
    )
    ram53 = build_area_data(
        area_id="ram53", label="ซอยรามคำแหง 53",
        centre_lat=13.765540, centre_lon=100.619095,
        generated_at_bkk=generated_at_bkk, generated_at_utc_iso=generated_at_utc_iso,
        now_local=now_local,
        canal_stations=canal_stations, canal_by_code=canal_by_code, canal_path=canal_path,
        pump_station_codes=["ST.WTL.01", "ST.BKP.01", "ST.BKP.06", "ST.BKP.02"],
        tide=tide, dds_relevant_names=dds_names, is_ram53=True,
    )
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
    # (TLS/API-key access this CI environment does not have) -- Open-Meteo above is the
    # stand-in, always labelled third-party. This caveat is surfaced in the sources
    # footer (see build_page.py's sources block), not silently hidden.
    forecast_caveat_th = ("พยากรณ์ฝนที่แสดงมาจาก Open-Meteo (แบบจำลองเปิด third-party) "
                           "เนื่องจากไม่สามารถดึงพยากรณ์อย่างเป็นทางการจากกรมอุตุนิยมวิทยา "
                           "(TMD) ได้ในระบบอัตโนมัตินี้ (ติด TLS/ต้องใช้ API key)")

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
    if briefing_raw:
        all_sources_briefing = {
            "id": "bma_governor_briefing", "agency_th": briefing_raw.get("agency_th"),
            "url": briefing_raw.get("url"), "fetched_at": fetched_at_of(BRIEFING_PATH),
            "trust_tier": "official_report",
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
        "areas": {"sammakorn": sammakorn, "ram53": ram53},
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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
