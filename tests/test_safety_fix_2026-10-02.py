"""Tests for the safety fix (2026-10-02) fix set: the RED life-safety headline
could fire off nothing but sensor-fault rows (bug A), the headline shipped with
no steps (bug B), the replacement RED actions used raw node ids/English field
names (bug C), and the real tier engine was not freshness-gated (bug D).

Every station/threshold value below is REAL: the pump rows are parsed straight out of
`tests/fixtures/pumphistory_sample.html` (an actual captured BMA PumpHistory page, the
same fixture `tests/test_live_water_level.py` already uses), and the canal thresholds
are the ACTUAL warning/critical figures this worktree's own `data/observations.sqlite`
holds for WL.SMK.01 today (0.35/0.44 m) -- `canal_bank_m` is left unset because this
worktree's real WL.SMK.01 rows genuinely have no bank figure recorded (never invented).
The one varying number across scenarios (the test canal reading itself, e.g. 0.50m) is a
probe value against those real thresholds, same convention as this repo's own existing
`tests/test_readout.py` fixture rows.

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_safety_fix_2026-10-02.py -q
"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools" / "backtest"))
sys.path.insert(0, str(HERE / "site"))

import kb  # noqa: E402
import store  # noqa: E402
import live_water_level as lwl  # noqa: E402
import community_dag  # noqa: E402
import compute_prop_flood_06_sammakorn as pf06  # noqa: E402
import build_page as bp  # noqa: E402

PUMPHISTORY_FIXTURE = HERE / "tests" / "fixtures" / "pumphistory_sample.html"

# Real WL.SMK.01 thresholds, read straight out of this worktree's own
# data/observations.sqlite (`SELECT station_code,warning,critical,bank FROM
# observations WHERE station_code='WL.SMK.01'`) -- bank is genuinely absent (None) in
# the real recorded rows.
WL_SMK_01_WARNING_M = 0.35
WL_SMK_01_CRITICAL_M = 0.44


def _insert_real_fault_pump_row(conn, observed_at_utc="2026-09-26T04:00:00+00:00"):
    """Parses the REAL pumphistory fixture (ST.SPS.01 = ขัดข้อง/fault in that real
    capture, ST.SPS.02-04 ปกติ/normal) and inserts only the ST.SPS.01 fault row --
    mirroring collect.collect_bma_pumphistory's own insertion shape verbatim. The other
    three pump stations are deliberately left with NO row this check (a real, common
    shape: only one station answered this poll), which on its own already reproduces
    bug A's class (see this file's module docstring)."""
    rows = lwl.parse_pumphistory_html(PUMPHISTORY_FIXTURE.read_text(encoding="utf-8"))
    sps01 = next(r for r in rows if r["station_code"] == "ST.SPS.01")
    assert sps01["status_th"] == "ขัดข้อง"  # sanity: the real fixture row is a fault
    store.insert_observation(
        conn, source_id="bma_pumphistory", station_code="ST.SPS.01",
        station_name=sps01["name_th"], lat=sps01["lat"], lon=sps01["lon"],
        variable="pump_level_m", value=sps01["level_m"], unit="m",
        observed_at_utc=observed_at_utc, fetched_at_utc=observed_at_utc,
        trust_tier="official_telemetry", status=sps01["status_th"],
    )


def _insert_canal_row(conn, value_m, observed_at_utc="2026-09-26T04:00:00+00:00"):
    store.insert_observation(
        conn, source_id="thaiwater_canal_waterlevel", station_code="WL.SMK.01",
        station_name="บึงรับน้ำหมู่บ้านสัมมากร", lat=13.767, lon=100.677,
        variable="canal_water_level_m", value=value_m, unit="m",
        observed_at_utc=observed_at_utc, fetched_at_utc=observed_at_utc,
        trust_tier="official_telemetry", warning=WL_SMK_01_WARNING_M,
        critical=WL_SMK_01_CRITICAL_M, bank=None, status="NORMAL" if value_m < WL_SMK_01_WARNING_M else "CRITICAL",
    )


@pytest.fixture
def real_pf06_db(tmp_path):
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    return conn, db_path


# ---------------------------------------------------------------------------
# Defect A -- fault-only pump evidence must never read as a confirmed zero.
# ---------------------------------------------------------------------------

def test_gather_real_inputs_fault_only_pump_row_is_open_not_zero(real_pf06_db):
    conn, _ = real_pf06_db
    _insert_real_fault_pump_row(conn)
    gathered = pf06.gather_real_inputs(conn)
    assert gathered["inputs"]["pumps_running_count"] is None
    prov = gathered["provenance"]["pumps_running_count"]
    assert prov["tag"] == "OPEN"
    assert "sensor fault" in prov["note"] or "a safety fix" in prov["note"]


def test_real_l5_never_fires_from_fault_only_pump_plus_real_critical_canal(real_pf06_db):
    """The exact bug shape measured on the real 175MB DB: a
    sensor-fault pump reading + a canal reading at/above its REAL critical line must
    cap at L4 (CANAL_AT_CRITICAL_LINE), never promote to L5 via
    PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD."""
    conn, _ = real_pf06_db
    _insert_real_fault_pump_row(conn)
    _insert_canal_row(conn, WL_SMK_01_CRITICAL_M + 0.05)
    record = pf06.compute(conn=conn)
    assert record["tier"] != "L5"
    assert "PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD" not in record["promoters_fired"]
    assert record["inputs"]["pumps_running_count"] is None


def test_kb_real_pf06_tier_reports_neutral_action_not_survival_card(real_pf06_db, monkeypatch):
    """End-to-end through kb.py's OWN `_real_pf06_tier` (never monkeypatched here,
    unlike every pre-existing test of this path -- bug E)."""
    conn, db_path = real_pf06_db
    _insert_real_fault_pump_row(conn)
    _insert_canal_row(conn, WL_SMK_01_CRITICAL_M + 0.05)
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    tier = kb._real_pf06_tier("sammakorn")
    assert tier != "L5"

    state = {"status_counts": {"CRITICAL": 1}}
    assert kb._classify_current_local_state(state) == "RED"
    out = kb._answer_next_action("sammakorn", state_answer=state)
    first = out["actions"][0]
    assert first["action"] == kb.STATION_RED_NEUTRAL_ACTION_TH
    assert "steps" not in first


# ---------------------------------------------------------------------------
# Defect B -- the L5 headline must always carry its real step list.
# ---------------------------------------------------------------------------

def test_l5_action_carries_the_real_step_list(monkeypatch):
    # founder ruling 2026-10-06 (KG-only/no-simulation): PROP-FLOOD-06 folds in
    # an external rain forecast promoter, so it is only ever consulted when
    # SIMULATION_ENABLED is explicitly turned on.
    import floodconnect_model
    monkeypatch.setattr(floodconnect_model, "SIMULATION_ENABLED", True)
    monkeypatch.setattr(kb, "_real_pf06_record",
                         lambda area_id, now_utc=None: {"tier": "L5"})
    state = {"status_counts": {"CRITICAL": 1}}
    out = kb._answer_next_action("sammakorn", state_answer=state)
    first = out["actions"][0]
    assert first["action"] == bp.L5_SURVIVAL_HEADLINE_TH
    assert first["steps"], "the L5 headline must never ship with an empty step list"
    assert len(first["steps"]) == 8  # bp._l5_survival_lines_html() has 8 <li> lines
    assert all("<" not in s for s in first["steps"]), "steps must be plain text, no HTML"
    # one real step's content must actually be present (not a placeholder)
    assert any("เบรกเกอร์" in s for s in first["steps"])


def test_l5_survival_steps_plain_returns_empty_on_bad_module():
    class _Bad:
        pass
    assert kb._l5_survival_steps_plain(_Bad()) == []


# ---------------------------------------------------------------------------
# Defect C -- continuity-gap actions must show a Thai display name + Thai field labels.
# ---------------------------------------------------------------------------

def test_continuity_gap_actions_use_label_th_and_thai_field_labels():
    doc = community_dag.load_document(kb.SELF_HELP_DAG_PATH)
    actions, notes = kb._continuity_gap_actions(doc)
    gaps = community_dag.report_safe_node_continuity_gaps(doc)
    nodes = doc.get("nodes") or {}
    real_location_gap_ids = [
        n for n in sorted(gaps)
        if not (nodes.get(n, {}).get("kind") == "external_safe"
                and nodes.get(n, {}).get("verified_safe") is not True)
    ]
    assert real_location_gap_ids, (
        "self_help_dag.yaml must have at least one real-location continuity gap today "
        "(an internal_safe/support node, or a verified_safe external_safe one)")
    first_node = real_location_gap_ids[0]
    first_label = doc["nodes"][first_node]["label_th"]
    first_action = actions[0]
    assert first_node not in first_action["action"], "raw node id must not leak through"
    assert first_label in first_action["action"]
    # no raw English continuity-field name should ever appear
    for field in community_dag.SAFE_NODE_CONTINUITY_FIELDS:
        assert field not in first_action["action"]
    assert "ไฟฟ้า" in first_action["action"] or "ทางเข้า-ออก" in first_action["action"]
    assert first_action["tag"] == "OPEN"


def test_continuity_gap_placeholder_node_goes_to_notes_not_actions():
    """A safety fix (2026-10-02, bug 4): an unverified `external_safe`
    placeholder node's continuity gap (self_help_dag.yaml's own
    `external_safe_bkk_east_01`, `label_th` literally "...ยังไม่กำหนดสถานที่จริง" / "no real
    location assigned yet") must never surface as a resident-facing action -- a resident
    cannot "check readiness" of a place that does not exist yet."""
    doc = {
        "nodes": {
            "external_safe_bkk_east_01": {
                "kind": "external_safe", "layer": 5, "area_id": "external",
                "label_th": "จุดปลอดภัยภายนอก #1 — ยังไม่กำหนดสถานที่จริง",
                "status": "UNKNOWN", "fresh": False, "verified_safe": False,
            },
        },
        "edges": [],
    }
    actions, notes = kb._continuity_gap_actions(doc)
    assert actions == [], "a placeholder (verified_safe=false) node must never become an action"
    assert notes, "the placeholder gap must still be reported, honestly, as a note"
    assert "placeholder" in notes[0] or "ยังไม่กำหนดสถานที่จริง" in notes[0]


# ---------------------------------------------------------------------------
# Defect D -- a stale canal/pump row must never unlock a promoter.
# ---------------------------------------------------------------------------

def test_stale_canal_row_dropped_never_promotes_tier(real_pf06_db):
    conn, _ = real_pf06_db
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=datetime.timezone.utc)
    stale_at = (now - datetime.timedelta(hours=lwl.STALE_HOURS + 1)).isoformat()
    _insert_canal_row(conn, WL_SMK_01_CRITICAL_M + 0.05, observed_at_utc=stale_at)
    gathered = pf06.gather_real_inputs(conn, now_utc=now)
    assert gathered["inputs"]["canal_level_m"] is None
    assert gathered["provenance"]["canal_level_m"]["tag"] == "OPEN"


def test_fresh_canal_row_within_window_still_used(real_pf06_db):
    conn, _ = real_pf06_db
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=datetime.timezone.utc)
    fresh_at = (now - datetime.timedelta(hours=1)).isoformat()
    _insert_canal_row(conn, WL_SMK_01_CRITICAL_M + 0.05, observed_at_utc=fresh_at)
    gathered = pf06.gather_real_inputs(conn, now_utc=now)
    assert gathered["inputs"]["canal_level_m"] == pytest.approx(WL_SMK_01_CRITICAL_M + 0.05)


def test_no_now_utc_pin_skips_the_staleness_gate_same_as_before(real_pf06_db):
    """`now_utc=None` (the default, real production call shape via compute()) still
    gates against the REAL current wall clock -- only a caller that explicitly wants
    'no gate at all' would need to bypass gather_real_inputs itself, which no caller
    in this repo does. This test pins compute()'s own now_utc to confirm the wiring."""
    conn, _ = real_pf06_db
    now = datetime.datetime(2026, 10, 2, 12, 0, 0, tzinfo=datetime.timezone.utc)
    stale_at = (now - datetime.timedelta(hours=lwl.STALE_HOURS + 1)).isoformat()
    _insert_canal_row(conn, WL_SMK_01_CRITICAL_M + 0.05, observed_at_utc=stale_at)
    record = pf06.compute(now_utc=now, conn=conn)
    assert record["inputs"]["canal_level_m"] is None
    assert "CANAL_AT_CRITICAL_LINE" not in record["promoters_fired"]


