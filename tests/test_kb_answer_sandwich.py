"""Tests for `kb._answer_sandwich` / the M8 P3 answer integration -- rings -> Z0
reading -> `floodconnect_model.sandwich_decision`, middle fetched only on conflict,
folded into `next_action.dual_state` via `build_answer`.

Every row below is REAL data, copied verbatim from a live `collect.py --source
bma_watermap` / `--source thaiwater_waterlevel` run recorded on 2026-10-05 (see this
worktree's own `data/observations.sqlite`) -- never simulated, per this project's
rule. Timestamps are kept EXACTLY as captured; `now_utc` is pinned close to them
(same convention `tests/test_kb_answer.py`'s own day-pinned fixtures use) so
freshness is deterministic regardless of wall-clock time.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_kb_answer_sandwich.py -q
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import floodconnect_model as fm  # noqa: E402
import kb  # noqa: E402
import store  # noqa: E402

NOW = datetime.datetime.fromisoformat("2026-10-05T06:20:00+00:00")

# Real row, WL.SMK.01, 2026-10-05 06:10 UTC capture (bma_watermap POST) -- STABLE,
# ปกติ, well below its own critical (-0.48 vs 0.44).
REAL_SMK01_STABLE_ROW = dict(
    source_id="bma_watermap", station_code="WL.SMK.01",
    station_name="จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2",
    lat=13.76676, lon=100.67784, variable="canal_water_level_m", value=-0.48, unit="m",
    observed_at_utc="2026-10-05T06:10:00+00:00", fetched_at_utc="2026-10-05T06:13:13+00:00",
    warning=0.35, critical=0.44, bank=None, status="ปกติ", trust_tier="official_telemetry",
)

# Real row, C.67 (Ayutthaya, near 14.33,100.39), 2026-10-05 05:00 UTC capture
# (thaiwater_waterlevel GET) -- the agency's own ล้นตลิ่ง (overbank) word, same
# sub_basin:1002 Sammakorn's own Z0 inherits via its OUTLET_TO join (see
# tests/test_rings.py).
REAL_C67_OVERBANK_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="C.67",
    station_name="สะพานหัวเวียง", lat=14.36851, lon=100.414391,
    variable="waterlevel_msl", value=5.48, unit="m",
    observed_at_utc="2026-10-05T05:00:00+00:00", fetched_at_utc="2026-10-05T06:13:20+00:00",
    warning=None, critical=None, bank=2.75, status="OVERBANK", trust_tier="official_telemetry",
    provenance={"diff_wl_bank_text": "ล้นตลิ่ง (ม.)", "waterlevel_msl_previous": 5.48,
                "sub_basin_id": 240},
)

# Real row, Kgt.1 (Prachin Buri, near 14.0,101.37) -- the agency's own OVERBANK word
# at Z0 itself: local critical always wins, no middle needed.
REAL_KGT1_OVERBANK_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="Kgt.1",
    station_name="กระบะตะไกร", lat=14.00318, lon=101.36955,
    variable="waterlevel_msl", value=4.74, unit="m",
    observed_at_utc="2026-10-05T05:00:00+00:00", fetched_at_utc="2026-10-05T06:13:20+00:00",
    warning=None, critical=None, bank=3.0, status="OVERBANK", trust_tier="official_telemetry",
)


@pytest.fixture
def sandwich_db(tmp_path, monkeypatch):
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    return conn


def test_sammakorn_stable_plus_saen_saep_overbank_resolves_green_but_still_facts(sandwich_db):
    """fix: C.67 is only in Sammakorn's INHERITED sub-basin
    (SAME_SUBBASIN, via the OUTLET_JOIN), not on an UPSTREAM_PATH relation to it --
    the founder's own rule is that Z3's top_alert is the KG-connected UPSTREAM
    stations, never every same-sub-basin station regardless of direction. So the
    top is read as calm (AGREE) and Sammakorn's own GREEN/STABLE bottom stands --
    but C.67's real over-bank reading is still surfaced in `facts`, never lost,
    because `facts` carries every RED Z3 station whatever the final colour is."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_C67_OVERBANK_ROW)
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:bma_watermap:WL.SMK.01"
    assert r["z0"]["fresh"] is True
    assert "READ_BOTTOM" in r["steps"] and "READ_TOP" in r["steps"]
    assert r["colour"] == "GREEN"
    assert r["label_th"] == "ปกติ"
    fact_ids = {f[0] for f in r["facts"]}
    assert "gauge:thaiwater_waterlevel:C.67" in fact_ids


def test_local_overbank_word_always_wins_never_needs_middle(sandwich_db):
    store.insert_observation(sandwich_db, **REAL_KGT1_OVERBANK_ROW)
    r = kb._answer_sandwich(14.0, 101.37, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:Kgt.1"
    assert r["colour"] == "RED"
    assert r["label_th"] == "วิกฤต"
    assert r["steps"] == ["READ_BOTTOM", "AT_OR_OVER_LOCAL"]
    assert r["mid"]["read"] is False  # never fetched -- RED is final at Z0


# Real row, BKK009 (thaiwater), 2026-10-05 12:20 UTC capture -- h EQUALS the
# agency's own published bank (0.62 == 0.62) while the agency's own status word
# (thaiwater_situation_4) alone would still classify as YELLOW/WATCH.
REAL_BKK009_AT_BANK_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="BKK009",
    station_name="คลองลำปลาทิว ลาดกระบัง", lat=13.7407, lon=100.79468,
    variable="waterlevel_msl", value=0.62, unit="m",
    observed_at_utc="2026-10-05T06:10:00+00:00", fetched_at_utc="2026-10-05T06:13:20+00:00",
    warning=None, critical=None, bank=0.62, status="thaiwater_situation_4",
    trust_tier="official_telemetry",
)


def test_z0_layer_matches_the_decisions_own_bank_check_at_bank_equal_point(sandwich_db):
    """Regression test, real station BKK009: h is
    exactly at the agency's own published bank (0.62 == 0.62), which `bank_check`
    (the decision's own READ_BOTTOM rule) reads as AT_OR_OVER -> RED -- but the
    agency's bare status word alone (`thaiwater_situation_4`) classifies as
    YELLOW. Before the fix, `layers["Z0"]`/`strip` used that bare classification
    and disagreed with the decision itself (RED here, Y in the strip). Both must
    now agree, since `layers["Z0"]` is derived from the SAME `colour_ladder` rule
    as the decision."""
    store.insert_observation(sandwich_db, **REAL_BKK009_AT_BANK_ROW)
    r = kb._answer_sandwich(13.7407, 100.79468, refresh=False, now_utc=NOW)
    assert r["z0"]["id"] == "gauge:thaiwater_waterlevel:BKK009"
    assert r["colour"] == "RED"
    assert r["layers"]["Z0"] == "RED"


