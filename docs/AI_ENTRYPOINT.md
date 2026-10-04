# AI Entry Point — Understand FloodConnect Fast

> **Writer agents:** Read `AGENTS.md` before this file. It defines claim-first ownership, branch/PR rules, and integration gates.

> **Start here if you are an AI/agent entering this repository for the first time.**
>
> Do **not** scan the repo blindly and do **not** create a new ontology until you have checked
> the canonical Repo Knowledge Graph (RKG).

**Only answering one state/forecast/accountability/route question, not writing code?**
`AI.md` (repo root) is a single compute call (`kb.py answer --at <area> --json`) that
covers exactly that case in a fraction of this file's token budget. Read on here only if
`AI.md` does not cover what you need, or if you are about to write.

The MCP server code (`tools/mcp/floodconnect_mcp.py`), the agent skill
(`skills/floodconnect/SKILL.md`), and the static `api/v1/*` export tool
(`tools/api/export_api.py`) are all tracked source files in this repo — but the
export tool's *output* (`site/dist/api/v1/**`) is gitignored and not tracked; it
exists only after you run `site/build_data.py` + `tools/api/export_api.py` on your
own machine. Nothing here is a hosted endpoint. `AI.md` names all three routes and
is the one place the reasoning rules are stated; `docs/AI_INTERFACE.md` is the
fuller MCP/export technical spec.

## 0A. If you will write

Before semantic changes:

1. read `AGENTS.md`;
2. check active claims with `python3 agent_claims.py --list`;
3. if your canonical node is unclaimed, submit/merge a claim-only PR;
4. start implementation from the updated `main`;
5. merge only after RKG validation, claim validation, and full regression.

Ownership is by canonical RKG node, not file path.

## 0. Canonical meta graph

Read first:

`site/inputs/meta/floodconnect_repo_kg.yaml`

It tells you:

- what the major systems/constructs are;
- which file is source-of-truth for each construct;
- which models depend on which graphs/data;
- what is live vs static vs policy vs proposal;
- which relationships are explicitly forbidden;
- which files to read for a given question.

Validator/exporter:

`repo_knowledge_graph.py`

## 1. Six rules you must preserve

1. **UNKNOWN != SAFE**
2. **Topology != forecast**
3. **Observation != forecast != warning != instruction != action**
4. **Movement graph != support/lifeline graph**
5. **Tool/facility type never overrides route/site hard safety**
6. **Extend canonical nodes/artifacts; do not create a parallel ontology**

## 2. Canonical identity rule

Government/agency identities live in:

`site/inputs/governance/thailand_water_governance_reference.json#verified_anchors`

Any role system must reference those IDs.

Example:

`tmd` is the canonical actor node.

`METEOROLOGICAL_OBSERVER_FORECASTER` is a role assigned to `tmd` by:

`site/inputs/governance/flood_warning_actor_typology.yaml`

Do **not** create a second TMD actor object inside another typology.

## 3. Fast routing by question

### “What is the disaster-system theory / DSVA / synthesis-first architecture?”

Read first:

- `docs/research/DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md`
- then the RKG route `question_routes.disaster_system_theory_or_dsva`

The manuscript is the canonical **PROPOSAL / THEORY_SYNTHESIS** expression of DSVA. v0.6
preserves v0.1 as the open-loop anchor, v0.2 as the adaptive-policy anchor, v0.3 as the
Toledo-welded anchor, v0.4 as repository-first synthesis, and v0.5 as the first-order
information-contract bridge. A second-order red-team then showed that all first-order closures can
PASS while an action is still wrong. v0.6 therefore adds a declared applicability envelope plus
applicability/model-invalidation, dependency, realizability, execution-time, protected-requirement,
persistent-recovery and independent-verification obligations. Existing FloodConnect canonical
subsystems remain authoritative; external theories enter only as narrow operators/solvers/contracts
inside DSVA/Toledo.

Read in this order:

- `docs/research/DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md`
- `docs/research/DSVA_TOLEDO_WELD.md`
- `docs/research/DSVA_FLOODCONNECT_CANONICAL_SYNTHESIS.md`
- `docs/research/DSVA_INFORMATION_CONTRACT_BRIDGE.md`
- `experiments/2026-10-01-dsva-v05-second-order-redteam.md`
- `docs/research/DSVA_SECOND_ORDER_LICENSE.md`
- then the RKG-listed canonical layers needed by the question.

Do **not** recreate constructs that already exist in:
- `COMMUNITY_DAG`
- `TDLC / LCF / LVCN`
- `ORCG`
- `ENV_DEGRADATION`
- `SOCL`
- `WARNING_TYPOLOGY`
- `UNIFIED_CRISIS`

