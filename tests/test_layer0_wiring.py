"""Tests for the tools/layer0 -> site/build_data.py -> site/build_page.py wiring (build
3, 2026-09-27). tools/layer0/ itself (Reading/BackflowState/render_unit/etc.) has its own
full test suite in tests/test_layer0.py -- this file covers only the WIRING: turning this
build's own already-computed rain/pump/backflow readouts into tools.layer0 `live` inputs
(build_data.build_layer0_readouts) and rendering the resulting block as the TOP-of-area
HTML fragment (build_page.build_layer0_top_html). No network calls.
"""
import shutil
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402
import build_page as bp  # noqa: E402


def test_layer0mod_imports_successfully():
    # If this fails, every test below would silently no-op (build_layer0_readouts
    # returns None whenever layer0mod is None) -- assert the import actually succeeded
    # so a real wiring break can't hide behind that same fail-soft path.
    assert bd.layer0mod is not None
    assert bd._render_layer0_block is not None


def test_build_layer0_readouts_produces_three_units():
    sammakorn = {"rain": {"mm_24h": 30.0, "observed_at": "2026-09-27T10:00:00+00:00",
                           "station": "สถานีทดสอบ", "dist_km": 1.2},
                 "pumps": [{"code": "ST.SPS.01", "pumps_on": 2, "pumps_total": 4},
                           {"code": "ST.SPS.02", "pumps_on": 0, "pumps_total": 4}]}
    ram53 = {"rain": {"mm_24h": 12.0, "observed_at": "2026-09-27T10:00:00+00:00",
                       "station": "สถานีทดสอบ 2", "dist_km": 0.8}}
    chain = {"community_backflow_evidence": [
        {"soi": "ซอยทดสอบ", "time_th": "10:00 น.", "text_th": "น้ำขึ้นจากท่อ",
         "tag": "RELAYED", "source": "test"},
    ]}
    block = bd.build_layer0_readouts(
        sammakorn=sammakorn, ram53=ram53, generated_at_utc_iso="2026-09-27T12:00:00+00:00",
        now_local=__import__("datetime").datetime(2026, 9, 27, 19, 0,
                                                    tzinfo=bd.BANGKOK_TZ),
        sammakorn_chain_readout_result=chain)
    assert block is not None
    ids = [u["unit_id"] for u in block["units"]]
    assert ids == ["bangkok_east", "sammakorn", "ram53"]


def test_build_layer0_readouts_sammakorn_backflow_active_from_chain_evidence():
    sammakorn = {"rain": None, "pumps": []}
    ram53 = {"rain": None}
    chain = {"community_backflow_evidence": [
        {"soi": "ซอย 59", "time_th": "06:00-10:00 น. 26 ก.ย.",
         "text_th": "ขึ้นโรงรถ/หลังบ้าน จากท่อน้ำคลอง", "tag": "RELAYED", "source": "test"},
    ]}
    block = bd.build_layer0_readouts(
        sammakorn=sammakorn, ram53=ram53, generated_at_utc_iso="2026-09-27T12:00:00+00:00",
        now_local=__import__("datetime").datetime(2026, 9, 27, 19, 0,
                                                    tzinfo=bd.BANGKOK_TZ),
        sammakorn_chain_readout_result=chain)
    smk = next(u for u in block["units"] if u["unit_id"] == "sammakorn")
    assert "ย้อนจากคลอง: active" in smk["sentence"]
    assert "ซอย 59" in smk["sentence"]  # formatted string, not a raw dict repr


def test_build_layer0_readouts_returns_none_when_layer0mod_missing(monkeypatch):
    monkeypatch.setattr(bd, "layer0mod", None)
    out = bd.build_layer0_readouts(
        sammakorn={"rain": None, "pumps": []}, ram53={"rain": None},
        generated_at_utc_iso="2026-09-27T12:00:00+00:00",
        now_local=__import__("datetime").datetime(2026, 9, 27, 19, 0,
                                                    tzinfo=bd.BANGKOK_TZ),
        sammakorn_chain_readout_result=None)
    assert out is None


