---
name: strategic-proposal-vault-persistence-check
description: |-
  Use at session-end (or mid-session when about to wrap a strategic discussion) when the session has produced structured strategic content — multi-row tables (priority/effort/value matrices, tool inventories), JSON/data schemas (API responses, config-shapes), multi-step recommendations ("Stage 1:..., Stage 2:..."), 5-category frameworks, or anything that took >10min to structure. Risk: this content lives in the conversation buffer, NOT in persistent knowledge — when context expires the entire structuring effort is lost. Trigger phrases like "session wrap-up", "end of day", "is that in the vault?", "did Claude capture that?", "summarize for later", "remember", "wrap up". Do NOT load for sessions producing only ephemeral content (chat-only, single-file-edit, debug-trace), mid-task while strategic discussion is still active, or when post-session-skill-review is already covering the same scan.

---

# Strategic Proposal Vault Persistence Check

> ✅ **PROMOTED** — TDD pressure test PASS. RED: 3-line daily-note limbo ("daily-note-centric instead of vault-structure-centric"); GREEN: 4-step persistence check + target paths per output + status markers with date column + privacy boundary from CLAUDE.md considered. Cycle 2 polish: privacy boundary explicit (sensitive-tag list linking), 50%-persisted edge case (extend existing vs parallel), JSON schema example snippet, cross-ref to "Current Truth before Timeline".

The most expensive bug in multi-session work is **re-discovery**: a previous session figured something substantial out, didn't write it down, and the current session pays for the rebuild. This skill is the systematic check that prevents it.

## When to use

- Natural end of a strategic discussion block (decision tree, prioritization, roadmap)
- Session-end, before context-window close
- Mid-session pivot from "thinking through" mode to "doing" mode
- User pushback "is that in the backlog?" or "where should we pick up?"
- When you notice yourself constructing a table, JSON-schema, or multi-step recommendation that took >10 minutes of structuring

## When NOT to use

- Chat-only sessions with no structured output
- Mid-debug or mid-implementation — finish the active task first
- When `post-session-skill-review` is already running on the same daily note — coordinate (run this FIRST, then skill-review)
- One-off solutions to single-instance problems (just log in daily note, no vault-cluster needed)

## The check (4 steps, ~5-10 minutes)

### Step 1: Scan the session output for "structured strategic content"

Mentally walk back through the session and flag any of:
- **Multi-row decision tables** (priority × effort × value, candidate × pain-point × reduction)
- **JSON/data schemas** with concrete keys (API response shapes, config templates)
- **Numbered multi-step recommendations** ("Stage 1: X, Stage 2: Y, ...")
- **N-category frameworks** ("3 strategies", "5 categories", "7 anti-patterns")
- **Effort-estimated backlogs** with time estimates per item
- **Pain-anchor + counter-measure pairings** ("Pre-state: 25 calls / Post-state: 1 call")

If NONE of these appeared → no proposals to persist, skip this skill.

If 1+ → continue to Step 2.

### Step 2: Vault-grep for existing persistence

For each flagged content block, search the vault for whether it's already there:
```
Grep keywords from the content (proper nouns, table-row identifiers, distinct phrases)
across `Projects/`, `Areas/`, `Resources/`, and today's daily note.
```

If the content is **already in a cluster hub or daily-note section** → done, no action needed.
If it's **only in the conversation buffer** → continue to Step 3.

### Step 3: Choose the persistence target

| Content type | Target |
|---|---|
| Strategic framework (N categories, multi-domain) | New cluster `Projects/<theme>/<theme>.md` |
| Single-topic decision/roadmap | Existing project's hub note + new sub-note |
| Tooling/method recommendation | `Resources/AI & Machine Learning/<topic>.md` |
| User-specific maxim derived from session | Core memories + project CLAUDE.md |
| Backlog table for one project | Existing project's hub `## Backlog` section |

