"""Contract test for RID region-9 (Chonburi) reservoir report (RID sweep, 2026-10-03).

Real single-GET capture (`tools/capture_source_sample.py`), replayed through the real
production parser -- never a hand-built payload, same discipline as the rest of this
directory. See `tests/contract/fixtures/rid9_chonburi_rpt_captured.sidecar.json` for the
exact URL/timestamp/sha256.
"""
import parsers
from tests.contract.conftest import load_captured


def test_rid9_chonburi_rpt_parses_reservoir_table():
    data, sidecar = load_captured("rid9_chonburi_rpt")
    assert sidecar["url"].startswith("http://irrigation.rid.go.th/rid9/")
    html = data.decode("cp874", errors="replace")
    rows = parsers.parse_rid9_chonburi_rpt(html)
    # Trimmed excerpt (publish-safety finding, 2026-10-03: 300KB fixture budget) --
    # the real full capture had 61 rows; this fixture keeps a small real prefix of the
    # same page, so this is a structural sanity floor only.
    assert isinstance(rows, list) and len(rows) >= 3
    for r in rows:
        assert r["name_th"]
        assert r["province_th"]
        assert r["category_th"] in (
            "อ่างเก็บน้ำขนาดใหญ่", "อ่างเก็บน้ำขนาดกลางและอ่างเก็บน้ำตามพระราชดำริ",
        )
        # capacity_mcm is populated for every real reservoir row (confirmed on the
        # capture); other numeric fields are legitimately None on days with no reading.
        assert isinstance(r["capacity_mcm"], float)


def test_rid9_chonburi_rpt_never_fabricates_a_missing_reading():
    data, _sidecar = load_captured("rid9_chonburi_rpt")
    html = data.decode("cp874", errors="replace")
    rows = parsers.parse_rid9_chonburi_rpt(html)
    # At least one real row on the capture date has a blank storage_current_mcm cell --
    # the parser must leave it None, never substitute 0 or any other fabricated value.
    assert any(r["storage_current_mcm"] is None for r in rows)
