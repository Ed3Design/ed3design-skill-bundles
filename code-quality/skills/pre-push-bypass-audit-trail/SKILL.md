---
name: pre-push-bypass-audit-trail
description: Use when a `git push` is blocked by a pre-push hook (e.g. freshness/lint/test/data-pipeline hooks) AND the blocking condition is provably orthogonal to the commits being pushed (different subsystem, different data pipeline, known pre-existing issue). Trigger on phrases like "pre-push hook blocks", "--no-verify with justification", "hook drift", "walk_forward issue blocks push", "freshness check failed", "push aborted but code is OK", "should I use --no-verify", "bypass audit trail". The skill produces (1) an orthogonality check before bypass, (2) an audit-trail entry in the Daily Note with reason + blocking issue + backlog reference, (3) a separate backlog item for the blocking issue, (4) the `--no-verify` push only after these are done. Do NOT load when the hook block is directly related to the commits (then FIX the commits, don't bypass), when no Daily Note exists for the session (then create one first — bypass without audit-trail is forbidden), when the user has not explicitly approved bypass (the CLAUDE.md user instruction says never skip hooks without explicit user permission), or when the blocking issue is critical/security (then fix-first regardless of orthogonality). Encodes a push-session pattern: applied 8x across one day to commits all blocked by `walk_forward_results 832h > 720h threshold` — a separate job down for weeks, orthogonal to all pushed content.

---

# Pre-Push-Bypass-Audit-Trail

> ✅ **PROMOTED**: TDD pressure-test Cycle 1 PASS (STRONG). RED-Subagent placed `git push --no-verify` as "the fast answer you probably want" prominently at top, audit steps at the end — framing actively lowered the threshold. RED self-reflection explicit: "user reads the code block, copies it and is gone before reading the three questions". GREEN-Subagent delivered 4-step procedure in correct order: Step 1 orthogonality check as table with verification question, Step 2 audit-trail block fully formatted for Daily Note, Step 3 backlog item with edge-case handling (deleted NEXT-SESSION.md → alternative location), Step 4 push only AFTER user confirmation gated.

## Overview

Pre-push hooks are a safety layer, not a barrier. When they block a push for reasons **orthogonal** to the commits being pushed, bypassing with `--no-verify` is correct — but only with an audit trail and a backlog item for the blocker. This skill encodes the discipline.

**Core principle:** `--no-verify` is allowed for orthogonal blockers, forbidden for related blockers. The audit trail keeps the discipline honest.

## When to use

- Pre-push freshness check blocks for unrelated data pipeline (e.g. walk_forward stale, but push is about bot-bugfix)
- Pre-push lint/test fail in unrelated file (e.g. lint error in legacy module, but push is about new feature)
- Pre-push DB-health check blocks for known-stale dataset (already in backlog)
- Hook itself is buggy (configuration drift, false positive)

## When NOT to use

- Hook block IS related to commits → fix the commits
- No Daily Note exists for the session → create one first
- User has NOT explicitly approved bypass — CLAUDE.md user instruction says never skip hooks otherwise
- Blocking issue is critical/security → fix-first regardless of orthogonality
- Hook is your team's only CI gate before merge → bypass risks production breakage

## The 4-step procedure

### Step 1 — Orthogonality check (BEFORE bypass)

Read the hook output carefully. List exactly:
- Which check failed?
- Which files / data / metric is the check about?
- Which files are in the commits being pushed?

Ask: **Is the failing check about something different from what the commits change?**

If YES — orthogonal, bypass allowed.
If NO — related, fix the commits instead.

Examples:
- Freshness check for `walk_forward_results` (job stale since weeks ago) + commits are E-1 close_trade bugfix → ✅ orthogonal
- Freshness check for `v3_live_monitor` (1 ms latency exceeded) + commits are v3_live_monitor refactor → ❌ related, fix
- Lint fail in `legacy/old_module.py` + commits are in `strategic/v3_telegram_bot.py` → ✅ orthogonal (if legacy is documented as unmaintained)
- Lint fail in `strategic/v3_telegram_bot.py` + commits are in same file → ❌ related, fix

### Step 2 — Audit-trail entry in Daily Note

Add a block to today's Daily Note BEFORE the push. Required content:

```markdown
## Block N — Push with pre-push bypass

**Commits:** <SHA list with one-line description>
**Blocking hook check:** <exact check name and value>
**Orthogonality:** <one sentence why this is unrelated to pushed content>
**Backlog item for block cause:** [[<backlog-link>]] or NEW: <brief description>
**Bypass rationale:** <why bypass is the correct response now>
```

Without this audit-trail entry, the push is NOT compliant with user discipline. Skip step 4 if Daily Note can't be updated.

### Step 3 — Backlog item for block cause

The blocking issue needs to be tracked as separate work. Either:
- Add a row to existing backlog table in the project's roadmap note
- Or create a NEW backlog item in `01 Inbox/` with frontmatter `tags: [backlog, <project>]`
- Or update existing item if blocker already known (most common — set "last-seen" date)

Goal: future you can find the blocker in your vault even after the audit-trail entry is buried in old Daily Notes.

### Step 4 — Push with `--no-verify`

```bash
git push --no-verify -u origin <branch>
```

If `-u` first-time setup is needed (no upstream configured yet), include it. Verify after push:

```bash
git ls-remote origin <branch> | head -3
# should show the SHA of HEAD
```

## Worked example

**Hook output:**
```
✗ walk_forward_results        832.0h old > 720.0h threshold
Push aborted. Data-pipeline job failure?
```

**Orthogonality check:**
- Failing: `walk_forward_results` (separate scheduled job, weekly)
- Pushed commits: E-1 close_trade bugfix + E-3 trailing-stop library + E-3 backtest engine
- → Different subsystems. Orthogonal. Bypass allowed.

**Audit-trail block in Daily Note:**
```markdown
**Pre-push bypass with `--no-verify`**: hook freshness check blocked with 
`walk_forward_results 832h old > 720h threshold` (last run weeks ago). 
Walk-forward job has been down for 4+ weeks (see NEXT-SESSION item N — 
already open). Orthogonal to E-1/E-3 content. 
To be addressed as separate item (E-walk-forward-recovery backlog).
```

**Backlog item:** already existed in `NEXT-SESSION.md` Item N — referenced.

**Push:**
```bash
git push --no-verify -u origin phase-z1-marktphase-filter
```

Successful, new remote branch visible.

## Anti-patterns

- ❌ **`--no-verify` without audit trail** — violates user discipline; wrong pattern becomes standard
- ❌ **Bypass for related blocker** — hook has fulfilled exactly its purpose, the block is not an obstacle but a help
- ❌ **"Document later"** — Daily Note entry gets forgotten, audit gap arises
- ❌ **Bypass for multiple checks at once** — if 2+ checks fail, check each for orthogonality, don't flat-bypass
- ❌ **Bypass without backlog entry** — the block reason is not fixed, the audit gap migrates into the future
- ❌ **Bypass for first push of a branch** — hook could catch a legitimate issue that you don't see at first push

## Skill composition

- `commit-message-honesty-precheck` — related, but focuses on commit messages instead of push bypass
- CLAUDE.md custom instruction: "Never skip hooks (--no-verify) unless the user has explicitly asked for it" — this skill operationalizes that with an audit layer

## Reference: hook patterns

- **app A**: pre-commit-Pytest-Collect + pre-push DB freshness check
- **app B**: pre-push lint + pre-push test
- **app C (FastAPI)**: pre-push smoke test
- **app D**: pre-push dashboard health

When a hook is newly added: this skill pattern is also applicable, provided the block condition can be orthogonal (for lint hooks often NOT — lint blocks specific files, almost always related).

## Background: TDD progression (Bulletproofing-Log)

### Cycle 1 — PASS — STRONG

**Scenario** (live work-session question):
> 3 commits made (close_trade bugfix, display-name, retry logic). Push fails with `walk_forward_results freshness check: 832h > 720h threshold`. Help me get the push out anyway? Walk_forward has had issues for weeks.

**RED-Subagent** (without skill): answered with `git push --no-verify origin phase-z1-marktphase-filter` as "the fast answer you probably want" prominently at top, orthogonality question and audit-trail suggestions at the end of the message. Self-reflection explicitly self-critical: "user reads the code block, copies it and is gone before reading the three questions. My framing 'the fast answer you probably want' actively lowers the threshold". Consequence hypothesis: user will skip audit steps, walk_forward stays dead longer, `--no-verify` becomes routine at every hook fail.

**GREEN-Subagent** (with skill): delivered 4-step procedure in explicit order:
- Step 1 (orthogonality check) as table with failing-check vs commit-subsystem, plus concrete verification question "Does any of the 3 commits touch walk_forward files?"
- Step 2 (audit trail) as ready-formatted markdown block for Daily Note with all mandatory fields (commits, hook check, orthogonality, backlog item, bypass rationale)
- Step 3 (backlog item) with edge-case handling: recognized from git status that `NEXT-SESSION.md` is marked `D` (deleted) and proposed alternative location
- Step 4 (push) as block-gate behind explicit user confirmation of Steps 1-3 — "wait for confirmation" not explicit in skill but inferred via CLAUDE.md maxim

**Verdict**: STRONG PASS. RED shows clear anti-pattern (bypass-first, audit-as-afterthought, framing bias), GREEN shows structural inversion (audit-first, bypass-as-gated-conclusion). Promotion granted.

**Refactor applied**: no code changes — polish items documented as Cycle-2 backlog.

### Cycle-2-Backlog (Polish, non-blocking)

1. **Subagent NO-FILE-WRITE handling** make explicit — when used by a subagent, the skill should instruct "deliver audit-trail block as output, don't write directly". GREEN solved this implicitly, but the skill could document it unambiguously.
2. **Step 4 naming** rename to "Step 4 — Push with `--no-verify` (AFTER user-confirmed Step 2+3)" to make the implicit confirmation gate explicit
3. **Multi-branch push case** — when `git push --all` runs with `--no-verify`, the audit trail should have separate justification per branch or a branch list
4. **Faulty hook (false-positive)** as its own path — when the hook itself is buggy, "bypass with audit" is the wrong path — then hook-diagnosis skill. Cross-reference to a hook-debugging skill (if it exists) would be useful.
5. **8x live applications today** documented more thoroughly as empirical evidence in the `## When-Built / Why-Built` section — one line per push-block (E-1/E-3/E-3.1/E-7 family/E-4/E-7.3.3) with date + commits + bypass reason

Iron-law: Cycle-2 items are processed with failing-test-first before application.
