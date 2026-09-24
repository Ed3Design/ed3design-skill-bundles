#!/bin/bash
PY=$(command -v python3 || command -v python)
# cross-repo-state-inspect.sh
#
# PreToolUse-Hook (Bash). Warnt vor blind-`git add .` / `git add -A` / `git commit -a`
# in Mono-Repos mit untracked Subdirs — Skill `cross-repo-state-inspection-before-commit`.
#
# Verhalten: warn-only (exit 0). Audit nicht nötig (transient).
# Warnung geht als hookSpecificOutput.additionalContext nach stdout (nicht als
# plain stderr) — nur additionalContext landet zuverlässig im Claude-Kontext.
#
# Source: ed3design-skill-bundles/code-quality

set -u

# Read PreToolUse-JSON from stdin
input=$(cat)
command=$(echo "$input" | "$PY" -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Match blind-add patterns
if echo "$command" | grep -qE '\bgit\s+add\s+(\.|--?[Aa])(\s|$)|\bgit\s+commit\s+--?a\b'; then
    "$PY" -c "
import json, sys
command = sys.argv[1]
ctx = (
    f\"cross-repo-state-inspect: '{command}' contains a blind-add pattern. \"
    \"Risk in a mono-repo: untracked subdirs / shared modules / sub-project files \"
    \"get committed by accident. Recommendation: read 'git status --short' before add, \"
    \"then stage an explicit file list. Skill: cross-repo-state-inspection-before-commit\"
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'allow',
        'additionalContext': ctx,
    }
}))
" "$command"
fi

exit 0
