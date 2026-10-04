"""the fix regression tests (2026-10-04): a `dds_daily_pdf` canal_level_0700_m
row must never decide `current_local_state` for a centre it cannot be shown to be near.

Background (a later re-check, full detail in the review history): the
first attempt at this fix gated a row on (a) the QUERY CENTRE being within 40 km of central
Bangkok, and (b) the row's station name containing one of a few canal-name substrings.
Both checks ignore where the GATE ITSELF actually is. Four real repro points --
Thonburi, Don Mueang, a point near Lat Krabang, and Sammakorn itself -- all got
`current_local_state=RED` from `canal_outer` ("ภายนอกคันปองกันน้ำทวม") rows measuring the
OUTSIDE-the-dike water level at a gate 8-30 km away, a different hydraulic regime than
what a resident at the query centre experiences.

This fix (readout.py's `_DDS_GATE_COORDS` + the dds_canal loop) requires THREE things
before a row may decide anything: it must be a `canal_inner` row, its own gate must have
a sourced coordinate (from `sources/canal_normal_levels.yaml`, never guessed from the
canal's name), and that coordinate must lie within the caller's own `radius_km` of the
centre.

Every row below is copied verbatim (station_name incl. its real PDF-font Private-Use-Area
codepoints, value, critical, status, section) from this repo's own
`data/observations.sqlite`, source_id `dds_daily_pdf`, latest real fetch
2026-10-03T16:21:42Z -- "real data only in tests, never simulated"
(`feedback-floodconnect-infer-from-strong-anchors.md`). Only `observed_at_utc`/
`fetched_at_utc` are shifted to a fixed recent instant so freshness is deterministic
regardless of wall-clock drift.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_dds_canal_geo_gate_2026-10-04.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import readout  # noqa: E402
import store  # noqa: E402

AS_OF = "2026-10-04"  # reference instant: 2026-10-04T00:00:00+00:00 (pinned, deterministic)
OBSERVED_AT = "2026-10-03T00:00:00+00:00"  # < 24h before AS_OF -- fresh under every gate
FETCHED_AT = "2026-10-03T16:21:42.467613+00:00"  # verbatim, real fetch batch

# Verbatim real rows (data/observations.sqlite, source_id=dds_daily_pdf,
# variable=canal_level_0700_m, fetched_at_utc=2026-10-03T16:21:42.467613+00:00, ids
# 10245-10254). (station_name, value, critical, status, section).
REAL_DDS_CANAL_ROWS = [
    ("คลองทวีวัฒนาตัดคลองภาษีเจริญ", 0.48, 0.7, "ระดับน้ำปกติ", "canal_inner"),
    ("คลองลาดพราว 56", 0.17, 0.4, "ระดับน้ำปกติ", "canal_inner"),
    ("คลองเปรมประชากร (ตอนคลองบานใหม)", 0.81, 1.2, "ระดับน้ำปกติ", "canal_inner"),
    ("คลองแสนแสบ-คลองตัน (แสนแสบเกา)", -0.43, 0.2, "ระดับน้ำปกติ", "canal_inner"),
    ("คลองแสนแสบ-เขตบางกะป", 0.21, 0.45, "ระดับน้ำปกติ", "canal_inner"),
    ("ปตร.คลองทวีวัฒนา (ดานใน)", 0.65, 1.0, "ระดับน้ำปกติ", "canal_inner"),
    ("ปตร.คลองประเวศฯ-ลาดกระบัง", 0.82, 0.35, "ระดับน้ำวิกฤติ", "canal_outer"),
    ("ปตร.คลองมหาสวัสดิ์-ฉิมพลี (ดานแมน้ำ)", 0.86, 2.8, "ระดับน้ำปกติ", "canal_inner"),
    ("ปตร.คลองสองสายใต", 1.91, 1.8, "ระดับน้ำวิกฤติ", "canal_outer"),
    ("ปตร.คลองแสนแสบ-มีนบุรี.80", 1.28, 0.7, "ระดับน้ำวิกฤติ", "canal_outer"),
]

# Real repro centres from an earlier re-check.
THONBURI = (13.72, 100.48)
DON_MUEANG = (13.91, 100.60)
PT3 = (13.75, 100.75)  # near Lat Krabang -- 2.9 km from WL.PWT.04 (ปตร.คลองประเวศฯ-ลาดกระบัง)
CHIANG_MAI = (18.79, 98.98)
SAMMAKORN = (13.758235, 100.676084)  # kb._ANSWER_AREAS["sammakorn"]


@pytest.fixture()
def conn(tmp_path):
    c = store.connect(tmp_path / "dds_geo_gate.sqlite")
    for name, value, critical, status, section in REAL_DDS_CANAL_ROWS:
        store.insert_observation(
            c, source_id="dds_daily_pdf", station_name=name,
            variable="canal_level_0700_m", value=value, unit="m",
            observed_at_utc=OBSERVED_AT, fetched_at_utc=FETCHED_AT,
            trust_tier="official_report", critical=critical, status=status,
            provenance={"section": section, "header_date_recognized": True})
    return c


def _dds_rows(full: dict) -> list[dict]:
    return [r for r in full["factors"]["4_การระบาย"]["measured"]
            if r.get("source") == "dds_daily_pdf"]


@pytest.mark.parametrize("centre", [THONBURI, DON_MUEANG, PT3, CHIANG_MAI])
def test_far_or_outer_only_centres_never_decided_by_dds_canal(conn, centre):
    """None of these centres may be decided by ANY dds_daily_pdf row: the 3 real
    critical rows are all `canal_outer` (excluded unconditionally), and no `canal_inner`
    row's sourced coordinate lies within a realistic radius of any of these points."""
    full = readout.build_readout(conn, centre[0], centre[1], 5.0, as_of_date=AS_OF)
    rows = _dds_rows(full)
    assert rows, "fixture rows must still be visible (never silently dropped)"
    used = [r for r in rows if r["used_for_decision"]]
    assert used == [], (
        f"centre {centre} was wrongly decided by: "
        f"{[(r['station'], r['status']) for r in used]}")
    # the outer rows in particular must say so plainly, not just "not local"
    outer = [r for r in rows if r["canal_outer"]]
    assert len(outer) == 3
    assert all(not r["used_for_decision"] for r in outer)
    assert all("canal_outer" in r["scope_note"] or "ฝั่งนอก" in r["scope_note"]
                for r in outer)


