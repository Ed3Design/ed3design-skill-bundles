---
name: enum-value-discovery-before-sql-where
description: Use BEFORE writing any SQL WHERE-clause that filters on a string/enum-typed column. Schema-verify via `\d <table>` shows COLUMN TYPE (text/varchar/enum) but NOT the actual values used. Code may set 'taken' while reviewer thinks 'accept'. Pattern: run `SELECT DISTINCT <col> FROM <table>` (or grep for `_update_<col>`-style setters in code) to discover the actual value-set BEFORE formulating WHERE. Without this discovery step, queries silently return wrong counts: rows matching the real value get excluded, user sees "0 results" while reality has many. The drift between assumed-values and actual-values is invisible in schema-introspection alone. Trigger on phrases like "how many <entity> with status X exist", "user_response='accept'", "SELECT ... WHERE <enum_col>=...", "why am I seeing no hits", "forensic DB analysis", "migration cleanup with status filter", "cockpit filter shows 0", "trade forensics". Do NOT load for known well-defined enum-types (PostgreSQL `CREATE TYPE ... AS ENUM`) where psql `\d` shows the value-set inline, for first-time-CREATE-TABLE queries (no existing data), or for non-text/non-enum columns (numeric/timestamp filters don't have this discovery-need).
---

# enum-value-discovery-before-sql-where

> ✅ **PROMOTED**: Pattern emerged from a production domain forensic session. TDD pressure test passed: GREEN-Subagent recognized the example as a 1:1 scenario and avoided the `WHERE user_response='accept'` anti-pattern; RED produced the same anti-pattern (was self-critical, but would have delivered a wrong query to the user).

## Pattern (short form)

Before any SQL WHERE clause with a string-/enum-typed column:

1. **Schema check** (maxim "verify DB schema"): `\d <table>`
   → returns COLUMN + TYPE, BUT not the actual values in use
2. **Value discovery**: `SELECT DISTINCT <col> FROM <table> ORDER BY 1;`
   → returns the real values. OR alternatively: code grep for setters (`_update_<col>`, `SET <col> = '...'`).
3. **Only then** formulate the WHERE clause with verified values

If (3) is done without (2) → query silently returns wrong counts. Reviewer sees "0 rows" where reality has many, falls into a wrong conclusion spiral.

## Concrete example (live encounter)

**Task**: Forensic baseline for your-app's signal performance.

**Wrong query**:
```sql
SELECT
  date_trunc('week', triggered_at)::date AS week_start,
  SUM(CASE WHEN user_response='accept' THEN 1 ELSE 0 END) AS user_accepted
FROM v3_signals
WHERE triggered_at >= NOW() - INTERVAL '4 weeks'
GROUP BY 1;
```

**Result**: `user_accepted = 0` in ALL weeks.
**Conclusion**: "User-Response-Loop is broken, the user has never accepted".

**User correction**: "I have indeed accepted signals (Alphabet, Bayer)."

**Reality via value discovery**:
```sql
SELECT user_response, COUNT(*) FROM v3_signals GROUP BY user_response;
```
```
 user_response | count
---------------+-------
 pending       |   107
 taken         |    17  ← the user's accepts here!
 skipped       |     5
```

→ Code sets `'taken'`, not `'accept'`. Grep verification in code:
```bash
grep -rn "user_response\s*=" --include="*.py" .
# strategic/v3_trade_manager.py:96: mark_signal_taken → 'taken'
# strategic/v3_trade_manager.py:100: mark_signal_skipped → 'skipped'
```

→ Original query must be corrected to `WHERE user_response='taken'`. Reality was 17 accepts, not 0.

## Quick reference: when to discover, when to skip

| Situation | Discovery needed? |
|---|---|
| WHERE on `text`/`varchar` column with string value | ✅ YES, always |
| WHERE on PostgreSQL `ENUM` type (`CREATE TYPE ... AS ENUM`) | ⚠️ No if `\d` shows the values — else YES |
| WHERE on `boolean` | ❌ No (only 2 values) |
| WHERE on `integer` with range filter (>, <) | ❌ No |
| WHERE on timestamp/date | ❌ No |
| WHERE on `id IN (...)` with concrete IDs | ❌ No |
| JOIN condition with string column | ✅ YES for both tables |
| AGGREGATE like `SUM(CASE WHEN col='X' THEN ...)` | ✅ YES — same trap as WHERE |

## Discovery methods (in order of speed)

### A. DB query (1-2s, always correct)
```sql
SELECT DISTINCT <col> FROM <table> ORDER BY 1;
-- or with counts:
SELECT <col>, COUNT(*) FROM <table> GROUP BY <col> ORDER BY 2 DESC LIMIT 20;
```

### B. Code grep (5-10s, shows setter intent)
```bash
# Where is the column set?
grep -rn "SET <col>\s*=" --include="*.py" --include="*.sql"
grep -rn "<col>\s*=\s*['\"]" --include="*.py"
# Functions that set the value:
grep -rn "mark_<entity>\|set_<col>\|update_<col>" --include="*.py"
```

### C. Schema-migration backtrace (complex, only for history questions)
```bash
grep -rn "<col>" core/db/migrations.py  # if initialized there
git log -p -- core/db/migrations.py | grep -A 2 "<col>"
```

→ For live forensics: **A first**. For code-understanding questions without live DB: **B first**.

## Anti-Patterns

| Anti-Pattern | Correct |
|---|---|
| `WHERE status='active'` without discovery | first `SELECT DISTINCT status FROM ...` |
| "Status values are always pending/accept/reject" — assumption from training data | every system has its own convention, verify |
| Forensic report presenting "0 rows match" as finding | first value discovery, otherwise wrong conclusion |
| `\d <table>` as sufficient schema verification | Schema only tells TYPE, not VALUES |
| Skipping discovery on AGGREGATE functions (`SUM(CASE WHEN col='X'...)`) | same trap as WHERE — aggregates with wrong string silently return 0 |
| Ignoring the user's "it works" against data result | if user reality ≠ data, the query is suspect — run discovery |

## Discovery surrogates without live DB access

If you have no live `psql` (subagent context, code review without prod access, new codebase without DB setup):

1. **Code grep for setters** is the primary surrogate:
   ```bash
   grep -rn "mark_<entity>\|set_<col>\|<col>\s*=\s*['\"]" --include="*.py"
   ```
2. **Read migration file** if available: often initial values or CHECK constraints are defined there
3. **Test fixtures** in `tests/` often show the canonical values (by convention `factories/<table>.py`)
4. **Fall back to the caller** (instead of guessing): "I need `SELECT DISTINCT <col> FROM <table>` output before I can finalize the WHERE clause. Can you run that or is the output available?" — frame it explicitly as a precondition, do not heuristically guess and hope.

→ This option is more legitimate than the training-data heuristic (`'accept'`/`'accepted'`) because it explicitly hands the uncertainty back to the caller's setup rather than silently burying it in the query.

## Background: TDD progress (Bulletproofing Log)

### Cycle 1 — PASS via Subagent-Pair-Dispatch

- **RED-Subagent** (without skill, prompt: "Write SQL for 4-week accepts on `v3_signals.user_response`"): wrote `WHERE user_response = 'accepted'` from training-data heuristic. Was self-critical in step 3 ("guessed heuristically, I did NOT check which distinct values are actually in the column") — recognized the gap but did not act on it. Would have given the user a wrong `count=0` query.

- **GREEN-Subagent** (with skill, identical prompt): prepended a discovery query as Step 0 → `SELECT user_response, COUNT(*) FROM v3_signals GROUP BY user_response`. Recognized the example in the skill as a 1:1 match → adopted `'taken'` as verified code value. Additionally documented "if count=0 do not draw naive conclusion" as anti-pattern.

- **Refactor applied**: Section "Discovery surrogates without live DB access" added (from GREEN self-reflection: "hint for what to do when a subagent has NO live DB access — the skill implicitly assumes executable `psql`"). Closes caller-context bias for subagents without DB tool.

### Cycle-2 Backlog (Polish, non-blocking)

1. **REST API variant**: pattern applies analogously to REST query params with enum-typed filter — separate section "Enum discovery for API filters (not just SQL)"
2. **GraphQL variant**: schema introspection vs resolver actual values — presumably same bug class, worth its own section
3. **Cross-skill synergy with `pre-migration-data-verification`**: in migration cleanup, discovery is MANDATORY also for the `WHERE` of UPDATE/DELETE statements — perhaps reinforce cross-reference

## Cross-references

- maxim "verify DB schema before every query" — column verification
- This skill is the **separate value-verification** layer to column verification
- `pre-migration-data-verification` — related: count data violations before constraint add
- maxim "counter-thesis check" — "could the 0 be wrong?" is a counter-thesis that leads to discovery

## Real-world impact

Forensic baseline for production domain:
- **Initial query**: 0 user_accepts in 4 weeks → conclusion "user-response loop broken"
- **User correction**: "Indeed I have, Alphabet + Bayer"
- **Value discovery** showed: 17 `'taken'`, 0 `'accept'` (code value is 'taken')
- **Result**: bug was in MY query, not in the system. Would have led to wrong forensic conclusion ("user-response pipeline broken") — and correspondingly wrong code-repair sessions.

**Time savings when correctly applied**: ~30-60 min of misdiagnosis detour avoided.

## Notes for skill reviewer (next session)

- If skill fails TDD: possibly just the maxim "DB schema before every query" — adding a "values before every WHERE" clause is enough.
- If TDD passes strongly: could become cross-project standard (all SQL forensic sessions)
- **Variant to evaluate**: does it also apply to API filters (REST query params with enum)?
