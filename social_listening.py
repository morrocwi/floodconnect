#!/usr/bin/env python3
"""
เสียงจากอินเทอร์เน็ต (social listening) -- the community/social-media layer of the
Sammakorn live flood-context data system.

What makes this DIFFERENT from generic "social listening": this module never stores
sentiment, opinion, engagement counts, or a poster's name/handle. It extracts exactly
three things per row -- **place** (soi/point), **water state** (a fixed, verifiable
vocabulary: house/garage/road/pond_overflow/canal_overbank/rising/receding/unknown, never
a feeling), and **time** -- tagged with `area` and `publisher_type` (media vs individual,
never a name). Every row is always read NEXT TO the official telemetry/report sources in
`sources/registry.yaml` (see `readout.py`'s "เสียงจากอินเทอร์เน็ต" section, which lists an
agree/disagree/no-overlap LOOKUP against the nearest official node -- never a score), and
this layer carries its own effectiveness record (`docs/METHOD_social_listening.md` +
the `method_evaluation` table, written by `--evaluate` below) instead of being assumed
useful.

Two registry sources feed this module (see `sources/registry.yaml`):
- `social_listening_google`   -- Google web search filtered to the last 24h, parsed via
  `parse_google_snapshot()` from a saved results snapshot (`search_google()` is the
  optional live fetcher -- see its own docstring for why it's optional).
- `social_listening_paste`    -- maintainer-pasted community-group text, parsed via
  `parse_paste()`. No fetcher by design (see registry `host_rule.max_requests_per_run: 0`).

Both parsers are pure functions (str in, list[dict] out, no network/DB access) --
`write_rows()` is the only function here that touches the store, and `search_google()` is
the only function here that touches the network (behind an optional `playwright` import).

No flood-risk score or formula anywhere in this file (this workspace's equation-discipline
rule, same as `store.py`/`readout.py`) -- `STATE_ORDER`'s ordinal codes are a fixed,
documented vocabulary for storage/sorting only, never combined into an index.
"""
import argparse
import datetime
import json
import re
from pathlib import Path

import store

HERE = Path(__file__).parent

# --- fixed, documented vocabulary -- never invent a new value without updating this ------

# Ordinal storage code per state, most severe last. `None` (unknown) is stored as a NULL
# `value` -- an unrecognized condition is never guessed into a severity band.
STATE_ORDER = {
    "receding": 0,
    "unknown": None,
    "rising": 1,
    "road": 2,
    "canal_overbank": 3,
    "pond_overflow": 3,
    "garage": 4,
    "house": 5,
}

# A name here does not certify the page is trustworthy -- it only routes that row's
# `publisher_type`/row-level trust_tier per the registry's own effectiveness note (a media
# row is stored as official_shared_inference, not community_report -- see write_rows()).
MEDIA_MARKERS = ("JS100", "อีจัน", "Rodee", "ไทยรัฐ", "ข่าวสด", "ผู้จัดการ", "เนชั่น",
                 "PPTV", "เจ้าพระยา", "Thai PBS", "ไทยพีบีเอส")

# First match wins -- ordered most-specific-area-name first (a place mentioning both
# "สัมมากร" and "ราม..." reads as sammakorn, not ram53, since it's the more specific hit
# for this workspace's own area of interest).
AREA_KEYWORDS = (("สัมมากร", "sammakorn"), ("ราม", "ram53"))

HASHTAG_RE = re.compile(r"#\S+")
DEPTH_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:[-–—]\s*(\d+(?:\.\d+)?)\s*)?ซม")
REL_HOUR_RE = re.compile(r"(\d+)\s*(?:ชั่วโมง|ชม)")
REL_MIN_RE = re.compile(r"(\d+)\s*นาที")
ABS_TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*น?")
TI_RE = re.compile(r"ตี\s*(\d{1,2})")
SOI_RE = re.compile(r"ซอย\s*([A-Za-z0-9/฀-๿]+)")
AUTHOR_LINE_RE = re.compile(r"^\s*(โดย|ผู้โพสต์|ชื่อผู้โพสต์|posted by)\s*[:：]")
_DASHY = set("-: ")


