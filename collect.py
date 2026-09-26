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
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import yaml

import live_water_level as lwl
import parsers
import store

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
    def __init__(self, source_id, ok, http=None, note="", counts=None):
        self.source_id, self.ok, self.http, self.note = source_id, ok, http, note
        self.counts = counts or {}

    def __repr__(self):
        return f"[{self.source_id}] ok={self.ok} http={self.http} {self.note} {self.counts}"


def _one_get(url: str, headers: dict, timeout: int = REQUEST_TIMEOUT_S) -> tuple:
    """ONE GET, no retry. Returns (status, body). Raises on network error/non-200."""
    req = urllib.request.Request(url, headers=headers)
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
                        "pumps_total": r.get("pumps_total"), "gate_open_m": r.get("gate_open")},
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


COLLECTORS = {
    "thaiwater_canal_waterlevel": collect_thaiwater_canal_waterlevel,
    "thaiwater_flood_road": collect_thaiwater_flood_road,
    "bma_pumphistory": collect_bma_pumphistory,
    "dds_flood_report": collect_dds_flood_report,
    "dds_daily_pdf": collect_dds_daily_pdf,
    "dds_tide_pdf": collect_dds_tide_pdf,
    "bma_klongmap": collect_bma_klongmap,
    "dds_nowcast_gif": collect_dds_nowcast_gif,
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
DORMANT_NOT_IN_ALL = {"bma_klongmap"}


def _host_of(url: str) -> str:
    return urlparse(url).netloc if url else ""


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


def run(source_ids, dry_run=False, from_file=None, db_path=None):
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
                sid, False,
                note=f"skipped -- host {host!r} was blocked (403/reset) by an earlier "
                     "source this run; host-safety rule says stop touching it, not "
                     "request a different path on the same host"))
            continue
        if sid in NO_FETCHER:
            results.append(CollectResult(sid, True, note="no fetcher by design -- see registry.yaml"))
            continue
        fn = COLLECTORS.get(sid)
        if fn is None:
            results.append(CollectResult(sid, False, note="no collector implemented"))
            continue
        try:
            if sid in ("dds_daily_pdf", "dds_tide_pdf", "dds_flood_report"):
                res = fn(conn, dry_run=dry_run, from_file=from_file.get(sid) if from_file else None)
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
    n_fail = sum(1 for r in results if not r.ok)
    if n_fail:
        print(f"\n{n_fail}/{len(results)} source(s) unavailable this run (see notes above).")


if __name__ == "__main__":
    main()
