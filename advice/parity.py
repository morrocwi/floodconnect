"""Official parity -- P-D, design section G ("alway EQUAL TO OR STRICTER than the
official Thai guidance... never weaker").

For each `tag: OFFICIAL` row in `advice/official_guidance.yaml`, finds a
`advice/preparedness_ladder.yaml` step carrying the SAME `action_key` and
compares colour rank against that row's own `trigger_colour`:

  - a matching step at the SAME rank         -> EQUAL
  - a matching step at an EARLIER rank        -> STRICTER
  - a matching step at a LATER rank           -> WEAKER   (a real defect)
  - no matching step anywhere in the ladder   -> MISSING  (a real defect)

2026-10-05: every row now also carries `source_class`
(`OFFICIAL_TH` or `GENERAL`, see `official_guidance.yaml`'s own header) --
`build_parity_table()`/`summarize()` report EACH class's own EQUAL/STRICTER/
WEAKER/MISSING/OPEN counts, never pooled into one undifferentiated total, so a
regression in either class is visible on its own. The hard rule (no WEAKER, no
MISSING) applies to BOTH classes identically -- a GENERAL item is never allowed
to be weaker than what this repo actually does, same as an OFFICIAL_TH one.

`tag: OPEN` rows are listed separately and never produce a MISSING/WEAKER verdict
(the task's own rule: "An official item we cannot source is OPEN; do not invent
it" -- it cannot be a defect against a step this repo never had a chance to be
compared to).

`build_parity_table()` returns the structured rows (for tests); `render_markdown()`
renders `advice/PARITY.md`; `main()` (also reachable as `python -m advice.parity`)
regenerates that file on disk.
"""
from __future__ import annotations

import functools
import pathlib
from typing import Any

import advice.ladder as ladder

_HERE = pathlib.Path(__file__).resolve().parent
_GUIDANCE_PATH = _HERE / "official_guidance.yaml"
_PARITY_MD_PATH = _HERE / "PARITY.md"

_RANK = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}

VERDICT_EQUAL = "EQUAL"
VERDICT_STRICTER = "STRICTER"
VERDICT_WEAKER = "WEAKER"
VERDICT_MISSING = "MISSING"
VERDICT_OPEN = "OPEN"


