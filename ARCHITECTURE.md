# ARCHITECTURE.md — how FloodConnect is built, and why

> Read order for a new AI/agent: `README.md` → `llms.txt` (if present) → **this file**
> → `ROADMAP.md` → `AGENTS.md` → the RKG (`site/inputs/meta/floodconnect_repo_kg.yaml`).
> This file explains *why the system is shaped this way*; `AGENTS.md`/`AI_ENTRYPOINT.md`
> give the exact commands and write-safety rules; the RKG is the machine-checked source
> of truth for which file owns which construct. When this file and the RKG disagree,
> the RKG wins — say so and fix this file, don't silently pick a side.

## 0. One sentence

FloodConnect assembles Thailand's scattered government/private flood data into **one
typed, source-tagged readout**, running entirely on the installer's own machine, with
one designed decision core — the **Water-Debt system** — at the centre; everything else
in this document is an input to that core or a protocol around it.

## 1. The centre: the Water-Debt Core

**Status: design target, not implemented in v0.1.x — see §9.** The sections below
describe the intended shape; today's `kb.py answer` does not compute a water-debt
value at all (`water_balance.py` still returns `REFUSED`/`MISSING_INPUT`).

Everything below reads from, or feeds, one object: **water debt**
`D = inflow − drainable`, computed per node (a community/sub-basin/canal point), with an
explicit interval when an input is missing rather than a refusal (see §7). This is a
founder-level architectural decision, not an implementation detail: *"แกนคือสมการที่เรา
พัฒนา เอาโมเดลเราเป็นศูนย์กลาง"* — the model is the centre; government and private data
are **inputs that feed it**, never the product itself.

The equation set is Toledo-registered (never ad-hoc). Registration status, re-verify
before citing any of these as settled (do not restate from memory — re-check
`toledo/registry/CANONICAL.json` and `toledo/registry/proposals/*.json` directly):