def test_no_z0_reading_in_db_is_unknown_not_a_guess(sandwich_db):
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    assert r["colour"] == "UNKNOWN"
    assert r["reason"].startswith("NO_Z0_READING")


def test_no_db_at_all_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "does_not_exist.sqlite")
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    assert r["colour"] == "UNKNOWN"
    assert r["reason"] == "NO_DB"


def test_point_with_no_gauge_within_radius_is_unknown(sandwich_db):
    r = kb._answer_sandwich(7.0, 101.5, refresh=False, now_utc=NOW)
    assert r["colour"] == "UNKNOWN"
    assert "NO_Z0" in r["reason"]


def test_stale_z0_reading_never_folds_into_dual_state(sandwich_db):
    stale_row = dict(REAL_SMK01_STABLE_ROW,
                      observed_at_utc="2026-01-01T00:00:00+00:00")
    store.insert_observation(sandwich_db, **stale_row)
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    assert r["z0"]["fresh"] is False


def test_build_answer_folds_sandwich_colour_into_dual_state_only_when_z0_fresh(
        tmp_path, monkeypatch):
    """`build_answer` has no `now_utc` passthrough (by design -- see its own
    docstring), so this test pins the wall clock itself (same fixed `NOW` every
    other test in this file pins via the `now_utc=NOW` argument) rather than
    relying on real wall-clock time staying within the freshness window of the
    fixed, real `REAL_KGT1_OVERBANK_ROW` timestamp -- without this, the test
    silently goes stale and fails on any run day after the row's recorded date."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    store.insert_observation(conn, **REAL_KGT1_OVERBANK_ROW)

    class _FixedDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW if tz is not None else NOW.replace(tzinfo=None)

    monkeypatch.setattr(kb.datetime, "datetime", _FixedDatetime)
    out = kb.build_answer("14.0,101.37", refresh=False)
    assert out["jev_decision"]["colour"] == "RED"
    assert out["next_action"]["dual_state"]["current_local_state"] == "RED"
    assert out["next_action"]["dual_state"]["colour"] == "RED"
    assert out["next_action"]["dual_state"]["label_th"] == "วิกฤต"


def test_dual_state_equals_fold_of_card_colour(tmp_path, monkeypatch):
    """Inverted from this test's own pre-fix name
    (`test_dual_state_never_downgraded_by_a_lower_sandwich_colour`): the old
    10 km-radius legacy classifier is NEVER used for `dual_state` once a
    `sandwich_answer` is given (S1) -- the sandwich decision is the ONLY source
    of `current_local_state`, in BOTH directions, never only a raise. The
    pre-fix "never downgraded" rule is exactly the bug (MEASURED live:
    201/1118 live points showed `current_local_state=RED` sitting next to a
    lower/disagreeing sandwich `colour` in the SAME `dual_state` dict, e.g.
    WL.AJP.01: RED from a basin station 12.02 km away, "ปกติ" in the same
    object) -- a real station merely within the legacy radius (here, the real
    Kgt.1 OVERBANK row) must NEVER make `current_local_state` disagree with
    `colour`/`label_th` any more, regardless of which one is "worse"."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    store.insert_observation(conn, **REAL_KGT1_OVERBANK_ROW)  # legacy RED at this point

    def _fake_yellow_sandwich(*_a, **_kw):
        return {"z0": {"id": "gauge:thaiwater_waterlevel:Kgt.1", "fresh": True},
                "colour": "YELLOW", "label_th": "เฝ้าระวัง", "confidence": "MEDIUM",
                "level": "YELLOW", "steps": [], "why": [], "gate": "LICENSED_WITHIN_ENVELOPE",
                "facts": [], "official_tier": True, "eq": {}}

    monkeypatch.setattr(kb, "_answer_sandwich", _fake_yellow_sandwich)
    out = kb.build_answer("14.0,101.37", refresh=False)
    ds = out["next_action"]["dual_state"]
    # `current_local_state` is now the sandwich's own fold -- NEVER the legacy
    # RED this point's real nearby station alone would have decided -- and it
    # never disagrees with `colour`/`label_th` in the same dict (S1).
    assert ds["current_local_state"] == "YELLOW"
    assert ds["colour"] == "YELLOW"
    assert ds["label_th"] == "เฝ้าระวัง"
    assert ds["confidence"] == "MEDIUM"


def test_dual_state_is_unknown_when_sandwich_z0_is_stale_or_missing(tmp_path, monkeypatch):
    """The other direction: when the sandwich's own Z0
    reading is stale or there is no Z0 reading at all, `current_local_state` is
    UNKNOWN -- never the legacy classifier's own colour, even a real one, since
    that is exactly the mixed-signal `dual_state` S1 forbids."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    store.insert_observation(conn, **REAL_KGT1_OVERBANK_ROW)  # legacy RED at this point

    def _fake_stale_sandwich(*_a, **_kw):
        return {"z0": {"id": "gauge:thaiwater_waterlevel:Kgt.1", "fresh": False},
                "colour": "UNKNOWN", "label_th": "ไม่ทราบ", "confidence": "NONE",
                "level": "UNKNOWN", "steps": [], "why": [], "gate": "REFUSED",
                "facts": [], "official_tier": False, "eq": {}}

    monkeypatch.setattr(kb, "_answer_sandwich", _fake_stale_sandwich)
    out = kb.build_answer("14.0,101.37", refresh=False)
    assert out["next_action"]["dual_state"]["current_local_state"] == "UNKNOWN"
    assert "confidence" not in out["next_action"]["dual_state"]


def test_dual_state_upgraded_by_a_higher_sandwich_colour(tmp_path, monkeypatch):
    """The mirror case: a legacy GREEN/UNKNOWN `current_local_state` IS overwritten
    when the sandwich's own colour ranks higher (the higher-risk of the two wins)."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    monkeypatch.setattr(kb, "DB_PATH", db_path)

    def _fake_red_sandwich(*_a, **_kw):
        return {"z0": {"id": "gauge:bma_watermap:FAKE", "fresh": True},
                "colour": "RED", "label_th": "วิกฤต", "confidence": "HIGH",
                "level": "RED", "steps": [], "why": [], "gate": "LICENSED_WITHIN_ENVELOPE",
                "facts": [], "official_tier": True, "eq": {}}

    monkeypatch.setattr(kb, "_answer_sandwich", _fake_red_sandwich)
    out = kb.build_answer("14.0,101.37", refresh=False)  # no observation -> legacy UNKNOWN
    assert out["next_action"]["dual_state"]["current_local_state"] == "RED"
    assert out["next_action"]["dual_state"]["colour"] == "RED"


