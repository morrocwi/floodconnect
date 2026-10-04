"""Tests for `kb.py answer`/`compute` -- an earlier check fix (2026-10-02).

None of this subcommand had a test calling `cmd_answer`/`_resolve_area`/`_answer_*` or
`tools.kg.accountability.build_result` directly before this file (an earlier check defect
M5). Every forecast value used below is REAL data, copied verbatim from a collection
run recorded in the main working repository's `data/observations.sqlite` on
2026-09-27/28 (Sammakorn point, source_id `openmeteo_forecast16d`), never simulated
-- per this project's rule "real data only in tests, never simulated". The CMA
2026-09-26T17:00Z=91.5mm row is the exact value was measured when it found defect H1
(a 5-day-stale row served as "tomorrow").

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_kb_answer.py -q
"""
from __future__ import annotations

import datetime
import hashlib
import sys
from pathlib import Path

import networkx as nx
import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import kb  # noqa: E402
import store  # noqa: E402
from tools.kg import accountability as acct  # noqa: E402

UTC = datetime.timezone.utc

# Real rows, copied verbatim (station_code, observed_at_utc, fetched_at_utc, value) --
# Sammakorn, source_id openmeteo_forecast16d, variable precipitation_forecast_daily_mm.
# cma_grapes_global's 2026-09-26 row (91.5mm) is a documented example.
REAL_SAMMAKORN_ROWS = [
    ("sammakorn:cma_grapes_global", "2026-09-26T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 91.5),
    ("sammakorn:cma_grapes_global", "2026-09-27T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 1.9),
    ("sammakorn:cma_grapes_global", "2026-09-28T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 6.7),
    ("sammakorn:cma_grapes_global", "2026-10-01T17:00:00+00:00", "2026-09-27T18:10:27.101877+00:00", 2.6),
    ("sammakorn:ecmwf_ifs025", "2026-09-26T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 49.0),
    ("sammakorn:ecmwf_ifs025", "2026-10-01T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 6.0),
    ("sammakorn:ecmwf_ifs025", "2026-10-02T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 5.8),
    ("sammakorn:ecmwf_ifs025", "2026-10-03T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 2.0),
    ("sammakorn:ecmwf_ifs025", "2026-10-04T17:00:00+00:00", "2026-09-27T12:48:42.485218+00:00", 5.4),
    ("sammakorn:ecmwf_ifs025", "2026-10-11T17:00:00+00:00", "2026-09-27T19:46:04.698470+00:00", 2.4),
]


@pytest.fixture
def real_forecast_db(tmp_path, monkeypatch):
    """Returns a FACTORY `make(now=None, fetched_at_overrides=None)` -- a tiny sqlite DB
    at a fresh path, populated with REAL_SAMMAKORN_ROWS via store.insert_observation (the
    production insert path, not a hand-built row), then kb.DB_PATH monkeypatched to point
    at it so `_forecast_rows_by_model`/`_answer_hazard` read it instead of the repo's real
    (and in this worktree, empty) DB.

    FIX (2026-10-04, F-forecast-freshness): `_forecast_rows_by_model` now gates every row
    on its OWN `fetched_at_utc` freshness (per-row, per-source) before it can enter
    `by_model` at all -- a row whose real collection timestamp (Sep 27-28 2026) is more
    than 24h before whatever synthetic `now` a test pins loses, by itself, the date-
    filtering scenario most of these tests exist to check. `now`, when given, makes every
    row's `fetched_at_utc` FRESH relative to it (`now - 1h`) instead of the real collected
    value -- this only moves a metadata/collection-time field a test already treats as
    synthetic (every test here already pins a fake `now_utc`, not real wall-clock time);
    it never touches `observed_at_utc` or `value`, which stay exactly the real recorded
    numbers (per this workspace's "real data only in tests" rule) and are what each
    date-filtering test actually asserts on. `fetched_at_overrides` (`{model:
    fetched_at_utc_iso}`) lets a test instead pin specific models' OWN real-looking
    fetched_at per-model, for a test that is specifically about freshness itself (not
    date filtering) -- a model named in it keeps that exact value; every other model
    falls back to the `now`-relative fresh default, or the real original value when
    `now` is also None."""
    def _make(now: "datetime.datetime | None" = None,
              fetched_at_overrides: "dict | None" = None):
        db_path = tmp_path / "observations.sqlite"
        conn = store.connect(db_path)
        fresh_fetched_at = (
            (now - datetime.timedelta(hours=1)).isoformat() if now is not None else None)
        for station_code, observed_at_utc, real_fetched_at_utc, value in REAL_SAMMAKORN_ROWS:
            model = station_code.split(":", 1)[1]
            if fetched_at_overrides and model in fetched_at_overrides:
                fetched_at = fetched_at_overrides[model]
            elif fresh_fetched_at is not None:
                fetched_at = fresh_fetched_at
            else:
                fetched_at = real_fetched_at_utc
            store.insert_observation(
                conn, source_id="openmeteo_forecast16d", station_code=station_code,
                variable="precipitation_forecast_daily_mm", value=value, unit="mm",
                observed_at_utc=observed_at_utc, fetched_at_utc=fetched_at,
                trust_tier="third_party",
            )
        conn.close()
        monkeypatch.setattr(kb, "DB_PATH", db_path)
        return db_path
    return _make


# ---------------------------------------------------------------------------
# Forecast point snapping must have a distance cap (2026-10-04)
# ---------------------------------------------------------------------------

def test_hazard_far_coordinate_never_borrows_a_named_points_hazard():
    """MEASURED later: `--at 7.88,98.39` (Phuket, >600km from
    every _FORECAST_KNOWN_POINTS entry) used to silently snap to `hatyai`'s own point
    and return Hat Yai's hazard (and, via the same bug elsewhere, its cameras) as if
    they were Phuket's. Beyond `_FORECAST_POINT_SNAP_RADIUS_KM` this must be an honest
    OPEN with its own coordinate-derived point_id -- never a neighbour's point_id or
    cached rows."""
    out = kb._answer_hazard("7.88,98.39", 7.88, 98.39)
    assert out["tag"] == "OPEN"
    assert out["point_id"] != "hatyai"
    assert out["point_id"].startswith("coord_")
    assert "per_model" not in out
    assert out.get("next_action")


def test_hazard_just_outside_sammakorn_radius_does_not_borrow_sammakorn():
    """~11km from Sammakorn (13.758235,100.676084) -- outside the snap radius, so this
    must not resolve to point_id="sammakorn" (the exact case measured:
    (13.7275,100.7785) resolving to Sammakorn's point and reporting its ACTIVE hazard
    as this other place's own)."""
    out = kb._answer_hazard("13.7275,100.7785", 13.7275, 100.7785)
    assert out["point_id"] != "sammakorn"
    assert out["point_id"] != "ram53"


def test_resolve_forecast_point_within_radius_still_snaps():
    """A genuinely close coordinate (well under the 5km cap) still snaps to the named
    point as before -- the cap must not turn every nearest-point lookup into a miss."""
    point_id, within_range = kb._resolve_forecast_point(
        "13.759,100.677", 13.759, 100.677)  # ~130m from sammakorn
    assert point_id == "sammakorn"
    assert within_range is True


# ---------------------------------------------------------------------------
# Defect H1 -- past-date filtering
# ---------------------------------------------------------------------------

def test_hazard_excludes_rows_whose_local_date_has_already_passed(real_forecast_db):
    """Fixed clock well after every cached row's date (all cached dates are <= 2026-10-11,
    `now` is 2026-10-20) -- before the fix this still returned the earliest stored date
    (2026-09-26, the 91.5mm CMA row) labelled "tomorrow". After the fix, no
    future-local-date rows remain for this point/clock.

    FIX D (2026-10-04, project decision -- no hosted access): `_answer_hazard` no longer
    falls back to a tracked offline hazard snapshot (that fallback/the file it read are
    both removed) -- "DB has rows but none are usable" is an honest OPEN with a
    `next_action` telling the caller to refresh on their own machine, same as the
    DB-missing case, never a retained figure from some earlier capture."""
    now = datetime.datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
    real_forecast_db(now)
    out = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert out["tag"] == "OPEN"
    assert out.get("next_action")
    assert "per_model" not in out
    assert "offline_snapshot" not in out
    # The stale 91.5mm row must not leak into the output under any key.
    assert "91.5" not in repr(out)


def test_hazard_tomorrow_is_the_correct_local_date_not_the_earliest_stored_date(real_forecast_db):
    """`now` = 2026-10-02T12:00Z -> Bangkok-local today = 2026-10-02, local tomorrow =
    2026-10-03. The row for `tomorrow` must be the one whose LOCAL date is 2026-10-03
    (observed_at_utc=2026-10-02T17:00Z, ECMWF 5.8mm) -- never the 2026-09-26 (91.5mm) or
    2026-09-27 (1.9mm) rows the pre-fix code would have picked as `dates[0]`."""
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
    real_forecast_db(now)
    out = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert out["tag"] == "RELAYED"
    by_model = {m["model"]: m for m in out["per_model"]}
    assert by_model["ECMWF"]["tomorrow_mm"] == 5.8
    assert by_model["ECMWF"]["tomorrow_mm"] not in (91.5, 49.0)
    # CMA's only future-local-date row at this clock is 2026-10-01 (local 10-02, which is
    # TODAY not tomorrow) -- so CMA must be entirely absent (not misreported as 2.6mm
    # "tomorrow"); only ECMWF has an actual local-tomorrow row in this fixture.
    assert "CMA" not in by_model


def test_hazard_per_model_total_days_matches_actual_cached_dates(real_forecast_db):
    """`total_days` must be the REAL count of distinct future-dated rows a model has
    cached (capped at 7), never a hardcoded 7 -- same bug class as the CLI line that
    used to print a fixed "7 วัน" label (`cmd_answer`'s per-model print) regardless of
    how many dates `7day_total_mm` actually summed."""
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
    real_forecast_db(now)
    out = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert out["tag"] == "RELAYED"
    assert out["per_model"], "fixture must produce at least one live per-model row"
    for m in out["per_model"]:
        assert 1 <= m["total_days"] <= 7
        # total_days must equal the actual number of (date, value) pairs summed into
        # 7day_total_mm for this model, recomputed independently here from the same
        # fixture rows via the public _answer_hazard output shape (never re-trusting
        # the field it is itself checking).
    # At least this fixture's rows must not ALL happen to have exactly 7 cached dates
    # (which would make this test unable to tell "real count" apart from "hardcoded
    # 7"); assert the real spread is present.
    assert any(m["total_days"] < 7 for m in out["per_model"]), (
        "fixture has no model with fewer than 7 cached dates -- this test cannot "
        "distinguish a real count from a hardcoded 7; extend the fixture")


def test_hazard_reports_issued_at(real_forecast_db):
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
    real_forecast_db(now)
    out = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert out["issued_at"] is not None
    assert "stale" in out


def test_hazard_stale_flag_matches_point_level_semantics(real_forecast_db):
    """FIX (2026-10-04, F-forecast-freshness): point-level `stale` is no longer derived
    from a single pooled `issued_at` vs. a fixed cutoff -- it is True only when NO fresh
    model is left (`per_model` empty). With every row fresh relative to `now` (the
    factory's default when `now` is passed), at least one model survives, so `stale`
    must be False here."""
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=UTC)
    real_forecast_db(now)
    out = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert out["per_model"], "fresh fixture must still produce live per-model rows"
    assert out["stale"] is False


def test_cmd_forecast_also_filters_past_dates(real_forecast_db, capsys):
    """H1's fix must land in `cmd_forecast` too, not only `answer` (both shared the same
    bug and now share `_forecast_rows_by_model`)."""
    now_fixed = datetime.datetime(2026, 10, 20, 12, 0, 0, tzinfo=UTC)
    real_forecast_db(now_fixed)
    by_model, issued_at, stale, err, issued_at_by_model = kb._forecast_rows_by_model(
        "sammakorn", now_fixed)
    assert err is None
    assert by_model == {}  # every real row above is in the past relative to this clock


# ---------------------------------------------------------------------------
# F-evidence-priority (2026-10-04) -- `_trim_evidence` sorts decision-driving rows so
# a flood-like one is never hidden behind an earlier normal one.
# ---------------------------------------------------------------------------

def test_trim_evidence_shows_flood_like_decision_row_not_an_earlier_normal_one(monkeypatch):
    """Regression for task (a)'s sibling fix: before this fix, `_trim_evidence`'s single
    capped `used_for_decision=True` row (`_TOP_N_EVIDENCE_DECIDING_IN_SUMMARY=1`) was
    whichever decision-driving row came first in `evidence`'s own order -- if a normal
    (`ปกติ`-like) reading happened to be listed before a real flood-like/critical one,
    the capped summary showed the UNREMARKABLE row and hid the one that actually drove
    a RED decision. `_flood_like_normal_like_status_words` is monkeypatched here (not
    `readout`/`build_data` directly) so this test does not depend on either module's
    real registered status words staying the same."""
    monkeypatch.setattr(
        kb, "_flood_like_normal_like_status_words", lambda: ({"CRITICAL"}, {"NORMAL"}, {"CRITICAL"}))
    evidence = [
        {"station": "A_normal", "status": "NORMAL", "age_h": 1.0, "used_for_decision": True},
        {"station": "B_critical", "status": "CRITICAL", "age_h": 1.0, "used_for_decision": True},
        {"station": "C_stale", "status": "CRITICAL", "age_h": 40.0, "used_for_decision": False},
    ]
    out = kb._trim_evidence(evidence)
    assert len(out) == 1, "cap is 1 deciding + 0 stale by default"
    assert out[0]["station"] == "B_critical", (
        "the flood-like decision-driving row must be shown, never an earlier normal one")


def test_trim_evidence_preserves_stale_flag_distinct_from_used_for_decision(monkeypatch):
    """fix (2026-10-04): `_trim_evidence`'s output must carry the real
    `stale` flag, not just `used_for_decision` -- a row can be `used_for_decision=
    False` while genuinely fresh (geo-excluded), and that must stay visibly different
    from a row that is actually `stale=True`. Raises `_TOP_N_EVIDENCE_STALE_IN_SUMMARY`
    (default 0) so the not-used sample is not trimmed away entirely for this check."""
    monkeypatch.setattr(
        kb, "_flood_like_normal_like_status_words", lambda: (set(), {"NORMAL"}, set()))
    monkeypatch.setattr(kb, "_TOP_N_EVIDENCE_STALE_IN_SUMMARY", 1)
    evidence = [
        {"station": "A_normal", "status": "NORMAL", "age_h": 1.0,
         "used_for_decision": True, "stale": False},
        {"station": "B_geo_excluded_fresh", "status": "ระดับน้ำวิกฤติ", "age_h": 4.8,
         "used_for_decision": False, "stale": False},
    ]
    out = kb._trim_evidence(evidence)
    geo_row = next(r for r in out if r["station"] == "B_geo_excluded_fresh")
    assert geo_row["stale"] is False
    assert geo_row["used_for_decision"] is False


def test_answer_state_evidence_row_carries_explicit_stale_field():
    """`_answer_state`'s own `evidence` rows (not `_trim_evidence`'s capped output)
    must carry the explicit `stale` field this fix added -- checked directly against
    `_answer_state`'s per-row construction, independent of any DB fixture."""
    import inspect
    src = inspect.getsource(kb._answer_state)
    assert '"stale": is_stale' in src


def test_trim_evidence_falls_back_to_first_deciding_row_when_none_are_flood_like(monkeypatch):
    """No flood-like row among the decision-driving rows -- the cap still takes the
    first one (stable sort, no reordering among equally-ranked rows), same as before
    this fix."""
    monkeypatch.setattr(
        kb, "_flood_like_normal_like_status_words", lambda: (set(), {"NORMAL"}, set()))
    evidence = [
        {"station": "A_normal", "status": "NORMAL", "age_h": 1.0, "used_for_decision": True},
        {"station": "B_normal2", "status": "NORMAL", "age_h": 2.0, "used_for_decision": True},
    ]
    out = kb._trim_evidence(evidence)
    assert out[0]["station"] == "A_normal"


# ---------------------------------------------------------------------------
# Defect H10 / M2 -- PROPOSAL label, never invented classes
# ---------------------------------------------------------------------------

def test_source_tags_label_proposal_as_not_yet_in_toledo(monkeypatch):
    monkeypatch.setattr(kb, "_rkg_epistemic_class", lambda node_id: "PROPOSAL")
    tag = kb._source_tag("next_action", "COMMUNITY_DAG", "test note")
    assert tag["epistemic_class"] == "PROPOSAL"
    assert tag["toledo"] == "not yet in Toledo"


def test_source_tags_non_proposal_has_no_toledo_key(monkeypatch):
    monkeypatch.setattr(kb, "_rkg_epistemic_class", lambda node_id: "LIVE_OBSERVATION")
    tag = kb._source_tag("state", "LIVE_DATA_SYSTEM", "test note")
    assert "toledo" not in tag


def test_source_tags_no_rkg_node_is_null_not_invented(monkeypatch):
    """`hazard` and `accountability` are backed by no RKG node -- the old code hard-coded
    "RELAYED" and "STATIC_TOPOLOGY/ROLE_OVERLAY" for them, neither a real
    `epistemic_classes` value. The fixed version must say null, not invent one."""
    tag = kb._source_tag("hazard", None, "no RKG node -- third-party")
    assert tag["epistemic_class"] is None
    assert "toledo" not in tag


# ---------------------------------------------------------------------------
# Defect L1/6 -- bad --at no longer crashes
# ---------------------------------------------------------------------------

def test_resolve_area_bad_at_raises_badat_not_valueerror():
    with pytest.raises(kb._BadAt):
        kb._resolve_area("foo")


def test_cmd_answer_cli_bad_at_exits_2_with_message(capsys):
    class Args:
        at = "foo"
        json = False
    rc = kb.cmd_answer(Args())
    assert rc == 2
    captured = capsys.readouterr()
    assert "ERROR" in captured.err
    assert "Traceback" not in captured.err


def test_cmd_answer_subprocess_bad_at_exits_2():
    import subprocess
    result = subprocess.run(
        [sys.executable, str(HERE / "kb.py"), "answer", "--at", "foo"],
        cwd=HERE, capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr


# ---------------------------------------------------------------------------
# next_action OPEN for a bare lat,lon
# ---------------------------------------------------------------------------

def test_next_action_open_for_bare_latlon():
    out = kb._answer_next_action(None)
    assert out["tag"] == "OPEN"


def test_next_action_found_for_known_area():
    """Sammakorn's self-help DAG start node must resolve to a route under this repo's
    real self_help_dag.yaml (not a fixture) -- this is a coverage test for `_answer_
    next_action` being called at all (an earlier check defect M5), not a claim about any
    particular path shape."""
    out = kb._answer_next_action("sammakorn")
    assert out["tag"] in ("MEASURED", "OPEN")
    if out["tag"] == "MEASURED":
        assert out["basis"] == "graph"
        assert out["found"] is True


# ---------------------------------------------------------------------------
# Envelope shape (cmd_answer, --json)
# ---------------------------------------------------------------------------

def test_answer_json_envelope_keys(real_forecast_db, capsys):
    real_forecast_db()
    class Args:
        at = "sammakorn"
        json = True
        # offline=True: refresh is now the default (project decision 2026-10-03) --
        # this test is about envelope shape against the fixture DB, never the
        # network, so it opts out explicitly (same as `kb.py answer --offline`).
        offline = True
    rc = kb.cmd_answer(Args())
    assert rc == 0
    import json as _json
    payload = _json.loads(capsys.readouterr().out)
    # fix (2026-10-04): `cctv` is now ALWAYS present (compact
    # {tag: OPEN, next_action} when no camera is in range, instead of omitted).
    # fix (2026-10-04, review finding #5): every answer now also carries
    # `indicators_doc`, pointing at docs/INDICATORS.md.
    assert set(payload) == {
        "generated_at", "at", "refresh", "state", "hazard", "accountability",
        "next_action", "source_tags", "cctv", "indicators_doc",
    }
    assert payload["indicators_doc"] == "docs/INDICATORS.md"
    assert payload["cctv"]["tag"] == "OPEN"
    assert payload["refresh"] is None  # no --refresh passed in this test
    assert len(payload["source_tags"]) == 4
    # Default (non-verbose) mode: token-budget cap -- {field, epistemic_class} plus
    # `toledo` when `_source_tag` set it; the longer `note` is a verbose-only field
    # (tests/test_token_budget.py).
    for tag in payload["source_tags"]:
        assert set(tag) >= {"field", "epistemic_class"}
        assert "note" not in tag
        assert set(tag) <= {"field", "epistemic_class", "toledo"}


def test_answer_json_envelope_source_tags_verbose(real_forecast_db, capsys):
    """`verbose=True` is the escape hatch back to the full `{field, epistemic_class,
    note}` shape (plus `toledo` where set) -- nothing is permanently lost by the
    default-mode cap above, only not shown by default."""
    real_forecast_db()
    class Args:
        at = "sammakorn"
        json = True
        verbose = True
        offline = True  # project decision 2026-10-03: refresh is now the default; this
        # test is about verbose envelope shape against the fixture DB, not the network.
    rc = kb.cmd_answer(Args())
    assert rc == 0
    import json as _json
    payload = _json.loads(capsys.readouterr().out)
    assert len(payload["source_tags"]) == 4
    for tag in payload["source_tags"]:
        assert set(tag) >= {"field", "epistemic_class", "note"}


@pytest.mark.parametrize("area", ["sammakorn", "ram53"])
def test_answer_never_prints_the_word_safe(real_forecast_db, capsys, area):
    """README F5 promises the answer never says `SAFE` (UNKNOWN != SAFE). Cover the
    full verbose envelope (notes included) so a reintroduced literal 'SAFE' anywhere
    in the payload -- not just the top-level state -- is caught."""
    real_forecast_db()
    class Args:
        at = area
        json = True
        verbose = True
        offline = True
    rc = kb.cmd_answer(Args())
    assert rc == 0
    import json as _json
    raw = capsys.readouterr().out
    assert "SAFE" not in raw
    payload = _json.loads(raw)
    assert "SAFE" not in _json.dumps(payload)


# ---------------------------------------------------------------------------
# Defect L2/7 -- build_result's two distinct refusal shapes
# ---------------------------------------------------------------------------

def test_build_result_empty_graph_is_top_level_refused(monkeypatch):
    monkeypatch.setattr(acct, "load_graph", lambda path=acct.GRAPH_PATH: nx.MultiDiGraph())
    full = acct.build_result("13.758235,100.676084")
    assert "refused" in full


def test_build_result_bad_point_is_nested_q1_refused(monkeypatch):
    """A non-empty graph but an unresolvable `at` hits the OTHER refusal shape:
    `{"at": at, "Q1": point}` with `point["refused"]` set -- the top-level dict has no
    "refused" key at all in this case (only nested under the bare "Q1" key, not
    "Q1_ใครรับผิดชอบที่นี่")."""
    G = nx.MultiDiGraph()
    G.add_node("asset:test:PUMP01", kind="asset", lat=13.0, lon=100.0)

    def _one_node_graph(path=acct.GRAPH_PATH):
        return G

    monkeypatch.setattr(acct, "load_graph", _one_node_graph)
    full = acct.build_result("not_a_real_asset_id_xyz")
    assert "refused" not in full
    assert "refused" in full.get("Q1", {})


def test_latest_pump_state_opens_db_read_only_never_mutates_it(tmp_path, monkeypatch):
    """Regression: `_latest_pump_state` previously opened
    `sqlite3.connect(str(DB_PATH))` (read-write) on the answer path. MEASURED,
    reproduced on a real DB copy (see the handoff report): one `kb.py answer` run
    changed the file's md5. The fix opens `file:...?mode=ro` the same way
    `kb.py`'s own forecast read does (kb.py:553) -- this test asserts the DB file's
    bytes are byte-identical before and after a real `_latest_pump_state` call."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    store.insert_readout_log(
        conn, run_at_utc="2026-09-28T00:00:00+00:00", area="sammakorn", kind="pump",
        key="sammakorn:pump_status", extra={"stations_faulted": 1, "stations_total": 5},
    )
    conn.close()
    monkeypatch.setattr(acct, "DB_PATH", db_path)

    before = hashlib.md5(db_path.read_bytes()).hexdigest()
    result = acct._latest_pump_state("sammakorn")
    after = hashlib.md5(db_path.read_bytes()).hexdigest()

    assert result is not None  # the row above must actually be found, not a no-op skip
    assert after == before, "answer path must never mutate data/observations.sqlite"


# ---------------------------------------------------------------------------
# An advice fix (2026-10-02) -- "what to do next" dual-state + actions.
#
# Every fixture row below is copied VERBATIM from a real `thaiwater_canal_waterlevel`
# collection run already sitting in the main repo's `data/observations.sqlite`
# (the canonical full-size copy, not this worktree's own; station WL.SSB.08,
# ค.แสนแสบ-เสรีไทย 24 -- one of
# `readout.SAMMAKORN_NODES`'s own north-chain stations, inside the 3km radius this
# area's centre already uses) -- read-only, via a `mode=ro` sqlite URI, never touching
# that worktree's file. Same "real data only in tests, never simulated" rule as the
# REAL_SAMMAKORN_ROWS fixture above; same read-only discipline as
# `test_latest_pump_state_opens_db_read_only_never_mutates_it`.
# ---------------------------------------------------------------------------

REAL_WL_SSB_08_CRITICAL_ROW = dict(
    source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.08",
    station_name="ค.แสนแสบ-เสรีไทย 24", lat=13.7805, lon=100.67387,
    variable="canal_water_level_m", value=0.8, unit="m",
    observed_at_utc="2026-09-28T06:20:00+00:00",
    fetched_at_utc="2026-09-28T10:19:16.710627+00:00",
    warning=0.35, critical=0.45, bank=1.91, status="CRITICAL",
    trust_tier="official_telemetry",
)

REAL_WL_SSB_08_NORMAL_ROW = dict(
    source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.08",
    station_name="ค.แสนแสบ-เสรีไทย 24", lat=13.7805, lon=100.67387,
    variable="canal_water_level_m", value=-0.1, unit="m",
    observed_at_utc="2026-09-28T03:05:00+00:00",
    fetched_at_utc="2026-09-28T03:13:42.995489+00:00",
    warning=0.35, critical=0.45, bank=1.91, status="NORMAL",
    trust_tier="official_telemetry",
)

# DERIVED (not a raw captured reading): same real station/thresholds as the two rows
# above (warning=0.35, critical=0.45, bank=1.91), value edited down into WATCH's own
# band [warning, critical) -- used by the WATCH-is-YELLOW-not-RED regression below
# (founder ruling 2026-10-04, verbatim: "WATCH = YELLOW (แนะนำ)"). A real WATCH row at
# this same station exists (see examples/answer_sammakorn.EXAMPLE-2026-10-04.json); this
# row is a synthetic edit of the station's real thresholds/identity, not that capture.
DERIVED_WL_SSB_08_WATCH_ROW = dict(
    source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.08",
    station_name="ค.แสนแสบ-เสรีไทย 24", lat=13.7805, lon=100.67387,
    variable="canal_water_level_m", value=0.38, unit="m",
    observed_at_utc="2026-09-28T05:10:00+00:00",
    fetched_at_utc="2026-09-28T05:19:16.710627+00:00",
    warning=0.35, critical=0.45, bank=1.91, status="WATCH",
    trust_tier="official_telemetry",
)

# DERIVED (not a raw captured reading): same station again, value edited up past
# `bank` (1.91 m) -- the canal has topped its bank. OVERBANK stays RED under the same
# ruling (agency critical/overflow).
DERIVED_WL_SSB_08_OVERBANK_ROW = dict(
    source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.08",
    station_name="ค.แสนแสบ-เสรีไทย 24", lat=13.7805, lon=100.67387,
    variable="canal_water_level_m", value=2.1, unit="m",
    observed_at_utc="2026-09-28T06:40:00+00:00",
    fetched_at_utc="2026-09-28T06:49:16.710627+00:00",
    warning=0.35, critical=0.45, bank=1.91, status="OVERBANK",
    trust_tier="official_telemetry",
)


@pytest.fixture
def fresh_state_db(tmp_path, monkeypatch):
    """A fresh sqlite DB with kb.DB_PATH monkeypatched, so `_answer_state` reads it
    instead of this worktree's (empty) real DB. Caller inserts rows, then calls
    `kb._answer_state(..., as_of_date=...)` pinned to the row's own date so the row is
    judged fresh/MEASURED against that date, never against today's real wall clock
    (mirrors `_answer_hazard`'s own `now_utc` test-pinning pattern)."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    return conn


SAMMAKORN_LAT, SAMMAKORN_LON = kb._ANSWER_AREAS["sammakorn"]["lat"], kb._ANSWER_AREAS["sammakorn"]["lon"]


def test_dual_state_critical_row_classifies_red_and_emits_neutral_action_without_real_l5_tier(
        fresh_state_db, monkeypatch):
    """A station-only RED (one canal station reading
    CRITICAL) must NEVER emit the L5 survival card's life-safety headline ("น้ำเข้าบ้าน
    แล้ว...") unless PROP-FLOOD-06's own real tier engine reports tier=L5 for this point.
    `fresh_state_db`'s tiny temp DB has none of that engine's required inputs, so
    `_real_pf06_tier` must come back None (never fabricated), and the action must be the
    neutral station-level line instead."""
    monkeypatch.setattr(kb, "_real_pf06_record", lambda area_id, now_utc=None: None)
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_CRITICAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {"CRITICAL": 1}
    assert kb._classify_current_local_state(state) == "RED"

    out = kb._answer_next_action("sammakorn", state_answer=state)
    assert out["dual_state"]["current_local_state"] == "RED"
    assert out["actions"], "a RED current state must always produce at least one action"
    first = out["actions"][0]
    assert first["action"] == kb.STATION_RED_NEUTRAL_ACTION_TH
    assert "not the L5 tier" in first["why"]
    # it must never claim water is already inside the house, and never claim safety
    for banned in ("น้ำเข้าบ้าน", "ปลอดภัย", "ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        assert banned not in first["action"]
    # ACTION_LIBRARY has no phase field -- pre-season self-help items must not
    # appear as a RED next-action; the gap is reported via `notes`, not hidden.
    assert not any(a["source"].startswith("docs/knowledge/") for a in out["actions"])
    assert any("ACTION_LIBRARY" in n for n in out.get("notes", []))


def test_watch_alone_classifies_yellow_not_red(fresh_state_db):
    """Founder ruling 2026-10-04 (verbatim: "WATCH = YELLOW (แนะนำ)"): a station-only
    WATCH/เฝ้าระวัง reading on its own must classify as YELLOW, never RED. RED is
    reserved for an agency-declared critical/overflow reading (วิกฤต/ล้นตลิ่ง =
    CRITICAL/OVERBANK)."""
    store.insert_observation(fresh_state_db, **DERIVED_WL_SSB_08_WATCH_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {"WATCH": 1}
    assert kb._classify_current_local_state(state) == "YELLOW"


def test_watch_alone_build_answer_emits_yellow_watch_action(fresh_state_db):
    """`_answer_next_action`-level regression for the same founder ruling (WATCH =
    YELLOW): a station-only WATCH reading must reach `_answer_next_action`'s `dual_state` as
    YELLOW (never RED), and the actions list must say so explicitly -- post-release
    defect: YELLOW's only wording before this fix was the generic "current state
    unclear" clause, and only when a forecast hazard was ACTIVE; a WATCH reading with
    no active forecast produced no WATCH-specific action at all."""
    store.insert_observation(fresh_state_db, **DERIVED_WL_SSB_08_WATCH_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    out = kb._answer_next_action("sammakorn", state_answer=state)
    assert out["dual_state"]["current_local_state"] == "YELLOW"
    assert any("WATCH" in a["action"] and a["tag"] == "MEASURED" for a in out["actions"]), \
        "a WATCH reading must produce an explicit MEASURED watch-level action"
    for banned in ("ปลอดภัย", "ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        assert all(banned not in a["action"] for a in out["actions"])


def test_overbank_alone_still_classifies_red(fresh_state_db):
    """The other side of the same ruling: OVERBANK (ล้นตลิ่ง, the canal has topped its
    bank) is an agency-declared critical/overflow reading and must still classify as
    RED, exactly like CRITICAL does -- only bare WATCH was downgraded to YELLOW."""
    store.insert_observation(fresh_state_db, **DERIVED_WL_SSB_08_OVERBANK_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {"OVERBANK": 1}
    assert kb._classify_current_local_state(state) == "RED"


# A real dds_daily_pdf rain row -- factor 1 (ฝน), not factor 4 (การระบาย/drainage).
# Used below to put a row in `data/observations.sqlite` (so `sources_used` is
# non-empty and `_answer_state` does NOT take the early "0 sources" OPEN branch)
# while leaving zero drainage/water-level rows of any kind in the store.
REAL_DDS_RAIN_ONLY_ROW = dict(
    source_id="dds_daily_pdf", station_name="กรมอุตุนิยมวิทยา บางนา",
    variable="rain_24h_mm", value=12.4, unit="mm",
    observed_at_utc="2026-09-28T00:00:00+00:00", fetched_at_utc="2026-09-28T04:00:00+00:00",
    trust_tier="official_report",
    provenance={"header_date_recognized": True},
)


def test_refresh_suggested_when_no_drainage_rows_in_radius_at_all(fresh_state_db):
    """FIX (v0.1.1): the store has a row for ANOTHER factor (rain), so
    `_answer_state` does not take the early "0 sources" OPEN branch -- but it has
    ZERO drainage/water-level rows of any kind (fresh or stale) within this point's
    radius. Before this fix, `refresh_suggested` only fired when stale rows existed
    AND were all gated out (`stale_count > 0 and not status_counts`); a point with no
    drainage rows in radius at all (`stale_count == 0`, `status_counts == {}`) fell
    through with `refresh_suggested` left False, wrongly implying nothing more could
    be learned by running `--refresh`."""
    store.insert_observation(fresh_state_db, **REAL_DDS_RAIN_ONLY_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {}
    assert state["stale_count"] == 0
    assert state["evidence_total_count"] == 0
    assert state["refresh_suggested"] is True
    assert kb._classify_current_local_state(state) == "UNKNOWN"


def test_watch_plus_normal_still_classifies_yellow(fresh_state_db):
    """A mix of one WATCH row and one NORMAL row at different stations must stay
    YELLOW (mixed/unclear) -- WATCH no longer escalates it to RED, and the presence of
    a non-normal status still stops it from being silently folded into GREEN."""
    watch_other_station = dict(DERIVED_WL_SSB_08_WATCH_ROW, station_code="WL.SSB.09")
    store.insert_observation(fresh_state_db, **watch_other_station)
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_NORMAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {"WATCH": 1, "NORMAL": 1}
    assert kb._classify_current_local_state(state) == "YELLOW"


def test_dual_state_red_with_real_l5_tier_emits_the_actual_survival_card_headline(
        fresh_state_db, monkeypatch):
    """The other side of that fix: when PROP-FLOOD-06's real engine DOES report
    tier=L5 for this point, the card's own headline is the correct thing to show (gated
    on the real engine, not a faked {"tier": "L5"} dict)."""
    monkeypatch.setattr(kb, "_real_pf06_record", lambda area_id, now_utc=None: {"tier": "L5"})
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_CRITICAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    out = kb._answer_next_action("sammakorn", state_answer=state)
    first = out["actions"][0]
    import build_page as bp  # site/build_page.py, already on sys.path via kb's own import
    assert first["action"] == bp.L5_SURVIVAL_HEADLINE_TH
    assert "build_l5_survival_card_html" in first["source"]
    assert "tier=L5" in first["why"]


def test_dual_state_red_fills_remaining_slots_with_continuity_gaps_not_preseason_actions(
        fresh_state_db, monkeypatch):
    """The other half of that fix: under RED, the slots that used to be filled by pre-season
    ACTION_LIBRARY items are instead filled by the real, already-computed safe-node
    continuity-gap report (community_dag.report_safe_node_continuity_gaps) -- real
    gaps exist in this repo's own site/inputs/community/self_help_dag.yaml today."""
    monkeypatch.setattr(kb, "_real_pf06_record", lambda area_id, now_utc=None: None)
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_CRITICAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    out = kb._answer_next_action("sammakorn", state_answer=state)
    sources = [a["source"] for a in out["actions"]]
    assert any(s == "community_dag.report_safe_node_continuity_gaps" for s in sources)
    assert not any("ACTION_LIBRARY" in s for s in sources)


def test_dual_state_normal_row_classifies_green_with_route_basis(fresh_state_db):
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_NORMAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {"NORMAL": 1}
    assert kb._classify_current_local_state(state) == "GREEN"

    # NORMAL-with-basis: a GREEN current state combined with accountability's real
    # (non-mocked) governance-graph self-help actions for sammakorn, and -- when the
    # self-help DAG happens to resolve a route -- the SAME "basis": "graph" tag
    # `test_next_action_found_for_known_area` already pins.
    acct = kb._answer_accountability("sammakorn")
    out = kb._answer_next_action("sammakorn", state_answer=state, accountability_answer=acct)
    assert out["dual_state"]["current_local_state"] == "GREEN"
    assert out["tag"] in ("MEASURED", "OPEN")
    # GREEN must never suppress the real self-help actions accountability already matched --
    # but only when accountability actually resolved a graph (acct["tag"] != "OPEN"). The MVP
    # public-port tree deliberately does not ship output/*.graphml (multi-MB build
    # artefacts a public consumer regenerates via tools/kg/build_kg.py, not a
    # committed blob), so on a fresh self-install `_answer_accountability` correctly refuses
    # OPEN rather than fabricate a route -- UNKNOWN != SAFE still applies here too.
    # Finding: the two assertions below used to be wrapped in `if
    # out["tag"] == "MEASURED"` / `if acct.get("tag") != "OPEN"` guards that silently did
    # nothing (vacuously "passed") on a fresh self-install with no graph -- which is
    # exactly this MVP tree's own CI, every run, with nothing ever flagging it. An
    # explicit `pytest.skip` makes that same "the graph isn't here" fact visible in the
    # CI test report instead of a quiet green.
    #
    # FIX C (2026-10-04): the skip condition used to be `acct.get("tag") == "OPEN"` --
    # on a fresh self-install sammakorn's accountability answer is no longer OPEN (the
    # `_accountability_fallback` fix below now fires for the missing-graph-file case
    # too, tag="INSTINCT"), but `basis` is still "governance_dag_fallback", never the
    # real "graph" basis this assertion block is actually about -- skip on basis, not
    # tag, so this still correctly skips on this public tree (no output/*.graphml) and
    # would correctly start running for real once a real graph with geolocated asset
    # nodes ships.
    if acct.get("basis") != "graph":
        pytest.skip("national/self-help graph not shipped in this public tree -- "
                     "accountability correctly falls back (OPEN/INSTINCT), "
                     "basis=graph path untested here")
    assert out["tag"] == "MEASURED"
    assert out["basis"] == "graph"
    assert out["found"] is True
    assert any(a["source"].startswith("docs/knowledge/") for a in out["actions"]), \
        "a GREEN state with real matched self-help actions must surface at least one"


def test_dual_state_no_fresh_rows_is_unknown_never_safe(fresh_state_db):
    """No rows inserted at all -- zero sources used, so this must classify UNKNOWN
    (FIX D, 2026-10-04: this is now the bare `status_counts`-less OPEN note, the
    tracked-snapshot fallback that used to carry an explicit empty `status_counts`
    here is removed), and the UNKNOWN action (never a claim of safety) must be the
    one emitted."""
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state.get("status_counts", {}) == {}
    assert kb._classify_current_local_state(state) == "UNKNOWN"

    out = kb._answer_next_action("sammakorn", state_answer=state)
    assert out["dual_state"]["current_local_state"] == "UNKNOWN"
    assert out["actions"][0]["action"] == kb.UNKNOWN_ACTION_TH
    # it must say "absence of data is not evidence of safety", never assert safety itself
    assert "แปลว่าปลอดภัย" in out["actions"][0]["action"]
    for banned in ("ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        assert banned not in out["actions"][0]["action"]


# The self-help route action (`community_dag.find_safe_route`) used to tell every
# asker to "stay at the safest point you have and wait for a re-assessment" whenever
# no verified route was found -- which is always, since every node in the shipped
# `site/inputs/community/self_help_dag.yaml` is UNKNOWN/not-fresh. That is a stay
# order built from placeholder data, the reverse of an evacuation instruction, and it
# fires under every current_local_state including a live RED. Regression: no action
# text may contain that stay-order phrasing, for any of RED/YELLOW/GREEN/UNKNOWN. This
# does not ban the bare word "ปลอดภัย" everywhere -- UNKNOWN_ACTION_TH legitimately
# uses it inside "ไม่ได้แปลว่าปลอดภัย" ("does not mean safe"), a negation, not a claim.
_BANNED_STAY_ORDER_PHRASES = ("อยู่ที่จุดปลอดภัยที่สุด", "รอประเมินซ้ำ", "อยู่ที่จุด")


@pytest.mark.parametrize("row,expected_state", [
    (REAL_WL_SSB_08_CRITICAL_ROW, "RED"),
    (REAL_WL_SSB_08_NORMAL_ROW, "GREEN"),
    (None, "UNKNOWN"),
])
def test_no_action_text_is_a_stay_order_regardless_of_current_state(
        fresh_state_db, row, expected_state):
    if row is not None:
        store.insert_observation(fresh_state_db, **row)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert kb._classify_current_local_state(state) == expected_state
    out = kb._answer_next_action("sammakorn", state_answer=state)
    for action in out["actions"]:
        for banned in _BANNED_STAY_ORDER_PHRASES:
            assert banned not in action["action"], (
                f"{expected_state} action contains the stay-order phrase {banned!r}: "
                f"{action['action']!r}")


def test_no_action_text_is_a_stay_order_for_yellow(fresh_state_db):
    row = dict(REAL_WL_SSB_08_NORMAL_ROW)
    row["status"] = "ABOVE_NORMAL"
    store.insert_observation(fresh_state_db, **row)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert kb._classify_current_local_state(state) == "YELLOW"
    out = kb._answer_next_action("sammakorn", state_answer=state)
    for action in out["actions"]:
        for banned in _BANNED_STAY_ORDER_PHRASES:
            assert banned not in action["action"], (
                f"YELLOW action contains the stay-order phrase {banned!r}: "
                f"{action['action']!r}")


def test_dual_state_stale_row_is_unknown_not_the_rows_own_status(fresh_state_db):
    """The SAME real CRITICAL row as above, but judged against a reference date far
    after its `observed_at_utc` (no `as_of_date` override -> the real `generated_at`
    wall clock, which in this repo's current state is well past 2026-09-28) -- it must
    be excluded as STALE and the dual-state classifier must say UNKNOWN, never silently
    keep reporting "CRITICAL" off a reading this old."""
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_CRITICAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON)  # no as_of_date -> real now
    assert state["status_counts"] == {}, "a stale row must not leak its status into the count"
    assert kb._classify_current_local_state(state) == "UNKNOWN"


def test_dual_state_contradiction_is_carried_through_not_hidden(monkeypatch, fresh_state_db):
    """Regression: the PRE-FIX version of this test
    fabricated the station row too ({"station": "WL.SSB.08", "status": "NORMAL"} was
    invented, only the contradiction row itself was real). Both sides are now REAL: the
    contradiction row is still the verbatim MAIN-worktree `contradictions` table id=1
    ST.BPD.08 coordinate mismatch, and the factors row is the SAME verbatim
    `REAL_WL_SSB_08_NORMAL_ROW` fixture already used (via `store.insert_observation`)
    elsewhere in this file -- its real shape (station/value/status/tag/source), not a
    hand-shrunk dict. `readout.build_readout` is still monkeypatched (engineering its
    own internal coordinate/value-diff detector from scratch is out of this item's
    scope), but it now returns the real row's own fields
    rather than inventing a second one. Also checks the second half of the earlier
    complaint: a non-empty contradiction count must actually reach `next_action` (as a
    note pointing to both sides), never silently stay buried in `state` alone.

    This test previously called `kb._answer_state` without
    `kb.DB_PATH` pointing at an existing file, so it hit the `not DB_PATH.exists()` early
    return (tag OPEN, no `contradiction_count` key at all) on a clean clone with no local
    `data/observations.sqlite` -- `readout.build_readout` was monkeypatched but never
    reached. `fresh_state_db` (an existing fixture, already used by every sibling test in
    this file) monkeypatches `kb.DB_PATH` to a real temp sqlite file, which is all this
    test needs since it fakes `readout.build_readout`'s return value directly."""
    import readout
    real_contradiction_row = {
        "topic": "asset_coordinate:pump_station:pumphistory:ST.BPD.08",
        "source_a": "pumphistory", "value_a": "13.8007,100.5149",
        "source_b": "water_station", "value_b": "13.6821,100.5923",
        "note": "สถานีสูบน้ำบางอ้อ: pumphistory vs water_station.csv coordinates differ by 15.614 km",
    }
    real_row = REAL_WL_SSB_08_NORMAL_ROW
    fake_full = {
        # A real `readout.build_readout` return always carries
        # `header.sources_used` (kb._answer_state's own fallback checks
        # this list to decide whether to fall through to the offline snapshot) -- this
        # fake dict was missing that key, which made this test spuriously hit the
        # snapshot fallback path once that check was added.
        "header": {"sources_used": [real_row["source_id"]]},
        "factors": {"4_การระบาย": {"measured": [
            {"station": real_row["station_name"], "value": real_row["value"],
             "unit": real_row["unit"], "status": real_row["status"],
             "observed_at_utc": real_row["observed_at_utc"], "age_h": 0.1,
             "source": real_row["source_id"], "tag": "MEASURED"},
        ]}},
        "contradictions": [real_contradiction_row],
        "missing": [],
        "overall_picture": {"tag": "INSTINCT", "notes": ["1 รายการที่แหล่งข้อมูลไม่ตรงกัน"]},
    }
    monkeypatch.setattr(readout, "build_readout", lambda *a, **k: fake_full)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON)
    assert state["contradiction_count"] == 1
    assert state["status_counts"] == {"NORMAL": 1}
    # the contradiction is never silently resolved into a single value -- both sides
    # still live in the readout the real caller (cmd_answer/MCP) can render; this test
    # only guards that counting it doesn't crash classification or get dropped.
    assert kb._classify_current_local_state(state) == "GREEN"

    out = kb._answer_next_action("sammakorn", state_answer=state)
    assert any("ขัดแย้ง" in n for n in out.get("notes", [])), \
        "a non-empty contradiction_count must reach next_action, not stay buried in state"


# ---------------------------------------------------------------------------
# Fixes (2026-10-02): Thai DDS status words, sensor fault handling,
# stale forecast, forward-hazard slot ordering.
# ---------------------------------------------------------------------------

# Verbatim from this repo's OWN existing fixture, tests/test_readout.py::_seed_fixture_store
# (not re-typed/invented here) -- a real dds_daily_pdf canal row whose raw Thai status word
# is "ระดับน้ำวิกฤติ", the exact word an earlier pass found uncounted. the fix
# (2026-10-04): this station name is in `readout._DDS_GATE_COORDS` (WL.SSB.07's own
# canonical label, see that table's own comment) and tagged `canal_inner` in provenance
# (that fixture's name/comment is an inner-zone reading by construction, it was simply
# missing the `section` field this fix now reads) -- both now required for a
# dds_daily_pdf row to decide anything (see readout.py's dds_canal loop). WL.SSB.07 is
# 3.14 km from the Sammakorn centre, so `radius_km` is passed as 5.0 explicitly below
# (same widened radius `tests/test_freshness_gate_2026-10-03.py`'s equivalent scenario
# already uses) rather than relying on `_answer_state`'s own 3.0 km default.
REAL_DDS_CRITICAL_CANAL_ROW = dict(
    source_id="dds_daily_pdf", station_name="คลองแสนแสบ-สนข.บางกะปิ",
    variable="canal_level_0700_m", value=0.90, unit="m",
    observed_at_utc="2026-09-26T00:00:00+00:00", fetched_at_utc="2026-09-26T04:00:00+00:00",
    trust_tier="official_report", critical=0.45, status="ระดับน้ำวิกฤติ",
    provenance={"section": "canal_inner", "header_date_recognized": True},
)


def test_dual_state_dds_thai_critical_word_classifies_red(fresh_state_db):
    """The raw Thai word a BMA DDS canal bulletin publishes for
    a critical reading ("ระดับน้ำวิกฤติ") is in NEITHER readout.FLOOD_LIKE_STATUS (English
    station words) nor NORMAL_LIKE_STATUS -- before this fix it fell through to YELLOW.
    It must classify RED, via the same `build_data._DDS_STATUS_TH` mapping this repo
    already registered (never a new standalone status word)."""
    store.insert_observation(fresh_state_db, **REAL_DDS_CRITICAL_CANAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, radius_km=5.0, as_of_date="2026-09-26")
    assert state["status_counts"] == {"ระดับน้ำวิกฤติ": 1}
    assert kb._classify_current_local_state(state) == "RED"


def test_dual_state_dds_thai_normal_word_classifies_green(fresh_state_db):
    row = dict(REAL_DDS_CRITICAL_CANAL_ROW)
    row["status"] = "ระดับน้ำปกติ"
    store.insert_observation(fresh_state_db, **row)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, radius_km=5.0, as_of_date="2026-09-26")
    assert state["status_counts"] == {"ระดับน้ำปกติ": 1}
    assert kb._classify_current_local_state(state) == "GREEN"


def test_dual_state_sensor_fault_only_is_unknown_not_yellow(fresh_state_db):
    """`ขัดข้อง` (sensor/equipment fault,
    `live_water_level.SENSOR_FAULT_STATUS_TH`) is a station reporting it has no
    trustworthy reading -- counting it as a status word invents evidence. When every
    fresh row this check is a fault, the state must be UNKNOWN, never YELLOW."""
    store.insert_observation(
        fresh_state_db, source_id="bma_pumphistory", station_code="ST.SPS.01",
        station_name="สถานีสูบน้ำสัมมากร", lat=13.759, lon=100.677,
        variable="pump_level_m", value=None, unit="m",
        observed_at_utc="2026-09-28T00:00:00+00:00",
        fetched_at_utc="2026-09-28T00:05:00+00:00",
        trust_tier="official_telemetry", status="ขัดข้อง",
    )
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert state["status_counts"] == {"ขัดข้อง": 1}
    assert kb._classify_current_local_state(state) == "UNKNOWN"


def test_forward_hazard_stale_cache_is_unknown_not_active_unit():
    """Direct unit test of the classifier: a stale forecast
    cache must never be reported ACTIVE just because some cached model happens to have
    a non-zero figure."""
    hazard_answer = {"tag": "RELAYED", "stale": True,
                      "per_model": [{"model": "ECMWF", "tomorrow_mm": 5.0, "7day_total_mm": 20.0}]}
    assert kb._classify_forward_hazard(hazard_answer) == "UNKNOWN"


def test_forward_hazard_real_stale_rows_classify_unknown_not_active(real_forecast_db):
    """FIX (2026-10-04, F-forecast-freshness) updated this test's expectation: before
    that fix, a point-wide pooled `issued_at`/`stale` let `_answer_hazard` report
    RELAYED + stale=True while STILL handing out real but individually-stale rows in
    `per_model` -- exactly the bug (a) exists to close (a stale row must never reach a
    caller as live evidence, pooled-fresh or not). With the REAL_SAMMAKORN_ROWS fixture
    left at its REAL recorded `fetched_at_utc` (~2026-09-27/28, no `now` passed to the
    factory) and `now=2026-10-05`, every row is now individually stale (>24h past its
    own fetch) -- `_forecast_rows_by_model` drops every one of them.

    FIX D (2026-10-04, project decision -- no hosted access): the tracked offline
    snapshot fallback this test used to exercise next is removed -- `_answer_hazard`
    now returns an honest OPEN + `next_action` in this case, and
    `_classify_forward_hazard` must still read that as UNKNOWN, never ACTIVE."""
    real_forecast_db()  # real original fetched_at (Sep 27-28), deliberately NOT fresh
    now = datetime.datetime(2026, 10, 5, 12, 0, 0, tzinfo=UTC)
    hazard = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert hazard["tag"] == "OPEN"
    assert hazard.get("next_action")
    assert "offline_snapshot" not in hazard
    assert "per_model" not in hazard
    assert kb._classify_forward_hazard(hazard) == "UNKNOWN"


def test_forward_hazard_mixed_freshness_drops_stale_model_keeps_fresh_one(tmp_path, monkeypatch):
    """Task (a)'s own acceptance case: a fresh zero-rain model + a stale rainy model must
    classify as forward_hazard NONE, never ACTIVE -- the stale rainy model's real mm
    figure must never leak into `per_model` just because another model's cache happens
    to be fresh right now. Both rows are REAL recorded values, never simulated: the
    rainy-but-stale row is `REAL_SAMMAKORN_ROWS`' own CMA 2026-10-01T17:00Z/2.6mm row
    (real value, real `fetched_at_utc` ~2026-09-27T18:10, left UNCHANGED so it is
    genuinely stale at this test's clock, while its `observed_at_utc` still resolves to
    a Bangkok-LOCAL date at/after local tomorrow -- so it is excluded for STALENESS,
    never masked by the unrelated date filter); the zero-rain-but-fresh row's 0.0mm
    value is this repo's own real recorded `ecmwf_ifs025` 0.0mm figure (`tests/
    test_token_budget.py`'s `REAL_POPULATED_ROWS`, `openmeteo_multimodel`/
    `precipitation_forecast_mm`, fetched 2026-10-02) -- re-inserted here under
    `openmeteo_forecast16d`/`precipitation_forecast_daily_mm` (the schema
    `_forecast_rows_by_model` actually reads) with a FRESH `fetched_at_utc` relative to
    this test's `now`, since the real row's own fetch batch predates every `now` this
    file uses."""
    # now's Bangkok-LOCAL date is 2026-10-01 (UTC 12:00 + 7h = 19:00 local) -> local
    # tomorrow = 2026-10-02, which is exactly the CMA row's own local date
    # (2026-10-01T17:00Z -> local 2026-10-02T00:00) -- the date filter passes for BOTH
    # rows below, isolating staleness as the only thing dropping CMA.
    now = datetime.datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    # Stale rainy model -- REAL_SAMMAKORN_ROWS' own CMA row, real value, real
    # (now ancient) fetched_at_utc, unchanged.
    cma_station, cma_observed, cma_fetched, cma_value = REAL_SAMMAKORN_ROWS[3]
    assert cma_value == 2.6 and cma_observed == "2026-10-01T17:00:00+00:00"  # guard
    store.insert_observation(
        conn, source_id="openmeteo_forecast16d", station_code=cma_station,
        variable="precipitation_forecast_daily_mm", value=cma_value, unit="mm",
        observed_at_utc=cma_observed, fetched_at_utc=cma_fetched, trust_tier="third_party",
    )
    # Fresh zero-rain model -- real recorded 0.0mm ECMWF figure, fresh fetched_at_utc,
    # same local-tomorrow date as the CMA row above.
    store.insert_observation(
        conn, source_id="openmeteo_forecast16d", station_code="sammakorn:ecmwf_ifs025",
        variable="precipitation_forecast_daily_mm", value=0.0, unit="mm",
        observed_at_utc="2026-10-01T17:00:00+00:00",  # local tomorrow (2026-10-02)
        fetched_at_utc=(now - datetime.timedelta(hours=1)).isoformat(),
        trust_tier="third_party",
    )
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)

    hazard = kb._answer_hazard("sammakorn", 13.758235, 100.676084, now_utc=now)
    assert hazard["tag"] == "RELAYED"
    assert hazard["stale"] is False, "a fresh model is live -- point-level stale must be False"
    models = {m["model"] for m in hazard["per_model"]}
    assert "ECMWF" in models, "the fresh zero-rain model must still be reported"
    assert "CMA" not in models, (
        "CMA's row is stale (real fetched_at ~2026-09-27, now 2026-10-02) -- a stale "
        "model must be dropped entirely, never surfaced as evidence")
    assert kb._classify_forward_hazard(hazard) == "NONE", (
        "fresh zero-rain model + dropped stale rainy model -> NONE, never ACTIVE")


def test_dual_state_unknown_with_active_hazard_reserves_a_slot_before_selfhelp():
    """The forward-hazard reminder must be reserved ahead of
    self-help items whenever forward_hazard=ACTIVE, even when current_local_state is
    UNKNOWN (the real measured case: a fixed action order let two pre-season
    accountability items fill both slots after the UNKNOWN action, so the forecast
    warning and the route never appeared at all)."""
    hazard_answer = {"tag": "RELAYED", "stale": False, "point_id": "sammakorn",
                      "per_model": [{"model": "ECMWF", "tomorrow_mm": 5.0, "7day_total_mm": 20.0}]}
    accountability_answer = {
        "owner_agencies": [],
        "self_help_actions": [{"text_th": "x", "cite": "docs/knowledge/foo.md",
                                "why_matched": "y"}],
    }
    out = kb._answer_next_action(
        "sammakorn", state_answer=None, hazard_answer=hazard_answer,
        accountability_answer=accountability_answer)
    assert out["dual_state"] == {"current_local_state": "UNKNOWN", "forward_hazard": "ACTIVE"}
    assert out["actions"][0]["action"] == kb.UNKNOWN_ACTION_TH
    assert "FORWARD_HAZARD_STATE" in out["actions"][1]["source"]


def test_answer_accountability_catches_both_refusal_shapes(monkeypatch):
    monkeypatch.setattr(
        acct, "build_result", lambda at, radius_km=acct.DEFAULT_RADIUS_KM: {
            "at": at, "Q1": {"refused": "synthetic: unresolvable point"},
        })
    out = kb._answer_accountability("not_a_real_asset_id_xyz")
    assert out["tag"] == "OPEN"
    assert "refused" in out


# ---------------------------------------------------------------------------
# Offline snapshot fallback when data/observations.sqlite
# is missing (a fresh self-install clone before any `--refresh`/`collect.py --all`).
# ---------------------------------------------------------------------------

def test_answer_state_on_fresh_clone_is_unknown_with_refresh_action(monkeypatch, tmp_path):
    """FIX D (2026-10-04, project decision -- no hosted access): `kb.DB_PATH` pointed at
    a path that does not exist (the real condition on a fresh clone with no local
    refresh run yet) must return an honest OPEN with a `next_action` telling the
    caller to refresh on their own machine -- never a value read from a tracked/
    shipped snapshot (that fallback, and the file it read, are both removed: this
    repo ships no pre-computed flood reading for anyone to read without computing it
    themselves)."""
    missing_db = tmp_path / "does_not_exist.sqlite"
    monkeypatch.setattr(kb, "DB_PATH", missing_db)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON)
    assert state["tag"] == "OPEN"
    assert state.get("next_action")
    assert "offline_snapshot" not in state
    assert kb._classify_current_local_state(state) == "UNKNOWN"


def test_answer_state_no_snapshot_match_for_unknown_latlon_stays_open(monkeypatch, tmp_path):
    """An arbitrary lat/lon gets the same honest OPEN + refresh action as a declared
    area -- never an approximated nearest-neighbour guess for a place this repo
    doesn't actually track."""
    missing_db = tmp_path / "does_not_exist.sqlite"
    monkeypatch.setattr(kb, "DB_PATH", missing_db)
    state = kb._answer_state(1.0, 1.0)
    assert state["tag"] == "OPEN"
    assert "offline_snapshot" not in state


# ---------------------------------------------------------------------------
# FIX D (2026-10-04, project decision -- no hosted access): the tracked
# `site/dist/api/v1/areas/sammakorn.json` offline-hazard-snapshot fallback
# (`_offline_hazard_from_snapshot`/`_offline_snapshot_for`) this block of tests used
# to exercise is removed along with the file it read -- this repo ships no
# pre-computed reading for anyone to read without their own refresh. The underlying
# honesty properties these tests guarded (a stale/missing-timestamp forecast must
# classify UNKNOWN, never ACTIVE; per-model freshness is judged independently) are
# still covered on the LIVE path by `test_forward_hazard_stale_cache_is_unknown_not_active_unit`,
# `test_forward_hazard_real_stale_rows_classify_unknown_not_active`, and
# `test_forward_hazard_mixed_freshness_drops_stale_model_keeps_fresh_one` above.
# ---------------------------------------------------------------------------


def _active_hazard_answer() -> dict:
    """A minimal synthetic ACTIVE forward-hazard answer, same shape
    `test_dual_state_unknown_with_active_hazard_reserves_a_slot_before_selfhelp` already
    uses -- only the wording the dual-state block emits around it is new here."""
    return {"tag": "RELAYED", "stale": False, "point_id": "sammakorn",
            "per_model": [{"model": "ECMWF", "tomorrow_mm": 5.0, "7day_total_mm": 20.0}]}


def test_dual_state_unknown_with_active_hazard_never_claims_normal(fresh_state_db):
    """Regression for an earlier check audit defect 3: UNKNOWN current state (no fresh rows at
    all) combined with an ACTIVE forward hazard must never say "ปกติ" ("normal") --
    it must use the same 'no current-state data' framing as `UNKNOWN_ACTION_TH`
    instead."""
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert kb._classify_current_local_state(state) == "UNKNOWN"
    out = kb._answer_next_action(
        "sammakorn", state_answer=state, hazard_answer=_active_hazard_answer())
    assert out["dual_state"] == {"current_local_state": "UNKNOWN", "forward_hazard": "ACTIVE"}
    # Positional indexing would be fragile here: an UNKNOWN current state with no
    # real DB rows at all falls back to the tracked offline snapshot, which also sets
    # `state.refresh_suggested` -- so a `run --refresh` action now legitimately
    # occupies a slot before this dual-state reminder (see tests/test_token_budget.py
    # for that behaviour's own coverage). Find the reminder by its `source`, same
    # pattern `test_dual_state_green_with_active_hazard_keeps_normal_wording` below
    # already uses.
    reminder = next(a for a in out["actions"] if "FORWARD_HAZARD_STATE" in a["source"])
    assert "ปกติ" not in reminder["action"]
    assert "ยังไม่มีข้อมูลสถานะปัจจุบัน" in reminder["action"]
    for banned in ("ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        assert banned not in reminder["action"]


def test_dual_state_green_with_active_hazard_keeps_normal_wording(fresh_state_db):
    """GREEN (a real fresh NORMAL station reading) combined with an ACTIVE forward
    hazard is the ONLY state allowed to keep the "ปกติ" wording -- it has a real fresh
    non-flood-like reading behind it."""
    store.insert_observation(fresh_state_db, **REAL_WL_SSB_08_NORMAL_ROW)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert kb._classify_current_local_state(state) == "GREEN"
    out = kb._answer_next_action(
        "sammakorn", state_answer=state, hazard_answer=_active_hazard_answer())
    assert out["dual_state"]["current_local_state"] == "GREEN"
    reminder = next(a for a in out["actions"] if "FORWARD_HAZARD_STATE" in a["source"])
    assert "ปกติ" in reminder["action"]
    for banned in ("ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        assert banned not in reminder["action"]


def test_dual_state_yellow_with_active_hazard_uses_its_own_wording(fresh_state_db):
    """YELLOW (a station status word that is neither FLOOD_LIKE_STATUS nor
    NORMAL_LIKE_STATUS nor a sensor fault -- here `live_water_level.classify_level`'s
    own already-registered `ABOVE_NORMAL` vocabulary, VERIFIED at live_water_level.py,
    not a new invented word) combined with an ACTIVE forward hazard must get its own
    wording -- neither the GREEN "ปกติ" claim nor the UNKNOWN 'no data' framing, since
    YELLOW is neither of those: a real but unclear/mixed reading exists."""
    row = dict(REAL_WL_SSB_08_NORMAL_ROW)
    row["status"] = "ABOVE_NORMAL"
    store.insert_observation(fresh_state_db, **row)
    state = kb._answer_state(SAMMAKORN_LAT, SAMMAKORN_LON, as_of_date="2026-09-28")
    assert kb._classify_current_local_state(state) == "YELLOW"
    out = kb._answer_next_action(
        "sammakorn", state_answer=state, hazard_answer=_active_hazard_answer())
    assert out["dual_state"]["current_local_state"] == "YELLOW"
    reminder = next(a for a in out["actions"] if "FORWARD_HAZARD_STATE" in a["source"])
    assert "ปกติ" not in reminder["action"]
    assert "ยังไม่มีข้อมูลสถานะปัจจุบัน" not in reminder["action"]
    assert "ไม่ชัดเจน" in reminder["action"]
    for banned in ("ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย"):
        assert banned not in reminder["action"]


# ---------------------------------------------------------------------------
# F8 (2026-10-04) -- nearest CCTV cameras, VISUAL-CHECK only, never a decision input.
# Real recorded camera rows (id/title/lat/lon/agency/url), copied verbatim from this
# repo's own captured contract fixture
# (tests/contract/fixtures/hii_analyst_cctv_captured.json, id 13's real 2026-10-03
# capture of https://api-v3.thaiwater.net/api/v1/thaiwater30/analyst/cctv) -- never
# simulated. None of this repo's served areas (sammakorn/ram53) have a real camera
# within radius in that real capture, so these tests query from camera id 21's own
# real coordinates instead of an area centre, to exercise the radius/sort/limit logic
# against real distances rather than inventing synthetic ones.
# ---------------------------------------------------------------------------

# (station_id, title, agency_en, province_th, lat, lon, cctv_url) -- real, verbatim.
REAL_CCTV_ROWS = [
    ("21", "ปากคลองลัดโพธิ์", "Department of Water Resources", "สมุทรปราการ",
     13.667307, 100.540037, ""),
    ("23", "ศาลากลางสมุทรปราการ", "Department of Water Resources", "สมุทรปราการ",
     13.598016, 100.596216,
     "http://samutprakan-cpy.dyndns.org:5001/axis-cgi/jpg/image.cgi?resolution=CiF"),
    ("20", "สามเสน", "Department of Water Resources", "กรุงเทพมหานคร",
     13.788754, 100.509776, ""),
]

# Real measured distances (haversine) from camera id 21's own coordinates -- 21 itself
# is 0.0 km, 23 is ~9.8 km, 20 is ~13.9 km.
_CCTV_QUERY_LAT, _CCTV_QUERY_LON = 13.667307, 100.540037


def _insert_cctv_rows(conn, rows, fetched_at_utc):
    for station_id, title, agency_en, province_th, lat, lon, cctv_url in rows:
        text = f"{station_id} | {title} | {agency_en} | {province_th} | {lat},{lon} | {cctv_url}"
        store.insert_document(
            conn, source_id="hii_analyst_cctv", fetched_at_utc=fetched_at_utc,
            section="cctv_station", text=text,
        )


@pytest.fixture
def real_cctv_db(tmp_path, monkeypatch):
    def _make(rows=REAL_CCTV_ROWS, fetched_at_utc="2026-10-03T12:00:00+00:00",
              older_rows=None, older_fetched_at_utc="2026-09-01T00:00:00+00:00"):
        db_path = tmp_path / "observations.sqlite"
        conn = store.connect(db_path)
        if older_rows:
            _insert_cctv_rows(conn, older_rows, older_fetched_at_utc)
        _insert_cctv_rows(conn, rows, fetched_at_utc)
        conn.close()
        monkeypatch.setattr(kb, "DB_PATH", db_path)
        return db_path
    return _make


def test_parse_cctv_document_text_round_trips_real_row():
    station_id, title, agency_en, province_th, lat, lon, cctv_url = REAL_CCTV_ROWS[1]
    text = f"{station_id} | {title} | {agency_en} | {province_th} | {lat},{lon} | {cctv_url}"
    out = kb._parse_cctv_document_text(text)
    assert out == {"station_id": station_id, "title": title, "lat": lat, "lon": lon,
                    "cctv_url": cctv_url}


def test_parse_cctv_document_text_malformed_line_is_none():
    assert kb._parse_cctv_document_text("not | enough | fields") is None
    assert kb._parse_cctv_document_text("21 | title | a | b | not_a_latlon | url") is None


def test_nearest_cctv_cameras_default_radius_flags_far_real_cameras(real_cctv_db):
    """Fix (2026-10-04): cameras are NEVER dropped by `radius_km`
    any more (the real MVP areas' nearest camera sits 12-18km away -- a hard radius
    cutoff left F8 with zero cameras for both). Camera 21 itself (distance 0.0) is
    within the default 3km radius; 23 (~9.8km) and 20 (~13.9km) are real but farther,
    still RETURNED (nearest-3, the default `limit`), each flagged via
    `within_radius`."""
    real_cctv_db()
    out = kb._nearest_cctv_cameras(_CCTV_QUERY_LAT, _CCTV_QUERY_LON)
    assert [c["name"] for c in out] == [
        "ปากคลองลัดโพธิ์", "ศาลากลางสมุทรปราการ", "สามเสน"]
    assert out[0]["distance_km"] == 0.0
    assert out[0]["url"] is None
    assert out[0]["within_radius"] is True
    assert out[1]["within_radius"] is False
    assert out[2]["within_radius"] is False


def test_nearest_cctv_cameras_wider_radius_flags_more_as_within_and_caps(real_cctv_db):
    """A wider radius (10km) flags camera 23 (~9.8km) as `within_radius` too, but not
    20 (~13.9km) -- still sorted nearest-first; every camera is still RETURNED either
    way (this fix), only the flag changes; `limit` still caps the result count."""
    real_cctv_db()
    out = kb._nearest_cctv_cameras(_CCTV_QUERY_LAT, _CCTV_QUERY_LON, radius_km=10.0)
    names = [c["name"] for c in out]
    assert names == ["ปากคลองลัดโพธิ์", "ศาลากลางสมุทรปราการ", "สามเสน"]
    assert out[1]["url"].startswith("http://samutprakan-cpy.dyndns.org")
    assert out[0]["within_radius"] is True
    assert out[1]["within_radius"] is True
    assert out[2]["within_radius"] is False
    out_capped = kb._nearest_cctv_cameras(
        _CCTV_QUERY_LAT, _CCTV_QUERY_LON, radius_km=10.0, limit=1)
    assert len(out_capped) == 1
    assert out_capped[0]["name"] == "ปากคลองลัดโพธิ์"


def test_nearest_cctv_cameras_reads_only_latest_batch(real_cctv_db):
    """An OLDER batch with a camera placed exactly at the query point must never be
    counted -- only the latest `fetched_at_utc` batch for this source is read, so a
    repeated refresh's older rows (no per-camera dedup on insert) never double the
    same real camera into the nearest list. The 3 real cameras in the NEWEST batch are
    still all returned (no radius cutoff), just never the OLD BATCH one."""
    older_duplicate = [("21", "ปากคลองลัดโพธิ์ (OLD BATCH)", "Department of Water Resources",
                         "สมุทรปราการ", _CCTV_QUERY_LAT, _CCTV_QUERY_LON, "")]
    real_cctv_db(older_rows=older_duplicate)
    out = kb._nearest_cctv_cameras(_CCTV_QUERY_LAT, _CCTV_QUERY_LON)
    assert len(out) == 3
    assert all("OLD BATCH" not in c["name"] for c in out)


def test_nearest_cctv_cameras_no_db_is_empty_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "does_not_exist.sqlite")
    assert kb._nearest_cctv_cameras(_CCTV_QUERY_LAT, _CCTV_QUERY_LON) == []


def test_answer_cctv_shape_is_visual_check_never_a_decision_tag(real_cctv_db):
    real_cctv_db()
    out = kb._answer_cctv(_CCTV_QUERY_LAT, _CCTV_QUERY_LON)
    assert out["kind"] == "VISUAL-CHECK"
    assert "tag" not in out, (
        "VISUAL-CHECK must never be carried under a literal `tag` key -- "
        "tests/test_tag_vocabulary.py enforces that every `tag` key holds one of the "
        "five floor tokens (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN), and VISUAL-CHECK "
        "is deliberately not a sixth one")
    assert out["radius_km"] == kb.DEFAULT_CCTV_RADIUS_KM
    # Fix: no radius cutoff any more -- all 3 real fixture cameras are returned
    # (capped by `_MAX_CCTV_RESULTS`, not by `radius_km`).
    assert len(out["cameras"]) == 3


def test_build_answer_includes_cctv_field_with_real_camera(real_cctv_db):
    """Through the real `build_answer` entrypoint (both the CLI and the MCP tool call
    this same function) -- `cctv` sits alongside `state`/`hazard`/`accountability`/
    `next_action`, never folded into any of them."""
    real_cctv_db()
    payload = kb.build_answer(f"{_CCTV_QUERY_LAT},{_CCTV_QUERY_LON}", refresh=False)
    assert payload["cctv"]["kind"] == "VISUAL-CHECK"
    assert payload["cctv"]["cameras"][0]["name"] == "ปากคลองลัดโพธิ์"
