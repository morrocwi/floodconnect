"""Fixes 2026-09-26 -- tests for site/build_page.py's pump tile and stale
banner logic. No network calls; build_page.py is self-contained (stdlib only)."""
import datetime
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_page as bp  # noqa: E402

TEMPLATE_PATH = Path(__file__).parent.parent / "site" / "index.template.html"

NOW = datetime.datetime(2026, 9, 26, 12, 0, tzinfo=datetime.timezone.utc)


def _pump(status_key, observed_at="2026-09-26T11:00:00+00:00"):
    return {"observed_at": observed_at, "status_th": status_key}


def test_pump_tile_separates_fail_from_idle():
    # Fixed 2026-09-26, refined 2026-09-27 (project decision: "2/4"-style numbers
    # were misread as "pumps running"). 4 STATIONS total, 3 fail, 1 idle, summing
    # to 11 physical pump MACHINES (0 running) across them -- tile's big value
    # names the machines, the fault count moves to a separate "สถานีขัดข้อง" line,
    # and idle must never be merged into the fault count.
    pumps = [
        {"observed_at": "2026-09-26T11:00:00+00:00", "pumps_on": 0, "pumps_total": 3},
        {"observed_at": "2026-09-26T11:00:00+00:00", "pumps_on": 0, "pumps_total": 3},
        {"observed_at": "2026-09-26T11:00:00+00:00", "pumps_on": 0, "pumps_total": 3},
        {"observed_at": "2026-09-26T11:00:00+00:00", "pumps_on": 0, "pumps_total": 2},
    ]
    area = {"pumps": pumps}
    pc = {"fail": 3, "idle": 1, "missing": 0, "ok": 0, "total": 4}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง")
    assert "ปั๊มน้ำเดิน 0 จาก 11 เครื่อง" in html
    assert "สถานีขัดข้อง 3 จาก 4" in html
    assert "4/4" not in html
    # Wording drift 2026-09-26 (founder-mandated): shipped text names the reporting
    # agency AND that the cause is unreported, not just "(กทม. รายงาน)" -- test updated
    # to match; the fail-vs-idle assertions below are unchanged.
    assert "ขัดข้อง 3 จาก 4 (กทม. รายงาน สาเหตุไม่ทราบ)" in html
    assert "ไม่ได้เดิน 1" in html


def test_pump_tile_no_idle_line_when_idle_zero():
    pumps = [{"observed_at": "2026-09-26T11:00:00+00:00", "pumps_on": 0, "pumps_total": 5}]
    area = {"pumps": pumps}
    pc = {"fail": 1, "idle": 0, "missing": 0, "ok": 0, "total": 1}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง")
    assert "ปั๊มน้ำเดิน 0 จาก 5 เครื่อง" in html
    assert "สถานีขัดข้อง 1 จาก 1" in html
    assert "ไม่ได้เดิน" not in html


def test_pump_tile_omits_parenthesis_when_no_stations_faulted():
    # project decision 2026-09-27: 0 faulted stations -> label drops the
    # "(กทม. รายงาน สาเหตุไม่ทราบ)" cause-attribution parenthesis entirely.
    pumps = [{"observed_at": "2026-09-26T11:00:00+00:00", "pumps_on": 6, "pumps_total": 6}]
    area = {"pumps": pumps}
    pc = {"fail": 0, "idle": 0, "missing": 0, "ok": 1, "total": 1}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง")
    assert "ปั๊มน้ำเดิน 6 จาก 6 เครื่อง" in html
    assert "สถานีขัดข้อง 0 จาก 1" in html
    assert "กทม. รายงาน" not in html


def test_stale_banner_ignores_null_observed_at_reference_rows():
    # MEDIUM-5: a station with NO observed_at at all (e.g. BKK013/BKK015-style reference
    # rows) must never pin the banner on by itself when everything live is fresh.
    area = {
        "pumps": [],
        "stations_near": [
            {"observed_at": None, "role": "north"},          # reference row, no timestamp
            {"observed_at": "2026-09-26T11:30:00+00:00", "role": "north"},  # 30 min old
        ],
        "staleness": {"newest_official_obs": "2026-09-26T11:30:00+00:00",
                      "hours_since": 0.5, "banner": False},
        "rain": None,
    }
    fragments = bp.build_area_fragments("sammakorn", area, NOW, {})
    assert fragments["{{STALE_RIBBON_HIDDEN}}"] == " hidden"


