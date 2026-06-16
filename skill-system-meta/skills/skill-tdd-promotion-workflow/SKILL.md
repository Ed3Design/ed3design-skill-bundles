---
name: skill-tdd-promotion-workflow
description: Use when promoting an existing DRAFT/STUB skill (suffix `-DRAFT` or `-STUB` in `name:` field, OR description starts with "STUB —") to GA (auto-discoverable). Different from `superpowers:writing-skills` which covers CREATE-from-scratch — this skill covers the LIFECYCLE-STAGE from "skeleton-exists" to "production-ready". Requires Agent/Task-tool for parallel RED+GREEN subagent-Dispatch (Step 3) — if the caller does NOT have Agent-tool (e.g. running as a general-purpose-subagent themselves), STOP and report-up; do NOT silently fall back to name-rename-only. Trigger on phrases like "promote this DRAFT skill", "TDD for the remaining STUBs", "make it auto-discoverable", "skill promotion cycle", "release skill from -DRAFT", "TDD promotion cycle for N skills". Do NOT load for creating a new skill from scratch (use `superpowers:writing-skills`), for editing GA-skills (just edit), when no DRAFT/STUB-suffix exists (skill is already GA), or when target skill file does not exist (no work to do).
---

# Skill TDD Promotion Workflow

> ✅ **PROMOTED**: Pattern from a cleanup-day session (applied 5× successfully), TDD pressure-test passed in a subsequent promotion session. R1-R3 refactor applied (Pre-Step 0, caller-context STOP mode, concrete dispatch example).

## Lifecycle position

`superpowers:writing-skills` covers **CREATE** (RED-GREEN-REFACTOR cycle for new skills). This skill covers **PROMOTE** — the other lifecycle stage:

```
[Idea] → CREATE (writing-skills) → -DRAFT suffix → [Skeleton with TDD task] → PROMOTE (this skill) → GA (auto-discoverable)
```

**PROMOTE is not automatic**: not every DRAFT becomes GA. Some remain deferred (pattern preserved, trigger not yet active) until enough re-use evidence exists.

## Pre-Step 0: caller-context + target-existence check (MANDATORY)

**STOP gate before everything else.** Both checks fail silently and lead to invalid promotions if skipped.

### Check A — Does the caller have the Agent/Task tool?

```
Does the current caller (= you, loading this skill) have Agent-tool in the tool inventory?
- TOP-LEVEL Claude Code session  →  yes  →  continue
- general-purpose subagent       →  no  →  STOP, see "Fallback: No-Agent-Tool-Caller"
- gsd-* spawned agent            →  usually no →  STOP
```

**If no → STOP**: You cannot execute Step 3 (parallel RED+GREEN dispatch). Single-caller simulation is NOT a substitute (you already know what the skill claims, which destroys RED validity). Report-up to the dispatching caller with:

> "Cannot execute skill-tdd-promotion-workflow without Agent/Task-tool. Step 3 (parallel RED+GREEN subagent-Dispatch) is the validity-load-bearing step and cannot be substituted by single-caller simulation. Promotion-Cycle must be invoked from a top-level Claude Code session that has Agent-tool access."

See "Fallback: No-Agent-Tool-Caller" below for the only legitimate single-caller action (Prep-Only mode).

### Check B — Does the target skill file exist?

```bash
test -f ~/.claude/skills/<SKILL-NAME>/SKILL.md && echo "exists" || echo "MISSING"
```

If `MISSING` → STOP and report back to the caller. Do not invent a new one synthetically (that would be the CREATE workflow, the wrong skill).

### Check C — Is the skill actually DRAFT/STUB?

```bash
head -3 ~/.claude/skills/<SKILL-NAME>/SKILL.md | grep -E "name:.*-DRAFT|name:.*-STUB|description:.*STUB —"
```

If no match → skill is already GA, no PROMOTE work needed. STOP, use an edit-mode skill if appropriate.

## Pattern (10 Steps)

Per DRAFT/STUB skill (after passing Pre-Step 0):

