#!/usr/bin/env python3
"""audit-skill-descriptions.py — find skills whose description violates
Claude Code skill-frontmatter conventions:

1. Length > 1024 chars (spec recommendation, validator doesn't enforce)
2. First-person language ("I", "we", "my", "our", "us", "me") — descriptions
   are injected into system prompts and must be third-person.

Run via `python3 scripts/audit-skill-descriptions.py` for a report.
Run with `--check` to fail CI on any violation.

The script does NOT auto-fix — descriptions are semantic content that
benefit from human / Claude-assisted rewriting.
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required.")


REPO = Path(__file__).resolve().parent.parent
FIRST_PERSON = re.compile(r"\b(I|we|my|our|us|me)\b")
LENGTH_LIMIT = 1024


def audit():
    overlong = []
    first_person = []
    for s in sorted(REPO.glob("*/skills/*/SKILL.md")):
        text = s.read_text()
        try:
            fm_end = text.index("\n---\n", 4)
            fm = yaml.safe_load(text[4:fm_end])
        except (ValueError, yaml.YAMLError):
            continue
        desc = fm.get("description", "")
        if len(desc) > LENGTH_LIMIT:
            overlong.append((s, len(desc), desc))
        fp = FIRST_PERSON.findall(desc)
        if fp:
            first_person.append((s, fp, desc))
    return overlong, first_person


def main():
    check_only = "--check" in sys.argv
    overlong, first_person = audit()
    print(f"== Description-length audit ==")
    print(f"Over {LENGTH_LIMIT} chars: {len(overlong)} skills")
    for s, n, d in overlong[:20]:
        print(f"  {n:4d}  {s.parent.parent.parent.name}/{s.parent.name}")
    if len(overlong) > 20:
        print(f"  ... and {len(overlong) - 20} more")

    print()
    print(f"== First-person audit (description must be third-person) ==")
    print(f"Skills with first-person markers: {len(first_person)}")
    for s, fp, d in first_person[:20]:
        unique_fp = sorted(set(fp))
        print(f"  {unique_fp}  {s.parent.parent.parent.name}/{s.parent.name}")
    if len(first_person) > 20:
        print(f"  ... and {len(first_person) - 20} more")

    if check_only and (overlong or first_person):
        print()
        print("❌ Description audit failed.")
        sys.exit(1)
    elif check_only:
        print("\n✅ All descriptions within spec.")


if __name__ == "__main__":
    main()
