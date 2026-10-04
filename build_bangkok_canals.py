#!/usr/bin/env python3
"""
Bangkok canal (khlong) graph -- companion/extension to build_river_kg.py's major-river graph.

Fills the gap identified in conversation: build_river_kg.py only covers major rivers
(Strahler order >= 6), which sit ~10-20km from most inner-Bangkok districts (e.g.
เขตสะพานสูง / Saphan Sung) and are useless for assessing local flood risk there.
Local flood risk in Bangkok is driven by the KHLONG (canal) network, not the major rivers.

Source data (all free, no API key):
  - OSM waterways for Thailand (HOTOSM export via data.humdata.org/dataset/hotosm_tha_waterways),
    clipped to a Bangkok-area bbox. Gives canal LINE GEOMETRY, but NO flow-direction field
    (unlike HydroRIVERS' NEXT_DOWN).
  - BMA (Bangkok Metropolitan Administration) opendata (data.bangkok.go.th):
      * floodgate.csv -- floodgate/pump-station point locations (lat/long), 237 rows.
      * water_level_outer_daily.csv / water_level_inner_daily.csv -- 2026 daily max canal
        water level by station NAME (no lat/lon on these two files).
  - The existing build_river_kg.py major-river graph output (thailand_river_flow.jsonld) --
    used as candidate "sink" points where a canal could plausibly discharge into a major river.

## What this is NOT -- read this before trusting any edge direction

Unlike build_river_kg.py's major-river graph (direction = HydroRIVERS' own NEXT_DOWN field,
`finite_diagnostic` tier), THIS graph's edge directions are a `Dr`-tier (INSTINCT) heuristic:
for each connected component of the canal network that has a major-river node within
SINK_SNAP_KM of one of its junctions, this script orients that component's edges as a
shortest-path tree rooted at the nearest such junction, pointing every edge "toward" that
root -- i.e. assumes canals drain toward the nearest known major-river connection point.
This is NOT verified against any actual flow-direction data (no DEM routing was used, no
gate-operation schedule, no elevation data). Components with no nearby major-river sink are
left with `direction="unknown"` on every edge -- most of inner Bangkok's canal network will
fall in this bucket, because build_river_kg.py's major-river graph itself is sparse near central
Bangkok (nearest major-river nodes are people ~14-20km from central districts). Do not
present any edge's direction from this script as equivalent in reliability to build_river_kg.py's.

Usage:
    python3 build_bangkok_canals.py
"""
import csv
import json
import math
import re
from collections import defaultdict, deque
from difflib import SequenceMatcher
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
from scipy.spatial import Delaunay
from shapely.geometry import Point
from shapely.ops import linemerge, unary_union

HERE = Path(__file__).parent
RAW_GPKG = HERE / "raw" / "bangkok" / "hotosm_lines" / "hotosm_tha_waterways_lines_gpkg.gpkg"
FLOODGATE_CSV = HERE / "raw" / "bangkok" / "floodgate.csv"
WATER_LEVEL_CSVS = [
    HERE / "raw" / "bangkok" / "water_level_inner_daily.csv",
    HERE / "raw" / "bangkok" / "water_level_outer_daily.csv",
]
MAIN_RIVER_JSONLD = HERE / "output" / "thailand_river_flow.jsonld"
OUT_DIR = HERE / "output"

BANGKOK_BBOX = (100.32, 13.49, 100.95, 13.96)  # lon_min, lat_min, lon_max, lat_max
JUNCTION_SNAP_DEG = 0.0003   # ~33m at this latitude -- merges near-duplicate OSM endpoint vertices
SINK_SNAP_KM = 3.0           # how close a major-river node must be to a canal junction to "anchor" direction
FLOODGATE_JOIN_KM = 0.3      # nearest-edge join radius for floodgate points
WATER_LEVEL_MATCH_MIN_RATIO = 0.55  # Dr-tier judgment cutoff for accepting a fuzzy station<->floodgate name match

KLONGMAP_JSON = HERE / "raw" / "bangkok" / "klongmap_data.json"
KLONGMAP_MIN_ANCHORS = 3            # minimum calibration anchors (stations w/ schematic pos + real latlon) per canal to even attempt the 1D fit
KLONGMAP_NAME_MATCH_MIN_RATIO = 0.8 # fuzzy name-match cutoff, BMA river_name <-> OSM name/name:th
KLONGMAP_SPATIAL_SANITY_KM = 5.0    # candidate OSM geometry's centroid must be this close to the BMA anchors' centroid, else reject the name match
KLONGMAP_LOO_TRUST_KM = 0.15        # per-canal leave-one-out median haversine error must be <= this to trust/integrate the canal (~1/3 of this graph's median edge length, ~= its p25 edge length)
KLONGMAP_ARROW_ASSIGN_MAX_PX = None # computed per-canal from anchor PCA residuals; see assign_arrows_to_canals()
KLONGMAP_EDGE_SNAP_KM = 0.3         # how close a predicted arrow real-world position must be to a same-name graph edge to orient it
CANAL_NAME_PREFIXES = ["คลอง", "คูน้ำ", "คู", "บึง", "แม่น้ำ", "สถานตากอากาศ", "บ่อสูบน้ำ"]

# Delaunay rubber-sheeting (2026-09-23) -- literature-standard piecewise-affine conflation,
# whole-panel, all 199 station control points at once (not partitioned per-canal).
DELAUNAY_TRUST_KM = 0.15   # same bar as the per-canal bridge: local LOO error must be <= this
DELAUNAY_EDGE_SNAP_KM = 0.3  # how close a trusted, projected arrow must be to ANY graph edge to orient it (not restricted by canal name, unlike the 1D bridge)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def line_length_km(coords) -> float:
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        total += haversine_km(lat1, lon1, lat2, lon2)
    return total


def snap_key(lon: float, lat: float) -> tuple:
    """Round to a grid so near-duplicate OSM vertex coordinates land on the same junction node."""
    return (round(lon / JUNCTION_SNAP_DEG) * JUNCTION_SNAP_DEG, round(lat / JUNCTION_SNAP_DEG) * JUNCTION_SNAP_DEG)


def load_canal_lines() -> gpd.GeoDataFrame:
    if not RAW_GPKG.exists():
        raise SystemExit(
            f"Missing {RAW_GPKG}. Download it first:\n"
            "  curl -o raw/bangkok/hotosm_waterways_lines.gpkg.zip "
            "https://s3.dualstack.us-east-1.amazonaws.com/production-raw-data-api/ISO3/THA/waterways/lines/hotosm_tha_waterways_lines_gpkg.zip\n"
            "  unzip raw/bangkok/hotosm_waterways_lines.gpkg.zip -d raw/bangkok/hotosm_lines/\n"
        )
    gdf = gpd.read_file(RAW_GPKG, bbox=BANGKOK_BBOX)
    return gdf[gdf["waterway"].isin(["canal", "ditch", "stream", "river", "drain"])].copy()


def build_undirected_canal_graph(gdf: gpd.GeoDataFrame) -> nx.Graph:
    G = nx.Graph()
    for row in gdf.itertuples():
        geom = row.geometry
        if geom is None or geom.geom_type != "LineString":
            continue
        coords = list(geom.coords)
        if len(coords) < 2:
            continue
        a = snap_key(*coords[0])
        b = snap_key(*coords[-1])
        if a == b:
            continue  # degenerate loop-to-self at this snap tolerance
        length_km = line_length_km(coords)
        for node, xy in ((a, coords[0]), (b, coords[-1])):
            if node not in G:
                G.add_node(node, lon=node[0], lat=node[1])
        # Parallel OSM ways between the same two snapped junctions do happen (e.g. a canal
        # mapped in two segments with a slightly different vertex list) -- keep the
        # shortest such edge only, since networkx.Graph can't hold parallel edges and the
        # shortest is the more conservative (less likely to be a digitization artifact).
        if G.has_edge(a, b):
            if length_km >= G[a][b]["length_km"]:
                continue
        G.add_edge(
            a, b,
            waterway=row.waterway,
            name=(row.name if isinstance(row.name, str) and row.name else
                  (getattr(row, "name_th", None) or "unnamed")),
            osm_id=str(row.osm_id),
            length_km=round(length_km, 4),
        )
    return G


