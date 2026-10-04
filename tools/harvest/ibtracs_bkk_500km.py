"""
tools/harvest/ibtracs_bkk_500km.py -- ONE-OFF harvester (not part of collect.py --all --
IBTrACS is a historical archive, not a live feed; re-running this script re-derives the
SAME extract from the SAME downloaded CSV unless NOAA republishes a new version).

Founder addition 2026-09-27 ("เอาเลย"): NOAA IBTrACS (International Best Track Archive
for Climate Stewardship) Western Pacific basin CSV -- historical tropical-cyclone best-
track data, downloaded ONCE into raw/ibtracs/ (gitignored, per this repo's own
.gitignore), then filtered here to storm-track points within 500 km of Bangkok,
2005-2025, for later calibration against this repo's own urban flood event ledger. DATA
ONLY -- no danger threshold derived from this quantity anywhere in this repo (per the
founder's own instruction alongside the pressure/sst additions the same day).

Source: https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-
stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv (public domain, NOAA/
WMO, no API key). NOT downloaded automatically by this module -- see download_csv_once()
for the one-time fetch, invoked from main() only when the raw file is absent.

Output: sources/ibtracs_bkk_500km.yaml -- one row per (storm, track-point) within 500km
of Bangkok, columns: storm id (SID), name, time (ISO_TIME, treated as UTC per IBTrACS's
own documented convention), lat, lon, wind (kt, WMO_WIND, falling back to USA_WIND when
WMO_WIND is blank), pressure (mb, WMO_PRES falling back to USA_PRES), distance_km (great-
circle distance from this point to Bangkok, haversine -- a plain geometric calculation,
not a Toledo equation, same discipline as capacity_ledger.yaml's own /86400 conversion).
"""
from __future__ import annotations

import csv
import math
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
RAW_DIR = REPO_ROOT / "raw" / "ibtracs"
RAW_CSV_PATH = RAW_DIR / "ibtracs.WP.list.v04r01.csv"
OUT_PATH = REPO_ROOT / "sources" / "ibtracs_bkk_500km.yaml"

IBTRACS_CSV_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-"
    "stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv"
)
REQUEST_TIMEOUT_S = 180

BANGKOK_LAT = 13.7563
BANGKOK_LON = 100.5018
RADIUS_KM = 500.0
SEASON_MIN, SEASON_MAX = 2005, 2025
EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance, km -- plain spherical-Earth arithmetic, not a Toledo
    equation (same posture as capacity_ledger.yaml's own unit-conversion arithmetic)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def download_csv_once(dest: Path = RAW_CSV_PATH, url: str = IBTRACS_CSV_URL) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "thailand_flood_kg-floodconnect/1.0"})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        status, body = resp.status, resp.read()
    if status != 200:
        raise RuntimeError(f"ibtracs_bkk_500km: HTTP {status}")
    dest.write_bytes(body)
    return dest


def _f(v):
    if v is None:
        return None
    v = v.strip()
    if v in ("", " "):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def extract_bkk_500km(csv_path: Path, season_min: int = SEASON_MIN,
                       season_max: int = SEASON_MAX, radius_km: float = RADIUS_KM) -> list:
    """Pure function over an already-downloaded IBTrACS WP CSV path -> a list of
    track-point rows within `radius_km` of Bangkok, `season_min<=SEASON<=season_max`.
    IBTrACS's own file has a units row as its SECOND line (row 0 after the header) --
    skipped by checking that SEASON parses as an int, same "skip unparseable, never
    fabricate" discipline as every parser in parsers.py. WMO_WIND/WMO_PRES are preferred;
    USA_WIND/USA_PRES are used only when the WMO field is blank (IBTrACS documents WMO_*
    as the agency-of-responsibility's own reporting, not always populated for every
    point)."""
    rows = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                season = int(r.get("SEASON", "").strip())
            except (ValueError, AttributeError):
                continue  # the units row, or a malformed line
            if not (season_min <= season <= season_max):
                continue
            lat, lon = _f(r.get("LAT")), _f(r.get("LON"))
            if lat is None or lon is None:
                continue
            dist = haversine_km(lat, lon, BANGKOK_LAT, BANGKOK_LON)
            if dist > radius_km:
                continue
            wind = _f(r.get("WMO_WIND")) if _f(r.get("WMO_WIND")) is not None else _f(r.get("USA_WIND"))
            pres = _f(r.get("WMO_PRES")) if _f(r.get("WMO_PRES")) is not None else _f(r.get("USA_PRES"))
            rows.append({
                "storm_id": r.get("SID"),
                "season": season,
                "name": (r.get("NAME") or "").strip() or None,
                "time_utc": r.get("ISO_TIME"),
                "lat": lat, "lon": lon,
                "wind_kt": wind, "pressure_mb": pres,
                "distance_km_from_bangkok": round(dist, 1),
            })
    return rows


def build_output(rows: list) -> dict:
    storm_ids = sorted({r["storm_id"] for r in rows})
    return {
        "_meta": {
            "generated": "2026-09-27",
            "source": "NOAA IBTrACS v04r01, Western Pacific basin (historical best-track)",
            "url": IBTRACS_CSV_URL,
            "licence": "US government public-domain data (NOAA/WMO), not independently "
                       "re-verified against a formal licence text by this repo.",
            "tag": "VERIFIED",
            "kind": "Historical storm-track POINTS within 500km of Bangkok, "
                    f"{SEASON_MIN}-{SEASON_MAX} -- for calibration against this repo's "
                    "urban_event_ledger, DATA ONLY, no danger threshold derived here.",
            "radius_km": RADIUS_KM,
            "reference_point": {"lat": BANGKOK_LAT, "lon": BANGKOK_LON, "label": "Bangkok"},
            "row_count": len(rows),
            "storm_count": len(storm_ids),
        },
        "rows": rows,
    }


def main() -> int:
    if not RAW_CSV_PATH.exists():
        print(f"Downloading {IBTRACS_CSV_URL} -> {RAW_CSV_PATH} (one-time, ~110MB)...")
        download_csv_once()
    else:
        print(f"Using already-downloaded {RAW_CSV_PATH} (delete it to re-fetch).")
    rows = extract_bkk_500km(RAW_CSV_PATH)
    out = build_output(rows)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Wrote {OUT_PATH} ({len(rows)} track-point row(s), "
          f"{out['_meta']['storm_count']} distinct storm(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
