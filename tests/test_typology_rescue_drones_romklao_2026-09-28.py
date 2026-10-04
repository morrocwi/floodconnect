"""
tests/test_typology_rescue_drones_romklao_2026-09-28.py -- rescue/survey drones at
เคหะชุมชนร่มเกล้า, กระทรวง อว. (MHESI) FB post 28 ก.ย. 2569 (RELAYED). Access-first case:
boat mode blocked by obstacles/fences -> air/drone mode. Network structure only, no
officials' personal names, no numbers in the typology layer.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import community_dag  # noqa: E402
from tools.typology import build_graph, validate  # noqa: E402

NODE_FILE = REPO_ROOT / "typology" / "nodes" / "mhesi_rescue_drones_romklao_2026-09-28.yaml"
CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_tool_rescue_drones_romklao_2569.md"


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


def test_new_agency_and_ministry_nodes_present(graph):
    for nid in ("AG_MHESI", "AG_MSDHS", "AG_KMUTNB", "AG_SOP", "AG_SYSTRONICS",
                "AG_RESCUE_ROMSAI", "MINISTRY.MHESI", "MINISTRY.SOCIAL"):
        assert graph.has_node(nid), f"expected node {nid}"


def test_ag_mhesi_msdhs_reused_ids_match_water_system_dag_mmd():
    """AG_MHESI/AG_MSDHS must be the SAME id strings water_system_dag.mmd already
    declares -- no renamed twin."""
    mmd_text = (REPO_ROOT / "docs" / "knowledge" / "water_system_dag.mmd").read_text(
        encoding="utf-8")
    assert "AG_MHESI[" in mmd_text
    assert "AG_MSDHS[" in mmd_text


def test_drone_tool_and_kitchen_resource_nodes(graph):
    for nid in ("RES.TOOL.RESCUE_DRONE", "RES.DRONE.ROMKLAO_20260928",
                "RES.KITCHEN.MSDHS_CENTRAL"):
        assert graph.has_node(nid), f"expected node {nid}"
    tool = graph.nodes["RES.TOOL.RESCUE_DRONE"]
    assert tool.get("mode") == "air_drone"
    assert set(tool.get("drone_subtypes") or []) == {"isr_survey", "heavy_lift_transport"}
    instance = graph.nodes["RES.DRONE.ROMKLAO_20260928"]
    assert instance.get("generic_tool_ref") == "RES.TOOL.RESCUE_DRONE"
    assert graph.nodes["RES.KITCHEN.MSDHS_CENTRAL"].get("owner_agency") == "AG_MSDHS"


def test_part_of_edges_to_new_ministries_and_to_gov_root(graph):
    for src, dst in (("AG_MHESI", "MINISTRY.MHESI"), ("AG_KMUTNB", "MINISTRY.MHESI"),
                       ("AG_MSDHS", "MINISTRY.SOCIAL")):
        assert graph.has_edge(src, dst)
        d = graph.get_edge_data(src, dst)
        assert any(ed.get("kind") == "part_of" and ed.get("tag") == "RELAYED"
                    for ed in d.values())
    import networkx as nx
    part_of_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("kind") == "part_of"]
    PG = nx.DiGraph()
    PG.add_edges_from(part_of_edges)
    for m in ("MINISTRY.MHESI", "MINISTRY.SOCIAL"):
        assert nx.has_path(PG, m, "GOV.TH"), f"{m} does not reach GOV.TH via part_of"


def test_operates_and_reports_to_edges(graph):
    for src, dst in (("AG_SYSTRONICS", "RES.DRONE.ROMKLAO_20260928"),
                       ("AG_SOP", "RES.DRONE.ROMKLAO_20260928"),
                       ("AG_MSDHS", "RES.KITCHEN.MSDHS_CENTRAL")):
        d = graph.get_edge_data(src, dst) or {}
        assert any(ed.get("kind") == "operates" and ed.get("tag") == "RELAYED"
                    for ed in d.values()), f"expected operates {src} -> {dst}"
    for src, dst in (("AG_SYSTRONICS", "AG_MHESI"), ("AG_SOP", "AG_MHESI"),
                       ("AG_RESCUE_ROMSAI", "AG_MSDHS")):
        d = graph.get_edge_data(src, dst) or {}
        assert any(ed.get("kind") == "reports_to" and ed.get("tag") == "RELAYED"
                    for ed in d.values()), f"expected reports_to {src} -> {dst}"


def test_supplies_edges_to_romklao_zone(graph):
    assert graph.has_node("romklao_zone")
    for src in ("RES.DRONE.ROMKLAO_20260928", "RES.KITCHEN.MSDHS_CENTRAL"):
        d = graph.get_edge_data(src, "romklao_zone") or {}
        assert any(ed.get("kind") == "supplies" and ed.get("tag") == "RELAYED"
                    for ed in d.values()), f"expected supplies {src} -> romklao_zone"


def test_romklao_support_nodes_status_unknown_not_field_verified(graph):
    for nid in ("romklao_ops_kitchen_ram192", "romklao_base_romklao2",
                "romklao_kitchen_relocation_watpakbueng", "romklao_vehicle_standby_4wd"):
        assert graph.has_node(nid)
        d = graph.nodes[nid]
        assert d.get("status") == "UNKNOWN"
        assert d.get("fresh") is False
        assert d.get("self_help_kind") == "support"


def test_romklao_zone_to_support_edges_are_open_not_field_verified(graph):
    for target in ("romklao_ops_kitchen_ram192", "romklao_base_romklao2",
                   "romklao_kitchen_relocation_watpakbueng", "romklao_vehicle_standby_4wd"):
        d = graph.get_edge_data("romklao_zone", target) or {}
        found = [ed for ed in d.values() if ed.get("kind") == "escalates_to"]
        assert found, f"expected escalates_to romklao_zone -> {target}"
        assert found[0].get("tag") == "OPEN", "not field-verified -- must stay OPEN"


def test_romklao_zone_drone_resource_entry():
    doc = yaml.safe_load(build_graph.SELF_HELP_DAG_PATH.read_text(encoding="utf-8"))
    zone = doc["nodes"]["romklao_zone"]
    drone_rows = [r for r in (zone.get("resources") or []) if r.get("type") == "drone"]
    assert drone_rows
    row = drone_rows[0]
    assert row["ref"] == "RES.TOOL.RESCUE_DRONE"
    for k, v in row.items():
        if k.startswith("condition_"):
            assert isinstance(v, bool)


def test_air_drone_mode_added_and_documented_delivery_only():
    assert "air_drone" in community_dag.EDGE_MODES
    src = Path(community_dag.__file__).read_text(encoding="utf-8")
    assert "MOVING PEOPLE" in src or "ย้ายคน" in src


def test_no_air_drone_mode_used_on_any_evacuation_layer_edge():
    """air_drone must never appear on an edge whose destination is internal_safe/
    egress/external_safe (a people-routing edge) -- delivery/survey only."""
    doc = yaml.safe_load(build_graph.SELF_HELP_DAG_PATH.read_text(encoding="utf-8"))
    nodes = doc["nodes"]
    people_routing_kinds = {"internal_safe", "egress", "external_safe"}
    for e in doc.get("edges") or []:
        v = e.get("to")
        if v in nodes and nodes[v].get("kind") in people_routing_kinds:
            assert "air_drone" not in (e.get("modes") or []), \
                f"edge {e.get('id')} routes people via air_drone -- forbidden"


def test_no_personal_names_in_new_files():
    text = NODE_FILE.read_text(encoding="utf-8")
    for prefix in ("นาย ", "นางสาว", "นาง "):
        assert prefix not in text
    # organisation names (company/association/foundation) are expected and allowed
    assert "บริษัท ซิสทรอนิกส์ จำกัด" in text
    assert "สมาคมอุตสาหกรรมเพื่อการป้องกันประเทศ" in text
    assert "มูลนิธิกู้ภัยร่มไทร" in text


def test_no_numeric_attributes_in_typology_layer():
    doc = yaml.safe_load(NODE_FILE.read_text(encoding="utf-8"))
    for r in doc.get("rows") or []:
        for k, v in r.items():
            is_number_not_bool = isinstance(v, (int, float)) and not isinstance(v, bool)
            assert not is_number_not_bool, \
                f"{NODE_FILE.name} row {r.get('id')} field {k!r} is a raw number: {v!r}"


def test_validate_reports_no_schema_errors(graph):
    schema_errors = []
    schema_errors += validate.rule_claim_edges_tagged(graph)
    schema_errors += validate.rule_closed_edge_vocab(graph)
    schema_errors += validate.rule_part_of_target_kind(graph)
    assert not schema_errors, schema_errors
