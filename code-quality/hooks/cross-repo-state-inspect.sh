#!/bin/bash
# cross-repo-state-inspect.sh
#
# PreToolUse-Hook (Bash). Warnt vor blind-`git add .` / `git add -A` / `git commit -a`
# in Mono-Repos mit untracked Subdirs — Skill `cross-repo-state-inspection-before-commit`.
#
# Verhalten: warn-only (exit 0). Audit nicht nötig (transient).
#
# Source: ed3design-skill-bundles/code-quality

set -u

# Read PreToolUse-JSON from stdin
input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Match blind-add patterns
if echo "$command" | grep -qE '\bgit\s+add\s+(\.|--?[Aa])\b|\bgit\s+commit\s+--?a\b'; then
    echo "⚠️  cross-repo-state-inspect: '$command' enthält blind-add Pattern." >&2
    echo "    Risiko in Mono-Repo: untracked Subdirs / _shared-Mods / Subprojekt-Files" >&2
    echo "    werden versehentlich mit-committed." >&2
    echo "    Empfehlung: 'git status --short' VOR add lesen, dann explizite File-Liste." >&2
    echo "    Skill: cross-repo-state-inspection-before-commit" >&2
fi

exit 0
