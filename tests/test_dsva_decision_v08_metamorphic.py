"""Metamorphic tests for the optimized DSVA v0.8 kernel."""
import copy
import json
from pathlib import Path

from dsva_decision import STATUS_HOLD, evaluate

ROOT = Path(__file__).resolve().parents[1]


def demo():
    return json.loads((ROOT / "examples" / "dsva_decision_minimal.json").read_text(encoding="utf-8"))


def projection(r):
    return (r["status"], r["selected_action"], set(r.get("viable_actions", [])))


def expand_refs(s):
    s = copy.deepcopy(s)
    lib = s.get("trace_library", {})
    for action in s["actions"]:
        for world_out in action["outcomes"].values():
            for item in world_out.values():
                if "trace_ref" in item:
                    ref = item.pop("trace_ref")
                    item["trace"] = copy.deepcopy(lib[ref])
    s.pop("trace_library", None)
    return s


def test_trace_ref_and_inline_are_decision_equivalent():
    assert projection(evaluate(demo())) == projection(evaluate(expand_refs(demo())))


def test_world_requirement_action_permutation_preserves_selected_readout():
    s = demo()
    base = evaluate(s)
    p = copy.deepcopy(s)
    p["worlds"].reverse()
    p["requirements"].reverse()
    p["actions"].reverse()
    out = evaluate(p)
    assert out["status"] == base["status"]
    assert out["selected_action"] == base["selected_action"]
    assert set(out["viable_actions"]) == set(base["viable_actions"])


def test_irrelevant_state_fields_do_not_change_requirement_readout():
    s = demo()
    base = projection(evaluate(s))
    for i, st in enumerate(s["trace_library"]["safe"]):
        st["irrelevant"] = {"nonce": i}
    assert projection(evaluate(s)) == base


def test_relevant_field_change_blocks():
    s = demo()
    s["trace_library"]["safe"][1]["life_safe"] = False
    out = evaluate(s)
    assert out["status"] == STATUS_HOLD
    assert out["selected_action"] is None


def test_reader_confidence_never_overrides_hard_gate():
    for confidence in [0.0, 0.5, 1.0]:
        s = demo()
        s["typed_reader"]["confidence"] = confidence
        s["actions"][0]["requires_info"].append("missing")
        out = evaluate(s)
        assert out["status"] == STATUS_HOLD


def test_decimal_and_fraction_time_encodings_agree():
    a = demo()
    a["question"]["horizon"] = 1.5
    a["valid_until"] = 1.5
    a["envelope"]["trace_resolution"] = 0.5
    a["trace_library"]["safe"] = [{"life_safe": True}] * 4
    a["trace_library"]["unsafe_late"] = [
        {"life_safe": True}, {"life_safe": True}, {"life_safe": True}, {"life_safe": False}
    ]
    for action in a["actions"]:
        action["lease"]["expire"] = 1.5

    b = copy.deepcopy(a)
    b["question"]["horizon"] = "3/2"
    b["valid_until"] = "3/2"
    b["envelope"]["trace_resolution"] = "1/2"
    for action in b["actions"]:
        action["lease"]["expire"] = "3/2"

    assert projection(evaluate(a)) == projection(evaluate(b))


def test_determinism_1000_repeats():
    s = demo()
    first = evaluate(s)
    for _ in range(1000):
        assert evaluate(s) == first
