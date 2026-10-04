"""Schema check for raw/backtests/sammakorn_7day_real_2026-09-27.jsonl (the REAL-data-only
7-day Sammakorn backtest event ledger, see docs/experiments/2026-09-27-sammakorn-7day-
backtest-REAL.md). Project decision: "ทดสอบข้อมูลจริงไม่จำลอง" -- this test only checks
structural honesty (every row carries a source + a timestamp + a tag), never re-derives or
re-scores the backtest itself. raw/ is gitignored, so this test is skipped (not failed) if
the ledger file isn't present in a given checkout/worktree."""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "raw" / "backtests" / "sammakorn_7day_real_2026-09-27.jsonl"

VALID_TAGS_PREFIXES = ("VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN")


def _load_rows():
    if not LEDGER_PATH.exists():
        pytest.skip(f"{LEDGER_PATH} not present in this checkout (raw/ is gitignored)")
    rows = []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                pytest.fail(f"line {line_no}: not valid JSON: {e}")
    return rows


def test_ledger_has_rows():
    rows = _load_rows()
    assert len(rows) > 0, "ledger file exists but has no rows"


def test_every_row_has_source_run_time_and_tag():
    rows = _load_rows()
    for i, row in enumerate(rows):
        assert row.get("source"), f"row {i} missing non-empty 'source'"
        assert row.get("run_time"), f"row {i} missing non-empty 'run_time'"
        assert row.get("tag"), f"row {i} missing non-empty 'tag'"


def test_every_tag_starts_with_a_known_epistemic_label():
    """Tags may carry extra qualifier text (e.g. 'MEASURED-community',
    'MEASURED (value real, but flagged SUSPECT ...)') -- this only checks the row starts
    with one of the five labels this repo's AGENTS.md ss2 declares, never invents a sixth."""
    rows = _load_rows()
    for i, row in enumerate(rows):
        tag = row["tag"]
        assert tag.startswith(VALID_TAGS_PREFIXES), (
            f"row {i} tag {tag!r} does not start with a known epistemic label "
            f"{VALID_TAGS_PREFIXES}")


def test_every_row_has_event_id_and_unit():
    rows = _load_rows()
    for i, row in enumerate(rows):
        assert row.get("event_id"), f"row {i} missing 'event_id'"
        assert row.get("unit"), f"row {i} missing 'unit'"


def test_horizon_to_t0_h_is_numeric_when_present():
    rows = _load_rows()
    for i, row in enumerate(rows):
        if "horizon_to_T0_h" in row:
            assert isinstance(row["horizon_to_T0_h"], (int, float)), (
                f"row {i} horizon_to_T0_h is not numeric: {row['horizon_to_T0_h']!r}")


def test_no_row_fabricates_a_missing_value_as_zero_silently():
    """A row whose action_label/tier explicitly says REFUSED/absent/n/a is fine (honest);
    this only guards against a row claiming a real numeric value while also saying, in its
    own note, that the value is missing -- a self-contradiction, not a schema violation
    this repo would want silently passing."""
    rows = _load_rows()
    for i, row in enumerate(rows):
        note = str(row.get("note", ""))
        value = row.get("value")
        if isinstance(value, (int, float)) and "ไม่มีข้อมูลจริง" in note:
            pytest.fail(f"row {i} has a numeric value but its own note says "
                        f"'ไม่มีข้อมูลจริง' (no real data) -- contradiction")
