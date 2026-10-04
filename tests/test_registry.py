"""Schema lint for sources/registry.yaml -- catches a malformed/incomplete entry before
it silently breaks collect.py or readout.py. No network calls."""
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).parent.parent / "sources" / "registry.yaml"

REQUIRED_TOP_KEYS = {"id", "agency", "url", "method", "cadence", "format", "auth",
                     "licence_status", "trust_tier", "host_rule", "last_status",
                     "variables"}
VALID_TRUST_TIERS = {"official_telemetry", "official_report",
                     "official_shared_inference", "third_party", "community_report"}

# Connector-contract fields that structurally enforce "on-demand only, no
# polling" at the schema level, plus contract-test/health-check bookkeeping.
CONNECTOR_REQUIRED_KEYS = {"kind", "fetch_mode", "retry", "schema_version", "imported_from",
                      "contract_test", "health_check"}
VALID_FETCH_MODES = {"on_demand"}  # the ONLY legal value -- no interval/cron field anywhere
VALID_RETRY = {"none"}             # one attempt only, no retry discipline
VALID_KINDS = {"api", "literature", "static", "candidate_unregistered"}
# (Previously "candidate" here AND a separate `status: candidate_unregistered`
# field on the same rows duplicated the same fact -- merged into this one value.)


def _load():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _all_sources():
    """`sources` (live-API-ish entries) -- not `reference_documents` (literature/static
    dataset citations, which carry a smaller, exempt schema -- see
    test_reference_documents_* below)."""
    return _load()["sources"]


def test_registry_loads_and_has_sources():
    data = _load()
    assert "sources" in data
    assert len(data["sources"]) >= 8


def test_every_source_has_required_keys():
    for s in _load()["sources"]:
        missing = REQUIRED_TOP_KEYS - set(s.keys())
        assert not missing, f"{s.get('id')} missing keys: {missing}"


def test_every_source_id_is_unique():
    ids = [s["id"] for s in _load()["sources"]]
    assert len(ids) == len(set(ids))


def test_every_trust_tier_is_from_the_fixed_vocabulary():
    for s in _load()["sources"]:
        assert s["trust_tier"] in VALID_TRUST_TIERS, (
            f"{s['id']} has an unrecognized trust_tier {s['trust_tier']!r}")


def test_every_agency_has_th_and_en():
    for s in _load()["sources"]:
        assert "th" in s["agency"] and "en" in s["agency"], s["id"]


def test_every_licence_status_has_unresolved_flag():
    """`unresolved: true` means "not independently confirmed against a formal licence
    text" -- it does NOT mean "openly licensed" (an earlier key name, `open`, could be
    misread that way)."""
    for s in _load()["sources"]:
        assert "unresolved" in s["licence_status"], s["id"]
        assert isinstance(s["licence_status"]["unresolved"], bool), s["id"]


def test_host_rule_has_max_requests_per_run():
    for s in _load()["sources"]:
        assert "max_requests_per_run" in s["host_rule"], s["id"]
        assert isinstance(s["host_rule"]["max_requests_per_run"], int), s["id"]


def test_bma_hosts_are_capped_at_one_request_per_run():
    """This workspace's host-safety rule: weather.bangkok.go.th / dds.bangkok.go.th
    sources must never declare more than one request per run."""
    for s in _load()["sources"]:
        url = s.get("url", "")
        if "weather.bangkok.go.th" in url or "dds.bangkok.go.th" in url:
            assert s["host_rule"]["max_requests_per_run"] <= 1, s["id"]


# --- connector-contract fields -------------------------------------------------


def test_every_source_has_the_wp2_connector_fields():
    for s in _all_sources():
        missing = CONNECTOR_REQUIRED_KEYS - set(s.keys())
        assert not missing, f"{s['id']} missing connector-contract fields: {missing}"


def test_fetch_mode_is_always_on_demand_never_an_interval():
    """Structural no-polling guarantee: `fetch_mode` has exactly one legal value and
    there is no cron/interval field anywhere in the schema -- a periodic poll cannot
    be declared through this registry even by accident."""
    for s in _all_sources():
        assert s["fetch_mode"] in VALID_FETCH_MODES, (
            f"{s['id']} declares fetch_mode={s['fetch_mode']!r}, "
            f"only {VALID_FETCH_MODES} is legal (no interval/cron field exists here).")
        for forbidden in ("interval", "interval_s", "cron", "schedule", "poll_every"):
            assert forbidden not in s, f"{s['id']} must not declare {forbidden!r}"


def test_retry_is_always_none():
    """One attempt only -- no retries on any source fetch."""
    for s in _all_sources():
        assert s["retry"] in VALID_RETRY, s["id"]


def test_kind_is_from_the_fixed_vocabulary():
    for s in _all_sources():
        assert s["kind"] in VALID_KINDS, (
            f"{s['id']} has an unrecognized kind {s['kind']!r}")


def test_contract_test_is_either_a_real_path_or_explicitly_missing():
    """A source's `contract_test` is either a path to a test file that actually exists,
    or the literal string MISSING -- never a placeholder standing in for a real capture
    (by design: 'a source with no capture gets contract_test: MISSING, never a
    hand-built fixture standing in for a real one')."""
    repo_root = REGISTRY_PATH.parent.parent
    for s in _all_sources():
        ct = s["contract_test"]
        if ct == "MISSING":
            continue
        assert (repo_root / ct).is_file(), f"{s['id']}: contract_test path {ct!r} does not exist"


def test_imported_from_is_local_or_a_recorded_union():
    for s in _all_sources():
        assert s["imported_from"] in ("local", "union(local,origin)"), s["id"]


# --- reference_documents (literature/static-dataset rows, exempt schema) ------


def test_reference_documents_section_exists():
    data = _load()
    assert "reference_documents" in data
    assert len(data["reference_documents"]) >= 1


def test_reference_documents_are_tagged_literature_and_exempt_from_contract_test():
    """Literature/static-dataset rows are exempt from contract_test/health_check
    (by design) -- they are not live APIs, so there is nothing to replay a
    captured HTTP response for."""
    for r in _load()["reference_documents"]:
        assert r["kind"] == "literature", r["id"]
        assert "contract_test" not in r, r["id"]
        assert "health_check" not in r, r["id"]
        assert "fetch_mode" not in r, r["id"]
