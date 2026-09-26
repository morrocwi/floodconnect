#!/usr/bin/env python3
"""
2026-09-23 -- 4th attempt at extracting SOME direction signal from BMA KlongMap for the
Bangkok canal graph. NOT the precise-georeferencing approach (that's dead, confirmed 3x --
see README_bangkok_canals.md). This is the maintainers' different idea, routed through the
orchestrator: use KlongMap arrow directions as a WEAK LOCAL PRIOR (schematic-local-cluster
bearing trend, rotation-corrected via each station's nearest-neighbor bearing in both spaces)
and empirically test whether it AGREES with ground truth often enough to be worth anything as
a corroborating tie-breaker for otherwise-unknown canal components.

This script ONLY measures the calibration/agreement rate. It does not touch
build_bangkok_canals.py. Ground truth = build_kg.py's major-river graph, whose direction is
`finite_diagnostic` tier (HydroRIVERS' own NEXT_DOWN field) -- i.e. real, non-heuristic
direction. For every KlongMap real-coordinate station (199 total) that has >=1 nearby arrow
in schematic-pixel space, and that also sits within some real-world radius of a major-river
edge, we compute:
  - the KlongMap-derived local real-world bearing estimate (see below), and
  - the true bearing of the nearest major-river edge (node -> its NEXT_DOWN successor),
and check whether they agree (angular difference <= AGREE_THRESHOLD_DEG, i.e. "roughly same
direction" as opposed to "roughly opposite/orthogonal").

Method for the KlongMap-derived local bearing estimate, per station S:
  1. Local schematic bearing trend: circular mean of the CSS-rotate-convention pixel bearing
     (0deg = up-canvas, clockwise) of every arrow within ARROW_RADIUS_PX of S in schematic
     (offset_x, offset_y) space.
  2. Local rotation estimate (Dr): S's K_NEIGHBORS nearest other real-coordinate stations by
     schematic pixel distance. For each such neighbor N, compute bearing(S->N) in schematic
     pixel space (same CSS-rotate convention) and bearing(S->N) in real lat/lon space (compass
     bearing, cos(lat)-corrected). rotation_offset = circular_mean(bearing_real - bearing_pixel)
     across those neighbors -- a small, local, defensible rotation estimate, NOT a panel-wide
     assumption.
  3. real_world_bearing_estimate = (local_schematic_bearing_trend + rotation_offset) mod 360.

This is intentionally a much smaller extrapolation than the failed whole-panel/per-canal
attempts: it never assumes a global scale or a single panel-wide rotation, only that a
station's immediate neighborhood (a handful of stations within ~100px, a few hundred meters
of schematic drawing) is not wildly re-rotated relative to itself.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
KLONGMAP_JSON = HERE / "raw" / "bangkok" / "klongmap_data.json"
MAIN_RIVER_JSONLD = HERE / "output" / "thailand_river_flow.jsonld"


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def compass_bearing(lat1, lon1, lat2, lon2) -> float:
    """Real-world compass bearing (deg clockwise from true north) from (lat1,lon1) to (lat2,lon2),
    with a cos(lat) correction for longitude compression."""
    mean_lat = math.radians((lat1 + lat2) / 2.0)
    east = (lon2 - lon1) * math.cos(mean_lat)
    north = lat2 - lat1
    return math.degrees(math.atan2(east, north)) % 360.0


def pixel_bearing(x1, y1, x2, y2) -> float:
    """Schematic-pixel bearing from (x1,y1) to (x2,y2), SAME CSS-rotate() convention already
    confirmed in build_bangkok_canals.py's _arrow_pixel_vector: 0deg = up-canvas (-y), clockwise
    positive (x right, y down screen coords)."""
    dx, dy = (x2 - x1), (y2 - y1)
    return math.degrees(math.atan2(dx, -dy)) % 360.0


def arrow_deg_to_pixel_bearing(deg: float) -> float:
    """arrowMap's own `deg` IS already in this convention (0=up, clockwise) -- see
    build_bangkok_canals.py's _arrow_pixel_vector docstring, confirmed by reading KlongMap's
    inline JS. Kept as an explicit pass-through function for clarity/symmetry with pixel_bearing()."""
    return deg % 360.0


def circular_mean_deg(degs: list) -> float:
    if not degs:
        return None
    s = sum(math.sin(math.radians(d)) for d in degs)
    c = sum(math.cos(math.radians(d)) for d in degs)
    if s == 0 and c == 0:
        return None
    return math.degrees(math.atan2(s, c)) % 360.0


def angular_diff_deg(a: float, b: float) -> float:
    """Smallest absolute difference between two bearings, in [0, 180]."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def load_stations_and_arrows():
    data = json.loads(KLONGMAP_JSON.read_text())
    stations = []
    for w in data.get("waterStation", []):
        info = w.get("water_station_info")
        ox, oy = w.get("offset_x"), w.get("offset_y")
        if info is None or ox is None or oy is None:
            continue
        lat, lon = info.get("latitude"), info.get("longitude")
        if lat is None or lon is None:
            continue
        stations.append({
            "water_id": w.get("water_id"), "x": float(ox), "y": float(oy),
            "lat": float(lat), "lon": float(lon), "canal": info.get("river_name"),
        })
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
    return stations, arrows


