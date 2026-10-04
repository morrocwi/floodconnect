# NEXT_AI_HANDOFF.md — a letter to the next AI (or human) working on this repo

**This project is paused as of 2026-10-05**, by founder decision, after releases
v0.1.2 and v0.1.3. This file is the map for anyone picking it back up — fork, PR,
or a completely separate continuation — and it does not replace reading the real
files it points to. Re-verify every number below against `CHANGELOG.md` and the
code; this file's own memory goes stale.

## 1. Why it is paused, in the founder's own words

- "ทำเลย v0.1.2 ทั้งประเทศ แล้วค่อยพัก" — do v0.1.2 nationwide, then pause.
- "ถ้าคนอื่นจะเอาไปพัฒนาต่อยอดเองทำได้ไหม เราจะพักโครงการนี้ไว้ก่อน" — can someone else take
  this and develop it further themselves; we will pause this project for now.
- Earlier, still-binding ruling on why there is no scheduler: "ปิดให้หมด...
  ป้องกันโทเคนไหลอัตโนมัติ" — shut it all off, to prevent tokens leaking out
  automatically. FloodConnect's public repo briefly carried a 30-minute GitHub
  Actions cron (added in the initial public release, removed in v0.1.0); since
  v0.1.0 there is no cron or scheduler this team operates, which is also why
  "pausing" mainly means: no further development from this team, not a takedown
  of what already shipped.

The milestone split (M2a now shipped as v0.1.3, M2b left as backlog) was itself a
founder-approved choice, not an improvised cut.

## 2. What is actually released (re-verify in `CHANGELOG.md`, not here)

- **v0.1.0** — CLI/MCP `answer`/`forecast` for two Bangkok areas only (Sammakorn
  village, Soi Ramkhamhaeng 53). No hosted data, no scheduler, caller installs and
  computes on their own machine.
- **v0.1.1** — external-AI-readability fixes (README/`llms.txt`/doc purge of
  "hosted API" language) plus real code: WATCH=YELLOW reclassification, a
  bbox-scoped refresh path, a static `site/landing/` page.
- **v0.1.2** (2026-10-04, "ทำเลย v0.1.2 ทั้งประเทศ") — any `lat,lon` in Thailand now
  gets a real `current_local_state`/`forward_hazard` reading at **COARSE
  (station/basin) resolution**, never household-level, outside the two named
  Bangkok areas (which keep their existing node-level detail unchanged). Station
  resolution: every fresh `thaiwater_waterlevel` station within 10 km decides,
  worst colour wins. Basin resolution (fallback): a fresh reading sharing the
  nearest station's `sub_basin_id` within 50 km decides, but can never produce
  GREEN alone. `NO_THRESHOLD` now correctly reads UNKNOWN, not GREEN. Full detail,
  including what is explicitly NOT included (`distance_to_bank_m`/
  `bank_fill_percent` stay provenance-only, no invented threshold): see
  `CHANGELOG.md`'s `## v0.1.2` section.
