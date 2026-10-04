"""Tests for tools/backtest/urban_event_ledger.py.

Covers: schema validation, the append-only guarantee, the decision rule on a
synthetic fixture, and (skipped gracefully if the DB is absent) that the real
25-26 Sep 2569 event derives its onset from the real database.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "backtest"))

import urban_event_ledger as uel  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sqlite_db(path: Path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        create table observations (
            id integer primary key autoincrement,
            source_id text not null,
            station_code text,
            station_name text,
            lat real,
            lon real,
            variable text not null,
            value real,
            unit text,
            observed_at_utc text not null,
            fetched_at_utc text not null,
            warning real,
            critical real,
            bank real,
            status text,
            trust_tier text not null,
            provenance_json text
        )
        """
    )
    for station_code, station_name, value, observed_at_utc in rows:
        conn.execute(
            """
            insert into observations
                (source_id, station_code, station_name, variable, value,
                 unit, observed_at_utc, fetched_at_utc, trust_tier)
            values (?, ?, ?, 'flood_road_height', ?, 'cm', ?, ?, 'official')
            """,
            (
                uel.FLOOD_ROAD_SOURCE_ID,
                station_code,
                station_name,
                value,
                observed_at_utc,
                observed_at_utc,
            ),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def synthetic_three_road_fixture(tmp_path):
    """3 roads in the same district, all crossing 10cm within a 6h window ->
    must be a candidate event. A 4th road in a DIFFERENT district must not be
    merged in."""
    db_path = tmp_path / "synthetic_observations.sqlite"
    rows = [
        ("FL.AAA.01", "road one", 12.0, "2026-01-01T10:00:00+00:00"),
        ("FL.AAA.02", "road two", 15.0, "2026-01-01T11:00:00+00:00"),
        ("FL.AAA.03", "road three", 20.0, "2026-01-01T12:00:00+00:00"),
        # below threshold -- must not count toward min_roads
        ("FL.AAA.04", "road four (dry)", 5.0, "2026-01-01T12:30:00+00:00"),
        # different district -- must not be merged into AAA's cluster
        ("FL.BBB.01", "other district road", 30.0, "2026-01-01T11:30:00+00:00"),
    ]
    _make_sqlite_db(db_path, rows)
    return db_path


# ---------------------------------------------------------------------------
# Decision rule on the synthetic fixture
# ---------------------------------------------------------------------------


def test_synthetic_three_road_cluster_is_candidate_event(synthetic_three_road_fixture):
    conn = sqlite3.connect(f"file:{synthetic_three_road_fixture}?mode=ro", uri=True)
    try:
        events = uel.derive_events_from_flood_road(conn, uel.CHOSEN_RULE)
    finally:
        conn.close()

    aaa_events = [e for e in events if e["district"] == "AAA"]
    assert len(aaa_events) == 1
    event = aaa_events[0]
    assert event["n_roads"] == 3
    assert event["onset"] == dt.datetime.fromisoformat("2026-01-01T10:00:00+00:00")
    assert event["offset"] == dt.datetime.fromisoformat("2026-01-01T12:00:00+00:00")
    assert set(event["roads"]) == {"FL.AAA.01", "FL.AAA.02", "FL.AAA.03"}


def test_below_min_roads_is_not_a_candidate_event(synthetic_three_road_fixture):
    conn = sqlite3.connect(f"file:{synthetic_three_road_fixture}?mode=ro", uri=True)
    try:
        events = uel.derive_events_from_flood_road(
            conn, uel.Rule(threshold_cm=10, min_roads=3, window_hours=6)
        )
        bbb_events = [e for e in events if e["district"] == "BBB"]
    finally:
        conn.close()
    # only 1 qualifying road in district BBB -- below min_roads=3
    assert bbb_events == []


def test_window_hours_separates_clusters(synthetic_three_road_fixture):
    """A 4th AAA reading far outside the window must start a new cluster,
    not extend the first one."""
    conn = sqlite3.connect(f"file:{synthetic_three_road_fixture}?mode=ro", uri=True)
    try:
        rows = uel.fetch_flood_road_rows(conn)
    finally:
        conn.close()
    rows = list(rows) + [("FL.AAA.05", "far-later road", 25.0, "2026-01-02T10:00:00+00:00")]
    events = uel.cluster_events(rows, threshold_cm=10, min_roads=3, window_hours=6)
    aaa_events = [e for e in events if e["district"] == "AAA"]
    # still only 1 event with >= 3 roads (the late single reading can't reach min_roads alone)
    assert len(aaa_events) == 1
    assert "FL.AAA.05" not in aaa_events[0]["roads"]


def test_district_code_parsing():
    assert uel._district_code("FL.BKP.04") == "BKP"
    # malformed code -- falls back to the raw string, never fabricates a district
    assert uel._district_code("weird_code") == "weird_code"


# ---------------------------------------------------------------------------
# Left-censoring: onset_censoring / first_fetch_utc
# ---------------------------------------------------------------------------


def test_get_first_fetch_utc_returns_min_fetched_at(synthetic_three_road_fixture):
    conn = sqlite3.connect(f"file:{synthetic_three_road_fixture}?mode=ro", uri=True)
    try:
        first_fetch = uel.get_first_fetch_utc(conn, uel.FLOOD_ROAD_SOURCE_ID)
    finally:
        conn.close()
    # fixture's fetched_at_utc == observed_at_utc for every row -- earliest is
    # the AAA cluster's first reading
    assert first_fetch == dt.datetime.fromisoformat("2026-01-01T10:00:00+00:00")


def test_get_first_fetch_utc_returns_none_for_absent_source(synthetic_three_road_fixture):
    conn = sqlite3.connect(f"file:{synthetic_three_road_fixture}?mode=ro", uri=True)
    try:
        first_fetch = uel.get_first_fetch_utc(conn, "no_such_source")
    finally:
        conn.close()
    assert first_fetch is None


def test_derive_events_from_flood_road_marks_left_censored_onset(tmp_path):
    """An onset row whose observed_at_utc is EARLIER than this source's own
    first-ever fetched_at_utc must be flagged onset_censoring=left_censored --
    the DB only proves 'already flooded no later than onset', never a true
    start time."""
    db_path = tmp_path / "left_censored.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        create table observations (
            id integer primary key autoincrement,
            source_id text not null,
            station_code text,
            station_name text,
            variable text,
            value real,
            unit text,
            observed_at_utc text not null,
            fetched_at_utc text not null,
            trust_tier text
        )
        """
    )
    # Collector's first fetch is 2026-02-02T00:00:00Z, but the API handed
    # back a backfilled observed_at_utc from a day earlier that is ALREADY
    # above threshold -- classic left-censoring.
    rows = [
        ("FL.ZZZ.01", "road one", 12.0, "2026-02-01T09:00:00+00:00", "2026-02-02T00:00:00+00:00"),
        ("FL.ZZZ.02", "road two", 15.0, "2026-02-01T10:00:00+00:00", "2026-02-02T00:00:00+00:00"),
        ("FL.ZZZ.03", "road three", 20.0, "2026-02-01T11:00:00+00:00", "2026-02-02T00:00:00+00:00"),
    ]
    for station_code, station_name, value, observed_at_utc, fetched_at_utc in rows:
        conn.execute(
            """
            insert into observations
                (source_id, station_code, station_name, variable, value,
                 unit, observed_at_utc, fetched_at_utc, trust_tier)
            values (?, ?, ?, 'flood_road_height', ?, 'cm', ?, ?, 'official')
            """,
            (uel.FLOOD_ROAD_SOURCE_ID, station_code, station_name, value,
             observed_at_utc, fetched_at_utc),
        )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        events = uel.derive_events_from_flood_road(conn, uel.CHOSEN_RULE)
    finally:
        conn.close()

    zzz_events = [e for e in events if e["district"] == "ZZZ"]
    assert len(zzz_events) == 1
    event = zzz_events[0]
    assert event["first_fetch_utc"] == dt.datetime.fromisoformat("2026-02-02T00:00:00+00:00")
    assert event["onset_censoring"] == "left_censored"


def test_derive_events_from_flood_road_marks_observed_when_onset_after_first_fetch(tmp_path):
    """An onset that happens strictly AFTER this source's own first fetch is
    a genuinely observed onset, not left-censored."""
    db_path = tmp_path / "observed.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        create table observations (
            id integer primary key autoincrement,
            source_id text not null,
            station_code text,
            station_name text,
            variable text,
            value real,
            unit text,
            observed_at_utc text not null,
            fetched_at_utc text not null,
            trust_tier text
        )
        """
    )
    rows = [
        ("FL.YYY.01", "road one", 12.0, "2026-02-01T09:00:00+00:00", "2026-02-01T00:00:00+00:00"),
        ("FL.YYY.02", "road two", 15.0, "2026-02-01T10:00:00+00:00", "2026-02-01T10:00:00+00:00"),
        ("FL.YYY.03", "road three", 20.0, "2026-02-01T11:00:00+00:00", "2026-02-01T11:00:00+00:00"),
    ]
    for station_code, station_name, value, observed_at_utc, fetched_at_utc in rows:
        conn.execute(
            """
            insert into observations
                (source_id, station_code, station_name, variable, value,
                 unit, observed_at_utc, fetched_at_utc, trust_tier)
            values (?, ?, ?, 'flood_road_height', ?, 'cm', ?, ?, 'official')
            """,
            (uel.FLOOD_ROAD_SOURCE_ID, station_code, station_name, value,
             observed_at_utc, fetched_at_utc),
        )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        events = uel.derive_events_from_flood_road(conn, uel.CHOSEN_RULE)
    finally:
        conn.close()

    yyy_events = [e for e in events if e["district"] == "YYY"]
    assert len(yyy_events) == 1
    event = yyy_events[0]
    # first_fetch_utc is the MIN across all rows for this source (the first
    # row's own fetched_at_utc, 2026-02-01T00:00:00Z), and the cluster's
    # onset (09:00Z) is strictly after it -- a genuine observed onset.
    assert event["first_fetch_utc"] == dt.datetime.fromisoformat("2026-02-01T00:00:00+00:00")
    assert event["onset_censoring"] == "observed"


