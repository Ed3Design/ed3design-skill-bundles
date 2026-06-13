---
name: code-review-findings-als-red-tests
description: Use when a code-review subagent (e.g. feature-dev:code-reviewer) has returned Critical/Important findings on a feature commit and you're about to write fixes. Standard default is "direct-fix, no new test". This skill says: each finding is itself a test case — write a RED test that shows the bug behavior, then GREEN fix. Prevents regressions + documents the bug pattern for future reviews. Trigger on phrases like "fix code-review findings", "implement Critical fix", "review subagent found C1/I1/I2", "convert reviewer output to fix", "close review cycle". Do NOT load for trivial style findings (typo, unused-import), for findings without a reproducible code path (perf hints, future-proofing), for code where TDD was consciously skipped (user-confirmed), or when the subagent had NO findings.
---

# Code-Review Findings as RED-Tests

> ✅ **PROMOTED** — TDD pressure-test PASS. RED showed "direct-edit + spot-check" as default, no regression protection, ~45min total; GREEN wrote 4 bug-pattern tests (test_sl_knocked_out_renders_warning_not_zero_eur etc.) with RED-verify obligation, +19min for regression protection. Cycle 2 polish: decision tree "RED-test passes unexpectedly", finding-cluster heuristic (combined-commit vs separated).

## Overview

A code-review subagent (e.g. Sonnet) typically returns findings as:
- **Critical/Important/Minor** with confidence score
- File-path + line-number  
- "Finding + What to do instead" explanation

Standard default on receipt: direct fix-commit with Edit. **Problem**: without a regression test, the same bug can reappear after refactoring. Plus: the bug pattern is not made learnable for future reviews.

**Fix-pattern of this skill**: convert each finding to a RED-test, then GREEN-implementation. Three outcomes:

1. **Regression protection**: future refactoring cannot reintroduce the same bug
2. **Bug-pattern documentation**: the test name + docstring makes the bug-pattern referenceable
3. **Confidence verification**: does the RED test fail for exactly what the reviewer described? If not — finding is unclear or reviewer over-reacted

## When to use

Trigger phrases:
- "fix code-review findings"
- "implement Critical fix"
- "review subagent found C1 / I1 / I2"
- "convert reviewer output to fix"
- "close review cycle"

Concrete signals:
- Subagent returned structured findings (not just vibes)
- At least 1 Critical or Important
- Findings have reproducible code paths (file + line)
- Code under test (not throwaway script)

## When NOT to use

- **Trivial style findings**: typo, unused-import → just fix
- **Future-proofing hints**: "at scale Y would be better" → no reproducible bug
- **Perf hints without benchmark test**: "could be faster" → not testable
- **TDD deliberately skipped**: user override "no test, direct fix"
- **No findings**: subagent gave green light

## How to use

### Step 1 — Parse + prioritize findings

Per finding:
- **Severity**: C/I/M
- **File + line**: concrete
- **Pattern name**: extract "what was the bug" (e.g. "knockout-SL-rendered-as-0.00-EUR")
- **Reproducible**: can I reproduce this in a test? (If no → anti-pattern)

### Step 2 — Write a RED test per finding

Test structure:
- **Test name**: bug-pattern descriptive (e.g. `test_sl_knocked_out_renders_warning_not_zero_eur`)
- **Docstring**: quote the reviewer finding + user impact
- **Assert**: the anti-pattern must NOT appear (e.g. `assert "0.00 EUR" not in sl_line`)

### Step 3 — Verify RED

Run the new tests against current production code → MUST fail. If not:
- Finding was incorrect (reviewer hallucination)
- Test assertion is too soft
- Bug pattern was not as described

In all 3 cases: DO NOT write GREEN — instead clarify with the subagent or user.

### Step 4 — GREEN implementation

Minimal fix that makes the tests green. Pattern like `superpowers:test-driven-development`.

### Step 5 — Commit message documents findings

```
fix(<scope>): code-review findings — <short list>

C1 (Critical) — <finding short>
Fix: <what was changed>

I1 (Important) — <finding>
Fix: <what was changed>

TDD: N new RED→GREEN tests in <test-file>.
```

Makes the fix-commit reviewable + shows that review findings were processed systematically.

## Anti-patterns

| Anti-Pattern | What to do instead |
|---|---|
| Direct fix without test | RED test per finding |
| Write test but don't quote reviewer finding | Docstring with reviewer finding excerpt |
| Generic test name (`test_fix_critical_1`) | Bug-pattern descriptive (`test_sl_knocked_out_renders_warning_not_zero_eur`) |
| Bundle multiple findings into one test | One test per finding (or one test class) |
| Skip RED phase ("test passes immediately") | Run tests against current code MUST fail before fix |
| Ignore findings because "reviewer over-reacted" | Clarify instead of skipping — discuss the subagent output |

## Real-world impact

Phase-B+C+D session: reviewer subagent found C1 + I1 + I2.

**Without skill**: 3 direct fixes per Edit, no regression test, no bug-pattern doc.

**With skill**:
- 4 new RED tests in `test_v3_combo_order.py` (C1 + I1 + edge case)
- RED phase verified: all 4 fail against production code
- GREEN implementation in commit `b634bb8`
- Test suite 13/13 (was 9 before fix) — regression protection against re-introduction

Counterfactual: in a later refactor, the knockout-render-trap (C1) could easily have slipped in again without the `test_sl_knocked_out_renders_warning_not_zero_eur` test.

## Cross-references

- `superpowers:requesting-code-review` — predecessor step (review dispatch)
- `superpowers:receiving-code-review` — related for user-review feedback
- `superpowers:test-driven-development` — the TDD discipline in the RED→GREEN cycle
- `code-review-chunk-dispatch` — for large review backlogs

## Background

Pattern formalized after a Phase-B+C+D review cycle. Reinforces the maxim "code review as standard" with the **systematic-test aspect** — review findings are tests-in-disguise.

## Background: TDD progression (Bulletproofing-Log)

### Cycle 1 — PASS

- **RED-Subagent** (without skill): direct-edit + spot-check, ~45min. Self-reflection acknowledged the risks (no regression test, bug classes uncovered, "done" is claim rather than proof) — but default was direct-edit.
- **GREEN-Subagent** (with skill): 4 bug-pattern tests (test_sl_knocked_out_renders_warning_not_zero_eur, test_sl_above_ko_ask_rejected_no_positive_pnl, test_sl_equals_ko_ask_rejected, test_quantity_fallback_raises_not_silently_defaults_to_100) + RED-verify obligation. Bonus: GREEN added edge-case test (sl == ko_ask) that the skill didn't explicitly require. ~31min total (+19min vs RED for regression protection).
- **Refactor**: none blocking.

### Cycle-2-Backlog (Polish, non-blocking)

- **Decision tree "RED-test passes unexpectedly"**: if the test passes against production code rather than failing, read production code → tighten test assertion, otherwise re-dispatch subagent to clarify finding
- **Finding-cluster heuristic**: when C1 + I1 sit in the same file section → combined commit, otherwise separated. Document decision heuristic.
