"""Tests for tools/backtest/compute_prop_flood_06_sammakorn.py -- PROP-FLOOD-06 (v6.1
registered statement, v5 Python engine, tools/backtest/prop_flood_06_v5.py, imported
verbatim) computed for the "sammakorn" unit (FOUNDER_TASKS_2026-09-27.md row 19).

Covers: the compute() call resolves to a valid tier/mode/coverage triple against this
run's real observations.sqlite rows, write_tier_run() writes a well-formed, sourced
readout record to raw/tier_runs/ (gitignored -- never asserts a fixed path across runs),
the tier-word/colour table, and the monotonicity rule this proposal itself proves in Coq
("more real data never lowers the tier" -- equivalently, removing a present input must
never RAISE the tier the raw rule reports, the direction actually exercised here since a
real-data run can only ever have inputs taken away, never invented).
"""
import datetime
import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools" / "backtest"))

import compute_prop_flood_06_sammakorn as pf06  # noqa: E402
from prop_flood_06_v5 import full_tier_v5, TIER_ORDER  # noqa: E402
import store  # noqa: E402

DB_PATH = REPO_ROOT / "data" / "observations.sqlite"


def _skip_if_no_db():
    if not DB_PATH.exists():
        pytest.skip("data/observations.sqlite not present in this checkout")
        return
    # Genuinely read-only (sqlite3 URI mode=ro), deliberately NOT store.connect() --
    # store.connect() always runs schema-ensure DDL (ALTER/DROP INDEX/CREATE INDEX)
    # even against an already-up-to-date schema, which can rewrite the real tracked
    # file's bytes as a side effect. This check only ever SELECTs.
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='observations'"
        ).fetchone()
        if table_exists is None:
            pytest.skip(
                "data/observations.sqlite has no 'observations' table (e.g. an empty "
                "db vivified by another test/module import) -- this check only applies "
                "against a populated local DB"
            )
        n = conn.execute("SELECT COUNT(*) AS n FROM observations").fetchone()["n"]
        if n == 0:
            pytest.skip(
                "data/observations.sqlite's 'observations' table is empty -- this "
                "check only applies against a populated local DB"
            )
    finally:
        conn.close()


# --------------------------------------------------------------------------- compute()

def test_compute_returns_valid_tier_and_mode():
    _skip_if_no_db()
    record = pf06.compute()
    assert record["tier"] in set(TIER_ORDER) | {"LR"}
    assert record["mode"] in {"FULL", "PARTIAL", "LR"}


def test_compute_coverage_counts_are_consistent():
    _skip_if_no_db()
    record = pf06.compute()
    assert record["coverage_present_n"] + record["coverage_absent_n"] == record["coverage_total_n"]
    assert record["coverage_total_n"] == 10
    assert set(record["coverage_present_components"]) & set(record["coverage_absent_components"]) == set()


def test_compute_never_fabricates_r_h_or_a_u():
    """R_H (คลองบ้านม้า 2 gravity outlet) and A_U (catchment area) are genuinely OPEN in
    raw/backtest/units.yaml's own SAMMAKORN entry -- compute() must pass them through as
    None, never invent a number, and the unit must therefore resolve PARTIAL (or LR), not
    FULL (FULL would require F_H(U), which needs A_U)."""
    _skip_if_no_db()
    record = pf06.compute()
    assert record["unit_fields"]["A_U_km2"]["value"] is None
    assert record["unit_fields"]["A_U_km2"]["tag"] == "OPEN"
    assert record["unit_fields"]["R_H_m3s"]["value"] is None
    assert record["unit_fields"]["R_H_m3s"]["tag"] == "OPEN"
    assert record["mode"] in {"PARTIAL", "LR"}


def test_compute_pond_capacity_is_the_sourced_bma_plan_figure():
    _skip_if_no_db()
    record = pf06.compute()
    field = record["unit_fields"]["pond_storage_capacity_m3"]
    assert field["value"] == 227200
    assert field["tag"] == "VERIFIED"
    assert "ภาคผนวก ก หน้า 74" in field["source"]


