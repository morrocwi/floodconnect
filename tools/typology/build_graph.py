#!/usr/bin/env python3
"""
tools/typology/build_graph.py -- builds ONE connected graph over the flow-stall water
typology (docs/FLOW_STALL_TYPOLOGY.md, `tools/flowmap/flow_stall.py`'s node/edge
vocabulary) plus the typology-links extension's power/resource/civil layers
(docs/FLOW_STALL_TYPOLOGY.md's new section, typology/nodes/*.yaml + typology/edges/*.yaml).

Founder's task, verbatim: "ทำให้เชื่อมกันหละ" -- turn the typology-extension PROPOSAL into a
REAL connected graph in the repo, not just a document.

Reuse-first, no new equations:
  - water-layer nodes/edges come straight from `site/inputs/canals/east_chain.yaml`
    (the same declared chain `canal_graph.py`/`flow_stall.py` already use) plus the
    Sammakorn private-pump control structures it names (ST.SPS.01-04) -- this module
    reads that file, it never re-derives topology.
  - `tools/dag`/`tools/kg` already build a MUCH bigger nationwide graph
    (`tools/kg/build_kg.py`, `docs/knowledge/water_system_dag.mmd`'s AG_* agencies) --
    this module deliberately stays SMALL and scoped to the typology-links registry
    (`typology/nodes/*.yaml`, `typology/edges/*.yaml`), reusing the SAME AG_* id strings
    the nationwide graph already declares (see typology/nodes/agencies.yaml's own
    `source` field per row) rather than rebuilding or duplicating that graph.
  - burden (`BURDENED`/`RELIEVED`, PROP-FLOOD-05a/05b) stays exactly where it already
    lives -- an attribute on the water `flows_to` edge (`design_direction`/
    `control_structures` carried straight from east_chain.yaml) -- this module never
    invents a new attribute for it and `decides` edges never target an edge (see
    typology/edges/decides.yaml header, independent-review fix 2026-09-28).

Node id scheme (typology/nodes/*.yaml §4a of the proposal doc):
    water node   WL.<CODE> / ST.<CODE>      (canal_oldcode from east_chain.yaml, or the
                                              already-used station code, e.g. WL.SMK.01/
                                              WL.BMA.02 from site/build_data.py, or a
                                              synthetic WATER.<key> for the 4 east_chain
                                              nodes with no public code at all)
    agency       AG_<SHORT_CODE>             (reused verbatim from water_system_dag.mmd
                                              where it already exists)
    sensor       SENSOR.<water node code>
    resource     RES.<TYPE>.<OWNER>.<seq>
    warning_channel  WCH.<NAME_SLUG>
    soi/zone     SOI.<AREA>.<slug>

Usage:
    python3 -m tools.typology.build_graph --out output/typology_graph

Writes `output/typology_graph.json` (full node-link graph, all layers) and
`output/typology_sammakorn_subgraph.json` (the Sammakorn worked example only: soi ->
pond -> pumps -> canal chain -> พระโขนง -> เจ้าพระยา, plus every civil/power/resource node
reachable from that chain in <=2 hops).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx
import yaml

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

EAST_CHAIN_PATH = REPO_ROOT / "site" / "inputs" / "canals" / "east_chain.yaml"
TYPOLOGY_NODES_DIR = REPO_ROOT / "typology" / "nodes"
TYPOLOGY_EDGES_DIR = REPO_ROOT / "typology" / "edges"
SELF_HELP_DAG_PATH = REPO_ROOT / "site" / "inputs" / "community" / "self_help_dag.yaml"

# site/build_data.py's own SAMMAKORN_CHAIN_NODES codes (read directly, not re-derived --
# see site/build_data.py ~line 2185-2190) -- these are the authoritative station codes for
# the two east_chain.yaml nodes ("sammakorn_pond"/"banma") that themselves declare
# `canal_oldcode: null` (no public BMA gauge code known when east_chain.yaml was written).
# Both codings exist in this repo for the same real-world structures; this build reconciles
# them by USING the station-code family (WL.*) as the graph node id, matching every other
# water node, and keeping the east_chain.yaml key as an alias attribute -- never silently
# picking one without recording the other.
EAST_CHAIN_KEY_TO_STATION_CODE = {
    "sammakorn_pond": "WL.SMK.01",
    "banma": "WL.BMA.02",
}
EAST_CHAIN_KEY_ALIAS_TAG = {
    "sammakorn_pond": "RELAYED-reconciled (site/build_data.py SAMMAKORN_CHAIN_NODES vs "
                       "east_chain.yaml's own canal_oldcode:null for this key -- OPEN "
                       "discrepancy, see docs/UNITS_AND_DATUMS.md)",
    "banma": "RELAYED-reconciled (same discrepancy as sammakorn_pond)",
}

# These two east_chain.yaml edges get REPLACED, not built generically -- see
# `_build_sammakorn_head_chain()` below. Fixed 2026-09-28 after an independent-review
# finding (NEEDS_FIXES): the earlier build chained ST.SPS.01-04 pump-to-pump in a single
# series and never linked the Sammakorn branch to the แสนแสบ mainline at all. The real
# link is `site/build_data.py`'s own `SAMMAKORN_CHAIN_EDGES` (PROP-FLOOD-04
# instantiation, founder ask verbatim there: "สัมมากรต้องเชื่อมกับน้ำในคลองด้วย เพราะมันเป็น
# น้ำย้อนจากคลอง ไม่ใช่แค่ปั๊ม") -- soi -> pond(WL.SMK.01) -> banma2(WL.BMA.02) ->
# saensaeb(WL.SSB.08), read DIRECTLY from that module rather than guessed by coordinate
# proximity (WL.BMA.02/WL.SMK.01 carry no lat/lon in this build at all -- both `east_chain
# .yaml` keys with `canal_oldcode: null`).
SAMMAKORN_SPECIAL_EDGE_IDS = {"e_banma_sammakornpond", "e_sammakornpond_wangyai"}

# Environman (สื่อสิ่งแวดล้อม) FB post, 28 ก.ย. 2569, RELAYED, citing ubonmet.tmd.go.th,
# prd.go.th, thaipbs -- drainage-precedence structural rule (no equation): a tributary
# can only be pumped out after the UPPER แสนแสบ level drops; deeper-inland tributaries
# take longer. `drains_after` names the mainline node this tributary edge is gated behind
# (RELAYED, qualitative, never computed -- ties to the same recession-front idea as
# tools/flowmap/flow_stall.py's RULE-STALL-01/_is_persistently_stalled, cross-referenced
# in the source string, not re-derived here).
DRAINS_AFTER_OVERRIDES = {
    "e_ram53_ssb07": {  # รามคำแหง (ซอยรามคำแหง 53 lateral)
        "drains_after": "WL.SSB.09",
        "drains_after_tag": "RELAYED",
        "drains_after_source": "Environman FB post 28 ก.ย. 2569 (citing ubonmet.tmd.go.th/"
                                 ".../1_Month/09.pdf, prd.go.th/.../iid/545141) -- cross-ref "
                                 "tools/flowmap/flow_stall.py RULE-STALL-01 (recession-front "
                                 "persistence check, same idea, not re-computed here)",
    },
    "e_kjn01_ssb07": {  # คลองจั่น -- explicitly named as taking LONGER (deeper inland)
        "drains_after": "WL.SSB.09",
        "drains_after_tag": "RELAYED",
        "drains_after_note_th": "ใช้เวลานานกว่ารามคำแหง/คลองจิก เพราะอยู่ลึกเข้าไปในแผ่นดินกว่า "
                                  "(Environman FB post 28 ก.ย. 2569, RELAYED, ไม่มีตัวเลขเวลากำกับ)",
        "drains_after_source": "Environman FB post 28 ก.ย. 2569 -- same cross-ref as e_ram53_ssb07",
    },
}


def _add_pump_node(G: nx.MultiDiGraph, code: str, source: str) -> bool:
    if G.has_node(code):
        return False
    G.add_node(code, kind="pump", layer="water", label_th=f"สถานีสูบ {code}",
                standard_class="HY_HydroNexus (OGC HY_Features, RELAYED)", tag="MEASURED",
                infra_class="grey", infra_class_tag="INSTINCT", source=source)
    return True


def _build_sammakorn_head_chain(G: nx.MultiDiGraph, key_to_id: dict) -> int:
    """North exit (soi -> pond -> ST.SPS.01 -> banma2 -> saensaeb/WL.SSB.08, plus the
    declared banma2->pond backflow-risk reverse edge): sourced from `site/build_data.py`'s
    `SAMMAKORN_CHAIN_NODES`/`SAMMAKORN_CHAIN_EDGES` (the repo's own PROP-FLOOD-04
    instantiation for this exact question), never guessed. South exit (pond ->
    {ST.SPS.02,03,04} -> wangyai): sourced from `site/inputs/canals/east_chain.yaml`'s
    `e_sammakornpond_wangyai` `control_structures` field, kept as 3 INDEPENDENT
    pond->pump->wangyai legs (never chained pump-to-pump) because that file names all 3
    pump codes on ONE shared edge without splitting a per-station outlet -- the
    per-station outlet is therefore genuinely OPEN, not invented."""
    n_pump_nodes = 0
    pond_id, banma_id = key_to_id["sammakorn_pond"], key_to_id["banma"]

    _NORTH_SRC = ("site/build_data.py SAMMAKORN_CHAIN_NODES/SAMMAKORN_CHAIN_EDGES "
                  "(pond_to_banma2/banma2_to_pond/banma2_to_saensaeb) + site/inputs/"
                  "canals/east_chain.yaml e_banma_sammakornpond control_structures "
                  "(\"Private pump ST.SPS.01 sits on this reach\")")
    if _add_pump_node(G, "ST.SPS.01", _NORTH_SRC):
        n_pump_nodes += 1
    G.add_edge(pond_id, "ST.SPS.01", kind="flows_to", tag="RELAYED", source=_NORTH_SRC)
    G.add_edge("ST.SPS.01", banma_id, kind="flows_to", tag="RELAYED", source=_NORTH_SRC)
    # declared backflow-risk reverse edge (site/build_data.py's own `banma2_to_pond`,
    # kind="backflow-risk") -- corroborated, never proven, by two community reports the
    # same module cites (ซ.59/ซ.17, 26 ก.ย. 2569, RELAYED, not MEASURED).
    G.add_edge(banma_id, pond_id, kind="flows_to", tag="RELAYED", edge_subkind="backflow-risk",
                source="site/build_data.py SAMMAKORN_CHAIN_EDGES banma2_to_pond "
                        "(kind=backflow-risk) + SAMMAKORN_COMMUNITY_BACKFLOW_EVIDENCE "
                        "(ซ.59/ซ.17, 26 ก.ย. 2569, RELAYED, corroborating only)")
    # THE missing link the independent review flagged: banma2 -> saensaeb (WL.SSB.08),
    # read directly off site/build_data.py, not picked by lat/lon (neither WL.BMA.02 nor
    # WL.SMK.01 carries a coordinate in this build at all).
    if G.has_node("WL.SSB.08"):
        G.add_edge(banma_id, "WL.SSB.08", kind="flows_to", tag="RELAYED",
                    source="site/build_data.py SAMMAKORN_CHAIN_EDGES banma2_to_saensaeb "
                            "(kind=outflow)")

    _SOUTH_SRC = ("site/inputs/canals/east_chain.yaml e_sammakornpond_wangyai "
                  "control_structures field (3 pump codes declared on ONE edge -- "
                  "per-station outlet split is OPEN, the shared wangyai outlet is the "
                  "only one the source names)")
    wangyai_id = key_to_id.get("wangyai")
    for pump_code in ("ST.SPS.02", "ST.SPS.03", "ST.SPS.04"):
        if _add_pump_node(G, pump_code, _SOUTH_SRC):
            n_pump_nodes += 1
        G.add_edge(pond_id, pump_code, kind="flows_to", tag="OPEN", source=_SOUTH_SRC)
        if wangyai_id:
            G.add_edge(pump_code, wangyai_id, kind="flows_to", tag="OPEN", source=_SOUTH_SRC)
    return n_pump_nodes

RIVER_NODE_ID = "river:chao_phraya"

# Two Sammakorn soi zones this build declares (reused by typology/edges/*.yaml) -- see
# proposal §4a: id scheme SOI.<AREA>.<slug>, matching social_listening.py's own soi/area
# convention (this build does not re-run the extractor, it only declares the ids the
# founder's worked example names).
SOI_ZONE_NODES = ["SOI.SAMMAKORN.17", "SOI.SAMMAKORN.18"]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from tag_vocabulary import TAG_VOCABULARY, COMPOUND_TAG_MAP  # noqa: E402

VALID_TAGS = set(TAG_VOCABULARY) | set(COMPOUND_TAG_MAP)


def _norm_tag(tag):
    """Normalize `tag` to a value in TAG_VOCABULARY, returning `(tag, extra_attrs)`.
    `extra_attrs` is a dict of additional node/edge attributes to merge in (empty for
    a tag that was already bare TAG_VOCABULARY). A pre-lock compound tag string
    (VERIFIED-CONTRADICTED, RELAYED-unverified, MEASURED+OPEN -- see
    typology/edges/owned_by.yaml, decides.yaml, typology/nodes/sensors.yaml) is mapped
    down via COMPOUND_TAG_MAP rather than passed through -- an earlier check defect:
    these three strings used to reach api/v1 and MCP verbatim, outside TAG_VOCABULARY."""
    if tag is None:
        return "OPEN", {}
    raw = str(tag)
    base = raw.split(" ")[0].split("(")[0].strip()
    for candidate in (raw, base):
        if candidate in COMPOUND_TAG_MAP:
            return COMPOUND_TAG_MAP[candidate]
        if candidate in TAG_VOCABULARY:
            return candidate, {}
    return "OPEN", {}


def load_east_chain():
    doc = yaml.safe_load(EAST_CHAIN_PATH.read_text(encoding="utf-8"))
    return doc.get("nodes") or {}, doc.get("edges") or []


def water_node_id(key: str, decl: dict) -> str:
    if key in EAST_CHAIN_KEY_TO_STATION_CODE:
        return EAST_CHAIN_KEY_TO_STATION_CODE[key]
    code = decl.get("canal_oldcode")
    if code:
        return code
    return f"WATER.{key}"


def build_water_layer(G: nx.MultiDiGraph):
    nodes_decl, edges_decl = load_east_chain()
    key_to_id = {}
    for key, decl in nodes_decl.items():
        nid = water_node_id(key, decl)
        key_to_id[key] = nid
        kind = "gate" if decl.get("is_gate") else (
            "pond" if key in ("sammakorn_pond",) else "canal_reach")
        tag = "RELAYED" if decl.get("canal_oldcode") or key in EAST_CHAIN_KEY_TO_STATION_CODE \
            else "OPEN"
        # infra_class (grey/green_blue/soft, TDRI framing 2026-09-28) -- default by kind:
        # engineered control structures/reaches are `grey`, a pond/retention basin is the
        # article's own `green_blue` example category. Tag INSTINCT (this check's own
        # classification applying TDRI's vocabulary, not a per-node TDRI statement) --
        # distinct from the node's own `tag` (which stays whatever east_chain.yaml earns).
        infra_class = "green_blue" if kind == "pond" else "grey"
        attrs = {
            "kind": kind, "layer": "water", "label_th": decl.get("label_th"),
            "standard_class": "HY_WaterBody/HY_HydroNexus (OGC HY_Features, RELAYED)"
                               if kind != "pond" else "HY_WaterBody (OGC HY_Features, RELAYED)",
            "tag": tag,
            "infra_class": infra_class,
            "infra_class_tag": "INSTINCT",
            "source": "site/inputs/canals/east_chain.yaml (declared chain)",
        }
        if key in EAST_CHAIN_KEY_ALIAS_TAG:
            attrs["east_chain_key_alias"] = key
            attrs["alias_reconciliation_tag"] = EAST_CHAIN_KEY_ALIAS_TAG[key]
        G.add_node(nid, **attrs)

    n_pump_nodes = 0
    for e in edges_decl:
        if e["edge_id"] in SAMMAKORN_SPECIAL_EDGE_IDS:
            continue  # replaced by _build_sammakorn_head_chain() below, not built generically
        u_id, v_id = key_to_id[e["u"]], key_to_id[e["v"]]
        direction_tag = "RELAYED" if e.get("design_direction") not in (None, "unknown") else "OPEN"
        edge_attrs = {"kind": "flows_to", "tag": direction_tag,
                      "source": f"site/inputs/canals/east_chain.yaml ({e['edge_id']})"}
        if e["edge_id"] in DRAINS_AFTER_OVERRIDES:
            edge_attrs.update(DRAINS_AFTER_OVERRIDES[e["edge_id"]])
        G.add_edge(u_id, v_id, **edge_attrs)

    n_pump_nodes += _build_sammakorn_head_chain(G, key_to_id)

    # terminal sink: pkn01 (WL.PKN.01, "พระโขนง") -> river (proposal §5 worked example).
    G.add_node(RIVER_NODE_ID, kind="river", layer="water", label_th="แม่น้ำเจ้าพระยา",
                standard_class="HY_WaterBody (OGC HY_Features, RELAYED)", tag="RELAYED",
                source="FLOW_STALL_TYPOLOGY_EXTENSION_PROPOSAL_2026-09-28.md §5 worked example")
    if G.has_node("WL.PKN.01"):
        G.add_edge("WL.PKN.01", RIVER_NODE_ID, kind="flows_to", tag="MEASURED",
                    source="docs/FLOW_STALL_TYPOLOGY.md (ปตร.พระโขนงลดก่อนต้นน้ำ 4-6 ชม., MEASURED)")
    # south_outlet is the OTHER declared terminal (proposal's ประเวศ->ลาดกระบัง branch);
    # also wired to the same river sink so every zone in that branch can reach a sink too.
    south_id = key_to_id.get("south_outlet")
    if south_id and G.has_node(south_id):
        G.add_edge(south_id, RIVER_NODE_ID, kind="flows_to", tag="OPEN",
                    source="site/inputs/canals/east_chain.yaml (south_outlet declared as a "
                            "terminal label only, no gauge -- OPEN whether it reaches the "
                            "river directly or via a further undeclared reach)")

    return n_pump_nodes


def load_registry_nodes(G: nx.MultiDiGraph):
    counts = {}
    for path in sorted(TYPOLOGY_NODES_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if doc.get("doc_kind") == "typology_node_overlay":
            continue  # merged separately, after every node-creating file has run --
            # see apply_node_overlays()
        rows = doc.get("rows") or []
        n = 0
        for r in rows:
            nid = r["id"]
            attrs = dict(r)
            attrs.pop("id", None)
            attrs["tag"], _tag_extra = _norm_tag(attrs.get("tag"))
            attrs.update(_tag_extra)
            G.add_node(nid, **attrs)
            n += 1
        counts[path.name] = n
    # zone (soi_surface) nodes this build declares for the Sammakorn worked example --
    # reuses the existing `soi_surface` water-typology node kind (docs/FLOW_STALL_
    # TYPOLOGY.md §1), not a new kind, per proposal §0's "no new graph, add a layer" rule.
    for zid in SOI_ZONE_NODES:
        if not G.has_node(zid):
            G.add_node(zid, kind="soi_surface", layer="civil",
                        label_th=zid.replace("SOI.SAMMAKORN.", "ซอย "),
                        standard_class="HY_Features local_surface (RELAYED, extension)",
                        tag="RELAYED",
                        source="social_listening.py soi/area convention "
                                "(FLOW_STALL_TYPOLOGY_EXTENSION_PROPOSAL_2026-09-28.md §4a); "
                                "this build declares the zone id, it does not re-run the "
                                "live extractor")
            counts.setdefault("soi_zone_nodes (declared here)", 0)
            counts["soi_zone_nodes (declared here)"] += 1
        # physical drainage flows_to edge (soi surface -> pond), separate from the
        # `reports_to` community-report edge typology/edges/reports_to.yaml declares for
        # the SAME pair -- the base flow-stall typology already treats a soi_surface
        # node's `role=local_surface` as physically draining into a `storage`/pond node
        # (docs/FLOW_STALL_TYPOLOGY.md §1); this is that physical edge, direction
        # genuinely undeclared (OPEN), not a claim about who reports what.
        if G.has_node("WL.SMK.01") and not G.has_edge(zid, "WL.SMK.01"):
            G.add_edge(zid, "WL.SMK.01", kind="flows_to", tag="OPEN",
                        source="docs/FLOW_STALL_TYPOLOGY.md §1 (soi_surface role="
                                "local_surface drains toward the nearest storage/pond "
                                "node) -- direction/rate undeclared, distinct from the "
                                "reports_to community-report edge for the same pair")
    return counts


def apply_node_overlays(G: nx.MultiDiGraph):
    """Merges attrs from every `doc_kind: typology_node_overlay` file in
    typology/nodes/*.yaml onto nodes that already exist in G -- never creates a node.
    Run AFTER build_water_layer()/load_registry_nodes() so every id it references is
    already present; a row whose id is not in G is a real data error and is reported
    (never silently created as a new node, which would defeat the overlay's own point)."""
    counts, missing = {}, []
    for path in sorted(TYPOLOGY_NODES_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if doc.get("doc_kind") != "typology_node_overlay":
            continue
        n = 0
        for r in doc.get("rows") or []:
            nid = r["id"]
            if not G.has_node(nid):
                missing.append((path.name, nid))
                continue
            attrs = {k: v for k, v in r.items() if k != "id"}
            for k, v in attrs.items():
                G.nodes[nid][k] = v
            n += 1
        counts[path.name] = n
    if missing:
        print(f"  WARNING: overlay row(s) reference node id(s) not present in the graph "
              f"(not applied, not created): {missing}", file=sys.stderr)
    return counts, missing


def load_self_help_dag(G: nx.MultiDiGraph):
    """Loads site/inputs/community/self_help_dag.yaml (imported from public/main 5364c23,
    2026-09-28) as a `self_help` layer in the SAME graph -- founder ask: "one graph
    carries water + power + resource + civil + self-help layers". Every node/edge here
    keeps its OWN id verbatim (household/buddy_cell/zone/support/internal_safe/egress/
    external_safe, e.g. `sammakorn_zone`) -- no CIV.* renaming. `kind`/`layer` are
    community_dag.py's own KIND_LAYER numbers (0-5, `support` shares 3 with
    `internal_safe` -- see that module's own docstring), kept separate from this
    typology's `layer` bucket (`self_help`, a NEW bucket alongside water/power/civil/
    resource) to avoid clashing with the water-layer's own numeric-free `layer` strings.
    Edge kind `escalates_to` (added to the closed vocabulary) carries the DAG's own
    forward-only household->...->external_safe edges -- every row in the source file is
    currently field_verified=false/status=UNKNOWN, so every edge here is tag OPEN,
    exactly as the source declares (never upgraded)."""
    if not SELF_HELP_DAG_PATH.exists():
        return {"nodes": 0, "edges": 0}
    import community_dag as cd
    doc = cd.load_document(SELF_HELP_DAG_PATH)
    n_nodes = n_edges = 0
    for nid, n in (doc.get("nodes") or {}).items():
        attrs = dict(n)
        attrs["self_help_kind"] = attrs.pop("kind", None)  # community_dag.py's own kind
        attrs["self_help_layer"] = attrs.pop("layer", None)  # 0-5 KIND_LAYER number
        attrs["kind"] = "self_help_" + (n.get("kind") or "unknown")
        attrs["layer"] = "self_help"
        attrs["tag"], _tag_extra = _norm_tag("OPEN" if n.get("status") == "UNKNOWN" else n.get("status"))
        attrs.update(_tag_extra)
        attrs["source"] = ("site/inputs/community/self_help_dag.yaml (imported from "
                             "public/main 5364c23, 2026-09-28)")
        G.add_node(nid, **attrs)
        n_nodes += 1
    for e in (doc.get("edges") or []):
        u, v = e.get("from"), e.get("to")
        if u is None or v is None or not G.has_node(u) or not G.has_node(v):
            continue
        tag = "OPEN" if not e.get("field_verified") else "RELAYED"
        G.add_edge(u, v, kind="escalates_to", tag=tag,
                    self_help_status=e.get("status"), self_help_safety=e.get("safety"),
                    modes=e.get("modes"), fresh=e.get("fresh"),
                    field_verified=e.get("field_verified"),
                    source="site/inputs/community/self_help_dag.yaml (imported from "
                            "public/main 5364c23, 2026-09-28)")
        n_edges += 1
    return {"nodes": n_nodes, "edges": n_edges}


def load_registry_edges(G: nx.MultiDiGraph):
    counts = {}
    open_target_counts = {}
    for path in sorted(TYPOLOGY_EDGES_DIR.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        edge_kind = doc.get("edge_kind")
        rows = doc.get("rows") or []
        n = n_open = 0
        for r in rows:
            u, v = r["from"], r["to"]
            for endpoint in (u, v):
                if endpoint != "OPEN" and not G.has_node(endpoint):
                    # OPEN sentinel node -- created once, never per-row, so every
                    # unresolved link in the graph points at ONE shared "OPEN" node
                    # rather than silently vanishing or being skipped.
                    if endpoint == "OPEN":
                        continue
                    print(f"  WARNING: {path.name} row from={u!r} to={v!r} references "
                          f"undeclared node id {endpoint!r} -- adding as a bare OPEN "
                          f"placeholder node (data error candidate, check the registry row)",
                          file=sys.stderr)
                    G.add_node(endpoint, kind="unknown", layer="unknown", tag="OPEN",
                                label_th=endpoint,
                                source=f"auto-created placeholder, referenced by {path.name}")
            if not G.has_node("OPEN"):
                G.add_node("OPEN", kind="open_sentinel", layer="unknown", tag="OPEN",
                            label_th="(ยังไม่ยืนยัน / unresolved)",
                            source="tools/typology/build_graph.py -- shared sentinel node "
                                    "for every unresolved edge target/source in the registry")
            attrs = {k: v for k, v in r.items() if k not in ("from", "to")}
            attrs["kind"] = edge_kind
            attrs["tag"], _tag_extra = _norm_tag(attrs.get("tag"))
            attrs.update(_tag_extra)
            G.add_edge(u, v, **attrs)
            n += 1
            if u == "OPEN" or v == "OPEN":
                n_open += 1
        counts[path.name] = {"edges": n, "open": n_open}
    return counts


def build(out_prefix: Path):
    G = nx.MultiDiGraph()
    n_pump_nodes = build_water_layer(G)
    node_counts = load_registry_nodes(G)
    overlay_counts, overlay_missing = apply_node_overlays(G)
    self_help_counts = load_self_help_dag(G)
    edge_counts = load_registry_edges(G)

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    data = nx.node_link_data(G, edges="edges")
    out_path = out_prefix.with_suffix(".json")
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    sub_path = out_prefix.parent / "typology_sammakorn_subgraph.json"
    sub = build_sammakorn_subgraph(G)
    sub_data = nx.node_link_data(sub, edges="edges")
    sub_path.write_text(json.dumps(sub_data, ensure_ascii=False, indent=2), encoding="utf-8")

    layer_counts = {}
    for _, d in G.nodes(data=True):
        layer_counts[d.get("layer", "unknown")] = layer_counts.get(d.get("layer", "unknown"), 0) + 1
    kind_edge_counts = {}
    for _, _, d in G.edges(data=True):
        kind_edge_counts[d.get("kind", "unknown")] = kind_edge_counts.get(d.get("kind", "unknown"), 0) + 1

    print(f"typology graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges "
          f"({n_pump_nodes} pump nodes inserted from control_structures)")
    print(f"  nodes by layer: {layer_counts}")
    print(f"  edges by kind: {kind_edge_counts}")
    print(f"  registry node files: {node_counts}")
    print(f"  node overlays applied: {overlay_counts}"
          f"{' (MISSING: ' + str(overlay_missing) + ')' if overlay_missing else ''}")
    print(f"  self_help layer: {self_help_counts}")
    print(f"  registry edge files: {edge_counts}")
    print(f"  wrote {out_path} and {sub_path}")
    return G


def build_sammakorn_subgraph(G: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """SOI.SAMMAKORN.17/18 -> WL.SMK.01 -> ST.SPS.* -> WL.BMA.02 -> WL.SSB.* -> WL.PKN.01
    -> river, plus every node reachable within 2 hops of any node on that chain (so the
    power/resource/civil layers around it show up too, per the founder's "ทำให้เชื่อมกันหละ")."""
    UG = G.to_undirected(as_view=True)
    chain_seed = list(SOI_ZONE_NODES) + ["WL.SMK.01", "ST.SPS.01", "ST.SPS.02", "ST.SPS.03",
                                          "ST.SPS.04", "WL.BMA.02", "WL.SSB.10", "WL.PKN.01",
                                          RIVER_NODE_ID]
    chain_seed = [n for n in chain_seed if G.has_node(n)]
    keep = set(chain_seed)
    for n in chain_seed:
        for nbr in nx.single_source_shortest_path_length(UG, n, cutoff=2):
            keep.add(nbr)
    return G.subgraph(keep).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO_ROOT / "output" / "typology_graph"))
    args = ap.parse_args()
    build(Path(args.out))


if __name__ == "__main__":
    main()
