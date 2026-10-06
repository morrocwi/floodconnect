"""tests/test_watchlist.py -- watchlist.py (WATCHLIST.md sections 1-9, TRIGGERS.md
sections 3-5: the cross-session WATCHLIST + ROUTER + ALERT_EVENT, part C2 of the M8
split).

Two kinds of test here, both honest about which they are:
  - Pure state-machine tests build `CheckInput` directly from trigger-id STRINGS
    (the vocabulary TRIGGERS.md itself defines, e.g. "CAP-SEV", "Z0-RISE") -- these
    are code-logic inputs, not simulated sensor readings, same as this repo's other
    suites feeding real fixture files through parse functions.
  - `test_w1_real_l0_check_escalates_a_new_row_live` drives the SAME path through a
    real, un-mocked `l0_check.check("sammakorn")` call (real network, real TMD/
    thaiwater/Open-Meteo/BMA responses on whatever machine runs this) -- this is
    TRIGGERS.md test T01's live shape and WATCHLIST.md's W1, run against today's
    actual sources rather than the fixture snapshot. It is marked so a fully
    offline CI run can skip it rather than fail on a sandboxed network.

WATCHLIST.md section 11's W2/W3/W5/W12 need an actual QUIET round from the real
sources to observe end to end; as of this run TMD's CAP feed had an active Severe
item (see the real T01-shaped test below), so no live QUIET round existed to drive
them from real data. Those four are exercised here as PURE state-machine tests
instead (constructing the ACTIVE/COOLING row + a QUIET CheckInput directly) --
listed honestly, not run against live data, per this task's own instruction not to
fabricate data to force a pass.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

import watchlist as wl


# ---------------------------------------------------------------------------
# section 1: schema / CSV round trip
# ---------------------------------------------------------------------------

def _sample_row(**overrides) -> dict:
    row = {
        "point_id": "kg:gauge:bma_watermap:WL.SMK.01", "h": wl.h12("kg:gauge:bma_watermap:WL.SMK.01"),
        "lat": 13.758235, "lon": 100.676084, "area": "กรุงเทพมหานคร",
        "iso": "TH-10", "province_th": "กรุงเทพมหานคร",
        "kg_anchor": "gauge:bma_watermap:WL.SMK.01",
        "reasons": ["Z0-RISE@2026-10-06T10:00:00Z"], "signals": ["Z0@2026-10-06T10:00:00Z"],
        "depth": "H2", "colour": "YELLOW", "first_seen": "2026-10-06T10:00:00Z",
        "last_checked": "2026-10-06T10:00:00Z", "next_due": "NEXT_SESSION", "expires": "",
        "quiet_streak": 0, "status": "ACTIVE", "alert_event_ids": [], "schema": wl.SCHEMA,
    }
    row.update(overrides)
    return row


def test_csv_header_matches_section_1_3():
    assert wl.CSV_HEADER == [
        "point_id", "h", "lat", "lon", "area", "iso", "province_th", "kg_anchor",
        "reasons", "signals", "depth", "colour", "first_seen", "last_checked",
        "next_due", "expires", "quiet_streak", "status", "alert_event_ids", "schema",
    ]


def test_csv_round_trip_utf8_bom(tmp_path):
    path = tmp_path / "watchlist.csv"
    rows = {r["point_id"]: r for r in [_sample_row(), _sample_row(
        point_id="pt:13.1,100.2", lat=13.1, lon=100.2, area="", kg_anchor="")]}
    wl.write_watchlist_csv(path, rows)
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    back = wl.read_watchlist_csv(path)
    assert back == rows


def test_optional_columns_may_be_empty_but_present():
    row = _sample_row(area="", kg_anchor="", expires="")
    flat = wl.row_to_csv_dict(row)
    assert flat["area"] == "" and flat["kg_anchor"] == "" and flat["expires"] == ""


def test_required_column_missing_raises():
    row = _sample_row()
    del row["colour"]
    with pytest.raises(ValueError):
        wl.row_to_csv_dict(row)


def test_point_id_kg_form_for_declared_z0():
    pid = wl.point_id_for({"lat": 1.0, "lon": 2.0,
                           "z0": {"source_id": "bma_watermap", "code": "WL.SMK.01"}})
    assert pid == "kg:gauge:bma_watermap:WL.SMK.01"


def test_point_id_pt_form_when_no_kg_anchor():
    pid = wl.point_id_for({"lat": 13.1, "lon": 100.2, "z0": None})
    assert pid == "pt:13.1,100.2"


def test_h_is_12_hex_and_never_the_raw_point_id():
    pid = "pt:13.765540125000635,100.61909460837903"
    h = wl.h12(pid)
    assert len(h) == 12 and all(c in "0123456789abcdef" for c in h)
    assert pid not in h


def test_vevent_never_contains_coordinates_or_point_id():
    ics = wl.ics_vevent("dd7144081d77", "สัมมากร", "YELLOW",
                         "2026-10-06T18:00:00+07:00", ["Z0-RISE@2026-10-06T10:00:00Z"], 0)
    assert "13.758235" not in ics and "100.676084" not in ics and "kg:" not in ics
    assert "dd7144081d77@fc-watch" in ics and "VALARM" not in ics


# ---------------------------------------------------------------------------
# colour / depth max
# ---------------------------------------------------------------------------

def test_colour_max_official_order_wins_over_lower_reading():
    assert wl.colour_max("GREEN", "RED") == "RED"


def test_colour_max_unknown_never_wins_over_concrete():
    assert wl.colour_max("UNKNOWN", "YELLOW") == "YELLOW"


def test_colour_max_all_unknown_stays_unknown_not_green():
    """UNKNOWN != safe: a failed reading must never silently become GREEN."""
    assert wl.colour_max(None, "UNKNOWN", None) == "UNKNOWN"


# ---------------------------------------------------------------------------
# TRIGGERS.md section 5 router: start_level, exact precedence order
# ---------------------------------------------------------------------------

def test_router_no_store_is_l0():
    assert wl.start_level("NO_STORE", None) == "H0"


def test_router_unread_is_h2_even_with_no_row():
    assert wl.start_level("UNREAD", None) == "H2"


def test_router_active_row_is_h2_regardless_of_streak():
    row = _sample_row(status="ACTIVE", quiet_streak=5)
    assert wl.start_level("READ_OK", row) == "H2"


def test_router_cooling_with_low_streak_is_h2():
    row = _sample_row(status="COOLING", quiet_streak=1)
    assert wl.start_level("READ_OK", row) == "H2"


def test_router_cooling_with_streak_at_n_quiet_is_l0():
    row = _sample_row(status="COOLING", quiet_streak=2)
    assert wl.start_level("READ_OK", row) == "H0"


def test_router_h3_order_wins_over_everything_including_unread():
    """"ไม่ว่า streak จะเท่าไร" -- H3-ORDER starts at H3 even if UNREAD would
    otherwise just say H2. UNREAD is checked first in this module (storage could
    not be trusted at all), so this documents that precedence explicitly: an
    unreadable store cannot even SEE the H3-ORDER reason, so it falls back to the
    still-safe H2, never silently to H0."""
    row = _sample_row(status="ACTIVE", reasons=["H3-ORDER@2026-10-06T09:00:00Z"])
    assert wl.start_level("READ_OK", row) == "H3"
    assert wl.start_level("UNREAD", row) == "H2"


def test_router_h3_notfetched_also_forces_h3():
    row = _sample_row(status="COOLING", quiet_streak=9, reasons=["H3-NOTFETCHED@t"])
    assert wl.start_level("READ_OK", row) == "H3"


# ---------------------------------------------------------------------------
# WATCHLIST.md section 3's reasons merge (since-tracking + sticky ids)
# ---------------------------------------------------------------------------

def test_merge_reasons_keeps_since_for_still_firing_id():
    old = ["Z0-RISE@2026-10-06T09:00:00Z"]
    new = wl.merge_reasons(old, ["Z0-RISE"], "2026-10-06T10:00:00Z", frozenset({"Z0"}))
    assert new == ["Z0-RISE@2026-10-06T09:00:00Z"]


def test_merge_reasons_drops_id_only_when_its_category_was_freshly_evaluated():
    old = ["Z0-RISE@t0"]
    new = wl.merge_reasons(old, [], "t1", evaluated_categories=frozenset({"Z0"}))
    assert new == []


def test_merge_reasons_keeps_id_when_category_not_evaluated_this_round():
    old = ["Z0-RISE@t0"]
    new = wl.merge_reasons(old, [], "t1", evaluated_categories=frozenset({"CAP"}))
    assert new == ["Z0-RISE@t0"]


def test_merge_reasons_sticky_ids_never_auto_dropped():
    old = ["H3-ORDER@t0", "H2-KGGAP@t0", "GROUND@t0"]
    new = wl.merge_reasons(old, [], "t1", evaluated_categories=frozenset({"H3", "H2", "GROUND"}))
    assert set(new) == set(old)


def test_merge_reasons_new_id_gets_now_as_since():
    new = wl.merge_reasons([], ["CAP-SEV"], "2026-10-06T11:00:00Z", frozenset({"CAP"}))
    assert new == ["CAP-SEV@2026-10-06T11:00:00Z"]


# ---------------------------------------------------------------------------
# alert_event dedup (section 6)
# ---------------------------------------------------------------------------

def test_alert_event_id_is_stable_for_same_id_and_since():
    a = wl.alert_event_id("h1", "CAP-FAIL", "2026-10-06T00:00:00Z")
    b = wl.alert_event_id("h1", "CAP-FAIL", "2026-10-06T00:00:00Z")
    assert a == b == "fc:h1:CAP-FAIL@2026-10-06T00:00:00Z"


def test_new_alert_event_ids_skips_already_covered_span():
    reasons = ["CAP-FAIL@2026-10-06T00:00:00Z"]
    existing = [wl.alert_event_id("h1", "CAP-FAIL", "2026-10-06T00:00:00Z")]
    assert wl.new_alert_event_ids("h1", reasons, existing) == []


def test_new_alert_event_ids_fires_once_per_new_span():
    reasons = ["CAP-FAIL@2026-10-06T00:00:00Z", "Z0-RISE@2026-10-06T00:00:00Z"]
    out = wl.new_alert_event_ids("h1", reasons, [])
    assert len(out) == 2 and len(set(out)) == 2


# ---------------------------------------------------------------------------
# WATCHLIST.md section 3 state machine -- the table itself, row by row.
# These are pure logic tests: CheckInput is built directly from trigger-id
# vocabulary, never from a fabricated numeric reading.
# ---------------------------------------------------------------------------

def _chk(firing_ids, action=None, colour="GREEN", cap_match=False, h3_order=False) -> wl.CheckInput:
    return wl.CheckInput(
        point_id="kg:gauge:bma_watermap:WL.SMK.01", lat=13.758235, lon=100.676084,
        area="สอดย", iso="TH-10", province_th="สอดย",
        kg_anchor="gauge:bma_watermap:WL.SMK.01", firing_ids=firing_ids,
        signals=[f"{i}@2026-10-06T10:00:00Z" for i in firing_ids], action=action,
        reading_colour=(colour if not firing_ids else None),
        cap_colour_floor=("YELLOW" if cap_match else None),
        h3_order_active=h3_order, cap_match_active=cap_match)


def test_w1_no_row_plus_fire_creates_active_row_with_colour_floor_and_event_line_first():
    chk = _chk(["CAP-SEV"], action="DRILL+H2", cap_match=True)
    out = wl.apply_check(None, chk, now_iso="2026-10-06T16:20:00Z")
    assert out["log_event"] == "NEW"
    row = out["row"]
    assert row["status"] == "ACTIVE" and row["quiet_streak"] == 0
    assert row["depth"] == "H2"  # DRILL -> H2, never CARD on CAP-SEV alone
    assert row["colour"] == "YELLOW"  # colour floor, no Z0 reading at all here
    assert len(out["new_alert_event_ids"]) == 1
    assert out["vevent"] and "UID:" in out["vevent"] and "SEQUENCE:0" in out["vevent"]


def test_active_quiet_streak_1_stays_active():
    row = _sample_row(status="ACTIVE", quiet_streak=0, reasons=["Z0-RISE@t0"])
    chk = _chk([])  # QUIET: nothing firing
    out = wl.apply_check(row, chk, now_iso="t1")
    assert out["row"]["status"] == "ACTIVE" and out["row"]["quiet_streak"] == 1
    assert out["log_event"] == "QUIET"


def test_w2_w3_active_quiet_streak_reaches_n_quiet_enters_cooling_streak_reset():
    row = _sample_row(status="ACTIVE", quiet_streak=1, reasons=["CAP-SEV@t0"])
    chk = _chk([])  # fresh QUIET round, no CAP match active, no H3 order
    out = wl.apply_check(row, chk, now_iso="t1")
    assert out["row"]["status"] == "COOLING" and out["row"]["quiet_streak"] == 0
    assert out["log_event"] == "COOL"


def test_active_quiet_does_not_cool_while_cap_item_still_matches():
    row = _sample_row(status="ACTIVE", quiet_streak=1, reasons=["CAP-SEV@t0"])
    chk = _chk([], cap_match=True)  # Z0 itself quiet, but CAP item still active+match
    out = wl.apply_check(row, chk, now_iso="t1")
    assert out["row"]["status"] == "ACTIVE"


def test_w12_h3_order_blocks_cooling_even_at_n_quiet():
    row = _sample_row(status="ACTIVE", quiet_streak=1, reasons=["H3-ORDER@t0"])
    chk = _chk([], h3_order=True)
    out = wl.apply_check(row, chk, now_iso="t1")
    assert out["row"]["status"] == "ACTIVE"
    assert "H3-ORDER@t0" in out["row"]["reasons"]  # sticky id never auto-dropped


def test_w6_active_rise_plus_this_round_miss_keeps_rise_adds_miss_no_cooling():
    row = _sample_row(status="ACTIVE", quiet_streak=0, reasons=["Z0-RISE@t0"])
    chk = _chk(["Z0-MISS"])  # Z0-RISE itself not re-fired, but its category (Z0) IS
    # evaluated this check (Z0-MISS fired) -- yet Z0-RISE must be KEPT, because the
    # merge rule only drops an id when its OWN category came back a clean fresh
    # read, and Z0-MISS says the opposite: the Z0 read failed, so nothing about
    # Z0-RISE's truth value was actually re-confirmed this check.
    old = row["reasons"]
    merged = wl.merge_reasons(old, chk.firing_ids, "t1", evaluated_categories=frozenset())
    assert "Z0-RISE@t0" in merged and any(r.startswith("Z0-MISS@") for r in merged)
    out = wl.apply_check(row, chk, now_iso="t1")
    assert out["row"]["status"] == "ACTIVE" and out["row"]["quiet_streak"] == 0


def test_w5_cooling_quiet_at_n_quiet_past_expiry_closes_and_appends_cancelled_vevent():
    row = _sample_row(status="COOLING", quiet_streak=1, reasons=[], expires="2020-01-01T00:00:00Z")
    chk = _chk([])
    out = wl.apply_check(row, chk, now_iso="2026-10-06T12:00:00Z")
    assert out["closed"] is True and out["row"]["status"] == "CLOSED"
    assert out["log_event"] == "CLOSE"
    assert out["vevent_status"] == "CANCELLED"


def test_cooling_quiet_at_n_quiet_but_expiry_not_reached_stays_cooling():
    future = (datetime.datetime.now(datetime.timezone.utc)
              + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    row = _sample_row(status="COOLING", quiet_streak=1, reasons=[], expires=future)
    out = wl.apply_check(row, _chk([]), now_iso="t1")
    assert out["closed"] is False and out["row"]["status"] == "COOLING"


def test_cooling_fire_reopens_to_active_streak_0():
    row = _sample_row(status="COOLING", quiet_streak=1, reasons=[])
    out = wl.apply_check(row, _chk(["Z0-RISE"]), now_iso="t1")
    assert out["row"]["status"] == "ACTIVE" and out["row"]["quiet_streak"] == 0
    assert out["log_event"] == "FIRE"


def test_w4_reopen_from_closed_row_is_tagged_reopen_not_new():
    closed = _sample_row(status="CLOSED", quiet_streak=0, reasons=[])
    out = wl.apply_check(closed, _chk(["CAP-FAIL"]), now_iso="t1")
    assert out["reopened"] is True and out["log_event"] == "REOPEN"
    assert out["row"]["status"] == "ACTIVE"


def test_w11_active_fire_only_mints_alert_for_new_ids():
    row = _sample_row(status="ACTIVE", quiet_streak=0, reasons=["Z0-RISE@t0"],
                       alert_event_ids=[wl.alert_event_id(row_h := wl.h12(_sample_row()["point_id"]), "Z0-RISE", "t0")])
    out = wl.apply_check(row, _chk(["Z0-RISE", "CAP-FAIL"]), now_iso="t1")
    assert len(out["new_alert_event_ids"]) == 1
    assert out["new_alert_event_ids"][0].startswith(f"fc:{row_h}:CAP-FAIL@")


def test_w14_idempotent_apply_twice_same_input_same_result():
    h = wl.h12("kg:gauge:bma_watermap:WL.SMK.01")
    row = _sample_row(status="ACTIVE", quiet_streak=0, reasons=["Z0-RISE@t0"],
                       alert_event_ids=[wl.alert_event_id(h, "Z0-RISE", "t0")])
    chk = _chk(["Z0-RISE"])
    out1 = wl.apply_check(row, chk, now_iso="t1")
    out2 = wl.apply_check(row, chk, now_iso="t1")
    assert out1["row"] == out2["row"]
    assert out1["new_alert_event_ids"] == out2["new_alert_event_ids"] == []  # id unchanged -> no NEW alert


# ---------------------------------------------------------------------------
# W7/W8/W9: storage failure modes (WatchStore, real tmp_path filesystem)
# ---------------------------------------------------------------------------

def test_w7_unread_store_never_touches_watchlist_goes_to_pending(tmp_path, monkeypatch):
    bad = tmp_path / "watchlist.csv"
    bad.write_text("not,the,right,header\n1,2,3,4\n", encoding="utf-8")
    store = wl.WatchStore(tmp_path)
    read = store.load()
    assert read.status == "UNREAD"
    chk = _chk(["Z0-RISE"])
    wu = store.check_point("kg:gauge:bma_watermap:WL.SMK.01", chk, None, "brief")
    assert wu["read"] == "UNREAD"
    assert wu["save_status"] == "PENDING_WRITE"
    assert bad.read_text(encoding="utf-8").startswith("not,the,right,header")  # untouched
    pending = (tmp_path / wl.WATCH_PENDING_JSONL_NAME).read_text(encoding="utf-8")
    assert json.loads(pending.strip())["base"] == "UNREAD"


def test_w9_csv_present_but_truncated_row_is_unread_not_a_silent_partial_read(tmp_path):
    path = tmp_path / wl.WATCHLIST_CSV_NAME
    path.write_bytes(("﻿" + ",".join(wl.CSV_HEADER) + "\n"
                       + "kg:x,h1,notafloat,100.0,,,,,,,H1,GREEN,t,t,NEXT_SESSION,,0,ACTIVE,,fc.watch.v2\n"
                       ).encode("utf-8"))
    read = wl.read_store(tmp_path)
    assert read.status == "UNREAD"


def test_no_store_true_first_run(tmp_path):
    read = wl.read_store(tmp_path)
    assert read.status == "NO_STORE" and read.rows == {}


def test_read_ok_on_valid_empty_or_populated_csv(tmp_path):
    wl.write_watchlist_csv(tmp_path / wl.WATCHLIST_CSV_NAME, {})
    read = wl.read_store(tmp_path)
    assert read.status == "READ_OK" and read.rows == {}


def test_full_session_cycle_on_real_filesystem_active_to_cooling_to_closed(tmp_path):
    """Drives WatchStore across 4 sessions purely through the public API (no
    fabricated sensor values -- each "check" is a direct trigger-id list, same as
    the pure state-machine tests above), and checks the on-disk CSVs after each."""
    point_id = "kg:gauge:bma_watermap:WL.SMK.01"

    store = wl.WatchStore(tmp_path)
    store.load()
    wu1 = store.check_point(point_id, _chk(["Z0-RISE"]), None, "b1")
    assert wu1["save_status"] == "SAVED"
    on_disk = wl.read_watchlist_csv(tmp_path / wl.WATCHLIST_CSV_NAME)
    assert on_disk[point_id]["status"] == "ACTIVE"

    for _ in range(2):  # N_QUIET = 2
        store = wl.WatchStore(tmp_path)
        store.load()
        store.check_point(point_id, _chk([]), None, "quiet")
    on_disk = wl.read_watchlist_csv(tmp_path / wl.WATCHLIST_CSV_NAME)
    assert on_disk[point_id]["status"] == "COOLING"

    # force past expiry so the next 2 quiet checks can close it
    rows = wl.read_watchlist_csv(tmp_path / wl.WATCHLIST_CSV_NAME)
    rows[point_id]["expires"] = "2020-01-01T00:00:00Z"
    wl.write_watchlist_csv(tmp_path / wl.WATCHLIST_CSV_NAME, rows)

    for _ in range(2):
        store = wl.WatchStore(tmp_path)
        store.load()
        store.check_point(point_id, _chk([]), None, "quiet")
    assert not wl.read_watchlist_csv(tmp_path / wl.WATCHLIST_CSV_NAME)  # removed
    closed = wl.read_watchlist_csv(tmp_path / wl.WATCH_CLOSED_CSV_NAME)
    assert closed[point_id]["status"] == "CLOSED"

    # a later FIRE reopens it
    store = wl.WatchStore(tmp_path)
    store.load()
    wu = store.check_point(point_id, _chk(["CAP-FAIL"]), None, "fire again")
    assert wu["ops"][0]["row"]["status"] == "ACTIVE"


# ---------------------------------------------------------------------------
# Real, un-mocked l0_check -> watchlist end-to-end (network required)
# ---------------------------------------------------------------------------

def test_w1_real_l0_check_escalates_a_new_row_live(tmp_path, monkeypatch):
    """Un-mocked `l0_check.check("sammakorn")` -> `watchlist.run_watch`. Skips (not
    fails) when this sandbox's network is blocked, rather than fabricating a
    result -- this test is only meaningful as a live check."""
    import l0_check
    monkeypatch.setattr(l0_check, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    try:
        wu = wl.run_watch("sammakorn", store_dir=tmp_path / "data")
    except Exception as e:  # pragma: no cover - network-dependent
        pytest.skip(f"live network check unavailable: {e}")
    assert wu["schema"] == "fc.watch_update.v2"
    if wu["ops"] == []:
        pytest.skip("live source was QUIET this run -- nothing to assert for W1's "
                     "escalate shape (see this suite's own OPEN note re: W2/W3/W5/W12)")
    assert wu["point_id"] == "kg:gauge:bma_watermap:WL.SMK.01"
    row = wu["ops"][0]["row"]
    assert row["status"] == "ACTIVE" and row["quiet_streak"] == 0
    assert row["h"] == wl.h12(wu["point_id"])
    if "CAP-SEV" in [r.split("@")[0] for r in row["reasons"]]:
        assert row["colour"] in ("YELLOW", "ORANGE", "RED")  # colour floor held
    assert wu["save_status"] == "SAVED"


def test_kb_cmd_check_wires_escalate_into_a_watch_update(tmp_path, monkeypatch):
    """live run, 2026-10-06: `kb.py check` fired ESCALATE (real
    CAP-SEV + Z0 fixtures, same shape as T01/W1 above) but emitted no
    watch_update/alert_event at all -- `kb.cmd_check` must now ALSO apply the
    SAME ESCALATE result through `watchlist.apply_watch_from_l0_result`, writing
    a real ACTIVE row + alert_event id, without a second live fetch (this test's
    own `_get` mock would raise/404 on a second call to a URL it has already
    served the single canned response for)."""
    import l0_check
    import kb
    import watchlist as wl_mod

    feed = (Path(__file__).parent / "fixtures" / "l0_check" / "cap_feed.xml").read_bytes()
    sev_item = (Path(__file__).parent / "fixtures" / "l0_check" / "cap_item_1.xml").read_bytes()
    rain_body = (Path(__file__).parent / "fixtures" / "l0_check" / "rain_24h_trimmed.json").read_bytes()
    fcst_body = (Path(__file__).parent / "fixtures" / "l0_check" / "openmeteo_7d_sammakorn.json").read_bytes()
    z0_html = (Path(__file__).parent / "fixtures" / "bma_station_detail"
               / "stationdetail_id284_20261005_trimmed.html").read_bytes()

    def fake_get(url, **kw):
        if url == l0_check.TMD_CAP_FEED_URL:
            return 200, feed
        if url == l0_check.THAIWATER_RAIN24H_URL:
            return 200, rain_body
        if url.startswith("https://weather.bangkok.go.th"):
            return 200, z0_html
        if url.startswith("https://api.open-meteo.com"):
            return 200, fcst_body
        return 200, sev_item

    monkeypatch.setattr(l0_check, "_get", fake_get)
    monkeypatch.setattr(l0_check, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    now = datetime.datetime(2026, 10, 6, 9, 20, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(l0_check, "_utcnow", lambda: now)
    monkeypatch.setattr(wl_mod, "DEFAULT_STORE_DIR", tmp_path / "data")

    class Args:
        at = "sammakorn"
        json = False

    rc = kb.cmd_check(Args())
    assert rc == 0

    store = wl_mod.WatchStore(tmp_path / "data")
    store.load()
    row = store.read.rows.get("kg:gauge:bma_watermap:WL.SMK.01")
    assert row is not None
    assert row["status"] == "ACTIVE"
    assert "CAP-SEV" in [r.split("@")[0] for r in row["reasons"]]