If unsure, default to: **new cluster note with explicit "Roadmap" + "Backlog" + "Inventory" structure**. Single-purpose hub note is recoverable later; missing content is not.

### Step 4: Write with status marker per item

Critical: don't just copy-paste the proposal. Add a **status column** (`✅ done` / `⚠ partial` / `❌ open`) per row/item.

Without status: future session reads it as "fresh backlog" and re-evaluates. With status: future session sees "X done, Y open" and continues from where you left off.

For tables:
```markdown
| # | Item | Effort | Token-Reduction | **Status** |
|---|---|---|---|---|
| 1 | health-aggregator | 3h | 90% | ✅ Phase A-G live |
| 2 | logs-prefilter | 1h | 70% | ✅ integrated as /health/logs |
| 3 | vault-search-helper | 1h | 20% | ❌ a planned later phase |
```

For step sequences:
```markdown
| Stage | Action | **Status** |
|---|---|---|
| Immediate (5min) | activate MCP | ✅ done |
| This week (3h) | health-aggregator | ✅ in 50min wallclock |
```

## Quick-Reference Workflow

```
1. End of session reached (or user: "let's wrap up")
2. Scan: tab. / schema / N-step / N-category? [Yes/No]
3. if Yes: grep vault for 2-3 distinct keywords from each block
4. if not persisted: choose target path + create note
5. Copy content WITH status column per row
6. Daily note: leave short reference "→ [[link]]"
7. Brain-dump / inbox: mark original block as <!-- migrated → [[link]] -->
```

## Anti-patterns

- ❌ **"That'll go in the backlog tomorrow"** — tomorrow is a new session without context. Persist NOW, not later.
- ❌ **Copy-paste without status marker** — status is the difference between "living roadmap" and "dead backlog list"
- ❌ **In daily note only "Status: worked out"** — daily notes are not searched for "what's running?". That belongs in the project cluster.
- ❌ **Skipping vault grep** and immediately creating new note — leads to double structures (two clusters for the same topic)
- ❌ **Persisting too fine-grained** — EACH single table entry as its own note creates vault sprawl. A consolidated cluster note with sub-sections is better.
- ❌ **Rephrasing original wording** — preserve the user's language (especially the user's own maxims + quotes). Re-phrasing loses nuance.

## Real-world example: health-aggregator session

**Previous session** worked out:
- 5-category token-optimization framework (model selection / sub-agents / MCP / tools / disciplines)
- 6-tool candidate table (tool / pain-point / effort / reduction)
- JSON schema for health endpoint
- 4-stage recommendation order

Persisted: **nothing**. Brain-dump item "token optimization" had only 3 keywords.

**Follow-up session**:
- User pushback: "the previous session had nothing documented"
- Recovery cost: ~30-40k tokens (user paste-back + cluster creation + schema rebuild + status marker per item)
- Would have cost ~5-10 minutes at end of previous session with THIS skill → 5-10× ROI

Token saving from active application of this skill: ~25-35k per avoided re-discovery.

## Connection to other skills

- `post-session-skill-review` (GA) — complementary; that one scans for SKILL candidates, this one for PROPOSAL persistence. Run THIS one FIRST so proposals are in vault before skill-review scans.
- `obsidian-vault-graph-cleanup` (GA) — after cluster creation, this catches duplicate-cluster scenarios
- `brain-dump-to-phased-roadmap` (GA) — if persistence target is a fresh brain-dump-derived cluster, use that skill for the roadmap-phase structure

## Promotion notes (DRAFT → GA)

Created after user pushback on missing persistence of previous-session strategic proposals. Promote via `skill-tdd-promotion-workflow` after:
- 1 RED subagent pressure test: edge cases like "proposal partially persisted (50% in daily note, 50% in conversation buffer)" and "proposal contradicts existing cluster"
- 1 real-world catch where the skill fires correctly at session-end and identifies an un-persisted strategic block
- Cross-link to `post-session-skill-review` with explicit "run me FIRST" coordination note
