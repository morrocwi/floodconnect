#!/usr/bin/env python3
"""
Thailand river flow-propagation knowledge graph builder.

Source data: HydroRIVERS v1.0 (HydroSHEDS, hydrosheds.org), Asia continental extract.
Answers: "node X is flooded -> what is the next downstream node?"
  -> that is literally G.successors(X) on the directed graph this script builds,
     or the `flowsInto` edge in the JSON-LD export.

Usage:
    python3 build_river_kg.py --strahler-min 6
    GISTDA_API_KEY=xxx python3 build_river_kg.py --strahler-min 6   # also overlays live flood extent

Requires the raw HydroRIVERS Asia shapefile to already be downloaded and unzipped at
raw/HydroRIVERS_v10_as_shp/HydroRIVERS_v10_as.shp (see README.md "Re-running" section
for the download command if raw/ is missing).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx

HERE = Path(__file__).parent
RAW_SHP = HERE / "raw" / "HydroRIVERS_v10_as_shp" / "HydroRIVERS_v10_as.shp"
RAW_PARQUET = HERE / "raw" / "thailand_bbox_clip.parquet"
THAILAND_BBOX = (97.3, 5.5, 105.7, 20.5)  # lon_min, lat_min, lon_max, lat_max (approx, incl. some border overlap)

GISTDA_BASE = "https://api-gateway.gistda.or.th/api/2.0/resources"


def load_thailand_clip() -> gpd.GeoDataFrame:
    """Load HydroRIVERS reaches clipped to Thailand's bbox, caching the clip as parquet."""
    if RAW_PARQUET.exists():
        return gpd.read_parquet(RAW_PARQUET)
    if not RAW_SHP.exists():
        sys.exit(
            f"Missing raw data: {RAW_SHP}\n"
            "Download it first:\n"
            "  curl -o raw/HydroRIVERS_v10_as_shp.zip "
            "https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip\n"
            "  unzip raw/HydroRIVERS_v10_as_shp.zip -d raw/\n"
        )
    gdf = gpd.read_file(RAW_SHP, bbox=THAILAND_BBOX)
    RAW_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(RAW_PARQUET)
    return gdf


def filter_major_rivers(gdf: gpd.GeoDataFrame, strahler_min: int) -> gpd.GeoDataFrame:
    return gdf[gdf["ORD_STRA"] >= strahler_min].copy()


def build_directed_graph(full_gdf: gpd.GeoDataFrame, major_gdf: gpd.GeoDataFrame) -> nx.DiGraph:
    """
    Build a directed graph over the MAJOR reaches only, edge = flows-into-next-downstream-major-reach.

    A raw HydroRIVERS NEXT_DOWN pointer often points at a MINOR (filtered-out) reach
    (e.g. a small tributary confluence before the water reaches the next major stem
    segment). We walk NEXT_DOWN repeatedly through the FULL (unfiltered) network until
    we land on a reach that survived the Strahler-order filter, so the major-river graph
    stays connected end-to-end instead of fragmenting at every minor confluence.
    """
    full_by_id = full_gdf.set_index("HYRIV_ID")
    major_ids = set(major_gdf["HYRIV_ID"])

    def next_major_downstream(hyriv_id: int, max_hops: int = 500):
        """Returns (next_major_hyriv_id, accumulated_length_km_of_skipped_minor_reaches) or (None, None)."""
        current = hyriv_id
        acc_len = 0.0
        for _ in range(max_hops):
            if current not in full_by_id.index:
                return None, None
            nxt = int(full_by_id.loc[current, "NEXT_DOWN"])
            if nxt == 0:
                return None, None  # outlet to sea / endorheic sink
            acc_len += float(full_by_id.loc[current, "LENGTH_KM"])
            if nxt in major_ids:
                return nxt, acc_len
            current = nxt
        return None, None  # safety valve against any cyclic data

    G = nx.DiGraph()
    for row in major_gdf.itertuples():
        centroid = row.geometry.centroid
        G.add_node(
            int(row.HYRIV_ID),
            main_river_id=int(row.MAIN_RIV),
            strahler_order=int(row.ORD_STRA),
            discharge_avg_cms=float(row.DIS_AV_CMS),
            length_km=float(row.LENGTH_KM),
            dist_to_outlet_km=float(row.DIST_DN_KM),
            lat=round(centroid.y, 5),
            lon=round(centroid.x, 5),
            name="unnamed",  # HydroRIVERS carries no river-name field
            flood_status="unknown",  # overlaid later if GISTDA_API_KEY is set
        )

    for row in major_gdf.itertuples():
        nxt, acc_len = next_major_downstream(int(row.HYRIV_ID))
        if nxt is not None:
            # length_km: accumulated physical distance to the next kept node, walking
            # through any skipped minor reaches -- used as the geodesic-distance weight
            # for closeness/betweenness centrality (shortest path = shortest river distance,
            # not hop count).
            length_km = acc_len if acc_len > 0 else 0.001
            velocity_mps = estimate_velocity_mps(float(row.DIS_AV_CMS))
            travel_time_hr = (length_km * 1000.0 / velocity_mps) / 3600.0
            G.add_edge(
                int(row.HYRIV_ID),
                nxt,
                relation="flowsInto",
                discharge_avg_cms=float(row.DIS_AV_CMS),  # flow-volume weight (not used for centrality distance)
                length_km=round(length_km, 3),
                velocity_est_mps=round(velocity_mps, 3),
                travel_time_hr=round(travel_time_hr, 3),
            )
    return G


