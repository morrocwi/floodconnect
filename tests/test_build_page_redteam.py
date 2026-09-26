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
    assert "ปั๊มขัดข้อง (กทม. รายงาน)" in html
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
