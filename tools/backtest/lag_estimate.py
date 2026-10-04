"""lag_estimate.py -- MEASURED travel time (lag) between two river gauges, per event.

Purpose: supply the `basis: measured` delay d_e that PROP-FLOOD-09 v1.1 (Δ1, edge booking
with a declared integer delay) needs before any inbound debt D_in can be booked for a
Bangkok-linked edge. PROP-FLOOD-09 itself says d_e may be "declared or measured
(EQ-001/P.61.v1)"; this module is the *measurement* side only. It never books debt and
never forecasts.

Equation status (repo rule, AGENTS.md §2): the three procedures below are measurement
procedures, not model equations, but they ARE formulas applied to data, so they are marked
here explicitly as **not yet in Toledo**:
  (a) centred running mean over `window` hourly ticks (used as a tide/diurnal filter);
  (b) event detection: a rising limb = a maximal run where the smoothed upstream series
      rises over the last `span_h` ticks, kept only if its total rise >= `min_rise`;
  (c) lag = argmax over integer hours L in [0, max_lag_h] of the Pearson correlation
      between the first differences of the smoothed upstream series on the event window
      and of the smoothed downstream series shifted by L.
A lag whose best correlation is < r_min, or that sits on the search boundary (0 or
max_lag_h), is reported UNRESOLVED for that event -- never coerced to a number.

Output discipline (PROP-FLOOD-09 / project decisions):
  - report per-event lags and their [min, max] range plus the number of events used --
    NEVER an average;
  - lag varies with flow (a large flood wave moves at a different speed than a small
    one) and, at tidal stations, with the tide -- a range is the honest readout;
  - zero is never a default: a pair with no resolved event is REFUSED, not 0.

Pure functions only (no network, no file writes) except `main()`, which reads the
archived raw payloads written by the 2026-09-28 fetch (raw/backtest/lag_2026-09-28/,
gitignored) and prints the per-pair results as JSON.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

Series = List[Optional[float]]


# ---------------------------------------------------------------- parsing / gridding
def load_graph_series(payload: dict, field: str) -> Dict[datetime, float]:
    """HII waterlevel_graph payload -> {timestamp: value} for one field.

    `field` is "discharge" (m3/s) or "value" (stage, m MSL-referenced per HII).
    Null readings are dropped (a missing tick stays missing; it is never 0)."""
    rows = (payload.get("data") or {}).get("graph_data") or []
    out: Dict[datetime, float] = {}
    for r in rows:
        v = r.get(field)
        if v is None:
            continue
        try:
            out[datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M")] = float(v)
        except (KeyError, ValueError, TypeError):
            continue
    return out


def hourly_grid(points: Dict[datetime, float], start: datetime, end: datetime) -> Series:
    """Bucket readings into whole hours [start, end); mean of readings inside the hour
    (10-min stations collapse to 1 value per hour). Empty hour -> None."""
    n = int((end - start).total_seconds() // 3600)
    sums = [0.0] * n
    cnts = [0] * n
    for t, v in points.items():
        i = int((t - start).total_seconds() // 3600)
        if 0 <= i < n:
            sums[i] += v
            cnts[i] += 1
    return [sums[i] / cnts[i] if cnts[i] else None for i in range(n)]


def bound_filter(xs: Series, lo: Optional[float] = None, hi: Optional[float] = None) -> Series:
    """Drop readings outside a caller-declared plausibility band (-> None). The band is a
    declared input per station (e.g. sensor spikes of several metres at a tidal gauge);
    nothing is interpolated."""
    out: Series = []
    for x in xs:
        if x is None or (lo is not None and x < lo) or (hi is not None and x > hi):
            out.append(None)
        else:
            out.append(x)
    return out


# ---------------------------------------------------------------- (a) running mean
def running_mean(xs: Series, window: int, min_frac: float = 0.8) -> Series:
    """Centred running mean over `window` ticks (not yet in Toledo). A tick gets a value
    only if >= min_frac of its window is present; otherwise None."""
    if window <= 1:
        return list(xs)
    n = len(xs)
    half_lo = window // 2
    half_hi = window - half_lo
    out: Series = [None] * n
    for i in range(n):
        a, b = max(0, i - half_lo), min(n, i + half_hi)
        vals = [x for x in xs[a:b] if x is not None]
        if (b - a) == window and len(vals) >= min_frac * window:
            out[i] = sum(vals) / len(vals)
    return out


def first_diff(xs: Series) -> Series:
    return [None] + [
        (xs[i] - xs[i - 1]) if (xs[i] is not None and xs[i - 1] is not None) else None
        for i in range(1, len(xs))
    ]


# ---------------------------------------------------------------- (b) rising limbs
def find_rising_limbs(xs: Series, min_rise: float, span_h: int = 24,
                      merge_gap_h: int = 12) -> List[Tuple[int, int]]:
    """Maximal runs of ticks where xs[i] - xs[i-span_h] > 0 (not yet in Toledo), gaps
    <= merge_gap_h merged, kept if the run's total rise (max inside run minus value at
    run start) >= min_rise. Returns [(i_start, i_end)] inclusive."""
    n = len(xs)
    rising = [False] * n
    for i in range(span_h, n):
        a, b = xs[i - span_h], xs[i]
        rising[i] = a is not None and b is not None and b - a > 0
    runs: List[List[int]] = []
    for i, r in enumerate(rising):
        if not r:
            continue
        if runs and i - runs[-1][1] <= merge_gap_h:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    out: List[Tuple[int, int]] = []
    for a, b in runs:
        start = max(0, a - span_h)
        vals = [x for x in xs[start:b + 1] if x is not None]
        x0 = xs[start]
        if x0 is None or not vals:
            continue
        if max(vals) - x0 >= min_rise:
            out.append((start, b))
    return out


# ---------------------------------------------------------------- (c) cross-correlation
def pearson(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)


def xcorr_lag(up: Series, down: Series, i0: int, i1: int, max_lag_h: int,
              min_overlap: int = 24) -> Tuple[Optional[int], Optional[float]]:
    """Best integer lag L in [0, max_lag_h] correlating diff(up)[i0..i1] with
    diff(down)[i0+L..i1+L]. Returns (L, r) or (None, None) if no lag has enough
    overlapping non-missing pairs."""
    du, dd = first_diff(up), first_diff(down)
    best: Tuple[Optional[int], Optional[float]] = (None, None)
    for L in range(0, max_lag_h + 1):
        a, b = [], []
        for i in range(i0, i1 + 1):
            j = i + L
            if j >= len(dd) or i >= len(du):
                break
            if du[i] is None or dd[j] is None:
                continue
            a.append(du[i])
            b.append(dd[j])
        if len(a) < min_overlap:
            continue
        r = pearson(a, b)
        if r is not None and (best[1] is None or r > best[1]):
            best = (L, r)
    return best


def estimate_pair(up: Series, down: Series, events: List[Tuple[int, int]], max_lag_h: int,
                  r_min: float = 0.5, pad_h: int = 24, min_overlap: int = 24) -> dict:
    """Per-event lag for one edge. Never averages. Status:
    MEASURED  -- >= 1 event resolved (report lag_min_h..lag_max_h + n_events_used);
    REFUSED   -- no event resolved (reason NO_RESOLVED_EVENT); never 0.
    An event whose rising limb starts at the first available tick of the up-series is
    UNRESOLVED_TRUNCATED: its true onset may lie before the record, so its lag is not
    aligned with the wave front."""
    first = next((i for i, x in enumerate(up) if x is not None), 0)
    per_event = []
    for (a, b) in events:
        i0, i1 = max(1, a - pad_h), min(len(up) - 1, b + pad_h)
        lag, r = xcorr_lag(up, down, i0, i1, max_lag_h, min_overlap)
        if a <= first:
            state = "UNRESOLVED_TRUNCATED"
        elif lag is None:
            state = "UNRESOLVED_NO_OVERLAP"
        elif r is None or r < r_min:
            state = "UNRESOLVED_LOW_R"
        elif lag == 0 or lag == max_lag_h:
            state = "UNRESOLVED_BOUNDARY"
        else:
            state = "RESOLVED"
        per_event.append({"i0": i0, "i1": i1, "lag_h": lag,
                          "r": None if r is None else round(r, 3), "state": state})
    used = [e for e in per_event if e["state"] == "RESOLVED"]
    if not used:
        return {"status": "REFUSED", "reason": "NO_RESOLVED_EVENT", "n_events_tried": len(per_event),
                "n_events_used": 0, "lag_min_h": None, "lag_max_h": None, "events": per_event}
    lags = [e["lag_h"] for e in used]
    return {"status": "MEASURED", "n_events_tried": len(per_event), "n_events_used": len(used),
            "lag_min_h": min(lags), "lag_max_h": max(lags), "events": per_event}


def sum_windows(windows: List[Optional[Tuple[float, float]]]) -> Optional[Tuple[float, float]]:
    """Path arrival window = element-wise sum of per-edge [min, max] (PROP-FLOOD-09 Δ1
    composed edge-by-edge over storage-free junctions). Any undeclared edge (None) makes
    the whole path None (-> REFUSED TAU_UNDECLARED upstream of the caller)."""
    lo = hi = 0.0
    for w in windows:
        if w is None:
            return None
        lo += w[0]
        hi += w[1]
    return (lo, hi)


# ---------------------------------------------------------------- CLI over archived raw
RAW = Path(__file__).resolve().parents[2] / "raw" / "backtest" / "lag_2026-09-28"
START = datetime(2025, 9, 29)
END = datetime(2026, 9, 28, 12)

# station label -> (file stem, field, plausibility band (lo, hi) or None)
STATIONS = {
    "C.2": ("C2_2795", "discharge", None),
    "C.13": ("C13_2744", "discharge", None),
    "C.7A": ("C7A_2626", "value", None),
    "C.35": ("C35_2609", "value", None),
    "C.12": ("C12_2599", "value", (-1.0, 4.0)),
    "S.28": ("S28_2712", "discharge", None),
    "S.26": ("S26_2624", "value", None),
}
# (up, down, upstream min_rise in the up-series unit, smoothing window h, max lag h)
PAIRS = [
    ("C.2", "C.13", 150.0, 25, 96),
    ("C.13", "C.7A", 150.0, 25, 96),
    ("C.7A", "C.35", 0.30, 25, 96),
    ("C.35", "C.12", 0.30, 25, 120),
    ("C.13", "C.12", 150.0, 25, 168),
    ("S.28", "S.26", 30.0, 25, 96),
    ("S.26", "C.12", 0.30, 25, 120),
]


def _series(label: str, window: int) -> Series:
    stem, field, band = STATIONS[label]
    path = next(RAW.glob(stem + "_*.json"))
    xs = hourly_grid(load_graph_series(json.loads(path.read_text()), field), START, END)
    if band:
        xs = bound_filter(xs, *band)
    return running_mean(xs, window)


def main(argv: List[str]) -> int:
    results = {}
    for up, down, min_rise, win, max_lag in PAIRS:
        su, sd = _series(up, win), _series(down, win)
        events = find_rising_limbs(su, min_rise, span_h=24)
        res = estimate_pair(su, sd, events, max_lag_h=max_lag)
        for e in res["events"]:
            e["t0"] = (START + timedelta(hours=e.pop("i0"))).strftime("%Y-%m-%d %H:00")
            e["t1"] = (START + timedelta(hours=e.pop("i1"))).strftime("%Y-%m-%d %H:00")
        res.update({"up": up, "down": down, "up_field": STATIONS[up][1],
                    "down_field": STATIONS[down][1], "smoothing_h": win, "max_lag_h": max_lag,
                    "min_rise": min_rise})
        results[f"{up}->{down}"] = res
    print(json.dumps(results, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
