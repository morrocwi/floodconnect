"""Deterministic per-province KG index builder (M4, "KG-first that AIs cannot
skip"). Reads the shipped graph only (networkx + stdlib) and writes
output/kg_index/index.json plus one output/kg_index/province_<code>.json per
province node present in the graph. See docs/KG_QUERY.md section 0b for the
schema and tools/kg/README.md for the underlying graph's own known gaps.

Determinism: json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
sort_keys=True) + "\n"; rows sorted by id; lat/lon rounded to 5dp, km to 3dp;
no timestamps anywhere -- the build is identified only by kg.sha256. Running
this script twice on the same graph must produce byte-identical output.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from typing import Any

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KG_GRAPHML = os.path.join(REPO_ROOT, "output", "thailand_water_kg.graphml")
KG_INDEX_DIR = os.path.join(REPO_ROOT, "output", "kg_index")

ASSET_CLASSES = ("gauge", "gate", "weir", "dam", "pump_station", "tide_gate")

GLOBAL_GAPS = [
    "assets without coordinates (14) are excluded from every slice's 'a' and 'mp' lists",
    "province:99 and province:10499 (non-Thailand codes present in the geocode source) have no bbox",
    "AG_BASIN_CMT.name_th says '36 lum nam' but the DWR crosswalk used here has 22 -- the KG node itself is not changed",
    "ON_REACH is a DERIVED-snap heuristic (nearest river_reach centroid by haversine), not a point-to-polyline match",
    "pv='b' (box-placed) assets have no IN_PROVINCE edge and may appear in more than one neighbouring province's slice",
    "162 gauge:thaiwater_rain:* nodes carry class=gauge in this KG build (a label mislabel in the "
    "underlying graph, not changed here) even though they are rainfall-only gauges, not water-level "
    "stations -- tools/kg/locate.py excludes thaiwater_rain: ids from 'stations'/station_ids by id prefix",
]


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, str):
        if v == "null" or v == "":
            return None
        try:
            v = float(v)
        except ValueError:
            return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return float(v)


def _r5(v: float | None) -> float | None:
    return None if v is None else round(v, 5)


def _r3(v: float | None) -> float | None:
    return None if v is None else round(v, 3)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_province_names_en() -> dict[str, str]:
    """Optional VERIFIED English province names from a committed snapshot of
    the HII feed (sources/province_names_en.yaml). Absent -> {} (en: null
    fallback per the design's F5 decline path)."""
    path = os.path.join(REPO_ROOT, "sources", "province_names_en.yaml")
    if not os.path.exists(path):
        return {}
    try:
        import yaml  # type: ignore
    except ImportError:
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    out = {}
    for row in data.get("provinces", []):
        code = str(row.get("province_code"))
        en = row.get("en")
        if code and en:
            out[code] = en
    return out


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


def build(graph_path: str = KG_GRAPHML, out_dir: str = KG_INDEX_DIR) -> dict[str, Any]:
    if nx is None:
        raise RuntimeError("networkx is required to build the KG index")
    g = nx.read_graphml(graph_path)
    kg_sha256 = sha256_file(graph_path)

    names_en = load_province_names_en()

    provinces: dict[str, dict[str, Any]] = {}
    for n, d in g.nodes(data=True):
        if d.get("kind") == "province":
            code = d.get("province_code") or n.split(":")[-1]
            provinces[code] = {"id": n, "th": d.get("name_th"), "en": names_en.get(code)}

    in_province: dict[str, list[str]] = {}  # asset/member id -> [province codes]
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "IN_PROVINCE":
            code = None
            if v in provinces.values():
                pass
            # v is a province node id like "province:13"
            pdata = g.nodes.get(v, {})
            if pdata.get("kind") == "province":
                code = pdata.get("province_code") or v.split(":")[-1]
            if code:
                in_province.setdefault(u, []).append(code)

    in_subbasin: dict[str, str] = {}
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "IN_SUBBASIN":
            in_subbasin[u] = v

    in_basin: dict[str, str] = {}
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "IN_BASIN":
            in_basin[u] = v

    on_reach: dict[str, tuple[str, float | None]] = {}
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "ON_REACH":
            on_reach[u] = (v, _num(d.get("distance_km")))

    responsible_for: dict[str, list[tuple[str, str]]] = {}  # target id -> [(agency_id, tag)]
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "RESPONSIBLE_FOR":
            responsible_for.setdefault(v, []).append((u, d.get("tag", "RELAYED")))

    owned_by_agency: dict[str, str] = {}  # asset id -> agency id, VERIFIED edge
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "OWNED_BY_AGENCY":
            owned_by_agency[u] = v

    reach_downstream: dict[str, str] = {}
    reach_ids = {n for n, d in g.nodes(data=True) if d.get("kind") == "river_reach"}
    for u, v, d in g.edges(data=True):
        if d.get("kind") == "WATER" and u in reach_ids and v in reach_ids:
            reach_downstream[u] = v

    agency_names: dict[str, str] = {
        n: d.get("name_th") for n, d in g.nodes(data=True) if d.get("kind") == "agency"
    }

    sub_basin_meta: dict[str, tuple[str, str, str]] = {}  # sb_code -> (name_th, basin_code, basin_name_th)
    for n, d in g.nodes(data=True):
        if d.get("kind") == "sub_basin":
            sub_basin_meta[n] = (d.get("name_th"), d.get("basin_code"), d.get("basin_name_th"))

    onwr_basin_names: dict[str, str] = {
        n: d.get("name_th") for n, d in g.nodes(data=True) if d.get("kind") == "asset" and d.get("class") == "basin"
    }

    # Asset rows (the 6 kept classes).
    asset_rows: dict[str, dict[str, Any]] = {}
    for n, d in g.nodes(data=True):
        if d.get("kind") != "asset" or d.get("class") not in ASSET_CLASSES:
            continue
        lat, lon = _num(d.get("lat")), _num(d.get("lon"))
        if lat is None or lon is None:
            continue
        reach, rkm = on_reach.get(n, (None, None))
        ms = None
        if reach is not None:
            rd = g.nodes.get(reach, {})
            ms = 1 if rd.get("main_stem") in (True, "True", "true") else 0
        asset_rows[n] = {
            "id": n,
            "n": d.get("name_th"),
            "k": d.get("class"),
            "lat": _r5(lat),
            "lon": _r5(lon),
            "ag": None,  # filled below via owner-name match if possible
            "sb": in_subbasin.get(n),
            "reach": reach,
            "rkm": _r3(rkm),
            "pv": None,  # filled per-province: e/b/n
        }

    # Rain-gauge member points (mp): coordinates only, used for bbox + candidate distance.
    rain_members: dict[str, list[tuple[str, float, float]]] = {}  # province code -> [(id, lat, lon)]
    for n, d in g.nodes(data=True):
        if d.get("kind") != "asset" or d.get("class") != "rain_gauge":
            continue
        lat, lon = _num(d.get("lat")), _num(d.get("lon"))
        if lat is None or lon is None:
            continue
        for code in in_province.get(n, []):
            rain_members.setdefault(code, []).append((n, lat, lon))

    # Member points for bbox purposes = gauges+rain_gauges with IN_PROVINCE (per F1/F2).
    member_points: dict[str, list[tuple[float, float]]] = {}
    for n, codes in in_province.items():
        d = g.nodes.get(n, {})
        if d.get("kind") != "asset":
            continue
        lat, lon = _num(d.get("lat")), _num(d.get("lon"))
        if lat is None or lon is None:
            continue
        for code in codes:
            member_points.setdefault(code, []).append((lat, lon))

    bboxes: dict[str, tuple[float, float, float, float]] = {}
    for code, pts in member_points.items():
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        s = math.floor(min(lats) * 1000) / 1000
        n_ = math.ceil(max(lats) * 1000) / 1000
        w = math.floor(min(lons) * 1000) / 1000
        e = math.ceil(max(lons) * 1000) / 1000
        bboxes[code] = (s, w, n_, e)

    def in_box(lat: float, lon: float, box: tuple[float, float, float, float]) -> bool:
        s, w, n_, e = box
        return s <= lat <= n_ and w <= lon <= e

    # Resolve pv for every (asset, province) placement.
    province_assets: dict[str, dict[str, dict[str, Any]]] = {code: {} for code in provinces}

    # (e) edge-linked placements.
    for n, codes in in_province.items():
        if n not in asset_rows:
            continue
        for code in codes:
            if code not in province_assets:
                continue
            row = dict(asset_rows[n])
            row["pv"] = "e"
            province_assets[code][n] = row

    # (b) box-contained placements for assets without any edge-linked row in that province.
    for n, row in asset_rows.items():
        lat, lon = row["lat"], row["lon"]
        if lat is None or lon is None:
            continue
        for code, box in bboxes.items():
            if n in province_assets.get(code, {}):
                continue
            if in_box(lat, lon, box):
                r = dict(row)
                r["pv"] = "b"
                province_assets[code][n] = r

    # (n) nearest-member fallback for assets placed nowhere by (e) or (b).
    placed_anywhere = set()
    for code, rows in province_assets.items():
        placed_anywhere.update(rows.keys())
    unplaced = [n for n in asset_rows if n not in placed_anywhere]
    # Build a flat list of edge-linked member points with their province code for nearest search.
    flat_members: list[tuple[str, float, float]] = []
    for code, pts in member_points.items():
        for (lat, lon) in pts:
            flat_members.append((code, lat, lon))
    for n in unplaced:
        row = asset_rows[n]
        lat, lon = row["lat"], row["lon"]
        if lat is None or lon is None or not flat_members:
            continue
        best_code, best_km = None, None
        for code, mlat, mlon in flat_members:
            km = haversine_km(lat, lon, mlat, mlon)
            if best_km is None or km < best_km:
                best_km, best_code = km, code
        if best_code:
            r = dict(row)
            r["pv"] = "n"
            province_assets[best_code][n] = r

    # Agency owner-name -> agency node name_th cross reference (best-effort, VERIFIED-only when exact).
    owner_to_agency: dict[str, str] = {}
    for n, d in g.nodes(data=True):
        if d.get("kind") == "agency":
            nm = d.get("name_th")
            if nm:
                owner_to_agency[nm.strip()] = n
    for n, d in g.nodes(data=True):
        if d.get("kind") == "asset" and d.get("class") in ASSET_CLASSES:
            if n not in asset_rows:
                continue
            # MED fix: the KG's own OWNED_BY_AGENCY edge (VERIFIED, from
            # sources/owner_agency_crosswalk.yaml) is the authoritative source
            # -- prefer it over the owner-NAME string match, which misses it
            # whenever the free-text `owner` field doesn't exactly match an
            # agency node's name_th.
            if n in owned_by_agency:
                asset_rows[n]["ag"] = owned_by_agency[n]
                continue
            owner = (d.get("owner") or "").strip() if isinstance(d.get("owner"), str) else None
            if owner and owner in owner_to_agency:
                asset_rows[n]["ag"] = owner_to_agency[owner]
    # Propagate the owner-agency id into every placed row copy.
    for rows in province_assets.values():
        for n, row in rows.items():
            row["ag"] = asset_rows[n]["ag"]

    os.makedirs(out_dir, exist_ok=True)

    a_cols = ["id", "n", "k", "lat", "lon", "ag", "sb", "reach", "rkm", "pv"]
    index_provs: dict[str, Any] = {}
    sizes: dict[str, int] = {}

    for code, meta in sorted(provinces.items()):
        rows = province_assets.get(code, {})
        row_list = [[r[c] for c in a_cols] for _id, r in sorted(rows.items())]

        sb_touch: dict[str, list] = {}
        onwr_touch: dict[str, list] = {}
        for n, r in rows.items():
            if r["pv"] != "e":
                continue
            sb = r.get("sb")
            if sb and sb not in sb_touch:
                nm, bcode, bname = sub_basin_meta.get(sb, (None, None, None))
                sb_touch[sb] = [nm, bcode, bname, 0]
            if sb:
                sb_touch[sb][3] += 1
            basin_id = in_basin.get(n)
            if basin_id and basin_id not in onwr_touch:
                onwr_touch[basin_id] = [onwr_basin_names.get(basin_id), 0]
            if basin_id:
                onwr_touch[basin_id][1] += 1

        reach_rows: dict[str, list] = {}
        for r in rows.values():
            reach = r.get("reach")
            if not reach or reach in reach_rows:
                continue
            rd = g.nodes.get(reach, {})
            so = rd.get("strahler_order")
            ms = 1 if rd.get("main_stem") in (True, "True", "true") else 0
            dn = reach_downstream.get(reach)
            reach_rows[reach] = [so, ms, dn]

        ag_ids = {r["ag"] for r in rows.values() if r.get("ag")}

        resp_rows = []
        prov_node = meta["id"]
        for agency_id, tag in sorted(responsible_for.get(prov_node, [])):
            resp_rows.append([agency_id, tag])
            ag_ids.add(agency_id)
        for basin_id in sorted(onwr_touch):
            for agency_id, tag in sorted(responsible_for.get(basin_id, [])):
                resp_rows.append([agency_id, tag + "-GENERAL" if "GENERAL" not in tag else tag, basin_id])
                ag_ids.add(agency_id)
        ag_names = {a: agency_names.get(a) for a in sorted(ag_ids)}

        mp = sorted({(round(lat, 5), round(lon, 5)) for (_n, lat, lon) in rain_members.get(code, [])})
        mp_list = [[lat, lon] for lat, lon in mp]

        b_count = sum(1 for r in rows.values() if r["pv"] == "b")
        e_count = sum(1 for r in rows.values() if r["pv"] == "e")
        n_count = sum(1 for r in rows.values() if r["pv"] == "n")
        on_reach_count = sum(1 for r in rows.values() if r["pv"] == "e" and r.get("reach"))

        gaps = []
        if e_count and (b_count + n_count):
            gaps.append(
                f"{b_count + n_count} of {len(rows)} gate/pump/weir/dam/tide_gate/gauge rows here have no "
                "IN_PROVINCE edge and were placed geometrically (pv=b/n), unconfirmed"
            )
        if e_count and on_reach_count == 0:
            gaps.append("0 ON_REACH among this province's IN_PROVINCE members")
        if not mp:
            gaps.append("no rain-gauge members in this province (mp is empty)")
        if code not in bboxes:
            gaps.append("no bbox for this province (no IN_PROVINCE gauge/rain_gauge members)")

        slice_obj = {
            "v": 1,
            "code": code,
            "th": meta["th"],
            "en": meta["en"],
            "kg_sha256": kg_sha256,
            "bbox": list(bboxes.get(code, [None, None, None, None])),
            "sb": {k: v for k, v in sorted(sb_touch.items())},
            "onwr": {k: v for k, v in sorted(onwr_touch.items())},
            "a_cols": a_cols,
            "a": row_list,
            "mp": mp_list,
            "r_cols": ["so", "ms", "dn"],
            "r": {k: v for k, v in sorted(reach_rows.items())},
            "ag": {k: v for k, v in sorted(ag_names.items())},
            "resp": resp_rows,
            "gaps": gaps,
        }
        out_path = os.path.join(out_dir, f"province_{code}.json")
        text = dumps(slice_obj)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        sizes[code] = len(text.encode("utf-8"))

        index_provs[code] = {
            "th": meta["th"],
            "en": meta["en"],
            "file": f"province_{code}.json",
            "bbox": list(bboxes.get(code, [None, None, None, None])),
            "n": {
                "mem": len(member_points.get(code, [])),
                "a": len(rows),
                "a_e": e_count,
                "a_b": b_count,
                "a_n": n_count,
                "on_reach": on_reach_count,
                "sb": len(sb_touch),
            },
        }

    index_obj = {
        "v": 1,
        "kg": {
            "file": "output/thailand_water_kg.graphml",
            "sha256": kg_sha256,
            "nodes": g.number_of_nodes(),
            "edges": g.number_of_edges(),
        },
        "a_cols": a_cols,
        "prov": index_provs,
        "gaps": GLOBAL_GAPS,
    }
    index_text = dumps(index_obj)
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        f.write(index_text)
    sizes["index"] = len(index_text.encode("utf-8"))

    return {"kg_sha256": kg_sha256, "sizes": sizes, "n_provinces": len(provinces)}


def main(argv: list[str] | None = None) -> int:
    result = build()
    sizes = sorted(v for k, v in result["sizes"].items() if k != "index")
    median = sizes[len(sizes) // 2] if sizes else 0
    print(
        f"kg_index built: {result['n_provinces']} provinces, kg_sha256={result['kg_sha256'][:12]}, "
        f"median_bytes={median}, max_bytes={max(sizes) if sizes else 0}, total_bytes={sum(sizes)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
