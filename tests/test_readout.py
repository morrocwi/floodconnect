"""Tests for readout.py -- renders against an empty store and a small fixture store.
No network calls."""
import json

import pytest

import readout
import store

CENTRE_LAT, CENTRE_LON = 13.758235, 100.676084


@pytest.fixture()
def conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


def test_build_readout_empty_store_no_crash(conn):
    result = readout.build_readout(
        conn, CENTRE_LAT, CENTRE_LON, 5.0,
        as_of_date="2026-09-26",
        generated_at_utc="2026-09-26T12:00:00+00:00",
    )
    assert result["header"]["as_of_date"] == "2026-09-26"
    assert result["header"]["sources_used"] == []
    for key in ("1_ฝน", "2_น้ำเหนือ", "3_น้ำทะเลหนุน", "4_การระบาย"):
        assert key in result["factors"]
    # every Sammakorn fixed node is present, tagged OPEN when the store has nothing
    all_codes = [r["station_code"] for rows in result["sammakorn_nodes"].values() for r in rows]
    assert "WL.SSB.07" in all_codes
    assert all(r["tag"] == "OPEN" for rows in result["sammakorn_nodes"].values() for r in rows)


def test_render_markdown_empty_store_no_crash(conn):
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    md = readout.render_markdown(result)
    assert "# Sammakorn live flood-context readout" in md
    assert "ไม่มีสูตรหรือคะแนนความเสี่ยง" in md  # no-formula epistemic notice always present


def test_no_score_or_formula_language_anywhere_in_output(conn):
    """Epistemic floor: this readout must never present a computed risk score."""
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    md = readout.render_markdown(result)
    forbidden = ["risk_score", "flood_score", "risk score:", "danger level:"]
    for term in forbidden:
        assert term not in md.lower()


def _seed_fixture_store(conn):
    fetched = "2026-09-26T04:00:00+00:00"
    # a MEASURED live canal reading near the centre, matching a Sammakorn fixed node
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.07",
        station_name="ค.แสนแสบ-สนข.บางกะปิ", lat=13.76509, lon=100.64791,
        variable="canal_water_level_m", value=0.40, unit="m",
        observed_at_utc="2026-09-25T13:05:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_telemetry", warning=0.50, critical=0.80, bank=1.20,
        status="NORMAL")
    # a MEASURED pump reading for one Sammakorn pump
    store.insert_observation(
        conn, source_id="bma_pumphistory", station_code="ST.SPS.01",
        station_name="สถานีสูบน้ำสัมมากร", lat=13.759, lon=100.677,
        variable="pump_level_m", value=0.9, unit="m",
        observed_at_utc="2026-09-26T02:00:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_telemetry", status="ปกติ",
        provenance={"pumps_on": 2, "pumps_total": 4, "gate_open_m": None})
    # a dds_daily_pdf rain reading
    store.insert_observation(
        conn, source_id="dds_daily_pdf", station_name="สำนักงานเขตสะพานสูง",
        variable="rain_24h_mm", value=203.5, unit="mm",
        observed_at_utc="2026-09-26T00:00:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_report")
    # a contradicting dds_daily_pdf canal reading whose station name normalizes to the
    # EXACT same string as the thaiwater station above ("คลอง"/"ค." are both stripped as
    # junk words by _normalize_name, so "คลองแสนแสบ-สนข.บางกะปิ" here and
    # "ค.แสนแสบ-สนข.บางกะปิ" above both normalize to "แสนแสบ-สนข.บางกะปิ") -- a real
    # exact-name candidate match, not the fuzzy-ratio false-positive pattern (matching two
    # DIFFERENT physical stations that merely share a canal name) this pairing logic no
    # longer allows.
    store.insert_observation(
        conn, source_id="dds_daily_pdf", station_name="คลองแสนแสบ-สนข.บางกะปิ",
        variable="canal_level_0700_m", value=0.90, unit="m",
        observed_at_utc="2026-09-26T00:00:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_report", critical=0.45, status="ระดับน้ำวิกฤติ")


def test_build_readout_with_fixture_store(conn):
    _seed_fixture_store(conn)
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    assert "thaiwater_canal_waterlevel" in result["header"]["sources_used"]
    rain_rows = result["factors"]["1_ฝน"]["measured"]
    assert any(r["value"] == 203.5 for r in rain_rows)
    ssb07 = next(r for r in result["sammakorn_nodes"]["north (แสนแสบ)"]
                if r["station_code"] == "WL.SSB.07")
    assert ssb07["tag"] == "MEASURED"
    assert ssb07["value_m"] == 0.40
    pump01 = next(r for r in result["sammakorn_nodes"]["in-basin pumps (ST.SPS)"]
                 if r["station_code"] == "ST.SPS.01")
    assert pump01["pumps_on"] == 2


