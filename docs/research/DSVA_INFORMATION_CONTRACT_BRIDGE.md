# DSVA Information-Contract Bridge
## Absorbing external leak-closing theories into the FloodConnect / Toledo universe

**Date:** 2026-10-01  
**Status:** DSVA theory synthesis / proposal  
**Root rule:** no external theory becomes a new root ontology. Every imported idea must enter as a declared operator, solver, contract semantics, or special case inside DSVA/Toledo.

# 1. Why this bridge exists

The brutal DSVA v0.4 red-team exposed a narrow set of closure defects rather than a failure of the central viability architecture:

1. an empty admissible-state set can make universal viability vacuously true;
2. evidence admission was weaker than the older FloodConnect QC layer;
3. unit/datum compatibility was stored but not made a readout gate;
4. forecast-support breach was Boolean even when support is undefined;
5. hazard-induced damage was not yet fully state-closed;
6. local viability could externalize harm outside the modeled boundary;
7. candidate-level lifeline feasibility could oversubscribe a shared edge;
8. recovery was operationally present but needed a stronger formal bridge to reachability/capture-basin theory.

The repair strategy is **not** to append eight unrelated theories. The repair is to translate the useful parts of those theories into one information-to-action bridge.

# 2. One bridge, six contracts

For a declared task reader \(Q\), define the DSVA information-contract bridge:

\[
\boxed{
\mathfrak C_t^Q
=
\left(
C_E^Q,\,
C_S^Q,\,
C_T^Q,\,
C_B^Q,\,
C_N^Q,\,
C_R^Q
\right)
}
\tag{ICB-01}
\]

where \(C_E^Q\) is the evidence contract, \(C_S^Q\) state sufficiency, \(C_T^Q\) transition/hybrid damage, \(C_B^Q\) boundary/assume-guarantee, \(C_N^Q\) shared network capacity, and \(C_R^Q\) recovery/re-entry.

\[
\boxed{
E_{\le t}
\xrightarrow{C_E^Q}
(\sigma_Q,\mathbb B_t)
\xrightarrow{C_S^Q,C_T^Q}
\mathcal R_H
\xrightarrow{C_B^Q,C_N^Q}
\{\Pi_H^{EB},\Pi_H^{REC}\}
\xrightarrow{O_Q}
Action/Recovery.
}
\tag{ICB-02}
\]

This is not a new ontology. It is a closure layer over the existing DSVA spine.

# 3. Contradiction-safe information status

Belnap-style four-valued / bilattice semantics are useful because they separate positive support, negative support, contradiction, and absence of information. DSVA absorbs only this information-status idea.

For proposition/readout predicate \(p\) under task \(Q\):

\[
\boxed{
\sigma_Q(p)
=
(s_Q^+(p),s_Q^-(p))
\in\{0,1\}^2.
}
\tag{ICB-03}
\]

| Pair | DSVA status |
|---|---|
| \((0,0)\) | UNRESOLVED |
| \((1,0)\) | SUPPORTED |
| \((0,1)\) | REFUTED |
| \((1,1)\) | CONTRADICTION |

This is a task/readout status, not a replacement for \(\mathbb B_t\).

\[
\boxed{
Status(\mathbb B_t)
=
\begin{cases}
CONTRADICTION,&\mathbb B_t=\varnothing,\\
CONSISTENT,&\mathbb B_t\neq\varnothing.
\end{cases}
}
\tag{ICB-04}
\]

\[
\boxed{
Defined\!\left(\Pi_H^{EB}(\mathbb B_t)\right)
\iff
Status(\mathbb B_t)=CONSISTENT.
}
\tag{ICB-05}
\]

The same definedness gate applies to \(T_V\), \(\Pi_H^{REC}\), and VOI.

\[
\boxed{
\mathbb B_t=\varnothing
\Rightarrow
REFUSED(CONTRADICTION).
}
\tag{ICB-06}
\]

External role: bilattice / paraconsistent information semantics enters as an OPERATOR on readout status, not as root state dynamics.

# 4. Evidence contract: metrology + set-membership + FloodConnect QC

The International Vocabulary of Metrology distinguishes metrological traceability, comparability, compatibility, and measurement uncertainty. Traceability alone does not prove uncertainty is adequate for a particular purpose.

