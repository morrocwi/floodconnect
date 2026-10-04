"""tests/test_api_schema_validity.py -- every generated FloodConnect API v1
file validates against its own schema/*.json, and openapi.yaml parses with
paths matching the file tree 1:1 (acceptance check 1 of the spec)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT))
from tools.api import export_api  # noqa: E402


@pytest.fixture()
def exported(tmp_path):
    out_dir = tmp_path / "api" / "v1"
    export_api.export_api(
        data_json_path=str(FIXTURES / "data_json_sample.json"),
        typology_graph_path=str(FIXTURES / "typology_graph_sample.json"),
        typology_subgraph_dir=str(FIXTURES / "typology_subgraph"),
        self_help_dag_path=str(FIXTURES / "self_help_dag_sample.yaml"),
        sources_registry_path=str(FIXTURES / "sources_registry_sample.yaml"),
        out_dir=str(out_dir),
    )
    return out_dir


TARGETS = [
    ("index.json", "schema/index.schema.json"),
    ("areas/sammakorn.json", "schema/area.schema.json"),
    ("areas/ram53.json", "schema/area.schema.json"),
    ("typology/graph.json", "schema/typology_graph.schema.json"),
    ("typology/subgraph/sammakorn.json", "schema/typology_graph.schema.json"),
    ("community/self_help_dag.json", "schema/self_help_dag.schema.json"),
    ("sources.json", "schema/sources.schema.json"),
]


@pytest.mark.parametrize("data_path,schema_path", TARGETS)
def test_file_validates_against_its_schema(exported, data_path, schema_path):
    data = json.loads((exported / data_path).read_text())
    schema = json.loads((exported / schema_path).read_text())
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    assert not errors, f"{data_path} failed {schema_path}: " + "; ".join(e.message for e in errors)


def test_openapi_parses_and_paths_match_file_tree(exported):
    spec = yaml.safe_load((exported / "openapi.yaml").read_text())
    assert spec["openapi"].startswith("3.")
    assert "/index.json" in spec["paths"]
    index = json.loads((exported / "index.json").read_text())
    for name, template in index["endpoints"].items():
        rel_path = "/" + template.replace("/api/v1/", "")
        assert rel_path in spec["paths"], f"{rel_path} missing from openapi.yaml paths"
