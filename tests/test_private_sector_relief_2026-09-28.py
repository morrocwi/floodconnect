"""
tests/test_private_sector_relief_2026-09-28.py -- private-sector relief network,
RELAYED text pasted by founder from THE STANDARD WEALTH 28.09.2026.
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

NODE_FILE = REPO_ROOT / "typology" / "nodes" / "private_sector_relief_2026-09-28.yaml"
CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_private_sector_relief_2026-09-28.md"

PHONE_RE = re.compile(r"0[\s-]?\d{1,2}[\s-]?\d{3}[\s-]?\d{4}")
ACCOUNT_RE = re.compile(r"\b\d{3}-\d-\d{5}-\d\b")


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


def test_actor_type_private_sector_present(graph):
    private_actors = [n for n, d in graph.nodes(data=True)
                       if d.get("actor_type") == "private_sector"]
    expected = {"AG_TELCO_AIS", "AG_TELCO_TRUE", "AG_LINEMAN", "AG_CENTRALPATTANA",
                "AG_ROBINSON", "AG_WHOLESALE_SUPPLIER", "AG_SANSIRI", "AG_SENA",
                "AG_RESTAURANT_NETWORK"}
    assert expected.issubset(set(private_actors))


def test_reused_ids_registered_first_time(graph):
    for nid in ("AG_DIST_NEIGH", "AG_KMITL", "AS_SHELTER_KMITL", "AS_SHELTER_SCHOOL",
                "AS_SANDBAGS"):
        assert graph.has_node(nid), f"expected reused id {nid}"


def test_vehicle_refuge_parking_resource(graph):
    assert graph.has_node("RES.TOOL.VEHICLE_REFUGE_PARKING")
    assert graph.nodes["RES.TOOL.VEHICLE_REFUGE_PARKING"]["resource_type"] == "vehicle_refuge_parking"
    d = graph.nodes["RES.PARKING.CENTRALPATTANA_01"]
    assert d["resource_type"] == "vehicle_refuge_parking"
    assert d["owner_agency"] == "AG_CENTRALPATTANA"


def test_power_dependency_attribute_not_new_edge_kind(graph):
    assert graph.nodes["RES.TOOL.COW"].get("power_dependency") is True
    assert graph.nodes["RES.COW.SHELTER_KMITL_01"].get("power_dependency") is True


def test_telco_operates_cow_and_reports_to_regulator(graph):
    for telco in ("AG_TELCO_AIS", "AG_TELCO_TRUE"):
        d = graph.get_edge_data(telco, "RES.COW.SHELTER_KMITL_01") or {}
        assert any(ed.get("kind") == "operates" and ed.get("tag") == "RELAYED"
                    for ed in d.values()), f"expected operates {telco} -> COW"
        rd = graph.get_edge_data(telco, "AG_NBTC") or {}
        assert any(ed.get("kind") == "reports_to" for ed in rd.values())


def test_lineman_warns_edge(graph):
    d = graph.get_edge_data("AG_LINEMAN", "WCH.LINEMAN_INAPP_RISK") or {}
    found = [ed for ed in d.values() if ed.get("kind") == "warns"]
    assert found
    assert found[0].get("instruction")  # non-empty, satisfies validate.py


def test_military_escort_edge_role_attribute(graph):
    d = graph.get_edge_data("AG_RTA", "RES.RELIEF_DELIVERY.PRIVATE_KHLONGCHAN_01") or {}
    found = [ed for ed in d.values() if ed.get("kind") == "operates"]
    assert found
    assert found[0].get("edge_role") == "access_escort"


def test_relief_delivery_supplies_existing_khlongchan_zone(graph):
    assert graph.has_edge("RES.RELIEF_DELIVERY.PRIVATE_KHLONGCHAN_01", "CIV.ZONE.KHLONGCHAN_FLATS")


def test_wholesale_to_village_head_to_kitchen_chain(graph):
    assert graph.has_edge("AG_WHOLESALE_SUPPLIER", "AG_ESTATE")
    assert graph.has_edge("AG_ESTATE", "khlongchan_flats_kitchen")


def test_mobile_pump_reused_not_duplicated(graph):
    """AG_SENA operates the EXISTING RES.TOOL.MOBILE_PUMP (from an earlier commit) --
    no duplicate mobile-pump tool node created for this check."""
    assert graph.has_edge("AG_SENA", "RES.TOOL.MOBILE_PUMP")
    mobile_pump_like = [n for n in graph.nodes if "MOBILE_PUMP" in n and n.startswith("RES.TOOL")]
    assert mobile_pump_like == ["RES.TOOL.MOBILE_PUMP"]


def test_no_numeric_attributes_in_typology_layer():
    doc = yaml.safe_load(NODE_FILE.read_text(encoding="utf-8"))
    for r in doc.get("rows") or []:
        for k, v in r.items():
            is_number_not_bool = isinstance(v, (int, float)) and not isinstance(v, bool)
            assert not is_number_not_bool, f"{r.get('id')} field {k!r} is a raw number: {v!r}"


def test_no_personal_names_or_call_centre_numbers():
    text = NODE_FILE.read_text(encoding="utf-8") + CARD_PATH.read_text(encoding="utf-8")
    for prefix in ("นาย ", "นางสาว", "นาง "):
        assert prefix not in text
    assert not PHONE_RE.search(text), "a phone-number-shaped string was found"
    assert not ACCOUNT_RE.search(text), "a bank-account-shaped string was found"


def test_validate_reports_no_schema_errors(graph):
    schema_errors = []
    schema_errors += validate.rule_claim_edges_tagged(graph)
    schema_errors += validate.rule_closed_edge_vocab(graph)
    assert not schema_errors, schema_errors
