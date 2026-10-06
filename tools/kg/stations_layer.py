#!/usr/bin/env python3
"""
tools/kg/stations_layer.py -- nationwide keyless station nodes, layer "stations_v1".

Adds, on top of whatever tools/kg/build_kg.py already built, ONE node per row of the
committed station tables (sources/stations/bma_watermap.json,
sources/stations/thaiwater_waterlevel.json -- see tools/harvest/station_tables.py),
plus the connectivity this M8 design calls for: SAME_STATION (agency-code match to an
existing thaiwater_bma gauge/gate node), ON_REACH (nearest-river_reach snap, same
heuristic build_kg.build_on_reach_edges already uses for every other asset class),
and the two declared LOCATED_ON/OUTLET_TO joins in
sources/canalchain_station_joins.yaml.

Every node/edge this module adds carries `layer="stations_v1"`, so `--augment` can
re-run idempotently: drop everything tagged with that layer, re-add from the same
committed inputs, re-export. Running `--augment` twice on the same graphml+inputs
produces BYTE-IDENTICAL output (same `export_graphml`/`export_jsonld` as
build_kg.py, same deterministic input ordering here).

IN_SUBBASIN for these new nodes is NOT attempted here when
raw/gis/dwr_subbasin/ (gitignored, see tools/harvest/dwr_subbasin.py) is absent from
the checkout -- same documented gap tools/kg/build_index.py's GLOBAL_GAPS already
carries for the rest of this KG, never silently guessed. `report()` says plainly
whether it ran with or without that archive.

Two entry points:
  apply(G, repo_root)             -- mutates G in place, called from build_kg.build_graph
                                      at the end of a FULL from-scratch rebuild.
  main() / --augment <path.graphml> -- offline path: read an ALREADY-BUILT graphml,
                                      drop the stations_v1 layer, re-add it, write back.
                                      This is the only reproducible path in a checkout
                                      that lacks the gitignored sqlite/geojson inputs
                                      build_kg.py's full rebuild needs in this
                                      checkout.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import networkx as nx
import yaml

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(HERE))

from tools.kg.build_kg import (  # noqa: E402 -- reuse, never re-derive
    build_on_reach_edges, export_graphml, export_jsonld, normalize_canal_name,
)

LAYER = "stations_v1"
STATIONS_DIR = HERE / "sources" / "stations"
JOINS_PATH = HERE / "sources" / "canalchain_station_joins.yaml"
KG_GRAPHML = HERE / "output" / "thailand_water_kg.graphml"
KG_JSONLD = HERE / "output" / "thailand_water_kg.jsonld"

STATION_TABLE_SOURCES = ("bma_watermap", "thaiwater_waterlevel")


def _load_table(source_id: str) -> dict:
    path = STATIONS_DIR / f"{source_id}.json"
    if not path.exists():
        return {"source_id": source_id, "rows": [], "as_of": None}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_joins() -> list:
    if not JOINS_PATH.exists():
        return []
    doc = yaml.safe_load(JOINS_PATH.read_text(encoding="utf-8")) or {}
    return doc.get("joins", [])


def _existing_thaiwater_bma_codes(G: nx.MultiDiGraph) -> dict:
    """code -> node id, for every already-present gauge:thaiwater_bma:* / gate:thaiwater_bma:*
    node -- the SAME_STATION match target."""
    out = {}
    for n in G.nodes:
        if n.startswith("gauge:thaiwater_bma:") or n.startswith("gate:thaiwater_bma:"):
            code = n.split(":", 2)[2]
            out[code] = n
    return out


def _existing_thaiwater_waterlevel_ids(G: nx.MultiDiGraph) -> set:
    return {n.split(":", 2)[2] for n in G.nodes if n.startswith("gauge:thaiwater_waterlevel:")}


def _drop_layer(G: nx.MultiDiGraph) -> None:
    drop_nodes = [n for n, d in G.nodes(data=True) if d.get("layer") == LAYER]
    G.remove_nodes_from(drop_nodes)
    drop_edges = [(u, v, k) for u, v, k, d in G.edges(keys=True, data=True) if d.get("layer") == LAYER]
    G.remove_edges_from([(u, v, k) for u, v, k in drop_edges])


def _river_reach_nodes(G: nx.MultiDiGraph) -> list:
    return [(n, d) for n, d in G.nodes(data=True) if d.get("kind") == "river_reach"]


def apply(G: nx.MultiDiGraph, repo_root: Path = HERE) -> dict:
    """Mutates G in place. Returns a report dict (see `report()` for the printed form)."""
    _drop_layer(G)  # idempotent: safe to call on a graph that already has this layer

    report = {"added_nodes": Counter(), "same_station": 0, "on_reach": 0,
              "located_on": 0, "outlet_to": 0, "sb_archive_present": None}

    existing_bma_codes = _existing_thaiwater_bma_codes(G)
    existing_waterlevel_ids = _existing_thaiwater_waterlevel_ids(G)

    new_station_nodes = []  # (asset_id, lat, lon, class) for the ON_REACH snap pass

    # -- bma_watermap: one new node PER ROW, always (SAME_STATION keeps both nodes,
    # per the founder's sandwich/connectivity design -- never merged into one id).
    bma_table = _load_table("bma_watermap")
    for row in sorted(bma_table.get("rows", []), key=lambda r: r["id"]):
        code = row["id"]
        nid = f"gauge:bma_watermap:{code}"
        G.add_node(nid, kind="asset", **{
            "class": "gauge", "name_th": row.get("name_th"), "lat": row.get("lat"),
            "lon": row.get("lon"), "owner": "สำนักการระบายน้ำ กรุงเทพมหานคร",
            "source": f"sources/stations/bma_watermap.json (live POST weather.bangkok.go.th, as_of {bma_table.get('as_of')})",
            "tag": "VERIFIED", "sb_dwr": row.get("sb_dwr"), "basin_code": row.get("basin_code"),
            "live_key": code, "layer": LAYER,
        })
        report["added_nodes"]["gauge:bma_watermap"] += 1
        if row.get("lat") is not None and row.get("lon") is not None:
            new_station_nodes.append((nid, row["lat"], row["lon"], "gauge"))
        same = existing_bma_codes.get(code)
        if same is not None:
            G.add_edge(nid, same, kind="SAME_STATION", tag="RELAYED",
                        method="agency_code_exact", source="tools/kg/stations_layer.py",
                        layer=LAYER)
            G.add_edge(same, nid, kind="SAME_STATION", tag="RELAYED",
                        method="agency_code_exact", source="tools/kg/stations_layer.py",
                        layer=LAYER)
            report["same_station"] += 1

    # -- thaiwater_waterlevel: only the stations with NO existing node (per MEASURED
    # facts, a handful of live stations join rate < 100%).
    tw_table = _load_table("thaiwater_waterlevel")
    for row in sorted(tw_table.get("rows", []), key=lambda r: str(r["id"])):
        live_key = str(row["id"])
        if live_key in existing_waterlevel_ids:
            continue
        nid = f"gauge:thaiwater_waterlevel:{live_key}"
        G.add_node(nid, kind="asset", **{
            "class": "gauge", "name_th": row.get("name_th"), "lat": row.get("lat"),
            "lon": row.get("lon"), "owner": row.get("agency_short"),
            "source": f"sources/stations/thaiwater_waterlevel.json (live GET api-v3.thaiwater.net, as_of {tw_table.get('as_of')})",
            "tag": "VERIFIED", "sb_dwr": row.get("sb_dwr"), "basin_code": row.get("basin_code"),
            "live_key": live_key, "layer": LAYER,
        })
        report["added_nodes"]["gauge:thaiwater_waterlevel"] += 1
        if row.get("lat") is not None and row.get("lon") is not None:
            new_station_nodes.append((nid, row["lat"], row["lon"], "gauge"))

    # -- declared LOCATED_ON / OUTLET_TO joins (sources/canalchain_station_joins.yaml)
    for j in _load_joins():
        edge_kind = j["edge"]
        if edge_kind == "LOCATED_ON":
            station_table, station_id, canal_node = j["station_table"], j["station_id"], j["canal_node"]
            station_nid = f"gauge:{station_table}:{station_id}"
            if station_nid not in G or canal_node not in G:
                continue
            G.add_edge(station_nid, canal_node, kind="LOCATED_ON", tag=j["tag"],
                        method=j["method"], evidence=j["evidence"], source=j["source"],
                        layer=LAYER)
            report["located_on"] += 1
            # give the (previously coordinate-less) canal node this station's own
            # coordinate, tag RELAYED -- per design "(d) ... these two joined nodes get
            # coordinates from their station". Never overwrites an already-good coord.
            cd = G.nodes[canal_node]
            if cd.get("lat") in (None, "null") and cd.get("lon") in (None, "null"):
                sd = G.nodes[station_nid]
                cd["lat"], cd["lon"] = sd.get("lat"), sd.get("lon")
                cd["tag"] = "RELAYED"
                cd["coord_source"] = f"RELAYED from {station_nid} (tools/kg/stations_layer.py)"
        elif edge_kind == "OUTLET_TO":
            u, v = j["canal_node"], j["target_canal_node"]
            if u not in G or v not in G:
                continue
            G.add_edge(u, v, kind="OUTLET_TO", tag=j["tag"], method=j["method"],
                        distance_km=j.get("distance_km"), evidence=j["evidence"],
                        contradicts=j.get("contradicts"), source=j["source"],
                        layer=LAYER)
            report["outlet_to"] += 1

    # -- ON_REACH: same nearest-river_reach-centroid heuristic as build_kg.py, applied
    # only to the NEW nodes this layer adds (existing assets already got their own
    # ON_REACH pass in build_kg.build_graph).
    river_nodes = _river_reach_nodes(G)
    if new_station_nodes and river_nodes:
        pseudo_assets = [{"asset_id": nid, "class": klass, "lat": lat, "lon": lon}
                          for nid, lat, lon, klass in new_station_nodes]
        for u, v, edata in build_on_reach_edges(pseudo_assets, river_nodes):
            edata["layer"] = LAYER
            G.add_edge(u, v, **edata)
            report["on_reach"] += 1

    report["sb_archive_present"] = any(r.get("sb_dwr") is not None
                                        for r in bma_table.get("rows", []) + tw_table.get("rows", []))
    return report


def print_report(report: dict, label: str) -> None:
    print(f"\n[{label}]")
    for klass, n in sorted(report["added_nodes"].items()):
        print(f"  added node class {klass}: {n}")
    print(f"  SAME_STATION edges: {report['same_station']}")
    print(f"  ON_REACH edges (new nodes only): {report['on_reach']}")
    print(f"  LOCATED_ON edges: {report['located_on']}")
    print(f"  OUTLET_TO edges: {report['outlet_to']}")
    print(f"  DWR sub-basin archive present (any sb_dwr resolved): {report['sb_archive_present']}")
    if not report["sb_archive_present"]:
        print("  -> IN_SUBBASIN for these new nodes: NOT attempted (raw/gis/dwr_subbasin/ "
              "absent from this checkout) -- same documented gap as the rest of this KG.")


def coverage_snapshot(G: nx.MultiDiGraph) -> dict:
    classes = ("gauge:thaiwater_waterlevel", "gauge:thaiwater_bma", "gate:thaiwater_bma",
               "gauge:bma_watermap", "canalchain")
    out = {}
    for prefix in classes:
        ids = [n for n in G.nodes if n.startswith(prefix + ":")]
        n_in_sub = sum(1 for i in ids if any(
            G.nodes[i].get(k) for k in ("sb_dwr",)) or
            any(d.get("kind") == "IN_SUBBASIN" for _, _, d in G.out_edges(i, data=True)))
        n_on_reach = sum(1 for i in ids if any(
            d.get("kind") == "ON_REACH" for _, _, d in G.out_edges(i, data=True)))
        out[prefix] = {"nodes": len(ids), "on_reach": n_on_reach}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--augment", metavar="GRAPHML",
                     help="read this graphml (force_multigraph), apply the stations_v1 "
                          "layer, write it + the sibling .jsonld back out")
    ap.add_argument("--report", action="store_true", help="print before/after coverage")
    args = ap.parse_args(argv)

    if not args.augment:
        ap.error("--augment PATH is required (this CLI only augments an existing graphml)")

    graphml_path = Path(args.augment)
    G = nx.read_graphml(graphml_path, force_multigraph=True)
    assert isinstance(G, nx.MultiDiGraph), "expected a MultiDiGraph (force_multigraph=True)"

    before = coverage_snapshot(G) if args.report else None
    report = apply(G, HERE)
    after = coverage_snapshot(G) if args.report else None

    export_graphml(G, graphml_path)
    jsonld_path = graphml_path.with_suffix(".jsonld")
    export_jsonld(G, jsonld_path)
    print(f"Wrote {graphml_path}")
    print(f"Wrote {jsonld_path}")

    print_report(report, "stations_v1 apply")
    if args.report:
        print("\n[coverage before -> after]")
        for prefix in sorted(before):
            b, a = before[prefix], after[prefix]
            print(f"  {prefix}: nodes {b['nodes']} -> {a['nodes']}, "
                  f"on_reach {b['on_reach']} -> {a['on_reach']}")
    print(f"\nTotal: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
