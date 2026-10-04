"""
tests/test_paakklongbangtalad_intake_starved_2569.py -- ปากคลองบางตลาด INTAKE_STARVED
pattern, RELAYED-field report by ทีมลงพื้นที่ภาคประชาชน, 28 ก.ย. 2569.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.typology import build_graph, validate  # noqa: E402

NODE_FILE = REPO_ROOT / "typology" / "nodes" / "paakklongbangtalad_2026-09-28.yaml"
CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_paakklongbangtalad_intake_starved_2569.md"


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


def test_card_exists():
    assert CARD_PATH.exists()


def test_intake_starved_documented():
    text = (REPO_ROOT / "docs" / "FLOW_STALL_TYPOLOGY.md").read_text(encoding="utf-8")
    assert "INTAKE_STARVED" in text


def test_nodes_present(graph):
    for nid in ("WATER.canal_bangtalad", "WATER.bangtalad_tiwanon_bridge",
                "ST.BANGTALAD.01", "ST.BANGTALAD.RELAY.01", "SOI.BANGTALAD.SAMAKKEE",
                "RES.TOOL.MOBILE_PUMP", "RES.PUMP.BANGTALAD_MOBILE_01",
                "CIV.FIELD_OBSERVER"):
        assert graph.has_node(nid), f"expected node {nid}"


def test_pump_stall_state(graph):
    d = graph.nodes["ST.BANGTALAD.01"]
    assert d.get("stall_state") == "INTAKE_STARVED"
    assert d.get("stall_cause_confirmed") == "upstream_blockage"
    assert set(d.get("stall_cause_checklist_pending") or []) == {
        "relay_pump_failure", "gate_state", "culvert_constriction"}


def test_blockage_condition_on_bridge_reach(graph):
    d = graph.nodes["WATER.bangtalad_tiwanon_bridge"]
    assert d.get("condition") == "debris_hyacinth"


def test_flows_to_chain(graph):
    assert graph.has_edge("SOI.BANGTALAD.SAMAKKEE", "WATER.canal_bangtalad")
    assert graph.has_edge("WATER.canal_bangtalad", "WATER.bangtalad_tiwanon_bridge")
    assert graph.has_edge("WATER.bangtalad_tiwanon_bridge", "ST.BANGTALAD.01")


def test_mobile_pump_supplies_station(graph):
    d = graph.get_edge_data("RES.PUMP.BANGTALAD_MOBILE_01", "ST.BANGTALAD.01") or {}
    assert any(ed.get("kind") == "supplies" and ed.get("tag") == "RELAYED"
                for ed in d.values())


def test_field_observer_reports_to_dds_open(graph):
    d = graph.get_edge_data("CIV.FIELD_OBSERVER", "AG_DDS") or {}
    assert any(ed.get("kind") == "reports_to" and ed.get("tag") == "OPEN"
                for ed in d.values())


def test_structural_issue_row_present():
    doc = yaml.safe_load(
        (REPO_ROOT / "docs" / "knowledge" / "structural_issues_2026-09-28.yaml")
        .read_text(encoding="utf-8"))
    ids = {row["id"] for row in doc["issues"]}
    assert "ISSUE-INFRA-03" in ids


def test_no_numeric_attributes():
    doc = yaml.safe_load(NODE_FILE.read_text(encoding="utf-8"))
    for r in doc.get("rows") or []:
        for k, v in r.items():
            is_number_not_bool = isinstance(v, (int, float)) and not isinstance(v, bool)
            assert not is_number_not_bool, f"{r.get('id')} field {k!r} is a raw number: {v!r}"


def test_validate_reports_no_schema_errors(graph):
    schema_errors = []
    schema_errors += validate.rule_claim_edges_tagged(graph)
    schema_errors += validate.rule_closed_edge_vocab(graph)
    assert not schema_errors, schema_errors
