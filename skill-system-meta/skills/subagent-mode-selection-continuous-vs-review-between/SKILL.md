---
name: subagent-mode-selection-continuous-vs-review-between
description: Use when starting a multi-task workflow via `superpowers:subagent-driven-development` (SDD) and the user needs to choose between two execution modes: (A) "Continuous Execution" — all tasks dispatched back-to-back without user-checkpoint between them (SDD-default), or (B) "Review-Between-Tasks" — user wants to inspect each task's output before authorizing the next. The choice depends on task-type-classification: mechanical-implementation-tasks (TDD with complete code in plan, deterministic outcomes) are continuous-safe — user can review at end. Judgment-heavy-tasks (forensik, interpretation-of-numbers, strategy-decisions, architectural-pivots based on subagent-output) require review-between because the next task's prompt depends on the prior task's outcome-interpretation. Trigger phrases like "soll ich continuous oder mit Pausen zwischen Tasks", "review zwischen den Schritten", "subagent-driven mit checkpoints", "nach jedem Task pausieren", "Continuous-Execution oder Pause-zwischen", "wie viele Tasks ohne Wolf-Wahl in Folge". Do NOT load for single-task workflows (no choice to make), for non-SDD workflows (use the direct task tool), for purely-mechanical TDD-implementations where all tasks have complete code in the plan and no judgment is needed (just go continuous), or for the very first task of a workflow (always start with one task — mode-choice comes after Wolf sees the first output). Encodes the 2026-06-02 Wolf-Choice-Pattern: Tasks 1-5 of C1-Backtest-Simulation (mechanical TDD with complete code in plan) were continuous = ~3h saved compared to 5× wait-for-Wolf-checkpoint. Tasks 6-8 (Live-Run, Forensik, Gate-Review = judgment-heavy with strategic implications) were continuous-execute but each had a Wolf-presentation-pause at end because the strategic findings required Wolf-direction. Phase 0 D1-D4 forensik (each interpretation-heavy) was REVIEW-BETWEEN — Wolf explicitly requested "Jeweils Review zwischen den Schritten" after the per-task outputs needed inspection-and-direction.

---

# subagent-mode-selection-continuous-vs-review-between
## What this skill does

When using `superpowers:subagent-driven-development` for a multi-task workflow, classify each task's risk-of-divergence-from-user-intent and propose either:
- **Continuous Execution** (Default SDD behaviour, no user-checkpoint between tasks)
- **Review-Between-Tasks** (user authorizes next-task only after seeing prior-task-output)

Wrong choice has real cost: continuous on judgment-heavy tasks wastes resources and produces drift; review-between on mechanical tasks creates 5+ wait-cycles for the user.

## Task-Type-Classification

The 3-factor-test for "is this task mechanical-enough to continuous?":

### Factor 1 — Spec-Completeness
- ✅ Mechanical: Plan-Doc has complete code blocks for every step. Implementation = type-and-test.
- ❌ Judgment-heavy: Plan-Doc says "decide which filter to apply first" or "interpret the numbers and write recommendation"

### Factor 2 — Outcome-Determinism
- ✅ Mechanical: Outcome is binary-checkable (test pass/fail, file exists, commit-SHA produced)
- ❌ Judgment-heavy: Outcome is text-interpretation, strategic-implication, or downstream-task-influencing-data

### Factor 3 — Next-Task-Dependency
- ✅ Mechanical: Next task in plan starts regardless of prior task's specifics
- ❌ Judgment-heavy: Next task's spec/prompt depends on what prior task found (e.g., "if D1 shows C1 is winner-dropper, then dispatch D2; if D1 shows otherwise, dispatch different forensik")

**All 3 ✅** → Continuous Execution safe. **Any 1 ❌** → Review-Between.

## The 2026-06-02 Wolf-Choice-Pattern (Genesis)

Three workflow segments illustrated the choice clearly:

### Segment 1 — C1-Backtest-Simulation Tasks 1-5 → Continuous ✅

