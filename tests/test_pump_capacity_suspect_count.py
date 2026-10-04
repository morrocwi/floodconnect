"""Tests for the `capacity_m3s_suspect_count` column (TODO #51, 2026-09-27) -- store.py's
`assets` table schema addition covering the 91-row pump-count-vs-capacity confusion found
in the bma_plan2569 extraction (e.g. อุโมงค์บางซื่อ: repo capacity_m3s=6 turned out to be
the PUMP COUNT, plan states 60 m3/s from 6 machines). Uses a tmp sqlite fixture built via
store.connect()/upsert_asset(), never the real repo-wide data/observations.sqlite or the
network -- same convention as tests/test_capacity_ledger.py and friends.

NOTE (2026-09-27): the same `capacity_m3s == pumps_total` query pattern used here also
surfaces 7 pumphistory-sourced rows in the real store NOT among the 91 TODO #51 fixed
this check (ST.DST.01, ST.BSU.01/02, ST.PYT.02, ST.BKN.06, ST.BPD.04/05) -- these ARE
named in the bma_plan2569 plan text too (p.175-205) with capacity figures that look
different from the pump count (e.g. คลองบางเขนเก่า/ST.BSU.01: plan parses as 9.0 m3/s,
repo holds 3.0 == its pumps_total), but they were not linked by the extraction step's
own `repo_match` field (that linking covered water_station.csv-sourced asset_ids, not
every pumphistory-sourced one), and at least one plan row for this set parsed
ambiguously (สถานีสูบน้ำคลองวัดศรีสุดาราม, p.202). Left uncorrected and OPEN rather than
guessed at -- a future task should re-run this same cross-check against
docs/knowledge/bma_plan2569_control_structures.yaml by NAME (not just repo_match) to
close these 7.
"""
import sqlite3
from pathlib import Path

import pytest

import store


def _rows_with_unflagged_pump_count_as_capacity(conn):
    """The invariant this file protects: a pump_station row whose capacity_m3s equals its
    own pumps_total is either (a) a real coincidence where the plant happens to be rated
    1 m3/s per machine (fine, capacity_m3s_suspect_count stays NULL), or (b) an
    unconverted pump-count mistake -- this repo can't tell which from the number alone,
    so the rule is: ANY such row must have capacity_m3s_suspect_count populated once
    reviewed, recording that it was checked (even if the coincidence is real and nothing
    changed). This helper returns rows that look like case (a)/(b) but were never
    reviewed at all."""
    return conn.execute(
        "SELECT asset_id FROM assets "
        "WHERE class = 'pump_station' "
        "AND capacity_m3s IS NOT NULL AND pumps_total IS NOT NULL "
        "AND capacity_m3s = pumps_total "
        "AND capacity_m3s_suspect_count IS NULL"
    ).fetchall()


