# Typology graph — build/validate, id scheme, edge vocabulary, standards crosswalk

Companion to `docs/FLOW_STALL_TYPOLOGY.md` §10 (that section is the narrative; this file
is the how-to-build/validate reference). Founder's task, verbatim: "ทำให้เชื่อมกันหละ" — turn
`FLOW_STALL_TYPOLOGY_EXTENSION_PROPOSAL_2026-09-28.md` into a real, connected graph in the
repo, not just a document. This file describes what got built.

## Build / validate

```
python3 -m tools.typology.build_graph      # writes output/typology_graph.json +
                                             # output/typology_sammakorn_subgraph.json
python3 -m tools.typology.validate          # linking-contract checks, exits non-zero
                                             # only on a schema error, never on an OPEN link
python3 -m pytest tests/test_typology_build_graph.py tests/test_typology_sammakorn_chain.py -q
```

Inputs (never modified by this build): `site/inputs/canals/east_chain.yaml` (water
topology), `typology/nodes/*.yaml` + `typology/edges/*.yaml` (hand-curated registry).
`data/observations.sqlite` and `raw/` are never touched.

## Id scheme (proposal §4a, reuse-first)

| kind | id pattern | source |
|---|---|---|
| water node | `WL.<CODE>` / `ST.<CODE>` | `site/inputs/canals/east_chain.yaml`'s own `canal_oldcode`, or `site/build_data.py`'s `SAMMAKORN_CHAIN_NODES` station codes (`WL.SMK.01`/`WL.BMA.02`) for the two east_chain nodes that declare `canal_oldcode: null` — both codings name the same real structure; the east_chain key is kept as an `east_chain_key_alias` attribute rather than dropped |
| `agency` | `AG_<SHORT_CODE>` | **reused verbatim** from `docs/knowledge/water_system_dag.mmd` wherever that id already exists — never a renamed twin. This build's own check found `AG_MEA` and `AG_ESTATE` already present; the proposal document's claim that they were missing is superseded (see `docs/knowledge/structural_issues_2026-09-28.yaml` ISSUE-PEOPLE-04/ISSUE-DECISION-02 for the corrected status) |
| `sensor` | `SENSOR.<water node code>` | new, this build |
| `resource` | `RES.<TYPE>.<OWNER>.<seq>` | new, this build (first resource-kind data this repo has ever held) |
| `warning_channel` | `WCH.<NAME_SLUG>` | new, this build |
| soi/zone | `SOI.<AREA>.<slug>` | matches `social_listening.py::_extract_soi()`'s own convention; this build declares only the two ids its Sammakorn worked example needs (`SOI.SAMMAKORN.17`/`18`), it does not re-run the live extractor |

## Edge vocabulary (closed — `tools/typology/validate.py::CLOSED_EDGE_VOCAB`)

`flows_to` (the base typology's `open_gravity`/`constrained_gravity`/`controlled`/
`backflow_risk`/`unknown` edge kinds, carried through with their own `design_direction`/
`control_structures` intact — this build does not collapse or discard that information),
`owned_by`, `operates`, `decides`, `warns`, `supplies`, `reports_to`. Allowed
`from_kind -> to_kind` pairs per edge kind are exactly the proposal's §2 table, amended by
the 2026-09-28 independent review: **`decides` targets `gate`/`pump` only, never `edge`**
(burden stays on the water edge's own `BURDENED`/`RELIEVED` attribute, PROP-FLOOD-05a/05b,
untouched — `decides` never becomes a second place burden is recorded).

## Standards crosswalk (all RELAYED — carried from the proposal document, not re-verified
against the live specs in this build; read the spec itself before citing any of this as
settled)

