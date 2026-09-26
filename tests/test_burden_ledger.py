"""Tests for burden_ledger.py -- Toledo PROP-FLOOD-05a/05b (proposals, unverified)."""
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import burden_ledger as bl  # noqa: E402

EPS = "0.02"


def test_undeclared_structure_refused():
    r = bl.structure_burden("ghost", 1.0, 0.5, EPS, EPS, bl.STATE_CLOSED, declared=False)
    assert r.result == bl.RESULT_REFUSED
    assert bl.REASON_UNDECLARED_STRUCTURE in r.reason_codes


def test_missing_input_refused():
    r = bl.structure_burden("c1", None, 0.5, EPS, EPS, bl.STATE_CLOSED)
    assert r.result == bl.RESULT_REFUSED
    assert bl.REASON_MISSING_INPUT in r.reason_codes


def test_stale_input_refused():
    r = bl.structure_burden("c1", 1.0, 0.5, EPS, EPS, bl.STATE_CLOSED, stale_a=True)
    assert r.result == bl.RESULT_REFUSED
    assert bl.REASON_STALE_INPUT in r.reason_codes


def test_datum_mismatch_refused():
    r = bl.structure_burden("c1", 1.0, 0.5, EPS, EPS, bl.STATE_CLOSED,
                             datum_a="MSL", datum_b="ม.รทก.")
    assert r.result == bl.RESULT_REFUSED
    assert bl.REASON_DATUM_MISMATCH in r.reason_codes


def test_control_state_missing_refused():
    r = bl.structure_burden("c1", 1.0, 0.5, EPS, EPS, None)
    assert r.result == bl.RESULT_REFUSED
    assert bl.REASON_CONTROL_STATE_MISSING in r.reason_codes


def test_unknown_state_value_is_control_state_missing():
    r = bl.structure_burden("c1", 1.0, 0.5, EPS, EPS, "SOMETHING_ELSE")
    assert r.result == bl.RESULT_REFUSED
    assert bl.REASON_CONTROL_STATE_MISSING in r.reason_codes


def test_gradient_only_when_open():
    r = bl.structure_burden("c1", 1.0, 0.5, EPS, EPS, bl.STATE_OPEN)
    assert r.result == bl.RESULT_GRADIENT_ONLY
    assert r.higher_side is None and r.lower_side is None


def test_unresolved_within_combined_epsilon():
    r = bl.structure_burden("c1", "0.50", "0.51", EPS, EPS, bl.STATE_CLOSED)
    assert r.result == bl.RESULT_UNRESOLVED


def test_unresolved_exactly_at_boundary_is_not_determinate():
    # a_c == eps_sum exactly must NOT be treated as strictly greater (boundary case).
    r = bl.structure_burden("c1", "0.58", "0.62", "0.02", "0.02", bl.STATE_CLOSED)
    assert r.result == bl.RESULT_UNRESOLVED
    assert r.a_c == Fraction(-1, 25)  # -0.04


def test_higher_side_a_when_closed_and_a_higher():
    r = bl.structure_burden("c1", "1.00", "0.50", EPS, EPS, bl.STATE_CLOSED)
    assert r.result == bl.RESULT_DETERMINATE
    assert r.higher_side == bl.SIDE_A and r.lower_side == bl.SIDE_B
    assert r.burdened_side == bl.SIDE_A and r.relieved_side == bl.SIDE_B


def test_higher_side_b_when_closed_and_b_higher():
    r = bl.structure_burden("c1", "0.82", "0.96", EPS, EPS, bl.STATE_CLOSED)
    assert r.result == bl.RESULT_DETERMINATE
    assert r.higher_side == bl.SIDE_B and r.lower_side == bl.SIDE_A


def test_pumping_a_to_b_still_reads_level_not_pump_direction():
    # PUMPING(A->B) with B gauged higher still reads HIGHER_SIDE=B -- the pump's
    # declared direction is not itself an input to which side is read HIGHER_SIDE.
    r = bl.structure_burden("c1", "0.30", "0.90", EPS, EPS, bl.STATE_PUMPING_A_TO_B)
    assert r.result == bl.RESULT_DETERMINATE
    assert r.higher_side == bl.SIDE_B


def test_as_dict_shape():
    r = bl.structure_burden("c1", "1.00", "0.50", EPS, EPS, bl.STATE_CLOSED)
    d = r.as_dict()
    for key in ("structure_id", "result", "reason_codes", "state", "higher_side",
                "lower_side", "burdened_side", "relieved_side", "a_c"):
        assert key in d


# -- persistence() -----------------------------------------------------------------

def test_persistence_empty_history_is_zero():
    assert bl.persistence([]) == 0


