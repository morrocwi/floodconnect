# Changelog

All notable changes to FloodConnect. Dates are Asia/Bangkok local. This file states
only what actually shipped and is tested in this repository — never a plan (see
`ROADMAP.md` for plans).

## v0.1.6 — 2026-10-07

**Packaging only — no flood-logic change.** Makes this repo installable as a
plugin for Codex, Claude Code and Gemini CLI, plus the existing generic
install (§4/§4a of `README.md`).

- **Skill consolidation:** the two skill files that used to live at `skill/`
  (the v0.1.5 vendor-neutral Sandwich method) and `skills/floodconnect/` (the
  MCP/CLI usage skill) are now both under one canonical tree:
  `skills/floodconnect/` (usage) and `skills/floodconnect-method/` (the
  Sandwich method, moved from `skill/` via `git mv`, keeping history). Each
  `SKILL.md`'s frontmatter `name`/`description` no longer overlaps, and each
  cross-links to the sibling. `skill/` no longer exists — every reference to
  it (`README.md`, `docs/API_MANUAL.md`) was updated; dated/historical files
  (`RELEASE_NOTES_v0.1.5.md`, `docs/handoff/NEXT_AI_HANDOFF.md`,
  `.ai/claims/20261007-ai-worker-floodconnect-v015-release.yaml`) were left
  as-is — they are accurate records of what v0.1.5 shipped, under the path it
  had then.
- **Plugin manifests, all pointing at the same `skills/` tree and the same MCP
  server (`tools/mcp/floodconnect_mcp.py`, requiring `pip install -e '.[mcp]'`):**
  - Codex: `.codex-plugin/plugin.json` + `.agents/plugins/marketplace.json`.
    MEASURED (codex-cli 0.155.1): the official docs' claim that a root-level
    `plugin.json` also works did not hold on this live CLI -- only
    `.codex-plugin/plugin.json` installed. Codex never reads a plugin-local
    `.codex-plugin/mcp.json` (removed, was dead weight); its real MCP source
    is the shared root `.mcp.json`, confirmed by `codex mcp list`/`codex mcp get`.
  - Claude Code: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`
    + `.mcp.json`. MEASURED (claude 2.1.291): `plugin.json`'s `author` field
    must be an object (`{"name": ...}`), not a string — `claude plugin validate`
    caught this before any install attempt. `.mcp.json`'s `command`/`args` use
    `${CLAUDE_PLUGIN_ROOT}` (the documented stdio-server variable) rather than
    a bare relative path — MEASURED: without it, `claude mcp list` fails with
    `ENOENT` from any working directory other than this clone; with it, the
    server connects from any directory.
  - Gemini CLI: `gemini-extension.json` (with `mcpServers` using the
    documented `${extensionPath}` placeholder) + `GEMINI.md`, a thin pointer
    to the two skills under `skills/` (no copied content). Gemini CLI has no
    marketplace concept; install is always `gemini extensions install
    <path|git-url>` directly.
  - `author: morrocwi`, `license: MIT` (matches `LICENSE`), `version: 0.1.6`,
    `homepage: https://github.com/morrocwi/floodconnect` on every manifest
    that has those fields. No field was invented for an ecosystem whose own
    docs don't define it (e.g. Gemini's manifest carries no author/license/
    homepage — not part of its documented schema).
- **Isolated install tests (MEASURED), each with `HOME`/`CODEX_HOME`/
  `CLAUDE_CONFIG_DIR`/Gemini config dir pointed at a throwaway scratch dir,
  never the founder's own global config:** all three CLIs installed this
  plugin from the local repo path and confirmed it. `claude plugin details`
  and `gemini extensions list`/`gemini skills list --all` both printed the 2
  skills and the 1 MCP server by name, non-interactively. Codex confirmed the
  plugin name+version install via `codex plugin list`, and `codex mcp list`/
  `codex mcp get floodconnect` list the bundled MCP server by name (both read
  the shared root `.mcp.json`, not a Codex-specific manifest — there is no
  `codex skill(s)` command at all to confirm skills the same way); `codex
  doctor` does not surface it. Whether the server actually launches
  correctly through Codex's plugin-cache copy needs an interactive/model
  session, which this test does not start (no credentials used anywhere in
  this release) — left OPEN, not claimed either way.
- **New test:** `tests/test_plugin_manifests.py` — every manifest is valid
  JSON, every path it references (directly, or via `${extensionPath}`)
  exists, the old `skill/` directory is gone, and the version string agrees
  across all 4 canonical places plus every plugin manifest.
- **Version bumped to 0.1.6** in the same 4 places v0.1.5 used: `pyproject.toml`,
  `system_capabilities.json`, `skills/floodconnect-method/SKILL.md`'s
  frontmatter, and `tools/mcp/floodconnect_mcp.py`'s `serverInfo`.
- **System Coverage Contract (SCC) — documentation only, no code change.**
  New §4b in `skills/floodconnect-method/SKILL.md` (a `Sibling:` pointer line
  in `skills/floodconnect/SKILL.md` plus rule 8 in `AI.md`'s "Mandatory
  reasoning rules"): when an assessment escalates to the area level, walk
  every dimension (pond, pumps, outlet, rain, road flooding, forecast,
  upstream pressure) via declared KG edges; one dimension's source failure
  marks only that dimension `OPEN`, never the whole assessment; attempt every
  dimension before giving an overall colour, and give one only when the local
  storage/pond (Z0) and the outlet/receiving canal it drains to have both
  come back `FOUND` (the minimum load-bearing pair) — if either is `OPEN`,
  report per-dimension `FOUND`/`OPEN` only, no overall colour; missing
  evidence lowers confidence, never the hazard; state current vs. forward
  hazard as two separate lines.
  `INSTALL_CHECK.md` gained Q13-Q15 covering this. **The code-level coverage
  block/gate (an actual pass/fail check wired into the answer path) is not in
  this release — targeted for v0.2.**

## v0.1.5 — 2026-10-07

**Targeted fixes (2026-10-07).** Fixes several specific gaps against the entry
immediately below ("M8 KG-only revision"), whose own listed changes had
not actually reached the real answer path for every case they described.

- The official-order-floor change really did reach the main path for every case now:
  the earlier fix was reachable only on a bare dict without a
  real `advice` block, which `build_answer` always attaches -- a RED colour, or a
  LEAVE_NOW/PREPARE_TO_LEAVE verdict, now gets the move-now line on the real path too.
- The rise-ETA lag arithmetic was computing a point's deviation from its own lag
  target (near zero by construction) instead of its real elapsed time, and the
  shorter-window point could sit after the current reading -- both are now the real
  elapsed hours, and a short `range_h` summary is reachable without `--verbose`.
  This is PROP-FLOOD-02 (linear, two windows), not PROP-FLOOD-11 -- see the
  ETA relabelling note below. (Replaces this file's own earlier wiring note
  below, which only covered the GATED/compact-answer wiring, not the
  arithmetic itself, and mislabelled it PROP-FLOOD-11.)
  - **KG gaps are now logged and returned by default** at the real entrypoints
  (the CLI, the MCP tool) -- the earlier gap-naming logic existed but
  neither entrypoint ever turned it on, and the names were never returned to the
  caller at all. `scope` now resolves the point's actual province (the KG's own
  nearest-asset membership) instead of a deliberately wide metro rectangle, which
  tagged several real stations in neighbouring provinces as `VALIDATED_MVP`; it
  also no longer treats every `bma_watermap` gauge nationwide as validated just
  because of its source prefix -- only Bangkok province or the declared
  Sammakorn-area station ids qualify now. One real station inside the old
  metro rectangle (BKK007, Bang Yai, Nonthaburi) still resolves VALIDATED_MVP
  because of a separate KG-data-coverage gap (too few Nonthaburi
  IN_PROVINCE-declared member points near it for the nearest-member-distance
  ranking to prefer Nonthaburi over Bangkok) -- see "Known issues" below.
- `SIMULATION_ENABLED` is now actually read at its one real call site (the
  PROP-FLOOD-06 engine's L5-tier promotion under RED, which folds in an external
  rain forecast) -- the flag existed but nothing checked it.
- The official-guidance parity inventory below this entry is now complete: the two
  "Known remainder: parity inventory not complete" notes further down describe an
  earlier state that no longer holds -- `advice/PARITY.md` is 0 WEAKER, 0 MISSING
  across both source classes, regenerated from the current `official_guidance.yaml`/
  `preparedness_ladder.yaml`. `advice/official_guidance_inventory.yaml`'s own
  per-page coverage checklist now also lists all 5 of these rows (OG-42..44,
  GEN-41/42).
- Two mutation-protecting tests closed a real gap: reverting the ring-row colour fix
  or the ring freshness/empty-ring UNKNOWN floor fix both still passed the full suite
  beforehand.
