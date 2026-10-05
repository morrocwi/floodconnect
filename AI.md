# AI.md — the minimal entrypoint

One compute call, one reading list. If you are an AI answering a question about current
flood/canal/pump state, a forecast, who is responsible, or what a resident can do for
Sammakorn or Ram53, start here before improvising your own route/forecast logic.

## Compute call

```bash
python3 kb.py answer --at sammakorn --json     # or --at ram53, or --at "lat,lon"
```

Returns one small JSON envelope: `generated_at` + `at` (request metadata) plus five
content fields, each carrying its own `tag` from the fixed set
VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN (never silently promoted to a higher tier; a
field that is MEASURED off a topology/graph rather than a live instrument also carries a
`basis` key saying so (allowed: `"unverified"`/`"partly measured"`), and a field whose
underlying tag was contradicted-but-not-yet-reconciled carries a sibling `contradicted:
true` key next to `tag` -- never a compound tag string. Either way the tag itself stays
one of the five, not a sixth value:

- `state` — current local reading (reuses `readout.build_readout`)
- `hazard` — forward rain outlook, third-party models, RELAYED, never averaged with
  `state` (dual-state: a calm current reading does not cancel a forecast hazard); dates
  are Bangkok-LOCAL, at or after local tomorrow; `stale: true` past the cutoff
- `accountability` — who owns/commands here, overlapping authority, self-help options
  (reuses `tools/kg/accountability.py`; each Q-answer keeps its own inline tag)
- `next_action` — a feasible self-help route if one exists (reuses
  `community_dag.find_safe_route`); `found: false`/`tag: OPEN` honestly, never `SAFE`
- `source_tags` — one entry per field above, its real RKG `epistemic_class` where one
  exists, `null` + a `note` where it doesn't (`hazard`/`accountability`); PROPOSAL-tier
  sources carry `toledo: "not yet in Toledo"`
- `cctv` — present only when a camera exists; ≤3 nearest, `VISUAL-CHECK` (look
  yourself, never a decision input), kept even when far (`within_radius: false`)

Health status is derived from the real fetch already recorded in
`data/observations.sqlite` (per-source staleness vs its own cutoff) by default — no
separate pre-use probe call runs unless you ask for one (see `connectors` below), to
avoid doubling any rate-limited upstream fetch.

## On-demand refresh — runs on YOUR network/keys, never ours

No scheduler. `answer`/`floodconnect_answer` refresh by default (`--offline` opts
out); `connectors --live` does one real GET per wired source. Full detail (per-source
`key_env`, skip/stale semantics, freshness gate): `docs/AI_ENTRYPOINT.md`.

## Three ways to the same data — pick one, don't improvise a fourth

```text
MCP tool    -- tools/mcp/floodconnect_mcp.py (stdio; needs `pip install -e '.[mcp]'`,
               config: tools/mcp/README_config_example.json)
kb.py answer -- the compute call above (direct, in-repo, no server to run)
api/v1 json -- local export under site/dist/api/v1/** (index.json first, then the
               endpoint it points to; a local file, never fetched over a network)
```

Freshness differs: `kb.py answer` reads the live store at call time; the other two
read `tools/api/export_api.py`'s last-written snapshot, which can lag. No hosted copy
exists -- `site/dist/api/v1/**` is gitignored, generated only by running
`site/build_data.py` then `tools/api/export_api.py` locally; `get_area_state`/
`list_areas` return UNKNOWN + a refresh action until you do, and the MCP server
refuses a remote `FLOODCONNECT_API_BASE` outright (no-hosted-access ruling,
2026-10-04). Prefer
`floodconnect_answer`/`kb.py answer` day to day. Route logic is not duplicated
between them (both call the same `community_dag.find_safe_route`). Full tool list,
config, and `skills/floodconnect/SKILL.md`'s relationship to these two routes:
`docs/AI_INTERFACE.md`.

## Upstream direct-fetch recipes

Only needed if you are an external AI that wants to fetch a government/third-party
source yourself rather than running `kb.py answer` (refresh is the default) in this repo. The full
recipe table (moved out of this always-loaded file, read only on demand, to stay
inside this file's own token budget — see the token-budget test) now lives in
`skills/floodconnect/references/upstream_recipes.md`. Same rule either way: **one GET
per URL, no retries, respect `host_rule.max_requests_per_run`** (`sources/registry.yaml`
is the full 42-source registry). Nothing fetched this way is a FloodConnect equation —
tag whatever you derive `RELAYED`, never `VERIFIED`.

## Mandatory reasoning rules (the one copy — do not restate elsewhere)

1. **Dual-state, always.** Report `state`/`current_local_state` and
   `hazard`/`forward_hazard` as two separate statements — never collapse them
   into one verdict. A calm current reading does not cancel an active forecast
   hazard.
2. **UNKNOWN is never SAFE.** A field tagged `OPEN`, or `staleness.age_class:
   expired`, means "data not available / stale" — never infer normalcy from
   absence (see `dsva-redteam` skill's non-equivalence list).
3. **Carry provenance through.** Every number/state you relay keeps its
   `source` + `observed_at`/`issued_at` + `tag` — copy these into your own
   answer, don't strip them.
4. **Contradictions, both sides.** If a `contradictions[]` list for the topic
   is non-empty, present both rows; never average or silently pick one.
5. **No evacuation orders.** Informational only. For anything actionable,
   defer to official channels: 1669 (medical emergency), 1784 (DDPM disaster),
   1555 (BMA), 1130 (กฟน./MEA — electrical hazard in floods), Traffy Fondue.
6. **Resident-facing word bans.** Never use ไม่ต้อง / ห้าม / ไม่ควร / ผ่อนคลาย in
   resident-facing text — rephrase around them, not just avoid them at a
   sentence's start.
7. **No AI/vendor credit.** Never name an AI vendor/model in resident-facing
   output; use the neutral "ผู้ช่วย AI" if attribution is asked for.

Full provenance/founder-rule citations for each rule:
`skills/floodconnect/references/epistemic_rules.md`. Worked example (the
Sammakorn incident this interface exists for):
`skills/floodconnect/references/sammakorn_worked_example.md`.

## If you need more than the three routes above

```text
AGENTS.md                                    -- rules, Toledo-first, wording law
docs/AI_ENTRYPOINT.md                        -- fuller AI-facing reference
docs/AI_INTERFACE.md                         -- MCP/API v1 technical spec
site/inputs/meta/floodconnect_repo_kg.yaml   -- canonical node/epistemic_class map
sources/registry.yaml                        -- every upstream source + its host_rule
```

(a per-file merge ledger from the 2026-10-02 local/public merge is kept as an internal
local-only team record, not synced to the public mirror)
