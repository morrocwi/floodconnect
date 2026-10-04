"""Pressure-based leading signal for Bangkok heavy rain -- real-data held-out test.

Question (founder, 2026-09-28): does a falling / low mean-sea-level pressure readout at
Bangkok warn of heavy rain (and urban flooding) BEFORE it happens, and does it add anything
over a rain-only baseline?

Signals (all finite retained differences over hourly ticks; no continuum object):
  dp24(t)  := p(t) - p(t-24)             PROP-FLOOD-01 lag-k retained difference, k = 24 ticks.
                                          Same clock hour -> the twice-daily pressure tide cancels.
  anom(t)  := p(t) - clim(cell, month, hour)   clim = mean over TRAINING years only (no leak).
  rain24(t):= sum of the 24 hourly precipitation readouts ending at t (rain-only baseline input).
City readout = worst cell (min over cells for pressure, max over cells for rain).

Firing rule of a promoter row: raw(t) true -> persisted after p = 2 consecutive ticks
(PROP-FLOOD-06 hysteresis default). Thresholds are chosen ONLY on the training period from a
grid declared in GRIDS, by: maximise training event hits subject to
ordinary-day firing rate <= FA_DAY_CEILING (declared before the scan); tie -> lower day rate.

Scoring (PROP-FLOOD-10 delta 10.3 semantics): per event HIT / MISS / UNRESOLVED (no readout in
the window -> UNRESOLVED, never a correct negative); alarm episodes that are not followed by an
event within the window are FALSE_ALARM. Cells are listed per event and never averaged;
skill claim REFUSED FEW_EVENTS when independent held-out events < N_MIN.

Pure functions only in the core; `main()` reads cached raw payloads (no network here).
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
from pathlib import Path

WINDOW_H = 72            # look-back window before onset in which a firing counts as a warning
PERSIST_P = 2            # PROP-FLOOD-06 hysteresis default p
EVENT_MM_24H = 80.0      # BMA design depth per 24 h (plan p.63, VERIFIED upstream)
EPISODE_GAP_H = 72       # crossings closer than this are one meteorological episode
ALARM_MERGE_GAP_H = 24   # firing runs closer than this are one alarm episode
FA_DAY_CEILING = 0.05    # declared before the scan (INSTINCT)
N_MIN = 10               # provisional, PROP-FLOOD-10 leaves N_min OPEN
TRAIN = ("2005-01-01T00:00", "2017-12-31T23:00")
HELD = ("2018-01-01T00:00", "2026-09-27T23:00")
GRIDS = {
    "dp24_hpa": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
    "anom_hpa": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
    "rain24_mm": [20.0, 30.0, 40.0, 50.0, 60.0, 70.0],
}


# ----------------------------------------------------------------- pure core
def lag_diff(series, k):
    """PROP-FLOOD-01 Delta_k: None (NO_READOUT) when t<k or either tick missing."""
    out = [None] * len(series)
    for t in range(k, len(series)):
        a, b = series[t], series[t - k]
        if a is not None and b is not None:
            out[t] = round(a - b, 1)
    return out


def rolling_sum(series, w):
    out = [None] * len(series)
    for t in range(w - 1, len(series)):
        win = series[t - w + 1:t + 1]
        if all(v is not None for v in win):
            out[t] = round(sum(win), 1)
    return out


def climatology(times, p, lo, hi):
    """mean p per (month, hour) over ticks with lo <= time <= hi (ISO local strings)."""
    acc = {}
    for t, v in zip(times, p):
        if v is None or t < lo or t > hi:
            continue
        key = (int(t[5:7]), int(t[11:13]))
        s, n = acc.get(key, (0.0, 0))
        acc[key] = (s + v, n + 1)
    return {k: s / n for k, (s, n) in acc.items()}


def anomaly(times, p, clim):
    out = []
    for t, v in zip(times, p):
        c = clim.get((int(t[5:7]), int(t[11:13])))
        out.append(None if v is None or c is None else round(v - c, 1))
    return out


def worst(series_list, fn):
    out = []
    for vals in zip(*series_list):
        got = [v for v in vals if v is not None]
        out.append(fn(got) if got else None)
    return out


def persisted(raw, p=PERSIST_P):
    """raw: list of True/False/None. Fires at t iff raw true at t-p+1..t (None breaks the run)."""
    out, run = [], 0
    for v in raw:
        run = run + 1 if v is True else 0
        out.append(run >= p)
    return out


def episodes(flags, gap=EPISODE_GAP_H):
    """indices where flags true -> list of (onset_idx, last_idx), crossings within gap merged."""
    eps = []
    for i, f in enumerate(flags):
        if not f:
            continue
        if eps and i - eps[-1][1] <= gap:
            eps[-1][1] = i
        else:
            eps.append([i, i])
    return [tuple(e) for e in eps]


def score_event(onset, fire, raw_avail, window=WINDOW_H):
    """HIT/MISS/UNRESOLVED for one event onset index; lead in ticks = onset - first firing."""
    lo = max(0, onset - window)
    idx = [i for i in range(lo, onset) if fire[i]]
    if idx:
        lead = onset - idx[0]
        buckets = sorted({min(3, (onset - i - 1) // 24 + 1) for i in idx})
        return {"cell": "HIT", "lead_h": lead, "horizons": [f"{24*(b-1)}-{24*b}h" for b in buckets]}
    if not all(raw_avail[i] for i in range(lo, onset)):
        return {"cell": "UNRESOLVED", "lead_h": None, "horizons": [], "why": "NO_READOUT in window"}
    return {"cell": "MISS", "lead_h": None, "horizons": []}


def alarm_episodes(fire, gap=ALARM_MERGE_GAP_H):
    return episodes(fire, gap)


def classify_alarms(alarms, event_eps, window=WINDOW_H):
    """HIT_ALARM (an onset follows within window), DURING_EVENT (starts inside an episode or
    <=24 h after it), FALSE_ALARM otherwise."""
    out = []
    for s, e in alarms:
        cls = "FALSE_ALARM"
        for on, last in event_eps:
            if s < on <= s + window:
                cls = "HIT_ALARM"
                break
            if on <= s <= last + 24:
                cls = "DURING_EVENT"
                break
        out.append((s, e, cls))
    return out


def ordinary_day_rate(times, fire, event_eps, lo_i, hi_i):
    """share of calendar days in [lo_i, hi_i] that are ordinary (no episode from 3 days before
    onset to 1 day after its end) and on which the signal fired at least once."""
    blocked = set()
    for on, last in event_eps:
        for i in range(max(0, on - 72), min(len(times), last + 25)):
            blocked.add(times[i][:10])
    days, fired = {}, set()
    for i in range(lo_i, hi_i + 1):
        d = times[i][:10]
        if d in blocked:
            continue
        days[d] = True
        if fire[i]:
            fired.add(d)
    n = len(days)
    return {"ordinary_days": n, "fired_days": len(fired), "rate": (len(fired) / n) if n else None}


def evaluate(times, raw, event_eps, lo_i, hi_i):
    avail = [v is not None for v in raw]
    fire = persisted(raw)
    evs = [e for e in event_eps if lo_i <= e[0] <= hi_i]
    cells = [dict(score_event(on, fire, avail), onset=times[on]) for on, _ in evs]
    alarms = [a for a in alarm_episodes(fire) if lo_i <= a[0] <= hi_i]
    cl = classify_alarms(alarms, event_eps)
    counts = {k: sum(1 for c in cells if c["cell"] == k) for k in ("HIT", "MISS", "UNRESOLVED")}
    counts["FALSE_ALARM"] = sum(1 for a in cl if a[2] == "FALSE_ALARM")
    counts["HIT_ALARM"] = sum(1 for a in cl if a[2] == "HIT_ALARM")
    counts["DURING_EVENT"] = sum(1 for a in cl if a[2] == "DURING_EVENT")
    return {"cells": cells, "counts": counts,
            "base": ordinary_day_rate(times, fire, event_eps, lo_i, hi_i),
            "false_alarm_starts": [times[a[0]] for a in cl if a[2] == "FALSE_ALARM"]}


def choose(results):
    """results: list of (label, eval_on_training). Max hits s.t. day rate <= ceiling; tie ->
    lower day rate. Returns (label, eval) or (None, None) if nothing meets the ceiling."""
    ok = [(lab, r) for lab, r in results
          if r["base"]["rate"] is not None and r["base"]["rate"] <= FA_DAY_CEILING]
    if not ok:
        return None, None
    return max(ok, key=lambda x: (x[1]["counts"]["HIT"], -x[1]["base"]["rate"]))


def verdict(n_ind, sig_hits, base_hits, extra_hits):
    if n_ind < N_MIN:
        return "REFUSED FEW_EVENTS"
    if extra_hits > 0 and sig_hits >= 1:
        return "ADDS_SKILL (held-out, per-event)"
    return "NO_ADDED_SKILL"


def chance_hit_prob(day_rate, window_days=WINDOW_H // 24):
    """probability that a signal firing independently on a share `day_rate` of days fires at
    least once in a window of `window_days` days -- the no-skill reference for a HIT."""
    if day_rate is None:
        return None
    return 1.0 - (1.0 - day_rate) ** window_days


def window_min(series, onset, window=WINDOW_H):
    vals = [v for v in series[max(0, onset - window):onset] if v is not None]
    return min(vals) if vals else None


def monthly_fire_rate(times, fire, lo_i, hi_i):
    days, fired = {}, {}
    for i in range(lo_i, hi_i + 1):
        m, d = int(times[i][5:7]), times[i][:10]
        days.setdefault(m, set()).add(d)
        if fire[i]:
            fired.setdefault(m, set()).add(d)
    return {m: round(len(fired.get(m, ())) / len(days[m]), 3) for m in sorted(days)}


SYNOPTIC_HOURS_ICT = ("01", "07", "13", "19")  # 18/00/06/12 UTC: real output in every model step


def model_day_flags(times, p, days, dp_thr, clim=None, anom_thr=None, bias=0.0):
    """per local day for one model series:
      min_dp24      -- same-hour lag-24 over every hourly tick the payload holds;
      min_dp24_syn  -- the same, restricted to the 4 synoptic hours (guard: when a model's
                       output step widens from 1-3 h to 6 h the provider interpolates, the
                       twice-daily tide peak/trough vanishes, and an all-hour dp24 shows a
                       spurious fall of up to ~3 hPa);
      min_anom      -- p - bias - training climatology (bias = mean model-minus-ERA5 overlap).
    Flags: DP24 (synoptic dp24 <= -dp_thr), DP24_ALLHOUR_ONLY (all-hour fires, synoptic does not
    -> tide-resolution artifact risk, not a signal), ANOM, NO_READOUT."""
    dp = lag_diff(p, 24)
    out = {}
    for d in days:
        idx = [i for i, t in enumerate(times) if t[:10] == d]
        dps = [dp[i] for i in idx if dp[i] is not None]
        syn = [dp[i] for i in idx if dp[i] is not None and times[i][11:13] in SYNOPTIC_HOURS_ICT]
        row = {"min_dp24": min(dps) if dps else None, "min_dp24_syn": min(syn) if syn else None,
               "n_dp24": len(dps)}
        if clim is not None:
            an = [round(p[i] - bias - clim[(int(times[i][5:7]), int(times[i][11:13]))], 1)
                  for i in idx if p[i] is not None and times[i][11:13] in SYNOPTIC_HOURS_ICT]
            row["min_anom"] = min(an) if an else None
        flags = []
        if row["min_dp24_syn"] is not None and row["min_dp24_syn"] <= -dp_thr:
            flags.append("DP24")
        elif row["min_dp24"] is not None and row["min_dp24"] <= -dp_thr:
            flags.append("DP24_ALLHOUR_ONLY")
        if clim is not None and row.get("min_anom") is not None and row["min_anom"] <= -anom_thr:
            flags.append("ANOM")
        if not dps:
            flags.append("NO_READOUT")
        row["flags"] = flags
        out[d] = row
    return out

# ----------------------------------------------------------------- IO (not pure)
def load_era5(paths):
    cells = {}
    for path in sorted(paths):
        for c in json.load(open(path)):
            key = (round(c["latitude"], 3), round(c["longitude"], 3))
            d = cells.setdefault(key, {"time": [], "p": [], "r": []})
            h = c["hourly"]
            d["time"] += h["time"]
            d["p"] += h["pressure_msl"]
            d["r"] += h["precipitation"]
    for key, d in cells.items():
        t0 = dt.datetime.fromisoformat(d["time"][0])
        for i, t in enumerate(d["time"]):
            assert dt.datetime.fromisoformat(t) == t0 + dt.timedelta(hours=i), (key, t)
    return cells


def raw_series(kind, thr, S):
    if kind == "dp24":
        return [None if v is None else v <= -thr for v in S["dp24"]]
    if kind == "anom":
        return [None if v is None else v <= -thr for v in S["anom"]]
    if kind == "rain":
        return [None if v is None else v >= thr for v in S["rain24"]]
    raise ValueError(kind)


def raw_or(a, b):
    return [None if (x is None and y is None) else bool(x) or bool(y) for x, y in zip(a, b)]


def build(cells):
    keys = sorted(cells)
    times = cells[keys[0]]["time"]
    dps, anoms, rains = [], [], []
    for k in keys:
        c = cells[k]
        dps.append(lag_diff(c["p"], 24))
        clim = climatology(times, c["p"], *TRAIN)
        c["clim"] = clim
        anoms.append(anomaly(times, c["p"], clim))
        rains.append(rolling_sum(c["r"], 24))
    S = {"times": times, "keys": keys,
         "dp24": worst(dps, min), "anom": worst(anoms, min), "rain24": worst(rains, max)}
    ev_flags = [v is not None and v >= EVENT_MM_24H for v in S["rain24"]]
    S["event_eps"] = episodes(ev_flags)
    S["rain_max_ep"] = [max(S["rain24"][on:last + 1]) for on, last in S["event_eps"]]
    return S


def idx_of(times, t):
    return times.index(t)


def run(S):
    times = S["times"]
    tr = (idx_of(times, TRAIN[0]), idx_of(times, TRAIN[1]))
    he = (idx_of(times, HELD[0]), len(times) - 1)
    scan = {}
    fam = {"dp24": GRIDS["dp24_hpa"], "anom": GRIDS["anom_hpa"], "rain": GRIDS["rain24_mm"]}
    for kind, grid in fam.items():
        scan[kind] = [(f"{kind}:{g}", evaluate(times, raw_series(kind, g, S), S["event_eps"], *tr))
                      for g in grid]
    for pk in ("dp24", "anom"):
        res = []
        for r in GRIDS["rain24_mm"]:
            for g in fam[pk]:
                raw = raw_or(raw_series("rain", r, S), raw_series(pk, g, S))
                res.append((f"rain:{r}|{pk}:{g}", evaluate(times, raw, S["event_eps"], *tr)))
        scan[f"rain_or_{pk}"] = res
    chosen, held = {}, {}
    for fam_name, res in scan.items():
        lab, ev = choose(res)
        chosen[fam_name] = lab
        if lab is None:
            continue
        parts = [p.split(":") for p in lab.split("|")]
        raws = [raw_series(k, float(v), S) for k, v in parts]
        raw = raws[0] if len(raws) == 1 else raw_or(*raws)
        held[fam_name] = evaluate(times, raw, S["event_eps"], *he)
    return scan, chosen, held, tr, he


FLOOD_TRUTH = [  # held-out Bangkok flood truth held in this repo (read, not re-derived)
    {"event_id": "bkk_2569_09_24_27_districts", "group": "G1_2569_09", "onset": "2026-09-25T20:00",
     "censoring": "left_censored", "tag": "MEASURED"},
    {"event_id": "sammakorn_2569_09_26", "group": "G1_2569_09", "onset": "2026-09-26T04:00",
     "censoring": "onset <= 04:00", "tag": "MEASURED"},
    {"event_id": "bkk_2568_09_14_street", "group": "G2_2568_09", "onset": "2025-09-14T00:00",
     "censoring": "day resolution -> onset taken as 00:00 (lead is a lower bound)", "tag": "RELAYED"},
]


def load_ibtracs(path):
    import yaml
    rows = yaml.safe_load(open(path))["rows"]
    out = []
    for r in rows:
        t = dt.datetime.fromisoformat(r["time_utc"]) + dt.timedelta(hours=7)
        out.append((t.strftime("%Y-%m-%dT%H:%M"), r["name"], r["storm_id"], r["distance_km_from_bangkok"]))
    return out


def nearest_storm(storms, onset, before_h=WINDOW_H, after_h=24):
    t0 = dt.datetime.fromisoformat(onset)
    lo, hi = t0 - dt.timedelta(hours=before_h), t0 + dt.timedelta(hours=after_h)
    got = [s for s in storms if lo <= dt.datetime.fromisoformat(s[0]) <= hi]
    if not got:
        return None
    s = min(got, key=lambda x: x[3])
    return {"name": s[1], "storm_id": s[2], "time_ict": s[0], "distance_km": s[3]}


def tonight(S, cells, live_glob, dp_thr, anom_thr, first_day, n_days=10):
    """latest raw pressure payload per point -> per model per day flags, D+1..D+n."""
    by_point = {}
    for f in sorted(glob.glob(live_glob)):
        by_point[Path(f).stem.split("_", 1)[1]] = f
    days = [(dt.date.fromisoformat(first_day) + dt.timedelta(days=i)).isoformat()
            for i in range(n_days)]
    k0 = S["keys"][0]  # east/Sammakorn ERA5 cell -- nearest to all three points
    era = cells[k0]
    era_map = dict(zip(era["time"], era["p"]))
    out = {"days": days, "era5_cell_for_clim": list(k0), "points": {}}
    for point, f in by_point.items():
        d = json.load(open(f))
        h = d["hourly"]
        pt = {"file_issue_utc": Path(f).stem.split("_")[0], "grid": [d["latitude"], d["longitude"]],
              "models": {}}
        for key, series in h.items():
            if not key.startswith("pressure_msl_"):
                continue
            model = key[len("pressure_msl_"):]
            ov = [series[i] - era_map[t] for i, t in enumerate(h["time"])
                  if series[i] is not None and era_map.get(t) is not None]
            bias = round(sum(ov) / len(ov), 2) if ov else 0.0
            flags = model_day_flags(h["time"], series, days, dp_thr, era["clim"], anom_thr, bias)
            pt["models"][model] = {"bias_vs_era5_hpa": bias, "n_overlap_h": len(ov), "days": flags}
        out["points"][point] = pt
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--era5-glob", required=True)
    ap.add_argument("--ibtracs", default="sources/ibtracs_bkk_500km.yaml")
    ap.add_argument("--live-glob", default=None, help="latest raw openmeteo_pressure files")
    ap.add_argument("--first-day", default=None, help="D+1 local date for the tonight check")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cells = load_era5(glob.glob(a.era5_glob))
    S = build(cells)
    scan, chosen, held, tr, he = run(S)
    times = S["times"]
    storms = load_ibtracs(a.ibtracs)
    thr = {f: dict(p.split(":") for p in (lab or "").split("|") if p) for f, lab in chosen.items()}
    dp_thr, anom_thr = float(thr["dp24"]["dp24"]), float(thr["anom"]["anom"])
    fires = {f: persisted(raw_series(f, float(thr[f][f]), S)) for f in ("dp24", "anom", "rain")}
    ev_rows = []
    for (on, last), m in zip(S["event_eps"], S["rain_max_ep"]):
        row = {"onset": times[on], "last": times[last], "max24_mm": m,
               "period": "train" if on <= tr[1] else "held",
               "min_dp24_72h": window_min(S["dp24"], on), "min_anom_72h": window_min(S["anom"], on),
               "storm": nearest_storm(storms, times[on])}
        for f in ("dp24", "anom", "rain"):
            row[f] = score_event(on, fires[f], [v is not None for v in raw_series(f, 1.0, S)])
        ev_rows.append(row)
    flood_rows = []
    for ft in FLOOD_TRUTH:
        on = idx_of(times, ft["onset"])
        row = dict(ft, min_dp24_72h=window_min(S["dp24"], on), min_anom_72h=window_min(S["anom"], on),
                   storm=nearest_storm(storms, ft["onset"]))
        for f in ("dp24", "anom", "rain"):
            row[f] = score_event(on, fires[f], [v is not None for v in raw_series(f, 1.0, S)])
        flood_rows.append(row)
    # 24-27 Sep 2569 trace (ERA5, worst cell), every 6 h
    i0, i1 = idx_of(times, "2026-09-20T00:00"), len(times) - 1
    trace = [{"t": times[i], "dp24": S["dp24"][i], "anom": S["anom"][i], "rain24": S["rain24"][i]}
             for i in range(i0, i1 + 1, 6)]
    chance = {f: {"day_rate": r["base"]["rate"], "p_hit_by_chance_72h": chance_hit_prob(r["base"]["rate"]),
                  "expected_chance_hits": len(r["cells"]) * chance_hit_prob(r["base"]["rate"])}
              for f, r in held.items()}
    n_ind = len(held["rain"]["cells"])
    extra = sum(1 for c_or, c_r in zip(held["rain_or_dp24"]["cells"], held["rain"]["cells"])
                if c_or["cell"] == "HIT" and c_r["cell"] != "HIT")
    out = {
        "cells": [list(k) for k in S["keys"]],
        "declared": {"window_h": WINDOW_H, "persist_p": PERSIST_P, "event_mm_24h": EVENT_MM_24H,
                     "fa_day_ceiling": FA_DAY_CEILING, "n_min": N_MIN, "train": TRAIN, "held": HELD,
                     "grids": GRIDS},
        "events": ev_rows, "flood_truth": flood_rows, "trace_2569_09": trace,
        "scan": {f: [{"label": lab, "counts": r["counts"], "base": r["base"]} for lab, r in res]
                 for f, res in scan.items()},
        "chosen": chosen,
        "held": held, "chance": chance,
        "monthly_fire_rate_held": {f: monthly_fire_rate(times, fires[f], he[0], he[1]) for f in fires},
        "verdict": verdict(n_ind, held["dp24"]["counts"]["HIT"], held["rain"]["counts"]["HIT"], extra),
        "n_independent_held": n_ind, "extra_hits_rain_or_dp24_over_rain": extra,
    }
    if a.live_glob and a.first_day:
        out["tonight"] = tonight(S, cells, a.live_glob, dp_thr, anom_thr, a.first_day)
    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps({"chosen": chosen, "verdict": out["verdict"], "n_ind": n_ind, "extra": extra,
                      "chance": chance}, indent=1))


if __name__ == "__main__":
    main()