class NotAvailable(RuntimeError):
    """Raised by `search_google()` when its optional dependency (`playwright`) isn't
    importable -- callers should catch this and treat live search as unavailable this run,
    never retry in a loop (same fail-closed discipline as every fetcher in collect.py)."""


# --- small pure helpers -------------------------------------------------------------------

def _classify_state(text: str) -> str:
    """Fixed keyword ladder, checked most-severe-first, over a VERIFIABLE physical state
    (water reached X), never a sentiment word alone. Returns "unknown" if nothing matches
    -- never guessed."""
    if any(k in text for k in ("เข้าบ้าน", "เข้าในตัวบ้าน", "เข้าชั้น 1", "เข้าครัว", "ซึมเข้าบ้าน")):
        return "house"
    if any(k in text for k in ("เข้าโรงรถ", "เข้าที่จอดรถ")):
        return "garage"
    if "ล้นตลิ่ง" in text:
        return "canal_overbank"
    if any(k in text for k in ("บึง", "ทะเลสาบ")) and any(k in text for k in ("ล้น", "ทะลัก")):
        return "pond_overflow"
    if any(k in text for k in ("ลดลง", "แห้งแล้ว", "คลี่คลาย")):
        return "receding"
    if any(k in text for k in ("เพิ่มขึ้น", "ไม่ลด", "ยิ่งขึ้น", "ยังวิกฤต", "ยังคง")):
        return "rising"
    if any(k in text for k in ("ท่วม", "น้ำขัง", "น้ำขึ้น")):
        return "road"
    return "unknown"


def _extract_hashtags(text: str) -> list:
    return HASHTAG_RE.findall(text)


def _extract_depth_cm(text: str):
    m = DEPTH_RE.search(text)
    if not m:
        return None
    a = float(m.group(1))
    b = float(m.group(2)) if m.group(2) else None
    return (a + b) / 2.0 if b is not None else a


def _publisher_type(text: str) -> str:
    return "media" if any(mk in text for mk in MEDIA_MARKERS) else "individual"


def _guess_area(text: str) -> str:
    for kw, area in AREA_KEYWORDS:
        if kw in text:
            return area
    return "unknown"


def _extract_soi(text: str):
    m = SOI_RE.search(text)
    return m.group(0) if m else None


def _is_separator_row(cells: list) -> bool:
    return all(set(c) <= _DASHY for c in cells)


def _parse_time_token(token: str, ref_dt: datetime.datetime):
    """One relative/absolute Thai time expression -> a `datetime`, anchored to `ref_dt`
    (the moment the paste was pasted, or the moment the search was run) -- or None if
    nothing recognized (never fabricated as "now").

    - "N ชม./ชั่วโมงก่อน" / "N ชั่วโมงที่ผ่านมา" -> ref_dt - N hours.
    - "N นาทีก่อน" -> ref_dt - N minutes.
    - "ตี N" (Thai colloquial small-hours marker, e.g. "ตี 4" = 4am) -> N:00 same local date.
    - "HH:MM" / "HH.MM น." (absolute clock time) -> same local date as ref_dt, UNLESS that
      candidate sits more than 2h after ref_dt (a poster relaying "22.10 น." while the
      paste/search happens at 12:00 the next day almost always means last night, not 10h
      in the future) -- then it's read as the previous local day. A Dr-tier engineering
      heuristic, not a confirmed rule; documented here rather than silently applied.
    """
    token = token.strip()
    if not token:
        return None
    m = REL_HOUR_RE.search(token)
    if m and ("ก่อน" in token or "ที่ผ่านมา" in token):
        return ref_dt - datetime.timedelta(hours=int(m.group(1)))
    m = REL_MIN_RE.search(token)
    if m and ("ก่อน" in token or "ที่ผ่านมา" in token):
        return ref_dt - datetime.timedelta(minutes=int(m.group(1)))
    m = TI_RE.search(token)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return datetime.datetime.combine(
                ref_dt.date(), datetime.time(hour, 0), tzinfo=ref_dt.tzinfo)
    m = ABS_TIME_RE.search(token)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            return None
        candidate = datetime.datetime.combine(
            ref_dt.date(), datetime.time(hour, minute), tzinfo=ref_dt.tzinfo)
        if candidate > ref_dt + datetime.timedelta(hours=2):
            candidate -= datetime.timedelta(days=1)
        return candidate
    return None


