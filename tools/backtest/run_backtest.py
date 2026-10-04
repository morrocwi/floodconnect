#!/usr/bin/env python3
"""run_backtest.py -- PROP-FLOOD-06 PROPOSAL, unverified.

Builds the >=100-unit-day event catalogue (raw/backtest/events.yaml), runs
tools/backtest/prop_flood_06.py over every (unit-day x c x pump-scenario x horizon)
combination using the raw historical data fetched by fetch_historical.py, and writes:
  - raw/backtest/results.jsonl   (one row per combination, streamed -- no big DataFrame)
  - docs/BACKTEST_PROP_FLOOD_06_v0.md (Thai, human-readable report)

Memory discipline: everything is streamed dict-by-dict / line-by-line. No pandas.
Founder brief (17:30, verbatim): "...จำลอง protocol จริงๆ อย่างน้อย 100 ครั้งจากเหตุการณ์จริง
ด้วยข้อมูลเก่า เพื่อดูว่าการคำนวณของเราให้ระบบถูกต้องไหม"

Does NOT commit. Does NOT edit any existing tracked file.
"""
import json
from datetime import date, timedelta
from pathlib import Path

import yaml

from prop_flood_06 import evaluate, PROPOSAL_TAG

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "raw" / "backtest"
DOCS = ROOT / "docs"


def daterange(start, end):
    d = date.fromisoformat(start)
    e = date.fromisoformat(end)
    while d <= e:
        yield d
        d += timedelta(days=1)


def load_rain(unit_file):
    p = RAW / "rain" / unit_file
    data = json.loads(p.read_text())
    times = data["hourly"]["time"]
    precip = data["hourly"]["precipitation"]
    by_day = {}
    for t, v in zip(times, precip):
        day = t[:10]
        by_day.setdefault(day, []).append(v if v is not None else 0.0)
    return by_day


def load_flood_daily(flood_file):
    p = RAW / "flood" / flood_file
    if not p.exists():
        return {}, None
    data = json.loads(p.read_text())
    if "daily" not in data:
        return {}, None
    times = data["daily"]["time"]
    disc = data["daily"]["river_discharge"]
    return dict(zip(times, disc)), (data.get("latitude"), data.get("longitude"))


# ---------------------------------------------------------------------------
# Event catalogue definition (mirrors raw/backtest/units.yaml narratively; see that
# file for full sourcing/tags of every constant used here).
# ---------------------------------------------------------------------------

