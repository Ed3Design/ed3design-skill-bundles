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

# Quoted strings inside a description are verbatim user-trigger-phrases
# and may legitimately contain first-person speech (e.g. "I want X",
# "how do I review 200 commits"). The audit must check first-person
# voice in the SURROUNDING NARRATIVE only, not inside trigger-quotes.
QUOTED_STRING = re.compile(r'"[^"]*"|"[^"]*"|"[^"]*"')


def strip_quoted(text: str) -> str:
    """Replace all `"..."` and curly-quoted segments with empty space —
    they're verbatim user phrases, not narrative voice."""
    return QUOTED_STRING.sub(" ", text)


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
        # Scan only the narrative portion (quoted user-phrases excluded)
        narrative = strip_quoted(desc)
        fp = FIRST_PERSON.findall(narrative)
        if fp:
            first_person.append((s, fp, desc))
    return overlong, first_person


def main():
    # CLI flags:
    #   --check-first-person   hard-fail if any first-person marker (default for CI)
    #   --check-length         hard-fail if any description over 1024 chars
    #   --check                hard-fail on BOTH (legacy combined flag — note: length
    #                          is currently soft-warn in CI; using --check locally
    #                          may fail until the over-length backlog is cleared)
    check_first = "--check-first-person" in sys.argv or "--check" in sys.argv
    check_length = "--check-length" in sys.argv or "--check" in sys.argv

    overlong, first_person = audit()
    print(f"== Description-length audit ==")
    print(f"Over {LENGTH_LIMIT} chars: {len(overlong)} skills")
    for s, n, d in overlong[:20]:
        print(f"  {n:4d}  {s.parent.parent.parent.name}/{s.parent.name}")
    if len(overlong) > 20:
        print(f"  ... and {len(overlong) - 20} more")

    print()
    print(f"== First-person audit (description must be third-person, excluding quoted user-trigger-phrases) ==")
    print(f"Skills with first-person markers in narrative: {len(first_person)}")
    for s, fp, d in first_person[:20]:
        unique_fp = sorted(set(fp))
        print(f"  {unique_fp}  {s.parent.parent.parent.name}/{s.parent.name}")
    if len(first_person) > 20:
        print(f"  ... and {len(first_person) - 20} more")

    fail = False
    if check_first and first_person:
        print(f"\n❌ first-person violations: {len(first_person)} (HARD fail)")
        fail = True
    if check_length and overlong:
        print(f"\n❌ length violations: {len(overlong)} (HARD fail with --check-length)")
        fail = True

    if fail:
        sys.exit(1)
    if check_first or check_length:
        print("\n✅ Description audit passed.")


if __name__ == "__main__":
    main()