def test_build_answer_never_crashes_when_rings_or_sandwich_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "observations.sqlite")

    def _boom(*_a, **_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(kb, "_answer_sandwich", _boom)
    out = kb.build_answer("14.0,101.37", refresh=False)
    assert out["jev_decision"]["colour"] == "UNKNOWN"
    # `why` is verbose-only in the compact jev_decision shape (M8 P-B's own compacting
    # rule keeps only colour/label/confidence/gate/layers/facts/choice.chosen/
    # prepare_steps/home_shelter -- never the raw reason trail) -- check the full why
    # on the verbose payload instead of the default compact one.
    out_verbose = kb.build_answer("14.0,101.37", refresh=False, verbose=True)
    assert any("boom" in w for w in out_verbose["jev_decision"]["why"])


# ---------------------------------------------------------------------------
# Founder ruling 2026-10-06, "เจ้าพระยาคือทางออก" -- หมู่บ้านสัมมากร outlet fix.
# Real rows, copied verbatim from this worktree's own `data/observations.sqlite`
# (live `collect.py --source thaiwater_waterlevel` capture, 2026-10-05 14:20Z):
# both OVERBANK, both in Sammakorn's inherited `sub_basin:1002` (SAME_SUBBASIN,
# via OUTLET_JOIN) -- but on DIFFERENT real rivers by the agency's own
# `river_name` (verified against `sources/hii_station_geocode.yaml`, the
# declared geocode source):
#   CPY014 (สะพานนวลฉวี, ปากเกร็ด, นนทบุรี) -- river_name "แม่น้ำเจ้าพระยา" (the
#     Chao Phraya MAIN STEM) -- a true outlet of Sammakorn's own drainage
#     (บึง -> คลองแสนแสบ -> ... -> แม่น้ำเจ้าพระยา), per the founder's ruling.
#   BKC002 (ปตร.วัดบางกระเจ้านอก, พระประแดง, สมุทรปราการ) -- river_name
#     "คลองบางกะเจ้า" (a DIFFERENT canal) -- NOT the main stem, NOT Saen Saep;
#     joined to Sammakorn only via the huge shared sub-basin -- never a real
#     outlet, must never be relabelled OUTLET/OUTLET_MAIN_STEM.
# ---------------------------------------------------------------------------
REAL_CPY014_OVERBANK_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="CPY014",
    station_name="สะพานนวลฉวี", lat=13.94749, lon=100.53507,
    variable="waterlevel_msl", value=2.57, unit="m",
    observed_at_utc="2026-10-05T14:20:00+00:00", fetched_at_utc="2026-10-05T14:31:29+00:00",
    warning=None, critical=None, bank=2.5, status="OVERBANK", trust_tier="official_telemetry",
    provenance={"province_th": "นนทบุรี", "amphoe_th": "ปากเกร็ด", "river_name": "แม่น้ำเจ้าพระยา",
                "sub_basin_id": 240, "basin_id": 10, "basin_name_th": "ลุ่มน้ำเจ้าพระยา",
                "diff_wl_bank_text": "ล้นตลิ่ง (ม.)", "waterlevel_msl_previous": 2.57},
)

REAL_BKC002_OVERBANK_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="BKC002",
    station_name="ปตร.วัดบางกระเจ้านอก", lat=13.689612, lon=100.554886,
    variable="waterlevel_msl", value=1.42, unit="m",
    observed_at_utc="2026-10-05T14:20:00+00:00", fetched_at_utc="2026-10-05T14:31:29+00:00",
    warning=None, critical=None, bank=1.26, status="OVERBANK", trust_tier="official_telemetry",
    provenance={"province_th": "สมุทรปราการ", "amphoe_th": "พระประแดง", "river_name": "คลองบางกะเจ้า",
                "sub_basin_id": 240, "basin_id": 10, "basin_name_th": "ลุ่มน้ำเจ้าพระยา",
                "diff_wl_bank_text": "ล้นตลิ่ง (ม.)", "waterlevel_msl_previous": 1.43},
)

NOW_OUTLET_CASE = datetime.datetime.fromisoformat("2026-10-05T14:35:00+00:00")


def test_sammakorn_cpy014_is_upstream_not_the_outlet_never_outlet_main_stem(sandwich_db):
    """fix (founder ruling 2026-10-06): CPY014 (13.947, ปากเกร็ด) sits NORTH of
    (upstream of) the ~lat 13.75 Saen Saep -> Chao Phraya junction this repo's
    own `kb.py` places Sammakorn's drainage at -- calling it "downstream" was
    false, measured against this repo's own declared lats. It is now DROPPED
    from `downstream_main_stem_codes`, so OVERBANK there never raises
    Sammakorn's GREEN Z0 at all; it stays a plain SAME_SUBBASIN fact, same as
    BKC002 (a different canal sharing the same huge sub-basin)."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_CPY014_OVERBANK_ROW)
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW_OUTLET_CASE)
    assert r["colour"] == "GREEN"
    assert "OUTLET_CRITICAL" not in r["why"]
    fact_relations = {f[0]: f[2] for f in r["facts"]}
    assert fact_relations.get("gauge:thaiwater_waterlevel:CPY014") != "OUTLET_MAIN_STEM"


def test_sammakorn_same_subbasin_only_bkc002_overbank_is_no_false_outlet(sandwich_db):
    """Founder ruling 2026-10-06: BKC002 shares Sammakorn's huge sub-basin only
    (a different canal, คลองบางกะเจ้า, by its own agency river_name) -- it must
    NEVER be relabelled OUTLET/OUTLET_MAIN_STEM, must never trigger
    OUTLET_CRITICAL, and must never drive the Z3 layer colour to RED on its
    own -- Sammakorn's own GREEN Z0 stays GREEN."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_BKC002_OVERBANK_ROW)
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW_OUTLET_CASE)
    assert r["colour"] == "GREEN"
    assert "OUTLET_CRITICAL" not in r["why"]
    fact_relations = {f[0]: f[2] for f in r["facts"]}
    assert fact_relations["gauge:thaiwater_waterlevel:BKC002"] == "SAME_SUBBASIN"
    assert r["layers"]["Z3"] != "RED"


