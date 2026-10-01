import json
from pathlib import Path

from dsva_decision import (
    STATUS_CONTRADICTION,
    STATUS_HOLD,
    STATUS_INVALIDATED,
    STATUS_LICENSED,
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


def test_first_order_gap_holds():
    s = demo()
    s["closures"]["first_order"]["transition"] = False
    r = evaluate(s)
    assert r["status"] == STATUS_HOLD
    assert r["selected_action"] is None


def test_contradiction_never_creates_vacuous_license():
    s = demo()
    s["information_status"] = "CONTRADICTION"
    r = evaluate(s)
    assert r["status"] == STATUS_CONTRADICTION


def test_model_invalidation_blocks_action():
    s = demo()
    s["model_invalidated"] = True
    r = evaluate(s)
    assert r["status"] == STATUS_INVALIDATED


def test_actor_local_information_blocks_centralized_shortcut():
    s = demo()
    s["actions"][0]["requires_info"] = ["current_state", "remote_signal"]
    s["typed_reader"]["selected"] = "PREPARE"
    r = evaluate(s)
    assert r["status"] == STATUS_HOLD
    assert any(
        "ACTOR_LOCAL_INFO_MISSING" in x
        for x in r["rejected_actions"]["PREPARE"]
    )


def test_trace_safety_rejects_intersample_breach():
    s = demo()
    trace = s["actions"][0]["outcomes"]["normal"]["base"]["trace"]
    trace[:] = [
        {"life_safe": True},
        {"life_safe": False},
        {"life_safe": True},
    ]
    s["typed_reader"]["selected"] = "PREPARE"
    r = evaluate(s)
    assert r["status"] == STATUS_HOLD
    assert any(
        "TRACE_REQUIREMENT_FAIL" in x
        for x in r["rejected_actions"]["PREPARE"]
    )


def test_multiple_viable_actions_without_reader_is_unresolved():
    s = demo()
    s.pop("typed_reader")
    s["actions"][1]["outcomes"]["fragile"]["degraded"]["trace"][-1][
        "life_safe"
    ] = True
    r = evaluate(s)
    assert r["status"] == STATUS_UNRESOLVED
    assert set(r["viable_actions"]) == {"PREPARE", "WAIT"}
