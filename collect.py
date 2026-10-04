#!/usr/bin/env python3
"""
Registry-driven collector for the Sammakorn live flood-context data system.

Reads `sources/registry.yaml`, then for `--all` or `--source ID` runs at most ONE request
per URL per source per run (this workspace's BMA host-safety rule and this repo's existing
fail-closed discipline in live_water_level.py: no retry loop anywhere in this file, and a
403/connection-reset on one source trips a per-host circuit breaker for the rest of the
run -- see `run()`), saves a raw snapshot under `raw/live/<source>/<UTC timestamp>.<ext>`,
then normalises what was fetched into `data/observations.sqlite` via store.py.

Fetch/parse logic for thaiwater canal_waterlevel and BMA PumpHistory is NOT duplicated
here -- it's imported straight from `live_water_level.py` (already implemented, already
unit-tested there). New parsers this system adds (flood_road, the DDS flood-report HTML
table, the DDS daily PDF, the tide-table PDF) live in `parsers.py`.

CLI:
    python3 collect.py --all
    python3 collect.py --source thaiwater_canal_waterlevel
    python3 collect.py --source dds_daily_pdf --from-file raw/dds_reports/dds_daily_20260926T0437Z.pdf
    python3 collect.py --all --dry-run
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode, urlparse

import yaml

import live_water_level as lwl
import parsers
import store
from tools.harvest.forecast7d_draft import (  # noqa: E402 -- reuse the ALREADY-reviewed
    # draft parsers (pure functions, no network I/O) instead of re-deriving a second copy
    # of the same daily/ensemble/MET-Norway/skill-check parsing logic -- see that module's
    # own docstring (docs/knowledge/FORECAST_7DAY_SOURCES.md ss5, "reference implementation").
    parse_openmeteo_multimodel_daily,
    parse_openmeteo_ensemble_members,
    parse_metno_locationforecast_daily,
    parse_openmeteo_previous_runs_skillcheck,
)

HERE = Path(__file__).parent
REGISTRY_PATH = HERE / "sources" / "registry.yaml"
RAW_LIVE_DIR = HERE / "raw" / "live"

GENERIC_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
}
REQUEST_TIMEOUT_S = 30
# NOTE: this is `urllib`'s per-socket-operation timeout (each individual send/recv), not a
# total wall-clock deadline for the request the way curl's `--max-time` is -- a server that
# drips bytes slowly enough to keep resetting the per-op clock could in principle run past
# this many seconds in total. Not observed in practice against these hosts; documented here
# instead of citing `--max-time`, which is a curl flag this code doesn't use.
PDF_TIMEOUT_S = 300


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data.get("sources", [])}


def _utcnow_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _cache_raw(source_id: str, payload: bytes, suffix: str) -> Path:
    d = RAW_LIVE_DIR / source_id
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{_utcnow_stamp()}.{suffix}"
    p.write_bytes(payload)
    return p


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class CollectResult:
    # A source this file never attempted to fetch (no fetcher
    # by design, no collector implemented) must not report ok=True -- that overstated
    # "N ok" counts as real network successes when some of them were never requested at
    # all. `skipped=True` means "intentionally not fetched this run"; `ok` for a skipped
    # result is always False, so nothing downstream has to special-case BOTH flags to
    # avoid double-counting.
    def __init__(self, source_id, ok, http=None, note="", counts=None, skipped=False):
        self.source_id, self.http, self.note = source_id, http, note
        self.skipped = skipped
        self.ok = False if skipped else ok
        self.counts = counts or {}

    def __repr__(self):
        # A missing-API-key result is UNKNOWN (never fetched, by design, on THIS
        # machine right now), not FAIL -- FAIL implies an attempt was made and it
        # failed. Detected off the note text `_missing_api_key_env`/the per-collector
        # belt-and-suspenders checks both use, rather than a third boolean flag, so
        # every current and future key-gated collector gets this for free.
        if self.skipped:
            status = "skipped"
        elif self.ok:
            status = "ok"
        elif (self.note or "").startswith("missing env var "):
            status = "unknown (not_fetched_missing_key)"
        else:
            status = "FAIL"
        counts_part = f" {self.counts}" if self.counts else ""
        return f"[{self.source_id}] status={status} http={self.http} {self.note}{counts_part}"


def _one_get(url: str, headers: dict, timeout: int = REQUEST_TIMEOUT_S) -> tuple:
    """ONE GET, no retry. Returns (status, body). Raises on network error/non-200."""
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def _one_post(url: str, headers: dict, body: bytes,
              timeout: int = REQUEST_TIMEOUT_S) -> tuple:
    """ONE POST, no retry -- same one-request-per-URL discipline as `_one_get`, for the
    handful of RID endpoints that require POST (e.g. `api/dams`). Returns (status, body).
    Raises on network error/non-200."""
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


# --- per-source collectors ---------------------------------------------------------------

def collect_thaiwater_canal_waterlevel(conn, dry_run=False) -> CollectResult:
    sid = "thaiwater_canal_waterlevel"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + lwl.THAIWATER_CANAL_URL)
    try:
        stations = lwl.fetch_thaiwater_stations()  # already caches raw + does the one GET
    except lwl.LiveSourceUnavailable as e:
        return CollectResult(sid, False, note=str(e))
    n = 0
    for s in stations:
        if s["lat"] is None or s["lon"] is None or s.get("observed_at") is None:
            continue
        inserted = store.insert_observation(
            conn, source_id=sid, station_code=s.get("canal_oldcode") or s.get("station_id"),
            station_name=s.get("name_th"), lat=s["lat"], lon=s["lon"],
            variable="canal_water_level_m", value=s["level_m"], unit="m",
            observed_at_utc=s["observed_at"], fetched_at_utc=s["fetched_at"],
            trust_tier="official_telemetry", warning=s.get("warning_level"),
            critical=s.get("critical_level"), bank=s.get("bank"),
            status=lwl.classify_level(s["level_m"], s.get("warning_level"),
                                       s.get("critical_level"), s.get("bank")),
            provenance={"source_url": s.get("source_url"), "agency": s.get("agency")},
        )
        n += inserted
    return CollectResult(sid, True, http=200, note=f"{len(stations)} station(s) fetched",
                          counts={"inserted": n})


def collect_thaiwater_flood_road(conn, dry_run=False) -> CollectResult:
    sid = "thaiwater_flood_road"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + parsers.THAIWATER_FLOOD_ROAD_URL)
    try:
        status, body = _one_get(parsers.THAIWATER_FLOOD_ROAD_URL, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_thaiwater_flood_road(json.loads(body))
    n = 0
    for r in rows:
        if r.get("observed_at") is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r.get("floodroad_oldcode") or r.get("station_id"),
            station_name=r.get("road_name_th"), lat=r["lat"], lon=r["lon"],
            variable="floodroad_value_cm", value=r.get("value_cm"), unit="cm",
            observed_at_utc=r["observed_at"], fetched_at_utc=fetched_at,
            trust_tier="official_telemetry",
            provenance={"source_url": r.get("source_url"), "district_th": r.get("district_th")},
        )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} road station(s) fetched",
                          counts={"inserted": n})


def collect_thaiwater_rain_24h(conn, dry_run=False) -> CollectResult:
    """CI had no rain collector at all, so the rain
    tile always fell back to a one-time manual raw/gapfill/rain_24h*.json snapshot that
    goes stale forever. Same one-GET/one-cache-raw discipline as
    collect_thaiwater_flood_road; writes to raw/live/thaiwater_rain_24h/<ts>.json."""
    sid = "thaiwater_rain_24h"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + parsers.THAIWATER_RAIN_24H_URL)
    try:
        status, body = _one_get(parsers.THAIWATER_RAIN_24H_URL, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_thaiwater_rain_24h(json.loads(body))
    n = 0
    n_1h = 0
    for r in rows:
        if r.get("observed_at") is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r.get("station_id"),
            station_name=r.get("station_name_th"), lat=r["lat"], lon=r["lon"],
            variable="rain_24h_mm", value=r.get("mm_24h"), unit="mm",
            observed_at_utc=r["observed_at"], fetched_at_utc=fetched_at,
            trust_tier="official_telemetry",
            provenance={"source_url": r.get("source_url"), "agency": r.get("agency"),
                        "agency_th": r.get("agency_th")},
        )
        # TODO #181 (2026-09-28): the same payload also carries a rolling 1h window
        # (`rain_1h`), absent on ~12% of records -- store it as its own variable only when
        # present, never fabricated from rain_24h. See sources/registry.yaml's
        # thaiwater_rain_24h entry and parsers.parse_thaiwater_rain_24h's docstring for the
        # window-end-timestamp caveat (RELAYED, not independently verified against API docs).
        if r.get("mm_1h") is not None:
            n_1h += store.insert_observation(
                conn, source_id=sid, station_code=r.get("station_id"),
                station_name=r.get("station_name_th"), lat=r["lat"], lon=r["lon"],
                variable="rain_1h_mm", value=r.get("mm_1h"), unit="mm",
                observed_at_utc=r["observed_at"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                provenance={"source_url": r.get("source_url"), "agency": r.get("agency"),
                            "agency_th": r.get("agency_th")},
            )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} rain station(s) fetched, {n_1h} with rain_1h_mm",
                          counts={"inserted": n, "inserted_1h": n_1h})


def collect_bma_pumphistory(conn, dry_run=False) -> CollectResult:
    sid = "bma_pumphistory"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + lwl.PUMPHISTORY_URL)
    try:
        rows = lwl.fetch_pumphistory(station_codes=[])  # every station on the page
    except lwl.LiveSourceUnavailable as e:
        return CollectResult(sid, False, note=str(e))
    n = 0
    for r in rows:
        if r.get("observed_at") is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r.get("station_code"),
            station_name=r.get("name_th"), lat=r.get("lat"), lon=r.get("lon"),
            variable="pump_level_m", value=r.get("level_m"), unit="m",
            observed_at_utc=r["observed_at"], fetched_at_utc=r["fetched_at"],
            trust_tier="official_telemetry", status=r.get("status_th"),
            provenance={"source_url": r.get("source_url"), "pumps_on": r.get("pumps_on"),
                        "pumps_total": r.get("pumps_total"), "gate_open_m": r.get("gate_open"),
                        "sensor_status": r.get("sensor_status")},
        )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} pump station row(s) fetched",
                          counts={"inserted": n})


def collect_dds_flood_report(conn, dry_run=False, from_file: Path = None) -> CollectResult:
    sid = "dds_flood_report"
    url = "https://dds.bangkok.go.th/flood_report.php"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    if from_file is not None:
        html = Path(from_file).read_text(encoding="utf-8")
        fetched_at = _utcnow_iso()
        note_prefix = f"from-file:{from_file}, no network call"
    else:
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            return CollectResult(sid, False, note=f"network/HTTP error: {e}")
        if status != 200:
            return CollectResult(sid, False, http=status, note=f"HTTP {status}")
        _cache_raw(sid, body, "html")
        html = body.decode("utf-8", errors="replace")
        fetched_at = _utcnow_iso()
        note_prefix = "live GET"
    rows = parsers.parse_dds_flood_report_html(html)
    if not rows:
        store.insert_document(conn, source_id=sid, fetched_at_utc=fetched_at, text=html,
                               section="flood_report_unparsed_page")
        return CollectResult(sid, True, http=200,
                              note=f"{note_prefix}; table not found, stored raw HTML")
    n_docs = 0
    for r in rows:
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at,
            section="flood_road_detail",
            text=(f"{r['district_th']} | {r['road_th']} | {r['area_detail_th']} | "
                  f"height_cm={r['flood_height_cm']} | length_m={r['flood_length_m']} | "
                  f"lanes={r['lanes_affected_th']} | start={r['flood_start']} | "
                  f"end={r['flood_end']} | duration={r['flood_duration_th']} | "
                  f"rain_mm={r['rain_total_mm']}"),
        )
        n_docs += 1
    return CollectResult(sid, True, http=200, note=f"{note_prefix}; {len(rows)} road row(s)",
                          counts={"documents": n_docs})


def collect_dds_daily_pdf(conn, dry_run=False, from_file: Path = None) -> CollectResult:
    sid = "dds_daily_pdf"
    url = "https://dds.bangkok.go.th/public_content/files/001/0004901_1.pdf"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)

    fetched_at = _utcnow_iso()
    http_status = None
    if from_file is not None:
        # Deliberately makes ZERO network calls -- this branch exists so a file another
        # pass already downloaded today can be reused without touching the host again at
        # all.
        pdf_path = Path(from_file)
        note = f"from-file:{from_file}, no network call at all"
    else:
        # ONE GET, no HEAD first. An earlier version did HEAD-then-conditional-GET, which
        # is two requests to the same URL on any run where the PDF has changed (or on the
        # very first run ever, before any snapshot/.meta.txt exists) -- that breaks the
        # "at most one request per URL per run" host-safety rule. A single unconditional
        # GET is simpler and never exceeds one request; it costs re-downloading an
        # unchanged same-day PDF, which is an acceptable trade against a host-safety
        # violation.
        try:
            status, body = _one_get(url, GENERIC_HEADERS, timeout=PDF_TIMEOUT_S)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            return CollectResult(sid, False, note=f"GET network/HTTP error: {e}")
        if status != 200:
            return CollectResult(sid, False, http=status, note=f"HTTP {status}")
        http_status = status
        pdf_path = _cache_raw(sid, body, "pdf")
        note = "live GET"

    proc = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                           capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at, path=str(pdf_path),
            section="pdftotext_failed",
            text=(f"pdftotext exit={proc.returncode} stderr={proc.stderr!r} "
                  f"stdout_len={len(proc.stdout)} -- PDF likely corrupted/empty/"
                  f"unreadable; raw file kept at {pdf_path}, nothing parsed this run."))
        return CollectResult(
            sid, True, http=http_status,
            note=f"{note}; pdftotext could not extract text -- raw path+error stored as "
                 "a document, 0 observations",
            counts={"observations": 0, "documents": 1})
    text = proc.stdout
    parsed = parsers.parse_dds_daily_pdf_text(text)
    header = parsed["header"]
    report_date = (f"{header['year_ce']}-{header['day']:02d}" if header else None)
    # `header_date_recognized` = False means `observed_at` below is NOT the bulletin's own
    # date -- it silently fell back to `fetched_at` (the moment THIS pipeline downloaded
    # the file). A prior version had no such flag, so a bulletin whose header line wasn't
    # recognized (layout change, OCR artifact, etc.) got every row stamped as if it were a
    # fresh same-instant reading -- never marked as uncertain. Carried in each row's
    # `provenance` below so a reader/readout can tell "the bulletin says this date" from
    # "this pipeline is guessing the date is roughly when it fetched the file" (which
    # should read as OPEN, not MEASURED/RELAYED at face value).
    header_date_recognized = False
    if header:
        # Thai month name -> ISO date, for observed_at_utc (07:00 Bangkok local snapshot
        # per the bulletin's own framing -- see parsers.py module docstring).
        month_num = parsers.THAI_MONTHS.get(header["month_th"])
        if month_num:
            obs_date = datetime.date(header["year_ce"], month_num, header["day"])
            observed_local = datetime.datetime.combine(
                obs_date, datetime.time(7, 0),
                tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
            observed_at = observed_local.astimezone(datetime.timezone.utc).isoformat()
            header_date_recognized = True
        else:
            observed_at = fetched_at
    else:
        observed_at = fetched_at
    if not header_date_recognized:
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at, path=str(pdf_path),
            section="header_date_not_recognized",
            text=(f"The bulletin header line/month wasn't recognized -- rows below that "
                  f"use `observed_at` are stamped with the FETCH time ({fetched_at}), not "
                  "a bulletin-stated date. Treat their freshness as OPEN, not confirmed."))

    n_obs, n_docs = 0, 0
    for row in parsed["rain_stations"]:
        n_obs += store.insert_observation(
            conn, source_id=sid, station_code=None, station_name=row["location_th"],
            variable="rain_24h_mm", value=row["rain_mm"], unit="mm",
            observed_at_utc=observed_at, fetched_at_utc=fetched_at, trust_tier="official_report",
            provenance={"section": "rainfall", "rank": row["rank"], "issue_no":
                        header.get("issue_no") if header else None,
                        "header_date_recognized": header_date_recognized})
    for key in ("canal_outer", "canal_inner"):
        for row in parsed[key]:
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=None, station_name=row["name_th"],
                variable="canal_level_0700_m", value=row["today_0700_m"], unit="m",
                observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", critical=row["critical_m"],
                status=row["status_th"],
                provenance={"section": key, "yesterday_max_m": row["yesterday_max_m"],
                            "header_date_recognized": header_date_recognized})
    for row in parsed["chaophraya_rows"]:
        row_date_iso = parsers.thai_short_date_to_iso(row["date_th"])
        if row_date_iso is None:
            store.insert_document(conn, source_id=sid, fetched_at_utc=fetched_at,
                                   section="chaophraya_flow_tide_unrecognized_date",
                                   text=str(row))
            continue
        # Daily Qmax figures carry no time-of-day in the bulletin -- 00:00 Bangkok local
        # (converted to UTC) is used as a date marker, not a claimed instant reading
        # (Dr-tier judgment call, documented here rather than silently assumed).
        row_observed_at = datetime.datetime.combine(
            datetime.date.fromisoformat(row_date_iso), datetime.time(0, 0),
            tzinfo=datetime.timezone(datetime.timedelta(hours=7))
        ).astimezone(datetime.timezone.utc).isoformat()
        for field in ("qmax_nakhonsawan_cms", "qmax_chaophraya_dam_cms",
                      "qmax_rama6_dam_cms", "qmax_samkhok_cms", "tide_base_level_m"):
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code="RID_CHAOPHRAYA", station_name=field,
                variable=field, value=row.get(field), unit=("cms" if "qmax" in field else "m"),
                observed_at_utc=row_observed_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance={"section": "chaophraya_flow_tide",
                                                            "date_th": row["date_th"]})
    for row in parsed["reservoirs"]:
        res_date_iso = parsers.thai_short_date_to_iso(row["as_of_date_th"])
        if res_date_iso is None:
            store.insert_document(conn, source_id=sid, fetched_at_utc=fetched_at,
                                   section="reservoirs_unrecognized_date", text=str(row))
            continue
        res_observed_at = datetime.datetime.combine(
            datetime.date.fromisoformat(res_date_iso), datetime.time(0, 0),
            tzinfo=datetime.timezone(datetime.timedelta(hours=7))
        ).astimezone(datetime.timezone.utc).isoformat()
        n_obs += store.insert_observation(
            conn, source_id=sid, station_code=row["name_th"], station_name=row["name_th"],
            variable="reservoir_storage_pct", value=row["storage_pct"], unit="%",
            observed_at_utc=res_observed_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"section": "reservoirs", "capacity_mcm": row["capacity_mcm"],
                        "storage_mcm": row["storage_mcm"],
                        "inflow_mcm_day": row["inflow_mcm_day"],
                        "outflow_mcm_day": row["outflow_mcm_day"]})
    for row in parsed["tide_dedicated"]:
        n_obs += store.insert_observation(
            conn, source_id=sid, station_code="NAVY_HYDRO", station_name=row["kind_th"],
            variable=f"tide_{row['kind_th']}_am_m", value=row["am_level_m"], unit="m",
            observed_at_utc=observed_at, fetched_at_utc=fetched_at, trust_tier="official_report",
            provenance={"section": "tide_dedicated", "am_time": row["am_time"],
                        "pm_time": row["pm_time"], "pm_level_m": row["pm_level_m"],
                        "header_date_recognized": header_date_recognized})
    for row in parsed["chaophraya_partial"]:
        store.insert_document(conn, source_id=sid, fetched_at_utc=fetched_at,
                               section="chaophraya_flow_tide_partial",
                               text=f"{row['date_th']}: {row['raw_line']}")
        n_docs += 1
    for doc in parsed["documents"]:
        store.insert_document(conn, source_id=sid, fetched_at_utc=fetched_at,
                               path=str(pdf_path), section=doc["section"], text=doc["text"])
        n_docs += 1

    return CollectResult(sid, True, http=http_status, note=note,
                          counts={"observations": n_obs, "documents": n_docs,
                                  "issue": header.get("issue_no") if header else None})


def collect_dds_tide_pdf(conn, dry_run=False, from_file: Path = None) -> CollectResult:
    sid = "dds_tide_pdf"
    url = "https://dds.bangkok.go.th/public_content/files/001/0006030_1.pdf"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)

    fetched_at = _utcnow_iso()
    http_status = None
    if from_file is not None:
        # See collect_dds_daily_pdf's from_file branch note -- same discipline: zero
        # network calls.
        pdf_path = Path(from_file)
        note = f"from-file:{from_file}, no network call at all"
    else:
        # ONE GET, no HEAD first -- see collect_dds_daily_pdf's comment for why the earlier
        # HEAD-then-conditional-GET shape broke the one-request-per-URL-per-run rule.
        try:
            status, body = _one_get(url, GENERIC_HEADERS, timeout=PDF_TIMEOUT_S)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            return CollectResult(sid, False, note=f"GET network/HTTP error: {e}")
        if status != 200:
            return CollectResult(sid, False, http=status, note=f"HTTP {status}")
        http_status = status
        pdf_path = _cache_raw(sid, body, "pdf")
        note = "live GET"

    proc = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                           capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at, path=str(pdf_path),
            section="pdftotext_failed",
            text=(f"pdftotext exit={proc.returncode} stderr={proc.stderr!r} "
                  f"stdout_len={len(proc.stdout)} -- PDF likely corrupted/empty/"
                  f"unreadable; raw file kept at {pdf_path}, nothing parsed this run."))
        return CollectResult(
            sid, True, http=http_status,
            note=f"{note}; pdftotext could not extract text -- raw path+error stored as "
                 "a document, 0 observations",
            counts={"months": 0, "observations": 0, "documents": 1})
    text = proc.stdout
    months = parsers.parse_tide_table_text(text)
    n_obs = 0
    for month in months:
        for day in month["days"]:
            try:
                obs_date = datetime.date(month["year"], month["month"], day["day"])
            except ValueError:
                continue
            for field in ("hw_am", "lw_am", "hw_pm", "lw_pm"):
                level = day.get(f"{field}_level_m")
                if level is None:
                    continue
                raw_time = day.get(f"{field}_time")  # "HHMM" or None
                if raw_time and len(raw_time) == 4 and raw_time.isdigit():
                    time_of_day = datetime.time(int(raw_time[:2]), int(raw_time[2:]))
                else:
                    time_of_day = datetime.time(0, 0)  # time unknown -- date-only marker
                observed_local = datetime.datetime.combine(
                    obs_date, time_of_day,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                n_obs += store.insert_observation(
                    conn, source_id=sid, station_code="NAVY_HYDRO_HQ",
                    station_name=month["station_th"], variable=f"tide_{field}_level_m",
                    value=level, unit="m",
                    observed_at_utc=observed_local.astimezone(datetime.timezone.utc).isoformat(),
                    fetched_at_utc=fetched_at, trust_tier="official_report",
                    provenance={"section": "monthly_tide_table", "day": day["day"],
                                "raw_time": raw_time})
    return CollectResult(sid, True, http=http_status, note=note,
                          counts={"months": len(months), "observations": n_obs})


def collect_bma_klongmap(conn, dry_run=False) -> CollectResult:
    sid = "bma_klongmap"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + lwl.KLONGMAP_URL)
    try:
        stations = lwl.fetch_klongmap()
    except lwl.LiveSourceUnavailable as e:
        return CollectResult(sid, False, note=f"dormant, confirmed: {e}")
    n = 0
    for s in stations:
        if s.get("observed_at") is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=s.get("station_id"), station_name=s.get("name_th"),
            lat=s["lat"], lon=s["lon"], variable="canal_water_level_m", value=s["level_m"],
            unit="m", observed_at_utc=s["observed_at"], fetched_at_utc=s["fetched_at"],
            trust_tier="official_telemetry", provenance={"source_url": s.get("source_url")})
    return CollectResult(sid, True, http=200, note=f"unexpectedly live -- {len(stations)} station(s)",
                          counts={"inserted": n})


def collect_bma_watermap(conn, dry_run=False) -> CollectResult:
    """BMA water/PageMap/GoogleMap -- see docs/knowledge/BMA_WATER_MAP_PROBE.md (probe,
    2026-09-27) and sources/registry.yaml's bma_watermap entry for the full spec. ONE
    POST per run (this workspace's BMA-host rule -- weather.bangkok.go.th), no retry;
    any non-200/non-JSON/non-list response is treated as a signal to report failure for
    this run, never to retry a different payload value.

    Three observation rows per station where applicable, all keyed by the station's own
    `water_code` (never geocoded/inferred): (1) `canal_water_level_m` (wl_in, +
    warning/critical), (2) `gate_opening_m` per non-null watergateNN field -- station_code
    is `<water_code>#gate<NN>` (NOT the bare water_code) because this repo's observations
    table's identity key is (source_id, station_code, variable, observed_at_utc), and
    several gates on the same station share one observed_at_utc timestamp -- a bare
    water_code would collide and silently drop every gate after the first (verified
    against store.py's ux_observations_identity_v2 index before choosing this key; the
    gate index is ALSO carried in `provenance.gate_index` and `provenance.water_code`
    for any reader that wants the bare water_code), (3) `water_control_m` only when the
    field is non-null (null on every station in the 2026-09-27 probe archive -- this
    collector stores it automatically the day BMA populates it, no code change needed).
    """
    sid = "bma_watermap"
    url = parsers.BMA_WATERMAP_URL
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would POST " + url)
    headers = dict(GENERIC_HEADERS)
    headers.update({
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://weather.bangkok.go.th/water/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    # "TEST_DATA_GOES_HERE" is the page's own JS placeholder value (per the probe doc,
    # section 2) -- sending it back returned the full unfiltered 312-record set. Treated
    # as this source's "get everything" payload, not reverse-engineered further.
    body_bytes = urlencode({"payload": "TEST_DATA_GOES_HERE"}).encode("ascii")
    try:
        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
            status, body = resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return CollectResult(sid, False, http=e.code,
                              note=f"HTTP {e.code} -- per sources/registry.yaml, mark DORMANT "
                                   "if this persists, do not retry a payload variation")
    except (urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        return CollectResult(sid, False, http=status, note=f"non-JSON response: {e}")
    if not isinstance(data, list):
        return CollectResult(sid, False, http=status,
                              note="unexpected response shape (not a JSON array) -- "
                                   "endpoint may have changed, not retried")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    stations = parsers.parse_bma_watermap_stations(data)
    n_level = n_gates = n_control = 0
    for s in stations:
        if s.get("observed_at") is None:
            continue
        # Sensor-fault guard (2026-09-27, same discipline as collect_bma_pumphistory()):
        # a station reporting a fault status (ขัดข้อง) has its wl_in stored as NULL, never
        # its last-latched/garbage reading -- `status` still carries the raw status_th so
        # the row stays queryable/auditable, just untrusted for level.
        wl_sensor_status = lwl.sensor_status_from_status_th(s.get("status_th"))
        wl_value = None if wl_sensor_status == "fault" else s.get("wl_in")
        if s.get("wl_in") is not None:
            n_level += store.insert_observation(
                conn, source_id=sid, station_code=s["water_code"],
                station_name=s.get("water_name"), lat=s.get("lat"), lon=s.get("lon"),
                variable="canal_water_level_m", value=wl_value, unit="m",
                observed_at_utc=s["observed_at"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry", warning=s.get("warning"),
                critical=s.get("critical"), status=s.get("status_th"),
                provenance={"source_url": s["source_url"],
                            "district_name": s.get("district_name"),
                            "sensor_status": wl_sensor_status})
        for gate_index, height_m in s["gates"].items():
            n_gates += store.insert_observation(
                conn, source_id=sid, station_code=f"{s['water_code']}#gate{gate_index:02d}",
                station_name=s.get("water_name"), lat=s.get("lat"), lon=s.get("lon"),
                variable="gate_opening_m", value=height_m, unit="m",
                observed_at_utc=s["observed_at"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                provenance={"source_url": s["source_url"], "water_code": s["water_code"],
                            "gate_index": gate_index})
        if s.get("water_control") is not None:
            n_control += store.insert_observation(
                conn, source_id=sid, station_code=s["water_code"],
                station_name=s.get("water_name"), lat=s.get("lat"), lon=s.get("lon"),
                variable="water_control_m", value=s["water_control"], unit="m",
                observed_at_utc=s["observed_at"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                provenance={"source_url": s["source_url"]})
    return CollectResult(
        sid, True, http=200,
        note=(f"{len(stations)} station(s) fetched, {n_level} water-level reading(s), "
              f"{n_gates} gate reading(s), {n_control} water_control reading(s)"),
        counts={"inserted": n_level, "gate_readings": n_gates, "water_control": n_control})


BMA_STATION_DETAIL_URL_TMPL = "https://weather.bangkok.go.th/water/StationDetail?id={water_id}"
BMA_STATION_DETAIL_CURSOR_PATH = HERE / "data" / "bma_station_detail_cursor.json"
BMA_STATION_DETAIL_BATCH_SIZE = 1
# NOTE (2026-09-27, corrected after this repo's own tests/test_registry.py::
# test_bma_hosts_are_capped_at_one_request_per_run and a live confirmed 403 on the 3rd
# request of a first attempted batch of 10): this workspace's BMA-host rule caps EVERY
# weather.bangkok.go.th / dds.bangkok.go.th source at max_requests_per_run <= 1, with no
# exception for "different query string, same path" -- a batch of 10 GETs to
# /water/StationDetail?id=... in one run IS a burst on that host, not 10 independent
# single-request sources. A full 312-station sweep at 1/run now takes ~312 runs to clear
# -- slower than the originally proposed 10/run (~16h at a 30-min cadence, historical note:
# collection became on-demand 2026-10-02, no fixed cadence, so wall-clock time depends on
# how often a run is triggered), but this is what the host tolerated in practice; a human
# may revisit the batch size only after confirming with the founder that a larger batch is
# authorized.

# Per-page admin-form field name -> the observation `variable` this collector stores it
# as. See tools/harvest/bma_station_detail_draft.py's FIELD_IDS /
# parse_station_detail_fields() and docs/knowledge/BMA_STATION_DETAIL_PROBE.md §6/§7.
_STATION_DETAIL_FIELD_TO_VARIABLE = {
    "txt_water_control": "water_control_m",
    "txt_warning": "warning_m",
    "txt_critical": "critical_m",
    "txt_warning_out01": "warning_out01_m",
    "txt_critical_out01": "critical_out01_m",
    "txt_left_bank": "left_bank_m",
    "txt_right_bank": "right_bank_m",
    "txt_bed_bank": "bed_bank_m",
}


def _bma_station_detail_water_ids() -> list:
    """Read (water_id, water_code, water_name) triples out of the most recent cached
    bma_watermap raw snapshot -- this source rotates over that same id space (confirmed
    1:1 with StationDetail's own `id` param, see BMA_STATION_DETAIL_PROBE.md §4) rather
    than re-deriving/guessing an id range itself. Returns [] if bma_watermap has never
    been run (nothing cached yet) -- never fabricates an id list."""
    d = RAW_LIVE_DIR / "bma_watermap"
    if not d.is_dir():
        return []
    snapshots = sorted(d.glob("*.json"))
    if not snapshots:
        return []
    try:
        data = json.loads(snapshots[-1].read_bytes())
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for rec in data:
        wid = rec.get("water_id")
        if wid is None:
            continue
        out.append((int(wid), rec.get("water_code"), rec.get("water_name")))
    out.sort(key=lambda t: t[0])
    return out


def _bma_station_detail_load_cursor() -> int:
    if not BMA_STATION_DETAIL_CURSOR_PATH.exists():
        return 0
    try:
        return int(json.loads(BMA_STATION_DETAIL_CURSOR_PATH.read_text(encoding="utf-8")).get("next_index", 0))
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return 0


def _bma_station_detail_save_cursor(next_index: int) -> None:
    BMA_STATION_DETAIL_CURSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    BMA_STATION_DETAIL_CURSOR_PATH.write_text(
        json.dumps({"next_index": next_index, "saved_at_utc": _utcnow_iso()}, ensure_ascii=False),
        encoding="utf-8",
    )


def collect_bma_station_detail(conn, dry_run=False) -> CollectResult:
    """BMA water/StationDetail?id= -- see docs/knowledge/BMA_STATION_DETAIL_PROBE.md
    (probe, 2026-09-27) and sources/registry.yaml's bma_station_detail entry. Rotates a
    fixed BMA_STATION_DETAIL_BATCH_SIZE-station subset of the water_id space per run
    (persisted cursor at data/bma_station_detail_cursor.json, gitignored) -- ONE GET per
    station per run, no retry, same BMA-host rule as bma_watermap/bma_klongmap. Any
    single non-200 this run is skipped (not retried); a 403 anywhere in the batch stops
    the remaining ids in that batch immediately (host-block signal picked up by
    collect.py's run()/_looks_like_host_block via this result's http/note).

    Stores: (1) the admin-form threshold/geometry fields (water_control, warning,
    critical, warning_out01, critical_out01, left_bank, right_bank, bed_bank) as one
    observation row each, keyed by water_code, observed_at = this run's fetched_at (these
    are BMA's current admin-set values, not a historical telemetry reading -- there is no
    other timestamp BMA publishes for them), trust_tier official_telemetry, tag
    VERIFIED-BMA-control in provenance; (2) the inline 2-day 5-minute history baked into
    the page as `station_level_history_m` rows, one per (timestamp, value) point, keyed
    by water_code -- NOTE (documented, not fixed): per the probe, this raw point list can
    concatenate two runs (inner+outer canal) back to back; this collector stores the raw
    series as-is with `provenance.series_split = "unresolved"`, never silently splitting
    or guessing which half is which.
    """
    sid = "bma_station_detail"
    ids = _bma_station_detail_water_ids()
    if dry_run:
        return CollectResult(sid, True, note=(
            f"dry-run: would GET up to {BMA_STATION_DETAIL_BATCH_SIZE} of "
            f"{len(ids)} known water_id(s) from " + BMA_STATION_DETAIL_URL_TMPL))
    if not ids:
        return CollectResult(sid, False, note=(
            "no water_id list available -- run `collect.py --source bma_watermap` "
            "at least once first (this source rotates over its cached water_id space, "
            "never guesses an id range)"))
    start = _bma_station_detail_load_cursor() % len(ids)
    batch = [ids[(start + i) % len(ids)] for i in range(min(BMA_STATION_DETAIL_BATCH_SIZE, len(ids)))]
    headers = dict(GENERIC_HEADERS)
    headers.update({
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://weather.bangkok.go.th/water/",
    })
    import tools.harvest.bma_station_detail_draft as bsd

    n_thresholds = n_history = n_ok = 0
    controls_obtained = []
    host_blocked = False
    advanced = 0
    for water_id, watermap_water_code, watermap_water_name in batch:
        advanced += 1
        url = BMA_STATION_DETAIL_URL_TMPL.format(water_id=water_id)
        try:
            status, body = _one_get(url, headers)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                host_blocked = True
                break
            continue
        except (urllib.error.URLError, TimeoutError):
            continue
        if status != 200:
            continue
        html = body.decode("utf-8", errors="replace")
        _cache_raw(f"{sid}/id{water_id}", body, "html")
        fetched_at = _utcnow_iso()
        fields = bsd.parse_station_detail_fields(html)
        water_code = fields.get("txt_water_code") or watermap_water_code
        if not water_code:
            continue  # never key an observation by a fabricated code
        n_ok += 1
        for field_id, variable in _STATION_DETAIL_FIELD_TO_VARIABLE.items():
            raw = fields.get(field_id)
            if raw is None:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            n_thresholds += store.insert_observation(
                conn, source_id=sid, station_code=water_code,
                station_name=fields.get("txt_water_name") or watermap_water_name,
                variable=variable, value=value, unit="m",
                observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                provenance={"source_url": url, "water_id": water_id, "tag": "VERIFIED-BMA-control"},
            )
            if variable == "water_control_m":
                controls_obtained.append((water_code, value))
        for point in bsd.parse_history_series(html):
            n_history += store.insert_observation(
                conn, source_id=sid, station_code=water_code,
                station_name=fields.get("txt_water_name") or watermap_water_name,
                variable="station_level_history_m", value=point["value"], unit="m",
                observed_at_utc=point["timestamp_utc"], fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                provenance={"source_url": url, "water_id": water_id,
                            "series_split": "unresolved"},
            )
    _bma_station_detail_save_cursor((start + advanced) % len(ids))
    if host_blocked:
        return CollectResult(sid, False, http=403, note=(
            f"HTTP 403 on water_id={batch[advanced - 1][0]} -- stopped remaining batch "
            "immediately, per registry.yaml's DORMANT-on-403 handling; a human must "
            "re-check via `--source bma_station_detail` before this runs again"),
            counts={"stations_ok": n_ok, "thresholds": n_thresholds, "history_points": n_history})
    return CollectResult(
        sid, True, http=200,
        note=(f"{n_ok}/{len(batch)} station(s) fetched this run, {n_thresholds} threshold "
              f"reading(s), {n_history} history point(s); water_control obtained: "
              f"{controls_obtained}"),
        counts={"stations_ok": n_ok, "thresholds": n_thresholds, "history_points": n_history})


def collect_dds_nowcast_gif(conn, dry_run=False) -> CollectResult:
    sid = "dds_nowcast_gif"
    url = "https://dds.bangkok.go.th/Line_data/picture/radar_rain.gif"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url + " (snapshot only, no parse)")
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    p = _cache_raw(sid, body, "gif")
    return CollectResult(sid, True, http=200,
                          note=f"snapshot saved to {p} -- image only, not parsed")


# Same two area centres build_data.py uses (หมู่บ้านสัมมากร / ซอยรามคำแหง 53) -- duplicated
# here (not imported from build_data.py, which lives under site/ and is a script, not a
# package this file should import from) so this collector can request each area's own
# Open-Meteo forecast. Keep in sync with site/build_data.py's main() centres if they move.
OPENMETEO_AREA_CENTRES = {
    "sammakorn": (13.758235, 100.676084),
    "ram53": (13.765540, 100.619095),
}


def collect_openmeteo_forecast(conn, dry_run=False) -> CollectResult:
    """One GET per area per run (registry: max_requests_per_run applies per area-URL, not
    per source id) -- see sources/registry.yaml's openmeteo_forecast entry. A failure on
    one area's request does not stop the other area's request (independent hosts-safety
    posture: same domain, but this is not a BMA host under the strict single-request rule,
    and Open-Meteo has no documented rate limit this repo has hit)."""
    sid = "openmeteo_forecast"
    if dry_run:
        urls = ", ".join(parsers.openmeteo_forecast_url(lat, lon)
                          for lat, lon in OPENMETEO_AREA_CENTRES.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any = False
    n_obs = 0
    notes = []
    for area_id, (lat, lon) in OPENMETEO_AREA_CENTRES.items():
        url = parsers.openmeteo_forecast_url(lat, lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{area_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{area_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{_utcnow_stamp()}_{area_id}.json"
        p.write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_forecast(json.loads(body))
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            observed_at = local_dt.replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=area_id, station_name=area_id,
                lat=lat, lon=lon, variable="precipitation_forecast_mm", value=r["mm"],
                unit="mm", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="third_party", provenance={"source_url": url, "prob_pct": r["prob"]},
            )
        notes.append(f"{area_id}: {len(rows)} hourly row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_thaiwater_waterlevel(conn, dry_run=False) -> CollectResult:
    """Nationwide HII river/canal telemetry (804 stations, 2026-09-27 -- see
    docs/ASSETS.md's HII/RID probe log). Same one-GET/one-cache-raw shape as
    collect_thaiwater_flood_road."""
    sid = "thaiwater_waterlevel"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + parsers.THAIWATER_WATERLEVEL_URL)
    try:
        status, body = _one_get(parsers.THAIWATER_WATERLEVEL_URL, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_thaiwater_waterlevel(json.loads(body))
    n = 0
    for r in rows:
        if r.get("observed_at") is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r.get("station_oldcode") or r.get("station_id"),
            station_name=r.get("station_name_th"), lat=r["lat"], lon=r["lon"],
            variable="waterlevel_msl", value=r.get("waterlevel_msl"), unit="m",
            observed_at_utc=r["observed_at"], fetched_at_utc=fetched_at,
            trust_tier="official_telemetry",
            provenance={"source_url": r.get("source_url"), "agency": r.get("agency"),
                        "province_th": r.get("province_th"),
                        "storage_percent": r.get("storage_percent")},
        )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} nationwide station(s) fetched",
                          counts={"inserted": n})


def collect_hii_dam(conn, dry_run=False) -> CollectResult:
    """Nationwide HII dam/reservoir census (dam_hourly/dam_daily/dam_medium/
    dam_small_tele, ~989 records -- see docs/ASSETS.md). Join asset_id scheme:
    dam:hii_dam:<dam_id>."""
    sid = "hii_dam"
    url = "https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/dam"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_hii_dam(json.loads(body))
    n = 0
    for r in rows:
        if r.get("observed_at") is None or r.get("dam_id") is None:
            continue
        station_code = f"dam:hii_dam:{r['dam_id']}"
        base_provenance = {"agency_en": r.get("agency_en"), "province_th": r.get("province_th"),
                            "station_type": r["station_type"]}
        # One row per variable the payload actually has (never fabricate a missing
        # field) -- MUST-FIX #E: previously only storage_pct was a queryable
        # observation row, the rest lived only inside this same row's provenance blob.
        n += store.insert_observation(
            conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
            lat=r["lat"], lon=r["lon"], variable=f"{r['station_type']}_storage_pct",
            value=r.get("storage_pct"), unit="%", observed_at_utc=r["observed_at"],
            fetched_at_utc=fetched_at, trust_tier="official_telemetry",
            provenance=base_provenance,
        )
        if r.get("storage_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
                lat=r["lat"], lon=r["lon"], variable=f"{r['station_type']}_storage_mcm",
                value=r["storage_mcm"], unit="MCM", observed_at_utc=r["observed_at"],
                fetched_at_utc=fetched_at, trust_tier="official_telemetry",
                provenance=base_provenance,
            )
        if r.get("inflow_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
                lat=r["lat"], lon=r["lon"], variable=f"{r['station_type']}_inflow_mcm",
                value=r["inflow_mcm"], unit="MCM/day", observed_at_utc=r["observed_at"],
                fetched_at_utc=fetched_at, trust_tier="official_telemetry",
                provenance=base_provenance,
            )
        if r.get("release_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
                lat=r["lat"], lon=r["lon"], variable=f"{r['station_type']}_release_mcm",
                value=r["release_mcm"], unit="MCM/day", observed_at_utc=r["observed_at"],
                fetched_at_utc=fetched_at, trust_tier="official_telemetry",
                provenance=base_provenance,
            )
            if r.get("release_m3s_computed") is not None:
                n += store.insert_observation(
                    conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
                    lat=r["lat"], lon=r["lon"],
                    variable=f"{r['station_type']}_release_m3s_computed",
                    value=r["release_m3s_computed"], unit="m3/s", observed_at_utc=r["observed_at"],
                    fetched_at_utc=fetched_at, trust_tier="official_telemetry",
                    provenance={**base_provenance, "tag": "MEASURED-derived",
                                "formula": "release_mcm * 1e6 / 86400",
                                "source_release_mcm": r["release_mcm"]},
                )
        if r.get("spilled_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
                lat=r["lat"], lon=r["lon"], variable=f"{r['station_type']}_spilled_mcm",
                value=r["spilled_mcm"], unit="MCM/day", observed_at_utc=r["observed_at"],
                fetched_at_utc=fetched_at, trust_tier="official_telemetry",
                provenance=base_provenance,
            )
        if r.get("level_m") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r.get("name_th"),
                lat=r["lat"], lon=r["lon"], variable=f"{r['station_type']}_level_m",
                value=r["level_m"], unit="m", observed_at_utc=r["observed_at"],
                fetched_at_utc=fetched_at, trust_tier="official_telemetry",
                provenance=base_provenance,
            )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} dam/reservoir record(s) fetched",
                          counts={"inserted": n})


def collect_hii_watergate(conn, dry_run=False) -> CollectResult:
    """Nationwide HII watergate census (~2,315 records -- see docs/ASSETS.md). Join
    asset_id scheme: gate:hii_watergate:<station_id>."""
    sid = "hii_watergate"
    url = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/watergate_load"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_hii_watergate(json.loads(body))
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    n = 0
    n_stale = 0
    for r in rows:
        if r.get("observed_at") is None:
            continue
        # Never prune (AGENTS.md §2/§4) -- a row older than 7 days is still stored, just
        # flagged status='stale' so consumers (build_data.py etc.) can filter it out
        # without this collector silently dropping it.
        row_status = None
        try:
            observed_dt = datetime.datetime.fromisoformat(r["observed_at"])
            if (now_dt - observed_dt) > datetime.timedelta(days=7):
                row_status = "stale"
                n_stale += 1
        except (ValueError, TypeError):
            pass
        n += store.insert_observation(
            conn, source_id=sid, station_code=f"gate:hii_watergate:{r['station_id']}",
            station_name=r.get("name_th"), lat=r["lat"], lon=r["lon"],
            variable="watergate_upstream_level_m", value=r.get("level_upstream_m"),
            unit="m", observed_at_utc=r["observed_at"], fetched_at_utc=fetched_at,
            trust_tier="official_telemetry", status=row_status,
            provenance={"level_downstream_m": r.get("level_downstream_m"),
                        "gate_open": r.get("gate_open"), "pump_on": r.get("pump_on"),
                        "oldcode": r.get("oldcode"), "agency_en": r.get("agency_en"),
                        "province_th": r.get("province_th")},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} watergate record(s) fetched ({n_stale} stale, >7d)",
                          counts={"inserted": n, "stale": n_stale})


def collect_rid_res_table(conn, dry_run=False) -> CollectResult:
    """RID's 35-large-dam name list, by region -- no coordinate/numeric reading on the
    page (confirmed 2026-09-27, see docs/ASSETS.md). Stored as one document per fetch
    (a name-only list has no `variable`/`value` to attach as an observation), never
    fabricated coordinates or readings."""
    sid = "rid_res_table"
    url = "http://water.rid.go.th/flood/flood/res_table.htm"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "html")
    fetched_at = _utcnow_iso()
    html = body.decode("cp874", errors="replace")
    rows = parsers.parse_rid_res_table(html)
    n_docs = 0
    for r in rows:
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at,
            section="dam_name_by_region",
            text=f"{r['region_th']} | {r['dam_name_th']}")
        n_docs += 1
    return CollectResult(sid, True, http=200, note=f"{len(rows)} dam name(s) by region",
                          counts={"documents": n_docs})


def collect_egat_water_crisis(conn, dry_run=False) -> CollectResult:
    """EGAT dam water-crisis table (founder-supplied URL, water.egat.co.th/
    water_crisis.php) -- real per-dam storage/inflow/release table, no coordinate on
    this page (see parsers.parse_egat_water_crisis's module note)."""
    sid = "egat_water_crisis"
    url = "http://water.egat.co.th/water_crisis.php"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "html")
    fetched_at = _utcnow_iso()
    html = body.decode("utf-8", errors="replace")
    rows = parsers.parse_egat_water_crisis(html)
    n = 0
    for r in rows:
        # station_code keyed on name (no numeric id on this page) -- MUST-FIX #E also
        # fixes a latent collision: station_code=None for every dam meant the
        # (source_id, station_code, variable, observed_at_utc) unique index could only
        # ever keep ONE dam's row per run for a given variable+timestamp.
        station_code = f"dam:egat_water_crisis:{r['name_th']}"
        base_provenance = {k: v for k, v in r.items() if k not in ("name_th", "storage_pct")}
        n += store.insert_observation(
            conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
            variable="egat_dam_storage_pct", value=r.get("storage_pct"), unit="%",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            trust_tier="official_report", provenance=base_provenance,
        )
        if r.get("storage_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                variable="egat_dam_storage_mcm", value=r["storage_mcm"], unit="MCM",
                observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance=base_provenance,
            )
        if r.get("storage_level_m") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                variable="egat_dam_level_m", value=r["storage_level_m"], unit="m",
                observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance=base_provenance,
            )
        if r.get("inflow_today_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                variable="egat_dam_inflow_mcm", value=r["inflow_today_mcm"], unit="MCM/day",
                observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance=base_provenance,
            )
        if r.get("release_today_mcm") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                variable="egat_dam_release_mcm", value=r["release_today_mcm"], unit="MCM/day",
                observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance=base_provenance,
            )
            release_m3s = parsers._mcm_per_day_to_m3s(r["release_today_mcm"])
            if release_m3s is not None:
                n += store.insert_observation(
                    conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                    variable="egat_dam_release_m3s_computed", value=release_m3s, unit="m3/s",
                    observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                    trust_tier="official_report",
                    provenance={**base_provenance, "tag": "MEASURED-derived",
                                "formula": "release_today_mcm * 1e6 / 86400",
                                "source_release_mcm": r["release_today_mcm"]},
                )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} EGAT dam row(s) fetched",
                          counts={"inserted": n})


