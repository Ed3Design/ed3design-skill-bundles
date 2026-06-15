#!/usr/bin/env python3
"""repair-deleted-i.py — repair user-trigger phrases where the previous
first-person purge over-deleted bare `I`.

The normalize-skill-descriptions.py pass (commit 244da5d) included a
regex rule that deleted bare `I` to remove first-person voice. This was
correct for narrative text but WRONG inside quoted user-trigger phrases
like `"I want X"`, `"I don't know where to start"`, `"how do I review
these 200 commits"` — these are verbatim phrases the SKILL is supposed
to recognize from the user, not Claude's own perspective.

This script restores `I` where:
  - the bare-I-deletion left a tell-tale grammatical fragment like
    `" want", " need", " don't", "how do review", " only see", ...`
  - the deletion is clearly inside a quoted-string trigger-phrase context

Targeted, idempotent, single-purpose. Run after the over-normalization
to restore trigger-coverage without re-introducing first-person voice
in the surrounding narrative.

Usage:
    python3 scripts/repair-deleted-i.py            # dry-run
    python3 scripts/repair-deleted-i.py --write    # apply
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required.")


REPO = Path(__file__).resolve().parent.parent

# Restore `I ` (capital-I + space) before specific 1st-person verbs at
# the start of a quoted trigger phrase. The regex looks for:
#   `"` + space + <verb> + word-boundary
# and replaces the space with `I `. Word-list is intentionally narrow:
# only verbs and contractions that strongly imply first-person speaker.
QUOTED_VERBS = r"(want|need|am|have|haven't|don't|can't|won't|implemented|noticed|observed|see|saw|only|never|do|can|will|just|tried)"
QUOTED_REPAIR = re.compile(r'(["“]) (' + QUOTED_VERBS + r'\b)', re.IGNORECASE)

# Restore `I` inside "how do <verb>" question patterns:
#   "how do review these 200 commits"  →  "how do I review these 200 commits"
HOW_DO_VERBS = r"(review|need|want|debug|fix|handle|tackle|build|test|track|find|know|tell)"
HOW_DO_REPAIR = re.compile(r"\b(how do) (" + HOW_DO_VERBS + r"\b)", re.IGNORECASE)

# Restore `I` inside `a "<verb> to do" list` patterns —
# the bare-I deletion produced `a " want to do all of these"`
A_QUOTED_REPAIR = re.compile(r'\b(a) (["“]) (' + QUOTED_VERBS + r'\b)', re.IGNORECASE)

# Restore `I` before contractions inside quotes:
#   "'m working on..."   →  "I'm working on..."
#   "'ve been..."        →  "I've been..."
CONTRACTION_REPAIR = re.compile(r'(["“])(\'(m|ve|d|ll)\b)')

# Restore `I` for `" know"` / `" knew"` at quoted-string starts
KNOW_REPAIR = re.compile(r'(["“]) (know|knew|knows)\b')

# Revert overly-aggressive "me → Claude" substitution in user-trigger-phrases:
#   "show Claude the complete output"  →  "show me the complete output"
#   "make Claude a plan"               →  "make me a plan"
#   "help Claude think"                →  "help me think"
#   "tell Claude X"                    →  "tell me X"
#   "give Claude X"                    →  "give me X"
ME_REVERT = re.compile(r'\b(show|make|help|tell|give|teach|explain to|walk) Claude\b')


def repair(text: str) -> tuple[str, int]:
    """Return (repaired_text, n_replacements)."""
    n = 0

    def quoted_replacer(m):
        nonlocal n
        n += 1
        return f"{m.group(1)}I {m.group(2)}"

    def how_do_replacer(m):
        nonlocal n
        n += 1
        return f"{m.group(1)} I {m.group(2)}"

    def a_quoted_replacer(m):
        nonlocal n
        n += 1
        return f"{m.group(1)} {m.group(2)}I {m.group(3)}"

    def contraction_replacer(m):
        nonlocal n
        n += 1
        # "'m  →  "I'm
        return f"{m.group(1)}I{m.group(2)}"

    def know_replacer(m):
        nonlocal n
        n += 1
        return f"{m.group(1)}I {m.group(2)}"

    def me_revert_replacer(m):
        nonlocal n
        n += 1
        return f"{m.group(1)} me"

    # Apply A-quoted FIRST so it doesn't conflict with bare quoted
    result = A_QUOTED_REPAIR.sub(a_quoted_replacer, text)
    result = QUOTED_REPAIR.sub(quoted_replacer, result)
    result = HOW_DO_REPAIR.sub(how_do_replacer, result)
    result = CONTRACTION_REPAIR.sub(contraction_replacer, result)
    result = KNOW_REPAIR.sub(know_replacer, result)
    result = ME_REVERT.sub(me_revert_replacer, result)
    return result, n


def process(s: Path, write: bool) -> dict:
    text = s.read_text()
    fm_end = text.index("\n---\n", 4)
    fm_raw = text[4:fm_end]
    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError:
        return {"skipped": "yaml"}
    desc = fm.get("description", "")
    if not desc:
        return {"skipped": "no-desc"}

    new_desc, n = repair(desc)
    if n == 0:
        return {"unchanged": True}

    if write:
        # Rewrite frontmatter with the new description as block-scalar
        new_lines = []
        for key, val in fm.items():
            if key == "description":
                new_lines.append("description: |-")
                for line in new_desc.splitlines() or [new_desc]:
                    new_lines.append(f"  {line}")
            else:
                new_lines.append(f"{key}: {val}")
        new_fm = "\n".join(new_lines)
        new_text = text[:4] + new_fm + "\n" + text[fm_end:]
        s.write_text(new_text)

    return {"replaced": n, "new_len": len(new_desc)}


def main():
    write = "--write" in sys.argv
    total = 0
    files_touched = 0
    print(f"[{'WRITE' if write else 'DRY-RUN'}]")
    for s in sorted(REPO.glob("*/skills/*/SKILL.md")):
        r = process(s, write)
        if r.get("replaced"):
            total += r["replaced"]
            files_touched += 1
            print(f"  +{r['replaced']:2d}  {s.parent.parent.parent.name}/{s.parent.name}")
    print()
    print(f"Total restorations: {total} across {files_touched} skills")


if __name__ == "__main__":
    main()
