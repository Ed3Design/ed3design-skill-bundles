#!/usr/bin/env python3
"""regenerate-counts.py — write authoritative bundle counts to README.md
and marketplace.json from filesystem reality.

Run via `python3 scripts/regenerate-counts.py` whenever skills/hooks/agents/
tools change. CI runs it in `--check` mode and fails if counts have drifted.

Usage:
    python3 scripts/regenerate-counts.py            # rewrite docs
    python3 scripts/regenerate-counts.py --check    # fail if drift exists
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUNDLES = sorted(
    p.name for p in REPO.iterdir()
    if p.is_dir()
    and not p.name.startswith(".")
    and (p / ".claude-plugin" / "plugin.json").exists()
)


def count_dir(bundle: str, subdir: str, pattern: str) -> int:
    base = REPO / bundle / subdir
    if not base.exists():
        return 0
    return len(list(base.rglob(pattern)))


def inventory():
    rows = []
    totals = {"skills": 0, "hooks": 0, "agents": 0, "tools": 0}
    for b in BUNDLES:
        skills = count_dir(b, "skills", "SKILL.md")
        hooks = count_dir(b, "hooks", "*.sh")
        agents = count_dir(b, "agents", "*.md")
        tools = count_dir(b, "tools", "*.py")
        rows.append({
            "bundle": b,
            "skills": skills,
            "hooks": hooks,
            "agents": agents,
            "tools": tools,
        })
        for k in totals:
            totals[k] += rows[-1][k]
    return rows, totals


def update_readme(rows, totals, check_only: bool) -> bool:
    """Returns True if the README was already in sync, False if drift existed."""
    path = REPO / "README.md"
    text = path.read_text()
    new_text = text

    # Update lead-paragraph: "N skills + M Python tools + K hooks + J sub-agents across L thematic bundles"
    lead_re = re.compile(
        r"(\d+) skills \+ (\d+) Python tools \+ (\d+) hooks \+ (\d+) sub-agents across (\d+) thematic bundles"
    )
    new_lead = (
        f"{totals['skills']} skills + {totals['tools']} Python tools + "
        f"{totals['hooks']} hooks + {totals['agents']} sub-agents across "
        f"{len(rows)} thematic bundles"
    )
    new_text = lead_re.sub(new_lead, new_text)

    # Update tail-paragraph: "**Total**: N skills + M hooks + K sub-agents + J tools"
    tail_re = re.compile(
        r"\*\*Total\*\*: (\d+) skills \+ (\d+) hooks \+ (\d+) sub-agents \+ (\d+) tools"
    )
    new_text = tail_re.sub(
        f"**Total**: {totals['skills']} skills + {totals['hooks']} hooks + "
        f"{totals['agents']} sub-agents + {totals['tools']} tools",
        new_text,
    )

    # Update per-bundle table rows
    for r in rows:
        # Match `| [\`bundle-name\`](./bundle-name/) | <skills> | ...` and replace counts
        row_re = re.compile(
            r"(\| \[`" + re.escape(r["bundle"]) + r"`\]\([^)]+\) \| )"
            r"(\d+)( \| )"
            r"(\*\*\d+\*\*|—)( \| )"
            r"((?:\*\*\d+\*\* \([^)]+\)|—))( \| )"
            r"(\d+|—)"
        )
        def repl(m, row=r):
            new_skills = str(row["skills"])
            new_hooks = f"**{row['hooks']}**" if row["hooks"] else "—"
            # Keep existing agent display (it has the agent name) — only update count
            agents_field = m.group(6)
            if row["agents"]:
                # Replace just the leading **N**
                agents_field = re.sub(r"\*\*\d+\*\*", f"**{row['agents']}**", agents_field)
            else:
                agents_field = "—"
            new_tools = str(row["tools"]) if row["tools"] else "—"
            return m.group(1) + new_skills + m.group(3) + new_hooks + m.group(5) + agents_field + m.group(7) + new_tools
        new_text = row_re.sub(repl, new_text)

    # Update inline-list under "Available plugins":
    # "- `bundle-name` — desc (N skills + M tools)"  etc.
    for r in rows:
        plugin_line_re = re.compile(
            r"(- `" + re.escape(r["bundle"]) + r"` — [^(]+\()(\d+) skills([^)]*)\)"
        )
        def plugin_repl(m, row=r):
            return f"{m.group(1)}{row['skills']} skills{m.group(3)})"
        new_text = plugin_line_re.sub(plugin_repl, new_text)

    if new_text == text:
        return True
    if not check_only:
        path.write_text(new_text)
    return False


def update_bundle_readmes(rows, check_only: bool) -> list[str]:
    """Update lead-paragraph counts inside each bundle's own README.md.
    Returns list of bundles where the README is/was stale."""
    stale = []
    for r in rows:
        bundle = r["bundle"]
        readme = REPO / bundle / "README.md"
        if not readme.exists():
            continue
        text = readme.read_text()
        new_text = text
        # Pattern: "N skills + M Python tools" / "N skills"
        # Replace the first occurrence in the lead paragraph (> blockquote OR top of file).
        # We target only the leading "N skills" mention, not all occurrences.
        lead_re = re.compile(
            r"^(> .*?)(\d+)( skills(?:\s*\+\s*\d+\s+(?:Python\s+)?(?:tools|hooks|sub-agents|agents))?)",
            re.MULTILINE,
        )
        def repl(m):
            return f"{m.group(1)}{r['skills']}{m.group(3)}"
        new_text = lead_re.sub(repl, new_text, count=1)
        if new_text != text:
            stale.append(bundle)
            if not check_only:
                readme.write_text(new_text)
    return stale


def update_bundle_plugin_json(rows, check_only: bool) -> list[str]:
    """Update the per-bundle .claude-plugin/plugin.json description's
    'N skills' phrase to match filesystem reality. Returns list of
    bundles where the manifest was/is stale."""
    stale = []
    for r in rows:
        bundle = r["bundle"]
        manifest = REPO / bundle / ".claude-plugin" / "plugin.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text())
        desc = data.get("description", "")
        # Replace the first "N skills" occurrence with reality.
        new_desc = re.sub(r"\b\d+ skills\b", f"{r['skills']} skills", desc, count=1)
        if new_desc != desc:
            stale.append(bundle)
            if not check_only:
                data["description"] = new_desc
                manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return stale


def update_marketplace(rows, totals, check_only: bool) -> bool:
    path = REPO / ".claude-plugin" / "marketplace.json"
    if not path.exists():
        return True
    data = json.loads(path.read_text())
    original = json.dumps(data, indent=2, ensure_ascii=False)

    # Rewrite top-level description to match reality
    data["description"] = (
        f"Engineering-discipline library for Claude Code: "
        f"{totals['skills']} skills, {totals['hooks']} hooks, "
        f"{totals['agents']} sub-agents, {totals['tools']} Python tools "
        f"across {len(rows)} thematic bundles. Empirically validated patterns."
    )

    # Rewrite per-plugin description: replace leading "N skills" count where present
    plugin_by_name = {r["bundle"]: r for r in rows}
    for plugin in data.get("plugins", []):
        row = plugin_by_name.get(plugin["name"])
        if not row:
            continue
        # Match "N skills" (the first occurrence) and replace with reality
        plugin["description"] = re.sub(
            r"\b\d+ skills\b",
            f"{row['skills']} skills",
            plugin["description"],
            count=1,
        )

    # Cross-check: plugin-array names should equal BUNDLES
    listed = {p["name"] for p in data.get("plugins", [])}
    expected = set(BUNDLES)
    if listed != expected:
        added = expected - listed
        removed = listed - expected
        msg = []
        if added:
            msg.append(f"plugins missing in marketplace.json: {sorted(added)}")
        if removed:
            msg.append(f"plugins listed but bundle-dir gone: {sorted(removed)}")
        print("⚠️  " + "; ".join(msg))

    new = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if new == original + "\n" if not original.endswith("\n") else new == original:
        return True
    if not check_only:
        path.write_text(new)
    return False


def main():
    check_only = "--check" in sys.argv
    rows, totals = inventory()

    print(f"Inventory ({len(rows)} bundles):")
    for r in rows:
        print(f"  {r['bundle']:24s}  {r['skills']:>2d} skills  "
              f"{r['hooks']:>2d} hooks  {r['agents']:>2d} agents  {r['tools']:>2d} tools")
    print(f"  {'TOTAL':24s}  {totals['skills']:>2d} skills  "
          f"{totals['hooks']:>2d} hooks  {totals['agents']:>2d} agents  {totals['tools']:>2d} tools")

    readme_ok = update_readme(rows, totals, check_only)
    market_ok = update_marketplace(rows, totals, check_only)
    bundle_stale = update_bundle_readmes(rows, check_only)
    plugin_json_stale = update_bundle_plugin_json(rows, check_only)

    if check_only:
        if readme_ok and market_ok and not bundle_stale and not plugin_json_stale:
            print("\n✅ README + marketplace.json + bundle READMEs + bundle plugin.json are in sync.")
            sys.exit(0)
        if bundle_stale:
            print(f"\n❌ Bundle READMEs drifted: {', '.join(bundle_stale)}")
        if plugin_json_stale:
            print(f"\n❌ Bundle plugin.json descriptions drifted: {', '.join(plugin_json_stale)}")
        print("\n❌ Counts drifted. Run `python3 scripts/regenerate-counts.py` to fix.")
        sys.exit(1)

    msg = []
    msg.append("README updated" if not readme_ok else "README already in sync")
    msg.append("marketplace.json updated" if not market_ok else "marketplace.json already in sync")
    if bundle_stale:
        msg.append(f"bundle READMEs updated: {', '.join(bundle_stale)}")
    print(f"\n✅ {'; '.join(msg)}.")


if __name__ == "__main__":
    main()