| our kind/field | standard | class/property | tag |
|---|---|---|---|
| `canal_reach`/`pond`/`river` (water node) | OGC HY_Features | `HY_WaterBody`/`HY_FlowPath` | RELAYED |
| `gate`/`pump` | OGC HY_Features | `HY_HydroNexus` | RELAYED |
| `sensor` + `Node.readings` | OGC SensorThings API v1.1 / ISO 19156 O&M | `Thing`/`Sensor`/`Observation`, `owned_by` ≈ `OM_Observation.procedure` (extension — SensorThings has no first-class owner field) | RELAYED |
| `warns` + `warning_channel` | OASIS CAP 1.2 | `alert/info` (sender/urgency/severity/certainty/area/`instruction`); `warning_channel` is our own extension — CAP models one alert, not a channel entity | RELAYED, extension |
| `agency` + `owned_by`/`operates`/`decides` | W3C PROV-O | `prov:Agent`, `actedOnBehalfOf`; `decides` ≈ `prov:Activity` `wasAssociatedWith` an Agent | RELAYED |
| `resource` + `supplies` | HXL / OCHA 3W | `#org`/`#sector`/`#loc`; 3W org×activity×location ≈ our agency–resource–zone triple | RELAYED |
| `BURDENED`/`RELIEVED` | *(no matching standard found)* | — | our own extension, Toledo `PROP-FLOOD-05a`/`05b`, already registered |

## Political/power layer: กพร. Joint KPI 29-body agency list (2026-09-28)

Founder ask: "สกัดไปเข้า typology node การเมืองด้วย" — fold in a new source: Lanner
(สื่อออนไลน์ภาคเหนือ) Facebook post, ~27 ก.ย. 2569, relaying กพร.'s Joint KPI FY2569-2570 for
"การบริหารจัดการและอนุรักษ์ฟื้นฟูน้ำทั้งระบบ" — 29 bodies (22 ส่วนราชการ + 2 องค์การมหาชน + 4
รัฐวิสาหกิจ + กทม.), host agency สทนช. **Tag RELAYED throughout, `verification_status: OPEN`
on every row** — media relaying an official กพร. framework, not read from the กพร. document
directly in this check.

