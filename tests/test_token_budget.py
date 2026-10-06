"""tests/test_token_budget.py -- AI.md + skills/floodconnect/SKILL.md + the `kb.py
answer` JSON must together stay inside this design's own 5,000-token ceiling
(tiktoken cl100k_base, same encoding the earlier manual measurements used).

This sum was once measured at 6,006 tokens (over the ceiling) before this test
existed, and the design had no test enforcing its own stated budget at all -- only ad
hoc manual re-measurements recorded in CONVERGE_LEDGER.yaml (internal, not read by
anyone outside this team).

Token-budget fix (2026-10-03): two gaps in the offline-only version of this test
remained open --

1. `_forecast_rows_by_model`/`_answer_accountability`'s `_latest_pump_state` both read
   their OWN module-level `DB_PATH` (`kb.DB_PATH` and
   `tools.kg.accountability.DB_PATH`, two separate module attributes pointing at the
   same default path) -- the old test only patched `kb.DB_PATH`, so a worktree that
   happened to have a real, large `data/observations.sqlite` on disk still had
   `accountability.DB_PATH` read that real file underneath the "offline" case. Both are
   patched below.
2. The "fresh clone, no DB" scenario is the right floor, but it is not the only real
   condition this budget has to hold under -- a `--refresh`'d installation ends up with
   a populated DB, and `readout.py`'s own overall-picture note names every DB-wide
   `source_id` by name (not just the ones near this area/radius), which grows without
   bound as more sources get wired. `test_answer_stays_under_budget_on_a_populated_db`
   below reproduces that with a SMALL real fixture DB (26 real rows, one per real
   `source_id`, copied verbatim from a real collection run recorded in this repo's own
   `data/observations.sqlite` on 2026-10-02 -- never simulated, per this workspace's
   "real data only in tests" rule), not the full ~22MB/175MB DB this worktree/production
   actually carries.

Token-budget fix: the fixture above had no row within the
3 km radius `_answer_state` actually queries around Sammakorn, so its answer never
exercised the notes (status counts, STALE count, contradiction notices) that overflow on
a real populated DB -- `_near_sammakorn_rows` + `REAL_CONTRADICTION_ROWS` below add real
drainage/canal rows that ARE in scope: a real STALE row (station WL.SSB.08, two agencies'
own readings at two different times) and a real cross-source contradiction
`readout.build_readout` already flags against this repo's own `data/observations.sqlite`
today (`dds_daily_pdf` vs `thaiwater_canal_waterlevel` naming the same canal gate 0.05 m
apart). The near-Sammakorn rows' `observed_at_utc` is computed relative to `now_utc`
rather than copied verbatim -- same convention `tests/test_safety_fix_2026-10-02.py`
already uses for STALE/fresh fixtures -- so the STALE/fresh split this test depends on
does not silently flip as real wall-clock time passes; every other field (station code/
name/coordinates/value/warning/critical/bank/status/trust_tier) is copied verbatim from
this repo's own `data/observations.sqlite`, never simulated.

`kb._answer_state`'s own fix (`_sources_summary_note` + the `status_counts_all`/
`stale_count` fields) is what keeps the populated-DB case under `TOKEN_BUDGET` at all --
before it, the real 175 MB/22 MB production DBs measured 5,514-5,781 tokens, over the
5,000 ceiling. `_check_budget` below still hard-asserts the real `TOKEN_BUDGET` ceiling,
but also raises a `UserWarning` ("soft assert" at a 300-token margin) whenever a
result is within `MARGIN_TOKENS` of it, so a small future AI.md/SKILL.md/answer-shape
change surfaces as a visible warning well before it actually breaks the ceiling.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

tiktoken = pytest.importorskip("tiktoken")

import kb  # noqa: E402
import store  # noqa: E402
from tools.kg import accountability as acct  # noqa: E402

TOKEN_BUDGET = 5000
# The fresh-clone floor used to pass by only 25
# tokens, so any small AI.md/SKILL.md wording edit could silently break the real
# ceiling with no advance warning. `_check_budget` below warns (never fails the test)
# once a result comes within this many tokens of TOKEN_BUDGET.
MARGIN_TOKENS = 300


def _check_budget(total: int, label: str) -> None:
    """Hard-asserts the real `TOKEN_BUDGET` ceiling; additionally raises a `UserWarning`
    (visible in pytest output, never a test failure on its own) once `total` is within
    `MARGIN_TOKENS` of it, so a shrinking margin is noticed long before it is a failure."""
    assert total <= TOKEN_BUDGET, (
        f"{label}: {total} tokens, over the {TOKEN_BUDGET}-token design ceiling")
    if total > TOKEN_BUDGET - MARGIN_TOKENS:
        warnings.warn(
            f"{label}: {total} tokens is within {TOKEN_BUDGET - total} of the "
            f"{TOKEN_BUDGET}-token ceiling (under the {MARGIN_TOKENS}-token safe "
            "margin) -- a small future wording change could break the real ceiling.")


def _tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def _ai_skill_tokens() -> tuple[int, int]:
    ai_md = (ROOT / "AI.md").read_text(encoding="utf-8")
    skill_md = (ROOT / "skills" / "floodconnect" / "SKILL.md").read_text(encoding="utf-8")
    return _tokens(ai_md), _tokens(skill_md)


def test_ai_md_skill_md_and_offline_answer_stay_under_token_budget(monkeypatch, tmp_path):
    """Fresh-clone floor: `data/observations.sqlite` does not exist yet (always
    gitignored, never shipped) -- both DB_PATH module attributes patched to a path that
    does not exist, so neither module can accidentally fall through to a real DB this
    worktree happens to have on disk."""
    missing_db = tmp_path / "does_not_exist.sqlite"
    monkeypatch.setattr(kb, "DB_PATH", missing_db)
    monkeypatch.setattr(acct, "DB_PATH", missing_db)
    payload = kb.build_answer("sammakorn", refresh=False)
    answer_json = json.dumps(payload, ensure_ascii=False, indent=2)

    ai_tok, skill_tok = _ai_skill_tokens()
    answer_tok = _tokens(answer_json)
    total = ai_tok + skill_tok + answer_tok

    _check_budget(total, f"AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + offline answer "
                          f"({answer_tok})")


def _fake_refresh_report_like_answer_sources() -> list[dict]:
    """A `_refresh_relevant_sources` report shaped like a real default `refresh=True`
    run (13 ANSWER_SOURCES + the hii_analyst_cctv carve-out -- see that constant's own
    docstring), never a tiny 1-row fake: this is exactly the shape
    measured at 2,216/2,259 tokens for sammakorn/ram53 before the fix."""
    ids = ["thaiwater_canal_waterlevel", "thaiwater_dam_release", "bma_watermap",
           "bma_dds_daily_pdf", "bma_dds_tide", "bma_dds_flood_report",
           "thaiwater_rain_gauge", "social_listening_facebook",
           "openmeteo_forecast7d", "metno_forecast7d", "pump_station_status",
           "flood_road_status", "hii_analyst_cctv"]
    return [{"id": sid, "ok": True, "skipped": False, "note": "simulated: measured run"}
            for sid in ids]


@pytest.mark.parametrize("area", ["sammakorn", "ram53"])
def test_default_refresh_answer_stays_under_token_budget(area, monkeypatch, tmp_path):
    """ the REAL default call is `refresh=True` (not the `refresh=False`
    floor above) -- MEASURED later at 5,365/5,408 tokens, over the
    5,000 ceiling, almost entirely from the uncompacted 13-entry refresh report. This
    reproduces that exact default path (refresh=True, verbose=False) with a
    realistically-sized refresh report and asserts the fix (`_compact_refresh_report`)
    keeps it inside budget."""
    missing_db = tmp_path / "does_not_exist.sqlite"
    monkeypatch.setattr(kb, "DB_PATH", missing_db)
    monkeypatch.setattr(acct, "DB_PATH", missing_db)
    monkeypatch.setattr(kb, "_refresh_relevant_sources",
                         lambda *a, **k: _fake_refresh_report_like_answer_sources())
    payload = kb.build_answer(area, refresh=True, verbose=False)
    assert isinstance(payload["refresh"], dict)  # compact form, never the raw list
    assert payload["refresh"]["total"] == 13
    answer_json = json.dumps(payload, ensure_ascii=False, indent=2)

    ai_tok, skill_tok = _ai_skill_tokens()
    answer_tok = _tokens(answer_json)
    total = ai_tok + skill_tok + answer_tok

    _check_budget(total, f"{area}: AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + default "
                          f"refresh=True answer ({answer_tok})")


# ---------------------------------------------------------------------------
# FIX C (2026-10-04) -- the F2 accountability-fallback + F8 CCTV realistic case,
# both MVP areas, with a lower ceiling to keep a real margin.
# ---------------------------------------------------------------------------

# The founder's own FIX C request tightened the design ceiling for THIS specific case
# (fallback accountability + 3 cameras, the two newest additions to the default answer)
# to 4,700 -- 300 tokens of margin below the repo-wide 5,000 `TOKEN_BUDGET`, not a
# separate/looser ceiling. `ram53` is always the larger of the two areas (longer
# `_ACCOUNTABILITY_FALLBACK` district label, longer `start_node`), so both are checked.
FIXC_TOKEN_BUDGET = 4700


def _insert_cctv_rows_for_budget_test(conn) -> None:
    """Same three real `hii_analyst_cctv` rows `tests/test_kb_answer.py::REAL_CCTV_ROWS`
    already uses (copied verbatim, never simulated, see that file's own comment for
    provenance) -- reused here rather than re-declared, so this fixture never drifts
    from the one other tests already exercise."""
    import tests.test_kb_answer as kb_answer_tests
    for station_id, title, agency_en, province_th, lat, lon, cctv_url in (
            kb_answer_tests.REAL_CCTV_ROWS):
        text = f"{station_id} | {title} | {agency_en} | {province_th} | {lat},{lon} | {cctv_url}"
        store.insert_document(
            conn, source_id="hii_analyst_cctv", fetched_at_utc="2026-10-03T12:00:00+00:00",
            section="cctv_station", text=text,
        )


@pytest.mark.parametrize("area", ["sammakorn", "ram53"])
def test_fallback_accountability_plus_cctv_stays_under_tightened_budget(
        area, monkeypatch, tmp_path):
    """FIX C's own realistic fixture: a fresh-clone DB (no `output/*.graphml`, so
    `_answer_accountability` takes the FIX C fallback path, tag=INSTINCT) that ALSO has
    the real `hii_analyst_cctv` catalog rows (so `cctv.cameras` is non-empty, 3 real
    cameras) -- the two conditions a later re-check found missing from every
    existing budget test. Checked for BOTH MVP areas (the prior measurement only ever
    covered sammakorn), against the tightened 4,700-token ceiling with its own margin,
    not only the repo-wide 5,000."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    _insert_cctv_rows_for_budget_test(conn)
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    monkeypatch.setattr(acct, "DB_PATH", db_path)

    payload = kb.build_answer(area, refresh=False)
    # Confirms the fixture actually exercises what this test is named for -- a silent
    # regression in either the fallback or the CCTV wiring must fail here, not just
    # quietly inflate/shrink the token count this test otherwise only checks.
    assert payload["accountability"]["tag"] == "INSTINCT", (
        f"{area}: accountability fallback did not fire on a fresh (no-graph) clone -- "
        "this fixture no longer exercises the F2 fix this test is named for")
    assert payload["accountability"]["basis"] == "governance_dag_fallback"
    assert not any(
        agency.startswith("AG_") for agency in payload["accountability"]["owner_agencies"]
    ), (f"{area}: compact owner_agencies still leaks an internal registry id "
        f"({payload['accountability']['owner_agencies']!r}) -- F2 fix requires "
        "human-readable Thai agency names only in the default (non-verbose) answer")
    assert len(payload.get("cctv", {}).get("cameras", [])) == 3, (
        f"{area}: fixture must surface all 3 real CCTV rows -- this test is named for "
        "the fallback+3-cameras case a later re-check found untested")

    answer_json = json.dumps(payload, ensure_ascii=False, indent=2)
    ai_tok, skill_tok = _ai_skill_tokens()
    answer_tok = _tokens(answer_json)
    total = ai_tok + skill_tok + answer_tok

    assert total <= FIXC_TOKEN_BUDGET, (
        f"{area}: AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + fallback+3-camera answer "
        f"({answer_tok}) = {total} tokens, over FIX C's {FIXC_TOKEN_BUDGET}-token "
        "ceiling (kept below the repo-wide 5,000 for margin)")
    # Also covered by the repo-wide ceiling, with its own soft-margin warning.
    _check_budget(total, f"{area}: AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + "
                          f"fallback+3-camera answer ({answer_tok})")


