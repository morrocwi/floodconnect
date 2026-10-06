"""floodconnect_model.py -- the by-hand FloodConnect compute path, in pure stdlib Python.

Why this file exists: `docs/EQUATIONS_FOR_AI.md` already tells a weak/sandboxed AI (one
that can read numbers off an official source but cannot run this repository's code) how
to compute PROP-FLOOD-01 (Δk, the rise/fall trend) and PROP-FLOOD-02 (Tk, time to an
official threshold) BY HAND, plus a six-step "one decision, with confidence" procedure.
This module's classification of official status words matches `kb.py` exactly (see
`classify()`/`classify_counts()` below, pinned against `kb.py` by
`tests/test_floodconnect_model.py::test_classify_matches_kb_for_shared_status_words`).
Its trend-only path (no official status available) is a separate, deliberately
conservative by-hand aid -- it never returns GREEN on its own; it is expressed as
runnable functions instead of prose for a sandbox AI that got upgraded to "can run a
little Python, still has no network/DB", or for a test that wants to pin the by-hand
procedure against this repository's real `kb.py` classification on the same inputs.

Constraints (deliberate, do not relax):
  - stdlib only. No `import collect`, no `import store`, no `import kb` at module scope,
    no network call, no filesystem/DB access. Every function here takes plain Python
    values in and returns a plain dict out.
  - Toledo-first, stated honestly: PROP-FLOOD-01/02 are registered Toledo PROPOSALS
    (tier `Dr`, placeholder code `weld/M.??.v1`), not merged CANONICAL.json theorems --
    `model_spec.json` next to this file carries the exact same status, codes and
    citation. PROP-FLOOD-03/06/07 (water debt, L0-L5 coping tier, F1-F6 flow state) are
    OPEN Toledo pull requests, not merged -- `one_decision` below never computes a
    number from them; see `docs/EQUATIONS_FOR_AI.md` section 3.
  - BOT != ZERO. A missing/stale/ambiguous input produces an explicit non-value
    (`NO_READOUT`, `REFUSED` with a `reason`, or `UNKNOWN`) -- never the number 0, and
    never silently treated as "nothing is happening". A genuinely flat reading (`FLAT`,
    |Δk| <= ε) IS a real measured zero-like state and is reported as such; a *missing*
    reading is a different thing and must never be reported as flat.
  - `classify()` must agree with `kb.py`'s own `_classify_current_local_state` for the
    same station-status words on the same inputs -- see
    `tests/test_floodconnect_model.py::test_classify_matches_kb_for_shared_status_words`.
    `STATUS_TO_LEVEL` below (v0.1.2) is this repository's ONE closed status-word map;
    `readout.py` and `kb.py` read the three derived sets off it instead of keeping a
    second copy. `NO_THRESHOLD` (no agency level published at all) is deliberately
    UNKNOWN, never GREEN -- fixed in v0.1.2, see `STATUS_TO_LEVEL`'s own comment.
"""

from __future__ import annotations

# STATUS_TO_LEVEL -- the ONE closed status-word -> colour map this repository uses
# (v0.1.2, earlier passes): readout.py and kb.py import the three derived sets
# below instead of keeping their own copy. Every word here is either an agency
# station-status word this repo already classified before v0.1.2 (CRITICAL/OVERBANK/
# WATCH/NORMAL, BMA DDS "วิกฤต(ิ)"/"เตือนภัย"/"ปกติ") or a `thaiwater_situation_N`
# code this repo now STORES verbatim in `observations.status` (see
# `collect.collect_thaiwater_waterlevel`). The 1-5 ordinal direction is MEASURED
# (2026-10-04, one live GET of api-v3.thaiwater.net .../public/waterlevel, 808
# stations): `situation_level == 5` co-occurred with `diff_wl_bank_text` == "ล้นตลิ่ง
# (ม.)" (the agency's own overflow word) in every checked record, and
# `storage_percent` (bank-fill %, also agency-published) rises monotonically with the
# code (1: <=10%, 2: >10-30%, 3: >30-70%, 4: >70-100%, 5: >100%/overflow). The agency's
# own Thai label and colour for each code (VERIFIED: fetched from the public bundle
# https://www.thaiwater.net/dist/js/app.chunk.js on 2026-10-04) --
#   0 ไม่มีข้อมูล (no data, grey #BDBDBD) · 1 น้อยวิกฤต (critically LOW water, orange
#   #db802b) · 2 น้อย (low, yellow #ffc000) · 3 ปกติ (normal, green #00b050) ·
#   4 มาก (high, BLUE #003cfa) · 5 ล้นตลิ่ง (overbank, red #ff0000).
# Two things this repo's own mapping deliberately does NOT inherit from the agency:
#   (a) level 1's label "น้อยวิกฤต" contains the word "วิกฤต" ("critical") but means
#       critically LOW water, not a flood risk -- an AI reading `diff_wl_bank_text`/
#       labels by hand must not pattern-match "วิกฤต" there onto RED (see
#       docs/NEAREST_STATION_RECIPE.md);
#   (b) the agency colours level 4 ("มาก"/high) BLUE and does not call it a warning --
#       mapping it to YELLOW below is FloodConnect's OWN conservative choice, not the
#       agency's; likewise 1/2 ("น้อยวิกฤต"/"น้อย", low water) -> GREEN here is this
#       repo's own choice that low water is not itself a flood signal, not an agency
#       claim. The ORDINAL mapping (which way is worse) is MEASURED-derived from
#       `storage_percent`/`diff_wl_bank_text` as above; which Thai-coloured level
#       crosses into FloodConnect's YELLOW/RED is this repo's judgment call on top of
#       that ordinal, stated here so it is never confused with an agency threshold.
#
# `NO_THRESHOLD` (no agency level published at all for this station) is deliberately
# ABSENT from every colour-bearing set -- it is UNKNOWN (fixed from v0.1.1's bug,
# which put it in the normal-like/GREEN set with no basis at all).
STATUS_TO_LEVEL: dict = {
    "CRITICAL": "RED", "OVERBANK": "RED",
    "วิกฤต": "RED", "วิกฤติ": "RED", "ระดับน้ำวิกฤติ": "RED",
    "thaiwater_situation_5": "RED",
    "WATCH": "YELLOW", "เตือนภัย": "YELLOW", "ระดับน้ำเตือนภัย": "YELLOW",
    "thaiwater_situation_4": "YELLOW",
    "NORMAL": "GREEN", "ปกติ": "GREEN", "ระดับน้ำปกติ": "GREEN",
    "thaiwater_situation_1": "GREEN", "thaiwater_situation_2": "GREEN",
    "thaiwater_situation_3": "GREEN",
}
CRITICAL_LIKE_STATUS = {k for k, v in STATUS_TO_LEVEL.items() if v == "RED"}
WATCH_LIKE_STATUS = {k for k, v in STATUS_TO_LEVEL.items() if v == "YELLOW"}
NORMAL_LIKE_STATUS = {k for k, v in STATUS_TO_LEVEL.items() if v == "GREEN"}
# Status words that carry NO basis for a colour at all (never GREEN, never YELLOW) --
# excluded from a multi-station count rather than driving YELLOW-by-default.
UNKNOWN_LIKE_STATUS = {"NO_THRESHOLD"}


def delta_k(h_t: float | None, h_t_minus_k: float | None, epsilon: float) -> dict:
    """PROP-FLOOD-01 (Toledo proposal, tier Dr, placeholder code weld/M.??.v1):
    Delta_k(t) := h(t) - h(t-k).

    `h_t`/`h_t_minus_k` are readings in metres at the SAME station, `epsilon` is the
    station's own declared sensor resolution in metres (never invented -- if the source
    states none, the caller should treat it as INSTINCT per docs/EQUATIONS_FOR_AI.md,
    not call this with a guessed epsilon as if it were measured).

    Returns {"value": float, "trend": "RISING"|"FALLING"|"FLAT"} or, when `h_t_minus_k`
    is missing, {"value": None, "trend": "NO_READOUT"} -- a real, distinct outcome, never
    silently FLAT (BOT != ZERO)."""
    if h_t is None or h_t_minus_k is None:
        return {"value": None, "trend": "NO_READOUT"}
    value = h_t - h_t_minus_k
    if value > epsilon:
        trend = "RISING"
    elif value < -epsilon:
        trend = "FALLING"
    else:
        trend = "FLAT"
    return {"value": value, "trend": trend}


