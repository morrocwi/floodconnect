"""Contract tests for the 2026-10-03 HII/BMA/GISTDA pass: real single-GET captures for
three newly-wired sources (hii_analyst_cctv, bma_pak_khlong_csv, bangkok_ckan_portal),
replayed through their real parsers -- never a hand-built payload, same discipline as
test_wp2_additional_sources.py / test_thaiwater_canal_waterlevel.py.

gistda_flood_extent_api and the 6 other key-needed sources added this same pass
(google_flood_hub_api, cds_era5_reanalysis, nasa_lhasa_landslide_nowcast,
opentopography_copernicus_dem_glo30, gfw_data_api, reliefweb_api_v2) are NOT covered
here -- none of their keys are available in this environment, so no real success
response was ever captured (see each one's own sources/registry.yaml entry,
contract_test: MISSING). tests/test_collect.py covers the generic missing-key-env gate
that protects all of them."""
import parsers
from tests.contract.conftest import load_captured


def test_hii_analyst_cctv_parses_camera_catalog():
    data, sidecar = load_captured("hii_analyst_cctv")
    assert sidecar["url"].endswith("/analyst/cctv")
    rows = parsers.parse_hii_analyst_cctv(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["station_id"]
        assert -90 <= r["lat"] <= 90
        assert -180 <= r["lon"] <= 180


def test_bma_pak_khlong_csv_parses_daily_level_series():
    body, sidecar = load_captured("bma_pak_khlong_csv", binary=True)
    assert sidecar["url"].endswith("river_pak_khlong.csv")
    rows = parsers.parse_bma_pak_khlong_csv(body.decode("utf-8"))
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["date"].count("-") == 2
        assert isinstance(r["max_water_level_m"], float)


def test_bangkok_ckan_portal_parses_dataset_catalog():
    data, sidecar = load_captured("bangkok_ckan_portal")
    assert "package_search" in sidecar["url"]
    rows = parsers.parse_bangkok_ckan_catalog(data)
    assert isinstance(rows, list) and len(rows) > 0
    for r in rows:
        assert r["dataset_id"]
