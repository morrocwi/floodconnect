"""The home-as-shelter (stay-vs-go) adapter -- P-C.

This module is deliberately a thin ADAPTER, not a new decision engine: the founder's
own ruling is that the stay/go and community-sustainment logic "already exists" on the
old shelter branches and "only needs connecting" (see the P-C design's reuse inventory).
Every actual hard-gate decision is delegated to the existing modules:

- `shelter_operation_ladder.dry_gate` -- the Dry Gate, same fail-closed gate a public
  shelter candidate is held to (P-C design section "Home Dry Gate").
- `shelter_decision.evaluate_sustainment` -- the home-sustainment check.
- `shelter_decision.recommend_protective_state` -- kept verbatim as
  `protective_state_raw`, for reference alongside the folded `verdict` below (the P-C
  design's own "Verdict" section asks for a DISTINCT, simpler household-only ladder on
  top of it, not a second copy of the raw states).

Invariant 9 (never fabricate a house depth): `water_vs_house_floor` is the household's
own declared observation (`schemas/household_declaration.schema.json`), never computed
from a canal/station reading. This module never reads a water level into that field --
`sandwich_to_forward_hazard` only ever maps the Jev Sandwich COLOUR (not a water depth)
onto the existing `forward_hazard` block `shelter_decision._forward_hazard_state`
already expects.

Missing required household input -> `UNKNOWN_ASK_INPUTS`, never `STAY_PREPARED`
(P-C design rule 2). An official `EVACUATE` instruction always wins first (rule 1).
"""
from __future__ import annotations

from typing import Any, Optional

import shelter_decision as sd
import shelter_operation_ladder as so

HOME_NODE_ID = "__home__"

VERDICT_STAY_PREPARED = "STAY_PREPARED"
VERDICT_PREPARE_TO_LEAVE = "PREPARE_TO_LEAVE"
VERDICT_LEAVE_NOW = "LEAVE_NOW"
VERDICT_FOLLOW_OFFICIAL_ORDER = "FOLLOW_OFFICIAL_ORDER"
VERDICT_UNKNOWN_ASK_INPUTS = "UNKNOWN_ASK_INPUTS"

# schemas/household_declaration.schema.json's own `required` list -- a household
# declaration missing any of these can never be read as "nothing to prepare for" or,
# worse, as a quiet STAY (rule 2).
REQUIRED_HOUSEHOLD_FIELDS = (
    "floors",
    "dry_upper_floor",
    "water_vs_house_floor",
    "official_instruction",
    "declared_now",
)

# jev_decision.colour -> shelter_decision._forward_hazard_state's own vocabulary
# (NONE/LOW/WATCH/HIGH/CRITICAL/ACTIVE). UNKNOWN colour has NO entry here on purpose --
# `sandwich_to_forward_hazard` returns {} for it, which `_forward_hazard_state` reads as
# UNKNOWN (an absent/not-a-dict block), per the P-C design table ("UNKNOWN: block
# absent, which reads as UNKNOWN").
_COLOUR_TO_FORWARD_HAZARD = {
    "GREEN": "NONE",
    "YELLOW": "WATCH",
    "ORANGE": "HIGH",
    "RED": "ACTIVE",
}

# declared household "days of supply" field -> the shelter_decision.RESOURCE_FIELDS /
# CONDITIONAL_RESOURCE_FIELDS name it feeds (P-C design: "supplies, per field, with
# assessed_horizon_h = days x 24"). This mapping itself is a FLOODCONNECT choice (not
# founder-dictated verbatim), documented so a reviewer can see exactly which household-
# declared key feeds which existing shelter_decision resource field -- OPEN pending the
# founder if a different key set is wanted.
_SUPPLY_FIELD_MAP = {
    "potable_water_days": "potable_water_for_horizon",
    "food_days": "food_for_horizon",
    "essential_medicine_days": "essential_medicine_for_horizon",
    "service_water_days": "service_water_for_horizon",
    "sanitation_hygiene_days": "sanitation_hygiene",
    "critical_power_days": "critical_power",
}

