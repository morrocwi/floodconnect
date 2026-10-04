"""peak_window.py -- Bangkok peak-window readout (28 Sep - 8 Oct 2026), four drivers only.

Founder question (2026-09-28, verbatim): "เอาเลย แล้วประเมินว่าสถานการณ์ กทม. กำลังจะแย่ลง
ถึงจุดสูงสุดวันไหน". Founder focus = four drivers only: ฝน (rain), การระบาย (drainage),
น้ำเหนือ (upstream / northern water), น้ำหนุน (tide).

Label every output "ทดลอง — สมการข้อเสนอ". Nothing here is a Toledo theorem.

Equation status (repo rule, AGENTS.md §2 -- Toledo-first):
  * days_to_full(): PROP-FLOOD-03 bucket step S(k+1) = S(k) + Q_in*tau - Q_out*tau
    (water_balance.py; Toledo PR #60, proposal, unverified) iterated with CONSTANT
    measured rates and solved for the first tick where S >= S_full. The iteration /
    inversion itself is **not yet in Toledo**. With constant rates the answer is
    (S_full - S) / (Q_in - Q_out); Q_in <= Q_out -> NOT_FILLING (never a number).
    Exact arithmetic on fractions.Fraction (IDM Q-computability law).
  * driver levels and the combined-state rule: a qualitative ordinal classifier
    (0 / 1 / 2 / None=REFUSED) -- **ours, PROPOSAL, not in Toledo**. No numeric index is
    formed: the combined state is a set of upward-closed boolean conditions on the four
    levels, so raising any driver can never lower the combined state (monotone; tested).
  * booked arrival windows are PROP-FLOOD-09 v1.1 Δ1 (draft) results copied from
    docs/knowledge/INBOUND_DEBT_ARRIVAL_TIMES_2026-09-28.md -- not recomputed here.

Pure functions except main(), which reads archived raw payloads (gitignored raw/) plus
data/observations.sqlite (read-only) and APPENDS one new forward-record file under
raw/forecast_tests/ (never overwrites an existing file).
"""
from __future__ import annotations

import glob
import json
import sqlite3
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
DAM_DIR = ROOT / "raw" / "backtest" / "dam_history_2026-09-28"
LAG_DIR = ROOT / "raw" / "backtest" / "lag_2026-09-28"
FORECAST_DIR = ROOT / "raw" / "forecast_tests"
LABEL_TH = "ทดลอง — สมการข้อเสนอ"

# ---------------------------------------------------------------- dam history ---------

def release_changes(series: Dict[str, dict], rel_tol: Fraction = Fraction(1, 10)) -> List[dict]:
    """Days where release differs from the previous day by more than rel_tol (relative).
    series: {YYYY-MM-DD: {"release": float|None, ...}} -> [{date, from, to, delta}]."""
    out, prev_day, prev = [], None, None
    for day in sorted(series):
        r = series[day].get("release")
        if r is None:
            continue
        if prev is not None:
            base = Fraction(str(prev))
            cur = Fraction(str(r))
            if base == 0 and cur != 0 or base != 0 and abs(cur - base) / base > rel_tol:
                out.append({"date": day, "from": prev, "to": r, "delta": float(cur - base)})
        prev_day, prev = day, r
    return out


def days_to_full(storage: float, full: float, inflow: float, release: float) -> dict:
    """PROP-FLOOD-03 constant-rate inversion (not yet in Toledo). MCM and MCM/day."""
    if None in (storage, full, inflow, release):
        return {"state": "REFUSED", "reason": "MISSING_INPUT"}
    s, f = Fraction(str(storage)), Fraction(str(full))
    net = Fraction(str(inflow)) - Fraction(str(release))
    head = f - s
    if head <= 0:
        return {"state": "AT_OR_ABOVE_FULL", "headroom_mcm": float(head)}
    if net <= 0:
        return {"state": "NOT_FILLING", "headroom_mcm": float(head), "net_mcm_day": float(net)}
    return {"state": "FILLING", "headroom_mcm": float(head), "net_mcm_day": float(net),
            "days": float(head / net), "days_exact": f"{head.numerator * net.denominator}/"
            f"{head.denominator * net.numerator}"}


