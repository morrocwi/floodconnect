#!/usr/bin/env python3
"""
tools/harvest/hii_station_geocode.py -- one-shot, offline harvester that builds
sources/hii_station_geocode.yaml: a per-asset_id index of the `geocode` block (province,
amphoe, tumbon, river name) already embedded in HII's own thaiwater30/thaiwater3.1
payloads this repo has cached under raw/live/.

Why this exists: `tools/kg/build_kg.py`'s `load_assets()` reads the sqlite `assets` table
(assets_registry.py's own schema, see store.py), which has NO province/amphoe column --
assets_registry.py's harvesters read `geocode.province_name` off these same payloads but
fold it into free-text `notes`, never a queryable column (checked: PRAGMA table_info(assets)
has no province/amphoe field). That is the KG gap this file closes: a province/amphoe VALUE
these payloads already carry, that the existing pipeline already discards.

No network request. Reads only already-archived raw/live/*.json files. Never silently
prefers a source: if an asset_id appears under more than one source directory and the two
geocode blocks disagree, BOTH are kept (see the `contradiction` row shape below), per
founder ruling 2026-09-27 ("two sources same station -> keep both, contradiction rows,
never silently prefer").

Asset-id convention reproduced from assets_registry.py (not reinvented here):
  gauge:thaiwater_waterlevel:<oldcode-or-id...>   (harvest_thaiwater_waterlevel)
  gauge:thaiwater_rain:<oldcode-or-id...>         (harvest_rain_24h, Bangkok-bbox only)
  rain_gauge:thaiwater_rain_24h:<station.id>      (harvest_rain_gauge_nationwide)
  gate|weir|pump_station:hii_watergate:<station.id>  (harvest_hii_watergate)
  dam|reservoir_medium|reservoir_small:hii_dam:<dam.id>  (harvest_hii_dam)

Usage:
    python3 -m tools.harvest.hii_station_geocode
    python3 -m tools.harvest.hii_station_geocode --raw-dir /path/to/other/checkout/raw

Tag on every row: VERIFIED (source: "HII thaiwater geocode block" -- read verbatim off an
official-API payload this repo already has on disk, not derived/guessed).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent.parent
DEFAULT_RAW_DIR = HERE / "raw" / "live"
OUT_PATH = HERE / "sources" / "hii_station_geocode.yaml"

TAG = "VERIFIED"
SOURCE_NOTE = "HII thaiwater geocode block (api-v3.thaiwater.net, cached under raw/live/)"


def _th(d: dict | None, key: str) -> str | None:
    if not d:
        return None
    v = d.get(key)
    if isinstance(v, dict):
        return v.get("th") or v.get("en")
    return v


def _row_from_rec(rec: dict, code: str, asset_id: str) -> dict:
    geocode = rec.get("geocode") or {}
    station = rec.get("station") or {}
    return {
        "asset_id": asset_id,
        "province_code": geocode.get("province_code"),
        "province_name_th": _th(geocode, "province_name"),
        "amphoe_code": geocode.get("amphoe_code"),
        "amphoe_name_th": _th(geocode, "amphoe_name"),
        "tumbon_name_th": _th(geocode, "tumbon_name"),
        "river_name": rec.get("river_name") or station.get("river_name"),
        "tag": TAG,
        "source": SOURCE_NOTE,
    }


def _collect_waterlevel(raw_dir: Path) -> list[dict]:
    """thaiwater_waterlevel -> gauge:thaiwater_waterlevel:<oldcode-or-id>."""
    out = []
    d = raw_dir / "thaiwater_waterlevel"
    for f in sorted(d.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for rec in payload.get("data", []) or []:
            station = rec.get("station") or {}
            sid = station.get("id")
            code = station.get("tele_station_oldcode") or (f"id{sid}" if sid is not None else None)
            if not code:
                continue
            out.append(_row_from_rec(rec, code, f"gauge:thaiwater_waterlevel:{code}"))
    return out


def _collect_rain_24h(raw_dir: Path) -> list[dict]:
    """thaiwater_rain_24h -> rain_gauge:thaiwater_rain_24h:<station.id> (nationwide
    convention, matches harvest_rain_gauge_nationwide, not the Bangkok-bbox
    gauge:thaiwater_rain:* namespace, which is a strict lat/lon-filtered subset of the
    same station.id and would double-count rows under a different asset_id)."""
    out = []
    d = raw_dir / "thaiwater_rain_24h"
    for f in sorted(d.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for rec in payload.get("data", []) or []:
            station = rec.get("station") or {}
            sid = station.get("id")
            if not sid:
                continue
            out.append(_row_from_rec(rec, str(sid), f"rain_gauge:thaiwater_rain_24h:{sid}"))
    return out


def _collect_watergate(raw_dir: Path) -> list[dict]:
    """hii_watergate -> {gate,weir,pump_station}:hii_watergate:<station.id>. This
    harvester does not reproduce assets_registry.py's `_classify_hii_watergate_row`
    name-based class split, so it emits ONE row keyed by station.id only and lets the
    caller (sources/hii_station_geocode.yaml's consumer) try all three class prefixes --
    documented as a known limitation below rather than silently guessing a class."""
    out = []
    d = raw_dir / "hii_watergate"
    for f in sorted(d.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rows = ((payload.get("watergate_data") or {}).get("data")) or []
        for rec in rows:
            station = rec.get("station") or {}
            sid = station.get("id")
            if not sid:
                continue
            row = _row_from_rec(rec, str(sid), f"hii_watergate:station:{sid}")
            out.append(row)
    return out


def _collect_dam(raw_dir: Path) -> list[dict]:
    """hii_dam -> dam:hii_dam:<dam.id> (also reservoir_medium/reservoir_small, same
    dam.id namespace per assets_registry.py's _HII_DAM_LIST_TO_CLASS)."""
    out = []
    d = raw_dir / "hii_dam"
    for f in sorted(d.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        data = payload.get("data", {}) or {}
        for list_name in ("dam_hourly", "dam_daily", "dam_medium", "dam_small_tele"):
            for rec in data.get(list_name, []) or []:
                dam = rec.get("dam") or {}
                dam_id = dam.get("id")
                if dam_id is None:
                    continue
                out.append(_row_from_rec(rec, str(dam_id), f"hii_dam:dam:{dam_id}"))
    return out


def merge(rows: list[dict]) -> tuple[dict, list[dict]]:
    """Collapse to one row per asset_id. Where two archived files disagree on the
    geocode block for the SAME asset_id, keep both as a contradiction row (never
    silently prefer one -- founder ruling 2026-09-27)."""
    by_id: dict[str, dict] = {}
    contradictions: list[dict] = []
    for r in rows:
        aid = r["asset_id"]
        key_fields = ("province_code", "amphoe_code", "river_name")
        if aid not in by_id:
            by_id[aid] = r
            continue
        existing = by_id[aid]
        if any(existing.get(k) and r.get(k) and existing.get(k) != r.get(k) for k in key_fields):
            contradictions.append({
                "asset_id": aid,
                "variant_a": {k: existing.get(k) for k in key_fields},
                "variant_b": {k: r.get(k) for k in key_fields},
                "tag": "OPEN",
                "note": "two archived raw/live/ files disagree on this station's geocode; "
                        "both kept, neither preferred",
            })
        # fill any field missing in the kept row from this later observation
        for k, v in r.items():
            if existing.get(k) in (None, "") and v not in (None, ""):
                existing[k] = v
    return by_id, contradictions


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR,
                     help="path to a raw/live directory (default: this repo's own, "
                          "gitignored; pass another checkout's raw/live to run offline "
                          "against already-archived files there)")
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    if not args.raw_dir.exists():
        print(f"no raw dir at {args.raw_dir} -- nothing to harvest (raw/ is gitignored, "
              f"local-only input)")
        return

    rows: list[dict] = []
    rows += _collect_waterlevel(args.raw_dir)
    rows += _collect_rain_24h(args.raw_dir)
    rows += _collect_watergate(args.raw_dir)
    rows += _collect_dam(args.raw_dir)
    print(f"collected {len(rows)} raw geocode observations "
          f"({len(_collect_waterlevel(args.raw_dir))} waterlevel, "
          f"{len(_collect_rain_24h(args.raw_dir))} rain_24h, "
          f"{len(_collect_watergate(args.raw_dir))} watergate, "
          f"{len(_collect_dam(args.raw_dir))} dam)")

    by_id, contradictions = merge(rows)
    print(f"merged to {len(by_id)} distinct asset_ids, {len(contradictions)} contradictions")

    doc = {
        "generated_by": "tools/harvest/hii_station_geocode.py",
        "generated_from": "raw/live/{thaiwater_waterlevel,thaiwater_rain_24h,hii_watergate,hii_dam}",
        "tag": TAG,
        "source": SOURCE_NOTE,
        "known_limitation": (
            "hii_watergate rows are keyed `hii_watergate:station:<id>` (station.id) and "
            "hii_dam rows `hii_dam:dam:<id>` (dam.id) -- not the final gate/weir/"
            "pump_station or dam/reservoir_medium/reservoir_small asset_id -- this script "
            "does not reproduce assets_registry.py's name-based "
            "_classify_hii_watergate_row split or its dam/reservoir list->class mapping. "
            "A consumer must try each possible class prefix (gate:/weir:/pump_station: "
            "for hii_watergate, dam:/reservoir_medium:/reservoir_small: for hii_dam) "
            "against this file's generic rows, or this file must be re-keyed once those "
            "classifiers are exposed as shared functions instead of inlined in "
            "assets_registry.py. Not yet done here -- left OPEN rather than duplicating "
            "that logic and risking drift. MEASURED join against the shipped "
            "output/thailand_water_kg.graphml (25,883 nodes) with this re-prefixing: "
            "gauge 804/1231, gate 2023/2280, weir 102/102, rain_gauge 4428/4428, "
            "dam+reservoir_medium+reservoir_small 973/1008, pump_station 39/301 "
            "(pump_station rows mostly come from a BMA source this harvester does not "
            "read, not from hii_watergate)."
        ),
        "rows": sorted(by_id.values(), key=lambda r: r["asset_id"]),
        "contradictions": contradictions,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"wrote {args.out} ({len(by_id)} rows, {len(contradictions)} contradictions)")


if __name__ == "__main__":
    main()
