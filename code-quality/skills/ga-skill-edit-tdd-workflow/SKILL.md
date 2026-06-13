---
name: ga-skill-edit-tdd-workflow
description: Use when editing or expanding an already-GA-promoted skill (suffix-less name, banner says PROMOTED) to add a new capability/class/feature. Different from `skill-tdd-promotion-workflow` which covers DRAFT→GA. This skill covers GA→GA+Capability — the failure mode is silent-rename-or-expand without RED-test for the new capability (Iron-Law violation). Trigger on phrases like "extend skill with X", "add a new class to an existing skill", "extend asyncpg-skill with JSONB", "rename GA skill + extend capability", "skill rename with content expansion", "Cycle-2 capability for promoted skill". Do NOT load for new skill from scratch (`superpowers:writing-skills`), for DRAFT→GA promotion (`skill-tdd-promotion-workflow`), for minor edit without new capability (just edit), or when the target skill doesn't exist.
---

# ga-skill-edit-tdd-workflow (DRAFT — TDD-Promotion-Pending)

> ⚠️ **DRAFT**: pattern derived from a work session where an existing GA skill was extended with new classes and renamed. Iron-law violation (silent rename without RED test for new capability) was caught by Pre-Step-0 check. Pattern was ad-hoc but repeatable.

## Lifecycle position

```
[Idea] → CREATE (writing-skills) → -DRAFT
  ↓
PROMOTE (skill-tdd-promotion-workflow) → GA-Skill
  ↓
EDIT (THIS skill) → GA-Skill with extended capability
```

`skill-tdd-promotion-workflow` is NOT for GA edits — it explicitly says "Do NOT load for editing GA-skills".  
`superpowers:writing-skills` (CREATE) is not for capability expansion on existing GA — otherwise existing content gets fragmented.

This skill is the missing lifecycle stage.

## Pre-Step-0: Target verification (MANDATORY)

### Check A — Skill is actually GA?

```bash
head -3 ~/.claude/skills/<SKILL-NAME>/SKILL.md | grep -E "name:.*-DRAFT|name:.*-STUB"
```

If MATCH → skill is still DRAFT → **wrong skill used** → STOP, `skill-tdd-promotion-workflow` first.

### Check B — PROMOTED banner present?

```bash
grep -E "PROMOTED|✅" ~/.claude/skills/<SKILL-NAME>/SKILL.md | head -3
```

If NO MATCH → skill was never explicitly promoted (no TDD progression documented) → STOP, first writing-skills + skill-tdd-promotion-workflow.

### Check C — New capability is orthogonal to existing?

Question: does the extension add a NEW bug-class / pattern-variant / use-case-branch (yes → EDIT workflow legitimate) OR is it just polish on existing content (no → simple edit, no TDD needed)?

| Extension | Workflow |
|---|---|
| New class / bug pattern (e.g. JSONB alongside Decimal) | EDIT workflow (this skill) |
| Edge-case doc for existing class | Simple edit (no TDD) |
| Extended trigger phrases without content change | Simple edit |
| Major rename (semantic shift) | EDIT workflow + possibly old-skill redirect |

## Pattern (8 Steps)

Per GA skill expansion (after Pre-Step-0 pass):

