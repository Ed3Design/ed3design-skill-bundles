---
name: aggregate-code-review-after-tdd-tasks
description: Use when implementing a multi-task TDD plan via `superpowers:subagent-driven-development` AND all individual tasks have already passed their per-task two-stage review (spec-compliance + code-quality). Per-task reviews check the diff of ONE commit against ONE task description — they cannot catch cross-commit drift where Task-N implementation accumulates a divergence from spec-text that only becomes visible when reading the full feature end-to-end. This skill triggers a final aggregate-cross-commit review with a dedicated reviewer-lens that looks for: (1) state-machine/algorithm-order drift between spec-text and accumulated code, (2) naming-inconsistency across commits (variable renamed in Task 3 but old name still used in Task 1 docstring), (3) end-to-end data-flow integrity (does field `x` set in Task-1-Loader still propagate correctly through Task-4-Renderer?), (4) commit-message-honesty across the full commit-set per `commit-message-honesty-precheck`, (5) pre-commit-hook-coverage-gaps (lazy imports inside function bodies bypass `pytest --collect-only` collection), (6) test-suite-cohesion (are 11 new tests across 4 tasks uniform in assertion-style?). Trigger phrases like "Tasks 1-N alle durch", "alle TDD-Tasks done", "aggregate-Review vor Live-Run", "cross-commit-Drift-Check", "Plan-Implementation komplett, vor Push reviewen", "End-to-End-Behavior gegen Spec verifizieren", "letzter Review-Schritt vor finishing-a-development-branch". Do NOT load for single-commit reviews (use `superpowers:requesting-code-review` direkt), per-task reviews innerhalb des SDD-workflows (das ist automatisch via Spec-Reviewer + Code-Quality-Reviewer pro Task), branches mit <3 atomaren Feature-Commits (Aggregate-Linse hat nichts zu finden), oder Hotfixes/Bug-Fixes ohne Spec-Text als Soll-Vergleich. Encodes the 2026-06-02 ClaudetteV-Session-Discovery: nach 4 erfolgreichen Tasks der C1-Backtest-Simulation (jeder mit 2-stage-review passed) fand der aggregate-cross-commit-Reviewer eine State-Machine-Order-Drift zwischen Spec-Text und Code-Implementation, die kein per-commit-Review hatte detecten können — der Drift war erst an der End-to-End-Behavior-Reading sichtbar.

---

# aggregate-code-review-after-tdd-tasks
## What this skill does

After completing N atomic tasks via `superpowers:subagent-driven-development`, dispatch ONE final cross-commit code-reviewer subagent with the FULL commit-range as context, focused specifically on the lenses that per-task-reviews structurally cannot apply.

## When per-task reviews are insufficient

Per-task two-stage-reviews (Spec-Compliance + Code-Quality) verify:
- Task N's diff matches Task N's spec ✓
- Task N's diff is well-written code ✓

They do NOT verify:
- Task N's code is consistent with Task M's code (M ≠ N)
- The accumulated implementation matches the SPEC-TEXT at end-to-end-behavior-level
- The data-flow chain (loader → core-function → consumer → renderer) preserves field semantics

## The 6 aggregate-review-lenses

| Lens | Per-task miss-pattern | Detectable how |
|---|---|---|
| 1. State-Machine-Order | Spec says "block-first-then-resume", code does "resume-first-then-block" — per-task review checks signature + return shape but not algorithmic ordering against prose spec | Read spec-text-clauses side-by-side with implementation |
| 2. Naming-Drift | Task 1 introduces `paused_indices`, Task 3 references `paused_trade_ids` — both work but semantic confusion accumulates | Grep all introduced names + cross-check usages |
| 3. Data-Flow-Integrity | Task 1 returns `set[int]`, Task 2 expects `set[int] \| None`, Task 4 uses `result['c1_total_blocked']`. Each per-task pair fits but full chain fragility hidden | Trace one complete data path end-to-end |
| 4. Cross-Commit-Commit-Message-Honesty | Per-task review checks one commit. Aggregate checks: does each of N commits in the chain accurately describe its diff, or does one commit silently lie? | Read every commit message vs its diff |
| 5. Pre-Commit-Hook-Coverage-Gap | Lazy `import` inside function body bypasses `pytest --collect-only`. Per-task review didn't notice because the lazy-import worked at runtime. | Search for `^\s+from .* import` (mid-function imports) |
| 6. Test-Suite-Cohesion | Task 1 tests use `assert x == 0`, Task 2 tests use `assert skipped.get('x', 0) == 0` defensively, Task 3 tests use `re.search(...)`. Inconsistent assertion-styles per per-task-review-author. Aggregate sees the suite as a whole. | Read all new tests as a single suite |

## How to dispatch

