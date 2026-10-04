"""
tools/harvest/hii_waterchart_draft.py -- DRAFT, not wired into collect.py.

Founder question, 2026-09-27: "waterchart.thaiwater.net/basin/chaophraya -- ทำไงให้เชื่อมกับ
api นี้ หรือเชื่อมอยู่แล้ว". See
docs/knowledge/card_api_2026-09-27_hii_waterchart_basin.md for the full readout and
docs/knowledge/api_census_additions_hii_waterchart.yaml for the census-schema rows.

This module covers ONLY the two genuinely new endpoints found by one live Playwright
network capture of that page (the page's `analyst/dam` and `public/watergate_load` calls
are the SAME host+path already wired in collect.py as `hii_dam`/`hii_watergate` -- nothing
new to draft there):

  - public/waterlevel_load  -- richer per-station shape than the already-wired
    `public/waterlevel` (thaiwater_waterlevel): adds discharge (cms), storage_percent,
    waterlevel_msl (+previous), situation_level, river_gid/river_name, and per-station
    cross-section params (left_bank/right_bank/min_bank/ground_level/critical_level_msl,
    is_key_station). REQUIRES basin_id + start_date + end_date query params -- national
    basin_code coverage is NOT confirmed (only the 11 codes the chaophraya page itself
    uses were observed: 6,7,8,9,10,11,12,13,14,15,26). Do not assume basin_id=999 means
    "all of Thailand" -- that is unconfirmed (OPEN), never fetched bare in this check.

  - analyst/cctv -- national station-camera directory (106 records, no query params
    needed). Each cctv_url points at the OWNING agency's own camera server, not thaiwater
    -- link liveness is per-link OPEN, not verified here.

Status: DRAFT ONLY. Every fetch function below makes exactly ONE GET per call, no retry,
no loop -- same one-request-per-URL discipline as collect.py's `_one_get` (this module
does not import collect.py to avoid any risk of being accidentally wired into
`collect.py --all`; it deliberately duplicates the tiny `_one_get` shape instead). Parsing
functions are pure (no I/O) and safe to unit-test against an already-fetched dict.

Promotion path (maker != checker, per AGENTS.md SS5): before this is
wired into collect.py for real, someone other than whoever writes the fetch/parse code
must (a) confirm the full basin_code list for national waterlevel_load coverage, (b)
decide the join/dedup rule against the already-wired thaiwater_waterlevel rows for
stations present in both (same station, richer fields -- prefer the richer row? keep
both, tagged? not decided here), and (c) add a fixture + test under tests/, a
sources/registry.yaml entry, and a store.py insert path. None of that is done by this
file.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

REQUEST_TIMEOUT_S = 20

# Same header shape live_water_level.py's THAIWATER_HEADERS uses for this host family --
# duplicated here (not imported) to keep this draft's only dependency stdlib, per its
# "not wired into anything" status.
THAIWATER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; floodconnect-research/0.1; +thailand_flood_kg)",
    "Accept": "application/json",
}

WATERLEVEL_LOAD_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load"
CCTV_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/cctv"

# The 11 basin_code values observed in one live capture of the chaophraya basin page.
# NOT confirmed as covering all of Thailand's ~25 basins -- treat as OPEN, verify against
# another basin page (or the site's own JS bundle) before relying on this list for a
# nationwide sweep.
CHAOPHRAYA_BASIN_CODES_OBSERVED_2026_09_27 = "6,7,8,9,10,11,12,13,14,15,26"


def _one_get(url: str, headers: Optional[dict] = None, timeout: int = REQUEST_TIMEOUT_S) -> tuple[int, bytes]:
    """ONE GET, no retry, no loop. Returns (status, body). Raises on network error."""
    req = urllib.request.Request(url, headers=headers or THAIWATER_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def fetch_waterlevel_load(basin_codes: str, start_date: str, end_date: str) -> dict:
    """One GET against public/waterlevel_load. `start_date`/`end_date` are
    "YYYY-MM-DD HH:MM" strings (the live page uses e.g. "2026-09-27 00:00" /
    "2026-09-27 23:59"). Raises urllib.error.* on network/HTTP failure -- caller decides
    what to do; this function never retries."""
    url = (
        f"{WATERLEVEL_LOAD_URL}?basin_id={basin_codes}"
        f"&&start_date={urllib.parse.quote(start_date)}"
        f"&&end_date={urllib.parse.quote(end_date)}"
    )
    status, body = _one_get(url)
    if status != 200:
        raise RuntimeError(f"waterlevel_load: HTTP {status}")
    return json.loads(body)


def fetch_cctv() -> dict:
    """One GET against analyst/cctv. No query params observed to be required."""
    status, body = _one_get(CCTV_URL)
    if status != 200:
        raise RuntimeError(f"analyst/cctv: HTTP {status}")
    return json.loads(body)


def parse_waterlevel_load_rows(data: dict) -> list[dict[str, Any]]:
    """Pure parser: public/waterlevel_load response -> flat row list.

    Mirrors the shape of parsers.parse_thaiwater_waterlevel's output where fields overlap
    (station_code/lat/lon/observed_at/value/unit), but keeps this endpoint's EXTRA fields
    (discharge, storage_percent, msl, situation_level, river join, cross-section params)
    rather than dropping them to match the older endpoint's narrower shape -- narrowing
    those away would silently throw away exactly what this endpoint is worth adding for.

    `discharge` and `storage_percent` are copied through as-is (still string types, as the
    API sends them) -- this function does no unit conversion and no fabrication. A record
    missing `waterlevel_datetime` is skipped (observed_at is None) rather than guessed.
    """
    records = (data.get("waterlevel_data") or {}).get("data") or []
    rows: list[dict[str, Any]] = []
    for r in records:
        station = r.get("station") or {}
        basin = r.get("basin") or {}
        agency = r.get("agency") or {}
        observed_at = r.get("waterlevel_datetime")
        if not observed_at:
            continue
        rows.append({
            "station_code": station.get("tele_station_oldcode"),
            "station_id": station.get("id"),
            "station_name_th": (station.get("tele_station_name") or {}).get("th"),
            "lat": station.get("tele_station_lat"),
            "lon": station.get("tele_station_long"),
            "observed_at": observed_at,
            "waterlevel_msl": r.get("waterlevel_msl"),
            "waterlevel_msl_previous": r.get("waterlevel_msl_previous"),
            "waterlevel_m": r.get("waterlevel_m"),
            "discharge_cms": r.get("discharge"),
            "storage_percent": r.get("storage_percent"),
            "situation_level": r.get("situation_level"),
            "station_type": r.get("station_type"),
            "is_key_station": station.get("is_key_station"),
            "left_bank": station.get("left_bank"),
            "right_bank": station.get("right_bank"),
            "min_bank": station.get("min_bank"),
            "ground_level": station.get("ground_level"),
            "warning_level_m": station.get("warning_level_m"),
            "critical_level_m": station.get("critical_level_m"),
            "critical_level_msl": station.get("critical_level_msl"),
            "river_gid": r.get("river_gid"),
            "river_name": r.get("river_name"),
            "basin_id": basin.get("id"),
            "basin_code": basin.get("basin_code"),
            "basin_name_th": (basin.get("basin_name") or {}).get("th"),
            "agency_shortname_en": (agency.get("agency_shortname") or {}).get("en"),
            "tag": "MEASURED",
        })
    return rows


def parse_cctv_rows(data: dict) -> list[dict[str, Any]]:
    """Pure parser: analyst/cctv response -> flat row list. A row with no `lat`/`long`
    (not observed in the one sample this check took, but not guaranteed absent) is kept,
    not dropped -- callers can filter on has-coords themselves."""
    records = data.get("data") or []
    rows: list[dict[str, Any]] = []
    for r in records:
        basin = r.get("basin") or {}
        agency = r.get("agency") or {}
        geocode = r.get("geocode") or {}
        rows.append({
            "cctv_id": r.get("id"),
            "title": r.get("title"),
            "description": r.get("description"),
            "lat": r.get("lat"),
            "lon": r.get("long"),
            "media_type": r.get("media_type"),
            "cctv_url": r.get("cctv_url"),
            "is_active": r.get("is_active"),
            "basin_id": basin.get("id"),
            "basin_name_th": (basin.get("basin_name") or {}).get("th"),
            "agency_shortname_en": (agency.get("agency_shortname") or {}).get("en"),
            "province_th": (geocode.get("province_name") or {}).get("th"),
            "amphoe_th": (geocode.get("amphoe_name") or {}).get("th"),
            "tag": "MEASURED",
        })
    return rows


def _main() -> int:
    """Manual one-shot check: fetches BOTH endpoints once each (2 live GETs total, no
    retries) and prints row counts + one sample row per endpoint. Does not write to
    data/observations.sqlite or raw/live/ -- this is a draft, not a collector; run
    collect.py for the real pipeline."""
    print("Fetching public/waterlevel_load (Chao Phraya + tributary basin codes)...")
    wl_data = fetch_waterlevel_load(
        CHAOPHRAYA_BASIN_CODES_OBSERVED_2026_09_27,
        "2026-09-27 00:00", "2026-09-27 23:59",
    )
    wl_rows = parse_waterlevel_load_rows(wl_data)
    print(f"  {len(wl_rows)} rows. Sample: {wl_rows[0] if wl_rows else None}")

    print("Fetching analyst/cctv (national)...")
    cctv_data = fetch_cctv()
    cctv_rows = parse_cctv_rows(cctv_data)
    print(f"  {len(cctv_rows)} rows. Sample: {cctv_rows[0] if cctv_rows else None}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main())
