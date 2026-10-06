"""Tests for `advice/gap_log.py` -- the M8 P-B policy_gap_record append-only writer.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_gap_log.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import advice.gap_log as gap_log  # noqa: E402


def test_log_gap_appends_one_line_per_call(tmp_path):
    path = tmp_path / "gap_log.jsonl"
    assert not path.exists()
    ref1 = gap_log.log_gap(blockers=["B1"], run_at="2026-10-05T10:00:00Z",
                            sensors=["WL.TEST.01"], path=path)
    ref2 = gap_log.log_gap(blockers=["B2"], run_at="2026-10-05T11:00:00Z",
                            sensors=["WL.TEST.02"], outlet_bottleneck="WL.OUT.01",
                            responsible_agency="ปภ.", path=path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    row1, row2 = json.loads(lines[0]), json.loads(lines[1])
    assert row1["record_id"] == ref1["record_id"]
    assert row2["record_id"] == ref2["record_id"]
    assert row1["record_id"] != row2["record_id"]
    assert row1["blockers"] == ["B1"]
    assert row2["outlet_bottleneck"] == "WL.OUT.01"


def test_append_never_rewrites_earlier_lines(tmp_path):
    """The module must only ever open the file with mode 'a' -- an earlier append's
    bytes must be byte-identical and still present (not rewritten/reordered) after a
    later append (the task's own rule: 'it only ever opens the file with "a" and
    never rewrites it')."""
    path = tmp_path / "gap_log.jsonl"
    gap_log.log_gap(blockers=["B1"], run_at="2026-10-05T10:00:00Z", path=path)
    before = path.read_text(encoding="utf-8")
    gap_log.log_gap(blockers=["B2"], run_at="2026-10-05T11:00:00Z", path=path)
    after = path.read_text(encoding="utf-8")
    assert after.startswith(before)
    assert len(after.splitlines()) == 2


def test_record_id_is_deterministic_for_identical_content():
    rec_a = gap_log.build_record(["X"], "2026-10-05T00:00:00Z", sensors=["A"])
    rec_b = gap_log.build_record(["X"], "2026-10-05T00:00:00Z", sensors=["A"])
    assert rec_a["record_id"] == rec_b["record_id"]
    rec_c = gap_log.build_record(["Y"], "2026-10-05T00:00:00Z", sensors=["A"])
    assert rec_c["record_id"] != rec_a["record_id"]


def test_record_id_excludes_itself_from_its_own_hash_input():
    rec = gap_log.build_record(["X"], "2026-10-05T00:00:00Z", sensors=["A"])
    base = {k: v for k, v in rec.items() if k != "record_id"}
    import hashlib
    expected = hashlib.sha256(
        json.dumps(base, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert rec["record_id"] == expected


def test_logged_record_validates_against_policy_gap_record_schema(tmp_path):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    schema_dir = HERE / "schemas"
    resources = {f.name: Resource.from_contents(json.loads(f.read_text()))
                 for f in schema_dir.glob("*.schema.json")}
    registry = Registry().with_resources(resources.items())
    validator = Draft202012Validator(
        resources["policy_gap_record.schema.json"].contents, registry=registry)

    path = tmp_path / "gap_log.jsonl"
    ref = gap_log.log_gap(blockers=["OUTLET_CRITICAL"], run_at="2026-10-05T10:00:00Z",
                           sensors=["WL.SSB.08"], outlet_bottleneck="WL.SSB.08",
                           responsible_agency=None, path=path)
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["record_id"] == ref["record_id"]
    errors = list(validator.iter_errors(row))
    assert not errors, [str(e) for e in errors]
