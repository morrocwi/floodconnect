"""Theory-gap red-team for DSVA v0.9.

These probes attack obligations that already exist in DSVA theory but are not
yet load-bearing in the v0.9 executable projection.  This PR is intentionally
test-only and should remain unmerged while failures exist.
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


def test_tg01_verification_must_be_bound_to_actual_spec_and_input():
    s = demo()
    s["verification_contract"] = {
        "producer": {"id": "solver-A", "implementation_digest": "impl-A", "lineage": ["team-A"]},
        "checker": {"id": "checker-B", "implementation_digest": "impl-B", "lineage": ["team-B"]},
        "spec_digest": "deadbeef",
        "input_digest": "cafebabe",
        "certificate": {"kind": "finite-constraint-recheck", "witness": "demo"}
    }
    assert_not_licensed(s)


def test_tg02_checker_with_same_failure_lineage_is_not_independent():
    s = demo()
    s["verification_contract"] = {
        "producer": {
            "id": "solver-A",
            "implementation_digest": "same-code",
            "lineage": ["vendor-X", "library-Y"],
        },
        "checker": {
            "id": "checker-A2",
            "implementation_digest": "same-code",
            "lineage": ["vendor-X", "library-Y"],
        },
        "spec_digest": "AUTO",
        "input_digest": "AUTO",
        "certificate": {"kind": "finite-constraint-recheck", "witness": "demo"}
    }
    assert_not_licensed(s)


def test_tg03_disjoint_model_and_observed_behavior_invalidates_applicability():
    s = demo()
    s["model_invalidated"] = False
    s["applicability_evidence"] = {
        "model_behavior_signatures": ["dry-compatible"],
        "observed_behavior_signatures": ["wet-incompatible"],
        "reader": "Q-DEMO-001",
    }
    assert_not_licensed(s)


def test_tg04_common_calibration_ancestor_breaks_independence_claim():
    s = demo()
    s["dependency_audit"] = {
        "lineage": {
            "sensor-1": ["calibration-C", "feed-A"],
            "sensor-2": ["calibration-C", "feed-B"],
        },
        "independence_groups": [["sensor-1", "sensor-2"]]
    }
    assert_not_licensed(s)


def test_tg05_requirement_horizon_and_coverage_status_must_cover_claim():
    s = demo()
    req = s["requirements"][0]
    req.update({
        "function": "preserve life safety",
        "constraint": "life_safe == true",
        "threshold": True,
        "horizon": 1,
        "provenance": ["human-safety-ledger-demo"],
        "coverageStatus": "COVERED",
    })
    # Q horizon is 2.  A one-step protected-requirement warrant cannot license
    # a two-step human-safety claim.
    assert_not_licensed(s)


def test_tg06_future_observation_policy_must_be_total_over_admitted_failures():
    s = demo()
    s["actions"][0]["future_observation_contract"] = {
        "channel": "future_sensor",
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
        "responses": {
            "VALUE": "CONTINUE"
        }
    }
    assert_not_licensed(s)
