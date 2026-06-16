---
name: asyncpg-live-vs-mock-shape
description: Use when writing pytest mocks for asyncpg-backed endpoints where the column type causes mock-vs-live divergence (SUM/COUNT/AVG → Decimal; JSONB → str; UUID → UUID-object; INET → str). asyncpg returns raw PG-types that don't match naive intuition — mocks with the "natural" dict/int/float pass shape-tests but the real DB-call fails live. Trigger on phrases like "asyncpg mock test", "asyncpg JSONB mock", "asyncpg returns string for JSONB", "TypeError Decimal float", "AttributeError str object no attribute keys", "mock-and-live diverge for asyncpg". Do NOT load for psycopg-2-based tests (different driver, auto-coerces JSONB), for SQLAlchemy ORM tests (the ORM coerces types), or for asyncpg connections with `set_type_codec('jsonb', ...)` registered (the codec handles conversion).
---

# asyncpg-live-vs-mock-shape

> ✅ **PROMOTED**: Rename + expansion of the previously-promoted `asyncpg-decimal-test-shape` skill. TDD pressure-test Cycle 2 (JSONB extension) PASS. The RED-Subagent used a `dict` mock and flagged the codec risk heuristically. The GREEN-Subagent (with skill) used a `json.dumps(...)` str-mock correctly and delivered 2-layer defense (defensive json.loads + set_type_codec). This skill prevents the "green-test-red-production" class of bugs for Decimal aggregates (Class A) AND JSONB/UUID/INET types (Classes B-E). Auto-discoverable.

## Overview

asyncpg returns PostgreSQL types as Python types. The mappings are often different from what naive mock intuition expects:

| PG-Type | naive mock | asyncpg-live | bug class |
|---|---|---|---|
| `numeric` / `bigint` aggregate | `int` / `float` | **`Decimal`** | `TypeError` Decimal-vs-float |
| `jsonb` / `json` | `dict` | **`str`** (RAW JSON text) | `TypeError` str has no attribute keys / `KeyError` |
| `uuid` | `str` | **`uuid.UUID`** | comparison or lookup failures |
| `inet` / `cidr` | some tools expect `str` | **`ipaddress.IPv4Address`** / `IPv6Address` | attribute / serialization fails |
| `timestamp` without TZ | `datetime` | **`datetime` naive** | `TypeError` aware-vs-naive comparison |
| `interval` | `timedelta` | `datetime.timedelta` ✓ | usually ok |
| `bytea` | `bytes` | `bytes` ✓ | usually ok |

Mock test green, live production code red — the class of bugs this skill prevents.

## Class A — Numeric Aggregates (Decimal)

PostgreSQL aggregates (`SUM`, `COUNT`, `AVG`, `STDDEV`) on numeric or bigint columns come back via asyncpg as `decimal.Decimal`, NOT as `int` or `float`.

Typical symptom:
```
TypeError: unsupported operand type(s) for /: 'float' and 'decimal.Decimal'
```

### Quick lookup PG aggregate → asyncpg Python type

| PG aggregate | PG result type | asyncpg Python type |
|---|---|---|
| `SUM(integer)` | `bigint` | `Decimal` |
| `SUM(bigint)` | `numeric` | `Decimal` |
| `SUM(numeric)` | `numeric` | `Decimal` |
| `SUM(double precision)` | `double precision` | `float` |
| `COUNT(*)` | `bigint` | `Decimal` |
| `AVG(numeric)` | `numeric` | `Decimal` |
| `AVG(integer)` | `numeric` | `Decimal` |
| `STDDEV_POP(numeric)` | `numeric` | `Decimal` |

### Mock pattern

Wrong (passes shape-test, fails live):
```python
return {
    "day_pnl_eur": 50.0,    # float — wrong, real is Decimal
    "r30_count":  5,         # int   — wrong, real is Decimal
    "r30_wins":   3,         # int   — wrong, real is Decimal
}
```

Correct:
```python
from decimal import Decimal
return {
    "day_pnl_eur": Decimal("50.0"),
    "r30_count":  Decimal(5),
    "r30_wins":   Decimal(3),
}
```

### Defensive code layer (production)

```python
r30_count = float(r["r30_count"] or 0)
r30_wins  = float(r["r30_wins"]  or 0)
wr30 = (r30_wins / r30_count) * 100 if r30_count > 0 else None
```

The skill recommends **both**: Decimal in the mock AND float-cast in the code.

## Class B — JSONB / JSON (str, NOT dict)

`SELECT some_jsonb_column FROM ...` with asyncpg returns the raw JSON text as **`str`**, not as a parsed Python `dict`. Symptoms vary by access pattern:

| Production code pattern | Live error |
|---|---|
| `row["report"]["confidence"]` (string-keyed lookup) | `TypeError: string indices must be integers` |
| `row["report"][0]` (int-indexing — code expected list) | nothing short — returns a single character `"{"` |
| `for k in row["report"]:` (iter over dict) | iterates over characters of the JSON string, not over keys |
| `row["report"].keys()` | `AttributeError: 'str' object has no attribute 'keys'` |
| `**row["report"]` (unpack as kwargs) | `TypeError: argument of type 'str' is not iterable as mapping` |

