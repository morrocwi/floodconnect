"""Tests for floodconnect_model.py -- the pure-stdlib, no-DB/no-network by-hand compute
path described in docs/EQUATIONS_FOR_AI.md. The one test this file exists to guarantee
(`test_classify_matches_kb_for_shared_status_words`) pins `classify_counts()` against
`kb.py`'s own `_classify_current_local_state` for the same inputs, per FIX B item 6."""
import pytest

import kb
import floodconnect_model as fm


# ---------------------------------------------------------------------------
# delta_k (PROP-FLOOD-01)
# ---------------------------------------------------------------------------

def test_delta_k_rising():
    r = fm.delta_k(0.38, 0.30, epsilon=0.01)
    assert r["trend"] == "RISING"
    assert round(r["value"], 2) == 0.08


def test_delta_k_falling():
    r = fm.delta_k(0.30, 0.38, epsilon=0.01)
    assert r["trend"] == "FALLING"


def test_delta_k_flat_within_epsilon():
    r = fm.delta_k(0.301, 0.300, epsilon=0.01)
    assert r["trend"] == "FLAT"


def test_delta_k_no_readout_when_missing():
    r = fm.delta_k(0.38, None, epsilon=0.01)
    assert r == {"value": None, "trend": "NO_READOUT"}
    r2 = fm.delta_k(None, 0.30, epsilon=0.01)
    assert r2["trend"] == "NO_READOUT"


# ---------------------------------------------------------------------------
# time_to_threshold (PROP-FLOOD-02)
# ---------------------------------------------------------------------------

def test_time_to_threshold_worked_example():
    delta = fm.delta_k(0.38, 0.30, epsilon=0.01)
    r = fm.time_to_threshold(0.38, delta, theta=0.45, k=1, epsilon=0.01)
    assert r["unit"] == "ticks"
    assert round(r["value"], 3) == 0.875


def test_time_to_threshold_refused_flat_is_unresolved():
    delta = fm.delta_k(0.301, 0.300, epsilon=0.01)
    r = fm.time_to_threshold(0.301, delta, theta=0.45, k=1, epsilon=0.01)
    assert r["value"] is None
    assert r["reason"] == "UNRESOLVED"


def test_time_to_threshold_refused_falling_is_not_applicable():
    delta = fm.delta_k(0.30, 0.38, epsilon=0.01)
    r = fm.time_to_threshold(0.30, delta, theta=0.45, k=1, epsilon=0.01)
    assert r["value"] is None
    assert r["reason"] == "NOT_APPLICABLE"


def test_time_to_threshold_refused_threshold_already_crossed():
    delta = fm.delta_k(0.50, 0.30, epsilon=0.01)
    r = fm.time_to_threshold(0.50, delta, theta=0.45, k=1, epsilon=0.01)
    assert r["value"] is None
    assert r["reason"] == "NOT_APPLICABLE"


def test_time_to_threshold_refused_no_readout_propagates():
    delta = fm.delta_k(0.38, None, epsilon=0.01)
    r = fm.time_to_threshold(0.38, delta, theta=0.45, k=1, epsilon=0.01)
    assert r == {"value": None, "reason": "NOT_APPLICABLE"}


# ---------------------------------------------------------------------------
# classify / classify_counts -- MUST agree with kb.py for the same inputs
# ---------------------------------------------------------------------------

def test_classify_single_word():
    assert fm.classify("CRITICAL") == "RED"
    assert fm.classify("OVERBANK") == "RED"
    assert fm.classify("WATCH") == "YELLOW"
    assert fm.classify("NORMAL") == "GREEN"
    # Fix (2026-10-04): a station with no agency threshold
    # published at all carries no basis for GREEN -- it is UNKNOWN, never GREEN.
    assert fm.classify("NO_THRESHOLD") == "UNKNOWN"
    assert fm.classify(None) == "UNKNOWN"
    assert fm.classify("SOME_UNRECOGNISED_WORD") == "UNKNOWN"


def test_classify_matches_kb_for_shared_status_words():
    """FIX B item 6's acceptance criterion: `classify_counts()` must give the SAME
    classification as `kb.py`'s real `_classify_current_local_state` for the same
    inputs, across every English status-word case this module recognises."""
    cases = [
        {"CRITICAL": 1},
        {"OVERBANK": 1},
        {"WATCH": 1},
        {"NORMAL": 1},
        {"NO_THRESHOLD": 2},
        {},
        {"NORMAL": 1, "WATCH": 1},
        {"WATCH": 1, "CRITICAL": 1},
        {"NORMAL": 3, "NO_THRESHOLD": 1},
    ]
    for status_counts in cases:
        ours = fm.classify_counts(status_counts)
        theirs = kb._classify_current_local_state({"status_counts": status_counts})
        assert ours == theirs, f"{status_counts}: floodconnect_model={ours!r} kb.py={theirs!r}"


