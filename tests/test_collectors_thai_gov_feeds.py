"""Tests for the 2026-09-27 "free government + free global" collector wave (founder ask:
"ต่อให้เสร็จเฉพาะของฟรี แน่นอน ก่อน"). No test here makes a live network call -- every
collector's single `_one_get` is monkeypatched to return a real (trimmed) cached payload
from `tests/fixtures/`, same discipline as the rest of this file's siblings."""
import json
from pathlib import Path

import pytest

import collect
import parsers
import store

FIXTURES = Path(__file__).parent / "fixtures"


def _fake_one_get(body: bytes, status: int = 200):
    def _fn(url, headers, timeout=None):
        return status, body
    return _fn


def test_thaiwater_waterlevel_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "thaiwater_waterlevel_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_thaiwater_waterlevel(conn)
    assert res.ok is True
    assert res.counts["inserted"] == 3
    rows = conn.execute(
        "SELECT * FROM observations WHERE source_id='thaiwater_waterlevel'").fetchall()
    assert len(rows) == 3
    assert rows[0]["variable"] == "waterlevel_msl"
    assert rows[0]["lat"] is not None



def test_hii_dam_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "hii_dam_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_hii_dam(conn)
    assert res.ok is True
    assert res.counts["inserted"] > 0
    row = conn.execute(
        "SELECT * FROM observations WHERE source_id='hii_dam' LIMIT 1").fetchone()
    assert row["station_code"].startswith("dam:hii_dam:")


def test_hii_dam_collector_emits_storage_inflow_release_spilled_level_rows(monkeypatch, tmp_path):
    """MUST-FIX #E: dam_hourly/dam_daily rows carry dam_storage/dam_inflow/dam_released/
    dam_spilled/dam_level -- each must become its own queryable observation row, plus a
    computed release_m3s_computed row (MCM/day -> m3/s), not just storage_pct."""
    body = (FIXTURES / "hii_dam_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    collect.collect_hii_dam(conn)
    variables = {r["variable"] for r in conn.execute(
        "SELECT DISTINCT variable FROM observations WHERE source_id='hii_dam'")}
    for expected in ("storage_pct", "storage_mcm", "inflow_mcm", "release_mcm",
                      "release_m3s_computed", "spilled_mcm", "level_m"):
        assert any(v.endswith(expected) for v in variables), \
            f"missing a {expected} observation row among {sorted(variables)}"
    release_row = conn.execute(
        "SELECT * FROM observations WHERE source_id='hii_dam' "
        "AND variable LIKE '%release_mcm' AND station_code='dam:hii_dam:43' LIMIT 1"
    ).fetchone()
    computed_row = conn.execute(
        "SELECT * FROM observations WHERE source_id='hii_dam' "
        "AND variable LIKE '%release_m3s_computed' AND station_code='dam:hii_dam:43' LIMIT 1"
    ).fetchone()
    if release_row is not None and computed_row is not None:
        assert computed_row["value"] == pytest.approx(
            release_row["value"] * 1e6 / 86400.0)
        assert "MEASURED-derived" in computed_row["provenance_json"]



def test_hii_watergate_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "hii_watergate_sample.json").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_hii_watergate(conn)
    assert res.ok is True
    # fixture has 5 rows: 3 real + 1 id==0 placeholder (skipped) + 1 (0,0)-coord sentinel
    # (skipped) -- only the 3 real rows should be inserted.
    assert res.counts["inserted"] == 3
    row = conn.execute(
        "SELECT * FROM observations WHERE source_id='hii_watergate' LIMIT 1").fetchone()
    assert row["station_code"].startswith("gate:hii_watergate:")



def test_hii_watergate_collector_flags_old_rows_stale_but_still_stores_them(monkeypatch, tmp_path):
    """AGENTS.md §2 never-prune rule + MUST-FIX #E: a watergate reading older than 7
    days must still be inserted (never dropped), just tagged status='stale' so
    consumers can filter it."""
    fixture = json.loads((FIXTURES / "hii_watergate_sample.json").read_text(encoding="utf-8"))
    watergate_data = fixture.get("watergate_data") or fixture
    recs = watergate_data.get("data", [])
    old_iso = "2020-01-01T00:00:00+00:00"
    for rec in recs:
        rec["watergate_datetime_in"] = "2020-01-01 00:00"
        rec["watergate_datetime_out"] = None
    body = json.dumps(fixture).encode("utf-8")
    monkeypatch.setattr(parsers, "_th_local_to_utc_iso", lambda s: old_iso if s else None)
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_hii_watergate(conn)
    assert res.ok is True
    assert res.counts["inserted"] > 0
    assert res.counts["stale"] == res.counts["inserted"]
    rows = conn.execute(
        "SELECT * FROM observations WHERE source_id='hii_watergate'").fetchall()
    assert len(rows) == res.counts["inserted"]  # never pruned
    assert all(r["status"] == "stale" for r in rows)


