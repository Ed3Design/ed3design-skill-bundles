#!/bin/bash
PY=$(command -v python3 || command -v python)
# pytest-venv-first.sh
#
# PreToolUse-Hook (Bash). Warnt wenn `pytest` ohne aktive venv ausgeführt wird
# (false-negative-Risk: Tests laufen gegen System-Python statt Projekt-deps).
#
# Skill: pytest-venv-first-triage
# Verhalten: warn-only (exit 0). Warnung geht als hookSpecificOutput.additionalContext
# nach stdout (nicht als plain stderr) — nur additionalContext landet zuverlässig im
# Claude-Kontext.

set -u

input=$(cat)
command=$(echo "$input" | "$PY" -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Detect pytest invocations across common runners (uv, poetry, hatch, pdm,
# .venv-direct-path, python -m pytest). Matched on the FIRST command of a
# pipeline (after optional leading whitespace / `&& ` / `; `).
#
# Patterns matched (=> "this is a pytest call we care about"):
#   pytest                          # bare
#   python -m pytest                # module form
#   python3 -m pytest
#   uv run pytest                   # uv runner
#   poetry run pytest               # poetry runner
#   hatch run pytest                # hatch runner
#   pdm run pytest                  # pdm runner
#   ./.venv/bin/pytest              # direct venv path
#   .venv/bin/pytest
#   venv/bin/pytest
#   ./tests/.venv/bin/pytest        # nested venv
#   /abs/path/.venv/bin/pytest
#
# This regex is permissive — better a false positive (extra warning) than a
# silent miss. Skip if it doesn't match at all.
# Leading boundary intentionally excludes bare whitespace to avoid false-
# positives from quoted argument strings (e.g. `echo "install pytest first"`).
# We require either start-of-line OR an unquoted shell-control operator
# (`&&`, `;`, `|`) before the pytest invocation.
if ! echo "$command" | grep -qE '(^|&&|;|\|)[[:space:]]*(pytest\b|python[3]?[[:space:]]+-m[[:space:]]+pytest\b|(uv|poetry|hatch|pdm)[[:space:]]+run[[:space:]]+pytest\b|(\./|/)?([^[:space:]]+/)*(\.?venv)/bin/pytest\b)'; then
    exit 0
fi

# Skip: explicit venv-activation present (covers `source .venv/bin/activate`,
# `. venv/bin/activate`, plus rare `conda activate <env> && pytest`).
if echo "$command" | grep -qE 'source[[:space:]]+\S+/(activate|activate\.\S+)|\.[[:space:]]+\S+/(activate|activate\.\S+)|conda[[:space:]]+activate[[:space:]]'; then
    exit 0
fi

# Skip: explicit .venv-relative or absolute-venv pytest path (already
# satisfies the discipline — no warning needed).
if echo "$command" | grep -qE '(\./|/)?([^[:space:]]+/)*\.?venv/bin/pytest\b'; then
    exit 0
fi

# Skip: uv/poetry/hatch/pdm already isolate env — they manage venv for you.
if echo "$command" | grep -qE '(uv|poetry|hatch|pdm)[[:space:]]+run[[:space:]]+pytest\b'; then
    exit 0
fi

# Check ob VIRTUAL_ENV gesetzt (gilt nicht für hook-context, aber zeigt Pattern)
if [ -z "${VIRTUAL_ENV:-}" ]; then
    # Check ob venv-Folder im CWD existiert
    if [ -d ".venv" ] || [ -d "venv" ]; then
        "$PY" -c "
import json
ctx = (
    'pytest-venv-first: pytest invoked without an active venv. '
    'CWD has a .venv/venv folder — this may be testing against system Python instead '
    \"of the project's deps. Recommendation: 'source .venv/bin/activate && pytest' or \"
    \"'.venv/bin/pytest'. Skill: pytest-venv-first-triage\"
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'allow',
        'additionalContext': ctx,
    }
}))
"
    fi
fi

exit 0
