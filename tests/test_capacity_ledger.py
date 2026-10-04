"""Tests for tools/kg/build_kg.py's build-4 additions (2026-09-27): capacity_ledger.yaml
node-attribute/OUTFALL/CAPACITY_OF attach, BMA sump_well wiring, and the drainage_unit
candidate attribute. Uses small local fixtures (tests/fixtures/capacity_ledger_sample.yaml,
tests/fixtures/bma_drain_pipes_sump_wells_sample.yaml), never the real repo-wide files, and
never touches the real sqlite store or the network -- a synthetic in-memory graph is built
by hand so this test is independent of whatever is currently in data/observations.sqlite.
"""
from pathlib import Path

import networkx as nx

from tools.kg import build_kg

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_LEDGER = REPO_ROOT / "tests" / "fixtures" / "capacity_ledger_sample.yaml"
FIXTURE_SUMP_WELLS = REPO_ROOT / "tests" / "fixtures" / "bma_drain_pipes_sump_wells_sample.yaml"


def _base_graph() -> nx.MultiDiGraph:
    """A tiny graph with just enough pre-existing nodes to exercise the ATTACH-onto-
    existing-node path and the sump-well district match."""
    G = nx.MultiDiGraph()
    G.add_node("pump_station:test_fixture:1", kind="asset", **{"class": "pump_station"},
                name_th="เดิม", lat=13.7, lon=100.6,
                owner=None, source="assets_registry.py", tag="VERIFIED")
    G.add_node("district:9999", kind="district", **{"class": "district"},
                name_th="เขตทดสอบ", name_en="TestDistrict", lat=None, lon=None, tag="OPEN")
    G.add_node("basin:onwr:99", kind="asset", **{"class": "basin"}, name_th="ลุ่มน้ำทดสอบ",
                lat=None, lon=None, owner=None, tag="VERIFIED")
    return G


def test_capacity_ledger_attaches_onto_existing_node():
    G = _base_graph()
    rows = build_kg.load_capacity_ledger(FIXTURE_LEDGER)
    report = build_kg.apply_capacity_ledger(G, rows)
    assert report["rows_total"] == 4
    node = G.nodes["pump_station:test_fixture:1"]
    assert node["capacity_m3s"] == 12
    assert node["capacity_tag"] == "MEASURED"
    assert node["capacity_basis"] == "design"
    # the node's OWN pre-existing tag must never be overwritten by the ledger's tag
    assert node["tag"] == "VERIFIED"


def test_capacity_ledger_creates_new_node_for_unknown_id():
    G = _base_graph()
    rows = build_kg.load_capacity_ledger(FIXTURE_LEDGER)
    build_kg.apply_capacity_ledger(G, rows)
    assert G.has_node("led:test_fixture_reach")
    node = G.nodes["led:test_fixture_reach"]
    assert node["kind"] == "capacity_ledger_node"
    assert node["class"] == "river_reach"
    assert node["capacity_m3s"] == 500
    assert node["tag"] == "RELAYED"  # brand-new node -- ledger's own tag IS its tag
    assert node["lat"] is None and node["lon"] is None  # never geocoded


def test_capacity_ledger_outfall_and_capacity_of_edges():
    G = _base_graph()
    rows = build_kg.load_capacity_ledger(FIXTURE_LEDGER)
    report = build_kg.apply_capacity_ledger(G, rows)
    assert report["outfall_edges"] == 1
    assert report["capacity_of_edges"] == 1
    # OUTFALL: the tunnel (a pump/tunnel/gate-kind row) -> the outfall row it discharges into
    assert G.has_edge("led:test_fixture_tunnel", "outfall:test_fixture")
    edge = G.get_edge_data("led:test_fixture_tunnel", "outfall:test_fixture")
    assert any(d["kind"] == "OUTFALL" for d in edge.values())
    # CAPACITY_OF: the outfall row -> the river_reach row it names in its own source text
    assert G.has_edge("outfall:test_fixture", "led:test_fixture_reach")
    edge2 = G.get_edge_data("outfall:test_fixture", "led:test_fixture_reach")
    assert any(d["kind"] == "CAPACITY_OF" for d in edge2.values())


def test_sump_wells_loaded_with_real_coords_and_matched_district_edge():
    G = _base_graph()
    sump_nodes = build_kg.load_sump_wells(FIXTURE_SUMP_WELLS)
    assert len(sump_nodes) == 2
    for nid, attrs in sump_nodes:
        G.add_node(nid, **attrs)
    matched = G.nodes["sumpwell:fixture_sump_matched"]
    assert matched["lat"] == 13.7 and matched["lon"] == 100.6  # real coords, never null
    edges = build_kg.build_sump_well_district_edges(G, sump_nodes)
    assert len(edges) == 1
    u, v, attrs = edges[0]
    assert u == "sumpwell:fixture_sump_matched"
    assert v == "district:9999"
    assert attrs["kind"] == "IN_DISTRICT"
    # the unmatched district_en must NOT silently fuzzy-match anything
    matched_sources = {e[0] for e in edges}
    assert "sumpwell:fixture_sump_unmatched" not in matched_sources


def test_drainage_unit_candidate_tags_basin_and_district_only():
    G = _base_graph()
    G.add_node("riverreach:not_a_unit", kind="river_reach", **{"class": "river_reach"},
                lat=None, lon=None, tag="RELAYED")
    count = build_kg.apply_drainage_unit_candidate(G)
    assert count == 2  # the one basin node + the one district node in _base_graph()
    assert G.nodes["basin:onwr:99"]["drainage_unit"] == "candidate"
    assert G.nodes["district:9999"]["drainage_unit"] == "candidate"
    assert "drainage_unit" not in G.nodes["riverreach:not_a_unit"]