| Task | All 3 Factors? | Mode |
|---|---|---|
| 1: simulate_pause_periods + 6 Tests | ✅✅✅ (complete code, test-pass binary, T2 wants paused_trade_ids in T1's spec) | Continuous |
| 2: apply_z1_filters extension | ✅✅✅ | Continuous |
| 3: _load_full_history loader | ✅✅✅ | Continuous |
| 4: run_backtest integration | ✅✅✅ | Continuous |
| 5: Aggregate-Cross-Commit-Review + Fixes | ✅✅ (findings are textual but downstream-actionable per fixes-routine) | Continuous |

Total continuous-time: ~3h, no Wolf-Wait-Cycles. Saved ~30-60 min of wait-time per checkpoint.

### Segment 2 — Tasks 6-8 (Live-Run, Forensik, Gate-Review) → Continuous-with-end-presentation ⚠

| Task | Mechanical-enough? | Mode |
|---|---|---|
| 6: Live-Run on swatserver | ✅✅⚠ (mechanical, but output-numbers drive Task 7 spec) | Continuous, but pause AFTER for Wolf to direct Task 7-8 |
| 7: Forensik-Note Phase 1 (C1-Befund) | ⚠⚠⚠ (interpretation-heavy, judgment in writing) | Continuous (writing is mechanical), but pause at end for Wolf review |
| 8: Gate-Review Forensik (Phase 2) | ⚠⚠⚠ (verdict-judgment) | Continuous |

Wolf was alerted before Task 6 (Live-Run): „Live-Run-Numbers könnten unexpected sein, dann Tasks 7-8 wollen Wolf-Direction". Wolf chose: continuous, but pause-after-Task-6 if numbers surprising. → Numbers WERE surprising → orchestrator paused at end of Task 6 with Wolf-Direction-Frage.

### Segment 3 — Phase 0 D1-D4 Forensik → Review-Between ❌-Continuous

| Task | Factor-Failures | Mode |
|---|---|---|
| D1 AvgPnL-Drop-Forensik | Factor 3 fail (D2-spec depends on D1-Befund — if C1 = Winner-Dropper, D2 audits look-ahead; if C1 = Loser-Dropper, D2 skipped) | Review-Between |
| D2 KW13-Anomalie-Forensik | Factor 3 fail (D3-spec depends on D1+D2 jointly) | Review-Between |
| D3 Multi-Run-Median-Stabilität | Factor 3 fail (D4-Compound-Gate-Werte depend on D3-Power-Analyse) | Review-Between |
| D4 Compound-Gate-Spec | mechanical given D3-belegte Werte → könnte continuous, aber Wolf explizit „Review-zwischen-Schritten" | Review-Between |

Wolf explizit: „Jeweils Review zwischen den Schritten" — because each task's output meaningfully changed the next task's prompt.

## How to apply

### At workflow-start

1. **Read the Plan-Doc**: for each task, count Factor-Checks (✅ or ❌)
2. **Classify each task** as Mechanical / Hybrid / Judgment-heavy
3. **Propose modes per segment**:
   - Sequence of all-Mechanical tasks → continuous, end-presentation
   - Hybrid tasks (✅✅⚠) → continuous-with-pause-AFTER for next-task-direction
   - Judgment-heavy tasks → review-between (default to "ask Wolf after each")
4. **Surface the proposal to Wolf** with AskUserQuestion: "I propose: Tasks 1-5 continuous, then pause after 5 for review. Tasks 6-8 each pause after for Wolf-direction. OK?"

### Mid-workflow Re-Classification

Wenn ein Task einen unexpected Output liefert (mechanical task wirkt suddenly judgment-heavy):
- STOP the continuous-execution
- Present findings to Wolf
- Re-classify remaining tasks
- Resume per new mode-choice

Beispiel heute: D1-Subagent fand "C1 = Winner-Dropper" (+4.54 % blocked-AvgPnL). Das war Subagent-Output-INTERPRETATION-required → orchestrator korrekt continuous-execute aber pause-at-end for Wolf-Direction.

## Anti-patterns

- ❌ **All-Continuous-by-Default ohne Factor-Check** — heute klar gezeigt: D1-D4 hätten DRIFT verursacht wenn continuous gewesen (D2-prompt hätte D1-Befund nicht reflektiert)
- ❌ **All-Review-Between-by-Default** — wäre für C1-Backtest-Tasks-1-5 5× wait-cycles à 30 Min = 2.5h verloren
- ❌ **Mode-Wahl nur am Workflow-Start ohne Re-Klassifikation** — Outputs können Klassifikation umkippen
- ❌ **Wolf-Wahl 'continuous' interpretieren als 'auch nach unerwarteten Outputs continuous'** — heute korrekt: Tasks 6-8 waren als 'continuous' begonnen, aber pause-after-Task-6 wegen Output-Surprise war richtig

## Komplementär zu `superpowers:subagent-driven-development`

Dieses Skill ist eine **Pre-Workflow-Klassifikations-Sub-Routine** für SDD. Es ersetzt nicht das SDD-Skill, sondern ergänzt es um eine Mode-Selection-Diszplin bevor die `Continuous execution` -Default-Setting des SDD-Workflows blind übernommen wird.

In SDD-Skill steht: „Continuous execution: Do not pause to check in with your human partner between tasks." Das ist der Standard. **Diese Skill liefert die Klassifikation, wann dieser Standard NICHT die richtige Wahl ist.**

## Promotion checklist (DRAFT → GA)

- [ ] Integrate 3-factor-classification as a callable AskUserQuestion-template
- [ ] Add concrete examples from at least 1 non-trading domain (e.g., a frontend-design-feature, a deploy-pipeline-refactor)
- [ ] Coordinate with `superpowers:subagent-driven-development` skill — propose upstream-PR that integrates this as a section
- [ ] Document the Re-Classification-Trigger („STOP and Re-Classify when") as a hard rule
- [ ] Test in a Wolf-session where the choice is ambiguous and verify the AskUserQuestion-Template surfaces it clearly

## Genesis-session metadata

- **Date:** 2026-06-02
- **Vault:** ClaudetteV
- **Workflow-domains:** C1-Backtest-Engineering (8 Tasks SDD), Live-Run Forensik (4 D-Tasks)
- **ABC-Verdict:** A ✅ Repeatable (3-Faktor-Check ist mechanisch), B ✅ Prevents-Error (heute klar: All-Continuous wäre für D1-D4 falsch gewesen), C ✅ Transferable (jede Multi-Task SDD-Workflow Wahl)
- **Real-world impact estimate:** Heute durch korrekte Wahl ~3h gewonnen (Tasks 1-5 continuous statt ~5 Wolf-Wait-Cycles) UND DRIFT-VERMIEDEN (D1-D4 als Review-Between statt blind-continuous)