# Confidence ordinal (schemas/defs.schema.json's own `confidence` enum, HIGH being the
# most-trusted end). Founder ruling 2026-10-06: a missing input no longer blocks
# the verdict outright (that was the earlier `member_need_profile is None -> ask`
# gate below, superseded here) -- it instead lowers this ordinal by one step per missing
# category, with a plain-Thai reason recorded. This stepping (one step per missing
# category, floor at NONE) is FloodConnect's own default, pending the founder, same as
# rules 4-9's own `pending_founder` tag just below.
_CONFIDENCE_ORDER = ("HIGH", "MEDIUM", "LOW", "NONE")

REASON_MISSING_VULNERABLE_TH = "ไม่มีข้อมูลกลุ่มเปราะบาง (คนและสัตว์)"


def _lower_confidence(level: str, steps: int) -> str:
    try:
        idx = _CONFIDENCE_ORDER.index(level)
    except ValueError:
        idx = 0
    idx = min(idx + max(steps, 0), len(_CONFIDENCE_ORDER) - 1)
    return _CONFIDENCE_ORDER[idx]


def _missing_vulnerable_inputs(decl: dict[str, Any]) -> list[str]:
    """Founder ruling 2026-10-06: a wholly absent `member_need_profile`
    (vulnerable people -- elderly, bedbound, infants, power-dependent) is real
    missing information, named here, never silently treated as "nobody/nothing
    to worry about". A household that DECLARED an empty profile (`{}` -- "we
    checked, nobody needs these things") is unaffected; that is information,
    not a gap.

    The same founder ruling (verbatim: "เช่นถ้าไม่ใส่กลุ่มเปราะบาง
    ผลการคำนวณผ่าน jev decision ต้องต่ำลง ... เช่น คนและสัตว์"): `animal_profile` is
    now checked the SAME way -- a wholly absent profile (`decl.get("animal_profile")
    is None`, i.e. the household declaration never mentioned animals at all) is a
    missing category, not "no animals". An EXPLICIT declaration of no animals
    (`{}`, or any dict whose `declared_animal_count` is 0) is real information and
    is NOT missing -- it is distinguished from absence by `is not None`, never by
    the count. This only changes what THIS confidence/`calc` check sees; it does
    not touch `household_to_node`/`shelter_decision`/`human_animal_household`'s own
    convention of treating a missing `animal_profile` as zero animal burden for the
    sustainment/Dry-Gate calculation itself -- that calculation still needs a
    number to run and 0 remains its safe default, but the ANSWER now separately
    says the household was never actually asked."""
    missing = []
    if decl.get("member_need_profile") is None:
        missing.append("member_need_profile")
    if decl.get("animal_profile") is None:
        missing.append("animal_profile")
    return missing


def _vulnerable_calc_inputs(decl: dict[str, Any]) -> list[dict[str, Any]]:
    declared_now = decl.get("declared_now")
    out = []
    for name in ("member_need_profile", "animal_profile"):
        value = decl.get(name)
        out.append({
            "name": name,
            "value": value,
            "source": "declared" if value is not None else "missing",
            "time": declared_now if value is not None else None,
        })
    return out


def _truthy(value: Any) -> Optional[bool]:
    if value is True:
        return True
    if value is False:
        return False
    return None


def _floors_count(decl: dict[str, Any]) -> Optional[int]:
    try:
        floors = decl.get("floors")
        return int(floors) if floors is not None else None
    except (TypeError, ValueError):
        return None


def _dry_upper(decl: dict[str, Any]) -> Optional[bool]:
    """A dry upper floor is declared directly, OR implied by the household's own
    `water_vs_house_floor == DRY` observation -- never implied by anything computed
    from a station/canal reading (invariant 9).

    fix (founder ruling 2026-10-06): an explicit `dry_upper_floor: False`, or a
    single-storey household (`floors == 1`, so there is no upper floor distinct
    from the one DRY ground level the water has not yet reached), is NEVER
    overridden by `water_vs_house_floor == DRY` -- both are checked FIRST, before
    the DRY inference. Before this fix, `water_vs_house_floor == DRY` returned
    True unconditionally, so a single-storey household with no dry upper floor
    at all (or one that explicitly declared it has none) still passed this
    check, reaching STAY_PREPARED/PREPARE_TO_LEAVE instead of rule 4's
    LEAVE_NOW."""
    direct = _truthy(decl.get("dry_upper_floor"))
    if direct is False:
        return False
    if _floors_count(decl) == 1:
        return False
    if direct is True:
        return True
    water_state = decl.get("water_vs_house_floor")
    if water_state == "DRY":
        return True
    return None