def test_sammakorn_cpy014_and_bkc002_both_same_subbasin_only_stay_green(sandwich_db):
    """fix (founder ruling 2026-10-06): with BOTH real OVERBANK rows present
    (the live 2026-10-05 14:20Z state) and CPY014 now correctly excluded from
    `downstream_main_stem_codes` (it is upstream of Sammakorn's own junction,
    not its outlet), neither row is colour-eligible (both plain SAME_SUBBASIN)
    -- the consistency floor has nothing RED to raise, and Sammakorn's own
    GREEN Z0 stays GREEN. This supersedes the test that used to assert YELLOW
    here via a false OUTLET_MAIN_STEM relabel of CPY014."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_CPY014_OVERBANK_ROW)
    store.insert_observation(sandwich_db, **REAL_BKC002_OVERBANK_ROW)
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW_OUTLET_CASE)
    assert not (r["colour"] == "GREEN" and "RED" in r["layers"].values())
    assert r["colour"] == "GREEN"
    assert "OUTLET_CRITICAL" not in r["why"]


# ---------------------------------------------------------------------------
# Founder subtractive-fix ruling (2026-10-06): OUTLET_MAIN_STEM only applies
# inside a DECLARED per-area list (today: หมู่บ้านสัมมากร), never nationwide.
# Three real stations outside that declared area, each 20km+ from Sammakorn's
# own centre -- the relabel must never fire for any of them, whether they are
# themselves the Z0 (self-river/other-outlet-river exclusion) or an upstream
# main-stem neighbour that used to be wrongly promoted sub-basin-wide.
# ---------------------------------------------------------------------------
REAL_CPY014_AS_Z0_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="CPY014",
    station_name="สะพานนวลฉวี", lat=13.94749, lon=100.53507,
    variable="waterlevel_msl", value=2.0, unit="m",
    observed_at_utc="2026-10-05T14:20:00+00:00", fetched_at_utc="2026-10-05T14:31:29+00:00",
    warning=None, critical=None, bank=2.5, status="ปกติ", trust_tier="official_telemetry",
    provenance={"river_name": "แม่น้ำเจ้าพระยา", "sub_basin_id": 240, "basin_id": 10,
                "waterlevel_msl_previous": 2.0},
)

REAL_C35_AS_Z0_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="C.35",
    station_name="บ้านป้อม", lat=14.3691, lon=100.528732,
    variable="waterlevel_msl", value=1.0, unit="m",
    observed_at_utc="2026-10-05T14:20:00+00:00", fetched_at_utc="2026-10-05T14:31:29+00:00",
    warning=None, critical=None, bank=3.0, status="ปกติ", trust_tier="official_telemetry",
    provenance={"river_name": "แม่น้ำเจ้าพระยา", "sub_basin_id": 240, "basin_id": 10,
                "waterlevel_msl_previous": 1.0},
)

REAL_THA001_AS_Z0_ROW = dict(
    source_id="thaiwater_waterlevel", station_code="THA001",
    station_name="สะพานคง-ศุข ศรีสวัสดิ์", lat=15.225, lon=100.07824,
    variable="waterlevel_msl", value=1.0, unit="m",
    observed_at_utc="2026-10-05T14:20:00+00:00", fetched_at_utc="2026-10-05T14:31:29+00:00",
    warning=None, critical=None, bank=4.0, status="ปกติ", trust_tier="official_telemetry",
    provenance={"river_name": "แม่น้ำท่าจีน", "sub_basin_id": 240, "basin_id": 10,
                "waterlevel_msl_previous": 1.0},
)


REAL_SS01_Z1_RED_ROW = dict(
    source_id="bma_watermap", station_code="WL.SSB.01",
    station_name="จุดวัดคลองแสนแสบ", lat=13.75276, lon=100.51693,
    variable="canal_water_level_m", value=1.6, unit="m",
    observed_at_utc="2026-10-06T06:00:00+00:00", fetched_at_utc="2026-10-06T06:05:00+00:00",
    warning=None, critical=1.5, bank=1.5, status="วิกฤต", trust_tier="official_telemetry",
    provenance={"ground_level": None},
)

NOW_SS01_CASE = datetime.datetime.fromisoformat("2026-10-06T06:10:00+00:00")


def test_no_z0_reading_still_computes_layers_and_facts(sandwich_db):
    """SS01's own id (`gauge:thaiwater_bma:SS01`) has no M8 reader and no readable
    `gauge:bma_watermap:` twin at all -- Z0 stays NO_Z0_READING/UNKNOWN. Its
    Z1 ring used to surface WL.SSB.01 via the reach-walk's SAME_REACH join
    (`basis="DERIVED-snap"`); under the founder's 2026-10-06 KG-only ruling
    ("ปิดการเดา ... ให้อยู่แค่ใน kg graph เท่านั้น") that reach-snap join is
    removed from the ring entirely, not merely demoted -- there is no declared
    east_chain.yaml edge here, so Z1 is honestly UNKNOWN (a KG gap), never a
    guessed RED."""
    store.insert_observation(sandwich_db, **REAL_SS01_Z1_RED_ROW)
    r = kb._answer_sandwich(13.75282, 100.51719, refresh=False, now_utc=NOW_SS01_CASE)
    assert r["colour"] == "UNKNOWN"
    assert r.get("reason", "").startswith("NO_Z0_READING")
    assert r["layers"]["Z0"] == "UNKNOWN"
    assert r["layers"]["Z1"] == "UNKNOWN"


@pytest.mark.parametrize("row,lat,lon", [
    (REAL_CPY014_AS_Z0_ROW, 13.94749, 100.53507),
    (REAL_C35_AS_Z0_ROW, 14.3691, 100.528732),
    (REAL_THA001_AS_Z0_ROW, 15.225, 100.07824),
])
def test_outlet_main_stem_never_fires_outside_declared_sammakorn_area(sandwich_db, row, lat, lon):
    """CPY014 (main stem itself), C.35
    (upstream, Ayutthaya) and THA001 (its own outlet river, ท่าจีน) must never
    get an OUTLET_MAIN_STEM row -- that relabel only fires inside the declared
    Sammakorn area (`_OUTLET_MAIN_STEM_DECLARED_AREAS`), which none of these
    points are within."""
    store.insert_observation(sandwich_db, **row)
    r = kb._answer_sandwich(lat, lon, refresh=False, now_utc=NOW_OUTLET_CASE)
    fact_relations = [f[2] for f in r["facts"]]
    assert "OUTLET_MAIN_STEM" not in fact_relations
    assert all(layer != "RED" or r["colour"] != "GREEN" for layer in r["layers"].values())


@pytest.mark.parametrize("code,lat,lon", [
    ("WL.KJA.02", 13.74953, 100.63387),   # คลองกะจะ, 4.66 km from Sammakorn's centre
    ("WL.YPN.01", 13.77868, 100.64013),   # คลองยายเผื่อน, 4.5 km from Sammakorn's centre
])
def test_kja02_and_ypn01_are_never_in_the_declared_sammakorn_area(code, lat, lon):
    """fix (founder ruling 2026-10-06): WL.KJA.02 and WL.YPN.01 are real BMA
    stations 4.5-4.7 km from Sammakorn's own centre point -- close enough that
    the OLD radius check wrongly declared THEM to be inside Sammakorn's own
    area (so querying AT their own coordinates could mis-relabel some
    unrelated main-stem station as THEIR outlet too). Neither is Sammakorn's
    own station id, nor located on the declared east_chain.yaml branch, so
    the station-id-based declared area must exclude both."""
    kg_id = f"gauge:bma_watermap:{code}"
    assert kg_id not in kb._station_ids_in_sammakorn_declared_area()
    assert kb._declared_outlet_area_for(kg_id) is None


# Real rows, copied verbatim from a live `collect.py --source bma_watermap` run,
# 2026-10-06 05:45Z. WL.LPT.05 (Z0) is a genuinely different, calm reading;
# WL.LPT.01 joins it as a real (non-heuristic) SAME_CANAL_DIRECTION_UNKNOWN/
# NAME_JOIN neighbour on the same declared canal name (คลองลำปลาทิว) and is
# fresh RED -- a real, colour-eligible critical, not a code-family guess.
REAL_WL_LPT05_GREEN_ROW = dict(
    source_id="bma_watermap", station_code="WL.LPT.05",
    station_name="คลองลำปลาทิว ตอนถนนบุรีภิรมย์*", lat=13.85586, lon=100.8654,
    variable="canal_water_level_m", value=1.33, unit="m",
    observed_at_utc="2026-10-06T05:45:00+00:00", fetched_at_utc="2026-10-06T05:51:48+00:00",
    warning=None, critical=50.0, bank=None, status="ปกติ", trust_tier="official_telemetry",
    provenance={"sensor_status": "ok"},
)
REAL_WL_LPT01_RED_ROW = dict(
    source_id="bma_watermap", station_code="WL.LPT.01",
    station_name="จุดวัดคลองลำปลาทิว ตอนถนนสังฆสันติสุข", lat=13.85366, lon=100.86679,
    variable="canal_water_level_m", value=1.24, unit="m",
    observed_at_utc="2026-10-06T05:45:00+00:00", fetched_at_utc="2026-10-06T05:51:48+00:00",
    warning=None, critical=1.1, bank=None, status="วิกฤต", trust_tier="official_telemetry",
    provenance={"sensor_status": "ok"},
)
NOW_LPT_CASE = datetime.datetime.fromisoformat("2026-10-06T05:50:00+00:00")


def test_real_canal_name_join_is_removed_entirely_under_kg_only_mode(sandwich_db):
    """Founder ruling 2026-10-06 (KG-only, no guessing) supersedes the earlier
    "genuine canal-name-join" distinction this test used to check -- a
    verbatim same-canal-name join (`basis="NAME_JOIN"`) is STILL a guess this
    repo makes about which two specific stations share water, never a
    declared KG edge, so WL.LPT.01 no longer reaches WL.LPT.05's ring at all.
    Z1 is honestly UNKNOWN (a KG gap), and the GREEN decision stays GREEN --
    never silently promoted, but also never raised by a row that is no
    longer there."""
    store.insert_observation(sandwich_db, **REAL_WL_LPT05_GREEN_ROW)
    store.insert_observation(sandwich_db, **REAL_WL_LPT01_RED_ROW)
    r = kb._answer_sandwich(13.85586, 100.8654, refresh=False, now_utc=NOW_LPT_CASE)
    assert r["layers"]["Z1"] == "UNKNOWN"
    assert r["colour"] == "GREEN"
    assert "LAYER_CRITICAL_UNDER_GREEN" not in r["why"]


# ---- fix (founder ruling 2026-10-06): scope tagging --------------------------------

def test_sammakorn_bma_watermap_z0_is_validated_mvp_scope(sandwich_db):
    """Sammakorn's own pond gauge (bma_watermap) is the one area actually swept
    end to end -- its answer must carry scope VALIDATED_MVP."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 13.758235, 100.676084)
    assert jev["scope"] == "VALIDATED_MVP"


