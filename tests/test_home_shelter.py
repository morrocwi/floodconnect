"""Tests for `advice.home_shelter` -- P-C, the home-as-shelter (stay-vs-go) adapter.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_home_shelter.py -q
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import kb  # noqa: E402
import store  # noqa: E402
import advice.home_shelter as hs  # noqa: E402

# A test household (schemas/household_declaration.schema.json's own
# `test_household` field) -- never a real person's data.
H2_SUSTAINED = {
    "floors": 2,
    "dry_upper_floor": True,
    "water_vs_house_floor": "DRY",
    "panel_above_current_water": True,
    "can_cut_power": True,
    "member_need_profile": {"total_persons": 2},
    # Founder ruling 2026-10-06: an explicit "checked, no animals" declaration -- kept in this
    # "complete declaration" fixture so the many tests built on it stay at full
    # confidence; see the dedicated animal_profile tests below for the missing case.
    "animal_profile": {},
    "supplies": {
        "potable_water_days": 5,
        "food_days": 5,
        "essential_medicine_days": 5,
        "service_water_days": 5,
        "sanitation_hygiene_days": 5,
    },
    "planning_horizon_h": 48,
    "communications": {"available": True},
    "exit": {"boat": False, "route_declared": True},
    "official_instruction": "NONE",
    # fix (founder ruling 2026-10-06): `_is_fresh_declaration` compares
    # `declared_now` against the real wall clock now (a staleness window) --
    # a hardcoded past timestamp would silently go stale as the test suite
    # ages. Computed fresh at import time instead.
    "declared_now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "test_household": True,
}


def _decl(**overrides):
    out = dict(H2_SUSTAINED)
    out.update(overrides)
    return out


# ---- rule 2: missing required input never becomes STAY ----------------------------

@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"])
@pytest.mark.parametrize("field", hs.REQUIRED_HOUSEHOLD_FIELDS)
def test_missing_any_input_never_stay(field, colour):
    decl = _decl()
    del decl[field]
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert field in out["missing_inputs"]
    assert out["verdict"] != hs.VERDICT_STAY_PREPARED


# ---- rules 6-9 unified gate: an UNKNOWN Dry Gate/sustainment/official_instruction --
# -- never a silent STAY --

_MINIMAL_REQUIRED_ONLY = {
    "floors": 2,
    "dry_upper_floor": True,
    "water_vs_house_floor": "DRY",
    "official_instruction": "NONE",
    # fix (founder ruling 2026-10-06): `_is_fresh_declaration` compares
    # `declared_now` against the real wall clock now (a staleness window) --
    # a hardcoded past timestamp would silently go stale as the test suite
    # ages. Computed fresh at import time instead.
    "declared_now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "test_household": True,
}


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "UNKNOWN"])
def test_minimal_declaration_dry_gate_or_sustainment_unknown_never_stay(colour):
    """Reproduces a measured bug: a declaration with ONLY the
    required fields (no `supplies`/`communications`/`panel_above_current_water`/
    `can_cut_power` at all) leaves the Dry Gate's `immediate_site_hazard_safe` and
    every sustainment resource field UNKNOWN -- this used to return STAY_PREPARED
    at every one of these colours (rule 7 never checked the Dry Gate; rule 9 never
    checked anything). It must now ask instead, and name what it is missing."""
    out = hs.decide_home_shelter(dict(_MINIMAL_REQUIRED_ONLY), {"colour": colour})
    assert out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert out["missing_inputs"], "must name the specific unknown field(s)"
    assert out["verdict"] != hs.VERDICT_STAY_PREPARED


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "UNKNOWN"])
def test_official_instruction_unknown_never_stay_silently(colour):
    """Real repro, 2026-10-05: `official_instruction="UNKNOWN"` (a
    valid declared value distinct from NONE/EVACUATE) used to still return
    STAY_PREPARED. It is itself an UNKNOWN input and must trigger the ask, not a
    silent STAY -- FloodConnect never assumes "no order" when the household
    plainly said it does not know."""
    decl = _decl(official_instruction="UNKNOWN")
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert "official_instruction" in out["missing_inputs"]
    assert out["verdict"] != hs.VERDICT_STAY_PREPARED


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "UNKNOWN"])
def test_known_supply_gap_gives_prepare_to_leave_never_stay(colour):
    """Real repro, 2026-10-05: supplies of 0.5 days against a 72 h
    planning horizon is a KNOWN, real gap (NOT_SUSTAINABLE) -- this is not an
    unknown, so the correct verdict is PREPARE_TO_LEAVE (never STAY_PREPARED, and
    never an ask for input the household already gave)."""
    decl = _decl(
        planning_horizon_h=72,
        supplies={"potable_water_days": 0.5, "food_days": 0.5,
                  "essential_medicine_days": 0.5, "service_water_days": 0.5,
                  "sanitation_hygiene_days": 0.5},
    )
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["sustainment"]["state"] == "NOT_SUSTAINABLE"
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE


def test_empty_declaration_is_unknown_ask_inputs():
    out = hs.decide_home_shelter({}, {"colour": "GREEN"})
    assert out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert set(out["missing_inputs"]) == set(hs.REQUIRED_HOUSEHOLD_FIELDS)
    assert out["checklist"] == []


# ---- rule 1: official order always wins --------------------------------------------

@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"])
def test_official_order_wins_over_every_colour_and_household(colour):
    decl = _decl(official_instruction="EVACUATE")
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["verdict"] == hs.VERDICT_FOLLOW_OFFICIAL_ORDER


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"])
def test_official_warning_also_wins_over_every_colour(colour):
    """Fix: an official WARNING instruction
    (prd.go.th/534015, OG-25: evacuate immediately on a warning signal, do not
    wait for crisis level) folds into the same outcome as EVACUATE -- never read
    as merely NONE."""
    decl = _decl(official_instruction="WARNING")
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["verdict"] == hs.VERDICT_FOLLOW_OFFICIAL_ORDER


def test_official_order_wins_even_with_dry_gate_fail():
    decl = _decl(official_instruction="EVACUATE", dry_upper_floor=False,
                  water_vs_house_floor="ABOVE_FLOOR")
    out = hs.decide_home_shelter(decl, {"colour": "RED"})
    assert out["verdict"] == hs.VERDICT_FOLLOW_OFFICIAL_ORDER


# ---- rule 3: dry gate fail ----------------------------------------------------------

def test_dry_gate_fail_gives_leave_now():
    decl = _decl(dry_upper_floor=False, water_vs_house_floor="ABOVE_FLOOR",
                  panel_above_current_water=False, can_cut_power=False)
    out = hs.decide_home_shelter(decl, {"colour": "YELLOW"})
    assert out["dry_gate"]["state"] == "FAIL"
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW


# ---- rules 4/5: RED ------------------------------------------------------------------

def test_red_no_dry_upper_floor_gives_leave_now():
    decl = _decl(dry_upper_floor=False, water_vs_house_floor="BELOW_FLOOR_RISING")
    out = hs.decide_home_shelter(decl, {"colour": "RED"})
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW


def test_red_uncovered_medical_dependency_gives_leave_now():
    decl = _decl(member_need_profile={
        "total_persons": 1,
        "needs_time_critical_medical_followup": 1,
        "medical_support_link_uncovered": 1,
    })
    out = hs.decide_home_shelter(decl, {"colour": "RED"})
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW


def test_red_with_dry_upper_and_covered_dependency_gives_prepare_to_leave():
    out = hs.decide_home_shelter(_decl(), {"colour": "RED"})
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE


# ---- rule 6/7: ORANGE -----------------------------------------------------------------

def test_orange_sustainable_with_dry_upper_gives_stay_prepared():
    out = hs.decide_home_shelter(_decl(), {"colour": "ORANGE"})
    assert out["verdict"] == hs.VERDICT_STAY_PREPARED
    assert out["checklist"]


@pytest.mark.parametrize(
    "colour,builder,expected_verdict",
    [
        ("RED", lambda: _decl(dry_upper_floor=False, water_vs_house_floor="ABOVE_FLOOR"), None),
        ("RED", lambda: _decl(), hs.VERDICT_PREPARE_TO_LEAVE),
        ("GREEN", lambda: _decl(), hs.VERDICT_STAY_PREPARED),
        ("UNKNOWN", lambda: _decl(), hs.VERDICT_UNKNOWN_ASK_INPUTS),
        ("GREEN", lambda: _decl(supplies={"potable_water_days": 0}), hs.VERDICT_PREPARE_TO_LEAVE),
    ],
)
def test_rules_4_to_9_verdicts_carry_the_pending_founder_tag(colour, builder, expected_verdict):
    """Fix: every verdict reached via rules 4-9
    (this repo's OWN escalation defaults, never founder-dictated) carries
    `rule`/`tag: FLOODCONNECT_DEFAULT_PENDING_FOUNDER` -- rules 1 (official order)
    and 3 (Dry Gate FAIL) are structural safety invariants and never carry it.
    UNKNOWN colour with a complete household (S4, founder subtractive-fix ruling
    2026-10-06) is a structural ask, not a rules-4-9 default, and never carries it
    either -- same shape as the missing-required-input early return."""
    out = hs.decide_home_shelter(builder(), {"colour": colour})
    if expected_verdict is not None:
        assert out["verdict"] == expected_verdict
    assert out["verdict"] not in (hs.VERDICT_FOLLOW_OFFICIAL_ORDER,)
    if out["verdict"] == hs.VERDICT_LEAVE_NOW and colour == "RED" and out["dry_gate"]["state"] == "FAIL":
        assert "tag" not in out  # rule 3, a safety invariant, never tagged
        return
    if out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS:
        assert "tag" not in out  # a structural ask, never tagged
        return
    assert out.get("tag") == "FLOODCONNECT_DEFAULT_PENDING_FOUNDER"
    assert out.get("rule", "").startswith("R")


def test_orange_no_dry_upper_floor_fails_dry_gate_first_and_gives_leave_now():
    """No dry upper floor at all means `dry_operating_surface` is False, so the Dry
    Gate (rule 3) fires before rule 6 ever gets a chance to -- there is no dry refuge
    to "prepare and stay" in, at any colour."""
    decl = _decl(dry_upper_floor=False, water_vs_house_floor="BELOW_FLOOR_RISING")
    out = hs.decide_home_shelter(decl, {"colour": "ORANGE"})
    assert out["dry_gate"]["state"] == "FAIL"
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW


def test_orange_not_sustainable_gives_prepare_to_leave():
    decl = _decl(supplies={"potable_water_days": 0})
    out = hs.decide_home_shelter(decl, {"colour": "ORANGE"})
    assert out["sustainment"]["state"] == "NOT_SUSTAINABLE"
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE


# ---- rule 7/8: GREEN/YELLOW -------------------------------------------------------------

@pytest.mark.parametrize("colour", ["GREEN", "YELLOW"])
def test_green_yellow_sustainable_gives_stay_prepared(colour):
    out = hs.decide_home_shelter(_decl(), {"colour": colour})
    assert out["verdict"] == hs.VERDICT_STAY_PREPARED


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW"])
def test_green_yellow_supply_gap_gives_prepare_to_leave(colour):
    decl = _decl(supplies={"potable_water_days": 0, "food_days": 5,
                            "essential_medicine_days": 5, "service_water_days": 5,
                            "sanitation_hygiene_days": 5})
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert "potable_water_for_horizon" in out["sustainment"]["gaps"]
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE


# ---- rule 9: UNKNOWN colour ----------------------------------------------------------

def test_unknown_colour_complete_inputs_gives_unknown_ask_inputs_never_stay():
    """Colour UNKNOWN never gives STAY, even with every household input known --
    the unknown here is the flood STATE itself, not the household. (Inverts
    the prior test, which asserted STAY_PREPARED.)"""
    out = hs.decide_home_shelter(_decl(), {"colour": "UNKNOWN"})
    assert out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert out["missing_inputs"] == ["flood_state"]


def test_no_jev_at_all_treated_as_unknown_colour_never_stay():
    out = hs.decide_home_shelter(_decl(), None)
    assert out["verdict"] == hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert out["missing_inputs"] == ["flood_state"]


def test_unknown_colour_with_known_sustainment_gap_gives_prepare_to_leave():
    """A KNOWN household gap (NOT_SUSTAINABLE) at colour UNKNOWN must still give
    PREPARE_TO_LEAVE, at LOW confidence, never STAY and never a repeated ask for
    input that is already known."""
    decl = _decl(supplies={"potable_water_days": 0.5, "food_days": 0.5,
                            "essential_medicine_days": 0.5, "service_water_days": 0.5,
                            "sanitation_hygiene_days": 0.5})
    out = hs.decide_home_shelter(decl, {"colour": "UNKNOWN"})
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE
    assert out["confidence"] == "LOW"


# ---- invariant 9: a canal reading never becomes a house depth -----------------------

def test_canal_reading_never_becomes_house_depth():
    """`sandwich_to_forward_hazard` must only ever carry the COLOUR-derived forward
    hazard state/mobility flag -- never a depth/value field -- and
    `household_to_node`'s own dry/physical-safety fields must come only from the
    household's OWN declared `water_vs_house_floor`, never from `jev`/`z0`."""
    jev_red_with_value = {
        "colour": "RED", "z0": {"fresh": True, "value": 9.99, "trend": "RISING"},
    }
    forward = hs.sandwich_to_forward_hazard(jev_red_with_value)
    assert set(forward) <= {"state", "fresh", "horizon_h", "mobility_window_closing"}
    assert "value" not in forward and "h" not in forward and "depth" not in forward

    decl_dry = _decl(water_vs_house_floor="DRY")
    node_dry = hs.household_to_node(decl_dry)
    decl_above = _decl(water_vs_house_floor="ABOVE_FLOOR")
    node_above = hs.household_to_node(decl_above)
    # Same jev (RED, value=9.99) in both cases -- only the household's OWN declared
    # water_vs_house_floor may change the Dry-Gate-relevant fields.
    assert node_dry["drainage_not_blocking_operation"] is True
    assert node_above["drainage_not_blocking_operation"] is False
    assert node_dry["sustainment"]["physical_safety"] != node_above["sustainment"]["physical_safety"]


def test_sandwich_to_forward_hazard_unknown_colour_gives_absent_block():
    assert hs.sandwich_to_forward_hazard({"colour": "UNKNOWN"}) == {}
    assert hs.sandwich_to_forward_hazard(None) == {}


def test_sandwich_to_forward_hazard_colour_map():
    assert hs.sandwich_to_forward_hazard({"colour": "GREEN"})["state"] == "NONE"
    assert hs.sandwich_to_forward_hazard({"colour": "YELLOW"})["state"] == "WATCH"
    assert hs.sandwich_to_forward_hazard({"colour": "ORANGE"})["state"] == "HIGH"
    assert hs.sandwich_to_forward_hazard({"colour": "RED"})["state"] == "ACTIVE"
    assert hs.sandwich_to_forward_hazard({"colour": "RED"})["mobility_window_closing"] is True


def test_orange_water_coming_sets_mobility_window_closing():
    jev = {"colour": "ORANGE", "why": ["WATER_COMING_ON_KG_PATH"]}
    out = hs.sandwich_to_forward_hazard(jev)
    assert out["mobility_window_closing"] is True


# ---- golden case: real WL.SMK.01 row -------------------------------------------------

NOW = datetime.datetime.fromisoformat("2026-10-05T06:20:00+00:00")

REAL_SMK01_STABLE_ROW = dict(
    source_id="bma_watermap", station_code="WL.SMK.01",
    station_name="จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2",
    lat=13.76676, lon=100.67784, variable="canal_water_level_m", value=-0.48, unit="m",
    observed_at_utc="2026-10-05T06:10:00+00:00", fetched_at_utc="2026-10-05T06:13:13+00:00",
    warning=0.35, critical=0.44, bank=None, status="ปกติ", trust_tier="official_telemetry",
)


@pytest.fixture
def sandwich_db(tmp_path, monkeypatch):
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    return conn


def test_golden_sammakorn_real_row_green_household_stays_prepared(sandwich_db):
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer)
    assert jev["colour"] == "GREEN"
    out = hs.decide_home_shelter(_decl(), jev)
    assert out["verdict"] == hs.VERDICT_STAY_PREPARED
    assert out["dry_gate"]["state"] == "PASS"