def sandwich_to_forward_hazard(jev: Optional[dict[str, Any]]) -> dict[str, Any]:
    """jev_decision -> the `forward_hazard` block `shelter_decision._forward_hazard_state`
    reads (P-C design table). `jev=None` (no Jev Sandwich answer available at all) gives
    `{}`, which that function already reads as UNKNOWN -- never a fabricated NONE."""
    if not isinstance(jev, dict):
        return {}
    colour = jev.get("colour")
    state = _COLOUR_TO_FORWARD_HAZARD.get(colour)
    if state is None:
        # UNKNOWN colour, or a colour outside the closed colour5 set -- no forward-hazard
        # claim can honestly be made from it.
        return {}
    why = jev.get("why") or jev.get("trace", {}).get("reasons") or []
    mobility_window_closing: Any = "UNKNOWN"
    if colour == "RED":
        mobility_window_closing = True
    elif colour == "ORANGE":
        mobility_window_closing = bool("WATER_COMING_ON_KG_PATH" in why)
    z0 = jev.get("z0") or {}
    fresh = bool(z0.get("fresh", True)) if isinstance(z0, dict) else True
    return {
        "state": state,
        "fresh": fresh,
        "horizon_h": None,
        "mobility_window_closing": mobility_window_closing,
    }


def household_to_node(decl: dict[str, Any]) -> dict[str, Any]:
    """Build the node `shelter_operation_ladder.dry_gate`/`shelter_decision.*` expect,
    out of one `household_declaration` (schemas/household_declaration.schema.json).

    Every Dry Gate / sustainment field here is either a direct household observation, or
    a conservative FLOODCONNECT derivation from one -- never a computed water depth
    (invariant 9) and never a silently-invented default: an undeclared input stays
    `None` (UNKNOWN), it is never defaulted to a pass."""
    water_state = decl.get("water_vs_house_floor", "UNKNOWN")
    dry_upper = _dry_upper(decl)
    panel_safe = _truthy(decl.get("panel_above_current_water"))
    can_cut = _truthy(decl.get("can_cut_power"))
    if panel_safe is True or can_cut is True:
        hazard_safe: Optional[bool] = True
    elif panel_safe is False and can_cut is False:
        hazard_safe = False
    elif panel_safe is False and can_cut is None:
        hazard_safe = None
    else:
        hazard_safe = None

    if water_state == "UNKNOWN":
        drainage_ok: Optional[bool] = None
    else:
        drainage_ok = water_state != "ABOVE_FLOOR"

    node: dict[str, Any] = {
        # community_dag.validate_document's own schema (only reached via
        # recommend_protective_state's EVACUATE/physical-unsafe branches).
        "kind": "household",
        "layer": 0,
        "status": "UNKNOWN",
        "fresh": True,
        # the home Dry Gate (P-C design table).
        "dry_operating_surface": dry_upper,
        "dry_status_verified": True,  # basis SELF_DECLARED -- see docstring below
        "dry_status_fresh": _is_fresh_declaration(decl.get("declared_now")),
        "immediate_site_hazard_safe": hazard_safe,
        "drainage_not_blocking_operation": drainage_ok,
    }

    member_profile = decl.get("member_need_profile")
    if isinstance(member_profile, dict):
        node["member_need_profile"] = member_profile
    animal_profile = decl.get("animal_profile")
    if isinstance(animal_profile, dict):
        node["animal_profile"] = animal_profile

    node["sustainment"] = _sustainment_block(decl, member_profile)
    return node