The pre-existing `experiments/2025-11-hat-yai-real-data-redteam.md` is a canonical stress-test
input to v0.4, not a newly discovered DSVA result.

Formal spine:

`S_n -> q_DSVA -> first-order contracts -> information state -> possible futures -> second-order applicability/dependency/realizability/execution/requirement/verification license -> {Pi_H^EB, Pi_H^REC} -> verified scope-preserving readout -> leased action/runtime feedback`

Load-bearing rules:
- T-CAN-006: dynamics/readout/invariant bridge obligations;
- T-CAN-007: finite-horizon reader equivalence / no-early-collapse;
- T-CAN-009: later evidence may extend but not rewrite earlier decision-time history;
- if a required first-order closure or second-order applicability/dependency/realizability/execution/requirement/verification obligation is absent, use `CONDITIONAL/UNKNOWN/HOLD/LOCAL-PARTIAL` as appropriate;
- `not invalidated != true model`; every strong action claim is relative to a declared applicability envelope;
- a readout is not execution-licensed if its action lease expires before effect or if the executable result is unverified;
- Toledo-existing equations and DSVA-proposal equations must never be conflated.

Read the Thailand/Bangkok/Sammakorn sections and the finite 28 Sep Sammakorn witness as the first
empirical instantiation. External literatures enter only after the DSVA universe is constructed,
and only through declared bridge status (WELDED / PARTIAL / HOLD / RIVAL) plus role mapping
(special case / solver / operator / parameterization / boundary / rival). The general-theory
claim is not a production forecast, warning, or operational command; live actions remain gated by
fresh evidence, validated models and reader-specific constraints.


### “How do I run the DSVA disaster decision model?”

Read:

- `docs/research/DSVA_DECISION_MODEL.md`
- `docs/research/DSVA_FINITE_OBSTRUCTION_KERNEL.md`
- `docs/research/DSVA_AUDITED_MEANING_CLOSURE.md`
- `docs/research/DSVA_THEORY_CONTRACT_PROJECTION.md`
- `docs/research/DSVA_FINITE_REALIZABILITY_PROJECTION.md`
- `dsva_decision.py`
- `site/inputs/decision/dsva_decision_schema.json`
- `examples/dsva_decision_minimal.json`
- `tests/test_dsva_decision.py`
- `tests/test_dsva_decision_v08_redteam.py`
- `tests/test_dsva_decision_v09_redteam.py`
- `tests/test_dsva_decision_v010_theory_contracts.py`
- `tests/test_dsva_decision_v011_realizability.py`

Run:

```bash
python3 dsva_decision.py examples/dsva_decision_minimal.json
python3 -m pytest -q tests/test_dsva_decision.py tests/test_dsva_decision_v08_redteam.py tests/test_dsva_decision_v09_redteam.py tests/test_dsva_decision_v010_theory_contracts.py tests/test_dsva_decision_v011_realizability.py
```

This is an executable finite projection of DSVA v0.11, not a hazard forecaster. v0.10 additionally projects finite applicability behavior overlap, dependency lineage/resource/compound-hazard checks, future-observation response totality, realized-actuation/runtime contracts, complete protected-requirement ledger scope, and verification bound cryptographically to the exact finite spec/input snapshot. v0.11 now checks a supplied finite actor-local adaptive-policy DAG and persistent recovery over the retained grid. It still does not synthesize an optimal/unbounded policy, prove continuous inter-sample recovery, or establish that upstream world/lineage/checker declarations are complete in reality. It consumes declared worlds/disturbances/traces and returns a scoped DSVA action-license status. v0.9 additionally requires type-stable retained values, explicit per-subject requirement bindings for multi-subject claims, complete closure-audit witness records, nonnegative action-effect time, and consistency between explicit and typed-reader proposal channels. v0.8 uses an IDM-informed finite retained obstruction kernel: non-empty finite axes, exact rational horizon/lease/resolution checks, fail-closed malformed input, protected-population coverage, retained-state reader quotients, reusable trace classes, and a cost ledger. A Jev/LLM/rule/human typed reader may propose an action, but confidence never overrides failed closure, actor-local information, protected requirement, trace-safety, verification, or lease gates.

### “What is happening now?”

Read:

1. `sources/registry.yaml`
2. `docs/DATA_SYSTEM.md`
3. `collect.py / parsers.py / store.py / readout.py`
4. relevant live source module such as `live_water_level.py`

Current-state claims require fresh operational evidence.