def time_to_threshold(h_t: float, delta: dict, theta: float, k: float = 1.0,
                       epsilon: float = 0.0) -> dict:
    """PROP-FLOOD-02 (same Toledo PR/tier/code as PROP-FLOOD-01):
    Tk := (theta - h(t)) * k / Delta_k(t), defined only when Delta_k(t) > epsilon
    (genuinely rising) and h(t) < theta (threshold not yet reached).

    `delta` is a `delta_k()` result. `k` is the same lag (in ticks) that produced it.
    Returns {"value": float, "unit": "ticks"} when defined, else
    {"value": None, "reason": "UNRESOLVED"|"NOT_APPLICABLE"} -- REFUSED is a
    non-value, not a number: never 0, never infinity, never blank (BOT != ZERO)."""
    trend = delta.get("trend")
    dv = delta.get("value")
    if trend == "NO_READOUT":
        return {"value": None, "reason": "NOT_APPLICABLE"}
    if trend != "RISING":
        # FALLING or FLAT: can't tell if it's really moving (FLAT, |Delta_k|<=epsilon) or
        # it is moving the wrong way (FALLING) -- NOT_APPLICABLE for FALLING,
        # UNRESOLVED for FLAT (can't tell if it's really moving at all).
        reason = "UNRESOLVED" if trend == "FLAT" else "NOT_APPLICABLE"
        return {"value": None, "reason": reason}
    if h_t >= theta:
        return {"value": None, "reason": "NOT_APPLICABLE"}
    return {"value": (theta - h_t) * k / dv, "unit": "ticks"}


def classify(status_word: str | None) -> str:
    """Map one agency-declared station-status word onto the closed GREEN/YELLOW/RED/
    UNKNOWN vocabulary via `STATUS_TO_LEVEL` -- CRITICAL/OVERBANK/thaiwater_situation_5
    -> RED, WATCH/thaiwater_situation_4 -> YELLOW, a recognised normal-like word
    (including thaiwater_situation_1/2/3) -> GREEN, anything else (including None, an
    unrecognised word, `NO_THRESHOLD`, or a sensor-fault word) -> UNKNOWN. This is a
    single-word simplification of `kb.py`'s own `_classify_current_local_state`, which
    runs over a station's full `status_counts` -- see `classify_counts()` below for the
    multi-station form, which is what the shared test actually pins against `kb.py`."""
    if not status_word:
        return "UNKNOWN"
    return STATUS_TO_LEVEL.get(status_word, "UNKNOWN")


def classify_counts(status_counts: dict) -> str:
    """Multi-station form of `classify()`, matching `kb.py`'s own
    `_classify_current_local_state` rule exactly for the English status-word sets this
    module hardcodes (no Thai DDS keys, no sensor-fault exclusion -- those require a
    DB/live_water_level.py import this stdlib-only module deliberately avoids; see the
    module docstring): any agency-declared critical/overflow word present -> RED;
    discard `UNKNOWN_LIKE_STATUS` words (no basis at all, e.g. `NO_THRESHOLD`) first --
    if nothing informative remains, or `status_counts` was empty, -> UNKNOWN; every
    remaining word is normal-like -> GREEN; anything else (a WATCH word, or a mix)
    -> YELLOW. Fix (2026-10-04): a station with NO agency threshold
    published at all is no longer GREEN -- it carries no basis for that colour."""
    if not status_counts:
        return "UNKNOWN"
    words = set(status_counts)
    if words & CRITICAL_LIKE_STATUS:
        return "RED"
    informative = words - UNKNOWN_LIKE_STATUS
    if not informative:
        return "UNKNOWN"
    if informative <= NORMAL_LIKE_STATUS:
        return "GREEN"
    return "YELLOW"


def one_decision(inputs: dict) -> dict:
    """The six-step "one decision, with confidence" procedure from
    `docs/EQUATIONS_FOR_AI.md` section 5, as a function -- Locate/Freshness are the
    caller's own job (this function trusts `inputs` as already located+freshness-tagged),
    so this covers steps 3-6: trend, time-to-threshold, official-context override, and
    one plain decision with a confidence label.

    `inputs` (all optional except `h_t`, which station-identifies what is being
    decided):
      h_t            -- current reading (m). Required; None means no reading at all.
      h_t_minus_k    -- reading k ticks earlier, same station (m).
      k              -- the lag in ticks the above two readings are k apart (default 1).
      epsilon        -- the station's own declared sensor resolution (m). Required to
                         compute a trend at all -- missing epsilon makes Delta_k/Tk
                         UNRESOLVED, never a guessed resolution.
      theta          -- an official agency threshold (m), e.g. the station's declared
                         `critical` level. Needed only for time_to_threshold.
      official_status -- an agency-declared station-status word (e.g. "WATCH",
                         "CRITICAL"), if one has already been published for this
                         station/area. Per docs/EQUATIONS_FOR_AI.md step 5, an official
                         declaration always outranks this function's own Delta_k/Tk
                         computation.
      fresh          -- bool, whether `h_t`/`h_t_minus_k` are both within the source's
                         own stated update interval (default True -- the caller is
                         expected to have already checked this; pass False explicitly
                         for a stale reading).
      station_id     -- a label for the `why` text only, no effect on the decision.

    Returns {"decision": str, "confidence": "HIGH"|"MEDIUM"|"LOW"|"NONE",
    "level": "RED"|"YELLOW"|"GREEN"|"UNKNOWN", "checks": [str, ...],
    "gate": "LICENSED_WITHIN_ENVELOPE"|"REFUSED", "why": str} -- Jev-style decision
    vocabulary (see ARCHITECTURE.md §5): `gate` is
    LICENSED_WITHIN_ENVELOPE only when at least one real, fresh reading backed the
    `level`; REFUSED (never a bare 0/None) whenever there is nothing fresh to decide
    from -- BOT != ZERO applies to `gate` and `decision` exactly as it does to
    Delta_k/Tk above."""
    checks: list[str] = []
    h_t = inputs.get("h_t")
    station = inputs.get("station_id") or "this station"
    fresh = inputs.get("fresh", True)

    if h_t is None:
        checks.append("no current reading (h_t) -- nothing to decide from")
        return {
            "decision": "NO_READOUT -- no current reading for " + station,
            "confidence": "NONE",
            "level": "UNKNOWN",
            "checks": checks,
            "gate": "REFUSED",
            "why": "h_t missing; BOT != ZERO, this is not reported as GREEN/0",
        }
    if not fresh:
        checks.append("reading(s) flagged stale by the caller -- not trustworthy on their own")

    # Step 5 (official context): an official declaration always outranks our own
    # trend/time-to-threshold computation below.
    official_status = inputs.get("official_status")
    official_level = classify(official_status) if official_status else "UNKNOWN"
    if official_status:
        checks.append(f"official status word {official_status!r} -> {official_level}")

    # Steps 3-4: trend and time-to-threshold, only meaningful with a fresh epsilon and a
    # second reading.
    epsilon = inputs.get("epsilon")
    h_t_minus_k = inputs.get("h_t_minus_k")
    k = inputs.get("k", 1)
    delta = None
    tk = None
    if epsilon is not None:
        delta = delta_k(h_t, h_t_minus_k, epsilon)
        checks.append(f"delta_k = {delta}")
        theta = inputs.get("theta")
        if theta is not None:
            tk = time_to_threshold(h_t, delta, theta, k=k, epsilon=epsilon)
            checks.append(f"time_to_threshold = {tk}")
    else:
        checks.append("no epsilon given -- trend/time-to-threshold UNRESOLVED, not computed")

    if official_status and fresh:
        level = official_level
        gate = "LICENSED_WITHIN_ENVELOPE" if level != "UNKNOWN" else "REFUSED"
        confidence = "HIGH" if level != "UNKNOWN" else "NONE"
        decision_text = f"{level} -- official status {official_status!r} for {station}"
    elif delta is not None and delta.get("trend") not in (None, "NO_READOUT") and fresh:
        trend = delta["trend"]
        # Trend-only path (no official status backs this): never GREEN. RISING is at
        # least YELLOW; FLAT/FALLING is UNKNOWN unless h_t has already reached a
        # declared warning level (theta), in which case it is YELLOW too -- the trend
        # itself stays in `decision_text` only, it never promotes this to GREEN.
        if trend == "RISING":
            level = "YELLOW"
        elif theta is not None and h_t >= theta:
            level = "YELLOW"
        else:
            level = "UNKNOWN"
        gate = "LICENSED_WITHIN_ENVELOPE"
        confidence = "MEDIUM"
        if trend == "RISING" and tk and tk.get("value") is not None:
            decision_text = (f"RISING at {station}, ~{tk['value']:.2f} tick(s) to the "
                              f"declared threshold at the current rate (Delta_k={delta['value']:.3f} m)")
        elif trend == "RISING":
            decision_text = (f"RISING at {station} (Delta_k={delta['value']:.3f} m); "
                              "time-to-threshold REFUSED, see checks")
        elif trend == "FALLING":
            decision_text = f"FALLING at {station} (Delta_k={delta['value']:.3f} m)"
        else:
            decision_text = f"FLAT at {station} (|Delta_k|<=epsilon) -- no rise or fall detected"
    else:
        level = "UNKNOWN"
        gate = "REFUSED"
        confidence = "NONE"
        reason = "stale reading(s)" if not fresh else "insufficient inputs for a trend (need h_t_minus_k and epsilon)"
        decision_text = f"UNKNOWN for {station} -- {reason}"

    return {
        "decision": decision_text,
        "confidence": confidence,
        "level": level,
        "checks": checks,
        "gate": gate,
        "why": ("official declaration outranks own computation per docs/EQUATIONS_FOR_AI.md step 5"
                if official_status and fresh else
                "own Delta_k/Tk computation per docs/EQUATIONS_FOR_AI.md steps 3-4, "
                "never claims safety, never a prediction beyond the current observed rate"),
    }


