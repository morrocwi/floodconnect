"""Tests for tools/harvest/bma_station_detail_draft.py's pure parser and collect.py's
collect_bma_station_detail() (source id `bma_station_detail`, registered 2026-09-27 per
docs/knowledge/BMA_STATION_DETAIL_PROBE.md's probe + proposed collector spec). Uses a
small trimmed-real fixture (tests/fixtures/bma_station_detail/stationdetail_id51_trimmed.html
-- txt_* admin-form fields + the first 20 inline history points, pulled from the archived
probe response raw/live/bma_station_detail/stationdetail_id51.html), never the network.
"""
import json

import pytest

import store
import tools.harvest.bma_station_detail_draft as bsd

FIXTURE_HTML = (
    "tests/fixtures/bma_station_detail/stationdetail_id51_trimmed.html"
)


def _load_fixture_html():
    with open(FIXTURE_HTML, encoding="utf-8") as fh:
        return fh.read()


def test_parse_station_detail_fields_reads_real_control_level():
    html = _load_fixture_html()
    fields = bsd.parse_station_detail_fields(html)
    assert fields["txt_water_code"] == "WL.SSB.12"
    assert fields["txt_water_control"] == "0.70"
    assert fields["txt_warning"] == "1.00"
    assert fields["txt_critical"] == "1.10"
    assert fields["txt_left_bank"] == "1.75"
    assert fields["txt_right_bank"] == "1.75"
    assert fields["txt_bed_bank"] == "-1.24"
    # BMA's own "not applicable" placeholder ("-") must be None, never fabricated as 0
    assert fields["txt_warning_out02"] is None
    assert fields["txt_critical_out02"] is None


def test_water_control_value_readout():
    html = _load_fixture_html()
    readout = bsd.water_control_value(html)
    assert readout == {"water_control": 0.70, "tag": "MEASURED"}


def test_parse_history_series_returns_points_in_order():
    """FIX (M8, 2026-10-05, blocking finding #2): the raw Date.UTC(...) literal is
    Bangkok LOCAL time (confirmed real BMA bug: it is labelled .UTC but is not UTC) --
    17:20 local -> 10:20Z, not the old (wrong) 17:20Z pin."""
    html = _load_fixture_html()
    series = bsd.parse_history_series(html)
    assert len(series) == 20
    assert series[0]["timestamp_utc"] == "2026-09-25T10:20:00Z"
    assert series[0]["value"] == 0.82
    assert series[1]["value"] == 0.83


def _watermap_snapshot(tmp_path, water_id=51, water_code="WL.SSB.12", water_name="test"):
    d = tmp_path / "raw" / "live" / "bma_watermap"
    d.mkdir(parents=True)
    (d / "2026-09-27T100000Z.json").write_text(
        json.dumps([{"water_id": water_id, "water_code": water_code, "water_name": water_name}]),
        encoding="utf-8",
    )
    return d


def test_water_id_list_sourced_from_latest_watermap_snapshot(tmp_path, monkeypatch):
    import collect

    _watermap_snapshot(tmp_path)
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    ids = collect._bma_station_detail_water_ids()
    assert ids == [(51, "WL.SSB.12", "test")]


def test_water_id_list_empty_when_no_watermap_snapshot_yet(tmp_path, monkeypatch):
    import collect

    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    assert collect._bma_station_detail_water_ids() == []


def test_cursor_round_trip(tmp_path, monkeypatch):
    import collect

    cursor_path = tmp_path / "bma_station_detail_cursor.json"
    monkeypatch.setattr(collect, "BMA_STATION_DETAIL_CURSOR_PATH", cursor_path)
    assert collect._bma_station_detail_load_cursor() == 0
    collect._bma_station_detail_save_cursor(7)
    assert collect._bma_station_detail_load_cursor() == 7


def test_collect_bma_station_detail_with_no_watermap_snapshot_refuses_not_fabricates(tmp_path, monkeypatch):
    import collect

    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "test.sqlite")
    res = collect.collect_bma_station_detail(conn, dry_run=False)
    assert res.ok is False
    assert "bma_watermap" in res.note