def _split_row(line: str):
    """A markdown table row "| a | b | c |" -> ["a", "b", "c"], or None if `line` isn't a
    table row at all."""
    line = line.strip()
    if not line.startswith("|"):
        return None
    cells = [c.strip() for c in line.strip("|").split("|")]
    return cells


def _as_dt(value) -> datetime.datetime:
    if isinstance(value, datetime.datetime):
        return value
    return datetime.datetime.fromisoformat(value)


# --- the two parsers (pure: str in, list[dict] out) ---------------------------------------

def parse_paste(text: str, pasted_at, area: str = "sammakorn") -> list:
    """Parses a maintainer-pasted community-group text block (facebook_paste-style: a
    markdown table of soi/point | condition | time, possibly preceded by an author/poster
    line) into rows: {area, place_text, soi, state, depth_cm, hashtags, posted_at,
    publisher_type, source_url_domain}.

    `area` is taken from the CALLER (the group this paste came from is already known --
    e.g. "รวมของดีสัมมากร" is a Sammakorn group), never guessed from a row's own text.
    An earlier version guessed per-row via `_guess_area()` (like `parse_google_snapshot`,
    where the source really is area-agnostic search results) -- confirmed wrong in
    practice: a genuine Sammakorn-group row mentioning a road named "ราม 110" was
    misfiled under area "ram53" purely because that word appears in its own text. See
    docs/METHOD_social_listening.md's dated note on this.

    Any line matching `AUTHOR_LINE_RE` ("โดย ...", "ผู้โพสต์: ...") is DROPPED entirely --
    the name that follows it is never read into a row, never stored, never returned. This
    is the one thing this function is not allowed to get wrong.
    """
    pasted_at = _as_dt(pasted_at)
    rows = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if AUTHOR_LINE_RE.match(line):
            continue  # author line dropped, never stored -- see docstring
        cells = _split_row(line)
        if cells is None or len(cells) < 2 or _is_separator_row(cells):
            continue
        if cells[0] in ("ซอย/จุด", "จุด", "เวลา", "เวลา (≈)"):
            continue  # header row
        place_text, condition = cells[0], cells[1]
        time_token = cells[2] if len(cells) >= 3 else ""
        posted_dt = _parse_time_token(time_token, pasted_at)
        combined = f"{place_text} {condition}"
        rows.append({
            "area": area,
            "place_text": place_text,
            "soi": _extract_soi(place_text),
            "state": _classify_state(condition),
            "depth_cm": _extract_depth_cm(condition),
            "hashtags": _extract_hashtags(combined),
            "posted_at": posted_dt.isoformat() if posted_dt else None,
            "publisher_type": _publisher_type(combined),
            "source_url_domain": None,
        })
    return rows


def parse_google_snapshot(text: str, searched_at) -> list:
    """Parses a saved Google-results snapshot (headings/table rows of the form time |
    platform | place | condition, with relative times like "3 ชั่วโมงที่ผ่านมา"/"19
    ชม.ก่อน" or absolute "22.10 น.") into the same row shape as `parse_paste()`, plus a
    `platform` field. `text` can be a plain-text transcription of the results page (a
    saved snapshot's own extracted text) or a markdown table -- both parse the same way
    here since only table-row lines (starting with "|") are read.
    """
    searched_at = _as_dt(searched_at)
    rows = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        cells = _split_row(line)
        if cells is None or len(cells) < 4 or _is_separator_row(cells):
            continue
        if cells[0] in ("เวลาโพสต์ (≈)", "เวลา"):
            continue  # header row
        time_token, platform, place_text, condition = cells[0], cells[1], cells[2], cells[3]
        posted_dt = _parse_time_token(time_token, searched_at)
        combined = f"{place_text} {condition}"
        rows.append({
            "area": _guess_area(place_text),
            "place_text": place_text,
            "soi": _extract_soi(place_text),
            "state": _classify_state(condition),
            "depth_cm": _extract_depth_cm(condition),
            "hashtags": _extract_hashtags(combined),
            "posted_at": posted_dt.isoformat() if posted_dt else None,
            "publisher_type": _publisher_type(f"{platform} {condition}"),
            "source_url_domain": None,
            "platform": platform,
        })
    return rows


