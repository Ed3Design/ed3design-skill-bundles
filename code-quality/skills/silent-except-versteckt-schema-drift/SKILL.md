---
name: silent-except-versteckt-schema-drift
description: |-
  Use when reviewing or writing Python code with `try`/`except Exception:` clauses around SQL queries (asyncpg.connect/conn.fetch/conn.execute, psycopg2, sqlalchemy, sqlite3, or any DB-driver call) where the except-branch either (a) silently returns an empty collection (`signals = []`, `ticks = []`, `rows = {}`, `data = None`), (b) re-renders the UI with the empty state ("No active signals", "No data today", "Loading..."), or (c) catches with a bare or overly-broad type — without `logger.exception()` / `log.error()` / re-raise. The danger: a schema-drift bug (`column "X" does not exist`, FK-target-rename, table-renamed-in-migration, ORM-model-out-of-sync) AND a legitimate empty-result state look IDENTICAL to the user. A dashboard panel that says "No signals today" silently means EITHER (1) there genuinely are no signals OR (2) the SQL crashed and was swallowed — without a log entry, you cannot tell which. Real evidence from a schema-drift audit: `api/routes/dashboard/modules/{signals,timeline}.py` had `except Exception: signals = []` / `except Exception: ticks = []` around SELECT queries on `opportunities.yf_symbol` (column doesn't exist — opportunities has `symbol`). Result: dashboard's "Active Signals" card showed `(0)` for unknown duration while DB had 2 real open signals. Trader logs in 24h window: **0 hits** on "column does not exist" — silent-except clauses fired BEFORE any log entry. Would never be noticed without code audit. Trigger phrases like "silent except with schema drift", "dashboard shows empty but DB has data", "why don't I see any signals", "except Exception: signals = []", "dashboard card permanently empty", "code swallows DB error", "silent failure with DB query". Do NOT load for non-DB silent-except (network calls, file-IO — different concern; use general silent-failure-hunter), for catch-and-re-raise patterns (already correct), or for narrow except-clauses that catch specific exception types like `asyncpg.PostgresError` AND log them (probably fine, audit case-by-case).
---

# Silent-Except hides schema drift

> ⚠️ **DRAFT** — needs TDD promotion (RED: deploy code with silent-except + schema-drift, observe user sees "empty"; GREEN: deploy with logger.exception, observe drift visible in log). See `skill-tdd-promotion-workflow`.

## Overview

`try: ... except Exception: data = []` is tempting defensive — the user sees the UI state and no 500 error. But for DB-driven endpoints this pattern makes **schema-drift bugs invisible**:

- Column renamed (migration) → code references old name → `column "X" does not exist` → silent-except → user sees "empty"
- Table renamed → `relation does not exist` → silent-except → user sees "empty"
- FK target moved → `foreign key constraint failure` → silent-except → user sees "empty"
- Type mismatch (TEXT vs JSONB after migration) → `column cannot be cast` → silent-except → user sees "empty"

When the UI state doesn't distinguish between "really empty" and "code broken", the bug goes latent in production — days, weeks, sometimes months — without trigger for attention.

**Real experience**: dashboard's "Active Signals" card showed `(0)` while DB had 2 real signals. 24h trader logs: **0 hits on "column does not exist"**. Drift was completely hidden from the user.

## When to use (audit trigger)

You're reviewing code with:
- `try:` / `except Exception:` (or bare `except:`)
- inside the try: some DB-driver call (`asyncpg.connect`, `conn.fetch`, `conn.execute`, `psycopg2.connect`, `engine.execute`, etc.)
- in the except: assignment `var = []` / `var = {}` / `var = None` OR a UI render with default state
- NO `logger.exception()`, NO `log.error()`, NO re-raise

You're diagnosing a symptom:
- "Dashboard card / tab / panel shows PERMANENTLY empty/null, but DB has data"
- "Endpoint returns 200 with empty body instead of error"
- "We have no log for the bug, but the UI clearly behaves wrong"
- "User complaint 'X doesn't work', but logs are empty"

## When NOT to use

- **Non-DB silent-except** (file-IO, HTTP calls, JSON parse) — different bug class, different heuristic
- **Specific exception types**: `except asyncpg.UndefinedColumnError:` OR `except (psycopg2.errors.UndefinedColumn, ...):` — correctly narrows the problem, less dangerous. Still audit whether the except class is too narrow/broad.
- **Catch-and-re-raise**: `except Exception as e: log.exception(...); raise` — already correct, no intervention needed
- **Tests / Mocks**: `except Exception: pass` in test setup is judged differently

## The 4-Step Audit Pattern

### Step 1 — Find candidates

Grep over the codebase:
```bash
# Direct pattern
rg -n 'except Exception:\s*\n\s+\w+\s*=\s*\[\]' --type py
rg -n 'except.*:\s*\n\s+\w+\s*=\s*None' --type py
# With DB call above
rg -nB 10 'except Exception:' --type py | grep -B 10 -E 'fetch|execute|connect|query'
```

### Step 2 — Verify the DB call would actually drift

Per hit: identify the SQL statement and check against the REAL schema:
```bash
# Pull schema reality from production DB
docker exec mydb psql -U <user> -d <db> -tA \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'X' ORDER BY ordinal_position"
```
Match every column in the code SQL against the real columns.

### Step 3 — Live-verify by hitting the endpoint

The `frontend-ui-self-verify-before-user-demo` skill comes into play here:
```bash
curl -sf 'http://app-host/endpoint' | head -30
# If "No data" / empty list despite expected DB data → bug confirmed
```

Or via Chrome DevTools MCP / Playwright directly in the browser render path.

### Step 4 — Fix the except clause

Don't remove the try — instrument the except:

```python
# ❌ WRONG
try:
    rows = await conn.fetch("SELECT o.yf_symbol FROM opportunities o WHERE o.status = 'open'")
    signals = [_row_to_signal(r) for r in rows]
except Exception:
    signals = []  # User sees "empty", drift invisible

# ✅ CORRECT
import logging
log = logging.getLogger(__name__)

try:
    rows = await conn.fetch("SELECT o.symbol AS yf_symbol FROM opportunities o WHERE o.status = 'open'")
    signals = [_row_to_signal(r) for r in rows]
except Exception:
    log.exception("active_signals query failed — returning empty list")
    signals = []
```

`log.exception()` (instead of `log.error()`) is important: it includes the traceback automatically. With `log.error("X")` you only see "X failed", not WHY.

## Why `log.exception` not raise?

In UI endpoints (dashboard cards, side panels, status tiles) the UX requirement is typically "card loads poorly > whole page crashes". So default state (`signals = []`) is UX-correct, but:

- **Log layer MUST see it failed** → `log.exception`
- **Optional**: distinguish second UI state ("Data could not be loaded") instead of just "empty"

For more critical calls (trade INSERT, money move): do NOT silently catch — re-raise with HTTP status code would be more correct.

## Anti-Patterns

| Pattern | Why bad |
|---|---|
| `except Exception: pass` | doesn't even return a default variable — NameError downstream |
| `except: signals = []` | bare except catches `KeyboardInterrupt`, `SystemExit` too — worst case |
| `except Exception: signals = []; print(traceback)` | print goes to stdout, not logging aggregator — invisible with container/systemd |
| `except Exception as e: log.error(f"failed: {e}")` | only message, no traceback — file:line of drift not identifiable |
| `try: rows = await conn.fetch(...); except: rows = await conn.fetch(...)` retry | wrong — drift won't resolve, loop hangs |

## Detection indicators in audit practice

These three heuristics indicate drift with high probability:

1. **UI says "(0)" or "No X" constantly** over days/weeks despite use-case traffic should be there
2. **Logs show 0 errors** in an endpoint despite high call frequency (no 200/500 would be normal — all 200 is suspicious)
3. **`docker logs ... | grep -i "column.*not exist"` = 0** despite likely migration history

## Cost of Skipping (real)

- **5 schema-drift findings** in dashboard/modules (signals.py, timeline.py, portfolio.py)
- **2 of them silent**: `except Exception: signals = []` and `except Exception: ticks = []`
- **Unknown drift duration**: dashboard was probably seen for weeks with empty cards without trigger for investigation
- **Direct outcome-visibility loss**

## Promotion Checklist (DRAFT → GA)

- [ ] RED subagent: deploy code with `except Exception: X = []` + schema-drift in SELECT — verify user sees "empty", logs show 0 errors
- [ ] GREEN subagent: same code with `log.exception(...)` — verify user sees "empty" AND log contains drift traceback
- [ ] Edge case: specific `except asyncpg.UndefinedColumnError` — confirm skill correctly classifies the pattern
- [ ] Cross-reference with `superpowers:silent-failure-hunter` (existing subagent in pr-review-toolkit) — delineate or supplement
- [ ] CSO check: does "dashboard card permanently empty" / "why don't I see any X" trigger reliably?
