---
name: code-review-backlog-cost-warning
description: Use when the user/agent is about to push code, merge a feature branch, or claim a body of work as "done" AND no code-review has happened in a while. Specifically trigger when ANY of these hold — (a) >7 days since last `requesting-code-review` invocation on this codebase, (b) >30 atomic commits accumulated since last review, (c) >5000 LoC changed since last review, (d) pre-push-hook code-review-warning has been bypassed ≥2 times in succession (bypass multiplication), (e) the user types phrases like "we haven't done a review in weeks", "I'll just push this", "the hook is only a warning, ignore it", "it's just a small fix on top". STOP and surface a cost-estimate-warning to the user BEFORE the push — quantify the expected backlog-cost (wallclock + token-budget + re-review cycles) and offer chunked-parallel-review-dispatch as the alternative. Maxim: "Code review must become standard" — encodes a painful proof-by-instance where 4 weeks without review = 5h wallclock + $50 tokens + 21 commits in 6 phases + 3 re-review cycles in ONE session vs ~10min/day with daily review. Do NOT load for fresh branches (≤3 commits, ≤500 LoC, ≤2 days), for explicitly-marked WIP pushes the user asked you to do without review ("just push, I'll review later"), or when running inside a `requesting-code-review` session itself (you're already reviewing). Also skip for one-line typo fixes / pure documentation commits. Complements `superpowers:requesting-code-review` (this skill is the warning-before, that skill is the review-during) and `code-review-chunk-dispatch` (this skill recommends it, that skill executes it).
---

# Code-Review-Backlog Cost Warning

> ✅ **PROMOTED** — TDD Cycle 1 PASS (moderate value-add). RED subagent: correctly refused the push based on the CLAUDE.md maxim, but unstructured and without concrete cost-quantification. GREEN subagent: delivered a structured mandatory output block with concrete cost table (45 commits / 6,200 LoC / 13d → table row 4), explicit Option A vs. Option B, "Which option?"-stop per Step 4. Value-add: quantification + trajectory hint (cycle repeats vs earlier instances). Polish items in the Cycle-2-Backlog at the end.

## Overview

Code-review backlogs are **superlinearly more expensive** than daily review — not linear. With 5x as many commits without review, the cleanup cost is not 5x but 20-50x higher, because:

- Re-review cycles accumulate (Fix-1 produces Fix-2-bug, Fix-2 produces Fix-3-bug)
- Schema-drifts cumulate in multiple paths simultaneously
- Pre-push suite cycle-time × #push-cycles becomes the dominant wallclock position
- Domain decisions must be made retroactively for 4 weeks of work

**This maxim is the cost-warning variant** of the maxim "code review must become standard". It prevents another large backlog from forming next time because the pre-push-hook warnings are "only a warning".

## When to use

**Trigger thresholds (≥1 sufficient)**:
- ≥7 days since last code review on this repo
- ≥30 atomic commits since last review (`git log <last-review-sha>..HEAD --oneline | wc -l`)
- ≥5000 LoC diff (`git diff <last-review-sha> HEAD --stat | tail -1`)
- ≥2 consecutive pre-push code-review hook bypasses (bypass multiplication)

**Trigger phrases** (user or you):
- "we haven't done a review in weeks"
- "just push this"
- "the hook is only a warning, can be ignored"
- "it's just a small fix on top"
- "we'll do an aggregate review later"
- "let's first finish the feature"

**High-risk markers** (additional amplifiers):
- Multiple critical paths / DB migrations / ML models touched simultaneously
- Multiple domain decisions flowed in without test-backing
- Pre-push-hook has fired ≥3x since last review (accumulated risk)

## When NOT to use

- **Fresh branch** (≤3 commits, ≤500 LoC, ≤2 days) — backlog not yet built up
- **Explicit WIP push** from user ("just push, I'll review later at merge")
- **During a `requesting-code-review` call** — you're reviewing right now, would warn yourself
- **One-line typo fixes** / pure documentation commits
- **Hotfix pressure** (live outage, trade-stop) — then "push first, review after" is the correct reflex, but **document** that a follow-up review is required

## The 4-Step Warning Flow

### Step 1 — Measure backlog size (don't guess)

```bash
# When was the last code-review push?
git log --grep="code-review\|code review\|CR-[A-Z][0-9]" --oneline -5
# Or: last PR-merge after review
git log --first-parent main --oneline -10

# Backlog size from that point
LAST=<sha-of-last-reviewed-commit>
git log $LAST..HEAD --oneline | wc -l         # #commits
git diff $LAST HEAD --shortstat               # LoC + files
git log $LAST..HEAD --since="7 days ago" --oneline | wc -l  # 7d rate
```

Write the 3 numbers explicitly: **commits / LoC / days**.

### Step 2 — Cost-estimation against threshold table

| Backlog size | Expected cleanup cost | Method |
|---|---|---|
| ≤3 commits / ≤500 LoC / ≤2 days | ~5min, single subagent | inline review |
| 4-10 commits / ≤2k LoC / ≤7 days | ~15-30min, 1-2 subagents | `superpowers:requesting-code-review` |
| 11-30 commits / 2k-5k LoC / ≤14 days | ~1-2h, 2-3 chunks | `code-review-chunk-dispatch` (3 chunks) |
| **>30 commits / >5k LoC / >14 days** | **>3h wallclock + re-review cycles + domain decisions** | `code-review-chunk-dispatch` (6+ chunks parallel) |
| **>70 commits / >10k LoC / >28 days** | **5h+ wallclock + $50+ tokens + 2 sessions** | **STOP — user warning + plan-B proposal** |

### Step 3 — Warn user explicitly (don't silently work)

**Mandatory output** before any code is written:

```
⚠️ Code-Review Backlog Warning

Status: <N> commits since <SHA-short> (<K> days ago)
        <M> LoC diff, <T> files touched
        Pre-push hook bypassed X times since <date>

Expected cleanup cost (see `code-review-backlog-cost-warning`):
- Wallclock: ~<hours>
- Token budget: ~$<estimate>
- Re-review cycles likely (bug-finding rate at 4-week backlog: ~3 of 6 phases)

Proposal:
  Option A — `code-review-chunk-dispatch` (N parallel subagents, ~1-2h)
  Option B — Continue push + pain later ($50+, 5h+, 2 sessions)

Maxim: "Code review must become standard"
Maxim: "...$50 burned..."
```

### Step 4 — Wait for user decision

**Do not** simply push. **Do not** simply start chunk review. **The user chooses** — they have budget awareness, you have only the cost estimate.

If the user chooses Option B: document the choice in Daily Note ("User read warning + consciously pushed, follow-up review scheduled for …").

## Quick Reference

| Question | Quick check |
|---|---|
| When was last review? | `git log --grep="CR-\|code-review" --first-parent -3` |
| How many commits since then? | `git log <sha>..HEAD --oneline \| wc -l` |
| How much code-diff? | `git diff <sha> HEAD --shortstat` |
| Where is the next threshold? | see table Step 2 |
| Which chunk skill? | `code-review-chunk-dispatch` (in skills list) |

## Anti-Patterns (what happens when you ignore this)

| Anti-Pattern | Experienced damage |
|---|---|
| "Pre-push hook is warning, ignore" 4x → 8x bypassed | Backlog grows from 30 to 74 commits silently |
| "We don't need chunks, one subagent suffices" | Subagent context overflows, findings incomplete |
| "Re-review per phase is bureaucracy" | 3 of 6 phases had bugs on first pass — without re-review, unnoticed in live code |
| "Tests + live-smoke replace review" | 3 Critical bugs were in live production for weeks |
| "Let's first finish the feature" | Feature gets completed, review never caught up |

## Cost of Skipping (real)

**User quote**:
> "The 'cleanup work' this morning consumed the complete token-limit of two sessions plus additional tokens for $50. That's what happens when you leave things sitting too long."

**Concrete**:
- 74 commits over 4 weeks → 5h wallclock + $50 tokens + 21 repair commits + 3 re-review cycles
- 8 push cycles × 9min pre-push suite = 72min just for push wallclock
- 5 Critical findings + 25 Important findings all live-relevant
- 6 implementation phases because thematically not separable after the 4-week mix

With daily review (maxim): ~10min × 28 days = **4.5h total** instead of 5h-in-one-session + $50.

## Red Flags — STOP and warn

- "just a small change on top"
- "the hook is only a warning"
- "we'll do it next week in a block"
- "I'll just push, review at merge"
- "4 weeks isn't that long"

**All mean: issue user warning, show cost estimate, propose chunked dispatch as default.**

## Cross-References

- **REQUIRED COMPLEMENT**: `superpowers:requesting-code-review` (the review action itself)
- **REQUIRED COMPLEMENT**: `code-review-chunk-dispatch` (for >30-commit backlogs)
- **Maxim**: `pre-push-bypass-audit-trail` (for hook-bypass logging)
- **Source lesson**: `.remember/core-memories.md` § "Code-review backlog becomes more expensive than daily review"

## Background: TDD progression (Bulletproofing log)

### Cycle 1 — PASS, moderate value-add

- **RED subagent** (without skill, scenario "45 commits since recent date, 6,200 LoC, user wants to push with --no-verify"): reacted surprisingly well — refused the push, cited CLAUDE.md maxim ("Code review must become standard") + similar existing skills (`code-review-chunk-dispatch`, `pre-push-bypass-audit-trail`). But: unstructured, no concrete cost table, no quantitative bug-cost estimate. Self-critique listed 6 missing points (no quantification, no audit-trail mechanic, "tonight feature" not addressed emotionally, no Option B, counter-thesis check skipped).

- **GREEN subagent** (with skill): structured output with threshold table (3 of 4 thresholds simultaneously exceeded), mandatory-output block 1:1 from skill template, cost estimation wallclock+token+re-review cycles, explicit Option A (chunk-dispatch now, ~1.5-2h) vs Option B (push + audit-trail-doc + follow-up appointment), clear "Which option?"-stop per Step 4 — no preemptive action.

- **Anti-pattern avoided**: GREEN explicitly noted that without skill the response would have been "OK, I'll push with --no-verify and you'll review tomorrow" → bypass-multiplication that led to the painful cleanup session.

- **R0** (no refactor applied): skill delivered all core steps correctly. Polish items documented as Cycle-2-Backlog (see below).

### Cycle-2-Backlog (Polish, non-blocking)

1. **Bypass multiplication: differentiate levels**: 1st bypass = warning enough; 2nd bypass = escalation. Currently the skill reads as if multiplication is already underway at the 1st bypass case.
2. **"Feature-start pressure"** as an explicit When-NOT clause or its own sub-trigger alongside hotfix pressure. Currently you have to categorize it as a variant of "first finish feature" — the subagent did that, but an explicit line would be more robust.
3. **Chunk-axis mini-hint** for Step-4 transition ("typical chunk axes: thematic / per-dir / per-file-type / per-domain") — even though the real chunk skill is linked, an inline hint simplifies the transition.
4. **Daily-note template** for Option-B doc: currently only "document the choice", no concrete format. A 2-line template would standardize the audit trail.
