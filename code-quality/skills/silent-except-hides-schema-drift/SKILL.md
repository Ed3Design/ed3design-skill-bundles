---
name: silent-except-hides-schema-drift
description: |-
  Use when reviewing or writing Python code with `try`/`except Exception:` clauses around SQL queries (asyncpg, psycopg2, sqlalchemy, sqlite3) where the except-branch either (a) silently returns an empty collection (`signals = []`, `rows = {}`, `data = None`), (b) re-renders the UI with empty state ("No active signals", "No data today"), or (c) catches with a bare/overly-broad type — without `logger.exception()` or re-raise. Danger: a schema-drift bug (column does not exist, FK-target-rename, ORM-out-of-sync) and a legitimate empty-result look IDENTICAL to the user. A dashboard panel saying "No signals today" silently means EITHER no signals OR the SQL crashed and was swallowed. Trigger phrases like "dashboard shows empty but DB has data", "except Exception: signals = []", "dashboard card permanently empty", "code swallows DB error". Do NOT load for non-DB silent-except, catch-and-re-raise patterns, or narrow except-clauses that log.

---

# Silent-Except hides schema drift

> ✅ **PROMOTED** 2026-06-15 — TDD pressure-test PASS. RED-Subagent reviewed `except Exception: return []` around SELECT on `opportunities.yf_symbol`; flagged silent-exception swallowing correctly, but Honesty-section: "Ich habe `yf_symbol` als Spaltennamen nicht hinterfragt. Ich habe Symptom 1 (Silent-Except) gefangen, aber Symptom 2 (mögliche Schema-Drift dahinter) nicht aktiv als Hypothese auf den Tisch gelegt." GREEN-Subagent identified BOTH issues in one review (silent-except + schema-drift on `yf_symbol`/`symbol` column-rename), proposed `log.exception()` + `information_schema.columns` verify, distinguished `log.exception` vs `log.error`. Skill description matched scenario 1:1 (canonical example).

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

## Background: TDD-Verlauf (Bulletproofing-Log)

### Cycle 1 — 2026-06-15 (PASS)

- **RED-Subagent** (without skill, code-review scenario with `except Exception: return []` around `SELECT yf_symbol FROM opportunities`, dashboard `(0)` for 3 days while DB has 2 signals): flagged silent-exception swallowing correctly + recommended `logger.exception`. Honesty: "Ich habe `yf_symbol` als Spaltennamen nicht hinterfragt — die Schema-Verify-Maxime fordert das aber. Ich habe Symptom 1 (Silent-Except) gefangen, aber Symptom 2 (Schema-Drift dahinter) nicht aktiv als Hypothese auf den Tisch gelegt."
- **GREEN-Subagent** (with skill, identical scenario): identified BOTH issues in one review — silent-except suppression AND schema-drift on `yf_symbol`/`symbol` column-rename. Proposed `log.exception()` + `information_schema.columns` verify-step. Self-reflection: "Skill's canonical example matches scenario 1:1 — unusually direct mapping."

### Cycle-2-Backlog (Polish, non-blocking)

- Cross-reference with `superpowers:silent-failure-hunter` (existing subagent in pr-review-toolkit) — delineate scope: this skill is the DB-query specialization; silent-failure-hunter is the general subagent
- Edge-case section: specific `except asyncpg.UndefinedColumnError` (narrow + logged is fine) vs `except Exception` (broad + silent is the trap)