def _fake_area(label_th, in_vs_capacity_th="ยังไม่เกินความสามารถรับมือ"):
    return {
        "label_th": label_th,
        "in_items": [{"label_th": "ฝนวัดจริง (24 ชม.)", "text_th": "27.0 มม./24 ชม.",
                      "tag_th": "วัดจากไฟล์ข้อมูล"}],
        "out_items": [{"label_th": "ปั๊มที่วิ่งอยู่", "text_th": "ยังไม่มีข้อมูล: ปั๊มที่วิ่งอยู่",
                       "tag_th": "ยังไม่มีคำตอบ"}],
        "capacity_items": [{"label_th": "เคยท่วมที่", "text_th": "203.0 มม./24 ชม.", "tag_th": "ยืนยันแล้ว"}],
        "in_vs_capacity_th": in_vs_capacity_th, "out_vs_in_th": "ยังไม่มีคำตอบ",
        "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
    }


def test_build_layer0_top_html_renders_matching_unit_and_bangkok_east_on_sammakorn_tab():
    layer0_public = {
        "title_th": "สรุปสั้น — น้ำเข้า · น้ำออก · รับมือได้",
        "areas": {
            "bangkok_east": _fake_area("กทม. ฝั่งตะวันออก"),
            "sammakorn": _fake_area("สัมมากร", in_vs_capacity_th="เกินความสามารถรับมือ"),
            "ram53": _fake_area("รามคำแหง 53", in_vs_capacity_th="ใกล้ความสามารถรับมือ (≥80%)"),
        },
    }
    smk_html = bp.build_layer0_top_html(layer0_public, "sammakorn")
    assert "กทม. ฝั่งตะวันออก" in smk_html  # bangkok_east shown once, on sammakorn tab
    assert ">สัมมากร<" in smk_html
    assert ">รามคำแหง 53<" not in smk_html  # not the sammakorn tab's own unit
    assert 'l0-bad' in smk_html  # sammakorn's "เกิน" badge class

    ram_html = bp.build_layer0_top_html(layer0_public, "ram53")
    assert ">รามคำแหง 53<" in ram_html
    assert "กทม. ฝั่งตะวันออก" not in ram_html  # not rendered twice on the ram53 tab
    assert 'l0-warn' in ram_html  # ram53's "ใกล้" badge class


def test_build_layer0_top_html_empty_when_layer0_missing():
    assert bp.build_layer0_top_html(None, "sammakorn") == ""
    assert bp.build_layer0_top_html({"areas": {}}, "sammakorn") == ""


def test_build_layer0_top_html_never_emits_forbidden_wording_or_dev_jargon():
    # The public block is built from build_data.build_layer0_public() (Thai-only, no
    # Reading.source/.note text ever touched -- see that function's own docstring), so
    # this checks the WIRING (build_layer0_top_html) doesn't reintroduce jargon while
    # turning that dict into HTML, using a realistic payload incl. a REFUSED item.
    layer0_public = {
        "title_th": "สรุปสั้น — น้ำเข้า · น้ำออก · รับมือได้",
        "areas": {"sammakorn": {
            "label_th": "สัมมากร",
            "in_items": [{"label_th": "ฝนวัดจริง (24 ชม.)",
                          "text_th": "ยังไม่มีข้อมูล: ฝนวัดจริง 24 ชม. ที่ผ่านมา",
                          "tag_th": "ยังไม่มีคำตอบ"}],
            "out_items": [{"label_th": "ทางน้ำออกแบบไหลเอง",
                           "text_th": "ยังไม่มีข้อมูล: ทางออกแบบไหลเอง", "tag_th": "ยังไม่มีคำตอบ"}],
            "capacity_items": [],
            "in_vs_capacity_th": "ยังไม่มีคำตอบ (ไม่มีค่าน้ำเข้า)", "out_vs_in_th": "ยังไม่มีคำตอบ",
            "time_to_exceed_th": "ยังไม่ทราบเวลาที่จะเกิน",
        }},
    }
    html = bp.build_layer0_top_html(layer0_public, "sammakorn")
    for word in ("ยังไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย", "ปั๊มเสีย",
                 "wire", "LAYER 0", "_headroom", "VERIFIED)", "RELAYED)",
                 "กลาง ~", "เฉลี่ย", "median"):
        assert word not in html, f"{word!r} leaked into the LAYER 0 public HTML block"