# fix (founder ruling 2026-10-06): a `declared_now` of any age used to count as
# fresh (a 2019 declaration passed the Dry Gate's `dry_status_fresh` field at
# face value), which let a very old self-assessment carry a household all the
# way to STAY_PREPARED at ORANGE. `_DECLARED_NOW_STALE_AFTER_H` is this adapter's
# own staleness window -- INSTINCT, not a founder-confirmed number (OPEN,
# pending the founder, same as the design's own `declared_now` field note);
# tagged here so a caller can tell this is a judgment call, not a declared
# agency rule. Past this window, `dry_status_fresh` is False (never None/
# UNKNOWN) -- the Dry Gate's own FAIL branch then routes to LEAVE_NOW (rule 3,
# a structural safety invariant), which is the conservative direction for a
# stale self-assessment this adapter can no longer trust.
# KNOWN ISSUE, tracked, not fixed (found 2026-10-06): the same
# FAIL-routes-to-LEAVE_NOW path above also fires for a GENUINELY single-storey
# house with NO dry upper floor at all -- `dry_operating_surface` (the other
# Dry Gate field this house can never pass) FAILs regardless of the area's own
# colour, including GREEN. MEASURED on a live sweep: 410 (single-storey) + 205
# (stale declaration) Bangkok answers reached LEAVE_NOW this way. Both are the
# SAME structural rule (rule 3, Dry Gate FAIL -> LEAVE_NOW, a safety invariant,
# never loosened on its own) reached from two different real household
# shapes, not a bug in rule 3 itself -- whether a single-storey/no-dry-upper-
# floor household at GREEN should instead reach a softer verdict (e.g.
# PREPARE_TO_LEAVE) is OPEN, pending the founder, same as this constant's own
# 24h window above.
_DECLARED_NOW_STALE_AFTER_H = 24.0


def _is_fresh_declaration(declared_now: Any) -> Optional[bool]:
    """A declaration with a `declared_now` timestamp counts as fresh only while it
    is within `_DECLARED_NOW_STALE_AFTER_H` of the real wall clock -- a malformed
    or unparseable timestamp returns None (UNKNOWN), never a guessed True/False;
    an absent timestamp also returns None."""
    if not declared_now:
        return None
    import datetime as _dt
    try:
        ts = _dt.datetime.fromisoformat(str(declared_now).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_dt.timezone.utc)
    age_h = (_dt.datetime.now(_dt.timezone.utc) - ts).total_seconds() / 3600.0
    return age_h <= _DECLARED_NOW_STALE_AFTER_H


def _resource_state(days: Any, planning_horizon_h: Optional[float]) -> str:
    if days is None:
        return "UNKNOWN"
    try:
        hours = float(days) * 24.0
    except (TypeError, ValueError):
        return "UNKNOWN"
    if planning_horizon_h is None:
        return "UNKNOWN"
    try:
        horizon = float(planning_horizon_h)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if horizon <= 0:
        return "UNKNOWN"
    return "SUFFICIENT" if hours >= horizon else "INSUFFICIENT"


def _vulnerable_support_state(member_profile: Optional[dict[str, Any]]) -> str:
    """Reuses `shelter_decision.evaluate_dependency_coverage` (SUPPORT_LINK_FIELDS,
    already self-declared in `member_need_profile`) rather than inventing a second,
    divergent vulnerable-support flag."""
    if not isinstance(member_profile, dict):
        return "NOT_REQUIRED"
    coverage = sd.evaluate_dependency_coverage(member_profile)
    if coverage.state == "NO_SPECIAL_DEPENDENCY_LINK_REQUIRED":
        return "NOT_REQUIRED"
    if coverage.state == "DEPENDENCY_COVERED":
        return "SUFFICIENT"
    if coverage.state == "DEPENDENCY_SUPPORT_GAP":
        return "INSUFFICIENT"
    return "UNKNOWN"