def test_compute_d_h_is_sourced_pump_design_total():
    _skip_if_no_db()
    record = pf06.compute()
    field = record["unit_fields"]["D_H_m3s"]
    assert field["value"] == pytest.approx(7.75)
    assert field["tag"] == "VERIFIED"
    assert "ง-25" in field["source"]


# --------------------------------------------------------------------------- write_tier_run()

def test_write_tier_run_creates_a_sourced_json_file(tmp_path):
    _skip_if_no_db()
    record = pf06.compute()
    out_path = pf06.write_tier_run(record, out_dir=tmp_path)
    assert out_path.exists()
    assert out_path.parent == tmp_path
    on_disk = json.loads(out_path.read_text(encoding="utf-8"))
    assert on_disk["unit_id"] == "sammakorn"
    assert "generated_at_utc" in on_disk
    assert "inputs" in on_disk and "input_provenance" in on_disk
    assert on_disk["tier"] == record["tier"]


def test_write_tier_run_is_append_only_never_overwrites(tmp_path):
    """Two runs with distinct generated_at_utc timestamps must land in two distinct
    files -- never the same path (raw/tier_runs/ is append-only per AGENTS.md ss2)."""
    _skip_if_no_db()
    import datetime
    r1 = pf06.compute(now_utc=datetime.datetime(2026, 9, 27, 12, 0, 0, tzinfo=datetime.timezone.utc))
    r2 = pf06.compute(now_utc=datetime.datetime(2026, 9, 27, 13, 0, 0, tzinfo=datetime.timezone.utc))
    p1 = pf06.write_tier_run(r1, out_dir=tmp_path)
    p2 = pf06.write_tier_run(r2, out_dir=tmp_path)
    assert p1 != p2
    assert p1.exists() and p2.exists()


# --------------------------------------------------------------------------- tier word/colour

def test_tier_word_and_color_cover_every_ladder_rung():
    for t in list(TIER_ORDER) + ["LR"]:
        word = pf06.tier_word_th(t)
        color = pf06.tier_color(t)
        assert word and word != t  # a real Thai word, not a fallback echo of the code
        assert color.startswith("#")


# --------------------------------------------------------------------------- monotonicity

def _base_inputs():
    return {
        "rain_24h_mm": 26.5, "canal_level_m": 0.82, "canal_warning_m": 0.35,
        "canal_critical_m": 0.44, "canal_bank_m": None, "Q_o_now": None, "Q_cap_o": None,
        "pumps_running_count": 0, "Q_in_up": None, "upstream_delta_pct": None,
        "tau_up_h": None, "upstream_gauge_id": None, "basin_rain_24h_mm": None,
        "basin_rain_72h_mm": None, "forecast_rain_72h_mm": None,
    }


def _tier_rank(tier: str) -> int:
    if tier == "LR":
        return -1
    return TIER_ORDER.index(tier)


def test_removing_a_present_input_never_raises_the_tier():
    """PROP-FLOOD-06's own v4/v5 monotonicity theorem (full_tier_v4_promoter_monotone /
    full_tier_v5's widened form): widening coverage (present stays present, or absent
    becomes present) never LOWERS the tier, for the non-LR case. This test exercises the
    contrapositive direction that an honest real-data run can actually produce -- taking
    a real input AWAY (canal_level_vs_lines, which currently fires CANAL_AT_CRITICAL_LINE
    and feeds PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD) must never RAISE the reported tier."""
    unit_tuple_full = pf06.build_unit_tuple(_base_inputs())
    readout_full = full_tier_v5(unit_tuple_full, H=24.0)

    reduced_inputs = dict(_base_inputs())
    reduced_inputs["canal_level_m"] = None
    reduced_inputs["canal_warning_m"] = None
    reduced_inputs["canal_critical_m"] = None
    unit_tuple_reduced = pf06.build_unit_tuple(reduced_inputs)
    readout_reduced = full_tier_v5(unit_tuple_reduced, H=24.0)

    if readout_full.tier != "LR" and readout_reduced.tier != "LR":
        assert _tier_rank(readout_reduced.tier) <= _tier_rank(readout_full.tier), (
            f"removing canal_level_vs_lines RAISED the tier: "
            f"{readout_reduced.tier} > {readout_full.tier}"
        )


