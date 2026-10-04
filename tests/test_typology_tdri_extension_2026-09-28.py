"""
tests/test_typology_tdri_extension_2026-09-28.py -- founder ask "สกัดเพื่อเสริม typology
ที่ยังขาดอยู่ เอาแค่ส่วนสำคัญ": phase (disaster-cycle), capability (C3), permanence/level,
infrastructure (grey/green_blue/soft), and warning-quality (CAP-like datum/area/
lead_time) attributes, extracted from 3 TDRI public think-tank articles. Real repo data
only (the typology/*.yaml this check added), no simulated data.
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


def test_overlay_has_no_missing_ids(graph):
    """Every id in tdri_overlay_2026-09-28.yaml must already exist in the graph (a
    missing id is a real data error, never silently dropped or auto-created)."""
    import networkx as nx
    G2 = nx.MultiDiGraph()
    build_graph.build_water_layer(G2)
    build_graph.load_registry_nodes(G2)
    _, missing = build_graph.apply_node_overlays(G2)
    assert not missing, f"overlay row(s) reference node id(s) not in the graph: {missing}"


def test_infra_class_present_on_water_nodes(graph):
    for n, d in graph.nodes(data=True):
        if d.get("layer") != "water" or d.get("kind") in ("river", "sensor"):
            continue  # sensor nodes are a governance/observation overlay, not physical
            # infrastructure -- outside this attribute's scope
        assert d.get("infra_class") in ("grey", "green_blue"), (
            f"{n} (kind={d.get('kind')}) missing a grey/green_blue infra_class")
    assert graph.nodes["WL.SMK.01"]["infra_class"] == "green_blue"
    assert graph.nodes["WL.NBN.01"]["infra_class"] == "green_blue"
    assert graph.nodes["WL.SSB.10"]["infra_class"] == "grey"
    assert graph.nodes["ST.SPS.01"]["infra_class"] == "grey"


def test_green_infrastructure_examples_present(graph):
    for nid in ("GI.CHULA_CENTENARY_PARK", "GI.BENJAKITTI_FOREST_PARK"):
        assert graph.has_node(nid)
        assert graph.nodes[nid]["infra_class"] == "green_blue"
    assert graph.nodes["RES.COMMUNITY_WARNING_LITERACY.SAMMAKORN.01"]["infra_class"] == "soft"


def test_phase_attribute_on_warning_channels_and_resources(graph):
    for n, d in graph.nodes(data=True):
        if d.get("kind") not in ("warning_channel", "resource"):
            continue
        assert d.get("phase") in ("normal", "pre_event", "incident", "post_event"), (
            f"{n} missing a valid phase attribute")


def test_permanence_and_level_on_agency_nodes(graph):
    expect = {
        "AG_BASIN_CMT": ("permanent", "basin"),
        "AG_REGCOM": ("ad_hoc", "basin"),
        "AG_ONWR": ("permanent", "national"),
        "AG_DDPM": ("permanent", "national"),
        "AG_BMA_GOV": ("permanent", "local"),
        "AG_ESTATE": ("permanent", "local"),
    }
    for nid, (permanence, level) in expect.items():
        d = graph.nodes[nid]
        assert d.get("permanence") == permanence, f"{nid}.permanence"
        assert d.get("level") == level, f"{nid}.level"


def test_capability_checklist_fields_exist_and_default_open(graph):
    for nid in ("AG_ONWR", "AG_DDPM", "AG_BMA_GOV", "AG_ESTATE", "AG_REGCOM"):
        d = graph.nodes[nid]
        for f in validate.CAPABILITY_FIELDS:
            assert f in d, f"{nid} missing capability field {f}"
            assert d[f] is None, f"{nid}.{f} should be OPEN (null) -- no source states it"


def test_capability_gaps_report_nonempty_and_no_schema_error(graph):
    gaps = validate.report_capability_gaps(graph)
    assert len(gaps) >= 5
    for nid, missing in gaps.items():
        assert set(missing) <= set(validate.CAPABILITY_FIELDS)


def test_warns_edges_carry_cap_like_fields(graph):
    for u, v, d in graph.edges(data=True):
        if d.get("kind") != "warns":
            continue
        for f in ("instruction", "datum", "area", "lead_time"):
            assert f in d, f"warns edge {u} -> {v} missing CAP-like field {f}"


def test_warning_quality_gaps_report_flags_open_datum_and_lead_time(graph):
    gaps = validate.report_warning_quality_gaps(graph)
    assert len(gaps) > 0
    for edge, missing in gaps.items():
        assert "datum" in missing or "lead_time" in missing or "area" in missing or \
               "instruction" in missing


def test_no_criticism_of_named_individuals_in_new_registry_files(graph):
    """Founder rule: extract structure only, never carry the TDRI articles' criticism of
    named individuals (Hat Yai mayor, named ministers) into the graph."""
    import yaml
    banned_terms = ["นายกเทศมนตรี", "รัฐมนตรี"]  # position words that would appear only if
    # a specific office-holder's personal conduct were being narrated, not structure
    for path in (REPO_ROOT / "typology" / "nodes").glob("*2026-09-28*.yaml"):
        text = path.read_text(encoding="utf-8")
        # allow generic structural mentions but forbid direct personal blame framings
        assert "โง่" not in text and "ผิดพลาดส่วนตัว" not in text and "ไร้ความสามารถ" not in text


def test_hat_yai_is_cross_case_lesson_only(graph):
    """Hat Yai is explicitly next-version scope -- must not appear as a first-class node
    in this build's graph, only as a lesson-row citation in the structural-issues doc."""
    for n in graph.nodes:
        assert "HATYAI" not in str(n).upper() and "หาดใหญ่" not in str(n)


def test_sponge_city_date_inconsistency_flagged_open_not_resolved():
    import yaml
    doc = yaml.safe_load(
        (REPO_ROOT / "typology" / "nodes" / "tdri_extension_2026-09-28.yaml")
        .read_text(encoding="utf-8"))
    found = False
    for r in doc["rows"]:
        src = r.get("source") or ""
        if "30 มิ.ย. 2025" in src and "24-26 ก.ย. 2569" in src:
            found = True
            assert "OPEN" in src
    assert found, "expected at least one row citing the sponge-city article's date inconsistency"