def forced_release_flag(storage: float, urc: Optional[float], dtf: dict,
                        horizon_days: int = 7) -> str:
    """INSTINCT flag only -- never a claim of an operator decision."""
    above = urc is not None and storage is not None and storage > urc
    soon = dtf.get("state") == "FILLING" and dtf["days"] <= horizon_days
    if dtf.get("state") == "AT_OR_ABOVE_FULL" or (above and soon):
        return "FLAG"
    if urc is None:
        return "NO_FLAG_URC_UNKNOWN" if not soon else "FLAG"
    return "NO_FLAG"

# ---------------------------------------------------------------- driver levels -------
# Levels: 0 ต่ำ, 1 ยกตัว, 2 สูง, None REFUSED. Thresholds and their owners:
RAIN_BMA_24H = 80.0      # BMA design capacity mm/24h (plan p.63) VERIFIED
RAIN_TMD_YELLOW = 35.1   # TMD yellow lower edge mm/24h VERIFIED (sources crosswalk)
STAGE_FAIL = 2.00        # BMA plan p.47 "may fail" m MSL VERIFIED
STAGE_DERATE = 1.80      # BMA plan p.22 derating m MSL VERIFIED
TIDE_REF_HW = 0.96       # predicted HW on 27 Sep, the day C.12 max was 2.24 (reference, ours)
TIDE_SPRING_HW = 1.14    # within 2 x 0.01 m gauge resolution of the period max 1.16 (ours)
UPSTREAM_REF_Q = 1409.0  # C.13 daily-mean 22 Sep: the flow booked to reach BKK when C.12
                         # first read >= +2.00 (26 Sep) -- MEASURED reference (ours)


def rain_level(worst_mm: Optional[float]) -> Optional[int]:
    if worst_mm is None:
        return None
    return 2 if worst_mm >= RAIN_BMA_24H else 1 if worst_mm >= RAIN_TMD_YELLOW else 0


def tide_level(hw_max: Optional[float]) -> Optional[int]:
    if hw_max is None:
        return None
    return 2 if hw_max >= TIDE_SPRING_HW else 1 if hw_max > TIDE_REF_HW else 0


def drainage_level(c12_max: Optional[float], polder_critical: Optional[bool]) -> Optional[int]:
    """Gravity drainage to the river derates with C.12 stage (BMA plan lines); a published
    CRITICAL status in the Sammakorn chain is debt already carried."""
    if c12_max is None and polder_critical is None:
        return None
    lv = 0
    if c12_max is not None:
        lv = 2 if c12_max >= STAGE_FAIL else 1 if c12_max >= STAGE_DERATE else 0
    if polder_critical:
        lv = 2
    return lv


def upstream_level(main_stem_q: Optional[float], component_booked: bool) -> Optional[int]:
    """main_stem_q: max booked main-stem flow (C.13/C.2 chain) whose window overlaps the day,
    None if no main-stem flow is booked for that day (INPUT_ABSENT beyond horizon)."""
    if main_stem_q is not None:
        return 2 if main_stem_q >= UPSTREAM_REF_Q else 1
    return None  # REFUSED INPUT_ABSENT -- see upstream_floor() for the booked lower bound


def upstream_floor(main_stem_q: Optional[float], component_booked: bool) -> int:
    """Lower bound when the main stem is REFUSED: booked tributary/dam components only."""
    return 1 if main_stem_q is None and component_booked else 0


CLASSES = ["ต่ำ", "ปานกลาง", "สูง", "สูงสุด"]