1. **Read the skill** (Read tool, full file) — understand what it claims, which trigger phrases, which anti-patterns
2. **Design RED + GREEN scenario** — identical prompt stem, only variable = skill-access directive. Scenario must be concrete enough that the anti-pattern arises "naturally" (build in bait if needed)
3. **Dispatch both subagents in ONE message block in parallel** — Agent tool, `general-purpose` subagents (see concrete example below)
4. **Analyze**: does RED reproduce the natural anti-pattern (failure mode)? Does GREEN behave compliantly? Compare via the self-reflection answers
5. **Refactor if needed** — caller-context bias check is a critical loophole: subagents may have less tool inventory than the caller, the skill must anticipate that
6. **Polish items from subagent self-reflection** — either incorporate or document as Cycle 2 backlog (see Polish-vs-Promote decision)
7. **Marker strip**: rename `name:` from `*-DRAFT` / `*-STUB` to clean AND clean `description:` of STUB prefix (BOTH fields — Auto-Discovery reads both)
8. **Header banner**: replace ⚠️ DRAFT-STATUS block with a ✅ PROMOTED banner including test date + verdict
9. **TDD log section** appended as background (Cycle 1 findings + Cycle 2 backlog)
10. **Commit** as atomic `feat: promote <skill-name> ...` with test verdict

## Concrete Dispatch Example (Step 3)

This is what a RED+GREEN dispatch pair looks like in a single message block (abridged):

