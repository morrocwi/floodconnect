"""
Tests for the Open-Meteo rain-forecast addition (2026-09-26):
  - parsers.parse_openmeteo_forecast on a fixture (<=12 hourly rows)
  - site/build_data.py's pure trend-word / dry-window / capacity-comparison arithmetic

No network calls anywhere in this file.
"""
import json
import sys
from pathlib import Path

import parsers

FIXTURES = Path(__file__).parent / "fixtures"

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "site"))
import build_data as bd  # noqa: E402


def _fixture_rows():
    data = json.loads((FIXTURES / "openmeteo_forecast_sample.json").read_text(encoding="utf-8"))
    return parsers.parse_openmeteo_forecast(data)


# --- parser -------------------------------------------------------------------------------

def test_parse_openmeteo_forecast_skips_missing_precipitation():
    rows = _fixture_rows()
    # fixture has 12 time entries, one with precipitation=null -> skipped
    assert len(rows) == 11
    for r in rows:
        assert r["mm"] is not None
        assert r["time_local"] is not None


def test_parse_openmeteo_forecast_keeps_ascending_order_and_probability():
    rows = _fixture_rows()
    times = [r["time_local"] for r in rows]
    assert times == sorted(times)
    assert rows[0]["prob"] == 10
    assert rows[3]["mm"] == 3.0


def test_openmeteo_forecast_url_has_hourly_precip_and_no_key():
    url = parsers.openmeteo_forecast_url(13.76, 100.62)
    assert "latitude=13.76" in url
    assert "longitude=100.62" in url
    assert "precipitation" in url
    assert "apikey" not in url.lower() and "api_key" not in url.lower()


# --- trend word (compares next-3h sum vs following-3h sum) --------------------------------

def test_trend_word_rising_when_second_window_much_wetter():
    rows = [{"time_local": f"2026-09-26T{15+i:02d}:00", "mm": mm}
            for i, mm in enumerate([0.0, 0.0, 0.0, 5.0, 5.0, 5.0])]
    direction, word = bd._trend_word(rows)
    assert direction == "rising"
    assert "เพิ่มขึ้น" in word


def test_trend_word_falling_when_second_window_much_drier():
    rows = [{"time_local": f"2026-09-26T{15+i:02d}:00", "mm": mm}
            for i, mm in enumerate([5.0, 5.0, 5.0, 0.0, 0.0, 0.0])]
    direction, word = bd._trend_word(rows)
    assert direction == "falling"
    assert "เบาลง" in word
    assert "18:00" in word  # rows[3]'s hour


def test_trend_word_steady_within_the_half_mm_step_boundary():
    # first3=3.0, next3=3.4 -> diff 0.4mm, under TREND_STEP_MM (0.5) -> steady, not rising
    rows = [{"time_local": f"2026-09-26T{15+i:02d}:00", "mm": mm}
            for i, mm in enumerate([1.0, 1.0, 1.0, 1.1, 1.1, 1.2])]
    direction, word = bd._trend_word(rows)
    assert direction == "steady"
    assert word == "ฝนยังตกต่อ"


def test_trend_word_boundary_is_exclusive_at_exactly_the_step():
    # first3=0, next3=1.5 -> diff exactly TREND_STEP_MM (0.5*3=1.5>0.5... use explicit numbers)
    rows = [{"time_local": f"2026-09-26T{15+i:02d}:00", "mm": mm}
            for i, mm in enumerate([0.0, 0.0, 0.0, 0.5, 0.0, 0.0])]
    # first3=0.0, next3=0.5 -> diff exactly 0.5 == TREND_STEP_MM -> NOT > threshold -> steady
    direction, _ = bd._trend_word(rows)
    assert direction == "steady"


# --- first_dry_6h_start ---------------------------------------------------------------------

def test_first_dry_6h_start_finds_first_six_consecutive_dry_hours():
    rows = [{"time_local": f"2026-09-26T{15+i:02d}:00", "mm": mm}
            for i, mm in enumerate([5.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    start = bd._first_dry_6h_start(rows)
    assert start == "17:00"  # first index (2) of the 6-hour dry run


def test_first_dry_6h_start_none_when_never_six_in_a_row():
    rows = [{"time_local": f"2026-09-26T{15+i:02d}:00", "mm": mm}
            for i, mm in enumerate([0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0])]
    assert bd._first_dry_6h_start(rows) is None


# --- build_forecast_short (integration of the pieces above) --------------------------------

def test_build_forecast_short_unavailable_on_empty_rows():
    out = bd.build_forecast_short([], None)
    assert out["available"] is False
    assert out["status"]


def test_build_forecast_short_sums_windows_from_fixture():
    rows = _fixture_rows()
    out = bd.build_forecast_short(rows, "2026-09-26T08:00:00+00:00")
    assert out["available"] is True
    assert out["next6h_mm"] == round(sum(r["mm"] for r in rows[:6]), 1)
    assert out["next24h_mm"] == round(sum(r["mm"] for r in rows[:24]), 1)
    assert len(out["hourly"]) <= 12


# --- capacity comparison arithmetic (sum + ratio only, never a model) -----------------------

def test_capacity_comparison_today_only():
    rain = {"mm_24h": 174.0}
    out = bd.build_capacity_comparison(rain, None)
    assert out["today_mm"] == 174.0
    assert out["today_ratio"] == round(174.0 / 80.0, 1)
    assert out["total_with_forecast_mm"] == round(174.0, 1)


def test_capacity_comparison_today_plus_forecast():
    rain = {"mm_24h": 100.0}
    forecast = {"available": True, "next24h_mm": 60.0}
    out = bd.build_capacity_comparison(rain, forecast)
    assert out["forecast_24h_mm"] == 60.0
    assert out["total_with_forecast_mm"] == 160.0
    assert out["total_with_forecast_ratio"] == 2.0


def test_capacity_comparison_no_data_is_all_none():
    out = bd.build_capacity_comparison(None, None)
    assert out["today_mm"] is None
    assert out["total_with_forecast_mm"] is None
    assert out["total_with_forecast_ratio"] is None
