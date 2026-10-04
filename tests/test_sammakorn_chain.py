"""Tests for site/build_data.py's build-6 (2026-09-27) Sammakorn head-chain readout
(PROP-FLOOD-04 instantiation) -- ซอย -> บึง (WL.SMK.01) -> คลองบ้านม้า 2 (WL.BMA.02) ->
แสนแสบ (WL.SSB.08), plus the explicit backflow-risk edge บ้านม้า 2 -> บึง added per the
founder's same-day correction ("สัมมากรต้องเชื่อมกับน้ำในคลองด้วย เพราะมันเป็นน้ำย้อนจากคลอง
ไม่ใช่แค่ปั๊ม"). Uses a real store.connect() tmp sqlite (has the `status` column the
sensor-fault guard depends on), never the real observations.sqlite or network.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "site"))
sys.path.insert(0, str(REPO_ROOT))

import store  # noqa: E402
import build_data as bd  # noqa: E402
from tools.heromap.sammakorn_map import classify_tier, load_normal_levels  # noqa: E402

REF_ISO = "2026-09-27T10:30:00+00:00"


def _obs(conn, station_code, value, observed_at, warning=None, critical=None, bank=None,
         status=None, source_id="bma_watermap"):
    store.insert_observation(
        conn, source_id=source_id, station_code=station_code, variable="canal_water_level_m",
        value=value, unit="m", observed_at_utc=observed_at,
        fetched_at_utc=observed_at, trust_tier="official_telemetry",
        warning=warning, critical=critical, bank=bank, status=status)


def test_soi_node_has_no_gauge():
    nodes = {"soi": bd.sammakorn_node_readout(None, "soi", bd.SAMMAKORN_CHAIN_NODES["soi"], REF_ISO)}
    assert nodes["soi"]["status_th"] == "NO_GAUGE"
    assert nodes["soi"]["value_m"] is None


def test_datum_unknown_refuses_true_delta_h_on_outflow_edge(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.SMK.01", 0.82, "2026-09-27T10:25:00+00:00", status="วิกฤต")
    _obs(conn, "WL.BMA.02", 0.73, "2026-09-27T10:25:00+00:00", status="ปกติ")
    nodes = {
        "pond": bd.sammakorn_node_readout(conn, "pond", bd.SAMMAKORN_CHAIN_NODES["pond"], REF_ISO),
        "banma2": bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"], REF_ISO),
    }
    edge_def = {"edge_id": "pond_to_banma2", "up": "pond", "down": "banma2", "kind": "outflow"}
    edge = bd.sammakorn_edge_readout(conn, edge_def, nodes, REF_ISO)
    # Both nodes' `datum` is declared None in SAMMAKORN_CHAIN_NODES (this repo's own
    # honest current state -- no MSL figure on record for either station) -- an outflow
    # edge must REFUSE a true ΔH, never fabricate one across an unknown datum.
    assert edge["status"] == "REFUSED"
    assert edge["refusal_reason"] == "DATUM_UNKNOWN"
    assert edge["delta_h"] is None
    # but the raw levels/timestamps still render (never hidden just because the edge refused)
    assert edge["h_up"] == 0.82
    assert edge["h_down"] == 0.73
    assert edge["observed_at_up"] == "2026-09-27T10:25:00+00:00"


def test_open_gate_flat_delta_h_reads_stalled(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.BMA.02", 0.50, "2026-09-27T10:25:00+00:00", status="ปกติ")
    _obs(conn, "WL.SMK.01", 0.51, "2026-09-27T10:25:00+00:00", status="ปกติ")
    nodes = {
        "banma2": bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"], REF_ISO),
        "pond": bd.sammakorn_node_readout(conn, "pond", bd.SAMMAKORN_CHAIN_NODES["pond"], REF_ISO),
    }
    # Force datum-known so delta_h is actually computed (this test exercises
    # flow_status/gate_state independence, not the datum gate itself).
    nodes["banma2"]["datum"] = nodes["pond"]["datum"] = "MSL"
    edge_def = {"edge_id": "banma2_to_pond", "up": "banma2", "down": "pond", "kind": "backflow-risk"}
    gate_state = {"value": "open", "basis": "measured"}
    edge = bd.sammakorn_edge_readout(conn, edge_def, nodes, REF_ISO, gate_state=gate_state,
                                      pumps_on=0)
    assert abs(edge["delta_h"]) < bd.SAMMAKORN_CHAIN_FLOW_EPSILON_M
    assert edge["gate_state"]["value"] == "open"
    assert edge["flow_status"]["value"] == "stalled"
    assert edge["flow_status"]["basis"] == "delta_h_flat"


def test_closed_gate_with_pumps_running_reads_moving(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.SMK.01", 0.82, "2026-09-27T10:25:00+00:00", status="วิกฤต")
    _obs(conn, "WL.BMA.02", 0.73, "2026-09-27T10:25:00+00:00", status="ปกติ")
    nodes = {
        "pond": bd.sammakorn_node_readout(conn, "pond", bd.SAMMAKORN_CHAIN_NODES["pond"], REF_ISO),
        "banma2": bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"], REF_ISO),
    }
    edge_def = {"edge_id": "pond_to_banma2", "up": "pond", "down": "banma2", "kind": "outflow"}
    gate_state = {"value": "closed", "basis": "measured"}
    # gate_state=CLOSED but pumps are actively running -- flow_status must still read
    # "moving" (pumps lift water regardless of gate state); the three readouts must
    # never be conflated into one another.
    edge = bd.sammakorn_edge_readout(conn, edge_def, nodes, REF_ISO, gate_state=gate_state,
                                      pumps_on=2)
    assert edge["gate_state"]["value"] == "closed"
    assert edge["flow_status"]["value"] == "moving"
    assert edge["flow_status"]["basis"] == "pumps_running"


def test_band_backflow_risk_unavailable_without_bank_threshold(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.BMA.02", 0.90, "2026-09-27T10:25:00+00:00", critical=0.44, status="วิกฤต")
    _obs(conn, "WL.SMK.01", 0.10, "2026-09-27T10:25:00+00:00", status="ปกติ")
    nodes = {
        "banma2": bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"], REF_ISO),
        "pond": bd.sammakorn_node_readout(conn, "pond", bd.SAMMAKORN_CHAIN_NODES["pond"], REF_ISO),
    }
    edge_def = {"edge_id": "banma2_to_pond", "up": "banma2", "down": "pond", "kind": "backflow-risk"}
    edge = bd.sammakorn_edge_readout(conn, edge_def, nodes, REF_ISO)
    # this repo's stations have no `bank` threshold populated yet (VERIFIED, see this
    # test's own fixture) -- the band fallback must say "unavailable", never guess a risk.
    assert edge["flow_direction"]["value"] == "unavailable"
    assert edge["backflow_active"] is None


def test_band_backflow_risk_flags_risk_when_thresholds_declared(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.BMA.02", 0.90, "2026-09-27T10:25:00+00:00", critical=0.44, status="วิกฤต")
    _obs(conn, "WL.SMK.01", 0.10, "2026-09-27T10:25:00+00:00", bank=0.30, status="ปกติ")
    nodes = {
        "banma2": bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"], REF_ISO),
        "pond": bd.sammakorn_node_readout(conn, "pond", bd.SAMMAKORN_CHAIN_NODES["pond"], REF_ISO),
    }
    edge_def = {"edge_id": "banma2_to_pond", "up": "banma2", "down": "pond", "kind": "backflow-risk"}
    edge = bd.sammakorn_edge_readout(conn, edge_def, nodes, REF_ISO)
    assert edge["flow_direction"]["value"] == "เสี่ยงย้อน"
    assert edge["backflow_active"] is True


def test_fault_input_excluded_from_chain(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.SMK.01", 0.82, "2026-09-27T10:25:00+00:00", status="ขัดข้อง")
    node = bd.sammakorn_node_readout(conn, "pond", bd.SAMMAKORN_CHAIN_NODES["pond"], REF_ISO)
    # the fault guard from Commit A means a faulted row's `value` was never even stored
    # (level_m None at write time) -- so the node reads NO_DATA, not a faulted number.
    assert node["value_m"] is None


def test_sammakorn_chain_readout_top_level_shape(tmp_path):
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.SMK.01", 0.82, "2026-09-27T10:25:00+00:00", status="วิกฤต")
    _obs(conn, "WL.BMA.02", 0.73, "2026-09-27T10:25:00+00:00", status="ปกติ")
    _obs(conn, "WL.SSB.08", -0.09, "2026-09-27T10:25:00+00:00", status="ปกติ")
    out = bd.sammakorn_chain_readout(conn, REF_ISO, pump_rows=[
        {"code": "ST.SPS.02", "pumps_on": 1}, {"code": "ST.SPS.03", "pumps_on": 0}])
    assert out["available"] is True
    edge_ids = {e["edge_id"] for e in out["edges"]}
    assert edge_ids == {"soi_to_pond", "pond_to_banma2", "banma2_to_pond", "banma2_to_saensaeb"}
    backflow_edge = next(e for e in out["edges"] if e["edge_id"] == "banma2_to_pond")
    assert backflow_edge["kind"] == "backflow-risk"
    assert len(out["community_backflow_evidence"]) == 2
    assert all(ev["tag"] == "RELAYED" for ev in out["community_backflow_evidence"])


# ---- founder rule (verbatim, real incident 2026-09-27): WL.BMA.02 (คลองบ้านม้า 2, 0.71 ม.)
# showed "ยังไม่มีเกณฑ์ปกติ" on the hero map (tools/heromap/sammakorn_map.classify_tier) but
# "ปกติ" in this section's own sammakorn_node_readout() -- SAME station, SAME reading, two
# different answers. "ปกติ" may only ever render when a normal_level is on record AND the
# reading is at/below it; a station with no normal_level on record must render
# "ยังไม่มีเกณฑ์ปกติ" (or "สูงกว่าปกติ" if it breaches nothing but its own normal), never "ปกติ".
#
# UPDATED then RE-CORRECTED 2026-09-27 (TODO #50/#62, bma_plan2569 extraction, then a P0
# same-day fix): sources/canal_normal_levels.yaml briefly carried an `official_threshold`
# row (the BMA plan's printed +0.40 m.MSL operating ceiling, p.191) KEYED to WL.BMA.02 --
# but that row's own lat/lon (and the 0.40/0.50 m lines) belong to the PUMP STATION
# ST.SPS.01, ~630 m away from WL.BMA.02's own gauge location, on a datum that has never
# been confirmed to match WL.BMA.02's own feed (whose warning/critical are 2.14/2.68 m --
# ~1.7 m off, consistent with a different datum, not the same ceiling). That row is now
# re-keyed to ST.SPS.01 (see that file's second CORRECTION note) and
# `load_canal_normal_levels()`/`load_normal_levels()` both refuse any `official_threshold`
# row that isn't within 100 m of its station with a confirmed datum -- so WL.BMA.02 is
# back to NO_NORMAL_BASIS/"ยังไม่มีเกณฑ์ปกติ" (grey), never "ปกติ" and never "สูงกว่าปกติ"
# (that would require WL.BMA.02's OWN confirmed normal level, still OPEN).

def test_banma2_has_no_normal_basis_after_mislocated_row_refused(tmp_path):
    """The `official_threshold` row that was briefly keyed to WL.BMA.02 (+0.40 m.MSL)
    actually describes ST.SPS.01, a station ~630 m away on an unconfirmed datum -- P0
    incident, 2026-09-27. Refused by `_official_threshold_row_admissible()`, so a 0.71 m
    reading (well below WL.BMA.02's OWN warning/critical, 2.14/2.68 m) must render
    NO_NORMAL_BASIS / "ยังไม่มีเกณฑ์ปกติ" -- never "ปกติ" and never "สูงกว่าปกติ"."""
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.BMA.02", 0.71, "2026-09-27T13:45:00+00:00",
         warning=2.14, critical=2.68, status="ปกติ")  # agency's own raw label, ignored
    node = bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"],
                                      "2026-09-27T13:50:00+00:00")
    assert node["status_th"] != "ปกติ"
    assert node["status_th"] != "สูงกว่าปกติ"
    assert node["status_th"] == "ยังไม่มีเกณฑ์ปกติ"
    assert node["status_code"] == "NO_NORMAL_BASIS"
    assert node["normal_level_basis"] == "OPEN"
    assert node["normal_level_m"] is None
    # the raw agency text is preserved, never silently discarded
    assert node["agency_status_th"] == "ปกติ"


def test_banma2_hero_and_chain_labels_agree_for_same_reading(tmp_path):
    """Hero map (`classify_tier`, independently re-derived) and the sammakorn_chain node
    readout (`sammakorn_node_readout`) must produce the SAME Thai word for the SAME
    station+reading -- the exact contradiction the founder flagged for WL.BMA.02. After
    the P0 re-key/refusal fix (see module note above), that word is NO_BASELINE /
    "ยังไม่มีเกณฑ์ปกติ" again, not "สูงกว่าปกติ"."""
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.BMA.02", 0.71, "2026-09-27T13:45:00+00:00",
         warning=2.14, critical=2.68, status="ปกติ")
    node = bd.sammakorn_node_readout(conn, "banma2", bd.SAMMAKORN_CHAIN_NODES["banma2"],
                                      "2026-09-27T13:50:00+00:00")
    nlevels = load_normal_levels()
    _, hero_word = classify_tier(node["value_m"], node["warning"], node["critical"],
                                  node["bank"], nlevels.get(node["station_code"]))
    assert hero_word == node["status_th"] == "ยังไม่มีเกณฑ์ปกติ"


# ---- neighbour-consistency (suspect-station) rule, founder verbatim 2026-09-27:
# "แสนแสบเสรีไทยทำไมปกติ ตรวจหลายแห่งรวมหน่อย" ----

def test_neighbour_consistency_check_pure_synthetic_outlier():
    """Synthetic 5-station canal, one outlier -> suspect flag. Generic, reusable
    algorithm (not tied to Saen Saep specifically)."""
    order = ["A", "B", "C", "D", "E"]
    statuses = {"A": "WATCH", "B": "CRITICAL", "C": "NORMAL", "D": "CRITICAL", "E": "WATCH"}
    result = bd.neighbour_consistency_check(order, statuses, "C", window=2)
    assert result["suspect"] is True
    assert result["own_status"] == "NORMAL"
    assert set(result["neighbour_statuses"]) == {"A", "B", "D", "E"}


def test_neighbour_consistency_check_not_suspect_when_matches_a_neighbour():
    order = ["A", "B", "C", "D", "E"]
    statuses = {"A": "NORMAL", "B": "CRITICAL", "C": "NORMAL", "D": "CRITICAL", "E": "WATCH"}
    result = bd.neighbour_consistency_check(order, statuses, "C", window=2)
    assert result["suspect"] is False


def test_neighbour_consistency_check_insufficient_data_never_flags():
    order = ["A", "B", "C", "D", "E"]
    statuses = {"C": "NORMAL", "D": "CRITICAL"}  # only 1 real neighbour (B/E missing)
    result = bd.neighbour_consistency_check(order, statuses, "C", window=2)
    assert result["suspect"] is False
    assert result["reason"] == "insufficient_neighbour_data"


def test_neighbour_consistency_check_target_not_in_order():
    assert bd.neighbour_consistency_check(["A", "B"], {"A": "NORMAL"}, "Z")["suspect"] is False


def test_saensaeb_suspect_check_flags_wl_ssb_08_like_real_incident(tmp_path, monkeypatch):
    """Real incident shape (founder-verified 2026-09-27): WL.SSB.08 reads NORMAL while
    every declared neighbour (SSB.07/06/09/10/12) is WATCH/CRITICAL.
    saensaeb_suspect_check() opens its OWN write connection to bd.OBS_DB_PATH (the real
    data/observations.sqlite) to log a contradiction whenever `suspect` comes back True
    -- independent of the `conn` passed in for reading -- so this test (which
    deliberately triggers `suspect=True`) redirects bd.OBS_DB_PATH to tmp_path first to
    avoid writing into the real gitignored store."""
    monkeypatch.setattr(bd, "OBS_DB_PATH", tmp_path / "real_obs_path_placeholder.sqlite")
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.SSB.08", -0.13, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    _obs(conn, "WL.SSB.07", 0.40, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    _obs(conn, "WL.SSB.06", 0.49, "2026-09-27T17:00:00+00:00",
         warning=0.20, critical=0.45, bank=1.50)
    _obs(conn, "WL.SSB.09", 0.95, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    _obs(conn, "WL.SSB.10", 1.01, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    _obs(conn, "WL.SSB.12", 1.22, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    result = bd.saensaeb_suspect_check(conn, "2026-09-27T17:00:00+00:00")
    assert result["suspect"] is True
    assert result["own_status"] == "NORMAL"
    assert "–" in result["band_label_th"] or result["band_label_th"] in ("เตือน", "วิกฤต")


def test_sammakorn_chain_readout_excludes_suspect_saensaeb_as_anchor(tmp_path, monkeypatch):
    """The banma2->saensaeb edge must REFUSE (not compute a real reading) once WL.SSB.08
    is flagged suspect -- excluded as an anchor, never silently used. Same
    bd.OBS_DB_PATH redirect as test_saensaeb_suspect_check_flags_wl_ssb_08_like_real_incident
    above, for the same reason (saensaeb_suspect_check()'s own real-db write-on-detect)."""
    monkeypatch.setattr(bd, "OBS_DB_PATH", tmp_path / "real_obs_path_placeholder.sqlite")
    conn = store.connect(tmp_path / "test.sqlite")
    _obs(conn, "WL.SMK.01", 0.50, "2026-09-27T17:00:00+00:00", status="ปกติ")
    _obs(conn, "WL.BMA.02", 0.40, "2026-09-27T17:00:00+00:00", status="ปกติ")
    _obs(conn, "WL.SSB.08", -0.13, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    _obs(conn, "WL.SSB.07", 0.40, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    _obs(conn, "WL.SSB.06", 0.49, "2026-09-27T17:00:00+00:00",
         warning=0.20, critical=0.45, bank=1.50)
    _obs(conn, "WL.SSB.09", 0.95, "2026-09-27T17:00:00+00:00",
         warning=0.30, critical=0.60, bank=1.50)
    result = bd.sammakorn_chain_readout(conn, "2026-09-27T17:00:00+00:00")
    assert result["nodes"]["saensaeb"]["suspect"] is True
    edge = next(e for e in result["edges"] if e["edge_id"] == "banma2_to_saensaeb")
    assert edge["status"] == "REFUSED"
    assert edge["refusal_reason"] == "SUSPECT_NEIGHBOUR_MISMATCH"
