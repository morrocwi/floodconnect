import convergence_board as cb


def l0_candidate(node_id, distance, **overrides):
    data = {
        "node_id": node_id,
        "distance_to_affected_m": distance,
        "dry_operating_surface": True,
        "dry_status_verified": True,
        "dry_status_fresh": True,
        "immediate_site_hazard_safe": True,
        "drainage_not_blocking_operation": True,
        "provider_access_verified": True,
        "community_distribution_access_verified": True,
        "communications_available": True,
        "basic_first_aid_access": True,
    }
    data.update(overrides)
    return data


def test_selects_nearest_verified_dry_shared_interface():
    result = cb.select_nearest_dry_interface([
        l0_candidate("q_far", 900),
        l0_candidate("q_near", 300),
    ])
    assert result.state == cb.SELECTED
    assert result.node_id == "q_near"
    assert result.distance_to_affected_m == 300


def test_closer_wet_node_is_not_candidate():
    result = cb.select_nearest_dry_interface([
        l0_candidate("wet", 100, dry_operating_surface=False),
        l0_candidate("dry", 400),
    ])
    assert result.state == cb.SELECTED
    assert result.node_id == "dry"


def test_unknown_candidate_prevents_false_nearest_claim():
    result = cb.select_nearest_dry_interface([
        l0_candidate("known", 500),
        l0_candidate("maybe_closer", 100, dry_status_verified=None),
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
