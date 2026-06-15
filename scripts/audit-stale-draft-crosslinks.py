#!/usr/bin/env python3
"""audit-stale-draft-crosslinks.py — fail if any skill body references
`<name>-DRAFT` while a GA-named `<name>` skill exists in the repo.

Some -DRAFT references are legitimate (meta-skills like
`skill-tdd-promotion-workflow` discuss the DRAFT lifecycle). The check
only flags references where the unsuffixed GA equivalent EXISTS as an
actual skill directory — those are stale crosslinks pointing at a
historical DRAFT state.

Usage:
    python3 scripts/audit-stale-draft-crosslinks.py            # report
    python3 scripts/audit-stale-draft-crosslinks.py --check    # hard-fail
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DRAFT_REF_RE = re.compile(r"`([a-z][a-z0-9-]+)-DRAFT`")


def find_stale_crosslinks():
    """Two kinds of stale -DRAFT crosslinks:
    1. The GA-named sibling exists in the repo → the reference is left-over from
       a pre-promotion state and should drop the suffix.
    2. Neither the DRAFT nor the GA form exists in this repo → the reference
       points at a non-shipped skill and reads as an unfinished catalog item.
       Mark these explicitly so they can be reworded or removed.
    """
    ga_skills = {
        s.parent.name
        for s in REPO.glob("*/skills/*/SKILL.md")
        if not s.parent.name.endswith("-DRAFT")
        and not s.parent.name.endswith("-STUB")
    }
    stale = []
    for s in sorted(REPO.glob("*/skills/*/SKILL.md")):
        text = s.read_text()
        for m in DRAFT_REF_RE.finditer(text):
            candidate = m.group(1)
            if candidate in ga_skills:
                stale.append((s, candidate, "GA-exists"))
            else:
                stale.append((s, candidate, "non-shipped"))
    return stale


def main():
    check_only = "--check" in sys.argv
    stale = find_stale_crosslinks()
    if stale:
        ga_exists = [(s, c) for s, c, kind in stale if kind == "GA-exists"]
        non_shipped = [(s, c) for s, c, kind in stale if kind == "non-shipped"]
        if ga_exists:
            print(f"❌ Stale -DRAFT crosslinks (GA sibling exists — drop the suffix): {len(ga_exists)}")
            for s, c in ga_exists:
                print(f"  {s.relative_to(REPO)}  →  `{c}-DRAFT`")
        if non_shipped:
            print(f"❌ -DRAFT crosslinks to non-shipped skills (reword or remove): {len(non_shipped)}")
            for s, c in non_shipped:
                print(f"  {s.relative_to(REPO)}  →  `{c}-DRAFT`  (not in repo)")
        if check_only:
            sys.exit(1)
    else:
        print("✅ No stale -DRAFT crosslinks.")


if __name__ == "__main__":
    main()