def combined_class(rain: Optional[int], drain: Optional[int], up: Optional[int],
                   tide: Optional[int]) -> str:
    """Upward-closed rule (PROPOSAL). REFUSED must be resolved by the caller (lo/hi)."""
    lv = [rain, drain, up, tide]
    if any(v is None for v in lv):
        raise ValueError("resolve REFUSED before classifying")
    n2 = sum(1 for v in lv if v == 2)
    n1 = sum(1 for v in lv if v >= 1)
    if up == 2 and tide == 2 and drain == 2:
        return "สูงสุด"
    if n2 >= 2:
        return "สูง"
    if n2 >= 1 or n1 >= 2:
        return "ปานกลาง"
    return "ต่ำ"


def combined_interval(rain, drain, up, tide, floors: Optional[dict] = None) -> dict:
    """REFUSED -> evaluate at its declared floor (default 0) for lo and at 2 for hi;
    worst-first reports hi first. floors keys: rain/drain/up/tide."""
    fl = floors or {}
    names = ("rain", "drain", "up", "tide")
    lo = combined_class(*[fl.get(n, 0) if v is None else v
                          for n, v in zip(names, (rain, drain, up, tide))])
    hi = combined_class(*[2 if v is None else v for v in (rain, drain, up, tide)])
    return {"hi": hi, "lo": lo, "resolved": lo == hi}


def trend_labels(classes_hi: List[str]) -> List[str]:
    """Map class sequence to ต่ำ/เพิ่มขึ้น/สูงสุด/ลดลง: before the first สูงสุด day -> เพิ่มขึ้น
    (or ต่ำ), สูงสุด days -> สูงสุด, after the last contiguous peak run -> ลดลง unless the
    class climbs back (then เพิ่มขึ้น)."""
    rank = {c: i for i, c in enumerate(CLASSES)}
    out, seen_peak = [], False
    for i, c in enumerate(classes_hi):
        if c == "สูงสุด":
            out.append("สูงสุด"); seen_peak = True; continue
        if c == "ต่ำ":
            out.append("ต่ำ"); continue
        prev = rank[classes_hi[i - 1]] if i else rank[c]
        if not seen_peak or rank[c] > prev:
            out.append("เพิ่มขึ้น")
        else:
            out.append("ลดลง")
    return out

# ---------------------------------------------------------------- main ----------------

def _load_dam_history() -> dict:
    D = {}
    for t in ("released", "inflow", "storage"):
        f = sorted(DAM_DIR.glob(f"{t}_*.json"))[-1]
        for g in json.loads(f.read_text())["data"]["graph_data"]:
            for p in g["data"]:
                D.setdefault(g["dam_name"], {"id": g["id"], "series": {}})["series"].setdefault(
                    p["date"][:10], {})[{"released": "release"}.get(t, t)] = p["value"]
    curves = {}
    for f in DAM_DIR.glob("dam*_storage_rulecurve_*.json"):
        d = json.loads(f.read_text())["data"]
        name = d["graph_data"][0]["dam_name"]
        curves[name] = {"normal_bound": d["normal_bound"], "upper_bound": d["upper_bound"],
                        "lower_bound": d["lower_bound"],
                        "urc_by_mmdd": {p["date"][5:10]: p["value"] for p in d["upper_rule_curve"]},
                        "curve_year_label": d["upper_rule_curve"][0]["date"][:4],
                        "file": str(f.relative_to(ROOT))}
    return {"dams": D, "curves": curves}


