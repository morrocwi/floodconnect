# DSVA v0.5 second-order red-team
## Can all seven closures PASS while the action is still wrong?

**Date:** 2026-10-01  
**Simulation:** YES — finite synthetic counterexamples.  
**Production effect:** NONE.  
**Baseline:** DSVA v0.5 Information-Contract Bridge on current main.  
**Attack rule:** force all seven v0.5 closure flags to appear PASS, then search for a world in which the licensed action, safety label, or recovery conclusion is still wrong.

The seven first-order closures are:

\[
Information,\ Evidence,\ State,\ Transition,\ Boundary,\ Capacity,\ Recovery.
\]

This red-team asks whether those seven checks are **sufficient**, not merely individually sensible.

# 1. Result

The v0.5 bridge survives the first-order defects found in the previous red-team, but the second-order attack exposes a deeper class:

\[
\boxed{
InternalClosure
\not\Rightarrow
WorldAdequacy.
}
\]

Twelve finite attacks were constructed. All seven v0.5 closure flags are set to PASS in every witness. The action/conclusion can still fail through one of four mechanisms:

1. the modeled world omits a materially possible world;
2. apparently independent contracts/evidence/resources share a hidden dependency;
3. a valid readout loses validity before execution or after transient recovery;
4. the mathematical contract is correct but the declared requirement or executable solver is incomplete.

| # | Attack | v0.5 closures | Outcome | Deep gap |
|---|---|---|---|---|
| 1 | true world lies outside \(\mathbb B/\mathcal W/\mathcal D\) | all PASS | WRONG | applicability / coverage |
| 2 | two good sensors share common-mode bias | all PASS | WRONG | dependency provenance |
| 3 | circular assume-guarantee contracts | all PASS syntactically | WRONG | contract realizability |
| 4 | advice valid at readout, invalid before actuator effect | all PASS at \(t\) | WRONG | execution-time validity |
| 5 | adaptive policy needs future evidence but channel fails | all PASS now | WRONG | observation-policy realizability |
| 6 | system touches \(\mathcal K\) for one instant then exits | all PASS | FALSE RECOVERY | persistent recovery |
| 7 | same boat allocated once in movement and once in support | both graph checks PASS | IMPOSSIBLE | cross-graph resource exclusivity |
| 8 | vulnerable subgroup omitted from \(Z,\mathcal K\) | all formal checks PASS | HARM | requirement/population completeness |
| 9 | solver says feasible but returned plan violates constraints | theory PASS | WRONG IMPLEMENTATION | certificate/verification |
| 10 | point estimate below threshold but uncertainty straddles threshold | evidence PASS | WRONG LABEL | decision-resolution adequacy |
| 11 | SAFE label omits its finite horizon | all PASS over \(H\) | MISLEADING | scope/lease |
| 12 | flood and outage each safe alone; joint interaction omitted | all PASS per factor | WRONG | interaction / joint-support coverage |

The executable witnesses are in:

