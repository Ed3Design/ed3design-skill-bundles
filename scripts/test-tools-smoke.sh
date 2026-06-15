#!/usr/bin/env bash
# test-tools-smoke.sh — minimal smoke-test for the 5 token-savers tools.
#
# Verifies each tool:
#   1. Has a working `--help` that exits 0 (incl. when third-party deps missing)
#   2. Compiles (caught earlier by `py_compile`, but re-verified here)
#   3. Gracefully reports missing third-party dependencies instead of opaque
#      `ImportError` / `ModuleNotFoundError`
#
# Wired into CI as a fast feedback gate. Deeper behavioral tests with
# mocked DB/SSH/Pillow inputs are scoped for a future test-scaffolding PR.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_DIR="$REPO_ROOT/token-savers/tools"

PASS=0
FAIL=0

assert_help_ok() {
    local tool="$1"
    local label="$2"
    if [ ! -x "$TOOLS_DIR/$tool" ]; then
        echo "  ❌ $label: $tool not executable"
        FAIL=$((FAIL + 1))
        return
    fi
    if "$TOOLS_DIR/$tool" --help > /dev/null 2>&1; then
        PASS=$((PASS + 1))
        echo "  ✅ $label"
    else
        echo "  ❌ $label: --help failed"
        FAIL=$((FAIL + 1))
    fi
}

assert_help_in_clean_venv() {
    local tool="$1"
    local label="$2"
    local tmp
    tmp=$(mktemp -d)
    python3 -m venv "$tmp/venv" 2>/dev/null
    if "$tmp/venv/bin/python3" "$TOOLS_DIR/$tool" --help > /dev/null 2>&1; then
        PASS=$((PASS + 1))
        echo "  ✅ $label (--help works without third-party deps)"
    else
        echo "  ❌ $label: --help fails in clean venv"
        FAIL=$((FAIL + 1))
    fi
    rm -rf "$tmp"
}

assert_missing_dep_message() {
    local tool="$1"
    local subcmd="$2"
    local needle="$3"
    local label="$4"
    local tmp
    tmp=$(mktemp -d)
    python3 -m venv "$tmp/venv" 2>/dev/null
    # Create a dummy file so the tool's path-check passes before the dep-check
    touch "$tmp/dummy.png"
    local out
    out=$("$tmp/venv/bin/python3" "$TOOLS_DIR/$tool" $subcmd "$tmp/dummy.png" 2>&1 || true)
    if echo "$out" | grep -qi "$needle"; then
        PASS=$((PASS + 1))
        echo "  ✅ $label (clear missing-dep message)"
    else
        echo "  ❌ $label: expected dep-hint '$needle' in stderr, got: $(echo "$out" | head -2)"
        FAIL=$((FAIL + 1))
    fi
    rm -rf "$tmp"
}

echo "── --help exit-code (with system Python — deps may be present) ──"
assert_help_ok "vault-search.py"          "vault-search --help"
assert_help_ok "db-schema-inspector.py"   "db-schema-inspector --help"
assert_help_ok "diff-summary.py"          "diff-summary --help"
assert_help_ok "html2md.py"               "html2md --help"
assert_help_ok "img-preprocess.py"        "img-preprocess --help"

echo ""
echo "── --help in clean venv (no third-party deps) ──"
# Tools that require third-party deps for SUBCOMMANDS only — --help itself
# should work everywhere via lazy imports.
assert_help_in_clean_venv "img-preprocess.py"  "img-preprocess"
assert_help_in_clean_venv "html2md.py"         "html2md"
# stdlib-only tools — should always work
assert_help_in_clean_venv "vault-search.py"        "vault-search"
assert_help_in_clean_venv "db-schema-inspector.py" "db-schema-inspector"
assert_help_in_clean_venv "diff-summary.py"        "diff-summary"

echo ""
echo "── Missing-dependency error messages ──"
assert_missing_dep_message "img-preprocess.py" "info" "Pillow" \
    "img-preprocess info without Pillow"

echo ""
echo "Totals: $PASS pass, $FAIL fail"
if [ $FAIL -gt 0 ]; then
    exit 1
fi
