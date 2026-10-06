"""Tests for `advice/card.py` and the M8 P-B `jev_decision`/`emergency_card`/
`policy_gap_ref` wiring in `kb.build_answer` (schemas/{jev_decision,emergency_card,
policy_gap_record}.schema.json, answer key order).

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_emergency_card.py -q
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import advice.card as card_mod  # noqa: E402
import advice.ladder as ladder_mod  # noqa: E402
import floodconnect_model as fm  # noqa: E402
import kb  # noqa: E402

_ALL_COLOURS = ("GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN")
_RANK = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}

# fix (do_th headline) -- every verdict `home_shelter.verdict` can actually hold, plus
# `None` for "no home_shelter block given at all" (a bare P-B/P-C-only caller).
_ALL_VERDICTS = (None, "UNKNOWN_ASK_INPUTS", "STAY_PREPARED", "PREPARE_TO_LEAVE",
                  "LEAVE_NOW", "FOLLOW_OFFICIAL_ORDER")

# Headline phrases this repo's own card never says watch-only/calm regardless of
# colour/verdict -- used by the RED/LEAVE_NOW never-watch-only test below.
_WATCH_ONLY_PHRASES = ("เฝ้าดู", "เฝ้าดูสถานการณ์", "เฝ้าระวังและติดตามสถานการณ์",
                        "ปกติ -- เฝ้าดูต่อไป")


def _schema_registry():
    from referencing import Registry, Resource
    schema_dir = HERE / "schemas"
    resources = {f.name: Resource.from_contents(json.loads(f.read_text()))
                 for f in schema_dir.glob("*.schema.json")}
    return Registry().with_resources(resources.items())


@pytest.mark.parametrize("colour", _ALL_COLOURS)
def test_card_never_drops_hotlines_or_not_official(colour):
    jev = {"colour": colour, "label_th": fm.COLOUR_LABEL_TH[colour],
           "layers": {"Z0": colour, "Z1": "UNKNOWN", "Z2": "UNKNOWN", "Z3": "UNKNOWN"}}
    card = card_mod.build_card(jev, lat=13.766, lon=100.678)
    assert card["hotlines"], "hotlines must never be dropped to make budget"
    assert card["not_official"] is True


@pytest.mark.parametrize("colour", _ALL_COLOURS)
def test_card_now_th_comes_from_the_closed_gloss_table(colour):
    jev = {"colour": colour, "label_th": fm.COLOUR_LABEL_TH[colour]}
    card = card_mod.build_card(jev)
    assert card["now_th"]


def test_card_raises_for_a_colour_outside_the_closed_vocabulary():
    with pytest.raises(KeyError):
        card_mod.build_card({"colour": "NOT_A_REAL_COLOUR"})


# ---- fix (founder ruling 2026-10-06, "official order is a FLOOR, not a ceiling") ----

def test_red_no_order_no_household_headline_moves_now_never_waits_for_order():
    """RED with no home_shelter block at all (no household declared, so this
    repo also has no official_instruction either) must never show a headline
    that reads as "wait for the official announcement" -- a missing order
    never lowers a RED point's own verdict. The headline must say to move to
    safety now and must not read as "follow the official order" alone.

    This goes through the bare-card path (no `advice` key at all), AND through
    the real `advice.build`-shaped path (a full `prepare_steps` list, no
    `home_shelter` verdict reached -- the common no-`--household` case) --
    `build_answer` always produces the latter shape, so a fix that only
    special-cased the bare dict would never actually reach a live caller."""
    bare = {"colour": "RED", "label_th": fm.COLOUR_LABEL_TH["RED"],
            "layers": {"Z0": "RED", "Z1": "UNKNOWN", "Z2": "UNKNOWN", "Z3": "UNKNOWN"}}
    with_advice = _jev_with_advice("RED", None)
    for jev in (bare, with_advice):
        card = card_mod.build_card(jev, lat=13.766, lon=100.678)
        assert card["do_th"] != "ติดตามประกาศทางการ"
        assert card["do_th"] != "ทำตามประกาศทางการ"
        assert card["do_th"] == card_mod._NO_OFFICIAL_ORDER_PHRASE
        assert "อย่ารอ" in card["do_th"]
        assert "ยังไม่มีคำสั่งทางการ" in card["do_th"]
        # the move-to-safety imperative must still be present, in `now_th`.
        assert card["now_th"] == card_mod._MOVE_NOW_NOW_TH


def test_red_no_order_choice7_moves_now_never_waits_for_order():
    """The same invariant at the jev_decision.choice level (`kb._choice_for_jev`,
    bare colour, no home-as-shelter verdict): RED's own colour-only choice must
    not be the bare "follow the official order" value -- it reuses the LEAVE_NOW
    verdict's own closed choice7 value instead."""
    assert kb._choice_for_jev("RED") == "ออกจากบ้านไปจุดปลอดภัย"
    assert kb._choice_for_jev("RED") != "ทำตามประกาศทางการ"


