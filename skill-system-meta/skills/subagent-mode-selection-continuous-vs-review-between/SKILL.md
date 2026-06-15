---
name: subagent-mode-selection-continuous-vs-review-between
description: |-
  Use when starting a multi-task workflow via `superpowers:subagent-driven-development` (SDD) and the user needs to choose between two execution modes: (A) "Continuous Execution" — all tasks dispatched back-to-back without a user checkpoint between them (SDD default), or (B) "Review-Between-Tasks" — user wants to inspect each task's output before authorizing the next. The choice depends on task-type classification: mechanical-implementation tasks (TDD with complete code in plan, deterministic outcomes) are continuous-safe — user can review at the end. Judgment-heavy tasks (forensics, interpretation of numbers, strategic decisions, architectural pivots based on subagent output) require review-between because the next task's prompt depends on the prior task's outcome interpretation. Trigger phrases like "should I run continuous or with pauses between tasks", "review between steps", "subagent-driven with checkpoints", "pause after each task", "continuous execution or pause-between", "how many tasks without user choice in a row". Do NOT load for single-task workflows (no choice to make), for non-SDD workflows (use the direct task tool), for purely mechanical TDD implementations where all tasks have complete code in the plan and no judgment is needed (just go continuous), or for the very first task of a workflow (always start with one task — mode choice comes after the user sees the first output). Encodes the choice pattern: in one production-domain workflow, Tasks 1-5 of a backtest simulation (mechanical TDD with complete code in plan) were continuous = ~3h saved compared to 5× wait-for-user checkpoints. Tasks 6-8 (live-run, forensics, gate-review = judgment-heavy with strategic implications) were continuous-execute but each had a user-presentation pause at end because the strategic findings required user direction. A separate Phase-0 forensic sequence was REVIEW-BETWEEN — user explicitly requested "Review between each step" after the per-task outputs needed inspection and direction.

---

# subagent-mode-selection-continuous-vs-review-between
## What this skill does

When using `superpowers:subagent-driven-development` for a multi-task workflow, classify each task's risk-of-divergence-from-user-intent and propose either:
- **Continuous Execution** (default SDD behaviour, no user checkpoint between tasks)
- **Review-Between-Tasks** (user authorizes next task only after seeing prior-task output)

Wrong choice has real cost: continuous on judgment-heavy tasks wastes resources and produces drift; review-between on mechanical tasks creates 5+ wait cycles for the user.

## Task-type classification

The 3-factor test for "is this task mechanical-enough for continuous?":

### Factor 1 — Spec completeness
- ✅ Mechanical: Plan-Doc has complete code blocks for every step. Implementation = type-and-test.
- ❌ Judgment-heavy: Plan-Doc says "decide which filter to apply first" or "interpret the numbers and write recommendation"

### Factor 2 — Outcome determinism
- ✅ Mechanical: Outcome is binary-checkable (test pass/fail, file exists, commit SHA produced)
- ❌ Judgment-heavy: Outcome is text interpretation, strategic implication, or downstream-task-influencing data

### Factor 3 — Next-task dependency
- ✅ Mechanical: Next task in plan starts regardless of prior task's specifics
- ❌ Judgment-heavy: Next task's spec/prompt depends on what prior task found (e.g., "if D1 shows X is winner-dropper, then dispatch D2; if D1 shows otherwise, dispatch a different forensic")

**All 3 ✅** → Continuous Execution safe. **Any 1 ❌** → Review-Between.

## The choice pattern (Genesis)

Three workflow segments illustrated the choice clearly:

### Segment 1 — Backtest-Simulation Tasks 1-5 → Continuous ✅

