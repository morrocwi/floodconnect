#!/usr/bin/env python3
"""Verified operational-resource capability evidence for FloodConnect.

This module does not decide route safety and does not certify shelter safety.
It converts a concrete resource deployment into capability evidence only when
verification, freshness, operability, operator qualification (when required),
capacity adequacy, and planning-horizon adequacy are explicitly declared.
"""

from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_REGISTRY = HERE / "site" / "inputs" / "community" / "operational_tools.yaml"


def load_registry(path: str | Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deployment_capability_evidence(
    deployment: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, dict[str, bool | None]]:
    """Return node-capability evidence from one concrete deployment.

    Tool type provides only *possible* capabilities. No capability is returned when
    hard deployment evidence fails. UNKNOWN evidence is preserved in each capability
    record so downstream fail-closed evaluators can refuse promotion.
    """

    tool_id = deployment.get("tool_id")
    tool = (registry.get("tools") or {}).get(tool_id)
    if not isinstance(tool, dict):
        return {}

    if deployment.get("verified") is False or deployment.get("operable") is False:
        return {}

    if tool.get("requires_qualified_operator") is True:
        if deployment.get("operator_qualified") is not True:
            return {}

    record = {
        "verified": deployment.get("verified"),
        "fresh": deployment.get("fresh"),
        "operable": deployment.get("operable"),
        "capacity_ok": deployment.get("capacity_ok"),
        "horizon_ok": deployment.get("horizon_ok"),
    }

    return {
        capability: dict(record)
        for capability in (tool.get("node_effect") or [])
    }


def merge_capability_evidence(
    deployments: list[dict[str, Any]],
    registry: dict[str, Any],
) -> dict[str, dict[str, bool | None]]:
    """Merge deployments conservatively.

    For each capability, one fully confirmed deployment is enough to provide confirmed
    evidence. Otherwise the first unresolved candidate remains unresolved. Explicitly
    failed deployments provide no credit.
    """

    merged: dict[str, dict[str, bool | None]] = {}
    for deployment in deployments:
        evidence = deployment_capability_evidence(deployment, registry)
        for capability, record in evidence.items():
            complete = all(record.get(k) is True for k in (
                "verified", "fresh", "operable", "capacity_ok", "horizon_ok"
            ))
            prior = merged.get(capability)
            prior_complete = prior is not None and all(prior.get(k) is True for k in (
                "verified", "fresh", "operable", "capacity_ok", "horizon_ok"
            ))
            if complete or prior is None or not prior_complete:
                merged[capability] = record
    return merged
