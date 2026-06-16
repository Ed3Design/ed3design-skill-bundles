---
name: pre-migration-data-verification
description: |-
  Use before adding a constraint to an existing populated table (CREATE UNIQUE INDEX, ALTER ... ADD CHECK, ALTER ... NOT NULL, ADD FOREIGN KEY): query the existing data for would-be violations FIRST and write a cleanup-statement (UPDATE/DELETE) into the same migration block BEFORE the constraint-create. Skipping this → silent migration failure ("duplicate key" / "check violation" / "null value not allowed"), the entire migration rolls back and no error surfaces until the next deploy. Trigger on phrases like "add unique constraint to existing table", "CREATE UNIQUE INDEX migration", "ALTER TABLE ADD CHECK", "make column NOT NULL on existing data", "add foreign key to populated table", "migration silently failed". Do NOT load for first-time CREATE TABLE migrations (no existing data to violate), for column ADD migrations without constraints (defaults handle the gap), or for development DBs that can be wiped. PostgreSQL-focused; the pattern transfers to MySQL/SQLite/Oracle.
---

# pre-migration-data-verification

> ✅ **PROMOTED**: TDD pressure-test passed. The RED-Subagent wrote a blind `CREATE UNIQUE INDEX CONCURRENTLY` without a pre-check (honest self-critique at the end: named 5 gaps). The GREEN-Subagent delivered the full 4-step pattern: DO-block diagnostic SELECT → idempotent UPDATE-cleanup → CREATE INDEX IF NOT EXISTS → RAISE-EXCEPTION verify. Cycle-2 backlog: status-CHECK-constraint pre-check, UUID-PK variant, migration-runner specifics.

## Pattern (short form)

Before any migration that adds a constraint to existing data:
1. **SELECT** to count the existing violations
2. **Write an UPDATE/DELETE cleanup statement** (idempotent, with a WHERE clause that only addresses the violations)
3. **Write the constraint-CREATE statement**
4. Both statements in the SAME migration block in the correct order

If the cleanup step is missing, the constraint creation fails silently (Postgres rolls the transaction back, and the migration runner often sees it as a "no-op" because `IF NOT EXISTS` does not raise an error).

## Concrete example (a live encounter)

**Goal**: `CREATE UNIQUE INDEX uq_vtrades_open_per_direction ON virtual_trades (symbol, direction) WHERE status='open';`

**Pre-migration SELECT** (manually or as a doc block in the migration file):
```sql
SELECT symbol, direction, count(*) AS n
FROM virtual_trades
WHERE status = 'open'
GROUP BY symbol, direction
HAVING count(*) > 1;
```

Output:
```
  symbol  | direction | n
----------+-----------+----
 CL=F     | SHORT     | 12
 IBE.MC   | LONG      |  7
 HG=F     | LONG      |  5
 GC=F     | LONG      |  3
 EURUSD=X | SHORT     |  3
 NG=F     | SHORT     |  2
 NVDA     | SHORT     |  2
 PL=F     | SHORT     |  2
 PBR      | SHORT     |  2
(9 rows)
```

→ **38 violations across 9 clusters.** Without cleanup, the CREATE INDEX would silently roll back.

**Cleanup statement** (in the migration block BEFORE the CREATE INDEX):
```sql
-- Mark all but the oldest row per (symbol, direction) as 'superseded'.
-- Idempotent: runs multiple times without harm (second run finds 0 violations).
UPDATE virtual_trades vt
SET status = 'superseded',
    closed_at = COALESCE(vt.closed_at, NOW()),
    pnl_eur   = COALESCE(vt.pnl_eur, 0),
    exit_price = COALESCE(vt.exit_price, vt.entry_price)
WHERE vt.status = 'open'
  AND vt.id NOT IN (
      SELECT MIN(id) FROM virtual_trades
      WHERE status = 'open'
      GROUP BY symbol, direction
  )
  AND (vt.symbol, vt.direction) IN (
      SELECT symbol, direction FROM virtual_trades
      WHERE status = 'open'
      GROUP BY symbol, direction
      HAVING count(*) > 1
  );
```

**Only then:**
```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_vtrades_open_per_direction
ON virtual_trades (symbol, direction) WHERE status = 'open';
```

**Verification after migration:**
```sql
SELECT indexname FROM pg_indexes 
WHERE tablename='virtual_trades' AND indexname='uq_vtrades_open_per_direction';
SELECT count(*) AS n_dupes FROM (
  SELECT symbol, direction FROM virtual_trades 
  WHERE status='open' GROUP BY symbol, direction HAVING count(*)>1
) t;
```
Expectation: 1 row (index exists) + n_dupes=0.

## Quick-reference table