def _rid9_dateid_th(now_utc: "datetime.datetime | None" = None) -> str:
    """Today's date (Asia/Bangkok, UTC+7) as this page's own `dateid` param: Buddhist-era
    year + 2-digit month + 2-digit day, e.g. 2026-10-03 -> "25691003". Confirmed
    2026-10-03 (real GET) that `dateid` alone is sufficient -- the page's own `dm`/`dms`
    params only affect a display label, not which table rows come back."""
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    bkk = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
    return f"{bkk.year + 543}{bkk.month:02d}{bkk.day:02d}"


def _rid9_dateid_to_observed_at_utc(dateid: str) -> str:
    """The report's OWN date (from `dateid`, Buddhist-era) as a UTC ISO timestamp at
    Bangkok midnight -- never the fetch time. Fixed: this
    collector previously stamped `observed_at_utc=fetched_at`, which is wrong whenever
    the report is for a date other than "now" (e.g. re-run after Bangkok midnight but
    before the page's own date rolls, or a backfill run)."""
    be_year, mm, dd = int(dateid[:4]), int(dateid[4:6]), int(dateid[6:8])
    bkk_midnight = datetime.datetime(be_year - 543, mm, dd, 0, 0,
                                      tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
    return bkk_midnight.astimezone(datetime.timezone.utc).isoformat()


def _rid_report_date_to_observed_at_utc(date_str: "str | None") -> "str | None":
    """Same honesty fix as `_rid9_dateid_to_observed_at_utc`, for `api/dams`'s own
    Gregorian `DMD_Date`/`date` field (`"YYYY-MM-DD"`, Bangkok midnight) instead of a
    Buddhist-era dateid. Returns None (caller falls back to fetch time) on anything that
    doesn't parse -- never fabricates a date."""
    if not date_str:
        return None
    try:
        y, m, d = (int(p) for p in date_str.split("-"))
        bkk_midnight = datetime.datetime(y, m, d, 0, 0,
                                          tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
        return bkk_midnight.astimezone(datetime.timezone.utc).isoformat()
    except (ValueError, TypeError):
        return None


def collect_rid9_chonburi_rpt(conn, dry_run=False) -> CollectResult:
    """RID region-9 (สำนักงานชลประทานที่ 9, Chonburi) per-reservoir water-situation
    report -- real storage/rain/inflow/release table, Bang Pakong/eastern-seaboard basin
    (Chonburi, Rayong, Chachoengsao, Prachinburi), confirmed 2026-10-03 (real GET,
    `dateid`-only URL, see `_rid9_dateid_th`). No coordinate anywhere on this page --
    stored by name only (`station_code=f"dam:rid9_chonburi_rpt:{name_th}"`), same posture
    as `collect_egat_water_crisis`. This basin does not cover any area this repo currently
    serves (sammakorn/ram53/bangkok_east all sit in the Chao Phraya basin) -- see
    `AREA_RELEVANT_SOURCES` below, which is why a sammakorn/ram53 `--refresh` skips this
    source while `--all`/`--source rid9_chonburi_rpt` still fetch it."""
    sid = "rid9_chonburi_rpt"
    dateid = _rid9_dateid_th()
    url = f"http://irrigation.rid.go.th/rid9/rid9_new/rpt_show.php?dateid={dateid}"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "html")
    fetched_at = _utcnow_iso()
    observed_at = _rid9_dateid_to_observed_at_utc(dateid)
    html = body.decode("cp874", errors="replace")
    rows = parsers.parse_rid9_chonburi_rpt(html)
    n = 0
    _VARIABLE_UNIT = {
        "capacity_mcm": ("rid9_reservoir_capacity_mcm", "MCM"),
        "storage_current_mcm": ("rid9_reservoir_storage_mcm", "MCM"),
        "rain_daily_mm": ("rid9_reservoir_rain_daily_mm", "mm"),
        "inflow_current_daily_mcm": ("rid9_reservoir_inflow_daily_mcm", "MCM/day"),
        "release_total_mcm": ("rid9_reservoir_release_mcm", "MCM/day"),
    }
    for r in rows:
        station_code = f"dam:rid9_chonburi_rpt:{r['name_th']}"
        provenance = {"category_th": r.get("category_th"), "district_th": r.get("district_th"),
                      "province_th": r.get("province_th"), "seq": r.get("seq"),
                      "dateid": dateid}
        for field, (variable, unit) in _VARIABLE_UNIT.items():
            value = r.get(field)
            if value is None:
                continue
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                variable=variable, value=value, unit=unit,
                observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance=provenance,
            )
    # Honesty note: this report's cells are often only partly filled
    # in when fetched early in the day (Bangkok time) -- never fabricated, but worth
    # surfacing rather than silently returning a mostly-blank table as if it were full.
    blank_storage = sum(1 for r in rows if r.get("storage_current_mcm") is None)
    note = f"{len(rows)} RID region-9 reservoir row(s) fetched"
    if rows and blank_storage > len(rows) // 2:
        note += f" ({blank_storage}/{len(rows)} storage cells blank -- partial_report)"
    return CollectResult(sid, True, http=200, note=note, counts={"inserted": n})