# ===========================================================================
# M8 Jev Sandwich model (founder 2026-10-05, "ทางที่ 2 เลย").
#
# ETA honesty (relabelled 2026-10-07, release-accuracy fix): the mandatory RISING
# ETA this module ships (`rise_eta_hours_range` / `_rise_eta_one_threshold` below) is
# a LINEAR two-window slope extrapolation -- `time_to_threshold`/`delta_k`
# (PROP-FLOOD-02/01, already-registered, already-merged proposals) called TWICE, at
# two different lags, never a second difference. That is PROP-FLOOD-02's own
# documented two-lag usage (see `model_spec.json`'s PROP-FLOOD-02 entry and its
# `worked_example.note`), not PROP-FLOOD-11.
#
# PROP-FLOOD-11 (acceleration via the 2nd retained difference, D2, with a least-n
# quadratic search) is SEPARATELY REGISTERED in the `toledo` repo's own
# registry/proposals/flood_acceleration_eta.json (PR #65, "proposals/flood-time-to-
# bank-v3", MERGED into origin/main at commit 65297f05 -- VERIFIED by reading that
# file at that commit, not relayed). It is a PROPOSAL object (tier `Dr`, status
# `unverified`) -- registered, but NOT IMPLEMENTED in this release (v0.2 target).
# `_rise_eta_prop11_computation` below is the real PROP-FLOOD-11 quadratic (D2 != 0);
# it exists and is tested but `rise_eta_hours_range` (the function the answer path
# actually calls) never reaches it -- `rise_eta()` (which does call it) is itself
# never called from `kb.py`'s answer path either. `PROP11_ENABLED` flips True here
# (founder ruling 2026-10-06: "ระดับน้ำกำลังขึ้น ทำไมไม่คำนวณน้ำให้ว่าล้นตลิ่งในกี่
# ชั่วโมง" -- mandatory ETA whenever Z0 is RISING) and gates the shipped PROP-FLOOD-02
# two-window calculation, not PROP-FLOOD-11.
PROP11_ENABLED = True

# founder ruling 2026-10-06, verbatim: "ทำไงให้ปิดการเดา ... โดยปิดการ
# จำลองโหลดไปเลย" -- switch simulated load off entirely): the ONE flag that
# promises no simulation or modelled forecast ever feeds an answer.
# `water_balance.py`'s water-debt model is never imported by `kb.py`'s answer
# path at all (no gate needed -- there is nothing to turn off). PROP-FLOOD-06's
# own engine (`tools/backtest/compute_prop_flood_06_sammakorn.py`) IS reached
# from the answer path (`kb.py._answer_next_action`'s RED branch, the L5
# survival-card promotion) and folds in `forecast_rain_72h_per_model`, an
# external rain FORECAST promoter -- `kb.py` now actually reads this flag
# before calling it, so that promotion never fires while it is False (today's
# default). What this flag does NOT gate: PROP-FLOOD-01/02 (`delta_k`/
# `time_to_threshold` above) and PROP-FLOOD-11 (`rise_eta`, `PROP11_ENABLED`)
# are arithmetic on the station's own measured readings, never a simulation
# or an extrapolated load, and keep running under their own separate Toledo
# status regardless of this flag.
SIMULATION_ENABLED = False

# Colours (founder 2026-10-05, verbatim ladder) -- Thai labels for the 5-value vocabulary
# this module's sandwich functions return. GREEN/YELLOW/RED/UNKNOWN already existed
# (STATUS_TO_LEVEL above); ORANGE is NEW and is NOT an official agency tier -- it is
# FloodConnect's own label for "the water is coming, by our own KG-path/trend reading",
# chosen to echo the agency's own phrase "เฝ้าระวังและเตรียมพร้อม" (watch-and-prepare)
# without claiming to BE that agency phrase (the agency itself only ever declares
# ปกติ/เตือนภัย/วิกฤต -- three words, not four).
COLOUR_LABEL_TH = {
    "GREEN": "ปกติ", "YELLOW": "เฝ้าระวัง", "ORANGE": "เตรียมพร้อม",
    "RED": "วิกฤต", "UNKNOWN": "ไม่ทราบ",
}
ORANGE_NOTE = ("FloodConnect's own label, aligned with the agency phrase "
               "'เฝ้าระวังและเตรียมพร้อม'; not an official tier")
# `next_action.dual_state.current_local_state` (docs/INDICATORS.md) is still the closed
# 4-value RED/YELLOW/GREEN/UNKNOWN vocabulary pinned by tests/test_floodconnect_model.py
# -- wiring the new 5-value `sandwich.colour` into that field (P3, kb.py, out of scope
# here) folds ORANGE down to YELLOW so the existing closed vocabulary never silently
# grows a 5th value underneath callers that already pinned 4.
FOLD_TO_LEGACY = {"GREEN": "GREEN", "YELLOW": "YELLOW", "ORANGE": "YELLOW",
                   "RED": "RED", "UNKNOWN": "UNKNOWN"}

# An agency word that means "at or over the bank/critical level", read verbatim off the
# source -- never a number this module invents. `diff_wl_bank_text` (thaiwater) is
# matched by `startswith` because the real field carries a unit suffix, e.g.
# "ล้นตลิ่ง (ม.)" (MEASURED, 2026-10-05 live capture, station C.67).
_OVERBANK_WORD_PREFIXES = ("ล้นตลิ่ง",)
_OVERBANK_WORD_EXACT = ("เท่าระดับตลิ่ง",)


