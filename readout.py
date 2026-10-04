#!/usr/bin/env python3
"""
Sammakorn live flood-context readout -- reads `data/observations.sqlite` (populated by
`collect.py`) and writes a plain-Markdown + JSON snapshot centred on one point.

NO flood-risk score or formula is computed anywhere in this file (this workspace's
equation discipline / the project's own instruction for this check) -- every row is either
a MEASURED reading, a RELAYED official forecast/report figure, or explicitly marked OPEN
(missing). Contradictions between sources are listed side by side and never resolved to
a single "true" value (per the maintainers' own framing: Thai agencies compete and disagree,
so this readout must show that, not paper over it).

CLI:
    python3 readout.py --centre 13.758235 100.676084
    python3 readout.py --centre 13.758235 100.676084 --radius-km 5 --date 2026-09-26
"""
import argparse
import datetime
import json
from pathlib import Path

import live_water_level as lwl
import store
from live_water_level import haversine_km

HERE = Path(__file__).parent
OUTPUT_DIR = HERE / "output"

# Fixed Sammakorn "nodes" per the orchestrator's design -- BMA station codes, not derived
# from a radius search, since these specific stations are the ones a human already
# identified as relevant to this neighbourhood (เขตสะพานสูง / Sammakorn village).
SAMMAKORN_NODES = {
    "north (แสนแสบ)": ["WL.SSB.07", "WL.SSB.08"],
    "south": ["WL.TPK.03", "WL.PWT.03", "WL.HMK.01"],
}
SAMMAKORN_PUMPS = ["ST.SPS.01", "ST.SPS.02", "ST.SPS.03", "ST.SPS.04"]

# fix (2026-10-04, re-fix after the first attempt was found to still be insufficient
# -- 40km-of-central-Bangkok + canal-name substring match -- still let a FAR gate
# decide any Bangkok-area point, e.g. Thonburi/Don Mueang/a point near Lat Krabang all
# got RED from ปตร.คลองประเวศฯ-ลาดกระบัง or ปตร.คลองแสนแสบ-มีนบุรี, both `canal_outer`
# ("ระดับน้ำพื้นที่ กทม. ภายนอกคันปองกันน้ำทวม" -- OUTSIDE the flood-protection dike)
# rows that measure a different hydraulic regime than what a resident inside the dike
# experiences): the bulletin's own canal rows carry no lat/lon (collect_dds_daily_pdf's
# documented limitation, see its own docstring), so this file now keeps an EXPLICIT
# gate-name -> (lat, lon) table below, sourced from this repo's own
# `sources/canal_normal_levels.yaml` (a per-canal dry-season-median project, itself
# MEASURED-history from a real api-v3.thaiwater.net station fetch -- see that file's own
# header for the archived raw payload each row cites). A bulletin row now decides
# `current_local_state` only if BOTH hold:
#   1. it is a `canal_inner` ("ภายในคันปองกันน้ำทวม") row -- every `canal_outer` row is
#      excluded from the decision unconditionally, regardless of distance, because it is
#      a different hydraulic zone, not merely a distant one (see `_DDS_CANAL_OUTER_SECTION`
#      below).
#   2. its OWN gate has a sourced coordinate in `_DDS_GATE_COORDS` (keyed by
#      `_normalize_name` of the bulletin's own station name) AND that coordinate lies
#      within `radius_km` of the query centre -- the same radius the caller already
#      asked for, not a separate hardcoded one.
# A gate this repo has no sourced coordinate for (most of them -- BMA has never
# published a canal-gate lat/lon crosswalk; this table is NOT a geocoding guess, only
# real matches to a row already in `sources/canal_normal_levels.yaml`) stays OPEN --
# visible, never silently dropped (per `feedback-floodconnect-conflicting-data-rule.md`),
# but never used to decide anything.
_DDS_CANAL_OUTER_SECTION = "canal_outer"


def _normalize_name(s: str) -> str:
    """Strips the usual prefix junk, PLUS (fix, 2026-10-04) any Private-Use-Area
    codepoint (U+F700-U+F8FF) -- MEASURED on this repo's own real dds_daily_pdf captures:
    the bulletin PDF's font maps several Thai vowel/tone marks (sara i, sara aa, mai tho,
    ...) to PUA codepoints that pdftotext/pypdf cannot resolve to the real Unicode
    character (e.g. real station_name "คลองแสนแสบ-เขตบางกะป" where  stands in
    for the dropped "ิ"). Left unstripped, these PUA artifacts silently broke every exact-
    name lookup against `_DDS_GATE_COORDS` (this fix's own coordinate table) and against
    `all_canal_any`'s clean thaiwater names (the contradiction-pairing loop below, which
    already relies on this same function for exact-match equality) -- stripping them is
    strictly a noise removal, never a different real character, so it only makes an
    already-exact-match check match more of what it was always meant to."""
    if not s:
        return ""
    s = "".join(ch for ch in s if not (0xF700 <= ord(ch) <= 0xF8FF))
    for junk in ("ปตร.", "ค.", "คลอง", "ประตูระบายน้ำ"):
        s = s.replace(junk, " ")
    return " ".join(s.split())


# {_normalize_name(bulletin station_name): (lat, lon, source_citation)}. Every entry
# here must be traceable to a real coordinate already on record in this repo -- see the
# per-entry comment for the exact source row cited. Do NOT add a coordinate here from a
# canal-name match alone (a canal can run tens of km) -- only when the SPECIFIC gate the
# DDS bulletin names also appears, by name, as a specific station in a sourced file.
_DDS_GATE_COORDS = {
    # DDS canal_outer row "ปตร.คลองประเวศฯ-ลาดกระบัง" is an EXACT string match to
    # sources/canal_normal_levels.yaml station_code WL.PWT.04's own `canal_name_th`
    # ("ปตร.คลองประเวศฯ-ลาดกระบัง") -- same gate, VERIFIED coordinate (that file's own
    # `source`: api-v3.thaiwater.net waterlevel_graph, station_id=81). Kept here even
    # though this is an outer-section row (excluded from the decision either way, see
    # above) so a future outer/inner reclassification still has a real coordinate to
    # check against, rather than silently falling back to "no coordinate = OPEN".
    _normalize_name("ปตร.คลองประเวศฯ-ลาดกระบัง"): (13.72411, 100.74987,
        "sources/canal_normal_levels.yaml#WL.PWT.04 (api-v3.thaiwater.net station_id=81)"),
    # DDS canal_inner row "คลองแสนแสบ-เขตบางกะปิ" is the same real gate as
    # sources/canal_normal_levels.yaml station_code WL.SSB.07 ("ค.แสนแสบ-สนข.บางกะปิ" --
    # เขต/สนข. บางกะปิ, same office, same canal) -- VERIFIED coordinate, that file's own
    # `source`: api-v3.thaiwater.net waterlevel_graph, station_id=77. Keyed on the real
    # captured station_name's own PUA-stripped form ("...กะป", not "...กะปิ" -- see
    # `_normalize_name`'s own docstring: the bulletin PDF's font drops the final สระอิ to
    # an unresolved Private-Use-Area codepoint, which this lookup's normalization already
    # strips on both sides) -- `_normalize_name` is idempotent on an already-clean literal
    # with no PUA/sara-i ambiguity, so this key is written in that already-stripped form
    # directly rather than re-deriving it from a literal that still has the ิ.
    "แสนแสบ-เขตบางกะป": (13.76509, 100.64791,
        "sources/canal_normal_levels.yaml#WL.SSB.07 (api-v3.thaiwater.net station_id=77)"),
    # The SAME WL.SSB.07 gate, under the station's own canonical label
    # (`sources/canal_normal_levels.yaml`'s own `canal_name_th: "ค.แสนแสบ-สนข.บางกะปิ"`,
    # also this repo's existing `tests/test_readout.py::_seed_fixture_store` fixture
    # name for the identical WL.SSB.07 lat/lon) -- a second real naming convention for
    # the same sourced coordinate, not a second gate.
    _normalize_name("ค.แสนแสบ-สนข.บางกะปิ"): (13.76509, 100.64791,
        "sources/canal_normal_levels.yaml#WL.SSB.07 (api-v3.thaiwater.net station_id=77)"),
    # DDS canal_inner row "คลองลาดพราว 56" (the soi-56 reading point on Khlong Lat
    # Phrao) is matched to sources/canal_normal_levels.yaml station_code WL.LPW.01
    # ("ปตร.คลองลาดพร้าว") -- same named canal gate; VERIFIED coordinate from that file's
    # `source`: api-v3.thaiwater.net waterlevel_graph, station_id=72.
    _normalize_name("คลองลาดพราว 56"): (13.79446, 100.58957,
        "sources/canal_normal_levels.yaml#WL.LPW.01 (api-v3.thaiwater.net station_id=72)"),
    # Every OTHER dds_daily_pdf canal row seen in real captures (ปตร.คลองสองสายใต,
    # ปตร.คลองแสนแสบ-มีนบุรี, คลองแสนแสบ-คลองตัน (แสนแสบเกา), คลองเปรมประชากร,
    # ปตร.คลองทวีวัฒนา, ปตร.คลองมหาสวัสดิ์-ฉิมพลี, คลองทวีวัฒนาตัดคลองภาษีเจริญ) has NO
    # sourced coordinate anywhere in this repo as of this fix -- deliberately left out
    # of this table rather than guessed from the canal's name (a canal can run tens of
    # km; "มีนบุรี" alone does not pin a specific gate to a specific point). Each stays
    # OPEN/`used_for_decision=False` below, not silently assumed nearby.
}