def collect_rid_app_reservoir(conn, dry_run=False) -> CollectResult:
    """RID's own reservoir web-app (`app.rid.go.th/reservoir`) -- `api/dams` (one POST,
    today's date, returns every large dam with coordinates, including the Chao
    Phraya-basin feeder dams เขื่อนภูมิพล/เขื่อนสิริกิติ์/เขื่อนป่าสักชลสิทธิ์) plus `api/alert`
    (one GET, a reservoir-warning feed). Added 2026-10-03 as the highest-value unwired
    RID source identified by the census sweep. This source field-overlaps
    `hii_dam` (see parsers.parse_rid_app_reservoir's module comment) -- kept as an
    independent official cross-check, never silently merged into hii_dam's rows."""
    sid = "rid_app_reservoir"
    bkk = datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=7)))
    date_str = bkk.strftime("%Y-%m-%d")
    dams_url = "https://app.rid.go.th/reservoir/api/dams"
    alert_url = "https://app.rid.go.th/reservoir/api/alert"
    if dry_run:
        return CollectResult(sid, True, note=f"dry-run: would POST {dams_url} "
                                              f"(date={date_str}), then GET {alert_url}")
    import json
    body = json.dumps({"date": date_str}).encode("utf-8")
    post_headers = {**GENERIC_HEADERS, "Content-Type": "application/json"}
    try:
        status, resp_body = _one_post(dams_url, post_headers, body)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error (api/dams): {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status} (api/dams)")
    _cache_raw(sid, resp_body, "json")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_rid_app_reservoir(json.loads(resp_body))
    n = 0
    _VARIABLE_UNIT = {
        "capacity_mcm": ("rid_dam_capacity_mcm", "MCM"),
        "storage_current_mcm": ("rid_dam_storage_mcm", "MCM"),
        # denominator is storage_norm_mcm (DAM_QStore), confirmed by recomputing
        # PERCENT_DMD_QUse against each DAM_Q* field on the real capture (MEASURED
        # 2026-10-03): DMD_QUse / DAM_QStore * 100 matches the reported percent for
        # every dam checked; DAM_QMax does not.
        "storage_pct": ("rid_dam_storage_pct_of_norm", "%"),
        "inflow_daily_mcm": ("rid_dam_inflow_daily_mcm", "MCM/day"),
        "release_daily_mcm": ("rid_dam_release_daily_mcm", "MCM/day"),
    }
    for r in rows:
        if r.get("dam_id") is None or r.get("name_th") is None:
            continue
        station_code = f"dam:rid_app_reservoir:{r['dam_id']}"
        has_coord = parsers._valid_th_coord(r.get("lat"), r.get("lon"))
        lat = float(r["lat"]) if has_coord else None
        lon = float(r["lon"]) if has_coord else None
        observed_at = _rid_report_date_to_observed_at_utc(r.get("date")) or fetched_at
        base_provenance = {"region_th": r.get("region_th"), "report_date": r.get("date")}
        for field, (variable, unit) in _VARIABLE_UNIT.items():
            value = r.get(field)
            if value is None:
                continue
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code, station_name=r["name_th"],
                lat=lat, lon=lon, variable=variable, value=value, unit=unit,
                observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="official_report", provenance=base_provenance,
            )
    note = f"{len(rows)} RID reservoir-app dam row(s) fetched"
    # api/alert: one GET, best-effort -- a failure here does not fail the whole
    # collector (the dam data above is the primary payload), but is never silently
    # swallowed either.
    try:
        a_status, a_body = _one_get(alert_url, GENERIC_HEADERS)
        if a_status == 200:
            alerts = parsers.parse_rid_app_alert(json.loads(a_body))
            if alerts:
                n += store.insert_observation(
                    conn, source_id=sid, station_code="rid_app_reservoir:alert_feed",
                    station_name="RID reservoir-app alert feed",
                    variable="rid_dam_alert_count", value=float(len(alerts)), unit="count",
                    observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
                    trust_tier="official_report",
                    provenance={"alerts": alerts},
                )
                note += f"; {len(alerts)} active alert(s)"
            else:
                note += "; api/alert: 0 active alerts at capture time (never means no " \
                        "alerting -- an empty feed, not a failed fetch)"
        else:
            note += f"; api/alert: HTTP {a_status} (not fatal to this collector)"
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        note += f"; api/alert: network/HTTP error: {e} (not fatal to this collector)"
    return CollectResult(sid, True, http=200, note=note, counts={"inserted": n})