# --- optional live fetcher -----------------------------------------------------------------

def search_google(query: str, hours: int = 24, area: str = "unknown") -> Path:
    """ONE Google search navigate + ONE page-content read, saved as a raw snapshot under
    raw/live/social_listening_google/<ts>_<area>.html -- never parsed in this function
    (parse the saved file afterwards with `parse_google_snapshot`).

    Uses `playwright` ONLY if importable -- this repo does not add it as a hard
    dependency (see `docs/METHOD_social_listening.md`'s "cannot give" section). Raises
    `NotAvailable` if it's not installed; callers must not retry in a loop.

    Respects this source's own host_rule (sources/registry.yaml:
    social_listening_google.host_rule -- at most 2 queries per area per run, >=60s apart,
    stop on CAPTCHA/429): enforcing the "2 per run, 60s apart" spacing is the CALLER's
    responsibility across multiple invocations; this function makes exactly one navigate
    per call and raises on a CAPTCHA/429-shaped response rather than retrying.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError as e:
        raise NotAvailable(f"playwright not importable: {e}") from e

    url = f"https://www.google.com/search?q={query}&tbs=qdr:d"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(url, timeout=30_000)
            html = page.content()
            if "recaptcha" in html.lower() or "unusual traffic" in html.lower():
                raise NotAvailable("CAPTCHA/unusual-traffic page returned -- stop, do not retry")
        finally:
            browser.close()

    out_dir = HERE / "raw" / "live" / "social_listening_google"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    out_path = out_dir / f"{ts}_{area}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


# --- writing rows to the store --------------------------------------------------------------

def _bucket_15min(dt: datetime.datetime) -> datetime.datetime:
    minute = (dt.minute // 15) * 15
    return dt.replace(minute=minute, second=0, microsecond=0)


def write_rows(conn, rows: list, source_id: str, fetched_at_utc: str = None) -> int:
    """Writes parsed rows as `community_report` observations (value = STATE_ORDER ordinal,
    unit "state", provenance_json holding place/soi/hashtags/publisher_type/depth_cm/area).
    Dedupes on (area/soi/place, posted_at bucketed to 15 min, state) via the SAME identity
    index every other source in this repo uses (source_id, station_name, variable,
    observed_at_utc) -- `station_name` here is the soi (or the raw place text if no soi
    was extracted), so two re-imports of the same paste/snapshot are a no-op, never a
    duplicate row.

    trust_tier is row-level, not fixed to the registry's default: a row whose
    `publisher_type` is "media" is stored as `official_shared_inference` (a media outlet is
    not a private individual's own account); everything else is stored as
    `community_report`, per this source's registry entry.
    """
    fetched_at_utc = fetched_at_utc or datetime.datetime.now(datetime.timezone.utc).isoformat()
    n = 0
    for r in rows:
        state = r.get("state") or "unknown"
        value = STATE_ORDER.get(state)
        observed_at = r.get("posted_at") or fetched_at_utc
        try:
            bucketed = _bucket_15min(_as_dt(observed_at)).isoformat()
        except ValueError:
            bucketed = observed_at
        station_name = r.get("soi") or r.get("place_text")
        trust_tier = ("official_shared_inference" if r.get("publisher_type") == "media"
                      else "community_report")
        n += store.insert_observation(
            conn, source_id=source_id, station_code=None, station_name=station_name,
            variable="community_report", value=value, unit="state",
            observed_at_utc=bucketed, fetched_at_utc=fetched_at_utc, trust_tier=trust_tier,
            status=state,
            provenance={
                "area": r.get("area"), "place_text": r.get("place_text"), "soi": r.get("soi"),
                "hashtags": r.get("hashtags"), "publisher_type": r.get("publisher_type"),
                "depth_cm": r.get("depth_cm"), "source_url_domain": r.get("source_url_domain"),
                "platform": r.get("platform"),
            },
        )
    return n


# --- effectiveness record (measured, not opinion) --------------------------------------------

def evaluate_metrics(conn, area: str, date: str) -> dict:
    """Computes plain counts/shares over every `community_report` row stored for `area`
    (from either social_listening_ source) and writes them into `method_evaluation`
    (area, date, metric, value) via `store.insert_method_evaluation` -- one row per
    metric, upserted, never accumulated as duplicates on re-run.

    Every metric here is a MEASURED count over what's actually in the store -- this
    function does not read the two maintainer-supplied files directly (that reading, and the
    narrative interpretation of it, lives in `docs/METHOD_social_listening.md`, written by
    a human/reviewer pass, not derived mechanically here).
    """
    matched = []
    for sid in ("social_listening_google", "social_listening_paste"):
        for r in store.query_observations(conn, source_id=sid, variable="community_report",
                                           limit=5000):
            prov = json.loads(r["provenance_json"]) if r.get("provenance_json") else {}
            if prov.get("area") != area:
                continue
            row = dict(r)
            row["_prov"] = prov
            matched.append(row)

    metrics = {"rows_total": len(matched)}
    if matched:
        times = sorted(r["observed_at_utc"] for r in matched if r.get("observed_at_utc"))
        metrics["earliest_report_utc"] = times[0] if times else None
        metrics["latest_report_utc"] = times[-1] if times else None
        n = len(matched)
        metrics["share_with_soi_point"] = round(
            sum(1 for r in matched if r["_prov"].get("soi")) / n, 3)
        metrics["share_with_depth_number"] = round(
            sum(1 for r in matched if r["_prov"].get("depth_cm") is not None) / n, 3)
        media_n = sum(1 for r in matched if r["_prov"].get("publisher_type") == "media")
        metrics["share_from_media"] = round(media_n / n, 3)
        metrics["share_from_individuals"] = round((n - media_n) / n, 3)

    for metric, value in metrics.items():
        store.insert_method_evaluation(conn, area=area, date=date, metric=metric, value=value)
    return metrics


# --- CLI ---------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--import-paste", metavar="PATH", help="Parse+import a pasted text file.")
    ap.add_argument("--import-google", metavar="PATH", help="Parse+import a Google snapshot file.")
    ap.add_argument("--at", metavar="ISO_TS", help="pasted_at/searched_at override (default: now).")
    ap.add_argument("--evaluate", action="store_true",
                     help="Compute+store method_evaluation metrics for --area on --date.")
    ap.add_argument("--area", default="sammakorn")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--db", metavar="PATH", help="Override the SQLite DB path.")
    args = ap.parse_args()

    conn = store.connect(Path(args.db)) if args.db else store.connect()
    ref = args.at or datetime.datetime.now(datetime.timezone.utc).isoformat()

    if args.import_paste:
        text = Path(args.import_paste).read_text(encoding="utf-8")
        rows = parse_paste(text, ref, area=args.area)
        n = write_rows(conn, rows, "social_listening_paste")
        print(f"parsed {len(rows)} row(s), inserted {n} new observation(s)")
    if args.import_google:
        text = Path(args.import_google).read_text(encoding="utf-8")
        rows = parse_google_snapshot(text, ref)
        n = write_rows(conn, rows, "social_listening_google")
        print(f"parsed {len(rows)} row(s), inserted {n} new observation(s)")
    if args.evaluate:
        metrics = evaluate_metrics(conn, args.area, args.date)
        print(f"method_evaluation for {args.area} / {args.date}:")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
    if not (args.import_paste or args.import_google or args.evaluate):
        ap.print_help()


if __name__ == "__main__":
    main()
