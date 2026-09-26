"""
Tests for parsers.py -- pure functions only, no network calls anywhere in this file.
Fixtures are trimmed real government data (public fields only): tests/fixtures/.
"""
import json
from pathlib import Path

import parsers

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_thaiwater_flood_road_skips_missing_coord():
    data = json.loads((FIXTURES / "thaiwater_flood_road_sample.json").read_text(encoding="utf-8"))
    rows = parsers.parse_thaiwater_flood_road(data)
    # fixture has 6 records, one with lat forced to None
    assert len(rows) == 5
    for r in rows:
        assert r["lat"] is not None and r["lon"] is not None
        assert r["source_url"] == parsers.THAIWATER_FLOOD_ROAD_URL


def test_parse_thaiwater_flood_road_converts_local_time_to_utc():
    data = json.loads((FIXTURES / "thaiwater_flood_road_sample.json").read_text(encoding="utf-8"))
    rows = parsers.parse_thaiwater_flood_road(data)
    r = rows[0]
    assert r["observed_at"] is not None
    assert r["observed_at"].endswith("+00:00")


def test_parse_dds_flood_report_html_still_flooded_row_is_none_not_zero():
    html = (FIXTURES / "dds_flood_report_sample.html").read_text(encoding="utf-8")
    rows = parsers.parse_dds_flood_report_html(html)
    assert len(rows) == 3
    still_flooded = next(r for r in rows if r["seq"] == "2")
    assert still_flooded["flood_end"] is None
    assert still_flooded["flood_duration_th"] is None
    normal = next(r for r in rows if r["seq"] == "1")
    assert normal["flood_height_cm"] == 15.0
    assert normal["flood_duration_th"] == "01:25"


def test_parse_dds_flood_report_html_dash_normalized_to_none():
    html = (FIXTURES / "dds_flood_report_sample.html").read_text(encoding="utf-8")
    rows = parsers.parse_dds_flood_report_html(html)
    r3 = next(r for r in rows if r["seq"] == "3")
    assert r3["flood_duration_th"] is None


def test_parse_dds_flood_report_html_no_matching_table_returns_empty():
    assert parsers.parse_dds_flood_report_html("<html><body>no tables here</body></html>") == []


def test_parse_dds_daily_pdf_text_header():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert parsed["header"]["day"] == 26
    assert parsed["header"]["year_ce"] == 2026
    assert parsed["header"]["issue_no"] == "269/69"


def test_parse_dds_daily_pdf_text_rain_stations():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert len(parsed["rain_stations"]) == 6
    top = parsed["rain_stations"][0]
    assert top["rank"] == 1
    assert top["rain_mm"] == 210.0
    ref_row = parsed["rain_stations"][-1]
    assert ref_row["rank"] is None  # the unranked reference row (เขตดินแดง)


def test_parse_dds_daily_pdf_text_canal_levels():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert len(parsed["canal_outer"]) == 3
    assert len(parsed["canal_inner"]) == 7
    row = parsed["canal_outer"][0]
    assert row["critical_m"] == 1.80
    assert row["today_0700_m"] == 1.92
    assert "วิกฤติ" in row["status_th"]


def test_parse_dds_daily_pdf_text_chaophraya_full_and_partial_rows():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert len(parsed["chaophraya_rows"]) == 6
    assert len(parsed["chaophraya_partial"]) == 1
    assert parsed["chaophraya_partial"][0]["date_th"].startswith("26")
    full = parsed["chaophraya_rows"][0]
    assert full["qmax_nakhonsawan_cms"] == 1108.0
    assert full["tide_base_level_m"] == 0.95


