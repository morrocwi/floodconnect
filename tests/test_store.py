"""Tests for store.py -- schema, insert/dedupe, query helpers. No network calls."""
import sqlite3

import pytest

import store


@pytest.fixture()
def conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


def test_schema_creates_all_three_tables(conn):
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"observations", "documents", "contradictions"} <= tables


def test_insert_observation_returns_true_on_new_row(conn):
    inserted = store.insert_observation(
        conn, source_id="test_src", station_code="WL.TEST.01", variable="level_m",
        value=1.23, observed_at_utc="2026-09-26T00:00:00+00:00",
        fetched_at_utc="2026-09-26T00:05:00+00:00", trust_tier="official_telemetry")
    assert inserted is True
    row = conn.execute("SELECT * FROM observations").fetchone()
    assert row["value"] == 1.23


def test_insert_observation_dedupes_identical_identity(conn):
    kwargs = dict(source_id="test_src", station_code="WL.TEST.01", variable="level_m",
                  observed_at_utc="2026-09-26T00:00:00+00:00",
                  fetched_at_utc="2026-09-26T00:05:00+00:00",
                  trust_tier="official_telemetry")
    first = store.insert_observation(conn, value=1.23, **kwargs)
    second = store.insert_observation(conn, value=9.99, **kwargs)  # same identity, different value
    assert first is True
    assert second is False  # append-only: never overwrites
    rows = conn.execute("SELECT * FROM observations").fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == 1.23  # original value preserved, not overwritten


def test_insert_observation_different_station_not_deduped(conn):
    kwargs = dict(source_id="test_src", variable="level_m",
                  observed_at_utc="2026-09-26T00:00:00+00:00",
                  fetched_at_utc="2026-09-26T00:05:00+00:00",
                  trust_tier="official_telemetry")
    store.insert_observation(conn, station_code="A", value=1.0, **kwargs)
    store.insert_observation(conn, station_code="B", value=2.0, **kwargs)
    rows = conn.execute("SELECT * FROM observations").fetchall()
    assert len(rows) == 2


def test_insert_document(conn):
    doc_id = store.insert_document(conn, source_id="test_src",
                                    fetched_at_utc="2026-09-26T00:00:00+00:00",
                                    text="some raw prose", section="narrative_log")
    assert doc_id > 0
    row = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    assert row["text"] == "some raw prose"


def test_insert_observation_dedupes_when_station_code_is_null(conn):
    """B7 regression: many dds_daily_pdf rows carry station_code=None by design (rain,
    canal_outer/inner). SQLite treats every NULL as distinct in a UNIQUE index, so a plain
    (source_id, station_code, variable, observed_at_utc) key never caught a re-collect of
    these rows as a duplicate. The identity key must fall back to station_name when
    station_code is NULL."""
    kwargs = dict(source_id="dds_daily_pdf", station_code=None,
                  station_name="สำนักงานเขตสะพานสูง", variable="rain_24h_mm", value=203.5,
                  unit="mm", observed_at_utc="2026-09-26T00:00:00+00:00",
                  fetched_at_utc="2026-09-26T04:00:00+00:00", trust_tier="official_report")
    first = store.insert_observation(conn, **kwargs)
    second = store.insert_observation(conn, **kwargs)
    assert first is True
    assert second is False
    rows = conn.execute("SELECT * FROM observations").fetchall()
    assert len(rows) == 1


def test_insert_contradiction_idempotent_across_reruns(conn):
    """B7 regression: a prior version had no identity key on `contradictions` at all, so
    every `readout.py` run re-inserted the same comparison and the table grew without
    bound (a real run: 8 contradictions became 16 after one extra run). Passing the same
    observed_a_utc/observed_b_utc pair twice must be a no-op the second time."""
    kwargs = dict(topic="canal_level_same_name_candidate", source_a="dds_daily_pdf",
                  value_a=1.0, observed_a_utc="2026-09-26T00:00:00+00:00",
                  source_b="thaiwater_canal_waterlevel", value_b=1.5,
                  observed_b_utc="2026-09-25T13:05:00+00:00", note="not resolved")
    store.insert_contradiction(conn, observed_at_utc="2026-09-26T05:00:00+00:00", **kwargs)
    store.insert_contradiction(conn, observed_at_utc="2026-09-26T06:00:00+00:00", **kwargs)
    rows = conn.execute("SELECT * FROM contradictions").fetchall()
    assert len(rows) == 1


def test_insert_contradiction_never_resolves(conn):
    store.insert_contradiction(
        conn, observed_at_utc="2026-09-26T00:00:00+00:00", topic="canal_level_same_station",
        source_a="src_a", value_a=1.0, source_b="src_b", value_b=1.5, note="not resolved")
    rows = store.query_contradictions(conn)
    assert len(rows) == 1
    assert rows[0]["value_a"] == "1.0"
    assert rows[0]["value_b"] == "1.5"


def test_query_observations_filters_by_source(conn):
    store.insert_observation(conn, source_id="A", variable="v", station_code="s",
                              observed_at_utc="2026-09-26T00:00:00+00:00",
                              fetched_at_utc="2026-09-26T00:00:00+00:00",
                              trust_tier="official_telemetry", value=1.0)
    store.insert_observation(conn, source_id="B", variable="v", station_code="s",
                              observed_at_utc="2026-09-26T00:00:00+00:00",
                              fetched_at_utc="2026-09-26T00:00:00+00:00",
                              trust_tier="official_telemetry", value=2.0)
    rows = store.query_observations(conn, source_id="A")
    assert len(rows) == 1
    assert rows[0]["source_id"] == "A"


def test_query_observations_near_filters_by_radius(conn):
    # Sammakorn centre ~13.758235, 100.676084 -- one station 100 m away, one ~50 km away
    store.insert_observation(conn, source_id="A", variable="v", station_code="near",
                              lat=13.7590, lon=100.6765,
                              observed_at_utc="2026-09-26T00:00:00+00:00",
                              fetched_at_utc="2026-09-26T00:00:00+00:00",
                              trust_tier="official_telemetry", value=1.0)
    store.insert_observation(conn, source_id="A", variable="v", station_code="far",
                              lat=14.2, lon=101.2,
                              observed_at_utc="2026-09-26T00:00:00+00:00",
                              fetched_at_utc="2026-09-26T00:00:00+00:00",
                              trust_tier="official_telemetry", value=2.0)
    rows = store.query_observations(conn, near=(13.758235, 100.676084, 5.0))
    codes = {r["station_code"] for r in rows}
    assert codes == {"near"}


def test_export_csv_last_24h(conn, tmp_path):
    store.insert_observation(conn, source_id="A", variable="v", station_code="s",
                              observed_at_utc="2026-09-26T00:00:00+00:00",
                              fetched_at_utc=store._utcnow(),
                              trust_tier="official_telemetry", value=1.0)
    out = tmp_path / "export.csv"
    n = store.export_csv_last_24h(conn, out)
    assert n == 1
    assert out.exists()
    assert "station_code" in out.read_text(encoding="utf-8")
