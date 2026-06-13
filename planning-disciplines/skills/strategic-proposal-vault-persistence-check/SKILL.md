---
name: strategic-proposal-vault-persistence-check
description: Use at session-end (or mid-session when about to wrap a strategic discussion) when the session has produced structured strategic content — multi-row tables (priority/effort/value matrices, tool inventories), JSON/data schemas (API responses, config-shapes), multi-step recommendations ("Stufe 1: ..., Stufe 2: ..."), 5-category frameworks, or anything that took >10min to think through and structure. The risk: this content lives in the conversation buffer, NOT in the Vault — when context expires (1M tokens for Fable/Opus, faster for Sonnet) the entire structuring effort is lost, and a future session has to re-discover it from scratch. Encodes the 2026-06-11 anti-pattern where the previous session erarbeitete (a) 5-category Token-Optimization framework, (b) 6-tool prioritized candidate table, (c) JSON-Schema for health-aggregator, (d) 4-stage recommendation sequence — and persisted NONE of it; today's recovery cost ~30-40k tokens to rebuild from Wolf's memory + paste-backs. Trigger phrases like "Session zu Ende", "Tagesabschluss", "session wrap-up", "ist das im Vault?", "wo sollten wir wieder aufsetzen?", "die letzte Session hatte nichts dokumentiert", "haben wir das festgehalten?", "fasse das mal zusammen für später", "remember", "wrap up". Do NOT load for sessions that produced only ephemeral content (chat-only, single-file-edit, debug-trace) — there's no strategic content to persist. Do NOT load mid-task when the strategic discussion is still active — the persistence step belongs at the natural end of the strategic block, not as interruption. Do NOT load when post-session-skill-review is already running and will cover the same scan — they're complementary but should not duplicate-scan the same Daily Note (skill-review looks for SKILL candidates; this skill looks for PROPOSAL persistence). If both apply, run this one FIRST (proposals into Vault) THEN skill-review (Skill candidates from session including newly persisted proposals).
---

