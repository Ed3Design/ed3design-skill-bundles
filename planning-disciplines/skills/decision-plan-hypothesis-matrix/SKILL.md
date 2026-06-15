---
name: decision-plan-hypothesis-matrix
description: |-
  Use BEFORE implementing a non-trivial decision-driven task where multiple outcomes are plausible — backtest planning, algorithm comparison, architecture choice, migration strategy, "should build X or not". Trigger on phrases like "should build X", "plan a backtest", "I need a decision", "test algo variants", "how do I measure success", "max-effort session", "choose refactoring strategy", "define Compound-GO". Produces a Plan-Note with explicit Hypothesis-Matrix (each H + counter-thesis + Distinguishing Metric), Compound-GO-Logic, Out-of-Scope, and Done-Definition. Do NOT load for single-path implementations with no decision ("fix this typo"), brainstorming/exploration phase (use `superpowers:brainstorming` first), plans without binary GO/NO-GO outcome (use `superpowers:writing-plans`), or tasks without a measurable success criterion.

---

# Decision-Plan-Hypothesis-Matrix

> ✅ **PROMOTED**: TDD-Pressure-Test Cycle 1 PASS (STRONG). RED subagent delivered a pro/con list with maxim references but no formal hypothesis matrix — no success criterion BEFORE analysis, no distinguishing-metric table, no Compound-GO. GREEN subagent delivered a complete 7-step plan note with 4 hypotheses + counter-theses + distinguishing-metric + Compound-GO branches + out-of-scope + done-checklist. Auto-discoverable.

## Overview

Most non-trivial decisions have a story: "I think X is the right approach, let me try it." That story is often wrong, and you only find out after the implementation. This skill forces explicit hypothesis-formulation + falsification-criteria BEFORE code, so the decision is robust to your initial bias.

**Core principle:** Every substantial decision is a multi-hypothesis problem disguised as a single solution. Make the hypotheses explicit, and the decision becomes data-driven instead of intuition-driven.

## When to use

- Backtest planning (trading algo, ML model variants, A/B framework)
- Algorithm selection (Trail-Stop A vs B, Optimizer X vs Y)
- Architecture choice with multiple valid paths
- Migration strategy with multiple risk profiles
- "Should I build X or not?" — gating before commitment
- Hard-won analysis sessions where you need to convince future-you of the verdict

## When NOT to use

- Single-path implementations (no decision character)
- Brainstorming / requirements-gathering (use `superpowers:brainstorming` first)
- Plans without GO/NO-GO outcome (use `superpowers:writing-plans` for procedural plans)
- Exploration phase where no success criterion exists yet
- Time-boxed prototypes meant to fail-fast

## The 7-step procedure

### Step 1 — Success criterion BEFORE start

