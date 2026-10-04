#!/usr/bin/env python3
"""
Physical flood-management asset registry -- harvest + build + query CLI.

Founder priority (verbatim, 2026-09-27): "ข้อมูลจากภาครัฐเชื่อมได้ทั้งหมด ให้เน้นข้อมูลที่
เชื่อถือได้ โดยเฉพาะตำแหน่งก่อน" then "แล้วค่อยวางระบบเรื่องข้อมูลอัพเดท" -- ONE authoritative
registry of physical flood-management assets (gauges, pump stations, gates, tunnels,
dams, culverts, ponds, control centres) with coordinates, each row provable from an
official source. No guessing, no geocoding, no OSM for coordinates.

Schema/vocabulary reference: sources/assets_registry.yaml. Storage: the `assets` +
`assets_log` tables in store.py (append-only additions to that module; see its own
"Assets registry" section) plus a regenerated YAML dump at
`data/assets_registry.dump.yaml` (gitignored, like the sqlite db itself).

Sources read (all from the local raw cache -- see `_freshest_cache_file` below for the
6h-staleness / at-most-one-request discipline):
  - raw/live/thaiwater_bma/*.json          -- BMA canal gauges + gates (is_gate rows)
  - raw/live/thaiwater_rain_24h/*.json     -- rain gauges, filtered to a Bangkok-metro
                                               bounding box (the raw feed is nationwide)
  - raw/live/pumphistory/*.html            -- BMA pump stations (embedded `datapump`)
  - raw/gapfill/water_station.csv          -- dds.bangkok.go.th open dataset (438 rows)
  - site/inputs/canals/control_structures.yaml -- 4 declared gates, cross-checked
                                               against thaiwater_bma by canal_oldcode
  - raw/live/thaiwater_waterlevel/*.json   -- nationwide HII telemetry gauges (~804
                                               stations, api-v3.thaiwater.net
                                               thaiwater30/public/waterlevel)
  - raw/live/rid_res_table/*.html          -- RID national large-dam name list (33
                                               dams by region; no coordinate published
                                               on the page, stored OPEN)
  - raw/live/hii_dam/*.json                -- HII dam/reservoir census (dam_hourly,
                                               dam_daily, dam_medium, dam_small_tele),
                                               real lat/lon on nearly every row -- used
                                               both as its own dam/reservoir_medium/
                                               reservoir_small rows AND to fill the 35
                                               RID res_table dams' coordinates (see
                                               _merge_hii_dam_into_rid_res_table)
  - raw/live/hii_watergate/*.json          -- HII watergate_data census (2,315 rows
                                               nationwide) -- gate/pump_station/weir
                                               rows, deduped against existing BMA gate
                                               rows by name+distance

No flood-risk score or formula is computed here (this workspace's equation-discipline
rule) -- every stored value is a relayed/measured reading or a declared identity field,
never derived.

CLI:
    python3 assets_registry.py build
    python3 assets_registry.py list --class gate
    python3 assets_registry.py near 13.758235 100.676084 --km 3
    python3 assets_registry.py stats
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import math
import re
import sys
from pathlib import Path

import yaml

import store

HERE = Path(__file__).parent
RAW_LIVE_DIR = HERE / "raw" / "live"
RAW_GAPFILL_DIR = HERE / "raw" / "gapfill"
CONTROL_STRUCTURES_YAML = HERE / "site" / "inputs" / "canals" / "control_structures.yaml"
YAML_DUMP_PATH = HERE / "data" / "assets_registry.dump.yaml"

MAX_CACHE_AGE_HOURS = 6.0

# Bangkok-metro bounding box used to cut the nationwide rain_24h feed (~4,300 stations
# nationwide) down to the ones relevant to a Bangkok flood-asset registry. Declared
# here, not fabricated per-station -- a station outside this box is simply not
# harvested by this registry, not marked OPEN (it isn't one of "our" assets).
BANGKOK_BBOX = {"lat_min": 13.4, "lat_max": 14.1, "lon_min": 100.2, "lon_max": 100.95}

CONTRADICTION_DISTANCE_M = 200.0


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km, stdlib only (math)."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def _freshest_cache_file(dir_path: Path, glob_pattern: str) -> Path | None:
    """Returns the newest file matching `glob_pattern` in `dir_path`, or None if the
    directory has no matching file at all. Does NOT itself decide staleness -- see
    `_cache_is_fresh` -- kept separate so a caller can still read a stale cache rather
    than silently harvesting nothing.
    """
    if not dir_path.exists():
        return None
    files = sorted(dir_path.glob(glob_pattern))
    return files[-1] if files else None


def _cache_is_fresh(path: Path, max_age_hours: float = MAX_CACHE_AGE_HOURS) -> bool:
    if path is None or not path.exists():
        return False
    age_h = (datetime.datetime.now().timestamp() - path.stat().st_mtime) / 3600.0
    return age_h <= max_age_hours


def _load_freshest_or_refetch(source_dir_name: str, glob_pattern: str, fetch_fn):
    """Cache-first: read the newest cached file if it's within MAX_CACHE_AGE_HOURS.
    Only if it's missing or stale does this call `fetch_fn()` (which itself performs
    AT MOST ONE network request, per this repo's live_water_level.py/collect.py
    no-retry discipline) to refresh the cache, then re-reads the newest file.
    Returns (path, is_fresh_from_cache: bool) or (None, False) if nothing usable.
    """
    d = RAW_LIVE_DIR / source_dir_name
    path = _freshest_cache_file(d, glob_pattern)
    if _cache_is_fresh(path):
        return path, True
    if fetch_fn is None:
        return path, False
    try:
        fetch_fn()
    except Exception as e:  # pragma: no cover -- network path, not exercised in tests
        print(f"[assets_registry] refetch for {source_dir_name} failed: {e}",
              file=sys.stderr)
        return path, False
    path = _freshest_cache_file(d, glob_pattern)
    return path, _cache_is_fresh(path)


# --- harvesters --------------------------------------------------------------------

def harvest_thaiwater_bma(path: Path) -> list:
    """BMA canal gauges + gates (station.canal_lat/canal_long) -> asset dicts.
    A record with no coordinate is skipped, never fabricated (same discipline as
    live_water_level.py's parse_thaiwater_canal_stations)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("canal_lat"), station.get("canal_long")
        if lat is None or lon is None:
            continue
        name_th = (station.get("canal_name") or {}).get("th")
        code = station.get("canal_oldcode") or (
            f"id{station.get('id')}" if station.get("id") is not None else None)
        if not code:
            continue
        is_gate = bool(name_th) and name_th.startswith("ปตร.")
        klass = "gate" if is_gate else "gauge"
        agency = ((rec.get("agency") or {}).get("agency_name") or {})
        owner = agency.get("th") or agency.get("en")
        out.append({
            "asset_id": f"{klass}:thaiwater_bma:{code}",
            "class": klass,
            "name_th": name_th,
            "source_code": code,
            "lat": float(lat),
            "lon": float(lon),
            "coord_source": "raw/live/thaiwater_bma (api-v3.thaiwater.net canal_waterlevel)",
            "coord_source_type": "official_api",
            "owner": owner,
            "owner_source": "thaiwater_bma API agency field",
            "warning_level": station.get("warning_level"),
            "critical_level": station.get("critical_level"),
            "bank": station.get("bank"),
            "tag": "VERIFIED",
            "notes": None,
        })
    return out


def harvest_rain_24h(path: Path, bbox: dict = BANGKOK_BBOX) -> list:
    """Rain gauges (nationwide feed), filtered to the Bangkok-metro bounding box."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if lat is None or lon is None:
            continue
        lat, lon = float(lat), float(lon)
        if not (bbox["lat_min"] <= lat <= bbox["lat_max"]
                and bbox["lon_min"] <= lon <= bbox["lon_max"]):
            continue
        code = station.get("tele_station_oldcode") or (
            f"id{station.get('id')}" if station.get("id") is not None else None)
        if not code:
            continue
        name_th = (station.get("tele_station_name") or {}).get("th")
        agency = ((rec.get("agency") or {}).get("agency_name") or {})
        owner = agency.get("th") or agency.get("en")
        out.append({
            "asset_id": f"gauge:thaiwater_rain:{code}",
            "class": "gauge",
            "name_th": name_th,
            "source_code": code,
            "lat": lat,
            "lon": lon,
            "coord_source": "raw/live/thaiwater_rain_24h (api-v3.thaiwater.net rain_24h)",
            "coord_source_type": "official_api",
            "owner": owner,
            "owner_source": "thaiwater_rain_24h API agency field",
            "tag": "VERIFIED",
            "notes": "rain_24h gauge, Bangkok-metro bounding box filter applied",
        })
    return out


_PUMP_DATAPUMP_RE = re.compile(r"var datapump\s*=\s*(\[.*?\]);", re.S)


def harvest_pumphistory(path: Path) -> list:
    """BMA PumpHistory embedded `datapump` JS array -> pump_station asset dicts. Real
    lat/lon from the page's own static metadata array, not a fuzzy join."""
    html = Path(path).read_text(encoding="utf-8", errors="replace")
    m = _PUMP_DATAPUMP_RE.search(html)
    if not m:
        return []
    try:
        records = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    out = []
    for rec in records:
        code = rec.get("pumpStation_code")
        lat, lon = rec.get("latitude"), rec.get("longitude")
        if not code or lat is None or lon is None:
            continue
        out.append({
            "asset_id": f"pump_station:pumphistory:{code}",
            "class": "pump_station",
            "name_th": rec.get("pumpStation_name"),
            "source_code": code,
            "lat": float(lat),
            "lon": float(lon),
            "coord_source": "raw/live/pumphistory (weather.bangkok.go.th datapump array)",
            "coord_source_type": "official_page",
            "owner": "สำนักการระบายน้ำ กรุงเทพมหานคร",
            "owner_source": "pumphistory page (BMA-operated system)",
            "pumps_total": rec.get("pump_count"),
            "capacity_m3s": rec.get("pump_capacity"),
            "tag": "VERIFIED",
            "notes": f"district: {rec.get('district_name')}",
        })
    return out


_GP_TYPE_TO_CLASS = {
    "บ่อสูบน้ำ": "pump_station",
    "ประตูระบายน้ำ": "gate",
}


def _parse_capacity_number(raw: str) -> float | None:
    """water_station.csv's gp_total_capacity/gp_pump cells sometimes hold a multi-line
    freeform string like '45\\n 35(3)+10(5)' -- only the first clean numeric token is
    taken (a stated headline figure), never summed/guessed from the parenthetical
    breakdown. Returns None if no clean leading number is found."""
    if not raw:
        return None
    first_line = raw.strip().splitlines()[0].strip()
    m = re.match(r"[-+]?\d+(\.\d+)?", first_line)
    return float(m.group(0)) if m else None


def harvest_water_station_csv(path: Path) -> list:
    """dds.bangkok.go.th open dataset (raw/gapfill/water_station.csv) -> pump_station /
    gate asset dicts."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            klass = _GP_TYPE_TO_CLASS.get(row.get("gp_type"))
            if klass is None:
                continue
            try:
                lat, lon = float(row["gp_lat"]), float(row["gp_long"])
            except (KeyError, TypeError, ValueError):
                continue
            gp_id = row.get("gp_id")
            entry = {
                "asset_id": f"{klass}:water_station:{gp_id}",
                "class": klass,
                "name_th": row.get("gp_name"),
                "source_code": gp_id,
                "lat": lat,
                "lon": lon,
                "coord_source": "raw/gapfill/water_station.csv (dds.bangkok.go.th open dataset)",
                "coord_source_type": "official_dataset",
                "owner": (row.get("district") or "").strip() or "สำนักการระบายน้ำ กรุงเทพมหานคร",
                "owner_source": "water_station.csv district field",
                "warning_level": _parse_capacity_number(row.get("gp_warning", "")),
                "critical_level": _parse_capacity_number(row.get("gp_critical", "")),
                "tag": "VERIFIED",
                "notes": None,
                "_gp_type": row.get("gp_type"),
            }
            if klass == "pump_station":
                entry["pumps_total"] = None
                cap = _parse_capacity_number(row.get("gp_total_capacity", ""))
                # KNOWN ISSUE (TODO #51, 2026-09-27): for 91 of these
                # water_station.csv rows, this `gp_total_capacity` headline number is
                # actually the PUMP COUNT, not m3/s (cross-checked against the BMA
                # 2569 plan p.170-208, e.g. อุโมงค์บางซื่อ parses here as 6 but the
                # plan states 60 m3/s from 6 machines). Those 91 rows were corrected
                # by hand directly in data/observations.sqlite's `assets` table (old
                # value moved to `capacity_m3s_suspect_count`, plan value written to
                # `capacity_m3s`, tag VERIFIED) -- a fresh full re-harvest of this CSV
                # via `python3 assets_registry.py build` WILL overwrite `capacity_m3s`
                # back to the suspect count for those asset_ids (upsert_asset()'s own
                # ON CONFLICT clause always sets capacity_m3s=excluded.capacity_m3s).
                # This parser itself is not changed here (no per-row plan lookup
                # wired in yet) -- re-apply the correction from
                # docs/knowledge/bma_plan2569_control_structures.yaml's `repo_match`
                # rows after any future full rebuild, or wire that cross-check into
                # this function properly, before trusting a fresh capacity_ledger sum.
                entry["capacity_m3s"] = cap
            out.append(entry)
    return out


def harvest_control_structures(path: Path, thaiwater_bma_by_code: dict) -> list:
    """The 4 declared gates in control_structures.yaml, cross-checked against the
    thaiwater_bma feed by canal_oldcode. When a match is found (all 4 resolved as of
    2026-09-27), the coordinate is VERIFIED (comes from the official API, not a
    hand-entered guess) -- this function returns an enrichment note merged onto the
    existing thaiwater_bma asset_id, not a second competing row. A structure whose
    code does NOT resolve would instead be returned as its own repo_declared row (none
    fell into that branch as of this build)."""
    if not path.exists():
        return []
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    structures = doc.get("structures") or {}
    out = []
    for key, s in structures.items():
        code = s.get("canal_oldcode")
        if not code:
            continue
        label = s.get("label_th")
        match = thaiwater_bma_by_code.get(code)
        if match:
            out.append({
                "asset_id": match["asset_id"],
                "class": match["class"],
                "name_th": match["name_th"],
                "source_code": code,
                "lat": match["lat"],
                "lon": match["lon"],
                "coord_source": match["coord_source"],
                "coord_source_type": match["coord_source_type"],
                "owner": match["owner"],
                "owner_source": match["owner_source"],
                "tag": "VERIFIED",
                "notes": (f"cross-checked: site/inputs/canals/control_structures.yaml "
                          f"structure '{key}' ({label}); source note: {s.get('source')}"),
            })
        else:
            out.append({
                "asset_id": f"gate:control_structures:{key}",
                "class": "gate",
                "name_th": label,
                "source_code": code,
                "lat": None,
                "lon": None,
                "coord_source": "site/inputs/canals/control_structures.yaml",
                "coord_source_type": "repo_declared",
                "owner": None,
                "owner_source": None,
                "tag": "OPEN",
                "notes": (f"declared structure '{key}' with canal_oldcode {code}, not "
                          f"found in the cached thaiwater_bma feed at build time"),
            })
    return out


def harvest_thaiwater_waterlevel(path: Path, bbox: dict | None = None) -> list:
    """Nationwide HII telemetry water-level stations (api-v3.thaiwater.net
    thaiwater30/public/waterlevel -- probed 2026-09-27 per founder ask "แม่น้ำ ... ครบ
    หรือยัง"; `dam_daily`/`dam_medium`/`dam`/`waterlevel_dam` all returned 404 "Unknown
    service id" on the same host at that probe, see docs/ASSETS.md's probe log -- no
    dedicated dam-reservoir endpoint was found within the 6-probe budget). This is
    river/canal telemetry (`station_type` == "tele_waterlevel"), not a dam-specific
    feed -- several station names contain "เขื่อน" (e.g. "ท้ายเขื่อนเจ้าพระยา") but those
    are gauges sited downstream/upstream OF a dam, not the dam/reservoir asset itself,
    so they are stored here as class `gauge`, never re-labelled `dam`.

    `bbox`, if given, restricts to that lat/lon box (same convention as
    `harvest_rain_24h`); default None = nationwide (this is the whole point of this
    harvester -- the existing thaiwater_bma/rain_24h harvesters are Bangkok-scoped,
    this one is the nationwide fill)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if lat is None or lon is None:
            continue
        lat, lon = float(lat), float(lon)
        if bbox and not (bbox["lat_min"] <= lat <= bbox["lat_max"]
                          and bbox["lon_min"] <= lon <= bbox["lon_max"]):
            continue
        code = station.get("tele_station_oldcode") or (
            f"id{station.get('id')}" if station.get("id") is not None else None)
        if not code:
            continue
        name_th = (station.get("tele_station_name") or {}).get("th")
        agency = ((rec.get("agency") or {}).get("agency_name") or {})
        owner = agency.get("th") or agency.get("en")
        basin = ((rec.get("basin") or {}).get("basin_name") or {}).get("th")
        out.append({
            "asset_id": f"gauge:thaiwater_waterlevel:{code}",
            "class": "gauge",
            "name_th": name_th,
            "source_code": code,
            "lat": lat,
            "lon": lon,
            "coord_source": "raw/live/thaiwater_waterlevel (api-v3.thaiwater.net thaiwater30/public/waterlevel)",
            "coord_source_type": "official_api",
            "owner": owner,
            "owner_source": "thaiwater_waterlevel API agency field",
            "warning_level": station.get("warning_level_m"),
            "critical_level": station.get("critical_level_m"),
            "bank": station.get("left_bank"),
            "tag": "VERIFIED",
            "notes": (f"nationwide HII telemetry station"
                      + (f"; basin: {basin}" if basin else "")),
        })
    return out


_RID_RES_TABLE_REGION_RE = re.compile(r'<p[^>]*>(ภาค[^<]+)</p>\s*<ul[^>]*>(.*?)</ul>', re.S)
_RID_RES_TABLE_NAME_RE = re.compile(r'class="highslide">([^<]+)</a>')


def harvest_rid_res_table(path: Path) -> list:
    """RID's national large-dam table page (water.rid.go.th/flood/flood/res_table.htm,
    probed 2026-09-27) -- an old (~2008-era) reservoir-chart index page that lists 33
    named large dams by RID region with links to historical level-chart images, but
    publishes NO coordinate anywhere on the page (checked by reading the full decoded
    HTML, not assumed). Per this check's rule ("if only names, ingest names with coord
    OPEN"), every dam here is stored with lat=lon=None, tag OPEN -- never geocoded."""
    if not path.exists():
        return []
    html = Path(path).read_bytes().decode("cp874", errors="replace")
    out = []
    for region_th, block in _RID_RES_TABLE_REGION_RE.findall(html):
        for name_th in _RID_RES_TABLE_NAME_RE.findall(block):
            out.append({
                "asset_id": f"dam:rid_res_table:{name_th}",
                "class": "dam",
                "name_th": name_th,
                "source_code": None,
                "lat": None,
                "lon": None,
                "coord_source": None,
                "coord_source_type": "none",
                "owner": "กรมชลประทาน (RID)",
                "owner_source": "raw/live/rid_res_table (water.rid.go.th/flood/flood/res_table.htm)",
                "tag": "OPEN",
                "notes": (f"RID region: {region_th}; large-dam reservoir-chart index "
                          f"page names this dam but publishes no lat/lon anywhere on "
                          f"the page (checked, not assumed) -- coordinate OPEN, no "
                          f"geocoding performed"),
            })
    return out


_HII_DAM_LIST_TO_CLASS = {
    "dam_hourly": "dam",
    "dam_daily": "dam",
    "dam_medium": "reservoir_medium",
    "dam_small_tele": "reservoir_small",
}

# Sanity bounding box for Thailand used only as a test/QA guard against a harvester
# accidentally emitting a coordinate that could not possibly be inside the country
# (e.g. a swapped lat/lon or a stray 0,0) -- NOT used to filter/cut real rows the way
# BANGKOK_BBOX cuts rain_24h; a real official coordinate outside this box would be
# a data-quality finding to report, not silently dropped.
THAILAND_BBOX = {"lat_min": 5.5, "lat_max": 20.6, "lon_min": 97.3, "lon_max": 105.7}


def _valid_th_coord(lat, lon) -> bool:
    """True only for a coordinate that could plausibly be a real Thailand reading.
    Rejects None (never a coordinate) and (0, 0) (a common government-feed sentinel
    for "no reading", not an Atlantic-Ocean asset -- found live in the 2026-09-27
    hii_watergate payload, station BKK007) and anything outside THAILAND_BBOX (also
    found live: station TN.10 reports tele_station_lat=118.58928, a clear decimal-
    place data error in HII's own feed, ~18.6 being the plausible Nan-province value).
    A harvester never GUESSES the correct value -- it downgrades the row to OPEN and
    notes the raw bad value for traceability, per this repo's no-geocoding rule."""
    if lat is None or lon is None:
        return False
    if lat == 0 and lon == 0:
        return False
    return (THAILAND_BBOX["lat_min"] <= lat <= THAILAND_BBOX["lat_max"]
            and THAILAND_BBOX["lon_min"] <= lon <= THAILAND_BBOX["lon_max"])


def _dam_subrecord_coord(dam: dict) -> tuple:
    """dam_hourly/dam_daily/dam_medium use dam_lat/dam_long; dam_small_tele uses
    tele_station_lat/tele_station_long. Returns (lat, lon) as floats, or (None, None)
    if either half is missing -- never geocoded/guessed."""
    lat = dam.get("dam_lat", dam.get("tele_station_lat"))
    lon = dam.get("dam_long", dam.get("tele_station_long"))
    if lat is None or lon is None:
        return None, None
    lat, lon = float(lat), float(lon)
    if not _valid_th_coord(lat, lon):
        return None, None
    return lat, lon


def harvest_hii_dam(path: Path) -> list:
    """HII's dam census (raw/live/hii_dam/*.json, from
    raw/knowledge/api_census/hii/dam.json -- {"data": {"dam_hourly", "dam_medium",
    "dam_daily", "dam_small_tele"}}) -> dam / reservoir_medium / reservoir_small asset
    dicts. Founder ask 2026-09-27: "เอาพิกัดจากเว็บไซต์รัฐมีเยอะ" -- this is HII's own
    dam/reservoir census with real lat/lon on nearly every row (unlike RID's
    res_table.htm page, which names dams but publishes no coordinate at all -- see
    harvest_rid_res_table above).

    `dam_hourly`/`dam_daily` -> class `dam` (large dams, RID/EGAT-operated).
    `dam_medium` -> class `reservoir_medium`. `dam_small_tele` -> class
    `reservoir_small` (both new vocabulary entries, see sources/assets_registry.yaml).
    A row with no lat/lon (a handful of `dam_medium` rows) is tagged OPEN, never
    geocoded -- same discipline as every other harvester here. `dam.id` (the nested
    dam-record's own stable id, not the outer per-reading `id`) is used as the asset
    code so repeated hourly/daily polls of the SAME dam+agency collapse to one row,
    while a different agency reporting the same-named dam under its own `dam.id`
    (e.g. RID's "ภูมิพล" id=1 vs EGAT's id=43) stays a separate row/asset_id -- same
    keep-both-don't-guess-a-winner posture as `_merge_pumphistory_and_water_station`'s
    contradiction handling."""
    if not path.exists():
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    data = payload.get("data", {})
    out = []
    for list_name, klass in _HII_DAM_LIST_TO_CLASS.items():
        for rec in data.get(list_name, []) or []:
            dam = rec.get("dam") or {}
            dam_id = dam.get("id")
            if dam_id is None:
                continue
            code = str(dam_id)
            name_th = (dam.get("dam_name") or dam.get("smalldam_name") or {}).get("th")
            lat, lon = _dam_subrecord_coord(dam)
            agency = ((rec.get("agency") or {}).get("agency_name") or {})
            owner = agency.get("th") or agency.get("en")
            geocode = rec.get("geocode") or {}
            province_th = (geocode.get("province_name") or {}).get("th")
            basin = ((rec.get("basin") or {}).get("basin_name") or {}).get("th")
            has_coord = lat is not None and lon is not None
            notes_bits = [f"HII {list_name} census row"]
            if province_th:
                notes_bits.append(f"province: {province_th}")
            if basin:
                notes_bits.append(f"basin: {basin}")
            if not has_coord:
                notes_bits.append("no lat/lon on this HII row -- coordinate OPEN, not geocoded")
            out.append({
                "asset_id": f"{klass}:hii_dam:{code}",
                "class": klass,
                "name_th": name_th,
                "source_code": code,
                "lat": lat,
                "lon": lon,
                "coord_source": ("raw/live/hii_dam (HII dam census, "
                                  "api-v3.thaiwater.net/thaiwater30 dam family)"
                                  if has_coord else None),
                "coord_source_type": "official_api" if has_coord else "none",
                "owner": owner,
                "owner_source": "hii_dam census agency field",
                "province": province_th,
                "tag": "VERIFIED" if has_coord else "OPEN",
                "notes": "; ".join(notes_bits),
            })
    return out


_DAM_NAME_STRIP_WORDS = ("เขื่อน", "อ่างเก็บน้ำ", "คลอง")


def _normalize_dam_name(name: str | None) -> str:
    """Confident-match-only normalization for matching a dam name across RID's
    res_table.htm names (e.g. "สียัด", "วชิราลงกรณ์") and HII's dam-census names (e.g.
    "คลองสียัด", "วชิราลงกรณ") -- strips the common descriptive prefixes/words this
    repo's own dam lists were seen to differ by (checked against the real 2026-09-27
    payloads, not guessed), the thanthakhat mark, and all whitespace. Never a fuzzy/
    edit-distance match -- only exact-after-normalization or clean substring below."""
    if not name:
        return ""
    s = name
    for w in _DAM_NAME_STRIP_WORDS:
        s = s.replace(w, "")
    s = s.replace("์", "")  # thanthakhat (การันต์)
    s = re.sub(r"\s+", "", s)
    return s.strip()


def _merge_hii_dam_into_rid_res_table(hii_dam_rows: list, rid_dam_rows: list,
                                       still_open_out: list) -> list:
    """RID's res_table.htm names 35 large dams with NO coordinate published anywhere
    on the page (harvest_rid_res_table, tag OPEN). HII's dam census (harvest_hii_dam,
    class `dam` rows only -- i.e. dam_hourly/dam_daily, the large-dam lists, never
    reservoir_medium/reservoir_small) DOES publish real lat/lon for the same physical
    dams under a different name spelling/agency. Matched by
    `_normalize_dam_name` (exact-after-normalization, or a clean substring either
    way -- never geocoded, never a fuzzy/edit-distance guess). On a confident match,
    the RID row is returned with lat/lon filled and tag bumped to VERIFIED, noting
    "coords from hii_dam, name from rid_res_table". An RID dam with no confident match
    is returned UNCHANGED (still OPEN) and also appended to `still_open_out` so the
    caller/docs can list exactly which ones remain open. A RID-agency HII row is
    preferred over an EGAT one when both match the same RID name (RID names its own
    dams; EGAT's parallel reporting of the same physical dam is a separate asset row
    already kept in `hii_dam_rows`, untouched by this function)."""
    hii_dam_only = [r for r in hii_dam_rows if r["class"] == "dam" and r.get("lat") is not None]
    by_norm: dict = {}
    for r in hii_dam_only:
        by_norm.setdefault(_normalize_dam_name(r.get("name_th")), []).append(r)

    out = []
    for rid_row in rid_dam_rows:
        n = _normalize_dam_name(rid_row.get("name_th"))
        hits = []
        for hn, rows in by_norm.items():
            if not hn or not n:
                continue
            if hn == n or (len(n) >= 3 and n in hn) or (len(hn) >= 3 and hn in n):
                hits.extend(rows)
        if not hits:
            out.append(rid_row)
            still_open_out.append(rid_row.get("name_th"))
            continue
        rid_agency_hits = [h for h in hits if h.get("owner") and "ชลประทาน" in h["owner"]]
        pick = rid_agency_hits[0] if rid_agency_hits else hits[0]
        merged = dict(rid_row)
        merged["lat"] = pick["lat"]
        merged["lon"] = pick["lon"]
        merged["coord_source"] = pick.get("coord_source")
        merged["coord_source_type"] = pick.get("coord_source_type")
        merged["tag"] = "VERIFIED"
        merged["notes"] = (
            (merged.get("notes") or "").rstrip("; ")
            + "; coords from hii_dam, name from rid_res_table"
              f" (hii name: {pick.get('name_th')}, hii owner: {pick.get('owner')})"
        ).lstrip("; ")
        out.append(merged)
    return out


_HII_WATERGATE_PUMP_WORD = "สูบน้ำ"
_HII_WATERGATE_WEIR_WORD = "ฝาย"


def _classify_hii_watergate_row(name_th: str | None) -> str:
    """Name-based classification (this feed carries no separate structure-type field,
    checked against the real payload, not assumed) -- "สูบน้ำ" (pump) -> pump_station,
    "ฝาย" (weir) -> weir, everything else defaults to class `gate` per this check's
    instruction (the endpoint is itself named `watergate_data`)."""
    name_th = name_th or ""
    if _HII_WATERGATE_PUMP_WORD in name_th:
        return "pump_station"
    if _HII_WATERGATE_WEIR_WORD in name_th:
        return "weir"
    return "gate"


def harvest_hii_watergate(path: Path) -> list:
    """HII's watergate census (raw/live/hii_watergate/*.json, from
    raw/knowledge/api_census/hii/watergate_load.json's `watergate_data.data`, 2,315
    rows nationwide) -> gate / pump_station / weir asset dicts. Each row's own
    `station` sub-object carries the real lat/lon (`tele_station_lat`/
    `tele_station_long`), an oldcode, and a `geocode.province_name` -- the sibling
    top-level `station`/`province` lists in the same file are reference lookups only,
    not iterated here (checked against the real payload: `watergate_data.data[i]`
    already embeds everything needed per row). A row with no lat/lon (149 of 2,315 in
    the 2026-09-27 payload) is tagged OPEN, never geocoded. Two more rows in that same
    payload carry a lat/lon that is present but not a plausible Thailand reading --
    station BKK007 reports (0, 0) (a sentinel, not a real point) and station TN.10
    reports tele_station_lat=118.58928 (a clear decimal-place error in HII's own feed,
    ~18.6 being the plausible Nan-province value) -- `_valid_th_coord` downgrades both
    to OPEN rather than storing a coordinate this repo already knows is wrong, and the
    raw rejected value is kept in `notes` for traceability, never corrected/guessed.

    The asset code is keyed on `station.id` (checked: unique across all 2,315 rows in
    the 2026-09-27 payload), never on `tele_station_oldcode` -- that field was found to
    be REUSED across two entirely different stations from two different agencies in
    this same payload (oldcode "E21" is both a RID river gauge on the Chi river and a
    BMA gate in Lat Krabang, ~370 km apart); keying on oldcode would have silently
    collapsed the two into one row via upsert-by-asset_id. `station.id == 0` (139 rows
    in the 2026-09-27 payload, every one with no name/oldcode/coordinate at all) is
    treated the same as a missing id -- skipped, not stored as a fake asset."""
    if not path.exists():
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = ((payload.get("watergate_data") or {}).get("data")) or []
    out = []
    for rec in rows:
        station = rec.get("station") or {}
        station_id = station.get("id")
        if not station_id:  # None or 0 -- both mean "no usable station identity" here
            continue
        oldcode = station.get("tele_station_oldcode")
        code = str(station_id)
        name_th = (station.get("tele_station_name") or {}).get("th")
        klass = _classify_hii_watergate_row(name_th)
        raw_lat, raw_lon = station.get("tele_station_lat"), station.get("tele_station_long")
        lat = float(raw_lat) if raw_lat is not None else None
        lon = float(raw_lon) if raw_lon is not None else None
        has_coord = _valid_th_coord(lat, lon)
        agency = ((rec.get("agency") or {}).get("agency_name") or {})
        owner = agency.get("th") or agency.get("en")
        geocode = rec.get("geocode") or {}
        province_th = (geocode.get("province_name") or {}).get("th")
        basin = ((rec.get("basin") or {}).get("basin_name") or {}).get("th")
        notes_bits = ["HII watergate_data census row"]
        if oldcode:
            notes_bits.append(f"oldcode: {oldcode}")
        if province_th:
            notes_bits.append(f"province: {province_th}")
        if basin:
            notes_bits.append(f"basin: {basin}")
        if not has_coord:
            if lat is not None and lon is not None:
                notes_bits.append(
                    f"HII reported an implausible coordinate ({lat}, {lon}) -- "
                    f"rejected by _valid_th_coord (outside Thailand/sentinel 0,0), "
                    f"coordinate OPEN, never corrected/guessed")
            else:
                notes_bits.append("no lat/lon on this HII row -- coordinate OPEN, not geocoded")
        out.append({
            "asset_id": f"{klass}:hii_watergate:{code}",
            "class": klass,
            "name_th": name_th,
            "source_code": code,
            "lat": lat if has_coord else None,
            "lon": lon if has_coord else None,
            "coord_source": ("raw/live/hii_watergate (HII watergate_data census, "
                              "api-v3.thaiwater.net/thaiwater30 family)" if has_coord else None),
            "coord_source_type": "official_api" if has_coord else "none",
            "owner": owner,
            "owner_source": "hii_watergate census agency field",
            "province": province_th,
            "warning_level": station.get("warning_level_m"),
            "critical_level": station.get("critical_level_m"),
            "tag": "VERIFIED" if has_coord else "OPEN",
            "notes": "; ".join(notes_bits),
        })
    return out


def harvest_rain_gauge_nationwide(path: Path) -> list:
    """Nationwide rain gauges from the SAME feed harvest_rain_24h reads
    (raw/live/thaiwater_rain_24h/*.json, ~4,300+ stations), but WITHOUT the
    Bangkok-metro bounding-box filter -- founder ask 2026-09-27 ("rain_gauge
    NATIONWIDE ... register ALL stations with coordinates"). Kept as its own class
    (`rain_gauge`) and its own asset_id namespace
    (`rain_gauge:thaiwater_rain_24h:<station.id>`) rather than widening
    harvest_rain_24h's existing `gauge:thaiwater_rain:*` rows -- those stay
    Bangkok-scoped and unchanged, this is a strict addition. Keyed on `station.id`
    (not `tele_station_oldcode`), matching the collision-avoidance discipline
    `harvest_hii_watergate` already established (an oldcode CAN repeat across
    stations in these HII-family feeds). Tag `VERIFIED` (real lat/lon read directly
    off this official API payload, same convention as the HII dam/watergate rows)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        raw_lat, raw_lon = station.get("tele_station_lat"), station.get("tele_station_long")
        if raw_lat is None or raw_lon is None:
            continue
        lat, lon = float(raw_lat), float(raw_lon)
        if not _valid_th_coord(lat, lon):
            continue
        sid = station.get("id")
        if not sid:
            continue
        code = str(sid)
        name_th = (station.get("tele_station_name") or {}).get("th")
        agency = ((rec.get("agency") or {}).get("agency_name") or {})
        owner = agency.get("th") or agency.get("en")
        basin = ((rec.get("basin") or {}).get("basin_name") or {}).get("th")
        geocode = rec.get("geocode") or {}
        province_th = (geocode.get("province_name") or {}).get("th")
        out.append({
            "asset_id": f"rain_gauge:thaiwater_rain_24h:{code}",
            "class": "rain_gauge",
            "name_th": name_th,
            "source_code": station.get("tele_station_oldcode") or code,
            "lat": lat,
            "lon": lon,
            "coord_source": "raw/live/thaiwater_rain_24h (api-v3.thaiwater.net rain_24h, nationwide)",
            "coord_source_type": "official_api",
            "owner": owner,
            "owner_source": "thaiwater_rain_24h API agency field",
            "tag": "VERIFIED",
            "notes": ("nationwide rain gauge (no bounding-box filter), keyed on "
                      "station.id, not tele_station_oldcode (oldcode reuse across "
                      "distinct stations was already found in this feed family)"
                      + (f"; province: {province_th}" if province_th else "")
                      + (f"; basin: {basin}" if basin else "")),
        })
    return out


_BASIN_EXCLUDE_CODES = {99, 88}  # "99 ไม่ระบุ" (unspecified) / "88 นอกประเทศไทย" (outside
                                  # Thailand) -- both found in the real payloads,
                                  # neither is one of the 22 official named basins


def _iter_basin_bearing_records(payload: dict) -> list:
    """Flatten any of this repo's three already-cached HII/thaiwater payload shapes
    down to a list of records that may carry a top-level `basin` field: watergate's
    `watergate_data.data[]`, hii_dam's `data.{dam_hourly,dam_medium,dam_daily,
    dam_small_tele}[]` (a dict of lists), or rain_24h/waterlevel's plain `data[]`."""
    if "watergate_data" in payload:
        return ((payload.get("watergate_data") or {}).get("data")) or []
    data = payload.get("data")
    if isinstance(data, dict):
        out = []
        for v in data.values():
            if isinstance(v, list):
                out.extend(v)
        return out
    if isinstance(data, list):
        return data
    return []


def harvest_basins(paths: list) -> list:
    """The 22 official ONWR/HII main river basins (`ลุ่มน้ำหลัก`), founder ask
    2026-09-27 -- extracted from the `basin.basin_code`/`basin.basin_name.th` field
    that is ALREADY embedded in every record of this repo's cached
    thaiwater_rain_24h / thaiwater_waterlevel / hii_dam / hii_watergate payloads (no
    new network probe needed -- the official 22-basin classification is already
    sitting in data this registry harvests for other classes). Basin code 99
    ("ไม่ระบุ" / unspecified) is excluded, leaving exactly the 22 named basins. No
    polygon/point geometry is attempted here (a basin is an area, not a point) --
    every row's lat/lon stays None; see docs/ASSETS.md for the geometry-OPEN note
    and the "probe once for an official GeoJSON" rule this check follows (no such
    download was performed this check)."""
    basins: dict = {}
    for path in paths:
        if not path or not Path(path).exists():
            continue
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for rec in _iter_basin_bearing_records(payload):
            b = rec.get("basin") or {}
            code = b.get("basin_code")
            name = (b.get("basin_name") or {}).get("th")
            if code is None or code in _BASIN_EXCLUDE_CODES or not name:
                continue
            basins.setdefault(code, name)
    out = []
    for code in sorted(basins):
        out.append({
            "asset_id": f"basin:onwr:{code}",
            "class": "basin",
            "name_th": basins[code],
            "source_code": str(code),
            "lat": None,
            "lon": None,
            "coord_source": None,
            "coord_source_type": "none",
            "owner": None,
            "owner_source": ("basin_code/basin_name field embedded in this repo's own "
                              "cached HII API payloads (rain_24h/waterlevel/hii_dam/"
                              "hii_watergate) -- the official 22-ลุ่มน้ำหลัก classification"),
            "tag": "VERIFIED",
            "notes": ("basin identity/code VERIFIED from an official HII API payload "
                      "already cached in this repo (not re-probed); no polygon/point "
                      "geometry attempted this check -- geometry OPEN, no official "
                      "GeoJSON/WFS downloaded"),
        })
    return out


def hand_declared_retention_basins() -> list:
    """RID's official 12 ทุ่งรับน้ำ (lower-Chao-Phraya monkey-cheek rice fields, below
    Nakhon Sawan) -- names + provinces read from the real archived article text
    (raw/knowledge/retention_basins/thaipbs_266415.html, fetched 2026-09-27, Thai PBS
    citing RID; NOT from this check's own web-search summary, which was cross-checked
    against and disagreed slightly with the actual article body, so the article text
    itself was re-extracted and used instead) -- plus the 2 aggregate RID/BMA
    monkey-cheek SCHEMES (east/west of the Chao Phraya) named in
    docs/knowledge/card_pidthong_kaemling_royal_initiative.md. No individual site
    coordinate is published in either source -- every row here is lat=lon=None, tag
    RELAYED (news/foundation article, not a structured official feed, per this
    repo's own tag_vocabulary). The pidthong card's aggregate BMA figure ("20 sites,
    10,062,525 ลบ.ม.") has NO per-site names/coordinates in the source read, so it is
    NOT registered as individual rows here -- see docs/ASSETS.md's OPEN note."""
    rows = []
    twelve_thung = [
        ("01_chiangrak", "ทุ่งเชียงราก", "สิงห์บุรี"),
        ("02_chainat_pasak_left", "ทุ่งฝั่งซ้ายคลองชัยนาท-ป่าสัก", None),
        ("03_thawung", "ทุ่งท่าวุ้ง", "ลพบุรี"),
        ("04_bangkum", "ทุ่งบางกุ่ม", None),
        ("05_bangkung", "ทุ่งบางกุ้ง", None),
        ("06_pamok", "ทุ่งป่าโมก", "อ่างทอง"),
        ("07_phakhai", "ทุ่งผักไห่", None),
        ("08_chaochet", "ทุ่งเจ้าเจ็ด", None),
        ("09_phrayabanlue", "ทุ่งพระยาบรรลือ", None),
        ("10_phophraya", "ทุ่งโพธิ์พระยา", None),
        ("11_bangban", "ทุ่งบางบาล", "พระนครศรีอยุธยา"),
        ("12_rangsittai", "ทุ่งรังสิตใต้", None),
    ]
    for key, name, prov in twelve_thung:
        rows.append({
            "asset_id": f"retention_basin:thaipbs_12thung:{key}",
            "class": "retention_basin",
            "name_th": name,
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "กรมชลประทาน (RID)",
            "owner_source": ("Thai PBS news article citing RID, "
                              "raw/knowledge/retention_basins/thaipbs_266415.html "
                              "(https://www.thaipbs.or.th/news/content/266415)"),
            "tag": "RELAYED",
            "notes": (f"one of RID's 12 ทุ่งรับน้ำ เจ้าพระยาตอนล่าง (below Nakhon Sawan); "
                      f"province: {prov or 'not stated in this source'}; no coordinate "
                      f"published in this news source -- OPEN"),
        })
    for key, name in [
        ("east", "โครงการแก้มลิงฝั่งตะวันออกของแม่น้ำเจ้าพระยา"),
        ("west", "โครงการแก้มลิงฝั่งตะวันตกของแม่น้ำเจ้าพระยา"),
    ]:
        rows.append({
            "asset_id": f"retention_basin:pidthong_scheme:{key}",
            "class": "retention_basin",
            "name_th": name,
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "สำนักการระบายน้ำ กรุงเทพมหานคร / กรมชลประทาน",
            "owner_source": "docs/knowledge/card_pidthong_kaemling_royal_initiative.md",
            "tag": "RELAYED",
            "notes": ("aggregate RID/BMA monkey-cheek scheme (multi-province, "
                      "multi-canal chain), not a single physical site -- no individual "
                      "coordinate published anywhere read for this check"),
        })
    return rows


def hand_declared_tunnels_bma_dds() -> list:
    """BMA DDS's own official tunnel document -- fetched once 2026-09-27
    (dds.bangkok.go.th/public_content/files/001/0004953_1.pdf, HTTP 200), archived at
    raw/knowledge/bma_dds_tunnels/0004953_1.pdf (+ .txt extraction). Lists 7 operating
    + 6 planned/under-construction large drainage tunnels; the document publishes NO
    coordinate anywhere (checked against the full extracted text) -- every row here
    is lat=lon=None, tag OPEN, same convention as this registry's pre-existing
    tunnel:hand_declared:rama9_ramkhamhaeng row. One of the 7 operating tunnels
    ("อุโมงค์ระบายน้ำบึงมักกะสันลงสู่แม่น้ำเจ้าพระยา", diameter 4.60 m, length 5.98 km) is
    the SAME physical asset as that pre-existing row (identical diameter/length) --
    not duplicated here; see hand_declared_open()'s own updated note instead."""
    operating = [
        ("sukhumvit26", "สถานีสูบน้ำและอุโมงค์ระบายน้ำซอยสุขุมวิท 26",
         "diameter 1.00 m, length ~1.10 km, capacity 4 m^3/s; แก้ปัญหาน้ำท่วมถนนสุขุมวิท "
         "ระหว่างซอย 22-28"),
        ("khlong_prem_diversion", "ระบบผันน้ำคลองเปรมประชากร (บางซื่อ/จตุจักร/หลักสี่/"
         "บางเขน/ดอนเมือง)",
         "diameter 3.40 m, length ~1.88 km, capacity 30 m^3/s; ครอบคลุมพื้นที่ ~3.50 ตร.กม."),
        ("sukhumvit36", "สถานีสูบน้ำและอุโมงค์ระบายน้ำซอยสุขุมวิท 36",
         "diameter 1.80 m, length 1.32 km, capacity 6 m^3/s"),
        ("sukhumvit42", "สถานีสูบน้ำและอุโมงค์ระบายน้ำซอยสุขุมวิท 42",
         "diameter 1.80 m, length 1.10 km, capacity 6 m^3/s"),
        ("phayathai", "ระบบระบายน้ำพื้นที่เขตพญาไท (ถนนพหลโยธิน/พระราม 6)",
         "diameters 2.40 m (~679 m) + 1.50 m (~1.90 km), capacity 4.50 m^3/s; "
         "ครอบคลุมพื้นที่ ~3 ตร.กม."),
        ("saensaeb_ladprao", "อุโมงค์ระบายน้ำคลองแสนแสบและคลองลาดพร้าวลงสู่แม่น้ำเจ้าพระยา",
         "diameter 5.00 m, length ~5.11 km, capacity 60 m^3/s; ครอบคลุมพื้นที่ ~50 ตร.กม."),
    ]
    planned = [
        ("bangsue", "อุโมงค์ระบายน้ำใต้คลองบางซื่อ จากคลองลาดพร้าวถึงแม่น้ำเจ้าพระยา (เกียกกาย)",
         "diameter 5.00 m, length ~6.40 km, pump 60 m^3/s, budget 2,422.50 ล้านบาท "
         "(กทม. 50% รัฐบาล 50%); under construction, expected complete ต้นปี 2560"),
        ("nongbon", "อุโมงค์ระบายน้ำจากบึงหนองบอนลงสู่แม่น้ำเจ้าพระยา",
         "diameter 5.00 m, length ~9.40 km, pump 60 m^3/s, budget 4,925.665 ล้านบาท "
         "(งบ กทม.); under construction, expected complete ภายใน 2562"),
        ("prem_bangbua", "อุโมงค์ระบายน้ำคลองเปรมประชากรจากคลองบางบัวลงสู่แม่น้ำเจ้าพระยา "
         "(สะพานพระราม 7)",
         "diameter 5.70 m, length ~13.50 km, pump 60 m^3/s, estimated budget "
         "7,300 ล้านบาท; still in preliminary survey/design, budget-allocation stage "
         "at time of document, expected start 2561 / complete 2564"),
        ("saensaeb_ext", "อุโมงค์ระบายน้ำคลองแสนแสบส่วนต่อขยาย (ถึงซอยลาดพร้าว 130)",
         "diameter 3.60 m, length ~3.80 km, capacity 30 m^3/s, budget 1,526 ล้านบาท; "
         "design complete, awaiting budget allocation, expected start 2561 / "
         "complete 2563"),
        ("taweewatthana", "อุโมงค์ระบายน้ำคลองทวีวัฒนาบริเวณคอขวด",
         "diameter >= 3.70 m, length ~2.03 km, capacity 32 m^3/s, budget 2,274.20 "
         "ล้านบาท; design complete, awaiting government subsidy, expected start 2560 "
         "/ complete 2563"),
        ("phraya_ratchamontri", "อุโมงค์ระบายน้ำคลองพระยาราชมนตรี (คลองภาษีเจริญ-คลองสนามชัย)",
         "diameter >= 5.00 m, length ~8.95 km, pump 48 m^3/s, budget 4,580 ล้านบาท; "
         "feasibility study complete, awaiting design budget, expected start 2560 / "
         "complete 2564"),
    ]
    out = []
    for key, name, notes in operating:
        out.append({
            "asset_id": f"tunnel:bma_dds:{key}",
            "class": "tunnel",
            "name_th": name,
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "สำนักการระบายน้ำ กรุงเทพมหานคร",
            "owner_source": ("official BMA DDS document (dds.bangkok.go.th/"
                              "public_content/files/001/0004953_1.pdf), fetched "
                              "2026-09-27, archived raw/knowledge/bma_dds_tunnels/"),
            "tag": "OPEN",
            "notes": f"status: operating; {notes}; no coordinate published in the source document",
        })
    for key, name, notes in planned:
        out.append({
            "asset_id": f"tunnel:bma_dds:{key}",
            "class": "tunnel",
            "name_th": name,
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "สำนักการระบายน้ำ กรุงเทพมหานคร",
            "owner_source": ("official BMA DDS document (dds.bangkok.go.th/"
                              "public_content/files/001/0004953_1.pdf), fetched "
                              "2026-09-27, archived raw/knowledge/bma_dds_tunnels/"),
            "tag": "OPEN",
            "notes": (f"status: planned/under construction (as of document date); "
                      f"{notes}; no coordinate published in the source document"),
        })
    return out


def hand_declared_levees() -> list:
    """Two named levees already declared as governance_dag nodes in
    docs/knowledge/water_system_dag.mmd (lat/lon null there too) -- registered here
    as their own `levee`-class asset rows per founder ask, still tag OPEN (no
    official coordinate found in any source read for this registry)."""
    return [
        {
            "asset_id": "levee:water_system_dag:king_dike_east",
            "class": "levee",
            "name_th": "คันกั้นน้ำพระราชดำริฝั่งตะวันออก",
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": None,
            "owner_source": "docs/knowledge/water_system_dag.mmd (node AS_KING_DIKE)",
            "tag": "OPEN",
            "notes": "royal-initiative levee, east side -- no coordinate in any source read",
        },
        {
            "asset_id": "levee:water_system_dag:ramkhamhaeng_road",
            "class": "levee",
            "name_th": "ถนนรามคำแหง (ทำหน้าที่คันกั้นน้ำ)",
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": None,
            "owner_source": "docs/knowledge/water_system_dag.mmd (node AS_RAM_ROAD)",
            "tag": "OPEN",
            "notes": ("Ramkhamhaeng road functions as a de facto levee -- no "
                      "coordinate in any source read"),
        },
    ]


def hand_declared_diversion_channels() -> list:
    """คลองผันน้ำยม-น่าน 2/3/4 -- named in this repo's own thaiwater_waterlevel feed as
    telemetry-GAUGE rows (gauge:thaiwater_waterlevel:DIV002/3/4, already VERIFIED via
    harvest_thaiwater_waterlevel). Registered here ADDITIONALLY as their own
    `diversion_channel`-class rows (the physical channel, distinct from the point
    gauge sited on it) per founder ask -- the channel's OWN geometry/coordinate (as
    opposed to its gauge's point reading) is not published anywhere read for this
    task, so lat/lon stays None/OPEN; the cross-reference to the VERIFIED gauge is
    kept in notes instead of borrowing its coordinate for a different asset class."""
    out = []
    for n, gauge_code in [(2, "DIV002"), (3, "DIV003"), (4, "DIV004")]:
        out.append({
            "asset_id": f"diversion_channel:thailand_water_kg:yom_nan{n}",
            "class": "diversion_channel",
            "name_th": f"คลองผันน้ำยม-น่าน{n}",
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "สถาบันสารสนเทศทรัพยากรน้ำ (องค์การมหาชน)",
            "owner_source": ("output/thailand_water_kg.jsonld node name; a telemetry "
                              f"gauge sited on this same channel is already VERIFIED "
                              f"in this registry as gauge:thaiwater_waterlevel:{gauge_code}"),
            "tag": "OPEN",
            "notes": (f"physical diversion-channel structure itself has no separate "
                      f"official coordinate read for this check; NOT borrowing the "
                      f"gauge:thaiwater_waterlevel:{gauge_code} point reading here to "
                      f"avoid conflating a point measurement with the channel's own "
                      f"geometry"),
        })
    return out


def hand_declared_tide_gates() -> list:
    """ประตูระบายน้ำคุ้งบางกระเจ้า, Samut Prakan -- 34 individual tide/flow-control
    gates built by the Dept. of Public Works and Town & Country Planning, handed to
    Samut Prakan province then to 6 tambon administrations. Direct fetch of the
    thaigov.go.th news page returned a 307 redirect (archived, not followed --
    no-retry rule); the name/count/owner detail below comes from this check's own
    web-search summary of that same government news page, so tag RELAYED (not
    VERIFIED -- not independently re-read from the raw article body). No individual
    gate name/coordinate list found -- ONE scheme-level row (34 gates), lat/lon
    None/OPEN."""
    return [{
        "asset_id": "tide_gate:thaigov_news:bang_krachao",
        "class": "tide_gate",
        "name_th": "ประตูระบายน้ำคุ้งบางกระเจ้า (34 ประตู)",
        "source_code": None, "lat": None, "lon": None,
        "coord_source": None, "coord_source_type": "none",
        "owner": ("กรมโยธาธิการและผังเมือง / อบต. 6 แห่ง (บางยอ, บางกะเจ้า, บางกอบัว, "
                   "บางน้ำผึ้ง, บางกระสอบ, ทรงคนอง)"),
        "owner_source": ("thaigov.go.th news (https://www.thaigov.go.th/news/contents/"
                          "details/91012); direct fetch archived as a 307 redirect at "
                          "raw/knowledge/tide_gate_bang_krachao/thaigov_91012.html"),
        "tag": "RELAYED",
        "notes": ("34 flood/salt-water-intrusion control gates in Bang Krachao, "
                  "Samut Prakan -- aggregate scheme, no individual gate list/"
                  "coordinate found in this check's probe budget"),
    }]


def hand_declared_open() -> list:
    """Assets this repo's docs/DAG rely on (canal_graph, water_balance, burden_ledger)
    that have NO coordinate in any source read for this registry. Listed OPEN rather
    than guessed/geocoded -- see docs/ASSETS.md."""
    return [
        {
            "asset_id": "tunnel:hand_declared:rama9_ramkhamhaeng",
            "class": "tunnel",
            "name_th": "อุโมงค์พระราม 9-รามคำแหง",
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "สำนักการระบายน้ำ กรุงเทพมหานคร", "owner_source": "site/dist/data.json capacity_records",
            "tag": "OPEN",
            "notes": ("diameter 4.60 m, length 5.98 km (site/dist/data.json "
                      "tunnel_phra_ram9_ramkhamhaeng_capacity); no coordinate or "
                      "capacity m^3/s found in any source read for this check. "
                      "Confirmed 2026-09-27 (this check) as the SAME physical tunnel "
                      "as the official BMA DDS document's item 6, \"อุโมงค์ระบายน้ำ"
                      "บึงมักกะสันลงสู่แม่น้ำเจ้าพระยา\" (diameter 4.60 m, length "
                      "5.98 km, capacity 45 m^3/s) -- see hand_declared_tunnels_bma_dds() "
                      "and raw/knowledge/bma_dds_tunnels/0004953_1.pdf; not duplicated "
                      "as a second row"),
        },
        {
            "asset_id": "pond:hand_declared:sammakorn",
            "class": "pond",
            "name_th": "บึงสัมมากร",
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": "นิติบุคคลหมู่บ้านสามัคคี (private village)",
            "owner_source": "site/inputs/canals/east_chain.yaml node sammakorn_pond note",
            "tag": "OPEN",
            "notes": ("no public gauge/coordinate; private village retention pond, "
                      "not found in thaiwater_bma, pumphistory, or water_station.csv"),
        },
        {
            "asset_id": "culvert:hand_declared:ramkhamhaeng",
            "class": "culvert",
            "name_th": "ท่อลอดรามคำแหง",
            "source_code": None, "lat": None, "lon": None,
            "coord_source": None, "coord_source_type": "none",
            "owner": None, "owner_source": None,
            "tag": "OPEN",
            "notes": "no coordinate/official record found in any source read for this check",
        },
    ]
    # NOTE: site/inputs/areas/sammakorn.balance.yaml's C_pump field claims ST.SPS.01-04
    # are "NOT FOUND in either raw/gapfill/pump_stations_full.json ... or
    # water_station.csv -- they are private, not registered publicly." That claim does
    # NOT hold against the pumphistory cache read for THIS registry (2026-09-27): all
    # four codes ARE present in pumphistory's embedded `datapump` array with real
    # lat/lon (harvest_pumphistory() above finds them as
    # pump_station:pumphistory:ST.SPS.0[1-4], tag VERIFIED). Not re-declared OPEN here
    # -- doing so would contradict data this same build actually read. See
    # docs/ASSETS.md for the discrepancy note against sammakorn.balance.yaml.


# --- merge / contradiction detection ------------------------------------------------

def _merge_pumphistory_and_water_station(pumphistory_rows: list, water_station_rows: list,
                                          contradictions_out: list) -> tuple:
    """Same asset present in PumpHistory and water_station.csv, matched by an exact
    Thai station-name string (no fuzzy/geocoded matching) -> merged into ONE row that
    keeps both source refs, using pumphistory's own coordinate (kept as-is; not
    averaged/altered). If the two sources' coordinates disagree by more than
    CONTRADICTION_DISTANCE_M, both are still kept but a row is appended to
    `contradictions_out` for store.insert_contradiction.

    Returns (merged_pump_station_rows, unmatched_water_station_rows).
    """
    by_name = {r["name_th"]: r for r in pumphistory_rows if r.get("name_th")}
    merged = []
    unmatched = []
    matched_names = set()
    for ws in water_station_rows:
        if ws["class"] != "pump_station":
            unmatched.append(ws)
            continue
        ph = by_name.get(ws["name_th"])
        if ph is None:
            unmatched.append(ws)
            continue
        matched_names.add(ws["name_th"])
        dist_km = haversine_km(ph["lat"], ph["lon"], ws["lat"], ws["lon"])
        if dist_km * 1000.0 > CONTRADICTION_DISTANCE_M:
            contradictions_out.append({
                "topic": f"asset_coordinate:{ph['asset_id']}",
                "source_a": "pumphistory", "value_a": f"{ph['lat']},{ph['lon']}",
                "source_b": "water_station", "value_b": f"{ws['lat']},{ws['lon']}",
                "note": (f"{ws['name_th']}: pumphistory vs water_station.csv "
                         f"coordinates differ by {dist_km:.3f} km"),
            })
        combined = dict(ph)
        combined["notes"] = (
            (combined.get("notes") or "")
            + f"; also present in water_station.csv (gp_id={ws['source_code']})"
        ).strip("; ")
        if combined.get("capacity_m3s") is None and ws.get("capacity_m3s") is not None:
            combined["capacity_m3s"] = ws["capacity_m3s"]
        merged.append(combined)
    # pumphistory rows never matched by name pass through unchanged
    for ph in pumphistory_rows:
        if ph.get("name_th") not in matched_names:
            merged.append(ph)
    return merged, unmatched


def _merge_hii_watergate_gates(hii_gate_rows: list, existing_gate_rows: list) -> list:
    """Dedup HII's `gate`-class watergate rows against this registry's existing BMA
    gate rows (thaiwater_bma + control_structures + water_station.csv), per this
    task's rule: match by exact Thai name, and (when both sides have a coordinate)
    within ~0.5 km. On a match, the EXISTING row is kept (mutated in place to note the
    HII station id, never replaced/duplicated) and the HII row is dropped; otherwise
    the HII row is returned as a brand-new row. `existing_gate_rows`' dicts are
    mutated in place (they are the same dict objects already destined for `all_rows`
    via their own harvester's list) -- this function's return value is ONLY the new
    rows to add, never a full list, so a caller must not also re-append
    `existing_gate_rows`."""
    new_rows = []
    for hg in hii_gate_rows:
        name = hg.get("name_th")
        matched = None
        if name:
            for e in existing_gate_rows:
                if e.get("name_th") != name:
                    continue
                if hg.get("lat") is not None and e.get("lat") is not None:
                    if haversine_km(hg["lat"], hg["lon"], e["lat"], e["lon"]) <= 0.5:
                        matched = e
                        break
                elif hg.get("lat") is None and e.get("lat") is None:
                    matched = e
                    break
        if matched is not None:
            note_bit = f"also present in HII watergate_data (station id {hg.get('source_code')})"
            existing_notes = matched.get("notes") or ""
            if "HII watergate_data" not in existing_notes:
                matched["notes"] = (existing_notes + "; " + note_bit).strip("; ")
        else:
            new_rows.append(hg)
    return new_rows


# --- build ---------------------------------------------------------------------------

def _drop_private_keys(row: dict) -> dict:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def build(db_path: Path | None = None, quiet: bool = False) -> dict:
    """Harvest every source, upsert into the `assets`/`assets_log` tables (idempotent,
    INSERT OR REPLACE-by-asset_id semantics via store.upsert_asset -- never deletes a
    row), write contradictions, and dump a YAML snapshot. Returns a small stats dict.
    """
    conn = store.connect(db_path) if db_path else store.connect()
    store.ensure_assets_schema(conn)

    bma_path = _freshest_cache_file(RAW_LIVE_DIR / "thaiwater_bma", "*.json")
    rain_path = _freshest_cache_file(RAW_LIVE_DIR / "thaiwater_rain_24h", "*.json")
    pump_path = _freshest_cache_file(RAW_LIVE_DIR / "pumphistory", "*.html")
    water_station_path = RAW_GAPFILL_DIR / "water_station.csv"
    waterlevel_path = _freshest_cache_file(RAW_LIVE_DIR / "thaiwater_waterlevel", "*.json")
    rid_res_table_path = _freshest_cache_file(RAW_LIVE_DIR / "rid_res_table", "*.html")
    hii_dam_path = _freshest_cache_file(RAW_LIVE_DIR / "hii_dam", "*.json")
    hii_watergate_path = _freshest_cache_file(RAW_LIVE_DIR / "hii_watergate", "*.json")

    if not _cache_is_fresh(bma_path) and bma_path is not None and not quiet:
        print(f"[assets_registry] thaiwater_bma cache is stale (> "
              f"{MAX_CACHE_AGE_HOURS}h); using it anyway (no live refetch wired for "
              f"this source in assets_registry.py)", file=sys.stderr)

    bma_rows = harvest_thaiwater_bma(bma_path) if bma_path else []
    rain_rows = harvest_rain_24h(rain_path) if rain_path else []
    pump_rows = harvest_pumphistory(pump_path) if pump_path else []
    ws_rows = harvest_water_station_csv(water_station_path) if water_station_path.exists() else []
    waterlevel_rows = harvest_thaiwater_waterlevel(waterlevel_path) if waterlevel_path else []
    rid_dam_rows = harvest_rid_res_table(rid_res_table_path) if rid_res_table_path else []
    hii_dam_rows = harvest_hii_dam(hii_dam_path) if hii_dam_path else []
    hii_watergate_rows = harvest_hii_watergate(hii_watergate_path) if hii_watergate_path else []

    bma_by_code = {r["source_code"]: r for r in bma_rows if r.get("source_code")}
    cs_rows = harvest_control_structures(CONTROL_STRUCTURES_YAML, bma_by_code)

    contradictions = []
    pump_rows_merged, ws_gates_and_unmatched = _merge_pumphistory_and_water_station(
        pump_rows, ws_rows, contradictions)

    open_rows = hand_declared_open()

    # HII official coordinates -- fill the 35 RID-named, coordinate-OPEN dams first
    # (founder ask "เอาพิกัดจากเว็บไซต์รัฐมีเยอะ") -- see _merge_hii_dam_into_rid_res_table.
    still_open_rid_dam_names: list = []
    rid_dam_rows_filled = _merge_hii_dam_into_rid_res_table(
        hii_dam_rows, rid_dam_rows, still_open_rid_dam_names)

    # HII gates deduped against BMA's existing gate rows (thaiwater_bma + declared
    # control_structures + water_station.csv) -- exact Thai name + <=0.5km match keeps
    # the existing row (annotated in place), otherwise the HII gate is a new row.
    # pump_station/weir rows from hii_watergate are never deduped against BMA gates
    # (different class) -- they pass straight through.
    existing_gate_rows = [r for r in (bma_rows + cs_rows + ws_gates_and_unmatched)
                           if r.get("class") == "gate"]
    hii_gate_rows = [r for r in hii_watergate_rows if r["class"] == "gate"]
    hii_non_gate_rows = [r for r in hii_watergate_rows if r["class"] != "gate"]
    new_hii_gate_rows = _merge_hii_watergate_gates(hii_gate_rows, existing_gate_rows)

    # New this check (founder ask 2026-09-27, "อย่าลืมระบบแก้มลิง และอื่นๆ ทำ kggraph ให้
    # สมบูรณ์"): nationwide rain gauges, the 22 official basins, retention basins,
    # BMA drainage tunnels, levees, diversion channels, tide gates.
    rain_gauge_rows = harvest_rain_gauge_nationwide(rain_path) if rain_path else []
    basin_rows = harvest_basins([rain_path, waterlevel_path, hii_dam_path, hii_watergate_path])
    retention_basin_rows = hand_declared_retention_basins()
    bma_tunnel_rows = hand_declared_tunnels_bma_dds()
    levee_rows = hand_declared_levees()
    diversion_channel_rows = hand_declared_diversion_channels()
    tide_gate_rows = hand_declared_tide_gates()

    all_rows = (bma_rows + rain_rows + pump_rows_merged + ws_gates_and_unmatched
                + cs_rows + open_rows + waterlevel_rows + rid_dam_rows_filled
                + hii_dam_rows + new_hii_gate_rows + hii_non_gate_rows
                + rain_gauge_rows + basin_rows + retention_basin_rows
                + bma_tunnel_rows + levee_rows + diversion_channel_rows + tide_gate_rows)

    verified_at = _utcnow()
    new_count = 0
    for row in all_rows:
        row = _drop_private_keys(row)
        is_new = store.upsert_asset(
            conn,
            asset_id=row["asset_id"], klass=row["class"], tag=row["tag"],
            name_th=row.get("name_th"), source_code=row.get("source_code"),
            lat=row.get("lat"), lon=row.get("lon"),
            coord_source=row.get("coord_source"),
            coord_source_type=row.get("coord_source_type"),
            owner=row.get("owner"), owner_source=row.get("owner_source"),
            pumps_total=row.get("pumps_total"), capacity_m3s=row.get("capacity_m3s"),
            warning_level=row.get("warning_level"), critical_level=row.get("critical_level"),
            bank=row.get("bank"), notes=row.get("notes"), verified_at_utc=verified_at,
        )
        if is_new:
            new_count += 1

    for c in contradictions:
        store.insert_contradiction(
            conn, observed_at_utc=verified_at, topic=c["topic"],
            source_a=c["source_a"], value_a=c["value_a"],
            source_b=c["source_b"], value_b=c["value_b"], note=c["note"],
            observed_a_utc=verified_at, observed_b_utc=verified_at,
        )

    all_assets = store.query_assets(conn)
    YAML_DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    YAML_DUMP_PATH.write_text(
        yaml.safe_dump({"assets": all_assets, "generated_at_utc": verified_at},
                        allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    return {
        "total_rows_harvested": len(all_rows),
        "new_assets": new_count,
        "total_assets_in_db": len(all_assets),
        "contradictions_found": len(contradictions),
        "rid_dams_filled_from_hii": 35 - len(still_open_rid_dam_names),
        "rid_dams_still_open": list(still_open_rid_dam_names),
        "hii_dam_rows_harvested": len(hii_dam_rows),
        "hii_watergate_rows_harvested": len(hii_watergate_rows),
        "hii_gate_rows_new": len(new_hii_gate_rows),
        "hii_gate_rows_merged_into_existing": len(hii_gate_rows) - len(new_hii_gate_rows),
        "rain_gauge_rows_nationwide": len(rain_gauge_rows),
        "basin_rows": len(basin_rows),
        "retention_basin_rows": len(retention_basin_rows),
        "bma_tunnel_rows_new": len(bma_tunnel_rows),
        "levee_rows": len(levee_rows),
        "diversion_channel_rows": len(diversion_channel_rows),
        "tide_gate_rows": len(tide_gate_rows),
    }


# --- CLI -------------------------------------------------------------------------

def cmd_list(args, conn) -> None:
    rows = store.query_assets(conn, klass=args.klass, tag=args.tag, owner=args.owner)
    for r in rows:
        print(f"{r['asset_id']:45s} {r['name_th'] or '':30s} "
              f"lat={r['lat']} lon={r['lon']} tag={r['tag']}")
    print(f"-- {len(rows)} row(s)")


def cmd_near(args, conn) -> None:
    rows = store.query_assets(conn)
    hits = []
    for r in rows:
        if r["lat"] is None or r["lon"] is None:
            continue
        d = haversine_km(args.lat, args.lon, r["lat"], r["lon"])
        if d <= args.km:
            hits.append((d, r))
    hits.sort(key=lambda t: t[0])
    for d, r in hits:
        print(f"{d:5.2f} km  {r['asset_id']:45s} {r['name_th'] or '':30s} "
              f"owner={r['owner']} tag={r['tag']}")
    print(f"-- {len(hits)} asset(s) within {args.km} km")


def cmd_stats(args, conn) -> None:
    rows = store.query_assets(conn)
    by_class_tag: dict = {}
    for r in rows:
        key = (r["class"], r["tag"])
        by_class_tag[key] = by_class_tag.get(key, 0) + 1
    print(f"total assets: {len(rows)}")
    for (klass, tag), n in sorted(by_class_tag.items()):
        print(f"  {klass:15s} {tag:10s} {n}")
    contras = store.query_contradictions(conn)
    print(f"contradictions: {len(contras)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="sqlite db path (default: store.py's own default)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="harvest all sources and upsert into the assets table")
    p_build.set_defaults(func=None)

    p_list = sub.add_parser("list", help="list assets")
    p_list.add_argument("--class", dest="klass", default=None)
    p_list.add_argument("--tag", default=None)
    p_list.add_argument("--owner", default=None)
    p_list.set_defaults(func=cmd_list)

    p_near = sub.add_parser("near", help="list assets within N km of a point")
    p_near.add_argument("lat", type=float)
    p_near.add_argument("lon", type=float)
    p_near.add_argument("--km", type=float, default=3.0)
    p_near.set_defaults(func=cmd_near)

    p_stats = sub.add_parser("stats", help="counts per class/tag + contradiction count")
    p_stats.set_defaults(func=cmd_stats)

    args = ap.parse_args()
    db_path = Path(args.db) if args.db else None

    if args.cmd == "build":
        stats = build(db_path=db_path)
        print(json.dumps(stats, indent=2))
        return

    conn = store.connect(db_path) if db_path else store.connect()
    store.ensure_assets_schema(conn)
    args.func(args, conn)


if __name__ == "__main__":
    main()
