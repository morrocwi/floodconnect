"""Tests for site/build_data.py's Toledo PROP-FLOOD-03 wiring (build_village_water_balance,
build_bangkok_east_upper_bound). No network calls."""
import json
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402


def test_sammakorn_balance_refuses_undeclared_area():
    res = bd.build_village_water_balance("sammakorn", "2026-09-26T12:00:00+00:00",
                                          {"mm_1h": 4, "observed_at": "2026-09-26T11:30:00+00:00"})
    assert res["status"] == "REFUSED"
    assert "UNDECLARED_AREA" in res["reason_codes"]
    assert "A" in res["inputs_missing"]


def test_ram53_balance_refuses_undeclared_area():
    res = bd.build_village_water_balance("ram53", "2026-09-26T12:00:00+00:00",
                                          {"mm_1h": 2, "observed_at": "2026-09-26T11:30:00+00:00"})
    assert res["status"] == "REFUSED"
    assert "UNDECLARED_AREA" in res["reason_codes"]


def test_bangkok_east_upper_bound_available_with_declared_area_and_pump():
    out = bd.build_bangkok_east_upper_bound(
        {"mm_1h": 4, "mm_24h": 200, "observed_at": "2026-09-26T11:30:00+00:00"},
        {"available": True, "next24h_mm": 53.6},
    )
    assert out["available"] is True
    assert out["area_km2"] == 1568.737
    assert out["area_tag"] == "RELAYED"
    assert out["c_pump_m3s"] == 335
    assert len(out["c_pump_breakdown"]) == 4
    assert out["rain_now_volume_million_m3"] is not None
    assert out["outflow_capacity_per_hour_million_m3"] == round(335 * 3600 / 1_000_000, 3)
    assert out["ledger"]["status"] == "REFUSED"
    assert "c" in out["ledger"]["inputs_missing"]


def test_bangkok_east_upper_bound_ratio_matches_arithmetic():
    out = bd.build_bangkok_east_upper_bound(
        {"mm_1h": 10, "observed_at": "2026-09-26T11:30:00+00:00"}, None)
    assert out["available"] is True
    expected_vol = round((10 / 1000.0) * 1568.737 * 1_000_000 / 1_000_000, 3)
    assert out["rain_now_volume_million_m3"] == expected_vol
    expected_ratio = round(expected_vol / out["outflow_capacity_per_hour_million_m3"], 3)
    assert out["ratio_rain_now_vs_outflow_per_hour"] == expected_ratio


def test_bangkok_east_upper_bound_handles_missing_rain():
    out = bd.build_bangkok_east_upper_bound(None, None)
    assert out["available"] is True
    assert out["rain_now_volume_million_m3"] is None
    assert out["ratio_rain_now_vs_outflow_per_hour"] is None


def test_load_capacity_records_returns_list():
    records = bd.load_capacity_records()
    assert isinstance(records, list)
    assert len(records) > 0
    keys = {r["key"] for r in records}
    assert "design_capacity_mm_per_hour" in keys
    assert "citywide_total_pumping_capacity_asked_1272_33" in keys


def test_load_balance_yaml_missing_node_returns_empty_dict():
    assert bd.load_balance_yaml("no_such_node") == {}


def test_load_briefing_returns_declared_facts():
    briefing = bd.load_briefing()
    assert briefing is not None
    facts = briefing["declared_facts"]
    assert facts["backlog_volume_phra_nakhon_side"]["value"] == 223_000_000
    assert facts["total_bma_pumping_capacity"]["value"] == 1200


def test_build_briefing_summary_hero_line():
    briefing = bd.load_briefing()
    summary = bd.build_briefing_summary(briefing)
    # 2026-09-27 governor media interview supersedes the two 26 ก.ย. official_report
    # briefings (13:00, 16:15) on the hero wording -- both older files stay on disk
    # (never deleted) and remain in readout_log history.
    assert "27 ก.ย." in summary["hero_line_th"]
    assert "2 สัปดาห์" in summary["hero_line_th"]
    assert summary["trust_tier"] == "official_report-via-media"
    assert "Traffy Fondue" in summary["hotlines"]
    assert summary["timeframe"]["main_roads_days"] == "2–3"
    assert summary["timeframe"]["communities_dry_weeks"] == "2"
    assert summary["ops"]["bkk_schools_closed_28sep_count"] == 437
    assert summary["evacuation"]["affected_approx"] == 30000
    assert summary["contradiction_th"]
    assert summary["deaths_note_th"]


def test_build_briefing_summary_older_shape_still_loads():
    """The 26 ก.ย. 16:15 briefing file (superseded, kept on disk for history) must still
    parse under build_briefing_summary()'s fallback hero-line wording -- it never carried
    its own declared_facts.hero_line_th field."""
    older = json.loads(bd.BRIEFING_1615_PATH.read_text(encoding="utf-8"))
    summary = bd.build_briefing_summary(older)
    assert "16:15" in summary["hero_line_th"]
    assert summary["shelters"]["count"] == 233
    assert summary["shelters"]["in_use"] == 4200
    assert summary["tmd_forecast_note_th"]


def test_build_briefing_summary_none_when_no_briefing():
    assert bd.build_briefing_summary(None) is None