# ---------------------------------------------------------------------------
# Populated-DB case -- small REAL fixture, many distinct source_ids
# ---------------------------------------------------------------------------

# One real row per real source_id, copied verbatim (every field) from this repo's own
# `data/observations.sqlite` as collected on 2026-10-02 -- 26 distinct source_ids,
# matching the shape of a real `--refresh`'d installation (a real measurement on the real
# 175MB DB's `sources_used` at a similar count). Never simulated.
REAL_POPULATED_ROWS = [
    {'source_id': 'bma_watermap', 'station_code': 'WL.KKD.04', 'station_name': 'จุดวัดคลองเคล็ด ตอนซอยเปรมฤทัย 20*', 'lat': 13.68033, 'lon': 100.63959, 'variable': 'canal_water_level_m', 'value': -0.47, 'unit': 'm', 'observed_at_utc': '2026-10-02T12:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:42:14.804970+00:00', 'warning': 0.5, 'critical': 1.0, 'bank': None, 'status': 'ขัดข้องชั่วคราว', 'trust_tier': 'official_telemetry'},
    {'source_id': 'dds_daily_pdf', 'station_code': 'NAVY_HYDRO', 'station_name': 'ขึ้นเต็มที่', 'lat': None, 'lon': None, 'variable': 'tide_ขึ้นเต็มที่_am_m', 'value': 1.07, 'unit': 'm', 'observed_at_utc': '2026-10-02T00:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:40:30.593164+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_report'},
    {'source_id': 'dds_tide_pdf', 'station_code': 'NAVY_HYDRO_HQ', 'station_name': 'กองบัญชาการกองทัพเรือ', 'lat': None, 'lon': None, 'variable': 'tide_hw_pm_level_m', 'value': 0.42, 'unit': 'm', 'observed_at_utc': '2026-12-31T16:40:00+00:00', 'fetched_at_utc': '2026-10-02T11:40:34.078842+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_report'},
    {'source_id': 'egat_water_crisis', 'station_code': 'dam:egat_water_crisis:จุฬาภรณ์', 'station_name': 'จุฬาภรณ์', 'lat': None, 'lon': None, 'variable': 'egat_dam_inflow_mcm', 'value': 1.19, 'unit': 'MCM/day', 'observed_at_utc': '2026-10-02T11:42:50.792146+00:00', 'fetched_at_utc': '2026-10-02T11:42:50.792146+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_report'},
    {'source_id': 'hii_dam', 'station_code': 'dam:hii_dam:44', 'station_name': 'สิรินธร', 'lat': 15.202778, 'lon': 105.432222, 'variable': 'dam_hourly_inflow_mcm', 'value': 0.05, 'unit': 'MCM/day', 'observed_at_utc': '2026-10-02T10:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:40:48.620296+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_telemetry'},
    {'source_id': 'hii_watergate', 'station_code': 'gate:hii_watergate:1117429', 'station_name': 'ฝายพับได้หนองเล็งทราย', 'lat': 19.350946, 'lon': 99.82508, 'variable': 'watergate_upstream_level_m', 'value': None, 'unit': 'm', 'observed_at_utc': '2026-10-02T11:30:00+00:00', 'fetched_at_utc': '2026-10-02T11:41:04.512818+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_telemetry'},
    {'source_id': 'hii_waterlevel_load', 'station_code': 'AIT001', 'station_name': 'อโศก', 'lat': 13.74325, 'lon': 100.562164, 'variable': 'waterlevel_msl', 'value': 1.29, 'unit': 'm', 'observed_at_utc': '2026-10-02T11:30:00+00:00', 'fetched_at_utc': '2026-10-02T11:44:01.596665+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_telemetry'},
    {'source_id': 'metno_locationforecast', 'station_code': 'bangkok_east:metno', 'station_name': 'bangkok_east:metno', 'lat': 13.7734, 'lon': 100.6813, 'variable': 'precipitation_forecast_daily_mm', 'value': 18.5, 'unit': 'mm', 'observed_at_utc': '2026-10-10T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:43:53.717142+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'nasa_power', 'station_code': 'sammakorn', 'station_name': 'sammakorn', 'lat': 13.758235, 'lon': 100.676084, 'variable': 'rain_24h_mm', 'value': 3.43, 'unit': 'mm', 'observed_at_utc': '2026-09-28T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:43:01.745079+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'noaa_oni', 'station_code': 'oni_pacific', 'station_name': 'ONI (Nino 3.4 region)', 'lat': None, 'lon': None, 'variable': 'oni', 'value': 1.8, 'unit': 'degC_anomaly', 'observed_at_utc': '2026-10-02T11:45:19.880629+00:00', 'fetched_at_utc': '2026-10-02T11:45:19.880629+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_report'},
    {'source_id': 'openmeteo_archive_precip', 'station_code': 'bangkok_east', 'station_name': 'bangkok_east', 'lat': 13.7734, 'lon': 100.6813, 'variable': 'precipitation_sum_daily_mm', 'value': 1.8, 'unit': 'mm', 'observed_at_utc': '2026-09-30T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:44:13.970144+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_ensemble', 'station_code': 'nakhonsawan', 'station_name': 'nakhonsawan', 'lat': 15.7047, 'lon': 100.1372, 'variable': 'precipitation_ensemble_median_mm', 'value': 0.0, 'unit': 'mm', 'observed_at_utc': '2026-10-04T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:42:58.875181+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_ensemble_daily', 'station_code': 'bangkok_east:gfs_ensemble_median', 'station_name': 'bangkok_east:gfs_ensemble_median', 'lat': 13.7734, 'lon': 100.6813, 'variable': 'precipitation_forecast_ensemble_daily_mm', 'value': 5.0, 'unit': 'mm', 'observed_at_utc': '2026-10-16T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:43:30.825127+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_flood', 'station_code': 'bang_sai', 'station_name': 'bang_sai', 'lat': 14.35, 'lon': 100.55, 'variable': 'glofas_river_discharge_m3s', 'value': 0.01, 'unit': 'm3/s', 'observed_at_utc': '2026-12-31T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:42:56.007042+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_forecast', 'station_code': 'ram53', 'station_name': 'ram53', 'lat': 13.76554, 'lon': 100.619095, 'variable': 'precipitation_forecast_mm', 'value': 2.4, 'unit': 'mm', 'observed_at_utc': '2026-10-06T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:39:36.842975+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_forecast16d', 'station_code': 'bangkok_east:gfs_seamless', 'station_name': 'bangkok_east:gfs_seamless', 'lat': 13.7734, 'lon': 100.6813, 'variable': 'precipitation_forecast_daily_mm', 'value': 18.7, 'unit': 'mm', 'observed_at_utc': '2026-10-16T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:43:15.247829+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_marine', 'station_code': 'gulf_of_thailand_bar', 'station_name': 'gulf_of_thailand_bar', 'lat': 13.458336, 'lon': 100.625015, 'variable': 'sea_level_height_msl_m', 'value': 0.58, 'unit': 'm', 'observed_at_utc': '2026-10-08T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:43:00.114145+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_multimodel', 'station_code': 'ecmwf_ifs025', 'station_name': 'ecmwf_ifs025', 'lat': 13.758235, 'lon': 100.676084, 'variable': 'precipitation_forecast_mm', 'value': 0.0, 'unit': 'mm', 'observed_at_utc': '2026-10-08T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:43:02.687758+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_pressure', 'station_code': 'bangkok_east:gfs_seamless', 'station_name': 'bangkok_east:gfs_seamless', 'lat': 13.7734, 'lon': 100.6813, 'variable': 'pressure_msl', 'value': 1011.1, 'unit': 'hPa', 'observed_at_utc': '2026-10-17T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:44:55.509017+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_previous_runs', 'station_code': 'sammakorn:gfs_seamless_currentbest', 'station_name': 'sammakorn:gfs_seamless_currentbest', 'lat': 13.758235, 'lon': 100.676084, 'variable': 'precipitation_skillcheck_daily_mm', 'value': 2.2, 'unit': 'mm', 'observed_at_utc': '2026-10-01T17:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:44:01.240193+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_soil_moisture', 'station_code': 'bangkok_east', 'station_name': 'bangkok_east', 'lat': 13.7734, 'lon': 100.6813, 'variable': 'soil_moisture_0_1cm', 'value': 0.449, 'unit': 'm3/m3', 'observed_at_utc': '2026-10-04T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:44:09.031288+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'openmeteo_sst', 'station_code': 'andaman_sea', 'station_name': 'andaman_sea', 'lat': 9.0, 'lon': 97.5, 'variable': 'sea_surface_temperature', 'value': 29.6, 'unit': 'degC', 'observed_at_utc': '2026-10-04T16:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:45:14.742933+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'},
    {'source_id': 'thaiwater_canal_waterlevel', 'station_code': 'WL.KPM.04', 'station_name': 'ค.เปรมประชากร-ค.บางตลาด*', 'lat': 13.87546, 'lon': 100.57424, 'variable': 'canal_water_level_m', 'value': 1.56, 'unit': 'm', 'observed_at_utc': '2026-09-28T06:30:00+00:00', 'fetched_at_utc': '2026-10-02T11:39:47.180416+00:00', 'warning': 0.6, 'critical': 0.7, 'bank': 2.0, 'status': 'CRITICAL', 'trust_tier': 'official_telemetry'},
    {'source_id': 'thaiwater_flood_road', 'station_code': 'FL.BBN.01', 'station_name': 'ถ.เอกชัย ช่วงห้างบิ๊กซีบางบอน', 'lat': 13.67942, 'lon': 100.43563, 'variable': 'floodroad_value_cm', 'value': 0.0, 'unit': 'cm', 'observed_at_utc': '2026-09-28T06:25:00+00:00', 'fetched_at_utc': '2026-10-02T11:39:49.045462+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_telemetry'},
    {'source_id': 'thaiwater_rain_24h', 'station_code': '1', 'station_name': 'คลองลาดพร้าว วัดบางบัว', 'lat': 13.85402, 'lon': 100.58746, 'variable': 'rain_1h_mm', 'value': 0.0, 'unit': 'mm', 'observed_at_utc': '2026-10-02T11:00:00+00:00', 'fetched_at_utc': '2026-10-02T11:39:51.571673+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_telemetry'},
    {'source_id': 'thaiwater_waterlevel', 'station_code': 'AIT001', 'station_name': 'อโศก', 'lat': 13.74325, 'lon': 100.562164, 'variable': 'waterlevel_msl', 'value': 1.29, 'unit': 'm', 'observed_at_utc': '2026-10-02T11:30:00+00:00', 'fetched_at_utc': '2026-10-02T11:41:59.035620+00:00', 'warning': None, 'critical': None, 'bank': None, 'status': None, 'trust_tier': 'official_telemetry'},
]


# A real cross-source contradiction `readout.build_readout` already flags on this
# repo's own `data/observations.sqlite` (checked by actually running `build_readout`
# against it on 2026-10-03, MEASURED: 1 contradiction, topic
# `canal_level_same_name_candidate`) -- `dds_daily_pdf`'s daily bulletin (id 8157) and
# `thaiwater_canal_waterlevel` (id 415) name the exact same canal gate
# ("ปตร.คลองประเวศฯ-ลาดกระบัง") 0.05 m apart. Copied verbatim, including both real
# dates -- the contradiction detector compares raw `observed_at_utc` values DB-wide, not
# radius- or staleness-filtered, so these never need the dynamic timestamp
# `_near_sammakorn_rows` below uses.
REAL_CONTRADICTION_ROWS = [
    {'source_id': 'thaiwater_canal_waterlevel', 'station_code': 'WL.PWT.04',
     'station_name': 'ปตร.คลองประเวศฯ-ลาดกระบัง', 'lat': 13.72411, 'lon': 100.74987,
     'variable': 'canal_water_level_m', 'value': 0.82, 'unit': 'm',
     'observed_at_utc': '2026-09-28T06:20:00+00:00',
     'fetched_at_utc': '2026-10-02T11:39:47.180416+00:00', 'warning': 0.4,
     'critical': 0.6, 'bank': 1.98, 'status': 'CRITICAL', 'trust_tier': 'official_telemetry'},
    {'source_id': 'dds_daily_pdf', 'station_code': None,
     'station_name': 'ปตร.คลองประเวศฯ-ลาดกระบัง', 'lat': None, 'lon': None,
     'variable': 'canal_level_0700_m', 'value': 0.87, 'unit': 'm',
     'observed_at_utc': '2026-10-02T00:00:00+00:00',
     'fetched_at_utc': '2026-10-02T11:40:30.593164+00:00', 'warning': None,
     'critical': 0.35, 'bank': None, 'status': 'ระดับน้ำวิกฤติ',
     'trust_tier': 'official_report'},
]


def _near_sammakorn_rows(now_utc: "datetime.datetime | None" = None) -> list[dict]:
    """Real drainage/canal stations within 3 km of Sammakorn (13.758235, 100.676084) --
    the radius `_answer_state` actually queries. None of `REAL_POPULATED_ROWS` above lie
    in range, so that fixture alone never exercised the status/STALE
    note that overflows on a real populated DB. Every field except `observed_at_utc` is
    copied verbatim from this repo's own `data/observations.sqlite` (ids
    9528/9580/9614/24705/24733/24734/331, collected 2026-10-02) -- station code, name,
    coordinates, value, warning/critical/bank thresholds, the owning agency's own status
    word, and trust_tier are all real, never simulated.

    `observed_at_utc` is computed relative to `now_utc` (real `now` when unset) instead
    of copied verbatim, the same convention `tests/test_safety_fix_2026-10-02.py` already
    uses for STALE/fresh fixtures, so this test's STALE/fresh split does not silently
    flip as wall-clock time moves on. The two WL.SSB.08 rows below (one fresh from
    `bma_watermap`, one aged past the STALE cutoff from `thaiwater_canal_waterlevel`) are
    the real same-station reading two different agencies published at different times
    for this case -- `readout.py` has no same-station-code contradiction detector today
    (only the name-matched `dds_daily_pdf`-vs-`thaiwater_canal_waterlevel` pairing
    `REAL_CONTRADICTION_ROWS` above reproduces), so this pair's job here is only to
    supply a real STALE row, not a second contradiction."""
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    fresh_at = (now_utc - datetime.timedelta(hours=1)).isoformat()
    stale_at = (now_utc - datetime.timedelta(hours=40)).isoformat()
    fetched_at = now_utc.isoformat()
    return [
        {'source_id': 'bma_watermap', 'station_code': 'WL.SMK.01',
         'station_name': 'จุดวัดบึงรับน้ำหมู่บ้านสัมมากร ตอนสถานีสูบน้ำบึงที่ 2 คลองบ้านม้า 2',
         'lat': 13.76676, 'lon': 100.67784, 'variable': 'canal_water_level_m',
         'value': 0.13, 'unit': 'm', 'observed_at_utc': fresh_at,
         'fetched_at_utc': fetched_at, 'warning': 0.35, 'critical': 0.44, 'bank': None,
         'status': 'ปกติ', 'trust_tier': 'official_telemetry'},
        {'source_id': 'bma_watermap', 'station_code': 'WL.BMA.02',
         'station_name': 'จุดวัดคลองบ้านม้า ตอนถนนรามคำแหง', 'lat': 13.77281,
         'lon': 100.66569, 'variable': 'canal_water_level_m', 'value': 0.28, 'unit': 'm',
         'observed_at_utc': fresh_at, 'fetched_at_utc': fetched_at, 'warning': 2.14,
         'critical': 2.68, 'bank': None, 'status': 'ปกติ', 'trust_tier': 'official_telemetry'},
        {'source_id': 'bma_watermap', 'station_code': 'WL.HMK.02',
         'station_name': 'จุดวัดคลองหัวหมาก ตอนซอยรามคาแหง 68', 'lat': 13.76438,
         'lon': 100.65679, 'variable': 'canal_water_level_m', 'value': 0.13, 'unit': 'm',
         'observed_at_utc': fresh_at, 'fetched_at_utc': fetched_at, 'warning': 0.68,
         'critical': 0.79, 'bank': None, 'status': 'ปกติ', 'trust_tier': 'official_telemetry'},
        {'source_id': 'bma_watermap', 'station_code': 'WL.SSB.08',
         'station_name': 'จุดวัดคลองแสนแสบ ช่วงซอยเสรีไทย 24', 'lat': 13.7805,
         'lon': 100.67387, 'variable': 'canal_water_level_m', 'value': 0.6, 'unit': 'm',
         'observed_at_utc': fresh_at, 'fetched_at_utc': fetched_at, 'warning': 0.35,
         'critical': 0.45, 'bank': None, 'status': 'วิกฤต', 'trust_tier': 'official_telemetry'},
        {'source_id': 'thaiwater_canal_waterlevel', 'station_code': 'WL.SSB.08',
         'station_name': 'ค.แสนแสบ-เสรีไทย 24', 'lat': 13.7805, 'lon': 100.67387,
         'variable': 'canal_water_level_m', 'value': 0.8, 'unit': 'm',
         'observed_at_utc': stale_at, 'fetched_at_utc': fetched_at, 'warning': 0.35,
         'critical': 0.45, 'bank': 1.91, 'status': 'CRITICAL',
         'trust_tier': 'official_telemetry'},
    ]


# The real DDS daily bulletin (dds_daily_pdf, latest fetch 2026-10-03T05:52:44Z,
# re-queried against this repo's own data/observations.sqlite) -- 10 canal rows city-
# wide, 3 of them 'ระดับน้ำวิกฤติ' (critical). Update (2026-10-04): the comment
# that used to be here claimed this was "the ACTUAL cause of a real RED/ACTIVE answer"
# -- it was, but only via the exact bug this fix fixes (readout.py never radius-filtered
# this source AND never distinguished `canal_outer` from `canal_inner`): all 3 critical
# rows below are `canal_outer` (ปตร.คลองประเวศฯ-ลาดกระบัง / ปตร.คลองสองสายใต้ /
# ปตร.คลองแสนแสบ-มีนบุรี, all 8-11 km from Sammakorn, measuring the outside-the-dike
# water level), so they correctly no longer decide anything for this centre (see
# `readout.py`'s `_DDS_GATE_COORDS`). Every row's `provenance={"section": ...}` below
# is added for this same reason -- without it every row defaulted to "not canal_outer"
# but still had no sourced coordinate either, so it would have stayed `used_for_decision
# =False` regardless; the explicit section tag keeps this fixture's `canal_outer`/
# `canal_inner` split matching the real bulletin's own two sections (see
# `_REAL_DDS_CANAL_ROWS_RAW`'s own per-row section below), not an assumption.
# station_name/value/warning/critical/status copied verbatim; observed_at_utc/
# fetched_at_utc computed relative to now_utc (same convention as
# `_near_sammakorn_rows`) so freshness never silently drifts with wall-clock time.
# 5th field: the real bulletin section each row actually came from (3. ระดับน้ำพื้นที่
# กทม. ภายนอกฯ = canal_outer, 4. ...ภายในฯ = canal_inner) -- see readout.py's own
# `_DDS_CANAL_OUTER_SECTION`/`_DDS_GATE_COORDS` comments for why this now matters.
_REAL_DDS_CANAL_ROWS_RAW = [
    ('คลองทวีวัฒนาตัดคลองภาษีเจริญ', 0.48, 0.7, 'ระดับน้ำปกติ', 'canal_inner'),
    ('คลองลาดพร้าว 56', 0.17, 0.4, 'ระดับน้ำปกติ', 'canal_inner'),
    ('คลองเปรมประชากร (ตอนคลองบ้านใหม่)', 0.81, 1.2, 'ระดับน้ำปกติ', 'canal_inner'),
    ('คลองแสนแสบ-คลองตัน (แสนแสบเก่า)', -0.43, 0.2, 'ระดับน้ำปกติ', 'canal_inner'),
    ('คลองแสนแสบ-เขตบางกะปิ', 0.21, 0.45, 'ระดับน้ำปกติ', 'canal_inner'),
    ('ปตร.คลองทวีวัฒนา (ด้านใน)', 0.65, 1.0, 'ระดับน้ำปกติ', 'canal_inner'),
    ('ปตร.คลองประเวศฯ-ลาดกระบัง (bulletin)', 0.82, 0.35, 'ระดับน้ำวิกฤติ', 'canal_outer'),
    ('ปตร.คลองมหาสวัสดิ์-ฉิมพลี (ด้านแม่น้ำ)', 0.86, 2.8, 'ระดับน้ำปกติ', 'canal_inner'),
    ('ปตร.คลองสองสายใต้', 1.91, 1.8, 'ระดับน้ำวิกฤติ', 'canal_outer'),
    ('ปตร.คลองแสนแสบ-มีนบุรี.80', 1.28, 0.7, 'ระดับน้ำวิกฤติ', 'canal_outer'),
]


def _real_dds_canal_rows(now_utc: "datetime.datetime | None" = None) -> list[dict]:
    """`fetched_at_utc` is pinned to the SAME value `REAL_CONTRADICTION_ROWS`' own
    dds_daily_pdf row already uses (not a dynamic `now_utc`) -- `readout.
    load_latest_dds_daily` keeps only the rows sharing the single MAX(fetched_at_utc)
    batch, so a later value here would silently drop that existing contradiction row
    out of the "latest batch" entirely (measured while building this fixture: it
    zeroed `contradiction_count`). `observed_at_utc` is still computed relative to
    `now_utc` (freshness is judged on THAT field, via `lwl.age_hours`, never
    `fetched_at_utc`), so these rows stay fresh/non-STALE regardless of wall-clock
    drift even though their batch timestamp is fixed."""
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    observed_at = (now_utc - datetime.timedelta(hours=1)).isoformat()
    fetched_at = "2026-10-02T11:40:30.593164+00:00"  # same batch as REAL_CONTRADICTION_ROWS
    return [
        {'source_id': 'dds_daily_pdf', 'station_code': None, 'station_name': name,
         'lat': None, 'lon': None, 'variable': 'canal_level_0700_m', 'value': value,
         'unit': 'm', 'observed_at_utc': observed_at, 'fetched_at_utc': fetched_at,
         'warning': None, 'critical': critical, 'bank': None, 'status': status,
         'trust_tier': 'official_report',
         'provenance': {'section': section, 'header_date_recognized': True}}
        for name, value, critical, status, section in _REAL_DDS_CANAL_ROWS_RAW
    ]


# The real `--refresh`'d forecast cache for Sammakorn (openmeteo_forecast16d/
# metno_locationforecast, each model's first future-dated `precipitation_forecast_
# daily_mm` row, copied verbatim from this repo's own data/observations.sqlite,
# collected 2026-10-02) -- the real 10 distinct models `_compact_hazard_for_display`
# actually caps today. `observed_at_utc` is computed relative to now_utc (LOCAL
# tomorrow) rather than copied verbatim, same convention as `_near_sammakorn_rows`,
# so this fixture's "tomorrow" never ages into the past as wall-clock time moves on.
_REAL_FORECAST_MODEL_ROWS_RAW = [
    ('openmeteo_forecast16d', 'cma_grapes_global', 6.6),
    ('openmeteo_forecast16d', 'ecmwf_ifs025', 2.3),
    ('openmeteo_forecast16d', 'gem_seamless', 18.3),
    ('openmeteo_forecast16d', 'gfs_seamless', 3.8),
    ('openmeteo_forecast16d', 'icon_seamless', 9.7),
    ('openmeteo_forecast16d', 'jma_seamless', 13.0),
    ('openmeteo_forecast16d', 'knmi_seamless', 2.0),
    ('openmeteo_forecast16d', 'meteofrance_seamless', 5.8),
    ('metno_locationforecast', 'metno', 0.6),
    ('openmeteo_forecast16d', 'ukmo_seamless', 7.3),
]


def _real_forecast_model_rows(
        point_id: str = "sammakorn",
        now_utc: "datetime.datetime | None" = None) -> list[dict]:
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    tomorrow = (now_utc + datetime.timedelta(days=1)).replace(
        hour=17, minute=0, second=0, microsecond=0).isoformat()
    fetched_at = now_utc.isoformat()
    return [
        {'source_id': source_id, 'station_code': f'{point_id}:{model}',
         'station_name': f'{point_id}:{model}', 'lat': None, 'lon': None,
         'variable': 'precipitation_forecast_daily_mm', 'value': value, 'unit': 'mm',
         'observed_at_utc': tomorrow, 'fetched_at_utc': fetched_at, 'warning': None,
         'critical': None, 'bank': None, 'status': None, 'trust_tier': 'third_party'}
        for source_id, model, value in _REAL_FORECAST_MODEL_ROWS_RAW
    ]


@pytest.fixture
def real_populated_db(tmp_path, monkeypatch):
    """A tiny sqlite DB built with `store.insert_observation` (the production insert
    path, not a hand-built row) from `REAL_POPULATED_ROWS` + `_near_sammakorn_rows()`
    + `_real_dds_canal_rows()` + `_real_forecast_model_rows()` -- 26 distinct real
    source_ids at the shape of a real `--refresh`'d installation, the real
    Sammakorn-radius drainage rows that drive `state.notes`' status/STALE/contradiction
    content, the real DDS bulletin rows that are what actually makes a real answer
    RED (an earlier measurement against the real database), and the real 10-model
    forecast cache that makes a
    real answer ACTIVE with a non-trivial `hazard.per_model`. Both `kb.DB_PATH` and
    `tools.kg.accountability.DB_PATH` are patched to it (the two
    modules each hold their own copy of this path)."""
    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    for row in (REAL_POPULATED_ROWS + REAL_CONTRADICTION_ROWS
                + _near_sammakorn_rows() + _real_dds_canal_rows()
                + _real_forecast_model_rows()):
        store.insert_observation(conn, **row)
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    monkeypatch.setattr(acct, "DB_PATH", db_path)
    return db_path


# The committed fixture's DEFAULT-mode answer used to pass the budget at 1,848 tokens
# while the REAL repo database's own default-mode answer measured 2,640/2,668 tokens
# (Sammakorn/Ram53, well over the 5,000-token total ceiling once AI.md+SKILL.md are
# added) -- the fixture was realistic in SHAPE (real rows, real STALE row, real
# contradiction) but not in SIZE, so this test's pass told nobody the real installation
# was actually over budget. `REALISTIC_FLOOR_TOKENS` fixes that: it is the VERBOSE
# (uncapped) answer's own floor, checked BEFORE any default-mode trimming runs,
# measured against the real repo's own real `data/observations.sqlite` (50,108
# rows/27 sources, fetched 2026-10-03T05:56Z) at 2,782-2,811 tokens verbose --
# comfortably above this floor, never simulated upward to clear it.
REALISTIC_FLOOR_TOKENS = 2600


def test_answer_stays_under_budget_on_a_populated_db(real_populated_db):
    """Token-budget check: against a DB with many distinct sources AND real
    status/STALE/contradiction rows within Sammakorn's radius (the shape a
    `--refresh`'d/real installation has), the default (non-verbose) answer must still
    fit the same budget `AI.md` promises for the fresh-clone case -- the structured
    `status_counts`/`status_counts_all`/`stale_count`/`contradiction_count` fields plus
    the capped `state.notes` source list (`kb._sources_summary_note`), the
    min/median/max `hazard.per_model` cap, and the `{field, epistemic_class}`-only
    `source_tags` are what keep this true; before those fixes this case alone pushed
    the total well over the ceiling, and the STALE/contradiction notes plus the
    10-model hazard breakdown were exactly what overflowed.

    This also re-checks that nothing was lost by capping: a real STALE row and a real
    contradiction both exist in the fixture, so the structured fields must say so."""
    # Floor check FIRST, on the UNCAPPED (verbose) answer, before any default-mode
    # trimming -- this is what proves the fixture is realistically large (matching the
    # real repo DB's shape), not merely large enough to pass once already trimmed.
    verbose_payload = kb.build_answer("sammakorn", refresh=False, verbose=True)
    verbose_answer_tok = _tokens(json.dumps(verbose_payload, ensure_ascii=False, indent=2))
    assert verbose_answer_tok >= REALISTIC_FLOOR_TOKENS, (
        f"populated-DB fixture's own verbose/uncapped answer is only {verbose_answer_tok} "
        f"tokens, under the {REALISTIC_FLOOR_TOKENS}-token realistic floor -- this fixture "
        "is too small to actually exercise the token-budget cap the way a real "
        "`--refresh`'d installation does; enlarge REAL_POPULATED_ROWS/_near_sammakorn_rows "
        "with more real rows rather than loosening this floor")

    payload = kb.build_answer("sammakorn", refresh=False)
    state = payload["state"]
    assert state.get("stale_count", 0) >= 1, (
        "fixture includes a real STALE row (WL.SSB.08/thaiwater_canal_waterlevel) -- "
        "stale_count must report it, not silently drop it")
    assert state.get("contradiction_count", 0) >= 1, (
        "fixture includes a real cross-source contradiction (REAL_CONTRADICTION_ROWS, "
        "dds_daily_pdf vs thaiwater_canal_waterlevel) -- contradiction_count must "
        "report it")
    assert state.get("status_counts_all", {}), (
        "status_counts_all must cover every drainage row this check, including STALE "
        "ones, not just the fresh subset status_counts already reported")

    # UPDATED 2026-10-04 (the fix): this fixture's RED used to come ENTIRELY from
    # the 3 `dds_daily_pdf` "ระดับน้ำวิกฤติ" rows in `_real_dds_canal_rows()`
    # (ปตร.คลองประเวศฯ-ลาดกระบัง / ปตร.คลองสองสายใต้ / ปตร.คลองแสนแสบ-มีนบุรี) -- exactly
    # the bulletin's `canal_outer` ("ภายนอกคันปองกันน้ำทวม") section, and exactly the
    # bug this fix removes: those 3 gates are 8-11 km from Sammakorn and measure the
    # OUTSIDE-the-dike water level, a different hydraulic regime than what a resident at
    # this centre experiences (see readout.py's `_DDS_GATE_COORDS`/dds_canal-loop
    # comments). None of this fixture's `canal_inner` rows are critical (all real
    # 'ระดับน้ำปกติ', matching the actual current bulletin -- MEASURED against this repo's
    # own data/observations.sqlite on 2026-10-04), and the one `canal_inner` gate this
    # repo has a sourced coordinate for (WL.SSB.07, "เขตบางกะปิ") sits 3.14 km from
    # Sammakorn -- just outside `_answer_state`'s own 3.0 km default radius -- so a
    # correctly-gated answer against this fixture is honestly UNKNOWN, not RED. Asserting
    # RED here would mean re-introducing the exact bug this check fixed. `forward_hazard`
    # still reaches ACTIVE (unaffected -- it comes from `_real_forecast_model_rows()`, not
    # the DDS canal rows), so the per-model hazard cap this test cares about is still
    # exercised; only the (incorrect) RED-path current-state text is not, which is exactly
    # this fix's point.
    # fix (2026-10-05, M8 P3 "Jev Sandwich"): `dual_state` now ALSO gets `colour`/
    # `label_th` folded in whenever this fixture's own Z0 (nearest bma_watermap/
    # thaiwater_waterlevel gauge to the Sammakorn point) has a fresh reading -- see
    # tests/test_kb_answer_sandwich.py for the fold's own dedicated tests. This
    # assertion only still pins the pre-existing two keys' VALUES (never loosened),
    # not the dict's exact key set.
    dual_state = payload["next_action"]["dual_state"]
    # UPDATED (S1/S2b, founder 2026-10-05, this M8 revision): the DDS-canal-row path
    # alone still decides UNKNOWN here (unchanged -- no sourced canal_inner gate
    # within radius turned critical). But S1 forbids ever discarding Z0's own fresh
    # agency word to UNKNOWN, AND S2b's fix now reads this fixture's own real
    # declared OUTLET (WL.SSB.08, "วิกฤต" in `_near_sammakorn_rows`) on every call,
    # which raises the sandwich's own colour from GREEN to YELLOW
    # (OUTLET_CRITICAL) -- the fold-in a few lines below this test then promotes
    # the undecided legacy UNKNOWN up to that YELLOW. This is the intended
    # correction, not a regression; asserting UNKNOWN again would mean
    # reintroducing the exact "top calm/UNKNOWN eats Z0's own word" and
    # "OUTLET critical silently ignored" bugs this guards against.
    assert dual_state["current_local_state"] == "YELLOW", (
        f"fixture's current_local_state is {dual_state['current_local_state']!r}, not "
        "the post-fix YELLOW (folded in from the sandwich's own OUTLET_CRITICAL "
        "reading) -- if this changed, check whether the sandwich fold-in, Z0 "
        "resolution, or the OUTLET read in kb.py/rings.py genuinely changed, don't "
        "just loosen this assertion")
    assert dual_state.get("confidence") == "LOW", (
        "the fold must carry the sandwich's own LOW confidence (TOP_UNREAD/"
        "OUTLET_CRITICAL reasons are never HIGH/official_tier) through to dual_state")
    assert dual_state["forward_hazard"] == "ACTIVE", (
        f"fixture's forward_hazard is {dual_state['forward_hazard']!r}, not the "
        "post-fix ACTIVE -- don't just loosen this assertion")
    assert len(payload["hazard"].get("per_model", [])) == 3, (
        "10-model fixture must be capped to 3 (min/median/max) in default mode")
    assert "+7 more" in (payload["hazard"].get("per_model_note") or "")

    answer_json = json.dumps(payload, ensure_ascii=False, indent=2)

    ai_tok, skill_tok = _ai_skill_tokens()
    answer_tok = _tokens(answer_json)
    total = ai_tok + skill_tok + answer_tok

    _check_budget(total, f"AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + populated-DB "
                          f"answer ({answer_tok})")
    # Hard-assert the margin here (never only the soft `_check_budget` warning) -- a
    # real installation's default answer was once measured with ZERO margin (already
    # over budget), so this case must never again pass with a thin-or-negative margin
    # going unnoticed.
    assert total <= TOKEN_BUDGET - MARGIN_TOKENS, (
        f"populated-DB answer total {total} is within {TOKEN_BUDGET - total} tokens of "
        f"the {TOKEN_BUDGET}-token ceiling -- under the required {MARGIN_TOKENS}-token "
        "margin")


def test_verbose_answer_names_every_source_uncapped(real_populated_db):
    """`verbose=True` is the escape hatch (`--verbose` CLI / MCP `verbose=true`) -- it
    must still return the full, uncapped source list (and the full Thai sentence notes
    `kb._sources_summary_note` replaces in default mode), never silently capped too."""
    capped = kb.build_answer("sammakorn", refresh=False, verbose=False)
    full = kb.build_answer("sammakorn", refresh=False, verbose=True)
    capped_notes = " ".join(capped["state"].get("notes", []))
    full_notes = " ".join(full["state"].get("notes", []))
    assert "--verbose" in capped_notes
    assert "--verbose" not in full_notes
    for row in REAL_POPULATED_ROWS:
        assert row["source_id"] in full_notes


# ---------------------------------------------------------------------------
# Refresh action on a real-DB-gone-stale answer
# ---------------------------------------------------------------------------

def test_refresh_action_present_when_populated_db_has_gone_stale(real_populated_db):
    """Reproduces a real, populated database
    whose rows have all aged past STALE_HOURS (an earlier measurement pinned the clock 6 days
    forward with `time_machine`; here the same effect is reached by pinning
    `as_of_date`/`now_utc` directly, with no extra dependency). The resulting
    `current_local_state`/`forward_hazard` must be UNKNOWN/UNKNOWN (never a stale
    reading dressed up as current), `state.stale_count` must be > 0, and -- the actual
    defect -- `next_action.actions` must contain the `--refresh` action naming the
    real area id, directly after the UNKNOWN action, regardless of what `state.notes`
    happens to say."""
    area = "sammakorn"
    lat, lon = kb._ANSWER_AREAS[area]["lat"], kb._ANSWER_AREAS[area]["lon"]
    future = datetime.datetime(2026, 10, 9, 12, 0, tzinfo=datetime.timezone.utc)

    state = kb._answer_state(lat, lon, as_of_date=future.isoformat(), verbose=False)
    assert state.get("stale_count", 0) > 0
    assert state.get("refresh_suggested") is True
    hazard = kb._answer_hazard(area, lat, lon, now_utc=future)
    assert hazard.get("stale") is True

    next_action = kb._answer_next_action(
        area, state_answer=state, hazard_answer=hazard, now_utc=future)
    assert next_action["dual_state"] == {
        "current_local_state": "UNKNOWN", "forward_hazard": "UNKNOWN"}

    actions = next_action["actions"]
    assert actions[0]["action"] == kb.UNKNOWN_ACTION_TH
    assert len(actions) >= 2, "the refresh action must not be crowded out"
    refresh_action = actions[1]
    # FIX (2026-10-03, this): refresh is now the DEFAULT -- this action fires
    # AFTER a default refresh attempt already ran (unless `--offline` was passed), so
    # the old "run --refresh"/"refresh=true" wording (a parameter the MCP tool no
    # longer even has) is wrong; the real action now names the real area id.
    # fix (2026-10-04): `refresh_ran` was not passed above, so it
    # defaults True (matches `_answer_next_action`'s own calls here, which pin a
    # refresh-already-ran run) -- the text must NOT tell the caller to drop
    # `--offline` (it was never passed this run); see
    # `test_refresh_action_wording_differs_when_offline_was_passed` below for that
    # other branch.
    assert f"--at {area}" in refresh_action["action"], (
        "the real area id must replace the old '<area>' placeholder")
    assert "--offline" not in refresh_action["action"]


def test_refresh_action_wording_differs_when_offline_was_passed():
    """fix (2026-10-04): MEASURED later -- with
    `--verbose` on an `--offline` call, the UNKNOWN-refresh action still claimed
    "refresh already ran by default and found nothing", even though `--offline` means
    no refresh ran at all this run. `refresh_ran=False` must produce the other,
    honest sentence -- mentioning `--offline`/`offline=false` (the thing the caller
    actually needs to change), never the "already refreshed" claim."""
    state = {"refresh_suggested": True, "status_counts": {}}
    out = kb._answer_next_action("sammakorn", state_answer=state, refresh_ran=False)
    refresh_action = next(a for a in out["actions"]
                           if "state.refresh_suggested" in a.get("source", ""))
    assert "--offline" in refresh_action["action"]
    assert "offline=false" in refresh_action["action"]
    assert "already ran" not in refresh_action["why"]
    # And the mirror: refresh_ran=True (the default) must never mention --offline.
    out_ran = kb._answer_next_action("sammakorn", state_answer=state, refresh_ran=True)
    refresh_action_ran = next(a for a in out_ran["actions"]
                               if "state.refresh_suggested" in a.get("source", ""))
    assert "--offline" not in refresh_action_ran["action"]


def test_refresh_action_not_present_when_fresh_but_fault_only():
    """The fault-only-sensor UNKNOWN case (every fresh row this check is a sensor
    fault, e.g. `ขัดข้อง`) is NOT a staleness problem -- `_answer_state` must not set
    `refresh_suggested` for it, and `_answer_next_action` must not append the refresh
    action, since re-fetching would not produce a different reading."""
    state = {"tag": "INSTINCT", "notes": [], "stale_count": 0, "status_counts": {},
             "refresh_suggested": False}
    hazard = {"tag": "RELAYED", "stale": False, "per_model": []}
    next_action = kb._answer_next_action(
        "sammakorn", state_answer=state, hazard_answer=hazard)
    actions = next_action["actions"]
    assert not any("--refresh" in a["action"] for a in actions)


# ---------------------------------------------------------------------------
# `_compact_hazard_for_display` -- real 10-model cap, and the None-sorts-as-0 fix
# ---------------------------------------------------------------------------

def test_compact_hazard_caps_real_ten_models_to_min_median_max():
    """Real shape (`_real_forecast_model_rows` above, 10 distinct models) -- capped to
    3 rows (min/median/max by `tomorrow_mm`), classification (`_classify_forward_
    hazard`) is unaffected because it runs on the UNCAPPED `hazard_answer`, never the
    display copy."""
    per_model = [{"model": m, "tomorrow_mm": v}
                 for _src, m, v in _REAL_FORECAST_MODEL_ROWS_RAW]
    hazard_answer = {"tag": "RELAYED", "stale": False, "per_model": per_model}
    before_classification = kb._classify_forward_hazard(hazard_answer)
    compact = kb._compact_hazard_for_display(hazard_answer)
    assert len(compact["per_model"]) == 3
    assert "+7 more" in compact["per_model_note"]
    values = sorted(v for _s, _m, v in _REAL_FORECAST_MODEL_ROWS_RAW)
    shown = sorted(m["tomorrow_mm"] for m in compact["per_model"])
    assert shown[0] == values[0]
    assert shown[-1] == values[-1]
    # Capping the DISPLAYED copy must never change the decision input's own
    # classification -- re-classify the same uncapped hazard_answer and compare.
    assert kb._classify_forward_hazard(hazard_answer) == before_classification


# ---------------------------------------------------------------------------
# MCP-serialised form (2026-10-04 FIX D) -- what a real MCP client actually
# receives on the wire for `floodconnect_answer`, not the plain
# `json.dumps(payload, indent=2)` the tests above measure.
#
# MEASURED cause: the real MCP SDK's FastMCP wraps a tool whose return type
# annotation is a bare `dict` as a STRUCTURED tool by default -- it then
# returns BOTH an unstructured text block (`pydantic_core.to_json(result,
# indent=2)`, the full payload) AND a second, separate `structuredContent`
# copy of the SAME payload (wrapped `{"result": ...}`, via
# `output_model.model_validate(...).model_dump(mode="json")`). A client sees
# the whole answer twice. That duplicate is what pushed the real default
# `refresh=True` path to 5,001/5,026 cl100k tokens (sammakorn/ram53,
# AI.md+SKILL.md+this MCP answer) -- over even the repo-wide 5,000
# `TOKEN_BUDGET`, despite the single-copy `json.dumps` form the tests above
# measure already fitting FIX C's tighter 4,700 ceiling on its own.
#
# Fix: `tools/mcp/floodconnect_mcp.py`'s `floodconnect_answer` tool is now
# declared `@mcp.tool(structured_output=False)` -- this removes the
# `structuredContent` duplicate entirely (confirmed below: `call_tool`
# returns a plain `list[TextContent]`, never the
# `(content, structuredContent)` tuple FastMCP produces for a structured
# tool). No field is dropped -- the single text block IS the full answer;
# only the second, redundant serialisation of it is gone.
#
# Ceiling raised (founder ruling 2026-10-04, verbatim: "ขยับขึ้นเป็น 10k Tokenได้"):
# this is now the ONE ceiling that matters for the real path an AI session actually
# takes -- AI.md + SKILL.md + one real `refresh=True`, real MCP-serialised
# `floodconnect_answer` call, both MVP areas. 9,500 leaves a 500-token margin below
# the 10,000 cl100k ceiling this founder ruling set; README/AI.md/SKILL.md state the
# ceiling as "<= 10,000 cl100k tokens (enforced by tests/test_token_budget.py at
# 9,500)". The smaller TOKEN_BUDGET/FIXC_TOKEN_BUDGET constants above measure
# narrower, less realistic sub-cases (offline-only, plain `json.dumps` without the
# real MCP transport) and are left as their own tighter internal checks -- they are
# not the ceiling an external AI session's real usage is measured against.
MCP_TOKEN_BUDGET = 9500
MCP_MARGIN_TOKENS = 500


def _check_mcp_budget(total: int, label: str) -> None:
    """Same soft-warning pattern as `_check_budget`, but against `MCP_TOKEN_BUDGET`/
    `MCP_MARGIN_TOKENS` (the real-refresh-path, real-MCP-serialisation ceiling) rather
    than the narrower offline-only `TOKEN_BUDGET`/`MARGIN_TOKENS` -- the two ceilings
    are intentionally different sizes, so this test must never fall back to asserting
    against the wrong one."""
    assert total <= MCP_TOKEN_BUDGET, (
        f"{label}: {total} tokens, over the {MCP_TOKEN_BUDGET}-token real-refresh-"
        "path ceiling")
    if total > MCP_TOKEN_BUDGET - MCP_MARGIN_TOKENS:
        warnings.warn(
            f"{label}: {total} tokens is within {MCP_TOKEN_BUDGET - total} of the "
            f"{MCP_TOKEN_BUDGET}-token ceiling (under the {MCP_MARGIN_TOKENS}-token "
            "safe margin) -- a small future wording change could break the real "
            "ceiling.")


def _fake_refresh_report_for_mcp() -> list[dict]:
    """Same 13-source shape as `_fake_refresh_report_like_answer_sources` above
    (not reused directly -- that helper is module-private to the earlier fix's own
    test -- but identical real `ANSWER_SOURCES` ids, so the refresh-report block's
    own size is realistic, not a tiny fake)."""
    ids = ["thaiwater_canal_waterlevel", "thaiwater_dam_release", "bma_watermap",
           "bma_dds_daily_pdf", "bma_dds_tide", "bma_dds_flood_report",
           "thaiwater_rain_gauge", "social_listening_facebook",
           "openmeteo_forecast7d", "metno_forecast7d", "pump_station_status",
           "flood_road_status", "hii_analyst_cctv"]
    return [{"id": sid, "ok": True, "skipped": False, "note": "simulated: measured run"}
            for sid in ids]


@pytest.mark.parametrize("area", ["sammakorn", "ram53"])
def test_mcp_serialised_default_refresh_answer_stays_under_tightened_budget(
        area, monkeypatch, tmp_path):
    """The REAL refresh-path, REAL MCP-serialised case: a fresh-clone DB (no
    `output/*.graphml`, so `_answer_accountability` takes the FIX C fallback path)
    that ALSO carries the real `hii_analyst_cctv` catalog rows (3 real cameras, same
    fixture `test_fallback_accountability_plus_cctv_stays_under_tightened_budget`
    above uses), with the real default `refresh=True` 13-source compacted refresh
    report on top -- at least as large as the real default-path answer this
    ceiling has to hold (the populated-DB case above is larger still, but does not
    go through refresh=True + the real MCP transport, which is the specific path
    the 5,001/5,026-token measurement was taken on). Calls the real
    `mcp.server.fastmcp` `FastMCP.call_tool` -- not a hand-rolled dict-plus-indent
    stand-in -- so a future FastMCP-side regression (e.g. structured_output
    silently re-enabled) is caught here, not only by reasoning about the SDK."""
    mcp_fastmcp = pytest.importorskip("mcp.server.fastmcp")  # noqa: F841 -- availability check only
    import importlib
    mcp_server_mod = importlib.import_module("tools.mcp.floodconnect_mcp")
    if mcp_server_mod.mcp is None:  # pragma: no cover -- stdlib JSON-RPC fallback active
        pytest.skip("mcp SDK not active in tools.mcp.floodconnect_mcp (fallback transport)")

    import tests.test_kb_answer as kb_answer_tests

    db_path = tmp_path / "observations.sqlite"
    conn = store.connect(db_path)
    for station_id, title, agency_en, province_th, lat, lon, cctv_url in (
            kb_answer_tests.REAL_CCTV_ROWS):
        text = f"{station_id} | {title} | {agency_en} | {province_th} | {lat},{lon} | {cctv_url}"
        store.insert_document(
            conn, source_id="hii_analyst_cctv", fetched_at_utc="2026-10-03T12:00:00+00:00",
            section="cctv_station", text=text,
        )
    conn.close()
    monkeypatch.setattr(kb, "DB_PATH", db_path)
    monkeypatch.setattr(acct, "DB_PATH", db_path)
    monkeypatch.setattr(kb, "_refresh_relevant_sources",
                         lambda *a, **k: _fake_refresh_report_for_mcp())

    payload = kb.build_answer(area, refresh=True, verbose=False)
    assert isinstance(payload["refresh"], dict)  # compact form, never the raw 13-row list
    assert payload["accountability"]["basis"] == "governance_dag_fallback"
    assert len(payload.get("cctv", {}).get("cameras", [])) == 3

    # The tool wrapper is patched to return this exact payload rather than running
    # a real refresh, so this test measures the MCP serialisation of a realistic
    # answer, not network behaviour -- `floodconnect_answer_core` itself is already
    # covered by the kb-level tests above and in tests/test_kb_answer.py.
    monkeypatch.setattr(
        mcp_server_mod, "floodconnect_answer_core",
        lambda at, refresh=None, offline=False, verbose=False, household=None: payload)

    result = asyncio.run(mcp_server_mod.mcp.call_tool("floodconnect_answer", {"at": area}))
    assert isinstance(result, list), (
        f"{area}: floodconnect_answer must return plain unstructured content "
        f"(structured_output=False) -- got {type(result)!r}, which means a "
        "structuredContent duplicate of the whole answer is back")
    mcp_answer_text = "".join(block.text for block in result if hasattr(block, "text"))
    # No information lost: every tag/safety-relevant marker from the kb-level
    # payload must still be present in the text the MCP client actually receives.
    for marker in ("UNKNOWN", "VISUAL-CHECK", "tag"):
        assert marker in mcp_answer_text, (
            f"{area}: MCP-serialised answer dropped the {marker!r} marker -- "
            "compacting the transport must never lose safety/tag information")

    ai_tok, skill_tok = _ai_skill_tokens()
    mcp_answer_tok = _tokens(mcp_answer_text)
    total = ai_tok + skill_tok + mcp_answer_tok

    assert total <= MCP_TOKEN_BUDGET, (
        f"{area}: AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + MCP-serialised "
        f"default refresh=True answer ({mcp_answer_tok}) = {total} tokens, over "
        f"the real refresh path's {MCP_TOKEN_BUDGET}-token ceiling")
    _check_mcp_budget(total, f"{area}: AI.md ({ai_tok}) + SKILL.md ({skill_tok}) + "
                              f"MCP-serialised default refresh answer ({mcp_answer_tok})")


def test_compact_hazard_never_shows_a_none_model_as_the_min():
    """Regression: `tomorrow_mm=None` used to
    sort as 0 (`m.get("tomorrow_mm") or 0`), so a model with no figure this check
    could be displayed AS the min, a false reading dressed up as the smallest real
    one. Dropped from selection, still counted in the note."""
    per_model = [
        {"model": "no_data", "tomorrow_mm": None},
        {"model": "low", "tomorrow_mm": 2.0},
        {"model": "mid", "tomorrow_mm": 5.0},
        {"model": "high", "tomorrow_mm": 10.0},
    ]
    hazard_answer = {"tag": "RELAYED", "stale": False, "per_model": per_model}
    compact = kb._compact_hazard_for_display(hazard_answer)
    shown_models = {m["model"] for m in compact["per_model"]}
    assert "no_data" not in shown_models, (
        "a model with tomorrow_mm=None must never be selected as the displayed min")
    assert shown_models == {"low", "mid", "high"}
    assert "no tomorrow_mm figure" in compact["per_model_note"]
