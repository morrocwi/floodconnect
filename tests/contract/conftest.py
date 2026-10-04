"""Shared helpers for the contract-test suite.

Every test in this directory replays a RECORDED real response captured in a single
founder-visible GET (never a hand-built/simulated payload). This file
verifies the fixture itself hasn't silently drifted (sha256 sidecar check) before any
parser is asked to read it.
"""
import hashlib
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Sources whose fixture was deliberately removed from the public tree (release prep
# licence/redistribution finding: the captured body was a large raw binary --
# PDF/GIF -- from a source whose licence_status.unresolved=true, with no minimal-excerpt
# form available for a binary format). `load_captured` skips these loudly rather than
# raising FileNotFoundError, so the public CI run shows a visible, explained skip instead
# of a confusing failure; the local/private repo (which did the real capture) is
# unaffected -- this list only matters when the fixture file is actually absent.
REMOVED_BINARY_FIXTURES = {
    "dds_nowcast_gif": "radar GIF snapshot dropped from public tree (licence_status.unresolved=true)",
    "dds_daily_pdf": "DDS daily bulletin PDF dropped from public tree (licence_status.unresolved=true)",
    "dds_tide_pdf": "DDS tide-table PDF dropped from public tree (licence_status.unresolved=true)",
}

# Fixtures were pinned by body sha256 but not by the parser
# version that is supposed to read them, so a parser's output shape could silently drift
# out from under a "real capture" fixture with nothing failing. One constant per
# collector, bumped whenever that collector's own parse function changes its output
# shape in a way that would make an old capture misleading. New collectors default to
# "v1" (see `load_captured` below) rather than needing an entry here on day one.
PARSER_VERSIONS: dict[str, str] = {
    "rid9_chonburi_rpt": "v1",
    "rid_app_reservoir": "v1",
}


def _find_body_path(source_id: str, sidecar: dict) -> Path:
    """The body's extension now follows the capture's real Content-Type
    (`sidecar["fixture_ext"]`) instead of always being assumed `.json` -- a PDF/GIF
    source captured under this scheme is no longer saved under a false `.json` name.
    Falls back to `.json` for a sidecar captured before this field existed."""
    ext = sidecar.get("fixture_ext", "json")
    p = FIXTURES_DIR / f"{source_id}_captured.{ext}"
    if p.exists():
        return p
    # Backward-compat: older sidecars (no fixture_ext) always used `.json`.
    legacy = FIXTURES_DIR / f"{source_id}_captured.json"
    if legacy.exists():
        return legacy
    raise FileNotFoundError(f"{source_id}: no captured fixture body found (looked for "
                             f"{p.name} and {legacy.name})")


def load_captured(source_id: str, binary: bool = False):
    """Load a captured fixture + its sidecar, verifying the sidecar's sha256 still
    matches the body on disk (catches silent edits to a "real capture" fixture).

    Returns `(data, sidecar)`. For a JSON capture (the common case), `data` is the
    parsed JSON. For a binary capture (PDF/GIF/etc, or when `binary=True` is passed
    explicitly), `data` is the raw bytes -- it is never run through `json.loads`, which
    would raise on a non-JSON body (defect 4: this used to be unconditional).

    Skips (not fails) when `source_id` is in `REMOVED_BINARY_FIXTURES` and its sidecar
    is absent -- see that dict's own docstring."""
    sidecar_path = FIXTURES_DIR / f"{source_id}_captured.sidecar.json"
    if not sidecar_path.exists() and source_id in REMOVED_BINARY_FIXTURES:
        pytest.skip(REMOVED_BINARY_FIXTURES[source_id])
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    body_path = _find_body_path(source_id, sidecar)
    body_bytes = body_path.read_bytes()
    actual_sha = hashlib.sha256(body_bytes).hexdigest()
    assert actual_sha == sidecar["sha256"], (
        f"{source_id}: captured fixture body no longer matches its sidecar sha256 -- "
        "re-capture, don't hand-edit a recorded real response.")
    assert sidecar["http_status"] == 200, (
        f"{source_id}: sidecar records a non-200 capture, not a usable contract fixture.")
    expected_version = PARSER_VERSIONS.get(source_id, "v1")
    assert sidecar.get("parser_version") == expected_version, (
        f"{source_id}: sidecar parser_version {sidecar.get('parser_version')!r} != pinned "
        f"{expected_version!r} -- either re-capture with the current parser's version "
        "stamped, or bump PARSER_VERSIONS here deliberately if the parser changed shape.")
    ext = sidecar.get("fixture_ext", "json")
    if binary or ext != "json":
        return body_bytes, sidecar
    data = json.loads(body_bytes)
    return data, sidecar
