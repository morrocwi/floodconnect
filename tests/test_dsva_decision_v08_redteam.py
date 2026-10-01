"""Heavy adversarial regression for DSVA v0.8.

These are the failures found by the v0.7 red-team plus new IDM-informed
resolution / quotient / malformed-input checks.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from tests.dsva_v010_helpers import execution, rebind, req

from dsva_decision import STATUS_LICENSED, STATUS_HOLD, evaluate

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads(
        (ROOT / "examples" / "dsva_decision_minimal.json").read_text(
            encoding="utf-8"
        )
    )


def assert_not_licensed(s):
    try:
        rebind(s)
    except (TypeError, ValueError):
        # Malformed/non-finite snapshots must still fail closed in the kernel.
        pass
    r = evaluate(s)
    assert r["status"] != STATUS_LICENSED, r
    assert r["selected_action"] is None, r
    return r


def test_rt01_empty_disturbance_set_cannot_vacuously_license():
    s = demo()
    s["disturbances"] = []
    assert_not_licensed(s)


def test_rt02_action_outside_declared_actuation_envelope():
    s = demo()
    s["envelope"]["actuation_envelope"] = ["WAIT"]
    s["typed_reader"]["selected"] = "PREPARE"
    assert_not_licensed(s)


def test_rt03_declared_disturbance_envelope_must_equal_checked_set():
    s = demo()
    s["disturbances"] = ["base"]
    assert_not_licensed(s)


def test_rt04_trace_must_cover_declared_horizon_exactly():
    s = demo()
    s["question"]["horizon"] = 10
    s["valid_until"] = 10
    s["trace_library"]["safe"] = [{"life_safe": True}]
    assert_not_licensed(s)


def test_rt05_effect_after_question_horizon():
    s = demo()
    s["question"]["horizon"] = 1
    s["envelope"]["trace_resolution"] = 1
    s["valid_until"] = 3
    s["actions"][0]["lease"] = {"issue": 0, "expire": 3}
    s["actions"][0]["effect_time"] = 2
    s["trace_library"]["safe"] = [{"life_safe": True}, {"life_safe": True}]
    assert_not_licensed(s)


def test_rt06_global_valid_until_bounds_effect_time():
    s = demo()
    s["valid_until"] = "1/2"
    s["actions"][0]["effect_time"] = 1
    assert_not_licensed(s)


def test_rt07_unknown_information_status_fails_closed():
    s = demo()
    s["information_status"] = "CHANNEL_DOWN"
    assert_not_licensed(s)


def test_rt08_duplicate_action_ids_fail_closed():
    s = demo()
    s["actions"].append(copy.deepcopy(s["actions"][0]))
    assert_not_licensed(s)


def test_rt09_protected_population_gap_never_licenses():
    s = demo()
    s["envelope"]["protected_population"].append("visitor")
    assert_not_licensed(s)


def test_rt10_unsupported_requirement_operator_does_not_crash():
    s = demo()
    s["requirements"][0]["op"] = "approximately"
    r = assert_not_licensed(s)
    assert r["status"] == STATUS_HOLD


def test_rt11_requirement_type_mismatch_does_not_crash():
    s = demo()
    s["requirements"][0].update({"op": "ge", "value": 1})
    s["trace_library"]["safe"] = [
        {"life_safe": "unknown"},
        {"life_safe": "unknown"},
        {"life_safe": "unknown"},
    ]
    r = assert_not_licensed(s)
    assert r["status"] == STATUS_HOLD


def test_rt12_malformed_outcome_branch_does_not_crash():
    s = demo()
    s["actions"][0]["outcomes"]["normal"] = "not-a-mapping"
    r = assert_not_licensed(s)
    assert r["status"] == STATUS_HOLD


def test_model_invalidated_flag_must_be_boolean():
    s = demo()
    s["model_invalidated"] = 1
    assert_not_licensed(s)


def test_trace_semantics_and_resolution_are_explicit():
    s = demo()
    s["envelope"].pop("trace_resolution")
    assert_not_licensed(s)

    s = demo()
    s["envelope"].pop("trace_semantics")
    assert_not_licensed(s)


def test_off_grid_horizon_holds():
    s = demo()
    s["question"]["horizon"] = "3/2"
    s["valid_until"] = "3/2"
    s["envelope"]["trace_resolution"] = 1
    assert_not_licensed(s)


def test_mixed_or_nonmonotone_trace_times_hold():
    s = demo()
    s["trace_library"]["safe"] = [
        {"t": 0, "life_safe": True},
        {"life_safe": True},
        {"t": 2, "life_safe": True},
    ]
    assert_not_licensed(s)

    s = demo()
    s["trace_library"]["safe"] = [
        {"t": 0, "life_safe": True},
        {"t": 2, "life_safe": True},
        {"t": 1, "life_safe": True},
    ]
    assert_not_licensed(s)


def test_typed_reader_confidence_must_be_finite_probability():
    s = demo()
    s["typed_reader"]["confidence"] = 2
    assert_not_licensed(s)


def test_trace_ref_quotient_checks_all_branches_but_one_trace_class():
    s = demo()
    worlds = [f"w{i}" for i in range(128)]
    dists = [f"d{i}" for i in range(8)]
    H = 32
    reqs = 8

    s["question"]["horizon"] = H
    s["valid_until"] = H
    s["worlds"] = [{"id": w} for w in worlds]
    s["disturbances"] = dists
    s["envelope"]["disturbance_envelope"] = dists
    s["envelope"]["actuation_envelope"] = ["PREPARE"]
    s["requirements"] = [
        req(
            rid=f"R{i}",
            population=["community"],
            bindings={"community": f"r{i}"},
            field=f"r{i}",
            op="eq",
            value=1,
            horizon=H,
        )
        for i in range(reqs)
    ]
    state = {f"r{i}": 1 for i in range(reqs)}
    s["trace_library"] = {
        "safe": [dict(state) for _ in range(H + 1)]
    }
    s["actions"] = [
        {
            "id": "PREPARE",
            "actor": "incident_lead",
            "requires_info": ["current_state"],
            "lease": {"issue": 0, "expire": H},
            "effect_time": 0,
            "outcomes": {
                w: {d: {"trace_ref": "safe"} for d in dists}
                for w in worlds
            },
            "execution_contract": execution("PREPARE"),
        }
    ]
    s["typed_reader"]["selected"] = "PREPARE"

    r = evaluate(rebind(s))
    assert r["status"] == STATUS_LICENSED
    ledger = r["cost_ledger"]
    assert ledger["branches_checked"] == 128 * 8
    assert ledger["traces_checked"] == 1
    assert ledger["trace_cache_hits"] == (128 * 8) - 1
    assert ledger["predicates_checked"] == reqs
    # Naive predicate obligations would be 128*8*33*8 = 270,336.
    assert ledger["predicates_checked"] < (128 * 8 * (H + 1) * reqs)


def _mutate(s, i):
    kind = i % 16
    if kind == 0:
        s["disturbances"] = []
    elif kind == 1:
        s["information_status"] = "BROKEN"
    elif kind == 2:
        s["model_invalidated"] = "yes"
    elif kind == 3:
        s["closures"]["first_order"]["transition"] = 1
    elif kind == 4:
        s["closures"]["second_order"]["verification"] = None
    elif kind == 5:
        s["worlds"] = []
    elif kind == 6:
        s["envelope"]["actuation_envelope"] = []
    elif kind == 7:
        s["envelope"]["protected_population"].append("uncovered")
    elif kind == 8:
        s["requirements"][0]["op"] = "???"
    elif kind == 9:
        s["actions"][0]["lease"]["expire"] = -1
    elif kind == 10:
        s["actions"][0]["effect_time"] = 99
    elif kind == 11:
        s["actor_information"]["incident_lead"]["known"] = []
    elif kind == 12:
        s["trace_library"]["safe"] = []
    elif kind == 13:
        s["trace_library"]["safe"][-1]["life_safe"] = False
    elif kind == 14:
        s["envelope"]["trace_resolution"] = 0
    else:
        s["typed_reader"]["confidence"] = float("nan")
    return s


def test_10000_single_fault_mutations_never_license_or_raise():
    for i in range(10_000):
        r = evaluate(_mutate(demo(), i))
        assert r["status"] != STATUS_LICENSED, (i, r)
        assert r["selected_action"] is None, (i, r)
