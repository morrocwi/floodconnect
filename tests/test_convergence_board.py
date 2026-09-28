import convergence_board as cb


def test_selects_nearest_verified_dry_shared_interface():
    result = cb.select_nearest_dry_interface([
        {
            "node_id": "q_far", "dry": True, "verified": True, "fresh": True,
            "provider_reachable": True, "community_reachable": True,
            "distribution_feasible": True, "distance_to_affected_m": 900,
        },
        {
            "node_id": "q_near", "dry": True, "verified": True, "fresh": True,
            "provider_reachable": True, "community_reachable": True,
            "distribution_feasible": True, "distance_to_affected_m": 300,
        },
    ])
    assert result.state == cb.SELECTED
    assert result.node_id == "q_near"
    assert result.distance_to_affected_m == 300


def test_closer_wet_node_is_not_candidate():
    result = cb.select_nearest_dry_interface([
        {
            "node_id": "wet", "dry": False, "verified": True, "fresh": True,
            "provider_reachable": True, "community_reachable": True,
            "distribution_feasible": True, "distance_to_affected_m": 100,
        },
        {
            "node_id": "dry", "dry": True, "verified": True, "fresh": True,
            "provider_reachable": True, "community_reachable": True,
            "distribution_feasible": True, "distance_to_affected_m": 400,
        },
    ])
    assert result.state == cb.SELECTED
    assert result.node_id == "dry"


def test_unknown_candidate_prevents_false_nearest_claim():
    result = cb.select_nearest_dry_interface([
        {
            "node_id": "known", "dry": True, "verified": True, "fresh": True,
            "provider_reachable": True, "community_reachable": True,
            "distribution_feasible": True, "distance_to_affected_m": 500,
        },
        {
            "node_id": "maybe_closer", "dry": True, "verified": None, "fresh": True,
            "provider_reachable": True, "community_reachable": True,
            "distribution_feasible": True, "distance_to_affected_m": 100,
        },
    ])
    assert result.state == cb.UNKNOWN


def test_kanban_is_three_information_lanes_without_dispatcher():
    cards = [
        {
            "card_id": "n1", "kind": "NEED", "updated_at": "2026-09-29T04:00:00+07:00",
            "zone_id": "z3", "resource": "medicine", "quantity": 1,
        },
        {
            "card_id": "s1", "kind": "SUPPLY", "updated_at": "2026-09-29T04:01:00+07:00",
            "provider_id": "team_a", "resource": "medicine", "quantity": 5,
            "at_node": "q1",
        },
        {
            "card_id": "r1", "kind": "ROUTE", "updated_at": "2026-09-29T04:02:00+07:00",
            "from_node": "q1", "to_zone": "z3", "verified": True, "fresh": True,
            "status": "OPEN",
        },
    ]
    board = cb.project_kanban(cards)
    assert [x["card_id"] for x in board["NEED"]] == ["n1"]
    assert [x["card_id"] for x in board["SUPPLY"]] == ["s1"]
    assert [x["card_id"] for x in board["ROUTE"]] == ["r1"]
    assert board["INVALID"] == []


def test_public_board_rejects_personal_identifiers():
    board = cb.project_kanban([{
        "card_id": "n1", "kind": "NEED", "updated_at": "2026-09-29T04:00:00+07:00",
        "zone_id": "z3", "resource": "medicine", "quantity": 1,
        "phone": "should-not-be-public",
    }])
    assert board["NEED"] == []
    assert "PRIVATE_FIELD_NOT_ALLOWED" in board["INVALID"][0]["_validation_reasons"]


def test_route_card_must_be_fresh_and_verified():
    board = cb.project_kanban([{
        "card_id": "r1", "kind": "ROUTE", "updated_at": "2026-09-29T04:02:00+07:00",
        "from_node": "q1", "to_zone": "z3", "verified": False, "fresh": True,
        "status": "OPEN",
    }])
    assert board["ROUTE"] == []
    assert "ROUTE_UNVERIFIED" in board["INVALID"][0]["_validation_reasons"]
