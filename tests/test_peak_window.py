"""Tests for tools/backtest/peak_window.py -- pure functions only (no network, no raw files)."""
import itertools
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "backtest"))

import peak_window as pw  # noqa: E402

LEVELS = [0, 1, 2]
RANK = {c: i for i, c in enumerate(pw.CLASSES)}


def test_days_to_full_matches_hand_arithmetic_pasak():
    # Pasak 27 Sep: storage 779.8, full-by-% 871.5 (=779.8/0.8948 rounded), inflow 59.14, release 2.16
    d = pw.days_to_full(779.8, 960, 59.14, 2.16)
    assert d["state"] == "FILLING"
    assert d["headroom_mcm"] == pytest.approx(180.2)
    assert d["net_mcm_day"] == pytest.approx(56.98)
    assert d["days"] == pytest.approx(180.2 / 56.98)


def test_days_to_full_refuses_never_zero():
    assert pw.days_to_full(None, 960, 1, 1)["state"] == "REFUSED"
    assert pw.days_to_full(100, 200, 1.0, 1.0)["state"] == "NOT_FILLING"
    assert pw.days_to_full(100, 200, 0.5, 1.0)["state"] == "NOT_FILLING"
    assert pw.days_to_full(210, 200, 5, 1)["state"] == "AT_OR_ABOVE_FULL"
    assert "days" not in pw.days_to_full(100, 200, 1.0, 1.0)


def test_release_changes_detects_steps_not_noise():
    s = {"2026-09-20": {"release": 1.30}, "2026-09-21": {"release": 1.30},
         "2026-09-22": {"release": 1.32}, "2026-09-23": {"release": 2.16},
         "2026-09-24": {"release": None}, "2026-09-25": {"release": 2.16}}
    ch = pw.release_changes(s)
    assert [c["date"] for c in ch] == ["2026-09-23"]
    assert ch[0]["delta"] == pytest.approx(0.84)


def test_forced_flag_is_flag_only_when_above_urc_and_soon():
    soon = pw.days_to_full(779.8, 871.5, 59.14, 2.16)
    far = pw.days_to_full(7606.06, 9510, 22.74, 8.03)
    assert pw.forced_release_flag(779.8, 445.33, soon) == "FLAG"
    assert pw.forced_release_flag(7606.06, 8664.09, far) == "NO_FLAG"
    assert pw.forced_release_flag(96.08, 78.67, pw.days_to_full(96.08, 106.22, 2.28, 1.97)) == "NO_FLAG"


def test_driver_levels_thresholds():
    assert pw.rain_level(80.0) == 2 and pw.rain_level(79.9) == 1 and pw.rain_level(35.0) == 0
    assert pw.rain_level(None) is None
    assert pw.tide_level(1.16) == 2 and pw.tide_level(1.14) == 2
    assert pw.tide_level(1.04) == 1 and pw.tide_level(0.96) == 0
    assert pw.drainage_level(2.24, None) == 2 and pw.drainage_level(1.85, None) == 1
    assert pw.drainage_level(1.2, True) == 2 and pw.drainage_level(None, None) is None
    assert pw.upstream_level(1950, False) == 2 and pw.upstream_level(1000, False) == 1
    assert pw.upstream_level(None, True) is None and pw.upstream_level(None, False) is None
    assert pw.upstream_floor(None, True) == 1 and pw.upstream_floor(1950, True) == 0


def test_combined_class_is_monotone_in_every_driver():
    for lv in itertools.product(LEVELS, repeat=4):
        base = RANK[pw.combined_class(*lv)]
        for i in range(4):
            if lv[i] < 2:
                up = list(lv); up[i] += 1
                assert RANK[pw.combined_class(*up)] >= base, (lv, i)


def test_combined_class_refuses_unresolved_and_interval_brackets():
    with pytest.raises(ValueError):
        pw.combined_class(0, 2, None, 2)
    ci = pw.combined_interval(0, 2, None, 2)
    assert ci == {"hi": "สูงสุด", "lo": "สูง", "resolved": False}
    assert RANK[ci["hi"]] >= RANK[ci["lo"]]
    ci2 = pw.combined_interval(0, 2, None, 1, floors={"up": 1})
    assert ci2 == {"hi": "สูง", "lo": "ปานกลาง", "resolved": False}


def test_trend_labels_rise_peak_fall_and_rebound():
    seq = ["สูง", "สูง", "สูงสุด", "สูงสุด", "ปานกลาง", "ปานกลาง", "สูง", "ต่ำ"]
    assert pw.trend_labels(seq) == ["เพิ่มขึ้น", "เพิ่มขึ้น", "สูงสุด", "สูงสุด",
                                    "ลดลง", "ลดลง", "เพิ่มขึ้น", "ต่ำ"]