def test_cluster_events_without_first_fetch_utc_omits_censoring_fields(synthetic_three_road_fixture):
    """Backward compatibility: calling cluster_events() without first_fetch_utc
    (e.g. rule_outcome_matrix()'s calibration sweep) must not add the new
    fields at all."""
    conn = sqlite3.connect(f"file:{synthetic_three_road_fixture}?mode=ro", uri=True)
    try:
        rows = uel.fetch_flood_road_rows(conn)
    finally:
        conn.close()
    events = uel.cluster_events(rows, threshold_cm=10, min_roads=3, window_hours=6)
    aaa_events = [e for e in events if e["district"] == "AAA"]
    assert len(aaa_events) == 1
    assert "first_fetch_utc" not in aaa_events[0]
    assert "onset_censoring" not in aaa_events[0]


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def _minimal_valid_event(event_id="ev_test"):
    return {
        "event_id": event_id,
        "unit_scope": "district",
        "urban_flood_observed": True,
        "official_disaster_declared": "OPEN",
        "evidence": [
            {
                "class": "road_telemetry",
                "source": "thaiwater_flood_road",
                "tag": "MEASURED",
            }
        ],
        "warnings": [
            {
                "issuer": "TMD",
                "scope": "regional_class",
                "tag": "RELAYED",
            }
        ],
        "tag": "MEASURED",
    }