def test_contradiction_detected_between_dds_and_thaiwater_same_station(conn):
    _seed_fixture_store(conn)
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    assert len(result["contradictions"]) >= 1
    c = result["contradictions"][0]
    assert c["topic"] == "canal_level_same_name_candidate"
    # a name-only candidate pairing is never asserted as a confirmed match
    assert c["tag"] == "INSTINCT"
    # never resolved to a single value -- both sides present
    assert c["value_a"] is not None and c["value_b"] is not None


def test_contradiction_not_fabricated_from_a_none_value(conn):
    """A missing (None) value on either side must never be coerced to 0 and compared --
    that used to be able to manufacture a contradiction out of missing data."""
    fetched = "2026-09-26T04:00:00+00:00"
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.X.01",
        station_name="ค.ทดสอบ", lat=13.76, lon=100.68, variable="canal_water_level_m",
        value=None, unit="m", observed_at_utc="2026-09-26T00:00:00+00:00",
        fetched_at_utc=fetched, trust_tier="official_telemetry")
    store.insert_observation(
        conn, source_id="dds_daily_pdf", station_name="คลองทดสอบ",
        variable="canal_level_0700_m", value=0.90, unit="m",
        observed_at_utc="2026-09-26T00:00:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_report")
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    assert result["contradictions"] == []


def test_sammakorn_node_shows_latest_not_oldest_reading(conn):
    """B4 regression: with two readings for the same fixed-node station (an old one and a
    fresh one), the node must show the LATEST, never the oldest."""
    fetched = "2026-09-26T04:00:00+00:00"
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.07",
        station_name="ค.แสนแสบ-สนข.บางกะปิ", lat=13.76509, lon=100.64791,
        variable="canal_water_level_m", value=0.10, unit="m",
        observed_at_utc="2026-09-20T00:00:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_telemetry")
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.07",
        station_name="ค.แสนแสบ-สนข.บางกะปิ", lat=13.76509, lon=100.64791,
        variable="canal_water_level_m", value=0.99, unit="m",
        observed_at_utc="2026-09-26T00:00:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_telemetry")
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    ssb07 = next(r for r in result["sammakorn_nodes"]["north (แสนแสบ)"]
                if r["station_code"] == "WL.SSB.07")
    assert ssb07["value_m"] == 0.99
    assert ssb07["observed_at_utc"] == "2026-09-26T00:00:00+00:00"


def test_stale_reading_tagged_stale_not_measured(conn):
    """B4 regression: a reading far older than lwl.STALE_HOURS must be tagged STALE, never
    presented as a fresh MEASURED reading."""
    import live_water_level as lwl
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.SSB.07",
        station_name="ค.แสนแสบ-สนข.บางกะปิ", lat=13.76509, lon=100.64791,
        variable="canal_water_level_m", value=-2.00, unit="m",
        observed_at_utc="2026-06-09T05:10:00+00:00",
        fetched_at_utc="2026-09-26T04:00:00+00:00", trust_tier="official_telemetry")
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    ssb07 = next(r for r in result["sammakorn_nodes"]["north (แสนแสบ)"]
                if r["station_code"] == "WL.SSB.07")
    assert ssb07["tag"] == "STALE"
    assert ssb07["age_h"] > lwl.STALE_HOURS


def test_tide_table_filtered_by_local_not_utc_date(conn):
    """B5 regression: the tide table's `observed_at_utc LIKE '<as_of_date>%'` used to
    filter on the UTC date of a UTC-stored instant, dropping/shifting early-local-morning
    readings. Filtering by Bangkok-LOCAL date must keep a 01:26 local reading for the
    as-of date (stored as the previous UTC day) and exclude the FOLLOWING local day's
    early reading (stored as this UTC day)."""
    fetched = "2026-09-26T04:00:00+00:00"
    store.insert_observation(  # 26 Sep 01:26 local -> 25 Sep 18:26 UTC
        conn, source_id="dds_tide_pdf", station_code="NAVY_HYDRO_HQ",
        variable="tide_lw_am_level_m", value=-0.05,
        observed_at_utc="2026-09-25T18:26:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_report")
    store.insert_observation(  # 27 Sep 01:55 local -> 26 Sep 18:55 UTC
        conn, source_id="dds_tide_pdf", station_code="NAVY_HYDRO_HQ",
        variable="tide_lw_am_level_m", value=-0.22,
        observed_at_utc="2026-09-26T18:55:00+00:00", fetched_at_utc=fetched,
        trust_tier="official_report")
    result = readout.build_readout(conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26")
    tide_rows = [r for r in result["factors"]["3_น้ำทะเลหนุน"]["official_forecast"]
                 if r["source"] == "dds_tide_pdf"]
    values = {r["value"] for r in tide_rows}
    assert -0.05 in values
    assert -0.22 not in values


def test_write_readout_creates_md_and_json(conn, tmp_path):
    _seed_fixture_store(conn)
    out_dir = tmp_path / "output"
    md_path, json_path, result = readout.write_readout(
        conn, CENTRE_LAT, CENTRE_LON, 5.0, as_of_date="2026-09-26", out_dir=out_dir)
    assert md_path.exists() and json_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded["header"]["as_of_date"] == "2026-09-26"