@functools.lru_cache(maxsize=1)
def _guidance_rows() -> list[dict[str, Any]]:
    import yaml
    with open(_GUIDANCE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
    return data


def _best_matching_step(action_key: str, steps: list[dict[str, Any]]) -> "dict[str, Any] | None":
    """Among every ladder step whose `action_keys` contains `action_key`, the one
    at the EARLIEST (strictest) colour rank -- so a key implemented at both YELLOW
    and ORANGE is judged by its strongest (earliest) occurrence, never its
    weakest."""
    candidates = [s for s in steps if action_key in (s.get("action_keys") or [])]
    if not candidates:
        return None
    return min(candidates, key=lambda s: _RANK.get(s["colour"], 99))


def build_parity_table() -> list[dict[str, Any]]:
    """One row per `official_guidance.yaml` entry -- `{id, agency, tag,
    source_class, action_key, trigger_colour, step_id, step_colour, verdict}`.
    `tag: OPEN` rows get `verdict: OPEN`, `source_class: None`, and no step
    lookup (never a MISSING/WEAKER verdict for an un-sourceable item).
    `source_class` (added so official parity covers two source classes) is `OFFICIAL_TH` or `GENERAL` for every
    `tag: OFFICIAL` row -- see `official_guidance.yaml`'s own header for what
    each means; the EQUAL/STRICTER/WEAKER/MISSING comparison rule itself is
    IDENTICAL for both classes (never a looser bar for GENERAL)."""
    steps = ladder.all_steps()
    out: list[dict[str, Any]] = []
    for row in _guidance_rows():
        if row.get("tag") == "OPEN":
            out.append({
                "id": row["id"], "agency": row.get("agency"), "tag": "OPEN",
                "source_class": None, "action_key": None, "trigger_colour": None,
                "step_id": None, "step_colour": None, "verdict": VERDICT_OPEN,
            })
            continue
        source_class = row.get("source_class")
        action_keys = row.get("action_keys") or []
        trigger_colour = row.get("trigger_colour")
        trigger_rank = _RANK.get(trigger_colour, 99)
        for action_key in action_keys or [None]:
            if action_key is None:
                out.append({
                    "id": row["id"], "agency": row.get("agency"), "tag": "OFFICIAL",
                    "source_class": source_class, "action_key": None,
                    "trigger_colour": trigger_colour,
                    "step_id": None, "step_colour": None, "verdict": VERDICT_MISSING,
                })
                continue
            best = _best_matching_step(action_key, steps)
            if best is None:
                verdict = VERDICT_MISSING
                step_id = step_colour = None
            else:
                step_colour = best["colour"]
                step_rank = _RANK.get(step_colour, 99)
                step_id = best["id"]
                if step_rank < trigger_rank:
                    verdict = VERDICT_STRICTER
                elif step_rank == trigger_rank:
                    verdict = VERDICT_EQUAL
                else:
                    verdict = VERDICT_WEAKER
            out.append({
                "id": row["id"], "agency": row.get("agency"), "tag": "OFFICIAL",
                "source_class": source_class, "action_key": action_key,
                "trigger_colour": trigger_colour,
                "step_id": step_id, "step_colour": step_colour, "verdict": verdict,
            })
    return out


def summarize(table: "list[dict[str, Any]] | None" = None) -> dict[str, int]:
    """{EQUAL: n, STRICTER: n, WEAKER: n, MISSING: n, OPEN: n} counts, pooled
    across both classes (unchanged shape, for any existing caller)."""
    table = table if table is not None else build_parity_table()
    counts = {VERDICT_EQUAL: 0, VERDICT_STRICTER: 0, VERDICT_WEAKER: 0,
              VERDICT_MISSING: 0, VERDICT_OPEN: 0}
    for row in table:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return counts


def summarize_by_class(table: "list[dict[str, Any]] | None" = None) -> dict[str, dict[str, int]]:
    """`{"OFFICIAL_TH": {...}, "GENERAL": {...}}`, each the same
    `{EQUAL, STRICTER, WEAKER, MISSING}` shape as `summarize()` but counted
    separately per `source_class` -- `OPEN` rows have no class (nothing was
    fetched) and are reported once, under a third `"OPEN"` key, rather than
    split arbitrarily between the two."""
    table = table if table is not None else build_parity_table()
    out: dict[str, dict[str, int]] = {
        "OFFICIAL_TH": {VERDICT_EQUAL: 0, VERDICT_STRICTER: 0, VERDICT_WEAKER: 0, VERDICT_MISSING: 0},
        "GENERAL": {VERDICT_EQUAL: 0, VERDICT_STRICTER: 0, VERDICT_WEAKER: 0, VERDICT_MISSING: 0},
        "OPEN": {VERDICT_OPEN: 0},
    }
    for row in table:
        if row["verdict"] == VERDICT_OPEN:
            out["OPEN"][VERDICT_OPEN] += 1
            continue
        cls = row.get("source_class") or "OFFICIAL_TH"
        out.setdefault(cls, {VERDICT_EQUAL: 0, VERDICT_STRICTER: 0, VERDICT_WEAKER: 0, VERDICT_MISSING: 0})
        out[cls][row["verdict"]] = out[cls].get(row["verdict"], 0) + 1
    return out


def render_markdown(table: "list[dict[str, Any]] | None" = None) -> str:
    table = table if table is not None else build_parity_table()
    counts = summarize(table)
    by_class = summarize_by_class(table)
    lines = [
        "# FloodConnect M8 official-parity table",
        "",
        "Generated by `advice/parity.py` from `advice/official_guidance.yaml` x "
        "`advice/preparedness_ladder.yaml`. See `advice/parity.py`'s own module "
        "docstring for the EQUAL/STRICTER/WEAKER/MISSING/OPEN rule.",
        "",
        f"**Counts (pooled):** EQUAL={counts[VERDICT_EQUAL]} STRICTER={counts[VERDICT_STRICTER]} "
        f"WEAKER={counts[VERDICT_WEAKER]} MISSING={counts[VERDICT_MISSING]} "
        f"OPEN={counts[VERDICT_OPEN]}",
        "",
        "**Counts by class** (two source classes -- no WEAKER, no MISSING for either class is the hard rule):",
        "",
        f"- OFFICIAL_TH: EQUAL={by_class['OFFICIAL_TH'][VERDICT_EQUAL]} "
        f"STRICTER={by_class['OFFICIAL_TH'][VERDICT_STRICTER]} "
        f"WEAKER={by_class['OFFICIAL_TH'][VERDICT_WEAKER]} "
        f"MISSING={by_class['OFFICIAL_TH'][VERDICT_MISSING]}",
        f"- GENERAL: EQUAL={by_class['GENERAL'][VERDICT_EQUAL]} "
        f"STRICTER={by_class['GENERAL'][VERDICT_STRICTER]} "
        f"WEAKER={by_class['GENERAL'][VERDICT_WEAKER]} "
        f"MISSING={by_class['GENERAL'][VERDICT_MISSING]}",
        f"- OPEN (unfetchable, either class): {by_class['OPEN'][VERDICT_OPEN]}",
        "",
        "| id | agency | source_class | action_key | trigger_colour | step_id | step_colour | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in table:
        lines.append(
            f"| {row['id']} | {row['agency'] or ''} | {row.get('source_class') or ''} | "
            f"{row['action_key'] or ''} | "
            f"{row['trigger_colour'] or ''} | {row['step_id'] or ''} | "
            f"{row['step_colour'] or ''} | {row['verdict']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    table = build_parity_table()
    _PARITY_MD_PATH.write_text(render_markdown(table), encoding="utf-8")


if __name__ == "__main__":
    main()