def test_stale_banner_shows_when_data_json_says_stale():
    area = {
        "pumps": [],
        "stations_near": [{"observed_at": None, "role": "north"}],
        "staleness": {"newest_official_obs": "2026-09-26T08:00:00+00:00",
                      "hours_since": 4.0, "banner": True},
        "rain": None,
    }
    fragments = bp.build_area_fragments("sammakorn", area, NOW, {})
    assert fragments["{{STALE_RIBBON_HIDDEN}}"] == ""


def test_safety_fact_present_and_advice_electricity_item_first():
    # maintainer-requested addition after the คลองจั่น electrocution death (2026-09-26):
    # a FACT line (never a command) plus moving the electricity advice to first place.
    assert "ไฟฟ้าดูด" in bp.SAFETY_FACT
    assert bp.ADVICE_ITEMS[0][1].startswith("ปิดเบรกเกอร์ชั้นล่าง")
    for bad in ("ไม่ต้อง", "ห้าม", "ไม่ควร"):
        assert bad not in bp.SAFETY_FACT
        for _, text in bp.ADVICE_ITEMS:
            assert bad not in text


def test_nearby_community_rendered_for_sammakorn_hidden_for_ram53():
    area_with_rows = {"nearby_community": [{"time": "~12:00", "place": "แฟลตคลองจั่น",
                                             "state": "น้ำสูงถึงอก"}]}
    html, hidden = bp.build_nearby_community_rows(area_with_rows)
    assert hidden == ""
    assert "แฟลตคลองจั่น" in html

    area_empty = {"nearby_community": []}
    html2, hidden2 = bp.build_nearby_community_rows(area_empty)
    assert hidden2 == " hidden"
    assert html2 == ""


# --------------------------------------------------------------------- an earlier check mobile
# verifier finding B1 (2026-09-28): the worst-case 72h rain figure (e.g. "100.1 มม.
# (CMA)") was absent from the first screen while a calming trend word ("เบาลง") was
# prominent. `build_indicator_tiles` now takes an optional `pf06` (the same
# `layer0_public.areas.<id>.prop_flood_06` dict `build_layer0_top_html` already reads)
# and surfaces its existing `forecast_72h_worst_text_th` on the rain tile -- no new
# computation, same worst-first string.

_PF06_FIXTURE = {
    "tier_word_th": "เฝ้าระวัง", "tier_color": "#D98A1F",
    "forecast_72h_worst_text_th": "แย่สุด 100.1 มม./72 ชม. (CMA)",
}


def test_rain_tile_shows_72h_worst_with_model_name_when_pf06_present():
    area = {"pumps": [], "rain": {"mm_24h": 12.0, "mm_1h": 1.0, "station": "S1", "dist_km": 1.0}}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    pc = {"fail": 0, "idle": 0, "missing": 0, "ok": 0, "total": 0}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง", pf06=_PF06_FIXTURE)
    assert "แย่สุด 100.1 มม./72 ชม. (CMA)" in html
    # readout tag accompanies the figure (RELAYED: a third-party multi-model forecast)
    assert "tag-relayed" in html


def test_rain_tile_shows_72h_worst_even_with_no_current_rain_reading():
    # the worst-case 72h figure comes from a different source than the live rain
    # gauge -- it must not disappear just because the gauge tile itself falls back
    # to the grey "no data" state.
    area = {"pumps": [], "rain": None}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    pc = {"fail": 0, "idle": 0, "missing": 0, "ok": 0, "total": 0}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง", pf06=_PF06_FIXTURE)
    assert "แย่สุด 100.1 มม./72 ชม. (CMA)" in html