CANAL_VALUE_DIFF_NOTE_M = 0.05  # a plain diff-detection cutoff for WHETHER to log a
                                 # contradiction row -- not a risk score/threshold

# Nationwide one-path radii (v0.1.2, FloodConnect's own design choice -- declared in
# docs/INDICATORS.md, NOT an agency threshold): a river-telemetry station decides at
# "station" resolution within this radius; only when nothing is fresh that close does
# a same-sub_basin station within the wider radius decide, at "basin" resolution
# (which can never produce GREEN -- see build_readout's nationwide block below).
NATIONWIDE_RIVER_RADIUS_KM = 10.0
NATIONWIDE_BASIN_RADIUS_KM = 50.0

# เสียงจากอินเทอร์เน็ต (social listening) -- see social_listening.py's module docstring for
# what makes this layer different from generic social listening (place+state+time only, no
# names, verifiable states not sentiment, always read next to official stations below).
SOCIAL_LISTENING_SOURCES = ("social_listening_google", "social_listening_paste")
FLOODING_STATES = {"house", "garage", "road", "canal_overbank", "pond_overflow", "rising"}
# v0.1.2 (regate finding #4): these three sets are no longer a second hardcoded copy --
# they are read off `floodconnect_model.py`'s own `STATUS_TO_LEVEL`, this repository's
# ONE closed status-word map (see that module). This also means the nationwide
# `thaiwater_situation_1..5` codes this file's own factor-4 loop below now stores
# participate in the same community-report "agreement" check as the English words did
# before, with no separate wiring needed.
import floodconnect_model as _fm
NORMAL_LIKE_STATUS = set(_fm.NORMAL_LIKE_STATUS)
# Subset of FLOOD_LIKE_STATUS that is an agency-declared critical/overflow reading
# (`live_water_level.classify_status`'s own top two bands: value >= critical, or
# value >= bank i.e. the canal has topped its bank) -- founder ruling 2026-10-04
# (verbatim: "WATCH = YELLOW (แนะนำ)"): a bare WATCH/เฝ้าระวัง station reading is no
# longer enough on its own to drive the resident-facing current_local_state to RED.
# RED is reserved for CRITICAL/OVERBANK (วิกฤต/ล้นตลิ่ง); WATCH alone now classifies
# as YELLOW via `kb._classify_current_local_state`'s fall-through. This is strictly
# smaller than FLOOD_LIKE_STATUS, which keeps its original (wider) meaning for the
# community-report "agreement" check above -- that check is unaffected by this ruling.
CRITICAL_LIKE_STATUS = set(_fm.CRITICAL_LIKE_STATUS)
FLOOD_LIKE_STATUS = set(_fm.CRITICAL_LIKE_STATUS) | set(_fm.WATCH_LIKE_STATUS)


def _fmt(v, nd=2):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def _local_date(observed_at_utc: str, tz_hours: float = 7.0):
    """UTC ISO timestamp -> its Bangkok-local (+07:00) calendar date, as "YYYY-MM-DD", or
    None if unparseable. Used to filter the tide table by the LOCAL day the reading is
    for, not the UTC day the same instant happens to fall on -- the two disagree for any
    local time before 07:00 (a `-` UTC offset relative to local midnight), which used to
    make the tide section for a given `as_of_date` drop that day's early-morning low/high
    tide and show the FOLLOWING day's early tide instead (both silently, since the query
    just returned fewer/different rows, never an error)."""
    if not observed_at_utc:
        return None
    try:
        dt = datetime.datetime.fromisoformat(observed_at_utc)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    local = dt.astimezone(datetime.timezone(datetime.timedelta(hours=tz_hours)))
    return local.date().isoformat()


def _header_date_recognized(o: dict) -> bool:
    """True unless this dds_daily_pdf row's provenance explicitly says the bulletin's own
    header date wasn't recognized (see collect.py's `header_date_recognized` flag) -- in
    that case `observed_at_utc` is actually the FETCH time, not a bulletin-stated date,
    and should not be presented as a confirmed-fresh reading. Rows with no such flag at
    all (older data collected before this fix, or a variable this flag doesn't apply to)
    default to True -- this is a "flag it when we know it's wrong" check, not proof of
    freshness."""
    prov = o.get("provenance_json")
    if not prov:
        return True
    try:
        return json.loads(prov).get("header_date_recognized", True)
    except (TypeError, ValueError):
        return True


def _latest_by_composite_key(rows: list, key_fn) -> dict:
    """Same collapsing rule as `_latest_by_key`, but keyed by whatever `key_fn(row)`
    returns (skipped if falsy) instead of a single fixed field name -- used where the
    identity key isn't just `station_code` (e.g. `station_code or station_name`, since
    some sources carry no code)."""
    out = {}
    for r in rows:
        key = key_fn(r)
        if not key:
            continue
        cur = out.get(key)
        if cur is None or (r.get("observed_at_utc") or "") > (cur.get("observed_at_utc") or ""):
            out[key] = r
    return out


def _latest_by_key(rows: list, key_field: str) -> dict:
    """Collapses `rows` (any order) to one row per `key_field` value: the one with the
    lexicographically-largest `observed_at_utc` (ISO-8601 strings with a fixed-width date/
    time sort chronologically) -- i.e. the LATEST reading for that key, never an arbitrary
    or oldest one.

    A prior version built this dict directly from `store.query_observations`'s own
    DESC-by-observed_at_utc ordering via a plain `{o[key]: o for o in rows}` comprehension
    -- for a DESC-ordered list, later loop iterations (the OLDER rows) overwrite earlier
    ones in the dict, so the dict ended up holding the OLDEST reading per station, not the
    newest. Verified wrong against a scratch DB (a station with a 09-20 and a 09-26
    reading came back showing 09-20). This helper does not depend on the caller's row
    order at all.
    """
    out = {}
    for r in rows:
        key = r.get(key_field)
        if not key:
            continue
        cur = out.get(key)
        if cur is None or (r.get("observed_at_utc") or "") > (cur.get("observed_at_utc") or ""):
            out[key] = r
    return out


def load_latest_dds_daily(conn) -> dict:
    """Returns the most recent dds_daily_pdf fetched_at_utc's rows, grouped by variable
    family, plus its documents. Empty dict if nothing has been collected yet."""
    row = conn.execute(
        "SELECT MAX(fetched_at_utc) AS ts FROM observations WHERE source_id='dds_daily_pdf'"
    ).fetchone()
    latest_ts = row["ts"] if row else None
    if not latest_ts:
        return {"observations": [], "documents": [], "fetched_at_utc": None}
    obs = [dict(r) for r in conn.execute(
        "SELECT * FROM observations WHERE source_id='dds_daily_pdf' AND fetched_at_utc=?",
        (latest_ts,)).fetchall()]
    docs = [dict(r) for r in conn.execute(
        "SELECT * FROM documents WHERE source_id='dds_daily_pdf' AND fetched_at_utc=?",
        (latest_ts,)).fetchall()]
    return {"observations": obs, "documents": docs, "fetched_at_utc": latest_ts}


def load_social_listening(conn) -> dict:
    """Every `community_report` row from either social_listening_ source, grouped by its
    own `area` field (from provenance_json) -- e.g. "sammakorn", "ram53". Never filters by
    distance (community reports carry a soi/place name, not lat/lon) -- see the
    "agreement" section's own OPEN note about that limitation."""
    rows = []
    for sid in SOCIAL_LISTENING_SOURCES:
        rows.extend(store.query_observations(conn, source_id=sid, variable="community_report",
                                              limit=2000))
    by_area: dict = {}
    for r in rows:
        prov = json.loads(r["provenance_json"]) if r.get("provenance_json") else {}
        row = dict(r)
        row["_prov"] = prov
        area = prov.get("area") or "unknown"
        by_area.setdefault(area, []).append(row)
    return by_area