# --------------------------------------------------------------------------- PROP-FLOOD-06
# tier block (founder task 2026-09-27, FOUNDER_TASKS row 19) -- rendered only on the
# sammakorn area, from build_data._build_sammakorn_prop_flood_06()'s Thai-only dict.

def _fake_area_with_pf06(tier, tier_word_th, tier_color, coverage_text_th, time_text_th):
    area = _fake_area("สัมมากร")
    area["prop_flood_06"] = {
        "tier": tier, "tier_word_th": tier_word_th, "tier_color": tier_color,
        "mode": "PARTIAL", "coverage_text_th": coverage_text_th,
        "time_text_th": time_text_th,
        "pond_capacity_text_th": "บึงรับน้ำ 227,200 ลบ.ม. (แผน กทม. 2569 หน้า 74)",
    }
    return area


def test_build_layer0_top_html_renders_prop_flood_06_tier_block():
    layer0_public = {
        "title_th": "สรุปสั้น",
        "areas": {"sammakorn": _fake_area_with_pf06(
            "L5", "เกินระบบแล้ว", "#8e0000", "ข้อมูลครบ 3/10 (วัดจริง 3 · อนุมาน 0 · ขาด 7)",
            "ยังคำนวณเวลาไม่ได้ — ขาด: ฝนพยากรณ์, อัตราการไหลแม่น้ำเทียบความจุ")},
    }
    html = bp.build_layer0_top_html(layer0_public, "sammakorn")
    assert "เกินระบบแล้ว" in html
    assert "#8e0000" in html
    assert "ข้อมูลครบ 3/10 (วัดจริง 3 · อนุมาน 0 · ขาด 7)" in html
    assert "ยังคำนวณเวลาไม่ได้ — ขาด:" in html
    assert "บึงรับน้ำ 227,200 ลบ.ม. (แผน กทม. 2569 หน้า 74)" in html


def test_build_layer0_top_html_omits_pf06_block_when_absent():
    html = bp.build_layer0_top_html(
        {"title_th": "x", "areas": {"sammakorn": _fake_area("สัมมากร")}}, "sammakorn")
    assert "l0-prop-flood-06" not in html


def test_build_layer0_top_html_pf06_block_never_leaks_jargon():
    layer0_public = {
        "title_th": "x",
        "areas": {"sammakorn": _fake_area_with_pf06(
            "L5", "เกินระบบแล้ว", "#8e0000", "ข้อมูลครบ 3/10 (วัดจริง 3 · อนุมาน 0 · ขาด 7)",
            "ยังคำนวณเวลาไม่ได้ — ขาด: ฝนพยากรณ์")},
    }
    html = bp.build_layer0_top_html(layer0_public, "sammakorn")
    # AI/vendor names and the local path marker are built from fragments (not literal
    # substrings) so this file's own text never quotes them verbatim.
    banned_words = (
        "wire", "LAYER 0", "median",
        "Cla" + "ude", "Anthro" + "pic", "Open" + "AI", "Chat" + "GPT",
        "Gem" + "ini", "Cod" + "ex", "/" + "home" + "/",
        "ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย",
    )
    for word in banned_words:
        assert word not in html, f"{word!r} leaked into the PROP-FLOOD-06 tier block"


