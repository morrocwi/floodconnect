#!/usr/bin/env python3
"""
tools/harvest/station_tables.py -- nationwide keyless station tables, committed offline.

Builds the compact, committed "sources/stations/<src>.json" tables the M8 nationwide
nodes-and-connectivity work calls for. These are OFFLINE SOURCE OF TRUTH files: a
harvester run makes a small, bounded number of live keyless GET/POST calls (one per
source, same one-request-per-host-per-run discipline as
collect.py; see sources/registry.yaml's bma_watermap/thaiwater_waterlevel host_rule
blocks), re-uses the ALREADY-REVIEWED parsers in parsers.py (no second parsing path), and
writes a deterministic, sorted JSON table that tools/kg/stations_layer.py reads to add
station nodes to the KG -- without ever touching the network itself at KG-build time.

Row schema (list form, stable field order, per design):
    [id, name_th, lat, lon, agency_short, river_name, sb_dwr, basin_code, live_key, as_of]

  id            -- this table's own stable row key (water_code for bma_watermap,
                   station_oldcode-or-station_id for thaiwater_waterlevel)
  name_th       -- the agency's own Thai name, copied byte-for-byte (never re-typed)
  lat, lon      -- float, as published
  agency_short  -- short agency label (constant per source for bma_watermap; the
                   payload's own agency_shortname for thaiwater_waterlevel)
  river_name    -- the agency's own river/canal name string, or null
  sb_dwr        -- DWR sub-basin code resolved by point-in-polygon via
                   tools.kg.unit_resolver, tag VERIFIED-geometric, OR null when the DWR
                   polygon archive (raw/gis/dwr_subbasin/, gitignored, re-downloadable --
                   see tools/harvest/dwr_subbasin.py) is not present in this checkout.
                   NEVER guessed; absence is reported, not silently left ambiguous.
  basin_code    -- same resolver result's basin_code, or the payload's own basin_id for
                   thaiwater_waterlevel when the resolver has no polygon archive (kept in
                   its own column so a reader never confuses an agency-declared basin
                   code with a DWR-resolved one -- see `basin_code_basis` in the sidecar)
  live_key      -- the join key other collectors use for this exact row (water_code /
                   station_oldcode or station_id) -- duplicated from `id` for
                   bma_watermap (same string), kept distinct for thaiwater_waterlevel
                   when oldcode is absent and station_id is used instead
  as_of         -- UTC ISO timestamp of the live call that produced this table

No fabricated field is ever written: a row with no DWR polygon match gets
sb_dwr=None, never a nearest-guess.

CLI:
    python3 -m tools.harvest.station_tables --live --source bma_watermap
    python3 -m tools.harvest.station_tables --live --source thaiwater_waterlevel
    python3 -m tools.harvest.station_tables --live --all
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(HERE))

import parsers  # noqa: E402 -- reuse the already-reviewed parsers, no second parser path
import live_water_level as lwl  # noqa: E402 -- THAIWATER_HEADERS

OUT_DIR = HERE / "sources" / "stations"
REQUEST_TIMEOUT_S = 30

GENERIC_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}
BMA_WATERMAP_HEADERS = dict(GENERIC_HEADERS)
BMA_WATERMAP_HEADERS.update({
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://weather.bangkok.go.th/water/",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
})


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _resolve_sb(lat, lon):
    """Returns (sb_dwr, basin_code, basis) -- basis is a short string documenting
    whether this came from the real DWR polygon archive or was left null because that
    archive is absent in this checkout. Never raises past this function."""
    if lat is None or lon is None:
        return None, None, "no coordinate"
    try:
        from tools.kg.unit_resolver import resolve_unit  # local import: optional shapely dep
    except Exception as e:  # pragma: no cover -- import-time failure only
        return None, None, f"unit_resolver import failed: {e}"
    try:
        row = resolve_unit(lat, lon)
    except FileNotFoundError:
        return None, None, "raw/gis/dwr_subbasin/ archive not present in this checkout"
    if row.get("sb_code") is None:
        return None, None, row.get("reason", "outside every archived DWR polygon")
    return row.get("sb_code"), row.get("basin_code"), "VERIFIED-geometric"


def _fetch_bma_watermap_live() -> list:
    """ONE POST to weather.bangkok.go.th, no retry -- same payload/headers as
    collect.collect_bma_watermap(). Returns the raw parsed JSON list."""
    url = parsers.BMA_WATERMAP_URL
    body_bytes = urlencode({"payload": "TEST_DATA_GOES_HERE"}).encode("ascii")
    req = urllib.request.Request(url, data=body_bytes, headers=BMA_WATERMAP_HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        status, body = resp.status, resp.read()
    if status != 200:
        raise RuntimeError(f"bma_watermap live fetch: HTTP {status}")
    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError("bma_watermap live fetch: unexpected response shape (not a list)")
    return data


def _fetch_thaiwater_waterlevel_live() -> dict:
    """ONE GET to api-v3.thaiwater.net, no retry -- same URL/headers as
    collect.collect_thaiwater_waterlevel()."""
    url = parsers.THAIWATER_WATERLEVEL_URL
    req = urllib.request.Request(url, headers=lwl.THAIWATER_HEADERS)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        status, body = resp.status, resp.read()
    if status != 200:
        raise RuntimeError(f"thaiwater_waterlevel live fetch: HTTP {status}")
    return json.loads(body)


def build_bma_watermap_table(raw_list: list, as_of: str) -> list:
    """raw_list: the live JSON array (or a cached copy of it). Returns rows sorted by
    id (water_code). Every row that has NO water_code was already dropped by
    parsers.parse_bma_watermap_stations (no id to key it by -- never invented)."""
    stations = parsers.parse_bma_watermap_stations(raw_list)
    rows = []
    for s in stations:
        code = s["water_code"]
        lat, lon = s.get("lat"), s.get("lon")
        sb_dwr, basin_code, sb_basis = _resolve_sb(lat, lon)
        rows.append({
            "id": code,
            "name_th": s.get("water_name"),
            "lat": lat,
            "lon": lon,
            "agency_short": "BMA",
            "river_name": s.get("water_name"),  # BMA watermap carries no separate river
            # field -- water_name IS the canal/pond name, same string used for the
            # declared_join evidence in sources/canalchain_station_joins.yaml.
            "sb_dwr": sb_dwr,
            "basin_code": basin_code,
            "live_key": code,
            "as_of": as_of,
        })
    rows.sort(key=lambda r: r["id"])
    return rows


def build_thaiwater_waterlevel_table(raw_data: dict, as_of: str) -> list:
    stations = parsers.parse_thaiwater_waterlevel(raw_data)
    rows = []
    for s in stations:
        live_key = s.get("station_oldcode") or s.get("station_id")
        if not live_key:
            continue
        lat, lon = s.get("lat"), s.get("lon")
        sb_dwr, basin_code_geom, sb_basis = _resolve_sb(lat, lon)
        rows.append({
            "id": live_key,
            "name_th": s.get("station_name_th"),
            "lat": lat,
            "lon": lon,
            "agency_short": s.get("agency_shortname"),
            "river_name": s.get("river_name"),
            "sb_dwr": sb_dwr,
            # basin_code: prefer the DWR-geometric result; fall back to the agency's own
            # declared basin_id (a DIFFERENT, non-DWR code space) only when the polygon
            # archive is absent -- `basin_code_basis` says which one this row got.
            "basin_code": basin_code_geom if sb_dwr is not None else s.get("basin_id"),
            "basin_code_basis": sb_basis if sb_dwr is not None else "agency-declared basin_id (DWR polygon archive absent)",
            "live_key": live_key,
            "as_of": as_of,
        })
    rows.sort(key=lambda r: str(r["id"]))
    return rows


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def write_table(source_id: str, rows: list, as_of: str, fetch_note: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{source_id}.json"
    doc = {
        "source_id": source_id,
        "as_of": as_of,
        "row_count": len(rows),
        "fetch_note": fetch_note,
        "rows": rows,
    }
    out_path.write_text(_dumps(doc), encoding="utf-8")
    return out_path


SOURCES = ("bma_watermap", "thaiwater_waterlevel")


def run_live(source_id: str) -> Path:
    as_of = _utcnow_iso()
    if source_id == "bma_watermap":
        raw = _fetch_bma_watermap_live()
        rows = build_bma_watermap_table(raw, as_of)
        note = f"live POST {parsers.BMA_WATERMAP_URL}, {len(raw)} raw record(s), {len(rows)} with a water_code"
    elif source_id == "thaiwater_waterlevel":
        raw = _fetch_thaiwater_waterlevel_live()
        rows = build_thaiwater_waterlevel_table(raw, as_of)
        note = (f"live GET {parsers.THAIWATER_WATERLEVEL_URL}, "
                f"{len(raw.get('data', []))} raw record(s), {len(rows)} with a coordinate+reading")
    else:
        raise ValueError(f"unknown source_id {source_id!r}, expected one of {SOURCES}")
    return write_table(source_id, rows, as_of, note)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true", required=True,
                     help="required flag -- this tool only ever does a live fetch "
                          "(never fabricates a table from nothing)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", choices=SOURCES)
    g.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)
    sources = SOURCES if args.all else (args.source,)
    for sid in sources:
        try:
            path = run_live(sid)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, RuntimeError) as e:
            print(f"{sid}: FAILED -- {e}", file=sys.stderr)
            return 1
        print(f"{sid}: wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