def test_classify_counts_no_threshold_only_is_unknown_never_green():
    """Regate finding #2's acceptance test: a station whose only published status is
    `NO_THRESHOLD` (no agency level at all) must be UNKNOWN, never GREEN -- fixed in
    v0.1.2 (v0.1.1 put `NO_THRESHOLD` in the GREEN/normal-like set with no basis)."""
    assert fm.classify_counts({"NO_THRESHOLD": 1}) == "UNKNOWN"
    assert fm.classify_counts({"NO_THRESHOLD": 5}) == "UNKNOWN"
    assert kb._classify_current_local_state({"status_counts": {"NO_THRESHOLD": 1}}) == "UNKNOWN"
    # A mix with a real NORMAL reading is still GREEN -- NO_THRESHOLD rows are
    # discarded, not promoted into evidence either way.
    assert fm.classify_counts({"NORMAL": 3, "NO_THRESHOLD": 1}) == "GREEN"


# ---------------------------------------------------------------------------
# one_decision -- the by-hand six-step procedure, Jev vocabulary, BOT != ZERO
# ---------------------------------------------------------------------------

def test_one_decision_no_reading_is_refused_not_zero():
    r = fm.one_decision({"h_t": None})
    assert r["gate"] == "REFUSED"
    assert r["confidence"] == "NONE"
    assert r["level"] == "UNKNOWN"
    assert "NO_READOUT" in r["decision"]


def test_one_decision_official_status_outranks_own_computation():
    r = fm.one_decision({
        "h_t": 0.38, "h_t_minus_k": 0.30, "epsilon": 0.01,
        "official_status": "WATCH", "station_id": "WL.SSB.08",
    })
    assert r["level"] == "YELLOW"
    assert r["gate"] == "LICENSED_WITHIN_ENVELOPE"
    assert "official" in r["why"]


def test_one_decision_rising_with_time_to_threshold():
    r = fm.one_decision({
        "h_t": 0.38, "h_t_minus_k": 0.30, "k": 1, "epsilon": 0.01, "theta": 0.45,
        "station_id": "WL.SSB.08",
    })
    assert r["level"] == "YELLOW"
    assert r["gate"] == "LICENSED_WITHIN_ENVELOPE"
    assert "RISING" in r["decision"]
    assert "0.88" in r["decision"] or "0.87" in r["decision"]


def test_one_decision_stale_is_refused():
    r = fm.one_decision({
        "h_t": 0.38, "h_t_minus_k": 0.30, "epsilon": 0.01, "fresh": False,
    })
    assert r["gate"] == "REFUSED"
    assert r["confidence"] == "NONE"


def test_one_decision_missing_epsilon_is_refused_not_a_guess():
    r = fm.one_decision({"h_t": 0.38})
    assert r["gate"] == "REFUSED"
    assert any("epsilon" in c for c in r["checks"])


def test_one_decision_falling_above_theta_is_never_green():
    """A falling reading that is STILL above a declared threshold must never be
    reported GREEN just because the trend is falling -- the trend-only path (no
    official status) is a conservative by-hand aid, not a clearance."""
    r = fm.one_decision({
        "h_t": 1.95, "h_t_minus_k": 2.00, "epsilon": 0.01, "theta": 0.45,
        "station_id": "X",
    })
    assert r["level"] != "GREEN"
    assert r["level"] == "YELLOW"
    assert "FALLING" in r["decision"]
    assert "no threshold risk" not in r["decision"]


def test_one_decision_falling_without_status_or_theta_is_unknown():
    r = fm.one_decision({
        "h_t": 0.30, "h_t_minus_k": 0.38, "epsilon": 0.01, "station_id": "X",
    })
    assert r["level"] == "UNKNOWN"
    assert r["level"] != "GREEN"
    assert "FALLING" in r["decision"]


def test_one_decision_flat_without_status_or_theta_is_unknown():
    r = fm.one_decision({
        "h_t": 0.30, "h_t_minus_k": 0.30, "epsilon": 0.01, "station_id": "X",
    })
    assert r["level"] == "UNKNOWN"
    assert r["level"] != "GREEN"
    assert "FLAT" in r["decision"]


# ---------------------------------------------------------------------------
# Indicators dictionary (docs/INDICATORS.md, founder ruling 2026-10-04:
# "ที่สำคัญคือให้ ตัวชี้วัดนี้น้ำน้ำท่วมต้องชัด" -- the flood indicators must be clear)
# ---------------------------------------------------------------------------
import json
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent.parent

INDICATOR_NAMES = [
    "current_local_state", "forward_hazard", "rise_rate_dk", "time_to_threshold_tk",
    "rain_24h_mm", "rain_7day_per_model_mm", "distance_to_bank_m", "bank_fill_percent",
    "one_decision", "water_debt",
]


def _load_json(name: str) -> dict:
    return json.loads((_HERE / name).read_text(encoding="utf-8"))


def test_indicators_block_has_every_closed_name():
    spec = _load_json("model_spec.json")
    names = {row["name"] for row in spec["indicators"]["names"]}
    assert names == set(INDICATOR_NAMES)


