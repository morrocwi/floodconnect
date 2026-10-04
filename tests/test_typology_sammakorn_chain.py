"""
tests/test_typology_sammakorn_chain.py -- the Sammakorn worked-example chain, real repo
data only: soi -> WL.SMK.01 -> ST.SPS.01-04 -> WL.BMA.02 -> WL.SSB.* -> WL.PKN.01
(พระโขนง) -> river (เจ้าพระยา) is connected by `flows_to`, and the known OPEN gaps
(pump operator, AG_MEA) are reported by validate.py, not hidden.
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
    build_graph.load_registry_edges(G)
    return G


# ST.SPS.01 sits on the pond -> banma2 (WL.BMA.02) leg (north exit, the real link to the
# แสนแสบ mainline -- see test_chain_ordered_path_pond_to_river below). ST.SPS.02/03/04
# sit in PARALLEL on the pond -> wangyai leg (south exit) -- see
# test_south_branch_pumps_are_parallel_not_series. Both fixed 2026-09-28 after an
# independent-review finding; tools/typology/build_graph.py's own
# `_build_sammakorn_head_chain()` docstring has the full source citation.


def test_all_sammakorn_chain_nodes_exist(graph):
    for nid in ["SOI.SAMMAKORN.17", "SOI.SAMMAKORN.18", "WL.SMK.01", "ST.SPS.01",
                "ST.SPS.02", "ST.SPS.03", "ST.SPS.04", "WL.BMA.02", "WL.SSB.10",
                "WL.PKN.01", "river:chao_phraya"]:
        assert graph.has_node(nid), f"expected Sammakorn-chain node {nid!r} missing"


def test_chain_connected_by_flows_to(graph):
    import networkx as nx
    flow_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("kind") == "flows_to"]
    FG = nx.DiGraph()
    FG.add_edges_from(flow_edges)
    for soi in ("SOI.SAMMAKORN.17", "SOI.SAMMAKORN.18"):
        assert nx.has_path(FG, soi, "river:chao_phraya"), (
            f"{soi} does not reach river:chao_phraya via flows_to edges")
    # both pump branches (ST.SPS.01 on the banma leg, ST.SPS.02/03/04 on the
    # sammakorn_pond->wangyai leg) must sit on a flows_to path reachable from the pond.
    for pump in ("ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"):
        assert pump in FG, f"{pump} not wired into the flows_to graph at all"


def test_chain_ordered_path_pond_to_river(graph):
    """Independent-review fix, 2026-09-28: the earlier build chained ST.SPS.01-04
    pump-to-pump in series and never linked the Sammakorn branch to the แสนแสบ mainline
    at all. Real order, sourced directly from site/build_data.py's own
    SAMMAKORN_CHAIN_NODES/SAMMAKORN_CHAIN_EDGES (not east_chain.yaml alone, and never
    picked by coordinate guessing): pond -> ST.SPS.01 -> banma2(WL.BMA.02) ->
    saensaeb(WL.SSB.08) -> ... -> WL.PKN.01 -> river."""
    import networkx as nx
    flow_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("kind") == "flows_to"]
    FG = nx.DiGraph()
    FG.add_edges_from(flow_edges)
    path = nx.shortest_path(FG, "WL.SMK.01", "river:chao_phraya")
    assert path == ["WL.SMK.01", "ST.SPS.01", "WL.BMA.02", "WL.SSB.08", "WL.SSB.07",
                     "WL.SSB.04", "WL.PKN.01", "river:chao_phraya"], (
        f"Sammakorn head chain does not match the source (site/build_data.py "
        f"SAMMAKORN_CHAIN_EDGES + east_chain.yaml mainline): got {path}")
    assert nx.has_path(FG, "WL.SMK.01", "WL.BMA.02")
    assert nx.has_path(FG, "WL.BMA.02", "WL.PKN.01")
    # the declared backflow-risk reverse edge (banma2 -> pond) must also exist
    assert FG.has_edge("WL.BMA.02", "WL.SMK.01")


def test_no_pump_to_pump_flows_to_edge(graph):
    """ST.SPS.02/03/04 are 3 independent pump stations around the pond (east_chain.yaml's
    control_structures names all 3 on one shared edge, never a chain) -- no flows_to
    edge should ever connect one pump node directly to another pump node."""
    pump_nodes = {n for n, d in graph.nodes(data=True) if d.get("kind") == "pump"}
    for u, v, d in graph.edges(data=True):
        if d.get("kind") != "flows_to":
            continue
        assert not (u in pump_nodes and v in pump_nodes), (
            f"unexpected pump-to-pump flows_to edge {u} -> {v}")


def test_south_branch_pumps_are_parallel_not_series(graph):
    for pump in ("ST.SPS.02", "ST.SPS.03", "ST.SPS.04"):
        assert graph.has_edge("WL.SMK.01", pump), f"expected WL.SMK.01 -> {pump}"
        assert graph.has_edge(pump, "WATER.wangyai"), f"expected {pump} -> WATER.wangyai"


def test_validate_reports_pump_operator_gap_as_open_not_hidden(graph):
    """The pump-operator OPEN gap (structural_issues_2026-09-28.yaml ISSUE-DECISION-02 /
    THAI_WATER_GOVERNANCE_MAP.md §(7)) must show up in validate.py's report, never be
    silently satisfied by an invented edge."""
    report_gp = validate.rule_gate_pump_operates_decides(graph)
    open_node_ids = {row["node"] for row in report_gp["open_gaps"]}
    for pump in ("ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"):
        assert pump in open_node_ids, (
            f"{pump} should appear in validate.py's open_gaps (no confirmed decides "
            f"edge exists for it in this repo) -- if this now fails because a decides "
            f"edge was added, that's real progress, update typology/edges/decides.yaml "
            f"and this test together, never silently drop the gap")
    for row in report_gp["open_gaps"]:
        if row["node"].startswith("ST.SPS"):
            assert row["operates_all_open"] is True, (
                f"{row['node']}: operates edge(s) exist but are not all tagged OPEN -- "
                f"a real, sourced operator was found and this test/registry is stale")


def test_ag_mea_present_but_no_confirmed_link_to_sammakorn_soi(graph):
    """AG_MEA exists in this repo's governance DAG (water_system_dag.mmd) -- the
    proposal doc's own claim that it was "missing" is wrong; this test locks in that
    AG_MEA the NODE exists, while the electricity-outage warns edge to the soi group
    (S10, structural_issues_2026-09-28.yaml ISSUE-PEOPLE-04) is genuinely OPEN."""
    assert graph.has_node("AG_MEA")
    mea_warns_to_soi = [
        (u, v, d) for u, v, d in graph.edges(data=True)
        if d.get("kind") == "warns" and u == "AG_MEA"
    ]
    assert mea_warns_to_soi, "expected AG_MEA to at least have a declared (even if OPEN) warns row"
    assert all(d.get("tag") == "OPEN" for _, _, d in mea_warns_to_soi), (
        "AG_MEA -> soi warns edge should be tagged OPEN (no confirmed warning channel "
        "reaches ซ.17/18 per S10) -- if a real channel was found, update "
        "typology/edges/warns.yaml and this test together")


def test_sammakorn_pump_wording_never_bare_0_of_11(graph):
    """Independent-review fix 2026-09-28: never write a bare '0/11' -- station count
    (4/4 faulted) and machine count (0/11 running) are two different levels."""
    import yaml
    doc = yaml.safe_load((REPO_ROOT / "typology" / "nodes" / "sensors.yaml")
                          .read_text(encoding="utf-8"))
    agg = doc["aggregate_readouts"][0]
    assert agg["station_count_total"] == 4
    assert agg["machine_count_total"] == 11
    assert agg["combined_wording_th"] == "สถานี 4/4 ขัดข้อง · เครื่อง 0/11 เดิน"
    assert agg["discrepancy_tag"] == "OPEN"