# Strategic Proposal Vault Persistence Check

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test PASS. RED: 3-Zeilen-Daily-Note-Limbo („Daily-Note-zentriert statt Vault-Strukturen-zentriert"); GREEN: 4-Step Persistence-Check + Target-Pfade pro Output + Status-Marker mit Datums-Spalte + Privacy-Boundary aus CLAUDE.md mitberücksichtigt. Cycle 2 Polish: Privacy-Boundary explizit (sensible-Tag-Liste-Verlinkung), 50%-persistiert-Edge-Case (existing erweitern vs parallel), JSON-Schema-Beispiel-Snippet, Cross-Ref zu „Current Truth vor Timeline".

The most expensive bug in multi-session work is **re-discovery**: a previous session figured something substantial out, didn't write it down, and the current session pays for the rebuild. This skill is the systematic check that prevents it.

## When to use

- Natural end of a strategic discussion block (decision tree, prioritization, roadmap)
- Session-end, before context-window close
- Mid-session pivot from "thinking through" mode to "doing" mode
- User pushback "ist das im Backlog?" or "wo sollten wir wieder aufsetzen?"
- When you notice yourself constructing a table, JSON-schema, or multi-step recommendation that took >10 minutes of structuring

## When NOT to use

- Chat-only sessions with no structured output
- Mid-debug or mid-implementation — finish the active task first
- When `post-session-skill-review` is already running on the same Daily Note — coordinate (run this FIRST, then skill-review)
- One-off solutions to single-instance problems (just log in Daily Note, no Vault-cluster needed)

## The check (4 steps, ~5-10 minutes)

### Step 1: Scan the session output for "structured strategic content"

Mentally walk back through the session and flag any of:
- **Multi-row decision tables** (priority × effort × value, candidate × pain-point × reduction)
- **JSON/data schemas** with concrete keys (API response shapes, config templates)
- **Numbered multi-step recommendations** ("Stufe 1: X, Stufe 2: Y, ...")
- **N-category frameworks** ("3 strategies", "5 categories", "7 anti-patterns")
- **Effort-estimated backlogs** with time-estimates per item
- **Pain-anchor + counter-measure pairings** ("Pre-State: 25 calls / Post-State: 1 call")

If NONE of these appeared → no proposals to persist, skip this skill.

If 1+ → continue to Step 2.

### Step 2: Vault-grep for existing persistence

For each flagged content-block, search the Vault for whether it's already there:
```
Grep keywords from the content (proper nouns, table-row identifiers, distinct phrases)
across `02 Projekte/`, `03 Bereiche/`, `04 Ressourcen/`, and today's Daily Note.
```

If the content is **already in a Cluster-Hub or Daily Note section** → done, no action needed.
If it's **only in the conversation buffer** → continue to Step 3.

### Step 3: Choose the persistence target

| Content type | Target |
|---|---|
| Strategic framework (N categories, multi-domain) | New cluster `02 Projekte/<theme>/<theme>.md` |
| Single-topic decision/roadmap | Existing project's hub note + new sub-note |
| Tooling/method recommendation | `04 Ressourcen/AI & Machine Learning/<topic>.md` |
| User-specific maxim derived from session | `.remember/core-memories.md` + Vault-CLAUDE.md |
| Backlog table for one project | Existing project's hub `## Backlog` section |

If unsure, default to: **new cluster note with explicit "Roadmap" + "Backlog" + "Bestandsaufnahme" structure**. Single-purpose hub-note is recoverable later; missing content is not.

### Step 4: Write with Status-Marker per item

Critical: don't just copy-paste the proposal. Add a **Status column** (`✅ done` / `⚠ partial` / `❌ open`) per row/item.

Without status: future session reads it as "fresh backlog" and re-evaluates. With status: future session sees "X done, Y open" and continues from where you left off.

For tables:
```markdown
| # | Item | Effort | Token-Reduction | **Status 11.06.** |
|---|---|---|---|---|
| 1 | ultimative-health-aggregator | 3h | 90% | ✅ Phase A-G live |
| 2 | logs-prefilter | 1h | 70% | ✅ als /health/logs integriert |
| 3 | vault-search-helper | 1h | 20% | ❌ Sprint 2 |
```

For step-sequences:
```markdown
| Stufe | Aktion | **Status** |
|---|---|---|
| Sofort (5min) | MCP aktivieren | ✅ erledigt |
| Diese Woche (3h) | health-aggregator | ✅ in 50min Wallclock |
```

## Quick-Reference Workflow

```
1. Session-Ende erreicht (oder Wolf: "lass uns abschließen")
2. Scan: tab. / schema / N-step / N-category? [Ja/Nein]
3. wenn Ja: grep Vault für 2-3 distinct keywords aus jedem Block
4. wenn nicht persistiert: Target-Pfad wählen + Note anlegen
5. Content kopieren MIT Status-Spalte pro Zeile
6. Daily Note: kurzen Verweis "→ [[link]]" hinterlegen
7. Brain-Dump / Inbox: Original-Block als <!-- migriert → [[link]] --> markieren
```

## Anti-patterns

- ❌ **"Das kommt morgen ins Backlog"** — morgen ist eine neue Session ohne Context. JETZT persistieren, nicht später.
- ❌ **Copy-paste ohne Status-Marker** — Status ist der Unterschied zwischen „lebendiger Roadmap" und „toter Backlog-Liste"
- ❌ **In Daily Note nur „Status: erarbeitet"** — Daily Notes werden nicht durchsucht für „was läuft?". Das gehört in Project-Cluster.
- ❌ **Vault-Grep skippen** und sofort neue Notiz erstellen — führt zu Doppel-Strukturen (zwei Cluster für dasselbe Thema)
- ❌ **Zu fein-granular persistieren** — JEDER einzelne Tabellen-Eintrag als eigene Notiz erzeugt Vault-Sprawl. Eine konsolidierte Cluster-Notiz mit Sub-Sektionen ist besser.
- ❌ **Original-Wording neu formulieren** — User-Sprache erhalten (besonders Wolf's eigene Maximen + Quotes). Re-Phrasing verliert Nuancen.

## Real-world example: 2026-06-11 ultimative-health session

**Vorige Session** (vor 11.06.) erarbeitete:
- 5-Kategorien-Token-Optimization-Framework (Modellauswahl/Sub-Agents/MCP/Tools/Disziplinen)
- 6-Tool-Kandidaten-Tabelle (Tool / Pain-Point / Effort / Reduction)
- JSON-Schema für ultimative-health Endpoint
- 4-Stufen-Empfehlung-Reihenfolge

Persistiert: **nichts**. Brain-Dump-Item „Token-Optimierung" hatte nur 3 Stichworte.

**11.06. Folge-Session**:
- Wolf-Pushback: „die vorherige Session hatte nichts dokumentiert"
- Recovery cost: ~30-40k Tokens (Wolf paste-back + Cluster-Anlegen + Schema-rückbau + Status-Marker pro Item)
- Hätte mit DIESEM Skill am Vorige-Session-Ende ~5-10 Minuten gekostet → 5-10× ROI

Token-Saving aus aktiver Anwendung dieses Skills: ~25-35k pro vermiedener Re-Discovery.

## Connection to other skills

- `post-session-skill-review` (GA) — complementary; that one scans for SKILL candidates, this one for PROPOSAL persistence. Run THIS one FIRST so proposals are in Vault before skill-review scans.
- `obsidian-vault-graph-cleanup` (GA) — after cluster-creation, this catches duplicate-cluster scenarios
- `brain-dump-to-phased-roadmap` (GA) — if persistence target is a fresh brain-dump-derived cluster, use that skill for the Roadmap-Phasen-Struktur

## Promotion notes (DRAFT → GA)

Created 2026-06-11 after Wolf-Pushback on missing persistence of previous-session strategic proposals. Promote via `skill-tdd-promotion-workflow` after:
- 1 RED-Subagent pressure-test: edge-cases like "proposal partially persisted (50% in Daily Note, 50% in conversation buffer)" and "proposal contradicts existing cluster"
- 1 real-world catch where the skill fires correctly at session-end and identifies an un-persisted strategic block
- Cross-link to `post-session-skill-review` with explicit "run me FIRST" coordination note
