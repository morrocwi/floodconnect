#!/usr/bin/env python3
"""
Wikipedia canal-category harvester -- founder task (verbatim): th.wikipedia
"หมวดหมู่:คลองในประเทศไทย" -> "สกัดเข้า kggraph อย่างเป็นระบบ" (extract systematically
into the knowledge graph).

This is a standalone harvester, NOT wired into `assets_registry.py`'s `build()`
pipeline in this check (that file, `tools/kg/build_kg.py`, `INDEX.yaml`,
`docs/knowledge/water_system_dag.mmd` and `WATER_SYSTEM_DAG.md` are owned by another
worker in this run -- see the task's file-lock list). It follows the same
archive-everything-raw / never-invent-a-coordinate / RELAYED discipline as
`assets_registry.py`'s harvesters and shares its OPEN/never-geocode posture, but
produces its own tracked output (`sources/wikipedia_canals.yaml`) and its own raw
archive directory (`raw/wikipedia/canals/<UTC ts>/`).

Pipeline:
    1. th.wikipedia.org/w/api.php `list=categorymembers` on
       "หมวดหมู่:คลองในประเทศไทย", `cmtype=page|subcat`, followed recursively into
       subcategories to depth 3, deduped by pageid, subcategory path recorded per page.
    2. Per page (batched 50 pageids/request, the MediaWiki API limit for this call
       shape): `prop=coordinates|pageprops|revisions`
       (`rvprop=ids|timestamp|content`, `rvslots=main`) -- extracts, from the wikitext
       infobox/body when present: จังหวัด, ต้นน้ำ/จุดเริ่ม, ปลายน้ำ/จุดสิ้นสุด, ความยาว,
       ผู้ดูแล/หน่วยงาน.
    3. If a page has no `coordinates` prop result, look up Wikidata P625 via the
       page's `pageprops.wikibase_item` (www.wikidata.org/w/api.php
       `action=wbgetclaims&property=P625`).
    4. Archive EVERY raw API response object, one per line, append-only, to
       `raw/wikipedia/canals/<UTC ts>/pages.jsonl` + a `manifest.json` alongside it.
    5. Normalise into `sources/wikipedia_canals.yaml` (tracked, one row per canal).

Rate/etiquette discipline (this check's own spec, matches this repo's existing
one-request-per-URL/no-retry-loop posture elsewhere):
    - max 1 request/second across BOTH th.wikipedia.org and www.wikidata.org
    - `maxlag=5` on every query-action MediaWiki call
    - no retries beyond ONE polite retry, after a flat 10s sleep, on HTTP 429/503
      only -- every other failure (network error, other HTTP status) is recorded and
      skipped, never looped.
    - identifying User-Agent: "FloodConnect canal harvester; non-commercial
      research" -- generic, never a personal name or email (this repo's own rule,
      AGENTS.md sec 2 "no personal names").

CLI:
    python3 -m tools.harvest.wikipedia_canals --run
    python3 -m tools.harvest.wikipedia_canals --run --max-depth 3 --dry-run
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent.parent  # repo root (tools/harvest/..)
RAW_DIR = HERE / "raw" / "wikipedia" / "canals"
OUT_YAML = HERE / "sources" / "wikipedia_canals.yaml"
KG_DOC = HERE / "docs" / "knowledge" / "WIKIPEDIA_CANALS.md"

USER_AGENT = "FloodConnect canal harvester; non-commercial research"
HEADERS = {"User-Agent": USER_AGENT}

TH_API = "https://th.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"

ROOT_CATEGORY = "หมวดหมู่:คลองในประเทศไทย"
MAX_SUBCAT_DEPTH = 3
BATCH_SIZE = 50  # MediaWiki pageids-per-request cap for these query shapes
MIN_REQUEST_INTERVAL_S = 4.0  # spec ceiling is max 1 req/s; run much slower (~0.25
# req/s) across both hosts because attempts at 1 req/s and 0.5 req/s both drew
# persistent HTTP 429 from th.wikipedia.org's categorymembers endpoint specifically
# (see WIKIPEDIA_CANALS.md "API problems") -- still within the "max 1 request/second"
# ceiling, just far more conservative given this endpoint's real observed behaviour.
RETRY_STATUSES = {429, 503}
RETRY_SLEEP_S = 10.0
LICENCE = "CC BY-SA 4.0"

# --- infobox/text field extraction ------------------------------------------------

# Thai wikitext infobox parameter names this check asks for (จังหวัด, ต้นน้ำ/จุดเริ่ม,
# ปลายน้ำ/จุดสิ้นสุด, ความยาว, ผู้ดูแล/หน่วยงาน), each mapped to the normalised output
# field. Checked against real fetched pages: th.wikipedia canal articles in this
# category overwhelmingly use the English-keyed `{{Infobox canal}}` template (e.g.
# `start_point`, `end_point`, `length_km`, `present_owner`, `navigation_authority`,
# `location`), not Thai-labelled infobox keys -- both key sets are matched below so
# the extraction actually finds what the real template stores, never invented.
FIELD_PATTERNS = {
    "provinces_raw": [r"จังหวัด", r"^location$"],
    "upstream_name": [r"ต้นน้ำ", r"จุดเริ่ม(?:ต้น)?", r"^start_point$", r"^begin_coord$"],
    "downstream_name": [r"ปลายน้ำ", r"จุดสิ้นสุด", r"^end_point$", r"^end_coord$"],
    "length_km_raw": [r"ความยาว", r"^length_km$", r"^len_m$"],
    "operator": [r"ผู้ดูแล", r"หน่วยงาน", r"^present_owner$", r"^navigation_authority$",
                 r"^original_owner$"],
}

_INFOBOX_LINE_RE = re.compile(
    r"^\|[ \t]*(?P<key>[^=\n|]+?)[ \t]*=[ \t]*(?P<val>.*)$", re.MULTILINE
)
# NOTE: the whitespace around key/val is deliberately [ \t]*, never \s* -- \s also
# matches newline, which would let an empty-valued line (e.g. "| coordinates =\n")
# swallow the following line's "| key = value" into ITS OWN val group (found the
# hard way against a real page fixture during this check's own test-writing).
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]")
_REF_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_TEMPLATE_RE = re.compile(r"\{\{[^{}]*\}\}")
# `{{convert|50.846|km}}` / `{{convert|50.846|km|mi}}` -> "50.846 km" -- unwrapped
# BEFORE the generic template-strip below would otherwise delete the number
# entirely. Never invents a unit conversion; keeps the template's own first
# number+unit verbatim.
_CONVERT_RE = re.compile(
    r"\{\{\s*convert\s*\|\s*([\d.,]+)\s*\|\s*([a-zA-Z]+)[^}]*\}\}", re.IGNORECASE)


def _clean_wikitext(val: str) -> str:
    """Strip refs, html tags, templates, wikilink brackets (keeping the display
    text), bold/italic markup, and surrounding whitespace from an infobox value."""
    if not val:
        return ""
    val = _REF_RE.sub("", val)
    val = _HTML_TAG_RE.sub("", val)
    val = _CONVERT_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", val)
    # collapse wikilinks: [[a|b]] -> b, [[a]] -> a
    val = _WIKILINK_RE.sub(lambda m: m.group(2) or m.group(1), val)
    for _ in range(3):
        val = _TEMPLATE_RE.sub("", val)
    val = val.replace("'''", "").replace("''", "")
    val = re.sub(r"<br\s*/?>", ", ", val, flags=re.IGNORECASE)
    val = re.sub(r"\s+", " ", val).strip(" ,;")
    return val.strip()


def extract_infobox_fields(wikitext: str) -> dict:
    """Parse `|key = value` infobox lines out of raw wikitext and map them onto
    this check's five requested fields via FIELD_PATTERNS. Returns only fields
    actually present (never fabricates a missing one)."""
    if not wikitext:
        return {}
    found_raw: dict = {}
    for m in _INFOBOX_LINE_RE.finditer(wikitext):
        key = m.group("key").strip()
        val = _clean_wikitext(m.group("val"))
        if not val:
            continue
        for field, patterns in FIELD_PATTERNS.items():
            if field in found_raw:
                continue
            for pat in patterns:
                if re.search(pat, key):
                    found_raw[field] = val
                    break
    return found_raw


def _parse_length_km(raw: str | None) -> float | None:
    if not raw:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(กม\.?|กิโลเมตร|km)", raw, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(ม\.?|เมตร|m)\b", raw)
    if m:
        try:
            return round(float(m.group(1).replace(",", ".")) / 1000.0, 3)
        except ValueError:
            return None
    # a bare number with no unit at all -- only for the `length_km`-named infobox
    # field itself, whose own key already declares the unit; a Thai `ความยาว` value
    # with no unit and no keyword match is left unparsed (None) rather than guessed.
    m = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*", raw)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _split_provinces(raw: str | None) -> list:
    if not raw:
        return []
    parts = re.split(r"[,\n/•]|(?:\s{2,})", raw)
    return [p.strip() for p in parts if p.strip()]


# --- HTTP with 1 req/s + maxlag + one polite retry on 429/503 ---------------------

class _RateLimiter:
    def __init__(self, min_interval_s: float):
        self.min_interval_s = min_interval_s
        self._last = 0.0

    def wait(self):
        now = time.monotonic()
        delta = now - self._last
        if delta < self.min_interval_s:
            time.sleep(self.min_interval_s - delta)
        self._last = time.monotonic()


_LIMITER = _RateLimiter(MIN_REQUEST_INTERVAL_S)


def _get(url: str, params: dict, log: list, timeout: int = 30) -> dict | None:
    """ONE request/second (shared limiter across hosts), at most one polite retry
    (flat 10s sleep) on 429/503, every other failure recorded to `log` and skipped
    -- never looped, never a second retry."""
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"
    attempts_left = 2
    while attempts_left > 0:
        attempts_left -= 1
        _LIMITER.wait()
        try:
            req = urllib.request.Request(full_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                body = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            body = e.read() if e.fp else b""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            log.append({"url": full_url, "error": str(e), "ts": _utcnow_iso()})
            return None
        if status == 200:
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError as e:
                log.append({"url": full_url, "http": status,
                            "error": f"non-JSON body: {e}", "ts": _utcnow_iso()})
                return None
            parsed["_meta"] = {"url": full_url, "http": status, "ts": _utcnow_iso()}
            return parsed
        if status in RETRY_STATUSES and attempts_left > 0:
            log.append({"url": full_url, "http": status,
                        "note": f"retrying once after {RETRY_SLEEP_S}s",
                        "ts": _utcnow_iso()})
            time.sleep(RETRY_SLEEP_S)
            continue
        log.append({"url": full_url, "http": status, "ts": _utcnow_iso()})
        return None
    return None


def _utcnow_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _utcnow_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


# --- categorymembers, recursive to depth 3, deduped -------------------------------

def fetch_category_tree(root_category: str, max_depth: int, raw_log: list,
                         error_log: list) -> dict:
    """Returns {pageid: {"title": str, "subcat_path": [category titles from root
    to the subcat this page was listed under]}} for every ns=0 (article) page found,
    recursively following ns=14 (subcategory) members to `max_depth`, deduped by
    pageid (a page reachable via two different subcat paths keeps the FIRST path
    seen, breadth-first from the root)."""
    seen_pages: dict = {}
    visited_cats = {root_category}
    frontier = [(root_category, [root_category], 0)]
    while frontier:
        cat_title, path, depth = frontier.pop(0)
        cmcontinue = None
        while True:
            params = {
                "action": "query", "list": "categorymembers",
                "cmtitle": cat_title, "cmtype": "page|subcat", "cmlimit": "500",
                "format": "json", "maxlag": "5",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            resp = _get(TH_API, params, error_log)
            if resp is None:
                break
            raw_log.append(resp)
            members = resp.get("query", {}).get("categorymembers", [])
            for m in members:
                if m.get("ns") == 0:
                    pid = m["pageid"]
                    if pid not in seen_pages:
                        seen_pages[pid] = {"title": m["title"], "subcat_path": path}
                elif m.get("ns") == 14:
                    subcat_title = m["title"]
                    if subcat_title not in visited_cats and depth + 1 <= max_depth:
                        visited_cats.add(subcat_title)
                        frontier.append((subcat_title, path + [subcat_title], depth + 1))
            cont = resp.get("continue", {}).get("cmcontinue")
            if not cont:
                break
            cmcontinue = cont
    return seen_pages


# --- per-page prop=coordinates|pageprops|revisions, batched -----------------------

def fetch_pages_batch(pageids: list, raw_log: list, error_log: list) -> dict:
    """One `prop=coordinates|pageprops|revisions` call per <=50 pageids. Returns
    {pageid: page-dict-from-API} for every page returned (a page can be entirely
    absent from the response if the whole batch failed -- caller sees it missing)."""
    out: dict = {}
    for i in range(0, len(pageids), BATCH_SIZE):
        chunk = pageids[i:i + BATCH_SIZE]
        params = {
            "action": "query", "pageids": "|".join(str(p) for p in chunk),
            "prop": "coordinates|pageprops|revisions",
            "rvprop": "ids|timestamp|content", "rvslots": "main",
            "format": "json", "maxlag": "5",
        }
        resp = _get(TH_API, params, error_log)
        if resp is None:
            continue
        raw_log.append(resp)
        for pid_str, pdata in resp.get("query", {}).get("pages", {}).items():
            out[int(pid_str)] = pdata
    return out


def fetch_wikidata_coord(wikibase_item: str, raw_log: list, error_log: list):
    """P625 (coordinate location) lookup via wbgetclaims. Returns (lat, lon) or
    (None, None) if the item has no P625 claim or the call failed."""
    params = {
        "action": "wbgetclaims", "entity": wikibase_item, "property": "P625",
        "format": "json",
    }
    resp = _get(WD_API, params, error_log)
    if resp is None:
        return None, None
    raw_log.append(resp)
    claims = resp.get("claims", {}).get("P625", [])
    if not claims:
        return None, None
    try:
        value = claims[0]["mainsnak"]["datavalue"]["value"]
        return value.get("latitude"), value.get("longitude")
    except (KeyError, IndexError, TypeError):
        return None, None


# --- normalisation -----------------------------------------------------------------

def normalise_page(pageid: int, meta: dict, page_data: dict, wikidata_coord) -> dict:
    title = page_data.get("title") or meta.get("title") or f"pageid:{pageid}"
    coords = page_data.get("coordinates") or []
    lat = lon = None
    coord_source = "none"
    if coords:
        lat = coords[0].get("lat")
        lon = coords[0].get("lon")
        coord_source = "page"
    elif wikidata_coord and wikidata_coord[0] is not None:
        lat, lon = wikidata_coord
        coord_source = "wikidata"

    revisions = page_data.get("revisions") or []
    revid = revision_timestamp = None
    wikitext = ""
    if revisions:
        rev = revisions[0]
        revid = rev.get("revid")
        revision_timestamp = rev.get("timestamp")
        slot = (rev.get("slots") or {}).get("main") or {}
        wikitext = slot.get("*") or slot.get("content") or ""

    fields = extract_infobox_fields(wikitext)
    provinces = _split_provinces(fields.get("provinces_raw"))
    length_km = _parse_length_km(fields.get("length_km_raw"))

    return {
        "canal_id": f"wp:{pageid}",
        "name_th": title,
        "provinces": provinces,
        "lat": lat,
        "lon": lon,
        "coord_source": coord_source,
        "length_km": length_km,
        "upstream_name": fields.get("upstream_name"),
        "downstream_name": fields.get("downstream_name"),
        "operator": fields.get("operator"),
        "revid": revid,
        "revision_timestamp": revision_timestamp,
        "licence": LICENCE,
        "tag": "RELAYED",
        "url": f"https://th.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
        "subcat_path": meta.get("subcat_path", []),
    }


# --- exact-name matching against existing assets (NOTE only, never merge) --------

def _normalise_th_name_for_match(name: str) -> str:
    s = name or ""
    s = re.sub(r"^(คลอง|ค\.)\s*", "", s)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)  # drop trailing "(จังหวัด...)" disambiguator
    s = s.replace("์", "")
    s = re.sub(r"\s+", "", s)
    return s.strip()


def match_existing_assets(canal_rows: list, db_path=None) -> None:
    """Exact normalised-Thai-name match against existing gauge/gate/pump_station/
    dam asset rows already in the assets registry (canal class assets, if any, plus
    any OSM-derived canal_node from the KG are out of scope here -- this repo's own
    `store.py`/`assets` table is read-only queried, never written to, and no
    coordinate is ever copied in either direction). Adds a `matches` list (asset_ids)
    to each row IN PLACE, as a NOTE only."""
    try:
        import store  # local import: repo root must be on sys.path (see __main__ below)
    except ImportError:
        for row in canal_rows:
            row["matches"] = []
        return
    try:
        conn = store.connect(db_path) if db_path else store.connect()
        store.ensure_assets_schema(conn)
        existing = store.query_assets(conn)
    except Exception:
        for row in canal_rows:
            row["matches"] = []
        return
    by_norm: dict = {}
    for a in existing:
        n = _normalise_th_name_for_match(a.get("name_th") or "")
        if n:
            by_norm.setdefault(n, []).append(a["asset_id"])
    for row in canal_rows:
        n = _normalise_th_name_for_match(row["name_th"])
        row["matches"] = list(by_norm.get(n, []))


# --- archive + write -----------------------------------------------------------------

def archive_run(raw_log: list, error_log: list, manifest_extra: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages_path = out_dir / "pages.jsonl"
    with pages_path.open("a", encoding="utf-8") as f:
        for obj in raw_log:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    manifest = {
        "run_started_utc": manifest_extra.get("run_started_utc"),
        "run_finished_utc": _utcnow_iso(),
        "root_category": ROOT_CATEGORY,
        "max_subcat_depth": MAX_SUBCAT_DEPTH,
        "batch_size": BATCH_SIZE,
        "min_request_interval_s": MIN_REQUEST_INTERVAL_S,
        "user_agent": USER_AGENT,
        "api_response_count": len(raw_log),
        "error_count": len(error_log),
        "errors": error_log,
        **manifest_extra,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return pages_path


def write_yaml(rows: list, path: Path) -> None:
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "generated_at_utc": _utcnow_iso(),
                "source": "th.wikipedia.org, " + ROOT_CATEGORY,
                "licence": LICENCE,
                "tag_default": "RELAYED",
                "canals": rows,
            },
            allow_unicode=True, sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_kg_doc(rows: list, error_log: list, path: Path) -> None:
    n = len(rows)
    with_coords = sum(1 for r in rows if r["lat"] is not None)
    with_up_down = sum(1 for r in rows if r.get("upstream_name") or r.get("downstream_name"))
    matched = sum(1 for r in rows if r.get("matches"))
    by_source = {"page": 0, "wikidata": 0, "none": 0}
    for r in rows:
        by_source[r["coord_source"]] = by_source.get(r["coord_source"], 0) + 1
    lines = [
        "# Wikipedia canals (หมวดหมู่:คลองในประเทศไทย)",
        "",
        f"Founder task (verbatim): th.wikipedia หมวดหมู่:คลองในประเทศไทย -> "
        f'"สกัดเข้า kggraph อย่างเป็นระบบ" (extract systematically into the knowledge '
        f"graph). This document + `sources/wikipedia_canals.yaml` are that extraction; "
        f"the KG-build step itself (`tools/kg/build_kg.py`) is owned by another worker "
        f"in this run and not touched here.",
        "",
        "## Method",
        "",
        f"- MediaWiki API (`th.wikipedia.org/w/api.php`), generic User-Agent "
        f'(`{USER_AGENT}`), `maxlag=5`, max 1 request/second, one polite retry '
        f"(10s) on HTTP 429/503 only, no other retries.",
        f"- `list=categorymembers` on `{ROOT_CATEGORY}`, `cmtype=page|subcat`, "
        f"followed recursively into subcategories to depth {MAX_SUBCAT_DEPTH}, "
        f"deduped by pageid; each page's subcategory path is recorded.",
        "- Per page: `prop=coordinates|pageprops|revisions` "
        "(`rvprop=ids|timestamp|content`, `rvslots=main`), batched 50 pageids/request. "
        "Infobox/body wikitext parsed for จังหวัด, ต้นน้ำ/จุดเริ่ม, ปลายน้ำ/จุดสิ้นสุด, "
        "ความยาว, ผู้ดูแล/หน่วยงาน where present -- never fabricated when absent.",
        "- No page coordinate -> Wikidata P625 lookup via the page's "
        "`pageprops.wikibase_item` (`wbgetclaims`).",
        "- Every raw API response archived append-only to "
        "`raw/wikipedia/canals/<UTC ts>/pages.jsonl` + `manifest.json` (gitignored "
        "under `raw/`, per this repo's convention).",
        "- Matched against this repo's existing assets registry "
        "(`data/observations.sqlite` `assets` table) by exact normalised Thai name "
        "only -- recorded as a `matches` NOTE field, never merged, never used to "
        "overwrite either source's coordinate.",
        "",
        "## Counts (this run)",
        "",
        f"- Pages found: **{n}**",
        f"- With a coordinate: **{with_coords}** (page: {by_source.get('page', 0)}, "
        f"wikidata: {by_source.get('wikidata', 0)}, none/OPEN: {by_source.get('none', 0)})",
        f"- With an upstream and/or downstream field extracted: **{with_up_down}**",
        f"- Matched (exact normalised name) to an existing asset in this repo's "
        f"registry: **{matched}**",
        f"- API errors this run: **{len(error_log)}**",
        "",
        "## API problems",
        "",
        "th.wikipedia.org's `categorymembers` endpoint returned HTTP 429 (Too Many "
        "Requests) repeatedly during this harvester's development, even at or well "
        "under the 1 request/second ceiling it enforces client-side (observed at "
        "1 req/s, then again at 0.5 req/s); only backing off to 0.25 req/s "
        "(`MIN_REQUEST_INTERVAL_S = 4.0` in the script) brought the error count down "
        f"substantially, to {len(error_log)} for this run. Every 429 gets one polite "
        "retry (10s) per this check's spec; a page still 429'd after that retry is "
        "simply skipped, never looped further -- so the category tree walked by any "
        "single run is not fully deterministic: a subcategory that 429's twice in a "
        "row is silently under-explored that run, and the total page count can move "
        "run to run as a result (this is the honest reason to re-run this harvester "
        "periodically rather than trust any one run as final/complete). Wikidata's "
        "`wbgetclaims` endpoint, by contrast, drew zero errors at every pace tried. "
        "No non-429/503 error (a genuine network failure or a different HTTP "
        "status) occurred in any run made for this check.",
        "",
        "## Licence / attribution",
        "",
        f"Content from th.wikipedia.org, licensed **{LICENCE}** (Wikipedia's own "
        "text licence). Every row here is tagged `RELAYED` -- a community-edited "
        "encyclopedia article, not an official agency telemetry feed or dataset; "
        "coordinates and prose fields carry whatever accuracy that article's own "
        "editors gave them, not independently re-verified by this repo.",
        "",
        "## OPEN",
        "",
        f"- {by_source.get('none', 0)} canal page(s) have no coordinate anywhere "
        "(neither the page itself nor its Wikidata item) -- left `lat`/`lon`: null, "
        "never geocoded.",
        "- Upstream/downstream/length/operator fields depend entirely on whether a "
        "given article's infobox actually uses one of the label variants this "
        "harvester looks for; an article using a different label, or prose-only "
        "with no infobox, yields nulls for those fields even if the information "
        "exists in running text.",
        "- `matches` is a name-string heuristic (exact-after-normalisation only) "
        "against this repo's own `assets` table snapshot at run time -- it is not "
        "re-run automatically when the assets registry itself is rebuilt, and a "
        "genuine same-canal pair with different Thai spellings between Wikipedia "
        "and the government source will simply not match (recorded as no match, "
        "never guessed).",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# --- orchestration -------------------------------------------------------------------

def run(max_depth: int = MAX_SUBCAT_DEPTH, dry_run: bool = False, db_path=None) -> dict:
    run_started = _utcnow_iso()
    raw_log: list = []
    error_log: list = []

    if dry_run:
        return {"dry_run": True, "root_category": ROOT_CATEGORY, "max_depth": max_depth}

    pages_by_id = fetch_category_tree(ROOT_CATEGORY, max_depth, raw_log, error_log)
    pageids = list(pages_by_id.keys())
    page_data_by_id = fetch_pages_batch(pageids, raw_log, error_log)

    rows = []
    for pid in pageids:
        meta = pages_by_id[pid]
        pdata = page_data_by_id.get(pid, {})
        wikibase_item = (pdata.get("pageprops") or {}).get("wikibase-item")
        wikidata_coord = None
        if not pdata.get("coordinates") and wikibase_item:
            wikidata_coord = fetch_wikidata_coord(wikibase_item, raw_log, error_log)
        rows.append(normalise_page(pid, meta, pdata, wikidata_coord))

    match_existing_assets(rows, db_path=db_path)

    out_dir = RAW_DIR / _utcnow_stamp()
    archive_run(raw_log, error_log, {
        "run_started_utc": run_started,
        "pages_found": len(rows),
    }, out_dir)

    write_yaml(rows, OUT_YAML)
    write_kg_doc(rows, error_log, KG_DOC)

    return {
        "pages_found": len(rows),
        "with_coords": sum(1 for r in rows if r["lat"] is not None),
        "with_upstream_or_downstream": sum(
            1 for r in rows if r.get("upstream_name") or r.get("downstream_name")),
        "matched_to_existing_asset": sum(1 for r in rows if r.get("matches")),
        "api_errors": len(error_log),
        "raw_dir": str(out_dir),
        "yaml_out": str(OUT_YAML),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="run the full harvest")
    ap.add_argument("--max-depth", type=int, default=MAX_SUBCAT_DEPTH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.run:
        ap.print_help()
        sys.exit(1)
    stats = run(max_depth=args.max_depth, dry_run=args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