def test_indicators_levels_are_the_closed_vocabulary():
    """Fix (2026-10-04, review finding #3): the bare RED/YELLOW/GREEN/UNKNOWN list is
    scoped under 'color_contract', not a top-level 'levels' claimed to apply to every
    indicator -- see test_every_indicator_entry_declares_its_own_levels for the
    per-indicator check."""
    spec = _load_json("model_spec.json")
    assert spec["indicators"]["color_contract"]["levels"] == ["RED", "YELLOW", "GREEN", "UNKNOWN"]
    assert "current_local_state" in spec["indicators"]["color_contract"]["applies_to"][0]


def test_model_spec_and_system_capabilities_indicators_match():
    spec = _load_json("model_spec.json")
    caps = _load_json("system_capabilities.json")
    assert spec["indicators"] == caps["indicators"]


def test_indicators_doc_exists_and_names_every_indicator():
    doc = (_HERE / "docs" / "INDICATORS.md").read_text(encoding="utf-8")
    for name in INDICATOR_NAMES:
        assert f"`{name}`" in doc, f"{name} missing from docs/INDICATORS.md"


def test_readme_llms_tiers_equations_link_and_name_indicators():
    """Every one of the four first-contact docs must link docs/INDICATORS.md AND name
    every indicator, so an AI reading any single one of them still gets the closed
    dictionary -- never just the equations doc or just the README."""
    for path in ("README.md", "llms.txt", "docs/AI_TIERS.md", "docs/EQUATIONS_FOR_AI.md"):
        text = (_HERE / path).read_text(encoding="utf-8")
        assert "docs/INDICATORS.md" in text, f"{path} does not link docs/INDICATORS.md"
        for name in INDICATOR_NAMES:
            assert name in text, f"{name} missing from {path}"


def test_every_indicator_entry_declares_its_own_levels():
    """Fix (2026-10-04, review finding #3): the colour contract (RED/YELLOW/GREEN/
    UNKNOWN) is not a universal rule -- every indicator must carry its own 'levels'
    key in model_spec.json, and only current_local_state/one_decision may use the
    shared colour-contract vocabulary."""
    spec = _load_json("model_spec.json")
    rows = {row["name"]: row for row in spec["indicators"]["names"]}
    assert set(rows) == set(INDICATOR_NAMES)
    for name, row in rows.items():
        assert "levels" in row, f"{name} has no 'levels' key"
    colour = ["RED", "YELLOW", "GREEN", "UNKNOWN"]
    assert rows["current_local_state"]["levels"] == colour
    assert rows["one_decision"]["levels"]["level"] == colour
    # every other indicator's levels must NOT silently reuse the bare colour contract
    # list as if it were the closed vocabulary (forward_hazard's real vocabulary is
    # ACTIVE/NONE/UNKNOWN, not RED/YELLOW/GREEN/UNKNOWN).
    assert rows["forward_hazard"]["levels"] == ["ACTIVE", "NONE", "UNKNOWN"]
    assert rows["forward_hazard"]["levels"] != colour


# Real, offline answer -- the output test review finding #4 asked for: every value this
# repository's own compute path (kb.build_answer, against "sammakorn", real recorded
# fixture data already in the repo's data/ store -- see tests/conftest.py's real-data
# guard) and its by-hand companion (floodconnect_model.one_decision) actually EMITS must
# be a name/value this dictionary declares, never an undeclared word.
_DUAL_STATE_LEVELS = {
    "current_local_state": ["RED", "YELLOW", "GREEN", "UNKNOWN"],
    "forward_hazard": ["ACTIVE", "NONE", "UNKNOWN"],
}


def test_offline_answer_dual_state_matches_declared_levels():
    payload = kb.build_answer("sammakorn", refresh=False)
    dual_state = payload["next_action"]["dual_state"]
    for key, declared in _DUAL_STATE_LEVELS.items():
        assert key in dual_state, f"next_action.dual_state missing {key!r}"
        assert dual_state[key] in declared, (
            f"next_action.dual_state[{key!r}] = {dual_state[key]!r} is not one of "
            f"the declared levels {declared!r} in docs/INDICATORS.md / model_spec.json"
        )
    assert payload.get("indicators_doc") == "docs/INDICATORS.md"


def test_offline_answer_names_an_unresolvable_point_outside_thailand_still_declared():
    """The outside-Thailand branch (`_outside_thailand`) returns UNKNOWN/UNKNOWN for
    both dual_state fields and must still carry `indicators_doc` -- never a shape only
    this one branch produces."""
    payload = kb.build_answer("999,999", refresh=False)
    dual_state = payload["next_action"]["dual_state"]
    for key, declared in _DUAL_STATE_LEVELS.items():
        assert dual_state[key] in declared
    assert payload.get("indicators_doc") == "docs/INDICATORS.md"