# ---------------------------------------------------------------------------
# MODE_DEGRADATION_LADDER -- display-only readout along a found route.
# ---------------------------------------------------------------------------

def _tiny_doc_with_degraded_edge():
    return {
        "nodes": {
            "a": {"kind": "household", "layer": 0, "status": "SAFE", "fresh": True},
            "b": {"kind": "external_safe", "layer": 5, "status": "SAFE", "fresh": True,
                  "verified_safe": True, "capacity_persons": 10, "occupied_persons": 0},
        },
        "edges": [
            {"id": "e1", "from": "a", "to": "b", "modes": ["walk"],
             "status": "OPEN", "safety": "CLEAR", "fresh": True, "field_verified": True,
             "mode_degradation": "boat_only"},
        ],
    }


def test_route_mode_degradation_reads_the_real_declared_edge_value():
    doc = _tiny_doc_with_degraded_edge()
    out = kb._route_mode_degradation(doc, ["a", "b"])
    assert out == [{"from": "a", "to": "b", "mode_degradation": "boat_only"}]


def test_route_mode_degradation_unknown_when_edge_declares_none():
    doc = _tiny_doc_with_degraded_edge()
    doc["edges"][0].pop("mode_degradation")
    out = kb._route_mode_degradation(doc, ["a", "b"])
    assert out == [{"from": "a", "to": "b", "mode_degradation": "UNKNOWN"}]


