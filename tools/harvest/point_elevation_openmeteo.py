"""
tools/harvest/point_elevation_openmeteo.py -- ONE-OFF static harvester, not part of
collect.py --all (elevation is a static DEM surface, not a time-varying reading -- re-
running this script fetches the SAME 90m DEM grid values, so it is invoked deliberately,
not on every 30-min cycle).

Founder gap (2026-09-27, docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_
2026-09-27.md #6): ground-level elevation z, for datum/point-depth context, at points
this repo cares about. Open-Meteo's Elevation API (Copernicus GLO-90 DEM re-serve, no
API key) answers this with comma-separated multi-point in ONE request.

CAVEAT (must be repeated wherever this file's output is used): this is DEM SURFACE
elevation, NOT a ม.รทก. survey benchmark -- it differs in kind from
sources/bkk_district_elevation.yaml's RTSD-2010-survey-derived values (which have their
own land-subsidence caveat, documented in that file's own header). Both are kept as
separate rows in sources/point_elevation_openmeteo.yaml, never merged/averaged with
bkk_district_elevation.yaml's numbers -- two different measurement methods for the same
underlying quantity, per this repo's own "never merge without source" discipline
(coping_thresholds.yaml).

Usage:
    python3 tools/harvest/point_elevation_openmeteo.py
        -> writes sources/point_elevation_openmeteo.yaml (ONE live GET, no retry)
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent
OUT_PATH = REPO_ROOT / "sources" / "point_elevation_openmeteo.yaml"

REQUEST_TIMEOUT_S = 30
GENERIC_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}

# Points this repo already tracks elsewhere (same names as SOIL_MOISTURE_POINTS /
# FORECAST7D_POINTS in collect.py, plus the two upstream Q_up gauge/model points) -- reused
# on purpose so this file's rows can be joined by point_id against those collectors'
# observations without inventing yet another point-naming scheme.
ELEVATION_POINTS = {
    "sammakorn": (13.758235, 100.676084),
    "ram53": (13.765540125000635, 100.61909460837903),
    "bangkok_east": (13.7734, 100.6813),
    "nakhonsawan": (15.7047, 100.1372),
    "chaophraya_dam": (15.1897, 100.1608),
    "bang_sai": (14.35, 100.55),
}

ELEVATION_URL_TMPL = "https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"


def elevation_url(points: dict = ELEVATION_POINTS) -> str:
    lats = ",".join(str(lat) for lat, _ in points.values())
    lons = ",".join(str(lon) for _, lon in points.values())
    return ELEVATION_URL_TMPL.format(lats=lats, lons=lons)


def parse_elevation(data: dict, point_ids: list) -> dict:
    """Open-Meteo Elevation API JSON ({"elevation": [float, ...]}, SAME ORDER as the
    input lat/lon lists) -> {point_id: elevation_m}. A point beyond the returned array
    length is simply not present in the output, never fabricated."""
    vals = data.get("elevation") or []
    out = {}
    for i, pid in enumerate(point_ids):
        if i < len(vals) and vals[i] is not None:
            out[pid] = float(vals[i])
    return out


def fetch_once() -> dict:
    """ONE GET, no retry -- per this repo's blanket one-request discipline."""
    url = elevation_url()
    req = urllib.request.Request(url, headers=GENERIC_HEADERS)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        status, body = resp.status, resp.read()
    if status != 200:
        raise RuntimeError(f"point_elevation_openmeteo: HTTP {status}")
    return json.loads(body)


def build_output(elev_by_point: dict) -> dict:
    return {
        "_meta": {
            "generated": "2026-09-27",
            "source": "Open-Meteo Elevation API (Copernicus GLO-90 DEM re-serve)",
            "url_template": ELEVATION_URL_TMPL,
            "caveat": "DEM SURFACE elevation, NOT a ม.รทก. survey benchmark -- see this "
                      "module's own docstring. Never merge/average silently with "
                      "sources/bkk_district_elevation.yaml's RTSD-2010-survey values -- "
                      "keep both, tagged by method.",
            "tag": "VERIFIED",
            "unit": "m",
        },
        "points": [
            {"point_id": pid, "lat": ELEVATION_POINTS[pid][0], "lon": ELEVATION_POINTS[pid][1],
             "elevation_m": elev_by_point[pid]}
            for pid in ELEVATION_POINTS if pid in elev_by_point
        ],
    }


def main() -> int:
    point_ids = list(ELEVATION_POINTS.keys())
    data = fetch_once()
    elev_by_point = parse_elevation(data, point_ids)
    out = build_output(elev_by_point)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"Wrote {OUT_PATH} ({len(out['points'])} point(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