### “Where does water/canal connect?”

Read:

- Thailand rivers: `build_river_kg.py`
- Bangkok canals: `build_bangkok_canals.py`
- Sammakorn local hydraulics:
  `site/inputs/canals/sammakorn_pond_canal_dag.yaml`

Never convert connectivity into a forecast without separate evidence.

### “Can the community stay / what support layer is needed?”

Read:

- `site/inputs/community/sustainment_policy.yaml`
- `shelter_decision.py`
- `docs/SHELTER_DECISION_AND_COMMUNITY_SUSTAINMENT.md`
- `docs/THAI_DISTRIBUTED_LIFELINE_CONVERGENCE.md`

Key construct: **LVCN**.

### “Can help/supplies actually reach them?”

Read:

- `convergence_feasibility.py` — LCF
- `convergence_board.py` — LCB
- `site/inputs/community/operational_tools.yaml` — resources/capabilities

Core distinction:

`resources exist != resources are deliverable in time`

### “Shelter / dry point / public building?”

Read:

- `shelter_operation_ladder.py`
- `docs/SHELTER_OPERATION_CAPABILITY_LADDER.md`
- `public_shelter_seed.py`
- `site/inputs/community/public_shelter_seeds.yaml`

Rule zero:

`NO verified fresh dry operating footprint -> NO shelter-operation level`

### “Which vehicle/boat/tool matters?”

Read:

- `site/inputs/community/operational_tools.yaml`
- `operational_resources.py`
- `docs/OPERATIONAL_RESOURCE_CAPABILITY_GRAPH.md`

Tool nodes add capabilities to nodes/edges only after deployment evidence is verified.

### “Pets / animals / livestock?”

Read:

- `human_animal_household.py`
- `docs/HUMAN_ANIMAL_HOUSEHOLD_UNIT.md`

Animal sustainment, movement readiness and destination compatibility are separate.

### “The place is safe now, but will it degrade?”

Read:

- `environmental_degradation.py`
- `docs/ENVIRONMENTAL_DEGRADATION_CLOCKS.md`

No universal “age of floodwater” threshold exists.

### “Experimental forecast / Toledo / prospective test?”

Read:

- `water_balance.py` — PROP-FLOOD-03
- `canal_graph.py` — PROP-FLOOD-04
- `burden_ledger.py` — PROP-FLOOD-05
- `hierarchical_flood_zoom.py`
- `raw_stage_forecast.py`
- `experiments/`

These belong to the **proposal / experiment branch**, not the live operational truth layer.

Important:
- missing Toledo inputs must remain refused/OPEN;
- raw-stage persistence is not a hydraulic model;
- a historical/prospective experiment is not a production forecast rule;
- the S0–S5 state machine in the early 7-day Sammakorn backtest is historical and has been
  superseded by `Unified Crisis State`.

### “Community/social reports?”

Read:

- `social_listening.py`
- `docs/METHOD_social_listening.md`
- `sources/registry.yaml`

Community/media signals are place+state+time evidence. They do not become official warnings merely
because they agree with an official source.

### “Who is responsible / who warns?”

Read identity first:

`site/inputs/governance/thailand_water_governance_reference.json`

Then role overlay:

`site/inputs/governance/flood_warning_actor_typology.yaml`

Then current/live source provenance:

`sources/registry.yaml`

### “What is the combined decision state?”

Read:

- `unified_crisis_state.py`
- `site/inputs/community/sustainment_policy.yaml`

Unified vector:

[
Z_i(t,T)=(O,F,M,S,E,H,A,P)
]

## 4. Core graph of graphs

```text
                   GOVERNANCE canonical actors
                           |
                           v
                    WARNING TYPOLOGY
                           |
                           v
SOURCE REGISTRY -> LIVE DATA SYSTEM ----------------------+
       |                                                  |
       v                                                  v
 RIVER / CANAL KG -> LOCAL HYDRAULICS              UNIFIED CRISIS STATE
                           |                              ^
                           v                              |
                    COMMUNITY CONTEXT                     |
                                                          |
COMMUNITY MOVEMENT DAG ---> LVCN <--- LCF <--- TDLC ------+
          ^                  ^       ^
          |                  |       |
          |               SOCL <-----+---- ORCG/tool nodes
          |                  ^
          |                  |
          +------ HAHU       PSSS/public shelter seeds
                 |
ENVIRONMENTAL DEGRADATION --+
```

This diagram is orientation only. The machine-readable edge list in the RKG is canonical.

## 5. Source-of-truth map

