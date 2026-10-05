"""llms.txt's first instruction must be the KG-first step (M4 acceptance A4) --
guards the ordering so a later edit cannot silently push it down past the
tier router or drop it."""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
LLMS_TXT = HERE / "llms.txt"


def _first_non_heading_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return stripped
    return ""


def test_first_instruction_names_kg_anchor_and_the_index():
    text = LLMS_TXT.read_text(encoding="utf-8")
    first_line = _first_non_heading_line(text)
    assert "kg_anchor" in first_line, f"llms.txt's first instruction does not mention kg_anchor: {first_line!r}"
    assert "STEP 1" in first_line and "KG" in first_line.upper()
    # The raw GitHub URL to the index must appear before the tier router block.
    step1_pos = text.index("STEP 1")
    tier_pos = text.index("Which AI are you?")
    index_url_pos = text.index("kg_index/index.json")
    assert step1_pos < index_url_pos < tier_pos, (
        "the KG-first step (with its index.json pointer) must come before the tier router"
    )