def estimate_velocity_mps(discharge_avg_cms: float) -> float:
    """
    Rough river flow-velocity estimate from long-term average discharge, used only to turn
    `length_km` into a travel-time-order-of-magnitude estimate for flood-wavefront
    propagation. `Dr` tier (INSTINCT) -- NOT a calibrated hydraulic model.

    Loosely follows the qualitative shape of Leopold-Maddock (1953) at-a-station/
    downstream hydraulic geometry (velocity rises slowly, roughly as a small positive
    power of discharge, rather than linearly) -- but the constants here are an
    order-of-magnitude engineering guess, not fit to any Thai gauge data. Clamped to a
    plausible physical range for lowland-to-highland rivers (0.3-3.5 m/s). Do not treat
    the resulting travel times as validated forecasts -- see README "Flood wavefront
    propagation" section.
    """
    import math
    v = 0.4 + 0.35 * math.log10(max(discharge_avg_cms, 0.1) + 1.0)
    return min(max(v, 0.3), 3.5)


def propagate_flood_wavefront(G: nx.DiGraph) -> dict:
    """
    Multi-source shortest-path propagation of ETA (hours) from every currently-flooded
    node, following directed `flowsInto` edges only, weighted by each edge's
    `travel_time_hr`. Sets `eta_from_flood_hr` and `flood_source_node` on every node
    reachable downstream from a flooded node; leaves both `None` elsewhere (including on
    the flooded source nodes themselves' upstream-only ancestors, and on any node with no
    flooded node upstream of it).

    This is a STRUCTURAL/DISTANCE-BASED ETA ORDERING, not a hydrodynamic flood-routing
    forecast: it has no rainfall input, no reservoir/gate operation, no real-time
    discharge or water level, and `travel_time_hr` itself rests on the Dr-tier velocity
    estimate above. Treat the output as "which downstream nodes are structurally closer
    in time, in rank order" -- not as calibrated hours-until-flooding.

    Returns the dict of {node: (eta_hr, source_flooded_node)} for reachable nodes, for the
    caller to also print a summary table.
    """
    flooded = [n for n, d in G.nodes(data=True) if d.get("flood_status") == "flooded"]
    for n, d in G.nodes(data=True):
        d["eta_from_flood_hr"] = None
        d["flood_source_node"] = None
    if not flooded:
        return {}

    # nx.multi_source_dijkstra requires >=1 source; run it once per source and keep the
    # minimum ETA across all sources for nodes reachable from more than one flooded node.
    best: dict = {}
    for src in flooded:
        try:
            lengths = nx.single_source_dijkstra_path_length(G, src, weight="travel_time_hr")
        except nx.NetworkXError:
            continue
        for node, eta in lengths.items():
            if node == src:
                continue  # the flooded node itself, not a downstream propagation target
            if node not in best or eta < best[node][0]:
                best[node] = (eta, src)

    for node, (eta, src) in best.items():
        G.nodes[node]["eta_from_flood_hr"] = round(eta, 3)
        G.nodes[node]["flood_source_node"] = src
    return best