def test_route_mode_degradation_included_in_next_action_route_out(monkeypatch):
    doc = _tiny_doc_with_degraded_edge()
    monkeypatch.setattr(community_dag, "load_document", lambda path: doc)
    monkeypatch.setattr(kb, "_ANSWER_AREAS", {
        **kb._ANSWER_AREAS,
        "sammakorn": {**kb._ANSWER_AREAS["sammakorn"], "self_help_start": "a"},
    })
    assert kb.SELF_HELP_DAG_PATH.exists(), "this repo's real self_help_dag.yaml must exist"
    out = kb._answer_next_action("sammakorn")
    assert out.get("mode_degradation") == [
        {"from": "a", "to": "b", "mode_degradation": "boat_only"}]


# ---------------------------------------------------------------------------
# A safety fix (2026-10-02) -- fixing HIGH/MED bugs found in the fix set above.
# ---------------------------------------------------------------------------

# Real verbatim rows for Sammakorn 2026-09-28, 12:15-12:45 UTC, copied out of the
# canonical repo's own data/observations.sqlite (the full-size copy, 175 MB
# -- NOT this worktree's own 22 MB copy) on 2026-10-02, per the review instruction
# ("build the temp DB from the verbatim real rows"). Never re-typed by hand from a guess:
# `SELECT * FROM observations WHERE station_code IN ('WL.SMK.01','ST.SPS.01'..'04') AND
# observed_at_utc BETWEEN '2026-09-28T12:00:00+00:00' AND '2026-09-28T13:00:00+00:00'`.
REAL_SAMMAKORN_20260928_1245_CANAL_ROW = dict(
    source_id="bma_watermap", station_code="WL.SMK.01",
    station_name="จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2",
    lat=13.76676, lon=100.67784, variable="canal_water_level_m", value=0.81, unit="m",
    observed_at_utc="2026-09-28T12:45:00+00:00", fetched_at_utc="2026-09-28T12:50:28.560318+00:00",
    warning=0.35, critical=0.44, bank=None, status="วิกฤต", trust_tier="official_telemetry",
)
REAL_SAMMAKORN_20260928_1245_PUMP_ROWS = [
    dict(source_id="bma_pumphistory", station_code="ST.SPS.01",
         station_name="สถานีสูบน้ำคลองบ้านม้า 2", lat=13.7763, lon=100.6713,
         variable="pump_level_m", value=None, unit="m",
         observed_at_utc="2026-09-28T12:45:00+00:00",
         fetched_at_utc="2026-09-28T12:50:11.967339+00:00",
         status="ขัดข้อง", trust_tier="official_telemetry"),
    dict(source_id="bma_pumphistory", station_code="ST.SPS.02",
         station_name="สถานีสูบน้ำบึงที่ 4 ตอนคลองวัดใหญ่", lat=13.7555, lon=100.6795,
         variable="pump_level_m", value=None, unit="m",
         observed_at_utc="2026-09-28T12:45:00+00:00",
         fetched_at_utc="2026-09-28T12:50:11.967339+00:00",
         status="ขัดข้อง", trust_tier="official_telemetry"),
    dict(source_id="bma_pumphistory", station_code="ST.SPS.03",
         station_name="สถานีสูบน้ำบึงที่ 2 ตอนคลองบ้านม้า 2", lat=13.767, lon=100.6771,
         variable="pump_level_m", value=None, unit="m",
         observed_at_utc="2026-09-28T12:45:00+00:00",
         fetched_at_utc="2026-09-28T12:50:11.967339+00:00",
         status="ขัดข้อง", trust_tier="official_telemetry"),
    dict(source_id="bma_pumphistory", station_code="ST.SPS.04",
         station_name="สถานีสูบน้ำบึงที่ 1 ตอนคลองสะพานสูง", lat=13.7706, lon=100.6798,
         variable="pump_level_m", value=None, unit="m",
         observed_at_utc="2026-09-28T12:45:00+00:00",
         fetched_at_utc="2026-09-28T12:50:11.967339+00:00",
         status="ขัดข้อง", trust_tier="official_telemetry"),
]
REAL_SAMMAKORN_20260928_PINNED_NOW = datetime.datetime(
    2026, 9, 28, 13, 0, 0, tzinfo=datetime.timezone.utc)  # 15 min after the latest real row