def _social_listening_section(area: str, rows: list, sammakorn_nodes: dict) -> dict:
    rows_sorted = sorted(rows, key=lambda r: r.get("observed_at_utc") or "", reverse=True)
    hourly: dict = {}
    for r in rows:
        dt = r.get("observed_at_utc") or ""
        hour_key = dt[:13] if dt else "unknown"
        hourly[hour_key] = hourly.get(hour_key, 0) + 1
    latest5 = [{
        "soi_place": r["_prov"].get("soi") or r["_prov"].get("place_text"),
        "state": r.get("status"), "observed_at_utc": r.get("observed_at_utc"),
        "publisher_type": r["_prov"].get("publisher_type"),
    } for r in rows_sorted[:5]]

    # Agreement: a LOOKUP against the nearest official Sammakorn node's own published
    # status at (about) the same hour -- never a score, never resolved to a single verdict
    # across the whole area. Only meaningful for "sammakorn" (the only area with a fixed,
    # coordinate-known node list -- see SAMMAKORN_NODES/SAMMAKORN_PUMPS above); other areas
    # get an explicit OPEN note instead of a fabricated comparison.
    agreement = []
    if area == "sammakorn":
        for group, node_rows in sammakorn_nodes.items():
            for nr in node_rows:
                if nr.get("tag") not in ("MEASURED", "STALE"):
                    continue
                node_label = nr.get("name") or nr.get("station_code")
                if not rows_sorted:
                    agreement.append({
                        "node": node_label, "community_state": None,
                        "station_status": nr.get("status"),
                        "verdict": "no-overlap [OPEN: no community report this run]"})
                    continue
                nearest = min(
                    rows_sorted,
                    key=lambda r: abs(lwl.age_hours(r.get("observed_at_utc"),
                                                     nr.get("observed_at_utc")) or 999.0))
                c_state = nearest.get("status")
                s_status = nr.get("status")
                if c_state in FLOODING_STATES and s_status in FLOOD_LIKE_STATUS:
                    verdict = "agree"
                elif c_state == "receding" and s_status in NORMAL_LIKE_STATUS:
                    verdict = "agree"
                elif c_state in FLOODING_STATES and s_status in NORMAL_LIKE_STATUS:
                    verdict = "disagree"
                elif c_state == "receding" and s_status in FLOOD_LIKE_STATUS:
                    verdict = "disagree"
                else:
                    verdict = "no-overlap"
                agreement.append({"node": node_label, "community_state": c_state,
                                  "station_status": s_status, "verdict": verdict})
    else:
        agreement.append({
            "node": None, "community_state": None, "station_status": None,
            "verdict": "no-overlap [OPEN: no coordinate-known official node list for "
                       f"area '{area}' yet -- only 'sammakorn' has one, see "
                       "SAMMAKORN_NODES/SAMMAKORN_PUMPS]"})
    return {"hourly_counts": hourly, "latest5": latest5, "agreement": agreement}


