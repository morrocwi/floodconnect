"""
tests/test_typology_selfhelp_bridge_2026-09-28.py -- the imported Community Self-Help
DAG (public/main 5364c23) wired into the SAME typology graph as a `self_help` layer,
bridged to power/resource via the existing reports_to/supplies edge kinds. Real repo
data only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.typology import build_graph, validate  # noqa: E402


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


def test_self_help_nodes_present_with_original_ids(graph):
    for nid in ("sammakorn_household_template", "sammakorn_buddy_cell", "sammakorn_zone",
                "sammakorn_internal_safe", "sammakorn_egress", "ram53_zone",
                "external_safe_bkk_east_01", "external_safe_bkk_east_02"):
        assert graph.has_node(nid), f"expected self-help DAG node {nid!r} (original id, no CIV.* rename)"
        assert graph.nodes[nid]["layer"] == "self_help"


def test_escalates_to_edges_present_and_open(graph):
    assert graph.has_edge("sammakorn_household_template", "sammakorn_buddy_cell")
    assert graph.has_edge("sammakorn_zone", "sammakorn_internal_safe")
    d = graph.get_edge_data("sammakorn_zone", "sammakorn_internal_safe")
    escalates = [ed for ed in d.values() if ed.get("kind") == "escalates_to"]
    assert escalates and escalates[0]["tag"] == "OPEN"


def test_bridge_edges_reuse_existing_vocabulary(graph):
    assert graph.has_edge("sammakorn_zone", "AG_ESTATE")
    assert graph.has_edge("AG_ESTATE", "AG_DDS")
    assert graph.has_edge("sammakorn_zone", "AG_BMA_GOV")
    assert graph.has_edge("sammakorn_zone", "AG_MEA")
    assert graph.has_edge("sammakorn_internal_safe", "sammakorn_zone")
    for u, v in (("sammakorn_zone", "AG_ESTATE"), ("AG_ESTATE", "AG_DDS"),
                 ("sammakorn_zone", "AG_BMA_GOV"), ("sammakorn_zone", "AG_MEA")):
        d = graph.get_edge_data(u, v)
        assert all(ed.get("kind") == "reports_to" for ed in d.values())
    d = graph.get_edge_data("sammakorn_internal_safe", "sammakorn_zone")
    assert all(ed.get("kind") == "supplies" for ed in d.values())


def test_bridge_does_not_conflate_mea_warns_with_zone_report(graph):
    """sammakorn_zone -> AG_MEA (reports_to, outage report inward) must stay distinct
    from the existing AG_MEA -> OPEN (warns, MEA warning outward) edge."""
    mea_warns = [(u, v, d) for u, v, d in graph.edges(data=True)
                 if d.get("kind") == "warns" and u == "AG_MEA"]
    assert mea_warns, "expected the pre-existing AG_MEA warns edge to still be present"
    mea_reports = [(u, v, d) for u, v, d in graph.edges(data=True)
                   if d.get("kind") == "reports_to" and v == "AG_MEA"]
    assert mea_reports, "expected the new sammakorn_zone -> AG_MEA reports_to bridge edge"
    assert {v for _, v, _ in mea_warns} != {u for u, _, _ in mea_reports}


def test_only_one_zone_for_sammakorn_no_invented_per_soi_zones(graph):
    zone_nodes = [n for n, d in graph.nodes(data=True)
                  if d.get("self_help_kind") == "zone" and str(n).startswith("sammakorn")]
    assert zone_nodes == ["sammakorn_zone"]


def test_internal_safe_and_egress_remain_unknown_status(graph):
    assert graph.nodes["sammakorn_internal_safe"].get("status") == "UNKNOWN"
    assert graph.nodes["sammakorn_egress"].get("status") == "UNKNOWN"


def test_validate_no_schema_errors_with_self_help_layer(graph):
    report_bad = validate.rule_closed_edge_vocab(graph)
    assert not report_bad, f"unexpected edge kind(s) outside closed vocabulary: {report_bad}"