| Topic | Canonical artifact |
|---|---|
| Repo architecture | `site/inputs/meta/floodconnect_repo_kg.yaml` |
| Live sources | `sources/registry.yaml` |
| Community policy | `site/inputs/community/sustainment_policy.yaml` |
| Movement topology | `site/inputs/community/self_help_dag.yaml` |
| Operational tools | `site/inputs/community/operational_tools.yaml` |
| Public shelter archetypes | `site/inputs/community/public_shelter_seeds.yaml` |
| Sammakorn hydraulic topology | `site/inputs/canals/sammakorn_pond_canal_dag.yaml` |
| Governance actor identity | `site/inputs/governance/thailand_water_governance_reference.json` |
| Warning roles | `site/inputs/governance/flood_warning_actor_typology.yaml` |
| Merge record (what/why per piece of work, and per-file merge detail) | internal local-only team record, not public-mirror-synced |

## 5AA. On-demand refresh — env vars and what gets fetched

No scheduler anywhere in this repo. Refresh is the DEFAULT as of 2026-10-03 (founder
ruling) -- `kb.py answer --at <area>` fetches wired sources on the CALLER's own
network/compute, then computes; `--offline` opts OUT (answer from the stored DB
only, no network this run); `--refresh` is kept as a no-op for old scripts. Never a
server we run, never our keys. A failed fetch (one source or all) falls back to
whatever is already stored, and every reading still passes the single freshness gate
before it can decide anything. Every `auth: api_key` source's exact environment variable
name is in its own `sources/registry.yaml` entry's `key_env` field; as of 2026-10-03
those are: `GISTDA_API_KEY` (+ optional `GISTDA_API_REFERER`),
`GOOGLE_FLOOD_HUB_API_KEY`, `CDSAPI_KEY`, `NASA_EARTHDATA_TOKEN`,
`OPENTOPOGRAPHY_API_KEY`, `GFW_API_KEY`, `RELIEFWEB_APPNAME`, `TMD_OPENDATA_API_KEY`.
None of these are read from anywhere but that env var -- never stored, never bundled,
never sent to us. A missing key reports `ok: False` with the env var name in `note`
(`status=unknown (not_fetched_missing_key)` under `collect.py`'s own CLI repr) --
never `SAFE`, never a guessed value, never plain `FAIL` (FAIL implies an attempt was
made; a missing-key source is never attempted).

`--refresh` does NOT fetch every registered source every time:
- `collect.DORMANT_NOT_IN_ALL` -- hosts that already returned a persistent 403.
- `collect.CATALOG_ONLY_NOT_IN_REFRESH` -- catalog/document-listing sources (e.g. the
  nationwide CCTV catalog, the Bangkok CKAN dataset catalog) that feed no `state`/
  `hazard`/`next_action` field; excluded unconditionally, `--all`/`--source` are
  unaffected.
- a key-gated source with no key present in this environment -- excluded when
  `verbose=False` (the default, both CLI `--verbose` and `build_answer(verbose=...)`)
  so a normal refresh doesn't attempt-and-report a guaranteed miss on every call;
  included when `verbose=True`.
- `collect.AREA_RELEVANT_SOURCES` -- a source whose own coverage is narrower than
  nationwide is skipped for an area outside that coverage.

## 5A. Operational vs proposal vs experiment

FloodConnect contains three branches that must not be collapsed:

```text
OPERATIONAL
  live sources -> evidence -> movement/support/shelter -> unified state

PROPOSAL
  Toledo water balance / declared canal chain / burden ledger / raw-stage helper

EXPERIMENT
  locked backtests / prospective tests / post-hoc audits
```

A proposal can be executable without being production truth. An experiment can be valuable evidence
without becoming the canonical current decision model.

## 6. Before adding a new construct

Ask in this order:

1. Is this already a node/edge/capability in the RKG?
2. Is there already a canonical registry or policy file for it?
3. Can this be an attribute/role overlay on an existing node?
4. Can this be a capability edge rather than a new node type?
5. Only if all four are no: add a new construct and update the RKG in the same commit.

## 7. Epistemic labels

When explaining an answer, distinguish:

- **live observation**
- **static topology**
- **policy/schema**
- **executable-model result**
- **role/governance context**
- **field evidence**
- **repo proposal**
- **inference**

Never silently promote one class into another.

## 8. Minimal AI boot path

For most tasks you only need:

```text
AI_ENTRYPOINT.md
        ↓
floodconnect_repo_kg.yaml
        ↓
question_routes[the user's question]
        ↓
2–5 canonical files
```

That is the intended way to understand FloodConnect quickly.
