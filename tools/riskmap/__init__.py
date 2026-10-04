"""tools/riskmap -- nationwide sub-basin risk layer (DWR 359 units).

Founder question (verbatim, 2026-09-27): "ทำไงเราถึงจะประเมินแบบ Google ได้นะ" -- this
package builds the honest, DWR-sub-basin-grained equivalent of Google Flood Hub's
county-scale risk view from data this repo already has archived (no new network
requests fired by this package itself).

Toledo: no new equation. Tiering composes the already-documented PROP-FLOOD-06 v5
band/promoter/coverage machinery (see tools/backtest/prop_flood_06_v5.py,
docs/LAYER0_IN_OUT_CAPACITY.md) plus a simple honest gap-comparison against
sources/coping_thresholds.yaml -- marked PARTIAL mode throughout (this package cannot
resolve the FULL 10-component coverage vector for every sub-basin; see
docs/NATIONWIDE_RISK_LAYER_DESIGN.md).

Everything here is a WRITE-ONLY addition (does not edit collect.py,
build_data.py, or build_page.py, and does not commit).
"""