def test_removing_every_input_falls_to_lr_never_fabricates_a_tier():
    empty_inputs = {k: None for k in _base_inputs()}
    unit_tuple = pf06.build_unit_tuple(empty_inputs)
    readout = full_tier_v5(unit_tuple, H=24.0)
    assert readout.tier == "LR"
    assert readout.mode == "LR"


# --------------------------------------------------------------------------- task 2: engine-version honesty

def test_compute_records_engine_version_honesty():
    """The registered proposal is v6.1 but this code calls the v5 engine -- compute()'s
    own record must say so explicitly, never claim the code implements v6.1."""
    _skip_if_no_db()
    record = pf06.compute()
    assert "full_tier_v5" in record["engine_version"]
    assert "v6.1" in record["engine_version"]
    assert "not yet fully implemented" in record["engine_version"]
    assert "delta:" in record["engine_version"]
    # resident-grade Thai one-liner, per FOUNDER_TASKS_2026-09-27.md #38
    assert record["engine_note_th"] == "คำนวณด้วยสมการรุ่น 5 ของเรา; รุ่น 6.1 ที่ยื่นไว้ยังไม่ครบในโค้ด"


# --------------------------------------------------------------------------- task 3: forecast_rain_72h, per model

def _seed_forecast_daily(conn, point_id, model, values_by_offset_day, base_date):
    """Writes synthetic per-model DAILY forecast rows into a test-local observations.sqlite
    (same shape collect_openmeteo_forecast16d/collect_metno_locationforecast would write:
    source_id='openmeteo_forecast16d', station_code='<point_id>:<model>',
    variable='precipitation_forecast_daily_mm')."""
    for offset_day, mm in values_by_offset_day.items():
        d = base_date + datetime.timedelta(days=offset_day)
        store.insert_observation(
            conn, source_id="openmeteo_forecast16d", station_code=f"{point_id}:{model}",
            variable="precipitation_forecast_daily_mm",
            observed_at_utc=d.strftime("%Y-%m-%dT00:00:00+00:00"),
            fetched_at_utc="2026-09-27T00:00:00+00:00", trust_tier="RELAYED", value=mm,
        )


def test_forecast_rain_72h_per_model_worst_case_and_all_recorded(tmp_path):
    """3 synthetic models -> forecast_rain_72h_per_model() must sum each model's own
    earliest 3 available days, and gather_real_inputs() must feed the ENGINE the WORST
    (highest-total) model's value while recording every model's own total in provenance
    -- founder rule: never average across models, worst case shown first."""
    db_path = tmp_path / "test_observations.sqlite"
    conn = store.connect(db_path)
    base = datetime.date(2026, 9, 28)
    # model A: 10+10+10 = 30mm over 3 days (best case)
    _seed_forecast_daily(conn, "sammakorn", "ecmwf_ifs025", {0: 10.0, 1: 10.0, 2: 10.0}, base)
    # model B: 20+25+15 = 60mm over 3 days (middle)
    _seed_forecast_daily(conn, "sammakorn", "gfs_seamless", {0: 20.0, 1: 25.0, 2: 15.0}, base)
    # model C: 40+35+30 = 105mm over 3 days (WORST -- highest total)
    _seed_forecast_daily(conn, "sammakorn", "icon_seamless", {0: 40.0, 1: 35.0, 2: 30.0}, base)

    per_model = pf06.forecast_rain_72h_per_model(conn, point_id="sammakorn")
    assert per_model == {"ecmwf_ifs025": 30.0, "gfs_seamless": 60.0, "icon_seamless": 105.0}

    gathered = pf06.gather_real_inputs(conn)
    assert gathered["inputs"]["forecast_rain_72h_mm"] == 105.0  # worst model's own total
    fc_prov = gathered["provenance"]["forecast_rain_72h_mm"]
    assert fc_prov["worst_model"] == "icon_seamless"
    assert fc_prov["worst_value_mm"] == 105.0
    assert fc_prov["n_models"] == 3
    # every named model's own value recorded, never averaged away
    assert fc_prov["per_model_mm"] == {"ecmwf_ifs025": 30.0, "gfs_seamless": 60.0,
                                        "icon_seamless": 105.0}
    conn.close()


