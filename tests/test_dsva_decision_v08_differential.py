"""Random differential test: optimized DSVA kernel vs a direct finite oracle."""
import random

from dsva_decision import STATUS_HOLD, STATUS_LICENSED, evaluate


def closure_audit():
    first = ["information", "evidence", "state", "transition", "boundary", "capacity", "recovery"]
    second = ["applicability", "dependency", "realizability", "execution", "requirement", "verification"]
    def cert(name):
        return {
            "spec": f"test:{name}",
            "input": "locked differential fixture",
            "witness": f"witness:{name}",
            "checker": "direct-test-oracle",
        }
    return {
        "first_order": {name: cert(name) for name in first},
        "second_order": {name: cert(name) for name in second},
    }


def case(seed):
    rng = random.Random(seed)
    W, D, H, R = rng.randint(1, 4), rng.randint(1, 3), rng.randint(1, 4), rng.randint(1, 4)
    worlds = [f"w{i}" for i in range(W)]
    dists = [f"d{i}" for i in range(D)]
    reqs = [
        {"id": f"R{i}", "population": ["P"], "field": f"r{i}", "bindings": {"P": f"r{i}"}, "op": "eq", "value": 1}
        for i in range(R)
    ]
    good = {f"r{i}": 1 for i in range(R)}
    bad = dict(good)
    bad[f"r{rng.randrange(R)}"] = 0
    traces = {
        "good": [dict(good) for _ in range(H + 1)],
        "bad": [dict(good) for _ in range(H + 1)],
    }
    traces["bad"][rng.randrange(H + 1)] = bad
    outcomes = {}
    expected = True
    for w in worlds:
        outcomes[w] = {}
        for d in dists:
            ref = "good" if rng.random() < 0.8 else "bad"
            outcomes[w][d] = {"trace_ref": ref}
            expected = expected and ref == "good"

    s = {
        "question": {"id": f"Q{seed}", "task": "differential", "horizon": H},
        "envelope": {
            "protected_population": ["P"],
            "disturbance_envelope": dists,
            "actuation_envelope": ["A"],
            "trace_semantics": "discrete_retained",
            "trace_resolution": 1
        },
        "information_status": "SUPPORTED",
        "model_invalidated": False,
        "closures": {
            "first_order": {
                "information": True, "evidence": True, "state": True,
                "transition": True, "boundary": True, "capacity": True, "recovery": True
            },
            "second_order": {
                "applicability": True, "dependency": True, "realizability": True,
                "execution": True, "requirement": True, "verification": True
            }
        },
        "closure_audit": closure_audit(),
        "worlds": [{"id": w} for w in worlds],
        "disturbances": dists,
        "requirements": reqs,
        "actor_information": {"actor": {"known": ["now"]}},
        "trace_library": traces,
        "actions": [{
            "id": "A", "actor": "actor", "requires_info": ["now"],
            "lease": {"issue": 0, "expire": H}, "effect_time": 0,
            "outcomes": outcomes
        }],
        "proposed_action": "A",
        "valid_until": H
    }
    return s, expected


def direct_oracle(s):
    action = s["actions"][0]
    for w in [x["id"] for x in s["worlds"]]:
        for d in s["disturbances"]:
            trace = s["trace_library"][action["outcomes"][w][d]["trace_ref"]]
            if len(trace) != s["question"]["horizon"] + 1:
                return False
            for state in trace:
                for req in s["requirements"]:
                    field = req["bindings"]["P"]
                    if state[field] != req["value"]:
                        return False
    return True


def test_5000_random_cases_match_direct_oracle():
    for seed in range(5000):
        s, expected = case(seed)
        assert direct_oracle(s) == expected
        out = evaluate(s)
        if expected:
            assert out["status"] == STATUS_LICENSED, (seed, out)
            assert out["selected_action"] == "A"
        else:
            assert out["status"] == STATUS_HOLD, (seed, out)
            assert out["selected_action"] is None