def test_capacity_m3s_suspect_count_column_exists_and_defaults_null(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    store.ensure_assets_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(assets)").fetchall()}
    assert "capacity_m3s_suspect_count" in cols
    store.upsert_asset(conn, asset_id="pump_station:test:1", klass="pump_station",
                        tag="VERIFIED", name_th="test", pumps_total=6, capacity_m3s=60.0)
    row = conn.execute(
        "SELECT capacity_m3s_suspect_count FROM assets WHERE asset_id = ?",
        ("pump_station:test:1",),
    ).fetchone()
    assert row["capacity_m3s_suspect_count"] is None


def test_flags_row_where_capacity_equals_pump_count_unreviewed(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    store.ensure_assets_schema(conn)
    # correct row: capacity_m3s (60) != pumps_total (6) -- never flagged
    store.upsert_asset(conn, asset_id="pump_station:test:ok", klass="pump_station",
                        tag="VERIFIED", pumps_total=6, capacity_m3s=60.0)
    # already-reviewed/corrected row: capacity_m3s happens to equal pumps_total (1:1
    # rating) but capacity_m3s_suspect_count is set, recording that this was checked
    conn.execute(
        "UPDATE assets SET capacity_m3s_suspect_count = 4.0 WHERE asset_id = ?",
        ("pump_station:test:ok",),
    )
    # unreviewed suspect row: capacity_m3s (6) == pumps_total (6), never flagged --
    # this is exactly the TODO #51 bug pattern (e.g. อุโมงค์บางซื่อ pre-correction)
    store.upsert_asset(conn, asset_id="pump_station:test:suspect", klass="pump_station",
                        tag="VERIFIED", pumps_total=6, capacity_m3s=6.0)
    flagged = _rows_with_unflagged_pump_count_as_capacity(conn)
    assert [r["asset_id"] for r in flagged] == ["pump_station:test:suspect"]


def test_correction_moves_old_value_to_suspect_count_and_clears_the_flag(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    store.ensure_assets_schema(conn)
    store.upsert_asset(conn, asset_id="pump_station:test:tunnel", klass="pump_station",
                        tag="VERIFIED", name_th="อุโมงค์บางซื่อ", pumps_total=6,
                        capacity_m3s=6.0)
    assert _rows_with_unflagged_pump_count_as_capacity(conn)  # starts flagged
    # apply the same correction shape as the real TODO #51 one-off script: old value ->
    # capacity_m3s_suspect_count, plan's m3/s -> capacity_m3s
    conn.execute(
        "UPDATE assets SET capacity_m3s_suspect_count = capacity_m3s, capacity_m3s = ? "
        "WHERE asset_id = ?",
        (60.0, "pump_station:test:tunnel"),
    )
    assert not _rows_with_unflagged_pump_count_as_capacity(conn)  # no longer flagged
    row = conn.execute(
        "SELECT capacity_m3s, capacity_m3s_suspect_count FROM assets WHERE asset_id = ?",
        ("pump_station:test:tunnel",),
    ).fetchone()
    assert row["capacity_m3s"] == 60.0
    assert row["capacity_m3s_suspect_count"] == 6.0  # old (suspect) value preserved, never deleted


def test_real_repo_todo51_corrected_rows_have_suspect_count_set():
    """Integration check against the REAL data/observations.sqlite, deliberately the one
    exception to this file's tmp-fixture convention: TODO #51 (2026-09-27) corrected 91
    live pump_station rows in place (old pump-count value moved to
    capacity_m3s_suspect_count, plan's own m3/s written to capacity_m3s, tag VERIFIED --
    see sources/capacity_ledger.yaml led:pump_bmakstations_summary_corrected). This test
    is the guard against that specific correction silently regressing on a future
    harvest re-run (see assets_registry.py's KNOWN ISSUE comment in
    harvest_water_station_csv()) -- scoped to those 91 known asset_ids, NOT a blanket
    claim that every pump_station row is now reviewed (7 more candidate rows were found
    by this same query pattern during TODO #51 but are NOT yet cross-checked against the
    plan and are deliberately left alone here -- see this file's own module note and
    sources/capacity_ledger.yaml's led:pump_bmakstations_summary_corrected notes for
    that count, never silently promoted to 'fixed'). Skips cleanly if the live db file
    doesn't exist in this environment (e.g. a fresh checkout with no data/ yet) -- never
    fabricates a result."""
    db_path = Path(__file__).resolve().parent.parent / "data" / "observations.sqlite"
    if not db_path.is_file():
        pytest.skip(
            "data/observations.sqlite absent (gitignored live store, not present on a "
            "fresh clone) -- this check only applies against a populated local DB"
        )
    # Genuinely read-only (sqlite3 URI mode=ro), deliberately NOT store.connect() --
    # store.connect() always runs schema-ensure DDL (ALTER/DROP INDEX/CREATE INDEX)
    # even against an already-up-to-date schema, which can rewrite the real tracked
    # file's bytes as a side effect. This check only ever SELECTs.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='assets'"
    ).fetchone()
    if table_exists is None:
        pytest.skip(
            "data/observations.sqlite exists but has no 'assets' table (e.g. an empty "
            "db vivified by another test/module import) -- this check only applies "
            "against a populated local DB"
        )
    assets_count = conn.execute("SELECT COUNT(*) AS n FROM assets").fetchone()["n"]
    if assets_count == 0:
        pytest.skip(
            "data/observations.sqlite's 'assets' table is empty -- this check only "
            "applies against a populated local DB"
        )
    corrected = conn.execute(
        "SELECT asset_id FROM assets WHERE class = 'pump_station' "
        "AND capacity_m3s_suspect_count IS NOT NULL"
    ).fetchall()
    ids = [r["asset_id"] for r in corrected]
    assert len(ids) >= 91, (
        f"expected >= 91 TODO #51-corrected pump_station rows, found {len(ids)} -- "
        "a future harvest re-run may have reset capacity_m3s_suspect_count"
    )
    # every corrected row must actually have a DIFFERENT capacity_m3s now (the whole
    # point of the correction) -- never a suspect_count set but capacity_m3s unchanged
    unmoved = conn.execute(
        "SELECT asset_id FROM assets WHERE class = 'pump_station' "
        "AND capacity_m3s_suspect_count IS NOT NULL "
        "AND capacity_m3s = capacity_m3s_suspect_count"
    ).fetchall()
    assert unmoved == [], f"corrected in name only: {[r['asset_id'] for r in unmoved]}"
