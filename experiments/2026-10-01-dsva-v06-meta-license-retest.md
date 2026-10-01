# DSVA v0.6 second-order license retest

**Date:** 2026-10-01  
**Simulation:** YES — finite synthetic witnesses.  
**Purpose:** rerun the 12 v0.5 second-order attacks against the v0.6 meta-license mapping.  
**Production effect:** NONE.

The executable reference is:

tests/test_dsva_v06_second_order_license.py

The retest does not claim that v0.6 is globally safe. It checks only whether every previously identified attack is now mapped to a load-bearing second-order obligation instead of slipping through after all first-order closures pass.

| v0.5 attack | v0.6 blocking obligation | Expected status |
|---|---|---|
| true world outside declared model/support | applicability / model invalidation | HOLD / CONDITIONAL |
| common-mode sensor bias | dependency lineage / shared latent uncertainty | HOLD |
| circular assume-guarantee | realizability | HOLD |
| advice expires before effect | execution lease | REVALIDATE / HOLD |
| future observation channel fails | policy/observation realizability | fallback or HOLD |
| transient re-entry | persistent return set | not RECOVERED |
| one boat double-booked across graphs | global resource dependency | HOLD |
| vulnerable subgroup omitted | protected requirement coverage | LOCAL/PARTIAL / HOLD |
| solver returns bad plan | independent verification | HOLD |
| uncertainty straddles threshold | categorical reader resolution | UNRESOLVED |
| finite horizon rendered as unqualified SAFE | scope-preserving serialization | HOLD |
| compound hazard interaction omitted | dependency/applicability envelope | CONDITIONAL / HOLD |

The v0.6 test target is intentionally narrower than a proof of correctness:

\[
\boxed{
PreviouslyKnownCounterexample
\Rightarrow
NoStrongLicense
}
\]

not:

\[
\boxed{
StrongLicense
\Rightarrow
SafeInEveryPossibleWorld.
}
\]

The latter is explicitly rejected by SOL-03/SOL-45. The next red-team must search for a **third-order** counterexample: all first-order and all second-order obligations PASS, the claim remains inside its declared envelope, and the independently verified action is still wrong.
