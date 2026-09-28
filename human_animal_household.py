#!/usr/bin/env python3
"""
Human-Animal Household Unit (HAHU) for FloodConnect.

A household may include animals whose food, water, medication, waste management,
containment and evacuation destination materially affect household disaster decisions.

Design rules:
- human and animal resource ledgers remain separate;
- animals are not treated as luggage;
- pet ownership never justifies keeping people in a physically unsafe location;
- if the household declares co-evacuation, destination compatibility and transport
  containment become hard movement constraints;
- no universal cat-litter/feed burn rate is invented;
- no infinite stock or infinite horizon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Optional

SUSTAINABLE = "SUSTAINABLE"
NOT_SUSTAINABLE = "NOT_SUSTAINABLE"
UNKNOWN = "UNKNOWN"

SUFFICIENT = "SUFFICIENT"
INSUFFICIENT = "INSUFFICIENT"
NOT_REQUIRED = "NOT_REQUIRED"

MODES = {
    "NONE",
    "CO_RESIDENT_CO_EVACUATING",
    "SEPARATE_VERIFIED_PLAN",
    "UNKNOWN",
}

ANIMAL_RESOURCE_FIELDS = (
    "animal_food_for_horizon",
    "animal_drinking_water_for_horizon",
    "animal_medication_for_horizon",
    "animal_waste_hygiene_for_horizon",
)

ANIMAL_FUNCTION_FIELDS = (
    "animal_containment_transport",
    "animal_identification_records",
    "animal_veterinary_support",
)

FAIL_REASON = {
    "animal_food_for_horizon": "ANIMAL_FOOD_GAP",
    "animal_drinking_water_for_horizon": "ANIMAL_DRINKING_WATER_GAP",
    "animal_medication_for_horizon": "ANIMAL_MEDICATION_GAP",
    "animal_waste_hygiene_for_horizon": "ANIMAL_WASTE_HYGIENE_GAP",
    "animal_containment_transport": "ANIMAL_CONTAINMENT_TRANSPORT_GAP",
    "animal_identification_records": "ANIMAL_IDENTIFICATION_GAP",
    "animal_veterinary_support": "ANIMAL_VETERINARY_SUPPORT_GAP",
}

UNKNOWN_REASON = {
    k: "UNKNOWN_" + FAIL_REASON[k] for k in FAIL_REASON
}


@dataclass(frozen=True)
class AnimalUnitResult:
    state: str
    reason_codes: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()
    route_needs: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "reason_codes": list(self.reason_codes),
            "gaps": list(self.gaps),
            "unknown_fields": list(self.unknown_fields),
            "route_needs": list(self.route_needs),
            "details": dict(self.details),
        }


def _state(value: Any) -> str:
    if isinstance(value, str):
        value = value.strip().upper()
    if value in {SUFFICIENT, True, "AVAILABLE", "READY", "VERIFIED"}:
        return SUFFICIENT
    if value in {INSUFFICIENT, False, "UNAVAILABLE", "FAILED", "BLOCKED"}:
        return INSUFFICIENT
    if value in {NOT_REQUIRED}:
        return NOT_REQUIRED
    return UNKNOWN


def _count_animals(profile: dict[str, Any]) -> int:
    counts = profile.get("counts") or {}
    total = 0
    if isinstance(counts, dict):
        for value in counts.values():
            try:
                total += max(0, int(value))
            except (TypeError, ValueError):
                continue
    return total


def declared_animal_count(profile: dict[str, Any]) -> int:
    explicit = profile.get("total_animals")
    if explicit is not None:
        try:
            return max(0, int(explicit))
        except (TypeError, ValueError):
            return 0
    return _count_animals(profile)


def animal_route_needs(profile: dict[str, Any]) -> tuple[str, ...]:
    if declared_animal_count(profile) <= 0:
        return ()
    mode = str(profile.get("plan_mode", "UNKNOWN")).upper()
    if mode == "CO_RESIDENT_CO_EVACUATING":
        needs = ["companion_animal_accommodation"]
        if _state(profile.get("animal_veterinary_support")) != NOT_REQUIRED:
            # Veterinary support at the destination is only a hard destination need when
            # explicitly declared by the household.
            if profile.get("veterinary_support_at_destination_required") is True:
                needs.append("veterinary_support")
        return tuple(needs)
    return ()


def evaluate_animal_unit(
    profile: dict[str, Any],
    planning_horizon_h: Optional[float],
) -> AnimalUnitResult:
    count = declared_animal_count(profile)
    if count <= 0:
        return AnimalUnitResult(SUSTAINABLE, details={"total_animals": 0})

    mode = str(profile.get("plan_mode", "UNKNOWN")).upper()
    if mode not in MODES or mode == "UNKNOWN":
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("UNKNOWN_ANIMAL_PLAN_MODE",),
            unknown_fields=("plan_mode",),
            details={"total_animals": count},
        )

    if mode == "NONE":
        # Inconsistent declaration: animals exist but household says no animal plan.
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMALS_PRESENT_WITHOUT_PLAN",),
            unknown_fields=("plan_mode",),
            details={"total_animals": count},
        )

    assessed = profile.get("assessed_horizon_h")
    if planning_horizon_h is None or planning_horizon_h <= 0:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("MISSING_PLANNING_HORIZON",),
            unknown_fields=("planning_horizon_h",),
            details={"total_animals": count},
        )
    try:
        if assessed is None or float(assessed) < float(planning_horizon_h):
            return AnimalUnitResult(
                UNKNOWN,
                reason_codes=("ANIMAL_ASSESSED_HORIZON_TOO_SHORT_OR_MISSING",),
                unknown_fields=("assessed_horizon_h",),
                details={"total_animals": count},
            )
    except (TypeError, ValueError):
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("INVALID_ANIMAL_ASSESSED_HORIZON",),
            unknown_fields=("assessed_horizon_h",),
            details={"total_animals": count},
        )

    if mode == "SEPARATE_VERIFIED_PLAN":
        separate = profile.get("separate_plan") or {}
        if (
            separate.get("verified") is True
            and separate.get("fresh") is True
            and separate.get("provider_or_destination")
        ):
            return AnimalUnitResult(
                SUSTAINABLE,
                details={
                    "total_animals": count,
                    "plan_mode": mode,
                    "separate_plan": "VERIFIED",
                },
            )
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("SEPARATE_ANIMAL_PLAN_UNVERIFIED",),
            unknown_fields=("separate_plan",),
            details={"total_animals": count, "plan_mode": mode},
        )

    gaps: list[str] = []
    unknowns: list[str] = []
    reasons: list[str] = []

    for field_name in ANIMAL_RESOURCE_FIELDS + ANIMAL_FUNCTION_FIELDS:
        # Identification may be NOT_REQUIRED only if a separate local policy explicitly says so;
        # otherwise the profile should declare its state.
        value = _state(profile.get(field_name))
        if value == INSUFFICIENT:
            gaps.append(field_name)
            reasons.append(FAIL_REASON[field_name])
        elif value == UNKNOWN:
            unknowns.append(field_name)
            reasons.append(UNKNOWN_REASON[field_name])

    # Cat litter / pee pads / bags are represented through functional waste-hygiene
    # sufficiency, not a universal amount.
    counts = profile.get("counts") or {}
    cats = int(counts.get("cat", 0) or 0) if isinstance(counts, dict) else 0
    if cats > 0 and profile.get("cats_indoor_or_shelter") is True:
        litter = _state(profile.get("cat_litter_for_horizon"))
        if litter == INSUFFICIENT:
            gaps.append("cat_litter_for_horizon")
            reasons.append("CAT_LITTER_GAP")
        elif litter == UNKNOWN:
            unknowns.append("cat_litter_for_horizon")
            reasons.append("UNKNOWN_CAT_LITTER")

    if gaps:
        return AnimalUnitResult(
            NOT_SUSTAINABLE,
            tuple(dict.fromkeys(reasons)),
            tuple(dict.fromkeys(gaps)),
            tuple(dict.fromkeys(unknowns)),
            animal_route_needs(profile),
            {"total_animals": count, "plan_mode": mode},
        )
    if unknowns:
        return AnimalUnitResult(
            UNKNOWN,
            tuple(dict.fromkeys(reasons)),
            (),
            tuple(dict.fromkeys(unknowns)),
            animal_route_needs(profile),
            {"total_animals": count, "plan_mode": mode},
        )
    return AnimalUnitResult(
        SUSTAINABLE,
        (),
        (),
        (),
        animal_route_needs(profile),
        {"total_animals": count, "plan_mode": mode},
    )


def transport_ready(profile: dict[str, Any]) -> bool:
    if declared_animal_count(profile) <= 0:
        return True
    if str(profile.get("plan_mode", "UNKNOWN")).upper() == "SEPARATE_VERIFIED_PLAN":
        separate = profile.get("separate_plan") or {}
        return separate.get("verified") is True and separate.get("fresh") is True
    return (
        _state(profile.get("animal_containment_transport")) == SUFFICIENT
        and profile.get("animal_transport_capacity_verified") is True
    )


def screen_animal_accommodation(
    node: dict[str, Any],
    profile: dict[str, Any],
) -> AnimalUnitResult:
    """Screen a destination for declared co-evacuating companion animals."""
    if declared_animal_count(profile) <= 0:
        return AnimalUnitResult(SUSTAINABLE)
    if str(profile.get("plan_mode", "UNKNOWN")).upper() != "CO_RESIDENT_CO_EVACUATING":
        return AnimalUnitResult(SUSTAINABLE)

    block = node.get("animal_accommodation")
    if not isinstance(block, dict):
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMAL_ACCOMMODATION_UNDECLARED",),
            unknown_fields=("animal_accommodation",),
        )

    if block.get("fresh") is not True or block.get("verified") is not True:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMAL_ACCOMMODATION_UNVERIFIED",),
            unknown_fields=("animal_accommodation",),
        )

    required = (
        "accepted_species",
        "animal_capacity",
        "animal_drinking_water",
        "animal_food",
        "animal_waste_management",
        "animal_containment_area",
        "separation_from_food_preparation",
    )
    unknowns = []
    gaps = []

    counts = profile.get("counts") or {}
    species_needed = {k for k, v in counts.items() if int(v or 0) > 0} if isinstance(counts, dict) else set()
    accepted = set(block.get("accepted_species") or [])
    if not species_needed.issubset(accepted):
        gaps.append("accepted_species")

    try:
        free = int(block.get("animal_capacity")) - int(block.get("animals_present", 0))
        if free < declared_animal_count(profile):
            gaps.append("animal_capacity")
    except (TypeError, ValueError):
        unknowns.append("animal_capacity")

    for field_name in required[2:]:
        state = _state(block.get(field_name))
        if state == INSUFFICIENT:
            gaps.append(field_name)
        elif state == UNKNOWN:
            unknowns.append(field_name)

    if gaps:
        return AnimalUnitResult(
            NOT_SUSTAINABLE,
            reason_codes=("ANIMAL_ACCOMMODATION_INSUFFICIENT",),
            gaps=tuple(gaps),
        )
    if unknowns:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMAL_ACCOMMODATION_UNKNOWN",),
            unknown_fields=tuple(unknowns),
        )
    return AnimalUnitResult(SUSTAINABLE)


def finite_resource_horizon_h(
    stock_units: Any,
    verified_inflow_units: Any,
    demand_units_per_day: Any,
) -> Optional[Fraction]:
    """Exact finite horizon in hours for one animal resource.

    Inputs must be finite declared numeric values in the same unit system.
    Zero/negative demand is not interpreted as infinity; return None and use NOT_REQUIRED
    explicitly in the categorical layer instead.
    """
    try:
        stock = Fraction(str(stock_units))
        inflow = Fraction(str(verified_inflow_units))
        demand = Fraction(str(demand_units_per_day))
    except (ValueError, ZeroDivisionError):
        return None
    if stock < 0 or inflow < 0 or demand <= 0:
        return None
    return (stock + inflow) * Fraction(24, 1) / demand
