"""Realizability red-team for DSVA v0.10.

Attacks the remaining gap between the finite theory-contract projection and
DSVA SOL-20..28: full future-policy structure, load-bearing contract
realizability, and persistent recovery.
"""
import json
from pathlib import Path

from dsva_decision import STATUS_LICENSED, evaluate
from tests.dsva_v010_helpers import rebind

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


def test_rz01_future_response_tokens_must_bind_to_real_policy_nodes():
    s = demo()
    s["envelope"]["observation_envelope"].append("future_sensor")
    s["actions"][0]["future_observation_contract"] = {
        "channel": "future_sensor",
        "admitted_outcomes": ["VALUE", "CHANNEL_DOWN"],
        "responses": {
            "VALUE": "MAGIC_NODE",
            "CHANNEL_DOWN": "ANOTHER_MAGIC_NODE"
        }
    }
    # A total string map currently passes even though no executable policy
    # node/action is bound to either response.
    assert_not_licensed(rebind(s))


def test_rz02_future_policy_action_must_stay_inside_actuation_envelope():
    s = demo()
    s["adaptive_policy"] = {
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
                    "outcomes": {"VALUE": "n1", "CHANNEL_DOWN": "n2"}
                }
            },
            "n1": {"time": 1, "actor": "incident_lead", "action": "FLY", "terminal": True},
            "n2": {"time": 1, "actor": "incident_lead", "action": "WAIT", "terminal": True}
        }
    }
    assert_not_licensed(s)


def test_rz03_future_actor_cannot_use_observation_not_delivered_to_them():
    s = demo()
    s["adaptive_policy"] = {
        "root": "n0",
        "nodes": {
            "n0": {
                "time": 0,
                "actor": "incident_lead",
                "action": "PREPARE",
                "observe": {
                    "channel": "future_sensor",
                    "time": 1,
                    "delivered_to": ["sensor_operator"],
                    "outcomes": {"VALUE": "n1", "CHANNEL_DOWN": "n2"}
                }
            },
            "n1": {
                "time": 1,
                "actor": "incident_lead",
                "action": "PREPARE",
                "requires_info": ["future_sensor"],
                "terminal": True
            },
            "n2": {"time": 1, "actor": "incident_lead", "action": "WAIT", "terminal": True}
        }
    }
    assert_not_licensed(s)


def test_rz04_policy_cannot_use_future_observation_before_it_arrives():
    s = demo()
    s["adaptive_policy"] = {
        "root": "n0",
        "nodes": {
            "n0": {
                "time": 0,
                "actor": "incident_lead",
                "action": "PREPARE",
                "observe": {
                    "channel": "future_sensor",
                    "time": 2,
                    "delivered_to": ["incident_lead"],
                    "outcomes": {"VALUE": "n1", "CHANNEL_DOWN": "n2"}
                }
            },
            "n1": {
                "time": 1,
                "actor": "incident_lead",
                "action": "PREPARE",
                "requires_info": ["future_sensor"],
                "terminal": True
            },
            "n2": {"time": 1, "actor": "incident_lead", "action": "WAIT", "terminal": True}
        }
    }
    assert_not_licensed(s)


def test_rz05_load_bearing_assume_guarantee_contract_must_be_realizable_on_every_branch():
    s = demo()
    s["boundary_contracts"] = [{
        "id": "power-pump",
        "used_by": ["PREPARE"],
        "invoke_time": 1,
        "branches": {
            "normal": {
                "base": {"assumption": True, "guarantee": True},
                "degraded": {"assumption": True, "guarantee": True}
            },
            "fragile": {
                "base": {"assumption": True, "guarantee": True},
                "degraded": {"assumption": False, "guarantee": True}
            }
        }
    }]
    assert_not_licensed(s)


def test_rz06_recovery_must_persist_not_only_touch_return_set():
    s = demo()
    s["recovery_contract"] = {
        "required": True,
        "field": "recovered",
        "value": True,
        "return_time": 1,
        "persistence_horizon": 1
    }
    s["trace_library"]["safe"] = [
        {"life_safe": True, "recovered": False},
        {"life_safe": True, "recovered": True},
        {"life_safe": True, "recovered": False}
    ]
    # The system touches recovered=True at t=1, then loses it at t=2.
    assert_not_licensed(rebind(s))


def test_rz07_policy_graph_must_be_acyclic_and_finite():
    s = demo()
    s["adaptive_policy"] = {
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
                    "outcomes": {"VALUE": "n1", "CHANNEL_DOWN": "n1"}
                }
            },
            "n1": {
                "time": 1,
                "actor": "incident_lead",
                "action": "WAIT",
                "observe": {
                    "channel": "future_sensor",
                    "time": 1,
                    "delivered_to": ["incident_lead"],
                    "outcomes": {"VALUE": "n0", "CHANNEL_DOWN": "n0"}
                }
            }
        }
    }
    assert_not_licensed(s)