# Same upstream/Sammakorn area points build_data.py's water-balance chain already reads
# (C.2 นครสวรรค์, เขื่อนเจ้าพระยา) plus Sammakorn itself -- see
# site/inputs/areas/*.balance.yaml for the same coordinates used elsewhere in this repo.
OPENMETEO_FLOOD_POINTS = {
    "nakhonsawan": (15.7047, 100.1372),
    "chaophraya_dam": (15.1897, 100.1608),
    "sammakorn": (13.758235, 100.676084),
    # Added 2026-09-27 per docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_
    # 2026-09-27.md #2 -- GloFAS at an upstream point (Bang Sai / Pathum Thani), a
    # secondary/cross-check Q_up source alongside hii_waterlevel_load (never a
    # substitute for it -- model vs gauge, per units_datum_crosswalk.yaml's
    # grid_cell_vs_gauge_not_equal rule).
    "bang_sai": (14.35, 100.55),
}
OPENMETEO_ENSEMBLE_POINTS = {
    "sammakorn": (13.758235, 100.676084),
    "nakhonsawan": (15.7047, 100.1372),
}
# Gulf of Thailand bar near the Chao Phraya river mouth (Bangkok's tidal boundary) --
# nearest Open-Meteo marine grid point to the actual river-mouth bar.
OPENMETEO_MARINE_POINT = (13.458336, 100.625015)

# Same 3 named points FORECAST7D_POINTS already uses for sammakorn/ram53/bangkok_east
# (see that dict's own comment for provenance of each coordinate) -- reused here, not
# re-derived, for soil-moisture/antecedent-precip (added 2026-09-27 per
# docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #4/#5).
SOIL_MOISTURE_POINTS = {
    "sammakorn": (13.758235, 100.676084),
    "ram53": (13.765540125000635, 100.61909460837903),
    "bangkok_east": (13.7734, 100.6813),
}
ARCHIVE_PRECIP_POINTS = dict(SOIL_MOISTURE_POINTS)


def collect_openmeteo_flood(conn, dry_run=False) -> CollectResult:
    """Open-Meteo Flood API (GloFAS daily river discharge, m3/s) for the upstream
    Chao Phraya chain points + Sammakorn. One GET per point per run."""
    sid = "openmeteo_flood"
    if dry_run:
        urls = ", ".join(parsers.openmeteo_flood_url(lat, lon)
                          for lat, lon in OPENMETEO_FLOOD_POINTS.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in OPENMETEO_FLOOD_POINTS.items():
        url = parsers.openmeteo_flood_url(lat, lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_flood(json.loads(body))
        for r in rows:
            observed_at = (datetime.datetime.combine(
                datetime.date.fromisoformat(r["date"]), datetime.time(0, 0),
                tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                .astimezone(datetime.timezone.utc).isoformat())
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=point_id, station_name=point_id,
                lat=lat, lon=lon, variable="glofas_river_discharge_m3s",
                value=r["discharge_m3s"], unit="m3/s", observed_at_utc=observed_at,
                fetched_at_utc=fetched_at, trust_tier="third_party",
                provenance={"source_url": url},
            )
        notes.append(f"{point_id}: {len(rows)} daily row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_openmeteo_ensemble(conn, dry_run=False) -> CollectResult:
    """Open-Meteo Ensemble API (multi-member hourly rain) for Sammakorn + one upstream
    point. One GET per point per run."""
    sid = "openmeteo_ensemble"
    if dry_run:
        urls = ", ".join(parsers.openmeteo_ensemble_url(lat, lon)
                          for lat, lon in OPENMETEO_ENSEMBLE_POINTS.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in OPENMETEO_ENSEMBLE_POINTS.items():
        url = parsers.openmeteo_ensemble_url(lat, lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_ensemble(json.loads(body))
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            observed_at = local_dt.replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=point_id, station_name=point_id,
                lat=lat, lon=lon, variable="precipitation_ensemble_median_mm",
                value=r["median_mm"], unit="mm", observed_at_utc=observed_at,
                fetched_at_utc=fetched_at, trust_tier="third_party",
                provenance={"source_url": url, "min_mm": r["min_mm"], "max_mm": r["max_mm"],
                            "n_members": r["n_members"]},
            )
        notes.append(f"{point_id}: {len(rows)} hourly row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_openmeteo_marine(conn, dry_run=False) -> CollectResult:
    """Open-Meteo Marine API (hourly sea-level height, m) near the Gulf of Thailand bar
    off Bangkok. One GET per run."""
    sid = "openmeteo_marine"
    lat, lon = OPENMETEO_MARINE_POINT
    url = parsers.openmeteo_marine_url(lat, lon)
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_openmeteo_marine(json.loads(body))
    n = 0
    for r in rows:
        try:
            local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
        except ValueError:
            continue
        observed_at = local_dt.replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=7))
        ).astimezone(datetime.timezone.utc).isoformat()
        n += store.insert_observation(
            conn, source_id=sid, station_code="gulf_of_thailand_bar",
            station_name="gulf_of_thailand_bar", lat=lat, lon=lon,
            variable="sea_level_height_msl_m", value=r["sea_level_m"], unit="m",
            observed_at_utc=observed_at, fetched_at_utc=fetched_at, trust_tier="third_party",
            provenance={"source_url": url},
        )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} hourly row(s) fetched",
                          counts={"inserted": n})


def collect_hii_waterlevel_load(conn, dry_run=False) -> CollectResult:
    """HII `public/waterlevel_load` -- richer per-station shape than
    thaiwater_waterlevel, including discharge (cms). Promoted from
    tools/harvest/hii_waterchart_draft.py per docs/knowledge/
    EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #1 (2026-09-27) -- this
    repo's first real gauge-based Q_up (upstream inflow) source for PROP-FLOOD-03's
    Q_in(k). ONE GET per run (all basin_ids in one comma-separated request, same shape
    as the site itself uses). Stores discharge as variable `discharge` (m3/s) and
    waterlevel_msl/critical_level_msl alongside it -- never merged/deduped against the
    already-wired thaiwater_waterlevel rows (same station may appear in both; join/dedup
    decision explicitly left OPEN per the draft module's own promotion-path note)."""
    sid = "hii_waterlevel_load"
    today = datetime.datetime.now(datetime.timezone.utc).astimezone(
        datetime.timezone(datetime.timedelta(hours=7))).date()
    start_date = f"{today.isoformat()} 00:00"
    end_date = f"{today.isoformat()} 23:59"
    url = parsers.hii_waterlevel_load_url(
        parsers.HII_WATERLEVEL_LOAD_BASIN_IDS_OBSERVED, start_date, end_date)
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_hii_waterlevel_load(json.loads(body))
    n = 0
    for r in rows:
        if r.get("observed_at") is None:
            continue
        # HII's own datetime string is "YYYY-MM-DD HH:MM" ICT (+07:00), same convention
        # as every other thaiwater.net collector in this file (see
        # collect_thaiwater_canal_waterlevel).
        try:
            local_dt = datetime.datetime.strptime(r["observed_at"], "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        observed_at = local_dt.replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=7))
        ).astimezone(datetime.timezone.utc).isoformat()
        station_code = r.get("station_code") or f"hii_waterlevel_load:{r.get('station_id')}"
        base_provenance = {
            "source_url": url, "basin_id": r.get("basin_id"), "basin_code": r.get("basin_code"),
            "basin_name_th": r.get("basin_name_th"), "river_name": r.get("river_name"),
            "agency_shortname_en": r.get("agency_shortname_en"),
            "is_key_station": r.get("is_key_station"), "left_bank": r.get("left_bank"),
            "right_bank": r.get("right_bank"), "min_bank": r.get("min_bank"),
            "ground_level": r.get("ground_level"),
        }
        if r.get("discharge_cms") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code,
                station_name=r.get("station_name_th"), lat=r.get("lat"), lon=r.get("lon"),
                variable="discharge", value=r["discharge_cms"], unit="m3/s",
                observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                warning=r.get("warning_level_m"), critical=r.get("critical_level_m"),
                provenance=base_provenance,
            )
        if r.get("waterlevel_msl") is not None:
            n += store.insert_observation(
                conn, source_id=sid, station_code=station_code,
                station_name=r.get("station_name_th"), lat=r.get("lat"), lon=r.get("lon"),
                variable="waterlevel_msl", value=r["waterlevel_msl"], unit="m",
                observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="official_telemetry",
                critical=r.get("critical_level_msl"),
                provenance=base_provenance,
            )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} station-timestep row(s) fetched",
                          counts={"inserted": n})


