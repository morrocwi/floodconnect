"""Adversarial tests for the DSVA v0.7 executable decision model.

These tests intentionally assert fail-closed behavior implied by the v0.7
standalone/model documentation. They increase coverage only; they do not change
model semantics. Failures are evidence for the red-team report and this PR is
not intended to merge while failures remain.
"""
import copy

import pytest

from dsva_decision import STATUS_HOLD, STATUS_LICENSED, evaluate


def base():
    return {
        "question": {"id": "Q-RT", "task": "red-team", "horizon": 2},
        "envelope": {
            "domain": "synthetic",
            "protected_population": ["A"],
            "disturbance_envelope": ["base"],
            "actuation_envelope": ["SAFE"],
        },
        "information_status": "SUPPORTED",
        "model_invalidated": False,
        "closures": {
            "first_order": {
                "information": True,
                "evidence": True,
                "state": True,
                "transition": True,
                "boundary": True,
                "capacity": True,
                "recovery": True,
            },
            "second_order": {
                "applicability": True,
                "dependency": True,
                "realizability": True,
                "execution": True,
                "requirement": True,
                "verification": True,
            },
        },
        "worlds": [{"id": "w"}],
        "disturbances": ["base"],
        "requirements": [
            {"id": "R", "field": "safe", "op": "eq", "value": True}
        ],
        "actor_information": {"lead": {"known": ["now"]}},
        "actions": [
            {
                "id": "SAFE",
                "actor": "lead",
                "requires_info": ["now"],
                "lease": {"issue": 0, "expire": 2},
                "effect_time": 0,
                "outcomes": {
                    "w": {
                        "base": {
                            "trace": [
                                {"safe": True},
                                {"safe": True},
                                {"safe": True},
                            ]
                        }
                    }
                },
            }
        ],
        "proposed_action": "SAFE",
        "valid_until": 2,
        "provenance": ["synthetic red-team"],
    }


def assert_not_licensed(s):
    r = evaluate(s)
    assert r["status"] != STATUS_LICENSED, r
    assert r["selected_action"] is None, r


def test_empty_disturbance_set_must_not_vacuously_license():
    s = base()
    s["disturbances"] = []
    assert_not_licensed(s)


def test_action_outside_declared_actuation_envelope_must_not_license():
    s = base()
    s["envelope"]["actuation_envelope"] = ["WAIT"]
    assert_not_licensed(s)


def test_declared_disturbance_envelope_must_be_covered():
    s = base()
    s["envelope"]["disturbance_envelope"] = ["base", "degraded"]
    # The executable only evaluates 'base'; the declared 'degraded' branch is absent.
    assert_not_licensed(s)


def test_trace_must_cover_declared_horizon():
    s = base()
    s["question"]["horizon"] = 10
    s["actions"][0]["outcomes"]["w"]["base"]["trace"] = [{"safe": True}]
    assert_not_licensed(s)


def test_action_effect_after_question_horizon_must_not_license():
    s = base()
    s["question"]["horizon"] = 1
    s["actions"][0]["lease"] = {"issue": 0, "expire": 3}
    s["actions"][0]["effect_time"] = 2
    assert_not_licensed(s)


def test_global_valid_until_must_bound_effect_time():
    s = base()
    s["valid_until"] = 0.5
    s["actions"][0]["lease"] = {"issue": 0, "expire": 2}
    s["actions"][0]["effect_time"] = 1
    assert_not_licensed(s)


def test_unknown_information_status_must_fail_closed():
    s = base()
    s["information_status"] = "CHANNEL_DOWN"
    assert_not_licensed(s)


def test_duplicate_action_ids_must_not_create_ambiguous_license():
    s = base()
    s.pop("proposed_action")
    s["actions"].append(copy.deepcopy(s["actions"][0]))
    r = evaluate(s)
    assert r["status"] == STATUS_HOLD, r
    assert r["selected_action"] is None, r


def test_requirement_population_must_cover_declared_population():
    s = base()
    s["envelope"]["protected_population"] = ["A", "B"]
    s["requirements"] = [
        {"id": "R-A", "field": "A_safe", "op": "eq", "value": True}
    ]
    s["actions"][0]["outcomes"]["w"]["base"]["trace"] = [
        {"A_safe": True, "B_safe": False},
        {"A_safe": True, "B_safe": False},
        {"A_safe": True, "B_safe": False},
    ]
    assert_not_licensed(s)


def test_unsupported_requirement_operator_must_fail_closed_not_crash():
    s = base()
    s["requirements"][0]["op"] = "approximately"
    try:
        r = evaluate(s)
    except Exception as exc:  # availability itself is part of the decision contract
        pytest.fail(f"evaluator crashed instead of failing closed: {exc!r}")
    assert r["status"] == STATUS_HOLD, r


def test_requirement_type_mismatch_must_fail_closed_not_crash():
    s = base()
    s["requirements"] = [
        {"id": "R", "field": "safe", "op": "ge", "value": 1}
    ]
    s["actions"][0]["outcomes"]["w"]["base"]["trace"] = [
        {"safe": "unknown"}
    ]
    try:
        r = evaluate(s)
    except Exception as exc:
        pytest.fail(f"evaluator crashed instead of failing closed: {exc!r}")
    assert r["status"] == STATUS_HOLD, r


def test_malformed_outcome_branch_must_fail_closed_not_crash():
    s = base()
    s["actions"][0]["outcomes"]["w"] = "not-a-mapping"
    try:
        r = evaluate(s)
    except Exception as exc:
        pytest.fail(f"evaluator crashed instead of failing closed: {exc!r}")
    assert r["status"] == STATUS_HOLD, r
