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
    # `bma_pumphistory` is unconditionally skipped too (its own endpoint returned HTTP
    # 404, MEASURED 2026-10-04 -- see collect.DORMANT_PERMANENT_404's own comment), same
    # unconditional-of-dry_run shape as NO_FETCHER above, so it needs the same carve-out
    # here rather than failing the catch-all "every other source ok, not skipped" branch.
    dormant_404_ids = collect.DORMANT_PERMANENT_404
    for r in results:
        if r.source_id in candidate_ids:
            assert r.ok is False and r.skipped and r.note == "skipped -- no collector implemented", r
        elif r.source_id in no_fetcher_ids:
            assert r.ok is False and r.skipped and r.note.startswith("skipped -- no fetcher by design"), r
        elif r.source_id in dormant_404_ids:
            assert r.ok is False and r.skipped and "HTTP 404" in r.note, r
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
        "thaiwater_canal_waterlevel", "thaiwater_waterlevel", "bma_pumphistory",
        "thaiwater_flood_road", "dds_daily_pdf", "dds_tide_pdf", "dds_flood_report",
        "thaiwater_rain_24h", "bma_watermap", "openmeteo_forecast16d",
        "metno_locationforecast", "social_listening_google", "social_listening_paste",
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

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
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


_CHIANG_MAI_LAT, _CHIANG_MAI_LON = 18.7883, 98.9853  # real Chiang Mai city centre


def test_refresh_relevant_sources_excludes_bangkok_dds_for_a_non_bangkok_point(monkeypatch):
    """v0.1.1 fix: a bare `--at lat,lon` far outside Bangkok (Chiang Mai, real
    coordinates) must never fetch the BMA/dds.bangkok.go.th sources
    (`collect.SOURCE_BBOX`) -- those endpoints only ever cover the Bangkok metro area.
    Before this fix, `_refresh_relevant_sources` only narrowed by `collect.
    AREA_RELEVANT_SOURCES`, which is keyed on a NAMED area_id -- an unnamed point
    (every `area_id` this repo does not declare) skipped that narrowing entirely and
    still fetched every BMA DDS source regardless of location."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
        captured["source_ids"] = list(source_ids)
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    # area_id=None (the real shape `build_answer` passes for an unnamed point: `area_id
    # or at` falls back to the raw "lat,lon" string, which matches no declared area_id
    # anywhere) -- lat/lon are the only signal this fix can act on.
    kb._refresh_relevant_sources(f"{_CHIANG_MAI_LAT},{_CHIANG_MAI_LON}", verbose=False,
                                  lat=_CHIANG_MAI_LAT, lon=_CHIANG_MAI_LON)
    fetched = set(captured["source_ids"])
    for bkk_only in collect.SOURCE_BBOX:
        assert bkk_only not in fetched, (
            f"{bkk_only} (Bangkok-only BMA source) was fetched for a Chiang Mai point")


def test_refresh_relevant_sources_keeps_bangkok_dds_for_a_bangkok_point(monkeypatch):
    """The other side of the same fix: a real Bangkok-area point (Sammakorn's own
    coordinates, passed as a bare lat,lon rather than the named area) must still
    fetch the BMA DDS sources -- the bbox filter narrows by location, not by whether
    the point happens to be one of this repo's named areas."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
        captured["source_ids"] = list(source_ids)
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    sammakorn = kb._ANSWER_AREAS["sammakorn"]
    kb._refresh_relevant_sources(f"{sammakorn['lat']},{sammakorn['lon']}", verbose=False,
                                  lat=sammakorn["lat"], lon=sammakorn["lon"])
    fetched = set(captured["source_ids"])
    for bkk_source in collect.SOURCE_BBOX:
        if bkk_source in collect.DORMANT_NOT_IN_ALL or bkk_source in collect.CATALOG_ONLY_NOT_IN_REFRESH:
            continue
        if bkk_source not in collect.ANSWER_SOURCES:
            continue
        assert bkk_source in fetched, (
            f"{bkk_source} wrongly excluded for a real Bangkok point")


