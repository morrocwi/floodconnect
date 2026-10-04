"""
tests/test_typology_postflood_guide_2026-09-28.py -- household-level (ปัจเจก) post_event
task DAG extracted from "คู่มือจัดการบ้านหลังน้ำลด" (ASA/ThaiGDA/EIT, พฤศจิกายน 2554).
Real repo data only (docs/knowledge/card_guide_post_flood_home.md +
typology/nodes/postflood_guide_*.yaml + typology/edges/*postflood_guide*.yaml).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.typology import build_graph, validate  # noqa: E402

TASK_IDS = [
    "HHTASK.PREP", "HHTASK.PHOTO_DAMAGE", "HHTASK.VENTILATE", "HHTASK.ELECTRICAL",
    "HHTASK.STRUCTURE", "HHTASK.CLEANING", "HHTASK.SANITATION", "HHTASK.DOORS_WINDOWS",
    "HHTASK.FLOORS", "HHTASK.WALLS", "HHTASK.APPLIANCES", "HHTASK.FURNITURE",
    "HHTASK.PLANTS",
]


@pytest.fixture(scope="module")
def graph():
    import networkx as nx
    G = nx.MultiDiGraph()
    build_graph.build_water_layer(G)
    build_graph.load_registry_nodes(G)
    build_graph.apply_node_overlays(G)
    build_graph.load_self_help_dag(G)
    build_graph.load_registry_edges(G)
    return G


def test_all_household_task_nodes_present(graph):
    for tid in TASK_IDS:
        assert graph.has_node(tid), f"expected household_task node {tid}"
        assert graph.nodes[tid]["kind"] == "household_task"


def test_every_task_has_page_cite_and_source(graph):
    for tid in TASK_IDS:
        d = graph.nodes[tid]
        assert d.get("page_cite"), f"{tid} missing page_cite"
        assert d.get("source"), f"{tid} missing source"


def test_every_task_is_phase_post_event(graph):
    for tid in TASK_IDS:
        assert graph.nodes[tid].get("phase") == "post_event", f"{tid}.phase"


def test_every_task_is_self_help_layer_0(graph):
    for tid in TASK_IDS:
        d = graph.nodes[tid]
        assert d.get("layer") == "self_help"
        assert d.get("self_help_layer") == 0


def test_precedes_dag_is_acyclic(graph):
    cycle = validate.rule_precedes_acyclic(graph)
    assert cycle == [], f"precedes edges must be acyclic, found cycle: {cycle}"


def test_precedes_chain_covers_all_13_tasks_in_order(graph):
    """Every consecutive pair in TASK_IDS (the guide's own TOC order) must have a direct
    precedes edge, and a topological sort of just these 13 nodes must respect that
    order. (Not asserted via shortest_path: HHTASK.ELECTRICAL -> HHTASK.CLEANING is a
    real, separately-sourced SHORTCUT edge -- the guide's strongest explicit dependency
    -- alongside HHTASK.ELECTRICAL -> HHTASK.STRUCTURE -> HHTASK.CLEANING, both true at
    once.)"""
    import networkx as nx
    precedes_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("kind") == "precedes"]
    PG = nx.DiGraph()
    PG.add_edges_from(precedes_edges)
    for a, b in zip(TASK_IDS, TASK_IDS[1:]):
        assert PG.has_edge(a, b), f"expected a direct precedes edge {a} -> {b}"
    sub = PG.subgraph(TASK_IDS)
    topo = list(nx.topological_sort(sub))
    assert topo == TASK_IDS, f"topological order of the 13 tasks does not match guide order: {topo}"


def test_electrical_precedes_cleaning_explicit_dependency(graph):
    """The guide's own strongest explicit dependency (p.8): cleaning only starts after
    the electrical system is confirmed fully off/safe."""
    assert graph.has_edge("HHTASK.ELECTRICAL", "HHTASK.CLEANING")
    d = graph.get_edge_data("HHTASK.ELECTRICAL", "HHTASK.CLEANING")
    edge = next(iter(d.values()))
    assert edge["precedes_basis"] == "explicit"


def test_household_template_bridges_to_task_chain(graph):
    assert graph.has_edge("sammakorn_household_template", "HHTASK.PREP")
    d = graph.get_edge_data("sammakorn_household_template", "HHTASK.PREP")
    edge = next(iter(d.values()))
    assert edge["kind"] == "precedes"
    assert edge["tag"] == "OPEN"  # bridge, not stated by the guide itself


def test_agency_links_resolve_to_existing_or_new_agency_nodes(graph):
    for tid, expected_agency in (("HHTASK.ELECTRICAL", "AG_MEA"),
                                  ("HHTASK.ELECTRICAL", "AG_PEA"),
                                  ("HHTASK.STRUCTURE", "AG_EIT")):
        assert graph.has_edge(tid, expected_agency), f"expected {tid} -> {expected_agency}"
        assert graph.nodes[expected_agency]["kind"] == "agency"
        d = graph.get_edge_data(tid, expected_agency)
        assert all(ed.get("kind") == "reports_to" for ed in d.values())


def test_no_invented_gas_or_health_tasks(graph):
    """The guide contains no gas-safety or drinking-water/food/health content -- must
    not be fabricated even though the founder's own example flow mentioned them."""
    labels = " ".join(str(graph.nodes[t].get("label_th", "")) for t in TASK_IDS)
    assert "แก๊ส" not in labels
    assert "น้ำดื่ม" not in labels


def test_no_computed_quantities_only_quoted_numbers(graph):
    """Every number the guide gives (chlorine ratio, wait times) must stay as quoted
    text with a page cite, never a bare numeric attribute like chlorine_ratio=0.001."""
    banned_numeric_fields = {"chlorine_ratio", "wait_time_minutes", "capacity_value",
                               "capacity_m3s"}
    for tid in TASK_IDS:
        d = graph.nodes[tid]
        assert not (banned_numeric_fields & set(d.keys())), (
            f"{tid} carries a computed-quantity field instead of quoted text")


def test_no_banned_wording_introduced_by_this_task():
    """Founder rule: if This check drafts resident-facing summary text, it must never use
    ไม่ต้อง/ห้าม/ไม่ควร/ผ่อนคลาย itself -- source quotes containing those words are fine.
    Every field in this file (label_th excepted, which is a short heading) uses either
    Thai curly quotation marks around the exact source sentence, or the explicit word
    "quoted" in a trailing note -- either marks it as the SOURCE's own wording, not text
    this check drafted."""
    import yaml
    doc = yaml.safe_load(
        (REPO_ROOT / "typology" / "nodes" / "postflood_guide_tasks_2026-09-28.yaml")
        .read_text(encoding="utf-8"))
    banned = ["ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"]
    quote_markers = ('"', "“", "”", "quoted")  # straight/curly quote marks or the word "quoted"
    for r in doc["rows"]:
        for field, value in r.items():
            if not field.endswith("_th") or field == "label_th":
                continue
            text = str(value)
            for word in banned:
                if word in text:
                    assert any(m in text for m in quote_markers), (
                        f"{r['id']}.{field}: contains banned word {word!r} without "
                        f"being marked as a quote from the source")
