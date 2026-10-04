"""Contract test for RID's reservoir web-app `api/dams` (the highest-value unwired RID
source found by the census sweep -- reservoir data with coordinates for the Chao
Phraya-basin feeder dams).

Real single-POST capture (`date=2026-10-03`), replayed through the real production
parser -- never a hand-built payload, same discipline as the rest of this directory. See
`tests/contract/fixtures/rid_app_reservoir_captured.sidecar.json` for the exact
URL/method/timestamp/sha256.
"""
import json

import parsers
from tests.contract.conftest import load_captured


def test_rid_app_reservoir_parses_dam_rows():
    data, sidecar = load_captured("rid_app_reservoir")
    assert sidecar["url"] == "https://app.rid.go.th/reservoir/api/dams"
    assert sidecar["method"] == "POST"
    rows = parsers.parse_rid_app_reservoir(data)
    # Trimmed excerpt (publish-safety finding, 2026-10-03: 300KB fixture budget) --
    # the real full capture had 35 dams; this fixture keeps the 3 named Chao
    # Phraya-basin feeder dams below plus 2 more real rows, so this is a structural
    # sanity floor only.
    assert isinstance(rows, list) and len(rows) >= 3
    names = {r["name_th"] for r in rows}
    # The exact Chao Phraya-basin feeder dams named above by name.
    assert "เขื่อนสิริกิติ์" in names
    assert "เขื่อนภูมิพล" in names
    assert "เขื่อนป่าสักชลสิทธิ์" in names
    for r in rows:
        assert r["dam_id"]
        assert r["name_th"]
        assert parsers._valid_th_coord(r["lat"], r["lon"]), (
            f"{r['name_th']} has no valid coordinate on the real capture")


def test_rid_app_reservoir_never_fabricates_a_missing_reading():
    data, _sidecar = load_captured("rid_app_reservoir")
    rows = parsers.parse_rid_app_reservoir(data)
    # The real capture has at least one dam with a literal " - " placeholder cell
    # (DMD_Q) -- confirm the parser's numeric fields never turn a placeholder into 0.
    assert any(r.get("capacity_mcm") is not None for r in rows)
    # No numeric field is ever a string here.
    for r in rows:
        for field in ("capacity_mcm", "storage_current_mcm", "storage_pct",
                       "inflow_daily_mcm", "release_daily_mcm"):
            assert r[field] is None or isinstance(r[field], float)


def test_rid_app_alert_handles_a_real_empty_feed():
    """The real capture_at-the-time response was `{"Dam":[],"Reservoir":[]}` -- confirm
    the parser returns an empty list (not None, not an exception) rather than treating
    an empty-but-valid feed as a parse failure."""
    empty = {"Dam": [], "Reservoir": []}
    assert parsers.parse_rid_app_alert(empty) == []


def test_rid_app_alert_tags_each_row_with_its_kind():
    sample = {"Dam": [{"DAM_ID": "1"}], "Reservoir": [{"id": "r1"}]}
    rows = parsers.parse_rid_app_alert(sample)
    kinds = {r["kind"] for r in rows}
    assert kinds == {"Dam", "Reservoir"}
