#!/usr/bin/env python3
"""
tools/kg/unit_resolver.py -- "any lat,lon in Thailand -> its sub-basin unit".

Promoted from tools/kg/unit_resolver_draft.py (build 6, 2026-09-27) -- the committing
worker accepted the draft's own proposal (see docs/knowledge/DWR_SUBBASIN.md "ขั้นตอนต่อ"
step 3) to move it out of draft status. Behaviour is unchanged from the draft.

Reads the DWR Sub_Basin polygons archived under raw/gis/dwr_subbasin/*.geojson (see
tools/harvest/dwr_subbasin.py, sources/dwr_subbasins.yaml) and answers point-in-polygon
with the real official polygon -- not the radius-INSTINCT fallback currently used for
PROP-FLOOD-06 unit resolution (see raw/backtest/units.yaml HATYAI note, and
docs/knowledge/DWR_SUBBASIN.md for how this replaces it).

Wired into tools/kg/build_kg.py (IN_SUBBASIN edges, see that module) and kb.py
(accountability prints resolved sub-basin first). A separate, unrelated worker's
in-progress file (tools/backtest/run_backtest_v2.py, not part of this commit) still
imports the old `unit_resolver_draft` module path as of this commit -- that file is
outside this commit's file ownership, so it is left for its own owner to update.

Prefers shapely (fast, robust, handles holes/multipolygon correctly) when installed;
falls back to a pure-Python ray-casting point-in-polygon (exterior ring only, per
sub-polygon of a MultiPolygon, ignoring holes -- documented limitation, see
`_point_in_ring_pure_python`) when shapely is not available, so this still works in a
minimal environment.

CLI:
    python3 -m tools.kg.unit_resolver 13.758235 100.676084
    python3 -m tools.kg.unit_resolver --self-test    # runs the 6 fixture points
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
GEOJSON_DIR = HERE / "raw" / "gis" / "dwr_subbasin"

try:
    from shapely.geometry import shape, Point  # type: ignore
    _HAVE_SHAPELY = True
except ImportError:  # pragma: no cover -- exercised only in a shapely-less environment
    _HAVE_SHAPELY = False


# ---------------------------------------------------------------------------
# pure-Python fallback (no shapely)
# ---------------------------------------------------------------------------

def _point_in_ring_pure_python(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Standard ray-casting point-in-polygon over one ring (exterior only -- this fallback
    does NOT subtract holes, a documented limitation vs. the shapely path)."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def _point_in_geometry_pure_python(lon: float, lat: float, geometry: dict) -> bool:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Polygon":
        polys = [coords]
    elif gtype == "MultiPolygon":
        polys = coords
    else:
        return False
    for poly in polys:
        if not poly:
            continue
        exterior = poly[0]
        if _point_in_ring_pure_python(lon, lat, exterior):
            return True
    return False


# ---------------------------------------------------------------------------
# geojson loading (cached -- avoid re-parsing a 70+ MB file per call)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _load_pages() -> tuple:
    pages = sorted(GEOJSON_DIR.glob("page_*.geojson"))
    if not pages:
        raise FileNotFoundError(
            "No archived Sub_Basin GeoJSON under raw/gis/dwr_subbasin/ -- run "
            "`python3 -m tools.harvest.dwr_subbasin` first."
        )
    out = []
    for page in pages:
        doc = json.loads(page.read_text(encoding="utf-8"))
        out.append(doc.get("features", []))
    return tuple(out)


@lru_cache(maxsize=None)
def _load_shapely_index():
    """Returns list of (prepared_shape, properties) -- built once, reused across calls."""
    from shapely.prepared import prep  # local import, only reached if shapely present

    entries = []
    for feats in _load_pages():
        for feat in feats:
            geom = feat.get("geometry")
            props = feat.get("properties") or {}
            if not geom:
                continue
            try:
                geom_shape = shape(geom)
            except Exception:  # noqa: BLE001 -- skip a malformed feature, don't crash
                continue
            entries.append((prep(geom_shape), geom_shape.bounds, props))
    return entries


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def resolve_unit(lat: float, lon: float) -> dict:
    """Returns:
      {"sb_code", "name_th", "basin_code", "basin_name_th", "basin_name_en",
       "area_km2", "tag": "VERIFIED-from-DWR-service", "engine": "shapely"|"pure_python"}
    or, when outside every archived polygon:
      {"sb_code": None, "reason": "<why>", "tag": "OPEN"}
    Never raises for a plausible Thailand-region point; raises FileNotFoundError only if
    the archive itself is missing (a setup problem, not a resolution outcome)."""
    if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
        return {"sb_code": None, "reason": "lat/lon not numeric", "tag": "OPEN"}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {"sb_code": None, "reason": "lat/lon out of world range", "tag": "OPEN"}

    if _HAVE_SHAPELY:
        pt = Point(lon, lat)
        for prepared, bounds, props in _load_shapely_index():
            minx, miny, maxx, maxy = bounds
            if not (minx <= lon <= maxx and miny <= lat <= maxy):
                continue
            if prepared.contains(pt):
                return _row_from_props(props, engine="shapely")
        return {"sb_code": None,
                "reason": "point falls outside every archived DWR Sub_Basin polygon "
                          "(likely sea, or outside Thailand's DWR-mapped extent)",
                "tag": "OPEN"}

    # pure-Python fallback
    for feats in _load_pages():
        for feat in feats:
            geom = feat.get("geometry")
            props = feat.get("properties") or {}
            if not geom:
                continue
            if _point_in_geometry_pure_python(lon, lat, geom):
                return _row_from_props(props, engine="pure_python")
    return {"sb_code": None,
            "reason": "point falls outside every archived DWR Sub_Basin polygon "
                      "(likely sea, or outside Thailand's DWR-mapped extent)",
            "tag": "OPEN"}


def _row_from_props(props: dict, engine: str) -> dict:
    return {
        "sb_code": props.get("SB_CODE"),
        "name_th": props.get("SB_NAME_T"),
        "basin_code": props.get("MB_CODE"),
        "basin_name_th": props.get("MBASIN_T"),
        "basin_name_en": props.get("MBASIN_E"),
        "area_km2": props.get("AREA_SQKM"),
        "tag": "VERIFIED-from-DWR-service",
        "engine": engine,
    }


# ---------------------------------------------------------------------------
# self-test fixture points (per this check's brief)
# ---------------------------------------------------------------------------

SELF_TEST_POINTS = [
    ("Sammakorn (Bangkok)", 13.758235, 100.676084),
    ("Hat Yai municipality", 7.008765, 100.474455),
    ("Nan town", 18.783958, 100.773636),
    ("Chiang Mai town", 18.787747, 98.993128),
    ("Bang Ban (Ayutthaya)", 14.573611, 100.548333),
    ("Gulf of Thailand (sea point)", 10.5, 101.0),
]


def _run_self_test() -> int:
    ok = True
    for label, lat, lon in SELF_TEST_POINTS:
        r = resolve_unit(lat, lon)
        if r.get("sb_code"):
            print(f"{label:28s} ({lat},{lon}) -> sb_code={r['sb_code']} "
                  f"name={r['name_th']} basin={r['basin_name_th']}/{r['basin_name_en']} "
                  f"area_km2={r['area_km2']} tag={r['tag']} engine={r.get('engine')}")
        else:
            print(f"{label:28s} ({lat},{lon}) -> None (reason: {r.get('reason')}) "
                  f"tag={r.get('tag')}")
        if label == "Gulf of Thailand (sea point)" and r.get("sb_code") is not None:
            print("  ** UNEXPECTED: sea point resolved to a sub-basin **")
            ok = False
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("lat", type=float, nargs="?")
    ap.add_argument("lon", type=float, nargs="?")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test or args.lat is None:
        sys.exit(_run_self_test())
    print(json.dumps(resolve_unit(args.lat, args.lon), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
