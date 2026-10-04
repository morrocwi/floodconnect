"""tests/test_heromap.py -- tests for tools/heromap/sammakorn_map.py's REMAINING
reusable helpers (classify_tier / worst_tier). Removed 2026-09-28 (founder
verbatim: "เอาเฟสนี้ออกจากหน้าสัมมากร ไม่ต้องใช้แล้ว"): the module's own hero-map render
function (render_sammakorn_hero_map) and every test that exercised it were removed
along with the render wiring in site/build_page.py -- see that module's own docstring
for what was retired and why. `classify_tier`/`worst_tier` are still imported directly
by tests/test_sammakorn_chain.py and (load_normal_levels) tests/
test_official_threshold_admissibility.py, independent of any rendering, so they and
their tests stay.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.heromap.sammakorn_map import classify_tier, worst_tier  # noqa: E402


# ---------------------------------------------------------------------------
# classify_tier / worst_tier
# ---------------------------------------------------------------------------

def test_classify_tier_none_value_is_no_data():
    assert classify_tier(None) == ("NO_DATA", "ไม่มีข้อมูล")


def test_classify_tier_breach_wins_even_without_normal_level():
    key, word = classify_tier(0.95, warning=0.4, critical=0.6, bank=1.98, normal_level_m=None)
    assert key == "CRITICAL"
    assert word == "วิกฤต"


def test_classify_tier_below_warning_but_no_baseline_is_grey_not_green():
    key, word = classify_tier(0.70, warning=2.14, critical=2.68, bank=None, normal_level_m=None)
    assert key == "NO_BASELINE"
    assert key != "NORMAL"


def test_classify_tier_at_or_below_normal_level_is_green():
    key, word = classify_tier(-0.40, warning=0.35, critical=0.45, bank=1.85, normal_level_m=-0.36)
    assert key == "NORMAL"


def test_classify_tier_overbank_outranks_critical():
    key, _ = classify_tier(2.0, warning=0.35, critical=0.45, bank=1.85, normal_level_m=-0.36)
    assert key == "OVERBANK"


def test_worst_tier_prefers_real_breach_over_grey():
    assert worst_tier(["NO_GAUGE", "CRITICAL", "NORMAL"]) == "CRITICAL"


def test_worst_tier_all_grey_stays_grey():
    assert worst_tier(["NO_GAUGE", "NO_DATA"]) in ("NO_GAUGE", "NO_DATA")
