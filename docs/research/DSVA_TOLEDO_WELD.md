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
(\bar\chi_n,E_{\le n},\mathbb B_n,\mathcal W_n,\mathcal K_n).
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

## Repository-first v0.4 weld discipline

DSVA v0.4 does not promote every useful FloodConnect construct into a new Toledo equation.

The following remain canonical FloodConnect domain sub-readers/operators and are **absorbed**, not
redefined:

```text
COMMUNITY_DAG
TDLC / LCF / LVCN
ORCG
ENV_DEGRADATION / finite temporal ledger
SOCL shelter/recovery
WARNING_TYPOLOGY
UNIFIED_CRISIS
```

The extraction/provenance note is:

`docs/research/DSVA_FLOODCONNECT_CANONICAL_SYNTHESIS.md`

Only the residual v0.4 theory equations are new DSVA proposals:

```text
DSVA-R01..R03  hazard-induced topology transition / operational projection
DSVA-R04..R07  evidence validity, expiry and freshness admission
DSVA-R08..R09  forecast support breach / OUTSIDE_CALIBRATED_RANGE
DSVA-R10..R12  life-critical floor + recoverability policy + re-entry time
DSVA-R13..R14  hysteretic re-escalation / de-escalation
DSVA-R15       synthesized theory path
```

All remain **Toledo-unregistered proposals**.

### Weld obligation for dynamic topology and recoverability

When a DSVA claim depends on hazard-driven topology evolution or recoverability, the application
must still satisfy the Toledo domain/readout obligations:

[
q_{DSVA}circ F
=
F_{DSVA}^{sharp}circ q_{DSVA}
]

and the declared task reader must remain preserved through the horizon.

Operational Community DAG/TDLC results can therefore be used as domain readouts without claiming
that Toledo has registered their equations.

### Historical Hat Yai red-team

`experiments/2025-11-hat-yai-real-data-redteam.md` predates v0.4 and already identified repeated
pulses, current-vs-forward-state separation, adaptive freshness, multimodal movement, safe-node
service verification, outside-calibrated-range semantics and throughput constraints.

CAN-009 requires those historical findings to remain prior evidence. v0.4 may absorb them but must
not rewrite their chronology or claim them as newly discovered by the later theory revision.


## v0.5 information-contract bridge weld discipline

The leak-closing bridge is:

docs/research/DSVA_INFORMATION_CONTRACT_BRIDGE.md

It is not a new Toledo root. It is a set of DSVA domain obligations that must themselves remain welded to the same Toledo reader/dynamics invariants.

The six task-relative contracts are:

\[
\mathfrak C_t^Q
=
(C_E^Q,C_S^Q,C_T^Q,C_B^Q,C_N^Q,C_R^Q).
\]

Their Toledo interpretation is:

- \(C_E^Q\): the reader may consume only evidence that passes semantic/provenance/QC/compatibility obligations;
- \(C_S^Q\): the DSVA state must retain every distinction needed to preserve the declared future reader;
- \(C_T^Q\): hybrid damage/topology jumps must commute with the DSVA domain stepper;
- \(C_B^Q\): local subsystem guarantees may be promoted only when boundary assumptions are discharged;
- \(C_N^Q\): candidate-level feasibility may not be promoted to joint allocation if shared capacities are violated;
- \(C_R^Q\): recoverability is licensed only when the common policy can keep the system inside the emergency floor and re-enter normal viability.

The contradiction-safe definedness gate is load-bearing:

\[
\mathbb B_t=\varnothing
\Rightarrow
REFUSED(CONTRADICTION),
\]

so universal quantification over an empty admissible set may never create vacuous viability.

External theories used by v0.5—bilattice semantics, metrology, set-membership estimation, hybrid systems, assume-guarantee contracts, multicommodity flow, optional conformal support construction, and capture-basin/reach-avoid theory—remain DSVA dialogue operators. Their external theorems are not automatically Toledo-welded merely because they are cited.


## Governance

DSVA-specific bridge equations remain proposals until separately reviewed/registered in Toledo. FloodConnect may execute, falsify, and refine them as proposal theory without promoting them to registered Toledo mathematics.
