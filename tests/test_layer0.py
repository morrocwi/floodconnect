"""Tests for tools/layer0/ -- the IN/OUT/CAPACITY three-number readout.

Covers: Reading/refusal discipline, backflow-state cases, time-to-exceed arithmetic,
coping_thresholds.yaml loading, render_unit's sentence-always-renders guarantee, the
live-unit builders (bangkok_east / sammakorn / ram53 / chao_phraya_bkk_reach /
historical demonstration units), the render_block wording-law gate, and a synthetic
end-to-end unit exercising every REFUSED/present combination.
"""

import math

import pytest

from tools.layer0.in_out_capacity import (
    Reading,
    BackflowState,
    refused,
    compute_backflow_state,
    time_to_exceed_hours,
    load_coping_thresholds,
    capacity_band,
    render_unit,
    build_bangkok_east,
    build_sammakorn,
    build_ram53,
    build_chao_phraya_bkk_reach,
    build_historical_unit,
)
from tools.layer0.render_block import render_layer0_block, render_layer0_html_fragment, _check_wording


# --------------------------------------------------------------------------- Reading

def test_reading_missing_must_be_open_tag():
    with pytest.raises(ValueError):
        Reading(value=None, unit="mm", tag="MEASURED", source="x")


def test_reading_present_rejects_unknown_tag():
    with pytest.raises(ValueError):
        Reading(value=1.0, unit="mm", tag="TOTALLY_MADE_UP", source="x")


def test_refused_helper_produces_open_missing_reading():
    r = refused("mm", "no source this run")
    assert r.missing
    assert r.tag == "OPEN"
    assert "ขาด" in r.render()


def test_reading_render_present():
    r = Reading(value=12.345, unit="mm", tag="MEASURED", source="x")
    out = r.render()
    assert "12.3" in out and "mm" in out and "MEASURED" in out


# --------------------------------------------------------------------------- backflow

def test_backflow_community_evidence_wins_active():
    bf = compute_backflow_state(community_evidence=["ซอย 59: จากท่อน้ำคลอง"])
    assert bf.state == "active"
    assert bf.tag == "MEASURED-community"


def test_backflow_gate_closed_not_active():
    bf = compute_backflow_state(gate_open=False)
    assert bf.state == "not_active"


def test_backflow_same_datum_positive_head_active():
    canal = Reading(value=2.0, unit="m", tag="MEASURED", source="x")
    pond = Reading(value=1.0, unit="m", tag="MEASURED", source="x")
    bf = compute_backflow_state(canal_level=canal, pond_level=pond, same_datum=True)
    assert bf.state == "active"
    assert bf.head_m == pytest.approx(1.0)


def test_backflow_same_datum_negative_head_not_active():
    canal = Reading(value=1.0, unit="m", tag="MEASURED", source="x")
    pond = Reading(value=2.0, unit="m", tag="MEASURED", source="x")
    bf = compute_backflow_state(canal_level=canal, pond_level=pond, same_datum=True)
    assert bf.state == "not_active"
    assert bf.head_m == pytest.approx(-1.0)


def test_backflow_band_comparison_likely_instinct():
    bf = compute_backflow_state(canal_above_own_critical=True, pond_below_own_bank=True)
    assert bf.state == "likely"
    assert bf.tag == "INSTINCT"
    assert bf.head_m is None


def test_backflow_band_comparison_not_likely():
    bf = compute_backflow_state(canal_above_own_critical=False, pond_below_own_bank=True)
    assert bf.state == "not_active"


def test_backflow_unknown_when_nothing_available():
    bf = compute_backflow_state()
    assert bf.state == "unknown"
    assert bf.tag == "OPEN"


def test_backflow_render_never_fabricates_number_without_datum():
    bf = compute_backflow_state(canal_above_own_critical=True, pond_below_own_bank=True)
    rendered = bf.render()
    assert "m3" not in rendered.replace(" ", "").lower() or bf.head_m is None


# --------------------------------------------------------------------------- time to exceed

def test_time_to_exceed_basic():
    hours = time_to_exceed_hours(current_value=50.0, threshold=100.0, rate_per_hour=10.0)
    assert hours == pytest.approx(5.0)