- **v0.1.3** (2026-10-05, milestone M2a, founder ruling "อย่างแรกให้เอไอต้องอ่าน
  แผนที่กราฟของเราได้จาก git ก่อน...") — the nationwide knowledge graph is now
  **shipped directly in git**: `output/thailand_water_kg.graphml` + `.jsonld`,
  26,727 nodes / 64,441 edges, readable with a plain `git clone`, no rebuild or
  network call required. `docs/KG_QUERY.md` is the read-this-first recipe page
  (runnable Python snippets, measured coverage numbers, not aspirational ones).
  KG-first is now a mandate in `AGENTS.md`/`docs/AI_TIERS.md`: before locating or
  reasoning about any place outside Sammakorn/Ram53, read the shipped graph from
  git first — never re-derive or re-geocode it. Full detail, including every
  stated known gap: `CHANGELOG.md`'s `## v0.1.3` section.

Nothing released is taken down by pausing. The repo, its tags, and its tests stay
exactly as released.

## 3. How to continue — anyone may fork

This is explicitly an open invitation, not a closed project:

- **Fork freely** under the existing licences (`LICENSE` — MIT, ARAYA Nikah Social
  Enterprise Co., Ltd., 2026). Re-check `LICENSE` and any per-file notice yourself;
  this file is not a legal opinion.
- **Keep lineage.** If you build on this, say what you started from (this repo,
  the tag/commit you forked at) rather than presenting it as a from-scratch work —
  this is a horizontal-validation project; lineage is how claims stay checkable,
  not a courtesy.
- **Run on your own machine, no scheduler.** The "no hosted data, no cron we
  operate" design is load-bearing (§1 above) — a fork that adds hosted/scheduled
  infrastructure is a different design choice than this repo's own, state that
  explicitly rather than quietly inheriting this repo's "no scheduler" claims
  while actually running one.
- **Toledo-first for any new equation.** Any new or revised equation in the
  decision path (`state`/`hazard`/`next_action`) goes through Toledo registration
  first — lookup, Genesis-gate compatibility, cite the parent, mark anything new
  `NEW DERIVATION / PROPOSAL` until actually registered. `PROP-FLOOD-03..07` are
  presently **open, unmerged Toledo PRs** — re-check
  `toledo/registry/CANONICAL.json` / `toledo/registry/proposals/*.json` yourself;
  do not cite them as registered equations in anything that ships.
- **Claim-first, still.** Before any semantic write, `python3 agent_claims.py
  --list`, then claim a canonical RKG node — see `AGENTS.md` and
  `.ai/claims/README.md`. A paused project is not an exception to one-writer-per-
  node.
- **Publish safety, still.** Any public push/release note/repo-description change
  needs an independent adversarial/leak-scan review (maker and checker different
  identities) before it goes out — the pause does not relax this.

## 4. The M2b backlog (left open, for whoever continues)

- [ ] **Canal-node + true-polyline `ON_REACH` snapping.** The current heuristic
  snaps to the nearest HydroRIVERS *river* reach centroid only — it never snaps to
  a declared canal-chain reach, and never snaps to a true polyline (point-to-line),
  only a point-to-centroid approximation. Pathum Thani currently has **0 of 15**
  assets with an `ON_REACH` edge.
- [ ] **Pathum Thani `IN_PROVINCE` join gap.** 13 of the 28 HII-geocoded Pathum ids
  ARE nodes in the shipped graph but carry no `IN_PROVINCE` edge, because of an
  id-prefix mismatch in the `hii_watergate` geocode join — a crosswalk fix, not a
  missing-node problem.
- [ ] **Point → province accountability wiring.** `tools/kg/accountability.py`'s
  `nearest_assets()` does not yet read `RESPONSIBLE_FOR` or walk to a
  province/basin node using the DWR `Province_2556`/`Amphoe_2556` polygons —
  by default (with `FLOODCONNECT_USE_SHIPPED_KG` unset) a bare `lat,lon` outside
  Sammakorn/Ram53 gets text-only accountability (the deciding station's own
  feed-published province/agency); with the guard set, the shipped KG is
  consulted via `nearest_assets()` only, still never a `RESPONSIBLE_FOR`/province
  walk.
- [ ] **Strahler ≥ 4 river network with real line geometry** (current snap is
  centroid-based, see above; the shipped network is Strahler ≥ 6, 2,250 reaches —
  docs/KG_QUERY.md).
- [ ] **Per-ONWR-basin "main river" flag.** The shipped `main_stem` is per
  HydroRIVERS system (by discharge), not the Thai administrative "สายหลัก"
  per-basin sense — a second explicit flag or crosswalk is needed.
- [ ] **`thaiwater` `situation_level` Thai labels per code** — the agency's
  labels/colours for 1–5 are VERIFIED (app.chunk.js, 2026-10-04; see the
  `STATUS_TO_LEVEL` comment in `floodconnect_model.py`); what stays open is
  re-checking them against the live bundle over time and whether FloodConnect's
  own conservative mapping (4→YELLOW, 1/2→GREEN) should change. That mapping is
  this repo's choice, not an agency threshold (see `docs/NEAREST_STATION_RECIPE.md`'s
  warning that code 1's label "น้อยวิกฤต" means critically LOW water, not RED, and
  that code 4 is agency-coloured BLUE, not a warning there).
- [ ] **A `rain_7day_per_model_mm` `json_path` test on a real payload** — not yet
  covered by a fixture test.
- [ ] `distance_to_bank_m`/`bank_fill_percent` remain provenance-only by design
  (Toledo-first — no invented threshold); revisit only if a registered equation
  justifies turning either into a real colour factor.

## 5. Other open items (not M2b, also not resumed by this team)

