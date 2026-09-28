import operational_resources as ores


def test_verified_water_truck_produces_potable_water_evidence():
    reg = ores.load_registry()
    out = ores.deployment_capability_evidence({
        "tool_id": "mobile_drinking_water_truck",
        "verified": True,
        "fresh": True,
        "operable": True,
        "operator_qualified": True,
        "capacity_ok": True,
        "horizon_ok": True,
    }, reg)
    assert "potable_water" in out
    assert out["potable_water"]["capacity_ok"] is True


def test_required_operator_blocks_capability_credit():
    reg = ores.load_registry()
    out = ores.deployment_capability_evidence({
        "tool_id": "mobile_drinking_water_truck",
        "verified": True,
        "fresh": True,
        "operable": True,
        "operator_qualified": False,
        "capacity_ok": True,
        "horizon_ok": True,
    }, reg)
    assert out == {}


def test_unknown_capacity_is_preserved_for_downstream_fail_closed_logic():
    reg = ores.load_registry()
    out = ores.deployment_capability_evidence({
        "tool_id": "portable_toilet_handwash",
        "verified": True,
        "fresh": True,
        "operable": True,
        "capacity_ok": None,
        "horizon_ok": True,
    }, reg)
    assert out["toilets_and_hand_hygiene"]["capacity_ok"] is None


def test_tool_registry_does_not_generate_dry_gate_capability():
    reg = ores.load_registry()
    out = ores.deployment_capability_evidence({
        "tool_id": "portable_pump_dewatering",
        "verified": True,
        "fresh": True,
        "operable": True,
        "operator_qualified": True,
        "capacity_ok": True,
        "horizon_ok": True,
    }, reg)
    assert "dry_operating_surface" not in out


def test_merge_accepts_one_complete_candidate_for_same_capability():
    reg = ores.load_registry()
    out = ores.merge_capability_evidence([
        {
            "tool_id": "potable_water_tank",
            "verified": True,
            "fresh": True,
            "operable": True,
            "capacity_ok": None,
            "horizon_ok": True,
        },
        {
            "tool_id": "mobile_drinking_water_truck",
            "verified": True,
            "fresh": True,
            "operable": True,
            "operator_qualified": True,
            "capacity_ok": True,
            "horizon_ok": True,
        },
    ], reg)
    assert out["potable_water"]["capacity_ok"] is True
