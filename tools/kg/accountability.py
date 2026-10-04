#!/usr/bin/env python3
"""
tools/kg/accountability.py -- "who is responsible here" readout over the nationwide KG.

Founder ask, verbatim: "ระบบต้องรู้เลยว่า น้ำท่วมที่นี่ใครรับผิดชอบ และอำนาจในการควบคุมทรัพยากร
ที่ซ้อนทับกันหรือต้องการความร่วมมือระหว่าง node คืออะไร และมีกฎหมายหรืออำนาจข้อไหนที่อาจมีปัญหา
แล้วประชาชนจะดูแลตัวเองอย่างไรในสภาพ ecosystem แบบนั้น" -- with the lens: "มองผ่านเลนส์ประชาชน
แบบช่วยตัวเองได้ จากข้อมูลทั้งระบบ โดยใช้สารสนเทศทั้งหมดที่เรามี".

Four questions, one tag on every line (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN, per AGENTS.md
epistemic floor -- REFUSED is its own explicit outcome, never silently blank):

  Q1 ใครรับผิดชอบที่นี่   -- nearest assets (radius, default 3km) -> OWNS -> agency (via the
                             owner->AG_ crosswalk, sources/owner_agency_crosswalk.yaml) ->
                             AUTHORIZES law (walking COMMANDS ancestors generically, so any
                             future tier added to the DAG surfaces automatically)
  Q2 อำนาจซ้อน/ต้องร่วมมือ -- tools/dag/bottlenecks.py's own functions (imported, never copied),
                             filtered down to the agencies Q1 actually found
  Q3 กฎหมาย/อำนาจมีปัญหา  -- edge_problems.yaml attributes already attached to the KG's path
                             edges (see tools/kg/build_kg.py apply_edge_problems), LAW_ nodes
                             whose own label still reads "มาตรา OPEN", and any node carrying a
                             missing_edge_problem attribute on the path
  Q4 ประชาชนทำอะไรได้เอง  -- WATER_MANAGER_QUESTION_BANK.md (VLG rows) + experience/ +
                             community cards (Yucharoen/Rangsit/Hat Yai), matched by class of
                             nearby asset and by the current readout_log state, each action
                             citing its card, phrased "อาจทำได้" -- never ไม่ต้อง/ห้าม/ไม่ควร/
                             ผ่อนคลาย

Refusal discipline: an empty/insufficient answer to any one question is reported as
{"refused": "<reason>"} for THAT question, never invented, and never silently blocks the
other three questions from answering what they can.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import networkx as nx
import yaml

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(HERE))

from assets_registry import haversine_km  # noqa: E402 -- reuse, do not copy
from tools.dag import bottlenecks as bn  # noqa: E402 -- reuse, do not copy
try:
    from tools.kg.unit_resolver import resolve_unit  # noqa: E402 -- build 6, 2026-09-27
except ImportError:  # pragma: no cover - defensive, e.g. shapely-less minimal env
    resolve_unit = None

GRAPH_PATH = HERE / "output" / "thailand_water_kg.graphml"
DB_PATH = HERE / "data" / "observations.sqlite"
CROSSWALK_PATH = HERE / "sources" / "owner_agency_crosswalk.yaml"

# RELAYED from site/build_data.py's own declared centre_lat/centre_lon per area_id (reused,
# never re-derived/geocoded here).
AREA_CENTERS = {
    "sammakorn": (13.758235, 100.676084),
    "ram53": (13.765540, 100.619095),
}

DEFAULT_RADIUS_KM = 3.0

BANNED_WORDS = ["ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"]

_LATLON_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


# ---------------------------------------------------------------------------
# graph / db loading
# ---------------------------------------------------------------------------

def load_graph(path: Path = GRAPH_PATH) -> nx.MultiDiGraph:
    if not path.exists():
        return nx.MultiDiGraph()
    return nx.read_graphml(path)


def _none_if_nullstr(v):
    return None if v in (None, "null", "None", "") else v


def _to_float(v):
    v = _none_if_nullstr(v)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_crosswalk(path: Path = CROSSWALK_PATH) -> dict:
    """Returns {owner_string: {"agency_id": str|None, "tag": str, "note": str}}."""
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    for r in doc.get("rows") or []:
        owner = r.get("owner")
        if owner is None:
            continue
        out[owner] = {
            "agency_id": r.get("agency_id"),
            "tag": r.get("tag") or "OPEN",
            "note": r.get("note") or "",
        }
    return out


def _latest_pump_state(area_id: str | None):
    """Most recent readout_log row of kind='pump' for an area, or None. Returns dict with
    stations_faulted/stations_total from extra_json, tagged MEASURED (it's this repo's own
    logged data), or None if no local DB / no rows (never fabricated)."""
    if not area_id or not DB_PATH.exists():
        return None
    try:
        # Read-only open: this answer path must never
        # mutate the store -- matches kb.py's own `?mode=ro` pattern.
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        cur = conn.execute(
            "SELECT extra_json, run_at_utc FROM readout_log "
            "WHERE area = ? AND kind = 'pump' ORDER BY run_at_utc DESC LIMIT 1",
            (area_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        extra_json, ts = row
        try:
            extra = json.loads(extra_json) if extra_json else {}
        except (TypeError, ValueError):
            extra = {}
        return {"ts": ts, "tag": "MEASURED", **extra}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# --at resolution
# ---------------------------------------------------------------------------

def resolve_point(at: str, G: nx.MultiDiGraph):
    """Returns dict {lat, lon, label, tag, area_id} or {"refused": reason}."""
    m = _LATLON_RE.match(at)
    if m:
        return {"lat": float(m.group(1)), "lon": float(m.group(2)),
                "label": at, "tag": "VERIFIED", "area_id": None}
    if at in AREA_CENTERS:
        lat, lon = AREA_CENTERS[at]
        return {"lat": lat, "lon": lon, "label": f"area_id:{at}", "tag": "RELAYED",
                "area_id": at}
    if at in G.nodes:
        d = G.nodes[at]
        lat, lon = _to_float(d.get("lat")), _to_float(d.get("lon"))
        if lat is None or lon is None:
            return {"refused": f"asset_id {at!r} exists in the graph but has no lat/lon "
                                f"(tag={d.get('tag')}) -- cannot compute a radius from it"}
        return {"lat": lat, "lon": lon, "label": f"asset_id:{at}", "tag": "VERIFIED",
                "area_id": None}
    return {"refused": f"could not resolve --at {at!r} as 'lat,lon', a known area_id "
                        f"({sorted(AREA_CENTERS)}), or an asset_id present in the graph"}


# ---------------------------------------------------------------------------
# Q1 -- nearest assets -> OWNS -> agency -> AUTHORIZES law, walking COMMANDS ancestors
# ---------------------------------------------------------------------------

def nearest_assets(G: nx.MultiDiGraph, lat: float, lon: float, radius_km: float) -> list:
    out = []
    for n, d in G.nodes(data=True):
        if d.get("kind") != "asset":
            continue
        alat, alon = _to_float(d.get("lat")), _to_float(d.get("lon"))
        if alat is None or alon is None:
            continue
        dist = haversine_km(lat, lon, alat, alon)
        if dist <= radius_km:
            out.append({
                "asset_id": n,
                "class": d.get("class"),
                "name_th": d.get("name_th"),
                "distance_km": round(dist, 3),
                "owner": _none_if_nullstr(d.get("owner")),
                "tag": d.get("tag"),
                "latest_value": _none_if_nullstr(d.get("latest_value")),
                "latest_ts": _none_if_nullstr(d.get("latest_ts")),
            })
    out.sort(key=lambda r: r["distance_km"])
    return out


def owner_to_agency(owner: str | None, crosswalk: dict) -> dict:
    if not owner:
        return {"agency_id": None, "tag": "OPEN",
                "note": "asset row has no owner recorded -- OWNS chain stops here"}
    row = crosswalk.get(owner)
    if row is None:
        return {"agency_id": None, "tag": "OPEN",
                "note": f"owner {owner!r} has no row in sources/owner_agency_crosswalk.yaml "
                        f"(known gap, see tools/kg/README.md 'Known gaps')"}
    return row


def commands_ancestor_chain(G: nx.MultiDiGraph, agency_id: str) -> list:
    """Walk COMMANDS edges backwards from agency_id, level by level, as far as the graph
    goes -- generic over however many tiers exist (this check's nationwide-hierarchy tiers
    included, once that data lands, with no code change needed here). Returns a list of
    {level, node, node_label, tag} ordered by level then node id; a node reachable at more
    than one level is kept at its FIRST (shallowest) level only."""
    if agency_id not in G:
        return []
    seen = {agency_id: 0}
    frontier = [agency_id]
    level = 0
    out = []
    while frontier:
        level += 1
        next_frontier = []
        for node in frontier:
            for u, _v, d in G.in_edges(node, data=True):
                if d.get("kind") != "COMMANDS":
                    continue
                if u in seen:
                    continue
                seen[u] = level
                out.append({
                    "level": level, "node": u,
                    "node_label": G.nodes[u].get("name_th") or u,
                    "tag": d.get("tag"),
                    "edge": (u, node),
                })
                next_frontier.append(u)
        frontier = next_frontier
    out.sort(key=lambda r: (r["level"], r["node"]))
    return out


def authorizes_for(G: nx.MultiDiGraph, agency_id: str) -> list:
    if agency_id not in G:
        return []
    out = []
    for u, _v, d in G.in_edges(agency_id, data=True):
        if d.get("kind") != "AUTHORIZES":
            continue
        label = G.nodes[u].get("name_th") or u
        section_open = "OPEN" in label
        out.append({
            "law_id": u,
            "law_label": label,
            "edge_tag": d.get("tag"),
            "section_status": "OPEN (section not yet verified)" if section_open
                               else "section stated in label (not re-verified against the "
                                    "gazette text by this tool)",
        })
    out.sort(key=lambda r: r["law_id"])
    return out


def q0_resolved_sub_basin(lat, lon) -> dict:
    """Build 6, 2026-09-27: resolves the queried point's DWR sub-basin FIRST, before Q1-Q4
    -- point-in-polygon against the real gis.dwr.go.th Sub_Basin archive (see
    tools/kg/unit_resolver.py), tag `VERIFIED-geometric` (same family as the KG's own
    IN_SUBBASIN edges). {"refused": "..."} (never a guess) when the resolver/archive is
    unavailable or the point falls outside every archived polygon."""
    if resolve_unit is None:
        return {"refused": "tools.kg.unit_resolver unavailable in this environment"}
    if lat is None or lon is None:
        return {"refused": "no resolved lat/lon for this query"}
    try:
        r = resolve_unit(lat, lon)
    except FileNotFoundError as e:
        return {"refused": str(e)}
    if not r.get("sb_code"):
        return {"refused": r.get("reason") or "point resolved outside every archived polygon"}
    return {
        "tag": "VERIFIED-geometric",
        "sb_code": r["sb_code"], "name_th": r.get("name_th"),
        "basin_code": r.get("basin_code"), "basin_name_th": r.get("basin_name_th"),
        "basin_name_en": r.get("basin_name_en"), "area_km2": r.get("area_km2"),
    }


def q1_who_is_responsible(G: nx.MultiDiGraph, lat: float, lon: float, radius_km: float,
                           crosswalk: dict) -> dict:
    assets = nearest_assets(G, lat, lon, radius_km)
    if not assets:
        return {"refused": f"no asset node within {radius_km} km of ({lat},{lon})"}

    chains = []
    agencies_found = set()
    path_edges = []  # (u, v) pairs walked, for Q3
    for a in assets:
        agency_row = owner_to_agency(a["owner"], crosswalk)
        chain_entry = {
            "asset": a,
            "owns_edge": {"agency_string": a["owner"], **agency_row},
            "commands_ancestors": [],
            "authorizes": [],
        }
        agency_id = agency_row.get("agency_id")
        if agency_id:
            agencies_found.add(agency_id)
            path_edges.append((f"agency:*", a["asset_id"]))  # OWNS edge, marker only
            chain_entry["commands_ancestors"] = commands_ancestor_chain(G, agency_id)
            for c in chain_entry["commands_ancestors"]:
                agencies_found.add(c["node"])
                path_edges.append(c["edge"])
            chain_entry["authorizes"] = authorizes_for(G, agency_id)
            for law in chain_entry["authorizes"]:
                path_edges.append((law["law_id"], agency_id))
        chains.append(chain_entry)

    return {
        "radius_km": radius_km,
        "assets_found": len(assets),
        "chains": chains,
        "_agencies_found": sorted(agencies_found),  # internal, feeds Q2/Q3
        "_path_edges": path_edges,  # internal, feeds Q3
    }


# ---------------------------------------------------------------------------
# Q2 -- overlapping/shared authority, reusing tools/dag/bottlenecks.py verbatim
# ---------------------------------------------------------------------------

def q2_overlapping_authority(agencies_found: list) -> dict:
    if not agencies_found:
        return {"refused": "Q1 found no agency chain -- nothing to check for overlap"}

    Gdag = bn.parse_dag(bn.DEFAULT_DAG_PATH)
    agset = set(agencies_found)

    conflicting = [
        r for r in bn.conflicting_commanders(Gdag)
        if r["node"] in agset or agset & set(r["commanders"])
    ]
    gaps = bn.ownership_gaps(Gdag)
    contested = [
        r for r in gaps["contested"]
        if r["node"] in agset or agset & set(r["owners"])
    ]
    unowned = [r for r in gaps["unowned"] if r["node"] in agset]
    shares = [
        r for r in bn.shares_without_arbitration(Gdag)
        if r["u"] in agset or r["v"] in agset
    ]

    if not (conflicting or contested or unowned or shares):
        return {
            "tag": "MEASURED-on-graph",
            "conflicting_commanders": [],
            "contested_ownership": [],
            "unowned": [],
            "shares_without_arbitration": [],
            "note": "no overlap/shared-authority row in tools/dag/bottlenecks.py's own "
                    "computations touches any agency Q1 found -- not the same as 'no overlap "
                    "exists anywhere in the DAG', see docs/knowledge/RESOURCE_AUTHORITY_AND_"
                    "BOTTLENECKS.md for the full graph-wide report",
        }
    return {
        "tag": "MEASURED-on-graph",
        "conflicting_commanders": conflicting,
        "contested_ownership": contested,
        "unowned": unowned,
        "shares_without_arbitration": shares,
    }


# ---------------------------------------------------------------------------
# Q3 -- law/authority problems on the path
# ---------------------------------------------------------------------------

def q3_problematic_law(G: nx.MultiDiGraph, chains: list, path_edges: list) -> dict:
    if not path_edges:
        return {"refused": "Q1 found no OWNS/COMMANDS chain -- no path edges to check"}

    edge_problems = []
    seen_edges = set()
    for u, v in path_edges:
        if u == "agency:*":
            continue  # synthetic OWNS marker, not a real DAG edge -- see Q1
        if (u, v) in seen_edges:
            continue  # same edge reached via more than one asset's chain -- report once
        if u not in G or v not in G:
            continue
        data = G.get_edge_data(u, v) or {}
        for _key, d in data.items():
            if d.get("problem_academic"):
                seen_edges.add((u, v))
                edge_problems.append({
                    "u": u, "u_label": G.nodes[u].get("name_th") or u,
                    "v": v, "v_label": G.nodes[v].get("name_th") or v,
                    "kind": d.get("kind"),
                    "problem_academic": d.get("problem_academic"),
                    "problem_tag": d.get("problem_tag"),
                    "problem_sources": d.get("problem_sources"),
                })

    missing_edge_problem_gaps = []
    nodes_on_path = {n for pair in path_edges for n in pair if n != "agency:*" and n in G}
    for n in sorted(nodes_on_path):
        gap = G.nodes[n].get("missing_edge_problem")
        if gap:
            missing_edge_problem_gaps.append({"node": n, "node_label": G.nodes[n].get("name_th") or n,
                                               "missing_edge_problem": gap})

    open_law_sections = []
    for chain in chains:
        for law in chain.get("authorizes", []):
            if "OPEN" in law["section_status"]:
                open_law_sections.append(law)
    # dedupe by law_id
    seen_law = set()
    dedup_open_laws = []
    for law in open_law_sections:
        if law["law_id"] in seen_law:
            continue
        seen_law.add(law["law_id"])
        dedup_open_laws.append(law)

    if not (edge_problems or missing_edge_problem_gaps or dedup_open_laws):
        return {
            "edge_problems_on_path": [],
            "law_sections_open": [],
            "missing_edge_problem_gaps": [],
            "note": "no edge_problems.yaml row, missing_edge_problem gap, or OPEN law "
                    "section found on this specific path -- see docs/knowledge/edge_problems"
                    ".yaml and docs/knowledge/RESOURCE_AUTHORITY_AND_BOTTLENECKS.md for the "
                    "graph-wide inventory (this is a per-path readout, not a whole-graph one)",
        }
    return {
        "edge_problems_on_path": edge_problems,
        "law_sections_open": dedup_open_laws,
        "missing_edge_problem_gaps": missing_edge_problem_gaps,
    }


# ---------------------------------------------------------------------------
# Q4 -- what citizens can do themselves (curated action library, each cites its card)
# ---------------------------------------------------------------------------

ACTION_LIBRARY = [
    {
        "id": "yucharoen_skill_roster",
        "trigger_classes": {"pump_station", "gate", "retention_basin"},
        "trigger_always": True,
        "text_th": "อาจทำ \"บัญชีทักษะ\" ลูกบ้าน (ช่าง/วิศวกร/พยาบาล/คนมีเรือ/บ้าน 3 ชั้น) ไว้ก่อนฤดูฝน",
        "cite": "docs/knowledge/card_yucharoen_model_2554.md#(f)-1",
    },
    {
        "id": "yucharoen_institution",
        "trigger_classes": set(),
        "trigger_always": True,
        "text_th": "อาจให้บทบาทนิติบุคคล/คณะกรรมการหมู่บ้านเป็น \"สถาบัน\" มีประชุมประจำ ไม่ผูกกับคนเดียว",
        "cite": "docs/knowledge/card_yucharoen_model_2554.md#(f)-2",
    },
    {
        "id": "yucharoen_fund",
        "trigger_classes": set(),
        "trigger_always": True,
        "text_th": "อาจตั้งกองทุนเล็กที่มีรายได้ประจำ กันไว้สำหรับช่วงน้ำท่วม",
        "cite": "docs/knowledge/card_yucharoen_model_2554.md#(f)-3",
    },
    {
        "id": "hatyai_backup_power",
        "trigger_classes": {"pump_station"},
        "trigger_pump_fault": True,
        "text_th": "อาจสอบถามนิติบุคคลหมู่บ้าน/สนน. เรื่องไฟฟ้าสำรอง/ไฟแยกของสถานีสูบใกล้บ้าน "
                    "(หาดใหญ่ระบุว่าไฟฟ้าดับกระทบสถานีสูบทั้งระบบพร้อมกัน)",
        "cite": "docs/knowledge/card_hatyai_city_climate.md#(f)-3",
    },
    {
        "id": "hatyai_raw_vs_official",
        "trigger_classes": set(),
        "trigger_always": True,
        "text_th": "อาจติดตามค่าดิบจากป้าย/ฟีดของหน่วยงานที่ประกาศแล้วประกอบการตัดสินใจเอง "
                    "แทนการอนุมานสาเหตุเอง",
        "cite": "docs/knowledge/card_hatyai_city_climate.md#(f)-2",
    },
    {
        "id": "hatyai_ground_map",
        "trigger_classes": set(),
        "trigger_always": True,
        "text_th": "อาจทำ \"แผนที่เดินดิน\" รายซอย: บ้าน 3 ชั้นที่เป็นจุดพักพิง, ผู้ป่วยติดเตียง/ฟอกไต, "
                    "เส้นทางน้ำเข้าจุดแรก",
        "cite": "docs/knowledge/card_hatyai_city_climate.md#(f)-4",
    },
    {
        "id": "rangsit_gauge_threshold",
        "trigger_classes": {"gate", "gauge"},
        "trigger_always": False,
        "text_th": "อาจติดตามระดับน้ำที่ประตู/สถานีวัดใกล้บ้านเทียบกับเกณฑ์เตือนภัยที่หน่วยงานเจ้าของ "
                    "ประกาศไว้ (ไม่ตั้งเกณฑ์ตัวเลขขึ้นเอง)",
        "cite": "docs/knowledge/card_rangsit_local_gov_flood_2561.md#(h)-1",
    },
    {
        "id": "rangsit_sandbag_electrical",
        "trigger_classes": {"pump_station", "gate"},
        "trigger_pump_fault": True,
        "text_th": "อาจเตรียมกระสอบทรายและระวังอุปกรณ์ไฟฟ้า/ขนของมีค่าขึ้นที่สูงไว้ล่วงหน้า "
                    "(มาตรการระดับ 1 ของรังสิตเมื่อสถานีสูบยังปกติแต่มีความเสี่ยง)",
        "cite": "docs/knowledge/card_rangsit_local_gov_flood_2561.md#(d)ระดับ-1",
    },
    {
        "id": "rangsit_relay_chain",
        "trigger_classes": set(),
        "trigger_always": True,
        "text_th": "อาจตั้งสายส่งต่อข่าวแบบ SMS/LINE ประธานชุมชน->เสียงตามสาย/กลุ่มไลน์ซอย "
                    "เพราะคนนอน-ตื่นไม่พร้อมกัน",
        "cite": "docs/knowledge/card_rangsit_local_gov_flood_2561.md#(h)-3",
    },
    {
        "id": "rangsit_structure_owner",
        "trigger_classes": {"pump_station", "gate"},
        "trigger_always": True,
        "text_th": "อาจถามคำถามเรื่องปั๊ม/ประตูโดยตรงกับเจ้าของโครงสร้าง (สนน./กรมชลประทาน) "
                    "เพราะ อปท./ชุมชนไม่มีอำนาจเหนือประตูระบายน้ำ",
        "cite": "docs/knowledge/card_rangsit_local_gov_flood_2561.md#(h)-5",
    },
]


def q4_self_help(assets: list, area_id: str | None) -> dict:
    classes_present = {a["class"] for a in assets}
    pump_state = _latest_pump_state(area_id)
    pump_fault = bool(pump_state and pump_state.get("stations_faulted", 0) and
                       pump_state.get("stations_faulted", 0) > 0)

    if not assets and not classes_present:
        return {"refused": "no nearby asset -- nothing to match a self-help action against "
                            "(Q1 already reported this)"}

    matched = []
    for act in ACTION_LIBRARY:
        applies = False
        reason = []
        if act.get("trigger_always") and (not act["trigger_classes"] or
                                           act["trigger_classes"] & classes_present):
            applies = True
            reason.append("always-applicable action for this village context")
        if act["trigger_classes"] & classes_present:
            applies = True
            reason.append(f"matches nearby asset class(es): "
                           f"{sorted(act['trigger_classes'] & classes_present)}")
        if act.get("trigger_pump_fault") and pump_fault:
            applies = True
            reason.append(f"matches current readout: {pump_state.get('stations_faulted')}/"
                           f"{pump_state.get('stations_total')} pump stations faulted "
                           f"(MEASURED, {pump_state.get('ts')})")
        if applies:
            matched.append({
                "id": act["id"], "text_th": act["text_th"], "cite": act["cite"],
                "why_matched": "; ".join(reason),
            })

    for act in matched:
        for w in BANNED_WORDS:
            if w in act["text_th"]:
                raise AssertionError(f"banned advice word {w!r} in action {act['id']!r}")

    if not matched:
        return {"refused": "no action in the curated library matched these asset classes "
                            "or readout state"}
    return {
        "pump_state": pump_state,
        "matched_actions": matched,
    }


# ---------------------------------------------------------------------------
# top-level
# ---------------------------------------------------------------------------

def build_result(at: str, radius_km: float = DEFAULT_RADIUS_KM,
                  use_shipped_kg: bool = True) -> dict:
    """Build the Q0-Q4 accountability dict without printing -- extracted 2026-10-02
    so `kb.py answer`/the MCP `floodconnect_get_accountability` tool can
    reuse this exact logic instead of re-deriving or shelling out to `run()`'s stdout.
    `run()` below is now a thin print wrapper over this function; behaviour unchanged.

    `use_shipped_kg`: shipping the nationwide
    output/thailand_water_kg.graphml must not silently change what kb.py's own
    answer path (`_answer_accountability`/`_answer_next_action`) returns for
    sammakorn/ram53, or the token-budget-tested shape of that answer -- kb.py's call
    site passes `use_shipped_kg=False` by default (see kb.py's own guard), which
    makes this function behave exactly as it did before the graph ever shipped (an
    empty graph -> the same `refused` -> MVP fallback path already covered by
    tests/test_kb_answer.py). Direct CLI use (`python3 -m tools.kg.accountability
    --at ...`) is the explicit request this guard is about, so `main()` below always
    passes the default `True` -- unaffected."""
    G = load_graph() if use_shipped_kg else nx.MultiDiGraph()
    if G.number_of_nodes() == 0:
        return {"at": at,
                "refused": "output/thailand_water_kg.graphml not found or empty -- run "
                           "`python3 -m tools.kg.build_kg` first"}

    point = resolve_point(at, G)
    if "refused" in point:
        return {"at": at, "Q1": point}

    sub_basin = q0_resolved_sub_basin(point.get("lat"), point.get("lon"))
    crosswalk = load_crosswalk()
    q1 = q1_who_is_responsible(G, point["lat"], point["lon"], radius_km, crosswalk)

    agencies_found = q1.pop("_agencies_found", [])
    path_edges = q1.pop("_path_edges", [])
    q2 = q2_overlapping_authority(agencies_found)
    q3 = q3_problematic_law(G, q1.get("chains", []), path_edges)
    assets = nearest_assets(G, point["lat"], point["lon"], radius_km)
    q4 = q4_self_help(assets, point.get("area_id"))

    return {
        "at": at, "resolved_point": point, "radius_km": radius_km,
        "Q0_sub_basin": sub_basin,
        "Q1_ใครรับผิดชอบที่นี่": q1,
        "Q2_อำนาจซ้อนทับ/ต้องร่วมมือ": q2,
        "Q3_กฎหมายหรืออำนาจที่อาจมีปัญหา": q3,
        "Q4_ประชาชนทำอะไรได้เอง": q4,
    }


def _kb_accountability_fallback(at: str, refused_text: "str | None") -> "dict | None":
    """FIX B item 3 (2026-10-04): reuses `kb.py`'s own `_accountability_fallback`
    verbatim -- never a second, divergent fallback implementation -- so this CLI gives
    the SAME answer `kb.py answer --at sammakorn`/`--at ram53` already gives on a fresh
    install, instead of a bare REFUSED this CLI alone used to print. `kb.py` already
    scopes this to the two MVP areas and to the two real refusal shapes it addresses
    (no graph file yet, or a graph with zero geolocated asset nodes nearby) -- see that
    function's own docstring; this wrapper adds no new scoping of its own, it is a thin
    lazy-import call to avoid a circular import at module load time (`kb.py` itself only
    imports this module lazily, inside `_answer_accountability`, never at its own module
    top level)."""
    try:
        import sys as _sys
        from pathlib import Path as _Path
        root = _Path(__file__).resolve().parent.parent.parent
        if str(root) not in _sys.path:
            _sys.path.insert(0, str(root))
        import kb as _kb_mod
    except Exception:  # pragma: no cover - defensive, kb.py must not be required to import
        return None
    try:
        return _kb_mod._accountability_fallback(at, refused_text, verbose=True)
    except Exception:  # pragma: no cover - defensive, a fallback bug must not crash the CLI
        return None


def _print_fallback(at: str, fallback: dict, as_json: bool) -> None:
    payload = {"at": at, "fallback": fallback}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    lines = [f"# accountability card -- ที่: {at}",
              f"[{fallback.get('tag', 'INSTINCT')}] {fallback.get('note', '')}"]
    for agency in fallback.get("owner_agencies", []):
        lines.append(f"  owner: {agency}")
    print("\n".join(lines))


def run(at: str, radius_km: float = DEFAULT_RADIUS_KM, as_json: bool = False) -> int:
    result = build_result(at, radius_km)
    # Three distinct refusal shapes, same as `kb.py::_answer_accountability`'s own
    # comment describes (checked in the same order, for the same reason -- the Thai-
    # keyed Q1 refusal must not slip through unchecked, see that function's comment):
    # (1) top-level `result["refused"]` (no graph file at all yet), (2) the bare early
    # key `result["Q1"]["refused"]` (point resolution itself failed), (3) the Thai-named
    # key `result["Q1_ใครรับผิดชอบที่นี่"]["refused"]` (point resolved, but no asset node
    # within radius -- the real, everywhere-nationwide gap `_kb_accountability_fallback`
    # exists for).
    refused_text = None
    if "refused" in result:
        refused_text = result["refused"]
    elif "refused" in result.get("Q1", {}):
        refused_text = result["Q1"]["refused"]
    elif "refused" in result.get("Q1_ใครรับผิดชอบที่นี่", {}):
        refused_text = result["Q1_ใครรับผิดชอบที่นี่"]["refused"]
    if refused_text is not None:
        fallback = _kb_accountability_fallback(at, refused_text)
        if fallback is not None:
            _print_fallback(at, fallback, as_json)
            return 0
        _print(result, as_json)
        return 1
    _print(result, as_json)
    return 0


def _print(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(_render_thai_card(result))


def _render_thai_card(result: dict) -> str:
    lines = []
    at = result.get("at")
    lines.append(f"# accountability card -- ที่: {at}")
    if "refused" in result:
        # Top-level refusal (e.g. the knowledge graph itself was not found/empty on a
        # fresh clone before `python3 -m tools.kg.build_kg` has run) -- there is no
        # `resolved_point`/`Q0_sub_basin` to render at all in this case, so this must
        # be checked before anything below reads into those keys with a bare
        # default {} (which used to fall through and KeyError on a missing field).
        lines.append(f"REFUSED [OPEN]: {result['refused']}")
        return "\n".join(lines)
    point = result.get("resolved_point", {})
    if "refused" in point:
        lines.append(f"REFUSED [OPEN]: {point['refused']}")
        return "\n".join(lines)
    lines.append(f"[{point.get('tag')}] resolved to lat={point.get('lat')}, "
                 f"lon={point.get('lon')} ({point.get('label')}), radius={result.get('radius_km')} km")

    sub_basin = result.get("Q0_sub_basin", {})
    if "refused" in sub_basin:
        lines.append(f"sub-basin: REFUSED [OPEN]: {sub_basin['refused']}")
    else:
        lines.append(f"sub-basin: [{sub_basin.get('tag', 'OPEN')}] {sub_basin.get('sb_code')} "
                     f"\"{sub_basin['name_th']}\" -- ลุ่มน้ำหลัก "
                     f"{sub_basin.get('basin_name_th')}/{sub_basin.get('basin_name_en')} "
                     f"({sub_basin.get('area_km2')} ตร.กม.)")
    lines.append("")

    q1 = result.get("Q1_ใครรับผิดชอบที่นี่", {})
    lines.append("## Q1 ใครรับผิดชอบที่นี่")
    if "refused" in q1:
        lines.append(f"REFUSED [OPEN]: {q1['refused']}")
    else:
        lines.append(f"[MEASURED] {q1['assets_found']} asset(s) within {q1['radius_km']} km")
        for c in q1["chains"]:
            a = c["asset"]
            lines.append(f"  [{a['tag']}] {a['class']} \"{a['name_th']}\" ({a['asset_id']}) "
                         f"— {a['distance_km']} km, owner={a['owner']!r}, "
                         f"latest={a['latest_value']}@{a['latest_ts']}")
            owns = c["owns_edge"]
            lines.append(f"    [{owns['tag']}] OWNS -> agency_id={owns['agency_id']} "
                         f"({owns['note']})")
            for anc in c["commands_ancestors"]:
                lines.append(f"    [{anc['tag']}] COMMANDS level {anc['level']}: "
                             f"{anc['node']} ({anc['node_label']})")
            for law in c["authorizes"]:
                lines.append(f"    [{law['edge_tag']}] AUTHORIZES <- {law['law_id']} "
                             f"({law['law_label']}) -- {law['section_status']}")
    lines.append("")

    q2 = result.get("Q2_อำนาจซ้อนทับ/ต้องร่วมมือ", {})
    lines.append("## Q2 อำนาจซ้อน/ต้องร่วมมือ")
    if "refused" in q2:
        lines.append(f"REFUSED [OPEN]: {q2['refused']}")
    else:
        tag = q2.get("tag", "MEASURED-on-graph")
        if q2.get("note"):
            lines.append(f"[{tag}] {q2['note']}")
        for r in q2.get("conflicting_commanders", []):
            lines.append(f"  [{tag}] conflicting commanders over {r['node']} "
                         f"({r['node_label']}): {r['commander_labels']}")
        for r in q2.get("contested_ownership", []):
            lines.append(f"  [{tag}] contested OWNS over {r['node']} ({r['node_label']}): "
                         f"{r['owner_labels']}")
        for r in q2.get("unowned", []):
            lines.append(f"  [{tag}] unowned resource: {r['node']} ({r['node_label']})")
        for r in q2.get("shares_without_arbitration", []):
            lines.append(f"  [{tag}] SHARES with no arbiter: {r['u_label']} <-> {r['v_label']}")
    lines.append("")

    q3 = result.get("Q3_กฎหมายหรืออำนาจที่อาจมีปัญหา", {})
    lines.append("## Q3 กฎหมาย/อำนาจที่อาจมีปัญหา")
    if "refused" in q3:
        lines.append(f"REFUSED [OPEN]: {q3['refused']}")
    else:
        if q3.get("note"):
            lines.append(f"[OPEN] {q3['note']}")
        for e in q3.get("edge_problems_on_path", []):
            lines.append(f"  [{e['problem_tag']}] {e['u_label']} -{e['kind']}-> {e['v_label']}: "
                         f"{e['problem_academic']} (sources: {e['problem_sources']})")
        for law in q3.get("law_sections_open", []):
            lines.append(f"  [OPEN] {law['law_label']} ({law['law_id']}) -- "
                         f"{law['section_status']}")
        for gap in q3.get("missing_edge_problem_gaps", []):
            lines.append(f"  [OPEN] gap at {gap['node']} ({gap['node_label']}): "
                         f"{gap['missing_edge_problem']}")
    lines.append("")

    q4 = result.get("Q4_ประชาชนทำอะไรได้เอง", {})
    lines.append("## Q4 ประชาชนทำอะไรได้เอง")
    if "refused" in q4:
        lines.append(f"REFUSED [OPEN]: {q4['refused']}")
    else:
        ps = q4.get("pump_state")
        if ps:
            lines.append(f"[{ps['tag']}] current pump readout: "
                         f"{ps.get('stations_faulted')}/{ps.get('stations_total')} faulted "
                         f"@ {ps.get('ts')}")
        for a in q4.get("matched_actions", []):
            lines.append(f"  [INSTINCT] {a['text_th']} (cite: {a['cite']}; {a['why_matched']})")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", required=True,
                    help="'lat,lon' | area_id (sammakorn, ram53) | asset_id in the graph")
    ap.add_argument("--radius", type=float, default=DEFAULT_RADIUS_KM,
                    help=f"km, default {DEFAULT_RADIUS_KM}")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    return run(args.at, args.radius, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
