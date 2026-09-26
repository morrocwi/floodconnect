"""Tests for water_balance.py -- Toledo PROP-FLOOD-03 (proposal, unverified; PR #60
pending). Covers every REFUSED reason code plus the OK/trend branches. No network."""
from fractions import Fraction

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import water_balance as wb  # noqa: E402


def make_inputs(**overrides):
    base = dict(
        node_id="sammakorn", tick_index=0, tick_time="2026-09-26T12:00:00+00:00",
        S0=Fraction(2000), A=Fraction(10000), c=Fraction(1, 2), tau=Fraction(3600),
        C_pump=Fraction(1),
        P=Fraction(1, 100), P_observed_at="2026-09-26T11:30:00+00:00",
        gate_flag="OPEN", gate_flag_observed_at="2026-09-26T11:30:00+00:00",
        Q_out_meas=Fraction(1, 2), Q_out_observed_at="2026-09-26T11:30:00+00:00",
        inflow_edges=[], declared_edges=set(),
    )
    base.update(overrides)
    return wb.WaterBalanceInputs(**base)


def test_ok_basic_computation_exact_fraction():
    inp = make_inputs()
    res = wb.step(inp)
    assert res.refused is False
    # increment = P*A*c + Q_in*tau - Q_out*tau = 0.01*10000*0.5 + 0 - 0.5*3600
    #           = 50 - 1800 = -1750
    assert res.increment == Fraction(50) - Fraction(1800)
    assert res.S_next == Fraction(2000) - Fraction(1750)


def test_ok_uses_s_prev_not_s0_after_first_tick():
    inp = make_inputs(tick_index=1, S0=None)
    res = wb.step(inp, S_prev=Fraction(5000))
    assert res.refused is False
    assert res.S_next == Fraction(5000) + res.increment


def test_missing_s0_refused_on_first_tick():
    inp = make_inputs(S0=None)
    res = wb.step(inp, S_prev=None)
    assert res.refused is True
    assert "MISSING_INPUT" in res.reason_codes
    assert "S0" in res.inputs_missing


def test_undeclared_area_reason_present_when_a_missing():
    inp = make_inputs(A=None)
    res = wb.step(inp)
    assert res.refused is True
    assert "UNDECLARED_AREA" in res.reason_codes
    assert "MISSING_INPUT" in res.reason_codes


def test_missing_c_refused():
    inp = make_inputs(c=None)
    res = wb.step(inp)
    assert res.refused is True
    assert "MISSING_INPUT" in res.reason_codes
    assert "c" in res.inputs_missing


def test_missing_c_pump_refused():
    inp = make_inputs(C_pump=None)
    res = wb.step(inp)
    assert res.refused is True
    assert "C_pump" in res.inputs_missing


def test_missing_p_refused():
    inp = make_inputs(P=None)
    res = wb.step(inp)
    assert res.refused is True
    assert "P" in res.inputs_missing


def test_missing_gate_flag_refused():
    inp = make_inputs(gate_flag=None)
    res = wb.step(inp)
    assert res.refused is True
    assert "gate_flag" in res.inputs_missing


def test_missing_q_out_meas_refused_when_gate_open():
    inp = make_inputs(Q_out_meas=None)
    res = wb.step(inp)
    assert res.refused is True
    assert "Q_out_meas" in res.inputs_missing


def test_stale_rain_refused():
    inp = make_inputs(P_observed_at="2026-09-26T08:00:00+00:00")  # 4h before tick_time
    res = wb.step(inp)
    assert res.refused is True
    assert "STALE_INPUT" in res.reason_codes


def test_stale_gate_flag_refused():
    inp = make_inputs(gate_flag_observed_at="2026-09-26T08:00:00+00:00")
    res = wb.step(inp)
    assert res.refused is True
    assert "STALE_INPUT" in res.reason_codes


def test_static_declarations_never_stale_even_if_they_had_a_timestamp():
    # A/c/tau/C_pump are static -- require() is called with static=True and never
    # checked for staleness even conceptually; this test locks that in by using an
    # otherwise-fresh input set and confirming no STALE_INPUT leaks in.
    inp = make_inputs()
    res = wb.step(inp)
    assert res.refused is False
    assert "STALE_INPUT" not in res.reason_codes