def trend_state(h_t, h_t_minus_k, epsilon, agency_trend=None) -> dict:
    """3-state trend (RISING/STABLE/FALLING/UNKNOWN) -- founder ruling 2026-10-05:
    "ไม่ต้องคิดความเร่งทุกกรณี ... มีสามสถานะ เพิ่มขึ้น เสถียร ลดลง" (no need to compute
    acceleration every time -- there are three states: rising, stable, falling). Wraps
    `delta_k()` (PROP-FLOOD-01): its FLAT is relabelled STABLE and its NO_READOUT is
    relabelled UNKNOWN for this vocabulary; the underlying `delta_k()` function and its
    own tests are untouched.

    `agency_trend`, when the source itself already publishes a trend word, is honoured
    THROUGH A CLOSED MAP ONLY (never a free-text passthrough) -- today no keyless source
    this repo calls publishes one (thaiwater's `percentageDiff` field lives on the keyed
    `twa` host, out of scope per this workspace's keyless-only rule), so `agency_trend`
    is always None in practice; the parameter exists so a future keyless source with a
    real trend word has somewhere honest to plug in without a second function.

    Returns {"trend": "RISING"|"STABLE"|"FALLING"|"UNKNOWN", "delta": float|None,
    "basis": "agency"|"PROP-FLOOD-01"|"none", "eq": "PROP-FLOOD-01"}."""
    _AGENCY_TREND_MAP = {"RISING": "RISING", "STABLE": "STABLE", "FALLING": "FALLING"}
    if agency_trend is not None:
        mapped = _AGENCY_TREND_MAP.get(agency_trend)
        if mapped is not None:
            return {"trend": mapped, "delta": None, "basis": "agency", "eq": "PROP-FLOOD-01"}
    d = delta_k(h_t, h_t_minus_k, epsilon)
    _RELABEL = {"RISING": "RISING", "FALLING": "FALLING", "FLAT": "STABLE", "NO_READOUT": "UNKNOWN"}
    trend = _RELABEL[d["trend"]]
    basis = "none" if trend == "UNKNOWN" else "PROP-FLOOD-01"
    return {"trend": trend, "delta": d["value"], "basis": basis, "eq": "PROP-FLOOD-01"}


