"""Schema lint for sources/api_census.yaml -- this is a CENSUS, not a claim of quality
(see that file's own header), but its `status` field still has to come from a fixed
vocabulary. Several re-probe rounds added new status values (`reachable_image_only`,
`unreachable_tls_error`, etc) with nothing validating or documenting them, so any code
that counts `status == "reachable"`/`"unreachable"` would silently undercount. This file
is the guard; the vocabulary itself is documented in api_census.yaml's own header
comment, not restated here beyond the bare list."""
from pathlib import Path

import yaml

CENSUS_PATH = Path(__file__).parent.parent / "sources" / "api_census.yaml"

# Keep in sync with the header comment in sources/api_census.yaml -- that comment is for
# humans, this set is what the test actually enforces.
ALLOWED_STATUS = {
    "connected",
    "catalog_only",
    "reachable",
    "reachable_http_only",
    "reachable_image_only",
    "reachable_js_only",
    "reachable_calendar_wrapper",
    "reachable_duplicate",
    "reachable_portal_only",
    "reachable_pdf_unparsed",
    "unreachable",
    "unreachable_tls_error",
    "host_blocked",
    "needs_key",
    "unknown",
    "unresolved_url",
    "not_a_source",
    "host_blocked",
}

ALLOWED_TAG = {"VERIFIED", "RELAYED", "OPEN", "MEASURED", "RELAYED-model", "FAILED"}