- The RISING Z0 line now carries a short ETA range directly (both in `kb.py`'s
  own `l0_check`-triggered line and in `l0_check.py`'s own QUIET/ESCALATE line),
  and the UNKNOWN-trend ETA reason is now distinct from the "not RISING" one
  (STABLE/FALLING have a resolved trend; UNKNOWN has no series to compare
  against at all).
- A real short-lag regression is now covered by a test replaying a live WL.KJK.02
  page whose own series had already advanced one step past the externally-read
  "now" -- reverting the short-lag point lookup back to a fixed array index now
  fails a test (the earlier fixture used for this happened to have its series end
  exactly at "now", which could not tell the two apart).
- Internal development-process labels and phrasing were removed from comments,
  docs and tests across this branch's own changed files, keeping each line's
  technical meaning.

Known issues (v0.1.5): BKK007's scope overclaim above is not fixed (a KG-data-
coverage gap, not a code bug -- see the scope bullet above and this file's own
xfail test, `tests/test_kb_answer_sandwich.py::test_bkk007_in_nonthaburi_is_
experimental_not_validated`); the GREEN-colour-with-a-single-storey-house/
stale-declaration LEAVE_NOW over-escalation (tracked below, in `_assemble`'s own
rules 4-9 note, as a FloodConnect default pending the founder, not changed here);
PREPARE_TO_LEAVE's own move-now/no-official-order line now also shows on a GREEN
card when the household's own need profile triggers it, which can read as more
urgent than the card's own colour -- not yet reconciled.

**JSON-serialiser minification shipped and measured; the L0
daily-check/trigger-table/watchlist engine still not attempted
(2026-10-06).**

`TRIGGERS.md` and `WATCHLIST.md` now carry founder-approval header lines
(`APPROVED by founder 2026-10-06`), lifting the blocker the entry
below recorded. That approval was confirmed by reading both files' headers
directly, not assumed from the task text alone.

What was actually shipped and tested:

- `kb.py answer --json` was pretty-printed (`indent=2`) even on the `--json`
  path, unlike `kb.py locate --json` right below it in the same file, which
  already minified. Fixed to the same `separators=(",", ":")`, no-indent form.
  Real measurement on this worktree's own offline Sammakorn fixture, same
  payload, `tiktoken` `cl100k_base` (the encoding `tests/test_token_budget.py`
  already uses): 2284 tokens (old, indent=2) -> 1653 tokens (new, minified),
  -631 tokens / -27.6% on this one query. Not a projection -- both numbers
  came from actually running `kb.cmd_answer` against the real fixture DB.
- The MCP stdio fallback transport (`tools/mcp/floodconnect_mcp.py`, the
  branch used only when the real `mcp` SDK is not importable) serialised its
  `tools/call` results and its stdout JSON-RPC lines with plain `json.dumps`
  (whitespace-padded, `\uXXXX`-escaped Thai). Switched to the same
  `ensure_ascii=False, separators=(",", ":")` convention. Covered by a new
  test (`test_stdlib_fallback_serialiser_is_minified_and_keeps_thai_literal`)
  that forces the fallback branch via a blocked import (this repo's own venv
  has the real SDK installed, so the branch does not run on its own) --
  without that forcing, this fix would have shipped untested in this
  environment, same gap the existing
  `test_floodconnect_locate_tools_call_round_trip_via_fallback` already
  documents for that branch.
- Full offline test suite re-run after both fixes: 2004 passed (was already
  2004 before these two edits; 8 pre-existing errors in `test_kg_build.py`/
  `test_wikipedia_canals.py` reproduce identically on the unmodified `HEAD`
  and are a session-write-guard gap unrelated to this change, not a
  regression introduced here).

**SUPERSEDED by later work in this same release (see the L0 check/watchlist/MCP
tools bullets at the top of this `v0.1.5` section):** the paragraph below
recorded, as of 2026-10-06, that the L0 check and the watchlist were not yet
built. `kb.py check`/`l0_check.py` (the L0 command), the MCP `floodconnect_check`
tool, and the `watchlist.py` cross-session state machine (ACTIVE/COOLING/CLOSED,
exposed as MCP `floodconnect_watch`) were all built and shipped before this
release closed -- kept below as the historical record of that point in time, not
a current status claim. The switchable L0/L1/L2 router with timing measurements,
the `fastlayer.py` report-reading layer (superseded by SKILL.md §0b's FAST
LAYER, documentation-only, no new code file), and the SKILL.md ≤150-token
daily-check header remain not attempted.

Not attempted, for real scope/time reasons, not a documents-still-
draft reason (that reason no longer applies -- both files are approved), AS OF
THIS 2026-10-06 ENTRY (see the SUPERSEDED note just above): the
new `kb.py check` L0 command and its 3-call budget, the MCP
`floodconnect_check` tool, the switchable L0/L1/L2 router and its timing
measurements, the full `TRIGGERS.md`/`WATCHLIST.md` state machine (trigger
evaluation, depth ladder, alert-event + `.ics` emission, append-only
`watch_log`/`watch_closed`), the new `fastlayer.py` report-reading layer, the
`docs/INDICATORS.md` information-hierarchy table, and the SKILL.md ≤150-token
daily-check header. None of their numbers were fabricated to stand in for
work not done.

---

**L0 daily-check / token-ladder work: not started as of 2026-10-06, scope recorded
plainly instead of a rushed partial build. SUPERSEDED later in this same
release** -- the L0 check and the watchlist state machine described as
not-yet-approved below were subsequently approved and built (`l0_check.py`,
`watchlist.py`, MCP `floodconnect_check`/`floodconnect_watch`; see the bullets
at the top of this `v0.1.5` section). This entry is kept as the historical
record of the 2026-10-06 point in time, not a current status claim.

The requested next step is a cheapest-first L0/H0..H3 daily check (a new `kb.py
check` command), its token ladder, a cross-session watchlist with a persistent
state machine, and an alert-event/calendar hand-off. A detailed trigger table and
a cross-session watchlist design were drafted for this and handed over as the
source of truth to implement exactly. Both documents say plainly, in their own
first lines, that they are still draft/proposal, not yet approved for the
codebase, and the trigger table says explicitly not to touch this repository or
worktree with their content yet. Writing that content into this repository's code
now would contradict the documents' own stated status, so none of it was
implemented here -- recorded rather than worked around.

Both documents were read in full, including their 2026-10-06 additions. Two
things already true in this repository line up with their content and needed no
new work: the TMD CAP feed's TLS chain is reachable over plain HTTPS from this
environment but fails certificate verification without the documented
intermediate certificate (consistent with the documents' own note that the
chain needed a GlobalSign intermediate fixed in); the keyless rain (thaiwater
24h) and 7-day forecast (Open-Meteo) sources the documents call for are already
declared in `sources/*.yaml` and were not duplicated.

Also not attempted, for the same reason -- each depends on the same
not-yet-approved trigger/watchlist design, or on a KG edge the documents
themselves mark pending founder acceptance (the proposed Sammakorn rain-gauge
edge) -- the new `fastlayer.py` report-reading layer, the `kb.py --json`
minified-output and MCP stdio serializer fix, `test_token_budget`'s real-
serializer measurement, a switchable L0/L1/L2 router with timing measurements,
the information-hierarchy table in `docs/INDICATORS.md`, and the before/after
token measurement for a Sammakorn query. None of these were coded, and none of
their claimed numbers were fabricated to fill this entry.

The safety-floor and KG-only rulings this task also named (official guidance as
a floor rather than a ceiling; station-to-station relations drawn only from
declared KG edges; no simulated or modelled load in an answer) are already the
subject of the "M8 KG-only revision" and "M8 subtractive-fix revision" entries
immediately below, from earlier -- re-checked against this entry's own
description and found unchanged, not re-implemented.

