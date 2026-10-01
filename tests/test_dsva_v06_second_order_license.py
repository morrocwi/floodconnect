"""Reference property tests for the DSVA v0.6 second-order license envelope.

These tests are finite executable witnesses of SOL equations. They are not a
production disaster decision engine.
"""


def license_status(
    *,
    first_order=True,
    applicability=True,
    dependency=True,
    realizability=True,
    execution=True,
    requirements=True,
    verification=True,
    action_viable=True,
):
    required = (
        first_order,
        applicability,
        dependency,
        realizability,
        execution,
        requirements,
        verification,
        action_viable,
    )
    return "LICENSED_WITHIN_ENVELOPE" if all(required) else "HOLD"


def model_invalidated(model_behaviors, observed_behaviors):
    return set(model_behaviors).isdisjoint(set(observed_behaviors))


def action_lease_valid(issue, effect, expire):
    return issue <= effect <= expire


def joint_resource_feasible(available, *allocations):
    return sum(allocations) <= available


def persistent_recovery(sequence, entry_index, hold_steps):
    if not sequence[entry_index]:
        return False
    end = entry_index + hold_steps
    if end >= len(sequence):
        return False
    return all(sequence[i] for i in range(entry_index, end + 1))


def requirement_coverage_gap(declared, represented):
    return set(declared) - set(represented)


def categorical_reader_resolved(labels):
    return len(set(labels)) == 1


def scope_preserved(rendered, *, horizon, valid_until):
    return (
        rendered.get("horizon") == horizon
        and rendered.get("valid_until") == valid_until
    )


def test_open_world_case_is_not_strongly_licensed_without_applicability():
    assert license_status(applicability=False) == "HOLD"


def test_model_invalidation_detects_disjoint_observed_behavior():
    assert model_invalidated({"normal"}, {"breach"}) is True


def test_common_mode_dependency_blocks_independence_promotion():
    # Same calibration ancestor => dependency closure is not discharged.
    ancestors = {"sensor_a": "cal_1", "sensor_b": "cal_1"}
    independent = ancestors["sensor_a"] != ancestors["sensor_b"]
    assert independent is False
    assert license_status(dependency=independent) == "HOLD"


def test_circular_contract_without_reachable_assumption_is_not_realizable():
    power = False
    pump = False
    realizable = power and pump
    assert realizable is False
    assert license_status(realizability=realizable) == "HOLD"


def test_expired_action_lease_blocks_move():
    assert action_lease_valid(issue=0, effect=10, expire=5) is False
    assert license_status(execution=False) == "HOLD"


def test_future_observation_channel_failure_blocks_contingent_policy():
    observation_available = False
    fallback_defined = False
    realizable = observation_available or fallback_defined
    assert realizable is False
    assert license_status(realizability=realizable) == "HOLD"


def test_transient_reentry_is_not_persistent_recovery():
    states_in_k = [False, True, False]
    recovered = persistent_recovery(states_in_k, entry_index=1, hold_steps=1)
    assert recovered is False
    assert license_status(realizability=recovered) == "HOLD"


def test_cross_graph_boat_double_booking_is_blocked_globally():
    feasible = joint_resource_feasible(1, 1, 1)
    assert feasible is False
    assert license_status(dependency=feasible) == "HOLD"


def test_omitted_vulnerable_group_blocks_complete_requirement_license():
    declared = {"general_population", "bed_bound"}
    represented = {"general_population"}
    gap = requirement_coverage_gap(declared, represented)
    assert gap == {"bed_bound"}
    assert license_status(requirements=(not gap)) == "HOLD"


def test_solver_without_independent_check_is_not_licensed():
    solver_says_feasible = True
    independent_check = False
    verification = solver_says_feasible and independent_check
    assert verification is False
    assert license_status(verification=verification) == "HOLD"


def test_threshold_straddle_is_unresolved():
    labels = {"below", "above"}
    resolved = categorical_reader_resolved(labels)
    assert resolved is False
    assert license_status(verification=resolved) == "HOLD"


def test_horizon_scope_erasure_is_not_verified():
    rendered = {"value": "SAFE"}
    ok = scope_preserved(rendered, horizon=6, valid_until=6)
    assert ok is False
    assert license_status(verification=ok) == "HOLD"


def test_compound_hazard_omission_blocks_dependency_license():
    modeled = {"flood", "outage"}
    required_joint = "flood+outage"
    dependency_closed = required_joint in modeled
    assert dependency_closed is False
    assert license_status(dependency=dependency_closed) == "HOLD"


def test_all_first_and_second_order_obligations_pass():
    assert license_status() == "LICENSED_WITHIN_ENVELOPE"