| Constraint type | Pre-migration SELECT | Cleanup statement |
|---|---|---|
| `UNIQUE INDEX` | `SELECT cols, count(*) FROM t GROUP BY cols HAVING count(*)>1` | UPDATE/DELETE the older dupes |
| `NOT NULL` | `SELECT count(*) FROM t WHERE col IS NULL` | UPDATE NULL rows with a default value |
| `CHECK` | `SELECT count(*) FROM t WHERE NOT (check-expr)` | UPDATE/DELETE the violating rows |
| `FOREIGN KEY` | `SELECT count(*) FROM t WHERE fk_col NOT IN (SELECT id FROM ref)` | DELETE orphan rows or INSERT backfill |
| `EXCLUDE USING gist` | constraint-specific range-overlap check | range-adjustment UPDATE |

## Status-value convention (for UPDATE cleanup)

When using UPDATE instead of DELETE → pick a new status value that is semantically unambiguous and does not distort statistics:

| Use case | Recommended value |
|---|---|
| "Superseded by a later entry" | `'superseded'` (neutral, not in win/loss stats) |
| "Data-cleanup artifact" | `'archived'` with `archived_at` column |
| "Soft delete" | an existing `'deleted'`/`'expired'`/`'inactive'` if present |
| If a status-CHECK constraint exists | be sure to pick an allowed value — otherwise a second cascade |

## Anti-Patterns

- ❌ "IF NOT EXISTS protects against errors" — IF NOT EXISTS only prevents the index-already-exists error, NOT the duplicate-key violation
- ❌ "If the migration fails, we leave it and try again tomorrow" — the migration runner commits partially, runs idempotently again, and you land in a limbo state
- ❌ "Constraint first, cleanup as a follow-up migration" — the FIRST migration fails, you never reach the second
- ❌ Cleanup with a hard DELETE (irreversible) when the data is history-relevant — prefer soft-delete via a status update
- ❌ Cleanup logic that breaks idempotency (e.g. SELECT with ROW_NUMBER without deterministic ordering) — a second run makes different cleanup decisions

## Idempotency check before deploy

Idempotency is mandatory — the migration runs multiple times (on re-deploy, container restart, etc.). If the cleanup logic is non-deterministic, the data states diverge between runs.

Test mentally:
- Run 1: Finds 38 violations. The UPDATE marks 29 rows as 'superseded'. End of run: 0 violations, constraint installed.
- Run 2: Finds 0 violations. The UPDATE WHERE clause matches nothing (`count(*) > 1` fails). CREATE INDEX IF NOT EXISTS no-op. End of run: state unchanged. ✓ idempotent.

If run 2 would do something run 1 did not → bug.

## Cross-references

- The "code review must become standard" maxim — a reviewer flagging missing pre-migration verification is a standard review lens
- `superpowers:test-driven-development` — migrations should ideally be TDD-tested (test = pre-cleanup state → apply → post-state)

## Real-world impact

`uq_vtrades_open_per_direction` migration:
- **First migration run without a cleanup statement** (before the insight): the migration runner reported "completed successfully", but the constraint was NOT in pg_indexes — silent rollback
- **Diagnosis**: 30 seconds to find manually (without the skill it would have taken much longer to dig out)
- **Fix**: SELECT the violations + UPDATE cleanup before CREATE INDEX → 29 rows set to 'superseded', index installed, 0 remaining violations
- **Lesson**: without pre-migration verification the constraint would have silently failed and "constraint installed" would have been reported without verification

The skill makes this step routine + provides the SELECT-statement templates per constraint type.

## Background: TDD log (bulletproofing log)

### Cycle 1 (PASS)

- **RED-Subagent** (without skill, virtual_trades UNIQUE-INDEX migration): Delivered `CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS` with BEGIN/COMMIT. No pre-check SQL. Honest self-critique at the end named 5 gaps: (1) no duplicate check, (2) no schema verification, (3) no status-value check, (4) no rollback test, (5) no existing-indexes check. The RED-Subagent recognized the gaps intellectually, but would not have applied them.
- **GREEN-Subagent** (with skill, same prompt): Full 4-step pattern implemented directly from the skill: DO-block diagnostic with RAISE NOTICE → idempotent UPDATE with `id NOT IN (MIN(id)...)` + `HAVING COUNT(*)>1` filter (taken 1:1 from the skill) → CREATE UNIQUE INDEX IF NOT EXISTS → DO-block verify with RAISE EXCEPTION on fail. Idempotency walked through mentally. Assumptions explicitly marked (`id` monotonic, `'superseded'` an allowed status value).
- **Verdict**: GREEN clearly. RED recognized the gaps but did not apply them — exactly the pattern value.

### Cycle-2 backlog (polish, non-blocking)

1. **Status-CHECK-constraint pre-check** as its own pre-check section: `SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='<table>'::regclass AND contype='c';`
2. **UUID-PK variant** as an alternative oldest-row strategy: with a UUID PK, instead of `MIN(id)` → `MIN(created_at)` with a tie-breaker
3. **Migration-runner specifics**: alembic vs flyway vs custom — transaction-wrap semantics differ
4. **Down-migration handling** for soft cleanup (not reversible without a backup)
