"""Tests for tools/kg/accountability.py -- a tiny synthetic graph, not the real KG.

Run only this file (per AGENTS.md "no repeated full-arc audits" while iterating):
    python3 -m pytest tests/test_accountability.py -q
"""
from __future__ import annotations

import networkx as nx
import pytest

from tools.kg import accountability as acct


def _tiny_graph() -> nx.MultiDiGraph:
    """A small synthetic KG: one asset near (13.0, 100.0), owned by an agency that is
    itself commanded by a higher agency and authorized by one law with an OPEN section,
    plus a COMMANDS edge carrying an edge_problems-style attribute (as build_river_kg.py's
    apply_edge_problems would attach it)."""
    G = nx.MultiDiGraph()
    G.add_node("asset:test:PUMP01", kind="asset", class_="pump_station",
               **{"class": "pump_station"},
               name_th="test pump", lat=13.0, lon=100.0, owner="TEST_OWNER",
               tag="VERIFIED", latest_value=None, latest_ts=None)
    G.add_node("AG_TEST_LOCAL", kind="agency", class_="governance_dag", name_th="Local test agency")
    G.add_node("AG_TEST_TOP", kind="agency", class_="governance_dag", name_th="Top test agency")
    G.add_node("LAW_TEST", kind="law", class_="governance_dag", name_th="Test Act (section OPEN)")

    G.add_edge("AG_TEST_LOCAL", "asset:test:PUMP01", kind="OWNS", tag="VERIFIED",
               source="test")
    G.add_edge("AG_TEST_TOP", "AG_TEST_LOCAL", kind="COMMANDS", tag="RELAYED",
               source="test", problem_academic="Institutional fragmentation (synthetic)",
               problem_tag="MEASURED-on-graph", problem_sources="test")
    G.add_edge("LAW_TEST", "AG_TEST_LOCAL", kind="AUTHORIZES", tag="RELAYED-GENERAL",
               source="test")
    return G


def test_nearest_assets_within_radius():
    G = _tiny_graph()
    found = acct.nearest_assets(G, 13.0, 100.0, radius_km=3.0)
    assert len(found) == 1
    assert found[0]["asset_id"] == "asset:test:PUMP01"
    assert found[0]["owner"] == "TEST_OWNER"


def test_nearest_assets_outside_radius_is_empty():
    G = _tiny_graph()
    found = acct.nearest_assets(G, 20.0, 105.0, radius_km=3.0)
    assert found == []


def test_owner_to_agency_via_crosswalk():
    crosswalk = {"TEST_OWNER": {"agency_id": "AG_TEST_LOCAL", "tag": "VERIFIED", "note": "test row"}}
    row = acct.owner_to_agency("TEST_OWNER", crosswalk)
    assert row["agency_id"] == "AG_TEST_LOCAL"
    row_missing = acct.owner_to_agency("NOT_IN_CROSSWALK", crosswalk)
    assert row_missing["agency_id"] is None
    assert row_missing["tag"] == "OPEN"


def test_commands_ancestor_chain_walks_generically():
    G = _tiny_graph()
    chain = acct.commands_ancestor_chain(G, "AG_TEST_LOCAL")
    assert len(chain) == 1
    assert chain[0]["node"] == "AG_TEST_TOP"
    assert chain[0]["level"] == 1
    assert chain[0]["edge"] == ("AG_TEST_TOP", "AG_TEST_LOCAL")


def test_authorizes_for_flags_open_section():
    G = _tiny_graph()
    laws = acct.authorizes_for(G, "AG_TEST_LOCAL")
    assert len(laws) == 1
    assert laws[0]["law_id"] == "LAW_TEST"
    assert "OPEN" in laws[0]["section_status"]


def test_q1_refuses_when_nothing_within_radius():
    G = _tiny_graph()
    crosswalk = {"TEST_OWNER": {"agency_id": "AG_TEST_LOCAL", "tag": "VERIFIED", "note": "test row"}}
    q1 = acct.q1_who_is_responsible(G, 20.0, 105.0, 3.0, crosswalk)
    assert "refused" in q1


def test_q1_builds_full_chain():
    G = _tiny_graph()
    crosswalk = {"TEST_OWNER": {"agency_id": "AG_TEST_LOCAL", "tag": "VERIFIED", "note": "test row"}}
    q1 = acct.q1_who_is_responsible(G, 13.0, 100.0, 3.0, crosswalk)
    assert q1["assets_found"] == 1
    chain = q1["chains"][0]
    assert chain["owns_edge"]["agency_id"] == "AG_TEST_LOCAL"
    assert chain["commands_ancestors"][0]["node"] == "AG_TEST_TOP"
    assert chain["authorizes"][0]["law_id"] == "LAW_TEST"
    assert "AG_TEST_LOCAL" in q1["_agencies_found"]
    assert ("AG_TEST_TOP", "AG_TEST_LOCAL") in q1["_path_edges"]


def test_q3_finds_problem_academic_on_path_edge():
    G = _tiny_graph()
    crosswalk = {"TEST_OWNER": {"agency_id": "AG_TEST_LOCAL", "tag": "VERIFIED", "note": "test row"}}
    q1 = acct.q1_who_is_responsible(G, 13.0, 100.0, 3.0, crosswalk)
    q3 = acct.q3_problematic_law(G, q1["chains"], q1["_path_edges"])
    assert len(q3["edge_problems_on_path"]) == 1
    assert q3["edge_problems_on_path"][0]["problem_academic"] == "Institutional fragmentation (synthetic)"
    assert len(q3["law_sections_open"]) == 1


def test_q3_refuses_with_no_path_edges():
    G = _tiny_graph()
    q3 = acct.q3_problematic_law(G, [], [])
    assert "refused" in q3


def test_q2_refuses_with_no_agencies():
    q2 = acct.q2_overlapping_authority([])
    assert "refused" in q2


def test_q4_matches_pump_action_and_no_banned_words():
    assets = [{"class": "pump_station", "asset_id": "x", "owner": "TEST_OWNER",
               "distance_km": 0.1, "name_th": "test", "tag": "VERIFIED",
               "latest_value": None, "latest_ts": None}]
    q4 = acct.q4_self_help(assets, area_id=None)
    assert "matched_actions" in q4
    assert len(q4["matched_actions"]) > 0
    joined = " ".join(a["text_th"] for a in q4["matched_actions"])
    for w in acct.BANNED_WORDS:
        assert w not in joined


def test_q4_refuses_with_no_assets():
    q4 = acct.q4_self_help([], area_id=None)
    assert "refused" in q4


def test_resolve_point_latlon_areaid_and_assetid():
    G = _tiny_graph()
    p1 = acct.resolve_point("13.0,100.0", G)
    assert p1["lat"] == 13.0 and p1["lon"] == 100.0
    p2 = acct.resolve_point("sammakorn", G)
    assert p2["area_id"] == "sammakorn"
    p3 = acct.resolve_point("asset:test:PUMP01", G)
    assert p3["lat"] == 13.0
    p4 = acct.resolve_point("not-a-real-anything", G)
    assert "refused" in p4
