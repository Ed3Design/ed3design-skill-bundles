---
name: schema-verify-via-information-schema
description: Use when about to write or execute an SQL-Query against a PostgreSQL/TimescaleDB-table whose exact schema (column names, types, deprecated-vs-active-variant) is not 100 % certain from current context — especially in forensic-debugging sessions where multiple tables have similar names (`ohlcv_1d` vs `ohlcv_1d_hist`, `users` vs `users_v2`, `orders` vs `orders_legacy`) or where column names have shifted over time (`open_price` → `ko_price_at_signal`, `bar_time` → `time`, `created` → `created_at`). The Iron-Law: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position` is the cheapest 30-second insurance against an entire bug-class (UndefinedColumn, false-positive-empty-result, wrong-table-queried). Trigger on phrases like "ich schreibe eine Query gegen Tabelle X", "warum kommt nichts zurück", "UndefinedColumn", "column X does not exist", "DB-Schema verifizieren", "verify schema first", "Schema-Drift", "Tabelle ist leer aber sollte gefüllt sein", "ich denke die Spalte heißt Y", "aus Erinnerung Query bauen", "vielleicht ist es Tabelle X oder Y", "deprecated table", "Suffix-Drift", "vor jeder forensischen Query". Do NOT load for ORM-mediated queries (SQLAlchemy / Django ORM handles schema-mapping declaratively — drift is caught at model-load), for first-time-schema-design (the table doesn't exist yet — use migration-design skill), for read-only catalog-queries that are themselves on `information_schema` / `pg_catalog`, or for connection-issues (can't connect to DB → schema-check fails first symptom). Encodes the 03.06.2026 ultimative-platform forensik-day: 3 separate schema-drifts caught in one day (open_price→ko_price_at_signal in Win-Rate-Analyse, bar_time→time in OHLCV-Query, ohlcv_1d-deprecated vs ohlcv_1d_hist-active in E-4-Diagnose), each would have produced a wrong-direction false-conclusion without the verify-first step.
---

# Schema-Verify via information_schema

## The Iron Law

> Before any forensic SELECT/UPDATE/DELETE against a table whose schema is not certain from current context: run **one** `information_schema.columns`-Query first. Cost: <100 ms + ~5 lines of code. Saved: typically 10-60 min of dead-end debugging or false-positive empty-result interpretations.

## Why this matters

The naive flow:
1. „Ich brauche die Win-Rate. Query gegen `virtual_trades` mit `open_price`."
2. `asyncpg.exceptions.UndefinedColumnError: column "open_price" does not exist`
3. „Ah, es heißt vielleicht `entry_price`?" — versuche, errors weiter
4. 2-3 Iterationen, 10-15 min weg

Oder schlimmer:
1. Query gegen `ohlcv_1d` für letzte 30 Tage.
2. **0 Rows zurück**.
3. „Die Daten-Pipeline ist tot, neue Hypothese aufbauen!"
4. 30 min Debugging Pipeline-Code.
5. Stellt sich heraus: `ohlcv_1d` ist deprecated, aktive Tabelle ist `ohlcv_1d_hist` — die hat 21 Bars/Symbol/30 Tage perfekt gefüllt.

Der echte Pfad:
1. **Erste Query immer**: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1 ORDER BY ordinal_position`
2. Schema-Output anschauen (10-30 Spalten lesen, 15 Sekunden)
3. Echte Query mit verifizierten Spaltennamen schreiben
4. Bei false-empty-Result: zusätzlich `SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%<base>%'` um Suffix-Varianten zu sehen

## The 3-Step Procedure

### Step 1 — Schema-Lookup als erste DB-Operation

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

Output anschauen. Dann erst die produktive Query bauen.

### Step 2 — Bei „leerem" Result: Tabellen-Geschwister suchen