Set-membership estimation contributes a complementary idea: retain the set of states or parameters consistent with bounded model and measurement uncertainty, and use feasibility as a consistency test.

For evidence item \(E_j\) and reader \(Q\):

\[
\boxed{
C_E^Q(E_j)
=
\left(
TypeOK,\,
ProvenanceOK,\,
Active,\,
Fresh,\,
QualityOK,\,
Compatible_Q
\right).
}
\tag{ICB-07}
\]

\[
\boxed{
Compatible_Q(E_j)
=
UnitOK_Q
\land
DatumOK_Q
\land
SpatialSupportOK_Q
\land
TemporalSupportOK_Q
\land
MeasurementModelOK_Q.
}
\tag{ICB-08}
\]

\[
\boxed{
Admit_Q(E_j)
=
\bigwedge C_E^Q(E_j).
}
\tag{ICB-09}
\]

The evidence tuple must carry, directly or by referenced source contract:

\[
\boxed{
E_j
=
\langle
id,source,agency,type,variable,value,unit,support,datum,
t_{obs},t_{pub},I^{valid},
uncertainty,quality,lineage,calibration
\rangle.
}
\tag{ICB-10}
\]

Calibration may be UNKNOWN; it is never fabricated.

\[
\boxed{
\mathbb B_t^+
=
\left\{
\chi\in\mathbb B_t^-:
\chi\text{ satisfies all admitted evidence constraints for }Q
\right\}.
}
\tag{ICB-11}
\]

If \(\mathbb B_t^+=\varnothing\), the result is CONTRADICTION, not an average.

External roles: metrology enters as an evidence-compatibility boundary; set-membership estimation enters as an estimator/consistency operator.

# 5. State-sufficiency contract

v0.4 introduced damage state \(D_t\), but the joint state still listed only \((G_t,X_t,Z_t,\Theta_t,\Gamma_t)\). If evolution depends on hidden \(D_t\), the state is not closed.

\[
\boxed{
\bar\chi_t
=
(G_t,X_t,Z_t,\Theta_t,\Gamma_t,D_t).
}
\tag{ICB-12}
\]

If a later implementation proves \(D_t\) is fully encoded in \(G_t\) or \(\Theta_t\), a reduction may remove the duplicate coordinate. Until then it remains explicit.

A state representation is sufficient for task \(Q\) over horizon \(H\) when:

