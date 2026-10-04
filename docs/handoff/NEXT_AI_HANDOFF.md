# NEXT_AI_HANDOFF.md — a letter to the next AI working on this repo

You are picking up FloodConnect after its v0.1.0 release and the v0.1.1
external-AI-readability fix set. This file is the map; it does not replace reading the
real files it points to.

## 1. Current state (re-verify every number below — do not trust this file's memory)

- **v0.1.0 is released** on GitHub (`morrocwi/floodconnect`), tag `v0.1.0`. It ships
  the CLI/MCP `answer`/`forecast` path for two areas only: Sammakorn village and Soi
  Ramkhamhaeng 53, Bangkok. No hosted data, no scheduler on our side, caller installs
  and computes on their own machine. See `README.md` §2 for the exact feature list
  (F1–F8) and §3 for what is explicitly out of scope.
- **v0.1.1** (this working set) started as a doc-only pass — fixing surfaces that made
  a free, code-execution-less AI misjudge the repo as a hosted, 30-minute-cron API
  with a "real" flood-depth forecaster, neither of which is true — and then picked up
  real code changes from an independent post-release review: the WATCH=YELLOW
  reclassification (`kb.py`/`readout.py`), a new YELLOW/WATCH action, a
  bbox-scoped refresh path (`collect.py`/`tools/mcp/floodconnect_mcp.py`), and a new
  static `site/landing/` page served by its own `pages-landing.yml` workflow. See
  `.ai/claims/20261004-floodconnect-v011-claim.yaml`'s `nodes`/`artifacts`/`intent`
  for the authoritative current scope — do not call this release doc-only anywhere.
  Check the actual PR/merge state of this branch before assuming it already shipped.
- **The decision model described in `ARCHITECTURE.md`** (Water-Debt Core, D1–D8
  protocol, Semantic Decision Holarchy, Jev one-decision envelope, DSVA gate) is **a
  design target for v0.2+, not what `kb.py answer` returns today.** Re-read
  `ARCHITECTURE.md` §9's implemented-vs-planned table before telling anyone (a user, a
  reviewer, the founder) what this system currently does.
- **Toledo registration is partial and must be re-verified, not assumed**: as of this
  writing, PROP-FLOOD-01/02 are unverified proposals on Toledo `main` with placeholder
  codes (`weld/M.??.v1`); PROP-FLOOD-03..07 are open, unmerged PRs; PROP-FLOOD-08/09/10
  are drafts on an unmerged branch. None of PROP-FLOOD-03..10 may be used in the
  shipped decision path until at least registered-proposal status — re-check
  `toledo/registry/CANONICAL.json` and `toledo/registry/proposals/*.json` directly;
  this file's statement of status will go stale.

## 2. Read order

```text
README.md              -- what it is, what it is not, install, limits, hotlines
llms.txt               -- if present: the short machine-oriented orientation page
ARCHITECTURE.md         -- why the system is shaped this way (Water-Debt Core first)
ROADMAP.md              -- the release sequence + acceptance criteria per slot
AGENTS.md               -- write-safety rules: claim-first, one-writer-per-node,
                           the three integration gates, non-negotiable repo rules
site/inputs/meta/floodconnect_repo_kg.yaml  -- the machine-checked Repo Knowledge
                           Graph (RKG); run `python3 repo_knowledge_graph.py
                           --validate` after reading it, not instead of reading it
```

For the DSVA theory/decision-model specifically, follow `AGENTS.md` →
`AI_ENTRYPOINT.md` → `docs/research/DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md`'s own
read order (it is more detailed than this file for that one subsystem — do not
duplicate it here). If your own environment has a red-team/continuation protocol for
this project, follow it; this file assumes none and gives the file-based read order
above either way.

## 3. What NOT to do

- **Do not treat this file, `ARCHITECTURE.md`, or `ROADMAP.md` as more current than
  the RKG or the code.** When they disagree, the RKG/code wins; fix the stale doc,
  don't quietly pick a side and move on.
- **Do not use an equation that is not Toledo-registered** (at minimum a registered
  proposal) in anything that feeds `state`/`hazard`/`next_action`/a future Jev
  envelope field. An experiment file (`raw_stage_forecast.py`,
  `hierarchical_flood_zoom.py`'s PROP-FLOOD-10 path before it is merged, etc.) stays
  confined to the experiment/proposal branch — see `ARCHITECTURE.md` §1 and
  `AI_ENTRYPOINT.md` §3 "Experimental forecast / Toledo / prospective test".
- **Do not claim a planned capability as shipped.** If you are writing a README line,
  a release note, an answer to the founder, or a public comparison table, check
  `ARCHITECTURE.md` §9 first and mark anything not in the "v0.1.x" column
  `planned (v0.2+)` explicitly.
- **Do not skip claim-first.** Before any semantic write, check
  `python3 agent_claims.py --list` and claim your canonical RKG node(s) first — see
  `AGENTS.md` and `.ai/claims/README.md`. Ownership is by RKG node, not file path:
  editing a different file that still touches an already-claimed node is still a
  conflict.
- **Do not merge local and public histories, or force-push.** This public mirror
  (`morrocwi/floodconnect`) is maintained from a separate private working repository
  with its own history; content moves across by file-level PR after an independent
  leak/adversarial scan, never by pushing or merging whole branches/histories across.
- **Do not publish anything** (a public push, an edited release note, a repo
  description/topics change, a pinned issue) without an independent adversarial/
  leak-scan review (maker and checker must be different identities), and without the
  founder's approval for that specific artifact — a prior approval does not carry over
  to the next
  release.
- **Do not rewrite a failed red-team/backtest result into a quiet pass.** Negative
  evidence (e.g. the `HIT 0 / MISS 12` backtest at the 80mm threshold, the open
  red-team draft PRs) stays published and linked — see `ROADMAP.md`'s binding rules.
- **Do not say `SAFE`, "universally correct", "proven", or push for peer-review/
  external validation as a legitimacy step.** Knowledge validation here is horizontal
  only — the project's own stated epistemic discipline, not a per-repo quirk.

## 4. Next concrete task

Check the live state before assuming either of these is still accurate:

1. If v0.1.1's doc-only fix set (repo description/topics, `llms.txt`,
   `docs/EVIDENCE.md`, the hosted-API-surface purge, this architecture/roadmap/handoff
   set) has not yet passed its adversarial gate and been published — that is the next
   task. Run the unprimed clean-room acceptance test (README/ROADMAP's own acceptance
   criteria) before asking for publish approval.
2. If v0.1.1 is already published, the next slot is **v0.2.0** in `ROADMAP.md`: V5
   BMA-direct status wiring + the D1–D8 decision-protocol *skeleton* + the Jev
   one-decision envelope + `--level 1|2|3` + V4 nationwide point support at COARSE
   zoom only (basin/province, never household detail nationwide) — read
   `ARCHITECTURE.md` §3, §5, §6 and §9 first so what you build matches the shape
   already designed, rather than inventing a second one. V8 (Toledo registration) and
   V6 (water debt) are re-sequenced to right after v0.2.0 (ROADMAP.md's sequencing
   note) — do not build V1/V2/V3/V10/V7 before them.

Either way: re-run `python3 repo_knowledge_graph.py --validate`,
`python3 agent_claims.py --validate`, and `python3 -m pytest -q` before trusting any
claim in this handoff about the repo's current green/red state — they may have changed
since this file was written.
