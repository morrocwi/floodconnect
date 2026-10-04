"""Contract tests for the C3-GOV9 pass (2026-10-03): real single-GET captures for the
6 sources this check actually wired out of sources/api_census.yaml's "plain reachable,
not wired" backlog (hii_mou_station_metadata, dnp_yom_basin_telemetry, pcd_mwqi,
dmcr_marine_acidification, royalrain_operations, royalrain_agriculture_rainfall), plus
3 more sources a follow-up pass the same day resolved from previously-parked CKAN
dataset-landing-page rows via one `package_show` call each (hii_water_level_catalog,
hii_reservoir_metadata, pcd_coastal_marine_quality).

Each fixture here is a REAL response from a single GET on 2026-10-03, captured with
`tools/capture_source_sample.py` (see each `*_captured.sidecar.json` for the exact
URL/timestamp/sha256), replayed through the real production parser -- never a
hand-built payload, same discipline as `test_hii_bma_gistda_sources.py`."""
import json

import parsers
from tests.contract.conftest import load_captured


def test_hii_mou_station_metadata_parses_station_catalog():
    body, sidecar = load_captured("hii_mou_station_metadata", binary=True)
    assert sidecar["url"].endswith("0all_stn_metadata.csv")
    rows = parsers.parse_hii_mou_station_metadata_csv(body.decode("utf-8-sig"))
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["station_code"]
        if r["lat"] is not None:
            assert -90 <= r["lat"] <= 90
            assert -180 <= r["lon"] <= 180


def test_dnp_yom_basin_telemetry_parses_station_list():
    body, sidecar = load_captured("dnp_yom_basin_telemetry", binary=True)
    assert sidecar["url"].endswith("telemetering-system-33-station-yom-basin.csv")
    rows = parsers.parse_dnp_yom_telemetry_csv(body.decode("utf-8-sig"))
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["station_code"]
        assert r["province"]


def test_pcd_mwqi_parses_annual_station_index():
    body, sidecar = load_captured("pcd_mwqi", binary=True)
    assert sidecar["url"].endswith("untitled.csv")
    rows = parsers.parse_pcd_mwqi_csv(body.decode("utf-8-sig"))
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["station_code"]
        assert isinstance(r["mwqi_value"], int)


def test_dmcr_marine_acidification_parses_ctd_casts():
    body, sidecar = load_captured("dmcr_marine_acidification", binary=True)
    assert sidecar["url"].endswith("untitled.csv")
    rows = parsers.parse_dmcr_marine_acidification_csv(body.decode("utf-8-sig"))
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["mooring_name"]
        assert r["observed_at_utc"].count("-") == 2
        if r["ph_tot"] is not None:
            assert 0 <= r["ph_tot"] <= 14


def test_royalrain_operations_parses_operation_log():
    data, sidecar = load_captured("royalrain_operations")
    assert sidecar["url"].endswith("dailyoperationsequenceinfo")
    rows = parsers.parse_royalrain_operations(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["operation_date"]
        if r["lat"] is not None:
            assert -90 <= r["lat"] <= 90
            assert -180 <= r["lon"] <= 180
    # This real capture has at least one record with a flown mission (lat/lon present)
    # -- guards against a parser regression that silently stops reading `missions`.
    assert any(r["lat"] is not None for r in rows)


def test_royalrain_agriculture_rainfall_parses_summary_and_has_no_coordinate():
    data, sidecar = load_captured("royalrain_agriculture_rainfall")
    assert sidecar["url"].endswith("summaryagricultureareainfo")
    rows = parsers.parse_royalrain_agriculture_rainfall(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["operation_date"]
        assert isinstance(r["province_count"], int)
    # No lat/lon key at all in this parser's output shape -- this source carries no
    # coordinate, never a fabricated one.
    assert all("lat" not in r and "lon" not in r for r in rows)


def test_hii_water_level_catalog_parses_nationwide_station_catalog():
    body, sidecar = load_captured("hii_water_level_catalog", binary=True)
    assert sidecar["url"].endswith("0all_stn_metadata.csv")
    rows = parsers.parse_hii_mou_station_metadata_csv(body.decode("utf-8-sig"))
    # Trimmed excerpt (publish-safety finding, 2026-10-03: 300KB fixture budget) --
    # structural floor only, not the full capture's 1,396-row nationwide count.
    assert len(rows) >= 3
    for r in rows:
        assert r["station_code"]
        if r["lat"] is not None:
            assert -90 <= r["lat"] <= 90
            assert -180 <= r["lon"] <= 180
    # Not a duplicate of hii_mou_station_metadata's own fixture -- different station set.
    other_body, _ = load_captured("hii_mou_station_metadata", binary=True)
    assert body != other_body


def test_hii_reservoir_metadata_parses_small_reservoir_catalog():
    body, sidecar = load_captured("hii_reservoir_metadata", binary=True)
    assert sidecar["url"].endswith("reservoir_metadata.csv")
    rows = parsers.parse_hii_reservoir_metadata_csv(body.decode("utf-8-sig"))
    # Trimmed excerpt (publish-safety finding, 2026-10-03) -- structural floor
    # only, not the full capture's 65-row count.
    assert len(rows) >= 3
    for r in rows:
        assert r["reservoir_name"]
        if r["lat"] is not None:
            assert -90 <= r["lat"] <= 90
            assert -180 <= r["lon"] <= 180
    # At least one real row has a parsed capacity figure, in million cubic meters.
    assert any(r["updated_capacity_mcm"] is not None or r["old_capacity_mcm"] is not None
               for r in rows)


def test_pcd_coastal_marine_quality_parses_monitoring_round():
    body, sidecar = load_captured("pcd_coastal_marine_quality", binary=True)
    assert sidecar["url"].endswith("marine_water_quality_2568.csv")
    rows = parsers.parse_pcd_coastal_marine_quality_csv(body.decode("utf-8-sig"))
    # Trimmed excerpt (publish-safety finding, 2026-10-03) -- structural floor
    # only, not the full capture's 420-row/419-ph-row count.
    assert len(rows) >= 3
    ph_rows = [r for r in rows if r["ph"] is not None]
    for r in ph_rows:
        assert 0 <= r["ph"] <= 14
        assert r["observed_at_utc"]
    # No lat/lon field at all in this payload -- never fabricated.
    assert all("lat" not in r and "lon" not in r for r in rows)
