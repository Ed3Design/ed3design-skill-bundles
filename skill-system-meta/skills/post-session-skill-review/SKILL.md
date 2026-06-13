---
name: post-session-skill-review
description: Use at the end of any productive session, when writing a Daily Note, when the user says "wrap up" / "remember" / "session done", or proactively after observing repeated workflow patterns within a session. Trigger on phrases like "end of session", "let's wrap up", "end of day", "session wrap-up", "end of day review", "what did we learn today", "is there a skill in here?", "post-session review", "skill candidate review". Do NOT load mid-session for active task work, for single-task sessions with nothing repeatable, or when the user is in mid-debug (they need closure, not meta-reflection). This skill encodes the maxim: "Checking at the end of every successful session whether developing a skill is worthwhile is one of the greatest strengths of the system." Skills compound; finding them at end-of-session is the highest-leverage moment.
---

# Post-Session Skill Review

At session-end, take 5 minutes to ask: **did any pattern repeat today that future-me would want as a Skill?** Most sessions: no. Some sessions: yes, and missing it means re-discovering the pattern next time, often worse.

This skill is the systematic version of "What did we learn?" — applied with three filters that distinguish genuine skill candidates from one-off solutions.

## When to use

- End of a productive session — especially when a Daily Note is being written
- User explicitly asks "remember", "session wrap-up", "end of day"
- Mid-session, when the same workflow pattern has appeared a 3rd time and you start to suspect "we should formalize this"
- After a hard-won debugging session that took unreasonably long — there's likely a skill in the "what we wish we'd known first"

## When NOT to use

- Single-task session where nothing repeated and there's no general lesson
- Mid-debug / mid-implementation — the user needs to finish first, reflect after
- Conversational chats with no productive output
- When the user is exhausted and just wants to close out — offer to do it next session

## The three-filter test

Every candidate pattern passes ALL three filters or it's not a skill. Some are better captured as:
- **Memory entry** in `.remember/core-memories.md` (user-specific maxims, lessons)
- **CLAUDE.md update** (project-specific structure, conventions)
- **Hook in settings.json** (mechanical/automatic enforcement — use `update-config` skill)

### Filter A — Is it a repeatable pattern with clear steps?
- ✅ Has 3+ discrete steps that always run in the same order
- ✅ Could be turned into a numbered procedure
- ❌ Vague principle without concrete actions → memory entry, not skill
- ❌ One-off solution to a unique problem → just log the solution in Daily Note

### Filter B — Without the skill, would Claude get it wrong again?
- ✅ Today's session showed Claude going down a wrong path before correcting (look for "v1-v4 iterations", "4 wasted days", "I initially tried X but that was wrong")
- ✅ A 5-minute write-up saves a future 2-hour re-discovery
- ❌ Claude got it right first try, no detour → no failure to prevent
- ❌ The "wrong path" was actually user-context-specific, not generalizable

### Filter C — Is it transferable beyond a single project?
- ✅ Pattern applies to >1 project or >1 domain
- ✅ Technology-specific but the tech is used across multiple projects (Tailscale, Obsidian, ESP32 ecosystems)
- ❌ Project-specific naming, file-paths, business-logic → CLAUDE.md update
- ❌ One-time refactor specific to one codebase → commit message + Daily Note

A candidate that fails Filter A → Daily Note. Fails B → memory entry. Fails C → CLAUDE.md or project-doc.

Only ABC-pass candidates become skills.

## The five-minute workflow

### Step 1: Scan the session for repeated patterns

```
Look for in today's work:
- Methodological pivots ("v1-v4 didn't work, v5 with method X did")
- Debugging dead-ends ("turned out to be Y, not X/W/V/U/T as I guessed")
- Multi-step procedures repeated successfully ("first git mv, then python fixer, then grep")
- Hard-won insights stated as principles ("identity-layer first, tunnel-layer second")
- User-stated maxims ("measure, don't estimate")
```

