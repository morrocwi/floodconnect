from datetime import datetime
from fractions import Fraction

from raw_stage_forecast import StageObs, phase_window_threshold_persistence


def obs(ts, v):
    return StageObs(datetime.fromisoformat(ts), Fraction(str(v)))


def test_two_cycle_evening_crossing_supported():
    yday = [
        obs("2026-09-26T18:50:00", 1.85),
        obs("2026-09-26T19:50:00", 1.92),
        obs("2026-09-26T20:50:00", 1.99),
        obs("2026-09-26T21:50:00", 2.02),
    ]
    today = [
        obs("2026-09-27T18:50:00", 1.95),
        obs("2026-09-27T19:50:00", 2.01),
        obs("2026-09-27T20:50:00", 2.09),
        obs("2026-09-27T21:50:00", 2.08),
    ]
    out = phase_window_threshold_persistence(today, yday, "1.95", 18, 22)
    assert out["forecast"] == "CROSS_BANK_SUPPORTED"


def test_one_cycle_only_does_not_support_crossing():
    yday = [
        obs("2026-09-26T18:50:00", 1.85),
        obs("2026-09-26T19:50:00", 1.92),
    ]
    today = [
        obs("2026-09-27T18:50:00", 1.95),
        obs("2026-09-27T19:50:00", 2.01),
    ]
    out = phase_window_threshold_persistence(today, yday, "1.95", 18, 22)
    assert out["forecast"] == "NOT_SUPPORTED"
