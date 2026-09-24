#!/bin/bash
PY=$(command -v python3 || command -v python)
# commit-message-honesty.sh
#
# PreToolUse-Hook (Bash). Warnt bei generic/honest-less commit-messages
# wie "WIP", "fix various", "update stuff", "misc changes".
#
# Skill: commit-message-honesty-precheck
# Verhalten: warn-only (exit 0). Warnung geht als hookSpecificOutput.additionalContext
# nach stdout (nicht als plain stderr) — nur additionalContext landet zuverlässig im
# Claude-Kontext; ein exit-0-Hook, der nur stderr beschreibt, wird von Claude nie gesehen.

set -u

input=$(cat)
command=$(echo "$input" | "$PY" -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Nur git commit -m branches checken
if ! echo "$command" | grep -qE 'git\s+commit.*-m'; then
    exit 0
fi

# Extract message text (zwischen Quotes nach -m)
message=$(echo "$command" | sed -nE 's/.*-m[[:space:]]+["\x27]([^"\x27]*)["\x27].*/\1/p')

# Generic-Message-Patterns
generic_patterns='^(WIP|wip|update|misc|fix|stuff|changes|various|tweak|small fixes?|cleanup|temp|temporary|test|TODO|tmp)$|^(fix|update|misc|stuff|various)[[:space:]]+(things|stuff|files|various|changes)$'

if echo "$message" | grep -qiE "$generic_patterns"; then
    "$PY" -c "
import json, sys
message = sys.argv[1]
ctx = (
    f\"commit-message-honesty: generic commit message '{message}' detected. \"
    \"Recommendation: subject should state (a) scope (feat/fix/refactor/docs/test/chore + module) \"
    \"and (b) concrete what AND why (1-2 sentences). Skill: commit-message-honesty-precheck\"
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'allow',
        'additionalContext': ctx,
    }
}))
" "$message"
fi

exit 0
