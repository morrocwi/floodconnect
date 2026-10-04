# AGENTS.md — the one AI entry point for this repo

**Read this before touching any file.** Humans start at `START_HERE.md`; this file is the
AI-facing equivalent — what an AI session must know before it edits code, adds a document,
or proposes a publish. It does not duplicate `START_HERE.md`'s narrative; it is the
rule-and-command reference. When the two disagree, treat that as a bug and fix the stale
one — don't silently pick a side.

**อ่านไฟล์นี้ก่อนแตะไฟล์ใด ๆ** — มนุษย์เริ่มที่ `START_HERE.md`, ไฟล์นี้คือฉบับสำหรับ AI: กติกา
+ คำสั่งที่ต้องรู้ก่อนแก้โค้ด เพิ่มเอกสาร หรือเสนอ publish อะไรก็ตาม

## 1. Purpose / จุดประสงค์

FloodConnect is a public **readout** system (not a forecast, not a safety certification) for
flood risk around Sammakorn village / Soi Ramkhamhaeng 53, Bangkok. Every number on the
public page is a timestamped, source-tagged reading from an official agency or a community
report, assembled by an all-volunteer team with no instruments of its own. An AI session
working in this repo is extending a **readout pipeline and its knowledge base**, not
building a prediction engine — any change that makes a number look more certain than its
source justifies is a regression, not an improvement.

## 2. Non-negotiable rules

