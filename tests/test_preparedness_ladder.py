"""Tests for `advice/ladder.py` + `advice/preparedness_ladder.yaml` (P-D, design
section D) and the `advice.build()`/`kb.build_answer` wiring of `prepare_steps`.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_preparedness_ladder.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import advice  # noqa: E402
import advice.ladder as ladder  # noqa: E402
import kb  # noqa: E402

_ALL_COLOURS = ("GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN")
_RANK = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}


@pytest.mark.parametrize("colour", _ALL_COLOURS)
def test_every_step_has_a_trigger_next(colour):
    steps = ladder.steps_for_colour(colour)
    assert steps, f"{colour} must carry at least one step"
    for s in steps:
        assert s.get("trigger_next"), f"{colour} step {s['id']} has no trigger_next"


@pytest.mark.parametrize("colour", ("GREEN", "YELLOW", "ORANGE", "RED"))
def test_cumulative_order_includes_every_earlier_colour(colour):
    """GREEN < YELLOW < ORANGE < RED -- a RED answer still carries every GREEN/
    YELLOW/ORANGE step id (cumulative, design section D)."""
    steps = ladder.steps_for_colour(colour)
    seen_colours = {s["colour"] for s in steps}
    for c, rank in _RANK.items():
        if rank <= _RANK[colour]:
            assert c in seen_colours, f"{colour} prepare_steps is missing every {c} step"


def test_unknown_includes_every_yellow_step_and_its_own_row():
    steps = ladder.steps_for_colour("UNKNOWN")
    ids = {s["id"] for s in steps}
    yellow_ids = {s["id"] for s in ladder.steps_for_colour("YELLOW")}
    assert yellow_ids <= ids
    assert any(s["colour"] == "UNKNOWN" for s in steps)
    # fix (current-colour-first, urgent-first): the UNKNOWN-only row is
    # now FIRST, not last -- it is the current colour's own rank, and the card's
    # `do_th` headline (`advice/card.py`) reads `prepare_steps[0]`, which must
    # never be a weaker/earlier-colour step than the answer's own colour.
    assert steps[0]["colour"] == "UNKNOWN"


@pytest.mark.parametrize("colour", ("GREEN", "YELLOW", "ORANGE", "RED"))
def test_steps_for_colour_is_current_colour_first(colour):
    """fix (do_th headline): `prepare_steps[0]` (and therefore `emergency_card.do_th`'s
    fallback) must always be a step at the answer's OWN colour rank -- never an
    earlier (weaker) colour's step, which was exactly the bug (a RED
    answer's do_th fell back to a GREEN-rank step because the old cumulative
    order started at GREEN)."""
    steps = ladder.steps_for_colour(colour)
    assert steps[0]["colour"] == colour, (
        f"{colour}: prepare_steps[0] is colour={steps[0]['colour']!r}, not the "
        "answer's own colour -- current-colour-first is broken")


def test_steps_without_official_ref_are_floodconnect():
    for step in ladder.all_steps():
        if not step.get("official_ref"):
            assert step["source_tag"] == "FLOODCONNECT", (
                f"step {step['id']} has no official_ref but source_tag="
                f"{step['source_tag']!r}")


def test_official_steps_carry_a_ref():
    for step in ladder.all_steps():
        if step["source_tag"] == "OFFICIAL":
            assert step.get("official_ref"), f"OFFICIAL step {step['id']} has no official_ref"


@pytest.mark.parametrize("colour", _ALL_COLOURS)
def test_advice_build_attaches_prepare_steps_for_the_given_colour(colour):
    out = advice.build({"colour": colour}, household=None)
    assert out["prepare_steps"] == ladder.steps_for_colour(colour)
    assert out["home_shelter"]["verdict"] == "UNKNOWN_ASK_INPUTS"
    assert out["home_shelter"]["missing_inputs"], "no household given -> every field missing"
    assert out["public_shelter"]["state"] == "OPEN"


def test_card_do_th_is_prepare_steps_zero_what_th_when_no_verdict_overrides():
    """Fix: `do_th` falls back to
    `prepare_steps[0].what_th` whenever no OTHER override applies -- including
    UNKNOWN_ASK_INPUTS at a KNOWN colour (household missing, but the colour itself
    is perfectly well known). A default `build_answer` call (no `household`)
    always gets `UNKNOWN_ASK_INPUTS`, but that is NOT the colour-UNKNOWN caution
    headline unless the colour itself is also UNKNOWN -- see
    `tests/test_emergency_card.py`'s dedicated per-colour x per-verdict headline
    tests for the full matrix, including why the caution headline used to (wrongly)
    fire here too."""
    out = kb.build_answer("sammakorn", refresh=False, verbose=True)
    jev = out["jev_decision"]
    steps = jev["advice"]["prepare_steps"]
    assert steps, "sammakorn answer must carry at least one prepare_step"
    home = jev["advice"]["home_shelter"]
    assert home["verdict"] == "UNKNOWN_ASK_INPUTS", (
        "no household given to build_answer -> UNKNOWN_ASK_INPUTS always")
    import advice.card as card_mod
    colour = jev.get("colour")
    do_th = out["emergency_card"]["do_th"]
    if colour == "UNKNOWN":
        assert do_th.startswith(card_mod._UNKNOWN_CAUTION)
    elif colour == "RED":
        # founder ruling 2026-10-06, "official order is a FLOOR": a missing
        # household (so no known official order either) never reads weaker
        # than RED itself -- RED's own ladder step ("follow the official
        # order") is never the headline here.
        assert do_th == card_mod._NO_OFFICIAL_ORDER_PHRASE
    else:
        assert not do_th.startswith(card_mod._UNKNOWN_CAUTION)
        assert do_th == steps[0]["what_th"]