def test_method_not_data_service_framing_present(): # review finding #2
    """Founder ruling 2026-10-04: FloodConnect gives the METHOD (which sources, how
    to pick the nearest station, the equations/thresholds, the honesty rules); your
    own AI geocodes and finds nearby POIs; the CLI/MCP is an OPTIONAL helper. Every
    first-contact doc + system_capabilities.json must say so and point at the
    nearest-station recipe for a tool-less chat AI."""
    recipe = _HERE / "docs" / "NEAREST_STATION_RECIPE.md"
    assert recipe.is_file(), "docs/NEAREST_STATION_RECIPE.md is missing"
    recipe_text = recipe.read_text(encoding="utf-8")
    for marker in ("geocod", "nearest station", "radius", "UNKNOWN"):
        assert marker.lower() in recipe_text.lower(), f"{marker!r} missing from recipe doc"

    caps = _load_json("system_capabilities.json")
    assert caps["method_not_data_service"]["recipe_for_chat_ai_with_no_tool"] == (
        "docs/NEAREST_STATION_RECIPE.md")

    for path in ("README.md", "llms.txt", "docs/AI_TIERS.md", "docs/EQUATIONS_FOR_AI.md"):
        text = (_HERE / path).read_text(encoding="utf-8")
        assert "NEAREST_STATION_RECIPE.md" in text, f"{path} does not link the recipe doc"
        assert ("geocod" in text.lower() or "พิกัด" in text), (
            f"{path} does not frame geocoding as the caller's own job")


# ---------------------------------------------------------------------------
# M8 Jev Sandwich functions -- real-fixture cases (tests/fixtures/bma_watermap/
# sammakorn_case_20261005_trimmed.json: WL.SSB.08 วิกฤต, WL.BMA.02 ปกติ, WL.SMK.01 ปกติ,
# a real trimmed capture, 2026-10-05, see that fixture's own .sidecar.json).
# ---------------------------------------------------------------------------

def _load_watermap_fixture():
    return _load_json("tests/fixtures/bma_watermap/sammakorn_case_20261005_trimmed.json")


def _by_code(rows, code):
    return next(r for r in rows if r["water_code"] == code)


def test_trend_state_stable_real_smk01_readings():
    # WL.SMK.01 real readings 5 min apart, both -0.45 (tests/fixtures/bma_station_detail/
    # stationdetail_id284_20261005_trimmed.html, last two points).
    r = fm.trend_state(-0.45, -0.45, epsilon=0.01)
    assert r["trend"] == "STABLE"
    assert r["eq"] == "PROP-FLOOD-01"


def test_trend_state_agency_trend_closed_map():
    assert fm.trend_state(None, None, 0.01, agency_trend="RISING")["trend"] == "RISING"
    assert fm.trend_state(None, None, 0.01, agency_trend="STABLE")["basis"] == "agency"


def test_bank_check_real_ssb08_at_critical():
    rows = _load_watermap_fixture()
    ssb08 = _by_code(rows, "WL.SSB.08")
    r = fm.bank_check(ssb08["wl_in"], critical=ssb08["critical"], bank=ssb08["left_bank"])
    assert r["state"] == "AT_OR_OVER"
    assert r["basis"] == "level"


def test_bank_check_real_smk01_below_critical_gap():
    rows = _load_watermap_fixture()
    smk01 = _by_code(rows, "WL.SMK.01")
    r = fm.bank_check(smk01["wl_in"], critical=smk01["critical"])
    assert r["state"] == "BELOW"
    assert round(r["gap"], 2) == 0.89


def test_bank_check_agency_word_overbank():
    r = fm.bank_check(5.49, critical=None, bank=2.75, agency_word="ล้นตลิ่ง (ม.)")
    assert r["state"] == "AT_OR_OVER"
    assert r["basis"] == "agency_word"


def test_bank_check_unset_zero_critical_is_not_a_real_threshold():
    """Regression test, real station MKVKD01 (EGAT):
    the agency publishes `critical_level_msl: 0` (never actually set) alongside a real
    `min_bank: 92.74` and `ground_level: 74.22`, h=80.4 m MSL, status word
    `thaiwater_situation_3` (below warning -- not a critical-like word). Before the
    fix, bare `critical is not None` accepted the 0 as a real threshold and
    `h >= 0` returned AT_OR_OVER (a false RED). The 0 critical must now be dropped as
    unusable, leaving the real `bank` (92.74, well above `ground_level`) as the only
    threshold -- h is 12.34 m below it, so the state is BELOW, never AT_OR_OVER."""
    r = fm.bank_check(80.4, critical=0.0, bank=92.74, ground_level=74.22)
    assert r["state"] == "BELOW"
    assert round(r["gap"], 2) == 12.34
    assert r["theta"] == 92.74


def test_bank_check_zero_bank_and_critical_with_no_agency_word_is_unknown():
    """The same degenerate-zero-threshold case with NO usable bank either (both 0,
    and `ground_level` also 0) and no agency word to fall back on -- the only honest
    answer is UNKNOWN, never AT_OR_OVER on a threshold that was never really set."""
    r = fm.bank_check(99.54, critical=0.0, bank=0.0, ground_level=0.0)
    assert r["state"] == "UNKNOWN"
    assert r["theta"] is None


