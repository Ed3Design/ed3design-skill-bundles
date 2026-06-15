---
name: plan-execution-state-drift-precheck
description: |-
  Use before executing any superpowers/gsd-style implementation plan (`docs/superpowers/plans/*.md`, `.planning/PLAN.md`, `roadmap-phase-*.md`) whose plan-file was written in a previous session — to detect whether tasks have already been implemented (in a parallel session, by a different agent, or by the user) before re-executing them. Trigger on phrases like "start Plan-Z.1 execution", "apply executing-plans skill", "start gsd-execute-phase", "execute phase", "plan file is from <yesterday/last week>", "plan written earlier, now executing". Do NOT load for plans written in the SAME session (no drift possible), for plans without git-tracked code targets (e. g. pure-documentation phases), or when the user explicitly says "I know the codebase is at the pre-plan state" (no need to verify). This skill encodes a detour where a 2083-LoC Z.1 plan was written one day AND all 8 code tasks were implemented the same day in a parallel session — but the daily note documented only "plan written". Without `git log <base>..HEAD` precheck, the tasks 1-8 would have been re-implemented inline, wasting 60+ min.

---

# Plan-Execution State-Drift Precheck

> ✅ **PROMOTED** 2026-06-15 — TDD pressure-test PASS. RED-Subagent received plan written 2 days ago + team-reviewed yesterday + Task 1 `INSERT INTO v3_signals` with assumed 5-column schema, "execute Task 1". Action: read plan, then execute INSERT directly. Honesty: "I would not have run `\d v3_signals` before executing the INSERT. I would have trusted the plan + team-review as sufficient evidence. Plan-review ≠ schema-currency. Team-review validates intent and logic; it does not freeze the DB." GREEN-Subagent ran `git log main..HEAD --oneline` first, then `\d v3_signals` schema-verify, cross-referenced Vault-CLAUDE-Maxime "SQL-Spalten immer via Schema verifizieren", proposed STOP+status-table-to-user at drift-detection. Cycle-2 polish in TDD-Verlauf log below.

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

> "Plan is already implemented for N/M tasks (commits XYZ). Adjusted scope proposal: [Option A / B / C]. Which fits?"

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
- **Complementary** to `plan-execution-stack-mode-precheck-DRAFT` — that skill checks **stack-mode** (local-runnable vs remote-only vs hybrid); this skill checks **state-drift** (tasks already done vs not). Run both as Pre-Step-0 before executing.
- **Complementary** to `pre-deploy-code-drift-detection-DRAFT` — that skill detects 3-way local↔origin↔server drift before rsync; this skill detects plan↔codebase drift before execution. Different drift dimensions, both worth checking.

## Genesis

A Z.1 market-phase filter plan (2083 LoC, 9 tasks) was written one morning — and ALL 8 code tasks + 5 code-review fixes were committed the same day. The daily note mentioned only "Plan Z.1 written"; the implementation was in a parallel session that wasn't logged. The `executing-plans` skill was started, about to dispatch subagents for tasks 1+2 — `git log main..HEAD` showed 12 Z.1 commits already in. Scope was adjusted from "Pre-Flight + DB + Confluence-Cap" to "Pre-Flight + Backtest-RUN", saving 60+ min, AND a separate Critical-Bug (CR-D1) was caught during Pre-Flight that the already-implemented code had.

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-15 (PASS)

- **RED-Subagent** (without skill, plan written 2 days ago + team-reviewed yesterday + Task 1 `INSERT INTO v3_signals (ticker, score, side)` with assumed 5-column schema): chose read-plan + execute-INSERT-directly. Honesty: "I would NOT have run `\d v3_signals` before executing. I would have trusted the plan + team-review. Plan-review ≠ schema-currency. Team-review validates intent and logic; it does not freeze the DB." Listed failure modes: silent NOT-NULL-column-added with default capturing wrong semantics, column-rename, NOT-NULL-constraint-added to existing nullable column.
- **GREEN-Subagent** (with skill, identical scenario): ran `git log main..HEAD --oneline | wc -l` first, then `\d v3_signals` schema-verify, cross-referenced project-CLAUDE.md maxim "SQL-Spalten immer via Schema verifizieren" (08.06.2026), proposed STOP+status-table-to-user if drift detected. Self-reflection: "skill cross-reference to `schema-verify-via-information-schema` would strengthen the workflow".

### Cycle-2-Backlog (Polish, non-blocking)

- Cross-reference `schema-verify-via-information-schema` skill explicitly as parallel precheck dimension (orthogonal to commit-drift)
- Even when `git log main..HEAD` shows commits-ahead=0, schema-verify should remain mandatory (Vault-CLAUDE rule trumps skill's "proceed normally")
- Verify pattern works for gsd-plans (different file-locations than `docs/superpowers/plans/`)
- "Task done but tests failing" edge-case — needs different scope-handling
- Anti-pattern: don't precheck for trivial single-file plans (overhead exceeds value)