def add_centrality(G: nx.DiGraph) -> None:
    """
    Centrality metrics, mirroring Phukseng (2020) J Sci Technol MSU 39(4):388-399's
    river-network centrality methodology (Degree, Closeness, Betweenness, Eccentricity,
    Eigenvector on an undirected projection of the river graph).

    Closeness and Betweenness use `weight="length_km"` (river distance along the network,
    summed across edges on the shortest path) -- NOT unweighted hop count -- so "shortest
    path" means shortest river distance, matching what the Thai paper's Geodesic Path
    Distance concept intends. length_km is the accumulated physical reach length
    (see build_directed_graph), a real distance, not a proxy.
    """
    und = G.to_undirected()
    deg = dict(G.degree())
    nx.set_node_attributes(G, deg, "degree")
    nx.set_node_attributes(G, nx.closeness_centrality(und, distance="length_km"), "closeness_centrality")
    nx.set_node_attributes(G, nx.betweenness_centrality(und, weight="length_km"), "betweenness_centrality")
    try:
        nx.set_node_attributes(G, nx.eigenvector_centrality(und, max_iter=1000), "eigenvector_centrality")
    except nx.PowerIterationFailedConvergence:
        nx.set_node_attributes(G, {n: None for n in G.nodes}, "eigenvector_centrality")
    ecc = {}
    for comp in nx.connected_components(und):
        sub = und.subgraph(comp)
        if len(sub) > 1:
            ecc.update(nx.eccentricity(sub, weight="length_km"))
        else:
            ecc[list(sub.nodes)[0]] = 0
    nx.set_node_attributes(G, ecc, "eccentricity")


def assign_basin_proxy(G: nx.DiGraph) -> None:
    """
    Proxy basin grouping: cluster by HydroRIVERS MAIN_RIV id (the id of the main-stem
    river each reach belongs to). This is NOT the official 25 river basins (ลุ่มน้ำหลัก)
    of Thailand's Office of National Water Resources -- HydroRIVERS carries no such
    boundary layer, and no authoritative Thai basin-boundary shapefile was fetched for
    this run. `basin_proxy_id` is an engineering approximation (INSTINCT, not VERIFIED):
    each MAIN_RIV id groups reaches that drain to the same river mouth, which usually
    but not always aligns with one official basin.
    """
    for n, d in G.nodes(data=True):
        d["basin_proxy_id"] = d["main_river_id"]


