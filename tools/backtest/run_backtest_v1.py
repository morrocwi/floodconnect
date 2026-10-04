#!/usr/bin/env python3
"""run_backtest_v1.py -- PROP-FLOOD-06 PROPOSAL, unverified.

Falsifier loop v1: re-runs the 217 unit-days from raw/backtest/events.yaml through
the v3 (PARTIAL-mode/C_H) engine, AND adds new unit-days built from Thai official
history (HII/thaiwater telemetry, BMA pumps_2569.csv + canal_normal_levels.yaml)
in place of GloFAS wherever that history exists, per this check's brief.

Scope: writes only raw/backtest/results_v1.jsonl (new file). Does not edit
events.yaml, units.yaml, or any existing tracked file. Not committed as part of
this change.
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from prop_flood_06_v3 import full_tier_v3, coverage_vector, coverage_score  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_yaml(path):
    import yaml
    with open(os.path.join(REPO, path)) as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(os.path.join(REPO, path)) as f:
        return json.load(f)


UNITS = load_yaml("raw/backtest/units.yaml")["units"]
UNITS_BY_ID = {u["id"]: u for u in UNITS}
EVENTS = load_yaml("raw/backtest/events.yaml")["units"]
CAP_ADD = load_yaml("sources/capacity_ledger_additions.yaml")["additions"]
CANAL_NORMAL = load_yaml("sources/canal_normal_levels.yaml")["canals"]

C_VALUES = [0.5, 1.0]
H_VALUES = [24, 48]

rows_out = []

# Flooded-day ground truth already established in events.yaml (from case cards) --
# reused here as the single source of truth for any date this backtest also covers,
# rather than re-guessing a window; this repo's own docs/knowledge case cards are the
# provenance, not this script.
GT_FLOODED = {}
for ev in EVENTS:
    GT_FLOODED[(ev["unit"], ev["date"])] = ev["flooded_significantly"]


def emit(unit, date, c, H, inputs, pumps_declared, R_H, D_H, F_H, flooded, gt_source, gt_tag, notes=""):
    readout = full_tier_v3(
        {"pumps_declared": pumps_declared, "R_H": R_H, "D_H": D_H, "F_H": F_H, "inputs": inputs}, H
    )
    rows_out.append({
        "unit": unit, "date": date, "c": c, "H": H,
        "mode": readout.mode, "tier": readout.tier,
        "coverage_n_of_7": round(readout.coverage * 7, 2),
        "based_on": readout.based_on, "missing": readout.missing,
        "promoters_fired": readout.promoters_fired,
        "terms_present": sorted(readout.terms_present),
        "S_H": readout.S_H,
        "flooded_significantly": flooded,
        "ground_truth_source": gt_source, "ground_truth_tag": gt_tag,
        "notes": notes,
    })


# ---------------------------------------------------------------------------
# Part A: re-run the 217 v0 unit-days (GloFAS-era, HATYAI/NAN/CHIANGMAI/AYUTTHAYA/
# BANGKOK_EAST) through the v3 engine, unchanged inputs, only the readout logic
# changes (C_H case split + PARTIAL mode instead of literal min()+REFUSED-on-any-gap).
# ---------------------------------------------------------------------------
for ev in EVENTS:
    unit_id = ev["unit"]
    u = UNITS_BY_ID[unit_id]
    pumps_declared = (u["pumps"]["P_U_m3s"] or 0) > 0
    A_U_m2 = u["A_U"]["value_km2"] * 1e6
    Q_cap_o = None
    if unit_id == "AYUTTHAYA_BANGBAN":
        Q_cap_o = u["outlet"]["Q_cap_o_m3s"]["value"]
    elif unit_id == "BANGKOK_EAST":
        Q_cap_o = u["outlet"]["Q_cap_o_m3s"]["value"]
    # HATYAI/NAN/CHIANGMAI: Q_cap_o OPEN or split pre/post date in v0 -- keep OPEN here
    # (these units get their real capacity from Part B's Thai-history rows instead).

    Q_o_now = ev.get("Q_o_now_m3s") if ev.get("Q_o_now_credible", True) else None
    Q_in_up = ev.get("Q_in_up_m3s")
    rain = ev.get("rain_mm_24h")

    for c in C_VALUES:
        for H in H_VALUES:
            R_H = None
            if Q_cap_o is not None and Q_o_now is not None:
                R_H = max(0.0, Q_cap_o - Q_o_now) * H * 3600
            D_H = 0.0 if not pumps_declared else None  # v0 units only declare pumps for BANGKOK_EAST
            if unit_id == "BANGKOK_EAST" and pumps_declared:
                D_H = u["pumps"]["P_U_m3s"] * H * 3600  # v0 used installed capacity, no running-state history
            F_H = None
            if rain is not None:
                F_H = c * A_U_m2 * (rain / 1000.0)
                if Q_in_up is not None:
                    F_H += Q_in_up * H * 3600
            elif Q_in_up is not None:
                F_H = Q_in_up * H * 3600
            inputs = {
                "rain_24h_mm": rain, "Q_o_now": Q_o_now, "Q_cap_o": Q_cap_o,
                "pumps_running_count": (4 if unit_id == "BANGKOK_EAST" and pumps_declared else None),
                "Q_in_up": Q_in_up,
                "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None,
            }
            emit(unit_id, ev["date"], c, H, inputs, pumps_declared, R_H, D_H, F_H,
                 ev["flooded_significantly"], ev["ground_truth_source"], ev["ground_truth_tag"],
                 notes="v0-carryover, GloFAS/reanalysis, rerun through v3 C_H+PARTIAL engine")


# ---------------------------------------------------------------------------
# Part B: Thai official history replacing GloFAS -- HATYAI (X.44, 2565),
# NAN (N.1, 2567), CHIANGMAI (P.1, 2567).
# ---------------------------------------------------------------------------

def daily_from_hii(path, value_key="discharge"):
    """Returns {date_str: {'max':..,'any_present':bool}} from an HII waterlevel_graph
    archive (graph_data list of {datetime, value, value_out, discharge})."""
    d = load_json(path)["data"]["graph_data"]
    by_day = {}
    for row in d:
        day = row["datetime"][:10]
        v = row.get(value_key)
        if v is None:
            continue
        by_day.setdefault(day, []).append(v)
    return {day: max(vals) for day, vals in by_day.items()}


def daily_rain_from_era5(path):
    if not os.path.exists(os.path.join(REPO, path)):
        return {}
    d = load_json(path)["hourly"]
    by_day = {}
    for t, p in zip(d["time"], d["precipitation"]):
        day = t[:10]
        by_day.setdefault(day, 0.0)
        by_day[day] += (p or 0.0)
    return by_day


def daterange(d0, d1):
    cur = datetime.strptime(d0, "%Y-%m-%d")
    end = datetime.strptime(d1, "%Y-%m-%d")
    while cur <= end:
        yield cur.strftime("%Y-%m-%d")
        cur += timedelta(days=1)


# --- HATYAI (X.44, 2565 event) ---
x44 = {a["ledger_id_new"]: a for a in CAP_ADD}["led:U_hatyai_x44_station"]
qcap_hatyai = x44["Q_cap_o_m3s"]["value"]
discharge_hatyai = daily_from_hii("raw/backtest/hii_history/X44_2591_2565.json", "discharge")
rain_hatyai = daily_rain_from_era5("raw/backtest/rain/HATYAI_2022-11-15_2022-12-05.json")
HATYAI_FLOOD_DAYS = set(daterange("2022-11-30", "2022-12-03"))  # fallback if not in events.yaml
A_U_hatyai = UNITS_BY_ID["HATYAI"]["A_U"]["value_km2"] * 1e6

for day in daterange("2022-11-10", "2022-12-10"):
    q_now = discharge_hatyai.get(day)
    rain = rain_hatyai.get(day)
    flooded = GT_FLOODED.get(("HATYAI", day), day in HATYAI_FLOOD_DAYS)
    for c in C_VALUES:
        for H in H_VALUES:
            R_H = max(0.0, qcap_hatyai - q_now) * H * 3600 if q_now is not None else None
            F_H = c * A_U_hatyai * (rain / 1000.0) if rain is not None else None
            inputs = {"rain_24h_mm": rain, "Q_o_now": q_now, "Q_cap_o": qcap_hatyai,
                      "pumps_running_count": None, "Q_in_up": None,
                      "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None}
            emit("HATYAI", day, c, H, inputs, False, R_H, 0.0, F_H, flooded,
                 "raw/backtest/hii_history/X44_2591_2565.json + docs/knowledge/case_hatyai_2553_2565.md",
                 "MEASURED-history(X.44 discharge)/RELAYED(flood window)",
                 notes="X.44 real gauge Q_cap,o=qmax RELAYED; replaces GloFAS for this event")

# --- NAN (N.1, 2567 event) ---
n1 = {a["ledger_id_new"]: a for a in CAP_ADD}["led:U_nan_n1_station"]
qcap_nan = n1["Q_cap_o_m3s"]["value"]
discharge_nan = daily_from_hii("raw/backtest/hii_history/N1_3219_2567.json", "discharge")
rain_nan = daily_rain_from_era5("raw/backtest/rain/NAN_2024-08-15_2024-08-31.json")
NAN_FLOOD_DAYS = set(daterange("2024-08-19", "2024-08-30"))
A_U_nan = UNITS_BY_ID["NAN"]["A_U"]["value_km2"] * 1e6

for day in daterange("2024-08-01", "2024-09-15"):
    q_now = discharge_nan.get(day)
    rain = rain_nan.get(day)  # None outside the ERA5 fetched sub-window (absent, not zero)
    flooded = GT_FLOODED.get(("NAN", day), day in NAN_FLOOD_DAYS)
    for c in C_VALUES:
        for H in H_VALUES:
            R_H = max(0.0, qcap_nan - q_now) * H * 3600 if q_now is not None else None
            F_H = c * A_U_nan * (rain / 1000.0) if rain is not None else None
            inputs = {"rain_24h_mm": rain, "Q_o_now": q_now, "Q_cap_o": qcap_nan,
                      "pumps_running_count": None, "Q_in_up": None,
                      "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None}
            emit("NAN", day, c, H, inputs, False, R_H, 0.0, F_H, flooded,
                 "raw/backtest/hii_history/N1_3219_2567.json + docs/knowledge/case_nan_2567.md",
                 "MEASURED-history(N.1 discharge)/RELAYED(flood window dates)",
                 notes="N.1 real gauge Q_cap,o=qmax RELAYED-HII-metadata; replaces GloFAS; window +-10d around 2024-08-22 peak plus control days")

# --- CHIANGMAI (P.1, 2567 event) ---
p1 = {a["ledger_id_new"]: a for a in CAP_ADD}["led:U_chiangmai_p1_station"]
qcap_cm = p1["Q_cap_o_m3s"]["value"]
discharge_cm = daily_from_hii("raw/backtest/hii_history/P1_3226_2567.json", "discharge")
rain_cm = daily_rain_from_era5("raw/backtest/rain/CHIANGMAI_2024-09-22_2024-10-07.json")
CM_FLOOD_DAYS = set(daterange("2024-10-03", "2024-10-07"))  # INSTINCT window around the task-given 5 Oct onset
A_U_cm = UNITS_BY_ID["CHIANGMAI"]["A_U"]["value_km2"] * 1e6

for day in daterange("2024-09-15", "2024-10-15"):
    q_now = discharge_cm.get(day)
    rain = rain_cm.get(day)
    flooded = GT_FLOODED.get(("CHIANGMAI", day), day in CM_FLOOD_DAYS)
    for c in C_VALUES:
        for H in H_VALUES:
            R_H = max(0.0, qcap_cm - q_now) * H * 3600 if q_now is not None else None
            F_H = c * A_U_cm * (rain / 1000.0) if rain is not None else None
            inputs = {"rain_24h_mm": rain, "Q_o_now": q_now, "Q_cap_o": qcap_cm,
                      "pumps_running_count": None, "Q_in_up": None,
                      "canal_level_m": None, "canal_warning_m": None, "canal_critical_m": None, "canal_bank_m": None}
            emit("CHIANGMAI", day, c, H, inputs, False, R_H, 0.0, F_H, flooded,
                 "raw/backtest/hii_history/P1_3226_2567.json + founder's instructions (P.1 5 Oct 2024 onset)",
                 "MEASURED-history(P.1 discharge)/RELAYED(onset date)",
                 notes="P.1 real gauge Q_cap,o=qmax RELAYED-HII-metadata; replaces GloFAS; +-10d window around 2024-10-05")

# ---------------------------------------------------------------------------
# Part C: BANGKOK_EAST 2569 -- real pumps_2569.csv + canal_normal_levels.yaml lines
# ---------------------------------------------------------------------------
pump_codes = {"ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"}
canal_rows = []
pump_rows = []
with open(os.path.join(REPO, "raw/backtest/pumps_2569.csv")) as f:
    for r in csv.DictReader(f):
        day = r["observed_at_utc"][:10]
        if r["variable"] == "pump_level_m" and r["station_code"] in pump_codes:
            pump_rows.append((day, r["station_code"], r["status"]))
        elif r["variable"] in ("canal_water_level_m", "canal_level_0700_m") and r["value"]:
            try:
                val = float(r["value"])
                warn = float(r["warning"]) if r["warning"] else None
                crit = float(r["critical"]) if r["critical"] else None
                bank = float(r["bank"]) if r["bank"] else None
            except ValueError:
                continue
            canal_rows.append((day, r["station_code"] or r["station_name"], val, warn, crit, bank))

rain_bkk_2569 = {}
with open(os.path.join(REPO, "raw/backtest/pumps_2569.csv")) as f:
    for r in csv.DictReader(f):
        if r["variable"] == "rain_24h_mm" and r["value"]:
            day = r["observed_at_utc"][:10]
            rain_bkk_2569.setdefault(day, []).append(float(r["value"]))

BKK_2569_DAYS = sorted({d for d, *_ in canal_rows} | {d for d, *_ in pump_rows})
pumps_total_installed = 1200.0  # led:bkk_total_pumping_phranakhon, RELAYED, per units.yaml

for day in BKK_2569_DAYS:
    day_canal = [c for c in canal_rows if c[0] == day]
    # worst (max relative-to-bank) reading of the day drives the promoter check
    worst = None
    worst_ratio = -1e9
    for (_, code, val, warn, crit, bank) in day_canal:
        ref = bank or crit or warn or 1.0
        ratio = val / ref if ref else 0
        if ratio > worst_ratio:
            worst_ratio, worst = ratio, (code, val, warn, crit, bank)
    day_pumps = [p for p in pump_rows if p[0] == day]
    running = sum(1 for (_, code, status) in day_pumps if status == "ปกติ")
    n_pump_readings = len(day_pumps)
    running_frac = (running / n_pump_readings) if n_pump_readings else None
    rain = sum(rain_bkk_2569.get(day, [])) if rain_bkk_2569.get(day) else None
    computed_flooded = worst is not None and worst[4] is not None and worst[1] >= worst[4]  # >= bank level
    flooded = GT_FLOODED.get(("BANGKOK_EAST", day), computed_flooded)

    for c in C_VALUES:
        for H in H_VALUES:
            D_H = (pumps_total_installed * (running_frac if running_frac is not None else 0.0)) * H * 3600
            F_H = c * (UNITS_BY_ID["BANGKOK_EAST"]["A_U"]["value_km2"] * 1e6) * ((rain or 0.0) / 1000.0) if rain is not None else None
            inputs = {
                "rain_24h_mm": rain, "Q_o_now": None, "Q_cap_o": None,  # Chao Phraya discharge not available for 2569 in this check
                "pumps_running_count": running if n_pump_readings else None,
                "Q_in_up": None,
                "canal_level_m": worst[1] if worst else None,
                "canal_warning_m": worst[2] if worst else None,
                "canal_critical_m": worst[3] if worst else None,
                "canal_bank_m": worst[4] if worst else None,
            }
            emit("BANGKOK_EAST", day, c, H, inputs, True, None, D_H, F_H, flooded,
                 "raw/backtest/pumps_2569.csv (BMA official_telemetry) + sources/canal_normal_levels.yaml",
                 "MEASURED-on-backtest(canal level vs BMA-declared lines)/MEASURED(pump running status)",
                 notes="real running pump count (ST.SPS.01-04), real canal level vs BMA warning/critical/bank; outlet (Chao Phraya) discharge not available for 2569 -> OUTLET_CAPACITY_UNKNOWN, C_H=D_H (PARTIAL flag on outlet term)")

# ---------------------------------------------------------------------------
out_path = os.path.join(REPO, "raw/backtest/results_v1.jsonl")
with open(out_path, "w") as f:
    for row in rows_out:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print(f"wrote {len(rows_out)} rows to {out_path}")
