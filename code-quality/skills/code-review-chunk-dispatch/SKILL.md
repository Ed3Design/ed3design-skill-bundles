---
name: code-review-chunk-dispatch
description: Use when the code-review-backlog is large (>30 commits OR >5,000 LoC changed since last review) AND the caller has Agent/Task-tool dispatch capability (i.e., top-level orchestrator or main Claude session). Trigger on phrases like "code-review backlog is big", "no review for weeks", "many commits without review", "review of 100+ commits", "how do I review these 200 commits", "chunk review", "parallel code-reviewer subagents". Do NOT load for single-PR review (use superpowers:requesting-code-review directly), for <30-commit backlog (single subagent suffices), for non-Git codebases (chunking-by-SHA-range presumes git workflow), or when running as a subagent yourself without Agent-tool access (the chunk-dispatch pattern is then unexecutable — use risk-based-triage instead, documented in the skill's Fallback section). Complements (sub-of) `superpowers:requesting-code-review` and `superpowers:dispatching-parallel-agents`.
---

# code-review-chunk-dispatch

> ✅ **PROMOTED**: TDD-Cycle-1 (caller-context refactor) + TDD-Cycle-2 (Mini-Verify-Fallback PASS, S3-Pattern-Mode-Value-Prop CONFIRMED) passed. Auto-discoverable. Polish items from Mini-Verify subagent feedback incorporated: sample definition, counter-thesis depth hierarchy (Critical=mandatory / Important=recommended / Minor=optional), tabular trust-verdict format in fallback, TDD progression as Background label.

## STOP — Caller-Context-Check (before anything else)

This skill recommends **parallel dispatch via sub-subagents**. That presumes: **YOU (the caller) have an `Agent`/`Task` tool**.

**Before doing anything else, check**:

| Caller check | Action |
|---|---|
| Do I have access to the `Agent` tool (top-level orchestrator, main Claude session)? | ✓ → continue with `## Pattern (short form)` and dispatch |
| I do NOT have the `Agent` tool (e.g., I'm a subagent myself)? | → jump to `## Fallback: Sequential-Triage-Mode` BELOW. **Do not try to force the chunk pattern sequentially.** |

**Anti-pattern**: blindly following the skill and chunking sequentially even though you can't parallel-dispatch — that's **worse** than natural risk-based triage. Proven by TDD-Test (see `## TDD progression` below): GREEN-Subagent without Agent-tool produced WORSE result (1 instead of 4 Critical findings, +70% wallclock) through forced chunking than a baseline subagent without skill that applied natural risk-based triage.

**Rationalization trap**:

| Rationalization | Reality |
|---|---|
| "The skill says chunk, so I chunk sequentially" | The skill presumes PARALLEL dispatch. Sequential chunking does NOT deliver the skill's promise, but has the overhead. |
| "My caller surely has Agent-tool, I'm a code-reviewer after all" | Check it. If `Agent`-tool not in your tool-set → you are a subagent. |
| "A bit of chunking is better than none" | Wrong. Risk-based triage without artificial chunks is better documented (see fallback). |
| "The caller wants to see chunks" | The caller wants good bugs. Coverage-disclosure in the report is more transparent than chunk-theater. |

## Pattern (short form)

When the code-review-backlog is large (heuristic: >30 commits OR >5,000 LoC OR >4 weeks without review):

1. **Measure scope reality** — `git log --since`, `git diff --stat`, commit count
2. **Identify thematic chunks** — ≤15 commits per chunk, ≤6 chunks total covering high-stake-recent-work, tail (old + less time-critical) as a separate backlog block
3. **Determine per-chunk a BASE_SHA / HEAD_SHA range** with `git rev-parse <sha>~1` for inclusive starts
4. **Parallel dispatch** in a single message block with multiple Agent-tool invocations (NOT sequentially — wastes wallclock)
5. **Aggregate** findings by Critical / Important / Minor + chunk-trust assessment (Acceptable / Acceptable-with-fixes / Rollback-suggested)

## Fallback: Sequential-Triage-Mode (when you have NO Agent-tool)

You landed here because the caller-context check above showed: you can't parallel-dispatch. **DON'T chunk**, do risk-based triage:

1. **Measure scope** as above (`git log --since`, `git diff --stat`, commit count) — still required for reporting
2. **Identify risk domains** instead of thematic chunks:

| Domain | Content | Read depth |
|---|---|---|
| HIGHEST | Money-path (trading logic, payments, auth, live persistence, order execution) | Full-text read of all touched files |
| HIGH | Adjacent to money-path (notifications, schedulers, background jobs, ML inference, DB migrations) | Full-text read of diff-relevant files |
| MEDIUM | Operations / UI / cockpit | **Sample = at least core methods (entry points + public API) of each diff-relevant file, plus targeted grep passes for suspected anti-patterns. Files <200 LoC completely.** |
| LOW | Tests, docs, templates, legacy moves, config reshuffles | Skim via commit messages + `git diff --stat`, not line-by-line. Sample only when test logic backstops a Critical fix. |

3. **Targeted grep passes** for domain-typical anti-patterns (e.g. `_load_*` 2x in the same statement, `direction.*==.*"LONG"` for casing drift, `cur.execute.*UPDATE.*WHERE` without `rowcount` check)
4. **Findings by severity** as in the main pattern (Critical / Important / Minor)
5. **Counter-thesis check**: 
   - **Critical → MANDATORY**: can the bug have another explanation? Is the diagnosis backed by code/schema/log?
   - **Important → RECOMMENDED**: for non-obvious findings explicitly write out counter-thesis
   - **Minor → OPTIONAL**: only when reviewer is uncertain
6. **EXPLICIT-COVERAGE-DISCLOSURE in the report — mandatory**:
   - Which files / modules did I read COMPLETELY?
   - Which did I sample?
   - Which did I NOT read?
   - That way the caller knows what the review does NOT cover → can specifically request more.

**Why not artificial chunking?** Without parallel dispatch, chunking is pure-overhead — it forces you to allow less depth per chunk, without delivering the throughput advantage. Risk-based triage scales better on single-threaded and delivered more Critical findings in the RED-S1-Test than the forced sequential chunking in the GREEN-S1-Test.

**Output format for fallback mode** (same as main pattern, plus coverage-disclosure + tabular verdict):
```
## Approach
[Risk-based triage, which domain tiers were read at what depth]

## Coverage-Disclosure
Fully read: [list of files]
Sample (core methods + grep): [list]
Not read: [list or domain description]

## Findings
### Critical (each with counter-thesis check)
### Important (with counter-thesis check for non-obvious)
### Minor

## Trust-Verdict (tabular, one row per domain)
| Domain | Read depth | Verdict |
|---|---|---|
| HIGHEST | Full text | Acceptable / Acceptable-with-fixes / Patch-immediately |
| HIGH | Full text (diff-relevant) | ... |
| MEDIUM | Sample | ... |
| LOW | Skim | (usually: Acceptable) |

## Recommendation
IMMEDIATELY / IN backlog / TRIVIAL — what when?
```

## Concrete example

**Scope snapshot**: 246 commits over 4 weeks, 287 files, +44,872 / -1,492 LoC.

**Single-subagent attempt would have failed**: 44k lines diff exceed context limit. Even if not: output would be "code looks OK, some TODOs present" — generic, no finding-value.

**Chunk split**:

| Chunk | Range | Commits | Theme | Risk |
|-------|-------|---------|-------|------|
| A | `5e5dd37..9a2cecb` | 4 | Today's dashboard bug + charts + race-fix | medium |
| B | `1b32427..5e5dd37` | 13 | Yesterday's cockpit Phase B + Phase A refactor | high (production-deployed) |
| C | `344671a..44c2e09` | 9 | Setup detector + ML / strategic | very high (live production) |
| D | `44c2e09..1b32427` | 4 | Telegram bot + dashboard SSD | high |
| E | `<base>..04fb03e` | ~216 | Tail (older work) | unknown, low (old) |

→ Chunks A-D = 30 commits = ~12% of backlog, but 100% of high-stake-recent work. Chunk E documented as a separate backlog item.

**Parallel dispatch** in a single message block:
```
<function_calls>
  <Agent description="Review Chunk A" prompt="...">...</Agent>
  <Agent description="Review Chunk B" prompt="...">...</Agent>
  <Agent description="Review Chunk C" prompt="...">...</Agent>
  <Agent description="Review Chunk D" prompt="...">...</Agent>
</function_calls>
```

Wallclock: 10-15 min for all 4. If sequential: 40-60 min for the same output quality.

**Aggregation**:
- 3 Critical (all in Chunk C — production logic)
- 11 Important across all 4 chunks
- Various Minor per chunk
- Chunk trust assessment: A=Acceptable, B-D=Acceptable-with-fixes, C additionally "patch-immediately" due to Critical

## Chunk strategies (which chunks?)

| Strategy | When |
|---|---|
| **Thematic** (Cockpit, ML, Bot) | When commits are clearly grouped by feature themes |
| **Chronological** (per week, per sprint) | When no clear themes — fallback |
| **Path-based** (per subdir or module) | For very large monorepos |
| **Critical-files-first** (`security/`, `payments/`, Auth) | For stake differentiation |

**Heuristic**: theme clusters are better than purely chronological chunks, because the reviewer subagent can then assess coherent logic (e.g. "this refactor + this test + this migration") instead of scattered commits.

## Subagent prompt template per chunk

Each subagent receives:
- **Repo path** (absolute path, because subagent has no conversation context)
- **Chunk description**: what was built (1 paragraph)
- **Plan/requirements pointer**: Daily-Note + spec files (subagent can read them)
- **SHA range**: BASE_SHA + HEAD_SHA with example `git diff` commands
- **Review checklist** from `superpowers:requesting-code-review/code-reviewer.md`:
  - Plan alignment
  - Code quality (separation-of-concerns, error-handling, type-safety, edge-cases)
  - Architecture (security, scalability, integration)
  - Testing (real-behavior vs mocks, edge-cases, integration)
  - Production-readiness (migrations, backward-compat, docs)
- **Domain-specific lenses** (e.g. "check display-name maxim", "check numeric-value verification")
- **Output format**: Strengths + Issues by Severity + Recommendations + Assessment Verdict

## Aggregation pattern

After parallel dispatch you have 4 structures. Aggregation:
1. **Critical collection list** across all chunks (sorted by risk impact)
2. **Important collection list** grouped by chunk
3. **Minor collection list** compact (1-liner per item)
4. **Trust table** per chunk with verdict
5. **Top recommendation**: which items IMMEDIATELY (Critical), which IN backlog (Important), which TRIVIAL (Minor)

## Anti-patterns

- ❌ Single subagent for 200+ commits — output is generic
- ❌ Sequential subagent dispatches (40 min instead of 10) — no wallclock savings
- ❌ Chunks with overlapping SHA ranges — same commits get double-reviewed, findings duplicated
- ❌ Ignore tail-chunk without backlog entry — falls through the cracks tomorrow
- ❌ Don't aggregate findings, show 4 separate reports — user has to synthesize themselves, loses overview
- ❌ Subagent prompts without repo path (subagent has no conversation context, doesn't know where the code is)

## Background: TDD progression (Bulletproofing-Log)

> This section is history + design-decision rationale, NOT instruction for the executing caller. Caller follows the sections above (STOP, Pattern, Fallback).

### Cycle 1 — Insight: Caller-Context-Mismatch

**RED-S1** (general-purpose subagent, repo: production app, range: 200 commits / 231 files / +33,009 LoC, skill explicitly forbidden):
- Subagent spontaneously chose **risk-based triage** (domain tiers HIGHEST/HIGH/MEDIUM/LOW)
- Result: **4 Critical / 9 Important / 6 Minor** with file:line precision
- Wallclock: 334 s | Tokens: 213k | Tool-uses: 43
- Including counter-thesis check per Critical, honest coverage-disclosure
- Note at the end: "skill exists per CLAUDE.md, but was forbidden to me" → CLAUDE.md mention is a confounder, should be temporarily masked for clean tests

**GREEN-S1** (general-purpose subagent, same scope, skill directive: "load & use"):
- Subagent loaded the skill, **but could NOT execute parallel dispatch** (subagent has no Agent tool)
- Fallback to **forced sequential chunking** (6 chunks A-F)
- Result: **1 Critical (+re-verification of today's fixes) / 7 Important / 5 Minor**
- Wallclock: 566 s (+70%) | Tokens: 134k (-37%) | Tool-uses: 54
- Meta-awareness bonus: recognized "today's commits are themselves code-review fixes, I'm reviewing re-reviews"
- **Output objectively WORSE than RED** for bug discovery (1 vs 4 Critical) despite more wallclock

**Skill design bug discovered**: caller-context-mismatch. Skill implicitly presumes the caller has Agent tool. With subagent-caller without Agent tool, chunking is pure overhead and blocks natural risk-based triage.

**Refactor applied** (R1+R2+R3):
- **R1** (caller-context guard): new STOP section at the very top, subagent check before everything else
- **R2** (Fallback mode): new section "Sequential-Triage-Mode" with risk-based-triage template for non-dispatch callers
- **R3** (description filter): description extended with "AND caller has Agent/Task-tool" + Do-NOT-load for subagent-caller (removes at the same time the description-trap of the workflow-summary)

### Cycle 2 — Mini-Verify-Fallback-PASS + S3-Pattern-Mode-Value-Prop-CONFIRMED

**Mini-Verify-RED** (general-purpose subagent, 35 commits, skill directive "load & use"):
- Subagent read STOP section FIRST, recognized missing Agent tool, jumped to fallback mode (explicitly documented in skill self-reflection)
- Risk-based triage applied, **2 Critical (real bugs) / 7 Important / 7 Minor** in 380s / 255k tokens
- Coverage disclosure as own section, counter-thesis check per Critical
- R1-guard works. R2-fallback-mode works. R3-description filters correctly.
- Subagent returned 4 constructive polish hints (incorporated: sample definition, counter-thesis depth hierarchy, tabular trust-verdict in fallback, TDD progression as Background label)

**S3-Pattern-Mode-Value-Prop-Test** (top-level caller with Agent tool, 80 commits, 5 chunks A-E dispatched in parallel):
- Wallclock: **488s parallel** vs ~1500s sequential-estimated = **3x speedup**
- Tokens: 581k total (5 chunks). Per finding: **10.4k vs 16k single-subagent = 38% efficiency win**
- Findings: **10 Critical / 20 Important / 27 Minor**
  - of which **6 truly-NEW Critical** (4 IMMEDIATE items in production app)
  - 4 Critical confirmed-already-fixed via cross-chunk triangulation (Chunk C + E confirm each other)
- Coverage depth: each chunk read touched files FULLY (Chunk A: 632 LoC v3_live_monitor.py + 456 LoC tests)
- Trust verdicts per chunk: A=Acceptable-with-fixes, B=Acceptable-with-fixes, C=Confirmed-fixed-in-follow-ups, D=Acceptable-with-C1-fix, E=**HIGH-Trust for Critical fixes**

**Test limitation documented**: S2 (Grayzone threshold loophole) + S3-Time-Pressure-Loophole-Test are not cleanly executable with the current test environment — subagents have no Agent tool (Pattern Mode not executable), top-level caller (main Claude) is biased in the test setup by skill-design knowledge. Pending for future tests in "naive" sessions without skill-design context.

**Status**: PROMOTED. Skill is auto-discoverable and productively usable.

## Cross-references

- `superpowers:requesting-code-review` — base skill for single review (chunk-dispatch is its multi-skill counterpart)
- `superpowers:dispatching-parallel-agents` — pattern base for parallel subagent dispatch
- `core-memories.md` "Code review must become standard" — meta-maxim that demands regular reviews; chunk-dispatch is the remedy when the maxim has been broken for a while
- `post-session-skill-review` — what to do after a successful chunk review (extract skill candidates from findings)

## Real-world impact

User push-back at 09:30: "complete code-review, hasn't been done for weeks."
- Scope measurement: 246 commits / 287 files / +44k LoC
- Single-subagent attempt would fail (context + generic output)
- Chunk strategy: 4 chunks (A-D) parallel, ~10 min wallclock
- Output: 4 detailed reports with 3 Critical (live production), 11 Important, various Minor
- Follow-up session: 8 of 9 follow-up tasks completed, all Critical bugs eliminated, all user-visible bugs fixed
- **Time-to-value**: without chunk strategy this would not have been doable in one session, Critical bugs would have stayed under the radar
