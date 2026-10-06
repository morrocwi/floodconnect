"""Tests for `advice/parity.py` (P-D, design section G -- "no step weaker than
official, MISSING official items are listed as blockers").

Run only this file while iterating (AGENTS.md "no repeated full-arc audits"):
    python3 -m pytest tests/test_official_parity.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import advice.ladder as ladder  # noqa: E402
import advice.parity as parity  # noqa: E402

_GUIDANCE_PATH = HERE / "advice" / "official_guidance.yaml"


def _guidance_rows():
    return yaml.safe_load(_GUIDANCE_PATH.read_text(encoding="utf-8")) or []


def test_every_official_row_has_a_url_retrieved_at_verbatim_text_and_class():
    """Schema rule: 'Every row that is not OPEN must have a non-empty url,
    retrieved_at, verbatim_th and source_class.' (source_class added --
    OFFICIAL_TH or GENERAL, never null, for a fetched row)."""
    for row in _guidance_rows():
        if row.get("tag") == "OFFICIAL":
            assert row.get("url"), f"{row['id']} (OFFICIAL) has no url"
            assert row.get("retrieved_at"), f"{row['id']} (OFFICIAL) has no retrieved_at"
            assert row.get("verbatim_th"), f"{row['id']} (OFFICIAL) has no verbatim_th"
            assert row.get("source_class") in ("OFFICIAL_TH", "GENERAL"), (
                f"{row['id']} (OFFICIAL) has source_class={row.get('source_class')!r}, "
                "not OFFICIAL_TH/GENERAL")


def test_open_rows_carry_no_text_or_class():
    for row in _guidance_rows():
        if row.get("tag") == "OPEN":
            assert not row.get("url")
            assert not row.get("verbatim_th")
            assert row.get("source_class") is None


def test_no_missing_and_no_weaker_for_sourced_items():
    """The parity hard rule itself: every OFFICIAL row (either class) must
    resolve to EQUAL or STRICTER. MISSING and WEAKER both fail -- this is the
    acceptance gate the P-D task asks for ('MISSING must be 0 for sourced
    items'), unchanged by the two-class split."""
    table = parity.build_parity_table()
    bad = [r for r in table if r["verdict"] in (parity.VERDICT_MISSING, parity.VERDICT_WEAKER)]
    assert not bad, f"parity defects found: {bad}"


def test_no_missing_and_no_weaker_per_class():
    """The hard rule holds for EACH class independently -- a
    regression hidden by pooling (e.g. all GENERAL defects offset by OFFICIAL_TH
    EQUALs) must still fail here."""
    by_class = parity.summarize_by_class()
    for cls in ("OFFICIAL_TH", "GENERAL"):
        assert by_class[cls][parity.VERDICT_WEAKER] == 0, f"{cls} has a WEAKER row"
        assert by_class[cls][parity.VERDICT_MISSING] == 0, f"{cls} has a MISSING row"


def test_both_source_classes_are_represented():
    """Official parity must cover BOTH classes, not just OFFICIAL_TH -- a
    GENERAL-only or OFFICIAL_TH-only table would mean the fetch pass silently
    did not happen."""
    by_class = parity.summarize_by_class()
    official_th_total = sum(by_class["OFFICIAL_TH"].values())
    general_total = sum(by_class["GENERAL"].values())
    assert official_th_total > 0, "no OFFICIAL_TH rows found"
    assert general_total > 0, "no GENERAL rows found"


def test_counts_cover_every_guidance_row():
    """fix (2026-10-06, parity split): a row's own sentence can carry
    MORE THAN ONE distinct action (`build_parity_table` already emits one
    verdict PER `action_keys` entry, not one per row -- see its own
    docstring/for-loop) -- the total verdict count is the sum of each
    OFFICIAL row's own `action_keys` length, never a flat 1-per-row count
    (which undercounts the moment any row carries more than one key)."""
    table = parity.build_parity_table()
    counts = parity.summarize(table)
    total_rows = len(_guidance_rows())
    official_rows = [r for r in _guidance_rows() if r.get("tag") == "OFFICIAL"]
    open_rows = total_rows - len(official_rows)
    official_verdict_count = sum(max(len(r.get("action_keys") or []), 1) for r in official_rows)
    assert counts[parity.VERDICT_OPEN] == open_rows
    assert (counts[parity.VERDICT_EQUAL] + counts[parity.VERDICT_STRICTER]
            + counts[parity.VERDICT_MISSING] + counts[parity.VERDICT_WEAKER]) == official_verdict_count


def test_render_markdown_includes_every_row_id():
    table = parity.build_parity_table()
    md = parity.render_markdown(table)
    for row in _guidance_rows():
        assert row["id"] in md


def test_generated_parity_md_matches_current_build():
    """advice/PARITY.md on disk must be the file advice/parity.main() actually
    produces right now -- a stale PARITY.md (edited without regenerating, or the
    ladder/guidance files changed afterwards) is itself a defect."""
    parity_md_path = HERE / "advice" / "PARITY.md"
    assert parity_md_path.exists(), "advice/PARITY.md has not been generated yet"
    on_disk = parity_md_path.read_text(encoding="utf-8")
    fresh = parity.render_markdown(parity.build_parity_table())
    assert on_disk == fresh, "advice/PARITY.md is stale -- run `python3 -m advice.parity`"


# ---------------------------------------------------------------------------
# S5 (founder subtractive-fix ruling 2026-10-06): full per-page item
# inventory. `advice/official_guidance_inventory.yaml` names every actionable
# item this repo has found on each already-fetched page -- this test checks
# every one of those items actually resolves to a real OFFICIAL row with
# text and a ladder step, so "MISSING=0" in the parity table can no longer
# mean only "the rows we happened to add have a step", only "every item we
# have ever inventoried for these pages has one."
# ---------------------------------------------------------------------------
_INVENTORY_PATH = HERE / "advice" / "official_guidance_inventory.yaml"


def _inventory_pages():
    return (yaml.safe_load(_INVENTORY_PATH.read_text(encoding="utf-8")) or {}).get("pages", [])


def test_inventory_file_exists_and_lists_every_fetched_and_retried_page():
    pages = _inventory_pages()
    urls = {p["url"] for p in pages}
    for url in (
        "https://www.prd.go.th/th/content/category/detail/id/31/iid/432703",
        "https://www.prd.go.th/th/content/category/detail/id/31/iid/529458",
        "https://www.prd.go.th/th/content/category/detail/id/31/iid/534015",
        "https://www.ready.gov/floods",
        "https://prepare.campaign.gov.uk/flooding/",
        "https://disaster.go.th",
        "https://www.niems.go.th",
    ):
        assert url in urls, f"{url} is not listed in the inventory file"


def test_excluded_items_carry_a_reason_and_no_og_id():
    """An item marked `excluded: true` (US/UK-only, or purely informational)
    must say WHY, and must not also claim a row -- excluded and sourced are
    mutually exclusive for one item."""
    for page in _inventory_pages():
        for entry in page.get("items", []):
            if entry.get("excluded"):
                assert entry.get("reason"), f"{entry['item']!r} is excluded with no reason"
                assert not entry.get("og_id"), f"{entry['item']!r} is excluded but also names an og_id"


def test_every_inventoried_item_resolves_to_a_real_sourced_row_with_a_ladder_step():
    guidance_by_id = {row["id"]: row for row in _guidance_rows()}
    steps = ladder.all_steps()
    for page in _inventory_pages():
        for entry in page.get("items", []):
            if entry.get("excluded"):
                continue
            row = guidance_by_id.get(entry["og_id"])
            assert row is not None, f"{entry['item']!r} -> {entry['og_id']} does not exist"
            assert row["tag"] == "OFFICIAL", f"{entry['item']!r} -> {entry['og_id']} is not OFFICIAL"
            assert row.get("url") == page["url"], (
                f"{entry['item']!r} -> {entry['og_id']} is not sourced from {page['url']!r}")
            assert row.get("verbatim_th"), f"{entry['item']!r} -> {entry['og_id']} has no verbatim_th"
            action_keys = row.get("action_keys") or []
            assert action_keys, f"{entry['item']!r} -> {entry['og_id']} has no action_keys"
            matched = [k for k in action_keys
                       if any(k in (s.get("action_keys") or []) for s in steps)]
            assert matched, f"{entry['item']!r} -> {entry['og_id']} has no matching ladder step"