def _sustainment_block(decl: dict[str, Any], member_profile: Optional[dict[str, Any]]) -> dict[str, Any]:
    planning_horizon_h = decl.get("planning_horizon_h")
    supplies = decl.get("supplies") if isinstance(decl.get("supplies"), dict) else {}
    communications = decl.get("communications") if isinstance(decl.get("communications"), dict) else {}

    block: dict[str, Any] = {
        "fresh": _is_fresh_declaration(decl.get("declared_now")) is True,
        "assessed_horizon_h": None,
        "physical_safety": _physical_safety(decl),
        "official_instruction": decl.get("official_instruction", "NONE"),
        "escalation": {"status": "UNKNOWN", "fresh": False, "verified": False},
    }
    if planning_horizon_h is not None:
        try:
            block["assessed_horizon_h"] = float(planning_horizon_h)
        except (TypeError, ValueError):
            block["assessed_horizon_h"] = None

    for supply_key, resource_field in _SUPPLY_FIELD_MAP.items():
        block[resource_field] = _resource_state(supplies.get(supply_key), planning_horizon_h)

    # `critical_power` is CONDITIONAL in shelter_decision (CONDITIONAL_RESOURCE_FIELDS):
    # a household with no declared power-dependent need defaults to NOT_REQUIRED rather
    # than an undeclared-input UNKNOWN that would otherwise block an ordinary STAY.
    if "critical_power_days" not in supplies:
        needs_power = isinstance(member_profile, dict) and (
            member_profile.get("needs_power_dependent_medical_device") or 0
        ) not in (0, None, "0")
        block["critical_power"] = "UNKNOWN" if needs_power else "NOT_REQUIRED"

    comms_available = _truthy(communications.get("available")) if communications else None
    block["communications"] = (
        "SUFFICIENT" if comms_available is True
        else "INSUFFICIENT" if comms_available is False
        else "UNKNOWN"
    )
    block["vulnerable_support"] = _vulnerable_support_state(member_profile)

    forward_hazard = decl.get("_forward_hazard")  # set only by decide_home_shelter, below
    if isinstance(forward_hazard, dict):
        block["forward_hazard"] = forward_hazard
    return block


def _physical_safety(decl: dict[str, Any]) -> str:
    """A home is physically SAFE for sustainment purposes only when the water has not
    reached/overtopped the house floor AND the electrical hazard is covered -- never
    assumed from an absent/UNKNOWN input."""
    water_state = decl.get("water_vs_house_floor", "UNKNOWN")
    if water_state == "ABOVE_FLOOR":
        return "UNSAFE"
    panel_safe = _truthy(decl.get("panel_above_current_water"))
    can_cut = _truthy(decl.get("can_cut_power"))
    if water_state == "UNKNOWN":
        return "UNKNOWN"
    if panel_safe is False and can_cut is False:
        return "UNSAFE"
    if panel_safe is True or can_cut is True:
        return "SAFE" if water_state in ("DRY", "BELOW_FLOOR_RISING") else "UNKNOWN"
    return "UNKNOWN"


def _missing_required(decl: dict[str, Any]) -> list[str]:
    return [f for f in REQUIRED_HOUSEHOLD_FIELDS if decl.get(f) in (None, "")]


def _has_uncovered_power_or_medical(member_profile: Optional[dict[str, Any]]) -> bool:
    """RED rule 4's 'uncovered power or medical dependency' -- a declared
    `needs_power_dependent_medical_device` / `needs_time_critical_medical_followup`
    (oxygen/dialysis, per the task's own examples) whose support link is NOT covered."""
    if not isinstance(member_profile, dict):
        return False
    needs_power_or_medical = any(
        (member_profile.get(k) or 0) not in (0, None, "0")
        for k in ("needs_power_dependent_medical_device", "needs_time_critical_medical_followup")
    )
    if not needs_power_or_medical:
        return False
    coverage = sd.evaluate_dependency_coverage(member_profile)
    return coverage.state == "DEPENDENCY_SUPPORT_GAP"


_L5_CHECKLIST_CACHE: Optional[list[str]] = None


def _l5_survival_lines() -> list[str]:
    """The 8 independently-reviewed "water already in the house" lines
    (`site/build_page.py::_l5_survival_lines_html`, already read out by
    `kb.py::_l5_survival_steps_plain`) -- reused verbatim, never a second copy."""
    global _L5_CHECKLIST_CACHE
    if _L5_CHECKLIST_CACHE is not None:
        return _L5_CHECKLIST_CACHE
    try:
        import sys
        from pathlib import Path

        here = Path(__file__).resolve().parent.parent
        if str(here / "site") not in sys.path:
            sys.path.insert(0, str(here / "site"))
        import build_page as _build_page_mod  # noqa: PLC0415

        if str(here) not in sys.path:
            sys.path.insert(0, str(here))
        import kb as _kb_mod  # noqa: PLC0415

        lines = _kb_mod._l5_survival_steps_plain(_build_page_mod)
    except Exception:  # pragma: no cover - defensive, must never crash the checklist
        lines = []
    _L5_CHECKLIST_CACHE = lines
    return lines


