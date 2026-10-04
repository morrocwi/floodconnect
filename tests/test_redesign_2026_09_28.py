"""Tests for the 2026-09-28 redesign (docs/design/FLOODCONNECT_UI_REDESIGN_2026-09-28.md):
founder direction "โมเดลไปรวบไว้ข้างล่างก็ได้นะ เน้นข้อมูลน้อยที่สุด ทำเป็นรูปภาพ
ส่วนรายละเอียดให้เอาไว้ท้ายๆ ให้กดแล้วอ่านเข้าใจในสิบวิ" -- the per-model rain
forecast list moves to a collapsed section near the bottom of the page (D14, right
before the water-balance section, which stays last), and the top-of-page LAYER 0
in/out/capacity block moves out of the always-visible hero area into a collapsed
details section. No network calls; build_page.py is self-contained (stdlib only).
"""
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_page as bp  # noqa: E402

TEMPLATE_PATH = Path(__file__).parent.parent / "site" / "index.template.html"


def _layer0_public_with_model_list():
    return {
        "title_th": "สรุปสั้น",
        "areas": {
            "sammakorn": {
                "label_th": "สัมมากร",
                "in_items": [], "out_items": [], "capacity_items": [],
                "in_vs_capacity_th": "รับมือได้", "out_vs_in_th": "ยังไม่มีคำตอบ",
                "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
                "prop_flood_06": {
                    "tier": "L2", "tier_word_th": "เฝ้าระวัง", "tier_color": "#D98A1F",
                    "coverage_text_th": "ข้อมูลครบ 5/10",
                    "time_text_th": "ยังคำนวณเวลาไม่ได้",
                    "pond_capacity_text_th": "บึงรับน้ำ 227,200 ลบ.ม.",
                    "forecast_72h_worst_text_th": "แย่สุด 100.1 มม./72 ชม. (CMA)",
                    "forecast_72h_items_th": [
                        "CMA: 100.1 มม./72 ชม.",
                        "ECMWF: 80.0 มม./72 ชม.",
                        "GFS: 60.0 มม./72 ชม.",
                    ],
                    "engine_note_th": "คำนวณด้วยสมการรุ่น 5 ของเรา; รุ่น 6.1 ที่ยื่นไว้ยังไม่ครบในโค้ด",
                },
            },
        },
    }


# --------------------------------------------------------------------- build_layer0_top_html
# (top-of-page summary): must NEVER carry the per-model list or the dev-jargon engine
# note any more -- both moved to build_layer0_model_list_html() (D14) below.

def test_layer0_top_html_no_longer_carries_per_model_list_or_engine_note():
    html = bp.build_layer0_top_html(_layer0_public_with_model_list(), "sammakorn")
    assert "ECMWF" not in html
    assert "GFS" not in html
    assert "สมการรุ่น" not in html
    # the single worst-case summary line is still allowed at the top (not a per-model
    # breakdown, and never an average/median).
    assert "แย่สุด 100.1 มม./72 ชม." in html


# --------------------------------------------------------------------- build_layer0_model_list_html
# (D14, new): the per-model list lives ONLY here now, worst-first, collapsed.

def test_model_list_html_renders_worst_first_verbatim():
    html = bp.build_layer0_model_list_html(_layer0_public_with_model_list(), "sammakorn")
    assert html.startswith("<details")
    assert "CMA: 100.1 มม./72 ชม." in html
    assert "ECMWF: 80.0 มม./72 ชม." in html
    assert "GFS: 60.0 มม./72 ชม." in html
    # worst-first order preserved verbatim (not re-sorted)
    assert html.index("CMA") < html.index("ECMWF") < html.index("GFS")
    # peek/headline gives the worst case at a glance -- no averaged/median headline
    # (the section explicitly says it is NOT an average -- "ไม่ใช่ค่าเฉลี่ยหรือค่ากลาง"
    # is allowed as a negation; a headline that IS an average/median value is not).
    assert "มัธยฐาน" not in html
    assert "median" not in html.lower()
    assert "ไม่ใช่ค่าเฉลี่ยหรือค่ากลาง" in html


