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
    html = _load_fixture_html()
    series = bsd.parse_history_series(html)
    assert len(series) == 20
    assert series[0]["timestamp_utc"] == "2026-09-25T17:20:00Z"
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