def load_major_river_edges():
    """Ground truth: build_kg.py's major-river graph, direction = HydroRIVERS NEXT_DOWN,
    finite_diagnostic tier (real, not heuristic). Returns list of
    {lat, lon, to_lat, to_lon, bearing_deg (true downstream direction)}."""
    if not MAIN_RIVER_JSONLD.exists():
        return []
    doc = json.loads(MAIN_RIVER_JSONLD.read_text())
    by_id = {n["hyriv_id"]: n for n in doc["@graph"]}
    edges = []
    for n in doc["@graph"]:
        for succ_id_str in n.get("flowsInto", []):
            succ_id = int(succ_id_str.split(":")[-1])
            succ = by_id.get(succ_id)
            if succ is None:
                continue
            edges.append({
                "lat": n["lat"], "lon": n["lon"],
                "to_lat": succ["lat"], "to_lon": succ["lon"],
                "bearing_deg": compass_bearing(n["lat"], n["lon"], succ["lat"], succ["lon"]),
            })
    return edges


def klongmap_local_bearing_estimate(station, stations, arrows, arrow_radius_px, k_neighbors):
    """Returns (real_world_bearing_estimate_deg, n_nearby_arrows, n_neighbors_used) or
    (None, n_nearby_arrows, 0) if no local schematic bearing trend or no neighbors available."""
    nearby_arrow_degs = []
    for a in arrows:
        d = math.hypot(a["x"] - station["x"], a["y"] - station["y"])
        if d <= arrow_radius_px:
            nearby_arrow_degs.append(arrow_deg_to_pixel_bearing(a["deg"]))
    if not nearby_arrow_degs:
        return None, 0, 0

    local_schem_bearing = circular_mean_deg(nearby_arrow_degs)

    others = [s for s in stations if s is not station]
    others.sort(key=lambda s: math.hypot(s["x"] - station["x"], s["y"] - station["y"]))
    neighbors = others[:k_neighbors]
    rotation_offsets = []
    for nb in neighbors:
        b_pix = pixel_bearing(station["x"], station["y"], nb["x"], nb["y"])
        b_real = compass_bearing(station["lat"], station["lon"], nb["lat"], nb["lon"])
        rotation_offsets.append((b_real - b_pix) % 360.0)
    rotation_offset = circular_mean_deg(rotation_offsets)
    if rotation_offset is None:
        return None, len(nearby_arrow_degs), 0

    estimate = (local_schem_bearing + rotation_offset) % 360.0
    return estimate, len(nearby_arrow_degs), len(neighbors)


def run(arrow_radius_px, k_neighbors, gt_radius_km, agree_threshold_deg):
    stations, arrows = load_stations_and_arrows()
    river_edges = load_major_river_edges()
    print(f"[setup] {len(stations)} stations, {len(arrows)} arrows, {len(river_edges)} major-river "
          f"(ground-truth, finite_diagnostic) directed edges")

    pairs = []  # (klongmap_bearing, true_bearing, station)
    n_with_local_signal = 0
    for s in stations:
        est, n_arrows, n_nb = klongmap_local_bearing_estimate(s, stations, arrows, arrow_radius_px, k_neighbors)
        if est is None:
            continue
        n_with_local_signal += 1
        # nearest ground-truth major-river edge (by midpoint distance to station)
        best_edge, best_d = None, float("inf")
        for e in river_edges:
            mid_lat = (e["lat"] + e["to_lat"]) / 2.0
            mid_lon = (e["lon"] + e["to_lon"]) / 2.0
            d = haversine_km(s["lat"], s["lon"], mid_lat, mid_lon)
            if d < best_d:
                best_d, best_edge = d, e
        if best_edge is None or best_d > gt_radius_km:
            continue
        pairs.append({
            "station": s.get("canal") or s.get("water_id"),
            "klongmap_bearing": round(est, 1),
            "true_bearing": round(best_edge["bearing_deg"], 1),
            "diff_deg": round(angular_diff_deg(est, best_edge["bearing_deg"]), 1),
            "gt_dist_km": round(best_d, 3),
            "n_arrows": n_arrows,
        })

    print(f"[signal] {n_with_local_signal}/{len(stations)} stations have >=1 nearby arrow "
          f"within {arrow_radius_px}px (a local KlongMap bearing trend)")
    print(f"[ground truth] {len(pairs)} of those stations also sit within {gt_radius_km}km of a "
          f"major-river (finite_diagnostic) directed edge -- this is the actual calibration sample")

    if not pairs:
        print("  NO ground-truth pairs available at this radius -- cannot calibrate.")
        return pairs, None

    n_agree = sum(1 for p in pairs if p["diff_deg"] <= agree_threshold_deg)
    n = len(pairs)
    rate = n_agree / n
    # chance baseline for "angular diff <= threshold" under a uniform random bearing:
    chance_rate = (2 * agree_threshold_deg) / 360.0
    print(f"\n[calibration] agreement rate (diff <= {agree_threshold_deg} deg) = "
          f"{n_agree}/{n} = {rate:.1%}  (chance baseline for this threshold: {chance_rate:.1%})")
    diffs = sorted(p["diff_deg"] for p in pairs)
    print(f"  median angular diff: {diffs[len(diffs)//2]:.1f} deg, mean: {sum(diffs)/len(diffs):.1f} deg")
    for p in sorted(pairs, key=lambda p: p["diff_deg"])[:10]:
        print(f"    {p}")
    return pairs, rate


if __name__ == "__main__":
    print("=" * 100)
    print("Sweep over arrow-cluster radius, neighbor count, ground-truth join radius, agreement threshold")
    print("=" * 100)
    for arrow_radius_px in (60, 100, 150, 200):
        for k_neighbors in (2, 4):
            for gt_radius_km in (1.0, 2.0, 3.0):
                print(f"\n--- arrow_radius_px={arrow_radius_px} k_neighbors={k_neighbors} gt_radius_km={gt_radius_km} ---")
                run(arrow_radius_px, k_neighbors, gt_radius_km, agree_threshold_deg=90.0)
