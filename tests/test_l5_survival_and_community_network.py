"""Tests for the 2026-09-28 life-safety addition (founder-approved: "ได้เลย ขอระดับโลก
เท่านั้น"): the L5 survival card (shown inside the hero banner, above the four driver
tiles, only when this area's PROP-FLOOD-06 tier is L5) and the "ช่วยกันเป็นเครือข่าย"
community-network details block. No network calls; build_page.py is self-contained
(stdlib only).
"""
import re
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_page as bp  # noqa: E402

DIST = Path(__file__).parent.parent / "site" / "dist" / "floodconnect.html"

BANNED_WORDS = ("ไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย")

L5_LINES_TH = [
    "ตัวแห้ง-มือแห้งเท่านั้น ปิดเบรกเกอร์ไฟหลักได้ทันที",
    "พาทุกคนและสัตว์เลี้ยงขึ้นชั้นบนสุด/ดาดฟ้า อยู่รวมจุดเดียวกัน",
    "คนป่วย/บาดเจ็บโทร",
    "ขึ้นหลังคาเฉพาะจำเป็น",
    "น้ำไหลแรงลึกแค่ข้อเท้า (~15 ซม.) ก็ล้มได้",
    "จิบน้ำสะอาดหรือน้ำต้มสุกทีละน้อยให้พอนาน",
    "สายไฟ-ปลั๊กที่เปียกน้ำ อยู่ห่างไว้เสมอ",
    "ดูแลผู้สูงอายุ/ผู้ป่วยติดเตียง/เด็กเป็นพิเศษ",
]


def _pf06(tier):
    return {"tier": tier, "tier_word_th": "x", "tier_color": "#000"}


# --------------------------------------------------------------------- L5 survival card

def test_l5_card_absent_when_no_pf06():
    assert bp.build_l5_survival_card_html(None) == ""


def test_l5_card_absent_when_tier_not_l5():
    for tier in ("L0", "L1", "L2", "L3", "L4", "LR"):
        assert bp.build_l5_survival_card_html(_pf06(tier)) == ""


def test_l5_card_present_when_tier_is_l5():
    html = bp.build_l5_survival_card_html(_pf06("L5"))
    assert html != ""
    assert bp.L5_SURVIVAL_HEADLINE_TH in html
    # an earlier check (coordinator layout fix): the spaces around the em dash are
    # non-breaking (U+00A0) so the dash never wraps onto its own orphan line --
    # same wording, verify the exact constant round-trips into the built HTML.
    assert "น้ำเข้าบ้านแล้ว เจ้าหน้าที่ยังไม่มา — ทำตามนี้" in html
    # collapsed-by-default is not acceptable for life-safety content
    assert '<details class="l5-details" open>' in html


def test_l5_card_has_all_eight_lines():
    html = bp.build_l5_survival_card_html(_pf06("L5"))
    for line in L5_LINES_TH:
        assert line in html, f"missing L5 line: {line!r}"
    assert html.count("<li>") == 8


def test_l5_card_every_phone_number_is_tel_link():
    html = bp.build_l5_survival_card_html(_pf06("L5"))
    for number in ("1130", "1669", "1784", "1555"):
        assert f'href="tel:{number}"' in html
    # an earlier check (coordinator layout fix): 4 tap-target buttons under the headline
    # (1669/1784/1130/1555) PLUS the same 5 inline occurrences inside the numbered
    # list (1130 appears twice, line 1 and line 3, the others once each) -- 9 total.
    assert html.count('href="tel:') == 9


def test_l5_card_call_grid_has_four_buttons_right_labels():
    html = bp.build_l5_survival_card_html(_pf06("L5"))
    assert '<div class="l5-callgrid"' in html
    for number, label in (("1669", "การแพทย์"), ("1784", "ปภ."), ("1130", "ไฟฟ้า"), ("1555", "กทม.")):
        assert f'<a class="l5-callbtn" href="tel:{number}">{number}<span class="l5-callbtn-sub">{label}</span></a>' in html
    # the call grid comes right after the headline, before the numbered list
    assert html.index("l5-callgrid") < html.index("l5-list")


def test_l5_card_source_line_present():
    html = bp.build_l5_survival_card_html(_pf06("L5"))
    assert "อ้างอิง:" in html
    assert "ready.gov" in html and "gov.uk" in html


def test_l5_card_no_banned_words():
    html = bp.build_l5_survival_card_html(_pf06("L5"))
    for w in BANNED_WORDS:
        assert w not in html, f"{w!r} leaked into the L5 survival card"


# --------------------------------------------------------------------- community-network block

def test_community_network_sammakorn_has_niti_phone():
    html = bp.build_community_network_html("sammakorn")
    assert "02-373-8004" in html
    assert 'href="tel:+6623738004"' in html
    assert "ยังไม่ยืนยันจากหน่วยงาน" in html


def test_community_network_ram53_generic_no_niti_phone():
    html = bp.build_community_network_html("ram53")
    assert "02-373-8004" not in html
    # the generic ปิดท้าย caveat line ("เช็กกับนิติบุคคลก่อนย้าย") still applies to both
    # areas -- only the Sammakorn-specific รถรับ-ส่ง phone row is dropped.
    assert "รถรับ-ส่งของนิติบุคคล" not in html


def test_community_network_three_groups_present():
    html = bp.build_community_network_html("sammakorn")
    assert "ตัวเรา" in html
    assert "ซอย/ชุมชน" in html
    assert "ส่งต่อถึงรัฐ" in html


def test_community_network_government_numbers_are_tel_links():
    html = bp.build_community_network_html("sammakorn")
    for number in ("1669", "1130", "1784", "1555"):
        assert f'href="tel:{number}"' in html


def test_community_network_template_present_with_copy_button():
    html = bp.build_community_network_html("sammakorn")
    assert bp.COMMUNITY_NETWORK_TEMPLATE_TH in html
    assert "<pre" in html and "cn-copy-btn" in html
    assert 'data-copy-target="cn-template-text-sammakorn"' in html


def test_community_network_unverified_exit_note_present():
    html = bp.build_community_network_html("sammakorn")
    assert bp.COMMUNITY_NETWORK_NOTE_TH in html


def test_community_network_no_banned_words():
    for area_id in ("sammakorn", "ram53"):
        html = bp.build_community_network_html(area_id)
        for w in BANNED_WORDS:
            assert w not in html, f"{w!r} leaked into community-network block ({area_id})"


# --------------------------------------------------------------------- built page gate

def test_built_page_l5_card_and_community_network_present():
    if not DIST.exists():
        import pytest
        pytest.skip("dist/floodconnect.html not built in this checkout")
    html = DIST.read_text(encoding="utf-8")
    assert 'id="community-network-details-sammakorn"' in html
    assert 'id="community-network-details-ram53"' in html
    # the L5 card only renders for an area whose live PROP-FLOOD-06 tier is genuinely
    # L5 this run -- assert the mechanism exists (empty wrapper divs for both areas)
    # rather than a specific tier, which can change between builds.
    assert re.search(r'id="l5-card-sammakorn">', html)
    assert re.search(r'id="l5-card-ram53">', html)
    for w in BANNED_WORDS:
        assert w not in html, f"{w!r} leaked into the built page"