def test_rid_res_table_collector_stores_documents_not_observations(monkeypatch, tmp_path):
    body = (FIXTURES / "rid_res_table_sample.html").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_rid_res_table(conn)
    assert res.ok is True
    assert res.counts["documents"] > 0
    obs = conn.execute(
        "SELECT * FROM observations WHERE source_id='rid_res_table'").fetchall()
    assert len(obs) == 0  # no numeric field on this page -- never fabricated
    docs = conn.execute(
        "SELECT * FROM documents WHERE source_id='rid_res_table'").fetchall()
    assert len(docs) == res.counts["documents"]



def test_egat_water_crisis_collector(monkeypatch, tmp_path):
    body = (FIXTURES / "egat_water_crisis_sample.html").read_bytes()
    monkeypatch.setattr(collect, "_one_get", _fake_one_get(body))
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    conn = store.connect(tmp_path / "t.sqlite")
    res = collect.collect_egat_water_crisis(conn)
    assert res.ok is True
    # MUST-FIX #E: now emits one row per available variable (storage_pct/storage_mcm/
    # level_m/inflow_mcm/release_mcm/release_m3s_computed), not just storage_pct -- 3
    # dams x 6 variables = 18 (all fixture dams have every field populated).
    assert res.counts["inserted"] == 18
    row = conn.execute(
        "SELECT * FROM observations WHERE source_id='egat_water_crisis' "
        "AND station_name='ภูมิพล' AND variable='egat_dam_storage_pct'").fetchone()
    assert row is not None
    assert row["value"] == pytest.approx(62.92)
    release_row = conn.execute(
        "SELECT * FROM observations WHERE source_id='egat_water_crisis' "
        "AND station_name='ภูมิพล' AND variable='egat_dam_release_m3s_computed'").fetchone()
    assert release_row is not None
    release_mcm_row = conn.execute(
        "SELECT * FROM observations WHERE source_id='egat_water_crisis' "
        "AND station_name='ภูมิพล' AND variable='egat_dam_release_mcm'").fetchone()
    assert release_row["value"] == pytest.approx(
        release_mcm_row["value"] * 1e6 / 86400.0)
    assert release_row["provenance_json"] is not None
    assert "MEASURED-derived" in release_row["provenance_json"]
    # station_code is now name-keyed, not the previous shared None (which could only
    # ever keep one dam's same-variable/same-timestamp row via the unique index).
    assert row["station_code"] == "dam:egat_water_crisis:ภูมิพล"



def test_all_new_sources_dry_run_no_network(monkeypatch, tmp_path):
    def _boom(*a, **k):
        raise AssertionError("network call attempted during --dry-run")
    monkeypatch.setattr(collect.urllib.request, "urlopen", _boom)
    new_ids = ["thaiwater_waterlevel", "hii_dam", "hii_watergate", "rid_res_table",
               "egat_water_crisis", "openmeteo_flood", "openmeteo_ensemble",
               "openmeteo_marine", "nasa_power", "openmeteo_multimodel"]
    results = collect.run(new_ids, dry_run=True, db_path=tmp_path / "t.sqlite")
    assert all(r.ok for r in results), [r for r in results if not r.ok]



def test_new_sources_all_present_in_registry_and_collectors():
    reg = collect.load_registry()
    new_ids = ["thaiwater_waterlevel", "hii_dam", "hii_watergate", "rid_res_table",
               "egat_water_crisis", "openmeteo_flood", "openmeteo_ensemble",
               "openmeteo_marine", "nasa_power", "openmeteo_multimodel"]
    for sid in new_ids:
        assert sid in reg, f"{sid} missing from registry.yaml"
        assert sid in collect.COLLECTORS, f"{sid} missing from collect.COLLECTORS"
