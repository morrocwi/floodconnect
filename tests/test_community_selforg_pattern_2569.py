"""
tests/test_community_selforg_pattern_2569.py -- community self-organisation pattern
(แฟลตคลองจั่น + ร่มเกล้า), RELAYED FB post by a university academic, 28 ก.ย. 2569.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import community_dag as cd  # noqa: E402
from tools.typology import build_graph, validate  # noqa: E402

NODE_FILE = REPO_ROOT / "typology" / "nodes" / "community_selforg_pattern_2026-09-28.yaml"
CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_community_selforg_pattern_2569.md"


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


def test_community_roles_vocab():
    assert cd.COMMUNITY_ROLES == {"coordinator", "welfare", "route_checker",
                                   "resource_keeper", "comms", "procurement_runner"}


def test_roles_active_validated():
    doc = {
        "nodes": {"z": {"kind": "zone", "layer": 2, "status": "UNKNOWN", "fresh": False,
                          "roles_active": ["coordinator", "procurement_runner"]}},
        "edges": [],
    }
    check = cd.validate_document(doc)
    assert check["valid"], check["errors"]

    bad = {
        "nodes": {"z": {"kind": "zone", "layer": 2, "status": "UNKNOWN", "fresh": False,
                          "roles_active": ["chief_executive"]}},
        "edges": [],
    }
    check2 = cd.validate_document(bad)
    assert not check2["valid"]
    assert any("roles_active" in e or "role(s)" in e for e in check2["errors"])


def test_typology_nodes_present(graph):
    for nid in ("RES.TOOL.SHARED_POOL", "CIV.ZONE.KHLONGCHAN_FLATS", "CIV.ZONE.ROMKLAO"):
        assert graph.has_node(nid), f"expected node {nid}"
    for nid in ("CIV.ZONE.KHLONGCHAN_FLATS", "CIV.ZONE.ROMKLAO"):
        d = graph.nodes[nid]
        assert d.get("kind") == "soi_surface"
        assert d.get("layer") == "civil"


def test_civ_zone_romklao_refs_existing_self_help_node_not_a_duplicate(graph):
    d = graph.nodes["CIV.ZONE.ROMKLAO"]
    assert d.get("self_help_dag_ref") == "romklao_zone"
    assert graph.has_node("romklao_zone")


def test_supplies_edges_pattern_to_both_zones(graph):
    for target in ("CIV.ZONE.KHLONGCHAN_FLATS", "CIV.ZONE.ROMKLAO"):
        d = graph.get_edge_data("RES.TOOL.SHARED_POOL", target) or {}
        assert any(ed.get("kind") == "supplies" and ed.get("tag") == "RELAYED"
                    for ed in d.values()), f"expected supplies -> {target}"


def test_khlongchan_flats_zone_and_kitchen_in_self_help_dag():
    doc = yaml.safe_load(build_graph.SELF_HELP_DAG_PATH.read_text(encoding="utf-8"))
    nodes = doc["nodes"]
    assert "khlongchan_flats_zone" in nodes
    assert "khlongchan_flats_kitchen" in nodes
    assert nodes["khlongchan_flats_kitchen"]["kind"] == "support"
    assert "kitchen" in nodes["khlongchan_flats_kitchen"]["services"]
    zone = nodes["khlongchan_flats_zone"]
    pools = [r for r in (zone.get("resources") or []) if r.get("type") == "shared_pool"]
    assert pools and pools[0]["ref"] == "RES.TOOL.SHARED_POOL"
    assert set(zone.get("roles_active") or []) == cd.COMMUNITY_ROLES


def test_romklao_zone_linked_to_shared_pool_pattern_too():
    doc = yaml.safe_load(build_graph.SELF_HELP_DAG_PATH.read_text(encoding="utf-8"))
    zone = doc["nodes"]["romklao_zone"]
    pools = [r for r in (zone.get("resources") or []) if r.get("type") == "shared_pool"]
    assert pools


def test_no_numeric_attributes_in_typology_layer():
    doc = yaml.safe_load(NODE_FILE.read_text(encoding="utf-8"))
    for r in doc.get("rows") or []:
        for k, v in r.items():
            is_number_not_bool = isinstance(v, (int, float)) and not isinstance(v, bool)
            assert not is_number_not_bool, f"{r.get('id')} field {k!r} is a raw number: {v!r}"


def test_procurement_runner_documented():
    text = (REPO_ROOT / "docs" / "COMMUNITY_SELF_HELP_DAG.md").read_text(encoding="utf-8")
    assert "procurement runner" in text or "procurement_runner" in text
    for word in ("ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        section_start = text.find("ตั้งชุมชนเมื่อฉุกเฉิน")
        assert section_start != -1
        section_end = text.find("\n---", section_start)
        section = text[section_start:section_end if section_end != -1 else None]
        assert word not in section


def test_validate_reports_no_schema_errors(graph):
    schema_errors = []
    schema_errors += validate.rule_claim_edges_tagged(graph)
    schema_errors += validate.rule_closed_edge_vocab(graph)
    assert not schema_errors, schema_errors