def test_official_warning_or_evacuate_still_wins_over_a_bare_red_choice():
    """An ACTUAL official EVACUATE/WARNING still gets the FOLLOW_OFFICIAL_ORDER
    choice verbatim -- the fix above only changes the NO-order default, never
    the case where an order genuinely exists."""
    assert kb._choice_for_jev("RED", verdict="FOLLOW_OFFICIAL_ORDER") == "ทำตามประกาศทางการ"


# ---------------------------------------------------------------------------
# fix (do_th headline): `do_th` is the most urgent action for
# the CURRENT state, not `prepare_steps[0]` of a cumulative list starting at
# GREEN. Full colour x verdict matrix below.
# ---------------------------------------------------------------------------

def _jev_with_advice(colour: str, verdict: "str | None") -> dict:
    steps = ladder_mod.steps_for_colour(colour)
    advice: dict = {"prepare_steps": steps}
    if verdict is not None:
        advice["home_shelter"] = {"verdict": verdict}
    return {"colour": colour, "label_th": fm.COLOUR_LABEL_TH[colour], "advice": advice}


@pytest.mark.parametrize("colour", _ALL_COLOURS)
@pytest.mark.parametrize("verdict", _ALL_VERDICTS)
def test_do_th_headline_rank_matches_colour_x_verdict(colour, verdict):
    """For every colour x verdict combination: the headline must never be WEAKER
    than the colour itself -- its rank must be at least the colour's own rank
    whenever the colour is KNOWN (fix: the
    caution headline used to fire on `verdict == UNKNOWN_ASK_INPUTS` alone, so a
    perfectly known RED answer with no household declared showed "ไม่ทราบ ไม่ได้
    แปลว่าปลอดภัย" -- a headline weaker than RED itself -- instead of RED's own
    step; measured at 1,042/1,042 known-colour answers in an earlier pass's live
    sweep). The caution headline is now reserved for colour == UNKNOWN, where
    there is no colour rank to be weaker than."""
    jev = _jev_with_advice(colour, verdict)
    card = card_mod.build_card(jev)
    do_th = card["do_th"]

    # Fix (founder ruling 2026-10-06, "official order is a FLOOR, not a
    # ceiling"): LEAVE_NOW and PREPARE_TO_LEAVE are only ever reached AFTER
    # `decide_home_shelter`'s own rule 1 (an actual official EVACUATE/WARNING)
    # has already failed to match -- so no order is active in either case,
    # regardless of colour, and the mandated no-order phrase is the headline.
    if verdict in ("LEAVE_NOW", "PREPARE_TO_LEAVE"):
        assert do_th == card_mod._NO_OFFICIAL_ORDER_PHRASE
        assert card["now_th"] == card_mod._MOVE_NOW_NOW_TH
        return
    if verdict == "FOLLOW_OFFICIAL_ORDER":
        expected = ladder_mod.step_by_action_key("follow_official_order")["what_th"]
        assert do_th == expected
        # An actual order never drops FloodConnect's own move-now line.
        assert card["now_th"] == card_mod._MOVE_NOW_NOW_TH
        return
    if colour == "RED":
        # A missing/late/weaker order never lowers RED below move-now, whether
        # or not a verdict was reached at all (no household, or
        # UNKNOWN_ASK_INPUTS/STAY_PREPARED -- none of these are an order).
        assert do_th == card_mod._NO_OFFICIAL_ORDER_PHRASE
        assert card["now_th"] == card_mod._MOVE_NOW_NOW_TH
        return
    if colour == "UNKNOWN":
        # No colour rank to compare against -- the caution headline is correct here
        # regardless of verdict, since the colour itself carries no real reading.
        assert do_th.startswith(card_mod._UNKNOWN_CAUTION), (
            f"colour=UNKNOWN (verdict={verdict}) must use the caution headline, "
            f"got {do_th!r}")
        return
    # colour is KNOWN and not RED here -- the caution headline must never appear.
    assert not do_th.startswith(card_mod._UNKNOWN_CAUTION), (
        f"{colour}/{verdict}: a KNOWN colour must never show the UNKNOWN caution "
        f"as its headline, got {do_th!r}")
    # STAY_PREPARED / UNKNOWN_ASK_INPUTS (colour known, non-RED) / None (no
    # home_shelter at all) -- the colour's own current-rank step, never an
    # earlier/weaker one: its rank (by construction, `steps[0]["colour"]`) must
    # equal/outrank `colour`.
    steps = jev["advice"]["prepare_steps"]
    assert do_th == steps[0]["what_th"]
    assert steps[0]["colour"] == colour, (
        f"{colour}/{verdict}: prepare_steps[0] is rank {steps[0]['colour']!r}, "
        "not the answer's own colour -- the card would say a lower-rank action "
        "than the colour/verdict calls for")
    assert _RANK[steps[0]["colour"]] >= _RANK[colour]


