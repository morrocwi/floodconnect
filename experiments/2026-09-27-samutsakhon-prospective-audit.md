# Audit of Samut Sakhon prospective test — 27 Sep 2026

This file audits, but does NOT rewrite, the locked prospective test in
`experiments/2026-09-27-samutsakhon-independent-prospective.md`.

## Finding 1 — "94% of bank" was over-interpreted

The locked file computed:

    headroom_ratio = 1 - 0.94 = 0.06

and described this as ~6% bank headroom.

That interpretation is NOT justified by the alert history. The same THA009 station is
reported with combinations such as:

- 1.00 m (81%)
- 1.00 m (83%)
- 1.40 m (94%)
- 1.46 m (95%)
- 1.49 m (95%)

The percentage therefore cannot safely be treated as a simple linear ratio H/H_bank from
the alert table alone. It may use a threshold transformation, changing metadata, rounding,
or another denominator. Until the FloodWatch percentage definition is inspected directly,
"6% headroom" must be considered INVALID as a physical calculation.

## Finding 2 — the primary prediction was not independent

The alert used as evidence literally said:

    THA009 — "แนวโน้มถึงตลิ่งใน 24 ชม."

Therefore the locked primary statement:

    THA009 will reach/exceed bank by 09:00

was substantially a restatement/narrowing of FloodWatch's own derived alert, not an
independent FloodConnect forecast.

For a clean independent test, FloodConnect must use the raw historical stage series
itself (e.g. dH/dt, tidal decomposition, upstream propagation) and must NOT use the
derived "24 h to bank" alert as an input feature.

## Finding 3 — urban road flooding was not derived

The secondary statement predicting road/community inundation 04:00–10:00 was not
mathematically supported by the declared inputs.

To derive an urban-road outcome, at minimum one needs some combination of:

- local road/ground elevations in a compatible datum;
- river/canal water-surface forecast or stage-transfer relation;
- local drainage/outfall/gate/pump state;
- river-to-drainage-network hydraulic connectivity;
- observed threshold linking river stage to road inundation.

None was declared for the target.

Thus the correct hierarchical output at lock time should have been:

    NODE: WATCH / HIGH-STAGE PRESSURE
    URBAN ROAD FLOOD: UNRESOLVED

not a positive urban-flood prediction.

## Finding 4 — tide datum cannot be subtracted directly

The cited tide-table value (e.g. 3.13 m) cannot be directly combined with THA009's stage
without confirming common vertical datum and a stage-transfer relation. It is valid only
as a qualitative downstream-boundary timing signal.

## Corrected scientific posture

The original locked forecast remains preserved for scoring (no hindsight edits), but it
must be classified as a **methodological overreach**.

A clean next prospective test should:

1. exclude all precomputed flood/near-bank forecast labels from input;
2. use only raw stage/rain/tide series available before lock;
3. fit or derive a transparent propagation/trend calculation;
4. predict a measurable node outcome first;
5. only predict urban road inundation after a declared stage-to-road relation exists.

This audit is itself timestamped in Git history and must not be used to retroactively
change the original score.
