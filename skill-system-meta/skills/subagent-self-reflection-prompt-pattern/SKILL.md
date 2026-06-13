---
name: subagent-self-reflection-prompt-pattern
description: Use when dispatching a subagent to test a skill, evaluate a tool, or perform any non-trivial task where YOU (the caller) want meta-feedback about the experience — what worked, what was unclear, what was missing. Include a mandatory "## Skill-Self-Reflection" section in the prompt asking 3-4 introspective questions. Without this, you only get task output, not improvement signal. Trigger on phrases like "dispatch subagent for skill test", "skill TDD pressure-test", "evaluate this tool via subagent", "subagent meta-feedback", "how do I use subagents for skill improvement". Do NOT load for production-task dispatch (only output matters, not reflection), for performance-critical dispatches (reflection adds tokens), or when the caller already has a strong skill-content hypothesis to test against (then use direct A/B comparison instead).
---

# Subagent Self-Reflection Prompt Pattern

> ✅ **PROMOTED**: TDD pressure-test passed. RED subagent wrote a standard task prompt WITH the trap but WITHOUT the self-reflection section (exactly the natural anti-pattern). GREEN subagent used the GREEN-variant template from the skill, built 5 structured questions at the end (not at the start!), adapted F3 to a single-pattern skill characteristic. Cycle-2 backlog: "how much of the test goal to reveal in the prompt" heuristic table, question-adaptation hint for multi-mode skills.

## Core Pattern

When you dispatch a subagent to **test a skill** or **evaluate a tool**, append a `## Skill-Self-Reflection` section to the prompt with 3-4 introspective questions.

**Without this section**: You only get task output. You don't know WHY the subagent proceeded that way, whether the skill helped, or what was unclear.

**With this section**: The subagent reflects on the tool/skill use itself. Output becomes an **improvement-signal source** for future skill edits.

## Standard template

```markdown
**Additional requirement**: At the end, section `## Skill-Self-Reflection`:
1. Which section of the skill did you read first? (shows skill-structure efficiency)
2. Which instructions did you follow? Which did you modify/ignore and why?
3. What was helpful / unclear / missing?
4. [Optional] Did the skill prevent you from making a "natural wrong recommendation"? Which one?
```

## Variant for GREEN subagent in TDD promotion cycle

```markdown
**SKILL DIRECTIVE**: You have access to the skill `<name>`. **Load it FIRST** via the Skill tool and follow its instructions.

**Additional requirement**: At the end, section `## Skill-Self-Reflection`:
1. Which section of the skill did you read first?
2. Did you have access to the tools the skill assumes? (Caller-Context check)
3. Which mode did you choose (main-pattern / fallback)? Reasoning.
4. Which instructions from the chosen mode did you apply point by point?
5. Are there unclear passages / missing instructions in the skill? Which?
```

## Variant for RED subagent (without skill)

```markdown
**CONSTRAINT**: You may NOT load a skill named `<name>` — it does not exist in your environment yet.

