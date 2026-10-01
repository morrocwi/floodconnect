"""Higher-order adversarial probes for DSVA v0.8.

Expected to remain unmerged while failures exist. These tests attack the
meaning-preservation boundary *after* the v0.8 finite obstruction gates pass.
"""
import copy
import json
from pathlib import Path

from dsva_decision import STATUS_LICENSED, evaluate

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


def test_ho01_numeric_bool_cache_alias_must_not_license():
    """Python True == 1 must not collapse numeric and Boolean retained states."""
    s = demo()
    s["requirements"] = [{
        "id": "R-NUM",
        "population": ["community"],
        "field": "level",
        "op": "ge",
        "value": 1
    }]
    s["trace_library"] = {
        "mixed": [
            {"level": 1},
            {"level": True},
            {"level": 1}
        ],
        "unsafe_late": [
            {"level": 1},
            {"level": 1},
            {"level": 0}
        ]
    }
    for world_out in s["actions"][0]["outcomes"].values():
        for item in world_out.values():
            item["trace_ref"] = "mixed"
    s["typed_reader"]["selected"] = "PREPARE"
    assert_not_licensed(s)


def test_ho02_action_effect_in_past_must_not_license():
    s = demo()
    s["actions"][0]["lease"] = {"issue": -2, "expire": 2}
    s["actions"][0]["effect_time"] = -1
    s["typed_reader"]["selected"] = "PREPARE"
    assert_not_licensed(s)


def test_ho03_conflicting_reader_and_proposed_action_must_not_silently_choose_one():
    s = demo()
    # Make both actions viable so the conflict cannot be hidden by a hard-safety rejection.
    s["trace_library"]["unsafe_late"] = copy.deepcopy(s["trace_library"]["safe"])
    s["typed_reader"]["selected"] = "WAIT"
    s["proposed_action"] = "PREPARE"
    assert_not_licensed(s)


def test_ho04_population_label_cannot_substitute_for_subject_binding():
    """Coverage metadata alone must not claim B is protected by a predicate that reads only A."""
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
    for action in s["actions"]:
        for world_out in action["outcomes"].values():
            for item in world_out.values():
                item["trace_ref"] = "safe"
    s["typed_reader"]["selected"] = "PREPARE"
    assert_not_licensed(s)


def test_ho05_true_closure_flags_without_audit_witness_must_not_be_a_strong_license():
    """A caller-written True is not itself a closure proof/certificate."""
    s = demo()
    s.pop("closure_certificates", None)
    assert_not_licensed(s)