def test_persistence_counts_consecutive_same_side():
    history = [bl.SIDE_B, bl.SIDE_B, bl.SIDE_B, bl.SIDE_B]
    assert bl.persistence(history) == 4


def test_persistence_resets_on_side_change():
    history = [bl.SIDE_A, bl.SIDE_B, bl.SIDE_B]
    assert bl.persistence(history) == 2


def test_persistence_resets_on_none_gap():
    history = [bl.SIDE_B, bl.SIDE_B, None, bl.SIDE_B]
    assert bl.persistence(history) == 1


def test_persistence_zero_when_last_tick_is_none():
    history = [bl.SIDE_B, bl.SIDE_B, None]
    assert bl.persistence(history) == 0


# -- zone_order() -------------------------------------------------------------------

def _det(structure_id, higher_side, a_c="0.10"):
    return bl.BurdenResult(structure_id, bl.RESULT_DETERMINATE, state=bl.STATE_CLOSED,
                            higher_side=higher_side,
                            lower_side=bl.SIDE_A if higher_side == bl.SIDE_B else bl.SIDE_B,
                            a_c=Fraction(a_c))


def _refused(structure_id, reason=bl.REASON_CONTROL_STATE_MISSING):
    return bl.BurdenResult(structure_id, bl.RESULT_REFUSED, reason_codes=[reason])


def _gradient(structure_id):
    return bl.BurdenResult(structure_id, bl.RESULT_GRADIENT_ONLY, state=bl.STATE_OPEN)


def test_not_evaluable_zone_with_no_boundaries():
    zones = {"z1": {"boundaries": []}}
    out = bl.zone_order(zones, {})
    assert out["not_evaluable"] == ["z1"]
    assert out["ranked"] == [] and out["no_order"] == []


def test_no_order_zone_with_refused_boundary():
    zones = {"z1": {"boundaries": [("c1", bl.SIDE_A)]}}
    readouts = {"c1": (_refused("c1"), 0)}
    out = bl.zone_order(zones, readouts)
    assert out["not_evaluable"] == []
    assert len(out["no_order"]) == 1 and out["no_order"][0]["zone_id"] == "z1"


def test_neutral_boundaries_excluded_from_r_and_b():
    zones = {"z1": {"boundaries": [("c1", bl.SIDE_A)]}}
    readouts = {"c1": (_gradient("c1"), 0)}
    out = bl.zone_order(zones, readouts)
    assert out["ranked"][0]["R"] == 0 and out["ranked"][0]["B"] == 0


def test_dense_rank_ties_share_rank_value():
    zones = {
        "z1": {"boundaries": [("c1", bl.SIDE_A)]},   # RELIEVED for z1 -> R=1,B=0
        "z2": {"boundaries": [("c2", bl.SIDE_A)]},   # RELIEVED for z2 -> R=1,B=0 (tie)
        "z3": {"boundaries": [("c3", bl.SIDE_B)]},   # BURDENED for z3 -> R=0,B=1
    }
    readouts = {
        "c1": (_det("c1", higher_side=bl.SIDE_B), 3),   # z1 side A = LOWER = RELIEVED
        "c2": (_det("c2", higher_side=bl.SIDE_B), 3),   # z2 side A = LOWER = RELIEVED (same net)
        "c3": (_det("c3", higher_side=bl.SIDE_B), 1),   # z3 side B = HIGHER = BURDENED
    }
    out = bl.zone_order(zones, readouts)
    ranks = {r["zone_id"]: r["rank"] for r in out["ranked"]}
    assert ranks["z1"] == ranks["z2"] == 1
    assert ranks["z3"] == 2  # next distinct value continues at rank+1, never rank+3


def test_sigma_p_tie_break_breaks_equal_r_minus_b():
    zones = {
        "z1": {"boundaries": [("c1", bl.SIDE_A)]},
        "z2": {"boundaries": [("c2", bl.SIDE_A)]},
    }
    readouts = {
        "c1": (_det("c1", higher_side=bl.SIDE_B), 2),
        "c2": (_det("c2", higher_side=bl.SIDE_B), 9),
    }
    out = bl.zone_order(zones, readouts)
    ranks = {r["zone_id"]: r["rank"] for r in out["ranked"]}
    # both have R=1,B=0 (net R-B=1) but z2's relieved persistence is higher -> ranks first
    assert ranks["z2"] == 1 and ranks["z1"] == 2


def test_missing_readout_for_a_boundary_forces_no_order():
    zones = {"z1": {"boundaries": [("c_missing", bl.SIDE_A)]}}
    out = bl.zone_order(zones, {})
    assert out["no_order"] and out["no_order"][0]["zone_id"] == "z1"
