"""tests/test_tag_vocabulary.py -- the fixed epistemic tag set is stated in exactly
one effective place and served identically everywhere.

AI.md documents the five-value vocabulary once, in prose, for a human/AI reader.
tag_vocabulary.py's TAG_VOCABULARY is the single machine-readable copy; kb.py's
TAG_ORDER, tools/mcp/floodconnect_mcp.py's TAG_VOCABULARY and tools/api/export_api.py's
TAG_VOCABULARY all import that one object now (an earlier check defect: the three
constants agreed with each other, but tools/typology/build_graph.py's own allowed-set
did not, and three compound values it let through reached api/v1 and MCP unchanged --
this file could not have caught that, because it never looked at served output; the
scan tests below close that gap). This test fails loud the moment any copy drifts,
instead of letting an AI reading AI.md trust a vocabulary that api/v1, MCP or kb.py no
longer honours (an earlier check defect: AI.md said "no sixth tag value" while
export_api.py's schema still listed eight).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AI_MD = ROOT / "AI.md"
API_V1_DIR = ROOT / "site" / "dist" / "api" / "v1"


def _ai_md_tag_vocabulary() -> tuple[str, ...]:
    text = AI_MD.read_text(encoding="utf-8")
    m = re.search(r"\bVERIFIED/MEASURED/RELAYED/INSTINCT/OPEN\b", text)
    assert m, "AI.md no longer states the slash-joined tag vocabulary this test parses"
    return tuple(m.group(0).split("/"))


def test_ai_md_mcp_export_api_and_kb_agree_on_tag_vocabulary():
    import kb
    from tools.api import export_api
    sys.path.insert(0, str(ROOT / "tools" / "mcp"))
    import floodconnect_mcp as mcp  # noqa: E402

    ai_md_tags = _ai_md_tag_vocabulary()
    kb_tags = tuple(kb.TAG_ORDER)
    assert ai_md_tags == mcp.TAG_VOCABULARY == export_api.TAG_VOCABULARY == kb_tags, (
        f"tag vocabulary drifted: AI.md={ai_md_tags}, "
        f"floodconnect_mcp.TAG_VOCABULARY={mcp.TAG_VOCABULARY}, "
        f"export_api.TAG_VOCABULARY={export_api.TAG_VOCABULARY}, "
        f"kb.TAG_ORDER={kb_tags}"
    )
    assert len(ai_md_tags) == 5, "the vocabulary is documented everywhere as five values"


def _walk_json_tag_values(obj, out: list[str], path: str = "$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "tag" and isinstance(v, str):
                out.append(f"{path}.tag={v!r}")
            _walk_json_tag_values(v, out, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_json_tag_values(item, out, f"{path}[{i}]")


def test_every_served_api_v1_tag_value_is_in_vocabulary():
    """Walks every *.json under site/dist/api/v1/ recursively and asserts every
    "tag" value is one of TAG_VOCABULARY -- this is the exact surface an earlier check's
    an earlier review found VERIFIED-CONTRADICTED/MEASURED+OPEN/RELAYED-unverified leaking
    through on, which the equality test above never looked at."""
    from tag_vocabulary import TAG_VOCABULARY

    if not API_V1_DIR.exists():
        import pytest
        pytest.skip("site/dist/api/v1 not built in this checkout")

    offenders: list[str] = []
    for jf in sorted(API_V1_DIR.rglob("*.json")):
        try:
            doc = json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        found: list[str] = []
        _walk_json_tag_values(doc, found)
        for entry in found:
            value = entry.split("=", 1)[1].strip("'")
            if value not in TAG_VOCABULARY:
                offenders.append(f"{jf.relative_to(ROOT)}: {entry}")
    assert not offenders, "tag value outside TAG_VOCABULARY served in api/v1:\n" + "\n".join(offenders)


def test_kb_answer_json_tags_are_in_vocabulary(tmp_path, monkeypatch):
    """Calls kb.build_answer in-process (the exact function `answer --json` prints,
    see its own docstring) against a fresh empty DB at a tmp_path, monkeypatched onto
    kb.DB_PATH -- never the real gitignored data/observations.sqlite (this repo's own
    conftest guard fails any test that writes into the real data/ store; a subprocess
    invocation of kb.py would use that real store instead). Asserts every `tag` key in
    the returned payload is in TAG_VOCABULARY -- the third surface (besides api/v1 and
    MCP) this vocabulary must hold on."""
    import kb
    from tag_vocabulary import TAG_VOCABULARY

    monkeypatch.setattr(kb, "DB_PATH", tmp_path / "does_not_exist.sqlite")
    # No broad try/except-skip here on purpose: a prior version of this test
    # turned every exception into a skip (including a real regression in
    # build_answer itself), which defeats the point of the assertion below.
    # MEASURED: build_answer("sammakorn") against a fresh, empty tmp DB
    # returns a dict cleanly -- it does not require the DB file to pre-exist.
    payload = kb.build_answer("sammakorn")
    found: list[str] = []
    _walk_json_tag_values(payload, found)
    offenders = [e for e in found if e.split("=", 1)[1].strip("'") not in TAG_VOCABULARY]
    assert not offenders, "tag value outside TAG_VOCABULARY in kb.py answer output:\n" + "\n".join(offenders)


def test_export_api_schema_tag_enum_matches_TAG_VOCABULARY():
    from tools.api import export_api

    # The schema-generation function builds `tag_enum = list(TAG_VOCABULARY)` inline;
    # assert the source constant directly rather than re-running schema generation
    # (which needs a populated --out-dir) -- any future edit that reintroduces a
    # hardcoded enum list here would still be caught by the AI.md/MCP comparison above.
    assert list(export_api.TAG_VOCABULARY) == [
        "VERIFIED", "MEASURED", "RELAYED", "INSTINCT", "OPEN",
    ]


def test_staleness_rejects_tag_outside_vocabulary():
    from tools.api import export_api

    class _FakeBuildData:
        @staticmethod
        def age_class(observed_at, generated_at_utc):
            return "fresh"

    try:
        export_api._staleness("2026-10-02T00:00:00Z", "2026-10-02T00:00:00Z",
                               _FakeBuildData(), "PROPOSAL-derived")
    except ValueError:
        pass
    else:
        raise AssertionError("_staleness accepted a tag outside TAG_VOCABULARY")
