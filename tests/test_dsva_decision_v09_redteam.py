"""Higher-order regression for DSVA v0.9 audited meaning closure."""
import copy
import json
from pathlib import Path

from dsva_decision import STATUS_HOLD, STATUS_LICENSED, evaluate

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads(
        (ROOT / "examples" / "dsva_decision_minimal.json").read_text(encoding="utf-8")
    )


def assert_not_licensed(s):
    out = evaluate(s)
    assert out["status"] != STATUS_LICENSED, out
    assert out["selected_action"] is None, out
    return out


def test_ho01_numeric_bool_cache_alias_closed():
    s = demo()
    s["requirements"] = [{
        "id": "R-NUM",
        "population": ["community"],
        "bindings": {"community": "level"},
        "field": "level",
        "op": "ge",
        "value": 1
    }]
    s["trace_library"] = {
        "mixed": [{"level": 1}, {"level": True}, {"level": 1}],
        "unsafe_late": [{"level": 1}, {"level": 1}, {"level": 0}]
    }
    for world_out in s["actions"][0]["outcomes"].values():
        for item in world_out.values():
            item["trace_ref"] = "mixed"
    s["typed_reader"]["selected"] = "PREPARE"
    out = assert_not_licensed(s)
    assert any("REQUIREMENT_FAIL" in x for x in out["rejected_actions"]["PREPARE"])


def test_ho02_action_effect_in_past_closed():
    s = demo()
    s["actions"][0]["lease"] = {"issue": -2, "expire": 2}
    s["actions"][0]["effect_time"] = -1
    out = assert_not_licensed(s)
    assert any("EFFECT_BEFORE_DECISION_ORIGIN" in x for x in out["rejected_actions"]["PREPARE"])


def test_ho03_reader_proposal_conflict_closed():
    s = demo()
    s["trace_library"]["unsafe_late"] = copy.deepcopy(s["trace_library"]["safe"])
    s["typed_reader"]["selected"] = "WAIT"
    s["proposed_action"] = "PREPARE"
    out = assert_not_licensed(s)
    assert "READER_PROPOSAL_CONFLICT" in out["obstructions"]


def test_ho04_population_label_without_subject_binding_closed():
    s = demo()
    s["envelope"]["protected_population"] = ["A", "B"]
    s["requirements"] = [{
        "id": "R-BOTH",
        "population": ["A", "B"],
        "field": "A_safe",
        "op": "eq",
        "value": True
    }]
    s["trace_library"] = {
        "safe": [
            {"A_safe": True, "B_safe": False},
            {"A_safe": True, "B_safe": False},
            {"A_safe": True, "B_safe": False}
        ],
        "unsafe_late": [
            {"A_safe": True, "B_safe": False},
            {"A_safe": True, "B_safe": False},
            {"A_safe": True, "B_safe": False}
        ]
    }
    out = assert_not_licensed(s)
    assert "REQUIREMENT_BINDING_INVALID" in out["obstructions"][0]


def test_ho05_bare_closure_flags_without_audit_closed():
    s = demo()
    s.pop("closure_audit")
    out = assert_not_licensed(s)
    assert "CLOSURE_AUDIT_MISSING" in out["obstructions"][0]


def test_complete_multi_subject_binding_checks_every_subject():
    s = demo()
    s["envelope"]["protected_population"] = ["A", "B"]
    s["requirements"] = [{
        "id": "R-BOTH",
        "population": ["A", "B"],
        "bindings": {"A": "A_safe", "B": "B_safe"},
        "op": "eq",
        "value": True
    }]
    s["trace_library"]["safe"] = [
        {"A_safe": True, "B_safe": True},
        {"A_safe": True, "B_safe": True},
        {"A_safe": True, "B_safe": True}
    ]
    s["trace_library"]["unsafe_late"] = [
        {"A_safe": True, "B_safe": True},
        {"A_safe": True, "B_safe": True},
        {"A_safe": True, "B_safe": False}
    ]
    out = evaluate(s)
    assert out["status"] == STATUS_LICENSED
    assert out["selected_action"] == "PREPARE"


def test_duplicate_subject_fields_rejected_for_strong_per_subject_path():
    s = demo()
    s["envelope"]["protected_population"] = ["A", "B"]
    s["requirements"] = [{
        "id": "R-BOTH",
        "population": ["A", "B"],
        "bindings": {"A": "shared", "B": "shared"},
        "op": "eq",
        "value": True
    }]
    out = assert_not_licensed(s)
    assert "REQUIREMENT_BINDING_INVALID" in out["obstructions"][0]


def test_closure_audit_requires_all_four_fields():
    for field in ["spec", "input", "witness", "checker"]:
        s = demo()
        del s["closure_audit"]["first_order"]["state"][field]
        out = assert_not_licensed(s)
        assert "CLOSURE_AUDIT" in out["obstructions"][0]


def test_closure_audit_digest_deterministic():
    s = demo()
    a = evaluate(s)
    b = evaluate(copy.deepcopy(s))
    assert a["status"] == STATUS_LICENSED
    assert a["closure_audit_digest"] == b["closure_audit_digest"]
    assert len(a["closure_audit_digest"]) == 64


def test_typed_equality_distinguishes_boolean_and_number():
    s = demo()
    s["requirements"] = [{
        "id": "R-BOOL",
        "population": ["community"],
        "bindings": {"community": "flag"},
        "op": "eq",
        "value": True
    }]
    s["trace_library"]["safe"] = [{"flag": 1}, {"flag": 1}, {"flag": 1}]
    out = assert_not_licensed(s)
    assert any("REQUIREMENT_FAIL" in x for x in out["rejected_actions"]["PREPARE"])


def test_10000_typed_alias_and_audit_mutations_fail_closed():
    for i in range(10_000):
        s = demo()
        k = i % 5
        if k == 0:
            s["actions"][0]["effect_time"] = -1
            s["actions"][0]["lease"]["issue"] = -2
        elif k == 1:
            s["proposed_action"] = "WAIT"
            s["typed_reader"]["selected"] = "PREPARE"
        elif k == 2:
            del s["closure_audit"]["second_order"]["verification"]["witness"]
        elif k == 3:
            s["envelope"]["protected_population"] = ["A", "B"]
            s["requirements"] = [{
                "id": "R",
                "population": ["A", "B"],
                "field": "A_safe",
                "op": "eq",
                "value": True
            }]
        else:
            s["requirements"] = [{
                "id": "R",
                "population": ["community"],
                "bindings": {"community": "x"},
                "op": "ge",
                "value": 1
            }]
            s["trace_library"]["safe"] = [{"x": 1}, {"x": True}, {"x": 1}]
        assert_not_licensed(s)