def test_rain_tile_omits_72h_line_when_pf06_absent_never_crashes():
    area = {"pumps": [], "rain": {"mm_24h": 12.0, "mm_1h": 1.0, "station": "S1", "dist_km": 1.0}}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    pc = {"fail": 0, "idle": 0, "missing": 0, "ok": 0, "total": 0}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง")  # pf06 defaults to None
    assert "tile-extra-72h" not in html
    html_none = bp.build_indicator_tiles(area, st, pc, NOW, "บึง", pf06=None)
    assert "tile-extra-72h" not in html_none


def test_build_area_fragments_wires_pf06_from_layer0_public_into_indicator_tiles():
    # end-to-end: build_area_fragments must pick prop_flood_06 for THIS area_id out of
    # layer0_public and pass it through, never crash when layer0_public is missing/empty.
    area = {"pumps": [], "rain": None}
    layer0_public = {"areas": {"sammakorn": {
        "label_th": "สัมมากร", "in_items": [], "out_items": [], "capacity_items": [],
        "prop_flood_06": _PF06_FIXTURE,
    }}}
    fragments = bp.build_area_fragments("sammakorn", area, NOW, {}, layer0_public=layer0_public)
    assert "แย่สุด 100.1 มม./72 ชม. (CMA)" in fragments["{{WHY_LIST}}"]
    # no crash / no leak when layer0_public has nothing for this area
    fragments2 = bp.build_area_fragments("ram53", area, NOW, {}, layer0_public=layer0_public)
    assert "tile-extra-72h" not in fragments2["{{WHY_LIST}}"]
    fragments3 = bp.build_area_fragments("sammakorn", area, NOW, {}, layer0_public=None)
    assert "tile-extra-72h" not in fragments3["{{WHY_LIST}}"]


# ---------------------------------------------------------------------------
# An earlier check mobile verifier B3/B4/B2/A1 fixes (2026-09-28)
# ---------------------------------------------------------------------------

_L0_AREA_FIXTURE = {
    "label_th": "สัมมากร",
    "in_vs_capacity_th": "ยังไม่เกินความสามารถรับมือ",
    "out_vs_in_th": "ระบายไม่ทัน",
    "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
    "in_items": [
        {"label_th": "ECMWF", "text_th": "49 มม.", "tag_th": "ข่าว/บุคคลที่สาม"},
        {"label_th": "GFS", "text_th": "27 มม.", "tag_th": "ข่าว/บุคคลที่สาม"},
    ],
    "out_items": [{"label_th": "ปั๊มหมู่บ้าน", "text_th": "ขัดข้อง", "tag_th": "วัดจากไฟล์ข้อมูล"}],
    "capacity_items": [{"label_th": "บึงรับน้ำ", "text_th": "227,200 ลบ.ม.", "tag_th": "ยืนยันแล้ว"}],
}


def test_layer0_top_html_keeps_model_breakdown_out_of_the_always_visible_part():
    # B3: the FIRST details section (D3) must show only the headline verdict + one
    # visual when first opened -- the per-model in_items rows (source order, e.g.
    # "ECMWF"/"GFS") must be inside a nested, closed-by-default <details>, never bare.
    layer0_public = {"title_th": "สรุปสั้น", "areas": {"sammakorn": _L0_AREA_FIXTURE}}
    html = bp.build_layer0_top_html(layer0_public, "sammakorn")
    assert 'class="dsec-evidence"' in html
    evidence_start = html.index('class="dsec-evidence"')
    headline_idx = html.index("ยังไม่เกินความสามารถรับมือ")
    ecmwf_idx = html.index("ECMWF")
    # headline verdict comes before the nested evidence block that holds the rows
    assert headline_idx < evidence_start < ecmwf_idx
    # the nested details is closed by default (no `open` attribute)
    nested_tag = html[html.rindex("<details", 0, evidence_start):evidence_start + 40]
    assert " open" not in nested_tag.split(">")[0]