- **Epistemic tags on every claim**: `VERIFIED` (checked yourself) / `MEASURED` (read from
  this repo's own data) / `RELAYED` (from another source, not independently checked) /
  `INSTINCT` (a judgment call) / `OPEN` (unresolved/contradictory). No untagged claim in
  any tracked `.md` file.
- **Toledo-first for equations**: every equation used in code must be a registered
  `PROP-FLOOD-xx` proposal (see `docs/CAPACITY.md` §7 for `PROP-FLOOD-03`, water balance)
  or explicitly marked "not yet in Toledo" in the code/doc. Never derive a new formula
  inline. `REFUSED` is a correct, honest output when required inputs are missing — never
  fabricate a number to fill the gap.
- **Never prune**: `data/observations.sqlite` (append-only), `raw/`, and the `readout_log`
  table are historical record. A stale/contradictory row (e.g. 195 vs 200 pump stations)
  stays, tagged `OPEN`, never deleted "for tidiness."
- **Public-page wording law**: never write `ยังไม่ต้อง` / `ห้าม` / `ไม่ควร` / `ผ่อนคลาย` /
  `ปั๊มเสีย` on the public page — these read as forecast/safety-certification language,
  which this project is not. A failed pump station is worded exactly
  `"ขัดข้อง (กทม. รายงาน สาเหตุไม่ทราบ)"` (see `site/build_page.py`, `pump_wording()`) —
  reuse that string, don't paraphrase it.
- **No personal names** in any tracked file, including community reports (soi + condition +
  time only).
- **No AI/vendor name and no absolute local filesystem path** in any tracked file — not as
  author/co-author, not in a commit trailer, not in a code comment.
- **BMA-host safety**: at most one request per URL per run on `weather.bangkok.go.th` /
  `dds.bangkok.go.th` (and in practice, everywhere in this repo) — no retry loops. A 403 or
  reset means stop touching that host this run.
- **One committing worker per worktree**: multiple workers may write different files
  concurrently; only the worker that owns a worktree/commit may `git add/commit/push` for
  it.
- **Maker ≠ checker**: whoever writes a collector/parser/document is not the one who
  approves it for public release — run an independent review before any publish.

## 3. Pipeline — exact commands

```
collect.py --all              # pulls every source in sources/registry.yaml (1 req/URL/run)
        ↓
data/observations.sqlite      # append-only store (observations/documents/contradictions)
        ↓
site/build_data.py            # runs only registered equations (PROP-FLOOD-01/03/04/05a/05b) -> data.json
        ↓
site/build_page.py            # assembles a local page from data.json (not hosted anywhere)
        ↓
tools/api/export_api.py       # writes site/dist/api/v1/** from the build above
```

**No hosted access (project decision 2026-10-04):** GitHub Pages is unpublished and stays
off. This repo ships no pre-computed flood reading for anyone to read without running the
pipeline themselves — `site/dist/**` (including `site/dist/api/v1/**`) is gitignored, not
tracked, and not part of any release artifact. `gate: leak-scan` (§6) still runs before any
public push, but there is no "publish -> Pages" step any more; there is no deploy job and
no `pages`/`id-token` permission in `.github/workflows/floodconnect.yml`.

No scheduled fetch anywhere: there is no cron/timer in this repo, and the committed GitHub
Actions workflow (`.github/workflows/floodconnect.yml`) runs on push to `main` or a manual
`workflow_dispatch`, but **never runs `collect.py` itself and never deploys anything** — it
only validates and runs the full regression suite against the committed tree
(`site/inputs/**`, `sources/*.yaml`, and the rest of the tracked tree). A fresh clone has
no `data/`, `raw/` or `site/dist/**` to read, so `floodconnect answer` reports UNKNOWN with
a refresh action until a caller runs `collect.py --all` (and, for the static API export,
`site/build_data.py` + `tools/api/export_api.py`) on their own machine, network and keys.
`readout_history.py --history --days N` replays `readout_log` — it computes nothing new
and picks no "winner" between runs.

## 4. File map by question

| Question | Open |
|---|---|
| Current water status | `floodconnect answer --refresh` on your own machine (no hosted page) / `site/dist/data.json` after you build it |
| Trend / who bears the burden | `readout_history.py --history` |
| BMA drainage capacity | `docs/CAPACITY.md` |
| Who has authority / who to ask | `docs/knowledge/POWER_RESOURCE_MAP.md` |
| Thai water governance structure | `docs/knowledge/THAI_WATER_GOVERNANCE_MAP.md` |
| Duplication/gaps between agencies | `docs/knowledge/OVERLAP_REGISTER.md`, `docs/knowledge/WATER_SYSTEM_DAG.md` |
| Per-agency mandate/feeds | `docs/knowledge/agencies/*.md` |
| What we still can't answer | `docs/knowledge/WATER_MANAGER_QUESTION_BANK.md` (or `kb.py status`) |
| System vs. world frameworks | `docs/ARCHITECTURE_world_frameworks.md` |
| Live plan / what to do next | `docs/knowledge/HANDOFF_ecosystem_2026-09-27.md` (see §7) |
| Find anything by keyword | `python3 kb.py find "<term>"` |

## 5. Adding things

- **New source**: add an entry to `sources/registry.yaml` (id, agency, url, trust_tier,
  `host_rule.max_requests_per_run`), wire it into `collect.py`, add a fixture + test in
  `tests/`. A static reference document additionally needs a card under
  `docs/knowledge/` (see below) and a `reference_documents:` entry in the registry.
- **New document**: write the card under `docs/knowledge/` (RELAYED tag + ingest date +
  what node/agency it describes — see `docs/knowledge/README.md`'s own rule), add a row to
  the level-N table in `docs/knowledge/README.md`, then run `python3 kb.py reindex` so
  `docs/knowledge/INDEX.yaml` picks it up. Never hand-edit `INDEX.yaml`.
- **New indicator**: any new per-run number that should be comparable over time must write
  a `readout_log` row (see `store.py`'s schema and `site/build_data.py`'s
  `write_readout_log()`) — a number computed but never logged is invisible to
  `readout_history.py` and to anyone reconstructing what happened.

## 6. Tests / gates

```
python3 -m pytest tests/ -q         # must pass before any commit
python3 kb.py status                # coverage vs. WATER_MANAGER_QUESTION_BANK.md
python3 kb.py reindex               # after adding/removing a docs/*.md file
python3 check_doc_links.py          # fail on any dangling relative .md link
# leak scan before any publish: grep every file about to leave this workstation for
# AI-vendor names, absolute local filesystem paths, and any local username -- run it,
# don't paraphrase it into a comment
```

## 7. Handoff convention

Multi-agent or multi-stage work gets a `docs/knowledge/HANDOFF_<topic>_<date>.md` memo
**written before the run starts**, not after: task + the requester's own words, what's
already read/decided, what NOT to do, and the concrete next step. The current live plan
is **`docs/knowledge/HANDOFF_ecosystem_2026-09-27.md`** (6-stage water-ecosystem
programme, sequencing gates, per-stage next step) — read it before starting stage 2 or
later.

## 8. Known OPEN items

This section is a point-in-time snapshot, not a live dashboard — counts drift with every
build; re-run the commands below rather than citing the numbers here as current.

- **Pump ownership, ST.SPS.01-04**: a line originally written here as "Sammakorn
  village's own pumps, not BMA's" is **CONTRADICTED** by an official document —
  `แผนปฏิบัติการป้องกันและแก้ไขปัญหาน้ำท่วม กทม. 2569` ภาคผนวก ง, p.191 lists all four under
  **สนน. กลุ่มงานระบบควบคุมน้ำตะวันออก** (BMA Drainage & Sewerage Department, East
  Water-Control Group) by name + coordinates — matched in
  `docs/knowledge/bma_plan2569_control_structures.yaml`. Total rated capacity 7.75 m³/s.
  Still pending confirmation from the relevant agency/village juristic person — treat as
  VERIFIED-from-the-plan-document, not yet externally confirmed. See `docs/CAPACITY.md`
  §2 for the corrected capacity table. Both the original claim and the correction are
  kept, dated, rather than silently rewritten — see `docs/knowledge/card_official_2026-09-27_bma_flood_plan_2569.md`
  §7 for the underlying source.
- **Gate states** (ประตูมีนบุรี/ประเวศ-ลาดกระบัง/พระโขนง) are not published by BMA and are
  currently **inferred**, not measured.
- **`PROP-FLOOD-02`** (time-to-threshold) is referenced in planning docs
  (`docs/ARCHITECTURE_world_frameworks.md`, `START_HERE.md`) but **not implemented
  anywhere in code** — do not cite it as live.
- **`tests/test_readout.py::test_build_readout_with_fixture_store`** — fixed. Root
  cause: `readout.build_readout()` computed every observation's staleness
  (`lwl.age_hours`) against real wall-clock `generated_at` even when the caller
  explicitly pinned a historical `as_of_date` (replay/backfill/test-fixture mode) — so a
  fixture reading correctly fresh *as of its declared date* kept flipping to `STALE`
  purely because real time had moved on since the fixture was written, never MEASURED.
  Fix (in `readout.py`, `build_readout()`): when `as_of_date` is explicitly passed,
  staleness is now judged from the **start of that declared day**
  (`staleness_reference_utc = f"{as_of_date}T00:00:00+00:00"`), not from real now; when
  `as_of_date` is omitted (the live `collect.py`/`build_data.py` path, which never passes
  `--date`), behaviour is unchanged (`generated_at`, real now). `python3 -m pytest
  tests/test_readout.py -q` → passes.
- **`tests/test_kg_build.py::test_no_coords_outside_thailand_bbox`** — fixed via an
  explicit, documented whitelist rather than left failing: 4 HydroRIVERS river-reach
  nodes sit at 105.706–105.710°E, just east of this repo's `THAILAND_BOUNDS`
  (97.3–105.7°E) cutoff — real border reaches (Mekong-adjacent), not a bad coordinate.
  `tools/kg/build_kg.py` names all 4 exact node ids + reason + `tag:
  RELAYED-HydroRIVERS` in `KNOWN_BORDER_EXCEPTIONS`; the test asserts every out-of-bbox
  node is in that dict (any NEW out-of-bbox node — a real leak — still fails the test)
  and that the whitelist's own count still matches. `python3 -m pytest
  tests/test_kg_build.py -q` → passes.

## 9. Multi-agent claim protocol

This repo also carries a Toledo-RKG claim-before-write protocol for the DSVA/knowledge-
graph cluster, summarized here; the full text is the canonical source and lives in
**`docs/MULTI_AGENT_PROTOCOL.md`** — read it directly for anything beyond this summary.
This file's §2–§8 above were written for the pipeline/readout side; the two rule sets do
**not contradict** each other (no shared rule states opposite things) but have not been
merged into one numbered list — a future pass should do that rather than leaving two
adjacent "rules" sections.

- **Boot order**: before changing anything DSVA/RKG-related, read `AGENTS.md` →
  `docs/AI_ENTRYPOINT.md` → `site/inputs/meta/floodconnect_repo_kg.yaml` → the task's
  `question_routes`/canonical artifacts → `.ai/claims/README.md`. Do not scan-and-invent
  a parallel ontology — if a node already exists in the RKG, extend it.
- **`main` is integration state, not a personal working branch**: normal work happens on
  `agent/<agent-id>/<task-slug>`, started from the current `main` head.
- **Claim before substantive writing**: if a task changes the meaning/schema/invariant/
  implementation/source-of-truth of a canonical RKG node, open a claim-only PR first
  (`.ai/claims/<claim-id>.yaml`), merge it to `main` ACTIVE before implementation starts.
  At most one ACTIVE claim per canonical node at a time (many reviewers are fine;
  multiple active writers are not). Not required for read-only analysis, typo-only doc
  fixes, evidence-only additions, or coverage-only tests — when uncertain, claim.
  Release via a `status: RELEASED` PR; never delete a claim file. List active claims:
  `python3 agent_claims.py --list`.
- **Ownership is by canonical node, not file path**: a second agent editing a different
  file that still touches the same canonical node is still a conflict.
- **Canonical extension rule**: before adding any new node/construct/registry/role,
  check the RKG and the closest existing canonical artifact; prefer extending an
  existing node (attribute/role-overlay/capability edge) over inventing a new one;
  update the RKG in the same implementation PR when architecture changes.
- **Epistemic invariants**: `UNKNOWN != SAFE`; `topology != forecast`;
  `observation != forecast != warning != instruction != action`;
  `movement graph != support/lifeline graph`; `tool/facility type != route/site safety`;
  `tool capability never overrides Dry Gate`; `proposal/experiment != production truth`;
  `role overlay != duplicate actor identity`.
- **Implementation PR requirements**: state active claim id(s), canonical RKG nodes
  changed, source-of-truth artifacts changed, dependency edges added/removed, epistemic
  class changes, hard invariants affected, tests run, whether the RKG changed. Use
  `.github/PULL_REQUEST_TEMPLATE.md`.
- **Integration gates** (identical in substance to this file's own §6 above, no
  conflict, just stated twice): `python3 repo_knowledge_graph.py --validate`,
  `python3 agent_claims.py --validate`, `python3 -m pytest -q`; all three must pass; a
  task-specific test passing is insufficient if full regression fails.
- **Conflict classes beyond text conflict**: no textual merge conflict does not imply a
  safe merge — also check schema conflict, semantic conflict, epistemic conflict (silent
  evidence-class promotion), dependency conflict (downstream code still assumes the old
  schema).
- **Handoff**: claim id, current branch + head SHA, RKG nodes touched, files changed,
  tests/status, unresolved assumptions, explicit next step. The receiving agent rereads
  the current canonical files; it must not rely only on the handoff summary.

*สรุปภาษาไทยของหัวข้อนี้ (ไม่ใช่คำแปลตรง — สรุปสาระสำคัญ): หัวข้อ 9 นี้คือกติกา multi-agent
claim สำหรับ DSVA/RKG cluster — เนื้อหาเต็มอยู่ที่ `docs/MULTI_AGENT_PROTOCOL.md` ก่อนแก้ไฟล์
ที่กระทบ canonical node ของ RKG ต้องเปิด claim-only PR ก่อน (`.ai/claims/<id>.yaml`) ยกเว้น
งานอ่านอย่างเดียว/แก้คำผิด/เพิ่มหลักฐาน/เทสต์ coverage — ถ้าไม่แน่ใจให้ claim, มี ACTIVE claim
ได้ครั้งละ 1 ต่อ node, และต้องผ่านทั้งสาม gate (`repo_knowledge_graph.py --validate`,
`agent_claims.py --validate`, `pytest -q`) ก่อน merge กติกาฝั่งนี้กับกติกาเดิมของ repo
(หัวข้อ 2–8) ไม่ขัดกัน แต่ยังไม่ได้รวมเป็นชุดเดียว*

---

*ดูสรุปภาษาไทยของกติกาทั้งหมดใน §2 (ผสมอยู่ในเนื้อหาภาษาอังกฤษด้านบนแล้ว — คำสำคัญ: ติดแท็ก
epistemic ทุก claim, สมการต้องผ่าน Toledo ก่อน, ห้าม prune ข้อมูล, ห้ามคำที่สื่อพยากรณ์/รับรอง
ความปลอดภัยบนหน้าเว็บสาธารณะ, ห้ามชื่อบุคคล/AI/vendor/local path, 1 request ต่อ URL บน host กทม.
ห้าม retry, 1 worker ต่อ worktree ที่มีสิทธิ์ commit, maker ≠ checker ก่อน publish)*