| Task | All 3 factors? | Mode |
|---|---|---|
| 1: simulate_pause_periods + 6 tests | ✅✅✅ (complete code, test-pass binary, T2 uses T1's output spec) | Continuous |
| 2: apply_filters extension | ✅✅✅ | Continuous |
| 3: _load_full_history loader | ✅✅✅ | Continuous |
| 4: run_backtest integration | ✅✅✅ | Continuous |
| 5: Aggregate cross-commit review + fixes | ✅✅ (findings are textual but downstream-actionable per fixes routine) | Continuous |

Total continuous time: ~3h, no user wait cycles. Saved ~30-60 min of wait time per checkpoint.

### Segment 2 — Tasks 6-8 (live-run, forensics, gate-review) → Continuous-with-end-presentation ⚠

| Task | Mechanical-enough? | Mode |
|---|---|---|
| 6: Live-run on server | ✅✅⚠ (mechanical, but output numbers drive Task 7 spec) | Continuous, but pause AFTER for user to direct Task 7-8 |
| 7: Forensics note (findings) | ⚠⚠⚠ (interpretation-heavy, judgment in writing) | Continuous (writing is mechanical), but pause at end for user review |
| 8: Gate-review forensics | ⚠⚠⚠ (verdict judgment) | Continuous |

The user was alerted before Task 6 (live-run): "Live-run numbers could be unexpected, then Tasks 7-8 want user direction". User chose: continuous, but pause-after-Task-6 if numbers surprising. → Numbers WERE surprising → orchestrator paused at end of Task 6 with a user-direction question.

### Segment 3 — Phase 0 D1-D4 forensics → Review-Between ❌-Continuous

| Task | Factor failures | Mode |
|---|---|---|
| D1 AvgPnL-drop forensic | Factor 3 fail (D2 spec depends on D1 finding — if result = Winner-Dropper, D2 audits look-ahead; if Loser-Dropper, D2 skipped) | Review-Between |
| D2 anomaly forensic | Factor 3 fail (D3 spec depends on D1+D2 jointly) | Review-Between |
| D3 multi-run median stability | Factor 3 fail (D4 compound-gate values depend on D3 power analysis) | Review-Between |
| D4 compound-gate spec | mechanical given D3-confirmed values → could be continuous, but user explicitly asked "review between each step" | Review-Between |

User explicit: "Review between each step" — because each task's output meaningfully changed the next task's prompt.

## How to apply

### At workflow start

1. **Read the Plan-Doc**: for each task, count factor checks (✅ or ❌)
2. **Classify each task** as Mechanical / Hybrid / Judgment-heavy
3. **Propose modes per segment**:
   - Sequence of all-Mechanical tasks → continuous, end-presentation
   - Hybrid tasks (✅✅⚠) → continuous-with-pause-AFTER for next-task direction
   - Judgment-heavy tasks → review-between (default to "ask user after each")
4. **Surface the proposal to the user** with AskUserQuestion: "I propose: Tasks 1-5 continuous, then pause after 5 for review. Tasks 6-8 each pause after for user direction. OK?"

### Mid-workflow re-classification

If a task delivers an unexpected output (mechanical task suddenly looks judgment-heavy):
- STOP the continuous execution
- Present findings to the user
- Re-classify remaining tasks
- Resume per new mode choice

Example: D1 subagent found "winner-dropper" (+4.54% blocked-AvgPnL). That was subagent-output-INTERPRETATION-required → orchestrator correctly continuous-executed but paused-at-end for user direction.

## Anti-patterns

- ❌ **All-Continuous-by-Default without factor check** — clearly shown: D1-D4 would have caused DRIFT had they run continuous (D2 prompt would not have reflected D1's finding)
- ❌ **All-Review-Between-by-Default** — for Tasks 1-5 above this would have been 5× wait cycles à 30 min = 2.5h lost
- ❌ **Mode choice only at workflow start without re-classification** — outputs can flip the classification
- ❌ **Interpreting user choice 'continuous' as 'still continuous after unexpected outputs'** — pausing after Task 6 due to output surprise was correct even though the segment was begun as 'continuous'

## Complementary to `superpowers:subagent-driven-development`

This skill is a **pre-workflow classification sub-routine** for SDD. It does not replace the SDD skill but extends it with a mode-selection discipline before the `Continuous execution` default setting of the SDD workflow is blindly adopted.

The SDD skill states: "Continuous execution: Do not pause to check in with your human partner between tasks." That is the standard. **This skill provides the classification of when that standard is NOT the right choice.**

## Promotion checklist (DRAFT → GA)

- [ ] Integrate 3-factor classification as a callable AskUserQuestion template
- [ ] Add concrete examples from at least 1 non-trading domain (e.g., a frontend design feature, a deploy-pipeline refactor)
- [ ] Coordinate with `superpowers:subagent-driven-development` skill — propose upstream PR that integrates this as a section
- [ ] Document the re-classification trigger ("STOP and re-classify when") as a hard rule
- [ ] Test in a session where the choice is ambiguous and verify the AskUserQuestion template surfaces it clearly

## Genesis-session metadata

- **Workflow domains:** backtest engineering (8 tasks SDD), live-run forensics (4 D-tasks)
- **ABC verdict:** A ✅ Repeatable (3-factor check is mechanical), B ✅ Prevents error (all-continuous would have been wrong for D1-D4), C ✅ Transferable (any multi-task SDD workflow choice)
- **Real-world impact estimate:** through correct choice ~3h gained (Tasks 1-5 continuous instead of ~5 user wait cycles) AND DRIFT AVOIDED (D1-D4 as review-between instead of blind-continuous)
