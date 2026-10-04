"""Tests for tools/backtest/bma_coping_indicator.py (S51 debt-onset readout; NEW DERIVATION /
PROPOSAL -- not yet in Toledo). Checks the D/M.71..76 transcription, the no-cross-window rule,
the scoring cells and the events file's internal consistency. No network."""
from fractions import Fraction
from pathlib import Path

import pytest

from tools.backtest import bma_coping_indicator as ci

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS = REPO_ROOT / "sources" / "bma_coping_indicator_events.yaml"


# ---- D/M.71..76 transcription --------------------------------------------------------
@pytest.mark.parametrize("floor,v,want", [
    (Fraction(1), Fraction(2), "+"),
    (Fraction(1), Fraction(-2), "-"),
    (Fraction(0), Fraction(0), "0"),
    (Fraction(1), Fraction(0), "_|_"),
    (Fraction(1), Fraction(1), "_|_"),      # band edges are inclusive (classify_bot_iff)
    (Fraction(1), Fraction(-1), "_|_"),
    (Fraction(0), Fraction(1, 10), "+"),
])
def test_classify_matches_coq_branches(floor, v, want):
    assert ci.classify(floor, v) == want


def test_bot_needs_positive_resolution():
    # bot_needs_positive_resolution: '_|_' only with floor > 0
    for v in (Fraction(-1), Fraction(0), Fraction(1)):
        assert ci.classify(Fraction(0), v) != "_|_"


# ---- section 5.1 bands against the owner's 1-h design depth --------------------------
def test_design_depths_are_owner_values_per_window():
    assert ci.DESIGN_DEPTH_MM[1] == Fraction("58.7")
    assert ci.DESIGN_DEPTH_MM[24] == Fraction(80)


def test_p1_band_straddles_design_so_unresolved():
    lo, hi = ci.PERIODS["P1"]["rain_band_mm_h"]
    assert ci.borrowing_state(lo, hi, 1) == "_|_"          # 10..60 contains 58.7
    assert ci.borrowing_state(10, "58.6", 1) == "-"


def test_p2_band_is_entirely_over_design():
    lo, hi = ci.PERIODS["P2"]["rain_band_mm_h"]
    assert ci.borrowing_state(lo, hi, 1) == "+"            # 60 > 58.7 -> every hour borrows


def test_open_ended_top_band_never_forms_infinity():
    assert ci.three_state(90, None, "58.7") == "+"
    assert ci.three_state(50, None, "58.7") == "_|_"
    assert ci.three_state(None, 5, 1) == ci.REFUSED


def test_exact_design_hour_is_balance_not_debt():
    assert ci.borrowing_state("58.7", "58.7", 1) == "0"


def test_no_pro_rating_to_undeclared_windows():
    # 3-h, 6-h, 12-h: the owner published no design depth for these windows -> REFUSED,
    # never (H/24)*80 and never an IDF bridge (rules R1/R2)
    for h in (2, 3, 6, 12):
        assert ci.borrowing_state(100, 100, h) == ci.REFUSED
        assert ci.load_ratio(100, 100, h) == (ci.REFUSED, "DESIGN_DEPTH_UNDECLARED")


def test_24h_total_gives_only_a_bound_on_the_hour():
    lo, hi = ci.hourly_interval_from_window_total("205.0")
    assert (lo, hi) == (Fraction(0), Fraction("205.0"))
    assert ci.borrowing_state(lo, hi, 1) == "_|_"          # 26 Sep 2569: hourly unresolved
    assert ci.borrowing_state("205.0", "205.0", 24) == "+"  # 24-h window: certain


# ---- stage / derating ------------------------------------------------------------------
def test_stage_readout_uses_period_edge_and_owner_line():
    s = ci.stage_state("1.84", "P2")
    assert s["derating"] == "+" and s["defence_line"] == "-"
    s = ci.stage_state("2.24", "P3")
    assert s["derating"] == "+" and s["defence_line"] == "+"
    s = ci.stage_state("1.80", "P2")
    assert s["derating"] == "_|_"                          # within gauge resolution of the edge
    assert ci.stage_state(None, "P1")["derating"] == ci.REFUSED


def test_october_is_in_both_p2_and_p3():
    assert ci.periods_for_month(10) == ["P2", "P3"]
    assert ci.periods_for_month(1) == []


# ---- composite + scoring ---------------------------------------------------------------
def test_derating_alone_never_certifies_debt():
    assert ci.composite_state("-", "NA", "+") == "_|_"
    assert ci.composite_state("-", "NA", "-") == "-"
    assert ci.composite_state("+", "NA", "-") == "+"
    assert ci.composite_state("-", ci.REFUSED, "-") == "_|_"
    assert ci.composite_state(ci.REFUSED, "NA", "+") == ci.REFUSED


@pytest.mark.parametrize("issued,truth,cell", [
    ("+", True, "HIT"), ("+", False, "FALSE_ALARM"), ("-", True, "MISS"),
    ("-", False, "CORRECT_NEG"), ("_|_", False, "UNRESOLVED"), ("0", True, "UNRESOLVED"),
    (ci.REFUSED, False, "UNRESOLVED"), ("-", None, "UNRESOLVED"),
])
def test_score_cells(issued, truth, cell):
    assert ci.score(issued, truth) == cell


def test_skill_guard_and_lead():
    assert ci.skill_guard(3, 10) == "REFUSED FEW_EVENTS"
    assert ci.skill_guard(10, 10) == "OK"
    assert ci.lead_ticks(10, 20) == 10
    assert ci.lead_ticks(None, 20) is None


# ---- events file -----------------------------------------------------------------------
def test_events_file_rescores_cleanly(capsys):
    assert ci.summarise(EVENTS) == 0
    out = capsys.readouterr().out
    assert "MISMATCH" not in out
    assert "REFUSED FEW_EVENTS" in out


def test_every_event_and_readout_is_tagged():
    import yaml

    doc = yaml.safe_load(EVENTS.read_text(encoding="utf-8"))
    ok = ("VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN")
    for ev in doc["events"]:
        assert str(ev["tag"]).startswith(ok), ev["event_id"]
        assert "independence_group" in ev, ev["event_id"]
        for r in ev.get("readouts", []):
            assert any(t in str(r["tag"]) for t in ok), (ev["event_id"], r)
