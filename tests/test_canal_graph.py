"""Tests for canal_graph.py -- Toledo PROP-FLOOD-04 (proposal, unverified)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import canal_graph as cg  # noqa: E402

REF = "2026-09-26T13:00:00+00:00"


def _node(code=None, is_gate=False, datum="MSL"):
    return {"canal_oldcode": code, "is_gate": is_gate, "datum": datum}


def _reading(level_m, observed_at=REF, canal_out=None):
    return {"level_m": level_m, "observed_at": observed_at, "canal_out": canal_out}


def _edge(edge_id="e_u_v", u="u", v="v", design_direction="u_to_v", control_structures=None):
    return {"edge_id": edge_id, "u": u, "v": v, "design_direction": design_direction,
            "design_direction_source": "test", "control_structures": control_structures or []}


def test_forward_when_u_higher():
    r = cg.edge_direction(_edge(), _node("A"), _node("B"),
                           _reading(1.00), _reading(0.50), REF)
    assert r.status == cg.STATUS_OK
    assert r.direction == cg.DIR_FORWARD


def test_reverse_when_v_higher():
    r = cg.edge_direction(_edge(), _node("A"), _node("B"),
                           _reading(0.50), _reading(1.00), REF)
    assert r.status == cg.STATUS_OK
    assert r.direction == cg.DIR_REVERSE


def test_unresolved_within_epsilon():
    r = cg.edge_direction(_edge(), _node("A"), _node("B"),
                           _reading(0.50), _reading(0.51), REF, epsilon_m="0.02")
    assert r.status == cg.STATUS_OK
    assert r.direction == cg.DIR_UNRESOLVED


def test_missing_input_when_no_gauge_declared():
    r = cg.edge_direction(_edge(), _node(None), _node("B"),
                           None, _reading(0.50), REF)
    assert r.status == cg.STATUS_REFUSED
    assert cg.REASON_MISSING_INPUT in r.reason_codes
    # design_direction is always carried through even when refused
    assert r.design_direction == "u_to_v"


def test_missing_input_when_code_not_found_in_live_data():
    r = cg.edge_direction(_edge(), _node("A"), _node("B"),
                           None, _reading(0.50), REF)
    assert r.status == cg.STATUS_REFUSED
    assert cg.REASON_MISSING_INPUT in r.reason_codes


def test_stale_input():
    old_reading = _reading(1.00, observed_at="2026-09-26T08:00:00+00:00")  # 5h before REF
    r = cg.edge_direction(_edge(), _node("A"), _node("B"),
                           old_reading, _reading(0.50), REF, stale_after_hours=2.0)
    assert r.status == cg.STATUS_REFUSED
    assert cg.REASON_STALE_INPUT in r.reason_codes


def test_datum_mismatch():
    r = cg.edge_direction(_edge(), _node("A", datum="MSL"), _node("B", datum="ม.รทก."),
                           _reading(1.00), _reading(0.50), REF)
    assert r.status == cg.STATUS_REFUSED
    assert cg.REASON_DATUM_MISMATCH in r.reason_codes


def test_controlled_when_gate_out_exceeds_in():
    gate_reading = _reading(0.58, canal_out=0.62)  # out > in -> locked
    r = cg.edge_direction(_edge(u="gate", v="B"), _node("A", is_gate=True), _node("B"),
                           gate_reading, _reading(0.30), REF)
    assert r.status == cg.STATUS_CONTROLLED
    assert r.locked_node == "gate"
    assert r.direction is None


def test_not_controlled_when_gate_out_not_exceeding_in():
    gate_reading = _reading(0.78, canal_out=0.62)  # out < in -> not locked, falls through
    r = cg.edge_direction(_edge(u="gate", v="B"), _node("A", is_gate=True), _node("B"),
                           gate_reading, _reading(0.30), REF)
    assert r.status == cg.STATUS_OK
    assert r.direction == cg.DIR_FORWARD


def test_undeclared_edge_refused():
    r = cg.edge_direction(_edge(edge_id="ghost"), _node("A"), _node("B"),
                           _reading(1.0), _reading(0.5), REF, declared_edges={"e_real"})
    assert r.status == cg.STATUS_REFUSED
    assert cg.REASON_UNDECLARED_EDGE in r.reason_codes


def test_compute_all_edges_runs_every_declared_edge():
    graph = {
        "sensor_resolution_m": {"value": 0.02},
        "stale_after_hours": 2.0,
        "nodes": {
            "a": _node("WL.A.01"),
            "b": _node("WL.B.01"),
            "c": _node(None),
        },
        "edges": [
            _edge(edge_id="e1", u="a", v="b"),
            _edge(edge_id="e2", u="b", v="c"),
        ],
    }
    canal_by_code = {
        "WL.A.01": _reading(1.00),
        "WL.B.01": _reading(0.50),
    }
    results = cg.compute_all_edges(graph, canal_by_code, REF)
    assert len(results) == 2
    by_id = {r.edge_id: r for r in results}
    assert by_id["e1"].status == cg.STATUS_OK
    assert by_id["e1"].direction == cg.DIR_FORWARD
    assert by_id["e2"].status == cg.STATUS_REFUSED  # node c has no gauge
    assert cg.REASON_MISSING_INPUT in by_id["e2"].reason_codes


def test_as_dict_shape():
    r = cg.edge_direction(_edge(), _node("A"), _node("B"), _reading(1.0), _reading(0.5), REF)
    d = r.as_dict()
    for key in ("edge_id", "u", "v", "status", "reason_codes", "direction", "delta_m",
                "locked_node", "design_direction", "design_direction_source",
                "control_structures"):
        assert key in d
