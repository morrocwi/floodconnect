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
# (v0.1.2, regate finding #2/#5): readout.py and kb.py import the three derived sets
# below instead of keeping their own copy. Every word here is either an agency
# station-status word this repo already classified before v0.1.2 (CRITICAL/OVERBANK/
# WATCH/NORMAL, BMA DDS "วิกฤต(ิ)"/"เตือนภัย"/"ปกติ") or a `thaiwater_situation_N`
# code this repo now STORES verbatim in `observations.status` (see
# `collect.collect_thaiwater_waterlevel`). The 1-5 ordinal direction is MEASURED
# (2026-10-04, one live GET of api-v3.thaiwater.net .../public/waterlevel, 808
# stations): `situation_level == 5` co-occurred with `diff_wl_bank_text` == "ล้นตลิ่ง
# (ม.)" (the agency's own overflow word) in every checked record, and
# `storage_percent` (bank-fill %, also agency-published) rises monotonically with the
# code (1: <10%, 2: 10-30%, 3: 30-70%, 4: 70-100%, 5: >100%/overflow). The exact Thai
# label text thaiwater.net itself prints for levels 1-4 was NOT independently
# confirmed (the legend page is JS-rendered; a plain GET could not read it) -- that
# label wording is OPEN, see docs/INDICATORS.md; the ORDINAL mapping below is
# MEASURED-derived, not a guessed label.
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
    -> YELLOW. Fix (2026-10-04, regate finding #2): a station with NO agency threshold
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
