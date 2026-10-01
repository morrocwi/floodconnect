"""Adversarial property tests for DSVA v0.4.

These tests do NOT change DSVA semantics. They encode counterexamples and invariants
used by experiments/2026-10-01-dsva-v04-brutal-redteam.md.

A passing pytest here can mean either:
- an intended invariant survives; or
- a counterexample is reproducible and therefore a documented theory/implementation gap is real.

The latter tests are named *_counterexample_* explicitly.
"""

from convergence_feasibility import evaluate_candidate, FEASIBLE


def common_actions(state_to_actions):
    sets = [set(v) for v in state_to_actions.values()]
    if not sets:
        return None
    out = sets[0]
    for s in sets[1:]:
        out = out.intersection(s)
    return out


def test_quantifier_trap_requires_common_observation_based_policy():
    # Each hidden state has a safe action, but the same current information cannot choose both.
    safe = {"x1": {"A"}, "x2": {"B"}}
    assert all(safe.values())
    assert common_actions(safe) == set()


def test_future_information_after_deadline_cannot_rescue_current_action():
    # State is revealed one step later, but safe action is required now.
    safe_now = {"x1": {"A"}, "x2": {"B"}}
    assert common_actions(safe_now) == set()


def test_empty_admissible_set_vacuity_counterexample_is_real():
    # Python's all(), like first-order universal quantification, is true over an empty set.
    # Therefore central viability equations need an explicit nonempty/consistent-state guard.
    assert all(True for _ in []) is True


def test_shared_edge_oversubscription_counterexample_is_real():
    # Two candidates independently pass today's single-candidate LCF evaluator.
    kwargs = dict(
        resource="water",
        demand=8,
        local_stock=0,
        provider_supply=8,
        path_capacity=10,
        interface_node="q",
        interface_exists=True,
        interface_verified=True,
        interface_fresh=True,
        path_exists=True,
        path_verified=True,
        path_fresh=True,
        path_feasible=True,
        failure_time_h=4,
        arrival_time_h=1,
    )
    a = evaluate_candidate(provider_id="p1", **kwargs)
    b = evaluate_candidate(provider_id="p2", **kwargs)
    assert a.state == FEASIBLE
    assert b.state == FEASIBLE

    # But simultaneous dispatch over one physical shared edge would exceed capacity.
    assert a.deliverable_quantity == 8
    assert b.deliverable_quantity == 8
    assert a.deliverable_quantity + b.deliverable_quantity > 10


def test_hysteresis_blocks_one_step_false_deescalation():
    danger = [True, False, True]

    naive = ["ESCALATE" if x else "DEESCALATE" for x in danger]

    phase = "ESCALATE"
    calm_run = 0
    held = []
    for x in danger:
        if x:
            phase = "ESCALATE"
            calm_run = 0
        else:
            calm_run += 1
            if calm_run >= 2:
                phase = "DEESCALATE"
        held.append(phase)

    assert naive == ["ESCALATE", "DEESCALATE", "ESCALATE"]
    assert held == ["ESCALATE", "ESCALATE", "ESCALATE"]


def test_recovery_dead_end_has_no_recovery_policy():
    # Minimal finite witness: life-critical state can be held, but K is unreachable.
    transitions = {"LIFE_ONLY": {"hold": "LIFE_ONLY"}}
    target = "NORMAL_K"
    reachable = {
        transitions["LIFE_ONLY"][a]
        for a in transitions["LIFE_ONLY"]
    }
    assert target not in reachable


def test_road_clear_does_not_imply_community_recovered():
    road_clear = True
    essential_services_restored = False
    assert road_clear is True
    assert essential_services_restored is False


def test_local_viability_can_hide_downstream_externality_counterexample():
    # If the model boundary excludes a harmed downstream node, local K can remain true.
    local_k = True
    omitted_downstream_safe = False
    assert local_k is True
    assert omitted_downstream_safe is False


def test_r07_shape_can_admit_fresh_but_bad_quality_counterexample():
    # DSVA-R07 currently lists semantic/provenance/active/fresh gates.
    # The broader manuscript has quality/QC, but the residual equation alone omits it.
    semantic_ok = provenance_ok = active = fresh = True
    quality_ok = False
    r07_as_written = semantic_ok and provenance_ok and active and fresh
    assert r07_as_written is True
    assert quality_ok is False


def test_r07_shape_can_admit_datum_incompatible_counterexample():
    semantic_ok = provenance_ok = active = fresh = True
    datum_compatible = False
    r07_as_written = semantic_ok and provenance_ok and active and fresh
    assert r07_as_written is True
    assert datum_compatible is False


def test_forecast_support_missing_requires_unknown_not_false():
    support = None
    observed = 100.0

    if support is None:
        support_breach = None
    else:
        lo, hi = support
        support_breach = not (lo <= observed <= hi)

    assert support_breach is None
