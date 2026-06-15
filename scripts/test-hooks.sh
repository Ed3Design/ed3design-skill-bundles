#!/usr/bin/env bash
# test-hooks.sh — verifies hook trigger-matrix.
#
# For each hook in code-quality/hooks/, runs a curated set of bash commands
# (representing both should-warn and should-skip cases) through the hook
# and asserts stderr output. Run via CI as a smoke-test.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_PYTEST="$REPO_ROOT/code-quality/hooks/pytest-venv-first.sh"
HOOK_BYPASS="$REPO_ROOT/code-quality/hooks/pre-push-bypass-audit.sh"

PASS=0
FAIL=0

run_hook() {
    local hook="$1"
    local command="$2"
    local payload
    payload=$(python3 -c "import json,sys; print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$command")
    echo "$payload" | bash "$hook" 2>&1
}

# "expected" is one of: "warn" (some stderr) or "silent" (no stderr).
assert() {
    local label="$1"
    local hook="$2"
    local command="$3"
    local expected="$4"   # warn | silent
    local out
    out=$(run_hook "$hook" "$command")
    local matched=0
    if [ "$expected" = "warn" ] && [ -n "$out" ]; then matched=1; fi
    if [ "$expected" = "silent" ] && [ -z "$out" ]; then matched=1; fi
    if [ $matched -eq 1 ]; then
        PASS=$((PASS + 1))
        printf "  ✅ %s\n" "$label"
    else
        FAIL=$((FAIL + 1))
        printf "  ❌ %s\n      expected=%s got=%q\n" "$label" "$expected" "$out"
    fi
}

# Create a fake-venv layout so the venv-first hook has something to grep
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.venv/bin"
cd "$TMP" || exit 1

echo "── pytest-venv-first.sh ──"
assert "bare pytest in venv-dir, no VIRTUAL_ENV → warn"          "$HOOK_PYTEST" "pytest tests/" "warn"
assert "python -m pytest → warn"                                  "$HOOK_PYTEST" "python -m pytest" "warn"
assert "python3 -m pytest -x → warn"                              "$HOOK_PYTEST" "python3 -m pytest -x" "warn"
assert ".venv/bin/pytest → silent (already venv-relative)"        "$HOOK_PYTEST" ".venv/bin/pytest" "silent"
assert "./.venv/bin/pytest → silent"                              "$HOOK_PYTEST" "./.venv/bin/pytest tests/" "silent"
assert "/abs/path/.venv/bin/pytest → silent"                      "$HOOK_PYTEST" "/home/user/.venv/bin/pytest" "silent"
assert "uv run pytest → silent (uv manages venv)"                 "$HOOK_PYTEST" "uv run pytest" "silent"
assert "poetry run pytest → silent"                               "$HOOK_PYTEST" "poetry run pytest tests/" "silent"
assert "hatch run pytest → silent"                                "$HOOK_PYTEST" "hatch run pytest" "silent"
assert "pdm run pytest → silent"                                  "$HOOK_PYTEST" "pdm run pytest" "silent"
assert "source .venv/bin/activate && pytest → silent"             "$HOOK_PYTEST" "source .venv/bin/activate && pytest" "silent"
assert ". venv/bin/activate && pytest → silent"                   "$HOOK_PYTEST" ". venv/bin/activate && pytest" "silent"
assert "ls (unrelated) → silent"                                  "$HOOK_PYTEST" "ls -la" "silent"
assert "echo 'pytest' (string, not invocation) → silent"          "$HOOK_PYTEST" "echo 'install pytest first'" "silent"

echo ""
echo "── pre-push-bypass-audit.sh ──"
assert "git push --no-verify → warn"                              "$HOOK_BYPASS" "git push --no-verify" "warn"
assert "git commit --no-verify -m fix → warn"                     "$HOOK_BYPASS" "git commit --no-verify -m 'fix'" "warn"
assert "git push --no-gpg-sign → warn"                            "$HOOK_BYPASS" "git push --no-gpg-sign" "warn"
assert "git commit --amend --no-edit → warn"                      "$HOOK_BYPASS" "git commit --amend --no-edit" "warn"
assert "git rebase --no-verify → warn"                            "$HOOK_BYPASS" "git rebase --no-verify main" "warn"
assert "regular git push → silent"                                "$HOOK_BYPASS" "git push origin main" "silent"
assert "regular git commit → silent"                              "$HOOK_BYPASS" "git commit -m 'fix'" "silent"
assert "unrelated command → silent"                               "$HOOK_BYPASS" "ls" "silent"

echo ""
echo "Totals: $PASS pass, $FAIL fail"
if [ $FAIL -gt 0 ]; then
    exit 1
fi
