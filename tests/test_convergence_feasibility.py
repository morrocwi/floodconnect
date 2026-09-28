import convergence_feasibility as cf


def base_candidate(**overrides):
    candidate = {
        "provider_id": "provider_a",
        "resource": "essential_medicine",
        "demand": 10,
        "local_stock": 2,
        "provider_supply": 20,
        "path_capacity": 12,
        "interface_node": "transfer_q",
        "interface_exists": True,
        "interface_verified": True,
        "interface_fresh": True,
        "path_exists": True,
        "path_verified": True,
        "path_fresh": True,
        "path_feasible": True,
        "failure_time_h": 5,
        "arrival_time_h": 2,
    }
    candidate.update(overrides)
    return candidate


def test_feasible_when_quantity_connectivity_and_time_close_gap():
    result = cf.evaluate_candidate(**base_candidate())
    assert result.state == cf.FEASIBLE
    assert result.need_gap == 8
    assert result.deliverable_quantity == 12
    assert result.arrival_slack_h == 3


def test_supply_exists_but_path_capacity_bottleneck_fails():
    result = cf.evaluate_candidate(**base_candidate(path_capacity=4))
    assert result.state == cf.INFEASIBLE
    assert cf.REASON_PATH_CAPACITY_INSUFFICIENT in result.reason_codes


def test_supply_and_capacity_exist_but_arrival_is_too_late():
    result = cf.evaluate_candidate(**base_candidate(arrival_time_h=5))
    assert result.state == cf.INFEASIBLE
    assert cf.REASON_ARRIVAL_TOO_LATE in result.reason_codes
    assert result.arrival_slack_h == 0


def test_unverified_interface_stays_unknown_fail_closed():
    result = cf.evaluate_candidate(**base_candidate(interface_verified=False))
    assert result.state == cf.UNKNOWN
    assert cf.REASON_INTERFACE_UNVERIFIED in result.reason_codes


def test_no_declared_gap_is_not_required():
    result = cf.evaluate_candidate(**base_candidate(demand=2, local_stock=2))
    assert result.state == cf.NOT_REQUIRED


def test_existential_semantics_any_verified_feasible_candidate_closes_gap():
    blocked = base_candidate(
        provider_id="provider_blocked",
        path_exists=False,
    )
    feasible = base_candidate(provider_id="provider_working")
    result = cf.evaluate_candidates([blocked, feasible])
    assert result.state == cf.FEASIBLE
    assert result.provider_id == "provider_working"


def test_unknown_is_preserved_when_no_candidate_is_feasible():
    blocked = base_candidate(path_exists=False)
    unknown = base_candidate(
        provider_id="provider_unknown",
        path_capacity=None,
    )
    result = cf.evaluate_candidates([blocked, unknown])
    assert result.state == cf.UNKNOWN
