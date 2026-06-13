---
name: enum-known-values-via-insert-grep
description: Use BEFORE writing or editing a Python-side constants/enum/validator-set that should match a DB-column's real value-space — `_KNOWN_X = {...}`, `VALID_<DIMENSION> = frozenset(...)`, `class XStatus(str, Enum)`, `pydantic.Field(..., regex='^(a|b|c)$')`, in-app filter-allow-lists. STOP and grep ALL `INSERT INTO <table>` + ALL `<table>.<column> = ...` setter-lines + ALL UPDATE-statements that touch the column, BEFORE deciding the value-set in Python. Specifically trigger when (a) you write phrases like "maintain the _KNOWN_SOURCES list", "define valid_phase_set", "build pydantic validator for <column>", "filter-allowlist for UI", "new constants for <DIMENSION>", (b) you are about to copy a value-set from spec / docs / memory without grepping the real INSERTs first, (c) the column is shared between MULTIPLE call-sites (different services, different scripts, replay vs live, mock vs production). Also use when reviewing existing constants and the symptom is "value X is silently accepted" or "value Y is wrongly rejected — it IS in the code". Real-world experience: `_KNOWN_SOURCES` mixed `system_phase.mode` with `virtual_trades.source` (different columns of different tables!), typo `shadow` silently accepted, real values `manual` + `replay` wrongly warned. Method: `grep -rn "INSERT INTO <table>"` + `grep -rn "<table_var>\.<column>\s*="` + `grep -rn "UPDATE <table> SET <column>"` — then verify actual values + disambiguate table/column/mode-field (multiple tables can have same-named columns with different value-spaces). Do NOT load for greenfield-tables (no INSERT exists, you are DEFINING right now), for typed-Postgres-ENUMs (PG `CREATE TYPE ... AS ENUM` shows the list in `\d` completely), or for purely internal Python-Constants without DB context (e.g. UI-theme-names). Complement to `enum-value-discovery-before-sql-where` (this skill is for the WRITE/DEFINE side, that skill is for the SQL WHERE-read side) + complement to `schema-verify-via-information-schema` (this assumes you already know the table+column, want to know the values).
---

# Enum Known-Values via INSERT-Grep

> ✅ **PROMOTED** — TDD Cycle 1 **STRONG PASS**. RED-Subagent reacted heuristically correct ("grep first") but without concrete verification at a real repo (7 self-critique points). GREEN-Subagent executed **18 Bash-Tool-Uses** in a real production domain repo and delivered substantial findings that would not have been reached without the skill: (1) current `_KNOWN_SOURCES` is already different from what the scenario assumed (recent hotfix), (2) missing productive value `'real'` from `ml/real_trade_bridge.py:142` — would silently trigger `unknown source: real`-warnings for weeks, (3) Cross-Table-False-Positives explicitly rejected (`'optimizer'`, `'manual'@strategy_params`, `'av_earnings'`), (4) `_MODE_TO_SOURCES`-Mapping + DB-Constraint-Implications identified. **R1-Refactor applied**: Step 4b "DB-Constraint-Verify" added as own sub-section — if a CHECK-Constraint / PG-ENUM limits the value-range, a constants-edit alone is ineffective.

## Overview

**A Python constants list that covers DB-values must be derived from the DB-values, not from memory.**

When you write `_KNOWN_X = {...}`, `VALID_<DIMENSION>`, `pydantic.Field(regex="^(a|b|c)$")`, or a status-enum validator, that is a **contract with the database**. If the list deviates from the real value-space:

