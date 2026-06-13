#!/bin/bash
# pre-push-bypass-audit.sh
#
# PreToolUse-Hook (Bash). Audit-Log + Warnung bei `git push --no-verify` /
# `--no-gpg-sign` Bypass-Flags.
#
# Skill: pre-push-bypass-audit-trail
# Verhalten: warn + audit (exit 0). Audit-Log: ~/.claude/audit/git-bypass.log

set -u

input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Match bypass-Flags in git push/commit
if echo "$command" | grep -qE 'git\s+(push|commit).*--?(no-verify|no-gpg-sign|amend.*--no-edit)'; then
    AUDIT_DIR="${HOME}/.claude/audit"
    AUDIT_LOG="${AUDIT_DIR}/git-bypass.log"
    mkdir -p "$AUDIT_DIR"

    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cwd=$(pwd)
    echo "[$timestamp] CWD=$cwd CMD=$command" >> "$AUDIT_LOG"

    echo "⚠️  pre-push-bypass-audit: Bypass-Flag in git-Command erkannt." >&2
    echo "    Logged to $AUDIT_LOG" >&2
    echo "    Empfehlung: Bypass nur mit dokumentiertem Grund." >&2
    echo "    Skill: pre-push-bypass-audit-trail" >&2
fi

exit 0