def test_undeclared_edge_refused_never_treated_as_zero():
    inp = make_inputs(
        inflow_edges=[wb.InflowEdge(edge_id="upstream_x", q_in=Fraction(5),
                                     observed_at="2026-09-26T11:30:00+00:00")],
        declared_edges=set(),  # upstream_x not declared
    )
    res = wb.step(inp)
    assert res.refused is True
    assert "UNDECLARED_EDGE" in res.reason_codes
    assert "edge:upstream_x" in res.inputs_missing


def test_declared_edge_missing_reading_refused():
    inp = make_inputs(declared_edges={"upstream_x"}, inflow_edges=[])
    res = wb.step(inp)
    assert res.refused is True
    assert "MISSING_INPUT" in res.reason_codes
    assert "Q_in" in res.inputs_missing


def test_declared_edge_with_reading_included_in_sum():
    inp = make_inputs(
        declared_edges={"upstream_x"},
        inflow_edges=[wb.InflowEdge(edge_id="upstream_x", q_in=Fraction(2),
                                     observed_at="2026-09-26T11:30:00+00:00")],
    )
    res = wb.step(inp)
    assert res.refused is False
    # increment now includes Q_in_total*tau = 2*3600 extra vs the no-edge case
    base = wb.step(make_inputs())
    assert res.increment == base.increment + Fraction(2) * Fraction(3600)


def test_gate_closed_forces_zero_outflow_even_if_q_out_meas_present():
    inp = make_inputs(gate_flag="CLOSED")
    res = wb.step(inp)
    assert res.refused is False
    # increment = P*A*c + 0 - 0 = 50
    assert res.increment == Fraction(50)


def test_q_out_capped_by_c_pump():
    inp = make_inputs(Q_out_meas=Fraction(100), C_pump=Fraction(1, 4))
    res = wb.step(inp)
    assert res.refused is False
    # Q_out = min(100, 0.25) = 0.25; increment = 50 - 0.25*3600 = 50 - 900
    assert res.increment == Fraction(50) - Fraction(900)


def test_negative_storage_refused_not_clamped():
    inp = make_inputs(S0=Fraction(1), Q_out_meas=Fraction(10), C_pump=Fraction(10))
    res = wb.step(inp)
    assert res.refused is True
    assert res.reason_codes == ["NEGATIVE_STORAGE"]
    assert res.S_next is None  # never clamped to 0


def test_trend_rising_when_increment_positive():
    inp = make_inputs(gate_flag="CLOSED")  # increment = +50, no prior increment
    res = wb.step(inp, trend_epsilon=Fraction(0))
    assert res.trend == wb.TREND_RISING


def test_trend_falling_when_increment_negative():
    inp = make_inputs()  # default: increment = -1750
    res = wb.step(inp, trend_epsilon=Fraction(0))
    assert res.trend == wb.TREND_FALLING


def test_trend_flat_within_epsilon_of_previous_increment():
    inp = make_inputs()
    res = wb.step(inp, prev_increment=Fraction(-1750), trend_epsilon=Fraction(1))
    assert res.trend == wb.TREND_FLAT


def test_all_arithmetic_is_exact_fraction_never_float():
    inp = make_inputs(P=Fraction(1, 3), A=Fraction(7), c=Fraction(1, 7))
    res = wb.step(inp)
    assert isinstance(res.increment, Fraction)
    assert isinstance(res.S_next, Fraction)
    # 1/3 * 7 * 1/7 = 1/3 exactly -- would not be exact in float
    assert res.increment == Fraction(1, 3) - Fraction(1800)


def test_step_result_as_dict_never_both_value_and_refusal():
    inp = make_inputs()
    ok = wb.step(inp)
    d_ok = ok.as_dict()
    assert d_ok["status"] == "OK"
    assert d_ok["S_next"] is not None
    assert d_ok["reason_codes"] == []

    bad = wb.step(make_inputs(A=None))
    d_bad = bad.as_dict()
    assert d_bad["status"] == "REFUSED"
    assert d_bad["S_next"] is None
    assert len(d_bad["reason_codes"]) > 0
