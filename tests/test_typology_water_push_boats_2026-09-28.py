"""
tests/test_typology_water_push_boats_2026-09-28.py -- "เรือผลักดันน้ำ" (water-pushing
boats) typology addition (docs/knowledge/card_tool_water_push_boats.md). Founder rule:
network structure only, no numbers in the typology layer (numbers live in the card only),
and no private individual's name anywhere in the typology/edges rows.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.typology import build_graph, validate  # noqa: E402

CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_tool_water_push_boats.md"
NODE_FILE = REPO_ROOT / "typology" / "nodes" / "tool_water_push_boats_2026-09-28.yaml"

NEW_TOOL_NODE_IDS = ("RES.TOOL.WATER_PUSH_BOAT", "RES.TOOL.AXIAL_WATER_PUSHER",
                     "AG_OPERATOR_SAENSAEB_BOAT")
INSTANCE_NODE_ID = "RES.BOAT_PUSH.AG_UNKNOWN.01"

# Numeric fields this check's own instructions forbid anywhere in the typology layer
# (boat count, hp, rpm, cm drop, Navy counts/flows -- card-only).
BANNED_NUMERIC_FIELDS = {"quantity", "boat_count", "hp", "horsepower", "rpm",
                          "level_drop_cm", "level_drop_m", "navy_boat_count",
                          "flow_rate", "capacity_m3s", "distance_km", "distance_m"}

# No private individual's name may appear -- this repo's own convention for an unnamed
# operator ("ผู้ประกอบการ...", never a personal name). We can't enumerate every possible
# name, so this test checks the specific strings this check named as forbidden if they
# were ever pasted in verbatim by mistake (company name/person name placeholders never
# used in this build to begin with -- a defence-in-depth check, not proof of absence).
# "นาย " (trailing space) to avoid false positives on "นายกฯ"/"นายกรัฐมนตรี" (role title)
FORBIDDEN_SUBSTRINGS_TH = ["นาย ", "นางสาว", "นาง "]  # common Thai personal-name prefixes


@pytest.fixture(scope="module")
def graph():
    import networkx as nx
    G = nx.MultiDiGraph()
    build_graph.build_water_layer(G)
    build_graph.load_registry_nodes(G)
    build_graph.apply_node_overlays(G)
    build_graph.load_registry_edges(G)
    return G


def test_card_exists_and_cites_all_sources():
    assert CARD_PATH.exists()
    text = CARD_PATH.read_text(encoding="utf-8")
    for url in (
        "https://www.thebangkokinsight.com/news/politics-general/general/1701479/",
        "https://mgronline.com/business/detail/9690000094733",
        "https://www.bangkokbiznews.com/news/1207987",
        "https://mgronline.com/onlinesection/detail/9600000108261",
        "https://mgronline.com/daily/detail/9540000135295",
    ):
        assert url in text, f"card missing citation URL {url}"


def test_card_registered_via_kb_reindex():
    """kb.py reindex must pick up the new card (docs/**/*.md walk) without raising, and
    the card's own path/backtick reference must resolve into INDEX.yaml after it runs.

    This runs `kb.py reindex` as a subprocess, which writes the real, git-tracked
    docs/knowledge/INDEX.yaml -- snapshot its bytes (or absence) first and restore them
    afterward so this test never leaves the tracked file dirty."""
    import subprocess
    index_path = REPO_ROOT / "docs" / "knowledge" / "INDEX.yaml"
    before = index_path.read_bytes() if index_path.exists() else None
    try:
        result = subprocess.run([sys.executable, str(REPO_ROOT / "kb.py"), "reindex"],
                                  cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert index_path.exists()
        index_text = index_path.read_text(encoding="utf-8")
        assert "card_tool_water_push_boats.md" in index_text
    finally:
        if before is None:
            if index_path.exists():
                index_path.unlink()
        else:
            index_path.write_bytes(before)


def test_new_tool_and_operator_nodes_present(graph):
    for nid in NEW_TOOL_NODE_IDS:
        assert graph.has_node(nid), f"expected node {nid}"
    assert graph.has_node(INSTANCE_NODE_ID)


def test_generic_boat_tool_node_attrs(graph):
    d = graph.nodes["RES.TOOL.WATER_PUSH_BOAT"]
    assert d.get("kind") == "resource"
    assert d.get("tool_class") == "water_push_boat"
    assert d.get("mode") == "boat"
    assert d.get("tag") in ("RELAYED", "RELAYED-reconciled")


def test_axial_water_pusher_is_orphan_and_open(graph):
    assert graph.degree("RES.TOOL.AXIAL_WATER_PUSHER") == 0
    assert graph.nodes["RES.TOOL.AXIAL_WATER_PUSHER"].get("tag") == "OPEN"


def test_operator_node_is_civil_agency(graph):
    d = graph.nodes["AG_OPERATOR_SAENSAEB_BOAT"]
    assert d.get("kind") == "agency"
    assert d.get("layer") == "civil"
    assert d.get("agency_class") == "commercial_operator"


def test_instance_node_updated_with_tool_class_and_effectiveness_open(graph):
    d = graph.nodes[INSTANCE_NODE_ID]
    assert d.get("tool_class") == "water_push_boat"
    assert d.get("generic_tool_ref") == "RES.TOOL.WATER_PUSH_BOAT"
    assert d.get("effectiveness") == "OPEN"
    assert d.get("owner_agency") == "AG_OPERATOR_SAENSAEB_BOAT"


def test_supplies_edge_to_rama9_tunnel_intake(graph):
    assert graph.has_edge(INSTANCE_NODE_ID, "tunnel:bma_dds:saensaeb_ladprao")
    edges = graph.get_edge_data(INSTANCE_NODE_ID, "tunnel:bma_dds:saensaeb_ladprao")
    found = [ed for ed in edges.values() if ed.get("kind") == "supplies" and ed.get("tag") == "RELAYED"]
    assert found, "expected a RELAYED supplies edge to the Rama 9 tunnel intake"


def test_operates_edge_operator_to_instance(graph):
    assert graph.has_edge("AG_OPERATOR_SAENSAEB_BOAT", INSTANCE_NODE_ID)
    edges = graph.get_edge_data("AG_OPERATOR_SAENSAEB_BOAT", INSTANCE_NODE_ID)
    found = [ed for ed in edges.values() if ed.get("kind") == "operates" and ed.get("tag") == "RELAYED"]
    assert found


def test_reports_to_bma_relayed_and_dds_open(graph):
    bma_edges = graph.get_edge_data("AG_OPERATOR_SAENSAEB_BOAT", "AG_BMA_GOV") or {}
    found_bma = [ed for ed in bma_edges.values() if ed.get("kind") == "reports_to"]
    assert found_bma and found_bma[0].get("tag") == "RELAYED"

    dds_edges = graph.get_edge_data("AG_OPERATOR_SAENSAEB_BOAT", "AG_DDS") or {}
    found_dds = [ed for ed in dds_edges.values() if ed.get("kind") == "reports_to"]
    assert found_dds and found_dds[0].get("tag") == "OPEN"


def test_no_numeric_attributes_in_typology_layer():
    """Founder rule: numbers (boat count, hp, rpm, cm drop, Navy counts/flows) may only
    appear as quoted text inside the knowledge card -- never as a typology node/edge
    attribute."""
    doc = yaml.safe_load(NODE_FILE.read_text(encoding="utf-8"))
    for r in doc.get("rows") or []:
        assert not (BANNED_NUMERIC_FIELDS & set(r.keys())), \
            f"{NODE_FILE.name} row {r.get('id')} carries a banned numeric field"
        for k, v in r.items():
            is_number_not_bool = isinstance(v, (int, float)) and not isinstance(v, bool)
            assert not is_number_not_bool, \
                f"{NODE_FILE.name} row {r.get('id')} field {k!r} is a raw number: {v!r}"

    resources_doc = yaml.safe_load(
        (REPO_ROOT / "typology" / "nodes" / "resources.yaml").read_text(encoding="utf-8"))
    boat_row = next(r for r in resources_doc["rows"] if r["id"] == INSTANCE_NODE_ID)
    for k, v in boat_row.items():
        if isinstance(v, bool):
            continue
        if v is None:
            continue
        assert not isinstance(v, (int, float)), \
            f"resources.yaml row {INSTANCE_NODE_ID} field {k!r} is a raw number: {v!r}"


def test_no_private_individual_name_strings():
    text = NODE_FILE.read_text(encoding="utf-8")
    text += (REPO_ROOT / "typology" / "nodes" / "resources.yaml").read_text(encoding="utf-8")
    text += (REPO_ROOT / "typology" / "edges" / "supplies.yaml").read_text(encoding="utf-8")
    text += (REPO_ROOT / "typology" / "edges" / "operates.yaml").read_text(encoding="utf-8")
    text += (REPO_ROOT / "typology" / "edges" / "reports_to.yaml").read_text(encoding="utf-8")
    for prefix in FORBIDDEN_SUBSTRINGS_TH:
        assert prefix not in text, f"forbidden personal-name-prefix {prefix!r} found"
    # generic role label only, never a company name (this check's own privacy rule)
    assert "ผู้ประกอบการเรือโดยสารคลองแสนแสบ" in \
        (REPO_ROOT / "typology" / "nodes" / "tool_water_push_boats_2026-09-28.yaml").read_text(encoding="utf-8")


def test_self_help_dag_zone_resource_entry():
    doc = build_graph.SELF_HELP_DAG_PATH
    text = doc.read_text(encoding="utf-8")
    assert "RES.TOOL.WATER_PUSH_BOAT" in text
    parsed = yaml.safe_load(text)
    zone = parsed["nodes"]["sammakorn_zone"]
    resources = zone.get("resources") or []
    boat_rows = [r for r in resources if r.get("type") == "boat"]
    assert boat_rows, "expected a boat resource entry on sammakorn_zone"
    row = boat_rows[0]
    assert row["ref"] == "RES.TOOL.WATER_PUSH_BOAT"
    for cond_key in ("condition_coordination_with_agency_required",
                     "condition_bridge_clearance_check", "condition_crew_rotation_check"):
        assert cond_key in row
        assert isinstance(row[cond_key], bool)


def test_validate_reports_no_schema_errors(graph):
    schema_errors = []
    schema_errors += validate.rule_claim_edges_tagged(graph)
    schema_errors += validate.rule_closed_edge_vocab(graph)
    assert not schema_errors, schema_errors