Write down the measurable outcome that determines GO/NO-GO. This must be:
- Concrete (Expectancy ≥ +0.05R, p<0.05, < 100ms latency)
- Falsifiable (not "improves UX" — "click-to-action < 200ms 95th percentile")
- Bounded (today's session, this PR, this experiment)

If you can't write the success criterion, you're still in exploration. Defer.

### Step 2 — List 3-5 hypotheses, each with counter-thesis

Each hypothesis = "I think X causes Y". Each counter-thesis = "but Z could also cause Y". The existence of the counter-thesis is the lock against confirmation bias.

| # | Hypothesis | Counter-thesis |
|---|---|---|
| H1 | <claim about cause/effect> | <alternative cause for same effect> |
| H2 | ... | ... |

### Step 3 — Distinguishing metric per hypothesis

For each H/counter-thesis pair: what concrete metric, when measured, would tell you which one is true?

This is the most important step. If you can't define a distinguishing metric, the hypotheses are not actually distinct, and the whole framing is muddled.

| # | Hypothesis | Counter-thesis | Distinguishing Metric |
|---|---|---|---|
| H1 | A causes X | B causes X | Mean of X under condition-A only vs condition-B only — significantly different? |
| ... | ... | ... | ... |

### Step 4 — Define Compound-GO logic

Most decisions are not 1-hypothesis. Define which combinations lead to GO vs NO-GO:

```
GO     ⇔ H1 confirmed AND H3 confirmed AND |Delta| ≥ X
NO-GO  ⇔ H1 refuted   OR  Sample-Size < N
Re-test ⇔ H2 inconclusive (CI overlaps 0)
```

Compound logic prevents "1 weak signal" from carrying a decision.

### Step 5 — Implementation plan (short)

Now that hypotheses + falsification are explicit, the implementation is just "the queries / code that produces the data". List the 3-5 implementation steps. Don't elaborate.

### Step 6 — Out-of-Scope explicit

Write what is NOT in scope. This is your gate against scope-creep mid-session. Examples:
- "Live deployment is NOT in scope — only sim-backtest"
- "Other algorithms (X, Y) are NOT in scope — only PSAR"
- "UI changes are NOT in scope — only backend logic"

### Step 7 — "When is the session done"

Concrete checklist (5-8 items max). Each item must be a yes/no that you can verify at session-end:
- ☐ Library implemented + N tests green
- ☐ Backtest runs against production DB without errors
- ☐ Result note with filled verdict table
- ☐ Compound verdict explicit (GO / NO-GO / re-test)
- ☐ Roadmap-item status updated

## Worked example (PSAR trailing-stop test)

**Step 1 success criterion:**
> Verdict by end of day on whether PSAR-Trailing lifts expectancy — via replay of the last 30 days of virtual_trades vs baseline.

**Step 2-3 hypothesis matrix (excerpt):**

| # | Hypothesis | Counter-thesis | Distinguishing Metric |
|---|---|---|---|
| H1 | PSAR-Trail lifts 30% of 1-1.5R wins to ≥2R | Trail closes too early, distribution similar | Histogram comparison of pnl_r distribution wins |
| H3 | Trail does not lower WR below 40% | Trail increases stop-rate | WR with Wilson-CI |

**Step 4 Compound-GO logic:**
```
GO ⇔ H1 confirmed AND H3 confirmed AND Delta-Expectancy ≥ +0.05R
```

**Step 5 implementation:**
1. Library `core/indicators/psar_trailing_stop.py` + TDD tests
2. Backtest script against 30d virtual_trades
3. Result note with verdict table

**Steps 6-7:** as usual.

**Outcome:** Backtest refuted H1 + H3 → Compound verdict NO-GO. **Without the plan matrix, the next phase would have been live-bot integration** (= 1 day of engineering for a net-negative algorithm).

## Anti-patterns

- ❌ Hypothesis list without counter-thesis ("I think X because reasons") — removes the falsification possibility
- ❌ Distinguishing metric "we'll just look at the data" — not concrete enough, lets confirmation bias through
- ❌ Single-hypothesis Compound-GO ("if H1 confirmed → GO") — one statement deciding is fragile, always ≥2 conditions
- ❌ Implementation steps with > 8 lines — plan becomes spec, loses decision character
- ❌ Out-of-Scope empty — missing the scope-creep protection shield
- ❌ Adjusting success criterion retroactively when data doesn't fit ("actually Y is the real criterion") — decision hygiene gone

## Template snippet

```markdown
# <Topic> — Plan YYYY-MM-DD

## Success criterion
> <one measurable sentence>

## Hypothesis matrix
| # | Hypothesis | Counter-thesis | Distinguishing Metric | Consequence if H | Consequence if ¬H |
|---|---|---|---|---|---|
| H1 | ... | ... | ... | GO hint | NO-GO hint |
| ... | ... | ... | ... | ... | ... |

## Compound-GO logic
- **GO** ⇔ <combination>
- **NO-GO** ⇔ <combination>
- **Re-test** ⇔ <combination>

## Implementation plan (max 8 steps)
1. ...

## Out-of-Scope (today)
- ...

## When is the session done
- ☐ ...
```

## Skill composition

- `superpowers:brainstorming` — runs BEFORE this skill if requirements are unclear
- `superpowers:writing-plans` — alternative for procedural plans WITHOUT decision character
- `superpowers:test-driven-development` — runs AFTER for the implementation step
- `compound-gate-over-single-metric-DRAFT` — related but smaller scope (no hypothesis matrix part)

## Background: TDD log (Bulletproofing log)

### Cycle 1 (PASS — STRONG)

**Scenario** (typical question for production system):
> I'm considering building an RSI-divergence filter (14-bar bullish divergence as required for long signal) as Layer 3. Should I build that?

**RED subagent** (without skill): Delivered a structured pro/con list with maxim references (Cardwell, Backtest-First, coin-flip problem). Implicitly at the end formulated "3 criteria Compound-GO". Self-reflection honest: "no formal hypothesis matrix, no real H/counter-thesis with distinguishing metric, success criteria constructed during (not before) the answer from gut feeling". Had the user followed it, 5 uncalibrated risks would have remained open (divergence-definition drift, WR-only metric, sample size, overfitting door, implicit layer-1+2 filterability assumption).

**GREEN subagent** (with skill): Delivered complete plan note in skill format:
- Success criterion concrete + falsifiable (Δ-Expectancy ≥ +0.05R, N ≥ 80, Wilson-LB-WR ≥ 40%)
- 4 hypotheses with real counter-theses + concrete distinguishing metrics (Bootstrap-CI, Wilson-CI, retention share, per-instrument top-2)
- Compound-GO with AND-conjunction across all 4 H, plus re-test branch for borderline cases
- Out-of-Scope with 7 explicit exclusions (live bot first gated)
- Done checklist 8 verifiable items
- None of the 7 steps skipped

**Verdict**: STRONG PASS. RED shows clear anti-pattern (pro/con instead of matrix), GREEN shows qualitative leap. Promotion done.

**Refactor applied**: no code changes — polish items documented as cycle-2 backlog (non-blocking).

### Cycle-2 backlog (polish, non-blocking)

1. **Heuristic when 3 vs 5 hypotheses** — Skill says "3-5", but gives no bottom-up rule. Proposal: "minimum 1 edge-H + 1 robustness-H + 1 tradability-H" (from GREEN subagent proposal)
2. **Power-check sub-step in Step 1** — for statistics-driven decisions (Bootstrap-CI, Wilson) additionally power analysis: "is N realistic for effect size E with significance level α?"
3. **Out-of-Sample validation as required in re-test branch** — currently only implicit, should be explicit as decision hygiene
4. **Live-application log** — tracking mechanic to count how often the skill triggers (for future promotion-audit logs)

Iron law: cycle-2 items are treated with failing-test-first before application, not as "silent edit".
