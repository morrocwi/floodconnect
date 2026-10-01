#!/usr/bin/env python3
"""CLI/public facade for the DSVA v0.9 finite obstruction + audited meaning kernel."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from dsva_kernel import *  # re-export stable public constants
from dsva_kernel import evaluate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a finite DSVA v0.9 decision snapshot"
    )
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    try:
        scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    except Exception as exc:
        result = {
            "status": STATUS_HOLD,
            "selected_action": None,
            "obstructions": [f"INPUT_FILE_ERROR:{type(exc).__name__}:{exc}"],
        }
    else:
        result = evaluate(scenario)
    json.dump(
        result,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