- **False-positive**: typo values slip through ("shadow" gets accepted even though nobody inserts that)
- **False-negative**: real values get warned / rejected ("manual" triggers `unknown source` warning even though it's legitimate)
- **Cross-Table-Drift**: columns of the same name exist in multiple tables with different value-spaces — Python side mixes them accidentally

Skill = discipline: **`grep -rn "INSERT INTO <table>"` + all `<column> =` setters BEFORE the constant is written.**

This maxim is the definition-side variant of the maxim "avoid schema-drift": not only must the columns exist, but the value-ranges must also align with the code side.

## When to use

**Trigger phrases (you would say right now)**:
- "maintain / extend the _KNOWN_X list"
- "define valid_phase_set / valid_states"
- "build pydantic validator for <column>"
- "filter-allowlist for UI / API"
- "new constants for DIMENSION X"
- "enum-class for <column>"
- "allowed-values for <field>"

**Symptom-Trigger** (you are investigating an existing skill):
- "Value X is silently accepted even though nobody inserts X" → grep INSERTs
- "Value Y triggers `unknown source`-warning but is in code as a setter" → grep INSERTs + setters
- "Cohort A vs B from DB" → check whether both cohorts use the same value-vocabulary

**High-risk markers**:
- The column has the **same name in multiple tables** (e.g. `mode` in `system_phase` AND `virtual_trades` AND `signals_log`)
- The column is **type `text`** instead of `enum` — PG does not help
- Values are written in Python code at **multiple locations** (multiple services, multiple workers)
- Code has a `_KNOWN_X` set OR a pydantic validator OR a UI dropdown on the same column
- Replay-mock setter differs from live setter

## When NOT to use

- **Greenfield table**: no INSERT exists, you are **defining** the values right now. Then Constants → Migration → Setter, in that order
- **Typed PostgreSQL ENUM** (`CREATE TYPE foo AS ENUM ('a', 'b', 'c')`): `\d <table>` shows the list completely + DB already rejects unknown values
- **Purely internal Python constants** without DB context (UI-theme-names, in-memory cache keys)
- **Single-writer pattern** with code lock (only one class may insert + it uses the constants list — validators are co-located)

## The 4-Step Insert-Grep Flow

### Step 1 — Identify table + column explicitly

Before the grep, write down:
- **Table**: e.g. `virtual_trades`
- **Column**: e.g. `source`
- **Suspected value list**: e.g. `{"live", "training", "shadow"}`
- **Assumption about disambiguation**: are there **same-named columns in other tables**? (risk check)

### Step 2 — Three grep passes for INSERTs + Setters + UPDATEs

```bash
# Pass 1: INSERT statements (all INSERTs touching virtual_trades)
grep -rn "INSERT INTO virtual_trades" --include="*.py" | head -50

# Pass 2: Setter lines (column = value or dict-style)
grep -rn "\.source\s*=\s*['\"]" --include="*.py" \
  | grep -E "(virtual_trade|vt|trade)" \
  | head -50

# Pass 3: UPDATE statements
grep -rn "UPDATE virtual_trades SET" --include="*.py" | grep "source"

# Pass 4 (Cross-Table-Check): same column-name in other tables
grep -rn "['\"]source['\"]" --include="*.sql" | head -20
grep -rn "\.source\s*=" --include="*.py" | head -20  # without table filter
```

### Step 3 — Distill value-set from hits

Sort each hit:

| Value | Source | Really used? | Similar-but-different? |
|---|---|---|---|
| `'live'` | `services/live_dispatcher.py:42` | ✅ yes | — |
| `'training'` | `services/training_runner.py:104` | ✅ yes | — |
| `'manual'` | `cli/manual_trade.py:67` | ✅ yes | — |
| `'replay'` | `scripts/replay_session.py:88` | ✅ yes | — |
| `'shadow'` | `services/system_phase.py:21` (sets `system_phase.mode`!) | ❌ wrong table | belongs to `system_phase.mode`, not `virtual_trades.source` |

### Step 4 — Define constants correctly with cross-table disambiguation

```python
# WRONG (mixes two tables):
_KNOWN_SOURCES = {"live", "training", "shadow"}  # 'shadow' does not belong here

# RIGHT (one per table/column, documented):
# virtual_trades.source — values from INSERT-grep
_KNOWN_TRADE_SOURCES = {"live", "training", "manual", "replay"}

# system_phase.mode — separate set
_KNOWN_PHASE_MODES = {"live", "training", "shadow"}
```

In the validator or logger-warning:
- Use `_KNOWN_TRADE_SOURCES` for `virtual_trades.source`
- Use `_KNOWN_PHASE_MODES` for `system_phase.mode`
- Never mix

### Step 4b — DB-Constraint-Verify (R1-Refactor)

**If the column in the DB is constrained by a `CHECK` constraint, a PG `ENUM` type definition, or a foreign-key lookup table, the constants-edit alone is ineffective** — new values will be rejected by the DB engine with `CheckViolation` or `InvalidTextRepresentation`.

```bash
# CHECK constraint on the column?
psql -c "\d+ virtual_trades" | grep -A1 "Check constraints"

# If ENUM type:
psql -c "\dT+ source_type"  # shows the enum values

# If FK lookup:
psql -c "SELECT * FROM source_lookup;"
```

**With a limiting DB constraint**: requires additional migration **BEFORE** the Python constants edit:

```sql
-- Example: extend CHECK constraint
ALTER TABLE virtual_trades DROP CONSTRAINT IF EXISTS virtual_trades_source_check;
ALTER TABLE virtual_trades ADD CONSTRAINT virtual_trades_source_check
  CHECK (source IN ('live', 'training', 'manual', 'replay', 'real', 'paper'));

-- Example: extend PG ENUM (PG13+)
ALTER TYPE source_type ADD VALUE 'paper';
```

Order: **DB-Migration → Python-Constants-Update → Setter-Code → Test**. Reversed, it crashes on the first real INSERT.

## Quick Reference

| Constants type | Grep pattern (example) |
|---|---|
| `_KNOWN_X = {...}` | `grep -rn "INSERT INTO <table>" + grep -rn "\.<col>\s*="` |
| `pydantic regex='^(a|b)$'` | same plus `grep "<col>:.*=" --include="*.py"` |
| `class XEnum(str, Enum)` | same plus `grep "class.*Enum"` for existing Enums |
| UI dropdown options | same plus `grep "options=\[" --include="*.ts,*.py"` |

## Anti-Patterns

| Anti-Pattern | Lesson |
|---|---|
| Copying `_KNOWN_X` from spec/docs without grep | Spec drifts, code does not — Single Source of Truth is INSERT |
| "I know the 3 values from memory" | Real case: 3 of 5 values were wrong (typo `shadow` + missing `manual`/`replay`) |
| Column name as disambiguation sufficient | `mode` exists in `system_phase` AND `signals_log` AND `virtual_trades` — same-name ≠ same value-space |
| Validators without table suffix | `_KNOWN_SOURCES` is ambiguous; `_KNOWN_TRADE_SOURCES` + `_KNOWN_PHASE_MODES` are explicit |
| Value list in a single file instead of central | Each new source lands with only one maintainer → drift guaranteed. **One** validators module per DB column |

## Cost of Skipping (real)

**Real-world Phase-5-Re-Review** (Schema-Drift-Sweep):
- `_KNOWN_SOURCES = {"live", "training", "shadow"}` from memory
- Reality (clarified by INSERT-grep): `virtual_trades.source` actually had `{"live", "training", "manual", "replay"}` (no `shadow`)
- `shadow` was a `system_phase.mode` value — different table
- Consequence before fix: `manual` + `replay` triggered silent `unknown source` warnings (filling logs), `shadow` typo would have been wrongly accepted
- Fix: two separate constants-sets per table

**Pattern**: same-named columns in different tables with different value-ranges are one of the most common drift sources. Python side not from memory — from the INSERT.

## Red Flags — STOP and grep

- You are writing `_KNOWN_<DIMENSION>` or a pydantic validator
- Your value list comes from memory / from spec / from old docs
- The column might exist in multiple tables
- You have not established a validators convention per table/column

**All mean: 3 grep passes (INSERT, Setter, UPDATE) + cross-table check, then constants per table/column named explicitly.**

## Cross-References

- **COMPLEMENT (read side)**: `enum-value-discovery-before-sql-where` — same pain from SQL WHERE perspective
- **COMPLEMENT**: `schema-verify-via-information-schema` — verifies that the column even exists
- **COMPLEMENT**: `silent-except-versteckt-schema-drift` — the `except Exception: x = []` pattern hides these drift bugs
- maxim: "Single Source of Truth — hardcoded defaults are ticking bombs"

## Background: TDD progress (Bulletproofing Log)

### Cycle 1 — STRONG PASS with R1 Refactor

- **RED-Subagent** (without skill, scenario "Extend _KNOWN_SOURCES with 'paper' for paper-trading mode"): Reacted heuristically correct from prior pattern ("grep first"), but **without repo access** — gave commands instead of executing them. Self-critique listed 7 points (no concrete verification, ignored migration history, did not mention test fixtures, overlooked logging downstream, did not check naming convention, did not search user-specific notes, did not directly answer "is that enough?").

- **GREEN-Subagent** (with skill): **Executed 18 Bash-Tool-Uses** in the real production repo `your-app/` and delivered 4 substantial findings:
  1. **Code-state drift**: `_KNOWN_SOURCES` is currently `{"training", "live", "backtest", "manual", "replay"}` — NOT the list claimed in the scenario. A recent Phase-5-Re-Review hotfix had already happened.
  2. **Outstanding tech-debt discovered**: `ml/real_trade_bridge.py:142` writes `source='real'` into `virtual_trades`, but it is missing from `_KNOWN_SOURCES` → silent `unknown source: real` warnings.
  3. **Cross-Table-False-Positives correctly rejected**: `'optimizer'`, `'av_earnings'`, `'combo_optimizer'` → other tables (`strategy_params.source`, etc.), do NOT belong in `virtual_trades.source` set.
  4. **`_MODE_TO_SOURCES`-Mapping + DB-Constraint-Implication**: When `system_phase.mode='paper'` triggers, additionally `_MODE_TO_SOURCES` AND possibly PG-ENUM/CHECK-Constraint must be extended — otherwise the first `SET mode='paper'` attempt crashes.

- **R1 Refactor applied**: Step 4b "DB-Constraint-Verify" added as own sub-section with code examples for CHECK constraint update, PG ENUM extension, FK lookup insert. Order documented explicitly: DB-Migration → Python-Constants → Setter → Test.

- **Avoided Anti-Pattern**: GREEN explicitly noted that the obvious answer "Yes, just add 'paper'" would have produced 4 bugs: (a) misses the recent hotfix, (b) leaves `'real'` missing, (c) cements `'shadow'` cross-table error, (d) lets DB constraint crash.

### Cycle-2 Backlog (Polish, non-blocking)

1. **Test pattern for completeness check**: Test that compares `_KNOWN_X` against `_MODE_TO_X` mapping (every mode value must be in sources set). GREEN suggested this.
2. **CWD-mismatch hint** for subagents: make repo path explicit when CWD is not the production repo.
3. **DB-Live-Verify as optional Step 4c**: `SELECT source, COUNT(*) FROM <table> GROUP BY source` for existing-values audit. Complementary to Step 2 INSERT-grep.
4. **Cross-Reference**: `schema-use-case-mismatch-detection` as complement when DB-side value-range is limited.
