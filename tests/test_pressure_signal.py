"""Fixture tests for tools/backtest/pressure_signal.py (pure functions, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "backtest"))
import pressure_signal as ps  # noqa: E402


def hours(day, n=24, start=0):
    return [f"{day}T{h:02d}:00" for h in range(start, start + n)]


def test_lag_diff_no_readout_and_same_hour():
    s = [1010.0] * 24 + [1007.5] * 24
    d = ps.lag_diff(s, 24)
    assert d[:24] == [None] * 24                 # t < k -> NO_READOUT
    assert d[24] == -2.5 and d[47] == -2.5
    s2 = list(s)
    s2[3] = None
    assert ps.lag_diff(s2, 24)[27] is None       # missing tick never read as FLAT


def test_rolling_sum_requires_full_window():
    assert ps.rolling_sum([1, 2, None, 4, 5], 2) == [None, 3, None, None, 9]


def test_persisted_needs_p_consecutive():
    assert ps.persisted([True, False, True, True, None, True]) == [False, False, False, True, False, False]


def test_episodes_merge_within_gap():
    flags = [False] * 200
    for i in (10, 11, 50, 150):
        flags[i] = True
    assert ps.episodes(flags, gap=72) == [(10, 50), (150, 150)]


def test_score_event_hit_miss_unresolved():
    fire = [False] * 100
    fire[60] = True
    avail = [True] * 100
    hit = ps.score_event(80, fire, avail)
    assert hit["cell"] == "HIT" and hit["lead_h"] == 20 and hit["horizons"] == ["0-24h"]
    assert ps.score_event(50, fire, avail)["cell"] == "MISS"
    avail[45] = False
    unres = ps.score_event(50, fire, avail)
    assert unres["cell"] == "UNRESOLVED"         # never a correct negative


def test_score_event_long_lead_bucket():
    fire = [False] * 200
    fire[100] = True
    r = ps.score_event(160, fire, [True] * 200)
    assert r["lead_h"] == 60 and r["horizons"] == ["48-72h"]


def test_classify_alarms():
    events = [(100, 110)]
    out = ps.classify_alarms([(50, 52), (105, 106), (300, 301)], events)
    assert [c for *_, c in out] == ["HIT_ALARM", "DURING_EVENT", "FALSE_ALARM"]


def test_ordinary_day_rate_blocks_event_days():
    times = hours("2020-01-01") + hours("2020-01-02") + hours("2020-01-03") + hours("2020-01-04") \
        + hours("2020-01-05") + hours("2020-01-06") + hours("2020-01-07") + hours("2020-01-08")
    fire = [False] * len(times)
    fire[5] = True                                # fired on 01-01
    events = [(24 * 6 + 10, 24 * 6 + 12)]         # onset 01-07 10:00 -> blocks 01-04..01-08
    r = ps.ordinary_day_rate(times, fire, events, 0, len(times) - 1)
    assert r["ordinary_days"] == 3 and r["fired_days"] == 1


def test_choose_respects_ceiling_then_lower_rate():
    mk = lambda hit, rate: {"counts": {"HIT": hit}, "base": {"rate": rate}}
    lab, _ = ps.choose([("a", mk(5, 0.20)), ("b", mk(3, 0.04)), ("c", mk(3, 0.01)), ("d", mk(1, 0.0))])
    assert lab == "c"
    assert ps.choose([("a", mk(5, 0.2))]) == (None, None)


def test_verdict_few_events():
    assert ps.verdict(7, 2, 7, 0) == "REFUSED FEW_EVENTS"
    assert ps.verdict(12, 3, 5, 0) == "NO_ADDED_SKILL"
    assert ps.verdict(12, 3, 5, 2).startswith("ADDS_SKILL")


def test_chance_hit_prob():
    assert ps.chance_hit_prob(0.0) == 0.0
    assert abs(ps.chance_hit_prob(0.5, 3) - 0.875) < 1e-12
    assert ps.chance_hit_prob(None) is None


def test_climatology_and_anomaly_use_training_only():
    times = ["2010-09-01T07:00", "2011-09-01T07:00", "2020-09-01T07:00"]
    p = [1008.0, 1010.0, 1000.0]
    clim = ps.climatology(times, p, "2005-01-01T00:00", "2017-12-31T23:00")
    assert clim == {(9, 7): 1009.0}
    assert ps.anomaly(times, p, clim)[2] == -9.0


def test_model_day_flags_tide_resolution_guard():
    tide = [0.0, -0.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 1.5, 1.0, 0.5, 0.0,
            -0.5, -1.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 1.0, 0.5, 0.0]
    day1 = [1010.0 + x for x in tide]              # hourly model output, tide resolved
    day2 = [1010.0] * 24                           # 6-hourly step interpolated: tide gone
    for h in (1, 7, 13, 19):                       # synoptic hours keep the real value
        day2[h] = day1[h]
    times = hours("2026-10-03") + hours("2026-10-04")
    out = ps.model_day_flags(times, day1 + day2, ["2026-10-04"], dp_thr=1.4)
    row = out["2026-10-04"]
    assert row["min_dp24"] == -1.5 and row["min_dp24_syn"] == 0.0
    assert row["flags"] == ["DP24_ALLHOUR_ONLY"]  # an artifact, not a pressure fall
    real = ps.model_day_flags(times, day1 + [v - 3.0 for v in day1], ["2026-10-04"], dp_thr=2.5)
    assert real["2026-10-04"]["flags"] == ["DP24"]
