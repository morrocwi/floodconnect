#!/usr/bin/env python3
"""Validate FloodConnect multi-agent semantic claims.

Claims are persistent YAML files under .ai/claims/. An ACTIVE claim owns canonical
Repo Knowledge Graph (RKG) node IDs. The central invariant is:

    at most one ACTIVE writer per canonical RKG node.

Released claims remain as provenance and do not own nodes.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_CLAIM_DIR = HERE / ".ai" / "claims"
DEFAULT_RKG = HERE / "site" / "inputs" / "meta" / "floodconnect_repo_kg.yaml"

STATUSES = {"ACTIVE", "RELEASED"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(r"^agent/[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+$")


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def canonical_node_ids(rkg_path: str | Path = DEFAULT_RKG) -> set[str]:
    doc = _load_yaml(Path(rkg_path)) or {}
    nodes = doc.get("nodes") or {}
    return set(nodes) if isinstance(nodes, dict) else set()


def claim_files(claim_dir: str | Path = DEFAULT_CLAIM_DIR) -> list[Path]:
    root = Path(claim_dir)
    if not root.exists():
        return []
    return sorted(
        p for p in root.glob("*.yaml")
        if not p.name.startswith("_")
    )


def _valid_iso8601(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip().replace("Z", "+00:00")
    try:
        datetime.fromisoformat(text)
    except ValueError:
        return False
    return True


def validate_claims(
    claim_dir: str | Path = DEFAULT_CLAIM_DIR,
    rkg_path: str | Path = DEFAULT_RKG,
) -> list[str]:
    errors: list[str] = []
    canonical = canonical_node_ids(rkg_path)
    if not canonical:
        errors.append("RKG has no canonical nodes")
        return errors

    seen_ids: dict[str, str] = {}
    active_by_node: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for path in claim_files(claim_dir):
        rel = str(path)
        try:
            claim = _load_yaml(path)
        except Exception as exc:
            errors.append(f"{rel}: cannot parse YAML: {exc}")
            continue

        if not isinstance(claim, dict):
            errors.append(f"{rel}: claim must be a mapping")
            continue

        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            errors.append(f"{rel}: missing claim_id")
            claim_id = f"<missing:{path.name}>"
        else:
            claim_id = claim_id.strip()
            if claim_id in seen_ids:
                errors.append(
                    f"{rel}: duplicate claim_id {claim_id!r}; first seen in {seen_ids[claim_id]}"
                )
            seen_ids[claim_id] = rel
            if path.stem != claim_id:
                errors.append(
                    f"{rel}: filename stem must equal claim_id ({path.stem!r} != {claim_id!r})"
                )

        status = str(claim.get("status") or "").upper()
        if status not in STATUSES:
            errors.append(f"{rel}: status must be one of {sorted(STATUSES)}")

        writer = claim.get("writer")
        if not isinstance(writer, str) or not writer.strip():
            errors.append(f"{rel}: missing writer")

        branch = claim.get("branch")
        if not isinstance(branch, str) or not BRANCH_RE.fullmatch(branch):
            errors.append(
                f"{rel}: branch must match agent/<agent-id>/<task-slug>"
            )

        base_sha = str(claim.get("base_sha") or "").lower()
        if not SHA_RE.fullmatch(base_sha):
            errors.append(f"{rel}: base_sha must be a 40-character lowercase hex SHA")

        nodes = claim.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            errors.append(f"{rel}: nodes must be a non-empty list")
            nodes = []
        elif len(nodes) != len(set(nodes)):
            errors.append(f"{rel}: nodes contains duplicates")

        for node in nodes:
            if node not in canonical:
                errors.append(f"{rel}: unknown canonical RKG node {node!r}")
            if status == "ACTIVE" and node in canonical:
                active_by_node[node].append((claim_id, str(writer)))

        artifacts = claim.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{rel}: artifacts must be a non-empty list")
        elif any(not isinstance(x, str) or not x.strip() for x in artifacts):
            errors.append(f"{rel}: artifacts must contain non-empty repository paths")

        intent = claim.get("intent")
        if not isinstance(intent, str) or not intent.strip():
            errors.append(f"{rel}: missing intent")

        if not _valid_iso8601(claim.get("created_at")):
            errors.append(f"{rel}: created_at must be an ISO-8601 datetime")

        expires_at = claim.get("expires_at")
        if expires_at is not None and not _valid_iso8601(expires_at):
            errors.append(f"{rel}: expires_at must be null or an ISO-8601 datetime")

        reviewers = claim.get("reviewers", [])
        if not isinstance(reviewers, list):
            errors.append(f"{rel}: reviewers must be a list")

    for node, owners in sorted(active_by_node.items()):
        if len(owners) > 1:
            owner_text = ", ".join(f"{cid}({writer})" for cid, writer in owners)
            errors.append(
                f"canonical node {node} has multiple ACTIVE writers: {owner_text}"
            )

    return errors


def active_claims(
    claim_dir: str | Path = DEFAULT_CLAIM_DIR,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in claim_files(claim_dir):
        claim = _load_yaml(path)
        if isinstance(claim, dict) and str(claim.get("status") or "").upper() == "ACTIVE":
            row = dict(claim)
            row["_file"] = str(path)
            out.append(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claims", default=str(DEFAULT_CLAIM_DIR))
    ap.add_argument("--rkg", default=str(DEFAULT_RKG))
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--list", action="store_true", dest="list_active")
    args = ap.parse_args()

    errors = validate_claims(args.claims, args.rkg)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    if args.validate or not args.list_active:
        active = active_claims(args.claims)
        print(f"claims valid: {len(active)} ACTIVE claim(s)")

    if args.list_active:
        for claim in active_claims(args.claims):
            print(
                f"{claim.get('claim_id')} writer={claim.get('writer')} "
                f"nodes={','.join(claim.get('nodes') or [])} branch={claim.get('branch')}"
            )


if __name__ == "__main__":
    main()
