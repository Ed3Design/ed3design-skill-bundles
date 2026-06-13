---
name: schema-use-case-mismatch-detection
description: Use when a user reports "field X is always NULL in table Y despite active code" or "data missing from a table that's actively being written to" — BEFORE jumping to "fix the bug, set the field". The Iron-Law: when a single DB-table has ≥2 writer-paths with different semantics (e.g. one writer is per-trade, another is per-portfolio, or legacy vs new pipeline), the field-NULL-symptom is often NOT a bug but a schema-use-case-mismatch — the active writer simply doesn't have the semantics to produce that field. A "fix" without this check would patch the writer to set a value-that-doesn't-exist-semantically, producing meaningless or wrong data in the DB. Trigger on phrases like "verdict ist immer NULL", "field X always missing", "this column is never populated", "53 rows all with NULL in field Y", "INSERT-Liste unvollständig", "data not appearing in table despite job running", "schema-drift", "legacy table being used by new code", "two write-paths same table different semantics". Do NOT load for ALTER-TABLE-missing-column (different problem — schema-evolution), for permission-issues (writer can't access table), for connection-issues (writer crashes silently), or for first-implementation of a feature (no historical pattern to verify). This skill encodes 27.05.2026 Wolf-Forensik: a "verdict-Befüllungs-Bug" in `claude_assessments` table was reported (53 rows in 4 weeks, all parameter_suggestions populated, 0 verdicts populated). Root-cause turned out to be NOT a bug but a schema-use-case-mismatch — the active writer (strategic_review.py = Portfolio-Reflexion) literally cannot produce per-trade verdicts because its System-Prompt never asks Claude for them. A naive "fix the INSERT" would have produced wrong data; the actual fix was building a NEW per-signal-advisor pipeline.
---

# Schema-Use-Case-Mismatch Detection

## The Iron Law

> When a field is "always NULL" in a table that has active writers, the FIRST hypothesis must NOT be "writer-bug" — it must be **"writer's use-case doesn't include this field"**. Audit BEFORE fixing.

## Why this matters

The naive flow:
1. Observe: `SELECT verdict, COUNT(*) FROM claude_assessments WHERE verdict IS NULL` returns 53.
2. Conclude: "the writer forgot to set verdict, fix the INSERT".
3. Patch INSERT to include verdict.
4. Discover later: the writer's input (LLM-response) doesn't HAVE a verdict-field, so `result.get('verdict')` returns None → INSERT still inserts NULL → no progress, plus now you've burned 2 hours and may have introduced semantic mismatches.

The right flow:
1. Observe NULL-pattern.
2. Find ALL writers to that table.
3. For each writer, check: does its DATA-SOURCE actually contain this field?
4. If NO writer produces the field → root cause is NOT a writer-bug, it's a **missing use-case**. Solution is to ADD a new writer-path with the right semantics, not patch existing writers.

## The 4-Step Diagnosis Procedure

### Step 1 — Find ALL writers via grep, not just the "obvious" one

```bash
# Don't trust "the file that obviously writes to X" — grep widely
grep -rn "INSERT INTO <table>\|UPDATE <table>\|MERGE INTO <table>" \
    --include="*.py" --include="*.sql" --include="*.ts" .
```

Common surprises:
- **Legacy writer** still present in repo but rarely-/never-called (check call-graph + last commit-touch)
- **Migration scripts** that wrote once at deployment
- **Test fixtures** that populate the table (don't count, but easy to mis-attribute)
- **Cron/Scheduler-job** writers separate from request-path writers
- **Multiple writers same table** with different INSERT-column-lists (the smoking gun)

### Step 2 — For each ACTIVE writer, read its DATA-SOURCE

For each writer, find what produces the value it INSERTs. If the writer's source is:

- An **LLM-call** → read the System-Prompt. Does the prompt ask for the field? If not, the field cannot be produced — Use-Case-Mismatch.
- A **user-input form** → check the form schema. Does the form collect this field?
- A **DB-query upstream** → check the upstream query. Does it SELECT the field?
- An **API-response** → check the API-spec. Does the response include the field?

The pattern: trace the field BACKWARDS through the data-flow. If at any point the field is not produced/collected, the writer cannot magically synthesize it.

### Step 3 — Quantitative plausibility-check

Compute the expected vs observed row-count for each writer:
- E.g. "active cron is every 4h × 7d × 4w = 112 ticks, with 47% gate-pass = 53 rows" → matches observation → that's THE active writer
- If observed << expected from any single writer → multiple writers or upstream-filter dropping rows

This isolates which writer is responsible for which subset of rows, and confirms whether the "NULL-field-symptom" applies to the right writer's semantic.

### Step 4 — Reframe the question with user before coding

Once Steps 1-3 show "no active writer's use-case includes this field", the question changes from "fix the bug" to a 3-way Wolf-question:

| Reframe | Action |
|---|---|
| **E1**: Field SHOULD be populated by an additional new use-case → build a new writer-pipeline (no patch on existing) |
| **E2**: Field is legacy from old schema, not needed anymore → document and ignore (no code change) |
| **E3**: Both — existing portfolio-use-case OK, but also add per-trade-use-case → new pipeline + keep existing |

This reframe MUST happen with the user — Claude cannot decide E1/E2/E3 from code alone, because it depends on the user's product-intent.

## Anti-Patterns

- ❌ "Just add the field to the INSERT-list" without checking if data exists to set it
- ❌ "Add a default value in the INSERT" — masks the missing data, doesn't add value
- ❌ Assuming the FIRST writer found by grep is the only / active one
- ❌ Skipping the System-Prompt read for LLM-driven writers (Wolf 27.05.: System-Prompt of strategic_review.py never asked for verdict — invisible until read)
- ❌ Skipping quantitative plausibility — without it you can't tell which writer is causing the NULL-pattern
- ❌ Implementing E1 without explicit user-reframe → may build the wrong feature

## When You Don't Need This

- **First-implementation** of a feature: no historical writer to audit, just build it.
- **Schema-evolution** (column added but old code doesn't know about it): different problem — pure code-update needed in existing writer.
- **Permission errors / connection errors**: writer is trying to set the field but fails — different debugging.
- **Single-writer scenarios** where you've already confirmed the writer's data-source includes the field: just fix the obvious bug.

## Related Skills

- `pre-migration-data-verification` — sibling for the case where you ARE patching INSERTs after schema-changes
- `external-advisor-output-plausibility-audit` — sibling for auditing LLM-Output against expectation (heavily overlaps Step 2 here for LLM-writers)
- `superpowers:systematic-debugging` — parent: this skill is a specific Phase-1-pattern for "missing-data" symptoms

## Background: 27.05.2026 Real-World-Case

`claude_assessments` table in Wolf's ultimative-platform: 53 rows in 4 weeks, all `parameter_suggestions` populated, 0 `verdicts` populated.

**Naive diagnosis (which I almost shipped)**: "Strategic-Review-Pfad vergisst beim INSERT die Spalte `verdict`, fix the INSERT-Liste."

**Actual diagnosis (after Step 2)**: Strategic-Review's System-Prompt asks Claude for `risk_level`, `alerts`, `parameter_suggestions`, `summary` — but NEVER for `verdict`. The active writer is doing **Portfolio-Reflexion** (since 2026-05-12 refactor), not Per-Trade-Bewertung. The legacy writer (`legacy/claude/assessment_store.py`) DID have per-trade-verdict semantics but is unused.

**Wolf-reframe-question (E1/E2/E3)**: turned out E1 — Wolf actually wanted Per-Signal-Advisor that the system doesn't have. Fix was building a NEW `claude/per_signal/` sub-package, not patching strategic_review.py. 8 atomic commits + Code-Review + Deploy in same session.

→ Quantitatively saved estimated 2-3h of wasted patching, plus avoided semantic-mismatch bug where strategic_review.py would have insert-NULL-verdicts forever.

## Edge-Cases

- **Seltener Writer (nicht „tot, nicht aktiv")**: wenn Datei B nur manuell oder durch seltene Events getriggert wird (z.B. CLI-Tool), kann sie 0 Inserts in 4 Wochen produzieren ohne tot zu sein. Step 1 Audit muss zwischen „nie aufgerufen seit X" vs „aktiv aber seltener Trigger" unterscheiden — Differenzierung via `git log` + Cron-/Hook-Bindings, nicht nur via Commit-Alter.
- **Schema-Hygiene bei E1**: wenn die Lösung „neue Writer-Pipeline" ist (E1 oder E3), ZWEITE Tabelle empfohlen statt gemischte NULL-Semantik in einer Tabelle. Eine Tabelle mit `risk_level XOR verdict` als „je nach Writer-Type"-Konvention ist Anti-Pattern — Reader-Code muss raten welcher Writer dahinter steckt, JOINs werden semantisch unklar, Indexe ineffizient. Saubere Lösung: Tabelle per Use-Case (`portfolio_assessments` + `per_signal_assessments` getrennt).
- **Migrations-Schatten-Records**: nach DB-Migrations gibt es manchmal Records mit Null in Spalten die normalerweise gefüllt sind (siehe G3-B1 KW22-Forensik). Das ist KEIN Schema-Use-Case-Mismatch, sondern Migration-Artefakt — Diagnose über `closed_at`/`created_at`-Bulk-Pattern (alle Records mit identischer Mikrosekunde).

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-05-27 (PASS via Subagent-Pair-Dispatch, Reframe-Disziplin-Class)

- **RED-Subagent** (ohne Skill, Prompt: `claude_assessments.verdict` immer NULL, Datei A aktiv, Datei B legacy): **identifizierte das Mismatch verbal** („Schema-Use-Case-Mismatch") — aber lief TROTZDEM in die Patch-Falle. Schlug konkret Code-Aktionen vor: Tabellen-Split (Option 1) oder DROP COLUMN (Option 2). Markierte Annahmen ehrlich, aber wählte selbst aus statt User zu fragen — exakt das Anti-Pattern „selbst entscheiden statt reframen".

- **GREEN-Subagent** (mit Skill, identisches Prompt): explizit E1/E2/E3-Reframe an User zurückgegeben statt selbst zu wählen. Quantitativ-Plausibilität durchgerechnet (168 Ticks vs 53 Rows = 31% Gate-Pass-Rate). Explizit „Nicht tun: verdict in INSERT von Datei A aufnehmen — der LLM-Response enthält das Feld nicht" — direkt das Anti-Pattern markiert. Klare Risiko-Differenzierung (naive Fix = HOCH, E2 = NIEDRIG).

- **Refactor angewendet**: Sektion „Edge-Cases" hinzugefügt: seltener-Writer-Differenzierung, Schema-Hygiene-Empfehlung (zweite Tabelle bei E1), Migrations-Schatten-Records-Abgrenzung. Aus GREEN-Self-Reflection: „Schema-Hygiene bei E1 sollte expliziter sein. Aktuell nur implizit in Anti-Patterns."

### Höchster Skill-Wert: Reframe-Disziplin

Der entscheidende Test war NICHT „erkennt das Skill Mismatch?" sondern „verhindert das Skill, dass Claude die Entscheidung selbst trifft?". RED erkannte das Wort, GREEN erkannte das Pattern. Der Unterschied ist Code-Disziplin — bevor man Code schreibt, dem User die Produkt-Intent-Frage zurückgeben.

### Cycle-2-Backlog (Polish, nicht-blocking)

1. **Multi-Tabellen-Audit**: Pattern für „field NULL across MULTIPLE related tables" — z.B. `claude_assessments.verdict` UND `signal_outcomes.verdict` beide NULL → eigene Sektion „Cross-Table-Mismatch"
2. **Caching-Pipeline-Variant**: gilt das gleiche Pattern wenn der „Writer" ein Cache-Layer ist (Redis/Memcached) und das Backing-Store andere Semantik hat? Vermutlich ja, eigene Diskussion wert
3. **API-Schema-Mismatch**: REST/GraphQL-Endpoints die optional-fields zurückgeben aber Producer-Backend hat die Semantik nicht — Pattern-Transfer auf API-Layer
