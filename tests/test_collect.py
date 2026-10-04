"""Tests for collect.py -- dry-run (no network) and --from-file paths only. No test in
this file makes a live network call; anything that would is exercised via --from-file
against a fixture instead, or by monkeypatching `urllib.request.urlopen`."""
import urllib.error
from pathlib import Path

import pytest

import collect
import store

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_registry_returns_dict_keyed_by_id():
    reg = collect.load_registry()
    assert "thaiwater_canal_waterlevel" in reg
    assert reg["thaiwater_canal_waterlevel"]["id"] == "thaiwater_canal_waterlevel"


def test_dry_run_all_sources_makes_no_network_call(monkeypatch, tmp_path):
    def _boom(*a, **k):
        raise AssertionError("network call attempted during --dry-run")
    monkeypatch.setattr(collect.urllib.request, "urlopen", _boom)
    reg = collect.load_registry()
    results = collect.run(list(reg.keys()), dry_run=True, db_path=tmp_path / "t.sqlite")
    # `kind: candidate_unregistered` rows (TMD/data.go.th/GISTDA/DDPM) have no
    # collector by design -- they are registered as a known gap, not claimed covered.
    # Honest result is ok=False, skipped=True, never a fabricated ok=True and never a
    # network call (the monkeypatched urlopen above would raise if one happened, for
    # these rows too).
    # (This used to be duplicated as both `status: candidate_unregistered`
    # and `kind: candidate` on the same row -- merged into the single `kind` field.)
    # A source never actually fetched (no collector, or no
    # fetcher by design -- `collect.NO_FETCHER`) is now `skipped=True` with `ok=False`,
    # never a bare `ok=True`/`ok=False` with no way to tell "didn't try" from "tried and
    # succeeded"/"tried and failed" apart -- see `collect.CollectResult`.
    candidate_ids = {sid for sid, s in reg.items() if s.get("kind") == "candidate_unregistered"}
    no_fetcher_ids = collect.NO_FETCHER
    for r in results:
        if r.source_id in candidate_ids:
            assert r.ok is False and r.skipped and r.note == "skipped -- no collector implemented", r
        elif r.source_id in no_fetcher_ids:
            assert r.ok is False and r.skipped and r.note.startswith("skipped -- no fetcher by design"), r
        else:
            assert r.ok and not r.skipped, r


def test_unknown_source_id_reported_not_raised(tmp_path):
    results = collect.run(["not_a_real_source"], dry_run=True, db_path=tmp_path / "t.sqlite")
    assert len(results) == 1
    assert results[0].ok is False
    assert "not in registry" in results[0].note


def test_dds_flood_report_from_file_no_network(tmp_path):
    db_path = tmp_path / "t.sqlite"
    results = collect.run(
        ["dds_flood_report"], dry_run=False,
        from_file={"dds_flood_report": FIXTURES / "dds_flood_report_sample.html"},
        db_path=db_path)
    assert results[0].ok is True
    assert "no network call" in results[0].note
    conn = store.connect(db_path)
    docs = conn.execute(
        "SELECT * FROM documents WHERE source_id='dds_flood_report'").fetchall()
    assert len(docs) == 3  # the 3 road rows in the fixture


def test_dds_daily_pdf_from_file_requires_real_pdf_and_pdftotext(tmp_path):
    """This one integration-style test DOES touch the filesystem's pdftotext binary
    (no network) against this repo's own cached real snapshot, if present -- skipped if
    that snapshot isn't there (e.g. a fresh checkout without raw/ populated)."""
    real_pdf = collect.HERE / "raw" / "dds_reports" / "dds_daily_20260926T0437Z.pdf"
    if not real_pdf.exists():
        pytest.skip("scout's cached PDF snapshot not present in this checkout")
    db_path = tmp_path / "t.sqlite"
    results = collect.run(
        ["dds_daily_pdf"], dry_run=False, from_file={"dds_daily_pdf": real_pdf},
        db_path=db_path)
    assert results[0].ok is True
    assert results[0].counts["observations"] > 0


def test_dds_daily_pdf_from_file_degrades_gracefully_on_corrupt_pdf(tmp_path):
    """B8(a)/(regression): a corrupted/unreadable PDF must not crash the whole collector
    with an unhandled subprocess error -- it should store the raw path+pdftotext error as
    a document and return ok=True with 0 observations, never raise."""
    db_path = tmp_path / "t.sqlite"
    garbage = tmp_path / "garbage.pdf"
    garbage.write_bytes(b"this is not a real pdf")
    result = collect.collect_dds_daily_pdf(store.connect(db_path), from_file=garbage)
    assert result.ok is True
    assert result.counts["observations"] == 0
    assert result.counts["documents"] == 1
    conn = store.connect(db_path)
    docs = conn.execute(
        "SELECT * FROM documents WHERE section='pdftotext_failed'").fetchall()
    assert len(docs) == 1