### SQL example

```sql
-- ml_models has report JSONB; query returns raw JSON string
SELECT id, report FROM ml_models WHERE active = true;
```

```python
row = await conn.fetchrow("SELECT report FROM ml_models WHERE id = $1", model_id)
report = row["report"]
# ⚠️ report is str, not dict!
# report["confidence"]   → TypeError: string indices must be integers
```

### Mock pattern for JSONB

Wrong (passes shape-test, fails live):
```python
return {
    "id": 713,
    "report": {"confidence": 0.75, "verdict": "accept"},   # ← dict, real is str!
}
```

Correct:
```python
import json
return {
    "id": 713,
    "report": json.dumps({"confidence": 0.75, "verdict": "accept"}),  # ← str
}
```

### Defensive code layer (production)

Two options — both good, depending on codebase convention:

**Option 1 — Defensive json.loads per call**:
```python
raw = row["report"]
report = json.loads(raw) if isinstance(raw, str) else raw  # handles already-dict (e.g. test mock that uses dict)
confidence = report["confidence"]
```

**Option 2 — set_type_codec at the pool-init level** (clean structural solution):
```python
async def init_pool():
    pool = await asyncpg.create_pool(...)
    async with pool.acquire() as conn:
        await conn.set_type_codec(
            "jsonb",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
        await conn.set_type_codec(
            "json",
            encoder=json.dumps,
            decoder=json.loads,
            schema="pg_catalog",
        )
    return pool
```

⚠️ **With set_type_codec**: the mock then also returns `dict` and that is consistent. BUT: check ALL places where the pool is used (some tests may use a separate pool without the codec → divergent mock shape depending on test setup).

### When it occurs

- **Live connection via `asyncpg.connect()` or `asyncpg.create_pool()` without JSONB codec** → str
- **With `set_type_codec(jsonb, decoder=json.loads)`** → dict
- **psycopg2** with `json.loads` cursor → dict (different behavior)

### Example

An ML-evaluator endpoint read `ml_models.report` (JSONB) and tried `report["confidence"]` directly — `TypeError: string indices must be integers`. The mock test was green with a `dict` mock. Fix in two steps:
1. `set_type_codec` at pool-init (structurally clean)
2. Defensive `json.loads` in the specific function (belt-and-suspenders)

## Class C — UUID

`SELECT id FROM x` with an `id uuid` column returns a `uuid.UUID` object, not `str`. Symptoms:

```python
# mock returns str: "abc-123-..."
# live returns UUID("abc-123-...")
row["id"] == "abc-123-..."   # ← False on live (UUID != str comparison)
```

### Mock pattern for UUID

Wrong:
```python
return {"id": "550e8400-e29b-41d4-a716-446655440000", ...}
```

Correct:
```python
import uuid
return {"id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"), ...}
```

### Defensive code

```python
str(row["id"])   # works for UUID and for str
# or
row["id"] if isinstance(row["id"], str) else str(row["id"])
```

## Class D — INET / CIDR

`SELECT ip FROM x` with an `ip inet` column returns an `ipaddress.IPv4Address` / `IPv6Address` / `IPv4Network` / `IPv6Network` object, not `str`. Symptom: JSON serialization fails (object not serializable).

### Mock pattern for INET

Wrong:
```python
return {"client_ip": "192.168.1.1"}
```

Correct:
```python
import ipaddress
return {"client_ip": ipaddress.IPv4Address("192.168.1.1")}
```

### Defensive code

```python
str(row["client_ip"])  # works for IPv4Address and for str
```

## Class E — Timestamps (Aware vs Naive)

`timestamp without time zone` → naive `datetime`. `timestamptz` → aware `datetime` with tzinfo. Comparing aware vs naive raises `TypeError`.

### Mock pattern

When the DB column is `timestamptz`:
```python
from datetime import datetime, timezone
return {"created_at": datetime(2026, 5, 29, 8, 0, tzinfo=timezone.utc)}
```

When the DB column is `timestamp` (without TZ):
```python
return {"created_at": datetime(2026, 5, 29, 8, 0)}   # NAIVE
```

Production code SHOULD typically keep all timestamps aware — if the DB column is `timestamp` and the code does aware comparison → a DB schema fix is cleaner than a defensive workaround.

## When to apply — trigger table

| Trigger | Apply? |
|---|---|
| asyncpg + SQL with `SUM()`, `COUNT()`, `AVG()`, `STDDEV()` over numeric/bigint | ✅ Class A |
| asyncpg + SELECT with JSONB/JSON column | ✅ Class B |
| asyncpg + SELECT with uuid column | ✅ Class C |
| asyncpg + SELECT with inet/cidr column | ✅ Class D |
| asyncpg + timestamp(tz) column | ✅ Class E |
| Test uses `AsyncMock`/`MagicMock` for `conn.fetchrow`/`conn.fetch` | ✅ yes (all classes) |
| Single-column SELECT without aggregate, basic types (text/int4) | ❌ no — type is as declared |
| SQLAlchemy ORM (ORM coerces) | ❌ no — ORM does .scalar() / TypeDecorator |
| psycopg2 with `RealDictCursor` | ⚠️ partially — depends on cursor class |
| asyncpg pool with set_type_codec for JSONB | ⚠️ Class B mock can then be dict — codec does the conversion |

