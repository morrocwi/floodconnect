# AI capability tiers

Which kind of AI are you, and what should you do with FloodConnect? This page
answers that in **capability** terms, not product names. Product names below
are **examples only — check your own tool's current features**, since any
given tool can move tier over time (gain a shell, lose browsing, add an MCP
connector, …).

**Ground truth this page assumes (re-verify against `system_capabilities.json`
and `AGENTS.md` rather than trusting this file's memory):** FloodConnect does
on-demand fetch on the caller's own machine when you run `floodconnect
answer` (refresh is the default; `--offline` opts out). There is no schedule,
no cron, and no server-side fetch of ours. A public static snapshot page
(`site/landing/`, no data) is rebuilt only on push to that one folder — it is
not a live data endpoint and must never be treated as one.

**Nationwide KG-first (founder ruling 2026-10-04):** before locating or reasoning
about any place outside Sammakorn/Ram53, every tier that can read files (T3-T5;
T2 via the MCP tool's own KG-aware answer) reads the shipped nationwide
knowledge graph from git first — never re-derive it. Recipes: `docs/KG_QUERY.md`.

| Tier | What it is (examples) | Shell/tools | Correct job here |
|---|---|---|---|
| **T0** | A search engine's AI summary snippet, no real browsing | none | Cannot act. Tell the user to open an AI that can browse or install software. |
| **T1** | Online chat session with web browsing, cannot run a local program or a local stdio MCP server (e.g. free web ChatGPT, Gemini, Claude.ai) | read pages only | Explain, point to official sources, never invent a reading. |
| **T2** | Desktop chat app with the FloodConnect MCP connector configured (e.g. Claude Desktop + MCP) | MCP tool calls only | Call the tool, relay its real answer and tags. |
| **T3** | Coding/terminal agent with a real shell (e.g. Codex CLI, Claude Code, similar) | full shell | Install, run the CLI/MCP, read the real output, run tests, troubleshoot. |
| **T4** | Co-work / computer-use agent with files and apps (e.g. Cowork-style agents) | shell + files/apps, no server of its own | Everything T3 can, plus prepare household checklists/files and set the **user's own local** reminders — never a shared/server-side schedule. |
| **T5** | Developer / API integrator — an agent framework or script calling this programmatically | code, no chat UI | Call the CLI/MCP from code, read `system_capabilities.json`, respect the token budget. |

**The flood indicators every tier reasons over — full dictionary in
`docs/INDICATORS.md`.** Closed set: `current_local_state`, `forward_hazard`,
`rise_rate_dk`, `time_to_threshold_tk`, `rain_24h_mm`, `rain_7day_per_model_mm`,
`distance_to_bank_m`, `bank_fill_percent`, `one_decision` (+ `confidence`),
`water_debt` (planned v0.2+). `current_local_state`/`one_decision.level` use
RED/YELLOW/GREEN/UNKNOWN only (UNKNOWN is never SAFE) — every OTHER indicator has its
own closed vocabulary, see `docs/INDICATORS.md`'s colour-contract scope note.

## T0 — search snippet, no browsing

- **CAN:** nothing active.
- **MUST NOT:** answer a flood question from a cached snippet as if it were current.
- **First step:** there is none — this tier cannot run FloodConnect.
- **Expected output:** none; defer to the user.

## T1 — online chat, no local execution

- **CAN:** explain what FloodConnect is; say it is a readout, not a forecast,
  not a safety certification; say it fetches **on the installer's own
  machine, on demand, with no schedule or server-side feed of ours** (not the
  bare word "not live" — it does fetch live data when a caller runs it, just
  never on our side and never automatically); give the official emergency
  numbers (1669, 1784, 1460, 1555, 1130, Traffy Fondue); tell the user to
  install it themselves or ask a T2/T3 AI.
- **MUST NOT:** say or imply "safe"/"ปลอดภัย"; claim an auto-update, a
  schedule, a cron job, or a server-side live feed of ours (there is a static
  explainer page on GitHub Pages — no data — do not call that "live" either);
  claim a validated water-level or flood-depth forecast; present a dated
  example in this repo (`examples/*.EXAMPLE-*.json`, README samples) as the
  current situation; judge the whole project from one legacy file (e.g.
  `raw_stage_forecast.py`, which is not called by any product path).
- **First step:** read `llms.txt` (the weak-AI entrypoint), not an older or
  cached doc.
- **Expected output:** a plain explanation + official numbers + the exact
  next step (install, or ask a shell-capable AI) — never a made-up reading.
- **If this T1 session CAN browse the open web** (most online chat AIs can):
  you do not have to stop at "explain only". FloodConnect is a **method**, not
  a hosted data service — it never geocodes and holds no place/POI database,
  so finding the user's coordinate is your own job (ask for a pin, or use
  your own map tool), but once you have lat,lon you can follow
  `docs/NEAREST_STATION_RECIPE.md` yourself: fetch the nationwide
  `api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel` JSON (no key)
  or the BMA Bangkok pages, pick the nearest station within ~3 km on the same
  water body, read the agency's own status word, check freshness, classify
  per `docs/INDICATORS.md` §1. **Never invent a station, a coordinate, or a
  number not actually on the page you fetched.**
- **If this T1 session also has a code sandbox** (no shell/no repo clone,
  but CAN run a little Python): fetch the two raw files below and use
  `floodconnect_model.py`'s `delta_k`/`time_to_threshold`/`classify`/
  `one_decision` functions directly, stdlib only, no install — the exact
  same by-hand arithmetic `docs/EQUATIONS_FOR_AI.md` describes in prose,
  never a looser version of its Toledo-status/BOT≠ZERO rules:
  - `https://raw.githubusercontent.com/morrocwi/floodconnect/main/floodconnect_model.py`
  - `https://raw.githubusercontent.com/morrocwi/floodconnect/main/model_spec.json`
  (resolve once this release reaches the public `main` branch; a 404 means
  it hasn't landed there yet — fall back to the prose page or a T0 answer.)
  A sandbox with NO compute at all (pure T0) has no use for these URLs.
  **If you must self-report a tier code, this case is still `T1`** (a code
  sandbox with no shell/no repo install is not a seventh tier — it is T1 plus
  the by-hand-compute ability described in this bullet; do not report `T3`,
  which requires a real shell and an actual installed CLI, neither of which
  this case has).

## T2 — desktop chat app with MCP

- **CAN:** call the `floodconnect_answer` MCP tool with the right area
  (`sammakorn`, `ram53`, or `"lat,lon"`); relay `state`/`hazard`/
  `accountability`/`next_action`/`cctv` with their real tags
  (VERIFIED/MEASURED/RELAYED/INSTINCT/OPEN).
- **Read `next_action.dual_state` first** (nested inside `next_action` in the
  tool's JSON — not top-level, and not the same as `state`/`hazard`):
  `next_action.dual_state.current_local_state` (RED/YELLOW/GREEN/UNKNOWN) and
  `next_action.dual_state.forward_hazard` (ACTIVE/NONE/UNKNOWN) are the
  headline colour verdict already classified by FloodConnect's fixed rules —
  never derive your own colour from `state`/`hazard` (those are the raw
  evidence, and `state.tag`/`hazard.tag` are epistemic confidence tags, not a
  colour).
- **MUST NOT:** answer from memory without calling the tool; invent a value,
  tag, camera, station name, or URL not verbatim in the tool's JSON (copy
  station names character-for-character from `state.evidence[].station` —
  never a paraphrase or a plausible-sounding Thai station name); relay
  `UNKNOWN`/`OPEN` as normal or safe; drop the "not an official notice" line;
  pass a `refresh` argument (the current tool takes `offline`/`verbose`, not
  `refresh`); drop any hotline number from `who_to_call`/the fixed list when
  relaying it — relay the full list, never a shortened subset.
- **First step:** call the tool — never guess the answer first.
- **Expected output:** the tool's real fields, each with its real tag, plus
  the data's age.

## T3 — coding/terminal agent with a shell

- **CAN:** install from a fresh clone; run `floodconnect answer --at <area>
  [--offline] --json`, `floodconnect forecast`, `floodconnect connectors
  [--live]`; run the test suite; read real stdout and relay it exactly. You
  HAVE a shell — use it; do not fall back to a T1-style "I cannot compute
  this" answer when a command is available to you (see `llms.txt`'s "If you
  cannot run code" section header, which explicitly tells a shell-capable
  reader to skip it).
- **Read `next_action.dual_state` first** in the JSON (nested inside
  `next_action`, not top-level): `next_action.dual_state.current_local_state`
  (RED/YELLOW/GREEN/UNKNOWN) and `next_action.dual_state.forward_hazard`
  (ACTIVE/NONE/UNKNOWN) are the one classification that matters — report
  these exact values, not a paraphrase of `state.tag`/`hazard.tag` (those
  are epistemic confidence tags on the evidence, not the colour verdict).
- **MUST NOT:** use the wrong command or none at all; invent a number, a
  station name (copy `state.evidence[].station` verbatim, never a
  plausible-sounding substitute), or a test-pass count not actually produced
  by a real run; treat a CCTV entry as a decision input instead of a
  look-yourself VISUAL-CHECK; pass `--refresh` expecting it to do anything
  (it is a deprecated no-op — refresh is already the default; `--offline` is
  the real opt-out); claim you lack live-data capability when you have a
  working shell and the CLI is installed.
- **First step:** read `README.md` / `AI.md` / `llms.txt` to find the right
  command, then actually run it before answering.
- **Expected output:** the command's real stdout, relayed faithfully, with
  `dual_state` reported exactly as returned, tags and freshness intact.

## T4 — co-work / computer-use agent

- **CAN:** everything T3 can, plus prepare a household checklist/file from
  the real answer, and set a reminder **on the user's own device/calendar**
  to re-run `floodconnect answer` later *(a dedicated `floodconnect watch`
  command is planned, not shipped in v0.1.x — use a plain re-run reminder
  today)*.
- **MUST NOT:** set up any server-side or shared schedule; invent a feature's
  output before it ships; treat a prepared checklist as an official notice.
- **First step:** same as T3, then ask the user where they want the local
  reminder set.
- **Expected output:** the same honest answer as T3, plus a file/reminder
  that lives only on the user's own machine.

## T5 — developer / API integrator

- **CAN:** call the CLI or MCP tool from code; read `system_capabilities.json`
  for the current feature list and token ceiling; build on today's `answer`
  JSON shape.
- **MUST NOT:** call a hosted live-data endpoint (there is none — the only
  public URL is the static, no-data landing page); hard-code a result
  instead of calling the tool each time; claim a planned feature (detail
  levels L2/L3, the one-decision Jev-style envelope, `floodconnect watch`)
  already works.
- **First step:** read `system_capabilities.json`, then call the CLI/MCP the
  same way T3 does.
- **Expected output:** structured JSON, programmatically consumed, with the
  same tags and freshness fields as every other tier sees.

## What's live today vs. planned

| Feature | Status |
|---|---|
| `floodconnect answer` (CLI + MCP), refresh-by-default, `--offline`, tags, freshness gate | **shipped** |
| CCTV nearest-camera (VISUAL-CHECK) | **shipped** |
| `system_capabilities.json`, `llms.txt`, `docs/EVIDENCE.md` | **shipped** |
| Detail levels L2/L3 (today's single combined answer is closer to a planned L2 shape) | planned (v0.2+) |
| `floodconnect watch` (local reminders) | planned |
| One-decision envelope (typed Choice/Score/gate contract, "Jev-style") | planned (v0.2+) |
| Water-debt decision model as the centre | planned (v0.2+) — see `ARCHITECTURE.md` §9 |

See `ARCHITECTURE.md` and `ROADMAP.md` for what each planned item actually requires
before it ships (including Toledo registration — see `docs/EQUATIONS_FOR_AI.md`).