def overlay_gistda_flood(G: nx.DiGraph, api_key: str) -> str:
    """
    Spatially join current flood extent (30-day window) from GISTDA Disaster API onto
    graph nodes. Requires GISTDA_API_KEY env var. Best-effort: network/API failures are
    reported, not silently swallowed, but do not abort the whole pipeline.

    The endpoint is OGC-features-style and paginated: an unparameterized call returns
    only `numberReturned` of `numberMatched` total features (observed: numberMatched
    ~14,376 flood polygons nationwide, default page ~10 -- confirmed by the `links`
    array's `rel: "next"` entry). This function pages with `limit=1000&offset=N` (1000
    was observed to be accepted as-is, not silently clamped) until all `numberMatched`
    features are collected or a page returns 0 features.

    Returns an ISO-8601 UTC timestamp string marking when this snapshot was taken, for
    the caller to record as provenance (this is a point-in-time readout, not a live feed).
    """
    import urllib.request
    import urllib.error
    import datetime
    from shapely.geometry import shape, Point

    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    all_features = []
    limit = 1000
    offset = 0
    number_matched = None
    while True:
        url = f"{GISTDA_BASE}/features/flood/30days?api_key={api_key}&limit={limit}&offset={offset}"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[flood overlay] GISTDA API call failed at offset={offset}: {e} -- "
                  f"using {len(all_features)} features collected so far", file=sys.stderr)
            break

        page_features = data.get("features", [])
        number_matched = data.get("numberMatched", number_matched)
        number_returned = data.get("numberReturned", len(page_features))
        print(f"[flood overlay] page offset={offset}: numberReturned={number_returned}, "
              f"numberMatched={number_matched}", file=sys.stderr)
        all_features.extend(page_features)

        has_next = any(link.get("rel") == "next" for link in data.get("links", []))
        if not has_next or number_returned == 0:
            break
        offset += limit
        if number_matched is not None and offset >= number_matched:
            break

    print(f"[flood overlay] collected {len(all_features)} flood polygons "
          f"(GISTDA numberMatched={number_matched}) as of {fetched_at}", file=sys.stderr)

    flood_polys = [shape(f["geometry"]) for f in all_features if f.get("geometry")]
    if not flood_polys:
        print("[flood overlay] GISTDA returned 0 flood features for /flood/30days", file=sys.stderr)
        for _, d in G.nodes(data=True):
            d["flood_status"] = "not_flooded"
        return fetched_at

    # 0.01 deg buffer (~1.1km at Thailand's latitude) as a near-polygon fallback for
    # reaches that pass close to but don't literally intersect a flood polygon centroid
    # sample point. Dr tier -- a judgment call, not validated against ground truth; a
    # tighter or coordinate-length-of-day-corrected buffer could change results.
    NEAR_BUFFER_DEG = 0.01
    for _, d in G.nodes(data=True):
        pt = Point(d["lon"], d["lat"])
        d["flood_status"] = "flooded" if any(
            poly.contains(pt) or poly.distance(pt) < NEAR_BUFFER_DEG for poly in flood_polys
        ) else "not_flooded"
    return fetched_at


def overlay_google_flood_forecast(G: nx.DiGraph, api_key: str) -> None:
    """
    STUB -- not implemented, blocked on access, not on code.

    Google's Flood Forecasting API (developers.google.com/flood-forecasting, part of
    Google Flood Hub) gives up-to-7-day-ahead riverine flood forecasts -- the piece this
    pipeline is missing (GISTDA's /flood/30days is a satellite-detected SNAPSHOT of
    current/recent extent, not a forecast; this graph's flowsInto edges give topological
    "what's downstream", not "when will it flood"). Confirmed by web research 2026-09-23
    (INSTINCT/relayed, not independently verified by this pipeline):
      - Free, public-good API, but ACCESS IS GATED: requires joining a waitlist, Google
        Cloud Project ID, and manual approval by email -- there is no self-serve API key
        like GISTDA's. Do not attempt to call this without an approved key; it will fail.
      - Coverage: 150+ countries / 1,800+ gauge sites globally as of the 2026 research
        pass; Thailand-specific gauge density was NOT confirmed (would need to inspect
        floodhub.google.com's map directly, which is a JS app, not fetchable headlessly
        here) -- do not assume dense Thailand coverage until checked.
      - Gauge ID scheme is UNDOCUMENTED in the pages checked -- almost certainly NOT the
        same HYRIV_ID this graph uses. Once real access exists, the join step will likely
        need to be a nearest-neighbor spatial match (gauge lat/lon -> nearest graph node)
        rather than a direct ID join -- implement and validate that match once you can see
        real gauge coordinates, don't assume it here.

    To activate: get API access (see developers.google.com/flood-forecasting), then
    implement the actual REST call + the spatial gauge-to-node join described above, and
    set a `forecast_flood_probability` / `forecast_horizon_days` style node attribute
    (finite_diagnostic tier, sourced from Google's model -- not this pipeline's own
    computation) parallel to how flood_status is set by overlay_gistda_flood().
    """
    raise NotImplementedError(
        "Google Flood Forecasting API access is pending (waitlist-gated). "
        "See this function's docstring for what's needed to implement it once access exists."
    )


def export_graphml(G: nx.DiGraph, path: Path) -> None:
    H = G.copy()
    for _, d in H.nodes(data=True):
        for k, v in list(d.items()):
            if v is None:
                d[k] = "null"
    nx.write_graphml(H, path)


