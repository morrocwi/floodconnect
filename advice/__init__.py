"""The M8 advice layer: emergency_card (advice/card.py), the policy gap log
(advice/gap_log.py), the home-as-shelter bridge (advice/home_shelter.py, P-C), the
public-shelter surfacer (advice/public_shelter.py, P-C), and -- P-D, this module's
own `build()` -- the preparedness ladder (advice/ladder.py +
advice/preparedness_ladder.yaml) and the official-parity check (advice/parity.py).

`build(jev, household=None)` is the one wiring point `kb.py:build_answer` calls
(design: `kb.build_answer -> _answer_sandwich -> advice.build(jev,
household=None|decl) -> jev_decision.advice -> card -> gap_log`). It returns the
`advice` object `schemas/advice.schema.json` describes: `prepare_steps` (ordered,
by `jev["colour"]`), `home_shelter` (the stay-vs-go verdict -- `UNKNOWN_ASK_INPUTS`
with every required field listed as missing when no household declaration was
given at all, never a silent STAY), and `public_shelter` (OPEN while this repo
declares zero real public-shelter sites).
"""
from __future__ import annotations

from typing import Any, Optional

import advice.home_shelter as home_shelter
import advice.ladder as ladder
import advice.public_shelter as public_shelter


def build(jev: Optional[dict[str, Any]], household: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """`jev` is a `jev_decision`-shaped dict (at least `colour`); `household` is a
    `schemas/household_declaration.schema.json`-shaped dict, or `None` when the
    caller gave no declaration at all this call -- that is NOT the same as a
    declaration missing one or two fields (`home_shelter.decide_home_shelter`
    already handles that case via `_missing_required`): a wholly absent household
    is every required field missing."""
    colour = (jev or {}).get("colour") or "UNKNOWN"
    prepare_steps = ladder.steps_for_colour(colour)

    if household is None:
        home = {
            "verdict": home_shelter.VERDICT_UNKNOWN_ASK_INPUTS,
            "dry_gate": {"state": "UNKNOWN", "failed": [], "unknown": []},
            "sustainment": {"state": "UNKNOWN", "gaps": [], "unknown": []},
            "missing_inputs": list(home_shelter.REQUIRED_HOUSEHOLD_FIELDS),
            "checklist": [],
            "protective_state_raw": None,
        }
    else:
        home = home_shelter.decide_home_shelter(household, jev)

    public = public_shelter.surface_public_shelters()

    return {
        "prepare_steps": prepare_steps,
        "home_shelter": home,
        "public_shelter": public,
    }
