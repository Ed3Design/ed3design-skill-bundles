#!/bin/bash
# pre-push-bypass-audit.sh
#
# PreToolUse-Hook (Bash). Audit-Log + Warnung bei `git push --no-verify` /
# `--no-gpg-sign` / `--amend --no-edit` Bypass-Flags.
#
# Skill: pre-push-bypass-audit-trail
# Verhalten: warn + audit (exit 0). Audit-Log: ~/.claude/audit/git-bypass.log
#
# Privacy: Audit-Log enthält bewusst NICHT den vollen Command, damit
# token-haltige Remote-URLs (https://oauth:TOKEN@github.com/...),
# Commit-Message-Inhalte oder andere Sensitiva nicht persistent
# in plaintext auf Disk landen. Stattdessen werden geloggt:
#   - Bypass-Flag(s) (welche)
#   - Repo-Name (aus origin URL extrahiert, ohne Schema/Host/Token)
#   - SHA256-Hash des vollen Commands (für Forensik-Korrelation)
#   - CWD (kein Secret-Risiko)
# Datei-Permissions: 0600 (nur User-readable).

set -u

input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Match bypass-Flags in git push/commit/rebase
if echo "$command" | grep -qE 'git\s+(push|commit|rebase).*--?(no-verify|no-gpg-sign|amend.*--no-edit)'; then
    AUDIT_DIR="${HOME}/.claude/audit"
    AUDIT_LOG="${AUDIT_DIR}/git-bypass.log"
    mkdir -p "$AUDIT_DIR"
    chmod 0700 "$AUDIT_DIR" 2>/dev/null || true

    # Extract only the bypass flag(s) — drop everything else from the command
    flags=$(echo "$command" | grep -oE -- '--(no-verify|no-gpg-sign|amend|no-edit)' | sort -u | tr '\n' ',' | sed 's/,$//')

    # Extract repo basename from origin URL (no token, no host, no path)
    repo="unknown"
    if git rev-parse --git-dir >/dev/null 2>&1; then
        origin_url=$(git config --get remote.origin.url 2>/dev/null || echo "")
        if [ -n "$origin_url" ]; then
            # Strip token@, strip path/host, strip .git suffix
            repo=$(echo "$origin_url" | sed -E 's#^[^@]+@##; s#.*[/:]##; s#\.git$##')
        fi
    fi

    # Hash of the full command (for forensic correlation, no plaintext)
    cmd_hash=$(printf '%s' "$command" | shasum -a 256 2>/dev/null | awk '{print $1}' | cut -c1-16)
    if [ -z "$cmd_hash" ]; then
        cmd_hash=$(printf '%s' "$command" | sha256sum 2>/dev/null | awk '{print $1}' | cut -c1-16)
    fi
    [ -z "$cmd_hash" ] && cmd_hash="no-hash-tool"

    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    cwd=$(pwd)

    # Touch + chmod BEFORE writing to ensure restrictive perms even on first creation
    : >> "$AUDIT_LOG"
    chmod 0600 "$AUDIT_LOG" 2>/dev/null || true

    echo "[$timestamp] repo=$repo flags=$flags cwd=$cwd cmd_sha256_16=$cmd_hash" >> "$AUDIT_LOG"

    echo "⚠️  pre-push-bypass-audit: Bypass-Flag in git-Command erkannt." >&2
    echo "    Flags:  $flags" >&2
    echo "    Repo:   $repo" >&2
    echo "    Logged (redacted) to $AUDIT_LOG" >&2
    echo "    Empfehlung: Bypass nur mit dokumentiertem Grund." >&2
    echo "    Skill: pre-push-bypass-audit-trail" >&2
fi

exit 0