def test_a_point_far_outside_bangkok_is_experimental_scope(sandwich_db):
    """A thaiwater_waterlevel point outside Bangkok metro (Ayutthaya) has not
    been swept the same way -- its answer must carry scope EXPERIMENTAL, never
    a silent claim of the same validated coverage."""
    store.insert_observation(sandwich_db, **REAL_C67_OVERBANK_ROW)
    sandwich_answer = kb._answer_sandwich(14.33, 100.39, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 14.33, 100.39)
    assert jev["scope"] == "EXPERIMENTAL"


@pytest.mark.parametrize("lat,lon,label", [
    (13.689612, 100.554886, "BKC002, สมุทรปราการ"),
    (13.97396, 100.31901, "BKK018, นนทบุรี"),
    (13.88207, 100.29086, "BKK019, นครปฐม"),
    (13.80777, 100.27417, "VLGE20, นครปฐม"),
])
def test_points_inside_the_old_metro_bbox_but_outside_bangkok_province_are_experimental(
        lat, lon, label):
    """fix: these 4 real stations (this repo's own
    `sources/stations/thaiwater_waterlevel.json`) all sit inside
    `collect.BANGKOK_METRO_BBOX` (the loose "greater metro" rectangle the old
    scope check used) but their own nearest declared KG asset resolves them to
    a province OTHER than Bangkok (MEASURED, `tools.kg.locate.locate`) -- the
    scope check must say so (EXPERIMENTAL), never VALIDATED_MVP off the
    rectangle alone. No `sandwich_db`/sqlite row needed -- `_answer_scope`
    itself is the unit under test, same precedent as this file's own
    `test_answer_scope_bare_defaults` below."""
    assert kb._is_bangkok_metro(lat, lon) is True, (
        label, "must still be inside the old loose metro bbox for this test "
        "to demonstrate the real fix")
    assert kb._answer_scope(None, lat, lon) == "EXPERIMENTAL", label


