---
name: vault-search-helper
description: Use when the user names a topic/project/object and you must do a Vault-First search for existing notes (mandatory pattern: "Vault-First — required for every named topic"). A single call to `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py` replaces 2-3 Glob+Grep calls and returns ranked top-N notes with wikilink + score breakdown + excerpts. Trigger on phrases like "Vault-First", "where in vault", "find note", "existing on this", "check inventory", "is there already something", "search vault". Do NOT load for known-path file reads (use `Read` directly), for pure filename searches (use `Glob`), for external-system searches (LaunchAgents, remote server — use `ls` and `ssh`), or when the user explicitly requests a multi-pass search.
---

# Vault-Search-Helper

> ✅ **PROMOTED** — TDD pressure-test PASS. Saving 70-80% empirically (RED: 5 Glob/Grep calls ~14k tokens; GREEN: 1 vault-search.py call ~3.5k tokens). Cycle 2 polish items: stopword-score-inflation warning, cross-references to `.remember/` + skill dir, scope selection heuristic.

## Overview

Maxim: **"When the user names a topic, project, or object — whether at session start or mid-session — the first step is ALWAYS Vault-First search."** Previous standard practice: 2-3 separate calls (Glob for filename pattern + Grep for content pattern, possibly again differently).

**Token-cost pattern so far**: each Vault-First check costs ~2-3k tokens (Glob output + Grep output + re-reads). At 5 Vault-Firsts per session = ~10-15k tokens unnecessary.

**With tool**: a single `vault-search.py <query>` call returns ranked top-N notes with wikilink + score breakdown + 2-line excerpts. ~500-1000 tokens. **80% saving**.

## When to use

Trigger phrases (explicit):
- "Vault-First check on X"
- "What do we already have on X in the vault?"
- "Find note on X"
- "Existing inventory on X"
- "Is there already something on X?"

Trigger signals (implicit, without the user saying "Vault-First"):
- User mentions a topic (project name, concept, person, date, hardware component)
- It's not obvious whether/where it exists in the vault
- Task would otherwise be started "fresh" without context check

## When NOT to use

- **Known path**: user explicitly gives a file path → direct `Read` (no search needed)
- **Pure filename search**: "List all daily notes from June" → `Glob` is more efficient
- **Regex content match**: specific code pattern → `Grep` with regex
- **External-system search**: LaunchAgents (`ls ~/Library/LaunchAgents/`), remote server (`ssh ... cmd`), GitHub (`gh search`)
- **Multi-pass required**: user explicitly says "search roughly first, then refine" → own multi-step sequence

## How to use

### Step 1 — Formulate query