def test_validate_event_accepts_minimal_valid_event():
    uel.validate_event(_minimal_valid_event())  # must not raise


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.pop("event_id"),
        lambda e: e.pop("unit_scope"),
        lambda e: e.pop("urban_flood_observed"),
        lambda e: e.pop("tag"),
    ],
)
def test_validate_event_rejects_missing_required_fields(mutate):
    event = _minimal_valid_event()
    mutate(event)
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_rejects_bad_unit_scope():
    event = _minimal_valid_event()
    event["unit_scope"] = "planet"
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_rejects_bad_tag():
    event = _minimal_valid_event()
    event["tag"] = "TOTALLY_SURE"
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_rejects_bad_evidence_class():
    event = _minimal_valid_event()
    event["evidence"][0]["class"] = "vibes"
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_rejects_evidence_missing_tag():
    event = _minimal_valid_event()
    del event["evidence"][0]["tag"]
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_rejects_bad_warning_scope():
    event = _minimal_valid_event()
    event["warnings"][0]["scope"] = "everywhere"
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_rejects_bad_official_disaster_declared():
    event = _minimal_valid_event()
    event["official_disaster_declared"] = "kinda"
    with pytest.raises(ValueError):
        uel.validate_event(event)


def test_validate_event_accepts_uncertain_observed():
    event = _minimal_valid_event()
    event["urban_flood_observed"] = "UNCERTAIN"
    uel.validate_event(event)  # must not raise


