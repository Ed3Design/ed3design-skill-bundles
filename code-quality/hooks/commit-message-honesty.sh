#!/bin/bash
# commit-message-honesty.sh
#
# PreToolUse-Hook (Bash). Warnt bei generic/honest-less commit-messages
# wie "WIP", "fix various", "update stuff", "misc changes".
#
# Skill: commit-message-honesty-precheck
# Verhalten: warn-only (exit 0).

set -u

input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Nur git commit -m branches checken
if ! echo "$command" | grep -qE 'git\s+commit.*-m'; then
    exit 0
fi

# Extract message text (zwischen Quotes nach -m)
message=$(echo "$command" | sed -nE 's/.*-m[[:space:]]+["\x27]([^"\x27]*)["\x27].*/\1/p')

# Generic-Message-Patterns
generic_patterns='^(WIP|wip|update|misc|fix|stuff|changes|various|tweak|small fixes?|cleanup|temp|temporary|test|TODO|tmp)$|^(fix|update|misc|stuff|various)[[:space:]]+(things|stuff|files|various|changes)$'

if echo "$message" | grep -qiE "$generic_patterns"; then
    echo "⚠️  commit-message-honesty: '$message'" >&2
    echo "    Generic-Pattern erkannt. Empfehlung: Subject sollte" >&2
    echo "    (a) Scope (feat/fix/refactor/docs/test/chore + module)" >&2
    echo "    (b) konkretes Was UND Warum (1-2 Sätze)" >&2
    echo "    Skill: commit-message-honesty-precheck" >&2
fi

exit 0
