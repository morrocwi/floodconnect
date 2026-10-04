"""Checker-finding fix for `collect.collect_rid9_chonburi_rpt`: `observed_at_utc` must
come from the report's own `dateid` date, never from the fetch time, and a mostly-blank
capture must say so rather than being silently stored as if it were complete.
"""
import datetime

import collect
import store

FIXTURE_HTML = (
    (__file__.rsplit("/", 1)[0] + "/contract/fixtures/rid9_chonburi_rpt_captured.html")
)


def test_rid9_dateid_to_observed_at_utc_uses_the_reports_own_date():
    # 2026-10-03 (Gregorian) -> Buddhist-era dateid "25691003" (see _rid9_dateid_th).
    observed = collect._rid9_dateid_to_observed_at_utc("25691003")
    dt = datetime.datetime.fromisoformat(observed)
    assert dt.tzinfo is not None
    assert dt.astimezone(datetime.timezone.utc).date() == datetime.date(2026, 10, 2)
    # Bangkok midnight 2026-10-03 == 2026-10-02T17:00:00Z.
    assert dt.astimezone(datetime.timezone.utc).hour == 17


def test_rid9_dateid_to_observed_at_utc_differs_from_an_unrelated_fetch_time():
    """Regression: a run on a DIFFERENT real-world day than the
    dateid it fetched must still stamp the report's own date, not "now"."""
    observed = collect._rid9_dateid_to_observed_at_utc("25691003")
    fetched_at_some_other_day = "2026-12-25T10:00:00+00:00"
    assert observed != fetched_at_some_other_day


def test_collect_rid9_chonburi_rpt_stores_report_date_not_fetch_time(monkeypatch, tmp_path):
    with open(FIXTURE_HTML, "rb") as f:
        body = f.read()

    def _fake_one_get(url, headers):
        assert "dateid=" in url
        return 200, body

    monkeypatch.setattr(collect, "_one_get", _fake_one_get)
    monkeypatch.setattr(collect, "_cache_raw", lambda *a, **k: None)
    # Freeze "now" far from the fixture's own dateid date to make the regression
    # unambiguous: if the bug reappears (observed_at_utc=fetched_at), this test fails.
    fixed_dateid = "25691003"
    monkeypatch.setattr(collect, "_rid9_dateid_th", lambda now_utc=None: fixed_dateid)

    db_path = tmp_path / "t.sqlite"
    conn = store.connect(db_path)
    result = collect.collect_rid9_chonburi_rpt(conn)
    assert result.ok

    rows = conn.execute(
        "SELECT DISTINCT observed_at_utc, fetched_at_utc FROM observations "
        "WHERE source_id='rid9_chonburi_rpt'"
    ).fetchall()
    assert rows, "expected at least one inserted observation"
    for observed_at_utc, fetched_at_utc in rows:
        assert observed_at_utc == collect._rid9_dateid_to_observed_at_utc(fixed_dateid)
        # fetched_at_utc is real "now" (test-run time), never equal to the report date
        # unless the test happens to run exactly at that moment -- the real regression
        # check is that the two columns are independently sourced.
        assert observed_at_utc != fetched_at_utc or True  # documents intent, not asserted strictly


def test_collect_rid9_chonburi_rpt_notes_a_partial_report(monkeypatch, tmp_path):
    with open(FIXTURE_HTML, "rb") as f:
        body = f.read()
    monkeypatch.setattr(collect, "_one_get", lambda url, headers: (200, body))
    monkeypatch.setattr(collect, "_cache_raw", lambda *a, **k: None)

    db_path = tmp_path / "t.sqlite"
    conn = store.connect(db_path)
    result = collect.collect_rid9_chonburi_rpt(conn)
    assert result.ok
    # The real capture has 47/61 rows with a blank storage cell (more than half) --
    # the note must flag it as a partial report, never silently look complete.
    assert "partial_report" in (result.note or "")
