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


def _load():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


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