def test_bank_check_zero_bank_overbank_word_gives_unknown_not_red():
    """Real
    station BLGTU05 -- `min_bank`/`critical_level_msl`/`ground_level` are all 0
    (never set). The feed's own `diff_wl_bank_text` reads "ล้นตลิ่ง", but that text is
    itself computed as `h - min_bank` = `h - 0`, not a real agency observation --
    `collect._thaiwater_status_word` no longer emits "OVERBANK" for this case (see its
    own fix), and `bank_check` itself now refuses to trust an "OVERBANK"/"ล้นตลิ่ง"-
    family word with no usable threshold behind it either way: this must come out
    UNKNOWN, never RED/AT_OR_OVER. (Inverts the prior test, which asserted the
    opposite.)"""
    r = fm.bank_check(99.54, critical=0.0, bank=0.0, ground_level=0.0, agency_word="OVERBANK")
    assert r["state"] == "UNKNOWN"


def test_bank_check_non_bank_diff_critical_word_still_wins_with_zero_thresholds():
    """A genuinely independent agency status classification (never a bank-diff
    artifact -- e.g. a direct "CRITICAL"/"วิกฤต" situation report) is still trusted
    even when bank/critical/ground are all unset, unlike the "OVERBANK"/"ล้นตลิ่ง"
    family above -- only the bank-diff-derived words lost that trust."""
    r = fm.bank_check(99.54, critical=0.0, bank=0.0, ground_level=0.0, agency_word="CRITICAL")
    assert r["state"] == "AT_OR_OVER"
    assert r["basis"] == "agency_word"


def test_colour_ladder_real_cases():
    rows = _load_watermap_fixture()
    ssb08 = _by_code(rows, "WL.SSB.08")
    bma02 = _by_code(rows, "WL.BMA.02")
    smk01 = _by_code(rows, "WL.SMK.01")
    assert fm.colour_ladder({"status_word": ssb08["txtStatus"], "h": ssb08["wl_in"],
                              "critical": ssb08["critical"], "warning": ssb08["warning"],
                              "fresh": True})["colour"] == "RED"
    assert fm.colour_ladder({"status_word": bma02["txtStatus"], "h": bma02["wl_in"],
                              "critical": bma02["critical"], "warning": bma02["warning"],
                              "fresh": True})["colour"] == "GREEN"
    assert fm.colour_ladder({"status_word": smk01["txtStatus"], "h": smk01["wl_in"],
                              "critical": smk01["critical"], "warning": smk01["warning"],
                              "trend": "STABLE", "fresh": True})["colour"] == "GREEN"


def test_colour_ladder_unknown_when_not_fresh_or_faulted_or_no_threshold():
    assert fm.colour_ladder({"h": 1.0, "fresh": False})["colour"] == "UNKNOWN"
    assert fm.colour_ladder({"h": 1.0, "fault": True, "fresh": True})["colour"] == "UNKNOWN"
    assert fm.colour_ladder({"h": 1.0, "fresh": True})["colour"] == "UNKNOWN"


def test_colour_ladder_mkvkd01_zero_critical_never_false_reds():
    """Regression test: real station MKVKD01's own
    published fields (h=80.4, bank=92.74, critical=0.0 (unset), ground_level=74.22,
    status word thaiwater_situation_3, below-warning per the agency) must never fold
    to RED -- before the fix this gave RED via the unset critical=0."""
    r = fm.colour_ladder({"status_word": "thaiwater_situation_3", "h": 80.4,
                           "critical": 0.0, "bank": 92.74, "ground_level": 74.22,
                           "fresh": True})
    assert r["colour"] != "RED"
    assert r["colour"] == "GREEN"


def test_colour_ladder_orange_rising_above_warning_below_critical():
    r = fm.colour_ladder({"h": 0.40, "warning": 0.35, "critical": 0.44,
                           "trend": "RISING", "fresh": True})
    assert r["colour"] == "ORANGE"
    assert fm.ORANGE_NOTE in r["reasons"]


def test_ring_readout_worst_and_at_or_over():
    rows = [
        {"id": "A", "colour": "GREEN", "fresh": True},
        {"id": "B", "colour": "RED", "fresh": True, "trend": "RISING"},
        {"id": "C", "status_word": "เตือนภัย", "fresh": False},
    ]
    r = fm.ring_readout(rows, relation="SAME_SUBBASIN")
    assert r["worst"] == "RED"
    assert r["at_or_over"] == ["B"]
    assert r["any_rising"] is True
    assert r["n"] == 3
    assert r["n_fresh"] == 2
    assert r["relation"] == "SAME_SUBBASIN"


def test_ring_readout_a_stale_row_colour_is_never_trusted():
    """Mutation-protecting test (review finding 5): a NON-fresh row's own
    colour must never be trusted for `worst` -- `fm.ring_readout` reads it as
    UNKNOWN regardless of what colour the row itself carries. Isolated from
    `test_ring_readout_worst_and_at_or_over` above (there, a fresh RED row
    already decides `worst` regardless of the stale row, so reverting this
    specific line would not fail that test)."""
    rows = [{"id": "A", "colour": "RED", "fresh": False}]
    r = fm.ring_readout(rows, relation="SAME_SUBBASIN")
    assert r["worst"] == "UNKNOWN", (
        "a stale RED row must never drag the ring to RED -- its colour is "
        "unknown, not the last value it happened to carry")
    assert r["at_or_over"] == [], "a stale row is never AT_OR_OVER either"