def test_chaophraya_row_dash_token_becomes_none_not_a_crash():
    """B8(c) regression: a real full 10-token Chao Phraya row can contain a "-" (no
    reading for that field) -- this used to hit float()'s ValueError and abort parsing of
    the WHOLE bulletin, not just that row."""
    line = "26 ก.ย. 69  1234  5678  90.1  -  0700  +1.20  0800  +1.30  1900  +1.50"
    text = "5. ปริมาณน้ำผ\n" + line + "\n"
    parsed = parsers.parse_dds_daily_pdf_text(text)  # must not raise
    row = parsed["chaophraya_rows"][0]
    assert row["qmax_samkhok_cms"] is None
    assert row["qmax_nakhonsawan_cms"] == 1234.0


def test_chaophraya_row_recognizes_any_month_not_just_september():
    """M5 regression: an earlier version hard-coded the month abbreviation 'ก.ย.'
    (September) into the date regex, so from ~1 Oct every Chao Phraya/reservoir row
    silently fell into `documents` instead of `chaophraya_rows`."""
    line = "1 ต.ค. 69  1234  5678  90.1  111  0700  +1.20  0800  +1.30  1900  +1.50"
    text = "5. ปริมาณน้ำผ\n" + line + "\n"
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert len(parsed["chaophraya_rows"]) == 1
    assert parsed["chaophraya_rows"][0]["date_th"] == "1 ต.ค. 69"


def test_unrecognized_layout_stores_header_never_silently_drops():
    """B8(b) regression: a PDF whose text matches NONE of `_SECTION_ANCHORS` used to come
    back as header=None, 0 observations, 0 documents -- indistinguishable from "nothing
    new in a normal bulletin". The full text must always be stored as a document."""
    parsed = parsers.parse_dds_daily_pdf_text("totally unrecognized layout, no anchors here")
    assert parsed["header"] is None
    sections = {d["section"] for d in parsed["documents"]}
    assert "header" in sections


def test_parse_dds_daily_pdf_text_reservoirs():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert len(parsed["reservoirs"]) == 4
    bhumibol = parsed["reservoirs"][0]
    assert bhumibol["capacity_mcm"] == 13462.0
    assert bhumibol["storage_pct"] == 62.0


def test_parse_dds_daily_pdf_text_tide_dedicated():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    assert len(parsed["tide_dedicated"]) == 2
    high = next(r for r in parsed["tide_dedicated"] if r["kind_th"] == "ขึ้นเต็มที่")
    assert high["am_level_m"] == 0.66


def test_parse_dds_daily_pdf_text_never_drops_prose_sections():
    text = (FIXTURES / "dds_daily_sample.txt").read_text(encoding="utf-8")
    parsed = parsers.parse_dds_daily_pdf_text(text)
    sections = {d["section"] for d in parsed["documents"]}
    assert "weather_forecast" in sections
    assert "narrative_log" in sections


def test_parse_dds_daily_pdf_text_empty_input_no_crash():
    parsed = parsers.parse_dds_daily_pdf_text("")
    assert parsed["header"] is None
    assert parsed["rain_stations"] == []
    assert parsed["canal_outer"] == []


def test_parse_tide_table_text_all_months_found():
    text = (FIXTURES / "dds_tide_sample.txt").read_text(encoding="utf-8")
    months = parsers.parse_tide_table_text(text)
    assert len(months) == 2
    assert months[0]["year"] == 2026
    assert months[0]["month"] == 1
    assert len(months[0]["days"]) == 31


def test_parse_tide_table_text_missing_extreme_is_none_not_zero():
    text = (FIXTURES / "dds_tide_sample.txt").read_text(encoding="utf-8")
    months = parsers.parse_tide_table_text(text)
    day1 = months[0]["days"][0]
    assert day1["hw_am_time"] is None  # printed as "-" in the source
    assert day1["hw_pm_level_m"] == 1.13


def test_parse_tide_table_text_empty_input_no_crash():
    assert parsers.parse_tide_table_text("") == []


def test_thai_short_date_to_iso():
    assert parsers.thai_short_date_to_iso("20 ก.ย. 69") == "2026-09-20"
    assert parsers.thai_short_date_to_iso("not a date") is None