def test_a_bma_watermap_station_outside_sammakorn_is_no_longer_validated_by_z0_id_alone():
    """Mutation-protecting (scope overclaim, item c): `_answer_scope` used to
    treat ANY `gauge:bma_watermap:*` z0 id as VALIDATED_MVP on its own, which
    wrongly covered every BMA canal gauge nationwide, not only the
    Sammakorn/Ram53 ones this repo actually swept. WL.KJK.02 (a real BMA
    canal gauge, Phra Khanong district) is neither in Bangkok province via its
    own coordinates nor one of the declared Sammakorn-area ids -- its z0 id
    alone must now resolve EXPERIMENTAL, never VALIDATED_MVP off the
    `bma_watermap:` prefix alone."""
    assert "gauge:bma_watermap:WL.KJK.02" not in kb._station_ids_in_sammakorn_declared_area()
    assert kb._answer_scope("gauge:bma_watermap:WL.KJK.02", None, None) == "EXPERIMENTAL"


@pytest.mark.xfail(
    reason=(
        "Known KG-data-coverage gap, not a code bug: BKK007 (คลองอ้อมนนท์ บางใหญ่, "
        "a real thaiwater_waterlevel station physically in Bang Yai, Nonthaburi) "
        "has too few Nonthaburi IN_PROVINCE-declared KG member points near it "
        "(tools/kg/build_index.py's own 'mp' list), so tools.kg.locate.locate's "
        "nearest-member-distance ranking still puts Bangkok (near_km=7.9) ahead of "
        "Nonthaburi (near_km=13.6) for this point. Fixing it needs more declared "
        "IN_PROVINCE edges for Nonthaburi stations near this border, a KG-data "
        "curation task, not a province-resolution code change -- see CHANGELOG's "
        "Known issues note for this version."
    ),
    strict=True,
)
def test_bkk007_in_nonthaburi_is_experimental_not_validated():
    """BKK007 -- real station, `sources/stations/thaiwater_waterlevel.json`,
    name_th 'คลองอ้อมนนท์ บางใหญ่ (ถนนบางกรวย-ไทรน้อย)', lat/lon 13.87089,100.43626,
    physically in Bang Yai, Nonthaburi, not Bangkok. The scope check must say
    EXPERIMENTAL for a station outside both Bangkok province and the declared
    Sammakorn area -- currently still returns VALIDATED_MVP, a real remaining
    gap (see the xfail reason above), not silently treated as fixed."""
    lat, lon = 13.87089, 100.43626
    assert kb._answer_scope("gauge:thaiwater_waterlevel:BKK007", lat, lon) == "EXPERIMENTAL"


def test_ring_row_colour_uses_the_bank_check_ladder_not_the_bare_status_word(
        sandwich_db, monkeypatch):
    """Mutation-protecting test (review finding 4, 2026-10-06): a real
    regression (K.62/MKVKD09) let a ring member at or over its OWN agency
    critical/bank level read as its weaker agency status word's colour
    instead of RED, because the ring row's own `colour` field used to be
    `floodconnect_model.classify(status_word)` alone -- the fix (`kb.py`'s own
    `_read_ring_rows`) calls `floodconnect_model.colour_ladder(reading)`
    instead (bank_check/fresh/fault aware, `classify` is only one of several
    inputs it reads internally). This spies on `colour_ladder` itself (not on
    the final answer's colour, which several other paths could also produce)
    so reverting that one call back to a bare `classify(status_word)` fails
    this test, even though (per the review) it would not fail any other
    existing test."""
    calls = []
    real_colour_ladder = fm.colour_ladder

    def _spy(reading):
        calls.append(dict(reading))
        return real_colour_ladder(reading)
    monkeypatch.setattr(fm, "colour_ladder", _spy)

    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    store.insert_observation(sandwich_db, **REAL_C67_OVERBANK_ROW)
    r = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    assert r["colour"] == "GREEN"

    c67_calls = [c for c in calls if c.get("id") == "gauge:thaiwater_waterlevel:C.67"]
    assert c67_calls, (
        "floodconnect_model.colour_ladder was never called for the C.67 ring "
        "row -- its colour would silently fall back to classify(status_word) "
        "alone, the exact bug this test guards against")


def test_sammakorn_point_resolves_to_bangkok_province_not_just_bbox():
    """The flip side: Sammakorn's own point (no z0_id) must still resolve
    VALIDATED_MVP through the real province lookup, not only through the
    `bma_watermap` z0_id shortcut."""
    assert kb._point_province_code(13.758235, 100.676084) == "10"
    assert kb._answer_scope(None, 13.758235, 100.676084) == "VALIDATED_MVP"


def test_scope_defaults_to_experimental_when_lat_lon_not_given():
    """A caller (e.g. a direct, older `_build_jev_decision(sandwich_answer)`
    call with no point) never guesses VALIDATED_MVP -- it degrades to
    EXPERIMENTAL unless Z0 itself is a bma_watermap gauge."""
    assert kb._answer_scope(None, None, None) == "EXPERIMENTAL"
    assert kb._answer_scope("gauge:thaiwater_waterlevel:C.67", None, None) == "EXPERIMENTAL"
    assert kb._answer_scope("gauge:bma_watermap:WL.SMK.01", None, None) == "VALIDATED_MVP"


# ---- Founder ruling 2026-10-06: jev_decision.calc transparency ----

