---
name: plan-execution-state-drift-precheck
description: Use before executing any superpowers/gsd-style implementation plan (`docs/superpowers/plans/*.md`, `.planning/PLAN.md`, `roadmap-phase-*.md`) whose plan-file was written in a previous session — to detect whether tasks have already been implemented (in a parallel session, by a different agent, or by the user) before re-executing them. Trigger on phrases like "Plan-Z.1-Execution starten", "executing-plans-skill anwenden", "gsd-execute-phase starten", "phase ausführen", "Plan-file ist vom <gestern/letzter Woche>", "plan written earlier, now executing". Do NOT load for plans written in the SAME session (no drift possible), for plans without git-tracked code-targets (e.g. pure-documentation phases), or when the user explicitly says "I know the codebase is at the pre-plan state" (no need to verify). This skill encodes the 30.05.2026 detour where a 2083-LoC Z.1-Plan was written 29.05. AND all 8 code-tasks were implemented the same day in a parallel session — but the daily-note documented only "plan written". Without `git log <base>..HEAD` precheck, I would have re-implemented tasks 1-8 inline, wasting 60+ min.
---

# Plan-Execution State-Drift Precheck

> **DRAFT — encodes the 30.05.2026 pattern, not yet TDD-promoted.**

## When to use

Before starting execution of any implementation-plan-file whose creation-date is NOT today, OR when there's any chance another agent/session/user-action has touched the codebase since the plan was written. Concrete triggers:

- `superpowers:executing-plans` skill is about to be applied
- `gsd:gsd-execute-phase` or related orchestrator is starting
- User says "execute the plan from yesterday"
- Plan-file mtime is more than 1 hour old at session-start

## When NOT to use

- Plan written and being executed in same session (no time for drift)
- Plan target is pure documentation (no git-tracked code changes expected)
- User explicitly states "codebase is at pre-plan state, proceed"
- Single-commit / single-file plans (overhead > value)

## The Workflow

### Step 1: Identify base + HEAD

Plans usually start from `main` (or a known-base branch). Determine:

```bash
cd <repo-root>
git log --oneline -1   # current HEAD
git log main..HEAD --oneline | wc -l   # commits ahead of base
```

If `commits ahead = 0` → plan-state is pristine, no drift, proceed normally.

If `commits ahead > 0` → continue to Step 2.

### Step 2: List commits since base

```bash
git log main..HEAD --format="%h %ai %s" | head -30
```

Read commit-dates and -subjects.

### Step 3: Match commit-subjects against plan task-headers

Open plan-file, list section headers (`## Task N: ...` or `### Step N: ...`).

For each plan-task, scan commit-subjects for evidence of implementation. Look for:
- `feat(<module>): <plan-component>` — task likely DONE
- `fix(critical): CR-<X> ...` — code-review-fix on a done task, task DONE plus review-cycle
- `test(<module>): ...` — test-only commit, task partially DONE
- `docs(...): ...` — documentation commit, ambiguous

### Step 4: Produce status-table

```markdown
| Task | Plan-Header | Evidence-Commit | Status |
|---|---|---|---|
| 0 | Pre-Flight | (none) | ❌ not done |
| 1 | DB-Migration | feat(db): 3 quarantine tables | ✅ done |
| 2 | Confluence-Cap | feat(setup_detector): C5 + C3 hooks | ✅ done |
| 8 | Backtest | feat(backtest): Multi-Run | ⚠ code committed, RUN-output missing |
| 9 | Vault-side | (none) | ❌ not done |
```

### Step 5: Re-scope BEFORE executing

If significant drift detected (≥ 3 tasks already done), STOP and present to user:

> "Plan ist bereits zu N/M Tasks implementiert (commits XYZ). Adjustierter Scope-Vorschlag: [Option A / B / C]. Welcher passt?"

Wait for user confirmation. Do NOT silently skip done-tasks — that hides relevant context (the user may not know what's been done).

### Step 6: Execute only remaining tasks

After scope-confirmation, proceed with the adjusted task-set, marking already-done tasks explicitly as `[verified-done]` in any todos.

## Anti-Patterns

- ❌ Starting Task 1 without precheck — risks re-implementing already-done work, creating conflicts, or worse: silently overwriting parallel-session code
- ❌ Silently skipping done tasks without showing the user — they need to know what state things are in
- ❌ Marking a task `done` based on commit-subject alone — verify outputs too (e.g., backtest committed code but never ran → outputs missing)
- ❌ Trusting plan's "Step 1 FAIL test" instruction when test would actually PASS now (because code was already implemented) — the TDD-RED-step becomes a no-op

## Cross-References

- Skill: `superpowers:executing-plans` — invokes this as precheck
- Skill: `superpowers:writing-plans` — produces the plans this verifies
- Skill: `superpowers:subagent-driven-development` — same precheck applies before dispatching subagents
- **Complementary** to `plan-execution-stack-mode-precheck-DRAFT` (29.05.2026) — that skill checks **stack-mode** (local-runnable vs remote-only vs hybrid); this skill checks **state-drift** (tasks already done vs not). Run both as Pre-Step-0 before executing.
- **Complementary** to `pre-deploy-code-drift-detection-DRAFT` (29.05.2026) — that skill detects 3-way Mac↔origin↔Server-Drift before rsync; this skill detects Plan↔Codebase-Drift before execution. Different drift-dimensions, both worth checking.

## Genese

30.05.2026: Z.1-Marktphase-Filter-Plan (2083 LoC, 9 Tasks) was written 29.05. 08:42 — and ALL 8 code-tasks + 5 code-review-fixes were committed the same day 08:48-15:13. Daily-Note 29.05. mentioned only "Plan-Z.1 geschrieben"; the implementation was in a parallel session that wasn't logged. I started `executing-plans` skill, was about to dispatch subagents for Tasks 1+2 — `git log main..HEAD` showed 12 Z.1-commits already in. Adjusted scope from "Pre-Flight + DB + Confluence-Cap" to "Pre-Flight + Backtest-RUN", saved 60+ min, AND caught a separate Critical-Bug (CR-D1) during Pre-Flight that the already-implemented code had.

## TODO (Promotion to GA)

- [ ] Verify pattern works for gsd-plans (different file-locations than superpowers/)
- [ ] Add example for "task done but tests failing" — needs different scope-handling
- [ ] Add anti-pattern: don't precheck for trivial single-file plans (overhead)
- [ ] TDD-pair: RED (plan-execution-without-precheck-re-implements); GREEN (with-precheck-detects)
- [ ] Test trigger-keywords surface this skill at execution-time