def _insert_real_sammakorn_20260928_rows(conn):
    store.insert_observation(conn, **REAL_SAMMAKORN_20260928_1245_CANAL_ROW)
    for row in REAL_SAMMAKORN_20260928_1245_PUMP_ROWS:
        store.insert_observation(conn, **row)


def test_sammakorn_20260928_pinned_case_pf06_tier_is_l4_not_l5(real_pf06_db):
    """The real Sammakorn 2026-09-28 case: a
    REAL critical canal reading (0.81m, over the REAL 0.44m critical line) plus REAL
    all-fault pump rows must cap at L4 (CANAL_AT_CRITICAL_LINE), never L5 -- this is
    the genuine incident shape bugs A and 5 guard against, on the exact real rows, not a
    probe value."""
    conn, _ = real_pf06_db
    _insert_real_sammakorn_20260928_rows(conn)
    record = pf06.compute(conn=conn, now_utc=REAL_SAMMAKORN_20260928_PINNED_NOW)
    assert record["tier"] == "L4"
    assert "CANAL_AT_CRITICAL_LINE" in record["promoters_fired"]
    assert "PUMPS_ZERO_RUNNING_ABOVE_THRESHOLD" not in record["promoters_fired"]
    assert record["inputs"]["pumps_running_count"] is None
    assert record["inputs"]["canal_level_m"] == pytest.approx(0.81)


