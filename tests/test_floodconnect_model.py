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
    spec = _load_json("model_spec.json")
    assert spec["indicators"]["levels"] == ["RED", "YELLOW", "GREEN", "UNKNOWN"]


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
