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
                stale.append((s, candidate))
    return stale


def main():
    check_only = "--check" in sys.argv
    stale = find_stale_crosslinks()
    if stale:
        print(f"Stale -DRAFT crosslinks (GA skill exists, ref still uses -DRAFT suffix): {len(stale)}")
        for s, c in stale:
            rel = s.relative_to(REPO)
            print(f"  {rel}  →  `{c}-DRAFT`")
        if check_only:
            sys.exit(1)
    else:
        print("✅ No stale -DRAFT crosslinks.")


if __name__ == "__main__":
    main()