```python
# RED subagent (without skill)
Agent(
    subagent_type="general-purpose",
    description="RED-X <skill-shortname>",
    prompt="""
You are part of a TDD pressure test. You are the RED baseline (without skill).

**CONSTRAINT**: You may NOT load a skill named `<skill-name>`.

**Scenario**: <concrete task with embedded natural anti-pattern bait>

**Honesty directive**: Be honest about how you proceed. If you answer heuristically, say so.

**⚠️ NO-FILE-WRITE**: Do NOT write any files to disk. All code examples go as Markdown code blocks in your reply — NOT as files in the working directory. The CWD may be an Obsidian vault or a production repo — creating files there produces ghost nodes or data garbage.

Report format: <task-specific>
"""
)

# GREEN subagent (with skill) — dispatched in parallel in the SAME message block
Agent(
    subagent_type="general-purpose",
    description="GREEN-X <skill-shortname>",
    prompt="""
You are the GREEN subagent (with skill).

**SKILL DIRECTIVE**: First read via Read-Tool the file `/Users/<user>/.claude/skills/<skill-name>/SKILL.md` (NOT via Skill-Tool, since DRAFT status blocks auto-discovery). Then follow its instructions.

**Scenario**: <identical to RED>

**⚠️ NO-FILE-WRITE**: Do NOT write any files to disk. All code examples go as Markdown code blocks in your reply — NOT as files in the working directory. The CWD may be an Obsidian vault or a production repo — creating files there produces ghost nodes or data garbage.

At the end, section `## Skill-Self-Reflection`:
1. Which section of the skill did you read first?
2. Did you have access to the tools the skill assumes? (Caller-Context check)
3. Which pattern steps did you execute? Which did you skip + why?
4. Which "natural wrong recommendation" did the skill prevent you from making?
5. What was helpful / unclear / missing?
"""
)
```

**Important for Step 3**:
- Both calls in ONE message block (parallel dispatch, not sequential)
- Keep `description` short, prefix with `RED-` / `GREEN-`
- Always specify skill path via Read-Tool (DRAFT status blocks Skill-Tool auto-discovery)
- For N skills: 2N Agent calls in one block (e.g. 8 skills = 16 calls)

## Caller-context bias check (CRITICAL loophole)

Subagents (general-purpose) have **no Agent/Task tool**. If the skill being promoted requires `superpowers:dispatching-parallel-agents` or similar as its core mechanic, the GREEN subagent cannot execute the pattern → GREEN test fails silently OR produces a sequential fallback worse than baseline.

**Mandatory check before RED+GREEN dispatch of the skill under test**:
- Which tools does the test skill assume? (Bash? SSH? Agent? MCP?)
- Does a general-purpose subagent have these tools?
- If no: the test skill must have a STOP section + fallback mode (see `code-review-chunk-dispatch` as a model; see THIS skill for self-reference)

**Example** (chunk-dispatch): GREEN subagent achieved sequentially-forced chunking instead of parallel dispatch → worse than RED baseline (1 Critical vs 4). R1+R2+R3 refactor with caller-context guard + fallback mode + description filter needed before promotion.

**Example** (skill-tdd-promotion-workflow itself): GREEN subagent recognized "no Agent tool, STOP" — but the skill itself had no STOP mode documented. Ironic recursion found, refactor (this block + Pre-Step 0) applied.

## Fallback: No-Agent-Tool-Caller (Prep-Only Mode)

If Pre-Step 0 Check A fails (subagent caller without Agent tool), there is exactly ONE legitimate action:

### Prep-Only Mode

1. **Read the target skill** (Read tool)
2. **Write a PROMOTION-PLAN.md** next to the target skill with:
   - RED subagent prompt suggestion (complete, copy-paste-ready)
   - GREEN subagent prompt suggestion (complete, copy-paste-ready)
   - Expected RED anti-pattern (hypothesis)
   - Expected GREEN compliance check
   - Caller-context-bias risk for the target skill
3. **Report-up**: "Prep done, file: PROMOTION-PLAN.md. Top-level caller with Agent tool must execute dispatch."

### What Prep-Only Mode does NOT do

❌ Single-caller RED+GREEN simulation (validity lost — you already know what the skill claims)
❌ Just name-rename (Iron-Law anti-pattern: PROMOTE without RED test)
❌ Heuristic "looks good, I'll promote"
❌ Header banner / description strip before TDD has succeeded

## Polish-vs-Promote Decision

Subagent self-reflection (see `subagent-self-reflection-prompt-pattern` skill) often delivers 3-5 polish items per skill. Decision per item:

| Item type | Action |
|---|---|
| Sub-skill-essential (e.g. unclear trigger, missing STOP mode) | build in now before PROMOTE |
| Edge-case doc (e.g. "what if X is NULL") | build in now if ≤5min |
| Pattern extension ("would also be useful for Y") | Cycle 2 backlog in TDD log, non-blocking |
| Tool-wrapper refactor (large) | separate session |

Iron Law: every polish edit AFTER PROMOTE needs its own failing-test-first. BEFORE PROMOTE, polish items can be incorporated as part of the promotion refactor.

## TDD log section convention

Every promoted skill gets at the end a `## Background: TDD Log (Bulletproofing Log)` section with:

```markdown
### Cycle 1 — YYYY-MM-DD (PASS/FAIL)

- **RED subagent** (without skill, prompt: ...): behavior described verbatim
- **GREEN subagent** (with skill, same prompt): behavior described verbatim
- **Refactor applied**: R1/R2/... what changed + why

### Cycle 2 backlog (Polish, non-blocking)

1. [Polish item 1]
2. [Polish item 2]
...
```

This section is background for executing callers, not instruction. But it makes skill maturity visible for future reviewers.

## Anti-Patterns

| Anti-Pattern | What to do instead |
|---|---|
| Promote skill without RED test because "looks intuitive enough" | RED test is mandatory — shows natural anti-pattern, validates skill value |
| Skip Pre-Step 0 because "the skill surely exists" | Existence check is 1s, wrong assumption costs 30min |
| Dispatch RED and GREEN sequentially instead of parallel | Parallel in the same message block, only variable = skill access |
| Skip caller-context-bias check because "the subagent will figure it out" | Subagents often have different tool inventories — skill must have a fallback mode |
| Single-caller simulation as substitute for RED+GREEN subagent dispatch | Validity lost (caller already knows skill claim) — use Prep-Only Mode instead |
| Strip only `name` field, forget `description` STUB prefix | Auto-Discovery reads BOTH fields |
| Try to incorporate all polish items before PROMOTE | Iron Law: every polish after PROMOTE needs a failing test. Cycle 2 backlog for non-blocking is legitimate. |
| PROMOTE without TDD-log section | Later reviewers don't know whether the skill is bulletproof or still DRAFT-quality |
| **Forget NO-FILE-WRITE constraint in subagent prompts** | Subagents inherit the session CWD (e.g. Obsidian vault or production repo). Without explicit prohibition they write RED/GREEN simulation outputs as files there → ghost nodes in the graph / data garbage. Correct: `⚠️ NO-FILE-WRITE` in EVERY subagent prompt. |

## Cross-references

- `superpowers:writing-skills` — CREATE stage (before this skill)
- `subagent-self-reflection-prompt-pattern` — polish-item source per subagent dispatch
- `superpowers:dispatching-parallel-agents` — mechanic for Step 3
- `superpowers:test-driven-development` — Iron-Law basis
- `code-review-chunk-dispatch` — best example for caller-context-bias refactor (model)

## Real-World Impact

**Cleanup day**: 5 skills promoted in one session via this workflow:
- chunk-dispatch (Cycle-1 refactor + Cycle-2 value-prop)
- asyncpg-decimal-test-shape (trivial PASS)
- cross-repo-stack-cockpit-pattern (moderate value-add, baseline good)
- htmx-outerhtml-load-loop (RED reproduced exact anti-pattern)
- macos-launchagent-fda-pattern (RED fell into Lesson-1 trap)

**Promotion day**: 8 skills promoted via this workflow (including this self-application):
- external-advisor-output-plausibility-audit
- legal-paragraph-recommendation-checklist
- pre-migration-data-verification
- pytest-venv-first-triage
- roadmap-phase-execution-verify-first
- skill-tdd-promotion-workflow (THIS — ironic-recursion: self-applied)
- subagent-self-reflection-prompt-pattern
- a cross-file decision-sync discipline (keeping a decision consistent across multiple files)

Token cost: ~0.5M per 5 skills (8-16 parallel subagents = 1 large dispatch). Without the workflow: re-discovery of every promotion cycle, caller-context-bias bug would not have been caught on the first skill → the rest would have been botched into promotion.

## Background: TDD Log (Bulletproofing Log)

### Cycle 1 — PASS via Self-Application

- **RED subagent**: Mechanical rename-only approach (1. read skill, 2. strip DRAFT suffix from name field, 3. remove STUB prefix from description, 4. delete header banner, 5. delete TDD-task section, 6. commit). Self-critique at the end listed 7 gaps (no TDD verification, no cross-skill consistency check, no TDD-task-completion check, no rollback path, no user query, no path-schema check) — RED recognized the gaps but would not have applied them without the skill.

- **GREEN subagent**: Recognized at the Pre-Step the Caller-Context-Bias EXPLICITLY — "As a general-purpose subagent I have NO Agent/Task tool, Step 3 (parallel subagent dispatch) is physically not executable." Stopped correctly instead of faking it. Additionally identified: (a) Pre-Step-0 (existence check) missing from the skill, (b) single-caller fallback mode preached by the skill for others but not lived itself (preaches it in the Caller-Context-Bias-Check block but has no block for itself), (c) Step-3 dispatch mechanic lacks a concrete example.

- **Refactor applied (R1+R2+R3)**:
  - **R1** (Pre-Step 0): Caller-context check + target-existence check + DRAFT-status check added as STOP gate before the pattern
  - **R2** (Fallback mode): "No-Agent-Tool-Caller → Prep-Only Mode" section with clear anti-list (what Prep-Only does NOT do)
  - **R3** (Concrete dispatch example): Python pseudocode block with RED+GREEN agent-call pair as Step-3 concretization
  - Bonus: Anti-Patterns table extended with Pre-Step 0 skip + single-caller-sim

### Cycle 2 backlog (Polish, non-blocking)

1. **Example output gallery**: concrete RED+GREEN output excerpts per skill type (trivial-PASS / moderate / refactor-needed) for calibration of what counts as "strong RED anti-pattern"
2. **Token-cost heuristic**: at N skills, estimated 2N×~50k = N×100k tokens; for N>8 consider wave-A/B split
3. **Test-skill tool-inventory table**: common tool sets (general-purpose / gsd-* / specialist) with "can skill X be tested yes/no" hint
4. **`/gsd-promote-skill <name>` orchestrator command**: if this workflow runs >10× per quarter, a dedicated slash command is worthwhile
5. **Cross-skill consistency check** (from RED self-critique): before PROMOTE, check whether trigger phrases collide with other GA skills — `grep -l "<trigger-phrase>" ~/.claude/skills/*/SKILL.md`
6. **Step 7b — remove Promotion-Checklist section**: many DRAFT skills have a "## Promotion-Checklist (TDD later)" section. On promote, as Step 7b after name strip, remove it, otherwise it's a dangling section in the promoted file. Pattern: `grep -A 10 "## Promotion-Checklist"` + Edit to delete.
7. **Empirical update** (8 skills in one 16-agent block): ~430k tokens total for an 8-skill promotion cycle. Confirms the N×100k heuristic (item 2). Skill-catalog growth: +8 GA skills in one session without Cycle 2 refactor need — highest throughput so far. Cycle 2 polish items per skill averaged 3-5, all from GREEN subagent self-reflection directly actionable. 16-agent-block ROI ~50% saving vs sequential.
