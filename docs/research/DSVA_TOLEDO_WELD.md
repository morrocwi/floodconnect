# DSVA ↔ Toledo Weld
## Formal bridge note for FloodConnect

**Status:** DSVA proposal / Toledo-unregistered  
**Date:** 2026-10-01

This note records the formal bridge used by \`docs/research/DISASTER_SYSTEM_VIABILITY_ARCHITECTURE.md\`.
It does **not** claim that DSVA-specific equations are already registered in Toledo.

## Existing Toledo anchors

1. **T-CAN-002** — retained root state: \(S_n=(G_n,\Lambda_n,T_n)\)
2. **T-CAN-003** — finite root stepper: \(S_{n+1}=F(S_n,u_n,c_n,T_n)\)
3. **T-CAN-006** — admissible domain translation preserves dynamics and declared readout
4. **T-CAN-007** — finite-horizon, task-relative reader equivalence
5. **T-CAN-008** — retained root / domain representation / discovered quotient non-collapse
6. **T-CAN-009** — finite append does not rewrite past indices

The authoritative Toledo registry/source is outside FloodConnect. This file is a dependency/provenance bridge, not a replacement registry.

## Candidate DSVA adapter

\[
q_{\mathrm{DSVA}}:
S_n
\mapsto
(\chi_n,E_{\le n},\mathbb B_n,\mathcal W_n,\mathcal K_n).
\]

Required dynamics weld:

\[
q_{\mathrm{DSVA}}\circ F
=
F_{\mathrm{DSVA}}^\sharp\circ q_{\mathrm{DSVA}}.
\]

Required reader preservation:

\[
O_Q^R
=
O_Q^{DSVA}\circ q_{\mathrm{DSVA}}.
\]

Required invariant preservation includes:

\`\`\`text
UNKNOWN != SAFE
MISSING != 0
OBS != FORECAST != WARNING != INSTRUCTION != ACTION
topology != forecast
installed capability != realized performance
\`\`\`

If a load-bearing weld cannot be demonstrated for a claim, the status is \`HOLD\`.

## Observation/evidence closure

The DSVA v0.3 information loop is:

\`\`\`text
retained root state
  -> root stepper
  -> DSVA domain adapter
  -> task/source reader
  -> accessible trace
  -> typed normalization
  -> admissible-world update
  -> adaptive policy
\`\`\`

This closes the v0.2 gap in which future information could affect policy without an explicit observation/evidence transition.

## Reader-equivalence and viable-future geometry

Toledo finite reader equivalence:

\[
z\sim_{Q,O,c,L}z'
\iff
O(F^kz)=O(F^kz')
\quad \forall k\le L.
\]

DSVA quotient:

\[
\mathcal C_{Q,L}(\mathbb B_t)
=
\mathbb B_t/\sim_{Q,O,c,L}.
\]

Viable-policy fibre:

\[
\mathfrak V_{Q,L}
=
\{(C,\Pi_L^{EB}(C)):C\in\mathcal C_{Q,L}\}.
\]

This is the DSVA **viable-future geometry**. The previous scalar \(T_V\) remains a projection/readout of this richer object.

## Finite action determination

A task action is determined only if reader-equivalent states yield the same declared action readout through the declared horizon. Otherwise the action readout is \`UNRESOLVED\`.

This formalizes:

\`\`\`text
forecast uncertainty != action uncertainty
\`\`\`

Different physical futures may remain possible while a conservative current action is already determined.

## External theory dialogue

An external theory is admitted into DSVA only through an adapter preserving the load-bearing dynamics, reader, and invariants for the declared question/horizon.

Bridge status:

\`\`\`text
WELDED
PARTIAL
HOLD
RIVAL
\`\`\`

A familiar theory name never becomes a DSVA premise merely by citation.

## Thailand finite witness

For the 28 Sep 2026 Sammakorn example, retained event evidence includes:

\`\`\`text
SMK.01 = 0.83 m
critical = 0.44 m
ST.SPS.01–04 = 0/4 operating
receiving-water state required for exact export = not closed
\`\`\`

Two logical admissible worlds can therefore agree on:

\`\`\`text
ABOVE_CRITICAL
pump state 0/4
NO_ALL_CLEAR
VERIFY_EXPORT_BOUNDARY
\`\`\`

while differing on exact clearance trajectory/ETA.

Hence the task-relative result is:

\`\`\`text
current threshold/action readout = determinate enough
exact clearance ETA = UNRESOLVED
\`\`\`

This is the finite Toledo-style witness for the DSVA proposition that state uncertainty can persist while a task action is already determined.

## Historical invariance / anti-hindsight

Toledo CAN-009 licenses the rule:

\`\`\`text
later evidence may extend a historical record
but may not rewrite the evidence available at an earlier decision time
\`\`\`

This is mandatory for FloodConnect backtests and prospective-style replays.

## Governance

DSVA-specific bridge equations remain proposals until separately reviewed/registered in Toledo. FloodConnect may execute, falsify, and refine them as proposal theory without promoting them to registered Toledo mathematics.
