---
name: vault-search-helper
description: Use when Wolf nennt ein Thema/Projekt/Objekt und du musst Vault-First nach existing Notes suchen (Pflicht-Pattern aus CLAUDE.md 08.06.2026 „Vault-First — PFLICHT bei jedem genannten Thema"). Ein einziger Call zu `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py` ersetzt 2-3 Glob+Grep-Calls und liefert ranked Top-N Notes mit Wikilink + Score-Breakdown + Excerpts. Trigger on phrases like "Vault-First", "wo in vault", "finde Notiz", "existing dazu", "Bestand prüfen", "gibt es schon was", "search vault". Do NOT load for known-path-File-Reads (use `Read` direkt), für reine Filename-Searches (use `Glob`), für External-System-Searches (LaunchAgents, swatserver — use `ls` und `ssh`), oder wenn der User explizit Multi-Pass-Search verlangt.
---

# Vault-Search-Helper

> ✅ **PROMOTED 2026-06-12** — TDD-Pressure-Test PASS. Saving 70-80% empirisch (RED: 5 Glob/Grep-Calls ~14k Tokens; GREEN: 1 vault-search.py-Call ~3.5k Tokens). Cycle 2 Polish-Items: Stopword-Score-Inflation-Warnung, Cross-References zu `.remember/`+Skill-Dir, Scope-Auswahl-Heuristik.

## Overview

Wolf-Maxime CLAUDE.md 08.06.2026: **„Wenn Wolf ein Thema, Projekt oder Objekt nennt — egal ob zu Sessionbeginn oder mittendrin — ist der erste Schritt IMMER Vault-First-Suche."** Bisherige Standard-Praxis: 2-3 separate Calls (Glob für Filename-Pattern + Grep für Content-Pattern, ggf. nochmal anders).

**Token-Cost-Pattern bisher**: jeder Vault-First-Check kostet ~2-3k Tokens (Glob-Output + Grep-Output + Re-Reads). Bei 5 Vault-Firsts pro Session = ~10-15k Tokens überflüssig.

**Mit Tool**: ein einziger `vault-search.py <query>`-Call liefert ranked Top-N Notes mit Wikilink + Score-Breakdown + 2-Line-Excerpts. ~500-1000 Tokens. **80% Saving**.

## When to use

Trigger-Phrasen (explizit):
- „Vault-First-Check zu X"
- „Was haben wir schon zu X im Vault?"
- „Finde Notiz zu X"
- „Existing Bestand zu X"
- „Gibt es schon was zu X?"

Trigger-Signale (implizit, ohne dass Wolf das Wort „Vault-First" sagt):
- Wolf nennt ein Thema (Projekt-Name, Konzept, Person, Datum, Hardware-Komponente)
- Es ist nicht offensichtlich ob/wo es im Vault existiert
- Aufgabe würde sonst „neu" gestartet ohne Kontext-Check

## When NOT to use

- **Known Path**: User gibt explizit File-Pfad → direkt `Read` (kein Search nötig)
- **Pure Filename-Search**: „Liste alle Daily Notes vom Juni" → `Glob` ist effizienter
- **Regex-Content-Match**: spezifisches Code-Pattern → `Grep` mit Regex
- **External-System-Search**: LaunchAgents (`ls ~/Library/LaunchAgents/`), swatserver (`ssh ... cmd`), GitHub (`gh search`)
- **Multi-Pass-Required**: User sagt explizit „suche erst mal grob, dann verfeinere" → eigene Multi-Step-Sequenz

## How to use

### Step 1 — Query formulieren

Multi-Word-Query ist OK. Tool stopword-filtert (in, im, an, auf, und, oder, the, and, or) + macht case-insensitive Lowercase-Tokenize.

```bash
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py "stop zu eng" --max 5
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py "ko schein hebel" --scope projekte
${CLAUDE_PLUGIN_ROOT:-$HOME/.claude}/tools/vault-search.py "verhandlung renten" --include-archiv
```

### Step 2 — Scope wählen

| `--scope` | Sucht in |
|---|---|
| `projekte` | `02 Projekte/` |
| `bereiche` | `03 Bereiche/` |
| `ressourcen` | `04 Ressourcen/` |
| `daily` | `05 Daily Notes/` |
| `inbox` | `01 Inbox/` |
| `kontext` | `00 Kontext/` |
| `all` (default) | alle außer `06 Archiv/` |
| `+--include-archiv` | auch `06 Archiv/` |

Bei Vault-First-Check unklarem Scope: `--scope all` (default). Bei Trading-Frage: `--scope projekte`. Bei Daily-Suche: `--scope daily`.

### Step 3 — Output interpretieren

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
- `score >100`: starker Treffer, höchstwahrscheinlich relevant
- `score 30-100`: wahrscheinlich relevant, lese Excerpt
- `score <30`: schwacher Treffer, eher skippen
- `breakdown.filename >0`: Thema ist im Filename → Hub-Note oder Hauptdoku
- `breakdown.heading >3`: Thema strukturell relevant
- `breakdown.tag >0`: explizit als Tag markiert → wahrscheinlich Hub
- `breakdown.recency`: bis +6 Punkte für neue Files (max 0 nach 12 Monaten)

### Step 4 — Top-Note(s) lesen

Mit Wikilink → `Read` direkt auf `path_rel`. Bei Score-Tie zwischen Top-2: beide lesen.

## Ranking-Heuristik (Score-Gewichte)

| Match-Typ | Punkte | Begründung |
|---|---|---|
| Filename-Match | +5 pro Query-Wort | Filename ist Hub-Indikator |
| Frontmatter-Tag-Match | +4 pro Query-Wort | Tag-Match = explizite Kategorisierung |
| Heading-Match (H1/H2/H3) | +3 pro Match | Struktur signalisiert Thema-Zentralität |
| Content-Match | +1 pro Vorkommen | Reine Erwähnung |
| Recency-Boost | +0.5/Monat (max +6) | Neuere Files wahrscheinlich relevanter |

**Tuning-Backlog**: Gewichte sind heuristisch, empirisch nicht ge-tuned. Bei Cycle-2 könnte ein A/B-Test gegen User-Choice runs Optimum finden.

## Anti-patterns

| Anti-Pattern | Was statt dessen |
|---|---|
| `Glob "**/*.md"` + `Grep ...` (2 Calls) für Vault-First | `vault-search.py <query>` (1 Call) |
| Multi-Pass: erst Glob, dann Grep im Result | vault-search macht beides in einem Pass |
| Multiple Searches mit Synonymen | Multi-Word-Query enthält schon Variationen, Stopword-Filter macht den Rest |
| Recursive Subagent für Vault-Search | Overhead frisst Saving, vault-search ist sync genug |
| Vault-Search für Code-Files | nur für `.md`, nicht für `.py`/`.ts`/`.yaml` |

## Token-Saving Empirik (12.06.2026)

Smoke-Test mit `"token optimierung"`:
- **96 candidates** durchsucht (alle .md in 6 Scopes)
- **Top-3 returned** mit Score 109 / 99 / 78
- **Output-Größe**: ~3 KB JSON ≈ 700 Tokens
- **Vorher (Glob+Grep manuell)**: ~3-5k Tokens für gleichen Output

**Saving pro Vault-First**: ~70-80%. Bei 5 Vault-Firsts/Session = **~10-15k Tokens/Session gespart**.

## Cross-References

- CLAUDE.md 08.06.2026 „Vault-First — PFLICHT" — die zugrundeliegende Wolf-Maxime
- `pdf-text-extract-without-vision` (GA seit 11.06.) — Schwester-Skill für PDFs
- `image-preprocessing-helper` (DRAFT seit 12.06.) — Vision-Token-Saver
- `bash-output-filtering-disciplines` (DRAFT seit 11.06.) — selbe Token-Optimierungs-Familie

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-12 (PASS)

- **RED-Subagent** (ohne Skill): 5 Tool-Calls (broad Grep + focused Grep -C=2 + 2× Glob + Read der Top-2), ~14k Tokens total. Übersah systematisch `.remember/core-memories.md`, CLAUDE.md selbst, Skill-Verzeichnis. „Drift-Risiko hoch — nur 60-70% Coverage in erster Iteration."
- **GREEN-Subagent** (mit Skill): 1× `vault-search.py "stop loss zu eng" --max 5` + 1 Refinement `--scope projekte` + 3 Grep-Excerpts, ~3.5k Tokens. **Saving 70-80%** exakt im Skill-versprochenen Korridor. Entdeckte zudem Stopword-Score-Inflation (Score 124 für False-Positive bei Multi-Word-Stopword-Query).
- **Refactor**: keiner blocker; Cycle-2-Backlog erweitert.

### Cycle-2-Backlog (Polish, nicht-blocking)

- **Anti-Pattern „Stopword-Score-Inflation"**: bei Score >100 ohne filename/tag-Boost → gegen-Greppen mit exakter Phrase als Disambiguierung-Layer
- **Scope-Auswahl-Heuristik**: Trading-Themen → `--scope projekte` Default; Daily-Note-Cross-Check optional
- **Cross-References zu Non-Vault-Quellen**: Skill sollte explizit erwähnen dass `.remember/`, CLAUDE.md, `~/.claude/skills/` nicht durch das Tool indexiert werden — Caller muss separat checken
- Embedding-basiertes Ranking (sentence-transformers lokal)
- Persistent Index (SQLite oder JSON-Cache)
- Multi-Vault-Support (private vs work-Vault)
- Cache-Invalidation bei Vault-Mods (inotify oder polling)
- Fuzzy-Match für Tippfehler