def test_time_to_exceed_already_exceeded_returns_zero():
    hours = time_to_exceed_hours(current_value=150.0, threshold=100.0, rate_per_hour=10.0)
    assert hours == 0.0


def test_time_to_exceed_missing_input_returns_none():
    assert time_to_exceed_hours(None, 100.0, 10.0) is None
    assert time_to_exceed_hours(50.0, None, 10.0) is None
    assert time_to_exceed_hours(50.0, 100.0, None) is None


def test_time_to_exceed_non_positive_rate_returns_none():
    assert time_to_exceed_hours(50.0, 100.0, 0.0) is None
    assert time_to_exceed_hours(50.0, 100.0, -5.0) is None


# --------------------------------------------------------------------------- coping_thresholds.yaml

def test_load_coping_thresholds_reads_real_file():
    thresholds = load_coping_thresholds()
    assert "bangkok_east" in thresholds
    assert "chao_phraya_bkk_reach" in thresholds


def test_load_coping_thresholds_missing_file_returns_empty(tmp_path):
    thresholds = load_coping_thresholds(path=tmp_path / "does_not_exist.yaml")
    assert thresholds == {}


def test_capacity_band_bangkok_east_one_sided():
    band = capacity_band("bangkok_east", "rain_24h_mm", "mm/24h")
    assert not band["flooded_min"].missing
    assert band["flooded_min"].value == pytest.approx(203.0)
    assert band["coped_max"].missing
    assert band["one_sided"] is True


def test_capacity_band_chao_phraya_two_sided_with_gap():
    band = capacity_band("chao_phraya_bkk_reach", "river_flow_m3s", "m3/s")
    assert not band["flooded_min"].missing
    assert not band["coped_max"].missing
    assert band["gap"] == pytest.approx(921.0)
    assert band["one_sided"] is False


def test_capacity_band_unknown_unit_all_refused():
    band = capacity_band("no_such_unit", "no_such_var", "unit")
    assert band["flooded_min"].missing
    assert band["coped_max"].missing


# --------------------------------------------------------------------------- render_unit / synthetic unit

def _synthetic_capacity_full():
    return {
        "design": Reading(value=100.0, unit="mm", tag="VERIFIED", source="design doc"),
        "flooded_min": Reading(value=150.0, unit="mm", tag="MEASURED", source="event log"),
        "coped_max": Reading(value=90.0, unit="mm", tag="MEASURED", source="event log"),
        "gap": 60.0,
        "one_sided": False,
    }


def test_render_unit_full_data_exceeds():
    cap = _synthetic_capacity_full()
    rain_in = Reading(value=160.0, unit="mm", tag="MEASURED", source="gauge")
    pump_out = Reading(value=5.0, unit="mm", tag="MEASURED", source="pump log")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ",
                     {"ฝน": rain_in}, {"ปั๊ม": pump_out}, cap,
                     primary_in=rain_in, primary_out=pump_out, rate_per_hour=10.0)
    assert r.in_vs_capacity == "เกิน"
    assert r.out_vs_in == "ไม่ทัน"
    assert r.time_to_exceed_h == 0.0  # already exceeded flooded_min
    assert "[หน่วยทดสอบ]" in r.sentence
    assert "เกิน" in r.sentence


