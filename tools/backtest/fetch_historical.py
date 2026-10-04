#!/usr/bin/env python3
"""fetch_historical.py -- PROP-FLOOD-06 PROPOSAL, unverified.

One-shot fetcher for the PROP-FLOOD-06 backtest (see docs/BACKTEST_PROP_FLOOD_06_v0.md).
Pulls free, no-key historical sources for the falsifier loop:
  - Open-Meteo Archive API (ERA5 reanalysis hourly precipitation) -- rain forcing
  - Open-Meteo Flood API (GloFAS reanalysis daily river_discharge) -- outlet/upstream flow
  - NASA POWER daily precipitation -- cross-check rain source (>=10 days)

Rule followed: one HTTP request per distinct URL (a distinct lat/lon/date-range/parameter
set counts as one URL); no retries. Every response is archived verbatim under
raw/backtest/<source>/ so nothing here needs to be re-fetched to reproduce the backtest.
Streams to disk immediately -- never holds more than one response in memory.

Does NOT commit anything. Does NOT edit any existing file. Writes only under raw/backtest/.
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "raw" / "backtest"
UA = "thailand_flood_kg-backtest/0.1 (research; PROP-FLOOD-06 PROPOSAL unverified)"


def fetch(url, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        print(f"SKIP (already fetched) {out_path.name}")
        return json.loads(out_path.read_text())
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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


# ---- rain blocks: (unit_id, lat, lon, start, end) ----
RAIN_BLOCKS = [
    ("HATYAI", 7.0084, 100.4747, "2010-10-20", "2010-11-10"),
    ("HATYAI", 7.0084, 100.4747, "2022-11-15", "2022-12-05"),
    ("HATYAI", 7.0084, 100.4747, "2015-12-01", "2015-12-10"),
    ("HATYAI", 7.0084, 100.4747, "2017-02-01", "2017-02-10"),
    ("HATYAI", 7.0084, 100.4747, "2019-03-01", "2019-03-10"),
    ("HATYAI", 7.0084, 100.4747, "2021-01-15", "2021-01-24"),
    ("NAN", 18.7756, 100.7730, "2024-08-15", "2024-08-31"),
    ("NAN", 18.7756, 100.7730, "2024-02-01", "2024-02-10"),
    ("CHIANGMAI", 18.7883, 98.9853, "2024-09-22", "2024-10-07"),
    ("CHIANGMAI", 18.7883, 98.9853, "2024-03-01", "2024-03-10"),
    ("AYUTTHAYA_BANGBAN", 14.4744, 100.5013, "2011-09-20", "2011-10-20"),
    ("AYUTTHAYA_BANGBAN", 14.4744, 100.5013, "2012-02-01", "2012-02-10"),
    ("BANGKOK_EAST", 13.7734, 100.6813, "2011-10-20", "2011-11-10"),
    ("BANGKOK_EAST", 13.7734, 100.6813, "2026-09-20", "2026-09-27"),
    ("BANGKOK_EAST", 13.7734, 100.6813, "2026-02-01", "2026-02-10"),
]

# ---- flood/discharge points: (label, lat, lon, [(start,end), ...]) ----
# lat/lon here are the REQUEST coords; Open-Meteo snaps to its own river-network cell
# (see the resolved lat/lon inside each response) -- this is the GloFAS 0.25 deg
# grid-snap limitation documented in the backtest report (Nan/Ping town-centre cells
# do NOT resolve the real river channel -- probed manually before this fetch, kept
# anyway so the REFUSED/NO_GAUGE_IN_UNIT outcome is reproducible from raw data, not
# just asserted).
FLOOD_POINTS = [
    ("HATYAI_CANAL", 7.0084, 100.4747, [
        ("2010-10-20", "2010-11-10"), ("2022-11-15", "2022-12-05"),
        ("2015-12-01", "2015-12-10"), ("2017-02-01", "2017-02-10"),
        ("2019-03-01", "2019-03-10"), ("2021-01-15", "2021-01-24"),
    ]),
    ("NAN_TOWN", 18.7756, 100.7730, [
        ("2024-08-15", "2024-08-31"), ("2024-02-01", "2024-02-10"),
    ]),
    ("CHIANGMAI_TOWN", 18.7883, 98.9853, [
        ("2024-09-22", "2024-10-07"), ("2024-03-01", "2024-03-10"),
    ]),
    ("AYUTTHAYA_BANGBAN", 14.4500, 100.5300, [
        ("2011-09-20", "2011-10-20"), ("2012-02-01", "2012-02-10"),
    ]),
    ("NAKHONSAWAN_C2_UPSTREAM", 15.7047, 100.1372, [
        ("2011-09-20", "2011-10-20"), ("2012-02-01", "2012-02-10"),
    ]),
    ("BANGKOK_CHAOPHRAYA", 13.7300, 100.5000, [
        ("2011-10-20", "2011-11-10"), ("2026-09-20", "2026-09-27"),
        ("2026-02-01", "2026-02-10"),
    ]),
]

# ---- NASA POWER cross-check (>=10 days each, 3 distinct points/ranges) ----
NASA_BLOCKS = [
    ("NAN_2567", 18.7756, 100.7730, "20240815", "20240831"),
    ("CHIANGMAI_2567", 18.7883, 98.9853, "20240922", "20241007"),
    ("HATYAI_2565", 7.0084, 100.4747, "20221115", "20221205"),
]


def main():
    print("=== Open-Meteo Archive (rain, hourly precipitation) ===")
    for unit, lat, lon, start, end in RAIN_BLOCKS:
        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
            "&hourly=precipitation&timezone=Asia%2FBangkok"
        )
        out = RAW / "rain" / f"{unit}_{start}_{end}.json"
        fetch(url, out)

    print("=== Open-Meteo Flood API (GloFAS daily river_discharge) ===")
    for label, lat, lon, ranges in FLOOD_POINTS:
        for start, end in ranges:
            url = (
                "https://flood-api.open-meteo.com/v1/flood"
                f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
                "&daily=river_discharge&timezone=Asia%2FBangkok"
            )
            out = RAW / "flood" / f"{label}_{start}_{end}.json"
            fetch(url, out)

    print("=== NASA POWER (rain cross-check) ===")
    for label, lat, lon, start, end in NASA_BLOCKS:
        url = (
            "https://power.larc.nasa.gov/api/temporal/daily/point"
            f"?parameters=PRECTOTCORR&community=AG&longitude={lon}&latitude={lat}"
            f"&start={start}&end={end}&format=JSON"
        )
        out = RAW / "nasa_power" / f"{label}_{start}_{end}.json"
        fetch(url, out)

    print("Done.")


if __name__ == "__main__":
    main()
