#!/usr/bin/env python3
"""Concrete field primitive for TDLC: nearest dry interface + shared Kanban.

This module deliberately does NOT implement incident command, dispatch authority, or
automatic allocation. It operationalises the minimum shared field state needed for
distributed responders to see the same picture:

    NEED   -- where/what/how much/by when
    SUPPLY -- who has what/how much/what mode
    ROUTE  -- which transfer/distribution path is currently usable

The board is anchored at a verified dry interface node that is reachable from both the
provider side and the community distribution side. "Nearest" is claimed only when all
otherwise-eligible candidates have comparable declared distance; unresolved candidates
preserve UNKNOWN rather than being silently ignored.
"""

from dataclasses import dataclass, asdict
from math import isfinite
from typing import Any, Iterable, Optional

import shelter_operation_ladder as so

SELECTED = "SELECTED"
UNKNOWN = "UNKNOWN"
NO_FEASIBLE_INTERFACE = "NO_FEASIBLE_INTERFACE"

CARD_NEED = "NEED"
CARD_SUPPLY = "SUPPLY"
CARD_ROUTE = "ROUTE"
CARD_KINDS = (CARD_NEED, CARD_SUPPLY, CARD_ROUTE)

OPEN = "OPEN"
CLAIMED = "CLAIMED"
DONE = "DONE"
BLOCKED = "BLOCKED"
CARD_STATES = (OPEN, CLAIMED, DONE, BLOCKED)

PRIVATE_KEYS = {
    "name", "full_name", "phone", "diagnosis", "exact_address",
    "house_number", "room_number", "personal_id",
}


@dataclass(frozen=True)
class InterfaceSelection:
    state: str
    node_id: Optional[str] = None
    distance_to_affected_m: Optional[float] = None
    reason_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finite_nonnegative(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(out) or out < 0:
        return None
    return out


def select_nearest_dry_interface(candidates: Iterable[dict[str, Any]]) -> InterfaceSelection:
    """Select the nearest node that is already a verified SO-L0 dry interface.

    Shelter-operation capability is the gate.  A candidate is eligible only when
    shelter_operation_ladder confirms SO-L0 or higher. UNKNOWN shelter-operation
    evidence preserves UNKNOWN here rather than being silently ignored.
    """

    known: list[tuple[float, str]] = []
    unresolved = False

    for raw in candidates:
        assessment = so.evaluate_shelter_operation(raw)

        if assessment.level is None:
            if assessment.state == so.UNKNOWN:
                unresolved = True
            # Explicit hard-gate failure is ineligible, not an UNKNOWN candidate.
            continue

        node_id = raw.get("node_id")
        distance = _finite_nonnegative(raw.get("distance_to_affected_m"))
        if not node_id or distance is None:
            unresolved = True
            continue
        known.append((distance, str(node_id)))

    if unresolved:
        return InterfaceSelection(
            UNKNOWN,
            reason_codes=("UNRESOLVED_SO_L0_INTERFACE_CANDIDATE",),
        )

    if not known:
        return InterfaceSelection(
            NO_FEASIBLE_INTERFACE,
            reason_codes=("NO_VERIFIED_DRY_SO_L0_INTERFACE",),
        )

    distance, node_id = min(known, key=lambda x: (x[0], x[1]))
    return InterfaceSelection(
        SELECTED,
        node_id=node_id,
        distance_to_affected_m=distance,
    )


def validate_card(card: dict[str, Any]) -> tuple[bool, tuple[str, ...]]:
    """Validate only the minimal shared-board shape; this is not a dispatch rule."""

    reasons: list[str] = []
    if any(k in card for k in PRIVATE_KEYS):
        reasons.append("PRIVATE_FIELD_NOT_ALLOWED")

    kind = card.get("kind")
    if kind not in CARD_KINDS:
        reasons.append("UNKNOWN_CARD_KIND")
        return False, tuple(reasons)

    state = card.get("state", OPEN)
    if state not in CARD_STATES:
        reasons.append("UNKNOWN_CARD_STATE")

    if not card.get("card_id"):
        reasons.append("MISSING_CARD_ID")
    if not card.get("updated_at"):
        reasons.append("MISSING_UPDATED_AT")

    if kind == CARD_NEED:
        for field in ("zone_id", "resource"):
            if not card.get(field):
                reasons.append(f"MISSING_{field.upper()}")
        if _finite_nonnegative(card.get("quantity")) is None:
            reasons.append("MISSING_OR_INVALID_QUANTITY")

    elif kind == CARD_SUPPLY:
        for field in ("provider_id", "resource", "at_node"):
            if not card.get(field):
                reasons.append(f"MISSING_{field.upper()}")
        if _finite_nonnegative(card.get("quantity")) is None:
            reasons.append("MISSING_OR_INVALID_QUANTITY")

    elif kind == CARD_ROUTE:
        for field in ("from_node", "to_zone"):
            if not card.get(field):
                reasons.append(f"MISSING_{field.upper()}")
        if card.get("verified") is not True:
            reasons.append("ROUTE_UNVERIFIED")
        if card.get("fresh") is not True:
            reasons.append("ROUTE_STALE_OR_UNKNOWN")
        if card.get("status") not in {"OPEN", "ASSISTED"}:
            reasons.append("ROUTE_NOT_USABLE")

    return not reasons, tuple(reasons)


def project_kanban(cards: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Return the three shared information lanes without auto-assignment."""

    board: dict[str, list[dict[str, Any]]] = {
        CARD_NEED: [],
        CARD_SUPPLY: [],
        CARD_ROUTE: [],
        "INVALID": [],
    }

    for raw in cards:
        card = dict(raw)
        ok, reasons = validate_card(card)
        if ok:
            card.setdefault("state", OPEN)
            board[card["kind"]].append(card)
        else:
            card["_validation_reasons"] = list(reasons)
            board["INVALID"].append(card)

    return board