def test_sammakorn_not_decided_red_by_a_far_outer_gate(conn):
    """The exact Sammakorn repro: `ปตร.คลองประเวศฯ-ลาดกระบัง` (canal_outer, 8.8 km away)
    and `ปตร.คลองแสนแสบ-มีนบุรี` (canal_outer, 10.4 km away) must not decide RED for
    Sammakorn just because they are both city-wide-bulletin "critical" rows within a
    generous Bangkok-wide radius -- they are excluded for being `canal_outer`,
    independent of distance."""
    full = readout.build_readout(conn, SAMMAKORN[0], SAMMAKORN[1], 5.0, as_of_date=AS_OF)
    rows = _dds_rows(full)
    red_rows = [r for r in rows if r["status"] == "ระดับน้ำวิกฤติ"]
    assert len(red_rows) == 3  # all 3 real critical rows are visible
    assert all(not r["used_for_decision"] for r in red_rows), (
        "a canal_outer critical row decided Sammakorn's current_local_state -- "
        "the exact bug this fix removes")


def test_sammakorn_inner_gate_with_sourced_coord_decides_within_radius(conn):
    """The one `canal_inner` row this repo has a sourced coordinate for
    (คลองแสนแสบ-เขตบางกะป / WL.SSB.07, 3.14 km from Sammakorn) DOES decide once the
    caller's radius actually covers it, and carries its coordinate source in
    `scope_note` -- proving the gate is radius-sensitive, not merely outer-exclusive."""
    full_5km = readout.build_readout(conn, SAMMAKORN[0], SAMMAKORN[1], 5.0, as_of_date=AS_OF)
    rows_5km = {r["station"]: r for r in _dds_rows(full_5km)}
    bangkapi = rows_5km["คลองแสนแสบ-เขตบางกะป"]
    assert bangkapi["used_for_decision"] is True
    assert bangkapi["canal_outer"] is False
    assert "canal_normal_levels.yaml" in bangkapi["scope_note"]

    # Narrowing the radius below the real 3.14 km distance must exclude it again --
    # proving this is a genuine distance check, not a fixed allowlist.
    full_3km = readout.build_readout(conn, SAMMAKORN[0], SAMMAKORN[1], 3.0, as_of_date=AS_OF)
    rows_3km = {r["station"]: r for r in _dds_rows(full_3km)}
    assert rows_3km["คลองแสนแสบ-เขตบางกะป"]["used_for_decision"] is False


def test_inner_row_with_no_sourced_coordinate_stays_open_never_decides(conn):
    """`คลองแสนแสบ-คลองตัน (แสนแสบเก่า)` is `canal_inner` and genuinely near Sammakorn by
    canal name, but this repo has NO sourced coordinate for that specific gate -- it must
    stay visible (never dropped) and OPEN, never guessed into deciding anything, even at
    a generous radius."""
    full = readout.build_readout(conn, SAMMAKORN[0], SAMMAKORN[1], 50.0, as_of_date=AS_OF)
    rows = {r["station"]: r for r in _dds_rows(full)}
    khlong_tan = rows["คลองแสนแสบ-คลองตัน (แสนแสบเกา)"]
    assert khlong_tan["canal_outer"] is False
    assert khlong_tan["used_for_decision"] is False
    assert "[OPEN]" in khlong_tan["scope_note"]


def test_headline_never_claims_all_stale_when_rows_are_fresh_but_geo_excluded(conn):
    """fix (2026-10-04): MEASURED later -- 10 fresh
    (4.8h old) geo-excluded DDS rows were presented under a header claiming the
    radius's values are "ทั้งหมดที่มี STALE" (all STALE), which is false -- every row in
    this fixture is fresh (OBSERVED_AT is <24h before AS_OF); none is really stale.
    A centre with zero decided rows, all of them geo-excluded (never truly STALE),
    must say so honestly -- never claim "ALL values are STALE"."""
    full = readout.build_readout(conn, THONBURI[0], THONBURI[1], 5.0, as_of_date=AS_OF)
    headline = full["overall_picture"]["notes"][0]
    assert "ทั้งหมดที่มี STALE" not in headline, headline
    assert "นอกรัศมี" in headline or "ไม่มีพิกัด" in headline, headline


def test_overall_picture_status_counts_match_used_for_decision(conn):
    """readout.py's own `overall_picture` prose-summary status_counts (a SEPARATE loop
    from kb.py's structured one) must count the exact same rows `used_for_decision`
    marks true -- the the fix also closed a second, narrower bug where this loop
    counted every fresh row regardless of `used_for_decision`."""
    full = readout.build_readout(conn, SAMMAKORN[0], SAMMAKORN[1], 5.0, as_of_date=AS_OF)
    notes = full["overall_picture"]["notes"]
    headline = notes[0]
    # None of the 3 outer "ระดับน้ำวิกฤติ" rows may appear as if deciding the headline.
    assert "ระดับน้ำวิกฤติ" not in headline, headline
    assert "ระดับน้ำปกติ" in headline, headline  # the in-radius inner row does decide
