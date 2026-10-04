"""Tests for kb.py's cmd_connectors -- FIX B item 2 (2026-10-04): --live must fetch in
parallel (collect.run(parallel=True, ...)) and stream a progress line per source via
on_result, not only print after the whole batch finishes."""
import argparse

import collect
import kb


class _FakeResult:
    def __init__(self, source_id, ok=True, skipped=False, note=""):
        self.source_id = source_id
        self.ok = ok
        self.skipped = skipped
        self.note = note


def test_connectors_live_calls_collect_run_parallel_with_on_result(monkeypatch, capsys):
    captured = {}

    def _fake_run(source_ids, dry_run=False, parallel=False, per_source_timeout_s=None,
                   max_workers=None, on_result=None, **_kw):
        captured["parallel"] = parallel
        captured["per_source_timeout_s"] = per_source_timeout_s
        captured["on_result"] = on_result
        results = [_FakeResult(sid, ok=True) for sid in source_ids[:2]]
        if on_result is not None:
            for r in results:
                on_result(r)
        return results

    monkeypatch.setattr(collect, "run", _fake_run)
    args = argparse.Namespace(live=True)
    rc = kb.cmd_connectors(args)
    assert rc == 0
    assert captured["parallel"] is True
    assert captured["per_source_timeout_s"] == 20
    assert captured["on_result"] is not None
    out = capsys.readouterr().out
    assert "...live:" in out  # the streaming progress line was actually printed


def test_connectors_dry_mode_unaffected(monkeypatch, capsys):
    def _boom(*a, **k):
        raise AssertionError("collect.run must not be called in dry mode")
    monkeypatch.setattr(collect, "run", _boom)
    args = argparse.Namespace(live=False)
    rc = kb.cmd_connectors(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "dry, no network" in out