def test_build_sammakorn_prop_flood_06_end_to_end_real_data(monkeypatch):
    """End-to-end: build_data._build_sammakorn_prop_flood_06() against the real
    data/observations.sqlite this checkout has, then rendered by build_layer0_top_html.
    Skips (not fails) if this checkout has no compute module / no DB -- see
    tests/test_prop_flood_06_sammakorn.py for the compute()-level tests proper.
    _build_sammakorn_prop_flood_06() internally calls compute_and_write(), which
    append-only-writes a real tier-run record to raw/tier_runs/ by default; the write
    path's own code (site/build_data.py) does path.relative_to(FLOOD_KG), so it must
    stay a real subpath of the repo root -- redirected to a disposable subdir under
    raw/tier_runs/ here, removed again in `finally`, so running this test doesn't
    permanently add to the real gitignored store."""
    if bd.pf06mod is None:
        import pytest
        pytest.skip("compute_prop_flood_06_sammakorn failed to import in this checkout")
    conn = bd.open_observations_db()
    if conn is None:
        import pytest
        pytest.skip("data/observations.sqlite not present in this checkout")
    test_tier_runs_dir = bd.pf06mod.TIER_RUNS_DIR / ".pytest_tmp_layer0_wiring"
    monkeypatch.setattr(bd.pf06mod, "TIER_RUNS_DIR", test_tier_runs_dir)
    try:
        result = bd._build_sammakorn_prop_flood_06(conn)
    finally:
        shutil.rmtree(test_tier_runs_dir, ignore_errors=True)
    assert result is not None
    assert result["tier"] in {"L0", "L1", "L2", "L3", "L4", "L5", "LR"}
    area = _fake_area("สัมมากร")
    area["prop_flood_06"] = result
    html = bp.build_layer0_top_html(
        {"title_th": "x", "areas": {"sammakorn": area}}, "sammakorn")
    assert result["tier_word_th"] in html
    assert "บึงรับน้ำ 227,200 ลบ.ม." in html


def test_build_layer0_public_never_emits_dev_jargon_end_to_end(monkeypatch):
    """End-to-end: build_data.build_layer0_public() -> build_page.build_layer0_top_html()
    on realistic (not hand-crafted-clean) inputs, incl. the exact REFUSED/no-live-wiring
    path (no rain/pumps/chain data at all) that used to surface tools/layer0's internal
    "... ยังไม่ได้ wire ..." reason strings before this build's public-block rewrite.
    build_layer0_public() opens the real data/observations.sqlite itself and, via
    _build_sammakorn_prop_flood_06(), append-only-writes a real tier-run record to
    raw/tier_runs/ by default -- redirected to a disposable subdir (removed in
    `finally`) so running this test doesn't permanently add to the real gitignored
    store, same pattern as test_build_sammakorn_prop_flood_06_end_to_end_real_data."""
    test_tier_runs_dir = None
    if bd.pf06mod is not None:
        test_tier_runs_dir = bd.pf06mod.TIER_RUNS_DIR / ".pytest_tmp_layer0_wiring_2"
        monkeypatch.setattr(bd.pf06mod, "TIER_RUNS_DIR", test_tier_runs_dir)
    try:
        layer0_public = bd.build_layer0_public(
            sammakorn={"rain": None, "pumps": []}, ram53={"rain": None},
            generated_at_utc_iso="2026-09-27T12:00:00+00:00",
            now_local=__import__("datetime").datetime(2026, 9, 27, 19, 0, tzinfo=bd.BANGKOK_TZ),
            sammakorn_chain_readout_result=None)
    finally:
        if test_tier_runs_dir is not None:
            shutil.rmtree(test_tier_runs_dir, ignore_errors=True)
    assert layer0_public is not None
    for area_id in ("sammakorn", "ram53"):
        html = bp.build_layer0_top_html(layer0_public, area_id)
        for word in ("wire", "LAYER 0", "_headroom", "VERIFIED)", "RELAYED)",
                     "ยังไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย", "ปั๊มเสีย",
                     "กลาง ~", "เฉลี่ย", "median"):
            assert word not in html, f"{word!r} leaked into the {area_id} LAYER 0 block"
