"""Red-team fixes 2026-09-26 -- tests for site/build_page.py's pump tile and stale
banner logic. No network calls; build_page.py is self-contained (stdlib only)."""
import datetime
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_page as bp  # noqa: E402

NOW = datetime.datetime(2026, 9, 26, 12, 0, tzinfo=datetime.timezone.utc)


def _pump(status_key, observed_at="2026-09-26T11:00:00+00:00"):
    return {"observed_at": observed_at, "status_th": status_key}


def test_pump_tile_separates_fail_from_idle():
    # HIGH-1: 4 pumps total, 3 fail, 1 idle -- tile must read fail-only "3/4", never
    # merge idle into the fault count as "4/4".
    pumps = [
        {"observed_at": "2026-09-26T11:00:00+00:00"},
        {"observed_at": "2026-09-26T11:00:00+00:00"},
        {"observed_at": "2026-09-26T11:00:00+00:00"},
        {"observed_at": "2026-09-26T11:00:00+00:00"},
    ]
    area = {"pumps": pumps}
    pc = {"fail": 3, "idle": 1, "missing": 0, "ok": 0, "total": 4}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง")
    assert "3/4" in html
    assert "4/4" not in html
    assert "ขัดข้อง (กทม. รายงาน)" in html
    assert "ไม่ได้เดิน 1" in html


def test_pump_tile_no_idle_line_when_idle_zero():
    pumps = [{"observed_at": "2026-09-26T11:00:00+00:00"}]
    area = {"pumps": pumps}
    pc = {"fail": 1, "idle": 0, "missing": 0, "ok": 0, "total": 1}
    st = {"fresh_near": [], "fresh_crit": 0, "fresh_up": []}
    html = bp.build_indicator_tiles(area, st, pc, NOW, "บึง")
    assert "1/1" in html
    assert "ไม่ได้เดิน" not in html


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
