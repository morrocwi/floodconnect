#!/usr/bin/env python3
"""Public Shelter Seed Strategy for FloodConnect.

Facility archetype is a discovery hint only. Real suitability comes from the same
fail-closed Dry Gate + Shelter Operation Capability Ladder used elsewhere.

No weighted score is used. Candidate ordering is lexicographic:
1) must pass Dry Gate / have at least SO-L0 to operate as a shelter seed;
2) must be allowed for the requested role;
3) prefer fewer missing hard capabilities to the target level;
4) then prefer verified logistics/interface access;
5) then shorter declared distance.

Hospitals and primary health centres remain health-support nodes by default; they enter
general-shelter selection only when explicitly officially designated for that use.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

import yaml

import shelter_operation_ladder as so

HERE = Path(__file__).resolve().parent
DEFAULT_STRATEGY = HERE / "site" / "inputs" / "community" / "public_shelter_seeds.yaml"


@dataclass(frozen=True)
class SeedCandidateResult:
    site_id: str
    archetype: str
    role: str
    admitted: bool
    shelter_level: Optional[str] = None
    target_level: Optional[str] = None
    missing_to_target: tuple[str, ...] = ()
    unknown_to_target: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    distance_to_affected_m: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_strategy(path: str | Path = DEFAULT_STRATEGY) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _finite_nonnegative(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out >= 0 else None


def _required_through(level: str) -> tuple[str, ...]:
    if level not in so.LEVELS:
        raise ValueError(f"unknown shelter level: {level}")
    out: list[str] = []
    for current in so.LEVELS:
        out.extend(so.LEVEL_REQUIREMENTS[current])
        if current == level:
            break
    return tuple(out)


def _facility_role(site: dict[str, Any], strategy: dict[str, Any]) -> tuple[str, bool]:
    archetype = site.get("archetype")
    definition = (strategy.get("archetypes") or {}).get(archetype) or {}
    role = definition.get("default_role", "unknown")

    if archetype in {"hospital", "primary_health_center"}:
        if site.get("officially_designated_general_shelter") is True:
            return "shelter_seed", True
        return role, False

    return role, role == "shelter_seed"


def evaluate_seed_candidate(
    site: dict[str, Any],
    *,
    target_level: str = so.LEVEL_3,
    strategy: Optional[dict[str, Any]] = None,
) -> SeedCandidateResult:
    """Evaluate one public-facility candidate without archetype-based safety inference."""

    strategy = strategy or load_strategy()
    site_id = str(site.get("site_id") or "")
    archetype = str(site.get("archetype") or "")
    definitions = strategy.get("archetypes") or {}

    if not site_id:
        return SeedCandidateResult(
            site_id="",
            archetype=archetype,
            role="unknown",
            admitted=False,
            target_level=target_level,
            reason_codes=("MISSING_SITE_ID",),
        )
    if archetype not in definitions:
        return SeedCandidateResult(
            site_id=site_id,
            archetype=archetype,
            role="unknown",
            admitted=False,
            target_level=target_level,
            reason_codes=("UNKNOWN_ARCHETYPE",),
        )

    role, allowed_general_shelter = _facility_role(site, strategy)

    assessment = so.evaluate_shelter_operation(site)
    if assessment.level is None:
        return SeedCandidateResult(
            site_id=site_id,
            archetype=archetype,
            role=role,
            admitted=False,
            shelter_level=None,
            target_level=target_level,
            reason_codes=("DRY_GATE_OR_SO_L0_NOT_CONFIRMED",),
            distance_to_affected_m=_finite_nonnegative(site.get("distance_to_affected_m")),
        )

    if not allowed_general_shelter:
        return SeedCandidateResult(
            site_id=site_id,
            archetype=archetype,
            role=role,
            admitted=False,
            shelter_level=assessment.level,
            target_level=target_level,
            reason_codes=("SUPPORT_NODE_NOT_GENERAL_SHELTER",),
            distance_to_affected_m=_finite_nonnegative(site.get("distance_to_affected_m")),
        )

    missing: list[str] = []
    unknown: list[str] = []
    for field in _required_through(target_level):
        value = so._requirement_truth(site, field)
        if value is False:
            missing.append(field)
        elif value is None:
            unknown.append(field)

    return SeedCandidateResult(
        site_id=site_id,
        archetype=archetype,
        role=role,
        admitted=True,
        shelter_level=assessment.level,
        target_level=target_level,
        missing_to_target=tuple(missing),
        unknown_to_target=tuple(unknown),
        distance_to_affected_m=_finite_nonnegative(site.get("distance_to_affected_m")),
    )


def select_fastest_upgrade_seed(
    sites: list[dict[str, Any]],
    *,
    target_level: str = so.LEVEL_3,
    strategy: Optional[dict[str, Any]] = None,
) -> Optional[SeedCandidateResult]:
    """Select a defensible seed by hard-gate + lexicographic capability gap.

    No archetype is automatically selected. Public-school preference exists only as a
    discovery order upstream; once real field evidence is available, actual hard gaps win.
    """

    strategy = strategy or load_strategy()
    candidates = [
        evaluate_seed_candidate(site, target_level=target_level, strategy=strategy)
        for site in sites
    ]
    admitted = [x for x in candidates if x.admitted]
    if not admitted:
        return None

    def key(result: SeedCandidateResult):
        site = next(x for x in sites if str(x.get("site_id") or "") == result.site_id)
        provider = site.get("provider_access_verified") is True
        community = site.get("community_distribution_access_verified") is True
        distance = result.distance_to_affected_m
        return (
            len(result.missing_to_target),
            len(result.unknown_to_target),
            0 if provider and community else 1,
            float("inf") if distance is None else distance,
            result.site_id,
        )

    return min(admitted, key=key)