New edge kind `part_of` (added to the closed vocabulary), allowed pairs
`agency -> ministry` and `ministry -> government` (`validate.py::rule_part_of_target_kind`
enforces this as a schema error, not an OPEN gap). `typology/nodes/ministries.yaml` adds
8 real กระทรวง nodes plus 3 non-ministry category nodes the source document itself uses
(องค์การมหาชน/รัฐวิสาหกิจ/กทม.'s special local-government status), distinguished by a
`group_type` attribute rather than silently calling all 11 "ministries". 18 brand-new
agency ids were needed (`typology/nodes/agencies_joint_kpi_2026-09-28.yaml`); 11 reused
existing ids (`AG_ONWR`/`AG_RID`/`AG_DDPM`/`AG_TMD`/`AG_DPT`/`AG_DOH`/`AG_MARINE`/
`AG_DWR`/`AG_GISTDA`/`AG_HII`/`AG_BMA_GOV`) — 7 of those 11 existed in
`water_system_dag.mmd` but had never been registered in this typology's own node
registry before; registered here for the first time, not duplicated. `AG_ONWR` carries
`joint_kpi_host: true`. Role statements the post itself makes (TMD forecasts/warns;
สทนช. policy+coordination; RID irrigation/dams/reservoirs/gates in irrigated areas; DWR
water sources outside irrigated areas; DDPM+province/local warning/evacuation/relief;
DPT+local bodies flood-defence/urban drainage; GISTDA/สสน. data+satellite support) are
captured as `role_th` node attributes only — **no `operates`/`decides` edge was invented**
from this source (the post states mandates, never a specific "agency X decides structure
Y" claim).

The post's closing structural question (who is the lead decision-maker in each phase; who
citizens contact) is recorded as `docs/knowledge/structural_issues_2026-09-28.yaml`
`ISSUE-LAW-03`, linked to the existing fragmentation card (`ISSUE-LAW-01`, 31 กรม/36
กฎหมาย, OECD 2018) — **the two counts (29 vs 31) are different frames and are
deliberately NOT reconciled**, both kept.

## TDRI extension: phase/capability/permanence/infrastructure/warning-quality (2026-09-28)

Founder ask: "สกัดเพื่อเสริม typology ที่ยังขาดอยู่ เอาแค่ส่วนสำคัญ" — 3 TDRI (สถาบันวิจัยเพื่อการพัฒนา
ประเทศไทย) public articles, tag RELAYED throughout (title+date+URL-stub cited per row in
`typology/nodes/tdri_extension_2026-09-28.yaml`/`tdri_overlay_2026-09-28.yaml`): "permanent-
disaster-management..." (ดร.นิพนธ์ พัวพงศกร, 9 ธ.ค. 2025), "anatomy-of-preventable-ruin..."
(ณัฐสิฏ รักษ์เกียรติวงศ์, 3 ธ.ค. 2025), "flooding-after-rain-bangkok-is..." (sponge-city, dated
30 มิ.ย. 2025 on the page but referencing 24-26 ก.ย. 2569 rain — **OPEN date inconsistency,
not resolved, both kept**).

- **Phase** — `phase` attribute (`normal|pre_event|incident|post_event`) on
  `warning_channel`/`resource` nodes and `decides`/`warns`/`supplies` edges. Every row in
  this repo is `incident` (the whole dataset is the active Sept 2026 flood) — tag
  `INSTINCT` (this check's own classification applying TDRI's vocabulary, not a TDRI
  per-row statement). Crosswalk: our 4 values ≈ UNDRR/Sendai's mitigation→preparedness→
  response→recovery phases (RELAYED, not independently verified against the Sendai text).
- **Capability (C3)** — 6-field checklist (`capability_operational_policy`,
  `_roles_responsibilities`, `_action_plan`, `_monitoring_loop`, `_logistics`,
  `_training`) on command-type agency nodes (`AG_ONWR`, `AG_DDPM`, `AG_BMA_GOV`,
  `AG_ESTATE`, `AG_REGCOM`). Every value is `null` (OPEN) — no source states a yes/no per
  agency. `validate.py::report_capability_gaps()` lists them, non-error.
- **Permanence + basin tier** — `permanence` (`permanent|ad_hoc`) + `level`
  (`national|ministry|basin|local`) on agency nodes. New: `AG_BASIN_CMT` (statutory,
  permanent, basin tier — fills "basin-level tier between ministry and local") and
  `AG_REGCOM` (ad-hoc regional committee, PM order 275/2569) — both reused from
  `water_system_dag.mmd`. One neutral structural line (per founder's rule, no criticism of
  named individuals): "อำนาจชักธงแดง/ประกาศเตือนอพยพระดับท้องถิ่นไม่มีกฎหมายรองรับชัดเจน (RELAYED,
  TDRI 3 ธ.ค. 2025)".
- **Infrastructure kind** — `infra_class` (`grey|green_blue|soft`) on every water node
  (`grey` default for gate/canal_reach/pump, `green_blue` for pond) and on new resource
  nodes: `WL.NBN.01` (บึงหนองบอน, VERIFIED via `bma_plan2569_retention_ponds.yaml`, a real
  gap this repo already had the data to close), `GI.CHULA_CENTENARY_PARK`,
  `GI.BENJAKITTI_FOREST_PARK` (green_blue examples TDRI names), and
  `RES.COMMUNITY_WARNING_LITERACY.SAMMAKORN.01` (soft, OPEN — no instance evidence).
- **Warning quality** — `warns` edges now carry `datum`/`area`/`lead_time` alongside
  `instruction` (CAP-like fields). Every row's `datum`/`lead_time` is `OPEN` — no S9/S14
  announcement states either. Ties to this repo's own existing rule (ground level ≠ water
  level, `canal_graph.py`'s `REASON_DATUM_MISMATCH`) — a warning with no datum is the same
  class of failure. `validate.py::report_warning_quality_gaps()`, non-error.

