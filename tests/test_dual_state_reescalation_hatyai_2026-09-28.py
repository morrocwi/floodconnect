"""
tests/test_dual_state_reescalation_hatyai_2026-09-28.py -- dual-state, re-escalation
memory, OUTSIDE_CALIBRATED_RANGE, mode-degradation ladder, safe-node continuity, and
NO_FEASIBLE_SAFE_ROUTE rules (docs/knowledge/card_dual_state_reescalation_hatyai_
2026-09-28.md). Every event fact used as a fixture is re-sourced from this repo's own
experiments/2025-11-hat-yai-real-data-redteam.md -- these are regression fixtures only,
NOT a Hat Yai page feature (Hat Yai stays next-version scope for the live site).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import community_dag as cd  # noqa: E402
from tools.backtest import outside_calibrated_range as ocr  # noqa: E402
from tools.backtest.prop_flood_06_v5 import apply_persistence  # noqa: E402

REDTEAM_PATH = REPO_ROOT / "experiments" / "2025-11-hat-yai-real-data-redteam.md"
CARD_PATH = REPO_ROOT / "docs" / "knowledge" / "card_dual_state_reescalation_hatyai_2026-09-28.md"


def test_card_and_source_exist():
    assert CARD_PATH.exists()
    assert REDTEAM_PATH.exists()


def test_ventilator_patient_count_not_in_repo_sources_and_therefore_dropped():
    """External-analysis claim of '130 ventilator patients' does not appear anywhere in
    this repo's own Hat Yai source file -- per founder instruction, a number not present
    in the repo's own files must be dropped, never imported from the external analysis.
    The card is allowed to EXPLAIN that '130' was checked and dropped (that sentence is
    provenance, not a claim); no typology node/edge attribute may carry it."""
    text = REDTEAM_PATH.read_text(encoding="utf-8")
    assert "130" not in text
    assert "ventilator" in text.lower()  # the qualitative finding IS present
    for path in (REPO_ROOT / "typology").rglob("*.yaml"):
        assert "130" not in path.read_text(encoding="utf-8"), f"{path} carries the dropped number"


# ---------------------------------------------------------------------------
# 1. DUAL STATE
# ---------------------------------------------------------------------------

def test_dual_state_vocab_closed_and_independent():
    assert cd.CURRENT_LOCAL_STATE == {"GREEN", "YELLOW", "RED", "UNKNOWN"}
    assert cd.FORWARD_HAZARD_STATE == {"NONE", "ACTIVE", "UNKNOWN"}


def _minimal_zone_doc(current_local_state=None, forward_hazard=None):
    node = {"kind": "zone", "layer": 2, "label_th": "test zone", "status": "UNKNOWN",
            "fresh": False}
    if current_local_state is not None:
        node["current_local_state"] = current_local_state
    if forward_hazard is not None:
        node["forward_hazard"] = forward_hazard
    return {"nodes": {"z1": node}, "edges": []}


def test_hatyai_dual_state_fixture_20nov_green_flag_vs_active_regional_warning():
    """Regression fixture (NOT a page feature): เทศบาลนครหาดใหญ่ แถลงการณ์ฉบับที่ 2, 20 พ.ย.
    2568 -- local flag GREEN/normal, while ONWR (30/2568, 13-14 พ.ย.) and TMD (16-19 พ.ย.)
    regional warnings were still active. The schema must accept BOTH fields declared
    independently, and neither may be derived from or silently overwrite the other."""
    doc = _minimal_zone_doc(current_local_state="GREEN", forward_hazard="ACTIVE")
    check = cd.validate_document(doc)
    assert check["valid"], check["errors"]
    assert doc["nodes"]["z1"]["current_local_state"] == "GREEN"
    assert doc["nodes"]["z1"]["forward_hazard"] == "ACTIVE"


def test_dual_state_invalid_values_are_schema_errors():
    doc = _minimal_zone_doc(current_local_state="ORANGE")
    check = cd.validate_document(doc)
    assert not check["valid"]
    assert any("current_local_state" in e for e in check["errors"])

    doc2 = _minimal_zone_doc(forward_hazard="MAYBE")
    check2 = cd.validate_document(doc2)
    assert not check2["valid"]
    assert any("forward_hazard" in e for e in check2["errors"])


def test_dual_state_fields_absent_is_not_an_error():
    doc = _minimal_zone_doc()
    check = cd.validate_document(doc)
    assert check["valid"], check["errors"]


# ---------------------------------------------------------------------------
# 2. RE-ESCALATION MEMORY
# ---------------------------------------------------------------------------

def test_apply_persistence_does_not_collapse_after_first_apparent_stabilization():
    """Generic structural property test (SYNTHETIC tier labels, not claimed as Hat Yai's
    real numbers) using the EXISTING apply_persistence() (tools/backtest/
    prop_flood_06_v5.py, reused verbatim, no new equation): a rise that holds for p
    consecutive readouts must register, even if it follows an earlier apparent
    stabilization -- the qualitative two-pulse pattern the redteam file describes
    (initial overflow ~21 พ.ย., second larger inflow 23-25 พ.ย.)."""
    # first pulse rises to L2, holds briefly, dips back toward L1 (apparent
    # stabilization), then a second, larger pulse rises further to L4.
    raw = ["L0", "L1", "L2", "L2", "L1", "L1", "L2", "L3", "L4", "L4"]
    persisted = apply_persistence(raw, p=2, q=3)
    assert persisted[-1] == "L4", (
        "second pulse must be able to raise the persisted tier past the first pulse's "
        f"level -- got {persisted}")
    # the persisted sequence must reach L4 at some point (not just approach it)
    assert "L4" in persisted


@pytest.mark.xfail(
    reason=(
        "U-Tapao/Hat Yai catchment (X.173A/X.90/X.44) has 0 nodes in "
        "docs/knowledge/water_system_dag.mmd and no bank/critical values verified in "
        "observations.sqlite (docs/knowledge/card_thirdparty_hatyai_redteam_2025-11_"
        "review_2026-09-27.md TODOLIST #13/#16) -- a real per-station tier sequence for "
        "this event cannot be built in this repo yet. Documented as OPEN rather than "
        "fabricating station data; this test names the exact missing precondition."
    ),
    strict=True,
)
def test_reescalation_on_real_hatyai_station_chain_not_yet_possible():
    raise AssertionError(
        "requires real X.173A->X.90->X.44 station tier readouts wired into a KG node "
        "chain -- does not exist in this repo yet")


# ---------------------------------------------------------------------------
# 3. OUTSIDE_CALIBRATED_RANGE
# ---------------------------------------------------------------------------

def test_outside_calibrated_range_labels():
    derived = ocr.load_derived()
    assert "bangkok_east" in derived
    ceiling = ocr.highest_calibrated_value(derived["bangkok_east"]["rain_24h_mm"])
    assert ceiling is not None
    below = ocr.classify_outside_calibrated_range(
        "bangkok_east", "rain_24h_mm", ceiling - 1, derived)
    assert below == ocr.LABEL_WITHIN
    above = ocr.classify_outside_calibrated_range(
        "bangkok_east", "rain_24h_mm", ceiling + 1, derived)
    assert above == ocr.LABEL_OUTSIDE


def test_outside_calibrated_range_open_for_unit_with_no_ceiling():
    derived = ocr.load_derived()
    assert ocr.classify_outside_calibrated_range(
        "no_such_unit", "no_such_variable", 999.0, derived) == ocr.LABEL_OPEN


def test_outside_calibrated_range_never_compares_across_basins():
    """hatyai/rain_24h_mm has no row in coping_thresholds.yaml's derived block
    (docs/knowledge/card_thirdparty_hatyai_redteam_2025-11_review_2026-09-27.md
    TODOLIST #15 -- hatyai only has river_flow_m3s/canal_level_m rows, not rain_24h_mm)
    -- classify() must return OPEN for it, never silently reuse a bangkok_east ceiling."""
    derived = ocr.load_derived()
    assert "rain_24h_mm" not in (derived.get("hatyai") or {})
    assert ocr.classify_outside_calibrated_range(
        "hatyai", "rain_24h_mm", 366.0, derived) == ocr.LABEL_OPEN


def test_report_outside_calibrated_range_wired_into_typology_validate():
    from tools.typology import validate
    import networkx as nx
    G = nx.MultiDiGraph()
    G.add_node("WL.TEST.01", kind="canal_reach",
               ocr_check={"unit": "bangkok_east", "variable": "rain_24h_mm",
                          "observed_value": 999.0})
    G.add_node("WL.TEST.02", kind="canal_reach")  # no ocr_check -- must be skipped
    result = validate.report_outside_calibrated_range(G)
    assert result["WL.TEST.01"] == ocr.LABEL_OUTSIDE
    assert "WL.TEST.02" not in result


# ---------------------------------------------------------------------------
# 4. EDGE MODE DEGRADATION ladder
# ---------------------------------------------------------------------------

def test_mode_degradation_ladder_closed_vocab_and_order():
    assert cd.MODE_DEGRADATION_LADDER == ("normal", "high_clearance_only", "boat_only",
                                           "blocked")
    assert cd.MODE_DEGRADATION_STATES == set(cd.MODE_DEGRADATION_LADDER) | {"UNKNOWN"}


def test_mode_degradation_invalid_value_is_schema_error():
    doc = {
        "nodes": {
            "a": {"kind": "zone", "layer": 2, "status": "UNKNOWN", "fresh": False},
            "b": {"kind": "support", "layer": 3, "status": "UNKNOWN", "fresh": False},
        },
        "edges": [
            {"id": "e1", "from": "a", "to": "b", "mode_degradation": "flying_carpet"},
        ],
    }
    check = cd.validate_document(doc)
    assert not check["valid"]
    assert any("mode_degradation" in e for e in check["errors"])


def test_mode_degradation_valid_values_pass():
    for val in cd.MODE_DEGRADATION_LADDER:
        doc = {
            "nodes": {
                "a": {"kind": "zone", "layer": 2, "status": "UNKNOWN", "fresh": False},
                "b": {"kind": "support", "layer": 3, "status": "UNKNOWN", "fresh": False},
            },
            "edges": [{"id": "e1", "from": "a", "to": "b", "mode_degradation": val}],
        }
        check = cd.validate_document(doc)
        assert check["valid"], (val, check["errors"])


# ---------------------------------------------------------------------------
# 5. SAFE NODE continuity fields
# ---------------------------------------------------------------------------

def test_safe_node_continuity_field_names():
    assert cd.SAFE_NODE_CONTINUITY_FIELDS == (
        "access_state", "power_state", "backup_power_state", "water_state",
        "comms_state", "medical_capacity_state", "occupancy_state")
    assert cd.SAFE_NODE_KINDS_REQUIRING_CONTINUITY == {"internal_safe", "external_safe",
                                                         "support"}


def test_report_safe_node_continuity_gaps():
    doc = {
        "nodes": {
            "full": {
                "kind": "external_safe", "layer": 5, "status": "UNKNOWN", "fresh": False,
                **{f: "UNKNOWN" for f in cd.SAFE_NODE_CONTINUITY_FIELDS},
            },
            "partial": {"kind": "internal_safe", "layer": 3, "status": "UNKNOWN",
                        "fresh": False, "access_state": "UNKNOWN"},
            "not_a_safe_kind": {"kind": "zone", "layer": 2, "status": "UNKNOWN",
                                "fresh": False},
        },
        "edges": [],
    }
    gaps = cd.report_safe_node_continuity_gaps(doc)
    assert "full" not in gaps
    assert "not_a_safe_kind" not in gaps
    assert set(gaps["partial"]) == set(cd.SAFE_NODE_CONTINUITY_FIELDS) - {"access_state"}


def test_hatyai_hospital_lesson_reflected_in_continuity_fields():
    """Hat Yai finding F (experiments/2025-11-hat-yai-real-data-redteam.md §F): Hospital
    Hat Yai had an urgent electricity problem despite being a hospital. power_state and
    backup_power_state must be distinct, declarable fields -- a hospital kind alone must
    never satisfy them."""
    assert "power_state" in cd.SAFE_NODE_CONTINUITY_FIELDS
    assert "backup_power_state" in cd.SAFE_NODE_CONTINUITY_FIELDS


# ---------------------------------------------------------------------------
# 6. NO FEASIBLE SAFE ROUTE
# ---------------------------------------------------------------------------

def test_find_safe_route_returns_explicit_no_route_reason_not_invented_path():
    doc = {
        "nodes": {
            "start": {"kind": "household", "layer": 0, "status": "UNKNOWN",
                       "fresh": False},
        },
        "edges": [],
    }
    result = cd.find_safe_route(doc, "start")
    assert result.found is False
    assert result.path == ()
    assert result.reason == cd.REASON_NO_FEASIBLE_SAFE_ROUTE


# ---------------------------------------------------------------------------
# 7. Four-graph framing documented (no new layer names)
# ---------------------------------------------------------------------------

def test_four_graph_framing_documented_in_typology_graph_md():
    text = (REPO_ROOT / "docs" / "TYPOLOGY_GRAPH.md").read_text(encoding="utf-8")
    assert "Four-graph framing" in text
    for word in ("Hydrology", "Control", "Community", "Safe/Logistics"):
        assert word in text


# ---------------------------------------------------------------------------
# structural_issues row
# ---------------------------------------------------------------------------

def test_structural_issue_row_present():
    import yaml
    doc = yaml.safe_load(
        (REPO_ROOT / "docs" / "knowledge" / "structural_issues_2026-09-28.yaml")
        .read_text(encoding="utf-8"))
    ids = {row["id"] for row in doc["issues"]}
    assert "ISSUE-WARNING-06" in ids


def test_no_hatyai_nodes_added_to_live_self_help_dag():
    """Hat Yai stays next-version scope for the live page -- this check must not add any
    Hat Yai/hatyai/songkhla node to the file the live site actually builds from."""
    doc_path = REPO_ROOT / "site" / "inputs" / "community" / "self_help_dag.yaml"
    text = doc_path.read_text(encoding="utf-8").lower()
    for banned in ("hatyai", "hat_yai", "หาดใหญ่", "songkhla"):
        assert banned not in text