\`tests/test_dsva_v05_second_order_redteam.py\`

# 2. Attack 1 — closed model, open world

Let the model retain only:

\[
\mathbb B_t=\{\chi^{normal}\}
\]

and let every evidence, state, transition, boundary, capacity and recovery contract pass.

Suppose the actual event is:

\[
\chi^{true}=\chi^{levee\ breach}
\notin\mathbb B_t.
\]

Then a policy can be robust over every modeled world and fail in the real world.

This is not the old empty-set problem. Here:

\[
\mathbb B_t\neq\varnothing
\]

and is internally consistent.

The defect is:

\[
\boxed{
RobustWithinDeclaredSupport
\neq
RobustToReality.
}
\]

**Finding: CRITICAL META-GAP.**

# 3. Attack 2 — individual evidence contracts pass, dependence is wrong

Two sensors can both be:
- official/provenanced;
- fresh;
- quality-approved;
- unit/datum compatible;

and still share the same reference/calibration bias.

Finite witness:

\[
H^{true}=1.20,
\qquad
bias=-0.35,
\]

so both sensors report:

\[
0.85<1.00=H^{crit}.
\]

A naive fusion sees agreement and becomes *more* confident in the wrong state.

The v0.5 evidence contract checks each item but has no explicit **dependence graph** saying both observations inherit one calibration ancestor.

Required concept is not “more sensors” but:

\[
EvidenceIndependence
\neq
SourceCount.
\]

**Finding: HIGH META-GAP.**

# 4. Attack 3 — circular contracts can compose syntactically but realize nothing

Subsystem A:

\[
Power\Rightarrow Pump.
\]

Subsystem B:

\[
Pump\Rightarrow Power.
\]

Their assumptions and guarantees match syntactically, but the actual initial state is:

\[
Power=0,\quad Pump=0.
\]

Nothing bootstraps either service.

Therefore compatibility alone is weaker than **contract realizability**.

A global claim needs a non-circular witness/fixed point, not only matching assumption/guarantee names.

**Finding: CRITICAL BOUNDARY META-GAP.**

# 5. Attack 4 — readout is correct, execution is late

At \(t=0\):

\[
Route=SAFE.
\]

The advice is MOVE. The route becomes unsafe at \(t=5\). The actuator/household reaches the decision point at \(t=10\).

All evidence/state/boundary checks were correct **at readout time**.

The missing object is an action validity interval/lease:

\[
I^{action}_{Q,a}
=
[t^{issue},t^{expire}].
\]

A licensed action must remain licensed at its effective execution time or be revalidated.

**Finding: CRITICAL OPERATIONAL META-GAP.**

# 6. Attack 5 — adaptive policy assumes an observation branch that may not exist

Two hidden worlds require opposite next actions:

\[
x_1\rightarrow OPEN,
\qquad
x_2\rightarrow CLOSE.
\]

The current policy chooses WAIT because the next observation is expected to distinguish the worlds.

If communications/sensor access fails exactly then, the adaptive branch cannot be executed.

Hence:

\[
PolicyExistsGivenFutureEvidence
\not\Rightarrow
PolicyExecutableUnderEvidenceFailure.
\]

Future observation-channel availability must be inside the uncertainty/support quantified by the policy, and the policy must be total on MISSING/UNKNOWN observation branches.

**Finding: CRITICAL POLICY-REALIZABILITY GAP.**

# 7. Attack 6 — transient re-entry is not recovery

DSVA recoverability currently requires existence of \(\tau\) such that:

\[
\chi_{t+\tau}\in\mathcal K.
\]

Counterexample:

\[
OUTSIDE,\ INSIDE,\ OUTSIDE.
\]

The system touches normal viability for one sample and immediately leaves again.

Thus:

\[
Reach(\mathcal K)
\neq
Recover(\mathcal K).
\]

A recovery declaration needs a terminal invariant/dwell condition or a verified robust return set.

**Finding: HIGH RECOVERY META-GAP.**

# 8. Attack 7 — movement and support each pass, but share one physical boat

FloodConnect correctly preserves:

\[
G_{move}\neq G_{support}.
\]

But physical resources can couple the graphs.

If one boat is assigned:
- once for resident evacuation;
- once for medicine delivery;

then both graph-level allocation checks can individually pass while the combined plan requires two boats.

Therefore the non-collapse rule creates a new obligation:

\[
SeparateGraphs
\land
SharedPhysicalResource
\Rightarrow
CrossGraphReservation.
\]

**Finding: HIGH CAPACITY META-GAP.**

# 9. Attack 8 — mathematically viable for the modeled population, harmful to an omitted group

Suppose \(Z_t\) and \(\mathcal K\) omit a bed-bound household, dialysis dependency, animal dependency, or another declared protected requirement.

Every modeled state and boundary can be closed while the action harms the omitted group.

This is not merely system boundary. The people may be physically *inside* the domain but semantically absent from the viability requirements.

Therefore:

\[
\boxed{
StateComplete
\not\Rightarrow
RequirementComplete.
}
\]

**Finding: CRITICAL HUMAN-SYSTEM META-GAP.**

# 10. Attack 9 — correct optimization problem, wrong executable answer

All theory contracts can be correct while a numerical solver, parser, rounding layer, heuristic, or stale cache returns a plan that violates them.

Therefore:

\[
SpecificationSatisfied
\not\Rightarrow
ImplementationSatisfied.
\]

Operational readouts need either:
- an independently checkable feasibility certificate; or
- deterministic post-solve constraint verification.

**Finding: HIGH EXECUTABLE-GAP.**

# 11. Attack 10 — compatible measurement but decision resolution is insufficient

Measurement:

\[
0.99\pm0.05
\]

Threshold:

\[
1.00.
\]

The datum/unit/quality contracts can all pass, yet a point reader emits BELOW THRESHOLD.

But:

\[
[0.94,1.04]
\]

straddles the threshold.

So reader compatibility must include **uncertainty adequacy for the decision margin**, not only measurement-model compatibility.

\[
CompatibleForMeasurement
\not\Rightarrow
ResolvedForDecision.
\]

**Finding: HIGH READER-GAP.**

# 12. Attack 11 — a finite-horizon theorem leaks into an unqualified SAFE label

Suppose the policy is proven safe for six hours and failure occurs at hour seven.

The theorem is correct:

\[
Safe_{[t,t+6]}.
\]

The public/readout label:

\[
SAFE
\]

is misleading if it drops \(H\).

Every reader-relative claim must carry its horizon and assumptions into the rendered/action artifact.

**Finding: HIGH SCOPE-GAP.**

# 13. Attack 12 — independently closed hazards can interact outside the factorized model

Flood alone: safe.

Power outage alone: safe.

Flood + power outage: pump unavailable, route lighting/communications fail, unsafe.

If the disturbance set contains only separate marginals and not their material joint interaction, all component analyses pass.

Therefore:

\[
MarginalCoverage
\neq
JointInteractionCoverage.
\]

This is a special case of open-world/model coverage, but important enough in disaster systems to preserve explicitly.

**Finding: CRITICAL COMPOUND-HAZARD GAP.**

# 14. What survived

The v0.5 bridge still removes the previous first-order failures:

- \(\mathbb B=\varnothing\) cannot create vacuous viability;
- fresh does not imply valid;
- datum/unit support is reader-specific;
- forecast support can remain UNRESOLVED;
- damage state is explicit;
- local claims cannot silently become global if boundary closure is missing;
- candidate feasibility is not joint flow feasibility;
- recoverability is distinct from ordinary viability.

The second-order failures occur **after** those checks report PASS.

# 15. The deeper pattern

The twelve attacks collapse into five meta-closures:

\[
\boxed{
\begin{aligned}
ApplicabilityClosure &: \text{does the admissible model/support still cover the material real world?}\\
DependencyClosure &: \text{are shared causes/resources/interactions represented?}\\
ExecutionClosure &: \text{will the licensed action remain valid and executable when it takes effect?}\\
RequirementClosure &: \text{does }\mathcal K\text{ include every material protected requirement/population?}\\
VerificationClosure &: \text{did the executable implementation actually satisfy the formal contract?}
\end{aligned}
}
\]

Recovery additionally needs persistence:

\[
\boxed{
Recovery
=
Reach\ \mathcal K
+
Remain\ Viable.
}
\]

This suggests the next theory repair should **not** add five new worlds. It should treat these as a second-order contract on the existing bridge:

\[
\boxed{
\text{Closure of the Closure Claims}.
}
\]

A candidate strong-license condition is:

\[
StrongLicense_Q
=
FirstOrderClosure_Q
\land
MetaClosure_Q.
\]

No semantic change is made by this experiment. It records the counterexamples first, preserving the claim-first protocol for any subsequent v0.6 repair.