Hat Yai is **next-version scope**, recorded as one cross-case lesson row only
(`docs/knowledge/structural_issues_2026-09-28.yaml` `ISSUE-LESSON-HATYAI`) — no Hat Yai
node anywhere in this graph.

## Environman extension + completeness pass (2026-09-28)

Founder ask: Environman (สื่อสิ่งแวดล้อม) FB post 28 ก.ย. 2569 (RELAYED, citing
ubonmet.tmd.go.th/.../1_Month/09.pdf, prd.go.th/.../iid/545141, thaipbs 558736/558712) --
then corrected: "ไม่ต้องเอาตัวเลข สกัดแค่เครือข่าย node โฟกัสที่ทำ typology ให้เต็ม" (network
structure only, no capacity/length/rain/level numbers).

- **Confluence**: `WATER.canal_ladprao` -> `WL.CONFLUENCE.LPR_SSB.01` -> `WL.SSB.04`
  (คลองลาดพร้าวเข้าคลองแสนแสบที่บึงพระราม 9) -- position on the mainline is OPEN precision
  (placed between `WL.SSB.07`/`WL.SSB.04` by rough geography, not a surveyed match),
  added as an ADDITIONAL inflow, never replacing the existing `e_ssb07_ssb04` edge.
- **Rama 9 tunnel + พระโขนง pumps**: reuses `sources/capacity_ledger.yaml` ids verbatim
  (`tunnel:bma_dds:saensaeb_ladprao`, `pump_station:water_station:1`/`2`,
  `tunnel:bma_dds:nongbon`) -- no capacity number imported into this typology, only the
  structural link `WL.SSB.04 -> tunnel -> pump -> river:chao_phraya`.
- **Drainage precedence**: `drains_after` attribute on tributary->mainline edges
  (`WATER.ram53_canal`/`WL.KJN.01`/`WATER.khlong_jik` -> `WL.SSB.07`, all pointing at
  `WL.SSB.09` as the "upper แสนแสบ" reference) -- qualitative, cross-referenced to
  `tools/flowmap/flow_stall.py`'s RULE-STALL-01, never computed here.
- **Debris/condition**: `condition: OPEN` on pump/tunnel intake nodes (which station(s)
  the post means is itself OPEN, applied to all rather than guessed at one) +
  `docs/knowledge/structural_issues_2026-09-28.yaml` `ISSUE-INFRA-02`.
- **North axis stub**: `WATER.canal_prem_prachakon` (`scope: bangkok_north_mvp_stub`),
  clearly out of Sammakorn MVP scope, one edge to the river sink, no station codes.

**Completeness pass** (same commit, founder: "fill structural gaps that sources already
in the repo can close"): `sources/owner_agency_crosswalk.yaml`'s own VERIFIED row
(owner "กทม. สนน. (กลุ่มงานระบบควบคุมน้ำตะวันออก)" -> `AG_DDS`) + `docs/CAPACITY.md` §2
resolved `ST.SPS.01-04`'s `owned_by` from `OPEN` to `AG_DDS` (tag `VERIFIED-CONTRADICTED`
-- `docs/CAPACITY.md` itself still flags this pending operator-side confirmation, kept
visible on the edge rather than upgraded to plain VERIFIED). Also closed: `AG_JS100`
(orphan -> `reports_to` `RES.BOAT_PUSH...`, same S11 source already on that resource),
`RES.TRUCK_GMC...` (orphan -> `supplies` `OPEN`, S9 names the need but not a zone), and
`WL.NBN.01` (orphan -> wired into the tunnel/pump/river chain above via the proposal's
own §5 text). `AG_BASIN_CMT`/`AG_REGCOM` and 3 no-connectivity-data nodes
(`GI.CHULA_CENTENARY_PARK`/`GI.BENJAKITTI_FOREST_PARK`/`RES.COMMUNITY_WARNING_LITERACY...`)
stay documented orphans -- the first two would need a `commands`-style edge kind outside
this typology's current closed vocabulary (not added, to avoid scope creep), the latter
three have no source in this check stating any connection at all.