def _load():
    with open(CENSUS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _all_sources():
    return _load()["sources"]


def test_census_loads_and_has_sources():
    data = _load()
    assert "sources" in data
    assert len(data["sources"]) >= 8


def test_every_census_source_has_a_recognized_status():
    for s in _all_sources():
        assert s.get("status") in ALLOWED_STATUS, (
            f"{s.get('id')!r} has an unrecognized census status {s.get('status')!r} -- "
            "add it to ALLOWED_STATUS here AND to the header comment in "
            "sources/api_census.yaml, or use an existing value.")


def test_every_census_source_has_a_recognized_tag():
    for s in _all_sources():
        assert s.get("tag") in ALLOWED_TAG, (
            f"{s.get('id')!r} has an unrecognized tag {s.get('tag')!r}")


def test_every_census_source_id_is_unique():
    ids = [s["id"] for s in _all_sources()]
    assert len(ids) == len(set(ids)), "duplicate id(s) in sources/api_census.yaml"


def test_reachable_prefixed_statuses_are_all_in_the_allowed_set():
    """Guards against a future status that starts with "reachable_" but was never added
    to ALLOWED_STATUS -- a narrower check than the full-membership test above, kept
    separate so a failure here points straight at a naming-convention slip."""
    for s in _all_sources():
        status = s.get("status", "")
        if status.startswith("reachable_"):
            assert status in ALLOWED_STATUS, status


def test_no_source_is_left_unknown():
    """The 2026-10-03 close-out probed every remaining `unknown` row once -- a future
    source added back into `unknown` without being probed would silently regress this
    census's "nothing left unprobed" state."""
    unknown = [s["id"] for s in _all_sources() if s.get("status") == "unknown"]
    assert unknown == [], f"{len(unknown)} source(s) still unknown: {unknown}"


#  Statuses whose very meaning requires an actual HTTP response to have been observed
#  -- a VERIFIED row (per this file's own tag vocabulary, "this check ... actually
#  fetched the URL and saw the payload/page") in one of these must carry a probed_at
#  and an http_status, never just a bare status. A RELAYED row is excluded on purpose
#  -- by that same vocabulary, RELAYED means "not fetched by this check", so the 2xx/
#  failure behind a RELAYED "reachable"/"unreachable" came from a secondary source,
#  not this check's own probe, and carries no probed_at/http_status by construction.
_STATUSES_IMPLYING_AN_OBSERVED_RESPONSE = {
    "reachable", "reachable_http_only", "reachable_image_only", "reachable_js_only",
    "reachable_calendar_wrapper", "reachable_duplicate", "reachable_portal_only",
    "reachable_pdf_unparsed", "unreachable", "unreachable_tls_error", "host_blocked",
}


def test_verified_probed_sources_carry_an_http_status():
    """A VERIFIED row with a non-null `probed_at` but no `http_status` on a status that
    implies an actual HTTP response was observed reads as a measurement nobody
    actually made."""
    for s in _all_sources():
        if s.get("tag") == "VERIFIED" and s.get("status") in _STATUSES_IMPLYING_AN_OBSERVED_RESPONSE:
            assert s.get("probed_at") is not None, (
                f"{s['id']!r} (status={s['status']!r}) has no probed_at")
            assert s.get("http_status") is not None, (
                f"{s['id']!r} (status={s['status']!r}) has no http_status")


def test_every_catalog_only_source_has_a_non_empty_reason():
    """C3-GOV9 (2026-10-03): a `catalog_only` row with no `catalog_reason` is as
    misleading as the generic `reachable` value this status replaced it for -- every
    deliberate "seen, decided not to wire" row must say why."""
    for s in _all_sources():
        if s.get("status") == "catalog_only":
            reason = (s.get("catalog_reason") or "").strip()
            assert reason, f"{s['id']!r} (status=catalog_only) has an empty catalog_reason"


def test_no_source_is_left_plain_reachable():
    """C3-GOV9 (2026-10-03): the generic `reachable` value (no specific reason, not
    wired) was fully swept this check into either `connected` (wired, see
    sources/registry.yaml) or `catalog_only` (seen, decided not to wire, with a
    reason) -- a future source landing back in plain `reachable` would silently
    regress this census's "nothing left pending" state."""
    pending = [s["id"] for s in _all_sources() if s.get("status") == "reachable"]
    assert pending == [], f"{len(pending)} source(s) still plain 'reachable': {pending}"


def test_no_source_is_left_in_a_finer_reachable_subtype_either():
    """Second C3-GOV9 pass (2026-10-03): the first pass's own guard above only caught
    the exact string `reachable`, so 31 rows left sitting in the finer `reachable_*`
    subtypes (the census header's own wording for several of them -- "not ingested
    yet" -- is pending by definition) survived undetected. Every such row is now
    `catalog_only` with the old value preserved in `catalog_subtype` -- a future row
    landing back in a bare `reachable_*` status would regress this census's "nothing
    left pending" state the same way plain `reachable` once did."""
    pending = [s["id"] for s in _all_sources()
               if str(s.get("status", "")).startswith("reachable_")]
    assert pending == [], (
        f"{len(pending)} source(s) still in a finer 'reachable_*' status, never "
        f"folded into catalog_only: {pending}")


def test_every_catalog_subtype_is_a_retired_reachable_value():
    """`catalog_subtype` exists only to preserve which finer `reachable_*` observation
    a catalog_only row started from -- a typo or a new ad-hoc value here would silently
    stop meaning anything."""
    retired = {
        "reachable_http_only", "reachable_image_only", "reachable_js_only",
        "reachable_calendar_wrapper", "reachable_duplicate", "reachable_portal_only",
        "reachable_pdf_unparsed",
    }
    for s in _all_sources():
        subtype = s.get("catalog_subtype")
        if subtype is not None:
            assert s.get("status") == "catalog_only", (
                f"{s['id']!r} has catalog_subtype set but status={s.get('status')!r}")
            assert subtype in retired, (
                f"{s['id']!r} has an unrecognized catalog_subtype {subtype!r}")


def test_unresolved_url_sources_are_tagged_open():
    """A row with no single concrete URL to probe carries no probed_at/http_status by
    construction (see the header's own `unresolved_url` definition) -- the only way
    such a row reads as "decided" rather than silently pending is an explicit `tag:
    OPEN`, the alternative this census's own vocabulary offers to a `catalog_reason`."""
    for s in _all_sources():
        if s.get("status") == "unresolved_url":
            assert s.get("tag") == "OPEN", (
                f"{s['id']!r} (status=unresolved_url) must carry tag: OPEN")


def test_unreachable_and_host_blocked_sources_have_a_non_empty_reason():
    """Every `unreachable`/`host_blocked` row must carry an actual reason in `notes` --
    an empty/whitespace-only note on a "we tried and it failed" row is as misleading as
    a missing probed_at."""
    for s in _all_sources():
        if s.get("status") in ("unreachable", "host_blocked"):
            notes = (s.get("notes") or "").strip()
            assert notes, f"{s['id']!r} (status={s['status']!r}) has an empty notes field"
