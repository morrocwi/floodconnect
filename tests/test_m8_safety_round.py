"""Regression tests for the M8 "safe fix" round (founder 2026-10-05: "แก้อีก 1 รอบ
แบบปลอดภัยก่อน"), covering the the prior independent review's findings and the S1-S5
safety rules. Every data row is REAL, copied verbatim from this worktree's own
captured live data (raw/live/bma_watermap/2026-10-05T061313Z.json, raw/live/
thaiwater_waterlevel/2026-10-05T061320Z.json, or data/observations.sqlite) --
never simulated, per this project's rule.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_m8_safety_round.py -q
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import kb  # noqa: E402
import store  # noqa: E402
import tools.kg.rings as rings_mod  # noqa: E402

NOW = datetime.datetime.fromisoformat("2026-10-05T06:20:00+00:00")

# Real row, WL.BBN.01, agency coordinate (13.67055,100.42713) -- an earlier pass's
# own regression case: the bma_watermap/thaiwater_bma twins tie on distance at this
# exact coordinate, and must resolve to the READABLE twin.
REAL_BBN01_ROW = dict(
    source_id="bma_watermap", station_code="WL.BBN.01",
    station_name="จุดวัดคลองบางบอน", lat=13.67055, lon=100.42713,
    variable="canal_water_level_m", value=-0.3, unit="m",
    observed_at_utc="2026-10-05T06:10:00+00:00", fetched_at_utc="2026-10-05T06:13:13+00:00",
    warning=0.2, critical=0.3, bank=None, status="ปกติ", trust_tier="official_telemetry",
)

# Real row, WL.SMK.01, 2026-10-05 06:10 UTC capture (same fixture as
# tests/test_kb_answer_sandwich.py's REAL_SMK01_STABLE_ROW).
REAL_SMK01_STABLE_ROW = dict(
    source_id="bma_watermap", station_code="WL.SMK.01",
    station_name="จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2",
    lat=13.76676, lon=100.67784, variable="canal_water_level_m", value=-0.48, unit="m",
    observed_at_utc="2026-10-05T06:10:00+00:00", fetched_at_utc="2026-10-05T06:13:13+00:00",
    warning=0.35, critical=0.44, bank=None, status="ปกติ", trust_tier="official_telemetry",
)

# Real row, WL.SSB.08, 2026-10-05 06:10 UTC capture -- SAME timestamp as SMK01 above
# (both from the same bma_watermap POST): wl_in 0.46 against critical 0.45 ->
# agency's own "วิกฤต" word. This is Sammakorn's declared OUTLET (east_chain.yaml).
REAL_SSB08_CRITICAL_ROW = dict(
    source_id="bma_watermap", station_code="WL.SSB.08",
    station_name="จุดวัดคลองแสนแสบ ช่วงซอยเสรีไทย 24", lat=13.7805, lon=100.67387,
    variable="canal_water_level_m", value=0.46, unit="m",
    observed_at_utc="2026-10-05T06:10:00+00:00", fetched_at_utc="2026-10-05T06:13:13+00:00",
    warning=0.35, critical=0.45, bank=None, status="วิกฤต", trust_tier="official_telemetry",
)

# Real row, BKK020 (คลองลาดพร้าว ปากคลอง2สายใต้, 13.93183,100.63952), UPSTREAM_CHAIN
# of BKK021 per tools/kg/rings.py's own reach walk -- OVERBANK word, real capture.
REAL_BKK020_OVERBANK_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="BKK020",
    station_name="คลองลาดพร้าว ปากคลอง2สายใต้", lat=13.93183, lon=100.63952,
    variable="waterlevel_msl", value=10.0, unit="m",
    observed_at_utc="2026-10-05T06:00:00+00:00", fetched_at_utc="2026-10-05T06:13:20+00:00",
    warning=None, critical=None, bank=9.5, status="OVERBANK", trust_tier="official_telemetry",
)

# Real row, BKK021 (คลองลาดพร้าว วัดบางบัว, 13.85402,100.58746) -- Z0 itself calm, so
# the colour must come from the confirmed-upstream middle, never plain MIDDLE_NOT_RISING.
REAL_BKK021_CALM_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="BKK021",
    station_name="คลองลาดพร้าว วัดบางบัว", lat=13.85402, lon=100.58746,
    variable="waterlevel_msl", value=1.0, unit="m",
    observed_at_utc="2026-10-05T06:00:00+00:00", fetched_at_utc="2026-10-05T06:13:20+00:00",
    warning=None, critical=None, bank=5.0, status="NORMAL", trust_tier="official_telemetry",
)

# Real row, CPY017 (Sena, Ayutthaya, 14.31976,100.37952 -- nearest gauge to
# 14.33,100.39), real capture 2026-10-05 13:00 Bangkok local: situation_level 4
# (thaiwater_situation_4 -> YELLOW, never RED; real waterlevel_msl 3.00 vs its own
# real min_bank 3.59, below bank).
REAL_CPY017_SITUATION4_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="CPY017",
    station_name="เสนา", lat=14.31976, lon=100.37952,
    variable="waterlevel_msl", value=3.00, unit="m",
    observed_at_utc="2026-10-05T06:00:00+00:00", fetched_at_utc="2026-10-05T06:13:20+00:00",
    warning=None, critical=None, bank=3.59, status="thaiwater_situation_4",
    trust_tier="official_telemetry",
)


@pytest.fixture
def sandwich_db(tmp_path, monkeypatch):
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    return conn


def test_bbn01_z0_resolves_to_readable_twin_and_gets_a_real_reading(sandwich_db):
    """Regression (MEASURED 2026-10-05): a distance tie between the
    readable gauge:bma_watermap: node and its unreadable gauge:thaiwater_bma: twin
    must always resolve to the readable one -- this was regressing 215/311 BMA
    stations to NO_Z0_READING."""
    store.insert_observation(sandwich_db, **REAL_BBN01_ROW)
    r = kb._answer_sandwich(13.67055, 100.42713, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:bma_watermap:WL.BBN.01"
    assert r["z0"]["fresh"] is True
    assert r["colour"] != "UNKNOWN"
    assert r.get("reason") != "NO_Z0_READING -- station has no observation row yet"


def test_sammakorn_outlet_critical_gives_at_least_yellow_never_green(sandwich_db):
    """S2b: a fresh RED OUTLET (WL.SSB.08 วิกฤต, Sammakorn's declared drainage
    outlet) is a drainage CONSTRAINT -- it must raise the result to at least YELLOW
    with reason OUTLET_CRITICAL, and must never be GREEN, even though Z0 (WL.SMK.01)
    itself reads ปกติ/STABLE and no upstream station was ever read (so AGREE/
    TOP_NO_UPSTREAM alone would otherwise leave Z0's own GREEN standing)."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_SSB08_CRITICAL_ROW)
    r = kb._answer_sandwich(13.766, 100.678, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:bma_watermap:WL.SMK.01"
    assert r["colour"] != "GREEN"
    assert r["colour"] in ("YELLOW", "ORANGE", "RED")
    assert "OUTLET_CRITICAL" in r["why"]
    fact_ids = {f[0] for f in r["facts"]}
    assert "gauge:bma_watermap:WL.SSB.08" in fact_ids


def test_bkk021_no_declared_edge_to_bkk020_is_unknown_not_a_guess(sandwich_db):
    """Founder ruling 2026-10-06 (KG-only, no guessing) supersedes this test's
    earlier claim: BKK021's own UPSTREAM_CHAIN relation to BKK020 came only from
    the reach-walk's geometric ON_REACH snap (`basis="DERIVED-snap"`), never a
    declared east_chain.yaml edge -- under `KG_ONLY_MODE` it no longer reaches
    this ring at all, so a real OVERBANK reading one hop away can no longer be
    read as "water coming" here. The Z1 layer is honestly UNKNOWN (a KG gap,
    see `kb.py`'s own policy-gap logging), and Z0's own calm reading stands --
    never a guessed escalation past what Z0 itself says."""
    store.insert_observation(sandwich_db, **REAL_BKK021_CALM_ROW)
    store.insert_observation(sandwich_db, **REAL_BKK020_OVERBANK_ROW)
    r = kb._answer_sandwich(13.85402, 100.58746, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:BKK021"
    assert r["layers"]["Z1"] == "UNKNOWN"
    fact_ids = {f[0] for f in r["facts"]}
    assert "gauge:thaiwater_waterlevel:BKK020" not in fact_ids


def test_ayutthaya_point_is_yellow_not_red_when_only_z0_is_situation4(sandwich_db):
    """S1: RED only when Z0 (or its SAME_STATION twin) is itself at/over
    critical/bank -- CPY017's real situation_level 4 (thaiwater_situation_4) maps
    to YELLOW, never RED, with no upstream read raising it further."""
    store.insert_observation(sandwich_db, **REAL_CPY017_SITUATION4_ROW)
    r = kb._answer_sandwich(14.33, 100.39, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:CPY017"
    assert r["colour"] != "RED"
    assert r["colour"] in ("YELLOW", "ORANGE")


def test_sammakorn_z1_contains_only_the_declared_east_chain_edges():
    """Founder ruling 2026-10-06 (KG-only, no guessing) supersedes S5's full-KG
    NAME_JOIN trace this test used to check: Z1 must contain the declared
    OUTLET (WL.SSB.08) and the other `site/inputs/canals/east_chain.yaml`
    edges (e.g. the Ban Ma branch), but the canal-code-family NAME_JOIN walk
    that used to add further WL.SSB.* stations is now removed entirely --
    every Z1/Z2 row carries `basis="declared"`, never "NAME_JOIN"."""
    assert rings_mod.KG_ONLY_MODE is True
    r = rings_mod.rings(13.766, 100.678)
    z1_ids = {row["id"] for row in r["z1"]}
    assert "gauge:bma_watermap:WL.SSB.08" in z1_ids  # declared OUTLET
    assert any("BMA.02" in i for i in z1_ids), "Ban Ma station missing from Z1"
    for row in r["z1"] + r["z2"]:
        assert row["basis"] == "declared", row


def test_top_no_upstream_point_gives_low_confidence_not_a_calm_claim(sandwich_db):
    """S2: a point whose Z3/middle has no fresh UPSTREAM_PATH/UPSTREAM_CHAIN/
    UPSTREAM_REACH row at all must never claim "top calm" -- Z0's own colour stands,
    tagged TOP_NO_UPSTREAM/TOP_UNREAD, LOW confidence, official_tier False."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    r = kb._answer_sandwich(13.766, 100.678, refresh=False, now_utc=NOW)
    if r["colour"] == "GREEN":  # no OUTLET/other RED row inserted in this test
        assert any(w in ("TOP_NO_UPSTREAM", "TOP_UNREAD") for w in r["why"])
        assert r["confidence"] == "LOW"
        assert r["official_tier"] is False


def test_per_layer_colours_present_and_unknown_never_shown_as_green(sandwich_db):
    """S1b: the answer carries a colour for each ring (Z0/Z1/Z2/Z3), each read
    from that ring's own agency readings; a ring with no fresh reading at all is
    UNKNOWN, never GREEN. Sammakorn with only Z0 (ปกติ) and the real critical
    OUTLET (Z1) inserted: Z0 green, Z1 red (from the real OUTLET reading), Z2/Z3
    unread -> unknown, never green."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_SSB08_CRITICAL_ROW)
    r = kb._answer_sandwich(13.766, 100.678, refresh=False, now_utc=NOW)
    layers = r["layers"]
    assert layers["Z0"] == "GREEN"
    assert layers["Z1"] == "RED"  # the real OUTLET reading, always read (S2b)
    assert layers["Z2"] == "UNKNOWN"
    assert layers["Z3"] == "UNKNOWN"

    # compact mode encodes the same 4 colours as one 4-char string, fixed order.
    compact = kb._compact_sandwich(r)
    assert compact["layers"] == "GRUU"


def test_basis_is_set_by_relation_never_by_pv():
    """Regression : every reach-walk relation (SAME_REACH/
    DOWNSTREAM_CHAIN/UPSTREAM_CHAIN/UPSTREAM_REACH/UPSTREAM_PATH) carries basis
    DERIVED-snap unconditionally; OUTLET carries basis "declared" with its own
    `contradicts`/`ref`; SAME_SUBBASIN carries whichever IN_SUBBASIN-family join tag
    actually supplied it (`sb_basis`) -- never a station's own unrelated `pv` field."""
    r = rings_mod.rings(13.766, 100.678)
    for row in r["z1"] + r["z2"]:
        if row["relation"] == "OUTLET":
            assert row["basis"] == "declared"
            assert row.get("contradicts") is True
        elif row["relation"] in ("SAME_REACH", "DOWNSTREAM_CHAIN", "UPSTREAM_CHAIN",
                                  "UPSTREAM_REACH"):
            assert row["basis"] == "DERIVED-snap"
    for row in r["z3"]["stations"]:
        if row["relation"] == "UPSTREAM_PATH":
            assert row["basis"] == "DERIVED-snap"
        elif row["relation"] == "SAME_SUBBASIN":
            assert row["basis"] == r["z3"]["sb_basis"]
