---
name: schema-use-case-mismatch-detection
description: |-
  Use when a user reports "field X is always NULL in table Y despite active code" or "data missing from a table that's actively being written to" — BEFORE jumping to "fix the bug, set the field". The Iron-Law: when a single DB-table has ≥2 writer-paths with different semantics (e.g. one writer is per-trade, another is per-portfolio, or legacy vs new pipeline), the field-NULL-symptom is often NOT a bug but a schema-use-case-mismatch — the active writer simply doesn't have the semantics to produce that field. A "fix" without this check would patch the writer to set a value-that-doesn't-exist-semantically, producing meaningless or wrong data in the DB. Trigger on phrases like "verdict is always NULL", "field X always missing", "this column is never populated", "53 rows all with NULL in field Y", "INSERT list incomplete", "data not appearing in table despite job running", "schema drift", "legacy table being used by new code", "two write-paths same table different semantics". Do NOT load for ALTER-TABLE-missing-column (different problem — schema-evolution), for permission-issues (writer can't access table), for connection-issues (writer crashes silently), or for first-implementation of a feature (no historical pattern to verify).

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

Once Steps 1-3 show "no active writer's use-case includes this field", the question changes from "fix the bug" to a 3-way user-question:

| Reframe | Action |
|---|---|
| **E1**: Field SHOULD be populated by an additional new use-case → build a new writer-pipeline (no patch on existing) |
| **E2**: Field is legacy from old schema, not needed anymore → document and ignore (no code change) |
| **E3**: Both — existing portfolio-use-case OK, but also add per-trade-use-case → new pipeline + keep existing |

This reframe MUST happen with the user — the assistant cannot decide E1/E2/E3 from code alone, because it depends on the user's product-intent.

## Anti-Patterns

- ❌ "Just add the field to the INSERT-list" without checking if data exists to set it
- ❌ "Add a default value in the INSERT" — masks the missing data, doesn't add value
- ❌ Assuming the FIRST writer found by grep is the only / active one
- ❌ Skipping the System-Prompt read for LLM-driven writers (real case: system prompt of strategic_review.py never asked for verdict — invisible until read)
- ❌ Skipping quantitative plausibility — without it you can't tell which writer is causing the NULL-pattern
- ❌ Implementing E1 without explicit user reframe → may build the wrong feature

## When You Don't Need This

- **First-implementation** of a feature: no historical writer to audit, just build it.
- **Schema-evolution** (column added but old code doesn't know about it): different problem — pure code-update needed in existing writer.
- **Permission errors / connection errors**: writer is trying to set the field but fails — different debugging.
- **Single-writer scenarios** where you've already confirmed the writer's data-source includes the field: just fix the obvious bug.

## Related Skills

- `pre-migration-data-verification` — sibling for the case where you ARE patching INSERTs after schema-changes
- `external-advisor-output-plausibility-audit` — sibling for auditing LLM-output against expectation (heavily overlaps Step 2 here for LLM-writers)
- `superpowers:systematic-debugging` — parent: this skill is a specific Phase-1-pattern for "missing-data" symptoms

## Background: Real-world case

`claude_assessments` table in your-app: 53 rows in 4 weeks, all `parameter_suggestions` populated, 0 `verdicts` populated.

**Naive diagnosis (which was almost shipped)**: "The strategic-review path forgets to include the `verdict` column in INSERT, fix the INSERT list."

**Actual diagnosis (after Step 2)**: Strategic-review's system prompt asks Claude for `risk_level`, `alerts`, `parameter_suggestions`, `summary` — but NEVER for `verdict`. The active writer is doing **portfolio reflection** (since a refactor), not per-trade assessment. The legacy writer (`legacy/claude/assessment_store.py`) DID have per-trade-verdict semantics but is unused.

**User reframe question (E1/E2/E3)**: turned out to be E1 — the user actually wanted a per-signal advisor that the system did not have. Fix was building a NEW `claude/per_signal/` sub-package, not patching strategic_review.py. 8 atomic commits + code review + deploy in same session.

→ Quantitatively saved estimated 2-3h of wasted patching, plus avoided semantic-mismatch bug where strategic_review.py would have inserted NULL verdicts forever.

## Edge-Cases

- **Rare writer (not "dead, not active")**: if file B is only triggered manually or by rare events (e.g. CLI tool), it can produce 0 inserts in 4 weeks without being dead. Step 1 audit must distinguish between "never called since X" vs "active but rare trigger" — differentiate via `git log` + cron/hook bindings, not just by commit age.
- **Schema hygiene at E1**: if the solution is "new writer pipeline" (E1 or E3), a SECOND table is recommended instead of mixed-NULL semantics in one table. A table with `risk_level XOR verdict` as "depends on writer type" convention is anti-pattern — reader code must guess which writer is behind it, JOINs become semantically unclear, indexes are inefficient. Clean solution: one table per use-case (`portfolio_assessments` + `per_signal_assessments` separately).
- **Migration shadow records**: after DB migrations there are sometimes records with NULL in columns that are normally populated. This is NOT a schema-use-case-mismatch, but a migration artifact — diagnose via `closed_at`/`created_at` bulk pattern (all records with identical microsecond).

## Background: TDD progress (Bulletproofing Log)

### Cycle 1 — PASS via Subagent-Pair-Dispatch, reframe-discipline class

- **RED subagent** (without skill, prompt: `claude_assessments.verdict` always NULL, file A active, file B legacy): **verbally identified the mismatch** ("schema-use-case-mismatch") — but STILL fell into the patch trap. Proposed concrete code actions: table split (Option 1) or DROP COLUMN (Option 2). Marked assumptions honestly but chose itself instead of asking the user — exactly the anti-pattern "decide oneself instead of reframing".

- **GREEN subagent** (with skill, identical prompt): explicitly returned the E1/E2/E3 reframe to the user instead of choosing itself. Calculated quantitative plausibility (168 ticks vs 53 rows = 31% gate-pass-rate). Explicitly stated "Do not: add verdict to the INSERT of file A — the LLM response does not contain the field" — directly flagged the anti-pattern. Clear risk differentiation (naive fix = HIGH, E2 = LOW).

- **Refactor applied**: Added "Edge-Cases" section: rare-writer differentiation, schema-hygiene recommendation (second table at E1), migration-shadow-record demarcation. From GREEN self-reflection: "Schema hygiene at E1 should be more explicit. Currently only implicit in anti-patterns."

### Highest skill value: reframe discipline

The decisive test was NOT "does the skill recognize the mismatch?" but "does the skill prevent the assistant from making the decision itself?". RED recognized the word, GREEN recognized the pattern. The difference is code discipline — before writing code, return the product-intent question to the user.

### Cycle-2 Backlog (Polish, non-blocking)

1. **Multi-table audit**: pattern for "field NULL across MULTIPLE related tables" — e.g. `claude_assessments.verdict` AND `signal_outcomes.verdict` both NULL → own section "Cross-Table-Mismatch"
2. **Caching pipeline variant**: does the same pattern apply when the "writer" is a cache layer (Redis/Memcached) and the backing store has different semantics? Presumably yes, worth its own discussion
3. **API schema mismatch**: REST/GraphQL endpoints that return optional fields but producer backend lacks the semantics — pattern transfer to the API layer
