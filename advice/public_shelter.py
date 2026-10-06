"""Public shelter surfacing -- P-C.

Reuses `public_shelter_seed.select_fastest_upgrade_seed` (Dry Gate + Shelter Operation
Capability Ladder + the 5-key lexicographic order) verbatim over a caller-declared site
list. `site/inputs/community/public_shelter_seeds.yaml` holds archetypes only and ZERO
real sites (VERIFIED, P-C design's own reuse inventory) -- so a default call with no
sites always returns OPEN, never a fabricated candidate.
"""
from __future__ import annotations

from typing import Any, Optional

import public_shelter_seed as pss

STATE_OPEN = "OPEN"
STATE_CANDIDATES = "CANDIDATES"

_OPEN_NOTE = (
    "no real public-shelter sites are declared yet -- ask the local อปท./ปภ. for the "
    "officially announced shelter list for this area"
)


def surface_public_shelters(
    sites: Optional[list[dict[str, Any]]] = None,
    *,
    target_level: str = pss.so.LEVEL_3,
    strategy: Optional[dict[str, Any]] = None,
    official_list_ref: Optional[str] = None,
) -> dict[str, Any]:
    """Return `advice.public_shelter` (schemas/advice.schema.json). `sites`, when
    given, is a list of real, declared public-facility candidates (never invented
    here) -- each evaluated through the exact same fail-closed Dry Gate + SO ladder a
    public-shelter promotion already requires elsewhere in this repo."""
    if not sites:
        return {"state": STATE_OPEN, "note": _OPEN_NOTE, "official_list_ref": official_list_ref}

    best = pss.select_fastest_upgrade_seed(sites, target_level=target_level, strategy=strategy)
    if best is None:
        return {"state": STATE_OPEN, "note": _OPEN_NOTE, "official_list_ref": official_list_ref}

    note = (
        f"{best.site_id} ({best.archetype}): shelter_level={best.shelter_level}, "
        f"missing_to_target={list(best.missing_to_target)}"
    )
    return {"state": STATE_CANDIDATES, "note": note, "official_list_ref": official_list_ref}
