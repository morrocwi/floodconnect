"""Tests for site/build_page.py's water-balance chart/table rendering (Toledo
PROP-FLOOD-03 section + BMA briefing 2026-09-26). No network calls."""
import datetime
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_page as bp  # noqa: E402

NOW = datetime.datetime(2026, 9, 26, 12, 0, tzinfo=datetime.timezone.utc)


def _drain_timeline():
    return {
        "generated_at_utc": "2026-09-26T13:00:00+00:00",
        "horizon_hours": 8,
        "forecast_coverage_hours": 8,
        "v0_m3": 223_000_000,
        "q_m3s": 1200,
        "area_km2": 1568.737,
        "rain_mm_hourly": [1, 2, 0, 0, 3, 0, 0, 0],
        "scenarios": {
            "c0": {"label_th": "ฝนหยุด (c=0)", "c": 0.0,
                   "values_m3": [223_000_000 - i * 4_320_000 for i in range(9)],
                   "end_hour": None, "end_time_utc": None},
            "c100": {"label_th": "ขอบบน (c=1)", "c": 1.0,
                     "values_m3": [223_000_000 + i * 1_000_000 for i in range(9)],
                     "end_hour": None, "end_time_utc": None},
            "d_jma": {"label_th": "JMA", "c": 0.5,
                      "values_m3": [223_000_000 - i * 1_000_000 for i in range(9)],
                      "end_hour": 6, "end_time_utc": "2026-09-26T19:00:00+00:00"},
        },
        "footnote_th": "footnote",
    }


def test_half_day_word_covers_all_hours():
    for h in range(24):
        assert bp._half_day_word(h) != ""


def test_fmt_end_time_th_none_says_not_drained():
    assert "ยังไม่พ้นน้ำ" in bp._fmt_end_time_th(None, NOW)


def test_fmt_end_time_th_rounds_to_half_day():
    text = bp._fmt_end_time_th("2026-09-28T14:00:00+00:00", NOW)
    assert "28" in text


def test_tide_windows_extracts_plus_minus_2h():
    area = {"tide": {"next_high": [{"time": "2026-09-26T19:25:00+07:00", "height_m": 1.2}]}}
    windows = bp._tide_windows(area)
    assert len(windows) == 1
    w0, w1 = windows[0]
    assert (w1 - w0) == datetime.timedelta(hours=4)


def test_tide_windows_empty_when_no_tide():
    assert bp._tide_windows({}) == []


def test_build_drain_timeline_svg_contains_svg_tag():
    html = bp.build_drain_timeline_svg(_drain_timeline(), NOW, [])
    assert "<svg" in html
    assert "</svg>" in html
    assert "drain-legend" in html


def test_build_drain_timeline_svg_handles_none():
    html = bp.build_drain_timeline_svg(None, NOW, [])
    assert "<svg" not in html


def test_build_daily_rain_table_html_renders_rows():
    compare = {
        "daily_open_meteo_mm": {
            "2026-09-26": {"median": 79.1, "min": 35.5, "max": 136.3},
            "2026-09-29": {"median": 4.7, "min": 0.2, "max": 8.7},
        },
        "flags": {"model_disagreement": ["today: models disagree"]},
        "sources": {"tmd": {"content": "heavy rain warning"}},
    }
    html = bp.build_daily_rain_table_html(compare)
    assert "79 (36-136)" in html or "79 (36-136)" in html.replace(".0", "")
    assert "ฝนเบา" in html  # 4.7mm row flagged light-rain
    assert "heavy rain warning" in html


def test_build_daily_rain_table_html_empty_without_compare():
    assert bp.build_daily_rain_table_html(None) == ""


def test_build_capacity_mini_table_caps_at_ten_rows():
    records = [{"key": f"k{i}", "value": i, "unit": "x", "tag": "VERIFIED"} for i in range(20)]
    html = bp.build_capacity_mini_table(records)
    assert html.count("<tr>") == 11  # header row not counted (no <tr> in thead here) + 10 body rows
    assert "อีก 10 รายการ" in html


def test_build_waterbalance_section_html_dedupes_for_ram53():
    html = bp.build_waterbalance_section_html(
        "ram53", {"status": "REFUSED", "reason_codes": ["MISSING_INPUT"],
                  "inputs_present": [], "inputs_missing": ["A"]},
        None, [], bp.AREA_LABELS["ram53"], drain_timeline=None, now_dt=NOW)
    assert "หมู่บ้านสัมมากร" in html
    assert "<svg" not in html