**Important for your reporting**: Be honest about what you did and didn't do. If you proceeded heuristically, say so. If you were unsure about a decision, say so.
```

(RED needs NO self-reflection section — the honesty directive suffices. Self-reflection would be redundant because RED has not loaded a skill.)

## Why does this work?

Subagents (Claude subagent, general-purpose) are **capable of self-reflection** — when asked explicitly. Without an explicit prompt they default to delivering only task output, not meta-feedback.

The 3-4 questions are not arbitrary:
1. **"Which section did you read first?"** → shows whether the skill structure is efficient (decisive info at the top?)
2. **"Which instructions modified/ignored?"** → shows skill realism (instructions that were not executable)
3. **"Helpful / unclear / missing?"** → directly delivers 3 improvement lists
4. **"Which natural wrong recommendation did it prevent?"** (optional) → shows the anti-pattern value of the skill

## When to apply

| Trigger | Apply? |
|---|---|
| Dispatch subagent for skill TDD test (RED+GREEN) | ✅ yes — GREEN path |
| Dispatch subagent for tool evaluation ("use MCP-X and tell me how it was") | ✅ yes |
| Dispatch subagent for skill promotion workflow (see skill-tdd-promotion-workflow) | ✅ yes — Cycle-2 backlog source |
| Dispatch subagent for production task (code fix, code review, feature) | ❌ no — output matters, not reflection |
| Dispatch subagent for time-critical dispatch | ⚠️ skip — self-reflection adds ~10-30% token cost |
| Test already-known skill weaknesses (targeted A/B) | ⚠️ partially — direct specific question is better than general reflection |

## Real output examples (cleanup day)

### Output example 1: htmx skill GREEN test

Subagent self-reflection delivered:
> **Which anti-pattern did the skill prevent?**
> The default reflex `hx-trigger="load, every 60s"` directly on the `<section>` with `hx-swap="outerHTML"`. That is exactly the natural pattern...

→ **Direct confirmation that the skill fulfils its purpose**. Without this question I would have seen only the code output, not the causal confirmation that the skill prevented the anti-pattern.

### Output example 2: launchagent skill GREEN test

> **Which "natural wrong recommendation" did it prevent?**
> At least three: 1. Set FDA for `/usr/bin/python3` (SIP stub), 2. Grant FDA to the plist or launchd (per-executable), 3. `/opt/homebrew/bin/python3` in the File Picker (symlink)...

→ Delivered an **explicit list of 3 anti-patterns** that I would never have documented so explicitly alone. These 3 are now hard-coded in the skill as a diagnostic table.

### Output example 3: asyncpg skill GREEN test

> **What was helpful / unclear / missing?**
> *Unclear:* The table doesn't explicitly state what happens with an empty aggregate result. I had to derive from PG semantics: `COUNT` always delivers `Decimal(0)`, `SUM`/`AVG` deliver `None`.

→ Cycle-2 backlog item identified directly: "Add empty-set-behavior column to the lookup table." Alone I would never have noticed the gap.

## Anti-patterns

| Anti-pattern | What to do instead |
|---|---|
| Dispatch subagent without self-reflection for skill test → only output without meta-feedback | Self-reflection section is mandatory for skill-test dispatches |
| Self-reflection questions too vague ("what do you think?") | Concrete 3-4 structured questions — template above |
| Forcing self-reflection on every subagent dispatch (also production) | Only for evaluation/test, not for pure execution |
| Ignoring subagent self-reflection ("interesting but not actionable") | Transfer polish-backlog items directly into the skill's TDD log |
| Self-reflection section at the start of the prompt instead of the end | The end ensures the subagent does the task first, then reflects |

## TDD task for next skill-building session

1. **RED**: Dispatch subagent for skill test WITHOUT self-reflection section. Observe: does it deliver polish items proactively? Probably no (only task output).
2. **GREEN**: With skill: caller gets an explicit self-reflection template suggestion, builds it in. Subagent then delivers 3-5 structured polish items.
3. **REFACTOR**: Loophole "but for LARGE subagent tasks self-reflection is 30% token overhead" → skill must explicitly state when to skip (production tasks).
4. **Trigger phrases**: "subagent for skill test", "TDD pressure-test", "evaluate this skill via subagent" → does the skill auto-trigger?

## Cross-references

- `skill-tdd-promotion-workflow` — main consumer of this pattern (Cycle-2 backlog source)
- `superpowers:writing-skills` — superordinate framework (this skill tightens the GREEN phase)
- `superpowers:dispatching-parallel-agents` — pattern for multiple parallel self-reflection subagents

## Real-world impact (cleanup day)

5 skill promotions × 1 GREEN subagent each = 5 self-reflection outputs.

Delivered: **13 Cycle-2 backlog items** (see TDD log sections per skill). Of which implemented:
- 4 immediately as polish commits (I1-I4 in the app)
- 2 as M items (M2 cleanup, M4 doc drift)
- 7 documented as Cycle-2 backlog in the skill files

Without the self-reflection pattern: I would have promoted the skills, NOT noticed that the lookup table in asyncpg skill misses empty-set behavior, would have released the cross-repo skill without an API-versioning hint, etc. The pattern visibly raised the **maturity level of the 5 skills** — from "compiles" to "documented + hardened".

## Background: TDD Log (Bulletproofing Log)

### Cycle 1 — PASS

- **RED subagent** (without skill, subagent-prompt-writing task for htmx-skill test): Wrote a standard task prompt with embedded trap (anti-pattern server response) + skill directive. Delivery format with reasoning + loop-free confirmation. **No self-reflection section**. Self-assessment at the end: "Self-reflection might have been relevant" — recognized the gap retrospectively but did not build it in.
- **GREEN subagent** (with skill, same prompt): Used explicitly the GREEN-variant template (lines 30-39 of the skill). 5 self-reflection questions built in at the end, adapted to single-pattern skill characteristic (F3 reshaped to "fix-pattern applied point by point"). Anti-pattern "self-reflection section at the start instead of the end" explicitly avoided. Bait subtlety discussed forward-looking.
- **Verdict**: GREEN reproduced the pattern exactly + added intelligent adaptations per skill type. PROMOTE.

### Cycle-2 Backlog (Polish, non-blocking)

1. **"How much of the test goal to reveal in the prompt?" heuristic table** — spectrum "blind test" (no hint) to "fully brief" (name all anti-patterns). Strong-natural anti-pattern → blind. Subtle anti-pattern → light hint.
2. **Question-adaptation hint for multi-mode skills**: F3 must be reshaped depending on skill characteristic (single-pattern vs. main/fallback split)
3. **Anti-leak protection pattern**: how subtle should the bait in the prompt be? Realism-vs-subtlety trade-off explicit.