# ---- schema validation -----------------------------------------------------------

def _home_shelter_validator():
    import json

    import jsonschema

    with open(HERE / "schemas" / "defs.schema.json", encoding="utf-8") as f:
        defs = json.load(f)
    with open(HERE / "schemas" / "advice.schema.json", encoding="utf-8") as f:
        advice_schema = json.load(f)
    resolver = jsonschema.validators.RefResolver.from_schema(
        advice_schema, store={defs["$id"]: defs}
    )
    return jsonschema.Draft202012Validator(
        advice_schema["properties"]["home_shelter"], resolver=resolver
    )


def _household_declaration_validator():
    import json

    import jsonschema

    with open(HERE / "schemas" / "household_declaration.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    return jsonschema.Draft202012Validator(schema)


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"])
def test_home_shelter_output_validates_against_schema(colour):
    validator = _home_shelter_validator()
    validator.validate(hs.decide_home_shelter(_decl(), {"colour": colour}))


def test_unknown_ask_inputs_output_validates_against_schema():
    validator = _home_shelter_validator()
    validator.validate(hs.decide_home_shelter({}, {"colour": "GREEN"}))


def test_test_household_declaration_itself_validates_against_schema():
    _household_declaration_validator().validate(_decl())


# ---- Founder ruling 2026-10-06: absent member_need_profile lowers
# ---- confidence with a reason, never asks, and never STAYs. This supersedes the
# ---- earlier "absent member_need_profile asks, never STAYs" fix (which used to
# ---- return UNKNOWN_ASK_INPUTS here) -- the founder's newer ruling wants an
# ---- actual answer, at a lowered confidence, instead of a blocked one.

@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE"])
def test_absent_member_need_profile_lowers_confidence_with_reason_never_stay(colour):
    """An entirely absent `member_need_profile` (the key never given at all) must
    still reach a verdict -- never UNKNOWN_ASK_INPUTS, never STAY_PREPARED -- at a
    lowered confidence, with the plain-Thai reason named in `calc.reasons`."""
    decl = dict(_decl())
    del decl["member_need_profile"]
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["verdict"] != hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert out["verdict"] != hs.VERDICT_STAY_PREPARED
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE
    assert out["confidence"] in ("MEDIUM", "LOW", "NONE")
    assert "member_need_profile" in out["calc"]["missing"]
    assert hs.REASON_MISSING_VULNERABLE_TH in out["calc"]["reasons"]


@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE"])
def test_complete_member_need_profile_keeps_full_confidence_no_reason(colour):
    """With `member_need_profile` actually declared (even `{}`), the downgrade above
    never fires -- confidence stays at the HIGH default (key absent from the
    output, same never-a-placeholder convention as elsewhere in this repo) and
    `calc.missing`/`calc.reasons` stay empty."""
    out = hs.decide_home_shelter(_decl(), {"colour": colour})
    assert "confidence" not in out
    assert out["calc"]["missing"] == []
    assert "reasons" not in out["calc"]


def test_declared_empty_member_need_profile_is_not_the_same_as_absent():
    """A household that DECLARED an empty profile (`{}` -- "we checked, nobody
    needs these things") is real information, not a gap -- it must still be able
    to reach STAY_PREPARED, unlike the wholly absent case above."""
    decl = _decl(member_need_profile={})
    out = hs.decide_home_shelter(decl, {"colour": "GREEN"})
    assert out["verdict"] == hs.VERDICT_STAY_PREPARED
    assert "confidence" not in out


def test_absent_member_need_profile_never_reaches_stay_even_when_otherwise_sustainable():
    """Same sustainable GREEN household as the STAY_PREPARED case above, but with
    `member_need_profile` missing -- the verdict must be downgraded to
    PREPARE_TO_LEAVE, never STAY_PREPARED, per the founder ruling above."""
    decl = dict(_decl())
    del decl["member_need_profile"]
    out = hs.decide_home_shelter(decl, {"colour": "GREEN"})
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE


# ---- Founder ruling 2026-10-06, "เช่นถ้าไม่ใส่กลุ่มเปราะบาง ...
# ---- เช่น คนและสัตว์"): animal_profile is now checked the same way -- a wholly
# ---- absent profile is missing information, an explicit (even empty) one is not.

@pytest.mark.parametrize("colour", ["GREEN", "YELLOW", "ORANGE"])
def test_absent_animal_profile_lowers_confidence_with_reason_never_stay(colour):
    """An entirely absent `animal_profile` (the key never given at all, distinct
    from an explicit `{}`/0-count declaration) must still reach a verdict -- never
    UNKNOWN_ASK_INPUTS, never STAY_PREPARED -- at a lowered confidence, with the
    same plain-Thai reason named in `calc.reasons` as a missing member_need_profile."""
    decl = dict(_decl())
    del decl["animal_profile"]
    out = hs.decide_home_shelter(decl, {"colour": colour})
    assert out["verdict"] != hs.VERDICT_UNKNOWN_ASK_INPUTS
    assert out["verdict"] != hs.VERDICT_STAY_PREPARED
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE
    assert out["confidence"] in ("MEDIUM", "LOW", "NONE")
    assert "animal_profile" in out["calc"]["missing"]
    assert hs.REASON_MISSING_VULNERABLE_TH in out["calc"]["reasons"]


def test_declared_empty_animal_profile_is_not_the_same_as_absent():
    """A household that DECLARED an empty animal profile (`{}` -- "we checked, no
    animals") is real information, not a gap -- it must still be able to reach
    STAY_PREPARED at full confidence, unlike the wholly absent case above."""
    decl = _decl(animal_profile={})
    out = hs.decide_home_shelter(decl, {"colour": "GREEN"})
    assert out["verdict"] == hs.VERDICT_STAY_PREPARED
    assert "confidence" not in out


def test_declared_zero_count_animal_profile_is_not_the_same_as_absent():
    """An explicit animal profile with a declared count of 0 is the same
    "checked, none" case as `{}` -- still not missing, still full confidence."""
    decl = _decl(animal_profile={"total_animals": 0})
    out = hs.decide_home_shelter(decl, {"colour": "GREEN"})
    assert out["verdict"] == hs.VERDICT_STAY_PREPARED
    assert "confidence" not in out


def test_missing_both_member_need_and_animal_profile_lowers_confidence_twice():
    """Both profiles absent at once lowers confidence by two ordinal steps (one
    per missing category) and names both in `calc.missing`, not just one."""
    decl = dict(_decl())
    del decl["member_need_profile"]
    del decl["animal_profile"]
    out = hs.decide_home_shelter(decl, {"colour": "GREEN"})
    assert out["verdict"] == hs.VERDICT_PREPARE_TO_LEAVE
    assert set(out["calc"]["missing"]) == {"member_need_profile", "animal_profile"}
    assert out["confidence"] == "LOW"  # HIGH -> MEDIUM -> LOW, two steps down


# ---- fix (founder ruling 2026-10-06): a stale declared_now fails the Dry Gate -------

def test_very_old_declared_now_fails_dry_gate_and_gives_leave_now():
    """A `declared_now` far outside the staleness window must make
    `dry_status_fresh` False (never True by default), which fails the Dry Gate
    (rule 3, a structural safety invariant) and gives LEAVE_NOW -- a years-old
    self-assessment must never carry a household all the way to STAY_PREPARED."""
    decl = _decl(declared_now="2019-01-01T00:00:00Z")
    out = hs.decide_home_shelter(decl, {"colour": "ORANGE"})
    assert out["dry_gate"]["state"] == "FAIL"
    assert "dry_status_fresh" in out["dry_gate"]["failed"]
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW


# ---- fix (founder ruling 2026-10-06): explicit False/single-storey beats DRY -------

def test_explicit_dry_upper_floor_false_at_orange_gives_leave_now_not_stay():
    """An explicit `dry_upper_floor: False` must never be overridden by
    `water_vs_house_floor == DRY` -- there is no dry upper floor to retreat to,
    at ANY colour, including ORANGE (not only the RISING case the old tests
    covered)."""
    decl = _decl(dry_upper_floor=False, water_vs_house_floor="DRY")
    out = hs.decide_home_shelter(decl, {"colour": "ORANGE"})
    assert out["dry_gate"]["state"] == "FAIL"
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW


def test_single_storey_at_red_gives_leave_now_not_stay():
    """`floors == 1` means there is no upper floor distinct from the one DRY
    ground level -- it must never be read as a safe dry upper floor, at RED,
    even when `water_vs_house_floor == DRY` right now and `dry_upper_floor`
    was given as a non-boolean value this adapter cannot read as an explicit
    True (e.g. a malformed `1` instead of `true`) -- `floors == 1` is the
    fallback safety floor for exactly that case."""
    decl = _decl(floors=1, water_vs_house_floor="DRY", dry_upper_floor=1)
    out = hs.decide_home_shelter(decl, {"colour": "RED"})
    assert out["dry_gate"]["state"] == "FAIL"
    assert out["verdict"] == hs.VERDICT_LEAVE_NOW
