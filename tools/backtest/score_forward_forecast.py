"""score_forward_forecast.py -- fills the PROP-FLOOD-10 Δ10.3 verification ledger for a
forward-forecast record written by forward_forecast_bkk_10day.py, once the days have
happened.

    ทดลอง — สมการเป็นข้อเสนอ ยังไม่ลงทะเบียน Toledo

cell := HIT          if F fires and O = EVENT
        MISS         if F does not fire and O = EVENT
        FALSE_ALARM  if F fires and O = NO_EVENT
        CORRECT_NEG  if F does not fire and O = NO_EVENT
        UNRESOLVED   if O = UNRESOLVED or F = REFUSED     (never counted as CORRECT_NEG)
"fires" is reported twice: strict (state = ROBUST) and worst-first (hi >= θ).
A5 (ค่าชั่วคราว รอผู้ก่อตั้ง, as currently coded): under STRICT a POSSIBLE forecast with
NO_EVENT counts CORRECT_NEG; every such cell carries `undecided_forecast: true` so it can be
re-bucketed when the founder decides.

Cells are listed one by one (per day, per unit, per axis, per θ). Nothing is averaged. The
only aggregate is a COUNT per cell type with the unresolved bracket beside it
(D/M.79-80). A skill claim is REFUSED FEW_EVENTS while the number of independent events is
below N_min (provisional 10).

Observation rules (declared here, INSTINCT, founder may change them):
  rain_24h axis : per gauge, the rain_24h_mm reading closest to the local-day window end
                  (within ±90 min); EVENT if max over the unit's gauges >= θ; NO_EVENT if at
                  least one gauge reported and all < θ; UNRESOLVED otherwise. Caveat: the
                  feed's own accumulation window (rolling vs 07:00) is OPEN (R3).
  rain_1h axis  : max rain_1h_mm over the window at the unit's gauges vs 58.7 mm.
  flood_road    : ledger rule road_telemetry_district_cluster_v1 (>= 3 distinct roads >= 10 cm
                  chained within 6 h) -> EVENT; >= 3 stations reported and no cluster ->
                  NO_EVENT; else UNRESOLVED.
  stage C.12    : max waterlevel_msl in the window vs +1.80 / +2.00 m MSL (ม.รทก.).
A day whose window (+ LAG) has not ended is UNRESOLVED NOT_YET_OBSERVABLE.

Usage:
    python3 tools/backtest/score_forward_forecast.py --record raw/forecast_tests/bkk_10day_<UTC>.json
Writes raw/forecast_tests/score_<record stem>_<UTC>.json (append-only, never overwritten).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forward_forecast_bkk_10day import (  # noqa: E402
    DB_PATH, OUT_DIR, LABEL_TH, N_MIN, assign_gauge_district, road_stations, local_day_window_utc,
)

LAG = dt.timedelta(hours=2)
ROAD_THRESHOLD_CM = 10.0
ROAD_MIN_ROADS = 3
ROAD_WINDOW = dt.timedelta(hours=6)
STAGE_STATION = "C.12"
BKK_BBOX = (13.49, 13.96, 100.32, 100.94)


def ledger_cell(f_state: Optional[str], fires: Optional[bool], obs: str) -> str:
    if obs == "UNRESOLVED" or f_state is None or f_state == "REFUSED" or fires is None:
        return "UNRESOLVED"
    if fires and obs == "EVENT":
        return "HIT"
    if not fires and obs == "EVENT":
        return "MISS"
    if fires and obs == "NO_EVENT":
        return "FALSE_ALARM"
    return "CORRECT_NEG"


def _t(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------- observations per window

def rain24_by_unit(conn, s: dt.datetime, e: dt.datetime, roads: dict) -> dict:
    """{'__city__': [values], district: [values]} -- the reading closest to window end."""
    lo, hi = (e - dt.timedelta(minutes=90)).isoformat(), (e + dt.timedelta(minutes=90)).isoformat()
    rows = conn.execute(
        "SELECT station_code, lat, lon, value, observed_at_utc FROM observations WHERE source_id='thaiwater_rain_24h' "
        "AND variable='rain_24h_mm' AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? AND observed_at_utc>=? "
        "AND observed_at_utc<=?", (BKK_BBOX[0], BKK_BBOX[1], BKK_BBOX[2], BKK_BBOX[3], lo, hi)).fetchall()
    best = {}
    for sc, la, lo_, v, t in rows:
        if v is None:
            continue
        gap = abs((_t(t) - e).total_seconds())
        if sc not in best or gap < best[sc][0]:
            best[sc] = (gap, v, la, lo_)
    out = {"__city__": []}
    for sc, (_, v, la, lo_) in best.items():
        out["__city__"].append(v)
        d = assign_gauge_district(sc, la, lo_, roads)
        if d:
            out.setdefault(d, []).append(v)
    return out


def rain1h_by_unit(conn, s: dt.datetime, e: dt.datetime, roads: dict) -> dict:
    rows = conn.execute(
        "SELECT station_code, lat, lon, value FROM observations WHERE source_id='thaiwater_rain_24h' "
        "AND variable='rain_1h_mm' AND lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? AND observed_at_utc>? "
        "AND observed_at_utc<=?", (BKK_BBOX[0], BKK_BBOX[1], BKK_BBOX[2], BKK_BBOX[3], s.isoformat(), e.isoformat())).fetchall()
    out = {"__city__": []}
    for sc, la, lo_, v in rows:
        if v is None:
            continue
        out["__city__"].append(v)
        d = assign_gauge_district(sc, la, lo_, roads)
        if d:
            out.setdefault(d, []).append(v)
    return out


def flood_road_by_district(conn, s: dt.datetime, e: dt.datetime) -> dict:
    rows = conn.execute(
        "SELECT station_code, value, observed_at_utc, provenance_json FROM observations WHERE "
        "source_id='thaiwater_flood_road' AND observed_at_utc>=? AND observed_at_utc<? ORDER BY observed_at_utc",
        (s.isoformat(), e.isoformat())).fetchall()
    stations, wet = {}, {}
    for sc, v, t, prov in rows:
        try:
            d = json.loads(prov or "{}").get("district_th")
        except ValueError:
            d = None
        if d is None:
            continue
        stations.setdefault(d, set()).add(sc)
        if v is not None and v >= ROAD_THRESHOLD_CM:
            wet.setdefault(d, []).append((_t(t), sc))
    out = {}
    for d, sts in stations.items():
        ev = sorted(wet.get(d, []))
        onset, cluster, seen = None, [], []
        for t, sc in ev:
            if cluster and t - cluster[-1][0] > ROAD_WINDOW:
                cluster, seen = [], []
            cluster.append((t, sc))
            if sc not in seen:
                seen.append(sc)
            if len(seen) >= ROAD_MIN_ROADS and onset is None:
                onset = t
        if onset is not None:
            obs = "EVENT"
        elif len(sts) >= ROAD_MIN_ROADS:
            obs = "NO_EVENT"
        else:
            obs = "UNRESOLVED"
        out[d] = {"obs": obs, "n_stations": len(sts), "onset_utc": onset.isoformat() if onset else None,
                  "n_wet_roads": len({sc for _, sc in ev})}
    return out


def stage_max(conn, s: dt.datetime, e: dt.datetime) -> Optional[dict]:
    r = conn.execute(
        "SELECT value, observed_at_utc, source_id FROM observations WHERE station_code=? AND variable='waterlevel_msl' "
        "AND observed_at_utc>=? AND observed_at_utc<? ORDER BY value DESC LIMIT 1",
        (STAGE_STATION, s.isoformat(), e.isoformat())).fetchone()
    return None if r is None else {"value_m": r[0], "at_utc": r[1], "source": r[2]}


def obs_from_values(vals: list, theta: float) -> str:
    if not vals:
        return "UNRESOLVED"
    return "EVENT" if max(vals) >= theta else "NO_EVENT"


# ---------------------------------------------------------------- scoring

def _forecast_cell(pt: dict, obs: str, **extra) -> dict:
    st = pt.get("state")
    c_strict = ledger_cell(st, pt.get("fires_strict"), obs)
    c_wf = ledger_cell(st, pt.get("fires_worst_first"), obs)
    return {**extra, "F_state": st, "O": obs, "cell_strict": c_strict, "cell_worst_first": c_wf,
            "undecided_forecast": bool(st == "POSSIBLE" and c_strict == "CORRECT_NEG")}


def score(record: dict, conn: sqlite3.Connection, now_utc: dt.datetime) -> dict:
    roads = road_stations(conn)
    cells = []
    for day in record["days"]:
        s, e = _t(day["window_utc"][0]), _t(day["window_utc"][1])
        base = {"day_index": day["day_index"], "date_local": day["date_local"]}
        if now_utc < e + LAG:
            cells.append({**base, "unit": "*", "axis": "*", "cell_strict": "UNRESOLVED",
                          "cell_worst_first": "UNRESOLVED", "O": "UNRESOLVED", "reason": "NOT_YET_OBSERVABLE"})
            continue
        r24 = rain24_by_unit(conn, s, e, roads)
        r1 = rain1h_by_unit(conn, s, e, roads)
        fr = flood_road_by_district(conn, s, e)
        # level 0 (city screen) — rain_24h axis
        for pt in day["level0"]["per_theta"]:
            obs = obs_from_values(r24["__city__"], pt["theta"])
            cells.append(_forecast_cell(pt, obs, **base, unit="L0:DWR1002-Bangkok", axis="rain_24h",
                                        theta=pt["theta"], rung=pt["rung"],
                                        obs_max=max(r24["__city__"]) if r24["__city__"] else None,
                                        obs_n=len(r24["__city__"])))
        # level 1 — 1 h at the Sammakorn cell vs gauges of สะพานสูง
        h = day.get("level1_1h_sammakorn_cell") or {}
        vals = r1.get("สะพานสูง", [])
        cells.append(_forecast_cell(h, obs_from_values(vals, 58.7), **base, unit="L1:Sammakorn-cell",
                                    axis="rain_1h", theta=58.7, obs_max=max(vals) if vals else None))
        # level 1 — districts
        for drow in day["level1_districts"]:
            dname = drow["district_th"]
            f = drow.get("forecast") or {}
            per = f.get("per_theta")
            road = fr.get(dname, {"obs": "UNRESOLVED", "n_stations": 0})
            dv = r24.get(dname, [])
            if not per:
                for axis, obs in (("rain_24h", obs_from_values(dv, 35.1)), ("flood_road", road["obs"])):
                    cells.append({**base, "unit": f"L1:{dname}", "axis": axis, "theta": 35.1 if axis == "rain_24h" else None,
                                  "F_state": "REFUSED", "O": obs, "cell_strict": "UNRESOLVED",
                                  "cell_worst_first": "UNRESOLVED", "reason": f.get("reason"),
                                  "road_detail": road if axis == "flood_road" else None})
                continue
            for pt in per:
                cells.append(_forecast_cell(pt, obs_from_values(dv, pt["theta"]), **base, unit=f"L1:{dname}",
                                            axis="rain_24h", theta=pt["theta"], obs_max=max(dv) if dv else None))
                if pt["theta"] in (35.1, 80.0):
                    cells.append(_forecast_cell(pt, road["obs"], **base, unit=f"L1:{dname}", axis="flood_road",
                                                theta=pt["theta"], road_detail=road))
        # stage boundary — forecast REFUSED; observation recorded anyway
        sm = stage_max(conn, s, e)
        for line in (1.80, 2.00):
            obs = "UNRESOLVED" if sm is None else ("EVENT" if sm["value_m"] >= line else "NO_EVENT")
            cells.append({**base, "unit": "boundary:C.12", "axis": "stage_msl", "theta": line,
                          "F_state": "REFUSED", "O": obs, "cell_strict": "UNRESOLVED",
                          "cell_worst_first": "UNRESOLVED", "obs_detail": sm,
                          "reason": "NO_STAGE_FORECAST (forecast refused at issue)"})
    counts = {}
    for c in cells:
        for k in ("cell_strict", "cell_worst_first"):
            key = f"{k}:{c[k]}"
            counts[key] = counts.get(key, 0) + 1
    n_ind = 1  # one forecast issue = at most one independent meteorological event window set
    return {
        "record_type": "bkk_10day_forward_forecast_score",
        "label_th": LABEL_TH,
        "scored_at_utc": now_utc.isoformat(),
        "record_issued_at_utc": record.get("issued_at_utc"),
        "cells": cells,
        "counts_not_averages": counts,
        "skill_claim": {"state": "REFUSED", "reason": f"FEW_EVENTS (n_ind={n_ind} < N_min={N_MIN}, ค่าชั่วคราว รอผู้ก่อตั้ง)"}
        if n_ind < N_MIN else {"state": "OPEN"},
        "A5_note": "as currently coded — POSSIBLE+NO_EVENT under STRICT = CORRECT_NEG, flagged undecided_forecast",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True)
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--now", default=None, help="override 'now' (ISO UTC) -- for replay/testing only")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    a = ap.parse_args()
    record = json.loads(Path(a.record).read_text(encoding="utf-8"))
    now = _t(a.now) if a.now else dt.datetime.now(dt.timezone.utc)
    conn = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    try:
        res = score(record, conn, now)
    finally:
        conn.close()
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"score_{Path(a.record).stem}_{stamp}.json"
    if out.exists():
        raise FileExistsError(out)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for c in res["cells"]:
        if c.get("axis") in ("*",) or c.get("unit", "").startswith("L0") or c.get("unit") == "boundary:C.12" \
                or c.get("cell_strict") != "UNRESOLVED":
            print(c["date_local"], c.get("unit"), c.get("axis"), c.get("theta"), c.get("F_state"), c.get("O"),
                  c["cell_strict"], c["cell_worst_first"])
    print(res["counts_not_averages"])
    print(res["skill_claim"])
    print(out)


if __name__ == "__main__":
    main()
