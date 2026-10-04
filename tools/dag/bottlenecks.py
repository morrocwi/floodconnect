#!/usr/bin/env python3
"""
Resource-authority + bottleneck extraction over the governance DAG (FOUNDER_TASKS item 7).

Founder's task, verbatim: "ทำให้อำนาจบริหารทรัพยากรชัด และสกัดหา DAG คอขวดในการจัดการปัญหาน้ำท่วม
ประเทศไทยว่า การบริหารทรัพยากรร่วมกันของแต่ละ node อยู่จุดไหน และมีปัญหาอย่างไร"

This module parses ONLY docs/knowledge/water_system_dag.mmd, using the SAME regexes as
tools/kg/build_kg.py (imported, never copied -- see AGENTS.md / no-duplicate-parsing).
It builds one nx.MultiDiGraph (MultiDiGraph, not a plain DiGraph, because the mermaid
file legitimately carries more than one edge kind between the same ordered pair of nodes
-- e.g. AG_DDS both OWNS and, via a DC_* decision node, COMMANDS the same asset through
different edges; collapsing to a simple DiGraph would silently drop one of those edges).
Every number this script prints or writes is tagged MEASURED-on-graph: it is arithmetic
over the graph as parsed, not an external fact -- see docs/knowledge/RESOURCE_AUTHORITY_
AND_BOTTLENECKS.md for the interpretation layer (INSTINCT) built on top of these numbers.

Five computations (docs/knowledge/FOUNDER_TASKS_2026-09-27.md item 7):
  1. conflicting commanders  -- nodes with COMMANDS in-degree >= 2, listing commanders
  2. resource ownership gaps -- AS_/DT_ nodes with OWNS in-degree 0 (unowned) or >=2
     (contested)
  3. SHARES edges with no arbitration path -- no common node COMMANDS-reaches both ends
  4. single points of failure -- articulation nodes that, if removed, disconnect EVERY
     path from ANY DT_ node to ANY PP_ node, or from ANY FUNDS-source to ANY pump AS_
     node (label matches pump/ปั๊ม/สูบ)
  5. per-AG_ node resource holdings -- what it OWNS/COMMANDS/FUNDS and which LAW_ node
     AUTHORIZES it (derived from the graph only)

Usage:
    python3 -m tools.dag.bottlenecks [--dag PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve().parent.parent.parent  # repo root
sys.path.insert(0, str(HERE))

# Reuse the exact same regexes/kind-rename table the KG builder uses -- do not copy them.
from tools.kg.build_kg import MERMAID_NODE_RE, MERMAID_EDGE_RE, KIND_RENAME  # noqa: E402

DEFAULT_DAG_PATH = HERE / "docs" / "knowledge" / "water_system_dag.mmd"
DEFAULT_OUT_PATH = HERE / "docs" / "knowledge" / "bottlenecks.derived.json"

PUMP_PAT_RE = None  # set below after import to keep module import cheap
import re as _re  # noqa: E402
PUMP_PAT_RE = _re.compile(r"pump|ปั๊ม|สูบ", _re.IGNORECASE)


# ---------------------------------------------------------------------------------
# parsing (same node/edge regexes as tools/kg/build_kg.py -- MERMAID_NODE_RE / _EDGE_RE)
# ---------------------------------------------------------------------------------

def parse_dag(path: Path) -> nx.MultiDiGraph:
    """Parse docs/knowledge/water_system_dag.mmd into a MultiDiGraph. Node/edge lines
    are matched with the identical regexes tools/kg/build_kg.py uses (imported above),
    so a change to the mermaid dialect only ever needs fixing in one place."""
    G = nx.MultiDiGraph()
    if not path.exists():
        return G
    for line in path.read_text(encoding="utf-8").splitlines():
        m = MERMAID_NODE_RE.match(line)
        if m:
            nid, label = m.group("id"), m.group("label")
            G.add_node(nid, label=label)
            continue
        m = MERMAID_EDGE_RE.match(line)
        if m:
            u, v = m.group("u"), m.group("v")
            kind_raw, tagchar = m.group("kind"), m.group("tagchar")
            kind = KIND_RENAME.get(kind_raw, kind_raw)
            tag_map = {"V": "VERIFIED", "R": "RELAYED", "G": "RELAYED-GENERAL", "O": "OPEN"}
            tag = tag_map.get(tagchar, "OPEN")
            # Endpoints of an edge line are sometimes only declared implicitly (never
            # given their own id["label"] line) -- e.g. a node used only as an edge
            # endpoint. Add a bare node so the graph stays edge-complete.
            if u not in G:
                G.add_node(u, label=None)
            if v not in G:
                G.add_node(v, label=None)
            G.add_edge(u, v, kind=kind, tag=tag)
    return G


def label_of(G: nx.MultiDiGraph, n: str) -> str:
    return G.nodes[n].get("label") or n


def is_pump(G: nx.MultiDiGraph, n: str) -> bool:
    if not n.startswith("AS_"):
        return False
    label = G.nodes[n].get("label") or ""
    return bool(PUMP_PAT_RE.search(label)) or bool(PUMP_PAT_RE.search(n))


# ---------------------------------------------------------------------------------
# (1) conflicting commanders: COMMANDS in-degree >= 2
# ---------------------------------------------------------------------------------

def conflicting_commanders(G: nx.MultiDiGraph) -> list[dict]:
    out = []
    for n in G.nodes:
        commanders = sorted({u for u, _, d in G.in_edges(n, data=True) if d.get("kind") == "COMMANDS"})
        if len(commanders) >= 2:
            out.append({
                "node": n,
                "node_label": label_of(G, n),
                "commanders": commanders,
                "commander_labels": [label_of(G, c) for c in commanders],
            })
    out.sort(key=lambda r: (-len(r["commanders"]), r["node"]))
    return out


# ---------------------------------------------------------------------------------
# (2) resource ownership gaps: AS_/DT_ nodes with OWNS in-degree 0 or >=2
# ---------------------------------------------------------------------------------

def ownership_gaps(G: nx.MultiDiGraph) -> dict:
    unowned, contested = [], []
    for n in G.nodes:
        if not (n.startswith("AS_") or n.startswith("DT_")):
            continue
        owners = sorted({u for u, _, d in G.in_edges(n, data=True) if d.get("kind") == "OWNS"})
        if len(owners) == 0:
            unowned.append({"node": n, "node_label": label_of(G, n)})
        elif len(owners) >= 2:
            contested.append({
                "node": n, "node_label": label_of(G, n),
                "owners": owners, "owner_labels": [label_of(G, o) for o in owners],
            })
    unowned.sort(key=lambda r: r["node"])
    contested.sort(key=lambda r: (-len(r["owners"]), r["node"]))
    return {"unowned": unowned, "contested": contested}


# ---------------------------------------------------------------------------------
# (3) SHARES edges with no arbitration path
# ---------------------------------------------------------------------------------

def _commands_ancestors(G: nx.MultiDiGraph, target: str) -> set:
    """Nodes that can COMMANDS-reach `target`, directly or transitively, walking only
    COMMANDS edges backwards (chain of command). `target` itself is excluded."""
    Gc = nx.MultiDiGraph()
    Gc.add_nodes_from(G.nodes)
    for u, v, d in G.edges(data=True):
        if d.get("kind") == "COMMANDS":
            Gc.add_edge(u, v)
    if target not in Gc:
        return set()
    return set(nx.ancestors(Gc, target))


def shares_without_arbitration(G: nx.MultiDiGraph) -> list[dict]:
    """Rule (explicit, per FOUNDER_TASKS item 7): a SHARES edge (u, v) has an
    'arbitration path' if there exists at least one node w (w != u, w != v) that can
    COMMANDS-reach BOTH u and v (directly or transitively through the COMMANDS-only
    subgraph -- i.e. w is a common node somewhere up both chains of command). If the
    intersection of u's command-ancestors and v's command-ancestors is empty, there is
    no single authority positioned to arbitrate a conflict over that shared resource,
    and the edge is flagged."""
    out = []
    seen = set()
    for u, v, d in G.edges(data=True):
        if d.get("kind") != "SHARES":
            continue
        key = (u, v)
        if key in seen:
            continue
        seen.add(key)
        anc_u = _commands_ancestors(G, u)
        anc_v = _commands_ancestors(G, v)
        common = (anc_u & anc_v) - {u, v}
        if not common:
            out.append({
                "u": u, "u_label": label_of(G, u),
                "v": v, "v_label": label_of(G, v),
                "tag": d.get("tag"),
            })
    out.sort(key=lambda r: (r["u"], r["v"]))
    return out


# ---------------------------------------------------------------------------------
# (4) single points of failure
# ---------------------------------------------------------------------------------

def _has_path_with_virtuals(G: nx.MultiDiGraph, sources: list, sinks: list, removed: str | None) -> bool:
    """True if at least one of `sources` can reach at least one of `sinks` in G, with
    `removed` (if given) deleted first. Implemented with a virtual super-source/sink so
    a single BFS answers the 'any of -> any of' question."""
    H = G.copy()
    if removed is not None and removed in H:
        H.remove_node(removed)
    src_ok = [s for s in sources if s in H]
    snk_ok = [s for s in sinks if s in H]
    if not src_ok or not snk_ok:
        return False
    H.add_node("__SRC__")
    H.add_node("__SNK__")
    for s in src_ok:
        H.add_edge("__SRC__", s)
    for t in snk_ok:
        H.add_edge(t, "__SNK__")
    return nx.has_path(H, "__SRC__", "__SNK__")


def single_points_of_failure(G: nx.MultiDiGraph) -> list[dict]:
    """Articulation points of the undirected simplification of G, filtered down to
    those whose removal disconnects EVERY path from any DT_ node to any PP_ node, or
    from any FUNDS-source (a node with an outgoing FUNDS edge) to any pump AS_ node.
    A candidate is reported once per broken route family it cuts."""
    UG = nx.Graph()
    UG.add_nodes_from(G.nodes)
    for u, v in G.edges():
        UG.add_edge(u, v)
    try:
        candidates = set(nx.articulation_points(UG))
    except nx.NetworkXPointlessConcept:
        candidates = set()

    dt_nodes = [n for n in G.nodes if n.startswith("DT_")]
    pp_nodes = [n for n in G.nodes if n.startswith("PP_")]
    funds_sources = sorted({u for u, _, d in G.edges(data=True) if d.get("kind") == "FUNDS"})
    pump_nodes = [n for n in G.nodes if is_pump(G, n)]

    dt_pp_before = _has_path_with_virtuals(G, dt_nodes, pp_nodes, None)
    funds_pump_before = _has_path_with_virtuals(G, funds_sources, pump_nodes, None)

    out = []
    for c in sorted(candidates):
        cuts_dt_pp = dt_pp_before and not _has_path_with_virtuals(G, dt_nodes, pp_nodes, c)
        cuts_funds_pump = funds_pump_before and not _has_path_with_virtuals(G, funds_sources, pump_nodes, c)
        if not (cuts_dt_pp or cuts_funds_pump):
            continue
        entry = {"node": c, "node_label": label_of(G, c), "cuts": []}
        if cuts_dt_pp:
            entry["cuts"].append("DT_to_PP (data -> citizen)")
        if cuts_funds_pump:
            entry["cuts"].append("FUNDS_source_to_pump")
        out.append(entry)
    out.sort(key=lambda r: r["node"])
    return out


# ---------------------------------------------------------------------------------
# (5) per-AG_ node resource holdings
# ---------------------------------------------------------------------------------

def resource_holdings(G: nx.MultiDiGraph) -> list[dict]:
    out = []
    for n in sorted(nd for nd in G.nodes if nd.startswith("AG_")):
        owns = sorted({v for _, v, d in G.out_edges(n, data=True) if d.get("kind") == "OWNS"})
        commands = sorted({v for _, v, d in G.out_edges(n, data=True) if d.get("kind") == "COMMANDS"})
        funds = sorted({v for _, v, d in G.out_edges(n, data=True) if d.get("kind") == "FUNDS"})
        authorized_by = sorted({u for u, _, d in G.in_edges(n, data=True) if d.get("kind") == "AUTHORIZES"})
        shares_with = sorted({v for _, v, d in G.out_edges(n, data=True) if d.get("kind") == "SHARES"} |
                              {u for u, _, d in G.in_edges(n, data=True) if d.get("kind") == "SHARES"})
        if not (owns or commands or funds or authorized_by or shares_with):
            continue
        out.append({
            "node": n,
            "node_label": label_of(G, n),
            "owns": owns,
            "commands": commands,
            "funds": funds,
            "authorized_by_law": authorized_by,
            "shares_resource_with": shares_with,
        })
    return out


# ---------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------

def build_report(G: nx.MultiDiGraph) -> dict:
    return {
        "tag": "MEASURED-on-graph",
        "source": "docs/knowledge/water_system_dag.mmd",
        "node_count": G.number_of_nodes(),
        "edge_count": G.number_of_edges(),
        "rule_1_conflicting_commanders": conflicting_commanders(G),
        "rule_2_ownership_gaps": ownership_gaps(G),
        "rule_3_shares_without_arbitration": shares_without_arbitration(G),
        "rule_4_single_points_of_failure": single_points_of_failure(G),
        "rule_5_resource_holdings_by_agency": resource_holdings(G),
    }


def print_table(title: str, rows: list[dict], cols: list[str]) -> None:
    print(f"\n== {title} ({len(rows)}) ==")
    if not rows:
        print("  (none)")
        return
    for r in rows:
        parts = [f"{c}={r.get(c)}" for c in cols]
        print("  " + " | ".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dag", default=str(DEFAULT_DAG_PATH))
    ap.add_argument("--out", default=str(DEFAULT_OUT_PATH))
    args = ap.parse_args()

    G = parse_dag(Path(args.dag))
    print(f"Parsed {G.number_of_nodes()} nodes, {G.number_of_edges()} edges from {args.dag}")

    report = build_report(G)

    print_table("Rule 1: conflicting commanders (COMMANDS in-degree >= 2)",
                report["rule_1_conflicting_commanders"], ["node", "node_label", "commanders"])
    print_table("Rule 2a: unowned resources (OWNS in-degree 0)",
                report["rule_2_ownership_gaps"]["unowned"], ["node", "node_label"])
    print_table("Rule 2b: contested resources (OWNS in-degree >= 2)",
                report["rule_2_ownership_gaps"]["contested"], ["node", "node_label", "owners"])
    print_table("Rule 3: SHARES edges with no arbitration path",
                report["rule_3_shares_without_arbitration"], ["u", "u_label", "v", "v_label"])
    print_table("Rule 4: single points of failure",
                report["rule_4_single_points_of_failure"], ["node", "node_label", "cuts"])
    print(f"\n== Rule 5: per-AG_ resource holdings ({len(report['rule_5_resource_holdings_by_agency'])} agencies with any holding) ==")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