def test_collect_bma_station_detail_inserts_thresholds_and_history_and_advances_cursor(tmp_path, monkeypatch):
    import collect

    _watermap_snapshot(tmp_path)
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    monkeypatch.setattr(collect, "BMA_STATION_DETAIL_CURSOR_PATH", tmp_path / "cursor.json")
    html_bytes = _load_fixture_html().encode("utf-8")
    monkeypatch.setattr(collect, "_one_get", lambda url, headers, timeout=30: (200, html_bytes))
    monkeypatch.setattr(collect, "_cache_raw", lambda sid, payload, suffix: tmp_path / "cache.html")

    conn = store.connect(tmp_path / "test.sqlite")
    res = collect.collect_bma_station_detail(conn, dry_run=False)
    assert res.ok is True
    assert res.counts["stations_ok"] == 1
    assert res.counts["thresholds"] == 8  # 8 populated txt_* fields in the fixture
    assert res.counts["history_points"] == 20

    control_rows = conn.execute(
        "SELECT value FROM observations WHERE source_id='bma_station_detail' "
        "AND station_code='WL.SSB.12' AND variable='water_control_m'"
    ).fetchall()
    assert len(control_rows) == 1
    assert control_rows[0]["value"] == 0.70

    history_rows = conn.execute(
        "SELECT value FROM observations WHERE source_id='bma_station_detail' "
        "AND station_code='WL.SSB.12' AND variable='station_level_history_m'"
    ).fetchall()
    assert len(history_rows) == 20

    # cursor must advance past the one known water_id (wraps back to 0 with a 1-id list)
    assert collect._bma_station_detail_load_cursor() == 0


