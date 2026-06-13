---
name: schema-verify-via-information-schema
description: Use when about to write or execute an SQL-Query against a PostgreSQL/TimescaleDB-table whose exact schema (column names, types, deprecated-vs-active-variant) is not 100 % certain from current context — especially in forensic-debugging sessions where multiple tables have similar names (`ohlcv_1d` vs `ohlcv_1d_hist`, `users` vs `users_v2`, `orders` vs `orders_legacy`) or where column names have shifted over time (`open_price` → `ko_price_at_signal`, `bar_time` → `time`, `created` → `created_at`). The Iron-Law: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position` is the cheapest 30-second insurance against an entire bug-class (UndefinedColumn, false-positive-empty-result, wrong-table-queried). Trigger on phrases like "writing a query against table X", "why is nothing coming back", "UndefinedColumn", "column X does not exist", "verify DB schema", "verify schema first", "schema drift", "table is empty but should be populated", "I think the column is called Y", "build query from memory", "maybe it's table X or Y", "deprecated table", "suffix drift", "before any forensic query". Do NOT load for ORM-mediated queries (SQLAlchemy / Django ORM handles schema-mapping declaratively — drift is caught at model-load), for first-time-schema-design (the table doesn't exist yet — use migration-design skill), for read-only catalog-queries that are themselves on `information_schema` / `pg_catalog`, or for connection-issues (can't connect to DB → schema-check fails first symptom). Encodes a forensic-day where 3 separate schema-drifts were caught: open_price→ko_price_at_signal in win-rate analysis, bar_time→time in OHLCV query, ohlcv_1d-deprecated vs ohlcv_1d_hist-active in diagnosis, each would have produced a wrong-direction false-conclusion without the verify-first step.
---

# Schema-Verify via information_schema

## The Iron Law

> Before any forensic SELECT/UPDATE/DELETE against a table whose schema is not certain from current context: run **one** `information_schema.columns` query first. Cost: <100 ms + ~5 lines of code. Saved: typically 10-60 min of dead-end debugging or false-positive empty-result interpretations.

## Why this matters

The naive flow:
1. "I need the win rate. Query against `virtual_trades` with `open_price`."
2. `asyncpg.exceptions.UndefinedColumnError: column "open_price" does not exist`
3. "Ah, maybe it's called `entry_price`?" — retry, errors continue
4. 2-3 iterations, 10-15 min gone

Or worse:
1. Query against `ohlcv_1d` for last 30 days.
2. **0 Rows returned**.
3. "The data pipeline is dead, build a new hypothesis!"
4. 30 min debugging pipeline code.
5. Turns out: `ohlcv_1d` is deprecated, the active table is `ohlcv_1d_hist` — it has 21 bars/symbol/30 days perfectly populated.

The real path:
1. **First query always**: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position`
2. Look at the schema output (read 10-30 columns, 15 seconds)
3. Write the real query with verified column names
4. On false-empty-result: additionally `SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%<base>%'` to see suffix variants

## The 3-Step Procedure

### Step 1 — Schema lookup as first DB operation

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'my_table'
ORDER BY ordinal_position;
```

In Python/asyncpg:
```python
cols = await conn.fetch(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name=$1 ORDER BY ordinal_position",
    table_name,
)
for c in cols:
    print(f"  {c['column_name']:30s} {c['data_type']}")
```

Look at the output. THEN build the production query.

### Step 2 — On "empty" result: search for sibling tables

If an expected table is empty, before concluding pipeline death:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name ILIKE '%my_table%'
ORDER BY table_name;
```

Discovered today: `ohlcv_1d` (deprecated, empty) vs `ohlcv_1d_hist` (active, full). Naming suffix `_hist` suggests "historical" → first intuition "backtest only". Wrong — it is the active daily yfinance source.

### Step 3 — On "weird values" / type-error: check data_type

```sql
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name=$1 AND column_name=$2;
```

