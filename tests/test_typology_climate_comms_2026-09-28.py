"""
tests/test_typology_climate_comms_2026-09-28.py -- MDES (กระทรวงดีอี) climate-comms
centre, per ข่าวแถลงกระทรวงดีอี 28 ก.ย. 2569 (RELAYED). Network structure only, no
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

from tools.typology import build_graph, validate  # noqa: E402

NODE_FILE = REPO_ROOT / "typology" / "nodes" / "mdes_climate_comms_2026-09-28.yaml"
CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_climate_comms_centre_2026-09-28.md"


@pytest.fixture(scope="module")
def graph():
    import networkx as nx
    G = nx.MultiDiGraph()
    build_graph.build_water_layer(G)
    build_graph.load_registry_nodes(G)
    build_graph.apply_node_overlays(G)
    build_graph.load_registry_edges(G)
    return G


def test_card_exists():
    assert CARD_PATH.exists()


def test_new_nodes_present(graph):
    for nid in ("AG_CLIMATE_COMMS_CENTRE", "AG_PRD", "AG_MCOT", "AG_PM_SPOKES", "AG_AFNC",
                "WCH.TV_RADIO_PRD_MCOT", "WCH.GOV_SOCIAL"):
        assert graph.has_node(nid), f"expected node {nid}"


def test_tmd_reused_not_duplicated(graph):
    """AG_TMD must be the SAME node this repo already had (part_of -> MINISTRY.DIGITAL
    predates this check) -- this check must not create a second TMD-like node."""
    assert graph.has_node("AG_TMD")
    ag_tmd_like = [n for n in graph.nodes if "TMD" in n]
    assert ag_tmd_like == ["AG_TMD"]


def test_centre_and_afnc_part_of_ministry_digital(graph):
    for src in ("AG_CLIMATE_COMMS_CENTRE", "AG_AFNC", "AG_TMD"):
        assert graph.has_edge(src, "MINISTRY.DIGITAL"), f"expected {src} -> MINISTRY.DIGITAL"
        d = graph.get_edge_data(src, "MINISTRY.DIGITAL")
        assert any(ed.get("kind") == "part_of" for ed in d.values())


def test_prd_and_spokes_part_of_pmo(graph):
    for src in ("AG_PRD", "AG_PM_SPOKES"):
        assert graph.has_edge(src, "MINISTRY.PMO")
        d = graph.get_edge_data(src, "MINISTRY.PMO")
        assert any(ed.get("kind") == "part_of" and ed.get("tag") == "RELAYED"
                    for ed in d.values())


def test_mcot_has_no_part_of_edge(graph):
    """AG_MCOT is not in the Joint-KPI 4-state-enterprise list this repo already
    recorded (CATEGORY.STATE_ENTERPRISE) -- no part_of edge invented for it."""
    part_of_edges = [(u, v) for u, v, d in graph.out_edges("AG_MCOT", data=True)
                       if d.get("kind") == "part_of"]
    assert part_of_edges == []
    assert graph.nodes["AG_MCOT"].get("agency_class") == "state_enterprise"


def test_tmd_operates_centre(graph):
    assert graph.has_edge("AG_TMD", "AG_CLIMATE_COMMS_CENTRE")
    d = graph.get_edge_data("AG_TMD", "AG_CLIMATE_COMMS_CENTRE")
    assert any(ed.get("kind") == "operates" and ed.get("tag") == "RELAYED" for ed in d.values())


def test_channel_partners_report_to_centre(graph):
    for src in ("AG_PRD", "AG_MCOT", "AG_PM_SPOKES"):
        assert graph.has_edge(src, "AG_CLIMATE_COMMS_CENTRE")
        d = graph.get_edge_data(src, "AG_CLIMATE_COMMS_CENTRE")
        assert any(ed.get("kind") == "reports_to" and ed.get("tag") == "RELAYED"
                    for ed in d.values())


def test_warns_edges_carry_severity_scale_and_open_cap_fields(graph):
    for ch in ("WCH.TV_RADIO_PRD_MCOT", "WCH.GOV_SOCIAL"):
        assert graph.has_edge("AG_CLIMATE_COMMS_CENTRE", ch)
        d = graph.get_edge_data("AG_CLIMATE_COMMS_CENTRE", ch)
        warns = [ed for ed in d.values() if ed.get("kind") == "warns"]
        assert warns, f"expected a warns edge to {ch}"
        ed = warns[0]
        assert ed.get("instruction")  # non-empty, satisfies validate.py's rule
        assert ed.get("severity_scale") == "symbolic+numeric compared to past events (announced policy)"
        assert ed.get("tag") == "RELAYED"


def test_afnc_has_no_outgoing_edges_to_data_or_gauge_nodes(graph):
    """Neutral note: AFNC is a monitoring channel only -- this repo never lets it assert
    anything about a station/gauge node."""
    for _, v, d in graph.out_edges("AG_AFNC", data=True):
        assert graph.nodes[v].get("kind") not in ("gate", "pump", "sensor"), \
            f"AG_AFNC must not have an edge asserting anything about {v}"


def test_no_personal_names_in_new_files():
    text = NODE_FILE.read_text(encoding="utf-8")
    # "นาย " (trailing space) to avoid false positives on "นายกฯ"/"นายกรัฐมนตรี" (role
    # title, not a personal-name prefix)
    for prefix in ("นาย ", "นางสาว", "นาง "):
        assert prefix not in text


def test_structural_issue_rows_present():
    doc = yaml.safe_load(
        (REPO_ROOT / "docs" / "knowledge" / "structural_issues_2026-09-28.yaml")
        .read_text(encoding="utf-8"))
    ids = {row["id"] for row in doc["issues"]}
    assert "ISSUE-WARNING-04" in ids
    assert "ISSUE-WARNING-05" in ids


def test_validate_reports_no_schema_errors(graph):
    schema_errors = []
    schema_errors += validate.rule_claim_edges_tagged(graph)
    schema_errors += validate.rule_closed_edge_vocab(graph)
    schema_errors += validate.rule_part_of_target_kind(graph)
    schema_errors += validate.rule_warns_instruction(graph)
    assert not schema_errors, schema_errors
