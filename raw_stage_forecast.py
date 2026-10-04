#!/usr/bin/env python3
"""LEGACY/STANDALONE EXPERIMENT -- not called by `floodconnect forecast`
(`kb.py::cmd_forecast`), `floodconnect answer` (`kb.py::cmd_answer`/`build_answer`), or
any MCP tool. The real forecast path FloodConnect ships is `kb.py::cmd_forecast`
(rain-per-model, relayed from Open-Meteo/MET Norway). Do not judge FloodConnect's
forecasting skill from this file alone -- see docs/EVIDENCE.md (where present) and
`kb.py::cmd_forecast` for what is actually wired and answered.

raw_stage_forecast.py -- transparent stage-only prospective helper.

This module deliberately excludes all derived alert fields such as:
- "แนวโน้มถึงตลิ่งใน 24 ชม."
- FloodWatch 24 h forecast
- alert severity labels

It accepts only timestamped raw stage observations and an independently declared bank
level. It is NOT a hydraulic model and NOT a Toledo theorem.

The default readout is intentionally conservative:
1. phase-match the latest complete daily cycle against the previous complete daily cycle;
2. compute same-hour 24 h deltas;
3. report observed persistence/uplift only;
4. forecast only a threshold event that is supported in BOTH of the two latest comparable
   cycles at the corresponding phase window.

No linear extrapolation is used by default.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from typing import Iterable


@dataclass(frozen=True)
class StageObs:
    time: datetime
    stage_m: Fraction


def q(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(str(x))


def same_hour_deltas(today: Iterable[StageObs], yesterday: Iterable[StageObs]) -> list[dict]:
    prev = {(x.time.hour, x.time.minute): x for x in yesterday}
    out = []
    for x in today:
        key = (x.time.hour, x.time.minute)
        if key not in prev:
            continue
        y = prev[key]
        out.append({
            "time": x.time.isoformat(),
            "stage_today_m": str(x.stage_m),
            "stage_yesterday_m": str(y.stage_m),
            "delta_24h_m": str(x.stage_m - y.stage_m),
        })
    return out


def phase_window_threshold_persistence(
    today: Iterable[StageObs],
    yesterday: Iterable[StageObs],
    bank_m,
    start_hour: int,
    end_hour: int,
) -> dict:
    """Threshold persistence criterion, no trend extrapolation.

    A future phase-window crossing is called SUPPORTED only if BOTH of the last two
    observed daily cycles crossed the bank in the same phase window.

    This is a persistence forecast, not a hydraulic forecast.
    """
    bank = q(bank_m)

    def vals(rows):
        return [x.stage_m for x in rows if start_hour <= x.time.hour <= end_hour]

    a = vals(today)
    b = vals(yesterday)
    if not a or not b:
        return {"status": "REFUSED", "reason": "INSUFFICIENT_PHASE_MATCHED_OBSERVATIONS"}

    max_today = max(a)
    max_yday = max(b)
    supported = max_today >= bank and max_yday >= bank

    return {
        "status": "OK",
        "method": "two-cycle phase-window threshold persistence",
        "bank_m": str(bank),
        "window_hours": [start_hour, end_hour],
        "latest_cycle_max_m": str(max_today),
        "previous_cycle_max_m": str(max_yday),
        "forecast": "CROSS_BANK_SUPPORTED" if supported else "NOT_SUPPORTED",
        "claim_boundary": (
            "No linear extrapolation; this predicts threshold recurrence only if the same "
            "phase window crossed bank in both of the two latest observed cycles."
        ),
    }