@pytest.mark.parametrize("verdict", ("LEAVE_NOW", None))
def test_red_leave_now_never_yields_watch_only_headline(verdict):
    """RED/LEAVE_NOW must never produce a watch-only do_th -- the exact bug
    this fix closes (the card used to say "เฝ้าดู" for a RED/LEAVE_NOW
    answer because `do_th` fell back to prepare_steps[0] of a cumulative list
    that started at GREEN)."""
    jev = _jev_with_advice("RED", verdict)
    card = card_mod.build_card(jev)
    assert card["do_th"] not in _WATCH_ONLY_PHRASES


def test_leave_now_headline_distinct_from_follow_official_order():
    """LEAVE_NOW and FOLLOW_OFFICIAL_ORDER must give DIFFERENT headlines -- a
    household told to leave now must never read the same text as a household
    told to simply follow whatever the official order says."""
    for colour in _ALL_COLOURS:
        leave_card = card_mod.build_card(_jev_with_advice(colour, "LEAVE_NOW"))
        follow_card = card_mod.build_card(_jev_with_advice(colour, "FOLLOW_OFFICIAL_ORDER"))
        assert leave_card["do_th"] != follow_card["do_th"]


def test_unknown_colour_headline_names_an_ask_step():
    """Fix: the do_th headline at colour UNKNOWN
    is now the founder's caution ALONE (not combined with the ask step's own text
    inline) -- the hard 80-token card budget leaves no room for both in one
    field. The ask-for-inputs action is still a genuine SECOND item: at colour
    UNKNOWN, `advice.ladder.steps_for_colour` surfaces its own UNKNOWN row first,
    then every GREEN step including `household_declaration` (G2) -- reachable in
    `prepare_steps`, never lost, just not crammed into `do_th` too."""
    jev = _jev_with_advice("UNKNOWN", "UNKNOWN_ASK_INPUTS")
    card = card_mod.build_card(jev)
    assert card["do_th"] == card_mod._UNKNOWN_CAUTION
    ask_step = ladder_mod.step_by_action_key("household_declaration")
    steps = jev["advice"]["prepare_steps"]
    step_ids = [s["id"] for s in steps]
    assert ask_step["id"] in step_ids, "the ask step must still be reachable in prepare_steps"


