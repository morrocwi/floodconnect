"""Tests for the human-experience layer: experience_log.py front-matter parsing +
store.py's experience_log table (insert/idempotent-replace/find). No network calls."""
from pathlib import Path

import pytest

import experience_log
import store

CARD_TEXT = """---
id: exp_test_card
date_event: 2026-09-26
date_collected: 2026-09-27
source_type: social_post
role: ผู้อยู่อาศัย
place: ทดสอบ
node_ids: []
tag: RELAYED-EXPERIENCE
measurables:
  - {what: "ตัวอย่าง", value: 1, unit: "หน่วย"}
lenses:
  politics: "ข้อความการเมือง"
  philosophy: "ข้อความปรัชญา"
  structure: "ข้อความโครงสร้าง"
  system: "ข้อความระบบ"
  ethics: "ข้อความจริยธรรม"
dag_gaps: [G1]
ews_element: 2
sprc: R
proposed_indicators: ["ตัวชี้วัดตัวอย่าง"]
future_signal: "สัญญาณอนาคตตัวอย่าง"
---

# บัตรทดสอบ

เนื้อหาทดสอบ ไม่ใช่ front-matter
"""


@pytest.fixture()
def conn(tmp_path):
    return store.connect(tmp_path / "test.sqlite")


@pytest.fixture()
def card_file(tmp_path):
    p = tmp_path / "exp_test_card.md"
    p.write_text(CARD_TEXT, encoding="utf-8")
    return p


def test_parse_front_matter_reads_required_fields(card_file):
    data = experience_log.parse_front_matter(card_file)
    assert data["id"] == "exp_test_card"
    assert data["role"] == "ผู้อยู่อาศัย"
    assert data["tag"] == "RELAYED-EXPERIENCE"
    assert data["lenses"]["ethics"] == "ข้อความจริยธรรม"
    assert data["dag_gaps"] == ["G1"]


def test_parse_front_matter_missing_fence_raises(tmp_path):
    p = tmp_path / "bad.md"
    p.write_text("# no front matter here\n", encoding="utf-8")
    with pytest.raises(ValueError):
        experience_log.parse_front_matter(p)


def test_parse_front_matter_missing_required_field_raises(tmp_path):
    p = tmp_path / "bad2.md"
    p.write_text("---\nid: x\n---\nbody\n", encoding="utf-8")
    with pytest.raises(ValueError):
        experience_log.parse_front_matter(p)


def test_schema_creates_experience_log_table(conn):
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "experience_log" in tables


def test_add_card_inserts_one_row(conn, card_file):
    card_id = experience_log.add_card(conn, card_file)
    assert card_id == "exp_test_card"
    rows = store.query_experience(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "exp_test_card"
    assert row["tag"] == "RELAYED-EXPERIENCE"
    assert row["politics"] == "ข้อความการเมือง"
    assert row["ethics"] == "ข้อความจริยธรรม"
    assert row["sprc"] == "R"
    assert row["ews_element"] == "2"


def test_add_card_is_idempotent_on_id(conn, card_file):
    experience_log.add_card(conn, card_file)
    experience_log.add_card(conn, card_file)  # re-add same card -- must not duplicate
    rows = store.query_experience(conn)
    assert len(rows) == 1


def test_re_add_replaces_changed_fields(conn, card_file):
    experience_log.add_card(conn, card_file)
    edited = card_file.read_text(encoding="utf-8").replace(
        "ข้อความจริยธรรม", "ข้อความจริยธรรมที่แก้ไขแล้ว")
    card_file.write_text(edited, encoding="utf-8")
    experience_log.add_card(conn, card_file)
    rows = store.query_experience(conn)
    assert len(rows) == 1
    assert rows[0]["ethics"] == "ข้อความจริยธรรมที่แก้ไขแล้ว"


def test_query_experience_find_by_term(conn, card_file):
    experience_log.add_card(conn, card_file)
    found = store.query_experience(conn, term="สัญญาณอนาคตตัวอย่าง")
    assert len(found) == 1
    assert found[0]["id"] == "exp_test_card"

    not_found = store.query_experience(conn, term="ไม่มีคำนี้แน่นอน")
    assert not_found == []


def test_query_experience_by_role_filter(conn, card_file):
    experience_log.add_card(conn, card_file)
    rows = store.query_experience(conn, role="ผู้อยู่อาศัย")
    assert len(rows) == 1
    rows_none = store.query_experience(conn, role="สื่อ")
    assert rows_none == []


def test_all_six_real_cards_parse_and_have_required_lenses():
    """Every shipped card under docs/knowledge/experience/ must parse and carry all 5
    lenses + RELAYED-EXPERIENCE tag -- a real regression guard, not just the synthetic
    fixture above."""
    exp_dir = Path(__file__).parent.parent / "docs" / "knowledge" / "experience"
    cards = sorted(exp_dir.glob("exp_*.md"))
    assert len(cards) == 6, f"expected 6 experience cards, found {len(cards)}: {cards}"
    for card_path in cards:
        data = experience_log.parse_front_matter(card_path)
        assert data["tag"] == "RELAYED-EXPERIENCE", card_path
        lenses = data.get("lenses") or {}
        for key in ("politics", "philosophy", "structure", "system", "ethics"):
            assert lenses.get(key), f"{card_path} missing lens '{key}'"
        assert data.get("proposed_indicators"), f"{card_path} missing proposed_indicators"
        assert data.get("future_signal"), f"{card_path} missing future_signal"
