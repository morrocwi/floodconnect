"""tools/api — FloodConnect API v1 static-export package (read-only, additive).

See tools/api/export_api.py for the generator itself and docs/AI_INTERFACE.md
for the endpoint contract. This package writes site/dist/api/v1/** from
build artifacts that already exist (site/dist/data.json, output/typology_graph.json,
site/inputs/community/self_help_dag.yaml, sources/registry.yaml) -- it never
fetches network data and never calls collect.py.
"""
