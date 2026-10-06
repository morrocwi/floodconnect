"""The preparedness ladder (P-D, design section D) -- loads
`advice/preparedness_ladder.yaml` and builds the ordered `prepare_steps` list for
one colour, per `schemas/advice.schema.json`.

Cumulative order, but CURRENT-COLOUR FIRST (urgent-first): every
step at that colour's own rank comes first (in file order), then every earlier-
colour step still relevant (so a RED answer still carries the GREEN/YELLOW/ORANGE
steps a household should already have done, in ascending-rank order among
themselves) -- a RED answer must never surface a GREEN-rank step as `prepare_steps[0]`
(and therefore as `emergency_card.do_th`), which is exactly the bug this
re-ordering fixes. UNKNOWN returns its own UNKNOWN-only row(s) FIRST, then every
YELLOW-rank-or-earlier step, per the same current-first rule (the design's
"UNKNOWN includes every YELLOW step" cumulative-coverage guarantee is unchanged --
only the ORDER changed, not the SET).

`all_steps()` (every row, every colour, in file order) is what `advice/parity.py`
checks official_guidance.yaml rows against -- a row backed at ANY colour rank is
visible to the parity check regardless of which single colour's `prepare_steps` a
particular `advice.build()` call happens to surface.
"""
from __future__ import annotations

import functools
import pathlib
import re
from typing import Any

_HERE = pathlib.Path(__file__).resolve().parent
_LADDER_PATH = _HERE / "preparedness_ladder.yaml"

_ID_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def _id_sort_key(step_id: str) -> tuple:
    """fix (founder subtractive-fix ruling 2026-10-06): `prepare_steps` ids
    (G1, G2, ..., G10, G11, ...) must sort by their NUMERIC part within one
    colour prefix, never as plain strings -- a bare string sort (the prior
    behaviour) puts "G10" before "G2" (and "O10"-"O15" before "O2"-"O9"),
    which silently reordered the compact answer's step list (U1 before G1;
    G1, G10, G11, G2, ... instead of G1, G2, ...; O1, O10, O11 -- gas
    cylinder/glass windows -- ahead of O3/O4 -- move upstairs/move
    vulnerable people first), although the docstring above promises file
    order. Falls back to a plain string key for an id that doesn't match the
    `<letters><digits>` shape (never raises)."""
    m = _ID_RE.match(step_id)
    if m:
        return (m.group(1), int(m.group(2)))
    return (step_id, 0)

# Rank order -- UNKNOWN is intentionally NOT in this dict (it is a separate,
# non-ranked bucket per the design: "cumulative order is GREEN < YELLOW < ORANGE <
# RED, and UNKNOWN includes every YELLOW step").
_RANK = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}


@functools.lru_cache(maxsize=1)
def _raw() -> dict[str, list[dict[str, Any]]]:
    import yaml
    with open(_LADDER_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    missing = {"GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"} - set(data)
    if missing:
        raise ValueError(f"advice/preparedness_ladder.yaml is missing colours: {sorted(missing)}")
    return data


def all_steps() -> list[dict[str, Any]]:
    """Every row in the ladder, in file order (GREEN, YELLOW, ORANGE, RED, UNKNOWN)
    -- used by `advice/parity.py` to check EVERY official_guidance.yaml row against
    the whole ladder, not just one colour's surfaced subset."""
    out: list[dict[str, Any]] = []
    for colour in ("GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"):
        for step in _raw().get(colour, []):
            row = dict(step)
            row["colour"] = colour
            out.append(row)
    return out


def steps_for_colour(colour: str) -> list[dict[str, Any]]:
    """The ordered `prepare_steps` for one jev_decision.colour, CURRENT-COLOUR
    FIRST (urgent-first): GREEN/YELLOW/ORANGE/RED get every step
    at their OWN rank first (file order), then every earlier-colour step still
    not done (ascending rank order among those) -- the full cumulative SET is
    unchanged from before this fix, only the ORDER is. UNKNOWN gets its own
    UNKNOWN row(s) first, then every YELLOW-rank-or-earlier step. An unrecognised
    colour (never happens from a real colour5 value) falls back to the UNKNOWN
    set -- never an empty/undefined "nothing to prepare"."""
    data = _raw()
    if colour in _RANK:
        own_rank = _RANK[colour]
        own: list[dict[str, Any]] = []
        earlier: list[dict[str, Any]] = []
        for c, rank in _RANK.items():
            if rank > own_rank:
                continue
            for step in data.get(c, []):
                row = dict(step)
                row["colour"] = c
                (own if rank == own_rank else earlier).append(row)
        own.sort(key=lambda r: _id_sort_key(r["id"]))
        earlier.sort(key=lambda r: (_RANK[r["colour"]], _id_sort_key(r["id"])))
        return own + earlier
    # UNKNOWN (or any other value) -- its own UNKNOWN-only row(s) first, then
    # every YELLOW-rank-or-earlier step.
    own = []
    for step in data.get("UNKNOWN", []):
        row = dict(step)
        row["colour"] = "UNKNOWN"
        own.append(row)
    earlier: list[dict[str, Any]] = []
    for c, rank in _RANK.items():
        if rank <= _RANK["YELLOW"]:
            for step in data.get(c, []):
                row = dict(step)
                row["colour"] = c
                earlier.append(row)
    earlier.sort(key=lambda r: (_RANK[r["colour"]], _id_sort_key(r["id"])))
    return own + earlier


def step_by_action_key(action_key: str) -> "dict[str, Any] | None":
    """The first row (file order, via `all_steps()`) carrying `action_key` --
    used by `advice/card.py` to reuse a specific ladder step's own `what_th`
    verbatim (e.g. the RED "follow official order" row) rather than a second,
    divergent copy of the same Thai text. `None` if no row carries that key
    (never fabricates one)."""
    for step in all_steps():
        if action_key in (step.get("action_keys") or []):
            return step
    return None
