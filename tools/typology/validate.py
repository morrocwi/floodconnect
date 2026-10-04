#!/usr/bin/env python3
"""
tools/typology/validate.py -- implements the linking-contract validation rules from
FLOW_STALL_TYPOLOGY_EXTENSION_PROPOSAL_2026-09-28.md §4c against the graph
`tools/typology/build_graph.py` produces.

Rules (proposal §4c, numbered to match that document):
  1. No orphan node -- every node has >=1 edge in or out.
  2. Every `sensor` has exactly one `owned_by` edge (an `OPEN` target still counts as
     "has one" -- the rule is about cardinality, not resolution).
  3. Every `gate`/`pump` has >=1 `operates` edge and >=1 `decides` edge.
  4. Every zone (`soi_surface`-kind node) reaches a sink (`river`/`sea`-kind node) via a
     `flows_to` chain.
  5. Every `warns` edge has a non-empty `instruction` attribute.
  6. Every edge that carries a claim (`decides`/`warns`/`supplies`/`reports_to`) has a
     tag from the workspace's 5-tag ladder (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN, or
     one of this graph's documented extensions of it).
  7. (added here, not numbered in the proposal, per its own §2 amendment) every
     `decides` edge targets a `gate`/`pump` node only, never an `edge` -- the
     independent-review fix.

OPEN links are the STRUCTURAL GAPS this typology extension exists to surface -- expected,
not failures to hide. This script exits non-zero ONLY on a schema error (a row that
can't be parsed, an edge_kind not in the closed vocabulary, a `decides` edge whose target
kind is wrong) -- never merely because an OPEN link exists.

Usage:
    python3 -m tools.typology.validate [--graph output/typology_graph.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.backtest.outside_calibrated_range import (  # noqa: E402
    classify_outside_calibrated_range, load_derived,
)

CLOSED_EDGE_VOCAB = {"flows_to", "owned_by", "operates", "decides", "warns", "supplies",
                      "reports_to", "part_of", "escalates_to", "precedes"}
# escalates_to (added 2026-09-28) -- community_dag.py's own forward-only household->
# buddy_cell->zone->support/internal_safe->egress->external_safe edges, imported from
# public/main 5364c23 and carried through unchanged; layer ordering is enforced by
# community_dag.py's own validate_document(), not re-checked here.
#
# precedes (added 2026-09-28, คู่มือจัดการบ้านหลังน้ำลด task DAG) -- household_task
# ordering ("B only after A"). No existing edge kind fit a task-sequencing relationship
# (flows_to=water, escalates_to=self-help social-network layer with its own KIND_LAYER
# numbers, everything else means agency/resource relationships). Acyclicity is enforced
# below (rule_precedes_acyclic), a schema error, never an OPEN gap.
CLAIM_EDGE_KINDS = {"decides", "warns", "supplies", "reports_to", "part_of"}
VALID_TAG_PREFIXES = ("VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN")

ALLOWED_PAIRS = {
    # edge_kind -> set of (from_kind, to_kind) pairs allowed, "*" = any kind, "OPEN" is
    # always allowed on either side regardless of this table (an unresolved link).
    "owned_by": {("sensor", "agency"), ("gate", "agency"), ("pump", "agency")},
    "operates": {("agency", "gate"), ("agency", "pump")},
    "decides": {("agency", "gate"), ("agency", "pump")},  # amended: no `edge` target
    "warns": {("agency", "warning_channel"), ("warning_channel", "soi_surface")},
    "supplies": {("resource", "soi_surface"), ("resource", "*")},
    "reports_to": {("soi_surface", "*"), ("agency", "agency"), ("*", "*")},
    # reports_to is deliberately loose (proposal: "community (person/page, ไม่ใช่
    # agency)" -- this graph's `agency_class` distinguishes state vs civil actors within
    # the same `agency` kind, so a strict from_kind check here would reject the
    # civil-society rows the proposal itself asks for; see validate_pairs() below for
    # the actual agency_class-aware check on reports_to/supplies).
    "part_of": {("agency", "ministry"), ("ministry", "government")},
    # part_of -- added 2026-09-28 (founder ask: fold the กพร. Joint KPI agency list into
    # the power layer). `ministry` here also covers the Joint-KPI document's two other
    # grouping categories (องค์การมหาชน/รัฐวิสาหกิจ) and กทม.'s special local-government
    # status -- see typology/nodes/ministries.yaml's own `group_type` attribute for which
    # is which; the edge-target KIND is still `ministry` for all of them (a modelling
    # simplification documented there, not a silent conflation).
}


def load_graph(path: Path) -> nx.MultiDiGraph:
    data = json.loads(path.read_text(encoding="utf-8"))
    return nx.node_link_graph(data, edges="edges", multigraph=True, directed=True)


def _tag_ok(tag) -> bool:
    if not tag:
        return False
    base = str(tag).split(" ")[0].split("(")[0].split("+")[0].split("-")[0].strip()
    return base in VALID_TAG_PREFIXES


def rule_no_orphans(G: nx.MultiDiGraph) -> list:
    return [n for n in G.nodes if G.degree(n) == 0]


def rule_sensor_owned_by_exactly_one(G: nx.MultiDiGraph) -> dict:
    violations, ok = [], []
    for n, d in G.nodes(data=True):
        if d.get("kind") != "sensor":
            continue
        owned_by_edges = [(u, v) for u, v, ed in G.out_edges(n, data=True)
                            if ed.get("kind") == "owned_by"]
        if len(owned_by_edges) == 1:
            ok.append(n)
        else:
            violations.append((n, len(owned_by_edges)))
    return {"ok": ok, "violations": violations}


def rule_gate_pump_operates_decides(G: nx.MultiDiGraph) -> dict:
    open_gaps, ok = [], []
    for n, d in G.nodes(data=True):
        if d.get("kind") not in ("gate", "pump"):
            continue
        operates = [ed for _, _, ed in G.in_edges(n, data=True) if ed.get("kind") == "operates"]
        decides = [ed for _, _, ed in G.in_edges(n, data=True) if ed.get("kind") == "decides"]
        row = {"node": n, "operates_count": len(operates), "decides_count": len(decides),
                "operates_all_open": bool(operates) and all(e.get("tag") == "OPEN" for e in operates),
                "decides_all_open_or_missing": (not decides) or all(e.get("tag") == "OPEN" for e in decides)}
        if operates and decides:
            ok.append(row)
        else:
            open_gaps.append(row)
    return {"ok": ok, "open_gaps": open_gaps}


def rule_zone_reaches_sink(G: nx.MultiDiGraph) -> dict:
    flow_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("kind") == "flows_to"]
    FG = nx.DiGraph()
    FG.add_edges_from(flow_edges)
    sinks = {n for n, d in G.nodes(data=True) if d.get("kind") in ("river", "sea")}
    zones = {n for n, d in G.nodes(data=True) if d.get("kind") == "soi_surface"}
    reachable, unreachable = [], []
    for z in zones:
        if z not in FG:
            unreachable.append(z)
            continue
        reached = any(nx.has_path(FG, z, s) for s in sinks if s in FG)
        (reachable if reached else unreachable).append(z)
    return {"sinks": sorted(sinks), "reachable": sorted(reachable), "unreachable": sorted(unreachable)}


def rule_warns_instruction(G: nx.MultiDiGraph) -> list:
    violations = []
    for u, v, d in G.edges(data=True):
        if d.get("kind") != "warns":
            continue
        instr = d.get("instruction")
        if not instr or not str(instr).strip():
            violations.append((u, v))
    return violations


def rule_claim_edges_tagged(G: nx.MultiDiGraph) -> list:
    violations = []
    for u, v, d in G.edges(data=True):
        if d.get("kind") in CLAIM_EDGE_KINDS and not _tag_ok(d.get("tag")):
            violations.append((u, v, d.get("kind"), d.get("tag")))
    return violations


def rule_decides_target_kind(G: nx.MultiDiGraph) -> list:
    """Schema error (not an OPEN gap): a `decides` edge whose target node is not a
    `gate`/`pump` kind (and not the shared OPEN sentinel) -- the independent-review fix
    that dropped `edge` as an allowed decides target."""
    violations = []
    for u, v, d in G.edges(data=True):
        if d.get("kind") != "decides":
            continue
        if v == "OPEN":
            continue
        target_kind = G.nodes[v].get("kind") if G.has_node(v) else None
        if target_kind not in ("gate", "pump"):
            violations.append((u, v, target_kind))
    return violations


def rule_precedes_acyclic(G: nx.MultiDiGraph) -> list:
    """Schema error: any cycle among `precedes` edges -- a household task sequence must
    be a genuine DAG (task 3's own requirement, คู่มือจัดการบ้านหลังน้ำลด task DAG,
    2026-09-28). Returns the list of node ids on a found cycle, or [] if acyclic."""
    precedes_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("kind") == "precedes"]
    PG = nx.DiGraph()
    PG.add_edges_from(precedes_edges)
    try:
        cycle = nx.find_cycle(PG)
        return [u for u, v in cycle] + [cycle[-1][1]]
    except nx.NetworkXNoCycle:
        return []


def rule_part_of_target_kind(G: nx.MultiDiGraph) -> list:
    """Schema error: a `part_of` edge whose (from_kind, to_kind) pair is not
    (agency, ministry) or (ministry, government) -- see ALLOWED_PAIRS["part_of"]."""
    violations = []
    for u, v, d in G.edges(data=True):
        if d.get("kind") != "part_of":
            continue
        u_kind = G.nodes[u].get("kind") if G.has_node(u) else None
        v_kind = G.nodes[v].get("kind") if G.has_node(v) else None
        if (u_kind, v_kind) not in ALLOWED_PAIRS["part_of"]:
            violations.append((u, v, u_kind, v_kind))
    return violations


CAPABILITY_FIELDS = ["capability_operational_policy", "capability_roles_responsibilities",
                      "capability_action_plan", "capability_monitoring_loop",
                      "capability_logistics", "capability_training"]


def report_capability_gaps(G: nx.MultiDiGraph) -> dict:
    """Non-error report (2026-09-28, TDRI C3 -- Command/Control/Capability -- framing):
    for every agency node that carries the 6-element capability checklist at all, which
    of the 6 are still `null` (OPEN). An agency with NONE of the 6 fields present is not
    listed here (it was never in scope for this checklist -- see typology/nodes/
    tdri_overlay_2026-09-28.yaml for which agencies carry it)."""
    gaps = {}
    for n, d in G.nodes(data=True):
        if d.get("kind") != "agency":
            continue
        present = [f for f in CAPABILITY_FIELDS if f in d]
        if not present:
            continue
        missing = [f for f in present if d.get(f) is None]
        if missing:
            gaps[n] = missing
    return gaps


def report_warning_quality_gaps(G: nx.MultiDiGraph) -> dict:
    """Non-error report (2026-09-28, TDRI/CAP-like warning-quality fields): for every
    `warns` edge, which of {instruction, datum, area, lead_time} is missing/OPEN. Ties to
    this repo's own existing datum rule (docs/FLOW_STALL_TYPOLOGY.md: ground level !=
    water level, canal_graph.py's REASON_DATUM_MISMATCH) -- a warning with no stated datum
    is the same class of failure as a station reading with no declared datum."""
    gaps = {}
    for u, v, d in G.edges(data=True):
        if d.get("kind") != "warns":
            continue
        missing = [f for f in ("instruction", "datum", "area", "lead_time")
                   if not d.get(f) or str(d.get(f)).strip().upper() == "OPEN"
                   or str(d.get(f)).startswith("OPEN")]
        if missing:
            gaps[f"{u} -> {v}"] = missing
    return gaps


def rule_closed_edge_vocab(G: nx.MultiDiGraph) -> list:
    return sorted({d.get("kind") for _, _, d in G.edges(data=True)} - CLOSED_EDGE_VOCAB)


def report_outside_calibrated_range(G: nx.MultiDiGraph) -> dict:
    """Non-error report (2026-09-28, docs/knowledge/card_dual_state_reescalation_
    hatyai_2026-09-28.md, Hat Yai finding H): for every node that declares an
    `ocr_check` attribute -- {unit, variable, observed_value}, a plain OPTIONAL
    self-declared readout, never invented here -- looks up
    sources/coping_thresholds.yaml's own derived ceiling and labels the node
    OUTSIDE_CALIBRATED_RANGE / WITHIN_CALIBRATED_RANGE / OPEN. No node in this graph
    declares `ocr_check` yet (no unit/variable in this repo has both a live numeric
    reading AND a calibrated ceiling wired to the SAME typology node) -- this function
    exists so the wiring is ready the moment one does, exactly the honest-gap discipline
    the rest of this file already follows."""
    derived = load_derived()
    out = {}
    for n, d in G.nodes(data=True):
        chk = d.get("ocr_check")
        if not chk:
            continue
        label = classify_outside_calibrated_range(
            chk.get("unit"), chk.get("variable"), chk.get("observed_value"), derived)
        out[n] = label
    return out


def run(graph_path: Path) -> int:
    G = load_graph(graph_path)
    report = {}
    schema_errors = []

    orphans = rule_no_orphans(G)
    report["orphans"] = orphans

    sensor_owned = rule_sensor_owned_by_exactly_one(G)
    report["sensor_owned_by_exactly_one"] = {
        "ok_count": len(sensor_owned["ok"]), "violations": sensor_owned["violations"]}
    if sensor_owned["violations"]:
        schema_errors.append(f"{len(sensor_owned['violations'])} sensor(s) do not have "
                              f"exactly one owned_by edge: {sensor_owned['violations']}")

    gp = rule_gate_pump_operates_decides(G)
    report["gate_pump_operates_decides"] = {
        "ok_count": len(gp["ok"]), "open_gap_count": len(gp["open_gaps"]),
        "open_gaps": gp["open_gaps"]}

    zones = rule_zone_reaches_sink(G)
    report["zone_reaches_sink"] = zones

    warns_viol = rule_warns_instruction(G)
    report["warns_instruction_violations"] = warns_viol
    if warns_viol:
        schema_errors.append(f"{len(warns_viol)} warns edge(s) missing instruction: {warns_viol}")

    tag_viol = rule_claim_edges_tagged(G)
    report["claim_edge_tag_violations"] = tag_viol
    if tag_viol:
        schema_errors.append(f"{len(tag_viol)} claim edge(s) missing a valid tag: {tag_viol}")

    decides_viol = rule_decides_target_kind(G)
    report["decides_target_kind_violations"] = decides_viol
    if decides_viol:
        schema_errors.append(f"{len(decides_viol)} decides edge(s) target a non-gate/pump "
                              f"node (schema error, dropped per independent review): {decides_viol}")

    part_of_viol = rule_part_of_target_kind(G)
    report["part_of_target_kind_violations"] = part_of_viol
    if part_of_viol:
        schema_errors.append(f"{len(part_of_viol)} part_of edge(s) violate the allowed "
                              f"(from_kind, to_kind) pairs: {part_of_viol}")

    precedes_cycle = rule_precedes_acyclic(G)
    report["precedes_cycle"] = precedes_cycle
    if precedes_cycle:
        schema_errors.append(f"precedes edges contain a cycle (schema error, task "
                              f"ordering must be a DAG): {precedes_cycle}")

    bad_kinds = rule_closed_edge_vocab(G)
    report["edge_kinds_outside_closed_vocab"] = bad_kinds
    if bad_kinds:
        schema_errors.append(f"edge kind(s) outside the closed vocabulary: {bad_kinds}")

    # -- non-error report sections (2026-09-28, TDRI framing) -- structural gaps this
    # extension exists to SURFACE, never cause a non-zero exit on their own.
    capability_gaps = report_capability_gaps(G)
    report["capability_gaps"] = capability_gaps
    warning_quality_gaps = report_warning_quality_gaps(G)
    report["warning_quality_gaps"] = warning_quality_gaps
    outside_calibrated_range = report_outside_calibrated_range(G)
    report["outside_calibrated_range"] = outside_calibrated_range

    report["schema_errors"] = schema_errors
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if schema_errors:
        print(f"\nFAILED: {len(schema_errors)} schema error(s) -- see above (real errors, "
              f"never an OPEN link).", file=sys.stderr)
        return 1
    print(f"\nOK: no schema errors. {len(orphans)} orphan node(s), "
          f"{len(sensor_owned['violations'])} sensor cardinality violation(s), "
          f"{len(gp['open_gaps'])} gate/pump operates+decides OPEN gap(s), "
          f"{len(zones['unreachable'])} zone(s) not reaching a sink, "
          f"{len(capability_gaps)} agency/agencies with capability-checklist gaps, "
          f"{len(warning_quality_gaps)} warns edge(s) with warning-quality gaps -- these "
          f"are the documented structural gaps this extension exists to surface, not "
          f"failures.", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default=str(REPO_ROOT / "output" / "typology_graph.json"))
    args = ap.parse_args()
    sys.exit(run(Path(args.graph)))


if __name__ == "__main__":
    main()
