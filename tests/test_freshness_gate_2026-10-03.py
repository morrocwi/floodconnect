"""Tests for the single-freshness-gate fix (2026-10-03, founder bug report):
"ทำไมเอไอดึงข้อมูลเก่ามาตอบ จะแก้บั๊กยังไง ควรจะเรียกสมการใหม่ทุกครั้งไม่ใช่เรอ".

The reading used below is the REAL row the diagnosis reproduced against (copied
verbatim from `this repo's own private development tree's data/observations.sqlite` on 2026-10-03,
id=331): station WL.SSB.08, source_id thaiwater_canal_waterlevel, value 0.80 m,
critical=0.45 m, status "CRITICAL" (in `readout.FLOOD_LIKE_STATUS`), observed_at_utc
2026-09-28T06:20:00+00:00 -- the 5-6 day stale reading that the founder saw drive
`current=RED` via `overall_picture.notes[0]`'s un-gated status count. Per this
workspace's floodconnect memory rule "real data only in tests, never simulated", only
the OBSERVED-AT timestamp is varied across scenarios (same convention as
`tests/test_readout.py`/`tests/test_safety_fix_2026-10-02.py`), to probe the gate at
different ages against that one real row's own real thresholds.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_freshness_gate_2026-10-03.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import kb  # noqa: E402
import readout  # noqa: E402
import store  # noqa: E402

CENTRE_LAT, CENTRE_LON = 13.758235, 100.676084  # kb._ANSWER_AREAS["sammakorn"]

# The real WL.SSB.08 row (id=331, this repo's own private development tree's data/observations.sqlite,
# 2026-10-03). `observed_at_utc` is overridden per-scenario below; every other field is
# the row exactly as recorded.
REAL_WL_SSB08 = dict(
    source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.08",
    station_name="ค.แสนแสบ-เสรีไทย 24", lat=13.7805, lon=100.67387,
    variable="canal_water_level_m", value=0.8, unit="m",
    fetched_at_utc="2026-10-02T11:39:47.180416+00:00",
    warning=0.35, critical=0.45, bank=1.91, status="CRITICAL",
    trust_tier="official_telemetry",
)
REAL_WL_SSB08_STALE_OBSERVED_AT = "2026-09-28T06:20:00+00:00"  # as actually recorded
AS_OF = "2026-10-03"  # reference instant: 2026-10-03T00:00:00+00:00 (pinned, deterministic)


@pytest.fixture()
def conn(tmp_path):
    return store.connect(tmp_path / "freshness_gate.sqlite")


def _insert_wl_ssb08(conn, observed_at_utc, status="CRITICAL", value=0.8):
    row = dict(REAL_WL_SSB08)
    row["observed_at_utc"] = observed_at_utc
    row["status"] = status
    row["value"] = value
    store.insert_observation(conn, **row)


# ---------------------------------------------------------------------------
# 1. Stale -> UNKNOWN (the exact founder repro, pinned to a deterministic clock)
# ---------------------------------------------------------------------------

def test_real_stale_row_is_gated_out_never_decides_a_colour(conn, monkeypatch):
    _insert_wl_ssb08(conn, REAL_WL_SSB08_STALE_OBSERVED_AT)  # age ~= 113.7h, > 24h
    full = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 3.0, as_of_date=AS_OF)
    row = full["factors"]["4_การระบาย"]["measured"][0]
    assert row["tag"] == "STALE"
    assert row["age_h"] > 24.0

    # The actual decision path: kb._answer_state only ever counts non-STALE rows into
    # `status_counts` (kb.py `_answer_state`) -- a stale CRITICAL reading must never
    # reach `_classify_current_local_state` as evidence.
    monkeypatch.setattr(kb, "DB_PATH", Path(conn.execute("PRAGMA database_list").fetchone()[2]))
    state_answer = kb._answer_state(CENTRE_LAT, CENTRE_LON, as_of_date=AS_OF)
    assert state_answer["status_counts"] == {}
    assert state_answer["stale_count"] >= 1
    assert state_answer["refresh_suggested"] is True
    assert kb._classify_current_local_state(state_answer) == "UNKNOWN"

    # The display bug itself: `overall_picture`'s own prose must say the stale row was
    # NOT used for the decision, not silently count it as if it were current.
    notes = full["overall_picture"]["notes"]
    assert any("ไม่ถูกใช้ในการตัดสิน" in n for n in notes), notes
    headline_note = notes[0]
    assert "CRITICAL" not in headline_note  # the stale CRITICAL status must not appear
    # as if it were a live station status in the first (headline) sentence.


# ---------------------------------------------------------------------------
# 2. The SAME row with a fresh observed_at -> RED
# ---------------------------------------------------------------------------

def test_same_real_row_fresh_observed_at_decides_red(conn, monkeypatch):
    fresh_observed_at = "2026-10-02T12:00:00+00:00"  # 12h before the AS_OF reference
    _insert_wl_ssb08(conn, fresh_observed_at)
    full = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 3.0, as_of_date=AS_OF)
    row = full["factors"]["4_การระบาย"]["measured"][0]
    assert row["tag"] == "MEASURED"
    assert row["age_h"] <= 24.0

    monkeypatch.setattr(kb, "DB_PATH", Path(conn.execute("PRAGMA database_list").fetchone()[2]))
    state_answer = kb._answer_state(CENTRE_LAT, CENTRE_LON, as_of_date=AS_OF)
    assert state_answer["status_counts"] == {"CRITICAL": 1}
    assert kb._classify_current_local_state(state_answer) == "RED"


# ---------------------------------------------------------------------------
# 3. Fresh-normal + stale-critical mix -> decided by the fresh one only
# ---------------------------------------------------------------------------

def test_fresh_normal_plus_stale_critical_mix_decided_by_fresh_only(conn, monkeypatch):
    _insert_wl_ssb08(conn, REAL_WL_SSB08_STALE_OBSERVED_AT, status="CRITICAL", value=0.8)
    # A second, different station, fresh, NORMAL -- within the same 3km radius.
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.07",
        station_name="ค.แสนแสบ-สนข.บางกะปิ", lat=13.76509, lon=100.64791,
        variable="canal_water_level_m", value=0.20, unit="m",
        observed_at_utc="2026-10-02T18:00:00+00:00",  # fresh (6h before AS_OF reference)
        fetched_at_utc="2026-10-02T18:05:00+00:00",
        trust_tier="official_telemetry", warning=0.50, critical=0.80, bank=1.20,
        status="NORMAL")
    full = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date=AS_OF)
    tags_by_station = {r["station"]: r["tag"] for r in full["factors"]["4_การระบาย"]["measured"]}
    assert tags_by_station["ค.แสนแสบ-เสรีไทย 24"] == "STALE"
    assert tags_by_station["ค.แสนแสบ-สนข.บางกะปิ"] == "MEASURED"

    monkeypatch.setattr(kb, "DB_PATH", Path(conn.execute("PRAGMA database_list").fetchone()[2]))
    state_answer = kb._answer_state(CENTRE_LAT, CENTRE_LON, radius_km=5.0, as_of_date=AS_OF)
    # Only the fresh NORMAL reading counts -- the stale CRITICAL one must not leak in.
    assert state_answer["status_counts"] == {"NORMAL": 1}
    assert kb._classify_current_local_state(state_answer) == "GREEN"


# ---------------------------------------------------------------------------
# 4. Refresh-failure fallback -> stale rows stay stale -> UNKNOWN
# ---------------------------------------------------------------------------

def test_refresh_total_failure_falls_back_to_stale_stored_rows_unknown(conn, monkeypatch):
    """Simulates every wired source failing this run (no network) -- `build_answer`
    must fall back to whatever is already in the DB (the stale real row) rather than
    crash or silently invent freshness, and that stale row must still be gated out of
    the decision (UNKNOWN, never a stale-driven colour)."""
    _insert_wl_ssb08(conn, REAL_WL_SSB08_STALE_OBSERVED_AT)
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    monkeypatch.setattr(kb, "DB_PATH", db_path)

    def _all_sources_fail(area_id=None, verbose=False, all_sources=False):
        return [{"id": "thaiwater_canal_waterlevel", "ok": False, "skipped": False,
                  "note": "simulated: no network this test"}]

    monkeypatch.setattr(kb, "_refresh_relevant_sources", _all_sources_fail)
    payload = kb.build_answer("sammakorn", refresh=True, verbose=False)
    # fix (2026-10-04): the payload's "refresh" is now the compact
    # {total, ok, skipped, failed_ids} form unless verbose=True -- never the raw
    # per-source list, to stay inside the token budget on the default refresh path.
    assert payload["refresh"] == {"total": 1, "ok": 0, "skipped": 0,
                                   "failed_ids": ["thaiwater_canal_waterlevel"]}
    # The real wall-clock "now" is used here (as_of_date not pinned, same as production)
    # -- the stored row is from 2026-09-28, genuinely days old regardless of today's
    # real date, so it is stale under any reasonable "now".
    current = payload["next_action"]["dual_state"]["current_local_state"]
    assert current == "UNKNOWN"


# ---------------------------------------------------------------------------
# 5. --offline path (CLI)
# ---------------------------------------------------------------------------

def test_cli_offline_flag_skips_refresh_and_still_decides_from_fresh_row(conn, monkeypatch, capsys):
    import datetime
    # Dynamically fresh (no as_of_date pin here -- this test is about the --offline
    # wiring, not the gate itself, and the real cmd_answer/build_answer use real
    # wall-clock "now" when as_of_date is not pinned).
    fresh_observed_at = (datetime.datetime.now(datetime.timezone.utc)
                          - datetime.timedelta(hours=2)).isoformat()
    _insert_wl_ssb08(conn, fresh_observed_at)
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    monkeypatch.setattr(kb, "DB_PATH", db_path)

    called = {"refresh": False}

    def _should_not_be_called(*a, **kw):
        called["refresh"] = True
        return []

    monkeypatch.setattr(kb, "_refresh_relevant_sources", _should_not_be_called)

    class Args:
        at = "sammakorn"
        json = True
        offline = True

    rc = kb.cmd_answer(Args())
    assert rc == 0
    assert called["refresh"] is False  # --offline must never call the refresh path
    import json as _json
    payload = _json.loads(capsys.readouterr().out)
    assert payload["refresh"] is None
    assert payload["next_action"]["dual_state"]["current_local_state"] == "RED"


def test_cli_refresh_and_offline_together_is_an_error(capsys, monkeypatch, tmp_path):
    # FIX (2026-10-03, ): this used to hit the real `data/observations.sqlite`
    # path and the real `_refresh_relevant_sources` -- MEASURED on a revert: with the
    # mutual-exclusion check removed, this test actually fetched 35 real RID
    # reservoir-app rows over the live network into the real DB before the `--refresh`/
    # `--offline` error path was ever reached by the code under test (the check runs
    # AFTER `build_answer` would have refreshed in the old code order). Both the DB path
    # and the refresh function are now monkeypatched so this test can never touch the
    # network or the real DB, regardless of where the error check sits.
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "unused_never_touched.sqlite")

    def _must_not_be_called(*a, **kw):
        raise AssertionError("refresh must never run -- the --refresh/--offline "
                              "conflict must be rejected before any fetch")

    monkeypatch.setattr(kb, "_refresh_relevant_sources", _must_not_be_called)

    class Args:
        at = "sammakorn"
        json = True
        refresh = True
        offline = True

    rc = kb.cmd_answer(Args())
    assert rc == 2
    assert "mutually exclusive" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 6. MCP path
# ---------------------------------------------------------------------------

def test_mcp_floodconnect_answer_core_offline_path(conn, monkeypatch):
    sys.path.insert(0, str(HERE / "tools" / "mcp"))
    import floodconnect_mcp as mcp_mod  # noqa: E402
    import datetime

    fresh_observed_at = (datetime.datetime.now(datetime.timezone.utc)
                          - datetime.timedelta(hours=2)).isoformat()
    _insert_wl_ssb08(conn, fresh_observed_at)
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    monkeypatch.setattr(kb, "DB_PATH", db_path)

    called = {"refresh": False}
    monkeypatch.setattr(kb, "_refresh_relevant_sources",
                         lambda *a, **kw: called.__setitem__("refresh", True) or [])

    out = mcp_mod.floodconnect_answer_core("sammakorn", offline=True)
    assert called["refresh"] is False
    assert out["refresh"] is None
    assert out["next_action"]["dual_state"]["current_local_state"] == "RED"


# ---------------------------------------------------------------------------
# 7. Regression: fresh DDS critical + stale canal -> headline must name
#    the fresh DDS status, never the "no fresh value -- UNKNOWN" sentinel, and the
#    decision must be RED (matches the real 2026-10-03 checker repro: 3 fresh
#    dds_daily_pdf "ระดับน้ำวิกฤติ" rows decided RED while the display sentence, filtered
#    to canal/pump sources only, printed the UNKNOWN sentinel in the SAME answer).
# ---------------------------------------------------------------------------

def test_fresh_dds_critical_plus_stale_canal_headline_names_dds_not_unknown(conn, monkeypatch):
    # The stale real WL.SSB.08 row -- gated out, same as scenario 1.
    _insert_wl_ssb08(conn, REAL_WL_SSB08_STALE_OBSERVED_AT)
    # A fresh dds_daily_pdf canal_inner bulletin row, critical, well within 24h of AS_OF.
    # the fix (2026-10-04): a dds_daily_pdf row only decides when it is `canal_inner`
    # AND its own gate has a sourced coordinate within radius_km (see readout.py's
    # `_DDS_GATE_COORDS`) -- the old synthetic placeholder name "คลองแสนแสบ-ทดสอบ" carried
    # neither, so it is replaced here with the REAL captured station name
    # "คลองแสนแสบ-เขตบางกะป" (verbatim from data/observations.sqlite 2026-10-03, id=10250,
    # incl. its real PUA font-artifact codepoint -- see `_normalize_name`'s docstring),
    # which IS in `_DDS_GATE_COORDS` (sourced from sources/canal_normal_levels.yaml
    # WL.SSB.07, 3.14 km from the sammakorn centre -- radius widened to 5.0 km here,
    # same as the other multi-station scenario in this file, so the real coordinate
    # falls inside it). Only `value`/`status`/`observed_at_utc` are varied from the real
    # row (same convention this file's own module docstring already establishes), to
    # exercise the "critical" branch the test's name promises.
    fresh_observed_at = "2026-10-02T12:00:00+00:00"  # 12h before the AS_OF reference
    fetched = "2026-10-02T12:05:00+00:00"
    store.insert_observation(
        conn, source_id="dds_daily_pdf", station_name="คลองแสนแสบ-เขตบางกะป",
        variable="canal_level_0700_m", value=0.95, unit="m",
        observed_at_utc=fresh_observed_at, fetched_at_utc=fetched,
        trust_tier="official_report", critical=0.45, status="ระดับน้ำวิกฤติ",
        provenance={"section": "canal_inner", "header_date_recognized": True})

    full = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date=AS_OF)
    notes = full["overall_picture"]["notes"]
    headline = notes[0]
    assert "UNKNOWN" not in headline, headline
    assert "ระดับน้ำวิกฤติ" in headline, headline

    monkeypatch.setattr(kb, "DB_PATH", Path(conn.execute("PRAGMA database_list").fetchone()[2]))
    state_answer = kb._answer_state(CENTRE_LAT, CENTRE_LON, radius_km=5.0, as_of_date=AS_OF)
    assert state_answer["status_counts"] == {"ระดับน้ำวิกฤติ": 1}
    assert kb._classify_current_local_state(state_answer) == "RED"
    assert state_answer["status_counts_stale"] == {"CRITICAL": 1}
    assert state_answer["evidence_total_count"] == 2

    # The FULL (verbose) evidence list must mark the fresh DDS row as decisive and the
    # stale canal row as not-used -- never the reverse, and never ambiguous. Non-verbose
    # (the default, checked above via `status_counts`/`status_counts_stale`) only
    # carries a small SAMPLE of `evidence` -- see `_trim_evidence`'s own docstring.
    verbose_state = kb._answer_state(CENTRE_LAT, CENTRE_LON, radius_km=5.0, as_of_date=AS_OF,
                                      verbose=True)
    used = {e["station"]: e for e in verbose_state["evidence"] if e["used_for_decision"]}
    not_used = {e["station"]: e for e in verbose_state["evidence"]
                if not e["used_for_decision"]}
    assert any(s == "ระดับน้ำวิกฤติ" for e in used.values() for s in [e["status"]])
    assert "ค.แสนแสบ-เสรีไทย 24" in not_used


def test_mcp_floodconnect_answer_core_default_refreshes_unless_offline(conn, monkeypatch):
    """Refresh-by-default (project decision 2026-10-03): omitting both `refresh` and
    `offline` must still attempt the refresh path (mirrors `kb.py answer` with neither
    `--refresh` nor `--offline`)."""
    sys.path.insert(0, str(HERE / "tools" / "mcp"))
    import floodconnect_mcp as mcp_mod  # noqa: E402

    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    monkeypatch.setattr(kb, "DB_PATH", db_path)

    called = {"refresh": False}
    monkeypatch.setattr(kb, "_refresh_relevant_sources",
                         lambda *a, **kw: called.__setitem__("refresh", True) or [])

    mcp_mod.floodconnect_answer_core("sammakorn")  # no refresh=, no offline=
    assert called["refresh"] is True