EVENTS = [
    # HATYAI -- founder: largest block, Hat Yai stress-tested
    dict(unit="HATYAI", rain_file="HATYAI_2010-10-20_2010-11-10.json",
         flood_file="HATYAI_CANAL_2010-10-20_2010-11-10.json",
         start="2010-10-20", end="2010-11-10",
         true_window=("2010-10-31", "2010-11-03"),
         event_label="hatyai_2553", ground_truth_source="docs/knowledge/case_hatyai_2553_2565.md",
         ground_truth_tag="RELAYED"),
    dict(unit="HATYAI", rain_file="HATYAI_2022-11-15_2022-12-05.json",
         flood_file="HATYAI_CANAL_2022-11-15_2022-12-05.json",
         start="2022-11-15", end="2022-12-05",
         true_window=("2022-11-30", "2022-12-02"),
         event_label="hatyai_2565", ground_truth_source="docs/knowledge/case_hatyai_2553_2565.md",
         ground_truth_tag="INSTINCT (card only names the month, not the exact day; exact 3-day window is this backtest's own placement, flagged)"),
    dict(unit="HATYAI", rain_file="HATYAI_2015-12-01_2015-12-10.json",
         flood_file="HATYAI_CANAL_2015-12-01_2015-12-10.json",
         start="2015-12-01", end="2015-12-10", true_window=None,
         event_label="hatyai_control_2015", ground_truth_source="no known flood reported this window (CONTROL)",
         ground_truth_tag="INSTINCT (absence-of-report, not a positive confirmation)"),
    dict(unit="HATYAI", rain_file="HATYAI_2017-02-01_2017-02-10.json",
         flood_file="HATYAI_CANAL_2017-02-01_2017-02-10.json",
         start="2017-02-01", end="2017-02-10", true_window=None,
         event_label="hatyai_control_2017", ground_truth_source="CONTROL (dry-season window)",
         ground_truth_tag="INSTINCT"),
    dict(unit="HATYAI", rain_file="HATYAI_2019-03-01_2019-03-10.json",
         flood_file="HATYAI_CANAL_2019-03-01_2019-03-10.json",
         start="2019-03-01", end="2019-03-10", true_window=None,
         event_label="hatyai_control_2019", ground_truth_source="CONTROL (dry-season window)",
         ground_truth_tag="INSTINCT"),
    dict(unit="HATYAI", rain_file="HATYAI_2021-01-15_2021-01-24.json",
         flood_file="HATYAI_CANAL_2021-01-15_2021-01-24.json",
         start="2021-01-15", end="2021-01-24", true_window=None,
         event_label="hatyai_control_2021", ground_truth_source="CONTROL (dry-season window)",
         ground_truth_tag="INSTINCT"),

    # NAN
    dict(unit="NAN", rain_file="NAN_2024-08-15_2024-08-31.json",
         flood_file="NAN_TOWN_2024-08-15_2024-08-31.json",
         start="2024-08-15", end="2024-08-31",
         true_window=("2024-08-19", "2024-08-25"),
         event_label="nan_2567", ground_truth_source="docs/knowledge/case_nan_2567.md, card_research_nan_flood_2567.md",
         ground_truth_tag="RELAYED for 19-20 Aug (specific reported rain-day), INSTINCT extension for the rest of the 7-day window"),
    dict(unit="NAN", rain_file="NAN_2024-02-01_2024-02-10.json",
         flood_file="NAN_TOWN_2024-02-01_2024-02-10.json",
         start="2024-02-01", end="2024-02-10", true_window=None,
         event_label="nan_control_2024", ground_truth_source="CONTROL (dry-season window)",
         ground_truth_tag="INSTINCT"),

    # CHIANGMAI -- two peaks (25 Sep, 5 Oct 2567) per case card
    dict(unit="CHIANGMAI", rain_file="CHIANGMAI_2024-09-22_2024-10-07.json",
         flood_file="CHIANGMAI_TOWN_2024-09-22_2024-10-07.json",
         start="2024-09-22", end="2024-10-07",
         true_windows=[("2024-09-24", "2024-09-30"), ("2024-10-04", "2024-10-06")],
         event_label="chiangmai_2567", ground_truth_source="docs/knowledge/case_chiangmai_2567.md",
         ground_truth_tag="RELAYED (exact peak dates 25 ก.ย. and 5 ต.ค. from theactive.thaipbs / provincial governor; surrounding days in each window are INSTINCT extension)"),
    dict(unit="CHIANGMAI", rain_file="CHIANGMAI_2024-03-01_2024-03-10.json",
         flood_file="CHIANGMAI_TOWN_2024-03-01_2024-03-10.json",
         start="2024-03-01", end="2024-03-10", true_window=None,
         event_label="chiangmai_control_2024", ground_truth_source="CONTROL (dry-season window)",
         ground_truth_tag="INSTINCT"),

    # AYUTTHAYA / BANG BAN 2554
    dict(unit="AYUTTHAYA_BANGBAN", rain_file="AYUTTHAYA_BANGBAN_2011-09-20_2011-10-20.json",
         flood_file="AYUTTHAYA_BANGBAN_2011-09-20_2011-10-20.json",
         flood_file_up="NAKHONSAWAN_C2_UPSTREAM_2011-09-20_2011-10-20.json",
         start="2011-09-20", end="2011-10-20",
         true_window=("2011-10-01", "2011-10-15"),
         event_label="ayutthaya_2554", ground_truth_source="docs/knowledge/case_2554_chaophraya_bangkok.md + general knowledge of the 2554 mahaoutokphai timeline",
         ground_truth_tag="INSTINCT (case card gives no Ayutthaya-specific per-day dates; this window is this backtest's own placement of the well-known Oct 2011 Ayutthaya flood peak, not independently re-verified this check)"),
    dict(unit="AYUTTHAYA_BANGBAN", rain_file="AYUTTHAYA_BANGBAN_2012-02-01_2012-02-10.json",
         flood_file="AYUTTHAYA_BANGBAN_2012-02-01_2012-02-10.json",
         flood_file_up="NAKHONSAWAN_C2_UPSTREAM_2012-02-01_2012-02-10.json",
         start="2012-02-01", end="2012-02-10", true_window=None,
         event_label="ayutthaya_control_2012", ground_truth_source="CONTROL (dry-season window, post-2554 recession)",
         ground_truth_tag="INSTINCT"),

    # BANGKOK EAST 2554 + 2569 (this week)
    dict(unit="BANGKOK_EAST", rain_file="BANGKOK_EAST_2011-10-20_2011-11-10.json",
         flood_file="BANGKOK_CHAOPHRAYA_2011-10-20_2011-11-10.json",
         start="2011-10-20", end="2011-11-10",
         true_window=("2011-10-25", "2011-11-05"),
         event_label="bangkok_2554", ground_truth_source="docs/knowledge/case_2554_chaophraya_bangkok.md",
         ground_truth_tag="INSTINCT (card describes Oct-Nov 2554 qualitatively, no per-day flags for the east zone specifically; window is this backtest's own placement)"),
    dict(unit="BANGKOK_EAST", rain_file="BANGKOK_EAST_2026-09-20_2026-09-27.json",
         flood_file="BANGKOK_CHAOPHRAYA_2026-09-20_2026-09-27.json",
         start="2026-09-20", end="2026-09-27",
         true_window=("2026-09-24", "2026-09-27"),
         event_label="bangkok_2569", ground_truth_source="docs/knowledge/case_bkk_2569.md, community_reports_2026-09-26.md (this project's own MEASURED community reports)",
         ground_truth_tag="MEASURED (community reports) + RELAYED (news) for the exact days -- this is the current live event, not fully closed out as of 2026-09-27"),
    dict(unit="BANGKOK_EAST", rain_file="BANGKOK_EAST_2026-02-01_2026-02-10.json",
         flood_file="BANGKOK_CHAOPHRAYA_2026-02-01_2026-02-10.json",
         start="2026-02-01", end="2026-02-10", true_window=None,
         event_label="bangkok_control_2026", ground_truth_source="CONTROL (dry-season window)",
         ground_truth_tag="INSTINCT"),
]

# Non-credible flood-discharge cells (see units.yaml Q_o_now_caveat) -- their Q_o,now /
# Q_in,up readings are NOT plugged into the model even though the raw files exist;
# doing so would fabricate a false-precision number. This set is checked at run time.
NON_CREDIBLE_FLOOD_UNITS = {"HATYAI", "NAN", "CHIANGMAI"}