def build_readout(conn, centre_lat: float, centre_lon: float, radius_km: float,
                   as_of_date: str = None) -> dict:
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # STALE/MEASURED staleness (lwl.STALE_HOURS, see below) must be judged against the
    # instant this readout claims to represent, never against the real wall-clock "now" --
    # otherwise a historical replay (readout_history.py) or a fixture test pinning a past
    # as_of_date would mislabel its own already-declared-fresh window as STALE purely
    # because real time has since moved on. When the caller does not pin a date (the live
    # collect.py -> build_data.py path, which never passes --date), as_of_date is None here
    # and staleness_reference_utc stays generated_at (real now) -- unchanged live behaviour.
    # When the caller explicitly pins as_of_date (replay, backfill, or a test fixture),
    # staleness is judged from the START of that declared day, so a reading from earlier
    # the same historical "as of" window is still MEASURED, not incorrectly STALE (bug
    # fixed here, see AGENTS.md §8 / tests/test_readout.py::test_build_readout_with_fixture_store).
    as_of_date_explicit = as_of_date is not None
    as_of_date = as_of_date or generated_at[:10]
    staleness_reference_utc = f"{as_of_date}T00:00:00+00:00" if as_of_date_explicit else generated_at
    # fix: `lwl.is_fresh`'s `future_tolerance_h` default (-1.0) is for a REAL
    # wall-clock reference. A day-pinned reference is LOCAL MIDNIGHT of the declared
    # day, so a legitimate same-day reading can be up to ~24h "after" it -- widen the
    # tolerance only for that explicit, bounded case (never unbounded).
    future_tolerance_h = -24.0 if as_of_date_explicit else -1.0

    # Single freshness gate (house rule, 2026-10-03): every age/staleness decision below
    # calls `lwl.is_fresh(observed_at, staleness_reference_utc, max_age)` -- ONE function,
    # never a re-inlined `age_h is None or age_h > lwl.STALE_HOURS` check. `max_age` per
    # source comes from `sources/registry.yaml`'s own `max_age_hours` field (falls back to
    # `lwl.STALE_HOURS` when the registry/field is unavailable -- see
    # `lwl.max_age_hours_for`'s own docstring). The registry is loaded once per call here,
    # not once per row, and a load failure must not crash a readout -- the per-source
    # fallback below is always `lwl.STALE_HOURS`, same as before this gate existed.
    try:
        import collect as collect_mod
        _registry = collect_mod.load_registry()
    except Exception:  # pragma: no cover - defensive, registry must not crash a readout
        _registry = {}

    def _max_age(source_id):
        return lwl.max_age_hours_for(source_id, _registry)

    def dist_km(o):
        return (haversine_km(centre_lat, centre_lon, o["lat"], o["lon"])
                if o.get("lat") is not None else None)

    sources_used = sorted({r["source_id"] for r in conn.execute(
        "SELECT DISTINCT source_id FROM observations").fetchall()})
    doc_sources = sorted({r["source_id"] for r in conn.execute(
        "SELECT DISTINCT source_id FROM documents").fetchall()})
    sources_used = sorted(set(sources_used) | set(doc_sources))

    dds = load_latest_dds_daily(conn)
    dds_obs = dds["observations"]

    near_canal = store.query_observations(
        conn, source_id="thaiwater_canal_waterlevel",
        near=(centre_lat, centre_lon, radius_km), limit=2000)
    near_pumps = store.query_observations(
        conn, source_id="bma_pumphistory", near=(centre_lat, centre_lon, radius_km),
        limit=2000)
    near_flood_road = store.query_observations(
        conn, source_id="thaiwater_flood_road", near=(centre_lat, centre_lon, radius_km),
        limit=2000)

    result = {
        "header": {
            "centre": {"lat": centre_lat, "lon": centre_lon}, "radius_km": radius_km,
            "generated_at_utc": generated_at, "as_of_date": as_of_date,
            "sources_used": sources_used,
        },
        "factors": {}, "sammakorn_nodes": {}, "contradictions": [], "missing": [],
        "overall_picture": {"tag": "INSTINCT", "notes": []},
    }

    # --- Factor 1: ฝน (rain) --------------------------------------------------------
    rain_rows = [o for o in dds_obs if o["variable"] == "rain_24h_mm"]
    f1 = {"measured": [], "official_forecast": [], "missing": []}
    for o in rain_rows:
        recognized = _header_date_recognized(o)
        f1["measured"].append({
            "station": o["station_name"], "value": o["value"], "unit": "mm",
            "status": None, "observed_at_utc": o["observed_at_utc"],
            "source": "dds_daily_pdf",
            "tag": "MEASURED" if recognized else "OPEN",
        })
        if not recognized:
            f1["missing"].append({
                "note": (f"'{o['station_name']}' reading's date could not be confirmed "
                         "(bulletin header line wasn't recognized this run) -- "
                         "observed_at_utc above is the FETCH time, not a confirmed "
                         "bulletin date."), "tag": "OPEN"})
    if not rain_rows:
        f1["missing"].append({"note": "No dds_daily_pdf rain readings in the store yet.",
                               "tag": "OPEN"})
    f1["missing"].append({
        "note": ("The bulletin's own 24h weather FORECAST is free-text prose, not a "
                 "structured figure this pipeline parses into a row -- see the "
                 "'weather_forecast' document instead of a table row here."),
        "tag": "OPEN",
    })
    result["factors"]["1_ฝน"] = f1

    # --- Factor 2: น้ำเหนือ (Chao Phraya discharge from the north) -------------------
    cp_rows = [o for o in dds_obs if o["variable"].startswith("qmax_")]
    f2 = {"measured": [], "official_forecast": [], "missing": []}
    by_date = {}
    for o in cp_rows:
        by_date.setdefault(o["observed_at_utc"], []).append(o)
    for dt in sorted(by_date):
        for o in by_date[dt]:
            f2["measured"].append({
                "station": "RID_CHAOPHRAYA", "value": o["value"], "unit": o["unit"],
                "variable": o["variable"], "status": None,
                "observed_at_utc": o["observed_at_utc"], "source": "dds_daily_pdf",
                "tag": "MEASURED",
            })
    partial = [d for d in dds["documents"]
               if d["section"] == "chaophraya_flow_tide_partial"]
    for d in partial:
        f2["missing"].append({
            "note": f"Report-date Chao Phraya row is incomplete in the bulletin, raw text "
                     f"preserved verbatim, not parsed: {d['text']}",
            "tag": "OPEN",
        })
    if not cp_rows:
        f2["missing"].append({"note": "No dds_daily_pdf Chao Phraya discharge rows yet.",
                               "tag": "OPEN"})
    result["factors"]["2_น้ำเหนือ"] = f2

    # --- Factor 3: น้ำทะเลหนุน (tide surge) -----------------------------------------
    tide_dedicated = [o for o in dds_obs if o["variable"] in
                      ("tide_ขึ้นเต็มที่_am_m", "tide_ลงเต็มที่_am_m")]
    tide_base_rows = [o for o in dds_obs if o["variable"] == "tide_base_level_m"]
    # Filtered on the Bangkok-LOCAL calendar date (via _local_date), not a UTC-date LIKE
    # match against a column that stores UTC instants -- the table's own day boundary is
    # local midnight (see dds_tide_pdf's collector), so a UTC-date match systematically
    # drops/shifts every reading before 07:00 local (see _local_date's docstring).
    _tide_all = [dict(r) for r in conn.execute(
        "SELECT * FROM observations WHERE source_id='dds_tide_pdf'").fetchall()]
    tide_table_today = [r for r in _tide_all if _local_date(r["observed_at_utc"]) == as_of_date]
    f3 = {"measured": [], "official_forecast": [], "missing": []}
    for o in tide_dedicated:
        f3["official_forecast"].append({
            "station": "NAVY_HYDRO (bulletin sec.7)", "value": o["value"], "unit": "m",
            "variable": o["variable"], "observed_at_utc": o["observed_at_utc"],
            "source": "dds_daily_pdf", "tag": "RELAYED",
        })
    for o in tide_base_rows:
        f3["official_forecast"].append({
            "station": "ฐานน้ำทะเลหนุน (bulletin sec.5, RID/Navy)", "value": o["value"],
            "unit": "m", "variable": o["variable"],
            "observed_at_utc": o["observed_at_utc"], "source": "dds_daily_pdf",
            "tag": "RELAYED",
        })
    for o in tide_table_today:
        f3["official_forecast"].append({
            "station": "NAVY_HYDRO_HQ (monthly tide table)", "value": o["value"],
            "unit": "m", "variable": o["variable"],
            "observed_at_utc": o["observed_at_utc"], "source": "dds_tide_pdf",
            "tag": "RELAYED",
        })
    if not f3["official_forecast"]:
        f3["missing"].append({"note": "No tide readings for this date in the store yet.",
                               "tag": "OPEN"})
    result["factors"]["3_น้ำทะเลหนุน"] = f3

    # --- Factor 4: การระบาย (drainage: canal levels + pumps) ------------------------
    f4 = {"measured": [], "official_forecast": [], "missing": []}
    # `near_canal`/`near_pumps` can hold MULTIPLE historical readings per station within
    # the radius (every past collect, not just the latest) -- collapsed here to the latest
    # reading per station before rendering, and tagged STALE instead of MEASURED when it's
    # older than `lwl.STALE_HOURS`. A prior version rendered every historical row as
    # MEASURED with no age shown at all, so a station's reading from months/years ago (a
    # real committed example: one station showed a 2026-06-09 value, another a 2019-12-24
    # value) sat in the "live drainage table" indistinguishable from a fresh reading.
    _key = lambda o: o.get("station_code") or o.get("station_name")
    # Tracks whether a LOCAL (already-geolocated, already radius-filtered to this
    # point) factor-4 reading is fresh -- used below to stop the nationwide
    # thaiwater_waterlevel block (stations up to 50 km away) from outranking a
    # point's own close-by canal/pump telemetry. Regression, found by independent
    # review (2026-10-04): before this flag, Sammakorn's own fresh canal stations
    # didn't count toward `_has_fresh_station` (that check only looked at the
    # nationwide thaiwater_waterlevel source), so a RED basin-resolution row 15-26 km
    # away on an unrelated canal could flip Sammakorn from YELLOW to RED even though
    # Sammakorn's own nearby stations were fresh and said otherwise.
    _local_factor4_decides = False
    for o in _latest_by_composite_key(near_canal, _key).values():
        fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                    _max_age("thaiwater_canal_waterlevel"), future_tolerance_h=future_tolerance_h)
        stale = not fresh
        if fresh:
            _local_factor4_decides = True
        f4["measured"].append({
            "station": o.get("station_name") or o.get("station_code"),
            "value": o["value"], "unit": "m", "status": o.get("status"),
            "observed_at_utc": o["observed_at_utc"], "age_h": age_h,
            "source": "thaiwater_canal_waterlevel", "tag": "STALE" if stale else "MEASURED",
        })
    for o in _latest_by_composite_key(near_pumps, _key).values():
        fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                    _max_age("bma_pumphistory"), future_tolerance_h=future_tolerance_h)
        stale = not fresh
        if fresh:
            _local_factor4_decides = True
        f4["measured"].append({
            "station": o.get("station_name") or o.get("station_code"),
            "value": o["value"], "unit": "m", "status": o.get("status"),
            "observed_at_utc": o["observed_at_utc"], "age_h": age_h,
            "source": "bma_pumphistory", "tag": "STALE" if stale else "MEASURED",
        })
    # --- Nationwide river/canal telemetry (v0.1.2, founder ruling 2026-10-04: "ทำเลย
    # v0.1.2 ทั้งประเทศ") -- same factor 4 (drainage), one generic path for EVERY
    # point in Thailand, not only the Bangkok-area sources above. Selection per
    # docs/INDICATORS.md §"nationwide resolution" (FloodConnect's own design choice,
    # not an agency threshold): the nearest fresh station within RIVER_RADIUS_KM
    # decides at "station" resolution; only when NONE is fresh within that radius does
    # a same-sub_basin station within BASIN_RADIUS_KM decide, at "basin" resolution,
    # and a basin-resolution row can never contribute a GREEN (far + "normal" is not a
    # clearance) -- it is still shown, just excluded from the decision
    # (`used_for_decision=False`) when its own classified level is GREEN. A
    # nationwide row of either resolution is ALSO excluded from the decision (still
    # shown as reference evidence) whenever this point's own LOCAL factor-4 reading
    # (near_canal/near_pumps, already geolocated+radius-filtered to this point) is
    # fresh -- see `_local_factor4_decides` above.
    near_wl_basin = store.query_observations(
        conn, source_id="thaiwater_waterlevel",
        near=(centre_lat, centre_lon, NATIONWIDE_BASIN_RADIUS_KM), limit=2000)
    _wl_candidates = []
    for o in _latest_by_composite_key(near_wl_basin, _key).values():
        d = dist_km(o)
        if d is None:
            continue
        fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                    _max_age("thaiwater_waterlevel"), future_tolerance_h=future_tolerance_h)
        try:
            prov = json.loads(o.get("provenance_json") or "{}")
        except (TypeError, ValueError):
            prov = {}
        _wl_candidates.append({"o": o, "dist_km": d, "stale": not fresh, "age_h": age_h,
                                "prov": prov})
    _wl_candidates.sort(key=lambda r: r["dist_km"])
    _station_rows = [r for r in _wl_candidates if r["dist_km"] <= NATIONWIDE_RIVER_RADIUS_KM]
    _has_fresh_station = any(not r["stale"] for r in _station_rows)
    _basin_rows = []
    if not _has_fresh_station and _wl_candidates:
        _basin_ref = _wl_candidates[0]["prov"].get("sub_basin_id")
        if _basin_ref is not None:
            _basin_rows = [r for r in _wl_candidates
                            if r["dist_km"] > NATIONWIDE_RIVER_RADIUS_KM
                            and r["dist_km"] <= NATIONWIDE_BASIN_RADIUS_KM
                            and r["prov"].get("sub_basin_id") == _basin_ref]
    for r in _station_rows + _basin_rows:
        o, prov = r["o"], r["prov"]
        resolution = "station" if r["dist_km"] <= NATIONWIDE_RIVER_RADIUS_KM else "basin"
        status_word = o.get("status")
        level = _fm.classify(status_word)
        decides = not r["stale"]
        if resolution == "basin" and level == "GREEN":
            # basin resolution can never decide GREEN on its own -- see this block's
            # own comment above.
            decides = False
        if _local_factor4_decides:
            # A local (Bangkok canal/pump, already-geolocated-and-radius-filtered)
            # reading already decides this point -- a nationwide row up to 50 km away
            # is shown as reference evidence only, never lets a far station override
            # the point's own close telemetry. See this block's comment above.
            decides = False
        f4["measured"].append({
            "station": o.get("station_name") or o.get("station_code"),
            "value": o.get("value"), "unit": "m", "status": status_word,
            "observed_at_utc": o["observed_at_utc"], "age_h": r["age_h"],
            "source": "thaiwater_waterlevel", "tag": "STALE" if r["stale"] else "MEASURED",
            "used_for_decision": decides,
            "dist_km": round(r["dist_km"], 2), "resolution": resolution,
            "agency": prov.get("agency"), "agency_shortname": prov.get("agency_shortname"),
            "province_th": prov.get("province_th"), "river_name": prov.get("river_name"),
        })
    if not _wl_candidates:
        f4["missing"].append({
            "note": (f"No nationwide thaiwater_waterlevel station within "
                     f"{NATIONWIDE_BASIN_RADIUS_KM} km of this point -- current_local_state "
                     "stays UNKNOWN at this resolution."),
            "tag": "OPEN",
        })

    dds_canal = [o for o in dds_obs if o["variable"] == "canal_level_0700_m"]
    # fix, re-fixed 2026-10-04 (see the long comment on `_DDS_GATE_COORDS` above
    # for the full story -- the first attempt, 40km-of-central-Bangkok + canal-name
    # substring, still let a far `canal_outer` gate decide Thonburi/Don Mueang/other
    # Bangkok-area points). A row now decides `current_local_state` only if it is a
    # `canal_inner` row, its own gate has a sourced coordinate in `_DDS_GATE_COORDS`,
    # and that coordinate lies within the CALLER's own `radius_km` of the centre --
    # never a separate hardcoded radius. A row failing any of these three stays visible
    # (never silently dropped) but `used_for_decision=False`.
    for o in dds_canal:
        # dds_canal is always exactly one bulletin's rows (load_latest_dds_daily already
        # selects the single latest fetched_at_utc batch), so no separate dedupe is needed
        # here -- only the tag, for the same reason as above.
        fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                    _max_age("dds_daily_pdf"), future_tolerance_h=future_tolerance_h)
        stale = not fresh
        # fix: a bulletin row whose header date could not be parsed is stamped
        # with the FETCH time as `observed_at_utc` (see collect_dds_daily_pdf), which
        # `lwl.is_fresh` then reads as "just fetched" -- always passing the freshness
        # gate even when the underlying bulletin date is unknown. Treat
        # `header_date_recognized=False` as STALE/not-decided regardless of what the
        # freshness-by-age check alone says (factor 1's rain rows already do this; this
        # was the one other dds_daily_pdf loop that didn't).
        date_recognized = _header_date_recognized(o)
        stale = stale or not date_recognized
        try:
            _section = json.loads(o.get("provenance_json") or "{}").get("section")
        except (TypeError, ValueError):
            _section = None
        is_outer = _section == _DDS_CANAL_OUTER_SECTION
        _row_canal_name = _normalize_name(o.get("station_name") or "")
        _coord = _DDS_GATE_COORDS.get(_row_canal_name)
        if _coord is None:
            has_coord = False
            in_radius = False
            coord_source = None
        else:
            has_coord = True
            _gate_lat, _gate_lon, coord_source = _coord
            in_radius = haversine_km(centre_lat, centre_lon, _gate_lat, _gate_lon) <= radius_km
        local_match = (not is_outer) and has_coord and in_radius
        if is_outer:
            scope_note = ("ค่าฝั่งนอกคันป้องกันน้ำท่วม (canal_outer) -- คนละสภาพน้ำกับคลอง"
                          "ในคันป้องกัน, ไม่ใช้ตัดสินสถานะปัจจุบันของจุดนี้ [OPEN]")
        elif not has_coord:
            scope_note = ("กทม. ทั้งเมือง (bulletin) -- ไม่มีพิกัดที่ยืนยันแล้วสำหรับสถานีนี้ใน"
                          "คลังข้อมูล, ไม่ใช่สถานีใกล้จุดนี้ [OPEN]")
        elif not in_radius:
            scope_note = f"กทม. ทั้งเมือง (bulletin) -- สถานีอยู่นอกรัศมี {radius_km} km ของจุดนี้"
        else:
            scope_note = f"สถานีใกล้จุดนี้ (พิกัดยืนยันแล้ว, {coord_source})"
        f4["measured"].append({
            "station": o["station_name"], "value": o["value"], "unit": "m",
            "status": o.get("status"), "observed_at_utc": o["observed_at_utc"],
            "age_h": age_h, "source": "dds_daily_pdf",
            "tag": "STALE" if stale else "MEASURED",
            "header_date_recognized": date_recognized,
            "canal_outer": is_outer,
            "local_match": local_match,
            "used_for_decision": local_match and not stale,
            "scope_note": scope_note,
        })
    f4["missing"].append({
        "note": ("No pump-on/off or gate-open/shut FORECAST exists anywhere in these "
                 "sources -- BMA PumpHistory gives current status only (MEASURED, "
                 "above), the DDS daily bulletin has no drainage forecast section."),
        "tag": "OPEN",
    })
    if not near_canal and not near_pumps:
        f4["missing"].append({
            "note": f"No live telemetry station matched within {radius_km} km of the centre.",
            "tag": "OPEN",
        })
    result["factors"]["4_การระบาย"] = f4

    # --- Factor 5: ถนนน้ำท่วม (flood-affected roads) ---------------------------------
    # Previously computed only to feed the contradictions check (near_flood_road never
    # showed up as its own readout row) -- the 7 non-zero thaiwater_flood_road readings
    # within a typical 5 km radius near this centre never appeared anywhere a reader could
    # see them directly.
    f5 = {"measured": [], "official_forecast": [], "missing": []}
    _nonzero_flood_road = [o for o in near_flood_road if o.get("value") and o["value"] > 0]
    for o in _latest_by_composite_key(
            _nonzero_flood_road, lambda r: r.get("station_code") or r.get("station_name")).values():
        fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                    _max_age("thaiwater_flood_road"), future_tolerance_h=future_tolerance_h)
        stale = not fresh
        name = o.get("station_name") or ""
        f5["measured"].append({
            "station": name, "value": o["value"], "unit": "cm",
            # A road name ending " *" was observed in the raw feed alongside a value of
            # exactly 20.0 or 10.0 -- the asterisk's meaning was never confirmed against
            # any BMA/thaiwater documentation (OPEN), so a station carrying it is flagged
            # here rather than silently trusted at official_telemetry tier.
            "status": "asterisk-flagged, meaning unconfirmed [OPEN]" if name.strip().endswith("*") else o.get("status"),
            "observed_at_utc": o["observed_at_utc"], "age_h": age_h,
            "source": "thaiwater_flood_road", "tag": "STALE" if stale else "MEASURED",
        })
    if not f5["measured"]:
        f5["missing"].append({
            "note": f"No nonzero thaiwater_flood_road reading within {radius_km} km this run.",
            "tag": "OPEN"})
    f5["missing"].append({
        "note": ("The '*' suffix seen on some road names in the raw feed, and its "
                 "exact-20.0/exact-10.0 values, are relayed as-is -- their meaning was "
                 "never confirmed against BMA/thaiwater documentation."),
        "tag": "OPEN"})
    result["factors"]["5_ถนนน้ำท่วม"] = f5

    # --- โหนดของสัมมากร (fixed Sammakorn station list) ------------------------------
    nodes = {}
    # Fixed-list stations may sit just outside the --radius-km search, so look them up
    # directly by code across ALL thaiwater_canal_waterlevel readings, not only `near_canal`.
    all_canal_any = store.query_observations(conn, source_id="thaiwater_canal_waterlevel",
                                              limit=5000)
    all_canal_by_code_any = _latest_by_key(all_canal_any, "station_code")
    for group, codes in SAMMAKORN_NODES.items():
        rows = []
        for code in codes:
            o = all_canal_by_code_any.get(code)
            if o is None:
                rows.append({"station_code": code, "tag": "OPEN",
                             "note": "not found in the current store", "source": None})
                continue
            fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                        _max_age("thaiwater_canal_waterlevel"), future_tolerance_h=future_tolerance_h)
            stale = not fresh
            rows.append({
                "station_code": code, "name": o.get("station_name"),
                "value_m": o["value"], "status": o.get("status"),
                "observed_at_utc": o["observed_at_utc"], "dist_km": dist_km(o),
                "age_h": age_h, "source": "thaiwater_canal_waterlevel",
                "tag": "STALE" if stale else "MEASURED",
            })
        nodes[group] = rows

    pump_rows = []
    all_pumps_any = store.query_observations(conn, source_id="bma_pumphistory", limit=1000)
    by_pump_code = _latest_by_key(all_pumps_any, "station_code")
    for code in SAMMAKORN_PUMPS:
        o = by_pump_code.get(code)
        if o is None:
            pump_rows.append({"station_code": code, "tag": "OPEN",
                              "note": "not found in the current store", "source": None})
            continue
        fresh, age_h = lwl.is_fresh(o["observed_at_utc"], staleness_reference_utc,
                                    _max_age("bma_pumphistory"), future_tolerance_h=future_tolerance_h)
        stale = not fresh
        prov = json.loads(o["provenance_json"]) if o.get("provenance_json") else {}
        pump_rows.append({
            "station_code": code, "name": o.get("station_name"),
            "level_m": o["value"], "pumps_on": prov.get("pumps_on"),
            "pumps_total": prov.get("pumps_total"), "gate_open_m": prov.get("gate_open_m"),
            "status": o.get("status"), "observed_at_utc": o["observed_at_utc"],
            "dist_km": dist_km(o), "age_h": age_h, "source": "bma_pumphistory",
            "tag": "STALE" if stale else "MEASURED",
        })
    nodes["in-basin pumps (ST.SPS)"] = pump_rows
    result["sammakorn_nodes"] = nodes

    # --- เสียงจากอินเทอร์เน็ต (social listening) -------------------------------------
    social_by_area = load_social_listening(conn)
    result["social_listening"] = {
        area: _social_listening_section(area, rows, nodes)
        for area, rows in social_by_area.items()
    }

    # --- ความขัดแย้งระหว่างแหล่ง (contradictions) ------------------------------------
    contradictions = []

    # Candidate pairing by EXACT normalized-name equality only -- an earlier version used
    # a fuzzy difflib ratio (>= 0.45) with no coordinate or station-code check, which
    # produced pairings like "ปตร.คลองแสนแสบ-มีนบุรี.80" (DDS) vs "ค.แสนแสบ-โบ๊เบ๊"
    # (thaiwater, ratio 0.53) -- two DIFFERENT physical stations that only share the
    # canal name "แสนแสบ". A coordinate cutoff isn't available here: dds_daily_pdf's own
    # canal rows carry no lat/lon (see collect_dds_daily_pdf). Exact-normalized-name
    # equality is used instead as the closest available substitute for a real code
    # crosswalk (BMA has never published one). Even an exact-name match is NOT proof of
    # "same physical station" (BMA and thaiwater could still independently reuse a canal
    # name for different segments) -- so every row here is tagged a CANDIDATE, INSTINCT,
    # never asserted as a confirmed same-station contradiction.
    latest_canal_by_name = {}
    for c in all_canal_any:
        key = _normalize_name(c.get("station_name") or "")
        if key and (key not in latest_canal_by_name or
                    (c.get("observed_at_utc") or "") >
                    (latest_canal_by_name[key].get("observed_at_utc") or "")):
            latest_canal_by_name[key] = c
    for o in dds_canal:
        if o.get("value") is None:
            continue
        target = _normalize_name(o["station_name"])
        best = latest_canal_by_name.get(target) if target else None
        if best is None or best.get("value") is None:
            continue
        diff = abs(best["value"] - o["value"])
        if diff < CANAL_VALUE_DIFF_NOTE_M:
            continue
        gap_h = lwl.age_hours(o["observed_at_utc"], best["observed_at_utc"])
        gap_note = f"~{abs(gap_h):.1f}h apart" if gap_h is not None else "gap unknown"
        # Single freshness gate, same as factor 4 above -- a contradiction row is always
        # shown (both sides, never resolved/averaged, per the house rule), but a STALE
        # side must say so plainly rather than read as a live disagreement (the real
        # example this fixes: `all_canal_any` can hold a years-old row like SS06/2019,
        # which a name match could otherwise pair as if it were a fresh contradiction).
        fresh_b, age_b_h = lwl.is_fresh(best["observed_at_utc"], staleness_reference_utc,
                                         _max_age("thaiwater_canal_waterlevel"), future_tolerance_h=future_tolerance_h)
        staleness_note = ("" if fresh_b else
                           f" -- '{best.get('station_name')}' side is STALE "
                           f"(age {age_b_h:.1f}h if parseable, not used for any decision, "
                           "shown for transparency only)" if age_b_h is not None else
                           f" -- '{best.get('station_name')}' side is STALE (age unknown)")
        row = {
            "topic": "canal_level_same_name_candidate", "tag": "INSTINCT",
            "source_a": "dds_daily_pdf", "value_a": o["value"],
            "observed_a": o["observed_at_utc"],
            "source_b": "thaiwater_canal_waterlevel", "value_b": best["value"],
            "observed_b": best["observed_at_utc"],
            "age_b_h": age_b_h, "stale_b": not fresh_b,
            "note": (f"CANDIDATE pairing by exact normalized-name match only (no "
                     f"coordinate/code crosswalk available for the DDS row) -- "
                     f"'{o['station_name']}' (DDS bulletin) vs "
                     f"'{best.get('station_name')}' (thaiwater) -- {diff:.2f} m apart, "
                     f"observations {gap_note} -- NOT verified as the same physical "
                     f"station, not resolved.{staleness_note}"),
        }
        contradictions.append(row)
        store.insert_contradiction(
            conn, observed_at_utc=generated_at, topic=row["topic"],
            source_a=row["source_a"], value_a=row["value_a"],
            observed_a_utc=row["observed_a"],
            source_b=row["source_b"], value_b=row["value_b"],
            observed_b_utc=row["observed_b"], note=row["note"])

    # Only the MOST RECENT dds_flood_report fetch (not every one ever stored) -- otherwise
    # a road still listed in yesterday's report can suppress today's genuine contradiction
    # against a live nonzero thaiwater_flood_road reading, or vice versa.
    _fr_latest_ts_row = conn.execute(
        "SELECT MAX(fetched_at_utc) AS ts FROM documents WHERE source_id='dds_flood_report'"
    ).fetchone()
    _fr_latest_ts = _fr_latest_ts_row["ts"] if _fr_latest_ts_row else None
    flood_report_docs = [dict(r) for r in conn.execute(
        "SELECT * FROM documents WHERE source_id='dds_flood_report' "
        "AND section='flood_road_detail' AND fetched_at_utc=?",
        (_fr_latest_ts,)).fetchall()] if _fr_latest_ts else []
    fr_by_district = {}
    for d in flood_report_docs:
        parts = d["text"].split(" | ")
        district = parts[0] if parts else None
        fr_by_district.setdefault(district, []).append(d["text"])
    for o in near_flood_road:
        if not o.get("value") or o["value"] <= 0:
            continue
        prov = json.loads(o["provenance_json"]) if o.get("provenance_json") else {}
        district = prov.get("district_th")
        listed = fr_by_district.get(district)
        if not listed:
            fetched_b = dds.get("fetched_at_utc")
            row = {
                "topic": "flood_road_vs_flood_report", "tag": "OPEN",
                "source_a": "thaiwater_flood_road",
                "value_a": f"{o.get('station_name')} = {o['value']} cm",
                "observed_a": o["observed_at_utc"],
                "source_b": "dds_flood_report",
                "value_b": f"no road listed for district '{district}'",
                "observed_b": _fr_latest_ts,
                "note": ("thaiwater_flood_road reports a nonzero depth at a station in "
                         f"district '{district}' but DDS's own flood_report (latest "
                         f"fetch {_fr_latest_ts}) has no road listed for that district -- "
                         "not resolved."),
            }
            contradictions.append(row)
            store.insert_contradiction(
                conn, observed_at_utc=generated_at, topic=row["topic"],
                source_a=row["source_a"], value_a=row["value_a"],
                observed_a_utc=row["observed_a"],
                source_b=row["source_b"], value_b=row["value_b"],
                observed_b_utc=row["observed_b"], note=row["note"])

    result["contradictions"] = contradictions

    # --- สิ่งที่ยังขาด (OPEN) --------------------------------------------------------
    missing = [
        {"item": "governor_shared_flooded_roads", "tag": "OPEN",
         "note": "Registered in sources/registry.yaml but not yet imported (manual-import "
                 "source, no fetcher by design) -- cannot cross-check against it yet."},
        {"item": "bma_klongmap", "tag": "OPEN",
         "note": "Still HTTP 403 as of the last check -- parser stays ready, dormant."},
        {"item": "pages 4-6 of the DDS daily PDF", "tag": "OPEN",
         "note": "Raster images (weather map, satellite photo, rain-distribution maps, "
                 "7-day forecast chart) -- zero extractable text, not covered without OCR."},
        {"item": "dds_nowcast_gif", "tag": "OPEN",
         "note": "Stored as an image snapshot only, never parsed -- no numeric reading "
                 "comes from this source."},
        {"item": "rtsd_2010_ground_level_map / rid_flood_risk_map", "tag": "OPEN",
         "note": "Static reference assets, not wired into observations/documents yet."},
    ]
    if not dds_obs:
        missing.insert(0, {"item": "dds_daily_pdf", "tag": "OPEN",
                           "note": "No DDS daily bulletin has been collected into the store yet."})
    result["missing"] = missing

    # --- ภาพรวม (overall picture) -- INSTINCT, descriptive counts only, NEVER a score ---
    # Directly answers the project's own framing for this check ("ต้องชั่งน้ำหนักแล้ว
    # ประเมินภาพรวม" -- weigh and assess the overall picture): every number below is a
    # plain count of what the tables above already show (station statuses AS PUBLISHED by
    # their own agency, contradiction count, source count, staleness count) -- nothing is
    # combined into a single index or ranked, and no threshold decides anything here.
    overall_notes = []
    # FIX (2026-10-03, founder-reported bug): this used to count raw `status` words
    # straight off `near_canal`/`near_pumps` -- EVERY historical row within range, no
    # dedup, no staleness check at all (`readout.build_readout`'s own README/AGENTS.md
    # note never claimed this line was gated). That meant a STALE row (sometimes the
    # ONLY row, e.g. WL.SSB.08's last reading 5-6 days old) could drive this sentence's
    # CRITICAL/etc count while sitting right next to "สถานะปัจจุบัน" looking exactly like
    # the stations' current status -- a real violation of the house "stale -> never
    # decides a colour" rule, even on a run where the actual RED/GREEN decision
    # (`kb._classify_current_local_state`, which already only reads `status_counts` from
    # THIS SAME gated loop below) was unaffected. Built from the already-deduplicated,
    # already-gated `f4["measured"]` rows (the single freshness gate, `lwl.is_fresh`,
    # already ran above) -- a STALE row is counted in `status_counts_stale` and shown as
    # NOT used for the decision, never folded into `status_counts`.
    #
    # FIX (2026-10-03): this loop used to `continue` past any row whose
    # `source` was not `thaiwater_canal_waterlevel`/`bma_pumphistory`, i.e. it dropped
    # every `dds_daily_pdf` row from this sentence/the UNKNOWN-sentinel decision below --
    # but `kb._answer_state`'s `status_counts` (what ACTUALLY decides
    # `current_local_state`/RED-GREEN via `_classify_current_local_state`) reads ALL of
    # `f4["measured"]` with no such filter. That let a real run show the verbose headline
    # "no fresh value left in this radius -- UNKNOWN" (this sentence, filtered) in the
    # SAME answer whose `current_local_state` was RED, decided by 3 fresh `dds_daily_pdf`
    # "ระดับน้ำวิกฤติ" rows this filter had thrown away before counting -- the display and
    # the decision silently counted different row sets. The filter is now dropped so this
    # loop counts the EXACT SAME set `_answer_state` decides from -- `f4["measured"]` as
    # a whole, no per-source carve-out.
    # fix (2026-10-04): this loop used to count every fresh row in `f4["measured"]`
    # regardless of the dds_canal loop's own `used_for_decision` field (the comment above
    # claimed this was "the EXACT SAME set `_answer_state` decides from", but `kb.py`'s
    # `_answer_state` already reads `used_for_decision` -- see its own fix comment
    # -- so a `canal_outer`/no-coordinate/out-of-radius dds_daily_pdf row, though excluded
    # from `kb.py`'s decision, was still silently folded into THIS prose summary). A row
    # with no `used_for_decision` field at all (thaiwater_canal_waterlevel/bma_pumphistory,
    # already radius-filtered before reaching `measured`) still defaults to "decide iff
    # fresh" -- unchanged for those sources.
    status_counts: dict = {}
    status_counts_stale: dict = {}
    stale_count = 0
    fresh_count = 0
    # fix (2026-10-04): a row that is fresh (tag != STALE) but geo-
    # excluded (canal_outer / no coordinate / outside radius, `used_for_decision=
    # False`) used to be silently dropped from EVERY count here -- invisible to both
    # `status_counts` and `stale_count`, which let the `elif stale_count:` branch below
    # claim "ALL values here are STALE" while such fresh-but-excluded rows also
    # existed, uncounted. Counted (never a decision input) so the headline below can
    # tell "no fresh data at all" apart from "fresh data exists, it's just not local".
    geo_excluded_count = 0
    for row in f4["measured"]:
        st = row.get("status") or "UNKNOWN"
        if row.get("tag") == "STALE":
            stale_count += 1
            status_counts_stale[st] = status_counts_stale.get(st, 0) + 1
            continue
        _used = row.get("used_for_decision")
        if _used is False:
            geo_excluded_count += 1
            continue
        status_counts[st] = status_counts.get(st, 0) + 1
        fresh_count += 1
    if status_counts:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))
        overall_notes.append(
            f"สถานะที่แต่ละหน่วยงานประกาศเองสำหรับสถานีสด (ไม่ STALE) ในรัศมี {radius_km} km "
            f"({fresh_count} reading(s)): {parts}. "
            "นี่คือการนับสถานะที่หน่วยงานต้นทางตั้งไว้เอง (warning/critical/bank ของแต่ละสถานี) "
            "ไม่ใช่คะแนนหรือการจัดอันดับของ pipeline นี้.")
    elif stale_count and not geo_excluded_count:
        overall_notes.append(
            "ไม่มีค่าสดเหลือในรัศมีนี้รอบนี้ -- ค่าทั้งหมดที่มี STALE (ดูด้านล่าง), จึงไม่มีการ"
            "ตัดสินสถานะปัจจุบันจากสถานีเหล่านี้ [UNKNOWN].")
    elif stale_count or geo_excluded_count:
        # fix: at least one fresh-but-geo-excluded row exists -- never
        # claim "ทั้งหมดที่มี STALE" (all values are stale) when that is false.
        overall_notes.append(
            f"ไม่มีค่าที่ตัดสินใน radius นี้รอบนี้ -- {stale_count} แถวเก่าเกินเกณฑ์ (STALE), "
            f"{geo_excluded_count} แถวสดแต่อยู่นอกรัศมี/ไม่มีพิกัดยืนยัน (ไม่ใช่ STALE แต่ไม่ใช้"
            "ตัดสินสถานีนี้ด้วย) -- จึงไม่มีการตัดสินสถานะปัจจุบันจากสถานีเหล่านี้ [UNKNOWN].")
    else:
        overall_notes.append("ยังไม่มีสถานี telemetry ในรัศมีนี้ในรอบนี้ [OPEN].")
    if stale_count:
        stale_parts = ", ".join(f"{k}={v}" for k, v in sorted(status_counts_stale.items()))
        overall_notes.append(
            f"{stale_count} แถวใน 'การระบาย' เป็นค่าเก่ากว่าเกณฑ์ freshness ของแหล่งนั้น (tag "
            f"STALE, สถานะที่อ่านได้ตอนนั้น: {stale_parts}) -- ยังแสดงไว้เพื่อความโปร่งใส แต่ "
            "ไม่ถูกใช้ในการตัดสินสถานะปัจจุบัน (ไม่ควรอ่านเป็นสถานการณ์ปัจจุบัน).")
    if contradictions:
        overall_notes.append(
            f"พบ {len(contradictions)} รายการที่แหล่งข้อมูลไม่ตรงกัน (ดู 'ความขัดแย้งระหว่าง"
            "แหล่ง' ด้านล่าง) -- หน่วยงานไทยหลายหน่วยงานทำงานแข่งกันและข้อมูลไม่สอดคล้องกัน "
            "(project ruling) -- ไม่ resolve ให้ว่าใครถูก, ผู้อ่านต้องชั่งน้ำหนักเอง.")
    overall_notes.append(
        f"ใช้ข้อมูลจาก {len(sources_used)} แหล่งในรอบนี้: {', '.join(sources_used) or '(none in store yet)'}. "
        "แต่ละแหล่งมี trust_tier ของตัวเอง (official_telemetry / official_report / "
        "official_shared_inference) -- ดูรายละเอียดที่ sources/registry.yaml, ไม่ได้ย่อยลงมา "
        "เป็นค่าเดียวที่นี่.")
    result["overall_picture"] = {"tag": "INSTINCT", "notes": overall_notes}

    return result


