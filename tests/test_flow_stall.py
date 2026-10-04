"""Tests for tools/flowmap/flow_stall.py -- synthetic 4-node chain (never touches the
repo's real observations.sqlite). Covers: 2 readings -> direction; a faulted sensor ->
REFUSED (no fabricated reading); stalled detection; and the inference layer added by the
founder's 2026-09-27 correction (REFUSED is the last resort, infer from strong anchors
first)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.flowmap.flow_stall import (  # noqa: E402
    Node, Edge, Reading, compute_chain, classify_landscape_type,
    EDGE_STATUS_OK, EDGE_STATUS_REFUSED, EDGE_STATUS_INFERRED,
    TREND_MOVING_UP, TREND_MOVING_DOWN, TREND_STALLED, STATUS_NO_READOUT,
    RULE_STALL_01, RULE_DIR_01,
)

REF = "2026-09-27T12:00:00+00:00"


def _chain_nodes():
    """A -> B -> C -> D, a plain 4-node canal_reach chain."""
    a = Node("a", "จุด A", "canal_reach", readings=[
        Reading(1.00, "2026-09-27T09:00:00+00:00", tag="VERIFIED_LIVE"),
        Reading(1.20, "2026-09-27T11:00:00+00:00", tag="VERIFIED_LIVE"),
    ])
    b = Node("b", "จุด B", "canal_reach", readings=[
        Reading(0.80, "2026-09-27T09:00:00+00:00", tag="VERIFIED_LIVE"),
        Reading(0.80, "2026-09-27T11:00:00+00:00", tag="VERIFIED_LIVE"),
    ])
    c = Node("c", "จุด C", "canal_reach")
    d = Node("d", "จุด D", "canal_reach", readings=[
        Reading(0.50, "2026-09-27T09:00:00+00:00", tag="VERIFIED_LIVE"),
        Reading(0.50, "2026-09-27T11:00:00+00:00", tag="VERIFIED_LIVE"),
    ])
    return {"a": a, "b": b, "c": c, "d": d}


def _chain_edges():
    return [
        Edge("e_ab", "a", "b"),
        Edge("e_bc", "b", "c"),
        Edge("e_cd", "c", "d"),
    ]


def test_two_readings_give_direction():
    nodes = _chain_nodes()
    edges = _chain_edges()
    result = compute_chain(nodes, edges, REF)
    e_ab = result.edge_flows["e_ab"]
    assert e_ab.status == EDGE_STATUS_OK
    assert e_ab.direction == "FORWARD"  # a (1.20) higher than b (0.80)


def test_stalled_node_detected():
    nodes = _chain_nodes()
    edges = _chain_edges()
    result = compute_chain(nodes, edges, REF)
    assert result.node_trends["b"].status == "OK"
    assert result.node_trends["b"].trend == TREND_STALLED
    assert result.node_trends["d"].trend == TREND_STALLED


def test_moving_trend_detected():
    nodes = _chain_nodes()
    edges = _chain_edges()
    result = compute_chain(nodes, edges, REF)
    assert result.node_trends["a"].trend == TREND_MOVING_UP


def test_faulted_sensor_never_fabricates_a_reading():
    nodes = _chain_nodes()
    nodes["a"].readings = [
        Reading(1.00, "2026-09-27T09:00:00+00:00", sensor_status="faulted"),
        Reading(1.20, "2026-09-27T11:00:00+00:00", sensor_status="faulted"),
    ]
    edges = _chain_edges()
    result = compute_chain(nodes, edges, REF)
    assert result.node_trends["a"].status == STATUS_NO_READOUT
    assert "MISSING_INPUT" in result.node_trends["a"].reason_codes
    # edge a-b needs a's reading -- must REFUSE, never guess a direction
    assert result.edge_flows["e_ab"].status in (EDGE_STATUS_REFUSED, EDGE_STATUS_INFERRED)
    if result.edge_flows["e_ab"].status == EDGE_STATUS_REFUSED:
        assert "MISSING_INPUT" in result.edge_flows["e_ab"].reason_codes


def test_no_readings_at_all_is_refused_not_guessed():
    nodes = {"a": Node("a", "A", "canal_reach"), "b": Node("b", "B", "canal_reach")}
    edges = [Edge("e_ab", "a", "b")]
    result = compute_chain(nodes, edges, REF)
    assert result.node_trends["a"].status == STATUS_NO_READOUT
    assert result.edge_flows["e_ab"].status == EDGE_STATUS_REFUSED
    assert result.edge_flows["e_ab"].inferred is False


def test_inference_stall_rule_when_anchors_agree_no_pump_and_community_report():
    """Founder correction (2026-09-27): a pond with 0 measured pumps running, a
    persistently-flat downstream anchor, and a community 'no drop' report should infer
    the un-gauged link between them as STALLED, not REFUSED."""
    downstream = Node("canal", "คลองนอก", "canal_reach", readings=[
        Reading(-0.12, "2026-09-26T06:00:00+00:00", tag="VERIFIED_LIVE"),
        Reading(-0.11, "2026-09-26T18:00:00+00:00", tag="VERIFIED_LIVE"),
        Reading(-0.12, "2026-09-27T11:00:00+00:00", tag="VERIFIED_LIVE"),
    ])
    pond = Node("pond", "บึง", "pond")  # no public gauge -- OPEN
    nodes = {"pond": pond, "canal": downstream}
    edges = [Edge("e_pond_canal", "pond", "canal", pumps_on=0, pumps_total=11,
                   pump_source_tag="VERIFIED_LIVE")]
    reports = [{"node_id": "pond", "no_drop": True, "tag": "COMMUNITY",
                "report_id": "r1", "observed_at": REF}]
    result = compute_chain(nodes, edges, REF, community_reports=reports,
                            persistence_hours=30.0)
    ef = result.edge_flows["e_pond_canal"]
    assert ef.status == EDGE_STATUS_INFERRED
    assert ef.rule_id == RULE_STALL_01
    assert ef.direction == TREND_STALLED
    nt = result.node_trends["pond"]
    assert nt.inferred is True
    assert nt.trend == TREND_STALLED


def test_inference_direction_rule_when_both_anchors_agree():
    nodes = {
        "up": Node("up", "ต้นน้ำ", "canal_reach", readings=[
            Reading(0.10, "2026-09-27T10:00:00+00:00", tag="VERIFIED_LIVE"),
            Reading(0.30, "2026-09-27T11:30:00+00:00", tag="VERIFIED_LIVE"),
        ]),
        "mid": Node("mid", "กลาง", "canal_reach"),
        "down": Node("down", "ปลายน้ำ", "canal_reach", readings=[
            Reading(-0.10, "2026-09-27T10:00:00+00:00", tag="VERIFIED_LIVE"),
            Reading(0.05, "2026-09-27T11:30:00+00:00", tag="VERIFIED_LIVE"),
        ]),
    }
    edges = [Edge("e_up_mid", "up", "mid"), Edge("e_mid_down", "mid", "down")]
    result = compute_chain(nodes, edges, REF)
    assert result.node_trends["mid"].inferred is True
    assert result.node_trends["mid"].rule_id == RULE_DIR_01
    assert result.node_trends["mid"].trend == TREND_MOVING_UP
    assert result.edge_flows["e_up_mid"].status == EDGE_STATUS_INFERRED


def test_next_measurement_recommends_highest_information_gain_node():
    nodes = _chain_nodes()  # c has no reading, bounded by b (stalled) and d (stalled)
    edges = _chain_edges()
    result = compute_chain(nodes, edges, REF)
    ids = [r.node_id for r in result.next_measurement]
    assert "c" in ids  # c is the node whose reading would resolve edges around it


def test_backflow_flag_when_measured_disagrees_with_declared_direction():
    """RELAYED-via-KlongMap-schema convention: a declared design/normal direction that
    disagrees with a live-measured direction is a backflow signal -- must be flagged,
    never silently overwritten by either side."""
    nodes = {
        "a": Node("a", "A", "canal_reach", readings=[
            Reading(0.10, "2026-09-27T09:00:00+00:00"),
            Reading(0.10, "2026-09-27T11:00:00+00:00"),
        ]),
        "b": Node("b", "B", "canal_reach", readings=[
            Reading(0.40, "2026-09-27T09:00:00+00:00"),
            Reading(0.40, "2026-09-27T11:00:00+00:00"),
        ]),
    }
    # design says a -> b ("forward"); measured a(0.10) < b(0.40) is REVERSE (b -> a)
    edges = [Edge("e_ab", "a", "b", flow_direction_state="forward")]
    result = compute_chain(nodes, edges, REF)
    ef = result.edge_flows["e_ab"]
    assert ef.direction == "REVERSE"
    assert ef.declared_direction == "forward"
    assert ef.backflow_flag is True


def test_no_backflow_flag_when_declared_direction_unknown():
    nodes = {
        "a": Node("a", "A", "canal_reach", readings=[
            Reading(0.10, "2026-09-27T09:00:00+00:00"),
            Reading(0.10, "2026-09-27T11:00:00+00:00"),
        ]),
        "b": Node("b", "B", "canal_reach", readings=[
            Reading(0.40, "2026-09-27T09:00:00+00:00"),
            Reading(0.40, "2026-09-27T11:00:00+00:00"),
        ]),
    }
    edges = [Edge("e_ab", "a", "b")]  # no declared direction at all
    result = compute_chain(nodes, edges, REF)
    ef = result.edge_flows["e_ab"]
    assert ef.declared_direction is None
    assert ef.backflow_flag is False


def test_chain_order_from_profile_orders_declared_then_open():
    from tools.flowmap.flow_stall import chain_order_from_profile
    nodes = {
        "z": Node("z", "Z", "canal_reach", profile_order=2),
        "y": Node("y", "Y", "canal_reach"),  # OPEN -- no profile_order
        "x": Node("x", "X", "canal_reach", profile_order=1),
    }
    order = chain_order_from_profile(nodes, ["z", "y", "x"])
    assert order == ["x", "z", "y"]


def test_classify_landscape_type_is_always_marked_inferred():
    nodes = _chain_nodes()
    edges = _chain_edges()
    result = compute_chain(nodes, edges, REF)
    label = classify_landscape_type(nodes, edges, result.node_trends)
    assert label["inferred"] is True
    assert isinstance(label["anchors"], list)
    assert label["type_id"] in range(1, 7)