def collect_openmeteo_soil_moisture(conn, dry_run=False) -> CollectResult:
    """Open-Meteo hourly soil-moisture (3 depth layers, m3/m3) at sammakorn/ram53/
    bangkok_east -- antecedent-wetness / S_0 proxy for PROP-FLOOD-03 (founder ask,
    2026-09-27, docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #4).
    One GET per point per run. Model grid-cell estimate, not a physical sensor -- every
    row's provenance carries `tag: forecast-inferred` per units_datum_crosswalk.yaml's
    grid_cell_vs_gauge_not_equal rule."""
    sid = "openmeteo_soil_moisture"
    if dry_run:
        urls = ", ".join(parsers.openmeteo_soil_moisture_url(lat, lon)
                          for lat, lon in SOIL_MOISTURE_POINTS.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in SOIL_MOISTURE_POINTS.items():
        url = parsers.openmeteo_soil_moisture_url(lat, lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_soil_moisture(json.loads(body))
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            observed_at = local_dt.replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
            for field, var in (("soil_moisture_0_to_1cm", "soil_moisture_0_1cm"),
                                ("soil_moisture_1_to_3cm", "soil_moisture_1_3cm"),
                                ("soil_moisture_3_to_9cm", "soil_moisture_3_9cm")):
                if r.get(field) is None:
                    continue
                n_obs += store.insert_observation(
                    conn, source_id=sid, station_code=point_id, station_name=point_id,
                    lat=lat, lon=lon, variable=var, value=r[field], unit="m3/m3",
                    observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                    trust_tier="third_party",
                    provenance={"source_url": url, "tag": "forecast-inferred",
                                "note": "MEASURED-model, grid-cell estimate not a physical sensor"},
                )
        notes.append(f"{point_id}: {len(rows)} hourly row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_openmeteo_archive_precip(conn, dry_run=False) -> CollectResult:
    """Open-Meteo Archive API (ERA5), daily precipitation_sum, 30-day trailing window,
    at sammakorn/ram53/bangkok_east -- secondary antecedent-wetness/antecedent-
    precipitation proxy alongside openmeteo_soil_moisture (founder ask, 2026-09-27,
    docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_INPUTS_2026-09-27.md #5). One GET
    per point per run. Day-boundary caveat: Open-Meteo's own local-midnight day, not a
    UTC calendar day -- same as this file's other daily Open-Meteo collectors."""
    sid = "openmeteo_archive_precip"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    start = (today - datetime.timedelta(days=30)).isoformat()
    end = (today - datetime.timedelta(days=1)).isoformat()
    if dry_run:
        urls = ", ".join(parsers.openmeteo_archive_precip_url(lat, lon, start, end)
                          for lat, lon in ARCHIVE_PRECIP_POINTS.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in ARCHIVE_PRECIP_POINTS.items():
        url = parsers.openmeteo_archive_precip_url(lat, lon, start, end)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_archive_precip(json.loads(body))
        for r in rows:
            observed_at = _forecast_row_observed_at_utc(r["date"]) if False else (
                datetime.datetime.combine(
                    datetime.date.fromisoformat(r["date"]), datetime.time(0, 0),
                    tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
                .astimezone(datetime.timezone.utc).isoformat())
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=point_id, station_name=point_id,
                lat=lat, lon=lon, variable="precipitation_sum_daily_mm",
                value=r["precipitation_sum_mm"], unit="mm", observed_at_utc=observed_at,
                fetched_at_utc=fetched_at, trust_tier="third_party",
                provenance={"source_url": url, "tag": "MEASURED-model",
                            "window": "day_boundary_mismatch applies -- see "
                                      "units_datum_crosswalk.yaml"},
            )
        notes.append(f"{point_id}: {len(rows)} daily row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_gdacs_events(conn, dry_run=False) -> CollectResult:
    """GDACS country-level flood event trip-wire (global disaster alert system), client-
    side filtered to Thailand -- see docs/knowledge/EASIEST_EXTERNAL_APIS_FOR_MISSING_
    INPUTS_2026-09-27.md #8. One GET per run. Country-level granularity only -- a trip-
    wire signal for PROP-FLOOD-08's D_critical calibration, never a per-tambon reading."""
    sid = "gdacs_events"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    fromdate = (today - datetime.timedelta(days=365 * 6)).isoformat()
    todate = today.isoformat()
    url = parsers.gdacs_event_list_url(fromdate, todate)
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    events = parsers.parse_gdacs_events_thailand(json.loads(body))
    n = 0
    for e in events:
        if not e.get("from_date"):
            continue
        try:
            observed_at = datetime.datetime.fromisoformat(
                e["from_date"].replace("Z", "+00:00"))
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=datetime.timezone.utc)
            observed_at = observed_at.astimezone(datetime.timezone.utc).isoformat()
        except ValueError:
            continue
        station_code = f"gdacs:{e.get('event_id')}"
        n += store.insert_observation(
            conn, source_id=sid, station_code=station_code, station_name=e.get("name"),
            lat=e.get("lat"), lon=e.get("lon"), variable="flood_event_tripwire",
            value=1, unit="event", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
            trust_tier="third_party",
            provenance={"source_url": url, "to_date": e.get("to_date"),
                        "alert_level": e.get("alert_level"),
                        "note": "country-level trip-wire only, not per-tambon"},
        )
    return CollectResult(sid, True, http=200, note=f"{len(events)} Thailand flood event(s) found",
                          counts={"inserted": n})


def collect_nasa_power(conn, dry_run=False) -> CollectResult:
    """NASA POWER daily bias-corrected rain (PRECTOTCORR, mm/day) for Sammakorn. One
    GET per run, 7-day trailing window (matches this repo's existing raw/live/nasa_power
    sample)."""
    sid = "nasa_power"
    lat, lon = 13.758235, 100.676084
    today = datetime.datetime.now(datetime.timezone.utc).date()
    start = (today - datetime.timedelta(days=7)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    url = parsers.nasa_power_url(lat, lon, start, end)
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_nasa_power_daily_rain(json.loads(body))
    n = 0
    for r in rows:
        observed_at = (datetime.datetime.combine(
            datetime.date.fromisoformat(r["date"]), datetime.time(0, 0),
            tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
            .astimezone(datetime.timezone.utc).isoformat())
        n += store.insert_observation(
            conn, source_id=sid, station_code="sammakorn", station_name="sammakorn",
            lat=lat, lon=lon, variable="rain_24h_mm", value=r["rain_mm"], unit="mm",
            observed_at_utc=observed_at, fetched_at_utc=fetched_at, trust_tier="third_party",
            provenance={"source_url": url},
        )
    return CollectResult(sid, True, http=200, note=f"{len(rows)} daily row(s) fetched",
                          counts={"inserted": n})


# The 6 open forecast models site/build_data.py's load_multimodel_hourly() already reads
# from raw/forecast/openmeteo_<model>.json -- see site/FORECAST_SPEC.md. This collector is
# the registry-driven replacement for the manual one-off files created 2026-09-26 (absent
# on CI); it writes the SAME raw/forecast/openmeteo_<model>.json paths build_data.py
# already looks for, plus the usual raw/live archive + observations rows (tagged RELAYED,
# one row per model per run, station_code=model name) so a re-run's provenance is
# traceable the same way every other source in this registry is.
OPENMETEO_MULTIMODEL_MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless",
                                "jma_seamless", "gem_seamless", "meteofrance_seamless"]
OPENMETEO_MULTIMODEL_POINT = (13.758235, 100.676084)  # Sammakorn -- see build_data.py note
OPENMETEO_MULTIMODEL_URL_TMPL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&hourly=precipitation&models={model}&timezone=Asia%2FBangkok&forecast_days=7"
)
FORECAST_DIR = HERE / "raw" / "forecast"


def collect_openmeteo_multimodel(conn, dry_run=False) -> CollectResult:
    """One GET per model per run (6 models = 6 requests total, same per-URL-not-per-
    source-id host_rule posture as collect_openmeteo_forecast's 2-area shape). Writes
    raw/forecast/openmeteo_<model>.json (consumed by site/build_data.py's
    load_multimodel_hourly()) in addition to the usual raw/live archive."""
    sid = "openmeteo_multimodel"
    lat, lon = OPENMETEO_MULTIMODEL_POINT
    if dry_run:
        urls = ", ".join(OPENMETEO_MULTIMODEL_URL_TMPL.format(lat=lat, lon=lon, model=m)
                          for m in OPENMETEO_MULTIMODEL_MODELS)
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for model in OPENMETEO_MULTIMODEL_MODELS:
        url = OPENMETEO_MULTIMODEL_URL_TMPL.format(lat=lat, lon=lon, model=model)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{model}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{model}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{model}.json").write_bytes(body)
        FORECAST_DIR.mkdir(parents=True, exist_ok=True)
        (FORECAST_DIR / f"openmeteo_{model}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_forecast(json.loads(body))
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            observed_at = local_dt.replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=model, station_name=model,
                lat=lat, lon=lon, variable="precipitation_forecast_mm", value=r["mm"],
                unit="mm", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="third_party", provenance={"source_url": url, "model": model},
            )
        notes.append(f"{model}: {len(rows)} hourly row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


# ---------------------------------------------------------------------------------------
# 7-16 day forecast wave (2026-09-27, founder ask: "มี api free แบบ windy ไหมที่เราเชื่อมได้"
# -> "เอาเลย ... ล่วงหน้า 7 วันขึ้นไป ... ถ้าใช้ API เดียวไม่ได้ก็มาสอง API" -> "ตอบเป็นช่วงไปเลยก็ได้").
# Census + parser design already done in docs/knowledge/FORECAST_7DAY_SOURCES.md /
# sources/api_census_forecast7d.yaml / tools/harvest/forecast7d_draft.py -- this section
# is the registry-driven wiring (one point set, shared by all 4 collectors below, so
# every area this repo tracks gets the SAME per-model rows -- see site/build_data.py's
# _layer0_forecast_24h_range/_layer0_forecast_7day_range which key off `station_code`
# f"{point_id}:{model}"). Points, per founder brief:
#   - sammakorn: the existing Sammakorn gauge point (this repo's long-standing proxy).
#   - ram53: soi midpoint (site/inputs/ram53/ram53_area.json's own `lat`/`lon` --
#     "midpoint by along-line length" of the 3 combined OSM ways).
#   - bangkok_east: the raw/backtest/units.yaml BANGKOK_EAST unit centroid (13.7734,
#     100.6813) -- DELIBERATELY NOT the Sammakorn point, even though the two are close --
#     this is the area-level centroid used by the backtest unit graph, stated here so a
#     future reader never assumes it's a duplicate of the sammakorn row.
#   - c2_nakhonsawan / c13_chaophraya_dam: sources/capacity_ledger.yaml's AS_GAUGE_C2/
#     AS_DAM_C13 rows carry no lat/lon (province/district only) -- coordinates here are
#     the founder brief's own figures (15.70,100.14 / 15.15,100.18), not from the registry.
#   - hatyai/nan/chiangmai: raw/backtest/units.yaml HATYAI/NAN/CHIANGMAI `centre` fields.
FORECAST7D_POINTS = {
    "sammakorn": (13.758235, 100.676084),
    "ram53": (13.765540125000635, 100.61909460837903),
    "bangkok_east": (13.7734, 100.6813),
    "c2_nakhonsawan": (15.70, 100.14),
    "c13_chaophraya_dam": (15.15, 100.18),
    "hatyai": (7.0084, 100.4747),
    "nan": (18.7756, 100.7730),
    "chiangmai": (18.7883, 98.9853),
}

FORECAST16D_MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "jma_seamless",
                       "gem_seamless", "meteofrance_seamless", "ukmo_seamless",
                       "knmi_seamless", "cma_grapes_global"]
FORECAST16D_URL_TMPL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&daily=precipitation_sum&forecast_days=16&models=" + ",".join(FORECAST16D_MODELS)
    + "&timezone=Asia%2FBangkok"
)
ENSEMBLE_DAILY_URL_TMPL = (
    "https://ensemble-api.open-meteo.com/v1/ensemble?latitude={lat}&longitude={lon}"
    "&daily=precipitation_sum&forecast_days=16&models=gfs_seamless&timezone=Asia%2FBangkok"
)
METNO_URL_TMPL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
# MET Norway's ToS requires a real, identifying User-Agent (not a key -- a courtesy rule);
# never a personal name, per this repo's own no-personal-names law -- a project-level
# contact string only.
METNO_HEADERS = {"User-Agent": "floodconnect/0.1 (+https://github.com/morrocwi/floodconnect)"}
PREVIOUS_RUNS_URL_TMPL = (
    "https://previous-runs-api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&hourly=precipitation,precipitation_previous_day1,precipitation_previous_day3"
    "&past_days=5&forecast_days=1&models=gfs_seamless"
)


def _forecast_row_observed_at_utc(target_date: str) -> str:
    """A daily forecast row's `target_date` (an ISO date, no time) -> the UTC instant for
    Bangkok midnight that day, same convention as this file's other daily collectors
    (e.g. collect_nasa_power)."""
    return (datetime.datetime.combine(
        datetime.date.fromisoformat(target_date), datetime.time(0, 0),
        tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
        .astimezone(datetime.timezone.utc).isoformat())


def collect_openmeteo_forecast16d(conn, dry_run=False, points=None) -> CollectResult:
    """One GET per point (8 points = 8 requests total), each returning ALL 9 named
    deterministic models in one response (`models=` list, not `best_match`) -- see
    FORECAST16D_MODELS. Writes raw/live archive + one observations row per (point, model,
    day) via the shared `parse_openmeteo_multimodel_daily()` parser (never fabricates a
    row for a model whose own horizon has already ended -- `precip_mm=None` days are
    skipped, not stored as 0mm)."""
    sid = "openmeteo_forecast16d"
    pts = points if points is not None else FORECAST7D_POINTS
    if dry_run:
        urls = ", ".join(FORECAST16D_URL_TMPL.format(lat=lat, lon=lon)
                          for lat, lon in pts.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in pts.items():
        url = FORECAST16D_URL_TMPL.format(lat=lat, lon=lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        rows = parse_openmeteo_multimodel_daily(json.loads(body), run_time=fetched_at)
        n_this_point = 0
        for r in rows:
            if r["precip_mm"] is None:
                continue
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=f"{point_id}:{r['model']}",
                station_name=f"{point_id}:{r['model']}", lat=lat, lon=lon,
                variable="precipitation_forecast_daily_mm", value=r["precip_mm"], unit="mm",
                observed_at_utc=_forecast_row_observed_at_utc(r["target_date"]),
                fetched_at_utc=fetched_at, trust_tier="third_party",
                provenance={"source_url": url, "model": r["model"],
                            "horizon_day": r["horizon_day"], "tag": r["tag"]},
            )
            n_this_point += 1
        notes.append(f"{point_id}: {n_this_point} row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_openmeteo_ensemble_daily(conn, dry_run=False, points=None) -> CollectResult:
    """One GET per point (8 requests total), each returning the real 31-member GFS-ENS
    daily precipitation_sum -- a genuinely different signal from the deterministic
    multi-model spread above (spread of MEMBERS within one model, not across models).
    Stores every member row PLUS the shared parser's own derived median/p10/p90 summary
    rows (tagged MEASURED, computed by this parser, never VERIFIED)."""
    sid = "openmeteo_ensemble_daily"
    pts = points if points is not None else FORECAST7D_POINTS
    if dry_run:
        urls = ", ".join(ENSEMBLE_DAILY_URL_TMPL.format(lat=lat, lon=lon)
                          for lat, lon in pts.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in pts.items():
        url = ENSEMBLE_DAILY_URL_TMPL.format(lat=lat, lon=lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        rows = parse_openmeteo_ensemble_members(json.loads(body), run_time=fetched_at)
        n_this_point = 0
        for r in rows:
            if r["precip_mm"] is None:
                continue
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=f"{point_id}:{r['model']}",
                station_name=f"{point_id}:{r['model']}", lat=lat, lon=lon,
                variable="precipitation_forecast_ensemble_daily_mm", value=r["precip_mm"],
                unit="mm", observed_at_utc=_forecast_row_observed_at_utc(r["target_date"]),
                fetched_at_utc=fetched_at, trust_tier="third_party",
                provenance={"source_url": url, "model": r["model"],
                            "horizon_day": r["horizon_day"], "tag": r["tag"]},
            )
            n_this_point += 1
        notes.append(f"{point_id}: {n_this_point} row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_metno_locationforecast(conn, dry_run=False, points=None) -> CollectResult:
    """One GET per point (8 requests total) against MET Norway's Locationforecast/2.0
    compact endpoint -- a third independent pipeline (not Open-Meteo at all), ~9.75-day
    horizon, requires an identifying User-Agent per MET Norway's ToS (see METNO_HEADERS,
    a project-level string, never a personal name)."""
    sid = "metno_locationforecast"
    pts = points if points is not None else FORECAST7D_POINTS
    if dry_run:
        urls = ", ".join(METNO_URL_TMPL.format(lat=lat, lon=lon)
                          for lat, lon in pts.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in pts.items():
        url = METNO_URL_TMPL.format(lat=lat, lon=lon)
        try:
            status, body = _one_get(url, METNO_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        rows = parse_metno_locationforecast_daily(json.loads(body), run_time=fetched_at)
        n_this_point = 0
        for r in rows:
            if r["precip_mm"] is None:
                continue
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=f"{point_id}:metno",
                station_name=f"{point_id}:metno", lat=lat, lon=lon,
                variable="precipitation_forecast_daily_mm", value=r["precip_mm"], unit="mm",
                observed_at_utc=_forecast_row_observed_at_utc(r["target_date"]),
                fetched_at_utc=fetched_at, trust_tier="third_party",
                provenance={"source_url": url, "model": "metno_locationforecast",
                            "horizon_day": r["horizon_day"], "tag": r["tag"]},
            )
            n_this_point += 1
        notes.append(f"{point_id}: {n_this_point} row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_openmeteo_previous_runs(conn, dry_run=False) -> CollectResult:
    """Sammakorn point ONLY (per founder brief) -- one GET, forecast skill-checking:
    GFS's own current-best-estimate for a past day vs. what GFS itself forecast 1/3 days
    before that day (model-vs-itself, NOT vs. an independent gauge -- see
    docs/knowledge/FORECAST_7DAY_SOURCES.md ss4 caveat, carried into each row's
    `MEASURED-vs-forecast` tag)."""
    sid = "openmeteo_previous_runs"
    lat, lon = FORECAST7D_POINTS["sammakorn"]
    url = PREVIOUS_RUNS_URL_TMPL.format(lat=lat, lon=lon)
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    rows = parse_openmeteo_previous_runs_skillcheck(json.loads(body), run_time=fetched_at)
    n = 0
    for r in rows:
        if r["precip_mm"] is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=f"sammakorn:{r['model']}",
            station_name=f"sammakorn:{r['model']}", lat=lat, lon=lon,
            variable="precipitation_skillcheck_daily_mm", value=r["precip_mm"], unit="mm",
            observed_at_utc=_forecast_row_observed_at_utc(r["target_date"]),
            fetched_at_utc=fetched_at, trust_tier="third_party",
            provenance={"source_url": url, "model": r["model"], "tag": r["tag"]},
        )
    return CollectResult(sid, True, http=200, note=f"{n} row(s) fetched",
                          counts={"inserted": n})


def _last_fetch_age_hours(sid: str) -> "Optional[float]":
    """Newest file mtime under raw/live/<sid>/, in hours before now -- None if the
    directory doesn't exist or is empty (never fetched). Used to throttle slow indices
    (ONI/pressure not this one, but oni specifically) to at most once/24h without a
    network round-trip just to find out."""
    d = RAW_LIVE_DIR / sid
    if not d.is_dir():
        return None
    files = list(d.glob("*"))
    if not files:
        return None
    newest = max(f.stat().st_mtime for f in files)
    age_s = datetime.datetime.now(datetime.timezone.utc).timestamp() - newest
    return age_s / 3600.0


def collect_openmeteo_pressure(conn, dry_run=False) -> CollectResult:
    """Open-Meteo hourly mean-sea-level pressure, per model (same 9-model list as
    openmeteo_forecast16d), past_days=7 + forecast_days=16, at sammakorn/ram53/
    bangkok_east. Founder addition 2026-09-27 ("เอาเลย") -- storm-track/pressure context,
    data only, no danger threshold derived here. One GET per point per run (3 points)."""
    sid = "openmeteo_pressure"
    if dry_run:
        urls = ", ".join(parsers.openmeteo_pressure_url(lat, lon)
                          for lat, lon in SOIL_MOISTURE_POINTS.values())
        return CollectResult(sid, True, note="dry-run: would GET " + urls)
    ok_any, n_obs, notes = False, 0, []
    for point_id, (lat, lon) in SOIL_MOISTURE_POINTS.items():
        url = parsers.openmeteo_pressure_url(lat, lon)
        try:
            status, body = _one_get(url, GENERIC_HEADERS)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            notes.append(f"{point_id}: network/HTTP error: {e}")
            continue
        if status != 200:
            notes.append(f"{point_id}: HTTP {status}")
            continue
        d = RAW_LIVE_DIR / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{_utcnow_stamp()}_{point_id}.json").write_bytes(body)
        ok_any = True
        fetched_at = _utcnow_iso()
        import json
        rows = parsers.parse_openmeteo_pressure_multimodel(json.loads(body))
        n_this_point = 0
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            observed_at = local_dt.replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
            n_obs += store.insert_observation(
                conn, source_id=sid, station_code=f"{point_id}:{r['model']}",
                station_name=f"{point_id}:{r['model']}", lat=lat, lon=lon,
                variable="pressure_msl", value=r["pressure_msl_hpa"], unit="hPa",
                observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="third_party",
                provenance={"source_url": url, "model": r["model"], "tag": "MEASURED-model"},
            )
            n_this_point += 1
        notes.append(f"{point_id}: {n_this_point} row(s) fetched")
    return CollectResult(sid, ok_any, http=(200 if ok_any else None),
                          note="; ".join(notes), counts={"inserted": n_obs})


def collect_openmeteo_sst(conn, dry_run=False) -> CollectResult:
    """Open-Meteo Marine sea-surface temperature at 3 sea points (upper Gulf of
    Thailand, South China Sea off Vietnam, Andaman Sea), ONE comma-separated multi-point
    request per run. Founder addition 2026-09-27 ("เอาเลย เชื่อมเลย")."""
    sid = "openmeteo_sst"
    point_ids = list(parsers.OPENMETEO_SST_POINTS.keys())
    url = parsers.openmeteo_sst_url()
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    by_point = parsers.parse_openmeteo_sst_multipoint(json.loads(body), point_ids)
    n = 0
    for point_id, rows in by_point.items():
        lat, lon = parsers.OPENMETEO_SST_POINTS[point_id]
        for r in rows:
            try:
                local_dt = datetime.datetime.strptime(r["time_local"], "%Y-%m-%dT%H:%M")
            except ValueError:
                continue
            observed_at = local_dt.replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
            n += store.insert_observation(
                conn, source_id=sid, station_code=point_id, station_name=point_id,
                lat=lat, lon=lon, variable="sea_surface_temperature", value=r["sst_degc"],
                unit="degC", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
                trust_tier="third_party",
                provenance={"source_url": url, "tag": "MEASURED-model"},
            )
    return CollectResult(sid, True, http=200,
                          note=f"{sum(len(v) for v in by_point.values())} row(s) across "
                               f"{len(by_point)} point(s) fetched",
                          counts={"inserted": n})


def collect_noaa_oni(conn, dry_run=False) -> CollectResult:
    """NOAA CPC ENSO Oceanic Nino Index, monthly text table -- a slow index, throttled to
    at most once/24h (skips the network call entirely if the last fetch under
    raw/live/noaa_oni/ is under 24h old). Founder addition 2026-09-27. Data only, no
    threshold derived here."""
    sid = "noaa_oni"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + parsers.NOAA_ONI_URL)
    age_h = _last_fetch_age_hours(sid)
    if age_h is not None and age_h < 24:
        return CollectResult(sid, True, note=f"skipped -- last fetch {age_h:.1f}h ago, "
                                              "throttled to 1/24h for a slow monthly index")
    try:
        status, body = _one_get(parsers.NOAA_ONI_URL, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "txt")
    fetched_at = _utcnow_iso()
    row = parsers.parse_noaa_oni_latest(body.decode("utf-8", errors="replace"))
    if row is None:
        return CollectResult(sid, False, note="no parseable data row found")
    # Season labels (e.g. "JJA") aren't a single calendar date -- store against the UTC
    # instant this collector fetched it (fetched_at), same convention as other text-table
    # sources without a per-row timestamp of their own (e.g. tmd_7day_text_forecast).
    n = store.insert_observation(
        conn, source_id=sid, station_code="oni_pacific", station_name="ONI (Nino 3.4 region)",
        variable="oni", value=row["anom_degc"], unit="degC_anomaly",
        observed_at_utc=fetched_at, fetched_at_utc=fetched_at, trust_tier="official_report",
        provenance={"source_url": parsers.NOAA_ONI_URL, "season": row["season"],
                    "year": row["year"], "total_degc": row["total_degc"]},
    )
    return CollectResult(sid, True, http=200,
                          note=f"latest season {row['season']} {row['year']}, "
                               f"anom={row['anom_degc']}degC",
                          counts={"inserted": n})


def collect_hii_analyst_cctv(conn, dry_run=False) -> CollectResult:
    """HII analyst CCTV station catalog (coords + feed URL per camera, each owned by
    whichever agency installed it -- DWR/EGAT/RID, not HII). No numeric reading on this
    endpoint -- stored as one document per camera, same discipline as
    `collect_rid_res_table`."""
    sid = "hii_analyst_cctv"
    url = "https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/cctv"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, lwl.THAIWATER_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_hii_analyst_cctv(json.loads(body))
    n = 0
    for r in rows:
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at,
            section="cctv_station",
            text=f"{r['station_id']} | {r['title']} | {r.get('agency_en')} | "
                 f"{r.get('province_th')} | {r['lat']},{r['lon']} | {r.get('cctv_url')}")
        n += 1
    return CollectResult(sid, True, http=200, note=f"{len(rows)} CCTV station(s) fetched",
                          counts={"documents": n})


def collect_bma_pak_khlong_csv(conn, dry_run=False) -> CollectResult:
    """BMA/data.bangkok.go.th CKAN resource -- daily max water level, single station
    (แม่น้ำเจ้าพระยา-ปากคลอง / Pak Khlong on the Chao Phraya), no coordinate published on
    the CSV itself -- see parsers.parse_bma_pak_khlong_csv's module note."""
    sid = "bma_pak_khlong_csv"
    url = ("https://data.bangkok.go.th/dataset/0b2b0b13-62b1-4489-85ef-bb76a09898af/"
           "resource/b3cc65d5-52d9-42c5-91e9-4f0137b43ae8/download/river_pak_khlong.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_bma_pak_khlong_csv(body.decode("utf-8", errors="replace"))
    n = 0
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    n_stale = 0
    for r in rows:
        observed_at = (datetime.datetime.combine(
            datetime.date.fromisoformat(r["date"]), datetime.time(0, 0),
            tzinfo=datetime.timezone(datetime.timedelta(hours=7)))
            .astimezone(datetime.timezone.utc).isoformat())
        row_status = None
        try:
            observed_dt = datetime.datetime.fromisoformat(observed_at)
            if (now_dt - observed_dt) > datetime.timedelta(days=7):
                row_status = "stale"
                n_stale += 1
        except (ValueError, TypeError):
            pass
        n += store.insert_observation(
            conn, source_id=sid, station_code="bma_pak_khlong",
            station_name="แม่น้ำเจ้าพระยา-ปากคลอง (Pak Khlong)",
            variable="river_max_water_level_daily_m", value=r["max_water_level_m"],
            unit="m", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
            trust_tier="official_telemetry", status=row_status,
            provenance={"source_url": url, "cadence": "daily_max"},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} daily row(s) fetched ({n_stale} stale, >7d)",
                          counts={"inserted": n, "stale": n_stale})


def collect_bangkok_ckan_portal(conn, dry_run=False) -> CollectResult:
    """data.bangkok.go.th CKAN `package_search` catalog ("น้ำ"/water datasets) -- a
    dataset-metadata catalog, not a telemetry reading in itself. Stored as one document
    per matched dataset so a human/future collector can see what BMA has published,
    rather than guessing a per-dataset parser.

    KNOWN TRUNCATION: `rows=20` is a hard cap, no paging -- the real catalog has more
    matches than that (VERIFIED 2026-10-03: `result.count` reports 132 for this same
    query). This is a deliberate, documented truncation (not a silent one): this
    source is catalog-only (see CATALOG_ONLY_NOT_IN_REFRESH) and exists to let a
    human/future collector SEE what's published, not to enumerate every dataset --
    paging through `start=` to the full 132 would be 7 requests for a listing nothing
    downstream currently reads in full. Raise `rows`/page via `start=` if a future use
    needs the complete set."""
    sid = "bangkok_ckan_portal"
    url = "https://data.bangkok.go.th/api/3/action/package_search?q=%E0%B8%99%E0%B9%89%E0%B8%B3&rows=20"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_bangkok_ckan_catalog(json.loads(body))
    n = 0
    for r in rows:
        store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at,
            section="ckan_dataset",
            text=f"{r['dataset_id']} | {r['title_th']} | {r.get('organization')} | "
                 f"resources={r.get('num_resources')} | {r.get('resource_urls')}")
        n += 1
    return CollectResult(sid, True, http=200, note=f"{len(rows)} dataset(s) found",
                          counts={"documents": n})


def collect_bangkok_floodgate_locations(conn, dry_run=False) -> CollectResult:
    """data.bangkok.go.th Open Data `floodgate.csv` -- a static asset inventory (gate
    locations + design opening/control/critical/warning thresholds), not a live
    telemetry reading. One row per gate with a valid lat/lon (see
    `parsers.parse_bangkok_floodgate_locations`); a row with no valid coordinate is
    dropped, never geocoded. Stored as `floodgate_location` presence rows (value=1.0)
    with the numeric critical/warning threshold in the dedicated columns when the
    source cell actually parsed as a number, and every raw field (including any
    non-numeric threshold cell) kept verbatim in `provenance` -- see each row's
    `tag: RELAYED-static-reference` (this is design reference data the agency
    published, independently unverified against the physical asset)."""
    sid = "bangkok_floodgate_locations"
    url = ("https://data.bangkok.go.th/dataset/83ae5639-a37f-4e19-bd37-e1c97930f39d/"
           "resource/42948cf7-0759-4719-a32f-8eeabd89b8ee/download/floodgate.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_bangkok_floodgate_locations(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        warning = r["warning"] if isinstance(r["warning"], float) else None
        critical = r["critical"] if isinstance(r["critical"], float) else None
        n += store.insert_observation(
            conn, source_id=sid, station_code=f"floodgate:{r['id']}",
            station_name=r["name_th"], lat=r["lat"], lon=r["lon"],
            variable="floodgate_location", value=1.0, unit="presence",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            warning=warning, critical=critical, trust_tier="official_report",
            provenance={"source_url": url, "tag": "RELAYED-static-reference",
                        "district": r["district"], "type_th": r["type_th"],
                        "gate_opening_height_m": r["gate_opening_height_m"],
                        "water_control": r["water_control"],
                        "critical_raw": r["critical"], "warning_raw": r["warning"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} floodgate location row(s) with a valid "
                               "coordinate (static reference data)",
                          counts={"inserted": n})


def collect_bangkok_pump_stations(conn, dry_run=False) -> CollectResult:
    """data.bangkok.go.th Open Data pump-station-and-floodgate physical-data CSV -- a
    static asset inventory (pump/gate counts, total capacity, design thresholds), not
    a live telemetry reading. Same discipline as `collect_bangkok_floodgate_locations`
    (see its docstring): one row per station with a valid lat/lon, dropped rows never
    geocoded, composite non-numeric cells (e.g. "35(3)+10(5)") kept verbatim in
    `provenance`, tag `RELAYED-static-reference`."""
    sid = "bangkok_pump_station_and_floodgate_physical_data"
    url = ("https://data.bangkok.go.th/dataset/22475fbb-18ef-4705-9ce2-53f4907394e7/"
           "resource/0d645a7e-50f4-4c4f-ad1c-19db560b29c8/download/-.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_bangkok_pump_stations(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        warning = r["warning"] if isinstance(r["warning"], float) else None
        critical = r["critical"] if isinstance(r["critical"], float) else None
        n += store.insert_observation(
            conn, source_id=sid, station_code=f"pump_station:{r['id']}",
            station_name=r["name_th"], lat=r["lat"], lon=r["lon"],
            variable="pump_station_location", value=1.0, unit="presence",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            warning=warning, critical=critical, trust_tier="official_report",
            provenance={"source_url": url, "tag": "RELAYED-static-reference",
                        "district": r["district"], "type_th": r["type_th"],
                        "gate_count": r["gate_count"], "pump_count": r["pump_count"],
                        "total_capacity": r["total_capacity"],
                        "water_control": r["water_control"],
                        "critical_raw": r["critical"], "warning_raw": r["warning"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} pump-station row(s) with a valid "
                               "coordinate (static reference data)",
                          counts={"inserted": n})


def collect_gistda_flood_extent_api(conn, dry_run=False) -> CollectResult:
    """GISTDA 1-day flood-extent API (api-gateway.gistda.or.th) -- `auth: api_key` in
    the registry, so `run()`'s generic `_missing_api_key_env` gate already refuses to
    call this function at all when `GISTDA_API_KEY` is not set on the CALLER's own
    machine (never stored/bundled by us). This function's own body only ever runs once a
    key IS present.

    Transport reconciled with the OTHER GISTDA path already in this repo
    (`build_river_kg.py::overlay_gistda_flood`), which is live-confirmed working
    against a real key: a plain `api_key=` QUERY PARAMETER on `GISTDA_BASE`, no custom
    header. This function previously guessed an `API-KEY` header on a different
    endpoint (`disasters/flood-extent-1day`) based on a single 403 observed against a
    key found in a public CKAN listing, before the query-param path was confirmed
    elsewhere in this same repo -- that guess is now replaced by the confirmed-working
    transport. `GISTDA_API_REFERER` is still read as an optional second env var for
    whatever Referer value the caller's own key was issued against; if unset, no
    Referer header is sent. The raw response is stored as a document (not parsed into
    typed observations) until a real success response's shape is confirmed by whoever
    has a working key against THIS endpoint specifically (the 1-day extent, not the
    30-day one `overlay_gistda_flood` already pages through)."""
    sid = "gistda_flood_extent_api"
    base_url = "https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.1/disasters/flood-extent-1day"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + base_url)
    key = os.environ.get("GISTDA_API_KEY")
    if not key:
        # Belt-and-suspenders -- run()'s generic gate should already prevent reaching
        # here, but this function must never fetch without a key even if called directly.
        return CollectResult(sid, False, note="missing env var GISTDA_API_KEY in this "
                                               "machine's own environment -- not fetched")
    url = f"{base_url}?api_key={key}"
    headers = dict(GENERIC_HEADERS)
    referer = os.environ.get("GISTDA_API_REFERER")
    if referer:
        headers["Referer"] = referer
    try:
        status, body = _one_get(url, headers)
    except urllib.error.HTTPError as e:
        # Still cache the error body -- it's evidence (e.g. REFERER_REQUIRED), never
        # silently discarded.
        err_body = e.read() if hasattr(e, "read") else b""
        if err_body:
            _cache_raw(sid, err_body, "json")
        return CollectResult(sid, False, http=e.code, note=f"HTTP {e.code}: "
                             f"{err_body[:200].decode('utf-8', errors='replace')}")
    except (urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    n = store.insert_document(
        conn, source_id=sid, fetched_at_utc=fetched_at, section="raw_response",
        text=body.decode("utf-8", errors="replace")[:20000])
    return CollectResult(sid, True, http=200,
                          note="raw response stored as document -- no typed parser yet "
                               "(response shape unconfirmed, see function docstring)",
                          counts={"documents": 1 if n else 0})


def _key_gated_not_yet_fetched(sid: str, key_env: str, when_present_note: str) -> CollectResult:
    """Shared body for a key-needed (`auth: api_key`) source whose collector this check
    only takes as far as confirming the CALLER's own key is present on THIS machine --
    never stores/bundles a key, same self-install project decision as
    collect_gistda_flood_extent_api. When the key IS present, this does not perform the
    real fetch yet (OPEN, documented per-source in `when_present_note`) -- it never
    reports a fetch that did not happen. `run()`'s generic `_missing_api_key_env` gate
    already blocks reaching here with no key; this is belt-and-suspenders, same as
    every other api_key collector in this file."""
    key = os.environ.get(key_env)
    if not key:
        return CollectResult(sid, False, note=f"missing env var {key_env} in this "
                                               "machine's own environment -- not fetched")
    return CollectResult(sid, False, note=f"{key_env} is present in this machine's "
                                           f"environment, but this collector does not "
                                           f"perform the real fetch yet this check "
                                           f"(OPEN): {when_present_note}")


def collect_google_flood_hub_api(conn, dry_run=False) -> CollectResult:
    """Google Flood Hub REST API (floodforecasting.googleapis.com) -- PILOT-WAITLIST
    access only (sources/api_census.yaml), not self-service signup, but still the
    CALLER's own key once granted, never ours."""
    sid = "google_flood_hub_api"
    url = "https://floodforecasting.googleapis.com/v1/floodStatus:searchLatestAndNextForecasts"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    return _key_gated_not_yet_fetched(
        sid, "GOOGLE_FLOOD_HUB_API_KEY",
        "exact request shape (gauge IDs for Thailand, query params) not confirmed -- "
        "no waitlist-granted key available to probe against this check.")


def collect_cds_era5_reanalysis(conn, dry_run=False) -> CollectResult:
    """Copernicus CDS ERA5-Land reanalysis -- the real client is the `cdsapi` Python
    package's async submit/poll/download flow, not a plain GET, so this collector only
    confirms the caller's own CDS key is configured (`cdsapi` reads `~/.cdsapirc` by
    default; the `CDSAPI_KEY` env var is the override this repo reads instead, so the
    key never has to live in a dotfile this code manages). Implementing the submit/
    poll/download sequence is OPEN, future work."""
    sid = "cds_era5_reanalysis"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would use the cdsapi client "
                                              "(async submit/poll/download, not a GET)")
    return _key_gated_not_yet_fetched(
        sid, "CDSAPI_KEY",
        "cdsapi's submit/poll/download flow is not implemented this check.")


def collect_nasa_lhasa_landslide_nowcast(conn, dry_run=False) -> CollectResult:
    """NASA LHASA-2 landslide nowcast -- needs a NASA Earthdata Bearer token; the exact
    current granule/OPeNDAP URL for the daily 1km raster is OPEN (sources/
    api_census.yaml: RELAYED, WebSearch only, never fetched this programme)."""
    sid = "nasa_lhasa_landslide_nowcast"
    url = "https://www.earthdata.nasa.gov/data/catalog/ges-disc-global-landslide-nowcast-2.0.0"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    return _key_gated_not_yet_fetched(
        sid, "NASA_EARTHDATA_TOKEN",
        "the real per-granule GES DISC URL this token would authorize against is not "
        "yet confirmed (OPEN).")


def collect_opentopography_copernicus_dem_glo30(conn, dry_run=False) -> CollectResult:
    """OpenTopography Copernicus GLO-30 DEM -- a plain GET with `API_Key=` as a query
    parameter (OpenTopography's own public docs: instant self-service signup, no
    payment/approval wait). bbox fixed to a Sammakorn-area box this check (OPEN: not
    yet confirmed against the full upstream watershed this repo would actually need)."""
    sid = "opentopography_copernicus_dem_glo30"
    bbox_params = {"south": "13.70", "north": "13.85", "west": "100.60", "east": "100.75"}
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET OpenTopography "
                                              "globaldem (COP30, bbox=" + str(bbox_params) + ")")
    key = os.environ.get("OPENTOPOGRAPHY_API_KEY")
    if not key:
        return CollectResult(sid, False, note="missing env var OPENTOPOGRAPHY_API_KEY "
                                               "in this machine's own environment -- not fetched")
    params = dict(bbox_params, demtype="COP30", outputFormat="GTiff", API_Key=key)
    url = "https://portal.opentopography.org/API/globaldem?" + urlencode(params)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "tif")
    fetched_at = _utcnow_iso()
    n = store.insert_document(
        conn, source_id=sid, fetched_at_utc=fetched_at, section="raw_response",
        text=f"GeoTIFF DEM tile, {len(body)} bytes, bbox={bbox_params}")
    return CollectResult(sid, True, http=200,
                          note=f"DEM tile fetched, {len(body)} bytes -- stored as a "
                               "document pointer, not parsed into a raster pipeline",
                          counts={"documents": 1 if n else 0})


def collect_gfw_data_api(conn, dry_run=False) -> CollectResult:
    """Global Forest Watch Data API (data-api.globalforestwatch.org) -- self-service
    signup, but the real auth (Bearer token vs API-key header, exact dataset/query
    path for GLAD/RADD deforestation alerts near Sammakorn's upstream watershed) is
    OPEN, not confirmed this check."""
    sid = "gfw_data_api"
    url = "https://data-api.globalforestwatch.org/"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    return _key_gated_not_yet_fetched(
        sid, "GFW_API_KEY",
        "exact auth transport (Bearer vs header) and dataset/query path not confirmed.")


def collect_reliefweb_api_v2(conn, dry_run=False) -> CollectResult:
    """ReliefWeb API v2 disasters endpoint -- `appname` is a free but NOT instant
    registration (sources/api_census.yaml: 403 AccessDeniedHttpException without one),
    read from the caller's own environment like every other key_env here even though
    it is an identifier, not a secret in the usual sense."""
    sid = "reliefweb_api_v2"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET ReliefWeb API v2 "
                                              "disasters filtered to Thailand/flood")
    appname = os.environ.get("RELIEFWEB_APPNAME")
    if not appname:
        return CollectResult(sid, False, note="missing env var RELIEFWEB_APPNAME in "
                                               "this machine's own environment -- not fetched")
    params = {"appname": appname, "filter[field]": "country", "filter[value]": "Thailand",
              "query[value]": "flood"}
    url = "https://api.reliefweb.int/v2/disasters?" + urlencode(params)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    n = store.insert_document(
        conn, source_id=sid, fetched_at_utc=fetched_at, section="raw_response",
        text=body.decode("utf-8", errors="replace")[:20000])
    return CollectResult(sid, True, http=200,
                          note="raw response stored as document -- no typed parser yet "
                               "(response shape unconfirmed, see function docstring)",
                          counts={"documents": 1 if n else 0})


def collect_hii_mou_station_metadata(conn, dry_run=False) -> CollectResult:
    """HII watershed-forest (MOU) telemetry station metadata CSV (data.hii.or.th CKAN) --
    a nationwide station-location reference catalog, not a live telemetry reading.
    Stored as `station_location` presence rows (value=1.0), same pattern as
    `collect_bangkok_floodgate_locations`. A row with no parseable lat/lon is still
    stored (lat/lon=None) -- this is a metadata catalog, not a coordinate filter."""
    sid = "hii_mou_station_metadata"
    url = ("https://data.hii.or.th/dataset/617d1a99-e1a3-49a8-b507-2ce6d6c081ec/"
           "resource/5301fd2c-3808-4a37-a62c-e50ea06c3cd5/download/0all_stn_metadata.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_hii_mou_station_metadata_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["station_code"],
            station_name=r["station_name"], lat=r["lat"], lon=r["lon"],
            variable="station_location", value=1.0, unit="presence",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "tag": "RELAYED-static-reference",
                        "basin": r["basin"], "province": r["province"],
                        "station_type": r["station_type"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} station metadata row(s) (nationwide, static "
                               "reference catalog)",
                          counts={"inserted": n})


def collect_dnp_yom_basin_telemetry(conn, dry_run=False) -> CollectResult:
    """DNP Yom-basin (Phayao province) telemetry station list CSV -- station-siting
    reference, OUTSIDE this repo's currently served areas (see AREA_RELEVANT_SOURCES).
    Several stations in this real capture carry status_th 'ไม่มีการอัปเดตข้อมูลแล้ว
    (offline)', stored verbatim in provenance, never silently dropped or promoted."""
    sid = "dnp_yom_basin_telemetry"
    url = ("https://catalog.dnp.go.th/dataset/5c2f7296-147f-4836-8fcb-05c6c176822b/"
           "resource/2e8161e9-c013-4ccf-be13-c9f8a7623d08/download/"
           "telemetering-system-33-station-yom-basin.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_dnp_yom_telemetry_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["station_code"],
            station_name=r["station_name"], lat=None, lon=None,
            variable="station_location", value=1.0, unit="presence",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "tag": "RELAYED-static-reference",
                        "tambon": r["tambon"], "amphoe": r["amphoe"],
                        "province": r["province"], "station_type": r["station_type"],
                        "utm_zone": r["utm_zone"], "utm_x": r["utm_x"], "utm_y": r["utm_y"],
                        "status_th": r["status_th"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} station row(s), Yom basin (Phayao) -- "
                               "coordinates are UTM (zone 47), not stored as lat/lon "
                               "(no conversion performed, kept verbatim in provenance)",
                          counts={"inserted": n})


def collect_pcd_mwqi(conn, dry_run=False) -> CollectResult:
    """PCD marine-water-quality-index-by-station CSV -- an annual per-station index
    reading (2015-2024 series), observed_at pinned to Jan 1 of the Buddhist-era year in
    `year_be` (the CSV carries no finer date), tagged accordingly in provenance."""
    sid = "pcd_mwqi"
    url = ("https://pcd.gdcatalog.go.th/dataset/a7f08b13-2d47-4d3d-9fe3-ecf9b57943b8/"
           "resource/3356137b-3c56-4955-a9c2-098a7107656c/download/untitled.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_pcd_mwqi_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        try:
            year_ce = int(r["year_be"]) - 543
            observed_at = datetime.datetime(year_ce, 1, 1, tzinfo=datetime.timezone.utc).isoformat()
        except (ValueError, OverflowError):
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["station_code"],
            station_name=r["station_name"], lat=None, lon=None,
            variable="marine_water_quality_index", value=float(r["mwqi_value"]),
            unit="mwqi_index", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "year_be": r["year_be"],
                        "date_precision": "year_only_jan1_placeholder",
                        "province": r["province"], "mwqi_class_th": r["mwqi_class_th"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} annual station-year MWQI reading(s)",
                          counts={"inserted": n})


def collect_dmcr_marine_acidification(conn, dry_run=False) -> CollectResult:
    """DMCR marine-acidification mooring CSV -- real per-cast CTD readings (temp,
    salinity, pH) at coastal moorings, historical (2018 in this capture)."""
    sid = "dmcr_marine_acidification"
    url = ("https://dmcr.gdcatalog.go.th/dataset/69bccfdf-70a9-433c-9d38-c9ce3eb6a899/"
           "resource/d88f1886-5bd1-458f-8b0f-2ca1e3869dea/download/untitled.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_dmcr_marine_acidification_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        if r["ph_tot"] is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["mooring_name"],
            station_name=r["mooring_name"], lat=r["lat"], lon=r["lon"],
            variable="marine_ph_tot", value=r["ph_tot"], unit="pH",
            observed_at_utc=r["observed_at_utc"], fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "temp_c": r["temp_c"],
                        "salinity_psu": r["salinity_psu"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} mooring-cast row(s) with a parsed pH",
                          counts={"inserted": n})


def collect_royalrain_operations(conn, dry_run=False) -> CollectResult:
    """Royal Rainmaking Dept daily cloud-seeding operation log -- nationwide, real-time
    (today's operations at capture time). OUTSIDE this repo's current area scope (see
    AREA_RELEVANT_SOURCES) -- stored as `rainmaking_operation` presence rows, value=1.0
    when a mission actually flew (`is_operation`), else 0.0."""
    sid = "royalrain_operations"
    url = "https://rmo.royalrain.go.th/api/InfoServiceApi/dailyoperationsequenceinfo"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_royalrain_operations(json.loads(body))
    n = 0
    for i, r in enumerate(rows):
        try:
            observed_at = datetime.datetime.fromisoformat(r["operation_date"]).replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=7))
            ).astimezone(datetime.timezone.utc).isoformat()
        except (ValueError, TypeError):
            observed_at = fetched_at
        n += store.insert_observation(
            conn, source_id=sid, station_code=f"{r['unit_name']}:{i}",
            station_name=r["center_name"], lat=r["lat"], lon=r["lon"],
            variable="rainmaking_operation", value=1.0 if r["is_operation"] else 0.0,
            unit="presence", observed_at_utc=observed_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "unit_name": r["unit_name"],
                        "memo": r["memo"], "track_count": r["track_count"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} operation-unit record(s) (nationwide "
                               "cloud-seeding log, not canal/flood telemetry)",
                          counts={"inserted": n})


def collect_royalrain_agriculture_rainfall(conn, dry_run=False) -> CollectResult:
    """Royal Rainmaking Dept daily agriculture-area rainfall summary -- real JSON, no
    coordinate field in this payload (province/district name only, see parser
    docstring) -- stored as one document per province/district row rather than an
    `observations` row with a fabricated coordinate."""
    sid = "royalrain_agriculture_rainfall"
    url = "https://rmo.royalrain.go.th/api/InfoServiceApi/summaryagricultureareainfo"
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "json")
    fetched_at = _utcnow_iso()
    import json
    rows = parsers.parse_royalrain_agriculture_rainfall(json.loads(body))
    n = 0
    for r in rows:
        n += store.insert_document(
            conn, source_id=sid, fetched_at_utc=fetched_at, section="agriculture_rainfall",
            text=f"{r['operation_date']} | {r['center_name']} / {r['unit_name']} | "
                 f"rainy_on_target={r['is_rainy_on_target_area']} | "
                 f"rain_quantity={r['rain_quantity_th']} | "
                 f"provinces_checked={r['province_count']}") is not None
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} agriculture-area rainfall record(s) stored "
                               "as documents (no coordinate in this payload)",
                          counts={"documents": n})


def collect_hii_water_level_catalog(conn, dry_run=False) -> CollectResult:
    """HII nationwide water-level station catalog CSV (data.hii.or.th CKAN) --
    resolved from the sources/api_census.yaml row's dataset-landing-page redirect to
    its real resource file via one `package_show` call (2026-10-03). Same CSV schema
    as hii_mou_station_metadata, reuses that parser -- a different, larger station set,
    not a duplicate (confirmed by sha256). Stored as `station_location` presence rows,
    same pattern as that collector."""
    sid = "hii_water_level_catalog"
    url = ("https://data.hii.or.th/dataset/334aa20b-8187-430a-b8c5-d924f37334fe/"
           "resource/47274e2b-c905-4762-b025-11ca9067d107/download/0all_stn_metadata.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_hii_mou_station_metadata_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["station_code"],
            station_name=r["station_name"], lat=r["lat"], lon=r["lon"],
            variable="station_location", value=1.0, unit="presence",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "tag": "RELAYED-static-reference",
                        "basin": r["basin"], "province": r["province"],
                        "station_type": r["station_type"]},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} station metadata row(s) (nationwide, static "
                               "reference catalog)",
                          counts={"inserted": n})


def collect_hii_reservoir_metadata(conn, dry_run=False) -> CollectResult:
    """HII small-reservoir metadata CSV (data.hii.or.th CKAN) -- resolved as the sibling
    resource of the hii_reservoir_elevation_capacity_curve census row's own CKAN dataset
    via one `package_show` call (2026-10-03); that row's own elevation-capacity-curve
    URL still does not resolve to a direct file and stays catalog_only. Stored as a
    `reservoir_capacity_mcm` reading using each row's updated-capacity figure (falls
    back to the old figure when the updated one is missing), never both."""
    sid = "hii_reservoir_metadata"
    url = ("https://data.hii.or.th/dataset/ffba6c62-b9df-4b46-86b6-361b615cbe40/"
           "resource/9a02d5b3-6019-4616-a4a9-5dfddb745e9d/download/reservoir_metadata.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_hii_reservoir_metadata_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        capacity = r["updated_capacity_mcm"] if r["updated_capacity_mcm"] is not None \
            else r["old_capacity_mcm"]
        if capacity is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["reservoir_code"],
            station_name=r["reservoir_name"], lat=r["lat"], lon=r["lon"],
            variable="reservoir_capacity_mcm", value=capacity, unit="million_cubic_meters",
            observed_at_utc=fetched_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "tag": "RELAYED-static-reference",
                        "survey_date": r["survey_date"], "district": r["district"],
                        "province": r["province"],
                        "capacity_is_updated_figure": r["updated_capacity_mcm"] is not None},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} small-reservoir row(s) (nationwide, static "
                               "survey catalog)",
                          counts={"inserted": n})