def _usable_threshold(value, ground_level=None) -> "float | None":
    """Fix: a threshold the agency never actually
    set (an unset field defaulting to 0/null) must never be read as a real, crossable
    level -- MEASURED: EGAT's MKVKD01/MKVKD02 publish `critical_level_msl: 0`, which a
    bare `is not None` check happily accepted, so h=80.4 (a real MSL reading, far
    above 0) read as "at/over critical" on a threshold the agency never gave. The same
    is true of a `bank`/`critical` that is numerically at or below the station's own
    `ground_level` (BLGTU05/06, MKSND01, MKSNU03, NPNPU01: bank=ground=0) -- a station
    cannot be "over the bank" relative to a bank sitting at or under the ground itself;
    that is degenerate agency data, not a real threshold. Returns `None` (no usable
    threshold) for: `None`, non-numeric, `0`, or `<= ground_level` when a ground_level
    is actually known -- never a guessed substitute value."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if value == 0:
        return None
    if ground_level is not None:
        try:
            if value <= float(ground_level):
                return None
        except (TypeError, ValueError):
            pass
    return value


def bank_check(h_t, critical=None, bank=None, agency_word=None, ground_level=None) -> dict:
    """At/over the bank or critical level -- this check always runs BEFORE any trend or
    time-to-threshold computation (flooding is water over the bank first).

    The agency's own word decides first, matched verbatim (never guessed): a
    critical-like `STATUS_TO_LEVEL` word, `diff_wl_bank_text` starting with "ล้นตลิ่ง",
    or the exact word "เท่าระดับตลิ่ง" (at bank level) -- this branch is unaffected by
    `ground_level`/zero-threshold filtering below, since the agency's own word, when
    given, already supports the AT_OR_OVER claim on its own (that earlier fix: "a 0/null
    bank or critical... means no threshold UNLESS the agency's own word supports it").
    Otherwise this is PROP-FLOOD-02's own `h(t) >= theta` branch (no new equation):
    `h_t >= critical` or `h_t >= bank` (BMA's `min_bank`, same datum per the M7 note)
    -- the NEARER of the two thresholds decides (whichever is crossed first is the one
    that matters); `theta` in the result is that nearer threshold. A `bank`/`critical`
    that is `0`/null, or at-or-below the station's own `ground_level` when that is
    known, is never a usable threshold here (see `_usable_threshold`) -- this is the
    one place `ground_level` is used, and only as a sanity filter on the threshold
    itself, never to compare BMA/thaiwater datums against each other.

    Returns {"state": "AT_OR_OVER"|"BELOW"|"UNKNOWN", "basis": "agency_word"|"level",
    "theta": float|None, "gap": float|None}."""
    usable_critical = _usable_threshold(critical, ground_level)
    usable_bank = _usable_threshold(bank, ground_level)
    if agency_word:
        word = agency_word.strip()
        # fix (S3, founder subtractive-fix ruling 2026-10-06): "ล้นตลิ่ง"/"เท่าระดับ
        # ตลิ่ง"/"OVERBANK" are specifically a BANK-DIFF claim -- `collect.py`'s own
        # `_thaiwater_status_word` is the only place that ever produces "OVERBANK",
        # and it does so straight off the agency's `diff_wl_bank_text`, which the
        # feed computes AGAINST `min_bank` -- a `diff_wl_bank` computed against a
        # bank of 0 (MEASURED: BLGTU05/NPNPD02 and four siblings, 2026-10-06) is not
        # a real agency observation, it is `h - 0`. These words are therefore
        # trusted here only when at least one real threshold (`usable_critical`/
        # `usable_bank`) exists to anchor the claim against -- with none at all,
        # the word is ignored and this falls through to the level branch (UNKNOWN,
        # since there is no threshold to compare `h_t` against either). Every OTHER
        # `CRITICAL_LIKE_STATUS` word (an agency's own independently-reported
        # situation/status classification, never a bank-diff artifact) is still
        # trusted unconditionally, exactly as before.
        is_bank_diff_word = (
            any(word.startswith(p) for p in _OVERBANK_WORD_PREFIXES)
            or word in _OVERBANK_WORD_EXACT
            or word == "OVERBANK"
        )
        is_overbank_word = (
            is_bank_diff_word and (usable_critical is not None or usable_bank is not None)
        ) or (not is_bank_diff_word and word in CRITICAL_LIKE_STATUS)
        if is_overbank_word:
            theta = critical if critical is not None else bank
            gap = (h_t - theta) if (h_t is not None and theta is not None) else None
            return {"state": "AT_OR_OVER", "basis": "agency_word", "theta": theta, "gap": gap}
    thetas = [t for t in (usable_critical, usable_bank) if t is not None]
    if not thetas or h_t is None:
        theta = thetas[0] if thetas else None
        return {"state": "UNKNOWN", "basis": "level", "theta": theta, "gap": None}
    theta = min(thetas)
    if h_t >= theta:
        return {"state": "AT_OR_OVER", "basis": "level", "theta": theta, "gap": h_t - theta}
    return {"state": "BELOW", "basis": "level", "theta": theta, "gap": theta - h_t}


def rise_eta(h_t, h_t_minus_k, h_t_minus_2k, theta, k_ticks, tick_desc, epsilon,
             pump_state="UNDECLARED", max_gap=None, n_max=None) -> dict:
    """Caller contract: call this ONLY when `trend_state(...)` already said RISING --
    AT_BANK is checked first (flooding-is-over-the-bank-first still applies even while
    rising), then the trend itself; anything else returns NOT_APPLICABLE for both parts,
    this function never re-derives the trend from a different lag.

    `tk` is PROP-FLOOD-02's own time_to_threshold (registered proposal, same Toledo
    PR/tier as PROP-FLOOD-01) via `delta_k`/`time_to_threshold` above -- unchanged
    equation, just called with the RISING precondition already satisfied by the caller.

    `prop11` is PROP-FLOOD-11 (2nd retained difference / acceleration, L(n) = h + n*delta
    + n*(n+1)/2*D2) -- a REGISTERED Toledo proposal (tier Dr, PR #65 merged 2026-10-06
    at 65297f05), but NOT IMPLEMENTED in this release (v0.2 target): this function is
    kept as the standalone PROP-FLOOD-11 quadratic (tested, never called from any
    answer path -- `kb.py` never calls `rise_eta()` itself). It returns
    `{"status": "GATED", "reason": "PROP-FLOOD-11 registered but not wired into
    any answer path (v0.2)"}` unless the module-level `PROP11_ENABLED` flag is set
    True (never by a caller passing an argument -- this is a module switch).
    When enabled, precedence is AT_BANK > NO_READOUT > PUMP_STATE_CHANGED >
    PUMP_STATE_UNDECLARED > SPARSE_SERIES > NO_RISE > NOT_WITHIN_HORIZON > OK.
    `pump_state` is one of "UNDECLARED"|"RUNNING"|"OFF"|"CHANGED" (never a bool -- a pump
    turning on/off mid-window invalidates a linear/quadratic extrapolation of the raw
    water level, a materially different failure than simply never having declared pump
    state at all)."""
    bank = bank_check(h_t, critical=theta)
    if bank["state"] == "AT_OR_OVER":
        tk = {"value": None, "reason": "AT_BANK"}
        prop11 = {"status": "AT_BANK"}
        return {"tk": tk, "prop11": prop11}

    trend = trend_state(h_t, h_t_minus_k, epsilon)
    if trend["trend"] != "RISING":
        return {"tk": {"value": None, "reason": "NOT_APPLICABLE"},
                "prop11": {"status": "NOT_APPLICABLE"}}

    d1 = delta_k(h_t, h_t_minus_k, epsilon)
    tk = time_to_threshold(h_t, d1, theta, k=k_ticks, epsilon=epsilon)
    if "unit" in tk:
        tk["unit"] = tick_desc

    if not PROP11_ENABLED:
        return {"tk": tk, "prop11": {"status": "GATED",
                                      "reason": "PROP-FLOOD-11 registered but not wired into any answer path (v0.2)"}}

    prop11 = _rise_eta_prop11_computation(
        h_t, h_t_minus_k, h_t_minus_2k, theta, epsilon, pump_state, max_gap, n_max, d1)
    return {"tk": tk, "prop11": prop11}


def _rise_eta_prop11_computation(h_t, h_t_minus_k, h_t_minus_2k, theta, epsilon,
                                  pump_state, max_gap, n_max, d1) -> dict:
    """PROP-FLOOD-11 proper -- only ever called from `rise_eta()` above, and only when
    `PROP11_ENABLED` is True (test-only today, PR #65 still OPEN). Kept as its own
    function so `rise_eta()`'s gate stays a single, auditable `if`."""
    if h_t_minus_2k is None:
        return {"status": "SPARSE_SERIES"}
    if pump_state == "CHANGED":
        return {"status": "PUMP_STATE_CHANGED"}
    if pump_state == "UNDECLARED":
        return {"status": "PUMP_STATE_UNDECLARED"}
    delta = d1["value"]
    d2 = (h_t - 2 * h_t_minus_k + h_t_minus_2k)
    if delta is None or delta <= epsilon:
        return {"status": "NO_RISE"}
    # Solve L(n) = h_t + n*delta + n*(n+1)/2*d2 = theta for the smallest positive n.
    if abs(d2) < 1e-12:
        n = (theta - h_t) / delta
    else:
        a, b, c = d2 / 2.0, delta + d2 / 2.0, h_t - theta
        disc = b * b - 4 * a * c
        if disc < 0:
            return {"status": "NOT_WITHIN_HORIZON"}
        roots = [(-b + disc ** 0.5) / (2 * a), (-b - disc ** 0.5) / (2 * a)]
        positive = [r for r in roots if r > 0]
        if not positive:
            return {"status": "NOT_WITHIN_HORIZON"}
        n = min(positive)
    if n_max is not None and n > n_max:
        return {"status": "NOT_WITHIN_HORIZON"}
    if max_gap is not None and (theta - h_t) > max_gap:
        return {"status": "NOT_WITHIN_HORIZON"}
    return {"status": "OK", "n": n}


def _rise_eta_one_threshold(h_t, h_short_prev, short_hours, h_long_prev, long_hours,
                             theta, epsilon, pump_state) -> dict:
    """One threshold's worth of `rise_eta_hours_range` below -- split out so the
    caller can run it twice (warning, critical/bank) without duplicating the
    precedence logic. Never called directly by anything outside this module."""
    if theta is None:
        return None
    bank = bank_check(h_t, critical=theta)
    if bank["state"] == "AT_OR_OVER":
        return {"status": "AT_BANK"}
    if pump_state == "CHANGED":
        return {"status": "PUMP_STATE_CHANGED"}
    if pump_state == "UNDECLARED":
        return {"status": "PUMP_STATE_UNDECLARED"}
    if h_short_prev is None or h_long_prev is None or short_hours is None or long_hours is None:
        return {"status": "NO_READOUT"}
    d_short = delta_k(h_t, h_short_prev, epsilon)
    d_long = delta_k(h_t, h_long_prev, epsilon)
    if d_short["trend"] == "NO_READOUT" or d_long["trend"] == "NO_READOUT":
        return {"status": "NO_READOUT"}
    if d_short["trend"] != "RISING" and d_long["trend"] != "RISING":
        return {"status": "NO_RISE"}
    tk_short = time_to_threshold(h_t, d_short, theta, k=short_hours, epsilon=epsilon)
    tk_long = time_to_threshold(h_t, d_long, theta, k=long_hours, epsilon=epsilon)
    hours = [tk["value"] for tk in (tk_short, tk_long) if tk.get("value") is not None]
    if not hours:
        return {"status": "NOT_WITHIN_HORIZON"}
    return {"status": "OK", "range_h": [round(min(hours), 1), round(max(hours), 1)],
            "short_h": round(tk_short["value"], 1) if tk_short.get("value") is not None else None,
            "long_h": round(tk_long["value"], 1) if tk_long.get("value") is not None else None}


def rise_eta_hours_range(h_t, h_short_prev, short_hours, h_long_prev, long_hours,
                          theta_warn=None, theta_crit=None, epsilon=0.01,
                          pump_state="UNDECLARED") -> dict:
    """Founder-mandated time-to-bank ETA, in hours, reported as a RANGE spanning the
    CURRENT slope (`short_hours`, the latest interval of the source's own series --
    e.g. the BMA StationDetail 5-min step) AND a longer-window slope (`long_hours`,
    e.g. the existing 30-60 min trend lag) -- founder ruling 2026-10-06, verbatim:
    "ถ้าน้ำขึ้นต้องบังคับให้คำนวณอัตราล้นตลิ่งจากความชันปัจจุบัน" ("when the water is
    rising, you MUST compute the overflow rate from the CURRENT slope"), restated the
    same day as "ระดับน้ำกำลังขึ้น ทำไมไม่คำนวณน้ำให้ว่าล้นตลิ่งในกี่ชั่วโมง".

    This is PROP-FLOOD-01/02 arithmetic (`delta_k`/`time_to_threshold`, already-
    registered, already-merged Toledo proposals) called TWICE, at two different lags
    passed directly in HOURS (so `time_to_threshold`'s own `value` comes out in hours,
    never a tick count needing a second conversion). Ships and is labelled as
    PROP-FLOOD-02 (linear, two windows), PROPOSAL -- NOT PROP-FLOOD-11. PROP-FLOOD-11
    (the acceleration-aware quadratic, 2nd retained difference D2, with a least-n
    search) is a SEPARATE, also-registered Toledo proposal (tier Dr, PR #65 merged
    2026-10-06) that is NOT IMPLEMENTED in this release (v0.2 target) -- see
    `_rise_eta_prop11_computation`, which exists and is tested but is never reached
    from this function or from `kb.py`'s answer path.

    Gated by the module flag `PROP11_ENABLED` (named for the still-unimplemented
    PROP-FLOOD-11 work this module also carries, not for this function's own
    PROP-FLOOD-02 calculation) and the SAME refusal precedence `rise_eta()` uses:
    AT_BANK > NO_READOUT > PUMP_STATE_CHANGED/PUMP_STATE_UNDECLARED > NO_RISE >
    NOT_WITHIN_HORIZON (checked per threshold; this repo's BMA series is dense 5-min
    data, so a prev reading entirely missing or outside the per-lag tolerance is
    reported NO_READOUT by the caller before this function is reached).

    `pump_state` is the SAME 3-way flag (`CHANGED`/`UNCHANGED`/`UNDECLARED`) as
    `rise_eta()` -- this function never defaults it to `UNCHANGED` on its own; a
    caller with no declared pump for the station in question must say so (see
    `kb.py`'s own caller-side comment for WL.SMK.01, which documents why it passes
    `UNCHANGED` rather than `UNDECLARED` for that specific station).

    Returns `{"status": "GATED", ...}` (module switch) when `PROP11_ENABLED` is
    False. Otherwise `{"warning": <per-threshold result or None>, "critical": <per-
    threshold result or None>}`, each either `None` (that theta was not given),
    `{"status": "AT_BANK"|"PUMP_STATE_CHANGED"|"PUMP_STATE_UNDECLARED"|"NO_READOUT"|
    "NO_RISE"|"NOT_WITHIN_HORIZON"}`, or `{"status": "OK", "range_h": [lo, hi],
    "short_h": x, "long_h": y}` -- `range_h` is `[min, max]` of the two slopes' own
    ETA in hours, never averaged, never a single number standing in for both."""
    if not PROP11_ENABLED:
        return {"status": "GATED", "reason": "PROP-FLOOD-02 ETA switched off (PROP11_ENABLED=False)"}
    return {
        "warning": _rise_eta_one_threshold(h_t, h_short_prev, short_hours, h_long_prev,
                                            long_hours, theta_warn, epsilon, pump_state),
        "critical": _rise_eta_one_threshold(h_t, h_short_prev, short_hours, h_long_prev,
                                             long_hours, theta_crit, epsilon, pump_state),
    }


def colour_ladder(z0: dict) -> dict:
    """Z0 (the point itself) only -- `z0` = {status_word, h, warning, critical, bank,
    ground_level, trend, fresh, fault} (fault/trend/fresh default to None/None/True
    when absent; ground_level defaults to None, read-only as a bank/critical sanity
    filter -- see `bank_check`/`_usable_threshold`, the earlier fix).

    Order: not fresh, a sensor fault, or no threshold/status at all -> UNKNOWN (never a
    guess). `bank_check` AT_OR_OVER -> RED. RISING with a published warning level reached
    but critical not yet reached -> ORANGE (FloodConnect's own label, see `ORANGE_NOTE`;
    needs an agency `warning` level, which BMA publishes and most thaiwater stations do
    not -- no ORANGE-local without one). An agency watch/warning word -> YELLOW. A
    recognised normal word -> GREEN.

    Returns {"colour", "basis", "reasons": [str, ...]}."""
    if not z0.get("fresh", True):
        return {"colour": "UNKNOWN", "basis": "STALE", "reasons": ["Z0 reading not fresh"]}
    if z0.get("fault"):
        return {"colour": "UNKNOWN", "basis": "FAULT", "reasons": ["sensor/equipment fault word"]}

    h = z0.get("h")
    critical = z0.get("critical")
    bank = z0.get("bank")
    ground_level = z0.get("ground_level")
    warning = z0.get("warning")
    status_word = z0.get("status_word")
    trend = z0.get("trend")

    bc = bank_check(h, critical=critical, bank=bank, agency_word=status_word,
                     ground_level=ground_level)
    if bc["state"] == "AT_OR_OVER":
        return {"colour": "RED", "basis": bc["basis"], "reasons": ["at/over agency bank or critical level"]}

    if trend == "RISING" and warning is not None and critical is not None and h is not None \
            and warning <= h < critical:
        return {"colour": "ORANGE", "basis": "RISING_ABOVE_WARNING", "reasons": [ORANGE_NOTE]}

    classified = classify(status_word) if status_word else "UNKNOWN"
    if classified == "YELLOW":
        return {"colour": "YELLOW", "basis": "agency_word", "reasons": ["agency watch/warning word"]}
    if classified == "GREEN":
        return {"colour": "GREEN", "basis": "agency_word", "reasons": ["agency normal word"]}
    if critical is None and bank is None and warning is None and not status_word:
        return {"colour": "UNKNOWN", "basis": "NO_THRESHOLD", "reasons": ["no agency threshold or status published"]}
    return {"colour": "UNKNOWN", "basis": "INSUFFICIENT", "reasons": ["no classifiable basis"]}


# fix (S1b): UNKNOWN dominates GREEN -- a ring that mixes a real
# GREEN reading with an unread/stale UNKNOWN row must never report a confident
# "worst=GREEN" (it cannot know the ring is calm when part of it was never read);
# UNKNOWN still loses to any actually-decided alert colour (YELLOW/ORANGE/RED).
_COLOUR_RANK = {"GREEN": 0, "UNKNOWN": 1, "YELLOW": 2, "ORANGE": 3, "RED": 4}

# Relations with no declared source behind them -- a bare agency code-prefix guess
# (SAME_CODE_FAMILY, never a verified same-canal claim), or a reach-snap pair whose
# own agency-declared river names disagree (SAME_REACH_RIVER_MISMATCH -- the KG
# geometry put them on the same reach, but their own agency names say otherwise).
# Founder subtractive-fix ruling (2026-10-06): these stay visible as facts with
# their true relation label, but must never set a ring's layer colour or the
# card's colour/verdict. SAME_SUBBASIN (a bare same-huge-sub-basin membership, no
# canal/reach claim at all) carries the same restriction and is excluded at its
# own call sites in `kb.py`.
HEURISTIC_RELATIONS = frozenset({"SAME_CODE_FAMILY", "SAME_REACH_RIVER_MISMATCH"})


def is_colour_eligible(row: dict) -> bool:
    """True iff `row` (a ring member dict with a `relation` key) may legally set a
    layer/card colour -- False for any relation in `HEURISTIC_RELATIONS` or a row
    whose own `basis` is tagged a heuristic, no-declared-source join
    ("NAME_JOIN-heuristic"). The row is never dropped from `facts`/the raw station
    list by this function -- callers that build the COLOUR view filter through
    this; callers that build the FACTS view do not."""
    if (row.get("relation") or "") in HEURISTIC_RELATIONS:
        return False
    if (row.get("basis") or "") == "NAME_JOIN-heuristic":
        return False
    return True


def ring_readout(rows: list, relation: str) -> dict:
    """Summarise one ring's worth of station rows (Z1/Z2/Z3 -- the caller already picked
    which rows belong to this ring/relation; this function does no KG traversal itself,
    see `tools/kg/rings.py`, out of scope for this part). Each row is
    {"id", "status_word"?, "colour"?, "trend"?, "fresh"?} -- `colour` is read straight off
    the row if the caller already ran `colour_ladder` on it, else derived here via
    `classify(status_word)`.

    fix (founder ruling 2026-10-06): a NON-FRESH row's own colour is never trusted for
    `worst` any more (treated as UNKNOWN instead) -- a stale RED reading could
    otherwise still drag the whole ring to RED. And `worst` starts UNDECIDED, not
    forced to UNKNOWN, so a ring whose every row is fresh and GREEN can actually
    report GREEN (before this fix, `worst` began at UNKNOWN and GREEN's own rank
    never outranked it, so a layer could never be GREEN at all -- MEASURED: 0 of
    4296 real layer values were GREEN). An empty ring (no rows at all -- no
    declared KG edge reaches it) still reports UNKNOWN, unchanged. UNKNOWN still
    dominates GREEN whenever the two are mixed in the same ring (any row this
    function cannot decide, fresh or not, outranks a merely-GREEN one).

    Returns {"worst": RED|YELLOW|GREEN|UNKNOWN, "any_rising", "at_or_over": [ids], "n",
    "n_fresh", "relation"}."""
    worst = None
    worst_rank = -1
    at_or_over = []
    any_rising = False
    n_fresh = 0
    for row in rows:
        fresh = row.get("fresh", True)
        if fresh:
            n_fresh += 1
        colour = row.get("colour") or classify(row.get("status_word"))
        if not fresh:
            colour = "UNKNOWN"  # a stale reading carries no current-colour claim
        rank = _COLOUR_RANK.get(colour, 0)
        if rank > worst_rank:
            worst_rank = rank
            worst = colour
        if fresh and row.get("trend") == "RISING":
            any_rising = True
        if colour == "RED":
            at_or_over.append(row.get("id"))
    if worst is None:
        worst = "UNKNOWN"
    return {"worst": worst, "any_rising": any_rising, "at_or_over": at_or_over,
            "n": len(rows), "n_fresh": n_fresh, "relation": relation}


def _sandwich_read_top(z3: dict, upstream_middle: list | None = None) -> dict:
    """Step READ_TOP: is there anything alarming upstream? `z3` =
    {"stations": [{"id","colour"?,"status_word"?,"relation","trend"?,"fresh"?}, ...],
    "dams": [{"id","released"?,"inflow"?,"fresh"?}, ...], "official": "NOT_WIRED"|...}.
    `upstream_middle`, new (S2, founder 2026-10-05) -- the Z1/Z2 rows already read on
    relation UPSTREAM_CHAIN/UPSTREAM_REACH ("the nearest KG-connected upstream
    stations"); counted exactly like a Z3 UPSTREAM_PATH row for both the alert and
    the `upstream_read` count below, never for a SAME_REACH/DOWNSTREAM_CHAIN/OUTLET
    row (those are never "upstream of Z0").

    `alert` is True iff: an UPSTREAM station (UPSTREAM_PATH in z3, or
    UPSTREAM_CHAIN/UPSTREAM_REACH in `upstream_middle`) is fresh and RED, or fresh and
    RISING; or a dam reports `released > inflow` (both agency values, non-null,
    fresh). RISING-scope is deliberately restricted to upstream relations, not every
    Z3 station -- a 15,689 km^2 sub-basin's rain-season base rate of "something
    upstream is rising" would otherwise make `top_alert` almost always True. A
    SAME_SUBBASIN/SAME_REACH/DOWNSTREAM_CHAIN RED reading is still carried (see
    `kb.py`'s `facts` passthrough, which reads every RED Z3 row regardless of
    relation), just never as a `top_alert` trigger here.

    `upstream_read` (S2) counts the FRESH upstream rows actually seen across both
    groups -- the caller (`sandwich_decision`) refuses to claim "top calm" when this
    is 0, per the founder's "never claim top calm unless at least one fresh upstream
    station was actually read" rule (an earlier pass: 644/645 AGREE answers had read
    zero upstream stations). An official keyless warning feed is NOT_WIRED today (no
    such source exists in this repo's registry.yaml yet) -- `official` is carried
    through verbatim so a caller/answer never claims a wired feed that doesn't exist."""
    stations = z3.get("stations") or []
    dams = z3.get("dams") or []
    upstream_middle = upstream_middle or []
    official = z3.get("official", "NOT_WIRED")

    any_fresh = (any(s.get("fresh", True) for s in stations)
                 or any(d.get("fresh", True) for d in dams)
                 or any(m.get("fresh", True) for m in upstream_middle))
    if not any_fresh:
        return {"alert": False, "fresh": False, "hits": [], "upstream_read": 0}

    upstream_rows = (
        [s for s in stations if (s.get("relation") or "") == "UPSTREAM_PATH"]
        + [m for m in upstream_middle
           if (m.get("relation") or "") in ("UPSTREAM_CHAIN", "UPSTREAM_REACH")]
    )
    upstream_read = sum(1 for r in upstream_rows if r.get("fresh", True))

    hits = []
    for s in upstream_rows:
        # fix : a STALE upstream row must never raise
        # the top alert -- `hits` used to ignore `fresh` entirely.
        if not s.get("fresh", True):
            continue
        colour = s.get("colour") or classify(s.get("status_word"))
        relation = s.get("relation") or "UNKNOWN"
        if colour == "RED":
            hits.append((s.get("id"), s.get("status_word") or colour, "TOP_CRITICAL_" + relation))
        elif s.get("trend") == "RISING":
            hits.append((s.get("id"), "RISING", "TOP_RISING_" + relation))
    for d in dams:
        released, inflow = d.get("released"), d.get("inflow")
        if d.get("fresh", True) and released is not None and inflow is not None and released > inflow:
            hits.append((d.get("id"), "released>inflow", "TOP_DAM_RELEASE_EXCEEDS_INFLOW"))

    return {"alert": bool(hits), "fresh": True, "hits": hits, "official": official,
            "upstream_read": upstream_read}


def _sandwich_extract_middle(middle: list) -> dict:
    """Step EXTRACT_MIDDLE: does the middle (Z1/Z2, "คลองใกล้เรา"/"พื้นที่น้ำเหนือเรา")
    confirm water coming toward Z0 along the KG path? `middle` = [{"id","relation" in
    ("UPSTREAM_CHAIN","UPSTREAM_REACH","OUTLET", ...),"trend"?,"colour"?,"status_word"?,
    "fresh"?}, ...]. Confirms True iff any row on relation UPSTREAM_CHAIN/UPSTREAM_REACH
    is RISING or at/over critical (colour RED). `observed` is False only when `middle` is
    empty (no row seen at all -- MIDDLE_UNOBSERVED, not MIDDLE_NOT_RISING, a distinct
    non-value per BOT != ZERO)."""
    if not middle:
        return {"confirms": False, "observed": False, "toward": []}
    toward = [m for m in middle if m.get("relation") in ("UPSTREAM_CHAIN", "UPSTREAM_REACH")]
    confirms = False
    for m in toward:
        colour = m.get("colour") or classify(m.get("status_word"))
        if m.get("trend") == "RISING" or colour == "RED":
            confirms = True
    return {"confirms": confirms, "observed": True, "toward": toward}


def sandwich_decision(z0: dict, z3: dict, middle: list | None = None, facts=()) -> dict:
    """The Jev Sandwich: read bottom (Z0, the point) and top (Z3, the basin plus any
    Z1/Z2 upstream rows the caller already read) together; agree -> decide; conflict
    -> extract the middle (Z1/Z2) along the KG path toward the point, THEN decide.
    `middle`, when given, is used BOTH for the upstream-read check in READ_TOP (S2)
    and, on conflict, for EXTRACT_MIDDLE -- a caller that already reads Z1/Z2
    unconditionally (`kb.py`, 2026-10-05 fix) passes it in on this single call;
    `middle=None` keeps the older two-call contract (`needs_middle=True`, no colour,
    caller re-calls with `middle` filled in) for a caller that still wants to fetch
    it only on conflict.

    Order: READ_BOTTOM (`colour_ladder(z0)`) -- UNKNOWN is final (REFUSED, no basin can
    rescue an unread point); RED is final too (a local at/over-critical reading always
    wins, the middle is never needed for it). READ_TOP (`_sandwich_read_top`, now also
    given any UPSTREAM_CHAIN/UPSTREAM_REACH rows already in `middle`). TOP_UNREAD (top
    itself could not be read at all) and TOP_NO_UPSTREAM (S2: nothing on an actual
    upstream relation was ever read, so "calm" cannot be claimed) both keep Z0's OWN
    colour -- never UNKNOWN, never lower than Z0's own agency word (S1). AGREE (top has
    no alert, and at least one upstream row WAS read) -> Z0's own colour stands.
    CONFLICT (Z0 GREEN/YELLOW but top alert) with no `middle` yet -> `needs_middle=True`.
    EXTRACT_MIDDLE -> ORANGE if the middle confirms water coming along the KG path
    toward Z0, else YELLOW (MIDDLE_NOT_RISING, or MIDDLE_UNOBSERVED at LOW confidence if
    the middle was never actually read). Finally, OUTLET_CRITICAL (S2b): a fresh RED
    OUTLET row in `middle` (a drainage constraint, never "water coming" since it is
    downstream) raises the result to at least YELLOW, whatever path got there -- except
    when Z0 itself is already UNKNOWN or RED (outlet info never promotes an unread point,
    and RED already is the ceiling).

    `facts` is a caller-supplied passthrough (fix: the caller,
    `kb.py`'s `_answer_sandwich`, takes every Z3 station at/over critical, sorted
    UPSTREAM_PATH-then-OUTLET-then-SAME_SUBBASIN and nearest-first within each
    relation, capped at `_SANDWICH_FACTS_CAP` -- the KG traversal/ordering is out of
    scope here, see `tools/kg/rings.py`/P3) -- this function never computes it, only
    carries it in the result so the answer layer has one place to read it from.

    Returns {"colour", "label_th", "level"(FOLD_TO_LEGACY'd), "official_tier": bool,
    "steps": [...], "reasons": [...], "needs_middle": bool,
    "confidence": "HIGH"|"MEDIUM"|"LOW"|"NONE", "gate": "LICENSED_WITHIN_ENVELOPE"|
    "REFUSED", "facts": [...]}."""
    steps = ["READ_BOTTOM"]
    facts = list(facts)
    bottom = colour_ladder(z0)

    # fix (founder ruling 2026-10-06, "เจ้าพระยาคือทางออก"): a row tagged
    # OUTLET_MAIN_STEM -- a Z3 station the caller (`kb.py`) re-labelled off a
    # SAME_SUBBASIN-only KG join because its OWN agency-declared river name is the
    # Chao Phraya main stem (our drainage's real outlet river, even where the KG
    # has no walked SAME_REACH/UPSTREAM edge from Sammakorn's own Saen Saep reach
    # all the way to it) -- counts as a real outlet exactly like a declared
    # canalchain OUTLET row. A bare SAME_SUBBASIN row (same huge sub-basin only,
    # no river-name or declared-edge basis -- e.g. a side canal states away) is
    # never promoted here; that relabelling decision is `kb.py`'s, not this
    # function's, and is never fabricated as a declared KG edge.
    outlet_rows = [m for m in (middle or [])
                   if (m.get("relation") or "") in ("OUTLET", "OUTLET_MAIN_STEM")]
    outlet_critical = any(
        m.get("fresh", True) and (m.get("colour") or classify(m.get("status_word"))) == "RED"
        for m in outlet_rows)

    def _result(colour, reasons, needs_middle, confidence, gate, official_tier):
        # fix (S2b): a fresh RED OUTLET never gets to upgrade an UNKNOWN/already-RED
        # result, but does raise anything else to at least YELLOW -- it is a
        # drainage constraint on US, read regardless of which ladder branch decided
        # `colour` (AGREE/TOP_NO_UPSTREAM/TOP_UNREAD/EXTRACT_MIDDLE all pass through
        # here identically, so OUTLET_CRITICAL is never silently lost on one path).
        if (outlet_critical and colour not in (None, "UNKNOWN", "RED")
                and _COLOUR_RANK.get(colour, 0) < _COLOUR_RANK["YELLOW"]):
            colour = "YELLOW"
            reasons = list(reasons) + ["OUTLET_CRITICAL"]
        return {
            "colour": colour,
            "label_th": COLOUR_LABEL_TH.get(colour, COLOUR_LABEL_TH["UNKNOWN"]) if colour else None,
            "level": FOLD_TO_LEGACY.get(colour, "UNKNOWN") if colour else None,
            "official_tier": official_tier,
            "steps": steps,
            "reasons": reasons,
            "needs_middle": needs_middle,
            "confidence": confidence,
            "gate": gate,
            "facts": facts,
        }

    if bottom["colour"] == "UNKNOWN":
        return _result("UNKNOWN", [bottom["basis"]] + bottom["reasons"], False, "NONE", "REFUSED", False)
    if bottom["colour"] == "RED":
        steps.append("AT_OR_OVER_LOCAL")
        return _result("RED", ["Z0 at/over bank or critical -- local critical always wins"],
                        False, "HIGH", "LICENSED_WITHIN_ENVELOPE", True)

    steps.append("READ_TOP")
    upstream_middle = [m for m in (middle or [])
                        if (m.get("relation") or "") in ("UPSTREAM_CHAIN", "UPSTREAM_REACH")]
    top = _sandwich_read_top(z3, upstream_middle=upstream_middle)
    if not top.get("fresh", True):
        # fix : TOP_UNREAD used to discard Z0's own agency word and
        # return bare UNKNOWN -- S1 forbids ever showing a colour lower than Z0's own
        # word, and UNKNOWN must never replace a decided colour.
        return _result(bottom["colour"], ["TOP_UNREAD"], False, "LOW",
                        "LICENSED_WITHIN_ENVELOPE", False)

    if top.get("upstream_read", 0) == 0:
        # fix (S2): no fresh UPSTREAM_PATH/UPSTREAM_CHAIN/UPSTREAM_REACH row was ever
        # read -- "top calm" cannot honestly be claimed (644/645 AGREE answers,
        # an earlier pass, MEASURED 2026-10-05). Z0's own colour still stands (S1),
        # just never promoted to a confident "ปกติ"/official_tier claim.
        return _result(bottom["colour"], ["TOP_NO_UPSTREAM"], False, "LOW",
                        "LICENSED_WITHIN_ENVELOPE", False)

    if not top["alert"]:
        steps.append("AGREE")
        colour = bottom["colour"]
        confidence = "MEDIUM" if top.get("official") == "NOT_WIRED" else "HIGH"
        return _result(colour, ["top calm; Z0's own reading stands"], False, confidence,
                        "LICENSED_WITHIN_ENVELOPE", colour != "ORANGE")

    steps.append("CONFLICT")
    if middle is None:
        return _result(None, [h[2] for h in top["hits"]], True, "LOW", "REFUSED", False)

    steps.append("EXTRACT_MIDDLE")
    mid = _sandwich_extract_middle(middle)
    top_reasons = [h[2] for h in top["hits"]]
    if mid["confirms"]:
        colour = "ORANGE"
        reasons = top_reasons + ["WATER_COMING_ON_KG_PATH"]
        confidence = "MEDIUM"
    elif mid["observed"]:
        colour = "YELLOW"
        reasons = top_reasons + ["MIDDLE_NOT_RISING"]
        confidence = "MEDIUM"
    else:
        colour = "YELLOW"
        reasons = top_reasons + ["MIDDLE_UNOBSERVED"]
        confidence = "LOW"
    # fix: the middle's own verdict can never DOWNGRADE Z0's own
    # bottom colour -- a local ORANGE (RISING above the agency warning level) plus a
    # top alert is itself the founder's ORANGE-agreement case, not a reason to fall
    # back to YELLOW just because the middle ring didn't happen to confirm it too.
    # Take the higher-risk (higher `_COLOUR_RANK`) of {bottom colour, middle verdict}.
    if _COLOUR_RANK.get(bottom["colour"], 0) > _COLOUR_RANK.get(colour, 0):
        colour = bottom["colour"]
        reasons = top_reasons + [f"BOTTOM_{bottom['colour']}_NEVER_DOWNGRADED"] + reasons[len(top_reasons):]
        confidence = "MEDIUM"
    steps.append("DECIDE")
    return _result(colour, reasons, False, confidence, "LICENSED_WITHIN_ENVELOPE", colour != "ORANGE")
