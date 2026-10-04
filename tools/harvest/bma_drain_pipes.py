#!/usr/bin/env python3
"""
BMA drainage-pipe inventory parser -- founder task (verbatim, 17:08 2026-09-27):
"เอาเลย สร้าง floodconnect topology จากสิ่งที่เรามี" (build the FloodConnect drainage
TOPOLOGY layer from what this repo already has on disk).

Reads the two already-archived BMA Open Data (data.bangkok.go.th, สำนักการระบายน้ำ) CSVs
this repo fetched earlier the same day (see `sources/api_census_drainage.yaml`,
`docs/knowledge/DRAINAGE_NETWORK_SOURCES.md`):

  1. `raw/live/bma_open_data_drainage_org/drain_pipe_full.csv` -- 2,903 data rows, one row
     roughly per road-segment. Each row can carry UP TO FOUR pipe sides
     (R=right, L=left, ROAD=road-level channel, PJ=pipe-jacking/trenchless culvert),
     each with its own DIMENSION/LENGTH/TYPE columns. `PIPE_FROM`/`PIPE_TO` are named
     street/intersection endpoints -- explicit TOPOLOGY, never coordinates. Encoding is
     windows-874 (TIS-620), confirmed by full-file decode with no errors this check.
  2. `raw/live/bma_open_data_drainage_org/pipe_jacking_full.csv` -- 12 data rows, a small,
     DIFFERENT dataset (sump/pumping wells associated with pipe-jacking works), with
     genuine UTM Zone 47N (EPSG:32647) coordinates in its own `UTM_X`/`UTM_Y` columns --
     these are the file's own explicit coordinates, converted to WGS84 here with pyproj
     (a coordinate-system conversion, not a geocoding/inference step -- the point is
     exactly where the source says it is, just expressed in a different CRS). Encoding is
     plain UTF-8 (confirmed; different from the drain_pipe file).

Never geocodes PIPE_FROM/PIPE_TO street names against any gazetteer -- that would be a
new inference step not present in the source, forbidden by this repo's "no geometric
snapping/inference without INSTINCT tag + founder approval" rule
(`docs/knowledge/DRAINAGE_NETWORK_SOURCES.md`). Every drain-pipe-CSV row's `coords` is
therefore always null; only the separate pipe_jacking sump-well rows carry real
coordinates (their own file's own numbers).

Output: `sources/bma_drain_pipes.yaml` (tracked), with two top-level lists:
  - `drain_pipe_rows`: one row per (csv row, side) where that side's DIMENSION/LENGTH/TYPE
    aren't all blank/dash -- segment_id, district, road, pipe_from, pipe_to, side,
    dimension, length_m, type, tag: VERIFIED-from-official-csv, coords: null.
  - `sump_wells`: one row per pipe_jacking CSV data row -- id, district, place, lat, lon,
    power_kw, tag: VERIFIED-from-official-csv, coords non-null (converted UTM47N->WGS84).

CLI:
    python3 -m tools.harvest.bma_drain_pipes --run
    python3 -m tools.harvest.bma_drain_pipes --run --dry-run   # parse + print counts only
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent.parent  # repo root

DRAIN_PIPE_CSV = HERE / "raw" / "live" / "bma_open_data_drainage_org" / "drain_pipe_full.csv"
PIPE_JACKING_CSV = HERE / "raw" / "live" / "bma_open_data_drainage_org" / "pipe_jacking_full.csv"
OUT_PATH = HERE / "sources" / "bma_drain_pipes.yaml"

TAG = "VERIFIED-from-official-csv"

# side -> (dimension_col, length_col, type_col)
SIDE_COLS = {
    "R": ("R_DIMENSION", "R_LENGTH", "R_TYPE"),
    "L": ("L_DIMENSION", "L_LENGTH", "L_TYPE"),
    "ROAD": ("ROAD_DIMENSION", "ROAD_LENGTH", "ROAD_TYPE"),
    "PJ": ("PJ_DIMENSION", "PJ_LENGTH", "PJ_TYPE"),
}

BLANK_VALUES = {"", "-", "None", None}


def _clean(v):
    if v is None:
        return None
    v = v.strip()
    return v if v not in BLANK_VALUES else None


def _to_float(v):
    v = _clean(v)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_drain_pipe_csv(path: Path) -> list[dict]:
    """Returns one normalised row per (csv row, side) with any real data on that side.
    `segment_id` is `seg<No>_<side>` -- `<No>` is the source file's own row number
    (its `No` column), never invented here."""
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="cp874") as f:
        for rec in csv.DictReader(f):
            no = _clean(rec.get("No"))
            district = _clean(rec.get("DISTRICT_NAME"))
            road = _clean(rec.get("ROADCL_NAME"))
            pipe_from = _clean(rec.get("PIPE_FROM"))
            pipe_to = _clean(rec.get("PIPE_TO"))
            for side, (dim_col, len_col, type_col) in SIDE_COLS.items():
                dimension = _clean(rec.get(dim_col))
                length_m = _to_float(rec.get(len_col))
                ptype = _clean(rec.get(type_col))
                if dimension is None and length_m is None and ptype is None:
                    continue  # this side has no data at all -- skip, don't fabricate a row
                rows.append({
                    "segment_id": f"seg{no}_{side}",
                    "district": district,
                    "road": road,
                    "pipe_from": pipe_from,
                    "pipe_to": pipe_to,
                    "side": side,
                    "dimension": dimension,
                    "length_m": length_m,
                    "type": ptype,
                    "tag": TAG,
                    "coords": None,
                    "source": "data.bangkok.go.th/dataset/drain-pipe (BMA drain_pipe.csv)",
                })
    return rows


def parse_pipe_jacking_csv(path: Path) -> list[dict]:
    """Sump/pump wells with real UTM47N coordinates -- converted to WGS84 here (CRS
    conversion of the source's own numbers, not a new geocode)."""
    if not path.exists():
        return []
    import pyproj
    transformer = pyproj.Transformer.from_crs("EPSG:32647", "EPSG:4326", always_xy=True)
    rows = []
    with open(path, encoding="utf-8") as f:
        for rec in csv.DictReader(f):
            no = _clean(rec.get("NO"))
            district = _clean(rec.get("DISTRICT_NAME"))
            place = _clean(rec.get("SUMP_PLACE"))
            utm_x = _to_float(rec.get("UTM_X"))
            utm_y = _to_float(rec.get("UTM_Y"))
            power = _to_float(rec.get("POWER"))
            lat = lon = None
            if utm_x is not None and utm_y is not None:
                lon, lat = transformer.transform(utm_x, utm_y)
            rows.append({
                "well_id": f"sump{no}",
                "district": district,
                "place": place,
                "lat": lat,
                "lon": lon,
                "power_kw": power,
                "tag": TAG,
                "coord_source": "sources own UTM_X/UTM_Y (EPSG:32647), converted to WGS84 here",
                "source": "data.bangkok.go.th/dataset/pipe_jacking (BMA data-pipe-jacking.csv)",
            })
    return rows


def build(dry_run: bool = False) -> dict:
    drain_rows = parse_drain_pipe_csv(DRAIN_PIPE_CSV)
    sump_rows = parse_pipe_jacking_csv(PIPE_JACKING_CSV)

    both_ends = sum(1 for r in drain_rows if r["pipe_from"] and r["pipe_to"])
    districts = sorted({r["district"] for r in drain_rows if r["district"]})
    print(f"drain_pipe_rows: {len(drain_rows)} (from {DRAIN_PIPE_CSV.name})")
    print(f"  with both pipe_from and pipe_to: {both_ends}")
    print(f"  distinct districts: {len(districts)}")
    print(f"sump_wells: {len(sump_rows)} (from {PIPE_JACKING_CSV.name})")

    doc = {
        "_meta": {
            "generated": "2026-09-27",
            "founder_ask_th": "เอาเลย สร้าง floodconnect topology จากสิ่งที่เรามี",
            "method": "tools/harvest/bma_drain_pipes.py -- one row per (CSV row, pipe "
                      "side) with real data; no geocoding of PIPE_FROM/PIPE_TO street "
                      "names; sump_wells coordinates are a CRS conversion of the "
                      "source's own UTM47N numbers, never inferred.",
            "sources": [str(DRAIN_PIPE_CSV.relative_to(HERE)),
                        str(PIPE_JACKING_CSV.relative_to(HERE))],
        },
        "drain_pipe_rows": drain_rows,
        "sump_wells": sump_rows,
    }
    if not dry_run:
        OUT_PATH.write_text(
            yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8")
        print(f"Wrote {OUT_PATH}")
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="parse and write sources/bma_drain_pipes.yaml")
    ap.add_argument("--dry-run", action="store_true", help="parse and print counts only, no write")
    args = ap.parse_args()
    if not args.run and not args.dry_run:
        ap.print_help()
        sys.exit(1)
    build(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
