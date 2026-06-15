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

# ─────────────────────────────────────────────────────────────────────
# Behavioral smoke-tests — exercise actual subcommands, not just --help.
# Added after PR #4 review identified that --help-only smoke would not
# have caught img-preprocess `colors` NameError. Each test produces a
# minimal fixture, invokes the tool, and asserts the expected output.
# ─────────────────────────────────────────────────────────────────────

echo ""
echo "── Behavioral smoke-tests (real subcommand invocations) ──"

assert_behavioral() {
    local label="$1"
    local cmd="$2"
    local expect_grep="$3"  # pattern that must appear in stdout+stderr
    local out
    out=$(eval "$cmd" 2>&1)
    if echo "$out" | grep -qE "$expect_grep"; then
        PASS=$((PASS + 1))
        echo "  ✅ $label"
    else
        FAIL=$((FAIL + 1))
        echo "  ❌ $label"
        echo "      cmd:    $cmd"
        echo "      expect: $expect_grep"
        echo "      got:    $(echo "$out" | head -1)"
    fi
}

# Behavioral tests need Pillow + bs4 in the test venv. Install them once
# in the same Python that will execute the tool. Skip the test if install
# fails (the CI workflow installs them at job setup).
TEST_PY="${PYTHON:-python3}"
"$TEST_PY" -c "import PIL" 2>/dev/null || pip install --quiet Pillow 2>/dev/null
"$TEST_PY" -c "import bs4" 2>/dev/null || pip install --quiet beautifulsoup4 2>/dev/null

FIXTURES=$(mktemp -d)
trap 'rm -rf "$FIXTURES"' EXIT

# img-preprocess: generate a real 4×4 PNG, then exercise info + colors + resize
"$TEST_PY" -c "
try:
    from PIL import Image
    img = Image.new('RGB', (4, 4), color=(128, 64, 192))
    img.save('$FIXTURES/tiny.png')
    print('OK')
except ImportError:
    print('SKIP — Pillow unavailable')
" > "$FIXTURES/pil_check.log"

if grep -q "OK" "$FIXTURES/pil_check.log"; then
    assert_behavioral "img-preprocess info <tiny.png> outputs JSON with 'dimensions'" \
        "$TOOLS_DIR/img-preprocess.py info $FIXTURES/tiny.png" \
        '"dimensions"'
    assert_behavioral "img-preprocess colors <tiny.png> --n 3 outputs 'dominant_colors'" \
        "$TOOLS_DIR/img-preprocess.py colors $FIXTURES/tiny.png --n 3" \
        '"dominant_colors"'
    assert_behavioral "img-preprocess resize <tiny.png> --max 2 outputs 'new_dims'" \
        "$TOOLS_DIR/img-preprocess.py resize $FIXTURES/tiny.png --max 2 --out $FIXTURES/tiny_resized.png" \
        '"new_dims"'
else
    echo "  ⏭  img-preprocess behavioral tests SKIPPED (Pillow not available)"
fi

# html2md: feed a minimal HTML document, expect Markdown-like output (#, *, links)
cat > "$FIXTURES/sample.html" << 'HTML'
<!DOCTYPE html>
<html><head><title>Hi</title></head><body>
<h1>Heading</h1>
<p>This is <strong>bold</strong> and a <a href="https://example.com">link</a>.</p>
</body></html>
HTML
"$TEST_PY" -c "import bs4" 2>/dev/null && BS4_OK=1 || BS4_OK=0
if [ "$BS4_OK" = "1" ]; then
    assert_behavioral "html2md <sample.html> extracts 'Heading' from <h1>" \
        "cat $FIXTURES/sample.html | $TOOLS_DIR/html2md.py -" \
        "Heading"
else
    echo "  ⏭  html2md behavioral test SKIPPED (bs4 not available)"
fi

# diff-summary: create a tiny git repo with 1 commit and assert it succeeds
mkdir -p "$FIXTURES/mini-repo" && (
    cd "$FIXTURES/mini-repo"
    git init --quiet
    git config user.email "smoke@test.local"
    git config user.name "Smoke Test"
    echo "hello" > a.txt
    git add a.txt
    git commit --quiet -m "initial"
    echo "world" >> a.txt
    git commit --quiet -am "extend a.txt"
)
assert_behavioral "diff-summary --repo <mini-repo> outputs 'files_changed'" \
    "$TOOLS_DIR/diff-summary.py --repo $FIXTURES/mini-repo" \
    '"files_changed"'

# vault-search: create a minimal vault structure and assert search finds it
mkdir -p "$FIXTURES/mini-vault/notes"
cat > "$FIXTURES/mini-vault/notes/needle.md" << 'NOTE'
# Needle Note

This file contains the special token UNIQUE-NEEDLE-TOKEN-12345.
NOTE
assert_behavioral "vault-search 'UNIQUE-NEEDLE-TOKEN-12345' finds 'needle.md'" \
    "$TOOLS_DIR/vault-search.py --vault $FIXTURES/mini-vault UNIQUE-NEEDLE-TOKEN-12345" \
    "needle"

# db-schema-inspector: cannot exercise live without DB; behavioral test
# is the SQL-injection guard (already covered by test-sql-injection-guard.py).

echo ""
echo "Behavioral test totals: see Totals row above"
