"""Tests for site/build_data.py's build-4 (2026-09-27) burden-ledger gate-state upgrade:
prefer a MEASURED `bma_watermap` gate_opening_m reading over the existing in/out-level
inference, per structure, when one is present -- falling back to the pre-existing
inference otherwise. See docs/knowledge/BMA_WATER_MAP_PROBE.md and
site/inputs/canals/control_structures.yaml (ssb10 = ปตร.แสนแสบ-มีนบุรี, WL.SSB.10; ssb09
= ปตร.บางชัน, WL.SSB.09; pwt04 = ปตร.ประเวศ-ลาดกระบัง, WL.PWT.04).
"""
import sys
from pathlib import Path

SITE_DIR = Path(__file__).parent.parent / "site"
if str(SITE_DIR) not in sys.path:
    sys.path.insert(0, str(SITE_DIR))

import build_data as bd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store  # noqa: E402


def _conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


def test_latest_measured_gate_state_none_without_reading(tmp_path):
    conn = _conn(tmp_path)
    assert bd._latest_measured_gate_state(conn, "WL.SSB.10") is None
    assert bd._latest_measured_gate_state(None, "WL.SSB.10") is None
    assert bd._latest_measured_gate_state(conn, None) is None


def test_latest_measured_gate_state_closed_when_all_gates_zero(tmp_path):
    conn = _conn(tmp_path)
    store.insert_observation(
        conn, source_id="bma_watermap", station_code="WL.SSB.09#gate01",
        station_name="ปตร.บางชัน", lat=13.7972, lon=100.70458,
        variable="gate_opening_m", value=0.0, unit="m",
        observed_at_utc="2026-09-27T10:00:00+00:00",
        fetched_at_utc="2026-09-27T10:05:00+00:00", trust_tier="official_telemetry")
    g = bd._latest_measured_gate_state(conn, "WL.SSB.09")
    assert g is not None
    assert g["is_open"] is False
    assert g["gates_m"] == {1: 0.0}


def test_latest_measured_gate_state_open_when_any_gate_positive(tmp_path):
    conn = _conn(tmp_path)
    store.insert_observation(
        conn, source_id="bma_watermap", station_code="WL.PWT.04#gate01",
        station_name="ปตร.ประเวศ-ลาดกระบัง", lat=13.72411, lon=100.74987,
        variable="gate_opening_m", value=0.5, unit="m",
        observed_at_utc="2026-09-27T10:00:00+00:00",
        fetched_at_utc="2026-09-27T10:05:00+00:00", trust_tier="official_telemetry")
    g = bd._latest_measured_gate_state(conn, "WL.PWT.04")
    assert g["is_open"] is True
    assert g["gates_m"] == {1: 0.5}