1. **Read original skill completely** — understand what's already validated, what the class/section structure is
2. **Lay out new extended skill as `-DRAFT`** under a new name (if rename) or under `<original-name>-DRAFT` (if in-place expansion staged) — original stays untouched while TDD runs
3. **Take over existing content unchanged** + **append NEW sections for new capability** — no re-validation of existing content needed (was already GA)
4. **Design RED + GREEN scenario** for the NEW capability — bait that leads to natural error in the new class (NOT re-test the old class — it's validated)
5. **Parallel subagent dispatch** (Agent tool, `general-purpose`) — identical prompt-stem, only variable = skill access. Use the `-DRAFT` file for GREEN Read-tool path
6. **Analysis + polish**: does GREEN comply for new capability? Self-reflection findings if applicable incorporated inline (iron-law-compliant: only if ≤5min polish, otherwise Cycle-2 backlog)
7. **Strip DRAFT marker** (name: + description: STUB prefix) + **PROMOTED banner Cycle-2 update** (date + verdict for NEW capability) + **TDD progression section extension** with Cycle-N entry
8. **Directory rename + old-skill removal** (if rename) — skills directory is not git-versioned, so no commit step

## Concrete dispatch example (Step 5)

This is what RED+GREEN dispatch-pair looks like for GA edit (shortened):

```python
# RED: without skill, NEW capability scenario
Agent(
    subagent_type="general-purpose",
    description="RED-X <skill-shortname> <new-capability>",
    prompt="""
You are RED baseline (without skill).

**CONSTRAINT**: do NOT load any skill named `<old-name>` OR `<new-name>`.

**Scenario**: <concrete mini-problem that triggers ONLY the new capability, not the old>
<built-in anti-pattern bait that naturally arises without skill>

⚠️ NO-FILE-WRITE: markdown code-blocks only, no files.

Output: code + reasoning + self-reflection with uncertainties.
"""
)

# GREEN: with extended -DRAFT
Agent(
    subagent_type="general-purpose",
    description="GREEN-X <skill-shortname> <new-capability>",
    prompt="""
You are GREEN subagent.

**SKILL DIRECTIVE**: Read via Read-tool: `/Users/<user>/.claude/skills/<NEW-NAME>-DRAFT/SKILL.md`.
Follow its instructions for the scenario.

**Scenario**: <IDENTICAL to RED>

⚠️ NO-FILE-WRITE: markdown code-blocks only.

Skill self-reflection section with: first section read / implemented / wrong-recommendation-avoided / caller-context check / helpful+missing.
"""
)
```

## Pre-validated-content skip

Iron-law allows skipping re-validation **only** for unchanged content:

- ✅ existing Class-A section unchanged → no Re-RED-Test for Class A
- ✅ Cycle-1 TDD-progression entry remains → gets supplemented by Cycle-2, not replaced
- ❌ Class-A section restructured/reformulated → Re-RED-Test for Class A needed
- ❌ Default values changed in existing section → Re-RED-Test for all affected classes

Rule of thumb: if you edit an existing section (not just append), it becomes the "new capability" → Re-TDD.

## Rename strategies

If EDIT of capability expansion also involves rename (e.g. `asyncpg-decimal-test-shape` → `asyncpg-live-vs-mock-shape`):

### Option A — Hard rename + delete-old

- New skill under new name
- Old skill directory completely removed
- **Advantage**: clean, no duplicate auto-discovery
- **Disadvantage**: trigger phrases from old description must be covered in new description (otherwise discovery gap)

### Option B — Old skill with redirect

- Old skill directory stays
- Content: single section "⚠️ This skill has been superseded by `<new-name>`. See there."
- Description stays with old triggers, supplemented with "use new-name instead"
- **Advantage**: backward-compatible for trigger-phrase discovery
- **Disadvantage**: 2 skills load on trigger match

**Default**: Option A (hard rename). Trigger phrases consolidated into new description.

## Polish-vs-Promote decision (analogous to skill-tdd-promotion-workflow)

| Item type | Action |
|---|---|
| Sub-skill essential for new capability (e.g. unclear trigger) | now build in before PROMOTE |
| Edge-case doc for new capability (≤5min) | build in now |
| Pattern extension ("would still be useful") | Cycle-N backlog |
| Refactor on existing content (≥5min, orthogonal to capability) | separate session |

## Anti-Patterns

| Anti-Pattern | Correct |
|---|---|
| Silent rename + expand without RED test for new capability | Iron-law violation; RED test is mandatory for every new class |
| Re-RED-Test for existing validated content | Iron-law obligation is failing-test-first; unchanged content doesn't need that |
| Skip Pre-Step-0 because "I know it's GA" | 1-second check, wrong assumption costs 30min re-work |
| Forget to remove old skill directory on hard rename | Auto-discovery finds both → user confusion |
| PROMOTED banner not Cycle-2-updated | Later reviewers think skill is GA-since-Cycle-1, but see new classes without TDD backing |
| NEW capability without TDD-progression Cycle-N entry | Cycle tracking is prerequisite for future Cycle-3+ edits |
| User directive "expand X" interpreted as CREATE workflow | If X is already GA skill, it's EDIT, not CREATE |

## Cross-references

- `superpowers:writing-skills` — CREATE stage (before PROMOTE)
- `skill-tdd-promotion-workflow` — PROMOTE stage (DRAFT → GA)
- `superpowers:dispatching-parallel-agents` — mechanic for Step 5
- `superpowers:test-driven-development` — Iron-law basis
- `subagent-self-reflection-prompt-pattern` — polish-item source

## TDD task for future promotion

Before GA promotion of this skill itself:
1. RED+GREEN pressure-test with scenario: "User says 'extend asyncpg-decimal-test-shape with JSONB'"
2. RED without skill: would likely load `superpowers:writing-skills` or silently rename
3. GREEN with THIS skill: loads Pre-Step-0 check A/B/C, identifies EDIT mode, dispatches RED+GREEN for JSONB capability, renames with Option A
4. Expectation: GREEN structurally cleaner, more explicit in workflow pick

## Background: TDD progression (Bulletproofing-Log)

### Cycle 1 — DRAFT phase

Skeleton from a work session. Real TDD pressure-test pending. Pattern applied ad-hoc:
- Original `asyncpg-decimal-test-shape` (GA) read
- Extension laid out as `asyncpg-live-vs-mock-shape-DRAFT` with 5 classes (A-E)
- RED+GREEN for Class B (JSONB) — PASS
- Inline polish for symptom clarity (5 access-pattern mapping)
- Hard rename Option A: directory `asyncpg-decimal-test-shape` removed, `-DRAFT` → final name
- PROMOTED banner Cycle-2 update with date

Result: skill with 5 bug classes instead of 1, Cycle-1 Decimal validation retained + Cycle-2 JSONB validation added. Clean lifecycle progression.