def collect_pcd_coastal_marine_quality(conn, dry_run=False) -> CollectResult:
    """PCD coastal/marine water-quality monitoring-round CSV -- resolved from the
    pcd_coastal_marine_water_quality census row's dataset-landing-page redirect via one
    `package_show` call (2026-10-03), which named 5 real per-round resource files; this
    collector wires the most recent (BE 2568 / 2025). The other 4 are real and
    resolvable the same way but not wired this check. A row with no parseable pH is
    skipped, same discipline as collect_dmcr_marine_acidification."""
    sid = "pcd_coastal_marine_quality"
    url = ("https://pcd.gdcatalog.go.th/dataset/c8ec4520-0173-495f-a8f9-e9a9985dc9a3/"
           "resource/7e4a31ea-1e5a-4613-bfaa-3898175c1e9d/download/"
           "marine_water_quality_2568.csv")
    if dry_run:
        return CollectResult(sid, True, note="dry-run: would GET " + url)
    try:
        status, body = _one_get(url, GENERIC_HEADERS)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return CollectResult(sid, False, note=f"network/HTTP error: {e}")
    if status != 200:
        return CollectResult(sid, False, http=status, note=f"HTTP {status}")
    _cache_raw(sid, body, "csv")
    fetched_at = _utcnow_iso()
    rows = parsers.parse_pcd_coastal_marine_quality_csv(body.decode("utf-8-sig", errors="replace"))
    n = 0
    for r in rows:
        if r["ph"] is None:
            continue
        n += store.insert_observation(
            conn, source_id=sid, station_code=r["station_id"],
            station_name=r["station_name"], lat=None, lon=None,
            variable="marine_ph_tot", value=r["ph"], unit="pH",
            observed_at_utc=r["observed_at_utc"] or fetched_at, fetched_at_utc=fetched_at,
            trust_tier="official_report",
            provenance={"source_url": url, "province": r["province"],
                        "date_precision": "date_only_noon_placeholder" if r["observed_at_utc"]
                        else "unparsed_date_fetched_at_placeholder"},
        )
    return CollectResult(sid, True, http=200,
                          note=f"{len(rows)} per-station reading(s), {n} with a parsed pH",
                          counts={"inserted": n})


