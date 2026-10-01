"""Second-order adversarial tests for DSVA v0.5.

Purpose:
Force the seven v0.5 closure flags to PASS, then construct finite cases in which
an action can still be wrong. These tests expose *meta-closure* gaps; they do not
change production semantics.

A passing pytest means the counterexample is reproducible.
"""

CLOSURES = (
    "information",
    "evidence",
    "state",
    "transition",
    "boundary",
    "capacity",
    "recovery",
)


def all_seven_pass():
    return {k: True for k in CLOSURES}


def test_open_world_truth_outside_admissible_set_counterexample():
    closures = all_seven_pass()
    modeled_worlds = {"normal_receiver"}
    true_world = "levee_breach_unmodelled"
    action = "EXPORT"
    safe_in_modeled_worlds = action == "EXPORT"
    unsafe_in_true_world = true_world not in modeled_worlds
    assert all(closures.values())
    assert safe_in_modeled_worlds
    assert unsafe_in_true_world


def test_common_mode_sensor_bias_counterexample():
    closures = all_seven_pass()
    # Two individually fresh/quality/compatible sensors share one biased reference.
    true_level = 1.20
    shared_bias = -0.35
    sensor_a = true_level + shared_bias
    sensor_b = true_level + shared_bias
    threshold = 1.00
    fused_estimate = (sensor_a + sensor_b) / 2
    assert all(closures.values())
    assert sensor_a < threshold and sensor_b < threshold
    assert fused_estimate < threshold
    assert true_level > threshold


def test_circular_assume_guarantee_counterexample():
    closures = all_seven_pass()
    # A: if B provides power, A guarantees pumping.
    # B: if A pumps, B guarantees power.
    # Syntactic compatibility is circular; neither service is initially available.
    power_available = False
    pump_available = False
    contract_a = ("assume_power", "guarantee_pump")
    contract_b = ("assume_pump", "guarantee_power")
    syntactically_coupled = (
        contract_a[0] == "assume_power"
        and contract_b[1] == "guarantee_power"
        and contract_b[0] == "assume_pump"
        and contract_a[1] == "guarantee_pump"
    )
    assert all(closures.values())
    assert syntactically_coupled
    assert not power_available and not pump_available


def test_advice_expires_before_actuation_counterexample():
    closures = all_seven_pass()
    readout_time = 0
    action_effect_time = 10
    route_safe_until = 5
    advice = "MOVE"
    assert all(closures.values())
    assert advice == "MOVE"
    assert readout_time < route_safe_until < action_effect_time


def test_future_evidence_channel_failure_counterexample():
    closures = all_seven_pass()
    # Current action WAIT is safe only if the next observation distinguishes x1/x2.
    current_action = "WAIT"
    next_observation_required = True
    comms_available_next_step = False
    branch_action = {"x1": "OPEN_GATE", "x2": "CLOSE_GATE"}
    assert all(closures.values())
    assert current_action == "WAIT"
    assert branch_action["x1"] != branch_action["x2"]
    assert next_observation_required and not comms_available_next_step


def test_transient_reentry_is_not_persistent_recovery_counterexample():
    closures = all_seven_pass()
    # t0 outside K, t1 inside K, t2 immediately outside again.
    in_normal_k = [False, True, False]
    assert all(closures.values())
    assert any(in_normal_k)
    assert in_normal_k[1] is True
    assert in_normal_k[2] is False


def test_cross_graph_resource_double_booking_counterexample():
    closures = all_seven_pass()
    # One physical boat is independently allocated in movement and support graphs.
    boats_available = 1
    movement_allocation = 1
    support_allocation = 1
    assert all(closures.values())
    assert movement_allocation <= boats_available
    assert support_allocation <= boats_available
    assert movement_allocation + support_allocation > boats_available


def test_omitted_vulnerable_group_counterexample():
    closures = all_seven_pass()
    modeled_population_safe = True
    vulnerable_group_in_state_and_constraints = False
    actual_vulnerable_group_safe = False
    assert all(closures.values())
    assert modeled_population_safe
    assert not vulnerable_group_in_state_and_constraints
    assert not actual_vulnerable_group_safe


def test_solver_result_without_certificate_counterexample():
    closures = all_seven_pass()
    mathematical_problem_has_feasible_solution = True
    solver_reports_feasible = True
    returned_plan_satisfies_constraints = False
    assert all(closures.values())
    assert mathematical_problem_has_feasible_solution
    assert solver_reports_feasible
    assert not returned_plan_satisfies_constraints


def test_near_threshold_uncertainty_can_flip_reader_counterexample():
    closures = all_seven_pass()
    measured = 0.99
    uncertainty = 0.05
    threshold = 1.00
    point_reader = measured < threshold
    interval_crosses_threshold = measured - uncertainty <= threshold <= measured + uncertainty
    assert all(closures.values())
    assert point_reader is True
    assert interval_crosses_threshold


def test_scope_leak_from_finite_horizon_counterexample():
    closures = all_seven_pass()
    declared_horizon = 6
    safe_until = 6
    failure_at = 7
    label_without_horizon = "SAFE"
    assert all(closures.values())
    assert safe_until == declared_horizon
    assert failure_at > declared_horizon
    assert label_without_horizon == "SAFE"


def test_compound_hazard_interaction_outside_factorized_model_counterexample():
    closures = all_seven_pass()
    flood_only_safe = True
    power_only_safe = True
    flood_plus_power_outage_safe = False
    factorized_scenario_set_contains_joint_event = False
    assert all(closures.values())
    assert flood_only_safe and power_only_safe
    assert not flood_plus_power_outage_safe
    assert not factorized_scenario_set_contains_joint_event
