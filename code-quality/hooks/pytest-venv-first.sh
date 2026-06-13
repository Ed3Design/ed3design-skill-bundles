#!/bin/bash
# pytest-venv-first.sh
#
# PreToolUse-Hook (Bash). Warnt wenn `pytest` ohne aktive venv ausgeführt wird
# (false-negative-Risk: Tests laufen gegen System-Python statt Projekt-deps).
#
# Skill: pytest-venv-first-triage
# Verhalten: warn-only (exit 0).

set -u

input=$(cat)
command=$(echo "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Nur direkten pytest-Aufruf checken (nicht `source venv && pytest`)
if ! echo "$command" | grep -qE '^[[:space:]]*pytest\b|^[[:space:]]*python[3]?\s+-m\s+pytest\b'; then
    exit 0
fi

# Skip wenn `source` / `activate` im command
if echo "$command" | grep -qE 'source\s+\S+/activate|\.\s+\S+/activate'; then
    exit 0
fi

# Check ob VIRTUAL_ENV gesetzt (gilt nicht für hook-context, aber zeigt Pattern)
if [ -z "${VIRTUAL_ENV:-}" ]; then
    # Check ob venv-Folder im CWD existiert
    if [ -d ".venv" ] || [ -d "venv" ]; then
        echo "⚠️  pytest-venv-first: pytest aufgerufen ohne aktive venv." >&2
        echo "    CWD hat .venv/venv-Folder — möglicherweise gegen System-Python getestet." >&2
        echo "    Empfehlung: 'source .venv/bin/activate && pytest' oder '.venv/bin/pytest'" >&2
        echo "    Skill: pytest-venv-first-triage" >&2
    fi
fi

exit 0