def test_refresh_relevant_sources_snaps_bare_coord_near_a_named_forecast_point(monkeypatch):
    """Independent review item 4 (MED): a bare lat,lon within
    `kb._FORECAST_POINT_SNAP_RADIUS_KM` of a named `kb._FORECAST_KNOWN_POINTS` entry
    (here Chiang Mai) must fetch its forecast under THAT named point id -- not under
    the coordinate's own `coord_*` id. Before this fix, the fetch always used
    `coord_*`, while the READ side (`kb._resolve_forecast_point`) snaps such a point
    onto the named point's cache -- so a fetch-then-read round trip for exactly this
    coordinate always came back `forward_hazard: UNKNOWN`, stale=True (MEASURED: real
    Chiang Mai and Hat Yai coordinates both regressed this way), because nothing was
    ever fetched under the name the read side looked for."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
        captured["points_by_source"] = points_by_source
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    kb._refresh_relevant_sources(f"{_CHIANG_MAI_LAT},{_CHIANG_MAI_LON}", verbose=False,
                                  lat=_CHIANG_MAI_LAT, lon=_CHIANG_MAI_LON)
    one_point = next(iter(captured["points_by_source"].values()))
    assert "chiangmai" in one_point, (
        f"expected the fetch to use the named point 'chiangmai', got {one_point!r}")
    assert one_point["chiangmai"] == kb._FORECAST_KNOWN_POINTS["chiangmai"]


def test_refresh_relevant_sources_bbox_filter_is_a_noop_with_no_coordinate(monkeypatch):
    """Existing direct callers (this test module, `kb.py`'s other internal uses before
    this fix) that pass no `lat`/`lon` at all must see unchanged behaviour -- the bbox
    filter is additive, never a silent new default narrowing for a caller that never
    opted into it."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
        captured["source_ids"] = list(source_ids)
        return []

    monkeypatch.setattr(collect, "run", _fake_run)
    kb._refresh_relevant_sources("sammakorn", verbose=False)
    fetched = set(captured["source_ids"])
    for bkk_source in collect.SOURCE_BBOX:
        if bkk_source in collect.ANSWER_SOURCES:
            assert bkk_source in fetched


def test_refresh_relevant_sources_all_flag_restores_full_sweep(monkeypatch):
    """`all_sources=True` (wired to `kb.py answer --all`) must restore the pre-fix full
    wired-source sweep (minus DORMANT/CATALOG_ONLY/AREA_RELEVANT_SOURCES/key-gating,
    unchanged) -- a human explicitly asking for everything still gets it."""
    import kb

    captured = {}

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
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

    def _fake_run(source_ids, dry_run=False, points_by_source=None, **_kw):
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


def test_cache_key_scopes_point_filterable_sources_by_point():
    """FIX B item 1 regression: openmeteo_forecast16d/metno_locationforecast are
    scoped to ONE area's point per call -- the TTL cache key must differ across two
    different points for the same sid, or area A's cache entry would falsely cache-
    hit area B's later call for a different point."""
    sid = "openmeteo_forecast16d"
    points_a = {sid: {"sammakorn": (13.75, 100.65)}}
    points_b = {sid: {"ram53": (13.76, 100.62)}}
    key_a = collect._cache_key(sid, points_a)
    key_b = collect._cache_key(sid, points_b)
    assert key_a != key_b
    # A non-point-filterable source's key is unaffected by points_by_source at all.
    assert collect._cache_key("dds_daily_pdf", points_a) == "dds_daily_pdf"
    assert collect._cache_key("dds_daily_pdf", None) == "dds_daily_pdf"


def test_parallel_cache_does_not_leak_across_different_points(monkeypatch, tmp_path):
    """End-to-end: `run(parallel=True, ttl_s=...)` for area A's point must NOT be
    treated as a cache hit for area B's different point within the same TTL window."""
    monkeypatch.setattr(collect, "FETCH_CACHE_PATH", tmp_path / ".fetch_cache.json")
    sid = "openmeteo_forecast16d"
    call_count = {"n": 0}

    def _fake_collector(conn, dry_run=False, points=None):
        call_count["n"] += 1
        return collect.CollectResult(sid, True, note=f"fetched for {points}")

    monkeypatch.setitem(collect.COLLECTORS, sid, _fake_collector)
    db_path = tmp_path / "t.sqlite"
    points_a = {sid: {"sammakorn": (13.75, 100.65)}}
    points_b = {sid: {"ram53": (13.76, 100.62)}}

    results_a = collect.run([sid], dry_run=False, db_path=db_path, points_by_source=points_a,
                             parallel=True, ttl_s=600, max_workers=2)
    assert call_count["n"] == 1
    assert results_a[0].ok

    # Different area/point, same sid, well within the TTL window -- must still fetch.
    results_b = collect.run([sid], dry_run=False, db_path=db_path, points_by_source=points_b,
                             parallel=True, ttl_s=600, max_workers=2)
    assert call_count["n"] == 2, "area B's distinct point must not be served from area A's cache entry"
    assert results_b[0].ok

    # Same area/point again, within TTL -- THIS should be a real cache hit.
    results_a2 = collect.run([sid], dry_run=False, db_path=db_path, points_by_source=points_a,
                              parallel=True, ttl_s=600, max_workers=2)
    assert call_count["n"] == 2, "the SAME point within the TTL window should be a cache hit"
    assert "cache hit" in results_a2[0].note


