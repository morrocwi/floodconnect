# AI Entry Point — Understand FloodConnect Fast

> **Writer agents:** Read `AGENTS.md` before this file. It defines claim-first ownership, branch/PR rules, and integration gates.

> **Start here if you are an AI/agent entering this repository for the first time.**
>
> Do **not** scan the repo blindly and do **not** create a new ontology until you have checked
> the canonical Repo Knowledge Graph (RKG).

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

The manuscript is the canonical **PROPOSAL / THEORY_SYNTHESIS** expression of DSVA. v0.3
preserves v0.1 as the explicit open-loop anchor and v0.2 as the adaptive-policy anchor, then
welds the disaster domain to Toledo's existing retained-state/stepper/domain-weld/reader-equivalence
grammar.

Read in this order:

- `docs/research/DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md`
- `docs/research/DSVA_TOLEDO_WELD.md`

Formal spine:

`S_n -> q_DSVA -> D_DSVA -> mathbb_B_t -> Pi_H^EB -> task-relative reader`

Load-bearing rules:
- T-CAN-006: dynamics/readout/invariant bridge obligations;
- T-CAN-007: finite-horizon reader equivalence / no-early-collapse;
- T-CAN-009: later evidence may extend but not rewrite earlier decision-time history;
- if a required adapter/weld is absent, use `HOLD`;
- Toledo-existing equations and DSVA-proposal equations must never be conflated.

Read the Thailand/Bangkok/Sammakorn sections and the finite 28 Sep Sammakorn witness as the first
empirical instantiation. External literatures enter only after the DSVA universe is constructed,
and only through declared bridge status (WELDED / PARTIAL / HOLD / RIVAL) plus role mapping
(special case / solver / operator / parameterization / boundary / rival). The general-theory
claim is not a production forecast, warning, or operational command; live actions remain gated by
fresh evidence, validated models and reader-specific constraints.

### “What is happening now?”

Read:

1. `sources/registry.yaml`
2. `docs/DATA_SYSTEM.md`
3. `collect.py / parsers.py / store.py / readout.py`
4. relevant live source module such as `live_water_level.py`

Current-state claims require fresh operational evidence.

### “Where does water/canal connect?”

Read:

- Thailand rivers: `build_kg.py`
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