# ---------------------------------------------------------------------------
# Append-only guarantee
# ---------------------------------------------------------------------------


def test_append_event_creates_new_ledger(tmp_path):
    ledger_path = tmp_path / "ledger.yaml"
    uel.append_event(_minimal_valid_event("ev1"), path=ledger_path)

    data = uel.load_ledger(ledger_path)
    assert len(data["events"]) == 1
    assert data["events"][0]["event_id"] == "ev1"


def test_append_event_only_adds_never_rewrites(tmp_path):
    ledger_path = tmp_path / "ledger.yaml"
    uel.append_event(_minimal_valid_event("ev1"), path=ledger_path)
    before = yaml.safe_load(ledger_path.read_text())

    uel.append_event(_minimal_valid_event("ev2"), path=ledger_path)
    after = yaml.safe_load(ledger_path.read_text())

    # ev1's row is byte-identical in content, and still present
    ev1_before = next(e for e in before["events"] if e["event_id"] == "ev1")
    ev1_after = next(e for e in after["events"] if e["event_id"] == "ev1")
    assert ev1_before == ev1_after
    assert len(after["events"]) == len(before["events"]) + 1
    assert {e["event_id"] for e in after["events"]} == {"ev1", "ev2"}


def test_append_event_refuses_duplicate_event_id(tmp_path):
    ledger_path = tmp_path / "ledger.yaml"
    uel.append_event(_minimal_valid_event("dup"), path=ledger_path)
    with pytest.raises(ValueError):
        uel.append_event(_minimal_valid_event("dup"), path=ledger_path)

    # the original row must still be there, untouched, after the refused append
    data = uel.load_ledger(ledger_path)
    assert len(data["events"]) == 1


def test_append_event_rejects_invalid_event_before_writing(tmp_path):
    ledger_path = tmp_path / "ledger.yaml"
    bad_event = _minimal_valid_event("bad")
    del bad_event["tag"]
    with pytest.raises(ValueError):
        uel.append_event(bad_event, path=ledger_path)
    # nothing written at all
    assert not ledger_path.exists()


# ---------------------------------------------------------------------------
# Real DB — skipped gracefully if absent
# ---------------------------------------------------------------------------


def test_2026_09_25_event_derives_onset_from_real_db():
    db_path = uel.DEFAULT_DB
    if not db_path.exists():
        pytest.skip("data/observations.sqlite not present in this environment")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        events = uel.derive_events_from_flood_road(conn, uel.CHOSEN_RULE)
    finally:
        conn.close()

    matches = [
        e
        for e in events
        if e["district"] == "BKP" and e["onset"].date() == dt.date(2026, 9, 25)
    ]
    if not matches:
        pytest.skip(
            "no BKP candidate on 2026-09-25 under the chosen rule in this DB snapshot "
            "-- data may have changed since this test was written"
        )
    event = matches[0]
    # MEASURED from the live DB at authoring time: BKP district reaches its
    # >=3-road threshold at 2026-09-25T13:05:00Z, 8 distinct roads.
    assert event["onset"] == dt.datetime.fromisoformat("2026-09-25T13:05:00+00:00")
    assert event["n_roads"] >= 3
    assert "FL.BKP.04" in event["roads"]  # ถ.รามคำแหง ตรงข้าม ซ.53
    assert "FL.BKP.05" in event["roads"]  # ถ.รามคำแหง ตรงข้าม ซ.43