UNIT_STATIC = {
    "HATYAI": dict(A_U_km2=28.27, c_low=0.5, c_high=1.0,
                   Q_cap_pre=465, Q_cap_post=1200, cutover=date(2022, 11, 1),
                   P_installed=0, has_outlet_cap=True, has_credible_Qnow=False,
                   has_upstream=False),
    "NAN": dict(A_U_km2=78.54, c_low=0.5, c_high=1.0,
                Q_cap_pre=None, Q_cap_post=None, cutover=None,
                P_installed=0, has_outlet_cap=False, has_credible_Qnow=False,
                has_upstream=False),
    "CHIANGMAI": dict(A_U_km2=78.54, c_low=0.5, c_high=1.0,
                       Q_cap_pre=None, Q_cap_post=None, cutover=None,
                       P_installed=0, has_outlet_cap=False, has_credible_Qnow=False,
                       has_upstream=False),
    "AYUTTHAYA_BANGBAN": dict(A_U_km2=78.54, c_low=0.5, c_high=1.0,
                               Q_cap_pre=3100, Q_cap_post=3100, cutover=None,
                               P_installed=0, has_outlet_cap=True, has_credible_Qnow=True,
                               has_upstream=True),
    "BANGKOK_EAST": dict(A_U_km2=78.54, c_low=0.5, c_high=1.0,
                          Q_cap_pre=3100, Q_cap_post=3100, cutover=None,
                          P_installed=1200, has_outlet_cap=True, has_credible_Qnow=True,
                          has_upstream=False),
}


def in_window(d, window):
    if window is None:
        return False
    s, e = window
    return date.fromisoformat(s) <= d <= date.fromisoformat(e)


def ground_truth_for(ev, d):
    if "true_windows" in ev:
        for w in ev["true_windows"]:
            if in_window(d, w):
                return True
        return False
    return in_window(d, ev.get("true_window"))


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    events_out = {"proposal_tag": PROPOSAL_TAG, "generated_by": "tools/backtest/run_backtest.py",
                  "units": []}
    results_path = RAW / "results.jsonl"
    unit_day_count = 0
    stats = {}  # unit -> {"true":n,"false":n}
    rows_for_doc = []

    with results_path.open("w") as results_f:
        for ev in EVENTS:
            unit = ev["unit"]
            static = UNIT_STATIC[unit]
            rain_by_day = load_rain(ev["rain_file"])
            flood_by_day, resolved_coords = load_flood_daily(ev["flood_file"])
            up_by_day = {}
            if ev.get("flood_file_up"):
                up_by_day, _ = load_flood_daily(ev["flood_file_up"])

            for d in daterange(ev["start"], ev["end"]):
                dstr = d.isoformat()
                rain_hourly = rain_by_day.get(dstr)
                # need next day's first hours too for H=48; simplest: concatenate this
                # day + next day's hourly rain (if available) to get up to 48h horizon
                next_d = (d + timedelta(days=1)).isoformat()
                next_rain = rain_by_day.get(next_d, [])
                rain_48h = (rain_hourly or []) + next_rain
                if rain_hourly is None or len(rain_hourly) < 24:
                    continue  # no data this day, skip (do not fabricate)

                gt = ground_truth_for(ev, d)
                unit_day_count += 1
                stats.setdefault(unit, {"true": 0, "false": 0})
                stats[unit]["true" if gt else "false"] += 1

                Q_now_today = flood_by_day.get(dstr)
                Q_up_today = up_by_day.get(dstr) if up_by_day else None
                credible = static["has_credible_Qnow"] and Q_now_today is not None

                gt_row = {
                    "unit": unit, "date": dstr, "event_label": ev["event_label"],
                    "flooded_significantly": gt,
                    "ground_truth_source": ev["ground_truth_source"],
                    "ground_truth_tag": ev["ground_truth_tag"],
                    "rain_mm_24h": round(sum(rain_hourly[:24]), 2),
                    "Q_o_now_m3s": Q_now_today, "Q_o_now_credible": credible,
                    "Q_in_up_m3s": Q_up_today,
                }
                events_out["units"].append(gt_row)

                for H in (24, 48):
                    rain_series = rain_48h[:H] if H == 48 else rain_hourly[:H]
                    if len(rain_series) < H:
                        continue
                    up_series = None
                    if static["has_upstream"] and Q_up_today is not None:
                        up_series = [Q_up_today] * H  # daily value held constant (INSTINCT)

                    Q_cap = static["Q_cap_pre"]
                    if static["cutover"] and d >= static["cutover"]:
                        Q_cap = static["Q_cap_post"]

                    outlets = [{
                        "element_th": unit, "Q_cap_o": Q_cap,
                        "Q_o_now": Q_now_today if credible else None,
                        "credible": credible,
                    }] if static["has_outlet_cap"] else []
                    if not static["has_outlet_cap"]:
                        outlets = [{"element_th": unit, "Q_cap_o": None, "Q_o_now": None, "credible": False}]

                    for c_label, c_val in (("c_low", static["c_low"]), ("c_high", static["c_high"])):
                        for pump_label, P_run in (("pumps_installed", static["P_installed"]),
                                                    ("pumps_zero", 0)):
                            unit_day = {
                                "outlets": outlets, "P_run_m3s": P_run,
                                "c_U": c_val, "A_U_km2": static["A_U_km2"],
                                "rain_mm_hourly": rain_series,
                                "Q_in_up_m3s_hourly": up_series,
                            }
                            result = evaluate(unit_day, H)
                            row = {
                                "unit": unit, "date": dstr, "event_label": ev["event_label"],
                                "H": H, "c": c_label, "pump_scenario": pump_label,
                                "flooded_significantly": gt, **result,
                            }
                            results_f.write(json.dumps(row) + "\n")
                            rows_for_doc.append(row)

    (RAW / "events.yaml").write_text(yaml.safe_dump(events_out, allow_unicode=True, sort_keys=False))
    write_report(rows_for_doc, unit_day_count, stats)
    print(f"unit-days={unit_day_count} results_rows={len(rows_for_doc)}")