def test_latest_measured_gate_state_only_keeps_latest_tick():
    """An older tick's gate reading must never mix with the latest tick's own set."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        conn = _conn(Path(d))
        store.insert_observation(
            conn, source_id="bma_watermap", station_code="WL.PWT.03#gate01",
            station_name="ปตร.ประเวศ-วัดกระทุ่ม", lat=None, lon=None,
            variable="gate_opening_m", value=0.0, unit="m",
            observed_at_utc="2026-09-27T09:00:00+00:00",
            fetched_at_utc="2026-09-27T09:05:00+00:00", trust_tier="official_telemetry")
        store.insert_observation(
            conn, source_id="bma_watermap", station_code="WL.PWT.03#gate01",
            station_name="ปตร.ประเวศ-วัดกระทุ่ม", lat=None, lon=None,
            variable="gate_opening_m", value=4.6, unit="m",
            observed_at_utc="2026-09-27T10:00:00+00:00",
            fetched_at_utc="2026-09-27T10:05:00+00:00", trust_tier="official_telemetry")
        g = bd._latest_measured_gate_state(conn, "WL.PWT.03")
        assert g["gates_m"] == {1: 4.6}
        assert g["observed_at"] == "2026-09-27T10:00:00+00:00"


def test_burden_declared_state_prefers_measured_over_inference():
    sdef = {"is_gate": True}
    reading = {"level_m": 1.0, "canal_out": 0.5}  # would infer OPEN under the old rule
    state, basis = bd._burden_declared_state(sdef, reading, 0.04,
                                              measured_gate={"is_open": False, "gates_m": {1: 0.0}})
    assert state == bd.blmod.STATE_CLOSED
    assert basis == "วัดจริง"


def test_burden_declared_state_falls_back_to_inference_without_measured_gate():
    sdef = {"is_gate": True}
    reading = {"level_m": 0.3, "canal_out": 0.5}  # out-in=0.2 > eps_sum -> CLOSED, inferred
    state, basis = bd._burden_declared_state(sdef, reading, 0.04, measured_gate=None)
    assert state == bd.blmod.STATE_CLOSED
    assert basis == "อนุมาน"


def test_burden_declared_state_control_state_missing_has_no_basis():
    state, basis = bd._burden_declared_state({}, None, 0.04, measured_gate=None)
    assert state is None and basis is None


def test_build_burden_ledger_readout_ssb09_uses_measured_gate(tmp_path):
    """End-to-end: ssb09 (WL.SSB.09, ปตร.บางชัน) gets a MEASURED closed-gate reading;
    its inferred in/out levels (if wired via canal_by_code) must be OVERRIDDEN, and the
    structure_rows output must say so via state_basis."""
    conn = _conn(tmp_path)
    store.insert_observation(
        conn, source_id="bma_watermap", station_code="WL.SSB.09#gate01",
        station_name="ปตร.บางชัน", lat=13.7972, lon=100.70458,
        variable="gate_opening_m", value=0.0, unit="m",
        observed_at_utc="2026-09-27T10:00:00+00:00",
        fetched_at_utc="2026-09-27T10:05:00+00:00", trust_tier="official_telemetry")
    # no canal_by_code reading at all for ssb09 -- measured gate state must still resolve
    # the structure's control state even with zero in/out telemetry this tick.
    out = bd.build_burden_ledger_readout({}, "2026-09-27T10:10:00+00:00", obs_conn=conn)
    assert out["available"] is True
    ssb09 = out["structures"]["ssb09"]
    assert ssb09["state"] == bd.blmod.STATE_CLOSED
    assert ssb09["state_basis"] == "วัดจริง"
    assert ssb09["measured_gates_m"] == {1: 0.0}


def test_build_burden_ledger_readout_without_obs_conn_is_unchanged_inference_only():
    out = bd.build_burden_ledger_readout({}, "2026-09-27T10:10:00+00:00")
    assert out["available"] is True
    for row in out["structures"].values():
        assert row["measured_gates_m"] is None
        assert row.get("state_basis") in (None, "อนุมาน")


def test_measured_vs_inferred_gate_state_disagreement_writes_contradiction(tmp_path):
    """A structure where the MEASURED gate reading (bma_watermap, closed) disagrees with
    what the pre-existing in/out-level inference would have said (open, since out-in
    stays within eps_sum) -- the measured reading must still be rendered as the
    structure's canonical `state`, but the disagreement must be flagged
    (gate_state_contradiction=True) and logged as a contradiction row, never silently
    dropped (founder rule, build 4, 2026-09-27: "ระวังข้อมูลขัดแย้งด้วย")."""
    conn = store.connect(tmp_path / "test.sqlite")
    # MEASURED: gate closed (0.0m)
    store.insert_observation(
        conn, source_id="bma_watermap", station_code="WL.SSB.10#gate01",
        station_name="ปตร.แสนแสบ-มีนบุรี", lat=None, lon=None,
        variable="gate_opening_m", value=0.0, unit="m",
        observed_at_utc="2026-09-27T10:00:00+00:00",
        fetched_at_utc="2026-09-27T10:05:00+00:00", trust_tier="official_telemetry")
    # canal_by_code reading that the OLD inference rule would read as OPEN (out-in
    # within the combined resolution, 0.02*2=0.04m -- no CLOSED trigger)
    canal_by_code = {
        "WL.SSB.10": {"level_m": 1.00, "canal_out": 1.01,
                      "observed_at": "2026-09-27T10:00:00+00:00"},
    }
    out = bd.build_burden_ledger_readout(canal_by_code, "2026-09-27T10:10:00+00:00",
                                          obs_conn=conn)
    ssb10 = out["structures"]["ssb10"]
    assert ssb10["state"] == bd.blmod.STATE_CLOSED  # measured wins, rendered as canonical
    assert ssb10["state_basis"] == "วัดจริง"
    assert ssb10["gate_state_contradiction"] is True
    assert ssb10["inferred_state_if_no_measurement"] == bd.blmod.STATE_OPEN
    rows = conn.execute(
        "SELECT topic, source_a, value_a, source_b, value_b FROM contradictions "
        "WHERE topic LIKE 'gate_state:%'").fetchall()
    assert len(rows) == 1
    topic, source_a, value_a, source_b, value_b = rows[0]
    assert topic == "gate_state:WL.SSB.10"
    assert source_a == "bma_watermap_gate_opening_m" and value_a == bd.blmod.STATE_CLOSED
    assert source_b == "inferred_level_diff" and value_b == bd.blmod.STATE_OPEN


def test_measured_matches_inferred_no_contradiction(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    store.insert_observation(
        conn, source_id="bma_watermap", station_code="WL.PWT.04#gate01",
        station_name="ปตร.ประเวศ-ลาดกระบัง", lat=None, lon=None,
        variable="gate_opening_m", value=0.5, unit="m",
        observed_at_utc="2026-09-27T10:00:00+00:00",
        fetched_at_utc="2026-09-27T10:05:00+00:00", trust_tier="official_telemetry")
    # measured=OPEN; inference would also say OPEN (is_gate declared, no CLOSED trigger)
    canal_by_code = {
        "WL.PWT.04": {"level_m": 0.80, "canal_out": 0.60,
                      "observed_at": "2026-09-27T10:00:00+00:00"},
    }
    out = bd.build_burden_ledger_readout(canal_by_code, "2026-09-27T10:10:00+00:00",
                                          obs_conn=conn)
    pwt04 = out["structures"]["pwt04"]
    assert pwt04["gate_state_contradiction"] is False
    assert conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE topic LIKE 'gate_state:%'"
    ).fetchone()[0] == 0
