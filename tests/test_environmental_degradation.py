from datetime import datetime, timezone

import environmental_degradation as ed
import shelter_decision as sd


NOW = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)


def _env(**overrides):
    block = {
        "evaluated_at": "2026-09-28T20:00:00+00:00",
        "sewage_intrusion": "NONE",
        "indoor_floodwater_present": False,
        "sewer_backflow": "NONE",
        "drainage_surcharge_possible": False,
        "backwater_valve_state": "OPEN",
        "sewer_gas_odor": "NONE",
        "low_lying_or_enclosed_space": False,
        "ventilation": "ADEQUATE",
        "measured_h2s_ppm": None,
        "drain_trap_state": "SEALED",
        "indoor_materials_wet": False,
        "indoor_wet_since": None,
        "fully_dried_and_remediated": False,
        "standing_water_present": False,
        "standing_water_since": None,
        "water_movement": "FLOWING",
        "organic_or_sewage_load": "LOW",
        "mitigation_plan_verified": False,
        "mitigation_before_deadline": False,
    }
    block.update(overrides)
    return block


def _sustain(**overrides):
    block = {
        "fresh": True,
        "assessed_horizon_h": 72,
        "physical_safety": "SAFE",
        "potable_water_for_horizon": "SUFFICIENT",
        "service_water_for_horizon": "SUFFICIENT",
        "food_for_horizon": "SUFFICIENT",
        "essential_medicine_for_horizon": "SUFFICIENT",
        "critical_power": "NOT_REQUIRED",
        "sanitation_hygiene": "SUFFICIENT",
        "communications": "SUFFICIENT",
        "vulnerable_support": "SUFFICIENT",
        "official_instruction": "NONE",
        "escalation": {"status": "AVAILABLE", "fresh": True, "verified": True},
        "resupply": {"supplier_node": None, "route_edges": [], "official_movement_conflict": False},
    }
    block.update(overrides)
    return block


def test_sewage_contamination_is_immediate_not_age_based():
    node = {"environment": _env(sewage_intrusion="CONFIRMED")}
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert result.state == ed.UNSAFE
    assert ed.TRIGGER_SEWAGE_CONTAMINATION in result.triggers
    assert "sanitation_hygiene" in result.hard_failures


def test_mold_prevention_clock_24_to_48_hours():
    node = {
        "environment": _env(
            indoor_materials_wet=True,
            indoor_wet_since="2026-09-27T14:00:00+00:00",
        )
    }
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert result.state == ed.DEGRADING
    assert ed.TRIGGER_MOLD_PREVENTION_WINDOW in result.triggers
    assert result.details["indoor_wet_age_h"] == 30.0
    assert result.next_deadline_h == 18.0


def test_wet_materials_48h_assume_mold_present():
    node = {
        "environment": _env(
            indoor_materials_wet=True,
            indoor_wet_since="2026-09-26T18:00:00+00:00",
        )
    }
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert result.state == ed.UNSAFE
    assert ed.TRIGGER_ASSUME_MOLD in result.triggers
    assert "indoor_environment" in result.hard_failures


def test_full_drying_ends_mold_clock():
    node = {
        "environment": _env(
            indoor_materials_wet=True,
            indoor_wet_since="2026-09-25T00:00:00+00:00",
            fully_dried_and_remediated=True,
        )
    }
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert ed.TRIGGER_ASSUME_MOLD not in result.triggers
    assert "indoor_environment" not in result.hard_failures


def test_standing_water_requires_vector_control_and_weekly_escalation():
    node = {
        "environment": _env(
            standing_water_present=True,
            standing_water_since="2026-09-20T20:00:00+00:00",
        )
    }
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert ed.TRIGGER_VECTOR_CONTROL in result.triggers
    assert ed.TRIGGER_VECTOR_CYCLE_ESCALATED in result.triggers


def test_sewer_odor_in_enclosed_space_is_unresolved_not_ppm_guess():
    node = {
        "environment": _env(
            sewer_gas_odor="ROTTEN_EGG",
            low_lying_or_enclosed_space=True,
            ventilation="POOR",
        )
    }
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert result.state == ed.UNKNOWN
    assert ed.TRIGGER_SEWER_GAS_UNRESOLVED in result.triggers
    assert "sewer_gas_concentration" in result.unknowns
    assert "measured_h2s_ppm" not in result.details