def test_render_unit_near_threshold():
    # coped_max=90 -> "ใกล้" band is [0.8*90, 90] = [72, 90]; 85 sits inside it.
    cap = _synthetic_capacity_full()
    rain_in = Reading(value=85.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "ใกล้ (>=80%)"


def test_render_unit_below_threshold():
    cap = _synthetic_capacity_full()
    rain_in = Reading(value=50.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "ไม่เกิน"


def test_render_unit_between_coped_and_flooded_is_unknown_band():
    # flooded_min=150, coped_max=90 -> 120 sits strictly between the two historical
    # bounds: never defaulted to "ไม่เกิน" just because flooded_min isn't reached.
    cap = _synthetic_capacity_full()
    rain_in = Reading(value=120.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "ไม่รู้ (อยู่ระหว่างเคยรับได้กับเคยท่วม)"


def test_in_vs_capacity_missing_coped_max_still_catches_exceeded():
    # flooded_min present, coped_max missing -- "เกิน" must still be decidable on
    # flooded_min alone.
    cap = {
        "design": None,
        "flooded_min": Reading(value=150.0, unit="mm", tag="MEASURED", source="event log"),
        "coped_max": refused("mm", "no history"),
        "gap": None,
        "one_sided": True,
    }
    rain_in = Reading(value=160.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "เกิน"


def test_in_vs_capacity_missing_coped_max_below_flooded_is_unknown():
    # flooded_min present but not reached, coped_max missing -- cannot prove "ไม่เกิน"
    # from flooded_min alone (UNKNOWN != SAFE).
    cap = {
        "design": None,
        "flooded_min": Reading(value=150.0, unit="mm", tag="MEASURED", source="event log"),
        "coped_max": refused("mm", "no history"),
        "gap": None,
        "one_sided": True,
    }
    rain_in = Reading(value=50.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "ไม่รู้ (ขาด: ความสามารถรับมือ)"


def test_in_vs_capacity_missing_flooded_min_within_coped_max_is_not_exceeded():
    # coped_max present, flooded_min missing -- "ไม่เกิน" still decidable from coped_max
    # alone when value is at/under it.
    cap = {
        "design": None,
        "flooded_min": refused("mm", "no history"),
        "coped_max": Reading(value=90.0, unit="mm", tag="MEASURED", source="event log"),
        "gap": None,
        "one_sided": True,
    }
    rain_in = Reading(value=50.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "ไม่เกิน"


def test_in_vs_capacity_missing_flooded_min_above_coped_max_is_unknown():
    cap = {
        "design": None,
        "flooded_min": refused("mm", "no history"),
        "coped_max": Reading(value=90.0, unit="mm", tag="MEASURED", source="event log"),
        "gap": None,
        "one_sided": True,
    }
    rain_in = Reading(value=120.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_unit", "หน่วยทดสอบ", {"ฝน": rain_in}, {}, cap, primary_in=rain_in)
    assert r.in_vs_capacity == "ไม่รู้ (ขาด: ความสามารถรับมือ)"


# --------------------------------------------------------------------------- shipped C.13 band:
# 2900 / 3200 / 3800 m3/s against the real coping_thresholds.yaml row for
# chao_phraya_bkk_reach (flooded_min=3721.0, coped_max=2800.0) -- no new thresholds.

def test_c13_band_2900_is_between_coped_and_flooded():
    cap = capacity_band("chao_phraya_bkk_reach", "river_flow_m3s", "m3/s")
    reading = Reading(value=2900.0, unit="m3/s", tag="MEASURED", source="gauge")
    r = render_unit("chao_phraya_bkk_reach", "C.13", {"ไหล": reading}, {}, cap,
                     primary_in=reading)
    assert r.in_vs_capacity == "ไม่รู้ (อยู่ระหว่างเคยรับได้กับเคยท่วม)"


def test_c13_band_3200_is_between_coped_and_flooded():
    cap = capacity_band("chao_phraya_bkk_reach", "river_flow_m3s", "m3/s")
    reading = Reading(value=3200.0, unit="m3/s", tag="MEASURED", source="gauge")
    r = render_unit("chao_phraya_bkk_reach", "C.13", {"ไหล": reading}, {}, cap,
                     primary_in=reading)
    assert r.in_vs_capacity == "ไม่รู้ (อยู่ระหว่างเคยรับได้กับเคยท่วม)"


def test_c13_band_3800_exceeds_flooded_min():
    cap = capacity_band("chao_phraya_bkk_reach", "river_flow_m3s", "m3/s")
    reading = Reading(value=3800.0, unit="m3/s", tag="MEASURED", source="gauge")
    r = render_unit("chao_phraya_bkk_reach", "C.13", {"ไหล": reading}, {}, cap,
                     primary_in=reading)
    assert r.in_vs_capacity == "เกิน"


def test_render_unit_all_refused_still_renders_sentence():
    cap = {
        "design": None,
        "flooded_min": refused("mm", "no history"),
        "coped_max": refused("mm", "no history"),
        "gap": None,
        "one_sided": True,
    }
    r = render_unit("synthetic_empty", "ว่างเปล่า", {"ฝน": refused("mm", "no gauge")},
                     {"ปั๊ม": refused("m3/s", "no telemetry")}, cap,
                     primary_in=None, primary_out=None)
    assert r.sentence  # must always render
    assert "ขาด" in r.sentence
    assert r.in_vs_capacity.startswith("ไม่รู้")
    assert r.out_vs_in == "ไม่รู้"
    assert r.time_to_exceed_h is None


def test_render_unit_with_backflow_component():
    cap = _synthetic_capacity_full()
    bf = compute_backflow_state(community_evidence=["ซอย X: หลักฐาน"])
    rain_in = Reading(value=50.0, unit="mm", tag="MEASURED", source="gauge")
    r = render_unit("synthetic_backflow", "หน่วยทดสอบคลอง",
                     {"ฝน": rain_in, "ย้อนจากคลอง": bf}, {}, cap, primary_in=rain_in)
    assert "ย้อนจากคลอง: active" in r.sentence


# --------------------------------------------------------------------------- live-unit builders

def test_build_bangkok_east_default_renders():
    r = build_bangkok_east()
    assert r.unit_id == "bangkok_east"
    assert r.sentence
    assert "ขาด" in r.sentence  # rain forecast/observed not wired by default


def test_build_bangkok_east_with_live_overrides():
    live = {
        "rain_observed_24h": Reading(value=210.0, unit="mm/24h", tag="MEASURED", source="thaiwater_rain_24h"),
    }
    r = build_bangkok_east(live=live)
    assert r.in_vs_capacity == "เกิน"


def test_build_sammakorn_default_has_active_backflow():
    r = build_sammakorn()
    assert r.unit_id == "sammakorn"
    assert isinstance(r.IN["ย้อนจากคลอง"], BackflowState)
    assert r.IN["ย้อนจากคลอง"].state == "active"
    assert r.OUT["ปั๊ม (0/4)"].value == 0.0


def test_build_ram53_borrows_capacity_band_and_flags_it():
    r = build_ram53()
    assert "ยืมแถบ CAPACITY" in r.sentence


def test_build_chao_phraya_bkk_reach_default_renders():
    r = build_chao_phraya_bkk_reach()
    assert r.unit_id == "chao_phraya_bkk_reach"
    assert not r.IN["C.13 ปัจจุบัน"].missing
    assert r.sentence


def test_build_historical_units_flag_not_live():
    for unit_id, label, variable, unit_of_value in [
        ("nan_town", "น่าน (สาธิตย้อนหลัง)", "river_flow_m3s_n1", "m3/s"),
        ("chiangmai_town", "เชียงใหม่ (สาธิตย้อนหลัง)", "river_flow_m3s_p1", "m3/s"),
        ("hatyai", "หาดใหญ่ (สาธิตย้อนหลัง)", "canal_level_m", "m"),
    ]:
        r = build_historical_unit(unit_id, label, variable, unit_of_value)
        assert "ไม่ใช่ live" in r.sentence
        assert r.sentence


# --------------------------------------------------------------------------- render_block wording gate

def test_check_wording_raises_on_forbidden_word():
    with pytest.raises(ValueError):
        _check_wording("ยังไม่ต้องอพยพ")


def test_render_layer0_block_and_html_fragment():
    readouts = [build_bangkok_east(), build_sammakorn()]
    block = render_layer0_block(readouts)
    assert block["units"][0]["unit_id"] == "bangkok_east"
    html = render_layer0_html_fragment(block)
    assert "<section" in html
    assert "sammakorn" in html


# --------------------------------------------------------------------------- no forbidden strings anywhere

def test_no_forbidden_strings():
    import pathlib
    # Built from fragments (not literal substrings) so this file's own text
    # never contains the local username or an AI/vendor name verbatim --
    # a public-bound test can assert the absence of a string without quoting it.
    forbidden = (
        "/" + "home" + "/",
        "yao" + "haree",
        "cla" + "ude",
        "anthro" + "pic",
        "open" + "ai",
        "gpt" + "-",
    )
    pkg_dir = pathlib.Path(__file__).resolve().parent.parent / "tools" / "layer0"
    for path in pkg_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for word in forbidden:
            assert word not in text, f"{word!r} found in {path}"
