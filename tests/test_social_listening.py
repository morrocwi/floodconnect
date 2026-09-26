"""Tests for social_listening.py -- pure parsers (no network), store write-through,
--evaluate metrics, and readout.py's new "เสียงจากอินเทอร์เน็ต (social listening)" section.
"""
import datetime
from pathlib import Path

import pytest

import readout
import social_listening as sl
import store

FIXTURES = Path(__file__).parent / "fixtures"


# --- parse_paste --------------------------------------------------------------------------

def test_parse_paste_returns_six_rows_and_drops_the_author_line():
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    assert len(rows) == 6
    for r in rows:
        assert "ทดสอบ" not in (r.get("place_text") or "") + (r.get("soi") or "")
        assert "author" not in r  # no author/poster field exists at all


def test_parse_paste_never_stores_the_author_name_anywhere():
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    import json
    dumped = json.dumps(rows, ensure_ascii=False)
    assert "ทดสอบ" not in dumped


def test_parse_paste_resolves_ti_marker_to_a_clock_time():
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    row = next(r for r in rows if r["soi"] and "50" in r["soi"])
    assert row["posted_at"].startswith("2026-09-26T04:00:00")
    assert row["state"] == "house"


def test_parse_paste_resolves_relative_hours_and_minutes():
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    garage_row = next(r for r in rows if r["state"] == "garage")
    assert garage_row["posted_at"].startswith("2026-09-26T10:00:00")  # 12:00 - 2h
    pond_row = next(r for r in rows if "ทะเลสาบ" in r["place_text"])
    assert pond_row["posted_at"].startswith("2026-09-26T11:15:00")  # 12:00 - 45min
    assert pond_row["state"] == "house"  # "ล้นเข้าบ้าน" -> water reached the house


def test_parse_paste_resolves_absolute_clock_time_and_depth():
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    row = next(r for r in rows if r["soi"] and "48/3" in r["soi"])
    assert row["posted_at"].startswith("2026-09-26T07:00:00")
    assert row["depth_cm"] == 30.0
    assert row["state"] == "house"


def test_parse_paste_classifies_road_and_rising_states():
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    road_row = next(r for r in rows if "40" in (r["soi"] or ""))
    assert road_row["state"] == "road"
    rising_row = next(r for r in rows if "110" in (r["soi"] or ""))
    assert rising_row["state"] == "rising"  # "ยังไม่ลด"


# --- parse_google_snapshot ------------------------------------------------------------------

def test_parse_google_snapshot_returns_five_rows():
    text = (FIXTURES / "social_listening_google_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_google_snapshot(text, "2026-09-26T13:00:00+07:00")
    assert len(rows) == 5


def test_parse_google_snapshot_relative_hours_and_media_publisher():
    text = (FIXTURES / "social_listening_google_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_google_snapshot(text, "2026-09-26T13:00:00+07:00")
    row = rows[0]
    assert row["publisher_type"] == "media"  # อีจัน
    assert row["posted_at"].startswith("2026-09-26T10:00:00")  # 13:00 - 3h
    assert row["depth_cm"] == 40.0
    assert row["state"] == "road"


def test_parse_google_snapshot_crosses_midnight_backwards():
    text = (FIXTURES / "social_listening_google_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_google_snapshot(text, "2026-09-26T13:00:00+07:00")
    # the row parsed from "19 ชม.ก่อน" should land on the previous day
    row19 = rows[1]
    assert row19["posted_at"].startswith("2026-09-25T18:00:00")
    assert row19["state"] == "canal_overbank"


def test_parse_google_snapshot_absolute_time_reads_as_previous_night():
    text = (FIXTURES / "social_listening_google_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_google_snapshot(text, "2026-09-26T13:00:00+07:00")
    row = rows[3]  # "22.10 น."
    assert row["posted_at"].startswith("2026-09-25T22:10:00")


def test_parse_google_snapshot_area_guess_prefers_sammakorn():
    text = (FIXTURES / "social_listening_google_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_google_snapshot(text, "2026-09-26T13:00:00+07:00")
    js100_row = rows[4]
    assert js100_row["area"] == "sammakorn"
    assert js100_row["publisher_type"] == "media"
    ram_row = rows[0]
    assert ram_row["area"] == "ram53"


# --- write_rows + evaluate_metrics -----------------------------------------------------------

@pytest.fixture()
def conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


def test_write_rows_inserts_and_dedupes(conn):
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    n1 = sl.write_rows(conn, rows, "social_listening_paste")
    assert n1 == 6
    n2 = sl.write_rows(conn, rows, "social_listening_paste")  # re-import, same rows
    assert n2 == 0
    stored = store.query_observations(conn, source_id="social_listening_paste", limit=100)
    assert len(stored) == 6
    assert all(r["variable"] == "community_report" for r in stored)


def test_write_rows_tags_media_rows_as_official_shared_inference(conn):
    text = (FIXTURES / "social_listening_google_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_google_snapshot(text, "2026-09-26T13:00:00+07:00")
    sl.write_rows(conn, rows, "social_listening_google")
    stored = store.query_observations(conn, source_id="social_listening_google", limit=100)
    media_rows = [r for r in stored if r["trust_tier"] == "official_shared_inference"]
    individual_rows = [r for r in stored if r["trust_tier"] == "community_report"]
    assert len(media_rows) == 3  # อีจัน, Rodee, JS100
    assert len(individual_rows) == 2


def test_evaluate_metrics_writes_method_evaluation_table(conn):
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    sl.write_rows(conn, rows, "social_listening_paste")
    metrics = sl.evaluate_metrics(conn, "sammakorn", "2026-09-26")
    assert metrics["rows_total"] == 6
    assert 0.0 <= metrics["share_with_soi_point"] <= 1.0
    stored = store.query_method_evaluation(conn, area="sammakorn", date="2026-09-26")
    assert {r["metric"] for r in stored} >= {"rows_total", "share_with_soi_point"}


def test_evaluate_metrics_upserts_not_duplicates(conn):
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    sl.write_rows(conn, rows, "social_listening_paste")
    sl.evaluate_metrics(conn, "sammakorn", "2026-09-26")
    sl.evaluate_metrics(conn, "sammakorn", "2026-09-26")
    stored = store.query_method_evaluation(conn, area="sammakorn", date="2026-09-26")
    metrics_names = [r["metric"] for r in stored]
    assert len(metrics_names) == len(set(metrics_names))  # no duplicate metric rows


# --- readout.py's social-listening section ---------------------------------------------------

def test_readout_renders_social_listening_section(conn):
    text = (FIXTURES / "social_listening_paste_sample.txt").read_text(encoding="utf-8")
    rows = sl.parse_paste(text, "2026-09-26T12:00:00+07:00")
    sl.write_rows(conn, rows, "social_listening_paste")
    result = readout.build_readout(conn, 13.758235, 100.676084, 5.0, as_of_date="2026-09-26")
    assert "sammakorn" in result["social_listening"]
    sec = result["social_listening"]["sammakorn"]
    assert sec["hourly_counts"]
    assert len(sec["latest5"]) <= 5
    md = readout.render_markdown(result)
    assert "เสียงจากอินเทอร์เน็ต" in md