def _build_checklist(decl: dict[str, Any], sustain: Any) -> list[str]:
    """The household-relevant subset of
    `shelter_decision.SHELTER_PHASE_REQUIREMENTS["OCCUPIED"]` + `RESOURCE_FIELDS` +
    the dependency links + the 8 reviewed L5 survival lines, each tagged (P-C design).
    This is a STAY checklist -- built only for STAY_PREPARED verdicts."""
    items: list[str] = []
    gaps = set(getattr(sustain, "gaps", ()) or ())
    unknowns = set(getattr(sustain, "unknown_fields", ()) or ())
    for field in sd.RESOURCE_FIELDS + sd.CONDITIONAL_RESOURCE_FIELDS:
        if field in gaps:
            items.append(f"FLOODCONNECT:resource_gap:{field}")
        elif field in unknowns:
            items.append(f"FLOODCONNECT:resource_unknown:{field}")
    member_profile = decl.get("member_need_profile")
    if isinstance(member_profile, dict):
        coverage = sd.evaluate_dependency_coverage(member_profile)
        for link in coverage.details.get("uncovered_links", []) if coverage.details else []:
            items.append(f"FLOODCONNECT:dependency_link_uncovered:{link}")
    for line in _l5_survival_lines():
        items.append(f"FLOODCONNECT:l5_survival:{line}")
    return items