- **Water-debt equations in the answer** (the v0.2 plan). `PROP-FLOOD-03..07` sit
  in open, unmerged Toledo PRs — **never registered yet**; do not cite them as
  registered in a derivation, answer, or release note. Toledo-first applies before
  any of this reaches the shipped decision path. PROP-FLOOD-01/02 and 08/09/10 also
  need re-checking; see ARCHITECTURE.md §1 / ROADMAP v0.2.1.
- CCTV integration, a BMA levee/tide bulletin feed, satellite imagery, and
  additional Bangkok data portals — all backlog, none started.

## 6. Validators/tests to run before any change

```text
python3 repo_knowledge_graph.py --validate     # RKG schema + claim-ownership checks
python3 agent_claims.py --validate              # claim-first discipline
python3 -m pytest -q                            # full test suite
python3 check_doc_links.py                      # doc cross-link integrity (if present)
```

Run these before trusting any claim in this handoff about the repo's current
green/red state, and again before any new change — they may have drifted since
this file was written.

## 7. Read order (unchanged from before the pause)

```text
README.md              -- what it is, what it is not, install, limits, hotlines
llms.txt               -- short machine-oriented orientation page
docs/KG_QUERY.md        -- read the shipped nationwide KG FIRST, mandate (v0.1.3)
ARCHITECTURE.md         -- why the system is shaped this way (Water-Debt Core first)
                           (a v0.2+ design target, not what `kb.py answer` returns
                           today — see ARCHITECTURE.md §9)
ROADMAP.md              -- release sequence + acceptance criteria (now marked PAUSED
                           at the top; sections below that predate v0.1.2/v0.1.3 are
                           stale — CHANGELOG.md is the ledger of what actually shipped)
AGENTS.md               -- write-safety rules: claim-first, one-writer-per-node,
                           the three integration gates, non-negotiable repo rules
site/inputs/meta/floodconnect_repo_kg.yaml  -- the machine-checked Repo Knowledge
                           Graph (RKG); run `python3 repo_knowledge_graph.py
                           --validate` after reading it, not instead of reading it
```

For the DSVA theory/decision-model specifically, follow `AGENTS.md` →
`AI_ENTRYPOINT.md` → `docs/research/DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md`'s own
read order.

## 8. What NOT to do (unchanged by the pause)

- **Do not treat this file, `ARCHITECTURE.md`, or `ROADMAP.md` as more current than
  the RKG, `CHANGELOG.md`, or the code.** When they disagree, the code/CHANGELOG
  wins; fix the stale doc, don't quietly pick a side and move on.
- **Do not use an equation that is not Toledo-registered** in anything that feeds
  `state`/`hazard`/`next_action`. `PROP-FLOOD-03..07` are open PRs, not registered.
- **Do not claim a planned capability as shipped**, or claim this project as
  "active"/"maintained" without saying it is paused.
- **Do not skip claim-first.** Check `python3 agent_claims.py --list` and claim a
  canonical RKG node before any semantic write.
- **Do not merge local and public histories, or force-push.** This public mirror
  (`morrocwi/floodconnect`) is maintained from a separate private working
  repository; content moves across by file-level PR after an independent
  leak/adversarial scan, never by merging whole histories.
- **Do not publish anything** without an independent adversarial/leak-scan review
  and the founder's approval for that specific artifact.
- **Do not rewrite a failed red-team/backtest result into a quiet pass.** Negative
  evidence stays published and linked.
- **Do not say `SAFE`, "universally correct", "proven", or push for peer-review/
  external validation as a legitimacy step.** Knowledge validation here is
  horizontal only.
- **Do not stand up a scheduler/cron this team operates** — the pause exists partly
  to prevent exactly that ("ป้องกันโทเคนไหลอัตโนมัติ").

## 9. If you are the next AI/human and want to resume or fork

There is no next concrete task assigned by this team right now — that is what
"paused" means. If you want to continue:

1. Re-read this whole file plus `CHANGELOG.md` and `ROADMAP.md`'s `PAUSED` note.
2. Run the validators in §6; trust only what they say now, not this file's memory.
3. Pick an item from §4 (M2b) or §5, or propose your own direction — either way,
   claim-first (§9 of `AGENTS.md`), Toledo-first for any equation, and run the
   adversarial/leak-scan gate before anything public.
4. If this is a genuinely separate fork rather than a continuation under this
   team: say so in your own README, keep the lineage pointer back to this repo
   and commit/tag, and you are free to take it in your own direction under the
   existing licence.
