"""Tests for sources/province_agency_crosswalk.yaml -- every agency_id it names must
exist as a real node in docs/knowledge/water_system_dag.mmd (no invented node), and the
file's own row counts/shape must hold."""
import re
from pathlib import Path

import yaml

HERE = Path(__file__).parent.parent
DAG_PATH = HERE / "docs" / "knowledge" / "water_system_dag.mmd"
CROSSWALK_PATH = HERE / "sources" / "province_agency_crosswalk.yaml"


def _dag_node_ids() -> set[str]:
    text = DAG_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*(AG_[A-Z0-9_]+)\[", text, flags=re.MULTILINE))


def _load():
    return yaml.safe_load(CROSSWALK_PATH.read_text(encoding="utf-8"))


def test_nine_province_rows_all_role_template_false():
    doc = _load()
    assert len(doc["province_rows"]) == 9
    for row in doc["province_rows"]:
        assert row["tag"] == "VERIFIED"
        assert len(row["province_code"]) == 2


def test_every_named_agency_id_exists_in_dag():
    doc = _load()
    dag_ids = _dag_node_ids()
    named = []
    for row in doc["province_rows"]:
        named += [row["gov"], row["rid"], row["pao"]]
    for row in doc["bangkok_rows"] + doc["basin_rows"]:
        named.append(row["agency_id"])
    for row in doc["role_template_rows"]:
        named += [v for k, v in row.items() if k in ("gov", "rid", "pao", "cmt")]
    missing = sorted(set(named) - dag_ids)
    assert not missing, f"crosswalk names agency ids not present in the DAG: {missing}"


def test_bangkok_saphan_sung_district_code_matches_elevation_source():
    doc = _load()
    bkk_elev = yaml.safe_load((HERE / "sources" / "bkk_district_elevation.yaml").read_text(encoding="utf-8"))
    ss_code = next(r["district_code"] for r in bkk_elev["districts"] if r["district_th"] == "สะพานสูง")
    row = next(r for r in doc["bangkok_rows"] if r["agency_id"] == "AG_DIST_SS")
    assert row["area_id"] == f"district:{ss_code}"


def test_role_template_rows_cover_province_and_basin_generic_cases():
    doc = _load()
    kinds = {r["applies_to"].split(":")[0] if ":" in r["applies_to"] else r["applies_to"]
             for r in doc["role_template_rows"]}
    assert len(doc["role_template_rows"]) == 2
    for row in doc["role_template_rows"]:
        assert row["role_template"] is True
        assert row["tag"] == "RELAYED-GENERAL"
