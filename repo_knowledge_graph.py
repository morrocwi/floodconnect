#!/usr/bin/env python3
"""Validate/export the FloodConnect Repo Knowledge Graph (RKG).

Canonical input:
  site/inputs/meta/floodconnect_repo_kg.yaml

Outputs are generated views only:
  output/floodconnect_repo_kg.jsonld
  output/floodconnect_repo_kg.graphml

The YAML remains the source of truth because it also carries AI routing, precedence,
epistemic boundaries and hard non-edges that generic graph formats cannot express well.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


HERE = Path(__file__).resolve().parent
DEFAULT_KG = HERE / "site" / "inputs" / "meta" / "floodconnect_repo_kg.yaml"
DEFAULT_JSONLD = HERE / "output" / "floodconnect_repo_kg.jsonld"
DEFAULT_GRAPHML = HERE / "output" / "floodconnect_repo_kg.graphml"


class RepoKGError(ValueError):
    pass


def load_kg(path: str | Path = DEFAULT_KG) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    if not isinstance(doc, dict):
        raise RepoKGError("RKG root must be a mapping")
    return doc


def validate_kg(doc: dict, repo_root: str | Path = HERE) -> list[str]:
    """Return validation errors; empty list means structurally valid."""

    errors: list[str] = []
    root = Path(repo_root)
    nodes = doc.get("nodes") or {}
    edges = doc.get("edges") or []

    if not isinstance(nodes, dict) or not nodes:
        errors.append("nodes must be a non-empty mapping")
        return errors

    if len(nodes) != len(set(nodes)):
        errors.append("duplicate node ids")

    allowed_kinds = set(doc.get("node_kinds") or [])
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            errors.append(f"{node_id}: node must be a mapping")
            continue
        kind = node.get("kind")
        if kind not in allowed_kinds:
            errors.append(f"{node_id}: unknown kind {kind!r}")
        artifacts = node.get("canonical_artifacts") or []
        for artifact in artifacts:
            if not (root / artifact).exists():
                errors.append(f"{node_id}: missing canonical artifact {artifact}")

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"edge[{idx}] must be a mapping")
            continue
        src = edge.get("from")
        dst = edge.get("to")
        rel = edge.get("relation")
        if src not in nodes:
            errors.append(f"edge[{idx}]: unknown source node {src!r}")
        if dst not in nodes:
            errors.append(f"edge[{idx}]: unknown target node {dst!r}")
        if not rel:
            errors.append(f"edge[{idx}]: missing relation")

    routes = doc.get("question_routes") or {}
    for route_id, route in routes.items():
        if not isinstance(route, dict):
            errors.append(f"question route {route_id}: must be a mapping")
            continue
        refs = list(route.get("start_nodes") or []) + list(route.get("then") or [])
        for ref in refs:
            if ref not in nodes:
                errors.append(f"question route {route_id}: unknown node {ref}")
        for artifact in route.get("read") or []:
            if not (root / artifact).exists():
                errors.append(f"question route {route_id}: missing file {artifact}")

    precedence = doc.get("artifact_precedence") or {}
    for topic, rule in precedence.items():
        if not isinstance(rule, dict):
            continue
        values: list[str] = []
        for value in rule.values():
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, list):
                values.extend(x for x in value if isinstance(x, str))
        for artifact in values:
            # Fragment refs are allowed but current RKG uses repository paths only.
            path = artifact.split("#", 1)[0]
            if path and not (root / path).exists():
                errors.append(f"artifact precedence {topic}: missing file {path}")

    # Governance identity invariant.
    warning = root / "site" / "inputs" / "governance" / "flood_warning_actor_typology.yaml"
    governance = root / "site" / "inputs" / "governance" / "thailand_water_governance_reference.json"
    if warning.exists() and governance.exists():
        with warning.open(encoding="utf-8") as f:
            warning_doc = yaml.safe_load(f) or {}
        with governance.open(encoding="utf-8") as f:
            governance_doc = json.load(f)
        canonical_ids = {
            row.get("id")
            for row in governance_doc.get("verified_anchors", [])
            if isinstance(row, dict) and row.get("id")
        }
        if "actors" in warning_doc:
            errors.append("warning typology duplicates actor identities via top-level actors")
        refs = ((warning_doc.get("canonical_actor_registry") or {}).get("actor_refs") or {})
        for actor_ref in refs:
            if actor_ref not in canonical_ids:
                errors.append(f"warning actor_ref {actor_ref!r} missing from canonical governance registry")

    return errors


def to_jsonld(doc: dict) -> dict:
    nodes = doc.get("nodes") or {}
    graph = []
    for node_id, node in nodes.items():
        item = {
            "@id": f"fc:{node_id}",
            "@type": f"fc:{node.get('kind', 'Node')}",
            "label": node.get("label", node_id),
            "epistemicClass": node.get("epistemic_class"),
            "summary": node.get("summary"),
            "canonicalArtifact": node.get("canonical_artifacts", []),
        }
        graph.append({k: v for k, v in item.items() if v not in (None, [], "")})

    for idx, edge in enumerate(doc.get("edges") or []):
        graph.append({
            "@id": f"fc:edge:{idx}",
            "@type": "fc:Relation",
            "source": {"@id": f"fc:{edge['from']}"},
            "relation": edge["relation"],
            "target": {"@id": f"fc:{edge['to']}"},
        })

    return {
        "@context": {
            "fc": "https://floodconnect.local/kg/",
            "label": "http://www.w3.org/2000/01/rdf-schema#label",
            "source": {"@id": "fc:source", "@type": "@id"},
            "target": {"@id": "fc:target", "@type": "@id"},
        },
        "@graph": graph,
    }


def write_jsonld(doc: dict, path: str | Path = DEFAULT_JSONLD) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(to_jsonld(doc), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def write_graphml(doc: dict, path: str | Path = DEFAULT_GRAPHML) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    ns = "http://graphml.graphdrawing.org/xmlns"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}graphml")

    keys = [
        ("k_label", "node", "label"),
        ("k_kind", "node", "kind"),
        ("k_epistemic", "node", "epistemic_class"),
        ("k_summary", "node", "summary"),
        ("k_relation", "edge", "relation"),
    ]
    for key_id, target, name in keys:
        ET.SubElement(
            root,
            f"{{{ns}}}key",
            id=key_id,
            **{"for": target, "attr.name": name, "attr.type": "string"},
        )

    graph = ET.SubElement(root, f"{{{ns}}}graph", id="FloodConnectRKG", edgedefault="directed")

    for node_id, node in (doc.get("nodes") or {}).items():
        el = ET.SubElement(graph, f"{{{ns}}}node", id=node_id)
        for key_id, field in (
            ("k_label", "label"),
            ("k_kind", "kind"),
            ("k_epistemic", "epistemic_class"),
            ("k_summary", "summary"),
        ):
            value = node.get(field)
            if value is not None:
                data = ET.SubElement(el, f"{{{ns}}}data", key=key_id)
                data.text = str(value)

    for idx, edge in enumerate(doc.get("edges") or []):
        el = ET.SubElement(
            graph,
            f"{{{ns}}}edge",
            id=f"e{idx}",
            source=edge["from"],
            target=edge["to"],
        )
        data = ET.SubElement(el, f"{{{ns}}}data", key="k_relation")
        data.text = edge["relation"]

    ET.ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kg", default=str(DEFAULT_KG))
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--export", action="store_true", help="write JSON-LD and GraphML generated views")
    ap.add_argument("--jsonld", default=str(DEFAULT_JSONLD))
    ap.add_argument("--graphml", default=str(DEFAULT_GRAPHML))
    args = ap.parse_args()

    doc = load_kg(args.kg)
    errors = validate_kg(doc, HERE)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)

    if args.validate or not args.export:
        print(
            f"RKG valid: {len(doc.get('nodes') or {})} nodes, "
            f"{len(doc.get('edges') or [])} edges, "
            f"{len(doc.get('question_routes') or {})} question routes"
        )

    if args.export:
        print(f"wrote {write_jsonld(doc, args.jsonld)}")
        print(f"wrote {write_graphml(doc, args.graphml)}")


if __name__ == "__main__":
    main()