| Code | What it computes | Status (re-verify) |
|---|---|---|
| PROP-FLOOD-01 | Δk — rise rate between two readings | On `toledo` `main` (PR #59, merged), as a **proposal** object (`registry/proposals/flood_readout_trend.json`, `status: "unverified"`) — placeholder code `weld/M.??.v1`, not yet promoted to `CANONICAL.json` |
| PROP-FLOOD-02 | T_k — time to the official threshold | Same PR #59 / same file, same placeholder-code and unverified status as PROP-FLOOD-01 |
| PROP-FLOOD-03 | Water balance / water debt `D = inflow − drainable`, the spine every other node plugs into | `toledo` PR #60, **OPEN**, not merged |
| PROP-FLOOD-04 | Edge direction (which way a canal/pipe actually flows) | `toledo` PR #61, **OPEN**, not merged |
| PROP-FLOOD-05a/b | Control-structure burden ledger (gates/pumps, who/what is carrying load) | `toledo` PR #62, **OPEN**, not merged |
| PROP-FLOOD-06 | Outlet-coping tier ladder L0–L5 | `toledo` PR #63, **OPEN**, not merged |
| PROP-FLOOD-07 | Flow-state classifier F1–F6 | Same PR #63 as 06, **OPEN**, not merged |
| PROP-FLOOD-08 | Per-window design-depth load ratio / forecast | Drafted on Toledo branch `proposals/flood-forecast-set` (commit history includes "proposal: PROP-FLOOD-08…"), **not on `main`**, not merged, not usable yet |
| PROP-FLOOD-09 | Edge booking delay (declared integer delay, stacked inbound debt) | Same branch as 08, **not on `main`**, draft |
| PROP-FLOOD-10 / 10a | Zoom forecast levels 0–3 + interval enclosure | Same branch as 08, **not on `main`**, draft |

**Toledo-first applies to this repo exactly as it does across this project's equation
work**: an
equation not registered (or still an open, unmerged proposal) may be used in an
*experiment* (tagged as such, never presented as production truth) but never cited as
settled, never promoted into `state`/`hazard` in the shipped `answer`/`forecast` CLI
output until it reaches at least registered-proposal status, and the code implementing
it (`water_balance.py` for 03, `canal_graph.py` for 04, `burden_ledger.py` for 05a/b,
`hierarchical_flood_zoom.py` for 10, `raw_stage_forecast.py` as a *standalone,
uncalled* persistence experiment, not 08/09/10) lives today in the **proposal /
experiment branch** of this repo (see `AI_ENTRYPOINT.md` §3 "Experimental forecast"),
not the operational truth layer. **In v0.1.x, none of PROP-FLOOD-03..10 decide any
field in the shipped `answer`/`forecast` output** — see the implemented/planned table
in §9.

**DSVA** (Disaster System Viability Architecture, `docs/research/DSVA_*.md`) is the
formal theory of which actions a decision is actually licensed to take given only the
evidence available at decision time. It sits downstream of the water-debt reading, not
in place of it: DSVA answers "is this action within envelope", not "what is the water
level". Strongest status it can ever emit is `LICENSED_WITHIN_ENVELOPE` — never `SAFE`,
never universally correct. See `docs/research/DSVA_DECISION_MODEL.md` and the
DSVA red-team protocol's (DSVA architecture doc) non-equivalence list (`Observation != Forecast != Warning !=
Instruction != Action`, `UNKNOWN != SAFE`, `Confidence != DecisionLicense`, …) for the
full discipline; it is not restated here.

## 2. Inputs — tagged by source, never the product

Every reading that feeds the Water-Debt Core carries a source tag through to the
output; the core does not care *which* agency a number came from, only its tag and
freshness:

- **Government** — BMA (canal/gate/pump telemetry, DDS bulletins), Royal Irrigation
  Department (dam inflow/outflow, hourly stations), HII/สสน. (water-level/CCTV
  catalog), the Royal Thai Navy Hydrographic Department (tide), GISTDA (flood extent),
  Thai Meteorological Department. See `sources/registry.yaml` for the live, wired list
  and `sources/api_census.yaml` for the full 160+-endpoint survey (connected /
  catalog-only / needs-key / unreachable / host-blocked).
- **Private** — private pumps/gates, estates, utilities, the private-sector relief
  network. **Planned (ROADMAP V6)** as a distinct input class in the registry — not
  wired in `sources/registry.yaml` in v0.1.x. Per founder ruling 2026-10-04:
  "อ่านร่วมกับข้อมูลจากรัฐและเอกชน" — government AND private data are read
  *together* into the per-node debt ledger, each still individually tagged, never
  merged into one untagged number, once this lands.
- **Crowd** — Traffy Fondue, Floodboard, community reports. **Planned** (Traffy Fondue:
  ROADMAP backlog; Floodboard: ROADMAP v0.2.4/V2) — neither is wired in this tree
  today; `community_report` already exists as a tag kind for a private individual's
  own account. Once wired, tagged `RELAYED`/crowd, never alone deciding a colour/tier
  (see `AGENTS.md`'s public-wording law and the `floodconnect-agent` skill's
  "contradictions, both sides" rule).
- **Model** — rain-per-model forecasts (Open-Meteo/ECMWF/GFS and siblings), reported
  per model, never averaged (`F4` in `README.md`).

No input is ever treated as the product. A browsing AI or a human reader should never
conclude "FloodConnect is a BMA mirror" or "FloodConnect is a weather API wrapper" —
every one of the above is an *input* the Water-Debt Core reads; the product is the
typed decision the core (and, downstream, DSVA) produces from them.

## 3. The D1–D8 decision protocol

Every answer runs through one fixed staged pipeline, reduced to a single typed decision
(§5). This is a protocol **design** — see the implemented-vs-planned table (§9) for
what actually runs this today versus what the current `kb.py answer` path approximates
with simpler logic.

```text
D1  locate        --at -> node/sub-basin + which rung of the source fallback ladder
                   (own station -> nearest station on the same network within a
                   declared radius -> basin/region value -> model value -> declared
                   interval; every value keeps its source level + distance)
D2  freshness gate fresh / stale / missing, per input, against that source's own
                   cadence -- a stale reading never decides a colour (see §7)
D3  drivers        rain / upstream / tide / drainage -> one typed state each
D4  water debt     PROP-FLOOD-03; an interval, not a refusal, when inputs are partial
D5  coping state   L0-L5 tier (PROP-FLOOD-06) / F1-F6 flow state (PROP-FLOOD-07) +
                   rise rate (01) + time-to-threshold (02)
D6  official context  an agency declaration (e.g. ปภ.) or alert always outranks our
                   own reading -> forces ESCALATE / "follow official" early
D7  Jev proposal   Choice (+ p) / Score / Noul checks (S4) -- see §5
D8  DSVA gate      ADMIT | HOLD | REJECT | ESCALATE = the one decision + confidence
```

**Speed rules** (why this shape, not an LLM-in-the-loop pipeline): every stage is a
pure function over typed inputs; `BOT` (unresolved) propagates and short-circuits to
`HOLD`; an official declaration short-circuits to early `ESCALATE`; each stage is
cached per input-hash; only the sources relevant to D1's located node/radius are
fetched, in parallel. No LLM sits in this loop — it is typed functions over typed data,
so the whole chain stays cheap enough for a home AI to call on every question.

**"Audition" reduction**: every Choice option is a candidate; each stage from D2
onward is an elimination round (stale evidence, debt too high for a "watch" option, an
official declaration forcing "follow official", a DSVA refusal) that can cut a
candidate or downgrade it to a safer, lower-commitment option; survivors are scored,
the winner is the one decision, and its confidence comes from its margin over the
runner-up plus evidence strength. If nothing survives, the result is `HOLD` (`BOT`),
never a forced guess. Elimination reasons are kept in the L2/L3 trace (§6), never in
L1.

## 4. The Semantic Decision Holarchy — hierarchy, not a flat answer

The D1–D8 protocol runs at every spatial level — basin → sub-basin → province →
district → community/node → household — not once. Each level runs its own D1–D8 on its
own scale:

- **Parent → child (down):** upstream debt/dam-release state, official declarations,
  tide, flow as typed *constraints* on the child level.
- **Child → parent (up):** local gauges, crowd reports, CCTV flow as typed *evidence*.
- **The single returned answer** is the reduced decision at the level asked (default:
  household/node), with **confidence = the weakest link across the path** — a `BOT`
  anywhere on the chain from household up to basin forces `HOLD` at the household
  level too, even if the household's own local reading looks fine.

This reuses existing constructs rather than inventing a parallel ontology:
`hierarchical_flood_zoom.py` and the Toledo `PROP-FLOOD-10` zoom-forecast levels for the
spatial zoom machinery, and the typology/community DAG (`community_dag.py`,
`COMMUNITY_DAG`/`TDLC`/`LVCN` in the RKG) for the existing node graph. Each level's
computation is cached so many households sharing a district/basin don't re-derive it.

## 5. The Jev one-decision contract

Every FloodConnect output — CLI `answer`, MCP tool call, a future `watch` check, a
forecast summary — reduces to **one typed decision object**, not prose, not several
separate verdicts:

```text
Choice   : a fixed, declared option set in everyday Thai (เฝ้าดู / เตรียมของ /
           ย้ายของขึ้นที่สูง / ไปจุดปลอดภัย / ทำตามประกาศทางการ), with a pick + a
           probability p. A Choice is a proposal, never an authorization on its own.
Score    : a level (ปกติ / เฝ้าระวัง / ระบายไม่ทัน / วิกฤต), indexed from the water-debt
           value/interval + the L-tier.
Noul     : one or more checks, each an S4 value -- POS / NEG / ZERO / BOT, where
           BOT = unresolved and is NOT the same as ZERO (BOT maps to HOLD at the gate;
           conflating "we don't know" with "the answer is no" is the single most
           important distinction in this contract).
gate     : the DSVA licence result -- ADMIT | HOLD | REJECT | ESCALATE. A Choice is
           never itself an authorization; only the gate's output is.
why      : the Toledo codes + debt value/interval + input tags that produced the above.
```

Output words are short typed codes/enums + numbers, in everyday Thai where a
human-facing gloss is unavoidable (e.g. "น้ำกำลังขึ้น", "ระบายไม่ทัน", "ยังไม่รู้") — never
long locked English/Thai prose, and never a pre-translated sentence baked into the
system (per founder ruling: "เอาเข้าโมเดลแล้วตอบแบบ jev... ที่เหลือให้เอไอบ้านเค้าไปแปลกันเอง"
— the caller's own home AI does the natural-language translation into whatever
language the user speaks; FloodConnect's job stops at the typed decision).

**This contract is a v0.2+ design target.** The *shape* described here (a one-decision
envelope wrapping Choice/Score/Noul/gate) is not what `kb.py answer` returns in v0.1.x
today — see §9.

## 6. Detail levels

One decision (§5) is the core at **every** level; levels only add the evidence around
that same single decision, never a second decision:

| Level | Token ceiling (cl100k) | Adds |
|---|---|---|
| L1 (brief, default for a home AI) | ≤ 5,000 | The one Jev decision + its key "why" |
| L2 (standard) | ≤ 10,000 | + the driver block, evidence rows, accountability |
| L3 (deep) | ≤ 100,000 | + full evidence, per-model forecasts, the per-node water-debt ledger, contradictions shown both-sides, the Toledo derivation trail |

v0.1.x ships one combined answer (no `--level` flag) under the 10,000-token ceiling
(enforced by `tests/test_token_budget.py`, 9,500 real-world threshold) — this is closer
to today's L2 than to a true tiered L1/L2/L3; the explicit `--level` flag and the L1
one-sentence-first shape are v0.2 work (§9, ROADMAP.md).

## 7. Partial-data handling — never a hard refusal

A missing input never blocks a decision outright. Each driver resolves through a
fallback chain (own station → nearest same-network station within a declared radius →
basin/region value → model value → a declared interval), and every value keeps its
source level and distance. Where the water balance itself is missing a required input,
the *design* is to widen the result into an interval (bounds + source tag) rather than
refusing — the current `water_balance.py` path, pending PROP-FLOOD-03's merge (§1),
still reports `REFUSED`/`MISSING_INPUT` for Sammakorn; replacing that with an interval
is tracked in ROADMAP.md. An action is only chosen when it stays correct across the
plausible range of the missing inputs (worst case first); otherwise the result
downgrades to a safer, lower-commitment option, and only falls to `HOLD`/`Noul` when
even that cannot be justified.

## 8. Operating constraints (apply everywhere above)

- **No hosted data.** Nothing is pre-computed and served from our infrastructure. A
  fresh clone ships no flood reading. `floodconnect answer` on a fresh clone refreshes
  by default (fetches live from the wired sources on the caller's own network) — it
  returns `UNKNOWN` with a `next_action` only if that refresh finds nothing fresh, or
  the caller passes `--offline`/has no network; it never fabricates a reading either
  way.
- **Caller-side only.** Every network call `answer` makes (refresh is the default;
  `--offline` skips it) runs on the installer's own machine, network and API keys (see
  `sources/registry.yaml`'s `key_env` names) — never ours, never routed through any
  server we operate.
- **No scheduler on our side.** No cron, no periodic job calls any live source from
  infrastructure we run. `floodconnect watch`/a threshold check (planned, ROADMAP.md
  V10) is designed to be scheduled by the *caller's own* OS/assistant, never by us.
- **"Neural" is a metaphor only.** Some design documents describe FloodConnect as a
  "decision circuit" / "decision brain" (nodes = typed gates, wires = typed signals).
  There is **no trained model, no learned weight, no black-box inference** anywhere in
  this pipeline. Every gate and threshold **must be** either a registered Toledo
  equation or an official regulatory threshold — this is the target, not yet fully
  true today: the 3 km nearest-station radius and the freshness-cutoff windows are
  engineering defaults, not registered equations or official thresholds, and are
  tracked as a gap to close rather than restated here as already met. Any future
  learned/calibrated parameter must be registered at the `fit_calibrated` tier and
  backtested before use — it does not get a free pass because the system is described
  with a neural metaphor.
- **UNKNOWN != SAFE**, everywhere, always (see the `floodconnect-agent` skill's
  mandatory reasoning rules for the full list this architecture inherits unchanged).

## 9. Implemented in v0.1.x vs. planned

| Capability | v0.1.x | Planned |
|---|---|---|
| `answer`/`forecast` CLI + MCP, 4-block output (state/hazard/accountability/next_action) | **Implemented** | — |
| CCTV nearest-camera block (`VISUAL-CHECK`, never decides state) | **Implemented** | — |
| Freshness gate (one gate per reading, stale never decides a colour) | **Implemented** | extend to every forecast-model row (known limit, §ROADMAP) |
| Token ceiling ≤10,000 (one combined answer) | **Implemented** | tiered `--level 1\|2\|3` (§6) |
| PROP-FLOOD-01/02 (rise rate / time-to-threshold) | Registered as unverified proposals on Toledo `main`, placeholder code | promote off placeholder code; wire into the answer path |
| PROP-FLOOD-03..07 (water balance / edge direction / burden ledger / coping tier / flow state) | Open Toledo PRs, **not usable** per Toledo-first | merge PRs, then wire into `answer` (ROADMAP V8/V6) |
| PROP-FLOOD-08/09/10 (forecast load ratio / edge booking / zoom forecast) | Draft branch, **not on Toledo `main`** | finish review, register, then wire (ROADMAP V8) |
| Water-debt interval on partial data (§7) | Not implemented — `water_balance.py` still `REFUSED`/`MISSING_INPUT` for Sammakorn | V6 (ROADMAP) |
| D1–D8 decision protocol (§3) as an explicit staged pipeline | Not implemented as such — today's `kb.py answer` approximates D1-D3/D6-D7 informally, without the formal stage boundaries, caching, or short-circuit rules described here | v0.2.0 skeleton (ROADMAP) |
| Semantic Decision Holarchy (§4), multi-level hierarchy | Not implemented — single-level answer only | 2-level (area+node) skeleton after V8/V4 (ROADMAP) |
| Jev one-decision envelope (Choice/Score/Noul/gate) (§5) | Not implemented — current output is 4 descriptive blocks, not a Choice/Score/Noul/gate envelope | v0.2.0 wraps the current answer into this envelope; V6/V7 fill it from real water debt + DSVA (ROADMAP) |
| DSVA executable decision model (`dsva_decision.py`) | Implemented as a **standalone, research-track** finite projection (v0.11) — exercised by its own test suite, not yet called from `kb.py answer`/`forecast` | wire into the D8 gate once the Jev envelope exists (ROADMAP V7) |
| `watch`/threshold check (V10), local viewer (V11) | Not implemented | v0.2.3 / v0.3 (ROADMAP) |

**Do not cite any "planned" row above as a current capability** — if asked what
FloodConnect does *today*, answer from the "v0.1.x" column only, and mark anything else
`planned (v0.2+)` explicitly, per the no-overclaim rule this file itself is bound by.
