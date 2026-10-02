"""DSVA v0.11 finite realizability regression.

Closes the seven SOL-20..28 executable failures preserved in draft PR #46.
"""
import json
from pathlib import Path

from dsva_decision import STATUS_HOLD, STATUS_LICENSED, evaluate
from tests.dsva_v010_helpers import rebind

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads(
        (ROOT / "examples" / "dsva_decision_minimal.json").read_text(encoding="utf-8")
    )


def assert_not_licensed(s):
    out = evaluate(rebind(s))
    assert out["status"] != STATUS_LICENSED, out
    assert out["selected_action"] is None, out
    return out


def valid_policy():
    return {
        "root": "n0",
        "nodes": {
            "n0": {
                "time": 0,
                "actor": "incident_lead",
                "action": "PREPARE",
                "observe": {
                    "channel": "future_sensor",
                    "time": 1,
                    "delivered_to": ["incident_lead"],
                    "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
                    "outcomes": {
                        "VALUE": "n1",
                        "CHANNEL_DOWN": "n2",
                    },
                },
            },
            "n1": {
                "time": 1,
                "actor": "incident_lead",
                "action": "PREPARE",
                "requires_info": ["future_sensor"],
                "terminal": True,
            },
            "n2": {
                "time": 1,
                "actor": "incident_lead",
                "action": "WAIT",
                "terminal": True,
            },
        },
    }


def attach_valid_future_policy(s):
    s["envelope"]["observation_envelope"].append("future_sensor")
    s["actions"][0]["future_observation_contract"] = {
        "channel": "future_sensor",
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
        "responses": {
            "VALUE": "n1",
            "CHANNEL_DOWN": "n2",
        },
    }
    s["adaptive_policy"] = valid_policy()
    return s


def test_rz01_future_response_tokens_bind_to_real_policy_nodes():
    s = demo()
    s["envelope"]["observation_envelope"].append("future_sensor")
    s["actions"][0]["future_observation_contract"] = {
        "channel": "future_sensor",
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
        "responses": {
            "VALUE": "MAGIC_NODE",
            "CHANNEL_DOWN": "ANOTHER_MAGIC_NODE",
        },
    }
    out = assert_not_licensed(s)
    assert any("ADAPTIVE_POLICY_MISSING" in x for x in out["rejected_actions"]["PREPARE"])


