"""
tests/test_typology_environman_2026-09-28.py -- Environman FB post 28 ก.ย. 2569
(RELAYED), network structure only (no capacity/length/rain/level numbers, per founder
correction 2026-09-28), plus the follow-up completeness pass (orphans/owned_by closed
with sources already in the repo). Real repo data only.
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
    build_graph.load_registry_edges(G)
    return G


def test_confluence_node_and_flows_to(graph):
    assert graph.has_node("WATER.canal_ladprao")
    assert graph.has_node("WL.CONFLUENCE.LPR_SSB.01")
    assert graph.has_edge("WATER.canal_ladprao", "WL.CONFLUENCE.LPR_SSB.01")
    assert graph.has_edge("WL.CONFLUENCE.LPR_SSB.01", "WL.SSB.04")


def test_existing_ssb07_ssb04_edge_untouched(graph):
    """The confluence must be an ADDITIONAL inflow, never a replacement of the existing
    declared east_chain.yaml edge -- independent-review discipline from earlier commits."""
    assert graph.has_edge("WL.SSB.07", "WL.SSB.04")


def test_tunnel_and_pump_chain_reuses_capacity_ledger_ids(graph):
    for nid in ("tunnel:bma_dds:saensaeb_ladprao", "pump_station:water_station:1",
                "pump_station:water_station:2", "tunnel:bma_dds:nongbon"):
        assert graph.has_node(nid), f"expected reused capacity_ledger id {nid}"
    assert graph.has_edge("WL.SSB.04", "tunnel:bma_dds:saensaeb_ladprao")
    assert graph.has_edge("tunnel:bma_dds:saensaeb_ladprao", "pump_station:water_station:2")
    assert graph.has_edge("pump_station:water_station:2", "river:chao_phraya")
    assert graph.has_edge("WL.NBN.01", "tunnel:bma_dds:nongbon")
    assert graph.has_edge("tunnel:bma_dds:nongbon", "river:chao_phraya")


def test_no_numeric_capacity_or_length_fields_imported(graph):
    """Founder correction 2026-09-28: 'ไม่ต้องเอาตัวเลข สกัดแค่เครือข่าย node' -- no
    capacity_m3s/route_length_km-style numeric field anywhere in the new registry files."""
    import yaml
    banned_fields = {"capacity_m3s", "capacity_value", "route_length_km",
                      "route_length_km_gt", "rain_mm", "level_m"}
    for fname in ("environman_extension_2026-09-28.yaml", "environman_overlay_2026-09-28.yaml",
                  "completeness_pass_2026-09-28.yaml"):
        doc = yaml.safe_load((REPO_ROOT / "typology" / "nodes" / fname).read_text(encoding="utf-8"))
        for r in doc.get("rows") or []:
            assert not (banned_fields & set(r.keys())), f"{fname} row {r.get('id')} carries a banned numeric field"
    for fname in ("flows_to_environman_2026-09-28.yaml", "flows_to_completeness_2026-09-28.yaml"):
        doc = yaml.safe_load((REPO_ROOT / "typology" / "edges" / fname).read_text(encoding="utf-8"))
        for r in doc.get("rows") or []:
            assert not (banned_fields & set(r.keys())), f"{fname} row carries a banned numeric field"


def test_drains_after_attribute_on_tributary_edges(graph):
    for u, v in (("WATER.ram53_canal", "WL.SSB.07"), ("WL.KJN.01", "WL.SSB.07"),
                 ("WATER.khlong_jik", "WL.SSB.07")):
        assert graph.has_edge(u, v), f"expected tributary edge {u} -> {v}"
        d = graph.get_edge_data(u, v)
        found = [ed for ed in d.values() if ed.get("kind") == "flows_to" and ed.get("drains_after")]
        assert found, f"{u} -> {v} missing drains_after attribute"
        assert found[0]["drains_after"] == "WL.SSB.09"


def test_condition_flag_open_on_pump_intake_nodes(graph):
    for nid in ("ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04",
                "pump_station:water_station:1", "pump_station:water_station:2",
                "tunnel:bma_dds:saensaeb_ladprao"):
        assert graph.nodes[nid].get("condition") == "OPEN", f"{nid} missing condition=OPEN"


def test_north_axis_stub_labelled_and_separate(graph):
    d = graph.nodes["WATER.canal_prem_prachakon"]
    assert d.get("scope") == "bangkok_north_mvp_stub"
    assert graph.has_edge("WATER.canal_prem_prachakon", "river:chao_phraya")


def test_completeness_pass_resolved_sps_owned_by(graph):
    """ST.SPS.01-04 owned_by is no longer OPEN -- resolved via sources/owner_agency_
    crosswalk.yaml's VERIFIED row + docs/CAPACITY.md §2. The source registry still
    writes the pre-lock compound string VERIFIED-CONTRADICTED (docs/CAPACITY.md itself
    still flags this pending confirmation) -- build_graph.py's _norm_tag normalizes
    that down to tag=VERIFIED + contradicted=True (an earlier check defect: the
    compound string used to reach api/v1/MCP verbatim, outside TAG_VOCABULARY)."""
    for pump in ("ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"):
        edges = [d for _, _, d in graph.out_edges(pump, data=True) if d.get("kind") == "owned_by"]
        assert len(edges) == 1, f"{pump} should have exactly one owned_by edge"
        assert edges[0]["tag"] == "VERIFIED"
        assert edges[0].get("contradicted") is True


def test_orphan_count_reduced_by_completeness_pass(graph):
    report = validate.rule_no_orphans(graph)
    # AG_BASIN_CMT/AG_REGCOM (no command-hierarchy edge kind exists in this typology's
    # closed vocabulary yet) and the 3 no-connectivity-data nodes stay orphans, documented.
    # RES.TOOL.WATER_PUSH_BOAT/RES.TOOL.AXIAL_WATER_PUSHER (added 2026-09-28, docs/
    # knowledge/card_tool_water_push_boats.md) are intentional orphans too: they are
    # GENERIC tool-classification nodes, referenced by the real deployment instance
    # (RES.BOAT_PUSH.AG_UNKNOWN.01) via a plain `generic_tool_ref` attribute rather than a
    # graph edge -- no edge kind in the closed vocabulary means "is an instance of"/
    # "classified as" (part_of is restricted to agency->ministry/ministry->government by
    # validate.py's ALLOWED_PAIRS), so this classification link is intentionally an
    # attribute, not an edge; see that card's §"Typology extension" for the full reasoning.
    # RES.TOOL.RESCUE_DRONE (added 2026-09-28, docs/knowledge/card_tool_rescue_drones_
    # romklao_2569.md) is the same kind of intentional orphan as RES.TOOL.WATER_PUSH_
    # BOAT above -- a generic tool-classification node the real deployment instance
    # (RES.DRONE.ROMKLAO_20260928) references via `generic_tool_ref`, not a graph edge.
    # ST.BANGTALAD.RELAY.01 (added 2026-09-28, docs/knowledge/card_paakklongbangtalad_
    # intake_starved_2569.md -- relay pump station position/status genuinely OPEN, the
    # field report's own open question, not connected to anything yet by design) is the
    # same documented-gap pattern as the rows above.
    # Private-sector relief task (2026-09-28, docs/knowledge/card_private_sector_
    # relief_2026-09-28.md) adds a further batch of the same documented-gap pattern:
    # generic RES.TOOL.* classification nodes with no graph edge to their instances
    # (COW/charging-point/vehicle-refuge-parking) -- the same intentional-orphan
    # convention as the other RES.TOOL.* generics above. The same card ALSO adds an
    # `operates` edge AG_SENA -> RES.TOOL.MOBILE_PUMP (§5, pump moved between SENA
    # projects), so RES.TOOL.MOBILE_PUMP is no longer an orphan and drops out of this
    # set -- confirmed via typology/edges/operates.yaml, not assumed.
    assert set(report) == {"AG_BASIN_CMT", "AG_REGCOM", "GI.CHULA_CENTENARY_PARK",
                             "GI.BENJAKITTI_FOREST_PARK",
                             "RES.COMMUNITY_WARNING_LITERACY.SAMMAKORN.01",
                             "RES.TOOL.WATER_PUSH_BOAT", "RES.TOOL.AXIAL_WATER_PUSHER",
                             "RES.TOOL.RESCUE_DRONE",
                             "ST.BANGTALAD.RELAY.01",
                             "RES.TOOL.CHARGING_POINT", "RES.TOOL.COW",
                             "RES.TOOL.VEHICLE_REFUGE_PARKING"}, (
        f"unexpected orphan set: {sorted(report)}")