Wenn eine erwartete Tabelle leer ist, bevor du auf Pipeline-Tod schließt:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name ILIKE '%my_table%'
ORDER BY table_name;
```

Heute aufgedeckt: `ohlcv_1d` (deprecated, leer) vs `ohlcv_1d_hist` (aktiv, voll). Naming-Suffix `_hist` suggeriert „historisch" → erste Intuition „nur Backtest". Falsch — es ist die aktive Daily-yfinance-Quelle.

### Step 3 — Bei „komische Werte" / „type-error": data_type prüfen

```sql
SELECT column_name, data_type, udt_name
FROM information_schema.columns
WHERE table_name=$1 AND column_name=$2;
```

Häufige Pitfalls die das deckt:
- `timestamp` vs `timestamptz`
- `numeric` vs `double precision` (Decimal-vs-float-Falle aus `asyncpg-live-vs-mock-shape`)
- `text` vs `varchar(N)` mit Length-Limit
- `jsonb` vs `json` vs `text` mit JSON-content
- Custom-Enum-Type vs `varchar`

## Concrete examples (03.06.2026 ultimative-platform)

| Symptom | Naive Hypothese | Wahrer Befund | Wenn Skill vorher gelaufen |
|---|---|---|---|
| `UndefinedColumn open_price` in v3_trades | „falscher Tabellen-Name?" | Spalte heißt `ko_price_at_signal` | 15s Schema-Read → richtige Spalte sofort |
| `UndefinedColumn bar_time` in ohlcv_1d | „Schema-Bug?" | Spalte heißt `time` | 15s Schema-Read |
| `ohlcv_1d` 0 Rows in 30d | „Daten-Pipeline tot!" | Tabelle ist deprecated, aktive ist `ohlcv_1d_hist` | Tables-Suffix-Search → richtige Tabelle |

## Anti-patterns

- ❌ **„Ich erinnere mich an die Spalten"** — Schema driftet über Wochen, Migrations sind unsichtbar
- ❌ **„Empty result → Pipeline tot"** — bevor Pipeline-Hypothese: Tabellen-Geschwister checken
- ❌ **Schema-Lookup nur bei Error** — der Bias ist umgekehrt: Lookup ist PREVENTION, nicht REACTION
- ❌ **`\d` in psql ohne Programmatic-Use** — beim Live-Debug-Loop verlierst du den Output beim nächsten Statement; programmatisch im fetch-Result behalten
- ❌ **Schema einmal lesen und für Stunden behalten** — bei langen Sessions kann eine parallele Migration laufen; bei Forensik immer fresh

## Quick template

```python
# Standard-Header für JEDE neue Forensik-Session gegen unbekannte Tabelle:
async def forensik_query(conn, table, **filters):
    # Step 1: Schema-Verify
    cols = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_name=$1 ORDER BY ordinal_position", table,
    )
    if not cols:
        # Step 2: Tabelle existiert nicht — Geschwister suchen
        siblings = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name ILIKE $1",
            f"%{table}%",
        )
        raise ValueError(
            f"Tabelle '{table}' nicht gefunden. Geschwister: "
            f"{[s['table_name'] for s in siblings]}"
        )
    schema = {c['column_name']: c['data_type'] for c in cols}
    print(f"[{table}] Schema: {list(schema.keys())}")
    # ... echte Query mit verifizierten Spalten
```

## Skill-Composition

- `superpowers:systematic-debugging` — runs BEFORE this skill for the wider „what is the bug" framing
- `asyncpg-live-vs-mock-shape` — runs AFTER this skill for the Mock-vs-Live-Type-Layer (separate concern: asyncpg-type-coercion)
- `schema-use-case-mismatch-detection` — runs IF schema is correct but NULL-pattern persists (different problem: semantic mismatch, not schema-drift)
- `decision-plan-hypothesis-matrix-DRAFT` — runs AROUND this skill: schema-verify is one of the „distinguishing metrics" before hypothesis-formulation

## Anti-skill — when this is NOT the right tool

| Symptom | Right tool instead |
|---|---|
| Field is consistently NULL despite active writer | `schema-use-case-mismatch-detection` |
| asyncpg Decimal vs float TypeErrors | `asyncpg-live-vs-mock-shape` |
| First-time-schema-design (table doesn't exist) | migration design skills (n/a in current catalog) |
| ORM-mediated query (SQLAlchemy / Django) | ORM model-introspection (different mechanism) |

## When-Built / Why-Built

Built 03.06.2026 after 3 separate schema-drifts caught in a single forensik-day on ultimative-platform:
1. **Win-Rate-Analyse** (morgens): `open_price` not in v3_trades — schema-drift seit Schema-Migration, correct column is `ko_price_at_signal`
2. **OHLCV-Coverage-Query** (nachmittags E-4): `bar_time` not in ohlcv_1d/_1h — correct column is `time`
3. **ohlcv_1d-Lookup** (nachmittags E-4): table is deprecated, active table is `ohlcv_1d_hist` (suffix `_hist` misleading)

Each instance would have cost 10-30 min of dead-end if discovered through trial-and-error. With `information_schema`-First: ~15 seconds total overhead, zero dead-ends.

Promotion-Trigger: ≥3 weitere Live-Anwendungen in nicht-Wolf-Sessions oder bei Wolf in anderen Projekten (z.B. pvista TimescaleDB).