COLLECTORS = {
    "thaiwater_canal_waterlevel": collect_thaiwater_canal_waterlevel,
    "thaiwater_flood_road": collect_thaiwater_flood_road,
    "thaiwater_rain_24h": collect_thaiwater_rain_24h,
    "thaiwater_waterlevel": collect_thaiwater_waterlevel,
    "bma_pumphistory": collect_bma_pumphistory,
    "dds_flood_report": collect_dds_flood_report,
    "dds_daily_pdf": collect_dds_daily_pdf,
    "dds_tide_pdf": collect_dds_tide_pdf,
    "bma_klongmap": collect_bma_klongmap,
    "bma_watermap": collect_bma_watermap,
    "bma_station_detail": collect_bma_station_detail,
    "dds_nowcast_gif": collect_dds_nowcast_gif,
    "openmeteo_forecast": collect_openmeteo_forecast,
    "hii_dam": collect_hii_dam,
    "hii_watergate": collect_hii_watergate,
    "rid_res_table": collect_rid_res_table,
    "egat_water_crisis": collect_egat_water_crisis,
    "rid9_chonburi_rpt": collect_rid9_chonburi_rpt,
    "rid_app_reservoir": collect_rid_app_reservoir,
    "openmeteo_flood": collect_openmeteo_flood,
    "openmeteo_ensemble": collect_openmeteo_ensemble,
    "openmeteo_marine": collect_openmeteo_marine,
    "nasa_power": collect_nasa_power,
    "openmeteo_multimodel": collect_openmeteo_multimodel,
    "openmeteo_forecast16d": collect_openmeteo_forecast16d,
    "openmeteo_ensemble_daily": collect_openmeteo_ensemble_daily,
    "metno_locationforecast": collect_metno_locationforecast,
    "openmeteo_previous_runs": collect_openmeteo_previous_runs,
    "hii_waterlevel_load": collect_hii_waterlevel_load,
    "openmeteo_soil_moisture": collect_openmeteo_soil_moisture,
    "openmeteo_archive_precip": collect_openmeteo_archive_precip,
    "gdacs_events": collect_gdacs_events,
    "openmeteo_pressure": collect_openmeteo_pressure,
    "openmeteo_sst": collect_openmeteo_sst,
    "noaa_oni": collect_noaa_oni,
    "hii_analyst_cctv": collect_hii_analyst_cctv,
    "bma_pak_khlong_csv": collect_bma_pak_khlong_csv,
    "bangkok_ckan_portal": collect_bangkok_ckan_portal,
    "bangkok_floodgate_locations": collect_bangkok_floodgate_locations,
    "bangkok_pump_station_and_floodgate_physical_data": collect_bangkok_pump_stations,
    "gistda_flood_extent_api": collect_gistda_flood_extent_api,
    "google_flood_hub_api": collect_google_flood_hub_api,
    "cds_era5_reanalysis": collect_cds_era5_reanalysis,
    "nasa_lhasa_landslide_nowcast": collect_nasa_lhasa_landslide_nowcast,
    "opentopography_copernicus_dem_glo30": collect_opentopography_copernicus_dem_glo30,
    "gfw_data_api": collect_gfw_data_api,
    "reliefweb_api_v2": collect_reliefweb_api_v2,
    "hii_mou_station_metadata": collect_hii_mou_station_metadata,
    "dnp_yom_basin_telemetry": collect_dnp_yom_basin_telemetry,
    "pcd_mwqi": collect_pcd_mwqi,
    "dmcr_marine_acidification": collect_dmcr_marine_acidification,
    "royalrain_operations": collect_royalrain_operations,
    "royalrain_agriculture_rainfall": collect_royalrain_agriculture_rainfall,
    "hii_water_level_catalog": collect_hii_water_level_catalog,
    "hii_reservoir_metadata": collect_hii_reservoir_metadata,
    "pcd_coastal_marine_quality": collect_pcd_coastal_marine_quality,
}