def dam_trend(pct_now: Dict[str, float], asof: str = "2026-09-27", days: int = 30) -> dict:
    h = _load_dam_history()
    out = {}
    for name, rec in h["dams"].items():
        s = {k: v for k, v in rec["series"].items() if k <= asof}
        window = sorted(s)[-days:]
        now = s[asof]
        pct = pct_now.get(name)
        full_pct = round(now["storage"] * 100 / pct, 1) if pct else None
        cv = h["curves"].get(name, {})
        urc = cv.get("urc_by_mmdd", {}).get(asof[5:]) if cv else None
        dtf_pct = days_to_full(now["storage"], full_pct, now["inflow"], now["release"])
        dtf_norm = (days_to_full(now["storage"], cv["normal_bound"], now["inflow"], now["release"])
                    if cv else {"state": "REFUSED", "reason": "NORMAL_BOUND_NOT_FETCHED"})
        worst = min((d for d in (dtf_pct, dtf_norm) if d.get("state") == "FILLING"),
                    key=lambda d: d["days"], default=dtf_pct)
        chg = release_changes({k: s[k] for k in window})
        out[name] = {
            "hii_dam_id": rec["id"], "asof_dam_date": asof,
            "inflow_mcm_day": now["inflow"], "release_mcm_day": now["release"],
            "release_m3s": round(now["release"] / 0.0864, 1),
            "storage_mcm": now["storage"], "storage_pct_hii": pct,
            "full_by_pct_mcm": full_pct,
            "normal_bound_mcm": cv.get("normal_bound"), "upper_bound_mcm": cv.get("upper_bound"),
            "upper_rule_curve_mcm_today": urc,
            "days_to_full_pct_denominator": dtf_pct, "days_to_full_normal_bound": dtf_norm,
            "release_changes_30d": chg,
            "last_release_change": chg[-1] if chg else None,
            "forced_release_flag_instinct": forced_release_flag(now["storage"], urc, worst),
            "series_30d": [{"date": k, **s[k]} for k in window],
        }
    return out