def test_ring_readout_empty_ring_floors_to_unknown():
    """Mutation-protecting test (review finding 5): an empty ring (no rows at
    all) must report `worst: UNKNOWN`, never `None` or a falsy default --
    `worst` starts UNDECIDED (`None`) specifically so a genuinely all-GREEN
    ring can report GREEN (see this function's own docstring), which means an
    EMPTY ring needs its own explicit floor back to UNKNOWN, not a decided
    colour by accident."""
    r = fm.ring_readout([], relation="SAME_SUBBASIN")
    assert r["worst"] == "UNKNOWN"
    assert r["n"] == 0
    assert r["n_fresh"] == 0


def test_sandwich_decision_bottom_red_never_needs_middle():
    rows = _load_watermap_fixture()
    ssb08 = _by_code(rows, "WL.SSB.08")
    z0 = {"status_word": ssb08["txtStatus"], "h": ssb08["wl_in"],
          "critical": ssb08["critical"], "fresh": True}
    r = fm.sandwich_decision(z0, z3={}, middle=None)
    assert r["colour"] == "RED"
    assert r["needs_middle"] is False
    assert r["gate"] == "LICENSED_WITHIN_ENVELOPE"


def test_sandwich_decision_bottom_unknown_is_refused():
    r = fm.sandwich_decision({"h": None, "fresh": True}, z3={})
    assert r["colour"] == "UNKNOWN"
    assert r["gate"] == "REFUSED"
    assert r["needs_middle"] is False


def test_sandwich_decision_agree_green_when_top_calm():
    """Updated (S2, founder 2026-10-05): a Z3 with only a SAME_SUBBASIN row (no
    UPSTREAM_PATH/UPSTREAM_CHAIN/UPSTREAM_REACH row at all) never reaches AGREE --
    "top calm" can't honestly be claimed when nothing on an actual upstream relation
    was read (an earlier pass: 644/645 AGREE answers had read zero upstream stations).
    Z0's own GREEN still stands (S1: never lower than Z0's own word), via
    TOP_NO_UPSTREAM at LOW confidence instead."""
    rows = _load_watermap_fixture()
    smk01 = _by_code(rows, "WL.SMK.01")
    z0 = {"status_word": smk01["txtStatus"], "h": smk01["wl_in"],
          "critical": smk01["critical"], "warning": smk01["warning"],
          "trend": "STABLE", "fresh": True}
    z3 = {"stations": [{"id": "CALM", "status_word": "ปกติ", "relation": "SAME_SUBBASIN",
                         "fresh": True}]}
    r = fm.sandwich_decision(z0, z3, middle=None)
    assert r["colour"] == "GREEN"
    assert r["needs_middle"] is False
    assert "TOP_NO_UPSTREAM" in r["reasons"]
    assert r["confidence"] == "LOW"
    assert r["official_tier"] is False


def test_sandwich_decision_agree_green_with_fresh_upstream_calm():
    """AGREE still fires normally when an actual upstream row (UPSTREAM_PATH) was
    read and is calm -- the real top-calm case S2 preserves."""
    rows = _load_watermap_fixture()
    smk01 = _by_code(rows, "WL.SMK.01")
    z0 = {"status_word": smk01["txtStatus"], "h": smk01["wl_in"],
          "critical": smk01["critical"], "warning": smk01["warning"],
          "trend": "STABLE", "fresh": True}
    z3 = {"stations": [{"id": "CALM", "status_word": "ปกติ", "relation": "UPSTREAM_PATH",
                         "fresh": True}]}
    r = fm.sandwich_decision(z0, z3, middle=None)
    assert r["colour"] == "GREEN"
    assert r["needs_middle"] is False
    assert "AGREE" in r["steps"]


def test_sandwich_decision_sammakorn_real_case_needs_middle_then_yellow():
    """The real Sammakorn case (2026-10-05): Z0 WL.SMK.01 ปกติ/STABLE, Z3 includes
    WL.SSB.08 วิกฤต on relation UPSTREAM_PATH (fix: only an
    UPSTREAM_PATH station raises `top_alert` on a RED reading, never a plain
    SAME_SUBBASIN one that may be downstream/unrelated) -> CONFLICT -> needs_middle;
    with the middle WL.BMA.02 ปกติ (UPSTREAM_CHAIN, not rising) -> YELLOW เฝ้าระวัง,
    per the founder's ladder (a conflict is resolved by extracting the middle, never
    downgraded on its own)."""
    rows = _load_watermap_fixture()
    smk01 = _by_code(rows, "WL.SMK.01")
    ssb08 = _by_code(rows, "WL.SSB.08")
    bma02 = _by_code(rows, "WL.BMA.02")

    z0 = {"status_word": smk01["txtStatus"], "h": smk01["wl_in"],
          "critical": smk01["critical"], "warning": smk01["warning"],
          "trend": "STABLE", "fresh": True}
    z3 = {"stations": [{"id": "WL.SSB.08", "status_word": ssb08["txtStatus"],
                         "relation": "UPSTREAM_PATH", "fresh": True}]}
    facts = [("WL.SSB.08", ssb08["txtStatus"], "OUTLET", 0.55)]

    first = fm.sandwich_decision(z0, z3, middle=None, facts=facts)
    assert first["needs_middle"] is True
    assert first["colour"] is None
    assert first["steps"] == ["READ_BOTTOM", "READ_TOP", "CONFLICT"]

    middle = [{"id": "WL.BMA.02", "status_word": bma02["txtStatus"],
               "relation": "UPSTREAM_CHAIN", "trend": "STABLE", "fresh": True}]
    final = fm.sandwich_decision(z0, z3, middle=middle, facts=facts)
    assert final["colour"] == "YELLOW"
    assert final["label_th"] == "เฝ้าระวัง"
    assert final["steps"] == ["READ_BOTTOM", "READ_TOP", "CONFLICT", "EXTRACT_MIDDLE", "DECIDE"]
    assert "MIDDLE_NOT_RISING" in final["reasons"]
    assert final["facts"] == facts


