---
name: strategic-questions-before-code-touch
description: |-
  Use when about to start a multi-architecture-decision feature implementation (Phase-X-Vision-Spec, complex refactor, new module that touches 3+ existing modules) AFTER Reality-Inventory but BEFORE first code-touch. Pose 2-4 strategic questions via AskUserQuestion that lock in: (a) scope (atomic-block vs phased), (b) model/algorithm choice when ≥2 valid options exist, (c) persistence-decision (new column vs JSONB vs new table), (d) backward-compat strategy. Each question with 2-4 specific options + Recommended-marker. Trigger on phrases like "start Phase X", "implement Vision-Spec", "build new module for X", "refactor Y", "larger code change", "multiple architecture decisions open". Do NOT load for single-bug-fixes, for tasks with only one reasonable approach, when scope/persistence/model are obvious from existing code, or when user explicitly says "just start".
---

# Strategic Questions Before Code-Touch

> ✅ **PROMOTED** — TDD pressure test PASS. RED made 6 assumptions without user question (wished-for-code risk, live-trade with wrong sizing as worst case); GREEN formulated 3 strategic questions with 2-3 options each + Recommended marker. Cycle 2 polish: caller-context section "subagent without AskUserQuestion → markdown-simulated block" + AskUserQuestion JSON schema template.

## Overview

For multi-architecture decisions, the default temptation is: just start with assumptions. This systematically produces wished-for implementation that later triggers user pushback + requires re-refactor. Pattern from a Phase B+C+D session: 3 strategic questions before code-touch → user 3× Recommended → 30s decision block, ~1.75h clean implementation instead of ~3.5h with pushback loops.

**Pattern order** (user-confirmed):
1. **Reality inventory** (via skill `roadmap-phase-execution-verify-first`) — document drift vs spec
2. **Strategic questions** (this skill) — decisions that influence code direction
3. **TDD cycle** (via skill `superpowers:test-driven-development`) — implementation

## When to use

Trigger phrases:
- "Start / implement Phase X"
- "Execute vision spec"
- "Build new module for Y"
- "Larger refactor"
- "Multiple architecture decisions open"

Concrete signals:
- Reality inventory has shown spec drift (wished-for-implementation risk high)
- ≥2 valid implementation approaches visible (new position-sizer vs re-use; Model A vs B; JSONB vs new column)
- Backward-compat strategy not obvious
- Persistence slot not unambiguous (which table/which field?)

## When NOT to use

- **Single bug fix**: no architecture decisions — directly TDD cycle
- **One obvious solution**: when there's only one sensible path
- **Existing pattern fully defined**: when the feature follows an established pattern (e.g. "another FastAPI endpoint")
- **User override**: "just start" or "do the code first, we'll refactor later"

## How to use

### Step 1 — Reality inventory done?

Pre-condition: drift table exists. If not → first run `roadmap-phase-execution-verify-first`.

### Step 2 — Formulate strategic questions

**2-4 questions** each with **2-4 specific options** plus **Recommended marker** for the default suggestion. Question types:

| Question type | Example options |
|---|---|
| **Scope** | "atomic block (~1.75h)" vs "phased (shorter iterations)" |
| **Model/Algorithm** | "Leverage-relative (consistent with existing)" vs "Strike-Delta (spec original)" |
| **Persistence** | "JSONB per suggestion (additive)" vs "new v3_signals column (migration)" vs "new table" |
| **Backward-compat** | "graceful fallback in read layer" vs "explicit migration with backfill" |

### Step 3 — Formulate options clearly

Per option:
- **Label**: 1-5 words
- **Description**: 1-2 sentences, what happens + trade-off
- **Recommended marker**: at the end of the label "(Recommended)" for the default suggestion

### Step 4 — AskUserQuestion with all questions in one block

One `AskUserQuestion` tool-call with 2-4 questions. User decides in 30s. Code-touch then gated on answers.

### Step 5 — Document decisions in commit message

In the feat-commit at the end a section:
```
Strategic decisions:
- Scope: B+C+D as block
- Model: Leverage-relative
- Persistence: JSONB per suggestion
```

Makes the pull request reviewable + documents for later code-read why-so.

## Anti-patterns

| Anti-pattern | What to do instead |
|---|---|
| Make assumptions without user question → user pushback later | Formulate 2-4 strategic questions, invest 30s |
| One giant question with 8 options | Max 4 questions × 4 options, cognitively manageable |
| Questions without Recommended marker | User wants to see default suggestion, not all equally weighted |
| Questions AFTER code-touch ("what should I do?") | Before code-touch — otherwise sunk-cost pressure |
| Vague options ("A: faster, B: cleaner") | Concrete trade-offs (effort estimate + consequences) |

## Real-world impact

Phase B+C+D session: spec had 60% drift vs code reality (see `roadmap-phase-execution-verify-first` application). Three strategic questions via AskUserQuestion (scope/model/persistence) → user 3× Recommended in ~30s.

Outcome:
- ~1.75h implementation instead of spec-naive ~3.5h
- Phase C completely saved (existing position_sizer.py re-used instead of built new)
- JSONB persistence instead of migration (no rollback risk)
- Backward-compat in bot layer for old signals (graceful skip)

Counterfactual without skill: wished-for-implementation would trigger 2-3 user pushback cycles, ~40min re-refactor effort minimum.

## Cross-References

- `roadmap-phase-execution-verify-first` — predecessor step (reality inventory)
- `superpowers:test-driven-development` — follow-up step (implementation)
- `decision-plan-hypothesis-matrix` — related pattern for decision discussions

## Background

Pattern discovered after maxim "Outcome > Tool" + Phase B+C+D experience.

## Background: TDD log (Bulletproofing log)

### Cycle 1 (PASS)

- **RED subagent** (without skill): 6 assumptions without user question (leverage-relative vs strike-delta, JSONB vs new column, sizing semantics, migration order). Wished-for implementation as default. Self-reflection identified worst case correctly: "live trades with wrong sizing → trust damage to entire vision-spec model." But self-reflection is not the default workflow.
- **GREEN subagent** (with skill): Formulated 3 strategic questions with 2-3 options each + Recommended marker. Caller-context bias (subagent without AskUserQuestion tool) explicitly addressed via markdown-simulated block. NO-code-touch gate before user answer maintained.
- **Refactor**: no blocker; cycle-2 backlog extended with subagent caller-context section.

### Cycle-2 backlog (polish, non-blocking)

- **Caller-context section** "subagent without AskUserQuestion → markdown-simulated block + report-up to top-level caller"
- **AskUserQuestion template** as JSON schema code block, so top-level caller can translate subagent markdown block directly into real tool-call
- **Cross-reference** to `subagent-driven-development` for caller-limit topic