def decide_home_shelter(decl: dict[str, Any], jev: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """The stay-vs-go verdict (P-C design "Verdict" section, rules 1-9), plus the Dry
    Gate/sustainment detail and the raw `shelter_decision.recommend_protective_state`
    result, shaped per `schemas/advice.schema.json`'s `home_shelter` object.

    `jev` is a `jev_decision` dict (or `None` -- no Jev Sandwich answer available at
    all, which this function treats as colour UNKNOWN, never as GREEN)."""
    missing = _missing_required(decl)
    if missing:
        return {
            "verdict": VERDICT_UNKNOWN_ASK_INPUTS,
            "dry_gate": {"state": "UNKNOWN", "failed": [], "unknown": []},
            "sustainment": {"state": "UNKNOWN", "gaps": [], "unknown": []},
            "missing_inputs": missing,
            "checklist": [],
            "protective_state_raw": None,
        }

    colour = (jev or {}).get("colour") or "UNKNOWN"
    forward_hazard = sandwich_to_forward_hazard(jev)
    node = household_to_node(decl)
    doc = {"nodes": {HOME_NODE_ID: node}}
    planning_horizon_h = decl.get("planning_horizon_h")

    try:
        raw = sd.recommend_protective_state(
            doc, HOME_NODE_ID, planning_horizon_h, forward_hazard=forward_hazard
        )
        protective_state_raw = raw.as_dict()
    except Exception as e:  # pragma: no cover - defensive, must never crash the verdict
        protective_state_raw = {"admitted": False, "state": "UNKNOWN", "error": str(e)}

    dry = so.dry_gate(node)
    member_profile = decl.get("member_need_profile")
    sustain = sd.evaluate_sustainment(node, planning_horizon_h)

    dry_gate_out = {"state": dry.state, "failed": list(dry.failed_fields),
                     "unknown": list(dry.unknown_fields)}
    sustainment_out = {"state": sustain.state, "gaps": list(sustain.gaps),
                        "unknown": list(sustain.unknown_fields)}

    # Founder ruling 2026-10-06, verbatim: "ถ้าไม่ใส่กลุ่มเปราะบาง ผลการคำนวณผ่าน
    # jev decision ต้องต่ำลง และบอกเหตุผล": a missing `member_need_profile`/
    # `animal_profile` no longer blocks the verdict (that was this function's own
    # earlier gate, now superseded) -- it lowers `confidence` by one ordinal step
    # per missing category and records the reason in `calc`. This never raises a
    # STAY_PREPARED verdict: any branch below that would otherwise reach STAY is
    # downgraded to PREPARE_TO_LEAVE instead, so a household this repo has no actual
    # vulnerable/animal information for is never told its home is simply fine.
    missing_vulnerable = _missing_vulnerable_inputs(decl)
    calc_block = {
        "eq": "FLOODCONNECT-vulnerable-confidence-step",
        "inputs": _vulnerable_calc_inputs(decl),
        "missing": list(missing_vulnerable),
    }

    # Fix: rules 4-9 below are this repo's OWN
    # defaults for exactly how aggressively to escalate a colour/gap combination
    # into LEAVE_NOW/PREPARE_TO_LEAVE/STAY_PREPARED -- FloodConnect's own judgment
    # call, never founder-dictated verbatim (unlike rule 1's official-order-always-
    # wins or rule 3's Dry-Gate-FAIL-always-leaves, which are structural safety
    # invariants, not defaults). Every verdict reached through rules 4-9 is tagged
    # `pending_founder: "R<n>"` -- both here in the output (so a caller can tell a
    # founder-confirmed rule from a standing orchestrator default) and in this
    # module's own comments -- until the founder confirms or revises it.
    def _assemble(verdict: str, *, checklist: Optional[list[str]] = None,
                  confidence_low: bool = False, rule: Optional[str] = None) -> dict[str, Any]:
        if missing_vulnerable and verdict == VERDICT_STAY_PREPARED:
            verdict = VERDICT_PREPARE_TO_LEAVE
        out = {
            "verdict": verdict,
            "dry_gate": dry_gate_out,
            "sustainment": sustainment_out,
            "missing_inputs": [],
            "checklist": checklist or [],
            "protective_state_raw": protective_state_raw,
        }
        confidence = "LOW" if confidence_low else "HIGH"
        reasons: list[str] = []
        if missing_vulnerable:
            confidence = _lower_confidence(confidence, len(missing_vulnerable))
            reasons.append(REASON_MISSING_VULNERABLE_TH)
        if confidence != "HIGH":
            out["confidence"] = confidence
        out["calc"] = dict(calc_block, result=verdict)
        if reasons:
            out["calc"]["reasons"] = reasons
        if rule is not None:
            out["rule"] = rule
            out["tag"] = "FLOODCONNECT_DEFAULT_PENDING_FOUNDER"
        return out

    # Rule 1: an official EVACUATE instruction always wins first (structural safety
    # invariant, not a FloodConnect default -- no pending_founder tag). Fix (an
    # earlier pass): an official WARNING instruction folds into this
    # same outcome -- per prd.go.th/534015 (OG-25), an official warning signal means
    # "evacuate immediately, do not wait for crisis level", so WARNING must never be
    # read as merely "no instruction" (NONE).
    if decl.get("official_instruction") in ("EVACUATE", "WARNING"):
        return _assemble(VERDICT_FOLLOW_OFFICIAL_ORDER)

    # Rule 3: Dry Gate FAIL -> LEAVE_NOW (structural safety invariant, same as rule 1).
    if dry.state == "FAIL":
        return _assemble(VERDICT_LEAVE_NOW)

    dry_upper = _dry_upper(decl) is True
    uncovered_power_medical = _has_uncovered_power_or_medical(member_profile)

    # Rule 4 (PENDING THE FOUNDER): RED with no dry upper floor, or an uncovered
    # power/medical dependency.
    if colour == "RED" and (not dry_upper or uncovered_power_medical):
        return _assemble(VERDICT_LEAVE_NOW, rule="R4")

    # Rule 5 (PENDING THE FOUNDER): RED otherwise.
    if colour == "RED":
        return _assemble(VERDICT_PREPARE_TO_LEAVE, rule="R5")

    # Rules 6-9 (fix, earlier pass): GREEN/YELLOW/ORANGE/UNKNOWN
    # all share ONE gate from here on (a Dry Gate FAIL -- rule 3 above -- already
    # covers "no dry upper floor" as a KNOWN gap for every colour, ORANGE included,
    # since `dry_operating_surface` is itself one of `shelter_operation_ladder.
    # DRY_GATE_FIELDS`; this gate below covers the rest). STAY_PREPARED is given
    # ONLY when every one of
    # the three hard conditions actually, affirmatively holds: Dry Gate state PASS,
    # sustainment state SUSTAINABLE, AND official_instruction NONE. Before this fix,
    # rule 7 checked sustainment alone (never the Dry Gate, never
    # official_instruction) and rule 9 (UNKNOWN colour) checked nothing at all --
    # reproduced: a declaration with ONLY the 5 required fields (Dry Gate UNKNOWN,
    # sustainment UNKNOWN), one with `official_instruction="UNKNOWN"`, and one with a
    # real 0.5-day supply gap against a 72 h horizon (NOT_SUSTAINABLE) all returned
    # STAY_PREPARED. An UNKNOWN anywhere in those three conditions now gives
    # UNKNOWN_ASK_INPUTS with the SPECIFIC missing/unknown fields named -- never a
    # silent STAY on an input this repo never actually got. A KNOWN gap (not an
    # unknown) gives PREPARE_TO_LEAVE instead of asking again for input that is
    # already known and simply insufficient. UNKNOWN colour reaches this exact same
    # gate (no free pass on its own unknowns either) and only differs by `confidence:
    # LOW` on whatever verdict it reaches, same as before this fix.
    official_instruction = decl.get("official_instruction", "NONE")
    unknown_inputs: list[str] = []
    if official_instruction == "UNKNOWN":
        unknown_inputs.append("official_instruction")
    if dry.state == "UNKNOWN":
        unknown_inputs.extend(f"dry_gate:{f}" for f in dry.unknown_fields)
        if not dry.unknown_fields:
            unknown_inputs.append("dry_gate")
    if sustain.state == "UNKNOWN":
        unknown_inputs.extend(f"sustainment:{f}" for f in sustain.unknown_fields)
        if not sustain.unknown_fields:
            unknown_inputs.append("sustainment")
    # Founder ruling 2026-10-06 supersedes the earlier version of this
    # paragraph: an entirely absent `member_need_profile` (or `animal_profile`) used
    # to be added to `unknown_inputs` here, forcing UNKNOWN_ASK_INPUTS outright
    # (measured 1,149 times reaching a silent STAY_PREPARED before that fix). The
    # founder's newer ruling asks for an actual answer instead -- lowered
    # `confidence` plus a named reason (`missing_vulnerable`/`calc` above,
    # `_assemble`'s own STAY->PREPARE_TO_LEAVE downgrade) -- so it is handled there,
    # not as a blocking unknown input, and is deliberately NOT added to
    # `unknown_inputs` below.

    if unknown_inputs:
        return {
            "verdict": VERDICT_UNKNOWN_ASK_INPUTS,
            "dry_gate": dry_gate_out,
            "sustainment": sustainment_out,
            "missing_inputs": unknown_inputs,
            "checklist": [],
            "protective_state_raw": protective_state_raw,
            "calc": dict(calc_block, result=VERDICT_UNKNOWN_ASK_INPUTS),
        }

    # fix (S4, founder subtractive-fix ruling 2026-10-06): colour UNKNOWN never
    # gives STAY, even with every household input known. Before this fix, rule 9
    # fell into the exact same STAY_PREPARED branch as a known-GREEN colour
    # whenever dry/sustainment/official_instruction all happened to be known --
    # MEASURED: 137/137 UNKNOWN-colour points with a complete household declared
    # STAY_PREPARED, including a point with no gauge within radius at all. The
    # flood STATE itself (not the household inputs) is the unknown here, so the
    # verdict is UNKNOWN_ASK_INPUTS naming `flood_state` -- unless a household
    # gap is ALSO already known (sustainment NOT_SUSTAINABLE, say), in which case
    # that known gap decides and PREPARE_TO_LEAVE is returned instead of asking
    # again for a flood reading this function cannot itself go fetch.
    if colour == "UNKNOWN":
        if dry.state == "PASS" and sustain.state == "SUSTAINABLE" and official_instruction == "NONE":
            return {
                "verdict": VERDICT_UNKNOWN_ASK_INPUTS,
                "dry_gate": dry_gate_out,
                "sustainment": sustainment_out,
                "missing_inputs": ["flood_state"],
                "checklist": [],
                "protective_state_raw": protective_state_raw,
                "calc": dict(calc_block, result=VERDICT_UNKNOWN_ASK_INPUTS),
            }
        return _assemble(VERDICT_PREPARE_TO_LEAVE, checklist=_build_checklist(decl, sustain),
                          confidence_low=True, rule="R9")

    if dry.state == "PASS" and sustain.state == "SUSTAINABLE" and official_instruction == "NONE":
        return _assemble(VERDICT_STAY_PREPARED, checklist=_build_checklist(decl, sustain), rule="R7")
    return _assemble(VERDICT_PREPARE_TO_LEAVE, checklist=_build_checklist(decl, sustain),
                      rule=("R6" if colour == "ORANGE" else "R8"))