## Anti-Patterns

- ❌ Test with `int`/`float` mocks → green pytest, red live (Class A)
- ❌ Test with `dict` mock for JSONB column → green pytest, `string indices must be integers` live (Class B)
- ❌ Test with `str` mock for UUID column → green pytest, comparison fail live (Class C)
- ❌ Assuming "asyncpg already coerces to whatever fits" — no, raw driver, no ORM
- ❌ set_type_codec inconsistent across pools (some test pools have it, others don't) → different mock shape depending on pool-init

## Defense-in-depth recommendation

| Layer | What |
|---|---|
| Test mock | EXACTLY the Python types asyncpg returns live (Decimal, str-JSONB, UUID-object, IPv4-object) |
| Production code | Defensive casts (`float()`, `json.loads(x) if isinstance(x, str) else x`, `str()`) |
| Pool-init | `set_type_codec` for structured types (JSONB) — consistent across ALL pools |
| Integration tests | at least 1 real DB roundtrip test per type class |

## Cross-references

- The "code review must become standard" maxim — reviewers did not find the Decimal-mock bug + JSONB-mock bug locally, because the mocks were green
- `superpowers:test-driven-development` — base pattern that this skill is only a test-shape refinement of

## Background: TDD log (bulletproofing log)

### Cycle 1 (PASS) — Decimal-only skill

- **RED-Subagent** (without skill): used `int` for COUNT, `float` for SUM/AVG. Flagged uncertainty explicitly. Test would be green, live would be `TypeError`.
- **GREEN-Subagent** (with skill): used `Decimal` for all aggregates + type assertions + defensive-coercion note. Skill self-reflection called the PG→asyncpg lookup table a "killer feature".
- **Verdict**: PROMOTE Decimal-only skill. Skill delivers demonstrable bug avoidance.

### Cycle 2 (PASS — JSONB extension)

**Scenario**: A FastAPI endpoint loads `ml_models.report` (JSONB) and does `row["report"]["confidence"]` directly. Pytest-mock task — RED without skill / GREEN with skill.

- **RED-Subagent** (without skill): used `dict` for the `report` mock ("JSONB is decoded as `dict` by asyncpg by default"). Self-reflection was unusually honest — explicitly flagged: "If the pool has not registered a JSON codec, `report` comes back as `str`, and `row["report"]["confidence"]` throws `TypeError`. That is a real live-bug risk that my mock test masks." RED recognized the bug HEURISTICALLY, but would not have corrected the mock without pool-setup verification.
- **GREEN-Subagent** (with skill): used `json.dumps(report_payload)` directly, Class-B table as a quick lookup, both defense-in-depth options documented (defensive json.loads + set_type_codec), production-code fix provided as a comment. Skill self-reflection called the Class-B table "killer content". GREEN code was safe + traceable where RED code was "plausible but with latent risk".
- **Verdict**: PROMOTE. Skill prevents exactly the JSONB bug class. RED's self-honesty showed that even a careful engineer recognizes-but-does-not-fix the bug without an external reference.

**Refactor applied (inline before promote)**:
- Class-B symptom table: 5 access patterns → exact live errors (previously a terse 3-line list). GREEN self-reflection feedback on symptom clarity incorporated.

### Cycle-2 backlog (polish, non-blocking after PROMOTE)

1. **conn.fetch() (list of rows) example** in addition to fetchrow — more frequent with window functions
2. **`AsyncMock` + `pool.acquire()` context-manager plumbing**: separate skill candidate `asyncpg-pool-mock-plumbing` (GREEN suggestion) — orthogonal to the type-shape question, a recurring stumbling block
3. **Empty-set behavior column** for the Class-A lookup table: `COUNT(*) → Decimal(0)`, `SUM/AVG → None` for empty result set
4. **set_type_codec pattern library**: document the repo-wide convention — when codec (all pools consistent), when defensive
5. **Class F (arrays)**: `text[]`/`int[]` → `list[str]`/`list[int]` (usually ok but check the dimension assumption)
6. **Class G (empty JSONB / NULL)**: `report IS NULL` → asyncpg returns `None`, defensive `or {}` pattern
7. **`pytest.approx` for Decimal comparisons** note — not needed if production code finally casts to float

## Real-world impact

**Class A**: An equity-curve endpoint mock test with int/float → 4/4 green; live deploy → 500 Internal Server Error in 5s. Skill would catch it locally.

**Class B**: An ML-evaluator endpoint mock test with dict → 32 tests green; live run → `string indices must be integers`. Fix in 2 steps: set_type_codec + defensive json.loads. **Both hits in one session** triggered this skill extension.

Skill would catch both bug classes locally without a live roundtrip.
