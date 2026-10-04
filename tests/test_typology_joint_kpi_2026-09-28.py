"""
tests/test_typology_joint_kpi_2026-09-28.py -- founder ask "สกัดไปเข้า typology node
การเมืองด้วย": the กพร. Joint KPI FY2569-2570 29-body agency list (via Lanner FB post),
folded into the power layer as agency/ministry/government nodes + `part_of` edges. Real
repo data only (the typology/*.yaml registries this check added), no simulated data.
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


def test_part_of_in_closed_vocab(graph):
    assert "part_of" in validate.CLOSED_EDGE_VOCAB


def test_onwr_is_joint_kpi_host_under_pmo(graph):
    assert graph.nodes["AG_ONWR"].get("joint_kpi_host") is True
    assert graph.has_edge("AG_ONWR", "MINISTRY.PMO")
    # get_edge_data on a MultiDiGraph returns {key: attrs}; at least one must be part_of
    assert any(d.get("kind") == "part_of" for d in
               graph.get_edge_data("AG_ONWR", "MINISTRY.PMO").values())


def test_every_ministry_and_category_reaches_government_root(graph):
    import networkx as nx
    part_of_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("kind") == "part_of"]
    PG = nx.DiGraph()
    PG.add_edges_from(part_of_edges)
    ministry_nodes = [n for n, d in graph.nodes(data=True) if d.get("kind") == "ministry"]
    # 11 from the Joint-KPI post + MINISTRY.MHESI/MINISTRY.SOCIAL (added 2026-09-28,
    # docs/knowledge/card_tool_rescue_drones_romklao_2569.md -- อว./พม. were never
    # registered as ministry nodes before that task, even though AG_MHESI/AG_MSDHS
    # already existed as agency ids in water_system_dag.mmd).
    assert len(ministry_nodes) == 13, f"expected 13 ministry/category nodes, got {len(ministry_nodes)}"
    for m in ministry_nodes:
        assert nx.has_path(PG, m, "GOV.TH"), f"{m} does not reach GOV.TH via part_of"


# Agencies added 2026-09-28 by the MDES climate-comms centre task (docs/knowledge/
# card_climate_comms_centre_2026-09-28.md) and the MHESI rescue-drone task (docs/
# knowledge/card_tool_rescue_drones_romklao_2569.md) -- real part_of edges, but NOT part
# of the Lanner-post Joint-KPI 29-body list this test file is specifically about, so
# they're excluded from the "exactly 29" count rather than silently inflating it.
_NON_JOINT_KPI_PART_OF_AGENCIES = {"AG_CLIMATE_COMMS_CENTRE", "AG_AFNC", "AG_PRD",
                                     "AG_PM_SPOKES", "AG_MHESI", "AG_KMUTNB", "AG_MSDHS"}


def test_29_agencies_have_exactly_one_part_of_edge_to_a_ministry(graph):
    """The Joint-KPI post names exactly 29 bodies -- every agency with a part_of edge
    should have exactly one (no agency double-counted under two ministries)."""
    agency_part_of_sources = {}
    for u, v, d in graph.edges(data=True):
        if d.get("kind") != "part_of":
            continue
        if graph.nodes[u].get("kind") != "agency":
            continue
        if u in _NON_JOINT_KPI_PART_OF_AGENCIES:
            continue
        agency_part_of_sources.setdefault(u, []).append(v)
    assert len(agency_part_of_sources) == 29, (
        f"expected 29 agency->ministry part_of edges (one per Joint-KPI body), got "
        f"{len(agency_part_of_sources)}")
    dupes = {k: v for k, v in agency_part_of_sources.items() if len(v) != 1}
    assert not dupes, f"agency(ies) with != 1 ministry parent: {dupes}"


def test_no_invented_operates_or_decides_from_joint_kpi_source(graph):
    """The Lanner post's role statements are general mandate text (captured as role_th
    node attributes), never a specific decider/operator claim -- so no NEW operates/
    decides edge should exist for any of the brand-new Joint-KPI agency ids."""
    import yaml
    new_ids = set()
    doc = yaml.safe_load(
        (REPO_ROOT / "typology" / "nodes" / "agencies_joint_kpi_2026-09-28.yaml")
        .read_text(encoding="utf-8"))
    for r in doc["rows"]:
        new_ids.add(r["id"])
    for u, v, d in graph.edges(data=True):
        if d.get("kind") in ("operates", "decides"):
            assert u not in new_ids and v not in new_ids, (
                f"unexpected {d.get('kind')} edge touching a brand-new Joint-KPI-only "
                f"agency id ({u} -> {v}) -- the source post never states this")


def test_role_th_attributes_present_for_stated_roles(graph):
    expect_role = {
        "AG_TMD": "พยากรณ์",
        "AG_ONWR": "ประสานงานภาพรวม",
        "AG_RID": "ชลประทาน",
        "AG_DWR": "นอกเขตชลประทาน",
        "AG_DDPM": "อพยพ",
        "AG_DPT": "ระบายน้ำเมือง",
        "AG_GISTDA": "ดาวเทียม",
        "AG_HII": "ดาวเทียม",
    }
    for nid, must_contain in expect_role.items():
        role = graph.nodes[nid].get("role_th") or ""
        assert must_contain in role, f"{nid}.role_th missing expected text {must_contain!r}: {role!r}"


def test_ministries_group_type_distinguishes_non_ministry_categories(graph):
    for cat_id in ("CATEGORY.PUBLIC_ORG", "CATEGORY.STATE_ENTERPRISE", "CATEGORY.LOCAL_GOV"):
        gt = graph.nodes[cat_id].get("group_type")
        assert gt in ("public_organization", "state_enterprise", "local_government")