def test_calc_block_z0_reading_itself_present_on_a_real_fresh_reading(sandwich_db):
    """A real, fresh, well-formed STABLE row has a real Z0 reading -- `calc.
    colour` must never name `z0_reading` itself as missing (it may still name
    `upstream_read`/`middle_read` separately, when this ring genuinely has
    none -- those are real, different gaps, not asserted away here), and
    `result` must echo the real colour/trend, never a placeholder."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 13.758235, 100.676084)
    calc = jev["calc"]
    assert "z0_reading" not in calc["colour"]["missing"]
    assert calc["colour"]["inputs"][0]["source"] == "declared"
    assert calc["colour"]["result"] == jev["colour"]
    assert calc["trend"]["result"] == sandwich_answer["z0"]["trend"]


def test_calc_block_names_missing_z0_reading_when_station_never_read(sandwich_db):
    """A point whose Z0 has no observation row at all (S6's own stub-reading
    case) must name `z0_reading` as missing for colour, with the matching
    plain-Thai reason, never a silent empty `missing` list."""
    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 13.758235, 100.676084)
    calc = jev["calc"]
    assert "z0_reading" in calc["colour"]["missing"]
    assert kb.REASON_MISSING_Z0_READING_TH in calc["colour"]["reasons"]


def test_calc_block_names_missing_trend_when_z0_trend_is_unknown(sandwich_db):
    """thaiwater_waterlevel's own OVERBANK row (`REAL_C67_OVERBANK_ROW`) carries
    no `waterlevel_msl_previous` in its provenance -- trend reads UNKNOWN, which
    `calc.trend` must name as missing, with the matching plain-Thai reason."""
    store.insert_observation(sandwich_db, **REAL_C67_OVERBANK_ROW)
    sandwich_answer = kb._answer_sandwich(14.33, 100.39, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 14.33, 100.39)
    calc = jev["calc"]
    assert sandwich_answer["z0"]["trend"] == "UNKNOWN"
    assert "z0_trend_series" in calc["trend"]["missing"]
    assert kb.REASON_MISSING_TREND_TH in calc["trend"]["reasons"]
    # Mutation-protecting: an UNKNOWN trend (no series at all) must give the
    # "no series" ETA reason, never the "not RISING" one -- those are
    # different facts (STABLE/FALLING HAVE a resolved trend; UNKNOWN has no
    # previous reading to compare against at all).
    assert calc["eta"]["result"] == "GATED"
    assert calc["eta"]["reasons"] == [kb.REASON_ETA_NO_SERIES_TH]
    assert kb.REASON_ETA_NOT_RISING_TH not in calc["eta"]["reasons"]


def test_calc_block_eta_is_gated_when_not_rising_never_a_computed_time(sandwich_db):
    """fix (release-accuracy, 2026-10-07): the shipped ETA is PROP-FLOOD-02
    (linear, two windows) -- an already-registered, already-merged proposal, not
    PROP-FLOOD-11 (which is registered but not implemented in this release, v0.2
    target). It is NOT "always" GATED; see this file's own
    `test_calc_block_eta_computes_a_real_range_when_rising` for the real,
    computed case. It IS gated whenever the Z0 trend is not RISING (this
    test's own STABLE row), which is a real, honest refusal (nothing to
    compute on a non-rising series), never a computed time value."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 13.758235, 100.676084)
    assert jev["calc"]["eta"]["result"] == "GATED"
    assert jev["calc"]["eta"]["eq"] == "PROP-FLOOD-02"


# Real trimmed page (tests/fixtures/bma_station_detail/
# stationdetail_id14_20261006_rising_trimmed.html): a live keyless GET on
# WL.BSU.05 this session (id14), found by sampling 40 real BMA stations and
# keeping the one genuinely monotonically rising at fetch time -- never a
# constructed/fabricated series (see this file's own module docstring, "every
# row is REAL data... never simulated"). The earlier version of this test used
# a hand-written `run_points` list, which broke that rule; this fixture replaces
# it rather than refining it.
_BSU05_RISING_HTML = (Path(__file__).resolve().parent / "fixtures" / "bma_station_detail"
                       / "stationdetail_id14_20261006_rising_trimmed.html")
_BSU05_LAST_REAL = {"t_utc": "2026-10-06T16:05:00Z", "v": -1.13}
_BSU05_WARNING = 0.30
_BSU05_CRITICAL = 0.50


def _fetch_real_rising_trend(monkeypatch):
    """Shared setup: feeds `kb._bma_series_trend` the real, live-fetched
    WL.BSU.05 rising fixture and returns its result. Not itself a test."""
    import collect as collect_mod

    html_bytes = _BSU05_RISING_HTML.read_bytes()
    monkeypatch.setattr(collect_mod, "_one_get", lambda url, headers, timeout=10: (200, html_bytes))
    monkeypatch.setattr(collect_mod, "_bma_station_detail_water_ids",
                         lambda: [(14, "WL.BSU.05", "test")])
    monkeypatch.setattr(collect_mod, "_cache_raw", lambda *a, **kw: None)
    return kb._bma_series_trend("WL.BSU.05", _BSU05_LAST_REAL["v"], _BSU05_LAST_REAL["t_utc"])


def test_bma_series_trend_eta_inputs_are_real_positive_lags(monkeypatch):
    """fix (2 real bugs, measured live -- every RISING station previously
    returned `range_h: [0.0, 0.0]`): `long_hours` used to be the point's own
    DEVIATION from the 30-minute target (near 0 by construction), and the
    short-lag point used to be a fixed `run_points[-2]` array index (which can
    sit AFTER `observed_at_now`, giving a negative `short_hours`). Against this
    real, live-fetched rising series, both lags must now be real, POSITIVE
    elapsed hours (the short one near the series' own 5-min cadence, the long
    one near its 30-min target), never ~0 and never negative."""
    trend = _fetch_real_rising_trend(monkeypatch)
    assert trend is not None
    assert trend["trend"] == "RISING"
    ei = trend["_eta_inputs"]
    # short lag: the real series' own cadence here is 5 minutes.
    assert 0 < ei["short_hours"] < 0.2, ei
    assert ei["short_prev"] == -1.15
    # long lag: real elapsed time to the ~30-minute-target point, not its
    # (near-zero) deviation from that target.
    assert 0.2 < ei["long_hours"] < 0.6, ei
    assert ei["long_prev"] == -1.26


_KJK02_SERIES_AHEAD_HTML = (Path(__file__).resolve().parent / "fixtures" / "bma_station_detail"
                             / "stationdetail_id199_20261006_series_ahead_of_reading_trimmed.html")
# The external (bma_watermap feed) reading used as "now" -- real, captured a few
# minutes BEFORE the series page below was fetched, so the series' own last point
# (17:15:00Z) sits strictly after it. See that fixture's own sidecar.json.
_KJK02_NOW_READING = {"t_utc": "2026-10-06T17:10:00Z", "v": -1.22}


