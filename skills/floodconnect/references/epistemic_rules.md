# FloodConnect epistemic rules — provenance only

**The rule text itself lives in exactly one place: `AI.md`'s "Mandatory
reasoning rules" section (repo root).** This file does not restate it. Read
`AI.md` for the current wording; use this file only to find where a rule
traces back to.

## Tag vocabulary — one place, `AI.md`

`AI.md`'s compute-call section states the fixed five-value set:
`VERIFIED | MEASURED | RELAYED | INSTINCT | OPEN`. There is no sixth tag
value. A finer-grained reading that a caller may want to log (e.g. "this
MEASURED value came off a topology/graph rather than a live instrument", or
"this RELAYED value traces to a community report rather than an official
source") is carried as a **`basis` key alongside the tag**, never as a new
tag string — see `AI.md`'s own parenthetical on this. Earlier drafts of this
file and of `tools/mcp/floodconnect_mcp.py`'s `EPISTEMIC_RULES` constant
listed `MEASURED-community`, `MEASURED-history`, and `PROPOSAL-derived` as if
they were additional tags; they were not kept — read them as `tag: MEASURED,
basis: "community"` / `tag: MEASURED, basis: "history"` and
`tag: "OPEN", basis: "proposal-derived"` respectively if you encounter that
older phrasing anywhere else in the repo.

## Per-rule provenance

1. **Dual-state, always.** Traces to the Sammakorn incident this whole
   interface exists for (`references/sammakorn_worked_example.md`): an
   external AI collapsed a calm current reading into "no forecast risk
   either." RELAYED from the wider workspace: the universal readout-not-truth
   lens (project decision 2026-07-31) applies the same discipline generally.
2. **UNKNOWN is never SAFE.** Same Sammakorn incident; formalized workspace-
   wide as the `UNKNOWN != SAFE` non-equivalence in the `dsva-redteam` skill
   (`DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md` lineage).
3. **Carry provenance through.** The four-tag epistemic floor
   (VERIFIED/MEASURED/RELAYED/INSTINCT, plus OPEN) is the workspace-wide
   epistemic-floor rule applied to this repo's data fields.
4. **Contradictions, both sides.** RELAYED: project decision 2026-09-27 on
   FloodConnect specifically — two sources on the same station are kept as
   both-sides contradiction rows, never silently preferred (memory:
   "FloodConnect: conflicting-data rule").
5. **No evacuation orders.** This repo's own design boundary (`AGENTS.md`,
   `community_dag.py` header): FloodConnect is an operational routing
   readout, not a flood forecaster or an authority that issues directives.
6. **Resident-facing word bans.** This repo's own lint list (see this
   skill's `SKILL.md` banned-words section and `kb.py`'s resident-facing
   formatter) — kept here as the fixed vocabulary the lint checks against,
   not as rule prose.
7. **No AI/vendor credit.** RELAYED: workspace-wide project decision 2026-09-05
   ("no AI/vendor name as author, co-author, contributor, or credit in
   anything leaving the workstation") applied to resident-facing FloodConnect
   output specifically.

Worked example for rules 1–2: `references/sammakorn_worked_example.md`.
