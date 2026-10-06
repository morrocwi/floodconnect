"""Reconciliation of the 8 independently-reviewed
`site/build_page.py::_l5_survival_lines_html()` lines against
`advice/preparedness_ladder.yaml` -- every one of the 8 real lines must be
individually reachable via its own `action_key` on ladder step R3 (never only
covered by the one combined "l5_survival_lines" pointer, which told a reader
nothing about which specific line a given official/general source actually
backs).

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_l5_lines_reachable_in_ladder.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
if str(HERE / "site") not in sys.path:
    sys.path.insert(0, str(HERE / "site"))

import advice.ladder as ladder  # noqa: E402
import build_page as bp  # noqa: E402

# The manual correspondence this reconciliation pass established between each
# of the 8 real lines (by their 0-based index in `_l5_survival_lines_html()`,
# pinned via a short substring unlikely to change by accident) and the
# granular action_key now on ladder step R3.
_LINE_SUBSTRING_TO_ACTION_KEY = {
    "ปิดเบรกเกอร์ไฟหลักได้ทันที": "l5_cut_breaker_if_dry",
    "พาทุกคนและสัตว์เลี้ยงขึ้นชั้นบนสุด": "l5_move_everyone_to_highest_point",
    "คนป่วย/บาดเจ็บโทร": "l5_call_hotlines_table",
    "ขึ้นหลังคาเฉพาะจำเป็น": "l5_roof_signal_if_necessary",
    "น้ำไหลแรงลึกแค่ข้อเท้า": "l5_moving_water_ankle_deep_hazard",
    "จิบน้ำสะอาดหรือน้ำต้มสุก": "l5_sip_water_continue_meds",
    "สายไฟ-ปลั๊กที่เปียกน้ำ": "l5_stay_away_wet_wires_plugs",
    "ดูแลผู้สูงอายุ/ผู้ป่วยติดเตียง": "l5_care_for_vulnerable_closely",
}


def _l5_lines_plain() -> list[str]:
    """Strips the `<li>...</li>` wrapper `_l5_survival_lines_html()` returns --
    the raw text (with inline `<a href="tel:...">` anchors still present, which
    is fine, the substring match below never touches that part) for each of
    the 8 real lines, in order."""
    html = bp._l5_survival_lines_html()
    items = html.split("<li>")[1:]
    return [item.split("</li>")[0] for item in items]


def test_exactly_8_l5_lines_exist():
    lines = _l5_lines_plain()
    assert len(lines) == 8, (
        f"found {len(lines)} L5 survival lines, not the 8 this reconciliation "
        "pass mapped -- update _LINE_SUBSTRING_TO_ACTION_KEY and R3's "
        "action_keys together if a line was added/removed/reworded")


@pytest.mark.parametrize("substring,action_key", list(_LINE_SUBSTRING_TO_ACTION_KEY.items()))
def test_every_l5_line_has_a_matching_real_line(substring, action_key):
    lines = _l5_lines_plain()
    assert any(substring in line for line in lines), (
        f"no L5 survival line contains {substring!r} any more -- "
        f"{action_key} in R3's action_keys is now reconciled against nothing real")


@pytest.mark.parametrize("action_key", list(_LINE_SUBSTRING_TO_ACTION_KEY.values()))
def test_every_l5_line_action_key_is_reachable_on_r3(action_key):
    """Every granular L5 action_key must actually be on a REAL ladder step
    (`advice.ladder.all_steps()`, which `advice/parity.py` and
    `advice.ladder.step_by_action_key` both read) -- never merely documented
    in a comment with no backing row."""
    step = ladder.step_by_action_key(action_key)
    assert step is not None, f"{action_key} is not on any ladder step"
    assert step["id"] == "R3", (
        f"{action_key} is on step {step['id']!r}, not R3 -- the L5 "
        "survival-when-water-is-already-in-the-house ladder row")


def test_every_8_lines_covered_exactly_once():
    """No line is left unmapped, and no two lines collide on the same
    action_key (each of the 8 real lines is distinct content, so each gets
    its own key)."""
    assert len(_LINE_SUBSTRING_TO_ACTION_KEY) == 8
    assert len(set(_LINE_SUBSTRING_TO_ACTION_KEY.values())) == 8
