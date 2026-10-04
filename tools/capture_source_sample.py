#!/usr/bin/env python3
"""Source-capture step: one founder-visible, single-GET capture of a real
upstream response for a registry source, saved as a contract-test fixture with a
provenance sidecar.

Rules this script enforces (never relaxed by a flag):
  - exactly one HTTP request per URL, no retry loop
  - no credentials read from or written to any file
  - the body is saved byte-for-byte as returned -- never hand-edited afterward
  - a sidecar {source_id, url, captured_at, sha256, http_status} sits next to it

This is a manual, founder-visible tool -- it is not wired into any scheduler/cron and
must never be invoked periodically. Re-running it on a source replaces that source's
fixture with a fresh real capture (and the sidecar's sha256/captured_at with it);
`tests/contract/test_<id>.py` then has to keep passing against the new fixture or be
updated deliberately, never silently.

Usage:
    python3 tools/capture_source_sample.py <source_id> <url>
"""
import datetime
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).parent
FIXTURES_DIR = HERE.parent / "tests" / "contract" / "fixtures"
REGISTRY_PATH = HERE.parent / "sources" / "registry.yaml"

# Content-Type (prefix match, longest-wins not needed -- these are disjoint upstream MIME
# families) -> file extension for the saved fixture. This used to always
# write `<id>_captured.json` regardless of what the upstream actually returned, which
# would silently mislabel a PDF/GIF source as JSON and then fail `json.loads` on replay.
CONTENT_TYPE_EXT = {
    "application/json": "json",
    "application/pdf": "pdf",
    "image/gif": "gif",
    "image/": "gif",  # fallback for an image/* type this table doesn't name explicitly
    "text/html": "html",
    "text/plain": "txt",
    "text/": "txt",
}


def _ext_for(content_type: str) -> str:
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    if ct in CONTENT_TYPE_EXT:
        return CONTENT_TYPE_EXT[ct]
    for prefix, ext in CONTENT_TYPE_EXT.items():
        if prefix.endswith("/") and ct.startswith(prefix):
            return ext
    # Unknown/empty Content-Type: never guess "json" by default (that is exactly the bug
    # this fixes) -- fall back to a generic binary extension instead.
    return "bin"


def _load_registry_row(source_id: str) -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    by_id = {s["id"]: s for s in data.get("sources", [])}
    return by_id.get(source_id)


def capture(source_id: str, url: str, timeout_s: int = 15, _skip_registry_check: bool = False) -> dict:
    """One GET, no retry. Raises on any network error -- caller decides what to do
    (this script does not swallow a failure into a fabricated 'empty' fixture).

    Refuses to capture a `source_id` that isn't in `sources/registry.yaml`
    (catches a typo'd id or a probe for something never registered), and refuses when
    that row's own `host_rule.max_requests_per_run` is below 1 (a row that explicitly
    declares it may not be hit at all)."""
    if not _skip_registry_check:
        row = _load_registry_row(source_id)
        if row is None:
            raise ValueError(
                f"{source_id!r} is not a registered source in {REGISTRY_PATH} -- "
                "refusing to capture an unregistered/typo'd id.")
        max_per_run = (row.get("host_rule") or {}).get("max_requests_per_run")
        if max_per_run is not None and max_per_run < 1:
            raise ValueError(
                f"{source_id!r}'s host_rule.max_requests_per_run={max_per_run!r} forbids "
                "any request this run -- refusing to capture.")

    req = urllib.request.Request(url, headers={"User-Agent": "floodconnect-contract-capture/1"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read()
        status = resp.status
        content_type = resp.headers.get("Content-Type", "")

    ext = _ext_for(content_type)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    body_path = FIXTURES_DIR / f"{source_id}_captured.{ext}"
    body_path.write_bytes(body)

    sidecar = {
        "source_id": source_id,
        "url": url,
        "captured_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": hashlib.sha256(body).hexdigest(),
        "http_status": status,
        "content_type": content_type,
        "fixture_ext": ext,
        "capture_method": (
            "single GET, one request per URL, no retry "
            "(per host_rule.max_requests_per_run)"
        ),
    }
    sidecar_path = FIXTURES_DIR / f"{source_id}_captured.sidecar.json"
    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sidecar


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    source_id, url = argv[1], argv[2]
    sidecar = capture(source_id, url)
    print(json.dumps(sidecar, indent=2, ensure_ascii=False))
    return 0 if sidecar["http_status"] == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