def load_sink_candidates() -> list:
    """Major-river graph nodes near Bangkok -- candidate discharge points for canals."""
    if not MAIN_RIVER_JSONLD.exists():
        print(f"[warn] {MAIN_RIVER_JSONLD} not found -- no sinks available, "
              "every canal component will be direction=unknown.")
        return []
    doc = json.loads(MAIN_RIVER_JSONLD.read_text())
    pad = 0.3
    lo_lon, lo_lat, hi_lon, hi_lat = (BANGKOK_BBOX[0] - pad, BANGKOK_BBOX[1] - pad,
                                       BANGKOK_BBOX[2] + pad, BANGKOK_BBOX[3] + pad)
    return [
        {"hyriv_id": n["hyriv_id"], "lat": n["lat"], "lon": n["lon"]}
        for n in doc["@graph"]
        if lo_lon <= n["lon"] <= hi_lon and lo_lat <= n["lat"] <= hi_lat
    ]


def orient_toward_nearest_sink(G: nx.Graph, sinks: list) -> nx.DiGraph:
    """
    Dr-tier heuristic direction assignment (see module docstring).

    For each connected component: find its junction node closest to ANY sink; if that
    distance is within SINK_SNAP_KM, run BFS from that junction and orient every tree edge
    from child -> parent (i.e. toward the sink-anchored junction = assumed downstream).
    Components with no sink within range get `direction="unknown"` and BOTH directions kept
    as edges (so the graph stays traversable, just without a claimed flow direction).
    """
    D = nx.DiGraph()
    for node, data in G.nodes(data=True):
        D.add_node(node, **data)

    n_anchored_components = 0
    n_unknown_components = 0
    for comp_nodes in nx.connected_components(G):
        comp = G.subgraph(comp_nodes)
        best_junction, best_dist = None, float("inf")
        if sinks:
            for node in comp_nodes:
                lon, lat = node[0], node[1]
                for sink in sinks:
                    d = haversine_km(lat, lon, sink["lat"], sink["lon"])
                    if d < best_dist:
                        best_dist, best_junction = d, node

        if best_junction is not None and best_dist <= SINK_SNAP_KM:
            n_anchored_components += 1
            # BFS tree from best_junction; orient each edge child->parent (toward sink-anchor)
            visited = {best_junction}
            queue = deque([best_junction])
            while queue:
                cur = queue.popleft()
                for nbr in comp.neighbors(cur):
                    if nbr in visited:
                        continue
                    visited.add(nbr)
                    edge_data = dict(comp[cur][nbr])
                    edge_data["direction_basis"] = "heuristic_nearest_river_sink"
                    edge_data["direction_confidence"] = "Dr"
                    edge_data["anchor_sink_dist_km"] = round(best_dist, 3)
                    D.add_edge(nbr, cur, **edge_data)  # nbr -> cur = toward the anchor
                    queue.append(nbr)
        else:
            n_unknown_components += 1
            for a, b, edata in comp.edges(data=True):
                edata = dict(edata)
                edata["direction_basis"] = "unknown"
                edata["direction_confidence"] = "unknown"
                edata["anchor_sink_dist_km"] = None
                D.add_edge(a, b, **edata)
                D.add_edge(b, a, **edata)  # both directions kept -- no claimed direction

    print(f"[direction] {n_anchored_components} component(s) anchored to a major-river sink "
          f"(<= {SINK_SNAP_KM} km), {n_unknown_components} component(s) direction=unknown")
    return D