def test_bma_series_trend_short_lag_uses_the_point_before_now_not_a_fixed_index(
        monkeypatch):
    """Mutation-protecting regression for the `run_points[-2]` short-lag bug
    (founder ruling 2026-10-06): reverting the short-lag lookup back to a fixed
    `run_points[-2]` array index must fail this test. The real WL.KJK.02 page
    this fixture replays was fetched a few minutes AFTER the bma_watermap feed's
    own last reading for the station -- its series' real last point (17:15:00Z)
    sits strictly AFTER that reading time (17:10:00Z), so `run_points[-1]` is
    NOT `now`, and `run_points[-2]` (17:10:00Z, identical to `now`) would give
    the degenerate `short_hours == 0.0` the real bug produced (every RISING
    station's `range_h` collapsing to `[0.0, 0.0]`) -- the fixed lookup instead
    finds the real preceding point (17:05:00Z), a real positive 5-minute lag."""
    import collect as collect_mod

    html_bytes = _KJK02_SERIES_AHEAD_HTML.read_bytes()
    monkeypatch.setattr(collect_mod, "_one_get", lambda url, headers, timeout=10: (200, html_bytes))
    monkeypatch.setattr(collect_mod, "_bma_station_detail_water_ids",
                         lambda: [(199, "WL.KJK.02", "test")])
    monkeypatch.setattr(collect_mod, "_cache_raw", lambda *a, **kw: None)

    trend = kb._bma_series_trend("WL.KJK.02", _KJK02_NOW_READING["v"], _KJK02_NOW_READING["t_utc"])
    assert trend is not None
    assert trend["trend"] == "RISING"
    ei = trend["_eta_inputs"]
    # The degenerate bug value is exactly 0.0 -- a real preceding point gives a
    # real positive lag near the series' own 5-minute cadence.
    assert ei["short_hours"] is not None and ei["short_hours"] > 0.0
    assert ei["short_hours"] == pytest.approx(5 / 60.0, abs=0.01)
    assert ei["short_prev"] == -1.23  # the real 17:05:00Z reading, never the 17:10:00Z one


def test_calc_block_eta_computes_a_real_range_when_rising(monkeypatch):
    """founder ruling 2026-10-06 ("ระดับน้ำกำลังขึ้น ทำไมไม่คำนวณน้ำให้
    ว่าล้นตลิ่งในกี่ชั่วโมง"): with `PROP11_ENABLED=True` (the module switch gating
    PROP-FLOOD-02, the shipped linear two-window ETA -- not PROP-FLOOD-11),
    `floodconnect_model.rise_eta_hours_range`, fed the REAL eta_inputs this
    file's own `test_bma_series_trend_eta_inputs_are_real_positive_lags` just
    measured off a live-fetched series, must carry a real computed range, not
    GATED/AT_BANK-with-a-zero-range, whenever the Z0 trend is RISING."""
    import floodconnect_model

    trend = _fetch_real_rising_trend(monkeypatch)
    ei = trend["_eta_inputs"]
    eta = floodconnect_model.rise_eta_hours_range(
        _BSU05_LAST_REAL["v"], ei["short_prev"], ei["short_hours"],
        ei["long_prev"], ei["long_hours"],
        theta_warn=_BSU05_WARNING, theta_crit=_BSU05_CRITICAL,
        epsilon=0.01, pump_state="UNCHANGED")
    assert eta["warning"]["status"] == "OK"
    assert eta["warning"]["range_h"][0] <= eta["warning"]["range_h"][1]
    assert eta["warning"]["range_h"][0] > 0
    assert eta["critical"]["status"] == "OK"
    assert eta["critical"]["range_h"][0] > 0


def test_jev_calc_block_eta_passes_through_a_real_computed_range(sandwich_db, monkeypatch):
    """`_build_jev_decision`'s own `calc.eta` wiring: once `_answer_sandwich`
    reports a real (non-GATED) `z0.eta`, `calc.eta.result` must carry it
    through verbatim, tagged PROPOSAL -- never recomputed, never silently
    dropped back to GATED. `kb._bma_series_trend` is monkeypatched to return
    the exact REAL numbers this file's own live-fetch test measured (not a
    fabricated series) so this test stays about the WIRING, not a second copy
    of the series-parsing test above."""
    now_utc_dt = datetime.datetime.fromisoformat("2026-10-06T16:05:00+00:00")
    rising_row = dict(REAL_SMK01_STABLE_ROW)
    rising_row.update(value=_BSU05_LAST_REAL["v"], warning=_BSU05_WARNING, critical=_BSU05_CRITICAL,
                       observed_at_utc=_BSU05_LAST_REAL["t_utc"],
                       fetched_at_utc="2026-10-06T16:05:30+00:00")
    store.insert_observation(sandwich_db, **rising_row)

    real_trend = {
        "trend": "RISING", "delta": 0.13, "basis": "PROP-FLOOD-01", "eq": "PROP-FLOOD-01",
        "_eta_inputs": {"short_prev": -1.15, "short_hours": 5 / 60,
                        "long_prev": -1.26, "long_hours": 30 / 60},
    }
    monkeypatch.setattr(kb, "_bma_series_trend", lambda *a, **kw: real_trend)

    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=True,
                                           now_utc=now_utc_dt)
    assert sandwich_answer["z0"]["trend"] == "RISING"
    eta = sandwich_answer["z0"]["eta"]
    assert eta["warning"]["status"] == "OK"
    assert eta["critical"]["status"] == "OK"

    jev = kb._build_jev_decision(sandwich_answer, 13.758235, 100.676084)
    assert jev["calc"]["eta"]["result"] != "GATED"
    assert jev["calc"]["eta"]["result"]["warning"]["status"] == "OK"
    assert jev["calc"]["eta"]["tag"] == "PROPOSAL (linear, two windows)"

    # fix: the ETA must also be reachable WITHOUT --verbose -- it used to be
    # buried only inside `calc.eta` (verbose-only).
    out = {"jev_decision": kb._compact_jev_decision(dict(jev, calc=jev["calc"]))}
    assert "eta" in out["jev_decision"]
    assert out["jev_decision"]["eta"]["warning"]["range_h"]


def test_calc_block_is_dropped_from_the_compact_non_verbose_answer(sandwich_db):
    """Token budget: `calc` is a verbose-only detail, same as `trace`/`noul`/
    `choice.options` -- `_compact_jev_decision` must never carry it."""
    store.insert_observation(sandwich_db, **REAL_SMK01_STABLE_ROW)
    sandwich_answer = kb._answer_sandwich(13.758235, 100.676084, refresh=False, now_utc=NOW)
    jev = kb._build_jev_decision(sandwich_answer, 13.758235, 100.676084)
    compact = kb._compact_jev_decision(jev)
    assert "calc" not in compact