def _row_table(rows, cols, col_titles=None):
    col_titles = col_titles or cols
    lines = ["| " + " | ".join(col_titles) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(_fmt(r.get(c)) for c in cols) + " |")
    return "\n".join(lines)


def render_markdown(readout: dict) -> str:
    h = readout["header"]
    lines = [
        "# Sammakorn live flood-context readout",
        "",
        f"- centre: {h['centre']['lat']}, {h['centre']['lon']} (ARAYA office, "
        f"หมู่บ้านสัมมากร สะพานสูง)",
        f"- radius: {h['radius_km']} km",
        f"- generated (UTC): {h['generated_at_utc']}",
        f"- as-of date: {h['as_of_date']}",
        f"- sources used this run: {', '.join(h['sources_used']) or '(none in store yet)'}",
        "",
        "**อ่านตารางนี้อย่างไร**: ทุกแถวมี tag -- "
        "**MEASURED** = official_telemetry (หน่วยงานวัดเองด้วยเซนเซอร์ ไม่ผ่านคนคอมไพล์), "
        "**RELAYED** = official_report/compiled bulletin figure ที่ pipeline นี้ relay ต่อมา "
        "ตรง ๆ ไม่ใช่ของ pipeline นี้เอง, "
        "**STALE** = ค่าเก่ากว่าเกณฑ์ freshness (ดู `age_h` ใน JSON) -- แสดงไว้ ไม่ได้ตัดทิ้ง, "
        "**INSTINCT** = engineering judgment call ที่ยังไม่ verified (เช่น การจับคู่ candidate "
        "ระหว่างแหล่งข้อมูลโดยชื่อ ไม่ใช่ยืนยันว่าเป็นสถานีเดียวกันจริง), "
        "**OPEN** = ยังไม่มีข้อมูล. tag เหล่านี้บอกชั้นความน่าเชื่อถือ (`trust_tier` เต็ม ๆ "
        "อยู่ที่ `sources/registry.yaml`), ไม่ใช่คะแนนความเสี่ยง. "
        "**ไม่มีสูตรหรือคะแนนความเสี่ยงใด ๆ ในเอกสารนี้** "
        "(ตามกฎ equation discipline ของ workspace นี้) -- ทุกค่าคือค่าที่ relay/วัดมาตรง ๆ.",
        "",
    ]

    factor_titles = {
        "1_ฝน": "1. ฝน (Rain)", "2_น้ำเหนือ": "2. น้ำเหนือ (Chao Phraya inflow)",
        "3_น้ำทะเลหนุน": "3. น้ำทะเลหนุน (Tide surge)",
        "4_การระบาย": "4. การระบาย (Drainage: canals + pumps)",
        "5_ถนนน้ำท่วม": "5. ถนนน้ำท่วม (Flood-affected roads)",
    }
    for key, title in factor_titles.items():
        f = readout["factors"].get(key)
        if f is None:
            continue
        has_variable = any("variable" in r for r in f["measured"] + f["official_forecast"])
        cols_measured = (["station", "variable", "value", "unit", "status",
                          "observed_at_utc", "source", "tag"] if has_variable else
                         ["station", "value", "unit", "status", "observed_at_utc",
                          "source", "tag"])
        cols_forecast = (["station", "variable", "value", "unit", "observed_at_utc",
                          "source", "tag"] if has_variable else
                         ["station", "value", "unit", "observed_at_utc", "source", "tag"])
        lines.append(f"## {title}")
        if f["measured"]:
            lines.append("**MEASURED**")
            lines.append(_row_table(f["measured"], cols_measured))
            lines.append("")
        if f["official_forecast"]:
            lines.append("**OFFICIAL FORECAST**")
            lines.append(_row_table(f["official_forecast"], cols_forecast))
            lines.append("")
        for m in f["missing"]:
            lines.append(f"- **MISSING [{m['tag']}]** {m['note']}")
        lines.append("")

    lines.append("## โหนดของสัมมากร (Sammakorn's own nodes)")
    for group, rows in readout["sammakorn_nodes"].items():
        lines.append(f"### {group}")
        if rows and "level_m" in rows[0]:
            lines.append(_row_table(
                rows, ["station_code", "name", "level_m", "pumps_on", "pumps_total",
                       "gate_open_m", "status", "dist_km", "observed_at_utc", "tag"]))
        else:
            lines.append(_row_table(
                rows, ["station_code", "name", "value_m", "status", "dist_km",
                       "observed_at_utc", "tag"]))
        lines.append("")

    lines.append("## เสียงจากอินเทอร์เน็ต (social listening)")
    lines.append(
        "อ่านคู่กับสถานีทางการเสมอ -- ตารางนี้เป็น count/lookup ธรรมดา ไม่ใช่คะแนน/ไม่รวมเป็นดัชนี "
        "(ดู `social_listening.py`, `docs/METHOD_social_listening.md` สำหรับ effectiveness record).")
    social = readout.get("social_listening") or {}
    if not social:
        lines.append("ยังไม่มีข้อมูล social listening ในรอบนี้ [OPEN].")
    for area, sec in social.items():
        lines.append(f"### {area}")
        lines.append("**จำนวนรายงานต่อชั่วโมง (plain counts, ไม่ใช่คะแนน)**")
        if sec["hourly_counts"]:
            for hk in sorted(sec["hourly_counts"]):
                lines.append(f"- {hk}: {sec['hourly_counts'][hk]}")
        else:
            lines.append("- (none)")
        lines.append("")
        lines.append("**5 รายงานล่าสุด**")
        if sec["latest5"]:
            lines.append(_row_table(sec["latest5"],
                                    ["soi_place", "state", "observed_at_utc", "publisher_type"]))
        else:
            lines.append("(none)")
        lines.append("")
        if sec["agreement"]:
            lines.append(
                "**agreement กับสถานีทางการที่ใกล้ที่สุด (lookup ต่อสถานี ไม่ใช่คะแนนรวม)**")
            lines.append(_row_table(sec["agreement"],
                                    ["node", "community_state", "station_status", "verdict"]))
        lines.append("")

    lines.append("## ความขัดแย้งระหว่างแหล่ง (Cross-source contradictions -- not resolved)")
    if readout["contradictions"]:
        for c in readout["contradictions"]:
            lines.append(f"- **{c['topic']}**: {c['source_a']}={c['value_a']} "
                         f"({c.get('observed_a')}) vs {c['source_b']}={c['value_b']} "
                         f"({c.get('observed_b')}) -- {c['note']}")
    else:
        lines.append("ไม่พบรายการขัดแย้งในรอบนี้ (ไม่ได้แปลว่าไม่มี -- แค่ pass ตรวจแบบง่าย"
                     "ของรอบนี้ไม่เจอ) [OPEN: coverage is partial, see สิ่งที่ยังขาด]")
    lines.append("")

    lines.append("## สิ่งที่ยังขาด (Open / missing)")
    for m in readout["missing"]:
        lines.append(f"- **[{m['tag']}] {m['item']}**: {m['note']}")
    lines.append("")

    op = readout.get("overall_picture")
    if op:
        lines.append(f"## ภาพรวม (Overall picture -- [{op['tag']}], ไม่ใช่คะแนน/ไม่ใช่การพยากรณ์)")
        for note in op["notes"]:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines)


def write_readout(conn, centre_lat, centre_lon, radius_km, as_of_date=None,
                   out_dir: Path = OUTPUT_DIR):
    readout = build_readout(conn, centre_lat, centre_lon, radius_km, as_of_date)
    date_tag = readout["header"]["as_of_date"]
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"sammakorn_readout_{date_tag}.md"
    json_path = out_dir / f"sammakorn_readout_{date_tag}.json"
    md_path.write_text(render_markdown(readout), encoding="utf-8")
    json_path.write_text(json.dumps(readout, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path, readout


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--centre", nargs=2, type=float, required=True, metavar=("LAT", "LON"))
    ap.add_argument("--radius-km", type=float, default=5.0)
    ap.add_argument("--date", help="Override the as-of date tag (default: today, UTC).")
    ap.add_argument("--db", help="Override the SQLite DB path.")
    args = ap.parse_args()
    conn = store.connect(Path(args.db)) if args.db else store.connect()
    md_path, json_path, _ = write_readout(conn, args.centre[0], args.centre[1],
                                           args.radius_km, as_of_date=args.date)
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()
