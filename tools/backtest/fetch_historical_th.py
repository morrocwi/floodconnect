#!/usr/bin/env python3
"""fetch_historical_th.py -- PROP-FLOOD-06 PROPOSAL, unverified.

Companion to fetch_historical.py, but pulls Thai OFFICIAL telemetry history
(HII/thaiwater api-v3) instead of global reanalysis (Open-Meteo/GloFAS). Written after the
2026-09-27 data sweep found that api-v3.thaiwater.net/api/v1/thaiwater30/public/
waterlevel_graph[_oldcode] has REAL hourly (tele_waterlevel) or 10-min (some stations)
level+discharge history, at least back to 2022, at several stations directly relevant to
this repo's backtest units (X.44/X.90 คลองอู่ตะเภา หาดใหญ่, N.1/N.64 แม่น้ำน่าน,
P.1 แม่น้ำปิง เชียงใหม่, plus BMA canal stations) -- see
docs/knowledge/DATA_SWEEP_2026-09-27.md and sources/capacity_ledger_additions.yaml for
what was actually fetched and found this check.

Endpoint discovered by reading the official thaiwater.net frontend's own JS bundle
(app.chunk.js, archived at raw/knowledge/api_census/hii/app.chunk.js) -- not brute force.
Two URL shapes exist:
  - .../public/waterlevel_graph?station_type=<tele_waterlevel|canal>&station_id=<HII numeric id>&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
  - .../public/waterlevel_graph_oldcode?station_id=<RID/BMA oldcode, e.g. X.44>&agency_id=<int>&start_date=...&end_date=...
This script implements the first shape only (numeric station_id), since that is the one
this check actually verified returns non-null data; the _oldcode variant is UNTESTED here
(OPEN) -- a future run should try it and compare before assuming either is authoritative.

Rule followed: one HTTP request per distinct URL (station_id + date-range counts as one
URL); no retries; browser User-Agent; 20s timeout. Every response is archived verbatim
under raw/backtest/hii_history/ so nothing here needs to be re-fetched to reproduce.
Streams to disk immediately -- never holds more than one response in memory beyond what
is needed to write it out.

Does NOT commit anything. Does NOT edit any existing file. Writes only under
raw/backtest/hii_history/.

Usage:
  python3 tools/backtest/fetch_historical_th.py            # runs the built-in STATIONS list
  python3 tools/backtest/fetch_historical_th.py --list      # print planned requests, fetch nothing
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "raw" / "backtest" / "hii_history"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
BASE = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_graph"


def fetch(url, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        print(f"SKIP (already fetched) {out_path.name}")
        return json.loads(out_path.read_text())
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        body = json.dumps({"error": True, "status": e.code, "reason": str(e), "url": url}).encode()
    except urllib.error.URLError as e:
        body = json.dumps({"error": True, "reason": str(e), "url": url}).encode()
    out_path.write_bytes(body)
    print(f"FETCHED {out_path.name} <- {url}")
    time.sleep(0.4)
    try:
        return json.loads(body)
    except Exception:
        return {"error": True, "raw": body.decode(errors="replace")}


# ---- stations: (label, station_type, station_id, [(start, end, tag), ...]) ----
# station_id is the HII numeric id (NOT the RID/BMA oldcode printed on public signage).
# Every id below was resolved from a LOCALLY CACHED api-v3 waterlevel/canal_waterlevel
# snapshot this repo's own collect.py already produced -- resolving an id costs zero new
# HTTP requests; only the waterlevel_graph calls below do.
STATIONS = [
    # Hat Yai / Khlong U Taphao -- PROP-FLOOD-06's largest, founder-flagged unit.
    ("HATYAI_X44", "tele_waterlevel", 2591, [
        ("2010-10-15", "2010-11-10", "flood_2553_probe (returned ALL-NULL this check -- telemetry does not reach back to 2010)"),
        ("2022-11-10", "2022-12-10", "flood_2565 + quiet-period control (VERIFIED non-null this check)"),
    ]),
    ("HATYAI_X90_CONTROL", "tele_waterlevel", 2589, [
        ("2022-11-10", "2022-12-10", "downstream quiet-period control station"),
    ]),
    ("HATYAI_ONE037", "tele_waterlevel", 1109526, [
        ("2022-11-10", "2022-12-10", "2nd Khlong U Taphao point, level-only (no discharge field populated)"),
    ]),
    # Nan -- 2567 (Aug 2024) event.
    ("NAN_N1", "tele_waterlevel", 3219, [
        ("2024-08-01", "2024-09-15", "flood_2567 (VERIFIED peak 1463.6 m3/s @ 2024-08-22 20:00)"),
    ]),
    ("NAN_N64", "tele_waterlevel", 3246, [
        ("2024-08-01", "2024-09-15", "flood_2567, upstream of N.1 (VERIFIED peak 1426.5 m3/s @ 2024-08-22 10:00)"),
    ]),
    # Chiang Mai -- 2567 (Sep-Oct 2024) event.
    ("CHIANGMAI_P1", "tele_waterlevel", 3226, [
        ("2024-09-15", "2024-10-15", "flood_2567 (VERIFIED peak 656 m3/s @ 2024-10-05 12:00, matches case-card date)"),
    ]),
    # Bangkok East -- BMA canal stations, dry-season "normal" baseline (target F, 2026-09-27).
    ("BKK_WL_SSB07", "canal", 77, [("2026-02-01", "2026-03-15", "dry-season normal-level baseline")]),
    ("BKK_WL_SSB09", "canal", 71, [("2026-02-01", "2026-03-15", "dry-season normal-level baseline")]),
    ("BKK_WL_SSB10", "canal", 67, [("2026-02-01", "2026-03-15", "dry-season normal-level baseline")]),
    ("BKK_WL_PWT03", "canal", 82, [("2026-02-01", "2026-03-15", "dry-season normal-level baseline")]),
    ("BKK_WL_PWT04", "canal", 81, [("2026-02-01", "2026-03-15", "dry-season normal-level baseline")]),
    ("BKK_WL_LPW01", "canal", 72, [("2026-02-01", "2026-03-15", "dry-season normal-level baseline")]),
    # Bangkok East -- 2554 (2011) canal history probe (returned ALL-NULL this check).
    ("BKK_CANAL_87_2554_PROBE", "canal", 87, [
        ("2011-10-01", "2011-11-15", "2554 flood probe -- returned ALL-NULL this check, canal telemetry likely post-dates 2011"),
    ]),
]


def plan():
    for label, station_type, station_id, windows in STATIONS:
        for start, end, note in windows:
            url = f"{BASE}?station_type={station_type}&station_id={station_id}&start_date={start}&end_date={end}"
            out = RAW / f"{label}_{station_id}_{start}_{end}.json"
            yield label, url, out, note


def main():
    list_only = "--list" in sys.argv
    for label, url, out, note in plan():
        print(f"{label}: {note}\n  {url}\n  -> {out}")
        if not list_only:
            fetch(url, out)


if __name__ == "__main__":
    main()