Common pitfalls this catches:
- `timestamp` vs `timestamptz`
- `numeric` vs `double precision` (Decimal-vs-float trap from `asyncpg-live-vs-mock-shape`)
- `text` vs `varchar(N)` with length limit
- `jsonb` vs `json` vs `text` with JSON content
- Custom-Enum-Type vs `varchar`

## Concrete examples (your-app forensic day)

| Symptom | Naive hypothesis | True finding | If skill had run first |
|---|---|---|---|
| `UndefinedColumn open_price` in v3_trades | "wrong table name?" | column is called `ko_price_at_signal` | 15s schema read → right column immediately |
| `UndefinedColumn bar_time` in ohlcv_1d | "schema bug?" | column is called `time` | 15s schema read |
| `ohlcv_1d` 0 rows in 30d | "data pipeline dead!" | table is deprecated, active is `ohlcv_1d_hist` | tables-suffix-search → right table |

## Anti-patterns

- ❌ **"I remember the columns"** — schema drifts over weeks, migrations are invisible
- ❌ **"Empty result → pipeline dead"** — before pipeline hypothesis: check sibling tables
- ❌ **Schema lookup only on error** — the bias is reversed: lookup is PREVENTION, not REACTION
- ❌ **`\d` in psql without programmatic use** — in live debug loop you lose the output on the next statement; keep it programmatically in the fetch result
- ❌ **Read schema once and keep it for hours** — in long sessions a parallel migration may run; for forensics always fresh

## Quick template

```python
# Standard header for EVERY new forensic session against unknown table:
async def forensic_query(conn, table, **filters):
    # Step 1: Schema verify
    cols = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name=$1 ORDER BY ordinal_position", table,
    )
    if not cols:
        # Step 2: Table does not exist — find siblings
        siblings = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name ILIKE $1",
            f"%{table}%",
        )
        raise ValueError(
            f"Table '{table}' not found. Siblings: "
            f"{[s['table_name'] for s in siblings]}"
        )
    schema = {c['column_name']: c['data_type'] for c in cols}
    print(f"[{table}] Schema: {list(schema.keys())}")
    # ... real query with verified columns
```

## Skill composition

- `superpowers:systematic-debugging` — runs BEFORE this skill for the wider "what is the bug" framing
- `asyncpg-live-vs-mock-shape` — runs AFTER this skill for the Mock-vs-Live-Type-Layer (separate concern: asyncpg-type-coercion)
- `schema-use-case-mismatch-detection` — runs IF schema is correct but NULL-pattern persists (different problem: semantic mismatch, not schema drift)
- `decision-plan-hypothesis-matrix-DRAFT` — runs AROUND this skill: schema-verify is one of the "distinguishing metrics" before hypothesis formulation

## Anti-skill — when this is NOT the right tool

| Symptom | Right tool instead |
|---|---|
| Field is consistently NULL despite active writer | `schema-use-case-mismatch-detection` |
| asyncpg Decimal vs float TypeErrors | `asyncpg-live-vs-mock-shape` |
| First-time-schema-design (table doesn't exist) | migration design skills (n/a in current catalog) |
| ORM-mediated query (SQLAlchemy / Django) | ORM model introspection (different mechanism) |

## When-Built / Why-Built

Built after 3 separate schema-drifts caught in a single forensic day on a production domain:
1. **Win-rate analysis** (morning): `open_price` not in v3_trades — schema drift since schema migration, correct column is `ko_price_at_signal`
2. **OHLCV-coverage query** (afternoon): `bar_time` not in ohlcv_1d/_1h — correct column is `time`
3. **ohlcv_1d lookup** (afternoon): table is deprecated, active table is `ohlcv_1d_hist` (suffix `_hist` misleading)

Each instance would have cost 10-30 min of dead-end if discovered through trial-and-error. With `information_schema`-First: ~15 seconds total overhead, zero dead-ends.

Promotion trigger: ≥3 further live applications in non-work sessions or in other projects (e.g. TimescaleDB-based monitoring).
