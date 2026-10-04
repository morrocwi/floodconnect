#!/usr/bin/env python3
"""
tools/harvest/dwr_subbasin.py -- harvest DWR (gis.dwr.go.th) Sub_Basin polygons and build
sources/dwr_subbasins.yaml, a per-sub-basin index (no geometry inline -- points to the
archived GeoJSON) that `tools/kg/unit_resolver.py` reads for point-in-polygon
resolution.

Source: gis.dwr.go.th/arcgis/rest/services/Sub_Basin/MapServer/0 -- unauthenticated ArcGIS
REST FeatureServer, confirmed reachable 2026-09-27 (see docs/knowledge/DATA_SWEEP_2026-09-27.md
section E). 359 features total (confirmed via returnCountOnly), under this layer's own
maxRecordCount (2000) -- fits in ONE page, no pagination loop needed in practice, but this
script still pages defensively (stops at 20 pages, matches the harvest budget in this check's
brief) in case the service's maxRecordCount or feature count changes later.

AGENTS.md host-safety rule applied: one request per URL, no retries. Every raw response is
archived verbatim under raw/gis/dwr_subbasin/ before any parsing.

Usage:
    python3 -m tools.harvest.dwr_subbasin              # fetch fresh (hits the live service)
    python3 -m tools.harvest.dwr_subbasin --offline     # rebuild sources/dwr_subbasins.yaml
                                                         # from already-archived raw files only
                                                         # (no network request at all)

Tag on every row this script writes: VERIFIED-from-DWR-service (geometric fact read directly
from an official agency polygon service, not a claim this repo derived or guessed).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
RAW_DIR = HERE / "raw" / "gis" / "dwr_subbasin"
OUT_YAML = HERE / "sources" / "dwr_subbasins.yaml"

BASE = "https://gis.dwr.go.th/arcgis/rest/services"
SUBBASIN_LAYER = f"{BASE}/Sub_Basin/MapServer/0"
BASIN_LAYER = f"{BASE}/25_BASIN/MapServer/0"  # confirmed single layer, name "BASIN"

UA = "Mozilla/5.0 (X11; Linux x86_64) FloodConnect-harvest/1.0"
MAX_PAGES = 20
TIMEOUT_S = 20


def _fetch(url: str) -> bytes:
    """ONE request, no retry. Raises on any failure -- caller decides what to do."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return resp.read()


def _save(name: str, data: bytes) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / name
    path.write_bytes(data)
    return path


def harvest_live() -> list[Path]:
    """Fetch layer metadata, feature count, Sub_Basin pages, and the Basin layer once each.
    Returns the list of archived file paths. One request per URL, no retries (per AGENTS.md)."""
    saved = []

    # 1. layer metadata (fields, maxRecordCount, spatialReference, licence text)
    info = _fetch(f"{SUBBASIN_LAYER}?f=json")
    saved.append(_save("layer_info.json", info))
    info_j = json.loads(info)
    max_rec = info_j.get("maxRecordCount", 1000)

    # 2. feature count (no geometry -- cheap probe before paging)
    count_raw = _fetch(
        f"{SUBBASIN_LAYER}/query?where=1%3D1&outFields=OBJECTID&returnGeometry=false"
        "&returnCountOnly=true&f=json"
    )
    saved.append(_save("count.json", count_raw))
    total = json.loads(count_raw).get("count", 0)

    # 3. page through features, WGS84 (outSR=4326) so unit_resolver never needs a
    #    projection step; each page is one request; archived under its own filename.
    offset = 0
    page_n = 0
    while True:
        if page_n >= MAX_PAGES:
            print(f"STOP: reached MAX_PAGES={MAX_PAGES} before exhausting {total} features "
                  f"(offset={offset}) -- documented in DWR_SUBBASIN.md, not silently retried.",
                  file=sys.stderr)
            break
        url = (
            f"{SUBBASIN_LAYER}/query?where=1%3D1&outFields=*&returnGeometry=true"
            f"&outSR=4326&f=geojson&resultOffset={offset}&resultRecordCount={max_rec}"
        )
        raw = _fetch(url)
        path = _save(f"page_{page_n}.geojson", raw)
        saved.append(path)
        doc = json.loads(raw)
        n = len(doc.get("features", []))
        page_n += 1
        offset += n
        if n < max_rec or offset >= total:
            break

    # 4. parent Basin layer, once (basin<->sub-basin mapping; Sub_Basin's own MB_CODE/
    #    MBASIN_T/MBASIN_E fields already carry this inline, so this is cross-check only).
    try:
        basin_info = _fetch(f"{BASIN_LAYER}?f=json")
        saved.append(_save("basin_layer_info.json", basin_info))
        basin_attrs = _fetch(
            f"{BASIN_LAYER}/query?where=1%3D1&outFields=*&returnGeometry=false&f=json"
        )
        saved.append(_save("basin_attrs.json", basin_attrs))
    except Exception as exc:  # noqa: BLE001 -- one host, report and move on, no retry
        print(f"OPEN: basin layer fetch failed once ({exc}); not retried.", file=sys.stderr)

    return saved