# The 6 key-needed collectors added 2026-10-03 whose own body, this check, only ever
# confirms the caller's own key is present (see `_key_gated_not_yet_fetched`) --
# distinct from gistda_flood_extent_api, which DOES perform the real fetch once a key
# is present. Named here so a reader (or a future test) can tell the two postures
# apart without reading every docstring.
KEY_PRESENCE_ONLY_COLLECTORS = {
    "google_flood_hub_api", "cds_era5_reanalysis", "nasa_lhasa_landslide_nowcast",
    "gfw_data_api",
}

# Sources with no fetcher by design (manual import / static reference) -- see registry.yaml.
# social_listening_google/social_listening_paste are imported via `social_listening.py`'s
# own CLI (`--import-google` / `--import-paste`), not through this file's COLLECTORS dict --
# see docs/METHOD_social_listening.md.
NO_FETCHER = {"governor_shared_flooded_roads", "rtsd_2010_ground_level_map",
              "rid_flood_risk_map", "social_listening_google", "social_listening_paste"}

# Sources confirmed dormant (persistent 403) that a plain `--all` run must NOT touch, per
# the host-safety rule ("if 403/reset, stop touching that host"). `bma_klongmap` returned
# 403 on weather.bangkok.go.th on 2026-09-26 and has no reason to have changed since --
# leaving it in `--all` means every `--all` run re-probes a host that already told us no.
# Still collectible explicitly via `--source bma_klongmap` (e.g. to re-check by hand
# whether the block has lifted) -- a human decision, not something `--all` should do for
# them silently. See sources/registry.yaml's own `host_rule.notes` for this source.
DORMANT_NOT_IN_ALL = {"bma_klongmap", "bma_station_detail"}

# Sources whose own content is a catalog/document listing, not a reading that feeds
# `state`/`hazard`/`next_action` (the answer fields a caller actually asked for).
# `kb._refresh_relevant_sources` excludes this set entirely from a per-area `--refresh`
# fetch -- `--all`/`--source` are unaffected (a human explicitly asking for this
# catalog still gets it). Added after a MEASURED finding: a Sammakorn `--refresh` was
# also fetching the nationwide CCTV catalog (hii_analyst_cctv, ~169KB) and the
# data.bangkok.go.th dataset catalog (bangkok_ckan_portal) on every call, neither of
# which changes what the answer says. `bangkok_floodgate_locations` and
# `bangkok_pump_station_and_floodgate_physical_data` are the same static-reference
# class (locations + design thresholds, not a telemetry reading) and were added here
# for the same reason: without this, a per-area `--refresh` re-fetches and re-inserts
# their ~659 unchanging rows (230 + 429) every call, with no dedup on the observations
# table, so repeated refreshes pile up duplicate rows that never affect the answer.
CATALOG_ONLY_NOT_IN_REFRESH = {
    "hii_analyst_cctv", "bangkok_ckan_portal",
    "bangkok_floodgate_locations", "bangkok_pump_station_and_floodgate_physical_data",
}

# FIX (2026-10-03): the positive allowlist a default (refresh-by-default)
# `kb.py answer`/MCP `floodconnect_answer` call actually fetches -- every source that
# feeds `state` (readout.build_readout's canal/pump/flood-road/dds-daily/dds-tide/
# dds-flood-report/rain/social-listening factors), `hazard` (the two 16-day forecast
# models), or the real PROP-FLOOD-06 L-tier engine the sammakorn area's `next_action`
# also calls (tools/backtest/compute_prop_flood_06_sammakorn.py -- canal/pump/rain/
# forecast, already listed below for `state`/`hazard`). This is a POSITIVE allowlist
# (named sources IN), the opposite shape from `DORMANT_NOT_IN_ALL`/
# `CATALOG_ONLY_NOT_IN_REFRESH` above (named sources OUT of an otherwise-full list) --
# `kb._refresh_relevant_sources` intersects its candidate source_ids against this set by
# default, so a bare `kb.py answer --at sammakorn` (or the MCP tool with no override)
# no longer also fetches the ~40 OTHER wired sources (nationwide CCTV/disaster-event/
# climate-index/marine/basin sources with no served-area relevance at all, e.g.
# gdacs_events, noaa_oni, openmeteo_sst, marine_imis) that cost real time/bandwidth on
# the CALLER's own network for zero effect on this answer -- MEASURED before this fix:
# 47 of 72 registry sources survived the old "everything minus exclusions" filter for
# sammakorn. `kb.py answer --all`/`--source <id>` (and `collect.py --all`/`--source`)
# are UNCHANGED by this set -- it narrows only the per-area DEFAULT-refresh path,
# exactly like `AREA_RELEVANT_SOURCES`/`POINT_FILTERABLE_SOURCES` above. `accountability`
# and `next_action`'s route-finding read a separate, already-built nationwide topology/
# governance KG file (tools/kg/accountability.py, community_dag.py) -- not a live
# source_id at all, so neither needs an entry here.
ANSWER_SOURCES: frozenset = frozenset({
    "thaiwater_canal_waterlevel",      # canal levels -- state factor 4 (drainage)
    "bma_pumphistory",                 # pump status -- state factor 4 (drainage)
    "thaiwater_flood_road",            # flood-affected roads -- state factor 5
    "dds_daily_pdf",                   # BMA DDS daily bulletin -- state factor 4 (canal)
    "dds_tide_pdf",                    # BMA DDS tide page -- state factor 3 (น้ำทะเลหนุน)
    "dds_flood_report",                # BMA DDS flood-report page -- flood_road contradiction pairing
    "thaiwater_rain_24h",              # rain gauge -- PF06 RAIN_24H_EXCEEDS_DESIGN input
    "bma_watermap",                    # BMA Watermap canal readings -- see readout.py OPEN note
    "openmeteo_forecast16d",           # hazard forward forecast, per-model
    "metno_locationforecast",          # hazard forward forecast, per-model
    "social_listening_google",         # state factor -- social listening (place+state+time)
    "social_listening_paste",          # state factor -- social listening (place+state+time)
})

# Area/node relevance map (Added 2026-10-03): a source whose own coverage is a specific river
# basin/region narrower than "nationwide" is declared here with the area_ids (the same
# ids FORECAST7D_POINTS uses) it IS relevant to. A source absent from this map is
# relevant to every area -- same default-preserving posture as POINT_FILTERABLE_SOURCES
# above. kb._refresh_relevant_sources consults this to NARROW (never widen) which
# sources a per-area `--refresh` fetches; it has no effect on collect.py's own
# --all/--source paths, which still reach every wired source regardless of area.
AREA_RELEVANT_SOURCES: dict[str, set] = {
    # RID region-9 (Chonburi/Rayong/Chachoengsao/Prachinburi) reservoir report --
    # Bang Pakong/eastern-seaboard basin. None of this repo's currently served areas
    # (sammakorn, ram53, bangkok_east) sit in that basin (all three are Chao Phraya
    # basin, see FORECAST7D_POINTS) -- empty set means "relevant to no currently-served
    # area", not "relevant to none ever"; a future eastern-seaboard area would be added
    # here, not inferred.
    "rid9_chonburi_rpt": set(),

    # GOV9 pass (2026-10-03): 6 newly-wired sources, none of them in the Chao Phraya /
    # Sammakorn-Ram53-bangkok_east basin this repo currently serves -- see each
    # collector's own docstring for which basin/scope it IS relevant to (Yom basin,
    # nationwide marine-coastal, nationwide cloud-seeding). Empty set here means the
    # same "relevant to no currently-served area" posture as rid9_chonburi_rpt above,
    # not "relevant to none ever".
    "hii_mou_station_metadata": set(),
    "dnp_yom_basin_telemetry": set(),
    "pcd_mwqi": set(),
    "dmcr_marine_acidification": set(),
    "royalrain_operations": set(),
    "royalrain_agriculture_rainfall": set(),

    # GOV9 follow-up pass (2026-10-03): 3 more sources resolved from previously-parked
    # CKAN dataset-landing-page rows -- same "relevant to no currently-served area"
    # posture, nationwide/coastal in scope, none of it Chao Phraya basin.
    "hii_water_level_catalog": set(),
    "hii_reservoir_metadata": set(),
    "pcd_coastal_marine_quality": set(),
}


def _host_of(url: str) -> str:
    return urlparse(url).netloc if url else ""


def _missing_api_key_env(sid: str, entry: dict) -> str | None:
    """A generic, registry-driven gate for any wired source
    tagged `auth: api_key` -- reads the key from THIS MACHINE's own environment only
    (`entry["key_env"]`, or `f"{sid.upper()}_API_KEY"` if that field isn't set), never
    stores or bundles a key on our side (the self-install project decision). Returns the env
    var name that is missing, or None if the source isn't api_key-gated or the key IS
    present. As of 2026-10-03, several wired collectors ARE tagged `auth: api_key`
    (`gistda_flood_extent_api` plus the key-needed sources added this check -- see
    KEY_NEEDED_COLLECTORS below); this gate protects every one of them from the same
    one place, so a new api_key-gated collector gets this behaviour for free instead
    of reinventing it."""
    if entry.get("auth") != "api_key":
        return None
    key_env = entry.get("key_env") or f"{sid.upper()}_API_KEY"
    return None if os.environ.get(key_env) else key_env


def _looks_like_host_block(res: "CollectResult") -> bool:
    """True if this failed result looks like the HOST rejected/blocked us (403, or a
    connection reset/refused), as opposed to e.g. a timeout or a parse-level bug -- the
    circuit breaker in `run()` only trips on this, per the host-safety rule's own wording
    ('if 403/reset, stop touching that host')."""
    if res.ok:
        return False
    if res.http == 403:
        return True
    note = (res.note or "").lower()
    return "403" in note or "reset" in note or "connection refused" in note


# The 3 collectors that loop over every entry of
# FORECAST7D_POINTS in one call (fetching all 8 points' worth of requests regardless of
# which single area a caller asked about) now accept a `points` kwarg -- `run()` wires
# that through only for these ids, via `points_by_source`, so `kb.py`'s `--refresh --at
# sammakorn` stops also hitting hatyai/nan/chiangmai points on these 3 sources (MEASURED
# finding: a sammakorn refresh requested MET Norway points for hatyai/nan/chiangmai).
# Every other wired source is unaffected -- see `_refresh_relevant_sources` in kb.py for
# how the per-area point subset is computed.
POINT_FILTERABLE_SOURCES = {
    "openmeteo_forecast16d", "openmeteo_ensemble_daily", "metno_locationforecast",
}


def run(source_ids, dry_run=False, from_file=None, db_path=None, points_by_source=None):
    registry = load_registry()
    conn = store.connect(db_path) if db_path else store.connect()
    results = []
    tripped_hosts = set()  # per-run circuit breaker -- see _looks_like_host_block
    for sid in source_ids:
        if sid not in registry:
            results.append(CollectResult(sid, False, note="not in registry.yaml"))
            continue
        host = _host_of(registry[sid].get("url", ""))
        if not dry_run and host and host in tripped_hosts:
            results.append(CollectResult(
                sid, False, skipped=True,
                note=f"skipped -- host {host!r} was unreachable or blocked earlier this "
                     "run (403, reset, or refused -- the exact cause is not "
                     "distinguished); host-safety rule says stop touching it, not "
                     "request a different path on the same host"))
            continue
        if sid in NO_FETCHER:
            results.append(CollectResult(
                sid, False, skipped=True,
                note="skipped -- no fetcher by design (manual import / static "
                     "reference), see registry.yaml; never fetched, never counted as ok"))
            continue
        fn = COLLECTORS.get(sid)
        if fn is None:
            results.append(CollectResult(
                sid, False, skipped=True,
                note="skipped -- no collector implemented"))
            continue
        # The key gate only blocks a REAL fetch -- a --dry-run never calls the network
        # regardless (every collector's own `if dry_run: return ... True` short-circuits
        # first), so it must not need a key present either; this keeps `--dry-run --all`
        # reporting ok=True for every wired source with a collector, key-gated or not
        # (see test_collect.py::test_dry_run_all_sources_makes_no_network_call).
        missing_key_env = None if dry_run else _missing_api_key_env(sid, registry[sid])
        if missing_key_env:
            results.append(CollectResult(
                sid, False,
                note=f"missing env var {missing_key_env} in this machine's own "
                     "environment -- we never store or bundle an API key for you; "
                     "set it yourself, then re-run --refresh"))
            continue
        try:
            if sid in ("dds_daily_pdf", "dds_tide_pdf", "dds_flood_report"):
                res = fn(conn, dry_run=dry_run, from_file=from_file.get(sid) if from_file else None)
            elif sid in POINT_FILTERABLE_SOURCES and points_by_source and sid in points_by_source:
                res = fn(conn, dry_run=dry_run, points=points_by_source[sid])
            else:
                res = fn(conn, dry_run=dry_run)
        except Exception as e:  # noqa: BLE001 -- one source's failure must not stop --all
            res = CollectResult(sid, False, note=f"unexpected error: {e!r}")
        if not dry_run and host and _looks_like_host_block(res):
            tripped_hosts.add(host)
        results.append(res)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="Collect every registry source with a collector.")
    ap.add_argument("--source", metavar="ID", help="Collect one source by its registry id.")
    ap.add_argument("--dry-run", action="store_true", help="Print what would be fetched, no network call.")
    ap.add_argument("--from-file", metavar="PATH", help=(
        "With --source dds_daily_pdf / dds_tide_pdf / dds_flood_report: use this local "
        "file instead of any network call."))
    ap.add_argument("--db", metavar="PATH", help="Override the SQLite DB path (default data/observations.sqlite).")
    args = ap.parse_args()

    if not args.all and not args.source:
        ap.print_help()
        sys.exit(1)
    if args.from_file and not args.source:
        sys.exit("--from-file requires --source")

    if args.all:
        source_ids = [sid for sid in load_registry().keys() if sid not in DORMANT_NOT_IN_ALL]
    else:
        source_ids = [args.source]

    from_file_map = {args.source: Path(args.from_file)} if args.from_file else None
    results = run(source_ids, dry_run=args.dry_run, from_file=from_file_map,
                  db_path=Path(args.db) if args.db else None)
    for r in results:
        print(r)
    n_skipped = sum(1 for r in results if r.skipped)
    n_fail = sum(1 for r in results if not r.ok and not r.skipped)
    if n_skipped or n_fail:
        print(f"\n{len(results)} source(s) this run: {len(results) - n_skipped - n_fail} ok, "
              f"{n_skipped} skipped (no fetcher by design/not implemented), "
              f"{n_fail} unavailable (see notes above).")


if __name__ == "__main__":
    main()
