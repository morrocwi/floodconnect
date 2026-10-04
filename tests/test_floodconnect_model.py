"""Tests for floodconnect_model.py -- the pure-stdlib, no-DB/no-network by-hand compute
path described in docs/EQUATIONS_FOR_AI.md. The one test this file exists to guarantee
(`test_classify_matches_kb_for_shared_status_words`) pins `classify_counts()` against
`kb.py`'s own `_classify_current_local_state` for the same inputs, per FIX B item 6."""
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
    assert fm.classify("NO_THRESHOLD") == "GREEN"
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
