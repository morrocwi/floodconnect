"""Community / social-listening reports must render newest-first (founder ask
2026-09-27): a reader opening the page should see the latest situation first,
not the oldest report from hours ago. Covers build_page.sort_reports_newest_first
and the community/nearby-community row renderers for both areas.
"""
import datetime
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_page as bp  # noqa: E402

BANGKOK_TZ = datetime.timezone(datetime.timedelta(hours=7))


def test_sort_reports_newest_first_mixed_order_with_ranges_and_one_unparseable():
    items = [
        {"time": "07:00", "date": "2026-09-26", "place": "ซอย A", "state": "เข้าบ้าน"},
        {"time": "06:00-08:00", "date": "2026-09-27", "place": "ซอย B", "state": "ท่วมถนน"},
        {"time": "X", "date": None, "place": "ไม่ทราบจุด", "state": "เวลาไม่ชัด"},
        {"time": "09:00", "date": "2026-09-27", "place": "ซอย C", "state": "น้ำลด"},
        {"time": "10:00-12:00", "date": "2026-09-26", "place": "ซอย D", "state": "เข้าชั้น 1"},
    ]
    out = bp.sort_reports_newest_first(items)
    places = [r["place"] for r in out]
    # newest first: 27 ก.ย. 09:00 > 27 ก.ย. 06:00(-08:00) > 26 ก.ย. 10:00(-12:00) > 26 ก.ย. 07:00
    # the unparseable "X" row goes last, in its original relative position among the tail.
    assert places == ["ซอย C", "ซอย B", "ซอย D", "ซอย A", "ไม่ทราบจุด"]


def test_sort_reports_newest_first_is_stable_for_equal_keys():
    items = [
        {"time": "09:00", "date": "2026-09-27", "place": "first", "state": "-"},
        {"time": "09:00", "date": "2026-09-27", "place": "second", "state": "-"},
        {"time": "X", "date": None, "place": "unparseable-1", "state": "-"},
        {"time": "ไม่ชัด", "date": None, "place": "unparseable-2", "state": "-"},
    ]
    out = bp.sort_reports_newest_first(items)
    assert [r["place"] for r in out] == ["first", "second", "unparseable-1", "unparseable-2"]


def test_build_community_rows_renders_newest_first_for_sammakorn():
    area = {
        "community": [
            {"time": "04:00", "date": "2026-09-26", "place": "ซอย 50", "state": "เข้าบ้าน"},
            {"time": "10:00", "date": "2026-09-27", "place": "ซอย 40", "state": "ท่วม"},
            {"time": "06:00-08:00", "date": "2026-09-26", "place": "ซอย 48", "state": "เข้าชั้น 1"},
        ]
    }
    now_dt = datetime.datetime(2026, 9, 27, 12, 0, tzinfo=BANGKOK_TZ)
    html = bp.build_community_rows(area, now_dt)
    # newest (27 ก.ย. 10:00) must appear before the two 26 ก.ย. rows
    assert html.index("ซอย 40") < html.index("ซอย 48") < html.index("ซอย 50")
    # today's row (27 ก.ย.) shows bare time; yesterday's rows carry the date suffix
    assert ">10:00<" in html
    assert "(26 ก.ย.)" in html


def test_build_nearby_community_rows_sorted_and_hidden_when_empty():
    now_dt = datetime.datetime(2026, 9, 27, 12, 0, tzinfo=BANGKOK_TZ)
    empty_html, hidden = bp.build_nearby_community_rows({}, now_dt)
    assert empty_html == "" and hidden == " hidden"

    area = {"nearby_community": [
        {"time": "~07:00 (9 ชม.)", "date": "2026-09-26", "place": "แฟลตคลองจั่น", "state": "สภาพเก่า"},
        {"time": "~13:00 (3 ชม.)", "date": "2026-09-26", "place": "แฟลตคลองจั่น", "state": "สภาพล่าสุด"},
    ]}
    html, hidden = bp.build_nearby_community_rows(area, now_dt)
    assert hidden == ""
    assert html.index("สภาพล่าสุด") < html.index("สภาพเก่า")  # 13:00 (newer) before 07:00
