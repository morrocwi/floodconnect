#!/usr/bin/env python3
"""
tools/backtest/outside_calibrated_range.py -- OUTSIDE_CALIBRATED_RANGE label (added
2026-09-28, docs/knowledge/card_dual_state_reescalation_hatyai_2026-09-28.md, Hat Yai
Nov 2025 red-team finding H: RID measured ~346-366 mm/24h across several Hat Yai
tributary catchments -- warnings used standard heavy/very-heavy categories, but nothing
in this repo flagged "this exceeds every value we have ever calibrated against for this
unit/variable").

Reuse-first: `sources/coping_thresholds.yaml` already computes, per unit x variable, a
`threshold_flooded_min`/`threshold_coped_max`/`design` via plain min/max over cited rows
(that file's own header: "arithmetic, not a registered formula"). This module does the
SAME kind of plain comparison -- observed_value vs the highest calibrated value already
on file for that exact unit x variable -- and returns a LABEL, never a new number, never
a depth/severity estimate, never a Toledo equation. No cross-basin comparison is made
anywhere in this module (comparing e.g. Hat Yai rainfall against a Bangkok threshold is
the exact mistake docs/knowledge/card_thirdparty_hatyai_redteam_2025-11_review_2026-09-27.md
TODOLIST #15 warns against) -- a unit with no calibrated ceiling on file returns OPEN,
never a guess borrowed from a different unit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
COPING_THRESHOLDS_PATH = REPO_ROOT / "sources" / "coping_thresholds.yaml"

LABEL_OUTSIDE = "OUTSIDE_CALIBRATED_RANGE"
LABEL_WITHIN = "WITHIN_CALIBRATED_RANGE"
LABEL_OPEN = "OPEN"  # no calibrated ceiling on file for this unit x variable


def load_derived(path: Path = COPING_THRESHOLDS_PATH) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load coping_thresholds.yaml")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("derived") or {}


def highest_calibrated_value(entry: dict[str, Any]) -> float | None:
    """Highest of threshold_flooded_min/threshold_coped_max/design already on file for
    one unit x variable entry -- plain max(), not a formula."""
    vals: list[float] = []
    for key in ("threshold_flooded_min", "threshold_coped_max", "design"):
        cell = entry.get(key)
        if isinstance(cell, dict) and cell.get("value") is not None:
            try:
                vals.append(float(cell["value"]))
            except (TypeError, ValueError):
                continue
    return max(vals) if vals else None


def classify_outside_calibrated_range(
    unit: str, variable: str, observed_value: float, derived: dict[str, Any] | None = None,
) -> str:
    """Returns LABEL_OUTSIDE / LABEL_WITHIN / LABEL_OPEN. Never computes a depth/severity
    estimate -- this is a plain greater-than comparison against an already-computed
    ceiling, exactly like coping_thresholds.yaml's own derived block."""
    if derived is None:
        derived = load_derived()
    entry = (derived.get(unit) or {}).get(variable)
    if not entry:
        return LABEL_OPEN
    ceiling = highest_calibrated_value(entry)
    if ceiling is None:
        return LABEL_OPEN
    return LABEL_OUTSIDE if observed_value > ceiling else LABEL_WITHIN