def test_model_list_html_never_leaks_dev_jargon():
    html = bp.build_layer0_model_list_html(_layer0_public_with_model_list(), "sammakorn")
    # AI/vendor names and the local path marker are built from fragments (not literal
    # substrings) so this file's own text never quotes them verbatim.
    banned_words = (
        "สมการรุ่น", "LAYER 0", "wire",
        "Cla" + "ude", "Anthro" + "pic", "Open" + "AI",
        "Chat" + "GPT", "Gem" + "ini", "Cod" + "ex", "/" + "home" + "/",
    )
    for word in banned_words:
        assert word not in html


def test_model_list_html_empty_when_no_forecast_data():
    assert bp.build_layer0_model_list_html(None, "sammakorn") == ""
    assert bp.build_layer0_model_list_html({"areas": {}}, "sammakorn") == ""
    # ram53 has no prop_flood_06 today -- must fail soft to "", never crash.
    assert bp.build_layer0_model_list_html(_layer0_public_with_model_list(), "ram53") == ""


def test_model_list_html_collapsed_by_default_no_open_attribute():
    html = bp.build_layer0_model_list_html(_layer0_public_with_model_list(), "sammakorn")
    assert "<details open" not in html
    assert "<details>" not in html  # always carries its own id


# --------------------------------------------------------------------- template order
# (§1 first-screen order): hero map first, then the model list (D14) sits just before
# the water-balance section (D15), which stays last of all.

def test_template_model_list_placeholder_present():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "{{LAYER0_MODEL_LIST_HTML}}" in template


def test_template_model_list_sits_right_before_waterbalance_details():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    model_list_idx = template.index("{{LAYER0_MODEL_LIST_HTML}}")
    wb_details_tag_idx = template.index('<details id="waterbalance-details-__AREA__"')
    assert model_list_idx < wb_details_tag_idx
    # nothing else (another details section) sits between them -- the only "<details"
    # in this gap is the waterbalance details tag's own opening, found at the end.
    between = template[model_list_idx:wb_details_tag_idx]
    assert "<details" not in between


def test_template_layer0_top_wrap_moved_out_of_always_visible_hero_area():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    # it must now live inside a <details> (collapsed), not directly after the hero
    # banner (an earlier check removal, 2026-09-28: the separate hero-map-wrap/hero4-grid
    # sections above the banner are retired -- the banner itself is now the anchor).
    hero_idx = template.index('class="banner"')
    layer0_idx = template.index("layer0-top-wrap")
    details_idx = template.index('<details id="d3-__AREA__"')
    assert hero_idx < details_idx < layer0_idx
    # still sits above (before) the other detail sections' position is not required --
    # only that it is no longer the immediate sibling of the hero (i.e. wrapped).
    assert 'id="layer0-top-__AREA__"' in template[details_idx:layer0_idx + 200]


def test_template_group_divider_still_says_ten_second_read():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "แต่ละหัวข้ออ่านจบใน 10 วินาที" in template


# --------------------------------------------------------------------- an earlier check removal
# (2026-09-28, founder verbatim: "เอาเฟสนี้ออกจากหน้าสัมมากร ไม่ต้องใช้แล้ว" on the hm2
# block, then "เอาออกทั้ง 4 ช่องด้วย" / "เอาออกเลยดีกว่าให้เข้า hero เลย" on the separate
# above-hero four-driver grid): both the hero-map-wrap section and the hero4-grid are
# retired. The banner is now the first element after the area selector; the compact
# call row moved INSIDE the banner, right after its tile-grid (the four folded
# drivers), so status word + drivers + call buttons sit together near the top.

