#!/usr/bin/env python3
"""
Human-Animal Household Unit (HAHU) for FloodConnect.

This module separates three questions that were previously mixed:

1) ANIMAL SUSTAINMENT
   Can declared animal dependents continue safely for the planning horizon?

2) ANIMAL MOVEMENT READINESS
   If movement becomes necessary, are containment/handling/transport arrangements ready?

3) ANIMAL DESTINATION COMPATIBILITY
   Is the destination compatible with the declared animal topology?

Design rules:
- human and animal resource ledgers remain separate;
- animal resource failure can make the household unit non-sustainable, but lack of a carrier
  does not make a physically safe home non-sustainable;
- assistance animals are treated as human functional-support dependencies, not ordinary pets;
- livestock/community animals do not default to companion-animal shelter pathways;
- no universal litter/feed rate and no infinite horizon.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Optional

SUSTAINABLE = "SUSTAINABLE"
NOT_SUSTAINABLE = "NOT_SUSTAINABLE"
UNKNOWN = "UNKNOWN"

READY = "READY"
NOT_READY = "NOT_READY"

SUFFICIENT = "SUFFICIENT"
INSUFFICIENT = "INSUFFICIENT"
NOT_REQUIRED = "NOT_REQUIRED"

MODES = {
    "NONE",
    "CO_RESIDENT_CO_EVACUATING",
    "SEPARATE_VERIFIED_PLAN",
    "UNKNOWN",
}

COMPANION_SPECIES = {
    "dog", "cat", "bird", "rabbit_or_small_mammal", "reptile", "fish", "other_companion"
}
LIVESTOCK_SPECIES = {
    "cattle_or_buffalo", "pig", "goat_or_sheep", "poultry", "horse", "other_livestock"
}
COMMUNITY_SPECIES = {"community_or_stray"}

ANIMAL_SUSTAINMENT_FIELDS = (
    "animal_food_for_horizon",
    "animal_drinking_water_for_horizon",
    "animal_medication_for_horizon",
    "animal_waste_hygiene_for_horizon",
)

ANIMAL_MOVEMENT_FIELDS = (
    "animal_containment_transport",
    "animal_identification_records",
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

UNKNOWN_REASON = {k: "UNKNOWN_" + v for k, v in FAIL_REASON.items()}

# Backward-compatibility name used elsewhere in the repository.
ANIMAL_RESOURCE_FIELDS = ANIMAL_SUSTAINMENT_FIELDS


@dataclass(frozen=True)
class AnimalUnitResult:
    state: str
    reason_codes: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()
    route_needs: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def admitted(self) -> bool:
        return self.state in {SUSTAINABLE, READY}

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
    if value in {SUFFICIENT, True, "AVAILABLE", READY, "VERIFIED"}:
        return SUFFICIENT
    if value in {INSUFFICIENT, False, "UNAVAILABLE", "FAILED", "BLOCKED", NOT_READY}:
        return INSUFFICIENT
    if value == NOT_REQUIRED:
        return NOT_REQUIRED
    return UNKNOWN


def _counts(profile: dict[str, Any]) -> dict[str, int]:
    raw = profile.get("counts") or {}
    out: dict[str, int] = {}
    if not isinstance(raw, dict):
        return out
    for key, value in raw.items():
        try:
            out[str(key)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return out


def declared_animal_count(profile: dict[str, Any]) -> int:
    explicit = profile.get("total_animals")
    if explicit is not None:
        try:
            return max(0, int(explicit))
        except (TypeError, ValueError):
            return 0
    return sum(_counts(profile).values())


def classify_animal_topology(profile: dict[str, Any]) -> dict[str, Any]:
    """Classify declared animals without forcing them into a pet-shelter pathway."""
    counts = _counts(profile)
    companion = sum(v for k, v in counts.items() if k in COMPANION_SPECIES)
    livestock = sum(v for k, v in counts.items() if k in LIVESTOCK_SPECIES)
    community = sum(v for k, v in counts.items() if k in COMMUNITY_SPECIES)
    assistance = 0
    try:
        assistance = max(0, int(profile.get("assistance_animal_count", 0) or 0))
    except (TypeError, ValueError):
        assistance = 0

    # Assistance animals are a role subset, normally also represented in species counts.
    return {
        "companion_count": companion,
        "livestock_count": livestock,
        "community_count": community,
        "assistance_animal_count": assistance,
        "mixed_topology": sum(int(x > 0) for x in (companion, livestock, community)) > 1,
        "species_counts": counts,
    }


def _horizon_ok(profile: dict[str, Any], planning_horizon_h: Optional[float]) -> tuple[bool, str]:
    if planning_horizon_h is None or planning_horizon_h <= 0:
        return False, "MISSING_PLANNING_HORIZON"
    assessed = profile.get("assessed_horizon_h")
    try:
        if assessed is None or float(assessed) < float(planning_horizon_h):
            return False, "ANIMAL_ASSESSED_HORIZON_TOO_SHORT_OR_MISSING"
    except (TypeError, ValueError):
        return False, "INVALID_ANIMAL_ASSESSED_HORIZON"
    return True, ""


def evaluate_animal_sustainment(
    profile: dict[str, Any],
    planning_horizon_h: Optional[float],
) -> AnimalUnitResult:
    """Evaluate stay/sustain resources only. Movement equipment is intentionally excluded."""
    count = declared_animal_count(profile)
    topology = classify_animal_topology(profile)
    if count <= 0:
        return AnimalUnitResult(SUSTAINABLE, details={"total_animals": 0, "topology": topology})

    mode = str(profile.get("plan_mode", "UNKNOWN")).upper()
    if mode not in MODES or mode == "UNKNOWN":
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("UNKNOWN_ANIMAL_PLAN_MODE",),
            unknown_fields=("plan_mode",),
            details={"total_animals": count, "topology": topology},
        )
    if mode == "NONE":
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMALS_PRESENT_WITHOUT_PLAN",),
            unknown_fields=("plan_mode",),
            details={"total_animals": count, "topology": topology},
        )

    horizon_ok, horizon_reason = _horizon_ok(profile, planning_horizon_h)
    if not horizon_ok:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=(horizon_reason,),
            unknown_fields=("assessed_horizon_h",),
            details={"total_animals": count, "topology": topology},
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
                    "topology": topology,
                },
            )
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("SEPARATE_ANIMAL_PLAN_UNVERIFIED",),
            unknown_fields=("separate_plan",),
            details={"total_animals": count, "plan_mode": mode, "topology": topology},
        )

    gaps: list[str] = []
    unknowns: list[str] = []
    reasons: list[str] = []

    for field_name in ANIMAL_SUSTAINMENT_FIELDS:
        value = _state(profile.get(field_name))
        if value == INSUFFICIENT:
            gaps.append(field_name)
            reasons.append(FAIL_REASON[field_name])
        elif value == UNKNOWN:
            unknowns.append(field_name)
            reasons.append(UNKNOWN_REASON[field_name])

    # Veterinary support is a sustainment hard constraint only when explicitly required.
    if profile.get("veterinary_support_required") is True:
        vet = _state(profile.get("animal_veterinary_support"))
        if vet == INSUFFICIENT:
            gaps.append("animal_veterinary_support")
            reasons.append(FAIL_REASON["animal_veterinary_support"])
        elif vet == UNKNOWN:
            unknowns.append("animal_veterinary_support")
            reasons.append(UNKNOWN_REASON["animal_veterinary_support"])

    counts = _counts(profile)
    if counts.get("cat", 0) > 0 and profile.get("cats_indoor_or_shelter") is True:
        litter = _state(profile.get("cat_litter_for_horizon"))
        if litter == INSUFFICIENT:
            gaps.append("cat_litter_for_horizon")
            reasons.append("CAT_LITTER_GAP")
        elif litter == UNKNOWN:
            unknowns.append("cat_litter_for_horizon")
            reasons.append("UNKNOWN_CAT_LITTER")

    details = {"total_animals": count, "plan_mode": mode, "topology": topology}
    if gaps:
        return AnimalUnitResult(
            NOT_SUSTAINABLE,
            tuple(dict.fromkeys(reasons)),
            tuple(dict.fromkeys(gaps)),
            tuple(dict.fromkeys(unknowns)),
            animal_route_needs(profile),
            details,
        )
    if unknowns:
        return AnimalUnitResult(
            UNKNOWN,
            tuple(dict.fromkeys(reasons)),
            (),
            tuple(dict.fromkeys(unknowns)),
            animal_route_needs(profile),
            details,
        )
    return AnimalUnitResult(SUSTAINABLE, route_needs=animal_route_needs(profile), details=details)


def evaluate_animal_movement_readiness(profile: dict[str, Any]) -> AnimalUnitResult:
    """Evaluate evacuation readiness separately from stay-at-home sustainment."""
    count = declared_animal_count(profile)
    topology = classify_animal_topology(profile)
    if count <= 0:
        return AnimalUnitResult(READY, details={"total_animals": 0, "topology": topology})

    mode = str(profile.get("plan_mode", "UNKNOWN")).upper()
    if mode == "SEPARATE_VERIFIED_PLAN":
        separate = profile.get("separate_plan") or {}
        if separate.get("verified") is True and separate.get("fresh") is True:
            return AnimalUnitResult(READY, details={"plan_mode": mode, "topology": topology})
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("SEPARATE_ANIMAL_PLAN_UNVERIFIED",),
            unknown_fields=("separate_plan",),
            details={"plan_mode": mode, "topology": topology},
        )

    if mode != "CO_RESIDENT_CO_EVACUATING":
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("UNKNOWN_ANIMAL_MOVEMENT_PLAN",),
            unknown_fields=("plan_mode",),
            details={"plan_mode": mode, "topology": topology},
        )

    gaps: list[str] = []
    unknowns: list[str] = []
    reasons: list[str] = []

    for field_name in ANIMAL_MOVEMENT_FIELDS:
        value = _state(profile.get(field_name))
        if value == INSUFFICIENT:
            gaps.append(field_name)
            reasons.append(FAIL_REASON[field_name])
        elif value == UNKNOWN:
            unknowns.append(field_name)
            reasons.append(UNKNOWN_REASON[field_name])

    if profile.get("animal_transport_capacity_verified") is not True:
        unknowns.append("animal_transport_capacity_verified")
        reasons.append("ANIMAL_TRANSPORT_CAPACITY_UNVERIFIED")

    # Assistance animal handler/continuity is a human functional dependency.
    if topology["assistance_animal_count"] > 0:
        handler = _state(profile.get("assistance_animal_handler_continuity"))
        if handler == INSUFFICIENT:
            gaps.append("assistance_animal_handler_continuity")
            reasons.append("ASSISTANCE_ANIMAL_HANDLER_GAP")
        elif handler == UNKNOWN:
            unknowns.append("assistance_animal_handler_continuity")
            reasons.append("UNKNOWN_ASSISTANCE_ANIMAL_HANDLER")

    if gaps:
        return AnimalUnitResult(
            NOT_READY, tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(gaps)),
            tuple(dict.fromkeys(unknowns)), animal_route_needs(profile),
            {"topology": topology},
        )
    if unknowns:
        return AnimalUnitResult(
            UNKNOWN, tuple(dict.fromkeys(reasons)), (), tuple(dict.fromkeys(unknowns)),
            animal_route_needs(profile), {"topology": topology},
        )
    return AnimalUnitResult(READY, route_needs=animal_route_needs(profile), details={"topology": topology})


def animal_route_needs(profile: dict[str, Any]) -> tuple[str, ...]:
    """Return destination capabilities for the declared animal topology."""
    if declared_animal_count(profile) <= 0:
        return ()
    if str(profile.get("plan_mode", "UNKNOWN")).upper() != "CO_RESIDENT_CO_EVACUATING":
        return ()

    topology = classify_animal_topology(profile)
    needs: list[str] = []

    # Assistance animal access is a human-accessibility need and must not be redirected to
    # a pet-only shelter.
    if topology["assistance_animal_count"] > 0:
        needs.append("assistance_animal_access")

    companion_non_assistance = max(
        0, topology["companion_count"] - topology["assistance_animal_count"]
    )
    if companion_non_assistance > 0:
        needs.append("companion_animal_accommodation")

    if topology["livestock_count"] > 0:
        needs.append("livestock_holding")

    if topology["community_count"] > 0:
        # Community/stray animals are not assumed to travel as a private household unit.
        needs.append("community_animal_handoff")

    if profile.get("veterinary_support_at_destination_required") is True:
        needs.append("veterinary_support")

    return tuple(dict.fromkeys(needs))


def movement_route_service_needs(profile: dict[str, Any]) -> tuple[str, ...]:
    """Capabilities that must be on the human movement destination itself.

    Companion/livestock accommodation may be satisfied by a linked co-located animal node,
    so those capabilities are screened separately by screen_animal_destination().
    Assistance-animal access stays attached to the human destination.
    """
    topology = classify_animal_topology(profile)
    if (
        declared_animal_count(profile) > 0
        and str(profile.get("plan_mode", "UNKNOWN")).upper() == "CO_RESIDENT_CO_EVACUATING"
        and topology["assistance_animal_count"] > 0
    ):
        return ("assistance_animal_access",)
    return ()


def transport_ready(profile: dict[str, Any]) -> bool:
    """Backward-compatible boolean wrapper for movement readiness."""
    return evaluate_animal_movement_readiness(profile).state == READY


def _resolve_linked_animal_node(
    doc: Optional[dict[str, Any]],
    node: dict[str, Any],
) -> Optional[dict[str, Any]]:
    if not isinstance(doc, dict):
        return None
    linked = node.get("linked_animal_node")
    if not linked:
        return None
    nodes = doc.get("nodes") or {}
    candidate = nodes.get(linked)
    return candidate if isinstance(candidate, dict) else None


def _animal_block_for_destination(
    node: dict[str, Any],
    profile: dict[str, Any],
    doc: Optional[dict[str, Any]] = None,
) -> tuple[Optional[dict[str, Any]], dict[str, Any]]:
    """Return accommodation block and the node that owns it.

    Supports:
    - animal accommodation embedded in the human shelter;
    - a co-located/linked animal service node;
    - direct livestock holding node.
    """
    if isinstance(node.get("animal_accommodation"), dict):
        return node["animal_accommodation"], node

    linked = _resolve_linked_animal_node(doc, node)
    if isinstance(linked, dict) and isinstance(linked.get("animal_accommodation"), dict):
        return linked["animal_accommodation"], linked

    if "livestock_holding" in set(node.get("capabilities") or []):
        if isinstance(node.get("animal_accommodation"), dict):
            return node["animal_accommodation"], node

    return None, node


def screen_animal_destination(
    node: dict[str, Any],
    profile: dict[str, Any],
    *,
    doc: Optional[dict[str, Any]] = None,
) -> AnimalUnitResult:
    """Screen destination compatibility for companion/assistance/livestock topology."""
    if declared_animal_count(profile) <= 0:
        return AnimalUnitResult(SUSTAINABLE)
    if str(profile.get("plan_mode", "UNKNOWN")).upper() != "CO_RESIDENT_CO_EVACUATING":
        return AnimalUnitResult(SUSTAINABLE)

    topology = classify_animal_topology(profile)
    capabilities = set(node.get("services") or []) | set(node.get("capabilities") or [])

    # Assistance animals should remain with the user; destination needs access, not pet housing.
    if topology["assistance_animal_count"] > 0 and "assistance_animal_access" not in capabilities:
        return AnimalUnitResult(
            NOT_SUSTAINABLE,
            reason_codes=("ASSISTANCE_ANIMAL_ACCESS_MISSING",),
            gaps=("assistance_animal_access",),
            details={"topology": topology},
        )

    if topology["community_count"] > 0 and "community_animal_handoff" not in capabilities:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("COMMUNITY_ANIMAL_HANDOFF_UNRESOLVED",),
            unknown_fields=("community_animal_handoff",),
            details={"topology": topology},
        )

    companion_non_assistance = max(
        0, topology["companion_count"] - topology["assistance_animal_count"]
    )
    needs_accommodation = companion_non_assistance > 0 or topology["livestock_count"] > 0
    if not needs_accommodation:
        return AnimalUnitResult(SUSTAINABLE, details={"topology": topology})

    required_cap = "livestock_holding" if topology["livestock_count"] > 0 else "companion_animal_accommodation"
    if required_cap not in capabilities:
        linked = _resolve_linked_animal_node(doc, node)
        linked_caps = set(linked.get("capabilities") or []) if isinstance(linked, dict) else set()
        if required_cap not in linked_caps:
            return AnimalUnitResult(
                NOT_SUSTAINABLE,
                reason_codes=("ANIMAL_DESTINATION_CAPABILITY_MISSING",),
                gaps=(required_cap,),
                details={"topology": topology},
            )

    block, owner_node = _animal_block_for_destination(node, profile, doc)
    if not isinstance(block, dict):
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMAL_ACCOMMODATION_UNDECLARED",),
            unknown_fields=("animal_accommodation",),
            details={"topology": topology},
        )
    if block.get("fresh") is not True or block.get("verified") is not True:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMAL_ACCOMMODATION_UNVERIFIED",),
            unknown_fields=("animal_accommodation",),
            details={"topology": topology},
        )

    counts = _counts(profile)
    species_needed = {k for k, v in counts.items() if v > 0 and k not in COMMUNITY_SPECIES}
    accepted = set(block.get("accepted_species") or [])
    gaps: list[str] = []
    unknowns: list[str] = []

    if not species_needed.issubset(accepted):
        gaps.append("accepted_species")

    try:
        free = int(block.get("animal_capacity")) - int(block.get("animals_present", 0))
        if free < companion_non_assistance + topology["livestock_count"]:
            gaps.append("animal_capacity")
    except (TypeError, ValueError):
        unknowns.append("animal_capacity")

    for field_name in (
        "animal_drinking_water",
        "animal_food",
        "animal_waste_management",
        "animal_containment_area",
        "separation_from_food_preparation",
    ):
        value = _state(block.get(field_name))
        if value == INSUFFICIENT:
            gaps.append(field_name)
        elif value == UNKNOWN:
            unknowns.append(field_name)

    if profile.get("veterinary_support_at_destination_required") is True:
        vet_caps = set(owner_node.get("services") or []) | set(owner_node.get("capabilities") or [])
        if "veterinary_support" not in vet_caps:
            gaps.append("veterinary_support")

    details = {"topology": topology, "accommodation_node_kind": owner_node.get("kind")}
    if gaps:
        return AnimalUnitResult(
            NOT_SUSTAINABLE,
            reason_codes=("ANIMAL_ACCOMMODATION_INSUFFICIENT",),
            gaps=tuple(dict.fromkeys(gaps)),
            details=details,
        )
    if unknowns:
        return AnimalUnitResult(
            UNKNOWN,
            reason_codes=("ANIMAL_ACCOMMODATION_UNKNOWN",),
            unknown_fields=tuple(dict.fromkeys(unknowns)),
            details=details,
        )
    return AnimalUnitResult(SUSTAINABLE, details=details)


def screen_animal_accommodation(
    node: dict[str, Any],
    profile: dict[str, Any],
) -> AnimalUnitResult:
    """Backward-compatible alias."""
    return screen_animal_destination(node, profile)


def evaluate_animal_unit(
    profile: dict[str, Any],
    planning_horizon_h: Optional[float],
) -> AnimalUnitResult:
    """Backward-compatible alias; now means sustainment only."""
    return evaluate_animal_sustainment(profile, planning_horizon_h)


def finite_resource_horizon_h(
    stock_units: Any,
    verified_inflow_units: Any,
    demand_units_per_day: Any,
) -> Optional[Fraction]:
    """Exact finite horizon in hours for one animal resource.

    Zero/negative/unknown demand is not interpreted as infinity.
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
