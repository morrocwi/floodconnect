"""DSVA v0.10 theory-contract regression.

Closes the v0.9 theory-gap failures preserved in draft PR #42.
"""
import copy
import json
from pathlib import Path

from dsva_decision import STATUS_HOLD, STATUS_INVALIDATED, STATUS_LICENSED, evaluate
from tests.dsva_v010_helpers import rebind

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads(
        (ROOT / "examples" / "dsva_decision_minimal.json").read_text(encoding="utf-8")
    )


def test_tc01_verification_is_bound_to_actual_spec_and_input():
    s = demo()
    s["verification_contract"]["spec_digest"] = "0" * 64
    out = evaluate(s)
    assert out["status"] == STATUS_HOLD
    assert "VERIFICATION_SPEC_BINDING_MISMATCH" in out["obstructions"][0]


def test_tc02_checker_must_be_declared_independent():
    s = demo()
    s["verification_contract"]["checker"]["implementation_digest"] = (
        s["verification_contract"]["producer"]["implementation_digest"]
    )
    s["verification_contract"]["checker"]["lineage"] = copy.deepcopy(
        s["verification_contract"]["producer"]["lineage"]
    )
    out = evaluate(s)
    assert out["status"] == STATUS_HOLD
    assert "VERIFIER_NOT_INDEPENDENT" in out["obstructions"][0]


def test_tc03_disjoint_model_and_observed_behavior_invalidates():
    s = demo()
    s["applicability_evidence"]["model_behavior_signatures"] = ["dry-compatible"]
    s["applicability_evidence"]["observed_behavior_signatures"] = ["wet-incompatible"]
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_INVALIDATED
    assert "MODEL_FAMILY_INVALIDATED_BY_BEHAVIOR" in out["obstructions"][0]


def test_tc04_common_lineage_breaks_independence_claim():
    s = demo()
    s["dependency_audit"] = {
        "lineage": {
            "sensor-1": ["calibration-C", "feed-A"],
            "sensor-2": ["calibration-C", "feed-B"],
        },
        "independence_groups": [["sensor-1", "sensor-2"]],
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_HOLD
    assert "DEPENDENCY_INDEPENDENCE_VIOLATION" in out["obstructions"][0]


def test_tc05_requirement_horizon_must_cover_question_horizon():
    s = demo()
    s["requirements"][0]["horizon"] = 1
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_HOLD
    assert "REQUIREMENT_HORIZON_TOO_SHORT" in out["obstructions"][0]


def test_tc06_future_observation_policy_is_total_over_admitted_outcomes():
    s = demo()
    s["envelope"]["observation_envelope"].append("future_sensor")
    s["actions"][0]["future_observation_contract"] = {
        "channel": "future_sensor",
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
        "responses": {"VALUE": "CONTINUE"},
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_HOLD
    assert any(
        "FUTURE_OBSERVATION_POLICY_NOT_TOTAL" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_tc07_global_resource_overbooking_rejects_action():
    s = demo()
    s["resource_audit"] = {
        "declared_none": False,
        "resources": {"pump_crew": {"available": 1}},
        "action_use": {"PREPARE": {"pump_crew": 2}, "WAIT": {}},
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_HOLD
    assert any("RESOURCE_OVERBOOKED" in x for x in out["rejected_actions"]["PREPARE"])


def test_tc08_compound_hazard_factorization_needs_license():
    s = demo()
    s["hazard_dependency_audit"] = {
        "components": ["rain", "tide"],
        "factorized": True,
        "factorization_licensed": False,
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_HOLD
    assert "COMPOUND_HAZARD_FACTORIZATION_UNLICENSED" in out["obstructions"][0]


def test_tc09_commanded_is_not_realized_without_verification_or_bound():
    s = demo()
    s["actions"][0]["execution_contract"] = {
        "commanded": "PREPARE",
        "realized_status": "UNVERIFIED",
        "runtime_revalidation_required": True,
        "runtime_revalidation_status": "MISSING",
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_HOLD
    assert any("REALIZED_ACTUATION_UNVERIFIED" in x for x in out["rejected_actions"]["PREPARE"])


def test_valid_bound_verification_metadata_is_returned():
    out = evaluate(demo())
    assert out["status"] == STATUS_LICENSED
    vb = out["verification_binding"]
    assert len(vb["spec_digest"]) == 64
    assert len(vb["input_digest"]) == 64
    assert len(vb["certificate_digest"]) == 64
    assert vb["producer"] != vb["checker"]


def test_complete_future_observation_policy_can_license():
    s = demo()
    s["envelope"]["observation_envelope"].append("future_sensor")
    s["actions"][0]["future_observation_contract"] = {
        "channel": "future_sensor",
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN", "STALE", "CONTRADICTION"],
        "responses": {
            "VALUE": "CONTINUE",
            "CHANNEL_DOWN": "HOLD",
            "STALE": "HOLD",
            "CONTRADICTION": "HOLD",
        },
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_LICENSED


def test_exact_resource_use_at_capacity_can_license():
    s = demo()
    s["resource_audit"] = {
        "declared_none": False,
        "resources": {"crew": {"available": "3/2"}},
        "action_use": {"PREPARE": {"crew": 1.5}, "WAIT": {}},
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_LICENSED


def test_licensed_compound_factorization_can_pass_dependency_gate():
    s = demo()
    s["hazard_dependency_audit"] = {
        "components": ["rain", "tide"],
        "factorized": True,
        "factorization_licensed": True,
    }
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_LICENSED


def test_10000_theory_contract_mutations_fail_closed():
    for i in range(10_000):
        s = demo()
        k = i % 9
        if k == 0:
            s["verification_contract"]["spec_digest"] = "f" * 64
            out = evaluate(s)
        elif k == 1:
            s["verification_contract"]["checker"]["lineage"] = copy.deepcopy(
                s["verification_contract"]["producer"]["lineage"]
            )
            out = evaluate(s)
        elif k == 2:
            s["applicability_evidence"]["observed_behavior_signatures"] = ["incompatible"]
            out = evaluate(rebind(s))
        elif k == 3:
            s["dependency_audit"] = {
                "lineage": {"a": ["root"], "b": ["root"]},
                "independence_groups": [["a", "b"]],
            }
            out = evaluate(rebind(s))
        elif k == 4:
            s["requirements"][0]["coverageStatus"] = "UNKNOWN"
            out = evaluate(rebind(s))
        elif k == 5:
            s["envelope"]["observation_envelope"].append("future")
            s["actions"][0]["future_observation_contract"] = {
                "channel": "future",
                "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
                "responses": {"VALUE": "CONTINUE"},
            }
            out = evaluate(rebind(s))
        elif k == 6:
            s["resource_audit"] = {
                "declared_none": False,
                "resources": {"r": {"available": 1}},
                "action_use": {"PREPARE": {"r": 2}},
            }
            out = evaluate(rebind(s))
        elif k == 7:
            s["hazard_dependency_audit"] = {
                "components": ["a", "b"],
                "factorized": True,
                "factorization_licensed": False,
            }
            out = evaluate(rebind(s))
        else:
            s["actions"][0]["execution_contract"]["realized_status"] = "UNVERIFIED"
            out = evaluate(rebind(s))

        assert out["status"] != STATUS_LICENSED, (i, out)
        assert out["selected_action"] is None, (i, out)