def main(argv=None) -> int:
    # Inputs as read 2026-09-28 (see docs/knowledge/BKK_PEAK_WINDOW_ASSESSMENT_2026-09-28.md).
    pct_now = {"ภูมิพล": 62.92, "สิริกิติ์": 79.98, "ป่าสักชลสิทธิ์": 89.48,
               "แควน้อยบำรุงแดน": 71.02, "กิ่วลม": 90.45, "กิ่วคอหมา": 94.06}
    dams = dam_trend(pct_now)
    # per-day driver inputs (ICT dates); sources in the doc
    days = [
        # date,     rain worst (model), c12 max (source), polder crit, main-stem Q, comp, HW
        ("2026-09-28", (78.7, "ukmo_seamless"), (2.23, "MEASURED partial to 08:00"), True, 1750.0, False, 0.96),
        ("2026-09-29", (7.6, "jma_seamless"), (2.24, "HELD 27 Sep max"), None, 1894.0, False, 1.04),
        ("2026-09-30", (4.0, "jma_seamless"), (2.24, "HELD"), None, 1950.0, False, 1.12),
        ("2026-10-01", (8.5, "gfs_seamless"), (2.24, "HELD"), None, 1950.0, False, 1.14),
        ("2026-10-02", (11.4, "icon_seamless"), (2.24, "HELD"), None, 1950.0, False, 1.16),
        ("2026-10-03", (9.9, "knmi_seamless"), (2.24, "HELD"), None, 1911.0, True, 1.14),
        ("2026-10-04", (11.9, "jma_seamless"), (2.24, "HELD"), None, None, True, 1.06),
        ("2026-10-05", (14.8, "gfs_seamless"), (2.24, "HELD"), None, None, True, 1.04),
        ("2026-10-06", (24.5, "jma_seamless"), (2.24, "HELD"), None, None, True, 1.09),
        ("2026-10-07", (17.5, "jma_seamless"), (2.24, "HELD"), None, None, True, 1.14),
        ("2026-10-08", (8.6, "ecmwf_ifs025"), (2.24, "HELD"), None, None, True, 1.16),
    ]
    table = []
    for date, (rmm, rsrc), (c12, c12src), pc, q, comp, hw in days:
        lv = {"rain": rain_level(rmm), "drainage": drainage_level(c12, pc),
              "upstream": upstream_level(q, comp), "tide": tide_level(hw)}
        ci = combined_interval(lv["rain"], lv["drainage"], lv["upstream"], lv["tide"],
                               floors={"up": upstream_floor(q, comp)})
        if lv["upstream"] is None:
            lv["upstream_refused"] = "INPUT_ABSENT: main-stem (C.13/C.2) flow for this arrival day not yet measured"
            lv["upstream_floor"] = upstream_floor(q, comp)
        table.append({"date_ict": date, "rain_worst_mm": rmm, "rain_worst_model": rsrc,
                      "c12_max_m_msl": c12, "c12_basis": c12src, "polder_critical": pc,
                      "main_stem_booked_q_m3s": q, "component_booked": comp,
                      "tide_hw_max_m": hw, "levels": lv, "combined": ci})
    labels = trend_labels([r["combined"]["hi"] for r in table])
    labels_lo = trend_labels([r["combined"]["lo"] for r in table])
    for r, lab, lab_lo in zip(table, labels, labels_lo):
        r["label_worst_first"] = lab
        r["label_lo"] = lab_lo
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rec = {"record_type": "bkk_peak_window_forward_record", "label_th": LABEL_TH,
           "issued_at_utc": now, "public_page": False,
           "supersedes": sorted(p.name for p in FORECAST_DIR.glob("bkk_peak_window_*.json")),
           "supersede_note": "earlier same-day records used upstream=1 (not REFUSED) for 4-8 Oct; "
                             "kept unchanged (append-only), this record replaces them",
           "answer": {"window_ict": ["2026-10-01T19:41+07:00", "2026-10-03T20:35+07:00"],
                      "worst_point_ict": "2026-10-02T20:09+07:00",
                      "scope": "river stage at C.12 Sam Sen (river/tide/upstream) -- NOT in-polder",
                      "in_polder_worst_day_ict": "2026-09-28",
                      "secondary_window_ict": ["2026-10-07", "2026-10-08"],
                      "secondary_state": "OPEN: hi=สูงสุด lo=สูง (main-stem flow after 28 Sep not yet measured)"},
           "rule": "combined_class(): สูงสุด iff upstream=2 AND tide=2 AND drainage=2; "
                   "สูง iff >=2 drivers at 2; ปานกลาง iff >=1 at 2 or >=2 at >=1; else ต่ำ. "
                   "REFUSED evaluated at 0 (lo) and 2 (hi). PROPOSAL, not in Toledo.",
           "days": table, "dams": {k: {kk: vv for kk, vv in v.items() if kk != "series_30d"}
                                   for k, v in dams.items()},
           "falsifiers": [
               "max C.12 daily max over 1-3 Oct < max over 28-30 Sep -> window wrong (peak earlier)",
               "no C.12 daily max >= +2.00 m MSL on any of 1-3 Oct -> 'สูงสุด' magnitude wrong",
               "any C.12 daily max on 4-8 Oct > max over 1-3 Oct -> window too early",
               "C.13 discharge < 1750 m3/s before 29 Sep 12:00 ICT -> milder than stated",
               "C.2 discharge still rising on 30 Sep-1 Oct -> secondary window 4-8 Oct may be worse",
               "Pasak release still 2.16 MCM/day and storage < 871.5 MCM on 1 Oct -> forced-release flag wrong",
               "any Bangkok gauge rain_24h >= 80 mm on 29 Sep-5 Oct -> rain driver wrong",
           ]}
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    path = FORECAST_DIR / f"bkk_peak_window_{now}.json"
    if path.exists():
        print(f"refusing to overwrite {path}", file=sys.stderr)
        return 1
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(json.dumps({"written": str(path.relative_to(ROOT)),
                      "days": [(r["date_ict"], r["levels"], r["combined"], r["label_worst_first"])
                               for r in table]}, ensure_ascii=False, indent=1))
    if argv and "--dams" in argv:
        print(json.dumps(dams, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
