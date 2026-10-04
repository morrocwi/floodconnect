"""Session-wide guards: the real gitignored `raw/` and `data/` stores, AND every
git-tracked file in this repo, must never change as a side effect of running the test
suite (real data only in tests, never simulated -- see AGENTS.md's top rules; and
tests must never mutate a tracked file -- see the 2026-10-02 fix for
tests/test_kb.py::test_reindex_produces_valid_yaml_with_min_entries and
tests/test_typology_water_push_boats_2026-09-28.py::test_card_registered_via_kb_reindex,
which both ran `kb.py reindex` and left docs/knowledge/INDEX.yaml -- a tracked file --
dirty before they were given snapshot/restore fixtures).

Snapshot is (relative path -> sha256 of file content) at collection time, compared
again at session teardown. Content hashing (not size/mtime) avoids false positives
from a read-only sqlite connection touching a file's mtime without changing its bytes.
A path that is new, missing, or whose content changed makes the whole session fail
with the list of offending paths.
"""
import hashlib
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WATCHED_DIRS = [REPO_ROOT / "raw", REPO_ROOT / "data"]


def _hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot():
    snap = {}
    for d in WATCHED_DIRS:
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file():
                try:
                    snap[str(p.relative_to(REPO_ROOT))] = _hash_file(p)
                except OSError:
                    continue
    return snap


@pytest.fixture(scope="session", autouse=True)
def _real_data_stores_untouched_guard():
    before = _snapshot()
    yield
    after = _snapshot()
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(
        p for p in (set(before) & set(after)) if before[p] != after[p]
    )
    if added or removed or changed:
        details = []
        if added:
            details.append(f"ADDED: {added}")
        if removed:
            details.append(f"REMOVED: {removed}")
        if changed:
            details.append(f"CHANGED: {changed}")
        pytest.fail(
            "This test session wrote into the real gitignored raw/ or data/ store -- "
            "a test is missing a RAW_LIVE_DIR/FORECAST_DIR/YAML_DUMP_PATH (or "
            "equivalent) monkeypatch onto tmp_path. " + "; ".join(details),
            pytrace=False,
        )


def _git_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def _snapshot_tracked():
    snap = {}
    for rel in _git_tracked_files():
        p = REPO_ROOT / rel
        if p.is_file():
            try:
                snap[rel] = _hash_file(p)
            except OSError:
                continue
    return snap


@pytest.fixture(scope="session", autouse=True)
def _tracked_files_untouched_guard():
    """No test may leave a git-tracked file dirty (real data only in tests, never a
    side effect on a file this repo ships -- see module docstring). Deletion/creation
    of a tracked path is reported too, since `git ls-files` is read once at session
    start; a path a test adds mid-session and never removes would otherwise be
    invisible to this guard until the NEXT session's `git ls-files` picks it up as
    tracked-but-uncommitted (git status would already show it dirty by then)."""
    before = _snapshot_tracked()
    yield
    after = _snapshot_tracked()
    changed = sorted(p for p in (set(before) & set(after)) if before[p] != after[p])
    removed = sorted(set(before) - set(after))
    if changed or removed:
        details = []
        if changed:
            details.append(f"CHANGED: {changed}")
        if removed:
            details.append(f"REMOVED: {removed}")
        pytest.fail(
            "This test session wrote into (or deleted) a git-tracked file -- a test "
            "is running a real CLI (e.g. `kb.py reindex`) against this repo's real "
            "tracked output without a snapshot/restore fixture. " + "; ".join(details),
            pytrace=False,
        )
