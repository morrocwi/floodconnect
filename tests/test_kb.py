"""Tests for kb.py -- stdlib-only knowledge query tool. No network calls.

Uses the repo's real files under docs/ and sources/registry.yaml as fixtures (this tool
has nothing else to index), but every test skips gracefully if a fixture file this repo
happens not to have right now is absent, per the task's own instruction not to hard-fail
on repo state this test file doesn't own.
"""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
KB = HERE / "kb.py"
QUESTION_BANK = HERE / "docs" / "knowledge" / "WATER_MANAGER_QUESTION_BANK.md"

sys.path.insert(0, str(HERE))
import kb  # noqa: E402


def run_kb(*args):
    result = subprocess.run(
        [sys.executable, str(KB), *args],
        cwd=HERE, capture_output=True, text=True, timeout=30, check=False,
    )
    return result


@pytest.fixture
def _index_yaml_restored():
    """`kb.py reindex` runs as a subprocess and writes the real, git-tracked
    docs/knowledge/INDEX.yaml -- a module-level monkeypatch of kb.INDEX_PATH in this
    process does not reach that subprocess. Snapshot the file's real bytes (or its
    absence) before the test and restore them after, so running this test never leaves
    the tracked file dirty (real data only in tests, never a side effect on a tracked
    file)."""
    path = kb.INDEX_PATH
    before = path.read_bytes() if path.exists() else None
    try:
        yield path
    finally:
        if before is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(before)


def test_find_known_term():
    if not (HERE / "docs").is_dir():
        pytest.skip("docs/ not present")
    result = run_kb("find", "readout")
    assert result.returncode == 0
    assert "readout" in result.stdout.lower() or "no matches" in result.stdout.lower()
    # docs/DATA_SYSTEM.md or similar should mention "readout" somewhere -- if docs/ has
    # any content at all this should not be the empty-match branch.
    if any(HERE.glob("docs/**/*.md")):
        assert ".md:" in result.stdout


def test_find_thai_safe():
    if not (HERE / "docs").is_dir():
        pytest.skip("docs/ not present")
    result = run_kb("find", "น้ำ")
    assert result.returncode == 0
    # Should not crash on non-ASCII input, and should find at least one line in a repo
    # this heavily documented in Thai.
    assert "Traceback" not in result.stderr


def test_ask_known_id():
    if not QUESTION_BANK.exists():
        pytest.skip("WATER_MANAGER_QUESTION_BANK.md not present")
    text = QUESTION_BANK.read_text(encoding="utf-8")
    m = kb.QID_RE.search(text)
    if not m:
        pytest.skip("no question id found in the bank file")
    qid = m.group(0)
    result = run_kb("ask", qid)
    assert result.returncode == 0
    assert qid in result.stdout


def test_ask_unknown_id_no_crash():
    result = run_kb("ask", "Q-NOPE-999")
    assert result.returncode == 0
    assert "not found" in result.stdout


def test_status_runs():
    if not QUESTION_BANK.exists():
        pytest.skip("WATER_MANAGER_QUESTION_BANK.md not present")
    result = run_kb("status")
    assert result.returncode == 0
    assert result.stdout.strip() != ""


def test_reindex_produces_valid_yaml_with_min_entries(_index_yaml_restored):
    if not (HERE / "docs").is_dir():
        pytest.skip("docs/ not present")

    # Run reindex against the real repo (it only reads docs/ and writes
    # docs/knowledge/INDEX.yaml) and parse the result back with kb's own parser.
    result = run_kb("reindex")
    assert result.returncode == 0
    assert kb.INDEX_PATH.exists()

    text = kb.INDEX_PATH.read_text(encoding="utf-8")
    entries = kb._parse_index(text)
    assert len(entries) >= 5, (
        f"expected >=5 INDEX.yaml entries from this repo's docs/, got {len(entries)}"
    )
    for e in entries:
        assert e.get("id")
        assert e.get("path")
        assert e.get("path", "").endswith(".md")
        assert isinstance(e.get("tags"), list)
        assert isinstance(e.get("answers"), list)

    # round-trip: dumping the parsed entries again should be stable (same entry count)
    redumped = kb._dump_index(entries)
    reparsed = kb._parse_index(redumped)
    assert len(reparsed) == len(entries)


def test_sources_runs_without_crashing():
    if not (HERE / "sources" / "registry.yaml").exists():
        pytest.skip("sources/registry.yaml not present")
    result = run_kb("sources")
    assert result.returncode == 0
    assert "Traceback" not in result.stderr


def test_yaml_str_escapes_quotes_and_backslashes():
    assert kb._yaml_str('he said "hi"') == '"he said \\"hi\\""'
    assert kb._yaml_str("a\\b") == '"a\\\\b"'


def test_parse_scalar_or_list_round_trip():
    items = ["a", 'b"c', "d\\e"]
    dumped = kb._yaml_list(items)
    assert kb._parse_scalar_or_list(dumped) == items


def test_trim_evidence_carries_province_th_for_a_deciding_nationwide_row():
    """Independent review item 3 (MED): `_trim_evidence` (the non-verbose `evidence`
    path every default `kb.py answer` call uses) used to drop `province_th` even
    though the untrimmed `evidence` list already carried it -- so
    `_nationwide_accountability_fallback` (which reads this trimmed list on the
    default path) always fell back to "ไม่ทราบจังหวัด [OPEN]" for every nationwide
    point, regardless of whether the feed's own geocode province was known."""
    evidence = [{
        "station": "สถานีตัวอย่าง", "status": "OVERBANK", "age_h": 0.5,
        "used_for_decision": True, "stale": False,
        "dist_km": 2.1, "resolution": "station",
        "agency": "RID", "province_th": "เชียงใหม่",
    }]
    trimmed = kb._trim_evidence(evidence)
    assert trimmed, "expected the deciding row to survive trimming"
    assert trimmed[0]["province_th"] == "เชียงใหม่"


def test_nationwide_accountability_fallback_relays_province_from_trimmed_evidence():
    """End-to-end companion to the test above: `_nationwide_accountability_fallback`
    must name the real province once `_trim_evidence` carries it through, not the
    "ไม่ทราบจังหวัด [OPEN]" placeholder."""
    state_answer = {"evidence": kb._trim_evidence([{
        "station": "สถานีตัวอย่าง", "status": "OVERBANK", "age_h": 0.5,
        "used_for_decision": True, "stale": False,
        "dist_km": 2.1, "resolution": "station",
        "agency": "RID", "province_th": "เชียงใหม่",
    }])}
    result = kb._nationwide_accountability_fallback(state_answer)
    assert result is not None
    assert "เชียงใหม่" in result["owner_agencies"][0]
    assert "ไม่ทราบจังหวัด" not in result["owner_agencies"][0]