Multi-word query is OK. Tool stopword-filters (in, im, an, auf, und, oder, the, and, or) + does case-insensitive lowercase tokenize.

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py "stop too tight" --max 5
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py "leverage certificate" --scope projekte
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py "negotiation retirement" --include-archiv
```

### Step 2 — Choose scope

| `--scope` | Searches in |
|---|---|
| `projekte` | `02 Projekte/` |
| `bereiche` | `03 Bereiche/` |
| `ressourcen` | `04 Ressourcen/` |
| `daily` | `05 Daily Notes/` |
| `inbox` | `01 Inbox/` |
| `kontext` | `00 Kontext/` |
| `all` (default) | all except `06 Archiv/` |
| `+--include-archiv` | also `06 Archiv/` |

For a Vault-First check with unclear scope: `--scope all` (default). For production-domain questions: `--scope projekte`. For daily search: `--scope daily`.

### Step 3 — Interpret output

```json
{
  "query": "...",
  "query_words": [...],
  "total_candidates": 96,
  "returned": 3,
  "results": [
    {
      "rank": 1,
      "score": 109.0,
      "wikilink": "[[02 Projekte/token-optimierung/token-optimierung]]",
      "path_rel": "02 Projekte/token-optimierung/token-optimierung.md",
      "breakdown": {
        "filename": 2, "heading": 7, "content": 64,
        "tag": 2, "recency": 6.0
      },
      "excerpts": ["..."]
    }
  ]
}
```

**Interpretation**:
- `score >100`: strong hit, most likely relevant
- `score 30-100`: probably relevant, read excerpt
- `score <30`: weak hit, likely skip
- `breakdown.filename >0`: topic is in filename → hub note or main doc
- `breakdown.heading >3`: topic structurally relevant
- `breakdown.tag >0`: explicitly marked as tag → probably hub
- `breakdown.recency`: up to +6 points for new files (max 0 after 12 months)

### Step 4 — Read top note(s)

With wikilink → `Read` directly on `path_rel`. On score-tie between top-2: read both.

## Ranking Heuristic (Score Weights)

| Match type | Points | Reasoning |
|---|---|---|
| Filename match | +5 per query word | Filename is hub indicator |
| Frontmatter tag match | +4 per query word | Tag match = explicit categorization |
| Heading match (H1/H2/H3) | +3 per match | Structure signals topic centrality |
| Content match | +1 per occurrence | Mere mention |
| Recency boost | +0.5/month (max +6) | Newer files more likely relevant |

**Tuning backlog**: weights are heuristic, not empirically tuned. In Cycle-2 an A/B test against user-choice runs could find the optimum.

## Anti-patterns

| Anti-Pattern | What to do instead |
|---|---|
| `Glob "**/*.md"` + `Grep ...` (2 calls) for Vault-First | `vault-search.py <query>` (1 call) |
| Multi-pass: Glob first, then Grep in the result | vault-search does both in one pass |
| Multiple searches with synonyms | Multi-word query already contains variations, stopword filter handles the rest |
| Recursive subagent for vault search | Overhead eats the saving, vault-search is sync enough |
| Vault search for code files | only for `.md`, not for `.py`/`.ts`/`.yaml` |

## Token-Saving Empirics

Smoke test with `"token optimierung"`:
- **96 candidates** searched (all .md in 6 scopes)
- **Top-3 returned** with score 109 / 99 / 78
- **Output size**: ~3 KB JSON ≈ 700 tokens
- **Previously (Glob+Grep manually)**: ~3-5k tokens for same output

**Saving per Vault-First**: ~70-80%. At 5 Vault-Firsts/session = **~10-15k tokens/session saved**.

## Cross-References

- "Vault-First — required" maxim — the underlying rule
- `pdf-text-extract-without-vision` (GA) — sister skill for PDFs
- `image-preprocessing-helper` — Vision token saver
- `bash-output-filtering-disciplines` — same token-optimization family

## Background: TDD Trail (Bulletproofing Log)

### Cycle 1 — PASS

- **RED-Subagent** (without skill): 5 tool calls (broad Grep + focused Grep -C=2 + 2× Glob + Read of top-2), ~14k tokens total. Systematically overlooked `.remember/core-memories.md`, CLAUDE.md itself, the skill directory. "Drift risk high — only 60-70% coverage on first iteration."
- **GREEN-Subagent** (with skill): 1× `vault-search.py "stop loss too tight" --max 5` + 1 refinement `--scope projekte` + 3 grep excerpts, ~3.5k tokens. **Saving 70-80%** exactly in the skill-promised corridor. Also discovered stopword-score-inflation (score 124 for a false positive on a multi-word stopword query).
- **Refactor**: none blocking; Cycle-2 backlog expanded.

### Cycle-2 Backlog (Polish, non-blocking)

- **Anti-pattern "stopword-score-inflation"**: with score >100 without filename/tag boost → counter-grep with exact phrase as disambiguation layer
- **Scope selection heuristic**: production-domain topics → `--scope projekte` default; daily-note cross-check optional
- **Cross-references to non-vault sources**: skill should explicitly mention that `.remember/`, CLAUDE.md, `~/.claude/skills/` are not indexed by the tool — caller must check separately
- Embedding-based ranking (sentence-transformers locally)
- Persistent index (SQLite or JSON cache)
- Multi-vault support (private vs work vault)
- Cache invalidation on vault mods (inotify or polling)
- Fuzzy match for typos