## Post-flood home recovery task DAG (2026-09-28)

Founder (verbatim): "'คู่มือจัดการบ้านหลังน้ำลด.pdf' สกัด dag typology
graph เสริมเข้าไปใน node ปัจเจก" — a household-level (ปัจเจก) post_event task DAG extracted
from the whole 40-page PDF (`pdftotext -layout`, read directly, never copied into the
repo). Bibliography + structure: `docs/knowledge/card_guide_post_flood_home.md`.
Publisher: คณะทำงานอาสาสมัครจาก สมาคมสถาปนิกสยาม ในพระบรมราชูปถัมภ์ + สมาคมนักออกแบบเรขศิลป์ไทย +
วิศวกรรมสถานแห่งประเทศไทย ในพระบรมราชูปถัมภ์ (วสท.), พฤศจิกายน 2554.

**Node kind `household_task`** (new — no existing kind fits a procedural checklist
item), `layer: self_help`, `self_help_layer: 0` (same numeric layer as `household` in
`community_dag.py`'s `KIND_LAYER` — a single household's own actions, not an escalation
to `buddy_cell`/`zone`), `phase: post_event` (the whole guide is entirely post-event by
its own title). 13 tasks (`typology/nodes/postflood_guide_tasks_2026-09-28.yaml`), every
row page-cited, tag `VERIFIED` (primary source read directly this check): `HHTASK.PREP`
→ `HHTASK.PHOTO_DAMAGE` → `HHTASK.VENTILATE` → `HHTASK.ELECTRICAL` → `HHTASK.STRUCTURE`
→ `HHTASK.CLEANING` → `HHTASK.SANITATION` → `HHTASK.DOORS_WINDOWS` → `HHTASK.FLOORS` →
`HHTASK.WALLS` → `HHTASK.APPLIANCES` → `HHTASK.FURNITURE` → `HHTASK.PLANTS`.