```
Agent({
  description: "Aggregate code-review all N tasks",
  subagent_type: "pr-review-toolkit:code-reviewer",
  model: "sonnet",  # standard, not the lightest
  prompt: """
    Aggregate cross-commit code-review of an N-commit feature implementation.
    Per-commit reviews already passed each commit individually. This review
    looks for cross-commit issues that per-commit reviews could miss.

    ## Commit Range
    BASE_SHA: <commit-before-feature-work>
    HEAD_SHA: <current-HEAD>
    Full diff: git diff BASE..HEAD

    ## Spec + Plan
    Spec: <path>
    Plan: <path>

    ## Cross-Commit Review Focus (the 6 lenses)

    1. State-Machine / Algorithm-Order drift between spec-text-clauses and
       accumulated code
    2. Naming consistency across all N commits (variable renames, field-names)
    3. Architectural integrity end-to-end: trace one complete data-flow from
       <loader> through <core> to <consumer/renderer>. Field-name-drift or
       shape-mismatch?
    4. Commit-message-honesty across all N commits (each commit message
       matches its diff per `commit-message-honesty-precheck`)
    5. Pre-commit-hook coverage: any lazy imports inside function bodies
       that would bypass `pytest --collect-only`?
    6. Test-suite cohesion: do the K new tests form a coherent suite, or
       are there assertion-style inconsistencies?

    Categories: Strengths / Critical / Important / Minor.
    Assessment: APPROVED / NEEDS_FIXES + suitability for next stage.
  """
})
```

## The 2026-06-02 Genesis-Case

8 atomic commits (4 task-commits + 4 fix-commits from per-task code-reviews) for the Z.1-C1 Backtest-Simulation.

Per-task reviews passed **all 8 commits individually**. 33/33 tests green.

The aggregate-cross-commit-review found:

| Lens | Finding |
|---|---|
| 1. State-Machine-Order | Spec-text said "if paused: add(i) FIRST (unconditionally), then check resume". Code did "if paused: check resume FIRST, then add(i) only if still paused". Both per-task reviewers checked the implementation against the per-task spec's signature+return-shape but missed the algorithmic-ordering-text. **Impact: 1 trade per resume-event differential** — not measurement-blocking but a real spec-vs-code-drift. Resolution: documented as deliberate live-mirror semantics + spec-doc-update. |
| 5. Pre-Commit-Hook-Coverage | `from strategic.macro_pause import simulate_pause_periods` was a lazy import inside `run_backtest` function body. Per-task review didn't flag it because the lazy-import works at runtime. Aggregate review noted: `pytest --collect-only` only catches module-level imports, so import-break would silently land. **Fix: hoist to module-level.** |

These two issues were **invisible to per-task reviews by construction**.

## Anti-patterns

- ❌ **Treating per-task two-stage-review as sufficient end-of-feature verification** — they're necessary but cross-commit drift is a separate failure mode
- ❌ **Dispatching the aggregate-review with the same prompt as per-task code-quality-review** — same prompt = same lens = same blind spots. The aggregate prompt MUST explicitly name the 6 cross-commit lenses.
- ❌ **Running aggregate-review on a 1-2-commit branch** — there's no cross-commit accumulation possible. Use `superpowers:requesting-code-review` direkt.
- ❌ **Skipping aggregate-review because "all tests pass"** — tests verify runtime-behavior-on-fixtures, not architectural integrity or commit-message-honesty.

## Promotion checklist (DRAFT → GA)

- [ ] Codify the dispatch-call as a reusable helper (e.g. `superpowers/aggregate-review.md` template that takes BASE_SHA / HEAD_SHA / Spec-Path / Plan-Path)
- [ ] Document a concrete sequencing pattern: aggregate-review goes BEFORE `superpowers:finishing-a-development-branch`, AFTER the last per-task review
- [ ] Add at least 1 more genesis-case from a different feature-domain (not trading) to validate transferability
- [ ] Test the workflow in a session where the aggregate-review finds nothing — verify the false-negative-rate is acceptable
- [ ] Document interaction with `subagent-driven-development` skill: should the SDD-skill itself trigger this at "all tasks complete"?

## Related skills

- **Upstream:** `superpowers:subagent-driven-development` — this skill is the natural epilogue
- **Sibling:** `superpowers:requesting-code-review` — single-commit / single-PR equivalent
- **Downstream:** `superpowers:finishing-a-development-branch` — aggregate-review-approval is the precondition

## Genesis-session metadata

- **Date:** 2026-06-02
- **Vault:** ClaudetteV
- **Feature:** Z.1-C1-Backtest-Simulation
- **Commit-range:** `959c0d7..2e30c68` (8 atomic commits after spec/plan)
- **Per-task two-stage-reviews:** all 8 passed individually
- **Aggregate-review findings:** 2 Important + 3 Minor (would-have-been-missed by per-task reviews)
- **ABC-Verdict:** A ✅ Repeatable (every SDD-driven plan with ≥3 atomic tasks), B ✅ Prevents-Error (silent spec-vs-code-drift, hook-coverage-gaps), C ✅ Transferable (cross-commit reviewing is domain-independent)
