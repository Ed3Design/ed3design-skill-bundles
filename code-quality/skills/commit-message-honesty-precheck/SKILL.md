---
name: commit-message-honesty-precheck
description: |-
  Use before writing or finalizing a git commit message, especially when the subject line uses words like "NO-OP fix", "no behavior change", "refactor only", "trivial", "cleanup", "minor", "simple bump", "doc-only" — these phrases are often LIES in disguise that hide real semantic changes. Trigger on phrases like "small fix", "just a refactor", "NO-OP", "behavior unchanged", "trivial change", "harmless cleanup", "just bumping the default", or before any commit that touches a default value, signature, env-var fallback, or filter parameter. Do NOT load for genuinely cosmetic changes (typos, comments-only, whitespace), for first-line spelling, or for non-git contexts (slack messages, jira tickets). Encodes a real self-correction: a commit was titled "Z.1-C5 default cap 5→3 (forensically-proven NO-OP fix)" for a change that blocks 40 trades and shifts win-rate by +0.43pp — that is NOT a NO-OP. A code-review subagent caught it with confidence 88 as Important Finding.

---

# commit-message-honesty-precheck

> ✅ **PROMOTED**: RED subagent identified "NO-OP" as false and suggested a better message — good basis. GREEN subagent applied all 3 steps + smell-table in a structured way, quantified the effect (40 trades blocked, +0.43pp WR), and emitted "PRECHECK: FAILED — message is a lie."

## The pattern

Before finalizing a commit message, especially the subject line:

**Step 1 — List every "no-effect" claim in the message**

Phrases like "NO-OP", "no behavior change", "refactor only", "doc-only", "cosmetic", "trivial", "default adjustment".

**Step 2 — For each claim, compute a behavior-diff proof**

| Smell | Likely lie | What to verify |
|---|---|---|
| "NO-OP" | Change actively blocks/triggers something now | Count rows/trades/calls affected by diff |
| "no behavior change" | Default value or branch condition was touched | grep for old default in tests + production code |
| "refactor only" | Tests were added/removed/renamed | `git show --stat` for new test files |
| "trivial" | Diff touches >1 file or >10 lines | `wc -l` the diff |
| "cosmetic" | Source files (not /docs) were touched | `git diff --stat` by directory |
| "default bump" | A consumer is affected with no opt-in | grep usage of the old default |

**Fallback when no repo access:** argue from the diff description itself. Count lines, identify which code path the new default touches, estimate affected calls. "I have no git access" is no free pass for the NO-OP claim.

**Step 3 — Replace lies with measured facts**

Rewrite the subject line to match the actual diff:
- ❌ `"feat(backtest): Z.1-C5 default cap 5→3 (forensically-proven NO-OP fix)"`
- ✅ `"feat(backtest): Z.1-C5 cap default 5→3 — blocks cc=4/5 days (~40 trades / +0.43pp WR)"`

Correct default-change message (positive example):
- ❌ `"chore: bump MAX_SIGNALS_PER_DAY 5→3 (harmless default)"`
- ✅ `"fix(z.1): scoring cap 5→3 — empirically: >3 signals/day tie up too much capital (~40 trades/day affected)"`

## The trigger case

A forensic SQL analysis showed Cap=5 as "mathematically NO-OP" (max `confluence_count` in training-VTs = 5, so Cap=5 never fired). Then the default was changed to 3 — which blocks cc=4 and cc=5 trades (40 trades, ~7% of sample, +0.43pp WR shift).

Commit message: **"forensically-proven NO-OP fix"** — the phrasing was semantically inverse to the actual diff. Reviewer Finding I1 (confidence 88): "commit message deceives."

**The trap**: "the old default was a NO-OP" ≠ "this change is a NO-OP". These are logically different claims. When you change a previously-NO-OP default to an active one, the CHANGE is NOT a NO-OP.

## Recovery: when an already-pushed commit has a misleading message

Per the maxim "NEW commits rather than amending":
- Do **not** rebase or amend
- **Forward-document** in the next commit's message + daily note
- Example: `"Clarification regarding 3247e28: original message 'NO-OP' was misleading — the change actually blocks cc=4/5 days"`

## Background: TDD progression (Bulletproofing log)

### Cycle 1 — PASS

- **RED subagent** (without skill): identified "NO-OP" as false ("a NO-OP change by definition has no effect"). Suggested a better message. Missing: structured smell-table, 3-step flow, quantification of the effect (how many trades affected?).
- **GREEN subagent** (with skill): applied smell-table ("NO-OP" + "default bump" both hit). Formulated: "PRECHECK: FAILED — message is a lie." Delivered two variants of the correct message (with and without quantification). Identified the core trap: "intent was NO-OP" ≠ "diff is NO-OP".
- **Refactor**: positive example for correct default-change message added (was missing in original). Fallback protocol for "precheck without live-code access" added.

### Cycle-2-Backlog (non-blocking)

1. Git hook that scans commit message draft and warns on smell-words (CI-lint rule)
2. Multi-claim handling: when "NO-OP" AND "minor" appear combined — check both, additive smells
3. Cross-repo examples from 2+ other projects
