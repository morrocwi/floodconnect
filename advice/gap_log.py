"""The M8 policy gap log -- `policy_gap_record.schema.json`'s writer.

Appends ONE record per call to the caller's local, git-ignored
`data/policy_gap_log.jsonl` -- opened only with mode "a" (append), never rewritten,
per the M8 task's own rule ("it only ever opens the file with 'a' and never rewrites
it"). The answer itself carries only `policy_gap_ref` ({path, record_id}), never the
full record inline (`build_answer`/`kb.py` wiring, see that module).
"""
from __future__ import annotations

import hashlib
import json
import pathlib

DEFAULT_LOG_PATH = pathlib.Path("data") / "policy_gap_log.jsonl"


def _record_id(record: dict) -> str:
    """sha256 of the record's own canonical (sorted-keys) JSON encoding --
    `record_id` is computed BEFORE it is added to the dict that gets hashed (it is
    never part of its own hash input), so appending the same logical record twice
    (same run_at/blockers/sensors/...) yields the same id both times -- a caller can
    de-duplicate on `record_id` without re-reading the whole log."""
    canonical = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_record(blockers: list, run_at: str, sensors: "list | None" = None,
                  outlet_bottleneck: "str | None" = None,
                  responsible_agency: "str | None" = None) -> dict:
    """Build one policy_gap_record dict (schema: policy_gap_record.schema.json),
    without writing it. `blockers` is never empty-checked here -- a caller may log a
    run with zero blockers if it chooses to; `append_record` is the one that decides
    whether a given answer run is worth logging at all (kb.py wiring, P-D)."""
    base = {
        "run_at": run_at,
        "blockers": list(blockers),
        "sensors": list(sensors or []),
        "outlet_bottleneck": outlet_bottleneck,
        "responsible_agency": responsible_agency,
    }
    record = dict(base)
    record["record_id"] = _record_id(base)
    return record


def append_record(record: dict, path: "pathlib.Path | str" = DEFAULT_LOG_PATH) -> dict:
    """Append `record` as one JSON line to `path`. Creates the parent directory if
    needed. Opens the file with mode "a" ONLY -- never "w", never reads-then-rewrites
    the whole file -- so a concurrent writer's earlier lines can never be lost by this
    call. Returns `{"path": str(path), "record_id": record["record_id"]}`, the exact
    shape `policy_gap_ref` carries in the answer."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return {"path": str(path), "record_id": record["record_id"]}


def log_gap(blockers: list, run_at: str, sensors: "list | None" = None,
            outlet_bottleneck: "str | None" = None,
            responsible_agency: "str | None" = None,
            path: "pathlib.Path | str" = DEFAULT_LOG_PATH) -> dict:
    """build_record + append_record in one call -- the convenience entry point a
    caller (kb.py, P-D) will actually use. Returns the `policy_gap_ref` shape."""
    record = build_record(blockers, run_at, sensors=sensors,
                           outlet_bottleneck=outlet_bottleneck,
                           responsible_agency=responsible_agency)
    return append_record(record, path=path)
