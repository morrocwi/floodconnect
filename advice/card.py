"""The M8 emergency card -- `emergency_card.schema.json`'s builder.

This is the FIRST audience (emergency card first -> evidence -> policy_gap_record,
per the M8 task's own ruling). It takes the `jev_decision` block (`kb.py._answer_sandwich`'s
output, possibly carrying P-C/P-D's `advice` sub-object once those parts exist) and
returns the compact card dict. Never raises on a missing `gloss_th.yaml` entry for a
real colour5 value -- that table is closed over exactly those 5 values (see that file's
own header note on the "keyed by reason code" deviation) -- but DOES raise (by design,
tests check this) if a caller ever manages to pass a colour outside that 5-value set,
since that would mean a new, un-glossed colour silently got a blank `now_th`.
"""
from __future__ import annotations

import functools
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
_GLOSS_PATH = _HERE / "gloss_th.yaml"


@functools.lru_cache(maxsize=1)
def _gloss() -> dict:
    import yaml
    with open(_GLOSS_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    missing = {"GREEN", "YELLOW", "ORANGE", "RED", "UNKNOWN"} - set(data or {})
    if missing:
        raise ValueError(f"advice/gloss_th.yaml is missing entries for: {sorted(missing)}")
    return data


def _now_th(colour: str) -> str:
    """Raises KeyError for anything not in the closed colour5 set -- a caller must
    never see a blank now_th for an un-glossed colour (fail-closed, per the file's own
    header note: 'a reason code [here: colour] with no entry raises an error in
    tests')."""
    gloss = _gloss()
    if colour not in gloss:
        raise KeyError(f"advice/gloss_th.yaml has no now_th entry for colour={colour!r}")
    return gloss[colour]["now_th"]


# Short agency-code labels for the CARD's own hotlines list -- kb.py's
# HOTLINES_NATIONWIDE/HOTLINES_BANGKOK_ONLY numbers are reused verbatim (never a second,
# divergent number list); only the Thai label text is shortened here, token-budget
# driven (the fuller descriptive label is still available via `--verbose`'s
# `next_action.who_to_call` -- see kb.py's own `_who_to_call` -- so repeating the
# same long text a second time inside the same answer was pure duplication, not
# new information). The agency identity itself is never dropped, only its
# description. kb.py's own `_who_to_call` now uses this same short-label pattern
# (a second table, same values, to avoid a circular import) for its own
# non-verbose `who_to_call.hotlines`.
_SHORT_HOTLINE_LABEL = {
    "1669": "สพฉ.",
    "1784": "ปภ.",
    "1555": "กทม.",
    "1130": "กฟน.",
}


def _hotlines(lat: "float | None", lon: "float | None") -> list:
    """Reuses kb.py's own HOTLINES_NATIONWIDE (+ HOTLINES_BANGKOK_ONLY's 1555, inside
    Bangkok metro) verbatim -- never a second, divergent number list. Imported lazily
    (function-local) to avoid a circular import, same pattern kb.py itself already
    uses for floodconnect_model.

    FIX (live run, 2026-10-06, Sammakorn/Bangkok): a real card for a Bangkok-metro
    point showed only '1669/1784', never the city's own 1555 line, because this
    function used to return HOTLINES_NATIONWIDE unconditionally ("deliberately
    NATIONWIDE ONLY, even inside Bangkok metro") and ignored `lat`/`lon` entirely.
    That contradicted `next_action.who_to_call`'s own geofenced set in the same
    answer and left the card's own first-audience hotlines short one number for a
    Bangkok resident. 1555 is now added, scoped by `_is_bangkok_metro(lat, lon)`
    exactly as `next_action.who_to_call` already does -- never added outside
    Bangkok metro, never dropped once added, and the one extra short-labelled
    number still fits the hard 80-token budget (measured, see
    tests/test_emergency_card.py). 1130 (กฟน./MEA, electrical hazard -- not an
    emergency-dispatch line) stays out of the card's own hotlines; it remains
    available via the fuller `next_action.who_to_call`."""
    import kb as kb_mod
    hotlines = list(kb_mod.HOTLINES_NATIONWIDE)
    if kb_mod._is_bangkok_metro(lat, lon):
        hotlines = hotlines + [h for h in kb_mod.HOTLINES_BANGKOK_ONLY if h["number"] == "1555"]
    return [{"number": h["number"],
             "label_th": _SHORT_HOTLINE_LABEL.get(h["number"], h["label_th"])}
            for h in hotlines]


def _hotlines_compact(lat: "float | None", lon: "float | None") -> list:
    """Same numbers as `_hotlines`, encoded as plain '<number> <label_th>' strings
    (the same compact style kb.py's own `next_action.who_to_call.hotlines` already
    uses) -- used ONLY when the object form pushes the card over `_TOKEN_BUDGET`.
    The object form (`_hotlines`) stays the schema's documented default shape; this
    is a budget-driven degrade, not a second permanent format."""
    return [f"{h['number']}{h['label_th']}" for h in _hotlines(lat, lon)]


def _hotlines_merged(lat: "float | None", lon: "float | None") -> list:
    """Fix: the card's DEFAULT hotlines shape
    now -- every nationwide number joined into ONE list item ('1669/1784'), no
    Thai labels. This is the single biggest remaining lever that still fit inside
    an already-measured, already-tight budget once `now_th`/`do_th` themselves
    were cut to the bone (see `advice/gloss_th.yaml` and this module's headline
    constants): the 2-item labelled form alone costs ~20-33 cl100k tokens, enough
    on its own to blow the hard 80-token cap at the worst colour x verdict
    combination (YELLOW + LEAVE_NOW, where `now_th` is the founder-mandated DDPM
    phrase and cannot be shortened). The numbers themselves are never dropped
    (founder/schema invariant); only the descriptive label is, same as this
    module's existing `_hotlines`/`_hotlines_compact` precedent of shortening the
    label, never the number. The fuller labelled form stays available via
    `next_action.who_to_call` in the full (non-card) answer."""
    nums = [h["number"] for h in _hotlines(lat, lon)]
    return ["/".join(nums)]


# Short colour-only action phrase, used as `do_th`'s last-resort fallback when
# neither a home_shelter verdict nor `advice.prepare_steps` is available at all (a
# bare dict without the full jev_decision envelope -- e.g. a P-B/P-C-only caller
# that never ran P-D's `advice.build`). Deliberately NOT a copy of `now_th`
# (duplicating the same full sentence twice inside one card used to cost ~90 extra
# tokens for zero new information) -- a short, distinct imperative per colour,
# FloodConnect's own wording, OPEN (not yet backed by an official_guidance.yaml
# parity row).
_DO_FALLBACK = {
    "GREEN": "เฝ้าดูสถานการณ์",
    # fix (2026-10-06, Bangkok-metro 1555 added to `hotlines` pushed the
    # YELLOW/no-household worst case 1 token over the hard 80-token budget):
    # shortened from "เตรียมของใช้จำเป็น" -- same meaning, drops "ใช้" -- to make
    # room for the hotline fix rather than drop 1555 or touch `now_th` (the
    # founder-mandated DDPM phrase, never shortened).
    "YELLOW": "เตรียมของจำเป็น",
    "ORANGE": "ย้ายของขึ้นที่สูง",
    # fix (founder ruling 2026-10-06, "official order is a FLOOR, not a
    # ceiling"): RED's own bare fallback (no home_shelter block at all -- a
    # point query with no household declared) used to read "follow the
    # official announcement" ALONE, with no move-now imperative -- exactly
    # what a missing/late official order must never read as. A missing order
    # never lowers this card; it moves the reader now and says plainly that
    # no order has come yet, never that one should be waited for.
    "RED": "ไปที่ปลอดภัยทันที อย่ารอ",
    "UNKNOWN": "ติดตามประกาศทางการ",
}

# fix (do_th headline): the headline when a home-as-shelter verdict was
# actually REACHED (never on UNKNOWN_ASK_INPUTS, which reached no verdict of its
# own -- see below) outranks the colour's own ladder step, same precedence
# `kb.py`'s own `choice.chosen` folding already gives the verdict over the
# colour's choice7 option. LEAVE_NOW gets FloodConnect's own short imperative
# (no ladder row says this -- "leave now" is the verdict's own conclusion, not a
# preparedness step); FOLLOW_OFFICIAL_ORDER reuses the RED ladder's own
# `follow_official_order` row verbatim (never a second, divergent phrase).
# STAY_PREPARED/PREPARE_TO_LEAVE are NOT special-cased here -- both fall through to
# the "first step at the current colour's own rank" branch below, which (now that
# `advice.ladder.steps_for_colour` is current-colour-first) already IS the
# most urgent still-relevant action.
# Fix: shortened from "ออกจากบ้านไปยังจุดปลอดภัย
# ทันที" (29 cl100k tokens) to fit the hard 80-token card cap -- "ไปยังจุดปลอดภัย"
# (to a safe point) is not lost information, it is exactly what the card's own
# hotlines + the full (non-card) answer's route/shelter guidance already carry;
# the headline's own job is the one word that matters most under this budget:
# leave, now.
_LEAVE_NOW_HEADLINE = "ออกจากบ้านทันที"

# This caution is the headline ONLY when the
# COLOUR ITSELF is UNKNOWN (no fresh/usable Z0 reading at all) -- NOT merely because
# `home_shelter.verdict == UNKNOWN_ASK_INPUTS` (household missing/incomplete) at a
# perfectly well-known colour. A RED/ORANGE/etc. answer with no
# household declared (the DEFAULT -- every real caller with no `--household` hits
# this) used to show "ไม่ทราบ ไม่ได้แปลว่าปลอดภัย" as its headline even while the COLOUR was
# known and RED -- measured at 1,042 of 1,042 known-colour answers in a full live
# sweep, e.g. CPY010 (OVERBANK/RED/HIGH) read "unknown" as its
# headline. The founder's own exact wording stays, but now only when it is actually
# true (colour UNKNOWN) -- combined with the ladder's own ask-for-inputs action
# (`household_declaration`, ladder step G2) as a SECOND item appended after it, so
# the card never merely states the caution without naming what closes it. At a
# KNOWN colour with a missing/incomplete household, `_do_th` instead falls through
# to the colour's OWN current-rank ladder step (see below) -- the ask step is still
# reachable there (and in the full `prepare_steps` list), never promoted to the
# headline at a colour the household answer plainly disagrees with.
_UNKNOWN_CAUTION = "ไม่ทราบ ไม่ได้แปลว่าปลอดภัย"

# Fix: PREPARE_TO_LEAVE is a verdict strictly
# more urgent than "just do this colour's own next step" (it means the Dry Gate or
# sustainment check already found a real gap) -- before this fix it fell through to
# the colour's own ladder step, so GREEN/YELLOW PREPARE_TO_LEAVE could read as calm
# as "เฝ้าดู"/"เตรียมของใช้จำเป็น", weaker than the verdict it was supposedly carrying.
_PREPARE_TO_LEAVE_HEADLINE = "เตรียมออกจากบ้าน"

# Official order is a FLOOR, not a ceiling -- founder ruling 2026-10-06: the SAFEST
# action wins; a missing/late/weaker official order never lowers a RED-colour or
# LEAVE-type answer below "move now". This mandated phrase is kept verbatim (never
# shortened, same precedent as `advice/gloss_th.yaml`'s YELLOW DDPM wording). It is
# `do_th` whenever colour is RED or the home-shelter verdict is LEAVE_NOW/
# PREPARE_TO_LEAVE and no official order was actually found -- those two verdicts are
# only EVER reached once `decide_home_shelter`'s rule 1 (official EVACUATE/WARNING)
# has already failed to match, so by construction no order is active there.
_NO_OFFICIAL_ORDER_PHRASE = "ยังไม่มีคำสั่งทางการ — อย่ารอ"

# `now_th` override carrying the actual move-to-safety imperative (short, token-
# budget driven) -- used alongside `_NO_OFFICIAL_ORDER_PHRASE` above (no order: move
# now, no order yet, don't wait) AND alongside `_follow_official_order_headline()`
# (order present: move now, AND follow the order) -- so an actual EVACUATE/WARNING
# never drops FloodConnect's own move-now line, per the same founder ruling.
_MOVE_NOW_NOW_TH = "ไปที่ปลอดภัยทันที"

# Verdicts that only ever fire once `decide_home_shelter` rule 1 (an actual official
# EVACUATE/WARNING) has already failed to match -- i.e. no order is active.
_NO_ORDER_VERDICTS = ("LEAVE_NOW", "PREPARE_TO_LEAVE")


def _prepare_to_leave_headline(advice: dict) -> str:
    """`_PREPARE_TO_LEAVE_HEADLINE` alone. Fix:
    this used to append the first still-open gap-closing step
    (`advice.prepare_steps[0].what_th`) after the headline -- real but, combined
    with the headline itself, routinely 35-50+ cl100k tokens, more than this
    card's entire hard 80-token budget leaves room for once `now_th` and the
    required skeleton fields are also counted. That gap step was never actually
    LOST information: it is `prepare_steps[0]` of the SAME answer regardless (the
    exact "second item, not the headline" precedent `_UNKNOWN_CAUTION`'s own fix
     already established for the ask-for-inputs step) -- a caller who
    wants the concrete next step reads it from there, never only from `do_th`."""
    return _PREPARE_TO_LEAVE_HEADLINE


def _unknown_ask_headline() -> str:
    """`_UNKNOWN_CAUTION` alone. Fix: this used
    to append the household-declaration ask step's own `what_th` after the
    caution -- real, but the combination was consistently the single most
    expensive `do_th` in the whole colour x verdict matrix (the caution text
    alone is already the founder's own fixed wording and cannot be shortened).
    The ask step is not lost: at colour UNKNOWN, `advice.ladder.steps_for_colour`
    already surfaces its own UNKNOWN row FIRST, then every GREEN step including
    `household_declaration` (G2) -- it is a genuine "second item" in
    `prepare_steps`, exactly as an earlier pass originally intended, just not crammed
    into this one field's token budget too."""
    return _UNKNOWN_CAUTION


def _follow_official_order_headline() -> str:
    import advice.ladder as ladder_mod
    step = ladder_mod.step_by_action_key("follow_official_order")
    return (step or {}).get("what_th") or "ทำตามประกาศทางการ"


def _now_th_for(jev: dict, colour: str) -> str:
    """`now_th` (the card's status line), overridden to `_MOVE_NOW_NOW_TH`
    whenever `_do_th` is about to carry either the no-order phrase or the
    official-order headline (see `_do_th`'s own docstring) -- so the move-to-
    safety imperative is never carried by `do_th` alone: with no order, `now_th`
    says move now and `do_th` says no order has come, don't wait; with an actual
    order, `now_th` still says move now and `do_th` says follow the order --
    per the founder's own ruling that an actual EVACUATE/WARNING must raise us
    AND never drop FloodConnect's own move-now line. Every other colour/verdict
    keeps the plain `_now_th(colour)` gloss-table lookup unchanged (including
    YELLOW's founder-mandated DDPM phrase, kept verbatim when no leave-type
    signal is present)."""
    home = (jev.get("advice") or {}).get("home_shelter") or {}
    verdict = home.get("verdict")
    if verdict == "FOLLOW_OFFICIAL_ORDER" or verdict in _NO_ORDER_VERDICTS or colour == "RED":
        return _MOVE_NOW_NOW_TH
    return _now_th(colour)


def _do_th(jev: dict) -> str:
    """The card's headline -- the MOST URGENT action for the CURRENT state (this
    field used to be `prepare_steps[0].what_th` from a cumulative list
    that started at GREEN, so it was always the weakest GREEN-rank step
    regardless of the real colour/verdict -- a RED/LEAVE_NOW answer could read
    "เฝ้าดู" (watch), which this fix makes structurally impossible, see
    `tests/test_emergency_card.py`'s per-colour-x-verdict rank checks).

    Priority (home_shelter verdict outranks the colour's own ladder step, same
    precedence `kb.py`'s `choice.chosen` folding already uses). Fix
    (founder ruling 2026-10-06, "official order is a FLOOR, not a ceiling" --
    the SAFEST action wins; a missing/late/weaker official order never lowers a
    RED-colour or LEAVE-type answer): colour RED and the two no-order-by-
    construction verdicts (LEAVE_NOW, PREPARE_TO_LEAVE -- `decide_home_shelter`
    only ever reaches either AFTER its own rule 1 official-order check has
    already failed to match) now ALWAYS get `_NO_OFFICIAL_ORDER_PHRASE` as
    `do_th`, paired with `_MOVE_NOW_NOW_TH` as `now_th` (see `build_card`) --
    never the bare "follow the official announcement" wording alone, which is
    exactly the FAIL this fix closes (measured: 731 RED/LEAVE Bangkok answers
    with no order gave no move-now wording at all, and the mandated phrase
    appeared in 0 of them).
    1. verdict == FOLLOW_OFFICIAL_ORDER -> the RED ladder's own
       `follow_official_order` row, verbatim -- `now_th` still carries
       `_MOVE_NOW_NOW_TH` (see `build_card`), so an ACTUAL order never drops
       FloodConnect's own move-now line, per the same ruling's second half.
    2. verdict in (LEAVE_NOW, PREPARE_TO_LEAVE), or colour == RED (including no
       verdict at all / UNKNOWN_ASK_INPUTS -- the common no-`--household` case)
       -> `_NO_OFFICIAL_ORDER_PHRASE`.
    3. colour == UNKNOWN (no fresh/usable Z0 reading at all) -> the founder's own
       caution + the ask-for-inputs step. Fix:
       this is keyed on the COLOUR, never on `verdict == UNKNOWN_ASK_INPUTS` alone
       -- a KNOWN colour with a missing/incomplete household declaration is NOT
       "unknown", and must never show this caution as its headline (measured bug:
       it did, at every known colour, including RED).
    4. otherwise (STAY_PREPARED, UNKNOWN_ASK_INPUTS at a KNOWN non-RED colour, or
       no home_shelter info at all -- a bare P-B/P-C-only caller) ->
       `advice.prepare_steps[0].what_th`, which (since
       `advice.ladder.steps_for_colour` is current-colour-first) IS the most
       urgent action still open at THIS colour's own rank -- never weaker than
       the colour calls for, and the ask-for-inputs step is still reachable
       inside the full `prepare_steps` list, never promoted to the headline here.

    Falls back to `choice.chosen`/`_DO_FALLBACK[colour]` only when `advice` is
    wholly absent (a bare dict without the full jev_decision envelope) AND the
    colour is not RED (RED's own no-order branch above already covers that bare
    case). Never a blank do_th, never a fabricated step this repo hasn't
    actually built."""
    advice = jev.get("advice") or {}
    home = advice.get("home_shelter") or {}
    verdict = home.get("verdict")
    colour = jev.get("colour", "UNKNOWN")

    if verdict == "FOLLOW_OFFICIAL_ORDER":
        return _follow_official_order_headline()
    if verdict in _NO_ORDER_VERDICTS or colour == "RED":
        return _NO_OFFICIAL_ORDER_PHRASE
    if colour == "UNKNOWN":
        return _unknown_ask_headline()

    steps = advice.get("prepare_steps") or []
    if steps:
        return steps[0].get("what_th") or _chosen_fallback(jev, colour)
    return _chosen_fallback(jev, colour)


def _chosen_fallback(jev: dict, colour: str) -> str:
    chosen = (jev.get("choice") or {}).get("chosen")
    return chosen or _DO_FALLBACK.get(colour, _DO_FALLBACK["UNKNOWN"])


def _strip(layers: dict) -> str:
    """'Z0:Y Z1:R Z2:R Z3:U' -- first letter of each layer's colour5 (U for UNKNOWN,
    which is distinct from every other first letter so it is never mistaken for
    GREEN -- note GREEN and no other colour5 value also starts with G, so this never
    collides)."""
    if not layers:
        return ""
    order = ["Z0", "Z1", "Z2", "Z3"]
    parts = []
    for z in order:
        colour = layers.get(z)
        if colour:
            parts.append(f"{z}:{colour[0]}")
    return " ".join(parts)


def _data_time(jev: dict) -> "str | None":
    z0 = jev.get("z0") or {}
    return z0.get("observed_at_utc")


def _estimate_tokens_without_tiktoken(text: str) -> int:
    """Portability: this repo is self-install, `pyproject.toml` only puts
    `tiktoken` in the `dev` extra -- a real self-install (`pip install -e .`, no
    extras) never gets it, so this path is this repo's actual PRODUCTION token count
    for most installs, not a rare defensive fallback. The OLD fallback (`len(text)`,
    one unit per character) measured 1.5-1.6x the real cl100k_base count on this
    card's own mixed Thai+JSON text (a 273-char/168-real-token sample measured 273,
    62% high) -- high enough that a real, correctly-sized card could raise
    `CardOverBudget` on a machine that simply never installed the `dev` extra, a
    false positive this function must not produce.

    Thai-aware weighted estimate (INSTINCT -- coefficients fitted against real
    `tiktoken.encode` output on this module's own sample cards, 2026-10-06, not
    derived from a tokenizer spec): non-ASCII characters (Thai text) are weighted
    1.05 tokens/char (MEASURED cl100k ratio for Thai prose is ~0.8-1.0), ASCII
    characters (JSON punctuation + English field names) at 0.45 tokens/char
    (MEASURED ~0.3-0.35 for short JSON keys/values) plus a flat +3 token buffer.
    Every sample measured against real tiktoken output came out ABOVE the real
    count by 5-18 tokens (conservative, never an undercount in that sample) while
    staying far closer than the old character-count proxy -- a caller must not cite
    these exact coefficients as settled without a wider measured sample."""
    non_ascii = sum(1 for c in text if ord(c) > 127)
    ascii_chars = len(text) - non_ascii
    return int(non_ascii * 1.05 + ascii_chars * 0.45) + 3


def _count_tokens(card: dict) -> "tuple[int, bool]":
    """Returns `(count, exact)`. `exact=True` only when the real `tiktoken`
    cl100k_base count was used; `exact=False` means the Thai-aware estimate
    above was used instead -- `build_card` reads this flag to decide whether an
    over-budget reading is trusted enough to hard-raise on (see its own note)."""
    import json
    text = json.dumps(card, ensure_ascii=False)
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), True
    except Exception:
        # No `tiktoken` installed (the common case for a self-install without the
        # `dev` extra -- see `_estimate_tokens_without_tiktoken`'s own note) or its
        # encoding data could not be loaded (e.g. no network on first use, cache
        # missing). Never the old raw `len(text)` character-count proxy -- that
        # overcounted Thai-heavy cards badly enough to raise `CardOverBudget` on a
        # card that was never actually over budget.
        return _estimate_tokens_without_tiktoken(text), False


