---
name: static-source-bug-class-coverage-test
description: |-
  Use when adding regression-test coverage for a bug-class that manifests as a repeated source-code pattern across multiple call-sites in the same file or codebase, NOT a single localized bug. Pattern: write a static-source-inspect-test that reads the source file directly via `Path(__file__).resolve().parents[N] / "src/file.py"`, extracts pattern candidates via regex (e.g. all triple-quoted SQL blocks containing certain tokens), and asserts each candidate contains the fix-marker. Critical: include a whitelist-skip for f-string templates with externalized variables that receive the fix at their definition site. Trigger on phrases like "write bug-class coverage test", "static source inspect test", "regression guard for the same bug pattern in multiple call-sites", "why not just endpoint mocks for all 4 spots?". Do NOT load for single-call-site bugs, bug classes not recognizable in the source pattern, or files with complex multi-layer f-string nesting where false-positive whitelisting becomes unreliable.

---

# static-source-bug-class-coverage-test

> ✅ **PROMOTED**: pattern from a query-fix session. TDD pressure-test passed (RED: relative path + fragile f-string detection; GREEN: `Path(__file__).resolve()` + triple-quote regex + clean whitelist skip). Polish incorporated: hint about f-string-concatenated SQL.

## Pattern (short form)

1. **Identify bug class as source pattern**: SQL block with X AND without Y, async function without Z, etc.
2. **Test loads file via Read** (`Path(__file__).resolve().parents[N] / "path/to/file.py"`) — NO relative path
3. **Extract pattern candidates via regex** over triple-quoted strings or code blocks
4. **For each candidate**: check fix-marker pattern is contained
5. **IMPORTANT — whitelist skip**: patterns that get the fix via f-string substitution (`{where_clause}` templates) skip, otherwise false-positives for already-fixed code
6. **Violations list**: on mismatch → assert with full snippet list in AssertionError

> **Limitation**: this test only covers triple-quoted SQL strings (`"""..."""`). SQL strings via f-string concatenation (`f"SELECT ... WHERE " + condition`) are not captured — for such patterns an integration test against real DB is the more reliable solution.

## Concrete example

```python
def test_status_module_no_unfiltered_win_aggregations():
    """Static check: every sum(CASE WHEN win) aggregation in status.py
    must be in a query block whose WHERE contains win IS NOT NULL."""
    from pathlib import Path
    import re

    src_path = (
        Path(__file__).resolve().parents[2]
        / "api/routes/dashboard/modules/status.py"
    )
    src = src_path.read_text(encoding="utf-8")

    # Extract triple-quoted SQL blocks
    sql_blocks = re.findall(r'"""(.*?)"""', src, re.DOTALL)

    violations: list[str] = []
    for block in sql_blocks:
        block_lower = block.lower()
        if "virtual_trades" not in block_lower:
            continue
        if not ("sum(case when" in block_lower and "win" in block_lower):
            continue
        # WHITELIST: skip f-string blocks with externalized where_clause —
        # those are guarded separately by the 4 endpoint mock tests
        if "{where_clause}" in block:
            continue
        if "win is not null" not in block_lower:
            violations.append(block.strip()[:200])

    assert not violations, (
        "Unfiltered win-aggregation(s) found in status.py — bug class "
        "(cockpit distortion) reintroduced:\n\n"
        + "\n---\n".join(violations)
    )
```

## Anti-Patterns

| Anti-Pattern | What to do instead |
|---|---|
| Naively report all pattern matches as violation (without whitelist) | False-positives for code where fix comes via externalized-variable → whitelist skip with clear comment |
| Pattern regex too greedy (matches multiple blocks) | Triple-quote capture with `DOTALL` + `.*?` non-greedy |
| Build test as endpoint-integration test | 4 bug spots = 4 endpoint mocks = 4× setup. Static-source inspect with 1 test covers all |
| File path hardcoded or relative | `Path(__file__).resolve().parents[N]` — test runs from any cwd |
| Violations error without snippet list | Test-failure message useless — user doesn't know WHERE in the file the violation is |

## Quick reference: when static-source vs endpoint-mock vs integration test

| Bug class | Test strategy |
|---|---|
| Source pattern in 1 call-site | Endpoint mock |
| Source pattern in N>1 call-sites in the same file | **Static-source inspect** (this skill) |
| Source pattern across multiple files | Static-source inspect over glob pattern |
| Runtime logic bug without syntactic pattern | Real-DB integration test |
| SQL via f-string concatenation (not triple-quoted) | Real-DB integration test |
| Multi-layer f-string nesting with complex substitution | Real-DB integration test (whitelist becomes unreliable) |

## Real-world impact

Query-fix session: 4 aggregation spots, 1 static-source test covers all plus regression guard for future aggregations. Test found 4 bug spots naively (2 of them false-positive due to f-string). Refinement to 2 real with whitelist skip was ironically a 2-iteration cycle, the skill does that in 1.

## Background: TDD progression (Bulletproofing log)

### Cycle 1 — PASS

- **RED subagent** (without skill): also chose static inspection (no endpoint mock) — surprisingly smart. BUT: used relative path `Path("api/routes/analytics/metrics.py")` (breaks at different cwd), and complex heuristic f-string-variable-definition regex (searches var definition in whole module — fragile with multi-module imports). Honesty caveat self-named.

- **GREEN subagent** (with skill): `Path(__file__).resolve().parents[2]` correct, triple-quote regex clean, whitelist skip with explanatory comment. Self-reflection identified skill gap: f-string-concatenated SQL not covered → polish item incorporated.

- **Refactor**: no R1-R3 needed. Polish item (f-string concatenation limitation note) directly incorporated.

### Cycle-2-Backlog (Polish, non-blocking)

1. Glob pattern example for "source pattern across multiple files" case (e.g. `glob("api/**/*.py")` + iterate)
2. `--no-header` / `format-string` adjustment for violations message when snippet is very large