def write_report(rows, unit_day_count, stats):
    total = len(rows)
    refused = sum(1 for r in rows if r["refused"])
    refused_by_code = {}
    for r in rows:
        if r["refused"]:
            refused_by_code[r["code"]] = refused_by_code.get(r["code"], 0) + 1

    # confusion matrix: tier collapse L3-L5="act now", L0-L2="time"; only non-refused rows
    resolved = [r for r in rows if not r["refused"]]
    conf = {"act_flooded": 0, "act_notflooded": 0, "time_flooded": 0, "time_notflooded": 0}
    per_unit_conf = {}
    for r in resolved:
        act_now = r["tier"] in ("L3", "L4", "L5")
        flooded = r["flooded_significantly"]
        key = ("act" if act_now else "time") + ("_flooded" if flooded else "_notflooded")
        conf[key] += 1
        pu = per_unit_conf.setdefault(r["unit"], {"act_flooded": 0, "act_notflooded": 0,
                                                     "time_flooded": 0, "time_notflooded": 0})
        pu[key] += 1

    hits = conf["act_flooded"] + conf["time_notflooded"]
    misses = conf["time_flooded"]  # flooded but ladder said "time" (L0-L2) -- late/missed
    false_alarms = conf["act_notflooded"]  # said act-now but nothing happened
    denom = sum(conf.values())
    hit_rate = hits / denom if denom else None
    miss_rate = misses / (conf["act_flooded"] + conf["time_flooded"]) if (conf["act_flooded"] + conf["time_flooded"]) else None
    fa_rate = false_alarms / (conf["act_notflooded"] + conf["time_notflooded"]) if (conf["act_notflooded"] + conf["time_notflooded"]) else None

    # Hat Yai lead time: for hatyai_2553/2565, find earliest hour (day+H) tier reached
    # L3/L4/L5 before the first "true" day, per c=c_high/pumps_zero/H=24 (worst-case
    # pump-off, upper-bound runoff coefficient) -- report both events.
    def hatyai_lead_time(event_label):
        ev_rows = sorted(
            [r for r in rows if r["unit"] == "HATYAI" and r["event_label"] == event_label
             and r["H"] == 24 and r["c"] == "c_high" and r["pump_scenario"] == "pumps_zero"],
            key=lambda r: r["date"])
        first_true_date = None
        first_act_date = None
        for r in ev_rows:
            if r["flooded_significantly"] and first_true_date is None:
                first_true_date = r["date"]
            if (not r["refused"]) and r["tier"] in ("L3", "L4", "L5") and first_act_date is None:
                first_act_date = r["date"]
        return ev_rows, first_true_date, first_act_date

    hy53_rows, hy53_true, hy53_act = hatyai_lead_time("hatyai_2553")
    hy65_rows, hy65_true, hy65_act = hatyai_lead_time("hatyai_2565")

    def fmt_lead(true_d, act_d):
        if true_d is None:
            return "OPEN (no true-day found in this run)"
        if act_d is None:
            return f"NOT REACHED before/at flood day {true_d} in this run (ladder never hit L3+ under this scenario, or was REFUSED every day -- see table)"
        from datetime import date as _d
        delta = (_d.fromisoformat(true_d) - _d.fromisoformat(act_d)).days
        return f"first L3+ on {act_d}, flood day {true_d} -> lead time ~{delta} day(s) (24h buckets, not hour-precise)"

    lines = []
    lines.append("# BACKTEST_PROP_FLOOD_06_v0 — falsifier ยกกำลัง 100+ instantiation")
    lines.append("")
    lines.append(f"**{PROPOSAL_TAG}** — เอกสารนี้ทั้งฉบับรายงานผลการทดสอบข้อเสนอ ไม่ใช่ผลลัพธ์ของสมการ Toledo ที่ขึ้นทะเบียนแล้ว")
    lines.append("")
    lines.append("## คำสั่ง founder (verbatim, 17:30)")
    lines.append("")
    lines.append("> \"โดยเฉพาะเคสหาดใหญ่หนักมาก เราจำลอง protocol จริงๆ อย่างน้อย 100 ครั้งจากเหตุการณ์จริงด้วยข้อมูลเก่า เพื่อดูว่าการคำนวณของเราให้ระบบถูกต้องไหม\"")
    lines.append("")
    lines.append("## 1. วิธีการ (Method)")
    lines.append("")
    lines.append("- 5 หน่วยระบายน้ำ (`raw/backtest/units.yaml`): หาดใหญ่ (คลอง ร.1), น่าน (เมือง),")
    lines.append("  เชียงใหม่ (เมือง, แม่น้ำปิง), อยุธยา/บางบาล (เจ้าพระยาสายหลัก), กรุงเทพฯ ฝั่งตะวันออก")
    lines.append("  (แสนแสบ/ประเวศ/พระโขนง + ทางออกเจ้าพระยา)")
    lines.append("- ฝน: Open-Meteo Archive API (ERA5 reanalysis) รายชั่วโมง ที่จุดศูนย์กลางแต่ละหน่วย —")
    lines.append("  **VERIFIED** ดึงจริงงานนี้ ทุกคำตอบเก็บที่ `raw/backtest/rain/*.json`")
    lines.append("- น้ำในลำน้ำ/คลอง: Open-Meteo Flood API (GloFAS reanalysis) รายวัน —")
    lines.append("  **VERIFIED** ดึงจริง แต่ **RELAYED-tier ในการใช้งาน**: grid 0.25 องศาไม่สามารถ")
    lines.append("  แม่นยำระบุลำน้ำจริงของคลองอู่ตะเภา/แม่น้ำน่าน/แม่น้ำปิงที่จุดศูนย์กลางเมืองได้ (พบว่าให้")
    lines.append("  discharge ต่ำกว่า 10 m3/s แม้ในวันพีคน้ำท่วมจริง) — สามหน่วยนี้จึงถูกปฏิบัติเป็น")
    lines.append("  `NO_GAUGE_IN_UNIT`/ไม่ credible ไม่ใช่ใช้ตัวเลขที่ผิดอย่างเงียบๆ; อยุธยา/บางบาล และ")
    lines.append("  กรุงเทพฯ (จุด 13.73,100.50 และ 15.70,100.14) ให้ discharge ระดับพันลบ.ม./วินาที ที่")
    lines.append("  สมเหตุสมผล — ใช้เป็น Q_o,now/Q_in,up ได้ (tag RELAYED)")
    lines.append("- ฝนสำรอง (cross-check): NASA POWER daily, 3 หน้าต่างเหตุการณ์ (น่าน 2567, เชียงใหม่ 2567,")
    lines.append("  หาดใหญ่ 2565) รวม >=10 วัน — `raw/backtest/nasa_power/*.json` — **VERIFIED** ดึงจริง")
    lines.append("- น้ำขึ้นลง (tide): **ข้าม** ตามคำสั่งงาน — g_U(t):=1 ทุกกรณี (OPEN, ตามข้อกำหนดของ")
    lines.append("  proposal เอง)")
    lines.append("- สถานะปั๊มในอดีต: **ไม่ทราบ** — รันสองสถานการณ์เสมอ: `pumps_installed` (ใช้ความจุที่")
    lines.append("  ติดตั้งไว้ทั้งหมดจาก ledger, tag INSTINCT ว่าเดินเครื่องเต็ม) กับ `pumps_zero`")
    lines.append("  (D_H:=0 ทุกหน่วย)")
    lines.append(f"- รวมทดสอบ: **{unit_day_count} unit-day** (มากกว่าเป้า 100 ที่ founder สั่ง) x 2 ค่า c")
    lines.append(f"  (0.5/1.0) x 2 สถานการณ์ปั๊ม x 2 horizon (H=24,48) = **{total} readout rows**")
    lines.append("  (`raw/backtest/results.jsonl`)")
    lines.append("")
    lines.append("### unit-day นับตามหน่วย")
    lines.append("")
    lines.append("| หน่วย | true (ท่วมจริง) | false (control/ไม่ท่วม) | รวม |")
    lines.append("|---|---|---|---|")
    for u, s in stats.items():
        lines.append(f"| {u} | {s['true']} | {s['false']} | {s['true']+s['false']} |")
    lines.append("")
    lines.append("## 2. REFUSED share และเหตุผล")
    lines.append("")
    lines.append(f"REFUSED: **{refused}/{total}** ({100*refused/total:.1f}%)")
    lines.append("")
    lines.append("| refusal code | count |")
    lines.append("|---|---|")
    for code, n in sorted(refused_by_code.items(), key=lambda x: -x[1]):
        lines.append(f"| {code} | {n} |")
    lines.append("")
    lines.append("ตรงกับที่คาดไว้: น่าน/เชียงใหม่ REFUSED 100% (`OUTLET_CAPACITY_UNKNOWN`) เพราะไม่มีเอกสาร")
    lines.append("ใดใน repo นี้ระบุความจุ bankfull/design ของแม่น้ำน่านหรือแม่น้ำปิงผ่านตัวเมือง — เป็นช่องว่าง")
    lines.append("ข้อมูลจริง ไม่ใช่บั๊ก หาดใหญ่ REFUSED เกือบทั้งหมดด้วย `MISSING_INPUT` เพราะ GloFAS grid ไม่")
    lines.append("resolve คลอง ร.1 ให้ค่าที่น่าเชื่อถือ (ดู §5)")
    lines.append("")
    lines.append("### 2.1 การค้นพบสำคัญที่สุดของรอบนี้: ข้อขัดแย้งในตัว proposal เอง (D_H=0 ทำให้ AYUTTHAYA REFUSED 100%)")
    lines.append("")
    lines.append("AYUTTHAYA_BANGBAN มี Q_cap,o และ Q_o,now/Q_in,up ที่ resolve ได้จริง (proxy, ดู §6 ข้อ 3)")
    lines.append("แต่กลับ **REFUSED ทั้ง 320/320 แถว ด้วย `ZERO_CAPACITY_NONZERO_INFLOW`** — สาเหตุ: หน่วยนี้")
    lines.append("ไม่มีปั๊มประกาศไว้ (`NO_PUMPS_IN_UNIT`) จึง D_H(U):=0 เสมอ (ทั้งสองสถานการณ์ปั๊ม, เพราะ")
    lines.append("P_installed=0 อยู่แล้ว) เมื่อคำนวณตามตัวอักษรของสมการ `min(D_H,R_H)` จริงๆ ค่านี้จะเป็น")
    lines.append("`min(0, R_H) = 0` เสมอ **ไม่ใช่ R_H ตามที่ตาราง \"Three worked instantiations\" ของ**")
    lines.append("**proposal เองอ้างไว้** (\"อยุธยา ... OUTLET always (min(D_H,R_H)=R_H)\") — สอง")
    lines.append("ข้อความในเอกสาร PROP-FLOOD-06 ขัดกันเอง: นิยาม `D_H(U):=0` เมื่อไม่มีปั๊ม บวกกับนิยาม")
    lines.append("`min(D_H,R_H)` ตามตัวอักษร ให้ผล REFUSED เสมอสำหรับเมืองริมแม่น้ำที่ไม่มีปั๊ม แต่ตาราง")
    lines.append("ตัวอย่างของ proposal เองสมมติว่า D_H ที่ =0 จาก \"ไม่มีปั๊ม\" ไม่ควรถูกนับใน min() เลย")
    lines.append("(ให้ผลลัพธ์เป็น R_H ล้วนๆ) — **นี่คือ falsifier ที่แรงที่สุดของงานนี้ต่อตัว proposal เอง**")
    lines.append("ไม่ใช่แค่ต่อ threshold: สมการตามตัวอักษรใช้กับ \"เมืองริมแม่น้ำสายหลักไม่มีปั๊ม\" (เช่น")
    lines.append("อยุธยา, และน่าจะรวมน่าน/เชียงใหม่ด้วยถ้าเคย resolve ได้) ไม่ได้เลยจนกว่าจะแก้ไข")
    lines.append("นิยาม `min(D_H,R_H)` ให้ข้าม D_H เมื่อ `NO_PUMPS_IN_UNIT` เป็นจริง — **รายงานไว้ตรงนี้")
    lines.append("ไม่ได้แก้สมการเอง** ตามกติกา Toledo (ห้ามแก้ proposal โดยพลการ, ต้องส่งคืนให้ founder/")
    lines.append("ผู้เสนอ)")
    lines.append("")
    lines.append("## 3. Confusion matrix (รวม, เฉพาะ non-REFUSED rows) — MEASURED-on-backtest")
    lines.append("")
    lines.append("รวบ L3-L5 = \"ทำตอนนี้ (act now)\", L0-L2 = \"ยังมีเวลา (time)\"")
    lines.append("")
    lines.append("| | ท่วมจริง | ไม่ท่วม |")
    lines.append("|---|---|---|")
    lines.append(f"| ทำตอนนี้ (L3-L5) | {conf['act_flooded']} | {conf['act_notflooded']} (false alarm) |")
    lines.append(f"| ยังมีเวลา (L0-L2) | {conf['time_flooded']} (miss) | {conf['time_notflooded']} |")
    lines.append("")
    lines.append(f"- Hit rate (ถูกทั้งเตือนทันเวลาและนิ่งตอนไม่ท่วม) / non-refused: "
                  f"{hit_rate*100:.1f}%" if hit_rate is not None else "- Hit rate: OPEN (no resolved rows)")
    lines.append(f"- Miss rate (ท่วมจริงแต่ระบบบอกว่ายังมีเวลา): "
                  f"{miss_rate*100:.1f}%" if miss_rate is not None else "- Miss rate: OPEN")
    lines.append(f"- False-alarm rate (บอกทำตอนนี้แต่ไม่ท่วม): "
                  f"{fa_rate*100:.1f}%" if fa_rate is not None else "- False-alarm rate: OPEN")
    lines.append("")
    lines.append(f"non-REFUSED rows ทั้งหมด: {denom} จาก {total} ({100*denom/total:.1f}%) — ตัวเลข")
    lines.append("hit/miss/false-alarm ด้านบนคำนวณบนเศษส่วนนี้เท่านั้น ไม่ใช่ทั้ง 100%")
    lines.append("")
    lines.append("### แยกตามหน่วย (non-REFUSED rows เท่านั้น)")
    lines.append("")
    lines.append("| หน่วย | act&flooded | act&not | time&flooded(miss) | time&not |")
    lines.append("|---|---|---|---|---|")
    for u, pu in per_unit_conf.items():
        lines.append(f"| {u} | {pu['act_flooded']} | {pu['act_notflooded']} | {pu['time_flooded']} | {pu['time_notflooded']} |")
    lines.append("")
    lines.append("## 4. หาดใหญ่ — รายละเอียด (founder-flagged, largest block)")
    lines.append("")
    lines.append(f"- 2553 (2010): {fmt_lead(hy53_true, hy53_act)}")
    lines.append(f"- 2565 (2022): {fmt_lead(hy65_true, hy65_act)}")
    lines.append("")
    lines.append("Scenario ที่ใช้หาค่านี้: `H=24, c=1.0 (upper bound), pumps_zero` (worst-case ที่")
    lines.append("ควรเตือนได้ไวที่สุดถ้าระบบทำงานถูก) — ตารางเต็มของทุกวันในสองเหตุการณ์นี้ (tier ต่อวัน):")
    lines.append("")
    lines.append("| เหตุการณ์ | วันที่ | REFUSED? | tier | S_H | T_act | ท่วมจริง? |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in hy53_rows + hy65_rows:
        lines.append(f"| {r['event_label']} | {r['date']} | {r['refused']} | {r.get('tier')} | "
                      f"{r.get('S_H','-') if not r['refused'] else '-'} | {r.get('T_act','-') if not r['refused'] else '-'} | "
                      f"{r['flooded_significantly']} |")
    lines.append("")
    lines.append("## 5. ความอ่อนไหวของ threshold (sensitivity, รายงานเฉยๆ ไม่ปรับเอง)")
    lines.append("")
    lines.append("proposal กำหนด S_H bands ที่ 0.3/0.6/0.9/1.2 และ T_act ที่ 6h/24h/48h เป็น")
    lines.append("OPEN-for-founder-tuning มาแต่ต้น — งานนี้ **ไม่ได้ปรับค่าเหล่านี้เอง** ตามกติกา ")
    lines.append("(\"report, do not tune silently\") สิ่งที่สังเกตได้จากผลลัพธ์ที่ resolve ได้จริง (อยุธยา/")
    lines.append("กรุงเทพฯ เท่านั้น เพราะน่าน/เชียงใหม่/หาดใหญ่ REFUSED เกือบหมด):")
    lines.append("")
    resolved_by_unit_s = {}
    for r in resolved:
        resolved_by_unit_s.setdefault(r["unit"], []).append(r)
    for u, rs in resolved_by_unit_s.items():
        flooded_s = [r["S_H"] for r in rs if r["flooded_significantly"]]
        notflooded_s = [r["S_H"] for r in rs if not r["flooded_significantly"]]
        fs = f"min={min(flooded_s):.2f} max={max(flooded_s):.2f} n={len(flooded_s)}" if flooded_s else "n=0"
        ns = f"min={min(notflooded_s):.2f} max={max(notflooded_s):.2f} n={len(notflooded_s)}" if notflooded_s else "n=0"
        lines.append(f"- **{u}**: S_H บนวันท่วมจริง [{fs}]; S_H บนวันไม่ท่วม [{ns}]")
    lines.append("")
    lines.append("ถ้าช่วงสองกลุ่มทับกันมาก (overlap) แปลว่า threshold คงที่ตัวเดียวแยกไม่ออกสำหรับหน่วยนี้")
    lines.append("— ดูตัวเลขจริงด้านบนก่อนสรุป ไม่ตัดสินแทน founder")
    lines.append("")
    lines.append("## 6. ข้อจำกัดที่ต้องพูดตรงๆ (honest limitations)")
    lines.append("")
    lines.append("1. **ฝนเป็น reanalysis (ERA5) ไม่ใช่เครื่องวัดจริง** — ที่จุดภูเขา/เมืองเล็ก ค่าอาจต่ำกว่า")
    lines.append("   ฝนที่ตกจริงมาก (กรณีน่าน 2567: การประชุมทางการรายงานฝนจริง 388 มม. ขณะที่โมเดล")
    lines.append("   พยากรณ์ไว้เพียง 80 มม. ตามการ์ด `case_nan_2567.md` — ถ้า reanalysis ERA5 มีอคติ")
    lines.append("   คล้ายกัน ตัวเลข F_H ของน่านในรายงานนี้อาจ**ต่ำกว่าความจริง**)")
    lines.append("2. **GloFAS เป็นโมเดล ไม่ใช่สถานีวัดจริง** และที่ grid 0.25 องศา ไม่ resolve ลำน้ำ/คลอง")
    lines.append("   ขนาดกลาง-เล็ก (น่าน, ปิงที่เชียงใหม่, คลอง ร.1) เลย — ผลที่ resolve ได้จริง (อยุธยา,")
    lines.append("   กรุงเทพฯ) มีขนาด magnitude สมเหตุสมผลเทียบ ledger เอง (ดู §1) แต่ก็ยังเป็นโมเดล")
    lines.append("   ไม่ใช่ VERIFIED gauge")
    lines.append("3. **ความจุ outlet บางส่วนเป็น OPEN หรือ proxy แทนตัวจริง** — อยุธยา/บางบาล ใช้ 3,100")
    lines.append("   m3/s (ตัวเลข C.13 operational limit) เป็น **proxy INSTINCT** ไม่ใช่ค่าความจุเฉพาะจุด")
    lines.append("   ของอยุธยาเอง และคลองผันน้ำหลากบางบาล-บางไทร (1,200 m3/s) **ยังไม่สร้างเสร็จ**ใน")
    lines.append("   ปี 2554 ที่กำลัง backtest — การใช้ตัวเลขความจุปัจจุบันย้อนไปปี 2554 เป็นความคลาดเคลื่อน")
    lines.append("   เชิงวิธีวิจัยที่ต้องระวัง ไม่ใช่ error ที่ซ่อนไว้")
    lines.append("4. **ไม่มีสถานะปั๊มในอดีตจริง** — ใช้ 2 สถานการณ์ครอบ (ติดตั้งเต็ม/ปั๊ม=0) แทนความจริงที่")
    lines.append("   ไม่รู้; กรุงเทพฯ ฝั่งตะวันออกยังใช้ตัวเลขความจุปั๊มปี 2569 (1,200 m3/s ฝั่งพระนคร)")
    lines.append("   ย้อนไปทดสอบปี 2554 ด้วย — anachronism อีกจุดหนึ่ง ที่ flag ไว้ใน units.yaml")
    lines.append("5. **g_U(t) (tide/gravity derating) = 1 เสมอ** ตามคำสั่งงาน (ข้าม tide) — ไม่มีตาราง")
    lines.append("   น้ำขึ้นลงย้อนหลังในงานนี้ ทำให้ D_H ของกรุงเทพฯ อาจสูงเกินจริงในช่วงน้ำทะเลหนุน")
    lines.append("6. **T_act ใช้ discharge รายวันคงที่ตลอด 24 ชม.** (ไม่มี hourly discharge จริงจาก")
    lines.append("   GloFAS free tier) — เป็นการประมาณ INSTINCT ทำให้ T_act หยาบกว่าที่ proposal ตั้งใจ")
    lines.append("7. **ground truth วันต่อวันส่วนใหญ่เป็น INSTINCT** (การ์ดเคสให้แค่เดือน/ช่วงกว้างๆ ไม่ใช่")
    lines.append("   ทุกวัน) — เฉพาะบางวันที่มีวันที่ชัดเจนในการ์ด (เช่น เชียงใหม่ 25 ก.ย./5 ต.ค., น่าน 19-20")
    lines.append("   ส.ค.) ถึงเป็น RELAYED จริง")
    lines.append("8. **L5 (already-critical pre-check) ไม่ได้ implement** — ไม่มีข้อมูล \"ระดับน้ำเกิน")
    lines.append("   threshold แล้ว\" ที่เชื่อถือได้ในงานนี้ (proposal เองก็ทิ้ง threshold นี้เป็น OPEN)")
    lines.append("")
    lines.append("## 7. คำตัดสิน (verdict) — ผ่าน falsifier ของตัวเองไหม")
    lines.append("")
    lines.append("**ยังสรุปแบบ pass/fail เดียวไม่ได้ (OPEN, ตรงไปตรงมา):**")
    lines.append("")
    lines.append("- ที่ resolve เป็นตัวเลขได้จริง (อยุธยา, กรุงเทพฯ) จำนวน non-REFUSED rows มีจำกัด และ")
    lines.append("  ยังพึ่ง proxy/anachronism หลายจุด (§6) — ตัวเลข hit/miss/false-alarm ใน §3 เป็น")
    lines.append("  MEASURED-on-this-backtest จริง แต่ตัวอย่างเล็กเกินกว่าจะยืนยัน/ปฏิเสธ calibration ของ")
    lines.append("  threshold ปัจจุบันอย่างเด็ดขาด")
    lines.append("- ที่ founder ต้องการทดสอบมากที่สุด (หาดใหญ่) **REFUSED เกือบทั้งหมด** เพราะ")
    lines.append("  GloFAS ไม่ resolve คลอง ร.1 — นี่คือ falsifier ที่แรงที่สุดของรอบนี้: **ระบบเตือนภัย")
    lines.append("  แบบ PROP-FLOOD-06 ใช้กับหาดใหญ่ไม่ได้เลยด้วยข้อมูลฟรีระดับโลกชุดนี้** ต้องมี Q_o,now")
    lines.append("  ของคลอง ร.1 จากสถานีจริง (ONE037 / X.44 / ปตร.อู่ตะเภา, มีอยู่ใน sqlite แล้วแต่ไม่มี")
    lines.append("  ประวัติย้อนหลังที่ backtest นี้เข้าถึงได้) จึงจะตอบคำถามของ founder ได้ตรงๆ")
    lines.append("- น่าน/เชียงใหม่: REFUSED 100% เพราะไม่มีความจุ outlet ที่ประกาศไว้เลย — falsifier")
    lines.append("  ระดับ \"ยังตอบไม่ได้เลย\" ไม่ใช่ \"ตอบผิด\"")
    lines.append("- **อยุธยา/บางบาล: REFUSED 100% (320/320) ด้วย `ZERO_CAPACITY_NONZERO_INFLOW` แม้")
    lines.append("  Q_cap,o/Q_o,now/Q_in,up resolve ได้จริงทุกตัว** — สาเหตุคือข้อขัดแย้งในตัว proposal")
    lines.append("  เอง (§2.1), ไม่ใช่ข้อมูลขาด — นี่คือ falsifier ที่หนักที่สุดของรอบนี้: สมการตามตัวอักษร")
    lines.append("  ใช้กับเมืองริมแม่น้ำสายหลักที่ไม่มีปั๊มไม่ได้เลย ต้องแก้นิยาม `min(D_H,R_H)` ก่อน")
    lines.append("- **ข้อสรุปที่ยืนยันได้ (MEASURED-on-backtest)**: การอ้างว่า PROP-FLOOD-06 \"ให้ระบบ")
    lines.append("  ถูกต้อง\" ในสภาพข้อมูลปัจจุบันของ repo นี้เป็นการ**อ้างเกินหลักฐาน** — ส่วนใหญ่ของ")
    lines.append("  unit-day ที่ทดสอบ (ดู §2) จบที่ REFUSED ไม่ใช่ tier ตัวเลข ต้องเติมสถานีย้อนหลังจริง")
    lines.append("  (Q_o,now/Q_in,up/pump-state) ก่อนจึงจะ falsify calibration ของ threshold ได้อย่างมี")
    lines.append("  น้ำหนักสถิติ")
    lines.append("")
    lines.append("## Sources / raw data")
    lines.append("")
    lines.append("- `raw/backtest/units.yaml` — unit tuples, ทุก constant ติด tag")
    lines.append("- `raw/backtest/events.yaml` — ground truth ทุก unit-day")
    lines.append("- `raw/backtest/results.jsonl` — ทุก readout row (unit x date x H x c x pump)")
    lines.append("- `raw/backtest/rain/*.json`, `raw/backtest/flood/*.json`, `raw/backtest/nasa_power/*.json`")
    lines.append("  — payload ดิบทุกคำขอ (33 คำขอ, 1 คำขอ/URL, ไม่ retry)")
    lines.append("")
    lines.append(f"*{PROPOSAL_TAG}*")

    (DOCS / "BACKTEST_PROP_FLOOD_06_v0.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