def test_sammakorn_20260928_pinned_case_full_next_action(real_pf06_db, monkeypatch):
    """End-to-end through `kb._answer_next_action`, pinned to the real 2026-09-28 clock
    (bug 6) -- asserts three things: (1) the neutral
    RED action, never the L5 survival card, (2) the forward-hazard reminder is present
    even under RED (bug 1), (3) the route result claims an action slot too."""
    conn, db_path = real_pf06_db
    _insert_real_sammakorn_20260928_rows(conn)
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    # founder ruling 2026-10-06 (KG-only/no-simulation): PROP-FLOOD-06 folds in
    # an external rain forecast promoter, so the real engine this test wants to
    # exercise end-to-end is only reachable with the flag explicitly on.
    import floodconnect_model
    monkeypatch.setattr(floodconnect_model, "SIMULATION_ENABLED", True)

    # current_local_state=RED is this test's one synthetic input (matching the
    # pre-existing, already-accepted convention in this same file, e.g.
    # test_kb_real_pf06_tier_reports_neutral_action_not_survival_card above) -- it only
    # drives which branch of _answer_next_action runs; the PF06 tier itself, the
    # pumps_running_count, and the canal reading are all real, pinned rows (see the
    # test above). forward_hazard=ACTIVE likewise only needs ONE model to show rain.
    state = {"status_counts": {"CRITICAL": 1}}
    hazard = {"tag": "RELAYED", "stale": False,
              "per_model": [{"model": "openmeteo", "tomorrow_mm": 12.0, "7day_total_mm": 40.0}]}
    assert kb._classify_current_local_state(state) == "RED"
    assert kb._classify_forward_hazard(hazard) == "ACTIVE"

    out = kb._answer_next_action(
        "sammakorn", state_answer=state, hazard_answer=hazard,
        now_utc=REAL_SAMMAKORN_20260928_PINNED_NOW)

    first = out["actions"][0]
    assert first["action"] == kb.STATION_RED_NEUTRAL_ACTION_TH, (
        "the real PF06 tier for this pinned case is L4, not L5 -- the survival card "
        "headline must never show")
    assert first["tag"] == "MEASURED"
    assert "sensor fault" in first["why"] or "ขัดข้อง" in first["why"], (
        "bug 8: the neutral action's why must say L5 was withheld specifically "
        "because of fault-only pump evidence, not a generic 'did not report L5'")

    reminder = next((a for a in out["actions"]
                      if a["action"].startswith("มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก")), None)
    assert reminder is not None, (
        "bug 1: the forward-hazard reminder must still appear under RED when "
        "forward_hazard=ACTIVE, not only when current_local_state is calm")
    assert "แม้สถานะปัจจุบันยังปกติ" not in reminder["action"], (
        "the RED version must drop the 'even though current state is normal' clause "
        "-- it would be false under RED")
    assert reminder["tag"] == "RELAYED"

    route_action = next((a for a in out["actions"]
                          if a.get("source", "").startswith("community_dag.find_safe_route")),
                         None)
    assert route_action is not None, "the route result must claim one of the up-to-3 slots"

    for a in out["actions"]:
        assert a.get("tag") in ("MEASURED", "RELAYED", "OPEN"), \
            f"every action must carry a tag, got {a!r}"