def test_sandwich_read_top_same_subbasin_red_never_raises_alert():
    """Regression: a RED station that is only SAME_SUBBASIN (not
    actually upstream of Z0 along the reach chain) must never raise `top_alert` --
    the founder's own rule is Z3 = the KG-connected UPSTREAM stations, not every
    station sharing a (possibly 15,000+ km^2) sub-basin regardless of direction."""
    z3 = {"stations": [{"id": "DOWNSTREAM_RED", "status_word": "วิกฤต",
                         "relation": "SAME_SUBBASIN", "fresh": True}]}
    top = fm._sandwich_read_top(z3)
    assert top["alert"] is False
    z3_up = {"stations": [{"id": "UPSTREAM_RED", "status_word": "วิกฤต",
                            "relation": "UPSTREAM_PATH", "fresh": True}]}
    top_up = fm._sandwich_read_top(z3_up)
    assert top_up["alert"] is True


def test_sandwich_decision_bottom_orange_plus_top_alert_never_downgrades_to_yellow():
    """Regression: a Z0 the bottom ladder itself rates ORANGE
    (RISING, above the agency's own warning level, below critical) plus a top
    alert must still resolve ORANGE or higher -- never fall back to YELLOW just
    because the middle ring didn't happen to independently confirm it too. The
    founder's own rule: a local ORANGE plus a top alert IS the agreement case."""
    z0 = {"status_word": "เตือนภัย", "h": 0.5, "warning": 0.4, "critical": 0.6,
          "bank": None, "trend": "RISING", "fresh": True}
    z3 = {"stations": [{"id": "TOP1", "status_word": "วิกฤต", "relation": "UPSTREAM_PATH",
                         "fresh": True}]}
    first = fm.sandwich_decision(z0, z3, middle=None)
    assert first["needs_middle"] is True

    middle = [{"id": "MID1", "status_word": "ปกติ", "relation": "UPSTREAM_CHAIN",
               "trend": "STABLE", "fresh": True}]
    final = fm.sandwich_decision(z0, z3, middle=middle)
    assert final["colour"] == "ORANGE"
    assert any("NEVER_DOWNGRADED" in r for r in final["reasons"])


def test_rise_eta_enabled_by_default_since_toledo_pr65_merged():
    """founder ruling 2026-10-06: PR #65 merged into Toledo main
    2026-10-06 (65297f05) registers PROP-FLOOD-11 as a PROPOSAL -- `PROP11_ENABLED`
    now defaults True. With no `pump_state` declared, the caller-must-declare rule
    still refuses (PUMP_STATE_UNDECLARED, never silently defaulted to UNCHANGED) --
    this is a real, named refusal, not the old module-level GATED."""
    assert fm.PROP11_ENABLED is True
    r = fm.rise_eta(0.38, 0.30, 0.22, theta=0.45, k_ticks=1, tick_desc="ticks", epsilon=0.01)
    assert r["prop11"] == {"status": "PUMP_STATE_UNDECLARED"}
    assert r["tk"]["value"] is not None  # PROP-FLOOD-02 (registered) still computes


def test_rise_eta_at_bank_checked_first():
    r = fm.rise_eta(0.50, 0.30, 0.20, theta=0.45, k_ticks=1, tick_desc="ticks", epsilon=0.01)
    assert r["tk"] == {"value": None, "reason": "AT_BANK"}
    assert r["prop11"] == {"status": "AT_BANK"}


def test_rise_eta_not_applicable_when_not_rising():
    r = fm.rise_eta(0.30, 0.38, 0.40, theta=0.45, k_ticks=1, tick_desc="ticks", epsilon=0.01)
    assert r["tk"] == {"value": None, "reason": "NOT_APPLICABLE"}
    assert r["prop11"] == {"status": "NOT_APPLICABLE"}


