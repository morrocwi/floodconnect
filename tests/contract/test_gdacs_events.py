"""Contract test for sources/registry.yaml's `gdacs_events` entry.

Replays a real response captured 2026-10-02T07:20:27Z (single GET, country=Thailand,
fromdate=2026-09-01, todate=2026-10-02, see fixtures/gdacs_events_captured.sidecar.json)
through the real parser -- never a hand-built payload. Per the registry's own `method`
note, GDACS's `country=` query param does not filter server-side, so this fixture is
expected to contain many non-Thailand events; the parser's client-side filter is what's
under test here, not the upstream API's own behaviour.

OPEN GAP (2026-10-02): this particular capture's 100 raw features contain
ZERO Thailand flood events (MEASURED, re-checked when this test was fixed) -- so the
positive path ("a real Thailand flood event survives the filter with the right fields")
is NOT exercised by this fixture. The assertions below only prove the filter actually
narrows the raw feed and that whatever it does return is Thailand-only; they do not
prove a true-positive Thailand event is correctly kept. Track that as an explicit,
named gap -- do not hand-build a fake Thailand event into this fixture to paper over it
(that would violate the "never a hand-built payload" rule above); close it by re-running
`tools/capture_source_sample.py gdacs_events <url>` during/after an actual Thailand flood
event window instead."""
import parsers
from tests.contract.conftest import load_captured


def test_captured_response_filters_to_thailand_flood_events_only():
    data, sidecar = load_captured("gdacs_events")
    assert "country=Thailand" in sidecar["url"]
    raw_count = len(data.get("features") or data.get("result") or (data if isinstance(data, list) else []))
    assert raw_count > 0, "fixture carries no raw features at all -- re-capture needed"
    events = parsers.parse_gdacs_events_thailand(data)
    assert isinstance(events, list)
    # Client-side filter must actually narrow the raw global feed -- not a no-op.
    assert len(events) < raw_count, (
        "the GDACS country= param is known not to filter server-side (see module "
        "docstring) -- the parser's own client-side filter must narrow a 100-feature "
        "global feed, a no-op here would mean the filter silently stopped working.")
    # Every row the filter DID keep must actually be a Thailand flood event -- never
    # trust the filter blindly just because it removed some rows.
    for f in data["features"]:
        props = f.get("properties") or f
        country = str(props.get("country") or "")
        iso3 = str(props.get("iso3") or "")
        eventtype = props.get("eventtype")
        is_kept = any(
            e["event_id"] == props.get("eventid") and e["name"] == (props.get("name") or props.get("eventname"))
            for e in events
        )
        if is_kept:
            assert "Thailand" in country or iso3.upper() == "THA", (
                f"kept a non-Thailand event: country={country!r} iso3={iso3!r}")
            assert eventtype in (None, "FL"), f"kept a non-flood event: eventtype={eventtype!r}"
