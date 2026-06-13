---
name: forensik-hypothese-widerlegt-code-read-weiter
description: Use when conducting a forensic investigation with explicit hypotheses (H1/H2/H3) on a system bug or anomaly, and 2+ hypotheses have been disproved by code-read or DB-query. Default-behavior is "Hypothesis disproved → investigation done, no real bug". This skill says: continue code-read with no specific hypothesis — bonus-findings often surface during the disproving process and are real bugs that would be missed otherwise. Trigger on phrases like "hypothesis H1 disproved", "all theories wrong", "forensics inconclusive", "no bug found but weird behavior", "abort forensics", "nothing there after all". Do NOT load for hypothesis-testing in research code where "disproved" is success, for time-boxed forensics with a hard stop after X minutes, when user explicitly says "if the hypotheses are disproved we are done", or for non-investigative tasks.
---

# Forensics: Hypothesis disproved → continue code-read

> ✅ **PROMOTED** — TDD pressure test PASS. GREEN structured bonus findings systematically (4 findings with a severity table: 2 Critical + 1 Important + 1 Minor) — RED did arrive at "keep investigating" via self-reflection but delivered an unstructured path list. Skill value: structured pattern instead of ad-hoc forensics. Cycle 2 polish: "at-least X" pre-existing-duration hint, user-confirmation-before-DB-DELETE cross-ref, project-CLAUDE.md linking.

## Overview

Forensic sessions often start with 2-3 plausible hypotheses. Default workflow:
1. Formulate hypotheses
2. Per hypothesis collect evidence (code-read, DB query, log inspect)
3. If all disproved: "no bug, wrong hypothesis" → end session

**Problem**: collecting evidence takes Claude deep into code that was under-investigated. **Bonus findings emerge precisely then** — bugs that have nothing to do with the original hypothesis but become visible during code-read. The default workflow misses them.

**Fix**: after a hypothesis is disproved, do NOT stop. Instead:
- Continue code-read without a specific hypothesis
- Watch for "second-order anomalies" (odd schema, redundant code paths, missing constraints)
- Document bonus findings with a clear severity rating (Critical/Important/Minor)

## When to use

Trigger phrases:
- "Hypothesis H1 disproved"
- "All theories are wrong"
- "Forensics inconclusive, no bug"
- "Weird behavior but no clear cause"
- "Should we abort the forensics?"

Concrete signals:
- 2+ hypotheses have been disproved with hard evidence (code-read shows pattern absent, DB has expected values)
- User maxim: "I don't understand this anomaly" → pattern for bonus-finding risk
- Code-read for hypothesis tests has already taken 30+ minutes

## When NOT to use

- **Research code**: "Hypothesis disproved" is a success state, not a bug hint
- **Time-boxed forensics**: user explicitly says "max 30 min, then whatever"
- **Clear hypothesis set**: when the 3 hypotheses fully cover the solution space
- **User override**: "if nothing is found, we're done"

## How to use

### Step 1 — Document the disproof

Per disproved hypothesis:
- **H1**: claim
- **Test**: what was checked (code-read / DB query / log)
- **Result**: what was found (pattern doesn't exist / values OK / logs clean)

This documentation stays in the forensic report — even if bonus findings dominate.

### Step 2 — Continue code-read without hypothesis

Continue with the **adjacent code paths**:
- What happens after the test point?
- Which **constraints** exist (DB indexes, NOT NULL, FK cascades)?
- Which **silent failures** could occur (try/except, COALESCE, default values)?
- Which **redundant paths** exist (two modules doing something similar)?

### Step 3 — Hunt second-order anomalies

Bonus-finding indicators during code-read:
- "There should be a dedup check here, but there isn't"
- "This column is nullable even though it should be required"
- "Two stages write to the same table without coordination"
- "COALESCE hides NULL values that get rendered as 0"
- "Schema drift between code convention and DB reality"

### Step 4 — Document bonus findings with severity rating

Per bonus finding:
- **Severity**: Critical (money-loss risk) / Important (user spam) / Minor (cycle 2)
- **User impact**: concrete experience for the user
- **Fix approach**: brief sketch
- **Pre-existing duration**: how long has the bug been latent?

### Step 5 — Write the forensic report

Structure:
1. Hypothesis disproof (short, evidence-based)
2. **Bonus findings** (main result, with severity list)
3. Backlog items + sequencing recommendation

## Anti-patterns

| Anti-pattern | What to do instead |
|---|---|
| "H1+H2+H3 disproved → session done" | Continue code-read with a "second-order anomaly" eye |
| Dismiss bonus finding as "random stuff" | Severity rating + user-impact documented |
| Hide hypothesis disproof in the report (only show bonus finding) | Document both — disproof protects against later "why didn't you check that" |
| Restrict code-read to a single function | Expand to the call chain + schema + constraints |

## Real-world impact

A direction-flip-before-advisor forensic investigation:
- H1: advisor cache lag → **disproved** (code-read: advisor runs async after persist)
- H2: different data basis → **disproved** (same DB queries)
- H3: independent direction computation in the advisor → **disproved** (advisor is a plausibility check, no direction)

The default workflow would have said: "the user's observation is expected behavior, no action."

With this skill: code-read continued → found `persist_signal` without a dedup check → 19 duplicate clusters with up to 12× → **Critical bug discovery**.

Consequence: 4 additional commits (code fix + cleanup + UNIQUE INDEX), 58 duplicates deleted, future notification spam eliminated.

## Cross-references

- `reporting-artefact-detection-before-claiming-anomaly` — predecessor skill (triage before forensic start)
- `superpowers:systematic-debugging` — related pattern for bug hunting
- `db-telemetry-primary-docker-logs-secondary` — forensic-source hierarchy

## Background

Pattern discovered after a user-directed forensic investigation into a direction flip. Extends the maxim "read logs/code/DB first before formulating a hypothesis" with the after-hypothesis continuation aspect.

## Background: TDD Log (Bulletproofing)

### Cycle 1 — PASS (with caveat)

- **RED-Subagent** (without skill): self-identified that "all MY hypotheses disproved = hypothesis set was incomplete" — surprisingly strong. But delivered an unstructured path list (Telegram layer, retry pattern, DB trigger, multiple senders) as "possibly missed", no systematic approach.
- **GREEN-Subagent** (with skill): structured 5-step approach (document disproof → continue code-read → second-order anomalies → bonus findings with severity → report). Delivered 4 bonus findings with severity table (Critical/Important/Minor) + sequencing recommendation to the user.
- **Skill value**: RED is "lucky engineer with self-awareness", GREEN is "structured forensic process". Skill replaces luck with system.
- **Refactor**: none blocking.

### Cycle-2 Backlog (polish, non-blocking)

- **"At-least X" pre-existing-duration hint**: when DB retention < suspected bug duration, document "at least X days, probably longer" as a valid answer
- **User-confirmation-before-DB-DELETE** pattern as cross-reference (project-CLAUDE.md maxim)
- **Cross-reference** to project-specific maxims for Critical findings with DB cleanup requirements
