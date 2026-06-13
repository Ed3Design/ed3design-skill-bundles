#!/bin/bash
# vault-first-prompt-detect.sh
#
# UserPromptSubmit-Hook. Detects when the user mentions a topic/project name
# that should trigger a vault-first check before any action.
#
# Pattern: when user prompts contain noun phrases like project names, topic refs,
# or "remember X" requests, suggest the vault-search-helper skill or vault-search.py
# tool before code action.
#
# Skill: vault-search-helper
# Behavior: warn-only (exit 0). Stderr message lands in Claude's context.
#
# Config: reads ~/.config/vault-search/config.json to know if a vault is set up.
# If no vault config exists, this hook is a no-op (clean install behavior).

set -u

VAULT_CONFIG="${HOME}/.config/vault-search/config.json"

# Skip if no vault configured (clean install — user hasn't run vault-search.py --init yet)
[ ! -f "$VAULT_CONFIG" ] && exit 0

# Read UserPromptSubmit JSON from stdin
input=$(cat)
prompt=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('prompt', ''))" 2>/dev/null)

# Skip empty or very short prompts (commands, single words, etc.)
[ -z "$prompt" ] || [ ${#prompt} -lt 20 ] && exit 0

# Trigger phrases that strongly suggest a vault-first check is needed.
# Adjust this regex for your own vault conventions.
trigger_pattern='[Pp]rojekt|[Pp]roject|[Tt]hema|[Tt]opic|"[Rr]emember|find.*notes?|search.*vault|existing.*on|what.*do.*we.*have'

if echo "$prompt" | grep -qE "$trigger_pattern"; then
    # Don't warn on every prompt — only on first few keywords
    echo "💡 vault-first-prompt-detect: prompt mentions a topic/project." >&2
    echo "    Consider running 'vault-search.py \"<topic>\"' before code action," >&2
    echo "    or load the 'token-savers:vault-search-helper' skill." >&2
fi

exit 0