\[
\boxed{
\bar\chi_t=\bar\chi'_t
\Rightarrow
O_Q(F^k(\bar\chi_t,u,w))
=
O_Q(F^k(\bar\chi'_t,u,w))
\quad
\forall k\le H
}
\tag{ICB-13}
\]

for admitted control/disturbance continuations.

If this fails, the state must be augmented before the reader can claim a closed forecast/action theorem. This is the DSVA information-language version of a sufficient/Markov state, welded to Toledo reader equivalence.

# 6. Transition contract: hybrid-system closure

Hybrid-system theory handles continuous dynamics together with discrete mode changes, guards, jumps, and failures. DSVA absorbs the flow/jump distinction rather than importing hybrid automata as a second ontology.

\[
\boxed{
X_{t+\Delta t}
\in
F_{G_t}(X_t,u_t,w_t;\Theta_t)
\oplus\Xi_t.
}
\tag{ICB-14}
\]

\[
\boxed{
D_{t+1}
\in
\mathcal D(D_t,G_t,X_t,w_t^G,u_t).
}
\tag{ICB-15}
\]

\[
\boxed{
G_{t+1}
=
\mathcal T_G(G_t,D_{t+1},u_t^S).
}
\tag{ICB-16}
\]

The old no-damage topology equation is recovered when:

\[
\boxed{
D_{t+1}=D_t
\land
HazardTopologyEffect=0.
}
\tag{ICB-17}
\]

External role: hybrid systems enters as TRANSITION OPERATOR / SPECIAL-CASE LIBRARY.

# 7. Forecast-support contract: three-valued, calibrator-optional

A forecast may be quantitative with a licensed prediction set, categorical, point-valued without calibrated support, or outside its calibration domain. A Boolean inside/outside reader is therefore too strong.

\[
\boxed{
SupportStatus_{j,t}
=
\begin{cases}
UNRESOLVED,
&\mathcal S_{j,t}^{fcst}\text{ unavailable/incompatible},\\
WITHIN\_SUPPORT,
&Y_t^{obs}\in\mathcal S_{j,t}^{fcst},\\
SUPPORT\_BREACH,
&Y_t^{obs}\notin\mathcal S_{j,t}^{fcst}.
\end{cases}
}
\tag{ICB-18}
\]

If support is breached:

\[
ForecastStatus=OUTSIDE\_CALIBRATED\_RANGE.
\tag{ICB-19}
\]

If support is unknown, the answer remains UNRESOLVED.

Conformal prediction may be inserted as an optional PARAMETERIZATION/SOLVER for constructing prediction sets only when its calibration assumptions are licensed. DSVA does not assume conformal validity under distribution shift.

# 8. Boundary contract: assume-guarantee closure

Assume-guarantee theory gives a formal way to reason about interconnected components: a component guarantees behavior only under declared assumptions about its environment, and global claims require compatible composition.

For subsystem \(i\):

\[
\boxed{
C_{B,i}^Q
=
(A_i^Q,G_i^Q)
}
\tag{ICB-20}
\]

where \(A_i^Q\) contains assumptions on boundary inflow/outflow, receiving levels, neighboring capacity, support arrival or institutional action, and \(G_i^Q\) contains the local guarantees.

\[
\boxed{
Env_i\models A_i^Q
\Rightarrow
Sys_i\models G_i^Q.
}
\tag{ICB-21}
\]

Global composition requires:

\[
\boxed{
\bigwedge_i G_i^Q
\Rightarrow
\bigwedge_i A_i^Q
\quad
\text{on shared boundary variables}.
}
\tag{ICB-22}
\]

For action \(u\), define:

\[
\boxed{
BoundaryClosed_Q(u)=1
}
\tag{ICB-23}
\]

only when every material effect is either inside the modeled domain or exported through a verified neighbor contract.

\[
\boxed{
\neg BoundaryClosed_Q(u)
\Rightarrow
ClaimScope=LOCAL/PARTIAL.
}
\tag{ICB-24}
\]

External role: assume-guarantee theory enters as COMPOSITION / BOUNDARY OPERATOR.

# 9. Shared network-capacity contract

Current LCF can correctly prove one provider/path candidate feasible while two simultaneous candidates overload one shared edge. This is the difference between candidate feasibility and joint allocation.

For support/evacuation commodity \(k\) and edge \(e\), let \(f_{k,e}(t)\) be allocated flow.

\[
\boxed{
\sum_k f_{k,e}(t)
\le
C_e^{eff}(t)
\quad\forall e.
}
\tag{ICB-25}
\]

\[
\boxed{
\sum_{e\in\delta^-(v)}f_{k,e}
-
\sum_{e\in\delta^+(v)}f_{k,e}
=
b_{k,v}.
}
\tag{ICB-26}
\]

Existing TDLC supply constraints remain:

\[
\sum_g y_{p\to g,e}
\le
S_{p,e}.
\tag{ICB-27}
\]

\[
\boxed{
CandidateFeasible
\not\Rightarrow
JointAllocationFeasible.
}
\tag{ICB-28}
\]

A multicommodity/time-expanded flow solver may be inserted as a SOLVER under TDLC/LCF. It does not replace the community/support ontology.

# 10. Recovery contract: capture-basin interpretation

Viability theory already contains capture-basin / reach-avoid ideas: states from which a target can be reached while respecting constraints. DSVA-R11 already expressed this in disaster language; the bridge makes the reduction explicit.

\[
\boxed{
\mathfrak C_H^{REC}
=
\left\{
\mathbb B:
\exists\pi\;
\forall\chi\in\mathbb B,\forall w,\;
\exists\tau\le H:
\begin{array}{l}
\chi_s^\pi\in\mathcal K^{life}
\;\forall s\in[t,t+\tau],\\
\chi_{t+\tau}^\pi\in\mathcal K
\end{array}
\right\}.
}
\tag{ICB-29}
\]

\[
\boxed{
\mathbb B_t\in\mathfrak C_H^{REC}
\iff
\Pi_H^{REC}(\mathbb B_t)\neq\varnothing.
}
\tag{ICB-30}
\]

When \(\mathbb B_t=\{\chi_t\}\), this reduces to a robust capture-basin/reach-avoid problem.

External role: capture-basin / reach-avoid theory enters as SPECIAL CASE / SOLVER for DSVA recoverability.

# 11. The whole bridge in information language

\[
\boxed{
\begin{array}{c}
\textbf{Evidence}\\
E_{\le t}
\end{array}
\xrightarrow[\text{metrology + QC}]{C_E^Q}
\begin{array}{c}
\textbf{Information}\\
(\sigma_Q,\mathbb B_t)
\end{array}
\xrightarrow[\text{sufficiency + hybrid dynamics}]{C_S^Q,C_T^Q}
\begin{array}{c}
\textbf{Possible Futures}\\
\mathcal R_H
\end{array}
\xrightarrow[\text{assume-guarantee + shared capacity}]{C_B^Q,C_N^Q}
\begin{array}{c}
\textbf{Viable / Recoverable Policies}\\
\Pi_H^{EB},\Pi_H^{REC}
\end{array}
\xrightarrow[\text{Toledo task reader}]{O_Q}
\begin{array}{c}
\textbf{Action / HOLD / Recovery}
\end{array}
}
\tag{ICB-31}
\]

The closure conditions are:

\[
\boxed{
\begin{aligned}
InformationClosure &: \mathbb B_t\neq\varnothing\text{ or REFUSE},\\
EvidenceClosure &: Admit_Q\text{ includes QC + compatibility},\\
StateClosure &: \bar\chi_t\text{ is reader-sufficient},\\
TransitionClosure &: \text{damage/topology jumps are in the transition law},\\
BoundaryClosure &: \text{material externalities are inside domain/contracts},\\
CapacityClosure &: \text{simultaneous flows obey shared capacities},\\
RecoveryClosure &: \text{re-entry into }\mathcal K\text{ is reachable under }\mathcal K^{life}.
\end{aligned}
}
\tag{ICB-32}
\]

A strong DSVA safety/viability claim is licensed only under the closures relevant to its reader.

# 12. External-theory placement

| External theory / discipline | What DSVA absorbs | Role inside DSVA | What DSVA does not import |
|---|---|---|---|
| Belnap / bilattice logic | supported / refuted / contradiction / unresolved | OPERATOR on information status | no replacement of \(\mathbb B_t\) or Toledo root |
| JCGM/VIM metrology | traceability, comparability, compatibility, uncertainty discipline | EVIDENCE CONTRACT | no assumption that official/calibrated means fit-for-purpose |
| set-membership estimation | feasible-state consistency under bounded uncertainty | ESTIMATOR | no forced probabilistic model |
| hybrid systems | continuous flow + discrete damage/mode jumps | TRANSITION OPERATOR | no second system ontology |
| conformal prediction | optional calibrated prediction-set builder | PARAMETERIZATION/SOLVER | no automatic validity under distribution shift |
| assume-guarantee contracts | local assumptions, guarantees, compositional closure | BOUNDARY OPERATOR | no local-to-global promotion without discharged assumptions |
| multicommodity flow | joint shared-edge capacity allocation | SOLVER under TDLC/LCF | no replacement of support semantics |
| viability capture basin / reach-avoid | re-entry while respecting emergency constraints | SPECIAL CASE / SOLVER | no collapse of human/service viability into physical reachability |

# 13. Source anchors

- Jakl, T. (2026), Four Imprints of Belnap's Useful Four-Valued Logic in Computer Science, Studia Logica. https://doi.org/10.1007/s11225-026-10230-3
- Fitting, M. (1991), Bilattices and the Semantics of Logic Programming, Journal of Logic Programming 11(2), 91–116. https://doi.org/10.1016/0743-1066(91)90014-G
- JCGM VIM 2.41 metrological traceability: https://jcgm.bipm.org/vim/en/2.41.html
- JCGM VIM 2.46 metrological comparability: https://jcgm.bipm.org/vim/en/2.46.html
- JCGM VIM index including 2.47 metrological compatibility: https://jcgm.bipm.org/vim/en/index.html
- Tornil-Sin et al. (2012), Robust fault detection of non-linear systems using set-membership state estimation based on constraint satisfaction, Engineering Applications of Artificial Intelligence 25(1), 1–10. https://doi.org/10.1016/j.engappai.2011.07.007
- Goebel, Sanfelice & Teel (2009), Hybrid Dynamical Systems, IEEE Control Systems Magazine 29(2), 28–93. https://doi.org/10.1109/MCS.2008.931718
- Saoud, Girard & Fribourg (2021), Assume-guarantee contracts for continuous-time systems, Automatica 134, 109910. https://doi.org/10.1016/j.automatica.2021.109910
- Viability / capture-basin background: https://viability-theory.org/index.php/en/basic-principles
- Reach-avoid / capture-basin characterization: https://www.sciencedirect.com/science/article/pii/S0005109816300966
- Multicommodity-flow shared-edge-capacity example: https://link.springer.com/article/10.1007/s00446-024-00460-w
- Zou & Liu (2024), Coverage-Guaranteed Prediction Sets for Out-of-Distribution Data, arXiv:2403.19950.

# 14. Status

The v0.5 bridge repairs first-order formal language and theory placement. v0.6 adds a second-order license envelope in `docs/research/DSVA_SECOND_ORDER_LICENSE.md` after adversarial tests showed first-order closure alone is insufficient. It does not claim that every FloodConnect source is metrologically traceable, every forecast has calibrated support, every topology-failure mode is enumerated, shared-flow allocation is already implemented in LCF, every local DSVA guarantee composes globally, or the DSVA-specific bridge equations are registered Toledo equations.

Where an obligation is absent, the correct state remains UNKNOWN, UNRESOLVED, LOCAL/PARTIAL, or HOLD.


# 15. v0.6 second-order continuation: closure claims need a license envelope

The v0.5 bridge closes first-order semantic gaps, but the second-order red-team showed that all seven closures can pass while the action is still wrong.

The bridge is therefore extended, not replaced.

First-order closure:

\[
FOC_t^Q
=
\bigwedge\mathfrak C_t^Q.
\]

Second-order meta-contract:

\[
\boxed{
\mathfrak M_t^Q
=
(
M_A^Q,
M_D^Q,
M_Z^Q,
M_X^Q,
M_K^Q,
M_V^Q
).
}
\]

The strong envelope-relative license is:

\[
\boxed{
License_t^Q(a)
=
FOC_t^Q
\land
\bigwedge\mathfrak M_t^Q
\land
a\in\mathcal A_H^{EB}(\mathbb B_t).
}
\]

The detailed formalization is:

docs/research/DSVA_SECOND_ORDER_LICENSE.md

The six meta-contracts are:

1. **Applicability** — the current context lies inside the declared applicability envelope and the load-bearing model family has not been invalidated by retained compatible behavior.
2. **Dependency** — common calibration ancestry, cross-graph shared resources and compound-hazard interactions are represented or remain unresolved.
3. **Realizability** — load-bearing contracts are dynamically realizable, adaptive policies remain defined under admitted observation-channel failures, and recovery reaches a persistent return set rather than touching normal viability for one instant.
4. **Execution** — action latency fits inside a declared action lease and commanded action is not equated with realized actuation without verification.
5. **Requirement** — the protected population/entities and load-bearing human/service requirements are represented in the viability set at the claimed scope.
6. **Verification** — executable solver/readout results pass an independent checker, decision uncertainty does not straddle the categorical output, and horizon/scope/assumptions survive rendering.

The resulting bridge is:

\[
\boxed{
Occurrence
\rightarrow
Evidence
\rightarrow
\mathfrak C_t^Q
\rightarrow
InformationState
\rightarrow
PossibleFutures
\rightarrow
\mathfrak M_t^Q
\rightarrow
Viable/RecoverablePolicy
\rightarrow
VerifiedReadout
\rightarrow
LeasedAction
\rightarrow
RuntimeFeedback.
}
\]

The constitutional distinction is:

\[
\boxed{
Computable
\neq
InternallyClosed
\neq
DecisionLicensed
\neq
TrueInAllPossibleWorlds.
}
\]

Model-invalidation, covariance-intersection/unknown-correlation fusion, contract realizability, runtime assurance, requirements traceability, controlled-invariant return sets and proof/certificate checking enter only as narrow operators inside this continuation of the same DSVA/Toledo bridge.