def test_rz02_future_policy_action_stays_inside_actuation_envelope():
    s = attach_valid_future_policy(demo())
    s["adaptive_policy"]["nodes"]["n1"]["action"] = "FLY"
    out = assert_not_licensed(s)
    assert any(
        "ADAPTIVE_POLICY_ACTION_OUTSIDE_ENVELOPE" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_rz03_future_actor_uses_only_delivered_information():
    s = attach_valid_future_policy(demo())
    s["adaptive_policy"]["nodes"]["n0"]["observe"]["delivered_to"] = ["incident_lead"]
    s["adaptive_policy"]["nodes"]["n1"]["actor"] = "incident_lead"
    # Remove delivery to the actual future actor while preserving a valid known actor.
    s["actor_information"]["sensor_operator"] = {"known": ["current_state"]}
    s["adaptive_policy"]["nodes"]["n0"]["observe"]["delivered_to"] = ["sensor_operator"]
    out = assert_not_licensed(s)
    assert any(
        "ADAPTIVE_POLICY_ACTOR_LOCAL_INFO_MISSING" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_rz04_future_observation_cannot_be_used_before_arrival():
    s = attach_valid_future_policy(demo())
    s["adaptive_policy"]["nodes"]["n0"]["observe"]["time"] = 2
    s["adaptive_policy"]["nodes"]["n1"]["time"] = 1
    s["adaptive_policy"]["nodes"]["n2"]["time"] = 1
    out = assert_not_licensed(s)
    assert any(
        "ADAPTIVE_POLICY_ANTI_HINDSIGHT_VIOLATION" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_rz05_load_bearing_contract_realizable_on_every_branch():
    s = demo()
    s["boundary_contracts"] = [{
        "id": "power-pump",
        "used_by": ["PREPARE"],
        "invoke_time": 1,
        "branches": {
            "normal": {
                "base": {"assumption": True, "guarantee": True},
                "degraded": {"assumption": True, "guarantee": True},
            },
            "fragile": {
                "base": {"assumption": True, "guarantee": True},
                "degraded": {"assumption": False, "guarantee": True},
            },
        },
    }]
    out = assert_not_licensed(s)
    assert any(
        "BOUNDARY_CONTRACT_ASSUMPTION_UNREALIZABLE" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_rz06_recovery_persists_not_only_touches_return_set():
    s = demo()
    s["recovery_contract"] = {
        "required": True,
        "field": "recovered",
        "value": True,
        "return_time": 1,
        "persistence_horizon": 1,
    }
    s["trace_library"]["safe"] = [
        {"life_safe": True, "recovered": False},
        {"life_safe": True, "recovered": True},
        {"life_safe": True, "recovered": False},
    ]
    out = assert_not_licensed(s)
    assert any(
        "RECOVERY_NOT_PERSISTENT_AT" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_rz07_policy_graph_is_finite_acyclic_and_forward_time():
    s = attach_valid_future_policy(demo())
    s["adaptive_policy"]["nodes"]["n1"].pop("terminal")
    s["adaptive_policy"]["nodes"]["n1"]["observe"] = {
        "channel": "future_sensor",
        "time": 1,
        "delivered_to": ["incident_lead"],
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
        "outcomes": {"VALUE": "n0", "CHANNEL_DOWN": "n0"},
    }
    out = assert_not_licensed(s)
    assert any(
        "ADAPTIVE_POLICY_OBSERVATION_TIME_INVALID" in x
        or "ADAPTIVE_POLICY_CYCLE" in x
        for x in out["rejected_actions"]["PREPARE"]
    )


def test_valid_finite_adaptive_policy_can_license():
    s = attach_valid_future_policy(demo())
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_LICENSED
    assert out["selected_action"] == "PREPARE"


def test_valid_load_bearing_boundary_contract_can_license():
    s = demo()
    s["boundary_contracts"] = [{
        "id": "power-pump",
        "used_by": ["PREPARE"],
        "invoke_time": 1,
        "branches": {
            world: {
                dist: {"assumption": True, "guarantee": True}
                for dist in s["disturbances"]
            }
            for world in [w["id"] for w in s["worlds"]]
        },
    }]
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_LICENSED


def test_valid_persistent_recovery_can_license():
    s = demo()
    s["recovery_contract"] = {
        "required": True,
        "field": "recovered",
        "value": True,
        "return_time": 1,
        "persistence_horizon": 1,
    }
    s["trace_library"]["safe"] = [
        {"life_safe": True, "recovered": False},
        {"life_safe": True, "recovered": True},
        {"life_safe": True, "recovered": True},
    ]
    s["trace_library"]["unsafe_late"] = [
        {"life_safe": True, "recovered": False},
        {"life_safe": True, "recovered": True},
        {"life_safe": False, "recovered": True},
    ]
    out = evaluate(rebind(s))
    assert out["status"] == STATUS_LICENSED
    assert out["selected_action"] == "PREPARE"


def test_10000_realizability_mutations_fail_closed():
    for i in range(10_000):
        s = demo()
        k = i % 7
        if k == 0:
            s["envelope"]["observation_envelope"].append("future_sensor")
            s["actions"][0]["future_observation_contract"] = {
                "channel": "future_sensor",
                "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
                "responses": {"VALUE": "ghost1", "CHANNEL_DOWN": "ghost2"},
            }
        elif k == 1:
            s = attach_valid_future_policy(s)
            s["adaptive_policy"]["nodes"]["n1"]["action"] = "OUTSIDE"
        elif k == 2:
            s = attach_valid_future_policy(s)
            s["actor_information"]["other"] = {"known": ["current_state"]}
            s["adaptive_policy"]["nodes"]["n0"]["observe"]["delivered_to"] = ["other"]
        elif k == 3:
            s = attach_valid_future_policy(s)
            s["adaptive_policy"]["nodes"]["n0"]["observe"]["time"] = 2
            s["adaptive_policy"]["nodes"]["n1"]["time"] = 1
        elif k == 4:
            s["boundary_contracts"] = [{
                "id": "c",
                "used_by": ["PREPARE"],
                "invoke_time": 1,
                "branches": {
                    world: {
                        dist: {
                            "assumption": not (world == "fragile" and dist == "degraded"),
                            "guarantee": True,
                        }
                        for dist in s["disturbances"]
                    }
                    for world in [w["id"] for w in s["worlds"]]
                },
            }]
        elif k == 5:
            s["recovery_contract"] = {
                "required": True,
                "field": "recovered",
                "value": True,
                "return_time": 1,
                "persistence_horizon": 1,
            }
            s["trace_library"]["safe"] = [
                {"life_safe": True, "recovered": False},
                {"life_safe": True, "recovered": True},
                {"life_safe": True, "recovered": False},
            ]
        else:
            s = attach_valid_future_policy(s)
            s["adaptive_policy"]["nodes"]["n1"].pop("terminal")
            s["adaptive_policy"]["nodes"]["n1"]["observe"] = {
                "channel": "future_sensor",
                "time": 1,
                "delivered_to": ["incident_lead"],
                "admitted_outcomes": ["VALUE"],
                "outcomes": {"VALUE": "n0"},
            }

        out = evaluate(rebind(s))
        assert out["status"] != STATUS_LICENSED, (i, out)
        assert out["selected_action"] is None, (i, out)