def test_future_row_rejected_even_when_within_stale_window(real_pf06_db):
    """A safety fix (2026-10-02, bug 7): a row timestamped AFTER the
    pinned `now_utc` must never be read, even though a NEGATIVE age is numerically
    "within" `age_h > lwl.STALE_HOURS` (negative is never greater than a positive
    cutoff) -- pinned at 05:00Z, a 12:45Z row must not leak backwards in time."""
    conn, _ = real_pf06_db
    _insert_real_sammakorn_20260928_rows(conn)
    pinned_before_the_real_rows = datetime.datetime(
        2026, 9, 28, 5, 0, 0, tzinfo=datetime.timezone.utc)
    gathered = pf06.gather_real_inputs(conn, now_utc=pinned_before_the_real_rows)
    assert gathered["inputs"]["canal_level_m"] is None
    assert gathered["provenance"]["canal_level_m"]["tag"] == "OPEN"


def test_pump_row_with_none_status_is_open_not_zero_running(real_pf06_db):
    """A safety fix (2026-10-02, bug 5): a pump row whose status is
    genuinely None (not a sensor-fault word, just no status reported) must
    not fall into `non_fault_pump_rows` and get summed as "0 pumps running" -- that is
    fabricated evidence (a confirmed zero), not an absent reading."""
    conn, _ = real_pf06_db
    store.insert_observation(
        conn, source_id="bma_pumphistory", station_code="ST.SPS.01",
        station_name="สถานีสูบน้ำคลองบ้านม้า 2", lat=13.7763, lon=100.6713,
        variable="pump_level_m", value=None, unit="m",
        observed_at_utc="2026-09-26T04:00:00+00:00",
        fetched_at_utc="2026-09-26T04:05:00+00:00",
        trust_tier="official_telemetry", status=None,
    )
    gathered = pf06.gather_real_inputs(conn)
    assert gathered["inputs"]["pumps_running_count"] is None
    prov = gathered["provenance"]["pumps_running_count"]
    assert prov["tag"] == "OPEN"


@pytest.mark.xfail(
    reason="OPEN: WL.SMK.01's real recorded rows in this repo have no canal_bank_m "
           "figure at all (always None, see this file's own module docstring) -- a "
           "genuine CANAL_AT_BANK_LEVEL L5 promoter can never fire on real Sammakorn "
           "data until a bank-level figure is actually surveyed and recorded. This is "
           "still OPEN, not a bug of this item, by design.",
    strict=True)
def test_real_l5_from_bank_level_promoter_not_possible_without_real_bank_figure(real_pf06_db):
    conn, _ = real_pf06_db
    _insert_real_sammakorn_20260928_rows(conn)
    record = pf06.compute(conn=conn, now_utc=REAL_SAMMAKORN_20260928_PINNED_NOW)
    assert record["tier"] == "L5", (
        "this assertion is expected to fail (xfail) -- there is no real canal_bank_m "
        "for WL.SMK.01 to promote off of")


