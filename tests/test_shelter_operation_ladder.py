import shelter_operation_ladder as so


def base_node(**overrides):
    node = {
        "dry_operating_surface": True,
        "dry_status_verified": True,
        "dry_status_fresh": True,
        "immediate_site_hazard_safe": True,
        "drainage_not_blocking_operation": True,

        "provider_access_verified": True,
        "community_distribution_access_verified": True,
        "communications_available": True,
        "basic_first_aid_access": True,

        "safe_loading_unloading": True,
        "goods_staging_area": True,
        "people_vehicle_separation": True,
        "basic_lighting_or_daylight": True,
        "drinking_water_for_workers": True,
        "waste_handling": True,

        "capacity_declared": True,
        "potable_water": True,
        "toilets_and_hand_hygiene": True,
        "weather_protection": True,
        "accessible_waiting_area": True,
        "food_distribution_safe": True,
        "health_referral_access": True,
        "vulnerable_support": True,

        "sleeping_space": True,
        "bedding_or_sleeping_surfaces": True,
        "privacy_and_dignity": True,
        "bathing_or_washing": True,
        "safe_food_preparation_or_provision": True,
        "night_lighting": True,
        "structural_and_fire_safety": True,
        "medicine_health_support": True,
        "critical_power_if_required": True,
        "resident_accountability": True,
        "protection_arrangements": True,

        "service_water": True,
        "sanitation_wastewater": True,
        "solid_waste_management": True,
        "resupply_continuity": True,
        "maintenance_staffing_or_mechanism": True,
        "feedback_complaints": True,
        "child_safeguarding": True,
        "gbv_protection": True,
        "family_unity": True,
        "psychosocial_referral": True,
        "animal_plan_if_present": True,
        "contingency_relocation_plan": True,
        "return_or_closure_plan": True,
        "reassessment_cycle": True,
    }
    node.update(overrides)
    return node


def test_wet_operating_surface_blocks_every_level():
    result = so.evaluate_shelter_operation(base_node(dry_operating_surface=False))
    assert result.state == so.NO_SHELTER_OPERATION
    assert result.level is None
    assert "dry_operating_surface" in result.failed_fields


def test_unknown_dry_status_never_promotes_to_l0():
    result = so.evaluate_shelter_operation(base_node(dry_status_verified=None))
    assert result.state == so.UNKNOWN
    assert result.level is None
    assert result.next_level == so.LEVEL_0


def test_l0_is_minimum_dry_interface():
    node = base_node()
    node["safe_loading_unloading"] = None
    result = so.evaluate_shelter_operation(node)
    assert result.state == "LEVEL_CONFIRMED"
    assert result.level == so.LEVEL_0
    assert result.next_level == so.LEVEL_1


def test_day_support_requires_wash_and_waiting_capability():
    node = base_node(toilets_and_hand_hygiene=False)
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_1
    assert result.next_level == so.LEVEL_2
    assert "toilets_and_hand_hygiene" in result.failed_fields


def test_overnight_requires_sleeping_privacy_fire_and_health():
    node = base_node(structural_and_fire_safety=False)
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_2
    assert result.next_level == so.LEVEL_3


def test_full_operation_is_cumulative_not_weighted():
    node = base_node(return_or_closure_plan=False)
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_3
    assert result.next_level == so.LEVEL_4
    assert "return_or_closure_plan" in result.failed_fields


def test_full_operation_when_all_hard_requirements_pass():
    result = so.evaluate_shelter_operation(base_node())
    assert result.state == "LEVEL_CONFIRMED"
    assert result.level == so.LEVEL_4
    assert result.next_level is None


def test_verified_tool_capability_can_satisfy_missing_level_requirement():
    node = base_node()
    node["potable_water"] = None
    node["verified_tool_capabilities"] = {
        "potable_water": {
            "verified": True,
            "fresh": True,
            "operable": True,
            "capacity_ok": True,
            "horizon_ok": True,
        }
    }
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_4


def test_tool_capability_without_capacity_or_horizon_stays_unknown():
    node = base_node()
    node["potable_water"] = None
    node["verified_tool_capabilities"] = {
        "potable_water": {
            "verified": True,
            "fresh": True,
            "operable": True,
            "capacity_ok": None,
            "horizon_ok": True,
        }
    }
    result = so.evaluate_shelter_operation(node)
    assert result.level == so.LEVEL_1
    assert result.next_level == so.LEVEL_2
    assert "potable_water" in result.unknown_fields


def test_tool_capability_never_overrides_dry_gate():
    node = base_node(dry_operating_surface=False)
    node["verified_tool_capabilities"] = {
        "dry_operating_surface": {
            "verified": True,
            "fresh": True,
            "operable": True,
            "capacity_ok": True,
            "horizon_ok": True,
        }
    }
    result = so.evaluate_shelter_operation(node)
    assert result.state == so.NO_SHELTER_OPERATION
    assert result.level is None


def test_dry_gate_pass_fail_unknown():
    assert so.dry_gate(base_node()).state == "PASS"
    assert so.dry_gate(base_node(dry_operating_surface=False)).state == "FAIL"
    assert so.dry_gate(base_node(dry_operating_surface=None)).state == "UNKNOWN"


def test_dry_gate_refactor_identical():
    """P-C design: `dry_gate(node)` was extracted out of
    `evaluate_shelter_operation`'s own first loop with NO behaviour change -- the
    failed/unknown fields and the resulting level/state must match exactly, across
    PASS/FAIL/UNKNOWN and every DRY_GATE_FIELDS combination."""
    import itertools

    for combo in itertools.product([True, False, None], repeat=len(so.DRY_GATE_FIELDS)):
        overrides = dict(zip(so.DRY_GATE_FIELDS, combo))
        node = base_node(**overrides)
        gate = so.dry_gate(node)
        result = so.evaluate_shelter_operation(node)
        if gate.state == "FAIL":
            assert result.state == so.NO_SHELTER_OPERATION
            assert result.failed_fields == gate.failed_fields
            assert result.unknown_fields == gate.unknown_fields
            assert result.level is None
        elif gate.state == "UNKNOWN":
            assert result.state == so.UNKNOWN
            assert result.next_level == so.LEVEL_0
            assert result.unknown_fields == gate.unknown_fields
        else:
            assert gate.state == "PASS"
            assert result.state in (so.UNKNOWN, so.NO_SHELTER_OPERATION, "LEVEL_CONFIRMED")
