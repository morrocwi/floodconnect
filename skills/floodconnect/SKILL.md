---
name: floodconnect
description: >-
  Use for any question about current flood/canal/pump/tide state or forecast
  for a Bangkok-area community FloodConnect covers (currently Sammakorn,
  Ram53) -- "is it safe to leave/stay", "where do I go", "what's the canal
  level", "is there flooding right now". Calls FloodConnect's read-only API
  v1 -- local files only, never hosted -- via MCP tools or the CLI, and
  reasons about the result under a fixed epistemic contract: dual-state,
  UNKNOWN != SAFE, sourced/tagged values, contradictions shown both-sides,
  no evacuation orders.
---

# FloodConnect — external AI interface

**Sibling:** reasoning rules live in `../floodconnect-method/SKILL.md`.

## When to use this skill

Any query about:
- current flood / canal water level / pump status / tide state for Sammakorn or Ram53
- a forecast or hazard outlook for those areas
- "is it safe to leave/stay", "where do I go", "what's the canal level right now"
- a self-help/evacuation route question for those areas

This skill does not cover areas FloodConnect has not built yet — check your own
local `site/dist/api/v1/index.json`'s `areas` list (or `floodconnect_list_areas`)
before answering for any other place name.

## Installing this skill (self-install only)

This skill's own markdown is portable, but calling it for real needs this repo cloned
on the SAME machine the skill runs on — never a call through a server we run (founder
ruling 2026-10-02). Minimum install:

```bash
git clone <repo-url> floodconnect && cd floodconnect
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[mcp]'   # drop [mcp] if you only want the CLI
```

Then either:
- copy (or symlink) `skills/floodconnect/` into your AI client's skill folder, and
  set its MCP config per `tools/mcp/README_config_example.json`; or
- skip MCP and run `floodconnect answer --at sammakorn --json` directly.

No hosted/pre-computed data: this clone ships NO *live* reading (`examples/` has
labelled samples only, never current). A fresh clone's first call refreshes by default
(live fetch, your own machine/network/keys); it returns `UNKNOWN` only if that refresh
finds nothing fresh, or `--offline` is passed — see `AI.md`'s "On-demand refresh". No
key, account, or server call of ours is ever required.

## How to call

**Call `floodconnect_answer` first** (MCP tool, or `floodconnect answer --at
<area> --json` on the CLI) for every real question — it checks freshness against
the real wall-clock and nulls stale forecast figures/words in the data itself, not
only in a printer. The other MCP tools (`floodconnect_list_areas`, `get_station`,
`get_typology_subgraph`, `find_safe_route`, `list_upstream_sources`) read the same
local export: they return `NOT_FOUND`/OPEN + "run refresh first" until you have
generated one on your own machine.

`get_area_state` is a secondary/debugging path: reads your own locally generated
`site/dist/api/v1/areas/<id>.json` (never a network fetch), recomputed against the
real wall-clock, not the baked build-time value. No remote `FLOODCONNECT_API_BASE`
is ever accepted — a URL is refused outright (no-hosted-access ruling, 2026-10-04).

`cctv` (≤3 nearest, `VISUAL-CHECK`) appears when a camera exists — look yourself,
never a decision input.

## Mandatory reasoning rules

**Single source: `AI.md`'s "Mandatory reasoning rules" section (repo root)**
— not restated here, to avoid a two-copies-drift risk. Read it before
answering. Full founder-rule provenance for each rule:
`references/epistemic_rules.md`.

## Worked example

See `references/sammakorn_worked_example.md` — it reproduces the exact
incident this API exists for (an external AI wrongly reported "receiving
canal = UNKNOWN" for a station that was in fact fresh and readable), plus the
correct downgrade behaviour once that same station ages past the freshness
cutoff.

## Upstream recipes

Before calling any upstream government/third-party API on a resident's
behalf, read `sources/registry.yaml` (or `floodconnect_list_upstream_sources`)
and obey that entry's `host_rule.max_requests_per_run` and the general
one-request-per-URL / no-retry discipline. Never call an upstream API that
isn't in the registry.

`references/upstream_recipes.md` carries the general calling rules, one
worked example, and a compact TOON-form recipe table (URL + method + parse
hint for 8 representative wired sources — `thaiwater.net` canal/dam feeds,
`open-meteo.com` forecast/archive, MET Norway, GDACS, RID) — read it there
rather than restating it here; `AI.md` (repo root) points to the same file.

## Banned words (for this file's own lint check — do not prune this list)

ไม่ต้อง, ห้าม, ไม่ควร, ผ่อนคลาย