def test_template_banner_is_first_element_after_area_select():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    select_idx = template.index('class="area-select-wrap"')
    area_start_idx = template.index("<!--AREA_TEMPLATE_START-->")
    banner_idx = template.index('class="banner"')
    assert select_idx < area_start_idx < banner_idx
    # nothing else with its own <section>/<div> content sits between the area
    # template start and the banner -- no leftover hero-map-wrap/hero4-grid.
    between = template[area_start_idx:banner_idx]
    assert "hero-map-wrap" not in between
    assert "hero4-grid" not in between
    assert "{{FOUR_DRIVERS_HTML}}" not in between
    assert "{{HERO_MAP_HTML}}" not in between


def test_template_compact_callrow_sits_inside_banner_after_tile_grid():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    banner_idx = template.index('class="banner"')
    tilegrid_idx = template.index('id="why-list-__AREA__"')
    compact_idx = template.index('class="callrow-compact"')
    rain_trend_idx = template.index('id="rain-trend-__AREA__"')
    assert banner_idx < tilegrid_idx < compact_idx < rain_trend_idx


def test_template_compact_callrow_has_all_three_channels():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    start = template.index('class="callrow-compact"')
    end = template.index("</div>", start)
    block = template[start:end]
    assert 'href="tel:1669"' in block
    assert 'href="tel:1555"' in block
    assert "traffy.in.th" in block


def test_template_no_leftover_hero_map_or_hero4_placeholders():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "{{HERO_MAP_HTML}}" not in template
    assert "{{FOUR_DRIVERS_HTML}}" not in template
    assert "hero-map-wrap" not in template
    assert "hero4-grid" not in template
    assert ".hm2" not in template


# --------------------------------------------------------------------- built page gate
# (founder rules, re-checked against a real build if dist/ exists from this run)

DIST = Path(__file__).parent.parent / "site" / "dist" / "floodconnect.html"


def test_built_page_banned_words_and_model_list_position():
    if not DIST.exists():
        import pytest
        pytest.skip("dist/floodconnect.html not built in this checkout")
    html = DIST.read_text(encoding="utf-8")
    # AI/vendor names and the local path marker are built from fragments (not literal
    # substrings) so this file's own text never quotes them verbatim.
    banned_words = (
        "ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย", "LAYER 0", "wire", "median",
        "Cla" + "ude", "Anthro" + "pic", "Open" + "AI", "Chat" + "GPT",
        "Gem" + "ini", "Cod" + "ex", "/" + "home" + "/",
        "PROP-FLOOD-08", "PROP-FLOOD-09", "PROP-FLOOD-10",
    )
    for w in banned_words:
        assert w not in html, f"{w!r} leaked into the built page"
    assert "วัดจริง" in html
    # An earlier check removal (2026-09-28): the hm2 block (and, before it, the old
    # compass-diagram map) is retired entirely -- no hm2-* class should be present.
    assert "hm2-pump-sq" not in html
    assert 'class="hm2"' not in html
    # the model-list section (its details id) sits after the waterbalance heading's
    # own details id start position check isn't meaningful post-templating (ids repeat
    # per area) -- assert instead that at least one model-list details block exists and
    # a waterbalance details block follows somewhere after it for the sammakorn area.
    m_idx = html.index("d14-model-list-sammakorn")
    wb_idx = html.index('id="waterbalance-details-sammakorn"')
    assert m_idx < wb_idx


# --------------------------------------------------------------------- folded-in four
# drivers (an earlier check fold, 2026-09-28, founder verbatim: "เอาออกทั้ง 4 ช่องด้วย" ...
# "เอาออกเลยดีกว่าให้เข้า hero เลย"): the four drivers ฝน/การระบาย/น้ำเหนือ/น้ำหนุน no
# longer render as a separate hero4-grid above the banner -- they fold into the
# existing banner tile-grid (build_indicator_tiles()) instead, as normal `.tile` cards,
# order ฝน/การระบาย/น้ำเหนือ/น้ำหนุน/คลองรอบบ้าน (5th, unchanged position).

import datetime as _dt

_NOW = _dt.datetime(2026, 9, 28, 9, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=7)))

_PF06_MODEL_FIXTURE = {"forecast_72h_worst_text_th": "แย่สุด 100.1 มม./72 ชม. (CMA)"}