def _bbox_centroid(geom: dict):
    """Pure-stdlib bbox/centroid over a GeoJSON Polygon/MultiPolygon ring set -- used only
    for the yaml's summary bbox/centroid fields (never the full geometry, which stays in
    the archived GeoJSON file). Centroid here is the simple ring-vertex average (a summary
    point for humans/indexing), NOT the true area centroid -- point-in-polygon resolution
    in unit_resolver.py uses the real polygon, not this approximation."""
    coords_flat = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            coords_flat.append(c)
        else:
            for sub in c:
                walk(sub)

    walk(geom["coordinates"])
    lons = [c[0] for c in coords_flat]
    lats = [c[1] for c in coords_flat]
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    centroid = [sum(lons) / len(lons), sum(lats) / len(lats)]
    return bbox, centroid


def build_yaml(offline: bool = False) -> Path:
    pages = sorted(RAW_DIR.glob("page_*.geojson"))
    if not pages:
        raise SystemExit(f"No archived pages under {RAW_DIR} -- run without --offline first.")

    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    seen_codes = set()
    for page_idx, page in enumerate(pages):
        doc = json.loads(page.read_text(encoding="utf-8"))
        feats = doc.get("features", [])
        for feat_idx, feat in enumerate(feats):
            props = feat.get("properties") or feat.get("attributes") or {}
            sb_code = props.get("SB_CODE")
            if sb_code in seen_codes:
                continue  # defensive: no duplicate rows if a re-run overlaps a page boundary
            seen_codes.add(sb_code)
            geom = feat.get("geometry")
            bbox, centroid = (_bbox_centroid(geom) if geom else (None, None))
            rows.append({
                "sb_code": sb_code,
                "name_th": props.get("SB_NAME_T"),
                "basin_code": props.get("MB_CODE"),
                "basin_name_th": props.get("MBASIN_T"),
                "basin_name_en": props.get("MBASIN_E"),
                "area_sqkm": props.get("AREA_SQKM"),
                "bbox_wgs84": bbox,
                "centroid_wgs84_approx": centroid,
                "feature_file": str(page.relative_to(HERE)),
                "feature_index": feat_idx,
                "tag": "VERIFIED-from-DWR-service",
                "fetched_at": fetched_at if not offline else "see file mtime (offline rebuild)",
            })

    OUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# sources/dwr_subbasins.yaml -- generated by tools/harvest/dwr_subbasin.py.",
        "# One row per DWR Sub_Basin polygon (gis.dwr.go.th, ArcGIS REST, unauthenticated,",
        "# no licence/terms page found this sweep -- OPEN, see docs/knowledge/DWR_SUBBASIN.md).",
        "# No geometry inline here -- see feature_file/feature_index for the archived GeoJSON.",
        "# centroid_wgs84_approx is a vertex-average summary point, NOT the true area centroid",
        "# -- do not use it for point-in-polygon; use tools/kg/unit_resolver.py instead.",
        f"generated_at: \"{fetched_at}\"",
        f"source_layer: \"{SUBBASIN_LAYER}\"",
        "crs: \"EPSG:4326 (requested via outSR=4326; layer's native storage CRS is EPSG:32647 / UTM47N, see raw/gis/dwr_subbasin/layer_info.json)\"",
        f"total_features: {len(rows)}",
        "licence: \"OPEN -- no copyrightText / terms-of-use page found in this sweep (docs/knowledge/DATA_SWEEP_2026-09-27.md sec E); do not treat as cleared for redistribution until checked\"",
        "rows:",
    ]
    for r in rows:
        lines.append(f"  - sb_code: {json.dumps(r['sb_code'], ensure_ascii=False)}")
        lines.append(f"    name_th: {json.dumps(r['name_th'], ensure_ascii=False)}")
        lines.append(f"    basin_code: {json.dumps(r['basin_code'], ensure_ascii=False)}")
        lines.append(f"    basin_name_th: {json.dumps(r['basin_name_th'], ensure_ascii=False)}")
        lines.append(f"    basin_name_en: {json.dumps(r['basin_name_en'], ensure_ascii=False)}")
        lines.append(f"    area_sqkm: {r['area_sqkm']}")
        lines.append(f"    bbox_wgs84: {json.dumps(r['bbox_wgs84'])}")
        lines.append(f"    centroid_wgs84_approx: {json.dumps(r['centroid_wgs84_approx'])}")
        lines.append(f"    feature_file: {json.dumps(r['feature_file'], ensure_ascii=False)}")
        lines.append(f"    feature_index: {r['feature_index']}")
        lines.append(f"    tag: {r['tag']}")
        lines.append(f"    fetched_at: {json.dumps(r['fetched_at'], ensure_ascii=False)}")
    OUT_YAML.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_YAML} ({len(rows)} sub-basin rows)")
    return OUT_YAML


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                     help="skip network entirely, rebuild yaml from already-archived raw files")
    args = ap.parse_args()
    if not args.offline:
        harvest_live()
    build_yaml(offline=args.offline)


if __name__ == "__main__":
    main()
