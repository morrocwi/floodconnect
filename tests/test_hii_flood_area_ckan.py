"""Tests for tools/harvest/hii_flood_area_ckan.py's pure extract/build functions. No
network -- uses a trimmed fixture CSV (tests/fixtures/hii_flood_area_sample.csv, real
rows from this check's own probe sample)."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
from tools.harvest import hii_flood_area_ckan as hfa  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_east_rows_filters_to_named_districts():
    rows = hfa.extract_east_rows(FIXTURES / "hii_flood_area_sample.csv",
                                  districts_th=["เขตบางกะปิ", "เขตสะพานสูง"])
    # 3 of the 4 data rows are in Bang Kapi/Saphan Sung; the Sai Noi (Nonthaburi) row is dropped
    assert len(rows) == 3
    assert all(r["amphoe_th"] in ("เขตบางกะปิ", "เขตสะพานสูง") for r in rows)


def test_extract_east_rows_parses_month_and_count_as_int():
    rows = hfa.extract_east_rows(FIXTURES / "hii_flood_area_sample.csv",
                                  districts_th=["เขตสะพานสูง"])
    assert len(rows) == 1
    assert rows[0]["month"] == 9
    assert rows[0]["count_17_year"] == 2
    assert rows[0]["tambon_th"] == "แขวงสะพานสูง"


def test_build_output_carries_founder_licence_ruling_and_public_page_true():
    out = hfa.build_output([{"month": 9}])
    meta = out["_meta"]
    assert meta["public_page"] is True
    assert meta["licence"] == "CC BY-NC (HII open data)"
    assert "founder 2026-09-27" in meta["licence_ruling"]
    assert meta["attribution_required"].startswith("ที่มา:")
    assert meta["row_count"] == 1