def test_build_drain_timeline_c0_matches_briefing_end_hour(monkeypatch):
    # Force the fallback (single-station) rain path so this test is independent of
    # whatever the real raw/forecast/openmeteo_<model>.json snapshots currently say.
    monkeypatch.setattr(bd, "load_multimodel_hourly", lambda: [])
    forecast = {"available": True, "hourly_full": [{"time_local": "x", "mm": 0.0}] * 60}
    dt = bd.build_drain_timeline({"mm_1h": 0}, forecast, "2026-09-26T13:00:00+00:00")
    assert dt is not None
    c0 = dt["scenarios"]["c0"]
    # V0=223e6, Q*3600=4.32e6/hr -> drains at ceil(223e6/4.32e6) = 52h with no rain
    assert c0["end_hour"] == 52
    assert c0["values_m3"][-1] == 0.0


def test_build_drain_timeline_c100_grows_with_heavy_rain(monkeypatch):
    monkeypatch.setattr(bd, "load_multimodel_hourly", lambda: [])
    forecast = {"available": True, "hourly_full": [{"time_local": "x", "mm": 50.0}] * 60}
    dt = bd.build_drain_timeline({"mm_1h": 50}, forecast, "2026-09-26T13:00:00+00:00")
    c100 = dt["scenarios"]["c100"]
    assert c100["end_hour"] is None
    assert c100["values_m3"][-1] > dt["v0_m3"]


def test_build_drain_timeline_uses_multimodel_median_when_available(monkeypatch):
    rows = [{"time_local": f"h{i}", "median_mm": 1.0, "min_mm": 0.5, "max_mm": 2.0,
             "jma_mm": 3.0, "n": 6} for i in range(100)]
    monkeypatch.setattr(bd, "load_multimodel_hourly", lambda: rows)
    dt = bd.build_drain_timeline({"mm_1h": 1}, {"available": True, "hourly_full": []},
                                  "2026-09-26T13:00:00+00:00")
    assert dt["rain_mm_hourly"][0] == 1.0
    assert dt["rain_min_hourly"][0] == 0.5
    assert dt["rain_max_hourly"][0] == 2.0
    assert dt["scenarios"]["d_jma"]["c"] == 0.5
    # forecast_coverage_hours reflects the full 96h since the multimodel rows cover it
    assert dt["forecast_coverage_hours"] == dt["horizon_hours"]
    # MUST-FIX #1 (independent review, 2026-09-27): the note must reflect the actual
    # per-hour model count seen (6 here), never a hardcoded "6" regardless of input.
    assert "6 แบบจำลองเปิด" in dt["rain_source_note_th"]


def test_build_drain_timeline_rain_source_note_reflects_partial_model_count(monkeypatch):
    """A run where only 3 of the 6 openmeteo_<model>.json files were fetched must say
    '3 แบบจำลองเปิด', not silently keep claiming 6."""
    rows = [{"time_local": f"h{i}", "median_mm": 1.0, "min_mm": 0.5, "max_mm": 2.0,
             "jma_mm": None, "n": 3} for i in range(100)]
    monkeypatch.setattr(bd, "load_multimodel_hourly", lambda: rows)
    dt = bd.build_drain_timeline({"mm_1h": 1}, {"available": True, "hourly_full": []},
                                  "2026-09-26T13:00:00+00:00")
    assert "3 แบบจำลองเปิด" in dt["rain_source_note_th"]
    assert "6" not in dt["rain_source_note_th"]


def test_build_drain_timeline_rain_source_note_fallback_path(monkeypatch):
    """The single-station fallback path (no multimodel files at all) must say so, never
    claim any model count."""
    monkeypatch.setattr(bd, "load_multimodel_hourly", lambda: [])
    forecast = {"available": True, "hourly_full": [{"time_local": "x", "mm": 0.0}] * 60}
    dt = bd.build_drain_timeline({"mm_1h": 0}, forecast, "2026-09-26T13:00:00+00:00")
    assert "แบบจำลองเปิด" not in dt["rain_source_note_th"] or "หลายตัว" in dt["rain_source_note_th"]
    assert "สถานีเดียว" in dt["rain_source_note_th"]


def test_build_drain_timeline_none_without_briefing(monkeypatch):
    monkeypatch.setattr(bd, "BRIEFING_PATH", bd.BALANCE_DIR / "no_such_briefing.json")
    assert bd.build_drain_timeline({}, {"available": True, "hourly_full": []},
                                    "2026-09-26T13:00:00+00:00") is None


def test_bangkok_east_upper_bound_includes_briefing_arithmetic():
    out = bd.build_bangkok_east_upper_bound(
        {"mm_1h": 4, "observed_at": "2026-09-26T11:30:00+00:00"},
        {"available": True, "next24h_mm": 53.6},
    )
    ba = out["briefing_arithmetic"]
    assert ba is not None
    assert ba["backlog_volume_m3"] == 223_000_000
    assert ba["pumping_capacity_m3s"] == 1200
    assert ba["hours_if_no_new_rain"] == 51.6
    assert ba["hours_range_with_forecast_rain"][0] == 51.6
    assert ba["hours_range_with_forecast_rain"][1] > 51.6