def overlay_floodgates(D: nx.DiGraph, floodgate_csv: Path) -> None:
    import csv
    gates = []
    with open(floodgate_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                lat, lon = float(row["lat"]), float(row["long"])
            except (ValueError, KeyError):
                continue
            gates.append({"id": row.get("id"), "name": row.get("name"), "lat": lat, "lon": lon})

    for n, data in D.nodes(data=True):
        nearby = [g["name"] for g in gates if haversine_km(data["lat"], data["lon"], g["lat"], g["lon"]) <= FLOODGATE_JOIN_KM]
        data["nearby_floodgates_km_0.3"] = "; ".join(nearby) if nearby else None
    print(f"[floodgates] {len(gates)} floodgate/pump points loaded, "
          f"joined onto nodes within {FLOODGATE_JOIN_KM} km")


def _normalize_station_name(s: str) -> str:
    """Strip common floodgate/station prefixes and punctuation so fuzzy matching compares
    the canal-identifying substance of the name, not boilerplate ('ปตร.' / 'ประตูระบายน้ำ'
    both mean 'floodgate' and are used inconsistently across BMA's two datasets)."""
    s = s.replace("ปตร.", " ").replace("ประตูระบายน้ำ", " ")
    s = re.sub(r"[()\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def match_water_level_stations_to_floodgates(floodgate_csv: Path) -> dict:
    """
    Dr-tier fuzzy name match between the BMA daily water-level CSVs' WATER_STATION_NAME
    (no lat/lon on those files) and floodgate.csv's point locations (lat/long, but a
    differently-formatted name field). This was left as an explicit unblocked-next-step in
    the prior pass ("station names don't share a clean join key with floodgate.csv's point
    locations"). This function attempts that join via normalized SequenceMatcher ratio and
    keeps only matches at/above WATER_LEVEL_MATCH_MIN_RATIO -- a judgment-call cutoff, not a
    verified ground-truth join. Every accepted match's ratio is preserved on the output so
    it stays auditable rather than silently presented as certain.

    Returns {station_name: {"floodgate_name", "lat", "lon", "match_ratio"}}.

    IMPORTANT: this join gives WATER LEVEL AT A POINT, not flow direction. A single scalar
    reading at one station cannot establish which way water is moving without a second
    reference point or a time-lag signal -- neither is attempted here. Do not treat a
    successful match as a direction source.
    """
    gates = []
    with open(floodgate_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                lat, lon = float(row["lat"]), float(row["long"])
            except (ValueError, KeyError):
                continue
            name = row.get("name", "")
            gates.append({"name": name, "norm": _normalize_station_name(name), "lat": lat, "lon": lon})

    stations = set()
    for csv_path in WATER_LEVEL_CSVS:
        if not csv_path.exists():
            continue
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("WATER_STATION_NAME", "").strip()
                if name:
                    stations.add(name)

    matches = {}
    for station in stations:
        norm_station = _normalize_station_name(station)
        best_gate, best_ratio = None, 0.0
        for g in gates:
            ratio = SequenceMatcher(None, norm_station, g["norm"]).ratio()
            if ratio > best_ratio:
                best_ratio, best_gate = ratio, g
        if best_gate is not None and best_ratio >= WATER_LEVEL_MATCH_MIN_RATIO:
            matches[station] = {
                "floodgate_name": best_gate["name"],
                "lat": best_gate["lat"],
                "lon": best_gate["lon"],
                "match_ratio": round(best_ratio, 3),
            }
    print(f"[water-level join] {len(matches)}/{len(stations)} station name(s) matched to a "
          f"floodgate.csv point at ratio >= {WATER_LEVEL_MATCH_MIN_RATIO} (Dr-tier fuzzy match, "
          f"see match_ratio on each -- NOT a direction source, water level only)")
    return matches


def overlay_water_level_stations(D: nx.DiGraph, matches: dict) -> None:
    """Attach matched water-level station context onto graph nodes within FLOODGATE_JOIN_KM
    of the matched floodgate coordinate. Adds `nearby_water_level_stations` (station names)
    and `water_level_match_confidence` (min match_ratio among attached stations, Dr-tier)."""
    if not matches:
        for n, data in D.nodes(data=True):
            data["nearby_water_level_stations"] = None
        return
    for n, data in D.nodes(data=True):
        nearby = [
            (station, m["match_ratio"])
            for station, m in matches.items()
            if haversine_km(data["lat"], data["lon"], m["lat"], m["lon"]) <= FLOODGATE_JOIN_KM
        ]
        data["nearby_water_level_stations"] = "; ".join(s for s, _ in nearby) if nearby else None
        data["water_level_match_confidence"] = round(min(r for _, r in nearby), 3) if nearby else None


#
# --- 2026-09-23 per-canal 1D arc-length bridge (KlongMap -> real graph) ---
#
# See README_bangkok_canals.md "2026-09-23 per-canal 1D bridge" section for the full writeup
# and the honest leave-one-out numbers. Short version of the idea (requested by the maintainers,
# routed through the orchestrator, after the whole-panel 2D georeferencing attempt failed
# with median error ~0.8-3km because BMA's KlongMap is a non-metric schematic diagram):
#
# Instead of one 2D geographic transform across an entire mixed-canal schematic panel, do it
# PER NAMED CANAL, in 1D (arc-length fraction along that one canal only). A schematic diagram
# can badly distort relative scale BETWEEN different canals while still drawing any ONE canal
# as a roughly monotonic line along its own length -- so a 1D order-preserving map (schematic
# position -> real arc-length fraction), fit separately per canal, might survive the
# panel-wide distortion that broke the 2D fit. This section tests that claim empirically
# (leave-one-out, per canal) rather than assuming it.
#

def _strip_canal_prefix(name: str) -> str:
    name = (name or "").strip()
    for p in CANAL_NAME_PREFIXES:
        if name.startswith(p):
            return name[len(p):].strip()
    return name


def load_klongmap_anchors_and_arrows(path: Path = KLONGMAP_JSON):
    """
    Parse the cached KlongMap API response into:
      anchors: list of {canal, x, y, lat, lon} -- BMA water-quality/level stations that carry
        BOTH a schematic pixel position (waterStation[i].offset_x/offset_y, the MAIN panel
        coordinate frame used consistently by both stations and arrows) AND a real lat/lon
        (nested in waterStation[i].water_station_info.latitude/longitude, along with the
        canal's Thai name in water_station_info.river_name).
      arrows: list of {x, y, deg, arrow_map_id} -- arrowMap entries with a parsed rotation
        angle from the `configs` field ("width,height,NNNdeg,color"). Arrows carry NO canal
        name/id field in the raw data (verified: arrowMap's only keys are arrow_map_id,
        offset_x/offset_y, offset_x_area/offset_y_area, area_id, configs, reverse, flow_id,
        configs_reverse -- flow_id is null on every record checked) -- canal assignment has to
        be done spatially, see assign_arrows_to_canals().
    Both anchors and arrows are read in the SAME pixel coordinate frame (offset_x/offset_y,
    the single ~1000x2059 main SVG canvas), not the per-area offset_x_area/offset_y_area
    fields (those are only populated for a minority of records and would need an extra
    area_id join that buys nothing once everything is already in one shared frame).
    """
    if not path.exists():
        print(f"[klongmap] {path} not found -- skipping per-canal 1D bridge entirely.")
        return [], []
    data = json.loads(path.read_text())

    anchors = []
    for w in data.get("waterStation", []):
        info = w.get("water_station_info")
        ox, oy = w.get("offset_x"), w.get("offset_y")
        if info is None or ox is None or oy is None:
            continue
        lat, lon = info.get("latitude"), info.get("longitude")
        canal = info.get("river_name")
        if lat is None or lon is None or not canal:
            continue
        anchors.append({"canal": canal, "x": float(ox), "y": float(oy),
                         "lat": float(lat), "lon": float(lon), "water_id": w.get("water_id")})

    arrows = []
    for a in data.get("arrowMap", []):
        ox, oy, configs = a.get("offset_x"), a.get("offset_y"), a.get("configs")
        if ox is None or oy is None or not configs:
            continue
        parts = configs.split(",")
        try:
            deg = float(parts[2].replace("deg", ""))
        except (IndexError, ValueError):
            continue
        arrows.append({"x": float(ox), "y": float(oy), "deg": deg, "arrow_map_id": a.get("arrow_map_id")})

    print(f"[klongmap] loaded {len(anchors)} station anchors (schematic pos + real latlon) "
          f"across {len(set(a['canal'] for a in anchors))} distinct canal names, "
          f"{len(arrows)} arrows with a parsed rotation angle")
    return anchors, arrows


def _merge_osm_geometry_for_canal(gdf: gpd.GeoDataFrame, osm_name: str, anchor_latlons: list):
    """
    Collect all OSM lines with name == osm_name, linemerge them. If the result is
    disconnected (a MultiLineString -- common: OSM canal names are re-used on unconnected
    ditches, or the mapped segments simply don't share endpoints), keep only the single
    component that has the most anchors projecting onto it within KLONGMAP_EDGE_SNAP_KM --
    i.e. let the real calibration data pick the right piece of geometry, don't guess.
    Returns (LineString or None, list of accepted anchor indices).
    """
    cand = gdf[gdf["name"] == osm_name]
    if len(cand) == 0:
        return None, []
    geoms = list(cand.geometry)
    merged = geoms[0] if len(geoms) == 1 else linemerge(unary_union(geoms))
    if merged.geom_type == "LineString":
        lines = [merged]
    elif merged.geom_type == "MultiLineString":
        lines = list(merged.geoms)
    else:
        return None, []

    best_line, best_covered = None, []
    for line in lines:
        covered = []
        for i, (lat, lon) in enumerate(anchor_latlons):
            frac = line.project(Point(lon, lat), normalized=True)
            proj_pt = line.interpolate(frac, normalized=True)
            d_km = haversine_km(lat, lon, proj_pt.y, proj_pt.x)
            if d_km <= KLONGMAP_EDGE_SNAP_KM:
                covered.append(i)
        if len(covered) > len(best_covered):
            best_line, best_covered = line, covered
    return best_line, best_covered


def match_canal_to_osm(canal_name: str, anchor_latlons: list, gdf: gpd.GeoDataFrame):
    """
    Fuzzy-match a BMA river_name onto an OSM `name`/`name:th` value, with a mandatory spatial
    cross-check (a name match whose geometry sits nowhere near this canal's own known-latlon
    anchors is rejected, per the founder's instructions). Returns (osm_name, ratio, dist_km) or
    (None, ratio, dist_km) if rejected.
    """
    stripped_target = _strip_canal_prefix(canal_name)
    osm_names = set(gdf["name"].dropna().unique()) | set(gdf["name:th"].dropna().unique())

    exact = canal_name in osm_names
    if exact:
        best_name, best_ratio = canal_name, 1.0
    else:
        best_name, best_ratio = None, 0.0
        for nm in osm_names:
            ratio = SequenceMatcher(None, stripped_target, _strip_canal_prefix(nm)).ratio()
            if ratio > best_ratio:
                best_ratio, best_name = ratio, nm
        if best_ratio < KLONGMAP_NAME_MATCH_MIN_RATIO:
            return None, best_ratio, None

    # spatial sanity check: candidate OSM lines' centroid vs anchors' centroid
    cand = gdf[(gdf["name"] == best_name) | (gdf["name:th"] == best_name)]
    if len(cand) == 0:
        return None, best_ratio, None
    def _coords_of(geom):
        if geom is None:
            return []
        if geom.geom_type == "LineString":
            return list(geom.coords)
        if hasattr(geom, "geoms"):
            out = []
            for g in geom.geoms:
                out.extend(_coords_of(g))
            return out
        return []
    all_pts = [pt for geom in cand.geometry for pt in _coords_of(geom)]
    if not all_pts:
        return None, best_ratio, None
    cx = sum(p[0] for p in all_pts) / len(all_pts)
    cy = sum(p[1] for p in all_pts) / len(all_pts)
    ay = sum(lat for lat, lon in anchor_latlons) / len(anchor_latlons)
    ax = sum(lon for lat, lon in anchor_latlons) / len(anchor_latlons)
    dist_km = haversine_km(ay, ax, cy, cx)
    if dist_km > KLONGMAP_SPATIAL_SANITY_KM:
        return None, best_ratio, dist_km
    # prefer the plain `name` column when both name and name:th matched (used elsewhere as G's edge "name")
    canonical = best_name
    if not (gdf["name"] == best_name).any() and (gdf["name:th"] == best_name).any():
        alt = gdf.loc[gdf["name:th"] == best_name, "name"].dropna()
        if len(alt) > 0:
            canonical = alt.iloc[0]
    return canonical, best_ratio, dist_km


def fit_canal_1d_bridge(canal_name: str, anchors: list, gdf: gpd.GeoDataFrame) -> dict:
    """
    For ONE named canal: match to OSM geometry, fit schematic-arc-length-fraction ->
    real-arc-length-fraction via PCA (schematic) + line.project (real), and measure honest
    leave-one-out error. Returns a result dict (always, even on failure) with a `usable` flag
    and the full diagnostic numbers -- never silently drops a canal without a reason.
    """
    result = {"canal": canal_name, "n_anchors": len(anchors), "usable": False, "reason": None}
    if len(anchors) < KLONGMAP_MIN_ANCHORS:
        result["reason"] = f"only {len(anchors)} anchor(s), need >= {KLONGMAP_MIN_ANCHORS}"
        return result

    anchor_latlons = [(a["lat"], a["lon"]) for a in anchors]
    osm_name, ratio, dist_km = match_canal_to_osm(canal_name, anchor_latlons, gdf)
    result["osm_name_match"] = osm_name
    result["name_match_ratio"] = round(ratio, 3)
    result["name_match_spatial_dist_km"] = round(dist_km, 3) if dist_km is not None else None
    if osm_name is None:
        result["reason"] = "no OSM name match passed fuzzy-ratio + spatial sanity check"
        return result

    line, covered_idx = _merge_osm_geometry_for_canal(gdf, osm_name, anchor_latlons)
    if line is None or len(covered_idx) < KLONGMAP_MIN_ANCHORS:
        result["reason"] = (f"OSM geometry for '{osm_name}' found but only "
                             f"{len(covered_idx)} anchor(s) project within {KLONGMAP_EDGE_SNAP_KM}km of it "
                             f"(need >= {KLONGMAP_MIN_ANCHORS})")
        return result
    anchors = [anchors[i] for i in covered_idx]
    result["n_anchors_used"] = len(anchors)
    result["real_line_length_km"] = round(line_length_km(list(line.coords)), 3)

    # schematic 1D coordinate: PCA (first principal component) of the anchors' pixel positions
    xy = np.array([[a["x"], a["y"]] for a in anchors], dtype=float)
    mean = xy.mean(axis=0)
    centered = xy - mean
    if len(anchors) >= 2 and np.linalg.matrix_rank(centered) >= 1:
        u, s, vt = np.linalg.svd(centered, full_matrices=False)
        pca_axis = vt[0]  # unit vector, sign arbitrary but fixed for this canal
    else:
        pca_axis = np.array([1.0, 0.0])
    schem_proj = centered @ pca_axis  # scalar per anchor along the PCA axis

    real_frac = np.array([line.project(Point(a["lon"], a["lat"]), normalized=True) for a in anchors])

    # sign convention: does increasing schematic PCA projection track increasing real frac?
    if np.std(schem_proj) > 0:
        slope_sign = np.sign(np.corrcoef(schem_proj, real_frac)[0, 1]) or 1.0
    else:
        slope_sign = 1.0
    result["flip"] = bool(slope_sign < 0)

    order = np.argsort(schem_proj)
    xp = schem_proj[order]
    fp = real_frac[order]

    # leave-one-out
    errors_km, errors_along_km = [], []
    for k in range(len(anchors)):
        mask = np.ones(len(anchors), dtype=bool)
        mask[order[k]] = False
        # refit on remaining points (already sorted by schem_proj via `order`)
        remaining_order = [j for j in order if j != order[k]]
        xp_loo = schem_proj[remaining_order]
        fp_loo = real_frac[remaining_order]
        pred_frac = float(np.interp(schem_proj[order[k]], xp_loo, fp_loo))
        pred_frac = min(1.0, max(0.0, pred_frac))
        pred_pt = line.interpolate(pred_frac, normalized=True)
        true_a = anchors[order[k]]
        err_km = haversine_km(true_a["lat"], true_a["lon"], pred_pt.y, pred_pt.x)
        errors_km.append(err_km)
        errors_along_km.append(abs(pred_frac - real_frac[order[k]]) * result["real_line_length_km"])

    errors_km_sorted = sorted(errors_km)
    n = len(errors_km_sorted)
    result["loo_median_km"] = round(errors_km_sorted[n // 2], 4)
    result["loo_max_km"] = round(max(errors_km_sorted), 4)
    result["loo_mean_km"] = round(sum(errors_km_sorted) / n, 4)
    result["loo_median_along_canal_km"] = round(sorted(errors_along_km)[n // 2], 4)

    result["usable"] = result["loo_median_km"] <= KLONGMAP_LOO_TRUST_KM
    result["reason"] = (
        f"LOO median {result['loo_median_km']*1000:.0f}m <= trust threshold "
        f"{KLONGMAP_LOO_TRUST_KM*1000:.0f}m" if result["usable"] else
        f"LOO median {result['loo_median_km']*1000:.0f}m > trust threshold "
        f"{KLONGMAP_LOO_TRUST_KM*1000:.0f}m -- left as unknown, not force-integrated"
    )

    # keep the fitted objects (final fit, all anchors) for the integration step
    result["_line"] = line
    result["_pca_mean"] = mean
    result["_pca_axis"] = pca_axis
    result["_xp"] = xp
    result["_fp"] = fp
    result["_anchors"] = anchors
    return result


def run_klongmap_1d_bridge(gdf: gpd.GeoDataFrame) -> dict:
    """
    Run fit_canal_1d_bridge() for every candidate canal (name groups with >= KLONGMAP_MIN_ANCHORS
    station anchors) and return {canal_name: result_dict}. This is the "actually measure it"
    step -- every canal gets tried and its real LOO numbers recorded, whether it ends up
    usable or not.
    """
    anchors, arrows = load_klongmap_anchors_and_arrows()
    if not anchors:
        return {"_anchors": [], "_arrows": [], "_results": {}}

    by_canal = defaultdict(list)
    for a in anchors:
        by_canal[a["canal"]].append(a)

    results = {}
    for canal_name, canal_anchors in by_canal.items():
        if len(canal_anchors) < KLONGMAP_MIN_ANCHORS:
            continue  # not even attempted -- too few anchors to do a leave-one-out fit at all
        results[canal_name] = fit_canal_1d_bridge(canal_name, canal_anchors, gdf)

    n_attempted = len(results)
    n_usable = sum(1 for r in results.values() if r["usable"])
    print(f"[klongmap 1D bridge] {n_attempted} canal(s) had >= {KLONGMAP_MIN_ANCHORS} anchors and "
          f"were fit; {n_usable} passed the LOO trust threshold ({KLONGMAP_LOO_TRUST_KM*1000:.0f}m median)")
    return {"_anchors": anchors, "_arrows": arrows, "_results": results}


def _arrow_pixel_vector(deg: float) -> tuple:
    """CSS `rotate(deg)` applied to an up-pointing base vector (0,-1) in screen coords
    (x right, y down), clockwise-positive -- matches the README's confirmed reading of the
    KlongMap page's own inline JS (0deg = up-canvas). Verified against clock-hand intuition:
    0->up, 90->right, 180->down, 270->left."""
    rad = math.radians(deg)
    return (math.sin(rad), -math.cos(rad))


def assign_arrows_and_orient_edges(D: nx.DiGraph, G: nx.Graph, bridge: dict) -> list:
    """
    For every USABLE canal from run_klongmap_1d_bridge(): assign nearby arrows to it (nearest
    PCA line, within a per-canal residual-derived band), project each assigned arrow's
    schematic position to a real point via the fitted 1D map, snap that real point to the
    nearest same-name graph edge, and orient that edge using the arrow's rotation angle
    (converted to "toward increasing/decreasing real arc-length fraction" via the fitted
    sign convention). Mutates D in place (adds/overwrites directed edges with
    direction_basis="klongmap_1d_arc_length_bridge", tier "Dr"). Returns a log of per-arrow
    decisions for reporting.
    """
    results = bridge["_results"]
    arrows = bridge["_arrows"]
    usable = {name: r for name, r in results.items() if r["usable"]}
    if not usable or not arrows:
        return []

    # per-canal residual band (how far an anchor itself sits from its own PCA line) --
    # an arrow farther than this (with a floor) from a canal's PCA line is not this canal's.
    bands = {}
    for name, r in usable.items():
        xy = np.array([[a["x"], a["y"]] for a in r["_anchors"]], dtype=float)
        centered = xy - r["_pca_mean"]
        perp = np.array([[-r["_pca_axis"][1], r["_pca_axis"][0]]])  # perpendicular unit vector
        residuals = np.abs(centered @ perp[0])
        band = max(float(residuals.max()) * 1.5 if len(residuals) else 0.0, 25.0)  # px floor
        bands[name] = band

    edge_log = []
    n_assigned, n_oriented = 0, 0
    for arrow in arrows:
        best_name, best_dist = None, float("inf")
        for name, r in usable.items():
            v = np.array([arrow["x"], arrow["y"]]) - r["_pca_mean"]
            perp_axis = np.array([-r["_pca_axis"][1], r["_pca_axis"][0]])
            perp_dist = abs(float(v @ perp_axis))
            along = float(v @ r["_pca_axis"])
            span = r["_xp"].max() - r["_xp"].min()
            margin = span * 0.25 + 1e-6
            if r["_xp"].min() - margin <= along <= r["_xp"].max() + margin and perp_dist < bands[name]:
                if perp_dist < best_dist:
                    best_dist, best_name = perp_dist, name
        if best_name is None:
            continue
        n_assigned += 1
        r = usable[best_name]
        v = np.array([arrow["x"], arrow["y"]]) - r["_pca_mean"]
        along = float(v @ r["_pca_axis"])
        pred_frac = float(np.interp(along, r["_xp"], r["_fp"]))
        pred_frac = min(1.0, max(0.0, pred_frac))
        pred_pt = r["_line"].interpolate(pred_frac, normalized=True)

        vx, vy = _arrow_pixel_vector(arrow["deg"])
        dot = vx * r["_pca_axis"][0] + vy * r["_pca_axis"][1]
        points_toward_increasing_schem = dot > 0
        points_toward_increasing_real = points_toward_increasing_schem != r["flip"]  # XOR

        # snap to nearest same-name graph edge
        best_edge, best_edge_dist = None, float("inf")
        for a_node, b_node, edata in G.edges(data=True):
            if edata.get("name") != r["osm_name_match"]:
                continue
            for node in (a_node, b_node):
                d_km = haversine_km(pred_pt.y, pred_pt.x, node[1], node[0])
                if d_km < best_edge_dist:
                    best_edge_dist, best_edge = d_km, (a_node, b_node)
        if best_edge is None or best_edge_dist > KLONGMAP_EDGE_SNAP_KM:
            edge_log.append({"canal": best_name, "arrow_map_id": arrow["arrow_map_id"],
                              "assigned": True, "oriented": False,
                              "reason": f"no same-name graph edge within {KLONGMAP_EDGE_SNAP_KM}km"})
            continue

        a_node, b_node = best_edge
        frac_a = r["_line"].project(Point(a_node[0], a_node[1]), normalized=True)
        frac_b = r["_line"].project(Point(b_node[0], b_node[1]), normalized=True)
        lo_node, hi_node = (a_node, b_node) if frac_a <= frac_b else (b_node, a_node)
        src, dst = (lo_node, hi_node) if points_toward_increasing_real else (hi_node, lo_node)

        edata = dict(G[a_node][b_node])
        edata["direction_basis"] = "klongmap_1d_arc_length_bridge"
        edata["direction_confidence"] = "Dr"
        edata["klongmap_canal"] = best_name
        edata["klongmap_arrow_map_id"] = arrow["arrow_map_id"]
        edata["klongmap_edge_snap_km"] = round(best_edge_dist, 4)
        # remove the generic unknown/heuristic edges between this pair (both directions) so
        # this more specific, better-grounded source is the one that governs this edge
        for u, v_ in ((a_node, b_node), (b_node, a_node)):
            if D.has_edge(u, v_):
                D.remove_edge(u, v_)
        D.add_edge(src, dst, **edata)
        n_oriented += 1
        edge_log.append({"canal": best_name, "arrow_map_id": arrow["arrow_map_id"],
                          "assigned": True, "oriented": True,
                          "edge": (node_id_str(src), node_id_str(dst)),
                          "edge_snap_km": round(best_edge_dist, 4)})

    print(f"[klongmap 1D bridge] {n_assigned}/{len(arrows)} arrows assigned to a usable canal, "
          f"{n_oriented} graph edge(s) newly oriented via klongmap_1d_arc_length_bridge")
    return edge_log


def _fit_triangle_affines(simplices: np.ndarray, pts: np.ndarray, real: np.ndarray) -> list:
    """
    For each Delaunay simplex (3 vertex indices), solve the EXACT affine map
    real = A @ schem + t through its 3 corner control points (3 correspondences fully
    determine a 2D affine transform -- no least squares needed, no residual). Returns a list
    of (A [2x2], t [2,]) parallel to `simplices`. This is the barycentric-equivalent
    "rubber sheeting" affine per triangle described in the GIS literature (ESRI's "rubber
    sheeting" dictionary entry; piecewise-linear conflation of a schematic to a geographic
    reference using triangulated control points).
    """
    affines = []
    for simplex in simplices:
        S = pts[simplex]          # 3x2 schematic (x, y)
        Rr = real[simplex]        # 3x2 real (lon, lat)
        M = np.hstack([S, np.ones((3, 1))])  # 3x3
        sol = np.linalg.solve(M, Rr)          # 3x2: rows = [a_row0, a_row1, t] per real dim... see below
        A = sol[:2, :].T           # 2x2: real = A @ schem + t
        t = sol[2, :]
        affines.append((A, t))
    return affines


def _find_simplex_or_nearest(tri: Delaunay, pts: np.ndarray, p: np.ndarray):
    """Locate the Delaunay simplex containing point p. If p is outside the convex hull of the
    control points (find_simplex returns -1), fall back to the NEAREST triangle by centroid
    distance and flag the result as extrapolated -- affine maps are defined everywhere, just
    less trustworthy outside their own triangle, per standard rubber-sheeting practice."""
    isimplex = int(tri.find_simplex(p))
    if isimplex >= 0:
        return isimplex, False
    centroids = pts[tri.simplices].mean(axis=1)
    isimplex = int(np.argmin(np.sum((centroids - p) ** 2, axis=1)))
    return isimplex, True


def _project_rubber_sheet(tri: Delaunay, pts: np.ndarray, affines: list, p: np.ndarray):
    """Project schematic point p=(x,y) to real (lon,lat) via the Delaunay rubber-sheet.
    Returns (lon, lat, isimplex, extrapolated)."""
    isimplex, extrapolated = _find_simplex_or_nearest(tri, pts, p)
    A, t = affines[isimplex]
    real_pt = A @ p + t
    return float(real_pt[0]), float(real_pt[1]), isimplex, extrapolated


def build_delaunay_rubber_sheet(anchors: list) -> dict:
    """
    Build a whole-panel Delaunay-triangulation rubber-sheet from ALL 199 station control
    points at once (schematic x,y -> real lon,lat), per literature referenced by the maintainers
    method (ESRI "rubber sheeting"; piecewise-linear conflation via triangulated control
    points -- standard practice for georeferencing a non-metric/schematic diagram, distinct
    from both the earlier whole-panel 2D affine/kNN attempt and the per-canal 1D arc-length
    attempt in this file). Deduplicates anchors at (near-)identical schematic pixel positions
    first -- scipy.spatial.Delaunay raises QhullError on exactly-coincident input points.
    """
    seen = {}
    for a in anchors:
        key = (round(a["x"], 3), round(a["y"], 3))
        seen.setdefault(key, a)  # keep first occurrence at a given pixel position
    uniq = list(seen.values())
    pts = np.array([[a["x"], a["y"]] for a in uniq], dtype=float)
    real = np.array([[a["lon"], a["lat"]] for a in uniq], dtype=float)
    tri = Delaunay(pts)
    affines = _fit_triangle_affines(tri.simplices, pts, real)
    return {"tri": tri, "pts": pts, "real": real, "affines": affines, "anchors": uniq}


def loo_validate_delaunay_rubber_sheet(anchors: list) -> dict:
    """
    Rigorous leave-one-out validation, same discipline as the per-canal 1D bridge and the
    earlier whole-panel affine/kNN attempts: for each of the (deduplicated) station control
    points, remove it, REBUILD the triangulation from the rest, project the held-out point's
    own schematic position through that rebuilt triangulation, and measure the haversine
    error against its own known true lat/lon. Requires >= 4 remaining points (a triangulation
    needs a non-degenerate point set); stations that can't be tested this way are skipped and
    reported as such, not silently dropped.
    """
    seen = {}
    for a in anchors:
        key = (round(a["x"], 3), round(a["y"], 3))
        seen.setdefault(key, a)
    uniq = list(seen.values())
    n = len(uniq)
    pts_all = np.array([[a["x"], a["y"]] for a in uniq], dtype=float)
    real_all = np.array([[a["lon"], a["lat"]] for a in uniq], dtype=float)

    per_station = []
    n_skipped = 0
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        pts_loo = pts_all[mask]
        real_loo = real_all[mask]
        if len(pts_loo) < 4:
            n_skipped += 1
            continue
        try:
            tri_loo = Delaunay(pts_loo)
        except Exception as exc:  # pragma: no cover -- degenerate point configuration
            n_skipped += 1
            continue
        affines_loo = _fit_triangle_affines(tri_loo.simplices, pts_loo, real_loo)
        pred_lon, pred_lat, _, extrapolated = _project_rubber_sheet(
            tri_loo, pts_loo, affines_loo, pts_all[i]
        )
        true_lat, true_lon = uniq[i]["lat"], uniq[i]["lon"]
        err_km = haversine_km(true_lat, true_lon, pred_lat, pred_lon)
        per_station.append({
            "canal": uniq[i]["canal"], "err_km": err_km, "extrapolated": extrapolated,
        })

    errs = sorted(s["err_km"] for s in per_station)
    m = len(errs)
    in_hull = [s for s in per_station if not s["extrapolated"]]
    extrap = [s for s in per_station if s["extrapolated"]]
    summary = {
        "n_tested": m,
        "n_skipped": n_skipped,
        "n_in_hull": len(in_hull),
        "n_extrapolated": len(extrap),
        "median_km": round(errs[m // 2], 4) if m else None,
        "mean_km": round(sum(errs) / m, 4) if m else None,
        "max_km": round(max(errs), 4) if m else None,
        "in_hull_median_km": round(sorted(s["err_km"] for s in in_hull)[len(in_hull) // 2], 4) if in_hull else None,
        "extrapolated_median_km": round(sorted(s["err_km"] for s in extrap)[len(extrap) // 2], 4) if extrap else None,
        "n_under_150m": sum(1 for e in errs if e <= 0.15),
        "per_station": per_station,
    }
    return summary


def _build_local_trust_by_index(rs: dict, anchors_uniq: list) -> dict:
    """
    Build a per-simplex trust proxy for the FULL (all-199) triangulation `rs`: for each
    control point, leave it out, rebuild a triangulation from the rest, project it back, and
    record its own LOO error indexed by its position in `rs["anchors"]` (the exact
    deduplicated list, same order `rs` was built from). Then for each simplex in the full
    triangulation, average the LOO error of its own 3 corner stations. Returns
    {isimplex_in_full_triangulation: mean_of_3_corner_err_km (or None if unavailable)}. This
    operationalizes "some triangles are locally trustworthy, some are not" -- station density
    is uneven across the panel, so LOO error is uneven too.
    """
    n = len(anchors_uniq)
    pts_all = rs["pts"]
    real_all = rs["real"]
    err_by_index = [None] * n
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        pts_loo = pts_all[mask]
        real_loo = real_all[mask]
        if len(pts_loo) < 4:
            continue
        try:
            tri_loo = Delaunay(pts_loo)
        except Exception:
            continue
        affines_loo = _fit_triangle_affines(tri_loo.simplices, pts_loo, real_loo)
        pred_lon, pred_lat, _, _ = _project_rubber_sheet(tri_loo, pts_loo, affines_loo, pts_all[i])
        true_lat, true_lon = anchors_uniq[i]["lat"], anchors_uniq[i]["lon"]
        err_by_index[i] = haversine_km(true_lat, true_lon, pred_lat, pred_lon)

    tri = rs["tri"]
    local_trust = {}
    for isimplex, simplex in enumerate(tri.simplices):
        corner_errs = [err_by_index[j] for j in simplex if err_by_index[j] is not None]
        local_trust[isimplex] = (sum(corner_errs) / len(corner_errs)) if corner_errs else None
    return local_trust


def _bearing_from_pixel_deg(A: np.ndarray, deg: float, mean_lat: float) -> float:
    """
    Convert a KlongMap arrow's schematic rotation angle to a real-world compass bearing, using
    the LOCAL triangle's affine linear part A (not just reusing the raw pixel degree value, per
    the founder's instructions). `_arrow_pixel_vector(deg)` gives the arrow's unit direction in schematic
    pixel space (x right, y down, per the confirmed CSS rotate() convention). A maps a
    schematic DELTA to a real (dlon, dlat) delta (A is the same for the whole triangle,
    translation-independent). Converts that to a compass bearing (degrees clockwise from true
    north), correcting dlon for longitude compression at this latitude (cos(lat)).
    """
    vx, vy = _arrow_pixel_vector(deg)
    d_real = A @ np.array([vx, vy])
    dlon, dlat = float(d_real[0]), float(d_real[1])
    east = dlon * math.cos(math.radians(mean_lat))
    north = dlat
    bearing = math.degrees(math.atan2(east, north)) % 360.0
    return bearing


def assign_arrows_via_delaunay_rubber_sheet(D: nx.DiGraph, G: nx.Graph, rs: dict,
                                             local_trust: dict, arrows: list) -> list:
    """
    For every arrow: project its schematic position through the whole-panel Delaunay
    rubber-sheet, look up its enclosing/nearest triangle's local-trust proxy (mean LOO error
    of that triangle's own 3 corner stations), and only integrate it if:
      (a) the point fell INSIDE the convex hull of control points (not extrapolated), and
      (b) that triangle's local-trust proxy is <= DELAUNAY_TRUST_KM (150m).
    Trusted arrows are snapped to the nearest graph edge (any canal name -- unlike the 1D
    bridge, the whole-panel method isn't partitioned by canal) within DELAUNAY_EDGE_SNAP_KM,
    oriented via a bearing computed from the LOCAL triangle's affine rotation (not the raw
    schematic degree value), and only overwrite edges that are currently direction="unknown"
    (never overrides the existing heuristic_nearest_river_sink claim, which is a separate,
    already-integrated direction source). Returns a per-arrow decision log.
    """
    tri, pts, affines = rs["tri"], rs["pts"], rs["affines"]
    mean_lat = float(rs["real"][:, 1].mean())
    log = []
    n_trusted, n_snapped, n_oriented = 0, 0, 0
    for arrow in arrows:
        p = np.array([arrow["x"], arrow["y"]], dtype=float)
        lon, lat, isimplex, extrapolated = _project_rubber_sheet(tri, pts, affines, p)
        trust_km = local_trust.get(isimplex)
        entry = {"arrow_map_id": arrow["arrow_map_id"], "lon": round(lon, 6), "lat": round(lat, 6),
                 "extrapolated": extrapolated, "local_trust_km": round(trust_km, 4) if trust_km is not None else None,
                 "trusted": False, "snapped": False, "oriented": False}
        if extrapolated or trust_km is None or trust_km > DELAUNAY_TRUST_KM:
            log.append(entry)
            continue
        entry["trusted"] = True
        n_trusted += 1

        # snap to nearest graph node/edge within DELAUNAY_EDGE_SNAP_KM
        best_edge, best_dist = None, float("inf")
        for a_node, b_node in G.edges():
            for node in (a_node, b_node):
                d_km = haversine_km(lat, lon, node[1], node[0])
                if d_km < best_dist:
                    best_dist, best_edge = d_km, (a_node, b_node)
        if best_edge is None or best_dist > DELAUNAY_EDGE_SNAP_KM:
            entry["reason"] = f"no graph edge within {DELAUNAY_EDGE_SNAP_KM}km of projected point"
            log.append(entry)
            continue
        entry["snapped"] = True
        entry["edge_snap_km"] = round(best_dist, 4)
        n_snapped += 1

        a_node, b_node = best_edge
        cur = D.get_edge_data(a_node, b_node) or D.get_edge_data(b_node, a_node)
        if cur is not None and cur.get("direction_basis") not in (None, "unknown"):
            entry["reason"] = f"edge already has a direction claim ({cur.get('direction_basis')}); not overridden"
            log.append(entry)
            continue

        A, _t = affines[isimplex]
        bearing = _bearing_from_pixel_deg(A, arrow["deg"], mean_lat)
        bearing_rad = math.radians(bearing)
        bx, by = math.sin(bearing_rad), math.cos(bearing_rad)  # (east, north) unit vector

        # orient a_node -> b_node vs b_node -> a_node by which alignment matches the bearing
        d_east = (b_node[0] - a_node[0]) * math.cos(math.radians(mean_lat))
        d_north = (b_node[1] - a_node[1])
        norm = math.hypot(d_east, d_north) or 1.0
        dot = (d_east / norm) * bx + (d_north / norm) * by
        src, dst = (a_node, b_node) if dot >= 0 else (b_node, a_node)

        edata = dict(G[a_node][b_node])
        edata["direction_basis"] = "klongmap_delaunay_rubber_sheet"
        edata["direction_confidence"] = "Dr"
        edata["klongmap_arrow_map_id"] = arrow["arrow_map_id"]
        edata["klongmap_bearing_deg"] = round(bearing, 1)
        edata["klongmap_local_trust_km"] = round(trust_km, 4)
        edata["klongmap_edge_snap_km"] = round(best_dist, 4)
        for u, v_ in ((a_node, b_node), (b_node, a_node)):
            if D.has_edge(u, v_):
                D.remove_edge(u, v_)
        D.add_edge(src, dst, **edata)
        n_oriented += 1
        entry["oriented"] = True
        entry["edge"] = (node_id_str(src), node_id_str(dst))
        log.append(entry)

    print(f"[delaunay rubber-sheet] {n_trusted}/{len(arrows)} arrows passed the local-trust gate, "
          f"{n_snapped} snapped to a nearby graph edge, {n_oriented} graph edge(s) newly oriented "
          f"via klongmap_delaunay_rubber_sheet")
    return log


def node_id_str(node: tuple) -> str:
    return f"{node[0]:.5f},{node[1]:.5f}"


def export_graphml(D: nx.DiGraph, path: Path) -> None:
    H = nx.DiGraph()
    for n, d in D.nodes(data=True):
        clean = {k: ("null" if v is None else v) for k, v in d.items()}
        H.add_node(node_id_str(n), **clean)
    for a, b, d in D.edges(data=True):
        clean = {k: ("null" if v is None else v) for k, v in d.items()}
        H.add_edge(node_id_str(a), node_id_str(b), **clean)
    nx.write_graphml(H, path)


def export_jsonld(D: nx.DiGraph, path: Path) -> None:
    context = {
        "@vocab": "https://schema.org/",
        "flowsInto": {"@id": "https://schema.org/isPartOf", "@type": "@id"},
        "bkk": "https://data.bangkok.go.th/vocab#",
    }
    nodes = []
    for n, d in D.nodes(data=True):
        nid = node_id_str(n)
        nodes.append({
            "@id": f"canaljunction:{nid}",
            "@type": "bkk:CanalJunction",
            "junction_id": nid,
            **{k: v for k, v in d.items()},
            "flowsInto": [f"canaljunction:{node_id_str(succ)}" for succ in D.successors(n)],
        })
    path.write_text(json.dumps({"@context": context, "@graph": nodes}, ensure_ascii=False, indent=2))


def saphan_sung_demo(D: nx.DiGraph) -> None:
    target_lat, target_lon = 13.7734, 100.6835  # เขตสะพานสูง (approx)
    dists = sorted(
        ((haversine_km(target_lat, target_lon, d["lat"], d["lon"]), n, d) for n, d in D.nodes(data=True)),
        key=lambda t: t[0],
    )
    print(f"\n=== เขตสะพานสูง demo (target {target_lat},{target_lon}) ===")
    print("Nearest canal junctions:")
    for dist, n, d in dists[:8]:
        out_edges = list(D.successors(n))
        basis = D[n][out_edges[0]]["direction_basis"] if out_edges else "n/a"
        print(f"  {dist*1000:.0f} m away | junction={node_id_str(n)} | "
              f"floodgates_nearby={d.get('nearby_floodgates_km_0.3')} | "
              f"out_degree={len(out_edges)} | direction_basis={basis}")


def print_klongmap_bridge_report(G: nx.Graph, D: nx.DiGraph, bridge: dict, edge_log: list) -> None:
    results = bridge.get("_results", {})
    if not results:
        return
    print("\n=== KlongMap per-canal 1D bridge -- leave-one-out results ===")
    print(f"{'canal':<28}{'anchors':>8}{'OSM match':<26}{'ratio':>6}{'LOO med(m)':>11}{'LOO max(m)':>11}  usable")
    for name, r in sorted(results.items(), key=lambda kv: kv[1].get("loo_median_km", 999)):
        if "loo_median_km" not in r:
            print(f"{name:<28}{r['n_anchors']:>8}  -- not fit: {r['reason']}")
            continue
        med_m = r["loo_median_km"] * 1000
        max_m = r["loo_max_km"] * 1000
        print(f"{name:<28}{r['n_anchors_used']:>8}{str(r['osm_name_match']):<26}{r['name_match_ratio']:>6.2f}"
              f"{med_m:>11.0f}{max_m:>11.0f}  {r['usable']}")

    n_usable = sum(1 for r in results.values() if r.get("usable"))
    n_oriented = sum(1 for e in edge_log if e.get("oriented"))
    edge_dir_known = sum(1 for _, _, d in D.edges(data=True) if d.get("direction_basis") != "unknown")
    total_undirected_edges = G.number_of_edges()
    print(f"\n{n_usable}/{len(results)} canal(s) passed the LOO trust threshold "
          f"({KLONGMAP_LOO_TRUST_KM*1000:.0f}m median error) and were eligible for integration.")
    print(f"{n_oriented} graph edge(s) newly oriented via klongmap_1d_arc_length_bridge.")
    print(f"Total edges with a claimed direction (any basis) after this run: "
          f"{edge_dir_known}/{total_undirected_edges}")


def print_delaunay_rubber_sheet_report(loo_summary: dict, arrow_log: list) -> None:
    print("\n=== Delaunay rubber-sheeting (whole-panel, 2026-09-23) -- leave-one-out results ===")
    print(f"Tested {loo_summary['n_tested']} station(s) ({loo_summary['n_skipped']} skipped -- "
          f"too few remaining points to rebuild a triangulation without them).")
    print(f"  median error: {loo_summary['median_km']*1000:.0f} m" if loo_summary['median_km'] is not None else "  median: n/a")
    print(f"  mean error:   {loo_summary['mean_km']*1000:.0f} m" if loo_summary['mean_km'] is not None else "  mean: n/a")
    print(f"  max error:    {loo_summary['max_km']*1000:.0f} m" if loo_summary['max_km'] is not None else "  max: n/a")
    print(f"  {loo_summary['n_under_150m']}/{loo_summary['n_tested']} station(s) had LOO error <= 150m")
    print(f"  in-hull (interpolated): {loo_summary['n_in_hull']} station(s)"
          + (f", median {loo_summary['in_hull_median_km']*1000:.0f} m" if loo_summary['in_hull_median_km'] is not None else ""))
    print(f"  outside hull (extrapolated): {loo_summary['n_extrapolated']} station(s)"
          + (f", median {loo_summary['extrapolated_median_km']*1000:.0f} m" if loo_summary['extrapolated_median_km'] is not None else ""))

    n_trusted = sum(1 for e in arrow_log if e.get("trusted"))
    n_snapped = sum(1 for e in arrow_log if e.get("snapped"))
    n_oriented = sum(1 for e in arrow_log if e.get("oriented"))
    print(f"\nArrows: {len(arrow_log)} total, {n_trusted} passed the local-trust gate "
          f"(<= {DELAUNAY_TRUST_KM*1000:.0f}m local LOO proxy, not extrapolated), "
          f"{n_snapped} snapped to a graph edge, {n_oriented} edges newly oriented.")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading Bangkok-clipped OSM waterway lines...")
    gdf = load_canal_lines()
    print(f"  {len(gdf)} canal/ditch/stream/river/drain lines in bbox")

    print("Building undirected canal junction graph (snap tolerance ~33m)...")
    G = build_undirected_canal_graph(gdf)
    print(f"  {G.number_of_nodes()} junction nodes, {G.number_of_edges()} canal-segment edges")

    print("Loading major-river graph nodes near Bangkok as sink candidates...")
    sinks = load_sink_candidates()
    print(f"  {len(sinks)} candidate sink node(s)")

    print("Assigning direction (Dr-tier heuristic, see module docstring)...")
    D = orient_toward_nearest_sink(G, sinks)

    print("Running per-canal 1D arc-length bridge (KlongMap arrow data, 2026-09-23)...")
    bridge = run_klongmap_1d_bridge(gdf)
    klongmap_log = assign_arrows_and_orient_edges(D, G, bridge)

    print("Running whole-panel Delaunay rubber-sheeting (KlongMap arrow data, 2026-09-23)...")
    dt_anchors, dt_arrows = bridge.get("_anchors", []), bridge.get("_arrows", [])
    delaunay_loo_summary = None
    delaunay_arrow_log = []
    if len(dt_anchors) >= 4 and dt_arrows:
        rs = build_delaunay_rubber_sheet(dt_anchors)
        delaunay_loo_summary = loo_validate_delaunay_rubber_sheet(dt_anchors)
        local_trust = _build_local_trust_by_index(rs, rs["anchors"])
        delaunay_arrow_log = assign_arrows_via_delaunay_rubber_sheet(D, G, rs, local_trust, dt_arrows)
    else:
        print("  skipped -- not enough anchors/arrows loaded")

    print("Overlaying BMA floodgate/pump-station points...")
    overlay_floodgates(D, FLOODGATE_CSV)

    print("Matching BMA water-level station names to floodgate.csv coordinates (Dr-tier fuzzy join)...")
    wl_matches = match_water_level_stations_to_floodgates(FLOODGATE_CSV)
    overlay_water_level_stations(D, wl_matches)

    graphml_path = OUT_DIR / "bangkok_canals.graphml"
    jsonld_path = OUT_DIR / "bangkok_canals.jsonld"
    export_graphml(D, graphml_path)
    export_jsonld(D, jsonld_path)
    print(f"Wrote {graphml_path}")
    print(f"Wrote {jsonld_path}")

    print_klongmap_bridge_report(G, D, bridge, klongmap_log)
    if delaunay_loo_summary is not None:
        print_delaunay_rubber_sheet_report(delaunay_loo_summary, delaunay_arrow_log)

    # component-level direction coverage (comparable to the "380/2,595" baseline figure)
    n_components = 0
    n_components_any_direction = 0
    for comp_nodes in nx.connected_components(G):
        n_components += 1
        has_direction = False
        for a, b in G.subgraph(comp_nodes).edges():
            d = D.get_edge_data(a, b) or D.get_edge_data(b, a)
            if d and d.get("direction_basis") != "unknown":
                has_direction = True
                break
        if has_direction:
            n_components_any_direction += 1
    print(f"\n[coverage] {n_components_any_direction}/{n_components} connected components have "
          f"at least one edge with a claimed direction (any basis) -- baseline before this "
          f"session's klongmap bridge was 380/2,595 from heuristic_nearest_river_sink alone.")

    saphan_sung_demo(D)


if __name__ == "__main__":
    main()
