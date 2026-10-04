#!/usr/bin/env python3
"""
experience_log.py -- CLI for the human-experience layer (docs/knowledge/experience/).

Parses a card's YAML front-matter (between the leading `---` / `---` fence) into the
append-only-schema `experience_log` table in `store.py` (INSERT OR REPLACE keyed on the
card's own `id` -- editing a card and re-running `add` updates that one row, never piles
up duplicates). Never touches the card's body text, never writes to any other table.

Usage:
    python3 experience_log.py add <card.md> [<card2.md> ...]
    python3 experience_log.py list
    python3 experience_log.py find <term>

No network. No git operations. Reads only files passed on the command line (+ writes
only to the sqlite DB at store.DEFAULT_DB_PATH, same as every other collector in this repo).
"""
import argparse
import sys
from pathlib import Path

import yaml

import store

REQUIRED_FIELDS = (
    "id", "date_event", "date_collected", "source_type", "role", "place", "tag",
)


def parse_front_matter(card_path: Path) -> dict:
    """Splits a card on the leading `---\\n...\\n---` YAML fence and returns the parsed
    dict. Raises ValueError with a clear message if the fence is missing/malformed --
    fail loud rather than silently skip a malformed card."""
    text = card_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{card_path}: does not start with a '---' front-matter fence")
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        raise ValueError(f"{card_path}: no closing '---' fence found")
    fm_text = "\n".join(lines[1:end])
    data = yaml.safe_load(fm_text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{card_path}: front-matter did not parse to a mapping")
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"{card_path}: front-matter missing required field(s): {missing}")
    return data


def add_card(conn, card_path: Path) -> str:
    data = parse_front_matter(card_path)
    lenses = data.get("lenses") or {}
    store.insert_experience(
        conn,
        id=data["id"],
        date_event=str(data.get("date_event")) if data.get("date_event") is not None else None,
        date_collected=str(data.get("date_collected")) if data.get("date_collected") is not None else None,
        role=data.get("role"),
        place=data.get("place"),
        node_ids=data.get("node_ids") or [],
        tag=data.get("tag", "RELAYED-EXPERIENCE"),
        measurables=data.get("measurables") or [],
        politics=lenses.get("politics"),
        philosophy=lenses.get("philosophy"),
        structure=lenses.get("structure"),
        system=lenses.get("system"),
        ethics=lenses.get("ethics"),
        dag_gaps=data.get("dag_gaps") or [],
        ews_element=data.get("ews_element"),
        sprc=data.get("sprc"),
        proposed_indicators=data.get("proposed_indicators") or [],
        future_signal=data.get("future_signal"),
        path=str(card_path),
    )
    return data["id"]


def _print_rows(rows: list) -> None:
    if not rows:
        print("(no rows)")
        return
    for r in rows:
        print(f"{r['id']}  [{r['role']}]  {r['date_event']}  {r['place']}")
        print(f"    sprc={r['sprc']}  ews_element={r['ews_element']}  tag={r['tag']}")
        if r.get("future_signal"):
            print(f"    future_signal: {r['future_signal']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="parse card(s) front-matter into experience_log")
    p_add.add_argument("cards", nargs="+", type=Path)

    sub.add_parser("list", help="list all rows in experience_log")

    p_find = sub.add_parser("find", help="search experience_log for a term")
    p_find.add_argument("term")

    args = parser.parse_args(argv)
    conn = store.connect()

    if args.cmd == "add":
        for card_path in args.cards:
            if not card_path.exists():
                print(f"ERROR: {card_path} does not exist", file=sys.stderr)
                return 1
            card_id = add_card(conn, card_path)
            print(f"OK: {card_path} -> experience_log.id={card_id}")
        return 0

    if args.cmd == "list":
        _print_rows(store.query_experience(conn))
        return 0

    if args.cmd == "find":
        _print_rows(store.query_experience(conn, term=args.term))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