def test_parallel_worker_db_lock_reported_as_lock_error_not_timeout(monkeypatch, tmp_path):
    """A `store.connect()` failure inside `run(parallel=True)`'s worker thread (e.g. a
    writer that could not get the lock within `busy_timeout`) must come back as its own
    "database locked" `CollectResult`, not propagate unhandled out of the worker -- an
    unhandled exception there would leave `result_holder` without an entry for that
    source, which the join-deadline loop would then misreport as "timed out" even
    though the real cause was a DB lock, not a slow fetch."""
    monkeypatch.setattr(collect, "FETCH_CACHE_PATH", tmp_path / ".fetch_cache.json")
    sid = "openmeteo_forecast16d"

    def _raise_locked(*_args, **_kwargs):
        raise __import__("sqlite3").OperationalError("database is locked")

    monkeypatch.setattr(collect.store, "connect", _raise_locked)
    monkeypatch.setitem(collect.COLLECTORS, sid,
                         lambda conn, dry_run=False, points=None: collect.CollectResult(sid, True))

    results = collect.run([sid], dry_run=False, db_path=tmp_path / "t.sqlite",
                           parallel=True, ttl_s=0, max_workers=2, per_source_timeout_s=20)
    assert len(results) == 1
    assert results[0].ok is False
    assert "database locked" in results[0].note
    assert "timed out" not in results[0].note


# ---------------------------------------------------------------------------
# `diff_wl_bank_text` reading "ล้นตลิ่ง" is itself computed as
# `h - min_bank`, so it is not a real agency observation when `min_bank` is 0,
# null, or at/below `ground_level`. Real recorded values, 2026-10-06.
# ---------------------------------------------------------------------------
def test_thaiwater_status_word_ignores_overbank_text_when_bank_is_zero():
    """BLGTU05/BLGTU06/MKSND01/MKSNU03/NPNPU01: min_bank == ground_level == 0,
    situation_level null -- must fall through to NO_THRESHOLD, never OVERBANK."""
    word = collect._thaiwater_status_word(
        situation_level=None, diff_wl_bank_text="ล้นตลิ่ง (ม.)", min_bank=0.0, ground_level=0.0)
    assert word == "NO_THRESHOLD"


def test_thaiwater_status_word_ignores_overbank_text_when_bank_is_null():
    word = collect._thaiwater_status_word(
        situation_level=None, diff_wl_bank_text="ล้นตลิ่ง (ม.)", min_bank=None, ground_level=None)
    assert word == "NO_THRESHOLD"


def test_thaiwater_status_word_ignores_overbank_text_when_bank_at_or_below_ground():
    word = collect._thaiwater_status_word(
        situation_level=None, diff_wl_bank_text="ล้นตลิ่ง (ม.)", min_bank=174.5, ground_level=174.5)
    assert word == "NO_THRESHOLD"
    # falls back to a real situation_level when one is also published
    word2 = collect._thaiwater_status_word(
        situation_level=3, diff_wl_bank_text="ล้นตลิ่ง (ม.)", min_bank=174.5, ground_level=174.5)
    assert word2 == "thaiwater_situation_3"


def test_thaiwater_status_word_trusts_overbank_text_when_bank_is_real():
    """NPNPD02-shaped case with a genuinely usable bank: "ล้นตลิ่ง" is still trusted
    (a real, non-degenerate threshold backs it)."""
    word = collect._thaiwater_status_word(
        situation_level=None, diff_wl_bank_text="ล้นตลิ่ง (ม.)", min_bank=170.0, ground_level=165.0)
    assert word == "OVERBANK"
