#!/usr/bin/env python3
"""FloodConnect Shelter Operation Capability Ladder (SOCL).

A repo-specific, evidence-informed operational ladder. It is NOT a claimed Sphere,
UNHCR, CDC, FEMA, or Thai DDPM standard.

Core invariant:
    NO VERIFIED FRESH DRY OPERATING FOOTPRINT -> NO SHELTER OPERATION LEVEL.

Higher levels are cumulative. A node can only be promoted to level L when the dry
gate and every hard requirement through level L are explicitly satisfied.
UNKNOWN never becomes TRUE and no weighted score may compensate for a failed gate.
"""

from dataclasses import dataclass, asdict
from typing import Any, Optional

NO_SHELTER_OPERATION = "NO_SHELTER_OPERATION"
UNKNOWN = "UNKNOWN"
LEVEL_0 = "SO_L0_DRY_INTERFACE"
LEVEL_1 = "SO_L1_RELIEF_TRANSFER"
LEVEL_2 = "SO_L2_DAY_SUPPORT"
LEVEL_3 = "SO_L3_OVERNIGHT_SHELTER"
LEVEL_4 = "SO_L4_FULL_SHELTER_OPERATION"

LEVELS = (LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4)

# Dry gate applies to every level. "dry_operating_surface" means the actual footprint
# used for people, goods, vehicles, transfer, or occupancy is free of floodwater /
# standing water at the declared assessment time.
DRY_GATE_FIELDS = (
    "dry_operating_surface",
    "dry_status_verified",
    "dry_status_fresh",
    "immediate_site_hazard_safe",
    "drainage_not_blocking_operation",
)

LEVEL_REQUIREMENTS = {
    LEVEL_0: (
        "provider_access_verified",
        "community_distribution_access_verified",
        "communications_available",
        "basic_first_aid_access",
    ),
    LEVEL_1: (
        "safe_loading_unloading",
        "goods_staging_area",
        "people_vehicle_separation",
        "basic_lighting_or_daylight",
        "drinking_water_for_workers",
        "waste_handling",
    ),
    LEVEL_2: (
        "capacity_declared",
        "potable_water",
        "toilets_and_hand_hygiene",
        "weather_protection",
        "accessible_waiting_area",
        "food_distribution_safe",
        "health_referral_access",
        "vulnerable_support",
    ),
    LEVEL_3: (
        "sleeping_space",
        "bedding_or_sleeping_surfaces",
        "privacy_and_dignity",
        "bathing_or_washing",
        "safe_food_preparation_or_provision",
        "night_lighting",
        "structural_and_fire_safety",
        "medicine_health_support",
        "critical_power_if_required",
        "resident_accountability",
        "protection_arrangements",
    ),
    LEVEL_4: (
        "service_water",
        "sanitation_wastewater",
        "solid_waste_management",
        "resupply_continuity",
        "maintenance_staffing_or_mechanism",
        "feedback_complaints",
        "child_safeguarding",
        "gbv_protection",
        "family_unity",
        "psychosocial_referral",
        "animal_plan_if_present",
        "contingency_relocation_plan",
        "return_or_closure_plan",
        "reassessment_cycle",
    ),
}


@dataclass(frozen=True)
class ShelterOperationResult:
    state: str
    level: Optional[str] = None
    next_level: Optional[str] = None
    failed_fields: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _truth(value: Any) -> Optional[bool]:
    if value is True:
        return True
    if value is False:
        return False
    return None


def evaluate_shelter_operation(node: dict[str, Any]) -> ShelterOperationResult:
    """Return highest defensible shelter-operation level under cumulative hard gates."""

    failed = []
    unknown = []
    for field in DRY_GATE_FIELDS:
        value = _truth(node.get(field))
        if value is False:
            failed.append(field)
        elif value is None:
            unknown.append(field)

    if failed:
        return ShelterOperationResult(
            NO_SHELTER_OPERATION,
            failed_fields=tuple(failed),
            unknown_fields=tuple(unknown),
        )
    if unknown:
        return ShelterOperationResult(
            UNKNOWN,
            next_level=LEVEL_0,
            unknown_fields=tuple(unknown),
        )

    highest = None
    for idx, level in enumerate(LEVELS):
        level_failed = []
        level_unknown = []
        for field in LEVEL_REQUIREMENTS[level]:
            value = _truth(node.get(field))
            if value is False:
                level_failed.append(field)
            elif value is None:
                level_unknown.append(field)

        if level_failed or level_unknown:
            if highest is None:
                # The dry gate passed but L0 cannot be claimed yet.
                return ShelterOperationResult(
                    UNKNOWN if level_unknown and not level_failed else NO_SHELTER_OPERATION,
                    next_level=level,
                    failed_fields=tuple(level_failed),
                    unknown_fields=tuple(level_unknown),
                )
            return ShelterOperationResult(
                "LEVEL_CONFIRMED",
                level=highest,
                next_level=level,
                failed_fields=tuple(level_failed),
                unknown_fields=tuple(level_unknown),
            )
        highest = level

    return ShelterOperationResult("LEVEL_CONFIRMED", level=highest, next_level=None)