**M8 KG-only revision (2026-10-06, founder ruling "ปิดการเดา ... ให้อยู่แค่ใน
kg graph เท่านั้น โดยปิดการจำลองโหลดไปเลย").** Supersedes the subtractive-fix
revision just below for station-to-station relations: instead of refining the
canal-name/code-family/reach-snap joins so they are only colour-ineligible,
this revision removes them from the ring itself.

- `tools/kg/rings.py` now filters every Z1/Z2/Z3 row down to `basis=="declared"`
  (the `site/inputs/canals/east_chain.yaml` edges and the declared canalchain
  OUTLET_TO target) plus plain `SAME_SUBBASIN` membership, under a
  `KG_ONLY_MODE` flag that defaults on. The verbatim canal-name join, the
  code-family join, and the reach-snap walk (`SAME_REACH`/`UPSTREAM_CHAIN`/
  `UPSTREAM_REACH`/`DOWNSTREAM_CHAIN`/`UPSTREAM_PATH`, and the outlet's own
  name-pattern-guess fallback) no longer reach the ring at all -- a station
  reachable only through one of them simply does not appear; the ring reads
  UNKNOWN instead.
- Ring-member rows are coloured with the same bank/critical ladder Z0 itself
  uses, instead of the bare agency status word.
- The Chao Phraya main-stem outlet relabel matches Sammakorn's own declared
  station ids instead of a 5 km radius, and drops CPY014 (it sits upstream of
  the junction this repo places Sammakorn's drainage at).
- `floodconnect_model.ring_readout` no longer forces a ring's worst colour to
  start at UNKNOWN (so an all-fresh-GREEN ring can actually report GREEN) and
  no longer lets a stale reading's old colour set the worst colour.
- An absent `member_need_profile`, a stale `declared_now`, and an explicit
  "no dry upper floor" (or single-storey household) can no longer be
  silently overridden into STAY_PREPARED.
- A missing, late, or weaker official order no longer reads as "wait for
  one" at RED -- the two places that used to default to "follow the official
  announcement" alone now say to move to safety now instead.
- Every answer carries a `scope` (`VALIDATED_MVP` for Bangkok/Sammakorn,
  `EXPERIMENTAL` elsewhere), and a ring with no declared KG edge is logged by
  name when the policy gap log is written.
- A single flag (`SIMULATION_ENABLED`, off) documents that no simulated or
  modelled load feeds an answer -- only measured readings, declared KG
  edges, and arithmetic on measured slopes.

Known remainder, not done in this revision: the official-guidance parity
inventory is not yet a complete per-page item list for every cited source
page (closed by a later entry above), and the cross-repo wording cleanup
(internal development-process phrasing in older comments) is only partially
done (also narrowed by a later entry above).

**Missing-input confidence (2026-10-06, founder ruling "ถ้าไม่ใส่
กลุ่มเปราะบาง ผลการคำนวณผ่าน jev decision ต้องต่ำลง และบอกเหตุผล ... เช่น คนและสัตว์").**
A missing household or station input never silently passes as "nothing to
report" -- it is named and lowers confidence, instead of either blocking the
answer outright or being absorbed into a verdict with no trace of the gap.

- The home-as-shelter verdict (`advice/home_shelter.py`) now lowers
  `confidence` one ordinal step (HIGH -> MEDIUM -> LOW -> NONE) per missing
  vulnerable-population category -- a wholly absent `member_need_profile`
  AND a wholly absent `animal_profile` each count separately ("คนและสัตว์"),
  while an explicit declaration of either (including `{}` or a declared
  animal count of 0 -- "checked, none") is real information and never lowers
  confidence. Every lowering is named in a `calc` block (eq/inputs/missing/
  reasons) with the plain-Thai reason, never a bare confidence number alone.
  This still never reaches STAY_PREPARED on a missing category -- any branch
  that would otherwise STAY is downgraded to PREPARE_TO_LEAVE instead.
- `jev_decision` itself now carries a sibling `calc` block (`colour`/`trend`/
  `eta`, verbose-only) naming which inputs the colour/headroom and trend
  sections actually had, with the plain-Thai reason when one is missing
  (no Z0 reading, no upstream read, no middle read, no trend series). `eta`
  is, AS OF THIS 2026-10-06 ENTRY, a passthrough of the module's own GATED
  status -- always `result: GATED`, never a computed time value. **SUPERSEDED
  later the same day** by the mandatory-ETA-when-RISING fix at the top of this
  section: `eta` now carries a real PROP-FLOOD-02 (linear, two windows)
  computed range whenever Z0 is RISING, mislabelled PROP-FLOOD-11 at the time
  this entry was written. This is transparency
  on top of `floodconnect_model.sandwich_decision`'s own existing confidence
  computation, not a second, competing confidence rule -- whether colour/
  trend should ALSO step confidence down further for a gap that computation
  does not already account for is PENDING THE FOUNDER, not attempted here.
- Portability fix: `advice/card.py`'s token-budget check no longer raises
  `CardOverBudget` off its no-`tiktoken` fallback alone (a real self-install
  without the `dev` extra never has `tiktoken` at all, so this was the
  actual production path for most installs, not a rare defensive branch).
  The fallback is now a Thai-aware weighted estimate (far closer to the real
  cl100k count than the old raw character-count proxy, which overcounted a
  Thai-heavy card by 60%+) and the hard-fail invariant is trusted
  only when the real tiktoken count was used; without it, the card is still
  built (optional fields still trimmed against the estimate) and only a
  wildly-over-budget estimate raises, as a last-resort guard against a real
  content bug rather than estimator slack.

Known remainder, not done in this revision: the official-guidance parity
inventory (same gap as the revision above) is still not rebuilt, and whether
to lower `jev_decision.confidence` itself for the new `calc.colour`/
`calc.trend` gaps (beyond what `sandwich_decision` already computes) is
pending the founder.

**M8 subtractive-fix revision (2026-10-06, founder ruling "แก้แบบตัดออก").** Removes
unsourced inference from anything that sets a layer or card colour, rather than
adding new inference to compensate for it.

- A same-canal claim via the bare agency code-prefix family (`SAME_CODE_FAMILY`)
  is now accepted only when EVERY member of that family has a non-null agency
  river name and all of them are equal; the family cache is scoped per agency
  source so two different agencies' codes never collide on the same bare letters
  (e.g. BMA's `WL.BBU.01` vs plain thaiwater's `BBU01`/`BBU02`, 453+ km away). A
  `SAME_REACH` pair whose own agency river names disagree is demoted to
  `SAME_REACH_RIVER_MISMATCH`. None of these heuristic relations, nor a bare
  `SAME_SUBBASIN` membership, may set a Z1/Z2/Z3 layer colour or the card colour
  any more (`floodconnect_model.is_colour_eligible`) — they still appear in
  `facts`/the raw station list with their true relation label.
- The `OUTLET_MAIN_STEM` relabel (founder ruling "เจ้าพระยาคือทางออก") now applies
  only inside a declared per-area list (today: หมู่บ้านสัมมากร), restricted to that
  area's own declared downstream main-stem stations, and never when the point
  itself is on the Chao Phraya main stem or another declared outlet river — it no
  longer applies to every Z0 anywhere in `sub_basin:1002` (~300+ stations
  nationwide), which had produced false outlets upstream of Bangkok.
- `collect._thaiwater_status_word` no longer reports "OVERBANK" from
  `diff_wl_bank_text` when the feed computed it against a `min_bank` that is 0,
  null, or at/below `ground_level` — that text is itself `h - min_bank`, not a
  real agency observation, and now falls through to the real `situation_level`
  word or `NO_THRESHOLD`. `floodconnect_model.bank_check` applies the same
  usable-threshold requirement to the "OVERBANK"/"ล้นตลิ่ง"/"เท่าระดับตลิ่ง" word
  family specifically; every other independently-reported agency status word is
  still trusted unconditionally.
- `advice/home_shelter.decide_home_shelter`: colour `UNKNOWN` never gives
  `STAY_PREPARED` any more, even with every household input known — it returns
  `UNKNOWN_ASK_INPUTS` naming `flood_state` when there is no other known gap, or
  `PREPARE_TO_LEAVE` (confidence LOW) when a household gap is already known.
  `advice/card._do_th` now checks `verdict == PREPARE_TO_LEAVE` before
  `colour == UNKNOWN`, so the headline never understates a verdict the ladder
  already escalated to.
- `kb._answer_sandwich`'s `NO_Z0_READING` path no longer returns early before any
  ring is read: it first tries Z0's readable `gauge:bma_watermap:` twin, and
  failing that, still computes the Z1/Z2/Z3 layers and `facts` from a stub Z0
  reading (Z0's own layer and the overall colour stay `UNKNOWN`, unchanged).
- A GREEN decision now raises to YELLOW whenever any layer (Z1/Z2/Z3) shows
  RED -- every row that reaches a layer colour is already colour-eligible (a
  declared relation, never a heuristic one), so this is always a real fresh
  critical the sandwich's own upstream-only ladder logic does not otherwise
  see (e.g. a same-canal neighbour whose direction is unknown). Found by this
  round's own live sweep over all 1,164 distinct committed station
  coordinates, all three sources, the real `build_answer` path plus 10
  household variants each -- that sweep's own 13 invariant counts (RED not
  from Z0, shown colour below Z0, GREEN with a true RED outlet, a layer
  hiding a critical, a layer RED under a GREEN card, an empty ring GREEN, a
  false same-canal/OUTLET label driving a colour, card colour/action rank
  mismatches, STAY at UNKNOWN or with an unknown input, RED from a 0/null
  bank) are all 0 after this fix.
- Full official-parity item inventory: 21 previously-missing actionable items
  added across the same five already-fetched guidance pages (electrocution
  rescue, lightning unplugging, branch trimming, earth-wire check,
  children-in-floodwater, rubbish/toilet, wound plaster, mosquito protection,
  sudden fever, depth pole, venomous-animal shoe check, stalled-car
  abandonment, prepare-before-calling, bridges, barricades, car-trapped,
  generator-outdoors, return-home-on-authority, children-not-in-cleanup, pets,
  report-flooding), each with its own ladder step. `disaster.go.th`/
  `niems.go.th` re-tried (both HTTP 200, neither carries standalone instruction
  text); their rows stay OPEN with that reason recorded. A new
  `advice/official_guidance_inventory.yaml` plus a coverage test checks every
  inventoried item resolves to a real, sourced row with a matching ladder step.
- `advice/ladder.py`'s `prepare_steps` ordering now sorts step ids by their
  numeric part (G1, G2, ..., G10, ...), not as plain strings — the prior sort
  put G10/O10-O15 ahead of G2-G9/O2-O9, contradicting the module's own
  file-order docstring.
- The compact (non-verbose) answer now keeps `home_shelter.tag`
  (`FLOODCONNECT_DEFAULT_PENDING_FOUNDER`) — previously only `--verbose` carried
  it, so a caller reading the default payload could not tell a founder-confirmed
  verdict from this repo's own rules-4-9 default.

**M8 safety revision (2026-10-05, independent-review response).**

- `tools/kg/rings.py`'s `_nearest_gauge` tie-break now prefers the readable
  `gauge:bma_watermap:`/`gauge:thaiwater_waterlevel:` node over an unreadable
  `gauge:thaiwater_bma:`/`gate:thaiwater_bma:` twin at the same distance. Fixes a
  regression where this tie let the unreadable twin win for most BMA stations.
- Z0 never shows a colour lower than its own fresh agency word; a point with no
  fresh upstream (`UPSTREAM_PATH`/`UPSTREAM_CHAIN`/`UPSTREAM_REACH`) row read
  never claims "top calm" (`TOP_NO_UPSTREAM`, LOW confidence,
  `official_tier: false`) instead of discarding Z0's reading to `UNKNOWN`.
- A fresh RED declared `OUTLET` row now raises the result to at least YELLOW
  (`OUTLET_CRITICAL`) on every ladder path, not only when a conflict already
  triggered the full middle fetch.
- `tools/kg/rings.py` now also walks the declared `east_chain.yaml` branch graph
  and a canal-name join (the agency's own verbatim canal/river name, never a bare
  code-prefix guess -- a code family whose members name different real canals is
  labelled ambiguous, `SAME_CODE_FAMILY`, never a same-canal claim), so Z1/Z2
  carry a canal's other stations even when they never snapped onto the same
  `river_reach`.
- Ring basis is set by relation (every reach-walk relation is `DERIVED-snap`,
  `OUTLET` is `declared` with its own `contradicts`/`ref`, `SAME_SUBBASIN` carries
  whichever join actually supplied it), never from a station's unrelated
  `IN_PROVINCE` field.
- Z3 facts are taken `UPSTREAM_PATH`-then-`OUTLET`-then-`SAME_SUBBASIN`, nearest
  first within each relation, never alphabetical by station id.
- `kb._bma_series_trend` now matches the chosen run's real timestamp nearest 30
  minutes before the current reading (not a fixed 7th-point index) and rounds
  both readings to the agency's own 0.01 m resolution before comparing, removing
  a float-noise misclassification on a true one-resolution-step change.
- `networkx` is now pinned (`==3.6.1`) in `pyproject.toml`/`requirements-ci.txt`
  so the committed `output/thailand_river_flow.graphml` re-export stays
  reproducible across environments.
- **MEASURED (live sweep, 2026-10-05, M8 revision)**: against the full 311
  committed `bma_watermap` + 807 committed `thaiwater_waterlevel` station
  coordinates, a fresh keyless collect (one GET/POST per source, no per-station
  fetch) plus the sandwich ladder gives: BMA colours
  `{GREEN: 181, YELLOW: 40, ORANGE: 33, RED: 38, UNKNOWN: 19}`; thaiwater colours
  `{GREEN: 564, YELLOW: 159, ORANGE: 9, RED: 51, UNKNOWN: 24}`. Programmatic S1
  violations (a shown colour ranked lower than Z0's own fresh decided colour) = 0
  across both sources; every `AGREE`/`official_tier: true` GREEN answer in the
  sweep had a genuine fresh upstream-relation row behind it (S2 violations = 0).
  This replaces the earlier, now-superseded "236 now resolve a real Z3" claim
  below, which was measured before the Z0-resolution fix and is no
  longer the current behaviour to cite.

**M8 P3 follow-up fix pass (same 2026-10-05 work).**

- `kb.py`'s `next_action.dual_state` overwrite from the sandwich colour no longer
  downgrades an already-decided state or replaces a decided value with UNKNOWN — it
  only overwrites `current_local_state` when the sandwich's own fold ranks
  strictly higher (RED > YELLOW > GREEN > UNKNOWN); `colour`/`label_th` are still
  always surfaced. `floodconnect_model.sandwich_decision`'s EXTRACT_MIDDLE step
  likewise never returns a colour lower-ranked than Z0's own bottom colour (a local
  ORANGE plus a top alert is agreement, not a reason to fall back to YELLOW).
- `kb._answer_sandwich` now reads the middle's toward-us relations
  (`UPSTREAM_CHAIN`/`UPSTREAM_REACH`, nearest-first by `tools/kg/rings.py`'s new
  `dist_km`) before any other relation, before the `_SANDWICH_MIDDLE_CAP` trims
  anything; when toward-us rows are left unread by the cap, the reason is
  `MIDDLE_PARTIAL:<n>_UNREAD`, never the false `MIDDLE_NOT_RISING`. Every middle row
  at/over critical is also added to `facts`.
- `floodconnect_model._sandwich_read_top`'s `TOP_CRITICAL_*`/basin-wide alert trigger
  is now restricted to `UPSTREAM_PATH` stations only (the founder's own "Z3 = the
  KG-connected upstream stations" rule) — a `SAME_SUBBASIN` station that is RED but
  not actually upstream of Z0 no longer raises a false top alert.
- `tools/kg/rings.py`: when Z0 (a `stations_v1` node) has no `IN_SUBBASIN`
  placement and no `OUTLET_JOIN` target either, its sub-basin is now inherited from
  its `SAME_STATION` twin (the pre-existing `thaiwater_bma`/`gate` node with the
  same agency code), tagged `sb_basis="SAME_STATION_JOIN"`. MEASURED on the 311
  committed `bma_watermap` rows: sub-basin coverage goes from 0/311 to 236/311
  (236 now resolve a real Z3 instead of the sandwich's `TOP_UNREAD`); the
  807 `thaiwater_waterlevel` rows were already at 797/807 and are unaffected.
  The remaining 75 bma_watermap / 10 thaiwater_waterlevel stations have no
  `thaiwater_bma`/`gate` twin at all and stay `TOP_UNREAD`, honestly, until a
  further join or the DWR polygon archive lands — not claimed fixed here. (See
  the M8 safety revision entry above for this count's own superseding re-measurement.)
- `model_spec.json` gains the missing `PROP-FLOOD-11` entry (status `GATED`,
  `shipped_in_answer: false`) that `docs/INDICATORS.md` §12 and
  `floodconnect_model.py` already pointed at; `docs/INDICATORS.md` §12 at the
  time also stated plainly that `kb._answer_sandwich` never calls `rise_eta`/
  `time_to_threshold`, so no `sandwich` answer showed Tk (a known gap, not
  shipped behaviour then), and labelled PROP-FLOOD-01/02 as PROPOSAL-tier
  there. **SUPERSEDED later in this release:** Tk and the mandatory RISING
  ETA (PROP-FLOOD-02, linear, two windows) are now wired into the sandwich
  answer (see the bullets at the top of this `v0.1.5` section); the
  `PROP-FLOOD-11` entry was later corrected (2026-10-07) to its accurate
  registered-but-not-implemented status.
- `output/thailand_water_kg.graphml`'s committed size corrected to 30.7 MB (was
  misstated as 30.3 MB); re-running `tools/kg/stations_layer.py --augment` on
  af4b1f4's pre-M8 graphml in this checkout reproduces the committed file
  byte-identically (sha256 `b430eaa3…`), verified fresh for this fix pass.

**Jev Sandwich decision model, in the model and the answer (M8, founder 2026-10-05,
"ทางที่ 2 เลย").**

- `floodconnect_model.py` gains `trend_state` (3-state RISING/STABLE/FALLING/UNKNOWN,
  PROP-FLOOD-01, a registered Toledo proposal, tier Dr — not yet a merged theorem),
  `bank_check` (at/over the agency's own bank or critical level, checked FIRST —
  flooding is water over the bank before anything else), `rise_eta` (PROP-FLOOD-02
  time-to-threshold, computed only when RISING; the separate acceleration/ETA
  extension, PROP-FLOOD-11, is built but stays **GATED** — as of this 2026-10-05
  entry Toledo PR #65 was still OPEN; it has since merged, 2026-10-06, but
  PROP-FLOOD-11 remains NOT IMPLEMENTED in this release, v0.2 target — this
  repo's equation-discipline rule means it is never computed in the answer path
  until it is wired in), `colour_ladder` (Z0 only) and `sandwich_decision` (Z0 "bottom" +
  Z3 "top" read together; on conflict the Z1/Z2 "middle" is fetched along the KG path
  toward the point — never on every call — then the decision is re-made).
- Five colours: ปกติ/เฝ้าระวัง/เตรียมพร้อม/วิกฤต/ไม่ทราบ. "เตรียมพร้อม" (ORANGE) is
  **FloodConnect's own label**, aligned with the agency phrase
  "เฝ้าระวังและเตรียมพร้อม" but not an official agency tier — stated as such everywhere
  it appears. The pre-existing closed 4-value `dual_state.current_local_state`
  vocabulary is unchanged (ORANGE folds to YELLOW there); the new 5-value colour rides
  alongside it as `dual_state.colour`/`label_th`, only when the sandwich's own Z0 has a
  fresh reading.
- `tools/kg/rings.py` (new): offline Z0/Z1/Z2/Z3 ring extraction from the committed
  `output/kg_index/` only (no graphml load, no network) — Z0 is the nearest gauge
  within radius; Z1/Z2 walk the per-province reach graph's own `dn` (downstream)
  pointers, plus the declared `canalchain_station_joins.yaml` `OUTLET_TO` edge when Z0
  has one; Z3 is every gauge in Z0's own sub-basin (or, when Z0 itself carries no
  `IN_SUBBASIN` placement — true for every brand-new M8 station node, see the P2 entry
  below — the sub-basin inherited from its declared `OUTLET_TO` target instead, tagged
  `sb_basis="OUTLET_JOIN"`, never silently treated as a direct geometric placement).
- `kb.py` wires this into `build_answer`: `_answer_sandwich` reads the Z0/Z3 (and, only
  on conflict, Z1/Z2) readings out of `data/observations.sqlite` for the two M8
  nationwide sources (`bma_watermap`, `thaiwater_waterlevel`; the pre-existing
  `gauge:thaiwater_bma:*` Sammakorn/Ram53 nodes already have their own answer path and
  are deliberately not double-read here), calls `sandwich_decision`, and appends a
  compact `sandwich` block to every answer (full decision trail — `steps`/`why`/
  `gate`/`eq` — only under `--verbose`, to stay inside the 5,000-token answer budget).
  `next_action.dual_state` gains `colour`/`label_th` and its `confidence` is capped to
  the sandwich's own confidence (weakest link) whenever Z0 is fresh.
- Real cases checked against the live 2026-10-05 capture (`tests/test_kb_answer_
  sandwich.py`): Sammakorn (WL.SMK.01, ปกติ/STABLE) next to a real over-bank reading
  elsewhere in its inherited sub-basin resolves **YELLOW เฝ้าระวัง**, never RED (a
  basin-resolution fact is never promoted to a local critical); a real agency OVERBANK
  word at Z0 itself (Prachin Buri, Kgt.1) resolves **RED วิกฤต** with the middle never
  fetched (local critical always wins).
- `docs/INDICATORS.md` documents the 4 (+UNKNOWN) colours and the sandwich ladder.
  Token-budget tests stay green with no budget loosened (see `tests/test_token_
  budget.py`); `tests/test_kb_answer.py`'s envelope-keys test updated for the new
  `sandwich` key.
- **Known limitation, stated plainly:** the pre-existing `gauge:thaiwater_bma:*`
  Sammakorn/Ram53 canal gauges are not read by `_answer_sandwich` (different, older
  collector/station-code convention) — a Z1/Z2 "middle" row on that prefix comes back
  `MIDDLE_UNOBSERVED` (LOW confidence), honestly, rather than a guessed colour. Wiring
  that prefix in too is a follow-up, not claimed here.

**Nationwide keyless station nodes in the KG (M8 P2, founder 2026-10-05, verbatim
"สกัดโหนดจากทั่วประเทศเต็มให้ครบด้วย เพื่อให้เอไอเรียก node และดูความเชื่อมโยงของสายน้ำถูก
ตาม kg" — extract nationwide nodes so an AI calling a node sees the water connectivity
correctly per the KG).**

- `tools/harvest/station_tables.py` — one bounded live fetch per keyless source
  (`bma_watermap` POST, `thaiwater_waterlevel` GET; 2 live calls total, well inside the
  ~30-call/1-req-s budget), reusing the already-reviewed `parsers.py` functions. Writes
  committed, sorted, offline source-of-truth tables `sources/stations/bma_watermap.json`
  (311 rows) and `sources/stations/thaiwater_waterlevel.json` (807 rows).
- `sources/canalchain_station_joins.yaml` — declared `LOCATED_ON` joins
  (`WL.SMK.01 -> canalchain:sammakorn_pond`, `WL.BMA.02 -> canalchain:banma`, both
  `declared_join`/RELAYED, evidence quoted) and the `sammakorn_pond -> ssb08` `OUTLET_TO`
  edge (`outlet_snap`/DERIVED-snap, 0.55 km), kept **alongside** the contradicting
  `east_chain.yaml` edge via an explicit `contradicts` attribute — neither source is
  dropped or upgraded (founder's conflicting-data rule, 2026-09-27).
- `tools/kg/stations_layer.py` — `apply(G)` / `--augment`: adds one KG node per
  committed-table row (`gauge:bma_watermap:*` — 311 new nodes, all three previously
  node-less BMA codes `WL.SMK.01`/`WL.BMA.02`/`WL.SSB.13` now resolvable; plus 5 new
  `gauge:thaiwater_waterlevel:*` nodes for live stations that had none), `SAME_STATION`
  edges to the matching existing `thaiwater_bma` gauge/gate node (235 matches, both
  directions, `agency_code_exact`/RELAYED), the two `LOCATED_ON`/`OUTLET_TO` joins
  above, and `ON_REACH` snaps for every new node using the SAME nearest-`river_reach`
  heuristic `build_kg.py` already uses for every other asset class (73 new `ON_REACH`
  edges). Every added node/edge carries `layer=stations_v1`; re-running `--augment` on
  the same graph+inputs is byte-identical (verified).
- `output/thailand_water_kg.graphml`/`.jsonld` rebuilt via `stations_layer.py
  --augment` (27,043 nodes / 64,987 edges, up from 26,727 / 64,441 — graphml 30.7 MB,
  jsonld 37.2 MB, both still well under the 95 MB budget) and `output/kg_index/`
  rebuilt via `build_index.py` on top of it.
- **Known gap, stated plainly (not silently worked around):** `IN_SUBBASIN` for these
  new station nodes is NOT attempted in this build — the DWR Sub-Basin polygon archive
  (`raw/gis/dwr_subbasin/`, gitignored, re-downloadable per
  `tools/harvest/dwr_subbasin.py`) is absent from this checkout, same documented gap
  `tools/kg/build_index.py`'s `GLOBAL_GAPS` already carries for the rest of this KG.
  `stations_layer.py`'s `--report` says so explicitly on every run. `output/kg_index/`'s
  per-province `reaches.json`/`canals.json` global slices discussed in the M8 design are
  **not built here** — left for a follow-up, not claimed here.
- `tests/test_stations_layer.py` (15 tests): committed-table sync/shape, the two
  `LOCATED_ON` joins and the `OUTLET_TO` contradiction, `apply()` behaviour on a
  synthetic graph (idempotency, no-fabrication-without-archive), and on the real
  committed KG (the 3 previously-missing nodes now resolvable, coverage-before-after,
  size budget, re-augment determinism). `tests/test_kg_index.py`'s province-slice size
  cap raised 200 KB → 250 KB (Bangkok's own slice grew to ~242 KB from real new
  content — stated here, not hidden in a diff). Full suite green, no token budget
  loosened.

**Advice layer: emergency card, preparedness ladder, home-as-shelter, official
parity (M8 P-B/P-C/P-D, 2026-10-05).**

- `advice/card.py` — `build_card()`: the compact `emergency_card` (the first key
  of the answer, aimed at the first of two audiences). A hard token budget (see
  below) applies; `now_th` comes from a closed per-colour gloss table
  (`advice/gloss_th.yaml`), `do_th` is the single most urgent action for the
  CURRENT colour/verdict (never a weaker, earlier-colour step).
- `advice/ladder.py` + `advice/preparedness_ladder.yaml` — the ordered,
  cumulative, current-colour-first `prepare_steps` list per colour (GREEN <
  YELLOW < ORANGE < RED, UNKNOWN its own row plus every YELLOW-or-earlier step).
- `advice/home_shelter.py` — `decide_home_shelter()`: the stay-vs-go verdict
  (`STAY_PREPARED`/`PREPARE_TO_LEAVE`/`LEAVE_NOW`/`FOLLOW_OFFICIAL_ORDER`/
  `UNKNOWN_ASK_INPUTS`) over the existing Dry Gate (`shelter_operation_ladder`)
  and sustainment (`shelter_decision`) checks -- a thin adapter, not a new
  decision engine. A missing/incomplete household declaration, or an unresolved
  Dry Gate/sustainment/official-instruction field, always asks rather than
  silently defaulting to STAY.
- `advice/public_shelter.py` — stays `OPEN` (no fabricated sites) while this
  repository has zero independently verified public-shelter candidates.
- `advice/parity.py` + `advice/official_guidance.yaml` + `advice/PARITY.md` —
  the official-parity check: every sourced (`OFFICIAL_TH`/`GENERAL`) guidance
  item must map to a ladder step at an equal-or-stricter colour rank, enforced
  by `tests/test_official_parity.py` (0 WEAKER, 0 MISSING in either class).
- `advice/gap_log.py` — an append-only policy-gap log (gitignored under
  `data/`), written only when a caller opts in (`write_gap_log=True`).
- `kb.py build_answer(..., household=...)` — the one wiring point accepting an
  optional household declaration (`schemas/household_declaration.schema.json`)
  and threading it into `advice.build()`.
- `schemas/advice.schema.json` / `schemas/emergency_card.schema.json` /
  `schemas/household_declaration.schema.json` / `schemas/jev_decision.schema.json`
  updated to match.
- Tests: `tests/test_emergency_card.py`, `tests/test_preparedness_ladder.py`,
  `tests/test_home_shelter.py`, `tests/test_official_parity.py`,
  `tests/test_l5_lines_reachable_in_ladder.py`, `tests/test_m8_safety_round.py`.

- **M5 water-debt backtest, EXPERIMENT** (PROP-FLOOD-03/PROP-FLOOD-10, PROPOSAL — not
  yet in Toledo): `tools/backtest/run_m5_water_debt.py` reuses `water_balance.py` and
  `score_forward_forecast.py`'s Δ10.3 ledger as-is over 6 real independent flood
  events + 8 control periods (`docs/experiments/M5_event_set.yaml`). Headline
  finding: every one of 219 unit-day rows REFUSES `MISSING_INPUT` — `S0` (initial
  storage) and `gate_flag` are **both universal** blockers (all 219/219 rows each;
  `gate_flag` is never declared for any unit), `Q_out_meas` is missing on 138/219
  rows, and the two village rows (`sammakorn`/`ram53`) additionally lack
  `A`/`c`/`C_pump`/`P` — see `docs/experiments/M5_WATER_DEBT_BACKTEST.md`.
  `n_independent=6 < N_min=10` → skill claim REFUSED FEW_EVENTS regardless. An
  experiment was added; its own numeric result (every row REFUSES) is reported, not
  a capability shipped — never wired into the answer path.

- **M7a GOV API MANUAL** (pseudocode-first calling manual, no new executable
  library, per founder scope decision 2026-10-05): `docs/API_MANUAL.md` documents
  every Thai government water API this repo's `collect.py`/`parsers.py` can fetch,
  organised by category. Adds `sources/sandwich_fetch_order.yaml` (the machine form
  of the Jev Sandwich S0-S8 fetch order) and `sources/live_call_index.yaml` (the
  KG-node-class ↔ live-source cross-reference). The rich per-ring vocabulary this
  manual documents (`worst_status`/`freshness`/`trend`/`acceleration`/`eta_to_bank`/
  `end_state`/`not_joined`/`kg_traversal`) is kept as fetch/traversal documentation
  only — `schemas/layer_readout.schema.json`/`schemas/sandwich_trace.schema.json`
  remain the actual runtime contract. New files only; no edit to
  `kb.py`/`collect.py`/`parsers.py`.

- **`skill/`**: a vendor-neutral FloodConnect SKILL.md plus `INSTALL_CHECK.md` and
  worked examples, written as instructions only (the §0b FAST LAYER one-line
  drill before any Sandwich zoom — a fixed 3-rule table, never asks the user —
  FACTS-vs-CONCLUSIONS, the mandatory RISING ETA, continuity, archive and email) —
  no new code. `schemas/email_report.schema.json` is added under `schemas/` so its
  sibling `$ref`s resolve against this repo's own schema set.
- **L0 daily check + cross-session watchlist (`l0_check.py`, `watchlist.py`):**
  a cheapest-first daily check (exactly 3 keyless sources: TMD CAP, rain, Z0
  level+trend) producing one QUIET/ESCALATE line, plus a cross-session
  watchlist state machine (ACTIVE/COOLING/CLOSED) that writes this
  installation's own local watchlist store. Exposed as the MCP tools
  `floodconnect_check` (L0 check alone) and `floodconnect_watch` (L0 check +
  watchlist write) — see the full MCP tool list below.
- **MCP tools, full list (11, `tools/mcp/floodconnect_mcp.py`):**
  `floodconnect_answer`, `floodconnect_locate`, `floodconnect_check`,
  `floodconnect_watch`, `floodconnect_list_areas`, `floodconnect_get_area_state`,
  `floodconnect_get_station`, `floodconnect_get_typology_subgraph`,
  `floodconnect_find_safe_route`, `floodconnect_list_upstream_sources`,
  `floodconnect_explain_rules`.
- **Known gap, documented not fixed:** with the real `mcp` SDK installed,
  `initialize`'s `serverInfo.version` reports the SDK library's own version
  (e.g. `1.30.0`), not `0.1.5` — `FastMCP.__init__` in this SDK version does
  not expose a `version` passthrough to the low-level `Server`, so this repo
  cannot set it without reaching into the SDK's private server object. `0.1.5`
  only appears on the stdlib stdio fallback path (no real SDK installed),
  `tools/mcp/floodconnect_mcp.py`'s own hardcoded `serverInfo`. A caller that
  needs to confirm the FloodConnect version should use `floodconnect_answer`'s
  own release tag or `pyproject.toml`, not `serverInfo.version`.
- **Mandatory RISING ETA (PROP-FLOOD-02, linear, two windows):** a
  `calc.eta`/`z0.eta` range-of-hours (current-slope + longer-window slope) is
  computed whenever Z0's trend is RISING, labelled PROPOSAL, and reachable
  without `--verbose`. This is PROP-FLOOD-01/02 arithmetic called twice — it
  is NOT PROP-FLOOD-11 (the separate acceleration-aware quadratic, which is
  also registered in Toledo, PR #65 merged 2026-10-06, tier Dr, but NOT
  IMPLEMENTED in this release; v0.2 is the target for wiring it in). See the
  release notes' ETA section for the full relabelling.

**MVP close.** Assembles the gated M8 Jev Sandwich KG-only revision with the M7a
GOV API MANUAL and M5 water-debt backtest content above, plus the `skill/`
package, the L0 check/watchlist engine, and the MCP tools above, into one
release. Scope: the MVP is validated for Bangkok and หมู่บ้านสัมมากร; other
areas are experimental (see `docs/API_MANUAL.md` and the answer tag). Relations
between stations are KG-graph-edges-only — no heuristic/guessed relation (code-
family join, name-only join, DERIVED-snap-reach join, radius-based outlet) reaches
an answer; a station with no KG edge to the user's point does not appear, and the
KG gap is logged (`policy_gap`), never guessed. Every simulation/modelled forecast
is off by default in answers (water-debt/M5 model, forecast ladder, synthetic or
extrapolated load); measured readings, KG edges, and the founder-mandated
time-to-bank arithmetic over measured slopes remain. The mandatory RISING ETA
uses PROP-FLOOD-02 (linear, two windows) — an already-registered, already-merged
proposal — labelled PROPOSAL, not a settled theorem, and still arithmetic on
readings, never a simulation. The official order is
a floor, not a ceiling: an official EVACUATE/WARNING always raises the verdict; a
missing, late, or weaker official order never lowers a ground- or reading-based RED/
LEAVE verdict, and that case's card always says to move to safety now plus
"ยังไม่มีคำสั่งทางการ — อย่ารอ" — never only "ทำตามประกาศทางการ".

Known issues (v0.1.5): BKK007's scope overclaim (a KG-data-coverage gap, not a
code bug; see `tests/test_kb_answer_sandwich.py::test_bkk007_in_nonthaburi_is_
experimental_not_validated`); the GREEN-colour-with-a-single-storey-house/
stale-declaration LEAVE_NOW over-escalation (`_assemble`'s own rules 4-9 note,
a FloodConnect default pending the founder); PREPARE_TO_LEAVE's own
move-now/no-official-order line can also show on a GREEN card when the
household's own need profile triggers it — not yet reconciled. See the
release notes' "Known gaps" section for the same list.

## v0.1.4 — 2026-10-05

**"KG-first that AIs cannot skip" (M4, founder ruling 2026-10-05, verbatim "แม้แต่เอไอ
เก่งๆก็อ่านข้าม ตกลงเราต้องทำยังไงให้เอไอไม่ดื้อ"): a chat AI that could read the v0.1.3 KG
mandate was observed (one founder-reported session) skipping straight to raw station
pages. This release makes the KG step small, fast, and load-bearing in `answer`'s and
`locate`'s own output; for a no-tool chat AI it remains an `llms.txt` instruction — no
behavioural measurement of any AI's reading choice was run this release.**

### Added
- `tools/kg/build_index.py` — deterministic per-province KG index builder (networkx +
  stdlib only, reads `output/thailand_water_kg.graphml` only, never writes to it).
  Writes `output/kg_index/index.json` plus one `province_<code>.json` per province node
  in the graph — **79 slices** (77 Thai provinces + 2 non-Thailand geocode codes present
  in the graph: 99, 10499), against the graph measured at **26,727 nodes, 64,441 edges**,
  `sha256` `33fcd36bafb7...`. Each slice carries the province's touched DWR sub-basins /
  ONWR basins, member assets (gauge/gate/weir/dam/pump_station/tide_gate) tagged by
  placement method (`pv`: `"e"` has an `IN_PROVINCE` edge, `"b"` placed by its coordinate
  falling inside the province's bbox, `"n"` placed at the nearest edge-linked member as a
  last resort — only gauges/rain-gauges carry `IN_PROVINCE` edges in this KG build, so
  every gate/weir/dam/pump_station/tide_gate row is `"b"` or `"n"`, stated plainly in that
  slice's own `gaps`), the `ON_REACH` reaches those assets snap to, `RESPONSIBLE_FOR`
  agencies, and an explicit `known_gaps` list. Province bboxes are built from
  `IN_PROVINCE` gauge/rain-gauge members only, rounded OUTWARD (`floor`/`ceil` at 3dp) so
  a member sitting exactly on a rounded boundary is never excluded (a plain `round(.,3)`
  previously excluded a real Pathum Thani member and, with it, 3 gates co-located with
  it). **Measured sizes:** median slice 9,821 B, max 187,072 B (Bangkok — its ~960
  box-placed gates/pumps are the point of that slice), total 1,045,491 B across 79 files —
  within the 30 KB median / 200 KB max budget. `tests/test_kg_index.py` asserts a fresh
  rebuild is byte-identical to the committed files, box members lie inside their own
  bbox, and index counts match slice counts.
- `tools/kg/locate.py` — offline `locate()` (stdlib only, no network, no graphml read):
  resolves a lat,lon point to its province (from a caller-supplied `--province`/`province`
  argument — code, Thai name, or English name via the committed `sources/province_names_en.yaml`
  snapshot — or up to 3 candidates, each tagged `RELAYED`, ranked by nearest `IN_PROVINCE`
  member when omitted, never a single silent guess), nearest sub-basin(s), nearest assets
  with their `ON_REACH` reach, stations sharing that reach/sub-basin, and responsible
  agencies and `known_gaps` **keyed per candidate code** when no province was resolved
  (never one flat list that silently answers for only one of the candidates), plus a
  compact `kg_anchor`. Stations exclude the 162 `gauge:thaiwater_rain:*` ids (rainfall-
  only, mislabelled `class=gauge` in this KG build — recorded in `index.json`'s `gaps`).
  **Measured:** box containment alone places the Pathum Thani test point
  14.0208,100.5343 only in Nonthaburi's box (its nearest Pathum member is 8.865 km away,
  outside Pathum's own rounded bbox) — confirming why `locate` must return candidates,
  never one guess; its `agencies`/`known_gaps` for that point are returned separately for
  each of the 3 candidate provinces, never Nonthaburi's alone. Output capped at 6,000
  characters; measured 3,344-3,827 characters (raw JSON, in-process, `ensure_ascii=False`,
  no indent) and indented CLI/MCP output 4,614–5,188 characters (indent=2; 5,188 at kb.py's
  Sammakorn coordinate 13.758235,100.676084) and in-process call time 0.004-0.023 s on
  the acceptance points (Pathum, Chiang Mai, Sai Buri, Ubon, Sammakorn, Sammakorn at
  kb.py's own coordinate), against the 3 s budget (CLI wall time, including Python
  startup, ~0.09 s per call).
- CLI: `floodconnect locate --at lat,lon [--province X] [--json]` (`kb.cmd_locate`). MCP:
  `floodconnect_locate(at, province=None)`, registered in both the real FastMCP block and
  the stdlib JSON-RPC fallback's `_TOOLS`/`_TOOL_DESCRIPTIONS`.
- `kb.build_answer` now appends `kg_anchor` as the LAST key of every answer (verified
  byte-identical to v0.1.3 otherwise, by diffing an offline Sammakorn answer against
  `origin/main` with `generated_at`/`kg_anchor` excluded). The outside-Thailand branch
  gets `kg_anchor: {"tag": "OPEN", "method": "outside_thailand"}`. When the KG index
  cannot be read, `kg_anchor` degrades to `{"tag": "OPEN", "method": "no_kg_index"}` and
  `next_action.dual_state.confidence` is capped from `HIGH` to `LOW` — `state`'s own
  `resolution_confidence` is a different field and is left untouched, so the two CAN
  differ when the index is missing (by design: `dual_state.confidence` is what a caller
  actually reads to decide how much to trust the colour; `resolution_confidence` records
  what the station data alone supported).
- `llms.txt`'s first non-heading line (both EN and TH) is now the KG-first instruction:
  tool users run `floodconnect locate`/`floodconnect_locate` first; no-tool chat AIs
  fetch the raw `output/kg_index/index.json` URL then the matching province slice; every
  answer must state its `kg_anchor` or it is "not a FloodConnect answer". Mirrored
  (briefly, pointing at the real detail rather than restating it) in `README.md`,
  `docs/AI_TIERS.md`, `docs/NEAREST_STATION_RECIPE.md` (new Step 0b), `docs/KG_QUERY.md`
  (new §0b, the slice schema + `pv` legend), and `system_capabilities.json` (new
  `kg_first` block, `locate`/`floodconnect_locate` added to `entry_points`).
- Token-budget fix: `AI.md`'s "On-demand refresh" section was
  trimmed (full detail already lived, unchanged, at `docs/AI_ENTRYPOINT.md`) from 1,997
  to 1,759 tokens to recover the margin `kg_anchor` costs. **Measured totals**
  (AI.md + SKILL.md + answer, cl100k): populated-DB scenario now 1,759 + 1,226 + 1,579 =
  **4,564** tokens (436 below the 5,000 ceiling, comfortably above the 300-token safe
  margin); `tests/test_token_budget.py`'s existing ceilings are unchanged and stay green.

- `sources/province_names_en.yaml` — a committed, hand-typed (`tag: RELAYED`, not an
  independently re-verified government source) snapshot of the 77 Thai provinces'
  standard English names, cross-checked code-by-code against the Thai names already in
  `output/thailand_water_kg.graphml`'s own province nodes. `build_index.py` reads it to
  fill `index.json`'s `en` field for all 77 (the 2 non-Thailand codes, 99/10499, stay
  `null`); `locate --province "Pathum Thani"` now resolves the same as `--province 13`.
- Per-asset `ag` in each slice now prefers the KG's own `OWNED_BY_AGENCY` edge (VERIFIED,
  from `sources/owner_agency_crosswalk.yaml`) over the previous owner-name string match,
  which missed it whenever the free-text owner field didn't exactly match an agency
  node's `name_th`. **Measured**, before/after this fix: asset rows with `ag=null`
  across all 79 slices dropped from 3,576/5,095 to 866/5,095.
- `locate`'s "province not recognised" error now lists every province in the index
  (previously the first 5 by code only).

### Fixed
- `system_capabilities.json`'s `pyproject_version` was still `"0.1.2"` (a pre-existing
  stale value, found while bumping it for this release) — now tracks `pyproject.toml`.
- `locate`'s `agencies`/`known_gaps` no longer come from a single silent nearest-member
  vote when no province could be resolved (the exact Pathum Thani 14.0208,100.5343
  pitfall this milestone names: the vote put it in Nonthaburi alone) — see above.
- `cand` entries and `kg_anchor` are now tagged `RELAYED` in candidate mode, matching the
  wording the docs already used.
- `stations`/`kg_anchor.station_ids` no longer include the 162 `gauge:thaiwater_rain:*`
  ids (rainfall-only gauges the KG mislabels `class=gauge`) ahead of real water-level
  gauges.

### Not in scope (frozen, per founder instruction)
- No small-model measurement pass (explicitly declined on cost).
- The shipped KG did not become the default for `answer`'s own accountability path;
  `FLOODCONNECT_USE_SHIPPED_KG` is unchanged.
- M2b items still backlog: crosswalking the geocode id-prefix for `pv="b"`/`"n"` assets,
  splitting the Bangkok slice.
- `output/thailand_water_kg.*` is byte-unchanged — this release only reads it.

## v0.1.3 — 2026-10-05

**Nationwide knowledge graph shipped in git, KG-first mandate (founder ruling
2026-10-04, verbatim "อย่างแรกให้เอไอต้องอ่านแผนที่กราฟของเราได้จาก git ก่อนและบังคับว่าต้องหาจาก
kggraph นี้") — milestone M2a of the founder-approved "แบ่ง M2a/M2b" split.**

### Added
- `output/thailand_water_kg.graphml` + `.jsonld` committed directly in git (build 7,
  2026-10-04) — **26,727 nodes, 64,441 edges**, readable with a plain `git clone`, no
  rebuild/network call required. Headline edge counts: `IN_SUBBASIN` 9,307 edges
  (`VERIFIED-geometric`, real point-in-polygon against the archived DWR Sub_Basin
  polygons), `ON_REACH` 785 edges (`DERIVED-snap`, nearest-centroid-point heuristic,
  never the snapped asset's own tag — per-class coverage: dam 4/86, gate 315/2,279,
  gauge 251/1,231, pump_station 117/297, reservoir_medium 69/862, weir 29/102, every
  other class 0; `rain_gauge` excluded by design). 79 `province` nodes + 735 `amphoe`
  nodes (both `VERIFIED`, from the HII geocode harvest).
- `main_stem` (bool) on every `river_reach` node — one branch per HydroRIVERS river
  system (`main_river_id` group) by discharge, including the Mekong group (restarted
  2026-10-04 after its own group was found split into two fragments, 983 + remainder,
  by the Thailand bbox clip — fixed so the in-Thailand portion is never silently left
  untagged). This is the HydroRIVERS-system sense, not the Thai administrative
  "สายหลัก" per-ONWR-basin sense — see `docs/KG_QUERY.md` section on `main_stem` and
  "Known gaps" below. `output/thailand_river_flow.graphml` (+ `.jsonld`) was
  regenerated without a GISTDA flood snapshot: `flood_status` is now `unknown` on
  all 2,250 reaches and `flood_source_node` / `eta_from_flood_hr` are `"null"`
  everywhere (the keys remain). `main_stem` is not in this file; it is only in
  `output/thailand_water_kg.*`.
- `docs/KG_QUERY.md` — the recipe page every AI session reads first for anything
  basin/province/amphoe/river/station/gate/agency-shaped, with measured (not
  aspirational) coverage numbers and runnable Python snippets against the shipped
  graph.
- **KG-first mandate** wired into `AGENTS.md` and `docs/AI_TIERS.md`: before locating
  or reasoning about any place outside Sammakorn/Ram53, a file-reading AI session
  reads the shipped graph from git first, never re-derives/re-geocodes it. A new
  `docs/knowledge/INDEX.yaml` entry (`KG_QUERY`) points at the same page.
- `FLOODCONNECT_USE_SHIPPED_KG` environment guard in `kb.py` — the shipped nationwide
  graph is only consulted for a bare lat,lon's accountability answer when this guard
  is set; the default (unset) answer path is unchanged from v0.1.2 (nationwide coarse
  station/basin reading + `_nationwide_accountability_fallback`'s text-only
  province/agency fallback), so shipping the KG does not silently change what a
  default `floodconnect answer` call returns.

### KNOWN GAPS → M2b (not closed by this build, stated here rather than papered over)
- **Pathum Thani: 0 of 15 Pathum assets have an `ON_REACH` edge** (4 water-level
  gauges + 11 rain gauges, the latter excluded from `ON_REACH` by design); 13 of the
  28 HII-geocoded Pathum ids ARE nodes in the shipped graph (as `gate:hii_watergate:<id>`)
  but carry no `IN_PROVINCE` edge, because the geocode join misses them on an id-prefix
  mismatch (see the geocode file's own `known_limitation`) — a join/crosswalk gap, not a
  missing-node gap. The "0 `ON_REACH` for Pathum" figure holds either way, these 13 included.
- **Canal snapping**: the `ON_REACH` heuristic never snaps to a declared canal-chain
  reach — a canal-sited asset still snaps to the nearest HydroRIVERS river reach
  regardless, often far away (250 of the 785 edges are from an asset whose name_th
  contains คลอง; among those 250 canal-sited edges: median snap 1.58 km, 34 over 5 km,
  15 over 10 km, max 15.71 km). True point-to-polyline snapping across river AND canal
  reaches together is M2b.
- **Point → province/accountability resolution is not wired** for a bare lat,lon
  outside Sammakorn/Ram53: `province`/`amphoe` nodes carry no geometry, and
  `tools/kg/accountability.py`'s `nearest_assets()` never reads `RESPONSIBLE_FOR` or
  walks to a province/basin node. Wiring this, plus a real id crosswalk for
  unmatched gates/dams, is M2b.
- **Per-basin main river**: `main_stem` is per HydroRIVERS system, not per ONWR
  basin — a second, explicit `basin_main_river` flag (or a crosswalk to the Thai
  "สายหลัก" sense) is M2b.

## v0.1.2 — 2026-10-04

**Nationwide coarse (station/basin) coverage — founder ruling 2026-10-04, verbatim
"ทำเลย v0.1.2 ทั้งประเทศ แล้วค่อยพัก".**

### Added
- Any `lat,lon` in Thailand now gets a real `current_local_state`/`forward_hazard`
  reading, not just the two Bangkok MVP areas (Sammakorn village, Soi Ramkhamhaeng 53,
  which keep their existing household/node-level detail, unchanged). Resolution is
  **coarse (station or basin), never household-level**, outside those two areas:
  - **Station resolution:** every fresh `thaiwater_waterlevel` station within 10 km
    (any water body, not checked against `river_name`) decides, worst colour wins —
    not just the nearest one (Chanthaburi has 3 deciding stations at once).
  - **Basin resolution:** failing that, a fresh reading sharing the NEAREST station's
    own `sub_basin_id` (a stand-in for "same basin", not a check that both stations
    sit on the same named river) within 50 km decides — but can **never** produce
    GREEN on its own (it can still raise YELLOW/RED), and only when no local
    colour-bearing factor-4 source (Bangkok canal/pump telemetry) already decided
    this point. A local reading never suppresses a nationwide STATION-resolution
    row (<=10 km) this way — only a basin-resolution one — so a station sitting at
    0.0 km on a fresh agency OVERBANK status still decides even when the point also
    has fresh local telemetry.
  - No fresh reading within 50 km sharing that sub-basin → `UNKNOWN` (never GREEN by
    default).
  - Both radii are FloodConnect's own stated design choice (`docs/INDICATORS.md` §11),
    never an agency threshold.
- `parsers.parse_thaiwater_waterlevel` now keeps `min_bank`, `ground_level`,
  `critical_level_msl`, `situation_level`, `diff_wl_bank`, `diff_wl_bank_text`,
  `river_name`, `sub_basin_id`, `basin_id`, `basin_name_th`, agency shortname, amphoe/
  tambon, and `waterlevel_msl_previous` (exact field paths MEASURED against one live
  GET of the feed, 2026-10-04 — `diff_wl_bank`/`diff_wl_bank_text`/`situation_level`/
  `storage_percent` are top-level, NOT nested under `station`).
- `collect.collect_thaiwater_waterlevel` fills `observations.bank`/`critical`/`status`
  (status is the agency's own verbatim code, `thaiwater_situation_<n>`, or `OVERBANK`
  when the agency's own `diff_wl_bank_text` itself reads "ล้นตลิ่ง"), and the source is
  now in `collect.ANSWER_SOURCES` with an explicit `max_age_hours: 24` in
  `sources/registry.yaml`.
- `floodconnect_model.STATUS_TO_LEVEL`: the ONE closed status-word → colour map this
  repository uses. `readout.py` and `kb.py` now read their `*_LIKE_STATUS` sets off it
  instead of keeping separate copies.
- The 16-day forecast (`forward_hazard`) is now fetched and read at the queried
  coordinate for any `lat,lon`, not only the 11 previously hardcoded forecast points
  — EXCEPT a point within the snap radius of one of those named points, which is
  still read under that named point (e.g. a Chiang Mai-area query prints "จุด
  chiangmai", not its own raw coordinate).
- Accountability for a nationwide (non-MVP-area) point is now **text**: the deciding
  station's own feed-published province and owning agency — never a fabricated phone
  number, never a graph lookup (the governance knowledge graph is a separate,
  not-yet-built piece of work).
- `state.evidence` rows from the nationwide path carry `dist_km`, `resolution`
  (`"station"`/`"basin"`), and `agency` — shown even in the default (non-`--verbose`)
  answer, never dropped into the stale-rows cap.

### Fixed
- **`NO_THRESHOLD` (no agency level published at all for a station) no longer
  classifies as GREEN.** It carried no basis for that colour — it now correctly gives
  `UNKNOWN`, both in `floodconnect_model.classify_counts`/`classify` and in
  `kb._classify_current_local_state`.
- The Thai colour-contract heading in `docs/INDICATORS.md` ("ใช้กับทุกตัวชี้วัด
  ไม่มีข้อยกเว้น") and the unscoped sentence in `docs/AI_TIERS.md` are corrected to say
  the RED/YELLOW/GREEN/UNKNOWN contract applies only to `current_local_state` and
  `one_decision.level` — every other indicator has its own closed vocabulary.
- `docs/NEAREST_STATION_RECIPE.md` Step 4 now names `situation_level` and
  `critical_level_msl` explicitly, states that a bare bank number never sets a colour
  on its own, and copies the full §1 status-word mapping (previously missing the
  "any other status word → YELLOW" fallback and the agency-overflow-text rule).
- Field-path statements in `docs/INDICATORS.md` §7/§8 and the recipe's source table
  corrected to the real, measured feed shape.
- `docs/NEAREST_STATION_RECIPE.md` no longer cites an internal, unpublished note name
  as its source for the conflicting-data rule — it now points at `AI.md`.

### Changed
- `pyproject.toml` version and the MCP server's `serverInfo.version` bumped to
  `0.1.2`.
- README.md, `llms.txt`, `docs/INDICATORS.md` §11, `system_capabilities.json`
  (`areas_covered`), and `ROADMAP.md` updated to say nationwide COARSE coverage is
  shipped, not "in progress" — and that it is coarse, never household-level, outside
  the two named Bangkok areas.

### Not included in this release
- `distance_to_bank_m`/`bank_fill_percent` (§7/§8) are relayed in `provenance` only,
  not a standalone top-level answer field or a numeric colour cutoff — Toledo-first
  discipline: no invented threshold. The agency's own `situation_level`/
  `diff_wl_bank_text` words are what actually drives the colour.
- The agency's own Thai label/colour for each `situation_level` code (1–5) is
  VERIFIED (fetched from the public bundle
  `https://www.thaiwater.net/dist/js/app.chunk.js`, 2026-10-04) — see
  `floodconnect_model.py`'s `STATUS_TO_LEVEL` comment for the full table. Level
  4 ("มาก") is coloured BLUE by the agency and is not called a warning there;
  FloodConnect's own mapping of level 4 → YELLOW (and 1/2 → GREEN) is this repo's own
  conservative choice on top of the agency's labels, not an agency threshold.
- The Water-Debt/Jev/DSVA one-decision envelope, the `--level` tiers, and a
  geolocated nationwide governance/accountability knowledge graph remain v0.2+ work
  (see `ROADMAP.md`).

## v0.1.1 — 2026-10-04

See `.ai/claims/20261004-floodconnect-v011-claim.yaml` and git history — predates this
file.