In Daily Notes these often appear as:
- `★ Insight ─────` blocks
- `## Maxim of the day` sections
- `### Lesson` subsections at the end of debugging stories

### Step 2: For each pattern, run the ABC-filter explicitly

Don't skip filter B — that's where most candidates fail honestly. "Could be useful someday" is not the same as "I would have done it wrong without it."

### Step 3: Categorize ABC-pass candidates

| Candidate type | Right home |
|---|---|
| ABC ✅✅✅ — repeatable, prevents error, transferable | New Skill in `~/.claude/skills/<name>/SKILL.md` |
| A❌ — principle without steps | `.remember/core-memories.md` maxim |
| B❌ — wouldn't have gotten it wrong | Daily Note insight + maybe `.remember/core-memories.md` |
| C❌ — project-specific | `CLAUDE.md` of the project (or vault's CLAUDE.md) |
| Mechanical / automatic enforcement needed | `update-config` skill → settings.json hook |

### Step 4: Surface to user with explicit recommendation

```
Format:

## Skill candidates from this session

### 🥇 ABC ✅✅✅ (skill-worthy)
- **<candidate-name>** — <one-line trigger> — <one-line value>

### 🥈 Borderline (memory or CLAUDE.md instead)
- **<candidate>** — <why it fails which filter> — <recommended home>

### 🥉 One-offs (just log, no skill)
- <list>
```

Then ask: "which one do you want to build now?" — never decide for the user.

### Step 5: If skills are built, also consider the meta-level

- New skill triggered by something automatic? → propose a Hook via `update-config`
- 3+ related skills in same domain? → consider an Agent that wraps them
- Skill needs external state? → consider an MCP server

But these are **next-step considerations**, not part of this skill's scope. Mention, don't build.

## The honest test for "is this skill-worthy?"

Ask yourself: **"If I encounter this situation 3 months from now in a fresh session, will I (a) instinctively reach for this pattern, or (b) re-discover it the hard way?"**

If (a) — no skill needed, the pattern is robust enough to surface from memory.
If (b) — skill-worthy. Write it now.

## Anti-patterns

- ❌ **Over-extracting**: every session has SOME pattern. Most are one-offs. Use the filters honestly.
- ❌ **Under-extracting**: "it was just a normal session" — but the user worked 6 hours and learned 3 things. Don't skip the review just because the work felt routine.
- ❌ **Building without testing the description triggers**: a skill with vague triggers won't auto-fire. After writing, ask: "what user phrase should make this load?" and check the description contains it.
- ❌ **Skipping the 'Do NOT load' section**: leads to skill collisions and over-triggering.
- ❌ **Mixing skill-creation with end-of-session admin**: the review should produce a *list of candidates* — actual skill-writing happens in a follow-up step (or next session) to avoid context-bloat at session end.
- ❌ **Letting "Iron Law" stop the review**: the strict TDD-for-skills protocol applies when *building*; the *review* is just identification. Identification has no Iron Law.

## Quick prompt template

If you want to invoke this from your own internal monolog at session-end:

```
Run post-session-skill-review:
1. Scan today's Daily Note for ★ Insight blocks, Maxim-of-the-day, and Lesson sections
2. List every repeated pattern
3. For each, run ABC-filter
4. Output: skill-candidates / memory-entries / CLAUDE.md-updates / one-offs
5. Ask user which to build
```

## Real-world impact

A productive evening session applied this review (informally, before this skill existed) to a day with ~6 distinct workflow domains. Result: 4 ABC-pass skill candidates (embedded-ui-svg, obsidian-vault-restructure, tailscale-multi-account, brain-dump-to-roadmap) plus 2 borderlines (domain-defense as memory, daily-commit as hook). All 4 skills built in the same session in MVP form.

User quote: "Every process goes through multiple phases that inevitably include errors and detours. Learning from them for future sessions is one of the greatest strengths of the system. Combining skills into agents, building MCP servers, and integrating hooks follow. But skills are the key to success."

This skill IS that learning-loop, formalized.
