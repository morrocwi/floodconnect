import copy
import json
from pathlib import Path

from tests.dsva_v010_helpers import rebind

from dsva_decision import (
    STATUS_CONTRADICTION,
    STATUS_HOLD,
    STATUS_INVALIDATED,
    STATUS_LICENSED,
    STATUS_LOCAL,
    STATUS_UNRESOLVED,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads(
        (ROOT / "examples" / "dsva_decision_minimal.json").read_text(
            encoding="utf-8"
        )
    )


def test_demo_licenses_prepare_and_rejects_wait():
    r = evaluate(demo())
    assert r["status"] == STATUS_LICENSED
    assert r["selected_action"] == "PREPARE"
    assert "PREPARE" in r["viable_actions"]
    assert "WAIT" in r["rejected_actions"]
    assert r["cost_ledger"]["trace_cache_hits"] > 0


def test_first_order_gap_holds():
    s = demo()
    s["closures"]["first_order"]["transition"] = False
    r = evaluate(s)
    assert r["status"] == STATUS_HOLD
    assert r["selected_action"] is None


def test_contradiction_never_creates_vacuous_license():
    s = demo()
    s["information_status"] = "CONTRADICTION"
    assert evaluate(s)["status"] == STATUS_CONTRADICTION


def test_model_invalidation_blocks_action():
    s = demo()
    s["model_invalidated"] = True
    assert evaluate(s)["status"] == STATUS_INVALIDATED


def test_actor_local_information_blocks_centralized_shortcut():
    s = demo()
    s["actions"][0]["requires_info"] = ["current_state", "remote_signal"]
    s["typed_reader"]["selected"] = "PREPARE"
    r = evaluate(rebind(s))
    assert r["status"] == STATUS_HOLD
    assert any(
        "ACTOR_LOCAL_INFO_MISSING" in x
        for x in r["rejected_actions"]["PREPARE"]
    )


def test_trace_requirement_breach_is_rejected():
    s = demo()
    s["trace_library"]["safe"][-1]["life_safe"] = False
    s["typed_reader"]["selected"] = "PREPARE"
    r = evaluate(rebind(s))
    assert r["status"] == STATUS_HOLD
    assert any(
        "REQUIREMENT_FAIL" in x
        for x in r["rejected_actions"]["PREPARE"]
    )


def test_multiple_viable_actions_without_reader_is_unresolved():
    s = demo()
    s.pop("typed_reader")
    s["trace_library"]["unsafe_late"][-1]["life_safe"] = True
    r = evaluate(rebind(s))
    assert r["status"] == STATUS_UNRESOLVED
    assert set(r["viable_actions"]) == {"PREPARE", "WAIT"}


def test_population_gap_is_local_partial():
    s = demo()
    s["envelope"]["protected_population"].append("visitor")
    r = evaluate(s)
    assert r["status"] == STATUS_LOCAL
    assert "PROTECTED_POPULATION_COVERAGE_GAP" in r["obstructions"][0]


def test_exact_fractional_resolution_is_supported():
    s = demo()
    s["question"]["horizon"] = "3/2"
    s["valid_until"] = "3/2"
    s["envelope"]["trace_resolution"] = "1/2"
    for key in list(s["trace_library"]):
        state = {"life_safe": key == "safe"}
        if key == "unsafe_late":
            s["trace_library"][key] = [
                {"life_safe": True},
                {"life_safe": True},
                {"life_safe": True},
                {"life_safe": False},
            ]
        else:
            s["trace_library"][key] = [
                {"life_safe": True},
                {"life_safe": True},
                {"life_safe": True},
                {"life_safe": True},
            ]
    r = evaluate(rebind(s))
    assert r["status"] == STATUS_LICENSED