_TOKEN_BUDGET = 80
# Portability: absolute last-resort ceiling for the no-`tiktoken`
# estimate alone (`build_card`'s own note) -- generous enough that normal
# estimator slack (measured single-digit-to-low-double-digit tokens on this
# module's own samples) never trips it, but still catches a genuinely broken/
# runaway-length card content bug rather than silently shipping one. INSTINCT:
# a round multiple of the real budget, not a measured bound.
_NO_TIKTOKEN_HARD_CEILING = _TOKEN_BUDGET * 3


class CardOverBudget(RuntimeError):
    """Fix: raised if `build_card` ever produces
    a card over `_TOKEN_BUDGET` cl100k tokens after every degrade step -- a HARD,
    fail-closed assert (the founder's own 2026-10-05 ruling: "ตัดให้เหลือไม่เกิน 80"
    is not advisory). `tests/test_emergency_card.py` asserts this never fires
    across the full colour x verdict x hotline-region matrix, including on real
    live-built answers -- this exception is the production-side mirror of that
    same hard rule, so a future change that quietly reintroduces an over-budget
    combination fails LOUD in the running system too, not only in CI."""


def build_card(jev: dict, lat: "float | None" = None, lon: "float | None" = None) -> dict:
    """Build the emergency_card for one jev_decision. `jev` is the dict `kb.py`'s
    `_answer_sandwich` returns (or the same shape once renamed into `jev_decision` --
    only `colour`/`layers`/`z0`/`advice` are read here). `lat`/`lon` decide whether
    the Bangkok-only hotlines are added (same geofence kb.py already uses for the
    rest of the answer) -- currently a no-op for the card itself (`_hotlines*` are
    deliberately nationwide-only), kept for schema/future-proofing symmetry.

    Budget discipline (a HARD cap, not a best
    effort): the six REQUIRED fields (`colour`/`now_th`/`do_th`/`hotlines`/
    `not_official`, `label_th` no longer emitted by default -- see below) are built
    already-minimal (`gloss_th.yaml`'s shortened non-YELLOW `now_th` rows, this
    module's shortened override headlines, `_hotlines_merged`'s number-only
    hotlines) so that even the single worst real combination (YELLOW's founder-
    mandated DDPM `now_th` plus a LEAVE_NOW `do_th`) still fits. `label_th`
    duplicates `colour` and is no longer included at all (an earlier pass's own
    suggested first cut); `strip`/`data_time` are added back OPPORTUNISTICALLY,
    each only if it still fits, in that order -- never required, and dropped again
    (never shrinking `now_th`/`do_th`/`hotlines`/`not_official` instead) the moment
    either would push the card over budget. `CardOverBudget` is raised, never
    silently returned, if the minimal required-fields-only card is somehow still
    over `_TOKEN_BUDGET` -- this must never actually happen; see this module's own
    test suite for the full measured matrix.

    Portability: that hard raise is trusted only when `_count_tokens`
    used the real `tiktoken` count (`exact=True`). Without `tiktoken` (a real
    self-install missing the `dev` extra -- `_estimate_tokens_without_tiktoken`'s
    own note), the estimate carries real, measured slack (a few tokens either
    way, not the old character-count proxy's 60%+ overcount, but still not exact
    enough to trust at this budget's own tight real margins, measured as little
    as 4 real tokens on some colours). So a self-install without `tiktoken`
    never raises `CardOverBudget` off the estimate alone for the REQUIRED-fields
    floor -- it still TRIMS the opportunistic `strip`/`data_time` additions below
    using the same estimate (dropping an addition the real count would have kept
    is a safe, non-breaking direction), and only raises as an absolute last
    resort if the estimate is wildly over budget (`_NO_TIKTOKEN_HARD_CEILING`),
    which would mean a real content bug, not estimator slack."""
    colour = jev.get("colour") or "UNKNOWN"
    card = {
        "colour": colour,
        "now_th": _now_th_for(jev, colour),
        "do_th": _do_th(jev),
        "hotlines": _hotlines_merged(lat, lon),
        "not_official": True,
    }
    base_tokens, exact = _count_tokens(card)
    if base_tokens > _TOKEN_BUDGET and (exact or base_tokens > _NO_TIKTOKEN_HARD_CEILING):
        raise CardOverBudget(
            f"emergency_card is {base_tokens} cl100k tokens (budget {_TOKEN_BUDGET}) "
            f"with every optional field already dropped: {card!r}")

    strip = _strip(jev.get("layers") or {})
    if strip:
        candidate = dict(card, strip=strip)
        if _count_tokens(candidate)[0] <= _TOKEN_BUDGET:
            card = candidate

    data_time = _data_time(jev)
    if data_time:
        candidate = dict(card, data_time=data_time)
        if _count_tokens(candidate)[0] <= _TOKEN_BUDGET:
            card = candidate
        else:
            # shorten to date-only (first 10 chars of an ISO-8601 timestamp)
            candidate = dict(card, data_time=str(data_time)[:10])
            if _count_tokens(candidate)[0] <= _TOKEN_BUDGET:
                card = candidate

    # fix (founder ruling 2026-10-06, scope tagging, MED): a single-letter
    # scope marker ("V" VALIDATED_MVP / "E" EXPERIMENTAL -- `jev.scope`'s own
    # closed 2-value vocabulary, `kb._SCOPE_VALIDATED_MVP`/`_SCOPE_EXPERIMENTAL`)
    # so the card itself never implies full MVP coverage outside Bangkok/
    # Sammakorn. OPPORTUNISTIC, same precedent as `strip`/`data_time` above --
    # never required, dropped first (it is the least safety-critical of the
    # three) the moment it would push the card over budget; the full `scope`
    # string is always available in `jev_decision.scope` regardless.
    scope = jev.get("scope")
    if scope:
        candidate = dict(card, scope="V" if scope == "VALIDATED_MVP" else "E")
        if _count_tokens(candidate)[0] <= _TOKEN_BUDGET:
            card = candidate
    return card
