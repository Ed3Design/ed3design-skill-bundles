---
name: silent-except-versteckt-schema-drift
description: Use when reviewing or writing Python code with `try`/`except Exception:` clauses around SQL queries (asyncpg.connect/conn.fetch/conn.execute, psycopg2, sqlalchemy, sqlite3, or any DB-driver call) where the except-branch either (a) silently returns an empty collection (`signals = []`, `ticks = []`, `rows = {}`, `data = None`), (b) re-renders the UI with the empty state ("Keine aktiven Signale", "No data today", "Loading..."), or (c) catches with a bare or overly-broad type — without `logger.exception()` / `log.error()` / re-raise. The danger: a Schema-Drift bug (`column "X" does not exist`, FK-target-rename, table-renamed-in-migration, ORM-model-out-of-sync) AND a legitimate empty-result state look IDENTICAL to the user. A dashboard panel that says "Keine Signale heute" silently means EITHER (1) there genuinely are no signals OR (2) the SQL crashed and was swallowed — without a log entry, you cannot tell which. Wolf-Live-Beweis 09.06.2026 Schema-Drift-Audit: `api/routes/dashboard/modules/{signals,timeline}.py` had `except Exception: signals = []` / `except Exception: ticks = []` around SELECT queries on `opportunities.yf_symbol` (column doesn't exist — opportunities has `symbol`). Result: Dashboard's "Active Signals" card showed `(0)` for unknown duration while DB had 2 real open signals (PBR SHORT, AAPL LONG). Trader-logs in 24h-window: **0 hits** on "column does not exist" — silent-except clauses fired BEFORE any log entry. Wolf would never notice without code-audit. Trigger phrases like "silent except mit schema-drift", "Dashboard zeigt empty aber DB hat Daten", "warum sehe ich keine Signale", "except Exception: signals = []", "Dashboard-Card permanently empty", "Code swallows DB error", "silent-failure mit DB-Query". Do NOT load for non-DB silent-except (network calls, file-IO — different concern; use general silent-failure-hunter), for catch-and-re-raise patterns (already correct), or for narrow except-clauses that catch specific exception types like `asyncpg.PostgresError` AND log them (probably fine, audit case-by-case).
---

# Silent-Except verstecken Schema-Drift

> ⚠️ **DRAFT 2026-06-09** — needs TDD-Promotion (RED: deploy Code mit silent-except + Schema-Drift, observe User sieht "leer"; GREEN: deploy mit logger.exception, observe Drift im Log sichtbar). See `skill-tdd-promotion-workflow`.

## Overview

`try: ... except Exception: data = []` ist verlockend defensive — der User sieht den UI-State weiter und kein 500-Error. Aber bei DB-getriebenen Endpoints macht dieser Pattern **Schema-Drift-Bugs unsichtbar**:

- Spalte umbenannt (Migration) → Code referenziert alten Namen → `column "X" does not exist` → silent-except → User sieht "empty"
- Tabelle umbenannt → `relation does not exist` → silent-except → User sieht "empty"
- FK-Target verschoben → `foreign key constraint failure` → silent-except → User sieht "empty"
- Type-Mismatch (TEXT vs JSONB nach Migration) → `column cannot be cast` → silent-except → User sieht "empty"

Wenn das UI-State zwischen "echt leer" und "Code-broken" nicht unterscheidet, geht der Bug latent in Production — Tage, Wochen, manchmal Monate — ohne Trigger für Wolf-Aufmerksamkeit.

**Die 09.06.2026-Erfahrung**: Dashboard's "Active Signals"-Card zeigte `(0)` während DB 2 echte Signale hatte (PBR + AAPL). 24h-Trader-Logs: **0 Hits auf "column does not exist"**. Drift war komplett vor Wolf versteckt.

## When to use (Audit-Trigger)

Du reviewst gerade Code mit:
- `try:` / `except Exception:` (oder bare `except:`)
- innerhalb des try: irgendein DB-Driver-Call (`asyncpg.connect`, `conn.fetch`, `conn.execute`, `psycopg2.connect`, `engine.execute`, etc.)
- im except: Zuweisung `var = []` / `var = {}` / `var = None` ODER ein UI-Render mit Default-State
- KEIN `logger.exception()`, KEIN `log.error()`, KEIN re-raise

Du diagnostizierst ein Symptom:
- „Dashboard-Card / Tab / Panel zeigt PERMANENT leer/null, aber DB hat Daten"
- „Endpoint returnt 200 mit empty body statt Error"
- „Wir haben kein Log für den Bug, aber das UI verhält sich offensichtlich falsch"
- „User-Beschwerde 'X funktioniert nicht', aber Logs sind leer"

## When NOT to use

- **Non-DB silent-except** (file-IO, HTTP-Calls, JSON-parse) — andere Bug-Klasse, andere Heuristik
- **Specific exception types**: `except asyncpg.UndefinedColumnError:` ODER `except (psycopg2.errors.UndefinedColumn, ...):` — engt das Problem korrekt ein, weniger gefährlich. Trotzdem auditieren ob die except-Klasse zu eng/breit ist.
- **Catch-and-re-raise**: `except Exception as e: log.exception(...); raise` — schon korrekt, kein Eingriff nötig
- **Tests / Mocks**: `except Exception: pass` in Test-Setup ist anders zu bewerten

## The 4-Step Audit Pattern

### Step 1 — Find candidates

Grep über die Codebase:
```bash
# Direkt-Pattern
rg -n 'except Exception:\s*\n\s+\w+\s*=\s*\[\]' --type py
rg -n 'except.*:\s*\n\s+\w+\s*=\s*None' --type py
# Mit DB-Call darüber
rg -nB 10 'except Exception:' --type py | grep -B 10 -E 'fetch|execute|connect|query'
```

### Step 2 — Verify the DB-call would actually drift

Pro Treffer: identifiziere das SQL-Statement und prüfe gegen das ECHTE Schema:
```bash
# Schema-Realität aus Production-DB ziehen
docker exec mydb psql -U <user> -d <db> -tA \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'X' ORDER BY ordinal_position"
```
Match jede Spalte im Code-SQL gegen die echten Spalten.

### Step 3 — Live-verify by hitting the endpoint

Wolf-Skill `frontend-ui-self-verify-before-user-demo` kommt jetzt zum Einsatz:
```bash
curl -sf 'http://app-host/endpoint' | head -30
# Wenn "Keine Daten" / empty list trotz erwarteter DB-Daten → Bug bestätigt
```

Oder via Chrome-DevTools-MCP / Playwright direkt im Browser-Render-Pfad.

### Step 4 — Fix the except clause

Nicht das try wegnehmen — den except instrumentieren:

```python
# ❌ FALSCH
try:
    rows = await conn.fetch("SELECT o.yf_symbol FROM opportunities o WHERE o.status = 'open'")
    signals = [_row_to_signal(r) for r in rows]
except Exception:
    signals = []  # User sieht "leer", Drift unsichtbar

# ✅ RICHTIG
import logging
log = logging.getLogger(__name__)

try:
    rows = await conn.fetch("SELECT o.symbol AS yf_symbol FROM opportunities o WHERE o.status = 'open'")
    signals = [_row_to_signal(r) for r in rows]
except Exception:
    log.exception("active_signals query failed — returning empty list")
    signals = []
```

`log.exception()` (statt `log.error()`) ist wichtig: es enthält das Traceback automatisch. Mit `log.error("X")` sieht man nur "X failed", nicht WARUM.

## Why `log.exception` not raise?

In UI-Endpoints (Dashboard-Cards, Side-Panels, Status-Tiles) ist die UX-Anforderung typischerweise „Card lädt schlecht > ganze Page crash". Daher Default-State (`signals = []`) ist UX-korrekt, aber:

- **Log-Layer MUSS sehen dass es failed** → `log.exception`
- **Optional**: zweite UI-State unterscheiden („Daten konnten nicht geladen werden") statt nur „leer"

Bei kritischeren Calls (Trade-INSERT, Money-Move): NICHT silent fangen — re-raise mit HTTP-Status-Code wäre korrekter.

## Anti-Patterns

| Pattern | Why bad |
|---|---|
| `except Exception: pass` | gibt nicht mal eine Default-Variable zurück — NameError downstream |
| `except: signals = []` | bare except fängt auch `KeyboardInterrupt`, `SystemExit` — Worst-Case |
| `except Exception: signals = []; print(traceback)` | print geht in stdout, nicht Logging-Aggregator — bei Container/systemd unsichtbar |
| `except Exception as e: log.error(f"failed: {e}")` | nur Message, kein Traceback — File:line des Drifts nicht erkennbar |
| `try: rows = await conn.fetch(...); except: rows = await conn.fetch(...)`  retry | falsch — Drift wird sich nicht auflösen, Loop hängt |

## Detection-Indikatoren in der Audit-Praxis

Diese drei Heuristiken weisen mit hoher Wahrscheinlichkeit auf Drift hin:

1. **UI sagt "(0)" oder "Keine X" konstant** über Tage/Wochen, obwohl Use-Case-Verkehr da sein müsste
2. **Logs zeigen 0 Errors** in einem Endpoint trotz hoher Aufruf-Frequenz (kein 200/500 wäre normal — alles 200 ist verdächtig)
3. **`docker logs ... | grep -i "column.*not exist"` = 0** trotz wahrscheinlicher Migration-Geschichte

## Cost of Skipping (09.06.2026 Wolf-empirisch)

- **5 Schema-Drift-Findings** in dashboard/modules (signals.py, timeline.py, portfolio.py)
- **2 davon silent**: `except Exception: signals = []` und `except Exception: ticks = []`
- **Unbekannte Drift-Dauer**: Wolf hat das Dashboard wahrscheinlich seit Wochen mit leeren Cards gesehen, ohne Trigger zur Untersuchung
- **Direkter Outcome-Sichtbarkeits-Verlust** (Wolf-Maxime "ultimative-platform: sichtbares Outcome")

→ Detail: [[../../Documents/Vault/ClaudetteV/02 Projekte/trading/ultimative-platform/code-review-aggregate-2026-06-09]] (F2, F5)

## Promotion Checklist (DRAFT → GA)

- [ ] RED-Subagent: deploy Code mit `except Exception: X = []` + Schema-Drift in SELECT — verify User sieht „leer", Logs zeigen 0 Errors
- [ ] GREEN-Subagent: gleicher Code mit `log.exception(...)` — verify User sieht „leer" UND Log enthält Drift-Traceback
- [ ] Edge-Case: spezifischer `except asyncpg.UndefinedColumnError` — bestätigen Skill den Pattern korrekt klassifiziert
- [ ] Cross-Reference mit `superpowers:silent-failure-hunter` (existing Subagent in pr-review-toolkit) — abgrenzen oder ergänzen
- [ ] CSO-Check: triggert "Dashboard-Card permanently empty" / "warum sehe ich keine X" zuverlässig?
