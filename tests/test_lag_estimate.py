"""Tests for tools/backtest/lag_estimate.py and sources/declared_travel_times.yaml.

Fixture = a synthetic pair of hourly series built in-test (no network, no raw files):
the downstream series is the upstream series shifted by a known lag, so the estimator
must recover that lag per event and must refuse (never return 0) when there is no signal.
"""
import math
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "backtest"))

import lag_estimate as le  # noqa: E402


def _wave(n, centres, width=30.0, base=500.0, amp=800.0):
    return [base + sum(amp * math.exp(-((i - c) / width) ** 2) for c in centres) for i in range(n)]


def _shift(xs, lag):
    return [None] * lag + xs[: len(xs) - lag]


def test_load_and_grid_drop_nulls_and_bucket_hours():
    payload = {"data": {"graph_data": [
        {"datetime": "2026-09-01 00:00", "value": 1.0, "discharge": None},
        {"datetime": "2026-09-01 00:30", "value": 3.0, "discharge": 100},
        {"datetime": "2026-09-01 02:00", "value": None, "discharge": 200},
    ]}}
    v = le.load_graph_series(payload, "value")
    q = le.load_graph_series(payload, "discharge")
    assert len(v) == 2 and len(q) == 2
    grid = le.hourly_grid(v, datetime(2026, 9, 1), datetime(2026, 9, 1, 3))
    assert grid == [2.0, None, None]  # hour 0 = mean(1, 3); missing stays None, never 0


def test_bound_filter_drops_spikes_without_filling():
    assert le.bound_filter([1.0, 9.9, None, 2.0], -1.0, 4.0) == [1.0, None, None, 2.0]


def test_running_mean_needs_enough_window():
    xs = [1.0] * 10
    rm = le.running_mean(xs, 5)
    assert rm[0] is None and rm[2] == 1.0 and rm[-1] is None


def test_recovers_known_lag_per_event_and_reports_range_not_mean():
    n = 1200
    up = _wave(n, [300, 800])
    down = _shift(up, 18)
    events = le.find_rising_limbs(up, min_rise=200.0, span_h=24)
    assert len(events) == 2
    res = le.estimate_pair(up, down, events, max_lag_h=72)
    assert res["status"] == "MEASURED"
    assert res["n_events_used"] == 2
    assert res["lag_min_h"] == 18 and res["lag_max_h"] == 18
    assert "lag_mean_h" not in res and "mean" not in res  # never an average


def test_lag_range_across_events_with_different_lags():
    n = 1400
    up = _wave(n, [300, 900])
    down = [None] * n
    for i in range(n):  # event 1 travels 12 h, event 2 travels 30 h
        lag = 12 if i < 600 else 30
        if i - lag >= 0:
            down[i] = up[i - lag]
    events = le.find_rising_limbs(up, min_rise=200.0, span_h=24)
    res = le.estimate_pair(up, down, events, max_lag_h=72)
    assert res["n_events_used"] == 2
    assert (res["lag_min_h"], res["lag_max_h"]) == (12, 30)


def test_no_signal_is_refused_never_zero():
    n = 800
    up = _wave(n, [300])
    down = [1.0 + 0.3 * math.sin(2 * math.pi * i / 12.42) for i in range(n)]  # tide only
    events = le.find_rising_limbs(up, min_rise=200.0, span_h=24)
    res = le.estimate_pair(le.running_mean(up, 25), le.running_mean(down, 25), events, max_lag_h=96)
    assert res["status"] == "REFUSED"
    assert res["lag_min_h"] is None and res["lag_max_h"] is None


def test_event_at_record_start_is_truncated():
    n = 600
    up = _wave(n, [20, 400])
    down = _shift(up, 10)
    events = le.find_rising_limbs(up, min_rise=200.0, span_h=24)
    res = le.estimate_pair(up, down, events, max_lag_h=72)
    states = [e["state"] for e in res["events"]]
    assert states[0] == "UNRESOLVED_TRUNCATED"
    assert res["n_events_used"] == 1 and res["lag_min_h"] == 10


def test_sum_windows_refuses_on_any_undeclared_edge():
    assert le.sum_windows([(12, 24), (84, 96)]) == (96, 120)
    assert le.sum_windows([(12, 24), None, (24, 24)]) is None


def test_travel_time_yaml_is_consistent():
    doc = yaml.safe_load((ROOT / "sources" / "declared_travel_times.yaml").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in doc["edges"]}
    for r in doc["edges"]:
        if r["delay_min_h"] is None:
            # undeclared/unmeasured is REFUSED, never zero
            assert r["delay_max_h"] is None and r.get("state") == "REFUSED"
        else:
            assert 0 < r["delay_min_h"] <= r["delay_max_h"]
            assert r["basis"] in ("declared", "measured")
            assert r["source"] in doc["sources"]
    p = doc["paths"]
    c13 = tuple(p["node:gauge:thaiwater_waterlevel:C.13"]["bangkok_window_h"])
    dec = rows["dec_c13_to_c29a"]["delay_min_h"] + rows["dec_c29a_to_c4"]["delay_min_h"]
    mea = rows["mea_c13_to_c12"]["delay_max_h"]
    assert c13 == (min(dec, mea), max(dec, mea))
    c2 = le.sum_windows([tuple(p["node:gauge:thaiwater_waterlevel:C.2"]["hops"][0]["window_h"]), c13])
    assert c2 == tuple(p["node:gauge:thaiwater_waterlevel:C.2"]["bangkok_window_h"])
    bh = le.sum_windows([(48, 48), (24, 24), c2])
    assert bh == tuple(p["node:dam:hii_dam:1"]["bangkok_window_h"])
    sk = le.sum_windows([(48, 72), (48, 48), (6, 6), c2])
    assert sk == tuple(p["node:dam:hii_dam:12"]["bangkok_window_h"])
    for refused in ("node:dam:hii_dam:11", "node:dam:hii_dam:36", "node:dam:hii_dam:34", "node:dam:hii_dam:35"):
        assert p[refused]["bangkok_window_h"] is None
        assert "TAU_UNDECLARED" in p[refused]["bangkok_state"]
