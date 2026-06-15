#!/usr/bin/env python3
"""normalize-skill-descriptions.py — pragmatic mass-pass to bring SKILL.md
descriptions closer to spec:

1. Length: trim narrative tail (typically "Encodes…", "Real evidence…",
   "Auslöser…" sentences) so that descriptions stay under the spec
   recommendation. Conservative: only drops content AFTER the "Do NOT load…"
   sentence + content after `Encodes ` / `Real evidence`-prefixed sentences.

2. First-person: rewrite common 1st-person patterns to 3rd-person:
       I observed   → it has been observed
       we had to    → users have had to
       my default   → the natural default
       our session  → a session
       I            → Claude / the agent     (context-dependent — only
                       safe in narrative phrasing; otherwise flagged)

The script previews changes by default and writes only with `--write`.
Skills that cannot be safely auto-rewritten are flagged for manual review.

Goal: bring descriptions under 1024-char spec recommendation and remove
the most common 1st-person leakages, without losing trigger-match coverage.
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required.")


REPO = Path(__file__).resolve().parent.parent
LENGTH_TARGET = 1024


# Narrative-tail patterns: sentences (or trailing fragments) that add
# real-world-encoding context but are not required for trigger-matching.
# Match from the start of one of these markers until end of description.
TAIL_TRIM_RE = re.compile(
    r"(?:^|\.\s+)(Encodes |Real evidence from|Auslöser:|Pattern derived from practice:|Real-world evidence:).*?$",
    re.DOTALL | re.IGNORECASE,
)

# First-person replacements. Order matters — longer phrases first.
FIRST_PERSON_SUBS = [
    # Common verb-phrases
    (re.compile(r"\bI observed\b", re.I),     "experience showed"),
    (re.compile(r"\bI saw\b", re.I),          "the evidence showed"),
    (re.compile(r"\bI noticed\b", re.I),      "Claude noticed"),
    (re.compile(r"\bI realized\b", re.I),     "the realization was"),
    (re.compile(r"\bwe had to\b", re.I),      "the team had to"),
    (re.compile(r"\bwe found\b", re.I),       "evidence showed"),
    (re.compile(r"\bwe saw\b", re.I),         "evidence showed"),
    (re.compile(r"\bmy default\b", re.I),     "the natural default"),
    (re.compile(r"\bmy initial\b", re.I),     "the initial"),
    (re.compile(r"\bour session\b", re.I),    "a session"),
    (re.compile(r"\bour code\b", re.I),       "the code"),
    (re.compile(r"\bour\b", re.I),            "the"),
    # Standalone — risky, only safe in trailing narrative phrasing
    (re.compile(r"\b(I|i)\b"),                ""),   # delete bare-I (creates double-space, normalized below)
    (re.compile(r"\b(we|We|us|Us)\b"),        "Claude"),
    (re.compile(r"\b(my|My)\b"),              "the"),
    (re.compile(r"\b(me|Me)\b"),              "Claude"),
]

# After substitution: normalize whitespace + clean stranded punctuation
WS_NORMALIZE_RE = re.compile(r"  +")
STRANDED_PUNCT_RE = re.compile(r"\s+([,.;:!?])")


def trim_narrative_tail(desc: str) -> str:
    """Drop trailing 'Encodes...' / 'Real evidence...' phrasing."""
    # Find the last 'Do NOT load' sentence — content AFTER it can usually go
    m = list(re.finditer(r"Do NOT load[^.]*\.", desc))
    if m:
        tail_start = m[-1].end()
        head = desc[:tail_start].strip()
        tail = desc[tail_start:].strip()
        # Drop the tail entirely if it starts with a "narrative" marker
        if re.match(
            r"^(Encodes |Real evidence|Auslöser|Pattern derived|Real-world|This skill encodes)",
            tail, re.I,
        ):
            return head
        # Otherwise drop only the explicit marker-phrase patterns within
        return head + (" " + TAIL_TRIM_RE.sub("", tail) if tail else "")
    # No "Do NOT load" — only strip explicit marker-phrases
    return TAIL_TRIM_RE.sub("", desc)


def fix_first_person(desc: str) -> str:
    result = desc
    for pattern, repl in FIRST_PERSON_SUBS:
        result = pattern.sub(repl, result)
    result = WS_NORMALIZE_RE.sub(" ", result)
    result = STRANDED_PUNCT_RE.sub(r"\1", result)
    return result.strip()


def process_one(skill_path: Path, write: bool, target_length: int) -> dict:
    text = skill_path.read_text()
    fm_end = text.index("\n---\n", 4)
    fm_raw = text[4:fm_end]
    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError:
        return {"skipped": "yaml-parse-fail"}
    desc = fm.get("description", "")
    if not desc:
        return {"skipped": "no-description"}

    original = desc
    # Step 1: trim narrative tail
    trimmed = trim_narrative_tail(desc)
    # Step 2: first-person fix
    cleaned = fix_first_person(trimmed)

    changed = cleaned != original
    flag = None
    if changed and len(cleaned) > target_length:
        flag = "still-over-limit-after-trim"
    if not changed:
        return {"unchanged": True, "len": len(original)}

    if write:
        # Construct the new frontmatter block as text — replace just the
        # description body inside the block-scalar (preserve other fields)
        new_fm_dict = dict(fm)
        new_fm_dict["description"] = cleaned
        # Serialize as block-scalar for description to keep YAML valid
        # (use literal `|-` since values may contain ':' etc.)
        new_lines = []
        for key, val in new_fm_dict.items():
            if key == "description":
                new_lines.append("description: |-")
                for line in cleaned.splitlines() or [cleaned]:
                    new_lines.append(f"  {line}")
            else:
                new_lines.append(f"{key}: {val}")
        new_fm_block = "\n".join(new_lines)
        new_text = text[:4] + new_fm_block + "\n" + text[fm_end:]
        skill_path.write_text(new_text)

    return {
        "old_len": len(original),
        "new_len": len(cleaned),
        "delta": len(original) - len(cleaned),
        "flag": flag,
    }


def main():
    write = "--write" in sys.argv
    target = LENGTH_TARGET
    if "--target" in sys.argv:
        idx = sys.argv.index("--target")
        target = int(sys.argv[idx + 1])

    skills = sorted(REPO.glob("*/skills/*/SKILL.md"))
    stats = {"changed": 0, "unchanged": 0, "still_over": 0, "skipped": 0}
    flagged = []
    print(f"[{'WRITE' if write else 'DRY-RUN'}] Target ≤ {target} chars")
    print()
    for s in skills:
        r = process_one(s, write, target)
        if "skipped" in r:
            stats["skipped"] += 1
            continue
        if r.get("unchanged"):
            stats["unchanged"] += 1
            continue
        stats["changed"] += 1
        if r.get("flag") == "still-over-limit-after-trim":
            stats["still_over"] += 1
            flagged.append((r["new_len"], s))
            print(f"  ⚠  {r['old_len']:4d} → {r['new_len']:4d}  STILL OVER  {s.parent.parent.parent.name}/{s.parent.name}")
        else:
            print(f"  ✓  {r['old_len']:4d} → {r['new_len']:4d}  Δ-{r['delta']:4d}  {s.parent.parent.parent.name}/{s.parent.name}")

    print()
    print(f"Changed: {stats['changed']}  unchanged: {stats['unchanged']}  still-over: {stats['still_over']}  skipped: {stats['skipped']}")
    if flagged:
        print(f"\nFlagged for manual review ({len(flagged)} still over limit after auto-trim):")
        for n, s in sorted(flagged, reverse=True)[:10]:
            print(f"  {n}  {s.parent.parent.parent.name}/{s.parent.name}")


if __name__ == "__main__":
    main()
