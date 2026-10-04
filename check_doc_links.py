#!/usr/bin/env python3
"""Find dangling relative .md links (link-check, not a general validator).

Scans every tracked *.md file for markdown links `[text](path)` whose path is
relative (no scheme, not an anchor-only `#frag`) and reports any that do not
resolve to a real file relative to the linking file's own directory. Does not
follow http(s) links, mailto:, or check in-page anchors.
"""
import re, subprocess, sys
from pathlib import Path

LINK_RE = re.compile(r"\]\(([^)]+)\)")
files = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True, check=True).stdout.splitlines()
missing = []
for f in files:
    src = Path(f)
    for target in LINK_RE.findall(src.read_text(encoding="utf-8", errors="replace")):
        target = target.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (src.parent / target).exists():
            missing.append(f"{f} -> {target}")
if missing:
    print(f"{len(missing)} dangling relative .md link(s):")
    for m in missing:
        print(" ", m)
    sys.exit(1)
print("0 dangling relative .md links found.")