def test_collect_bma_station_detail_stops_batch_on_403(tmp_path, monkeypatch):
    import urllib.error

    import collect

    d = tmp_path / "raw" / "live" / "bma_watermap"
    d.mkdir(parents=True)
    (d / "snap.json").write_text(
        json.dumps([
            {"water_id": 1, "water_code": "A", "water_name": "a"},
            {"water_id": 2, "water_code": "B", "water_name": "b"},
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    monkeypatch.setattr(collect, "BMA_STATION_DETAIL_CURSOR_PATH", tmp_path / "cursor.json")

    def _fake_get(url, headers, timeout=30):
        raise urllib.error.HTTPError(url, 403, "forbidden", None, None)

    monkeypatch.setattr(collect, "_one_get", _fake_get)
    conn = store.connect(tmp_path / "test.sqlite")
    res = collect.collect_bma_station_detail(conn, dry_run=False)
    assert res.ok is False
    assert res.http == 403


# ---------------------------------------------------------------------------
# parsers.parse_bma_station_series (M8, 2026-10-05) -- real fixtures only.
# id51/WL.SSB.12 (one clean run, 20 points, strictly increasing).
# id284/WL.SMK.01 (a real, maker-trimmed 6-point slice spanning two Date.UTC
# days with a gap in between -- NOT two overlapping runs, so still one run;
# see the sidecar .sidecar.json next to the fixture for provenance).
# ---------------------------------------------------------------------------
import parsers

SMK01_FIXTURE_HTML = (
    "tests/fixtures/bma_station_detail/stationdetail_id284_20261005_trimmed.html"
)


def _load_smk01_html():
    with open(SMK01_FIXTURE_HTML, encoding="utf-8") as fh:
        return fh.read()


def test_parse_bma_station_series_fixes_the_7h_utc_label_bug():
    html = _load_fixture_html()
    result = parsers.parse_bma_station_series(html)
    assert result["status"] == "OK"
    assert result["chosen_run"] == 0
    assert len(result["runs"]) == 1
    assert len(result["points"]) == 20
    # 17:20 Bangkok local -> 10:20Z (7h behind), NOT the page's own (wrong) .UTC label.
    assert result["points"][0]["t_utc"] == "2026-09-25T10:20:00Z"
    assert result["points"][0]["v"] == 0.82
    assert result["step_s"] == 300  # 5-minute step


def test_parse_bma_station_series_smk01_real_fixture_one_run():
    html = _load_smk01_html()
    result = parsers.parse_bma_station_series(html)
    assert result["status"] == "OK"
    assert len(result["points"]) == 6
    # 2026-10-03 11:30 local -> 2026-10-03 04:30Z; 2026-10-05 11:20 local -> 04:20Z.
    assert result["points"][0]["t_utc"] == "2026-10-03T04:30:00Z"
    assert result["points"][0]["v"] == -0.13
    assert result["points"][-1]["t_utc"] == "2026-10-05T04:20:00Z"
    assert result["points"][-1]["v"] == -0.45


def test_parse_bma_station_series_empty_when_no_date_utc_found():
    """A real empty-series page (this repo has seen WL.SSB.13/id312 return no inline
    series at all) must be the distinct EMPTY status, never fabricated as a trend."""
    html = "<!doctype html><html><body>no script here</body></html>"
    result = parsers.parse_bma_station_series(html)
    assert result == {"points": [], "step_s": None, "runs": [], "chosen_run": None,
                       "status": "EMPTY"}


def test_parse_bma_station_series_ambiguous_without_disambiguators():
    """Two runs, no wl_in_now/observed_at_now given -> AMBIGUOUS, never guesses the
    'last run is the real one'."""
    html = (
        "<script>var data=[Date.UTC(2026, 9, 5, 10, 0, 0),1.0,"
        "Date.UTC(2026, 9, 5, 10, 5, 0),1.1,"
        "Date.UTC(2026, 9, 5, 9, 0, 0),2.0,"
        "Date.UTC(2026, 9, 5, 9, 5, 0),2.1];</script>"
    )
    result = parsers.parse_bma_station_series(html)
    assert len(result["runs"]) == 2
    assert result["status"] == "AMBIGUOUS"
    assert result["chosen_run"] is None


def test_parse_bma_station_series_splits_two_runs_and_disambiguates_by_wl_in_now():
    html = (
        "<script>var data=[Date.UTC(2026, 9, 5, 10, 0, 0),1.0,"
        "Date.UTC(2026, 9, 5, 10, 5, 0),1.1,"
        "Date.UTC(2026, 9, 5, 9, 0, 0),2.0,"
        "Date.UTC(2026, 9, 5, 9, 5, 0),2.1];</script>"
    )
    result = parsers.parse_bma_station_series(
        html, wl_in_now=1.1, observed_at_now="2026-10-05T03:05:00Z")
    assert result["status"] == "OK"
    assert result["chosen_run"] == 0
    assert result["runs"][0][-1]["v"] == 1.1


def test_parse_bma_station_series_sparse_single_point_run():
    html = "<script>var data=[Date.UTC(2026, 9, 5, 10, 0, 0),1.0];</script>"
    result = parsers.parse_bma_station_series(html)
    assert result["status"] == "SPARSE_SERIES"
    assert result["step_s"] is None


# ---------------------------------------------------------------------------
# collect.fetch_bma_station_series / collect_bma_station_series (M8, 2026-10-05) --
# single-station, on-demand, never a batch. Uses the same real trimmed WL.SMK.01
# fixture as the parser tests above, via a monkeypatched _one_get (no network).
# ---------------------------------------------------------------------------

def test_collect_bma_station_series_refuses_without_water_id():
    import collect

    conn = store.connect(":memory:")
    res = collect.collect_bma_station_series(conn, dry_run=False, water_id=None)
    assert res.ok is False
    assert "water_id" in res.note


def test_collect_bma_station_series_dry_run_makes_no_network_call(monkeypatch):
    import collect

    def _boom(*a, **k):
        raise AssertionError("network call attempted during dry-run")
    monkeypatch.setattr(collect, "_one_get", _boom)
    conn = store.connect(":memory:")
    res = collect.collect_bma_station_series(conn, dry_run=True, water_id=284)
    assert res.ok is True


def test_fetch_bma_station_series_real_fixture_stores_history(tmp_path, monkeypatch):
    import collect

    html_bytes = _load_smk01_html().encode("utf-8")
    monkeypatch.setattr(collect, "_one_get", lambda url, headers, timeout=30: (200, html_bytes))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    monkeypatch.setattr(collect, "_BMA_STATION_SERIES_MEMO", {})

    conn = store.connect(tmp_path / "test.sqlite")
    res = collect.collect_bma_station_series(conn, dry_run=False, water_id=284)
    assert res.ok is True
    assert res.counts["history_points"] == 6

    rows = conn.execute(
        "SELECT value, observed_at_utc FROM observations WHERE source_id='bma_station_series' "
        "AND variable='station_level_history_m' ORDER BY observed_at_utc"
    ).fetchall()
    assert len(rows) == 6
    assert rows[0]["observed_at_utc"] == "2026-10-03T04:30:00Z"
    assert rows[0]["value"] == -0.13
    assert rows[-1]["observed_at_utc"] == "2026-10-05T04:20:00Z"
    assert rows[-1]["value"] == -0.45


def test_fetch_bma_station_series_memoises_within_one_step(tmp_path, monkeypatch):
    import collect

    html_bytes = _load_smk01_html().encode("utf-8")
    calls = []

    def _counting_get(url, headers, timeout=30):
        calls.append(url)
        return 200, html_bytes

    monkeypatch.setattr(collect, "_one_get", _counting_get)
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    monkeypatch.setattr(collect, "_BMA_STATION_SERIES_MEMO", {})

    t0 = "2026-10-05T04:20:00+00:00"
    t1 = "2026-10-05T04:21:00+00:00"  # 60s later, within the 300s step -- memo hit
    collect.fetch_bma_station_series(284, _now=t0)
    collect.fetch_bma_station_series(284, _now=t1)
    assert len(calls) == 1


def test_fetch_bma_station_series_403_is_fetch_failed_not_fabricated(tmp_path, monkeypatch):
    import urllib.error

    import collect

    def _fake_get(url, headers, timeout=30):
        raise urllib.error.HTTPError(url, 403, "forbidden", None, None)

    monkeypatch.setattr(collect, "_one_get", _fake_get)
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    monkeypatch.setattr(collect, "_BMA_STATION_SERIES_MEMO", {})

    conn = store.connect(tmp_path / "test.sqlite")
    res = collect.collect_bma_station_series(conn, dry_run=False, water_id=312)
    assert res.ok is False
    assert res.http == 403