def test_dds_daily_pdf_one_get_no_head(monkeypatch, tmp_path):
    """B1 regression: a live (non-from-file) fetch must make exactly ONE urlopen call for
    this URL, never a HEAD followed by a GET (that was 2 requests to the same URL per run,
    which broke the host-safety rule whenever the PDF had changed or no snapshot existed
    yet)."""
    calls = []

    class _FakeResp:
        def __init__(self, body):
            self.status = 200
            self._body = body
            self.headers = {}

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def _fake_urlopen(req, timeout=None):
        calls.append(req.get_method() if hasattr(req, "get_method") else "GET")
        return _FakeResp(b"%PDF-1.4 not really a pdf but has bytes")

    monkeypatch.setattr(collect.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(collect, "RAW_LIVE_DIR", tmp_path / "raw" / "live")
    db_path = tmp_path / "t.sqlite"
    collect.collect_dds_daily_pdf(store.connect(db_path))
    assert len(calls) == 1
    assert calls[0] == "GET"


def test_run_trips_circuit_breaker_on_403_and_skips_same_host(monkeypatch, tmp_path):
    """B2 regression: once one source on a host returns 403, every later source on that
    SAME host in the same run must be skipped, not requested."""
    def _fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(collect.urllib.request, "urlopen", _fake_urlopen)
    db_path = tmp_path / "t.sqlite"
    results = collect.run(
        ["dds_daily_pdf", "dds_flood_report", "dds_tide_pdf", "dds_nowcast_gif"],
        db_path=db_path)
    by_id = {r.source_id: r for r in results}
    assert by_id["dds_daily_pdf"].ok is False
    for sid in ("dds_flood_report", "dds_tide_pdf", "dds_nowcast_gif"):
        assert by_id[sid].ok is False
        assert "skipped" in by_id[sid].note
        assert "tripped" in by_id[sid].note or "blocked" in by_id[sid].note


def test_all_excludes_dormant_sources():
    """B2 regression: `bma_klongmap` (confirmed persistent 403) must not be part of a
    plain `--all` run, only reachable via an explicit `--source bma_klongmap`."""
    reg = collect.load_registry()
    all_ids = [sid for sid in reg if sid not in collect.DORMANT_NOT_IN_ALL]
    assert "bma_klongmap" not in all_ids
    assert "bma_klongmap" in reg  # still a real, collectible source


def test_missing_api_key_env_blocks_before_any_fetch(monkeypatch, tmp_path):
    """A registry-driven `auth: api_key` gate in `run()`
    blocks a collector call BEFORE it ever runs when the caller's own environment has
    no value for the declared `key_env` -- never silently fetched, never a fabricated
    `ok: True`. Stub source (real api_key-gated sources now exist --
    `gistda_flood_extent_api` and 6 more added 2026-10-03 -- but this stub keeps the
    test independent of whether a real key happens to be present anywhere) so this is
    a real, reproducible unit test rather than depending on a live key existing."""
    stub_id = "stub_api_key_source_for_test"
    stub_entry = {"id": stub_id, "url": "https://example.invalid/stub",
                  "auth": "api_key", "key_env": "FLOODCONNECT_STUB_TEST_API_KEY"}

    def _fake_load_registry(path=None):
        return {stub_id: stub_entry}

    def _boom(conn, dry_run=False):
        raise AssertionError("collector must never be called when the key is missing")

    monkeypatch.setattr(collect, "load_registry", _fake_load_registry)
    monkeypatch.setattr(collect, "COLLECTORS", {stub_id: _boom})
    monkeypatch.delenv("FLOODCONNECT_STUB_TEST_API_KEY", raising=False)

    results = collect.run([stub_id], dry_run=False, db_path=tmp_path / "t.sqlite")
    assert len(results) == 1
    r = results[0]
    assert r.ok is False and r.skipped is False
    assert "FLOODCONNECT_STUB_TEST_API_KEY" in r.note
    assert "missing env var" in r.note

    monkeypatch.setenv("FLOODCONNECT_STUB_TEST_API_KEY", "fake-key-value")
    results2 = collect.run([stub_id], dry_run=False, db_path=tmp_path / "t.sqlite")
    # Key now present -- the gate passes the call through to the (stub) collector,
    # which raises; `run()`'s own except-clause turns that into ok=False with the
    # exception text, proving the key check no longer blocks it.
    assert results2[0].ok is False
    assert "never be called" in results2[0].note


def test_collect_result_repr_marks_missing_key_as_unknown_not_fail(tmp_path):
    """A missing-API-key result must read as
    `unknown`/`not_fetched_missing_key`, never `FAIL` -- FAIL implies an attempt was
    made and failed, but `run()`'s key gate never attempts the fetch at all. Also
    checks the stray empty `{}` (an empty `counts` dict) no longer prints."""
    r = collect.CollectResult(
        "stub_source", False,
        note="missing env var SOME_STUB_API_KEY in this machine's own environment -- "
             "not fetched")
    text = repr(r)
    assert "status=unknown" in text
    assert "not_fetched_missing_key" in text
    assert "FAIL" not in text
    assert "{}" not in text  # no stray empty-counts dict


@pytest.mark.parametrize("sid,key_env", [
    ("google_flood_hub_api", "GOOGLE_FLOOD_HUB_API_KEY"),
    ("cds_era5_reanalysis", "CDSAPI_KEY"),
    ("nasa_lhasa_landslide_nowcast", "NASA_EARTHDATA_TOKEN"),
    ("opentopography_copernicus_dem_glo30", "OPENTOPOGRAPHY_API_KEY"),
    ("gfw_data_api", "GFW_API_KEY"),
    ("reliefweb_api_v2", "RELIEFWEB_APPNAME"),
])
def test_key_needed_collectors_added_20261003_report_missing_key_not_safe(
        sid, key_env, monkeypatch, tmp_path):
    """The 6 key-needed sources added 2026-10-03 (google_flood_hub_api,
    cds_era5_reanalysis, nasa_lhasa_landslide_nowcast, opentopography_copernicus_dem_glo30,
    gfw_data_api, reliefweb_api_v2) each: (1) are registered with the right `key_env`,
    (2) are wired into COLLECTORS, (3) make NO network call and report UNKNOWN with a
    reason -- never SAFE, never a guessed value -- when that key is absent from this
    environment, exactly like gistda_flood_extent_api already does."""
    registry = collect.load_registry()
    assert sid in registry, f"{sid} must be registered in sources/registry.yaml"
    assert registry[sid].get("auth") == "api_key"
    assert registry[sid].get("key_env") == key_env
    assert sid in collect.COLLECTORS

    monkeypatch.delenv(key_env, raising=False)
    results = collect.run([sid], dry_run=False, db_path=tmp_path / "t.sqlite")
    assert len(results) == 1
    r = results[0]
    assert r.ok is False
    assert key_env in r.note
    assert "missing env var" in r.note
    assert "unknown" in repr(r) and "FAIL" not in repr(r)


def test_answer_sources_is_exact_positive_allowlist():
    """Fix (2026-10-03): `collect.ANSWER_SOURCES` must be the exact set
    documented on the constant -- every source that feeds `state`/`hazard`/the PF06
    L-tier engine for a served area, and nothing with no such relevance (the MEASURED
    finding that triggered this fix: 47 of 72 registry sources, including
    gdacs_events/noaa_oni/openmeteo_sst/data_go_th_ckan/marine_imis, survived the old
    "everything minus exclusions" filter for a plain sammakorn answer)."""
    expected = {
        "thaiwater_canal_waterlevel", "bma_pumphistory", "thaiwater_flood_road",
        "dds_daily_pdf", "dds_tide_pdf", "dds_flood_report", "thaiwater_rain_24h",
        "bma_watermap", "openmeteo_forecast16d", "metno_locationforecast",
        "social_listening_google", "social_listening_paste",
    }
    assert set(collect.ANSWER_SOURCES) == expected
    reg = collect.load_registry()
    for sid in collect.ANSWER_SOURCES:
        assert sid in reg, f"{sid} must be a real, registered source"
    # The exact MEASURED-irrelevant sources named in the earlier review report must be absent.
    for irrelevant in ("gdacs_events", "noaa_oni", "openmeteo_sst", "openmeteo_pressure",
                       "data_go_th_ckan", "gistda_portal", "ddpm_portal", "tmd_main_site",
                       "marine_imis", "marine_elaws"):
        assert irrelevant not in collect.ANSWER_SOURCES


def test_refresh_relevant_sources_default_is_narrowed_to_answer_sources(monkeypatch):
    """A plain, non-verbose `kb.py answer --at sammakorn` (the default/common case) must
    fetch ONLY the `collect.ANSWER_SOURCES` set (intersected with the usual DORMANT/
    CATALOG_ONLY/AREA_RELEVANT_SOURCES narrowings) -- never the full wired-source list."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None):
        captured["source_ids"] = list(source_ids)
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    kb._refresh_relevant_sources("sammakorn", verbose=False)
    fetched = set(captured["source_ids"])
    # FIX (2026-10-04, F8/CCTV): `hii_analyst_cctv` is the ONE deliberate exception to
    # the `ANSWER_SOURCES` allowlist -- `kb._nearest_cctv_cameras` needs it refreshed
    # per area now, even though it feeds no state/hazard/next_action decision (see
    # `kb._refresh_relevant_sources`'s own docstring).
    assert fetched - {"hii_analyst_cctv"} <= collect.ANSWER_SOURCES
    assert len(fetched) < 20, (
        f"default sammakorn refresh fetched {len(fetched)} sources -- expected a small "
        "allowlisted set, not the near-full registry")


def test_refresh_relevant_sources_all_flag_restores_full_sweep(monkeypatch):
    """`all_sources=True` (wired to `kb.py answer --all`) must restore the pre-fix full
    wired-source sweep (minus DORMANT/CATALOG_ONLY/AREA_RELEVANT_SOURCES/key-gating,
    unchanged) -- a human explicitly asking for everything still gets it."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None):
        captured["source_ids"] = list(source_ids)
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    kb._refresh_relevant_sources("sammakorn", verbose=False, all_sources=True)
    fetched = set(captured["source_ids"])
    assert "gdacs_events" in fetched or "noaa_oni" in fetched, (
        "--all must restore sources with no sammakorn/ram53 relevance")
    assert len(fetched) > 40


def test_catalog_only_sources_excluded_from_refresh_set():
    """A catalog/document-only source must never
    be part of the fetch set `kb._refresh_relevant_sources` builds, regardless of
    area or verbosity -- it feeds no `state`/`hazard`/`next_action` field, so fetching
    it on every `--refresh` was pure token/bandwidth waste with no benefit."""
    assert "hii_analyst_cctv" in collect.CATALOG_ONLY_NOT_IN_REFRESH
    assert "bangkok_ckan_portal" in collect.CATALOG_ONLY_NOT_IN_REFRESH
    assert "bangkok_floodgate_locations" in collect.CATALOG_ONLY_NOT_IN_REFRESH
    assert ("bangkok_pump_station_and_floodgate_physical_data"
            in collect.CATALOG_ONLY_NOT_IN_REFRESH)
    reg = collect.load_registry()
    for sid in collect.CATALOG_ONLY_NOT_IN_REFRESH:
        assert sid in reg, f"{sid} must still be a real, collectible source"


def test_refresh_relevant_sources_excludes_catalog_and_quiets_missing_key(monkeypatch):
    """Same catalog-only exclusion, exercised through `kb._refresh_relevant_sources` itself --
    no network call: `collect.run` is monkeypatched to just RECORD which source_ids it
    was asked to fetch, never actually fetching. Catalog-only sources must be absent
    regardless of `verbose`/`all_sources`; a key-gated source with no key present must
    be absent when `verbose=False` (the default) and present when `verbose=True`
    (fix, 2026-10-03: `gistda_flood_extent_api` is not in
    `collect.ANSWER_SOURCES` -- it feeds no state/hazard field for any served area -- so
    seeing it now also requires `all_sources=True`, the explicit full-sweep opt-out;
    `verbose` alone no longer widens the SOURCE SET, only whether a key-gated gap with
    no fetch attempt still appears in the returned list)."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None):
        captured["source_ids"] = list(source_ids)
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    monkeypatch.delenv("GISTDA_API_KEY", raising=False)

    kb._refresh_relevant_sources("sammakorn", verbose=False)
    quiet_ids = captured["source_ids"]
    # FIX (2026-10-04, F8/CCTV): `hii_analyst_cctv` is now the ONE deliberate exception
    # re-added after the catalog-only exclusion below -- `_nearest_cctv_cameras` needs
    # it refreshed per area; every other catalog-only source stays excluded.
    assert "hii_analyst_cctv" in quiet_ids
    assert "bangkok_ckan_portal" not in quiet_ids
    assert "bangkok_floodgate_locations" not in quiet_ids
    assert "gistda_flood_extent_api" not in quiet_ids  # no key -> quietly skipped

    kb._refresh_relevant_sources("sammakorn", verbose=True, all_sources=True)
    verbose_ids = captured["source_ids"]
    assert "hii_analyst_cctv" in verbose_ids  # CCTV carve-out -- present regardless
    assert "bangkok_ckan_portal" not in verbose_ids
    assert "gistda_flood_extent_api" in verbose_ids  # verbose+all_sources -- still listed

    # New (): `verbose=True` alone, without `all_sources`, stays narrowed
    # to `collect.ANSWER_SOURCES` -- it must NOT resurrect a source with no state/hazard
    # relevance just because the caller wants visibility into key-gated gaps.
    kb._refresh_relevant_sources("sammakorn", verbose=True, all_sources=False)
    verbose_only_ids = captured["source_ids"]
    assert "gistda_flood_extent_api" not in verbose_only_ids