def _folded_area():
    return {
        "pumps": [{"code": "ST.SPS.01", "pond_name": "บึงรับน้ำสัมมากร 1",
                    "pumps_on": 1, "pumps_total": 2, "status_th": None,
                    "observed_at": "2026-09-28T01:00:00+00:00", "level_m": 0.5}],
        "stations_near": [],
        "rain": {"mm_24h": 12.0, "mm_1h": 1.0, "station": "S1", "dist_km": 1.0},
        "tide": {},
    }


def test_folded_tile_grid_renders_exactly_four_tiles():
    # An earlier check removal (2026-09-28, coordinator follow-up): the คลองรอบบ้าน 5th tile
    # is dropped from this always-visible grid (its info already lives in full,
    # unduplicated, in the canal-table detail sections further down the page) --
    # exactly the four folded drivers ฝน/การระบาย/น้ำเหนือ/น้ำหนุน remain.
    area = _folded_area()
    pc = bp.pump_counts(area["pumps"], _NOW)
    st = bp.compute_status(area, _NOW, pc)
    html = bp.build_indicator_tiles(area, st, pc, _NOW, "บึง", pf06=_PF06_MODEL_FIXTURE,
                                     area_id="sammakorn")
    # exact outer-wrapper class match only ("tile-value"/"tile-label"/etc. all start
    # with the substring "tile" too, so a loose `in` count would over-count them).
    wrapper_count = html.count('<div class="tile">') + html.count('<a class="tile tile-link"')
    assert wrapper_count == 4
    assert "คลองรอบบ้าน" not in html


def test_folded_tile_grid_rain_tile_shows_worst_case_and_model_pill():
    area = _folded_area()
    pc = bp.pump_counts(area["pumps"], _NOW)
    st = bp.compute_status(area, _NOW, pc)
    html = bp.build_indicator_tiles(area, st, pc, _NOW, "บึง", pf06=_PF06_MODEL_FIXTURE,
                                     area_id="sammakorn")
    assert "แย่สุด 100.1 มม./72 ชม. (CMA)" in html
    assert 'tag-pill tag-relayed' in html
    assert '>แบบจำลอง<' in html


def test_folded_tile_grid_rain_tile_falls_back_to_rain_now_without_pf06():
    # ram53-shaped call: no pf06 (no PROP-FLOOD-06 tier engine for this area today) --
    # the ฝน tile must still show the live rain-now reading, never disappear/blank.
    area = _folded_area()
    pc = bp.pump_counts(area["pumps"], _NOW)
    st = bp.compute_status(area, _NOW, pc)
    html = bp.build_indicator_tiles(area, st, pc, _NOW, "บึง", area_id="ram53")
    assert "1.0 มม./ชม." in html
    assert "tile-extra-72h" not in html


def test_folded_tile_grid_pump_tile_links_to_its_own_d1_table():
    area = _folded_area()
    pc = bp.pump_counts(area["pumps"], _NOW)
    st = bp.compute_status(area, _NOW, pc)
    html = bp.build_indicator_tiles(area, st, pc, _NOW, "บึง", area_id="sammakorn")
    assert '<a class="tile tile-link" href="#d1-pump-sammakorn"' in html


def test_folded_tile_grid_short_evidence_pills_not_long_form():
    # An earlier check fold: these four driver tiles use the SHORT pill wording ("วัดจริง",
    # "ทางการ") the retired hero4-grid used, not the long-form default
    # ("วัดจากไฟล์ข้อมูล", "ทางการแถลง") the rest of the page still uses elsewhere.
    area = _folded_area()
    pc = bp.pump_counts(area["pumps"], _NOW)
    st = bp.compute_status(area, _NOW, pc)
    html = bp.build_indicator_tiles(area, st, pc, _NOW, "บึง", area_id="sammakorn")
    assert "วัดจริง" in html
    assert "วัดจากไฟล์ข้อมูล" not in html
    assert "ทางการแถลง" not in html