def export_jsonld(G: nx.DiGraph, path: Path) -> None:
    context = {
        "@vocab": "https://schema.org/",
        "flowsInto": {"@id": "https://schema.org/isPartOf", "@type": "@id"},
        "hyd": "https://hydrosheds.org/vocab#",
    }
    nodes = []
    for n, d in G.nodes(data=True):
        entry = {
            "@id": f"riverreach:{n}",
            "@type": "hyd:RiverReach",
            "hyriv_id": n,
            **{k: v for k, v in d.items()},
            "flowsInto": [f"riverreach:{succ}" for succ in G.successors(n)],
        }
        nodes.append(entry)
    doc = {"@context": context, "@graph": nodes}
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strahler-min", type=int, default=6,
                     help="Minimum Strahler stream order to keep as a 'major river' reach (default 6)")
    ap.add_argument("--out-dir", type=Path, default=HERE / "output")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading Thailand-clipped HydroRIVERS reaches...")
    full_gdf = load_thailand_clip()
    print(f"  {len(full_gdf)} total reaches in bbox")

    major_gdf = filter_major_rivers(full_gdf, args.strahler_min)
    print(f"  {len(major_gdf)} reaches kept at Strahler order >= {args.strahler_min}")

    print("Building directed flow graph (skipping minor confluences)...")
    G = build_directed_graph(full_gdf, major_gdf)
    print(f"  graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print("Computing centrality metrics...")
    add_centrality(G)

    print("Assigning basin-proxy grouping (MAIN_RIV id, see docstring/README for caveat)...")
    assign_basin_proxy(G)
    n_basins = len({d["basin_proxy_id"] for _, d in G.nodes(data=True)})
    print(f"  {n_basins} distinct basin-proxy groups")

    api_key = os.environ.get("GISTDA_API_KEY")
    flood_snapshot_at = None
    if api_key:
        print("GISTDA_API_KEY set -- overlaying live 30-day flood extent...")
        flood_snapshot_at = overlay_gistda_flood(G, api_key)
    else:
        print("GISTDA_API_KEY not set -- skipping live flood overlay, flood_status left as 'unknown' on all nodes.")

    from collections import Counter
    status_counts = Counter(d["flood_status"] for _, d in G.nodes(data=True))
    print(f"\nflood_status distribution: {dict(status_counts)}"
          + (f" (snapshot at {flood_snapshot_at})" if flood_snapshot_at else ""))

    print("\nPropagating flood wavefront ETA (Dr-tier structural estimate, see README)...")
    eta_map = propagate_flood_wavefront(G)
    if eta_map:
        print(f"  {len(eta_map)} downstream node(s) reachable from a currently-flooded node")
        ranked = sorted(eta_map.items(), key=lambda kv: kv[1][0])[:15]
        print("  Nearest-in-time downstream nodes (node_id: eta_hr <- flooded source):")
        for node, (eta, src) in ranked:
            print(f"    {node}: {eta:.2f} hr <- {src}")
    else:
        print("  no flooded nodes to propagate from (flood_status inactive or none flooded)")

    graphml_path = args.out_dir / "thailand_river_flow.graphml"
    jsonld_path = args.out_dir / "thailand_river_flow.jsonld"
    export_graphml(G, graphml_path)
    export_jsonld(G, jsonld_path)
    print(f"Wrote {graphml_path}")
    print(f"Wrote {jsonld_path}")

    print("\nExample query -- next downstream node(s) for the first node in the graph:")
    example_node = next(iter(G.nodes))
    print(f"  G.successors({example_node}) -> {list(G.successors(example_node))}")

    flooded = [n for n, d in G.nodes(data=True) if d["flood_status"] == "flooded"]
    if flooded:
        print(f"\n{len(flooded)} flooded node(s) found. Downstream-chain demo for up to 3:")
        for n in flooded[:3]:
            chain = [n]
            cur = n
            for _ in range(5):
                succs = list(G.successors(cur))
                if not succs:
                    break
                cur = succs[0]
                chain.append(cur)
            print(f"  {n} -> " + " -> ".join(str(x) for x in chain[1:]) if len(chain) > 1
                  else f"  {n} -> (outlet / no further major downstream reach)")


if __name__ == "__main__":
    main()