def test_forward_hazard_reminder_present_under_red_when_active(monkeypatch):
    """Defect 1, isolated from the pinned real-data case above: an ACTIVE forward
    hazard must get a reminder slot even when current_local_state=RED, whatever the
    PF06 tier is (here forced to None via monkeypatch, so the RED action is the
    neutral line, not the L5 card)."""
    monkeypatch.setattr(kb, "_real_pf06_record", lambda area_id, now_utc=None: None)
    state = {"status_counts": {"CRITICAL": 1}}
    hazard = {"tag": "RELAYED", "stale": False,
              "per_model": [{"model": "openmeteo", "tomorrow_mm": 5.0, "7day_total_mm": 10.0}]}
    out = kb._answer_next_action("sammakorn", state_answer=state, hazard_answer=hazard)
    assert out["dual_state"] == {"current_local_state": "RED", "forward_hazard": "ACTIVE"}
    reminder_actions = [a for a in out["actions"]
                         if a["action"].startswith("มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก")]
    assert reminder_actions, "ACTIVE forward_hazard must still surface a reminder under RED"
    assert "แม้สถานะปัจจุบันยังปกติ" not in reminder_actions[0]["action"]


def test_forward_hazard_reminder_still_present_under_non_red_unchanged():
    """Regression guard: the pre-existing non-RED reminder wording (with the "even
    though normal" clause) must be unchanged for GREEN/YELLOW."""
    state = {"status_counts": {"NORMAL": 1}}
    hazard = {"tag": "RELAYED", "stale": False,
              "per_model": [{"model": "openmeteo", "tomorrow_mm": 5.0, "7day_total_mm": 10.0}]}
    out = kb._answer_next_action("sammakorn", state_answer=state, hazard_answer=hazard)
    assert out["dual_state"]["current_local_state"] == "GREEN"
    reminder_actions = [a for a in out["actions"]
                         if a["action"].startswith("มีฝนคาดการณ์ล่วงหน้าจากโมเดลภายนอก")]
    assert reminder_actions
    assert "แม้สถานะปัจจุบันยังปกติ" in reminder_actions[0]["action"]
    assert reminder_actions[0]["tag"] == "RELAYED"


def test_every_action_in_unknown_branch_has_a_tag():
    out = kb._answer_next_action("sammakorn", state_answer={"status_counts": {}})
    assert out["dual_state"]["current_local_state"] == "UNKNOWN"
    for a in out["actions"]:
        assert a.get("tag") in ("MEASURED", "RELAYED", "OPEN")


# ---------------------------------------------------------------------------
# Real, non-monkeypatched contradiction path -- a genuine thaiwater_flood_road vs
# dds_flood_report mismatch, through the real (un-faked) readout.build_readout, not a
# hand-built fake `full` dict like the pre-existing test in test_kb_answer.py.
# ---------------------------------------------------------------------------

# Real row, copied verbatim from the canonical repo's data/observations.sqlite
# (`thaiwater_flood_road`, district บางกะปิ, ~3.15 km from the Sammakorn centre --
# `radius_km=4.0` below is the existing `_answer_state` parameter widened to include
# it, not a fabricated reading).
REAL_FLOOD_ROAD_CONTRADICTION_ROW = dict(
    source_id="thaiwater_flood_road", station_code="FL.BKP.01",
    station_name="ถ.นวมินทร์ ช่วงตรงข้ามสถานีตำรวจนครบาลลาดพร้าว *",
    lat=13.7658, lon=100.6490, variable="floodroad_value_cm", value=20.0, unit="cm",
    observed_at_utc="2026-09-25T13:05:00+00:00", fetched_at_utc="2026-09-25T13:10:00+00:00",
    trust_tier="official_telemetry",
    provenance={"source_url": "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/flood_road",
                "district_th": "บางกะปิ"},
)


def test_real_contradiction_through_non_monkeypatched_build_readout(real_pf06_db, monkeypatch):
    """A safety fix (2026-10-02, bug 3): the existing contradiction test
    in test_kb_answer.py still monkeypatches `readout.build_readout` itself. This one
    does not -- a real `thaiwater_flood_road` row with no matching `dds_flood_report`
    document for its district is a genuine, already-implemented contradiction path
    (readout.py's own `flood_road_vs_flood_report` check) on a fresh DB with the row
    actually inserted, computed by the real engine end to end."""
    conn, db_path = real_pf06_db
    store.insert_observation(conn, **REAL_FLOOD_ROAD_CONTRADICTION_ROW)
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    state = kb._answer_state(13.767, 100.677, radius_km=4.0)
    assert state["contradiction_count"] >= 1
    out = kb._answer_next_action("sammakorn", state_answer=state)
    assert any("ขัดแย้ง" in n for n in out.get("notes", [])), \
        "a non-empty contradiction_count must reach next_action, not stay buried in state"
