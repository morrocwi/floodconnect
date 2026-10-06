"""Tests for kg_anchor in kb.py's build_answer (M4 acceptance A3). Reuses this
repo's own `real data only in tests` convention: the one inserted row below
is a real nationwide-telemetry row shape (station/value/status), with only
its timestamp computed relative to wall-clock `now` so the HIGH-confidence
scenario it drives does not silently rot as real time passes (same
convention `tests/test_token_budget.py`'s own `_near_sammakorn_rows` uses).

Run only this file while iterating:
    python3 -m pytest tests/test_kb_answer_kg_anchor.py -q
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
from tools.kg import accountability as acct  # noqa: E402

UTC = datetime.timezone.utc
SAMMAKORN_LAT = kb._ANSWER_AREAS["sammakorn"]["lat"]
SAMMAKORN_LON = kb._ANSWER_AREAS["sammakorn"]["lon"]
_NEAR_SAMMAKORN_LAT = SAMMAKORN_LAT + 0.01  # ~1.1 km -- within station-resolution radius


@pytest.fixture
def high_confidence_db(tmp_path, monkeypatch):
    """A fresh DB with one fresh, near-Sammakorn nationwide telemetry row, PLUS
    a matching fresh reading for the Jev Sandwich's own
    Z0 station at this point (`gauge:bma_watermap:WL.SMK.01`) -- `dual_state.
    confidence` is now the sandwich's own confidence (`kb._answer_next_action`'s
    docstring note), never the legacy nationwide-radius classifier alone, so a
    HIGH-confidence scenario for THIS test must give the sandwich a fresh Z0
    reading at/over its own critical level (`sandwich_decision`'s bottom-RED
    branch always returns confidence HIGH, regardless of what the top/middle
    ever show) -- the nationwide row alone (what this fixture used before this
    fix) no longer drives `dual_state.confidence` on its own."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    now = datetime.datetime.now(UTC)
    store.insert_observation(
        conn, source_id="thaiwater_waterlevel", station_code="NEAR.CONF.KGA",
        station_name="สถานีใกล้ (kg_anchor confidence test)",
        lat=_NEAR_SAMMAKORN_LAT, lon=SAMMAKORN_LON,
        variable="waterlevel_m", value=9.9, unit="m",
        observed_at_utc=now.isoformat(),
        fetched_at_utc=(now + datetime.timedelta(minutes=1)).isoformat(),
        trust_tier="official_telemetry", status="OVERBANK",
        provenance={"sub_basin_id": 777, "agency": "RID", "province_th": "กรุงเทพมหานคร"})
    store.insert_observation(
        conn, source_id="bma_watermap", station_code="WL.SMK.01",
        station_name="จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2",
        lat=13.76676, lon=100.67784, variable="canal_water_level_m", value=0.5, unit="m",
        observed_at_utc=now.isoformat(),
        fetched_at_utc=(now + datetime.timedelta(minutes=1)).isoformat(),
        warning=0.35, critical=0.44, bank=None, status="วิกฤต",
        trust_tier="official_telemetry")
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    monkeypatch.setattr(acct, "DB_PATH", db_path)
    return db_path


def _build_offline():
    return kb.build_answer("sammakorn", refresh=False)


def test_answer_has_kg_anchor_when_index_present():
    payload = _build_offline()
    assert "kg_anchor" in payload
    anchor = payload["kg_anchor"]
    assert anchor.get("method") in ("caller", "cand"), (
        f"expected a resolved anchor (output/kg_index/ is committed in this checkout), got {anchor}"
    )
    assert anchor.get("kg_sha256")


def test_payloads_identical_minus_generated_at_and_kg_anchor_when_index_missing(monkeypatch):
    real = _build_offline()
    monkeypatch.setattr(kb, "_kg_anchor", lambda lat, lon: {"tag": "OPEN", "method": "no_kg_index"})
    missing = _build_offline()
    for d in (real, missing):
        d.pop("generated_at", None)
        d.pop("kg_anchor", None)
    assert real == missing, "build_answer's other fields must not change when the KG index is unreadable"


def test_confidence_capped_low_when_index_missing_and_colours_unchanged(high_confidence_db, monkeypatch):
    real = _build_offline()
    assert real["next_action"]["dual_state"].get("confidence") == "HIGH", (
        "fixture setup check: expected a HIGH-confidence scenario before testing the cap"
    )
    monkeypatch.setattr(kb, "_kg_anchor", lambda lat, lon: {"tag": "OPEN", "method": "no_kg_index"})
    missing = _build_offline()
    assert missing["kg_anchor"] == {"tag": "OPEN", "method": "no_kg_index"}
    assert missing["next_action"]["dual_state"]["confidence"] == "LOW", (
        "dual_state.confidence must be capped to LOW when kg_anchor could not be built"
    )
    # Colours (current_local_state/forward_hazard) must be unaffected by the cap.
    assert (missing["next_action"]["dual_state"]["current_local_state"]
            == real["next_action"]["dual_state"]["current_local_state"])
    assert (missing["next_action"]["dual_state"]["forward_hazard"]
            == real["next_action"]["dual_state"]["forward_hazard"])
    # state.resolution_confidence is a DIFFERENT field and is left untouched by the cap.
    assert missing["state"].get("resolution_confidence") == real["state"].get("resolution_confidence")


def test_outside_thailand_answer_kg_anchor_tag_is_open():
    payload = kb.build_answer("999.0,999.0", refresh=False)
    assert payload["kg_anchor"] == {"tag": "OPEN", "method": "outside_thailand"}
