"""Offline locate: resolve a lat/lon point to its province, sub-basin, nearest
assets/reach, stations, agencies and known gaps using only the committed
output/kg_index/ slices built by tools/kg/build_index.py. See
docs/KG_QUERY.md section 0b for the slice schema and docs/NEAREST_STATION_RECIPE.md
for how a chat AI without tools should use this by hand.

No live network calls, no graphml read -- this module only reads the small
(~0.8 MB total) kg_index JSON files, memoized per process.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KG_INDEX_DIR = os.path.join(REPO_ROOT, "output", "kg_index")

MAX_OUTPUT_CHARS = 6000


class KGIndexMissing(Exception):
    """Raised when output/kg_index/ is absent or empty."""


_cache: dict[str, Any] = {}


def _load_index(index_dir: str) -> dict[str, Any]:
    key = f"index::{index_dir}"
    if key in _cache:
        return _cache[key]
    path = os.path.join(index_dir, "index.json")
    if not os.path.isfile(path):
        raise KGIndexMissing(f"missing {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[key] = data
    return data


def _load_slice(index_dir: str, filename: str) -> dict[str, Any]:
    key = f"slice::{index_dir}::{filename}"
    if key in _cache:
        return _cache[key]
    path = os.path.join(index_dir, filename)
    if not os.path.isfile(path):
        raise KGIndexMissing(f"missing {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[key] = data
    return data


def _all_slices(index_dir: str, index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for code, meta in index["prov"].items():
        out[code] = _load_slice(index_dir, meta["file"])
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _in_box(lat: float, lon: float, box: list) -> bool:
    if not box or box[0] is None:
        return False
    s, w, n, e = box
    return s <= lat <= n and w <= lon <= e


def _match_province(query: str, index: dict[str, Any]) -> str | None:
    q = query.strip()
    for code, meta in index["prov"].items():
        if q == code:
            return code
    for code, meta in index["prov"].items():
        if meta.get("th") and q == meta["th"]:
            return code
    qf = q.casefold()
    for code, meta in index["prov"].items():
        if meta.get("en") and qf == meta["en"].casefold():
            return code
    return None


def locate(lat: float, lon: float, province: str | None = None, index_dir: str = KG_INDEX_DIR) -> dict[str, Any]:
    index = _load_index(index_dir)
    slices = _all_slices(index_dir, index)
    kg_sha12 = index["kg"]["sha256"][:12]

    method = None
    resolved_code = None
    candidates: list[dict[str, Any]] = []

    if province is not None:
        resolved_code = _match_province(province, index)
        if resolved_code is None:
            # Every province in the index, not just the first 5 by code --
            # a caller mistyping/misspelling a name deserves the full list to
            # search themselves rather than an arbitrary truncated slice.
            cand = [
                {"code": c, "th": m.get("th"), "en": m.get("en")}
                for c, m in sorted(index["prov"].items())
            ]
            return {"error": "province not recognised", "cand": cand}
        method = "caller"
    else:
        # Candidate resolution: bbox containment unioned with nearest-member distance.
        per_prov_near: dict[str, float] = {}
        for code, sl in slices.items():
            best = None
            for row in sl.get("mp", []):
                km = haversine_km(lat, lon, row[0], row[1])
                if best is None or km < best:
                    best = km
            for row in sl.get("a", []):
                if row[9] != "e":
                    continue
                arlat, arlon = row[3], row[4]
                if arlat is None or arlon is None:
                    continue
                km = haversine_km(lat, lon, arlat, arlon)
                if best is None or km < best:
                    best = km
            if best is not None:
                per_prov_near[code] = best
        in_bbox_codes = {code for code, meta in index["prov"].items() if _in_box(lat, lon, meta.get("bbox"))}
        all_codes = set(per_prov_near) | in_bbox_codes
        ranked = sorted(all_codes, key=lambda c: (per_prov_near.get(c, 1e9), c))[:3]
        for code in ranked:
            meta = index["prov"][code]
            candidates.append(
                {
                    "code": code,
                    "th": meta.get("th"),
                    "en": meta.get("en"),
                    "near_km": round(per_prov_near.get(code), 3) if code in per_prov_near else None,
                    "in_bbox": code in in_bbox_codes,
                    "tag": "RELAYED",
                }
            )
        method = "cand"

    # Collect candidate assets to rank by distance, de-duplicated by id.
    search_codes = [resolved_code] if resolved_code else [c["code"] for c in candidates]
    assets_by_id: dict[str, dict[str, Any]] = {}
    for code in search_codes:
        sl = slices.get(code)
        if not sl:
            continue
        for row in sl["a"]:
            aid = row[0]
            if aid in assets_by_id:
                continue
            arlat, arlon = row[3], row[4]
            if arlat is None or arlon is None:
                continue
            km = round(haversine_km(lat, lon, arlat, arlon), 3)
            assets_by_id[aid] = {
                "id": aid,
                "n": row[1],
                "k": row[2],
                "km": km,
                "pv": row[9],
                "reach": row[7],
                "rkm": row[8],
                "ms": None,
                "_province": code,
            }

    ranked_assets = sorted(assets_by_id.values(), key=lambda r: (r["km"], r["id"]))

    sub_basins: dict[str, float] = {}
    for a in ranked_assets[:10]:
        code = a["_province"]
        sl = slices.get(code, {})
        sb = None
        for row in sl.get("a", []):
            if row[0] == a["id"]:
                sb = row[6]
                break
        if sb and sb not in sub_basins:
            sub_basins[sb] = a["km"]
        if len(sub_basins) >= 2:
            break

    nearest5 = ranked_assets[:5]
    for a in nearest5:
        if a.get("reach"):
            code = a["_province"]
            sl = slices.get(code, {})
            r = sl.get("r", {}).get(a["reach"])
            if r:
                a["ms"] = r[1]

    reach_info = None
    for a in nearest5:
        if a.get("reach"):
            reach_info = {"id": a["reach"], "main_stem": bool(a.get("ms")), "km": a["km"]}
            break

    stations: list[dict[str, Any]] = []
    target_sb = next(iter(sub_basins), None)
    target_reach = reach_info["id"] if reach_info else None
    for a in ranked_assets:
        if a["k"] != "gauge":
            continue
        # The KG mislabels the 162 thaiwater_rain:* nodes as class=gauge even
        # though they are rainfall-only gauges, not water-level stations --
        # recorded as a GLOBAL_GAPS entry in build_index.py. Excluded here by
        # id prefix so a rain gauge never becomes a "nearest station".
        if a["id"].startswith("gauge:thaiwater_rain:"):
            continue
        code = a["_province"]
        sl = slices.get(code, {})
        sb = None
        for row in sl.get("a", []):
            if row[0] == a["id"]:
                sb = row[6]
                break
        if (target_reach and a.get("reach") == target_reach) or (target_sb and sb == target_sb):
            stations.append({"id": a["id"], "n": a["n"], "km": a["km"]})
        if len(stations) >= 5:
            break

    def _agencies_for_code(code: str) -> list[dict[str, Any]]:
        """Agencies for exactly ONE province's own slice -- never mixed with
        another candidate's, so a caller can never read "the" agency list for
        a point that was not actually resolved to a single province (HIGH
        finding: a nearest-member vote silently naming Nonthaburi's governor
        for a Pathum Thani point)."""
        sl = slices.get(code)
        agencies: dict[str, str | None] = {}
        if sl:
            for row in sl.get("resp", [])[:6]:
                agencies.setdefault(row[0], None)
            for aid, nm in sl.get("ag", {}).items():
                if len(agencies) >= 6 and aid not in agencies:
                    continue
                agencies[aid] = nm
        for a in nearest5:
            if a.get("_province") != code or not sl:
                continue
            for row in sl.get("a", []):
                if row[0] == a["id"] and row[5]:
                    agencies.setdefault(row[5], sl.get("ag", {}).get(row[5]))
        return [{"id": k, "n": v} for k, v in agencies.items()]

    def _gaps_for_code(code: str) -> list[str]:
        sl = slices.get(code)
        return list(sl.get("gaps", [])) if sl else []

    kg_anchor: dict[str, Any] = {"kg_sha256": kg_sha12, "method": method}
    if resolved_code:
        kg_anchor["province"] = resolved_code
    elif candidates:
        kg_anchor["cand"] = [c["code"] for c in candidates]
        kg_anchor["province_tag"] = "RELAYED"
    if target_sb:
        kg_anchor["sub_basin"] = target_sb
    if target_reach:
        kg_anchor["reach"] = target_reach
    if stations:
        kg_anchor["station_ids"] = [s["id"] for s in stations[:2]]

    # MED/HIGH fix: in "caller" mode the province is unambiguous, so agencies/
    # known_gaps are a flat list for that one province. In "cand" mode there
    # is NO resolved province, so both are returned PER CANDIDATE CODE
    # ({code: [...]})-- never a single list that silently picks one
    # candidate's answer for all of them.
    if method == "caller" and resolved_code:
        agencies_out: Any = _agencies_for_code(resolved_code)
        known_gaps_out: Any = _gaps_for_code(resolved_code)
    else:
        agencies_out = {c["code"]: _agencies_for_code(c["code"]) for c in candidates}
        known_gaps_out = {c["code"]: _gaps_for_code(c["code"]) for c in candidates}

    out: dict[str, Any] = {
        "province": resolved_code,
        "method": method,
        "sub_basin": [{"id": sb, "km": round(km, 3)} for sb, km in sub_basins.items()],
        "nearest_assets": [
            {k: v for k, v in a.items() if k != "_province"} for a in nearest5
        ],
        "reach": reach_info,
        "stations": stations,
        "agencies": agencies_out,
        "known_gaps": known_gaps_out,
        "kg_anchor": kg_anchor,
    }
    if not resolved_code:
        out["cand"] = candidates

    text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    if len(text) > MAX_OUTPUT_CHARS:
        out["nearest_assets"] = out["nearest_assets"][:3]
        if isinstance(out["agencies"], list):
            out["agencies"] = out["agencies"][:4]
        else:
            out["agencies"] = {k: v[:4] for k, v in out["agencies"].items()}
        if isinstance(out["known_gaps"], list):
            out["known_gaps"] = out["known_gaps"][:2]
        else:
            out["known_gaps"] = {k: v[:2] for k, v in out["known_gaps"].items()}
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="locate")
    parser.add_argument("--at", required=True, help="lat,lon")
    parser.add_argument("--province", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    lat_s, lon_s = args.at.split(",")
    try:
        result = locate(float(lat_s), float(lon_s), province=args.province)
    except KGIndexMissing as exc:
        print(json.dumps({"error": "kg index missing", "detail": str(exc)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))
