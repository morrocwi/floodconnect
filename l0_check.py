#!/usr/bin/env python3
"""l0_check.py -- FloodConnect L0 daily check (TRIGGERS.md section 1/2/6).

What this is: the cheapest possible daily "do I need to look closer" check, EXACTLY 3
sources (TMD CAP feed, rain [observed today + 7-day forecast], Z0 level+trend), decided
entirely in code, with ONE line of output a weak/sandboxed AI needs to read (<=50
tokens). This module does NOT run the full H1->H2->H3 zoom (that is a separate, later
step) -- it only answers "QUIET or ESCALATE, and if ESCALATE, toward which first step".

Scope (explicit, per the founder's own MVP-limit ruling): fully wired for `sammakorn`
only (its own Z0 gauge WL.SMK.01/water_id 284, and its own declared rain gauge BKK008 --
see typology/edges/rain_gauge_for.yaml). Every other point (including `ram53`, still
registered as an MVP area elsewhere in this repo) is marked `"experimental": true` in
this module's own output and gets an honest RAIN-NOGAUGE/Z0 gap rather than a guess --
this module never snaps to a nearest station by distance at answer time (KG-only rule).

Design constraints (do not relax without re-reading TRIGGERS.md):
  - UNKNOWN != safe: every missing/stale/failed/unparseable fetch is a trigger (adds a
    reason id), never silently treated as QUIET.
  - KG-only: a station relation (which rain gauge belongs to which point) comes only
    from a declared edge (typology/edges/rain_gauge_for.yaml) -- never a nearest/radius
    pick computed here.
  - No simulation: this module reads live numbers and does arithmetic on them
    (PROP-FLOOD-01 delta_k / 3-state trend); it never runs or calls a forecast/load
    model.
  - TLS: `assets/tmd_intermediate_ca.pem` (the GlobalSign GCC R6 AlphaSSL CA 2025
    intermediate, see evidence/tmd_tls_chain_2026-10-06.md provenance in the founder's
    own trigger research) is ALWAYS passed for verification against tmd.go.th -- never
    `verify=False`/`ssl._create_unverified_context()`.
  - Retain-every-run: every live GET this module makes is archived under
    raw/live/<name>/<UTC timestamp>*.<ext> (raw/ is gitignored, per this repo's existing
    convention) -- append-only, best-effort (a failed archive write is reported, never
    fatal to the check itself).

CLI:
    python3 l0_check.py --at sammakorn
    python3 l0_check.py --at sammakorn --json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
RAW_LIVE_DIR = HERE / "raw" / "live"
CA_BUNDLE_PATH = HERE / "assets" / "tmd_intermediate_ca.pem"

TMD_CAP_FEED_URL = "https://www.tmd.go.th/api/xml/CAP"
OPENMETEO_7D_URL_TMPL = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&daily=precipitation_sum&forecast_days=7&timezone=Asia%2FBangkok")
THAIWATER_RAIN24H_URL = "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/rain_24h"
BMA_STATION_DETAIL_URL_TMPL = "https://weather.bangkok.go.th/water/StationDetail?id={water_id}"

GENERIC_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 floodconnect-l0check/1.0"),
}
BMA_HEADERS = dict(GENERIC_HEADERS, **{
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://weather.bangkok.go.th/water/",
})
REQUEST_TIMEOUT_S = 15

# TMD's own published glossary (VERIFIED 2026-10-06 against tmd.go.th's own page, a
# JS-rendered browser fetch -- see evidence/tmd_rain_intensity_glossary_2026-10-06.md):
# "ฝนหนัก" = 35.1-90.0 mm/24h. This is the LOWER bound, used as the RAIN-NUM trigger.
RAIN_HEAVY_MM_24H = 35.1

# Z0 trend lag, FC_DEFAULT (founder-approved 2026-10-06 default) -- 1 hour.
Z0_TREND_LAG_HOURS = 1.0
# A nearest-point lookup more than this far from the lag target is too loose to trust
# as "that many hours ago" -- refuse (NO_READOUT) rather than guess. Matches the
# tolerance kb.py's own `_bma_series_trend` already uses for its 30-minute lag.
Z0_TREND_TOLERANCE_S = 15 * 60
# BMA's own 2-decimal publication resolution -- this is the SAME epsilon kb.py's own
# `_sandwich_station_reading`/`_bma_series_trend` already use for WL.SMK.01 (not a new
# invented number); TRIGGERS.md still lists a per-station declared epsilon as OPEN
# (item 5) for lack of a separate agency publication -- this module follows the
# existing repo precedent rather than silently diverging from it.
Z0_EPSILON_M = 0.01
# Freshness ceiling, FC_DEFAULT (founder-approved 2026-10-06 default).
MAX_AGE_HOURS = 24.0

# Points this module is wired for. `status: "validated"` = the founder-approved MVP
# path (Sammakorn only, per the task's own scope ruling); every other entry is
# `"experimental"` and deliberately carries no z0/rain_gauge config here (a real one
# must be added as a declared KG edge first, never guessed).
POINTS: dict = {
    "sammakorn": {
        "lat": 13.758235, "lon": 100.676084,
        "province_th": "กรุงเทพมหานคร", "iso": "TH-10",
        "z0": {"source_id": "bma_watermap", "code": "WL.SMK.01", "water_id": 284},
        "rain_gauge": {"thaiwater_station_id": 2, "code": "BKK008",
                        "name_th": "คลองแสนแสบ บางกะปิ"},
        "status": "validated",
    },
    "ram53": {
        "lat": 13.765540125000635, "lon": 100.61909460837903,
        "province_th": "กรุงเทพมหานคร", "iso": "TH-10",
        "z0": None, "rain_gauge": None,
        "status": "experimental",
    },
}

# Broad-region/ambiguous areaDesc tokens TMD CAP items use that are NOT one of the 77
# province names -- TRIGGERS.md section 1A names these as its own examples; the
# official region -> province table is still OPEN (no citable source found), so this
# set is deliberately NOT exhaustive (see that file's OPEN item 7). A token here (and
# ONLY these) yields `match?` (CAP-AREA?) instead of silently matching or silently
# dropping.
_AMBIGUOUS_AREA_TOKENS = frozenset({
    "ภาคกลาง", "ปริมณฑล", "ประเทศไทยตอนบน", "ภาคเหนือ", "ภาคใต้",
    "ภาคตะวันออก", "ภาคตะวันออกเฉียงเหนือ", "ภาคตะวันตก",
})


class L0FetchError(RuntimeError):
    """Raised internally by a fetch helper; callers always catch this and turn it into
    a FAIL/MISS reason -- it must never propagate out of `check()`."""


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: "str | None") -> "datetime.datetime | None":
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _archive(name: str, payload: bytes, suffix: str = "json", key: "str | None" = None) -> "str | None":
    """Append-only raw archive under raw/live/<name>/ -- retain-every-run discipline
    (feedback-floodconnect-retain-every-run.md, extended 2026-10-06: "every keyless API
    call is archived locally ... if the path is unwritable, mark it NOT_SAVED and carry
    on"). Returns the path written, or None on any OSError (never raises)."""
    d = RAW_LIVE_DIR / name
    try:
        d.mkdir(parents=True, exist_ok=True)
        stamp = _utcnow().strftime("%Y-%m-%dT%H%M%SZ")
        fn = f"{stamp}_{key}.{suffix}" if key else f"{stamp}.{suffix}"
        p = d / fn
        p.write_bytes(payload)
        return str(p)
    except OSError:
        return None


_TMD_SSL_CONTEXT: "ssl.SSLContext | None" = None


def _tmd_ssl_context() -> ssl.SSLContext:
    """A default-verifying SSL context (system CA store) PLUS the bundled TMD
    intermediate. Never disables verification -- see module docstring."""
    global _TMD_SSL_CONTEXT
    if _TMD_SSL_CONTEXT is None:
        ctx = ssl.create_default_context()
        if CA_BUNDLE_PATH.exists():
            try:
                ctx.load_verify_locations(cafile=str(CA_BUNDLE_PATH))
            except ssl.SSLError:
                pass  # falls back to system-store-only verification, never to no verification
        _TMD_SSL_CONTEXT = ctx
    return _TMD_SSL_CONTEXT


def _get(url: str, *, headers: "dict | None" = None, context: "ssl.SSLContext | None" = None,
          timeout: float = REQUEST_TIMEOUT_S) -> "tuple[int, bytes]":
    """One GET, no retry (this workspace's host-safety rule). Raises L0FetchError on any
    network/HTTP-transport failure; a non-200 status is returned normally (caller
    decides what that means) rather than raised."""
    req = urllib.request.Request(url, headers=headers or GENERIC_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() if e.fp else b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise L0FetchError(str(e)) from e


def _resolve_point(at: str) -> "tuple[str, dict]":
    """'<area_id>' | 'lat,lon' -> (point_id, point_config). A bare lat,lon that isn't a
    known point gets a coordinate-derived point_id and an all-experimental config
    (no z0/rain_gauge -- those are declared per named point only, never guessed from
    coordinates)."""
    if at in POINTS:
        return at, POINTS[at]
    try:
        lat_s, lon_s = at.split(",", 1)
        lat, lon = float(lat_s), float(lon_s)
    except ValueError as e:
        raise ValueError(f"'--at' is neither a known point id ({', '.join(POINTS)}) "
                          f"nor a parseable 'lat,lon': {at!r}") from e
    return f"pt:{lat},{lon}", {
        "lat": lat, "lon": lon, "province_th": None, "iso": None,
        "z0": None, "rain_gauge": None, "status": "experimental",
    }


# ---------------------------------------------------------------------------
# 1A. TMD CAP
# ---------------------------------------------------------------------------

_CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


def _cap_parse_feed(xml_bytes: bytes) -> "list[dict] | None":
    """Returns [{"link", "guid", "title", "pubdate"}, ...] for every <item> in the RSS
    feed, in feed order, or None on any parse failure (no <channel> at all, malformed
    XML) -- TRIGGERS.md CAP-FAIL. `pubDate` is carried through but MUST NOT be used for
    anything time-sensitive (MEASURED 2026-10-06: it runs 7h behind the item's own
    `sent`, mislabelled +0700)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    channel = root.find("channel")
    if channel is None:
        return None
    items = []
    for item in channel.findall("item"):
        link = item.findtext("link")
        if not link:
            continue
        items.append({
            "link": link.strip(),
            "guid": (item.findtext("guid") or "").strip(),
            "title": (item.findtext("title") or "").strip(),
            "pubdate": (item.findtext("pubDate") or "").strip(),
        })
    return items


def _cap_parse_item(xml_bytes: bytes) -> "dict | None":
    """One CAP 1.2 <alert> item -> {"identifier","sender","sent","status","msgType",
    "references","infos":[{"event","severity","urgency","certainty","effective",
    "expires","areaDesc","geocodes":[(valueName,value),...],"responseType",
    "instruction"}]}. Returns None on parse failure (no root/namespace mismatch)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    ns = _CAP_NS

    def _t(el, tag):
        return el.findtext(f"cap:{tag}", namespaces=ns) if el is not None else None

    identifier = _t(root, "identifier")
    if identifier is None:
        return None
    infos = []
    for info in root.findall("cap:info", ns):
        geocodes = [
            ((_t(g, "valueName") or "").strip(), (_t(g, "value") or "").strip())
            for g in info.findall("cap:geocode", ns)
        ]
        area_descs = [(_t(a, "areaDesc") or "").strip() for a in info.findall("cap:area", ns)]
        # CAP's <area> wraps <areaDesc> + its own <geocode> children in CAP 1.2, but
        # this feed's real items (evidence/*.xml) put geocode directly under <info> in
        # some samples and under <area> in others -- read both locations rather than
        # assume one schema variant.
        for a in info.findall("cap:area", ns):
            for g in a.findall("cap:geocode", ns):
                geocodes.append(((_t(g, "valueName") or "").strip(), (_t(g, "value") or "").strip()))
        infos.append({
            "language": _t(info, "language"),
            "event": _t(info, "event"),
            "severity": _t(info, "severity"),
            "urgency": _t(info, "urgency"),
            "certainty": _t(info, "certainty"),
            "effective": _t(info, "effective"),
            "expires": _t(info, "expires"),
            "sent_fallback": _t(root, "sent"),
            "areaDesc": " ".join(d for d in area_descs if d),
            "geocodes": geocodes,
            "responseType": _t(info, "responseType"),
            "instruction": _t(info, "instruction") or "",
        })
    return {
        "identifier": identifier,
        "sender": _t(root, "sender"),
        "sent": _t(root, "sent"),
        "status": _t(root, "status"),
        "msgType": _t(root, "msgType"),
        "references": _t(root, "references"),
        "infos": infos,
    }


def _cap_match(info: dict, iso: "str | None", province_th: "str | None") -> "str | None":
    """Returns "match", "match?", or None, per TRIGGERS.md section 1A's `match`/`match?`
    definitions. `iso`/`province_th` None (no province resolved for this point) never
    matches -- it is not this function's job to guess a province from lat/lon."""
    if iso is None and province_th is None:
        return None
    geocode_isos = {v for name, v in info["geocodes"] if name == "ISO3166-2"}
    other_geocode = any(name != "ISO3166-2" for name, _v in info["geocodes"])
    if iso is not None and iso in geocode_isos:
        return "match"
    area_desc = info.get("areaDesc") or ""
    tokens = area_desc.split()
    if province_th is not None:
        for tok in tokens:
            if tok == province_th:
                return "match"
            if tok.startswith(province_th + "และ"):
                return "match"
    if any(tok in _AMBIGUOUS_AREA_TOKENS for tok in tokens):
        return "match?"
    if other_geocode:
        return "match?"
    if not info["geocodes"] and not area_desc:
        return "match?"
    return None


_cap_item_cache: dict = {}


def _cap_fetch_item(link: str) -> "bytes | None":
    """GET once per URL, cached forever (a CAP item file never changes after issue, per
    TRIGGERS.md) -- in-process memo PLUS an on-disk cache under
    raw/live/tmd_cap_items/<sha256(url)[:16]>.xml so a later run (new process) does not
    refetch it either. Returns None on any fetch failure."""
    if link in _cap_item_cache:
        return _cap_item_cache[link]
    disk_key = _sha256(link.encode("utf-8"))[:16]
    disk_path = RAW_LIVE_DIR / "tmd_cap_items" / f"{disk_key}.xml"
    if disk_path.exists():
        try:
            body = disk_path.read_bytes()
            _cap_item_cache[link] = body
            return body
        except OSError:
            pass
    try:
        status, body = _get(link, context=_tmd_ssl_context())
    except L0FetchError:
        return None
    if status != 200:
        return None
    try:
        disk_path.parent.mkdir(parents=True, exist_ok=True)
        disk_path.write_bytes(body)
    except OSError:
        pass  # cache write failed -- still usable this run, just refetched next time
    _cap_item_cache[link] = body
    return body


def evaluate_cap(point: dict) -> dict:
    """TRIGGERS.md section 1A. Returns {"reasons": [...], "signals": [...],
    "phrases": {id: phrase}, "colour_floor": None|"YELLOW", "latest_sent": str|None}."""
    out = {"reasons": [], "signals": [], "phrases": {}, "colour_floor": None, "latest_sent": None}
    try:
        status, feed_body = _get(TMD_CAP_FEED_URL, context=_tmd_ssl_context())
    except L0FetchError:
        out["reasons"].append("CAP-FAIL")
        out["phrases"]["CAP-FAIL"] = "อ่านประกาศ TMD ไม่ได้"
        return out
    _archive("tmd_cap_feed", feed_body, "xml")
    if status != 200:
        out["reasons"].append("CAP-FAIL")
        out["phrases"]["CAP-FAIL"] = "อ่านประกาศ TMD ไม่ได้"
        return out
    items = _cap_parse_feed(feed_body)
    if items is None:
        out["reasons"].append("CAP-FAIL")
        out["phrases"]["CAP-FAIL"] = "อ่านประกาศ TMD ไม่ได้"
        return out

    now = _utcnow()
    iso, province_th = point.get("iso"), point.get("province_th")
    latest_sent = None
    cancelled_ids = set()
    parsed_items = []
    for feed_item in items:
        item_body = _cap_fetch_item(feed_item["link"])
        if item_body is None:
            out["reasons"].append("CAP-FAIL")
            out["phrases"]["CAP-FAIL"] = "อ่านประกาศ TMD ไม่ได้"
            continue
        alert = _cap_parse_item(item_body)
        if alert is None:
            out["reasons"].append("CAP-FAIL")
            out["phrases"]["CAP-FAIL"] = "อ่านประกาศ TMD ไม่ได้"
            continue
        # live run, 2026-10-06: the RSS <item><title> is TMD's own
        # Thai headline (e.g. "ฝนตกหนัก") -- the CAP <info><event> field, even on
        # the th-TH <info> block, is published in ENGLISH ("Heavy Rain"/"Very Heavy
        # Rain", MEASURED 2026-10-06 against a live capture). Carrying the feed
        # item's own Thai title through lets every phrase below use the agency's
        # actual Thai wording -- English is kept ONLY as a last-resort fallback
        # (feed title missing/empty), per the founder's own rule.
        alert["feed_title_th"] = feed_item.get("title") or None
        sent_dt = _parse_iso(alert.get("sent"))
        if sent_dt is not None and (latest_sent is None or sent_dt > latest_sent[0]):
            latest_sent = (sent_dt, alert.get("sent"))
        if alert.get("msgType") == "Cancel" and alert.get("references"):
            for ref in alert["references"].split():
                ref_id = ref.split(",")[0] if "," in ref else ref
                cancelled_ids.add(ref_id)
        parsed_items.append(alert)

    if latest_sent is not None:
        out["latest_sent"] = latest_sent[1]
        out["signals"].append(f"CAP@{latest_sent[1]}")

    best_rank = -1  # CAP-SEV(3) > CAP-ANY(2) > CAP-AREA?(1) > CAP-NEXT(0)
    for alert in parsed_items:
        if alert["identifier"] in cancelled_ids:
            continue
        if alert.get("status") != "Actual" or alert.get("msgType") not in ("Alert", "Update"):
            continue
        for info in alert["infos"]:
            eff = _parse_iso(info.get("effective")) or _parse_iso(alert.get("sent"))
            exp = _parse_iso(info.get("expires"))
            active = eff is not None and now >= eff and (exp is None or now < exp)
            upcoming = eff is not None and now < eff
            if not active and not upcoming:
                continue
            m = _cap_match(info, iso, province_th)
            if m is None:
                continue
            severity = (info.get("severity") or "").strip()
            # live run, 2026-10-06: prefer the feed's own Thai title; fall back to a
            # th-language <info> block's own `event` (if some future feed item
            # ever actually carries a Thai event string); English `event` is the
            # last resort, only when no Thai is available at all.
            event = (alert.get("feed_title_th")
                     or (info.get("event") if (info.get("language") or "").lower().startswith("th") else None)
                     or info.get("event") or "เตือน")
            prov = province_th or "พื้นที่คุณ"
            exp_hhmm = exp.astimezone(datetime.timezone(datetime.timedelta(hours=7))).strftime("%H:%M") if exp else "ไม่ระบุ"
            eff_hhmm = eff.astimezone(datetime.timezone(datetime.timedelta(hours=7))).strftime("%H:%M") if eff else "ไม่ระบุ"
            if active and m == "match" and severity in ("Severe", "Extreme"):
                rid, phrase, rank = "CAP-SEV", f"TMD เตือน{event} {prov} ถึง{exp_hhmm}", 3
            elif active and m == "match":
                rid, phrase, rank = "CAP-ANY", f"TMD แจ้ง{event} {prov} ถึง{exp_hhmm}", 2
            elif m == "match?":
                rid, phrase, rank = "CAP-AREA?", f"TMD เตือน{(info.get('areaDesc') or '')[:20]} อาจรวมพื้นที่คุณ", 1
            elif upcoming and m == "match":
                rid, phrase, rank = "CAP-NEXT", f"TMD เตือนล่วงหน้า เริ่ม{eff_hhmm}", 0
            else:
                continue
            if rid not in out["reasons"]:
                out["reasons"].append(rid)
            out["phrases"][rid] = phrase
            out["signals"].append(f"{rid}@{alert.get('sent')}")
            if rid == "CAP-SEV" and rank > best_rank:
                out["colour_floor"] = "YELLOW"
            if active and (info.get("responseType") == "Evacuate"
                           or re.search(r"\bอพยพ\b", info.get("instruction") or "")):
                # A real official evacuation instruction is a floor higher than
                # colour_floor=YELLOW -- surfaced as its own reason so a caller/zoom
                # step treats it as the H3-ORDER floor (TRIGGERS.md section 1A last
                # bullet). No sample CAP item carries this yet (TRIGGERS OPEN item 11)
                # -- this branch is unexercised by live data so far, kept conservative.
                if "H3-ORDER" not in out["reasons"]:
                    out["reasons"].append("H3-ORDER")
                out["phrases"]["H3-ORDER"] = phrase
            best_rank = max(best_rank, rank)
    return out


# ---------------------------------------------------------------------------
# 1B. Rain
# ---------------------------------------------------------------------------

def evaluate_rain(point: dict) -> dict:
    """TRIGGERS.md section 1B. Returns {"reasons": [...], "signals": [...],
    "phrases": {id: phrase}, "observed": {...}|None, "forecast": {...}|None}."""
    out = {"reasons": [], "signals": [], "phrases": {}, "observed": None, "forecast": None}
    gauge = point.get("rain_gauge")
    if gauge is None:
        out["reasons"].append("RAIN-NOGAUGE")
        out["phrases"]["RAIN-NOGAUGE"] = "ไม่มีสถานีฝนที่ประกาศ"
        return out

    try:
        status, body = _get(THAIWATER_RAIN24H_URL)
    except L0FetchError:
        out["reasons"].append("RAIN-FAIL")
        out["phrases"]["RAIN-FAIL"] = "อ่านฝนวันนี้ไม่ได้"
        return out
    _archive("thaiwater_rain_24h", body, "json")
    if status != 200:
        out["reasons"].append("RAIN-FAIL")
        out["phrases"]["RAIN-FAIL"] = "อ่านฝนวันนี้ไม่ได้"
        return out
    try:
        payload = json.loads(body)
    except ValueError:
        out["reasons"].append("RAIN-FAIL")
        out["phrases"]["RAIN-FAIL"] = "อ่านฝนวันนี้ไม่ได้"
        return out
    row = None
    for r in payload.get("data") or []:
        st = r.get("station") or {}
        if st.get("id") == gauge.get("thaiwater_station_id") or st.get("tele_station_oldcode") == gauge.get("code"):
            row = r
            break
    if row is None:
        out["reasons"].append("RAIN-FAIL")
        out["phrases"]["RAIN-FAIL"] = "อ่านฝนวันนี้ไม่ได้"
        return out
    mm_24h = row.get("rain_24h")
    observed_at_local = row.get("rainfall_datetime")  # "YYYY-MM-DD HH:MM", Asia/Bangkok
    out["observed"] = {"mm_24h": mm_24h, "observed_at_local": observed_at_local,
                        "station_code": gauge.get("code")}
    bkk_today = (_utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    obs_date = (observed_at_local or "")[:10]
    hhmm = (observed_at_local or "")[11:16] or "--:--"
    if mm_24h is None or not observed_at_local:
        out["reasons"].append("RAIN-FAIL")
        out["phrases"]["RAIN-FAIL"] = "อ่านฝนวันนี้ไม่ได้"
        return out
    if obs_date != bkk_today:
        out["reasons"].append("RAIN-STALE")
        out["phrases"]["RAIN-STALE"] = f"ฝนวันนี้ยังไม่มีค่า ล่าสุด{obs_date[5:]} {hhmm}"
    out["signals"].append(f"RAIN@{observed_at_local}")
    rain_num_hit = mm_24h is not None and mm_24h >= RAIN_HEAVY_MM_24H

    # 7-day forecast (Open-Meteo, keyless, single model).
    url = OPENMETEO_7D_URL_TMPL.format(lat=point["lat"], lon=point["lon"])
    try:
        status, body = _get(url)
    except L0FetchError:
        out["reasons"].append("FCST-FAIL")
        out["phrases"]["FCST-FAIL"] = "อ่านพยากรณ์ฝนไม่ได้"
        return out
    _archive("openmeteo_7d", body, "json")
    if status != 200:
        out["reasons"].append("FCST-FAIL")
        out["phrases"]["FCST-FAIL"] = "อ่านพยากรณ์ฝนไม่ได้"
        return out
    try:
        fpayload = json.loads(body)
        times = fpayload["daily"]["time"]
        values = fpayload["daily"]["precipitation_sum"]
    except (ValueError, KeyError, TypeError):
        out["reasons"].append("FCST-FAIL")
        out["phrases"]["FCST-FAIL"] = "อ่านพยากรณ์ฝนไม่ได้"
        return out
    if not times or len(times) != len(values) or any(v is None for v in values):
        out["reasons"].append("FCST-FAIL")
        out["phrases"]["FCST-FAIL"] = "อ่านพยากรณ์ฝนไม่ได้"
        return out
    out["forecast"] = {"days": list(zip(times, values))}
    max_idx = max(range(len(values)), key=lambda i: values[i])
    out["signals"].append(f"FCST_MAX@{times[max_idx]}")
    if any(v >= RAIN_HEAVY_MM_24H for v in values):
        rain_num_hit = True
    if rain_num_hit:
        out["reasons"].append("RAIN-NUM")
        if mm_24h is not None and mm_24h >= RAIN_HEAVY_MM_24H:
            out["phrases"]["RAIN-NUM"] = f"ฝนหนัก{mm_24h}มม.@{hhmm}"
        else:
            out["phrases"]["RAIN-NUM"] = f"พยากรณ์ฝนหนัก{values[max_idx]}มม.@{times[max_idx][5:]}"
    return out


# ---------------------------------------------------------------------------
# 1C. Z0
# ---------------------------------------------------------------------------

def _z0_nearest_point(points: "list[dict]", target_dt: datetime.datetime) -> "dict | None":
    best, best_gap = None, None
    for p in points:
        p_dt = _parse_iso(p.get("t_utc"))
        if p_dt is None:
            continue
        gap = abs((p_dt - target_dt).total_seconds())
        if best_gap is None or gap < best_gap:
            best, best_gap = p, gap
    if best is None or best_gap > Z0_TREND_TOLERANCE_S:
        return None
    return best


_BMA_DETAIL_HTML_CACHE: dict = {}  # water_id -> (monotonic_fetched_at, status, body)
# live run, 2026-10-06 (22s wall time): `kb.py answer` now also
# calls `check()` on an ESCALATE/RISING trigger (kb.build_answer) in
# the SAME process that may have JUST fetched this exact BMA StationDetail page
# through a completely separate code path (`collect.fetch_bma_station_series`,
# for the Sandwich's own Z0 series) -- without this, that is a genuine repeated
# GET to the same URL, seconds apart, in one answer. A short in-process-only TTL
# (well under the station's own ~5-min update step, so it is NEVER mistaken for a
# fresh fetch next run or across processes) de-dupes exactly that pattern, never
# the real browser-visible 5-min data herself -- a cache MISS still fires a real
# GET exactly as before.
_BMA_DETAIL_CACHE_TTL_S = 20.0


def evaluate_z0(point: dict) -> dict:
    """TRIGGERS.md section 1C, for a `bma_watermap`-sourced Z0 (this module's only
    wired source today -- a `thaiwater_waterlevel`-sourced Z0, with its own
    agency status words, is OPEN/future scope, see module docstring). Returns
    {"reasons": [...], "signals": [...], "phrases": {id: phrase}, "h": float|None,
    "trend": str, "observed_at_utc": str|None, "eta": dict|None}. `eta`
    (PROP-FLOOD-02, linear, two windows -- not PROP-FLOOD-11, which is registered but
    not implemented in this release) is only ever set when `trend` is RISING and a
    warning/critical threshold exists --
    None otherwise, including UNKNOWN trend (no series to compute a slope from)."""
    out = {"reasons": [], "signals": [], "phrases": {}, "h": None,
           "trend": "UNKNOWN", "observed_at_utc": None, "eta": None}
    z0 = point.get("z0")
    if z0 is None:
        out["reasons"].append("Z0-MISS")
        out["phrases"]["Z0-MISS"] = "อ่านระดับน้ำจุดคุณไม่ได้"
        return out

    import parsers as _parsers  # local import: keeps this module importable stdlib-only
    import tools.harvest.bma_station_detail_draft as _bsd

    url = BMA_STATION_DETAIL_URL_TMPL.format(water_id=z0["water_id"])
    import time as _time_mod
    cached = _BMA_DETAIL_HTML_CACHE.get(z0["water_id"])
    if cached is not None and (_time_mod.monotonic() - cached[0]) < _BMA_DETAIL_CACHE_TTL_S:
        status, body = cached[1], cached[2]
    else:
        try:
            status, body = _get(url, headers=BMA_HEADERS)
        except L0FetchError:
            out["reasons"].append("Z0-MISS")
            out["phrases"]["Z0-MISS"] = "อ่านระดับน้ำจุดคุณไม่ได้"
            return out
        _BMA_DETAIL_HTML_CACHE[z0["water_id"]] = (_time_mod.monotonic(), status, body)
        _archive("bma_station_detail_l0", body, "html", key=f"id{z0['water_id']}")
    if status != 200:
        out["reasons"].append("Z0-MISS")
        out["phrases"]["Z0-MISS"] = "อ่านระดับน้ำจุดคุณไม่ได้"
        return out
    html = body.decode("utf-8", errors="replace")

    fields = _bsd.parse_station_detail_fields(html)

    def _f(key):
        raw = fields.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    warning, critical = _f("txt_warning"), _f("txt_critical")
    series = _parsers.parse_bma_station_series(html)
    if series.get("status") == "EMPTY" or series.get("chosen_run") is None:
        out["reasons"].append("Z0-MISS")
        out["phrases"]["Z0-MISS"] = "อ่านระดับน้ำจุดคุณไม่ได้"
        return out
    run_points = series["runs"][series["chosen_run"]]
    if not run_points:
        out["reasons"].append("Z0-MISS")
        out["phrases"]["Z0-MISS"] = "อ่านระดับน้ำจุดคุณไม่ได้"
        return out
    last = run_points[-1]
    h_now = round(last["v"], 2)
    observed_at_now = last["t_utc"]
    now_dt = _parse_iso(observed_at_now)
    out["h"], out["observed_at_utc"] = h_now, observed_at_now

    now = _utcnow()
    if now_dt is None:
        out["reasons"].append("Z0-MISS")
        out["phrases"]["Z0-MISS"] = "อ่านระดับน้ำจุดคุณไม่ได้"
        return out
    age_h = (now - now_dt).total_seconds() / 3600.0
    hhmm_local = (now_dt + datetime.timedelta(hours=7)).strftime("%H:%M")
    if age_h > MAX_AGE_HOURS:
        out["reasons"].append("Z0-STALE")
        out["phrases"]["Z0-STALE"] = f"ระดับน้ำจุดคุณเก่า {age_h:.0f}ชม."
    out["signals"].append(f"Z0@{observed_at_now}")

    if warning is None and critical is None:
        out["reasons"].append("Z0-NOTHR")
        out["phrases"]["Z0-NOTHR"] = "จุดคุณไม่มีเกณฑ์ทางการ"
    if critical is not None and h_now >= critical:
        out["reasons"].append("Z0-CRIT")
        out["phrases"]["Z0-CRIT"] = f"จุดคุณวิกฤต {h_now}ม.>={critical}"
    elif warning is not None and h_now >= warning:
        out["reasons"].append("Z0-WARN")
        out["phrases"]["Z0-WARN"] = f"จุดคุณถึงเกณฑ์เตือน {h_now}ม."

    target_dt = now_dt - datetime.timedelta(hours=Z0_TREND_LAG_HOURS)
    prev_point = _z0_nearest_point(run_points[:-1], target_dt)
    if prev_point is None:
        out["reasons"].append("Z0-NOTREND")
        out["phrases"]["Z0-NOTREND"] = "แนวโน้มจุดคุณไม่ทราบ"
        out["trend"] = "UNKNOWN"
    else:
        import floodconnect_model
        h_prev = round(prev_point["v"], 2)
        trend_info = floodconnect_model.trend_state(h_now, h_prev, epsilon=Z0_EPSILON_M)
        out["trend"] = trend_info["trend"]
        if trend_info["trend"] == "RISING":
            out["reasons"].append("Z0-RISE")
            eta_phrase = None
            if warning is not None or critical is not None:
                prev_dt = _parse_iso(prev_point.get("t_utc"))
                long_hours = ((now_dt - prev_dt).total_seconds() / 3600.0
                              if prev_dt is not None else None)
                # short-lag point: this series' own most recent reading
                # strictly BEFORE `now_dt` (never a fixed array index -- the
                # same "nearest real point, not an assumed step" rule the
                # long-lag `_z0_nearest_point` lookup above already follows).
                short_prev_pt, short_prev_dt = None, None
                for p in run_points:
                    p_dt = _parse_iso(p.get("t_utc"))
                    if p_dt is not None and p_dt < now_dt and (
                            short_prev_dt is None or p_dt > short_prev_dt):
                        short_prev_dt, short_prev_pt = p_dt, p
                short_hours = ((now_dt - short_prev_dt).total_seconds() / 3600.0
                               if short_prev_dt is not None else None)
                h_short_prev = round(short_prev_pt["v"], 2) if short_prev_pt else None
                out["eta"] = floodconnect_model.rise_eta_hours_range(
                    h_now, h_short_prev, short_hours, h_prev, long_hours,
                    theta_warn=warning, theta_crit=critical,
                    epsilon=Z0_EPSILON_M, pump_state="UNCHANGED")
                # prefer critical's own ETA (the more decision-relevant
                # threshold) over warning's when both compute a real range.
                for _tier in ("critical", "warning"):
                    _tier_eta = (out["eta"] or {}).get(_tier) or {}
                    if _tier_eta.get("status") == "OK":
                        lo, hi = _tier_eta["range_h"]
                        eta_phrase = f"น้ำขึ้นถึงเกณฑ์ใน{lo:g}-{hi:g}ชม."
                        break
            # the short ETA, when computable, replaces the raw delta/lag
            # phrase -- both describe the same RISING fact, and the line this
            # phrase feeds has a hard <=50-token budget (see `check()` below).
            out["phrases"]["Z0-RISE"] = eta_phrase or (
                f"จุดคุณน้ำขึ้น +{trend_info['delta']:.2f}ม./{Z0_TREND_LAG_HOURS:.0f}ชม.")
    out["_display_hhmm"] = hhmm_local
    return out


# ---------------------------------------------------------------------------
# section 2 (QUIET) + section 6 (one-line output)
# ---------------------------------------------------------------------------

# Priority order for picking the "top" id to show on an escalate line (CARD > DRILL+H2
# > H2 > H1, per TRIGGERS.md's own `Action` legend "CARD > H2 > H1" plus the
# CAP-SEV-specific "DRILL เข้า H2 เสมอ" rule) -- highest first.
_ID_RANK = {
    "Z0-CRIT": 100,
    "H3-ORDER": 95,
    "CAP-SEV": 90,
    "Z0-WARN": 80,
    "Z0-THRCONF": 60, "Z0-UNMAPPED": 60, "Z0-MISS": 60, "Z0-STALE": 55,
    "Z0-NOTHR": 50, "Z0-NOTREND": 50, "Z0-RISE": 45,
    "RAIN-FAIL": 40, "RAIN-STALE": 40, "RAIN-NOGAUGE": 35, "FCST-FAIL": 35,
    "RAIN-NUM": 30,
    "CAP-ANY": 25, "CAP-AREA?": 20, "CAP-NEXT": 15, "CAP-FAIL": 40,
}
_ID_ACTION = {
    "Z0-CRIT": "CARD", "H3-ORDER": "CARD",
    "CAP-SEV": "DRILL+H2", "Z0-WARN": "H2",
}


def _action_for(top_id: str) -> str:
    return _ID_ACTION.get(top_id, "H1")


def check(at: str) -> dict:
    """Runs all 3 sources (CAP, rain, Z0) for one point and returns the full
    `fc.l0_check.v1` dict -- schema per TRIGGERS.md section 1/2/6 plus this module's
    own `line`/`flag`/`action` fields. Never raises: every fetch failure becomes a
    reason id (UNKNOWN != safe) inside the returned dict."""
    point_id, point = _resolve_point(at)
    cap = evaluate_cap(point)
    rain = evaluate_rain(point)
    z0 = evaluate_z0(point)

    reasons = list(cap["reasons"]) + list(rain["reasons"]) + list(z0["reasons"])
    signals = list(cap["signals"]) + list(rain["signals"]) + list(z0["signals"])
    phrases = {**cap["phrases"], **rain["phrases"], **z0["phrases"]}
    quiet = len(reasons) == 0  # section 2: QUIET iff no trigger fired at all

    colour_floor = cap.get("colour_floor")
    if reasons:
        top_id = max(reasons, key=lambda r: _ID_RANK.get(r, 0))
        action = _action_for(top_id)
        phrase = phrases.get(top_id, top_id)
        src_time = None
        for sig in signals:
            if sig.startswith(top_id.split(":")[0] + "@") or sig.startswith(top_id + "@"):
                src_time = sig.split("@", 1)[1]
                break
        other_ids = [r for r in reasons if r != top_id]
        # founder ruling 2026-10-06: this one line has a HARD <=50
        # o200k-token cap -- a point with several reasons (e.g. ram53's own
        # CAP-SEV + RAIN-NOGAUGE + Z0-MISS) used to spell out every id, which the
        # top_id's own phrase can already push past the cap on its own. The line
        # names only the TOP id (plus a bare "+N" count when others exist) -- the
        # full `reasons` list is never lost, it is still in the returned dict and
        # in `--json`, just not repeated inside this one compact line.
        id_field = top_id if not other_ids else f"{top_id}+{len(other_ids)}"
        line = f"ขยับ:ใช่|{id_field}|{phrase}|{(src_time or '')}|→{action}"
    else:
        top_id, action = None, None
        obs = rain.get("observed") or {}
        fcst = rain.get("forecast") or {}
        fdays = fcst.get("days") or []
        max_day = max(fdays, key=lambda d: d[1]) if fdays else (None, None)
        z0_hhmm = z0.get("_display_hhmm") or "--:--"
        trend_sym = {"RISING": "↑", "STABLE": "=", "FALLING": "↓"}.get(
            {"RISING": "RISING", "FALLING": "FALLING", "FLAT": "STABLE"}.get(z0.get("trend"), "UNKNOWN"), "=")
        cap_sent = cap.get("latest_sent") or ""
        cap_disp = (cap_sent[5:16].replace("T", " ") if cap_sent else "ไม่มี")
        line = (f"ปกติ|CAP-:{cap_disp}"
                f"|ฝน{obs.get('mm_24h')}มม.@{(obs.get('observed_at_local') or '')[11:16]}"
                f"|7ว max{max_day[1]}@{(max_day[0] or '')[5:]}"
                f"|Z0 {z0.get('h')}ม.{trend_sym}@{z0_hhmm}")

    return {
        "schema": "fc.l0_check.v1",
        "at": at, "point_id": point_id,
        "experimental": point.get("status") != "validated",
        "generated_at": _utcnow_iso(),
        "flag": "QUIET" if quiet else "ESCALATE",
        "reasons": reasons, "signals": signals, "phrases": phrases,
        "colour_floor": colour_floor,
        "action": action,
        "line": line,
        "cap": {k: v for k, v in cap.items() if k not in ("phrases",)},
        "rain": {k: v for k, v in rain.items() if k not in ("phrases",)},
        "z0": {k: v for k, v in z0.items() if k not in ("phrases", "_display_hhmm")},
    }


def _compact_check_json(result: dict) -> dict:
    """live run, 2026-10-06: the CLI `--json` printer used to dump
    `check()`'s FULL dict (every source's own `cap`/`rain`/`z0` sub-block, every
    `phrases` entry) -- MEASURED 603 o200k tokens on a live ESCALATE run, far past
    this module's own ``<=50 tokens`` one-line design budget (module docstring).
    `check()` itself (watchlist.py / tools/mcp/floodconnect_mcp.py's own callers,
    which need the full detail to build a watch_update/alert_event) is UNCHANGED --
    this trims ONLY what the CLI's own `--json` flag prints to stdout, to exactly
    the 5 fields a caller reading the printed JSON actually needs: `line` (the same
    one-line summary --json's non-flag sibling prints), `flag`, `colour_floor`,
    `reasons`, and `times` (the signal timestamps, `"<reason_id>@<iso>"`, already
    carried by `signals` -- never a second, divergent time encoding)."""
    # Only each reason's OWN time, ONE per reason id (never every matching signal --
    # a feed with several items sharing one reason id, e.g. several CAP-SEV alerts,
    # used to repeat that same id's time once per item; a quiet run's full signals
    # list was the single biggest contributor to the pre-fix 603-token dump).
    times = []
    for rid in result["reasons"]:
        for sig in result["signals"]:
            if sig.startswith(rid + "@"):
                times.append(sig)
                break
    return {
        "flag": result["flag"], "colour_floor": result.get("colour_floor"),
        "reasons": result["reasons"], "times": times,
        "line": result["line"],
    }


def cmd_check(args) -> int:
    result = check(args.at)
    if getattr(args, "json", False):
        print(json.dumps(_compact_check_json(result), ensure_ascii=False, separators=(",", ":")))
    else:
        print(result["line"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", required=True, help="area_id (sammakorn, ram53) or 'lat,lon'")
    ap.add_argument("--json", action="store_true", help="print the full JSON result")
    args = ap.parse_args(argv)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
