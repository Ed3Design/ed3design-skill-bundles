#!/usr/bin/env python3
"""audit-promotion-residue.py — fail when a GA-promoted skill still
carries pre-promotion residue: a `## Promotion checklist (DRAFT → GA)`
section, a `## When to promote out of STUB` section, a `## TDD task for
next` section, or stray narrative phrases like "(why DRAFT marker here)"
that no longer correspond to the skill's current GA state.

A GA skill is one whose `name:` field has no `-DRAFT` / `-STUB` suffix
and whose body has no `⚠️ DRAFT` banner (the existing audit-stale-draft-
crosslinks.py covers the back-ticked crosslink case; this script covers
the section-header + in-body-narrative case it doesn't see).

Usage:
    python3 scripts/audit-promotion-residue.py            # report
    python3 scripts/audit-promotion-residue.py --check    # hard-fail
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Section-header patterns that should NOT appear in a GA skill body.
# These are all pre-promotion templates that must be removed at GA time.
PROMOTION_SECTION_RE = re.compile(
    r"^##\s+(Promotion\s+checklist|When\s+to\s+promote\s+out\s+of\s+STUB|"
    r"TDD\s+task\s+for\s+next|Promotion\s+to\s+GA)\b",
    re.MULTILINE | re.IGNORECASE,
)

# Narrative phrases that imply the skill is still draft / pre-promoted.
# "why DRAFT marker here" only makes sense when there IS a DRAFT marker;
# a promoted skill no longer carries one, so the phrase reads wrong.
NARRATIVE_DRAFT_REF_RE = re.compile(
    r"why\s+DRAFT\s+marker\s+here|"
    r"why\s+this\s+is\s+still\s+DRAFT|"
    r"still\s+in\s+DRAFT\s+status",
    re.IGNORECASE,
)


def is_ga_skill(path: Path, text: str) -> bool:
    """A skill is GA when:
       1. directory name has no -DRAFT / -STUB suffix
       2. body has no `⚠️ DRAFT` banner
    """
    name = path.parent.name
    if name.endswith("-DRAFT") or name.endswith("-STUB"):
        return False
    if re.search(r"^>?\s*⚠️\s*\*?\*?DRAFT", text, re.MULTILINE):
        return False
    return True


def find_residue():
    findings = []
    for s in sorted(REPO.glob("*/skills/*/SKILL.md")):
        text = s.read_text()
        if not is_ga_skill(s, text):
            continue
        rel = s.relative_to(REPO)
        for m in PROMOTION_SECTION_RE.finditer(text):
            # Line number for diagnostics
            line = text[: m.start()].count("\n") + 1
            findings.append((rel, line, "promotion-section", m.group(0)))
        for m in NARRATIVE_DRAFT_REF_RE.finditer(text):
            line = text[: m.start()].count("\n") + 1
            findings.append((rel, line, "narrative-draft-ref", m.group(0)))
    return findings


def main():
    check_only = "--check" in sys.argv
    findings = find_residue()
    if findings:
        print(f"❌ Pre-promotion residue in GA skills: {len(findings)} item(s)")
        for rel, line, kind, snippet in findings:
            print(f"  {rel}:{line}  [{kind}]  {snippet[:80]}")
        if check_only:
            sys.exit(1)
    else:
        print("✅ No pre-promotion residue in GA skills.")


if __name__ == "__main__":
    main()