def test_layer0_top_html_has_one_mini_visual():
    # B4: one visual accompanies the headline sentence (icon-only in/out/capacity strip).
    layer0_public = {"title_th": "สรุปสั้น", "areas": {"sammakorn": _L0_AREA_FIXTURE}}
    html = bp.build_layer0_top_html(layer0_public, "sammakorn")
    assert 'class="l0-mini-visual"' in html
    assert html.count('class="l0-mini-visual"') == 1


def test_layer0_peek_prefers_72h_worst_then_falls_back_to_verdict():
    layer0_public = {"areas": {
        "sammakorn": {**_L0_AREA_FIXTURE, "prop_flood_06": _PF06_FIXTURE},
        "ram53": _L0_AREA_FIXTURE,
    }}
    assert bp.build_layer0_peek_th(layer0_public, "sammakorn") == "แย่สุด 100.1 มม./72 ชม. (CMA)"
    assert bp.build_layer0_peek_th(layer0_public, "ram53") == "ยังไม่เกินความสามารถรับมือ"
    assert bp.build_layer0_peek_th(layer0_public, "missing") == ""
    assert bp.build_layer0_peek_th(None, "sammakorn") == ""


def test_model_bars_html_worst_first_no_js_widths_from_existing_order():
    # A1/D14: pure HTML/CSS bars, no <script>; width is a display-only parse of the
    # ALREADY worst-first sorted strings -- never re-sorted here.
    items = ["CMA: 100.1 มม.", "KNMI: 96.7 มม.", "MET Norway: 32.9 มม."]
    html = bp._model_bars_html(items)
    assert "<script" not in html
    assert html.index("CMA") < html.index("KNMI") < html.index("MET Norway")
    assert 'class="model-bar-row worst"' in html
    # worst (first, 100.1) bar is full width; the smallest is narrower
    worst_block = html[html.index("CMA"):html.index("KNMI")]
    smallest_block = html[html.index("MET Norway"):]
    worst_pct = float(worst_block[worst_block.index("width:") + 6:worst_block.index("%")])
    smallest_pct = float(smallest_block[smallest_block.index("width:") + 6:smallest_block.index("%")])
    assert worst_pct == 100.0
    assert 0.0 < smallest_pct < worst_pct


def test_model_bars_html_unparseable_item_degrades_to_zero_width_not_dropped():
    html = bp._model_bars_html(["ไม่มีตัวเลข"])
    assert "ไม่มีตัวเลข" in html
    assert 'width:0.0%' in html


def test_d14_model_list_html_uses_bars_not_plain_ul():
    layer0_public = {"areas": {"sammakorn": {"prop_flood_06": {
        **_PF06_FIXTURE, "forecast_72h_items_th": ["CMA: 100.1 มม.", "GFS: 42.6 มม."]}}}}
    html = bp.build_layer0_model_list_html(layer0_public, "sammakorn")
    assert 'class="model-bars"' in html
    assert "<script" not in html


def test_template_d3_summary_uses_dsec_h_and_peek_placeholder():
    # B2: the D3 summary must follow the same dsec-h/dsec-peek pattern as D14 (h2 +
    # peek span), so the shared wrap/no-clip CSS fix applies to it too.
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    d3_idx = template.index('<details id="d3-__AREA__"')
    summary_end = template.index("</summary>", d3_idx)
    summary = template[d3_idx:summary_end]
    assert 'class="dsec-h"' in summary
    assert "{{LAYER0_PEEK}}" in summary


def test_template_summary_css_wraps_peek_instead_of_nowrap_clip():
    # B2 root cause: .dsec-peek used to be white-space:nowrap with margin-inline-
    # start:auto on the same row as the title, which overflowed/clipped at 360px.
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    peek_rule = template[template.index(".dsec-peek{"):template.index("}", template.index(".dsec-peek{"))]
    assert "white-space:normal" in peek_rule
    assert "nowrap" not in peek_rule
    # block layout, not a percentage flex-basis (which still overflowed in Chromium
    # measurement -- see the CSS comment above .dsec-h/.dsec-peek): a block-level
    # peek always wraps to exactly its summary parent's content width.
    assert "display:block" in peek_rule