def test_unknown_ask_inputs_at_a_known_colour_never_shows_the_caution_headline():
    """Fix: UNKNOWN_ASK_INPUTS (household
    missing) at a KNOWN colour must show that colour's own current-rank step as
    its headline, never the UNKNOWN caution -- the ask-for-inputs step is still
    reachable inside the full `prepare_steps` list, just never promoted to the
    headline over a known colour's own urgency. RED is the one exception
    (founder ruling 2026-10-06, "official order is a FLOOR"): a missing
    household (so no known official order either) never reads weaker than RED
    itself, so it gets the no-order move-now headline instead of
    `prepare_steps[0]` (which would be the RED ladder's own
    "follow the official order" row)."""
    for colour in ("GREEN", "YELLOW", "ORANGE"):
        jev = _jev_with_advice(colour, "UNKNOWN_ASK_INPUTS")
        card = card_mod.build_card(jev)
        assert card_mod._UNKNOWN_CAUTION not in card["do_th"], (colour, card["do_th"])
        steps = jev["advice"]["prepare_steps"]
        assert card["do_th"] == steps[0]["what_th"]

    red_jev = _jev_with_advice("RED", "UNKNOWN_ASK_INPUTS")
    red_card = card_mod.build_card(red_jev)
    assert card_mod._UNKNOWN_CAUTION not in red_card["do_th"]
    assert red_card["do_th"] == card_mod._NO_OFFICIAL_ORDER_PHRASE
    assert red_card["now_th"] == card_mod._MOVE_NOW_NOW_TH


def test_yellow_card_uses_the_ddpm_phrase_verbatim():
    """Default rule (founder ruling 2026-10-05): YELLOW's now_th is the DDPM
    phrase 'เฝ้าระวังและติดตามสถานการณ์', kept verbatim -- never shortened/paraphrased,
    unlike every other colour's FloodConnect-own wording."""
    card = card_mod.build_card({"colour": "YELLOW", "label_th": "เฝ้าระวัง"})
    assert card["now_th"] == "เฝ้าระวังและติดตามสถานการณ์"