def test_measured_h2s_at_occupational_ceiling_is_hard_hazard_trigger():
    node = {"environment": _env(measured_h2s_ppm=10.0)}
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert result.state == ed.UNSAFE
    assert ed.TRIGGER_H2S_MEASURED_ELEVATED in result.triggers
    assert "air_quality" in result.hard_failures


def test_absence_of_odor_does_not_clear_unknown_h2s_by_itself():
    node = {
        "environment": _env(
            sewer_gas_odor="NONE",
            low_lying_or_enclosed_space=True,
            ventilation="POOR",
            water_movement="STAGNANT",
            organic_or_sewage_load="SEWAGE",
        )
    }
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert ed.TRIGGER_ANAEROBIC_ODOR_PLAUSIBLE in result.triggers
    assert result.details["h2s_model_note"].startswith("anaerobic sulfide formation is plausible")


def test_dry_trap_is_distinct_sewer_gas_pathway():
    node = {"environment": _env(drain_trap_state="DRY")}
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert ed.TRIGGER_DRY_TRAP_SEWER_GAS in result.triggers


def test_closed_backwater_valve_triggers_water_use_limit():
    node = {"environment": _env(backwater_valve_state="CLOSED")}
    result = ed.evaluate_environmental_degradation(node, now=NOW)
    assert ed.TRIGGER_BACKWATER_WATER_USE_LIMIT in result.triggers


def test_sustainment_becomes_unknown_when_environmental_deadline_is_inside_horizon():
    node = {
        "kind": "household",
        "sustainment": _sustain(),
        "environment": _env(
            indoor_materials_wet=True,
            indoor_wet_since="2026-09-27T14:00:00+00:00",
        ),
    }
    # evaluate_environmental_degradation uses evaluated_at, making replay deterministic.
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.UNKNOWN
    assert sd.REASON_ENVIRONMENTAL_DEGRADATION_WITHIN_HORIZON in result.reason_codes


def test_verified_mitigation_before_deadline_preserves_horizon_claim():
    node = {
        "kind": "household",
        "sustainment": _sustain(),
        "environment": _env(
            indoor_materials_wet=True,
            indoor_wet_since="2026-09-27T14:00:00+00:00",
            mitigation_plan_verified=True,
            mitigation_before_deadline=True,
        ),
    }
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.SUSTAINABLE


def test_environmental_unsafe_makes_household_not_sustainable():
    node = {
        "kind": "household",
        "sustainment": _sustain(),
        "environment": _env(sewer_backflow="CONFIRMED"),
    }
    result = sd.evaluate_sustainment(node, 24)
    assert result.state == sd.NOT_SUSTAINABLE
    assert sd.REASON_ENVIRONMENTAL_DEGRADATION_UNSAFE in result.reason_codes


def test_shelter_environmental_failure_rejects_occupancy():
    shelter = {
        "kind": "internal_safe",
        "status": "SAFE",
        "fresh": True,
        "capacity_persons": 20,
        "occupied_persons": 2,
        "services": [],
        "environment": _env(sewage_intrusion="CONFIRMED"),
        "shelter": {
            "site_hazard_safety": "SAFE",
            "structural_fire_safety": "SAFE",
            "access_accessibility": "AVAILABLE",
            "drinking_water": "SUFFICIENT",
            "service_water": "SUFFICIENT",
            "sanitation_hygiene": "SUFFICIENT",
            "food_special_diets": "SUFFICIENT",
            "medicine_health": "SUFFICIENT",
            "critical_power": "SUFFICIENT",
            "communications": "AVAILABLE",
            "capacity": "SUFFICIENT",
            "member_accountability": "READY",
            "vulnerable_support": "SUFFICIENT",
            "resupply_access": "AVAILABLE",
            "management_staffing": "READY",
            "waste_management": "READY",
            "sleeping_protection": "READY",
            "privacy_dignity": "READY",
            "child_safeguarding": "READY",
            "gbv_protection": "READY",
            "feedback_complaints": "READY",
            "family_unity": "READY",
            "psychosocial_referral": "READY",
            "exit_closure_plan": "READY",
        },
    }
    result = sd.screen_shelter_candidate(shelter, phase="OCCUPIED")
    assert result.admitted is False
    assert "environmental_degradation" in result.details["failed"]