def test_forecast_rain_72h_per_model_skips_ensemble_member_source():
    """openmeteo_ensemble_daily_precip (per-member rows) is a DIFFERENT source_id from
    openmeteo_forecast16d/metno_locationforecast -- forecast_rain_72h_per_model() must
    never pick it up (skip ensemble members entirely, per founder rule)."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        conn = store.connect(Path(td) / "obs.sqlite")
        base = datetime.date(2026, 9, 28)
        _seed_forecast_daily(conn, "sammakorn", "ecmwf_ifs025", {0: 10.0}, base)
        # an ensemble-member row under a DIFFERENT source_id -- must be ignored
        store.insert_observation(
            conn, source_id="openmeteo_ensemble_daily_precip",
            station_code="sammakorn:gfs_ensemble_member17",
            variable="precipitation_forecast_daily_mm",
            observed_at_utc=base.strftime("%Y-%m-%dT00:00:00+00:00"),
            fetched_at_utc="2026-09-27T00:00:00+00:00", trust_tier="RELAYED", value=9999.0,
        )
        per_model = pf06.forecast_rain_72h_per_model(conn, point_id="sammakorn")
        assert "gfs_ensemble_member17" not in per_model
        assert per_model == {"ecmwf_ifs025": 10.0}
        conn.close()


def test_forecast_rain_72h_returns_empty_when_no_rows():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        conn = store.connect(Path(td) / "obs.sqlite")
        assert pf06.forecast_rain_72h_per_model(conn, point_id="sammakorn") == {}
        conn.close()


def test_gather_real_inputs_forecast_72h_open_when_no_rows():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        conn = store.connect(Path(td) / "obs.sqlite")
        gathered = pf06.gather_real_inputs(conn)
        assert gathered["inputs"]["forecast_rain_72h_mm"] is None
        assert gathered["provenance"]["forecast_rain_72h_mm"]["tag"] == "OPEN"
        conn.close()


def test_adding_forecast_72h_promoter_never_lowers_the_tier_monotonic():
    """Founder monotonicity rule (this proposal's own theorem, full_tier_v5): adding a
    real forecast_rain_72h reading on top of the same other inputs must never LOWER the
    reported tier vs. having it absent."""
    inputs_without = _base_inputs()
    inputs_without["forecast_rain_72h_mm"] = None
    readout_without = full_tier_v5(pf06.build_unit_tuple(inputs_without), H=24.0)

    inputs_with = dict(_base_inputs())
    inputs_with["forecast_rain_72h_mm"] = 999.0  # well above any FORECAST_RAIN_72H_EXCEEDS threshold
    readout_with = full_tier_v5(pf06.build_unit_tuple(inputs_with), H=24.0)

    if readout_without.tier != "LR" and readout_with.tier != "LR":
        assert _tier_rank(readout_with.tier) >= _tier_rank(readout_without.tier), (
            f"adding forecast_rain_72h LOWERED the tier: "
            f"{readout_with.tier} < {readout_without.tier}"
        )


# --------------------------------------------------------------------------- task 3: coverage "inferred" marking

def test_compute_marks_forecast_component_inferred_not_measured(monkeypatch):
    """When forecast_rain_72h resolves (present to the engine), compute()'s OWN reporting
    layer must flag it 'inferred' (a forecast, not a direct field reading) -- separate from
    the engine's own present/absent truth, which is UNCHANGED (task 3)."""
    _skip_if_no_db()
    real_gather = pf06.gather_real_inputs

    def _fake_gather(conn=None, now_utc=None):
        out = real_gather(conn, now_utc=now_utc)
        out["inputs"]["forecast_rain_72h_mm"] = 999.0
        out["provenance"]["forecast_rain_72h_mm"] = {
            "per_model_mm": {"fake_model": 999.0}, "worst_model": "fake_model",
            "worst_value_mm": 999.0, "n_models": 1, "tag": "RELAYED",
        }
        return out

    monkeypatch.setattr(pf06, "gather_real_inputs", _fake_gather)
    record = pf06.compute()
    assert "forecast_rain_72h" in record["coverage_present_components"]
    assert "forecast_rain_72h" in record["coverage_inferred_components"]
    assert record["coverage_inferred_n"] >= 1
    assert record["coverage_measured_n"] == record["coverage_present_n"] - record["coverage_inferred_n"]
