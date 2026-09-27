# Audit — THA008 clean prospective test threshold invalidation

This audit does NOT alter the locked prediction in
`experiments/2026-09-27-tha008-clean-prospective.md`.

## New finding

The assumed fixed physical bank threshold of 1.95 m is not adequately supported by the
available FloodWatch alert records.

Observed alert-history examples for THA008 include:

- 26 Sep 2026 03:05 — 1.78 m (98%) displayed under an alert classified as
  "ระดับน้ำถึงเกณฑ์ / ล้นตลิ่ง".
- 27 Sep 2026 16:55 — 1.93 m (100%) displayed under
  "แนวโน้มถึงตลิ่งใน 24 ชม." rather than a consistent over-bank state.

These combinations are inconsistent with a simple, fixed interpretation:

    percent = stage / bank_stage
    bank_stage = 1.95 m

Therefore:
- 1.95 m MUST NOT be treated as a verified physical bank elevation.
- FloodWatch percentage/alert labels require source-schema inspection before use as a
  hydraulic threshold.
- The locked THA008 prediction remains preserved for provenance, but its scoring criterion
  is methodologically invalid until the bank-threshold semantics are resolved.

## Consequence

The correct current statement is:

    THA008 stage is high / near an alert threshold in the source system,
    but a physically verified "overflow at 1.95 m" prediction cannot be made from the
    currently understood fields.

## Next required work

1. Resolve raw HII station metadata for THA008.
2. Identify the actual reference/bank/warning/critical field definitions and vertical datum.
3. Retrieve raw stage time series independent of FloodWatch derived labels.
4. Only then define a fixed threshold and run a prospective node test.

Simulation: NO.
