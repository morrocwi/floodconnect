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
    assert all(r.ok for r in results)


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
