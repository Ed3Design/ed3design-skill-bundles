#!/usr/bin/env python3
"""audit-private-skill-crosslinks.py — fail if a skill body references a
skill-name that does not resolve to anything a public user can install.

Motivation
----------
A dense skill catalog cross-references siblings. When a skill is curated
privately and only SOME siblings get published, the published ones can keep
back-ticked references to siblings that never shipped — e.g.
`legal-paragraph-recommendation-checklist`, `your-server-fastapi-iteration`.
A public user installing this bundle cannot resolve those references.

`audit-stale-draft-crosslinks.py` only catches `<name>-DRAFT` references.
This guard catches the broader class: any back-ticked token that LOOKS like a
skill name but resolves to neither (a) a skill in this repo, (b) a
`superpowers:` / `gsd:` prefixed skill, nor (c) the curated allow-list of
known non-skill tokens (CSS properties, libraries, CLI tools, transports,
renamed-historical names, Claude Code built-ins).

When a NEW legitimate external reference is introduced, add it to ALLOW below
with a one-word reason — that is the deliberate gate.

Usage:
    python3 scripts/audit-private-skill-crosslinks.py            # report
    python3 scripts/audit-private-skill-crosslinks.py --check    # hard-fail
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# A token that looks like a skill name: lowercase, >=2 hyphen-joined segments.
SKILL_TOKEN = re.compile(r"`([a-z][a-z0-9]+(?:-[a-z0-9]+){1,})`")

# Prefixes that resolve to external plugins (always allowed).
ALLOWED_PREFIXES = ("superpowers:", "gsd:")

# Known non-skill tokens that match the skill-name shape but are NOT
# cross-references to installable skills. Keep sorted; add with a reason.
ALLOW = {
    # CSS properties / web / programming concepts
    "flex-direction", "format-string",
    # Public skills in the sibling repo ed3design-engineering-bundles
    # (installable cross-repo; not present on this CI runner).
    "cad-api-scripting", "cad-construction", "fusion-mcp-bridge",
    "image-to-mesh-cad-workflow", "mechanical-design-principles",
    "victron-cerbo-modbus-device-onboarding", "bom-validation-workflow",
    "embedded-ui-svg-doc-from-source",
    # Python libraries / packages
    "python-docx", "python-telegram-bot", "poppler-utils",
    # MCP / transport / protocol terms
    "streamable-http", "my-mcp-server",
    # Generic placeholders produced by anonymization
    "your-app", "your-server", "example-project",
    # Claude Code built-ins (installable, not in any bundle)
    "update-config", "claude-in-chrome", "general-purpose",
    # Historical / renamed skill names referenced as provenance or worked
    # examples (the rename is the documented subject — not a live cross-ref).
    "asyncpg-decimal-test-shape",
    # Explicitly-labeled future "skill candidate" (not a shipped skill).
    "asyncpg-pool-mock-plumbing",
    # Repo's own tooling scripts (referenced in skill bodies).
    "regenerate-counts", "fix-yaml-frontmatter", "normalize-skill-descriptions",
    "audit-skill-descriptions", "audit-promotion-residue",
    "audit-stale-draft-crosslinks", "audit-private-skill-crosslinks",
    "test-tools-smoke", "test-hooks", "test-sql-injection-guard",
    "repair-deleted-i", "db-schema-inspector",
    # Tool / hook basenames referenced in prose.
    "vault-search", "img-preprocess", "diff-summary", "pre-push-bypass-audit",
    "commit-message-honesty", "pytest-venv-first", "cross-repo-state-inspect",
    "vault-first-prompt-detect", "post-session-skill-review-trigger",
    # Common compound English / doc terms that match the shape.
    "read-only", "first-person", "third-person", "cross-reference",
    "cross-references", "real-world", "when-to-use", "step-by-step",
    "end-to-end", "off-the-shelf", "package-lock", "code-of-conduct",
    "pull-request",
}


def local_skill_names() -> set[str]:
    names = set()
    for p in REPO.glob("*/skills/*/SKILL.md"):
        names.add(p.parent.name)
    return names


def audit() -> list[tuple[str, str]]:
    local = local_skill_names()
    findings: list[tuple[str, str]] = []  # (skill_path, ref)
    for p in sorted(REPO.glob("*/skills/*/SKILL.md")):
        skill = p.parent.name
        text = p.read_text()
        for ref in sorted(set(SKILL_TOKEN.findall(text))):
            if ref == skill or ref in local or ref in ALLOW:
                continue
            if any(f"{pref}{ref}" in text for pref in ALLOWED_PREFIXES):
                continue
            rel = p.relative_to(REPO)
            findings.append((str(rel), ref))
    return findings


def main() -> int:
    check = "--check" in sys.argv
    findings = audit()
    if not findings:
        print("✅ No unresolved skill cross-references.")
        return 0
    print(f"❌ {len(findings)} unresolved skill cross-reference(s):")
    for path, ref in findings:
        print(f"  {path}: `{ref}` — not a local skill, not superpowers:/gsd:, "
              f"not in ALLOW")
    print("\nFix: genericize the reference to prose, OR — if it is a legitimate "
          "external token (library, CLI, built-in) — add it to ALLOW in "
          "scripts/audit-private-skill-crosslinks.py with a reason.")
    return 1 if check else 0


if __name__ == "__main__":
    sys.exit(main())