def test_rise_eta_prop11_enabled_only_in_test_math_check(monkeypatch):
    """`PROP11_ENABLED` is True by default now (Toledo PR #65 merged) -- this test
    still pins it True explicitly (belt-and-suspenders against a future default
    flip) so it keeps checking the function's own arithmetic (L(n) = h + n*delta +
    n(n+1)/2*D2 solved for theta) regardless of that default."""
    monkeypatch.setattr(fm, "PROP11_ENABLED", True)
    r = fm.rise_eta(0.40, 0.30, 0.20, theta=0.70, k_ticks=1, tick_desc="ticks", epsilon=0.01,
                     pump_state="RUNNING")
    assert r["prop11"]["status"] == "OK"
    assert r["prop11"]["n"] > 0

    r2 = fm.rise_eta(0.40, 0.30, 0.20, theta=0.70, k_ticks=1, tick_desc="ticks", epsilon=0.01,
                      pump_state="UNDECLARED")
    assert r2["prop11"]["status"] == "PUMP_STATE_UNDECLARED"

    r3 = fm.rise_eta(0.40, 0.30, None, theta=0.70, k_ticks=1, tick_desc="ticks", epsilon=0.01,
                      pump_state="RUNNING")
    assert r3["prop11"]["status"] == "SPARSE_SERIES"


def test_rise_eta_hours_range_computes_a_range_from_two_slopes():
    """founder ruling 2026-10-06: WL.SMK.01-shaped inputs -- h now 0.30, 0.02m up over the last
    5-min step (short slope) and 0.10m up over the last hour (long slope, which
    includes a slower earlier stretch) -- warning=0.45, critical=0.55. The range
    must be [min, max] of the two slopes' own linear ETA, never averaged, and both
    thresholds must be present."""
    r = fm.rise_eta_hours_range(
        h_t=0.30, h_short_prev=0.28, short_hours=5 / 60.0,
        h_long_prev=0.20, long_hours=1.0,
        theta_warn=0.45, theta_crit=0.55, epsilon=0.01, pump_state="UNCHANGED")
    assert r["warning"]["status"] == "OK"
    lo, hi = r["warning"]["range_h"]
    assert lo <= hi
    # short slope (0.02/5min = 0.24 m/h) reaches 0.45 faster than the long slope
    # (0.10 m/h) -- short_h must be the smaller of the two.
    assert r["warning"]["short_h"] == pytest.approx(lo, abs=0.05)
    assert r["critical"]["status"] == "OK"
    assert r["critical"]["range_h"][0] <= r["critical"]["range_h"][1]


def test_rise_eta_hours_range_gated_when_module_disabled(monkeypatch):
    monkeypatch.setattr(fm, "PROP11_ENABLED", False)
    r = fm.rise_eta_hours_range(0.30, 0.28, 5 / 60.0, 0.20, 1.0, theta_warn=0.45,
                                 pump_state="UNCHANGED")
    assert r == {"status": "GATED", "reason": "PROP-FLOOD-02 ETA switched off (PROP11_ENABLED=False)"}


def test_rise_eta_hours_range_at_bank_checked_first():
    r = fm.rise_eta_hours_range(0.60, 0.58, 5 / 60.0, 0.50, 1.0, theta_crit=0.55,
                                 pump_state="UNCHANGED")
    assert r["critical"]["status"] == "AT_BANK"


def test_rise_eta_hours_range_pump_undeclared_refuses():
    r = fm.rise_eta_hours_range(0.30, 0.28, 5 / 60.0, 0.20, 1.0, theta_warn=0.45)
    assert r["warning"]["status"] == "PUMP_STATE_UNDECLARED"


def test_rise_eta_hours_range_none_threshold_skipped():
    r = fm.rise_eta_hours_range(0.30, 0.28, 5 / 60.0, 0.20, 1.0, theta_warn=0.45,
                                 theta_crit=None, pump_state="UNCHANGED")
    assert r["critical"] is None
    assert r["warning"]["status"] == "OK"


def test_sensor_fault_word_khat_khong_chua_khrao_added_to_shared_set():
    """Finding #6: the real watermap archive also carries ขัดข้องชั่วคราว for the same
    sensor-fault condition -- without this, it fell through to a normal-like/YELLOW
    read, inventing evidence."""
    import live_water_level as lwl
    assert "ขัดข้องชั่วคราว" in lwl.SENSOR_FAULT_STATUS_TH
    assert "ขัดข้อง" in lwl.SENSOR_FAULT_STATUS_TH
    assert lwl.sensor_status_from_status_th("ขัดข้องชั่วคราว") == "fault"


def test_one_decision_level_and_confidence_match_declared_levels():
    spec = _load_json("model_spec.json")
    rows = {row["name"]: row for row in spec["indicators"]["names"]}
    declared = rows["one_decision"]["levels"]
    cases = [
        {"h_t": 0.38, "h_t_minus_k": 0.30, "epsilon": 0.01, "station_id": "X", "k": 1},
        {"h_t": 0.30, "h_t_minus_k": 0.38, "epsilon": 0.01, "station_id": "X"},
        {"h_t": None, "station_id": "X"},
        {"h_t": 0.30, "official_status": "WATCH", "station_id": "X"},
    ]
    for inputs in cases:
        r = fm.one_decision(inputs)
        assert r["level"] in declared["level"], r
        assert r["confidence"] in declared["confidence"], r
        assert r["gate"] in declared["gate"], r