**Node kind NOT reused, new edge kind `precedes`** (task ordering only — `flows_to` is
water topology, `escalates_to` is the self-help social-network layer with its own
forward-only numbering, nothing else in the closed vocabulary means "task B after task
A"). `precedes_basis` distinguishes `explicit` (the guide states the dependency
directly, e.g. p.8: cleaning only starts once the electrical system is confirmed fully
off) from `toc_order` (follows the guide's own stated ordering PRINCIPLE, p.3: "การเรียง
ลำดับหัวข้อในคู่มือนี้จะเริ่มจากเรื่องสำคัญที่สุดไปหาเรื่องสำคัญน้อย"). `tools/typology/
validate.py::rule_precedes_acyclic()` enforces the DAG stays acyclic as a schema error.

**Bridged to the household template** (`sammakorn_household_template -> HHTASK.PREP`,
`precedes`, tag `OPEN` — the ONE proposal-only edge in this whole set, since the guide
never mentions this repo's graph; every task-to-task edge downstream is `VERIFIED`).
`sammakorn_household_template` is already area-agnostic BY DESIGN in the imported
file's own comment ("template สำหรับสร้าง node จริงรายกลุ่มบ้าน") — not edited, reused as-is,
its `area_id: sammakorn` field left untouched (out of scope to fork the imported file).

**Agency links** (`reports_to`, existing edge kind): `HHTASK.ELECTRICAL -> AG_MEA` +
`AG_PEA` (p.10: "แนะนำว่าให้ท่านติดต่อไปที่การไฟฟ้านครหลวงหรือการไฟฟ้าภูมิภาค...") — `AG_MEA`
already existed, **`AG_PEA` (กฟภ.) is new**, no node existed anywhere in this typology or
`water_system_dag.mmd` before now. `HHTASK.STRUCTURE -> AG_EIT` (p.15: "วิศวกรอาสา"
hotline, 080-812-3733/3743/2853, weekdays 9:00-17:00) — **`AG_EIT` is new** too.
Generic private technicians/repair centres the guide also names ("ช่างไฟฟ้า", "ศูนย์ซ่อม")
are NOT governance agencies and are left unlinked (not invented as nodes).

**Numbers kept as quoted text only** (`quoted_text_th`, page-cited, never a computed
attribute): chlorine ratio "ร้อยละ 0.1 หรือคลอรีน 1 ซีซีต่อน้ำหนึ่งลิตร" (p.18), disinfection
wait times, insulation resistance "ไม่น้อยกว่า 1 เมกกะโอห์ม ที่ 500 โวล์ท" (p.12), wall drying
times, planting-hole dimensions (p.37) — see the card for the full list.

**Wording rule**: any `ไม่ต้อง`/`ห้าม`/`ไม่ควร`/`ผ่อนคลาย` appearing in a task node is the
GUIDE's own verbatim wording (marked with quote marks + page cite, e.g. HHTASK.WALLS/
HHTASK.APPLIANCES/HHTASK.PLANTS explicitly flag which quoted sentence uses which banned
word) — this check never drafted new resident-facing text using those words itself
(test-enforced, `test_no_banned_wording_introduced_by_this_task`).

**Unsourceable, checked and confirmed absent from the PDF** (not invented): gas/LPG
safety content (no match for "แก๊ส" anywhere in the 40 pages), a drinking-water/food/
household-health chapter (the founder's own example flow mentioned this category, but
this specific guide does not cover it — only "ระบบประปา", the piped-water SYSTEM, not
drinking water/health), any ISBN/registration number, any phone number for ปภ./MEA/PEA
(only the EIT volunteer-engineer numbers are printed in the file).

## Community self-help DAG bridge (2026-09-28)

Founder (verbatim): "เหมือนเรามีงานวิจัยและโปรโตคอลแล้วนะ" — "ตรวจ git ให้ดี" found the protocol
already existed on `public/main` (GitHub `origin/main`, orphan history vs. this private
tree) but had never been imported into any private branch. Imported by content copy
(`git show public/main:<path> > <path>`, commit `5364c23`, no merge/cherry-pick of
unrelated history): `community_dag.py`, `docs/COMMUNITY_SELF_HELP_DAG.md`,
`site/inputs/community/self_help_dag.yaml`, `tests/test_community_dag.py` — all 7
imported tests pass unmodified. **Not imported this check** (listed for founder
decision): `docs/THAILAND_WATER_GOVERNANCE.md`, `docs/HIERARCHICAL_FLOOD_ZOOM.md`,
`hierarchical_flood_zoom.py`, `raw_stage_forecast.py`,
`site/inputs/governance/thailand_water_governance_reference.json`,
`tests/test_hierarchical_flood_zoom.py`, `tests/test_raw_stage_forecast.py`, and 8
`experiments/*.md` backtest/redteam/prospective-audit files.

**Protocol extension** (reuse, not a fork — `community_dag.py`'s own imported code is
otherwise untouched):
- `EDGE_MODES = {walk, vehicle, boat, high_clearance}` — first closed-vocabulary
  enforcement of `modes` in `validate_document()` (previously unvalidated).
- `support` node kind, layer 3 (shared with `internal_safe`, not a new layer number —
  see `community_dag.py`'s own comment for why), `SUPPORT_SERVICES` = kitchen/
  medical_post/charging/supply_depot/donation_point/rescue_staging.
- `zone_priority_order()` / `zone_has_verified_access()` — access-first structural rule
  (no equation): `RESTORE_ACCESS` before `SUPPORT` before `EVACUATE` when no verified,
  fresh, OPEN/ASSISTED, CLEAR/CAUTION edge chain with a fitting mode reaches egress/
  external_safe; `UNKNOWN` never counted as passable (same discipline as the rest of the
  module).

**Bridge into this typology graph** (`tools/typology/build_graph.py::load_self_help_dag()`):
every self-help DAG node loads as `layer: self_help`, `kind: self_help_<original kind>`,
original id kept verbatim (`self_help_kind`/`self_help_layer` carry `community_dag.py`'s
own kind/layer number). Internal DAG edges load as a new closed-vocabulary edge kind
`escalates_to` (all currently tag `OPEN` — every source row is `status: UNKNOWN`,
`field_verified: false`). Cross-layer bridge edges reuse the EXISTING `reports_to`/
`supplies` kinds (founder-provided drafting input, all PROPOSAL/OPEN):
`sammakorn_zone -> AG_ESTATE`, `AG_ESTATE -> AG_DDS` (closes the community->pump-operator
gap structurally; the pump OWNER stays `VERIFIED-CONTRADICTED`, unchanged),
`sammakorn_zone -> AG_BMA_GOV` (formal channel, distinct from the existing
`AG_FB_ADMIN -> AG_BMA_MED` social-media pickup edge), `sammakorn_zone -> AG_MEA`
(outage-report-inward, distinct from the existing `AG_MEA -> OPEN` warns-outward edge —
test-enforced they never conflate), `sammakorn_internal_safe -> sammakorn_zone`
(`supplies`). Known OPEN, kept as declared: only ONE `sammakorn_zone` for the whole
village (no per-soi zones invented); `sammakorn_internal_safe`/`sammakorn_egress` stay
`status: UNKNOWN` (not field-verified).

## Sammakorn worked chain (this build's `output/typology_sammakorn_subgraph.json`)

**Fixed 2026-09-28 after an independent-review finding (NEEDS_FIXES)**: an earlier version
of this section hand-wrote a chain that did not match what `tools/typology/build_graph.py`
actually built (pumps chained in series, no edge linking the Sammakorn branch to the
แสนแสบ mainline at all). The text below is generated FROM the built graph
(`nx.shortest_path` over its own `flows_to` edges), not hand-written — reproduce with:

```
python3 -c "
import networkx as nx
from tools.typology import build_graph
G = nx.MultiDiGraph()
build_graph.build_water_layer(G); build_graph.load_registry_nodes(G); build_graph.load_registry_edges(G)
FG = nx.DiGraph(); FG.add_edges_from((u,v) for u,v,d in G.edges(data=True) if d['kind']=='flows_to')
print(nx.shortest_path(FG, 'WL.SMK.01', 'river:chao_phraya'))"
```

**North exit** (the real, sourced link to the แสนแสบ mainline — read directly off
`site/build_data.py`'s own `SAMMAKORN_CHAIN_NODES`/`SAMMAKORN_CHAIN_EDGES`, the repo's
existing PROP-FLOOD-04 instantiation for exactly this question, founder's own correction
there verbatim: "สัมมากรต้องเชื่อมกับน้ำในคลองด้วย เพราะมันเป็นน้ำย้อนจากคลอง ไม่ใช่แค่ปั๊ม" — never
picked by coordinate proximity; neither `WL.SMK.01` nor `WL.BMA.02` carries a lat/lon in
this build at all):

```
SOI.SAMMAKORN.17/18 --flows_to--> WL.SMK.01 (บึงสัมมากร)
WL.SMK.01 --flows_to--> ST.SPS.01 --flows_to--> WL.BMA.02 (คลองบ้านม้า)
WL.BMA.02 --flows_to--> WL.SMK.01   [declared backflow-risk reverse edge, RELAYED,
                                      corroborated by 2 community reports, not MEASURED]
WL.BMA.02 --flows_to--> WL.SSB.08 (แสนแสบ-เสรีไทย 24)
    --flows_to--> WL.SSB.07 (แสนแสบ-บางกะปิ)
    --flows_to--> WL.SSB.04 (แสนแสบ ตอนใน)
    --flows_to--> WL.PKN.01 (พระโขนง)
    --flows_to--> river:chao_phraya (เจ้าพระยา)
```

**South exit** (`site/inputs/canals/east_chain.yaml`'s `e_sammakornpond_wangyai`
`control_structures` field names all 3 pump codes on ONE shared edge without a
per-station outlet — modelled as 3 INDEPENDENT pond→pump→wangyai legs, never chained
pump-to-pump, tag `OPEN` since the per-station split itself is undeclared):

```
WL.SMK.01 --flows_to--> ST.SPS.02 --flows_to--> WATER.wangyai
WL.SMK.01 --flows_to--> ST.SPS.03 --flows_to--> WATER.wangyai
WL.SMK.01 --flows_to--> ST.SPS.04 --flows_to--> WATER.wangyai
WATER.wangyai --flows_to--> WATER.tpk03 --flows_to--> WL.PWT.03 --flows_to--> WL.PWT.04
    --flows_to--> WATER.ladkrabang --flows_to--> WATER.south_outlet [OPEN]
    --flows_to--> river:chao_phraya
```

Every `flows_to` edge's direction/tag is carried straight from its cited source
(`site/build_data.py` for the north exit, `east_chain.yaml`'s own `design_direction` —
`RELAYED` when declared, `OPEN` when `unknown` — for everything else); this build never
invents a direction or a connection. `tests/test_typology_sammakorn_chain.py::test_chain_
ordered_path_pond_to_river` asserts the exact north-exit path above,
`test_no_pump_to_pump_flows_to_edge` and `test_south_branch_pumps_are_parallel_not_series`
lock in the pump-topology fix. Run `python3 -m tools.typology.validate` for the full gap
report (pump operator OPEN, AG_MEA warns-to-soi OPEN, south-exit per-station outlet OPEN,
etc — these are the documented structural gaps, not bugs).

## Four-graph framing (Hydrology / Control / Community / Safe-Logistics) mapped onto
## this typology's existing layers (2026-09-28)

Added per docs/knowledge/card_dual_state_reescalation_hatyai_2026-09-28.md (reasoning
over experiments/2025-11-hat-yai-real-data-redteam.md, already in this repo, treated as
RELAYED/INSTINCT ideas re-sourced against this repo's own files). No new layer name is
introduced here — this is a mapping table onto layers this typology already has:

| Four-graph framing | This typology's existing layer | Node kinds already carrying it |
|---|---|---|
| **Hydrology** (rain/river/canal state) | `layer: water` | `canal_reach`, `gate`, `pump`, `pond`, `river`, `tunnel` (this build's water layer, above) |
| **Control** (who decides/operates/reports, agencies/ministries) | `layer: power` | `agency` (`agency_class: state`), `ministry`, `government`, `warning_channel` |
| **Community** (mutual-aid social graph) | `layer: self_help` (this build's `load_self_help_dag()`) | `self_help_household`/`self_help_buddy_cell`/`self_help_zone`/`self_help_support`/`self_help_internal_safe`/`self_help_egress`/`self_help_external_safe` |
| **Safe/Logistics** (resources/tools that move people or supplies, and the safe-node continuity check, §"Safe-node continuity fields" in `community_dag.py`) | `layer: resource` (typology) + the `self_help` layer's `support`/`internal_safe`/`external_safe` kinds | `resource` (`RES.TOOL.*`, `RES.*` instances), civil `agency` (`layer: civil`) operators |

The `civil` layer (non-state agencies: `AG_ESTATE`, `AG_JS100`, commercial operators,
foundations, industry associations — see `typology/nodes/agencies.yaml`) cuts across
Control and Community rather than being a fifth graph: a civil agency can sit inside
Control (e.g. `AG_ESTATE` as the juristic village committee) or drive Community/Safe-
Logistics resources (e.g. `AG_OPERATOR_SAENSAEB_BOAT`, `AG_SYSTRONICS` — see
`typology/nodes/tool_water_push_boats_2026-09-28.yaml` and
`typology/nodes/mhesi_rescue_drones_romklao_2026-09-28.yaml`).
