#!/usr/bin/env python3
"""
fix-yaml-frontmatter.py — convert broken inline `description:` values
to YAML block-scalars so the frontmatter parses cleanly.

Root-cause of breakage (15.06.2026 audit): many SKILL.md files have
single-line `description:` values containing embedded `: ` sequences
(colon + space) — e.g. `description: Use when SELECT * FROM ...`.
YAML interprets the embedded `: ` as a nested key, throwing
"mapping values are not allowed here".

Fix: rewrite `description: <inline>` → `description: |-\n  <inline>`
(literal block scalar, no trailing newline). The value is preserved
character-for-character; only the indentation marker changes.

Usage:
    python3 scripts/fix-yaml-frontmatter.py           # dry-run, report only
    python3 scripts/fix-yaml-frontmatter.py --write   # apply changes
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
DESCRIPTION_INLINE_RE = re.compile(r"^description: (.+)$", re.MULTILINE)


def parse_frontmatter(text: str):
    """Return (raw, start_idx, end_idx) of frontmatter block or None."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return m.group(1), m.start(), m.end()


def is_yaml_valid(raw: str) -> bool:
    try:
        yaml.safe_load(raw)
        return True
    except yaml.YAMLError:
        return False


def rewrite_description_to_block_scalar(raw: str) -> str:
    """Convert inline `description: ...` to `description: |-\n  ...`.

    Only acts when the description value contains a problematic
    pattern (colon-space, leading ${...}, etc.). Leaves clean
    descriptions alone.
    """
    def replacer(match):
        value = match.group(1)
        # Indent every line by 2 spaces (block-scalar indentation)
        indented = "\n".join(f"  {line}" for line in value.splitlines() or [value])
        if not indented.startswith("  "):
            indented = f"  {value}"
        return f"description: |-\n{indented}"

    return DESCRIPTION_INLINE_RE.sub(replacer, raw, count=1)


def process_file(path: Path, write: bool) -> str:
    """Return status: 'ok', 'fixed', 'still-broken', 'no-frontmatter'."""
    text = path.read_text()
    parsed = parse_frontmatter(text)
    if not parsed:
        return "no-frontmatter"
    raw, start, end = parsed

    if is_yaml_valid(raw):
        return "ok"

    new_raw = rewrite_description_to_block_scalar(raw)
    if not is_yaml_valid(new_raw):
        return "still-broken"

    if write:
        new_text = text[:start] + f"---\n{new_raw}\n---\n" + text[end:]
        path.write_text(new_text)

    return "fixed"


def main():
    write = "--write" in sys.argv
    skills = sorted(Path(".").glob("*/skills/*/SKILL.md"))
    stats = {"ok": 0, "fixed": 0, "still-broken": 0, "no-frontmatter": 0}
    still_broken_paths = []
    for s in skills:
        status = process_file(s, write)
        stats[status] += 1
        if status == "still-broken":
            still_broken_paths.append(s)

    mode = "WRITE" if write else "DRY-RUN"
    print(f"[{mode}] Processed {len(skills)} skills")
    print(f"  ok:             {stats['ok']}")
    print(f"  fixed:          {stats['fixed']}")
    print(f"  still-broken:   {stats['still-broken']}")
    print(f"  no-frontmatter: {stats['no-frontmatter']}")
    if still_broken_paths:
        print("\nSkills still broken after description-only fix (need manual review):")
        for p in still_broken_paths:
            print(f"  {p}")
        sys.exit(1)


if __name__ == "__main__":
    main()
