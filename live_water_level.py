#!/usr/bin/env python3
"""
Live Bangkok canal water-level attachment -- companion to build_bangkok_canals.py.

Attaches a LIVE (or best-effort near-live) water-level reading to canal-graph nodes,
reusing this repo's existing patterns: GISTDA-style pagination/caching discipline from
build_river_kg.py's `overlay_gistda_flood()`, and the fuzzy station-name -> floodgate-coordinate
join from build_bangkok_canals.py's `match_water_level_stations_to_floodgates()`.

## What this is NOT -- read README.md's "What this is NOT" section first

A live water-level reading is a POINT READOUT at one station at one instant. It does
**not** give flow direction (see README_bangkok_canals.md, "one point says nothing about
which way water is moving; that would need two stations on the same canal" -- section
"BMA water-level station join"), and it is **not a forecast** (see README.md's top-level
"What this is NOT"). Do not present `live_water_level_m` as anything more than "this is
what one sensor read at `live_water_level_observed_at`".

## Sources probed 2026-09-26 (see README.md "Live canal water level" for the full table)

- BMA KlongMap backend (`https://weather.bangkok.go.th/Klongmap/GetDataForUpdate`):
  confirmed HTTP 403 even with full browser-like headers (User-Agent/Accept/Referer).
  `fetch_klongmap()` makes exactly one such attempt and raises `LiveSourceUnavailable`
  on non-200 -- no retry loop. Parsing (`parse_klongmap_stations`) is implemented and
  unit-tested against a real recorded response shape (this repo's earlier session cached
  one at `raw/bangkok/klongmap_data.json`) so it activates the moment the 403 lifts.
- HII/สสน. `standard.thaiwater.net` (the spec/wedocs site): a national data-EXCHANGE
  STANDARD document, not itself a hosted API -- its own "Base URL" doc says each provider
  agency runs its own server (`https://api.<agency>.go.th/twsapi/v1.0/...`, the shown
  host is a placeholder). Superseded below.
- **Found working 2026-09-26**: a maintainer pointed at HII's own consumer-facing page
  `https://www.thaiwater.net/bma`. Loading it in a real browser and reading its XHR calls
  showed the page itself pulls `https://api-v3.thaiwater.net/api/v1/thaiwater30/public/
  canal_waterlevel` -- a public, unauthenticated JSON GET (no token/cookie/login), 282
  records, every one tagged `agency.agency_name.en == "Department of Bangkok"` i.e. BMA's
  สำนักการระบายน้ำ, with real `canal_lat`/`canal_long` coordinates. Confirmed reachable
  with a plain `urllib.request` + generic User-Agent (200 OK, no auth). This is now the
  live path (`fetch_thaiwater_stations()` / `parse_thaiwater_canal_stations()`);
  KlongMap stays as a second attempted source (still 403) in case it ever opens up.

CLI:
    python3 live_water_level.py --probe
    python3 live_water_level.py --attach output/bangkok_canals.graphml --out output/bangkok_canals.graphml
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    import networkx as nx
except ImportError:  # pragma: no cover -- only needed by the --attach/graphml CLI path,
    # not by collect.py/readout.py, which only use this module's fetch/classify/age_hours
    # helpers. Kept optional so the live-collection pipeline never fails on a missing
    # heavy dependency it doesn't actually need.
    nx = None

HERE = Path(__file__).parent
RAW_LIVE_DIR = HERE / "raw" / "live"
FLOODGATE_CSV = HERE / "raw" / "bangkok" / "floodgate.csv"

KLONGMAP_URL = "https://weather.bangkok.go.th/Klongmap/GetDataForUpdate"
KLONGMAP_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://weather.bangkok.go.th/Klongmap/",
}

# Found 2026-09-26 by loading https://www.thaiwater.net/bma (HII/สสน. "National
# Hydroinformatics Data Center") in a real browser and inspecting the page's own XHR
# calls: this JSON endpoint is one of the calls the page itself makes to render the BMA
# canal-station table -- it is a public, unauthenticated GET (no token/cookie observed),
# confirmed reachable with a plain `urllib.request` + generic User-Agent, no auth header.
THAIWATER_CANAL_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/canal_waterlevel"
THAIWATER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-fetch/1.0",
    "Accept": "application/json",
}
REQUEST_TIMEOUT_S = 15
NODE_MATCH_MAX_KM = 0.3  # 300 m -- same join radius as build_bangkok_canals.py's FLOODGATE_JOIN_KM


class LiveSourceUnavailable(RuntimeError):
    """A live source could not be reached/authorized. Callers must surface this plainly
    (OPEN status) rather than silently substituting fabricated data."""


def _utcnow_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _cache_raw(source: str, payload: bytes, suffix: str = "json") -> Path:
    """raw/ is gitignored (see .gitignore) -- caching here keeps re-runs reproducible
    without committing scraped upstream data, same discipline as raw/bangkok/*.csv."""
    d = RAW_LIVE_DIR / source
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{_utcnow_stamp()}.{suffix}"
    p.write_bytes(payload)
    return p


def _dotnet_date_to_iso(s):
    """BMA KlongMap timestamps are ASP.NET-style '/Date(1790098800000)/' (ms since epoch,
    UTC per the observed cached dump). Returns an ISO-8601 UTC string, or None."""
    if not s:
        return None
    m = re.match(r"/Date\((-?\d+)\)/", s)
    if not m:
        return None
    ms = int(m.group(1))
    return datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc).isoformat()


def parse_klongmap_stations(data: dict) -> list:
    """
    Pure parser: BMA KlongMap `GetDataForUpdate` JSON -> station dicts.

    Schema confirmed from a real cached dump (raw/bangkok/klongmap_data.json, 2026-09-23):
    top-level `waterStation` is a list; each record nests `water_station_info` (real
    `latitude`/`longitude`, thresholds, `river_name`) and `water_level_last` (`wl_in` =
    current level in metres, `-99` = no reading, `site_timestamp` = ASP.NET date string).

    Stations with no coordinate, or no current reading, are skipped -- this pipeline does
    not fabricate a station's location or level (same discipline as build_river_kg.py's
    `flood_status` staying "unknown" without a key, and build_bangkok_canals.py's fuzzy
    match keeping every match_ratio auditable).

    Returns [{station_id, name_th, lat, lon, level_m, observed_at, source_url, fetched_at}],
    `fetched_at` left None (caller fills it in with the actual fetch time).
    """
    out = []
    for rec in data.get("waterStation", []):
        info = rec.get("water_station_info") or {}
        lat, lon = info.get("latitude"), info.get("longitude")
        if lat is None or lon is None:
            continue
        wl_last = rec.get("water_level_last") or info.get("water_level_last") or {}
        level = wl_last.get("wl_in")
        if level is None or level == -99:
            continue
        out.append({
            "station_id": str(rec.get("water_id")),
            "name_th": info.get("water_name") or rec.get("station_name") or info.get("water_shortname") or None,
            "lat": float(lat),
            "lon": float(lon),
            "level_m": float(level),
            "observed_at": _dotnet_date_to_iso(wl_last.get("site_timestamp")),
            "source_url": KLONGMAP_URL,
            "fetched_at": None,
        })
    return out


def fetch_klongmap() -> list:
    """
    ONE GET to BMA's KlongMap backend with browser-like headers. No retry.

    Confirmed live 2026-09-26: HTTP 403 even with a full User-Agent/Accept/Referer set
    (see module docstring / README "Live canal water level"). Raises
    LiveSourceUnavailable on any non-200 or network error.
    """
    req = urllib.request.Request(KLONGMAP_URL, headers=KLONGMAP_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise LiveSourceUnavailable(
            f"KlongMap GetDataForUpdate returned HTTP {e.code} (confirmed 2026-09-26 with "
            "browser-like headers -- BMA is blocking non-browser traffic at the edge, not "
            "a bug in this module; do not retry in a loop)."
        ) from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise LiveSourceUnavailable(f"KlongMap GetDataForUpdate network error: {e}") from e

    if status != 200:
        raise LiveSourceUnavailable(f"KlongMap GetDataForUpdate returned HTTP {status}")

    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _cache_raw("klongmap", body)
    data = json.loads(body)
    stations = parse_klongmap_stations(data)
    for s in stations:
        s["fetched_at"] = fetched_at
    return stations


def parse_thaiwater_canal_stations(data: dict) -> list:
    """
    Pure parser: `api-v3.thaiwater.net .../public/canal_waterlevel` JSON -> station dicts.

    Schema confirmed 2026-09-26 from a real live fetch (282 records, all
    `agency.agency_name.en == "Department of Bangkok"` i.e. BMA's สำนักการระบายน้ำ --
    these ARE BMA canal stations, not Chao Phraya river gauges). Each record's `station`
    sub-object carries `canal_lat`/`canal_long` (real coordinates) and `canal_name.th`;
    the record itself carries `canal_value` (current level, metres) and `canal_datetime`
    ("YYYY-MM-DD HH:MM", local Thailand time, UTC+7 -- converted to UTC ISO-8601 here so
    it is directly comparable to KlongMap's `observed_at`).

    Also carries, straight from the same public payload -- never fabricated, None passed
    through as-is when BMA itself reports no threshold for that station:
    - `canal_oldcode` -- the BMA station code (e.g. "WL.SSB.07")
    - `bank`, `warning_level`, `critical_level` -- BMA's own published thresholds (metres)
    - `canal_out` -- outside-gate level (raw record field; meaningful only for a gate
      station, see `is_gate` below)
    - `is_gate` -- True when `canal_name.th` starts with "ปตร." (ประตูระบายน้ำ, floodgate),
      the same prefix `resolve_station_coordinate`'s name-normalizer already strips
    - `amphoe_th` -- `geocode.amphoe_name.th` (district), for human orientation only

    Same discipline as `parse_klongmap_stations`: a record with no coordinate is skipped,
    never fabricated.
    """
    out = []
    for rec in data.get("data", []):
        station = rec.get("station") or {}
        lat, lon = station.get("canal_lat"), station.get("canal_long")
        if lat is None or lon is None:
            continue
        level = rec.get("canal_value")
        if level is None:
            continue
        dt_str = rec.get("canal_datetime")
        observed_at = None
        if dt_str:
            try:
                local_dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                local_dt = local_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                observed_at = local_dt.astimezone(datetime.timezone.utc).isoformat()
            except ValueError:
                observed_at = None
        agency = ((rec.get("agency") or {}).get("agency_name") or {}).get("en")
        name_th = (station.get("canal_name") or {}).get("th")
        geocode = rec.get("geocode") or {}
        out.append({
            "station_id": str(station.get("id")) if station.get("id") is not None else None,
            "name_th": name_th,
            "lat": float(lat),
            "lon": float(lon),
            "level_m": float(level),
            "observed_at": observed_at,
            "source_url": THAIWATER_CANAL_URL,
            "fetched_at": None,
            "agency": agency,
            "canal_oldcode": station.get("canal_oldcode"),
            "bank": station.get("bank"),
            "warning_level": station.get("warning_level"),
            "critical_level": station.get("critical_level"),
            "canal_out": rec.get("canal_out"),
            "is_gate": bool(name_th) and name_th.startswith("ปตร."),
            "amphoe_th": (geocode.get("amphoe_name") or {}).get("th"),
        })
    return out


def fetch_thaiwater_stations() -> list:
    """
    ONE GET to `api-v3.thaiwater.net`'s public canal_waterlevel endpoint, discovered by
    loading https://www.thaiwater.net/bma in a browser and reading the page's own XHR
    calls (2026-09-26). No auth header/token/cookie observed or required; confirmed
    reachable with a plain `urllib.request` + generic User-Agent. No retry.

    Data source: HII/สสน. (Hydro-Informatics Institute, a Thai public organization) via
    thaiwater.net, republishing BMA (สำนักการระบายน้ำ กรุงเทพมหานคร) canal-station
    readings. See README.md "Live canal water level" for the licence/attribution note.
    """
    req = urllib.request.Request(THAIWATER_CANAL_URL, headers=THAIWATER_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise LiveSourceUnavailable(f"thaiwater canal_waterlevel returned HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise LiveSourceUnavailable(f"thaiwater canal_waterlevel network error: {e}") from e

    if status != 200:
        raise LiveSourceUnavailable(f"thaiwater canal_waterlevel returned HTTP {status}")

    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _cache_raw("thaiwater_bma", body)
    data = json.loads(body)
    stations = parse_thaiwater_canal_stations(data)
    for s in stations:
        s["fetched_at"] = fetched_at
    return stations


def load_thaiwater_stations_from_file(path: Path) -> list:
    """Offline path for --from-file: parse a previously-saved raw JSON body (as cached
    by fetch_thaiwater_stations()/`_cache_raw`) without any network call."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stations = parse_thaiwater_canal_stations(data)
    for s in stations:
        s["fetched_at"] = fetched_at
    return stations


# --- BMA PumpHistory (Sammakorn ST.SPS pumping stations) -------------------------------
#
# Source: https://weather.bangkok.go.th/Station/PumpHistory -- a server-rendered "all
# stations" summary table (not a per-station AJAX endpoint: a saved copy loaded 2026-09-26
# already contains every station's current row, keyed by `id="tbodysummary"`, plus a
# separate embedded `var datapump = [...]` JS array with static per-station metadata
# (code, Thai/English name, district, pump_count, lat/lon). Host note: this same host
# returned HTTP 403 on /Home and /Map on 2026-09-26 while /Station/PumpHistory returned
# 200 -- treated as a per-path difference, not assumed to persist; `fetch_pumphistory()`
# makes exactly ONE GET, no retry, and raises LiveSourceUnavailable on anything but 200.
PUMPHISTORY_URL = "https://weather.bangkok.go.th/Station/PumpHistory"
PUMPHISTORY_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://weather.bangkok.go.th/Station/PumpHistory",
}
PUMPHISTORY_TIMEOUT_S = 20

DEFAULT_PUMP_STATION_CODES = ["ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"]

DATAPUMP_COORD_SOURCE = "pumphistory datapump"

_PUMP_ROW_RE = re.compile(r'<tr role="row" class="\w+">(.*?)</tr>', re.S)
_PUMP_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_PUMP_STATUS_RUNNING = "ทำงาน"


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def _parse_pumphistory_meta(html: str) -> dict:
    """Pull the embedded `var datapump = [...]` JS array (present on the same page,
    static per-station metadata separate from the live table) and return
    {station_code: {"district": ..., "lat": ..., "lon": ...}}. Real coordinates --
    confirmed 2026-09-26 against a live fetch (`latitude`/`longitude` fields), not a
    fuzzy/approximate join. Returns {} if the array isn't found -- callers then leave
    district/lat/lon as None rather than fabricating them."""
    m = re.search(r"var datapump\s*=\s*(\[.*?\]);", html, re.S)
    if not m:
        return {}
    try:
        records = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    out = {}
    for rec in records:
        code = rec.get("pumpStation_code")
        if not code:
            continue
        out[code] = {
            "district": rec.get("district_name"),
            "lat": rec.get("latitude"),
            "lon": rec.get("longitude"),
        }
    return out


# Sensor-fault statuses (data hygiene, 2026-09-27): PumpHistory's "สถานะ" column returns
# ปกติ (normal) or ขัดข้อง (out of service / faulted) per station per tick. Before this
# fix, `level_m` was parsed and stored as a real number even when the station itself
# reported ขัดข้อง (e.g. ST.SPS.01 reading 0.0 m while flagged ขัดข้อง) -- a faulted
# sensor's last-latched or garbage reading, not a trustworthy MEASURED value. Going
# forward, a faulted row's `level_m` is None (never a fabricated/frozen number) and
# `sensor_status` carries the machine-readable flag ("fault"/"ok"/None) so every
# downstream consumer can exclude it without re-parsing `status_th` itself. Existing rows
# already written to `data/observations.sqlite` before this fix are NOT rewritten
# (append-only); they stay untrusted at query time via their own `status` column, which
# already carried the raw `status_th` text (see collect.py's collect_bma_pumphistory()).
SENSOR_FAULT_STATUS_TH = {"ขัดข้อง"}


def sensor_status_from_status_th(status_th) -> str | None:
    """"fault" if status_th is a known out-of-service marker, "ok" if present and not
    faulted, None if status_th itself is missing/unknown (never guessed)."""
    if not status_th:
        return None
    return "fault" if status_th in SENSOR_FAULT_STATUS_TH else "ok"


def parse_pumphistory_html(html: str) -> list:
    """
    Pure parser: BMA PumpHistory's server-rendered summary table -> station-reading dicts.

    Table columns confirmed 2026-09-26 from a saved real page (`id="tbodysummary"`, fixed
    17 <td> per row): No., รหัสสถานี (code), ชื่อสถานี (name), วัน-เวลา (datetime, "DD/MM/YYYY
    HH:MM" local Thailand time), สถานะ (station status, ปกติ/ขัดข้อง), ระดับน้ำ (level, m),
    ระดับน้ำจุดที่ 2 (second level point, m -- not carried through, most stations leave it
    blank), 6 pump-status cells (each either empty -- no such pump slot -- or a Thai label,
    "ทำงาน" = running, "รอทำงาน" = standby/off), 4 floodgate-opening cells (m, blank if no
    such gate). A row with fewer than 17 cells (e.g. a header/no-data row) is skipped.

    Returns every station row found (not filtered to any station list -- callers filter),
    each: {station_code, name_th, district, lat, lon, coord_source, level_m, pumps_total,
    pumps_on, gate_open, observed_at (UTC ISO), status_th, sensor_status, source_url,
    fetched_at=None}.
    `district`/`lat`/`lon` come from the same page's embedded `datapump` JS array (real
    coordinates, not a fuzzy join; None if that array is missing or the code isn't in it --
    never fabricated). `coord_source` is `DATAPUMP_COORD_SOURCE` when lat/lon were found,
    else None.

    `level_m` is None whenever `status_th` reports a sensor fault (`ขัดข้อง`) -- the
    station's own reading is untrusted, never stored as a real number (see
    `SENSOR_FAULT_STATUS_TH` above). `sensor_status` is "fault"/"ok"/None.
    """
    meta = _parse_pumphistory_meta(html)
    out = []
    for row_html in _PUMP_ROW_RE.findall(html):
        cells = [_strip_tags(c) for c in _PUMP_TD_RE.findall(row_html)]
        if len(cells) < 17:
            continue
        _no, code, name, dt_str, status_th = cells[0:5]
        level_s, _level2_s = cells[5:7]
        pump_cells = cells[7:13]
        gate_cells = cells[13:17]
        if not code:
            continue

        pumps_total = sum(1 for c in pump_cells if c)
        pumps_on = sum(1 for c in pump_cells if c == _PUMP_STATUS_RUNNING)
        gate_vals = []
        for c in gate_cells:
            if not c:
                continue
            try:
                gate_vals.append(float(c))
            except ValueError:
                continue
        gate_open = gate_vals[0] if gate_vals else None

        level_m = None
        if level_s:
            try:
                level_m = float(level_s)
            except ValueError:
                level_m = None
        sensor_status = sensor_status_from_status_th(status_th or None)
        if sensor_status == "fault":
            level_m = None  # untrusted -- never store/return a faulted sensor's reading

        observed_at = None
        if dt_str:
            try:
                local_dt = datetime.datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                local_dt = local_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                observed_at = local_dt.astimezone(datetime.timezone.utc).isoformat()
            except ValueError:
                observed_at = None

        rec_meta = meta.get(code) or {}
        lat, lon = rec_meta.get("lat"), rec_meta.get("lon")
        out.append({
            "station_code": code,
            "name_th": name or None,
            "district": rec_meta.get("district"),
            "lat": float(lat) if lat is not None else None,
            "lon": float(lon) if lon is not None else None,
            "coord_source": DATAPUMP_COORD_SOURCE if lat is not None and lon is not None else None,
            "level_m": level_m,
            "pumps_total": pumps_total,
            "pumps_on": pumps_on,
            "gate_open": gate_open,
            "observed_at": observed_at,
            "status_th": status_th or None,
            "sensor_status": sensor_status,
            "source_url": PUMPHISTORY_URL,
            "fetched_at": None,
        })
    return out


def fetch_pumphistory(station_codes=None) -> list:
    """
    ONE GET to `weather.bangkok.go.th/Station/PumpHistory` (20 s timeout, browser-like
    User-Agent, no retry). Raises LiveSourceUnavailable on any non-200/network error --
    same fail-closed discipline as `fetch_klongmap()`/`fetch_thaiwater_stations()`.

    `station_codes` (default `DEFAULT_PUMP_STATION_CODES`, the 4 Sammakorn ST.SPS
    stations) filters the returned rows; pass `[]` or `None` explicitly bypassed via
    `station_codes=[]` to get every station on the page (not the default).
    """
    if station_codes is None:
        station_codes = DEFAULT_PUMP_STATION_CODES
    req = urllib.request.Request(PUMPHISTORY_URL, headers=PUMPHISTORY_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=PUMPHISTORY_TIMEOUT_S) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        raise LiveSourceUnavailable(f"PumpHistory returned HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise LiveSourceUnavailable(f"PumpHistory network error: {e}") from e

    if status != 200:
        raise LiveSourceUnavailable(f"PumpHistory returned HTTP {status}")

    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _cache_raw("pumphistory", body, suffix="html")
    html = body.decode("utf-8", errors="replace")
    rows = parse_pumphistory_html(html)
    for r in rows:
        r["fetched_at"] = fetched_at
    if station_codes:
        rows = [r for r in rows if r["station_code"] in station_codes]
    return rows


def load_pumphistory_from_file(path: Path, station_codes=None) -> list:
    """Offline path for --pump-from-file: parse a previously-saved raw PumpHistory HTML
    page (as cached by fetch_pumphistory()/`_cache_raw`) without any network call."""
    if station_codes is None:
        station_codes = DEFAULT_PUMP_STATION_CODES
    html = Path(path).read_text(encoding="utf-8")
    fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = parse_pumphistory_html(html)
    for r in rows:
        r["fetched_at"] = fetched_at
    if station_codes:
        rows = [r for r in rows if r["station_code"] in station_codes]
    return rows


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _normalize_station_name(s: str) -> str:
    """Mirror build_bangkok_canals.py's `_normalize_station_name` (kept local so this
    module has no import-time dependency on that script's module-level constants)."""
    s = (s or "").replace("ปตร.", " ").replace("ประตูระบายน้ำ", " ")
    s = re.sub(r"[()\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def resolve_station_coordinate(station: dict, floodgate_csv: Path = FLOODGATE_CSV) -> dict:
    """
    If `station` already carries its own lat/lon, return it unchanged (direct join --
    KlongMap stations from `parse_klongmap_stations` already have this).

    Otherwise, reuse build_bangkok_canals.py's fuzzy station-name -> floodgate.csv
    coordinate join (`SequenceMatcher` ratio, same normalization) as a fallback path for
    a future source that only gives a station NAME, not a coordinate. Returns the station
    dict augmented with lat/lon/match_confidence, or unchanged (no lat/lon key added) if
    no floodgate name clears build_bangkok_canals.py's own 0.55 acceptance bar.
    """
    if station.get("lat") is not None and station.get("lon") is not None:
        return station
    name = station.get("name_th")
    if not name or not floodgate_csv.exists():
        return station
    from difflib import SequenceMatcher
    import csv
    norm_station = _normalize_station_name(name)
    best_gate, best_ratio = None, 0.0
    with open(floodgate_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                lat, lon = float(row["lat"]), float(row["long"])
            except (ValueError, KeyError):
                continue
            norm_gate = _normalize_station_name(row.get("name", ""))
            ratio = SequenceMatcher(None, norm_station, norm_gate).ratio()
            if ratio > best_ratio:
                best_ratio, best_gate = ratio, {"name": row.get("name"), "lat": lat, "lon": lon}
    if best_gate is not None and best_ratio >= 0.55:
        out = dict(station)
        out["lat"], out["lon"] = best_gate["lat"], best_gate["lon"]
        out["match_confidence"] = round(best_ratio, 3)
        return out
    return station


STALE_HOURS = 24.0


def safe_float(x):
    """Coerce to float, returning None on any failure (missing, "N/A", empty string,
    non-numeric) instead of raising -- never let one bad agency-published field crash the
    whole classification pass (fix MEDIUM-4, 2026-09-26)."""
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# Sentinel for `classify_level(..., normal_level=...)`: the caller HAS opted into the
# normal-level ladder (founder rule below) but this station has no resolved normal_level
# on record (`resolve_normal_level()`'s own basis=="OPEN" case) -- distinct from simply
# not passing `normal_level` at all (old 4-arg call sites, unchanged behavior below).
NO_NORMAL_LEVEL = object()


def classify_level(value, warning, critical, bank, normal_level=None):
    """
    Pure classifier against BMA's own published thresholds for a station -- never a
    forecast, just "where does this one reading sit against the agency's own bands".

    Returns one of:
    - "NO_THRESHOLD" -- BMA publishes no warning/critical/bank level at all for this
      station (`warning is None and critical is None and bank is None`) AND the caller
      did not opt into the normal-level ladder; this is common for non-gate monitoring
      points (see fixture station 153).
    - "OVERBANK"  -- value >= bank (bank is the highest published band: canal has topped
      its bank)
    - "CRITICAL"  -- value >= critical
    - "WATCH"     -- value >= warning
    - "ABOVE_NORMAL" -- (only when `normal_level` is passed) below every danger
      threshold but ABOVE the station's own normal_level -- founder rule (verbatim,
      2026-09-27): "ไม่ปกติ ต้องต่ำกว่าเกณฑ์ปกติหรือเปล่า แค่นี้ยังไม่เรียกปกติ" -- a level
      merely below `warning` is NOT "ปกติ" on its own.
    - "NO_NORMAL_BASIS" -- (only when `normal_level=NO_NORMAL_LEVEL`) the caller opted
      into the ladder but this station has no resolved normal_level -- grey, NEVER
      treated as "ปกติ".
    - "NORMAL"    -- below every danger threshold, AND (when opted into the ladder) at
      or below the station's own normal_level; when NOT opted in (the original 4-arg
      call, unchanged), below every published threshold that exists for this station.

    Checked highest-band-first so a station missing one threshold (e.g. bank published
    but warning not) still classifies correctly off whichever bands it does have.
    Passing `normal_level=None` (the default) preserves the EXACT original 4-arg
    behavior for every existing call site -- only a caller that explicitly resolves and
    passes a normal_level (or the `NO_NORMAL_LEVEL` sentinel) gets the new ladder.

    Fix MEDIUM-4 (2026-09-26): a non-numeric value/threshold (e.g. a station
    publishing "N/A" or "" instead of a number) used to raise TypeError/ValueError deep in
    the comparison; every input is now coerced through a safe float() first, so a
    non-numeric field is just treated as "not published" (None) rather than crashing.
    """
    opted_in = normal_level is not None
    nl = None if normal_level is NO_NORMAL_LEVEL or normal_level is None else safe_float(normal_level)
    value = safe_float(value)
    warning = safe_float(warning)
    critical = safe_float(critical)
    bank = safe_float(bank)
    if value is None:
        return "NO_THRESHOLD"
    if warning is None and critical is None and bank is None and not opted_in:
        return "NO_THRESHOLD"
    if bank is not None and value >= bank:
        return "OVERBANK"
    if critical is not None and value >= critical:
        return "CRITICAL"
    if warning is not None and value >= warning:
        return "WATCH"
    if opted_in:
        if nl is None:
            return "NO_NORMAL_BASIS"
        return "NORMAL" if value <= nl else "ABOVE_NORMAL"
    if warning is None and critical is None and bank is None:
        return "NO_THRESHOLD"
    return "NORMAL"


def age_hours(observed_at, reference):
    """
    Pure: hours between two ISO-8601 timestamp strings (`reference` - `observed_at`).
    Returns None if either side is missing/unparseable -- callers treat that as stale
    (fail-closed: an unknown age is never presented as fresh).
    """
    if not observed_at or not reference:
        return None
    try:
        dt_obs = datetime.datetime.fromisoformat(observed_at)
        dt_ref = datetime.datetime.fromisoformat(reference)
    except ValueError:
        return None
    return (dt_ref - dt_obs).total_seconds() / 3600.0


# --- THE single freshness gate (house rule, 2026-10-03) ------------------------------
# Every reading must pass THIS function before it is used to decide anything
# (current_local_state colour, L-tier, a contradiction row, a pump/rain/tide/hazard
# field). Fail-closed: an unparseable/missing age is never treated as fresh (same
# posture `age_hours` already documents). No new physics/cutoff is invented here --
# `max_age_hours` is read by the caller from `sources/registry.yaml`'s own
# `max_age_hours` field (added 2026-10-03, documented default per variable class: canal
# level/pump/flood-road readings keep the pre-existing `STALE_HOURS` = 24h cutoff this
# module already enforced; rain/tide/hazard reuse the same 24h figure `kb.py` already
# hardcodes as `_FORECAST_STALE_AFTER_S`); a source with no registry entry/field falls
# back to `STALE_HOURS` below, unchanged from before this function existed.
def is_fresh(observed_at, reference, max_age_hours=STALE_HOURS, future_tolerance_h=-1.0):
    """Return (fresh: bool, age_h: float|None). `fresh=False` -- never read as evidence
    for a decision -- when age_h is None (missing/unparseable timestamp), OR
    age_h > max_age_hours, OR age_h < future_tolerance_h. This is the ONE gate: every
    call site that used to inline `age_h is None or age_h > lwl.STALE_HOURS` should call
    this instead, so there is a single place that defines what "stale" means.

    Fix (2026-10-04): this function used to accept ANY negative
    `age_h` with no lower bound at all -- a row whose `observed_at` was mis-parsed into
    the far future (the real measured case: a Buddhist-year PDF date misread as
    `2569-09-28`, giving `age_h = -4,759,715.5`) passed straight through as `fresh=True`
    and decided `current_local_state`. `future_tolerance_h` is now an explicit,
    bounded allowance -- NOT infinite -- for the one real, intended case: `readout.py`'s
    `as_of_date`-pinned callers set `reference` to LOCAL MIDNIGHT of a given calendar
    day, so a REAL same-day reading observed later that day (e.g. 06:20 UTC against a
    00:00 UTC reference) legitimately produces a small negative age and must still read
    as fresh -- long-settled, widely depended-on behaviour
    (`tests/test_kb_answer.py`'s own `test_dual_state_*` fixtures). The DEFAULT here
    (`-1.0`) is for a REAL wall-clock `reference` (production `kb.py answer`/the MCP
    path, and `readout.py` when no `as_of_date` was pinned) -- at most 1 hour of clock
    skew is tolerated, anything further in the future is rejected outright, regardless
    of `max_age_hours`. A day-pinned caller passes a wider `future_tolerance_h` itself
    (see `readout.py`'s own `_DAY_PIN_FUTURE_TOLERANCE_H`) -- this function never
    guesses which regime it's in from the reference string alone."""
    age_h = age_hours(observed_at, reference)
    if age_h is None:
        return False, age_h
    fresh = age_h <= max_age_hours and age_h >= future_tolerance_h
    return fresh, age_h


def max_age_hours_for(source_id: str, registry: "dict | None" = None) -> float:
    """Max age for `source_id`, read from `sources/registry.yaml`'s own `max_age_hours`
    field for that source (added 2026-10-03). Falls back to `STALE_HOURS` (24h,
    unchanged pre-existing default) when the registry is unavailable or the source has
    no `max_age_hours` field of its own -- never invents a new number, never silently
    widens a cutoff a prior version enforced."""
    if registry is None:
        try:
            import collect as collect_mod
            registry = collect_mod.load_registry()
        except Exception:  # pragma: no cover - defensive, registry must not crash a gate
            return STALE_HOURS
    entry = registry.get(source_id) if registry else None
    val = entry.get("max_age_hours") if entry else None
    try:
        return float(val) if val is not None else STALE_HOURS
    except (TypeError, ValueError):
        return STALE_HOURS


def attach_live_water_level(graph: nx.DiGraph, stations: list) -> dict:
    """
    Join each station to its nearest graph node within NODE_MATCH_MAX_KM (300 m) -- the
    same join radius build_bangkok_canals.py already uses for floodgates/water-level
    context (`FLOODGATE_JOIN_KM`). Stations without their own lat/lon are first run
    through `resolve_station_coordinate()` (fuzzy floodgate-name join).

    Staleness: a station's `observed_at` is compared against the NEWEST `observed_at` in
    this same batch (`STALE_HOURS` = 24h). A stale station (or one with no parseable
    `observed_at`) is skipped entirely -- never attached, counted in `stations_stale`.
    This mirrors the repo's fail-closed discipline: an old or unknown-age reading is not
    presented as a live one.

    NEVER overwrites a node attribute already set by another source or a prior run --
    this function only ever writes its own `live_water_level_*` keys, and skips a node
    that already has a non-null `live_water_level_m`.

    Returns {"nodes_matched", "stations_matched", "stations_total", "stations_no_coord",
    "stations_stale"}.
    """
    nodes = [(n, float(d["lat"]), float(d["lon"]))
             for n, d in graph.nodes(data=True) if d.get("lat") is not None and d.get("lon") is not None]

    observed_ats = [s.get("observed_at") for s in stations if s.get("observed_at")]
    newest = max(observed_ats) if observed_ats else None

    stations_matched = 0
    stations_no_coord = 0
    stations_stale = 0
    matched_node_ids = set()
    for raw_station in stations:
        st = resolve_station_coordinate(raw_station)
        if st.get("lat") is None or st.get("lon") is None:
            stations_no_coord += 1
            continue

        age = age_hours(st.get("observed_at"), newest)
        if age is None or age > STALE_HOURS:
            stations_stale += 1
            continue

        best_node, best_dist = None, float("inf")
        for n, lat, lon in nodes:
            dist = haversine_km(st["lat"], st["lon"], lat, lon)
            if dist < best_dist:
                best_dist, best_node = dist, n
        if best_node is None or best_dist > NODE_MATCH_MAX_KM:
            continue

        data = graph.nodes[best_node]
        existing = data.get("live_water_level_m")
        if existing not in (None, "null", ""):
            continue  # never overwrite an existing live reading (this source or another)

        data["live_water_level_m"] = st["level_m"]
        data["live_water_level_observed_at"] = st.get("observed_at")
        data["live_water_level_station"] = st.get("name_th") or st.get("station_id")
        data["live_water_level_source"] = st.get("source_url")
        data["live_water_level_match_confidence"] = round(
            st.get("match_confidence", 1.0 - min(best_dist / NODE_MATCH_MAX_KM, 1.0)), 3
        )
        data["live_water_level_status"] = classify_level(
            st["level_m"], st.get("warning_level"), st.get("critical_level"), st.get("bank")
        )
        data["live_water_level_warning_m"] = st.get("warning_level")
        data["live_water_level_critical_m"] = st.get("critical_level")
        data["live_water_level_bank_m"] = st.get("bank")
        data["live_water_level_bma_code"] = st.get("canal_oldcode")
        stations_matched += 1
        matched_node_ids.add(best_node)

    return {
        "nodes_matched": len(matched_node_ids),
        "stations_matched": stations_matched,
        "stations_total": len(stations),
        "stations_no_coord": stations_no_coord,
        "stations_stale": stations_stale,
    }


def attach_live_pump_status(graph: nx.DiGraph, pumps: list) -> dict:
    """
    Join each pump station (from `parse_pumphistory_html()`/`fetch_pumphistory()`, real
    lat/lon from the page's own `datapump` metadata array) to its nearest graph node
    within NODE_MATCH_MAX_KM (300 m) -- same radius and never-overwrite rule as
    `attach_live_water_level()`. A pump with no lat/lon (metadata array missing/incomplete
    for that code) is skipped and counted, never guessed.

    Writes `live_pump_code`, `live_pump_name`, `live_pump_level_m`, `live_pump_pumps_on`,
    `live_pump_pumps_total`, `live_pump_gate`, `live_pump_status` (the station's own
    `status_th`, e.g. ปกติ/ขัดข้อง), `live_pump_observed_at`.

    Returns {"nodes_matched", "pumps_matched", "pumps_total", "pumps_no_coord",
    "matches": [{"station_code", "node", "canal_name"} or {"station_code", "node": None}
    per pump, for reporting which canal each pump landed on]}.
    """
    nodes = [(n, float(d["lat"]), float(d["lon"]))
             for n, d in graph.nodes(data=True) if d.get("lat") is not None and d.get("lon") is not None]

    pumps_matched = 0
    pumps_no_coord = 0
    matched_node_ids = set()
    matches = []
    for pump in pumps:
        if pump.get("lat") is None or pump.get("lon") is None:
            pumps_no_coord += 1
            matches.append({"station_code": pump.get("station_code"), "node": None})
            continue

        best_node, best_dist = None, float("inf")
        for n, lat, lon in nodes:
            dist = haversine_km(pump["lat"], pump["lon"], lat, lon)
            if dist < best_dist:
                best_dist, best_node = dist, n
        if best_node is None or best_dist > NODE_MATCH_MAX_KM:
            matches.append({"station_code": pump.get("station_code"), "node": None})
            continue

        data = graph.nodes[best_node]
        if data.get("live_pump_code") not in (None, "null", ""):
            matches.append({"station_code": pump.get("station_code"), "node": None})
            continue  # never overwrite an existing live pump reading

        data["live_pump_code"] = pump.get("station_code")
        data["live_pump_name"] = pump.get("name_th")
        data["live_pump_level_m"] = pump.get("level_m")
        data["live_pump_pumps_on"] = pump.get("pumps_on")
        data["live_pump_pumps_total"] = pump.get("pumps_total")
        data["live_pump_gate"] = pump.get("gate_open")
        data["live_pump_status"] = pump.get("status_th")
        data["live_pump_observed_at"] = pump.get("observed_at")
        pumps_matched += 1
        matched_node_ids.add(best_node)
        matches.append({
            "station_code": pump.get("station_code"),
            "node": best_node,
            "canal_name": data.get("canal_name") or data.get("name") or best_node,
            "dist_km": round(best_dist, 3),
        })

    return {
        "nodes_matched": len(matched_node_ids),
        "pumps_matched": pumps_matched,
        "pumps_total": len(pumps),
        "pumps_no_coord": pumps_no_coord,
        "matches": matches,
    }


def run_probe() -> None:
    print("=== live_water_level.py --probe ===")
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] probing KlongMap ({KLONGMAP_URL}) ...")
    try:
        stations = fetch_klongmap()
        print(f"  OK -- {len(stations)} station(s) with a real coordinate + current reading")
        for s in stations[:3]:
            print(f"    {s['station_id']} {s['name_th']!r} {s['lat']},{s['lon']} "
                  f"{s['level_m']} m @ {s['observed_at']}")
    except LiveSourceUnavailable as e:
        print(f"  UNAVAILABLE -- {e}")

    print(f"\nprobing thaiwater.net BMA canal-level API ({THAIWATER_CANAL_URL}) ...")
    try:
        stations = fetch_thaiwater_stations()
        print(f"  OK -- {len(stations)} station(s) with a real coordinate + current reading")
        for s in stations[:3]:
            print(f"    {s['station_id']} {s['name_th']!r} {s['lat']},{s['lon']} "
                  f"{s['level_m']} m @ {s['observed_at']} ({s.get('agency')})")
    except LiveSourceUnavailable as e:
        print(f"  UNAVAILABLE -- {e}")


def run_attach(graph_path: Path, out_path: Path, from_file: Path = None) -> None:
    if nx is None:
        raise SystemExit(
            "networkx is required for --attach (graph read/write); install it with "
            "`pip install networkx` -- it is not needed for --probe or the collect.py path."
        )
    G = nx.read_graphml(graph_path)
    all_stations = []

    if from_file is not None:
        stations = load_thaiwater_stations_from_file(from_file)
        print(f"[from-file:{from_file}] parsed {len(stations)} station(s), no network call")
        all_stations.extend(stations)
    else:
        for label, fetch_fn in (("klongmap", fetch_klongmap), ("thaiwater", fetch_thaiwater_stations)):
            try:
                stations = fetch_fn()
                print(f"[{label}] fetched {len(stations)} station(s)")
                all_stations.extend(stations)
            except LiveSourceUnavailable as e:
                print(f"[{label}] UNAVAILABLE -- {e}")

    summary = attach_live_water_level(G, all_stations)
    print(f"[attach] {summary['stations_matched']}/{summary['stations_total']} station(s) matched to "
          f"{summary['nodes_matched']} node(s) within {NODE_MATCH_MAX_KM} km "
          f"({summary['stations_no_coord']} station(s) had no resolvable coordinate)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(G, out_path)
    print(f"[attach] wrote {out_path}")


def _bangkok_local(observed_at_utc: str) -> str:
    """UTC ISO-8601 -> 'YYYY-MM-DD HH:MM' in Bangkok local time (UTC+7), for display only."""
    if not observed_at_utc:
        return "-"
    try:
        dt = datetime.datetime.fromisoformat(observed_at_utc)
    except ValueError:
        return observed_at_utc
    local = dt.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
    return local.strftime("%Y-%m-%d %H:%M")


def _print_pump_block(lat: float, lon: float, pump_from_file: Path = None) -> None:
    """
    Prints the Sammakorn ST.SPS pump-station rows as a separate block, sorted by distance
    from the --watch centre (lat, lon) using the real lat/lon carried on each row from the
    page's own `datapump` metadata array. Only runs when `--pump-from-file` is given (no
    implicit live fetch on every --watch call, given the host's other 403s).
    """
    if pump_from_file is None:
        return
    rows = load_pumphistory_from_file(Path(pump_from_file))
    rows.sort(key=lambda r: (haversine_km(lat, lon, r["lat"], r["lon"])
                              if r.get("lat") is not None and r.get("lon") is not None else float("inf")))
    print()
    print("pump stations (sorted by distance from --watch centre):")
    header = (f"{'dist_km':>8}  {'code':<12} {'name':<32} {'district':<14} {'level_m':>8} "
              f"{'pumps_on/total':>15} {'gate_m':>7} {'observed_at (Bangkok)':<20}")
    print(header)
    print("-" * len(header))
    for r in rows:
        dist_str = (f"{haversine_km(lat, lon, r['lat'], r['lon']):8.2f}"
                    if r.get("lat") is not None and r.get("lon") is not None else f"{'-':>8}")
        level_str = f"{r['level_m']:.2f}" if r["level_m"] is not None else "-"
        gate_str = f"{r['gate_open']:.2f}" if r["gate_open"] is not None else "-"
        pumps_str = f"{r['pumps_on']}/{r['pumps_total']}"
        print(f"{dist_str}  {r['station_code']:<12} {(r.get('name_th') or '-'):<32} "
              f"{(r.get('district') or '-'):<14} {level_str:>8} "
              f"{pumps_str:>15} {gate_str:>7} "
              f"{_bangkok_local(r.get('observed_at')):<20}")


def run_watch(lat: float, lon: float, radius_km: float, from_file: Path = None,
              pump_from_file: Path = None) -> None:
    """
    Print a plain-text table of every non-stale thaiwater/BMA canal station within
    `radius_km` of (lat, lon), sorted by distance, plus a one-line summary. Read-only --
    does not touch any graph file. `--from-file` reuses a previously-cached raw response
    (no network call); otherwise does exactly one live fetch via `fetch_thaiwater_stations()`.
    """
    if from_file is not None:
        stations = load_thaiwater_stations_from_file(Path(from_file))
        print(f"[from-file:{from_file}] parsed {len(stations)} station(s), no network call")
    else:
        stations = fetch_thaiwater_stations()
        print(f"[thaiwater] fetched {len(stations)} station(s)")

    observed_ats = [s.get("observed_at") for s in stations if s.get("observed_at")]
    newest = max(observed_ats) if observed_ats else None

    rows = []
    stale_skipped = 0
    for s in stations:
        dist = haversine_km(lat, lon, s["lat"], s["lon"])
        if dist > radius_km:
            continue
        age = age_hours(s.get("observed_at"), newest)
        if age is None or age > STALE_HOURS:
            stale_skipped += 1
            continue
        status = classify_level(s["level_m"], s.get("warning_level"), s.get("critical_level"), s.get("bank"))
        rows.append((dist, s, status))
    rows.sort(key=lambda r: r[0])

    header = (f"{'dist_km':>8}  {'bma_code':<12} {'name':<30} {'value_m':>8} {'out_m':>7} "
              f"{'warn_m':>7} {'crit_m':>7} {'bank_m':>7} {'status':<12} {'observed_at (Bangkok)':<20}")
    print()
    print(header)
    print("-" * len(header))
    for dist, s, status in rows:
        out_str = f"{s.get('canal_out'):.2f}" if s.get("is_gate") and s.get("canal_out") is not None else "-"
        fmt = lambda v: (f"{v:.2f}" if v is not None else "-")
        print(f"{dist:8.2f}  {(s.get('canal_oldcode') or '-'):<12} {(s.get('name_th') or '-'):<30} "
              f"{s['level_m']:8.2f} {out_str:>7} {fmt(s.get('warning_level')):>7} "
              f"{fmt(s.get('critical_level')):>7} {fmt(s.get('bank')):>7} {status:<12} "
              f"{_bangkok_local(s.get('observed_at')):<20}")

    n_critical = sum(1 for _, _, st in rows if st in ("CRITICAL", "OVERBANK"))
    n_watch = sum(1 for _, _, st in rows if st == "WATCH")
    print()
    print(f"{len(rows)} stations, {n_critical} CRITICAL, {n_watch} WATCH, {stale_skipped} stale skipped")

    _print_pump_block(lat, lon, pump_from_file)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", action="store_true", help="Fresh single fetch from each source, print status.")
    ap.add_argument("--attach", metavar="GRAPH_IN", help="Attach live levels onto an existing canal GraphML file.")
    ap.add_argument("--out", metavar="GRAPH_OUT", help="Where to write the updated GraphML (required with --attach).")
    ap.add_argument("--from-file", metavar="JSON", help=(
        "Attach/watch offline from a previously-saved raw thaiwater canal_waterlevel JSON "
        "body (e.g. raw/live/thaiwater_bma/<ts>_canal_waterlevel.json) instead of a live fetch."))
    ap.add_argument("--watch", nargs=2, type=float, metavar=("LAT", "LON"), help=(
        "Print a plain-text table of non-stale canal stations within --radius-km of "
        "LAT LON, sorted by distance. Read-only, no graph file touched."))
    ap.add_argument("--radius-km", type=float, default=5.0, help="Radius for --watch (default 5 km).")
    ap.add_argument("--pump-from-file", metavar="HTML", help=(
        "With --watch, also print the Sammakorn ST.SPS pump-station block from a "
        "previously-saved raw PumpHistory HTML page, sorted by distance from the --watch "
        "centre (real lat/lon from the page's own datapump metadata), no live fetch."))
    args = ap.parse_args()

    if args.probe:
        run_probe()
        return
    if args.attach:
        if not args.out:
            sys.exit("--attach requires --out")
        run_attach(Path(args.attach), Path(args.out), from_file=Path(args.from_file) if args.from_file else None)
        return
    if args.watch:
        lat, lon = args.watch
        run_watch(lat, lon, args.radius_km, from_file=Path(args.from_file) if args.from_file else None,
                  pump_from_file=Path(args.pump_from_file) if args.pump_from_file else None)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