def test_card_measured_token_cost_per_colour():
    """MEASURED (2026-10-05, re-measured after the hard-budget fix): records the
    real cl100k token cost of a built card for every colour, with every
    documented budget-degrade step already applied by `build_card` itself. Every
    one of these must now be within `_TOKEN_BUDGET` -- see
    `test_card_hard_budget_across_full_matrix` below for the real hard gate
    across the full colour x verdict x hotline-region matrix; this one stays as
    a simple per-colour sanity measurement."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    measured = {}
    for colour in _ALL_COLOURS:
        jev = {"colour": colour, "label_th": fm.COLOUR_LABEL_TH[colour],
               "layers": {"Z0": colour, "Z1": "UNKNOWN", "Z2": "UNKNOWN", "Z3": "UNKNOWN"},
               "choice": {"chosen": "เตรียมของ"}}
        card = card_mod.build_card(jev, lat=13.766, lon=100.678)
        measured[colour] = len(enc.encode(json.dumps(card, ensure_ascii=False)))
        assert measured[colour] <= card_mod._TOKEN_BUDGET, (colour, measured[colour])
    print("DEBUG card tokens by colour:", measured)


# Portability: `pyproject.toml` only lists `tiktoken` under the `dev`
# extra -- a real self-install never gets it, so `_count_tokens`'s no-tiktoken
# fallback is this repo's actual production path for most installs, not a rare
# defensive branch. These tests simulate that absence directly (monkeypatching
# `builtins.__import__` to fail only the `tiktoken` import, leaving every other
# import working normally) rather than relying on the environment actually
# lacking it, so they run the same way in every CI environment regardless of
# whether `dev` extras happen to be installed here.
class _NoTiktoken:
    """Context manager simulating `tiktoken` not being installed by making its
    import raise `ImportError`, exactly the exception `_count_tokens`'s own
    `except Exception` already catches -- any OTHER module's import is left
    completely alone, which is why this is a plain `__import__` wrapper rather
    than removing `tiktoken` from `sys.modules` (that would also break this very
    test file's own earlier, unrelated uses of real tiktoken at collection time)."""

    def __enter__(self):
        import builtins
        self._real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "tiktoken" or name.startswith("tiktoken."):
                raise ImportError("simulated: tiktoken not installed")
            return self._real_import(name, *args, **kwargs)

        builtins.__import__ = _fake_import
        return self

    def __exit__(self, *exc):
        import builtins
        builtins.__import__ = self._real_import


def test_count_tokens_without_tiktoken_never_raises_and_stays_close():
    """Repro of the real bug: the OLD fallback (`len(text)`, 1 unit/char)
    overcounted a Thai-heavy card badly enough to raise `CardOverBudget` on a
    card that was never actually over budget. The fallback must still produce a
    number (never raise `ImportError` itself) and that number must stay within a
    bounded distance of the real tiktoken count -- not just be "a number"."""
    sample = {
        "colour": "YELLOW",
        "now_th": "เตรียมของขึ้นที่สูง ถ้ามีประกาศให้ย้าย ให้ย้ายทันที",
        "do_th": "ย้ายของขึ้นที่สูง ยังไม่มีคำสั่งทางการ — อย่ารอ",
        "hotlines": ["1784", "1137", "199"],
        "not_official": True,
        "strip": "Z0:Y Z1:G Z2:U Z3:U",
        "data_time": "2026-10-06T10:00:00Z",
    }
    # Real tiktoken count, measured BEFORE simulating its absence below.
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    real = len(enc.encode(json.dumps(sample, ensure_ascii=False)))
    old_buggy_fallback = len(json.dumps(sample, ensure_ascii=False))

    with _NoTiktoken():
        estimate, exact = card_mod._count_tokens(sample)  # must not raise ImportError
    assert exact is False

    assert estimate >= real, "a budget estimate must never UNDERcount the real tokens"
    # the real bug: the old proxy overcounted by 1.6x on exactly this kind of
    # card -- the new estimate must land much closer to the real count than that.
    assert estimate < old_buggy_fallback
    assert estimate <= real + 25, (estimate, real)


@pytest.mark.parametrize("colour", _ALL_COLOURS)
def test_build_card_never_raises_card_over_budget_without_tiktoken(colour):
    """The actual end-to-end repro: a self-install with no `dev` extra (no
    `tiktoken` at all) must be able to build every colour's card without
    `CardOverBudget` ever firing -- the same combinations
    `test_card_measured_token_cost_per_colour` already proves fit the real
    budget when tiktoken IS available."""
    jev = {"colour": colour, "label_th": fm.COLOUR_LABEL_TH[colour],
           "layers": {"Z0": colour, "Z1": "UNKNOWN", "Z2": "UNKNOWN", "Z3": "UNKNOWN"},
           "choice": {"chosen": "เตรียมของ"}}
    with _NoTiktoken():
        card = card_mod.build_card(jev, lat=13.766, lon=100.678)  # must not raise
    assert card["colour"] == colour


# fix (founder ruling "ตัดให้เหลือไม่เกิน 80"): the
# hard cap -- every colour x verdict x hotline-region combination the card can
# actually be built for, PLUS real live-built answers, must measure at or under
# `_TOKEN_BUDGET` cl100k tokens. `build_card` itself raises `CardOverBudget` if its
# own minimal (required-fields-only) card is over budget; this test additionally
# re-measures the token count directly (never trusting the absence of an
# exception alone) and fails loud with the exact combination if it ever creeps
# back over.
_HOTLINE_REGIONS = [
    (13.766, 100.678),   # Bangkok metro (Sammakorn)
    (14.0, 101.37),      # Prachinburi, outside Bangkok metro
    (None, None),        # no location given at all
]


@pytest.mark.parametrize("region", _HOTLINE_REGIONS)
@pytest.mark.parametrize("verdict", _ALL_VERDICTS)
@pytest.mark.parametrize("colour", _ALL_COLOURS)
def test_card_hard_budget_across_full_matrix(colour, verdict, region):
    jev = _jev_with_advice(colour, verdict)
    lat, lon = region
    card = card_mod.build_card(jev, lat=lat, lon=lon)  # raises CardOverBudget if over
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    n = len(enc.encode(json.dumps(card, ensure_ascii=False)))
    assert n <= card_mod._TOKEN_BUDGET, (colour, verdict, region, n, card)


def test_card_hard_budget_on_real_live_answers(tmp_path):
    """The same hard cap, measured on cards built via the real `kb.build_answer`
    path (not a synthetic jev dict passed straight to `build_card`) -- with and
    without a declared household. Uses a fresh/empty `tmp_path` DB (same
    isolation pattern this file's own `test_jev_decision_and_emergency_card_
    validate_against_schema` already uses), never the real committed
    `data/observations.sqlite` directly (that DB is WAL-mode and a bare
    read-only open against it leaves `-shm`/`-wal` side files this workspace's
    own test-isolation guard flags -- see `tools/kg/rings.py`'s own documented
    fix for the identical issue)."""
    kb.DB_PATH = tmp_path / "observations.sqlite"
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    for point in ("sammakorn", "14.0,101.37"):
        for household in (None, {
            "floors": 2, "dry_upper_floor": True, "water_vs_house_floor": "DRY",
            "official_instruction": "NONE",
            # fix (founder ruling 2026-10-06): a dynamic timestamp (never a
            # hardcoded past one, which would go stale as the suite ages) and
            # an explicit empty `member_need_profile` (declared "nobody needs
            # these things", not an absent profile, which now itself asks for
            # input) -- see advice/home_shelter.py's own fixes, same day.
            "declared_now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "member_need_profile": {},
            "test_household": True,
        }):
            out = kb.build_answer(point, refresh=False, household=household)
            card = out["emergency_card"]
            n = len(enc.encode(json.dumps(card, ensure_ascii=False)))
            assert n <= card_mod._TOKEN_BUDGET, (point, household, n, card)


def test_build_answer_key_order_and_presence(tmp_path):
    kb.DB_PATH = tmp_path / "observations.sqlite"
    payload = kb.build_answer("sammakorn", refresh=False)
    keys = list(payload)
    assert keys[0] == "emergency_card"
    assert keys[1] == "jev_decision"
    assert keys[-1] == "policy_gap_ref"
    assert "policy_gap_ref" in payload
    assert payload["policy_gap_ref"]["record_id"] is None, (
        "write_gap_log defaults to False -- no real write/record_id on a plain call")


def test_write_gap_log_true_actually_appends(tmp_path, monkeypatch):
    kb.DB_PATH = tmp_path / "observations.sqlite"
    gap_path = tmp_path / "data" / "policy_gap_log.jsonl"
    monkeypatch.setattr(kb, "HERE", tmp_path)
    payload = kb.build_answer("sammakorn", refresh=False, write_gap_log=True)
    assert payload["policy_gap_ref"]["record_id"] is not None
    assert gap_path.exists()
    lines = gap_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_write_gap_log_names_every_ring_the_kg_has_no_declared_edge_for(tmp_path, monkeypatch):
    """fix (founder ruling 2026-10-06, KG-only): a ring with no declared KG
    edge reaching it is logged by name (`KG_GAP:<ring>`), never silently
    absorbed into an UNKNOWN layer colour with no trace of why. A real DB
    (even an empty one) must actually exist for `_answer_sandwich` to reach
    the ring-colouring path at all -- an absent DB short-circuits to NO_DB
    before rings are ever read."""
    import json as _json

    import store

    db_path = tmp_path / "observations.sqlite"
    store.connect(db_path)  # creates the real (empty) sqlite file
    kb.DB_PATH = db_path
    gap_path = tmp_path / "data" / "policy_gap_log.jsonl"
    monkeypatch.setattr(kb, "HERE", tmp_path)
    kb.build_answer("sammakorn", refresh=False, write_gap_log=True)
    record = _json.loads(gap_path.read_text(encoding="utf-8").splitlines()[0])
    assert any(b.startswith("KG_GAP:") for b in record["blockers"])


def test_jev_decision_and_emergency_card_validate_against_schema(tmp_path):
    from jsonschema import Draft202012Validator
    registry = _schema_registry()
    schema_dir = HERE / "schemas"
    jev_schema = json.loads((schema_dir / "jev_decision.schema.json").read_text())
    card_schema = json.loads((schema_dir / "emergency_card.schema.json").read_text())
    jev_v = Draft202012Validator(jev_schema, registry=registry)
    card_v = Draft202012Validator(card_schema, registry=registry)

    kb.DB_PATH = tmp_path / "observations.sqlite"
    for verbose in (False, True):
        payload = kb.build_answer("sammakorn", refresh=False, verbose=verbose)
        jev_errors = list(jev_v.iter_errors(payload["jev_decision"]))
        card_errors = list(card_v.iter_errors(payload["emergency_card"]))
        assert not jev_errors, [str(e) for e in jev_errors]
        assert not card_errors, [str(e) for e in card_errors]
