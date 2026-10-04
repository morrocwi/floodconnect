"""Draft page-block renderer for LAYER 0 -- a function the committer can call from
site/build_page.py (NOT wired in by this check; see AGENTS.md "one committing worker per
worktree" -- writes files only, does not edit build_page.py/build_data.py).

Given a list of Layer0Readout records (from tools/layer0/in_out_capacity.py's build_*
functions), produces a small dict-of-strings block suitable for inserting into the existing
page template -- plain data, no HTML framework dependency, so the committer decides how (or
whether) to splice it into build_page.py's own templating.

Public-page wording law (AGENTS.md §2): never emit ยังไม่ต้อง/ห้าม/ไม่ควร/ผ่อนคลาย/ปั๊มเสีย on
rendered strings -- this module only passes through Layer0Readout.sentence strings (already
built by in_out_capacity.py without those words) and adds neutral section labels.
"""

from __future__ import annotations

from typing import Iterable

from .in_out_capacity import Layer0Readout

_FORBIDDEN_WORDS = ("ยังไม่ต้อง", "ห้าม", "ไม่ควร", "ผ่อนคลาย", "ปั๊มเสีย")


def _check_wording(text: str) -> None:
    for word in _FORBIDDEN_WORDS:
        if word in text:
            raise ValueError(f"public-page wording law violation: {word!r} in {text!r}")


def render_layer0_block(readouts: Iterable[Layer0Readout]) -> dict:
    """Returns {"title": str, "units": [{"unit_id", "label", "sentence", "in_vs_capacity",
    "out_vs_in", "time_to_exceed_h"}], "generated_note": str}. Every sentence is checked
    against the public-page wording law before being included."""
    units = []
    for r in readouts:
        _check_wording(r.sentence)
        units.append({
            "unit_id": r.unit_id,
            "label": r.label,
            "sentence": r.sentence,
            "in_vs_capacity": r.in_vs_capacity,
            "out_vs_in": r.out_vs_in,
            "time_to_exceed_h": r.time_to_exceed_h,
        })
    return {
        "title": "LAYER 0 -- น้ำเข้า / น้ำออก / รับมือได้",
        "units": units,
        "generated_note": (
            "สามตัวเลขต่อหน่วย (IN/OUT/CAPACITY), PROPOSAL-derived simplification ของ "
            "PROP-FLOOD-06 -- ดู docs/LAYER0_IN_OUT_CAPACITY.md"
        ),
    }


def render_layer0_html_fragment(block: dict) -> str:
    """Optional plain-HTML fragment (no CSS framework, no <html>/<head> wrapper) the
    committer may splice into an existing page template, or ignore entirely in favour of
    driving their own template from render_layer0_block()'s plain dict instead."""
    rows = []
    for u in block["units"]:
        _check_wording(u["sentence"])
        rows.append(f"<li data-unit=\"{u['unit_id']}\">{u['sentence']}</li>")
    return (
        f"<section class=\"layer0-block\"><h2>{block['title']}</h2>"
        f"<ul>{''.join(rows)}</ul>"
        f"<p class=\"layer0-note\">{block['generated_note']}</p></section>"
    )
